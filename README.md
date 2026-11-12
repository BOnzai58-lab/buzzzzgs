# BugHunter AI — Multi-Agent Team Kit

This repository is a multi-agent development kit for building **BUG HUNTER AI**, an AI-assisted bug bounty operations platform for explicitly authorized testing.

## Start here
1. Extract this archive into a new workspace.
2. Initialize git and make a baseline commit.
3. Open the folder in Google Antigravity (or a compatible coding agent).
4. Read `docs/MASTER_PROMPT.md` completely.
5. Read `docs/DASHBOARD_SPEC.md` and `docs/IMPLEMENTATION_PLAN.md`.
6. Open `team/KICKOFF.md` and start with the lead agent.
7. Follow `.agent/rules/team-protocol.md` and the ownership boundaries in `team/contracts/`.

## Key documents
- `docs/MASTER_PROMPT.md` — full build prompt and acceptance requirements.
- `docs/DASHBOARD_SPEC.md` — detailed real-time dashboard requirements.
- `docs/IMPLEMENTATION_PLAN.md` — phased checklist.
- `team/contracts/03-safety-rules.md` — mandatory authorization and safety controls.
- `team/contracts/00-architecture.md` — architecture and ownership.

## Team chat
```bash
python team/chat.py post --from recon --to lead --type question "Need Asset.source enum values"
python team/chat.py read --me lead
python team/chat.py log
```

Roles: `lead`, `scope`, `recon`, `scanner`, `triage`, `frontend`, `qa`, `human`, `all`.

## Important
- Only test assets explicitly authorized by a program owner.
- Use local OWASP Juice Shop for integration tests.
- Public accessibility does not imply permission.
- Tool integrations must report real installation/execution status.
- Dashboard statistics and controls must be connected to actual backend state.
- No automatic report submission, destructive testing, denial-of-service, credential attacks, or sensitive-data exfiltration.
- No tool guarantees findings or bounty earnings.

## Honest limits
The team chat coordinates agents by convention; it is not a security boundary. Backend scope enforcement, authentication, approvals, and audit logging must enforce all permissions.
