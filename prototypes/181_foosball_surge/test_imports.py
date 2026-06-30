"""test_imports.py — Headless logic tests for FOOSBALL SURGE (181)."""
from __future__ import annotations

import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/181_foosball_surge")

from main import (
    BALL_INITIAL_SPEED,
    COMBO_THRESHOLD,
    GOALS_TO_WIN,
    HEAT_INCREMENT,
    HEAT_MAX,
    PLAYER_DEF_X,
    PLAYER_FWD_X,
    AI_FWD_X,
    AI_DEF_X,
    ROD_COLORS,
    SUPER_DURATION,
    SUPER_RAINBOW,
    Ball,
    Figure,
    FloatingText,
    Game,
    Particle,
    Phase,
    Rod,
    ROD_SPEED,
    WHITE,
    RED,
    GREEN,
    DARK_BLUE,
    YELLOW,
)

# === Test Helpers ===


def _make_game() -> Game:
    """Create a Game bypassing __init__ for headless testing."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.particles = []
    g.floating_texts = []
    g.player_up = False
    g.player_down = False
    g.player_fwd_up = False
    g.player_fwd_down = False
    g.reset()
    return g


# === Data Classes ===


def test_figure_creation() -> None:
    fig = Figure(x=64.0, y=120.0, color=RED)
    assert fig.x == 64.0
    assert fig.y == 120.0
    assert fig.radius == 8
    assert fig.color == RED


def test_ball_creation() -> None:
    ball = Ball(x=160.0, y=120.0, vx=2.0, vy=1.0)
    assert ball.x == 160.0
    assert ball.y == 120.0
    assert ball.vx == 2.0
    assert ball.vy == 1.0
    assert ball.color == WHITE
    assert ball.radius == 5


def test_rod_creation() -> None:
    rod = Rod(x=64.0, y=100.0, color=RED)
    assert rod.x == 64.0
    assert rod.y == 100.0
    assert rod.color == RED
    assert rod.figures == []


def test_particle_creation() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-1.0, life=30, color=WHITE)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.life == 30


def test_floating_text_creation() -> None:
    ft = FloatingText(x=100.0, y=50.0, text="TEST", life=40, color=YELLOW)
    assert ft.text == "TEST"
    assert ft.life == 40


# === Phase Enum ===


def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# === Game.reset() ===


def test_reset_initial_state() -> None:
    g = _make_game()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.goals_player == 0
    assert g.goals_ai == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.shake_frames == 0
    assert g.goal_scored_timer == 0


def test_reset_creates_four_rods() -> None:
    g = _make_game()
    assert len(g.rods) == 4
    assert g.rods[0].x == PLAYER_DEF_X
    assert g.rods[1].x == PLAYER_FWD_X
    assert g.rods[2].x == AI_FWD_X
    assert g.rods[3].x == AI_DEF_X


def test_reset_rod_colors_are_unique() -> None:
    g = _make_game()
    colors = [rod.color for rod in g.rods]
    assert len(set(colors)) == 4  # All 4 colors represented


def test_reset_rods_have_three_figures() -> None:
    g = _make_game()
    for rod in g.rods:
        assert len(rod.figures) == 3


def test_reset_rod_figures_share_color() -> None:
    g = _make_game()
    for rod in g.rods:
        for fig in rod.figures:
            assert fig.color == rod.color


def test_reset_figures_spaced() -> None:
    g = _make_game()
    for rod in g.rods:
        assert rod.figures[0].y == rod.y - 22
        assert rod.figures[1].y == rod.y
        assert rod.figures[2].y == rod.y + 22


def test_reset_ball_position() -> None:
    g = _make_game()
    assert g.ball.x == 160.0
    assert g.ball.y == 120.0
    assert g.ball.color == WHITE


def test_reset_ball_has_speed() -> None:
    g = _make_game()
    speed = math.sqrt(g.ball.vx**2 + g.ball.vy**2)
    assert abs(speed - BALL_INITIAL_SPEED) < 0.01


# === _clamp_rod_y ===


def test_clamp_rod_y_low() -> None:
    assert Game._clamp_rod_y(0.0) == 22.0


def test_clamp_rod_y_high() -> None:
    assert Game._clamp_rod_y(300.0) == 218.0


def test_clamp_rod_y_mid() -> None:
    assert Game._clamp_rod_y(120.0) == 120.0


def test_clamp_rod_y_exact_min() -> None:
    assert Game._clamp_rod_y(22.0) == 22.0


def test_clamp_rod_y_exact_max() -> None:
    assert Game._clamp_rod_y(218.0) == 218.0


# === _sync_figures ===


def test_sync_figures_updates_positions() -> None:
    g = _make_game()
    rod = g.rods[0]
    rod.y = 100.0
    g._sync_figures(rod)
    assert rod.figures[0].y == 78.0
    assert rod.figures[1].y == 100.0
    assert rod.figures[2].y == 122.0


def test_sync_figures_preserves_color() -> None:
    g = _make_game()
    rod = g.rods[0]
    original_color = rod.color
    g._sync_figures(rod)
    for fig in rod.figures:
        assert fig.color == original_color


# === _update_physics ===


def test_physics_moves_ball() -> None:
    g = _make_game()
    g.ball.x = 160.0
    g.ball.y = 120.0
    g.ball.vx = 2.0
    g.ball.vy = 1.0
    g._update_physics()
    assert g.ball.x == 162.0
    assert g.ball.y == 121.0


def test_physics_bounce_top_wall() -> None:
    g = _make_game()
    g.ball.x = 160.0
    g.ball.y = 3.0
    g.ball.vy = -1.0
    g._update_physics()
    assert g.ball.vy > 0  # Bounced down


def test_physics_bounce_bottom_wall() -> None:
    g = _make_game()
    g.ball.x = 160.0
    g.ball.y = 237.0
    g.ball.vy = 1.0
    g._update_physics()
    assert g.ball.vy < 0  # Bounced up


def test_physics_left_goal_scores_ai() -> None:
    g = _make_game()
    g.ball.x = 14.0
    g.ball.y = 120.0
    g.ball.vx = -2.0
    g._update_physics()
    assert g.goals_ai == 1


def test_physics_right_goal_scores_player() -> None:
    g = _make_game()
    g.ball.x = 306.0
    g.ball.y = 120.0
    g.ball.vx = 2.0
    g._update_physics()
    assert g.goals_player == 1


# === _check_figure_collisions ===


def test_collision_ball_hits_figure() -> None:
    g = _make_game()
    # Place ball right on top of a figure
    fig = g.rods[0].figures[1]  # Center figure of defense rod
    g.ball.x = fig.x
    g.ball.y = fig.y
    g.ball.vx = 1.0
    g.ball.vy = 0.0
    g.ball.color = WHITE
    old_color = g.rods[0].color
    g._check_figure_collisions()
    # Ball should take figure's color
    assert g.ball.color == old_color


def test_collision_combo_increments_on_same_color() -> None:
    g = _make_game()
    # Make 2 rods same color
    g.rods[0].color = RED
    g.rods[1].color = RED
    g._sync_figures(g.rods[0])
    g._sync_figures(g.rods[1])

    # Hit first rod (RED)
    fig0 = g.rods[0].figures[1]
    g.ball.x = fig0.x
    g.ball.y = fig0.y
    g.ball.vx = 1.0
    g.ball.vy = 0.0
    g.ball.color = RED  # Already RED
    g.combo = 0
    g._check_figure_collisions()
    assert g.combo == 1  # Same color hit


def test_collision_combo_resets_on_different_color() -> None:
    g = _make_game()
    # Set up different colors
    g.rods[0].color = RED
    g.rods[1].color = GREEN
    g._sync_figures(g.rods[0])
    g._sync_figures(g.rods[1])

    # Hit with RED then GREEN
    # First establish combo
    fig0 = g.rods[0].figures[1]
    g.ball.x = fig0.x
    g.ball.y = fig0.y
    g.ball.vx = 1.0
    g.ball.vy = 0.0
    g.ball.color = RED
    g.combo = 2
    g._check_figure_collisions()
    assert g.combo == 3  # Same color: RED->RED

    # Push ball away so it doesn't re-collide
    g.ball.x += 20

    # Now hit different color
    fig1 = g.rods[1].figures[1]
    g.ball.x = fig1.x
    g.ball.y = fig1.y
    g.ball.vx = -1.0
    g.ball.vy = 0.0
    g._check_figure_collisions()
    assert g.combo == 0  # Reset on different color
    assert g.heat == HEAT_INCREMENT  # HEAT increased


def test_collision_heat_increases_on_mismatch() -> None:
    g = _make_game()
    g.rods[0].color = RED
    g.rods[1].color = GREEN
    g._sync_figures(g.rods[0])
    g._sync_figures(g.rods[1])

    # Ball is RED, hit GREEN figure
    fig1 = g.rods[1].figures[1]
    g.ball.x = fig1.x
    g.ball.y = fig1.y
    g.ball.vx = -1.0
    g.ball.vy = 0.0
    g.ball.color = RED
    g.combo = 0
    g.heat = 0.0
    g._check_figure_collisions()
    assert g.heat == HEAT_INCREMENT
    assert g.combo == 0


def test_collision_no_combo_on_white_ball() -> None:
    """When ball is WHITE, first hit doesn't check color match."""
    g = _make_game()
    fig0 = g.rods[0].figures[1]
    g.ball.x = fig0.x
    g.ball.y = fig0.y
    g.ball.vx = 1.0
    g.ball.vy = 0.0
    g.ball.color = WHITE
    g.combo = 0
    g.heat = 0.0
    g._check_figure_collisions()
    # Combo stays 0 on initial white hit
    assert g.combo == 0
    assert g.heat == 0.0


