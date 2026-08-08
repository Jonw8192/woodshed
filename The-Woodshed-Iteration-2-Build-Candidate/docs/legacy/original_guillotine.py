"""
THE WOODSHED — Guillotine Survival Engine
==========================================
The beachhead product. Guillotine inverts standard fantasy math:

  - No head-to-head opponent. Every week the LOWEST-scoring team is chopped.
  - Your only job: don't finish last. Survive to be the last team standing.
  - Therefore CONSISTENCY beats upside. A safe weekly floor keeps you alive;
    a boom/bust roster eventually busts on the wrong week and you're gone.
  - When a team is chopped, their ENTIRE roster hits waivers. The waiver
    wire is the game — you rebuild weekly from the survivor pool via FAAB.

This engine does two jobs standard tools can't, because their models
optimize ceiling and season-long value — the opposite of what wins here:

  JOB 1  survival_score()   -> ranks players by FLOOR SAFETY, not ceiling.
  JOB 2  waiver_board()     -> predicts the week's chop, models the roster
                               about to flood waivers, and returns
                               floor-maximizing FAAB bids for YOUR team.

Sleeper-first (free API: rosters, matchups, transactions, FAAB budgets).
All projection inputs are pluggable — swap the sample projections for a
live feed without touching the survival logic.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from statistics import mean, pstdev
from typing import Optional
import math, json

# ============================================================
#  DECISION KNOBS  (you own these)
# ============================================================

# Survival scoring: how much we punish volatility. Guillotine cares about
# the BAD week, so we weight the downside far more than the median.
# floor = projection - FLOOR_Z * weekly_stdev   (a low-percentile outcome)
FLOOR_Z = 1.0            # ~16th percentile "bad but not disaster" week

# Blend that decides survival_score:
#   score = FLOOR_WEIGHT * floor + (1 - FLOOR_WEIGHT) * median_projection
# Higher FLOOR_WEIGHT = more paranoid / more guillotine-correct.
FLOOR_WEIGHT = 0.70

# Volume is the strongest floor signal in guillotine (research-backed:
# high-volume + dual-threat QBs carry safe floors). Bonus added to score.
VOLUME_BONUS_MAX = 3.0   # points added at elite volume share

# Chop prediction: teams within this projected-points margin of the bottom
# are flagged "on the block" this week.
CHOP_DANGER_MARGIN = 12.0

# FAAB: never blow the whole budget on one week unless survival demands it.
MAX_BID_PCT_NORMAL = 0.35     # cap a routine bid at 35% of remaining FAAB
MAX_BID_PCT_DESPERATE = 0.90  # if YOU are on the block, open the vault


# ============================================================
#  DATA MODELS
# ============================================================

@dataclass
class PlayerProj:
    player_id: str
    name: str
    position: str
    nfl_team: str
    proj: float                 # median weekly projection (points)
    stdev: float                # weekly volatility (std dev of outcomes)
    volume_share: float = 0.0   # 0..1 team-usage share (snaps/touches/targets)
    owned_by: Optional[str] = None   # roster_id of owner, or None = free agent

    # computed
    floor: float = 0.0
    survival_score: float = 0.0
    tier: str = ""

@dataclass
class Team:
    roster_id: str
    name: str
    faab_left: int
    proj_points_this_week: float
    starters: list = field(default_factory=list)   # player_ids

@dataclass
class WaiverTarget:
    player: PlayerProj
    suggested_bid: int
    max_bid: int
    reason: str
    fills_hole: bool

@dataclass
class WaiverBoard:
    week: int
    my_team: str
    my_faab_left: int
    i_am_on_block: bool
    chop_watch: list           # list[(team_name, margin)]
    incoming_pool: list        # players about to hit waivers (from predicted chop)
    targets: list              # list[WaiverTarget]
    summary: str


# ============================================================
#  JOB 1 — SURVIVAL SCORING (the ranking inversion)
# ============================================================

def compute_survival(players: list[PlayerProj]) -> list[PlayerProj]:
    """Score every player by FLOOR SAFETY, not ceiling.
    This is what makes a guillotine board different from every other board."""
    for p in players:
        # a bad-week outcome, floored at zero
        p.floor = max(0.0, p.proj - FLOOR_Z * p.stdev)
        # blend floor with median — paranoid weighting
        base = FLOOR_WEIGHT * p.floor + (1 - FLOOR_WEIGHT) * p.proj
        # volume bonus: safe floors come from guaranteed usage
        base += VOLUME_BONUS_MAX * _clamp(p.volume_share)
        p.survival_score = round(base, 2)

    # Tier by ABSOLUTE floor safety, not rank percentile. In guillotine the
    # question is "will this player put up a survivable floor?" — that's a
    # property of the player, not of where they sit in this particular list.
    # A pool of all-safe players should not manufacture a "Landmine"; a pool
    # of all-risky players should not manufacture an "Anchor".
    ranked = sorted(players, key=lambda x: x.survival_score, reverse=True)
    for p in ranked:
        # thresholds are in projected-points of floor (a bad-week outcome)
        if p.floor >= 12.0:
            p.tier = "Anchor"      # safe even on a down week
        elif p.floor >= 8.5:
            p.tier = "Safe"
        elif p.floor >= 5.5:
            p.tier = "Startable"   # usable but sweat it
        elif p.floor >= 3.0:
            p.tier = "Volatile"    # can hand you a chop-week
        else:
            p.tier = "Landmine"    # will eventually zero you out
    return ranked


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


# ============================================================
#  JOB 2 — CHOP PREDICTION + FAAB OPTIMIZER
# ============================================================

def predict_chop(teams: list[Team]) -> tuple[list, list]:
    """Return (chop_watch, chopped_team) for the week.
    chop_watch = teams within danger margin of the lowest projection.
    chopped_team = single most-likely chop (lowest projection)."""
    ranked = sorted(teams, key=lambda t: t.proj_points_this_week)
    lowest = ranked[0]
    watch = []
    for t in ranked:
        margin = round(t.proj_points_this_week - lowest.proj_points_this_week, 1)
        if margin <= CHOP_DANGER_MARGIN:
            watch.append((t.name, margin))
    return watch, lowest


def _roster_holes(my_team: Team, all_players: dict) -> set:
    """Which positions is my starting lineup weakest at?
    Returns positions whose current starter is Volatile/Landmine tier."""
    holes = set()
    for pid in my_team.starters:
        p = all_players.get(pid)
        if p and p.tier in ("Volatile", "Landmine"):
            holes.add(p.position)
    return holes


def waiver_board(week: int,
                 my_roster_id: str,
                 teams: list[Team],
                 players: list[PlayerProj]) -> WaiverBoard:
    """The week's real decision: who to bid on and how much."""
    ranked = compute_survival(players)
    pmap = {p.player_id: p for p in ranked}
    my_team = next((t for t in teams if t.roster_id == my_roster_id), None)
    if my_team is None:
        valid = ", ".join(t.roster_id for t in teams)
        raise ValueError(
            f"roster_id {my_roster_id!r} not found in this league. "
            f"Valid roster_ids: {valid}"
        )

    chop_watch, chopped = predict_chop(teams)
    i_am_on_block = any(name == my_team.name and margin <= CHOP_DANGER_MARGIN
                        for name, margin in chop_watch)

    # players about to flood waivers = the predicted chopped team's roster,
    # PLUS any current free agents worth claiming.
    incoming = [p for p in ranked if p.owned_by == chopped.roster_id]
    free_agents = [p for p in ranked if p.owned_by is None]
    pool = sorted(incoming + free_agents,
                  key=lambda x: x.survival_score, reverse=True)

    holes = _roster_holes(my_team, pmap)

    # bid sizing
    cap_pct = MAX_BID_PCT_DESPERATE if i_am_on_block else MAX_BID_PCT_NORMAL
    budget = my_team.faab_left
    hard_cap = int(budget * cap_pct)

    targets = []
    # value the pool relative to what YOU currently start (upgrade math)
    my_start_scores = sorted(
        [pmap[pid].survival_score for pid in my_team.starters if pid in pmap]
    )
    weakest_starter = my_start_scores[0] if my_start_scores else 0.0

    for p in pool[:8]:
        upgrade = p.survival_score - weakest_starter
        fills = p.position in holes
        # A player too risky to survive with should never attract real money,
        # even to fill a hole or in desperation. In guillotine the unsafe
        # player IS the thing that gets you chopped — bidding up a Landmine
        # to patch a hole just moves the landmine into your starting lineup.
        rosterable = p.tier in ("Anchor", "Safe", "Startable")

        intensity = _clamp(upgrade / 12.0)            # 12 pts = full send
        if rosterable:
            if fills:
                intensity = _clamp(intensity + 0.25)
            if i_am_on_block:
                intensity = _clamp(intensity + 0.30)
        else:
            # unsafe: token-only. Worth a $0-1 flier at most, never a real bid.
            intensity = min(intensity, 0.02)

        bid = int(round(hard_cap * intensity))
        if rosterable and bid < 1:
            bid = 1
        if bid < 1:
            continue
        reason = _bid_reason(p, upgrade, fills and rosterable, i_am_on_block and rosterable)
        targets.append(WaiverTarget(
            player=p, suggested_bid=bid, max_bid=min(hard_cap, budget),
            reason=reason, fills_hole=fills,
        ))

    targets.sort(key=lambda t: t.suggested_bid, reverse=True)
    summary = _board_summary(my_team, i_am_on_block, chopped, chop_watch, targets)
    return WaiverBoard(
        week=week, my_team=my_team.name, my_faab_left=budget,
        i_am_on_block=i_am_on_block, chop_watch=chop_watch,
        incoming_pool=[p.name for p in incoming[:6]],
        targets=targets, summary=summary,
    )


