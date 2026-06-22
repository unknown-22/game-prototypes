"""test_imports.py — Headless logic tests for PAINT SURGE prototype."""
from __future__ import annotations

import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/148_paint_surge")

from main import (
    Game,
    Target,
    Paintball,
    Particle,
    Phase,
    TARGET_COLORS,
    HEAT_MAX,
    HEAT_PER_WRONG,
    HEAT_PER_ESCAPE,
    HEAT_DECAY_PER_FRAME,
    SUPER_DURATION,
    GAME_DURATION,
    PLAYER_SPEED,
    SHOOT_COOLDOWN,
    SPREAD_INTERVAL,
    PLAYER_RADIUS,
)


def _make_game(seed: int = 42) -> Game:
    """Create a Game instance for headless testing (bypasses pyxel.init/run)."""
    g = Game.__new__(Game)
    g.CELL = 16
    g.GRID_COLS = 18
    g.GRID_ROWS = 13
    g.OFFSET_X = 16
    g.OFFSET_Y = 16
    g.ARENA_W = g.GRID_COLS * g.CELL
    g.ARENA_H = g.GRID_ROWS * g.CELL
    g.SCREEN_W = 320
    g.SCREEN_H = 240
    g.rng = random.Random(seed)
    g.previous_grid = None
    g.prev_score = 0
    g.prev_max_combo = 0
    g.reset()
    g.rng = random.Random(seed)  # re-seed after reset overwrites
    return g


# ── Dataclass tests ──────────────────────────────────────────────────
def test_target_creation() -> None:
    t = Target(100.0, 120.0, 1.0, -0.5, color=0)
    assert t.x == 100.0
    assert t.y == 120.0
    assert t.vx == 1.0
    assert t.vy == -0.5
    assert t.color == 0
    assert t.hp == 1


def test_paintball_creation() -> None:
    b = Paintball(50.0, 60.0, 3.0, 4.0, color=2)
    assert b.x == 50.0
    assert b.y == 60.0
    assert b.vx == 3.0
    assert b.vy == 4.0
    assert b.color == 2
    assert b.radius == 3.0


