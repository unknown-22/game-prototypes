"""test_imports.py — Headless logic tests for 147_wreck_chain."""
from __future__ import annotations

import importlib.util
import random
import sys
import types
from pathlib import Path

# Stub pyxel before any import
_pyxel = types.ModuleType("pyxel")
sys.modules["pyxel"] = _pyxel
_pyxel.KEY_SPACE = 32
_pyxel.KEY_R = 114
_pyxel.KEY_RETURN = 13
_pyxel.MOUSE_BUTTON_LEFT = 0
_pyxel.frame_count = 0
_pyxel.mouse_x = 0
_pyxel.mouse_y = 0
_pyxel.mouse_wheel = 0


def _stub(*a, **kw):
    pass


for _attr in ("init", "run", "btn", "btnp", "cls", "camera", "text",
              "rect", "rectb", "line", "circ", "play"):
    if _attr in ("btn", "btnp"):
        setattr(_pyxel, _attr, lambda x: False)
    else:
        setattr(_pyxel, _attr, _stub)

# Import main via spec_from_file_location (avoids dataclass None.__module__ issue)
_main_path = str(Path(__file__).resolve().parent / "main.py")
_spec = importlib.util.spec_from_file_location("wreck_main", _main_path)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["wreck_main"] = _mod
_spec.loader.exec_module(_mod)

Game = _mod.Game
Phase = _mod.Phase
Block = _mod.Block
Debris = _mod.Debris
Particle = _mod.Particle
FloatingText = _mod.FloatingText
_combo_multiplier = _mod._combo_multiplier
COLS = _mod.COLS
ROWS = _mod.ROWS
BLOCK_W = _mod.BLOCK_W
BLOCK_H = _mod.BLOCK_H
BUILDING_X = _mod.BUILDING_X
BUILDING_Y = _mod.BUILDING_Y
CHAIN_LENGTH = _mod.CHAIN_LENGTH
ANCHOR_Y = _mod.ANCHOR_Y
BALL_RADIUS = _mod.BALL_RADIUS
HEAT_MAX = _mod.HEAT_MAX
HEAT_PENALTY = _mod.HEAT_PENALTY
TIMER_MAX = _mod.TIMER_MAX
SUPER_DURATION = _mod.SUPER_DURATION
BASE_SCORE = _mod.BASE_SCORE
CHAIN_BONUS = _mod.CHAIN_BONUS
WRONG_COLOR_SCORE = _mod.WRONG_COLOR_SCORE
SUPER_MULTIPLIER = _mod.SUPER_MULTIPLIER
VICTORY_BONUS = _mod.VICTORY_BONUS


def _make_game() -> Game:
    """Headless factory: bypass pyxel.init/run via Game.__new__."""
    g = Game.__new__(Game)
    g._init_state()
    g.rng = random.Random(42)
    g.reset()
    return g


# ─── Tests ────────────────────────────────────────────────────────────


class TestComboMultiplier:
    def test_combo_1(self) -> None:
        assert _combo_multiplier(1) == 1.0

    def test_combo_2(self) -> None:
        assert _combo_multiplier(2) == 1.5

    def test_combo_3(self) -> None:
        assert _combo_multiplier(3) == 2.0

    def test_combo_4(self) -> None:
        assert _combo_multiplier(4) == 3.0

    def test_combo_10(self) -> None:
        assert _combo_multiplier(10) == 3.0

    def test_combo_0(self) -> None:
        assert _combo_multiplier(0) == 1.0


