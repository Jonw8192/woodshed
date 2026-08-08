# Requirements Traceability

The detailed Iteration 2 map is maintained in `IMPLEMENTATION_STATUS.md`. This file summarizes the principal QA defect lineage.

| QA / Plan requirement | Implementation | Verification | Status |
|---|---|---|---|
| Partial projection bug | discriminated projection modes + central scoring | Iteration2 tests 09–16 | Verified |
| Start/Sit ignores TEP | scoring-compatible projections in `start_sit.py` | test 17 flips recommendation | Verified |
| Trade ignores SF/TEP/horizon | replacement-demand and horizon logic | tests 21–24 | Verified primitive; full league workflow partial |
| ROS wrong horizon | Pydantic validator | original/API tests | Verified |
| League DNA dominant position / same-window baseline | `league_dna.py` | original DNA tests | Verified |
| Draft purpose vs mechanic | Sleeper mapping + schema | tests 28–30 | Verified mapping baseline |
| Misleading confidence | `evidence_strength` | test 31 | Verified terminology |
| Historical Team Homer / ADP unsupported | explicit unavailable states | DNA tests/coverage fields | Verified unavailable |
| Sleeper lifecycle / retry | application-lifetime client + typed errors + Retry-After parser | sleeper tests + 34–35 | Verified covered paths |
| Cache lock growth | managed lock cleanup | test 36 | Verified |
| CPU-heavy Guillotine | `to_thread` + app semaphore | tests + local load evidence | Verified local primitive |
| Readiness flags documented but absent | typed settings + `/ready` required/optional state | tests 32–33 + source | Partially verified |
| Canonical data layer | canonical schemas/models/import service | compile/static evidence | Implemented; real DB integration pending |
| Account isolation | protected import + account-scoped league model | source | Partial; real DB/authorization suite pending |
| Fake frontend players | removed from ToolWorkbench | source/grep | Verified source |
| Frontend lock/build | no fake lock; external queue | registry 404 evidence | Environment pending |
| Deployment evidence | no target/credentials | external queue | Pending |
