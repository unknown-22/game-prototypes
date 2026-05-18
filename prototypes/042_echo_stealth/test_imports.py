"""test_imports.py — Headless logic tests for ECHO STEALTH."""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/042_echo_stealth")
from main import (
    COLOR_RED,
    COLOR_WHITE,
    GUARD_COLORS,
    GUARD_NAMES,
    NUM_COLORS,
    PHASE_DURATION,
    PLAYER_HP,
    GUARD_COUNT,
    GEM_COUNT,
    WALL_COUNT,
    TIME_LIMIT,
    GEM_SCORE,
    VISION_RANGE,
    ECHO_LIFE,
    CAUGHT_INVULN,
    Direction,
    DIR_VECTORS,
    Phase,
    Guard,
    Echo,
    Game,
    SCREEN_W,
    SCREEN_H,
    TILE_SIZE,
    GRID_W,
    GRID_H,
)


def test_config() -> None:
    """Test config constants are sane."""
    assert SCREEN_W == 256
    assert SCREEN_H == 256
    assert TILE_SIZE == 16
    assert GRID_W == 16
    assert GRID_H == 16
    assert NUM_COLORS == 4
    assert len(GUARD_COLORS) == NUM_COLORS
    assert len(GUARD_NAMES) == NUM_COLORS
    assert PLAYER_HP == 3
    assert GUARD_COUNT == 5
    assert GEM_COUNT == 8
    assert WALL_COUNT == 14
    assert VISION_RANGE == 3
    assert PHASE_DURATION == 90
    assert ECHO_LIFE == PHASE_DURATION * 2
    assert CAUGHT_INVULN == 30
    assert TIME_LIMIT == 60 * 30  # 30 FPS
    assert DIR_VECTORS[Direction.DOWN] == (0, 1)
    assert DIR_VECTORS[Direction.UP] == (0, -1)
    assert DIR_VECTORS[Direction.LEFT] == (-1, 0)
    assert DIR_VECTORS[Direction.RIGHT] == (1, 0)


def test_direction_reverse() -> None:
    """Direction reversal should go to opposite."""
    assert Direction((int(Direction.UP) + 2) % 4) == Direction.DOWN
    assert Direction((int(Direction.DOWN) + 2) % 4) == Direction.UP
    assert Direction((int(Direction.LEFT) + 2) % 4) == Direction.RIGHT
    assert Direction((int(Direction.RIGHT) + 2) % 4) == Direction.LEFT


def test_game_headless() -> None:
    """Test Game.__new__ headless instantiation and logic."""
    g = Game.__new__(Game)
    # Pre-init all attributes that reset() touches
    g._rng = random.Random(42)
    g.phase = Phase.PLAYING
    g.player_gx = 0
    g.player_gy = 0
    g.player_hp = 0
    g.score = 0
    g.max_score = 0
    g.gems_collected = 0
    g.active_color = 0
    g.phase_timer = 0
    g.game_timer = 0
    g.caught_timer = 0
    g.caught_flash = 0
    g.grid = []
    g.guards = []
    g.echoes = []
    g.particles = []
    g.floating_texts = []
    g.gems = []
    g.exit_gx = 0
    g.exit_gy = 0
    g.reset()

    # Grid dimensions
    assert len(g.grid) == GRID_H
    assert len(g.grid[0]) == GRID_W

    # Guards created
    assert len(g.guards) == GUARD_COUNT
    for guard in g.guards:
        assert 0 <= guard.color < NUM_COLORS
        assert 0 <= guard.x < GRID_W
        assert 0 <= guard.y < GRID_H
        assert guard.patrol_min_x <= guard.patrol_max_x
        assert guard.patrol_min_y <= guard.patrol_max_y

    # Gems placed
    assert len(g.gems) == GEM_COUNT
    for gem in g.gems:
        gx, gy, gcolor = gem
        assert 0 <= gx < GRID_W
        assert 0 <= gy < GRID_H
        assert 0 <= gcolor < NUM_COLORS
        assert g.grid[gy][gx] == 0  # not on wall

    # Wall count — should be exactly WALL_COUNT since we place guards first
    wall_count = sum(1 for row in g.grid for cell in row if cell == 1)
    assert wall_count == WALL_COUNT, f"Expected {WALL_COUNT} walls, got {wall_count}"

    # Exit is walkable
    assert g.grid[g.exit_gy][g.exit_gx] == 0

    # Start is walkable
    assert g.grid[1][1] == 0

    # Player at start
    assert g.player_gx == 1
    assert g.player_gy == 1
    assert g.player_hp == PLAYER_HP


