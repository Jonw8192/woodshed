"""
THE WOODSHED — Live Sleeper Ingestion Adapter
==============================================
Point this at a real Sleeper league ID and it pulls live data, then feeds
either engine (League DNA or Guillotine Survival).

    python sleeper_live.py 1386465951670599680

Sleeper API facts this respects:
  - Base: https://api.sleeper.app/v1  — read-only, NO auth token needed.
  - Rate limit: stay under 1000 calls/min or you risk an IP block.
  - /players/nfl is ~5MB. Call it ONCE PER DAY max; we cache to disk.

Endpoints used (all GET):
  /league/{id}                      league name, season, settings, prev id
  /league/{id}/users                display names per user_id
  /league/{id}/rosters              roster_id -> owner, players, FAAB, settings
  /league/{id}/drafts               draft objects (for League DNA history)
  /draft/{draft_id}/picks           every pick (League DNA)
  /league/{id}/matchups/{week}      weekly points (Guillotine chop math)
  /players/nfl                      id -> name/pos/team (cached daily)

NOTE ON THIS SPECIFIC LEAGUE:
  The URL you gave ends in /predraft — the draft hasn't happened yet.
  * League DNA needs PAST drafts. If this league is brand new (no
    previous_league_id chain), there's no history to scout yet. The
    adapter walks the chain and tells you exactly how many seasons exist.
  * Guillotine needs weekly matchup points, which also don't exist
    pre-season. Until Week 1, the Guillotine engine can only produce the
    static SURVIVAL BOARD (needs projections), not the live waiver/chop
    math (needs real weekly scores).
  This adapter degrades gracefully and reports what it CAN build today.
"""

from __future__ import annotations
import sys, os, json, time, urllib.request, urllib.error

BASE = "https://api.sleeper.app/v1"
SPORT = "nfl"
PLAYERS_CACHE = "players_nfl.json"
PLAYERS_CACHE_MAX_AGE = 60 * 60 * 20   # ~20h; refresh at most ~once/day
CALL_SPACING = 0.05                     # be polite; ~20 calls/sec ceiling


# ============================================================
#  HTTP  (the one place that touches the network)
# ============================================================

