# Woodshed Runbook — Build Candidate

## Backend local verification
```bash
cd backend
python -m compileall -q app tests
pytest -q
pytest -q --cov=app --cov-branch --cov-report=term --cov-report=json=../qa_evidence/coverage.json
alembic -c alembic.ini heads
```

## Backend runtime
```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- `GET /live` = process liveness.
- `GET /ready` = environment-aware dependency readiness.

## Environment
Copy `backend/.env.example` to `backend/.env` only in the target environment and supply real runtime secrets through the platform secret manager. Never commit the resulting `.env`.

Production policy flags:
- `DATABASE_REQUIRED`
- `REDIS_REQUIRED`
- `SLEEPER_REQUIRED`
- `AI_ENABLED`
- `SIMULATION_CONCURRENCY`
- `RATE_LIMIT_PER_MINUTE`
- `BODY_LIMIT_BYTES`
- `TRUSTED_PROXY_IPS`

`ACCOUNT_API_KEYS` is a build-candidate bootstrap mechanism, not the final recommended consumer identity system.

## Frontend
A real `package-lock.json` must be generated in an environment where the declared registry can resolve dependencies:
```bash
cd frontend
npm install --package-lock-only --ignore-scripts
npm ci
npm run build
```

## Database migrations
The candidate uses Alembic:
```bash
cd backend
alembic -c alembic.ini upgrade head
alembic -c alembic.ini downgrade base
alembic -c alembic.ini upgrade head
```
Execute only against a disposable DB until the migration transition is validated.

## Compose
A frontend lockfile is required first.
```bash
cp backend/.env.example backend/.env
# configure disposable values

docker compose build --no-cache
docker compose up -d
docker compose ps
```
Only gateway port 8080 should be exposed.

## Observe
Correlate requests with `X-Request-ID`. Alert on readiness failures, 5xx rate, Sleeper 429/5xx, cache degraded status, rate-limit failures, simulation queueing, DB pool pressure, and latency/error regressions.

## Backup / restore / rollback
Exact disposable verification commands are in `EXTERNAL_VERIFICATION_QUEUE.md`. Production should use immutable releases, managed Postgres backups/PITR where available, and an explicitly recorded rollback target.
