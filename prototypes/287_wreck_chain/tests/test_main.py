from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (
    BASE_SCORE,
    BUILDING_GAP,
    BUILDING_H_MAX,
    BUILDING_H_MIN,
    BUILDING_W,
    BUILDING_Y,
    COLORS,
    COMBO_SUPER_THRESHOLD,
    FLOAT_TEXT_LIFE,
    GAME_DURATION,
    HEAT_MISMATCH,
    HEAT_MAX,
    HEAT_MISS,
    IMPACT_FRAMES,
    INITIAL_COLOR_CYCLE,
    INITIAL_SPAWN_INTERVAL,
    PARTICLE_COUNT,
    PARTICLE_LIFE,
    PIVOT_X,
    PIVOT_Y,
    RETRACT_FRAMES,
    ROPE_LENGTH,
    SCREEN_H,
    SCREEN_W,
    SLOT_COUNT,
    SPAWN_ANIM_FRAMES,
    SUPER_DURATION,
    Building,
    Game,
    Particle,
    Phase,
    PlayPhase,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(seed)
    g.font = None
    g.phase = Phase.PLAYING
    g.play_phase = PlayPhase.SWINGING
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.super_timer = 0
    g.timer = GAME_DURATION
    g.best_score = 0
    g.buildings = []
    g.particles = []
    g.floating_texts = []
    g.angle = 0.0
    g.angular_velocity = 0.01
    g.holding = False
    g.ball_color_idx = 0
    g.ball_color = COLORS[0]
    g.ball_x = float(PIVOT_X)
    g.ball_y = float(PIVOT_Y + ROPE_LENGTH)
    g.ball_vx = 0.0
    g.ball_vy = 0.0
    g.spawn_timer = 0
    g.color_timer = 0
    g.impact_timer = 0
    g.retract_timer = 0
    g.spawn_interval = INITIAL_SPAWN_INTERVAL
    g.color_cycle_speed = INITIAL_COLOR_CYCLE
    g.shake_frames = 0
    g.rainbow_tick = 0
    return g


def _make_building(x: int, h: int = 50, color: int = COLORS[0]) -> Building:
    return Building(x=x, h=h, color=color, spawn_anim=0)


# --------------------------------------------------------------------------
# Building Spawning
# --------------------------------------------------------------------------
class TestBuildingSpawning:
    def test_spawn_adds_building(self) -> None:
        g = _make_game()
        assert len(g.buildings) == 0
        g._spawn_building()
        assert len(g.buildings) == 1

    def test_spawn_has_valid_color(self) -> None:
        g = _make_game()
        g._spawn_building()
        assert g.buildings[0].color in COLORS

    def test_spawn_has_valid_height(self) -> None:
        g = _make_game()
        g._spawn_building()
        assert BUILDING_H_MIN <= g.buildings[0].h <= BUILDING_H_MAX

    def test_spawn_has_spawn_anim(self) -> None:
        g = _make_game()
        g._spawn_building()
        assert g.buildings[0].spawn_anim == SPAWN_ANIM_FRAMES

    def test_no_spawn_when_all_slots_full(self) -> None:
        g = _make_game()
        for i in range(SLOT_COUNT):
            g.buildings.append(_make_building(g._slot_x(i)))
        g._spawn_building()
        assert len(g.buildings) == SLOT_COUNT

    def test_populate_adds_count_buildings(self) -> None:
        g = _make_game()
        g._populate_buildings(3)
        assert len(g.buildings) == 3

    def test_populate_limits_to_empty_slots(self) -> None:
        g = _make_game()
        for i in range(3):
            g.buildings.append(_make_building(g._slot_x(i)))
        g._populate_buildings(3)
        assert len(g.buildings) == 5  # 5 slots total

    def test_spawn_anim_decrements(self) -> None:
        g = _make_game()
        g._spawn_building()
        assert g.buildings[0].spawn_anim > 0
        g._update_building_anims()
        assert g.buildings[0].spawn_anim == SPAWN_ANIM_FRAMES - 1

    def test_spawn_anim_stays_at_zero(self) -> None:
        g = _make_game()
        b = _make_building(g._slot_x(0))
        b.spawn_anim = 1
        g.buildings.append(b)
        g._update_building_anims()
        assert g.buildings[0].spawn_anim == 0
        g._update_building_anims()
        assert g.buildings[0].spawn_anim == 0

    def test_reset_populates_3_buildings(self) -> None:
        g = _make_game()
        g.reset()
        assert len(g.buildings) == 3

    def test_building_y_computed(self) -> None:
        b = _make_building(0, h=50)
        assert b.y == BUILDING_Y - 50


# --------------------------------------------------------------------------
# Pendulum Physics
# --------------------------------------------------------------------------
class TestPendulumPhysics:
    def test_pendulum_updates_angle(self) -> None:
        g = _make_game()
        g.angle = 0.0
        g.angular_velocity = 0.05
        initial_angle = g.angle
        g._update_pendulum(holding=False)
        assert g.angle != initial_angle

    def test_pendulum_updates_ball_position(self) -> None:
        g = _make_game()
        g._update_pendulum(holding=False)
        assert g.ball_x != PIVOT_X or g.ball_y != PIVOT_Y + ROPE_LENGTH

    def test_holding_increases_angular_velocity(self) -> None:
        g = _make_game()
        g.angular_velocity = 0.01
        g._update_pendulum(holding=True)
        assert g.angular_velocity > 0.01

    def test_holding_increases_negative_angular_velocity(self) -> None:
        g = _make_game()
        g.angular_velocity = -0.01
        g._update_pendulum(holding=True)
        # negative + negative direction = more negative (larger magnitude)
        # Direction for negative velocity is -1, so tension_rate * -1 gets added
        # -0.01 + (-0.0016) = -0.0116, plus gravity accel and damping
        # The exact value depends on physics, but it should be more negative
        assert g.angular_velocity < -0.01

    def test_angle_clamped(self) -> None:
        g = _make_game()
        g.angle = 2.0
        g.angular_velocity = 0.1
        g._update_pendulum(holding=False)
        assert abs(g.angle) <= 2.0

    def test_ball_at_rest_is_below_pivot(self) -> None:
        g = _make_game()
        g.angle = 0.0
        g.angular_velocity = 0.0
        g._update_pendulum(holding=False)
        assert abs(g.ball_x - PIVOT_X) < 1.0
        assert g.ball_y > PIVOT_Y

    def test_damping_reduces_velocity(self) -> None:
        g = _make_game()
        g.angle = 0.3
        g.angular_velocity = 0.05
        g._update_pendulum(holding=False)
        # after one frame with damping, velocity should decrease from gravity+accel
        assert g.angular_velocity < 0.05 + 0.01  # basically check it's damped


# --------------------------------------------------------------------------
# Ball Launch
# --------------------------------------------------------------------------
class TestBallLaunch:
    def test_launch_sets_flying_phase(self) -> None:
        g = _make_game()
        g.angular_velocity = 0.05
        g.angle = 0.5
        g._launch_ball()
        assert g.play_phase == PlayPhase.FLYING

    def test_launch_sets_ball_velocity(self) -> None:
        g = _make_game()
        g.angular_velocity = 0.05
        g._launch_ball()
        assert g.ball_vx != 0.0 or g.ball_vy != 0.0

    def test_flying_updates_position(self) -> None:
        g = _make_game()
        g.play_phase = PlayPhase.FLYING
        g.ball_x = 160.0
        g.ball_y = 100.0
        g.ball_vx = 3.0
        g.ball_vy = 2.0
        g._update_flying()
        assert g.ball_x == 163.0
        assert g.ball_y == 102.0

    def test_flying_applies_gravity(self) -> None:
        g = _make_game()
        g.play_phase = PlayPhase.FLYING
        g.ball_vy = 0.0
        g._update_flying()
        assert g.ball_vy > 0.0

    def test_ball_off_screen_detected(self) -> None:
        g = _make_game()
        g.ball_y = SCREEN_H + 100.0
        assert g._is_ball_off_screen()

    def test_ball_on_screen_not_detected(self) -> None:
        g = _make_game()
        g.ball_x = 160.0
        g.ball_y = 150.0
        assert not g._is_ball_off_screen()


# --------------------------------------------------------------------------
# Hit Detection
# --------------------------------------------------------------------------
class TestHitDetection:
    def test_ball_hits_building(self) -> None:
        g = _make_game()
        b = _make_building(x=100, h=50)
        g.buildings.append(b)
        g.ball_x = 120.0  # center of building
        g.ball_y = float(b.y - 5)  # just above building top
        hit = g._check_building_hit()
        assert hit is not None

    def test_ball_misses_building(self) -> None:
        g = _make_game()
        b = _make_building(x=100, h=50)
        g.buildings.append(b)
        g.ball_x = 200.0
        g.ball_y = 150.0
        hit = g._check_building_hit()
        assert hit is None

    def test_ball_hits_building_side(self) -> None:
        g = _make_game()
        b = _make_building(x=100, h=50)
        g.buildings.append(b)
        g.ball_x = float(b.x) - 3  # near left edge
        g.ball_y = float(b.y + 25)  # middle of building
        hit = g._check_building_hit()
        assert hit is not None

    def test_returns_first_building_hit(self) -> None:
        g = _make_game()
        b1 = _make_building(x=80, h=50, color=COLORS[0])
        b2 = _make_building(x=140, h=50, color=COLORS[1])
        g.buildings.extend([b1, b2])
        g.ball_x = 100.0
        g.ball_y = float(b1.y)
        hit = g._check_building_hit()
        assert hit is b1


# --------------------------------------------------------------------------
# COMBO Logic & Scoring
# --------------------------------------------------------------------------
class TestComboScoring:
    def test_match_builds_combo(self) -> None:
        g = _make_game()
        g.combo = 0
        g.ball_color = COLORS[0]
        b = _make_building(x=100, h=50, color=COLORS[0])
        g.buildings.append(b)
        g._process_hit(b)
        assert g.combo == 1

    def test_match_adds_score(self) -> None:
        g = _make_game()
        g.combo = 0
        g.ball_color = COLORS[0]
        b = _make_building(x=100, h=50, color=COLORS[0])
        g.buildings.append(b)
        g._process_hit(b)
        assert g.score == BASE_SCORE  # 100 * 1 * 1.0 = 100

    def test_combo_2_score(self) -> None:
        g = _make_game()
        g.combo = 1
        g.ball_color = COLORS[0]
        b = _make_building(x=100, h=50, color=COLORS[0])
        g.buildings.append(b)
        g._process_hit(b)
        # combo=2: 100 * 2 * (1 + 0.25*1) = 100 * 2 * 1.25 = 250
        assert g.score == 250

    def test_combo_3_score(self) -> None:
        g = _make_game()
        g.combo = 2
        g.ball_color = COLORS[0]
        b = _make_building(x=100, h=50, color=COLORS[0])
        g.buildings.append(b)
        g._process_hit(b)
        # combo=3: 100 * 3 * (1 + 0.25*2) = 100 * 3 * 1.5 = 450
        assert g.score == 450

    def test_combo_4_score_triggers_super(self) -> None:
        g = _make_game()
        g.combo = 3
        g.ball_color = COLORS[0]
        b = _make_building(x=100, h=50, color=COLORS[0])
        g.buildings.append(b)
        g._process_hit(b)
        # combo=4: 100 * 4 * (1 + 0.25*3) = 100 * 4 * 1.75 = 700
        assert g.score == 700
        assert g.super_timer == SUPER_DURATION

    def test_wrong_color_resets_combo(self) -> None:
        g = _make_game()
        g.combo = 3
        g.ball_color = COLORS[0]
        b = _make_building(x=100, h=50, color=COLORS[1])
        g.buildings.append(b)
        g._process_hit(b)
        assert g.combo == 0

    def test_wrong_color_adds_heat(self) -> None:
        g = _make_game()
        g.heat = 10.0
        g.ball_color = COLORS[0]
        b = _make_building(x=100, h=50, color=COLORS[1])
        g.buildings.append(b)
        g._process_hit(b)
        assert g.heat == 10.0 + HEAT_MISMATCH

    def test_wrong_color_no_score(self) -> None:
        g = _make_game()
        g.score = 100
        g.ball_color = COLORS[0]
        b = _make_building(x=100, h=50, color=COLORS[1])
        g.buildings.append(b)
        g._process_hit(b)
        assert g.score == 100

    def test_removes_building_on_hit(self) -> None:
        g = _make_game()
        b = _make_building(x=100, h=50, color=COLORS[0])
        g.buildings.append(b)
        g._process_hit(b)
        assert len(g.buildings) == 0

    def test_miss_adds_heat(self) -> None:
        g = _make_game()
        g.heat = 10.0
        g._handle_miss()
        assert g.heat == 10.0 + HEAT_MISS

    def test_miss_resets_combo(self) -> None:
        g = _make_game()
        g.combo = 3
        g._handle_miss()
        assert g.combo == 0

    def test_max_combo_tracked(self) -> None:
        g = _make_game()
        g.ball_color = COLORS[0]
        for i in range(3):
            b = _make_building(x=g._slot_x(i), h=50, color=COLORS[0])
            g.buildings.append(b)
            g._process_hit(b)
        assert g.max_combo == 3

    def test_spawns_particles_on_match(self) -> None:
        g = _make_game()
        g.ball_color = COLORS[0]
        b = _make_building(x=100, h=50, color=COLORS[0])
        g.buildings.append(b)
        g._process_hit(b)
        assert len(g.particles) == PARTICLE_COUNT

    def test_spawns_floating_text_on_match(self) -> None:
        g = _make_game()
        g.ball_color = COLORS[0]
        b = _make_building(x=100, h=50, color=COLORS[0])
        g.buildings.append(b)
        g._process_hit(b)
        assert len(g.floating_texts) >= 1

    def test_spawns_wrong_text_on_mismatch(self) -> None:
        g = _make_game()
        g.ball_color = COLORS[0]
        b = _make_building(x=100, h=50, color=COLORS[1])
        g.buildings.append(b)
        g._process_hit(b)
        has_wrong = any("WRONG" in ft.text for ft in g.floating_texts)
        assert has_wrong

    def test_sets_impact_phase_on_hit(self) -> None:
        g = _make_game()
        g.ball_color = COLORS[0]
        b = _make_building(x=100, h=50, color=COLORS[0])
        g.buildings.append(b)
        g._process_hit(b)
        assert g.play_phase == PlayPhase.IMPACT
        assert g.impact_timer == IMPACT_FRAMES


# --------------------------------------------------------------------------
# SUPER Wreck
# --------------------------------------------------------------------------
class TestSuperWreck:
    def test_combo_4_activates_super(self) -> None:
        g = _make_game()
        g.combo = COMBO_SUPER_THRESHOLD - 1  # combo will become 4 after hit
        g.ball_color = COLORS[0]
        b = _make_building(x=100, h=50, color=COLORS[0])
        g.buildings.append(b)
        g._process_hit(b)
        assert g.super_timer == SUPER_DURATION

    def test_super_allows_any_color(self) -> None:
        g = _make_game()
        g.super_timer = SUPER_DURATION
        g.combo = 1
        g.ball_color = COLORS[0]
        b = _make_building(x=100, h=50, color=COLORS[1])  # different color
        g.buildings.append(b)
        g._process_hit(b)
        assert g.combo == 2  # should match despite color mismatch

    def test_super_3x_score(self) -> None:
        g = _make_game()
        g.super_timer = SUPER_DURATION
        g.combo = 1
        g.ball_color = COLORS[0]
        b = _make_building(x=100, h=50, color=COLORS[0])
        g.buildings.append(b)
        g._process_hit(b)
        # combo=2: 100 * 2 * 1.25 * 3 = 750
        assert g.score == 750

    def test_super_timer_decrements(self) -> None:
        g = _make_game()
        g.super_timer = 10
        g.update()
        assert g.super_timer == 9

    def test_super_deactivates(self) -> None:
        g = _make_game()
        g.super_timer = 1
        g.update()
        assert g.super_timer == 0
        assert not g.is_super

    def test_super_spawns_text(self) -> None:
        g = _make_game()
        g.combo = COMBO_SUPER_THRESHOLD - 1
        g.ball_color = COLORS[0]
        b = _make_building(x=100, h=50, color=COLORS[0])
        g.buildings.append(b)
        g._process_hit(b)
        has_super = any("SUPER WRECK" in ft.text for ft in g.floating_texts)
        assert has_super

    def test_super_does_not_re_activate(self) -> None:
        g = _make_game()
        g.super_timer = SUPER_DURATION
        g.combo = COMBO_SUPER_THRESHOLD - 1
        g.ball_color = COLORS[0]
        b = _make_building(x=100, h=50, color=COLORS[0])
        g.buildings.append(b)
        g._process_hit(b)
        # super_timer should NOT be reset (should stay at SUPER_DURATION - decrement in update)
        assert g.super_timer == SUPER_DURATION  # hasn't been decremented yet


# --------------------------------------------------------------------------
# Heat
# --------------------------------------------------------------------------
class TestHeat:
    def test_heat_decays(self) -> None:
        g = _make_game()
        g.heat = 50.0
        g._update_heat()
        assert g.heat < 50.0

    def test_heat_floor_zero(self) -> None:
        g = _make_game()
        g.heat = 0.0
        g._update_heat()
        assert g.heat == 0.0

    def test_heat_ceiling_100(self) -> None:
        g = _make_game()
        g.heat = HEAT_MAX + 10.0
        g._update_heat()
        assert g.heat <= HEAT_MAX

    def test_heat_100_game_over(self) -> None:
        g = _make_game()
        g.heat = HEAT_MAX
        g.update()
        assert g.phase == Phase.GAME_OVER

    def test_mismatch_adds_15_heat(self) -> None:
        g = _make_game()
        g.ball_color = COLORS[0]
        b = _make_building(x=100, h=50, color=COLORS[1])
        g.buildings.append(b)
        g._process_hit(b)
        assert g.heat == HEAT_MISMATCH

    def test_miss_adds_5_heat(self) -> None:
        g = _make_game()
        g._handle_miss()
        assert g.heat == HEAT_MISS

    def test_match_does_not_add_heat(self) -> None:
        g = _make_game()
        g.heat = 10.0
        g.ball_color = COLORS[0]
        b = _make_building(x=100, h=50, color=COLORS[0])
        g.buildings.append(b)
        g._process_hit(b)
        assert g.heat == 10.0


# --------------------------------------------------------------------------
# Timer
# --------------------------------------------------------------------------
class TestTimer:
    def test_timer_decrements(self) -> None:
        g = _make_game()
        initial = g.timer
        g.update()
        assert g.timer == initial - 1

    def test_timer_zero_game_over(self) -> None:
        g = _make_game()
        g.timer = 1
        g.update()
        assert g.phase == Phase.GAME_OVER

    def test_timer_not_below_zero(self) -> None:
        g = _make_game()
        g.timer = 0
        g.update()
        assert g.timer == 0


# --------------------------------------------------------------------------
# Difficulty
# --------------------------------------------------------------------------
class TestDifficulty:
    def test_progress_zero_at_start(self) -> None:
        g = _make_game()
        g.timer = GAME_DURATION
        assert g._progress() == 0.0

    def test_progress_one_at_end(self) -> None:
        g = _make_game()
        g.timer = 0
        assert g._progress() == 1.0

    def test_spawn_interval_decreases(self) -> None:
        g = _make_game()
        g.timer = GAME_DURATION
        g._update_difficulty()
        early = g.spawn_interval
        g.timer = 1
        g._update_difficulty()
        late = g.spawn_interval
        assert late <= early

    def test_color_cycle_decreases(self) -> None:
        g = _make_game()
        g.timer = GAME_DURATION
        g._update_difficulty()
        early = g.color_cycle_speed
        g.timer = 1
        g._update_difficulty()
        late = g.color_cycle_speed
        assert late <= early


# --------------------------------------------------------------------------
# Color Cycle
# --------------------------------------------------------------------------
class TestColorCycle:
    def test_color_changes_after_cycle(self) -> None:
        g = _make_game()
        g.ball_color_idx = 0
        g.ball_color = COLORS[0]
        g.color_timer = 1
        g._update_color_cycle()
        assert g.ball_color != COLORS[0]

    def test_color_cycle_wraps(self) -> None:
        g = _make_game()
        g.ball_color_idx = len(COLORS) - 1
        g.ball_color = COLORS[-1]
        g.color_timer = 1
        g._update_color_cycle()
        assert g.ball_color_idx == 0
        assert g.ball_color == COLORS[0]

    def test_color_cycle_disabled_in_super(self) -> None:
        g = _make_game()
        g.super_timer = SUPER_DURATION
        g.ball_color_idx = 0
        g.ball_color = COLORS[0]
        g.color_timer = 1
        g._update_color_cycle()
        assert g.ball_color == COLORS[0]  # should not change


# --------------------------------------------------------------------------
# Particles
# --------------------------------------------------------------------------
class TestParticles:
    def test_spawn_particles_creates_correct_count(self) -> None:
        g = _make_game()
        g._spawn_particles(160.0, 120.0, COLORS[0])
        assert len(g.particles) == PARTICLE_COUNT

    def test_particle_life_decrements(self) -> None:
        g = _make_game()
        g.particles.append(Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, color=COLORS[0], life=5))
        g._update_particles()
        assert g.particles[0].life == 4

    def test_dead_particle_removed(self) -> None:
        g = _make_game()
        g.particles.append(Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, color=COLORS[0], life=1))
        g._update_particles()
        assert len(g.particles) == 0

    def test_particles_move_and_gravity(self) -> None:
        g = _make_game()
        g.particles.append(Particle(x=100.0, y=100.0, vx=2.0, vy=0.0, color=COLORS[0], life=10))
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
        initial_y = g.floating_texts[0].y
        g._update_floating_texts()
        assert g.floating_texts[0].y < initial_y

    def test_floating_text_expires(self) -> None:
        g = _make_game()
        g._spawn_floating_text(160.0, 120.0, "TEST", 7)
        g.floating_texts[0].life = 1
        g._update_floating_texts()
        assert len(g.floating_texts) == 0

    def test_float_text_has_correct_life(self) -> None:
        g = _make_game()
        g._spawn_floating_text(160.0, 120.0, "TEST", 7)
        assert g.floating_texts[0].life == FLOAT_TEXT_LIFE


