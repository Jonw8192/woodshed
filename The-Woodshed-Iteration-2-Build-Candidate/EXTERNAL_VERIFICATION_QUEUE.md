# External Verification Queue

Run these commands from a fresh copy of this build candidate in the target verification environment. Do not change the verdict to READY unless all mandatory gates pass.

## 1. Frontend lockfile and clean install

```bash
cd frontend
rm -rf node_modules .next
npm install --package-lock-only --ignore-scripts
npm ci
```

Success conditions: `package-lock.json` is generated from `package.json`, committed into the verification tree, `npm ci` exits 0 from an empty `node_modules`, and no undeclared local package state is required.

## 2. Frontend production build

Current repository command:

```bash
cd frontend
npm run build
```

Success: Next.js production build exits 0 with no missing `@/*` imports or runtime compilation errors.

### Frontend lint/type/component test infrastructure

The build candidate does not yet contain a verified ESLint/component-test/Playwright dependency set because the current registry cannot resolve Next.js. After registry access is restored, add those tools through normal package management so they are recorded in the real lockfile; then run repository scripts created in that verification commit. This is a **remaining application/release-engineering task**, not a completed gate in this archive.

## 3. Playwright / accessibility / visual regression

After adding verified Playwright + accessibility dependencies to the real lockfile, execute the configured repository test commands against a running production build. Minimum success conditions:

- landing page loads;
- Sleeper league import path works;
- selected league persists across navigation;
- League DNA renders without raw JSON;
- gated tools show truthful unavailable states when feeds are absent;
- no cross-account league access;
- desktop and mobile navigation pass;
- keyboard-only critical paths pass;
- automated accessibility scan has no serious/critical violations;
- reviewed visual snapshots do not show regressions.

This candidate intentionally does not invent commands for scripts that are not yet present.

## 4. PostgreSQL migration up/down/up

From repository root with a disposable database:

```bash
export DATABASE_URL='postgresql+asyncpg://woodshed:woodshed@127.0.0.1:5432/woodshed_test'
cd backend
alembic -c alembic.ini upgrade head
alembic -c alembic.ini downgrade base
alembic -c alembic.ini upgrade head
```

Success: all three commands exit 0, expected canonical tables/constraints/indexes exist after the final upgrade, and no data is touched outside the disposable database.

Previous Iteration 2 schema upgrade compatibility remains a separate migration-hardening check because the candidate migration is a canonical baseline.

## 5. PostgreSQL integration tests

After the disposable DB is healthy:

```bash
cd backend
DATABASE_URL="$DATABASE_URL" DATABASE_REQUIRED=true pytest -q
```

Success: all tests pass plus dedicated repository/import authorization tests added for the real database path. Current in-memory/unit suite alone is insufficient for this gate.

## 6. Redis integration

Start disposable Redis, then:

```bash
export REDIS_URL='redis://127.0.0.1:6379/15'
cd backend
REDIS_URL="$REDIS_URL" REDIS_REQUIRED=true pytest -q
```

Add/run integration cases for atomic rate limits, fail-closed behavior, cache stampede/coalescing, degraded status, and restart behavior. Success requires atomic limits across multiple API processes.

## 7. Docker/Compose clean build

A frontend lockfile must exist first.

```bash
cp backend/.env.example backend/.env
# Set disposable, non-secret test values in backend/.env.
docker compose build --no-cache
docker compose up -d
sleep 10
docker compose ps
curl -fsS http://127.0.0.1:8080/live
curl -fsS http://127.0.0.1:8080/api/v1/league/INVALID || true
```

Success: all containers build from scratch, Postgres/Redis become healthy, API/web/gateway remain healthy, `/live` responds, API is not directly exposed on a host port, and logs show no startup exceptions.

## 8. Readiness dependency matrix

Against Compose or staging, verify:

```bash
curl -fsS http://127.0.0.1:8080/ready
# stop Redis, repeat
# restore Redis; stop Postgres, repeat
# restore Postgres; simulate required Sleeper failure, repeat
```

Success: overall readiness is false exactly when a configured **required** dependency fails or is unconfigured; optional dependency failures are reported separately without being hidden.

## 9. Dependency audits

Backend clean environment:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e 'backend[dev]'
pip-audit
```

Frontend after real lock generation:

```bash
cd frontend
npm ci
npm audit --audit-level=high
```

Success: no exploitable critical/high findings, or an explicit time-bounded exception is documented.

## 10. Container scan

```bash
docker build -f Dockerfile.api -t woodshed-api:i2 .
docker build -f Dockerfile.web -t woodshed-web:i2 .
trivy image --exit-code 1 --severity CRITICAL,HIGH woodshed-api:i2
trivy image --exit-code 1 --severity CRITICAL,HIGH woodshed-web:i2
```

Success: no exploitable critical/high finding without documented exception.

## 11. Backup / restore

With disposable Compose data:

```bash
docker compose exec -T postgres pg_dump -U woodshed -Fc woodshed > /tmp/woodshed-i2.dump
docker compose exec -T postgres createdb -U woodshed woodshed_restore
docker compose exec -T postgres pg_restore -U woodshed -d woodshed_restore --clean --if-exists < /tmp/woodshed-i2.dump
```

Success: restore exits 0 and canonical row counts / sample imported league state match the source DB.

## 12. Production deployment

Use the target platform's documented deployment command with the **verified** immutable image/revision. Requirements before promotion:

- real frontend/backend locks committed;
- migrations pass;
- secrets injected by platform secret manager;
- required DB/Redis/provider settings validate;
- AI remains disabled unless its full entitlement/governance gate is separately passed;
- rollback target recorded.

The exact cloud-specific deploy command cannot be supplied by this repository because no deployment target was provided.

## 13. Post-deployment smoke

Against the actual public base URL:

```bash
curl -fsS https://<host>/live
curl -fsS https://<host>/ready
curl -fsSI https://<host>/
```

Then run the verified browser/E2E suite against `https://<host>` and inspect logs/metrics/alerts.

Success: TLS/routing/security headers/auth, DB/Redis connectivity, Sleeper import, League DNA, and every **enabled** tool pass with no uncaught server/browser errors.

## 14. Rollback validation

Execute the platform-specific rollback to the previously recorded immutable release, verify `/live` and `/ready`, then re-promote the candidate only if rollback and forward migration strategy are both proven.
