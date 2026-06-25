"""test_imports.py — Headless logic tests for 159_kite_surge."""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/159_kite_surge")
from main import (  # noqa: E402
    Game,
    Phase,
    WindGust,
    Particle,
    FloatingText,
    EchoPoint,
)


def _make_game() -> Game:
    """Create a Game bypassing pyxel.init/run for headless testing."""
    g = Game.__new__(Game)
    g.rng = random.Random(42)
    g.gusts = []
    g.particles = []
    g.floats = []
    g.echo_trail = []
    g.current_trail = []
    g.tail_segments = []
    g.best_score = 0
    g.sky_stars = []
    g.sky_bands = []
    g.reset()
    return g


# ── Dataclass Tests ──


def test_wind_gust_defaults() -> None:
    g = WindGust(x=100.0, y=50.0, vx=-1.0, color=8, radius=10)
    assert g.alive is True
    assert g.x == 100.0
    assert g.color == 8


def test_particle() -> None:
    p = Particle(x=10.0, y=20.0, vx=0.5, vy=-1.0, life=15, color=8)
    assert p.radius == 2.0
    assert p.life == 15


def test_floating_text() -> None:
    ft = FloatingText(x=100.0, y=50.0, text="+10", life=30, color=8)
    assert ft.vy == -1.5
    assert ft.life == 30


# ── Phase Enum Tests ──


def test_phase_values() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ── Game Reset Tests ──


def test_reset_initial_state() -> None:
    g = _make_game()
    g.reset()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.timer == Game.GAME_DURATION
    assert g.heat_triggered is False
    assert len(g.tail_segments) == Game.TAIL_COUNT
    assert len(g.gusts) == 0
    assert len(g.particles) == 0
    assert len(g.floats) == 0


def test_reset_kite_color_default() -> None:
    g = _make_game()
    assert g.kite_color_idx == 0
    assert g.kite_color == Game.COLOR_CYCLE[0]


# ── Kite Movement Tests ──


def test_update_kite_up() -> None:
    g = _make_game()
    g.kite_y = 100.0
    g._update_kite(-1)
    assert g.kite_y == 98.0


def test_update_kite_down() -> None:
    g = _make_game()
    g.kite_y = 100.0
    g._update_kite(1)
    assert g.kite_y == 102.0


def test_update_kite_neutral() -> None:
    g = _make_game()
    g.kite_y = 100.0
    g._update_kite(0)
    assert g.kite_y == 100.0


def test_update_kite_upper_bound() -> None:
    g = _make_game()
    g.kite_y = Game.KITE_Y_MIN
    g._update_kite(-1)
    assert g.kite_y == Game.KITE_Y_MIN  # clamped


def test_update_kite_lower_bound() -> None:
    g = _make_game()
    g.kite_y = Game.KITE_Y_MAX
    g._update_kite(1)
    assert g.kite_y == Game.KITE_Y_MAX  # clamped


# ── Color Cycle Tests ──


def test_cycle_color_no_change_before_timer() -> None:
    g = _make_game()
    g.color_timer = 100
    g.kite_color_idx = 0
    g._cycle_color()
    assert g.color_timer == 99
    assert g.kite_color_idx == 0  # unchanged


def test_cycle_color_at_zero() -> None:
    g = _make_game()
    g.color_timer = 1
    g.kite_color_idx = 0
    g._cycle_color()
    assert g.color_timer == Game.COLOR_CYCLE_DURATION  # reset
    assert g.kite_color_idx == 1  # cycled to next


def test_cycle_color_wraps() -> None:
    g = _make_game()
    g.color_timer = 1
    g.kite_color_idx = 3  # last index
    g._cycle_color()
    assert g.kite_color_idx == 0  # wrap around


def test_kite_color_property() -> None:
    g = _make_game()
    g.kite_color_idx = 0
    assert g.kite_color == Game.COLOR_CYCLE[0]
    g.kite_color_idx = 2
    assert g.kite_color == Game.COLOR_CYCLE[2]


# ── Collision Tests ──


