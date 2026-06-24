"""test_imports.py — Headless logic tests for CHUTE CHAIN."""
from __future__ import annotations

import random
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/158_chute_chain")
from main import (
    SCREEN_W,
    SCREEN_H,
    FALL_SPEED_FREEFALL,
    FALL_SPEED_CHUTE,
    VX_MAX_FREEFALL,
    VX_MAX_CHUTE,
    HEAT_WRONG,
    HEAT_MISS,
    HEAT_DECAY,
    SUPER_DURATION,
    SUPER_MULTIPLIER,
    TIMER_MAX,
    ALTITUDE_START,
    LANDING_SCORE,
    COLOR_NAMES,
    COLOR_VALS,
    Phase,
    Ring,
    Particle,
    FloatingText,
    WindLine,
    Game,
)


# ── Sound mock for headless tests ─────────────────────────

def _mock_sound_methods(g: Game) -> None:
    """Replace pyxel.play() calls with no-ops for headless testing."""
    object.__setattr__(g, "_play_sound_collect", lambda: None)
    object.__setattr__(g, "_play_sound_combo", lambda: None)
    object.__setattr__(g, "_play_sound_super", lambda: None)


# ── Factory ────────────────────────────────────────────────

def _make_game(seed: int = 42) -> Game:
    """Create a Game instance for headless testing (no Pyxel init)."""
    g = Game.__new__(Game)
    # Pre-init ALL attributes that _start_game() or methods will touch
    g.rings = []
    g.particles = []
    g.floating_texts = []
    g.wind_lines = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.super_timer = 0
    g.timer = TIMER_MAX
    g.altitude = ALTITUDE_START
    g.bg_offset = 0.0
    g.player_x = 160.0
    g.player_y = 30.0
    g.player_vx = 0.0
    g.player_vy = FALL_SPEED_FREEFALL
    g.parachute_deployed = False
    g.landing_x = 160.0
    g.shake_frames = 0
    g.ring_timer = 0
    g.wind_dir = 0.0
    g.wind_timer = 0
    g.last_color = None
    g.heat_warning_timer = 0
    g._spawn_ring_cooldown = 60
    g.phase = Phase.PLAYING
    g.rng = random.Random(seed)
    _mock_sound_methods(g)
    return g


# ── Data Classes ───────────────────────────────────────────

def test_ring_creation() -> None:
    ring = Ring(x=100.0, y=200.0, color=0, radius=10.0, vy=1.5)
    assert ring.x == 100.0
    assert ring.y == 200.0
    assert ring.color == 0
    assert ring.radius == 10.0
    assert ring.vy == 1.5
    assert ring.collected is False


def test_particle_defaults() -> None:
    p = Particle(x=50.0, y=60.0, vx=1.0, vy=-2.0, life=20, color=8)
    assert p.life == 20
    assert p.max_life == 20
    assert p.color == 8


def test_floating_text_defaults() -> None:
    ft = FloatingText(x=100.0, y=50.0, text="+100", life=25, color=7)
    assert ft.text == "+100"
    assert ft.life == 25


def test_wind_line_defaults() -> None:
    wl = WindLine(x=0.0, y=100.0, length=50.0, speed=1.0, life=30)
    assert wl.length == 50.0
    assert wl.speed == 1.0


# ── Ring Spawning ──────────────────────────────────────────

def test_spawn_ring_adds_to_rings() -> None:
    g = _make_game()
    g._spawn_ring()
    assert len(g.rings) == 1
    r = g.rings[0]
    assert 20 <= r.x <= SCREEN_W - 20
    assert SCREEN_H + 10 <= r.y <= SCREEN_H + 40
    assert 0 <= r.color <= 3
    assert 8 <= r.radius <= 12
    assert 1.0 <= r.vy <= 2.0


def test_spawn_multiple_rings() -> None:
    g = _make_game()
    for _ in range(8):
        g._spawn_ring()
    assert len(g.rings) == 8


# ── Ring Collection ────────────────────────────────────────

def test_collect_same_color_builds_combo() -> None:
    g = _make_game()
    g.last_color = 0
    ring = Ring(x=100.0, y=30.0, color=0, radius=10.0, vy=1.0)
    g.player_x = 100.0
    g.player_y = 30.0
    initial_score = g.score
    g._collect_ring(ring)
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score > initial_score
    assert ring.collected is True


