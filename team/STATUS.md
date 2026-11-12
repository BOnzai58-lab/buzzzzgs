# Acceptance checklist (lead maintains; QA verifies)

## Foundation
- [ ] Docker services start with health checks
- [ ] Frontend talks to FastAPI
- [ ] DB migrations work from a clean database
- [ ] Authentication and RBAC work

## Scope and programs
- [ ] User can create and edit a program
- [ ] Scope validation blocks excluded targets
- [ ] Ambiguous scope denies by default
- [ ] Redirect and DNS/IP scope escape is blocked
- [ ] Scope decisions are audited

## Operations control plane
- [ ] Jobs persist with valid state transitions
- [ ] Real pause/resume/stop works
- [ ] Stop-all terminates active work and cancels queued work
- [ ] Worker recovery works
- [ ] WebSocket events stream and reconnect safely

## Reconnaissance and scanning
- [ ] Tool detection reports real status and version
- [ ] Subfinder runs on authorized test domain
- [ ] DNS resolution works
- [ ] httpx identifies live hosts
- [ ] Endpoint discovery returns real results
- [ ] Nuclei runs on local test environment
- [ ] Scanner results and evidence are stored
- [ ] Rate limits and timeouts are enforced

## AI and findings
- [ ] AI analysis returns schema-valid structured output
- [ ] AI cannot bypass scope or invoke tools directly
- [ ] Findings are reviewable and evidence-backed
- [ ] Scanner alerts remain potential until reviewed
- [ ] Approval workflow gates restricted active tests

## Dashboard
- [ ] Overview metrics match database records
- [ ] Live operations show real job state and logs
- [ ] Agent monitor reflects actual agent state
- [ ] Tool Manager reflects actual installation/health
- [ ] Dashboard controls invoke real backend operations
- [ ] Findings, approvals, history, and audit pages work

## Reports and release
- [ ] PDF and Markdown reports work
- [ ] Reports use actual stored evidence
- [ ] Notifications work
- [ ] Scheduled passive monitoring respects scope/policy
- [ ] Automated tests pass or skipped tests are explicitly reported
- [ ] Security review and installation documentation complete
