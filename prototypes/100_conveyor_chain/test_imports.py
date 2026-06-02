"""test_imports.py -- Headless logic tests for 100_conveyor_chain."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (
    COLS,
    ROWS,
    CELL,
    GRID_X,
    GRID_Y,
    SCREEN_H,
    MAX_HEAT,
    CHAIN_THRESHOLD,
    SUPER_SCORE_MULT,
    SPAWN_INTERVAL_INIT,
    SPAWN_INTERVAL_MIN,
    DIFFICULTY_INTERVAL,
    RED,
    YELLOW,
    WHITE,
    ITEM_COLORS,
    RAINBOW_COLORS,
    Phase,
    Item,
    OutputBin,
    Particle,
    FloatingText,
    Game,
)


def _make_game(seed: int = 42) -> Game:
    """Factory for headless Game instances bypassing Pyxel init."""
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.phase = Phase.TITLE
    g.tiles = []
    g.items = []
    g.bins = []
    g.particles = []
    g.floating_texts = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0
    g.super_count = 0
    g.spawn_interval = SPAWN_INTERVAL_INIT
    g.spawn_timer = 0
    g.difficulty_timer = 0
    g.game_timer = 0
    g._active_colors = [0, 1]
    g.reset()
    g._rng = random.Random(seed)
    return g


# ── Tile Rotation ───────────────────────────────────────────────────────────

def test_tile_initial_direction_down():
    """All tiles start with direction=1 (down)."""
    g = _make_game()
    for r in range(ROWS):
        for c in range(COLS):
            assert g.tiles[r][c].direction == 1


def test_rotate_tile_increments():
    """Rotating a tile increments direction modulo 4."""
    g = _make_game()
    g._rotate_tile(0, 0)
    assert g.tiles[0][0].direction == 2
    g._rotate_tile(0, 0)
    assert g.tiles[0][0].direction == 3
    g._rotate_tile(0, 0)
    assert g.tiles[0][0].direction == 0
    g._rotate_tile(0, 0)
    assert g.tiles[0][0].direction == 1


def test_rotate_tile_bounds():
    """Rotation works at grid boundaries."""
    g = _make_game()
    g._rotate_tile(7, 7)
    assert g.tiles[7][7].direction == 2
    g._rotate_tile(0, 7)
    assert g.tiles[7][0].direction == 2


# ── Item Movement ───────────────────────────────────────────────────────────

def test_item_direction_down():
    """Item moves down when tile direction=1."""
    g = _make_game()
    g.tiles[0][3].direction = 1
    item = Item(col=3, row=0, color=0)
    g.items = [item]
    dc, dr = g._item_direction(item)
    assert (dc, dr) == (0, 1)


def test_item_direction_right():
    """Item moves right when tile direction=0."""
    g = _make_game()
    g.tiles[0][3].direction = 0
    item = Item(col=3, row=0, color=0)
    g.items = [item]
    dc, dr = g._item_direction(item)
    assert (dc, dr) == (1, 0)


def test_item_direction_left():
    """Item moves left when tile direction=2."""
    g = _make_game()
    g.tiles[0][3].direction = 2
    item = Item(col=3, row=0, color=0)
    g.items = [item]
    dc, dr = g._item_direction(item)
    assert (dc, dr) == (-1, 0)


def test_item_direction_up():
    """Item moves up when tile direction=3."""
    g = _make_game()
    g.tiles[0][3].direction = 3
    item = Item(col=3, row=0, color=0)
    g.items = [item]
    dc, dr = g._item_direction(item)
    assert (dc, dr) == (0, -1)


def test_move_items_updates_position():
    """_move_items updates item col/row based on tile direction."""
    g = _make_game()
    g.tiles[0][3].direction = 1  # down
    item = Item(col=3, row=0, color=0)
    g.items = [item]
    g._move_items()
    assert item.col == 3
    assert item.row == 1


def test_move_items_right():
    """Move right."""
    g = _make_game()
    g.tiles[0][3].direction = 0  # right
    item = Item(col=3, row=0, color=0)
    g.items = [item]
    g._move_items()
    assert item.col == 4
    assert item.row == 0


# ── Bin Arrival ─────────────────────────────────────────────────────────────

def test_check_bin_arrival_not_arrived():
    """Items still in grid return empty list."""
    g = _make_game()
    g.items = [Item(col=3, row=5, color=0)]
    arrivals = g._check_bin_arrival()
    assert len(arrivals) == 0


def test_check_bin_arrival_bottom():
    """Item at row >= ROWS triggers arrival."""
    g = _make_game()
    g.items = [Item(col=3, row=ROWS, color=0)]
    arrivals = g._check_bin_arrival()
    assert len(arrivals) == 1


def test_check_bin_arrival_left_edge():
    """Item at col < 0 triggers arrival."""
    g = _make_game()
    g.items = [Item(col=-1, row=0, color=0)]
    arrivals = g._check_bin_arrival()
    assert len(arrivals) == 1


def test_check_bin_arrival_right_edge():
    """Item at col >= COLS triggers arrival."""
    g = _make_game()
    g.items = [Item(col=COLS, row=0, color=0)]
    arrivals = g._check_bin_arrival()
    assert len(arrivals) == 1


def test_get_bin_at_exists():
    """_get_bin_at returns the bin at the given column."""
    g = _make_game()
    g.bins = [OutputBin(col=3, target_color=0)]
    b = g._get_bin_at(3)
    assert b is not None
    assert b.target_color == 0


def test_get_bin_at_missing():
    """_get_bin_at returns None for columns without bins."""
    g = _make_game()
    g.bins = [OutputBin(col=3, target_color=0)]
    b = g._get_bin_at(5)
    assert b is None


# ── Score & Arrival Processing ──────────────────────────────────────────────

def test_process_arrival_match_no_combo():
    """Correct bin + no combo = 10 points."""
    g = _make_game()
    g.combo = 0
    item = Item(col=3, row=0, color=0)
    bin_ = OutputBin(col=3, target_color=0)
    gained = g._process_arrival(item, bin_)
    assert gained == 10
    assert g.score == 10


def test_process_arrival_match_with_combo():
    """Correct bin + combo=3 = 30 points."""
    g = _make_game()
    g.combo = 3
    item = Item(col=3, row=0, color=0)
    bin_ = OutputBin(col=3, target_color=0)
    gained = g._process_arrival(item, bin_)
    assert gained == 30
    assert g.score == 30


def test_process_arrival_mismatch_adds_heat():
    """Wrong color adds 15 heat."""
    g = _make_game()
    g.heat = 10
    item = Item(col=3, row=0, color=0)
    bin_ = OutputBin(col=3, target_color=1)  # GREEN, not RED
    gained = g._process_arrival(item, bin_)
    assert gained == 0
    assert g.heat == 25


def test_process_arrival_no_bin():
    """Column with no bin adds heat."""
    g = _make_game()
    g.heat = 10
    item = Item(col=3, row=0, color=0)
    gained = g._process_arrival(item, None)
    assert gained == 0
    assert g.heat == 25


def test_process_arrival_super_item():
    """SUPER item always scores 3x (with combo multiplier)."""
    g = _make_game()
    g.combo = 2
    item = Item(col=3, row=0, color=0, super_item=True)
    bin_ = OutputBin(col=3, target_color=1)  # wrong color, but super ignores
    gained = g._process_arrival(item, bin_)
    assert gained == 10 * SUPER_SCORE_MULT * 2  # 60
    assert g.score == 60
    assert g.super_count == 1


def test_process_arrival_heat_caps():
    """Heat does not exceed MAX_HEAT."""
    g = _make_game()
    g.heat = 95
    item = Item(col=3, row=0, color=0)
    g._process_arrival(item, None)
    assert g.heat == MAX_HEAT


# ── Chain Detection ─────────────────────────────────────────────────────────

def test_detect_chains_none():
    """No items = no chains."""
    g = _make_game()
    g.items = []
    g._detect_chains()
    assert all(not it.chained for it in g.items)


def test_detect_chains_single_item():
    """Single item is not chained."""
    g = _make_game()
    g.items = [Item(col=3, row=2, color=0)]
    g._detect_chains()
    assert not g.items[0].chained


def test_detect_chains_two_adjacent():
    """Two adjacent same-color items form a chain."""
    g = _make_game()
    g.items = [
        Item(col=3, row=2, color=0),
        Item(col=3, row=3, color=0),
    ]
    g._detect_chains()
    assert g.items[0].chained
    assert g.items[1].chained


def test_detect_chains_different_colors():
    """Different colors do not chain even if adjacent."""
    g = _make_game()
    g.items = [
        Item(col=3, row=2, color=0),
        Item(col=3, row=3, color=1),
    ]
    g._detect_chains()
    assert not g.items[0].chained
    assert not g.items[1].chained


def test_detect_chains_diagonal_not_chain():
    """Diagonal adjacency does not form a chain."""
    g = _make_game()
    g.items = [
        Item(col=3, row=2, color=0),
        Item(col=4, row=3, color=0),
    ]
    g._detect_chains()
    assert not g.items[0].chained
    assert not g.items[1].chained


def test_detect_chains_horizontal():
    """Horizontal adjacent same-color items chain."""
    g = _make_game()
    g.items = [
        Item(col=3, row=2, color=0),
        Item(col=4, row=2, color=0),
    ]
    g._detect_chains()
    assert g.items[0].chained
    assert g.items[1].chained


def test_detect_chains_three_line():
    """Three same-color items in a line all chain."""
    g = _make_game()
    g.items = [
        Item(col=3, row=2, color=0),
        Item(col=3, row=3, color=0),
        Item(col=3, row=4, color=0),
    ]
    g._detect_chains()
    assert all(it.chained for it in g.items)


# ── COMBO Processing ────────────────────────────────────────────────────────

def test_process_chains_no_chains():
    """No chains = no combo increase."""
    g = _make_game()
    g.items = [Item(col=3, row=2, color=0)]
    g._detect_chains()
    g._process_chains()
    assert g.combo == 0


def test_process_chains_below_threshold():
    """Chain of 2 = no COMBO trigger."""
    g = _make_game()
    g.combo = 0
    g.score = 0
    g.items = [
        Item(col=3, row=2, color=0),
        Item(col=3, row=3, color=0),
    ]
    g._detect_chains()
    g._process_chains()
    assert g.combo == 0


def test_process_chains_triggers_combo():
    """Chain of 3 triggers COMBO, adds score, makes lead SUPER."""
    g = _make_game()
    g.combo = 0
    g.score = 0
    g.items = [
        Item(col=3, row=2, color=0),
        Item(col=3, row=3, color=0),
        Item(col=3, row=4, color=0),
    ]
    g._detect_chains()
    g._process_chains()
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score == 5  # combo * 5
    assert g.items[0].super_item


def test_process_chains_multiple_combos():
    """Multiple chains each trigger COMBO increment."""
    g = _make_game()
    g.combo = 0
    g.score = 0
    g.items = [
        Item(col=3, row=2, color=0),
        Item(col=3, row=3, color=0),
        Item(col=3, row=4, color=0),
        Item(col=5, row=2, color=1),
        Item(col=5, row=3, color=1),
        Item(col=5, row=4, color=1),
    ]
    g._detect_chains()
    g._process_chains()
    assert g.combo == 2
    assert g.max_combo == 2
    assert g.score == 5 + 10  # 5 + 10 = 15
    assert g.items[0].super_item
    assert g.items[3].super_item


def test_process_chains_max_combo_tracks():
    """max_combo is never reset during a game."""
    g = _make_game()
    g.combo = 5
    g.max_combo = 5
    g.items = [
        Item(col=3, row=2, color=0),
        Item(col=3, row=3, color=0),
        Item(col=3, row=4, color=0),
    ]
    g._detect_chains()
    g._process_chains()
    assert g.max_combo == 6


# ── Spawning ────────────────────────────────────────────────────────────────

def test_spawn_item_creates_item():
    """_spawn_item returns an Item at row 0."""
    g = _make_game()
    item = g._spawn_item()
    assert item is not None
    assert item.row == 0
    assert 0 <= item.col < COLS
    assert item.color in g._active_colors


def test_spawn_item_blocked():
    """_spawn_item returns None if cell(0, col) occupied."""
    g = _make_game()
    g.items = [Item(col=3, row=0, color=0)]
    # Force spawn at col 3 (mock _rng)
    old_randint = g._rng.randint
    g._rng.randint = lambda a, b: 3  # type: ignore
    item = g._spawn_item()
    g._rng.randint = old_randint  # type: ignore
    assert item is None


# ── Difficulty ──────────────────────────────────────────────────────────────

def test_update_difficulty_reduces_spawn_interval():
    """After DIFFICULTY_INTERVAL frames, spawn_interval decreases."""
    g = _make_game()
    g.difficulty_timer = DIFFICULTY_INTERVAL - 1
    g._update_difficulty()
    assert g.spawn_interval < SPAWN_INTERVAL_INIT
    assert g.spawn_interval == SPAWN_INTERVAL_INIT - 3


def test_update_difficulty_spawn_interval_min():
    """spawn_interval does not go below SPAWN_INTERVAL_MIN."""
    g = _make_game()
    g.spawn_interval = SPAWN_INTERVAL_MIN
    g.difficulty_timer = DIFFICULTY_INTERVAL - 1
    g._update_difficulty()
    assert g.spawn_interval == SPAWN_INTERVAL_MIN


def test_update_difficulty_unlocks_colors():
    """Gradually unlocks all 4 colors."""
    g = _make_game()
    g._active_colors = [0, 1]
    g._rng = random.Random(42)
    # Force difficulty tick many times
    for _ in range(10):
        g.difficulty_timer = DIFFICULTY_INTERVAL - 1
        g._update_difficulty()
    assert len(g._active_colors) == 4


# ── Heat System ─────────────────────────────────────────────────────────────

def test_heat_passive_increase():
    """Heat increases by 1 every 60 frames."""
    g = _make_game()
    g.heat = 0
    g.game_timer = 60
    g._update_heat_passive()
    assert g.heat == 1

    g.game_timer = 120
    g._update_heat_passive()
    assert g.heat == 2


def test_heat_passive_not_every_frame():
    """Heat does not increase on non-60-divisible frames."""
    g = _make_game()
    g.heat = 0
    g.game_timer = 59
    g._update_heat_passive()
    assert g.heat == 0


def test_heat_passive_caps():
    """Passive heat caps at MAX_HEAT."""
    g = _make_game()
    g.heat = MAX_HEAT
    g.game_timer = 60
    g._update_heat_passive()
    assert g.heat == MAX_HEAT


def test_check_game_over_under_threshold():
    """heat < MAX_HEAT returns False."""
    g = _make_game()
    g.heat = 99
    assert not g._check_game_over()


def test_check_game_over_at_threshold():
    """heat >= MAX_HEAT returns True."""
    g = _make_game()
    g.heat = MAX_HEAT
    assert g._check_game_over()


# ── Reset ───────────────────────────────────────────────────────────────────

def test_reset_clears_state():
    """reset() reinitializes all game state."""
    g = _make_game()
    g.score = 999
    g.combo = 5
    g.heat = 80
    g.items = [Item(col=0, row=0, color=0)]
    g.phase = Phase.GAME_OVER

    g.reset()

    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0
    assert len(g.items) == 0
    assert g.phase == Phase.TITLE
    assert g.max_combo == 0
    assert g.super_count == 0
    assert g.spawn_interval == SPAWN_INTERVAL_INIT


def test_reset_creates_tiles():
    """reset() reinitializes tiles."""
    g = _make_game()
    g._rotate_tile(0, 0)
    g._rotate_tile(0, 0)
    g.reset()
    assert g.tiles[0][0].direction == 1
    assert len(g.tiles) == ROWS
    assert len(g.tiles[0]) == COLS


def test_reset_creates_bins():
    """reset() creates 4 bins."""
    g = _make_game()
    g.reset()
    assert len(g.bins) == 4
    cols_set = {b.col for b in g.bins}
    assert len(cols_set) == 4  # all unique columns
    colors_set = {b.target_color for b in g.bins}
    assert colors_set == {0, 1, 2, 3}


# ── Constants ───────────────────────────────────────────────────────────────

def test_cells_count():
    """Grid is 8x8."""
    assert COLS == 8
    assert ROWS == 8


def test_cell_size():
    """CELL is 26."""
    assert CELL == 26


def test_grid_centered():
    """GRID_X and GRID_Y are correctly computed."""
    assert GRID_X * 2 + COLS * CELL == 320
    assert GRID_Y >= 0
    assert GRID_Y + ROWS * CELL <= SCREEN_H


def test_chain_threshold():
    """COMBO threshold is 3."""
    assert CHAIN_THRESHOLD == 3


def test_super_score_mult():
    """SUPER score multiplier is 3."""
    assert SUPER_SCORE_MULT == 3


def test_max_heat():
    """MAX_HEAT is 100."""
    assert MAX_HEAT == 100


def test_rainbow_colors():
    """Rainbow has 6 colors."""
    assert len(RAINBOW_COLORS) == 6


def test_item_colors():
    """ITEM_COLORS has 4 entries."""
    assert len(ITEM_COLORS) == 4


# ── Phase Enum ──────────────────────────────────────────────────────────────

def test_phase_values():
    """Phase enum has TITLE, PLAYING, GAME_OVER."""
    assert Phase.TITLE is not None
    assert Phase.PLAYING is not None
    assert Phase.GAME_OVER is not None
    assert Phase.TITLE != Phase.PLAYING


# ── Floating Text ───────────────────────────────────────────────────────────

def test_add_floating_text():
    """Floating text is added to the list."""
    g = _make_game()
    g._add_floating_text(100.0, 200.0, "+10", YELLOW)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "+10"
    assert g.floating_texts[0].life == 20


# ── Particle/Text Update ────────────────────────────────────────────────────

def test_update_particles_decays():
    """Particles decay and are removed when life <= 0."""
    g = _make_game()
    g.particles = [Particle(x=10.0, y=10.0, vx=0.5, vy=-0.3, life=1, color=RED)]
    g._update_particles()
    assert len(g.particles) == 0


def test_update_floating_texts_decay():
    """Floating texts are removed when life <= 0."""
    g = _make_game()
    g.floating_texts = [FloatingText(x=10.0, y=10.0, text="hi", life=1, color=WHITE)]
    g._update_particles()
    assert len(g.floating_texts) == 0


# ── Bins Init ───────────────────────────────────────────────────────────────

def test_init_bins_all_colors():
    """_init_bins covers all 4 target colors."""
    g = _make_game()
    g._init_bins()
    targets = [b.target_color for b in g.bins]
    assert set(targets) == {0, 1, 2, 3}


def test_init_bins_unique_cols():
    """_init_bins assigns unique columns."""
    g = _make_game()
    g._init_bins()
    cols = [b.col for b in g.bins]
    assert len(set(cols)) == 4
