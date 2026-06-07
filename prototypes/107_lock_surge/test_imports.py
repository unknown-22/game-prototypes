"""test_imports.py — Headless logic tests for Lockpick Surge."""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/107_lock_surge")

from main import (  # noqa: E402
    Game,
    Phase,
    PinState,
    Particle,
    FloatingText,
    SynthesisStep,
    COLOR_VALS,
    GREEN,
    LIGHT_BLUE,
    WHITE,
    RED,
    YELLOW,
)


def _make_game(seed: int = 42) -> Game:
    """Factory: create Game without pyxel.init/run."""
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.tension = 0
    g.locks_cleared = 0
    g.security_timer = 0
    g.prev_color = None
    g.grid = []
    g.state = []
    g.jammed_count = 0
    g.synth_steps = []
    g.synth_step_idx = 0
    g.synth_bonus = 0
    g.particles = []
    g.floating_texts = []
    g._shake_frames = 0
    g.game_timer = 90 * 30
    g.high_score = 0
    g.final_score_breakdown = []
    g.synth_anim_timer = 0
    g.synth_anim_duration = 20
    g._prev_mouse_pressed = False
    g.reset()
    return g


def _make_blank_game(seed: int = 42) -> Game:
    """Factory: Game with manually-set grid (no random generation)."""
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.tension = 0
    g.locks_cleared = 0
    g.security_timer = 0
    g.prev_color = None
    g.grid = [[0] * Game.GRID_COLS for _ in range(Game.GRID_ROWS)]
    g.state = [[PinState.LOCKED] * Game.GRID_COLS for _ in range(Game.GRID_ROWS)]
    g.jammed_count = 0
    g.synth_steps = []
    g.synth_step_idx = 0
    g.synth_bonus = 0
    g.particles = []
    g.floating_texts = []
    g._shake_frames = 0
    g.game_timer = 90 * 30
    g.high_score = 0
    g.final_score_breakdown = []
    g.synth_anim_timer = 0
    g.synth_anim_duration = 20
    g._prev_mouse_pressed = False
    return g


# ── Module-level imports ──
def test_imports():
    """Verify all classes and constants import correctly."""
    assert Phase.TITLE is not None
    assert PinState.LOCKED is not None
    assert len(COLOR_VALS) == 4
    assert COLOR_VALS[0] == RED  # 8
    assert COLOR_VALS[1] == GREEN  # 3
    assert COLOR_VALS[2] == LIGHT_BLUE  # 6
    assert COLOR_VALS[3] == YELLOW  # 10
    assert Game.SCREEN_W == 320
    assert Game.SCREEN_H == 240
    assert Game.GRID_COLS == 4
    assert Game.GRID_ROWS == 5
    assert Game.SYNTHESIS_THRESHOLD == 4
    assert Game.TENSION_PER_CLICK == 12
    assert Game.MAX_TENSION == 100
    assert Game.SECURITY_THRESHOLD == 70
    assert Game.SECURITY_INTERVAL == 30
    assert Game.MAX_JAMMED == 8


# ── Game init + grid generation ──
def test_make_game():
    """_make_game creates a valid Game with 5x4 grid."""
    g = _make_game()
    assert len(g.grid) == Game.GRID_ROWS
    assert len(g.grid[0]) == Game.GRID_COLS
    assert len(g.state) == Game.GRID_ROWS
    assert all(s == PinState.LOCKED for row in g.state for s in row)
    assert g.score == 0
    assert g.combo == 0
    assert g.tension == 0
    assert g.locks_cleared == 0
    assert g.jammed_count == 0
    assert g.phase == Phase.TITLE


def test_generate_lock_has_all_colors():
    """_generate_lock ensures all 4 colors appear at least once."""
    g = _make_game()
    colors = set()
    for r in range(Game.GRID_ROWS):
        for c in range(Game.GRID_COLS):
            colors.add(g.grid[r][c])
    assert len(colors) == 4, f"Expected all 4 colors, got {len(colors)}"


def test_make_game_deterministic():
    """Same seed produces same grid."""
    g1 = _make_game(42)
    g2 = _make_game(42)
    for r in range(Game.GRID_ROWS):
        for c in range(Game.GRID_COLS):
            assert g1.grid[r][c] == g2.grid[r][c]


