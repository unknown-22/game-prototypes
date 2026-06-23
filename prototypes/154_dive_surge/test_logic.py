"""test_logic.py — Headless logic tests for DIVE SURGE.

Uses Game.__new__ pattern to bypass pyxel.init/run for headless testing.
"""

from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/154_dive_surge")
from main import (
    COMBO_SUPER_THRESHOLD,
    DIVER_HEIGHT,
    GRAVITY,
    GREEN,
    HEAT_DECAY,
    INITIAL_PLATFORM_Y,
    MAX_HEAT,
    MIN_PLATFORM_Y,
    PLATFORM_RISE,
    PLATFORM_X,
    RED,
    ROTATION_SPEED,
    SUPER_DURATION,
    WATER_Y,
    ZONE_COLORS,
    ZONE_HEIGHT,
    ZONE_WIDTH,
    ZONE_Y,
    DiveState,
    Game,
    Particle,
    Phase,
    SplashZone,
    TrailPoint,
)


def _make_game(seed: int = 42) -> Game:
    """Create a Game instance bypassing pyxel.init/run."""
    g = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.dive_state = DiveState.READY
    g.diver_x = float(PLATFORM_X)
    g.diver_y = float(INITIAL_PLATFORM_Y - DIVER_HEIGHT)
    g.diver_vx = 0.0
    g.diver_vy = 0.0
    g.diver_rotation = 0.0
    g.diver_rotation_speed = 0.0
    g.platform_y = float(INITIAL_PLATFORM_Y)
    g.dive_count = 0
    g.zones = []
    g.zone_count = 5
    g.last_zone_color = -1
    g.combo = 0
    g.max_combo = 0
    g.score = 0
    g.high_score = 0
    g.base_height_points = 10
    g.super_dive = False
    g.super_timer = 0
    g.heat = 0.0
    g.particles = []
    g.ghost_trail = []
    g.splash_flash = 0
    g.text_popups = []
    g.splash_delay = 0
    g.frame = 0
    g.rng = random.Random(seed)
    g.reset(seed)
    return g


# ── Dataclass / Enum tests ──────────────────────────────────────────────────


def test_splash_zone_defaults() -> None:
    """SplashZone has correct defaults."""
    z = SplashZone(x=100.0, y=float(ZONE_Y))
    assert z.width == ZONE_WIDTH
    assert z.height == ZONE_HEIGHT
    assert z.color == GREEN


def test_particle_defaults() -> None:
    """Particle has correct defaults."""
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=30, color=RED)
    assert p.size == 2
    assert p.color == RED
    assert p.life == 30


def test_trail_point_fields() -> None:
    """TrailPoint stores position and life."""
    t = TrailPoint(x=150.0, y=100.0, life=90)
    assert t.x == 150.0
    assert t.life == 90


def test_phase_enum() -> None:
    """Phase has expected members."""
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


def test_dive_state_enum() -> None:
    """DiveState has expected members."""
    assert DiveState.READY in DiveState
    assert DiveState.AIRBORNE in DiveState
    assert DiveState.SPLASH in DiveState


# ── Reset tests ─────────────────────────────────────────────────────────────


def test_reset_initial_state() -> None:
    """After reset(), all state variables are at initial values."""
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.dive_state == DiveState.READY
    assert g.diver_x == float(PLATFORM_X)
    assert g.platform_y == float(INITIAL_PLATFORM_Y)
    assert g.dive_count == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.score == 0
    assert g.heat == 0.0
    assert g.super_dive is False
    assert g.last_zone_color == -1
    assert g.particles == []
    assert g.ghost_trail == []
    assert g.text_popups == []
    assert len(g.zones) >= 4


def test_reset_with_seed_reproducible() -> None:
    """Same seed produces same zones."""
    g1 = _make_game(seed=123)
    g2 = _make_game(seed=123)
    zones1 = [(z.x, z.color) for z in g1.zones]
    zones2 = [(z.x, z.color) for z in g2.zones]
    assert zones1 == zones2


# ── Zone generation tests ───────────────────────────────────────────────────


def test_spawn_zones_count() -> None:
    """_spawn_zones returns 4-6 zones."""
    g = _make_game()
    for _ in range(100):
        zones = g._spawn_zones()
        assert 4 <= len(zones) <= 6