def test_check_collision_overlapping() -> None:
    g = _make_game()
    g.kite_y = 100.0
    gust = WindGust(x=Game.KITE_X, y=100.0, vx=-1, color=8, radius=10)
    assert g._check_collision(gust) is True


def test_check_collision_far_away() -> None:
    g = _make_game()
    g.kite_y = 100.0
    gust = WindGust(x=300.0, y=200.0, vx=-1, color=8, radius=10)
    assert g._check_collision(gust) is False


def test_check_collision_dead_gust() -> None:
    g = _make_game()
    g.kite_y = 100.0
    gust = WindGust(x=Game.KITE_X, y=100.0, vx=-1, color=8, radius=10, alive=False)
    assert g._check_collision(gust) is False


def test_check_collision_near_threshold() -> None:
    g = _make_game()
    g.kite_y = 100.0
    # collision_dist = 6 + radius. For radius=10: threshold = 16
    # Place gust at exactly 16px away → should trigger (strict <)
    gust = WindGust(x=Game.KITE_X + 15.9, y=100.0, vx=-1, color=8, radius=10)
    assert g._check_collision(gust) is True
    gust2 = WindGust(x=Game.KITE_X + 17.0, y=100.0, vx=-1, color=8, radius=10)
    assert g._check_collision(gust2) is False


# ── Match / Resolve Gust Tests ──


def test_resolve_match_increments_combo_and_score() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.kite_y = 100.0
    g.kite_color_idx = 0  # RED
    gust = WindGust(x=80.0, y=100.0, vx=-1, color=g.kite_color, radius=10)
    g.gusts = [gust]
    g._check_all_collisions()
    assert gust.alive is False
    assert g.combo == 1
    assert g.score > 0


def test_resolve_match_builds_combo_chain() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.kite_y = 100.0
    g.kite_color_idx = 0
    for expected_combo in range(1, 5):
        gust = WindGust(x=80.0, y=100.0, vx=-1, color=g.kite_color, radius=10)
        g.gusts = [gust]
        g._check_all_collisions()
        assert g.combo == expected_combo


def test_resolve_match_updates_max_combo() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.kite_y = 100.0
    g.kite_color_idx = 0
    for _ in range(3):
        gust = WindGust(x=80.0, y=100.0, vx=-1, color=g.kite_color, radius=10)
        g.gusts = [gust]
        g._check_all_collisions()
    assert g.max_combo == 3


def test_resolve_mismatch_adds_heat() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.kite_y = 100.0
    g.kite_color_idx = 0  # RED
    wrong_color = Game.COLOR_CYCLE[1]  # GREEN
    gust = WindGust(x=80.0, y=100.0, vx=-1, color=wrong_color, radius=10)
    g.gusts = [gust]
    g._check_all_collisions()
    assert gust.alive is False
    assert g.heat == Game.HEAT_PER_MISS


def test_resolve_mismatch_resets_combo() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.kite_y = 100.0
    g.kite_color_idx = 0
    g.combo = 3
    g.max_combo = 3
    wrong_color = Game.COLOR_CYCLE[1]
    gust = WindGust(x=80.0, y=100.0, vx=-1, color=wrong_color, radius=10)
    g.gusts = [gust]
    g._check_all_collisions()
    assert g.combo == 0
    # max_combo should still be 3 (not reset)
    assert g.max_combo == 3


def test_resolve_mismatch_heat_clamped() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.kite_y = 100.0
    g.kite_color_idx = 0
    g.heat = 95.0
    wrong_color = Game.COLOR_CYCLE[1]
    gust = WindGust(x=80.0, y=100.0, vx=-1, color=wrong_color, radius=10)
    g.gusts = [gust]
    g._check_all_collisions()
    assert g.heat == Game.HEAT_MAX  # clamped at 100


# ── Super Mode Tests ──


def test_super_mode_activation_at_combo_4() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.kite_y = 100.0
    g.kite_color_idx = 0
    for _ in range(4):
        gust = WindGust(x=80.0, y=100.0, vx=-1, color=g.kite_color, radius=10)
        g.gusts = [gust]
        g._check_all_collisions()
    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == Game.SUPER_DURATION


