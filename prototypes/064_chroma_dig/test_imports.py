"""test_imports.py — Headless logic tests for 064_chroma_dig."""
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/064_chroma_dig")
from main import Game, Enemy, Rock, Particle, COLS, ROWS, CELL, NUM_COLORS, DIRT_COLORS, MAX_LIVES
import random


def _make_game(seed: int = 42) -> Game:
    """Factory: create Game bypassing __init__ (no pyxel.init needed)."""
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.grid = [[-1 for _ in range(COLS)] for _ in range(ROWS)]
    g.player_x = COLS // 2
    g.player_y = 1
    g.combo = 0
    g.max_combo = 0
    g.last_dug_color = None
    g.score = 0
    g.lives = MAX_LIVES
    g.level = 1
    g.enemies = []
    g.rocks = []
    g.particles = []
    g.phase = "playing"
    g.invuln_timer = 0
    g.level_clear_timer = 0
    g.reset()
    return g


def _make_blank_game(seed: int = 42) -> Game:
    """Factory: create blank Game (all empty) without reset()."""
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.grid = [[-1 for _ in range(COLS)] for _ in range(ROWS)]
    g.player_x = COLS // 2
    g.player_y = 1
    g.combo = 0
    g.max_combo = 0
    g.last_dug_color = None
    g.score = 0
    g.lives = MAX_LIVES
    g.level = 1
    g.enemies = []
    g.rocks = []
    g.particles = []
    g.phase = "playing"
    g.invuln_timer = 0
    g.level_clear_timer = 0
    return g


# ── Dataclass tests ──

def test_enemy_dataclass():
    e = Enemy(x=5, y=3)
    assert e.x == 5
    assert e.y == 3
    assert e.move_timer == 0

def test_rock_dataclass():
    r = Rock(x=7, y=2)
    assert r.x == 7
    assert r.y == 2
    assert r.fall_timer == 0
    assert not r.falling

def test_particle_dataclass():
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=15, color=8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == 8

# ── Grid helpers ──

def test_is_dirt():
    g = _make_game(42)
    assert not g._is_dirt(5, 0)
    assert not g._is_dirt(5, 1)
    assert g._is_dirt(5, 2)
    assert not g._is_dirt(-1, 5)
    assert not g._is_dirt(5, -1)
    assert not g._is_dirt(COLS, 5)
    assert not g._is_dirt(5, ROWS)

def test_is_empty():
    g = _make_game(42)
    assert g._is_empty(5, 0)
    assert g._is_empty(5, 1)
    assert not g._is_empty(5, 2)

def test_is_rock():
    g = _make_game(42)
    rock_cells = [(r.x, r.y) for r in g.rocks]
    for x, y in rock_cells:
        assert g._is_rock(x, y)

def test_is_enemy():
    g = _make_game(42)
    enemy_cells = [(e.x, e.y) for e in g.enemies]
    for x, y in enemy_cells:
        assert g._is_enemy(x, y)

# ── Level generation ──

def test_generate_level_fills_grid():
    g = _make_game(42)
    for y in range(2, ROWS):
        for x in range(COLS):
            assert g._is_dirt(x, y), f"Expected dirt at ({x},{y})"
    for y in range(2):
        for x in range(COLS):
            assert g._is_empty(x, y), f"Expected empty at ({x},{y})"

def test_generate_level_spawns_enemies():
    g = _make_game(42)
    assert len(g.enemies) == 2

def test_generate_level_spawns_rocks():
    g = _make_game(42)
    assert 5 <= len(g.rocks) <= 8

def test_level_2_more_enemies():
    g = _make_game(42)
    g.level = 2
    g._generate_level()
    assert len(g.enemies) == 3

# ── Dig mechanics ──

def test_dig_same_color_combo():
    g = _make_blank_game(42)
    g.grid[2][5] = 0  # row 2, col 5 = RED
    g.grid[2][6] = 0  # row 2, col 6 = RED

    g.player_x = 5
    g.player_y = 2
    g._dig(5, 2)
    assert g.combo == 1
    assert g._is_empty(5, 2)

    g.player_x = 6
    g.player_y = 2
    g._dig(6, 2)
    assert g.combo == 2
    assert g.max_combo == 2

def test_dig_different_color_resets_combo():
    g = _make_blank_game(42)
    g.grid[2][5] = 0  # RED
    g.grid[2][6] = 1  # GREEN

    g.player_x = 5
    g.player_y = 2
    g._dig(5, 2)
    assert g.combo == 1

    g.player_x = 6
    g.player_y = 2
    g._dig(6, 2)
    assert g.combo == 1  # Reset

def test_dig_empty_no_op():
    g = _make_blank_game(42)
    old_score = g.score
    old_combo = g.combo
    g._dig(5, 0)  # Already empty
    assert g.score == old_score
    assert g.combo == old_combo

