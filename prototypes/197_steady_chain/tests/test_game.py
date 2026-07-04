"""Tests for STEADY CHAIN pure-logic methods."""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import (  # type: ignore[import-untyped]
    CHECKPOINT_COLORS,
    GAME_TIME,
    NUM_CHECKPOINTS,
    WRONG_COLOR_HEAT,
    Checkpoint,
    Game,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.combo = 0
    g.max_combo = 0
    g.last_color = None
    g.score = 0
    g.heat = 0.0
    g.timer = GAME_TIME
    g.super_timer = 0
    g.super_cooldown = 0
    g.shake_x = 0
    g.shake_y = 0
    g.shake_frames = 0
    g.shake_amplitude = 0
    g.particles = []
    g.floats = []
    g.checkpoints = []
    g.phase = None  # type: ignore[assignment]
    g._rng = random.Random(42)
    g._build_path()
    return g


class TestPathCollision:
    def test_on_path_center(self) -> None:
        g = _make_game()
        assert g._is_on_path(150, 30) is True

    def test_off_path_far(self) -> None:
        g = _make_game()
        assert g._is_on_path(0, 0) is False

    def test_on_path_corner(self) -> None:
        g = _make_game()
        assert g._is_on_path(200, 35) is True

    def test_off_path_between_segments(self) -> None:
        g = _make_game()
        assert g._is_on_path(220, 35) is False


class TestCheckpointCollision:
    def test_hit_on_checkpoint(self) -> None:
        g = _make_game()
        cp = Checkpoint(x=150, y=30, color=CHECKPOINT_COLORS[0])
        g.checkpoints = [cp]
        result = g._check_checkpoint_collision(150.0, 30.0)
        assert result is cp

    def test_miss_far_from_checkpoint(self) -> None:
        g = _make_game()
        cp = Checkpoint(x=150, y=30, color=CHECKPOINT_COLORS[0])
        g.checkpoints = [cp]
        result = g._check_checkpoint_collision(150.0, 100.0)
        assert result is None

    def test_skip_collected_checkpoint(self) -> None:
        g = _make_game()
        cp = Checkpoint(x=150, y=30, color=CHECKPOINT_COLORS[0], collected=True)
        g.checkpoints = [cp]
        result = g._check_checkpoint_collision(150.0, 30.0)
        assert result is None


class TestProcessCheckpoint:
    def test_same_color_increments_combo(self) -> None:
        g = _make_game()
        g.last_color = CHECKPOINT_COLORS[0]
        g.combo = 2
        cp = Checkpoint(x=0, y=0, color=CHECKPOINT_COLORS[0])
        score_add, heat_add = g._process_checkpoint(cp)
        assert g.combo == 3
        assert heat_add == 0
        assert score_add > 10

    def test_different_color_resets_combo(self) -> None:
        g = _make_game()
        g.last_color = CHECKPOINT_COLORS[0]
        g.combo = 3
        cp = Checkpoint(x=0, y=0, color=CHECKPOINT_COLORS[1])
        score_add, heat_add = g._process_checkpoint(cp)
        assert g.combo == 0
        assert heat_add == WRONG_COLOR_HEAT

    def test_super_mode_all_colors_match(self) -> None:
        g = _make_game()
        g.last_color = CHECKPOINT_COLORS[0]
        g.combo = 5
        g.super_timer = 100
        cp = Checkpoint(x=0, y=0, color=CHECKPOINT_COLORS[1])
        score_add, heat_add = g._process_checkpoint(cp)
        assert g.combo == 6
        assert heat_add == 0

    def test_super_multiplier(self) -> None:
        g = _make_game()
        g.last_color = CHECKPOINT_COLORS[0]
        g.combo = 4
        g.super_timer = 100
        cp = Checkpoint(x=0, y=0, color=CHECKPOINT_COLORS[0])
        score_add, _ = g._process_checkpoint(cp)
        expected = int(10 * (1 + 5 * 0.5) * 3)
        assert score_add == expected


class TestHeat:
    def test_heat_increases(self) -> None:
        g = _make_game()
        game_over = g._update_heat(30)
        assert g.heat == 30
        assert game_over is False

    def test_heat_game_over_at_max(self) -> None:
        g = _make_game()
        game_over = g._update_heat(100)
        assert g.heat == 100
        assert game_over is True

    def test_heat_above_max_clamped(self) -> None:
        g = _make_game()
        g._update_heat(150)
        assert g.heat == 100

    def test_heat_stays_non_negative(self) -> None:
        g = _make_game()
        g._update_heat(-50)
        assert g.heat == 0


class TestComputeScore:
    def test_basic_score(self) -> None:
        g = _make_game()
        s = g._compute_score(10, 0, False)
        assert s == 10

    def test_combo_score(self) -> None:
        g = _make_game()
        s = g._compute_score(10, 4, False)
        assert s == int(10 * (1 + 4 * 0.5))

    def test_super_multiplier(self) -> None:
        g = _make_game()
        s = g._compute_score(10, 2, True)
        assert s == int(10 * (1 + 2 * 0.5) * 3)

    def test_super_combo_combined(self) -> None:
        g = _make_game()
        s = g._compute_score(10, 8, True)
        assert s == int(10 * (1 + 8 * 0.5) * 3)


class TestCanActivateSuper:
    def test_combo_4_no_cooldown(self) -> None:
        g = _make_game()
        g.combo = 4
        assert g._can_activate_super() is True

    def test_combo_3_not_enough(self) -> None:
        g = _make_game()
        g.combo = 3
        assert g._can_activate_super() is False

    def test_combo_4_with_cooldown(self) -> None:
        g = _make_game()
        g.combo = 4
        g.super_cooldown = 10
        assert g._can_activate_super() is False

    def test_combo_10_no_cooldown(self) -> None:
        g = _make_game()
        g.combo = 10
        assert g._can_activate_super() is True


class TestBuildPath:
    def test_path_segments_created(self) -> None:
        g = _make_game()
        assert len(g.path_segments) > 0

    def test_path_contains_start_position(self) -> None:
        g = _make_game()
        assert g._is_on_path(g.cursor_x, g.cursor_y) is True


class TestSpawnCheckpoints:
    def test_checkpoints_spawned(self) -> None:
        g = _make_game()
        g._spawn_checkpoints()
        assert len(g.checkpoints) == NUM_CHECKPOINTS

    def test_all_checkpoints_on_path(self) -> None:
        g = _make_game()
        g._spawn_checkpoints()
        for cp in g.checkpoints:
            assert g._is_on_path(cp.x, cp.y) is True, (
                f"Checkpoint at ({cp.x}, {cp.y}) not on path"
            )

    def test_checkpoints_deterministic_with_seed(self) -> None:
        g1 = _make_game()
        g1._rng = random.Random(42)
        g1._spawn_checkpoints()

        g2 = _make_game()
        g2._rng = random.Random(42)
        g2._spawn_checkpoints()

        for c1, c2 in zip(g1.checkpoints, g2.checkpoints):
            assert c1.x == c2.x
            assert c1.y == c2.y
            assert c1.color == c2.color


class TestReset:
    def test_reset_zeroes_state(self) -> None:
        g = _make_game()
        g.combo = 5
        g.score = 1000
        g.heat = 50
        g.timer = 100
        g.super_timer = 50

        g.reset()

        assert g.combo == 0
        assert g.score == 0
        assert g.heat == 0.0
        assert g.timer == GAME_TIME
        assert g.super_timer == 0
        assert g.super_cooldown == 0
        assert g.last_color is None
        assert g.max_combo == 0


class TestSuperAutoPull:
    def test_pull_toward_checkpoint(self) -> None:
        g = _make_game()
        g.cursor_x = 160.0
        g.cursor_y = 120.0
        g.checkpoints = [
            Checkpoint(x=160, y=80, color=8),
            Checkpoint(x=160, y=160, color=3),
        ]
        g.checkpoints[1].collected = True
        dx, dy = g._super_auto_pull()
        assert dy < 0

    def test_pull_toward_uncollected_only(self) -> None:
        g = _make_game()
        g.cursor_x = 100.0
        g.cursor_y = 100.0
        g.checkpoints = [
            Checkpoint(x=200, y=100, color=8),
        ]
        dx, dy = g._super_auto_pull()
        assert dx > 0
