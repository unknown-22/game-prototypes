"""test_imports.py — Headless logic tests for CELL SURGE."""
import sys

# Suppress pyxel import errors in headless environment
import unittest.mock as mock
mock_display = mock.MagicMock()
mock_display.return_value = None
sys.modules["pyxel"] = mock.MagicMock()
sys.modules["pyxel"].COLOR_BLACK = 0
sys.modules["pyxel"].COLOR_NAVY = 1
sys.modules["pyxel"].COLOR_PURPLE = 2
sys.modules["pyxel"].COLOR_GREEN = 3
sys.modules["pyxel"].COLOR_BROWN = 4
sys.modules["pyxel"].COLOR_DARK_BLUE = 5
sys.modules["pyxel"].COLOR_LIGHT_BLUE = 6
sys.modules["pyxel"].COLOR_WHITE = 7
sys.modules["pyxel"].COLOR_RED = 8
sys.modules["pyxel"].COLOR_ORANGE = 9
sys.modules["pyxel"].COLOR_YELLOW = 10
sys.modules["pyxel"].COLOR_LIME = 11
sys.modules["pyxel"].COLOR_CYAN = 12
sys.modules["pyxel"].COLOR_GRAY = 13
sys.modules["pyxel"].COLOR_PINK = 14
sys.modules["pyxel"].COLOR_PEACH = 15
sys.modules["pyxel"].MOUSE_BUTTON_LEFT = 0
sys.modules["pyxel"].MOUSE_BUTTON_RIGHT = 1
sys.modules["pyxel"].MOUSE_BUTTON_MIDDLE = 2
sys.modules["pyxel"].KEY_W = 0
sys.modules["pyxel"].KEY_A = 1
sys.modules["pyxel"].KEY_S = 2
sys.modules["pyxel"].KEY_D = 3
sys.modules["pyxel"].KEY_UP = 4
sys.modules["pyxel"].KEY_DOWN = 5
sys.modules["pyxel"].KEY_LEFT = 6
sys.modules["pyxel"].KEY_RIGHT = 7
sys.modules["pyxel"].KEY_SPACE = 8
sys.modules["pyxel"].btnp = mock.MagicMock(return_value=False)
sys.modules["pyxel"].btn = mock.MagicMock(return_value=False)
sys.modules["pyxel"].frame_count = 0
sys.modules["pyxel"].mouse_x = 0
sys.modules["pyxel"].mouse_y = 0

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/023_cell_surge")
from main import (  # noqa: E402
    CellState,
    Game,
    GRID_W,
    GRID_H,
    SYNTHESIS_THRESHOLD,
    MAX_ENERGY,
    TICK_INTERVAL,
    Phase,
)

# ── Test CellState ──
def test_cellstate_properties() -> None:
    """Test CellState owner properties."""
    empty = CellState(owner=0)
    assert empty.is_empty
    assert not empty.is_player
    assert not empty.is_enemy
    assert not empty.is_node

    player = CellState(owner=1)
    assert player.is_player
    assert not player.is_empty
    assert not player.is_enemy

    enemy = CellState(owner=5)
    assert enemy.is_enemy
    assert not enemy.is_player

    node = CellState(owner=1, is_node=True)
    assert node.is_node
    assert node.is_player  # nodes are still player-owned


# ── Test Game initialization ──
def test_game_init() -> None:
    """Test game state initialization via reset()."""
    g = Game.__new__(Game)
    g.reset()
    assert g.phase == Phase.PLAYING
    assert g.energy == MAX_ENERGY
    assert g.score == 0
    assert g.combo == 1
    assert g.nodes_created == 0
    assert g.tick_count == 0
    assert len(g.grid) == GRID_H
    assert len(g.grid[0]) == GRID_W
    assert g.cursor_x == GRID_W // 2
    assert g.cursor_y == GRID_H // 2


