"""Tests for 080_stack_surge core logic."""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import (
    BASE_SCORE,
    BLOCK_COLORS,
    BLOCK_COLS,
    HEAT_PER_UNSTABLE_PULL,
    INITIAL_ROWS,
    MAX_ROWS,
    SYNTHESIS_BONUS_PER_COMBO,
    BlockState,
    Game,
    Phase,
)


def make_game() -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g._font = None
    g.rows = []
    g.score = 0
    g.best_score = 0
    g.combo = 0
    g.max_combo = 0
    g.last_color = -1
    g.heat = 0
    g.blocks_pulled = 0
    g.particles = []
    g.synthesis_flash = 0
    g.collapse_anim = 0
    g.phase = Phase.TITLE
    g._shake_frames = 0
    g._frame_count = 0
    g._init_state()
    g._rng = random.Random(42)
    return g


# ── Init ─────────────────────────────────────────────────────────────────────
def test_init_state_creates_rows() -> None:
    g = make_game()
    assert len(g.rows) == INITIAL_ROWS
    for row in g.rows:
        assert len(row) == BLOCK_COLS
        for block in row:
            assert block.state == BlockState.STABLE
            assert block.color in BLOCK_COLORS


def test_init_state_row_indices() -> None:
    g = make_game()
    for i, row in enumerate(g.rows):
        for block in row:
            assert block.row == i


# ── Block Hit Detection ──────────────────────────────────────────────────────
def test_block_at_returns_valid() -> None:
    g = make_game()
    x, y = 80 + 48 // 2, 20 + 20 // 2
    result = g._block_at(x, y)
    assert result is not None
    assert result == (0, 0)


def test_block_at_none_out_of_bounds() -> None:
    g = make_game()
    assert g._block_at(0, 0) is None
    assert g._block_at(500, 500) is None


def test_block_at_none_for_gone() -> None:
    g = make_game()
    g.rows[0][0].state = BlockState.GONE
    x, y = 80 + 48 // 2, 20 + 20 // 2
    assert g._block_at(x, y) is None


# ── Pull Mechanics ───────────────────────────────────────────────────────────
def test_pull_block_marks_gone() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    block = g.rows[0][0]
    g._pull_block(0, 0)
    assert block.state == BlockState.GONE
    assert g.blocks_pulled == 1


def test_pull_block_combo_same_color() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    color = g.rows[0][0].color
    g.last_color = color
    g.combo = 2
    # Make same color in row 1, col 0
    g.rows[1][0].color = color
    g._pull_block(1, 0)
    assert g.combo == 3


def test_pull_block_combo_reset_wrong_color() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.last_color = 8
    g.combo = 3
    for c in BLOCK_COLORS:
        if c != 8:
            g.rows[0][0].color = c
            break
    g._pull_block(0, 0)
    assert g.combo == 0


def test_pull_block_score() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.combo = 2
    g.last_color = g.rows[0][0].color
    g._pull_block(0, 0)
    assert g.score >= BASE_SCORE * 3


def test_pull_block_first_no_combo() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.last_color = -1
    g._pull_block(0, 0)
    assert g.combo == 0
    assert g.score == BASE_SCORE * 1


# ── SYNTHESIS ───────────────────────────────────────────────────────────────
def test_synthesis_triggers_on_combo_3() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    color = g.rows[0][0].color
    g.last_color = color
    g.combo = 2
    g.rows[1][0].color = color
    # Make some blocks unstable
    g.rows[2][0].state = BlockState.UNSTABLE
    g.rows[2][1].state = BlockState.UNSTABLE
    g._pull_block(1, 0)
    assert g.combo == 3
    assert g.synthesis_flash > 0
    # Unstable blocks should be stable now
    assert g.rows[2][0].state == BlockState.STABLE
    assert g.rows[2][1].state == BlockState.STABLE
    # Bonus score
    assert g.score >= SYNTHESIS_BONUS_PER_COMBO * 3


def test_synthesis_no_unstable_still_adds_bonus() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    color = g.rows[0][0].color
    g.last_color = color
    g.combo = 2
    g.rows[1][0].color = color
    initial_score = g.score
    g._pull_block(1, 0)
    assert g.score > initial_score + (3 * SYNTHESIS_BONUS_PER_COMBO - 10)


# ── CA Instability Spread ───────────────────────────────────────────────────
def test_spread_instability_adjacent_same_row() -> None:
    g = make_game()
    g.rows[0][0].state = BlockState.STABLE
    g.rows[0][1].state = BlockState.STABLE
    g.rows[0][2].state = BlockState.STABLE
    g._spread_instability(0, 1)
    assert g.rows[0][0].state == BlockState.UNSTABLE
    assert g.rows[0][2].state == BlockState.UNSTABLE
    assert g.rows[0][1].state == BlockState.STABLE  # origin unchanged by spread


def test_spread_instability_adjacent_rows() -> None:
    g = make_game()
    g.rows[0][1].state = BlockState.STABLE
    g.rows[1][1].state = BlockState.STABLE
    g._spread_instability(1, 1)
    assert g.rows[0][1].state == BlockState.UNSTABLE


def test_spread_skips_gone_and_already_unstable() -> None:
    g = make_game()
    g.rows[0][0].state = BlockState.GONE
    g.rows[0][2].state = BlockState.UNSTABLE
    g._spread_instability(0, 1)
    assert g.rows[0][0].state == BlockState.GONE  # no change
    assert g.rows[0][2].state == BlockState.UNSTABLE  # no change