def test_collect_wrong_color_resets_combo() -> None:
    g = _make_game()
    g.last_color = 0
    g.combo = 3
    g.max_combo = 3
    ring = Ring(x=100.0, y=30.0, color=1, radius=10.0, vy=1.0)
    g.player_x = 100.0
    g.player_y = 30.0
    g._collect_ring(ring)
    assert g.combo == 0
    assert g.max_combo == 3  # max_combo preserved
    assert g.heat == HEAT_WRONG  # heat added
    assert ring.collected is True


def test_collect_wrong_color_adds_heat() -> None:
    g = _make_game()
    g.last_color = 0
    ring = Ring(x=100.0, y=30.0, color=1, radius=10.0, vy=1.0)
    g.player_x = 100.0
    g.player_y = 30.0
    g._collect_ring(ring)
    assert g.heat == HEAT_WRONG


def test_collect_same_color_score_scales_with_combo() -> None:
    g = _make_game()
    g.last_color = 0
    # Combo 0 → hit same color → combo 1, score = 100 * (1 + 1) = 200
    ring = Ring(x=100.0, y=30.0, color=0, radius=10.0, vy=1.0)
    g.player_x = 100.0
    g.player_y = 30.0
    g._collect_ring(ring)
    assert g.combo == 1
    score1 = g.score
    assert score1 == 200

    # Combo 1 → hit same color → combo 2, score += 100 * (1 + 2) = 300
    ring2 = Ring(x=100.0, y=30.0, color=0, radius=10.0, vy=1.0)
    g._collect_ring(ring2)
    assert g.combo == 2
    assert g.score == score1 + 300


def test_collect_first_ring_with_no_last_color() -> None:
    g = _make_game()
    # last_color is None → any color builds combo
    ring = Ring(x=100.0, y=30.0, color=2, radius=10.0, vy=1.0)
    g.player_x = 100.0
    g.player_y = 30.0
    g._collect_ring(ring)
    assert g.combo == 1
    assert g.heat == 0.0  # no heat for first ring
    assert g.last_color == 2


def test_collect_creates_particles() -> None:
    g = _make_game()
    g.last_color = 0
    ring = Ring(x=100.0, y=30.0, color=0, radius=10.0, vy=1.0)
    g.player_x = 100.0
    g.player_y = 30.0
    assert len(g.particles) == 0
    g._collect_ring(ring)
    assert len(g.particles) >= 10  # at least 10 particles


def test_collect_creates_floating_text() -> None:
    g = _make_game()
    g.last_color = 0
    ring = Ring(x=100.0, y=30.0, color=0, radius=10.0, vy=1.0)
    g.player_x = 100.0
    g.player_y = 30.0
    assert len(g.floating_texts) == 0
    g._collect_ring(ring)
    assert len(g.floating_texts) >= 1


# ── SUPER Mode ─────────────────────────────────────────────

def test_combo_4_triggers_super_chute() -> None:
    g = _make_game()
    g.last_color = 0
    g.combo = 3
    ring = Ring(x=100.0, y=30.0, color=0, radius=10.0, vy=1.0)
    g.player_x = 100.0
    g.player_y = 30.0
    g._collect_ring(ring)
    assert g.combo == 4
    assert g.super_timer == SUPER_DURATION  # 300


def test_super_mode_all_colors_match() -> None:
    g = _make_game()
    g.super_timer = 100
    g.last_color = 0
    g.combo = 4
    # Different color should still build combo in super mode
    ring = Ring(x=100.0, y=30.0, color=1, radius=10.0, vy=1.0)
    g.player_x = 100.0
    g.player_y = 30.0
    g._collect_ring(ring)
    assert g.combo == 5  # still built combo
    assert g.heat == 0.0  # no heat added


def test_super_mode_score_multiplier() -> None:
    g = _make_game()
    g.super_timer = 100
    g.last_color = 0
    g.combo = 4
    ring = Ring(x=100.0, y=30.0, color=0, radius=10.0, vy=1.0)
    g.player_x = 100.0
    g.player_y = 30.0
    initial_score = g.score
    g._collect_ring(ring)
    # score = base_score * SUPER_MULTIPLIER * (1 + combo)
    # = 100 * 3 * (1 + 5) = 1800
    assert g.score == initial_score + 100 * SUPER_MULTIPLIER * (1 + 5)


