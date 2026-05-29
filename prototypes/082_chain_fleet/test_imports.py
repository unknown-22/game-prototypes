"""test_imports.py — Headless logic tests for CHAIN FLEET (082)."""
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/082_chain_fleet")
import random
from main import (
    Game, ShipCell, Particle, FloatingText,
    GRID_W, GRID_H, CELL_SIZE, GRID_OX, GRID_OY,
    SHIP_SIZES, SHIP_COLORS, MAX_HEAT, MAX_HP, SURGE_DURATION,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.reset()
    return g


def _make_game_with_fleet() -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.reset()
    g._rng = random.Random(42)
    g._start_game()
    return g


# ── Constants ────────────────────────────────────────────────────────────

def test_constants():
    assert GRID_W == 10
    assert GRID_H == 8
    assert CELL_SIZE == 24
    assert GRID_OX == 40
    assert GRID_OY == 24
    assert len(SHIP_SIZES) == 5
    assert sum(SHIP_SIZES) == 14
    assert len(SHIP_COLORS) == 4
    assert SHIP_COLORS == (8, 3, 6, 10)
    assert MAX_HEAT == 8
    assert MAX_HP == 3


# ── Reset / initial state ────────────────────────────────────────────────

def test_reset_initial_state():
    g = _make_game()
    assert g.phase == "TITLE"
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.last_hit_color is None
    assert g.heat == 0
    assert g.hp == MAX_HP
    assert g.score == 0
    assert g.ships_remaining == 0
    assert g.surge_cells == []
    assert g.surge_timer == 0
    assert g.particles == []
    assert g.floating_texts == []
    assert not g._mouse_was_pressed
    for row in g.revealed:
        assert all(not r for r in row)


def test_start_game_builds_fleet():
    g = _make_game()
    g._rng = random.Random(42)
    g._start_game()
    assert g.phase == "PLAYING"
    assert g.total_ship_cells > 0
    assert g.ships_remaining == g.total_ship_cells
    assert g.combo == 0
    assert g.heat == 0
    assert g.hp == MAX_HP
    assert g.score == 0


def test_generate_fleet_deterministic():
    g1 = _make_game()
    g2 = _make_game()
    g1._rng = random.Random(42)
    g2._rng = random.Random(42)
    g1._start_game()
    g2._start_game()
    assert g1.total_ship_cells == g2.total_ship_cells
    # Check same ship positions
    for y in range(GRID_H):
        for x in range(GRID_W):
            c1 = g1.cells[y][x]
            c2 = g2.cells[y][x]
            if c1 is not None:
                assert c2 is not None
                assert c1.color == c2.color
            else:
                assert c2 is None


def test_total_ship_cells_matches_sum():
    g = _make_game()
    g._rng = random.Random(42)
    g._start_game()
    expected = sum(SHIP_SIZES)
    assert g.total_ship_cells == expected


# ── Click handling ───────────────────────────────────────────────────────

def test_click_ship_hit():
    g = _make_game_with_fleet()
    # Find first ship cell
    sx, sy = -1, -1
    for y in range(GRID_H):
        for x in range(GRID_W):
            if g.cells[y][x] is not None and not g.revealed[y][x]:
                sx, sy = x, y
                break
        if sx >= 0:
            break

    g._handle_click(sx, sy)
    assert g.revealed[sy][sx]
    assert g.combo == 1
    assert g.score >= 10
    assert g.ships_remaining == g.total_ship_cells - 1


def test_click_miss():
    g = _make_game_with_fleet()
    # Find empty cell
    for y in range(GRID_H):
        for x in range(GRID_W):
            if g.cells[y][x] is None:
                g._handle_click(x, y)
                assert g.revealed[y][x]
                assert g.combo == 0
                assert g.heat == 1
                return
    assert False, "No empty cell found"


def test_click_already_revealed_ignored():
    g = _make_game_with_fleet()
    # Find and click a cell
    for y in range(GRID_H):
        for x in range(GRID_W):
            if g.cells[y][x] is not None:
                g._handle_click(x, y)
                old_score = g.score
                old_combo = g.combo
                old_ships = g.ships_remaining
                g._handle_click(x, y)  # click again
                assert g.score == old_score
                assert g.combo == old_combo
                assert g.ships_remaining == old_ships
                return
    assert False


# ── Combo mechanics ──────────────────────────────────────────────────────

def test_same_color_combo_builds():
    g = _make_game_with_fleet()
    g.last_hit_color = SHIP_COLORS[0]
    g.combo = 2
    # Place a same-color ship manually
    g.cells[0][0] = ShipCell(x=0, y=0, color=SHIP_COLORS[0])
    g.cells[0][1] = ShipCell(x=1, y=0, color=SHIP_COLORS[0])
    g.revealed[0][1] = True  # already revealed
    g.ships_remaining = 1
    g.total_ship_cells = 2

    g._handle_click(0, 0)
    assert g.combo == 3  # increased
    assert g.score >= 10 * (1 + 3)


def test_different_color_resets_combo():
    g = _make_game_with_fleet()
    g.last_hit_color = SHIP_COLORS[0]
    g.combo = 3
    g.cells[0][0] = ShipCell(x=0, y=0, color=SHIP_COLORS[1])
    g.ships_remaining = 1
    g.total_ship_cells = 2

    g._handle_click(0, 0)
    assert g.combo == 1  # reset to 1
    assert g.last_hit_color == SHIP_COLORS[1]


def test_miss_resets_combo():
    g = _make_game_with_fleet()
    g.last_hit_color = SHIP_COLORS[0]
    g.combo = 3
    g.cells[0][0] = None
    g._handle_click(0, 0)
    assert g.combo == 0
    assert g.last_hit_color is None


def test_heat_causes_enemy_strike():
    g = _make_game_with_fleet()
    g.heat = MAX_HEAT - 1
    g.cells[0][0] = None
    g._handle_click(0, 0)
    assert g.hp == MAX_HP - 1
    assert g.heat == 0


# ── SURGE mechanics ──────────────────────────────────────────────────────

def test_bfs_surge_finds_same_color_adjacent():
    g = _make_game()
    g._rng = random.Random(42)
    g._start_game()
    g.combo = 3
    g.last_hit_color = SHIP_COLORS[0]

    # Manually put same-color ship cells in a cluster
    color = SHIP_COLORS[0]
    g.cells[0][0] = ShipCell(x=0, y=0, color=color)
    g.cells[0][1] = ShipCell(x=1, y=0, color=color)
    g.cells[0][2] = ShipCell(x=2, y=0, color=color)
    g.cells[1][0] = ShipCell(x=0, y=1, color=color)
    g.ships_remaining = 4
    g.total_ship_cells = 4
    for row in g.revealed:
        for i in range(len(row)):
            row[i] = False

    g._surge(0, 0, color)
    # Should reveal adjacent same-color cells: (1,0), (2,0), (0,1)
    revealed_count = sum(1 for gx, gy in [(1, 0), (2, 0), (0, 1)] if g.revealed[gy][gx])
    assert revealed_count == 3
    assert g.ships_remaining <= 1


def test_bfs_surge_stops_at_different_color():
    g = _make_game()
    g._rng = random.Random(42)
    g._start_game()
    color = SHIP_COLORS[0]
    g.cells[0][0] = ShipCell(x=0, y=0, color=color)
    g.cells[0][1] = ShipCell(x=1, y=0, color=SHIP_COLORS[1])  # different color
    g.cells[0][2] = ShipCell(x=2, y=0, color=color)
    g.ships_remaining = 3
    g.total_ship_cells = 3
    for row in g.revealed:
        for i in range(len(row)):
            row[i] = False

    g._surge(0, 0, color)
    # (1,0) is different color, should NOT be revealed
    assert not g.revealed[0][1]
    # (2,0) is same color but not reachable via BFS (blocked by diff color), so NOT revealed
    assert not g.revealed[0][2]


def test_bfs_surge_expands_through_chain():
    g = _make_game()
    g._rng = random.Random(42)
    g._start_game()
    color = SHIP_COLORS[0]
    # Create a chain: (0,0) -> (1,0) -> (1,1) -> (2,1) all same color
    g.cells[0][0] = ShipCell(x=0, y=0, color=color)
    g.cells[0][1] = ShipCell(x=1, y=0, color=color)
    g.cells[1][1] = ShipCell(x=1, y=1, color=color)
    g.cells[1][2] = ShipCell(x=2, y=1, color=color)
    g.ships_remaining = 4
    g.total_ship_cells = 4
    for row in g.revealed:
        for i in range(len(row)):
            row[i] = False

    g._surge(0, 0, color)
    assert g.revealed[0][1]  # (1,0)
    assert g.revealed[1][1]  # (1,1)
    assert g.revealed[1][2]  # (2,1)
    # surge reveals 3 cells, (0,0) was already handled
    assert g.ships_remaining == 1


# ── Win/Lose conditions ──────────────────────────────────────────────────

def test_win_when_all_ships_revealed_via_hit():
    g = _make_game_with_fleet()
    g._rng = random.Random(42)
    g._start_game()
    # Reveal all but one
    g.ships_remaining = 1
    g.total_ship_cells = 1
    # Place one ship
    g.cells[0][0] = ShipCell(x=0, y=0, color=SHIP_COLORS[0])
    g.revealed[0][0] = False
    g.last_hit_color = SHIP_COLORS[0]
    g.combo = 2

    g._handle_click(0, 0)
    assert g.phase == "GAME_OVER"
    assert g._win_result == "VICTORY"


def test_lose_when_hp_zero():
    g = _make_game_with_fleet()
    g.hp = 1
    g.heat = MAX_HEAT - 1
    g.cells[0][0] = None
    g._handle_click(0, 0)
    assert g.hp == 0
    assert g.phase == "GAME_OVER"
    assert g._win_result == "DEFEATED"


# ── Particles ────────────────────────────────────────────────────────────

def test_spawn_hit_particles():
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_hit_particles(100.0, 100.0, SHIP_COLORS[0])
    assert len(g.particles) == 6
    for p in g.particles:
        assert p.color == SHIP_COLORS[0]
        assert p.life == 12


def test_spawn_miss_particles():
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_miss_particles(100.0, 100.0)
    assert len(g.particles) == 4
    for p in g.particles:
        assert p.color == 13  # GRAY
        assert p.life == 8


def test_spawn_surge_particles():
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_surge_particles(100.0, 100.0, SHIP_COLORS[0])
    assert len(g.particles) == 4
    for p in g.particles:
        assert p.color == 7  # WHITE
        assert p.life == 15


def test_update_particles_removes_expired():
    g = _make_game()
    g.particles = [
        Particle(x=0, y=0, vx=1, vy=1, color=8, life=1),
        Particle(x=0, y=0, vx=1, vy=1, color=8, life=5),
    ]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 4


# ── Floating texts ───────────────────────────────────────────────────────

def test_spawn_floating_text():
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_floating_text(100.0, 100.0, "+10", SHIP_COLORS[0])
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.text == "+10"
    assert ft.color == SHIP_COLORS[0]
    assert ft.life == 30


def test_update_floating_texts_removes_expired():
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=0, y=0, text="A", life=1, color=7),
        FloatingText(x=0, y=0, text="B", life=5, color=7),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "B"
    assert g.floating_texts[0].life == 4


