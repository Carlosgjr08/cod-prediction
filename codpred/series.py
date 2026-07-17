"""Series (best-of-N) win probability from a per-map win probability.

Maps are treated as i.i.d. — a simplification (mode order HP/SnD/CTL and
map vetoes create per-map variation), but standard for a first model.
"""

from functools import lru_cache


@lru_cache(maxsize=None)
def series_win_prob(p_map: float, best_of: int) -> float:
    """P(win first-to-ceil(best_of/2) race) given per-map win prob p_map."""
    need = best_of // 2 + 1

    @lru_cache(maxsize=None)
    def race(wins_a: int, wins_b: int) -> float:
        if wins_a == need:
            return 1.0
        if wins_b == need:
            return 0.0
        return p_map * race(wins_a + 1, wins_b) + (1 - p_map) * race(wins_a, wins_b + 1)

    return race(0, 0)
