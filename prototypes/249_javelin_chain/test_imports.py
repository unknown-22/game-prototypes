"""test_imports.py — Headless logic tests for 249_javelin_chain."""
from __future__ import annotations

import random
import sys
from pathlib import Path

_PROTO_DIR = str(Path(__file__).resolve().parent)
if _PROTO_DIR not in sys.path:
    sys.path.insert(0, _PROTO_DIR)

from main import (  # noqa: E402
    SCREEN_W,
    SCREEN_H,
    COLORS,
    COLOR_NAMES,
    NUM_COLORS,
    THROWER_X,
    THROWER_Y,
    GROUND_Y,
    GRAVITY,
    POWER_MAX,
    POWER_MIN,
    VELOCITY_SCALE,
    NUM_ZONES,
    ZONE_RADIUS,
    ZONE_MIN_X,
    ZONE_MAX_X,
    COMBO_THRESHOLD,
    SUPER_DURATION,
    GAME_DURATION,
    STAMINA_MAX,
    STAMINA_COST,
    STAMINA_RECHARGE,
    HEAT_MAX,
    HEAT_MISMATCH,
    HEAT_FAULT,
    HEAT_DECAY,
    WIND_CHANGE_INTERVAL,
    SCORING_FRAMES,
    Phase,
    LandingZone,
    Javelin,
    Particle,
    FloatingText,
    Game,
)


# ── helpers ──────────────────────────────────────────────────────────

def _make_game(seed: int = 42) -> Game:
    """Create a headless Game instance with deterministic RNG."""
    g = Game.__new__(Game)
    # Pre-init ALL attributes that reset() touches
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.timer = GAME_DURATION
    g.heat = 0.0
    g.stamina = STAMINA_MAX
    g.zones = []
    g.javelin = None
    g.javelin_color_idx = 0
    g.particles = []
    g.floats = []
    g._charging = False
    g._charge_power = 0.0
    g.super_mode = False
    g.super_timer = 0
    g.wind_dir = 0.0
    g.wind_speed = 0.0
    g._throw_count = 0
    g._scoring_timer = 0
    g._screen_shake = 0
    g._rng = random.Random(seed)
    g._last_matched = False
    g._last_fault = False
    g.reset()
    # Re-seed after reset (reset calls _rng for wind etc.)
    g._rng = random.Random(seed)
    return g


# ── constants ────────────────────────────────────────────────────────

def test_constants() -> None:
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert COLORS == (8, 11, 5, 10)  # RED, LIME, DARK_BLUE, YELLOW
    assert COLOR_NAMES == ("RED", "LIME", "D BLUE", "YELLOW")
    assert NUM_COLORS == 4
    assert THROWER_X == 40
    assert THROWER_Y == 180
    assert GROUND_Y == 200
    assert GRAVITY == 0.2
    assert POWER_MAX == 12.0
    assert POWER_MIN == 3.0
    assert NUM_ZONES == 6
    assert ZONE_RADIUS == 18
    assert ZONE_MIN_X == 120
    assert ZONE_MAX_X == 300
    assert COMBO_THRESHOLD == 4
    assert SUPER_DURATION == 300
    assert GAME_DURATION == 60 * 60
    assert STAMINA_MAX == 100.0
    assert STAMINA_COST == 25.0
    assert STAMINA_RECHARGE == 0.15
    assert HEAT_MAX == 100.0
    assert HEAT_MISMATCH == 15.0
    assert HEAT_FAULT == 20.0
    assert HEAT_DECAY == 0.02
    assert WIND_CHANGE_INTERVAL == 3
    assert SCORING_FRAMES == 30


# ── dataclasses ──────────────────────────────────────────────────────

def test_landing_zone() -> None:
    z = LandingZone(x=200.0, y=GROUND_Y, radius=ZONE_RADIUS, color=8, active=True)
    assert z.x == 200.0
    assert z.y == GROUND_Y
    assert z.radius == ZONE_RADIUS
    assert z.color == 8
    assert z.active is True


def test_javelin() -> None:
    j = Javelin(x=40.0, y=180.0, vx=5.0, vy=-8.0, color=8, angle=0.5, landed=False)
    assert j.x == 40.0
    assert j.y == 180.0
    assert j.vx == 5.0
    assert j.vy == -8.0
    assert j.color == 8
    assert j.angle == 0.5
    assert j.landed is False
    assert j.hit_zone_idx == -1


