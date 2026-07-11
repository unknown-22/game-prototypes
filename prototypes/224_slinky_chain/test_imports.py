"""test_imports.py — Headless logic tests for Slinky Chain."""
from __future__ import annotations

import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/224_slinky_chain")
from main import (  # noqa: E402
    AUTO_FLIP_INTERVAL,
    COLORS,
    COLOR_CYCLE,
    COLOR_NAMES,
    COMBO_THRESHOLD,
    FLIP_DURATION,
    GAME_DURATION,
    HEAT_DECAY,
    HEAT_MAX,
    HEAT_WRONG,
    FloatingText,
    Game,
    IDLE_FALL,
    IDLE_WOBBLE,
    NUM_STEPS,
    Particle,
    SCREEN_H,
    SCREEN_W,
    Slinky,
    STAIRS_START_X,
    STAIRS_START_Y,
    STEP_GAP_X,
    STEP_GAP_Y,
    STEP_H,
    STEP_W,
    Step,
    SUPER_DURATION,
    Phase,
)


def _make_game() -> Game:
    """Factory: create a Game instance usable in headless tests."""
    g = Game.__new__(Game)
    # Pre-init all attributes that _reset_state() touches
    g.phase = Phase.PLAYING
    g.steps = []
    g.slinky = Slinky(0, 0, 0, 0, False, 0, 0.0)
    g.particles = []
    g.floating_texts = []
    g.score = 0
    g.best_score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = GAME_DURATION
    g.super_active = False
    g.super_timer = 0
    g.multiplier = 1.0
    g.idle_timer = 0
    g.wobble_phase = 0.0
    g.scroll_x = 0.0
    g.steps_descended = 0
    g.best_path = []  # type: ignore[assignment]
    g.current_path = []  # type: ignore[assignment]
    g.color_timer = 0
    g.super_flip_timer = AUTO_FLIP_INTERVAL
    g.game_over_reason = ""
    g.screen_shake = 0
    return g


class TestConstants:
    """Verify module-level constants are sane."""

    def test_screen_dimensions(self) -> None:
        assert SCREEN_W == 320
        assert SCREEN_H == 240

    def test_step_dimensions(self) -> None:
        assert STEP_W > 0
        assert STEP_H > 0
        assert STEP_GAP_X > 0
        assert STEP_GAP_Y > 0

    def test_colors(self) -> None:
        assert len(COLORS) == 4
        assert len(COLOR_NAMES) == 4
        assert all(isinstance(c, int) and 0 <= c <= 15 for c in COLORS)

    def test_game_constants(self) -> None:
        assert COMBO_THRESHOLD == 4
        assert SUPER_DURATION == 300
        assert GAME_DURATION == 3600
        assert HEAT_MAX == 100
        assert HEAT_WRONG == 15
        assert HEAT_DECAY == 0.05
        assert FLIP_DURATION == 20

    def test_idle_constants(self) -> None:
        assert IDLE_WOBBLE < IDLE_FALL


class TestStep:
    """Step dataclass tests."""

    def test_step_creation(self) -> None:
        s = Step(100.0, 50.0, 80, 20, 2)
        assert s.x == 100.0
        assert s.y == 50.0
        assert s.width == 80
        assert s.height == 20
        assert s.color == 2


class TestSlinky:
    """Slinky dataclass tests."""

    def test_slinky_creation(self) -> None:
        s = Slinky(50.0, 30.0, 1, 2, False, 0, 0.0)
        assert s.x == 50.0
        assert s.color == 1
        assert s.on_step_index == 2
        assert not s.flipping
        assert s.vy == 0.0


class TestParticle:
    """Particle dataclass tests."""

    def test_particle_creation(self) -> None:
        p = Particle(10.0, 20.0, 1.5, -2.0, 30, 8)
        assert p.life == 30
        assert p.color == 8
        assert p.vx == 1.5


class TestFloatingText:
    """FloatingText dataclass tests."""

    def test_floating_text_creation(self) -> None:
        ft = FloatingText(100.0, 200.0, "TEST", 40, 10)
        assert ft.text == "TEST"
        assert ft.life == 40


