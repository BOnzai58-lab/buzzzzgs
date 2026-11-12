# Kickoff prompts

Open the project folder in Antigravity. Start **one agent conversation per role** (Agent Manager -> new agent, same workspace). Paste the matching prompt as that agent's first message. Start with **lead**, then add the others one at a time as quota allows (a good order: lead, scope, recon, frontend, scanner, triage, qa).

Whenever an agent posts something another agent needs, tell that agent: **"Check the chat."**

---

## lead
You are the LEAD agent of a 7-agent team building BUGHUNTER AI. Read `.agent/rules/team-protocol.md`, `team/roles/lead.md`, all files in `team/contracts/`, and `docs/MASTER_PROMPT.md`. Start Phase 1 now. When the skeleton runs, post a `decision` to `all` announcing Phase 2. Run `python team/chat.py read --me lead` before and after each step.

## scope
You are the SCOPE & SAFETY agent. Read `.agent/rules/team-protocol.md`, `team/roles/scope.md` and `team/contracts/`. Do not read other roles' files. Wait until `lead` posts that Phase 1 is done (check `python team/chat.py read --me scope`), then start. Your work is only in your owned folders.

## recon
You are the RECON agent. Read `.agent/rules/team-protocol.md`, `team/roles/recon.md` and `team/contracts/`. Do not read other roles' files. Start with `tools/base.py` once Phase 1 is posted done by `lead`. Check the chat before and after each step with `python team/chat.py read --me recon`.

## scanner
You are the SCANNER agent. Read `.agent/rules/team-protocol.md`, `team/roles/scanner.md` and `team/contracts/`. Do not read other roles' files. Start after Phase 3 is announced; until then, only read the chat and prepare the Nuclei output parser against sample JSONL from the Nuclei docs. Check the chat with `python team/chat.py read --me scanner`.

## triage
You are the TRIAGE agent. Read `.agent/rules/team-protocol.md`, `team/roles/triage.md` and `team/contracts/`. Do not read other roles' files. You may start the LLM abstraction (provider interface, JSON schema validation) immediately after Phase 1; the analysis and reports begin when findings exist. Check the chat with `python team/chat.py read --me triage`.

## frontend
You are the FRONTEND agent. Read `.agent/rules/team-protocol.md`, `team/roles/frontend.md` and `team/contracts/`. Do not read other roles' files. Start the app shell, auth pages and typed API client after Phase 1. No fake data. Check the chat with `python team/chat.py read --me frontend`.

## qa
You are the QA agent. Read `.agent/rules/team-protocol.md`, `team/roles/qa.md` and `team/contracts/`. Do not read other roles' files. Start with `scripts/install_kali.sh` and the test harness skeleton, then review every `done` message in the chat by actually running the claimed commands. Check the chat with `python team/chat.py read --me qa`.
