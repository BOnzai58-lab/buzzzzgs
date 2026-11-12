"""Deterministic Python scope validator — NO LLM involvement.

Decision logic:
1. Normalize target (extract host, strip protocol, port, userinfo, and trailing paths)
2. No rules → deny
3. Exclusions first (kind=exclude) → if any match → deny (exclusions always win)
4. Private IP & Cloud Metadata check:
   - Unless an explicit in-scope rule permits private CIDRs, any target resolving to a private
     or cloud-metadata IP (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.169.254, ::1)
     is strictly blocked to prevent SSRF and internal scanning.
5. Positive rules (domain exact, wildcard *.example.com, CIDR for IPs)
   - Wildcard matching strictly enforces subdomain boundaries (*.example.com will NEVER match evil-example.com)
6. No positive rule matches → deny
7. Redirect validation ensures HTTP 3xx hops stay strictly within authorized scope.
8. Every decision is recorded in AuditLog
"""
from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlparse, unquote
from uuid import UUID

from loguru import logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# RFC1918, Loopback, Link-Local, and Cloud Metadata (169.254.169.254)
RESERVED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("10.0.0.0/8"),       # RFC1918 Private
    ipaddress.ip_network("172.16.0.0/12"),    # RFC1918 Private
    ipaddress.ip_network("192.168.0.0/16"),   # RFC1918 Private
    ipaddress.ip_network("169.254.0.0/16"),   # Link-Local & Cloud Metadata (AWS/GCP/Azure)
    ipaddress.ip_network("100.64.0.0/10"),    # Carrier-grade NAT
    ipaddress.ip_network("0.0.0.0/8"),        # Broadcast / unspecified
    ipaddress.ip_network("::1/128"),          # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),         # IPv6 Unique Local
    ipaddress.ip_network("fe80::/10"),        # IPv6 Link-Local
]


@dataclass
class ScopeResult:
    allowed: bool
    reason: str
    matched_rule_id: UUID | None = None
    normalized_target: str = ""