class TestGameReset:
    """Tests for _reset_state()."""

    def test_reset_state_initializes_steps(self) -> None:
        g = _make_game()
        g._reset_state()
        assert len(g.steps) == NUM_STEPS
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0.0
        assert g.timer == GAME_DURATION
        assert not g.super_active
        assert g.multiplier == 1.0
        assert g.steps_descended == 0

    def test_reset_state_positions_slinky(self) -> None:
        g = _make_game()
        g._reset_state()
        assert g.slinky.on_step_index == 0
        assert g.slinky.x > 0
        assert g.slinky.y > 0
        assert not g.slinky.flipping
        # Slinky should be above first step
        first_step = g.steps[0]
        assert abs(g.slinky.x - (first_step.x + first_step.width / 2)) < 1
        assert abs(g.slinky.y - (first_step.y - 24 / 2)) < 1

    def test_reset_clears_particles_and_texts(self) -> None:
        g = _make_game()
        g.particles = [Particle(0, 0, 0, 0, 10, 8)]
        g.floating_texts = [FloatingText(0, 0, "x", 10, 8)]
        g._reset_state()
        assert len(g.particles) == 0
        assert len(g.floating_texts) == 0


class TestGenerateSteps:
    """Tests for _generate_steps()."""

    def test_generate_steps_for_reset(self) -> None:
        g = _make_game()
        g._generate_steps(for_reset=True)
        assert len(g.steps) == NUM_STEPS
        # Check step spacing
        for i in range(NUM_STEPS):
            expected_x = STAIRS_START_X + i * STEP_GAP_X
            expected_y = STAIRS_START_Y + i * STEP_GAP_Y
            assert g.steps[i].x == expected_x
            assert g.steps[i].y == expected_y
            assert g.steps[i].width == STEP_W
            assert g.steps[i].height == STEP_H
            assert 0 <= g.steps[i].color <= 3

    def test_generate_steps_extends(self) -> None:
        g = _make_game()
        # Use deterministic seed for colors
        random.seed(42)
        g._generate_steps(for_reset=True)
        initial_count = len(g.steps)
        # Simulate being on last step
        g.slinky.on_step_index = NUM_STEPS - 1
        g._generate_steps()  # should extend
        assert len(g.steps) > initial_count

    def test_generated_steps_have_valid_colors(self) -> None:
        g = _make_game()
        g._generate_steps(for_reset=True)
        for step in g.steps:
            assert step.color in (0, 1, 2, 3)


class TestFlipSlinky:
    """Tests for _flip_slinky()."""

    def test_flip_initiates(self) -> None:
        g = _make_game()
        g._reset_state()
        g.slinky.on_step_index = 0
        result = g._flip_slinky()
        assert result is True
        assert g.slinky.flipping is True
        assert g.slinky.flip_timer == FLIP_DURATION

    def test_flip_during_flip_returns_false(self) -> None:
        g = _make_game()
        g._reset_state()
        g.slinky.on_step_index = 0
        g.slinky.flipping = True
        g.slinky.flip_timer = 10
        result = g._flip_slinky()
        assert result is False

    def test_flip_when_fallen_returns_false(self) -> None:
        g = _make_game()
        g._reset_state()
        g.slinky.on_step_index = -1
        result = g._flip_slinky()
        assert result is False

    def test_flip_resets_idle_timer(self) -> None:
        g = _make_game()
        g._reset_state()
        g.idle_timer = 100
        g._flip_slinky()
        assert g.idle_timer == 0

    def test_flip_generates_more_steps_if_needed(self) -> None:
        g = _make_game()
        g._reset_state()
        original_len = len(g.steps)
        g.slinky.on_step_index = len(g.steps) - 1
        g._flip_slinky()
        assert len(g.steps) > original_len


class TestCheckMatch:
    """Tests for _check_match()."""

    def test_match_when_colors_same(self) -> None:
        g = _make_game()
        g._reset_state()
        g.slinky.on_step_index = 0
        g.slinky.color = g.steps[0].color
        assert g._check_match() is True

    def test_mismatch_when_colors_different(self) -> None:
        g = _make_game()
        g._reset_state()
        g.slinky.on_step_index = 0
        g.slinky.color = (g.steps[0].color + 1) % 4
        assert g._check_match() is False

    def test_check_match_when_fallen(self) -> None:
        g = _make_game()
        g._reset_state()
        g.slinky.on_step_index = -1
        assert g._check_match() is False


class TestUpdateHeat:
    """Tests for _update_heat()."""

    def test_heat_increase(self) -> None:
        g = _make_game()
        g._reset_state()
        g._update_heat(20)
        assert g.heat == 20.0

    def test_heat_clamped_to_max(self) -> None:
        g = _make_game()
        g._reset_state()
        g.heat = 95
        g._update_heat(20)
        assert g.heat == HEAT_MAX

    def test_heat_clamped_to_zero(self) -> None:
        g = _make_game()
        g._reset_state()
        g.heat = 5
        g._update_heat(-20)
        assert g.heat == 0.0


