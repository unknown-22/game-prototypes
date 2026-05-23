"""test_imports.py — Headless logic tests for CHROMA CROSS.

Uses Game.__new__ to bypass pyxel.init/pyxel.run.
Tests inner logic methods directly, never wrapper methods that access pyxel.btn etc.
"""
from __future__ import annotations

import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/057_chroma_cross")
from main import (
    COLOR_NAMES,
    COLOR_VALS,
    COMBO_THRESHOLD,
    COMBO_TIMEOUT,
    DAMAGE_COOLDOWN,
    LANE_COUNT,
    LANE_H,
    NUM_COLORS,
    OBSTACLE_H,
    OBSTACLE_MIN_GAP,
    OBSTACLE_MAX_W,
    OBSTACLE_MIN_W,
    PLAYER_H,
    PLAYER_SPEED,
    PLAYER_W,
    SCREEN_H,
    SCREEN_W,
    SUPER_DURATION,
    FloatingText,
    Game,
    Obstacle,
    Particle,
    Phase,
)


def _make_game() -> Game:
    """Create a Game instance without calling pyxel.init/run."""
    g = Game.__new__(Game)
    g._rng = random.Random()
    g.phase = Phase.TITLE
    g.player_x = SCREEN_W / 2
    g.player_y = SCREEN_H - LANE_H / 2
    g.player_color_idx = 0
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.combo_timer = 0
    g.hp = 5
    g.max_hp = 5
    g.level = 1
    g.damage_cooldown = 0
    g.obstacles = []
    g.particles = []
    g.floating_texts = []
    g.super_mode = False
    g.super_timer = 0
    g._init_state()
    return g


# ── Constants tests ──


def test_constants() -> None:
    assert len(COLOR_VALS) == 4
    assert len(COLOR_NAMES) == 4
    assert NUM_COLORS == 4
    assert COMBO_THRESHOLD == 5
    assert COMBO_TIMEOUT == 90
    assert SUPER_DURATION == 180
    assert DAMAGE_COOLDOWN == 30
    assert LANE_COUNT == 8
    assert LANE_H == 32
    assert SCREEN_H == 256
    assert SCREEN_W == 256
    assert PLAYER_W == 12
    assert PLAYER_H == 12
    assert PLAYER_SPEED == 2


# ── Dataclass tests ──


def test_obstacle_dataclass() -> None:
    obs = Obstacle(x=50.0, y=64, w=40, color_idx=0, speed=1.2)
    assert obs.x == 50.0
    assert obs.y == 64
    assert obs.w == 40
    assert obs.right == 90.0
    assert obs.color_idx == 0
    assert obs.color_val == 8  # RED
    assert abs(obs.speed - 1.2) < 0.01

    obs2 = Obstacle(x=10.0, y=0, w=30, color_idx=2, speed=-0.8)
    assert obs2.color_val == 10  # YELLOW
    assert obs2.speed < 0


def test_particle_dataclass() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=15, color=8)
    assert p.x == 10.0
    assert p.life == 15
    assert p.color == 8


def test_floating_text_dataclass() -> None:
    ft = FloatingText(x=50.0, y=30.0, text="+100", life=40, color=10)
    assert ft.text == "+100"
    assert ft.life == 40


# ── Game initialization tests ──


def test_game_init_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.hp == 5
    assert g.max_hp == 5
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.level == 1
    assert not g.super_mode
    assert g.super_timer == 0
    assert g.damage_cooldown == 0
    assert len(g.obstacles) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0


def test_player_color_property() -> None:
    g = _make_game()
    g.player_color_idx = 0
    assert g.player_color == 8  # RED
    g.player_color_idx = 1
    assert g.player_color == 3  # GREEN
    g.player_color_idx = 2
    assert g.player_color == 10  # YELLOW
    g.player_color_idx = 3
    assert g.player_color == 6  # LIGHT_BLUE


# ── Geometry tests ──


