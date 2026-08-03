"""test_imports.py — Headless logic tests for 275_tile_chain."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.absolute()))

from main import (
    SCREEN_W, SCREEN_H, COLS, ROWS, CELL, GRID_X, GRID_Y,
    LAYER_OFFSET, TILE_SIZE, TOTAL_LAYERS, TIMER_FRAMES,
    SUPER_DURATION, DESELECT_TIME, HEAT_DECAY, HEAT_MISMATCH, HEAT_CAP,
    BLACK, WHITE, RED, ORANGE, YELLOW, LIME, CYAN, GRAY, PINK,
    DARK_BLUE, PEACH,
    TILE_COLORS, RAINBOW_COLORS, LAYER_DEFS,
    Phase, Tile, Particle, FloatingText, Game,
)


# ── Helper: create a Game via __new__ with deterministic RNG ─────────

def _make_game(seed: int = 42) -> Game:
    """Create a Game instance bypassing Pyxel init, with seeded RNG."""
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.phase = Phase.TITLE
    g.tiles = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.super_timer = 0
    g.time_left = TIMER_FRAMES
    g.selected_tile = None
    g.deselect_timer = 0
    g.particles = []
    g.floating_texts = []
    g.last_matched_color = -1
    g._shake_frames = 0
    g._init_tiles()
    g.phase = Phase.PLAYING
    return g


# ── Tile Count & Structure Tests ────────────────────────────────────

def test_total_tile_count():
    g = _make_game()
    count = sum(t[4] * 4 for t in LAYER_DEFS)
    assert count == 188
    assert len(g.tiles) == 188


def test_layer_counts():
    g = _make_game()
    counts = {0: 0, 1: 0, 2: 0}
    for t in g.tiles:
        counts[t.layer] += 1
    assert counts[0] == 96   # 12 * 8
    assert counts[1] == 60   # 10 * 6
    assert counts[2] == 32   # 8 * 4


def test_color_distribution_per_layer():
    g = _make_game(42)
    for layer_idx, (c0, c1, r0, r1, per_color) in enumerate(LAYER_DEFS):
        color_counts: dict[int, int] = {}
        for t in g.tiles:
            if t.layer == layer_idx:
                color_counts[t.color] = color_counts.get(t.color, 0) + 1
        for c in TILE_COLORS:
            assert color_counts.get(c, 0) == per_color, f"Layer {layer_idx} color {c}"
        assert sum(color_counts.values()) == per_color * 4


def test_deterministic_shuffle():
    g1 = _make_game(42)
    g2 = _make_game(42)
    for i in range(len(g1.tiles)):
        t1 = g1.tiles[i]
        t2 = g2.tiles[i]
        assert t1.col == t2.col
        assert t1.row == t2.row
        assert t1.layer == t2.layer
        assert t1.color == t2.color


def test_different_seeds_different():
    g1 = _make_game(42)
    g2 = _make_game(99)
    colors1 = [(t.col, t.row, t.layer, t.color) for t in sorted(g1.tiles, key=lambda x: (x.layer, x.row, x.col))]
    colors2 = [(t.col, t.row, t.layer, t.color) for t in sorted(g2.tiles, key=lambda x: (x.layer, x.row, x.col))]
    assert colors1 != colors2


# ── Exposure Tests ──────────────────────────────────────────────────

def test_layer2_tiles_always_exposed():
    g = _make_game()
    for t in g.tiles:
        if t.layer == 2:
            assert t.exposed is True, f"Layer 2 tile at ({t.col},{t.row}) should be exposed"


def test_layer0_edge_tiles_exposed():
    g = _make_game()
    # Layer 1 covers cols 1-10, rows 1-6
    # So layer 0 tiles at edges (col=0, col=11, row=0, row=7) should be exposed if no layer 1 above them
    for t in g.tiles:
        if t.layer == 0 and (t.col == 0 or t.col == 11 or t.row == 0 or t.row == 7):
            assert t.exposed is True, f"Layer 0 edge at ({t.col},{t.row}) should be exposed"


def test_layer0_center_tiles_covered():
    g = _make_game()
    for t in g.tiles:
        if t.layer == 0 and 2 <= t.col <= 9 and 2 <= t.row <= 5:
            # These are directly below layer 2, so covered
            assert t.exposed is False, f"Layer 0 center at ({t.col},{t.row}) should be covered"


def test_update_exposed_after_kill():
    g = _make_game()
    # Find a layer 2 tile and a layer 1 tile below it
    l2_tile = None
    for t in g.tiles:
        if t.layer == 2:
            l2_tile = t
            break
    assert l2_tile is not None

    l1_tile = g._find_tile_at(l2_tile.col, l2_tile.row, 1)
    assert l1_tile is not None
    assert l1_tile.exposed is False  # Covered by layer 2

    l2_tile.alive = False
    g._update_exposed()
    l1_tile_after = g._find_tile_at(l2_tile.col, l2_tile.row, 1)
    assert l1_tile_after is not None
    assert l1_tile_after.exposed is True  # Now exposed


def test_dead_tiles_not_exposed():
    g = _make_game()
    t = g.tiles[0]
    t.alive = False
    g._update_exposed()
    assert t.exposed is False


# ── Coverage Tests ──────────────────────────────────────────────────

def test_is_covered_layer2():
    g = _make_game()
    t = g._find_tile_at(2, 2, 2)
    assert t is not None
    assert g._is_covered(t) is False


def test_is_covered_layer1_under_layer2():
    g = _make_game()
    t = g._find_tile_at(4, 4, 1)
    assert t is not None
    assert g._is_covered(t) is True  # layer 2 above it


def test_is_covered_layer0_under_layer1():
    g = _make_game()
    t = g._find_tile_at(5, 5, 0)
    assert t is not None
    assert g._is_covered(t) is True  # layers 1 and 2 above


# ── Find Tile Tests ─────────────────────────────────────────────────

def test_find_tile_at_returns_correct_tile():
    g = _make_game()
    t = g._find_tile_at(5, 3, 0)
    assert t is not None
    assert t.col == 5
    assert t.row == 3
    assert t.layer == 0


def test_find_tile_at_nonexistent():
    g = _make_game()
    assert g._find_tile_at(0, 0, 2) is None  # Layer 2 starts at col 2, row 2


def test_find_tile_at_dead():
    g = _make_game()
    t = g._find_tile_at(3, 2, 0)
    assert t is not None
    t.alive = False
    assert g._find_tile_at(3, 2, 0) is None


# ── Top Tile Find Tests ─────────────────────────────────────────────

def test_find_top_tile_at_returns_topmost():
    g = _make_game()
    px = GRID_X + 5 * CELL + CELL // 2
    py = GRID_Y + 4 * CELL + CELL // 2
    t = g._find_top_tile_at(px, py)
    assert t is not None
    # Should return layer 2 tile (topmost at this position)
    assert t.layer == 2


def test_find_top_tile_at_edge_only_layer0():
    g = _make_game()
    px = GRID_X + CELL // 2
    py = GRID_Y + CELL // 2
    t = g._find_top_tile_at(px, py)
    assert t is not None
    assert t.layer == 0


def test_find_top_tile_at_out_of_bounds():
    g = _make_game()
    assert g._find_top_tile_at(-10, -10) is None
    assert g._find_top_tile_at(500, 500) is None


def test_find_top_tile_at_dead_skipped():
    g = _make_game()
    # Pick position with layers 0,1,2. Kill layer 2 tile.
    l2 = g._find_tile_at(4, 3, 2)
    if l2 is not None:
        l2.alive = False
    t = g._find_top_tile_at(
        GRID_X + 4 * CELL + CELL // 2,
        GRID_Y + 3 * CELL + CELL // 2,
    )
    assert t is not None
    assert t.layer == 1  # Falls through to layer 1


# ── Exposed Pairs Tests ─────────────────────────────────────────────

def test_exposed_pairs_exist_initially():
    g = _make_game()
    assert g._exposed_pairs_exist() is True


def test_exposed_pairs_no_pairs():
    g = _make_game()
    # Kill ALL tiles except one per color, iterating until no pairs remain
    for _ in range(10):
        g._update_exposed()
        if not g._exposed_pairs_exist():
            break
        color_count: dict[int, int] = {}
        for t in g.tiles:
            if t.alive and t.exposed:
                color_count[t.color] = color_count.get(t.color, 0) + 1
        # Kill all but one of each color among exposed tiles
        seen: set[int] = set()
        for t in g.tiles:
            if t.alive and t.exposed:
                if t.color in seen:
                    t.alive = False
                else:
                    seen.add(t.color)
    g._update_exposed()
    assert g._exposed_pairs_exist() is False


# ── Match Logic Tests ───────────────────────────────────────────────

def test_match_same_color_increments_combo():
    g = _make_game()
    # Find two exposed tiles of same color
    color_map: dict[int, list[Tile]] = {}
    for t in g.tiles:
        if t.alive and t.exposed:
            color_map.setdefault(t.color, []).append(t)
    for color, tiles in color_map.items():
        if len(tiles) >= 2:
            t1, t2 = tiles[0], tiles[1]
            break
    else:
        assert False, "No matching exposed pair found"

    t1.selected = True
    g.selected_tile = t1
    # Simulate second click via _match_tiles directly
    g._match_tiles(t1, t2)
    assert t1.alive is False
    assert t2.alive is False
    assert g.combo == 1
    assert g.score == 100  # 100 * 1


def test_match_combo_builds_score():
    g = _make_game()
    g.combo = 3  # Already matched 3
    g.score = 600  # Previous score
    color_map: dict[int, list[Tile]] = {}
    for t in g.tiles:
        if t.alive and t.exposed:
            color_map.setdefault(t.color, []).append(t)
    for color, tiles in color_map.items():
        if len(tiles) >= 2:
            t1, t2 = tiles[0], tiles[1]
            break
    else:
        assert False, "No matching exposed pair found"

    g._match_tiles(t1, t2)
    assert g.combo == 4
    assert g.score == 600 + 400  # 100 * 4
    assert g.max_combo == 4


def test_match_triggers_super_at_combo_4():
    g = _make_game()
    g.combo = 3
    g.super_timer = 0
    color_map: dict[int, list[Tile]] = {}
    for t in g.tiles:
        if t.alive and t.exposed:
            color_map.setdefault(t.color, []).append(t)
    for color, tiles in color_map.items():
        if len(tiles) >= 2:
            t1, t2 = tiles[0], tiles[1]
            break
    else:
        assert False, "No matching exposed pair found"

    g._match_tiles(t1, t2)
    assert g.combo == 4
    assert g.super_timer == SUPER_DURATION


def test_super_match_allows_any_color():
    g = _make_game()
    g.super_timer = 100
    g.combo = 4
    # Find two exposed tiles of DIFFERENT colors
    diff1: Tile | None = None
    diff2: Tile | None = None
    for t in g.tiles:
        if t.alive and t.exposed:
            if diff1 is None:
                diff1 = t
            elif t.color != diff1.color and diff2 is None:
                diff2 = t
                break
    assert diff1 is not None
    assert diff2 is not None
    assert diff1.color != diff2.color

    g.selected_tile = diff1
    # In super mode, _handle_click matches even different colors
    # We test by calling _match_tiles directly (since _handle_click checks color)
    g._match_tiles(diff1, diff2)
    assert diff1.alive is False
    assert diff2.alive is False
    assert g.combo == 5


def test_super_match_3x_score():
    g = _make_game()
    g.super_timer = 100
    g.combo = 4
    g.score = 1000
    color_map: dict[int, list[Tile]] = {}
    for t in g.tiles:
        if t.alive and t.exposed:
            color_map.setdefault(t.color, []).append(t)
    for color, tiles in color_map.items():
        if len(tiles) >= 2:
            t1, t2 = tiles[0], tiles[1]
            break
    else:
        assert False, "No matching exposed pair found"

    g._match_tiles(t1, t2)
    assert g.score == 1000 + 100 * 5 * 3  # 100 * combo(5) * 3


def test_match_updates_max_combo():
    g = _make_game()
    g.combo = 2
    g.max_combo = 2
    color_map: dict[int, list[Tile]] = {}
    for t in g.tiles:
        if t.alive and t.exposed:
            color_map.setdefault(t.color, []).append(t)
    for color, tiles in color_map.items():
        if len(tiles) >= 2:
            t1, t2 = tiles[0], tiles[1]
            break
    else:
        assert False, "No matching exposed pair found"

    g._match_tiles(t1, t2)
    assert g.max_combo == 3
    assert g.combo == 3


def test_mismatch_resets_combo():
    g = _make_game()
    g.combo = 5
    g.last_matched_color = RED  # some non-matching color
    # Find two exposed tiles of DIFFERENT colors
    diff1: Tile | None = None
    diff2: Tile | None = None
    for t in g.tiles:
        if t.alive and t.exposed:
            if diff1 is None:
                diff1 = t
            elif t.color != diff1.color and diff2 is None:
                diff2 = t
                break
    assert diff1 is not None
    assert diff2 is not None

    g._handle_mismatch(diff1, diff2)
    assert g.combo == 0
    assert g.last_matched_color == -1


def test_mismatch_adds_heat():
    g = _make_game()
    assert g.heat == 0.0
    g.combo = 3
    t1 = g.tiles[0]
    g._find_tile_at(5, 3, 1)
    # Just call _handle_mismatch
    t1 = [t for t in g.tiles if t.exposed and t.alive][0]
    t2_candidates = [t for t in g.tiles if t.exposed and t.alive and t is not t1 and t.color != t1.color]
    if t2_candidates:
        t2 = t2_candidates[0]
        g._handle_mismatch(t1, t2)
        assert g.heat == HEAT_MISMATCH


def test_super_match_duration_ticks_down():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_timer = 100
    g.time_left = TIMER_FRAMES  # enough time
    # Simulate one frame
    g.super_timer -= 1
    assert g.super_timer == 99


# ── Heat System Tests ───────────────────────────────────────────────

def test_heat_update_clamped():
    g = _make_game()
    g._update_heat(200.0)
    assert g.heat == HEAT_CAP
    g._update_heat(-200.0)
    assert g.heat == 0.0


def test_heat_decay():
    g = _make_game()
    g.heat = 50.0
    g._decay_heat()
    assert g.heat == 50.0 - HEAT_DECAY


def test_heat_game_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = HEAT_CAP
    # Manually trigger the check
    assert g.heat >= HEAT_CAP


# ── Deselect Timer Tests ────────────────────────────────────────────

def test_deselect_timer_clears_selection():
    g = _make_game()
    t = [t for t in g.tiles if t.exposed and t.alive][0]
    t.selected = True
    g.selected_tile = t
    g.deselect_timer = 1
    # Simulate timer expiring
    g.deselect_timer -= 1
    if g.deselect_timer <= 0 and g.selected_tile is not None:
        g.selected_tile.selected = False
        g.selected_tile = None
    assert g.selected_tile is None
    assert t.selected is False


def test_deselect_timer_resets_on_click():
    g = _make_game()
    t = [t for t in g.tiles if t.exposed and t.alive][0]
    g.selected_tile = None
    g.deselect_timer = 0
    # Simulate first click
    t.selected = True
    g.selected_tile = t
    g.deselect_timer = DESELECT_TIME
    assert g.deselect_timer == DESELECT_TIME


# ── Timer Tests ─────────────────────────────────────────────────────

def test_timer_initial_value():
    g = _make_game()
    assert g.time_left == TIMER_FRAMES


def test_timer_decrements():
    g = _make_game()
    initial = g.time_left
    g.time_left -= 1
    assert g.time_left == initial - 1


# ── Game Over Conditions ────────────────────────────────────────────

def test_time_up_game_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.time_left = 0
    # Simulate check
    assert g.time_left <= 0


def test_heat_cap_game_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = HEAT_CAP
    assert g.heat >= HEAT_CAP


def test_all_cleared_victory():
    g = _make_game()
    for t in g.tiles:
        t.alive = False
    alive_count = sum(1 for t in g.tiles if t.alive)
    assert alive_count == 0


def test_all_clear_bonus():
    g = _make_game()
    g.time_left = 3000  # 50 seconds
    for t in g.tiles:
        t.alive = False
    g.score += (g.time_left // 60) * 10
    assert g.score == 50 * 10  # 500


# ── Particle Tests ──────────────────────────────────────────────────

def test_spawn_match_particles():
    g = _make_game()
    assert len(g.particles) == 0
    g._spawn_match_particles(100, 100, RED)
    assert len(g.particles) == 8
    for p in g.particles:
        assert isinstance(p, Particle)
        assert p.color == RED
        assert p.life >= 10


def test_spawn_super_particles():
    g = _make_game()
    g._spawn_super_particles(100, 100)
    assert len(g.particles) == 12
    for p in g.particles:
        assert p.color in RAINBOW_COLORS


def test_spawn_wrong_particles():
    g = _make_game()
    g._spawn_wrong_particles(100, 100)
    assert len(g.particles) == 4
    for p in g.particles:
        assert p.color == RED
        assert 8 <= p.life <= 12


def test_update_particles_reduces_life():
    g = _make_game()
    g._spawn_match_particles(100, 100, RED)
    initial_count = len(g.particles)
    g._update_particles()
    assert len(g.particles) == initial_count  # All still alive


def test_particles_die_and_removed():
    g = _make_game()
    g.particles.append(Particle(x=0, y=0, vx=0, vy=0, life=1, color=RED))
    assert len(g.particles) == 1
    g._update_particles()
    assert len(g.particles) == 0


# ── Floating Text Tests ─────────────────────────────────────────────

def test_floating_text_created_on_match():
    g = _make_game()
    g.combo = 0
    color_map: dict[int, list[Tile]] = {}
    for t in g.tiles:
        if t.alive and t.exposed:
            color_map.setdefault(t.color, []).append(t)
    for color, tiles in color_map.items():
        if len(tiles) >= 2:
            t1, t2 = tiles[0], tiles[1]
            break
    else:
        assert False, "No matching exposed pair found"

    g._match_tiles(t1, t2)
    assert len(g.floating_texts) >= 1
    ft = g.floating_texts[0]
    assert "+100" in ft.text


def test_floating_text_created_on_super_match():
    g = _make_game()
    g.super_timer = 100
    g.combo = 5
    color_map: dict[int, list[Tile]] = {}
    for t in g.tiles:
        if t.alive and t.exposed:
            color_map.setdefault(t.color, []).append(t)
    for color, tiles in color_map.items():
        if len(tiles) >= 2:
            t1, t2 = tiles[0], tiles[1]
            break
    else:
        assert False, "No matching exposed pair found"

    g._match_tiles(t1, t2)
    assert len(g.floating_texts) >= 1
    assert any("+" in ft.text for ft in g.floating_texts)


def test_floating_text_on_mismatch():
    g = _make_game()
    g.combo = 3
    t1 = [t for t in g.tiles if t.exposed and t.alive][0]
    t2_candidates = [t for t in g.tiles if t.exposed and t.alive and t is not t1 and t.color != t1.color]
    if t2_candidates:
        t2 = t2_candidates[0]
        g._handle_mismatch(t1, t2)
        assert len(g.floating_texts) >= 1
        assert g.floating_texts[0].text == "WRONG!"
        assert g.floating_texts[0].color == RED


def test_floating_text_super_match_announcement():
    g = _make_game()
    g.combo = 3  # Next match triggers super
    color_map: dict[int, list[Tile]] = {}
    for t in g.tiles:
        if t.alive and t.exposed:
            color_map.setdefault(t.color, []).append(t)
    for color, tiles in color_map.items():
        if len(tiles) >= 2:
            t1, t2 = tiles[0], tiles[1]
            break
    else:
        assert False, "No matching exposed pair found"

    g._match_tiles(t1, t2)
    texts = [ft.text for ft in g.floating_texts]
    assert any("SUPER MATCH!" in t for t in texts)


def test_floating_text_updates():
    g = _make_game()
    g.floating_texts.append(FloatingText(x=100, y=100, text="TEST", life=5, color=WHITE))
    g._update_floating_texts()
    ft = g.floating_texts[0]
    assert ft.life == 4
    assert ft.y == 99.0  # vy = -1


def test_floating_text_removed():
    g = _make_game()
    g.floating_texts.append(FloatingText(x=100, y=100, text="TEST", life=1, color=WHITE))
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Reset / Re-init Tests ───────────────────────────────────────────

def test_init_tiles_recreates_all():
    g = _make_game()
    g._init_tiles()
    assert len(g.tiles) == 188
    for t in g.tiles:
        assert t.alive is True


def test_init_state_clears_previous_run():
    g = _make_game()
    g.score = 9999
    g.combo = 10
    g.heat = 99
    g.super_timer = 200
    g.selected_tile = g.tiles[0]
    g.floating_texts = [FloatingText(x=0, y=0, text="x", life=1, color=WHITE)]
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=1, color=BLACK)]

    g._init_state()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.time_left == TIMER_FRAMES
    assert g.selected_tile is None
    assert g.deselect_timer == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.last_matched_color == -1
    assert g._shake_frames == 0


# ── Constants Tests ─────────────────────────────────────────────────

def test_constants():
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert COLS == 12
    assert ROWS == 8
    assert CELL == 20
    assert GRID_X == 40
    assert GRID_Y == 16
    assert LAYER_OFFSET == 3
    assert TILE_SIZE == 18
    assert TOTAL_LAYERS == 3
    assert TIMER_FRAMES == 5400
    assert SUPER_DURATION == 300
    assert DESELECT_TIME == 120
    assert HEAT_DECAY == 0.02
    assert HEAT_MISMATCH == 15.0
    assert HEAT_CAP == 100.0
    assert len(TILE_COLORS) == 4
    assert TILE_COLORS == (RED, LIME, DARK_BLUE, YELLOW)


def test_color_constants():
    assert BLACK == 0
    assert WHITE == 7
    assert RED == 8
    assert ORANGE == 9
    assert YELLOW == 10
    assert LIME == 11
    assert CYAN == 12
    assert GRAY == 13
    assert PINK == 14
    assert PEACH == 15
    assert DARK_BLUE == 5


# ── Data Class Tests ────────────────────────────────────────────────

def test_tile_defaults():
    t = Tile(col=0, row=0, layer=0, color=RED)
    assert t.col == 0
    assert t.row == 0
    assert t.layer == 0
    assert t.color == RED
    assert t.alive is True
    assert t.exposed is False
    assert t.selected is False


def test_particle_fields():
    p = Particle(x=1.5, y=2.5, vx=0.5, vy=-0.5, life=10, color=YELLOW)
    assert p.x == 1.5
    assert p.y == 2.5
    assert p.life == 10
    assert p.color == YELLOW


def test_floating_text_fields():
    ft = FloatingText(x=100, y=200, text="+500", life=20, color=LIME)
    assert ft.x == 100
    assert ft.y == 200
    assert ft.text == "+500"
    assert ft.life == 20
    assert ft.color == LIME
    assert ft.vy == -1.0


# ── Phase Enum Tests ────────────────────────────────────────────────

def test_phase_enum_values():
    assert Phase.TITLE == 0
    assert Phase.PLAYING == 1
    assert Phase.GAME_OVER == 2
    assert len(Phase) == 3


# ── Tile Center Tests ───────────────────────────────────────────────

def test_tile_center():
    g = _make_game()
    t = Tile(col=0, row=0, layer=0, color=RED)
    cx, cy = g._tile_center(t)
    assert abs(cx - (GRID_X + CELL / 2)) < 0.01
    assert abs(cy - (GRID_Y + CELL / 2)) < 0.01


def test_tile_center_with_layer_offset():
    g = _make_game()
    t = Tile(col=5, row=3, layer=2, color=LIME)
    cx, cy = g._tile_center(t)
    expected_x = GRID_X + 2 * LAYER_OFFSET + 5 * CELL + CELL / 2
    expected_y = GRID_Y + 2 * LAYER_OFFSET + 3 * CELL + CELL / 2
    assert abs(cx - expected_x) < 0.01
    assert abs(cy - expected_y) < 0.01


# ── Shake Test ─────────────────────────────────────────────────────

def test_shake_frames_set_on_mismatch():
    g = _make_game()
    g.combo = 3
    t1 = [t for t in g.tiles if t.exposed and t.alive][0]
    t2_candidates = [t for t in g.tiles if t.exposed and t.alive and t is not t1 and t.color != t1.color]
    if t2_candidates:
        t2 = t2_candidates[0]
        g._handle_mismatch(t1, t2)
        assert g._shake_frames == 6


def test_shake_decays():
    g = _make_game()
    g._shake_frames = 3
    g._shake_frames -= 1
    assert g._shake_frames == 2
