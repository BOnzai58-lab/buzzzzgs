import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.models.all import UserRole, ScopeKind, AssetSource, ScopeStatus
from app.models.all import ScanType, ScanStatus, Severity, FindingStatus
from app.models.all import EvidenceKind, ReportStatus, ApprovalStatus


# ── Auth ─────────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserRoleUpdate(BaseModel):
    role: UserRole

class UserResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    email: str
    role: UserRole
    created_at: datetime


# ── Programs ─────────────────────────────────────────────────────────────

class ProgramCreate(BaseModel):
    name: str
    platform_url: str | None = None
    policy_url: str | None = None
    rate_limit_rps: float = 1.0
    allowed_methods: list[str] = []
    prohibited_methods: list[str] = []
    schedule_cron: str | None = None

class ProgramUpdate(BaseModel):
    name: str | None = None
    platform_url: str | None = None
    policy_url: str | None = None
    rate_limit_rps: float | None = None
    allowed_methods: list[str] | None = None
    prohibited_methods: list[str] | None = None
    schedule_cron: str | None = None
    monitoring_enabled: bool | None = None
    active: bool | None = None

class ProgramResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    name: str
    platform_url: str | None
    policy_url: str | None
    rate_limit_rps: float
    allowed_methods: list
    prohibited_methods: list
    schedule_cron: str | None
    monitoring_enabled: bool
    active: bool
    created_at: datetime
    updated_at: datetime


# ── Scope Rules ───────────────────────────────────────────────────────────

class ScopeRuleCreate(BaseModel):
    kind: ScopeKind
    value: str
    notes: str | None = None

class ScopeRuleResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    program_id: uuid.UUID
    kind: ScopeKind
    value: str
    notes: str | None
    created_at: datetime

class ScopeCheckRequest(BaseModel):
    program_id: uuid.UUID
    target: str

class ScopeCheckResponse(BaseModel):
    allowed: bool
    reason: str
    matched_rule_id: uuid.UUID | None


# ── Scans ─────────────────────────────────────────────────────────────────

class ScanCreate(BaseModel):
    type: ScanType
    targets: list[str] = []

class ScanResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    program_id: uuid.UUID
    type: ScanType
    status: ScanStatus
    progress: int
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


# ── Assets ─────────────────────────────────────────────────────────────────

class AssetResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    program_id: uuid.UUID
    domain: str
    source: AssetSource
    first_seen: datetime
    last_seen: datetime
    scope_status: ScopeStatus
    http_status: int | None
    technologies: list


# ── Live Hosts ────────────────────────────────────────────────────────────

class LiveHostResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    asset_id: uuid.UUID
    url: str
    status_code: int
    title: str | None
    tech: list
    response_meta: dict
    last_probed: datetime


# ── Endpoints ─────────────────────────────────────────────────────────────

class EndpointResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    asset_id: uuid.UUID
    url: str
    method: str
    params: dict
    source: str
    tags: list
    group_key: str | None
    ai_rank: float | None


# ── Findings ──────────────────────────────────────────────────────────────

class FindingResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    program_id: uuid.UUID
    asset_id: uuid.UUID | None
    endpoint_id: uuid.UUID | None
    name: str
    category: str
    severity: Severity
    scanner: str
    scanner_version: str | None
    template_id: str | None
    status: FindingStatus
    dedup_key: str
    scope_result: dict
    created_at: datetime
    updated_at: datetime

class FindingStatusUpdate(BaseModel):
    status: FindingStatus
    note: str | None = None


# ── Evidence ──────────────────────────────────────────────────────────────

class EvidenceResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    finding_id: uuid.UUID
    kind: EvidenceKind
    content_ref: str
    sha256: str
    collected_at: datetime
    collected_by: str


# ── AI Analysis ───────────────────────────────────────────────────────────

class AIAnalysisResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    finding_id: uuid.UUID
    model: str
    provider: str
    output: dict
    reasoning_summary: str | None
    created_at: datetime


# ── Reports ───────────────────────────────────────────────────────────────

class ReportResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    finding_id: uuid.UUID
    markdown: str
    pdf_ref: str | None
    status: ReportStatus
    created_at: datetime

class ReportUpdate(BaseModel):
    markdown: str


# ── Approvals ─────────────────────────────────────────────────────────────

class ApprovalResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    finding_id: uuid.UUID
    action_description: str
    requested_by: uuid.UUID
    status: ApprovalStatus
    decided_by: uuid.UUID | None
    decided_at: datetime | None
    created_at: datetime

class ApprovalDecision(BaseModel):
    reason: str | None = None


# ── Stats ─────────────────────────────────────────────────────────────────

class OverviewStats(BaseModel):
    total_programs: int
    total_subdomains: int
    live_hosts: int
    endpoints: int
    potential_vulnerabilities: int
    verified_vulnerabilities: int
    false_positives: int
    pending_approvals: int
    severity_distribution: dict[str, int]


# ── Tools ─────────────────────────────────────────────────────────────────

class ToolStatus(BaseModel):
    name: str
    installed: bool
    version: str | None
    install_hint: str
    enabled: bool


# ── Pagination ────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    items: list
    total: int


from app.schemas.batch import (  # noqa: F401
    BatchCreate,
    BatchResponse,
    BatchDetailResponse,
    TargetImportRequest,
    BatchTargetResponse,
    AssessmentJobResponse,
    JobEventResponse,
    EmergencyStopRequest,
    JobScheduleCreate,
    JobScheduleResponse,
    WorkerHeartbeatResponse,
)

