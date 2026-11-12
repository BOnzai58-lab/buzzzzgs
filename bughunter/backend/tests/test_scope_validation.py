"""
tests/test_scope_validation.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Comprehensive deterministic tests for ScopeValidator.

Covers:
  - Wildcard matching edge cases (§1.1)
  - Exact domain matching
  - CIDR/IP matching
  - Exclusion-first priority
  - Private IP / SSRF defense (§1.1, §4.4)
  - Redirect validation
  - URL normalization (ports, schemes, paths)
  - IDN / IPv6 edge cases

No network calls are made; all DNS tests use mock-safe known addresses.
"""
import uuid
from types import SimpleNamespace

import pytest

from app.scope.validator import ScopeValidator, scope_validator


# ── Fixtures ─────────────────────────────────────────────────────────────────

def rule(kind: str, value: str):
    return SimpleNamespace(id=uuid.uuid4(), kind=kind, value=value)


@pytest.fixture
def basic_rules():
    """Standard wildcard program with an excluded subdomain."""
    return [
        rule("wildcard", "*.target.com"),
        rule("domain", "extra.example.org"),
        rule("exclude", "admin.target.com"),
        rule("exclude", "staging.target.com"),
        rule("cidr", "198.51.100.0/24"),
    ]


@pytest.fixture
def no_rules():
    return []


# ── Normalization ─────────────────────────────────────────────────────────────

class TestNormalization:
    def test_strips_scheme_and_port(self):
        v = ScopeValidator()
        assert v.normalize_target("https://sub.target.com:8443/path") == "sub.target.com"

    def test_strips_userinfo(self):
        v = ScopeValidator()
        assert v.normalize_target("http://user:pass@target.com/") == "target.com"

    def test_bare_domain_unchanged(self):
        v = ScopeValidator()
        assert v.normalize_target("api.target.com") == "api.target.com"

    def test_wildcard_prefix_preserved(self):
        v = ScopeValidator()
        assert v.normalize_target("*.target.com") == "*.target.com"

    def test_cidr_preserved(self):
        v = ScopeValidator()
        result = v.normalize_target("198.51.100.0/24")
        assert "/" in result  # CIDR notation kept intact

    def test_empty_returns_empty(self):
        v = ScopeValidator()
        assert v.normalize_target("") == ""

    def test_idn_punycode_normalized(self):
        v = ScopeValidator()
        assert v.normalize_target("münchen.de") == "xn--mnchen-3ya.de"

    def test_url_encoded_target_normalized(self):
        v = ScopeValidator()
        assert v.normalize_target("https%3A%2F%2Fsub.target.com%3A443%2Fapi") == "sub.target.com"

    def test_trailing_dot_stripped(self):
        v = ScopeValidator()
        assert v.normalize_target("sub.target.com.") == "sub.target.com"

    def test_lowercase(self):
        v = ScopeValidator()
        assert v.normalize_target("UPPER.EXAMPLE.COM") == "upper.example.com"


# ── Wildcard Matching ─────────────────────────────────────────────────────────

class TestWildcardMatching:
    def test_subdomain_allowed(self, basic_rules):
        r = scope_validator.validate_target("api.target.com", basic_rules)
        assert r.allowed is True

    def test_deep_subdomain_allowed(self, basic_rules):
        r = scope_validator.validate_target("v2.api.target.com", basic_rules)
        assert r.allowed is True

    def test_root_domain_not_automatically_included_in_wildcard(self, basic_rules):
        """Per Review Report §1.1: *.target.com should NOT automatically include target.com."""
        r = scope_validator.validate_target("target.com", basic_rules)
        assert r.allowed is False

    def test_root_domain_allowed_when_explicitly_listed(self):
        """When program explicitly lists target.com as an exact domain rule, it is allowed."""
        rules = [rule("wildcard", "*.target.com"), rule("domain", "target.com")]
        r = scope_validator.validate_target("target.com", rules)
        assert r.allowed is True
        assert r.allowed is True

    def test_attacker_suffix_denied(self, basic_rules):
        """evil-target.com must NOT match *.target.com"""
        r = scope_validator.validate_target("evil-target.com", basic_rules)
        assert r.allowed is False

    def test_attacker_subdomain_spoof_denied(self, basic_rules):
        """target.com.attacker.com must NOT match *.target.com"""
        r = scope_validator.validate_target("target.com.attacker.com", basic_rules)
        assert r.allowed is False

    def test_url_with_scheme_and_port(self, basic_rules):
        r = scope_validator.validate_target("https://sub.target.com:8080/login?x=1", basic_rules)
        assert r.allowed is True


# ── Exact Domain Matching ─────────────────────────────────────────────────────

class TestExactDomainMatching:
    def test_exact_match(self, basic_rules):
        r = scope_validator.validate_target("extra.example.org", basic_rules)
        assert r.allowed is True

    def test_subdomain_of_exact_denied(self, basic_rules):
        r = scope_validator.validate_target("sub.extra.example.org", basic_rules)
        assert r.allowed is False

    def test_different_tld_denied(self, basic_rules):
        r = scope_validator.validate_target("extra.example.com", basic_rules)
        assert r.allowed is False