# --------------------------------------------------------------------------
# Retract & Reset
# --------------------------------------------------------------------------
class TestRetract:
    def test_handle_miss_sets_retract(self) -> None:
        g = _make_game()
        g._handle_miss()
        assert g.play_phase == PlayPhase.RETRACT
        assert g.retract_timer == RETRACT_FRAMES

    def test_retract_ends_at_zero(self) -> None:
        g = _make_game()
        g.play_phase = PlayPhase.RETRACT
        g.retract_timer = 1
        g._update_retract()
        assert g.play_phase == PlayPhase.SWINGING

    def test_reset_ball_sets_swinging(self) -> None:
        g = _make_game()
        g.play_phase = PlayPhase.RETRACT
        g._reset_ball_to_pivot()
        assert g.play_phase == PlayPhase.SWINGING
        assert g.holding is False
        assert g.ball_vx == 0.0
        assert g.ball_vy == 0.0

    def test_retract_populates_minimum_buildings(self) -> None:
        g = _make_game()
        g.buildings = []
        g.play_phase = PlayPhase.RETRACT
        g.retract_timer = 1
        g._update_retract()
        assert len(g.buildings) >= 2

    def test_retract_no_extra_spawn_if_enough(self) -> None:
        g = _make_game()
        for i in range(3):
            g.buildings.append(_make_building(g._slot_x(i)))
        g.play_phase = PlayPhase.RETRACT
        g.retract_timer = 1
        g._update_retract()
        assert len(g.buildings) == 3  # already 3, no change


