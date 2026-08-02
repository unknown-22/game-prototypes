"""test_imports.py — Headless logic tests for IDLE SURGE (271_idle_surge)."""
from __future__ import annotations

import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/271_idle_surge")
from main import (
    AUTO_TICK_INTERVAL,
    COLOR_CYAN,
    COLOR_DARK_BLUE,
    COLOR_LIME,
    COLOR_RED,
    COLOR_WHITE,
    COLOR_YELLOW,
    COMBO_THRESHOLD,
    FPS,
    GAME_DURATION,
    GEN_COLORS,
    HEAT_CAP,
    HEAT_DECAY_RATE,
    HEAT_MISMATCH,
    SCORE_BASE,
    SHIFT_DURATION,
    SUPER_DURATION,
    SUPER_MULT,
    WIDTH,
    HEIGHT,
    FloatingText,
    Game,
    Generator,
    Particle,
    Phase,
)


def _make_game() -> Game:
    """Create a Game instance without pyxel init for headless testing."""
    g = Game.__new__(Game)
    # Pre-init all instance attributes that reset() touches
    g._frame_count = 0
    g.generators = []
    g.combo = 0
    g.max_combo = 0
    g.score = 0
    g.best_score = 0
    g.heat = 0.0
    g.super_timer = 0
    g.super_mult = 1.0
    g.game_timer = 0
    g.shift_timer = 0
    g.active_color = -1
    g.particles = []
    g.floating_texts = []
    g.phase = Phase.PLAYING
    g._rng = random.Random(42)
    g.reset()
    return g


# ──────────────────────────────────────────────────────────────────
# Data class tests
# ──────────────────────────────────────────────────────────────────


def test_generator_defaults() -> None:
    gen = Generator(x=40, y=120, color=COLOR_RED)
    assert gen.x == 40
    assert gen.y == 120
    assert gen.w == 48
    assert gen.h == 48
    assert gen.color == COLOR_RED
    assert gen.clicks == 0
    assert gen.auto is False
    assert gen.auto_timer == 0
    assert gen.pulse == 0.0


def test_particle_creation() -> None:
    p = Particle(x=100.0, y=50.0, vx=1.5, vy=-2.0, color=COLOR_YELLOW, life=20)
    assert p.x == 100.0
    assert p.y == 50.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.color == COLOR_YELLOW
    assert p.life == 20
    assert p.size == 2


def test_floating_text_creation() -> None:
    ft = FloatingText(x=160.0, y=120.0, text="+10", color=COLOR_LIME, life=30)
    assert ft.text == "+10"
    assert ft.color == COLOR_LIME
    assert ft.life == 30
    assert ft.vy == -0.5


# ──────────────────────────────────────────────────────────────────
# Phase enum
# ──────────────────────────────────────────────────────────────────


def test_phase_values() -> None:
    assert Phase.TITLE is not None
    assert Phase.PLAYING is not None
    assert Phase.GAME_OVER is not None


# ──────────────────────────────────────────────────────────────────
# Reset / initialization
# ──────────────────────────────────────────────────────────────────


def test_reset_initial_state() -> None:
    g = _make_game()
    assert g.phase is Phase.PLAYING
    assert len(g.generators) == 4
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.score == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.super_mult == 1.0
    assert g.game_timer == GAME_DURATION
    assert g.shift_timer == SHIFT_DURATION
    assert g.active_color == -1
    assert g.particles == []
    assert g.floating_texts == []


def test_reset_clears_particles_and_texts() -> None:
    g = _make_game()
    g.particles.append(Particle(0, 0, 0, 0, 0, 10))
    g.floating_texts.append(FloatingText(0, 0, "test", 0, 10))
    g.reset()
    assert g.particles == []
    assert g.floating_texts == []


def test_reset_generator_positions() -> None:
    g = _make_game()
    # Expected positions: x=40,100,160,220 with y=120
    expected_x = [40, 100, 160, 220]
    for i, gen in enumerate(g.generators):
        assert gen.x == expected_x[i]
        assert gen.y == 120
        assert gen.color == GEN_COLORS[i]
        assert gen.clicks == 0
        assert gen.auto is False


# ──────────────────────────────────────────────────────────────────
# _find_gen_at (AABB hit-test)
# ──────────────────────────────────────────────────────────────────


