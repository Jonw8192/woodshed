# Model Cards — Iteration 2 Build Candidate

## League DNA rules baseline
**Type:** rules/statistics baseline, not a calibrated personality model.  
**Inputs:** completed historical draft picks segmented by draft purpose, position and round; dated ADP only when explicitly sourced.  
**Outputs:** manager rate, same-window league baseline, relative signal, tendency strength, predictability heuristic, Evidence Strength, exploitability heuristic, sample/coverage metadata.  
**Leakage controls:** live `drafting` drafts excluded from historical profile.  
**Truthfulness:** Team Homer unavailable without team-at-event history; market style unavailable without dated ADP source.  
**Validation:** deterministic regression tests for same-window baseline, purpose segmentation, incomplete drafts and unavailable traits.  
**Limitations:** Evidence Strength is a sample-support heuristic, not calibrated probability/credible interval; robust traded-pick/cross-season identity attribution remains partial.

## ROS scoring/ranking baseline
**Type:** deterministic scoring/ranking primitive.  
**Inputs:** explicit `raw_stats` or scoring-compatible `fantasy_points` ROS projections.  
**Rules:** incomplete raw stats rejected; incompatible fantasy-point scoring fingerprint rejected; no silent component imputation.  
**Outputs:** rank, median/floor/ceiling, source freshness fields, quality state, scoring fingerprint.  
**Validation:** PPR/TEP/pass-TD/bonus regression tests plus partial-projection QA case.  
**Limitations:** no authorized production projection feed and no held-out ranking backtest in this package.

## Start/Sit baseline
**Type:** deterministic risk-weighted decision primitive.  
**Inputs:** legal slot, week, active candidates, scoring-compatible projection distribution, risk profile.  
**Outputs:** start choice, alternatives, expected score edge, drivers and scoring fingerprint.  
**Validation:** eligibility/inactive filtering and a TE-premium recommendation flip.  
**Limitations:** full-lineup global optimization and current injury/availability source are not implemented/authorized.

## Trade baseline
**Type:** transparent value-over-replacement decision primitive.  
**Inputs:** market value, projection/replacement value, starter probability, roster-space context, format, league size and scoring format.  
**Outputs:** give/receive/net value, edge, roster overflow, uncertainty and verdict.  
**Validation:** symmetry/accounting, SF QB demand, TEP TE context, dynasty/redraft and redraft-pick behavior.  
**Limitations:** consumer workflow is gated without authorized market/projection feeds; actual full league replacement pool/both-team persisted context is not fully wired.

## Waiver baseline
**Type:** deterministic incremental utility / FAAB heuristic.  
**Inputs:** candidate vs replacement, start probability, usable weeks, scarcity, drop cost, league depth, survival risk, scoring context.  
**Validation:** budget bound, incremental replacement behavior, SF/TEP context and drop-candidate preservation.  
**Limitations:** no authorized production projection feed; no validated opponent bid/game-theory model.

## Guillotine baseline_v1
**Type:** seeded Monte Carlo baseline.  
**Inputs:** current points, projected remaining mean, volatility, FAAB.  
**Assumptions:** independent normal remaining scores truncated at zero.  
**Outputs:** chop probability, Monte Carlo standard error, seed, simulations and assumptions.  
**Validation:** deterministic fixed-seed tests, probability sum, bounds and local concurrency probe.  
**Limitations:** no player/game covariance, questionable-player sensitivity or historical calibration. No Brier/log-loss/calibration claim is made.

## Player insight
**Type:** deterministic summary by default; optional LLM summarizer only.  
**Truth rule:** LLM is never a player-data/news/projection source.  
**Public state:** AI disabled by default pending complete entitlement/quota/evidence governance.  
**Limitations:** claim-level structured output validation and spend telemetry remain before public enablement.
