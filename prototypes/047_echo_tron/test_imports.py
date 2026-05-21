"""test_imports.py — Headless logic tests for ECHO TRON.

Uses Game.__new__ pattern to bypass Pyxel init.
"""
from __future__ import annotations

import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/047_echo_tron")

from main import Bike, Gem, Particle, Phase, Game
from main import GRID_W, GRID_H, CELL, NUM_COLORS, DIRS, COLOR_VALS


def test_data_classes() -> None:
    """Test dataclass construction."""
    b = Bike(x=5, y=10, d=2, color=1)
    assert b.x == 5
    assert b.y == 10
    assert b.d == 2
    assert b.alive is True
    assert b.color == 1

    g = Gem(x=3, y=7, color=2)
    assert g.x == 3
    assert g.y == 7
    assert g.collected is False
    g.collected = True
    assert g.collected is True

    p = Particle(x=1.5, y=2.5, vx=0.5, vy=-0.3, life=10, color=8)
    assert abs(p.x - 1.5) < 0.01
    assert p.life == 10
    assert p.max_life == 12


def test_phase_enum() -> None:
    """Test Phase enum values."""
    assert Phase.PLAYING is not Phase.GAME_OVER
    assert Phase.PLAYING in Phase


def test_config() -> None:
    """Test config constants."""
    assert GRID_W == 30
    assert GRID_H == 24
    assert CELL == 8
    assert NUM_COLORS == 4
    assert len(COLOR_VALS) == 4
    assert len(DIRS) == 4
    assert DIRS[0] == (0, -1)  # UP
    assert DIRS[1] == (1, 0)   # RIGHT
    assert DIRS[2] == (0, 1)   # DOWN
    assert DIRS[3] == (-1, 0)  # LEFT


def test_game_reset() -> None:
    """Test Game.reset() via __new__ pattern."""
    g: Game = Game.__new__(Game)
    # Pre-init all attributes that reset() touches
    g._rng = None  # type: ignore[assignment]
    g.reset()
    assert g.phase == Phase.PLAYING
    assert g.tick_timer == 0
    assert abs(g.tick_interval - 10.0) < 0.01
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.combo_color == -1
    assert g.kills == 0
    assert g._shake_frames == 0
    assert len(g.wall_grid) == GRID_H
    assert len(g.wall_grid[0]) == GRID_W
    assert g.player.alive is True
    assert g.player.x == GRID_W // 4
    assert len(g.enemies) == 3
    assert len(g.gems) == 6
    assert len(g.particles) == 0


def test_wall_grid_empty_after_reset() -> None:
    """Test wall grid is all -1 after reset."""
    g: Game = Game.__new__(Game)
    g._rng = None  # type: ignore[assignment]
    g.reset()
    for y in range(GRID_H):
        for x in range(GRID_W):
            assert g.wall_grid[y][x] == -1, f"Wall at ({x},{y}) is {g.wall_grid[y][x]}"


def test_bike_movement_collision() -> None:
    """Test that a bike moving into a wall dies."""
    g: Game = Game.__new__(Game)
    g._rng = None  # type: ignore[assignment]
    g.reset()
    # Place a wall in front of the player
    g.wall_grid[g.player.y][g.player.x + 1] = 0
    # Force player to move right
    g.player.d = 1
    # Process tick (player should hit wall)
    # Set up tick interval so _tick fires
    g.tick_interval = 0.5  # will fire on next update call
    g.tick_timer = 0
    # Simulate a tick manually
    g._ai_decide = lambda enemy: None  # no-op AI
    g._tick()
    # Player should be dead (hit wall)
    assert g.player.alive is False
    assert g.phase == Phase.GAME_OVER


def test_enemy_ai_avoids_walls() -> None:
    """Test enemy AI picks non-wall directions."""
    g: Game = Game.__new__(Game)
    g._rng = None  # type: ignore[assignment]
    g.reset()
    enemy = g.enemies[0]
    # Surround enemy with walls in 3 of 4 directions
    for d_idx in range(4):
        dx, dy = DIRS[d_idx]
        nx, ny = enemy.x + dx, enemy.y + dy
        if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
            g.wall_grid[ny][nx] = 1

    # Clear one direction to give the AI an option
    clear_d = (enemy.d + 1) % 4  # not reverse
    dx, dy = DIRS[clear_d]
    nx, ny = enemy.x + dx, enemy.y + dy
    if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
        g.wall_grid[ny][nx] = -1

    original_d = enemy.d
    g._ai_decide(enemy)
    # Enemy should have picked a non-reverse direction
    assert enemy.d != (original_d + 2) % 4


def test_combo_reset_on_different_color() -> None:
    """Test combo resets when collecting different color gem."""
    g: Game = Game.__new__(Game)
    g._rng = None  # type: ignore[assignment]
    g.reset()
    # Place a gem where the player is
    g.gems = [Gem(x=g.player.x, y=g.player.y, color=0)]
    g.combo_color = 0
    g.combo = 3
    g._check_gem_collection()
    assert g.combo == 4
    assert g.combo_color == 0
    # Now different color
    g.gems = [Gem(x=g.player.x, y=g.player.y, color=1)]
    g._check_gem_collection()
    assert g.combo == 1
    assert g.combo_color == 1


