#!/usr/bin/env python3
"""Run the CoD Champs 2026 prediction model and write a markdown report.

Usage:
    python3 run_prediction.py [--sims N]

Reads:  data/teams.csv, data/matches.csv, data/bracket_state.json,
        data/payouts.csv, data/odds.csv
Writes: predictions/champs_2026_report.md (and prints a summary)
"""

import argparse
import csv
import datetime
import os

from codpred.elo import EloModel
from codpred.simulate import load_bracket, simulate, expected_payouts
from codpred.betting import load_odds, analyze

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "predictions", "champs_2026_report.md")


def load_payouts() -> dict:
    payouts = {}
    with open(os.path.join(DATA, "payouts.csv")) as f:
        for row in csv.DictReader(f):
            payouts[int(row["placement"])] = float(row["payout_usd"])
    return payouts


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=100_000)
    args = ap.parse_args()

    model = EloModel.from_files(
        os.path.join(DATA, "teams.csv"), os.path.join(DATA, "matches.csv")
    )
    bracket = load_bracket(os.path.join(DATA, "bracket_state.json"))
    results = simulate(model, bracket, n_sims=args.sims)
    payouts = expected_payouts(results, load_payouts())
    odds_rows = analyze(
        {t: r["champion"] for t, r in results.items()},
        load_odds(os.path.join(DATA, "odds.csv")),
    )

    ranked = sorted(results.items(), key=lambda kv: kv[1]["champion"], reverse=True)

    lines = [
        "# CoD Champs 2026 — Model Predictions",
        "",
        f"Generated {datetime.date.today().isoformat()} · "
        f"{args.sims:,} Monte Carlo simulations · bracket state as of "
        f"{bracket['as_of']}",
        "",
        "## Ratings (Elo)",
        "",
        "| Team | Rating |",
        "|---|---|",
    ]
    for t, r in sorted(model.ratings.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {t} | {r:.0f} |")

    lines += [
        "",
        "## Tournament outcome probabilities",
        "",
        "| Team | Champion | Top 2 | Top 3 | 4th | 5th-6th | 7th-8th | Exp. payout |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for t, res in ranked:
        d = res["placement_dist"]
        lines.append(
            f"| {t} | {pct(res['champion'])} | {pct(res['top2'])} | "
            f"{pct(res['top3'])} | {pct(d[4])} | {pct(2 * d[5])} | "
            f"{pct(2 * d[7])} | ${payouts[t]:,.0f} |"
        )
    lines += [
        "",
        "Placement columns are per-slot probabilities (5th-6th and 7th-8th "
        "shown as the combined chance of landing in that tier). Expected "
        "payout uses the ESTIMATED prize split in data/payouts.csv.",
        "",
        "## Betting edges vs. market",
        "",
    ]
    if odds_rows:
        lines += [
            "| Team | Odds | Market prob | Model prob | Edge | EV/$1 | Stake (¼ Kelly) | Bet? |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for r in odds_rows:
            lines.append(
                f"| {r['team']} | {r['decimal_odds']:.2f} | {pct(r['market_prob'])} | "
                f"{pct(r['model_prob'])} | {pct(r['edge'])} | {r['ev_per_dollar']:+.2f} | "
                f"{pct(r['stake_frac'])} of bankroll | {'YES' if r['flag'] else 'no'} |"
            )
    else:
        lines.append(
            "*No odds entered yet. Fill in `data/odds.csv` with live decimal "
            "odds from your book, re-run, and this section will show implied "
            "vs. model probability, edge, EV, and quarter-Kelly stakes.*"
        )
    lines += [
        "",
        "## Caveats",
        "",
        "- The match log currently holds only headline results (4 Major grand "
        "finals + Champs day 1); ratings lean heavily on seeding priors. "
        "Adding the full season match log to `data/matches.csv` will sharpen this.",
        "- Maps are modeled i.i.d.; no mode-specific (HP/SnD/CTL) or map-veto modeling.",
        "- No roster-change or LAN-form adjustments.",
        "- Prize split is an estimate; seeds 2/3 and 5/6/7 assignments inferred "
        "from confirmed round-1 pairings.",
        "- This is analysis for entertainment — not financial advice. Bet only "
        "what you can afford to lose.",
        "",
    ]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write("\n".join(lines))

    print(f"Report written to {OUT}\n")
    print(f"{'Team':<22}{'Champ':>8}{'Top2':>8}{'Top3':>8}{'ExpPayout':>12}")
    for t, res in ranked:
        print(
            f"{t:<22}{pct(res['champion']):>8}{pct(res['top2']):>8}"
            f"{pct(res['top3']):>8}{'$' + format(payouts[t], ',.0f'):>12}"
        )


if __name__ == "__main__":
    main()
