from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (  # noqa: E402
    SCREEN_W,
    SCREEN_H,
    FPS,
    Game,
    Particle,
    Phase,
    FloatingText,
)

GAME_TIME = Game.GAME_TIME
GEAR_COLORS = Game.GEAR_COLORS
RED = 8
LIME = 11


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.reset()
    return g


class TestImports:
    def test_game_class_imports(self) -> None:
        assert Game is not None
        assert Phase.TITLE is not None
        assert Phase.PLAYING is not None
        assert Phase.GAME_OVER is not None

    def test_particle_field_order(self) -> None:
        p = Particle(1.0, 2.0, 3.0, 4.0, 5, 6)
        assert (p.x, p.y, p.vx, p.vy, p.color, p.life) == (1.0, 2.0, 3.0, 4.0, 5, 6)

    def test_floating_text_field_order(self) -> None:
        t = FloatingText("hi", 1.0, 2.0, 5, 6)
        assert (t.text, t.x, t.y, t.color, t.life) == ("hi", 1.0, 2.0, 5, 6)

    def test_class_constants(self) -> None:
        assert SCREEN_W == 320
        assert SCREEN_H == 240
        assert FPS == 60
        assert Game.QUEUE_LEN == 6
        assert Game.GEAR_COLORS == [8, 11, 5, 10]
        assert Game.CYCLE_INTERVAL_START == 20
        assert Game.CYCLE_INTERVAL_END == 12
        assert Game.HEAT_MISMATCH == 15
        assert Game.HEAT_DECAY == 0.02
        assert Game.HEAT_CAP == 100
        assert Game.SUPER_THRESHOLD == 4
        assert Game.SUPER_DURATION == 300
        assert Game.REWIND_COST == 120
        assert Game.GAME_TIME == 3600


class TestReset:
    def test_reset_initializes_state(self) -> None:
        g = _make_game()
        assert g.phase == Phase.TITLE
        assert g.tool_color == 0
        assert g.cycle_timer == Game.CYCLE_INTERVAL_START
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.score == 0
        assert g.best_score == 0
        assert g.heat == 0.0
        assert g.timer == GAME_TIME
        assert g.super_timer == 0
        assert g.elapsed == 0
        assert g.shake == 0
        assert g.last_color is None

    def test_reset_queue_length_and_range(self) -> None:
        g = _make_game()
        assert len(g.queue) == Game.QUEUE_LEN
        assert all(0 <= c <= 3 for c in g.queue)

    def test_reset_clears_particles_and_texts(self) -> None:
        g = _make_game()
        assert g.particles == []
        assert g.floating_texts == []

    def test_reset_is_deterministic(self) -> None:
        g1 = _make_game()
        g2 = _make_game()
        assert g1.queue == g2.queue


class TestRepair:
    def test_match_increments_combo_and_score(self) -> None:
        g = _make_game()
        g.tool_color = g.queue[0]
        assert g._repair() is True
        assert g.combo == 1
        assert g.score == 10
        assert g.last_color is not None
        assert g.heat == 0.0

    def test_match_sets_last_color(self) -> None:
        g = _make_game()
        g.tool_color = g.queue[0]
        color = g.queue[0]
        g._repair()
        assert g.last_color == color

    def test_mismatch_adds_heat_and_resets_combo(self) -> None:
        g = _make_game()
        g.combo = 3
        g.tool_color = (g.queue[0] + 1) % 4
        assert g._repair() is False
        assert g.heat == Game.HEAT_MISMATCH
        assert g.combo == 0
        assert g.last_color is None
        assert g.score == 0

    def test_repair_keeps_queue_length(self) -> None:
        g = _make_game()
        before = len(g.queue)
        g.tool_color = g.queue[0]
        g._repair()
        assert len(g.queue) == before

    def test_repair_advances_queue(self) -> None:
        g = _make_game()
        g.queue = [0, 1, 2, 3, 0, 1]
        g.tool_color = 0
        g._repair()
        assert g.queue[0] == 1
        assert len(g.queue) == 6

    def test_mismatch_does_not_change_score(self) -> None:
        g = _make_game()
        g.tool_color = (g.queue[0] + 1) % 4
        g._repair()
        assert g.score == 0

    def test_combo_chain_scoring(self) -> None:
        g = _make_game()
        total = 0
        for i in range(1, 4):
            g.tool_color = g.queue[0]
            g._repair()
            total += 10 * i
            assert g.combo == i
        assert g.score == total


class TestSuper:
    def test_super_activates_at_combo_4(self) -> None:
        g = _make_game()
        for _ in range(4):
            g.tool_color = g.queue[0]
            g._repair()
        assert g.super_timer == Game.SUPER_DURATION

    def test_super_not_active_before_4(self) -> None:
        g = _make_game()
        for _ in range(3):
            g.tool_color = g.queue[0]
            g._repair()
        assert g.super_timer == 0

    def test_super_multiplies_score_by_3(self) -> None:
        g = _make_game()
        for _ in range(4):
            g.tool_color = g.queue[0]
            g._repair()
        prev = g.score
        g._repair()  # super active, combo 5
        assert g.combo == 5
        assert g.score == prev + 10 * 5 * 3

    def test_super_matches_any_color(self) -> None:
        g = _make_game()
        g.super_timer = 100
        g.tool_color = (g.queue[0] + 1) % 4
        assert g._repair() is True
        assert g.combo == 1
        assert g.heat == 0.0

    def test_super_prevents_mismatch_heat(self) -> None:
        g = _make_game()
        g.super_timer = 100
        g.tool_color = (g.queue[0] + 2) % 4
        g._repair()
        assert g.heat == 0.0

    def test_is_match_true_during_super(self) -> None:
        g = _make_game()
        g.super_timer = 50
        assert g._is_match((g.tool_color + 3) % 4) is True