def test_find_gen_hit_center() -> None:
    g = _make_game()
    gen = g._find_gen_at(40, 120)
    assert gen is not None
    assert gen.x == 40


def test_find_gen_miss_empty_space() -> None:
    g = _make_game()
    # Between gen 0 (16-64) and gen 1 (76-124): x=70 is empty
    gen = g._find_gen_at(70, 120)
    assert gen is None


def test_find_gen_edge_of_bounds() -> None:
    g = _make_game()
    # Left edge of gen[0]: x=40, w=48 → left=40-24=16
    gen = g._find_gen_at(16, 120)
    assert gen is not None
    assert gen.x == 40


def test_find_gen_outside_bounds() -> None:
    g = _make_game()
    # Just outside gen[0] left edge
    gen = g._find_gen_at(15, 120)
    assert gen is None


# ──────────────────────────────────────────────────────────────────
# _click_gen — matching color (COMBO chain)
# ──────────────────────────────────────────────────────────────────


def test_click_first_gen_sets_active_color_and_combo() -> None:
    g = _make_game()
    gen = g.generators[0]  # RED
    initial_score = g.score
    g.active_color = gen.color  # First click matches
    g._click_gen(gen)
    assert g.active_color == gen.color
    assert g.combo == 1
    assert g.score > initial_score


def test_click_same_color_builds_combo() -> None:
    g = _make_game()
    gen = g.generators[0]  # RED
    g.active_color = gen.color
    g._click_gen(gen)  # combo 1
    g._click_gen(gen)  # combo 2
    assert g.combo == 2
    assert g.active_color == gen.color


def test_click_wrong_color_resets_combo() -> None:
    g = _make_game()
    gen0 = g.generators[0]  # RED
    gen1 = g.generators[1]  # LIME
    g.active_color = gen0.color
    g._click_gen(gen0)  # combo 1
    assert g.combo == 1
    # Now click different color gen
    g._click_gen(gen1)  # should reset
    assert g.combo == 0
    assert g.active_color == gen1.color


def test_click_wrong_color_adds_heat() -> None:
    g = _make_game()
    gen0 = g.generators[0]  # RED
    gen1 = g.generators[1]  # LIME
    g.active_color = gen0.color  # RED active
    g._click_gen(gen1)  # LIME click → wrong!
    assert g.combo == 0
    assert g.heat == HEAT_MISMATCH
    assert g.active_color == gen1.color


# ──────────────────────────────────────────────────────────────────
# _click_gen — SUPER SURGE mode
# ──────────────────────────────────────────────────────────────────


def test_super_mode_any_color_matches() -> None:
    g = _make_game()
    gen0 = g.generators[0]  # RED
    gen1 = g.generators[1]  # LIME
    # Activate SUPER manually
    g.super_timer = SUPER_DURATION
    g.super_mult = SUPER_MULT
    g.active_color = gen0.color
    g._click_gen(gen0)  # RED click during SUPER
    combo_after_red = g.combo
    g._click_gen(gen1)  # LIME click during SUPER — should still match
    assert g.combo == combo_after_red + 1


def test_super_mode_3x_score() -> None:
    g = _make_game()
    gen = g.generators[0]
    g.super_timer = SUPER_DURATION
    g.super_mult = SUPER_MULT
    g.active_color = gen.color
    g.combo = 2
    initial_score = g.score
    g._click_gen(gen)
    # score = 10 * (1 + 2*0.5) * 3.0 = 10 * 2.0 * 3.0 = 60
    assert g.score - initial_score == 60


# ──────────────────────────────────────────────────────────────────
# SUPER trigger
# ──────────────────────────────────────────────────────────────────


def test_super_triggers_at_combo_threshold() -> None:
    g = _make_game()
    gen = g.generators[0]
    g.active_color = gen.color
    g.combo = COMBO_THRESHOLD - 1  # combo = 3
    # Next matching click should trigger SUPER
    g._click_gen(gen)
    assert g.super_timer == SUPER_DURATION
    assert g.super_mult == SUPER_MULT


def test_super_does_not_retrigger_if_already_active() -> None:
    g = _make_game()
    g.super_timer = 50
    g.super_mult = SUPER_MULT
    gen = g.generators[0]
    g.active_color = gen.color
    g.combo = COMBO_THRESHOLD
    g._click_gen(gen)
    assert g.super_timer == 50  # Unchanged, SUPER already active


# ──────────────────────────────────────────────────────────────────
# _update_timers
# ──────────────────────────────────────────────────────────────────