def test_super_mode_no_activation_before_combo_4() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.kite_y = 100.0
    g.kite_color_idx = 0
    for _ in range(3):
        gust = WindGust(x=80.0, y=100.0, vx=-1, color=g.kite_color, radius=10)
        g.gusts = [gust]
        g._check_all_collisions()
    assert g.combo == 3
    assert g.super_mode is False


def test_super_timer_decrements() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g._update_super_timer()
    assert g.super_timer == 99
    assert g.super_mode is True


def test_super_timer_expires() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_super_timer()
    assert g.super_timer == 0
    assert g.super_mode is False


def test_super_timer_zero_does_nothing() -> None:
    g = _make_game()
    g.super_mode = False
    g.super_timer = 0
    g._update_super_timer()
    assert g.super_mode is False
    assert g.super_timer == 0


# ── Heat Tests ──


def test_heat_decay() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert abs(g.heat - (50.0 - Game.HEAT_DECAY)) < 0.001


def test_heat_game_over_at_max() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = Game.HEAT_MAX
    g._update_heat()
    assert g.heat_triggered is True
    assert g.phase == Phase.GAME_OVER


def test_heat_decay_to_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0  # clamped at 0 by max(0.0, ...)


def test_heat_no_trigger_below_max() -> None:
    g = _make_game()
    g.heat = Game.HEAT_MAX - 0.01
    g._update_heat()
    assert g.heat_triggered is False
    assert g.phase != Phase.GAME_OVER


# ── Timer Tests ──


def test_timer_decrements() -> None:
    g = _make_game()
    g.timer = 50.0
    g._update_timer()
    assert abs(g.timer - (50.0 - 1.0 / 60.0)) < 0.001


def test_timer_game_over_at_zero() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.timer = 0.01  # will go to 0 or below
    g._update_timer()
    assert g.timer == 0.0  # clamped
    assert g.phase == Phase.GAME_OVER


def test_timer_game_over_below_zero() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.timer = 0.0
    g._update_timer()
    assert g.timer == 0.0
    assert g.phase == Phase.GAME_OVER


# ── Spawn Gust Tests ──


def test_spawn_gust_adds_gust() -> None:
    g = _make_game()
    initial_count = len(g.gusts)
    g.spawn_cooldown = 0
    g._spawn_gust()
    assert len(g.gusts) == initial_count + 1


def test_spawn_gust_sets_cooldown() -> None:
    g = _make_game()
    g.spawn_cooldown = 0
    g._spawn_gust()
    assert g.spawn_cooldown > 0


def test_spawn_gust_respects_cooldown() -> None:
    g = _make_game()
    g.spawn_cooldown = 5
    initial_count = len(g.gusts)
    g._spawn_gust()
    assert len(g.gusts) == initial_count  # no spawn
    assert g.spawn_cooldown == 4  # decremented


def test_spawn_gust_respects_max() -> None:
    g = _make_game()
    g.spawn_cooldown = 0
    # Fill up to MAX_GUSTS
    for _ in range(Game.MAX_GUSTS):
        g._spawn_gust()
        g.spawn_cooldown = 0
    active = sum(1 for gust in g.gusts if gust.alive)
    assert active <= Game.MAX_GUSTS
    # Try to spawn one more
    g._spawn_gust()
    active2 = sum(1 for gust in g.gusts if gust.alive)
    assert active2 <= Game.MAX_GUSTS


def test_spawn_gust_within_bounds() -> None:
    g = _make_game()
    g.spawn_cooldown = 0
    for _ in range(Game.MAX_GUSTS):
        g._spawn_gust()
        g.spawn_cooldown = 0
    for gust in g.gusts:
        assert 30 <= gust.y <= Game.SCREEN_H - 20
        assert gust.radius in (8, 9, 10, 11, 12)
        assert gust.color in Game.COLOR_CYCLE


# ── Gust Update Tests ──


def test_update_gusts_moves_gust() -> None:
    g = _make_game()
    gust = WindGust(x=200.0, y=100.0, vx=-1.5, color=8, radius=10)
    g.gusts = [gust]
    g._update_gusts()
    assert abs(gust.x - 198.5) < 0.01


