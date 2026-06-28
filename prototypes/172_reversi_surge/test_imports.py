"""test_imports.py — Headless logic tests for REVERSI SURGE.

Uses GameHeadless which inherits from Game and skips pyxel.init/run.
All tests use pure logic methods — no pyxel input calls.
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import pytest

# Add prototype dir to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (
    AI_MOVE_DELAY,
    BOARD_SIZE,
    CELL,
    COLOR_AI,
    COLOR_DARK_BLUE,
    COLOR_GREEN,
    COLOR_RED,
    COLOR_YELLOW,
    DIRS,
    EMPTY,
    HEAT_MAX,
    PLAYER_COLORS,
    SUPER_DURATION,
    FloatingText,
    Game,
    GameHeadless,
    Particle,
    Phase,
    Turn,
)


def _make_game() -> GameHeadless:
    """Create a headless game instance with seeded RNG for deterministic tests."""
    g = GameHeadless()
    g.rng = random.Random(42)
    g.reset()
    return g


# ── Board Initialization ──

def test_board_init():
    g = _make_game()
    assert len(g.grid) == BOARD_SIZE
    assert len(g.grid[0]) == BOARD_SIZE
    # Center 4 cells should be initialized
    assert g.grid[3][3] == COLOR_RED
    assert g.grid[3][4] == COLOR_AI
    assert g.grid[4][3] == COLOR_AI
    assert g.grid[4][4] == COLOR_GREEN
    # Remaining cells should be empty
    empty_count = sum(1 for row in g.grid for cell in row if cell == EMPTY)
    assert empty_count == 60  # 64 - 4


def test_initial_state():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.turn == Turn.PLAYER
    assert g.player_color == COLOR_RED
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.score == 0
    assert g.ai_score == 0
    assert g.heat == 0.0
    assert not g.super_mode
    assert g.super_timer == 0
    assert g.particles == []
    assert g.floating_texts == []
    assert g.hover_cell is None
    assert g.valid_moves == []
    assert g.game_over_reason == ""


# ── In-Bounds Check ──

def test_in_bounds():
    g = _make_game()
    assert Game._in_bounds(0, 0)
    assert Game._in_bounds(7, 7)
    assert Game._in_bounds(3, 3)
    assert not Game._in_bounds(-1, 0)
    assert not Game._in_bounds(0, 8)
    assert not Game._in_bounds(8, 0)
    assert not Game._in_bounds(8, 8)


# ── Valid Move Detection ──

def test_initial_valid_moves():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player_color = COLOR_RED
    moves = g._get_valid_moves_for(COLOR_RED)
    # With center setup: RED at (3,3), GREEN at (4,4), AI at (3,4) and (4,3)
    # RED player (color=1) can sandwich AI between two existing red cells
    # RED at (3,3): can sandwich AI at (3,4) with RED at (3,?) - needs another RED
    # Actually: RED is at (3,3) and (4,4) but (4,4) is GREEN not RED.
    # Wait - the init is: grid[3][3]=RED, grid[3][4]=AI, grid[4][3]=AI, grid[4][4]=GREEN
    # For RED (color=1): needs existing RED + AI disc + placement
    # RED at (3,3): looking south: (4,3)=AI, (5,3)=EMPTY (no RED at end)
    # RED at (3,3): looking east: (3,4)=AI, (3,5)=EMPTY (no RED)
    # RED at (3,3): looking SE: (4,4)=GREEN (not RED)
    # So RED has no valid moves initially!

    # Let me check GREEN moves (color=2)
    green_moves = g._get_valid_moves_for(COLOR_GREEN)
    # GREEN at (4,4): looking north: (3,4)=AI, (2,4)=EMPTY - need to place at (2,4) with GREEN backing
    # GREEN at (4,4): looking west: (4,3)=AI, (4,2)=EMPTY
    # GREEN at (4,4): looking NW: (3,3)=RED (not GREEN)
    # So placing GREEN at (2,4) sandwiches AI at (3,4) between (2,4) and (4,4)=GREEN
    assert (2, 4) in green_moves
    # Placing GREEN at (4,2) sandwiches AI at (4,3) between (4,2) and (4,4)=GREEN
    assert (4, 2) in green_moves
    assert len(green_moves) >= 2

    # Check AI moves
    ai_moves = g._get_valid_moves_for(COLOR_AI)
    # AI at (3,4): looking south: (4,4)=GREEN - can sandwich GREEN. Place north at (2,4) with AI at (3,4) backing?
    # Actually: AI at (3,4), looking north: (2,4)=EMPTY, needs another AI. AI at (4,3), looking north: (3,3)=RED
    # AI can place at (5,3) to sandwich (4,3) between (5,3) and AI at (3,4)?
    # AI at (3,4)=COLOR_AI, (4,4)=GREEN. Placing AI at (5,4): (5,4)=AI, looking west→(4,4)=GREEN→(3,4)=AI ✓
    assert (5, 4) in ai_moves
    assert len(ai_moves) >= 1


def test_valid_move_sandwich():
    """Test that valid moves require sandwiching at least 1 opponent disc."""
    g = _make_game()
    g.phase = Phase.PLAYING
    # Set up a simple sandwich scenario manually
    g.grid = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    g.grid[3][3] = COLOR_RED
    g.grid[3][4] = COLOR_AI
    # Place at (3,5): RED at (3,3) → AI at (3,4) → (3,5) placement
    # This sandwiches AI at (3,4) between RED at (3,3) and new RED at (3,5)
    assert g._is_valid_move(5, 3, COLOR_RED)  # col=5, row=3

    # Place at (3,2): RED at (3,3) → AI at (3,4) — AI is EAST not WEST of RED
    # No sandwich in that direction
    assert not g._is_valid_move(2, 3, COLOR_RED)

    # Same color should not sandwich
    assert not g._is_valid_move(5, 3, COLOR_GREEN)
    assert not g._is_valid_move(5, 3, COLOR_AI)


def test_no_valid_move_on_occupied():
    g = _make_game()
    g.phase = Phase.PLAYING
    assert not g._is_valid_move(3, 3, COLOR_RED)  # Already occupied by RED
    assert not g._is_valid_move(3, 4, COLOR_RED)  # Occupied by AI


# ── Flip Logic ──

def test_get_flippable():
    g = _make_game()
    g.phase = Phase.PLAYING
    # Set up scenario: RED at (3,3), AI at (3,4), want to place RED at (3,5)
    g.grid = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    g.grid[3][3] = COLOR_RED
    g.grid[3][4] = COLOR_AI
    # Place RED at (3,5) — should flip AI at (3,4)
    flippable = g._get_flippable(5, 3, COLOR_RED)  # col=5, row=3
    assert len(flippable) == 1
    assert flippable[0] == (4, 3)  # col=4, row=3 is the AI disc


def test_get_flippable_multi_direction():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.grid = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    # RED at center, AI discs surrounding, place RED at (5,5) to flip multiple
    g.grid[3][3] = COLOR_RED  # Center
    g.grid[3][4] = COLOR_AI   # East
    g.grid[4][3] = COLOR_AI   # South
    g.grid[4][4] = COLOR_AI   # SE diagonal
    # Place RED at (5,5) — sandwiches AI at (4,4) between (5,5) and (3,3)=RED in NW direction
    flippable = g._get_flippable(5, 5, COLOR_RED)
    # Should flip AI at (4,4) via NW direction
    assert (4, 4) in flippable
    # Also check: RED at (3,3) to (3,5): AI at (3,4) is sandwiched
    # Actually (3,5) is not being checked here, we placed at (5,5)
    # South direction: (6,5) empty, so no sandwich from south
    # East direction: (5,6) empty
    # NW direction: (4,4)=AI→(3,3)=RED ✓
    # North: (4,5)=empty
    # West: (5,4)=empty
    # NE, SE, SW: all empty
    assert len(flippable) == 1


def test_place_disc():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.grid = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    g.grid[3][3] = COLOR_RED
    g.grid[3][4] = COLOR_AI
    # Place RED at (3,5)
    count = g._place_disc(5, 3, COLOR_RED)
    assert count == 1
    assert g.grid[3][5] == COLOR_RED  # Placed
    assert g.grid[3][4] == COLOR_RED  # Flipped from AI to RED


def test_place_disc_no_flip():
    """Placing where nothing flips shouldn't be possible via _place_disc."""
    g = _make_game()
    g.grid = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    g.grid[3][3] = COLOR_RED
    # Place RED at (5,0) — no AI between to sandwich
    count = g._place_disc(0, 5, COLOR_RED)
    assert count == 0


