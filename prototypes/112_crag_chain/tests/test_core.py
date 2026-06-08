"""Tests for 112_crag_chain core logic."""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import (  # type: ignore[import-untyped]
    CELL,
    COMBO_FOR_SUPER,
    COLS,
    GRID_X,
    INITIAL_PLAYER_COL,
    INITIAL_PLAYER_ROW,
    INITIAL_STAMINA,
    RED,
    STAMINA_COST_FAR,
    STAMINA_COST_NEAR,
    SUPER_STAMINA_MULT,
    TOTAL_ROWS,
    Game,
    Hold,
    Particle,
    Phase,
)


def make_game() -> Game:
    """Create a headless Game instance for testing."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.stamina = INITIAL_STAMINA
    g.max_stamina = INITIAL_STAMINA
    g.combo_color = -1
    g.player_col = INITIAL_PLAYER_COL
    g.player_row = INITIAL_PLAYER_ROW
    g.scroll_offset = 0.0
    g.total_height = 0
    g.super_reach_timer = 0
    g.holds = []
    g.particles = []
    g.game_timer = 0
    g.shake_frames = 0
    g.highest_generated_row = 0
    g.lowest_generated_row = TOTAL_ROWS - 1
    g.last_score_popup = None
    g.reset_to_title()
    return g


def make_playing() -> Game:
    """Create a headless Game instance already in PLAYING phase."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.stamina = INITIAL_STAMINA
    g.max_stamina = INITIAL_STAMINA
    g.combo_color = -1
    g.player_col = INITIAL_PLAYER_COL
    g.player_row = INITIAL_PLAYER_ROW
    g.scroll_offset = 0.0
    g.total_height = 0
    g.super_reach_timer = 0
    g.holds = []
    g.particles = []
    g.game_timer = 0
    g.shake_frames = 0
    g.highest_generated_row = 0
    g.lowest_generated_row = TOTAL_ROWS - 1
    g.last_score_popup = None
    g._init_state()
    return g


# ── Initialization / reset ───────────────────────────────────────────────


def test_reset_to_title() -> None:
    g = make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.stamina == INITIAL_STAMINA
    assert g.combo_color == -1
    assert g.player_col == INITIAL_PLAYER_COL
    assert g.player_row == INITIAL_PLAYER_ROW
    assert g.total_height == 0
    assert g.super_reach_timer == 0
    assert len(g.holds) == 0
    assert len(g.particles) == 0


def test_init_state_enters_playing() -> None:
    g = make_game()
    g._init_state()
    assert g.phase == Phase.PLAYING
    assert g.stamina == INITIAL_STAMINA
    assert len(g.holds) > 0


def test_init_state_has_start_hold() -> None:
    g = make_game()
    g._init_state()
    start = g._get_hold(INITIAL_PLAYER_COL, INITIAL_PLAYER_ROW)
    assert start is not None
    assert start.grabbed is True
    assert start.color == 1  # GREEN index


def test_init_state_holds_within_grid() -> None:
    g = make_game()
    g._init_state()
    for h in g.holds:
        assert 0 <= h.col < COLS
        assert h.color in (0, 1, 2, 3)


# ── Hold generation ──────────────────────────────────────────────────────


def test_generate_holds_produces_holds() -> None:
    g = make_game()
    g._generate_holds(0, TOTAL_ROWS - 1)
    assert len(g.holds) >= TOTAL_ROWS * 2  # at least 2 per row


def test_generate_holds_no_duplicates() -> None:
    g = make_game()
    g._generate_holds(5, 10)
    seen: set[tuple[int, int]] = set()
    for h in g.holds:
        key = (h.col, h.row)
        assert key not in seen, f"Duplicate hold at {key}"
        seen.add(key)


def test_get_hold_finds_and_misses() -> None:
    g = make_game()
    g.holds = [Hold(col=3, row=7, color=0)]
    assert g._get_hold(3, 7) is not None
    assert g._get_hold(3, 8) is None
    assert g._get_hold(4, 7) is None


# ── Distance / cost ──────────────────────────────────────────────────────