def test_walkable() -> None:
    """Test _walkable boundary checks."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.PLAYING
    g.player_gx = 0
    g.player_gy = 0
    g.player_hp = 0
    g.score = 0
    g.max_score = 0
    g.gems_collected = 0
    g.active_color = 0
    g.phase_timer = 0
    g.game_timer = 0
    g.caught_timer = 0
    g.caught_flash = 0
    g.grid = []
    g.guards = []
    g.echoes = []
    g.particles = []
    g.floating_texts = []
    g.gems = []
    g.exit_gx = 0
    g.exit_gy = 0
    g.reset()

    # In bounds, walkable
    assert g._walkable(1, 1) is True
    # Out of bounds
    assert g._walkable(-1, 0) is False
    assert g._walkable(0, -1) is False
    assert g._walkable(GRID_W, 0) is False
    assert g._walkable(0, GRID_H) is False


def test_vision_logic() -> None:
    """Test _in_vision computes correctly for facing directions."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.PLAYING
    g.player_gx = 0
    g.player_gy = 0
    g.player_hp = 0
    g.score = 0
    g.max_score = 0
    g.gems_collected = 0
    g.active_color = 0
    g.phase_timer = 0
    g.game_timer = 0
    g.caught_timer = 0
    g.caught_flash = 0
    g.grid = []
    g.guards = []
    g.echoes = []
    g.particles = []
    g.floating_texts = []
    g.gems = []
    g.exit_gx = 0
    g.exit_gy = 0
    g.reset()

    # Make a guard at (8, 8) facing RIGHT
    guard = Guard(
        x=8, y=8, color=0,
        direction=Direction.RIGHT,
        patrol_min_x=5, patrol_min_y=8,
        patrol_max_x=10, patrol_max_y=8,
    )

    # Player directly in front (within range 3)
    g.player_gx = 10
    g.player_gy = 8
    assert g._in_vision(guard) is True

    # Player behind guard
    g.player_gx = 6
    g.player_gy = 8
    assert g._in_vision(guard) is False

    # Player too far (range 4)
    g.player_gx = 12
    g.player_gy = 8
    assert g._in_vision(guard) is False

    # Player at same position
    g.player_gx = 8
    g.player_gy = 8
    assert g._in_vision(guard) is False  # forward=0

    # Diagonal within cone
    g.player_gx = 10
    g.player_gy = 7
    assert g._in_vision(guard) is True


def test_phase_transitions() -> None:
    """Test phase enum values."""
    assert Phase.PLAYING == 0
    assert Phase.CAUGHT == 1
    assert Phase.VICTORY == 2
    assert Phase.DEFEAT == 3


