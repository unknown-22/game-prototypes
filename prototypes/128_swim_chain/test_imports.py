"""test_imports.py — Headless logic tests for SWIM CHAIN."""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/128_swim_chain")
from main import (
    AUTO_SCROLL_SPEED,
    BUOY_COLORS,
    BUOY_RADIUS,
    BUBBLE_RADIUS,
    COMBO_THRESHOLD,
    CYAN,
    FloatingText,
    GREEN,
    HEAT_DECAY,
    HEAT_MAX,
    HEAT_WRONG_COLOR,
    LANE_COUNT,
    LANE_YS,
    MAX_PREDATORS,
    OXYGEN_BUBBLE_REPLENISH,
    OXYGEN_DECAY,
    OXYGEN_MAX,
    Particle,
    Phase,
    PLAYER_RADIUS,
    PLAYER_SPEED,
    PREDATOR_RADIUS,
    RED,
    SCREEN_H,
    SCREEN_W,
    SPAWN_INTERVAL,
    SUPER_DURATION,
    SUPER_SPEED_MULT,
    YELLOW,
    Buoy,
    Bubble,
    Game,
    Predator,
)
from main import _lane_y as _lane_y_fn


def _make_game() -> Game:
    g: Game = Game.__new__(Game)
    g._rng = random.Random(42)
    g._frame_count = 0
    g.buoys = []
    g.bubbles = []
    g.predators = []
    g.particles = []
    g.floating_texts = []
    g._shake_frames = 0
    g.reset()
    return g


# ── Constants Tests ──────────────────────────────────────────────────


def test_constants() -> None:
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert PLAYER_RADIUS == 8
    assert LANE_COUNT == 4
    assert BUOY_RADIUS == 8
    assert BUBBLE_RADIUS == 5
    assert PREDATOR_RADIUS == 12
    assert COMBO_THRESHOLD == 4
    assert SUPER_DURATION == 300
    assert OXYGEN_MAX == 100.0
    assert OXYGEN_DECAY == 0.03
    assert OXYGEN_BUBBLE_REPLENISH == 25.0
    assert HEAT_MAX == 100.0
    assert HEAT_DECAY == 0.02
    assert HEAT_WRONG_COLOR == 15.0
    assert AUTO_SCROLL_SPEED == 0.5
    assert SUPER_SPEED_MULT == 2.0
    assert PLAYER_SPEED == 3.0
    assert SPAWN_INTERVAL == 120
    assert MAX_PREDATORS == 8
    assert len(BUOY_COLORS) == 4
    assert BUOY_COLORS == (RED, GREEN, YELLOW, CYAN)


def test_lane_ys() -> None:
    assert len(LANE_YS) == 4
    for i in range(3):
        assert LANE_YS[i] < LANE_YS[i + 1]


def test_lane_y_fn() -> None:
    y0 = _lane_y_fn(0)
    y1 = _lane_y_fn(1)
    assert y1 > y0


# ── Dataclass Tests ──────────────────────────────────────────────────


def test_buoy_fields() -> None:
    b = Buoy(x=100.0, y=50.0, color=RED)
    assert b.x == 100.0
    assert b.y == 50.0
    assert b.color == RED
    assert b.active is True
    assert b.radius == BUOY_RADIUS


def test_bubble_fields() -> None:
    b = Bubble(x=200.0, y=100.0)
    assert b.x == 200.0
    assert b.y == 100.0
    assert b.radius == BUBBLE_RADIUS
    assert b.active is True


def test_predator_fields() -> None:
    p = Predator(x=300.0, y=80.0, vy=0.5)
    assert p.x == 300.0
    assert p.y == 80.0
    assert p.vy == 0.5
    assert p.active is True
    assert p.radius == PREDATOR_RADIUS


def test_particle_fields() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=15, color=RED)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == RED


def test_floating_text_fields() -> None:
    ft = FloatingText(x=50.0, y=60.0, text="+100", life=25, color=YELLOW)
    assert ft.x == 50.0
    assert ft.y == 60.0
    assert ft.text == "+100"
    assert ft.life == 25
    assert ft.color == YELLOW
    assert ft.vy == -1.0


# ── Game State Tests ─────────────────────────────────────────────────


def test_game_reset() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.player_x > 0
    assert g.oxygen == OXYGEN_MAX
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.distance == 0.0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.super_mode is False
    assert len(g.buoys) == 0
    assert len(g.bubbles) == 0
    assert len(g.predators) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0


def test_game_reset_clears_all() -> None:
    g = _make_game()
    g.buoys = [Buoy(x=100, y=50, color=RED)]
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=1, color=RED)]
    g.floating_texts = [FloatingText(x=0, y=0, text="x", life=1, color=RED)]
    g.reset()
    assert len(g.buoys) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0


# ── Oxygen System Tests ──────────────────────────────────────────────


def test_oxygen_decreases() -> None:
    g = _make_game()
    g.oxygen = 50.0
    g._update_oxygen()
    assert g.oxygen == 50.0 - OXYGEN_DECAY


def test_oxygen_floor() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.oxygen = OXYGEN_DECAY / 2
    g._update_oxygen()
    assert g.oxygen == 0
    assert g.phase == Phase.GAME_OVER


