"""Deterministic Python scope validator — NO LLM involvement.

Decision logic:
1. No rules → deny
2. Exclusions first (kind=exclude) → if any match → deny (exclusions always win)
3. Positive rules (domain exact, wildcard *.example.com, CIDR for IPs)
4. No positive rule matches → deny
5. Every decision is recorded in AuditLog

IP/CIDR matching uses stdlib ``ipaddress``.
Wildcard matching supports ``*.example.com`` style patterns.
"""
from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from loguru import logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ScopeResult:
    allowed: bool
    reason: str
    matched_rule_id: UUID | None = None


class ScopeValidator:
    """Stateless, deterministic scope checker."""

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
            target = str(arg2)
        else:
            target = str(arg1)
            rules = arg2 or []
        target = target.strip().lower()

        # 1. No rules → deny
        if not rules:
            result = ScopeResult(
                allowed=False,
                reason="No scope rules defined for this program.",
            )
            logger.debug(
                "Scope DENY [no-rules] program={} target={}", program_id, target
            )
            return result

        # 2. Exclusions first (always win)
        for rule in rules:
            if rule.kind == "exclude" or (hasattr(rule.kind, 'value') and rule.kind.value == "exclude"):
                if self._matches(target, rule):
                    result = ScopeResult(
                        allowed=False,
                        reason=f"Target matches exclusion rule: {rule.value}",
                        matched_rule_id=rule.id,
                    )
                    logger.debug(
                        "Scope DENY [exclusion] program={} target={} rule={}",
                        program_id,
                        target,
                        rule.id,
                    )
                    return result

        # 3. Positive rules
        for rule in rules:
            kind_val = rule.kind if isinstance(rule.kind, str) else rule.kind.value
            if kind_val == "exclude":
                continue
            if self._matches(target, rule):
                result = ScopeResult(
                    allowed=True,
                    reason=f"Target matches rule ({kind_val}): {rule.value}",
                    matched_rule_id=rule.id,
                )
                logger.debug(
                    "Scope ALLOW program={} target={} rule={}",
                    program_id,
                    target,
                    rule.id,
                )
                return result

        # 4. No positive match → deny
        result = ScopeResult(
            allowed=False,
            reason="No matching in-scope rule found.",
        )
        logger.debug(
            "Scope DENY [no-match] program={} target={}", program_id, target
        )
        return result

    async def validate_target_with_dns(
        self,
        program_id: UUID,
        target: str,
        rules: list,
        db: "AsyncSession | None" = None,
    ) -> ScopeResult:
        """Like :meth:`validate_target` but also checks resolved IPs.

        If the initial check fails and the target looks like a hostname,
        the method resolves it and re-checks each resolved IP against CIDR rules.
        A CIDR match after DNS resolution is still a valid in-scope result.
        """
        result = self.validate_target(program_id, target, rules)
        if result.allowed:
            return result

        # Try DNS resolution for extra CIDR checks
        if not self._is_ip(target):
            try:
                infos = socket.getaddrinfo(target, None)
                resolved_ips = {info[4][0] for info in infos}
            except OSError:
                resolved_ips = set()

            for ip in resolved_ips:
                dns_result = self.validate_target(program_id, ip, rules)
                if dns_result.allowed:
                    logger.debug(
                        "Scope ALLOW [dns-resolved] program={} target={} resolved_ip={}",
                        program_id,
                        target,
                        ip,
                    )
                    return ScopeResult(
                        allowed=True,
                        reason=f"Resolved IP {ip} matches rule: {dns_result.reason}",
                        matched_rule_id=dns_result.matched_rule_id,
                    )

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _matches(self, target: str, rule) -> bool:
        """Return True if *target* matches the given *rule*."""
        kind: str = rule.kind if isinstance(rule.kind, str) else rule.kind.value
        value: str = rule.value.strip().lower()

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
        # Allow *.example.com stored under "domain" kind as well
        if value.startswith("*."):
            suffix = value[2:]
            return target == suffix or target.endswith("." + suffix)
        return target == value

    @staticmethod
    def _match_wildcard(target: str, value: str) -> bool:
        """Match ``*.example.com`` style wildcards."""
        if not value.startswith("*."):
            # Treat as exact if no wildcard prefix
            return target == value
        suffix = value[2:]  # e.g. "example.com"
        # Must end with .suffix OR equal suffix itself
        return target == suffix or target.endswith("." + suffix)

    @staticmethod
    def _match_cidr(target: str, value: str) -> bool:
        """Check whether *target* (IP string) falls within the CIDR *value*."""
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