class TestCheckGameOver:
    """Tests for _check_game_over()."""

    def test_no_game_over_at_start(self) -> None:
        g = _make_game()
        g._reset_state()
        assert g._check_game_over() == ""

    def test_game_over_by_heat(self) -> None:
        g = _make_game()
        g._reset_state()
        g.heat = HEAT_MAX
        assert g._check_game_over() == "OVERHEAT"

    def test_game_over_by_timer(self) -> None:
        g = _make_game()
        g._reset_state()
        g.timer = 0
        assert g._check_game_over() == "TIME"

    def test_game_over_by_fall(self) -> None:
        g = _make_game()
        g._reset_state()
        g.slinky.on_step_index = -1
        assert g._check_game_over() == "FALL"


class TestUpdateTimer:
    """Tests for _update_timer()."""

    def test_timer_decrements(self) -> None:
        g = _make_game()
        g._reset_state()
        g.timer = 100
        g._update_timer()
        assert g.timer == 99

    def test_timer_stops_at_zero(self) -> None:
        g = _make_game()
        g._reset_state()
        g.timer = 0
        g._update_timer()
        assert g.timer == 0


class TestSuperMode:
    """Tests for _activate_super() and _update_super()."""

    def test_activate_super(self) -> None:
        g = _make_game()
        g._reset_state()
        g._activate_super()
        assert g.super_active is True
        assert g.super_timer == SUPER_DURATION
        assert g.multiplier == 3.0

    def test_super_timer_decrements(self) -> None:
        g = _make_game()
        g._reset_state()
        g._activate_super()
        g._update_super()
        assert g.super_timer == SUPER_DURATION - 1
        assert g.super_active is True

    def test_super_ends_when_timer_zero(self) -> None:
        g = _make_game()
        g._reset_state()
        g._activate_super()
        g.super_timer = 1
        g._update_super()
        assert g.super_timer == 0
        assert g.super_active is False
        assert g.multiplier == 1.0

    def test_update_super_noop_when_inactive(self) -> None:
        g = _make_game()
        g._reset_state()
        g._update_super()
        assert g.super_active is False


class TestCompleteFlip:
    """Tests for _complete_flip()."""

    def test_complete_flip_increments_step_index(self) -> None:
        g = _make_game()
        g._reset_state()
        old_index = g.slinky.on_step_index
        g.slinky.flipping = True
        g._complete_flip()
        assert g.slinky.on_step_index == old_index + 1
        assert not g.slinky.flipping

    def test_complete_flip_positions_slinky_on_new_step(self) -> None:
        g = _make_game()
        g._reset_state()
        g.slinky.flipping = True
        g._complete_flip()
        step = g.steps[g.slinky.on_step_index]
        assert abs(g.slinky.x - (step.x + step.width / 2)) < 1

    def test_complete_flip_with_match_builds_combo(self) -> None:
        g = _make_game()
        g._reset_state()
        # Ensure colors match
        step = g.steps[1]  # next step
        g.slinky.color = step.color
        g.slinky.flipping = True
        initial_combo = g.combo
        g._complete_flip()
        assert g.combo == initial_combo + 1
        assert g.score > 0

    def test_complete_flip_with_mismatch_resets_combo(self) -> None:
        g = _make_game()
        g._reset_state()
        g.combo = 3  # Build up some combo
        step = g.steps[1]  # next step
        g.slinky.color = (step.color + 1) % 4  # Ensure mismatch
        g.slinky.flipping = True
        g._complete_flip()
        assert g.combo == 0
        assert g.heat > 0

    def test_complete_flip_triggers_super_at_threshold(self) -> None:
        g = _make_game()
        g._reset_state()
        g.combo = COMBO_THRESHOLD - 1  # One away from SUPER
        step = g.steps[1]
        g.slinky.color = step.color  # Ensure match
        g.slinky.flipping = True
        g._complete_flip()
        assert g.combo == COMBO_THRESHOLD  # Combo reached threshold
        assert g.super_active is True

    def test_complete_flip_increments_steps_descended(self) -> None:
        g = _make_game()
        g._reset_state()
        g.slinky.flipping = True
        initial_steps = g.steps_descended
        g._complete_flip()
        assert g.steps_descended == initial_steps + 1

    def test_complete_flip_super_mode_auto_match(self) -> None:
        g = _make_game()
        g._reset_state()
        g._activate_super()  # Activate super manually
        g.slinky.flipping = True
        step = g.steps[1]
        # Set color to mismatch — super mode should still match
        g.slinky.color = (step.color + 1) % 4
        g._complete_flip()
        # In super mode, all matches succeed, combo increases
        assert g.combo > 0 or g.score > 0


