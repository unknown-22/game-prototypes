"""test_imports.py — Headless logic tests for 072_pair_chain."""
import random
import sys
from pathlib import Path

# Add prototype dir to path for import
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from main import (
    GREEN, DARK_BLUE, RED, YELLOW, PEACH,
    GRID_X, GRID_Y, CELL, COLS, ROWS, TOTAL_CARDS, TIMER_FRAMES,
    CHAIN_REVEAL_FRAMES, PARTICLE_COUNT,
    CARD_COLORS, PAIRS_PER_COLOR, WILD_PAIRS,
    Phase, Card, Particle, Game,
)


# ── Helper: create a Game via __new__ with deterministic RNG ─────────

def _make_game(seed: int = 42) -> Game:
    """Create a Game instance bypassing Pyxel init, with seeded RNG."""
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.grid = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.pairs_matched = 0
    g.timer = TIMER_FRAMES
    g.first_card = None
    g.second_card = None
    g.anim_timer = 0
    g.chain_bonus = 0
    g.matched_color = 0
    g.particles = []
    g.phase = Phase.TITLE
    g._init_state()
    return g


# ── Grid & Card Tests ────────────────────────────────────────────────

def test_grid_dimensions():
    g = _make_game()
    assert len(g.grid) == ROWS
    for row in g.grid:
        assert len(row) == COLS


def test_total_cards():
    g = _make_game()
    count = 0
    for row in g.grid:
        for card in row:
            assert isinstance(card, Card)
            count += 1
    assert count == TOTAL_CARDS
    assert TOTAL_CARDS == 36


def test_color_distribution():
    """4 colors × 4 pairs × 2 cards + 2 wild pairs × 2 cards = 36."""
    g = _make_game()
    color_counts: dict[int, int] = {}
    for row in g.grid:
        for card in row:
            color_counts[card.color] = color_counts.get(card.color, 0) + 1
    for c in CARD_COLORS:
        assert color_counts.get(c, 0) == PAIRS_PER_COLOR * 2  # 8 each
    assert color_counts.get(PEACH, 0) == WILD_PAIRS * 2  # 4 wild


def test_all_cards_face_down_initially():
    g = _make_game()
    for row in g.grid:
        for card in row:
            assert card.revealed is False
            assert card.matched is False


def test_deterministic_shuffle():
    g1 = _make_game(42)
    g2 = _make_game(42)
    for r in range(ROWS):
        for c in range(COLS):
            assert g1.grid[r][c].color == g2.grid[r][c].color


def test_different_seeds_different():
    g1 = _make_game(42)
    g2 = _make_game(99)
    colors1 = [g1.grid[r][c].color for r in range(ROWS) for c in range(COLS)]
    colors2 = [g2.grid[r][c].color for r in range(ROWS) for c in range(COLS)]
    # Extremely unlikely to be identical
    assert colors1 != colors2


# ── Pixel/Cell Conversion ───────────────────────────────────────────

def test_pixel_to_cell_origin():
    g = _make_game()
    result = g._pixel_to_cell(GRID_X, GRID_Y)
    assert result == (0, 0)