def test_update_gusts_removes_offscreen() -> None:
    g = _make_game()
    gust = WindGust(x=-25.0, y=100.0, vx=-1.0, color=8, radius=10)
    g.gusts = [gust]
    g._update_gusts()
    assert len(g.gusts) == 0  # removed (x <= -20)


def test_update_gusts_keeps_on_edge() -> None:
    g = _make_game()
    gust = WindGust(x=-19.0, y=100.0, vx=-1.0, color=8, radius=10)
    g.gusts = [gust]
    g._update_gusts()
    assert len(g.gusts) == 1  # kept (x > -20)


# ── Particle Tests ──


def test_spawn_particles() -> None:
    g = _make_game()
    g._spawn_particles(100.0, 50.0, 8, 10)
    assert len(g.particles) == 10
    for p in g.particles:
        assert p.x == 100.0
        assert p.y == 50.0
        assert p.color == 8


def test_update_particles_moves() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=50.0, vx=1.0, vy=-1.0, life=10, color=8)
    g.particles = [p]
    g._update_particles()
    assert abs(p.x - 101.0) < 0.01
    assert p.y < 50.0  # gravity vy += grav before move


def test_update_particles_decrements_life() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=50.0, vx=0.0, vy=0.0, life=5, color=8)
    g.particles = [p]
    g._update_particles()
    assert p.life == 4


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=50.0, vx=0.0, vy=0.0, life=1, color=8)
    g.particles = [p]
    g._update_particles()
    assert len(g.particles) == 0  # life 1 → 0, removed


def test_update_particles_gravity() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=50.0, vx=0.0, vy=0.0, life=10, color=8)
    g.particles = [p]
    g._update_particles()
    assert p.vy > 0  # gravity applied (0.05)


# ── Floating Text Tests ──


def test_add_float() -> None:
    g = _make_game()
    g._add_float(100.0, 50.0, "+10", 8)
    assert len(g.floats) == 1
    assert g.floats[0].text == "+10"
    assert g.floats[0].color == 8


def test_update_floats_moves_up() -> None:
    g = _make_game()
    ft = FloatingText(x=100.0, y=50.0, text="+10", life=30, color=8)
    g.floats = [ft]
    g._update_floats()
    assert ft.y == 48.5  # y + vy (-1.5)


def test_update_floats_decrements_life() -> None:
    g = _make_game()
    ft = FloatingText(x=100.0, y=50.0, text="+10", life=10, color=8)
    g.floats = [ft]
    g._update_floats()
    assert ft.life == 9


def test_update_floats_removes_dead() -> None:
    g = _make_game()
    ft = FloatingText(x=100.0, y=50.0, text="+10", life=1, color=8)
    g.floats = [ft]
    g._update_floats()
    assert len(g.floats) == 0


# ── Game Over & Best Score Tests ──


def test_game_over_records_best_score() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.score = 500
    g.best_score = 300
    g.heat = Game.HEAT_MAX
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 500  # updated


def test_game_over_preserves_existing_best() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.score = 200
    g.best_score = 500
    g.heat = Game.HEAT_MAX
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 500  # unchanged


def test_game_over_echo_trail_recorded() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.score = 500
    g.best_score = 300
    g.current_trail = [EchoPoint(x=10.0, y=20.0, color=8)]
    g.heat = Game.HEAT_MAX
    g._update_heat()
    assert len(g.echo_trail) == 1
    assert g.echo_trail[0].x == 10.0


# ── Score Calculation Tests ──


def test_score_increases_with_combo() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.kite_y = 100.0
    g.kite_color_idx = 0

    # Combo 1: BASE * (1 + 1*0.5) = 10 * 1.5 = 15
    gust1 = WindGust(x=80.0, y=100.0, vx=-1, color=g.kite_color, radius=10)
    g.gusts = [gust1]
    g._check_all_collisions()
    score_after_1 = g.score

    # Combo 2: BASE * (1 + 2*0.5) = 10 * 2.0 = 20
    gust2 = WindGust(x=80.0, y=100.0, vx=-1, color=g.kite_color, radius=10)
    g.gusts = [gust2]
    g._check_all_collisions()
    score_after_2 = g.score

    assert score_after_2 > score_after_1


