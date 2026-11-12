# Implementation Plan and Acceptance Checklist

## Phase 0 — Repository inspection
- [ ] Read README, kickoff, all role prompts, contracts, team protocol, status, and existing master prompt.
- [ ] Inspect source tree and git status.
- [ ] Map existing, partial, missing, and broken features.
- [ ] Publish implementation plan and ownership map.
- [ ] Reconcile API and database contracts.

## Phase 1 — Foundation
- [ ] FastAPI app and health endpoints.
- [ ] React/TypeScript/Vite app.
- [ ] PostgreSQL and Alembic migrations.
- [ ] Redis and worker queue.
- [ ] Docker Compose health checks.
- [ ] Authentication and RBAC.
- [ ] `.env.example` and secure configuration.

## Phase 2 — Scope and programs
- [ ] Program CRUD and policy snapshots.
- [ ] Deterministic exact/wildcard matching.
- [ ] Exclusion precedence.
- [ ] Deny-by-default behavior.
- [ ] Redirect and DNS/IP revalidation.
- [ ] Scope unit tests and audit records.

## Phase 3 — Operations control plane
- [ ] Persisted job state machine.
- [ ] Worker heartbeats and recovery.
- [ ] Real pause/resume/cancel behavior.
- [ ] Global stop-all behavior.
- [ ] Structured logs and event persistence.
- [ ] WebSocket streaming and reconnect reconciliation.

## Phase 4 — Dashboard vertical slice
- [ ] Overview backed by database queries.
- [ ] Live Operations Center.
- [ ] Functional job controls.
- [ ] Agent monitor.
- [ ] Program management UI.
- [ ] Tool Manager.
- [ ] Audit Logs.

## Phase 5 — Reconnaissance
- [ ] Tool availability/version detection.
- [ ] Subfinder adapter.
- [ ] Amass adapter.
- [ ] dnsx adapter.
- [ ] httpx adapter.
- [ ] Naabu only when explicitly authorized.
- [ ] Asset provenance and deduplication.

## Phase 6 — Endpoint intelligence
- [ ] Katana adapter.
- [ ] gau and waybackurls adapters.
- [ ] URL normalization and deduplication.
- [ ] Endpoint categorization.
- [ ] Endpoint dashboard.

## Phase 7 — Vulnerability intelligence
- [ ] Nuclei adapter.
- [ ] Controlled ffuf adapter.
- [ ] Evidence persistence and redaction.
- [ ] Finding deduplication.
- [ ] AI structured analysis.
- [ ] False-positive workflow.

## Phase 8 — Verification and approval
- [ ] Approval request lifecycle.
- [ ] Exact-operation-bound approval.
- [ ] Scope revalidation before execution.
- [ ] Safe verification allowlist.
- [ ] Human verification decision and evidence.

## Phase 9 — Reports and monitoring
- [ ] Markdown report export.
- [ ] PDF report export.
- [ ] Notifications.
- [ ] Scheduled passive monitoring.
- [ ] Monitoring history and pause conditions.

## Phase 10 — Release readiness
- [ ] Unit tests.
- [ ] Local Juice Shop integration tests.
- [ ] Scope escape tests.
- [ ] Worker cancellation tests.
- [ ] WebSocket tests.
- [ ] Dashboard/API consistency tests.
- [ ] Security review and deployment docs.

## Completion rule
A checkbox is complete only when implemented and verified. Mark unavailable-tool tests as skipped with the reason; never report them as passed.