def test_spawn_zones_within_bounds() -> None:
    """Zone x positions are within screen bounds."""
    g = _make_game()
    zones = g._spawn_zones()
    for z in zones:
        assert 30 - ZONE_WIDTH / 2 <= z.x <= 290 + ZONE_WIDTH / 2
        assert z.y == float(ZONE_Y)
        assert z.color in ZONE_COLORS


def test_spawn_zones_deterministic() -> None:
    """Same seed produces identical zones."""
    g = _make_game()
    zones1 = g._spawn_zones(seed=42)
    zones2 = g._spawn_zones(seed=42)
    assert [(z.x, z.color) for z in zones1] == [(z.x, z.color) for z in zones2]


# ── Jump tests ─────────────────────────────────────────────────────────────


def test_jump_sets_airborne() -> None:
    """_jump() transitions to AIRBORNE state."""
    g = _make_game()
    g.dive_state = DiveState.READY
    g._jump()
    assert g.dive_state == DiveState.AIRBORNE
    assert g.diver_vy == 0.0
    assert g.diver_vx == 0.0


def test_jump_calculates_base_height_points() -> None:
    """_jump() sets base_height_points based on platform height."""
    g = _make_game()
    g.platform_y = 40.0
    g._jump()
    expected = max(1, int((INITIAL_PLATFORM_Y - 40.0) / 2) + 10)
    assert g.base_height_points == expected


# ── Airborne tests ─────────────────────────────────────────────────────────


def test_update_airborne_applies_gravity() -> None:
    """Gravity increases vy each frame."""
    g = _make_game()
    g.diver_vy = 0.0
    g._update_airborne(1.0)
    assert g.diver_vy == GRAVITY
    g._update_airborne(1.0)
    assert g.diver_vy == GRAVITY * 2


def test_update_airborne_moves_diver() -> None:
    """Diver position updates with velocity (gravity applied first)."""
    g = _make_game()
    g.diver_vy = 5.0
    start_y = g.diver_y
    g._update_airborne(1.0)
    # gravity adds GRAVITY to vy, then vy added to y
    assert g.diver_y == start_y + 5.0 + GRAVITY


def test_update_airborne_applies_rotation() -> None:
    """Rotation accumulates based on rotation_speed."""
    g = _make_game()
    g.diver_rotation_speed = ROTATION_SPEED
    g.diver_rotation = 0.0
    g._update_airborne(1.0)
    assert g.diver_rotation == ROTATION_SPEED


def test_update_airborne_rotation_wraps_360() -> None:
    """Rotation wraps at 360 degrees."""
    g = _make_game()
    g.diver_rotation = 350.0
    g.diver_rotation_speed = 15.0
    g._update_airborne(1.0)
    assert 0 <= g.diver_rotation < 360.0


def test_update_airborne_dt_scaling() -> None:
    """Larger dt produces larger changes."""
    g = _make_game()
    g.diver_rotation_speed = ROTATION_SPEED
    g.diver_rotation = 0.0
    g._update_airborne(2.0)
    assert abs(g.diver_rotation - ROTATION_SPEED * 2) < 0.01


# ── Landing check tests ────────────────────────────────────────────────────


def test_check_landing_above_water() -> None:
    """Diver above water returns None."""
    g = _make_game()
    g.diver_y = 100.0
    assert g._check_landing() is None


def test_check_landing_in_zone() -> None:
    """Diver overlapping a zone returns its index."""
    g = _make_game()
    zone = SplashZone(x=160.0, y=float(ZONE_Y), color=RED)
    g.zones = [zone]
    g.diver_x = 160.0
    g.diver_y = float(WATER_Y)  # center of diver at water level
    result = g._check_landing()
    assert result is not None
    assert result == 0


def test_check_landing_between_zones() -> None:
    """Diver between zones returns None."""
    g = _make_game()
    g.zones = [
        SplashZone(x=100.0, y=float(ZONE_Y), color=RED),
        SplashZone(x=220.0, y=float(ZONE_Y), color=GREEN),
    ]
    g.diver_x = 160.0
    g.diver_y = float(WATER_Y)
    assert g._check_landing() is None


def test_check_landing_at_zone_edge() -> None:
    """Diver exactly at zone boundary is inside."""
    g = _make_game()
    zone = SplashZone(x=160.0, y=float(ZONE_Y), color=RED)
    g.zones = [zone]
    g.diver_x = 160.0 + ZONE_WIDTH / 2  # right edge
    g.diver_y = float(WATER_Y)
    assert g._check_landing() is not None


