"""Adaptive Assessment Planner — Intelligent, context-driven security assessment planning.

Implements the 10-step adaptive planning cycle per Master Development Specification §9:
- Generates candidate checks based on discovered inventory (CMS, APIs, JS, Login, Uploads, Parameters).
- Rejects checks violating scope or policy with explicit justification.
- Tracks check states per §9.3 (planned, running, passed, potential, verified, skipped_by_policy,
  blocked_by_scope, unsupported, failed, inconclusive).
- Reports capability-based coverage metrics.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger
from app.services.policy_manager import (
    EffectivePolicy,
    TestCategory,
    policy_manager,
)
from app.scope.validator import ScopeValidator, scope_validator


class CheckStatus(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    PASSED = "passed"
    POTENTIAL = "potential"
    VERIFIED = "verified"
    SKIPPED_BY_POLICY = "skipped_by_policy"
    BLOCKED_BY_SCOPE = "blocked_by_scope"
    UNSUPPORTED = "unsupported"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


class CheckPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class CandidateCheck:
    """An individual assessment check proposed by the adaptive planner."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    category: TestCategory = TestCategory.INFO_DISCLOSURE
    target: str = ""
    tool_hint: str = ""
    status: CheckStatus = CheckStatus.PLANNED
    priority: CheckPriority = CheckPriority.MEDIUM
    rationale: str = ""
    evidence_trigger: str = ""  # What discovered inventory triggered this check
    parameters: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "target": self.target,
            "tool_hint": self.tool_hint,
            "status": self.status.value,
            "priority": self.priority.value,
            "rationale": self.rationale,
            "evidence_trigger": self.evidence_trigger,
            "parameters": self.parameters,
            "error_message": self.error_message,
        }


@dataclass
class AssessmentPlan:
    """The generated assessment plan with candidate checks and coverage metrics."""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    target: str = ""
    policy_version: str = ""
    checks: list[CandidateCheck] = field(default_factory=list)
    total_checks: int = 0
    planned_checks: int = 0
    skipped_checks: int = 0
    blocked_checks: int = 0
    coverage_by_category: dict[str, dict[str, int]] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "target": self.target,
            "policy_version": self.policy_version,
            "total_checks": len(self.checks),
            "planned": sum(1 for c in self.checks if c.status == CheckStatus.PLANNED),
            "skipped_by_policy": sum(1 for c in self.checks if c.status == CheckStatus.SKIPPED_BY_POLICY),
            "blocked_by_scope": sum(1 for c in self.checks if c.status == CheckStatus.BLOCKED_BY_SCOPE),
            "unsupported": sum(1 for c in self.checks if c.status == CheckStatus.UNSUPPORTED),
            "coverage_by_category": self.coverage_by_category,
        }