# ── _handle_click ──
# IMPORTANT: _handle_click(col, row) accesses grid[row][col].
# When setting up cells manually, use grid[row][col] notation.

def test_handle_click_sets_tumbler():
    """Clicking a LOCKED tumbler sets it and adds score."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    # Set grid[0][0] to RED (color 0)
    g.grid[0][0] = 0  # row 0, col 0 → _handle_click(0, 0)
    # Ensure background is different color to avoid BFS surprises
    for r in range(Game.GRID_ROWS):
        for c in range(Game.GRID_COLS):
            if not (r == 0 and c == 0):
                g.grid[r][c] = 2  # BLUE
    
    result = g._handle_click(0, 0)
    assert result is True
    assert g.state[0][0] == PinState.SET
    assert g.combo == 1
    assert g.prev_color == 0
    assert g.tension == Game.TENSION_PER_CLICK  # 12
    assert g.score == 100  # combo=1, multiplier=1.0, base=100
    assert g.max_combo == 1


def test_handle_click_same_color_combo():
    """Same-color consecutive clicks increase combo. No synthesis if not adjacent."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    # Fill with BLUE background
    for r in range(Game.GRID_ROWS):
        for c in range(Game.GRID_COLS):
            g.grid[r][c] = 2  # BLUE
    # Place RED cells at non-adjacent positions:
    # grid[0][0] = RED → click (col=0, row=0)
    # grid[2][0] = RED → click (col=0, row=2) — non-adjacent to first
    # grid[4][0] = RED → click (col=0, row=4) — non-adjacent
    # grid[1][2] = RED → click (col=2, row=1) — non-adjacent
    g.grid[0][0] = 0  # RED, row 0 col 0
    g.grid[2][0] = 0  # RED, row 2 col 0
    g.grid[4][0] = 0  # RED, row 4 col 0
    g.grid[1][2] = 0  # RED, row 1 col 2
    
    g._handle_click(0, 0)  # grid[0][0]=RED, combo=1
    assert g.score == 100
    assert g.combo == 1
    
    g._handle_click(0, 2)  # grid[2][0]=RED, combo=2
    assert g.score == 250
    assert g.combo == 2
    
    g._handle_click(0, 4)  # grid[4][0]=RED, combo=3
    assert g.score == 450
    assert g.combo == 3
    
    g._handle_click(2, 1)  # grid[1][2]=RED, combo=4 → SYNTHESIS!
    assert g.combo == 4
    # BFS should find no adjacent RED cells since all neighbors are BLUE


def test_handle_click_different_color_resets_combo():
    """Different color click resets combo to 1."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    for r in range(Game.GRID_ROWS):
        for c in range(Game.GRID_COLS):
            g.grid[r][c] = 2  # BLUE background
    
    g.grid[0][0] = 0  # RED, row 0 col 0
    g.grid[2][0] = 0  # RED, row 2 col 0
    g.grid[0][1] = 1  # GREEN, row 0 col 1

    g._handle_click(0, 0)  # RED, combo=1
    assert g.combo == 1
    assert g.prev_color == 0
    
    g._handle_click(0, 2)  # RED (grid[2][0]), combo=2
    assert g.combo == 2
    
    g._handle_click(1, 0)  # GREEN (grid[0][1]), combo resets to 1
    assert g.combo == 1
    assert g.prev_color == 1


def test_handle_click_already_set_returns_false():
    """Clicking an already SET tumbler is ignored."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.grid[0][0] = 0
    g._handle_click(0, 0)  # Sets it
    result = g._handle_click(0, 0)  # Already SET
    assert result is False


def test_handle_click_jammed_returns_false():
    """Clicking a JAMMED tumbler is ignored."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.grid[0][0] = 0
    g.state[0][0] = PinState.JAMMED
    result = g._handle_click(0, 0)
    assert result is False


def test_handle_click_out_of_bounds():
    """Out-of-bounds click returns False."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    assert g._handle_click(-1, 0) is False
    assert g._handle_click(0, -1) is False
    assert g._handle_click(Game.GRID_COLS, 0) is False
    assert g._handle_click(0, Game.GRID_ROWS) is False


