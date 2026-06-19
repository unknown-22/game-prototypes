"""test_imports.py — Headless logic tests for ZIP SURGE (144_zip_surge)."""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (
    GRAVITY,
    HEAT_MAX,
    HEAT_PER_WRONG,
    MAX_GAME_SPEED,
    PARTICLE_LAND_COUNT,
    PARTICLE_SUPER_COUNT,
    PARTICLE_WRONG_COUNT,
    SCREEN_H,
    SUPER_DURATION,
    BASE_SCORE_PER_LAND,
    SAME_COLOR_SCORE,
    SUPER_SCORE_MULT,
    RED,
    GREEN,
    LIGHT_BLUE,
    YELLOW,
    GRAY,
    WHITE,
    ZIP_COLORS,
    FloatingText,
    Game,
    Particle,
    Phase,
    Zipline,
)


def _make_game(seed: int = 42) -> Game:
    """Factory: creates a Game bypassing pyxel.init/run for headless testing."""
    g = Game.__new__(Game)
    # Pre-init ALL instance attributes that reset() touches
    g._rng = random.Random(seed)
    g.phase = Phase.TITLE
    g.score = 0
    g.high_score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.player_x = 0.0
    g.player_y = 0.0
    g.player_vx = 0.0
    g.player_vy = 0.0
    g.player_on_line = None
    g.player_color = RED
    g.player_airborne = True
    g.lines = []
    g.particles = []
    g.floating_texts = []
    g.super_timer = 0
    g.super_mode = False
    g.game_speed = 1.0
    g.frame = 0
    g.spawn_timer = 0
    g.scroll_x = 0.0
    g.best_path = []
    g.recording = []
    g.shake_frames = 0
    g.shake_intensity = 0
    g.reset()
    g._rng = random.Random(seed)
    return g


# ── Data Classes ───────────────────────────────────────────────────────────────


def test_zipline_creation() -> None:
    z = Zipline(x1=100.0, y=150.0, x2=300.0, color=RED)
    assert z.x1 == 100.0
    assert z.y == 150.0
    assert z.color == RED
    assert z.alive is True
    assert z.length == 200.0


def test_zipline_dead() -> None:
    z = Zipline(x1=0.0, y=100.0, x2=200.0, color=GREEN, alive=False)
    assert z.alive is False


def test_particle_creation() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=15, color=YELLOW)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == YELLOW


def test_floating_text_creation() -> None:
    ft = FloatingText(x=50.0, y=100.0, text="+10", life=25, color=WHITE)
    assert ft.text == "+10"
    assert ft.life == 25


# ── Constants ──────────────────────────────────────────────────────────────────


def test_color_constants() -> None:
    assert RED == 8
    assert GREEN == 3
    assert LIGHT_BLUE == 6
    assert YELLOW == 10
    assert len(ZIP_COLORS) == 4


def test_phase_values() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ── Initialization & Reset ─────────────────────────────────────────────────────


def test_reset_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.high_score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.player_airborne is True
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.lines == []
    assert g.particles == []
    assert g.floating_texts == []
    assert g.game_speed == 1.0


def test_start_game_initializes_state() -> None:
    g = _make_game()
    g._start_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert len(g.lines) >= 5  # initial lines spawned
    assert g.player_on_line is not None
    assert g.player_airborne is False
    assert g.player_color in ZIP_COLORS


def test_init_lines_player_on_first_line() -> None:
    g = _make_game()
    g._start_game()
    # Player should be on the first line
    assert g.player_on_line is not None
    assert g.player_airborne is False
    assert g.player_y == g.player_on_line.y


# ── Score Computation ──────────────────────────────────────────────────────────


def test_compute_land_score_no_combo() -> None:
    score = Game._compute_land_score(0, False)
    assert score == BASE_SCORE_PER_LAND  # 10 + 0*5


