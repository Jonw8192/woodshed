"""FAAB rules module — transparent, reusable across divisions."""

from typing import Tuple


def propose_faab_range(
    opportunity_score: float,
    role_certainty: str = "medium",
    remaining_budget: int = 200,
    season_budget: int = 200,
) -> Tuple[str, str]:
    """
    Transparent rules for $200 season-long FAAB.
    Returns (range_string, rationale).
    Never invents exact bids.
    """
    remaining_pct = remaining_budget / season_budget if season_budget else 1.0
    scale = max(0.35, min(remaining_pct, 1.0))

    if opportunity_score >= 70 and role_certainty == "high":
        low = max(15, int(28 * scale))
        high = max(low + 5, int(48 * scale))
        why = "Verified high opportunity + clear sustainable role. Priority range."
    elif opportunity_score >= 50:
        low = max(5, int(12 * scale))
        high = max(low + 3, int(28 * scale))
        why = "Solid emerging usage. Competitive but not max bid."
    elif opportunity_score >= 30:
        low = 2
        high = max(8, int(15 * scale))
        why = "Limited sample or competition. Speculative only."
    else:
        low, high = 1, 4
        why = "Insufficient verified opportunity. Minimal or pass."

    return f"${low}-${high}", why