def _bid_reason(p, upgrade, fills, desperate):
    bits = [f"{p.tier} floor ({p.survival_score} pts)"]
    if upgrade > 0:
        bits.append(f"+{round(upgrade,1)} over your weakest starter")
    if fills:
        bits.append("fills a lineup hole")
    if desperate:
        bits.append("you're on the block — survival buy")
    return " · ".join(bits)


def _board_summary(my_team, on_block, chopped, watch, targets):
    if on_block:
        lead = (f"⚠ {my_team.name} is ON THE BLOCK this week. "
                f"Spend to survive — floor now, save FAAB later only if you live.")
    else:
        lead = (f"{my_team.name} projects safe this week. "
                f"Buy floor from the chop pool at a discount while rivals panic.")
    if targets:
        top = targets[0]
        lead += f" Top target: {top.player.name} at ${top.suggested_bid}."
    lead += f" Predicted chop: {chopped.name}."
    return lead


# ============================================================
#  SAMPLE DATA
# ============================================================

def _sample():
    """One week of a guillotine league: 8 teams, mixed projections,
    a projected chop whose roster will flood waivers, and free agents."""
    # players: (id, name, pos, team, proj, stdev, volume, owner)
    raw = [
        # my roster (roster_id "r1") — a couple weak spots on purpose
        ("p01","Bijan Robinson","RB","ATL",18.5,4.2,0.82,"r1"),
        ("p02","Nico Collins","WR","HOU",15.1,5.8,0.71,"r1"),
        ("p03","Boom Bust WR","WR","LV",11.0,9.5,0.40,"r1"),   # landmine starter
        ("p04","Streaming TE","TE","CHI",7.2,6.1,0.33,"r1"),   # volatile starter
        ("p05","Safe QB","QB","BUF",19.8,3.9,0.90,"r1"),
        # the projected-chop team (roster_id "r8") — floods waivers
        ("p10","Consistent RB","RB","IND",14.9,3.1,0.78,"r8"), # SAFE — target
        ("p11","Volume WR","WR","CIN",13.7,4.0,0.74,"r8"),     # SAFE — target
        ("p12","Dual-Threat QB","QB","PHI",21.2,4.4,0.88,"r8"),# ANCHOR — target
        ("p13","Bye-week TE","TE","SEA",5.0,3.0,0.25,"r8"),
        # free agents on the wire now
        ("p20","Ascending Slot WR","WR","MIA",10.8,3.4,0.62,None), # safe FA
        ("p21","Handcuff RB","RB","SF",6.5,5.5,0.20,None),         # volatile
        ("p22","Deep Sleeper","WR","NE",8.9,7.8,0.35,None),        # landmine
        # filler owned players on other teams
        ("p30","Other RB","RB","GB",12.0,4.5,0.60,"r2"),
        ("p31","Other WR","WR","DET",13.0,5.0,0.65,"r3"),
    ]
    players = [PlayerProj(*r) for r in raw]

    teams = [
        Team("r1","You",             faab_left=64, proj_points_this_week=118.0,
             starters=["p01","p02","p03","p04","p05"]),
        Team("r2","Chalk Chuck",     faab_left=40, proj_points_this_week=131.0, starters=["p30"]),
        Team("r3","Waiver Wendy",    faab_left=12, proj_points_this_week=126.0, starters=["p31"]),
        Team("r4","Boom Brandon",    faab_left=88, proj_points_this_week=109.0, starters=[]),
        Team("r5","Steady Sofia",    faab_left=55, proj_points_this_week=124.0, starters=[]),
        Team("r6","Reach Rob",       faab_left=30, proj_points_this_week=115.0, starters=[]),
        Team("r7","Homer Hank",      faab_left=71, proj_points_this_week=120.0, starters=[]),
        Team("r8","Doomed Dave",     faab_left=22, proj_points_this_week=103.0, starters=[]),  # chop
    ]
    return teams, players