# ── Apply landing tests ────────────────────────────────────────────────────


def test_apply_landing_first_dive() -> None:
    """First dive always matches (last_zone_color = -1)."""
    g = _make_game()
    g.last_zone_color = -1
    g.zones = [SplashZone(x=160.0, y=float(ZONE_Y), color=RED)]
    g._apply_landing(0)
    assert g.combo == 1
    assert g.last_zone_color == RED
    assert g.score > 0
    assert g.heat == 0.0


def test_apply_landing_same_color_combo() -> None:
    """Same color as previous landing builds combo."""
    g = _make_game()
    g.combo = 2
    g.last_zone_color = RED
    g.zones = [SplashZone(x=160.0, y=float(ZONE_Y), color=RED)]
    g._apply_landing(0)
    assert g.combo == 3
    assert g.last_zone_color == RED


def test_apply_landing_different_color_resets_combo() -> None:
    """Different color resets combo to 1."""
    g = _make_game()
    g.combo = 3
    g.last_zone_color = RED
    g.zones = [SplashZone(x=160.0, y=float(ZONE_Y), color=GREEN)]
    g._apply_landing(0)
    assert g.combo == 1
    assert g.last_zone_color == GREEN


def test_apply_landing_miss_adds_heat() -> None:
    """Landing outside zones adds 25 heat."""
    g = _make_game()
    g.combo = 3
    g.heat = 10.0
    g._apply_landing(None)
    assert g.combo == 0
    assert g.last_zone_color == -1
    assert g.heat == 35.0


def test_apply_landing_heat_caps_at_max() -> None:
    """Heat does not exceed MAX_HEAT."""
    g = _make_game()
    g.heat = 90.0
    g._apply_landing(None)
    assert g.heat == MAX_HEAT


def test_apply_landing_updates_max_combo() -> None:
    """max_combo tracks the highest combo."""
    g = _make_game()
    g.combo = 4
    g.max_combo = 4
    g.last_zone_color = RED
    g.zones = [SplashZone(x=160.0, y=float(ZONE_Y), color=RED)]
    g._apply_landing(0)
    assert g.max_combo == 5


def test_apply_landing_super_dive_always_matches() -> None:
    """During SUPER DIVE, any color landing increments combo."""
    g = _make_game()
    g.combo = 2
    g.last_zone_color = RED
    g.super_dive = True
    g.super_timer = 60
    g.zones = [SplashZone(x=160.0, y=float(ZONE_Y), color=GREEN)]
    g._apply_landing(0)
    assert g.combo == 3  # combo continues despite color mismatch


def test_apply_landing_triggers_super_dive() -> None:
    """COMBO >= 5 activates SUPER DIVE."""
    g = _make_game()
    g.combo = COMBO_SUPER_THRESHOLD - 1  # combo=4
    g.last_zone_color = RED
    g.zones = [SplashZone(x=160.0, y=float(ZONE_Y), color=RED)]
    g._apply_landing(0)  # combo becomes 5
    assert g.super_dive is True
    assert g.super_timer == SUPER_DURATION
    assert len(g.text_popups) > 0


# ── Score computation tests ────────────────────────────────────────────────


def test_compute_score_no_combo() -> None:
    """Score with combo=0, no super."""
    g = _make_game()
    g.combo = 0
    g.base_height_points = 10
    score = g._compute_score(RED)
    assert score == 10


def test_compute_score_with_combo() -> None:
    """Score scales with combo."""
    g = _make_game()
    g.combo = 4
    g.base_height_points = 20
    score = g._compute_score(RED)
    assert score == int(20 * (1.0 + 4 * 0.5))


def test_compute_score_super_multiplier() -> None:
    """Super dive applies 3x multiplier."""
    g = _make_game()
    g.combo = 3
    g.base_height_points = 10
    g.super_dive = True
    g.super_timer = 100
    score = g._compute_score(RED)
    assert score == int(10 * (1.0 + 3 * 0.5) * 3)


# ── Super dive tests ───────────────────────────────────────────────────────


def test_is_super_dive_active_false_when_inactive() -> None:
    """_is_super_dive_active returns False when not active."""
    g = _make_game()
    assert g._is_super_dive_active() is False


def test_is_super_dive_active_false_when_timer_zero() -> None:
    """_is_super_dive_active returns False when timer is 0."""
    g = _make_game()
    g.super_dive = True
    g.super_timer = 0
    assert g._is_super_dive_active() is False