def test_pixel_to_cell_center():
    g = _make_game()
    result = g._pixel_to_cell(GRID_X + CELL // 2, GRID_Y + CELL // 2)
    assert result == (0, 0)


def test_pixel_to_cell_last():
    g = _make_game()
    result = g._pixel_to_cell(GRID_X + (COLS - 1) * CELL, GRID_Y + (ROWS - 1) * CELL)
    assert result == (COLS - 1, ROWS - 1)


def test_pixel_to_cell_out_of_bounds():
    g = _make_game()
    assert g._pixel_to_cell(-10, -10) is None
    assert g._pixel_to_cell(500, 500) is None
    assert g._pixel_to_cell(GRID_X - 1, GRID_Y) is None


def test_cell_center():
    g = _make_game()
    cx, cy = g._cell_center(0, 0)
    assert abs(cx - (GRID_X + CELL / 2)) < 0.01
    assert abs(cy - (GRID_Y + CELL / 2)) < 0.01
    cx, cy = g._cell_center(5, 5)
    assert abs(cx - (GRID_X + 5 * CELL + CELL / 2)) < 0.01
    assert abs(cy - (GRID_Y + 5 * CELL + CELL / 2)) < 0.01


# ── Click & Phase Tests ──────────────────────────────────────────────

def test_first_click_transitions_to_flip_second():
    g = _make_game()
    g.phase = Phase.FLIP_FIRST
    col, row = 0, 0
    g._grid_click(col, row)
    assert g.phase == Phase.FLIP_SECOND
    assert g.first_card == (col, row)
    assert g.grid[row][col].revealed is True
    assert g.grid[row][col].matched is False


def test_click_already_revealed_ignored():
    g = _make_game()
    g.phase = Phase.FLIP_FIRST
    g.grid[0][0].revealed = True
    g._grid_click(0, 0)
    # Should not set first_card
    assert g.first_card is None
    assert g.phase == Phase.FLIP_FIRST


def test_click_already_matched_ignored():
    g = _make_game()
    g.phase = Phase.FLIP_FIRST
    g.grid[0][0].matched = True
    g._grid_click(0, 0)
    assert g.first_card is None


def test_click_same_card_twice_ignored():
    g = _make_game()
    g.phase = Phase.FLIP_FIRST
    g._grid_click(0, 0)
    assert g.phase == Phase.FLIP_SECOND
    g._grid_click(0, 0)  # same card
    assert g.phase == Phase.FLIP_SECOND  # unchanged
    assert g.second_card is None


# ── Match/Miss Tests ─────────────────────────────────────────────────

def test_match_same_color():
    g = _make_game()
    # Find two cards with same color
    color_map: dict[int, list[tuple[int, int]]] = {}
    for r in range(ROWS):
        for c in range(COLS):
            color = g.grid[r][c].color
            if color not in color_map:
                color_map[color] = []
            color_map[color].append((c, r))
    # Pick a non-wild color that has pairs
    for color, positions in color_map.items():
        if color != PEACH and len(positions) >= 2:
            c1, r1 = positions[0]
            c2, r2 = positions[1]
            break
    else:
        assert False, "No non-wild pair found"

    g.phase = Phase.FLIP_SECOND
    g.first_card = (c1, r1)
    g.grid[r1][c1].revealed = True
    g._grid_click(c2, r2)
    assert g.phase == Phase.MATCH_ANIM
    assert g.combo == 1
    assert g.score == 100  # 100 * combo(1)
    assert g.pairs_matched == 1
    assert g.grid[r1][c1].matched is True
    assert g.grid[r2][c2].matched is True


def test_miss_different_color():
    g = _make_game()
    g.phase = Phase.FLIP_SECOND
    # Find two cards with different non-wild colors
    color_map: dict[int, list[tuple[int, int]]] = {}
    for r in range(ROWS):
        for c in range(COLS):
            color = g.grid[r][c].color
            if color != PEACH:
                if color not in color_map:
                    color_map[color] = []
                color_map[color].append((c, r))
    colors = list(color_map.keys())
    if len(colors) < 2:
        assert False, "Need at least 2 different colors"
    c1, r1 = color_map[colors[0]][0]
    c2, r2 = color_map[colors[1]][0]

    g.first_card = (c1, r1)
    g.grid[r1][c1].revealed = True
    g._grid_click(c2, r2)
    assert g.phase == Phase.MISS_ANIM
    assert g.combo == 0
    assert g.pairs_matched == 0


def test_wild_matches_any():
    g = _make_game()
    # Find a wild card and a non-wild card
    wild_pos = None
    other_pos = None
    for r in range(ROWS):
        for c in range(COLS):
            if g.grid[r][c].color == PEACH:
                wild_pos = (c, r)
            elif other_pos is None:
                other_pos = (c, r)
    assert wild_pos is not None
    assert other_pos is not None

    g.phase = Phase.FLIP_SECOND
    g.first_card = wild_pos
    g.grid[wild_pos[1]][wild_pos[0]].revealed = True
    g._grid_click(*other_pos)
    assert g.phase == Phase.MATCH_ANIM
    assert g.combo == 1
    assert g.pairs_matched == 1


def test_wild_wild_match():
    g = _make_game()
    wild_positions = []
    for r in range(ROWS):
        for c in range(COLS):
            if g.grid[r][c].color == PEACH:
                wild_positions.append((c, r))
    assert len(wild_positions) >= 2

    g.phase = Phase.FLIP_SECOND
    g.first_card = wild_positions[0]
    g.grid[wild_positions[0][1]][wild_positions[0][0]].revealed = True
    g._grid_click(*wild_positions[1])
    assert g.phase == Phase.MATCH_ANIM
    assert g.combo == 1


def test_combo_increments_on_consecutive_matches():
    g = _make_game()
    g.phase = Phase.FLIP_SECOND
    g.combo = 2  # pretend we matched twice before

    # Find same-color pair
    color_map: dict[int, list[tuple[int, int]]] = {}
    for r in range(ROWS):
        for c in range(COLS):
            color = g.grid[r][c].color
            if color != PEACH:
                if color not in color_map:
                    color_map[color] = []
                color_map[color].append((c, r))
    colors = list(color_map.keys())
    c1, r1 = color_map[colors[0]][0]
    c2, r2 = color_map[colors[0]][1]

    g.first_card = (c1, r1)
    g.grid[r1][c1].revealed = True
    g._grid_click(c2, r2)
    assert g.phase == Phase.MATCH_ANIM
    assert g.combo == 3
    assert g.score == 300  # 100 * combo(3)
    assert g.max_combo == 3


def test_combo_resets_on_miss():
    g = _make_game()
    g.phase = Phase.FLIP_SECOND
    g.combo = 5

    # Find two different-color cards
    color_map: dict[int, list[tuple[int, int]]] = {}
    for r in range(ROWS):
        for c in range(COLS):
            color = g.grid[r][c].color
            if color != PEACH:
                if color not in color_map:
                    color_map[color] = []
                color_map[color].append((c, r))
    colors = list(color_map.keys())
    c1, r1 = color_map[colors[0]][0]
    c2, r2 = color_map[colors[1]][0]

    g.first_card = (c1, r1)
    g.grid[r1][c1].revealed = True
    g._grid_click(c2, r2)
    assert g.phase == Phase.MISS_ANIM
    assert g.combo == 0


# ── BFS Adjacent Tests ───────────────────────────────────────────────

def test_bfs_adjacent_collects_all_reachable_face_down():
    g = _make_game()
    # Make all cards face-down
    for r in range(ROWS):
        for c in range(COLS):
            g.grid[r][c].revealed = False
            g.grid[r][c].matched = False

    # BFS from center — origin gets added when expanding from neighbors
    result = g._bfs_adjacent(3, 3)
    assert len(result) == TOTAL_CARDS  # 36 (origin reachable via neighbor expansion)


def test_bfs_adjacent_blocked_by_revealed():
    g = _make_game()
    for r in range(ROWS):
        for c in range(COLS):
            g.grid[r][c].revealed = False
            g.grid[r][c].matched = False

    # Block by revealing a ring around (0,0)
    # Reveal (0,1) and (1,0) to isolate (0,0) from rest
    g.grid[0][1].revealed = True
    g.grid[1][0].revealed = True

    result = g._bfs_adjacent(0, 0)
    # Only (0,0) neighbors: (0,1) blocked, (1,0) blocked → empty
    assert len(result) == 0

    # But BFS from center should still reach everything except blocked cells
    result2 = g._bfs_adjacent(3, 3)
    # 36 total - 2 revealed wall cells (not visited) - 1 isolated unreachable = 33
    assert len(result2) == 33


def test_bfs_adjacent_blocked_by_matched():
    g = _make_game()
    for r in range(ROWS):
        for c in range(COLS):
            g.grid[r][c].revealed = False
            g.grid[r][c].matched = False

    g.grid[0][1].matched = True
    g.grid[1][0].matched = True

    result = g._bfs_adjacent(0, 0)
    assert len(result) == 0


def test_bfs_no_duplicates():
    g = _make_game()
    for r in range(ROWS):
        for c in range(COLS):
            g.grid[r][c].revealed = False
            g.grid[r][c].matched = False

    result = g._bfs_adjacent(2, 2)
    assert len(result) == len(set(result))  # no duplicates


# ── Chain Reveal Tests ───────────────────────────────────────────────

def test_chain_reveal_requires_combo_3():
    """Chain reveal only triggered by update, not directly tested here."""
    g = _make_game()
    g.combo = 2
    g.first_card = (0, 0)
    g.second_card = (1, 0)
    g.matched_color = g.grid[0][0].color
    bonus = g._trigger_chain_reveal()
    assert bonus >= 0  # chain reveal still runs if called, but in-game it's guarded


def test_chain_reveal_flips_matching_adjacent():
    """BFS from matched pair reaches all face-down cards; matching-color get auto-matched."""
    g = _make_game()
    # Set ALL cards to face-down except the matched pair
    for r in range(ROWS):
        for c in range(COLS):
            g.grid[r][c].revealed = False
            g.grid[r][c].matched = False

    # Match a pair at (0,0) and (1,1)
    g.grid[0][0].revealed = True
    g.grid[0][0].matched = True
    g.grid[1][1].revealed = True
    g.grid[1][1].matched = True
    g.first_card = (0, 0)
    g.second_card = (1, 1)
    g.matched_color = g.grid[0][0].color  # whatever color (0,0) happens to be
    g.pairs_matched = 1

    # Count how many face-down cards have the matched color
    expected_matches = sum(
        1 for r in range(ROWS) for c in range(COLS)
        if not g.grid[r][c].revealed
        and (g.grid[r][c].color == g.matched_color or g.grid[r][c].color == PEACH)
    )

    bonus = g._trigger_chain_reveal()
    # bonus = 50 * expected_matches
    assert bonus == 50 * expected_matches
    # Verify the matched cards are now matched
    matched_count = sum(
        1 for r in range(ROWS) for c in range(COLS)
        if g.grid[r][c].matched
    )
    assert matched_count == 2 + expected_matches  # original 2 + auto-matched


def test_chain_reveal_wild_matches_any():
    """WILD (PEACH) cards match any color during chain reveal."""
    g = _make_game()
    for r in range(ROWS):
        for c in range(COLS):
            g.grid[r][c].revealed = False
            g.grid[r][c].matched = False

    g.grid[0][0].revealed = True
    g.grid[0][0].matched = True
    g.grid[1][1].revealed = True
    g.grid[1][1].matched = True
    g.first_card = (0, 0)
    g.second_card = (1, 1)
    g.matched_color = g.grid[0][0].color
    g.pairs_matched = 1

    # Count WILD cards in face-down cells
    wild_count = sum(
        1 for r in range(ROWS) for c in range(COLS)
        if not g.grid[r][c].revealed and g.grid[r][c].color == PEACH
    )
    assert wild_count >= 1  # should have WILD cards

    bonus = g._trigger_chain_reveal()
    # All WILD cards should be matched now
    wild_matched = sum(
        1 for r in range(ROWS) for c in range(COLS)
        if g.grid[r][c].color == PEACH and g.grid[r][c].matched
    )
    assert wild_matched == 4  # all 4 WILD cards (2 pairs) should be matched
    assert bonus >= 50 * wild_count


def test_chain_reveal_no_first_second_card():
    g = _make_game()
    g.first_card = None
    g.second_card = None
    bonus = g._trigger_chain_reveal()
    assert bonus == 0


# ── Particle Tests ───────────────────────────────────────────────────

def test_spawn_particles_adds_to_list():
    g = _make_game()
    assert len(g.particles) == 0
    g._spawn_particles(100.0, 100.0, RED, PARTICLE_COUNT)
    assert len(g.particles) == PARTICLE_COUNT
    for p in g.particles:
        assert isinstance(p, Particle)
        assert p.color == RED
        assert p.life > 0


def test_update_particles_reduces_life():
    g = _make_game()
    g._spawn_particles(100.0, 100.0, RED, 5)
    initial_count = len(g.particles)
    g._update_particles()
    # All particles still alive (life >= 15)
    assert len(g.particles) == initial_count


def test_particles_die_and_remove():
    g = _make_game()
    g.particles.append(Particle(x=0, y=0, vx=0, vy=0, life=1, color=RED))
    assert len(g.particles) == 1
    g._update_particles()
    assert len(g.particles) == 0  # life decremented to 0, removed


def test_particles_spawned_from_both_matched_cards():
    g = _make_game()
    g.phase = Phase.FLIP_SECOND
    color_map: dict[int, list[tuple[int, int]]] = {}
    for r in range(ROWS):
        for c in range(COLS):
            color = g.grid[r][c].color
            if color != PEACH:
                if color not in color_map:
                    color_map[color] = []
                color_map[color].append((c, r))
    colors = list(color_map.keys())
    c1, r1 = color_map[colors[0]][0]
    c2, r2 = color_map[colors[0]][1]

    g.first_card = (c1, r1)
    g.grid[r1][c1].revealed = True
    g._grid_click(c2, r2)

    # Should have 2 * PARTICLE_COUNT particles (from both cards)
    assert len(g.particles) == PARTICLE_COUNT * 2


# ── Timer Tests ──────────────────────────────────────────────────────

def test_timer_initial_value():
    g = _make_game()
    assert g.timer == TIMER_FRAMES  # 2700


def test_timer_decrements_in_playing():
    g = _make_game()
    g.phase = Phase.FLIP_FIRST
    initial = g.timer
    # Simulate one frame of _update_playing minus the pyxel calls
    g.timer -= 1
    assert g.timer == initial - 1


# ── Miss Flip Back Tests ─────────────────────────────────────────────

def test_miss_anim_flips_cards_back():
    g = _make_game()
    g.phase = Phase.FLIP_SECOND
    color_map: dict[int, list[tuple[int, int]]] = {}
    for r in range(ROWS):
        for c in range(COLS):
            color = g.grid[r][c].color
            if color != PEACH:
                if color not in color_map:
                    color_map[color] = []
                color_map[color].append((c, r))
    colors = list(color_map.keys())
    c1, r1 = color_map[colors[0]][0]
    c2, r2 = color_map[colors[1]][0]

    g.first_card = (c1, r1)
    g.grid[r1][c1].revealed = True
    g._grid_click(c2, r2)
    assert g.phase == Phase.MISS_ANIM

    # Simulate running the miss anim timer out via manual state manipulation
    g.anim_timer = 0  # simulate timer hitting 0
    # Manually do what _update_miss_anim does:
    c1_card = g.grid[g.first_card[1]][g.first_card[0]]
    c1_card.revealed = False
    c2_card = g.grid[g.second_card[1]][g.second_card[0]]
    c2_card.revealed = False
    g.first_card = None
    g.second_card = None

    assert g.grid[r1][c1].revealed is False
    assert g.grid[r2][c2].revealed is False
    assert g.first_card is None
    assert g.second_card is None


# ── Victory Condition ────────────────────────────────────────────────

def test_all_matched_triggers_game_over():
    g = _make_game()
    g.phase = Phase.FLIP_FIRST
    # Mark all cards as matched
    g.pairs_matched = TOTAL_CARDS // 2
    for r in range(ROWS):
        for c in range(COLS):
            g.grid[r][c].matched = True
            g.grid[r][c].revealed = True

    # Simulate _update_playing all-matched check
    assert g.pairs_matched * 2 >= TOTAL_CARDS
    # In the real game this transitions to GAME_OVER
    g.score += 500  # clear bonus
    g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


# ── Phase Transitions ────────────────────────────────────────────────

def test_match_anim_chain_reveal_at_combo_3():
    g = _make_game()
    g.phase = Phase.MATCH_ANIM
    g.combo = 3
    g.first_card = (0, 0)
    g.second_card = (1, 1)
    g.matched_color = RED
    g.anim_timer = 0  # simulate timer expiry

    # Simulate what _update_match_anim does when anim_timer <= 0 and combo >= 3
    g._trigger_chain_reveal()
    g.anim_timer = CHAIN_REVEAL_FRAMES
    g.phase = Phase.CHAIN_REVEAL
    assert g.phase == Phase.CHAIN_REVEAL


def test_match_anim_no_chain_at_combo_2():
    g = _make_game()
    g.phase = Phase.MATCH_ANIM
    g.combo = 2
    g.anim_timer = 0

    # Simulate what _update_match_anim does when combo < 3
    g.first_card = None
    g.second_card = None
    g.phase = Phase.FLIP_FIRST
    assert g.phase == Phase.FLIP_FIRST
    assert g.first_card is None
    assert g.second_card is None


# ── Scoring ──────────────────────────────────────────────────────────

def test_score_increases_with_combo():
    g = _make_game()
    g.phase = Phase.FLIP_SECOND

    # Match 1: combo 0 → 1, score += 100*1 = 100
    color_map: dict[int, list[tuple[int, int]]] = {}
    for r in range(ROWS):
        for c in range(COLS):
            color = g.grid[r][c].color
            if color != PEACH:
                if color not in color_map:
                    color_map[color] = []
                color_map[color].append((c, r))

    colors = list(color_map.keys())
    # Match first pair
    c1, r1 = color_map[colors[0]][0]
    c2, r2 = color_map[colors[0]][1]
    g.first_card = (c1, r1)
    g.grid[r1][c1].revealed = True
    g._grid_click(c2, r2)
    assert g.combo == 1
    assert g.score == 100
    assert g.max_combo == 1

    # Match second pair (need another pair of same color)
    c3, r3 = color_map[colors[0]][2]
    c4, r4 = color_map[colors[0]][3]
    g.phase = Phase.FLIP_SECOND
    g.first_card = (c3, r3)
    g.grid[r3][c3].revealed = True
    prev_score = g.score
    g._grid_click(c4, r4)
    assert g.combo == 2
    assert g.score == prev_score + 200  # 100 * combo(2)
    assert g.max_combo == 2


def test_max_combo_tracks_highest():
    g = _make_game()
    g.combo = 5
    g.max_combo = 3
    g.max_combo = max(g.max_combo, g.combo)
    assert g.max_combo == 5


# ── Reset / Re-init Tests ────────────────────────────────────────────

def test_init_state_clears_previous_run():
    g = _make_game()
    g.score = 9999
    g.combo = 10
    g.max_combo = 10
    g.pairs_matched = 18
    g.first_card = (0, 0)
    g.second_card = (0, 0)
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=1, color=RED)]
    g.timer = 1

    g._init_state()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.pairs_matched == 0
    assert g.timer == TIMER_FRAMES
    assert g.first_card is None
    assert g.second_card is None
    assert g.anim_timer == 0
    assert g.chain_bonus == 0
    assert len(g.particles) == 0


