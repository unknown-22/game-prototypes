"""Tests for DEPTH CHAIN prototype."""
from __future__ import annotations

import math
import random

import pytest

from main import (
    COLLECT_RADIUS,
    CREATURE_COLORS,
    DARK_BLUE,
    GAME_DURATION,
    HEAT_DECAY,
    HEAT_DEPTH_RATE,
    HEAT_MAX,
    HEAT_MISMATCH,
    LIFESPAN_START,
    LIME,
    MAX_CREATURES_START,
    RED,
    SCREEN_H,
    SCREEN_W,
    SPAWN_INTERVAL_START,
    SUPER_COLLECT_RADIUS,
    SUPER_DURATION,
    WHITE,
    YELLOW,
    Creature,
    FloatingText,
    Game,
    Particle,
    Phase,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.phase = Phase.PLAYING
    g.player_x = 160.0
    g.player_y = 40.0
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.last_color = None
    g.super_sonar_timer = 0
    g.timer = GAME_DURATION
    g.creatures = []
    g.particles = []
    g.floating_texts = []
    g.best_score = 0
    g._elapsed = 0
    g._spawn_timer = 0
    g._depth_reached = 0.0
    g._shake_offset_x = 0.0
    g._shake_offset_y = 0.0
    g._sonar_pulse_timer = 0
    g._spawn_interval = SPAWN_INTERVAL_START
    g._max_creatures = MAX_CREATURES_START
    g._drift_speed = 0.3
    g._lifespan = LIFESPAN_START
    return g


class TestDataclasses:
    def test_creature_construction(self) -> None:
        c = Creature(x=100.0, y=50.0, color=RED, size=10,
                     vx=0.5, vy=0.3, life=300, seed=1.0)
        assert c.x == 100.0
        assert c.y == 50.0
        assert c.color == RED
        assert c.size == 10
        assert c.vx == 0.5
        assert c.vy == 0.3
        assert c.life == 300
        assert c.seed == 1.0

    def test_particle_construction(self) -> None:
        p = Particle(x=50.0, y=60.0, vx=1.0, vy=-0.5,
                     color=WHITE, life=20, size=2)
        assert p.x == 50.0
        assert p.y == 60.0
        assert p.vx == 1.0
        assert p.vy == -0.5
        assert p.color == WHITE
        assert p.life == 20
        assert p.size == 2

    def test_floating_text_construction(self) -> None:
        ft = FloatingText(x=70.0, y=80.0, text="+10", color=YELLOW,
                          life=45, vy=-1.0)
        assert ft.x == 70.0
        assert ft.y == 80.0
        assert ft.text == "+10"
        assert ft.color == YELLOW
        assert ft.life == 45
        assert ft.vy == -1.0

    def test_phase_enum(self) -> None:
        assert Phase.TITLE != Phase.PLAYING
        assert Phase.PLAYING != Phase.GAME_OVER
        assert Phase.TITLE != Phase.GAME_OVER


class TestFactory:
    def test_make_game_creates_valid_game(self) -> None:
        g = _make_game(42)
        assert g.phase == Phase.PLAYING
        assert g.player_x == 160.0
        assert g.player_y == 40.0
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0.0
        assert g.last_color is None
        assert g.super_sonar_timer == 0
        assert g.timer == GAME_DURATION
        assert g.creatures == []
        assert g.particles == []
        assert g.floating_texts == []
        assert g.best_score == 0


class TestSpawnCreature:
    def test_spawn_creature_returns_valid_creature(self) -> None:
        g = _make_game(42)
        c = g._spawn_creature()
        assert isinstance(c, Creature)
        assert 20 <= c.x <= SCREEN_W - 20
        assert 20 <= c.y <= SCREEN_H - 20
        assert c.color in CREATURE_COLORS
        assert 8 <= c.size <= 14
        assert c.life > 0
        assert isinstance(c.seed, float)

    def test_spawn_bias_places_more_in_deeper_zones(self) -> None:
        g = _make_game(42)
        deep_count = 0
        total = 500
        for _ in range(total):
            c = g._spawn_creature()
            if c.y >= SCREEN_H * 0.5:
                deep_count += 1
        ratio = deep_count / total
        assert ratio > 0.6


class TestUpdateDepth:
    def test_update_depth_surface(self) -> None:
        g = _make_game()
        g.player_y = 0.0
        m = g._update_depth()
        assert m == pytest.approx(1.0)

    def test_update_depth_bottom(self) -> None:
        g = _make_game()
        g.player_y = float(SCREEN_H)
        m = g._update_depth()
        assert m == pytest.approx(3.0)

    def test_update_depth_mid(self) -> None:
        g = _make_game()
        g.player_y = float(SCREEN_H) / 2.0
        m = g._update_depth()
        assert m == pytest.approx(2.0)

    def test_depth_multiplier_affects_score(self) -> None:
        g = _make_game()
        g.player_y = float(SCREEN_H)
        c = Creature(x=g.player_x + 5, y=g.player_y + 5, color=RED,
                     size=10, vx=0, vy=0, life=300, seed=0)
        g._handle_collection(c)
        assert g.score > 10
        g2 = _make_game()
        g2.player_y = 0.0
        c2 = Creature(x=g2.player_x + 5, y=g2.player_y + 5, color=RED,
                      size=10, vx=0, vy=0, life=300, seed=0)
        g2._handle_collection(c2)
        assert g.score > g2.score


class TestHandleCollection:
    def test_first_collection_combo_becomes_one(self) -> None:
        g = _make_game()
        assert g.combo == 0
        assert g.last_color is None
        c = Creature(x=g.player_x + 5, y=g.player_y + 5, color=RED,
                     size=10, vx=0, vy=0, life=300, seed=0)
        g._handle_collection(c)
        assert g.combo == 1
        assert g.score > 0

    def test_same_color_combos_increment(self) -> None:
        g = _make_game()
        for i in range(4):
            c = Creature(x=g.player_x + 5, y=g.player_y + 5, color=RED,
                         size=10, vx=0, vy=0, life=300, seed=0)
            g._handle_collection(c)
        assert g.combo == 4
        assert g.max_combo == 4
        assert g.last_color == RED

    def test_same_color_heat_does_not_increase(self) -> None:
        g = _make_game()
        c = Creature(x=g.player_x + 5, y=g.player_y + 5, color=DARK_BLUE,
                     size=10, vx=0, vy=0, life=300, seed=0)
        g._handle_collection(c)
        g._handle_collection(c)
        assert g.heat == pytest.approx(0.0)
        assert g.combo == 2

    def test_different_color_resets_combo_and_adds_heat(self) -> None:
        g = _make_game()
        c1 = Creature(x=g.player_x + 5, y=g.player_y + 5, color=RED,
                      size=10, vx=0, vy=0, life=300, seed=0)
        g._handle_collection(c1)
        assert g.combo == 1
        assert g.last_color == RED
        c2 = Creature(x=g.player_x + 5, y=g.player_y + 5, color=LIME,
                      size=10, vx=0, vy=0, life=300, seed=0)
        g._handle_collection(c2)
        assert g.combo == 0
        assert g.heat == pytest.approx(HEAT_MISMATCH)

    def test_combo_4_triggers_super_sonar(self) -> None:
        g = _make_game()
        for _ in range(4):
            c = Creature(x=g.player_x + 5, y=g.player_y + 5, color=YELLOW,
                         size=10, vx=0, vy=0, life=300, seed=0)
            g._handle_collection(c)
        assert g.combo == 4
        assert g.super_sonar_timer == SUPER_DURATION

    def test_super_sonar_always_matches_and_uses_3x_multiplier(self) -> None:
        g = _make_game()
        for _ in range(4):
            c = Creature(x=g.player_x + 5, y=g.player_y + 5, color=YELLOW,
                         size=10, vx=0, vy=0, life=300, seed=0)
            g._handle_collection(c)
        assert g.super_sonar_timer == SUPER_DURATION
        score_before = g.score
        c_wrong = Creature(x=g.player_x + 5, y=g.player_y + 5, color=RED,
                           size=10, vx=0, vy=0, life=300, seed=0)
        g._handle_collection(c_wrong)
        assert g.combo == 5
        assert g.heat == pytest.approx(0.0)
        assert g.score > score_before

    def test_max_combo_tracks_highest(self) -> None:
        g = _make_game()
        for _ in range(3):
            c = Creature(x=g.player_x + 5, y=g.player_y + 5, color=LIME,
                         size=10, vx=0, vy=0, life=300, seed=0)
            g._handle_collection(c)
        assert g.max_combo == 3
        c_diff = Creature(x=g.player_x + 5, y=g.player_y + 5, color=RED,
                          size=10, vx=0, vy=0, life=300, seed=0)
        g._handle_collection(c_diff)
        assert g.combo == 0
        assert g.max_combo == 3
        for _ in range(5):
            c2 = Creature(x=g.player_x + 5, y=g.player_y + 5, color=DARK_BLUE,
                          size=10, vx=0, vy=0, life=300, seed=0)
            g._handle_collection(c2)
        assert g.max_combo >= 5


class TestUpdateHeat:
    def test_heat_does_not_increase_at_shallow_depth(self) -> None:
        g = _make_game()
        g.player_y = 40.0
        g._update_heat()
        assert g.heat == pytest.approx(0.0)

    def test_heat_increases_deep(self) -> None:
        g = _make_game()
        g.player_y = float(SCREEN_H) * 0.8
        g.heat = 5.0
        g._update_heat()
        depth_val = g.player_y / SCREEN_H * 100.0
        expected = 5.0 + HEAT_DEPTH_RATE * (depth_val / 100.0) - HEAT_DECAY
        assert g.heat == pytest.approx(expected)

    def test_heat_game_over_triggers(self) -> None:
        g = _make_game()
        g.heat = HEAT_MAX
        g._update_heat()
        assert g.phase == Phase.GAME_OVER

    def test_heat_game_over_checked_before_decay(self) -> None:
        g = _make_game()
        g.heat = 100.0
        g._update_heat()
        assert g.phase == Phase.GAME_OVER

    def test_heat_decays_when_super_sonar_active(self) -> None:
        g = _make_game()
        g.super_sonar_timer = 100
        g.player_y = float(SCREEN_H) * 0.8
        g.heat = 50.0
        g._update_heat()
        assert g.heat == pytest.approx(50.0)

    def test_heat_decays_below_shallow(self) -> None:
        g = _make_game()
        g.player_y = 30.0
        g.heat = 10.0
        g._update_heat()
        assert g.heat == pytest.approx(10.0 - HEAT_DECAY)


class TestUpdateTimer:
    def test_timer_counts_down(self) -> None:
        g = _make_game()
        assert g.timer == GAME_DURATION
        g._update_timer()
        assert g.timer == GAME_DURATION - 1

    def test_timer_zero_triggers_game_over(self) -> None:
        g = _make_game()
        g.timer = 1
        g._update_timer()
        assert g.timer == 0
        g._update_timer()
        assert g.phase == Phase.GAME_OVER


class TestUpdateSuperSonar:
    def test_super_sonar_decrements(self) -> None:
        g = _make_game()
        g.super_sonar_timer = SUPER_DURATION
        g._update_super_sonar()
        assert g.super_sonar_timer == SUPER_DURATION - 1

    def test_super_sonar_deactivates_and_resets_combo(self) -> None:
        g = _make_game()
        g.super_sonar_timer = 1
        g.combo = 5
        g.last_color = RED
        g._update_super_sonar()
        assert g.super_sonar_timer == 0
        assert g.combo == 0
        assert g.last_color is None


class TestUpdateParticles:
    def test_particles_move_and_die(self) -> None:
        g = _make_game()
        g.particles = [
            Particle(x=100.0, y=100.0, vx=1.0, vy=-1.0,
                     color=WHITE, life=2, size=2),
            Particle(x=200.0, y=200.0, vx=0.5, vy=0.5,
                     color=RED, life=2, size=1),
        ]
        g._update_particles()
        assert len(g.particles) == 2
        assert g.particles[0].x == 101.0
        assert g.particles[0].y == 99.0
        assert g.particles[0].life == 1
        g._update_particles()
        assert len(g.particles) == 0

    def test_spawn_particles_creates_correct_count(self) -> None:
        g = _make_game(42)
        g._spawn_particles(160.0, 120.0, RED, 8)
        assert len(g.particles) == 8
        for p in g.particles:
            assert p.color == RED

    def test_spawn_particles_zero_count(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, WHITE, 0)
        assert len(g.particles) == 0


class TestFloatingText:
    def test_floating_texts_move_and_die(self) -> None:
        g = _make_game()
        g.floating_texts = [
            FloatingText(x=100.0, y=100.0, text="+10", color=YELLOW,
                         life=2, vy=-1.0),
        ]
        g._update_floating_texts()
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].y == 99.0
        assert g.floating_texts[0].life == 1
        g._update_floating_texts()
        assert len(g.floating_texts) == 0

    def test_add_floating_text_creates_valid_text(self) -> None:
        g = _make_game()
        g._add_floating_text(120.0, 80.0, "SUPER!", YELLOW)
        assert len(g.floating_texts) == 1
        ft = g.floating_texts[0]
        assert ft.text == "SUPER!"
        assert ft.color == YELLOW
        assert ft.life == 45
        assert ft.vy == -1.0