def test_super_mode_does_not_retrigger_super() -> None:
    g = _make_game()
    g.super_timer = 100  # already in super
    g.last_color = 0
    g.combo = 3
    ring = Ring(x=100.0, y=30.0, color=0, radius=10.0, vy=1.0)
    g.player_x = 100.0
    g.player_y = 30.0
    g._collect_ring(ring)
    assert g.combo == 4
    assert g.super_timer == 100  # NOT reset, stays at whatever it was


def test_super_mode_more_particles() -> None:
    g = _make_game()
    g.super_timer = 100
    g.last_color = 0
    ring = Ring(x=100.0, y=30.0, color=0, radius=10.0, vy=1.0)
    g.player_x = 100.0
    g.player_y = 30.0
    g._collect_ring(ring)
    # 16 particles in super mode (vs 10 normal)
    assert len(g.particles) == 16


def test_super_mode_ring_radius_multiplied_in_collision() -> None:
    g = _make_game()
    g.super_timer = 100
    ring = Ring(x=100.0, y=50.0, color=0, radius=10.0, vy=1.0)
    g.rings.append(ring)
    g.player_x = 100.0
    g.player_y = 30.0
    # In super mode, effective radius = 10 * 2 = 20
    # distance = 20 → within PLAYER_RADIUS + effective = 6 + 20 = 26
    g._check_collisions()
    assert ring.collected is True


# ── SUPER Timer ────────────────────────────────────────────

def test_update_super_decrements_timer() -> None:
    g = _make_game()
    g.super_timer = 100
    g._update_super()
    assert g.super_timer == 99


def test_update_super_resets_combo_on_expire() -> None:
    g = _make_game()
    g.super_timer = 1
    g.combo = 5
    g.last_color = 2
    g._update_super()
    assert g.super_timer == 0
    assert g.combo == 0
    assert g.last_color is None


# ── Collision Detection ────────────────────────────────────

def test_check_collisions_detects_overlap() -> None:
    g = _make_game()
    g.last_color = 0
    ring = Ring(x=100.0, y=30.0, color=0, radius=10.0, vy=1.0)
    g.rings.append(ring)
    g.player_x = 100.0
    g.player_y = 30.0
    g._check_collisions()
    assert ring.collected is True


def test_check_collisions_ignores_far_rings() -> None:
    g = _make_game()
    ring = Ring(x=200.0, y=200.0, color=0, radius=10.0, vy=1.0)
    g.rings.append(ring)
    g.player_x = 50.0
    g.player_y = 30.0
    g._check_collisions()
    assert ring.collected is False


def test_check_collisions_ignores_already_collected() -> None:
    g = _make_game()
    g.last_color = 0
    ring = Ring(x=100.0, y=30.0, color=0, radius=10.0, vy=1.0, collected=True)
    g.rings.append(ring)
    g.player_x = 100.0
    g.player_y = 30.0
    g._check_collisions()
    assert g.combo == 0  # combo unchanged


# ── Particle System ────────────────────────────────────────

def test_update_particles_decrements_life() -> None:
    g = _make_game()
    p = Particle(x=0.0, y=0.0, vx=1.0, vy=0.0, life=5, color=8)
    g.particles.append(p)
    g._update_particles()
    assert p.life == 4


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    p = Particle(x=0.0, y=0.0, vx=1.0, vy=0.0, life=1, color=8)
    g.particles.append(p)
    g._update_particles()
    assert len(g.particles) == 0


def test_update_particles_moves_position() -> None:
    g = _make_game()
    p = Particle(x=0.0, y=0.0, vx=2.0, vy=3.0, life=10, color=8)
    g.particles.append(p)
    g._update_particles()
    assert abs(p.x - 2.0) < 0.01
    assert abs(p.y - 3.0) < 0.01
    # gravity on vy: vy += 0.05
    assert abs(p.vy - 3.05) < 0.01


# ── Floating Text ──────────────────────────────────────────

