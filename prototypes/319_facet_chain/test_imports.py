"""test_imports.py — Headless logic tests for FACET CHAIN (319_facet_chain).

Uses the Game.__new__(Game) bypass pattern to avoid pyxel.init/run. Logic
methods are pure (no pyxel.* calls) so they can be exercised directly. Sound is
routed through Game._sfx which is a no-op when _sfx_enabled is False (the
default after reset()).
"""

from __future__ import annotations

import math
import random
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import main as M
from main import FACET_COLORS, Facet, Game, Phase


def assert_close(a: float, b: float, tol: float = 1e-6) -> None:
    assert abs(a - b) < tol, f"{a!r} != {b!r}"


def make_game() -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(42)
    g.reset()
    return g


def set_facet(g: Game, idx: int, color: int, depth: int) -> None:
    g.facets[idx] = Facet(color=color, depth=depth)


# ---- 1. import / constants ----


def test_imports_no_pyxel_init() -> None:
    assert M.Game is Game
    assert M.Facet is Facet
    assert M.Phase is Phase
    assert len(FACET_COLORS) == 4
    assert M.FACET_COUNT == 6
    assert M.MAX_DEPTH == 3
    assert M.HEAT_MAX == 100.0
    assert M.HEAT_MISMATCH == 15.0
    assert M.COMBO_SUPER == 4
    assert M.SUPER_DURATION == 300
    assert M.TIMER_MAX == 3600
    assert M.GEM_BONUS == 100


# ---- 2. factory / initial state ----


def test_make_game_factory() -> None:
    g = make_game()
    assert g.phase == Phase.TITLE
    assert len(g.facets) == 6
    assert all(f.depth == 0 for f in g.facets)
    assert g.score == 0 and g.combo == 0 and g.max_combo == 0
    assert g.heat == 0.0 and g.gems_completed == 0
    assert g.super_timer == 0 and g.lap_color == 0
    assert g.frame == 0


# ---- 3. brilliance ----


def test_brilliance_min_depth_plus_one() -> None:
    g = make_game()
    assert g.brilliance() == 1
    set_facet(g, 0, 0, 1)
    assert g.brilliance() == 1  # one facet raised, others still 0
    for i in range(6):
        set_facet(g, i, 0, 1)
    assert g.brilliance() == 2


# ---- 4. match ----


def test_match_increments_combo_depth_score() -> None:
    g = make_game()
    g.lap_color = 0
    set_facet(g, 0, 0, 0)
    g._polish_facet(0)
    assert g.combo == 1
    assert g.facets[0].depth == 1
    assert g.score == 10  # 10 * 1 * 1


# ---- 5. mismatch ----


def test_mismatch_adds_heat_resets_combo_chips() -> None:
    g = make_game()
    g.lap_color = 0
    set_facet(g, 0, 1, 2)
    g.combo = 3
    g._polish_facet(0)
    assert g.heat == 15
    assert g.combo == 0
    assert g.facets[0].depth == 1


# ---- 6. SUPER ----


def test_super_activates_at_combo_4() -> None:
    g = make_game()
    g.lap_color = 0
    for i in range(4):
        set_facet(g, i, 0, 0)
        g._polish_facet(i)
    assert g.combo == 4
    assert g.super_timer == M.SUPER_DURATION


def test_super_matches_any_color_and_3x() -> None:
    g = make_game()
    g.lap_color = 0
    for i in range(4):
        set_facet(g, i, 0, 0)
        g._polish_facet(i)
    assert g.score == 100  # 10 + 20 + 30 + 40
    set_facet(g, 4, 2, 0)  # mismatched color
    g._polish_facet(4)
    assert g.combo == 5
    assert g.score == 100 + 10 * 5 * g.brilliance() * 3


def test_super_freezes_heat_and_lap() -> None:
    g = make_game()
    g.super_timer = M.SUPER_DURATION
    g.heat = 50.0
    g.lap_color = 0
    g.lap_timer = 5
    g._update_heat()
    g._update_lap()
    assert g.heat == 50.0
    assert g.lap_color == 0
    assert g.lap_timer == 5


# ---- 7. MAX_DEPTH no-op ----


def test_max_depth_polish_is_noop() -> None:
    g = make_game()
    g.lap_color = 0
    set_facet(g, 0, 0, M.MAX_DEPTH)
    g.combo = 2
    g.score = 100
    g.heat = 10.0
    g._polish_facet(0)
    assert g.combo == 2 and g.score == 100 and g.heat == 10.0
    assert g.facets[0].depth == M.MAX_DEPTH


# ---- 8. gem complete ----


def test_gem_complete() -> None:
    g = make_game()
    g.lap_color = 0
    g.combo = 5
    for i in range(5):
        set_facet(g, i, 0, M.MAX_DEPTH)
    set_facet(g, 5, 0, M.MAX_DEPTH - 1)
    g.score = 0
    g._polish_facet(5)
    assert g.gems_completed == 1
    assert g.combo == 6  # preserved across gems
    assert all(f.depth == 0 for f in g.facets)  # fresh gem
    # match gain 10*6*brilliance(4) + gem bonus 100*6
    assert g.score == 240 + 600


# ---- 9. heat threshold ----


def test_heat_game_over_before_decay() -> None:
    g = make_game()
    g.heat = M.HEAT_MAX
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.heat == M.HEAT_MAX  # no decay applied


# ---- 10. timer ----


def test_timer_game_over() -> None:
    g = make_game()
    g.frame = M.TIMER_MAX - 1
    g._update_timer()
    assert g.phase == Phase.GAME_OVER


# ---- 11. cycle interval escalation ----


def test_cycle_interval_range_and_monotonic() -> None:
    g = make_game()
    assert g._cycle_interval() == 20
    g.frame = M.TIMER_MAX
    assert g._cycle_interval() == 12
    g2 = make_game()
    prev = 10**9
    for fr in range(0, M.TIMER_MAX, 200):
        g2.frame = fr
        v = g2._cycle_interval()
        assert v <= prev
        assert 12 <= v <= 20
        prev = v


# ---- 12. chip lowers brilliance ----


def test_chip_lowers_brilliance() -> None:
    g = make_game()
    for i in range(6):
        set_facet(g, i, 0, 1)
    assert g.brilliance() == 2
    g.lap_color = 0
    set_facet(g, 0, 1, 1)  # mismatch
    g._polish_facet(0)
    assert g.facets[0].depth == 0
    assert g.brilliance() == 1


# ---- 13. facet hit detection ----


def test_facet_at() -> None:
    g = make_game()
    for i in range(6):
        a = math.radians(i * 60 - 90)
        x = int(round(M.GEM_CX + math.cos(a) * M.GEM_OUTER_R))
        y = int(round(M.GEM_CY + math.sin(a) * M.GEM_OUTER_R))
        assert g._facet_at(x, y) == i
    assert g._facet_at(0, 0) is None
    assert g._facet_at(319, 239) is None


if __name__ == "__main__":
    tests = sorted(
        (name, fn) for name, fn in globals().items() if name.startswith("test_") and callable(fn)
    )
    failures = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception:
            failures += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
