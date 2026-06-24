"""test_imports.py — Headless logic tests for GLIDE SURGE (155)."""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/155_glide_surge")
from main import (  # noqa: E402
    COLOR_CYCLE_FRAMES,
    COLOR_VALS,
    COMBO_FOR_SUPER,
    GRAVITY,
    GREEN,
    HEAT_PER_BIRD,
    HEAT_PER_MISMATCH,
    LIGHT_BLUE,
    MAX_HEAT,
    MAX_THERMALS,
    RED,
    SCORE_PER_RING,
    SCORE_PER_THERMAL,
    SCREEN_H,
    SCREEN_W,
    SUPER_DURATION,
    TURBULENCE_DURATION,
    WORLD_SCROLL_SPEED,
    YELLOW,
    Bird,
    Game,
    Particle,
    Phase,
    Ring,
    Thermal,
    ThermalColor,
)


def _make_game() -> Game:
    """Factory for headless Game instances with seeded RNG."""
    g = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.super_timer = 0
    g.player_x = 160.0
    g.player_y = 120.0
    g.player_color = ThermalColor.RED
    g.scroll_x = 0.0
    g.thermals = []
    g.rings = []
    g.birds = []
    g.particles = []
    g.turbulence_timer = 0
    g.screen_shake = 0
    g.game_timer = 0
    g.color_cycle_timer = COLOR_CYCLE_FRAMES
    g._rng = random.Random(42)
    g._thermal_spawn_timer = 0
    g._ring_spawn_timer = 0
    g._bird_spawn_timer = 0
    g._in_thermal_this_frame = False
    g._combo_flash_timer = 0
    g.reset()
    return g


# ── Dataclass Tests ──


def test_thermal_creation() -> None:
    t = Thermal(x=100.0, width=30, color=ThermalColor.RED)
    assert t.x == 100.0
    assert t.width == 30
    assert t.color == ThermalColor.RED


def test_ring_creation() -> None:
    r = Ring(x=50.0, y=60.0, color=ThermalColor.BLUE)
    assert r.x == 50.0
    assert r.y == 60.0
    assert r.color == ThermalColor.BLUE
    assert r.collected is False


def test_bird_creation() -> None:
    b = Bird(x=100.0, y=80.0, vx=-1.5, base_y=80.0, timer=1.0)
    assert b.x == 100.0
    assert b.y == 80.0
    assert b.vx == -1.5
    assert b.base_y == 80.0
    assert b.timer == 1.0


def test_particle_creation() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=20, color=RED)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 20
    assert p.color == RED


# ── Enum Tests ──


def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


def test_thermal_color_values() -> None:
    assert ThermalColor.RED.color_val() == COLOR_VALS[0] == 8
    assert ThermalColor.GREEN.color_val() == COLOR_VALS[1] == 3
    assert ThermalColor.BLUE.color_val() == COLOR_VALS[2] == 6
    assert ThermalColor.YELLOW.color_val() == COLOR_VALS[3] == 10


def test_thermal_color_next() -> None:
    assert ThermalColor.RED.next_color() == ThermalColor.GREEN
    assert ThermalColor.GREEN.next_color() == ThermalColor.BLUE
    assert ThermalColor.BLUE.next_color() == ThermalColor.YELLOW
    assert ThermalColor.YELLOW.next_color() == ThermalColor.RED


# ── Game Reset Tests ──


def test_make_game() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.player_x == 160.0
    assert g.player_y == 120.0
    assert g.player_color == ThermalColor.RED
    assert g.thermals == []
    assert g.rings == []
    assert g.birds == []
    assert g.particles == []
    assert g.turbulence_timer == 0
    assert g.screen_shake == 0
    assert g.game_timer == 0


# ── Player Movement Tests ──


def test_player_movement() -> None:
    g = _make_game()
    orig_x, orig_y = g.player_x, g.player_y
    g._update_player(5.0, -3.0)
    assert g.player_x == orig_x + 5.0
    assert g.player_y == orig_y - 3.0


def test_player_clamp_left() -> None:
    g = _make_game()
    g.player_x = 5.0
    g._update_player(-100.0, 0.0)
    assert g.player_x == 10.0