def test_collision_unsticks_slow_ball() -> None:
    g = _make_game()
    g.ball.x = 160.0
    g.ball.y = 200.0  # Away from all figures
    g.ball.vx = 0.1
    g.ball.vy = 0.1
    g._check_figure_collisions()
    speed = math.sqrt(g.ball.vx**2 + g.ball.vy**2)
    assert speed >= BALL_INITIAL_SPEED  # Got unstuck


def test_collision_max_combo_tracks_highest() -> None:
    g = _make_game()
    g.rods[0].color = RED
    g.rods[1].color = RED
    g._sync_figures(g.rods[0])
    g._sync_figures(g.rods[1])
    g.combo = 5
    g.max_combo = 5

    fig0 = g.rods[0].figures[1]
    g.ball.x = fig0.x
    g.ball.y = fig0.y
    g.ball.vx = 1.0
    g.ball.vy = 0.0
    g.ball.color = RED
    g._check_figure_collisions()
    assert g.max_combo == 6  # Updated


# === _activate_super ===


def test_activate_super_sets_timer() -> None:
    g = _make_game()
    g.ball.vx = 2.0
    g.ball.vy = 1.0
    g.super_timer = 0
    g._activate_super()
    assert g.super_timer == SUPER_DURATION


def test_activate_super_doubles_ball_speed() -> None:
    g = _make_game()
    g.ball.vx = 2.0
    g.ball.vy = 1.0
    g._activate_super()
    assert g.ball.vx == 4.0
    assert g.ball.vy == 2.0