# --------------------------------------------------------------------------
# Phase Transitions
# --------------------------------------------------------------------------
class TestPhaseTransitions:
    def test_impact_transitions_to_retract(self) -> None:
        g = _make_game()
        g.play_phase = PlayPhase.IMPACT
        g.impact_timer = 1
        g.update()
        assert g.play_phase == PlayPhase.RETRACT

    def test_flying_miss_off_screen(self) -> None:
        g = _make_game()
        g.play_phase = PlayPhase.FLYING
        g.ball_y = SCREEN_H + 100.0
        g.buildings = []
        g.update()
        assert g.play_phase == PlayPhase.RETRACT

    def test_flying_hit_building(self) -> None:
        g = _make_game()
        g.play_phase = PlayPhase.FLYING
        g.ball_x = 100.0
        g.ball_y = float(BUILDING_Y - 30)
        g.buildings.append(_make_building(x=80, h=50))
        g.update()
        assert g.play_phase == PlayPhase.IMPACT


# --------------------------------------------------------------------------
# Reset
# --------------------------------------------------------------------------
class TestReset:
    def test_reset_clears_score(self) -> None:
        g = _make_game()
        g.score = 500
        g.combo = 5
        g.heat = 50.0
        g.reset()
        assert g.score == 0
        assert g.combo == 0
        assert g.heat == 0.0
        assert g.phase == Phase.PLAYING

    def test_reset_clears_buildings(self) -> None:
        g = _make_game()
        g.buildings.append(_make_building(x=100, h=50))
        g.reset()
        assert len(g.buildings) == 3  # populated by reset

    def test_best_score_preserved_on_reset(self) -> None:
        g = _make_game()
        g.best_score = 1000
        g.reset()
        assert g.best_score == 1000

    def test_end_game_updates_best_score(self) -> None:
        g = _make_game()
        g.score = 500
        g.best_score = 300
        g._end_game()
        assert g.best_score == 500
        assert g.phase == Phase.GAME_OVER

    def test_end_game_no_update_when_lower(self) -> None:
        g = _make_game()
        g.score = 200
        g.best_score = 300
        g._end_game()
        assert g.best_score == 300

    def test_end_game_on_timeout(self) -> None:
        g = _make_game()
        g.timer = 1
        g.update()
        assert g.phase == Phase.GAME_OVER


# --------------------------------------------------------------------------
# Integration: Full swing-launch-hit cycle simulation
# --------------------------------------------------------------------------
class TestFullCycle:
    def test_swing_to_launch_to_hit(self) -> None:
        g = _make_game()
        g.angle = 0.3
        g.angular_velocity = 0.04
        b = _make_building(x=100, h=50, color=g.ball_color)
        g.buildings.append(b)
        g._launch_ball()
        assert g.play_phase == PlayPhase.FLYING
        # Simulate flying toward building
        g.ball_x = b.x + b.w / 2
        g.ball_y = float(b.y - 5)
        g.ball_vy = 5.0
        g.update()
        # Should have hit the building
        assert g.play_phase in (PlayPhase.IMPACT, PlayPhase.RETRACT)
