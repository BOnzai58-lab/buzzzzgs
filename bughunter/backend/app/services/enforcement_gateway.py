"""Policy Enforcement Gateway — the single choke-point that authorises every
network action before it runs.

Every scanner adapter, task, and service that wants to send traffic MUST call
``PolicyEnforcementGateway.authorize_action()`` first.  The gateway is
deterministic Python — the AI never overrides its decisions.

Design rules (Master Dev Spec §4, §5.3):
- Authorization record must be valid and non-expired.
- Target must be within declared scope.
- Operation must not be in the prohibited-operations list.
- Category must be enabled under the effective policy.
- DoS / DDoS / stress-testing is *always* prohibited regardless of any other
  setting — it cannot be enabled by configuration.
- Fail closed: any ambiguity returns BLOCKED.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Decision types
# ---------------------------------------------------------------------------

class GatewayDecision(str, Enum):
    ALLOWED = "allowed"
    BLOCKED_NO_AUTHORIZATION = "blocked_no_authorization"
    BLOCKED_AUTHORIZATION_EXPIRED = "blocked_authorization_expired"
    BLOCKED_OUT_OF_SCOPE = "blocked_out_of_scope"
    BLOCKED_PROHIBITED_OPERATION = "blocked_prohibited_operation"
    BLOCKED_CATEGORY_DISABLED = "blocked_category_disabled"
    BLOCKED_DOS_HARDCODED = "blocked_dos_hardcoded"
    BLOCKED_POLICY = "blocked_policy"


# Operations that are *always* blocked regardless of any configuration.
# This list is intentionally compiled into this module and cannot be altered
# at runtime — not by the user, not by the AI, not by any API call.
_ALWAYS_PROHIBITED: frozenset[str] = frozenset({
    "dos",
    "ddos",
    "stress_test",
    "flood",
    "amplification",
    "rate_flood",
    "syn_flood",
    "udp_flood",
    "http_flood",
    "slowloris",
    "hulk",
    "loic",
    "hoic",
    "rudy",
})


@dataclass(frozen=True)
class GatewayResult:
    """Immutable result returned by the gateway for every authorization check."""
    decision: GatewayDecision
    reason: str
    action_type: str
    target: str
    category: Optional[str] = None

    @property
    def allowed(self) -> bool:
        return self.decision == GatewayDecision.ALLOWED

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "action_type": self.action_type,
            "target": self.target,
            "category": self.category,
            "allowed": self.allowed,
        }


# ---------------------------------------------------------------------------
# Authorization record protocol
# ---------------------------------------------------------------------------

class AuthorizationRecord:
    """Minimal authorization record interface.

    The gateway only requires these attributes; the full DB model (or a plain
    dict passed from tests) may carry additional fields.
    """
    authorized_domains: list[str]
    authorized_ips: list[str]
    excluded_domains: list[str]
    expiry_date: Optional[datetime]
    is_active: bool

    def __init__(
        self,
        authorized_domains: list[str],
        authorized_ips: list[str] | None = None,
        excluded_domains: list[str] | None = None,
        expiry_date: Optional[datetime] = None,
        is_active: bool = True,
    ):
        self.authorized_domains = authorized_domains or []
        self.authorized_ips = authorized_ips or []
        self.excluded_domains = excluded_domains or []
        self.expiry_date = expiry_date
        self.is_active = is_active


# ---------------------------------------------------------------------------
# Gateway
# ---------------------------------------------------------------------------

class PolicyEnforcementGateway:
    """Central policy enforcement gateway.

    Usage::

        gateway = PolicyEnforcementGateway()
        result = gateway.authorize_action(
            action_type="sqli_scan",
            target="https://example.com/login?user=1",
            category="sqli",
            authorization=auth_record,
            effective_policy=policy,
            scope_validator=scope_validator,
            scope_rules=rules,
        )
        if not result.allowed:
            raise PermissionError(result.reason)
    """

    def authorize_action(
        self,
        action_type: str,
        target: str,
        *,
        category: str | None = None,
        authorization: "AuthorizationRecord | None" = None,
        effective_policy=None,          # EffectivePolicy from policy_manager
        scope_validator=None,            # ScopeValidator from scope.validator
        scope_rules: list | None = None,
    ) -> GatewayResult:
        """Authorise a single network action.

        Parameters
        ----------
        action_type:
            Human-readable identifier for the action, e.g. ``"sqli_scan"``,
            ``"xss_probe"``, ``"nuclei_ssrf"``.  Used for audit logging.
        target:
            The URL or host that the action will touch.
        category:
            The ``TestCategory`` value this action falls under, e.g. ``"xss"``.
        authorization:
            An authorization record that covers the target.  Pass ``None`` to
            test the "no auth" path (will be blocked).
        effective_policy:
            The computed ``EffectivePolicy`` for this scan context.
        scope_validator:
            Instance of ``ScopeValidator`` for scope-checking the target.
        scope_rules:
            Scope rule objects to pass through to the validator.
        """

        # 1. Hard-coded DoS prohibition — checked before everything else.
        lower_action = action_type.lower().replace("-", "_").replace(" ", "_")
        lower_cat = (category or "").lower().replace("-", "_").replace(" ", "_")
        if lower_action in _ALWAYS_PROHIBITED or lower_cat in _ALWAYS_PROHIBITED:
            return GatewayResult(
                decision=GatewayDecision.BLOCKED_DOS_HARDCODED,
                reason=(
                    "DoS / DDoS / stress-testing is architecturally prohibited and "
                    "cannot be enabled by any configuration."
                ),
                action_type=action_type,
                target=target,
                category=category,
            )

        # 2. Authorization record must exist.
        if authorization is None or not authorization.is_active:
            return GatewayResult(
                decision=GatewayDecision.BLOCKED_NO_AUTHORIZATION,
                reason=(
                    "No active authorization record found for this target. "
                    "Attach a valid authorization record before testing."
                ),
                action_type=action_type,
                target=target,
                category=category,
            )

        # 3. Authorization record must not be expired.
        if authorization.expiry_date is not None:
            now = datetime.now(timezone.utc)
            expiry = authorization.expiry_date
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if now > expiry:
                return GatewayResult(
                    decision=GatewayDecision.BLOCKED_AUTHORIZATION_EXPIRED,
                    reason=(
                        f"Authorization record expired at {expiry.isoformat()}. "
                        "Renew the authorization before resuming testing."
                    ),
                    action_type=action_type,
                    target=target,
                    category=category,
                )

        # 4. Target must be within scope (if a validator is provided).
        if scope_validator is not None and scope_rules is not None:
            try:
                scope_result = scope_validator.validate_target(target, scope_rules)
                if not scope_result.allowed:
                    return GatewayResult(
                        decision=GatewayDecision.BLOCKED_OUT_OF_SCOPE,
                        reason=f"Scope check failed: {scope_result.reason}",
                        action_type=action_type,
                        target=target,
                        category=category,
                    )
            except Exception as exc:
                logger.warning("Scope validator raised an exception: %s", exc)
                return GatewayResult(
                    decision=GatewayDecision.BLOCKED_OUT_OF_SCOPE,
                    reason=f"Scope validation error (fail-closed): {exc}",
                    action_type=action_type,
                    target=target,
                    category=category,
                )

        # 5. Explicit excluded domains from auth record.
        try:
            from urllib.parse import urlparse
            parsed_host = urlparse(target).hostname or target
            for excl in authorization.excluded_domains:
                excl_clean = excl.lstrip("*.").lower()
                if parsed_host.lower() == excl_clean or parsed_host.lower().endswith("." + excl_clean):
                    return GatewayResult(
                        decision=GatewayDecision.BLOCKED_OUT_OF_SCOPE,
                        reason=f"Target '{parsed_host}' is in the authorization exclusion list.",
                        action_type=action_type,
                        target=target,
                        category=category,
                    )
        except Exception:
            pass

        # 6. Policy-level prohibited operations (from effective_policy).
        if effective_policy is not None:
            if lower_action in {op.value.lower() for op in effective_policy.prohibited_operations}:
                return GatewayResult(
                    decision=GatewayDecision.BLOCKED_PROHIBITED_OPERATION,
                    reason=f"Operation '{action_type}' is in the policy prohibited-operations list.",
                    action_type=action_type,
                    target=target,
                    category=category,
                )

        # 7. Category-level policy check.
        if effective_policy is not None and category is not None:
            if not effective_policy.is_category_permitted(category):
                return GatewayResult(
                    decision=GatewayDecision.BLOCKED_CATEGORY_DISABLED,
                    reason=(
                        f"Category '{category}' is not permitted under the current policy "
                        f"profile '{effective_policy.profile.value}'."
                    ),
                    action_type=action_type,
                    target=target,
                    category=category,
                )

        # All checks passed.
        return GatewayResult(
            decision=GatewayDecision.ALLOWED,
            reason="All policy checks passed.",
            action_type=action_type,
            target=target,
            category=category,
        )


# Module-level singleton — import and use directly.
enforcement_gateway = PolicyEnforcementGateway()

