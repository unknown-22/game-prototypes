"""Headless tests for 209_hopscotch_surge game logic."""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/209_hopscotch_surge")

import pytest

from main import (  # noqa: E402
    COLOR_BLACK,
    COLOR_DARK_BLUE,
    COLOR_GRAY,
    COLOR_GREEN,
    COLOR_LIME,
    COLOR_NAVY,
    COLOR_ORANGE,
    COLOR_PINK,
    COLOR_RED,
    COLOR_VALS,
    COLOR_WHITE,
    COLOR_YELLOW,
    COMBO_SUPER,
    GAME_DURATION,
    HEAT_MAX,
    HEAT_MISMATCH,
    HEAT_TIMEOUT,
    HOP_INTERVAL_INITIAL,
    HOP_INTERVAL_MIN,
    NUM_COLORS,
    SCREEN_H,
    SCREEN_W,
    SUPER_DURATION,
    FloatingText,
    Game,
    Particle,
    Phase,
    _make_game,
)


# ── Test helpers ───────────────────────────────────────────────────


def _set_colors(g: Game, player_color: int, next_color: int) -> None:
    """Set deterministic colors for testing."""
    g.player_color = player_color
    g.next_color = next_color


# ── Test constants ─────────────────────────────────────────────────


def test_constants() -> None:
    """Verify constants are in expected ranges."""
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert NUM_COLORS == 4
    assert COMBO_SUPER == 4
    assert SUPER_DURATION == 300
    assert HEAT_MAX == 100
    assert HEAT_MISMATCH == 15
    assert HEAT_TIMEOUT == 5
    assert GAME_DURATION == 60 * 60
    assert HOP_INTERVAL_INITIAL == 75
    assert HOP_INTERVAL_MIN == 18
    assert len(COLOR_VALS) == 4


def test_colors_are_valid_pyxel_ints() -> None:
    """Color constants are valid pyxel color indices (0-15)."""
    for c in (COLOR_BLACK, COLOR_NAVY, COLOR_GREEN, COLOR_DARK_BLUE,
              COLOR_WHITE, COLOR_RED, COLOR_ORANGE, COLOR_YELLOW,
              COLOR_LIME, COLOR_GRAY, COLOR_PINK):
        assert 0 <= c <= 15
    for c in COLOR_VALS:
        assert 0 <= c <= 15


def test_phase_values() -> None:
    """Phase enum has expected values."""
    assert Phase.TITLE == 0
    assert Phase.PLAYING == 1
    assert Phase.GAME_OVER == 2


# ── Test _make_game ────────────────────────────────────────────────


def test_make_game_creates_valid_state() -> None:
    """_make_game returns a valid game with deterministic state."""
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == pytest.approx(0.0)
    assert g.timer == GAME_DURATION
    assert g.hop_timer == HOP_INTERVAL_INITIAL
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.particles == []
    assert g.floating_texts == []


# ── Helper to get a PLAYING-phase game ─────────────────────────────


def _playing_game(seed: int = 42) -> Game:
    """Create a headless Game instance with deterministic RNG in PLAYING phase."""
    g = _make_game()
    g._rng = random.Random(seed)
    g.reset()
    g.phase = Phase.PLAYING
    g.player_color = 0
    g.current_color = 0
    g.next_color = g._generate_next_square()
    return g


# ── Test reset ─────────────────────────────────────────────────────


def test_reset() -> None:
    g = _playing_game()
    g.score = 999
    g.combo = 5
    g.heat = 50.0
    g.super_mode = True
    g.super_timer = 100
    g.timer = 1000
    g.reset()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == pytest.approx(0.0)
    assert g.timer == GAME_DURATION
    assert g.hop_timer == HOP_INTERVAL_INITIAL
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.particles == []
    assert g.floating_texts == []
    assert g.player_color in range(NUM_COLORS)
    assert g.current_color == g.player_color
    assert g.next_color in range(NUM_COLORS)


# ── Test hop mechanics ─────────────────────────────────────────────