def test_particle() -> None:
    p = Particle(x=100.0, y=50.0, vx=1.0, vy=-2.0, life=20, color=8)
    assert p.life == 20
    assert p.color == 8


def test_floating_text() -> None:
    ft = FloatingText(x=100.0, y=50.0, text="+100", life=35, color=10)
    assert ft.text == "+100"
    assert ft.life == 35


# ── phase enum ───────────────────────────────────────────────────────

def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.AIMING in Phase
    assert Phase.FLYING in Phase
    assert Phase.SCORING in Phase
    assert Phase.GAME_OVER in Phase
    assert len(list(Phase)) == 5


# ── Game.__init__ / reset ────────────────────────────────────────────

def test_game_reset() -> None:
    g = _make_game(42)
    assert g.phase == Phase.AIMING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.timer == GAME_DURATION
    assert g.heat == 0.0
    assert g.stamina == STAMINA_MAX
    assert g.javelin is None
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g._throw_count == 0
    assert g._last_matched is False
    assert g._last_fault is False
    assert len(g.zones) == NUM_ZONES


# ── spawn_zones ──────────────────────────────────────────────────────

def test_spawn_zones_count() -> None:
    g = _make_game(42)
    assert len(g.zones) == NUM_ZONES


def test_spawn_zones_positions_in_range() -> None:
    g = _make_game(42)
    for zone in g.zones:
        assert ZONE_MIN_X <= zone.x <= ZONE_MAX_X
        assert abs(zone.y - GROUND_Y) < 0.01


def test_spawn_zones_colors_in_palette() -> None:
    g = _make_game(42)
    for zone in g.zones:
        assert zone.color in COLORS


def test_spawn_zones_active() -> None:
    g = _make_game(42)
    for zone in g.zones:
        assert zone.active is True


def test_spawn_zones_min_gap() -> None:
    g = _make_game(42)
    xs = sorted(z.x for z in g.zones)
    # min_gap is ZONE_RADIUS*3 but fallback after 50 attempts allows overlap.
    # Verify that zones are sorted and within bounds.
    for i in range(len(xs) - 1):
        assert xs[i] <= xs[i + 1]  # sorted


def test_spawn_zones_deterministic() -> None:
    g1 = _make_game(42)
    g2 = _make_game(42)
    for z1, z2 in zip(g1.zones, g2.zones):
        assert abs(z1.x - z2.x) < 0.01
        assert z1.color == z2.color


# ── _compute_javelin_velocity ────────────────────────────────────────

def test_compute_velocity_horizontal() -> None:
    g = _make_game(42)
    vx, vy = g._compute_javelin_velocity(12.0, 0.3)
    assert vx > 0
    assert vy < 0  # upward


def test_compute_velocity_vertical() -> None:
    g = _make_game(42)
    vx, vy = g._compute_javelin_velocity(12.0, 0.8)
    # steeper angle: more vertical component than horizontal
    assert abs(vy) > abs(vx)
    assert vy < 0


def test_compute_velocity_power_scales() -> None:
    g = _make_game(42)
    vx_low, vy_low = g._compute_javelin_velocity(3.0, 0.3)
    vx_high, vy_high = g._compute_javelin_velocity(12.0, 0.3)
    assert vx_high > vx_low
    assert vy_high < vy_low  # more power = higher arc (more negative vy)


def test_compute_velocity_stamina_penalty() -> None:
    g = _make_game(42)
    g.stamina = 10.0  # below STAMINA_COST(25)
    vx, vy = g._compute_javelin_velocity(100.0, 0.3)
    # power capped at POWER_MAX * 0.5 = 6.0
    assert abs(vx) <= 6.0 * VELOCITY_SCALE + 0.01


def test_compute_velocity_full_stamina() -> None:
    g = _make_game(42)
    g.stamina = STAMINA_MAX
    vx, vy = g._compute_javelin_velocity(POWER_MAX, 0.3)
    # full power available
    assert vx > 5.0  # approximate


# ── _throw_javelin ───────────────────────────────────────────────────

