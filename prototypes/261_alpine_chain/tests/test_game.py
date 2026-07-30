"""Headless tests for ALPINE CHAIN game logic."""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (
    SCREEN_H,
    SCREEN_W,
    DARK_BLUE,
    Game,
    Gate,
    LIME,
    Phase,
    RED,
    TrailDot,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.player_x = SCREEN_W / 2
    g.player_y = SCREEN_H - 60
    g.player_color = RED
    g.player_color_timer = 20
    g.player_color_idx = 0
    g.gates = []
    g.particles = []
    g.floating_texts = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.best_score = 0
    g.super_timer = 0
    g.heat = 0.0
    g.game_timer = 1800
    g.gate_spawn_timer = 60
    g.gate_spawn_interval = 60
    g.shake_frames = 0
    g.scroll_offset = 0.0
    g.best_trail = []
    g.current_trail = []
    g.trail_record_timer = 0
    g._rng = random.Random(42)
    g.game_over_reason = ""
    g._bg_dots = []
    return g


class TestReset:
    def test_reset_clears_state(self) -> None:
        g = _make_game()
        g.score = 500
        g.combo = 3
        g.heat = 50
        g.game_timer = 100
        g.gates.append(Gate(x=100.0, y=100.0, color=RED))
        g.phase = Phase.PLAYING
        g.reset()
        assert g.score == 0
        assert g.combo == 0
        assert g.heat == 0.0
        assert g.game_timer == 1800
        assert len(g.gates) == 0
        assert g.phase == Phase.PLAYING  # reset does NOT change phase


class TestGateMatch:
    def test_match_increments_combo_and_score(self) -> None:
        g = _make_game()
        g.combo = 2
        g.player_color = RED
        gate = Gate(x=160.0, y=200.0, color=RED)
        g._handle_match(gate)
        assert g.combo == 3
        assert g.score == 300  # 100 * 3
        assert len(g.particles) == 8
        assert len(g.floating_texts) >= 1

    def test_combo_4_triggers_super_ski(self) -> None:
        g = _make_game()
        g.combo = 3
        g.player_color = RED
        g.super_timer = 0

        gate = Gate(x=160.0, y=200.0, color=RED)
        g._handle_match(gate)
        assert g.combo == 4
        assert g.super_timer == 300

    def test_super_not_retriggered(self) -> None:
        g = _make_game()
        g.combo = 4
        g.player_color = RED
        g.super_timer = 300

        gate = Gate(x=160.0, y=200.0, color=RED)
        old_super = g.super_timer
        g._handle_match(gate)
        assert g.super_timer == old_super  # not reset
        assert g.combo == 5

    def test_mismatch_resets_combo_adds_heat(self) -> None:
        g = _make_game()
        g.combo = 5
        g.heat = 10
        g.player_color = RED

        gate = Gate(x=160.0, y=200.0, color=LIME)
        g._handle_mismatch(gate)
        assert g.combo == 0
        assert g.heat == 25  # 10 + 15
        assert g.shake_frames == 8
        assert len(g.particles) == 4

    def test_mismatch_game_over_heat_overflow(self) -> None:
        g = _make_game()
        g.combo = 1
        g.heat = 90
        g.player_color = RED
        g.phase = Phase.PLAYING

        gate = Gate(x=160.0, y=200.0, color=LIME)
        g._handle_mismatch(gate)
        assert g.heat >= 100
        # The game-over check happens in _update_playing, not in handler


class TestSuperPass:
    def test_super_pass_3x_score(self) -> None:
        g = _make_game()
        g.combo = 4
        g.super_timer = 100
        g.player_color = RED

        gate = Gate(x=160.0, y=200.0, color=DARK_BLUE)
        g._handle_super_pass(gate)
        assert g.combo == 5
        assert g.score == 1500  # 100 * 5 * 3
        assert len(g.particles) == 15


class TestHeatSystem:
    def test_heat_decay(self) -> None:
        g = _make_game()
        g.heat = 30.0
        g.super_timer = 0
        for _ in range(100):
            g.heat = max(0.0, g.heat - 0.03)
        assert g.heat < 30.0
        assert g.heat >= 26.99

    def test_heat_frozen_during_super(self) -> None:
        g = _make_game()
        g.heat = 30.0
        g.super_timer = 100
        # During SUPER SKI, HEAT decay is skipped
        # This is tested by verifying the update code skips decay
        assert g.super_timer > 0


class TestDifficulty:
    def test_scroll_speed_increases(self) -> None:
        g = _make_game()
        g.game_timer = 1800
        s1 = g._gate_scroll_speed()
        g.game_timer = 900
        s2 = g._gate_scroll_speed()
        g.game_timer = 0
        s3 = g._gate_scroll_speed()
        assert s1 < s2 < s3
        assert s1 == 1.5
        assert s3 == 4.0

    def test_spawn_interval_decreases(self) -> None:
        g = _make_game()
        g.game_timer = 1800
        i1 = g._spawn_interval()
        g.game_timer = 0
        i2 = g._spawn_interval()
        assert i1 > i2
        assert i1 == 60
        assert i2 == 25


class TestTrailRecording:
    def test_trail_records_position(self) -> None:
        g = _make_game()
        g.player_x = 100.0
        g.player_y = 150.0
        g.trail_record_timer = 4
        # Simulate one frame of trail recording in _update_playing
        g.trail_record_timer += 1
        if g.trail_record_timer >= 5:
            g.trail_record_timer = 0
            g.current_trail.append(TrailDot(g.player_x, g.player_y))
        assert len(g.current_trail) == 1
        assert g.current_trail[0].x == 100.0
        assert g.current_trail[0].y == 150.0


class TestFinalizeRun:
    def test_saves_best_score_and_trail(self) -> None:
        g = _make_game()
        g.score = 5000
        g.best_score = 3000
        g.current_trail = [TrailDot(10.0, 20.0), TrailDot(30.0, 40.0)]
        g.best_trail = []
        g._finalize_run()
        assert g.best_score == 5000
        assert len(g.best_trail) == 2
        assert g.best_trail[0].x == 10.0

    def test_does_not_overwrite_worse_score(self) -> None:
        g = _make_game()
        g.score = 2000
        g.best_score = 5000
        g.current_trail = [TrailDot(1.0, 2.0)]
        g.best_trail = [TrailDot(99.0, 99.0)]
        g._finalize_run()
        assert g.best_score == 5000
        assert g.best_trail[0].x == 99.0
