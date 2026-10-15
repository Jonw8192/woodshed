# THE WOODSHED Research Engine v2.0

**Local-first fantasy football research and editorial operations.** This project extends the v1.0 Touch Transfer engine with Favorites & Fades, VERSUS DFS Showdown validation, original Edge Report newsletter preparation, business accounting, and an expanded Streamlit dashboard.

**Important:** This is an operational editor/research assistant, not a self-running autonomous media business. Live data acquisition is an optional adapter, not independently verified in this build. The dashboard and extensions were exercised with offline fixtures; do not publish fixture data. Articles, newsletters, X posts and email are *never* automatically sent. Source dates and facts need review before editorial approval.

## Quick start (Mac / Linux)

```bash
unzip woodshed_research_engine_v2.zip
cd woodshed_v2
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest tests -q
streamlit run dashboard.py
```

On Windows activate with `.venv\Scripts\activate`. Open `http://localhost:8501`. No accounts, API keys, or cloud hosting are required for the local dashboard. SQLite persists to `woodshed.db` by default (override using `WOODSHED_DB`). Back up the database regularly; do not put it in a public Git repository.

## Main tabs

- **Overview:** Count research rows, FAAB balance, newsletter issues.
- **Data & Touch Transfer:** Import normalized player-week CSV, compare usage changes, review ownership flags, save Jon-approved decisions, export research and draft. Empty or unverified eligibility is never treated as a valid waiver add.
- **FAAB:** Enter actual expenditure against the $200 budget.
- **Favorites & Fades:** Enter *assigned* matchups, betting lines/totals, player categories and analytical theses, then export. Source and editorial verification are manual; missing opponent fantasy-points-allowed values remain explicitly flagged.
- **VERSUS:** Configure a contest, upload a slate-specific CSV salary pool, evaluate and save salary-valid Captain/Flex lineups, export show notes. Rules must be entered from the actual contest, not assumed from defaults. This does not create entries or retrieve prices/results.
- **Edge Report:** Compose original free and paid newsletter issues, record source review, apply an approval status, export Markdown. No Substack/beehiiv API or payment processing is connected.
- **Business:** Log confirmed cash flow separately from unconfirmed prospective revenue.
- **Audit:** Existing Touch Transfer decision/import log.

## Optional nflverse data pull

```bash
python cli.py fetch --season 2026 --week 6 --csv data/week6.csv
```

Inspect the output for player IDs, game week, stat mappings and source coverage before importing:

```bash
python cli.py import data/week6.csv
python cli.py packet --season 2026 --week 6
```

Installing `nflreadpy` and reaching nflverse does **not** establish ownership, current injury status, route participation, full source provenance, or full editorial verification. A normalized CSV can be imported without using the live adapter. A small **fictional** example is available at `examples/fictional_weekly_stats.csv` for UI tests only.

## Batch preparation (no publishing)

```bash
python ops.py --season 2026 --week 6 --db woodshed.db --out output
```

This prepares available Touch Transfer research, a Touch Transfer draft, Favorites & Fades draft (based on user-entered matchups) and an Edge Report issue outline. It does **not** fetch live data; schedule `ops.py` only after you have planned your verified imports. It does not email Mike, post to X, publish newsletters or place DFS entries.

## VERSUS salary import format

A CSV must have these columns:

```csv
player_id,name,salary,team
001,Example Player,10000,TB
002,Another Player,8000,ATL
```

Prices must match the **same slate, provider, and roster slot pricing convention**. For DraftKings Showdown, if the CSV contains FLEX/base salaries, the configured captain multiplier will be applied. Do **not** import a provider CSV containing already-multiplied captain salaries into this simplified adapter. The validation checks cap, count, exactly one captain, uniqueness, available prices, and slot names. It does not enforce provider-specific team-composition or other eligibility constraints; manually check all current contest rules.

## Known limitations / next integrations

1. No live production validation of current 2026 nflreadpy dataset schema, endpoints, timeliness, or licensing. The adapter needs a live integration run.
2. Routes, first-read rates, red-zone information, fantasy roster ownership, and injury verification require reliable data sources or manual entry.
3. Opponent fantasy points allowed, rankings, sportsbook lines and game picks are manual verified inputs.
4. DFS CSV salary import is generic and does not validate every platform-specific contest restriction.
5. No live game result importer, DFS optimizer, viewer/subscriber accounts, newsletter API, payment collection, X API, or Tuta send integration.
6. No cloud hosting/authentication hardening. Do not expose this local app to the open internet. If you deploy to the cloud, first implement authentication, secrets management, backups and multi-user data isolation.
7. Dashboard interaction has not been end-to-end tested in a browser in this environment; underlying module tests pass.
8. All editorial and licensing checks must still be performed by Jon. Existing FFToday assignments have priority, and commissioned article text should not be resold as original newsletter content.

## Validation

Run `python -m pytest tests -q`. Automated tests cover the v1 core and new Favorites & Fades category/approval logic, VERSUS cap and duplicate-player validation, newsletter approval requirements, and separation of actual versus hypothetical revenue. No live NFL data assertions are made by the offline tests.

## Folder guide

- `woodshed/core.py` – Touch Transfer, normalized imports, FAAB and editorial decisions.
- `woodshed/nflverse.py` – optional, unverified live data adapter.
- `woodshed/editorial.py` – Favorites & Fades storage and drafting.
- `woodshed/versus.py` – configured contest and salary verification.
- `woodshed/publishing.py` – original newsletter and finance tracking.
- `woodshed/automation.py` – safe, batch draft exports.
- `dashboard.py` – Streamlit control center.
- `cli.py` – original research command line.
- `ops.py` – batch multi-product document preparation.
- `legacy/` – original Grok files kept for reference; not executed.

**Contact for manual FFToday submission:** JonWoods@tutamail.com. Tuta has no supported standard SMTP or public email-sending API.
