"""test_imports.py — Headless logic tests for ICE CARVE.

Tests core game logic without initializing Pyxel (no display needed).
Uses Game.__new__ pattern to bypass pyxel.init().
"""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/306_ice_carve")
from main import (
    BASE_SCORE,
    CELL,
    DISPLAY_SCALE,
    EMPTY,
    FPS,
    GRID_PIXELS,
    GRID_SIZE,
    GRID_X,
    GRID_Y,
    HEAT_DECAY,
    HEAT_MAX,
    HEAT_MISMATCH,
    MELT_INTERVAL_END,
    MELT_INTERVAL_START,
    MELT_SPREAD_CHANCE,
    MELTED,
    NUM_COLORS,
    SCREEN_H,
    SCREEN_W,
    SHARD_COLORS,
    SPAWN_INTERVAL_END,
    SPAWN_INTERVAL_START,
    SUPER_FRAMES,
    SUPER_MULT,
    SUPER_THRESHOLD,
    TARGET_SHARDS,
    TOTAL_FRAMES,
    FloatText,
    Game,
    Particle,
    Phase,
)


def _make_game(seed: int = 42) -> Game:
    g: Game = Game.__new__(Game)
    g.best_score = 0
    g.reset()
    g.rng = random.Random(seed)
    return g


def _fill(g: Game, value: int) -> None:
    g.grid = [[value for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]


# ── Constants ──────────────────────────────────────────────────────────


def test_constants() -> None:
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert DISPLAY_SCALE == 2
    assert FPS == 60
    assert GRID_SIZE == 8
    assert CELL == 24
    assert GRID_PIXELS == 192
    assert len(SHARD_COLORS) == NUM_COLORS == 4
    assert TOTAL_FRAMES == 3600
    assert SUPER_FRAMES == 300
    assert SUPER_THRESHOLD == 4
    assert HEAT_MAX == 100.0
    assert HEAT_MISMATCH == 15
    assert TARGET_SHARDS == 24
    assert MELT_INTERVAL_START > MELT_INTERVAL_END
    assert SPAWN_INTERVAL_START > SPAWN_INTERVAL_END
    assert 0.0 < MELT_SPREAD_CHANCE < 1.0
    assert GRID_X + GRID_PIXELS <= SCREEN_W
    assert GRID_Y + GRID_PIXELS <= SCREEN_H


# ── Dataclasses ────────────────────────────────────────────────────────


def test_particle_fields() -> None:
    p = Particle(x=1.0, y=2.0, vx=0.5, vy=-0.5, life=15, color=8)
    assert p.x == 1.0 and p.life == 15 and p.color == 8


def test_float_text_fields() -> None:
    ft = FloatText(x=5.0, y=6.0, text="+10", life=40, color=7)
    assert ft.text == "+10" and ft.life == 40


# ── Reset / board ──────────────────────────────────────────────────────


def test_reset_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.timer == TOTAL_FRAMES
    assert g.chisel_color == 0
    assert g.best_score == 0


def test_board_has_target_shards() -> None:
    g = _make_game()
    assert g._shard_count() == TARGET_SHARDS
    assert len(g.grid) == GRID_SIZE
    assert all(len(row) == GRID_SIZE for row in g.grid)


def test_best_score_persists_across_reset() -> None:
    g = _make_game()
    g.best_score = 500
    g.reset()
    assert g.best_score == 500


# ── Click: match ───────────────────────────────────────────────────────


def test_match_builds_combo_and_score() -> None:
    g = _make_game()
    _fill(g, MELTED)
    g.chisel_color = 0
    g.grid[0][0] = 0
    g._click_cell(0, 0)
    assert g.combo == 1
    assert g.score == BASE_SCORE
    assert g.chisel_color == 0
    assert g.last_color == 0


def test_match_combo_multiplies_score() -> None:
    g = _make_game()
    _fill(g, MELTED)
    g.chisel_color = 0
    g.grid[0][0] = 0  # (col 0, row 0)
    g.grid[1][0] = 0  # (col 0, row 1)
    g._click_cell(0, 0)
    s1 = g.score
    g._click_cell(0, 1)
    assert g.combo == 2
    assert g.score == s1 + BASE_SCORE * 2


def test_mismatch_resets_combo_and_adds_heat() -> None:
    g = _make_game()
    _fill(g, MELTED)
    g.chisel_color = 0
    g.grid[0][0] = 0
    g.grid[1][0] = 1  # wrong color
    g._click_cell(0, 0)
    assert g.combo == 1
    g._click_cell(0, 1)
    assert g.combo == 0
    assert g.heat == HEAT_MISMATCH
    assert g.grid[1][0] == MELTED


def test_click_empty_or_melted_is_noop() -> None:
    g = _make_game()
    _fill(g, MELTED)
    g.grid[0][0] = EMPTY
    g.grid[1][0] = MELTED
    before_score = g.score
    g._click_cell(0, 0)
    g._click_cell(0, 1)
    assert g.score == before_score
    assert g.combo == 0
    assert g.heat == 0.0


def test_click_out_of_bounds_is_noop() -> None:
    g = _make_game()
    g._click_cell(-1, 0)
    g._click_cell(GRID_SIZE, 0)
    assert g.score == 0


# ── SUPER mode ─────────────────────────────────────────────────────────


def test_combo_4_activates_super() -> None:
    g = _make_game()
    _fill(g, MELTED)
    g.chisel_color = 0
    for i in range(4):
        g.grid[i][0] = 0  # (col 0, row i)
    for i in range(4):
        g._click_cell(0, i)
    assert g.super_timer == SUPER_FRAMES


def test_super_rainbow_matches_any_color() -> None:
    g = _make_game()
    _fill(g, MELTED)
    g.chisel_color = 0
    g.super_timer = SUPER_FRAMES
    g.grid[0][0] = 3  # different color
    g._click_cell(0, 0)
    assert g.combo == 1  # matched despite color mismatch
    assert g.heat == 0.0


def test_super_multiplies_score_3x() -> None:
    g = _make_game()
    _fill(g, MELTED)
    g.chisel_color = 0
    g.super_timer = SUPER_FRAMES
    g.combo = 1
    g.grid[0][0] = 0
    before = g.score
    g._click_cell(0, 0)
    # combo becomes 2 -> 10 * 2 * 3 = 60
    assert g.score == before + int(BASE_SCORE * 2 * SUPER_MULT)


# ── Melt CA ────────────────────────────────────────────────────────────


def test_spread_melt_snapshots_prior_melted() -> None:
    g = _make_game(seed=1)
    _fill(g, EMPTY)
    g.grid[4][4] = MELTED
    for _ in range(200):
        g._spread_melt()
    # Melt only ever spreads; the source cell stays melted.
    assert g.grid[4][4] == MELTED


def test_spread_melt_single_pass_bounds() -> None:
    g = _make_game(seed=0)
    _fill(g, EMPTY)
    g.grid[0][0] = MELTED
    g.rng = random.Random(0)
    g._spread_melt()
    # after ONE pass, at most the source plus its 4 orthogonal neighbors
    melted = sum(1 for row in g.grid for cell in row if cell == MELTED)
    assert melted <= 5


# ── Heat / timer / game over ───────────────────────────────────────────


def test_heat_exactly_100_triggers_game_over_before_decay() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = HEAT_MAX
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_heat_decays_when_below_max() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 50.0 - HEAT_DECAY


def test_heat_never_goes_below_zero() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_super_freezes_heat_decay() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 50.0
    g.super_timer = 100
    g._update_heat()
    assert g.heat == 50.0


def test_timer_expiry_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.timer = 1
    g._tick_timer()
    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER


def test_game_over_updates_best_score() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.score = 777
    g.timer = 0
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 777


# ── Escalation ─────────────────────────────────────────────────────────


def test_escalate_shrinks_intervals_over_time() -> None:
    g = _make_game()
    g.timer = TOTAL_FRAMES
    g._escalate()
    assert g.melt_interval == MELT_INTERVAL_START
    assert g.spawn_interval == SPAWN_INTERVAL_START

    g.timer = 0
    g._escalate()
    assert g.melt_interval == MELT_INTERVAL_END
    assert g.spawn_interval == SPAWN_INTERVAL_END


# ── Spawn / maintain board ─────────────────────────────────────────────


def test_spawn_shard_fills_empty_cell() -> None:
    g = _make_game()
    _fill(g, EMPTY)
    g._spawn_shard()
    assert g._shard_count() == 1


def test_spawn_shard_no_empty_noop() -> None:
    g = _make_game()
    _fill(g, MELTED)
    g._spawn_shard()
    assert g._shard_count() == 0


def test_maintain_board_restores_target() -> None:
    g = _make_game()
    _fill(g, EMPTY)
    g._maintain_board()
    assert g._shard_count() == TARGET_SHARDS


# ── Run ────────────────────────────────────────────────────────────────


def main() -> None:
    tests = [
        test_constants,
        test_particle_fields,
        test_float_text_fields,
        test_reset_state,
        test_board_has_target_shards,
        test_best_score_persists_across_reset,
        test_match_builds_combo_and_score,
        test_match_combo_multiplies_score,
        test_mismatch_resets_combo_and_adds_heat,
        test_click_empty_or_melted_is_noop,
        test_click_out_of_bounds_is_noop,
        test_combo_4_activates_super,
        test_super_rainbow_matches_any_color,
        test_super_multiplies_score_3x,
        test_spread_melt_snapshots_prior_melted,
        test_spread_melt_single_pass_bounds,
        test_heat_exactly_100_triggers_game_over_before_decay,
        test_heat_decays_when_below_max,
        test_heat_never_goes_below_zero,
        test_super_freezes_heat_decay,
        test_timer_expiry_game_over,
        test_game_over_updates_best_score,
        test_escalate_shrinks_intervals_over_time,
        test_spawn_shard_fills_empty_cell,
        test_spawn_shard_no_empty_noop,
        test_maintain_board_restores_target,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  PASS  {test.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  FAIL  {test.__name__}: {e}")

    print(f"\n{passed} passed, {failed} failed out of {len(tests)}")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
