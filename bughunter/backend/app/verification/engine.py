"""Verification Engine — Non-destructive target verification.

Implements safe, evidence-grounded verification of potential findings
with scope re-checking, redirect validation, and cryptographic hashing.
Per Review Report §1.3, §4.4, §5 (Phase 4).
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx
from loguru import logger

from app.scope.validator import ScopeValidator, scope_validator


@dataclass
class VerificationResult:
    success: bool
    status_code: int
    url: str
    request_headers: dict[str, str]
    response_headers: dict[str, str]
    raw_request: str
    raw_response: str
    curl_command: str
    request_sha256: str
    response_sha256: str
    duration_ms: float
    error: str | None = None
    scope_valid: bool = True


class VerificationEngine:
    """Non-destructive HTTP verification engine with strict redirect and scope gating."""

    def __init__(self, timeout: float = 10.0, user_agent: str = "BugHunter-AI-Verifier/1.0"):
        self.timeout = timeout
        self.user_agent = user_agent

    async def verify_endpoint(
        self,
        url: str,
        rules: list,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        data: str | None = None,
        max_redirects: int = 3,
        verify_tls: bool = True,
    ) -> VerificationResult:
        """Execute a safe, non-destructive verification request against *url*.
        
        Strictly revalidates scope at each hop and blocks SSRF / out-of-scope redirects.
        TLS certificate verification is enabled by default (§2.4).
        """
        # 1. Initial scope check
        sr = scope_validator.validate_target(url, rules)
        if not sr.allowed:
            return VerificationResult(
                success=False,
                status_code=0,
                url=url,
                request_headers={},
                response_headers={},
                raw_request="",
                raw_response="",
                curl_command=self.build_curl_command(method, url, headers, data),
                request_sha256="",
                response_sha256="",
                duration_ms=0.0,
                error=f"Initial target out of scope: {sr.reason}",
                scope_valid=False,
            )

        req_headers = {"User-Agent": self.user_agent}
        if headers:
            req_headers.update(headers)

        curl_cmd = self.build_curl_command(method, url, req_headers, data)
        raw_req_lines = [f"{method} {url} HTTP/1.1"]
        for k, v in req_headers.items():
            raw_req_lines.append(f"{k}: {v}")
        if data:
            raw_req_lines += ["", data]
        raw_req = "\n".join(raw_req_lines)
        req_sha256 = hashlib.sha256(raw_req.encode()).hexdigest()

        start_time = time.monotonic()

        current_url = url
        redirect_count = 0

        # Create custom client without auto-following redirects so we validate each hop
        # TLS certificate verification enabled by default (§2.4)
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=self.timeout,
            verify=verify_tls,
        ) as client:
            try:
                while True:
                    resp = await client.request(
                        method=method,
                        url=current_url,
                        headers=req_headers,
                        content=data.encode() if data else None,
                    )

                    # Check for redirect
                    if resp.is_redirect and "location" in resp.headers and redirect_count < max_redirects:
                        loc = resp.headers["location"]
                        # Resolve relative redirect URLs
                        if loc.startswith("/"):
                            parsed = urlparse(current_url)
                            loc = f"{parsed.scheme}://{parsed.netloc}{loc}"

                        # Validate redirect scope (§1.1)
                        red_sr = scope_validator.validate_redirect(current_url, loc, rules)
                        if not red_sr.allowed:
                            duration = (time.monotonic() - start_time) * 1000.0
                            return VerificationResult(
                                success=False,
                                status_code=resp.status_code,
                                url=current_url,
                                request_headers=req_headers,
                                response_headers=dict(resp.headers),
                                raw_request=raw_req,
                                raw_response=f"Redirect blocked: destination '{loc}' is OUT OF SCOPE ({red_sr.reason})",
                                curl_command=curl_cmd,
                                request_sha256=req_sha256,
                                response_sha256="",
                                duration_ms=duration,
                                error=f"Redirect blocked: {red_sr.reason}",
                                scope_valid=False,
                            )

                        current_url = loc
                        redirect_count += 1
                        continue
                    break

                duration = (time.monotonic() - start_time) * 1000.0
                raw_resp_text = resp.text[:10000]  # Cap response body length
                resp_lines = [f"HTTP/1.1 {resp.status_code} {resp.reason_phrase or ''}"]
                for k, v in resp.headers.items():
                    resp_lines.append(f"{k}: {v}")
                resp_lines += ["", raw_resp_text]
                raw_resp = "\n".join(resp_lines)
                resp_sha256 = hashlib.sha256(raw_resp.encode()).hexdigest()

                return VerificationResult(
                    success=resp.is_success or resp.is_redirect,
                    status_code=resp.status_code,
                    url=current_url,
                    request_headers=req_headers,
                    response_headers=dict(resp.headers),
                    raw_request=raw_req,
                    raw_response=raw_resp,
                    curl_command=curl_cmd,
                    request_sha256=req_sha256,
                    response_sha256=resp_sha256,
                    duration_ms=duration,
                    error=None,
                    scope_valid=True,
                )

            except httpx.TimeoutException:
                duration = (time.monotonic() - start_time) * 1000.0
                return VerificationResult(
                    success=False,
                    status_code=0,
                    url=current_url,
                    request_headers=req_headers,
                    response_headers={},
                    raw_request=raw_req,
                    raw_response="",
                    curl_command=curl_cmd,
                    request_sha256=req_sha256,
                    response_sha256="",
                    duration_ms=duration,
                    error="Request timed out",
                    scope_valid=True,
                )
            except Exception as exc:
                duration = (time.monotonic() - start_time) * 1000.0
                return VerificationResult(
                    success=False,
                    status_code=0,
                    url=current_url,
                    request_headers=req_headers,
                    response_headers={},
                    raw_request=raw_req,
                    raw_response="",
                    curl_command=curl_cmd,
                    request_sha256=req_sha256,
                    response_sha256="",
                    duration_ms=duration,
                    error=str(exc),
                    scope_valid=True,
                )

    @staticmethod
    def build_curl_command(
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        data: str | None = None,
    ) -> str:
        """Generate a copy-pasteable curl reproduction command."""
        parts = ["curl", "-i", "-s", "-k", "-X", method.upper()]
        if headers:
            for k, v in headers.items():
                parts += ["-H", f"'{k}: {v}'"]
        if data:
            escaped_data = data.replace("'", "'\\''")
            parts += ["--data-raw", f"'{escaped_data}'"]
        parts.append(f"'{url}'")
        return " ".join(parts)


verification_engine = VerificationEngine()

