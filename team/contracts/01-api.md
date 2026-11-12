# API contract v0 (owner: lead). Base path `/api/v1`. JSON. Bearer auth (JWT).

Roles: `admin`, `analyst`, `viewer`. Viewers are read-only.

## Programs and scope (scope agent)
- `POST /programs` create. Body: `name, platform_url, policy_url, rate_limit_rps, allowed_methods[], prohibited_methods[]`
- `GET /programs`, `GET /programs/{id}`, `PATCH /programs/{id}`
- `POST /programs/{id}/scope-rules` body: `{kind: "domain"|"wildcard"|"cidr"|"exclude", value, notes}`
- `POST /scope/check` body `{program_id, target}` -> `{allowed: bool, reason, matched_rule_id}`. Default is **deny** when no rule matches or rules conflict. Exclusions always win.

## Scans (recon + scanner agents)
- `POST /programs/{id}/scans` body `{type: "subdomains"|"resolve"|"probe"|"crawl"|"history"|"vuln", targets?: []}` -> `{scan_id}`; refuses with 403 + reason if any target fails scope.
- `GET /scans/{id}` -> `{status: "queued|running|done|failed|stopped", progress: 0-100, started_at, finished_at}`
- `POST /scans/{id}/stop` must stop the job within 5 seconds.
- `WS /ws/scans/{id}` streams `{ts, level, message}` log lines.

## Data (read endpoints; each supports `?program_id=&q=&limit=&offset=`)
- `GET /assets`, `/live-hosts`, `/endpoints`, `/findings`, `/reports`, `/audit-logs`
- `GET /stats/overview` returns real counts from the DB only. Zero when empty. Never fake numbers.

## Findings and AI (triage agent)
- `GET /findings/{id}` includes evidence list and validation history.
- `POST /findings/{id}/analyze` -> structured AIAnalysis (see data model).
- `POST /findings/{id}/status` body `{status, note}`. Setting `verified` requires an evidence record produced by the verification engine and a human user, never AI confidence alone.
- `POST /findings/{id}/verify` creates an approval request. Active checks run only after `POST /approvals/{id}/approve` by an analyst or admin.

## Reports (triage agent)
- `POST /findings/{id}/report` -> draft; `GET /reports/{id}?format=md|pdf`; `PATCH /reports/{id}` for editing. Nothing is ever auto-submitted.

## Tools (recon agent owns detection)
- `GET /tools` -> `[{name, installed, version, install_hint}]`

All errors: `{error: {code, message}}`. Pagination: `{items, total}`.
