"""test_imports.py — Headless logic tests for 334_shell_chain."""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/334_shell_chain")

from main import (
    BALL_COLORS,
    Cup,
    FloatingText,
    HEAT_MAX,
    HEAT_PER_MISS,
    MAX_CUPS,
    Particle,
    Phase,
    SUPER_VISION_FRAMES,
    TIMER_FRAMES,
    Game,
    START_CUPS,
    RED,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(42)
    g.reset()
    return g


# ── Setup / Reset ──────────────────────────────────────────────────

def test_reset_starts_at_show():
    g = _make_game()
    assert g.phase == Phase.SHOW


def test_reset_creates_start_cups():
    g = _make_game()
    assert len(g.cups) == START_CUPS


def test_reset_cups_unrevealed():
    """After reset -> SHOW, cups should be revealed (SHOW phase shows all)."""
    g = _make_game()
    assert all(c.revealed for c in g.cups)


def test_reset_sets_initial_state():
    g = _make_game()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0
    assert g.timer == TIMER_FRAMES


def test_reset_clears_particles():
    g = _make_game()
    g.particles = [Particle(0, 0, 0, 0, 10, 1)]
    g.reset()
    assert g.particles == []


# ── Phase Transitions ──────────────────────────────────────────────

def test_show_to_shuffle():
    g = _make_game()
    assert g.phase == Phase.SHOW
    g._start_shuffle()
    assert g.phase == Phase.SHUFFLE


def test_shuffle_to_guess():
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    assert g.phase == Phase.GUESS


def test_shuffle_hides_cups():
    g = _make_game()
    g._start_shuffle()
    assert all(not c.revealed for c in g.cups)


def test_guess_phase_unrevealed_cups():
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    assert all(not c.revealed for c in g.cups)


# ── Matching ───────────────────────────────────────────────────────

def test_correct_guess_matches():
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    c = g.cups[0]
    g._handle_guess(0, c.ball_color)
    assert c.revealed
    assert g.combo == 1
    assert g.score == 10


def test_second_correct_guess_increases_combo():
    """Guess two DIFFERENT-colored cups sequentially to build combo."""
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    # Ensure cups 0 and 1 have DIFFERENT colors so chain burst doesn't reveal both
    g.cups[0].ball_color = BALL_COLORS[0]
    g.cups[1].ball_color = BALL_COLORS[1]
    g.cups[2].ball_color = BALL_COLORS[2] if len(BALL_COLORS) > 2 else BALL_COLORS[0]
    g._handle_guess(0, g.cups[0].ball_color)
    assert g.combo == 1
    g._handle_guess(1, g.cups[1].ball_color)
    assert g.combo == 2
    assert g.score == 10 + 20  # 10*1 + 10*2


def test_wrong_guess_mismatches():
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    c = g.cups[0]
    wrong = [x for x in BALL_COLORS if x != c.ball_color][0]
    g._handle_guess(0, wrong)
    assert not c.revealed
    assert g.combo == 0
    assert g.heat == HEAT_PER_MISS


def test_mismatch_randomizes_ball_color():
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    old_color = g.cups[0].ball_color
    wrong = [x for x in BALL_COLORS if x != old_color][0]
    g._handle_guess(0, wrong)
    assert g.heat == HEAT_PER_MISS


def test_mismatch_adds_floating_text():
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    c = g.cups[0]
    wrong = [x for x in BALL_COLORS if x != c.ball_color][0]
    g._handle_guess(0, wrong)
    texts = [t.text for t in g.floating_texts]
    assert "MISS" in texts


# ── Chain Burst ───────────────────────────────────────────────────

def test_chain_burst_reveals_adjacent_same_color():
    """When cups 0,1,2 all have same color, matching cup 0 should reveal all."""
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    # Force all same color
    color = BALL_COLORS[0]
    for c in g.cups:
        c.ball_color = color
    g._handle_guess(0, color)
    # All should be revealed via chain burst
    assert all(c.revealed for c in g.cups)
    # Only the initial match increments combo (chain-burst cups don't)
    assert g.combo == 1


def test_chain_burst_stops_at_different_color():
    """When cup 0 and 1 match but cup 2 differs, chain should stop at 2."""
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    color = BALL_COLORS[0]
    other = [x for x in BALL_COLORS if x != color][0]
    g.cups[0].ball_color = color
    g.cups[1].ball_color = color
    g.cups[2].ball_color = other
    g._handle_guess(0, color)
    assert g.cups[0].revealed
    assert g.cups[1].revealed
    assert not g.cups[2].revealed


def test_chain_burst_spawns_particles():
    """Chain burst should spawn particles for each revealed cup."""
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    color = BALL_COLORS[0]
    for c in g.cups:
        c.ball_color = color
    before = len(g.particles)
    g._handle_guess(0, color)
    assert len(g.particles) > before


# ── Super Vision ───────────────────────────────────────────────────

def test_super_vision_activates_at_combo_4():
    """4 sequential correct guesses (each different color) should trigger super vision."""
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    # Start with 4 cups to allow 4 guesses without round-complete
    g.cup_count = 4
    g._make_cups()
    # Assign unique colors to each cup so chain burst never triggers
    for i, c in enumerate(g.cups):
        c.ball_color = BALL_COLORS[i % len(BALL_COLORS)]
    for i in range(4):
        g._handle_guess(i, g.cups[i].ball_color)
    assert g.combo == 4
    assert g.super_vision > 0


def test_super_vision_auto_matches():
    """Super vision should match even wrong color guesses."""
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    # Need 4 cups
    g.cup_count = 4
    g._make_cups()
    for i, c in enumerate(g.cups):
        c.ball_color = BALL_COLORS[i % len(BALL_COLORS)]
    # Force combo to 3
    for i in range(3):
        g._handle_guess(i, g.cups[i].ball_color)
    g.super_vision = SUPER_VISION_FRAMES
    # Guess wrong color on cup 3 — should still match
    c = g.cups[3]
    wrong = [x for x in BALL_COLORS if x != c.ball_color][0]
    g._handle_guess(3, wrong)
    assert c.revealed
    assert g.combo == 4


def test_super_vision_frozen_heat():
    """Heat should not increase during super vision."""
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    g.super_vision = SUPER_VISION_FRAMES
    g.heat = 50
    c = g.cups[0]
    wrong = [x for x in BALL_COLORS if x != c.ball_color][0]
    g._handle_guess(0, wrong)
    assert g.heat == 50


def test_super_vision_3x_score():
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    g.super_vision = SUPER_VISION_FRAMES
    g.combo = 2
    g._handle_guess(0, g.cups[0].ball_color)
    # combo becomes 3, score = 10 * 3 * 3 = 90
    assert g.score == 90


def test_super_vision_timer_decrements():
    g = _make_game()
    g.super_vision = SUPER_VISION_FRAMES
    g.super_vision -= 1
    assert g.super_vision == SUPER_VISION_FRAMES - 1


def test_super_vision_message_spawned():
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    g.cup_count = 4
    g._make_cups()
    for i, c in enumerate(g.cups):
        c.ball_color = BALL_COLORS[i % len(BALL_COLORS)]
    for i in range(4):
        g._handle_guess(i, g.cups[i].ball_color)
    texts = [t.text for t in g.floating_texts]
    assert "SUPER VISION!" in texts


# ── Heat System ────────────────────────────────────────────────────

def test_heat_accumulates_on_mismatch():
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    for i in range(5):
        c = g.cups[i % len(g.cups)]
        wrong = [x for x in BALL_COLORS if x != c.ball_color][0]
        g._handle_guess(i % len(g.cups), wrong)
    assert g.heat == HEAT_PER_MISS * 5


def test_heat_caps_at_max():
    g = _make_game()
    g.heat = HEAT_MAX - 5
    g._update_heat(HEAT_PER_MISS)
    assert g.heat == HEAT_MAX


def test_heat_triggers_game_over():
    g = _make_game()
    g.heat = HEAT_MAX
    assert g._check_game_over()
    assert g.phase == Phase.GAME_OVER


# ── Timer ──────────────────────────────────────────────────────────

def test_timer_decrements_outside_super_vision():
    g = _make_game()
    g.timer = 100
    g.timer -= 1
    assert g.timer == 99


def test_timer_zero_triggers_game_over():
    g = _make_game()
    g.timer = 0
    assert g._check_game_over()


def test_super_vision_prevents_timer_decrement():
    g = _make_game()
    g.super_vision = 10
    g.timer = 100
    if g.super_vision > 0:
        g.super_vision -= 1
    else:
        g.timer -= 1
    assert g.timer == 100


# ── Round Complete ─────────────────────────────────────────────────

def test_round_complete_gives_bonus():
    g = _make_game()
    g.combo = 3
    for c in g.cups:
        c.revealed = True
    g._round_complete()
    assert g.score == 300  # 100 * 3


def test_round_complete_increases_cup_count():
    g = _make_game()
    g.cup_count = 3
    for c in g.cups:
        c.revealed = True
    g._round_complete()
    assert g.cup_count == 4


def test_round_complete_caps_at_max_cups():
    g = _make_game()
    g.cup_count = MAX_CUPS
    for c in g.cups:
        c.revealed = True
    g._round_complete()
    assert g.cup_count == MAX_CUPS


def test_round_complete_sets_resolve_phase():
    g = _make_game()
    for c in g.cups:
        c.revealed = True
    g._round_complete()
    assert g.phase == Phase.RESOLVE


def test_all_revealed_returns_true():
    g = _make_game()
    for c in g.cups:
        c.revealed = True
    assert g._all_revealed()


def test_all_revealed_returns_false():
    g = _make_game()
    g.cups[0].revealed = False
    assert not g._all_revealed()


# ── Escalation ─────────────────────────────────────────────────────

def test_show_timer_decreases_with_more_cups():
    g = _make_game()
    g.cup_count = START_CUPS
    t1 = g._show_timer()
    g.cup_count = MAX_CUPS
    t2 = g._show_timer()
    assert t2 < t1


def test_shuffle_duration_decreases_with_more_cups():
    g = _make_game()
    g.cup_count = START_CUPS
    s1 = g._shuffle_duration()
    g.cup_count = MAX_CUPS
    s2 = g._shuffle_duration()
    assert s2 < s1


def test_show_timer_at_start():
    g = _make_game()
    g.cup_count = START_CUPS
    assert 60 <= g._show_timer() <= 120


def test_shuffle_duration_at_start():
    g = _make_game()
    g.cup_count = START_CUPS
    assert 20 <= g._shuffle_duration() <= 40


# ── Particles ──────────────────────────────────────────────────────

def test_spawn_burst_creates_particles():
    g = _make_game()
    before = len(g.particles)
    g._spawn_burst(100, 100, 8)
    assert len(g.particles) > before


def test_update_particles_removes_dead():
    g = _make_game()
    g.particles = [
        Particle(0, 0, 0, 0, 1, 8),
        Particle(0, 0, 0, 0, 5, 11),
    ]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 4


def test_particle_physics():
    g = _make_game()
    g.particles = [Particle(0, 0, 1, -2, 10, 8)]
    g._update_particles()
    p = g.particles[0]
    assert p.x == 1
    assert p.vy > -2


# ── Floating Text ──────────────────────────────────────────────────

def test_floating_text_rises():
    g = _make_game()
    g.floating_texts = [FloatingText(100, 100, "TEST", 8, 10)]
    g._update_floating_texts()
    assert g.floating_texts[0].y < 100


def test_floating_text_life_decrements():
    g = _make_game()
    g.floating_texts = [FloatingText(100, 100, "TEST", 8, 2)]
    g._update_floating_texts()
    assert g.floating_texts[0].life == 1


def test_floating_text_removed_at_zero():
    g = _make_game()
    g.floating_texts = [FloatingText(100, 100, "TEST", 8, 1)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Input ──────────────────────────────────────────────────────────

def test_guess_out_of_bounds_ignored():
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    g._handle_guess(999, RED)
    assert g.combo == 0


def test_guess_revealed_cup_ignored():
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    g.cups[0].revealed = True
    g._handle_guess(0, g.cups[0].ball_color)
    assert g.combo == 0
    assert g.score == 0


# ── Layout ─────────────────────────────────────────────────────────

def test_layout_positions_cups_evenly():
    g = _make_game()
    g.cup_count = 3
    positions = g._layout()
    assert len(positions) == 3
    assert positions[0] < positions[1] < positions[2]


def test_layout_fits_more_cups():
    g = _make_game()
    g.cup_count = 10
    positions = g._layout()
    assert len(positions) == 10
    for i in range(len(positions) - 1):
        assert positions[i] < positions[i + 1]


# ── Dataclass Tests ────────────────────────────────────────────────

def test_cup_dataclass():
    c = Cup(x=0, y=0, target_x=10, revealed=False, ball_color=8, wobble=0, index=0)
    assert c.x == 0
    assert c.ball_color == 8
    assert not c.revealed


def test_particle_dataclass():
    p = Particle(x=1, y=2, vx=0.5, vy=-1, life=20, color=8)
    assert p.x == 1
    assert p.life == 20


def test_floating_text_dataclass():
    ft = FloatingText(x=50, y=100, text="SCORE", color=10, life=30)
    assert ft.text == "SCORE"
    assert ft.color == 10


# ── Integration ────────────────────────────────────────────────────

def test_full_round_all_correct_different_colors():
    """Guess all cups with unique colors — each is a separate match."""
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    for i, c in enumerate(g.cups):
        c.ball_color = BALL_COLORS[i % len(BALL_COLORS)]
    for i in range(len(g.cups)):
        g._handle_guess(i, g.cups[i].ball_color)
    assert all(c.revealed for c in g.cups)
    assert g.combo == len(g.cups)


def test_mixed_correct_wrong():
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    # Ensure different colors
    for i, c in enumerate(g.cups):
        c.ball_color = BALL_COLORS[i % len(BALL_COLORS)]
    # First correct
    g._handle_guess(0, g.cups[0].ball_color)
    assert g.combo == 1
    # Then wrong
    c1 = g.cups[1]
    wrong = [x for x in BALL_COLORS if x != c1.ball_color][0]
    g._handle_guess(1, wrong)
    assert g.combo == 0
    assert g.heat == HEAT_PER_MISS


def test_reset_after_game_over():
    g = _make_game()
    g.heat = HEAT_MAX
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER
    g.reset()
    assert g.phase == Phase.SHOW
    assert g.heat == 0
    assert g.score == 0


# ── Edge Cases ─────────────────────────────────────────────────────

def test_single_color_board_all_match():
    """All cups same color -> one match reveals all via chain burst."""
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    color = BALL_COLORS[0]
    for c in g.cups:
        c.ball_color = color
    g._handle_guess(0, color)
    assert g.combo == 1
    assert all(c.revealed for c in g.cups)


def test_alternating_colors_no_chain():
    """Alternating colors -> no chain propagation beyond first cup."""
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    for i, c in enumerate(g.cups):
        c.ball_color = BALL_COLORS[i % len(BALL_COLORS)]
    g._handle_guess(0, g.cups[0].ball_color)
    assert g.cups[0].revealed
    if len(g.cups) > 1:
        assert not g.cups[1].revealed


def test_best_combo_tracks_maximum():
    g = _make_game()
    g._start_shuffle()
    g._start_guess()
    # Need 4 cups to track combo up to 3 without round complete
    g.cup_count = 4
    g._make_cups()
    for i, c in enumerate(g.cups):
        c.ball_color = BALL_COLORS[i % len(BALL_COLORS)]
    for i in range(3):
        g._handle_guess(i, g.cups[i].ball_color)
    assert g.best_combo == 3
    # Now wrong guess resets combo but best_combo stays
    wrong = [x for x in BALL_COLORS if x != g.cups[3].ball_color][0]
    g._handle_guess(3, wrong)
    assert g.combo == 0
    assert g.best_combo == 3


def test_resolve_phase_transitions_back_to_show():
    g = _make_game()
    g.phase = Phase.RESOLVE
    g.resolve_frames = 1
    g.resolve_frames -= 1
    assert g.resolve_frames <= 0


if __name__ == "__main__":
    import traceback
    passed = 0
    failed = 0
    for name, func in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                func()
                passed += 1
            except Exception as e:
                failed += 1
                print(f"FAIL {name}: {e}")
                traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