class AdaptiveAssessmentPlanner:
    """Analyzes discovered target inventory and generates a safe, policy-compliant assessment plan."""

    KNOWN_CMS_INDICATORS = {
        "wordpress": ("WordPress", TestCategory.TECH_FINGERPRINT, "nuclei"),
        "wp-content": ("WordPress", TestCategory.TECH_FINGERPRINT, "nuclei"),
        "wp-includes": ("WordPress", TestCategory.TECH_FINGERPRINT, "nuclei"),
        "drupal": ("Drupal", TestCategory.TECH_FINGERPRINT, "nuclei"),
        "joomla": ("Joomla", TestCategory.TECH_FINGERPRINT, "nuclei"),
        "magento": ("Magento", TestCategory.TECH_FINGERPRINT, "nuclei"),
        "shopify": ("Shopify", TestCategory.TECH_FINGERPRINT, "nuclei"),
    }

    def generate_plan(
        self,
        target: str,
        scope_rules: list,
        policy: EffectivePolicy | None = None,
        inventory: dict[str, Any] | None = None,
        available_tools: set[str] | None = None,
    ) -> AssessmentPlan:
        """Executes the planning cycle per §9.1 and returns an AssessmentPlan."""
        eff_policy = policy or policy_manager.resolve_effective_policy()
        inv = inventory or {}
        tools = available_tools or {"subfinder", "httpx", "katana", "nuclei", "dalfox", "ffuf"}

        candidates: list[CandidateCheck] = []

        # 1. Base DNS and Recon checks
        candidates.append(CandidateCheck(
            name="Passive Subdomain Discovery",
            category=TestCategory.DNS,
            target=target,
            tool_hint="subfinder",
            priority=CheckPriority.HIGH,
            rationale="Enumerate active subdomains within the authorized apex.",
            evidence_trigger="Target intake root apex",
        ))

        # 2. HTTP Probing and TLS inspection
        candidates.append(CandidateCheck(
            name="HTTP and TLS Configuration Review",
            category=TestCategory.HTTP_HEADERS,
            target=target,
            tool_hint="httpx",
            priority=CheckPriority.HIGH,
            rationale="Probe alive ports (80, 443), inspect TLS cipher suite, and verify security headers (HSTS, CSP).",
            evidence_trigger="Target host resolution",
        ))

        # 3. Analyze discovered inventory (tech stack, endpoints, parameters)
        tech_list = inv.get("tech", [])
        endpoints = inv.get("endpoints", [])
        urls = inv.get("urls", [])
        headers = inv.get("headers", {})
        server_header = headers.get("server", "").lower()

        # CMS-specific checks
        cms_found = None
        for indicator, (cms_name, cat, tool) in self.KNOWN_CMS_INDICATORS.items():
            if any(indicator in str(u).lower() for u in urls + endpoints) or any(indicator in t.lower() for t in tech_list):
                cms_found = cms_name
                candidates.append(CandidateCheck(
                    name=f"{cms_name} Security & Exposure Configuration",
                    category=TestCategory.TECH_FINGERPRINT,
                    target=target,
                    tool_hint=tool,
                    priority=CheckPriority.HIGH,
                    rationale=f"Target inventory reveals {cms_name}; assess public version disclosure and exposed admin endpoints.",
                    evidence_trigger=f"CMS indicator matched: {cms_name}",
                    parameters={"cms": cms_name},
                ))
                break

        # API-specific checks
        api_endpoints = [
            e for e in (endpoints + urls)
            if any(p in str(e).lower() for p in ["/api/", "/v1/", "/v2/", "/graphql", "/swagger", "/openapi"])
        ]
        if api_endpoints:
            candidates.append(CandidateCheck(
                name="API Route Inventory and Access Control",
                category=TestCategory.API_ASSESSMENT,
                target=api_endpoints[0],
                tool_hint="nuclei",
                priority=CheckPriority.HIGH,
                rationale="API routes detected in discovered URLs; verify authentication enforcement and schema exposure.",
                evidence_trigger=f"API path pattern matched: {len(api_endpoints)} endpoints found",
                parameters={"sample_endpoints": api_endpoints[:5]},
            ))

        # Client-side JavaScript checks
        js_endpoints = [e for e in (endpoints + urls) if str(e).lower().endswith(".js") or ".js?" in str(e).lower()]
        if js_endpoints:
            candidates.append(CandidateCheck(
                name="Client-Side JavaScript Route & Secret Inspection",
                category=TestCategory.JAVASCRIPT_REVIEW,
                target=js_endpoints[0],
                tool_hint="katana",
                priority=CheckPriority.MEDIUM,
                rationale="Client-side JavaScript files detected; inspect script contents for route references and endpoint paths.",
                evidence_trigger=f"{len(js_endpoints)} JavaScript bundle(s) discovered",
                parameters={"js_targets": js_endpoints[:5]},
            ))

        # Authentication / Session checks
        auth_endpoints = [
            e for e in (endpoints + urls)
            if any(p in str(e).lower() for p in ["/login", "/signin", "/auth", "/session", "/oauth"])
        ]
        if auth_endpoints:
            candidates.append(CandidateCheck(
                name="Authentication Endpoint Session & Header Validation",
                category=TestCategory.AUTH_CHECKS,
                target=auth_endpoints[0],
                tool_hint="httpx",
                priority=CheckPriority.HIGH,
                rationale="Login/authentication interface detected; inspect cookie flags (Secure, HttpOnly, SameSite) and anti-CSRF protections.",
                evidence_trigger=f"Authentication route matched: {auth_endpoints[0]}",
            ))

        # File Upload checks
        upload_endpoints = [
            e for e in (endpoints + urls)
            if any(p in str(e).lower() for p in ["/upload", "/attachment", "/file-upload", "/media/upload"])
        ]
        if upload_endpoints:
            candidates.append(CandidateCheck(
                name="Non-Destructive File Upload Handling Review",
                category=TestCategory.FILE_HANDLING_SAFE,
                target=upload_endpoints[0],
                tool_hint="nuclei",
                priority=CheckPriority.MEDIUM,
                rationale="Upload endpoint detected; perform safe validation checks for MIME-type restrictions and file extension handling.",
                evidence_trigger=f"Upload route matched: {upload_endpoints[0]}",
            ))

        # Parameter-based Reflected XSS checks
        param_endpoints = [e for e in (endpoints + urls) if "?" in str(e) and "=" in str(e)]
        if param_endpoints:
            candidates.append(CandidateCheck(
                name="Safe Reflected Input Validation & Context Escaping",
                category=TestCategory.XSS,
                target=param_endpoints[0],
                tool_hint="dalfox",
                priority=CheckPriority.MEDIUM,
                rationale="Query parameters identified in crawled endpoints; test safe benign characters for context escaping.",
                evidence_trigger=f"{len(param_endpoints)} parameterized endpoint(s) discovered",
                parameters={"sample_param_url": param_endpoints[0]},
            ))

        # Crawling and endpoint discovery
        candidates.append(CandidateCheck(
            name="Authorized Crawl & Endpoint Discovery",
            category=TestCategory.CONTENT_DISCOVERY,
            target=target,
            tool_hint="katana",
            priority=CheckPriority.MEDIUM,
            rationale="Crawl authorized hyperlinks within the target domain to build attack surface inventory.",
            evidence_trigger="Target host online confirmation",
        ))

        # 4. Filter candidates through Scope and Policy Engine (§9.1 Step 5)
        validated_checks: list[CandidateCheck] = []
        coverage_map: dict[str, dict[str, int]] = {}

        for check in candidates:
            cat_name = check.category.value
            if cat_name not in coverage_map:
                coverage_map[cat_name] = {"total": 0, "planned": 0, "skipped": 0, "blocked": 0}
            coverage_map[cat_name]["total"] += 1

            # Check 1: Tool installed / supported
            if check.tool_hint and check.tool_hint not in tools:
                check.status = CheckStatus.UNSUPPORTED
                check.error_message = f"Required tool '{check.tool_hint}' is not installed or available on this platform."
                coverage_map[cat_name]["skipped"] += 1
                validated_checks.append(check)
                continue

            # Check 2: Policy permission
            if not eff_policy.is_category_permitted(check.category):
                check.status = CheckStatus.SKIPPED_BY_POLICY
                check.error_message = (
                    f"Category '{check.category.value}' is not permitted under effective policy profile '{eff_policy.profile.value}'."
                )
                coverage_map[cat_name]["skipped"] += 1
                validated_checks.append(check)
                continue

            # Check 3: Scope validation (Deterministic pure Python)
            sr = scope_validator.validate_target(check.target, scope_rules)
            if not sr.allowed:
                check.status = CheckStatus.BLOCKED_BY_SCOPE
                check.error_message = f"Target '{check.target}' is outside authorized scope: {sr.reason}."
                coverage_map[cat_name]["blocked"] += 1
                validated_checks.append(check)
                continue

            # Passed all filters -> PLANNED
            check.status = CheckStatus.PLANNED
            coverage_map[cat_name]["planned"] += 1
            validated_checks.append(check)

        # 5. Rank remaining checks by priority
        priority_order = {CheckPriority.HIGH: 0, CheckPriority.MEDIUM: 1, CheckPriority.LOW: 2}
        validated_checks.sort(key=lambda c: (
            0 if c.status == CheckStatus.PLANNED else 1,
            priority_order.get(c.priority, 1)
        ))

        return AssessmentPlan(
            target=target,
            policy_version=eff_policy.version,
            checks=validated_checks,
            total_checks=len(validated_checks),
            planned_checks=sum(1 for c in validated_checks if c.status == CheckStatus.PLANNED),
            skipped_checks=sum(1 for c in validated_checks if c.status == CheckStatus.SKIPPED_BY_POLICY),
            blocked_checks=sum(1 for c in validated_checks if c.status == CheckStatus.BLOCKED_BY_SCOPE),
            coverage_by_category=coverage_map,
        )


adaptive_planner = AdaptiveAssessmentPlanner()