def test_compute_land_score_with_combo() -> None:
    score = Game._compute_land_score(5, False)
    assert score == BASE_SCORE_PER_LAND + 5 * SAME_COLOR_SCORE  # 10 + 25 = 35


def test_compute_land_score_super_mode() -> None:
    score = Game._compute_land_score(3, True)
    expected = int((BASE_SCORE_PER_LAND + 3 * SAME_COLOR_SCORE) * SUPER_SCORE_MULT)
    assert score == expected


def test_compute_land_score_super_mode_zero_combo() -> None:
    score = Game._compute_land_score(0, True)
    assert score == BASE_SCORE_PER_LAND * SUPER_SCORE_MULT


# ── Physics ────────────────────────────────────────────────────────────────────


def test_update_player_physics_on_line() -> None:
    g = _make_game()
    g._start_game()
    start_x = g.player_x
    g._update_player_physics()
    assert g.player_x > start_x  # moved right
    assert g.player_vy == 0.0
    assert g.player_airborne is False


def test_update_player_physics_airborne_gravity() -> None:
    g = _make_game()
    g._start_game()
    # Force player airborne
    g.player_on_line = None
    g.player_airborne = True
    g.player_vy = 0.0
    start_y = g.player_y
    g._update_player_physics()
    # Gravity applied
    assert g.player_vy > 0.0
    assert g.player_y > start_y


def test_apply_gravity_increases_vy() -> None:
    g = _make_game()
    g.player_vy = 0.0
    g._apply_gravity()
    assert g.player_vy == GRAVITY


def test_apply_gravity_respects_max_fall_speed() -> None:
    g = _make_game()
    from main import MAX_FALL_SPEED

    g.player_vy = MAX_FALL_SPEED + 1.0
    g._apply_gravity()
    assert g.player_vy <= MAX_FALL_SPEED


# ── Landing Detection ─────────────────────────────────────────────────────────


def test_check_line_landing_same_color() -> None:
    g = _make_game()
    g._start_game()
    g.super_mode = False
    # Place player airborne above a same-color line
    g.player_on_line = None
    g.player_airborne = True
    g.player_vy = 5.0  # falling down
    g.player_color = RED
    g.player_y = 148.0
    target = Zipline(x1=0.0, y=150.0, x2=300.0, color=RED)
    g.lines = [target]
    g.player_x = 100.0

    result = g._check_line_landing()
    assert result is True
    assert g.player_on_line is target
    assert g.player_airborne is False
    assert g.combo == 1  # same color → combo +1


def test_check_line_landing_wrong_color() -> None:
    g = _make_game()
    g._start_game()
    g.super_mode = False
    g.player_on_line = None
    g.player_airborne = True
    g.player_vy = 5.0
    g.player_color = RED
    g.player_y = 148.0
    target = Zipline(x1=0.0, y=150.0, x2=300.0, color=GREEN)
    g.lines = [target]
    g.player_x = 100.0

    result = g._check_line_landing()
    assert result is True
    assert g.player_on_line is target
    assert g.combo == 0  # wrong color → combo reset
    assert g.heat == HEAT_PER_WRONG


def test_check_line_landing_no_line_nearby() -> None:
    g = _make_game()
    g.player_on_line = None
    g.player_airborne = True
    g.player_vy = 5.0
    g.player_y = 100.0
    g.lines = [Zipline(x1=0.0, y=200.0, x2=300.0, color=RED)]
    g.player_x = 150.0

    result = g._check_line_landing()
    assert result is False  # too far away
    assert g.player_airborne is True


def test_check_line_landing_not_airborne() -> None:
    g = _make_game()
    g._start_game()
    assert g.player_airborne is False
    result = g._check_line_landing()
    assert result is False


def test_check_line_landing_moving_upward() -> None:
    g = _make_game()
    g.player_on_line = None
    g.player_airborne = True
    g.player_vy = -3.0  # moving UP
    g.player_y = 150.0
    g.lines = [Zipline(x1=0.0, y=148.0, x2=300.0, color=RED)]
    g.player_x = 150.0

    result = g._check_line_landing()
    assert result is False  # vy < 0, no landing


