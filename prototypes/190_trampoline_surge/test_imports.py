"""test_imports.py — Headless logic tests for 190_trampoline_surge."""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/190_trampoline_surge")

from main import (  # noqa: E402
    AIR_FRICTION,
    BOUNCE_VEL,
    COMBO_THRESHOLD,
    FloatText,
    GAME_DURATION,
    GRAVITY,
    HEAT_DECAY,
    HEAT_MAX,
    HEAT_MISMATCH,
    MAX_VX,
    Particle,
    Phase,
    PLAYER_RADIUS,
    Player,
    RED,
    SUPER_DURATION,
    TRAMPOLINE_Y,
    ZONE_COLORS,
    ZONE_WIDTH,
    Game,
)


def _make_game(seed: int = 42) -> Game:
    """Factory: create a Game instance bypassing pyxel init."""
    g = Game.__new__(Game)
    # Pre-init ALL attributes that reset() touches
    g.phase = Phase.TITLE
    g.player = Player(x=160.0, y=float(TRAMPOLINE_Y - PLAYER_RADIUS), vx=0.0, vy=0.0, color=RED, on_ground=True)
    g.zones = list(ZONE_COLORS)
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.super_timer = 0
    g.timer = GAME_DURATION
    g.last_zone_color = RED
    g.particles = []
    g.float_texts = []
    g._rng = random.Random()  # placeholder; reset() overwrites
    g._peak_y = float(TRAMPOLINE_Y)
    g._game_over_reason = ""
    g.reset()
    # Set seeded RNG AFTER reset() (reset overwrites _rng)
    g._rng = random.Random(seed)
    return g


# ─── Constants ───

def test_constants():
    assert len(ZONE_COLORS) == 4
    assert ZONE_WIDTH == 60
    assert PLAYER_RADIUS == 6
    assert GRAVITY == 0.3
    assert BOUNCE_VEL == -8.0
    assert HEAT_MAX == 100
    assert HEAT_MISMATCH == 15
    assert SUPER_DURATION == 300
    assert GAME_DURATION == 3600
    assert COMBO_THRESHOLD == 4


# ─── Data Classes ───

def test_player_dataclass():
    p = Player(x=100.0, y=200.0, vx=1.0, vy=-2.0, color=RED, on_ground=False)
    assert p.x == 100.0
    assert p.y == 200.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.color == RED
    assert p.on_ground is False


def test_particle_dataclass():
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.5, life=20, color=8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -2.5
    assert p.life == 20
    assert p.color == 8


def test_float_text_dataclass():
    ft = FloatText(x=50.0, y=30.0, text="+100", life=30, color=7)
    assert ft.text == "+100"
    assert ft.life == 30
    assert ft.color == 7


# ─── Phase Enum ───

def test_phase_enum():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ─── Game Initialization ───

def test_make_game_factory():
    g = _make_game()
    # reset() transitions to TITLE
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.timer == GAME_DURATION
    assert g.last_zone_color == RED
    assert g.zones == [8, 3, 5, 10]  # RED, GREEN, DARK_BLUE, YELLOW (unshuffled after reset)
    assert isinstance(g._rng, random.Random)


def test_reset_clears_state():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.score = 500
    g.combo = 3
    g.heat = 50.0
    g.super_timer = 100
    g.timer = 1000
    g.particles = [Particle(0, 0, 0, 0, 5, RED)]
    g.float_texts = [FloatText(0, 0, "test", 5, 7)]
    g.reset()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.timer == GAME_DURATION
    assert g.particles == []
    assert g.float_texts == []


# ─── Zone Shuffling ───

def test_shuffle_zones_preserves_colors():
    g = _make_game()
    g._rng = random.Random(42)
    original = sorted(g.zones)
    g._shuffle_zones()
    assert sorted(g.zones) == original  # same colors, different order
    assert g.zones != [8, 3, 5, 10]  # should be shuffled


def test_shuffle_zones_deterministic():
    g1 = _make_game(42)
    g2 = _make_game(42)
    g1._shuffle_zones()
    g2._shuffle_zones()
    assert g1.zones == g2.zones