def test_update_floating_texts_decrements_life() -> None:
    g = _make_game()
    ft = FloatingText(x=100.0, y=50.0, text="+100", life=5, color=7)
    g.floating_texts.append(ft)
    g._update_floating_texts()
    assert ft.life == 4


def test_update_floating_texts_removes_dead() -> None:
    g = _make_game()
    ft = FloatingText(x=100.0, y=50.0, text="+100", life=1, color=7)
    g.floating_texts.append(ft)
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_floating_text_floats_upward() -> None:
    g = _make_game()
    ft = FloatingText(x=100.0, y=50.0, text="+100", life=5, color=7)
    g.floating_texts.append(ft)
    g._update_floating_texts()
    assert ft.y < 50.0


# ── Heat System ────────────────────────────────────────────

def test_update_heat_decays() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat < 50.0
    assert g.heat > 49.9  # ~0.008 decay


def test_update_heat_floor_at_zero() -> None:
    g = _make_game()
    g.heat = 0.001
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_warning_timer() -> None:
    g = _make_game()
    g.heat = 80.0
    g._update_heat()
    assert g.heat_warning_timer >= 1


def test_heat_warning_timer_resets_below_70() -> None:
    g = _make_game()
    g.heat = 60.0
    g.heat_warning_timer = 5
    g._update_heat()
    assert g.heat_warning_timer == 0


# ── Game Over Conditions ───────────────────────────────────

def test_game_over_sets_phase() -> None:
    g = _make_game()
    g._game_over()
    assert g.phase == Phase.GAME_OVER


def test_game_over_updates_best_score() -> None:
    Game.best_score = 0
    g = _make_game()
    g.score = 5000
    g._game_over()
    assert Game.best_score == 5000


def test_game_over_does_not_lower_best_score() -> None:
    Game.best_score = 10000
    g = _make_game()
    g.score = 5000
    g._game_over()
    assert Game.best_score == 10000


# ── Ring Update ────────────────────────────────────────────

def test_update_rings_moves_rings_upward() -> None:
    g = _make_game()
    ring = Ring(x=160.0, y=100.0, color=0, radius=10.0, vy=2.0)
    g.rings.append(ring)
    g._update_rings()
    assert ring.y < 100.0  # moved up


def test_update_rings_removes_offscreen_rings() -> None:
    g = _make_game()
    ring = Ring(x=160.0, y=-30.0, color=0, radius=10.0, vy=1.0)
    g.rings.append(ring)
    g._update_rings()
    assert len(g.rings) == 0


def test_update_rings_miss_adds_heat() -> None:
    g = _make_game()
    ring = Ring(x=160.0, y=-30.0, color=0, radius=10.0, vy=1.0)
    g.rings.append(ring)
    g._update_rings()
    assert g.heat == HEAT_MISS


# ── Player Update ──────────────────────────────────────────

def test_update_player_clamps_to_bounds() -> None:
    g = _make_game()
    g.player_x = -10.0
    g.player_y = -10.0
    g._update_player()
    assert g.player_x >= 5.0
    assert g.player_y >= 5.0


def test_update_player_clamps_right_bottom() -> None:
    g = _make_game()
    g.player_x = float(SCREEN_W + 10)
    g.player_y = float(SCREEN_H + 10)
    g._update_player()
    assert g.player_x <= SCREEN_W - 5
    assert g.player_y <= SCREEN_H - 5


def test_update_player_max_vx_freefall() -> None:
    g = _make_game()
    g.parachute_deployed = False
    g.player_vx = 10.0  # beyond max
    g._update_player()
    # drag applies: 10 * 0.9 = 9.0, then clamped to VX_MAX_FREEFALL = 2.5
    assert abs(g.player_vx) <= VX_MAX_FREEFALL + 0.01


def test_update_player_max_vx_chute() -> None:
    g = _make_game()
    g.parachute_deployed = True
    g.player_vx = 10.0
    g._update_player()
    assert abs(g.player_vx) <= VX_MAX_CHUTE + 0.01


def test_update_player_parachute_fall_speed() -> None:
    g = _make_game()
    g.parachute_deployed = True
    g.player_vy = FALL_SPEED_CHUTE
    g._update_player()
    assert g.player_y > 30.0  # fell


# ── Phase Transitions ──────────────────────────────────────