def test_echo_lifecycle() -> None:
    """Test echoes get created and expire."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.PLAYING
    g.player_gx = 0
    g.player_gy = 0
    g.player_hp = 0
    g.score = 0
    g.max_score = 0
    g.gems_collected = 0
    g.active_color = 0
    g.phase_timer = 0
    g.game_timer = 0
    g.caught_timer = 0
    g.caught_flash = 0
    g.grid = []
    g.guards = []
    g.echoes = []
    g.particles = []
    g.floating_texts = []
    g.gems = []
    g.exit_gx = 0
    g.exit_gy = 0
    g.reset()

    # Add an echo
    g.echoes.append(Echo(gx=5, gy=5, color=0, life=ECHO_LIFE))
    assert len(g.echoes) == 1

    # Update enough times to expire
    for _ in range(ECHO_LIFE):
        g._update_echoes()
    assert len(g.echoes) == 0


def test_guard_patrol_reversal() -> None:
    """Test guard reverses direction at patrol bounds."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.PLAYING
    g.player_gx = 0
    g.player_gy = 0
    g.player_hp = 0
    g.score = 0
    g.max_score = 0
    g.gems_collected = 0
    g.active_color = 0
    g.phase_timer = 0
    g.game_timer = 0
    g.caught_timer = 0
    g.caught_flash = 0
    g.grid = []
    g.guards = []
    g.echoes = []
    g.particles = []
    g.floating_texts = []
    g.gems = []
    g.exit_gx = 0
    g.exit_gy = 0
    g.reset()

    # Replace guards with a single controlled guard
    guard = Guard(
        x=4, y=8, color=0,
        direction=Direction.RIGHT,
        patrol_min_x=4, patrol_min_y=8,
        patrol_max_x=6, patrol_max_y=8,
    )
    g.guards = [guard]
    g.echoes = []  # no echoes to distract

    # Move right 2 times
    g._update_guards()
    assert guard.x == 5
    assert guard.direction == Direction.RIGHT
    g._update_guards()
    assert guard.x == 6
    assert guard.direction == Direction.RIGHT

    # Next move should reverse
    g._update_guards()
    assert guard.x == 5
    assert guard.direction == Direction.LEFT


def test_echo_distraction() -> None:
    """Test echo attracts same-color guard."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.PLAYING
    g.player_gx = 0
    g.player_gy = 0
    g.player_hp = 0
    g.score = 0
    g.max_score = 0
    g.gems_collected = 0
    g.active_color = 0
    g.phase_timer = 0
    g.game_timer = 0
    g.caught_timer = 0
    g.caught_flash = 0
    g.grid = []
    g.guards = []
    g.echoes = []
    g.particles = []
    g.floating_texts = []
    g.gems = []
    g.exit_gx = 0
    g.exit_gy = 0
    g.reset()

    # Set up: guard at (4, 8), echo at (10, 8)
    guard = Guard(
        x=4, y=8, color=0,
        direction=Direction.RIGHT,
        patrol_min_x=2, patrol_min_y=8,
        patrol_max_x=12, patrol_max_y=8,
    )
    g.guards = [guard]
    g.echoes = [Echo(gx=10, gy=8, color=0, life=ECHO_LIFE)]

    # Guard should be distracted and move toward echo
    g._update_guards()
    assert guard.distracted is True
    assert guard.x > 4  # moved right toward echo
    assert guard.y == 8

    # Remove echo
    g.echoes = []
    # Should resume normal patrol
    g._update_guards()
    assert guard.distracted is False


def test_gem_collection() -> None:
    """Test collecting gems adds score."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.PLAYING
    g.player_gx = 0
    g.player_gy = 0
    g.player_hp = 0
    g.score = 0
    g.max_score = 0
    g.gems_collected = 0
    g.active_color = 0
    g.phase_timer = 0
    g.game_timer = 0
    g.caught_timer = 0
    g.caught_flash = 0
    g.grid = []
    g.guards = []
    g.echoes = []
    g.particles = []
    g.floating_texts = []
    g.gems = []
    g.exit_gx = 0
    g.exit_gy = 0
    g.reset()

    # Place player and gem at same position
    g.player_gx = 5
    g.player_gy = 5
    g.gems = [(5, 5, 0)]  # gem at player position, color 0
    g.active_color = 0  # same as gem gives bonus

    old_score = g.score
    g._collect_gems()
    assert len(g.gems) == 0
    assert g.gems_collected == 1
    # Score: GEM_SCORE * 2 (matching active color)
    assert g.score == old_score + GEM_SCORE * 2