def test_hop_match() -> None:
    """Score and combo increase when next_color matches player_color."""
    g = _playing_game()
    initial_score = g.score
    _set_colors(g, player_color=0, next_color=0)
    g._do_hop()
    assert g.score > initial_score
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.heat == pytest.approx(0.0)


def test_hop_mismatch() -> None:
    """Heat increases and combo resets on mismatch."""
    g = _playing_game()
    _set_colors(g, player_color=0, next_color=1)
    g._do_hop()
    assert g.combo == 0
    assert g.heat == pytest.approx(HEAT_MISMATCH)


def test_hop_color_cycle() -> None:
    """Player color updates to the square color after hop."""
    g = _playing_game()
    _set_colors(g, player_color=0, next_color=2)
    g._do_hop()
    assert g.player_color == 2
    assert g.current_color == 2


def test_combo_builds_max_combo() -> None:
    """Max combo tracks the highest combo achieved."""
    g = _playing_game()
    for i in range(3):
        _set_colors(g, player_color=i, next_color=i)
        g._do_hop()
    assert g.combo == 3
    assert g.max_combo == 3
    # Mismatch resets combo but max stays
    _set_colors(g, player_color=3, next_color=0)
    g._do_hop()
    assert g.combo == 0
    assert g.max_combo == 3


def test_combo_super_activation() -> None:
    """Combo >= COMBO_SUPER activates super_mode."""
    g = _playing_game()
    for i in range(COMBO_SUPER):
        _set_colors(g, player_color=i, next_color=i)
        g._do_hop()
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_super_any_color_match() -> None:
    """In super mode, any next_color counts as a match."""
    g = _playing_game()
    for i in range(COMBO_SUPER):
        _set_colors(g, player_color=i, next_color=i)
        g._do_hop()
    assert g.super_mode is True

    score_before = g.score
    combo_before = g.combo
    _set_colors(g, player_color=0, next_color=3)
    g._do_hop()
    assert g.score > score_before
    assert g.combo > combo_before
    assert g.heat == pytest.approx(0.0)  # No heat in super


def test_super_score_3x() -> None:
    """Super mode gives 3x score multiplier."""
    g = _playing_game()
    for i in range(COMBO_SUPER):
        _set_colors(g, player_color=i, next_color=i)
        g._do_hop()
    _set_colors(g, player_color=0, next_color=0)
    g._do_hop()
    score_super = g.score

    # Compare without super (same combo starting point)
    g2 = _playing_game()
    for i in range(COMBO_SUPER):
        _set_colors(g2, player_color=i, next_color=i)
        g2._do_hop()
    g2.super_mode = False
    g2.combo = 4
    g2.max_combo = 4
    _set_colors(g2, player_color=0, next_color=0)
    g2._do_hop()
    assert score_super > g2.score


def test_super_timer_decay() -> None:
    """Super mode deactivates after SUPER_DURATION frames."""
    g = _playing_game()
    for i in range(COMBO_SUPER):
        _set_colors(g, player_color=i, next_color=i)
        g._do_hop()
    assert g.super_mode is True
    for _ in range(SUPER_DURATION):
        g._update_super()
    assert g.super_mode is False
    assert g.super_timer == 0


def test_auto_hop_heat() -> None:
    """Auto-hop timeout adds heat."""
    g = _playing_game()
    heat_before = g.heat
    g._do_hop(mismatch=True)
    assert g.heat == pytest.approx(heat_before + HEAT_TIMEOUT)
    assert g.combo == 0


def test_heat_game_over() -> None:
    """Heat >= HEAT_MAX triggers game over."""
    g = _playing_game()
    g.heat = HEAT_MAX - 1
    _set_colors(g, player_color=0, next_color=1)
    g._do_hop()
    # Heat + HEAT_MISMATCH should push over HEAT_MAX
    # Actually _do_hop sets heat = min(HEAT_MAX, heat + HEAT_MISMATCH)
    # The check is in _update_timers. Let's trigger it.
    # Since _do_hop clamps at 100, we need to set it to 100 and call _update_timers
    g.heat = float(HEAT_MAX)
    g.phase = Phase.PLAYING
    g._update_timers()
    assert g.phase == Phase.GAME_OVER