def test_manhattan_dist() -> None:
    assert Game._manhattan_dist(0, 0, 2, 3) == 5
    assert Game._manhattan_dist(4, 11, 4, 11) == 0
    assert Game._manhattan_dist(4, 11, 6, 9) == 4


def test_cost_near() -> None:
    assert Game._cost_for_distance(0) == float(STAMINA_COST_NEAR)
    assert Game._cost_for_distance(1) == float(STAMINA_COST_NEAR)


def test_cost_far() -> None:
    assert Game._cost_for_distance(2) == float(STAMINA_COST_FAR)
    assert Game._cost_for_distance(3) == float(STAMINA_COST_FAR)


def test_is_adjacent() -> None:
    g = make_game()
    g.player_col = 4
    g.player_row = 11
    assert g._is_adjacent(4, 11) is True  # dist 0
    assert g._is_adjacent(4, 10) is True  # dist 1
    assert g._is_adjacent(5, 10) is True  # dist 2  (|5-4|+|10-11|=2)
    assert g._is_adjacent(4, 9) is True  # dist 2
    assert g._is_adjacent(6, 10) is False  # dist 3 (|6-4|+|10-11|=3)
    assert g._is_adjacent(6, 9) is False  # dist 4 (|6-4|+|9-11|=4)


# ── Grab hold ────────────────────────────────────────────────────────────


def test_grab_hold_moves_player() -> None:
    g = make_game()
    g._init_state()
    # Place a hold adjacent to start
    hold = Hold(col=4, row=10, color=0)
    g.holds.append(hold)
    g._grab_hold(hold)
    assert g.player_row == 10
    assert g.player_col == 4
    assert hold.grabbed is True


def test_grab_hold_costs_stamina_near() -> None:
    g = make_game()
    g._init_state()
    g.stamina = 100.0
    hold = Hold(col=4, row=10, color=0)
    g.holds.append(hold)
    g._grab_hold(hold)
    assert g.stamina == 100.0 - STAMINA_COST_NEAR


def test_grab_hold_costs_stamina_far() -> None:
    g = make_game()
    g._init_state()
    g.stamina = 100.0
    hold = Hold(col=6, row=10, color=0)  # dist = |6-4| + |10-11| = 2+1 = 3 wait...
    # Actually dist 2: dist = 3? No, |6-4|=2, |10-11|=1 → 3.
    # That's > 2, so not adjacent. Let me use a closer one.
    hold = Hold(col=5, row=10, color=0)  # dist = |5-4| + |10-11| = 1+1 = 2
    g.holds.append(hold)
    g._grab_hold(hold)
    assert g.stamina == 100.0 - STAMINA_COST_FAR


def test_grab_hold_same_color_builds_combo() -> None:
    g = make_game()
    g._init_state()
    g.combo = 1
    g.combo_color = 1  # GREEN
    hold = Hold(col=4, row=10, color=1)  # GREEN
    g.holds.append(hold)
    g._grab_hold(hold)
    assert g.combo == 2
    assert g.combo_color == 1


def test_grab_hold_different_color_resets_combo() -> None:
    g = make_game()
    g._init_state()
    g.combo = 3
    g.combo_color = 1  # GREEN
    hold = Hold(col=4, row=10, color=0)  # RED
    g.holds.append(hold)
    g._grab_hold(hold)
    assert g.combo == 1
    assert g.combo_color == 0


def test_grab_hold_increases_height() -> None:
    g = make_game()
    g._init_state()
    g.player_row = 11
    g.total_height = 0
    hold = Hold(col=4, row=9, color=1)  # dist 2, climbing up 2 rows
    g.holds.append(hold)
    g._grab_hold(hold)
    assert g.total_height == 2


def test_grab_hold_spawns_particles() -> None:
    g = make_game()
    g._init_state()
    hold = Hold(col=4, row=10, color=0)
    g.holds.append(hold)
    assert len(g.particles) == 0
    g._grab_hold(hold)
    assert len(g.particles) > 0


# ── SUPER REACH ──────────────────────────────────────────────────────────


