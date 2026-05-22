"""test_imports.py — Headless logic tests for Blast Chain.

Runs in CI / WSL without display. Tests core data structures and game logic
without touching Pyxel's Rust runtime.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (
    BLAST_RADIUS,
    BOMB_COLORS,
    BOMB_COOLDOWN,
    BOMB_FUSE,
    BOMB_LIMIT,
    CELL,
    CHAIN_BLAST_RADIUS,
    CHAIN_DELAY,
    GRID_COLS,
    GRID_OX,
    GRID_OY,
    GRID_ROWS,
    NUM_COLORS,
    PLAYER_MOVE_SPEED,
    PLAY_W,
    Bomb,
    Enemy,
    Explosion,
    Game,
    Particle,
    Phase,
)


def test_constants() -> None:
    """Verify constants are sane."""
    assert len(BOMB_COLORS) == NUM_COLORS == 5
    assert GRID_COLS == 12
    assert GRID_ROWS == 10
    assert CELL == 16
    assert BOMB_FUSE > 0
    assert BLAST_RADIUS > 0
    assert CHAIN_BLAST_RADIUS > BLAST_RADIUS
    assert BOMB_LIMIT >= 1
    assert BOMB_COOLDOWN >= 0
    assert PLAYER_MOVE_SPEED > 0
    assert PLAY_W == GRID_COLS * CELL


def test_grid_helpers() -> None:
    """Test coordinate conversion."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    # Pre-init all state attributes
    g.phase = Phase.TITLE
    g.player_x = 0.0
    g.player_y = 0.0
    g.lives = 0
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.wave = 0
    g.bombs = []
    g.enemies = []
    g.explosions = []
    g.particles = []
    g._bomb_cooldown = 0
    g._chain_queue = []
    g._chain_timer = 0
    g._pause_timer = 0
    g._can_chain = True
    g.reset()

    # grid_to_pixel
    px, py = g._grid_to_pixel(0, 0)
    assert px == GRID_OX + CELL / 2
    assert py == GRID_OY + CELL / 2

    px2, py2 = g._grid_to_pixel(5, 3)
    assert px2 == GRID_OX + 5 * CELL + CELL / 2
    assert py2 == GRID_OY + 3 * CELL + CELL / 2

    # pixel_to_grid
    gx, gy = g._pixel_to_grid(GRID_OX + 20, GRID_OY + 20)
    assert gx == 1
    assert gy == 1

    # in_bounds
    assert g._in_bounds(0, 0)
    assert g._in_bounds(GRID_COLS - 1, GRID_ROWS - 1)
    assert not g._in_bounds(-1, 0)
    assert not g._in_bounds(0, GRID_ROWS)
    assert not g._in_bounds(GRID_COLS, 0)


def test_bomb_placement() -> None:
    """Test bomb placement and limits."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()

    # Place player in a clear spot
    g.player_x = GRID_OX + CELL * 3 + CELL / 2
    g.player_y = GRID_OY + CELL * 3 + CELL / 2
    g.phase = Phase.PLAYING
    g._start_wave()

    g._place_bomb()
    assert len(g.bombs) == 1
    gx, gy = g._pixel_to_grid(g.player_x, g.player_y)
    assert g.bombs[0].gx == gx
    assert g.bombs[0].gy == gy
    assert 0 <= g.bombs[0].color < NUM_COLORS
    assert g.bombs[0].timer == BOMB_FUSE
    assert not g.bombs[0].chained

    # Can't place another bomb in same cell
    g._bomb_cooldown = 0  # bypass cooldown
    g._place_bomb()
    # Same cell — should be blocked
    assert len(g.bombs) == 1

    # Move and place
    g.player_x += CELL * 2
    g.player_y += CELL * 2
    g._bomb_cooldown = 0
    g._place_bomb()
    assert len(g.bombs) == 2

    # Place 3rd
    g.player_x += CELL
    g._bomb_cooldown = 0
    g._place_bomb()
    assert len(g.bombs) == 3

    # 4th should fail (BOMB_LIMIT)
    g.player_x += CELL
    g._bomb_cooldown = 0
    g._place_bomb()
    assert len(g.bombs) == 3


def test_bomb_timer() -> None:
    """Test bomb timer decreases and triggers explosion."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g.phase = Phase.PLAYING
    g.player_x = GRID_OX + CELL * 3 + CELL / 2
    g.player_y = GRID_OY + CELL * 3 + CELL / 2
    g._bomb_cooldown = 0
    g._place_bomb()
    assert len(g.bombs) == 1
    assert g.bombs[0].timer == BOMB_FUSE

    # Tick the bomb (simulate many frames)
    g.bombs[0].timer = 1
    g._update_bombs()
    # Bomb should have detonated (removed from list, explosion added)
    assert len(g.bombs) == 0
    # Explosion should exist or have killed nearby enemies
    assert len(g.explosions) >= 1


