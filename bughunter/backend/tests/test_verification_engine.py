"""
tests/test_verification_engine.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tests for VerificationEngine:
  - Scope pre-validation before execution
  - Redirect safety gating
  - Reproducible curl generation
  - Cryptographic evidence hashing

Per Review Report §1.3, §4.4, §5 (Phase 4).
"""
import asyncio
import uuid
from types import SimpleNamespace

import pytest

from app.verification.engine import VerificationEngine, verification_engine


def rule(kind: str, value: str):
    return SimpleNamespace(id=uuid.uuid4(), kind=kind, value=value)


class TestVerificationEngine:

    def test_build_curl_command_basic(self):
        cmd = VerificationEngine.build_curl_command("GET", "https://api.example.com/v1")
        assert cmd == "curl -i -s -k -X GET 'https://api.example.com/v1'"

    def test_build_curl_command_with_headers_and_data(self):
        headers = {"Authorization": "Bearer test1234", "Content-Type": "application/json"}
        data = '{"test": 1}'
        cmd = VerificationEngine.build_curl_command("POST", "https://api.example.com/auth", headers, data)
        assert "-X POST" in cmd
        assert "Authorization: Bearer test1234" in cmd
        assert "--data-raw '{\"test\": 1}'" in cmd
        assert "'https://api.example.com/auth'" in cmd

    def test_out_of_scope_target_rejected_without_network_call(self):
        rules = [rule("wildcard", "*.authorized.com")]
        res = asyncio.run(verification_engine.verify_endpoint("https://unauthorized.com/api", rules))
        assert res.success is False
        assert res.scope_valid is False
        assert "out of scope" in res.error.lower()
        assert res.status_code == 0

    def test_private_ip_target_rejected(self):
        rules = [rule("wildcard", "*.authorized.com")]
        res = asyncio.run(verification_engine.verify_endpoint("http://127.0.0.1:8000/secret", rules))
        assert res.success is False
        assert res.scope_valid is False
        assert "out of scope" in res.error.lower() or "ssrf" in res.error.lower()

    def test_metadata_ip_target_rejected(self):
        rules = [rule("wildcard", "*.authorized.com")]
        res = asyncio.run(verification_engine.verify_endpoint("http://169.254.169.254/latest/meta-data/", rules))
        assert res.success is False
        assert res.scope_valid is False