def test_player_rect() -> None:
    r = Game._player_rect(100.0, 200.0)
    assert abs(r[0] - 94.0) < 0.01
    assert abs(r[1] - 194.0) < 0.01
    assert abs(r[2] - 106.0) < 0.01
    assert abs(r[3] - 206.0) < 0.01


def test_rects_overlap_true() -> None:
    a = (0.0, 0.0, 10.0, 10.0)
    b = (5.0, 5.0, 15.0, 15.0)
    assert Game._rects_overlap(a, b)


def test_rects_overlap_false() -> None:
    a = (0.0, 0.0, 10.0, 10.0)
    b = (20.0, 20.0, 30.0, 30.0)
    assert not Game._rects_overlap(a, b)


def test_rects_overlap_edge_touch() -> None:
    a = (0.0, 0.0, 10.0, 10.0)
    b = (10.0, 0.0, 20.0, 10.0)
    # Touching edges don't overlap (strict inequality)
    assert not Game._rects_overlap(a, b)


# ── Lane spawning tests ──


def test_spawn_lanes_creates_obstacles() -> None:
    g = _make_game()
    g.level = 1
    g._spawn_lanes()
    assert len(g.obstacles) > 0
    # Level 1: 1-2 per lane, 8 lanes
    assert 8 <= len(g.obstacles) <= 16


def test_spawn_lanes_higher_level() -> None:
    g = _make_game()
    g.level = 7  # should spawn 3-4 per lane
    g._spawn_lanes()
    assert len(g.obstacles) >= 16  # at least 2 per lane


def test_spawn_lanes_obstacle_bounds() -> None:
    g = _make_game()
    g.level = 1
    g._spawn_lanes()
    for obs in g.obstacles:
        assert 0 <= obs.x < SCREEN_W
        assert 0 <= obs.y < SCREEN_H
        assert OBSTACLE_MIN_W <= obs.w <= OBSTACLE_MAX_W
        assert 0 <= obs.color_idx < NUM_COLORS
        assert abs(obs.speed) > 0


def test_spawn_lanes_respects_lane_y() -> None:
    g = _make_game()
    g.level = 1
    g._spawn_lanes()
    lane_ys: set[int] = set()
    for obs in g.obstacles:
        # obs.y should be a multiple of LANE_H
        assert obs.y % LANE_H == 0
        lane_ys.add(obs.y)
    # Should have obstacles in at least a few lanes
    assert len(lane_ys) >= 4


# ── Obstacle movement tests ──


def test_update_obstacles_moves() -> None:
    g = _make_game()
    obs = Obstacle(x=100.0, y=0, w=40, color_idx=0, speed=2.0)
    g.obstacles = [obs]
    g._update_obstacles()
    assert abs(obs.x - 102.0) < 0.01


def test_update_obstacles_wraps_right() -> None:
    g = _make_game()
    obs = Obstacle(x=SCREEN_W + 10.0, y=0, w=40, color_idx=0, speed=3.0)
    g.obstacles = [obs]
    g._update_obstacles()
    # Should wrap to just off left edge
    assert obs.x < 0


def test_update_obstacles_wraps_left() -> None:
    g = _make_game()
    obs = Obstacle(x=-50.0, y=0, w=40, color_idx=0, speed=-3.0)
    g.obstacles = [obs]
    g._update_obstacles()
    # Should wrap to just off right edge
    assert obs.x >= SCREEN_W - 40


# ── Collision tests ──


def test_collision_matching_color_builds_combo() -> None:
    g = _make_game()
    g.player_color_idx = 0  # RED
    g.combo = 0
    g.max_combo = 0
    g.hp = 5
    g.damage_cooldown = 0
    g.super_mode = False
    # Place player and a RED obstacle overlapping
    g.player_x = 100.0
    g.player_y = 20.0
    g.obstacles = [
        Obstacle(x=90.0, y=0, w=40, color_idx=0, speed=0.0)  # RED, same as player
    ]
    g._update_collisions()
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.hp == 5  # No damage


