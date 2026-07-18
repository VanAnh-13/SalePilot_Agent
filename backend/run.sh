.venv/bin/python -m uvicorn app.main:app \
  --env-file ../.env --reload --reload-dir app --host 0.0.0.0 --port 8000