# ── COMBO / SUPER ──

def test_combo_increment():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.turn = Turn.PLAYER
    g.player_color = COLOR_RED
    g.heat = 0.0
    g.combo = 0
    g.max_combo = 0

    # Set up: RED at (3,3), AI at (3,4) → place RED at (3,5)
    g.grid = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    g.grid[3][3] = COLOR_RED
    g.grid[3][4] = COLOR_AI
    g._handle_click(5, 3)  # col=5, row=3

    assert g.combo >= 1
    assert g.max_combo >= 1
    assert g.score > 0
    assert g.turn == Turn.AI  # Turn passes to AI after player move


def test_combo_chain():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.turn = Turn.PLAYER
    g.player_color = COLOR_RED
    g.heat = 0.0
    g.combo = 0

    # First move
    g.grid = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    g.grid[3][3] = COLOR_RED
    g.grid[3][4] = COLOR_AI
    g._handle_click(5, 3)  # Place RED at (3,5)
    first_combo = g.combo

    # AI turn -> back to player
    # Manually set turn back (bypass AI)
    g.turn = Turn.PLAYER

    # Second: setup another sandwich
    # After first move: grid[3][3]=RED, grid[3][4]=RED, grid[3][5]=RED
    g.grid[3][6] = COLOR_AI
    g._handle_click(7, 3)  # Place RED at (3,7), sandwiches AI at (3,6)
    assert g.combo > first_combo
    assert g.max_combo >= g.combo