def test_collision_wrong_color_damages() -> None:
    g = _make_game()
    g.player_color_idx = 0  # RED
    g.combo = 3
    g.hp = 5
    g.damage_cooldown = 0
    g.super_mode = False
    g.combo_timer = 50
    g.player_x = 100.0
    g.player_y = 20.0
    g.obstacles = [
        Obstacle(x=90.0, y=0, w=40, color_idx=1, speed=0.0)  # GREEN, not RED
    ]
    g._update_collisions()
    assert g.hp == 4  # -1 HP
    assert g.combo == 0  # Reset
    assert g.combo_timer == 0


def test_collision_damage_cooldown_prevents_double_damage() -> None:
    g = _make_game()
    g.player_color_idx = 0
    g.hp = 5
    g.damage_cooldown = 10  # Still cooling down
    g.super_mode = False
    g.player_x = 100.0
    g.player_y = 20.0
    g.obstacles = [
        Obstacle(x=90.0, y=0, w=40, color_idx=1, speed=0.0)
    ]
    g._update_collisions()
    assert g.hp == 5  # No damage due to cooldown


def test_collision_super_mode_prevents_damage() -> None:
    g = _make_game()
    g.player_color_idx = 0
    g.hp = 5
    g.damage_cooldown = 0
    g.super_mode = True
    g.super_timer = 100
    g.player_x = 100.0
    g.player_y = 20.0
    g.obstacles = [
        Obstacle(x=90.0, y=0, w=40, color_idx=1, speed=0.0)  # Wrong color
    ]
    g._update_collisions()
    assert g.hp == 5  # No damage


def test_collision_no_overlap_no_effect() -> None:
    g = _make_game()
    g.player_x = 10.0
    g.player_y = 10.0
    g.combo = 0
    g.hp = 5
    g.obstacles = [
        Obstacle(x=200.0, y=0, w=40, color_idx=1, speed=0.0)  # Far away
    ]
    g._update_collisions()
    assert g.combo == 0
    assert g.hp == 5


# ── Combo timer tests ──


def test_combo_timer_decrements() -> None:
    g = _make_game()
    g.combo = 3
    g.combo_timer = 10
    g._update_timers()
    assert g.combo_timer == 9
    assert g.combo == 3  # Still active


def test_combo_timer_expires() -> None:
    g = _make_game()
    g.combo = 3
    g.combo_timer = 2
    g._update_timers()
    assert g.combo_timer == 1
    assert g.combo == 3  # Still active at timer=1
    g._update_timers()
    assert g.combo_timer == 0
    assert g.combo == 0  # Reset when timer reaches 0


# ── Super mode tests ──


def test_activate_super() -> None:
    g = _make_game()
    g.player_x = 100.0
    g.player_y = 100.0
    g.particles = []
    g.floating_texts = []
    g._activate_super()
    assert g.super_mode
    assert g.super_timer == SUPER_DURATION
    assert len(g.particles) > 0
    assert len(g.floating_texts) > 0


def test_deactivate_super() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 50
    g._deactivate_super()
    assert not g.super_mode
    assert g.super_timer == 0


def test_super_timer_runs_out() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_timers()
    assert g.super_timer == 0
    assert not g.super_mode


def test_combo_activates_super_at_threshold() -> None:
    g = _make_game()
    g.player_x = 100.0
    g.player_y = 20.0
    g.player_color_idx = 0  # RED
    g.combo = COMBO_THRESHOLD - 1  # 4
    g.super_mode = False
    g.damage_cooldown = 0
    g.particles = []
    g.floating_texts = []
    g.obstacles = [
        Obstacle(x=90.0, y=0, w=40, color_idx=0, speed=0.0)  # Matching RED
    ]
    g._update_collisions()
    assert g.combo == COMBO_THRESHOLD  # 5
    assert g.super_mode
    assert g.super_timer == SUPER_DURATION


# ── Damage tests ──