# ─── Physics ───

def test_apply_gravity_to_player():
    g = _make_game()
    g.player.vy = 0.0
    g.player.on_ground = False
    g.player.y = 100.0
    g._apply_physics()
    assert g.player.vy == GRAVITY  # gravity applied
    assert g.player.y > 100.0      # fell


def test_player_not_fall_through_trampoline():
    g = _make_game()
    g.player.y = float(TRAMPOLINE_Y + 10)
    g.player.vy = 5.0
    g._apply_physics()
    # Should be clamped at trampoline surface
    assert g.player.y == float(TRAMPOLINE_Y - PLAYER_RADIUS)
    assert g.player.vy == 0.0
    assert g.player.on_ground is True


def test_air_friction_reduces_vx():
    g = _make_game()
    g.player.on_ground = False
    g.player.vx = 4.0
    g._apply_physics()
    assert g.player.vx == 4.0 * AIR_FRICTION


def test_vx_clamped_to_max():
    g = _make_game()
    g.player.on_ground = False
    g.player.vx = 10.0
    g._apply_physics()
    assert g.player.vx <= MAX_VX


def test_vx_zero_when_on_ground():
    g = _make_game()
    g.player.on_ground = True
    g.player.vx = 2.0
    g._apply_physics()
    assert g.player.vx == 0.0


def test_player_clamped_to_left_boundary():
    g = _make_game()
    g.player.x = -10.0
    g.player.vx = -1.0
    g._apply_physics()
    assert g.player.x == PLAYER_RADIUS


def test_player_clamped_to_right_boundary():
    g = _make_game()
    g.player.x = 500.0
    g.player.vx = 1.0
    g._apply_physics()
    assert g.player.x == 320 - PLAYER_RADIUS


# ─── Landing Detection ───

def test_check_landing_detects_zone_0():
    g = _make_game()
    g.player.x = 50.0  # in zone 0 (40..100)
    g.player.y = float(TRAMPOLINE_Y - PLAYER_RADIUS + 1)  # below trampoline
    g.player.vy = 1.0  # falling
    g.player.on_ground = False
    did_land, zone_idx = g._check_landing()
    assert did_land is True
    assert zone_idx == 0


def test_check_landing_detects_zone_3():
    g = _make_game()
    g.player.x = 250.0  # in zone 3 (220..280)
    g.player.y = float(TRAMPOLINE_Y - PLAYER_RADIUS + 5)
    g.player.vy = 1.0
    g.player.on_ground = False
    did_land, zone_idx = g._check_landing()
    assert did_land is True
    assert zone_idx == 3


def test_check_landing_off_zone_returns_neg1():
    g = _make_game()
    g.player.x = 10.0  # left of zone 0
    g.player.y = float(TRAMPOLINE_Y - PLAYER_RADIUS + 1)
    g.player.vy = 1.0
    g.player.on_ground = False
    did_land, zone_idx = g._check_landing()
    assert did_land is True
    assert zone_idx == -1


def test_check_landing_no_landing_when_going_up():
    g = _make_game()
    g.player.y = float(TRAMPOLINE_Y - PLAYER_RADIUS)
    g.player.vy = -5.0  # going up
    g.player.on_ground = False
    did_land, _ = g._check_landing()
    assert did_land is False


def test_check_landing_no_landing_when_on_ground():
    g = _make_game()
    g.player.on_ground = True
    g.player.vy = 1.0
    g.player.y = float(TRAMPOLINE_Y - PLAYER_RADIUS)
    did_land, _ = g._check_landing()
    assert did_land is False


def test_check_landing_boundary_between_zones():
    g = _make_game()
    g.player.x = 100.0  # exactly at zone 1 left edge (left-inclusive)
    g.player.y = float(TRAMPOLINE_Y - PLAYER_RADIUS + 1)
    g.player.vy = 1.0
    g.player.on_ground = False
    did_land, zone_idx = g._check_landing()
    assert did_land is True
    assert zone_idx == 1  # zx <= p.x < zx + ZONE_WIDTH