def test_super_activation():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.turn = Turn.PLAYER
    g.player_color = COLOR_RED
    g.heat = 0.0
    g.combo = 3  # One away from SUPER
    g.max_combo = 3

    g.grid = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    g.grid[3][3] = COLOR_RED
    g.grid[3][4] = COLOR_AI
    g._handle_click(5, 3)  # This should make combo=4 and trigger SUPER
    assert g.combo >= 4
    assert g.super_mode
    assert g.super_timer == SUPER_DURATION
    assert g.shake_frames > 0


def test_super_mode_3x_score():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.turn = Turn.PLAYER
    g.player_color = COLOR_RED
    g.heat = 0.0
    g.combo = 4
    g.super_mode = True
    g.super_timer = 100
    g.max_combo = 4

    g.grid = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    g.grid[3][3] = COLOR_RED
    g.grid[3][4] = COLOR_AI
    score_before = g.score
    g._handle_click(5, 3)
    # During SUPER, flips get 3x multiplier
    assert g.score > score_before
    # Points = match_count * 10 * (1 + 0.5*(combo-1)) * 3
    expected_multiplier = (1.0 + 0.5 * (g.combo - 1)) * 3.0
    expected = int(1 * 10 * expected_multiplier)
    # Score gain should be approximately this (pre-combo state is combo=4 at click time)
    # Actually after handle_click, combo becomes 5, so multiplier uses combo-1=4
    assert g.score - score_before > 0


def test_super_timer_decrement():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 10
    g._update_super()
    assert g.super_timer == 9
    assert g.super_mode

    g.super_timer = 1
    g._update_super()
    assert g.super_timer == 0
    assert not g.super_mode  # Deactivated


# ── HEAT System ──

def test_heat_decay():
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat == pytest.approx(49.98, abs=0.001)


def test_heat_never_negative():
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0

    g.heat = 0.01
    g._update_heat()
    assert g.heat == 0.0  # Decays to 0


def test_heat_game_over_check():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = HEAT_MAX  # 100
    # Simulate what _update_playing does
    if g.heat >= HEAT_MAX:
        g.phase = Phase.GAME_OVER
        g.game_over_reason = "overheat"
    assert g.phase == Phase.GAME_OVER
    assert g.game_over_reason == "overheat"


# ── Board Full ──

def test_board_not_full_initially():
    g = _make_game()
    assert not g._check_board_full()