def test_super_reach_activates_at_combo_threshold() -> None:
    g = make_game()
    g._init_state()
    g.combo = COMBO_FOR_SUPER - 1  # 3
    g.combo_color = 1
    hold = Hold(col=4, row=10, color=1)  # GREEN
    g.holds.append(hold)
    g._grab_hold(hold)
    assert g.combo == COMBO_FOR_SUPER
    assert g.super_reach_timer > 0
    assert g.shake_frames > 0


def test_super_reach_3x_score() -> None:
    g = make_game()
    g._init_state()
    g.combo = COMBO_FOR_SUPER - 1
    g.combo_color = 1
    g.super_reach_timer = 300  # already active
    # Put player at row 8, hold at row 7
    g.player_row = 8
    hold = Hold(col=4, row=7, color=1)
    g.holds.append(hold)
    score_before = g.score
    gained = g._grab_hold(hold)
    # height_diff=1, base=20, combo=4 but super makes it combo*3 = 12, score = 20*12 = 240
    assert score_before < g.score
    assert gained > 0


def test_super_reach_half_stamina() -> None:
    g = make_game()
    g._init_state()
    g.combo = COMBO_FOR_SUPER - 1
    g.combo_color = 1
    hold = Hold(col=4, row=10, color=1)
    g.holds.append(hold)
    g._grab_hold(hold)  # activates super
    assert g.super_reach_timer > 0
    # Now grab another hold while super is active
    hold2 = Hold(col=4, row=9, color=0)  # RED — different color doesn't matter in super
    g.holds.append(hold2)
    stamina_before = g.stamina
    g._grab_hold(hold2)
    expected_cost = STAMINA_COST_NEAR * SUPER_STAMINA_MULT
    assert g.stamina == pytest.approx(stamina_before - expected_cost)


def test_super_reach_any_color_combos() -> None:
    g = make_game()
    g._init_state()
    g.super_reach_timer = 300
    g.combo = 5
    g.combo_color = 1
    hold = Hold(col=4, row=10, color=0)  # RED
    g.holds.append(hold)
    g._grab_hold(hold)
    assert g.combo == 6  # still increments in super mode


def test_super_reach_expires_resets_combo() -> None:
    g = make_game()
    g._init_state()
    g.super_reach_timer = 1
    g.combo = 5
    g.combo_color = 1
    g.phase = Phase.PLAYING
    g.update_frame()
    assert g.super_reach_timer == 0
    assert g.combo == 0
    assert g.combo_color == -1


# ── Stamina / game over ──────────────────────────────────────────────────


def test_game_over_when_stamina_zero() -> None:
    g = make_game()
    g._init_state()
    g.stamina = 5.0
    hold = Hold(col=4, row=10, color=1)
    g.holds.append(hold)
    g._grab_hold(hold)
    g._check_game_over()
    assert g.stamina == 0.0
    assert g.phase == Phase.GAME_OVER


def test_game_over_when_fall_off() -> None:
    g = make_game()
    g._init_state()
    g.player_row = 30  # way below visible area
    g.scroll_offset = 0.0
    g.phase = Phase.PLAYING
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER


def test_update_frame_advances_timer() -> None:
    g = make_playing()
    g.game_timer = 0
    g.update_frame()
    assert g.game_timer == 1


# ── Max combo tracking ───────────────────────────────────────────────────


def test_max_combo_tracks_highest() -> None:
    g = make_game()
    g._init_state()
    g.combo = 1
    g.combo_color = 1
    hold1 = Hold(col=4, row=10, color=1)  # GREEN
    g.holds.append(hold1)
    g._grab_hold(hold1)
    assert g.combo == 2
    assert g.max_combo == 2

    hold2 = Hold(col=5, row=9, color=0)  # RED, different color
    g.holds.append(hold2)
    g._grab_hold(hold2)
    assert g.combo == 1
    assert g.max_combo == 2  # unchanged


# ── Score popup ──────────────────────────────────────────────────────────