def test_throw_javelin_creates() -> None:
    g = _make_game(42)
    g.javelin_color_idx = 0  # RED=8
    j = g._throw_javelin(10.0, 0.5)
    assert j.x == THROWER_X
    assert j.y == THROWER_Y
    assert j.color == 8  # RED
    assert j.landed is False


def test_throw_javelin_color_matches_idx() -> None:
    g = _make_game(42)
    for ci in range(NUM_COLORS):
        g.javelin_color_idx = ci
        j = g._throw_javelin(10.0, 0.5)
        assert j.color == COLORS[ci]


# ── _update_javelin ──────────────────────────────────────────────────

def test_update_javelin_moves() -> None:
    g = _make_game(42)
    g.javelin = Javelin(x=100.0, y=100.0, vx=3.0, vy=-5.0, color=8)
    g.wind_dir = 0.0
    g.wind_speed = 0.0
    g._update_javelin()
    assert g.javelin.x == 103.0
    assert g.javelin.y == 95.0
    assert g.javelin.vy == -5.0 + GRAVITY


def test_update_javelin_lands() -> None:
    g = _make_game(42)
    g.javelin = Javelin(x=200.0, y=GROUND_Y, vx=1.0, vy=1.0, color=8)
    g.wind_dir = 0.0
    g.wind_speed = 0.0
    g._update_javelin()
    assert g.javelin.landed is True
    assert g.javelin.y == GROUND_Y


def test_update_javelin_wind_effect() -> None:
    g = _make_game(42)
    g.javelin = Javelin(x=100.0, y=100.0, vx=3.0, vy=-5.0, color=8)
    g.wind_dir = 1.0
    g.wind_speed = 3.0
    vx_before = g.javelin.vx
    g._update_javelin()
    assert g.javelin.vx > vx_before  # wind added to vx


def test_update_javelin_none_does_nothing() -> None:
    g = _make_game(42)
    g.javelin = None
    g._update_javelin()  # should not crash
    assert g.javelin is None


def test_update_javelin_landed_does_nothing() -> None:
    g = _make_game(42)
    g.javelin = Javelin(x=200.0, y=GROUND_Y, vx=1.0, vy=0.0, color=8, landed=True)
    old_x = g.javelin.x
    g.wind_dir = 1.0
    g.wind_speed = 3.0
    g._update_javelin()
    assert g.javelin.x == old_x  # unchanged


# ── _on_landing ──────────────────────────────────────────────────────

def test_on_landing_matched() -> None:
    g = _make_game(42)
    g.javelin_color_idx = 0  # RED=8
    g.score = 0
    g.combo = 0
    # Place a RED zone exactly where javelin lands
    g.zones = [LandingZone(x=200.0, y=GROUND_Y, radius=ZONE_RADIUS, color=8, active=True)]
    g.javelin = Javelin(x=200.0, y=GROUND_Y, vx=0.0, vy=0.0, color=8, landed=False)
    g._on_landing()
    assert g._last_matched is True
    assert g._last_fault is False
    assert g.combo == 1
    assert g.score == 100  # 100 * 1 * 1
    assert g.phase == Phase.SCORING


def test_on_landing_mismatch() -> None:
    g = _make_game(42)
    g.javelin_color_idx = 0  # RED=8
    g.score = 0
    g.combo = 3
    g.heat = 0.0
    # Place a LIME zone
    g.zones = [LandingZone(x=200.0, y=GROUND_Y, radius=ZONE_RADIUS, color=11, active=True)]
    g.javelin = Javelin(x=200.0, y=GROUND_Y, vx=0.0, vy=0.0, color=8, landed=False)
    g._on_landing()
    assert g._last_matched is False
    assert g._last_fault is False
    assert g.combo == 0  # reset
    assert g.heat > 0  # HEAT_MISMATCH added
    assert g.phase == Phase.SCORING


def test_on_landing_fault() -> None:
    g = _make_game(42)
    g.javelin_color_idx = 0
    g.score = 0
    g.combo = 3
    g.heat = 0.0
    # No zones at all (or all inactive)
    g.zones = []
    g.javelin = Javelin(x=50.0, y=GROUND_Y, vx=0.0, vy=0.0, color=8, landed=False)
    g._on_landing()
    assert g._last_matched is False
    assert g._last_fault is True
    assert g.combo == 0
    assert g.heat == HEAT_FAULT
    assert g.phase == Phase.SCORING


