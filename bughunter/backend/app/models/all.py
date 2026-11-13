"""Complete SQLAlchemy 2.x mapped models for all BugHunter tables."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type on Postgres, otherwise uses CHAR(36).
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(str(value))
        return value


def UUID(*args, **kwargs):
    return GUID()

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Enums ──────────────────────────────────────────────────────────────────────
class UserRole(str, enum.Enum):
    admin = "admin"
    analyst = "analyst"
    viewer = "viewer"


class ScopeKind(str, enum.Enum):
    domain = "domain"
    wildcard = "wildcard"
    cidr = "cidr"
    exclude = "exclude"


class AssetSource(str, enum.Enum):
    subfinder = "subfinder"
    amass = "amass"
    crawl = "crawl"
    history = "history"
    manual = "manual"


class ScopeStatus(str, enum.Enum):
    in_scope = "in_scope"
    out_of_scope = "out_of_scope"
    unknown = "unknown"


class ScanType(str, enum.Enum):
    subdomains = "subdomains"
    resolve = "resolve"
    probe = "probe"
    crawl = "crawl"
    history = "history"
    vuln = "vuln"


class ScanStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"
    stopped = "stopped"


class FindingSeverity(str, enum.Enum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


Severity = FindingSeverity


class FindingStatus(str, enum.Enum):
    informational = "informational"
    potential = "potential"
    needs_manual_verification = "needs_manual_verification"
    verified = "verified"
    false_positive = "false_positive"
    out_of_scope = "out_of_scope"


class EvidenceKind(str, enum.Enum):
    request = "request"
    response = "response"
    header = "header"
    screenshot = "screenshot"
    tool_output = "tool_output"


class ReportStatus(str, enum.Enum):
    draft = "draft"
    ready = "ready"


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


# ── Models ─────────────────────────────────────────────────────────────────────
class User(Base):
    """Platform user account."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False, default=UserRole.analyst
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    # Relationships
    scans: Mapped[list["Scan"]] = relationship("Scan", back_populates="started_by_user")
    approval_requests: Mapped[list["ApprovalRequest"]] = relationship(
        "ApprovalRequest", foreign_keys="ApprovalRequest.requested_by", back_populates="requester"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user"
    )


class Program(Base):
    """Bug bounty program configuration."""

    __tablename__ = "programs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    policy_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    rate_limit_rps: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    allowed_methods: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    prohibited_methods: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    schedule_cron: Mapped[str | None] = mapped_column(String(100), nullable=True)
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    # Relationships
    scope_rules: Mapped[list["ScopeRule"]] = relationship(
        "ScopeRule", back_populates="program", cascade="all, delete-orphan"
    )
    assets: Mapped[list["Asset"]] = relationship(
        "Asset", back_populates="program", cascade="all, delete-orphan"
    )
    scans: Mapped[list["Scan"]] = relationship(
        "Scan", back_populates="program", cascade="all, delete-orphan"
    )
    findings: Mapped[list["Finding"]] = relationship(
        "Finding", back_populates="program", cascade="all, delete-orphan"
    )
    authorization_records: Mapped[list["AuthorizationRecord"]] = relationship(
        "AuthorizationRecord", back_populates="program", cascade="all, delete-orphan"
    )


class AuthorizationRecord(Base):
    """Formal authorization record — ties a program to proof of permission.

    A target may only enter the active scan queue if its program has a valid,
    non-expired AuthorizationRecord.  This is enforced by the
    PolicyEnforcementGateway (§5 of Master Dev Spec).
    """

    __tablename__ = "authorization_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # own_asset / client / bug_bounty / other
    auth_type: Mapped[str] = mapped_column(String(64), nullable=False, default="bug_bounty")
    program_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scope_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Whether staff have independently verified the authorization
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # JSON arrays of authorized / excluded domains, IPs, paths
    authorized_domains: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    excluded_domains: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    authorized_ips: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    authorized_paths: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Program-specific conditions (no-dos, test-accounts-only, etc.)
    program_conditions: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    # Relationships
    program: Mapped["Program"] = relationship("Program", back_populates="authorization_records")


class ScopeRule(Base):
    """Defines in-scope / out-of-scope rules for a program."""

    __tablename__ = "scope_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[ScopeKind] = mapped_column(
        Enum(ScopeKind, name="scope_kind"), nullable=False
    )
    value: Mapped[str] = mapped_column(String(512), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    # Relationships
    program: Mapped["Program"] = relationship("Program", back_populates="scope_rules")


class Asset(Base):
    """Discovered subdomain / host."""

    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    source: Mapped[AssetSource] = mapped_column(
        Enum(AssetSource, name="asset_source"), nullable=False
    )
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    scope_status: Mapped[ScopeStatus] = mapped_column(
        Enum(ScopeStatus, name="scope_status"), nullable=False, default=ScopeStatus.unknown
    )
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    technologies: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    __table_args__ = (UniqueConstraint("program_id", "domain", name="uq_asset_program_domain"),)

    # Relationships
    program: Mapped["Program"] = relationship("Program", back_populates="assets")
    live_hosts: Mapped[list["LiveHost"]] = relationship(
        "LiveHost", back_populates="asset", cascade="all, delete-orphan"
    )
    endpoints: Mapped[list["Endpoint"]] = relationship(
        "Endpoint", back_populates="asset", cascade="all, delete-orphan"
    )
    findings: Mapped[list["Finding"]] = relationship("Finding", back_populates="asset")


class LiveHost(Base):
    """HTTP-reachable host with probed metadata."""

    __tablename__ = "live_hosts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tech: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    response_meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_probed: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="live_hosts")


class Endpoint(Base):
    """Crawled / discovered HTTP endpoint."""

    __tablename__ = "endpoints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False, default="GET")
    params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    group_key: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    ai_rank: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="endpoints")
    findings: Mapped[list["Finding"]] = relationship("Finding", back_populates="endpoint")


