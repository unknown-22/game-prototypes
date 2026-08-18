"""test_imports.py — Headless logic tests for 321_kintsugi_chain (KINTSUGI CHAIN).

Runs standalone (uv run python prototypes/321_kintsugi_chain/test_imports.py) or via pytest.
Constructs Game via __new__ to bypass pyxel.init/pyxel.run, seeds rng for determinism.
Never calls methods that touch pyxel input state (update/draw, pyxel.btn/mouse).
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # noqa: E402
    CLICK_RADIUS,
    CRACK_COLORS,
    MAX_CRACKS,
    TIME_LIMIT,
    Crack,
    FloatText,
    Game,
    Particle,
    Phase,
    Segment,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(seed)
    g.reset()
    return g


def _other_color(color: int) -> int:
    return next(c for c in CRACK_COLORS if c != color)


# ── import / dataclass / constants ──────────────────────────────────────────


def test_imports_and_phase():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


def test_dataclass_construction():
    s = Segment(x=10.0, y=20.0, color=8)
    assert s.filled is False
    c = Crack(angle=0.5, segments=[s])
    assert c.complete is False
    p = Particle(x=1.0, y=2.0, vx=0.5, vy=-0.5, life=20, color=11)
    assert p.life == 20
    ft = FloatText(x=5.0, y=5.0, text="+10", color=8, life=30)
    assert ft.text == "+10"


# ── reset / spawn ───────────────────────────────────────────────────────────


def test_reset_initial_state():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.score == 0
    assert g.heat == 0.0
    assert len(g.cracks) == 4
    assert all(len(c.segments) == 4 for c in g.cracks)
    assert all(not seg.filled for c in g.cracks for seg in c.segments)
    assert all(not c.complete for c in g.cracks)


def test_reset_preserves_best_score():
    g = _make_game()
    g.best_score = 1234
    g.reset()
    assert g.best_score == 1234
    assert g.score == 0


# ── brush cycle ─────────────────────────────────────────────────────────────


def test_brush_cycle_advances():
    g = _make_game()
    start = g.brush_color
    g.brush_timer = 1
    g._brush_cycle()
    assert g.brush_color == CRACK_COLORS[(CRACK_COLORS.index(start) + 1) % 4]
    assert g.brush_timer == 20  # reset to cycle_interval at frame 0


def test_brush_cycle_frozen_in_super():
    g = _make_game()
    g.super_timer = 300
    start = g.brush_color
    g.brush_timer = 1
    g._brush_cycle()
    assert g.brush_color == start
    assert g.brush_timer == 1  # unchanged


# ── fill / combo / score ────────────────────────────────────────────────────


def test_matching_fill_builds_combo_and_score():
    g = _make_game()
    seg = g.cracks[0].segments[0]
    seg.color = g.brush_color
    g._try_fill(seg.x, seg.y)
    assert seg.filled is True
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score == 10
    seg2 = g.cracks[0].segments[1]
    seg2.color = g.brush_color
    g._try_fill(seg2.x, seg2.y)
    assert g.combo == 2
    assert g.score == 30


def test_mismatch_resets_combo_adds_heat():
    g = _make_game()
    seg = g.cracks[0].segments[0]
    seg.color = _other_color(g.brush_color)
    g.combo = 3
    g._try_fill(seg.x, seg.y)
    assert seg.filled is False
    assert g.combo == 0
    assert g.heat == 15
    assert g.score == 0


def test_super_mode_any_color_3x():
    g = _make_game()
    g.combo = 4
    g.super_timer = 300
    assert g.super_active is True
    seg = g.cracks[0].segments[0]
    seg.color = _other_color(g.brush_color)  # non-matching color
    g._try_fill(seg.x, seg.y)
    assert seg.filled is True  # super matches any color
    assert g.combo == 5
    assert g.score == 150  # 10 * 5 * 3


def test_fill_full_crack_triggers_complete():
    g = _make_game()
    crack = g.cracks[0]
    for seg in crack.segments:
        seg.color = g.brush_color
    for seg in crack.segments:
        g._try_fill(seg.x, seg.y)
    assert crack.complete is True
    assert g.completed_veins == 1
    # 10 + 20 + 30 + 40 + bonus(50*4*1=200) = 300
    assert g.score == 300


def test_click_empty_space_no_op():
    g = _make_game()
    g._try_fill(0, 0)
    assert g.combo == 0
    assert g.heat == 0
    assert g.score == 0


def test_click_filled_segment_no_op():
    g = _make_game()
    seg = g.cracks[0].segments[0]
    seg.filled = True
    g.combo = 2
    g._try_fill(seg.x, seg.y)
    assert g.combo == 2
    assert g.score == 0


# ── crack completion / vein network (log/replay as asset) ───────────────────


def test_crack_complete_bonus_scales_with_veins():
    g = _make_game()
    g.combo = 5
    c0 = g.cracks[0]
    for seg in c0.segments:
        seg.filled = True
    b0 = g._check_crack_complete(c0)
    assert b0 == 50 * 5 * 1  # 250
    assert g.completed_veins == 1
    assert c0.complete is True
    assert g.score == 250

    c1 = g.cracks[1]
    for seg in c1.segments:
        seg.filled = True
    b1 = g._check_crack_complete(c1)
    assert b1 == 50 * 5 * 2  # 500 — vein count doubles the bonus
    assert g.completed_veins == 2
    assert g.score == 750


def test_crack_complete_no_double_count():
    g = _make_game()
    c0 = g.cracks[0]
    for seg in c0.segments:
        seg.filled = True
    g._check_crack_complete(c0)
    assert g.completed_veins == 1
    g._check_crack_complete(c0)  # already complete -> no-op
    assert g.completed_veins == 1


# ── vessel restoration ──────────────────────────────────────────────────────


def test_vessel_restored_preserves_combo():
    g = _make_game()
    g.combo = 7
    for crack in g.cracks:
        for seg in crack.segments:
            seg.filled = True
        crack.complete = True
    g.completed_veins = 4
    result = g._check_vessel_restored()
    assert result is True
    assert g.restored_count == 1
    assert g.completed_veins == 0
    assert g.score == 500
    assert g.combo == 7  # combo preserved across restoration
    assert len(g.cracks) == 4
    assert all(not c.complete for c in g.cracks)
    assert all(not seg.filled for c in g.cracks for seg in c.segments)


def test_vessel_not_restored_when_incomplete():
    g = _make_game()
    assert g._check_vessel_restored() is False
    assert g.restored_count == 0


# ── failure conditions ──────────────────────────────────────────────────────


def test_heat_cap_game_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 100
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_heat_decay():
    g = _make_game()
    g.heat = 50
    g._update_heat()
    assert abs(g.heat - 49.98) < 0.001


def test_heat_frozen_in_super():
    g = _make_game()
    g.super_timer = 300
    g.heat = 50
    g._update_heat()
    assert g.heat == 50


def test_timer_game_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.frame = TIME_LIMIT
    g._update_timer()
    assert g.phase == Phase.GAME_OVER


# ── escalation ──────────────────────────────────────────────────────────────


def test_cycle_interval_escalation():
    g = _make_game()
    g.frame = 0
    assert g._cycle_interval() == 20
    g.frame = 1200
    assert g._cycle_interval() == 12
    g.frame = 3600
    assert g._cycle_interval() == 12


def test_crack_spawn_interval_escalation():
    g = _make_game()
    g.frame = 0
    assert g._crack_spawn_interval() == 240
    g.frame = 3600
    assert g._crack_spawn_interval() == 120


def test_crack_spawn_respects_max():
    g = _make_game()
    g.next_crack_spawn = 0
    g.frame = 1
    g._update_crack_spawn()
    assert len(g.cracks) == 5
    g.next_crack_spawn = 0
    g._update_crack_spawn()
    assert len(g.cracks) == 6
    g.next_crack_spawn = 0
    g._update_crack_spawn()
    assert len(g.cracks) == MAX_CRACKS  # no further spawns


# ── geometry / layout ───────────────────────────────────────────────────────


def test_segment_layout_within_screen():
    g = _make_game()
    for crack in g.cracks:
        for seg in crack.segments:
            assert 0 <= seg.x <= 320
            assert 0 <= seg.y <= 240


def test_adjacent_segments_not_overlapping():
    g = _make_game()
    crack = g.cracks[0]
    for i in range(len(crack.segments) - 1):
        a = crack.segments[i]
        b = crack.segments[i + 1]
        d = math.hypot(b.x - a.x, b.y - a.y)
        assert d > 2 * CLICK_RADIUS  # click radii never overlap


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