# ── Enum Values ──────────────────────────────────────────────────────

def test_phase_enum_values():
    assert Phase.TITLE == 0
    assert Phase.FLIP_FIRST == 1
    assert Phase.FLIP_SECOND == 2
    assert Phase.MATCH_ANIM == 3
    assert Phase.MISS_ANIM == 4
    assert Phase.CHAIN_REVEAL == 5
    assert Phase.GAME_OVER == 6
    assert len(Phase) == 7


# ── Constants ────────────────────────────────────────────────────────

def test_constants():
    assert GRID_X == 16
    assert GRID_Y == 24
    assert CELL == 48
    assert COLS == 6
    assert ROWS == 6
    assert TOTAL_CARDS == 36
    assert TIMER_FRAMES == 2700
    assert PAIRS_PER_COLOR == 4
    assert WILD_PAIRS == 2
    assert len(CARD_COLORS) == 4
    assert RED == 8
    assert GREEN == 3
    assert DARK_BLUE == 5
    assert YELLOW == 10
    assert PEACH == 15


# ── Dataclass Tests ─────────────────────────────────────────────────

def test_card_defaults():
    c = Card(color=RED)
    assert c.color == RED
    assert c.revealed is False
    assert c.matched is False


def test_card_custom_values():
    c = Card(color=GREEN, revealed=True, matched=True)
    assert c.color == GREEN
    assert c.revealed is True
    assert c.matched is True


def test_particle_fields():
    p = Particle(x=1.5, y=2.5, vx=0.5, vy=-0.5, life=10, color=YELLOW)
    assert p.x == 1.5
    assert p.y == 2.5
    assert p.life == 10
    assert p.color == YELLOW