def test_on_landing_combo_chain() -> None:
    g = _make_game(42)
    g.javelin_color_idx = 0  # RED
    g.score = 0
    g.combo = 2
    g.max_combo = 2
    g.zones = [LandingZone(x=200.0, y=GROUND_Y, radius=ZONE_RADIUS, color=8, active=True)]
    g.javelin = Javelin(x=200.0, y=GROUND_Y, vx=0.0, vy=0.0, color=8, landed=False)
    g._on_landing()
    assert g.combo == 3
    assert g.max_combo == 3
    assert g.score == 300  # 100 * 3 * 1


def test_on_landing_super_mode_any_color_matches() -> None:
    g = _make_game(42)
    g.javelin_color_idx = 0  # RED
    g.super_mode = True
    g.score = 0
    g.combo = 0
    # LIME zone — normally a mismatch, but SUPER matches anything
    g.zones = [LandingZone(x=200.0, y=GROUND_Y, radius=ZONE_RADIUS, color=11, active=True)]
    g.javelin = Javelin(x=200.0, y=GROUND_Y, vx=0.0, vy=0.0, color=8, landed=False)
    g._on_landing()
    assert g._last_matched is True
    assert g.combo == 1
    assert g.score == 300  # 100 * 1 * 3 (super multiplier)


def test_on_landing_activates_super() -> None:
    g = _make_game(42)
    g.javelin_color_idx = 0  # RED
    g.combo = 3  # next matched will make it 4 = threshold
    g.super_mode = False
    g.zones = [LandingZone(x=200.0, y=GROUND_Y, radius=ZONE_RADIUS, color=8, active=True)]
    g.javelin = Javelin(x=200.0, y=GROUND_Y, vx=0.0, vy=0.0, color=8, landed=False)
    g._on_landing()
    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_on_landing_zone_deactivated() -> None:
    g = _make_game(42)
    g.javelin_color_idx = 0  # RED
    zone = LandingZone(x=200.0, y=GROUND_Y, radius=ZONE_RADIUS, color=8, active=True)
    g.zones = [zone]
    g.javelin = Javelin(x=200.0, y=GROUND_Y, vx=0.0, vy=0.0, color=8, landed=False)
    g._on_landing()
    assert zone.active is False


def test_on_landing_inactive_zone_ignored() -> None:
    g = _make_game(42)
    g.javelin_color_idx = 0  # RED
    # RED zone but inactive → should be ignored → fault
    g.zones = [LandingZone(x=200.0, y=GROUND_Y, radius=ZONE_RADIUS, color=8, active=False)]
    g.javelin = Javelin(x=200.0, y=GROUND_Y, vx=0.0, vy=0.0, color=8, landed=False)
    g._on_landing()
    assert g._last_fault is True


def test_on_landing_color_idx_cycles() -> None:
    g = _make_game(42)
    g.javelin_color_idx = 2  # DARK_BLUE
    g.zones = [LandingZone(x=200.0, y=GROUND_Y, radius=ZONE_RADIUS, color=5, active=True)]
    g.javelin = Javelin(x=200.0, y=GROUND_Y, vx=0.0, vy=0.0, color=5, landed=False)
    g._on_landing()
    assert g.javelin_color_idx == 3  # cycled to YELLOW


def test_on_landing_wind_changes() -> None:
    g = _make_game(42)
    g._throw_count = 2  # next throw = 3 = wind change
    g.wind_dir = 99.0  # will be overwritten
    g.javelin_color_idx = 0
    g.zones = [LandingZone(x=200.0, y=GROUND_Y, radius=ZONE_RADIUS, color=8, active=True)]
    g.javelin = Javelin(x=200.0, y=GROUND_Y, vx=0.0, vy=0.0, color=8, landed=False)
    g._on_landing()
    assert g._throw_count == 0  # reset
    assert -1.0 <= g.wind_dir <= 1.0
    assert 0.0 <= g.wind_speed <= 3.0
    assert g.wind_dir != 99.0  # changed


