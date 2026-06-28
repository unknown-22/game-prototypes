"""Comprehensive import and logic tests for 174_judo_surge.

Run from repo root:
    uv run python prototypes/174_judo_surge/test_imports.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import (  # noqa: E402
    COLORS,
    COL_CYAN,
    COL_GRAY,
    COL_RED,
    COL_WHITE,
    COMBO_SCORE_BASE,
    COMBO_SCORE_PER,
    COMBO_THRESHOLD,
    GAME_TIME,
    HEAT_AI_HIT,
    HEAT_DECAY,
    HEAT_MAX,
    HEAT_MISMATCH,
    IPPON_DURATION,
    IPPON_SCORE,
    MAT_CX,
    MAT_CY,
    FloatingText,
    Game,
    Particle,
    Phase,
    _make_game,
)


# ── Imports & Constants ────────────────────────────────────────────────────────
def test_imports_ok() -> None:
    """All expected names are importable."""
    assert Game is not None
    assert Phase is not None
    assert Particle is not None
    assert FloatingText is not None
    assert _make_game is not None
    assert COMBO_THRESHOLD == 4


def test_game_creation_bypasses_pyxel() -> None:
    """_make_game() creates a Game without pyxel.init/run."""
    g = _make_game(random.Random(42))
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.ippon_timer == 0
    assert g.game_timer == GAME_TIME
    assert g.particles == []
    assert g.floating_texts == []


# ── Reset / Init State ─────────────────────────────────────────────────────────
def test_reset_initializes_to_title() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE


def test_init_state_transitions_to_playing() -> None:
    g = _make_game()
    g._init_state()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.ippon_timer == 0
    assert g.game_timer == GAME_TIME
    assert g.particles == []
    assert g.floating_texts == []
    assert g.player_x == MAT_CX - 50
    assert g.player_y == MAT_CY
    assert g.ai_x == MAT_CX + 50
    assert g.ai_y == MAT_CY
    assert g.player_color_index == 0
    assert g.player_color_timer == 90
    assert 120 <= g.ai_color_timer <= 180


# ── Color Helpers ──────────────────────────────────────────────────────────────
def test_player_color_returns_current_index_color() -> None:
    g = _make_game(random.Random(42))
    g._init_state()
    g.player_color_index = 0
    assert g._player_color() == COLORS[0]
    g.player_color_index = 2
    assert g._player_color() == COLORS[2]


def test_ai_color_returns_current_index_color() -> None:
    g = _make_game(random.Random(42))
    g._init_state()
    g.ai_color_index = 1
    assert g._ai_color() == COLORS[1]


# ── _attempt_throw ─────────────────────────────────────────────────────────────
class TestAttemptThrow:
    def test_match_success(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        success, delta = g._attempt_throw(COLORS[0], COLORS[0])
        assert success is True
        assert delta == COMBO_SCORE_BASE + 1 * COMBO_SCORE_PER
        assert g.combo == 1
        assert g.score == delta

    def test_mismatch_failure(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        success, delta = g._attempt_throw(COLORS[0], COLORS[1])
        assert success is False
        assert delta == 0
        assert g.combo == 0
        assert g.heat == HEAT_MISMATCH
        assert g.score == 0

    def test_combo_increments_on_match(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g._attempt_throw(COLORS[0], COLORS[0])  # combo 1
        g._attempt_throw(COLORS[0], COLORS[0])  # combo 2
        g._attempt_throw(COLORS[0], COLORS[0])  # combo 3
        assert g.combo == 3

    def test_combo_resets_on_mismatch(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g._attempt_throw(COLORS[0], COLORS[0])  # combo 1
        g._attempt_throw(COLORS[0], COLORS[0])  # combo 2
        g._attempt_throw(COLORS[0], COLORS[1])  # mismatch
        assert g.combo == 0

    def test_max_combo_tracks_highest(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g._attempt_throw(COLORS[0], COLORS[0])  # combo 1
        g._attempt_throw(COLORS[0], COLORS[0])  # combo 2
        g._attempt_throw(COLORS[0], COLORS[0])  # combo 3
        g._attempt_throw(COLORS[0], COLORS[1])  # mismatch, combo=0
        g._attempt_throw(COLORS[0], COLORS[0])  # combo 1
        assert g.max_combo == 3

    def test_score_increases_with_combo(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g._attempt_throw(COLORS[0], COLORS[0])  # combo 1 → 100+50=150
        g._attempt_throw(COLORS[0], COLORS[0])  # combo 2 → 100+100=200
        assert g.combo == 2
        assert g.score == 150 + 200

    def test_ippon_mode_auto_success_any_color(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.ippon_timer = 1  # IPPON active
        # Any color combination should succeed during IPPON
        success, delta = g._attempt_throw(COLORS[0], COLORS[1])
        assert success is True
        assert g.combo == 1

    def test_ippon_mode_3x_score_multiplier(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.ippon_timer = 1
        g.combo = 0
        success, delta = g._attempt_throw(COLORS[0], COLORS[1])
        # combo becomes 1, base = 100 + 1*50 = 150, *3 = 450
        assert delta == (COMBO_SCORE_BASE + 1 * COMBO_SCORE_PER) * 3
        assert g.score == delta

    def test_heat_capped_at_max(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.heat = HEAT_MAX - 5.0
        g._attempt_throw(COLORS[0], COLORS[1])  # adds HEAT_MISMATCH
        assert g.heat <= HEAT_MAX

    def test_mismatch_does_not_change_score_combo_on_mismatch(self) -> None:
        # Verify no score change on mismatch beyond heat
        g = _make_game(random.Random(42))
        g._init_state()
        g.combo = 2
        g.score = 500
        g._attempt_throw(COLORS[0], COLORS[1])
        assert g.combo == 0
        assert g.score == 500  # unchanged


# ── _trigger_ippon ─────────────────────────────────────────────────────────────
class TestTriggerIppon:
    def test_trigger_sets_timer_and_adds_score(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        prev_score = g.score
        g._trigger_ippon()
        assert g.ippon_timer == IPPON_DURATION
        assert g.score == prev_score + IPPON_SCORE

    def test_ippon_can_be_triggered_multiple_times(self) -> None:
        """Each IPPON trigger adds score and resets timer."""
        g = _make_game(random.Random(42))
        g._init_state()
        g._trigger_ippon()
        g.ippon_timer = 0  # force end
        g.combo = 4  # rebuild combo
        g._trigger_ippon()
        assert g.score == IPPON_SCORE * 2


# ── _update_heat ────────────────────────────────────────────────────────────────
class TestUpdateHeat:
    def test_decay_reduces_heat(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.heat = 10.0
        game_over = g._update_heat()
        assert g.heat == 10.0 - HEAT_DECAY
        assert game_over is False

    def test_decay_does_not_go_below_zero(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.heat = 0.0
        g._update_heat()
        assert g.heat == 0.0

    def test_decay_negative_becomes_zero(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.heat = 0.001
        g._update_heat()
        assert g.heat == 0.0

    def test_heat_at_max_returns_game_over(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.heat = HEAT_MAX
        game_over = g._update_heat()
        assert game_over is True

    def test_heat_below_max_no_game_over(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.heat = HEAT_MAX - 0.01
        game_over = g._update_heat()
        assert game_over is False


# ── _update_ippon ───────────────────────────────────────────────────────────────
class TestUpdateIppon:
    def test_decrements_active_timer(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.ippon_timer = 100
        g._update_ippon()
        assert g.ippon_timer == 99

    def test_noop_when_zero(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.ippon_timer = 0
        g._update_ippon()
        assert g.ippon_timer == 0

    def test_ends_and_resets_combo(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.ippon_timer = 1
        g.combo = 5
        g._update_ippon()
        assert g.ippon_timer == 0
        assert g.combo == 0

    def test_ends_stays_at_zero(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.ippon_timer = 0
        g._update_ippon()
        assert g.ippon_timer == 0


# ── _update_ai ─────────────────────────────────────────────────────────────────
class TestUpdateAi:
    def test_color_cycles_when_timer_expires(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.ai_color_timer = 1
        g._update_ai()
        # timer expired, color cycled OR same if random picked same
        assert 0 <= g.ai_color_index <= 3
        assert g.ai_color_timer >= 120  # new timer assigned

    def test_attack_triggers_after_timer_expires(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g._ai_attack_timer = 1
        g._ai_attacking = False
        attacking, color = g._update_ai()
        assert attacking is True
        assert g._ai_attacking is True
        assert g._ai_attack_flash == 15

    def test_attack_not_triggered_prematurely(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g._ai_attack_timer = 100
        g._ai_attacking = False
        attacking, color = g._update_ai()
        assert attacking is False

    def test_attack_flash_decrements(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g._ai_attacking = True
        g._ai_attack_flash = 5
        attacking, color = g._update_ai()
        assert g._ai_attack_flash == 4

    def test_attack_ends_when_flash_expires(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g._ai_attacking = True
        g._ai_attack_flash = 1
        attacking, color = g._update_ai()
        assert g._ai_attacking is False
        assert g._ai_attack_flash == 0


# ── _handle_ai_attack ──────────────────────────────────────────────────────────
class TestHandleAiAttack:
    def test_hit_when_colors_differ(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.player_color_index = 0  # RED
        g.ai_color_index = 1  # GREEN
        result = g._handle_ai_attack()
        assert result == "hit"
        assert g.heat == HEAT_AI_HIT

    def test_defend_when_colors_match(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.player_color_index = 2  # BLUE
        g.ai_color_index = 2  # BLUE
        result = g._handle_ai_attack()
        assert result == "defend"
        assert g.heat == 0.0

    def test_heat_caps_at_max_on_hit(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.player_color_index = 0
        g.ai_color_index = 1
        g.heat = HEAT_MAX - 1.0
        g._handle_ai_attack()
        assert g.heat == HEAT_MAX


# ── Timer ──────────────────────────────────────────────────────────────────────
class TestTimer:
    def test_decrements_game_timer(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        assert g.game_timer == GAME_TIME
        g._update_timer()
        assert g.game_timer == GAME_TIME - 1

    def test_timer_zero_returns_game_over(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.game_timer = 1
        game_over = g._update_timer()
        assert game_over is True
        assert g.game_timer == 0


# ── Particle System ────────────────────────────────────────────────────────────
class TestParticles:
    def test_spawn_adds_particles(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g._spawn_particles(100.0, 100.0, 10, COL_RED)
        assert len(g.particles) == 10

    def test_spawned_particles_have_valid_properties(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g._spawn_particles(100.0, 100.0, 5, COL_RED)
        for p in g.particles:
            assert p.x == 100.0
            assert p.y == 100.0
            assert p.color == COL_RED
            assert 8 <= p.life <= 20

    def test_update_ages_and_removes_dead(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.particles = [
            Particle(x=0, y=0, vx=1, vy=0, color=COL_RED, life=1),
            Particle(x=0, y=0, vx=0, vy=1, color=COL_RED, life=2),
        ]
        g._update_particles()
        # life=1 → life becomes 0 → removed. life=2 → life becomes 1 → survives.
        assert len(g.particles) == 1
        assert g.particles[0].life == 1

    def test_particles_move(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.particles = [Particle(x=10.0, y=20.0, vx=3.0, vy=-2.0, color=COL_RED, life=10)]
        g._update_particles()
        assert g.particles[0].x == 13.0
        assert g.particles[0].y == 18.0

    def test_spawn_ippon_creates_many_particles(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g._spawn_ippon_particles()
        assert len(g.particles) == 40

    def test_spawn_ai_attack_creates_particles(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g._spawn_ai_attack_particles()
        assert len(g.particles) == 8
        for p in g.particles:
            assert p.color == COL_GRAY


# ── Floating Text System ───────────────────────────────────────────────────────
class TestFloatingTexts:
    def test_spawn_adds_text(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g._spawn_floating_text(100.0, 100.0, "+150", COL_WHITE, 30)
        assert len(g.floating_texts) == 1

    def test_spawned_text_has_correct_properties(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g._spawn_floating_text(50.0, 60.0, "IPPON!!", COL_CYAN, 60)
        ft = g.floating_texts[0]
        assert ft.x == 50.0
        assert ft.y == 60.0
        assert ft.text == "IPPON!!"
        assert ft.color == COL_CYAN
        assert ft.life == 60

    def test_update_ages_and_removes_dead(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.floating_texts = [
            FloatingText(x=0, y=0, text="A", color=COL_WHITE, life=1),
            FloatingText(x=0, y=0, text="B", color=COL_WHITE, life=2),
        ]
        g._update_floating_texts()
        # life=1 → becomes 0 → removed. life=2 → becomes 1 → survives.
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].life == 1


# ── Full Flow ──────────────────────────────────────────────────────────────────
class TestFullFlow:
    def test_ippon_triggers_after_4_consecutive_matches(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        # 4 consecutive matches
        for _ in range(4):
            g._attempt_throw(COLORS[0], COLORS[0])
        assert g.combo == 4
        assert g.max_combo == 4

    def test_game_over_from_heat(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.heat = HEAT_MAX
        assert g._update_heat() is True

    def test_game_over_from_timer(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.game_timer = 1
        assert g._update_timer() is True

    def test_ippon_timer_decrements_each_update(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g._trigger_ippon()
        assert g.ippon_timer == IPPON_DURATION
        g._update_ippon()
        assert g.ippon_timer == IPPON_DURATION - 1

    def test_multiple_ippon_cycles(self) -> None:
        """Verify IPPON can be triggered, end, and triggered again."""
        g = _make_game(random.Random(42))
        g._init_state()

        # First IPPON
        for _ in range(4):
            g._attempt_throw(COLORS[0], COLORS[0])
        assert g.combo == 4
        g._trigger_ippon()
        assert g.ippon_timer == IPPON_DURATION
        assert g.score >= IPPON_SCORE

        # Wait for IPPON to end
        g.ippon_timer = 1
        g._update_ippon()
        assert g.ippon_timer == 0
        assert g.combo == 0

        # Build combo again and trigger second IPPON
        for _ in range(4):
            g._attempt_throw(COLORS[0], COLORS[0])
        assert g.combo == 4
        g._trigger_ippon()
        assert g.ippon_timer == IPPON_DURATION
        assert g.score >= IPPON_SCORE * 2

    def test_score_progression_across_throws(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        # 5 successful throws
        expected_score = 0
        for i in range(5):
            success, delta = g._attempt_throw(COLORS[0], COLORS[0])
            assert success is True
            expected_score += delta
        assert g.score == expected_score
        assert g.combo == 5

    def test_heat_accumulates_from_mismatches(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        for _ in range(3):
            g._attempt_throw(COLORS[0], COLORS[1])
        assert g.heat == HEAT_MISMATCH * 3

    def test_heat_decay_between_mismatches(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g._attempt_throw(COLORS[0], COLORS[1])  # heat = 20
        g._update_heat()  # decay
        g._attempt_throw(COLORS[0], COLORS[1])  # heat = decayed + 20
        assert g.heat == HEAT_MISMATCH - HEAT_DECAY + HEAT_MISMATCH

    def test_player_position_initial(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        assert g.player_x == MAT_CX - 50
        assert g.player_y == MAT_CY

    def test_ai_position_initial(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        assert g.ai_x == MAT_CX + 50
        assert g.ai_y == MAT_CY

    def test_repeated_reset_clears_state(self) -> None:
        g = _make_game(random.Random(42))
        g._init_state()
        g.score = 999
        g.combo = 7
        g.heat = 80.0
        g.ippon_timer = 50
        g.particles = [Particle(x=0, y=0, vx=1, vy=1, color=COL_RED, life=10)]
        g.floating_texts = [FloatingText(x=0, y=0, text="x", color=COL_WHITE, life=10)]

        g._init_state()

        assert g.phase == Phase.PLAYING
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0.0
        assert g.ippon_timer == 0
        assert g.particles == []
        assert g.floating_texts == []
        assert g.game_timer == GAME_TIME

    def test_k8x12_bdf_exists(self) -> None:
        """BDF font should exist alongside main.py for web packaging."""
        font_path = Path(__file__).parent / "k8x12.bdf"
        assert font_path.exists(), f"Missing font at {font_path}"


# ── Runner ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import traceback

    tests = [
        # Imports
        ("test_imports_ok", test_imports_ok),
        ("test_game_creation_bypasses_pyxel", test_game_creation_bypasses_pyxel),
        # Reset
        ("test_reset_initializes_to_title", test_reset_initializes_to_title),
        ("test_init_state_transitions_to_playing", test_init_state_transitions_to_playing),
        # Colors
        ("test_player_color_returns_current_index_color", test_player_color_returns_current_index_color),
        ("test_ai_color_returns_current_index_color", test_ai_color_returns_current_index_color),
        # _attempt_throw
        ("TestAttemptThrow.test_match_success", TestAttemptThrow().test_match_success),
        ("TestAttemptThrow.test_mismatch_failure", TestAttemptThrow().test_mismatch_failure),
        ("TestAttemptThrow.test_combo_increments_on_match", TestAttemptThrow().test_combo_increments_on_match),
        ("TestAttemptThrow.test_combo_resets_on_mismatch", TestAttemptThrow().test_combo_resets_on_mismatch),
        ("TestAttemptThrow.test_max_combo_tracks_highest", TestAttemptThrow().test_max_combo_tracks_highest),
        ("TestAttemptThrow.test_score_increases_with_combo", TestAttemptThrow().test_score_increases_with_combo),
        ("TestAttemptThrow.test_ippon_mode_auto_success_any_color", TestAttemptThrow().test_ippon_mode_auto_success_any_color),
        ("TestAttemptThrow.test_ippon_mode_3x_score_multiplier", TestAttemptThrow().test_ippon_mode_3x_score_multiplier),
        ("TestAttemptThrow.test_heat_capped_at_max", TestAttemptThrow().test_heat_capped_at_max),
        ("TestAttemptThrow.test_mismatch_no_score_change", TestAttemptThrow().test_mismatch_does_not_change_score_combo_on_mismatch),
        # _trigger_ippon
        ("TestTriggerIppon.test_trigger_sets_timer_and_adds_score", TestTriggerIppon().test_trigger_sets_timer_and_adds_score),
        ("TestTriggerIppon.test_ippon_multiple", TestTriggerIppon().test_ippon_can_be_triggered_multiple_times),
        # _update_heat
        ("TestUpdateHeat.test_decay_reduces_heat", TestUpdateHeat().test_decay_reduces_heat),
        ("TestUpdateHeat.test_decay_not_below_zero", TestUpdateHeat().test_decay_does_not_go_below_zero),
        ("TestUpdateHeat.test_decay_negative_becomes_zero", TestUpdateHeat().test_decay_negative_becomes_zero),
        ("TestUpdateHeat.test_heat_at_max_game_over", TestUpdateHeat().test_heat_at_max_returns_game_over),
        ("TestUpdateHeat.test_heat_below_max_no_game_over", TestUpdateHeat().test_heat_below_max_no_game_over),
        # _update_ippon
        ("TestUpdateIppon.test_decrements_active_timer", TestUpdateIppon().test_decrements_active_timer),
        ("TestUpdateIppon.test_noop_when_zero", TestUpdateIppon().test_noop_when_zero),
        ("TestUpdateIppon.test_ends_and_resets_combo", TestUpdateIppon().test_ends_and_resets_combo),
        ("TestUpdateIppon.test_ends_stays_at_zero", TestUpdateIppon().test_ends_stays_at_zero),
        # _update_ai
        ("TestUpdateAi.test_color_cycles", TestUpdateAi().test_color_cycles_when_timer_expires),
        ("TestUpdateAi.test_attack_triggers", TestUpdateAi().test_attack_triggers_after_timer_expires),
        ("TestUpdateAi.test_attack_not_premature", TestUpdateAi().test_attack_not_triggered_prematurely),
        ("TestUpdateAi.test_attack_flash_decrements", TestUpdateAi().test_attack_flash_decrements),
        ("TestUpdateAi.test_attack_ends", TestUpdateAi().test_attack_ends_when_flash_expires),
        # _handle_ai_attack
        ("TestHandleAiAttack.test_hit", TestHandleAiAttack().test_hit_when_colors_differ),
        ("TestHandleAiAttack.test_defend", TestHandleAiAttack().test_defend_when_colors_match),
        ("TestHandleAiAttack.test_heat_caps", TestHandleAiAttack().test_heat_caps_at_max_on_hit),
        # Timer
        ("TestTimer.test_decrements", TestTimer().test_decrements_game_timer),
        ("TestTimer.test_zero_game_over", TestTimer().test_timer_zero_returns_game_over),
        # Particles
        ("TestParticles.test_spawn_adds", TestParticles().test_spawn_adds_particles),
        ("TestParticles.test_valid_properties", TestParticles().test_spawned_particles_have_valid_properties),
        ("TestParticles.test_update_ages", TestParticles().test_update_ages_and_removes_dead),
        ("TestParticles.test_particles_move", TestParticles().test_particles_move),
        ("TestParticles.test_spawn_ippon", TestParticles().test_spawn_ippon_creates_many_particles),
        ("TestParticles.test_spawn_ai_attack", TestParticles().test_spawn_ai_attack_creates_particles),
        # Floating Texts
        ("TestFloatingTexts.test_spawn_adds", TestFloatingTexts().test_spawn_adds_text),
        ("TestFloatingTexts.test_correct_props", TestFloatingTexts().test_spawned_text_has_correct_properties),
        ("TestFloatingTexts.test_update_ages", TestFloatingTexts().test_update_ages_and_removes_dead),
        # Full Flow
        ("TestFullFlow.test_ippon_4_consecutive", TestFullFlow().test_ippon_triggers_after_4_consecutive_matches),
        ("TestFullFlow.test_game_over_heat", TestFullFlow().test_game_over_from_heat),
        ("TestFullFlow.test_game_over_timer", TestFullFlow().test_game_over_from_timer),
        ("TestFullFlow.test_ippon_timer_decrements", TestFullFlow().test_ippon_timer_decrements_each_update),
        ("TestFullFlow.test_multiple_ippon", TestFullFlow().test_multiple_ippon_cycles),
        ("TestFullFlow.test_score_progression", TestFullFlow().test_score_progression_across_throws),
        ("TestFullFlow.test_heat_accumulates", TestFullFlow().test_heat_accumulates_from_mismatches),
        ("TestFullFlow.test_heat_decay_between", TestFullFlow().test_heat_decay_between_mismatches),
        ("TestFullFlow.test_player_position", TestFullFlow().test_player_position_initial),
        ("TestFullFlow.test_ai_position", TestFullFlow().test_ai_position_initial),
        ("TestFullFlow.test_repeated_reset", TestFullFlow().test_repeated_reset_clears_state),
        ("TestFullFlow.test_font_exists", TestFullFlow().test_k8x12_bdf_exists),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
            print(f"  PASS  {name}")
        except Exception:
            failed += 1
            print(f"  FAIL  {name}")
            traceback.print_exc()

    print(f"\n{passed} passed, {failed} failed out of {len(tests)} tests")
    if failed > 0:
        sys.exit(1)