# ── Test grid cell types ──
def test_grid_all_empty_initially() -> None:
    """After reset, most cells should be empty (some enemies on edges)."""
    g = Game.__new__(Game)
    # Monkey-patch random.random to prevent edge enemies
    import random as rnd
    _old = rnd.random
    rnd.random = lambda: 0.99  # > 0.3, no edge enemies
    g.reset()
    rnd.random = _old

    empty_count = sum(1 for row in g.grid for c in row if c.is_empty)
    assert empty_count == GRID_W * GRID_H


# ── Test seed placement ──
def test_place_seed_on_empty() -> None:
    """Placing a seed on an empty cell should work."""
    g = Game.__new__(Game)
    import random as rnd
    _old = rnd.random
    rnd.random = lambda: 0.99
    g.reset()
    rnd.random = _old

    g.energy = MAX_ENERGY
    g._place_seed(5, 5)
    assert 1 <= g.grid[5][5].owner <= 4
    assert g.grid[5][5].is_player
    assert g.energy == MAX_ENERGY - 2


def test_place_seed_no_energy() -> None:
    """Placing a seed without energy should fail."""
    g = Game.__new__(Game)
    import random as rnd
    _old = rnd.random
    rnd.random = lambda: 0.99
    g.reset()
    rnd.random = _old

    g.energy = 0
    g._place_seed(5, 5)
    assert g.grid[5][5].is_empty
    assert g.message == "NO ENERGY"


def test_place_seed_on_occupied() -> None:
    """Placing a seed on occupied cell should fail."""
    g = Game.__new__(Game)
    import random as rnd
    _old = rnd.random
    rnd.random = lambda: 0.99
    g.reset()
    g.energy = MAX_ENERGY
    g._place_seed(5, 5)
    old_energy = g.energy
    g._place_seed(5, 5)
    assert g.energy == old_energy  # no additional cost
    assert g.message == "OCCUPIED"


# ── Test neighbors ──
def test_neighbors_center() -> None:
    """Center cell should have 4 neighbors."""
    g = Game.__new__(Game)
    neighbors = g._neighbors(5, 5)
    assert len(neighbors) == 4


def test_neighbors_corner() -> None:
    """Corner cell should have 2 neighbors."""
    g = Game.__new__(Game)
    neighbors = g._neighbors(0, 0)
    assert len(neighbors) == 2


def test_neighbors_edge() -> None:
    """Edge cell should have 3 neighbors."""
    g = Game.__new__(Game)
    neighbors = g._neighbors(0, 5)
    assert len(neighbors) == 3


# ── Test CA spread ──
def test_ca_spread_to_empty() -> None:
    """Player cells should spread to adjacent empty cells."""
    g = Game.__new__(Game)
    import random as rnd
    _old = rnd.random
    rnd.random = lambda: 0.99
    g.reset()
    rnd.random = _old

    # Place a seed
    g._place_seed(5, 5)
    owner = g.grid[5][5].owner
    assert owner >= 1

    # Spread
    g._spread_player_cells()
    spread_count = 0
    for nx, ny in g._neighbors(5, 5):
        if g.grid[ny][nx].owner == owner:
            spread_count += 1
    assert spread_count >= 1  # should spread to at least some neighbors


# ── Test flood fill ──
def test_flood_fill_single() -> None:
    """Flood fill on a single cell should return 1 cell."""
    g = Game.__new__(Game)
    import random as rnd
    _old = rnd.random
    rnd.random = lambda: 0.99
    g.reset()
    g._place_seed(5, 5)
    owner = g.grid[5][5].owner
    rnd.random = _old

    region = g._flood_fill(5, 5, owner, set())
    assert len(region) == 1
    assert (5, 5) in region


def test_flood_fill_connected() -> None:
    """Flood fill on connected cells should find all."""
    g = Game.__new__(Game)
    import random as rnd
    _old = rnd.random
    rnd.random = lambda: 0.99
    g.reset()
    # Manually place same-color cells
    g.grid[5][5] = CellState(owner=1)
    g.grid[5][6] = CellState(owner=1)
    g.grid[6][5] = CellState(owner=1)
    rnd.random = _old

    region = g._flood_fill(5, 5, 1, set())
    assert len(region) == 3
    assert (5, 5) in region
    assert (5, 6) in region
    assert (6, 5) in region