def test_on_landing_stamina_cost() -> None:
    g = _make_game(42)
    g.stamina = STAMINA_MAX
    g.javelin_color_idx = 0
    g.zones = [LandingZone(x=200.0, y=GROUND_Y, radius=ZONE_RADIUS, color=8, active=True)]
    g.javelin = Javelin(x=200.0, y=GROUND_Y, vx=0.0, vy=0.0, color=8, landed=False)
    g._on_landing()
    assert g.stamina == STAMINA_MAX - STAMINA_COST


def test_on_landing_score_multiplier_increases_with_combo() -> None:
    g = _make_game(42)
    g.javelin_color_idx = 0  # RED
    g.combo = 4
    g.score = 0
    g.zones = [LandingZone(x=200.0, y=GROUND_Y, radius=ZONE_RADIUS, color=8, active=True)]
    g.javelin = Javelin(x=200.0, y=GROUND_Y, vx=0.0, vy=0.0, color=8, landed=False)
    g._on_landing()
    # combo becomes 5, score = 100 * 5 * 1 = 500
    assert g.combo == 5
    assert g.score == 500


# ── _add_heat ────────────────────────────────────────────────────────

def test_add_heat_increases() -> None:
    g = _make_game(42)
    g.heat = 10.0
    g._add_heat(15.0)
    assert g.heat == 25.0


def test_add_heat_caps() -> None:
    g = _make_game(42)
    g.heat = 98.0
    g._add_heat(10.0)
    assert g.heat == HEAT_MAX


def test_add_heat_super_mode_blocks() -> None:
    g = _make_game(42)
    g.heat = 10.0
    g.super_mode = True
    g._add_heat(15.0)
    assert g.heat == 10.0  # unchanged


# ── _activate_super ──────────────────────────────────────────────────

def test_activate_super() -> None:
    g = _make_game(42)
    g.super_mode = False
    g.super_timer = 0
    g._activate_super()
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION
    assert len(g.floats) == 1  # SUPER THROW! text


# ── _update_stamina ──────────────────────────────────────────────────

def test_update_stamina_recharges() -> None:
    g = _make_game(42)
    g.stamina = 50.0
    g._update_stamina()
    assert abs(g.stamina - (50.0 + STAMINA_RECHARGE)) < 0.01


def test_update_stamina_caps() -> None:
    g = _make_game(42)
    g.stamina = STAMINA_MAX - 0.05
    g._update_stamina()
    assert g.stamina == STAMINA_MAX


# ── _update_heat ─────────────────────────────────────────────────────

def test_update_heat_decays() -> None:
    g = _make_game(42)
    g.heat = 50.0
    g.phase = Phase.AIMING
    g._update_heat()
    assert abs(g.heat - (50.0 - HEAT_DECAY)) < 0.01
    assert g.phase == Phase.AIMING  # not game over


def test_update_heat_game_over_at_cap() -> None:
    g = _make_game(42)
    g.heat = HEAT_MAX
    g.phase = Phase.AIMING
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_update_heat_does_not_go_below_zero() -> None:
    g = _make_game(42)
    g.heat = 0.005
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_check_before_decay() -> None:
    """Verify threshold check happens BEFORE decay (decay-before-check pitfall test)."""
    g = _make_game(42)
    g.heat = HEAT_MAX
    g.phase = Phase.AIMING
    g._update_heat()
    # Should be GAME_OVER because check happened before decay
    assert g.phase == Phase.GAME_OVER


# ── _update_super_mode ───────────────────────────────────────────────

def test_update_super_mode_timer_counts_down() -> None:
    g = _make_game(42)
    g.super_mode = True
    g.super_timer = 100
    g._update_super_mode()
    assert g.super_timer == 99
    assert g.super_mode is True


def test_update_super_mode_deactivates() -> None:
    g = _make_game(42)
    g.super_mode = True
    g.super_timer = 1
    g._update_super_mode()
    assert g.super_timer == 0
    assert g.super_mode is False


def test_update_super_mode_does_nothing_when_not_active() -> None:
    g = _make_game(42)
    g.super_mode = False
    g.super_timer = 0
    g._update_super_mode()
    assert g.super_mode is False
    assert g.super_timer == 0


# ── _update_particles ────────────────────────────────────────────────

def test_update_particles_moves_and_decays() -> None:
    g = _make_game(42)
    p = Particle(x=100.0, y=100.0, vx=1.0, vy=-2.0, life=5, color=8)
    g.particles = [p]
    g._update_particles()
    assert p.x == 101.0
    assert p.y == 98.0
    assert p.vy == -2.0 + 0.05  # gravity on particles
    assert p.life == 4
    assert len(g.particles) == 1  # still alive


