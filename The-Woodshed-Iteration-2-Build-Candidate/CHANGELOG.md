# Changelog

## Iteration 2 build candidate

- Preserved FastAPI/Next.js/domain separation and Woodshed midnight/emerald brand.
- Added discriminated `raw_stats` / `fantasy_points` projection contracts and scoring fingerprints.
- Added central scoring engine and regression coverage for PPR, TEP, TD, first-down and selected yardage-bonus rules.
- Made Start/Sit scoring-aware; added a TEP recommendation-flip regression.
- Made Trade/Waiver decision primitives respond to SF/TEP/horizon context without a fake fantasy-point scoring multiplier.
- Kept ROS horizon enforcement and removed partial-stat reconstruction behavior.
- Separated League DNA draft purpose from draft mechanic; renamed heuristic confidence to Evidence Strength and preserved unavailable historical ADP/team states.
- Hardened Sleeper Retry-After parsing and cache-key lock lifecycle.
- Added environment-aware production policy, dependency readiness states, Redis-backed rate-limiter path and bounded Guillotine simulation semaphore.
- Added provider-neutral canonical schemas, expanded persistence models, Sleeper normalization and authenticated durable import endpoint.
- Added Alembic baseline configuration/migration.
- Removed fake/sample player/team data from production frontend decision paths and replaced unsupported workflows with explicit unavailable states.
- Expanded backend suite to **61 passing tests**.
- Added build-candidate implementation status, external verification queue and data-integration requirements.
