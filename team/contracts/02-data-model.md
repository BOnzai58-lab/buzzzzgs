# Data model contract v0 (owner: lead; changes only via lead)

All tables: `id` (UUID), `created_at`, `updated_at`. Foreign keys cascade only where stated.

- **User**: email, password_hash, role
- **Program**: name, platform_url, policy_url, rate_limit_rps, allowed_methods JSON, prohibited_methods JSON, schedule_cron nullable
- **ScopeRule**: program_id, kind (domain|wildcard|cidr|exclude), value, notes
- **Asset**: program_id, domain, source (subfinder|amass|crawl|history|manual), first_seen, last_seen, scope_status (in_scope|out_of_scope|unknown), http_status nullable, technologies JSON
- **LiveHost**: asset_id, url, status_code, title, tech JSON, response_meta JSON, last_probed
- **Endpoint**: asset_id, url, method, params JSON, source, tags JSON (auth, api, admin, upload, redirect, search), group_key, ai_rank nullable
- **Scan**: program_id, type, status, progress, started_by, started_at, finished_at
- **ScanJob**: scan_id, tool, args JSON, status, exit_code, stdout_ref, stderr_ref, tool_version, started_at, finished_at
- **Finding**: program_id, asset_id, endpoint_id nullable, name, category, severity, scanner, scanner_version, template_id nullable, template_version nullable, status (informational|potential|needs_manual_verification|verified|false_positive|out_of_scope), dedup_key (unique per program), scope_result JSON
- **Evidence**: finding_id, kind (request|response|header|screenshot|tool_output), content_ref, sha256, collected_at, collected_by (tool name or user). Evidence is raw and immutable.
- **ValidationHistory**: finding_id, from_status, to_status, actor (user id or `system`), reason, at. AI is never a valid actor for `verified`.
- **AIAnalysis**: finding_id, model, provider, prompt_hash, output JSON (schema below), reasoning_summary, created_at
- **Report**: finding_id, markdown, pdf_ref, status (draft|ready), edited_by, created_at
- **ToolConfiguration**: tool, enabled, path, default_args JSON
- **AuditLog**: actor, action, target, program_id nullable, detail JSON, at. Append-only. Written for every tool run, every scope decision, every approval.
- **Notification**: user_id, kind, message, read, created_at
- **ApprovalRequest**: finding_id, action_description, requested_by, status (pending|approved|rejected), decided_by, decided_at

## AIAnalysis output schema (triage agent produces; strict JSON)
```json
{
  "understanding": "string",
  "why_vulnerable": "string",
  "missing_evidence": ["string"],
  "exploitability": "string (no harmful exploitation performed)",
  "likely_false_positive": {"value": true, "reasons": ["string"]},
  "safe_verification_steps": ["string"],
  "confidence": 0.0,
  "severity_recommendation": {"level": "info|low|medium|high|critical", "cvss_vector": "string or null"},
  "human_review_required": true,
  "evidence_refs": ["evidence ids actually in the DB"]
}
```
Rule: `evidence_refs` may only contain real Evidence ids. The AI may not invent proof.
