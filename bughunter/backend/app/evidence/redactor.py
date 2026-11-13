"""Evidence Redaction Service — Sanitization of captured security evidence.

Implements minimal sanitized evidence per Master Development Specification §12.1.
Redacts session identifiers, bearer tokens, API keys, passwords, and private
credentials from raw requests, raw responses, and generated curl commands
while preserving technical reproduciblity and structural integrity.
"""
from __future__ import annotations

import re
from typing import Any


class EvidenceRedactor:
    """Sanitizes sensitive tokens, credentials, and PII from evidence."""

    # Sensitive header names (case-insensitive)
    SENSITIVE_HEADERS = {
        "authorization",
        "proxy-authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "x-auth-token",
        "api-key",
        "apikey",
        "private-token",
        "x-access-token",
        "x-secret-token",
        "token",
        "secret",
    }

    # Sensitive query / form parameter keys
    SENSITIVE_PARAMS = [
        "password",
        "passwd",
        "pass",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "apikey",
        "client_secret",
        "auth_token",
        "session_id",
        "session",
        "jwt",
    ]

    # JWT regex
    JWT_PATTERN = re.compile(
        r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
    )

    # AWS Access Key ID
    AWS_KEY_PATTERN = re.compile(r"\bAKIA[0-9A-Z]{16}\b")

    # Private Key PEM blocks
    PRIVATE_KEY_PATTERN = re.compile(
        r"-----BEGIN (?:[A-Z0-9_-]+ )?PRIVATE KEY-----[\s\S]+?-----END (?:[A-Z0-9_-]+ )?PRIVATE KEY-----"
    )

    def redact_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """Redact sensitive HTTP header values in a header mapping."""
        redacted = {}
        for name, value in headers.items():
            lower = name.lower()
            if lower == "authorization":
                if value.lower().startswith("bearer "):
                    redacted[name] = "Bearer [REDACTED_TOKEN]"
                elif value.lower().startswith("basic "):
                    redacted[name] = "Basic [REDACTED_CREDENTIALS]"
                else:
                    redacted[name] = "[REDACTED_AUTH]"
            elif lower == "cookie":
                redacted[name] = self._redact_cookie_header(value)
            elif lower == "set-cookie":
                redacted[name] = self._redact_set_cookie_header(value)
            elif lower in self.SENSITIVE_HEADERS or any(s in lower for s in ("token", "secret", "key", "auth")):
                redacted[name] = "[REDACTED_SECRET]"
            else:
                redacted[name] = self.redact_text(value)
        return redacted

    def _redact_cookie_header(self, cookie_val: str) -> str:
        """Sanitizes Cookie header values (e.g. session=abc; token=xyz)."""
        pairs = [p.strip() for p in cookie_val.split(";") if p.strip()]
        sanitized = []
        for pair in pairs:
            if "=" in pair:
                k, _ = pair.split("=", 1)
                sanitized.append(f"{k.strip()}=[REDACTED]")
            else:
                sanitized.append(pair)
        return "; ".join(sanitized)

    def _redact_set_cookie_header(self, set_cookie_val: str) -> str:
        """Sanitizes Set-Cookie values while keeping directive attributes intact."""
        parts = [p.strip() for p in set_cookie_val.split(";")]
        if not parts:
            return set_cookie_val
        first = parts[0]
        if "=" in first:
            name, _ = first.split("=", 1)
            parts[0] = f"{name.strip()}=[REDACTED]"
        return "; ".join(parts)

    def redact_text(self, text: str) -> str:
        """Sanitizes general text strings (JWTs, AWS keys, PEM blocks, query params)."""
        if not text:
            return ""

        # 1. Redact Private Keys
        out = self.PRIVATE_KEY_PATTERN.sub("[REDACTED_PRIVATE_KEY]", text)

        # 2. Redact AWS Keys
        out = self.AWS_KEY_PATTERN.sub("[REDACTED_AWS_KEY]", out)

        # 3. Redact JWTs
        out = self.JWT_PATTERN.sub("[REDACTED_JWT]", out)

        # 4. Redact URL / query string parameters
        for param in self.SENSITIVE_PARAMS:
            # Query param / form param: param=value
            out = re.sub(
                rf"(?i)(\b{re.escape(param)}\b\s*[:=]\s*)([\"']?)[^&\"\s\n\r]+(\2)",
                r"\1\2[REDACTED]\2",
                out,
            )

        return out

    def redact_raw_request(self, raw_request: str) -> str:
        """Sanitizes a full raw HTTP request string (headers + body)."""
        if not raw_request:
            return ""

        lines = raw_request.splitlines()
        if not lines:
            return ""

        out_lines = []
        body_start = False
        body_lines = []

        for line in lines:
            if body_start:
                body_lines.append(line)
                continue

            if line.strip() == "":
                body_start = True
                continue

            # Header line: Name: Value
            if ":" in line and not line.startswith("GET ") and not line.startswith("POST ") and not line.startswith("PUT ") and not line.startswith("DELETE ") and not line.startswith("PATCH ") and not line.startswith("HEAD ") and not line.startswith("OPTIONS "):
                parts = line.split(":", 1)
                header_name = parts[0].strip()
                header_val = parts[1].strip()
                h_map = self.redact_headers({header_name: header_val})
                out_lines.append(f"{header_name}: {h_map.get(header_name, header_val)}")
            else:
                out_lines.append(self.redact_text(line))

        result = "\n".join(out_lines)
        if body_lines:
            body_text = "\n".join(body_lines)
            redacted_body = self.redact_text(body_text)
            result += "\n\n" + redacted_body

        return result

    def redact_raw_response(self, raw_response: str) -> str:
        """Sanitizes a full raw HTTP response string (headers + body)."""
        if not raw_response:
            return ""

        lines = raw_response.splitlines()
        if not lines:
            return ""

        out_lines = []
        body_start = False
        body_lines = []

        for line in lines:
            if body_start:
                body_lines.append(line)
                continue

            if line.strip() == "":
                body_start = True
                continue

            if ":" in line and not line.startswith("HTTP/"):
                parts = line.split(":", 1)
                header_name = parts[0].strip()
                header_val = parts[1].strip()
                h_map = self.redact_headers({header_name: header_val})
                out_lines.append(f"{header_name}: {h_map.get(header_name, header_val)}")
            else:
                out_lines.append(line)

        result = "\n".join(out_lines)
        if body_lines:
            body_text = "\n".join(body_lines)
            redacted_body = self.redact_text(body_text)
            result += "\n\n" + redacted_body

        return result

    def redact_curl_command(self, curl_cmd: str) -> str:
        """Sanitizes curl command headers and body payloads."""
        if not curl_cmd:
            return ""
        return self.redact_text(curl_cmd)


evidence_redactor = EvidenceRedactor()