def test_flood_fill_different_color_boundary() -> None:
    """Flood fill should stop at different colored cells."""
    g = Game.__new__(Game)
    import random as rnd
    _old = rnd.random
    rnd.random = lambda: 0.99
    g.reset()
    g.grid[5][5] = CellState(owner=1)  # (x=5, y=5)
    g.grid[5][6] = CellState(owner=1)  # (x=6, y=5) — adjacent to (5,5)
    g.grid[5][7] = CellState(owner=2)  # (x=7, y=5) — different color
    rnd.random = _old

    region = g._flood_fill(5, 5, 1, set())
    assert len(region) == 2
    assert (5, 5) in region
    assert (6, 5) in region
    assert (7, 5) not in region


# ── Test synthesis ──
def test_synthesis_happens_at_threshold() -> None:
    """Region with >= SYNTHESIS_THRESHOLD cells should synthesize."""
    g = Game.__new__(Game)
    import random as rnd
    _old = rnd.random
    rnd.random = lambda: 0.99
    g.reset()
    rnd.random = _old

    # Create a connected region of size SYNTHESIS_THRESHOLD
    for i in range(SYNTHESIS_THRESHOLD):
        g.grid[5][i] = CellState(owner=1)

    initial_score = g.score
    initial_nodes = g.nodes_created
    g._check_synthesis()
    # Should have created a node
    assert g.nodes_created > initial_nodes
    assert g.score > initial_score
    # One cell should be a node
    node_count = sum(1 for row in g.grid for c in row if c.is_node)
    assert node_count == 1


def test_synthesis_below_threshold() -> None:
    """Region below SYNTHESIS_THRESHOLD should NOT synthesize."""
    g = Game.__new__(Game)
    import random as rnd
    _old = rnd.random
    rnd.random = lambda: 0.99
    g.reset()
    rnd.random = _old

    # Create a region of size threshold - 1
    for i in range(SYNTHESIS_THRESHOLD - 1):
        g.grid[5][i] = CellState(owner=1)

    initial_nodes = g.nodes_created
    g._check_synthesis()
    assert g.nodes_created == initial_nodes
    # All cells should still be player cells, not nodes
    for i in range(SYNTHESIS_THRESHOLD - 1):
        assert g.grid[5][i].is_player
        assert not g.grid[5][i].is_node


# ── Test enemy spread ──
def test_enemy_spread_to_empty() -> None:
    """Enemy cells should spread to adjacent empty cells."""
    g = Game.__new__(Game)
    import random as rnd
    _old = rnd.random
    rnd.random = lambda: 0.99
    g.reset()
    rnd.random = _old

    g.grid[5][5] = CellState(owner=5)  # enemy

    g._spread_enemy_cells()
    # At least one neighbor should become enemy
    enemy_neighbors = 0
    for nx, ny in g._neighbors(5, 5):
        if g.grid[ny][nx].is_enemy:
            enemy_neighbors += 1
    assert enemy_neighbors >= 1


def test_enemy_cannot_spread_to_node() -> None:
    """Enemy should not be able to spread into a node."""
    g = Game.__new__(Game)
    import random as rnd
    _old = rnd.random
    rnd.random = lambda: 0.99
    g.reset()
    rnd.random = _old

    g.grid[5][5] = CellState(owner=5)  # enemy
    g.grid[5][6] = CellState(owner=1, is_node=True)  # node adjacent

    g._spread_enemy_cells()
    # Node should still be a node
    assert g.grid[5][6].is_node
    assert g.grid[5][6].owner == 1


# ── Test energy ──
def test_energy_regen() -> None:
    """Energy should regenerate each tick."""
    g = Game.__new__(Game)
    import random as rnd
    _old = rnd.random
    rnd.random = lambda: 0.99
    g.reset()
    rnd.random = _old

    g.energy = 5
    g.tick_timer = TICK_INTERVAL - 1  # next call triggers tick
    g._update_tick()
    assert g.energy == 6  # regen 1