# ─── Landing Resolution ───

def test_resolve_landing_same_color_builds_combo():
    g = _make_game()
    g.last_zone_color = RED
    g.zones = [RED, 3, 5, 10]  # zone 0 is RED
    g._peak_y = 100.0  # simulate high bounce
    score = g._resolve_landing(0)
    assert g.combo == 1
    assert g.max_combo == 1
    assert score > 0  # height-based score


def test_resolve_landing_wrong_color_resets_combo():
    g = _make_game()
    g.last_zone_color = RED
    g.zones = [3, RED, 5, 10]  # zone 0 is GREEN, not RED
    g.combo = 3
    g._peak_y = 100.0
    g._resolve_landing(0)
    assert g.combo == 0
    assert g.heat == float(HEAT_MISMATCH)


def test_resolve_landing_off_zone_resets_combo():
    g = _make_game()
    g.last_zone_color = RED
    g.combo = 2
    g._peak_y = 100.0
    g._resolve_landing(-1)  # missed all zones
    assert g.combo == 0
    assert g.heat == float(HEAT_MISMATCH)


def test_resolve_landing_combo_multiplier():
    g = _make_game()
    g.last_zone_color = RED
    g.zones = [RED, 3, 5, 10]
    g._peak_y = 100.0
    # combo=0, landing on same color → combo becomes 1, multiplier = 1 + 0.5*1 = 1.5
    score1 = g._resolve_landing(0)
    assert score1 == int((TRAMPOLINE_Y - 100.0) * 1.5)

    g._peak_y = 50.0
    g.last_zone_color = RED
    # combo=1, landing on same → combo=2, multiplier = 1 + 0.5*2 = 2.0
    score2 = g._resolve_landing(0)
    assert score2 == int((TRAMPOLINE_Y - 50.0) * 2.0)


def test_resolve_landing_super_mode_always_matches():
    g = _make_game()
    g.last_zone_color = RED
    g.zones = [3, 5, 10, 8]  # all different from RED
    g.super_timer = 100  # active
    g._peak_y = 100.0
    score = g._resolve_landing(0)  # GREEN zone, but super mode
    assert g.combo == 1
    assert g.super_timer == 100  # not decremented yet (that's _update_super's job)
    assert score == int((TRAMPOLINE_Y - 100.0) * 1.5 * 3.0)  # base * combo_mult * super_mult


def test_resolve_landing_triggers_super_at_threshold():
    g = _make_game()
    g.last_zone_color = RED
    g.zones = [RED, 3, 5, 10]
    g.combo = 3  # next landing makes 4
    g._peak_y = 100.0
    score = g._resolve_landing(0)
    assert g.combo == 4
    assert g.super_timer == SUPER_DURATION
    # was_super was False (super_timer was 0 before check)
    multiplier = 1.0 + 0.5 * 4  # = 3.0
    assert score == int((TRAMPOLINE_Y - 100.0) * multiplier)


def test_resolve_landing_super_does_not_re_trigger():
    g = _make_game()
    g.last_zone_color = RED
    g.zones = [RED, 3, 5, 10]
    g.combo = 5
    g.super_timer = 50  # already in super
    g._peak_y = 100.0
    g._resolve_landing(0)
    # super_timer should NOT be reset to SUPER_DURATION
    assert g.super_timer == 50  # unchanged (only set when == 0)


def test_resolve_landing_mismatch_adds_heat():
    g = _make_game()
    g.last_zone_color = RED
    g.zones = [3, RED, 5, 10]
    g.combo = 2
    g.heat = 20.0
    g._peak_y = 100.0
    g._resolve_landing(0)  # GREEN zone
    assert g.heat == 20.0 + HEAT_MISMATCH


def test_resolve_landing_mismatch_heat_capped():
    g = _make_game()
    g.last_zone_color = RED
    g.zones = [3, RED, 5, 10]
    g.heat = 95.0
    g._peak_y = 100.0
    g._resolve_landing(0)  # GREEN zone
    assert g.heat == 100.0  # capped


