from __future__ import annotations
import hashlib, json
from app.schemas.fantasy import ScoringSettings, RawStatProjection


def scoring_fingerprint(settings: ScoringSettings) -> str:
    payload = json.dumps(settings.model_dump(mode='json'), sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


def score_raw_projection(p: RawStatProjection, s: ScoringSettings) -> float:
    # Raw-stat projections must be complete enough for all exposed scoring dimensions.
    vals = p.model_dump()
    required = [
        'pass_yards','pass_tds','interceptions','rush_yards','rush_tds',
        'receptions','rec_yards','rec_tds','two_pt','fumbles'
    ]
    missing = [k for k in required if vals.get(k) is None]
    if missing:
        raise ValueError('raw_stats projection missing required fields: ' + ', '.join(missing))
    rec_bonus = s.te_rec_bonus if p.position == 'TE' else 0.0
    first_down = (
        (p.pass_first_downs or 0) * s.pass_first_down
        + (p.rush_first_downs or 0) * s.rush_first_down
        + (p.rec_first_downs or 0) * s.rec_first_down
    )
    yard_bonus = (
        (p.pass_300_games or 0) * s.bonus_pass_300
        + (p.rush_100_games or 0) * s.bonus_rush_100
        + (p.rec_100_games or 0) * s.bonus_rec_100
    )
    return (
        p.pass_yards * s.pass_yd + p.pass_tds * s.pass_td + p.interceptions * s.pass_int
        + p.rush_yards * s.rush_yd + p.rush_tds * s.rush_td
        + p.receptions * (s.rec + rec_bonus) + p.rec_yards * s.rec_yd + p.rec_tds * s.rec_td
        + p.two_pt * s.two_pt + p.fumbles * s.fumble + first_down + yard_bonus
    )