def test_dig_gives_score():
    g = _make_blank_game(42)
    g.grid[2][5] = 0  # row 2, col 5
    g.player_x = 5
    g.player_y = 2
    g.score = 0
    g._dig(5, 2)
    assert g.score == 10

def test_dig_combo_score_increases():
    g = _make_blank_game(42)
    g.grid[2][5] = 0
    g.grid[2][6] = 0

    g.player_x = 5
    g.player_y = 2
    g.score = 0
    g._dig(5, 2)
    assert g.score == 10
    g.player_x = 6
    g.player_y = 2
    g._dig(6, 2)
    assert g.score == 30

# ── BFS ──

def test_bfs_empty_single_cell():
    g = _make_blank_game(42)
    # Create one isolated empty cell
    g.grid[5][5] = -1
    region = g._bfs_empty(5, 5)
    assert (5, 5) in region

def test_bfs_empty_region_size():
    g = _make_game(42)
    region = g._bfs_empty(0, 0)
    assert len(region) == COLS * 2  # Top 2 rows connected

def test_bfs_same_color_dirt_small_patch():
    g = _make_blank_game(42)
    # Create 3x3 patch of color 0, surrounded by other colors
    for y in range(5, 8):
        for x in range(5, 8):
            g.grid[y][x] = 0
    # Surround with different color to isolate
    for y in range(4, 9):
        for x in range(4, 9):
            if g.grid[y][x] == -1:
                g.grid[y][x] = 1

    chain = g._bfs_same_color_dirt(6, 6, 0)
    assert len(chain) == 9  # 3x3

def test_bfs_same_color_dirt_stops_at_different_color():
    g = _make_blank_game(42)
    g.grid[5][5] = 0  # RED
    g.grid[5][6] = 1  # GREEN

    chain = g._bfs_same_color_dirt(5, 5, 0)
    assert len(chain) == 1

def test_bfs_same_color_dirt_stops_at_empty():
    g = _make_blank_game(42)
    g.grid[5][5] = 0  # RED, isolated (all neighbors are empty -1)
    # No surrounding dirt of same color
    chain = g._bfs_same_color_dirt(5, 5, 0)
    assert len(chain) == 1  # Only itself

# ── Converge detection ──

def test_check_converge_no_empty_neighbors():
    g = _make_blank_game(42)
    # Cell (10, 7) surrounded by dirt (color 1, not empty)
    g.grid[7][9] = 1
    g.grid[7][10] = 1
    g.grid[7][11] = 1
    g.grid[6][10] = 1
    g.grid[8][10] = 1
    assert not g._check_converge(10, 7)

def test_check_converge_two_separate_regions():
    g = _make_blank_game(42)
    # Fill ALL cells with dirt first to prevent BFS from going around through empty cells
    for y in range(ROWS):
        for x in range(COLS):
            g.grid[y][x] = 1
    # Create two separate empty regions divided by dirt
    g.grid[5][4] = -1  # Empty region 1
    g.grid[5][6] = -1  # Empty region 2
    g.grid[5][5] = 0   # Dirt between them
    # Barrier: fill surrounding cells with dirt (color 1) so empty regions can't connect
    for y in range(5, 7):
        for x in range(4, 7):
            if g.grid[y][x] == -1 and (x, y) not in [(4, 5), (6, 5)]:
                g.grid[y][x] = 1
    # Now (5,4) empty and (5,6) empty are separated by dirt at (5,5)
    # Also, fill cells around so they're truly isolated
    g.grid[4][4] = 1; g.grid[4][5] = 1; g.grid[4][6] = 1
    g.grid[6][4] = 1; g.grid[6][5] = 1; g.grid[6][6] = 1

    assert g._check_converge(5, 5)

def test_check_converge_same_region_no_converge():
    g = _make_blank_game(42)
    # One connected empty region
    g.grid[5][4] = -1
    g.grid[5][5] = -1  # Connected
    g.grid[5][6] = -1  # Connected
    # Barrier around the region
    for y in range(4, 7):
        for x in range(3, 8):
            if g.grid[y][x] == -1:
                g.grid[y][x] = 1
    g.grid[5][4] = -1
    g.grid[5][5] = -1
    g.grid[5][6] = -1

    # Cell (5,7) has neighbor (5,6) which is empty, all same region
    g.grid[5][7] = 0  # This is dirt we're checking
    # Fill around (5,7) with dirt to isolate
    g.grid[4][7] = 1; g.grid[6][7] = 1

    assert not g._check_converge(5, 7)

# ── Chain collapse (via _dig) ──

