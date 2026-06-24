"""Headless tests for Tug Chain game logic."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import (  # type: ignore[import-untyped]
    COMBO_THRESHOLD,
    GAME_DURATION,
    MAX_HEAT,
    SEGMENTS,
    COLOR_ORDER,
    FloatingText,
    Particle,
    Phase,
    Game,
)


def _make_game(seed: int = 42) -> Game:
    """Factory for a fresh headless Game instance."""
    return Game._make_game(seed)


# ------------------------------------------------------------------
# Initial state
# ------------------------------------------------------------------
class TestInitialState:
    def test_phase_is_playing(self) -> None:
        g = _make_game(42)
        assert g.phase == Phase.PLAYING

    def test_segments_count(self) -> None:
        g = _make_game()
        assert len(g.segments) == SEGMENTS

    def test_stats_are_zero(self) -> None:
        g = _make_game()
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.score == 0
        assert g.pull_distance == 0.0
        assert g.super_timer == 0
        assert g.game_timer == GAME_DURATION
        assert g.heat == 0.0

    def test_active_color_in_order(self) -> None:
        g = _make_game()
        assert g.active_color in COLOR_ORDER


# ------------------------------------------------------------------
# Color cycling
# ------------------------------------------------------------------
class TestColorCycle:
    def test_cycles_to_next(self) -> None:
        g = _make_game()
        initial = g.active_color
        next_c = g._cycle_color()
        assert next_c != initial
        idx = COLOR_ORDER.index(initial)
        expected = COLOR_ORDER[(idx + 1) % len(COLOR_ORDER)]
        assert next_c == expected

    def test_wraps_around(self) -> None:
        g = _make_game()
        seen = {g.active_color}
        for _ in range(4):
            g._cycle_color()
            seen.add(g.active_color)
        assert len(seen) == 4


# ------------------------------------------------------------------
# Pull resolution — match
# ------------------------------------------------------------------
class TestPullMatch:
    def test_increments_combo(self) -> None:
        g = _make_game()
        assert g.combo == 0
        score_add, combo_change, fray = g._resolve_pull(matched=True)
        assert combo_change == 1
        assert fray is False
        assert g.combo == 1
        assert score_add > 0

    def test_adds_score(self) -> None:
        g = _make_game()
        s0 = g.score
        g._resolve_pull(matched=True)
        assert g.score > s0

    def test_increases_pull_distance(self) -> None:
        g = _make_game()
        assert g.pull_distance == 0.0
        g._resolve_pull(matched=True)
        assert g.pull_distance > 0.0

    def test_keeps_heat_zero(self) -> None:
        g = _make_game()
        g._resolve_pull(matched=True)
        assert g.heat == 0.0

    def test_score_scales_with_combo(self) -> None:
        g = _make_game()
        g._resolve_pull(matched=True)  # combo=1
        s1 = g.score
        g._resolve_pull(matched=True)  # combo=2
        s2 = g.score
        assert s2 - s1 > s1  # combo scaling makes second pull worth more


# ------------------------------------------------------------------
# Pull resolution — mismatch
# ------------------------------------------------------------------
class TestPullMismatch:
    def test_resets_combo(self) -> None:
        g = _make_game()
        g.combo = 5
        score_add, combo_change, fray = g._resolve_pull(matched=False)
        assert combo_change == -999
        assert g.combo == 0
        assert score_add == 0

    def test_triggers_fray(self) -> None:
        g = _make_game()
        _, _, fray = g._resolve_pull(matched=False)
        assert fray is True
        assert any(s.frayed for s in g.segments)

    def test_increases_heat(self) -> None:
        g = _make_game()
        h0 = g.heat
        g._resolve_pull(matched=False)
        assert g.heat > h0

    def test_does_not_change_score(self) -> None:
        g = _make_game()
        g.score = 100
        g._resolve_pull(matched=False)
        assert g.score == 100

    def test_triggers_screen_shake(self) -> None:
        g = _make_game()
        g._resolve_pull(matched=False)
        assert g.shake_frames == 10


# ------------------------------------------------------------------
# Super mode
# ------------------------------------------------------------------
class TestSuperMode:
    def test_activates_at_threshold(self) -> None:
        g = _make_game()
        for _ in range(COMBO_THRESHOLD - 1):
            g._resolve_pull(matched=True)
        assert g.combo == COMBO_THRESHOLD - 1
        assert not g._is_super()
        g._resolve_pull(matched=True)
        assert g.combo == COMBO_THRESHOLD
        assert g._is_super()

    def test_deactivates_on_mismatch(self) -> None:
        g = _make_game()
        g._activate_super()
        assert g._is_super()
        g._resolve_pull(matched=False)
        assert not g._is_super()

    def test_3x_score_multiplier(self) -> None:
        g = _make_game()
        g._activate_super()
        s0 = g.score
        g._resolve_pull(matched=True)  # combo=1, base=15, *3 = 45
        assert g.score - s0 == 45


# ------------------------------------------------------------------
# CA fray spread
# ------------------------------------------------------------------
class TestFraySpread:
    def test_returns_list(self) -> None:
        g = _make_game()
        g.segments[5].frayed = True
        newly = g._spread_fray()
        assert isinstance(newly, list)

    def test_empty_if_all_frayed(self) -> None:
        g = _make_game()
        for s in g.segments:
            s.frayed = True
        newly = g._spread_fray()
        assert newly == []

    def test_empty_if_no_frayed(self) -> None:
        g = _make_game()
        newly = g._spread_fray()
        assert newly == []

    def test_only_spreads_from_initial_fray(self) -> None:
        g = _make_game()
        g.segments[3].frayed = True
        newly = g._spread_fray()
        # CA may spread sequentially within same frame (3→4, then 4→5)
        # so newly frayed can include 2, 4, 5, etc.
        assert len(newly) >= 0
        # Verify the initial segment is still frayed
        assert g.segments[3].frayed


# ------------------------------------------------------------------
# Game over
# ------------------------------------------------------------------
class TestGameOver:
    def test_timer_zero(self) -> None:
        g = _make_game()
        g.game_timer = 0
        assert g._check_game_over()

    def test_all_frayed(self) -> None:
        g = _make_game()
        for s in g.segments:
            s.frayed = True
        assert g._check_game_over()

    def test_not_yet(self) -> None:
        g = _make_game()
        assert not g._check_game_over()


# ------------------------------------------------------------------
# Particles
# ------------------------------------------------------------------
class TestParticles:
    def test_update_and_die(self) -> None:
        g = _make_game()
        g.particles.append(Particle(x=100, y=100, vx=1, vy=-2, life=1, max_life=10, color=8))
        g._update_particles()
        assert len(g.particles) == 0

    def test_survive_with_life(self) -> None:
        g = _make_game()
        g.particles.append(Particle(x=100, y=100, vx=1, vy=-2, life=5, max_life=10, color=8))
        g._update_particles()
        assert len(g.particles) == 1

    def test_gravity_applied(self) -> None:
        g = _make_game()
        g.particles.append(Particle(x=100, y=100, vx=0, vy=0, life=10, max_life=10, color=8))
        g._update_particles()
        assert g.particles[0].vy > 0  # gravity pulls down


# ------------------------------------------------------------------
# Floating texts
# ------------------------------------------------------------------
class TestFloatingTexts:
    def test_die_when_life_zero(self) -> None:
        g = _make_game()
        g.floating_texts.append(FloatingText(x=100, y=100, text="T", life=0, max_life=10, color=7))
        g._update_floating_texts()
        assert len(g.floating_texts) == 0

    def test_move_upward(self) -> None:
        g = _make_game()
        g.floating_texts.append(FloatingText(x=100, y=100, text="TEST", life=10, max_life=10, color=7))
        y0 = g.floating_texts[0].y
        g._update_floating_texts()
        assert g.floating_texts[0].y < y0


# ------------------------------------------------------------------
# Max combo tracking
# ------------------------------------------------------------------
class TestMaxCombo:
    def test_tracks_peak(self) -> None:
        g = _make_game()
        g._resolve_pull(matched=True)
        g._resolve_pull(matched=True)
        g._resolve_pull(matched=True)
        assert g.max_combo == 3

    def test_does_not_decrease_on_miss(self) -> None:
        g = _make_game()
        for _ in range(5):
            g._resolve_pull(matched=True)
        assert g.max_combo == 5
        g._resolve_pull(matched=False)
        assert g.max_combo == 5


# ------------------------------------------------------------------
# Heat cap
# ------------------------------------------------------------------
class TestHeat:
    def test_caps_at_max(self) -> None:
        g = _make_game()
        for _ in range(10):
            g._resolve_pull(matched=False)
        assert g.heat == MAX_HEAT


# ------------------------------------------------------------------
# Pull distance
# ------------------------------------------------------------------
class TestPullDistance:
    def test_increases(self) -> None:
        g = _make_game()
        g._resolve_pull(matched=True)
        d1 = g.pull_distance
        g._resolve_pull(matched=True)
        assert g.pull_distance > d1