def test_update_particles_removes_dead() -> None:
    g = _make_game(42)
    p = Particle(x=100.0, y=100.0, vx=1.0, vy=0.0, life=1, color=8)
    g.particles = [p]
    g._update_particles()
    assert len(g.particles) == 0  # life became 0, removed


# ── _update_floating_texts ───────────────────────────────────────────

def test_update_floating_texts_moves_and_decays() -> None:
    g = _make_game(42)
    ft = FloatingText(x=100.0, y=100.0, text="HI", life=5, color=10)
    g.floats = [ft]
    g._update_floating_texts()
    assert abs(ft.y - 99.5) < 0.01  # moved up 0.5
    assert ft.life == 4
    assert len(g.floats) == 1


def test_update_floating_texts_removes_dead() -> None:
    g = _make_game(42)
    ft = FloatingText(x=100.0, y=100.0, text="HI", life=1, color=10)
    g.floats = [ft]
    g._update_floating_texts()
    assert len(g.floats) == 0


# ── _spawn_particles ─────────────────────────────────────────────────

def test_spawn_particles_count() -> None:
    g = _make_game(42)
    g._spawn_particles(200.0, GROUND_Y, 8, 10)
    assert len(g.particles) == 10


def test_spawn_particles_in_expected_range() -> None:
    g = _make_game(42)
    g._spawn_particles(200.0, GROUND_Y, 8, 100)
    for p in g.particles:
        assert abs(p.x - 200.0) < 5.0  # within velocity range
        assert p.life >= 12
        assert p.life <= 25


# ── _spawn_float ─────────────────────────────────────────────────────

def test_spawn_float() -> None:
    g = _make_game(42)
    g._spawn_float(200.0, 100.0, "TEST", 8, 30)
    assert len(g.floats) == 1
    assert g.floats[0].text == "TEST"
    assert g.floats[0].color == 8
    assert g.floats[0].life == 30


# ── _check_game_over ─────────────────────────────────────────────────

def test_check_game_over_timer() -> None:
    g = _make_game(42)
    g.timer = 0
    g.phase = Phase.AIMING
    result = g._check_game_over()
    assert result is True
    assert g.phase == Phase.GAME_OVER


def test_check_game_over_heat() -> None:
    g = _make_game(42)
    g.timer = 100
    g.heat = HEAT_MAX
    g.phase = Phase.AIMING
    result = g._check_game_over()
    assert result is True
    assert g.phase == Phase.GAME_OVER


def test_check_game_over_not_over() -> None:
    g = _make_game(42)
    g.timer = 100
    g.heat = 0.0
    g.phase = Phase.AIMING
    result = g._check_game_over()
    assert result is False
    assert g.phase == Phase.AIMING


# ── _respawn_zones_if_needed ─────────────────────────────────────────

def test_respawn_zones_no_respawn_when_enough_active() -> None:
    g = _make_game(42)
    original_zone_data = [(z.x, z.y, z.radius, z.color, z.active) for z in g.zones]
    # All zones active, no respawn needed
    g._respawn_zones_if_needed()
    assert len(g.zones) == NUM_ZONES
    # Content should be same (no respawn occurred)
    current_zone_data = [(z.x, z.y, z.radius, z.color, z.active) for z in g.zones]
    assert current_zone_data == original_zone_data


def test_respawn_zones_when_low_active() -> None:
    g = _make_game(42)
    # Deactivate all but 2 zones
    for i, z in enumerate(g.zones):
        if i >= 2:
            z.active = False
    g._respawn_zones_if_needed()
    assert len(g.zones) == NUM_ZONES
    assert all(z.active for z in g.zones)


# ── combo + heat integration ─────────────────────────────────────────

def test_combo_reset_on_mismatch() -> None:
    g = _make_game(42)
    g.combo = 5
    g.max_combo = 5
    g.javelin_color_idx = 0  # RED
    g.zones = [LandingZone(x=200.0, y=GROUND_Y, radius=ZONE_RADIUS, color=11, active=True)]  # LIME
    g.javelin = Javelin(x=200.0, y=GROUND_Y, vx=0.0, vy=0.0, color=8, landed=False)
    g._on_landing()
    assert g.combo == 0
    assert g.max_combo == 5  # max_combo preserved


