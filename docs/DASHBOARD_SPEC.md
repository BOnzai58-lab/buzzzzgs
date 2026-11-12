# Dashboard Specification — BUG HUNTER AI

## Purpose
The dashboard is the operator's single control plane for authorized bug bounty operations. It must display real backend state and control real jobs, workers, agents, and schedules.

## Navigation
- Overview
- Operations Center
- AI Agents
- Programs
- Reconnaissance
- Assets
- Live Hosts
- Endpoints
- Vulnerabilities
- Verification Queue
- Reports
- Scan History
- Tool Manager
- Notifications
- Settings
- Audit Logs

## Overview metrics
All metrics are computed from persisted records:
- Programs: total and active
- Assets: subdomains, live hosts, dead hosts
- Endpoints discovered
- Jobs: queued, running, paused, completed, failed, stopped
- Findings: potential, needs review, verified, false positive, out of scope
- Severity distribution
- Recent operations and findings

Empty data displays zero. No production demo values or fabricated charts.

## Operations Center
Each operation row/detail includes:
- Job ID and type
- Program and validated target
- Tool and tool version
- Current state
- Start/end timestamps and elapsed duration
- Progress only when measurable
- Current stage
- Output counters and finding count
- Warnings and errors
- Queue position
- Live timestamped logs

Controls:
- Start
- Pause
- Resume
- Stop
- Cancel queued
- Retry failed
- Stop all

A control is not successful until the backend confirms the state transition. Show intermediate `stopping` state while workers terminate. Stop-all must halt dispatch, cancel queued work, signal active workers, prevent new requests, persist state, and audit the operator.

## Agent Monitor
Show agent name, online/offline/paused status, current task, program, job, last activity, task counts, provider/model, available usage metadata, errors, decision summaries, and tool-call audit records. Never expose hidden chain-of-thought.

## Tool Manager
Show installed/missing, version, executable path with sensitive portions redacted, health check, enabled state, last execution, errors, and installation guidance. Never claim a missing tool is installed.

## Program manager
Create/edit programs, add root domains and wildcard rules, exclusions, authorized IP ranges, policy references, permitted tools, prohibited methods, rate limits, and schedule settings. Imported rules require human review. Display a clear scope validation result before a job starts.

## Findings center
Search/filter by severity, status, program, asset, and category. Detail view includes evidence references, scanner provenance, AI analysis, confidence, notes, status history, and approval request. Scanner alerts start as potential. Verification requires evidence and human review.

## Verification queue
Show exact requested action, target, tool, purpose, policy basis, scope snapshot, expected impact, expiry, requester, and approval status. Approval is specific to one operation and must be revalidated before execution.

## Reports
Generate editable Markdown/PDF from persisted evidence. Show draft/review/export states. Never auto-submit.

## Notifications
New assets, findings, approval requests, failed jobs, monitoring changes, and worker errors.

## Real-time events
WebSocket events:
`agent_status_changed`, `scan_started`, `scan_progress`, `scan_log`, `scan_paused`, `scan_resumed`, `scan_stopping`, `scan_stopped`, `scan_completed`, `scan_failed`, `finding_created`, `finding_updated`, `approval_requested`, `approval_completed`, `notification_created`.

On reconnect, fetch authoritative state before applying new events.

## Design
Professional dark SOC interface, restrained cyan/green accents, responsive sidebar layout, accessible contrast, searchable/filterable tables, clear state labels, charts, toast messages, and confirmation dialogs. Operational clarity takes priority over animation.