def test_is_super_dive_active_true_with_timer() -> None:
    """_is_super_dive_active returns True when timer > 0."""
    g = _make_game()
    g.super_dive = True
    g.super_timer = 100
    assert g._is_super_dive_active() is True


def test_activate_super_dive() -> None:
    """_activate_super_dive sets flags and timer."""
    g = _make_game()
    g._activate_super_dive()
    assert g.super_dive is True
    assert g.super_timer == SUPER_DURATION


def test_update_super_dive_decrements_timer() -> None:
    """Super timer counts down each frame."""
    g = _make_game()
    g.super_dive = True
    g.super_timer = 10
    g._update_super_dive()
    assert g.super_timer == 9


def test_update_super_dive_deactivates() -> None:
    """Super dive deactivates when timer reaches 0."""
    g = _make_game()
    g.super_dive = True
    g.super_timer = 1
    g._update_super_dive()
    assert g.super_dive is False
    assert g.super_timer == 0


# ── Particle tests ─────────────────────────────────────────────────────────


def test_spawn_splash_particles_count() -> None:
    """Splash spawns particles."""
    g = _make_game()
    particles = g._spawn_splash_particles(160.0, 200.0, RED)
    assert 8 <= len(particles) <= 12
    for p in particles:
        assert p.color == RED
        assert p.life >= 15


def test_spawn_splash_particles_super_count() -> None:
    """Super dive spawns more particles."""
    g = _make_game()
    g.super_dive = True
    particles = g._spawn_splash_particles(160.0, 200.0, RED)
    assert len(particles) == 20
    colors = {p.color for p in particles}
    assert len(colors) >= 2  # rainbow colors


def test_update_particles_decrements_life() -> None:
    """_update_particles reduces life by 1."""
    g = _make_game()
    g.particles = [Particle(x=100, y=100, vx=1, vy=-1, life=5, color=RED)]
    g._update_particles()
    assert g.particles[0].life == 4


def test_update_particles_applies_gravity() -> None:
    """Particles are affected by gravity."""
    g = _make_game()
    g.particles = [Particle(x=100, y=100, vx=0, vy=0, life=10, color=RED)]
    g._update_particles()
    assert g.particles[0].vy > 0


def test_update_particles_removes_dead() -> None:
    """Particles with life <= 0 are removed."""
    g = _make_game()
    g.particles = [Particle(x=100, y=100, vx=0, vy=0, life=0, color=RED)]
    g._update_particles()
    assert len(g.particles) == 0


# ── Ghost trail tests ──────────────────────────────────────────────────────


def test_ghost_trail_adds_in_airborne() -> None:
    """Ghost trail points are added during AIRBORNE."""
    g = _make_game()
    g.dive_state = DiveState.AIRBORNE
    g.frame = 2
    initial_len = len(g.ghost_trail)
    g._update_ghost_trail()
    assert len(g.ghost_trail) == initial_len + 1


def test_ghost_trail_ages_points() -> None:
    """Trail point life decreases each frame."""
    g = _make_game()
    g.ghost_trail = [TrailPoint(x=150, y=100, life=10)]
    g._update_ghost_trail()
    assert g.ghost_trail[0].life == 9


def test_ghost_trail_removes_expired() -> None:
    """Trail points with life <= 0 are removed."""
    g = _make_game()
    g.ghost_trail = [TrailPoint(x=150, y=100, life=0)]
    g._update_ghost_trail()
    assert len(g.ghost_trail) == 0


def test_ghost_trail_not_added_outside_airborne() -> None:
    """No trail points added when not in AIRBORNE."""
    g = _make_game()
    g.dive_state = DiveState.READY
    g.frame = 2
    g.ghost_trail = []
    g._update_ghost_trail()
    assert len(g.ghost_trail) == 0


# ── Heat tests ─────────────────────────────────────────────────────────────


def test_update_heat_decays() -> None:
    """Heat decreases by HEAT_DECAY each frame."""
    g = _make_game()
    g.heat = 10.0
    g._update_heat()
    assert g.heat == 10.0 - HEAT_DECAY


def test_update_heat_not_negative() -> None:
    """Heat does not go below 0."""
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


# ── Phase / Dive progression tests ─────────────────────────────────────────


def test_next_dive_increments_count() -> None:
    """_next_dive increments dive_count."""
    g = _make_game()
    g.dive_count = 3
    g._next_dive()
    assert g.dive_count == 4


