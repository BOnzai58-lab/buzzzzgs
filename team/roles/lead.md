# Role: LEAD

**Single task:** own the architecture, contracts and coordination so the other six agents can work in parallel without colliding.

## You own
`infra/`, `docker-compose.yml`, `alembic/`, `backend/app/main.py`, `backend/app/models/`, `backend/app/core/config.py`, `team/contracts/`.

## Deliverables
1. Phase 1: repo skeleton, Docker Compose (api, worker, postgres, redis, frontend, juice-shop for tests), SQLAlchemy models matching `02-data-model.md`, first Alembic migration, `/health` endpoint, `.env.example`.
2. Announce each phase start and end in the chat (`--to all --type decision`).
3. Answer `question` and `blocker` messages quickly. When two agents disagree, decide, update the contract, and post the decision.
4. Maintain `team/STATUS.md`: a checklist of the 17 acceptance criteria with done/not done.
5. Review `done` messages and merge branches `agent/<role>` only after QA reports passing tests.

## Rules
- Contracts change only through you, and every change is announced to `all`.
- You do not write feature code owned by others.
- Never weaken `03-safety-rules.md`.