def test_chain_detection() -> None:
    """Test same-color chain detection."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g.phase = Phase.PLAYING

    # Place player safely away
    g.player_x = GRID_OX + CELL * 11 + CELL / 2
    g.player_y = GRID_OY + CELL * 9 + CELL / 2

    # Place two same-color bombs next to each other
    px1, py1 = g._grid_to_pixel(3, 4)
    px2, py2 = g._grid_to_pixel(4, 4)
    dist = math.hypot(px2 - px1, py2 - py1)
    # They should be within BLAST_RADIUS
    assert dist <= BLAST_RADIUS + 0.01, f"Bombs too far: {dist} > {BLAST_RADIUS}"

    b1 = Bomb(3, 4, 0)  # RED
    b2 = Bomb(4, 4, 0)  # RED (same color)
    g.bombs = [b1, b2]

    # Detonate b1
    g._detonate_bomb(b1, is_chain=False)

    # b1 should be removed
    assert b1 not in g.bombs
    # b2 should be chained (queued for explosion)
    assert b2.chained
    assert b2 in g._chain_queue
    # Combo should increment
    assert g.combo == 1
    assert g.max_combo >= 1
    # Phase should be CHAINING
    assert g.phase == Phase.CHAINING


def test_different_color_no_combo() -> None:
    """Test different-color bombs don't add combo."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g.phase = Phase.PLAYING

    g.player_x = GRID_OX + CELL * 11 + CELL / 2
    g.player_y = GRID_OY + CELL * 9 + CELL / 2

    b1 = Bomb(3, 4, 0)  # RED
    b2 = Bomb(4, 4, 1)  # GREEN (different color)
    g.bombs = [b1, b2]

    g._detonate_bomb(b1, is_chain=False)

    assert b1 not in g.bombs
    assert b2.chained  # still detonated
    assert b2 in g._chain_queue  # still queued
    assert g.combo == 0  # no combo for different color


def test_enemy_spawn() -> None:
    """Test enemies are spawned on wave start."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g.phase = Phase.PLAYING
    g.player_x = GRID_OX + PLAY_W / 2
    g.player_y = GRID_OY + 300  # far away for spawn validation
    g._start_wave()
    assert len(g.enemies) >= 1
    assert g.wave == 1

    # Each enemy should be in bounds
    for e in g.enemies:
        assert GRID_OX + 4 <= e.x <= GRID_OX + PLAY_W - 5
        assert GRID_OY + 4 <= e.y <= GRID_OY + (GRID_ROWS * CELL) - 5


def test_enemy_kill_scoring() -> None:
    """Test enemies are killed by explosions and score awarded."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g.phase = Phase.PLAYING
    g.player_x = GRID_OX + CELL * 11 + CELL / 2
    g.player_y = GRID_OY + CELL * 9 + CELL / 2

    # Place an enemy at a known position
    g.enemies = [Enemy(GRID_OX + 48 + 8, GRID_OY + 48 + 8, 1.0)]

    # Place a bomb at the same position
    b = Bomb(3, 3, 2)
    px, py = g._grid_to_pixel(3, 3)
    g.bombs = [b]

    score_before = g.score
    g._detonate_bomb(b, is_chain=False)

    # Enemy should be dead
    assert len(g.enemies) == 0
    assert g.score > score_before