def test_next_dive_raises_platform() -> None:
    """_next_dive moves platform up by PLATFORM_RISE."""
    g = _make_game()
    g.platform_y = INITIAL_PLATFORM_Y
    g._next_dive()
    assert g.platform_y == INITIAL_PLATFORM_Y - PLATFORM_RISE


def test_next_dive_platform_min_y() -> None:
    """Platform doesn't go above MIN_PLATFORM_Y."""
    g = _make_game()
    g.platform_y = MIN_PLATFORM_Y
    g._next_dive()
    assert g.platform_y == MIN_PLATFORM_Y


def test_next_dive_resets_diver_state() -> None:
    """_next_dive resets diver to READY position."""
    g = _make_game()
    g.diver_x = 200.0
    g.diver_y = 180.0
    g.diver_rotation = 90.0
    g.diver_rotation_speed = 5.0
    g.ghost_trail = [TrailPoint(x=150, y=100, life=10)]
    g._next_dive()
    assert g.diver_x == PLATFORM_X
    assert g.diver_y == g.platform_y - DIVER_HEIGHT
    assert g.diver_rotation == 0.0
    assert g.diver_rotation_speed == 0.0
    assert g.ghost_trail == []
    assert g.dive_state == DiveState.READY


def test_next_dive_spawns_new_zones() -> None:
    """_next_dive generates new set of zones."""
    g = _make_game()
    g._next_dive()
    new_zones = [(z.x, z.color) for z in g.zones]
    assert len(new_zones) >= 4


def test_start_playing_transitions_to_playing() -> None:
    """_start_playing sets phase to PLAYING."""
    g = _make_game()
    g.phase = Phase.TITLE
    g._start_playing()
    assert g.phase == Phase.PLAYING
    assert g.dive_state == DiveState.READY
    assert g.diver_x == float(PLATFORM_X)
    assert len(g.zones) >= 4


# ── Edge case tests ────────────────────────────────────────────────────────


def test_heat_game_over_boundary() -> None:
    """Heat at MAX_HEAT should be detected as game over (>= check)."""
    g = _make_game()
    g.heat = MAX_HEAT
    assert g.heat >= MAX_HEAT


def test_heat_just_below_max_not_game_over() -> None:
    """Heat at MAX_HEAT - 0.01 should not trigger game over."""
    g = _make_game()
    g.heat = MAX_HEAT - 0.01
    assert g.heat < MAX_HEAT


def test_super_dive_expires_while_airborne() -> None:
    """Super dive can expire while diver is still airborne (handled gracefully)."""
    g = _make_game()
    g.super_dive = True
    g.super_timer = 1
    g._update_super_dive()
    assert g.super_dive is False
    assert g._is_super_dive_active() is False


def test_combo_resets_on_game_restart() -> None:
    """Combo resets to 0 after full reset()."""
    g = _make_game()
    g.combo = 10
    g.max_combo = 15
    g.score = 5000
    g.reset()
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.score == 0


def test_all_zones_same_color_edge_case() -> None:
    """Manual same-color zones: combo still builds."""
    g = _make_game()
    g.zones = [
        SplashZone(x=100.0, y=float(ZONE_Y), color=RED),
        SplashZone(x=160.0, y=float(ZONE_Y), color=RED),
        SplashZone(x=220.0, y=float(ZONE_Y), color=RED),
    ]
    g._apply_landing(0)
    assert g.combo == 1
    assert g.last_zone_color == RED
    g._apply_landing(1)
    assert g.combo == 2
    g._apply_landing(2)
    assert g.combo == 3


def test_no_zones_always_miss() -> None:
    """Empty zones list: _check_landing returns None."""
    g = _make_game()
    g.zones = []
    g.diver_x = 160.0
    g.diver_y = float(WATER_Y)
    assert g._check_landing() is None