class TestCheckCollection:
    def test_finds_creature_within_radius(self) -> None:
        g = _make_game()
        c = Creature(x=165.0, y=45.0, color=RED, size=10,
                     vx=0, vy=0, life=300, seed=0)
        g.creatures.append(c)
        result = g._check_collection(160.0, 40.0)
        assert result is c
        assert len(g.creatures) == 0

    def test_returns_none_when_no_creature_nearby(self) -> None:
        g = _make_game()
        c = Creature(x=300.0, y=200.0, color=LIME, size=10,
                     vx=0, vy=0, life=300, seed=0)
        g.creatures.append(c)
        result = g._check_collection(50.0, 50.0)
        assert result is None
        assert len(g.creatures) == 1

    def test_super_sonar_increases_collection_radius(self) -> None:
        g = _make_game()
        g.super_sonar_timer = 100
        c = Creature(x=175.0, y=60.0, color=RED, size=10,
                     vx=0, vy=0, life=300, seed=0)
        g.creatures.append(c)
        dist = math.hypot(c.x - 160, c.y - 40)
        assert dist > COLLECT_RADIUS
        assert dist <= SUPER_COLLECT_RADIUS
        result = g._check_collection(160.0, 40.0)
        assert result is c


class TestDifficulty:
    def test_difficulty_scales_spawn_interval(self) -> None:
        g = _make_game()
        g._elapsed = 0
        g._update_difficulty()
        assert g._spawn_interval == 90
        g._elapsed = GAME_DURATION
        g._update_difficulty()
        assert g._spawn_interval == 30

    def test_difficulty_scales_max_creatures(self) -> None:
        g = _make_game()
        g._elapsed = 0
        g._update_difficulty()
        assert g._max_creatures == 6
        g._elapsed = GAME_DURATION
        g._update_difficulty()
        assert g._max_creatures == 14


class TestReset:
    def test_reset_returns_game_to_initial_state(self) -> None:
        g = _make_game()
        g.score = 500
        g.combo = 3
        g.heat = 80.0
        g.timer = 100
        g._depth_reached = 75.0
        g._start_game()
        assert g.score == 0
        assert g.combo == 0
        assert g.heat == 0.0
        assert g.timer == GAME_DURATION
        assert g._depth_reached == 0.0
        assert g.phase == Phase.PLAYING

    def test_game_over_stores_best_score(self) -> None:
        g = _make_game()
        g.score = 1200
        g.best_score = 800
        g._on_game_over()
        assert g.best_score == 1200
        assert g.phase == Phase.GAME_OVER

    def test_best_score_persists_below_current(self) -> None:
        g = _make_game()
        g.best_score = 2000
        g.score = 500
        g._on_game_over()
        assert g.best_score == 2000
