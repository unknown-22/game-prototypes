"""test_imports.py — Headless logic tests for SLED RUNAWAY (318_sled_chain).

Uses the Game.__new__(Game) bypass pattern to avoid pyxel.init/run.
Logic methods are pure (no pyxel.* calls) so they can be exercised directly.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import main as M
from main import FloatingText, Game, Gate, Particle, Phase


def assert_close(a: float, b: float, tol: float = 1e-6) -> None:
    assert abs(a - b) < tol, f"{a!r} != {b!r}"


def make_game() -> Game:
    g = Game.__new__(Game)
    g.reset()
    return g


def set_gate(g: Game, idx: int, color: int, active: bool = True) -> None:
    gate = g.gates[idx]
    g.gates[idx] = Gate(x=gate.x, y=gate.y, color=color, active=active, respawn_timer=0)


# ---- constants / init ----


def test_constants() -> None:
    assert len(M.GATE_COLORS) == 4
    assert M.GATE_COUNT == 6
    assert len(M.GATE_XS) == 6 and len(M.GATE_YS) == 6
    assert M.RUNAWAY_THRESHOLD < M.MOMENTUM_MAX
    assert M.COMBO_SUPER == 4


def test_reset_initial_state() -> None:
    g = make_game()
    assert len(g.gates) == M.GATE_COUNT
    assert g.phase == Phase.TITLE
    assert g.combo == 0 and g.max_combo == 0
    assert g.score == 0
    assert g.heat == 0.0 and g.momentum == 0.0
    assert g.runaway is False and g.super_timer == 0
    assert g.timer == M.TIMER_MAX
    assert all(gate.active for gate in g.gates)


# ---- core action ----


def test_first_match_scores_10() -> None:
    g = make_game()
    set_gate(g, 0, M.GATE_COLORS[0])
    g.sled_color = M.GATE_COLORS[0]
    assert g._hit_gate(0) is True
    assert g.combo == 1
    assert g.score == 10  # 10 * 1 * 1
    assert_close(g.momentum, M.MOMENTUM_GAIN)


def test_match_deactivates_gate() -> None:
    g = make_game()
    set_gate(g, 0, M.GATE_COLORS[0])
    g.sled_color = M.GATE_COLORS[0]
    g._hit_gate(0)
    assert g.gates[0].active is False
    assert g.gates[0].respawn_timer > 0


def test_mismatch_resets_combo_and_momentum() -> None:
    g = make_game()
    set_gate(g, 0, M.GATE_COLORS[0])
    g.sled_color = M.GATE_COLORS[0]
    g._hit_gate(0)
    set_gate(g, 1, M.GATE_COLORS[1])
    g.sled_color = M.GATE_COLORS[0]  # differs from gate 1's color
    assert g._hit_gate(1) is False
    assert g.combo == 0
    assert g.momentum == 0.0
    assert_close(g.heat, M.HEAT_MISMATCH)


def test_hit_inactive_gate_returns_false() -> None:
    g = make_game()
    set_gate(g, 0, M.GATE_COLORS[0], active=False)
    g.sled_color = M.GATE_COLORS[0]
    assert g._hit_gate(0) is False
    assert g.combo == 0 and g.score == 0


def test_combo_accumulates_score() -> None:
    g = make_game()
    color = M.GATE_COLORS[0]
    g.sled_color = color
    total = 0
    for i in range(4):
        set_gate(g, i, color)
        assert g._hit_gate(i) is True
        total += 10 * (i + 1)
        assert g.score == total
    assert g.combo == 4 and g.max_combo == 4


# ---- SUPER (combo >= 4) ----


def test_super_triggers_at_combo_4() -> None:
    g = make_game()
    color = M.GATE_COLORS[0]
    g.sled_color = color
    for i in range(4):
        set_gate(g, i, color)
        g._hit_gate(i)
    assert g.super_timer == M.SUPER_DURATION


def test_super_any_color_match_and_3x() -> None:
    g = make_game()
    color = M.GATE_COLORS[0]
    g.sled_color = color
    for i in range(4):
        set_gate(g, i, color)
        g._hit_gate(i)
    assert g.score == 100  # 10 + 20 + 30 + 40
    set_gate(g, 4, M.GATE_COLORS[2])  # mismatched color
    g.sled_color = color  # super ignores mismatch
    g._hit_gate(4)
    assert g.combo == 5
    assert g.score == 100 + 10 * 5 * 3


def test_super_freezes_heat_and_momentum() -> None:
    g = make_game()
    color = M.GATE_COLORS[0]
    g.sled_color = color
    for i in range(4):
        set_gate(g, i, color)
        g._hit_gate(i)
    g.heat = 50.0
    g.momentum = 50.0
    g._update_playing()
    assert_close(g.heat, 50.0)
    assert_close(g.momentum, 50.0)
    assert g.super_timer == M.SUPER_DURATION - 1


# ---- RUNAWAY (momentum >= threshold) ----


def test_runaway_engages_above_threshold() -> None:
    g = make_game()
    g.momentum = 75.0
    g._update_momentum()
    assert g.runaway is True


def test_runaway_entry_effect() -> None:
    g = make_game()
    g.momentum = 75.0
    g._update_momentum()
    assert g.shake == 6
    assert any(t.text == "RUNAWAY!" for t in g.floating_texts)
    assert len(g.particles) == 16


def test_runaway_3x_score() -> None:
    g = make_game()
    g.momentum = 75.0
    g._update_momentum()
    assert g.runaway is True
    set_gate(g, 0, M.GATE_COLORS[0])
    g.sled_color = M.GATE_COLORS[0]
    g.combo = 0
    g._hit_gate(0)
    assert g.score == 30  # 10 * 1 * 3


def test_runaway_momentum_decays_faster() -> None:
    g = make_game()
    g.momentum = 75.0
    g._update_momentum()  # -> runaway True, idle decay 0.1 -> 74.9
    before = g.momentum
    g._update_momentum()  # -> runaway decay 0.35
    assert_close(before - g.momentum, M.MOMENTUM_DECAY_RUNAWAY)


def test_idle_momentum_decays_slowly() -> None:
    g = make_game()
    g.momentum = 50.0
    g._update_momentum()
    assert_close(g.momentum, 50.0 - M.MOMENTUM_DECAY_IDLE)
    assert g.runaway is False


def test_runaway_disengages_below_threshold() -> None:
    g = make_game()
    g.momentum = 75.0
    g._update_momentum()
    assert g.runaway is True
    g.momentum = 0.0
    g._update_momentum()
    assert g.runaway is False


def test_momentum_clamped_at_max() -> None:
    g = make_game()
    g.momentum = M.MOMENTUM_MAX - 1
    set_gate(g, 0, M.GATE_COLORS[0])
    g.sled_color = M.GATE_COLORS[0]
    g._hit_gate(0)
    assert_close(g.momentum, M.MOMENTUM_MAX)


# ---- heat / timer / failure ----


def test_heat_game_over() -> None:
    g = make_game()
    g.heat = M.HEAT_MAX
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_heat_decays() -> None:
    g = make_game()
    g.heat = 30.0
    g._update_heat()
    assert_close(g.heat, 30.0 - M.HEAT_DECAY)


def test_heat_never_below_zero() -> None:
    g = make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_timer_game_over() -> None:
    g = make_game()
    g.timer = 1
    g._update_timer()
    assert g.phase == Phase.GAME_OVER


# ---- respawn / escalation ----


def test_gate_respawns() -> None:
    g = make_game()
    set_gate(g, 0, M.GATE_COLORS[0])
    g.sled_color = M.GATE_COLORS[0]
    g._hit_gate(0)
    assert g.gates[0].active is False
    for _ in range(g.gates[0].respawn_timer + 5):
        g._update_gates()
    assert g.gates[0].active is True


def test_respawn_delay_range() -> None:
    g = make_game()
    assert g._respawn_delay() == 60
    g.elapsed = 3600
    # 60 - 3600//120 == 30; the max(25, ...) floor is not reached within 60s
    assert g._respawn_delay() == 30
    # escalation is monotonic non-increasing
    assert g._respawn_delay() < 60


def test_cycle_interval_range() -> None:
    g = make_game()
    assert g._cycle_interval() == 20
    g.elapsed = 3600
    assert g._cycle_interval() == 12


def test_current_cycle_halves_in_runaway() -> None:
    g = make_game()
    g.runaway = True
    assert g._current_cycle() == g._cycle_interval() // 2


def test_sled_color_cycles() -> None:
    g = make_game()
    start = g.sled_color
    g.color_timer = 1
    g._update_sled_color()
    assert g.sled_color == M.GATE_COLORS[(M.GATE_COLORS.index(start) + 1) % 4]


# ---- particles / floating text ----


def test_particle_lifecycle() -> None:
    g = make_game()
    g.particles = [Particle(x=10.0, y=10.0, vx=1.0, vy=0.0, color=8, life=1)]
    g._update_particles()
    assert g.particles == []


def test_floating_text_lifecycle() -> None:
    g = make_game()
    g.floating_texts = [FloatingText(x=10.0, y=10.0, text="x", color=8, life=1)]
    g._update_floating_texts()
    assert g.floating_texts == []


def test_best_score_preserved_across_reset() -> None:
    g = make_game()
    g.best_score = 500
    g.reset()
    assert g.best_score == 500
    assert g.score == 0


if __name__ == "__main__":
    tests = sorted(
        (name, fn)
        for name, fn in globals().items()
        if name.startswith("test_") and callable(fn)
    )
    failures = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception:
            failures += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
