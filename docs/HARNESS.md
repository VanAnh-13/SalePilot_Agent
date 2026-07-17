# Harness map — SalePilot

Based on [Learn Harness Engineering](https://walkinglabs.github.io/learn-harness-engineering/en/)  
(Lectures: [Why agents fail](https://walkinglabs.github.io/learn-harness-engineering/en/lectures/lecture-01-why-capable-agents-still-fail/) · [What a harness is](https://walkinglabs.github.io/learn-harness-engineering/en/lectures/lecture-02-what-a-harness-actually-is/) · [Feature lists](https://walkinglabs.github.io/learn-harness-engineering/en/lectures/lecture-08-why-feature-lists-are-harness-primitives/) · [Clean state](https://walkinglabs.github.io/learn-harness-engineering/en/lectures/lecture-12-why-every-session-must-leave-a-clean-state/))

Templates adapted from the course [resource library](https://walkinglabs.github.io/learn-harness-engineering/en/resources/templates/).

## Five subsystems in this repo

| Subsystem | Repo artifacts |
|-----------|----------------|
| **Instructions** | Root `AGENTS.md` + nested `backend/AGENTS.md` / `frontend/AGENTS.md` (progressive context) + `docs/*` |
| **Tools** | shell, pip/npm, curl; product tools under `backend/app/agent/tools/` |
| **Environment** | `.env.example`, `backend/Dockerfile`, `docker-compose.yml`, `init.sh` |
| **State** | `claude-progress.md`, `feature_list.json`, `session-handoff.md` |
| **Feedback** | `./scripts/verify.sh`, manual API/UI checks, `evaluator-rubric.md` |

## Core agent patterns (host-agnostic)

These patterns work with any coding agent that reads the repo:

| Pattern | In this repo |
|---------|----------------|
| **Context files** | `AGENTS.md` at root; subdirectory maps for progressive discovery |
| **Portable skills** | `backend/app/agent/skills/*/SKILL.md` + `activate_skill` progressive load |
| **Isolated + parallel sub-agents** | `delegate` / `delegate_many` → short summaries only |
| **Customer memory** | SQLite per channel+external_id; inject each turn |
| **Channel bus** | `gateway.ingest_message` for Web + Zalo |
| **Scheduler** | Follow-up jobs + background loop |
| **Safe execution** | Sandbox whitelist + web fetch with SSRF guards |
| **Trajectory** | JSON runs under `data/trajectories/` |
| **Session continuity (coding)** | `claude-progress.md` + `feature_list.json` |
| **Verification loop** | `./scripts/verify.sh` before marking features `passing` |

## Session loop

1. Read progress + feature list  
2. `./init.sh` / verify baseline  
3. One feature only  
4. Run verification + record evidence  
5. Update progress + clean-state checklist  

## Two layers (do not collapse)

| Layer | Role |
|-------|------|
| **Repo harness** | Constrains *coding agents* editing this codebase |
| **Product multi-agent** | Lead + specialists for SME customers (`backend/app/agent/`) |

Both need explicit verification and durable state files.