def test_game_over_on_hp_depletion() -> None:
    """Test phase goes to DEFEAT when HP reaches 0."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.PLAYING
    g.player_gx = 0
    g.player_gy = 0
    g.player_hp = 0
    g.score = 0
    g.max_score = 0
    g.gems_collected = 0
    g.active_color = 0
    g.phase_timer = 0
    g.game_timer = 0
    g.caught_timer = 0
    g.caught_flash = 0
    g.grid = []
    g.guards = []
    g.echoes = []
    g.particles = []
    g.floating_texts = []
    g.gems = []
    g.exit_gx = 0
    g.exit_gy = 0
    g.reset()

    g.player_hp = 1
    guard = Guard(x=5, y=5, color=0, direction=Direction.RIGHT,
                  patrol_min_x=5, patrol_min_y=5, patrol_max_x=5, patrol_max_y=5)
    g._on_caught(guard)
    assert g.player_hp == 0
    assert g.phase == Phase.DEFEAT


def test_victory_on_exit() -> None:
    """Test reaching exit triggers victory."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.PLAYING
    g.player_gx = 0
    g.player_gy = 0
    g.player_hp = 0
    g.score = 0
    g.max_score = 0
    g.gems_collected = 0
    g.active_color = 0
    g.phase_timer = 0
    g.game_timer = 0
    g.caught_timer = 0
    g.caught_flash = 0
    g.grid = []
    g.guards = []
    g.echoes = []
    g.particles = []
    g.floating_texts = []
    g.gems = []
    g.exit_gx = 0
    g.exit_gy = 0
    g.reset()

    g.player_gx = g.exit_gx
    g.player_gy = g.exit_gy
    g.game_timer = 30 * 60  # 30 seconds worth
    g._check_exit()
    assert g.phase == Phase.VICTORY
    assert g.score >= 30 * 10  # TIME_SCORE_MULT


def test_line_of_sight_wall_block() -> None:
    """Test _line_of_sight returns False when wall blocks view."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.PLAYING
    g.player_gx = 0
    g.player_gy = 0
    g.player_hp = 0
    g.score = 0
    g.max_score = 0
    g.gems_collected = 0
    g.active_color = 0
    g.phase_timer = 0
    g.game_timer = 0
    g.caught_timer = 0
    g.caught_flash = 0
    g.grid = []
    g.guards = []
    g.echoes = []
    g.particles = []
    g.floating_texts = []
    g.gems = []
    g.exit_gx = 0
    g.exit_gy = 0
    g.reset()

    # Clear grid
    for y in range(GRID_H):
        for x in range(GRID_W):
            g.grid[y][x] = 0

    # No wall: line of sight should work
    assert g._line_of_sight(4, 4, 8, 8) is True

    # Place wall between (4,4) and (8,8)
    g.grid[6][6] = 1
    assert g._line_of_sight(4, 4, 8, 8) is False

    # Same position
    assert g._line_of_sight(5, 5, 5, 5) is True


def test_particle_lifecycle() -> None:
    """Test particles spawn and decay."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.PLAYING
    g.player_gx = 0
    g.player_gy = 0
    g.player_hp = 0
    g.score = 0
    g.max_score = 0
    g.gems_collected = 0
    g.active_color = 0
    g.phase_timer = 0
    g.game_timer = 0
    g.caught_timer = 0
    g.caught_flash = 0
    g.grid = []
    g.guards = []
    g.echoes = []
    g.particles = []
    g.floating_texts = []
    g.gems = []
    g.exit_gx = 0
    g.exit_gy = 0
    g.reset()

    g._spawn_particles(5, 5, COLOR_RED, 10)
    assert len(g.particles) == 10
    for p in g.particles:
        assert p.color == COLOR_RED
        assert p.life > 0

    # Run until all expire
    for _ in range(30):
        g._update_particles()
    assert len(g.particles) == 0