def test_combo_chain_same_color() -> None:
    """Test combo builds on same color consecutively."""
    g: Game = Game.__new__(Game)
    g._rng = None  # type: ignore[assignment]
    g.reset()
    g.combo_color = 2
    g.combo = 1
    g.gems = [Gem(x=g.player.x, y=g.player.y, color=2)]
    g._check_gem_collection()
    assert g.combo == 2
    g.gems = [Gem(x=g.player.x, y=g.player.y, color=2)]
    g._check_gem_collection()
    assert g.combo == 3


def test_find_empty_cells() -> None:
    """Test _find_empty_cells returns cells without walls or bikes."""
    g: Game = Game.__new__(Game)
    g._rng = None  # type: ignore[assignment]
    g.reset()
    total = GRID_W * GRID_H
    # Bikes occupy some cells
    occupied_bikes = 1  # player
    for e in g.enemies:
        if e.alive:
            occupied_bikes += 1
    empty = g._find_empty_cells()
    assert len(empty) == total - occupied_bikes


def test_head_on_collision() -> None:
    """Test two bikes heading into each other both die."""
    g: Game = Game.__new__(Game)
    g._rng = None  # type: ignore[assignment]
    g.reset()
    # Place player and enemy facing each other
    g.player.x = 10
    g.player.y = 10
    g.player.d = 1  # right
    g.enemies[0].x = 11
    g.enemies[0].y = 10
    g.enemies[0].d = 3  # left
    g.enemies[0].alive = True
    # Clear walls
    for y in range(GRID_H):
        for x in range(GRID_W):
            g.wall_grid[y][x] = -1
    g._ai_decide = lambda enemy: None
    g._tick()
    assert g.player.alive is False
    assert g.enemies[0].alive is False


def test_gem_spawning() -> None:
    """Test _spawn_gem_single creates a gem on empty cell."""
    g: Game = Game.__new__(Game)
    g._rng = None  # type: ignore[assignment]
    g.reset()
    g.gems.clear()
    g._spawn_gem_single()
    assert len(g.gems) == 1
    gem = g.gems[0]
    assert 0 <= gem.x < GRID_W
    assert 0 <= gem.y < GRID_H
    assert 0 <= gem.color < NUM_COLORS
    # Check it's on an empty cell
    assert g.wall_grid[gem.y][gem.x] == -1


def test_particles_lifecycle() -> None:
    """Test particles are created and decay."""
    g: Game = Game.__new__(Game)
    g._rng = None  # type: ignore[assignment]
    g.reset()
    g._add_particles(100.0, 50.0, 5, 0)
    assert len(g.particles) == 5
    # Update several times to decay
    for _ in range(20):
        g._update_particles()
    assert len(g.particles) == 0  # all particles should be dead


def test_score_increments() -> None:
    """Test score increments on tick and kills."""
    g: Game = Game.__new__(Game)
    g._rng = None  # type: ignore[assignment]
    g.reset()
    initial = g.score
    g._ai_decide = lambda enemy: None
    g._tick()
    assert g.score == initial + 1  # survived one tick


def test_speed_increases() -> None:
    """Test tick interval decreases over time."""
    g: Game = Game.__new__(Game)
    g._rng = None  # type: ignore[assignment]
    g.reset()
    initial_interval = g.tick_interval
    g._ai_decide = lambda enemy: None
    g._tick()
    assert g.tick_interval < initial_interval


def test_kill_increments() -> None:
    """Test kills counter increments when enemy dies."""
    g: Game = Game.__new__(Game)
    g._rng = None  # type: ignore[assignment]
    g.reset()
    assert g.kills == 0
    # Kill an enemy
    enemy = g.enemies[0]
    g._kill_bike(enemy)
    assert g.kills == 1
    assert enemy.alive is False


def test_game_over_restart() -> None:
    """Test reset after game over clears state."""
    g: Game = Game.__new__(Game)
    g._rng = None  # type: ignore[assignment]
    g.reset()
    g.phase = Phase.GAME_OVER
    g.score = 999
    g.combo = 10
    g.kills = 5
    g.wall_grid[5][5] = 0  # some wall
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=5, color=8)]
    g.gems = [Gem(x=10, y=10, color=0)]
    g.reset()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.kills == 0
    assert g.wall_grid[5][5] == -1
    assert len(g.particles) == 0
    assert len(g.gems) == 6


if __name__ == "__main__":
    test_data_classes()
    test_phase_enum()
    test_config()
    test_game_reset()
    test_wall_grid_empty_after_reset()
    test_bike_movement_collision()
    test_enemy_ai_avoids_walls()
    test_combo_reset_on_different_color()
    test_combo_chain_same_color()
    test_find_empty_cells()
    test_head_on_collision()
    test_gem_spawning()
    test_particles_lifecycle()
    test_score_increments()
    test_speed_increases()
    test_kill_increments()
    test_game_over_restart()
    print("ALL TESTS PASSED")
