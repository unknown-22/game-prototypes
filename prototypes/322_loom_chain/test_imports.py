"""test_imports.py — Headless logic tests for 322_loom_chain (LOOM CHAIN).

Runs standalone (uv run python prototypes/322_loom_chain/test_imports.py) or via pytest.
Constructs Game via __new__ to bypass pyxel.init/pyxel.run, seeds rng for determinism.
Never calls methods that touch pyxel input state (update/draw, pyxel.btn/mouse).
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # noqa: E402
    COLS,
    FLAW,
    HEAT_MAX,
    LIME,
    RED,
    SUPER_DURATION,
    WEAVE_COLORS,
    FloatText,
    Game,
    Phase,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(seed)
    g.reset()
    return g


# ── import / dataclass / phase ──────────────────────────────────────────────


def test_imports_and_phase():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


def test_dataclass_construction():
    ft = FloatText(x=5, y=6, text="+10", color=8, life=30)
    assert ft.text == "+10"
    assert ft.life == 30


# ── reset ───────────────────────────────────────────────────────────────────


def test_reset_initial_state():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.cells == [-1] * COLS
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.consecutive_perfect == 0
    assert g.score == 0
    assert len(g.warp_colors) == COLS
    assert g.fabric_log == []


def test_reset_preserves_best_score():
    g = _make_game()
    g.best_score = 1234
    g.reset()
    assert g.best_score == 1234
    assert g.score == 0


# ── weave ───────────────────────────────────────────────────────────────────


def test_weave_match():
    g = _make_game()
    g.warp_colors = [RED] + [LIME] * (COLS - 1)
    g.weft_color = RED
    g._weave(0)
    assert g.cells[0] == RED
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score == 10


def test_weave_mismatch():
    g = _make_game()
    g.warp_colors = [LIME] + [RED] * (COLS - 1)
    g.weft_color = RED
    g._weave(0)
    assert g.cells[0] == FLAW
    assert g.heat == 15
    assert g.combo == 0
    assert g.score == 0


def test_weave_noop_already_woven():
    g = _make_game()
    g.cells[0] = RED
    g.combo = 2
    g._weave(0)
    assert g.combo == 2
    assert g.score == 0


def test_combo_four_triggers_super():
    g = _make_game()
    g.warp_colors = [RED] * COLS
    g.weft_color = RED
    g.combo = 3
    g._weave(0)
    assert g.combo == 4
    assert g.super_timer == SUPER_DURATION


def test_super_any_color_3x():
    g = _make_game()
    g.super_timer = SUPER_DURATION
    g.combo = 4
    g.weft_color = RED
    g.warp_colors = [LIME] * COLS  # no match without super
    g._weave(0)
    assert g.cells[0] == RED
    assert g.combo == 5
    assert g.score == 150  # 10 * 5 * 3


# ── complete row ────────────────────────────────────────────────────────────


def test_complete_row_all_perfect():
    g = _make_game()
    g.cells = [RED] * COLS
    g.consecutive_perfect = 0
    g.combo = 5
    g._complete_row()
    assert g.consecutive_perfect == 1
    assert g.score == 100 + 6 * 20 * 2  # 340
    assert len(g.fabric_log) == 1
    assert g.cells == [-1] * COLS
    assert g.combo == 5  # combo preserved across rows


def test_complete_row_with_flaw_breaks_streak():
    g = _make_game()
    g.cells = [RED, RED, RED, RED, RED, FLAW]
    g.consecutive_perfect = 2
    g._complete_row()
    assert g.consecutive_perfect == 0
    assert g.score == 5 * 20  # 100


def test_complete_row_all_flaw_tangled():
    g = _make_game()
    g.cells = [FLAW] * COLS
    g.heat = 0
    g._complete_row()
    assert g.heat == 15
    assert g.consecutive_perfect == 0


# ── heat ────────────────────────────────────────────────────────────────────


def test_update_heat_game_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = HEAT_MAX
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_heat_decay():
    g = _make_game()
    g.heat = 50
    g._update_heat()
    assert abs(g.heat - 49.98) < 0.001


def test_heat_frozen_in_super():
    g = _make_game()
    g.super_timer = SUPER_DURATION
    g.heat = 50
    g._update_heat()
    assert g.heat == 50


# ── weft cycle / difficulty ─────────────────────────────────────────────────


def test_cycle_interval_ramp():
    g = _make_game()
    g.frame = 0
    assert g.cycle_interval() == 20
    g.frame = 1200
    assert g.cycle_interval() == 12
    g.frame = 3600
    assert g.cycle_interval() == 12


def test_advance_weft_cycles_in_order():
    g = _make_game()
    start = g.weft_color
    g.cycle_timer = g.cycle_interval() - 1
    g._advance_weft()
    assert g.weft_color == WEAVE_COLORS[(WEAVE_COLORS.index(start) + 1) % 4]
    assert g.cycle_timer == 0


def test_advance_weft_frozen_in_super():
    g = _make_game()
    g.super_timer = SUPER_DURATION
    start = g.weft_color
    g.cycle_timer = g.cycle_interval() - 1
    g._advance_weft()
    assert g.weft_color == start
    assert g.cycle_timer == g.cycle_interval() - 1


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
