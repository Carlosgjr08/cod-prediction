# cod-prediction

Prediction model for **CoD Champs 2026** (Call of Duty League Championship, July 16–19, Las Vegas, $2M pool): Elo ratings + Monte Carlo simulation of the live double-elimination bracket, with a betting-edge calculator to compare model probabilities against sportsbook odds.

## Quick start

```bash
python3 run_prediction.py            # 100k sims, writes predictions/champs_2026_report.md
python3 run_prediction.py --sims 500000
```

No dependencies beyond the Python 3 standard library.

## How it works

1. **Ratings** (`codpred/elo.py`) — each team gets a prior from its regular-season seed (a proxy for CDL points) plus a small bump per Major grand-final appearance, then Elo updates run over the match log in `data/matches.csv`, weighted by series margin (a 3–0 moves ratings more than a 4–3).
2. **Series math** (`codpred/series.py`) — Elo difference → per-map win probability → best-of-N series probability (Bo5 rounds, Bo9 grand final).
3. **Simulation** (`codpred/simulate.py`) — 100k Monte Carlo runs of the remaining bracket. Completed matches in `data/bracket_state.json` are locked in; Gaussian noise is added to ratings each run to reflect how thin the input data is. Outputs champion %, full placement distributions, and expected prize money.
4. **Betting** (`codpred/betting.py`) — put live decimal odds in `data/odds.csv` and the report adds vig-adjusted market probability, model edge, EV per $1, and quarter-Kelly stake suggestions. Bets are only flagged when the edge clears 5%.

## Updating the data (do this before trusting any number)

- **`data/matches.csv`** — currently holds only headline results (four Major grand finals + Champs day 1). The model works but leans on seeding priors. Copy the full 2026 season match log from breakingpoint.gg or Liquipedia into this CSV and ratings get much sharper.
- **`data/bracket_state.json`** — update `winner`/`score` as Champs matches finish (OpTic vs Miami Heretics was still pending as of 2026-07-17), then re-run.
- **`data/odds.csv`** — fill in live outright odds from your book right before comparing; odds move fast mid-tournament.
- **`data/payouts.csv`** — prize split is an estimate; fix it if the official breakdown is published.

## Current bracket state (as of July 17, 2026)

Winners R1: Gentle Mates 3–0 KOI · Falcons 3–1 LA Thieves (upset) · FaZe 3–1 G2 · OpTic vs Heretics pending.

## Known limitations

- Maps are i.i.d. — no HP/SnD/CTL mode splits, map vetoes, or head-to-head style effects.
- No roster-change, LAN-form, or momentum adjustments.
- Seeds 2/3 and 5/6/7 were inferred from the confirmed round-1 pairings.

**Disclaimer:** entertainment/analysis only, not financial advice. Even a good model has huge variance in a single 8-team bracket — never bet more than you can afford to lose.
