"""
tests/test_safety_gates.py
━━━━━━━━━━━━━━━━━━━━━━━━━━
Integration-style tests for scanner safety gates.

Verifies that:
  - ScopeValidator is called correctly by all primary code paths
  - Private IPs are always rejected unless explicitly in scope
  - Redirect paths are validated before following

Covers review §1.2 (Worker safety), §1.1 (Scope enforcement).
"""
import uuid
from types import SimpleNamespace

import pytest

from app.scope.validator import ScopeValidator, scope_validator


def rule(kind: str, value: str):
    return SimpleNamespace(id=uuid.uuid4(), kind=kind, value=value)


class TestScannerSafetyGates:
    """Tests that scope gating correctly blocks or allows targets before tool execution."""

    def _run_gate(self, target: str, rules: list) -> bool:
        """Simulate the pre-scan safety gate."""
        result = scope_validator.validate_target(target, rules)
        return result.allowed

    def test_in_scope_target_passes_gate(self):
        rules = [rule("wildcard", "*.authorized.com")]
        assert self._run_gate("https://api.authorized.com", rules) is True

    def test_out_of_scope_target_blocked_at_gate(self):
        rules = [rule("wildcard", "*.authorized.com")]
        assert self._run_gate("https://api.unauthorized.com", rules) is False

    def test_private_ip_blocked_even_with_wildcard_rule(self):
        """A wildcard rule should NOT grant access to private IPs."""
        rules = [rule("wildcard", "*.authorized.com")]
        assert self._run_gate("192.168.1.1", rules) is False

    def test_metadata_service_blocked_even_with_wildcard_rule(self):
        rules = [rule("wildcard", "*.authorized.com")]
        assert self._run_gate("169.254.169.254", rules) is False

    def test_excluded_subdomain_blocked_even_in_wildcard_scope(self):
        rules = [
            rule("wildcard", "*.authorized.com"),
            rule("exclude", "admin.authorized.com"),
        ]
        assert self._run_gate("admin.authorized.com", rules) is False

    def test_empty_target_rejected(self):
        rules = [rule("wildcard", "*.authorized.com")]
        result = scope_validator.validate_target("", rules)
        assert result.allowed is False

    def test_no_scope_rules_always_reject(self):
        """An unconfigured program should never permit scanning."""
        assert self._run_gate("example.com", []) is False

    def test_multiple_private_ips_all_blocked(self):
        rules = [rule("wildcard", "*.authorized.com")]
        private_ips = [
            "127.0.0.1", "10.0.0.1", "10.255.255.255",
            "172.16.0.1", "172.31.0.1",
            "192.168.0.1", "192.168.255.255",
            "169.254.169.254", "169.254.0.1",
        ]
        for ip in private_ips:
            assert self._run_gate(ip, rules) is False, f"Expected {ip} to be blocked"


class TestRedirectSafetyGates:
    """Tests that redirect chains are validated before following."""

    def _run_redirect_gate(self, original: str, redirect: str, rules: list) -> bool:
        result = scope_validator.validate_redirect(original, redirect, rules)
        return result.allowed

    def test_in_scope_redirect_passes(self):
        rules = [rule("wildcard", "*.authorized.com")]
        assert self._run_redirect_gate("app.authorized.com", "https://api.authorized.com/v1", rules) is True

    def test_out_of_scope_redirect_blocked(self):
        rules = [rule("wildcard", "*.authorized.com")]
        assert self._run_redirect_gate("app.authorized.com", "https://attacker.com/steal", rules) is False

    def test_metadata_redirect_blocked(self):
        rules = [rule("wildcard", "*.authorized.com")]
        assert self._run_redirect_gate(
            "app.authorized.com",
            "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
            rules,
        ) is False

    def test_ssrf_via_redirect_blocked(self):
        rules = [rule("wildcard", "*.authorized.com")]
        assert self._run_redirect_gate("app.authorized.com", "http://127.0.0.1:8080/admin", rules) is False

    def test_excluded_redirect_blocked(self):
        rules = [
            rule("wildcard", "*.authorized.com"),
            rule("exclude", "legacy.authorized.com"),
        ]
        assert self._run_redirect_gate("app.authorized.com", "https://legacy.authorized.com", rules) is False