def test_dig_with_converge_triggers_chain():
    g = _make_blank_game(42)
    # Create two separate empty regions with same-color dirt bridge
    # Grid layout (col,row): cells are indexed grid[row][col]
    # Fill all with color 1 (different from bridge) as barrier
    for y in range(ROWS):
        for x in range(COLS):
            g.grid[y][x] = 1

    g.grid[5][4] = -1   # Empty region 1 at (4,5)
    g.grid[5][6] = -1   # Empty region 2 at (6,5)
    g.grid[5][5] = 0    # Bridge dirt at (5,5), color 0
    g.grid[6][5] = 0    # Extra dirt at (5,6), color 0

    g.player_x = 5
    g.player_y = 5
    old_score = g.score
    g._dig(5, 5)

    # (5,5) cleared; converge triggered; chain BFS from (5,5) color 0 finds {(5,5), (5,6)}
    # Wait — BFS runs AFTER clearing (5,5), so grid[5][5] = -1 already
    # _bfs_same_color_dirt(5,5,0): starts at (5,5) which is now -1.
    # visited adds (5,5). Then neighbors: (4,5)=1(≠0), (6,5)=0→ADD, (5,4)=1(≠0), (5,6)=1(≠0)
    # From (6,5)=0: neighbors: (5,5)=-1(≠0), (7,5)=1(≠0), (6,4)=1(≠0), (6,6)=1(≠0)
    # BFS result: {(5,5), (6,5)} = 2 cells
    # chain_score = 2 * 50 * combo(1) = 100
    # dig_score = 10 * combo(1) = 10
    # total = 110
    assert g._is_empty(5, 5)
    assert g._is_empty(6, 5)  # row 6, col 5 → (5,6)
    assert g.score == old_score + 110

def test_dig_with_converge_kills_adjacent_enemy():
    g = _make_blank_game(42)
    for y in range(ROWS):
        for x in range(COLS):
            g.grid[y][x] = 1  # Barrier

    g.grid[5][4] = -1   # Empty region 1
    g.grid[5][6] = -1   # Empty region 2
    g.grid[5][5] = 0    # Bridge, color 0
    g.grid[6][5] = 0    # Extra dirt at (5,6), color 0

    # Enemy adjacent to (5,6) — neighbor of chain cell
    # Chain cell (6,5) has neighbor (6,6) in killed_positions
    g.enemies = [Enemy(x=6, y=6)]  # At (6,6)

    assert len(g.enemies) == 1
    g.player_x = 5
    g.player_y = 5
    g._dig(5, 5)

    # Enemy at (6,6) should be in killed_positions (neighbor of chain cell (6,5))
    assert len(g.enemies) == 0
    assert g.score >= 200  # Enemy kill bonus

# ── Player movement ──

def test_move_player_into_dirt_digs():
    g = _make_blank_game(42)
    g.grid[2][5] = 0

    g.player_x = 5
    g.player_y = 1
    g._move_player(0, 1)
    assert g.player_x == 5
    assert g.player_y == 2
    assert g._is_empty(5, 2)
    assert g.combo == 1

def test_move_player_blocked_by_rock():
    g = _make_blank_game(42)
    g.rocks = [Rock(x=5, y=3)]

    g.player_x = 5
    g.player_y = 2
    old_x, old_y = g.player_x, g.player_y
    g._move_player(0, 1)  # Try to move into rock
    # Player should NOT have moved
    assert g.player_x == old_x
    assert g.player_y == old_y

def test_move_player_boundary():
    g = _make_blank_game(42)
    g.player_x = 0
    g.player_y = 1
    g._move_player(-1, 0)
    assert g.player_x == 0
    assert g.player_y == 1

# ── Enemy movement ──

def test_update_enemies_timer_increments():
    g = _make_blank_game(42)
    g.enemies = [Enemy(x=5, y=5)]
    g.player_x = 10
    g.player_y = 5

    old_timer = g.enemies[0].move_timer
    g._update_enemies()
    assert g.enemies[0].move_timer == old_timer + 1

def test_move_enemy_toward_player():
    g = _make_blank_game(42)
    g.player_x = 10
    g.player_y = 5
    enemy = Enemy(x=5, y=5)
    g.enemies = [enemy]

    g._move_enemy(enemy)
    new_dist = abs(enemy.x - 10) + abs(enemy.y - 5)
    assert new_dist <= 5

def test_move_enemy_stuck_no_valid_moves():
    g = _make_blank_game(42)
    enemy = Enemy(x=5, y=5)
    g.enemies = [enemy]
    g.rocks = [
        Rock(x=5, y=4), Rock(x=5, y=6),
        Rock(x=4, y=5), Rock(x=6, y=5)
    ]
    g.player_x = 10
    g.player_y = 5

    old_x, old_y = enemy.x, enemy.y
    g._move_enemy(enemy)
    assert enemy.x == old_x
    assert enemy.y == old_y

# ── Rock physics ──