def test_take_damage_reduces_hp() -> None:
    g = _make_game()
    g.player_x = 100.0
    g.player_y = 100.0
    g.hp = 3
    g.combo = 5
    g.combo_timer = 30
    g.damage_cooldown = 0
    g.super_mode = False
    g.particles = []
    g.floating_texts = []
    g._take_damage()
    assert g.hp == 2
    assert g.combo == 0
    assert g.combo_timer == 0
    assert g.damage_cooldown == DAMAGE_COOLDOWN


def test_take_damage_sets_game_over() -> None:
    g = _make_game()
    g.player_x = 100.0
    g.player_y = 100.0
    g.hp = 1
    g.damage_cooldown = 0
    g.super_mode = False
    g.particles = []
    g.floating_texts = []
    g.phase = Phase.PLAYING
    g._take_damage()
    assert g.hp == 0
    assert g.phase == Phase.GAME_OVER


def test_take_damage_blocked_by_super() -> None:
    g = _make_game()
    g.hp = 3
    g.super_mode = True
    g._take_damage()
    assert g.hp == 3


def test_take_damage_blocked_by_cooldown() -> None:
    g = _make_game()
    g.hp = 3
    g.damage_cooldown = 10
    g.super_mode = False
    g._take_damage()
    assert g.hp == 3


# ── Damage cooldown timer test ──


def test_damage_cooldown_decrements() -> None:
    g = _make_game()
    g.damage_cooldown = 10
    g._update_timers()
    assert g.damage_cooldown == 9


# ── Particle tests ──


def test_spawn_particles() -> None:
    g = _make_game()
    g.particles = []
    g._spawn_particles(50.0, 60.0, 8, count=5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert abs(p.x - 50.0) < 4
        assert abs(p.y - 60.0) < 4
        assert p.life > 0
        assert p.color == 8


def test_update_particles_moves_and_dies() -> None:
    g = _make_game()
    g.particles = [
        Particle(x=0.0, y=0.0, vx=1.0, vy=0.0, life=5, color=8),
        Particle(x=10.0, y=10.0, vx=0.0, vy=-1.0, life=2, color=3),
    ]
    g._update_particles()
    assert len(g.particles) == 2
    assert g.particles[0].life == 4
    assert abs(g.particles[0].x - 1.0) < 0.01
    # Particle with life=0 after decrement should be removed
    g._update_particles()
    assert len(g.particles) == 1  # Second particle removed
    assert g.particles[0].life == 3


# ── Floating text tests ──


def test_spawn_floating_text() -> None:
    g = _make_game()
    g.floating_texts = []
    g._spawn_floating_text(50.0, 60.0, "+100", 10)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "+100"
    assert g.floating_texts[0].life == 40


def test_update_floating_texts_moves_and_dies() -> None:
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=50.0, y=60.0, text="A", life=2, color=10),
        FloatingText(x=70.0, y=80.0, text="B", life=5, color=8),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 2
    assert g.floating_texts[0].life == 1  # Decremented from 2
    assert g.floating_texts[0].y < 60.0  # Floats up
    g._update_floating_texts()
    assert len(g.floating_texts) == 1  # Text A removed
    assert g.floating_texts[0].text == "B"


# ── Goal check tests ──


def test_check_goal_triggers_level_up() -> None:
    g = _make_game()
    g.player_y = LANE_H / 2 - 1  # Top lane
    g.score = 0
    g.level = 1
    g.combo = 3
    g.super_mode = False
    g.particles = []
    g.floating_texts = []
    g.obstacles = []
    g._check_goal()
    assert g.score > 0  # Points awarded
    assert g.level == 2
    # Player reset to bottom
    assert g.player_y == SCREEN_H - LANE_H / 2
    assert len(g.particles) > 0
    assert len(g.floating_texts) > 0


def test_check_goal_super_multiplier() -> None:
    g = _make_game()
    g.player_y = LANE_H / 2 - 1
    g.score = 0
    g.level = 1
    g.combo = 0
    g.super_mode = True
    g.super_timer = 50
    g.particles = []
    g.floating_texts = []
    g.obstacles = []
    g._check_goal()
    assert g.score == 300  # 100 * 3 (super multiplier)