def test_start_game_resets_state() -> None:
    g = _make_game()
    g.score = 500
    g.combo = 3
    g.heat = 50.0
    g.super_timer = 100
    g._start_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.player_x == 160.0
    assert g.player_y == 30.0


# ── Parachute Toggle ───────────────────────────────────────

def test_parachute_deployed_sets_fall_speed() -> None:
    g = _make_game()
    g.parachute_deployed = False
    # Simulate what _handle_input does on SPACE press
    g.parachute_deployed = True
    g.player_vy = FALL_SPEED_CHUTE
    assert g.player_vy == FALL_SPEED_CHUTE
    assert g.player_vy < FALL_SPEED_FREEFALL


def test_parachute_undeployed_resets_fall_speed() -> None:
    g = _make_game()
    g.parachute_deployed = True
    g.player_vy = FALL_SPEED_CHUTE
    g.parachute_deployed = False
    g.player_vy = FALL_SPEED_FREEFALL
    assert g.player_vy == FALL_SPEED_FREEFALL


# ── Landing ────────────────────────────────────────────────

def test_landing_bonus_when_near_target() -> None:
    g = _make_game()
    g.parachute_deployed = True
    g.player_x = 160.0  # right on target
    g.landing_x = 160.0
    g.timer = 0  # force landing
    # Simulate landing check from update()
    if g.timer <= 0:
        if g.parachute_deployed:
            if abs(g.player_x - g.landing_x) < 40:
                g.score += LANDING_SCORE
    assert g.score == LANDING_SCORE


def test_no_landing_bonus_when_far_from_target() -> None:
    g = _make_game()
    g.parachute_deployed = True
    g.player_x = 50.0
    g.landing_x = 160.0
    g.timer = 0
    if g.timer <= 0:
        if g.parachute_deployed:
            if abs(g.player_x - g.landing_x) < 40:
                g.score += LANDING_SCORE
    assert g.score == 0


# ── Difficulty Scaling ─────────────────────────────────────

def test_update_difficulty_reduces_cooldown() -> None:
    g = _make_game()
    g.score = 4000  # = floor(4000/2000)*2 = 4
    g._update_difficulty()
    assert g._spawn_ring_cooldown == 56  # 60 - 4


def test_update_difficulty_min_cooldown() -> None:
    g = _make_game()
    g.score = 100000
    g._update_difficulty()
    assert g._spawn_ring_cooldown == 30  # min is 30


# ── Wind System ────────────────────────────────────────────

def test_update_wind_changes_direction() -> None:
    g = _make_game()
    g.wind_timer = 1
    g.wind_dir = 0.5
    g._update_wind()
    # wind_timer reached 0, new wind_dir set
    assert g.wind_timer > 0  # reset


# ── max_combo Tracking ─────────────────────────────────────

def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    g.last_color = 0
    g.combo = 0
    g.max_combo = 0
    # Build combo to 3
    for i in range(3):
        ring = Ring(x=100.0, y=30.0, color=0, radius=10.0, vy=1.0)
        g.player_x = 100.0
        g.player_y = 30.0
        g._collect_ring(ring)
    assert g.max_combo == 3


def test_max_combo_preserved_after_reset() -> None:
    g = _make_game()
    g.last_color = 0
    g.max_combo = 3
    g.combo = 3
    # Wrong color resets combo but not max_combo
    ring = Ring(x=100.0, y=30.0, color=1, radius=10.0, vy=1.0)
    g.player_x = 100.0
    g.player_y = 30.0
    g._collect_ring(ring)
    assert g.combo == 0
    assert g.max_combo == 3


# ── Phase Enum ─────────────────────────────────────────────

def test_phase_enum_values() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ── Color Constants ────────────────────────────────────────

def test_color_vals_match() -> None:
    assert len(COLOR_VALS) == 4
    assert len(COLOR_NAMES) == 4
    assert COLOR_VALS[0] == 8  # RED
    assert COLOR_VALS[1] == 3  # GREEN
    assert COLOR_VALS[2] == 5  # DARK_BLUE
    assert COLOR_VALS[3] == 10  # YELLOW


# ── HEAT Decay Value ───────────────────────────────────────

def test_heat_decay_constant() -> None:
    assert abs(HEAT_DECAY - 0.5 / 60.0) < 0.0001


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