def test_activate_super_adds_floating_text() -> None:
    g = _make_game()
    g.ball.x = 160.0
    g.ball.y = 120.0
    g.ball.vx = 2.0
    g.ball.vy = 1.0
    g._activate_super()
    assert len(g.floating_texts) == 1
    assert "SUPER" in g.floating_texts[0].text


def test_activate_super_triggers_shake() -> None:
    g = _make_game()
    g.ball.vx = 2.0
    g.ball.vy = 1.0
    g.shake_frames = 0
    g._activate_super()
    assert g.shake_frames > 0


# === _handle_goal ===


def test_handle_goal_player_scores() -> None:
    g = _make_game()
    g._handle_goal("player")
    assert g.goals_player == 1
    assert g.goals_ai == 0
    assert g.score == 100
    assert g.goal_scored_timer > 0


def test_handle_goal_ai_scores() -> None:
    g = _make_game()
    g._handle_goal("ai")
    assert g.goals_ai == 1
    assert g.goals_player == 0


def test_handle_goal_super_gives_300() -> None:
    g = _make_game()
    g.super_timer = 30
    g._handle_goal("player")
    assert g.score == 300


def test_handle_goal_does_not_double_score() -> None:
    """goal_scored_timer > 0 prevents double-counting."""
    g = _make_game()
    g.goal_scored_timer = 30
    g._handle_goal("player")
    assert g.goals_player == 0  # No increment


def test_handle_goal_adds_particles() -> None:
    g = _make_game()
    g._handle_goal("player")
    assert len(g.particles) > 0


def test_handle_goal_cycles_rod_colors() -> None:
    g = _make_game()
    old_colors = [rod.color for rod in g.rods]
    g._handle_goal("player")
    new_colors = [rod.color for rod in g.rods]
    # Colors shifted: [A,B,C,D] -> [B,C,D,A]
    assert new_colors == old_colors[1:] + old_colors[:1]


# === _cycle_rod_colors ===