class TestRewind:
    def test_rewind_costs_time(self) -> None:
        g = _make_game()
        g.timer = GAME_TIME
        assert g._rewind() is True
        assert g.timer == GAME_TIME - Game.REWIND_COST

    def test_rewind_preserves_combo(self) -> None:
        g = _make_game()
        g.combo = 3
        g.last_color = 1
        g.heat = 10.0
        g._rewind()
        assert g.combo == 3
        assert g.last_color == 1
        assert g.heat == 10.0

    def test_rewind_preserves_score(self) -> None:
        g = _make_game()
        g.score = 500
        g._rewind()
        assert g.score == 500

    def test_rewind_keeps_queue_length(self) -> None:
        g = _make_game()
        g.queue = [0, 1, 2, 3, 0, 1]
        g._rewind()
        assert len(g.queue) == 6
        assert g.queue[0] == 1

    def test_rewind_blocked_during_super(self) -> None:
        g = _make_game()
        g.super_timer = 50
        g.timer = GAME_TIME
        assert g._rewind() is False
        assert g.timer == GAME_TIME

    def test_rewind_blocked_with_short_queue(self) -> None:
        g = _make_game()
        g.queue = [0]
        g.timer = GAME_TIME
        assert g._rewind() is False
        assert g.timer == GAME_TIME


class TestHeat:
    def test_heat_decays(self) -> None:
        g = _make_game()
        g.heat = 50.0
        g._update_heat()
        assert g.heat < 50.0

    def test_heat_floors_at_zero(self) -> None:
        g = _make_game()
        g.heat = 0.0
        g._update_heat()
        assert g.heat == 0.0

    def test_heat_cap_game_over_before_decay(self) -> None:
        g = _make_game()
        g.heat = Game.HEAT_CAP
        g._update_heat()
        assert g.phase == Phase.GAME_OVER
        assert g.heat == Game.HEAT_CAP

    def test_heat_frozen_during_super(self) -> None:
        g = _make_game()
        g.super_timer = 50
        g.heat = 50.0
        g._update_heat()
        assert g.heat == 50.0

    def test_heat_just_below_cap_decays(self) -> None:
        g = _make_game()
        g.heat = Game.HEAT_CAP - 0.01
        g._update_heat()
        assert g.phase != Phase.GAME_OVER
        assert g.heat < Game.HEAT_CAP - 0.01


class TestTimer:
    def test_timer_decrements(self) -> None:
        g = _make_game()
        g.timer = 100
        g._update_timer()
        assert g.timer == 99

    def test_timer_zero_game_over(self) -> None:
        g = _make_game()
        g.timer = 1
        g._update_timer()
        assert g.timer == 0
        assert g.phase == Phase.GAME_OVER

    def test_timer_not_game_over_while_positive(self) -> None:
        g = _make_game()
        g.timer = 2
        g._update_timer()
        assert g.phase != Phase.GAME_OVER


class TestCycleInterval:
    def test_interval_decreases_over_time(self) -> None:
        g = _make_game()
        g.elapsed = 0
        start = g._cycle_interval()
        g.elapsed = GAME_TIME
        end = g._cycle_interval()
        assert end < start

    def test_interval_monotonic(self) -> None:
        g = _make_game()
        vals = []
        for e in (0, 900, 1800, 2700, 3600):
            g.elapsed = e
            vals.append(g._cycle_interval())
        assert vals == sorted(vals, reverse=True)

    def test_interval_endpoints(self) -> None:
        g = _make_game()
        g.elapsed = 0
        assert g._cycle_interval() == Game.CYCLE_INTERVAL_START
        g.elapsed = GAME_TIME
        assert g._cycle_interval() == Game.CYCLE_INTERVAL_END


class TestSpawnGear:
    def test_spawn_gear_in_range(self) -> None:
        g = _make_game()
        for _ in range(100):
            assert 0 <= g._spawn_gear() <= 3

    def test_spawn_gear_deterministic_seed(self) -> None:
        g1 = _make_game()
        g2 = _make_game()
        seq1 = [g1._spawn_gear() for _ in range(20)]
        seq2 = [g2._spawn_gear() for _ in range(20)]
        assert seq1 == seq2

    def test_spawn_gear_matches_reset_queue_head(self) -> None:
        g = _make_game()
        g._rng = random.Random(42)
        first = g._spawn_gear()
        g2 = _make_game()
        assert first == g2.queue[0]


class TestAdvanceToolColor:
    def test_advance_decrements_when_positive(self) -> None:
        g = _make_game()
        g.cycle_timer = 10
        g.tool_color = 0
        g._advance_tool_color()
        assert g.cycle_timer == 9
        assert g.tool_color == 0

    def test_advance_cycles_color_and_resets_timer(self) -> None:
        g = _make_game()
        g.cycle_timer = 0
        g.tool_color = 0
        g._advance_tool_color()
        assert g.tool_color == 1
        assert g.cycle_timer == g._cycle_interval()

    def test_advance_wraps_from_3_to_0(self) -> None:
        g = _make_game()
        g.cycle_timer = -1
        g.tool_color = 3
        g._advance_tool_color()
        assert g.tool_color == 0


class TestIsMatch:
    def test_is_match_same_color(self) -> None:
        g = _make_game()
        g.tool_color = 2
        assert g._is_match(2) is True

    def test_is_match_different_color(self) -> None:
        g = _make_game()
        g.tool_color = 2
        assert g._is_match(3) is False

    def test_is_match_super_always_true(self) -> None:
        g = _make_game()
        g.super_timer = 10
        g.tool_color = 2
        assert g._is_match(3) is True