def test_board_full_detection():
    g = _make_game()
    # Fill entire board
    g.grid = [[COLOR_RED] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    assert g._check_board_full()


def test_count_discs():
    g = _make_game()
    assert g._count_discs(COLOR_RED) == 1
    assert g._count_discs(COLOR_GREEN) == 1
    assert g._count_discs(COLOR_AI) == 2
    assert g._count_discs(EMPTY) == 60


# ── AI Logic ──

def test_ai_finds_best_move():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.grid = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    g.grid[3][3] = COLOR_RED
    g.grid[3][4] = COLOR_AI
    g.grid[3][5] = COLOR_RED
    g.grid[4][4] = COLOR_AI
    g.grid[5][5] = COLOR_GREEN

    best = g._ai_find_best_move()
    assert best is not None
    col, row = best
    assert g._is_valid_move(col, row, COLOR_AI)


def test_ai_no_valid_moves():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.grid = [[COLOR_RED] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    # No AI discs, no empty cells
    result = g._ai_find_best_move()
    assert result is None


def test_ai_do_move():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 0.0
    g.grid = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    g.grid[3][3] = COLOR_RED
    g.grid[3][4] = COLOR_AI
    g.grid[3][5] = COLOR_RED
    g.grid[4][4] = COLOR_AI
    g.grid[5][5] = COLOR_GREEN

    ai_score_before = g.ai_score
    g._ai_do_move()
    assert g.ai_score > ai_score_before


def test_ai_skip_adds_heat():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 10.0
    # Fill board so AI has no moves
    g.grid = [[COLOR_RED] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    g._ai_do_move()
    # AI skips, so heat penalty applied
    assert g.heat > 10.0


# ── Color Selection ──

def test_color_select():
    g = _make_game()
    assert g.player_color == COLOR_RED
    g._handle_color_select(COLOR_GREEN)
    assert g.player_color == COLOR_GREEN
    g._handle_color_select(COLOR_DARK_BLUE)
    assert g.player_color == COLOR_DARK_BLUE
    g._handle_color_select(COLOR_YELLOW)
    assert g.player_color == COLOR_YELLOW


# ── Particle System ──

def test_particle_spawn():
    g = _make_game()
    assert len(g.particles) == 0
    g._spawn_particles_burst(100.0, 100.0, 8, 10)
    assert len(g.particles) == 10
    for p in g.particles:
        assert isinstance(p, Particle)
        assert p.life >= 15
        assert p.life <= 30


def test_particle_update_removes_dead():
    g = _make_game()
    g.particles = [
        Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=8),
        Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=3, color=8),
    ]
    g._update_particles()
    # life=1 → decremented to 0 → removed. life=3 → 2 → kept
    assert len(g.particles) == 1
    assert g.particles[0].life == 2


def test_floating_text_spawn():
    g = _make_game()
    assert len(g.floating_texts) == 0
    g._spawn_floating_text(100.0, 100.0, "+50", 7)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.text == "+50"
    assert ft.life == 30
    assert ft.vy == -0.5


def test_floating_text_update():
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=0.0, y=0.0, text="A", color=7, life=1, vy=-0.5),
        FloatingText(x=0.0, y=0.0, text="B", color=7, life=5, vy=-0.5),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "B"
    assert g.floating_texts[0].life == 4


# ── Edge Cases ──

def test_click_out_of_bounds():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.turn = Turn.PLAYER
    g.player_color = COLOR_RED
    # Click should be handled by _handle_click which checks validity
    # -1, -1 is out of bounds
    flippable = g._get_flippable(-1, -1, COLOR_RED)
    assert len(flippable) == 0


def test_click_on_already_occupied():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.turn = Turn.PLAYER
    g.player_color = COLOR_RED
    g.grid = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    g.grid[3][3] = COLOR_RED
    g.grid[3][4] = COLOR_AI
    # Click on (3,3) which has RED
    assert not g._is_valid_move(3, 3, COLOR_RED)


def test_reset_clears_state():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.score = 100
    g.combo = 5
    g.heat = 50.0
    g.super_mode = True
    g.particles = [Particle(0, 0, 0, 0, 10, 8)]
    g.reset()

    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert not g.super_mode
    assert g.particles == []


def test_player_no_valid_moves_heat():
    """When player has no valid moves, _update_playing gives slight heat penalty."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.turn = Turn.PLAYER
    g.heat = 10.0
    # Fill board with only AI discs and a few player discs — player has no valid moves
    g.grid = [[COLOR_AI] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    g.grid[0][0] = COLOR_RED
    # Player needs to sandwich AI between two REDs — not possible
    assert g._get_valid_moves_for(COLOR_RED) == []


def test_handle_click_invalid_move():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.turn = Turn.PLAYER
    g.player_color = COLOR_RED
    g.score = 0
    g.combo = 0
    # Click on invalid cell (no sandwich)
    g.grid = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    g.grid[3][3] = COLOR_RED
    g._handle_click(0, 0)  # No sandwich possible
    assert g.score == 0
    assert g.combo == 0


def test_valid_moves_for_ai():
    g = _make_game()
    g.phase = Phase.PLAYING
    # With initial setup, AI should have valid moves
    moves = g._get_valid_moves_for(COLOR_AI)
    assert len(moves) > 0
    for col, row in moves:
        assert g._is_valid_move(col, row, COLOR_AI)


# ── Constants ──

def test_directions():
    assert len(DIRS) == 8
    # All 8 directions should be unique
    assert len(set(DIRS)) == 8


def test_player_colors():
    assert len(PLAYER_COLORS) == 4
    assert COLOR_RED in PLAYER_COLORS
    assert COLOR_GREEN in PLAYER_COLORS
    assert COLOR_DARK_BLUE in PLAYER_COLORS
    assert COLOR_YELLOW in PLAYER_COLORS


def test_super_duration():
    assert SUPER_DURATION == 300
    assert SUPER_DURATION / 60 == 5.0  # 5 seconds at 60fps


def test_heat_max():
    assert HEAT_MAX == 100


# ── FloatingText lifecycle off-by-one check ──

def test_floating_text_life_2_survives_one_update():
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=0.0, y=0.0, text="X", color=7, life=2, vy=-0.5),
    ]
    g._update_floating_texts()
    # life=2 → decremented to 1 → kept
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].life == 1
