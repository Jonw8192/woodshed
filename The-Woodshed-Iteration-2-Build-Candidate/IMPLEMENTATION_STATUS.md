# Implementation Plan 2 — Build Candidate Status

Status vocabulary:
- **Completed / verified** — implemented and executed successfully in this tree.
- **Partially completed** — meaningful implementation exists but a required product path or release gate remains.
- **Environment-verification pending** — implementation/configuration exists, but the current environment lacks the required runtime/tool/service.
- **External-data pending** — intentionally disabled in consumer UI until an authorized source is connected.
- **Remaining defect** — application work still required; not an environment excuse.

| Requirement | Status | Code / tests / evidence |
|---|---|---|
| Preserve FastAPI/Next.js separation and Woodshed branding | Completed / verified (source inspection) | `backend/app/main.py`, `frontend/app/*`, `frontend/components/Logo.jsx` |
| Untouched Iteration 2 baseline captured before changes | Completed / verified | prior RC evidence retained; current candidate evidence in `qa_evidence/` |
| Explicit raw-stat vs already-scored projections | Completed / verified | `backend/app/schemas/fantasy.py`; `tests/test_iteration2.py` 09–16 |
| Never discard a total because one partial stat is present | Completed / verified | discriminated projection union; test 12 rejects mixed payload |
| Compatible scoring fingerprint on already-scored projections | Completed / verified | `domain/scoring.py`, `domain/rankings.py`, `domain/start_sit.py`; tests 11,13,16 |
| Central scoring service | Completed / verified | `backend/app/domain/scoring.py`; tests 01–10 |
| PPR / half PPR / TEP / pass / rush / receive / 2PT / fumble / selected first-down and yardage bonuses | Completed / verified | `ScoringSettings`, `score_raw_projection`; tests 03–08 |
| Superflex modeled as lineup demand/eligibility rather than a scoring multiplier | Completed / verified for current primitives | Start/Sit eligibility + Trade/Waiver replacement-demand context; tests 19,21,25 |
| ROS endpoint enforces ROS horizon | Completed / verified | `RankingsRequest.ros_only`; original + Iteration 2 tests |
| ROS source/update/quality/scoring context | Completed / verified in engine output | `domain/rankings.py` |
| Start/Sit responds to league scoring and TEP | Completed / verified | `domain/start_sit.py`; test 17 demonstrates recommendation flip |
| Start/Sit legal slot validation | Completed / verified for QB/RB/WR/TE/FLEX/SUPERFLEX | `domain/start_sit.py`; original tests + 18–20 |
| Whole-lineup optimization | Remaining defect | pair/candidate decision engine exists; full lineup optimizer not yet implemented |
| Trade responds to 1QB/SF, TEP, dynasty/redraft context | Completed / verified at decision-primitive level | `domain/trades.py`; tests 21–24 |
| Trade uses actual imported rosters, replacement pool, picks, both-team effects | Partially completed | schema supports context primitives; full league-to-trade consumer workflow remains |
| Waiver scoring context / SF / TEP | Completed / verified at decision-primitive level | `domain/waivers.py`; tests 25–27 |
| Waivers load actual unrostered players and legal drops automatically | External-data / integration pending | ownership is available from Sleeper, but consumer tool is gated pending authorized projections |
| Guillotine deterministic seed / MC error / 2–32 teams | Completed / verified | `domain/guillotine.py`; original tests |
| Guillotine off-event-loop and bounded workload | Completed / verified | `api/routes/tools.py`, `SIMULATION_CONCURRENCY`; `qa_evidence/guillotine_load.txt` |
| Advanced player/game correlation simulation | External-data / model-validation pending | baseline independent-normal model retained and documented |
| League DNA same-window baseline and dominant-position bug fix | Completed / verified | `domain/league_dna.py`; original tests |
| Exclude drafting drafts | Completed / verified | Sleeper ingestion and DNA filtering |
| Separate draft purpose from mechanic | Completed / verified for mapping logic | `integrations/sleeper.py`, schema; tests 28–30 |
| Historical Team Homer truthfulness | Completed / verified as unavailable | no current-team backfill; output explicitly unavailable |
| Historical ADP traits truthfulness | Completed / verified as unavailable without dated source | DNA output coverage flag and unavailable market style |
| Evidence Strength replaces calibrated-confidence claim | Completed / verified | `domain/league_dna.py`; test 31 |
| Robust cross-season manager identity and traded-pick attribution | Partially completed | season-qualified fallback IDs + attribution quality; full provider-proven pick ownership history is not yet complete |
| Canonical schemas | Completed / source compiled | `backend/app/schemas/canonical.py` |
| Canonical persistence models | Completed / source compiled | `backend/app/data/models.py` |
| Provider connection / account / user / league / manager / roster / transaction / projection / market / ADP / ranking / ModelRun / lineage entities | Partially completed | persistence models exist for current workflow core; some relationships/retention semantics remain to harden |
| Injury snapshot | External-data pending | intentionally not invented; no authorized injury source |
| Sleeper normalization | Completed / source compiled | `backend/app/services/importer.py` |
| Idempotent durable import | Partially completed | account+league and league+roster uniqueness/upsert implemented; real Postgres execution pending |
| Authenticated import / account isolation | Partially completed | `current_account` and account-scoped league uniqueness implemented; frontend sign-in and comprehensive authorization suite remain |
| Persist ModelRun/DataLineage/Recommendation for every decision route | Remaining defect | models exist; routes are not yet fully wired to persistence |
| Alembic configuration and canonical baseline migration | Implemented; environment-verification pending | `backend/alembic.ini`, `backend/alembic/*`; `alembic heads` passes statically |
| Migration up/down/up + upgrade from prior schema | Environment-verification pending / remaining migration hardening | requires disposable PostgreSQL |
| Shared application-lifetime Sleeper AsyncClient | Completed / verified by existing tests/source | `main.py`, `integrations/sleeper.py` |
| Typed Sleeper 404/429/5xx/timeout/invalid JSON | Completed / verified for covered cases | `tests/test_sleeper.py`; Retry-After tests 34–35 |
| Cache stampede protection | Completed / verified per process | existing test; key locks now cleaned after use |
| Redis-backed public rate limiter | Implemented; Redis verification pending | `core/rate_limit.py`; fail-closed Redis path |
| Environment-aware startup policy | Completed / verified for required DB/Redis cases | `core/config.py`; tests 32–33 |
| `/live` and environment-aware `/ready` | Implemented; dependency failure matrix partially unverified | `api/routes/health.py` |
| Trusted proxy handling | Implemented / source verified | `main.py`, `deployment/nginx/woodshed.conf` |
| API only exposed through gateway in Compose | Implemented / Docker verification pending | `docker-compose.yml` |
| AI real authentication / entitlement / quota / evidence governance | External / remaining defect | AI is disabled by default; account key guard exists, full quota/cost/claim validation not complete |
| Deterministic non-AI insight path | Completed / verified by existing service behavior | `services/insights.py` |
| Remove fake/sample players from production frontend | Completed / source verified | `ToolWorkbench.jsx`; grep evidence recorded in candidate build process |
| Unsupported tools return designed unavailable states | Completed / source verified in frontend | `ToolWorkbench.jsx` |
| Consumer result components for enabled League DNA | Completed / source inspection | `ToolWorkbench.jsx` |
| Full consumer Trade/Waiver/ROS/StartSit/Guillotine result experiences | External-data pending + remaining integration | gated, not fabricated |
| Frontend lockfile | Environment-verification pending | registry attempt failed; `qa_evidence/npm_lock_attempt.txt` |
| Frontend lint/type/component/E2E/a11y/visual | Environment-verification pending + test-infrastructure work remains | see `EXTERNAL_VERIFICATION_QUEUE.md` |
| Python transitive lock | Environment-verification pending | no fabricated lock included |
| Backend compile | Completed / verified | `qa_evidence/compileall.txt` |
| Backend test suite | Completed / verified | 61/61 |
| Branch coverage | Completed / verified | overall 82.0% line / 63.6% branch; domain 97.4% line / 90.0% branch |
| Security dependency/container scans | Environment-verification pending | Docker/security scanners unavailable; CI no longer suppresses `pip-audit` |
| Docker/Compose health | Environment-verification pending | Docker CLI unavailable |
| PostgreSQL/Redis integration | Environment-verification pending | services unavailable |
| Backup/restore/rollback | Environment-verification pending | requires PostgreSQL/deployment environment |
| Production deployment / post-deploy smoke | Credentials/infrastructure pending | no deployment target or credentials in this environment |
| Internal SHA manifest without self-entry | Completed / verified at packaging | `SHA256SUMS.txt` |
| Outer ZIP checksum | Completed / verified at packaging | adjacent `.sha256` file |

## Current verdict

**NOT READY.** The build candidate preserves implemented work while accurately separating executable local evidence from external data, infrastructure, browser, security, and deployment gates.
