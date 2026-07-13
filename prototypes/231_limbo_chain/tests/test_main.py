"""Tests for Limbo Chain — color-match limbo dance game."""
from __future__ import annotations

import random
import sys
from unittest import mock

# Mock pyxel before importing main
_mock_pyxel = mock.MagicMock()
_mock_pyxel.btnp.return_value = False
_mock_pyxel.btn.return_value = False
for attr in (
    "KEY_SPACE", "KEY_RETURN", "KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT",
    "MOUSE_BUTTON_LEFT", "MOUSE_BUTTON_RIGHT", "MOUSE_BUTTON_MIDDLE",
):
    setattr(_mock_pyxel, attr, 0)
sys.modules["pyxel"] = _mock_pyxel

# Now safe to import
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/231_limbo_chain")

from main import (  # noqa: E402
    ATTEMPT_INTERVAL_INITIAL,
    ATTEMPT_INTERVAL_MIN,
    BAR_DESCENT,
    BAR_INITIAL_Y,
    BAR_MIN_Y,
    BAR_RAISE_ON_SUPER,
    BASE_SCORE,
    COLORS,
    COLOR_CYCLE_INTERVAL,
    FloatingText,
    GAME_DURATION,
    Game,
    HEAT_BAR_HIT,
    HEAT_DECAY,
    HEAT_MAX,
    HEAT_MISMATCH,
    Particle,
    Phase,
    SUPER_DURATION,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g._init_state()
    g.rng = random.Random(seed)
    return g


# ------------------------------------------------------------------ 1
def test_first_duck_succeeds_without_color_match() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.last_duck_color = None
    g.bar_color = COLORS[0]

    combo, matched, triggered_super = g._process_duck()

    assert matched is False
    assert triggered_super is False
    assert combo == 0
    assert g.score == BASE_SCORE
    assert g.last_duck_color == COLORS[0]


# ------------------------------------------------------------------ 2
def test_same_color_consecutive_ducks_build_combo() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.last_duck_color = COLORS[0]
    g.bar_color = COLORS[0]

    combo, matched, triggered_super = g._process_duck()

    assert matched is True
    assert triggered_super is False
    assert g.combo == 1
    assert g.score == BASE_SCORE * 1


# ------------------------------------------------------------------ 3
def test_wrong_color_duck_resets_combo_and_adds_heat() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 3
    g.heat = 10.0
    g.last_duck_color = COLORS[0]
    g.bar_color = COLORS[1]

    combo, matched, triggered_super = g._process_duck()

    assert matched is False
    assert triggered_super is False
    assert g.combo == 0
    assert g.heat == 10.0 + HEAT_MISMATCH
    assert g.score == BASE_SCORE  # base score only
    assert g.last_duck_color == COLORS[1]


# ------------------------------------------------------------------ 4
def test_combo_4_triggers_super_mode() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.bar_y = 120.0  # bar has descended somewhat
    g.combo = 3
    g.last_duck_color = COLORS[0]
    g.bar_color = COLORS[0]
    old_bar_y = g.bar_y

    combo, matched, triggered_super = g._process_duck()

    assert matched is True
    assert triggered_super is True
    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION
    # bar raised + descent: 120 + 15 - 0.6 = 134.4 > 120
    assert g.bar_y > old_bar_y


# ------------------------------------------------------------------ 5
def test_super_mode_auto_matches() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_mode = True
    g.super_timer = SUPER_DURATION
    g.combo = 5
    g.score = 100
    g.last_duck_color = COLORS[0]
    g.bar_color = COLORS[2]  # different color
    old_bar_y = g.bar_y

    g._auto_duck()

    assert g.combo == 6
    assert g.score > 100  # scored 3x
    assert g.last_duck_color == COLORS[2]
    assert g.bar_y < old_bar_y  # bar descends


# ------------------------------------------------------------------ 6
def test_super_mode_raises_bar() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 3
    g.last_duck_color = COLORS[0]
    g.bar_color = COLORS[0]
    g.bar_y = 100.0
    g._process_duck()

    # bar raised to 100+15=115, then descent: 115 - 0.6 = 114.4
    assert g.bar_y == min(BAR_INITIAL_Y, 100.0 + BAR_RAISE_ON_SUPER) - BAR_DESCENT


# ------------------------------------------------------------------ 7
def test_heat_max_causes_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 2
    g.heat = HEAT_MAX - 1
    g.last_duck_color = COLORS[0]
    g.bar_color = COLORS[1]  # mismatch

    g._process_duck()

    assert g.heat >= HEAT_MAX
    assert g.phase == Phase.GAME_OVER


# ------------------------------------------------------------------ 8
def test_timer_zero_causes_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.timer = 1

    g._update_playing()

    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER


# ------------------------------------------------------------------ 9
def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.last_duck_color = COLORS[0]
    g.bar_color = COLORS[0]

    # Build combo to 3
    g.combo = 0
    g._process_duck()  # combo 1
    g._process_duck()  # combo 2
    g._process_duck()  # combo 3
    assert g.max_combo == 3

    # Mismatch resets combo but max stays
    g.bar_color = COLORS[1]
    g._process_duck()  # reset
    assert g.combo == 0
    assert g.max_combo == 3


# ------------------------------------------------------------------ 10
def test_bar_descends_after_each_duck() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.bar_y = 150.0
    g.last_duck_color = COLORS[0]
    g.bar_color = COLORS[0]

    g._process_duck()

    assert g.bar_y == 150.0 - BAR_DESCENT


# ------------------------------------------------------------------ 11
def test_color_cycles_correctly() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.bar_color = COLORS[0]
    g.color_cycle_timer = 1

    g._update_playing()

    assert g.bar_color == COLORS[1]
    assert g.color_cycle_timer > 0


# ------------------------------------------------------------------ 12
def test_score_calculation_base_times_combo() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.last_duck_color = COLORS[0]
    g.bar_color = COLORS[0]
    g.combo = 4  # 5th duck will be combo 5

    old_score = g.score
    g._process_duck()

    assert g.score == old_score + BASE_SCORE * 5  # BASE * combo (5)


# ------------------------------------------------------------------ 13
def test_super_mode_prevents_game_over_from_heat() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_mode = True
    g.super_timer = SUPER_DURATION
    g.last_duck_color = COLORS[0]
    g.bar_color = COLORS[1]  # mismatch

    g.heat = HEAT_MAX
    g._process_duck()

    assert g.phase == Phase.PLAYING  # not game over because SUPER


# ------------------------------------------------------------------ 14
def test_init_state_resets_all() -> None:
    g = _make_game()
    g.best_score = 500  # explicitly set so hasattr is True
    g.phase = Phase.PLAYING
    g.score = 1000
    g.combo = 10
    g.max_combo = 10
    g.heat = 80.0
    g.timer = 100
    g.bar_y = 50.0
    g.bar_color = COLORS[2]
    g.color_cycle_timer = 30
    g.player_ducking = True
    g.player_duck_timer = 5
    g.player_cooldown = 3
    g.super_mode = True
    g.super_timer = 150
    g.last_duck_color = COLORS[1]
    g.attempt_timer = 20
    g.particles = [Particle(0, 0, 0, 0, 10, 8)]
    g.floating_texts = [FloatingText(0, 0, "test", 10, 7)]
    g._shake_frames = 5

    g._init_state()

    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == GAME_DURATION
    assert g.bar_y == BAR_INITIAL_Y
    assert g.bar_color == COLORS[0]
    assert g.color_cycle_timer == COLOR_CYCLE_INTERVAL
    assert g.player_ducking is False
    assert g.player_duck_timer == 0
    assert g.player_cooldown == 0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.last_duck_color is None
    assert g.attempt_timer == ATTEMPT_INTERVAL_INITIAL
    assert g.particles == []
    assert g.floating_texts == []
    assert g.best_score == 500  # best_score is NOT reset (carried over)
    assert g._shake_frames == 0


# ------------------------------------------------------------------ 15
def test_difficulty_escalation_interval_decreases() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING

    # Full time remaining -> interval should be large
    g.timer = GAME_DURATION
    g._reset_attempt(0.0)
    assert g.attempt_timer == ATTEMPT_INTERVAL_INITIAL

    # Half time elapsed -> interval should be medium
    g._reset_attempt(0.5)
    mid = int(ATTEMPT_INTERVAL_INITIAL - (ATTEMPT_INTERVAL_INITIAL - ATTEMPT_INTERVAL_MIN) * 0.5)
    assert g.attempt_timer == mid

    # Near end -> interval should be at minimum
    g._reset_attempt(0.95)
    assert g.attempt_timer < ATTEMPT_INTERVAL_INITIAL
    assert g.attempt_timer >= ATTEMPT_INTERVAL_MIN


# ------------------------------------------------------------------ 16
def test_attempt_timer_capped_at_min() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._reset_attempt(1.0)
    assert g.attempt_timer == ATTEMPT_INTERVAL_MIN


# ------------------------------------------------------------------ 17
def test_bar_y_does_not_go_below_min() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.bar_y = BAR_MIN_Y + 0.1
    g.last_duck_color = COLORS[0]
    g.bar_color = COLORS[0]

    g._process_duck()

    assert g.bar_y == BAR_MIN_Y


# ------------------------------------------------------------------ 18
def test_bar_y_does_not_exceed_initial_on_super() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.bar_y = BAR_INITIAL_Y - 5  # 175.0
    g.combo = 3
    g.last_duck_color = COLORS[0]
    g.bar_color = COLORS[0]

    g._process_duck()

    # bar raised to 175+15=190, capped at 180, then descent: 180-0.6=179.4
    assert g.bar_y == BAR_INITIAL_Y - BAR_DESCENT


# ------------------------------------------------------------------ 19
def test_on_bar_hit_adds_heat_and_resets_combo() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 3
    g.heat = 20.0

    g._on_bar_hit()

    assert g.combo == 0
    assert g.heat == 20.0 + HEAT_BAR_HIT


# ------------------------------------------------------------------ 20
def test_bar_hit_with_max_heat_causes_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = HEAT_MAX - 1

    g._on_bar_hit()

    assert g.heat >= HEAT_MAX
    assert g.phase == Phase.GAME_OVER


# ------------------------------------------------------------------ 21
def test_super_mode_deactivation_checks_heat() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_mode = True
    g.super_timer = 1
    g.heat = HEAT_MAX + 1.0  # enough that even after decay it's >= HEAT_MAX

    g._update_playing()

    assert g.super_mode is False
    assert g.phase == Phase.GAME_OVER


# ------------------------------------------------------------------ 22
def test_heat_decays_per_frame() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 50.0
    g.timer = GAME_DURATION

    g._update_playing()

    assert g.heat == 50.0 - HEAT_DECAY


# ------------------------------------------------------------------ 23
def test_heat_does_not_go_below_zero() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 0.001

    g._update_playing()

    assert g.heat == 0.0


# ------------------------------------------------------------------ 24
def test_super_mode_all_colors_match() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_mode = True
    g.super_timer = SUPER_DURATION
    g.last_duck_color = COLORS[0]
    g.bar_color = COLORS[3]  # completely different color

    combo, matched, triggered_super = g._process_duck()

    assert matched is True
    assert g.combo > 0


# ------------------------------------------------------------------ 25
def test_particles_spawn_and_expire() -> None:
    g = _make_game()
    g._spawn_combo_particles(COLORS[0], 5)
    assert len(g.particles) == 5

    for _ in range(50):
        g._update_particles()
    assert len(g.particles) == 0


# ------------------------------------------------------------------ 26
def test_floating_texts_spawn_and_expire() -> None:
    g = _make_game()
    g._spawn_floating_text("test", 100, 100, 7)
    assert len(g.floating_texts) == 1

    for _ in range(50):
        g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ------------------------------------------------------------------ 27
def test_phase_transitions_title_to_playing() -> None:
    g = _make_game()
    g.phase = Phase.TITLE

    # Simulate SPACE press by calling _init_state + phase change
    g._init_state()
    g.phase = Phase.PLAYING

    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0


# ------------------------------------------------------------------ 28
def test_phase_transitions_playing_to_game_over_on_heat() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = HEAT_MAX
    g.last_duck_color = COLORS[0]
    g.bar_color = COLORS[1]

    g._process_duck()

    assert g.phase == Phase.GAME_OVER


# ------------------------------------------------------------------ 29
def test_phase_transitions_game_over_to_playing() -> None:
    g = _make_game()
    g.best_score = 100
    g.phase = Phase.GAME_OVER
    g.score = 200

    # Simulate SPACE press on game over
    g.best_score = max(g.best_score, g.score)
    g._init_state()
    g.phase = Phase.PLAYING

    assert g.best_score == 200
    assert g.phase == Phase.PLAYING
    assert g.score == 0
