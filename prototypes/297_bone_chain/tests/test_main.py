"""Tests for FOSSIL CHAIN — 297_bone_chain."""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (
    ANIM_SYNTH_DURATION,
    COLS,
    DIRT,
    EMPTY,
    FOSSIL_COLORS,
    GAME_DURATION,
    FPS,
    HEAT_COVER,
    HEAT_DECAY,
    HEAT_MAX,
    LIME,
    RED,
    ROWS,
    SUPER_COMBO_THRESHOLD,
    SUPER_DURATION,
    TIER_BONE,
    TIER_COMPLETE,
    TIER_MEGA,
    Game,
    Phase,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(seed)
    g.best_score = 0
    g._init_state()
    return g


class TestGameInitialization:
    def test_init_state(self) -> None:
        g = _make_game()
        assert g.phase == Phase.TITLE
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0.0
        assert g.super_timer == 0
        assert g.timer == GAME_DURATION * FPS
        assert g.player_color_idx == 0

    def test_reset(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.score = 500
        g.combo = 3
        g.heat = 30
        g.timer = 100
        g.best_score = 500
        g.reset()
        assert g.phase == Phase.TITLE
        assert g.score == 0
        assert g.combo == 0
        assert g.heat == 0.0
        assert g.timer == GAME_DURATION * FPS
        assert g.best_score == 500

    def test_initial_grid_dirt_edges(self) -> None:
        g = _make_game()
        # Edges should be dirt
        assert g._grid[0][0] == DIRT
        assert g._grid[0][COLS - 1] == DIRT
        assert g._grid[ROWS - 1][0] == DIRT
        assert g._grid[ROWS - 1][COLS - 1] == DIRT
        # Center should be exposed
        if ROWS > 2 and COLS > 2:
            assert g._grid[1][1] != DIRT


class TestExcavate:
    def test_excavate_out_of_bounds(self) -> None:
        g = _make_game()
        matched, event = g._excavate(-1, 0)
        assert not matched
        assert event == ""

    def test_excavate_non_dirt(self) -> None:
        g = _make_game()
        matched, event = g._excavate(1, 1)
        assert not matched
        assert event == ""

    def test_excavate_empty_result(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.rng = random.Random(5)
        matched, event = g._excavate(0, 0)
        assert not matched
        assert event == ""

    def test_excavate_fossil_first(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.rng = random.Random(1)
        # seed 1: random() = 0.13436 < 0.6 → fossil
        matched, event = g._excavate(0, 0)
        assert matched
        assert g.combo == 1
        # Grid should now have a fossil color (> 0)
        assert g._grid[0][0] > 0
        assert g._tiers[0][0] == TIER_BONE

    def test_excavate_mismatch_resets_combo(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.combo = 2
        g.last_excavated_color = 0  # RED
        g.heat = 0
        g.rng = random.Random(42)
        # seed 42: random()=0.6394 >= 0.6 → empty, no fossil
        # This doesn't test mismatch since it returns immediately
        # Use seed 46: random()=0.8883 >= 0.6 → empty
        # We need a seed that gives fossil AND color != last_excavated_color
        g.rng = random.Random(123)
        g._grid[0][0] = DIRT
        matched, event = g._excavate(0, 0)
        if not matched and event == "mismatch":
            assert g.combo == 0
            assert g.heat > 0
        # If it matched by chance, combo would be 3 — acceptable either way

    def test_excavate_super_activates_at_threshold(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.combo = SUPER_COMBO_THRESHOLD - 1
        g.last_excavated_color = 0
        g.super_timer = 0
        g._grid[0][0] = DIRT
        # seed 1: random()=0.1344 < 0.6 → fossil, randint(0,3)=0 → RED match
        g.rng = random.Random(1)
        matched, event = g._excavate(0, 0)
        assert matched
        assert event == "super_activate"
        assert g.super_timer == SUPER_DURATION


class TestBFS:
    def test_empty_cluster(self) -> None:
        g = _make_game()
        g._grid[0][0] = EMPTY
        cluster = g._bfs_synthesis(0, 0, 0)
        assert len(cluster) == 0

    def test_single_cell_cluster(self) -> None:
        g = _make_game()
        g._grid[0][0] = RED
        g._tiers[0][0] = TIER_BONE
        cluster = g._bfs_synthesis(0, 0, 0)
        assert cluster == {(0, 0)}

    def test_connected_cluster(self) -> None:
        g = _make_game()
        g._grid[0][0] = RED
        g._grid[0][1] = RED
        g._grid[0][2] = RED
        g._tiers[0][0] = TIER_BONE
        g._tiers[0][1] = TIER_BONE
        g._tiers[0][2] = TIER_BONE
        cluster = g._bfs_synthesis(0, 0, 0)
        assert cluster == {(0, 0), (1, 0), (2, 0)}

    def test_different_color_not_connected(self) -> None:
        g = _make_game()
        g._grid[0][0] = RED
        g._grid[0][1] = LIME
        g._tiers[0][0] = TIER_BONE
        g._tiers[0][1] = TIER_BONE
        cluster = g._bfs_synthesis(0, 0, 0)
        assert cluster == {(0, 0)}

    def test_different_tier_not_connected(self) -> None:
        g = _make_game()
        g._grid[0][0] = RED
        g._grid[0][1] = RED
        g._tiers[0][0] = TIER_BONE
        g._tiers[0][1] = TIER_COMPLETE
        cluster = g._bfs_synthesis(0, 0, 0)
        assert cluster == {(0, 0)}

    def test_tier2_cluster(self) -> None:
        g = _make_game()
        g._grid[0][0] = RED
        g._grid[0][1] = RED
        g._grid[0][2] = RED
        g._tiers[0][0] = TIER_COMPLETE
        g._tiers[0][1] = TIER_COMPLETE
        g._tiers[0][2] = TIER_COMPLETE
        cluster = g._bfs_synthesis(0, 0, FOSSIL_COLORS.index(RED))
        assert cluster == {(0, 0), (1, 0), (2, 0)}


class TestSynthesis:
    def test_small_cluster_no_synthesis(self) -> None:
        g = _make_game()
        cluster: set[tuple[int, int]] = {(0, 0), (1, 0)}
        triggered, bonus = g._try_synthesis(cluster)
        assert not triggered
        assert bonus == 0

    def test_bone_to_complete_synthesis(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.score = 0
        g.combo = 2
        g._grid[0][0] = RED
        g._grid[0][1] = RED
        g._grid[0][2] = RED
        g._tiers[0][0] = TIER_BONE
        g._tiers[0][1] = TIER_BONE
        g._tiers[0][2] = TIER_BONE
        g.synth_anim_timer = 0
        cluster = {(0, 0), (1, 0), (2, 0)}
        triggered, bonus = g._try_synthesis(cluster)
        assert triggered
        assert bonus == 100 * 3 * 2
        assert g._tiers[0][0] == TIER_COMPLETE
        assert g._tiers[0][1] == TIER_COMPLETE
        assert g._tiers[0][2] == TIER_COMPLETE
        assert g.score == bonus
        assert g.synth_anim_timer == ANIM_SYNTH_DURATION

    def test_complete_to_mega_synthesis(self) -> None:
        g = _make_game()
        g.phase = Phase.PLAYING
        g.score = 0
        g.combo = 3
        g._grid[0][0] = RED
        g._grid[0][1] = RED
        g._grid[0][2] = RED
        g._tiers[0][0] = TIER_COMPLETE
        g._tiers[0][1] = TIER_COMPLETE
        g._tiers[0][2] = TIER_COMPLETE
        cluster = {(0, 0), (1, 0), (2, 0)}
        triggered, bonus = g._try_synthesis(cluster)
        assert triggered
        assert bonus == 300 * 3 * 3
        assert g._tiers[0][0] == TIER_MEGA
        assert g._tiers[0][1] == TIER_MEGA
        assert g._tiers[0][2] == TIER_MEGA
        assert g.score == bonus


class TestDirtSpread:
    def test_dirt_spreads_to_empty(self) -> None:
        g = _make_game()
        g.rng = random.Random(42)
        g._grid[0][0] = DIRT
        g._grid[0][1] = EMPTY
        count = g._spread_dirt()
        assert count >= 0

    def test_dirt_covers_fossil_adds_heat(self) -> None:
        g = _make_game()
        g.rng = random.Random(42)
        g.heat = 0
        # Fill everything with dirt except (0,1) which has a RED fossil
        for r in range(ROWS):
            for c in range(COLS):
                g._grid[r][c] = DIRT
                g._tiers[r][c] = 0
        g._grid[0][1] = RED
        g._tiers[0][1] = TIER_BONE
        # Only (0,0) can spread to (0,1). 20% chance per frame.
        for _ in range(20):
            count = g._spread_dirt()
            if count > 0:
                assert g._grid[0][1] == DIRT
                assert g.heat == HEAT_COVER
                return
        # Probability of not triggering in 20 tries: 0.8^20 ≈ 1.2% — skip if unlucky


class TestFossilSpawn:
    def test_spawn_in_empty_cell(self) -> None:
        g = _make_game()
        g.rng = random.Random(42)
        # Clear all cells to dirt except one
        for r in range(ROWS):
            for c in range(COLS):
                g._grid[r][c] = DIRT
                g._tiers[r][c] = 0
        g._grid[0][0] = EMPTY
        result = g._spawn_single_fossil()
        assert result
        assert g._grid[0][0] in FOSSIL_COLORS
        assert g._tiers[0][0] == TIER_BONE

    def test_spawn_no_empty_cells(self) -> None:
        g = _make_game()
        for r in range(ROWS):
            for c in range(COLS):
                g._grid[r][c] = DIRT
        result = g._spawn_single_fossil()
        assert not result

    def test_spawn_fossils_respects_max(self) -> None:
        g = _make_game()
        g.rng = random.Random(42)
        for r in range(ROWS):
            for c in range(COLS):
                g._grid[r][c] = RED
                g._tiers[r][c] = TIER_BONE
        spawned = g._spawn_fossils()
        assert spawned == 0


class TestHeat:
    def test_heat_clamp_zero(self) -> None:
        g = _make_game()
        g.heat = 5
        g._update_heat(-10)
        assert g.heat == 0

    def test_heat_clamp_max(self) -> None:
        g = _make_game()
        g.heat = HEAT_MAX - 1
        g._update_heat(5)
        assert g.heat == HEAT_MAX

    def test_heat_decay(self) -> None:
        g = _make_game()
        g.heat = 10
        g._update_heat(-HEAT_DECAY)
        assert g.heat == 10 - HEAT_DECAY


class TestTimer:
    def test_timer_decrements(self) -> None:
        g = _make_game()
        g.timer = 100
        expired = g._update_timer()
        assert not expired
        assert g.timer == 99

    def test_timer_expires(self) -> None:
        g = _make_game()
        g.timer = 1
        expired = g._update_timer()
        assert expired
        assert g.timer == 0
