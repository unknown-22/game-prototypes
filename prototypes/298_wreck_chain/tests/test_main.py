from __future__ import annotations

import random
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (
    BASE_SCORE,
    BALL_RADIUS,
    BUILDING_COLORS,
    BuildingSegment,
    CABLE_LENGTH,
    CRANE_Y,
    CRANE_SPEED,
    FPS,
    GAME_DURATION,
    GROUND_Y,
    HEAT_MAX,
    HEAT_MISS,
    MAX_SEGMENTS,
    PARTICLE_DESTROY_COUNT,
    PARTICLE_HIT_COUNT,
    SEGMENT_HP,
    SEGMENT_H,
    SEGMENT_W,
    SCREEN_W,
    SPAWN_INTERVAL_START,
    SUPER_DURATION,
    SUPER_MULTIPLIER,
    Game,
    Particle,
    Phase,
    check_collision,
    compute_heat_game_over,
    compute_score,
    compute_timer_game_over,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(seed)
    g.best_score = 0
    g.phase = Phase.PLAYING
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = GAME_DURATION * FPS
    g.crane_x = float(SCREEN_W // 2)
    g.ball_x = g.crane_x
    g.ball_y = CRANE_Y + CABLE_LENGTH
    g.ball_vx = 0.0
    g.ball_vy = 0.0
    g.ball_released = False
    g.last_hit_color: int | None = None
    g.super_mode = False
    g.super_timer = 0
    g.spawn_timer = SPAWN_INTERVAL_START
    g.shake_timer = 0
    g.segments = []
    g.particles = []
    g.floating_texts = []
    return g


def _make_segment(
    x: float = 160.0,
    y: float = 100.0,
    color: int = BUILDING_COLORS[0],
    hp: float = SEGMENT_HP,
    weakened: bool = False,
) -> BuildingSegment:
    return BuildingSegment(
        x=x, y=y, w=SEGMENT_W, h=SEGMENT_H, color=color, hp=hp, weakened=weakened,
    )


# --------------------------------------------------------------------------
# Pure Functions
# --------------------------------------------------------------------------
class TestPureFunctions:
    def test_compute_score_basic(self) -> None:
        assert compute_score(1, False, False) == BASE_SCORE

    def test_compute_score_combo(self) -> None:
        assert compute_score(3, False, False) == BASE_SCORE * 3

    def test_compute_score_weakened(self) -> None:
        assert compute_score(1, True, False) == BASE_SCORE * 2

    def test_compute_score_super(self) -> None:
        assert compute_score(1, False, True) == BASE_SCORE * 3

    def test_compute_score_weakened_super(self) -> None:
        assert compute_score(1, True, True) == BASE_SCORE * 2 * 3

    def test_compute_score_combo_weakened_super(self) -> None:
        assert compute_score(3, True, True) == BASE_SCORE * 3 * 2 * 3

    def test_check_collision_hit(self) -> None:
        assert check_collision(160.0, 100.0, BALL_RADIUS, 160.0, 100.0, SEGMENT_W, SEGMENT_H)

    def test_check_collision_miss(self) -> None:
        assert not check_collision(160.0, 100.0, BALL_RADIUS, 50.0, 50.0, SEGMENT_W, SEGMENT_H)

    def test_check_collision_edge(self) -> None:
        seg_edge = 160.0 - SEGMENT_W / 2 - BALL_RADIUS + 0.5
        assert check_collision(seg_edge, 100.0, BALL_RADIUS, 160.0, 100.0, SEGMENT_W, SEGMENT_H)

    def test_check_collision_just_outside(self) -> None:
        seg_outside = 160.0 - SEGMENT_W / 2 - BALL_RADIUS - 0.5
        assert not check_collision(seg_outside, 100.0, BALL_RADIUS, 160.0, 100.0, SEGMENT_W, SEGMENT_H)

    def test_compute_heat_game_over_true(self) -> None:
        assert compute_heat_game_over(HEAT_MAX)

    def test_compute_heat_game_over_false(self) -> None:
        assert not compute_heat_game_over(HEAT_MAX - 0.1)

    def test_compute_timer_game_over_true(self) -> None:
        assert compute_timer_game_over(0)

    def test_compute_timer_game_over_false(self) -> None:
        assert not compute_timer_game_over(1)


# --------------------------------------------------------------------------
# Crane Movement
# --------------------------------------------------------------------------
class TestCraneMovement:
    def test_crane_moves_right(self) -> None:
        g = _make_game()
        x0 = g.crane_x
        g._update_crane(1.0)
        assert g.crane_x > x0

    def test_crane_moves_left(self) -> None:
        g = _make_game()
        x0 = g.crane_x
        g._update_crane(-1.0)
        assert g.crane_x < x0

    def test_crane_clamped_right(self) -> None:
        g = _make_game()
        g.crane_x = float(SCREEN_W - 20)
        g._update_crane(1.0)
        assert g.crane_x <= SCREEN_W - 20

    def test_crane_clamped_left(self) -> None:
        g = _make_game()
        g.crane_x = 20.0
        g._update_crane(-1.0)
        assert g.crane_x >= 20.0

    def test_crane_moves_ball_when_locked(self) -> None:
        g = _make_game()
        g.ball_released = False
        g.ball_x = g.crane_x
        g.crane_x = 100.0
        g._update_crane(1.0)
        assert g.ball_x == g.crane_x

    def test_crane_not_move_ball_when_released(self) -> None:
        g = _make_game()
        g.ball_released = True
        g.ball_x = 150.0
        g._update_crane(1.0)
        # ball position shouldn't be directly set to crane_x
        assert g.ball_x == 150.0

    def test_crane_speed_constant(self) -> None:
        g = _make_game()
        x0 = g.crane_x
        g._update_crane(1.0)
        assert g.crane_x - x0 == CRANE_SPEED


# --------------------------------------------------------------------------
# Pendulum Physics
# --------------------------------------------------------------------------
class TestPendulumPhysics:
    def test_locked_ball_stays_below_crane(self) -> None:
        g = _make_game()
        g.ball_released = False
        g.crane_x = 160.0
        g._update_physics()
        assert g.ball_x == 160.0
        assert g.ball_y == CRANE_Y + CABLE_LENGTH

    def test_released_ball_applies_gravity(self) -> None:
        g = _make_game()
        g.ball_released = True
        g.ball_vy = 0.0
        g._update_physics()
        assert g.ball_vy > 0.0

    def test_released_ball_constrained_to_cable(self) -> None:
        g = _make_game()
        g.ball_released = True
        g.crane_x = 160.0
        g.ball_x = 160.0
        g.ball_y = CRANE_Y + CABLE_LENGTH + 100.0
        g.ball_vx = 0.0
        g.ball_vy = 0.0
        g._update_physics()
        dist = ((g.ball_x - g.crane_x) ** 2 + (g.ball_y - CRANE_Y) ** 2) ** 0.5
        assert dist <= CABLE_LENGTH + 0.01

    def test_released_ball_moves_with_crane_pivot(self) -> None:
        g = _make_game()
        g.ball_released = True
        g.crane_x = 100.0
        g.ball_x = 100.0
        g.ball_y = CRANE_Y + CABLE_LENGTH
        g.ball_vx = 0.0
        g.ball_vy = 0.0
        g._update_physics()
        # move crane
        g.crane_x = 120.0
        g._update_physics()
        # ball should swing toward new pivot
        assert g.ball_vx != 0.0 or g.ball_vy != 0.0 or g.ball_x == 120.0

    def test_released_ball_swings(self) -> None:
        g = _make_game()
        g.ball_released = True
        g.crane_x = 160.0
        g.ball_x = 160.0 + 30.0  # offset horizontally
        g.ball_y = CRANE_Y + CABLE_LENGTH
        g.ball_vx = 0.0
        g.ball_vy = 0.0
        g._update_physics()
        # should have non-zero velocity from pendulum constraint
        assert g.ball_vx != 0.0 or g.ball_vy != 0.0


# --------------------------------------------------------------------------
# Collision Detection
# --------------------------------------------------------------------------
class TestCollisionDetection:
    def test_damage_applied_on_collision(self) -> None:
        g = _make_game()
        seg = _make_segment(x=160.0, y=100.0)
        g.segments.append(seg)
        g.ball_x = 160.0
        g.ball_y = 100.0
        g.ball_released = True
        g._check_ball_collisions()
        assert seg.hp < SEGMENT_HP

    def test_no_damage_when_far(self) -> None:
        g = _make_game()
        seg = _make_segment(x=160.0, y=100.0)
        g.segments.append(seg)
        g.ball_x = 50.0
        g.ball_y = 50.0
        g.ball_released = True
        g._check_ball_collisions()
        assert seg.hp == SEGMENT_HP

    def test_weakened_segment_takes_2x_damage(self) -> None:
        g = _make_game()
        seg = _make_segment(x=160.0, y=100.0, weakened=True)
        g.segments.append(seg)
        g.ball_x = 160.0
        g.ball_y = 100.0
        g.ball_released = True
        g._check_ball_collisions()
        assert seg.hp <= 0.0  # 0.6 * 2 = 1.2 > 1.0, one-shot kill

    def test_normal_segment_dies_in_one_hit(self) -> None:
        g = _make_game()
        seg = _make_segment(x=160.0, y=100.0, weakened=False)
        g.segments.append(seg)
        g.ball_x = 160.0
        g.ball_y = 100.0
        g.ball_released = True
        g._check_ball_collisions()
        assert seg.hp <= 0.0  # 1.0 >= 1.0, dies in one hit

    def test_heat_from_miss(self) -> None:
        g = _make_game()
        g.ball_released = True
        g.heat = 0.0
        g.crane_x = 160.0
        g.ball_x = 160.0 + CABLE_LENGTH * 0.5  # significant swing but no buildings
        g.ball_y = CRANE_Y
        g._check_ball_collisions()
        assert g.heat >= HEAT_MISS

    def test_no_heat_from_miss_when_locked(self) -> None:
        g = _make_game()
        g.ball_released = False
        g.heat = 0.0
        g.ball_x = 160.0
        g.ball_y = CRANE_Y + CABLE_LENGTH
        g._check_ball_collisions()
        assert g.heat == 0.0


# --------------------------------------------------------------------------
# Combo Logic
# --------------------------------------------------------------------------
class TestCombo:
    def test_first_hit_combo_is_1(self) -> None:
        g = _make_game()
        seg = _make_segment(color=BUILDING_COLORS[0])
        g.segments.append(seg)
        g.ball_x = seg.x
        g.ball_y = seg.y - 2
        g.ball_released = True
        g._check_ball_collisions()
        assert g.combo == 1

    def test_same_color_continues_combo(self) -> None:
        g = _make_game()
        g.last_hit_color = BUILDING_COLORS[0]
        g.combo = 2
        seg = _make_segment(color=BUILDING_COLORS[0])
        g.segments.append(seg)
        g.ball_x = seg.x
        g.ball_y = seg.y - 2
        g.ball_released = True
        g._check_ball_collisions()
        assert g.combo == 3

    def test_different_color_resets_combo(self) -> None:
        g = _make_game()
        g.last_hit_color = BUILDING_COLORS[0]
        g.combo = 3
        seg = _make_segment(color=BUILDING_COLORS[1])
        g.segments.append(seg)
        g.ball_x = seg.x
        g.ball_y = seg.y - 2
        g.ball_released = True
        g._check_ball_collisions()
        assert g.combo == 1

    def test_super_mode_always_matches(self) -> None:
        g = _make_game()
        g.super_mode = True
        g.super_timer = 60
        g.last_hit_color = BUILDING_COLORS[0]
        g.combo = 5
        seg = _make_segment(color=BUILDING_COLORS[1])  # different color
        g.segments.append(seg)
        g.ball_x = seg.x
        g.ball_y = seg.y - 2
        g.ball_released = True
        g._check_ball_collisions()
        assert g.combo == 6

    def test_max_combo_tracked(self) -> None:
        g = _make_game()
        g.combo = 0
        g.max_combo = 0
        seg = _make_segment(color=BUILDING_COLORS[0])
        g.segments.append(seg)
        g.ball_x = seg.x
        g.ball_y = seg.y - 2
        g.ball_released = True
        g._check_ball_collisions()
        assert g.max_combo == 1

    def test_combo_4_activates_super(self) -> None:
        g = _make_game()
        g.last_hit_color = BUILDING_COLORS[0]
        g.combo = 3
        g.super_mode = False
        seg = _make_segment(color=BUILDING_COLORS[0])
        g.segments.append(seg)
        g.ball_x = seg.x
        g.ball_y = seg.y - 2
        g._check_ball_collisions()
        assert g.super_mode
        assert g.super_timer == SUPER_DURATION

    def test_super_does_not_re_activate(self) -> None:
        g = _make_game()
        g.super_mode = True
        g.super_timer = 60
        g.last_hit_color = BUILDING_COLORS[0]
        g.combo = 5
        seg = _make_segment(color=BUILDING_COLORS[0])
        g.segments.append(seg)
        g.ball_x = seg.x
        g.ball_y = seg.y - 2
        g._check_ball_collisions()
        assert g.super_timer == 60  # not reset


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------
class TestScoring:
    def test_basic_score_on_destroy(self) -> None:
        g = _make_game()
        seg = _make_segment(color=BUILDING_COLORS[0], hp=0.05)  # will die on first hit
        g.segments.append(seg)
        g.ball_x = seg.x
        g.ball_y = seg.y - 2
        g.score = 0
        g._check_ball_collisions()
        assert g.score > 0

    def test_combo_multiplier_on_score(self) -> None:
        g = _make_game()
        g.last_hit_color = BUILDING_COLORS[0]
        g.combo = 3
        seg = _make_segment(color=BUILDING_COLORS[0], hp=0.05)
        g.segments.append(seg)
        g.ball_x = seg.x
        g.ball_y = seg.y - 2
        g.score = 0
        g._check_ball_collisions()
        assert g.score >= BASE_SCORE * 4  # combo becomes 4, possibly +debris

    def test_super_mode_3x_score(self) -> None:
        g = _make_game()
        g.super_mode = True
        g.super_timer = 60
        g.last_hit_color = BUILDING_COLORS[0]
        g.combo = 3
        seg = _make_segment(color=BUILDING_COLORS[0], hp=0.05)
        g.segments.append(seg)
        g.ball_x = seg.x
        g.ball_y = seg.y - 2
        g.score = 0
        g._check_ball_collisions()
        assert g.score >= BASE_SCORE * 4 * SUPER_MULTIPLIER

    def test_weakened_doubles_score(self) -> None:
        g = _make_game()
        g.combo = 1
        seg = _make_segment(color=BUILDING_COLORS[0], hp=0.05, weakened=True)
        g.segments.append(seg)
        g.ball_x = seg.x
        g.ball_y = seg.y - 2
        g.score = 0
        g._check_ball_collisions()
        assert g.score >= BASE_SCORE * 2 * 2  # combo becomes 2, *2 for weakened

    def test_debris_bonus_on_destroy(self) -> None:
        g = _make_game()
        g.rng = random.Random(123)  # deterministic
        seg = _make_segment(color=BUILDING_COLORS[0], hp=0.05)
        g.segments.append(seg)
        g.ball_x = seg.x
        g.ball_y = seg.y - 2
        g.score = 0
        g._check_ball_collisions()
        # Some debris bonus may be added probabilistically
        assert g.score > 0


# --------------------------------------------------------------------------
# SUPER Mode
# --------------------------------------------------------------------------
class TestSuperMode:
    def test_super_timer_decrements(self) -> None:
        g = _make_game()
        g.super_mode = True
        g.super_timer = 10
        g.phase = Phase.PLAYING
        g._update_super_mode()
        assert g.super_timer == 9

    def test_super_deactivates_at_zero(self) -> None:
        g = _make_game()
        g.super_mode = True
        g.super_timer = 1
        g._update_super_mode()
        assert not g.super_mode
        assert g.super_timer == 0

    def test_super_not_below_zero(self) -> None:
        g = _make_game()
        g.super_mode = False
        g.super_timer = 0
        g._update_super_mode()
        assert g.super_timer == 0


# --------------------------------------------------------------------------
# Building Spawning
# --------------------------------------------------------------------------
class TestBuildingSpawning:
    def test_spawn_creates_segments(self) -> None:
        g = _make_game()
        prev = len(g.segments)
        g._spawn_building()
        assert len(g.segments) > prev

    def test_spawn_segments_in_play_area(self) -> None:
        g = _make_game()
        g._spawn_building()
        for seg in g.segments:
            assert 20 <= seg.x <= SCREEN_W - 20
            assert seg.y <= GROUND_Y

    def test_spawn_respects_max_segments(self) -> None:
        g = _make_game()
        for _ in range(MAX_SEGMENTS + 5):
            g.segments.append(_make_segment())
        g._spawn_building()
        assert len(g.segments) <= MAX_SEGMENTS + 5  # no additional spawn

    def test_spawn_segment_colors_valid(self) -> None:
        g = _make_game()
        g._spawn_building()
        for seg in g.segments:
            assert seg.color in BUILDING_COLORS

    def test_segment_cleanup_removes_dead(self) -> None:
        g = _make_game()
        seg = _make_segment(hp=-1.0)
        g.segments.append(seg)
        g._update_segments()
        assert len(g.segments) == 0

    def test_segment_cleanup_keeps_alive(self) -> None:
        g = _make_game()
        seg = _make_segment(hp=0.5)
        g.segments.append(seg)
        g._update_segments()
        assert len(g.segments) == 1


# --------------------------------------------------------------------------
# Weakening
# --------------------------------------------------------------------------
class TestWeakening:
    def test_adjacent_same_color_weakened(self) -> None:
        g = _make_game()
        destroyed = _make_segment(x=160.0, y=100.0, color=BUILDING_COLORS[0])
        neighbor = _make_segment(x=160.0 + SEGMENT_W, y=100.0, color=BUILDING_COLORS[0])
        g.segments.extend([destroyed, neighbor])
        g._weaken_adjacent(destroyed)
        assert neighbor.weakened

    def test_different_color_not_weakened(self) -> None:
        g = _make_game()
        destroyed = _make_segment(x=160.0, y=100.0, color=BUILDING_COLORS[0])
        neighbor = _make_segment(x=160.0 + SEGMENT_W, y=100.0, color=BUILDING_COLORS[1])
        g.segments.extend([destroyed, neighbor])
        g._weaken_adjacent(destroyed)
        assert not neighbor.weakened

    def test_distant_not_weakened(self) -> None:
        g = _make_game()
        destroyed = _make_segment(x=160.0, y=100.0, color=BUILDING_COLORS[0])
        far = _make_segment(x=300.0, y=200.0, color=BUILDING_COLORS[0])
        g.segments.extend([destroyed, far])
        g._weaken_adjacent(destroyed)
        assert not far.weakened


# --------------------------------------------------------------------------
# HEAT System
# --------------------------------------------------------------------------
class TestHeat:
    def test_heat_decays(self) -> None:
        g = _make_game()
        g.heat = 50.0
        g._update_heat()
        assert g.heat < 50.0

    def test_heat_not_below_zero(self) -> None:
        g = _make_game()
        g.heat = 0.0
        g._update_heat()
        assert g.heat == 0.0

    def test_heat_game_over(self) -> None:
        g = _make_game()
        g.heat = HEAT_MAX
        g._update_heat()
        assert g.phase == Phase.GAME_OVER

    def test_heat_stays_at_max(self) -> None:
        g = _make_game()
        g.heat = HEAT_MAX
        g._update_heat()
        assert g.heat <= HEAT_MAX


# --------------------------------------------------------------------------
# Timer
# --------------------------------------------------------------------------
class TestTimer:
    def test_timer_decrements(self) -> None:
        g = _make_game()
        initial = g.timer
        g._update_timer()
        assert g.timer == initial - 1

    def test_timer_zero_game_over(self) -> None:
        g = _make_game()
        g.timer = 1
        g._update_timer()
        assert g.phase == Phase.GAME_OVER


# --------------------------------------------------------------------------
# Particles
# --------------------------------------------------------------------------
class TestParticles:
    def test_spawn_particles_adds_correct_count(self) -> None:
        g = _make_game()
        seg = _make_segment()
        g._spawn_hit_particles(seg)
        assert len(g.particles) == PARTICLE_HIT_COUNT

    def test_destroy_particles_count(self) -> None:
        g = _make_game()
        seg = _make_segment()
        g._spawn_destroy_particles(seg)
        assert len(g.particles) == PARTICLE_DESTROY_COUNT

    def test_particle_life_decrements(self) -> None:
        g = _make_game()
        g.particles.append(
            Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, color=BUILDING_COLORS[0], life=5, max_life=5)
        )
        g._update_particles()
        assert g.particles[0].life == 4

    def test_dead_particle_removed(self) -> None:
        g = _make_game()
        g.particles.append(
            Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, color=BUILDING_COLORS[0], life=1, max_life=1)
        )
        g._update_particles()
        assert len(g.particles) == 0

    def test_particles_have_gravity(self) -> None:
        g = _make_game()
        g.particles.append(
            Particle(x=100.0, y=100.0, vx=2.0, vy=0.0, color=BUILDING_COLORS[0], life=10, max_life=10)
        )
        g._update_particles()
        assert g.particles[0].x == 102.0
        assert g.particles[0].vy > 0