def test_check_goal_no_trigger_below_top() -> None:
    g = _make_game()
    g.player_y = SCREEN_H / 2  # Middle of screen
    g.score = 0
    g.level = 1
    g._check_goal()
    assert g.score == 0
    assert g.level == 1


# ── Update collisions with both matching and wrong ──


def test_collision_wrong_takes_priority_over_matching() -> None:
    """When overlapping both matching and wrong-color obstacles, damage takes priority."""
    g = _make_game()
    g.player_color_idx = 0  # RED
    g.hp = 5
    g.combo = 2
    g.damage_cooldown = 0
    g.super_mode = False
    g.player_x = 100.0
    g.player_y = 20.0
    g.obstacles = [
        Obstacle(x=90.0, y=0, w=40, color_idx=0, speed=0.0),  # RED (matching)
        Obstacle(x=95.0, y=0, w=30, color_idx=1, speed=0.0),  # GREEN (wrong)
    ]
    g._update_collisions()
    assert g.hp == 4  # Damage applied
    assert g.combo == 0  # Reset


# ── Combo max tracking ──


def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    g.player_color_idx = 0
    g.player_x = 100.0
    g.player_y = 20.0
    g.combo = 0
    g.max_combo = 0
    g.damage_cooldown = 0
    g.super_mode = False
    g.obstacles = [
        Obstacle(x=90.0, y=0, w=40, color_idx=0, speed=0.0)
    ]
    g._update_collisions()
    assert g.max_combo == 1
    g._update_collisions()
    assert g.max_combo == 2
    # Damage resets combo but max_combo stays
    g.obstacles[0].color_idx = 1  # Make it wrong color
    g.damage_cooldown = 0
    g._update_collisions()
    assert g.combo == 0
    assert g.max_combo == 2  # Should retain max


# ── Phase enum ──


def test_phase_values() -> None:
    assert Phase.TITLE == 0
    assert Phase.PLAYING == 1
    assert Phase.GAME_OVER == 2


if __name__ == "__main__":
    import traceback

    tests = [
        test_constants,
        test_obstacle_dataclass,
        test_particle_dataclass,
        test_floating_text_dataclass,
        test_game_init_state,
        test_player_color_property,
        test_player_rect,
        test_rects_overlap_true,
        test_rects_overlap_false,
        test_rects_overlap_edge_touch,
        test_spawn_lanes_creates_obstacles,
        test_spawn_lanes_higher_level,
        test_spawn_lanes_obstacle_bounds,
        test_spawn_lanes_respects_lane_y,
        test_update_obstacles_moves,
        test_update_obstacles_wraps_right,
        test_update_obstacles_wraps_left,
        test_collision_matching_color_builds_combo,
        test_collision_wrong_color_damages,
        test_collision_damage_cooldown_prevents_double_damage,
        test_collision_super_mode_prevents_damage,
        test_collision_no_overlap_no_effect,
        test_combo_timer_decrements,
        test_combo_timer_expires,
        test_activate_super,
        test_deactivate_super,
        test_super_timer_runs_out,
        test_combo_activates_super_at_threshold,
        test_take_damage_reduces_hp,
        test_take_damage_sets_game_over,
        test_take_damage_blocked_by_super,
        test_take_damage_blocked_by_cooldown,
        test_damage_cooldown_decrements,
        test_spawn_particles,
        test_update_particles_moves_and_dies,
        test_spawn_floating_text,
        test_update_floating_texts_moves_and_dies,
        test_check_goal_triggers_level_up,
        test_check_goal_super_multiplier,
        test_check_goal_no_trigger_below_top,
        test_collision_wrong_takes_priority_over_matching,
        test_max_combo_tracks_highest,
        test_phase_values,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  PASS {test.__name__}")
        except Exception:
            print(f"  FAIL {test.__name__}")
            traceback.print_exc()
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
    sys.exit(0)