# ============================================================
#  CLI / demo
# ============================================================

if __name__ == "__main__":
    teams, players = _sample()

    print("=" * 64)
    print("GUILLOTINE SURVIVAL BOARD  —  floor over ceiling")
    print("=" * 64)
    ranked = compute_survival(players)
    print(f"{'PLAYER':22}{'POS':5}{'PROJ':>6}{'FLOOR':>7}{'SURV':>7}  TIER")
    print("-" * 64)
    for p in ranked[:10]:
        print(f"{p.name:22}{p.position:5}{p.proj:6.1f}{p.floor:7.1f}"
              f"{p.survival_score:7.1f}  {p.tier}")

    print("\n" + "=" * 64)
    print("WEEK 6 — WAIVER BOARD  (chop pool + FAAB bids)")
    print("=" * 64)
    board = waiver_board(week=6, my_roster_id="r1", teams=teams, players=players)
    print("READ:", board.summary)
    print(f"\nYour FAAB left: ${board.my_faab_left}   On the block: "
          f"{'YES' if board.i_am_on_block else 'no'}")
    print("Chop watch:",
          ", ".join(f"{n} (+{m})" for n, m in board.chop_watch))
    print("Incoming from predicted chop:", ", ".join(board.incoming_pool))
    print("-" * 64)
    print(f"{'TARGET':22}{'BID':>6}{'MAX':>6}   WHY")
    for t in board.targets:
        print(f"{t.player.name:22}${t.suggested_bid:<5}${t.max_bid:<5}  {t.reason}")

    # emit JSON for the frontend
    payload = {
        "survival_board": [
            {"name":p.name,"pos":p.position,"team":p.nfl_team,"proj":p.proj,
             "floor":round(p.floor,1),"survival":p.survival_score,"tier":p.tier,
             "owned": p.owned_by is not None}
            for p in ranked
        ],
        "waiver": {
            "week": board.week, "my_team": board.my_team,
            "my_faab_left": board.my_faab_left,
            "i_am_on_block": board.i_am_on_block,
            "summary": board.summary,
            "chop_watch": board.chop_watch,
            "incoming_pool": board.incoming_pool,
            "targets": [
                {"name":t.player.name,"pos":t.player.position,
                 "tier":t.player.tier,"bid":t.suggested_bid,"max":t.max_bid,
                 "reason":t.reason,"fills_hole":t.fills_hole}
                for t in board.targets
            ],
        },
    }
    with open("guillotine.json","w") as fh:
        json.dump(payload, fh, indent=2)
    print("\nWrote guillotine.json")
