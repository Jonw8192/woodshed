# Test Evidence — Iteration 2 Build Candidate

All results below were executed against the packaged working tree unless explicitly marked pending.

## Backend verification

| Command | Result | Evidence |
|---|---|---|
| `cd backend && python -m compileall -q app tests` | PASS | `qa_evidence/compileall.txt` |
| `cd backend && pytest -q` | PASS — **61 passed** | final packaging log |
| `cd backend && pytest -q --cov=app --cov-branch --cov-report=term --cov-report=json=../qa_evidence/coverage.json` | PASS — **61 passed** | `qa_evidence/coverage.json`, final coverage log |
| `cd backend && alembic -c alembic.ini heads` | PASS — `0001_iteration2 (head)` | `qa_evidence/alembic_heads.txt` |

Measured coverage from the recorded branch-enabled run:

- Overall application: **82.0% line coverage**, **63.6% branch coverage**, **77.2% combined coverage.py display**.
- Domain/decision modules: **152/156 statements = 97.4% line coverage**.
- Domain/decision modules: **45/50 branches = 90.0% branch coverage**.
- This does **not** satisfy the final release target for every P0/P1 path; it is build-candidate evidence only.

## Analytical regression evidence

The 61-test suite includes the previous regression coverage plus Iteration 2 cases for:

- explicit `raw_stats` vs `fantasy_points` modes;
- rejection of incomplete raw-stat scoring inputs;
- preservation of compatible already-scored totals;
- incompatible scoring-fingerprint rejection;
- standard/half/full PPR and TEP effects;
- passing TD, first-down and yardage bonus semantics;
- ROS-only horizon enforcement;
- a Start/Sit TE-premium case where the recommendation flips;
- 1QB/Superflex trade context;
- TEP trade context;
- dynasty/redraft horizon effects;
- Superflex and TEP waiver context;
- League DNA draft-purpose separation;
- `Evidence Strength` terminology;
- production configuration validation;
- Retry-After seconds/date parsing;
- cache key-lock cleanup;
- deterministic bounded Guillotine probabilities.

## Guillotine concurrency/load probe

Executed command:

```bash
cd <repository-root>
python /tmp/load_guillotine.py
```

The script used the packaged `app.domain.guillotine` implementation with a semaphore bound equivalent to `SIMULATION_CONCURRENCY=2`.

Recorded parameters and results (`qa_evidence/guillotine_load.txt`):

- Requests: **20 concurrent jobs**
- Teams/request: **32**
- Simulations/request: **20,000**
- Concurrency bound: **2**
- Total elapsed: **0.2557 s**
- Throughput: **78.22 jobs/s**
- Latency p50: **143.60 ms**
- Latency p95: **249.56 ms**
- Latency p99: **249.56 ms**
- Event-loop lag p95: **0.827 ms**
- Peak process RSS: **130.42 MB**
- Errors: **0**

This is a local CPU/memory probe of the independent-normal `baseline_v1`; it is not predictive-model validation and is not a substitute for production HTTP load testing.

## Frontend dependency/build attempt

Executed:

```bash
cd frontend
npm install --package-lock-only --ignore-scripts --no-audit --no-fund
```

Result: **BLOCKED by available registry**. The configured registry returned HTTP 404 for `next@15.4.6`. See `qa_evidence/npm_lock_attempt.txt`.

No `package-lock.json` was fabricated. Frontend clean install/build/browser claims remain pending.

## Python environment check

`python -m pip check` reported a global-environment `moviepy`/`pillow` conflict unrelated to the Woodshed dependency set. This environment is shared and not a clean project virtualenv, so that result is not treated as a Woodshed dependency pass or failure. A clean locked install is queued externally.

## Tools unavailable in this environment

The following required tools/services were not available and therefore have no fabricated result:

- `ruff`
- `mypy`
- Docker CLI / Docker daemon
- `psql` / disposable PostgreSQL
- disposable Redis service
- Playwright/browser runtime
- accessibility/visual-regression tooling
- container vulnerability scanner
- production deployment target and credentials

Exact follow-up commands and success conditions are in `EXTERNAL_VERIFICATION_QUEUE.md`.