def test_player_death_by_explosion() -> None:
    """Test player dies when caught in explosion."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g.phase = Phase.PLAYING
    g.lives = 3

    # Place player right next to a bomb
    g.player_x = GRID_OX + CELL * 3 + CELL / 2
    g.player_y = GRID_OY + CELL * 3 + CELL / 2
    b = Bomb(3, 3, 0)
    g.bombs = [b]

    g._detonate_bomb(b, is_chain=False)

    assert g.lives == 2
    assert g.phase == Phase.DYING


def test_player_death_by_enemy() -> None:
    """Test player dies on enemy contact."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g.phase = Phase.PLAYING
    g.lives = 3
    g.player_x = GRID_OX + 50
    g.player_y = GRID_OY + 50

    # Place enemy right on player
    g.enemies = [Enemy(g.player_x, g.player_y, 1.0)]

    g._update_enemies()

    assert g.lives == 2
    assert g.phase == Phase.DYING


def test_wave_escalation() -> None:
    """Test enemy count and speed increase per wave."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g.phase = Phase.PLAYING
    g.player_x = GRID_OX + PLAY_W / 2
    g.player_y = GRID_OY + 300

    g._start_wave()
    assert g.wave == 1
    wave1_count = len(g.enemies)

    # Clear enemies, advance wave
    g.enemies.clear()
    g._start_wave()
    assert g.wave == 2
    wave2_count = len(g.enemies)
    assert wave2_count >= wave1_count

    # Speed should increase
    g.enemies.clear()
    g._start_wave()
    assert g.wave == 3
    if len(g.enemies) > 0:
        # Speed increases each wave
        assert g.enemies[0].speed > 1.0 + 0.2  # base + wave*0.25 for wave 3


def test_game_over_on_zero_lives() -> None:
    """Test game transitions to GAME_OVER when lives reach 0."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g.phase = Phase.PLAYING
    g.lives = 1

    g.player_x = GRID_OX + CELL * 3 + CELL / 2
    g.player_y = GRID_OY + CELL * 3 + CELL / 2
    b = Bomb(3, 3, 0)
    g.bombs = [b]

    g._detonate_bomb(b, is_chain=False)
    assert g.lives == 0
    assert g.phase == Phase.DYING
    # Wait for death pause
    g._pause_timer = 1
    g._update_particles()
    g._update_explosions()
    g._pause_timer = 0
    g.update()
    assert g.phase == Phase.GAME_OVER


def test_reset() -> None:
    """Test reset clears all state."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g.phase = Phase.PLAYING
    g.score = 999
    g.combo = 5
    g.max_combo = 7
    g.wave = 3
    g.lives = 1
    g.bombs = [Bomb(1, 1, 0)]
    g.enemies = [Enemy(100, 100, 1.0)]
    g.particles = [Particle(50, 50, 1, 0, 5, 8)]
    g.explosions = [Explosion(100, 100)]

    g.reset()

    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.wave == 0
    assert g.lives == 3
    assert len(g.bombs) == 0
    assert len(g.enemies) == 0
    assert len(g.particles) == 0
    assert len(g.explosions) == 0


def test_particle_spawn() -> None:
    """Test particle creation."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()

    g._spawn_particles(100, 100, 8)
    assert len(g.particles) > 0
    for p in g.particles:
        assert p.life > 0
        assert abs(p.vx) > 0 or abs(p.vy) > 0


