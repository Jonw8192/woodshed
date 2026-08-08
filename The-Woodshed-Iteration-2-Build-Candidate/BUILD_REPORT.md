# Build Report — Iteration 2 Build Candidate

## Outcome

The current working tree was preserved and packaged as a build candidate. It is **NOT READY** for deployment because mandatory external/infrastructure/browser/data gates remain unverified or intentionally gated.

## Local executable evidence

- Python compile: PASS.
- Backend: **61/61 tests PASS**.
- Overall coverage: **82.0% line / 63.6% branch** (77.2% combined display).
- Domain modules: **97.4% line / 90.0% branch**.
- Alembic static head discovery: `0001_iteration2 (head)`.
- Guillotine local concurrency probe: 20 requests, 32 teams/request, 20,000 simulations/request, concurrency bound 2; 0 errors; see `qa_evidence/guillotine_load.txt`.
- Frontend lock generation attempt: blocked by configured registry 404 for Next.js; no lockfile fabricated.

See `TEST_EVIDENCE.md` for commands and `IMPLEMENTATION_STATUS.md` for requirement mapping.