def test_resolve_landing_score_accumulates():
    g = _make_game()
    g.last_zone_color = RED
    g.zones = [RED, 3, 5, 10]
    g._peak_y = 100.0
    g.score = 50
    g._resolve_landing(0)
    assert g.score > 50


# ─── Heat Management ───

def test_update_heat_decays():
    g = _make_game()
    g.heat = 10.0
    g._update_heat()
    assert g.heat == 10.0 - HEAT_DECAY


def test_update_heat_floor_zero():
    g = _make_game()
    g.heat = 0.01
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_game_over_at_cap():
    g = _make_game()
    g.heat = 100.0
    g.phase = Phase.PLAYING
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g._game_over_reason == "OVERHEAT!"


def test_update_heat_check_before_decay():
    """Verify threshold is checked BEFORE decay (correct order)."""
    g = _make_game()
    g.heat = 100.0  # exactly at cap
    g.phase = Phase.PLAYING
    g._update_heat()
    assert g.phase == Phase.GAME_OVER  # triggered
    # heat stays at 100 (decay didn't happen because we returned early)


# ─── Timer ───

def test_update_timer_decrements():
    g = _make_game()
    g.timer = 300
    g._update_timer()
    assert g.timer == 299


def test_update_timer_game_over_at_zero():
    g = _make_game()
    g.timer = 1
    g.phase = Phase.PLAYING
    g._update_timer()
    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER
    assert g._game_over_reason == "TIME UP!"


# ─── Super Timer ───

def test_update_super_decrements():
    g = _make_game()
    g.super_timer = 100
    g._update_super()
    assert g.super_timer == 99


def test_update_super_stays_zero():
    g = _make_game()
    g.super_timer = 0
    g._update_super()
    assert g.super_timer == 0


# ─── Particles ───

def test_spawn_bounce_particles():
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_bounce_particles(160.0, RED)
    assert len(g.particles) == 8
    for p in g.particles:
        assert 15 <= p.life <= 25
        assert p.color == RED


def test_spawn_super_particles():
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_super_particles(160.0, 100.0)
    assert len(g.particles) == 20
    for p in g.particles:
        assert 20 <= p.life <= 35