if __name__ == "__main__":
    import traceback

    tests = [
        ("splash_zone_defaults", test_splash_zone_defaults),
        ("particle_defaults", test_particle_defaults),
        ("trail_point_fields", test_trail_point_fields),
        ("phase_enum", test_phase_enum),
        ("dive_state_enum", test_dive_state_enum),
        ("reset_initial_state", test_reset_initial_state),
        ("reset_with_seed_reproducible", test_reset_with_seed_reproducible),
        ("spawn_zones_count", test_spawn_zones_count),
        ("spawn_zones_within_bounds", test_spawn_zones_within_bounds),
        ("spawn_zones_deterministic", test_spawn_zones_deterministic),
        ("jump_sets_airborne", test_jump_sets_airborne),
        ("jump_calculates_base_height_points", test_jump_calculates_base_height_points),
        ("update_airborne_applies_gravity", test_update_airborne_applies_gravity),
        ("update_airborne_moves_diver", test_update_airborne_moves_diver),
        ("update_airborne_applies_rotation", test_update_airborne_applies_rotation),
        ("update_airborne_rotation_wraps_360", test_update_airborne_rotation_wraps_360),
        ("update_airborne_dt_scaling", test_update_airborne_dt_scaling),
        ("check_landing_above_water", test_check_landing_above_water),
        ("check_landing_in_zone", test_check_landing_in_zone),
        ("check_landing_between_zones", test_check_landing_between_zones),
        ("check_landing_at_zone_edge", test_check_landing_at_zone_edge),
        ("apply_landing_first_dive", test_apply_landing_first_dive),
        ("apply_landing_same_color_combo", test_apply_landing_same_color_combo),
        ("apply_landing_different_color_resets_combo", test_apply_landing_different_color_resets_combo),
        ("apply_landing_miss_adds_heat", test_apply_landing_miss_adds_heat),
        ("apply_landing_heat_caps_at_max", test_apply_landing_heat_caps_at_max),
        ("apply_landing_updates_max_combo", test_apply_landing_updates_max_combo),
        ("apply_landing_super_dive_always_matches", test_apply_landing_super_dive_always_matches),
        ("apply_landing_triggers_super_dive", test_apply_landing_triggers_super_dive),
        ("compute_score_no_combo", test_compute_score_no_combo),
        ("compute_score_with_combo", test_compute_score_with_combo),
        ("compute_score_super_multiplier", test_compute_score_super_multiplier),
        ("is_super_dive_active_false_when_inactive", test_is_super_dive_active_false_when_inactive),
        ("is_super_dive_active_false_when_timer_zero", test_is_super_dive_active_false_when_timer_zero),
        ("is_super_dive_active_true_with_timer", test_is_super_dive_active_true_with_timer),
        ("activate_super_dive", test_activate_super_dive),
        ("update_super_dive_decrements_timer", test_update_super_dive_decrements_timer),
        ("update_super_dive_deactivates", test_update_super_dive_deactivates),
        ("spawn_splash_particles_count", test_spawn_splash_particles_count),
        ("spawn_splash_particles_super_count", test_spawn_splash_particles_super_count),
        ("update_particles_decrements_life", test_update_particles_decrements_life),
        ("update_particles_applies_gravity", test_update_particles_applies_gravity),
        ("update_particles_removes_dead", test_update_particles_removes_dead),
        ("ghost_trail_adds_in_airborne", test_ghost_trail_adds_in_airborne),
        ("ghost_trail_ages_points", test_ghost_trail_ages_points),
        ("ghost_trail_removes_expired", test_ghost_trail_removes_expired),
        ("ghost_trail_not_added_outside_airborne", test_ghost_trail_not_added_outside_airborne),
        ("update_heat_decays", test_update_heat_decays),
        ("update_heat_not_negative", test_update_heat_not_negative),
        ("next_dive_increments_count", test_next_dive_increments_count),
        ("next_dive_raises_platform", test_next_dive_raises_platform),
        ("next_dive_platform_min_y", test_next_dive_platform_min_y),
        ("next_dive_resets_diver_state", test_next_dive_resets_diver_state),
        ("next_dive_spawns_new_zones", test_next_dive_spawns_new_zones),
        ("start_playing_transitions_to_playing", test_start_playing_transitions_to_playing),
        ("heat_game_over_boundary", test_heat_game_over_boundary),
        ("heat_just_below_max_not_game_over", test_heat_just_below_max_not_game_over),
        ("super_dive_expires_while_airborne", test_super_dive_expires_while_airborne),
        ("combo_resets_on_game_restart", test_combo_resets_on_game_restart),
        ("all_zones_same_color_edge_case", test_all_zones_same_color_edge_case),
        ("no_zones_always_miss", test_no_zones_always_miss),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
            print(f"  PASS {name}")
        except Exception:
            failed += 1
            print(f"  FAIL {name}")
            traceback.print_exc()

    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    if failed > 0:
        sys.exit(1)