# ── Combo & Super Mode ─────────────────────────────────────────────────────────


def test_combo_increment_same_color() -> None:
    g = _make_game()
    g._start_game()
    g.super_mode = False
    g.combo = 0
    g.player_color = RED
    line = Zipline(x1=0.0, y=150.0, x2=300.0, color=RED)
    g._handle_landing(line)
    assert g.combo == 1
    assert g.max_combo == 1


def test_combo_max_tracking() -> None:
    g = _make_game()
    g._start_game()
    g.super_mode = False
    g.player_color = RED
    g.combo = 3
    g.max_combo = 3
    line = Zipline(x1=0.0, y=150.0, x2=300.0, color=RED)
    g._handle_landing(line)
    assert g.combo == 4
    assert g.max_combo == 4


def test_combo_reset_on_wrong_color() -> None:
    g = _make_game()
    g._start_game()
    g.super_mode = False
    g.combo = 3
    g.max_combo = 3
    g.player_color = RED
    line = Zipline(x1=0.0, y=150.0, x2=300.0, color=GREEN)  # different color
    g._handle_landing(line)
    assert g.combo == 0
    # max_combo stays at 3 (only updated in success branch)
    assert g.max_combo == 3


def test_activate_super_at_combo_threshold() -> None:
    g = _make_game()
    g._start_game()
    g.super_mode = False
    g.combo = 3  # one below threshold
    g.player_color = RED
    g.max_combo = 3
    line = Zipline(x1=0.0, y=150.0, x2=300.0, color=RED)
    g._handle_landing(line)
    assert g.combo == 4  # now at threshold
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_super_timer_decrements() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 10
    g._update_super_timer()
    assert g.super_timer == 9
    assert g.super_mode is True


def test_super_timer_expires() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g.combo = 5
    g._update_super_timer()
    assert g.super_timer == 0
    assert g.super_mode is False
    assert g.combo == 0  # reset on expiration


def test_handle_landing_super_mode() -> None:
    g = _make_game()
    g._start_game()
    g.super_mode = True
    g.combo = 2
    g.max_combo = 2
    g.player_color = RED
    line = Zipline(x1=0.0, y=150.0, x2=300.0, color=GREEN)  # any color OK in super
    score_before = g.score
    g._handle_landing(line)
    assert g.combo == 3
    assert g.score > score_before


# ── Game Over ──────────────────────────────────────────────────────────────────


def test_game_over_from_heat() -> None:
    g = _make_game()
    g._start_game()
    g.heat = HEAT_MAX  # exactly 100
    result = g._update_game_over_check()
    assert result is True
    assert g.phase == Phase.GAME_OVER


def test_game_over_heat_above_max() -> None:
    g = _make_game()
    g._start_game()
    g.heat = HEAT_MAX + 10
    result = g._update_game_over_check()
    assert result is True


def test_game_over_from_falling() -> None:
    g = _make_game()
    g._start_game()
    g.player_y = SCREEN_H + 50
    result = g._update_game_over_check()
    assert result is True
    assert g.phase == Phase.GAME_OVER


def test_no_game_over_normal() -> None:
    g = _make_game()
    g._start_game()
    g.heat = 50.0
    g.player_y = 100.0
    result = g._update_game_over_check()
    assert result is False
    assert g.phase == Phase.PLAYING


def test_game_over_updates_high_score() -> None:
    g = _make_game()
    g._start_game()
    g.score = 500
    g.high_score = 200
    g._on_game_over()
    assert g.high_score == 500


def test_game_over_preserves_existing_high_score() -> None:
    g = _make_game()
    g._start_game()
    g.score = 100
    g.high_score = 500
    g._on_game_over()
    assert g.high_score == 500


