"""
tests/test_evidence_and_reports.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tests for the ReportGenerator to ensure:
  - Reports are always marked DRAFT
  - No content is fabricated
  - Evidence-backed content appears when evidence is provided
  - Missing evidence is flagged explicitly
  - CVSS appears only when scanner provides it
  
Covers review §1.5, §4.4, §4.6.
"""
import hashlib
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.reports.generator import ReportGenerator


# ── Fixtures ─────────────────────────────────────────────────────────────────

def mock_finding(
    name="Open Redirect",
    category="redirect",
    severity="high",
    scanner="nuclei",
    scanner_version="v3.1.0",
    template_id="open-redirect-generic",
    matched_at="https://app.target.com/redirect?url=",
    curl_command="curl -i -s 'https://app.target.com/redirect?url=https://evil.com'",
    cvss_score=None,
    cvss_metrics=None,
):
    class FakeSeverity:
        def __init__(self, v):
            self._v = v
        def __str__(self):
            return self._v

    return SimpleNamespace(
        id=uuid.uuid4(),
        name=name,
        category=category,
        severity=FakeSeverity(severity),
        scanner=scanner,
        scanner_version=scanner_version,
        template_id=template_id,
        status="potential",
        scope_result={
            "matched_at": matched_at,
            "curl_command": curl_command,
            "extracted_results": ["https://evil.com"],
            "cvss_score": cvss_score,
            "cvss_metrics": cvss_metrics,
            "cwe": ["CWE-601"],
        },
        raw_output="{}",
    )


def mock_evidence(
    kind="tool_output",
    content="nuclei matched open-redirect",
    raw_request="GET /redirect?url=https://evil.com HTTP/1.1\r\nHost: app.target.com",
    raw_response="HTTP/1.1 302 Found\r\nLocation: https://evil.com",
    curl_command="curl -i 'https://app.target.com/redirect?url=https://evil.com'",
    human_verified=False,
):
    class FakeKind:
        def __init__(self, v):
            self.value = v
        def __str__(self):
            return self.value

    return SimpleNamespace(
        id=uuid.uuid4(),
        kind=FakeKind(kind),
        content_ref=content[:200],
        sha256=hashlib.sha256(content.encode()).hexdigest(),
        collected_at=datetime(2026, 11, 12, 10, 0, 0, tzinfo=timezone.utc),
        collected_by="nuclei",
        raw_request=raw_request,
        raw_response=raw_response,
        curl_command=curl_command,
        is_verified_by_human=human_verified,
        reproduction_steps=None,
    )


def mock_program(name="ACME Bug Bounty"):
    return SimpleNamespace(name=name)


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestReportAlwaysDraft:
    def test_report_contains_draft_warning(self):
        gen = ReportGenerator()
        md = gen.generate_markdown(mock_finding(), [], None, mock_program())
        assert "DRAFT" in md
        assert "HUMAN REVIEW REQUIRED" in md

    def test_report_contains_not_submitted_disclaimer(self):
        gen = ReportGenerator()
        md = gen.generate_markdown(mock_finding(), [], None, mock_program())
        assert "not submitted" in md.lower() or "Not submitted" in md


class TestReportWithEvidence:
    def test_report_includes_http_request(self):
        gen = ReportGenerator()
        ev = mock_evidence()
        md = gen.generate_markdown(mock_finding(), [ev], None, mock_program())
        assert "GET /redirect" in md

    def test_report_includes_http_response(self):
        gen = ReportGenerator()
        ev = mock_evidence()
        md = gen.generate_markdown(mock_finding(), [ev], None, mock_program())
        assert "302 Found" in md

    def test_report_includes_curl_command(self):
        gen = ReportGenerator()
        ev = mock_evidence()
        md = gen.generate_markdown(mock_finding(), [ev], None, mock_program())
        assert "curl" in md

    def test_report_shows_sha256(self):
        gen = ReportGenerator()
        ev = mock_evidence()
        md = gen.generate_markdown(mock_finding(), [ev], None, mock_program())
        assert ev.sha256 in md

    def test_unverified_evidence_flagged(self):
        gen = ReportGenerator()
        ev = mock_evidence(human_verified=False)
        md = gen.generate_markdown(mock_finding(), [ev], None, mock_program())
        assert "not yet verified by human" in md.lower() or "Automated" in md

    def test_human_verified_evidence_flagged(self):
        gen = ReportGenerator()
        ev = mock_evidence(human_verified=True)
        md = gen.generate_markdown(mock_finding(), [ev], None, mock_program())
        assert "Verified by human" in md


class TestReportWithoutEvidence:
    def test_no_evidence_warning_shown(self):
        gen = ReportGenerator()
        md = gen.generate_markdown(mock_finding(), [], None, mock_program())
        assert "No evidence records found" in md

    def test_no_evidence_requires_manual_capture(self):
        gen = ReportGenerator()
        md = gen.generate_markdown(mock_finding(), [], None, mock_program())
        assert "manually capture" in md.lower() or "must manually" in md.lower()


class TestReportCVSS:
    def test_cvss_shown_when_provided(self):
        gen = ReportGenerator()
        f = mock_finding(cvss_score=7.5, cvss_metrics="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N")
        md = gen.generate_markdown(f, [], None, mock_program())
        assert "7.5" in md
        assert "CVSS:3.1" in md

    def test_cvss_not_fabricated_when_absent(self):
        gen = ReportGenerator()
        f = mock_finding(cvss_score=None, cvss_metrics=None)
        md = gen.generate_markdown(f, [], None, mock_program())
        # Should NOT contain fake CVSS data
        assert "CVSS:3.1/AV:" not in md


class TestReportScopeSection:
    def test_scope_confirmation_present(self):
        gen = ReportGenerator()
        md = gen.generate_markdown(mock_finding(), [], None, mock_program())
        assert "Scope Confirmation" in md

    def test_program_name_present(self):
        gen = ReportGenerator()
        md = gen.generate_markdown(mock_finding(), [], None, mock_program("TargetCorp VDP"))
        assert "TargetCorp VDP" in md


class TestReportChecklist:
    def test_submission_checklist_present(self):
        gen = ReportGenerator()
        md = gen.generate_markdown(mock_finding(), [], None, mock_program())
        assert "Review Checklist" in md
        assert "manually reproduced" in md.lower()
        assert "in-scope" in md.lower()
