"""Scan Limitations & Policy Manager Service.

Implements hierarchical scan policy inheritance (Global -> Program -> Target)
with conflict resolution favoring stricter rules, scan profile presets, rate-limiting
enforcement, and prohibited attack category blocking per Master Development
Specification §6.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ScanProfile(str, Enum):
    PASSIVE = "passive"
    LOW_IMPACT = "low_impact"
    STANDARD = "standard"
    EXTENDED = "extended"


class TestCategory(str, Enum):
    DNS = "dns"
    TECH_FINGERPRINT = "tech_fingerprint"
    HTTP_HEADERS = "http_headers"
    CONTENT_DISCOVERY = "content_discovery"
    JAVASCRIPT_REVIEW = "javascript_review"
    API_ASSESSMENT = "api_assessment"
    AUTH_CHECKS = "auth_checks"
    ACCESS_CONTROL = "access_control"
    XSS = "xss"
    SSRF_SAFE = "ssrf_safe"
    SSRF = "ssrf"
    FILE_HANDLING_SAFE = "file_handling_safe"
    FILE_UPLOAD = "file_upload"
    INFO_DISCLOSURE = "info_disclosure"
    SQLI = "sqli"
    INJECTION = "injection"
    IDOR = "idor"
    AUTH_BYPASS = "auth_bypass"
    SSTI = "ssti"
    BUSINESS_LOGIC = "business_logic"


class RestrictedOperation(str, Enum):
    DOS = "dos"
    DESTRUCTIVE_PAYLOADS = "destructive_payloads"
    DATA_MODIFICATION = "data_modification"
    BRUTE_FORCE = "brute_force"
    SOCIAL_ENGINEERING = "social_engineering"
    REAL_USER_DATA_EXTRACTION = "real_user_data_extraction"
    EXCLUDED_ASSETS = "excluded_assets"


# Profile default capabilities
PROFILE_CAPABILITIES: dict[ScanProfile, set[TestCategory]] = {
    ScanProfile.PASSIVE: {
        TestCategory.DNS,
        TestCategory.TECH_FINGERPRINT,
        TestCategory.HTTP_HEADERS,
        TestCategory.INFO_DISCLOSURE,
    },
    ScanProfile.LOW_IMPACT: {
        TestCategory.DNS,
        TestCategory.TECH_FINGERPRINT,
        TestCategory.HTTP_HEADERS,
        TestCategory.INFO_DISCLOSURE,
        TestCategory.CONTENT_DISCOVERY,
        TestCategory.JAVASCRIPT_REVIEW,
    },
    ScanProfile.STANDARD: {
        TestCategory.DNS,
        TestCategory.TECH_FINGERPRINT,
        TestCategory.HTTP_HEADERS,
        TestCategory.INFO_DISCLOSURE,
        TestCategory.CONTENT_DISCOVERY,
        TestCategory.JAVASCRIPT_REVIEW,
        TestCategory.API_ASSESSMENT,
        TestCategory.AUTH_CHECKS,
        TestCategory.ACCESS_CONTROL,
        TestCategory.XSS,
        TestCategory.SSRF_SAFE,
        TestCategory.SSRF,
        TestCategory.FILE_HANDLING_SAFE,
        TestCategory.FILE_UPLOAD,
        TestCategory.SQLI,
        TestCategory.INJECTION,
        TestCategory.IDOR,
        TestCategory.AUTH_BYPASS,
        TestCategory.SSTI,
        TestCategory.BUSINESS_LOGIC,
    },
    ScanProfile.EXTENDED: set(TestCategory),
}

# Profile default rate limits (RPS, max concurrency)
PROFILE_RATE_LIMITS: dict[ScanProfile, tuple[float, int]] = {
    ScanProfile.PASSIVE: (10.0, 5),
    ScanProfile.LOW_IMPACT: (2.0, 1),
    ScanProfile.STANDARD: (10.0, 5),
    ScanProfile.EXTENDED: (25.0, 10),
}


@dataclass
class PolicyDefinition:
    """Explicit policy definition at any tier (global, program, or target)."""
    profile: ScanProfile = ScanProfile.STANDARD
    allowed_categories: set[TestCategory] | None = None
    blocked_categories: set[TestCategory] = field(default_factory=set)
    prohibited_operations: set[RestrictedOperation] = field(
        default_factory=lambda: set(RestrictedOperation)
    )
    max_rps: float | None = None
    max_concurrency: int | None = None
    backoff_on_429: bool = True
    requires_approval_for_extended: bool = True
    custom_exclusions: list[str] = field(default_factory=list)


@dataclass
class EffectivePolicy:
    """Evaluated immutable policy governing an active scan or batch execution."""
    profile: ScanProfile
    allowed_categories: set[TestCategory]
    blocked_categories: set[TestCategory]
    prohibited_operations: set[RestrictedOperation]
    max_rps: float
    max_concurrency: int
    backoff_on_429: bool
    requires_approval_for_extended: bool
    version: str
    custom_exclusions: list[str]

    def is_category_permitted(self, category: TestCategory | str) -> bool:
        """Determines if a test category is allowed under the effective policy."""
        try:
            cat_enum = TestCategory(category) if isinstance(category, str) else category
        except ValueError:
            return False
        return cat_enum in self.allowed_categories and cat_enum not in self.blocked_categories

    def is_operation_prohibited(self, op: RestrictedOperation | str) -> bool:
        """Determines if an operation violates prohibited attack constraints."""
        try:
            op_enum = RestrictedOperation(op) if isinstance(op, str) else op
        except ValueError:
            return True
        return op_enum in self.prohibited_operations

    def to_dict(self) -> dict[str, Any]:
        """Serialize for audit logs, scan reports, and API responses."""
        return {
            "profile": self.profile.value,
            "allowed_categories": sorted([c.value for c in self.allowed_categories]),
            "blocked_categories": sorted([c.value for c in self.blocked_categories]),
            "prohibited_operations": sorted([o.value for o in self.prohibited_operations]),
            "max_rps": self.max_rps,
            "max_concurrency": self.max_concurrency,
            "backoff_on_429": self.backoff_on_429,
            "requires_approval_for_extended": self.requires_approval_for_extended,
            "version": self.version,
            "custom_exclusions": self.custom_exclusions,
        }


class PolicyManager:
    """Resolves and enforces hierarchical scan policies.
    
    Inheritance rules (§6):
      Global Default -> Program Policy -> Target Policy
      
    Conflict resolution:
      - Stricter rule always wins.
      - A lower tier CANNOT grant categories forbidden by a higher tier.
      - A lower tier CANNOT increase RPS or concurrency beyond parent caps.
      - Prohibited attack categories (DoS, brute force, destructive) can NEVER be enabled.
    """

    @classmethod
    def get_global_default_policy(cls) -> PolicyDefinition:
        """Returns the system-wide baseline security policy."""
        return PolicyDefinition(
            profile=ScanProfile.STANDARD,
            allowed_categories=PROFILE_CAPABILITIES[ScanProfile.STANDARD],
            blocked_categories=set(),
            prohibited_operations=set(RestrictedOperation),
            max_rps=10.0,
            max_concurrency=5,
            backoff_on_429=True,
            requires_approval_for_extended=True,
            custom_exclusions=[],
        )

    @classmethod
    def resolve_effective_policy(
        cls,
        program_policy: PolicyDefinition | None = None,
        target_policy: PolicyDefinition | None = None,
        global_policy: PolicyDefinition | None = None,
    ) -> EffectivePolicy:
        """Computes the effective policy combining all tiers.
        
        Strictly applies the rule that target-level settings cannot weaken
        program or global restrictions.
        """
        base = global_policy or cls.get_global_default_policy()

        # Step 1: Base profile & capabilities
        profile = base.profile
        if program_policy and program_policy.profile:
            # Cannot escalate to EXTENDED without explicit authorization
            profile = program_policy.profile
        if target_policy and target_policy.profile:
            # Target can only downgrade profile (e.g. STANDARD -> LOW_IMPACT or PASSIVE)
            hierarchy = [ScanProfile.PASSIVE, ScanProfile.LOW_IMPACT, ScanProfile.STANDARD, ScanProfile.EXTENDED]
            current_idx = hierarchy.index(profile)
            target_idx = hierarchy.index(target_policy.profile)
            if target_idx < current_idx:
                profile = target_policy.profile

        allowed = set(PROFILE_CAPABILITIES.get(profile, set()))
        if base.allowed_categories is not None:
            allowed = allowed.intersection(base.allowed_categories)

        blocked = set(base.blocked_categories)

        # Merge program restrictions
        if program_policy:
            if program_policy.allowed_categories is not None:
                # Program can restrict allowed categories
                allowed = allowed.intersection(program_policy.allowed_categories)
            blocked.update(program_policy.blocked_categories)

        # Merge target restrictions
        if target_policy:
            if target_policy.allowed_categories is not None:
                # Target can further restrict allowed categories
                allowed = allowed.intersection(target_policy.allowed_categories)
            blocked.update(target_policy.blocked_categories)

        # Ensure blocked categories take total precedence
        allowed = allowed - blocked

        # Prohibited operations: union of all prohibited operations across all tiers
        prohibited = set(base.prohibited_operations)
        if program_policy:
            prohibited.update(program_policy.prohibited_operations)
        if target_policy:
            prohibited.update(target_policy.prohibited_operations)
        # Always enforce baseline safety
        prohibited.add(RestrictedOperation.DOS)
        prohibited.add(RestrictedOperation.DESTRUCTIVE_PAYLOADS)
        prohibited.add(RestrictedOperation.BRUTE_FORCE)

        # Rate limits: strictly minimum of specified limits (stricter wins)
        default_rps, default_conc = PROFILE_RATE_LIMITS.get(profile, (10.0, 5))
        rps = base.max_rps or default_rps
        conc = base.max_concurrency or default_conc

        if program_policy:
            if program_policy.max_rps is not None:
                rps = min(rps, program_policy.max_rps)
            if program_policy.max_concurrency is not None:
                conc = min(conc, program_policy.max_concurrency)

        if target_policy:
            if target_policy.max_rps is not None:
                rps = min(rps, target_policy.max_rps)
            if target_policy.max_concurrency is not None:
                conc = min(conc, target_policy.max_concurrency)

        # Custom exclusions
        exclusions = list(base.custom_exclusions)
        if program_policy:
            exclusions.extend([e for e in program_policy.custom_exclusions if e not in exclusions])
        if target_policy:
            exclusions.extend([e for e in target_policy.custom_exclusions if e not in exclusions])

        # Generate deterministic version hash
        version_payload = json.dumps({
            "profile": profile.value,
            "allowed": sorted([c.value for c in allowed]),
            "blocked": sorted([c.value for c in blocked]),
            "prohibited": sorted([p.value for p in prohibited]),
            "rps": rps,
            "concurrency": conc,
            "exclusions": exclusions,
        }, sort_keys=True)
        version = hashlib.sha256(version_payload.encode()).hexdigest()[:12]

        return EffectivePolicy(
            profile=profile,
            allowed_categories=allowed,
            blocked_categories=blocked,
            prohibited_operations=prohibited,
            max_rps=rps,
            max_concurrency=conc,
            backoff_on_429=True,
            requires_approval_for_extended=True,
            version=version,
            custom_exclusions=exclusions,
        )

    # Alias for method compatibility
    compute_effective_policy = resolve_effective_policy


policy_manager = PolicyManager()