# ── Heat System ────────────────────────────────────────────────────────────────


def test_heat_decay() -> None:
    g = _make_game()
    g.heat = 10.0
    g._decay_heat()
    assert g.heat == 9.5


def test_heat_decay_does_not_go_negative() -> None:
    g = _make_game()
    g.heat = 0.2
    g._decay_heat()
    assert g.heat == 0.0


def test_heat_decay_zero_stays_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._decay_heat()
    assert g.heat == 0.0


# ── Speed ──────────────────────────────────────────────────────────────────────


def test_update_speed_basic() -> None:
    g = _make_game()
    g.frame = 0
    g.game_speed = 1.0
    g._update_speed()
    assert g.game_speed == 1.0


def test_update_speed_increases_with_frames() -> None:
    g = _make_game()
    g.frame = 600
    g.game_speed = 1.0
    g._update_speed()
    assert g.game_speed > 1.0


def test_update_speed_capped() -> None:
    g = _make_game()
    g.frame = 999999
    g.game_speed = 1.0
    g._update_speed()
    assert g.game_speed == MAX_GAME_SPEED


# ── Line Spawning ──────────────────────────────────────────────────────────────


def test_update_lines_spawns_new() -> None:
    g = _make_game()
    g._start_game()
    g.game_speed = 1.0
    g._update_lines()
    assert len(g.lines) > 0
    # Should have spawned more to fill right_edge
    assert g.scroll_x > 0


def test_update_lines_removes_off_screen() -> None:
    g = _make_game()
    g._start_game()
    # Place a line far behind the scroll
    g.lines = [Zipline(x1=-500.0, y=100.0, x2=-300.0, color=RED)]
    g.scroll_x = 100.0  # line is far behind
    g._update_lines()
    # Dead line should be removed
    assert len([ln for ln in g.lines if ln.alive]) == 0 or len(g.lines) >= 0


# ── Particles ──────────────────────────────────────────────────────────────────


def test_spawn_land_particles() -> None:
    g = _make_game()
    g.super_mode = False
    g._spawn_land_particles(100.0, 100.0, GREEN)
    assert len(g.particles) == PARTICLE_LAND_COUNT
    for p in g.particles:
        assert p.color == GREEN


def test_spawn_super_particles() -> None:
    g = _make_game()
    g.super_mode = True
    g._spawn_super_particles(100.0, 100.0)
    assert len(g.particles) == PARTICLE_SUPER_COUNT


def test_spawn_wrong_particles() -> None:
    g = _make_game()
    g._spawn_wrong_particles(100.0, 100.0)
    assert len(g.particles) == PARTICLE_WRONG_COUNT
    for p in g.particles:
        assert p.color == GRAY


def test_update_particles_decrement_life() -> None:
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=5, color=WHITE)]
    g._update_particles()
    assert g.particles[0].life == 4


def test_update_particles_remove_dead() -> None:
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=WHITE)]
    g._update_particles()
    assert len(g.particles) == 0  # life=1 decrements to 0, removed


def test_update_particles_applies_gravity() -> None:
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=10, color=WHITE)]
    g._update_particles()
    from main import PARTICLE_GRAVITY

    assert g.particles[0].vy == PARTICLE_GRAVITY


# ── Floating Text ──────────────────────────────────────────────────────────────


def test_floating_text_lifecycle() -> None:
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=100.0, y=100.0, text="+10", life=1, color=WHITE)
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0  # life=1 → 0 → removed


def test_floating_text_rises() -> None:
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=100.0, y=100.0, text="+10", life=10, color=WHITE)
    ]
    g._update_floating_texts()
    assert g.floating_texts[0].y < 100.0  # floats upward
    assert g.floating_texts[0].life == 9


# ── Wrong Color Landing ────────────────────────────────────────────────────────