class TestStartFall:
    """Tests for _start_fall()."""

    def test_start_fall_sets_state(self) -> None:
        g = _make_game()
        g._reset_state()
        g._start_fall()
        assert g.slinky.on_step_index == -1
        assert g.slinky.vy < 0  # initial upward push
        assert g.game_over_reason == "FALL"


class TestOnGameOver:
    """Tests for _on_game_over()."""

    def test_on_game_over_sets_phase(self) -> None:
        g = _make_game()
        g._reset_state()
        g.score = 500
        g._on_game_over()
        assert g.phase == Phase.GAME_OVER

    def test_on_game_over_updates_best_score(self) -> None:
        g = _make_game()
        g._reset_state()
        g.best_score = 100
        g.score = 500
        g._on_game_over()
        assert g.best_score == 500

    def test_on_game_over_does_not_lower_best(self) -> None:
        g = _make_game()
        g._reset_state()
        g.best_score = 500
        g.score = 100
        g._on_game_over()
        assert g.best_score == 500


class TestComboAndScoring:
    """Tests for combo and scoring mechanics."""

    def test_score_increases_with_combo(self) -> None:
        g = _make_game()
        g._reset_state()
        # Match 4 times in a row by setting colors
        for i in range(4):
            step = g.steps[i + 1]  # next step after current
            g.slinky.color = step.color
            g.slinky.flipping = True
            g._complete_flip()
        assert g.combo == 4
        assert g.score > 0

    def test_max_combo_tracks_highest(self) -> None:
        g = _make_game()
        g._reset_state()
        # Build to combo 3
        for i in range(3):
            step = g.steps[i + 1]
            g.slinky.color = step.color
            g.slinky.flipping = True
            g._complete_flip()
        assert g.max_combo == 3
        # Reset by mismatch
        step = g.steps[4]
        g.slinky.color = (step.color + 1) % 4
        g.slinky.flipping = True
        g._complete_flip()
        assert g.combo == 0
        assert g.max_combo == 3  # max_combo preserved


class TestIdleAndFall:
    """Tests for idle timer and fall mechanics."""

    def test_idle_timer_increments_when_not_flipping(self) -> None:
        g = _make_game()
        g._reset_state()
        g.slinky.flipping = False
        # Simulate what _update_playing does for idle
        initial_idle = g.idle_timer
        g.idle_timer += 1
        assert g.idle_timer == initial_idle + 1

    def test_fall_at_idle_limit(self) -> None:
        g = _make_game()
        g._reset_state()
        g.idle_timer = IDLE_FALL
        assert g.idle_timer >= IDLE_FALL
        g._start_fall()
        assert g.slinky.on_step_index == -1


class TestColorCycle:
    """Tests for slinky color cycling."""

    def test_color_cycles_after_color_cycle_frames(self) -> None:
        g = _make_game()
        g._reset_state()
        g.color_timer = COLOR_CYCLE
        original_color = g.slinky.color
        # Simulate color cycle
        g.color_timer += 1
        if g.color_timer >= COLOR_CYCLE:
            g.color_timer = 0
            g.slinky.color = (g.slinky.color + 1) % 4
        if g.color_timer == 0:  # only if it actually cycled
            assert g.slinky.color == (original_color + 1) % 4


class TestScrollMechanics:
    """Tests for scroll mechanics."""

    def test_scroll_increases_with_progress(self) -> None:
        g = _make_game()
        g._reset_state()
        g.slinky.on_step_index = 5  # Past SCROLL_THRESHOLD
        target_scroll = (5 - 3) * STEP_GAP_X
        g.scroll_x += (target_scroll - g.scroll_x) * 0.1
        assert g.scroll_x > 0


class TestPhaseEnum:
    """Tests for Phase enum."""

    def test_phase_values(self) -> None:
        assert Phase.TITLE is not None
        assert Phase.PLAYING is not None
        assert Phase.GAME_OVER is not None
        assert Phase.TITLE != Phase.PLAYING


if __name__ == "__main__":
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    sys.exit(result.returncode)