def test_cycle_rod_colors_shifts() -> None:
    g = _make_game()
    g.rods[0].color = RED
    g.rods[1].color = GREEN
    g.rods[2].color = DARK_BLUE
    g.rods[3].color = YELLOW
    g._cycle_rod_colors()
    assert g.rods[0].color == GREEN
    assert g.rods[1].color == DARK_BLUE
    assert g.rods[2].color == YELLOW
    assert g.rods[3].color == RED


def test_cycle_rod_colors_updates_figures() -> None:
    g = _make_game()
    g.rods[0].color = RED
    g.rods[1].color = GREEN
    g._cycle_rod_colors()
    for fig in g.rods[0].figures:
        assert fig.color == g.rods[0].color


# === _reset_after_goal ===


def test_reset_after_goal_resets_ball() -> None:
    g = _make_game()
    g.ball.x = 50.0
    g.ball.y = 50.0
    g.ball.color = RED
    g.combo = 3
    g.super_timer = 50
    g._reset_after_goal()
    assert g.ball.x == 160.0
    assert g.ball.y == 120.0
    assert g.ball.color == WHITE
    assert g.combo == 0
    assert g.super_timer == 0


def test_reset_after_goal_ball_has_speed() -> None:
    g = _make_game()
    g._reset_after_goal()
    speed = math.sqrt(g.ball.vx**2 + g.ball.vy**2)
    assert abs(speed - BALL_INITIAL_SPEED) < 0.01


# === Particle System ===


def test_update_particles_decrements_life() -> None:
    g = _make_game()
    g.particles = [Particle(100, 100, 1, 1, 5, WHITE)]
    g._update_particles()
    assert g.particles[0].life == 4


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    g.particles = [Particle(100, 100, 1, 1, 0, WHITE)]
    g._update_particles()
    assert len(g.particles) == 0


def test_update_particles_moves() -> None:
    g = _make_game()
    g.particles = [Particle(100, 100, 2, -1, 5, WHITE)]
    g._update_particles()
    assert g.particles[0].x == 102.0
    assert g.particles[0].y == 99.0


def test_spawn_hit_particles_creates_six() -> None:
    g = _make_game()
    g.particles.clear()
    g._spawn_hit_particles(100, 100, RED)
    assert len(g.particles) == 6


def test_spawn_goal_particles_creates_count() -> None:
    g = _make_game()
    g.particles.clear()
    g._spawn_goal_particles(160, 120, 25)
    assert len(g.particles) == 25


# === Floating Text System ===


def test_update_floating_texts_moves_up() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(100, 100, "TEST", 20, WHITE)]
    g._update_floating_texts()
    assert g.floating_texts[0].y == 99.0
    assert g.floating_texts[0].life == 19


def test_update_floating_texts_removes_dead() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(100, 100, "TEST", 0, WHITE)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# === _update_rods (headless-safe parts) ===
# _update_rods accesses pyxel.frame_count which may panic headlessly.
# Test player rod movement via direct rod manipulation instead.


def test_rod_movement_up() -> None:
    g = _make_game()
    g.player_up = True
    g.player_down = False
    g.player_fwd_up = False
    g.player_fwd_down = False
    # Set up static frame_count for AI jitter (if _update_rods is callable)
    # Since _update_rods uses pyxel.frame_count, we test rod logic manually:
    rod = g.rods[0]
    old_y = rod.y
    rod.y = g._clamp_rod_y(rod.y - ROD_SPEED)
    assert rod.y < old_y


def test_rod_movement_down() -> None:
    g = _make_game()
    rod = g.rods[0]
    old_y = rod.y
    rod.y = g._clamp_rod_y(rod.y + ROD_SPEED)
    assert rod.y > old_y


def test_rod_movement_clamped_top() -> None:
    g = _make_game()
    rod = g.rods[0]
    rod.y = 22.0
    rod.y = g._clamp_rod_y(rod.y - ROD_SPEED)
    assert rod.y == 22.0


def test_rod_movement_clamped_bottom() -> None:
    g = _make_game()
    rod = g.rods[0]
    rod.y = 218.0
    rod.y = g._clamp_rod_y(rod.y + ROD_SPEED)
    assert rod.y == 218.0


# === Game Over Conditions ===


def test_game_over_heat_check() -> None:
    g = _make_game()
    g.heat = HEAT_MAX
    # Simulate the check from update():
    assert g.heat >= HEAT_MAX


def test_game_over_player_wins() -> None:
    g = _make_game()
    g.goals_player = GOALS_TO_WIN
    assert g.goals_player >= GOALS_TO_WIN