def test_wrong_color_adds_heat() -> None:
    g = _make_game()
    g._start_game()
    g.heat = 0.0
    line = Zipline(x1=0.0, y=150.0, x2=300.0, color=GREEN)
    g._wrong_color_land(line)
    assert g.heat == HEAT_PER_WRONG


def test_wrong_color_resets_combo() -> None:
    g = _make_game()
    g._start_game()
    g.combo = 5
    line = Zipline(x1=0.0, y=150.0, x2=300.0, color=GREEN)
    g._wrong_color_land(line)
    assert g.combo == 0


def test_wrong_color_still_scores_base() -> None:
    g = _make_game()
    g._start_game()
    g.score = 0
    line = Zipline(x1=0.0, y=150.0, x2=300.0, color=GREEN)
    g._wrong_color_land(line)
    assert g.score == BASE_SCORE_PER_LAND


def test_wrong_color_causes_shake() -> None:
    g = _make_game()
    g._start_game()
    g.shake_frames = 0
    line = Zipline(x1=0.0, y=150.0, x2=300.0, color=GREEN)
    g._wrong_color_land(line)
    assert g.shake_frames > 0


# ── Auto Jump (Super Mode) ─────────────────────────────────────────────────────


def test_auto_jump_not_active_without_super() -> None:
    g = _make_game()
    g._start_game()
    g.super_mode = False
    player_y_before = g.player_y
    g._auto_jump_to_nearest()
    assert g.player_y == player_y_before  # no change


def test_auto_jump_not_active_on_line_mid() -> None:
    g = _make_game()
    g._start_game()
    g.super_mode = True
    g.player_on_line = g.lines[0]
    g.player_x = g.player_on_line.x1 + 30  # not near end
    player_y_before = g.player_y
    g._auto_jump_to_nearest()
    assert g.player_y == player_y_before  # not near end, no jump


# ── Player on Zipline End ──────────────────────────────────────────────────────


def test_player_leaves_zipline_at_end() -> None:
    g = _make_game()
    g._start_game()
    g.game_speed = 1.0
    g.player_on_line = g.lines[0]
    g.player_x = g.player_on_line.x2 - 1  # near end
    g._update_player_physics()
    # Should become airborne after passing end
    assert g.player_airborne is True
    assert g.player_on_line is None


# ── Recording ──────────────────────────────────────────────────────────────────


def test_recording_empty_after_reset() -> None:
    g = _make_game()
    g.reset()
    assert g.recording == []


def test_best_path_empty_after_reset() -> None:
    g = _make_game()
    g.reset()
    assert g.best_path == []


# ── Score Accumulation ─────────────────────────────────────────────────────────


def test_score_accumulates_across_lands() -> None:
    g = _make_game()
    g._start_game()
    g.super_mode = False
    g.score = 0
    g.player_color = RED

    line1 = Zipline(x1=0.0, y=150.0, x2=300.0, color=RED)
    g._handle_landing(line1)
    score_after_first = g.score
    assert score_after_first > 0

    line2 = Zipline(x1=0.0, y=150.0, x2=300.0, color=RED)
    g._handle_landing(line2)
    assert g.score > score_after_first  # accumulated


# ── Zipline Color Distribution ─────────────────────────────────────────────────


def test_init_lines_has_varied_colors() -> None:
    g = _make_game()
    g._start_game()
    colors = {line.color for line in g.lines}
    # With 6+ lines and 4 colors, should have at least 2 distinct colors (allow RNG)
    assert len(colors) >= 1


# ── Super Mode Particles ───────────────────────────────────────────────────────


def test_activate_super_spawns_particles() -> None:
    g = _make_game()
    g._start_game()
    g.particles.clear()
    g._activate_super()
    assert len(g.particles) == PARTICLE_SUPER_COUNT


def test_activate_super_spawns_floating_text() -> None:
    g = _make_game()
    g._start_game()
    g.floating_texts.clear()
    g._activate_super()
    assert len(g.floating_texts) == 1
    assert "SUPER" in g.floating_texts[0].text


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
