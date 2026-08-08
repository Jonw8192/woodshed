"""
THE WOODSHED — League DNA Analyzer
===================================
Scouts the *humans* in a fantasy league, not the players.

Ingests a Sleeper league's historical drafts and detects each manager's
repeatable, predictable tendencies so you know how the room will misdraft
BEFORE your draft starts.

WHY SLEEPER-FIRST: Sleeper exposes a free, documented, no-auth API that
returns full historical draft data. ESPN/Yahoo/CBS do not (see notes at
bottom). This module is built so live ingestion is a one-function swap.

------------------------------------------------------------------------
DATA FLOW
------------------------------------------------------------------------
  user_id (or username)
        -> get_user_leagues()        # every league they're in, per season
        -> walk previous_league_id    # chain back through past seasons
        -> get_league_drafts()        # draft objects per season
        -> get_draft_picks()          # every pick, with round/slot/roster
        -> normalize to Pick records
        -> TendencyEngine.analyze()   # per-manager fingerprints
        -> ScoutingReport             # what the frontend renders

Every network call is isolated in the SleeperClient class. Swap
USE_SAMPLE_DATA = False and provide a fetch function to go live.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from collections import defaultdict, Counter
from statistics import mean, pstdev
from typing import Optional
import json

# ============================================================
#  CONFIG / DECISION KNOBS  (you make these calls)
# ============================================================

# How many rounds count as "early" for positional-reach detection.
EARLY_ROUND_CUTOFF = 4

# A manager is flagged as "reaches for <pos>" if they take that position
# in the early rounds at this rate or higher, across their history.
REACH_RATE_THRESHOLD = 0.60          # 60%+ of their seasons

# ADP discipline: average |pick - player_adp|. Lower = drafts by the book.
# Above this gap (in draft slots) => "goes off-script / unpredictable".
CHALK_GAP_THRESHOLD = 8.0            # avg slots away from ADP

# Minimum seasons of history before we trust a "pattern" label.
MIN_SEASONS_FOR_PATTERN = 2

POSITIONS = ["QB", "RB", "WR", "TE"]


# ============================================================
#  DATA MODELS
# ============================================================

@dataclass
class Pick:
    """One normalized draft pick."""
    season: str
    manager_id: str
    manager_name: str
    round: int
    pick_no: int          # overall pick number in that draft
    player_id: str
    player_name: str
    position: str
    nfl_team: str
    adp: Optional[float] = None   # consensus ADP at draft time, if known


@dataclass
class ManagerFingerprint:
    manager_id: str
    manager_name: str
    seasons_analyzed: int
    # headline label + supporting evidence
    archetype: str = ""
    tells: list = field(default_factory=list)          # list[str] scouting tells
    # raw signals (also handed to frontend for detail views)
    pos_reach_rates: dict = field(default_factory=dict)  # pos -> rate early
    first_pick_positions: list = field(default_factory=list)
    avg_adp_gap: Optional[float] = None
    adp_discipline: str = ""      # "chalk"|"balanced"|"gunslinger"|"unknown"(no ADP)
    favorite_teams: list = field(default_factory=list)   # (team, count)
    predictability: int = 0        # 0-100, higher = easier to exploit
    exploit: str = ""              # the one-line "so do THIS" takeaway


@dataclass
class ScoutingReport:
    league_name: str
    seasons: list
    fingerprints: list             # list[ManagerFingerprint]
    room_summary: str              # league-wide read
    generated_for: str = ""        # the user's own manager name


# ============================================================
#  SLEEPER CLIENT  (network isolated here)
# ============================================================

class SleeperClient:
    """
    All live calls live here. Base URL: https://api.sleeper.app/v1
    Real endpoints (no auth required):
        GET /user/<username>                     -> {user_id,...}
        GET /user/<user_id>/leagues/nfl/<year>   -> [league,...]
        GET /league/<league_id>                  -> {previous_league_id,...}
        GET /league/<league_id>/drafts           -> [draft,...]
        GET /draft/<draft_id>/picks              -> [pick,...]
        GET /league/<league_id>/users            -> [user,...]  (names)
    Player metadata (id->name/pos/team) from GET /players/nfl (cache daily).

    In THIS environment there is no network, so USE_SAMPLE_DATA drives it.
    To go live: set USE_SAMPLE_DATA=False and implement _get() with your
    HTTP client of choice (requests/httpx), plus a players cache.
    """
    BASE = "https://api.sleeper.app/v1"

    def __init__(self, use_sample=True):
        self.use_sample = use_sample

    def _get(self, path):
        raise NotImplementedError(
            "Live mode: implement HTTP GET on {}{}".format(self.BASE, path)
        )

    def load_picks(self) -> tuple[str, list[Pick]]:
        """Returns (league_name, [Pick,...]) across all available seasons."""
        if self.use_sample:
            return _sample_league()
        # --- LIVE PATH (wire up when deploying) ---
        # 1. resolve user -> user_id
        # 2. find current league_id for user
        # 3. walk previous_league_id chain -> [league_ids per season]
        # 4. for each: /drafts -> /draft/<id>/picks -> normalize -> Pick
        # 5. join player_id against /players/nfl cache for name/pos/team
        # 6. attach adp from your aggregate board (see league_dna notes)
        raise NotImplementedError


# ============================================================
#  TENDENCY ENGINE
# ============================================================

class TendencyEngine:
    def __init__(self, picks: list[Pick]):
        self.picks = picks
        self.seasons = sorted({p.season for p in picks})
        # index picks by manager
        self.by_mgr: dict[str, list[Pick]] = defaultdict(list)
        for p in picks:
            self.by_mgr[p.manager_id].append(p)

    # ---- individual signal detectors ----

    def _pos_reach_rates(self, mgr_picks) -> dict:
        """Rate at which manager took each position in EARLY rounds,
        measured per season (did they spend an early pick on it?)."""
        seasons = defaultdict(set)  # season -> set(positions taken early)
        for p in mgr_picks:
            if p.round <= EARLY_ROUND_CUTOFF:
                seasons[p.season].add(p.position)
        n = max(len(seasons), 1)
        rates = {}
        for pos in POSITIONS:
            hits = sum(1 for s in seasons.values() if pos in s)
            rates[pos] = round(hits / n, 2)
        return rates

    def _first_pick_positions(self, mgr_picks) -> list:
        firsts = []
        by_season = defaultdict(list)
        for p in mgr_picks:
            by_season[p.season].append(p)
        for s, ps in by_season.items():
            ps.sort(key=lambda x: x.pick_no)
            if ps:
                firsts.append(ps[0].position)
        return firsts

    def _adp_gap(self, mgr_picks):
        gaps = [abs(p.pick_no - p.adp) for p in mgr_picks if p.adp is not None]
        return round(mean(gaps), 1) if gaps else None

    def _favorite_teams(self, mgr_picks) -> list:
        c = Counter(p.nfl_team for p in mgr_picks if p.nfl_team)
        # a "favorite" bias = a team they draft repeatedly beyond chance
        return [(t, n) for t, n in c.most_common(3) if n >= 3]

    # ---- synthesis into a fingerprint ----

    def _label(self, fp: ManagerFingerprint, mgr_picks):
        tells = []
        # positional reach tells
        for pos in POSITIONS:
            rate = fp.pos_reach_rates.get(pos, 0)
            if rate >= REACH_RATE_THRESHOLD and pos in ("QB", "TE"):
                tells.append(
                    f"Reaches for {pos} early — {int(rate*100)}% of drafts "
                    f"spent a top-{EARLY_ROUND_CUTOFF}-round pick on {pos}."
                )
        # first-pick habit
        fpc = Counter(fp.first_pick_positions)
        if fpc:
            top_pos, top_n = fpc.most_common(1)[0]
            if top_n / max(len(fp.first_pick_positions), 1) >= 0.6:
                tells.append(f"Opens with {top_pos} almost every year.")
        # ADP discipline. IMPORTANT: "no ADP feed wired in" is NOT a
        # classification. We mark it "unknown" so nothing downstream mistakes
        # missing data for a real read on the manager. Positional/homer tells
        # above still work with pure Sleeper data; only discipline needs ADP.
        gap = fp.avg_adp_gap
        if gap is None:
            fp.adp_discipline = "unknown"   # ADP not available for this manager
        elif gap <= CHALK_GAP_THRESHOLD * 0.6:
            fp.adp_discipline = "chalk"
            tells.append("Drafts straight off ADP — highly predictable.")
        elif gap >= CHALK_GAP_THRESHOLD:
            fp.adp_discipline = "gunslinger"
            tells.append("Ignores ADP, drafts on gut — wildcard.")
        else:
            fp.adp_discipline = "balanced"
        # team bias
        if fp.favorite_teams:
            t, n = fp.favorite_teams[0]
            tells.append(f"Homer tell: keeps drafting {t} players ({n} across history).")

        fp.tells = tells

        # ---- archetype: score every candidate, pick the STRONGEST signal ----
        # Each candidate scores 0..100 on how loud/exploitable its tell is.
        # This fixes two failure modes of naive rule-ordering:
        #   (a) an RB-hoarder who also drafts to ADP shouldn't read as "chalk"
        #   (b) a homer who also takes a QB early shouldn't hide the homer tell
        candidates = []

        # QB reach signal — strength scales with how often they do it
        qb_rate = fp.pos_reach_rates.get("QB", 0)
        if qb_rate >= REACH_RATE_THRESHOLD:
            candidates.append((
                40 + int(qb_rate * 55),  # 0.6->73, 1.0->95
                "The QB Panic Drafter",
                "Let him take his QB early. You wait — the RB/WR he skips is your value.",
            ))

        # RB hoard signal — count of early RBs per season, not just first pick
        rb_early = [p for p in mgr_picks
                    if p.position == "RB" and p.round <= EARLY_ROUND_CUTOFF]
        seasons_ct = max(fp.seasons_analyzed, 1)
        rb_per_season = len(rb_early) / seasons_ct
        if rb_per_season >= 1.6:  # takes ~2 early RBs most years
            candidates.append((
                50 + int(min(rb_per_season - 1.6, 1.4) * 30),
                "The RB Hoarder",
                "He'll clear the RB early. Load elite WR/TE while the position is thin for everyone else.",
            ))

        # Homer signal — strength scales with concentration on one team
        if fp.favorite_teams:
            team, cnt = fp.favorite_teams[0]
            total = len(mgr_picks)
            concentration = cnt / max(total, 1)
            if cnt >= 4:  # a genuine repeated bias, not noise
                candidates.append((
                    45 + int(concentration * 120),
                    f"The {team} Homer",
                    f"Reliable {team} bias — those players go early to him. "
                    f"Don't overpay to block; let him overspend on his guys.",
                ))

        # Discipline signals (weaker/ default-y; lower base scores)
        if fp.adp_discipline == "chalk":
            candidates.append((
                42, "The Chalk Merchant",
                "Fully predictable. Draft one slot ahead of ADP on players he wants and he'll never adjust.",
            ))
        elif fp.adp_discipline == "gunslinger":
            candidates.append((
                38, "The Gunslinger",
                "Unpredictable early. Don't plan reaches around him — plan for chaos and grab falling value.",
            ))

        if candidates:
            candidates.sort(reverse=True)
            _, fp.archetype, fp.exploit = candidates[0]
        else:
            fp.archetype = "The Balanced Drafter"
            fp.exploit = "No strong tell. Watch his first two picks live and adjust."

        # predictability score (0-100): rewards consistency, penalizes gunslinging
        score = 40
        if fp.adp_discipline == "chalk":
            score += 40
        elif fp.adp_discipline == "gunslinger":
            score -= 25
        # consistent first-pick position adds predictability
        if fpc:
            score += int(30 * (fpc.most_common(1)[0][1] / max(len(fp.first_pick_positions), 1)))
        fp.predictability = max(0, min(100, score))

    def analyze(self) -> list[ManagerFingerprint]:
        out = []
        for mgr_id, mgr_picks in self.by_mgr.items():
            name = mgr_picks[0].manager_name
            seasons_n = len({p.season for p in mgr_picks})
            fp = ManagerFingerprint(
                manager_id=mgr_id,
                manager_name=name,
                seasons_analyzed=seasons_n,
                pos_reach_rates=self._pos_reach_rates(mgr_picks),
                first_pick_positions=self._first_pick_positions(mgr_picks),
                avg_adp_gap=self._adp_gap(mgr_picks),
                favorite_teams=self._favorite_teams(mgr_picks),
            )
            self._label(fp, mgr_picks)
            if seasons_n < MIN_SEASONS_FOR_PATTERN:
                fp.archetype = "Insufficient History"
                fp.exploit = f"Only {seasons_n} season(s) of data — patterns not yet reliable."
                fp.predictability = 0
            out.append(fp)
        # sort most-exploitable first
        out.sort(key=lambda f: f.predictability, reverse=True)
        return out


def build_report(use_sample=True, my_name="") -> ScoutingReport:
    league_name, picks = SleeperClient(use_sample=use_sample).load_picks()
    engine = TendencyEngine(picks)
    fps = engine.analyze()
    # room-level read
    n_chalk = sum(1 for f in fps if f.adp_discipline == "chalk")
    n_qb = sum(1 for f in fps if "QB Panic" in f.archetype)
    bits = []
    if n_qb:
        bits.append(f"{n_qb} manager(s) panic-draft QB early — QB value slides to whoever waits.")
    if n_chalk:
        bits.append(f"{n_chalk} chalk drafter(s) — this room is beatable by drafting one slot ahead of ADP.")
    if not bits:
        bits.append("No dominant room-wide tell. Edge comes from live reads, not pre-draft scripts.")
    summary = " ".join(bits)
    return ScoutingReport(
        league_name=league_name,
        seasons=engine.seasons,
        fingerprints=fps,
        room_summary=summary,
        generated_for=my_name,
    )


# ============================================================
#  SAMPLE DATA  (mirrors real Sleeper pick shape)
# ============================================================

def _sample_league() -> tuple[str, list[Pick]]:
    """Three seasons, six managers, hand-built to show each archetype.
    Positions/teams realistic; ADP included so discipline math runs."""
    mgrs = {
        "m1": "Kevin",   # QB panic drafter
        "m2": "Dana",    # chalk merchant
        "m3": "Sam",     # gunslinger
        "m4": "Priya",   # RB hoarder
        "m5": "Marcus",  # homer (drafts his team)
        "m6": "You",     # the user
    }
    picks: list[Pick] = []

    def add(season, mid, rnd, pickno, pid, name, pos, team, adp):
        picks.append(Pick(season, mid, mgrs[mid], rnd, pickno, pid, name, pos, team, adp))

    # --- 2023 ---
    add("2023","m1",2,14,"a","QB Early Guy","QB","BUF",26)     # Kevin reaches QB
    add("2023","m1",1,3,"b","Bijan","RB","ATL",4)
    add("2023","m2",1,6,"c","Chase","WR","CIN",6)              # Dana = chalk
    add("2023","m2",2,18,"d","Breece","RB","NYJ",19)
    add("2023","m3",1,2,"e","Wildcard TE","TE","KC",22)        # Sam = gunslinger
    add("2023","m3",2,23,"f","Deep Sleeper","WR","SEA",55)
    add("2023","m4",1,4,"g","Hoard RB1","RB","SF",5)           # Priya RB hoard
    add("2023","m4",2,21,"h","Hoard RB2","RB","DET",30)
    add("2023","m5",3,30,"i","Home QB","QB","DAL",34)          # Marcus homer DAL
    add("2023","m5",5,54,"j","Home WR","WR","DAL",60)
    add("2023","m6",1,7,"k","Your Pick","WR","MIN",8)

    # --- 2024 ---
    add("2024","m1",2,15,"l","QB Early2","QB","PHI",28)        # Kevin QB again
    add("2024","m1",1,5,"m","RB fill","RB","BAL",7)
    add("2024","m2",1,8,"n","Chalk WR","WR","MIA",8)           # Dana chalk again
    add("2024","m2",2,17,"o","Chalk RB","RB","GB",18)
    add("2024","m3",1,1,"p","Chaos1","RB","LV",14)             # Sam reaches wild
    add("2024","m3",3,29,"q","Chaos2","QB","ARI",48)
    add("2024","m4",1,3,"r","Hoard RB3","RB","PHI",3)          # Priya RB hoard
    add("2024","m4",2,20,"s","Hoard RB4","RB","HOU",25)
    add("2024","m5",4,40,"t","Home RB","RB","DAL",44)          # Marcus DAL again
    add("2024","m5",6,66,"u","Home WR2","WR","DAL",70)
    add("2024","m6",1,9,"v","Your Pick2","RB","CHI",10)

    # --- 2025 ---
    add("2025","m1",2,13,"w","QB Early3","QB","CIN",24)        # Kevin QB third time
    add("2025","m1",1,6,"x","RB fill2","RB","IND",8)
    add("2025","m2",1,4,"y","Chalk RB2","RB","LAR",4)          # Dana chalk
    add("2025","m2",2,16,"z","Chalk WR2","WR","NYJ",17)
    add("2025","m3",2,19,"aa","Chaos3","WR","NE",41)           # Sam off-book
    add("2025","m3",4,44,"ab","Chaos4","TE","CHI",67)
    add("2025","m4",1,2,"ac","Hoard RB5","RB","DET",2)         # Priya RB
    add("2025","m4",3,26,"ad","Hoard RB6","RB","SF",33)
    add("2025","m5",3,33,"ae","Home QB2","QB","DAL",38)        # Marcus DAL
    add("2025","m5",5,55,"af","Home TE","TE","DAL",61)
    add("2025","m6",1,5,"ag","Your Pick3","WR","CIN",6)

    return "The Woodshed Test League", picks


# ============================================================
#  CLI / demo
# ============================================================

if __name__ == "__main__":
    report = build_report(use_sample=True, my_name="You")
    print("=" * 62)
    print(f"LEAGUE DNA  —  {report.league_name}")
    print(f"Seasons: {', '.join(report.seasons)}")
    print("=" * 62)
    print("ROOM READ:", report.room_summary)
    print("-" * 62)
    for fp in report.fingerprints:
        if fp.manager_name == report.generated_for:
            continue
        print(f"\n{fp.manager_name}  —  {fp.archetype}"
              f"   [predictability {fp.predictability}/100]")
        for t in fp.tells:
            print(f"   • {t}")
        print(f"   >> EXPLOIT: {fp.exploit}")
    print("\n" + "=" * 62)

    # emit JSON for the frontend
    payload = {
        "league_name": report.league_name,
        "seasons": report.seasons,
        "room_summary": report.room_summary,
        "generated_for": report.generated_for,
        "fingerprints": [asdict(f) for f in report.fingerprints],
    }
    with open("report.json", "w") as fh:
        json.dump(payload, fh, indent=2)
    print("Wrote report.json")