def test_handle_click_tension_max_triggers_game_over():
    """When tension reaches MAX, game over triggers."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.tension = Game.MAX_TENSION - Game.TENSION_PER_CLICK  # 88
    g.grid[0][0] = 0
    
    g._handle_click(0, 0)
    assert g.tension == Game.MAX_TENSION  # 100
    assert g.phase == Phase.GAME_OVER
    assert g.high_score > 0


def test_handle_click_synthesis_triggered():
    """COMBO>=4 triggers SYNTHESIS phase."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    for r in range(Game.GRID_ROWS):
        for c in range(Game.GRID_COLS):
            g.grid[r][c] = 0  # All RED
    
    # Build combo to 3 (non-adjacent to avoid early synthesis)
    g._handle_click(0, 0)  # combo 1
    g._handle_click(1, 0)  # combo 2
    g._handle_click(2, 0)  # combo 3
    assert g.combo == 3
    
    # 4th click → combo 4 → synthesis
    result = g._handle_click(3, 0)
    assert result is True
    assert g.phase == Phase.SYNTHESIS_ANIM
    assert len(g.synth_steps) > 0


def test_handle_click_all_set_triggers_lock_clear():
    """Setting the last tumbler triggers LOCK_CLEAR."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    for r in range(Game.GRID_ROWS):
        for c in range(Game.GRID_COLS):
            g.grid[r][c] = 0
    
    # Set all tumblers except one
    for r in range(Game.GRID_ROWS):
        for c in range(Game.GRID_COLS):
            if not (r == 0 and c == 0):
                g.state[r][c] = PinState.SET
                g.combo = 1  # prevent synthesis
    
    # Set combo to avoid synthesis
    g.combo = 1
    g.prev_color = 1  # Different from color 0 → will reset combo
    
    result = g._handle_click(0, 0)
    assert result is True
    assert g.phase == Phase.LOCK_CLEAR
    assert g.locks_cleared == 1
    assert len(g.final_score_breakdown) > 0
    assert g.high_score > 0


# ── _bfs_synthesis ──
def test_bfs_synthesis_finds_adjacent_same_color():
    """BFS finds all adjacent same-color LOCKED tumblers."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    # Create a 3×2 block of RED (color 0) at top-left
    for r in range(3):
        for c in range(2):
            g.grid[r][c] = 0
            g.state[r][c] = PinState.LOCKED
    # Surround with different color
    for r in range(Game.GRID_ROWS):
        for c in range(Game.GRID_COLS):
            if r >= 3 or c >= 2:
                g.grid[r][c] = 1  # GREEN
    
    steps = g._bfs_synthesis(0, 0)
    assert len(steps) == 5
    
    # Verify all are set now
    for step in steps:
        assert g.state[step.row][step.col] == PinState.SET


def test_bfs_synthesis_no_adjacent():
    """BFS with no adjacent same-color returns empty."""
    g = _make_blank_game()
    g.grid[0][0] = 0  # RED at corner
    g.grid[0][1] = 1  # GREEN next to it
    g.grid[1][0] = 1  # GREEN below
    g.grid[1][1] = 1  # GREEN diagonal
    
    steps = g._bfs_synthesis(0, 0)
    assert len(steps) == 0


def test_bfs_synthesis_respects_already_set():
    """BFS skips already-SET tumblers."""
    g = _make_blank_game()
    # All RED
    for r in range(Game.GRID_ROWS):
        for c in range(Game.GRID_COLS):
            g.grid[r][c] = 0
    # Set grid[1][0] (row=1, col=0) = SET
    # This corresponds to (col=0, row=1) in BFS coordinates
    g.state[1][0] = PinState.SET
    
    steps = g._bfs_synthesis(0, 0)
    # Should not include col=0, row=1 (the cell we pre-set)
    step_coords = {(s.col, s.row) for s in steps}
    assert (0, 1) not in step_coords, f"Found (0,1) in {step_coords}"


def test_bfs_synthesis_sets_score():
    """BFS adds 200 per auto-set tumbler."""
    g = _make_blank_game()
    for r in range(Game.GRID_ROWS):
        for c in range(Game.GRID_COLS):
            g.grid[r][c] = 0  # All RED
    
    g.score = 0
    g.synth_bonus = 0
    steps = g._bfs_synthesis(0, 0)
    expected = len(steps) * 200
    assert g.score == expected
    assert g.synth_bonus == expected