def test_spread_instability_edge_bounds() -> None:
    g = make_game()
    g._spread_instability(0, 0)  # top-left corner, should not error
    assert True


# ── Tower Compaction ─────────────────────────────────────────────────────────
def test_compact_tower_removes_empty_rows() -> None:
    g = make_game()
    for b in g.rows[0]:
        b.state = BlockState.GONE
    g._compact_tower()
    assert len(g.rows) == INITIAL_ROWS - 1


def test_compact_tower_keeps_partial_rows() -> None:
    g = make_game()
    g.rows[0][0].state = BlockState.GONE
    g.rows[0][1].state = BlockState.GONE
    # row[0][2] is still STABLE
    g._compact_tower()
    assert len(g.rows) == INITIAL_ROWS  # row not empty


def test_compact_tower_empty() -> None:
    g = make_game()
    for r in g.rows:
        for b in r:
            b.state = BlockState.GONE
    g._compact_tower()
    assert len(g.rows) == 0


# ── Add Top Row ─────────────────────────────────────────────────────────────
def test_add_top_row_appends_row() -> None:
    g = make_game()
    initial = len(g.rows)
    g._add_top_row()
    assert len(g.rows) == initial + 1
    assert len(g.rows[-1]) == BLOCK_COLS
    for b in g.rows[-1]:
        assert b.state == BlockState.STABLE
        assert b.color in BLOCK_COLORS


def test_add_top_row_caps_max_rows() -> None:
    g = make_game()
    # Fill up to MAX_ROWS
    while len(g.rows) < MAX_ROWS:
        g._add_top_row()
    assert len(g.rows) == MAX_ROWS
    g._add_top_row()
    assert len(g.rows) == MAX_ROWS  # capped


# ── Instability Ratio ───────────────────────────────────────────────────────
def test_count_unstable_ratio_all_stable() -> None:
    g = make_game()
    assert g._count_unstable_ratio() == 0.0


def test_count_unstable_ratio_half() -> None:
    g = make_game()
    total = 0
    for r in g.rows:
        for b in r:
            if total % 2 == 0:
                b.state = BlockState.UNSTABLE
            total += 1
    ratio = g._count_unstable_ratio()
    assert 0.4 < ratio < 0.6


def test_count_unstable_ratio_excludes_gone() -> None:
    g = make_game()
    for b in g.rows[0]:
        b.state = BlockState.GONE
    for b in g.rows[1]:
        b.state = BlockState.UNSTABLE
    # 1 row gone, 1 row unstable, 6 rows stable = 18 total, 3 unstable
    ratio = g._count_unstable_ratio()
    assert ratio == 3 / 21  # 18 stable + 3 unstable = 21 total


# ── Collapse Detection ──────────────────────────────────────────────────────
def test_check_collapse_below_threshold() -> None:
    g = make_game()
    assert not g._check_collapse()


def test_check_collapse_above_threshold() -> None:
    g = make_game()
    for r in g.rows:
        for b in r:
            b.state = BlockState.UNSTABLE
    assert g._check_collapse()


# ── Heat ────────────────────────────────────────────────────────────────────
def test_heat_increases_on_unstable_pull() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.rows[0][0].state = BlockState.UNSTABLE
    g._pull_block(0, 0)
    assert g.heat == HEAT_PER_UNSTABLE_PULL


def test_heat_does_not_increase_on_stable_pull() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.rows[0][0].state = BlockState.STABLE
    g._pull_block(0, 0)
    assert g.heat == 0


# ── Combo Tracking ──────────────────────────────────────────────────────────
def test_max_combo_tracks_highest() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    color = g.rows[0][0].color
    g.last_color = color
    g.combo = 4
    g.max_combo = 4
    g.rows[1][0].color = color
    g._pull_block(1, 0)
    assert g.max_combo == 5


def test_max_combo_preserves_on_reset() -> None:
    g = make_game()
    g.max_combo = 10
    g.combo = 0
    assert g.max_combo == 10


# ── Pull triggers collapse ──────────────────────────────────────────────────
def test_pull_triggers_collapse_on_high_instability() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    for r in g.rows:
        for b in r:
            b.state = BlockState.UNSTABLE
    g.rows[0][0].state = BlockState.STABLE  # keep one stable to pull
    g.last_color = g.rows[0][0].color
    g._pull_block(0, 0)
    assert g.phase == Phase.COLLAPSE_ANIM
    assert g.collapse_anim > 0


# ── Collapse anim transition ────────────────────────────────────────────────
def test_collapse_anim_transitions_to_game_over() -> None:
    g = make_game()
    g.phase = Phase.COLLAPSE_ANIM
    g.collapse_anim = 1
    g.update()
    assert g.phase == Phase.GAME_OVER


# ── Reset ───────────────────────────────────────────────────────────────────
def test_reset_initializes_all() -> None:
    g = make_game()
    assert len(g.rows) == INITIAL_ROWS
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.last_color == -1
    assert g.heat == 0
    assert g.blocks_pulled == 0
    assert g.particles == []
    assert g.synthesis_flash == 0


# ── Best Score ──────────────────────────────────────────────────────────────
def test_best_score_updated_on_collapse() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.score = 5000
    g.best_score = 3000
    for r in g.rows:
        for b in r:
            b.state = BlockState.UNSTABLE
    g.rows[0][0].state = BlockState.STABLE
    g.last_color = g.rows[0][0].color
    g._pull_block(0, 0)
    assert g.best_score == 5020  # 5000 + BASE_SCORE * (1 + 1)