# --------------------------------------------------------------------------
# Floating Text
# --------------------------------------------------------------------------
class TestFloatingText:
    def test_spawn_floating_text(self) -> None:
        g = _make_game()
        g._spawn_floating_text(160.0, 120.0, "TEST", 7)
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].text == "TEST"

    def test_floating_text_moves_up(self) -> None:
        g = _make_game()
        g._spawn_floating_text(160.0, 120.0, "TEST", 7)
        y0 = g.floating_texts[0].y
        g._update_floating_texts()
        assert g.floating_texts[0].y < y0

    def test_floating_text_expires(self) -> None:
        g = _make_game()
        g._spawn_floating_text(160.0, 120.0, "TEST", 7)
        g.floating_texts[0].life = 1
        g._update_floating_texts()
        assert len(g.floating_texts) == 0

    def test_floating_text_default_life(self) -> None:
        g = _make_game()
        g._spawn_floating_text(160.0, 120.0, "TEST", 7)
        assert g.floating_texts[0].life == 30


# --------------------------------------------------------------------------
# Reset
# --------------------------------------------------------------------------
class TestReset:
    def test_reset_clears_state(self) -> None:
        g = _make_game()
        g.score = 500
        g.combo = 5
        g.max_combo = 5
        g.heat = 80.0
        g.super_mode = True
        g.super_timer = 100
        g.ball_released = True
        g.segments.append(_make_segment())
        g.reset()
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0.0
        assert not g.super_mode
        assert g.super_timer == 0
        assert not g.ball_released
        assert g.phase == Phase.TITLE  # reset goes to TITLE

    def test_reset_spawns_initial_building(self) -> None:
        g = _make_game()
        g.reset()
        assert len(g.segments) > 0

    def test_best_score_preserved(self) -> None:
        g = _make_game()
        g.best_score = 1000
        g.reset()
        assert g.best_score == 1000

    def test_game_over_updates_best_score(self) -> None:
        g = _make_game()
        g.score = 700
        g.best_score = 300
        g._game_over("TEST")
        assert g.best_score == 700
        assert g.phase == Phase.GAME_OVER

    def test_game_over_no_update_when_lower(self) -> None:
        g = _make_game()
        g.score = 200
        g.best_score = 300
        g._game_over("TEST")
        assert g.best_score == 300