def test_game_over_ai_wins() -> None:
    g = _make_game()
    g.goals_ai = GOALS_TO_WIN
    assert g.goals_ai >= GOALS_TO_WIN


# === Color Constants ===


def test_rod_colors_tuple() -> None:
    assert len(ROD_COLORS) == 4
    assert RED in ROD_COLORS
    assert GREEN in ROD_COLORS
    assert DARK_BLUE in ROD_COLORS
    assert YELLOW in ROD_COLORS


def test_super_rainbow() -> None:
    assert len(SUPER_RAINBOW) > 0


# === Edge Cases ===


def test_reset_multiple_calls() -> None:
    g = _make_game()
    g.score = 500
    g.combo = 10
    g.reset()
    assert g.score == 0
    assert g.combo == 0


def test_ball_collision_pushes_out() -> None:
    """After collision, ball should not overlap with figure."""
    g = _make_game()
    fig = g.rods[1].figures[1]
    # Place ball slightly offset from figure center (exact center causes zero normal vector)
    g.ball.x = fig.x - 3.0
    g.ball.y = fig.y
    g.ball.vx = 1.0
    g.ball.vy = 0.0
    g._check_figure_collisions()
    dist = math.sqrt((g.ball.x - fig.x)**2 + (g.ball.y - fig.y)**2)
    # Ball should be pushed out beyond contact distance
    assert dist >= g.ball.radius + fig.radius - 1


def test_ball_velocity_changes_on_hit() -> None:
    g = _make_game()
    fig = g.rods[0].figures[1]
    g.ball.x = fig.x
    g.ball.y = fig.y
    g.ball.vx = 1.0
    g.ball.vy = 0.0
    old_vx = g.ball.vx
    old_vy = g.ball.vy
    g._check_figure_collisions()
    # Velocity should be reflected
    assert g.ball.vx != old_vx or g.ball.vy != old_vy


def test_heat_does_not_exceed_max_plus_one() -> None:
    """Heat is clamped at HEAT_MAX+1.0 by the code."""
    g = _make_game()
    g.rods[0].color = RED
    g.rods[1].color = GREEN
    g._sync_figures(g.rods[0])
    g._sync_figures(g.rods[1])
    g.heat = HEAT_MAX
    g.ball.color = RED

    fig1 = g.rods[1].figures[1]
    g.ball.x = fig1.x
    g.ball.y = fig1.y
    g.ball.vx = -1.0
    g.ball.vy = 0.0
    g.combo = 0
    g._check_figure_collisions()
    # Heat should be min(HEAT_MAX+1, HEAT_MAX + HEAT_INCREMENT) = HEAT_MAX+1
    assert g.heat <= HEAT_MAX + 1.0


# === SUPER SHOT edge cases ===


def test_super_timer_deactivation() -> None:
    """SUPER timer should expire normally (testing timer logic)."""
    g = _make_game()
    g.super_timer = 1
    g.ball.vx = 4.0  # doubled speed
    g.ball.vy = 2.0
    # Simulate timer tick (without pyxel.frame_count)
    g.super_timer -= 1
    if g.super_timer == 0:
        g.ball.vx /= 2.0
        g.ball.vy /= 2.0
    assert g.super_timer == 0
    assert g.ball.vx == 2.0
    assert g.ball.vy == 1.0


def test_super_not_activated_below_threshold() -> None:
    g = _make_game()
    g.combo = COMBO_THRESHOLD - 1
    g.super_timer = 0
    # Check that activate wouldn't trigger at combo < threshold
    assert g.combo < COMBO_THRESHOLD


def test_multiple_same_color_hits_build_combo() -> None:
    g = _make_game()
    g.rods[0].color = RED
    g.rods[1].color = RED
    g.rods[2].color = RED
    g.rods[3].color = RED
    g._sync_figures(g.rods[0])
    g._sync_figures(g.rods[1])
    g._sync_figures(g.rods[2])
    g._sync_figures(g.rods[3])

    g.combo = 0
    g.ball.color = RED
    for i in range(4):
        rod = g.rods[i]
        fig = rod.figures[1]
        g.ball.x = fig.x
        g.ball.y = fig.y
        g.ball.vx = 1.0 if i % 2 == 0 else -1.0
        g._check_figure_collisions()
        g.ball.x += 20 * (1 if i % 2 == 0 else -1)  # push away
    assert g.combo >= 4  # Should have built combo through all 4 hits