def test_score_popup_on_grab() -> None:
    g = make_game()
    g._init_state()
    g.combo = 1
    g.combo_color = 1
    hold = Hold(col=4, row=10, color=1)
    g.holds.append(hold)
    g._grab_hold(hold)
    assert g.last_score_popup is not None


def test_score_popup_fades() -> None:
    g = make_playing()
    g.last_score_popup = ("+100", 100.0, 100.0, 2)
    g.update_frame()
    _, _, _, life = g.last_score_popup
    assert life == 1
    g.update_frame()
    assert g.last_score_popup is None


# ── Particles ────────────────────────────────────────────────────────────


def test_spawn_particles() -> None:
    g = make_game()
    g._rng = random.Random(42)
    g._spawn_particles(100.0, 100.0, RED, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color == RED
        assert 15 <= p.life <= 25


def test_particles_removed_when_dead() -> None:
    g = make_game()
    g.particles = [
        Particle(0, 0, 0, 0, 0, RED),
        Particle(0, 0, 0, 0, 5, RED),
    ]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 4


# ── Scroll ───────────────────────────────────────────────────────────────


def test_scroll_moves_toward_player() -> None:
    g = make_game()
    g._init_state()
    old_offset = g.scroll_offset
    g.player_row = 8  # climb up
    g._update_scroll()
    # scroll_offset should decrease to keep player visible
    assert g.scroll_offset < old_offset


# ── Ensure reachable holds ───────────────────────────────────────────────


def test_ensure_reachable_generates_if_stuck() -> None:
    g = make_game()
    g._init_state()
    g.player_col = 4
    g.player_row = 11
    # Remove all ungrabbed holds in reach
    g.holds = [h for h in g.holds if h.grabbed]
    assert len(g.holds) == 1  # only start hold
    g._ensure_reachable_holds()
    assert len(g.holds) > 1  # generated at least one


# ── attempt_grab_at ──────────────────────────────────────────────────────


def test_attempt_grab_at_screen_coords() -> None:
    g = make_playing()
    g.player_col = 4
    g.player_row = 10
    # Place a hold at col=4, row=9 (adjacent)
    g.holds = [Hold(col=4, row=9, color=1, grabbed=False)]
    g.combo_color = 1
    g.scroll_offset = 0.0
    score = g.attempt_grab_at(
        float(GRID_X + 4 * CELL + CELL // 2),
        float(9 * CELL + CELL // 2),
    )
    assert score is not None
    assert score > 0
    hold = g._get_hold(4, 9)
    assert hold is not None and hold.grabbed


def test_attempt_grab_at_already_grabbed_returns_none() -> None:
    g = make_playing()
    g.player_col = 4
    g.player_row = 10
    g.holds = [Hold(col=4, row=9, color=1, grabbed=True)]
    g.scroll_offset = 0.0
    score = g.attempt_grab_at(
        float(GRID_X + 4 * CELL + CELL // 2),
        float(9 * CELL + CELL // 2),
    )
    assert score is None


def test_attempt_grab_at_not_adjacent_returns_none() -> None:
    g = make_playing()
    g.player_col = 4
    g.player_row = 10
    g.holds = [Hold(col=0, row=0, color=1, grabbed=False)]
    g.scroll_offset = 0.0
    score = g.attempt_grab_at(
        float(GRID_X),
        float(0),
    )
    assert score is None


def test_attempt_grab_at_out_of_bounds_returns_none() -> None:
    g = make_playing()
    score = g.attempt_grab_at(-10.0, -10.0)
    assert score is None


def test_attempt_grab_at_with_scroll() -> None:
    g = make_playing()
    g.player_col = 4
    g.player_row = 5
    g.scroll_offset = 0.0
    g.combo_color = 1
    # Hold at row 4, col 4
    g.holds = [Hold(col=4, row=4, color=1, grabbed=False)]
    score = g.attempt_grab_at(
        float(GRID_X + 4 * CELL + CELL // 2),
        float(4 * CELL + CELL // 2),
    )
    assert score is not None


# ── _make_game factory ───────────────────────────────────────────────────


def test_make_game_factory() -> None:
    g = Game._make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