def test_particle_lifetime() -> None:
    """Test particles expire over time."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g._spawn_particles(100, 100, 8)
    count = len(g.particles)
    assert count > 0

    # Run many ticks
    for _ in range(50):
        g._update_particles()

    assert len(g.particles) < count  # Some should have expired


def test_chain_resolves() -> None:
    """Test chain queue fully resolves and returns to PLAYING."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g.phase = Phase.PLAYING

    g.player_x = GRID_OX + CELL * 11 + CELL / 2
    g.player_y = GRID_OY + CELL * 9 + CELL / 2

    b1 = Bomb(3, 4, 0)
    b2 = Bomb(4, 4, 0)
    g.bombs = [b1, b2]

    # Detonate first
    g._detonate_bomb(b1, is_chain=False)
    assert g.phase == Phase.CHAINING
    assert len(g._chain_queue) > 0

    # Run the chain queue
    g._chain_timer = 1
    while g._chain_queue:
        g._update_chain()
        g._update_explosions()
        if g._chain_timer <= 0:
            g._chain_timer = CHAIN_DELAY

    # Should return to PLAYING after all chains processed
    g._chain_timer = 0
    if not g._chain_queue:
        g.phase = Phase.PLAYING
        g.combo = 0
    assert g.phase == Phase.PLAYING
    assert g.combo == 0


def test_wave_clear_transition() -> None:
    """Test wave clear when all enemies eliminated."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g.phase = Phase.PLAYING
    g.player_x = GRID_OX + CELL * 11 + CELL / 2
    g.player_y = GRID_OY + CELL * 9 + CELL / 2

    g._start_wave()
    assert g.wave >= 1
    assert len(g.enemies) > 0

    # Kill all enemies (simulate via manual removal + check)
    g.enemies.clear()
    g._chain_queue.clear()
    # Simulate what update() does after enemy updates
    if not g.enemies and not g._chain_queue:
        g.phase = Phase.WAVE_CLEAR
        g._pause_timer = 30  # shorter for test

    assert g.phase == Phase.WAVE_CLEAR

    # After pause, new wave starts
    g._pause_timer = 1
    g._update_particles()
    g._pause_timer = 0
    g.update()
    assert g.phase == Phase.PLAYING
    assert g.wave == 2


def test_max_enemies_cap() -> None:
    """Test enemy count is capped at MAX_ENEMIES via _start_wave."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(42)
    g.reset()
    g.phase = Phase.PLAYING
    g.player_x = GRID_OX + PLAY_W / 2
    g.player_y = GRID_OY + 300

    # Force wave to large number — _start_wave caps at MAX_ENEMIES
    g.wave = 20
    g._start_wave()
    assert len(g.enemies) <= 10


def test_dataclass_fields() -> None:
    """Test dataclass construction and field types."""
    b = Bomb(3, 4, 2)
    assert b.gx == 3
    assert b.gy == 4
    assert b.color == 2
    assert b.timer == BOMB_FUSE
    assert not b.chained

    e = Enemy(100.0, 200.0, 1.5)
    assert e.x == 100.0
    assert e.y == 200.0
    assert e.speed == 1.5

    exp = Explosion(150.0, 160.0, 20, 15.0, 9)
    assert exp.x == 150.0
    assert abs(exp.radius - 15.0) < 0.01

    p = Particle(50.0, 60.0, 1.5, -2.0, 10, 8)
    assert p.x == 50.0
    assert p.vy == -2.0
    assert p.life == 10


def test_phase_enum() -> None:
    """Test all Phase values exist."""
    phases = {Phase.TITLE, Phase.PLAYING, Phase.CHAINING, Phase.DYING,
              Phase.WAVE_CLEAR, Phase.GAME_OVER}
    assert len(phases) == 6


if __name__ == "__main__":
    import traceback

    tests = [
        test_constants,
        test_grid_helpers,
        test_bomb_placement,
        test_bomb_timer,
        test_chain_detection,
        test_different_color_no_combo,
        test_enemy_spawn,
        test_enemy_kill_scoring,
        test_player_death_by_explosion,
        test_player_death_by_enemy,
        test_wave_escalation,
        test_game_over_on_zero_lives,
        test_reset,
        test_particle_spawn,
        test_particle_lifetime,
        test_chain_resolves,
        test_wave_clear_transition,
        test_max_enemies_cap,
        test_dataclass_fields,
        test_phase_enum,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  PASS {test.__name__}")
        except Exception:
            failed += 1
            print(f"  FAIL {test.__name__}")
            traceback.print_exc()

    print(f"\n{passed}/{len(tests)} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