class TestGameInit:
    def test_reset_creates_full_grid(self) -> None:
        g = _make_game()
        assert g.phase == Phase.TITLE
        assert len(g.grid) == COLS
        for col in range(COLS):
            assert len(g.grid[col]) == ROWS
            for row in range(ROWS):
                assert g.grid[col][row] is not None, f"Block at ({col},{row}) is None"

    def test_reset_resets_score(self) -> None:
        g = _make_game()
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0

    def test_reset_resets_heat(self) -> None:
        g = _make_game()
        assert g.heat == 0.0

    def test_reset_resets_timer(self) -> None:
        g = _make_game()
        assert g.timer == TIMER_MAX

    def test_reset_resets_super(self) -> None:
        g = _make_game()
        assert g.super_timer == 0

    def test_reset_resets_ball(self) -> None:
        g = _make_game()
        assert g.ball_angle == 0.0
        assert g.ball_angular_vel == 0.0
        assert not g.swing_active

    def test_reset_clears_debris_particles_texts(self) -> None:
        g = _make_game()
        assert g.debris == []
        assert g.particles == []
        assert g.floating_texts == []

    def test_make_game_rng_deterministic(self) -> None:
        g1 = _make_game()
        g2 = _make_game()
        # Both grids initialized with same seed, so identical
        for col in range(COLS):
            for row in range(ROWS):
                assert g1.grid[col][row].color == g2.grid[col][row].color