def _get(path: str):
    url = BASE + path
    time.sleep(CALL_SPACING)
    req = urllib.request.Request(url, headers={"User-Agent": "TheWoodshed/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"[HTTP {e.code}] {url}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[ERR] {url} :: {e}", file=sys.stderr)
        return None


def load_players() -> dict:
    """id -> {name,pos,team}. Cached to disk; ~5MB so daily at most."""
    if os.path.exists(PLAYERS_CACHE):
        age = time.time() - os.path.getmtime(PLAYERS_CACHE)
        if age < PLAYERS_CACHE_MAX_AGE:
            with open(PLAYERS_CACHE) as f:
                return json.load(f)
    print("Fetching /players/nfl (large, cached daily)...", file=sys.stderr)
    raw = _get(f"/players/{SPORT}") or {}
    slim = {
        pid: {
            "name": (p.get("full_name")
                     or f"{p.get('first_name','')} {p.get('last_name','')}".strip()
                     or pid),
            "pos": (p.get("position") or "").upper(),
            "team": p.get("team") or "FA",
        }
        for pid, p in raw.items()
    }
    try:
        with open(PLAYERS_CACHE, "w") as f:
            json.dump(slim, f)
    except OSError:
        pass
    return slim


# ============================================================
#  LEAGUE FETCH
# ============================================================

class LeagueNotAvailable(Exception):
    """Raised when a league can't be loaded (missing, private, bad id).
    Raising instead of sys.exit() so an importing SERVER doesn't die — the
    CLI catches this and exits; the server catches it and returns an error."""


def fetch_league_core(league_id: str):
    league = _get(f"/league/{league_id}")
    if not league:
        raise LeagueNotAvailable(
            f"Could not load league {league_id}. Is the id correct and the league public?"
        )
    users = _get(f"/league/{league_id}/users") or []
    rosters = _get(f"/league/{league_id}/rosters") or []
    name_by_user = {u["user_id"]: (u.get("display_name") or u.get("username") or u["user_id"])
                    for u in users}
    # roster_id -> owner display name
    team_name = {}
    for r in rosters:
        owner = r.get("owner_id")
        team_name[r["roster_id"]] = name_by_user.get(owner, f"Roster {r['roster_id']}")
    return league, rosters, name_by_user, team_name


def season_chain(league_id: str, max_back=6):
    """Walk previous_league_id to collect this + prior seasons (for DNA)."""
    chain = []
    cur = league_id
    while cur and len(chain) < max_back:
        lg = _get(f"/league/{cur}")
        if not lg:
            break
        chain.append({"league_id": cur, "season": lg.get("season"),
                      "name": lg.get("name")})
        cur = lg.get("previous_league_id")
    return chain


# ============================================================
#  BUILD: LEAGUE DNA INPUT  (needs past drafts)
# ============================================================

def build_dna_picks(league_id: str, players: dict):
    """Returns (league_name, [Pick-dict,...]) across all seasons w/ drafts."""
    chain = season_chain(league_id)
    all_picks = []
    league_name = chain[0]["name"] if chain else "Unknown League"
    for season in chain:
        lid = season["league_id"]
        drafts = _get(f"/league/{lid}/drafts") or []
        for d in drafts:
            did = d.get("draft_id")
            if not did:
                continue
            picks = _get(f"/draft/{did}/picks") or []
            for pk in picks:
                pid = pk.get("player_id")
                meta = players.get(pid, {})
                all_picks.append({
                    "season": d.get("season") or season["season"],
                    "manager_id": str(pk.get("picked_by") or pk.get("roster_id")),
                    "round": pk.get("round"),
                    "pick_no": pk.get("pick_no"),
                    "player_id": pid,
                    "player_name": meta.get("name", pid),
                    "position": meta.get("pos", ""),
                    "nfl_team": meta.get("team", ""),
                })
    return league_name, all_picks, chain


# ============================================================
#  BUILD: GUILLOTINE INPUT  (needs weekly points; pre-season = board only)
# ============================================================

def current_week():
    st = _get("/state/nfl") or {}
    # 'week' is the active NFL week; 'display_week' also exists
    return st.get("week") or st.get("display_week") or 0


def build_guillotine_teams(league_id: str, rosters, team_name, week: int,
                           league: dict | None = None):
    """Weekly matchup points per roster -> Team-like dicts.
    Returns [] if no matchup data yet (pre-season).

    FAAB: Sleeper stores budget USED on each roster
    (settings.waiver_budget_used) and the league TOTAL on the league object
    (league.settings.waiver_budget, default 100). The engine and frontend
    expect faab_LEFT, so we compute it: left = total - used.
    """
    if not week or week < 1:
        return []
    matchups = _get(f"/league/{league_id}/matchups/{week}") or []
    pts = {m["roster_id"]: m.get("points", 0.0) for m in matchups}

    # total waiver budget is a league-level setting (default 100 on Sleeper)
    lg_settings = (league or {}).get("settings") or {}
    total_budget = lg_settings.get("waiver_budget", 100)

    teams = []
    for r in rosters:
        rid = r["roster_id"]
        settings = r.get("settings") or {}
        faab_used = settings.get("waiver_budget_used", 0) or 0
        faab_left = max(0, total_budget - faab_used)
        teams.append({
            "roster_id": str(rid),
            "name": team_name.get(rid, f"Roster {rid}"),
            "faab_left": faab_left,          # what the engine/frontend expect
            "faab_used": faab_used,          # kept for reference
            "faab_total": total_budget,
            "points_this_week": pts.get(rid, 0.0),
            "players": r.get("players") or [],
        })
    return teams


# ============================================================
#  MAIN
# ============================================================

def main():
    if len(sys.argv) < 2:
        print("usage: python sleeper_live.py <league_id>")
        sys.exit(1)
    league_id = sys.argv[1].strip()

    players = load_players()
    try:
        league, rosters, name_by_user, team_name = fetch_league_core(league_id)
    except LeagueNotAvailable as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    print("=" * 64)
    print(f"LEAGUE:   {league.get('name')}")
    print(f"SEASON:   {league.get('season')}   STATUS: {league.get('status')}")
    print(f"TEAMS:    {len(rosters)}")
    print("=" * 64)

    # ---- League DNA availability ----
    chain = season_chain(league_id)
    prior = [c for c in chain if c["league_id"] != league_id]
    print("\n[ LEAGUE DNA ]")
    if not prior:
        print("  No prior-season history linked to this league yet.")
        print("  DNA scouting needs 2+ past drafts. Nothing to build until")
        print("  this league has completed drafts (or links a previous season).")
    else:
        league_name, picks, ch = build_dna_picks(league_id, players)
        seasons = sorted({p['season'] for p in picks if p['season']})
        print(f"  Found {len(picks)} picks across seasons: {', '.join(seasons)}")
        print("  -> feed these into league_dna.py TendencyEngine")
        with open("dna_picks.json", "w") as f:
            json.dump({"league_name": league_name, "picks": picks}, f, indent=2)
        print("  Wrote dna_picks.json")

    # ---- Guillotine availability ----
    wk = current_week()
    print(f"\n[ GUILLOTINE ]  (current NFL week: {wk})")
    teams = build_guillotine_teams(league_id, rosters, team_name, wk, league)
    if not teams:
        print("  No weekly scoring yet (pre-season / pre-Week-1).")
        print("  The live chop + FAAB math needs real weekly points.")
        print("  You CAN still build the static Survival Board now — that only")
        print("  needs player projections (plug your projection feed in).")
    else:
        ranked = sorted(teams, key=lambda t: t["points_this_week"])
        print(f"  Live points loaded. Current low (chop risk): "
              f"{ranked[0]['name']} @ {ranked[0]['points_this_week']:.1f}")
        with open("guillotine_teams.json", "w") as f:
            json.dump({"week": wk, "teams": teams}, f, indent=2)
        print("  Wrote guillotine_teams.json")
        print("  -> feed into guillotine.py waiver_board() with projections")

    print("\nDone.")


if __name__ == "__main__":
    main()