# ── _release_tension ──
def test_release_tension_resets_state():
    """Release tension resets tension, combo, prev_color, security_timer."""
    g = _make_blank_game()
    g.tension = 85
    g.combo = 5
    g.prev_color = 2
    g.security_timer = 25
    
    g._release_tension()
    
    assert g.tension == 0
    assert g.combo == 0
    assert g.prev_color is None
    assert g.security_timer == 0


# ── _update_security ──
def test_update_security_jams_one_on_interval():
    """Every SECURITY_INTERVAL frames, one LOCKED tumbler gets jammed."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.tension = Game.SECURITY_THRESHOLD  # 70
    g.security_timer = Game.SECURITY_INTERVAL - 1  # 29
    
    # Patch randomness for deterministic test
    old_choice = g._rng.choice
    old_random = g._rng.random
    g._rng.choice = lambda seq: seq[0]  # Always first LOCKED
    g._rng.random = lambda: 0.0  # Never spread (below 0.5)
    
    g._update_security()
    
    assert g.jammed_count >= 1  # At least one jammed
    assert g.security_timer == 0  # Timer reset
    
    g._rng.choice = old_choice
    g._rng.random = old_random


def test_update_security_ca_spread():
    """CA spread: jammed pins spread to adjacent LOCKED pins."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.tension = Game.SECURITY_THRESHOLD
    g.security_timer = Game.SECURITY_INTERVAL - 1
    
    # Manually set one cell as jammed
    g.state[0][0] = PinState.JAMMED
    g.jammed_count = 1
    # Adjacent cells are LOCKED
    g.state[0][1] = PinState.LOCKED
    g.state[1][0] = PinState.LOCKED
    g.state[1][1] = PinState.LOCKED
    
    # Patch: choice picks a locked cell, random always spreads
    old_choice = g._rng.choice
    old_random = g._rng.random
    g._rng.choice = lambda seq: seq[-1]
    g._rng.random = lambda: 0.4  # Always spread (< 0.5)
    
    g._update_security()
    
    assert g.jammed_count > 1
    
    g._rng.choice = old_choice
    g._rng.random = old_random


