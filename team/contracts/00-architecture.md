# Architecture and ownership (owner: lead)

## Stack
Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL, Redis, Celery, WebSockets.
Frontend: React, TypeScript, Tailwind CSS, Recharts, Lucide. AI: provider-independent LLM layer (OpenAI-compatible and Ollama), structured JSON output.

## Directory ownership
| Path | Owner |
|---|---|
| `infra/`, `docker-compose.yml`, `alembic/`, `backend/app/main.py`, `backend/app/models/`, `backend/app/core/config.py`, `team/contracts/` | lead |
| `backend/app/scope/`, `backend/app/audit/`, `backend/app/auth/` | scope |
| `backend/app/recon/`, `backend/app/tools/base.py` and recon adapters | recon |
| `backend/app/scanners/` (Nuclei, ffuf, Dalfox, SQLMap adapters, evidence, dedup) | scanner |
| `backend/app/ai/`, `backend/app/verification/`, `backend/app/reports/` | triage |
| `frontend/` | frontend |
| `tests/`, `scripts/install_kali.sh`, `docs/` | qa |

## Layering rules
1. Every tool run goes: API or Celery task -> `scope.validate_target()` -> tool adapter -> audit log. No adapter may be called without a scope check.
2. Adapters never talk to the database; they return validated Pydantic objects. Services persist them.
3. The AI layer cannot call adapters directly. It outputs structured JSON; backend code decides what runs, after scope validation and, for active tests, human approval.
4. Scope validation is deterministic Python. No LLM is involved.

## Phase order (do not skip)
1 skeleton, Docker, DB -> 2 programs, scope, Subfinder, dnsx, httpx -> 3 crawling, endpoints, historical URLs -> 4 Nuclei, findings, evidence -> 5 AI triage, false positives, verification -> 6 reports, dashboard, monitoring -> 7 tests, security review, docs.
Lead announces each phase start in the chat. Agents do not start a phase early.


## Operations dashboard and real-time control (extension)
- `frontend/` owns all dashboard pages and WebSocket client state.
- `backend/app/operations/` owns job lifecycle, control actions, event persistence, and worker cancellation.
- `backend/app/agents/` owns agent registry, task state, and agent controls.
- `backend/app/tools/` owns tool registry, health checks, and adapter metadata.
- `backend/app/notifications/` owns notification persistence and delivery.
- Lead owns shared event/API contracts and cross-module integration; QA owns acceptance and integration tests.

### Mandatory control-plane rules
1. Dashboard metrics are database-backed; no hardcoded operational statistics.
2. A UI control is complete only when it invokes a protected backend action and the backend confirms the result.
3. `stop-all` halts dispatch, cancels queued tasks, signals running workers, prevents new outbound requests, persists outcomes, and writes an audit event.
4. WebSocket events are notifications, not the source of truth. Clients reconcile with persisted API state after reconnect.
5. Progress may be shown only when measured. Otherwise display an indeterminate state.
6. Approval is bound to a specific operation and must be revalidated against current scope and policy at execution time.
