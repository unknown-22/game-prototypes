"""test_imports.py — Headless logic tests for 320_steady_chain (STEADY CHAIN).

Runs standalone (uv run python prototypes/320_steady_chain/test_imports.py) or via pytest.
Constructs Game via __new__ to bypass pyxel.init/pyxel.run, seeds rng for determinism,
and disables sound. Never calls methods that touch pyxel input state.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import FloatingText, Game, Particle, Phase, Segment  # noqa: E402


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(seed)
    g.best_score = 0
    g._sfx_enabled = False
    g.reset()
    return g


def _midpoint(seg: Segment) -> tuple[float, float]:
    return ((seg.x1 + seg.x2) / 2.0, (seg.y1 + seg.y2) / 2.0)


def _set_all_segments_color(g: Game, color: int) -> None:
    for seg in g.segments:
        seg.color = color


# ── import / dataclass / constants ──────────────────────────────────────────


def test_imports_and_phase():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


def test_constants():
    assert Game.SCREEN_W == 320
    assert Game.SCREEN_H == 240
    assert Game.TIMER_START == 3600
    assert Game.MAX_HEAT == 100
    assert Game.SUPER_DURATION == 300
    assert tuple(Game.COLORS) == (8, 11, 5, 10)


def test_dataclass_construction():
    s = Segment(x1=0.0, y1=0.0, x2=10.0, y2=10.0, color=8)
    assert s.cut is False
    p = Particle(x=1.0, y=2.0, vx=0.5, vy=-0.5, life=20, color=11)
    assert p.life == 20
    t = FloatingText(x=5.0, y=5.0, text="+10", life=40, color=8)
    assert t.text == "+10"


# ── reset / spawn ───────────────────────────────────────────────────────────


def test_reset_initial_state():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.score == 0
    assert g.heat == 0.0
    assert g.time_left == Game.TIMER_START
    assert g.super_mode is False
    assert g.scalpel_color == Game.COLORS[0]
    assert g.active_idx == 0


def test_spawn_incision_geometry():
    g = _make_game()
    assert len(g.segments) == len(Game.WAYPOINTS) - 1  # 6 segments
    for seg in g.segments:
        assert seg.color in Game.COLORS
        assert seg.cut is False
    # deterministic with seeded rng
    g2 = _make_game(seed=42)
    assert [s.color for s in g.segments] == [s.color for s in g2.segments]


# ── _try_cut core action ────────────────────────────────────────────────────


def test_try_cut_none_when_not_playing():
    g = _make_game()  # phase == TITLE
    mid = _midpoint(g.segments[0])
    assert g._try_cut(*mid) == "none"


def test_try_cut_match():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.segments[0].color = g.scalpel_color
    mid = _midpoint(g.segments[0])
    assert g._try_cut(*mid) == "cut"
    assert g.combo == 1
    assert g.score == 10  # 10 * combo(1) * mult(1)
    assert g.segments[0].cut is True
    assert g.active_idx == 1


def test_try_cut_wrong_color():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.segments[0].color = Game.COLORS[1]  # different from scalpel (COLORS[0])
    mid = _midpoint(g.segments[0])
    assert g._try_cut(*mid) == "wrong"
    assert g.combo == 0
    assert g.heat == 15.0
    assert g.segments[0].cut is False  # segment stays
    assert g.active_idx == 0


def test_try_cut_slip_off_path():
    g = _make_game()
    g.phase = Phase.PLAYING
    # (0, 0) is far from segment 0 (30,130)-(70,80) — distance >> half_width
    assert g._try_cut(0.0, 0.0) == "slip"
    assert g.combo == 0
    assert g.heat == 15.0


def test_on_path_boundary_is_not_slip():
    # a point exactly on the segment centerline is on-path (distance 0 <= half_width)
    g = _make_game()
    g.phase = Phase.PLAYING
    g.segments[0].color = g.scalpel_color
    mid = _midpoint(g.segments[0])
    assert g._try_cut(*mid) == "cut"  # not a slip


# ── combo chain / scoring ───────────────────────────────────────────────────


def test_combo_chain_scoring():
    g = _make_game()
    g.phase = Phase.PLAYING
    _set_all_segments_color(g, g.scalpel_color)
    for _ in range(3):
        seg = g.segments[g.active_idx]
        assert g._try_cut(*_midpoint(seg)) == "cut"
    assert g.combo == 3
    assert g.score == 10 + 20 + 30  # 60


def test_super_triggers_at_combo_4():
    g = _make_game()
    g.phase = Phase.PLAYING
    _set_all_segments_color(g, g.scalpel_color)
    for _ in range(4):
        seg = g.segments[g.active_idx]
        g._try_cut(*_midpoint(seg))
    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == Game.SUPER_DURATION


def test_super_multiplies_score():
    g = _make_game()
    g.phase = Phase.PLAYING
    _set_all_segments_color(g, g.scalpel_color)
    for _ in range(4):
        seg = g.segments[g.active_idx]
        g._try_cut(*_midpoint(seg))
    # combo==4, super now active; 5th cut scores 10 * 5 * 3 = 150
    score_before = g.score
    seg = g.segments[g.active_idx]
    g._try_cut(*_midpoint(seg))
    assert g.combo == 5
    assert g.score == score_before + 150


def test_incision_complete_preserves_combo():
    g = _make_game()
    g.phase = Phase.PLAYING
    _set_all_segments_color(g, g.scalpel_color)
    for _ in range(6):  # cut all segments -> incision complete
        seg = g.segments[g.active_idx]
        g._try_cut(*_midpoint(seg))
    # new incision spawned, active back to 0, combo PRESERVED
    assert len(g.segments) == 6
    assert g.active_idx == 0
    assert g.combo == 6
    # score = 10+20+30+40 (mult1) +150+180 (super 3x) + 100*6 bonus = 1030
    assert g.score == 1030


# ── heat / timer / super lifecycle ─────────────────────────────────────────


def test_heat_game_over_threshold():
    g = _make_game()
    g.heat = 100.0
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_heat_decay():
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert abs(g.heat - (50.0 - 0.02)) < 0.001


def test_heat_frozen_in_super():
    g = _make_game()
    g.super_mode = True
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 50.0  # no decay while super


def test_timer_game_over():
    g = _make_game()
    g.time_left = 1
    g._update_timer()
    assert g.time_left == 0
    assert g.phase == Phase.GAME_OVER


def test_super_expiry():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_super()
    assert g.super_timer == 0
    assert g.super_mode is False


# ── color cycling / difficulty curves ──────────────────────────────────────


def test_cycle_color_advances():
    g = _make_game()
    g.scalpel_timer = 1
    g.super_mode = False
    g._cycle_color()
    assert g.scalpel_color == Game.COLORS[1]


def test_cycle_color_frozen_in_super():
    g = _make_game()
    g.super_mode = True
    timer_before = g.scalpel_timer
    color_before = g.scalpel_color
    g._cycle_color()
    assert g.scalpel_timer == timer_before
    assert g.scalpel_color == color_before


def test_cycle_interval_curve():
    g = _make_game()
    g.elapsed = 0
    assert g._cycle_interval() == 20
    g.elapsed = 150
    assert g._cycle_interval() == 19
    g.elapsed = 1200
    assert g._cycle_interval() == 12  # floor


def test_half_width_narrows():
    g = _make_game()
    g.elapsed = 0
    assert g._half_width() == 10.0
    g.elapsed = 450
    assert g._half_width() == 9.0
    g.elapsed = 3000
    assert g._half_width() == 7.0  # floor


# ── geometry ────────────────────────────────────────────────────────────────


def test_distance_point_segment():
    g = _make_game()
    seg = Segment(x1=0.0, y1=0.0, x2=10.0, y2=0.0, color=8)
    assert abs(g._distance_point_segment(5.0, 0.0, seg) - 0.0) < 0.001
    assert abs(g._distance_point_segment(5.0, 3.0, seg) - 3.0) < 0.001
    # projection clamped to endpoint (10,0): distance = sqrt(2^2 + 4^2) = sqrt(20)
    import math

    assert abs(g._distance_point_segment(12.0, 4.0, seg) - math.sqrt(20.0)) < 0.001


# ── restart ─────────────────────────────────────────────────────────────────


def test_restart_preserves_best_score():
    g = _make_game()
    g.score = 500
    g._restart()
    assert g.best_score == 500
    assert g.phase == Phase.PLAYING
    assert g.combo == 0
    assert g.score == 0


# ── runner ──────────────────────────────────────────────────────────────────


def _run_all() -> int:
    tests = [
        (name, fn)
        for name, fn in sorted(globals().items())
        if name.startswith("test_") and callable(fn)
    ]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS {name}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  FAIL {name}: {type(exc).__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} tests passed")
    return failures


if __name__ == "__main__":
    sys.exit(_run_all())
