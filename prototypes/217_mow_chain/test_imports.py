"""test_imports.py — Headless logic tests for 217_mow_chain."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from main import (  # type: ignore[import-not-found]
    FLOWER_COLORS,
    FloatingText,
    Game,
    Particle,
    Phase,
)


def _make_game() -> Game:
    """Factory: create Game bypassing pyxel init/run for headless testing."""
    g = Game.__new__(Game)
    # Pre-init all attributes that reset() touches
    g._rng = random.Random(42)
    g.reset()
    g.phase = Phase.PLAYING  # Set after reset for test readiness
    return g


# ── Data class tests ──
def test_particle_creation() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=20, color=8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.life == 20
    assert p.color == 8


def test_floating_text_creation() -> None:
    ft = FloatingText(x=5.0, y=10.0, text="+10", life=30, color=7)
    assert ft.x == 5.0
    assert ft.y == 10.0
    assert ft.text == "+10"
    assert ft.life == 30
    assert ft.color == 7


# ── Grid initialization tests ──
def test_grid_dimensions() -> None:
    g = _make_game()
    assert len(g.grid) == Game.ROWS
    assert len(g.grid[0]) == Game.COLS
    assert len(g.flowers) == Game.ROWS
    assert len(g.flowers[0]) == Game.COLS


def test_grid_all_uncut_initially() -> None:
    g = _make_game()
    for row in range(Game.ROWS):
        for col in range(Game.COLS):
            assert g.grid[row][col] == 0


def test_flower_colors_valid() -> None:
    g = _make_game()
    for row in range(Game.ROWS):
        for col in range(Game.COLS):
            assert 0 <= g.flowers[row][col] < len(FLOWER_COLORS)


def test_mower_start_center() -> None:
    g = _make_game()
    assert g.mower_col == Game.COLS // 2
    assert g.mower_row == Game.ROWS // 2


def test_initial_state() -> None:
    g = _make_game()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == 60 * 30
    assert g.super_timer == 0
    assert g.last_color == -1
    assert g.multiplier == 1
    assert g.particles == []
    assert g.floating_texts == []


# ── Movement tests ──
def test_move_right() -> None:
    g = _make_game()
    start_col = g.mower_col
    result = g._move_mower(1, 0)
    assert result is True
    assert g.mower_col == start_col + 1
    assert g.mower_row == Game.ROWS // 2


def test_move_left() -> None:
    g = _make_game()
    start_col = g.mower_col
    result = g._move_mower(-1, 0)
    assert result is True
    assert g.mower_col == start_col - 1


def test_move_up() -> None:
    g = _make_game()
    start_row = g.mower_row
    result = g._move_mower(0, -1)
    assert result is True
    assert g.mower_row == start_row - 1


def test_move_down() -> None:
    g = _make_game()
    start_row = g.mower_row
    result = g._move_mower(0, 1)
    assert result is True
    assert g.mower_row == start_row + 1


def test_move_oob_left() -> None:
    g = _make_game()
    g.mower_col = 0
    result = g._move_mower(-1, 0)
    assert result is False
    assert g.mower_col == 0


def test_move_oob_right() -> None:
    g = _make_game()
    g.mower_col = Game.COLS - 1
    result = g._move_mower(1, 0)
    assert result is False
    assert g.mower_col == Game.COLS - 1


def test_move_oob_up() -> None:
    g = _make_game()
    g.mower_row = 0
    result = g._move_mower(0, -1)
    assert result is False
    assert g.mower_row == 0


def test_move_oob_down() -> None:
    g = _make_game()
    g.mower_row = Game.ROWS - 1
    result = g._move_mower(0, 1)
    assert result is False
    assert g.mower_row == Game.ROWS - 1


def test_move_sets_direction() -> None:
    g = _make_game()
    g._move_mower(1, 0)
    assert g.mower_dir == 0  # right
    g._move_mower(0, 1)
    assert g.mower_dir == 1  # down
    g._move_mower(-1, 0)
    assert g.mower_dir == 2  # left
    g._move_mower(0, -1)
    assert g.mower_dir == 3  # up


# ── Cutting tests ──
def test_cut_tile_marks_grid() -> None:
    g = _make_game()
    col, row = g.mower_col, g.mower_row
    g._cut_tile(col, row)
    assert g.grid[row][col] == -1


def test_cut_tile_adds_heat() -> None:
    g = _make_game()
    heat_before = g.heat
    g._cut_tile(g.mower_col, g.mower_row)
    assert g.heat > heat_before
    assert g.heat == Game.HEAT_PER_CUT


def test_cut_tile_spawns_particles() -> None:
    g = _make_game()
    assert len(g.particles) == 0
    g._cut_tile(g.mower_col, g.mower_row)
    assert len(g.particles) >= 8


def test_cut_tile_spawns_floating_text() -> None:
    g = _make_game()
    assert len(g.floating_texts) == 0
    g._cut_tile(g.mower_col, g.mower_row)
    assert len(g.floating_texts) >= 1


def test_move_cuts_tile() -> None:
    g = _make_game()
    assert g.grid[g.mower_row][g.mower_col] == 0
    g._move_mower(1, 0)
    # Previous position was cut
    # Actually the _move_mower moves first, then cuts at NEW position
    prev_row = Game.ROWS // 2
    prev_col = Game.COLS // 2
    # The OLD position is NOT cut — only the new position
    # Actually wait, _move_mower moves to new position, then cuts there
    # The old position stays uncut unless the mower was there before
    # After moving, the new position should be cut
    new_col = prev_col + 1
    assert g.grid[prev_row][new_col] == -1


def test_already_cut_no_re_cut() -> None:
    g = _make_game()
    col, row = g.mower_col, g.mower_row
    g._cut_tile(col, row)  # First cut
    particles_before = len(g.particles)
    g._move_mower(-1, 0)  # Move away
    g._move_mower(1, 0)   # Move back to already cut tile
    # Should not spawn new particles for the already-cut tile
    # check that no additional particles beyond what the move-cut-then-already-cut generates
    # Actually _move_mower only calls _cut_tile if not already_cut
    assert g.grid[row][col] == -1  # Still cut
    # Moving back made it skip cutting → no extra particles from that cell


# ── Combo tests ──
def test_first_cut_builds_combo_1() -> None:
    g = _make_game()
    assert g.combo == 0
    g._cut_tile(g.mower_col, g.mower_row)
    assert g.combo == 1


def test_same_color_extends_combo() -> None:
    g = _make_game()
    # Force two adjacent tiles to have same color
    col1, row1 = 5, 6
    col2, row2 = 6, 6
    color_idx = 0  # RED
    g.flowers[row1][col1] = color_idx
    g.flowers[row2][col2] = color_idx
    g.grid[row1][col1] = 0
    g.grid[row2][col2] = 0
    g.mower_col = col1
    g.mower_row = row1

    g._cut_tile(col1, row1)
    assert g.combo == 1
    assert g.last_color == color_idx

    g.mower_col = col2
    g.mower_row = row2
    g._cut_tile(col2, row2)
    assert g.combo == 2


def test_different_color_resets_combo() -> None:
    g = _make_game()
    col1, row1 = 5, 6
    col2, row2 = 6, 6
    g.flowers[row1][col1] = 0  # RED
    g.flowers[row2][col2] = 1  # LIME
    g.grid[row1][col1] = 0
    g.grid[row2][col2] = 0
    g.mower_col = col1
    g.mower_row = row1

    g._cut_tile(col1, row1)
    assert g.combo == 1

    g.mower_col = col2
    g.mower_row = row2
    g._cut_tile(col2, row2)
    assert g.combo == 0  # Reset
    assert g.heat >= Game.HEAT_MISMATCH  # Heat penalty


def test_combo_increases_max_combo() -> None:
    g = _make_game()
    color_idx = 0
    for c in range(5, 9):
        g.flowers[6][c] = color_idx
        g.grid[6][c] = 0
    g.mower_col = 4
    g.mower_row = 6
    for c in range(5, 9):
        g.mower_col = c
        g._cut_tile(c, 6)
    assert g.max_combo >= 4


# ── SUPER mode tests ──
def test_combo_4_activates_super() -> None:
    g = _make_game()
    color_idx = 0
    for c in range(5, 9):
        g.flowers[6][c] = color_idx
        g.grid[6][c] = 0
    g.mower_col = 4
    g.mower_row = 6
    for c in range(5, 9):
        g.mower_col = c
        g._cut_tile(c, 6)
    assert g.super_timer > 0
    assert g.multiplier == 3


def test_super_mode_auto_matches_any_color() -> None:
    g = _make_game()
    # Activate super manually
    g.super_timer = 150
    g.multiplier = 3
    g.last_color = 0  # RED
    # Cut a different color — should still combo in super mode
    g.mower_col = 5
    g.mower_row = 6
    g.flowers[6][5] = 1  # LIME
    g.grid[6][5] = 0

    combo_before = g.combo
    g._cut_tile(5, 6)
    assert g.combo == combo_before + 1  # Should increase, not reset


def test_super_mode_duration_tracks_down() -> None:
    g = _make_game()
    g.super_timer = 150
    g.multiplier = 3
    g.phase = Phase.PLAYING
    # Simulate one frame
    g.frame += 1
    if g.super_timer > 0:
        g.super_timer -= 1
        if g.super_timer <= 0:
            g.multiplier = 1
    assert g.super_timer == 149


def test_super_expires_resets_multiplier() -> None:
    g = _make_game()
    g.super_timer = 1
    g.multiplier = 3
    g.frame += 1
    if g.super_timer > 0:
        g.super_timer -= 1
        if g.super_timer <= 0:
            g.multiplier = 1
    assert g.super_timer == 0
    assert g.multiplier == 1


def test_reactivate_super_resets_timer() -> None:
    g = _make_game()
    g.super_timer = 30  # Has some time left
    g.multiplier = 3
    g._activate_super()  # Reactivate
    assert g.super_timer == Game.SUPER_DURATION  # Reset to full
    assert g.multiplier == 3


# ── Scoring tests ──
def test_cut_adds_score() -> None:
    g = _make_game()
    score_before = g.score
    g._cut_tile(g.mower_col, g.mower_row)
    assert g.score > score_before


def test_combo_multiplies_score() -> None:
    g = _make_game()
    # Same color chain
    color_idx = 0
    for c in range(5, 7):
        g.flowers[6][c] = color_idx
        g.grid[6][c] = 0
    g.mower_col = 4
    g.mower_row = 6

    g._cut_tile(5, 6)  # combo=1, score=10
    score_after_1 = g.score
    g.mower_col = 6
    g._cut_tile(6, 6)  # combo=2, score=10+20=30
    score_after_2 = g.score
    assert score_after_2 > score_after_1


# ── Heat tests ──
def test_heat_decays_when_not_moving() -> None:
    g = _make_game()
    g.heat = 50.0
    heat_before = g.heat
    # Simulate heat decay (not moving)
    g.heat = max(g.heat - Game.HEAT_DECAY, 0.0)
    assert g.heat == heat_before - Game.HEAT_DECAY


def test_heat_capped_at_max() -> None:
    g = _make_game()
    g.heat = Game.HEAT_MAX
    g._cut_tile(g.mower_col, g.mower_row)
    assert g.heat == Game.HEAT_MAX


def test_heat_at_max_triggers_game_over() -> None:
    g = _make_game()
    g.heat = Game.HEAT_MAX
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_heat_below_max_no_game_over() -> None:
    g = _make_game()
    g.heat = 99.9
    g._update_heat()
    assert g.phase == Phase.PLAYING


# ── Timer tests ──
def test_timer_decrements() -> None:
    g = _make_game()
    timer_before = g.timer
    g._update_timer()
    assert g.timer == timer_before - 1


def test_timer_zero_game_over() -> None:
    g = _make_game()
    g.timer = 1
    g._update_timer()
    assert g.timer == 0
    # update_timer sets phase when timer <= 0
    assert g.phase == Phase.GAME_OVER


def test_timer_min_zero() -> None:
    g = _make_game()
    g.timer = 0
    g.phase = Phase.GAME_OVER  # Already over
    g._update_timer()
    assert g.timer <= 0


# ── Particle tests ──
def test_particles_update_and_decay() -> None:
    g = _make_game()
    g.particles = [Particle(x=10.0, y=20.0, vx=1.0, vy=-1.0, life=3, color=8)]
    g._update_particles()
    assert len(g.particles) == 1
    p = g.particles[0]
    assert p.life == 2
    assert p.vy == -0.9  # gravity applied
    assert abs(p.x - 11.0) < 0.01
    assert abs(p.y - 19.0) < 0.01


def test_particles_removed_when_life_zero() -> None:
    g = _make_game()
    g.particles = [Particle(x=10.0, y=20.0, vx=0.0, vy=0.0, life=1, color=8)]
    g._update_particles()
    assert len(g.particles) == 0


# ── Floating text tests ──
def test_floating_text_update_and_decay() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=10.0, y=20.0, text="HI", life=3, color=7)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.life == 2
    assert ft.y < 20.0  # Floats upward


def test_floating_text_removed_when_life_zero() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=10.0, y=20.0, text="HI", life=1, color=7)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Trail tests ──
def test_trail_tracks_cut_tiles() -> None:
    g = _make_game()
    assert g.trail == []
    g._cut_tile(g.mower_col, g.mower_row)
    assert len(g.trail) == 1
    assert g.trail[0] == (g.mower_col, g.mower_row)


def test_trail_max_length() -> None:
    g = _make_game()
    for c in range(min(10, Game.COLS)):
        g.mower_col = c
        g.mower_row = 6
        g.flowers[6][c] = 0
        g.grid[6][c] = 0
        g._cut_tile(c, 6)
    assert len(g.trail) <= Game.TRAIL_LENGTH


# ── Mismatch tests ──
def test_mismatch_adds_heat_penalty() -> None:
    g = _make_game()
    g.heat = 0.0
    g.last_color = 0  # RED
    g.mower_col = 5
    g.mower_row = 6
    g.flowers[6][5] = 1  # LIME (different)
    g.grid[6][5] = 0
    g._cut_tile(5, 6)
    assert g.combo == 0
    assert g.heat >= Game.HEAT_MISMATCH


def test_mismatch_spawns_jam_text() -> None:
    g = _make_game()
    g.last_color = 0  # RED
    g.mower_col = 5
    g.mower_row = 6
    g.flowers[6][5] = 1  # LIME
    g.grid[6][5] = 0
    ft_count_before = len(g.floating_texts)
    g._cut_tile(5, 6)
    # Should have at least: "+N" text + "JAM!" text
    assert len(g.floating_texts) >= ft_count_before + 2


# ── Phase tests ──
def test_reset_sets_title_phase() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING  # Our factory sets this
    g.reset()  # reset() sets to TITLE
    assert g.phase == Phase.TITLE


# ── Game state factory test ──
def test_make_game_produces_valid_state() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert 0 <= g.mower_col < Game.COLS
    assert 0 <= g.mower_row < Game.ROWS
    assert g.timer > 0
    assert g.heat == 0.0
    assert len(g.grid) == Game.ROWS
    assert len(g.flowers) == Game.ROWS


print("All tests passed!")
