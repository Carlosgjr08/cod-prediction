"""Compare model probabilities against sportsbook odds.

Fill in data/odds.csv with live outright-winner decimal odds, then the
report shows: implied probability (vig-adjusted), model probability,
edge, EV per $1, and a quarter-Kelly stake suggestion.

A bet is only flagged when the model edge clears EDGE_THRESHOLD — and
given how thin the input data is, treat flags as "worth a closer look",
not "smash the bet".
"""

import csv

EDGE_THRESHOLD = 0.05   # minimum model-vs-market edge to flag
KELLY_FRACTION = 0.25   # quarter Kelly: sane given model uncertainty


def load_odds(path: str) -> dict:
    odds = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            raw = (row["decimal_odds"] or "").strip()
            if raw:
                odds[row["team"]] = float(raw)
    return odds


def analyze(model_probs: dict, odds: dict) -> list[dict]:
    """model_probs: {team: P(champion)}. odds: {team: decimal odds}."""
    if not odds:
        return []
    raw_implied = {t: 1.0 / o for t, o in odds.items()}
    overround = sum(raw_implied.values())
    rows = []
    for team, o in odds.items():
        p_model = model_probs.get(team, 0.0)
        p_market = raw_implied[team] / overround if overround > 0 else 0.0
        edge = p_model - p_market
        ev = p_model * o - 1.0
        kelly = max(0.0, (p_model * o - 1.0) / (o - 1.0)) if o > 1.0 else 0.0
        rows.append({
            "team": team,
            "decimal_odds": o,
            "market_prob": p_market,
            "model_prob": p_model,
            "edge": edge,
            "ev_per_dollar": ev,
            "stake_frac": kelly * KELLY_FRACTION,
            "flag": edge >= EDGE_THRESHOLD and ev > 0,
        })
    rows.sort(key=lambda r: r["edge"], reverse=True)
    return rows
