# Role: FRONTEND

**Single task:** build the dark, professional React dashboard that talks to the real FastAPI backend.

## You own
`frontend/`.

## Deliverables
1. Vite + React + TypeScript + Tailwind + Recharts + Lucide. Typed API client generated from or matching `team/contracts/01-api.md`.
2. Pages: Overview, Programs, Reconnaissance, Assets, Live hosts, Endpoints, Findings, AI analysis, Reports (editable), Scan history, Tool manager, Settings.
3. Overview widgets from `GET /stats/overview` only: programs, subdomains, live hosts, endpoints, potential vs verified vs false positives, severity chart, recent scans, recent findings.
4. Live scan view over WebSocket: status, progress bar, streaming logs, a Stop button.
5. Search, filters, pagination, CSV/JSON export, asset relationship graph.
6. Approval inbox for active-test requests. Clear badges: potential / needs verification / verified / false positive / out of scope.
7. Auth screens and role-aware UI (viewer is read-only).
8. Empty, loading and error states everywhere.

## Rules
- No hardcoded or fake statistics, ever. An empty database shows zeros and empty states.
- Never display a finding as "verified" unless the API says so.
- If an endpoint you need is missing from the contract, post a `question` to `lead`; do not invent API shapes.
