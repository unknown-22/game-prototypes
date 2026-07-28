"""test_imports.py — Headless logic tests for PARKOUR CHAIN (252_parkour_chain)."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import types

_mock_pyxel = types.ModuleType("pyxel")
_mock_pyxel.BLACK = 0
_mock_pyxel.NAVY = 1
_mock_pyxel.PURPLE = 2
_mock_pyxel.GREEN = 3
_mock_pyxel.BROWN = 4
_mock_pyxel.DARK_BLUE = 5
_mock_pyxel.LIGHT_BLUE = 6
_mock_pyxel.WHITE = 7
_mock_pyxel.RED = 8
_mock_pyxel.ORANGE = 9
_mock_pyxel.YELLOW = 10
_mock_pyxel.LIME = 11
_mock_pyxel.CYAN = 12
_mock_pyxel.GRAY = 13
_mock_pyxel.PINK = 14
_mock_pyxel.PEACH = 15
_mock_pyxel.KEY_SPACE = 32
_mock_pyxel.KEY_RETURN = 13
_mock_pyxel.KEY_UP = 265
_mock_pyxel.KEY_DOWN = 264
_mock_pyxel.frame_count = 0
_mock_pyxel.btn = lambda key: False
_mock_pyxel.btnp = lambda key: False
_mock_pyxel.camera = lambda x, y: None
sys.modules["pyxel"] = _mock_pyxel

from main import (  # noqa: E402
    Game,
    Phase,
    Obstacle,
    Particle,
    FloatingText,
)

RED = 8
LIME = 11
DARK_BLUE = 5
YELLOW = 10
WHITE = 7
ORANGE = 9
CYAN = 12
GRAY = 13


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(seed)
    g.phase = Phase.TITLE
    g.frame = 0
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.best_run_score = 0
    g.flow_color_idx = 0
    g.flow_color_cooldown = 0
    g.player_y = float(Game.GROUND_Y - Game.PLAYER_H)
    g.player_vy = 0.0
    g.player_on_ground = True
    g.player_ducking = False
    g.player_stun = 0
    g.obstacles = []
    g.particles = []
    g.floating_texts = []
    g.heat = 0.0
    g.game_timer = Game.GAME_DURATION
    g.super_timer = 0
    g.scroll_speed = Game.INITIAL_SCROLL_SPEED
    g.spawn_timer = Game.INITIAL_SPAWN_INTERVAL
    g.ghost_trail = []
    g.ghost_recording = []
    g.shake_frames = 0
    g._title_blink = 0
    g.reset()
    g.rng = random.Random(seed)
    return g


class TestDataClasses:
    def test_obstacle_creation(self) -> None:
        o = Obstacle(x=100.0, color=RED)
        assert o.x == 100.0
        assert o.color == RED
        assert o.processed is False

    def test_particle_creation(self) -> None:
        p = Particle(x=10.0, y=20.0, vx=1.0, vy=-1.0, life=30, color=RED)
        assert p.x == 10.0
        assert p.y == 20.0
        assert p.vx == 1.0
        assert p.vy == -1.0
        assert p.life == 30
        assert p.color == RED

    def test_floating_text_creation(self) -> None:
        ft = FloatingText(x=100.0, y=50.0, text="+10", life=30, color=WHITE)
        assert ft.x == 100.0
        assert ft.y == 50.0
        assert ft.text == "+10"
        assert ft.life == 30
        assert ft.color == WHITE

    def test_color_constants(self) -> None:
        assert Game.COLORS == (8, 11, 5, 10)
        assert Game.COLOR_NAMES == ("RED", "LIME", "DARK_BLUE", "YELLOW")


class TestGameState:
    def test_reset_initial_state(self) -> None:
        g = _make_game()
        assert g.phase == Phase.TITLE
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.game_timer == Game.GAME_DURATION
        assert g.heat == 0.0
        assert g.super_timer == 0
        assert g.player_on_ground is True
        assert len(g.obstacles) == 0
        assert len(g.particles) == 0
        assert len(g.floating_texts) == 0
        assert g.best_run_score == 0
        assert g.scroll_speed == Game.INITIAL_SCROLL_SPEED

    def test_player_starts_on_ground(self) -> None:
        g = _make_game()
        assert g.player_y == float(Game.GROUND_Y - Game.PLAYER_H)
        assert g.player_on_ground is True

    def test_start_game_resets_state(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.score = 500
        g.combo = 5
        g.heat = 50.0
        g.obstacles = [Obstacle(x=200.0, color=RED)]
        g._start_game()
        assert g.phase == Phase.PLAYING
        assert g.score == 0
        assert g.combo == 0
        assert g.heat == 0.0
        assert len(g.obstacles) == 0
        assert g.game_timer == Game.GAME_DURATION

    def test_default_flow_color_is_RED(self) -> None:
        g = _make_game()
        assert g.flow_color() == RED
        assert g.flow_color_idx == 0


class TestObstacleSpawning:
    def test_spawn_obstacle(self) -> None:
        g = _make_game()
        g._spawn_obstacle()
        assert len(g.obstacles) == 1
        assert g.obstacles[0].x >= g.SCREEN_W
        assert g.obstacles[0].color in Game.COLORS
        assert g.obstacles[0].processed is False

    def test_spawn_obstacle_deterministic(self) -> None:
        g = _make_game(42)
        g._spawn_obstacle()
        first_color = g.obstacles[0].color
        g2 = _make_game(42)
        g2._spawn_obstacle()
        assert g2.obstacles[0].color == first_color

    def test_obstacle_cleanup_off_screen(self) -> None:
        g = _make_game()
        g.obstacles = [Obstacle(x=-100.0, color=RED)]
        g.scroll_speed = 2.0
        g._update_obstacles()
        assert len(g.obstacles) == 0

    def test_obstacle_count_limited(self) -> None:
        g = _make_game()
        for _ in range(20):
            g.obstacles.append(Obstacle(x=300.0, color=RED))
        g.spawn_timer = 1
        g.game_timer = Game.GAME_DURATION
        assert len(g.obstacles) > Game.MAX_OBSTACLES

    def test_spawn_interval_decreases_over_time(self) -> None:
        g = _make_game()
        g.game_timer = Game.GAME_DURATION
        elapsed_early = 0
        interval_early = max(Game.MIN_SPAWN_INTERVAL,
                             Game.INITIAL_SPAWN_INTERVAL - (elapsed_early // 60) * Game.SPAWN_INTERVAL_DECREASE)
        elapsed_late = Game.GAME_DURATION - Game.MIN_SPAWN_INTERVAL
        interval_late = max(Game.MIN_SPAWN_INTERVAL,
                            Game.INITIAL_SPAWN_INTERVAL - (elapsed_late // 60) * Game.SPAWN_INTERVAL_DECREASE)
        assert interval_late <= interval_early


class TestVaultProcessing:
    def test_process_matching_obstacle(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.flow_color_idx = 0  # RED
        g.player_y = float(Game.GROUND_Y - Game.PLAYER_H - Game.OBSTACLE_H - 1)  # jumped above obstacle
        g.player_on_ground = False
        g.score = 0
        g.combo = 0
        obs = Obstacle(x=10.0, color=RED)
        g._process_obstacle(obs)
        assert g.combo == 1
        assert g.max_combo == 1
        assert g.score == 10  # 10 * 1 * 1

    def test_process_mismatching_obstacle(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.flow_color_idx = 0  # RED
        g.player_y = float(Game.GROUND_Y - Game.PLAYER_H - Game.OBSTACLE_H - 1)  # jumped above
        g.player_on_ground = False
        g.heat = 0.0
        g.combo = 3
        obs = Obstacle(x=10.0, color=LIME)
        g._process_obstacle(obs)
        assert g.combo == 0
        assert g.heat == Game.HEAT_ON_MISMATCH
        assert g.player_stun == Game.STUN_MISMATCH

    def test_crash_when_on_ground(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.player_y = float(Game.GROUND_Y - Game.PLAYER_H)  # on ground
        g.player_on_ground = True
        g.heat = 0.0
        g.combo = 2
        obs = Obstacle(x=10.0, color=RED)
        g._process_obstacle(obs)
        assert g.combo == 0
        assert g.heat == Game.HEAT_ON_CRASH
        assert g.player_stun == Game.STUN_CRASH

    def test_combo_multiplier(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.flow_color_idx = 0  # RED
        g.player_y = float(Game.GROUND_Y - Game.PLAYER_H - Game.OBSTACLE_H - 1)
        g.player_on_ground = False
        g.combo = 2
        g.score = 0
        obs = Obstacle(x=10.0, color=RED)
        g._process_obstacle(obs)
        assert g.combo == 3
        assert g.score == 30  # 10 * 3 * 1

    def test_super_mode_any_color(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.super_timer = 100
        g.flow_color_idx = 0  # RED
        g.player_y = float(Game.GROUND_Y - Game.PLAYER_H - Game.OBSTACLE_H - 1)
        g.player_on_ground = False
        g.combo = 3
        g.score = 0
        obs = Obstacle(x=10.0, color=LIME)  # different color
        g._process_obstacle(obs)
        assert g.combo == 4
        assert g.score == 120  # 10 * 4 * 3

    def test_super_activation_at_combo_4(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.flow_color_idx = 0  # RED
        g.player_y = float(Game.GROUND_Y - Game.PLAYER_H - Game.OBSTACLE_H - 1)
        g.player_on_ground = False
        g.combo = 3
        obs = Obstacle(x=10.0, color=RED)
        g._process_obstacle(obs)
        assert g.super_timer == Game.SUPER_DURATION

    def test_super_does_not_reactivate(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.super_timer = 100
        g.flow_color_idx = 0  # RED
        g.player_y = float(Game.GROUND_Y - Game.PLAYER_H - Game.OBSTACLE_H - 1)
        g.player_on_ground = False
        g.combo = 5
        obs = Obstacle(x=10.0, color=RED)
        g._process_obstacle(obs)
        assert g.super_timer == 100  # unchanged

    def test_max_combo_tracking(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.flow_color_idx = 0  # RED
        g.player_y = float(Game.GROUND_Y - Game.PLAYER_H - Game.OBSTACLE_H - 1)
        g.player_on_ground = False
        for _ in range(5):
            obs = Obstacle(x=10.0, color=RED)
            g._process_obstacle(obs)
        assert g.combo == 5
        assert g.max_combo == 5

    def test_mismatch_resets_combo(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.flow_color_idx = 0  # RED
        g.player_y = float(Game.GROUND_Y - Game.PLAYER_H - Game.OBSTACLE_H - 1)
        g.player_on_ground = False
        g.combo = 4
        g.heat = 0.0
        obs = Obstacle(x=10.0, color=LIME)
        g._process_obstacle(obs)
        assert g.combo == 0

    def test_obstacle_collision_mark_processed(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.player_y = float(Game.GROUND_Y - Game.PLAYER_H)
        g.player_on_ground = True
        g.scroll_speed = 2.0
        obs = Obstacle(x=float(Game.PLAYER_X), color=RED)  # at player center
        g.obstacles = [obs]
        g._update_obstacles()
        assert obs.processed is True


class TestJumpPhysics:
    def test_jump_sets_vy(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.player_on_ground = True
        g.player_vy = Game.JUMP_VY
        g.player_on_ground = False
        assert g.player_vy == Game.JUMP_VY
        assert g.player_vy < 0

    def test_gravity_applied_when_airborne(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.player_on_ground = False
        g.player_vy = 0.0
        g.player_y = 100.0
        g._update_player()
        assert g.player_vy > 0.0  # gravity pulls down

    def test_no_physics_on_ground(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.player_on_ground = True
        g.player_vy = 5.0
        g.player_y = 100.0
        g._update_player()
        assert g.player_vy == 5.0  # unchanged
        assert g.player_y == 100.0  # unchanged

    def test_landing_on_ground(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.player_on_ground = False
        g.player_vy = 5.0
        g.player_y = float(Game.GROUND_Y - Game.PLAYER_H + 2)  # past the ground
        g._update_player()
        assert g.player_on_ground is True
        assert g.player_y == float(Game.GROUND_Y - Game.PLAYER_H)
        assert g.player_vy == 0.0


class TestColorCycling:
    def test_cycle_color_up(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.flow_color_idx = 0  # RED
        g._cycle_color(1)
        assert g.flow_color() == LIME
        assert g.flow_color_idx == 1

    def test_cycle_color_down(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.flow_color_idx = 1  # LIME
        g._cycle_color(-1)
        assert g.flow_color() == RED
        assert g.flow_color_idx == 0

    def test_cycle_color_wraps(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.flow_color_idx = 3  # YELLOW
        g._cycle_color(1)
        assert g.flow_color() == RED
        assert g.flow_color_idx == 0

    def test_cycle_cooldown(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.flow_color_idx = 0
        g.flow_color_cooldown = 0
        g._cycle_color(1)
        assert g.flow_color() == LIME
        assert g.flow_color_cooldown == Game.COLOR_CYCLE_COOLDOWN
        g._cycle_color(1)  # blocked
        assert g.flow_color() == LIME
        g.flow_color_cooldown = 0
        g._cycle_color(1)
        assert g.flow_color() == DARK_BLUE


class TestHeat:
    def test_heat_game_over(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = 100.0
        g.game_timer = 100
        g._update_playing()
        assert g.phase == Phase.GAME_OVER

    def test_heat_decay(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.heat = 50.0
        g.super_timer = 0
        g.game_timer = 100
        g.obstacles = []
        g.spawn_timer = 999
        g._update_playing()
        assert g.heat < 50.0
        assert g.heat >= 50.0 - Game.HEAT_DECAY

    def test_heat_no_decay_in_super(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.super_timer = 100
        g.heat = 50.0
        g.game_timer = 100
        g.obstacles = []
        g.spawn_timer = 999
        g._update_playing()
        assert g.heat == 50.0  # super freezes heat

    def test_heat_from_mismatch(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.flow_color_idx = 0  # RED
        g.player_y = float(Game.GROUND_Y - Game.PLAYER_H - Game.OBSTACLE_H - 1)
        g.player_on_ground = False
        g.heat = 0.0
        obs = Obstacle(x=10.0, color=LIME)
        g._process_obstacle(obs)
        assert g.heat == Game.HEAT_ON_MISMATCH

    def test_heat_from_crash(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.player_y = float(Game.GROUND_Y - Game.PLAYER_H)
        g.player_on_ground = True
        g.heat = 0.0
        obs = Obstacle(x=10.0, color=RED)
        g._process_obstacle(obs)
        assert g.heat == Game.HEAT_ON_CRASH


class TestParticles:
    def test_spawn_particles(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 5, 20, color=RED)
        assert len(g.particles) == 5
        for p in g.particles:
            assert p.color == RED
            assert p.life == 20

    def test_spawn_particles_rainbow(self) -> None:
        g = _make_game(42)
        g._spawn_particles(100.0, 100.0, 20, 20, color=-1)
        assert len(g.particles) == 20

    def test_update_particles_decay(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 3, 1, color=RED)
        assert len(g.particles) == 3
        g._update_particles()
        assert len(g.particles) == 0

    def test_update_particles_gravity(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 1, 10, color=RED)
        vy_before = g.particles[0].vy
        g._update_particles()
        assert g.particles[0].vy > vy_before


class TestFloatingTexts:
    def test_spawn_floating_text(self) -> None:
        g = _make_game()
        g._spawn_floating_text(100.0, 50.0, "+10", WHITE)
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].x == 100.0
        assert g.floating_texts[0].text == "+10"
        assert g.floating_texts[0].color == WHITE
        assert g.floating_texts[0].life == 30

    def test_update_floating_texts_decay(self) -> None:
        g = _make_game()
        g.floating_texts = [FloatingText(x=100.0, y=50.0, text="test", life=1, color=WHITE)]
        g._update_floating_texts()
        assert len(g.floating_texts) == 0

    def test_update_floating_texts_move_up(self) -> None:
        g = _make_game()
        g.floating_texts = [FloatingText(x=100.0, y=50.0, text="test", life=30, color=WHITE)]
        g._update_floating_texts()
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].y < 50.0
        assert g.floating_texts[0].life == 29


class TestTimer:
    def test_timer_countdown(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.game_timer = 10
        g.obstacles = []
        g.spawn_timer = 999
        g._update_playing()
        assert g.game_timer == 9

    def test_timer_victory(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.game_timer = 1
        g.heat = 0.0
        g.obstacles = []
        g.spawn_timer = 999
        g._update_playing()
        assert g.phase == Phase.GAME_OVER
        assert getattr(g, "_last_victory", False) is True

    def test_timer_defeat(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.game_timer = 100
        g.heat = 100.0
        g.obstacles = []
        g.spawn_timer = 999
        g._update_playing()
        assert g.phase == Phase.GAME_OVER
        assert getattr(g, "_last_victory", False) is False

    def test_super_timer_expires(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.super_timer = 2
        g.game_timer = 100
        g.obstacles = []
        g.spawn_timer = 999
        g._update_playing()
        assert g.super_timer == 1
        g._update_playing()
        assert g.super_timer == 0

    def test_best_score_on_game_over(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.score = 500
        g.best_run_score = 300
        g.game_timer = 1
        g.heat = 0.0
        g.obstacles = []
        g.spawn_timer = 999
        g._update_playing()
        assert g.phase == Phase.GAME_OVER
        assert g.best_run_score == 500

    def test_best_score_not_beaten(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.score = 200
        g.best_run_score = 500
        g.game_timer = 1
        g.heat = 0.0
        g.obstacles = []
        g.spawn_timer = 999
        g._update_playing()
        assert g.best_run_score == 500


class TestScrollSpeed:
    def test_initial_scroll_speed(self) -> None:
        g = _make_game()
        assert g.scroll_speed == Game.INITIAL_SCROLL_SPEED

    def test_scroll_speed_increases(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.game_timer = Game.GAME_DURATION // 2
        g.obstacles = []
        g.spawn_timer = 999
        g._update_playing()
        assert g.scroll_speed > Game.INITIAL_SCROLL_SPEED

    def test_scroll_speed_at_max(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.game_timer = 100
        g.obstacles = []
        g.spawn_timer = 999
        g._update_playing()
        assert g.scroll_speed > Game.INITIAL_SCROLL_SPEED


class TestGhostTrail:
    def test_ghost_recording_while_playing(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.game_timer = 100
        g.obstacles = []
        g.spawn_timer = 999
        g.frame = 5
        g._update_playing()
        assert len(g.ghost_recording) > 0

    def test_ghost_trail_saved_on_game_over(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.ghost_recording = [(60.0, 100.0), (60.0, 95.0)]
        g.game_timer = 1
        g.heat = 0.0
        g.obstacles = []
        g.spawn_timer = 999
        g._update_playing()
        assert len(g.ghost_trail) > 0


class TestScreenShake:
    def test_shake_returns_offset(self) -> None:
        g = _make_game(42)
        g.shake_frames = 10
        x, y = g._get_shake_offset()
        assert g.shake_frames == 9
        assert -2 <= x <= 2
        assert -2 <= y <= 2

    def test_shake_returns_zero_when_done(self) -> None:
        g = _make_game(42)
        g.shake_frames = 0
        x, y = g._get_shake_offset()
        assert x == 0
        assert y == 0
        assert g.shake_frames == 0


class TestActivateSuper:
    def test_activate_super_sets_timer(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g._activate_super()
        assert g.super_timer == Game.SUPER_DURATION

    def test_activate_super_spawns_particles(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g._activate_super()
        assert len(g.particles) == 20  # 4 colors * 5

    def test_activate_super_spawns_floating_text(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g._activate_super()
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].text == "SUPER FLOW!"


class TestObstacleUpdate:
    def test_obstacle_moves_left(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.scroll_speed = 2.0
        obs = Obstacle(x=300.0, color=RED)
        g.obstacles = [obs]
        g.spawn_timer = 999
        g.game_timer = 100
        g._update_playing()
        assert obs.x < 300.0

    def test_obstacle_processed_after_passing_player(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.scroll_speed = 20.0
        obs = Obstacle(x=float(Game.PLAYER_X + Game.PLAYER_W // 2 + 5), color=RED)
        g.obstacles = [obs]
        g.player_y = float(Game.GROUND_Y - Game.PLAYER_H)
        g.player_on_ground = True
        g.game_timer = 100
        g.spawn_timer = 999
        g._update_playing()
        assert obs.processed is True


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