class TestDestroyBlock:
    def test_destroy_returns_base_score(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        pts = g._destroy_block(0, 0)
        assert pts == BASE_SCORE

    def test_destroy_clears_grid_cell(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g._destroy_block(0, 0)
        assert g.grid[0][0] is None

    def test_destroy_spawns_debris(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g._destroy_block(0, 0)
        assert len(g.debris) == 8  # 8 debris per block

    def test_destroy_none_returns_zero(self) -> None:
        g = _make_game()
        g.grid[0][0] = None
        pts = g._destroy_block(0, 0)
        assert pts == 0


class TestApplyGravity:
    def test_gravity_pulls_block_down_one(self) -> None:
        g = _make_game()
        # Clear entire column, then place one block at row 5, empty below
        for row in range(ROWS):
            g.grid[0][row] = None
        g.grid[0][5] = Block(0, 5, 0)  # block at row 5
        moved = g._apply_gravity()
        assert len(moved) == 1
        assert moved[0] == (0, 6)
        assert g.grid[0][6] is not None
        assert g.grid[0][6].row == 6  # row updated on block

    def test_gravity_pulls_block_down_multiple(self) -> None:
        g = _make_game()
        for row in range(ROWS):
            g.grid[0][row] = None
        g.grid[0][2] = Block(0, 2, 0)  # block at row 2, empty below
        moved = g._apply_gravity()
        assert len(moved) == 1
        assert g.grid[0][6] is not None  # falls all the way to bottom

    def test_gravity_no_movement_when_stacked(self) -> None:
        g = _make_game()
        moved = g._apply_gravity()
        assert len(moved) == 0

    def test_gravity_empty_column_no_move(self) -> None:
        g = _make_game()
        for row in range(ROWS):
            g.grid[0][row] = None
        moved = g._apply_gravity()
        assert len(moved) == 0


class TestUpdateHeat:
    def test_heat_at_zero_no_change(self) -> None:
        g = _make_game()
        g.heat = 0.0
        assert not g._update_heat()

    def test_heat_decays(self) -> None:
        g = _make_game()
        g.heat = 10.0
        assert not g._update_heat()
        assert g.heat < 10.0

    def test_heat_at_max_returns_true(self) -> None:
        g = _make_game()
        g.heat = HEAT_MAX
        assert g._update_heat()

    def test_heat_above_max_returns_true(self) -> None:
        g = _make_game()
        g.heat = HEAT_MAX + 10
        assert g._update_heat()

    def test_heat_below_max_no_gameover(self) -> None:
        g = _make_game()
        g.heat = HEAT_MAX - 0.1
        assert not g._update_heat()


class TestCheckVictory:
    def test_full_grid_not_victory(self) -> None:
        g = _make_game()
        assert not g._check_victory()

    def test_empty_grid_is_victory(self) -> None:
        g = _make_game()
        for col in range(COLS):
            for row in range(ROWS):
                g.grid[col][row] = None
        assert g._check_victory()

    def test_one_block_not_victory(self) -> None:
        g = _make_game()
        for col in range(COLS):
            for row in range(ROWS):
                g.grid[col][row] = None
        g.grid[0][0] = Block(0, 0, 0)
        assert not g._check_victory()


class TestResolveCollisions:
    def test_first_hit_starts_combo(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        block = g.grid[0][0]
        color = block.color
        g.last_color = None
        g.combo = 0
        total = g._resolve_collisions([(0, 0)])
        assert total > 0
        assert g.combo == 1
        assert g.last_color == color

    def test_same_color_extends_combo(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        # Set up: last_color = color0, combo = 1
        block0 = g.grid[0][0]
        color = block0.color
        g.last_color = color
        g.combo = 1
        # Place same-color block at (0,1)
        g.grid[0][1] = Block(0, 1, color)
        total = g._resolve_collisions([(0, 1)])
        assert total == int(BASE_SCORE * 1.5)  # combo 1→2, x1.5
        assert g.combo == 2

    def test_wrong_color_resets_combo_and_adds_heat(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        block0 = g.grid[0][0]
        color = block0.color
        g.last_color = color
        g.combo = 2
        heat_before = g.heat
        # Place different color block at (0,1)
        diff_color = (color + 1) % 4
        g.grid[0][1] = Block(0, 1, diff_color)
        total = g._resolve_collisions([(0, 1)])
        assert total == WRONG_COLOR_SCORE
        assert g.combo == 0
        assert g.heat > heat_before
        assert g.last_color == diff_color

    def test_super_mode_all_colors_match(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        block0 = g.grid[0][0]
        color = block0.color
        g.last_color = color
        g.combo = 1
        g.super_timer = 100
        # Different color block should still extend combo in super mode
        diff_color = (color + 1) % 4
        g.grid[0][1] = Block(0, 1, diff_color)
        total = g._resolve_collisions([(0, 1)])
        # In super: combo extends + super multiplier applied
        assert g.combo == 2  # extended
        mult = _combo_multiplier(2) * SUPER_MULTIPLIER
        assert total == int(BASE_SCORE * mult)

    def test_super_activation_at_combo_4(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        block0 = g.grid[0][0]
        color = block0.color
        g.last_color = color
        g.combo = 3  # about to hit combo 4
        g.grid[0][1] = Block(0, 1, color)
        g._resolve_collisions([(0, 1)])
        assert g.combo >= 4
        assert g.super_timer == SUPER_DURATION  # activated

    def test_max_combo_tracks(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        block0 = g.grid[0][0]
        color = block0.color
        g.last_color = color
        g.combo = 1
        g.grid[0][1] = Block(0, 1, color)
        g._resolve_collisions([(0, 1)])
        assert g.max_combo == 2

    def test_empty_cell_skipped(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.grid[0][0] = None
        g.last_color = None
        total = g._resolve_collisions([(0, 0)])
        assert total == 0


class TestBallPhysics:
    def test_update_ball_position(self) -> None:
        g = _make_game()
        g.anchor_x = 160.0
        g.ball_angle = 0.0
        g._update_ball_position()
        assert abs(g.ball_x - 160.0) < 0.01
        assert abs(g.ball_y - (ANCHOR_Y + CHAIN_LENGTH)) < 0.01

    def test_release_ball_to_right(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.ball_angle = -0.1  # tilted slightly left, will swing right
        g._release_ball()
        assert g.swing_active
        assert g.phase == Phase.SWINGING
        assert g.ball_angular_vel > 0  # positive = swinging right

    def test_release_ball_to_left(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.ball_angle = 0.1  # tilted slightly right, will swing left
        g._release_ball()
        assert g.ball_angular_vel < 0  # negative = swinging left

    def test_update_ball_physics_changes_angle(self) -> None:
        g = _make_game()
        g.ball_angle = 0.1
        g.ball_angular_vel = 0.0
        g._update_ball_physics()
        # Gravity should add velocity
        assert g.ball_angular_vel != 0.0


class TestCollision:
    def test_block_collision_detected(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        # Position ball over a block
        col, row = 0, 0
        bx = BUILDING_X + col * BLOCK_W + BLOCK_W // 2
        by = BUILDING_Y + row * BLOCK_H + BLOCK_H // 2
        g.ball_x = float(bx)
        g.ball_y = float(by)
        collisions = g._check_block_collision()
        assert (col, row) in collisions

    def test_ball_far_away_no_collision(self) -> None:
        g = _make_game()
        g.ball_x = 10.0
        g.ball_y = 10.0
        collisions = g._check_block_collision()
        assert len(collisions) == 0

    def test_hit_this_swing_prevents_double_count(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        col, row = 0, 0
        bx = BUILDING_X + col * BLOCK_W + BLOCK_W // 2
        by = BUILDING_Y + row * BLOCK_H + BLOCK_H // 2
        g.ball_x = float(bx)
        g.ball_y = float(by)
        g._hit_this_swing.add((col, row))
        collisions = g._check_block_collision()
        assert (col, row) not in collisions


class TestDebrisAndParticles:
    def test_spawn_debris(self) -> None:
        g = _make_game()
        g._spawn_debris(100.0, 100.0, 8, 6)
        assert len(g.debris) == 6
        for d in g.debris:
            assert d.life >= 30
            assert d.life <= 45

    def test_spawn_particles(self) -> None:
        g = _make_game()
        g._spawn_particles(100.0, 100.0, 8, 6)
        assert len(g.particles) == 6

    def test_add_floating_text(self) -> None:
        g = _make_game()
        g._add_floating_text(100, 100, "TEST", 7)
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].text == "TEST"
        assert g.floating_texts[0].life == 30

    def test_update_debris_reduces_life(self) -> None:
        g = _make_game()
        g._spawn_debris(100.0, 100.0, 8, 1)
        assert g.debris[0].life > 30
        g._update_debris()
        assert g.debris[0].life > 29  # decremented but still alive

    def test_update_debris_removes_expired(self) -> None:
        g = _make_game()
        g.debris = [Debris(x=100, y=100, vx=1, vy=1, life=1, color=8)]
        g._update_debris()
        assert len(g.debris) == 0

    def test_update_particles_removes_expired(self) -> None:
        g = _make_game()
        g.particles = [Particle(x=100, y=100, vx=1, vy=1, life=1, color=8)]
        g._update_particles()
        assert len(g.particles) == 0

    def test_update_floating_texts_removes_expired(self) -> None:
        g = _make_game()
        g.floating_texts = [FloatingText(x=100, y=100, text="X", life=1, color=7)]
        g._update_floating_texts()
        assert len(g.floating_texts) == 0


class TestConstants:
    def test_grid_dimensions(self) -> None:
        assert COLS == 8
        assert ROWS == 7

    def test_block_dimensions(self) -> None:
        assert BLOCK_W == 36
        assert BLOCK_H == 20

    def test_heat_max(self) -> None:
        assert HEAT_MAX == 100.0

    def test_heat_penalty(self) -> None:
        assert HEAT_PENALTY == 20.0

    def test_timer_max(self) -> None:
        assert TIMER_MAX == 3600  # 60 seconds

    def test_super_duration(self) -> None:
        assert SUPER_DURATION == 300  # 5 seconds


class TestPhaseEnum:
    def test_phases_exist(self) -> None:
        assert Phase.TITLE in Phase
        assert Phase.PLAYING in Phase
        assert Phase.SWINGING in Phase
        assert Phase.GAME_OVER in Phase
        assert Phase.VICTORY in Phase

    def test_phases_distinct(self) -> None:
        phases = [Phase.TITLE, Phase.PLAYING, Phase.SWINGING, Phase.GAME_OVER, Phase.VICTORY]
        assert len(set(phases)) == 5


if __name__ == "__main__":
    # Manual test runner
    import traceback

    tests_run = 0
    tests_passed = 0
    test_classes = [
        TestComboMultiplier, TestGameInit, TestDestroyBlock, TestApplyGravity,
        TestUpdateHeat, TestCheckVictory, TestResolveCollisions,
        TestBallPhysics, TestCollision, TestDebrisAndParticles,
        TestConstants, TestPhaseEnum,
    ]
    for tc in test_classes:
        for name in dir(tc):
            if name.startswith("test_"):
                tests_run += 1
                method = getattr(tc(), name)
                try:
                    method()
                    tests_passed += 1
                    print(f"  ✓ {tc.__name__}.{name}")
                except Exception as e:
                    print(f"  ✗ {tc.__name__}.{name} — {e}")
                    traceback.print_exc()
    print(f"\n{tests_passed}/{tests_run} passed")
    if tests_passed < tests_run:
        sys.exit(1)
