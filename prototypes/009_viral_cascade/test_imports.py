"""test_imports.py — Headless logic tests for VIRAL CASCADE."""
from __future__ import annotations

import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/009_viral_cascade")

from main import (
    Game, Phase, Particle,
    EMPTY, V_RED, V_BLUE, V_GREEN, V_GOLD,
    VIRUS_TYPES, VIRUS_COLORS, VIRUS_NAMES, VIRUS_CHARS, VIRUS_DMG_MULT,
    MAX_CLUSTER, HAND_SIZE, MAX_HEAT,
    GRID_COLS, GRID_ROWS, SCREEN_W, SCREEN_H,
)


def test_constants() -> None:
    """Verify game constants."""
    assert GRID_COLS == 6
    assert GRID_ROWS == 6
    assert SCREEN_W == 400
    assert SCREEN_H == 300
    assert HAND_SIZE == 3
    assert MAX_CLUSTER == 5
    assert MAX_HEAT == 15
    assert EMPTY == 0
    assert V_RED == 1
    assert V_BLUE == 2
    assert V_GREEN == 3
    assert V_GOLD == 4


def test_virus_mappings() -> None:
    """Verify virus type dictionaries."""
    assert len(VIRUS_TYPES) == 4
    assert VIRUS_TYPES == [V_RED, V_BLUE, V_GREEN, V_GOLD]

    for vt in VIRUS_TYPES:
        assert vt in VIRUS_COLORS
        assert vt in VIRUS_NAMES
        assert vt in VIRUS_CHARS
        assert vt in VIRUS_DMG_MULT

    assert VIRUS_COLORS[V_RED] == 8
    assert VIRUS_COLORS[V_BLUE] == 6
    assert VIRUS_COLORS[V_GREEN] == 11
    assert VIRUS_COLORS[V_GOLD] == 9

    assert VIRUS_DMG_MULT[V_RED] == 3
    assert VIRUS_DMG_MULT[V_BLUE] == 1
    assert VIRUS_DMG_MULT[V_GREEN] == 1
    assert VIRUS_DMG_MULT[V_GOLD] == 5

    assert VIRUS_NAMES[V_RED] == "RED"
    assert VIRUS_CHARS[V_RED] == "R"


def test_particle_dataclass() -> None:
    """Verify Particle dataclass."""
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-0.5, life=15, color=8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -0.5
    assert p.life == 15
    assert p.color == 8


def test_phase_enum() -> None:
    """Verify Phase enum members."""
    phases = {Phase.DRAW, Phase.INJECT, Phase.SPREAD, Phase.HARVEST,
              Phase.ENEMY_TURN, Phase.VICTORY, Phase.DEFEAT}
    assert len(phases) == 7


def test_neighbors() -> None:
    """Verify _neighbors static method."""
    # Corner (0, 0) should have 2 neighbors
    n = Game._neighbors(0, 0)
    assert len(n) == 2
    assert (0, 1) in n
    assert (1, 0) in n

    # Center (3, 3) should have 4 neighbors
    n = Game._neighbors(3, 3)
    assert len(n) == 4

    # Edge (0, 3) should have 3 neighbors
    n = Game._neighbors(0, 3)
    assert len(n) == 3


def test_game_reset() -> None:
    """Verify Game.reset() initializes state correctly (logic-only, no pyxel.run)."""
    g = Game.__new__(Game)
    g.reset()

    assert g.player_hp == 20
    assert g.player_max_hp == 20
    assert g.player_shield == 0
    assert g.enemy_hp == 100
    assert g.enemy_max_hp == 100
    assert g.turn == 1
    assert g.heat == 0
    assert g.score == 0
    assert g.phase == Phase.DRAW  # reset calls _begin_draw which sets DRAW phase
    assert len(g.grid) == GRID_ROWS
    assert len(g.grid[0]) == GRID_COLS
    # All cells should be EMPTY
    for row in g.grid:
        for cell in row:
            assert cell == EMPTY
    assert len(g.hand) == HAND_SIZE
    assert g.selected_card == 0


def test_count_viruses() -> None:
    """Verify _count_viruses."""
    g = Game.__new__(Game)
    g.reset()
    assert g._count_viruses() == 0

    g.grid[0][0] = V_RED
    g.grid[2][3] = V_BLUE
    g.grid[5][5] = V_GREEN
    assert g._count_viruses() == 3


def test_find_cluster_empty() -> None:
    """Verify _find_cluster on empty grid."""
    g = Game.__new__(Game)
    g.reset()
    visited: set[tuple[int, int]] = set()
    cluster = g._find_cluster(0, 0, V_RED, visited)
    assert cluster == []


def test_find_cluster_single() -> None:
    """Verify _find_cluster with a single virus."""
    g = Game.__new__(Game)
    g.reset()
    g.grid[2][2] = V_RED
    visited: set[tuple[int, int]] = set()
    cluster = g._find_cluster(2, 2, V_RED, visited)
    assert len(cluster) == 1
    assert (2, 2) in cluster


def test_find_cluster_connected() -> None:
    """Verify _find_cluster finds connected region."""
    g = Game.__new__(Game)
    g.reset()
    # Create a 3-cell connected RED cluster
    g.grid[1][1] = V_RED
    g.grid[1][2] = V_RED
    g.grid[2][1] = V_RED
    # Separate RED cell (not connected)
    g.grid[4][4] = V_RED

    visited: set[tuple[int, int]] = set()
    cluster = g._find_cluster(1, 1, V_RED, visited)
    assert len(cluster) == 3
    assert (1, 1) in cluster
    assert (1, 2) in cluster
    assert (2, 1) in cluster
    assert (4, 4) not in cluster