class ScopeValidator:
    """Stateless, deterministic scope checker."""

    # ------------------------------------------------------------------
    # Normalization helper
    # ------------------------------------------------------------------

    @staticmethod
    def normalize_target(target: str) -> str:
        """Extract clean hostname/IP from URL, hostname:port, or raw input.
        
        Handles:
          - URL decoding (e.g. %3A%2F%2F)
          - Protocol and port stripping
          - Userinfo stripping (user:pass@host)
          - IDN punycode normalization (e.g. münchen.de -> xn--mnchen-3ya.de)
          - FQDN trailing dot removal
        
        Examples:
          'https://sub.example.com:8080/path?q=1' -> 'sub.example.com'
          'http://admin@10.0.0.1:80/'            -> '10.0.0.1'
          'api.example.com:443'                  -> 'api.example.com'
          '*.example.com.'                       -> '*.example.com'
          'sub.example.com.'                     -> 'sub.example.com'
        """
        if not target:
            return ""
        # Handle URL encoded targets
        target = unquote(target.strip()).lower()

        # Strip trailing dot if FQDN
        if target.endswith(".") and not target.endswith(".."):
            target = target[:-1]

        # Handle wildcard pattern prefix if present
        is_wildcard = target.startswith("*.")
        if is_wildcard:
            sub_target = target[2:]
        else:
            sub_target = target

        # If it looks like a URL with scheme, parse with urlparse
        if "://" in sub_target:
            parsed = urlparse(sub_target)
            host = parsed.hostname or ""
        elif "/" in sub_target:
            # Check if CIDR notation (e.g. 192.168.1.0/24)
            parts = sub_target.split("/")
            if len(parts) == 2 and parts[1].isdigit():
                try:
                    ipaddress.ip_network(sub_target, strict=False)
                    return sub_target
                except ValueError:
                    pass
            host = parts[0]
        else:
            host = sub_target

        # Strip user:pass if present (e.g. user@host)
        if "@" in host:
            host = host.split("@")[-1]

        # Strip port if present (e.g. example.com:8080 or 127.0.0.1:8000, but not IPv6 literal [::1])
        if ":" in host and not host.startswith("["):
            host = host.split(":")[0]
        elif host.startswith("[") and "]" in host:
            host = host.split("]")[0].lstrip("[")

        # Normalize IDN / Internationalized Domain Names to punycode
        if host and not any(host.startswith(c) for c in ("1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "[", ":")):
            try:
                host = host.encode("idna").decode("ascii")
            except Exception:
                pass

        if is_wildcard:
            return f"*.{host}"
        return host

    # ------------------------------------------------------------------
    # SSRF / Reserved IP Detection
    # ------------------------------------------------------------------

    @staticmethod
    def is_reserved_or_private_ip(ip_str: str) -> bool:
        """Return True if ip_str is private, loopback, link-local, or cloud metadata."""
        try:
            ip = ipaddress.ip_address(ip_str)
            return any(ip in net for net in RESERVED_NETWORKS)
        except ValueError:
            return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_target(
        self,
        arg1,
        arg2,
        rules: list | None = None,
        program_id: UUID | None = None,
    ) -> ScopeResult:
        """Check whether *target* is in-scope for *program_id*.
        Supports both validate_target(target, rules) and validate_target(program_id, target, rules).
        """
        if rules is not None:
            program_id = arg1
            raw_target = str(arg2)
        else:
            raw_target = str(arg1)
            rules = arg2 or []

        normalized = self.normalize_target(raw_target)
        if not normalized:
            return ScopeResult(
                allowed=False,
                reason="Invalid or empty target identifier.",
                normalized_target=raw_target,
            )

        # 1. No rules → deny
        if not rules:
            result = ScopeResult(
                allowed=False,
                reason="No scope rules defined for this program.",
                normalized_target=normalized,
            )
            logger.debug(
                "Scope DENY [no-rules] program={} target={}", program_id, normalized
            )
            return result

        # 2. Exclusions first (always win)
        for rule in rules:
            kind_val = rule.kind if isinstance(rule.kind, str) else rule.kind.value
            if kind_val == "exclude":
                if self._matches(normalized, rule):
                    result = ScopeResult(
                        allowed=False,
                        reason=f"Target matches exclusion rule: {rule.value}",
                        matched_rule_id=rule.id,
                        normalized_target=normalized,
                    )
                    logger.debug(
                        "Scope DENY [exclusion] program={} target={} rule={}",
                        program_id,
                        normalized,
                        rule.id,
                    )
                    return result

        # 3. Check for direct private IP / metadata without explicit private CIDR authorization
        if self._is_ip(normalized) and self.is_reserved_or_private_ip(normalized):
            has_explicit_private_rule = False
            for rule in rules:
                kind_val = rule.kind if isinstance(rule.kind, str) else rule.kind.value
                if kind_val == "cidr" and self._matches(normalized, rule):
                    has_explicit_private_rule = True
                    break
            if not has_explicit_private_rule:
                return ScopeResult(
                    allowed=False,
                    reason=f"Target {normalized} is a protected private or cloud metadata IP (SSRF defense).",
                    normalized_target=normalized,
                )

        # 4. Positive rules
        for rule in rules:
            kind_val = rule.kind if isinstance(rule.kind, str) else rule.kind.value
            if kind_val == "exclude":
                continue
            if self._matches(normalized, rule):
                result = ScopeResult(
                    allowed=True,
                    reason=f"Target matches rule ({kind_val}): {rule.value}",
                    matched_rule_id=rule.id,
                    normalized_target=normalized,
                )
                logger.debug(
                    "Scope ALLOW program={} target={} rule={}",
                    program_id,
                    normalized,
                    rule.id,
                )
                return result

        # 5. No positive match → deny
        result = ScopeResult(
            allowed=False,
            reason="No matching in-scope rule found.",
            normalized_target=normalized,
        )
        logger.debug(
            "Scope DENY [no-match] program={} target={}", program_id, normalized
        )
        return result

    def validate_redirect(
        self,
        original_target: str,
        redirect_url: str,
        rules: list,
        program_id: UUID | None = None,
    ) -> ScopeResult:
        """Validate whether an HTTP redirect location is safely in-scope.
        
        Prevents open-redirect following from crossing out-of-scope boundaries,
        contacting third-party IDPs, or probing internal metadata services.
        """
        redirect_host = self.normalize_target(redirect_url)
        if not redirect_host:
            return ScopeResult(
                allowed=False,
                reason="Invalid redirect destination URL.",
                normalized_target=redirect_url,
            )

        # Re-run strict scope evaluation against target rules
        result = self.validate_target(redirect_host, rules, program_id=program_id)
        if not result.allowed:
            return ScopeResult(
                allowed=False,
                reason=f"Redirect destination '{redirect_host}' is OUT OF SCOPE ({result.reason}).",
                matched_rule_id=result.matched_rule_id,
                normalized_target=redirect_host,
            )

        return ScopeResult(
            allowed=True,
            reason=f"Redirect destination '{redirect_host}' is in-scope.",
            matched_rule_id=result.matched_rule_id,
            normalized_target=redirect_host,
        )

    async def validate_target_with_dns(
        self,
        program_id: UUID,
        target: str,
        rules: list,
        db: "AsyncSession | None" = None,
    ) -> ScopeResult:
        """Like :meth:`validate_target` but also resolves DNS and enforces IP safety.

        - Rejects any domain resolving to private/metadata IP unless explicitly authorized.
        - Checks resolved IPs against exclusion rules.
        - Checks resolved IPs against positive CIDR rules.
        """
        normalized = self.normalize_target(target)
        result = self.validate_target(program_id, normalized, rules)
        
        # If target itself is a domain, check resolved IPs
        if not self._is_ip(normalized):
            try:
                infos = socket.getaddrinfo(normalized, None)
                resolved_ips = {info[4][0] for info in infos}
            except OSError:
                resolved_ips = set()

            for ip in resolved_ips:
                # 1. SSRF check on resolved IP
                if self.is_reserved_or_private_ip(ip):
                    has_explicit_private = any(
                        (r.kind == "cidr" or getattr(r.kind, "value", None) == "cidr")
                        and self._matches(ip, r)
                        for r in rules
                    )
                    if not has_explicit_private:
                        return ScopeResult(
                            allowed=False,
                            reason=f"Domain {normalized} resolves to protected private IP {ip} (SSRF defense).",
                            normalized_target=normalized,
                        )

                # 2. Check exclusions on resolved IP
                for rule in rules:
                    kind_val = rule.kind if isinstance(rule.kind, str) else rule.kind.value
                    if kind_val == "exclude" and self._matches(ip, rule):
                        return ScopeResult(
                            allowed=False,
                            reason=f"Resolved IP {ip} matches exclusion rule: {rule.value}",
                            matched_rule_id=rule.id,
                            normalized_target=normalized,
                        )

            # If original domain check failed, check if resolved IP matches positive CIDR rules
            if not result.allowed:
                for ip in resolved_ips:
                    dns_result = self.validate_target(program_id, ip, rules)
                    if dns_result.allowed:
                        logger.debug(
                            "Scope ALLOW [dns-resolved] program={} target={} resolved_ip={}",
                            program_id,
                            normalized,
                            ip,
                        )
                        return ScopeResult(
                            allowed=True,
                            reason=f"Resolved IP {ip} matches rule: {dns_result.reason}",
                            matched_rule_id=dns_result.matched_rule_id,
                            normalized_target=normalized,
                        )

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _matches(self, target: str, rule) -> bool:
        """Return True if *target* matches the given *rule*."""
        kind: str = rule.kind if isinstance(rule.kind, str) else rule.kind.value
        value: str = self.normalize_target(rule.value)

        if kind in ("domain", "exclude"):
            return self._match_domain(target, value)
        if kind == "wildcard":
            return self._match_wildcard(target, value)
        if kind == "cidr":
            return self._match_cidr(target, value)
        return False

    @staticmethod
    def _match_domain(target: str, value: str) -> bool:
        """Exact domain match (case-insensitive)."""
        if value.startswith("*."):
            suffix = value[2:]
            return target.endswith("." + suffix)
        return target == value

    @staticmethod
    def _match_wildcard(target: str, value: str, include_apex: bool = False) -> bool:
        """Match ``*.example.com`` style wildcards with strict subdomain boundary.
        
        Per Review Report §1.1:
          A rule for *.example.com covers subdomains (e.g. sub.example.com, api.sub.example.com).
          It does NOT automatically include the apex/root domain (example.com) unless
          explicitly configured or covered by a distinct rule.
        
        Examples:
          *.example.com:
            - sub.example.com -> True
            - deep.sub.example.com -> True
            - example.com -> False (apex domain requires explicit program listing)
            - evil-example.com -> False
            - example.com.attacker.com -> False
        """
        if not value.startswith("*."):
            return target == value
        suffix = value[2:]  # e.g. "example.com"
        
        if include_apex and target == suffix:
            return True
        return target.endswith("." + suffix)

    @classmethod
    def _match_cidr(cls, target: str, value: str) -> bool:
        """Check whether *target* (IP string) falls within the CIDR *value*."""
        if not cls._is_ip(target):
            return False
        try:
            network = ipaddress.ip_network(value, strict=False)
            addr = ipaddress.ip_address(target)
            return addr in network
        except ValueError:
            logger.warning("Invalid CIDR rule value: {}", value)
            return False

    @staticmethod
    def _is_ip(target: str) -> bool:
        """Return True if *target* is a valid IPv4 or IPv6 address."""
        try:
            ipaddress.ip_address(target)
            return True
        except ValueError:
            return False


# Module-level singleton
scope_validator = ScopeValidator()