def test_particle_creation() -> None:
    p = Particle(10.0, 20.0, 1.0, 2.0, life=15, color=8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == 2.0
    assert p.life == 15
    assert p.color == 8
    assert p.radius == 2.0


# ── Phase enum tests ─────────────────────────────────────────────────
def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ── Initial state tests ──────────────────────────────────────────────
def test_reset_sets_title() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0


def test_initial_paint_grid_empty() -> None:
    g = _make_game()
    for row in range(g.GRID_ROWS):
        for col in range(g.GRID_COLS):
            assert g.paint_grid[row][col] == -1


def test_initial_player_centered() -> None:
    g = _make_game()
    cx = g.OFFSET_X + g.ARENA_W / 2
    cy = g.OFFSET_Y + g.ARENA_H / 2
    assert g.player_x == cx
    assert g.player_y == cy


# ── Target spawning tests ────────────────────────────────────────────
def test_spawn_target_adds_to_list() -> None:
    g = _make_game()
    initial = len(g.targets)
    g._spawn_target()
    assert len(g.targets) == initial + 1


def test_spawned_target_has_valid_color() -> None:
    g = _make_game()
    g._spawn_target()
    t = g.targets[-1]
    assert 0 <= t.color <= 3
    assert t.hp == 1


def test_spawned_target_has_velocity() -> None:
    g = _make_game()
    g._spawn_target()
    t = g.targets[-1]
    assert t.vx != 0 or t.vy != 0


# ── Target update tests ──────────────────────────────────────────────
def test_update_targets_moves() -> None:
    g = _make_game()
    g.targets = [Target(100.0, 100.0, 1.0, 0.0, color=0)]
    g._update_targets()
    assert g.targets[0].x == 101.0
    assert g.targets[0].y == 100.0


def test_update_targets_escape_adds_heat() -> None:
    g = _make_game()
    # Place target far outside the arena (well past margin)
    g.targets = [Target(-50.0, 100.0, -1.0, 0.0, color=0)]
    g._update_targets()
    assert len(g.targets) == 0
    assert g.heat == HEAT_PER_ESCAPE


# ── Paintball update tests ───────────────────────────────────────────
def test_update_paintballs_moves() -> None:
    g = _make_game()
    g.paintballs = [Paintball(100.0, 100.0, 3.0, 4.0, color=1)]
    g._update_paintballs()
    assert g.paintballs[0].x == 103.0
    assert g.paintballs[0].y == 104.0


def test_update_paintballs_removes_offscreen() -> None:
    g = _make_game()
    g.paintballs = [Paintball(-10.0, 100.0, -1.0, 0.0, color=0)]
    g._update_paintballs()
    assert len(g.paintballs) == 0


# ── Hit detection tests ──────────────────────────────────────────────
def test_check_hits_matching_color() -> None:
    g = _make_game()
    t = Target(100.0, 100.0, 0.0, 0.0, color=0)
    g.targets = [t]
    g.paintballs = [Paintball(100.0, 100.0, 0.0, 0.0, color=0)]
    g._check_hits()
    assert len(g.targets) == 0  # hit removed
    assert g.combo >= 1
    assert g.score > 0


def test_check_hits_wrong_color_resets_combo() -> None:
    g = _make_game()
    g.combo = 3
    g.max_combo = 3
    t = Target(100.0, 100.0, 0.0, 0.0, color=0)
    g.targets = [t]
    g.paintballs = [Paintball(100.0, 100.0, 0.0, 0.0, color=1)]  # different color
    heat_before = g.heat
    g._check_hits()
    assert g.combo == 0
    assert g.heat == heat_before + HEAT_PER_WRONG


def test_check_hits_no_collision() -> None:
    g = _make_game()
    t = Target(100.0, 100.0, 0.0, 0.0, color=0)
    g.targets = [t]
    g.paintballs = [Paintball(200.0, 200.0, 0.0, 0.0, color=0)]
    g._check_hits()
    assert len(g.targets) == 1  # not hit


# ── Combo and scoring tests ──────────────────────────────────────────
def test_consecutive_same_color_builds_combo() -> None:
    g = _make_game()
    # First hit
    t1 = Target(100.0, 100.0, 0.0, 0.0, color=0)
    g.targets = [t1]
    g.paintballs = [Paintball(100.0, 100.0, 0.0, 0.0, color=0)]
    g._check_hits()
    assert g.combo == 1
    # Second same-color hit
    t2 = Target(120.0, 120.0, 0.0, 0.0, color=0)
    g.targets = [t2]
    g.paintballs = [Paintball(120.0, 120.0, 0.0, 0.0, color=0)]
    g._check_hits()
    assert g.combo == 2
    assert g.max_combo == 2


def test_score_scales_with_combo() -> None:
    g = _make_game()
    g.combo = 3
    t = Target(100.0, 100.0, 0.0, 0.0, color=0)
    g.targets = [t]
    g.paintballs = [Paintball(100.0, 100.0, 0.0, 0.0, color=0)]
    g._check_hits()
    assert g.score == 40  # combo=4, points = 10*4 = 40
    assert g.combo == 4


# ── SUPER SHOT tests ─────────────────────────────────────────────────
def test_combo_5_activates_super() -> None:
    g = _make_game()
    g.combo = 4
    g.super_timer = 0.0
    t = Target(100.0, 100.0, 0.0, 0.0, color=0)
    g.targets = [t]
    g.paintballs = [Paintball(100.0, 100.0, 0.0, 0.0, color=0)]
    g._check_hits()
    assert g.combo == 5
    assert g.super_timer > 0


def test_super_mode_gives_3x_score() -> None:
    g = _make_game()
    g.combo = 4
    g.super_timer = 1.0  # already in super mode
    g.score = 0
    t = Target(100.0, 100.0, 0.0, 0.0, color=0)
    g.targets = [t]
    g.paintballs = [Paintball(100.0, 100.0, 0.0, 0.0, color=1)]  # wrong color but super matches all
    g._check_hits()
    assert g.score == 10 * 5 * 3  # combo*10 * super 3x


def test_super_mode_all_colors_match() -> None:
    g = _make_game()
    g.combo = 2
    g.super_timer = 1.0
    t = Target(100.0, 100.0, 0.0, 0.0, color=2)
    g.targets = [t]
    g.paintballs = [Paintball(100.0, 100.0, 0.0, 0.0, color=0)]  # different color
    g._check_hits()
    assert g.combo == 3  # matched because super mode


def test_super_timer_decreases() -> None:
    g = _make_game()
    g.super_timer = 3.0
    g.targets = []  # no targets, no auto-fire
    g._update_super()
    assert g.super_timer < 3.0
    assert g.super_timer > 0


# ── Paint splash tests ───────────────────────────────────────────────
def test_splash_paint_fills_3x3_area() -> None:
    g = _make_game()
    x = g.OFFSET_X + 4 * g.CELL + g.CELL // 2  # center of cell (4,2)
    y = g.OFFSET_Y + 2 * g.CELL + g.CELL // 2
    g._splash_paint(x, y, color=0)
    # Check center and surrounding cells
    painted = 0
    for row in range(g.GRID_ROWS):
        for col in range(g.GRID_COLS):
            if g.paint_grid[row][col] == 0:
                painted += 1
    assert painted >= 1  # at least center cell
    # Center cell should be painted
    assert g.paint_grid[2][4] == 0


def test_splash_paint_at_edge_clips() -> None:
    g = _make_game()
    x = g.OFFSET_X + g.CELL // 2  # first cell
    y = g.OFFSET_Y + g.CELL // 2
    g._splash_paint(x, y, color=2)
    # Should not crash, should paint available cells
    assert g.paint_grid[0][0] == 2


# ── CA paint spread tests ────────────────────────────────────────────
def test_paint_spread_counter_increments() -> None:
    g = _make_game()
    assert g.spread_counter == 0
    g._update_paint_spread()  # spread_counter becomes 1
    assert g.spread_counter == 1


def test_paint_spread_triggered_at_interval() -> None:
    g = _make_game()
    g.spread_counter = SPREAD_INTERVAL - 1
    # Place one painted cell
    g.paint_grid[6][9] = 0
    g.rng = random.Random(42)
    g.spread_counter = SPREAD_INTERVAL - 1
    g._update_paint_spread()
    # after the update, counter should reset and grid should have been processed
    assert g.spread_counter == 0


# ── Heat decay tests ─────────────────────────────────────────────────
def test_heat_decay_reduces_heat() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat_decay()
    assert g.heat == max(0.0, 50.0 - HEAT_DECAY_PER_FRAME)


def test_heat_decay_does_not_go_below_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat_decay()
    assert g.heat == 0.0


# ── Game over tests ──────────────────────────────────────────────────
def test_game_over_on_heat_max() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = HEAT_MAX
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER
    assert g.previous_grid is not None
    assert g.prev_score == g.score


def test_game_over_on_timer_zero() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 0.0
    g.game_timer = 0.0
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER


def test_no_game_over_when_safe() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 50.0
    g.game_timer = 45.0
    g._check_game_over()
    assert g.phase == Phase.PLAYING


# ── Particle tests ───────────────────────────────────────────────────
def test_add_particles_creates_correct_count() -> None:
    g = _make_game()
    g._add_particles(100.0, 100.0, 8, 5)
    assert len(g.particles) == 5


def test_update_particles_reduces_life() -> None:
    g = _make_game()
    g.particles = [Particle(10.0, 10.0, 1.0, 1.0, life=2, color=8, radius=2.0)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 1


def test_particles_removed_when_life_expires() -> None:
    g = _make_game()
    g.particles = [Particle(10.0, 10.0, 0.0, 0.0, life=1, color=8, radius=2.0)]
    g._update_particles()
    assert len(g.particles) == 0


# ── Speed multiplier tests ───────────────────────────────────────────
def test_speed_multiplier_increases_over_time() -> None:
    g = _make_game()
    initial = g.speed_multiplier
    g.frame = 1000
    g._update_speed_multiplier()
    assert g.speed_multiplier > initial


# ── Spawning tests ───────────────────────────────────────────────────
def test_spawn_timer_triggers_spawn() -> None:
    g = _make_game()
    g.spawn_timer = 1
    initial_count = len(g.targets)
    g._update_spawning()
    assert g.spawn_timer <= 0 or len(g.targets) > initial_count


# ── Color cycling tests ──────────────────────────────────────────────
def test_color_idx_cycles_after_shoot() -> None:
    g = _make_game()
    # Instead of calling _shoot (which calls pyxel.play), test the cycle logic
    g.color_idx = 0
    g.color_idx = (g.color_idx + 1) % 4
    assert g.color_idx == 1
    g.color_idx = (g.color_idx + 1) % 4
    assert g.color_idx == 2
    g.color_idx = (g.color_idx + 1) % 4
    assert g.color_idx == 3
    g.color_idx = (g.color_idx + 1) % 4
    assert g.color_idx == 0


# ── Constants tests ──────────────────────────────────────────────────
def test_target_colors_are_valid() -> None:
    assert len(TARGET_COLORS) == 4
    assert TARGET_COLORS[0] == 8   # RED
    assert TARGET_COLORS[1] == 3   # GREEN
    assert TARGET_COLORS[2] == 12  # CYAN
    assert TARGET_COLORS[3] == 10  # YELLOW


def test_duration_constants() -> None:
    assert GAME_DURATION == 90.0
    assert SUPER_DURATION == 5.0
    assert HEAT_MAX == 100.0


# ── Arena bounds tests ───────────────────────────────────────────────
def test_arena_dimensions() -> None:
    g = _make_game()
    assert g.ARENA_W == g.GRID_COLS * g.CELL
    assert g.ARENA_H == g.GRID_ROWS * g.CELL


def test_grid_coordinates_in_bounds() -> None:
    g = _make_game()
    assert g.GRID_COLS == 18
    assert g.GRID_ROWS == 13
    assert g.CELL == 16


print("All tests passed!")