def test_game_timer_decrements() -> None:
    g = _make_game()
    initial = g.game_timer
    g._update_timers()
    assert g.game_timer == initial - 1


def test_game_timer_zero_triggers_game_over() -> None:
    g = _make_game()
    g.game_timer = 1
    g.best_score = 0
    g.score = 1000
    g._update_timers()
    assert g.phase is Phase.GAME_OVER
    assert g.best_score == 1000


def test_super_timer_decrements() -> None:
    g = _make_game()
    g.super_timer = 10
    g.super_mult = SUPER_MULT
    g._update_timers()
    assert g.super_timer == 9
    assert g.super_mult == SUPER_MULT  # Still active


def test_super_timer_expiry_resets_mult() -> None:
    g = _make_game()
    g.super_timer = 1
    g.super_mult = SUPER_MULT
    g._update_timers()
    assert g.super_timer == 0
    assert g.super_mult == 1.0


def test_shift_timer_triggers_auto_assign() -> None:
    g = _make_game()
    g.shift_timer = 1
    gen = g.generators[0]
    gen.clicks = 5
    g._update_timers()
    # shift_timer hit 0 → auto-assign triggered → timer reset
    assert g.shift_timer == SHIFT_DURATION
    assert gen.auto is True
    assert gen.auto_timer == AUTO_TICK_INTERVAL
    assert gen.clicks == 0  # All clicks reset


# ──────────────────────────────────────────────────────────────────
# _update_auto_gens
# ──────────────────────────────────────────────────────────────────


def test_auto_gen_ticks_produce_score() -> None:
    g = _make_game()
    gen = g.generators[0]
    gen.auto = True
    gen.auto_timer = 1
    g.combo = 0
    initial_score = g.score
    g._update_auto_gens()
    assert gen.auto_timer == AUTO_TICK_INTERVAL
    assert g.score > initial_score
    assert g.combo == 1


def test_non_auto_gen_does_not_tick() -> None:
    g = _make_game()
    gen = g.generators[0]
    gen.auto = False
    gen.auto_timer = 1
    g.combo = 0
    g._update_auto_gens()
    assert gen.auto_timer == 1  # Unchanged
    assert g.combo == 0


def test_auto_gen_builds_combo_chain() -> None:
    g = _make_game()
    gen = g.generators[0]
    gen.auto = True
    gen.auto_timer = 1
    g.combo = 0
    g._update_auto_gens()  # combo → 1
    gen.auto_timer = 1
    g._update_auto_gens()  # combo → 2
    assert g.combo == 2


# ──────────────────────────────────────────────────────────────────
# _update_super_surge_tick
# ──────────────────────────────────────────────────────────────────


def test_super_auto_tick_increments_combo() -> None:
    g = _make_game()
    g.super_timer = SUPER_DURATION
    g.super_mult = SUPER_MULT
    g.combo = 4
    # Frame set to a multiple of SUPER_AUTO_TICK
    g._frame_count = 15  # SUPER_AUTO_TICK = 15
    initial_score = g.score
    g._update_super_surge_tick()
    assert g.combo == 4 + len(g.generators)  # +4 (one per gen)
    assert g.score > initial_score


def test_super_auto_tick_skips_when_inactive() -> None:
    g = _make_game()
    g.super_timer = 0
    g.combo = 4
    g._frame_count = 15
    g._update_super_surge_tick()
    assert g.combo == 4  # Unchanged


def test_super_auto_tick_skips_off_frame() -> None:
    g = _make_game()
    g.super_timer = SUPER_DURATION
    g.combo = 4
    g._frame_count = 1  # Not a multiple of 15
    g._update_super_surge_tick()
    assert g.combo == 4  # Unchanged


# ──────────────────────────────────────────────────────────────────
# _update_heat
# ──────────────────────────────────────────────────────────────────


def test_heat_decays_when_no_auto_gens() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat < 50.0


def test_heat_auto_gens_add_heat() -> None:
    g = _make_game()
    g.heat = 50.0
    g.generators[0].auto = True
    g._update_heat()
    # Decay: -0.02, auto heat: +0.02 (1 auto gen)
    # Net: ~50.0 (equal)
    assert abs(g.heat - 50.0) < 0.01