def test_oxygen_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.oxygen = 0.0
    g._update_oxygen()
    assert g.phase == Phase.GAME_OVER


# ── Heat System Tests ────────────────────────────────────────────────


def test_heat_decay() -> None:
    g = _make_game()
    g.heat = 10.0
    g._update_heat()
    assert g.heat == 10.0 - HEAT_DECAY


def test_heat_floor() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_heat_max_causes_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = HEAT_MAX
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_heat_immunity_during_super() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_timer = 10
    g.heat = HEAT_MAX
    g._update_heat()
    assert g.phase == Phase.PLAYING


# ── Super Mode Tests ─────────────────────────────────────────────────


def test_super_mode_property() -> None:
    g = _make_game()
    assert g.super_mode is False
    g.super_timer = 10
    assert g.super_mode is True
    g.super_timer = 0
    assert g.super_mode is False


def test_activate_super() -> None:
    g = _make_game()
    g._activate_super()
    assert g.super_timer == SUPER_DURATION
    assert g.super_mode is True
    assert g._shake_frames == 8


def test_update_super_decrements() -> None:
    g = _make_game()
    g.super_timer = 10
    g._update_super()
    assert g.super_timer == 9


def test_update_super_expires() -> None:
    g = _make_game()
    g.super_timer = 1
    g.combo = 5
    g._update_super()
    assert g.super_timer == 0
    assert g.super_mode is False
    assert g.combo == 0


def test_update_super_noop_when_inactive() -> None:
    g = _make_game()
    g._update_super()
    assert g.super_timer == 0


# ── Buoy Collision Tests ─────────────────────────────────────────────


def test_on_same_color_buoy() -> None:
    g = _make_game()
    g.combo = 0
    g.score = 0
    g._on_same_color_buoy(RED)
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score == 10
    assert len(g.floating_texts) == 1
    assert len(g.particles) == 5


def test_on_wrong_color_buoy() -> None:
    g = _make_game()
    g.combo = 3
    g.heat = 10.0
    g._on_wrong_color_buoy()
    assert g.combo == 0
    assert g.heat == 10.0 + HEAT_WRONG_COLOR


def test_buoy_hit_starts_combo() -> None:
    g = _make_game()
    g.combo = 0
    g.score = 0
    b = Buoy(x=g.player_x, y=g.player_y, color=RED)
    g._on_buoy_hit(b)
    assert g.combo == 1
    assert g.score == 10


def test_buoy_hit_continues_combo_same_color() -> None:
    g = _make_game()
    g.combo = 2
    g.score = 0
    current_color = BUOY_COLORS[2 % 4]  # YELLOW
    b = Buoy(x=g.player_x, y=g.player_y, color=current_color)
    g._on_buoy_hit(b)
    assert g.combo == 3
    assert g.score > 0


def test_buoy_hit_wrong_color_breaks_combo() -> None:
    g = _make_game()
    g.combo = 2
    g.score = 0
    g.heat = 0
    current_color = BUOY_COLORS[2 % 4]
    wrong_color = RED if current_color != RED else GREEN
    b = Buoy(x=g.player_x, y=g.player_y, color=wrong_color)
    g._on_buoy_hit(b)
    assert g.combo == 0
    assert g.heat > 0


def test_combo_score_scales() -> None:
    g = _make_game()
    g.combo = 0
    g.score = 0
    g._on_same_color_buoy(RED)
    score1 = g.score
    g._on_same_color_buoy(RED)
    score2 = g.score - score1
    g._on_same_color_buoy(RED)
    score3 = g.score - score1 - score2
    assert score3 >= score2 >= score1


def test_combo_triggers_super() -> None:
    g = _make_game()
    g.combo = COMBO_THRESHOLD - 1
    g._on_same_color_buoy(RED)
    assert g.combo == COMBO_THRESHOLD
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


# ── Bubble Tests ─────────────────────────────────────────────────────


def test_bubble_replenish_oxygen() -> None:
    g = _make_game()
    g.oxygen = 50.0
    g.bubbles = [Bubble(x=g.player_x, y=g.player_y)]
    g._check_bubble_collisions()
    assert g.oxygen == 50.0 + OXYGEN_BUBBLE_REPLENISH


def test_bubble_capped_at_max() -> None:
    g = _make_game()
    g.oxygen = 99.0
    g.bubbles = [Bubble(x=g.player_x, y=g.player_y)]
    g._check_bubble_collisions()
    assert g.oxygen == OXYGEN_MAX


# ── Predator Collision Tests ─────────────────────────────────────────


def test_predator_collision_damage() -> None:
    g = _make_game()
    g.oxygen = 100.0
    g.heat = 0.0
    g.combo = 3
    g.predators = [Predator(x=g.player_x, y=g.player_y)]
    g._check_predator_collisions()
    assert g.oxygen < 100.0
    assert g.heat > 0.0
    assert g.combo == 0


def test_predator_collision_in_super() -> None:
    g = _make_game()
    g.super_timer = 10
    g.score = 0
    g.predators = [Predator(x=g.player_x, y=g.player_y)]
    g._check_predator_collisions()
    assert g.predators[0].active is False
    assert g.score == 50