# ── Score multiplier tests ──


def test_score_gain_increases_with_higher_combo() -> None:
    """Higher combo should give more points per match."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.kite_y = 100.0
    g.kite_color_idx = 0
    g.combo = 5  # already high combo
    gust = WindGust(x=80.0, y=100.0, vx=-1, color=g.kite_color, radius=10)
    g.gusts = [gust]
    g._check_all_collisions()
    assert g.combo == 6
    assert g.score > Game.BASE_SCORE * 3  # (1 + 6*0.5) = 4x * 10 = 40


def test_mismatch_does_not_add_score() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.kite_y = 100.0
    g.kite_color_idx = 0
    g.score = 0
    wrong_color = Game.COLOR_CYCLE[1]
    gust = WindGust(x=80.0, y=100.0, vx=-1, color=wrong_color, radius=10)
    g.gusts = [gust]
    g._check_all_collisions()
    assert g.score == 0


# ── Multiple Gusts Tests ──


def test_multiple_gusts_same_frame_mixed() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.kite_y = 100.0
    g.kite_color_idx = 0
    # Two gusts at same spot: one matching, one wrong
    gust_match = WindGust(x=80.0, y=100.0, vx=-1, color=g.kite_color, radius=10)
    gust_wrong = WindGust(x=80.0, y=100.0, vx=-1, color=Game.COLOR_CYCLE[1], radius=10)
    g.gusts = [gust_match, gust_wrong]
    g._check_all_collisions()
    assert gust_match.alive is False
    assert gust_wrong.alive is False
    # Both were alive when looped; depends on order
    assert g.combo >= 0


def test_already_dead_gust_skipped() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.kite_y = 100.0
    g.kite_color_idx = 0
    gust = WindGust(x=80.0, y=100.0, vx=-1, color=g.kite_color, radius=10, alive=False)
    g.gusts = [gust]
    g._check_all_collisions()
    # Should be skipped — still dead, combo unchanged
    assert g.combo == 0


# ── Trail Tests ──


def test_record_trail_adds_point() -> None:
    g = _make_game()
    initial = len(g.current_trail)
    g.kite_y = 100.0
    g.kite_color_idx = 2
    g._record_trail()
    assert len(g.current_trail) == initial + 1
    assert g.current_trail[-1].x == Game.KITE_X
    assert g.current_trail[-1].y == 100.0
    assert g.current_trail[-1].color == Game.COLOR_CYCLE[2]


# ── Tail Segment Tests ──


def test_tail_segments_initialized() -> None:
    g = _make_game()
    assert len(g.tail_segments) == Game.TAIL_COUNT
    for seg in g.tail_segments:
        assert seg.x == Game.KITE_X


# ── Class Constant Tests ──


def test_class_constants() -> None:
    assert Game.SCREEN_W == 320
    assert Game.SCREEN_H == 240
    assert Game.HEAT_MAX == 100.0
    assert Game.HEAT_PER_MISS == 20.0
    assert Game.GAME_DURATION == 90.0
    assert len(Game.COLOR_CYCLE) == 4
    assert Game.COLOR_CYCLE[0] == 8  # RED
    assert Game.COLOR_CYCLE[1] == 3  # GREEN
    assert Game.COLOR_CYCLE[2] == 5  # DARK_BLUE
    assert Game.COLOR_CYCLE[3] == 10  # YELLOW


# ── Heat decay ordering test (pitfall check) ──


def test_heat_check_before_decay() -> None:
    """Verify heat >= MAX check happens BEFORE decay, not after."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = Game.HEAT_MAX
    # heat == MAX → should trigger game over immediately
    g._update_heat()
    assert g.heat_triggered is True
    assert g.phase == Phase.GAME_OVER
    # heat should NOT have been decayed (returned before decay line)
    assert g.heat == Game.HEAT_MAX