def test_heat_capped_to_100() -> None:
    g = _make_game()
    g.heat = HEAT_CAP
    g._update_heat()
    # Heat should be clamped: max(0, min(100, heat))
    assert g.heat <= HEAT_CAP


def test_heat_at_cap_triggers_game_over() -> None:
    g = _make_game()
    g.heat = HEAT_CAP
    g.score = 500
    g.best_score = 0
    g._update_heat()
    assert g.phase is Phase.GAME_OVER
    assert g.best_score == 500


def test_heat_frozen_during_super() -> None:
    g = _make_game()
    g.super_timer = SUPER_DURATION
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 50.0  # Unchanged (frozen)


def test_heat_non_negative() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat >= 0.0


# ──────────────────────────────────────────────────────────────────
# _assign_auto
# ──────────────────────────────────────────────────────────────────


def test_assign_auto_highest_clicks() -> None:
    g = _make_game()
    g.generators[0].clicks = 10
    g.generators[1].clicks = 5
    g.generators[2].clicks = 7
    g.generators[3].clicks = 3
    g._assign_auto()
    assert g.generators[0].auto is True
    assert g.generators[0].auto_timer == AUTO_TICK_INTERVAL
    # Others unchanged
    assert g.generators[1].auto is False
    assert g.generators[2].auto is False
    assert g.generators[3].auto is False


def test_assign_auto_resets_all_clicks() -> None:
    g = _make_game()
    g.generators[0].clicks = 10
    g.generators[1].clicks = 5
    g._assign_auto()
    for gen in g.generators:
        assert gen.clicks == 0


def test_assign_auto_zero_clicks_does_nothing() -> None:
    g = _make_game()
    # All clicks = 0
    g._assign_auto()
    for gen in g.generators:
        assert gen.auto is False


def test_assign_auto_multiple_calls() -> None:
    g = _make_game()
    g.generators[0].clicks = 10
    g._assign_auto()
    assert g.generators[0].auto is True
    # Second shift: gen[1] gets most clicks
    g.generators[1].clicks = 15
    g._assign_auto()
    assert g.generators[1].auto is True
    assert g.generators[0].auto is True  # Still auto from before


# ──────────────────────────────────────────────────────────────────
# _update_particles
# ──────────────────────────────────────────────────────────────────


def test_particles_move_upward() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=100.0, vx=0.0, vy=-2.0, color=COLOR_RED, life=20)
    g.particles.append(p)
    g._update_particles()
    # vy was -2.0, vy -= 0.1 → vy = -2.1, y += vy → y = 97.9 (moves UP)
    assert p.y < 100.0
    assert p.life == 19


def test_particles_removed_when_life_expires() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, color=COLOR_RED, life=1)
    g.particles.append(p)
    g._update_particles()
    assert len(g.particles) == 0


# ──────────────────────────────────────────────────────────────────
# _update_floating_texts
# ──────────────────────────────────────────────────────────────────


def test_floating_texts_move_up() -> None:
    g = _make_game()
    ft = FloatingText(x=160.0, y=120.0, text="+10", color=COLOR_WHITE, life=30)
    g.floating_texts.append(ft)
    g._update_floating_texts()
    assert ft.y < 120.0  # vy=-0.5, so moves up
    assert ft.life == 29


def test_floating_texts_removed_when_life_expires() -> None:
    g = _make_game()
    ft = FloatingText(x=160.0, y=120.0, text="+10", color=COLOR_WHITE, life=1)
    g.floating_texts.append(ft)
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ──────────────────────────────────────────────────────────────────
# Scoring
# ──────────────────────────────────────────────────────────────────


def test_score_formula_combo_0() -> None:
    g = _make_game()
    gen = g.generators[0]  # RED
    g.active_color = gen.color
    g.combo = 0
    initial = g.score
    g._score_hit(gen)
    # SCORE_BASE * (1 + 0 * 0.5) * 1.0 = 10
    assert g.score - initial == 10


def test_score_formula_combo_3() -> None:
    g = _make_game()
    gen = g.generators[0]
    g.active_color = gen.color
    g.combo = 3
    initial = g.score
    g._score_hit(gen)
    # SCORE_BASE * (1 + 3 * 0.5) * 1.0 = 10 * 2.5 = 25
    assert g.score - initial == 25