def test_player_clamp_right() -> None:
    g = _make_game()
    g.player_x = SCREEN_W - 5.0
    g._update_player(100.0, 0.0)
    assert g.player_x == float(SCREEN_W - 10)


def test_player_clamp_top() -> None:
    g = _make_game()
    g.player_y = 5.0
    g._update_player(0.0, -100.0)
    assert g.player_y == 10.0


def test_player_clamp_bottom() -> None:
    g = _make_game()
    from main import MOUNTAIN_H

    g.player_y = SCREEN_H - MOUNTAIN_H
    g._update_player(0.0, 100.0)
    assert g.player_y == float(SCREEN_H - MOUNTAIN_H - 5)


# ── Physics Tests ──


def test_gravity_applies() -> None:
    g = _make_game()
    orig_y = g.player_y
    g._update_physics()
    assert g.player_y == orig_y + GRAVITY


def test_gravity_not_in_super() -> None:
    g = _make_game()
    g.super_timer = 100
    orig_y = g.player_y
    g._update_physics()
    assert g.player_y == orig_y  # no gravity in super


# ── Thermal Collision Tests ──


def test_thermal_collision_detected() -> None:
    g = _make_game()
    g.player_x = 150.0
    g.player_y = 100.0
    g.thermals = [Thermal(x=140.0, width=30, color=ThermalColor.RED)]
    result = g._check_thermal_collision()
    assert result is not None
    assert result.color == ThermalColor.RED


def test_thermal_collision_missed() -> None:
    g = _make_game()
    g.player_x = 50.0
    g.player_y = 100.0
    g.thermals = [Thermal(x=140.0, width=30, color=ThermalColor.RED)]
    result = g._check_thermal_collision()
    assert result is None


def test_thermal_collision_edge_inside() -> None:
    g = _make_game()
    g.player_x = 140.0  # exactly at left edge
    g.player_y = 100.0
    g.thermals = [Thermal(x=140.0, width=30, color=ThermalColor.GREEN)]
    result = g._check_thermal_collision()
    # player_x > t.x is strict, so at x=140.0 it's not > 140
    # Check near edge
    g.player_x = 140.1
    result = g._check_thermal_collision()
    assert result is not None


# ── Thermal Entry Tests ──


def test_thermal_entry_match() -> None:
    g = _make_game()
    g.player_color = ThermalColor.RED
    g.player_x = 150.0
    g.player_y = 100.0
    thermal = Thermal(x=140.0, width=30, color=ThermalColor.RED)
    g._handle_thermal_entry(thermal)
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score == SCORE_PER_THERMAL * 1  # combo=1 → multiplier=1
    assert g.heat == 0.0
    assert len(g.particles) == 4  # match spawns 4 particles
    assert g._combo_flash_timer > 0


def test_thermal_entry_match_combo_increases() -> None:
    g = _make_game()
    g.player_color = ThermalColor.RED
    g.combo = 3
    g.max_combo = 3
    g.score = 300
    thermal = Thermal(x=140.0, width=30, color=ThermalColor.RED)
    g._handle_thermal_entry(thermal)
    assert g.combo == 4
    assert g.max_combo == 4
    # combo multiplier = 4 → score += 100 * 4
    assert g.score == 300 + SCORE_PER_THERMAL * 4


def test_thermal_entry_match_triggers_super() -> None:
    g = _make_game()
    g.player_color = ThermalColor.RED
    g.combo = COMBO_FOR_SUPER - 1  # combo = 4
    g.max_combo = COMBO_FOR_SUPER - 1
    thermal = Thermal(x=140.0, width=30, color=ThermalColor.RED)
    g._handle_thermal_entry(thermal)
    assert g.combo == COMBO_FOR_SUPER
    assert g.super_timer == SUPER_DURATION
    assert g.turbulence_timer == 0  # super cancels turbulence
    assert g.screen_shake == 5


def test_thermal_entry_match_during_super_double_score() -> None:
    g = _make_game()
    g.player_color = ThermalColor.RED
    g.super_timer = 100
    g.combo = 2
    g.max_combo = 2
    g.score = 200
    thermal = Thermal(x=140.0, width=30, color=ThermalColor.RED)
    g._handle_thermal_entry(thermal)
    assert g.score == 200 + SCORE_PER_THERMAL * 3 * 2  # combo=3, super x2


