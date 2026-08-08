# Data Integration Requirements

No commercial or proprietary dataset is selected or fabricated in this build candidate. Sleeper public read-only league data is the only live provider integrated here. Other features stay gated until an authorized source is supplied.

## Common adapter contract

Every external adapter must normalize records with:

- provider/source name;
- provider record ID;
- player identity key and provider player ID;
- observed-at timestamp;
- effective timestamp when the source supports it;
- season/week/horizon;
- scoring fingerprint or format key where applicable;
- schema version;
- quality state: `good`, `partial`, `stale`, `unknown`, or `unavailable`;
- source freshness and coverage metadata.

Adapters must reject malformed payloads, preserve explicit zero values, distinguish missing from zero, and never replace unavailable data with invented defaults.

## Sleeper league / roster / ownership

**Used by:** League import, League DNA, future roster-aware Trade/Waiver/Start-Sit/Guillotine.

Required fields:
- league ID, season, name, status;
- roster positions;
- scoring settings;
- waiver settings and budget;
- user IDs/display names;
- roster IDs/owner IDs;
- players/starters;
- draft IDs/status/type/metadata;
- draft picks and provider-reported `picked_by` / roster attribution;
- matchups and transactions when requested.

Update frequency:
- league/settings: on import + periodic refresh;
- rosters/ownership: minutes during active periods, otherwise cacheable;
- draft history: long cache after complete;
- player dictionary: approximately daily.

Historical coverage: follows the Sleeper `previous_league_id` chain where available.

Licensing assumption: public Sleeper API use subject to Sleeper's terms; no private credential is required by the current adapter.

Adapter: `backend/app/integrations/sleeper.py`.

Validation: typed error normalization; player dictionary must be a dictionary with at least 1,000 records; completed drafts only for historical DNA.

Stale/unavailable behavior: explicit provider error/degraded state. League DNA suppresses Team Homer and historical ADP traits when dated historical evidence is unavailable.

Tests: `backend/tests/test_sleeper.py` uses fixtures/mocked HTTP only; no claim of live-provider contract certification is made.

## ROS / weekly projection feed

**Gates:** ROS Rankings, Start/Sit, Waiver Optimizer, projected-remaining Guillotine, projection component of Trade Analyzer.

Accepted representations:

1. `projection_mode="fantasy_points"`
   - player ID/name/position/team;
   - horizon;
   - median plus floor/ceiling or stdev;
   - exact `scoring_fingerprint` used to calculate those points;
   - source and source update timestamp;
   - quality state.

2. `projection_mode="raw_stats"`
   - complete fields needed by active scoring rules, including currently supported passing/rushing/receiving yards/TDs, interceptions, receptions, two-point conversions, fumbles and supported bonus counters;
   - horizon/source/update timestamp/quality.

Update frequency:
- weekly projections: at least daily and near news/inactive windows if the authorized source supports it;
- ROS: at least daily during season.

Historical coverage required for predictive validation: multiple prior seasons/weeks with timestamped snapshots that prevent future-information leakage.

Licensing: must permit ingestion, derived analysis, caching/retention, and user-facing derived outputs. No source is authorized in this candidate.

Adapter interface: implement provider-specific retrieval returning `FantasyPointsProjection` or `RawStatProjection`; domain modules must never access provider payloads directly.

Stale behavior: mark `stale`; consumer recommendation must surface freshness and may disable if beyond feature SLA.

Incomplete behavior: incomplete `raw_stats` is rejected; incompatible already-scored fingerprint is rejected.

Tests: current scoring tests use deterministic fixtures only, not licensed live projections.

## Market value feed

**Gates:** consumer Trade Analyzer and market-vs-projection displays.

Required fields:
- asset identity (player or draft pick);
- value;
- format key (dynasty/redraft, SF/1QB, TEP where source distinguishes);
- source;
- observed-at time;
- source methodology/version when available;
- future-pick season/round and uncertainty metadata for pick assets.

Update frequency: daily or better during active NFL transaction/news periods.

Historical coverage: timestamped snapshots needed for backtesting acceptance ranges and drift.

Licensing: must permit derived recommendation use and persistence. No source is authorized in this candidate.

Adapter target: persist `MarketValueSnapshot`; convert to engine asset context only after format compatibility is proven.

Stale/unavailable behavior: market component is labeled unavailable; consumer Trade Analyzer remains gated rather than using fabricated values.

Tests: current Trade engine tests use explicit fixtures, not live commercial market values.

## Historical ADP feed

**Gates:** League DNA reach/value behavior and market-style traits.

Required fields:
- player ID;
- exact draft timestamp/effective date;
- ADP/rank;
- platform/source;
- scoring and draft format;
- player pool/draft type where relevant.

Update frequency: snapshot cadence sufficient to retrieve contemporaneous ADP at the historical draft time.

Historical coverage: must overlap every analyzed draft season for a trait to claim coverage.

Licensing: must permit historical storage/derived analysis. No source is authorized.

Unavailable behavior: League DNA returns `market_style="unavailable"` and coverage false.

Tests: fixtures only.

## Player team-at-event history

**Gates:** League DNA favorite-team/Team Homer analysis.

Required fields:
- player identity;
- NFL team;
- effective-from/effective-to or timestamped roster snapshot;
- source/observed-at.

Historical coverage: must cover the event date of each historical draft selection.

Unavailable behavior: Team Homer remains disabled. Current Sleeper player team is never backfilled into historical draft events.

## Injury / availability

**Gates:** production Start/Sit and time-sensitive projection interpretation.

Required fields:
- player identity;
- status;
- practice/game designation;
- source;
- observed/effective time;
- game/week.

Update frequency: near-real-time enough for lineup decisions according to the licensed source SLA.

Licensing: no authorized source exists in this candidate.

Unavailable behavior: typed unavailable state; no injury/news claim is generated by AI or heuristics.

## AI inputs

AI is **disabled by default** and is not a source of truth. If enabled later, it may receive only structured evidence already validated by Woodshed. Required future governance includes authenticated entitlement, quotas/spend ceiling, structured output validation, claim-to-source IDs, unsupported-claim rejection, model/token/cost telemetry, and persisted ModelRun/DataLineage.