def test_score_formula_super_mult() -> None:
    g = _make_game()
    gen = g.generators[0]
    g.super_mult = SUPER_MULT  # 3.0
    g.combo = 2
    initial = g.score
    g._score_hit(gen)
    # SCORE_BASE * (1 + 2 * 0.5) * 3.0 = 10 * 2.0 * 3.0 = 60
    assert g.score - initial == 60


# ──────────────────────────────────────────────────────────────────
# _click_gen score integration
# ──────────────────────────────────────────────────────────────────


def test_click_gen_match_scores_correctly() -> None:
    g = _make_game()
    gen = g.generators[0]
    g.active_color = gen.color
    g.combo = 1
    initial = g.score
    g._click_gen(gen)
    # _score_hit: 10 * (1 + 1*0.5) * 1.0 = 15
    assert g.score - initial == 15
    assert g.combo == 2


def test_click_gen_wrong_no_score() -> None:
    g = _make_game()
    gen0 = g.generators[0]  # RED
    gen1 = g.generators[1]  # LIME
    g.active_color = gen0.color
    g.combo = 3
    initial = g.score
    g._click_gen(gen1)  # Wrong!
    assert g.score == initial  # No score added
    assert g.combo == 0


# ──────────────────────────────────────────────────────────────────
# _spawn_click_particles (with seeded RNG)
# ──────────────────────────────────────────────────────────────────


def test_spawn_click_particles_creates_particles() -> None:
    g = _make_game()
    gen = g.generators[0]
    initial_count = len(g.particles)
    g._spawn_click_particles(gen)
    assert len(g.particles) > initial_count


def test_spawn_auto_particles_creates_particles() -> None:
    g = _make_game()
    gen = g.generators[0]
    initial_count = len(g.particles)
    g._spawn_auto_particles(gen)
    assert len(g.particles) > initial_count


# ──────────────────────────────────────────────────────────────────
# _spawn_floating_score / _spawn_combo_text
# ──────────────────────────────────────────────────────────────────


def test_spawn_floating_score_creates_text() -> None:
    g = _make_game()
    gen = g.generators[0]
    g.combo = 2
    g.super_mult = 1.0
    initial = len(g.floating_texts)
    g._spawn_floating_score(gen)
    assert len(g.floating_texts) == initial + 1
    ft = g.floating_texts[-1]
    assert ft.color == gen.color
    assert ft.life == 30
    # Score: 10 * (1 + 2*0.5) * 1.0 = 20
    assert ft.text == "+20"


def test_spawn_combo_text_creates_text() -> None:
    g = _make_game()
    gen = g.generators[0]
    g.combo = 3
    initial = len(g.floating_texts)
    g._spawn_combo_text(gen)
    assert len(g.floating_texts) == initial + 1
    ft = g.floating_texts[-1]
    assert ft.color == COLOR_YELLOW
    assert "COMBO" in ft.text


# ──────────────────────────────────────────────────────────────────
# Full game flow integration tests
# ──────────────────────────────────────────────────────────────────


def test_full_game_flow_to_game_over_by_timer() -> None:
    g = _make_game()
    g.game_timer = 10
    # Simulate frames
    gen = g.generators[0]
    g.active_color = gen.color
    for _ in range(10):
        g._update_timers()
    assert g.phase is Phase.GAME_OVER


def test_full_game_flow_to_game_over_by_heat() -> None:
    g = _make_game()
    g.heat = HEAT_CAP
    g._update_heat()
    assert g.phase is Phase.GAME_OVER


def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    gen = g.generators[0]
    g.active_color = gen.color
    # Build combo to 5 (triggers SUPER at combo>=4)
    for _ in range(5):
        g._click_gen(gen)
    assert g.max_combo == 5
    # Let SUPER expire
    g.super_timer = 0
    g.super_mult = 1.0
    # Now wrong click should reset combo
    gen1 = g.generators[1]
    g._click_gen(gen1)
    assert g.combo == 0
    assert g.max_combo == 5  # Max should remain


def test_constant_values() -> None:
    """Verify key constants are sane."""
    assert WIDTH == 320
    assert HEIGHT == 240
    assert FPS == 30
    assert SHIFT_DURATION == 900
    assert SUPER_DURATION == 150
    assert GAME_DURATION == 1800
    assert AUTO_TICK_INTERVAL == 30
    assert HEAT_CAP == 100.0
    assert HEAT_MISMATCH == 15.0
    assert COMBO_THRESHOLD == 4
    assert SUPER_MULT == 3.0
    assert len(GEN_COLORS) == 4


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