def test_energy_cap() -> None:
    """Energy should not exceed MAX_ENERGY."""
    g = Game.__new__(Game)
    import random as rnd
    _old = rnd.random
    rnd.random = lambda: 0.99
    g.reset()
    rnd.random = _old

    g.energy = MAX_ENERGY
    g._update_tick()
    assert g.energy == MAX_ENERGY


# ── Test win/lose ──
def test_defeat_condition() -> None:
    """Enemy controlling >= 50% cells should trigger defeat."""
    g = Game.__new__(Game)
    import random as rnd
    _old = rnd.random
    rnd.random = lambda: 0.99
    g.reset()
    rnd.random = _old

    total = GRID_W * GRID_H
    # Fill >= 50% with enemy
    for y in range(GRID_H):
        for x in range(GRID_W):
            if y * GRID_W + x < total // 2:
                g.grid[y][x] = CellState(owner=5)

    g._check_win_lose()
    assert g.phase == Phase.DEFEAT


def test_victory_condition() -> None:
    """All enemy eliminated + player cells exist = victory."""
    g = Game.__new__(Game)
    import random as rnd
    _old = rnd.random
    rnd.random = lambda: 0.99
    g.reset()
    rnd.random = _old

    # Place some player cells, no enemies
    g.grid[5][5] = CellState(owner=1)
    g._check_win_lose()
    assert g.phase == Phase.VICTORY


# ── Test combo ──
def test_combo_increases_on_synthesis() -> None:
    """Combo should increase after synthesis."""
    g = Game.__new__(Game)
    import random as rnd
    _old = rnd.random
    rnd.random = lambda: 0.99
    g.reset()
    rnd.random = _old

    assert g.combo == 1
    # Create a synthesizable region
    for i in range(SYNTHESIS_THRESHOLD):
        g.grid[5][i] = CellState(owner=1)
    g._check_synthesis()
    assert g.combo == 2
    assert g.combo_timer == 3


# ── Test particle count cap ──
def test_particle_cap() -> None:
    """Particle list should not exceed MAX_PARTICLES."""
    import pyxel as px
    g = Game.__new__(Game)
    import random as rnd
    _old = rnd.random
    rnd.random = lambda: 0.99
    g.reset()
    rnd.random = _old

    for _ in range(200):
        g._spawn_particles(150, 150, px.COLOR_RED, 5)
    assert len(g.particles) <= 50  # MAX_PARTICLES constant


# ── Run all tests ──
if __name__ == "__main__":
    import traceback

    tests = [
        ("test_cellstate_properties", test_cellstate_properties),
        ("test_game_init", test_game_init),
        ("test_grid_all_empty_initially", test_grid_all_empty_initially),
        ("test_place_seed_on_empty", test_place_seed_on_empty),
        ("test_place_seed_no_energy", test_place_seed_no_energy),
        ("test_place_seed_on_occupied", test_place_seed_on_occupied),
        ("test_neighbors_center", test_neighbors_center),
        ("test_neighbors_corner", test_neighbors_corner),
        ("test_neighbors_edge", test_neighbors_edge),
        ("test_ca_spread_to_empty", test_ca_spread_to_empty),
        ("test_flood_fill_single", test_flood_fill_single),
        ("test_flood_fill_connected", test_flood_fill_connected),
        ("test_flood_fill_different_color_boundary", test_flood_fill_different_color_boundary),
        ("test_synthesis_happens_at_threshold", test_synthesis_happens_at_threshold),
        ("test_synthesis_below_threshold", test_synthesis_below_threshold),
        ("test_enemy_spread_to_empty", test_enemy_spread_to_empty),
        ("test_enemy_cannot_spread_to_node", test_enemy_cannot_spread_to_node),
        ("test_energy_regen", test_energy_regen),
        ("test_energy_cap", test_energy_cap),
        ("test_defeat_condition", test_defeat_condition),
        ("test_victory_condition", test_victory_condition),
        ("test_combo_increases_on_synthesis", test_combo_increases_on_synthesis),
        ("test_particle_cap", test_particle_cap),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS {name}")
            passed += 1
        except Exception:
            print(f"  FAIL {name}")
            traceback.print_exc()
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
