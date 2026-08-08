# Woodshed Data Dictionary — Iteration 2 Candidate

## Canonical schema
`backend/app/schemas/canonical.py` defines provider-neutral transfer entities with schema version `2.0` and source stamps carrying provider, source record ID, observed/effective/ingested times, and schema version.

Implemented schema entities include:
- Account / User / ProviderConnection
- League / LeagueSettings
- ManagerIdentity / ManagerSeasonIdentity
- Roster
- Player
- Draft metadata / DraftPick
- ModelRun / DataLineage / Recommendation

## Persistence models
`backend/app/data/models.py` includes:
- `accounts`, `users`, `provider_connections`
- `leagues`, `manager_identities`, `rosters`
- `league_snapshots`, `players`, `player_team_history`
- `drafts`, `draft_picks`, `transactions`
- `projection_snapshots`, `market_value_snapshots`, `adp_snapshots`, `ranking_snapshots`
- `model_runs`, `data_lineage`, `recommendations`, `feature_flags`

The real Postgres migration/integration path is **environment-verification pending**. Model presence is not presented as proof of durable production behavior.

## Fantasy projection contract
Two explicit modes exist:

### `fantasy_points`
Required: player identity, horizon, median, scoring fingerprint. Optional floor/ceiling/stdev. The total is preserved only when its scoring fingerprint matches the requested scoring profile.

### `raw_stats`
Requires the raw stat components needed by the supported scoring engine. Missing required components cause a validation/engine error rather than silently becoming zero.

## Scoring settings
Current supported rule fields include passing/rushing/receiving yards and TDs, interceptions, receptions, TE reception bonus, two-point conversions, fumbles, passing/rushing/receiving first-down values, selected 300/100-yard bonus counters, and Superflex lineup context.

## Quality states
Projection quality supports `good`, `partial`, `stale`, `unknown`. External adapters must not upgrade unavailable/stale data without source timestamp evidence.

## Unavailable canonical areas
No authorized injury/availability dataset is bundled. PickOwnership and richer co-manager/ownership-history semantics are not yet complete enough for a deployment-ready claim; current draft attribution exposes quality/uncertainty instead.