def test_floating_text_lifecycle() -> None:
    """Test floating text spawns and decays."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.PLAYING
    g.player_gx = 0
    g.player_gy = 0
    g.player_hp = 0
    g.score = 0
    g.max_score = 0
    g.gems_collected = 0
    g.active_color = 0
    g.phase_timer = 0
    g.game_timer = 0
    g.caught_timer = 0
    g.caught_flash = 0
    g.grid = []
    g.guards = []
    g.echoes = []
    g.particles = []
    g.floating_texts = []
    g.gems = []
    g.exit_gx = 0
    g.exit_gy = 0
    g.reset()

    g._spawn_floating_text(5, 5, "TEST", COLOR_WHITE)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "TEST"

    for _ in range(30):
        g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_color_cycle() -> None:
    """Test active color cycles through all colors."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.PLAYING
    g.player_gx = 0
    g.player_gy = 0
    g.player_hp = 0
    g.score = 0
    g.max_score = 0
    g.gems_collected = 0
    g.active_color = 0
    g.phase_timer = 0
    g.game_timer = 0
    g.caught_timer = 0
    g.caught_flash = 0
    g.grid = []
    g.guards = []
    g.echoes = []
    g.particles = []
    g.floating_texts = []
    g.gems = []
    g.exit_gx = 0
    g.exit_gy = 0
    g.reset()

    assert g.active_color == 0
    # Simulate phase timer decrement
    for i in range(1, NUM_COLORS * 2):
        g.active_color = (g.active_color + 1) % NUM_COLORS
        expected = i % NUM_COLORS
        assert g.active_color == expected


def test_detection_skips_inactive_color() -> None:
    """Test _check_detection ignores guards of inactive colors."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.PLAYING
    g.player_gx = 0
    g.player_gy = 0
    g.player_hp = 0
    g.score = 0
    g.max_score = 0
    g.gems_collected = 0
    g.active_color = 0
    g.phase_timer = 0
    g.game_timer = 0
    g.caught_timer = 0
    g.caught_flash = 0
    g.grid = []
    g.guards = []
    g.echoes = []
    g.particles = []
    g.floating_texts = []
    g.gems = []
    g.exit_gx = 0
    g.exit_gy = 0
    g.reset()

    # Clear grid for deterministic vision
    for y in range(GRID_H):
        for x in range(GRID_W):
            g.grid[y][x] = 0

    # Guard of active color at same position as player
    g.active_color = 0
    guard_active = Guard(
        x=5, y=5, color=0,
        direction=Direction.RIGHT,
        patrol_min_x=5, patrol_min_y=5,
        patrol_max_x=5, patrol_max_y=5,
    )
    g.guards = [guard_active]
    g.player_gx = 6
    g.player_gy = 5
    # Player in front of active guard -> should be caught
    g._check_detection()
    assert g.phase == Phase.CAUGHT
    assert g.player_hp == PLAYER_HP - 1

    # Reset and test inactive guard
    g.phase = Phase.PLAYING
    g.player_hp = PLAYER_HP
    g.caught_timer = 0
    g.active_color = 1  # different from guard (0)
    g.guards = [guard_active]
    g.player_gx = 6
    g.player_gy = 5
    g._check_detection()
    assert g.phase == Phase.PLAYING  # not caught
    assert g.player_hp == PLAYER_HP


if __name__ == "__main__":
    test_config()
    test_direction_reverse()
    test_game_headless()
    test_walkable()
    test_vision_logic()
    test_phase_transitions()
    test_echo_lifecycle()
    test_guard_patrol_reversal()
    test_echo_distraction()
    test_gem_collection()
    test_game_over_on_hp_depletion()
    test_victory_on_exit()
    test_line_of_sight_wall_block()
    test_particle_lifecycle()
    test_floating_text_lifecycle()
    test_color_cycle()
    test_detection_skips_inactive_color()
    print("ALL 17 TESTS PASSED")
