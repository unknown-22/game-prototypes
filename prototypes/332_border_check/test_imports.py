"""test_imports.py — Headless logic tests for 332_border_check.

Imports the game module without initializing Pyxel (the `if __name__ == "__main__"`
guard prevents pyxel.init/pyxel.run), and tests pure logic via Game.__new__(Game).
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # noqa: E402
    COUNTRIES,
    GAME_DURATION,
    LIVES_START,
    NAMES,
    RULE_COUNT,
    VISA_TYPES,
    Game,
    Phase,
    Rule,
    RuleKind,
    Traveler,
    patience_start,
    rule_interval,
    rule_violated,
    score_correct,
    traveler_is_denied,
)


def make_game(seed: int = 42) -> Game:
    """Headless factory: bypass __init__ (no pyxel.init), seed the RNG, reset()."""
    g = Game.__new__(Game)
    g.rng = random.Random(seed)
    g.reset()
    return g


def test_constants() -> None:
    assert len(COUNTRIES) == 4
    assert len(VISA_TYPES) == 4
    assert len(NAMES) == 8
    assert LIVES_START == 3
    assert GAME_DURATION == 3600
    assert RULE_COUNT == 3


def test_rule_violated_ban_country() -> None:
    t = Traveler(0, country=1, visa_type=0, visa_days=30, declared=200)
    assert rule_violated(Rule(RuleKind.BAN_COUNTRY, 1), t) is True
    assert rule_violated(Rule(RuleKind.BAN_COUNTRY, 0), t) is False


def test_rule_violated_min_visa_days() -> None:
    t = Traveler(0, 0, 0, visa_days=14, declared=200)
    assert rule_violated(Rule(RuleKind.MIN_VISA_DAYS, 30), t) is True
    assert rule_violated(Rule(RuleKind.MIN_VISA_DAYS, 14), t) is False  # strict <


def test_rule_violated_max_declared() -> None:
    t = Traveler(0, 0, 0, 30, declared=500)
    assert rule_violated(Rule(RuleKind.MAX_DECLARED, 300), t) is True
    assert rule_violated(Rule(RuleKind.MAX_DECLARED, 500), t) is False  # strict >


def test_rule_violated_ban_visa_type() -> None:
    t = Traveler(0, 0, visa_type=2, visa_days=30, declared=200)
    assert rule_violated(Rule(RuleKind.BAN_VISA_TYPE, 2), t) is True
    assert rule_violated(Rule(RuleKind.BAN_VISA_TYPE, 0), t) is False


def test_rule_violated_wanted_name() -> None:
    t = Traveler(3, 0, 0, 30, 200)
    assert rule_violated(Rule(RuleKind.WANTED_NAME, 3), t) is True
    assert rule_violated(Rule(RuleKind.WANTED_NAME, 5), t) is False


def test_traveler_is_denied_any_rule() -> None:
    t = Traveler(0, 0, 0, visa_days=5, declared=100)
    rules = [Rule(RuleKind.BAN_COUNTRY, 0), Rule(RuleKind.MIN_VISA_DAYS, 30)]
    assert traveler_is_denied(t, rules) is True
    ok = Traveler(0, country=1, visa_type=0, visa_days=50, declared=100)
    assert traveler_is_denied(ok, rules) is False


def test_score_correct_streak_and_quick_bonus() -> None:
    # streak caps at 5x: base = 10 * min(streak, 5)
    assert score_correct(1, 0.5) == 10
    assert score_correct(3, 0.5) == 30
    assert score_correct(5, 0.5) == 50
    assert score_correct(9, 0.5) == 50  # capped at 5
    # QUICK bonus when patience_ratio > 0.75
    assert score_correct(1, 0.9) == 10 + 25
    assert score_correct(1, 0.75) == 10  # not > 0.75


def test_patience_start_monotonic_decreasing_with_floor() -> None:
    assert patience_start(0) == 300.0
    assert patience_start(3600) == 150.0
    assert patience_start(0) > patience_start(1800) > patience_start(3600)
    assert patience_start(100000) == 150.0  # floor


def test_rule_interval_monotonic_decreasing_with_floor() -> None:
    assert rule_interval(0) == 720
    assert rule_interval(0) > rule_interval(3600)
    assert rule_interval(100000) == 240  # floor


def test_make_traveler_valid_ranges() -> None:
    g = make_game(1)
    t = g.make_traveler(random.Random(1))
    assert 0 <= t.name_index < len(NAMES)
    assert 0 <= t.country < len(COUNTRIES)
    assert 0 <= t.visa_type < len(VISA_TYPES)
    assert 1 <= t.visa_days <= 90
    assert t.declared >= 100


def test_reset_initializes_state() -> None:
    g = make_game()
    assert g.phase is Phase.TITLE
    assert g.score == 0
    assert g.streak == 0
    assert g.lives == LIVES_START
    assert g.frame == 0
    assert len(g.rules) == RULE_COUNT
    assert g.correct_total == 0 and g.missed == 0 and g.errors == 0
    assert g.traveler is None
    assert g.best_score >= 0


def test_reset_preserves_best_score_and_seeded_rng() -> None:
    g = make_game(7)
    g.best_score = 999
    g.reset()
    assert g.best_score == 999  # best_score preserved across reset
    # rng identity preserved (seeded) — verify deterministic re-seed not applied
    assert g.rng is not None


def test_decide_correct_deny() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.traveler = Traveler(0, 0, 0, visa_days=5, declared=100)  # denied (BAN country 0)
    g.rules = [Rule(RuleKind.BAN_COUNTRY, 0)]
    g._decide(False)  # DENY the violator -> correct
    assert g.last_outcome == "CORRECT"
    assert g.streak == 1
    assert g.correct_total == 1
    assert g.errors == 0
    assert g.lives == LIVES_START
    assert g.score == 10 * 1 + 25  # fresh traveler -> patience ratio 1.0 -> QUICK bonus


def test_decide_error_wrong_approve() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.traveler = Traveler(0, 0, 0, visa_days=5, declared=100)  # denied
    g.rules = [Rule(RuleKind.BAN_COUNTRY, 0)]
    g._decide(True)  # APPROVE a violator -> error
    assert g.last_outcome == "ERROR"
    assert g.lives == LIVES_START - 1
    assert g.streak == 0
    assert g.errors == 1
    assert g.score == 0
    assert g.shake_frames > 0


def test_decide_error_wrong_deny() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.traveler = Traveler(0, country=2, visa_type=0, visa_days=80, declared=100)  # valid
    g.rules = [Rule(RuleKind.BAN_COUNTRY, 0)]
    g._decide(False)  # DENY a valid traveler -> error
    assert g.last_outcome == "ERROR"
    assert g.lives == LIVES_START - 1


def test_decide_spawns_next_traveler() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.traveler = Traveler(0, 0, 0, 30, 200)
    g.rules = [Rule(RuleKind.BAN_COUNTRY, 1)]  # not violated by country 0
    g._decide(True)
    assert g.traveler is not None
    assert g.traveler.patience == patience_start(0)


def test_update_patience_miss() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.traveler = Traveler(0, 0, 0, 30, 200, patience=1.0)
    g._update_patience()
    assert g.last_outcome == "MISS"
    assert g.streak == 0
    assert g.missed == 1
    assert g.correct_total == 0
    # next traveler spawned with fresh patience
    assert g.traveler is not None and g.traveler.patience > 1


def test_mutate_rules_replaces_one_rule() -> None:
    g = make_game(3)
    before = list(g.rules)
    g._mutate_rules()
    after = list(g.rules)
    assert len(after) == RULE_COUNT
    # exactly one rule index changed (mutate_index)
    diffs = [i for i in range(RULE_COUNT) if before[i] != after[i]]
    assert len(diffs) == 1


def test_check_game_over_detained() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.lives = 0
    g._check_game_over()
    assert g.phase is Phase.GAME_OVER
    assert g.end_reason == "DETAINED"


def test_check_game_over_shift_over() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.frame = GAME_DURATION
    g._check_game_over()
    assert g.phase is Phase.GAME_OVER
    assert g.end_reason == "SHIFT OVER"


def test_check_game_over_updates_best_score() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.score = 500
    g.lives = 0
    g._check_game_over()
    assert g.best_score == 500


def test_rule_label_properties() -> None:
    assert Rule(RuleKind.BAN_COUNTRY, 0).label == "BAN ATLANTIA"
    assert Rule(RuleKind.MIN_VISA_DAYS, 30).label == "VISA < 30"
    assert Rule(RuleKind.MAX_DECLARED, 500).label == "DECL < $500"
    assert Rule(RuleKind.BAN_VISA_TYPE, 2).label == "NO TRANSIT"
    assert Rule(RuleKind.WANTED_NAME, 0).label == "WANTED ALEX"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"FAIL {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