def test_thermal_entry_mismatch() -> None:
    g = _make_game()
    g.player_color = ThermalColor.RED
    g.combo = 3
    g.max_combo = 3
    g._combo_flash_timer = 30
    thermal = Thermal(x=140.0, width=30, color=ThermalColor.BLUE)
    g._handle_thermal_entry(thermal)
    assert g.combo == 0
    assert g.max_combo == 3  # max_combo preserved
    assert g._combo_flash_timer == 0  # flash reset on mismatch
    assert g.heat == HEAT_PER_MISMATCH
    assert len(g.particles) == 2  # mismatch spawns 2 particles


def test_thermal_entry_mismatch_during_super_no_heat() -> None:
    g = _make_game()
    g.player_color = ThermalColor.RED
    g.super_timer = 100
    g.combo = 5
    g.heat = 0.0
    thermal = Thermal(x=140.0, width=30, color=ThermalColor.BLUE)
    g._handle_thermal_entry(thermal)
    assert g.combo == 0  # combo still resets
    assert g.heat == 0.0  # but no heat added during super


# ── Ring Tests ──


def test_ring_collision_near() -> None:
    g = _make_game()
    g.player_x = 100.0
    g.player_y = 100.0
    ring = Ring(x=102.0, y=100.0, color=ThermalColor.GREEN)
    g.rings = [ring]
    collected = g._check_ring_collision()
    assert len(collected) == 1
    assert collected[0] is ring
    assert g.score == SCORE_PER_RING  # multiplier=1 (not in super)


def test_ring_collision_super_radius() -> None:
    g = _make_game()
    g.player_x = 100.0
    g.player_y = 100.0
    g.super_timer = 100
    ring = Ring(x=140.0, y=100.0, color=ThermalColor.YELLOW)
    g.rings = [ring]
    collected = g._check_ring_collision()
    assert len(collected) == 1
    assert g.score == SCORE_PER_RING * 2  # super doubles ring score


def test_ring_collision_far() -> None:
    g = _make_game()
    g.player_x = 100.0
    g.player_y = 100.0
    ring = Ring(x=200.0, y=200.0, color=ThermalColor.RED)
    g.rings = [ring]
    collected = g._check_ring_collision()
    assert len(collected) == 0


# ── Bird Tests ──


def test_bird_collision_hit() -> None:
    g = _make_game()
    g.player_x = 100.0
    g.player_y = 100.0
    bird = Bird(x=100.0, y=100.0, vx=-1.5, base_y=100.0, timer=0.0)
    g.birds = [bird]
    result = g._check_bird_collision()
    assert result is bird


def test_bird_collision_miss() -> None:
    g = _make_game()
    g.player_x = 100.0
    g.player_y = 100.0
    bird = Bird(x=200.0, y=200.0, vx=-1.5, base_y=200.0, timer=0.0)
    g.birds = [bird]
    result = g._check_bird_collision()
    assert result is None


def test_bird_hit_adds_heat() -> None:
    g = _make_game()
    g.player_x = 100.0
    g.player_y = 100.0
    g.heat = 10.0
    bird = Bird(x=100.0, y=100.0, vx=-1.5, base_y=100.0, timer=0.0)
    g.birds = [bird]
    g._update_birds()
    assert bird not in g.birds  # removed
    assert g.heat == 10.0 + HEAT_PER_BIRD
    assert len(g.particles) == 5  # bird hit spawns 5


# ── Super Tick Tests ──


def test_super_tick_decrements() -> None:
    g = _make_game()
    g.super_timer = 10
    g._handle_super_tick()
    assert g.super_timer == 9


def test_super_tick_auto_collects_rings() -> None:
    g = _make_game()
    g.player_x = 100.0
    g.player_y = 100.0
    g.super_timer = 100
    ring = Ring(x=102.0, y=100.0, color=ThermalColor.GREEN)
    g.rings = [ring]
    g._handle_super_tick()
    assert ring not in g.rings


# ── Turbulence Tests ──


def test_turbulence_tick_decrements() -> None:
    g = _make_game()
    g.turbulence_timer = 50
    g.screen_shake = 50
    g._handle_turbulence_tick()
    assert g.turbulence_timer == 49
    assert g.screen_shake == 49


