"""
BugHunter AI — Automated Test Suite Runner.
Discovers and executes all unit and integration tests.
Per Review Report §2.4, §6.
"""
import asyncio
import hashlib
import sys
import time
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

# Ensure app is in sys.path
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.scope.validator import ScopeValidator, scope_validator
from app.reports.generator import ReportGenerator
from app.verification.engine import VerificationEngine, verification_engine
from app.core.process_tracker import ProcessTracker

passed = 0
failed = 0
errors = []


def check(name: str, condition: bool):
    global passed, failed, errors
    if condition:
        passed += 1
        print(f"  \033[32m✔\033[0m {name}")
    else:
        failed += 1
        errors.append(name)
        print(f"  \033[31m✘ FAIL:\033[0m {name}")


def rule(kind: str, value: str):
    return SimpleNamespace(id=uuid.uuid4(), kind=kind, value=value)


def main():
    print("=" * 65)
    print("      BugHunter AI — Automated Test Suite Execution")
    print("=" * 65)

    # ─────────────────────────────────────────────────────────────────
    print("\n[Suite 1] Scope Validator & SSRF Protections (§1.1)")
    # ─────────────────────────────────────────────────────────────────
    v = ScopeValidator()
    check("Normalize strips scheme and port", v.normalize_target("https://sub.target.com:8443/path") == "sub.target.com")
    check("Normalize IDN punycode (münchen.de)", v.normalize_target("münchen.de") == "xn--mnchen-3ya.de")
    check("Normalize URL-encoded string", v.normalize_target("https%3A%2F%2Fsub.target.com%3A443%2Fapi") == "sub.target.com")
    check("Normalize trailing FQDN dot", v.normalize_target("sub.target.com.") == "sub.target.com")
    check("Normalize preserves CIDR notation", "/" in v.normalize_target("198.51.100.0/24"))
    check("Normalize strips userinfo", v.normalize_target("http://admin:pass@target.com") == "target.com")

    basic_rules = [
        rule("wildcard", "*.target.com"),
        rule("domain", "extra.example.org"),
        rule("exclude", "admin.target.com"),
        rule("exclude", "staging.target.com"),
        rule("cidr", "198.51.100.0/24"),
    ]

    check("Wildcard subdomain allowed (api.target.com)", scope_validator.validate_target("api.target.com", basic_rules).allowed is True)
    check("Wildcard deep subdomain allowed (v2.api.target.com)", scope_validator.validate_target("v2.api.target.com", basic_rules).allowed is True)
    check("Wildcard root apex NOT auto-included (*.target.com != target.com)", scope_validator.validate_target("target.com", basic_rules).allowed is False)
    check("Wildcard root allowed when explicitly listed", scope_validator.validate_target("target.com", [rule("wildcard", "*.target.com"), rule("domain", "target.com")]).allowed is True)
    check("Attacker prefix spoof denied (evil-target.com)", scope_validator.validate_target("evil-target.com", basic_rules).allowed is False)
    check("Attacker subdomain spoof denied (target.com.attacker.com)", scope_validator.validate_target("target.com.attacker.com", basic_rules).allowed is False)
    check("Excluded subdomain denied (admin.target.com)", scope_validator.validate_target("admin.target.com", basic_rules).allowed is False)
    check("Exclusion priority over wildcard (staging.target.com)", scope_validator.validate_target("staging.target.com", basic_rules).allowed is False)
    check("IP in CIDR allowed (198.51.100.50)", scope_validator.validate_target("198.51.100.50", basic_rules).allowed is True)
    check("IP outside CIDR denied (198.51.101.1)", scope_validator.validate_target("198.51.101.1", basic_rules).allowed is False)

    # SSRF / Reserved IP checks
    check("Loopback blocked (127.0.0.1)", scope_validator.validate_target("127.0.0.1", basic_rules).allowed is False)
    check("Cloud metadata blocked (169.254.169.254)", scope_validator.validate_target("169.254.169.254", basic_rules).allowed is False)
    check("RFC1918 10.x blocked (10.0.0.1)", scope_validator.validate_target("10.0.0.1", basic_rules).allowed is False)
    check("RFC1918 172.16.x blocked (172.16.0.1)", scope_validator.validate_target("172.16.0.1", basic_rules).allowed is False)
    check("RFC1918 192.168.x blocked (192.168.1.1)", scope_validator.validate_target("192.168.1.1", basic_rules).allowed is False)
    check("IPv6 loopback blocked (::1)", scope_validator.validate_target("::1", basic_rules).allowed is False)
    check("No rules always denies", scope_validator.validate_target("example.com", []).allowed is False)

    # Redirect validation
    check("In-scope redirect allowed", scope_validator.validate_redirect("app.target.com", "https://api.target.com/v1", basic_rules).allowed is True)
    check("Out-of-scope redirect denied", scope_validator.validate_redirect("app.target.com", "https://evil.com/leak", basic_rules).allowed is False)
    check("Redirect to cloud metadata denied (SSRF)", scope_validator.validate_redirect("app.target.com", "http://169.254.169.254/meta", basic_rules).allowed is False)
    check("Redirect to excluded target denied", scope_validator.validate_redirect("app.target.com", "https://admin.target.com/admin", basic_rules).allowed is False)
    check("Empty redirect URL denied", scope_validator.validate_redirect("app.target.com", "", basic_rules).allowed is False)

    # ─────────────────────────────────────────────────────────────────
    print("\n[Suite 2] Process Tracker & Worker Cancellation (§1.2)")
    # ─────────────────────────────────────────────────────────────────
    test_id = str(uuid.uuid4())
    cmd = ["cmd", "/c", "echo ok"] if sys.platform == "win32" else ["echo", "ok"]
    exit_code, stdout, _ = ProcessTracker.run_cancellable(cmd, test_id, timeout=10)
    check("ProcessTracker runs command successfully", exit_code == 0)
    check("ProcessTracker unregisters on complete", test_id not in ProcessTracker._ACTIVE_PROCESSES if hasattr(ProcessTracker, "_ACTIVE_PROCESSES") else True)
    check("Terminating nonexistent task returns False", ProcessTracker.terminate_process(str(uuid.uuid4())) is False)

    # ─────────────────────────────────────────────────────────────────
    print("\n[Suite 3] Verification Engine & Reproducible Requests (§1.3, §4.4)")
    # ─────────────────────────────────────────────────────────────────
    headers = {"Authorization": "Bearer test1234", "Content-Type": "application/json"}
    curl_cmd = VerificationEngine.build_curl_command("POST", "https://api.example.com/auth", headers, '{"test": 1}')
    check("curl includes method (-X POST)", "-X POST" in curl_cmd)
    check("curl includes headers", "Authorization: Bearer test1234" in curl_cmd)
    check("curl includes data-raw", "--data-raw" in curl_cmd)
    check("curl includes target url", "'https://api.example.com/auth'" in curl_cmd)

    res_oob = asyncio.run(verification_engine.verify_endpoint("https://unauthorized.com/api", basic_rules))
    check("VerificationEngine rejects out-of-scope without outbound request", res_oob.success is False and res_oob.scope_valid is False)

    res_meta = asyncio.run(verification_engine.verify_endpoint("http://169.254.169.254/latest/meta-data/", basic_rules))
    check("VerificationEngine rejects SSRF metadata targets", res_meta.success is False and res_meta.scope_valid is False)

    # ─────────────────────────────────────────────────────────────────
    print("\n[Suite 4] Report Generator & Evidence Quality (§1.5, §4.6)")
    # ─────────────────────────────────────────────────────────────────
    class FakeSev:
        def __str__(self): return "high"

    finding = SimpleNamespace(
        id=uuid.uuid4(), name="Open Redirect Vulnerability", category="redirect",
        severity=FakeSev(), scanner="nuclei", scanner_version="v3.3.7",
        template_id="open-redirect-generic", status="potential",
        scope_result={
            "matched_at": "https://sub.target.com/redirect?url=",
            "curl_command": "curl -i -s 'https://sub.target.com/redirect?url=https://evil.com'",
            "extracted_results": ["https://evil.com"],
            "cvss_score": 7.4,
            "cvss_metrics": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
            "cwe": ["CWE-601"],
        },
        raw_output="{}",
    )

    ev = SimpleNamespace(
        id=uuid.uuid4(),
        kind=SimpleNamespace(value="request"),
        content_ref="HTTP Request Evidence",
        sha256=hashlib.sha256(b"request_body").hexdigest(),
        collected_at=datetime(2026, 11, 12, 10, 0, 0, tzinfo=timezone.utc),
        collected_by="nuclei",
        raw_request="GET /redirect?url=https://evil.com HTTP/1.1\r\nHost: sub.target.com",
        raw_response="HTTP/1.1 302 Found\r\nLocation: https://evil.com",
        curl_command="curl -i 'https://sub.target.com/redirect?url=https://evil.com'",
        is_verified_by_human=True,
        reproduction_steps=None,
    )

    prog = SimpleNamespace(name="ACME Security Program")
    gen = ReportGenerator()
    md = gen.generate_markdown(finding, [ev], None, prog)

    check("Report prominently displays DRAFT warning", "DRAFT" in md and "HUMAN REVIEW REQUIRED" in md)
    check("Report includes captured HTTP request", "GET /redirect" in md)
    check("Report includes captured HTTP response", "302 Found" in md)
    check("Report includes SHA-256 evidence hash", hashlib.sha256(b"request_body").hexdigest() in md)
    check("Report displays CVSS score from scanner", "7.4" in md)
    check("Report displays CVSS vector string", "CVSS:3.1/AV:N" in md)
    check("Report includes manual submission checklist", "Review Checklist" in md)
    check("Report includes scope confirmation section", "Scope Confirmation" in md)

    md_empty = gen.generate_markdown(finding, [], None, prog)
    check("Report without evidence explicitly flags missing evidence", "No evidence records found" in md_empty)

    # ─────────────────────────────────────────────────────────────────
    print("\n[Suite 5] Auth Security & Privilege Escalation Defense (§2.2)")
    # ─────────────────────────────────────────────────────────────────
    from app.schemas.user import UserCreate as UserCreateSchema
    # Check that UserCreate schema does not contain 'role' field
    check("UserCreate schema excludes 'role' field to prevent privilege escalation", "role" not in UserCreateSchema.model_fields)

    # ─────────────────────────────────────────────────────────────────
    print("\n[Suite 6] Batch Execution Integrity & Real Probing (§2.1)")
    # ─────────────────────────────────────────────────────────────────
    import inspect
    from app.workers.batch_executor import execute_assessment_job
    source = inspect.getsource(execute_assessment_job)
    check("Batch executor has no hardcoded status_code=200", "status_code=200" not in source)
    check("Batch executor has no hardcoded Cloudflare/Nginx tech array", 'tech=["Nginx", "Cloudflare", "HTTP/2"]' not in source)
    check("Batch executor uses verification_engine for real probing", "verification_engine.verify_endpoint" in source)
    check("Batch executor uses process_tracker for cancellable tool execution", "process_tracker.run_cancellable" in source)

    # ─────────────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print(f"Results: \033[32m{passed} passed\033[0m, \033[31m{failed} failed\033[0m")
    print("=" * 65)

    if failed > 0:
        print("\nFailed checks:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("\n\033[32m✔ All automated tests PASSED successfully!\033[0m\n")
        sys.exit(0)


if __name__ == "__main__":
    main()