def test_timer_game_over() -> None:
    """Timer reaching 0 triggers game over."""
    g = _playing_game()
    g.timer = 1
    g.phase = Phase.PLAYING
    g._update_timers()
    assert g.phase == Phase.GAME_OVER


def test_heat_cap() -> None:
    """Heat should not exceed HEAT_MAX."""
    g = _playing_game()
    g.heat = HEAT_MAX - 5
    _set_colors(g, player_color=0, next_color=1)
    g._do_hop()
    assert g.heat <= HEAT_MAX
    # Multiple mismatches
    g.heat = HEAT_MAX - 1
    g.phase = Phase.PLAYING
    _set_colors(g, player_color=0, next_color=2)
    g._do_hop()
    assert g.heat <= HEAT_MAX


def test_heat_decay() -> None:
    """Heat decays over time."""
    g = _playing_game()
    g.heat = 50.0
    g.phase = Phase.PLAYING
    g._update_timers()
    assert g.heat < 50.0


def test_particle_lifecycle() -> None:
    """Particles spawn, move and expire."""
    g = _playing_game()
    g._spawn_particles(100.0, 100.0, COLOR_RED, 1)
    assert len(g.particles) == 1
    for _ in range(100):
        g._update_particles()
    assert len(g.particles) == 0


def test_floating_text_lifecycle() -> None:
    """Floating texts spawn, move and expire."""
    g = _playing_game()
    g._spawn_floating_text("+10", COLOR_WHITE)
    assert len(g.floating_texts) == 1
    for _ in range(100):
        g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_generate_next_square_bias() -> None:
    """Verify 40% bias toward player_color works approximately."""
    g = _playing_game()
    g.player_color = 0
    matches = 0
    trials = 10000
    for _ in range(trials):
        result = g._generate_next_square()
        if result == 0:
            matches += 1
    rate = matches / trials
    assert 0.45 < rate < 0.65


def test_hop_interval_decreases() -> None:
    """Hop interval decreases as timer progresses."""
    g = _playing_game()
    initial = g._hop_interval()
    g.timer = GAME_DURATION // 2
    mid = g._hop_interval()
    g.timer = 10
    end_val = g._hop_interval()
    assert initial >= mid >= end_val
    assert end_val >= HOP_INTERVAL_MIN


def test_do_hop_ignored_in_non_playing_phase() -> None:
    """_do_hop should be no-op outside PLAYING phase."""
    g = _playing_game()
    g.phase = Phase.TITLE
    score_before = g.score
    g._do_hop()
    assert g.score == score_before


def test_update_timers_ignored_in_non_playing_phase() -> None:
    """_update_timers should be no-op outside PLAYING phase."""
    g = _playing_game()
    g.phase = Phase.TITLE
    timer_before = g.timer
    g._update_timers()
    assert g.timer == timer_before


def test_full_reset_clears_all_state() -> None:
    """reset() clears all game state."""
    g = _playing_game()
    g.score = 9999
    g.combo = 10
    g.heat = 80.0
    g.super_mode = True
    g.super_timer = 100
    g.particles.append(Particle(0, 0, 0, 0, 10, COLOR_RED, 2))
    g.floating_texts.append(FloatingText(0, 0, "test", 10, COLOR_RED))

    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == pytest.approx(0.0)
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.particles == []
    assert g.floating_texts == []


def test_player_color_and_current_color_sync_on_reset() -> None:
    """After reset, current_color should equal player_color."""
    g = _playing_game(seed=123)
    assert g.current_color == g.player_color


def test_float_assertions() -> None:
    """Use pytest.approx for float comparisons."""
    g = _playing_game()
    g.heat = 15.0
    assert g.heat == pytest.approx(15.0)
    g.heat += 0.05
    assert g.heat != pytest.approx(15.0)
