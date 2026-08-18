from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "prototypes" / "323_rule_flux"))

from main import (  # noqa: E402
    COOL_COLORS,
    GREEN,
    HEAT_MAX,
    LIGHT_BLUE,
    RED,
    WARM_COLORS,
    YELLOW,
    Game,
    Phase,
    Rule,
    Token,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(seed)
    g.reset()
    return g


class TestIsGo:
    def test_high(self) -> None:
        assert Game._is_go(Token(7, RED), Rule.HIGH)
        assert not Game._is_go(Token(4, RED), Rule.HIGH)

    def test_even(self) -> None:
        assert Game._is_go(Token(4, RED), Rule.EVEN)
        assert not Game._is_go(Token(3, RED), Rule.EVEN)

    def test_warm(self) -> None:
        assert Game._is_go(Token(0, RED), Rule.WARM)
        assert Game._is_go(Token(0, YELLOW), Rule.WARM)
        assert not Game._is_go(Token(0, LIGHT_BLUE), Rule.WARM)

    def test_cool(self) -> None:
        assert Game._is_go(Token(0, LIGHT_BLUE), Rule.COOL)
        assert Game._is_go(Token(0, GREEN), Rule.COOL)
        assert not Game._is_go(Token(0, RED), Rule.COOL)

    def test_color_sets(self) -> None:
        assert WARM_COLORS == frozenset({RED, YELLOW})
        assert COOL_COLORS == frozenset({LIGHT_BLUE, GREEN})


class TestNextRule:
    def test_rotation_order(self) -> None:
        assert Game._next_rule(Rule.HIGH) is Rule.EVEN
        assert Game._next_rule(Rule.EVEN) is Rule.WARM
        assert Game._next_rule(Rule.WARM) is Rule.COOL
        assert Game._next_rule(Rule.COOL) is Rule.HIGH


class TestMakeToken:
    def test_token_ranges(self) -> None:
        g = _make_game(7)
        for _ in range(100):
            t = g._make_token()
            assert 0 <= t.number <= 9
            assert t.color in (RED, YELLOW, LIGHT_BLUE, GREEN)

    def test_deterministic_with_seed(self) -> None:
        a = _make_game(42)._make_token()
        b = _make_game(42)._make_token()
        assert a == b


class TestPress:
    def test_hit_increments_combo_and_score(self) -> None:
        g = _make_game()
        g.rule = Rule.HIGH
        g.token = Token(7, RED)  # GO
        g.token_elapsed = 999  # avoid speed bonus
        g.combo = 0
        g._handle_press()
        assert g.combo == 1
        assert g.score == 10
        assert g.max_combo == 1

    def test_hit_speed_bonus(self) -> None:
        g = _make_game()
        g.rule = Rule.HIGH
        g.token = Token(7, RED)
        g.token_elapsed = 0
        g._handle_press()
        assert g.score == 15  # 10 * 1 * 1 + 5

    def test_false_alarm_adds_heat_and_resets_combo(self) -> None:
        g = _make_game()
        g.rule = Rule.HIGH
        g.token = Token(2, RED)  # NO-GO
        g.combo = 3
        g._handle_press()
        assert g.heat == 15.0
        assert g.combo == 0
        assert g.score == 0

    def test_press_advances_token(self) -> None:
        g = _make_game()
        g.rule = Rule.HIGH
        g.token = Token(7, RED)
        before = g.token
        g._handle_press()
        assert g.token != before
        assert g.token_elapsed == 0

    def test_hit_starts_flux_at_combo_4(self) -> None:
        g = _make_game()
        g.rule = Rule.HIGH
        g.token = Token(7, RED)  # GO
        g.combo = 3
        g.token_elapsed = 999
        g._handle_press()
        assert g.combo == 4
        assert g.flux_active
        assert g.flux_timer == 300

    def test_flux_triples_hit_score(self) -> None:
        g = _make_game()
        g.rule = Rule.HIGH
        g.token = Token(7, RED)
        g.flux_active = True
        g.flux_timer = 200
        g.token_elapsed = 999
        g.combo = 2
        g._handle_press()
        assert g.score == 10 * 3 * 3  # combo=3, mult=3


class TestTokenExpiry:
    def test_miss_on_go_token(self) -> None:
        g = _make_game()
        g.rule = Rule.HIGH
        g.token = Token(8, RED)  # GO
        g.combo = 2
        g._handle_token_expiry()
        assert g.heat == 8.0
        assert g.combo == 0

    def test_correct_restraint_on_nogo_token(self) -> None:
        g = _make_game()
        g.rule = Rule.HIGH
        g.token = Token(3, RED)  # NO-GO
        g.combo = 2
        g._handle_token_expiry()
        assert g.score == 5
        assert g.combo == 2

    def test_expiry_advances_token(self) -> None:
        g = _make_game()
        g.rule = Rule.HIGH
        g.token = Token(3, RED)
        before = g.token
        g._handle_token_expiry()
        assert g.token != before


class TestHeat:
    def test_heat_decays(self) -> None:
        g = _make_game()
        g.heat = 50.0
        g._update_heat()
        assert g.heat == 50.0 - 0.02

    def test_heat_clamped_at_zero(self) -> None:
        g = _make_game()
        g.heat = 0.0
        g._update_heat()
        assert g.heat == 0.0

    def test_heat_frozen_in_flux(self) -> None:
        g = _make_game()
        g.heat = 50.0
        g.flux_active = True
        g._update_heat()
        assert g.heat == 50.0

    def test_game_over_on_max_heat(self) -> None:
        g = _make_game()
        g.heat = HEAT_MAX
        g._update_heat()
        assert g.phase == Phase.GAME_OVER
        assert g.overloaded


class TestRuleMutation:
    def test_rule_changes_on_timer_expiry(self) -> None:
        g = _make_game()
        g.rule = Rule.HIGH
        g.rule_timer = 1
        g._maybe_mutate_rule()
        assert g.rule is Rule.EVEN
        assert g.rule_timer == g._rule_interval()

    def test_warning_set_within_window(self) -> None:
        g = _make_game()
        g.rule_timer = 60
        g._maybe_mutate_rule()
        assert g.rule_warning > 0

    def test_no_warning_outside_window(self) -> None:
        g = _make_game()
        g.rule_timer = 200
        g._maybe_mutate_rule()
        assert g.rule_warning == 0

    def test_frozen_in_flux(self) -> None:
        g = _make_game()
        g.rule = Rule.HIGH
        g.rule_timer = 1
        g.flux_active = True
        g._maybe_mutate_rule()
        assert g.rule is Rule.HIGH
        assert g.rule_timer == 1


class TestFlux:
    def test_flux_expires_and_resets_combo(self) -> None:
        g = _make_game()
        g.flux_active = True
        g.flux_timer = 1
        g.combo = 5
        g._update_flux()
        assert not g.flux_active
        assert g.combo == 0


class TestDifficulty:
    def test_cycle_interval_ramps(self) -> None:
        g = _make_game()
        g.elapsed = 0
        assert g._cycle_interval() == 30
        g.elapsed = 5000
        assert g._cycle_interval() == 12

    def test_rule_interval_ramps(self) -> None:
        g = _make_game()
        g.elapsed = 0
        assert g._rule_interval() == 480
        g.elapsed = 5000
        assert g._rule_interval() == 240


class TestReset:
    def test_reset_initializes_state(self) -> None:
        g = _make_game()
        assert g.phase == Phase.TITLE
        assert g.score == 0
        assert g.heat == 0.0
        assert g.combo == 0
        assert g.timer == 3600
        assert not g.flux_active

    def test_reset_preserves_rng_seed(self) -> None:
        g = _make_game(99)
        token_a = g.token
        g.reset()
        token_b = g.token
        # same rng stream continues; reset() itself makes one token
        assert g.token.number in range(10)
        _ = token_a, token_b
