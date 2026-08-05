"""Tests for Sky Surge — headless, no pyxel.init required."""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "prototypes/285_sky_surge")
from main import (
    COMBO_THRESHOLD,
    GAME_DURATION,
    HEAT_COMBO_COOL,
    HEAT_MAX,
    HEAT_WRONG,
    MAX_RINGS,
    PLAYER_SPEED,
    RING_COLORS,
    SCREEN_W,
    SUPER_MULTIPLIER,
    DivePhase,
    Game,
    Phase,
    Ring,
)


def _make_game() -> Game:
    """Factory: create Game bypassing pyxel.init via __new__."""
    g = Game.__new__(Game)
    g.rng = random.Random(42)
    g._init_game_state()
    g.phase = Phase.PLAYING
    return g


# --- Combo System ---
def test_match_increments_combo() -> None:
    g = _make_game()
    g.player_color_idx = 1  # LIME
    ring = Ring(x=g.player_x, y=g.player_y, color=RING_COLORS[1])
    g.rings = [ring]
    g._update_collisions()
    assert g.combo == 1
    assert ring.passed


def test_mismatch_resets_combo() -> None:
    g = _make_game()
    g.combo = 3
    g.player_color_idx = 0  # RED
    ring = Ring(x=g.player_x, y=g.player_y, color=RING_COLORS[1])  # LIME
    g.rings = [ring]
    g._update_collisions()
    assert g.combo == 0


def test_combo_4_activates_super_dive() -> None:
    g = _make_game()
    g.combo = 3
    g.player_color_idx = 0  # RED
    ring = Ring(x=g.player_x, y=g.player_y, color=RING_COLORS[0])  # RED
    g.rings = [ring]
    g._update_collisions()
    g._update_super_dive()
    assert g.combo == 4
    assert g.super_dive


def test_super_dive_any_color_matches() -> None:
    g = _make_game()
    g.super_dive = True
    g.super_dive_timer = 100
    g.combo = 5
    g.player_color_idx = 0
    ring = Ring(x=g.player_x, y=g.player_y, color=RING_COLORS[2])  # BLUE (different)
    g.rings = [ring]
    g.heat = 50
    g._update_collisions()
    assert g.combo == 6
    assert ring.passed
    assert g.heat < 50  # cooled down


def test_super_dive_ends_resets_combo() -> None:
    g = _make_game()
    g.super_dive = True
    g.super_dive_timer = 1
    g.combo = 10
    g._update_super_dive()
    assert not g.super_dive
    assert g.combo == 0


# --- HEAT System ---
def test_match_cools_heat() -> None:
    g = _make_game()
    g.heat = 50
    g.player_color_idx = 0
    ring = Ring(x=g.player_x, y=g.player_y, color=RING_COLORS[0])
    g.rings = [ring]
    g._update_collisions()
    assert g.heat == 50 + HEAT_COMBO_COOL


def test_mismatch_adds_heat() -> None:
    g = _make_game()
    g.heat = 20
    g.player_color_idx = 0
    ring = Ring(x=g.player_x, y=g.player_y, color=RING_COLORS[1])
    g.rings = [ring]
    g._update_collisions()
    assert g.heat == min(HEAT_MAX, 20 + HEAT_WRONG)


def test_heat_capped_at_100() -> None:
    g = _make_game()
    g.heat = 99
    g.heat += HEAT_WRONG
    g.heat = min(HEAT_MAX, g.heat)
    assert g.heat == HEAT_MAX


def test_heat_100_game_over() -> None:
    g = _make_game()
    g.heat = HEAT_MAX
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


# --- Scoring ---
def test_score_on_match() -> None:
    g = _make_game()
    g.combo = 1
    g.player_color_idx = 0
    ring = Ring(x=g.player_x, y=g.player_y, color=RING_COLORS[0])
    g.rings = [ring]
    old_score = g.score
    g._update_collisions()
    assert g.score == old_score + 10 * 2  # combo becomes 2


def test_super_dive_score_multiplier() -> None:
    g = _make_game()
    g.super_dive = True
    g.super_dive_timer = 100
    g.combo = 5
    g.player_color_idx = 0
    ring = Ring(x=g.player_x, y=g.player_y, color=RING_COLORS[0])
    g.rings = [ring]
    old_score = g.score
    g._update_collisions()
    expected = old_score + int(10 * 6 * SUPER_MULTIPLIER)
    assert g.score == expected


def test_landing_bonus() -> None:
    g = _make_game()
    g.dive_timer = 200
    old_score = g.score
    g._deploy_chute()
    assert g.score == old_score + 200 * 2
    assert g.dive_phase == DivePhase.CHUTE


# --- Ring Spawning ---
def test_ring_spawn() -> None:
    g = _make_game()
    g.ring_spawn_timer = g.ring_spawn_interval
    g._spawn_ring()
    assert len(g.rings) == 1
    assert g.rings[0].y == -16
    assert g.rings[0].color in RING_COLORS


def test_ring_scrolls_down() -> None:
    g = _make_game()
    g.fall_speed = 3.0
    ring = Ring(x=100, y=50, color=RING_COLORS[0])
    g.rings = [ring]
    g._update_rings()
    assert ring.y == 53.0


