#!/usr/bin/env bash
set -euo pipefail

# Shell entrypoints are pinned to LF in .gitattributes for Windows checkouts.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "==> Working directory: $PWD"

echo "==> Agent scope guard"
python3 scripts/validate_agent_scope.py

if [ ! -f .env ]; then
  echo "==> Creating .env from .env.example"
  cp .env.example .env
fi

echo "==> Backend dependencies"
if [ ! -d backend/.venv ]; then
  python3 -m venv backend/.venv
fi
# shellcheck disable=SC1091
# Support both POSIX venvs (.venv/bin/activate) and Windows venvs
# (.venv/Scripts/activate) — python -m venv lays these out differently per
# platform (2026-08-01: this used to unconditionally source bin/activate,
# which does not exist on Windows and would hard-fail under set -euo pipefail).
if [ -f backend/.venv/bin/activate ]; then
  source backend/.venv/bin/activate
elif [ -f backend/.venv/Scripts/activate ]; then
  source backend/.venv/Scripts/activate
else
  echo "ERROR: no venv activation script found under backend/.venv" >&2
  exit 1
fi
pip install -q -r backend/requirements.txt
(cd backend && python -m scripts.seed_db && python -m scripts.ingest_kb)

echo "==> Frontend dependencies"
if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm install)
fi

echo "==> Baseline verification"
./scripts/verify.sh

echo "==> Record agent session scope"
python3 scripts/validate_agent_scope.py --start-session

echo "==> Startup commands (run in two terminals)"
echo "    Backend:  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000"
echo "    Frontend: cd frontend && npm run dev"
echo "    UI: http://localhost:3000  API: http://localhost:8000/docs"

if [ "${RUN_START_COMMAND:-0}" = "1" ]; then
  echo "==> Starting backend only (RUN_START_COMMAND=1)"
  cd backend
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000
fi

echo "Set RUN_START_COMMAND=1 to launch backend from init.sh."