# ── Exclusions ────────────────────────────────────────────────────────────────

class TestExclusions:
    def test_excluded_subdomain_denied(self, basic_rules):
        r = scope_validator.validate_target("admin.target.com", basic_rules)
        assert r.allowed is False

    def test_excluded_takes_priority_over_wildcard(self, basic_rules):
        r = scope_validator.validate_target("staging.target.com", basic_rules)
        assert r.allowed is False

    def test_non_excluded_subdomain_allowed(self, basic_rules):
        r = scope_validator.validate_target("app.target.com", basic_rules)
        assert r.allowed is True


# ── CIDR Matching ─────────────────────────────────────────────────────────────

class TestCIDRMatching:
    def test_ip_in_cidr_allowed(self, basic_rules):
        r = scope_validator.validate_target("198.51.100.50", basic_rules)
        assert r.allowed is True

    def test_ip_outside_cidr_denied(self, basic_rules):
        r = scope_validator.validate_target("198.51.101.1", basic_rules)
        assert r.allowed is False


# ── SSRF / Private IP Defense ─────────────────────────────────────────────────

class TestSSRFDefense:
    def test_loopback_denied(self, basic_rules):
        r = scope_validator.validate_target("127.0.0.1", basic_rules)
        assert r.allowed is False

    def test_cloud_metadata_denied(self, basic_rules):
        """AWS/GCP/Azure instance metadata endpoint must always be blocked."""
        r = scope_validator.validate_target("169.254.169.254", basic_rules)
        assert r.allowed is False

    def test_rfc1918_10_denied(self, basic_rules):
        r = scope_validator.validate_target("10.0.0.1", basic_rules)
        assert r.allowed is False

    def test_rfc1918_172_denied(self, basic_rules):
        r = scope_validator.validate_target("172.16.0.1", basic_rules)
        assert r.allowed is False

    def test_rfc1918_192_denied(self, basic_rules):
        r = scope_validator.validate_target("192.168.1.100", basic_rules)
        assert r.allowed is False

    def test_private_ip_in_exclusion(self):
        """A private IP explicitly in an exclusion rule should still be blocked (exclusion wins)."""
        rules = [rule("cidr", "192.168.1.0/24"), rule("exclude", "192.168.1.1")]
        r = scope_validator.validate_target("192.168.1.1", rules)
        assert r.allowed is False

    def test_private_ip_in_explicit_cidr_rule_allowed(self):
        """If the program explicitly authorizes a private range (e.g. lab), allow it."""
        rules = [rule("cidr", "192.168.100.0/24")]
        r = scope_validator.validate_target("192.168.100.50", rules)
        assert r.allowed is True

    def test_no_rules_private_ip_denied(self):
        r = scope_validator.validate_target("10.0.0.1", [])
        assert r.allowed is False


# ── No Rules ──────────────────────────────────────────────────────────────────

class TestNoRules:
    def test_public_target_denied_with_no_rules(self, no_rules):
        r = scope_validator.validate_target("example.com", no_rules)
        assert r.allowed is False
        assert "No scope rules" in r.reason


# ── Redirect Validation ───────────────────────────────────────────────────────

class TestRedirectValidation:
    def test_in_scope_redirect_allowed(self, basic_rules):
        r = scope_validator.validate_redirect("app.target.com", "https://api.target.com/v1", basic_rules)
        assert r.allowed is True

    def test_excluded_redirect_denied(self, basic_rules):
        r = scope_validator.validate_redirect("app.target.com", "https://admin.target.com/", basic_rules)
        assert r.allowed is False

    def test_out_of_scope_redirect_denied(self, basic_rules):
        r = scope_validator.validate_redirect("app.target.com", "https://evil.com/steal", basic_rules)
        assert r.allowed is False

    def test_private_ip_redirect_denied(self, basic_rules):
        r = scope_validator.validate_redirect("app.target.com", "http://169.254.169.254/latest/meta-data/", basic_rules)
        assert r.allowed is False

    def test_empty_redirect_url_denied(self, basic_rules):
        r = scope_validator.validate_redirect("app.target.com", "", basic_rules)
        assert r.allowed is False


# ── is_reserved_or_private_ip ────────────────────────────────────────────────

class TestReservedIPCheck:
    @pytest.mark.parametrize("ip", [
        "127.0.0.1",
        "127.255.255.255",
        "10.0.0.1",
        "172.16.0.1",
        "172.31.255.255",
        "192.168.0.1",
        "169.254.169.254",
        "169.254.0.1",
        "::1",
        "fc00::1",
        "fe80::1",
    ])
    def test_private_ips_are_reserved(self, ip):
        assert ScopeValidator.is_reserved_or_private_ip(ip) is True

    @pytest.mark.parametrize("ip", [
        "8.8.8.8",
        "1.1.1.1",
        "198.51.100.1",
        "203.0.113.1",
    ])
    def test_public_ips_are_not_reserved(self, ip):
        assert ScopeValidator.is_reserved_or_private_ip(ip) is False