class Scan(Base):
    """Top-level scan record linking to individual ScanJobs."""

    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[ScanType] = mapped_column(
        Enum(ScanType, name="scan_type"), nullable=False
    )
    status: Mapped[ScanStatus] = mapped_column(
        Enum(ScanStatus, name="scan_status"), nullable=False, default=ScanStatus.queued
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    # Relationships
    program: Mapped["Program"] = relationship("Program", back_populates="scans")
    started_by_user: Mapped["User"] = relationship("User", back_populates="scans")
    jobs: Mapped[list["ScanJob"]] = relationship(
        "ScanJob", back_populates="scan", cascade="all, delete-orphan"
    )


class ScanJob(Base):
    """Individual tool invocation within a Scan."""

    __tablename__ = "scan_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tool: Mapped[str] = mapped_column(String(64), nullable=False)
    args: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stdout_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    stderr_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tool_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    scan: Mapped["Scan"] = relationship("Scan", back_populates="jobs")


class Finding(Base):
    """Vulnerability / informational finding from a scan."""

    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    endpoint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("endpoints.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[FindingSeverity] = mapped_column(
        Enum(FindingSeverity, name="finding_severity"), nullable=False
    )
    scanner: Mapped[str] = mapped_column(String(64), nullable=False)
    scanner_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    template_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    template_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[FindingStatus] = mapped_column(
        Enum(FindingStatus, name="finding_status"),
        nullable=False,
        default=FindingStatus.potential,
    )
    dedup_key: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    scope_result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    raw_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    __table_args__ = (
        UniqueConstraint("program_id", "dedup_key", name="uq_finding_program_dedup"),
    )

    # Relationships
    program: Mapped["Program"] = relationship("Program", back_populates="findings")
    asset: Mapped["Asset | None"] = relationship("Asset", back_populates="findings")
    endpoint: Mapped["Endpoint | None"] = relationship("Endpoint", back_populates="findings")
    evidence: Mapped[list["Evidence"]] = relationship(
        "Evidence", back_populates="finding", cascade="all, delete-orphan"
    )
    validation_history: Mapped[list["ValidationHistory"]] = relationship(
        "ValidationHistory", back_populates="finding", cascade="all, delete-orphan"
    )
    ai_analyses: Mapped[list["AIAnalysis"]] = relationship(
        "AIAnalysis", back_populates="finding", cascade="all, delete-orphan"
    )
    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="finding", cascade="all, delete-orphan"
    )
    approval_requests: Mapped[list["ApprovalRequest"]] = relationship(
        "ApprovalRequest", back_populates="finding"
    )


class Evidence(Base):
    """Immutable evidence artifact attached to a Finding."""

    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[EvidenceKind] = mapped_column(
        Enum(EvidenceKind, name="evidence_kind"), nullable=False
    )
    content_ref: Mapped[str] = mapped_column(String(2048), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    collected_by: Mapped[str] = mapped_column(String(128), nullable=False)
    # Extended fields for reproducible evidence (§1.3, §4.4)
    raw_request: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    curl_command: Mapped[str | None] = mapped_column(Text, nullable=True)
    reproduction_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_verified_by_human: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    finding: Mapped["Finding"] = relationship("Finding", back_populates="evidence")


class ValidationHistory(Base):
    """Audit trail of finding status transitions."""

    __tablename__ = "validation_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[str] = mapped_column(String(64), nullable=False)
    to_status: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    # Relationships
    finding: Mapped["Finding"] = relationship("Finding", back_populates="validation_history")


class AIAnalysis(Base):
    """AI-generated analysis of a finding."""

    __tablename__ = "ai_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    output: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    reasoning_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    # Relationships
    finding: Mapped["Finding"] = relationship("Finding", back_populates="ai_analyses")


class Report(Base):
    """Generated bug report (Markdown + optional PDF)."""

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status"), nullable=False, default=ReportStatus.draft
    )
    edited_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    # Relationships
    finding: Mapped["Finding"] = relationship("Finding", back_populates="reports")


class ToolConfiguration(Base):
    """Per-tool configuration and enable/disable switch."""

    __tablename__ = "tool_configurations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tool: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    default_args: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class AuditLog(Base):
    """Append-only audit log — never updated or deleted."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target: Mapped[str | None] = mapped_column(String(512), nullable=True)
    program_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    detail: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, index=True)


class Notification(Base):
    """In-platform notification for a user."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")


class ApprovalRequest(Base):
    """Approval workflow record for sensitive actions (e.g. mark verified)."""

    __tablename__ = "approval_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_description: Mapped[str] = mapped_column(Text, nullable=False)
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="approval_status"),
        nullable=False,
        default=ApprovalStatus.pending,
    )
    decided_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    # Relationships
    finding: Mapped["Finding"] = relationship("Finding", back_populates="approval_requests")
    requester: Mapped["User"] = relationship(
        "User", foreign_keys=[requested_by], back_populates="approval_requests"
    )
