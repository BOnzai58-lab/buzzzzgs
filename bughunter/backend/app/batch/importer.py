"""Multi-format Target Importer with streaming parsing and deduplication."""
from __future__ import annotations

import csv
import io
import json
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import AsyncGenerator, Iterator


@dataclass
class ImportedTargetRecord:
    raw_target: str
    normalized_target: str
    target_type: str = "domain"
    program_hint: str | None = None
    authorization_reference: str | None = None
    scope_reference: str | None = None
    testing_profile: str = "standard"
    priority: str = "normal"
    notes: str | None = None
    is_duplicate: bool = False
    existing_assessment_id: str | None = None


def normalize_target_string(raw: str) -> tuple[str, str]:
    """Normalize input target and return (normalized_string, target_type).
    Handles:
    - URLs: http://example.com/api -> example.com (type: url or domain)
    - Hostnames: Sub.Example.Com -> sub.example.com (type: domain)
    - IP addresses: 192.168.1.1 (type: ip)
    - CIDR ranges: 10.0.0.0/24 (type: cidr)
    - Git repositories: https://github.com/org/repo (type: repo)
    """
    cleaned = raw.strip()
    if not cleaned:
        return "", "invalid"

    # Git repo detection
    if "github.com/" in cleaned or "gitlab.com/" in cleaned or cleaned.endswith(".git"):
        parsed = urllib.parse.urlparse(cleaned if "://" in cleaned else f"https://{cleaned}")
        clean_path = parsed.path.rstrip("/")
        return f"{parsed.netloc}{clean_path}".lower(), "repo"

    # CIDR detection
    cidr_match = re.match(r"^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$", cleaned)
    if cidr_match:
        return cleaned, "cidr"

    # Single IP detection
    ip_match = re.match(r"^(\d{1,3}\.){3}\d{1,3}$", cleaned)
    if ip_match:
        return cleaned, "ip"

    # URL / Hostname parsing
    if "://" in cleaned:
        parsed = urllib.parse.urlparse(cleaned)
        host = parsed.netloc or parsed.path
        # Remove default ports
        host = re.sub(r":(80|443)$", "", host)
        # If specific path was provided, distinguish as URL/API
        if parsed.path and parsed.path != "/":
            return f"{host.lower()}{parsed.path.rstrip('/')}", "url"
        return host.lower(), "domain"
    else:
        # Hostname with optional port or path
        parts = cleaned.split("/", 1)
        host = parts[0]
        host = re.sub(r":(80|443)$", "", host)
        if len(parts) > 1 and parts[1].strip():
            return f"{host.lower()}/{parts[1].rstrip('/')}", "url"
        return host.lower(), "domain"


class TargetListImporter:
    """Streams and parses TXT, CSV, JSON, and manual input formats with deduplication."""

    @staticmethod
    def parse_txt(content: str) -> Iterator[ImportedTargetRecord]:
        lines = content.splitlines()
        seen = set()
        for line in lines:
            trimmed = line.strip()
            if not trimmed or trimmed.startswith("#") or trimmed.startswith("//"):
                continue
            normalized, ttype = normalize_target_string(trimmed)
            if not normalized:
                continue
            is_dup = normalized in seen
            seen.add(normalized)
            yield ImportedTargetRecord(
                raw_target=trimmed,
                normalized_target=normalized,
                target_type=ttype,
                is_duplicate=is_dup,
            )

    @staticmethod
    def parse_csv(content: str) -> Iterator[ImportedTargetRecord]:
        f = io.StringIO(content.strip())
        reader = csv.DictReader(f)
        seen = set()

        # If header doesn't have 'target', fallback to first column
        for row in reader:
            target_val = (
                row.get("target")
                or row.get("domain")
                or row.get("url")
                or row.get("host")
                or (list(row.values())[0] if row else "")
            )
            if not target_val or not target_val.strip():
                continue

            raw = target_val.strip()
            normalized, ttype = normalize_target_string(raw)
            if not normalized:
                continue

            is_dup = normalized in seen
            seen.add(normalized)

            yield ImportedTargetRecord(
                raw_target=raw,
                normalized_target=normalized,
                target_type=row.get("target_type") or ttype,
                program_hint=row.get("program"),
                authorization_reference=row.get("authorization_reference"),
                scope_reference=row.get("scope_reference"),
                testing_profile=row.get("testing_profile", "standard"),
                priority=row.get("priority", "normal"),
                notes=row.get("notes"),
                is_duplicate=is_dup,
            )

    @staticmethod
    def parse_json(content: str) -> Iterator[ImportedTargetRecord]:
        data = json.loads(content)
        seen = set()
        items = data if isinstance(data, list) else data.get("targets", [])

        for item in items:
            if isinstance(item, str):
                raw = item.strip()
                normalized, ttype = normalize_target_string(raw)
                if not normalized:
                    continue
                is_dup = normalized in seen
                seen.add(normalized)
                yield ImportedTargetRecord(
                    raw_target=raw,
                    normalized_target=normalized,
                    target_type=ttype,
                    is_duplicate=is_dup,
                )
            elif isinstance(item, dict):
                raw = (item.get("target") or item.get("domain") or item.get("url") or "").strip()
                if not raw:
                    continue
                normalized, ttype = normalize_target_string(raw)
                if not normalized:
                    continue
                is_dup = normalized in seen
                seen.add(normalized)
                yield ImportedTargetRecord(
                    raw_target=raw,
                    normalized_target=normalized,
                    target_type=item.get("target_type") or ttype,
                    program_hint=item.get("program"),
                    authorization_reference=item.get("authorization_reference"),
                    scope_reference=item.get("scope_reference"),
                    testing_profile=item.get("testing_profile", "standard"),
                    priority=item.get("priority", "normal"),
                    notes=item.get("notes"),
                    is_duplicate=is_dup,
                )

    @classmethod
    def parse(cls, content: str, source_format: str) -> Iterator[ImportedTargetRecord]:
        source = source_format.lower()
        if source == "csv":
            return cls.parse_csv(content)
        elif source == "json":
            return cls.parse_json(content)
        else:
            return cls.parse_txt(content)