def test_rock_falls_when_unsupported():
    g = _make_blank_game(42)
    rock = Rock(x=5, y=3)
    g.rocks = [rock]

    old_y = rock.y
    for _ in range(20):
        g._update_rocks()

    assert rock.y > old_y or rock.falling

def test_rock_stops_on_dirt():
    g = _make_blank_game(42)
    g.grid[6][5] = 0  # Dirt at (5,6)
    rock = Rock(x=5, y=4)
    g.rocks = [rock]

    for _ in range(40):
        g._update_rocks()

    assert rock.y <= 6
    assert not rock.falling

def test_rock_kills_enemy():
    g = _make_blank_game(42)
    enemy = Enemy(x=5, y=6)
    g.enemies = [enemy]
    rock = Rock(x=5, y=4)
    g.rocks = [rock]

    for _ in range(60):
        g._update_rocks()

    assert len(g.enemies) == 0
    assert g.score >= 200

def test_rock_falls_off_screen():
    g = _make_blank_game(42)
    rock = Rock(x=5, y=ROWS - 1)
    g.rocks = [rock]

    for _ in range(30):
        g._update_rocks()

    assert len(g.rocks) == 0

# ── Player hit ──

def test_player_hit_reduces_lives():
    g = _make_blank_game(42)
    g.lives = 3
    g._player_hit()
    assert g.lives == 2
    assert g.invuln_timer > 0

def test_player_hit_game_over():
    g = _make_blank_game(42)
    g.lives = 1
    g._player_hit()
    assert g.lives == 0
    assert g.phase == "game_over"

def test_player_hit_resets_combo():
    g = _make_blank_game(42)
    g.combo = 5
    g.last_dug_color = 0
    g.lives = 3
    g._player_hit()
    assert g.combo == 0
    assert g.last_dug_color is None

def test_player_hit_invuln_prevents_double_hit():
    g = _make_blank_game(42)
    g.lives = 3
    g._player_hit()
    assert g.lives == 2
    g._player_hit()
    assert g.lives == 2

# ── Enemy collision ──

def test_check_enemy_collision_triggers_hit():
    g = _make_blank_game(42)
    g.lives = 3
    g.enemies = [Enemy(x=5, y=3)]
    g.player_x = 5
    g.player_y = 3
    g._check_enemy_collision()
    assert g.lives == 2

def test_check_enemy_collision_invuln():
    g = _make_blank_game(42)
    g.lives = 3
    g.invuln_timer = 10
    g.enemies = [Enemy(x=5, y=3)]
    g.player_x = 5
    g.player_y = 3
    g._check_enemy_collision()
    assert g.lives == 3

# ── Combo & max_combo ──

def test_max_combo_tracks_highest():
    g = _make_blank_game(42)
    for i in range(5):
        g.grid[2][5 + i] = 0

    g.player_x = 5
    g.player_y = 2
    for i in range(5):
        g.player_x = 5 + i
        g.player_y = 2
        g._dig(5 + i, 2)

    assert g.max_combo == 5

# ── Collapse chain utility ──

def test_collapse_chain_clears_cells():
    g = _make_blank_game(42)
    g.grid[5][5] = 0  # row 5, col 5 → (5,5)
    g.grid[5][6] = 0  # row 5, col 6 → (6,5)
    g.combo = 3

    # _collapse_chain returns the score, does NOT add to self.score
    result = g._collapse_chain({(5, 5), (6, 5)})
    # 2 dirt cells × 50 × combo(3) = 300
    assert result == 300
    assert g._is_empty(5, 5)
    assert g._is_empty(6, 5)

def test_collapse_chain_skips_non_dirt():
    g = _make_blank_game(42)
    # (5,5) is empty, (6,5) is dirt
    g.grid[5][6] = 0  # row 5, col 6 → (6,5)
    g.combo = 1

    result = g._collapse_chain({(5, 5), (6, 5)})
    assert result == 50  # Only one dirt cell × 50 × 1

# ── State reset ──

def test_reset_clears_state():
    g = _make_game(42)
    g.score = 9999
    g.combo = 10
    g.lives = 1
    g.level = 5

    g.reset()
    # reset() calls _generate_level which resets some things
    assert g.combo == 0
    assert g.score == 0
    assert g.phase == "title"

# ── Level clear ──

def test_level_clear_advances_level():
    g = _make_blank_game(42)
    g.enemies = []
    g.level = 3
    g.phase = "level_clear"
    g.level_clear_timer = 1
    g.level_clear_timer -= 1
    if g.level_clear_timer <= 0:
        g.level += 1
        g._generate_level()
        g.phase = "playing"

    assert g.level == 4
    assert g.phase == "playing"


if __name__ == "__main__":
    import traceback
    tests = [v for k, v in globals().items() if k.startswith("test_")]
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
    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    if failed:
        sys.exit(1)