def test_turbulence_ends() -> None:
    g = _make_game()
    g.turbulence_timer = 1
    g.screen_shake = 1
    g._handle_turbulence_tick()
    assert g.turbulence_timer == 0
    assert g.screen_shake == 0


# ── Heat Tests ──


def test_heat_triggers_turbulence() -> None:
    g = _make_game()
    g.heat = MAX_HEAT
    g.combo = 3
    g._combo_flash_timer = 30
    g._update_heat()
    assert g.turbulence_timer == TURBULENCE_DURATION
    assert g.screen_shake == TURBULENCE_DURATION
    assert g.combo == 0  # combo reset on turbulence
    assert g._combo_flash_timer == 0


def test_heat_decays_when_not_turbulent() -> None:
    g = _make_game()
    g.heat = 50.0
    g.turbulence_timer = 0
    g._update_heat()
    assert g.heat == 49.9  # decays by 0.1


def test_heat_does_not_go_negative() -> None:
    g = _make_game()
    g.heat = 0.05
    g._update_heat()
    assert g.heat == 0.0


def test_heat_resets_during_turbulence() -> None:
    g = _make_game()
    g.heat = MAX_HEAT
    g._update_heat()  # triggers turbulence
    assert g.turbulence_timer == TURBULENCE_DURATION
    assert g.heat == 0.0  # heat resets


def test_turbulence_not_trigged_during_super() -> None:
    g = _make_game()
    g.heat = MAX_HEAT
    g.super_timer = 100
    g._update_heat()
    assert g.turbulence_timer == 0  # super blocks turbulence


# ── Spawn Tests ──


def test_spawn_thermal() -> None:
    g = _make_game()
    t = g._spawn_thermal()
    assert isinstance(t, Thermal)
    assert 24 <= t.width <= 40
    assert isinstance(t.color, ThermalColor)
    assert t.x >= SCREEN_W  # spawns ahead


def test_spawn_ring() -> None:
    g = _make_game()
    r = g._spawn_ring()
    assert isinstance(r, Ring)
    assert isinstance(r.color, ThermalColor)
    assert r.x >= SCREEN_W
    assert 30.0 <= r.y <= SCREEN_H - 50.0  # within bounds (-MOUNTAIN_H-30)


def test_spawn_bird() -> None:
    g = _make_game()
    b = g._spawn_bird()
    assert isinstance(b, Bird)
    assert -2.0 <= b.vx <= -1.0
    assert b.x >= SCREEN_W


def test_spawn_particles() -> None:
    g = _make_game()
    g._spawn_particles(100.0, 200.0, RED, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert isinstance(p, Particle)
        assert p.x == 100.0
        assert p.y == 200.0
        assert p.color == RED
        assert -1.0 <= p.vx <= 1.0
        assert -3.0 <= p.vy <= -1.0
        assert 15 <= p.life <= 30


def test_spawn_super_particles() -> None:
    g = _make_game()
    g.player_x = 150.0
    g.player_y = 100.0
    g._spawn_super_particles()
    assert len(g.particles) == 12  # 4 colors × 3 each
    colors = {p.color for p in g.particles}
    assert colors == {RED, GREEN, LIGHT_BLUE, YELLOW}


# ── Particle Update Tests ──


def test_update_particles() -> None:
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=1.0, vy=-2.0, life=2, color=RED)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].x == 1.0
    assert g.particles[0].y == -2.0
    assert g.particles[0].life == 1


def test_particles_removed_when_life_zero() -> None:
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=RED)]
    g._update_particles()
    assert len(g.particles) == 0  # life went to 0, removed


# ── Color Cycle Tests ──


def test_color_cycle() -> None:
    g = _make_game()
    assert g.player_color == ThermalColor.RED
    g.color_cycle_timer = 1
    g._cycle_player_color()
    assert g.player_color == ThermalColor.GREEN
    assert g.color_cycle_timer == COLOR_CYCLE_FRAMES  # reset


def test_color_cycle_no_change_when_timer_not_zero() -> None:
    g = _make_game()
    g.color_cycle_timer = 100
    g._cycle_player_color()
    assert g.player_color == ThermalColor.RED
    assert g.color_cycle_timer == 99


# ── Game Over Tests ──


