# Data Pipeline Notes — The Woodshed Research Engine
**Priority:** Reusable, low-cost, code-first where possible.

## Primary Data Source
**nflverse via `nflreadpy` (Python)**  
- Free, legitimate, community-maintained.  
- Covers: play-by-play, player stats, snap counts, injuries, depth charts, schedules, FantasyPros rankings, opportunity metrics (WOPR, target share, air yards share, etc.).  
- Confirmed working with 2026 data.

### Example usage
```python
import nflreadpy as nfl

# Current season injuries
injuries = nfl.load_injuries([2026])

# Player stats (weekly)
stats = nfl.load_player_stats([2026])

# Depth charts, schedules, etc. available
```

## Recommended Architecture (Lean Start)
1. **Local or lightweight cloud scripts** (Python + Polars) that pull nflverse data on a schedule.
2. **Central store:** Google Sheets, Airtable free tier, or simple SQLite/Parquet files. One player table keyed by nflverse ID + week.
3. **Research packet generator:** Script that, for a given week, outputs a Markdown or JSON packet of candidates with usage, injury, and opportunity fields pre-filled.
4. **AI layer:** Use for first-draft narrative only, grounded in the structured packet. Always include citations.
5. **Approval workflow:** Drafts land in a review folder or doc. You mark approved. No auto-publish or auto-send.

## Avoid Early
- Expensive commercial APIs until free data + manual checks prove insufficient.
- Fully autonomous publishing or emailing.
- Separate research stacks for each content division.

## Next Implementation Steps (Pending Your Standards)
- Build a simple weekly research packet script for Touch Transfer candidates.
- Add basic opportunity scoring (role certainty + usage trend).
- Create VERSUS salary validation helper (once current DraftKings Showdown rules and prices are confirmed).

**Cost:** $0 for data and core pipeline at this stage.