def test_ring_removed_offscreen() -> None:
    g = _make_game()
    g.rings = [Ring(x=100, y=300, color=RING_COLORS[0])]
    g._update_rings()
    assert len(g.rings) == 0


def test_max_rings_limit() -> None:
    g = _make_game()
    g.rings = [Ring(x=float(50 + i * 30), y=50.0, color=RING_COLORS[0]) for i in range(MAX_RINGS)]
    g.ring_spawn_timer = g.ring_spawn_interval
    g._update_rings()
    assert len(g.rings) == MAX_RINGS


# --- Player ---
def test_player_clamped_to_edges() -> None:
    g = _make_game()
    g.player_x = -10
    g._move_player(0)  # triggers clamp
    assert g.player_x == 16.0
    g.player_x = SCREEN_W + 10
    g._move_player(0)  # triggers clamp
    assert g.player_x == SCREEN_W - 16


def test_player_move_left() -> None:
    g = _make_game()
    g.player_x = 200.0
    g._move_player(-PLAYER_SPEED)
    assert g.player_x == 200.0 - PLAYER_SPEED


def test_player_move_right() -> None:
    g = _make_game()
    g.player_x = 100.0
    g._move_player(PLAYER_SPEED)
    assert g.player_x == 100.0 + PLAYER_SPEED


def test_player_color_cycles() -> None:
    g = _make_game()
    g.player_color_idx = 0
    g.player_color_timer = g.player_color_interval - 1
    g._update_player_color()
    assert g.player_color_idx == 1


# --- Dive Cycle ---
def test_dive_auto_chute() -> None:
    g = _make_game()
    g.dive_timer = 1
    g._update_dive_timers()
    assert g.dive_phase == DivePhase.CHUTE


def test_chute_to_landed() -> None:
    g = _make_game()
    g.dive_phase = DivePhase.CHUTE
    g.chute_timer = 1
    g._update_dive_timers()
    assert g.dive_phase == DivePhase.LANDED


def test_landed_starts_new_dive() -> None:
    g = _make_game()
    g.dive_phase = DivePhase.LANDED
    g.landed_timer = 1
    g.dive_count = 2
    g._update_dive_timers()
    assert g.dive_phase == DivePhase.FALLING
    assert g.dive_count == 3


# --- Escalation ---
def test_fall_speed_increases() -> None:
    g = _make_game()
    g.game_timer = GAME_DURATION
    g._update_escalation()
    assert g.fall_speed == 2.0
    g.game_timer = 0
    g._update_escalation()
    assert g.fall_speed == 6.0


def test_ring_interval_decreases() -> None:
    g = _make_game()
    g.game_timer = GAME_DURATION
    g._update_escalation()
    assert g.ring_spawn_interval == 40
    g.game_timer = 0
    g._update_escalation()
    assert g.ring_spawn_interval == 20


def test_color_interval_decreases() -> None:
    g = _make_game()
    g.game_timer = GAME_DURATION
    g._update_escalation()
    assert g.player_color_interval == 30
    g.game_timer = 0
    g._update_escalation()
    assert g.player_color_interval == 15


# --- Reset / State ---
def test_reset_initializes_state() -> None:
    g = _make_game()
    g.score = 500
    g.combo = 10
    g.heat = 80
    g.dive_count = 3
    g._init_game_state()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0
    assert g.dive_count == 0


def test_game_over_preserves_best_score() -> None:
    g = _make_game()
    g.score = 500
    g.best_score = 300
    g._game_over()
    assert g.best_score == 500


# --- Edge Cases ---
def test_multiple_rings_same_frame() -> None:
    g = _make_game()
    g.player_color_idx = 0
    ring1 = Ring(x=g.player_x, y=g.player_y, color=RING_COLORS[0])
    ring2 = Ring(x=g.player_x, y=g.player_y, color=RING_COLORS[0])
    g.rings = [ring1, ring2]
    g._update_collisions()
    assert ring1.passed
    assert ring2.passed
    assert g.combo == 2


def test_super_dive_exactly_at_4() -> None:
    g = _make_game()
    g.combo = COMBO_THRESHOLD
    g._update_super_dive()
    assert g.super_dive


def test_heat_exactly_100() -> None:
    g = _make_game()
    g.heat = HEAT_MAX
    assert g.phase == Phase.PLAYING
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_player_at_screen_edge_still_collides() -> None:
    g = _make_game()
    g.player_x = 16.0
    g.player_color_idx = 0
    ring = Ring(x=g.player_x, y=g.player_y, color=RING_COLORS[0])
    g.rings = [ring]
    g._update_collisions()
    assert ring.passed


def test_collision_not_triggered_when_chute_deployed() -> None:
    g = _make_game()
    g.dive_phase = DivePhase.CHUTE
    g.player_color_idx = 0
    ring = Ring(x=g.player_x, y=g.player_y, color=RING_COLORS[0])
    g.rings = [ring]
    g._update_collisions()
    assert not ring.passed