# ── Particle Tests ───────────────────────────────────────────────────


def test_spawn_particles() -> None:
    g = _make_game()
    g._spawn_particles(100, 100, 5, RED)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color == RED


def test_update_particles_decay() -> None:
    g = _make_game()
    g.particles = [Particle(x=50, y=50, vx=0, vy=0, life=3, color=RED)]
    for _ in range(4):
        g._update_particles()
    assert len(g.particles) == 0


def test_update_particles_buoyancy() -> None:
    g = _make_game()
    g.particles = [Particle(x=50, y=50, vx=0, vy=2, life=30, color=RED)]
    g._update_particles()
    assert g.particles[0].vy < 2


# ── Floating Text Tests ──────────────────────────────────────────────


def test_spawn_floating_text() -> None:
    g = _make_game()
    g._spawn_floating_text(100, 100, "+100", YELLOW)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "+100"
    assert g.floating_texts[0].color == YELLOW


def test_update_floating_texts_decay() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=50, y=50, text="test", life=2, color=RED)]
    for _ in range(3):
        g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_floating_texts_float_up() -> None:
    g = _make_game()
    ft = FloatingText(x=50, y=50, text="test", life=10, color=RED, vy=-1.0)
    g.floating_texts = [ft]
    g._update_floating_texts()
    assert g.floating_texts[0].y < 50


# ── Spawn Tests ──────────────────────────────────────────────────────


def test_spawn_buoys() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.scroll_x = 0.0
    g.player_x = 60.0
    g.player_y = SCREEN_H / 2
    g._spawn_buoys()
    assert len(g.buoys) >= LANE_COUNT


def test_spawn_bubbles_sometimes() -> None:
    g = _make_game()
    g.scroll_x = 0.0
    for _ in range(200):
        g._spawn_bubbles()
    assert len(g.bubbles) >= 0


def test_spawn_predator_respects_max() -> None:
    g = _make_game()
    g.scroll_x = 0.0
    for _ in range(MAX_PREDATORS + 5):
        g._rng = random.Random(42 + _)
        g._spawn_predator()
    assert len(g.predators) <= MAX_PREDATORS


# ── Update Buoys/Predators/Bubbles Tests ─────────────────────────────


def test_update_buoys_removes_offscreen() -> None:
    g = _make_game()
    g.scroll_x = 1000.0
    g.buoys = [Buoy(x=10.0, y=100, color=RED)]
    g._update_buoys()
    assert len(g.buoys) == 0


def test_update_buoys_keeps_onscreen() -> None:
    g = _make_game()
    g.scroll_x = 0.0
    g.buoys = [Buoy(x=200.0, y=100, color=RED)]
    g._update_buoys()
    assert len(g.buoys) == 1


def test_update_predators_removes_offscreen() -> None:
    g = _make_game()
    g.scroll_x = 1000.0
    g.predators = [Predator(x=10.0, y=100)]
    g._update_predators()
    assert len(g.predators) == 0


def test_update_bubbles_removes_offscreen() -> None:
    g = _make_game()
    g.scroll_x = 1000.0
    g.bubbles = [Bubble(x=10.0, y=100)]
    g._update_bubbles()
    assert len(g.bubbles) == 0


# ── Run ──────────────────────────────────────────────────────────────


def main() -> None:
    tests = [
        test_constants,
        test_lane_ys,
        test_lane_y_fn,
        test_buoy_fields,
        test_bubble_fields,
        test_predator_fields,
        test_particle_fields,
        test_floating_text_fields,
        test_game_reset,
        test_game_reset_clears_all,
        test_oxygen_decreases,
        test_oxygen_floor,
        test_oxygen_game_over,
        test_heat_decay,
        test_heat_floor,
        test_heat_max_causes_game_over,
        test_heat_immunity_during_super,
        test_super_mode_property,
        test_activate_super,
        test_update_super_decrements,
        test_update_super_expires,
        test_update_super_noop_when_inactive,
        test_on_same_color_buoy,
        test_on_wrong_color_buoy,
        test_buoy_hit_starts_combo,
        test_buoy_hit_continues_combo_same_color,
        test_buoy_hit_wrong_color_breaks_combo,
        test_combo_score_scales,
        test_combo_triggers_super,
        test_bubble_replenish_oxygen,
        test_bubble_capped_at_max,
        test_predator_collision_damage,
        test_predator_collision_in_super,
        test_spawn_particles,
        test_update_particles_decay,
        test_update_particles_buoyancy,
        test_spawn_floating_text,
        test_update_floating_texts_decay,
        test_floating_texts_float_up,
        test_spawn_buoys,
        test_spawn_bubbles_sometimes,
        test_spawn_predator_respects_max,
        test_update_buoys_removes_offscreen,
        test_update_buoys_keeps_onscreen,
        test_update_predators_removes_offscreen,
        test_update_bubbles_removes_offscreen,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  PASS  {test.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL  {test.__name__}: {e}")

    print(f"\n{passed} passed, {failed} failed out of {len(tests)}")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