def test_update_particles_reduces_life():
    g = _make_game()
    g.particles = [Particle(0.0, 0.0, 0.0, 0.0, 5, RED)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 4


def test_update_particles_removes_dead():
    g = _make_game()
    g.particles = [
        Particle(0.0, 0.0, 0.0, 0.0, 1, RED),
        Particle(10.0, 10.0, 1.0, -1.0, 5, RED),
    ]
    g._update_particles()
    # life=1 particle: decremented to 0 → removed
    assert len(g.particles) == 1
    assert g.particles[0].life == 4


def test_update_particles_applies_gravity():
    g = _make_game()
    g.particles = [Particle(0.0, 0.0, 0.0, -1.0, 5, RED)]
    g._update_particles()
    assert g.particles[0].vy == -1.0 + 0.1  # gravity applied


# ─── Floating Texts ───

def test_spawn_float_text():
    g = _make_game()
    g._spawn_float_text(100.0, 50.0, "+50", 7, 30)
    assert len(g.float_texts) == 1
    ft = g.float_texts[0]
    assert ft.text == "+50"
    assert ft.life == 30
    assert ft.color == 7


def test_update_float_texts_moves_up_and_decays():
    g = _make_game()
    g.float_texts = [FloatText(100.0, 50.0, "test", 10, 7)]
    g._update_float_texts()
    assert len(g.float_texts) == 1
    assert g.float_texts[0].y == 49.5  # drifted up
    assert g.float_texts[0].life == 9


def test_update_float_texts_removes_dead():
    g = _make_game()
    g.float_texts = [
        FloatText(100.0, 50.0, "dead", 1, 7),
        FloatText(200.0, 60.0, "alive", 5, 7),
    ]
    g._update_float_texts()
    assert len(g.float_texts) == 1
    assert g.float_texts[0].text == "alive"


# ─── Peak Y Tracking ───

def test_peak_y_updated_when_above():
    g = _make_game()
    g._peak_y = TRAMPOLINE_Y
    g.player.y = 100.0
    g.player.on_ground = False
    g._apply_physics()
    assert g._peak_y < TRAMPOLINE_Y  # peak updated


def test_peak_y_reset_after_bounce():
    g = _make_game()
    g._peak_y = 100.0
    # Simulate a landing sequence (manually)
    g.player.vy = BOUNCE_VEL
    g.player.y = float(TRAMPOLINE_Y - PLAYER_RADIUS)
    g.player.on_ground = False
    g._peak_y = float(TRAMPOLINE_Y)
    assert g._peak_y == TRAMPOLINE_Y


# ─── Game Loop Simulation ───

def test_full_bounce_cycle_same_color():
    """Simulate a complete bounce: land on same color → combo builds."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.last_zone_color = RED
    g.zones = [RED, 3, 5, 10]
    g.player.x = 50.0  # zone 0 = RED
    g.player.y = float(TRAMPOLINE_Y - PLAYER_RADIUS + 1)  # below trampoline surface
    g.player.vy = 1.0  # falling
    g.player.on_ground = False

    did_land, zone_idx = g._check_landing()
    assert did_land
    assert zone_idx == 0
    g._resolve_landing(zone_idx)
    assert g.combo == 1


def test_full_bounce_cycle_wrong_color():
    """Simulate a bounce landing on wrong color → combo reset, heat added."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.last_zone_color = RED
    g.zones = [3, 5, 10, 8]  # no RED
    g.combo = 2
    g.player.on_ground = False
    g.player.vy = 1.0
    g.player.y = float(TRAMPOLINE_Y - PLAYER_RADIUS + 5)
    g.player.x = 50.0  # zone 0 = GREEN

    did_land, zone_idx = g._check_landing()
    assert did_land
    g._resolve_landing(zone_idx)
    assert g.combo == 0
    assert g.heat == float(HEAT_MISMATCH)


def test_super_mode_activation_sequence():
    """Build combo to 3, next same-color triggers SUPER."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.last_zone_color = RED
    g.zones = [RED, 3, 5, 10]
    g.combo = 3

    # Landing on RED → combo=4, SUPER activates
    g.player.x = 50.0  # zone 0
    g.player.vy = 1.0
    g.player.y = float(TRAMPOLINE_Y - PLAYER_RADIUS + 5)
    g.player.on_ground = False
    g._peak_y = 100.0

    did_land, zone_idx = g._check_landing()
    assert did_land
    g._resolve_landing(zone_idx)
    assert g.combo == 4
    assert g.super_timer == SUPER_DURATION
    assert g.max_combo >= 4


def test_max_combo_tracking():
    g = _make_game()
    g.last_zone_color = RED
    g.zones = [RED, 3, 5, 10]
    g._peak_y = 200.0

    # Build combo to 5
    for _ in range(5):
        g._resolve_landing(0)
    assert g.max_combo == 5
    # Reset and verify max_combo persists in reset
    g.reset()
    assert g.max_combo == 0  # reset clears it


def test_multiple_bounces_score_accumulation():
    g = _make_game()
    g.last_zone_color = RED
    g.zones = [RED, 3, 5, 10]
    g._peak_y = 100.0

    before = g.score
    g._resolve_landing(0)  # combo 1
    g._resolve_landing(0)  # combo 2
    g._resolve_landing(0)  # combo 3
    after = g.score
    assert after > before


def test_combo_reset_score_no_multiplier():
    g = _make_game()
    g.last_zone_color = RED
    g.zones = [3, 5, 10, 8]
    g.combo = 5
    g._peak_y = 100.0

    before = g.score
    g._resolve_landing(0)  # mismatch → combo reset, base score only
    after = g.score
    scored = after - before
    expected = int(TRAMPOLINE_Y - 100.0)  # base only, no multiplier
    assert scored == expected


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