def test_update_security_max_jammed_game_over():
    """When jammed_count >= MAX_JAMMED, game over."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.tension = Game.SECURITY_THRESHOLD
    g.security_timer = Game.SECURITY_INTERVAL - 1
    g.jammed_count = Game.MAX_JAMMED - 1  # 7
    
    old_random = g._rng.random
    g._rng.random = lambda: 1.0  # Never spread
    
    g._update_security()
    
    assert g.jammed_count >= Game.MAX_JAMMED
    assert g.phase == Phase.GAME_OVER
    
    g._rng.random = old_random


def test_update_security_only_when_tension_high():
    """Security update doesn't happen below threshold in the game loop.
    (But _update_security itself runs regardless — it's guarded in update())"""
    g = _make_blank_game()
    g.tension = 50  # Below threshold
    g.security_timer = Game.SECURITY_INTERVAL - 1
    
    old_choice = g._rng.choice
    old_random = g._rng.random
    g._rng.choice = lambda seq: seq[0]
    g._rng.random = lambda: 0.0
    
    initial_jammed = g.jammed_count
    g._update_security()
    assert g.jammed_count >= initial_jammed
    
    g._rng.choice = old_choice
    g._rng.random = old_random


# ── _check_game_over ──
def test_check_game_over_tension():
    """Game over when tension >= MAX_TENSION."""
    g = _make_game()
    g.tension = Game.MAX_TENSION
    assert g._check_game_over() is True


def test_check_game_over_jammed():
    """Game over when jammed_count >= MAX_JAMMED."""
    g = _make_game()
    g.jammed_count = Game.MAX_JAMMED
    assert g._check_game_over() is True


def test_check_game_over_timer():
    """Game over when game_timer <= 0."""
    g = _make_game()
    g.game_timer = 0
    assert g._check_game_over() is True


def test_check_game_over_false():
    """Not game over under normal conditions."""
    g = _make_game()
    g.tension = 50
    g.jammed_count = 0
    g.game_timer = 1000
    assert g._check_game_over() is False


# ── _all_set ──
def test_all_set_false():
    """_all_set returns False when some tumblers are LOCKED."""
    g = _make_game()
    assert g._all_set() is False


def test_all_set_true():
    """_all_set returns True when all tumblers are SET."""
    g = _make_blank_game()
    for r in range(Game.GRID_ROWS):
        for c in range(Game.GRID_COLS):
            g.state[r][c] = PinState.SET
    assert g._all_set() is True


def test_all_set_jammed_blocks():
    """_all_set returns False if any tumbler is JAMMED."""
    g = _make_blank_game()
    for r in range(Game.GRID_ROWS):
        for c in range(Game.GRID_COLS):
            g.state[r][c] = PinState.SET
    g.state[0][0] = PinState.JAMMED
    assert g._all_set() is False


# ── _count_set ──
def test_count_set():
    """_count_set counts tumblers in SET state."""
    g = _make_blank_game()
    assert g._count_set() == 0
    
    g.state[0][0] = PinState.SET
    g.state[0][1] = PinState.SET
    g.state[1][0] = PinState.SET
    assert g._count_set() == 3


# ── _grid_to_screen ──
def test_grid_to_screen():
    """Coordinate conversion works correctly."""
    g = _make_game()
    sx, sy = g._grid_to_screen(0, 0)
    assert sx == Game.GRID_X  # 60
    assert sy == Game.GRID_Y  # 20
    
    sx, sy = g._grid_to_screen(1, 2)
    assert sx == Game.GRID_X + 1 * (Game.CELL_SIZE + Game.CELL_GAP)
    assert sy == Game.GRID_Y + 2 * (Game.CELL_SIZE + Game.CELL_GAP)


# ── Particle system ──
def test_spawn_particles():
    """_spawn_particles creates correct count of particles."""
    g = _make_game()
    g._spawn_particles(100.0, 100.0, WHITE, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert -1.5 <= p.vx <= 1.5
        assert -1.5 <= p.vy <= 1.5
        assert 15 <= p.life <= 25
        assert p.color == WHITE


def test_update_particles_lifecycle():
    """Particles are removed when life <= 0."""
    g = _make_game()
    g._spawn_particles(100.0, 100.0, WHITE, 2)
    g.particles[0].life = 1
    g.particles[1].life = 2
    
    g._update_particles()
    
    assert len(g.particles) == 1
    assert g.particles[0].life == 1


def test_update_particles_gravity():
    """Particles are affected by gravity (vy += 0.05)."""
    g = _make_game()
    g._spawn_particles(100.0, 100.0, WHITE, 1)
    original_vy = g.particles[0].vy
    g._update_particles()
    expected_vy = original_vy + 0.05
    assert abs(g.particles[0].vy - expected_vy) < 0.001


# ── Floating text ──
def test_spawn_floating_text():
    """_spawn_floating_text creates floating text."""
    g = _make_game()
    g._spawn_floating_text(100.0, 100.0, "+150", YELLOW)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "+150"
    assert g.floating_texts[0].color == YELLOW
    assert 20 <= g.floating_texts[0].life <= 30


def test_update_floating_texts_lifecycle():
    """Floating text is removed when life <= 0."""
    g = _make_game()
    g._spawn_floating_text(100.0, 100.0, "test", WHITE)
    g.floating_texts[0].life = 1
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Score multipliers ──
def test_score_multipliers():
    """Score calculation uses correct multipliers per combo level."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    for r in range(Game.GRID_ROWS):
        for c in range(Game.GRID_COLS):
            g.grid[r][c] = 2  # BLUE background
    g.grid[0][0] = 0  # RED
    g.grid[2][0] = 0  # RED
    g.grid[4][0] = 0  # RED
    g.grid[1][2] = 0  # RED
    
    g._handle_click(0, 0)  # combo=1, +100
    assert g.score == 100
    assert g.combo == 1
    
    g._handle_click(0, 2)  # combo=2, +150
    assert g.score == 250
    assert g.combo == 2
    
    g._handle_click(0, 4)  # combo=3, +200
    assert g.score == 450
    assert g.combo == 3
    
    g._handle_click(2, 1)  # combo=4, +300 (+ synthesis if adjacent)
    assert g.combo == 4


# ── Synthesis scoring ──
def test_synthesis_adds_200_per_cell():
    """BFS synthesis adds 200 score per auto-set tumbler."""
    g = _make_blank_game()
    for r in range(Game.GRID_ROWS):
        for c in range(Game.GRID_COLS):
            g.grid[r][c] = 0  # All RED
    
    steps = g._bfs_synthesis(0, 0)
    expected = len(steps) * 200
    assert g.score == expected
    assert g.synth_bonus == expected


# ── Reset ──
def test_reset_clears_state():
    """reset() clears all game state for fresh start."""
    g = _make_game()
    g.score = 500
    g.combo = 3
    g.max_combo = 3
    g.tension = 50
    g.locks_cleared = 2
    g.high_score = 500
    
    g.reset()
    
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.tension == 0
    assert g.locks_cleared == 0
    assert len(g.grid) == Game.GRID_ROWS
    assert g.high_score == 500  # High score persists


# ── Edge cases ──
def test_empty_synth_steps():
    """Synthesis with no steps doesn't crash."""
    g = _make_blank_game()
    g.synth_steps = []
    g.synth_step_idx = 0
    g.synth_anim_timer = 0
    g.phase = Phase.SYNTHESIS_ANIM
    g.synth_anim_timer += 1
    if g.synth_step_idx >= len(g.synth_steps) or g.synth_anim_timer >= g.synth_anim_duration:
        g.phase = Phase.PLAYING
    assert g.phase == Phase.PLAYING


def test_lock_clear_bonus():
    """Lock clear bonus = tension * 10."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.tension = 60
    # Set all EXCEPT grid[0][0] to SET
    for r in range(Game.GRID_ROWS):
        for c in range(Game.GRID_COLS):
            g.state[r][c] = PinState.SET
    g.state[0][0] = PinState.LOCKED  # Leave grid[0][0] LOCKED
    g.grid[0][0] = 0  # RED
    g.score = 1000
    g.combo = 1
    g.prev_color = 1  # Different from color 0 → combo resets
    
    g._handle_click(0, 0)  # Sets the last LOCKED tumbler → LOCK_CLEAR
    assert g.phase == Phase.LOCK_CLEAR
    assert g.locks_cleared == 1
    # Score = 1000 + 100 (base click) + (60+12)*10 (clear bonus on updated tension)
    assert g.score == 1000 + 100 + 720


def test_max_combo_tracking():
    """max_combo tracks the highest combo achieved even after reset."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    for r in range(Game.GRID_ROWS):
        for c in range(Game.GRID_COLS):
            g.grid[r][c] = 2  # BLUE background
    g.grid[0][0] = 0  # RED, row 0 col 0
    g.grid[2][0] = 0  # RED, row 2 col 0
    g.grid[4][0] = 0  # RED, row 4 col 0
    g.grid[0][1] = 1  # GREEN, row 0 col 1
    
    g._handle_click(0, 0)  # RED, combo=1
    assert g.max_combo == 1
    g._handle_click(0, 2)  # RED, combo=2
    assert g.max_combo == 2
    g._handle_click(0, 4)  # RED, combo=3
    assert g.max_combo == 3
    
    # Now click different color → combo resets to 1, max_combo stays
    g._handle_click(1, 0)  # GREEN (grid[0][1]), combo=1
    assert g.combo == 1
    assert g.max_combo == 3  # Still tracks the peak


def test_tension_never_exceeds_max():
    """Tension is clamped at MAX_TENSION."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.tension = Game.MAX_TENSION - 5  # 95
    g.grid[0][0] = 0
    
    g._handle_click(0, 0)
    assert g.tension == Game.MAX_TENSION  # Clamped at 100


# ── Dataclass creation ──
def test_particle_creation():
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-0.5, life=15, color=RED)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -0.5
    assert p.life == 15
    assert p.color == RED


def test_floating_text_creation():
    ft = FloatingText(x=50.0, y=60.0, text="+100", life=25, color=YELLOW)
    assert ft.text == "+100"
    assert ft.color == YELLOW


def test_synthesis_step_creation():
    ss = SynthesisStep(col=2, row=3, color=0)
    assert ss.col == 2
    assert ss.row == 3
    assert ss.color == 0
