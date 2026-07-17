"""Elo ratings for CDL teams.

Priors come from final regular-season seeding (a proxy for CDL points,
which aggregate a full season of results we don't have match-by-match).
Ratings are then updated with the match log in data/matches.csv, using
map-score margin to scale each update.

With the full season match log this converges to a real Elo; with the
seven headline results currently in the CSV it behaves as
"seeding prior + adjustments for the biggest recent results", which is
the honest description of what we can support from gathered data.
"""

import csv
from dataclasses import dataclass, field

BASE = 1500.0
SEED_SPREAD = 26.0   # Elo points per seed position above/below average
K = 40.0             # high K: few matches, want recent results to matter
MAJOR_FINAL_BONUS = 12.0  # small prior bump per Major grand-final appearance


def seed_prior(seed: int, major_finals: int = 0) -> float:
    return BASE + SEED_SPREAD * (4.5 - seed) + MAJOR_FINAL_BONUS * major_finals


def expected(r_a: float, r_b: float) -> float:
    """P(team A wins a single map) from rating difference."""
    return 1.0 / (1.0 + 10 ** ((r_b - r_a) / 400.0))


def margin_multiplier(score_w: int, score_l: int) -> float:
    """Scale update by how lopsided the series was (3-0 counts more than 4-3)."""
    total = score_w + score_l
    if total == 0:
        return 1.0
    return 0.5 + 1.5 * (score_w - score_l) / total


@dataclass
class EloModel:
    ratings: dict = field(default_factory=dict)

    @classmethod
    def from_files(cls, teams_csv: str, matches_csv: str) -> "EloModel":
        model = cls()
        major_finals: dict[str, int] = {}
        rows = []
        with open(matches_csv) as f:
            for row in csv.DictReader(f):
                rows.append(row)
                if row["stage"] == "Grand Final":
                    for side in ("team_a", "team_b"):
                        major_finals[row[side]] = major_finals.get(row[side], 0) + 1
        with open(teams_csv) as f:
            for row in csv.DictReader(f):
                team = row["team"]
                model.ratings[team] = seed_prior(
                    int(row["seed"]), major_finals.get(team, 0)
                )
        rows.sort(key=lambda r: r["date"])
        for row in rows:
            model.update(
                row["team_a"], row["team_b"],
                int(row["score_a"]), int(row["score_b"]),
            )
        return model

    def update(self, team_a: str, team_b: str, score_a: int, score_b: int) -> None:
        r_a, r_b = self.ratings[team_a], self.ratings[team_b]
        exp_a = expected(r_a, r_b)
        actual_a = 1.0 if score_a > score_b else 0.0
        mult = margin_multiplier(max(score_a, score_b), min(score_a, score_b))
        delta = K * mult * (actual_a - exp_a)
        self.ratings[team_a] = r_a + delta
        self.ratings[team_b] = r_b - delta

    def map_win_prob(self, team_a: str, team_b: str) -> float:
        return expected(self.ratings[team_a], self.ratings[team_b])
