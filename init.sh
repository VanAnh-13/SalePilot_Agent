#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "==> Working directory: $PWD"

if [ ! -f .env ]; then
  echo "==> Creating .env from .env.example"
  cp .env.example .env
fi

echo "==> Backend dependencies"
if [ ! -d backend/.venv ]; then
  python3 -m venv backend/.venv
fi
# shellcheck disable=SC1091
source backend/.venv/bin/activate
pip install -q -r backend/requirements.txt
(cd backend && python -m scripts.seed_db && python -m scripts.ingest_kb)

echo "==> Frontend dependencies"
if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm install)
fi

echo "==> Baseline verification"
./scripts/verify.sh

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
