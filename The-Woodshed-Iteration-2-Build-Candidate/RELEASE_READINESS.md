# Release Readiness — Iteration 2 Build Candidate

**Current verdict: NOT READY**

This archive preserves the completed Iteration 2 working tree and verified local evidence. It is deliberately labeled a **build candidate**, not a deployment-ready release.

## Implemented and verified locally

- 61/61 backend tests pass.
- Python application/tests compile.
- Branch-enabled coverage was recorded; domain/decision modules measure 97.4% line and 90.0% branch coverage.
- Projection modes/scoring semantics fix the QA partial-stat defect.
- Start/Sit demonstrates a TEP-driven recommendation flip.
- Trade and Waiver primitives respond to SF/TEP/horizon context.
- League DNA separates purpose/mechanic and uses Evidence Strength.
- Guillotine seed/bounds/Monte Carlo output and bounded execution are implemented; a 20-request max-size local probe completed without error.
- Application-lifetime Sleeper HTTP lifecycle, typed provider errors, Retry-After parsing, cache coalescing/cleanup, readiness policy and Redis-capable rate limiting are present.
- Canonical schemas/persistence models, an authenticated durable import endpoint and Alembic baseline are present and compile.
- Fake/sample players were removed from production frontend paths; source-dependent tools are explicitly gated.

## Implemented but not executable in this environment

- Frontend lock generation / `npm ci` / Next production build: configured registry returns 404 for `next@15.4.6`.
- Alembic real PostgreSQL up/down/up and persistence integration.
- Redis distributed integration/failure drills.
- Docker/Compose build/runtime/container scans.
- Browser E2E/accessibility/visual regression.
- Clean dependency audits in isolated frontend/backend environments.

## Disabled pending authorized external data

- Consumer ROS Rankings, Start/Sit, Waiver and projected-remaining Guillotine experiences that require current projections.
- Consumer Trade Analyzer market-vs-projection workflow that requires an authorized market-value source.
- Historical ADP League DNA traits.
- Historical team-at-event / Team Homer traits.
- Injury/availability claims.
- Public AI feature (disabled by default; full entitlement/quota/claim governance is incomplete).

## Requiring deployment credentials/infrastructure

- staging/production deployment;
- managed Postgres/Redis;
- TLS/public routing verification;
- monitoring/alert validation;
- backup/restore and platform rollback.

## Remaining application defects / release-engineering work

- Full lineup optimization is not implemented.
- Decision routes are not yet universally wired to persisted ModelRun/DataLineage/Recommendation records.
- Full authenticated consumer sign-in/session UX and comprehensive cross-tenant integration tests remain.
- Current Alembic revision is a canonical baseline; upgrade compatibility from the prior pre-release SQL schema needs a real migration drill and may require a dedicated transition revision.
- Frontend lint/type/component/Playwright/accessibility/visual test infrastructure is not yet locked and verified.
- Full transitive dependency locks are absent and intentionally not fabricated.
- Predictive model calibration/backtesting cannot be claimed without authorized historical outcome/snapshot data.

See `IMPLEMENTATION_STATUS.md`, `TEST_EVIDENCE.md`, `EXTERNAL_VERIFICATION_QUEUE.md`, and `DATA_INTEGRATION_REQUIREMENTS.md`.