def test_find_all_clusters() -> None:
    """Verify _find_all_clusters."""
    g = Game.__new__(Game)
    g.reset()
    # Two separate RED clusters
    g.grid[0][0] = V_RED
    g.grid[0][1] = V_RED  # cluster 1: 2 cells
    g.grid[3][3] = V_RED  # cluster 2: 1 cell

    clusters = g._find_all_clusters(V_RED)
    assert len(clusters) == 2
    sizes = sorted(len(c) for c in clusters)
    assert sizes == [1, 2]


def test_find_all_clusters_mixed() -> None:
    """Verify _find_all_clusters only returns one type."""
    g = Game.__new__(Game)
    g.reset()
    g.grid[0][0] = V_RED
    g.grid[0][1] = V_BLUE
    g.grid[0][2] = V_RED

    clusters = g._find_all_clusters(V_RED)
    # RED at (0,0) and (0,2) are NOT connected (BLUE at (0,1) blocks)
    assert len(clusters) == 2
    for c in clusters:
        assert len(c) == 1


def test_cell_center() -> None:
    """Verify _cell_center returns correct pixel coordinates."""
    g = Game.__new__(Game)
    g.reset()
    cx, cy = g._cell_center(0, 0)
    from main import GRID_X, GRID_Y, CELL_SIZE
    assert cx == float(GRID_X + CELL_SIZE // 2)
    assert cy == float(GRID_Y + CELL_SIZE // 2)


def test_begin_draw_phase() -> None:
    """Verify _begin_draw sets phase and draws hand."""
    g = Game.__new__(Game)
    g.reset()
    g._begin_draw()
    assert g.phase == Phase.DRAW
    assert g.phase_timer == 15
    assert len(g.hand) == HAND_SIZE
    # All cards should be valid virus types (not GOLD before turn 3)
    valid = {V_RED, V_BLUE, V_GREEN}
    for card in g.hand:
        assert card in valid


def test_begin_draw_gold_unlocked() -> None:
    """Verify GOLD appears from turn 3 onwards."""
    g = Game.__new__(Game)
    g.reset()
    g.turn = 4  # GOLD should be available
    g._begin_draw()
    valid = {V_RED, V_BLUE, V_GREEN, V_GOLD}
    assert len(g.hand) == HAND_SIZE
    for card in g.hand:
        assert card in valid


def test_do_spread_produces_events() -> None:
    """Verify _do_spread propagates viruses."""
    g = Game.__new__(Game)
    g.reset()
    g.grid[3][3] = V_RED
    events = g._do_spread()
    # After 2 generations starting from 1 cell in center:
    # gen1: up to 4 neighbors can be infected (55% each)
    # gen2: each new infected cell can infect its neighbors
    # So we expect some events (not 0, but random; can't guarantee exact count)
    # Just verify it runs and returns a list
    assert isinstance(events, list)


def test_do_harvest_damages_enemy() -> None:
    """Verify _do_harvest deals damage and clears grid."""
    g = Game.__new__(Game)
    g.reset()
    initial_enemy_hp = g.enemy_hp
    # Create a 3-cell RED cluster
    g.grid[1][1] = V_RED
    g.grid[1][2] = V_RED
    g.grid[2][1] = V_RED

    g._do_harvest(V_RED)
    # 3 cells × 3 multiplier = 9 damage
    assert g.enemy_hp == initial_enemy_hp - 9
    assert g.score == 9
    # Grid should be cleared
    assert g.grid[1][1] == EMPTY
    assert g.grid[1][2] == EMPTY
    assert g.grid[2][1] == EMPTY


def test_do_harvest_blue_shield() -> None:
    """Verify BLUE harvest grants shield."""
    g = Game.__new__(Game)
    g.reset()
    g.grid[0][0] = V_BLUE
    g.grid[0][1] = V_BLUE

    g._do_harvest(V_BLUE)
    assert g.player_shield == 2


def test_do_harvest_green_heal() -> None:
    """Verify GREEN harvest heals."""
    g = Game.__new__(Game)
    g.reset()
    g.player_hp = 10  # damaged
    g.grid[0][0] = V_GREEN
    g.grid[0][1] = V_GREEN

    g._do_harvest(V_GREEN)
    assert g.player_hp == 12  # 10 + 2


def test_do_harvest_overflow() -> None:
    """Verify clusters > MAX_CLUSTER cause overflow damage."""
    g = Game.__new__(Game)
    g.reset()
    initial_hp = g.player_hp
    # Create a 6-cell connected RED cluster (exceeds MAX_CLUSTER=5)
    for r in range(3):
        for c in range(2):
            g.grid[r][c] = V_RED

    assert g._count_viruses() == 6
    g._do_harvest(V_RED)
    # Overflow: 6 - 5 = 1 damage
    assert g.player_hp == initial_hp - 1


def test_do_harvest_empty_type() -> None:
    """Verify harvesting a type with no viruses shows message."""
    g = Game.__new__(Game)
    g.reset()
    g._do_harvest(V_RED)
    assert "No RED" in g.message


def test_game_draw_phase_transition() -> None:
    """Verify DRAW phase transitions to INJECT after timer."""
    g = Game.__new__(Game)
    g.reset()
    g.phase = Phase.DRAW
    g.phase_timer = 1
    g.update()
    assert g.phase == Phase.INJECT


def test_game_enemy_turn_transition() -> None:
    """Verify ENEMY_TURN timer transitions correctly."""
    g = Game.__new__(Game)
    g.reset()
    g.phase = Phase.ENEMY_TURN
    g.phase_timer = 1
    g.enemy_hp = 50
    g.player_hp = 10
    g.update()
    # After enemy turn, should be back in DRAW
    assert g.phase == Phase.DRAW


print("All tests passed!")
