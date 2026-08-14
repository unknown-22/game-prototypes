"""test_imports.py — Headless logic tests for 307_origami_chain (ORIGAMI CHAIN).

Uses Game.__new__ + _init_state to bypass pyxel.init/pyxel.run.
Tests pure-logic methods only (never pyxel.btn/mouse/input wrappers).
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import Game, Particle, FloatingText, Phase  # noqa: E402

RED, LIME, DARK_BLUE, YELLOW, ORANGE = 8, 11, 5, 10, 9
WHITE = 7


def _make_game() -> Game:
    g = Game.__new__(Game)
    g._init_state()
    g.rng = random.Random(42)
    g.reset()
    return g


def _set_paper(g: Game, grid: list[list[int]]) -> None:
    g.paper = [list(row) for row in grid]
    g.rows = len(grid)
    g.cols = len(grid[0])


def _fresh(g: Game) -> None:
    g.combo = 0
    g.max_combo = 0
    g.score = 0
    g.heat = 0.0
    g.super_mode = False
    g.super_timer = 0
    g.phase = Phase.PLAYING


# ---------------------------------------------------------------- constants

def test_constants() -> None:
    assert Game.CELL == 22
    assert Game.MAX_HEAT == 100
    assert Game.SUPER_DURATION == 300
    assert Game.TIME_START == 3600
    assert len(Game.COLOR_VALS) == 5
    assert Game.COLOR_VALS[:4] == (8, 11, 5, 10)  # RED, LIME, DARK_BLUE, YELLOW


def test_phase_members() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.CRANE_COMPLETE in Phase
    assert Phase.GAME_OVER in Phase


def test_dataclasses() -> None:
    p = Particle(x=1.0, y=2.0, vx=0.5, vy=-1.0, life=10, color=RED)
    assert p.life == 10 and p.color == RED and p.gravity == 0.12
    t = FloatingText(x=5, y=6, text="+10", life=45, color=WHITE)
    assert t.text == "+10" and t.life == 45


# ---------------------------------------------------------------- init state

def test_init_state_defaults() -> None:
    g = _make_game()
    assert g.rows == 8 and g.cols == 8
    assert g.num_colors == 3
    assert g.score == 0 and g.combo == 0 and g.max_combo == 0
    assert g.heat == 0.0
    assert g.time_left == 3600
    assert g.phase == Phase.PLAYING
    assert len(g.paper) == 8 and len(g.paper[0]) == 8
    assert g.super_mode is False


# ---------------------------------------------------------------- resolve_pair

def test_resolve_pair_same_color_fuses() -> None:
    g = _make_game()
    result, fused, mismatch = g._resolve_pair(1, 1)
    assert result == 1 and fused is True and mismatch is False


def test_resolve_pair_diff_color_mismatch() -> None:
    g = _make_game()
    result, fused, mismatch = g._resolve_pair(0, 1)
    assert result == -1 and fused is False and mismatch is True


def test_resolve_pair_dead_is_neutral() -> None:
    g = _make_game()
    result, fused, mismatch = g._resolve_pair(-1, 2)
    assert result == -1 and fused is False and mismatch is False
    result, fused, mismatch = g._resolve_pair(2, -1)
    assert result == -1 and fused is False and mismatch is False


def test_resolve_pair_super_mode_fuses_any() -> None:
    g = _make_game()
    g.super_mode = True
    result, fused, mismatch = g._resolve_pair(0, 1)
    assert result == 0 and fused is True and mismatch is False


# ---------------------------------------------------------------- fold vertical

def test_fold_vertical_halves_and_scores() -> None:
    g = _make_game()
    _fresh(g)
    _set_paper(g, [[0, 0], [1, 1]])
    gained = g._fold_vertical()
    assert g.cols == 1 and g.rows == 2
    assert gained == 30  # 10*1 + 10*2
    assert g.score == 30
    assert g.combo == 2 and g.max_combo == 2
    assert g.paper == [[0], [1]]


def test_fold_vertical_mismatch_adds_heat_resets_combo() -> None:
    g = _make_game()
    _fresh(g)
    g.combo = 5
    g.max_combo = 5
    _set_paper(g, [[0, 1], [0, 0]])
    g._fold_vertical()
    assert g.cols == 1 and g.rows == 2
    assert g.heat == 10.0
    assert g.combo == 0
    assert g.paper == [[-1], [0]]


def test_fold_vertical_dead_pair_neutral() -> None:
    g = _make_game()
    _fresh(g)
    _set_paper(g, [[-1, 0], [1, 1]])
    g._fold_vertical()
    # dead pair adds no heat and no score; only the r=1 live fusion scores
    assert g.heat == 0.0
    assert g.score == 10
    assert g.combo == 1
    assert g.paper == [[-1], [1]]


def test_fold_vertical_super_mode_3x_multiplier() -> None:
    g = _make_game()
    _fresh(g)
    g.super_mode = True
    _set_paper(g, [[0, 1], [0, 1]])
    g._fold_vertical()
    # any-color fuse in super mode; mult=3 -> 10*1*3 + 10*2*3 = 90
    assert g.score == 90
    assert g.combo == 2
    assert g.paper == [[0], [0]]


def test_fold_vertical_noop_when_single_col() -> None:
    g = _make_game()
    _fresh(g)
    _set_paper(g, [[0], [1]])
    gained = g._fold_vertical()
    assert gained == 0 and g.cols == 1 and g.rows == 2


def test_fold_vertical_odd_width_middle_stays() -> None:
    g = _make_game()
    _fresh(g)
    # 3 cols -> new_cols = 2; middle col (c=1) has mirror==1 and stays
    _set_paper(g, [[0, 3, 0]])
    g._fold_vertical()
    assert g.cols == 2
    # c=0 mirror=2: 0 vs 0 fuse; middle 3 stays
    assert g.paper == [[0, 3]]


# ---------------------------------------------------------------- fold horizontal

def test_fold_horizontal_halves_and_scores() -> None:
    g = _make_game()
    _fresh(g)
    _set_paper(g, [[0, 0], [0, 0]])
    gained = g._fold_horizontal()
    assert g.rows == 1 and g.cols == 2
    assert gained == 30
    assert g.score == 30
    assert g.combo == 2
    assert g.paper == [[0, 0]]


def test_fold_horizontal_noop_when_single_row() -> None:
    g = _make_game()
    _fresh(g)
    _set_paper(g, [[0, 1]])
    gained = g._fold_horizontal()
    assert gained == 0 and g.rows == 1


# ---------------------------------------------------------------- super fold

def test_super_fold_triggers_at_combo_4() -> None:
    g = _make_game()
    _fresh(g)
    _set_paper(g, [[0] * 8 for _ in range(8)])
    g._fold_vertical()  # 8 rows x 4 pairs = 32 fusions
    assert g.super_mode is True
    assert g.super_timer == 300
    assert g.combo == 32 and g.max_combo == 32
    # score = 10*(1+2+3+4) + 3*10*(5+...+32) = 100 + 30*518 = 15640
    assert g.score == 15640


# ---------------------------------------------------------------- crane complete

def test_crane_complete_bonus_and_new_sheet() -> None:
    g = _make_game()
    _fresh(g)
    _set_paper(g, [[0], [0]])
    g._fold_horizontal()  # 2x1 -> 1x1 -> crane complete
    assert g.phase == Phase.CRANE_COMPLETE
    assert g.rows == 8 and g.cols == 8  # new sheet spawned
    # 1 fusion (10*1=10) + 500 bonus (live final cell)
    assert g.score == 510


def test_crane_complete_dead_cell_smaller_bonus() -> None:
    g = _make_game()
    _fresh(g)
    _set_paper(g, [[-1], [-1]])
    g._fold_horizontal()  # dead vs dead neutral -> final cell -1
    assert g.phase == Phase.CRANE_COMPLETE
    assert g.score == 100  # dead final cell bonus


# ---------------------------------------------------------------- difficulty

def test_difficulty_escalation() -> None:
    g = _make_game()
    g.time_left = 3000
    g._update_difficulty()
    assert g.num_colors == 3
    g.time_left = 2000
    g._update_difficulty()
    assert g.num_colors == 4
    g.time_left = 1000
    g._update_difficulty()
    assert g.num_colors == 5


# ---------------------------------------------------------------- heat & timer

def test_heat_game_over_at_threshold() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 100.0
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_heat_decay_when_below_threshold() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 50.0
    g._update_heat()
    assert abs(g.heat - 49.98) < 0.001
    assert g.phase == Phase.PLAYING


def test_heat_decay_frozen_in_super_mode() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 50.0
    g.super_mode = True
    g._update_heat()
    assert g.heat == 50.0


def test_add_heat_clamps_and_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 95.0
    g._add_heat(10.0)
    assert g.phase == Phase.GAME_OVER
    assert g.heat == 100.0


def test_timer_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.time_left = 1
    g._update_timer()
    assert g.time_left == 0
    assert g.phase == Phase.GAME_OVER


# ---------------------------------------------------------------- best score

def test_best_score_saved_on_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.score = 1234
    g.heat = 100.0
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 1234


def _run_all() -> None:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"  PASS {t.__name__}")
    print(f"\n{passed}/{len(tests)} tests passed")


if __name__ == "__main__":
    _run_all()