def test_update_floating_texts_moves_up():
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=0, y=100.0, text="A", life=5, color=7),
    ]
    g._update_floating_texts()
    assert g.floating_texts[0].y == 99.5


# ── Max combo tracking ───────────────────────────────────────────────────

def test_max_combo_tracked():
    g = _make_game_with_fleet()
    g.combo = 0
    g.last_hit_color = SHIP_COLORS[0]
    g.max_combo = 0

    g.cells[0][0] = ShipCell(x=0, y=0, color=SHIP_COLORS[0])
    g.cells[0][1] = ShipCell(x=1, y=0, color=SHIP_COLORS[0])
    g.cells[0][2] = ShipCell(x=2, y=0, color=SHIP_COLORS[0])
    g.ships_remaining = 3
    g.total_ship_cells = 3

    for i in range(3):
        g._handle_click(i, 0)
    assert g.max_combo == 3
    assert g.combo == 3


# ── SURGE duration ────────────────────────────────────────────────────────

def test_surge_timer_sets_and_clears():
    g = _make_game()
    g._rng = random.Random(42)
    g._start_game()
    color = SHIP_COLORS[0]
    g.cells[0][0] = ShipCell(x=0, y=0, color=color)
    g.cells[0][1] = ShipCell(x=1, y=0, color=color)
    g.ships_remaining = 2
    g.total_ship_cells = 2
    g.revealed[0][0] = True
    g.revealed[0][1] = False
    g.combo = 3
    g.last_hit_color = color

    g._surge(0, 0, color)
    assert g.surge_timer == SURGE_DURATION
    assert len(g.surge_cells) > 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
