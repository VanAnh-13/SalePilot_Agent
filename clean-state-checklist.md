# Clean State Checklist

- [x] The standard startup path still works (`./init.sh` or documented uvicorn + npm).
- [x] The standard verification path still runs (`./scripts/verify.sh`).
- [x] Current progress is recorded in `claude-progress.md`.
- [x] Feature state in `feature_list.json` reflects what is actually passing versus unverified.
- [x] No half-finished step is left undocumented.
- [x] The next session can continue without manual repair.
- [x] No secrets committed (`.env` gitignored).