def test_game_over_at_bottom() -> None:
    g = _make_game()
    from main import MOUNTAIN_H

    g.player_y = SCREEN_H - MOUNTAIN_H
    assert g._check_game_over() is True


def test_not_game_over_in_air() -> None:
    g = _make_game()
    g.player_y = 100.0
    assert g._check_game_over() is False


# ── Thermal Update Tests ──


def test_thermals_spawn_when_timer_zero() -> None:
    g = _make_game()
    g._thermal_spawn_timer = 1
    g.thermals = []
    g._update_thermals()
    # timer decremented to 0, spawn triggers, timer reset immediately
    assert len(g.thermals) == 1
    assert g._thermal_spawn_timer > 0  # timer was reset by spawn


def test_thermals_dont_exceed_max() -> None:
    g = _make_game()
    g._thermal_spawn_timer = 0
    g.thermals = [Thermal(x=100.0, width=30, color=ThermalColor.RED) for _ in range(MAX_THERMALS)]
    g._update_thermals()
    assert len(g.thermals) == MAX_THERMALS  # no new spawn


def test_thermals_scroll_left() -> None:
    g = _make_game()
    t = Thermal(x=50.0, width=30, color=ThermalColor.RED)
    g.thermals = [t]
    g._update_thermals()
    assert t.x == 50.0 - WORLD_SCROLL_SPEED


def test_thermals_removed_offscreen() -> None:
    g = _make_game()
    g.thermals = [Thermal(x=-40.0, width=30, color=ThermalColor.RED)]  # off-left
    g._update_thermals()
    assert len(g.thermals) == 0


# ── Ring Update Tests ──


def test_rings_spawn_when_timer_zero() -> None:
    g = _make_game()
    g._ring_spawn_timer = 1
    g.rings = []
    g.player_x = 999.0  # far from anything
    g.player_y = 999.0
    g._update_rings()
    # timer decremented to 0, spawn triggers, timer reset immediately
    assert len(g.rings) == 1
    assert g._ring_spawn_timer > 0  # timer was reset by spawn


# ── Bird Update Tests ──


def test_birds_spawn_when_timer_zero() -> None:
    g = _make_game()
    g._bird_spawn_timer = 1
    g.birds = []
    g.player_x = 999.0
    g.player_y = 999.0
    g._update_birds()
    # timer decremented to 0, spawn triggers, timer reset immediately
    assert len(g.birds) == 1
    assert g._bird_spawn_timer > 0  # timer was reset by spawn


# ── Thermal Lift via Physics ──


def test_thermal_lift_applies() -> None:
    g = _make_game()
    g.player_x = 100.0
    g.player_y = 100.0
    g.thermals = [Thermal(x=90.0, width=30, color=ThermalColor.RED)]
    g.player_color = ThermalColor.RED
    orig_score = g.score
    g._update_physics()
    assert g.combo == 1
    assert g.score > orig_score


# ── Score Calculation Consistency Tests ──


def test_score_increases_monotonically() -> None:
    g = _make_game()
    g.player_color = ThermalColor.RED
    scores = []
    for i in range(1, 6):
        g.combo = i - 1
        g.max_combo = max(g.max_combo, i - 1)
        old_score = g.score
        thermal = Thermal(x=50.0, width=30, color=ThermalColor.RED)
        g._handle_thermal_entry(thermal)
        scores.append(g.score - old_score)
    # Each successive match should give more score (higher combo multiplier)
    assert all(scores[i] >= scores[i - 1] for i in range(1, len(scores)))


# ── Ring Update with Collision ──


def test_rings_removed_after_collection() -> None:
    g = _make_game()
    ring = Ring(x=99.0, y=100.0, color=ThermalColor.GREEN)
    g.rings = [ring]
    g.player_x = 100.0
    g.player_y = 100.0
    g._update_rings()
    assert ring not in g.rings


# ── Bird Move and Removal Tests ──


def test_bird_removed_offscreen() -> None:
    g = _make_game()
    g.player_x = 999.0
    g.player_y = 999.0
    bird = Bird(x=-40.0, y=100.0, vx=-1.5, base_y=100.0, timer=0.0)
    g.birds = [bird]
    g._update_birds()
    assert len(g.birds) == 0


# ── Run all tests ──

if __name__ == "__main__":

    tests = [
        (name, obj)
        for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
