# The Woodshed — Iteration 2 Build Candidate

The Woodshed is a FastAPI + Next.js fantasy-football decision platform built around **Process Over Hype**. This tree is a **build candidate**, not a deployment-ready release.

## Verified locally in this package

- FastAPI backend imports and compiles on Python 3.13 in the available environment.
- 61/61 backend tests pass.
- Overall measured backend coverage: 82.0% line / 63.6% branch (77.2% combined display) with branch measurement enabled.
- Decision/domain modules: 97.4% line coverage and 90.0% branch coverage in the recorded run.
- Explicit `fantasy_points` vs `raw_stats` projection contracts prevent partial-stat projection corruption.
- Central scoring engine is used by ROS rankings and Start/Sit, with scoring context used in Trade and Waiver decision primitives.
- League DNA separates draft purpose from draft mechanic and uses `Evidence Strength` rather than claiming calibrated confidence.
- Guillotine Monte Carlo is deterministic for a fixed seed and is bounded by an application simulation semaphore.
- Sleeper uses a shared application-lifetime HTTP client, per-process concurrency control, caching/coalescing, typed errors, and Retry-After parsing.
- Canonical schemas, persistence models, authenticated durable league-import endpoint, environment-aware readiness policy, and Redis-capable rate limiting are present.
- Production frontend paths contain no fake/sample players; data-dependent tools are visibly gated when authorized external projections/market data are unavailable.

## Current verdict

**NOT READY**. See `IMPLEMENTATION_STATUS.md`, `EXTERNAL_VERIFICATION_QUEUE.md`, `KNOWN_LIMITATIONS.md`, and `TEST_EVIDENCE.md`.

The current environment cannot complete the frontend dependency lock/build, Docker/Compose, PostgreSQL/Redis integration, browser/accessibility, container/security, backup/restore, or production deployment gates. No result for those gates is claimed.

## Backend local verification

```bash
cd backend
python -m compileall -q app tests
pytest -q
pytest -q --cov=app --cov-branch --cov-report=term --cov-report=json=../qa_evidence/coverage.json
alembic -c alembic.ini heads
```

## Frontend

A frontend lockfile is intentionally **not fabricated**. In an environment with registry access:

```bash
cd frontend
npm install --package-lock-only --ignore-scripts
npm ci
npm run build
```

See `EXTERNAL_VERIFICATION_QUEUE.md` for the complete verification cycle.

## Data truthfulness

League and draft data are available from Sleeper's public read-only API. Consumer Trade, Waiver, ROS, Start/Sit, and projected-remaining Guillotine experiences remain gated until authorized projection/market inputs are connected. The backend analytical primitives accept explicit sourced inputs for testing/integration, but the frontend does not seed fabricated player data.
