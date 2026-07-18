"""Monte Carlo simulation of the CDL Champs 2026 double-elimination bracket.

Bracket flow (8-team double elim, CDL layout):

  WB R1:  A = 1v8   B = 4v5   C = 2v7   D = 3v6
  WB SF1: W(A) vs W(B)      WB SF2: W(C) vs W(D)
  WB F:   W(SF1) vs W(SF2)
  LB R1:  L(A) vs L(B)  ;  L(C) vs L(D)
  LB R2:  W(LBR1-ab) vs L(WB SF2)  ;  W(LBR1-cd) vs L(WB SF1)   (crossed)
  LB SF:  winners of LB R2
  LB F:   W(LB SF) vs L(WB F)
  GF:     W(WB F) vs W(LB F)   (Bo9, no bracket reset)

Completed matches from data/bracket_state.json are fixed; everything else
is sampled. Per-simulation Gaussian noise is added to each rating to
reflect uncertainty in the ratings themselves (the match log is thin).
"""

import json
import random
from collections import defaultdict

from .elo import expected
from .series import series_win_prob

RATING_NOISE_SIGMA = 65.0  # per-sim rating uncertainty; widens placement tails


def load_bracket(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def _play(ratings, a, b, best_of, rng, fixed_winner=None):
    """Sample a series; if fixed_winner is set (completed match), lock it in."""
    if fixed_winner is not None:
        return (a, b) if fixed_winner == a else (b, a)
    p_map = expected(ratings[a], ratings[b])
    p_series = series_win_prob(round(p_map, 4), best_of)
    return (a, b) if rng.random() < p_series else (b, a)


def simulate(model, bracket: dict, n_sims: int = 100_000, seed: int = 7):
    rng = random.Random(seed)
    bo = bracket["best_of"]
    bo_def, bo_gf = bo["default"], bo["grand_final"]

    champion = defaultdict(int)
    placements = defaultdict(lambda: defaultdict(int))

    r1 = bracket["winners_r1"]
    done = bracket.get("completed", {})

    for _ in range(n_sims):
        ratings = {
            t: r + rng.gauss(0.0, RATING_NOISE_SIGMA)
            for t, r in model.ratings.items()
        }

        wb_w, wb_l = [], []
        for m in r1:
            if m["winner"]:
                w = m["winner"]
                l = m["low_seed"] if w == m["high_seed"] else m["high_seed"]
            else:
                w, l = _play(ratings, m["high_seed"], m["low_seed"], bo_def, rng)
            wb_w.append(w)
            wb_l.append(l)

        sf1_w, sf1_l = _play(ratings, wb_w[0], wb_w[1], bo_def, rng, done.get("wb_sf1"))
        sf2_w, sf2_l = _play(ratings, wb_w[2], wb_w[3], bo_def, rng, done.get("wb_sf2"))

        wbf_w, wbf_l = _play(ratings, sf1_w, sf2_w, bo["winners_final"], rng, done.get("wb_final"))

        lb1a_w, lb1a_l = _play(ratings, wb_l[0], wb_l[1], bo_def, rng, done.get("lb_r1a"))
        lb1b_w, lb1b_l = _play(ratings, wb_l[2], wb_l[3], bo_def, rng, done.get("lb_r1b"))

        lb2a_w, lb2a_l = _play(ratings, lb1a_w, sf2_l, bo_def, rng, done.get("lb_r2a"))
        lb2b_w, lb2b_l = _play(ratings, lb1b_w, sf1_l, bo_def, rng, done.get("lb_r2b"))

        lbsf_w, lbsf_l = _play(ratings, lb2a_w, lb2b_w, bo_def, rng, done.get("lb_sf"))
        lbf_w, lbf_l = _play(ratings, lbsf_w, wbf_l, bo["losers_final"], rng, done.get("lb_final"))
        gf_w, gf_l = _play(ratings, wbf_w, lbf_w, bo_gf, rng, done.get("grand_final"))

        champion[gf_w] += 1
        placements[gf_w][1] += 1
        placements[gf_l][2] += 1
        placements[lbf_l][3] += 1
        placements[lbsf_l][4] += 1
        for t in (lb2a_l, lb2b_l):
            placements[t][5] += 1  # 5th-6th
        for t in (lb1a_l, lb1b_l):
            placements[t][7] += 1  # 7th-8th

    teams = list(model.ratings)
    result = {}
    for t in teams:
        dist = {p: placements[t][p] / n_sims for p in (1, 2, 3, 4, 5, 7)}
        result[t] = {
            "champion": champion[t] / n_sims,
            "top2": dist[1] + dist[2],
            "top3": dist[1] + dist[2] + dist[3],
            "placement_dist": dist,
        }
    return result


def expected_payouts(sim_results: dict, payouts: dict) -> dict:
    """payouts: {placement: usd}. 5th/6th and 7th/8th are ties."""
    out = {}
    for team, res in sim_results.items():
        d = res["placement_dist"]
        out[team] = (
            d[1] * payouts[1] + d[2] * payouts[2] + d[3] * payouts[3]
            + d[4] * payouts[4] + d[5] * payouts[5] + d[7] * payouts[7]
        )
    return out
