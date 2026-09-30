#!/usr/bin/env bash
set -euo pipefail

# Detect the correct venv python path (POSIX vs Windows).
if [ -f .venv/bin/python ]; then
  VENV_PYTHON=.venv/bin/python
elif [ -f .venv/Scripts/python.exe ]; then
  VENV_PYTHON=.venv/Scripts/python.exe
else
  echo "ERROR: no venv python found under .venv" >&2
  exit 1
fi

exec $VENV_PYTHON -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --env-file ../.env
