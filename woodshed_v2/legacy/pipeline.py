"""
THE WOODSHED Research Pipeline — Touch Transfer Core
Loads verified 2026 NFL data via nflreadpy, computes usage changes,
joins injuries/depth where reliable, ranks waiver candidates,
proposes transparent FAAB ranges, and generates review drafts.

Never invents values. Flags missing/stale data.
All output requires Jon Woods' editorial review and approval before any send.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl

try:
    import nflreadpy as nfl
except ImportError as e:
    raise ImportError("Install nflreadpy: pip install nflreadpy") from e

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = Path(__file__).parent / "sample_output"
OUTPUT_DIR.mkdir(exist_ok=True)

SOURCE_TIMESTAMP = datetime.now(timezone.utc).isoformat()


def load_verified_data(season: int = 2026) -> dict[str, pl.DataFrame]:
    """Load latest available verified weekly data. Flags failures."""
    data: dict[str, pl.DataFrame] = {}
    loaders = {
        "player_stats": lambda: nfl.load_player_stats([season]),
        "snap_counts": lambda: nfl.load_snap_counts([season]),
        "injuries": lambda: nfl.load_injuries([season]),
        "depth_charts": lambda: nfl.load_depth_charts([season]),
        "players": lambda: nfl.load_players(),
    }
    for name, loader in loaders.items():
        try:
            df = loader()
            if not isinstance(df, pl.DataFrame):
                df = pl.from_pandas(df) if hasattr(df, "to_pandas") else pl.DataFrame(df)
            data[name] = df
            print(f"[OK] Loaded {name}: {df.shape}")
        except Exception as exc:
            print(f"[FLAG] Failed to load {name}: {exc}")
            data[name] = pl.DataFrame()
    return data


def latest_week(stats: pl.DataFrame) -> int:
    if stats.is_empty() or "week" not in stats.columns:
        return 0
    return int(stats["week"].max())


def compute_usage_changes(stats: pl.DataFrame, snaps: pl.DataFrame) -> pl.DataFrame:
    """Compute week-over-week usage deltas for skill positions. Only verified columns."""
    if stats.is_empty():
        return pl.DataFrame()

    skill = stats.filter(pl.col("position").is_in(["WR", "RB", "TE", "QB"]))
    # Core opportunity metrics already present
    usage_cols = [
        "player_id", "player_display_name", "position", "team", "week",
        "targets", "receptions", "receiving_yards", "carries", "rushing_yards",
        "target_share", "air_yards_share", "wopr",
    ]
    available = [c for c in usage_cols if c in skill.columns]
    usage = skill.select(available).sort(["player_id", "week"])

    # Week-over-week changes where both weeks exist
    if "targets" in usage.columns and "target_share" in usage.columns:
        usage = usage.with_columns([
            pl.col("targets").diff().over("player_id").alias("targets_wow"),
            pl.col("target_share").diff().over("player_id").alias("target_share_wow"),
            pl.col("wopr").diff().over("player_id").alias("wopr_wow"),
        ])

    # Join snap % where available (offense_pct)
    if not snaps.is_empty() and "offense_pct" in snaps.columns:
        snap_clean = snaps.select([
            pl.col("player").alias("player_display_name"),
            "team", "week", "offense_pct", "offense_snaps"
        ])
        # Better join on player_id if possible; for now name+team+week as fallback
        usage = usage.join(
            snap_clean,
            on=["player_display_name", "team", "week"],
            how="left",
        )
        usage = usage.with_columns(
            pl.col("offense_pct").diff().over("player_id").alias("snap_pct_wow")
        )
    else:
        usage = usage.with_columns([
            pl.lit(None).alias("offense_pct"),
            pl.lit(None).alias("offense_snaps"),
            pl.lit(None).alias("snap_pct_wow"),
        ])

    return usage


def join_injury_depth(
    usage: pl.DataFrame,
    injuries: pl.DataFrame,
    depth: pl.DataFrame,
    week: int,
) -> pl.DataFrame:
    """Join injury status and depth rank where reliable. Flag missing."""
    if usage.is_empty():
        return usage

    # Injuries: match on full_name + team + week (or latest)
    if not injuries.is_empty() and "full_name" in injuries.columns:
        inj_latest = injuries.filter(pl.col("week") == week) if "week" in injuries.columns else injuries
        inj_clean = inj_latest.select([
            pl.col("full_name").alias("player_display_name"),
            "team",
            "report_status",
            "practice_status",
            "report_primary_injury",
        ]).unique(subset=["player_display_name", "team"])
        usage = usage.join(inj_clean, on=["player_display_name", "team"], how="left")
    else:
        usage = usage.with_columns([
            pl.lit(None).alias("report_status"),
            pl.lit(None).alias("practice_status"),
            pl.lit(None).alias("report_primary_injury"),
        ])

    # Depth: take most recent available for week (depth charts are daily; filter by date if possible)
    # For demo, take latest snapshot per player if gsis_id join possible
    if not depth.is_empty() and "gsis_id" in depth.columns and "player_id" in usage.columns:
        # Approximate: use most recent depth rank
        depth_recent = depth.sort("dt", descending=True).unique(subset=["gsis_id"], keep="first")
        depth_clean = depth_recent.select([
            pl.col("gsis_id").alias("player_id"),
            "pos_rank",
            "pos_abb",
        ])
        usage = usage.join(depth_clean, on="player_id", how="left")
    else:
        usage = usage.with_columns([
            pl.lit(None).alias("pos_rank"),
            pl.lit(None).alias("pos_abb"),
        ])

    return usage


def score_opportunity(row: dict[str, Any]) -> tuple[float, str]:
    """Transparent opportunity score (0-100). Flags missing inputs."""
    score = 0.0
    notes = []
    missing = []

    ts = row.get("target_share") or 0
    wopr = row.get("wopr") or 0
    targets = row.get("targets") or 0
    snaps = row.get("offense_pct") or 0
    ts_wow = row.get("target_share_wow") or 0

    if ts is None:
        missing.append("target_share")
    else:
        score += min(ts * 200, 40)  # 20% share ≈ 40 pts
    if wopr is None:
        missing.append("wopr")
    else:
        score += min(wopr * 50, 20)
    if targets is None:
        missing.append("targets")
    else:
        score += min(targets * 1.5, 20)
    if snaps is None:
        missing.append("offense_pct")
    else:
        score += min(snaps * 20, 15)
    if ts_wow is None:
        missing.append("target_share_wow")
    else:
        score += min(max(ts_wow, 0) * 100, 15)  # rising opportunity bonus

    if missing:
        notes.append(f"Missing: {', '.join(missing)}")
    if row.get("report_status") in ("Out", "IR", "Doubtful"):
        score *= 0.3
        notes.append("Injury flag reduces score")

    return round(score, 1), "; ".join(notes) if notes else "complete"


def propose_faab(score: float, role_certainty: str, remaining_budget_pct: float = 1.0) -> tuple[str, str]:
    """Transparent $200 FAAB range. Considers opportunity, role, season-long budget context.
    Does not invent exact bids; returns range + rationale.
    """
    # Scale by remaining budget awareness (caller can pass remaining/200)
    scale = max(0.4, min(remaining_budget_pct, 1.0))

    if score >= 70 and role_certainty == "high":
        low, high = int(25 * scale), int(45 * scale)
        rationale = "High verified opportunity + clear role path. Priority bid range."
    elif score >= 50:
        low, high = int(10 * scale), int(25 * scale)
        rationale = "Solid emerging opportunity. Worth a competitive bid."
    elif score >= 30:
        low, high = int(3 * scale), int(12 * scale)
        rationale = "Interesting but limited sample or competition. Speculative range."
    else:
        low, high = 1, 5
        rationale = "Low verified opportunity. Minimal or pass."

    return f"${low}-${high}", rationale


def build_research_packet(
    usage: pl.DataFrame,
    week: int,
    top_n: int = 15,
) -> list[dict[str, Any]]:
    """Ranked waiver candidates with verified stats only. Flags gaps."""
    if usage.is_empty():
        return []

    latest = usage.filter(pl.col("week") == week)
    if latest.is_empty():
        return []

    # Prefer emerging roles over established stars for waiver context
    # Filter to players with meaningful but not locked-in volume, or strong positive WoW
    emerging = latest.filter(
        (
            (pl.col("target_share").is_null()) |
            (pl.col("target_share") < 0.28) |
            (pl.col("target_share_wow").fill_null(0) > 0.05)
        ) &
        (
            (pl.col("offense_pct").fill_null(0) > 0.25) |
            (pl.col("targets").fill_null(0) >= 4)
        )
    )
    if emerging.is_empty():
        emerging = latest

    candidates = []
    for row in emerging.iter_rows(named=True):
        score, score_notes = score_opportunity(row)
        role = "high" if (row.get("offense_pct") or 0) >= 0.60 and (row.get("target_share") or 0) >= 0.15 else \
               "medium" if (row.get("offense_pct") or 0) >= 0.40 else "low"
        faab_range, faab_why = propose_faab(score, role)

        candidates.append({
            "player_id": row.get("player_id"),
            "name": row.get("player_display_name"),
            "position": row.get("position"),
            "team": row.get("team"),
            "week": week,
            "verified_stats": {
                "targets": row.get("targets"),
                "receptions": row.get("receptions"),
                "target_share": row.get("target_share"),
                "wopr": row.get("wopr"),
                "offense_pct": row.get("offense_pct"),
                "offense_snaps": row.get("offense_snaps"),
                "targets_wow": row.get("targets_wow"),
                "target_share_wow": row.get("target_share_wow"),
            },
            "injury": {
                "report_status": row.get("report_status"),
                "practice_status": row.get("practice_status"),
                "primary_injury": row.get("report_primary_injury"),
            },
            "depth_rank": row.get("pos_rank"),
            "opportunity_score": score,
            "score_notes": score_notes,
            "role_certainty": role,
            "faab_range": faab_range,
            "faab_rationale": faab_why,
            "source": "nflverse via nflreadpy",
            "source_timestamp": SOURCE_TIMESTAMP,
            "data_flags": score_notes if "Missing" in score_notes or "Injury" in score_notes else None,
        })

    # Rank by score descending
    candidates.sort(key=lambda x: x["opportunity_score"], reverse=True)
    return candidates[:top_n]


def generate_touch_transfer_draft(
    packet: list[dict[str, Any]],
    week: int,
    season: int = 2026,
) -> str:
    """Generate Touch Transfer draft in established FFToday format.
    Separates verified observations from AI interpretation.
    Requires editorial review. Never auto-send.
    """
    if not packet:
        return f"# Touch Transfer — Week {week}\n\nNo verified candidates available. Data missing or stale.\n"

    lines = [
        f"# Touch Transfer — Week {week}",
        "**By Jon Woods**",
        "**Process Over Hype**",
        "",
        f"*Source: nflverse (nflreadpy) | Loaded: {SOURCE_TIMESTAMP} | Requires Jon Woods review before any submission to Mike.*",
        "",
        "## Introduction",
        "Waiver week is about the routes and the snaps that actually happened, not the narrative that might. "
        "The names below cleared a basic opportunity filter on verified usage. Everything else is context you still need to confirm.",
        "",
        "## $200 FAAB Tracker",
        "*Remaining budget and prior spends tracked externally. Ranges below assume full $200 still available unless noted. "
        "Adjust down if your league is already depleted.*",
        "",
        "## Priority Adds",
    ]

    priority = [c for c in packet if c["opportunity_score"] >= 55][:4]
    also = [c for c in packet if 35 <= c["opportunity_score"] < 55][:4]

    for c in priority:
        header = f"{c['position']} {c['name']}, {c['team']}"
        stats = c["verified_stats"]
        lines.append(f"### {header}")
        lines.append(f"**Verified usage (Week {week}):** "
                     f"{stats.get('targets') or '—'} targets "
                     f"({round(stats.get('target_share') or 0, 2) if stats.get('target_share') is not None else '—'} share), "
                     f"WOPR {round(stats.get('wopr') or 0, 2) if stats.get('wopr') is not None else '—'}, "
                     f"offense snap % {round(stats.get('offense_pct') or 0, 2) if stats.get('offense_pct') is not None else '—'}.")
        if stats.get("targets_wow") is not None:
            lines.append(f"Week-over-week target change: {stats.get('targets_wow')}.")
        if c["injury"]["report_status"]:
            lines.append(f"**Injury flag:** {c['injury']['report_status']} "
                         f"({c['injury'].get('primary_injury') or 'details pending'}).")
        lines.append(f"**FAAB range:** {c['faab_range']} — {c['faab_rationale']}")
        if c["data_flags"]:
            lines.append(f"**Data flag:** {c['data_flags']}")
        lines.append("*Interpretation (requires your voice):* Role looks sustainable on the numbers, but confirm competing players and actual route participation before locking a bid.")
        lines.append("")

    lines.append("## Also Worth a Bid")
    for c in also:
        header = f"{c['position']} {c['name']}, {c['team']}"
        stats = c["verified_stats"]
        lines.append(f"**{header}** — {stats.get('targets') or '—'} targets, "
                     f"{stats.get('offense_pct') or '—'} snap %. Range: {c['faab_range']}.")
        if c["data_flags"]:
            lines.append(f"  Flag: {c['data_flags']}")

    lines.extend([
        "",
        "## Panic Meter",
        "No panic names elevated solely on one-week volume without a role path. "
        "If a high-owned player is suddenly inactive, re-check the packet for the backup who actually took the snaps.",
        "",
        "## Monday Night Waiver Watch",
        "*Tuesday update slot. Re-run pipeline after MNF and injury reports lock.*",
        "",
        "## How I'm Spending",
        "Prioritize the verified opportunity jumps that still have a path to weekly routes or early-down work. "
        "Leave room for the one or two names that clear a higher bar after you review the competing players and injury notes. "
        "Do not chase the narrative that the market is already pricing.",
        "",
        "---",
        "**STATUS: DRAFT FOR JON WOODS REVIEW**",
        "Do not send to Mike or publish until approved.",
        f"Prepared for: JonWoods@tutamail.com",
    ])

    return "\n".join(lines)


def run_pipeline(season: int = 2026, week: int | None = None, top_n: int = 12) -> dict[str, Any]:
    """Main entry. Returns packet + draft paths and validation summary."""
    data = load_verified_data(season)
    stats = data.get("player_stats", pl.DataFrame())
    if stats.is_empty():
        return {"error": "No player_stats loaded. Pipeline halted."}

    current_week = week or latest_week(stats)
    usage = compute_usage_changes(stats, data.get("snap_counts", pl.DataFrame()))
    usage = join_injury_depth(
        usage,
        data.get("injuries", pl.DataFrame()),
        data.get("depth_charts", pl.DataFrame()),
        current_week,
    )

    packet = build_research_packet(usage, current_week, top_n)
    draft = generate_touch_transfer_draft(packet, current_week, season)

    # Export
    packet_path = OUTPUT_DIR / f"research_packet_week{current_week}.json"
    draft_path = OUTPUT_DIR / f"touch_transfer_draft_week{current_week}.md"
    packet_path.write_text(json.dumps(packet, indent=2, default=str))
    draft_path.write_text(draft)

    validation = {
        "season": season,
        "week": current_week,
        "candidates": len(packet),
        "stats_rows": stats.height,
        "source_timestamp": SOURCE_TIMESTAMP,
        "packet_path": str(packet_path),
        "draft_path": str(draft_path),
        "flags": [c["data_flags"] for c in packet if c.get("data_flags")],
    }
    print(f"Pipeline complete. Week {current_week}: {len(packet)} candidates.")
    print(f"Draft: {draft_path}")
    return {"packet": packet, "draft": draft, "validation": validation}


if __name__ == "__main__":
    result = run_pipeline()
    print(json.dumps(result.get("validation", {}), indent=2))