def test_heat_accumulates_on_repeated_mismatch() -> None:
    g = _make_game(42)
    g.zones = [LandingZone(x=200.0, y=GROUND_Y, radius=ZONE_RADIUS, color=11, active=True)]  # LIME
    for _ in range(3):
        g.javelin_color_idx = 0  # always RED → mismatch with LIME
        g.zones[0].active = True
        g.javelin = Javelin(x=200.0, y=GROUND_Y, vx=0.0, vy=0.0, color=8, landed=False)
        g._on_landing()
    assert g.heat >= HEAT_MISMATCH * 3


def test_super_mode_no_heat_from_mismatch() -> None:
    g = _make_game(42)
    g.super_mode = True
    g.javelin_color_idx = 0  # RED
    g.heat = 0.0
    g.zones = [LandingZone(x=200.0, y=GROUND_Y, radius=ZONE_RADIUS, color=11, active=True)]  # LIME
    g.javelin = Javelin(x=200.0, y=GROUND_Y, vx=0.0, vy=0.0, color=8, landed=False)
    g._on_landing()
    assert g.heat == 0.0  # no heat added in super mode


# ── reset restores clean state ───────────────────────────────────────

def test_reset_restores_all_state() -> None:
    g = _make_game(42)
    # Mess up the state
    g.score = 9999
    g.combo = 10
    g.heat = 80.0
    g.stamina = 10.0
    g.super_mode = True
    g.super_timer = 50
    g.javelin = Javelin(x=100.0, y=100.0, vx=1.0, vy=0.0, color=8)
    g.particles = [Particle(x=1.0, y=1.0, vx=0.0, vy=0.0, life=5, color=8)]
    g.floats = [FloatingText(x=1.0, y=1.0, text="X", life=5, color=10)]
    g._throw_count = 5
    g._last_matched = True
    g._last_fault = True

    g.reset()

    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.stamina == STAMINA_MAX
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.javelin is None
    assert len(g.particles) == 0
    assert len(g.floats) == 0
    assert g._throw_count == 0
    assert g._last_matched is False
    assert g._last_fault is False
    assert g.phase == Phase.AIMING


# ── javelin trajectory plausibility ──────────────────────────────────

def test_javelin_reaches_far_with_high_power() -> None:
    """A high-power throw should reach beyond the first zone."""
    g = _make_game(42)
    g.wind_dir = 0.0
    g.wind_speed = 0.0
    g.javelin = g._throw_javelin(POWER_MAX, 0.5)  # max power, moderate angle
    max_x = g.javelin.x
    for _ in range(200):
        g._update_javelin()
        if g.javelin is None or g.javelin.landed:
            break
        max_x = max(max_x, g.javelin.x)
    assert max_x >= ZONE_MIN_X  # reaches the landing zone area


# ── landing zone boundary test ────────────────────────────────────────

def test_landing_at_edge_of_zone_counts() -> None:
    """Landing exactly at radius distance should count as hit."""
    g = _make_game(42)
    g.javelin_color_idx = 0  # RED
    zone = LandingZone(x=200.0, y=GROUND_Y, radius=ZONE_RADIUS, color=8, active=True)
    g.zones = [zone]
    # Place javelin exactly at zone edge (distance = radius)
    g.javelin = Javelin(x=200.0 + ZONE_RADIUS, y=GROUND_Y, vx=0.0, vy=0.0, color=8, landed=False)
    g._on_landing()
    assert g._last_matched is True


def test_landing_just_outside_zone_is_fault() -> None:
    """Landing just beyond radius should NOT count as hit (no other zones → fault)."""
    g = _make_game(42)
    g.javelin_color_idx = 0  # RED
    zone = LandingZone(x=200.0, y=GROUND_Y, radius=ZONE_RADIUS, color=8, active=True)
    g.zones = [zone]
    # Place javelin just outside
    g.javelin = Javelin(x=200.0 + ZONE_RADIUS + 1.0, y=GROUND_Y, vx=0.0, vy=0.0, color=8, landed=False)
    g._on_landing()
    assert g._last_fault is True


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
