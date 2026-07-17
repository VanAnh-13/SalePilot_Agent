# AGENTS.md — SalePilot

This repository is designed for long-running coding-agent work (VAIC 2026 hackathon base).
The goal is not to maximize raw code output. The goal is to leave the repo in a state where
the next session can continue without guessing.

**Harness model (5 subsystems):** Instructions · Tools · Environment · State · Feedback  
Reference: [Learn Harness Engineering](https://walkinglabs.github.io/learn-harness-engineering/en/)

**Context files:** this root file plus progressive maps in `backend/AGENTS.md` and `frontend/AGENTS.md`.  
**Product skills:** `backend/app/agent/skills/*/SKILL.md` (portable skill format).

## Project map

| Path | Role |
|------|------|
| `backend/` | FastAPI + LangGraph multi-agent (Lead + sub-agents) |
| `frontend/` | Next.js chat, Agent Trace, dashboard |
| `docs/` | Architecture, demo, Zalo, pivot, harness |
| `feature_list.json` | Feature state (source of truth) |
| `claude-progress.md` | Session log + verified state |
| `init.sh` | Install + baseline verify |

## Startup workflow

Before writing code:

1. Confirm working directory with `pwd` (expect repo root).
2. Read `claude-progress.md` for latest verified state and next step.
3. Read `feature_list.json` and choose the **highest-priority unfinished** feature (`status != passing`).
4. Review recent commits if git exists: `git log --oneline -5`.
5. Run `./init.sh` (or at least the verification path below).
6. Run smoke verification before stacking new feature work.

If baseline verification is already failing, **fix that first**.

## Working rules

- Work on **one feature at a time** (only one `in_progress` in `feature_list.json`).
- Do not mark a feature `passing` just because code was added — evidence required.
- Keep changes within the selected feature unless a narrow blocker fix is required.
- Do not silently change verification rules during implementation.
- Prefer durable repo artifacts (`feature_list.json`, `claude-progress.md`) over chat summaries.
- Do **not** re-introduce third-party product branding the user forbade.
- Keep Vietnamese UX strings for customer-facing chat unless asked otherwise.
- Backend: Python 3.12 target in Docker; local may be 3.12+. Frontend: Node 20+.

## Architecture constraints

- Multi-agent: Lead orchestrates via `delegate` / `finalize`; specialists: catalog, knowledge, crm, order, escalation.
- Channels: Web + Zalo stub only (no Feishu/Slack/Telegram unless explicitly requested).
- Offline path must keep working without API keys (`backend/app/agent/offline.py`).
- Do not break `/health`, seed, or chat smoke paths.

## Verification commands (feedback subsystem)

```bash
# Install / baseline
./init.sh

# Backend smoke (from repo root)
./scripts/verify.sh

# Manual API smoke (backend running on :8000)
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Gia đình 4 người cần tủ lạnh dưới 15 triệu, ngang tối đa 70 cm","external_id":"verify","channel":"web"}'
```

## Definition of done

A feature is done only when all are true:

1. Target user-visible behavior is implemented.
2. Required verification actually ran.
3. Evidence is recorded in `feature_list.json` and/or `claude-progress.md`.
4. Repo remains restartable via `./init.sh` and standard start commands.

## End of session

1. Update `claude-progress.md`.
2. Update `feature_list.json` statuses + evidence.
3. Optionally fill `session-handoff.md`.
4. Run `clean-state-checklist.md`.
5. Commit only if the user asked; leave a clean restartable state either way.

## Deep docs (read on demand)

- `docs/ARCHITECTURE.md` — multi-agent layout
- `docs/DEMO_SCRIPT.md` — pitch path
- `docs/ZALO_INTEGRATION.md` — OA stub → real
- `docs/PIVOT_PLAYBOOK.md` — VAIC problem drop
- `docs/HARNESS.md` — harness map + patterns + lecture links
