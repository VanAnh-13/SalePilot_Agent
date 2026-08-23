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
| `scripts/validate_agent_scope.py` | WIP, whitelist, and protected-file guard |

## Startup workflow

Before writing code:

1. Confirm working directory with `pwd` (expect repo root).
2. Read `claude-progress.md` for latest verified state and next step.
3. Run `python3 scripts/validate_agent_scope.py` to validate harness state.
4. Choose the **highest-priority actionable** feature. Skip `blocked` features until their blocker is resolved.
5. Before source edits, set exactly that feature to `in_progress` and declare its `allowed_files` in `feature_list.json`.
6. If a protected file is required, get explicit user approval and list its exact path in `approved_protected_files`.
7. Review recent commits if git exists: `git log --oneline -5`.
8. Run `./init.sh` (or at least the verification path below).
9. Run smoke verification before stacking new feature work.

If baseline verification is already failing, **fix that first**.

## Working rules

- Work on **one feature at a time**. `feature_list.json` enforces WIP <= 1.
- Finish and test the active feature before starting another feature.
- Do not mark a feature `passing` just because code was added. Required tests must pass and evidence must be recorded.
- Keep changes within the selected feature unless a narrow blocker fix is required.
- Do not refactor, rename, reformat, or clean up unrelated modules.
- Edit only paths matched by the active feature's `allowed_files`.
- Never edit paths matched by `sensitive_files_never_edit`.
- Edit a protected path only when the user explicitly approved it and the exact path is listed in `approved_protected_files`.
- Do not silently change verification rules during implementation.
- Prefer durable repo artifacts (`feature_list.json`, `claude-progress.md`) over chat summaries.
- Do **not** re-introduce third-party product branding the user forbade.
- Keep Vietnamese UX strings for customer-facing chat unless asked otherwise.
- Backend: Python 3.12 target in Docker; local may be 3.12+. Frontend: Node 20+.

## Scope lock and whitelist

`feature_list.json` is the policy source of truth. Every `in_progress` feature must define a narrow `allowed_files` list of exact file paths. `feature_list.json` and `claude-progress.md` are always writable for lifecycle state, but that exception does not permit unrelated content changes.

Before editing, validate planned paths:

```bash
python3 scripts/validate_agent_scope.py --feature-id <feature-id> \
  --check-files path/to/file another/file
```

The guard applies in this order:

1. Sensitive path match: always deny.
2. Missing from feature whitelist: deny.
3. Protected path without exact user-approved entry: deny.
4. Otherwise: allow for the active feature only.

Protected approvals are pinned by feature in the guard implementation. Adding an approval only to `feature_list.json` is not sufficient. Generated dependency, cache, database, and log artifacts are excluded from source-scope hashing; agents must not edit those artifacts directly.

`./init.sh` records a hash baseline under `.git/`. Before handoff, `python3 scripts/validate_agent_scope.py --check-session` verifies every file changed since that baseline.

If an additional file becomes necessary, stop, add its exact path to `allowed_files`, then rerun `python3 scripts/validate_agent_scope.py --start-session` before editing it. The command checks the previous scope before refreshing the baseline. Wildcards are forbidden in feature allowlists and protected-file approvals.

If the guard detects a concurrent change that the user owns, stop and ask. Only after confirmation, preserve it with `--accept-external-files <exact-path>`; sensitive and protected paths cannot use this exception.

## Architecture constraints

- Multi-agent: Lead orchestrates via `delegate` / `finalize`; specialists: catalog, knowledge, crm, order, escalation.
- Channels: Web only (the Zalo stub was removed by owner decision; no other channels unless explicitly requested).
- Offline path must keep working without API keys (`backend/app/agent/offline.py`).
- Do not break `/health`, seed, or chat smoke paths.

## Verification commands (feedback subsystem)

```bash
# Install / baseline
./init.sh

# Harness and scope guard
python3 scripts/validate_agent_scope.py --self-test
python3 scripts/validate_agent_scope.py

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
3. All required tests pass. A failed or skipped required test means the feature is not done.
4. The final changed-file set passes `validate_agent_scope.py --check-files ...`.
5. The diff contains no unrelated refactor or cleanup.
6. Evidence is recorded in `feature_list.json` and/or `claude-progress.md`.
7. Repo remains restartable via `./init.sh` and standard start commands.

## End of session

1. Run the active feature's tests and inspect the failure logs before changing code again.
2. Run `python3 scripts/validate_agent_scope.py --check-session` and the scope guard against every file changed in this session.
3. Review the diff as the checker; use an independent checker agent when available.
4. Update `claude-progress.md` and `feature_list.json` with status and test evidence.
5. Mark the feature `passing` only after every required check passes; otherwise leave it `in_progress` or `blocked`.
6. Optionally fill `session-handoff.md`.
7. Run `clean-state-checklist.md`.
8. Commit only if the user asked; leave a clean restartable state either way.

## Deep docs (read on demand)

- `docs/ARCHITECTURE.md` — multi-agent layout
- `docs/DEMO_SCRIPT.md` — pitch path
- `docs/PIVOT_PLAYBOOK.md` — VAIC problem drop
- `docs/HARNESS.md` — harness map + patterns + lecture links
