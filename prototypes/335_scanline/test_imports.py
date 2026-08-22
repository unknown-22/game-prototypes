"""Headless logic tests for SCANLINE (335_scanline).

Runs without Pyxel: imports the game module (which imports pyxel but only
calls Rust-backed functions inside draw/update/__init__, never in the tested
logic methods), and uses Game.__new__ to bypass __init__.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import (  # noqa: E402
    BAG_W,
    BAG_Y,
    SHIFT_FRAMES,
    SECURITY_START,
    Bag,
    FloatingText,
    Game,
    ITEMS,
    Particle,
    Phase,
    bag_speed,
    combo_multiplier,
    contraband_chance,
    max_items,
    resolve_outcome,
    spawn_interval,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.rng = random.Random(42)
    g.best_score = 0
    g.reset()
    g.start_game()
    return g


def _bag(items, flagged=False):
    return Bag(x=0.0, y=float(BAG_Y), items=items, flagged=flagged)


# --- Pure functions ---


def test_combo_multiplier_basic():
    assert combo_multiplier(0) == 1.0
    assert combo_multiplier(1) == 1.5
    assert combo_multiplier(2) == 2.0
    assert combo_multiplier(3) == 2.5


def test_combo_multiplier_caps_at_4():
    assert combo_multiplier(6) == 4.0
    assert combo_multiplier(100) == 4.0


def test_resolve_outcome_all_cases():
    assert resolve_outcome(True, True) == "CAUGHT"
    assert resolve_outcome(False, True) == "FALSE_ALARM"
    assert resolve_outcome(True, False) == "MISS"
    assert resolve_outcome(False, False) == "PASS"


def test_spawn_interval_decreases_with_min():
    assert spawn_interval(0) == 90
    assert spawn_interval(45) == 89
    assert spawn_interval(10_000) == 28
    assert spawn_interval(0) > spawn_interval(5000)


def test_bag_speed_increases():
    assert bag_speed(0) == 1.0
    assert bag_speed(SHIFT_FRAMES) > bag_speed(0)
    assert bag_speed(SHIFT_FRAMES) < 4.0


def test_max_items_increases_and_caps():
    assert max_items(0) == 2
    assert max_items(1800) == 3
    assert max_items(7200) == 5


def test_contraband_chance_increases_and_caps():
    assert abs(contraband_chance(0) - 0.30) < 1e-9
    assert contraband_chance(SHIFT_FRAMES) > contraband_chance(0)
    assert contraband_chance(100_000) == 0.55


# --- ItemDef / Bag ---


def test_item_defs_are_correct():
    assert set(ITEMS) == {"BOOK", "SHOE", "BOTTLE", "GUN", "KNIFE"}
    assert ITEMS["GUN"].contraband is True
    assert ITEMS["KNIFE"].contraband is True
    assert ITEMS["BOTTLE"].contraband is True
    assert ITEMS["BOOK"].contraband is False
    assert ITEMS["SHOE"].contraband is False
    assert ITEMS["GUN"].subtle is False
    assert ITEMS["KNIFE"].subtle is True
    assert ITEMS["BOTTLE"].subtle is True


def test_bag_has_contraband():
    assert _bag([ITEMS["BOOK"], ITEMS["SHOE"]]).has_contraband() is False
    assert _bag([ITEMS["GUN"]]).has_contraband() is True
    assert _bag([ITEMS["BOOK"], ITEMS["KNIFE"]]).has_contraband() is True
    assert _bag([]).has_contraband() is False


# --- Game state init / restart ---


def test_start_game_initializes_state():
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.security == SECURITY_START
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.caught == 0 and g.missed == 0
    assert g.false_alarms == 0 and g.passed == 0
    assert g.bags == []
    assert g.frame == 0


def test_reset_preserves_best_score():
    g = _make_game()
    g.best_score = 777
    g.start_game()
    assert g.best_score == 777
    assert g.score == 0
    assert g.phase == Phase.PLAYING


def test_reset_preserves_seeded_rng():
    g = Game.__new__(Game)
    g.rng = random.Random(42)
    g.best_score = 0
    g.reset()
    # rng is not overwritten by reset() thanks to getattr(...) or ...
    a = g.rng.random()
    b = random.Random(42).random()
    assert a == b


# --- Spawning ---


def test_spawn_bag_adds_a_bag():
    g = _make_game()
    g._spawn_bag()
    assert len(g.bags) == 1
    assert 2 <= len(g.bags[0].items) <= max_items(0)
    assert g.bags[0].x < 0  # spawns off the left edge


def test_spawn_bag_respects_item_count_bounds():
    g = _make_game()
    g.frame = 7200  # max_items == 5
    for _ in range(20):
        g._spawn_bag()
    for bag in g.bags:
        assert 2 <= len(bag.items) <= 5


# --- Resolution / outcomes ---


def test_caught_grants_score_and_combo():
    g = _make_game()
    bag = _bag([ITEMS["GUN"]], flagged=True)
    outcome = g._resolve_bag(bag)
    assert outcome == "CAUGHT"
    assert g.score == 100  # int(100 * 1.0)
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.caught == 1
    assert g.security == SECURITY_START  # min(100, 105)


def test_caught_combo_multiplier_scales_score():
    g = _make_game()
    g.combo = 4  # combo_multiplier(4) == 3.0
    bag = _bag([ITEMS["GUN"]], flagged=True)
    g._resolve_bag(bag)
    assert g.score == 300  # int(100 * 3.0)
    assert g.combo == 5


def test_caught_security_clamps_at_100():
    g = _make_game()
    g.security = 98
    g._resolve_bag(_bag([ITEMS["GUN"]], flagged=True))
    assert g.security == 100


def test_false_alarm_resets_combo_and_penalizes():
    g = _make_game()
    g.combo = 3
    g.max_combo = 3
    outcome = g._resolve_bag(_bag([ITEMS["BOOK"]], flagged=True))
    assert outcome == "FALSE_ALARM"
    assert g.combo == 0
    assert g.security == SECURITY_START - 10
    assert g.false_alarms == 1
    assert g.score == 0


def test_miss_resets_combo_and_penalizes_more():
    g = _make_game()
    g.combo = 2
    outcome = g._resolve_bag(_bag([ITEMS["KNIFE"]], flagged=False))
    assert outcome == "MISS"
    assert g.combo == 0
    assert g.security == SECURITY_START - 15
    assert g.missed == 1


def test_pass_grants_small_score_and_combo():
    g = _make_game()
    outcome = g._resolve_bag(_bag([ITEMS["BOOK"], ITEMS["SHOE"]], flagged=False))
    assert outcome == "PASS"
    assert g.score == 20
    assert g.combo == 1
    assert g.passed == 1
    assert g.security == SECURITY_START


def test_risk_reward_caught_beats_pass():
    # Flagging a contraband bag (risky decision) pays more than a safe pass.
    g = _make_game()
    g._resolve_bag(_bag([ITEMS["GUN"]], flagged=True))
    caught_score = g.score
    g2 = _make_game()
    g2._resolve_bag(_bag([ITEMS["BOOK"]], flagged=False))
    assert caught_score > g2.score


# --- Flagging ---


def test_flag_at_toggles_flag():
    g = _make_game()
    g.bags = [_bag([ITEMS["GUN"]])]  # x=0..64, y=100..140
    assert g._flag_at(32, BAG_Y) is True
    assert g.bags[0].flagged is True
    assert g._flag_at(32, BAG_Y) is True
    assert g.bags[0].flagged is False


def test_flag_at_misses_outside_bounds():
    g = _make_game()
    g.bags = [_bag([ITEMS["GUN"]])]
    assert g._flag_at(200, BAG_Y) is False
    assert g._flag_at(32, 10) is False


def test_flag_at_targets_topmost_bag():
    g = _make_game()
    g.bags = [_bag([ITEMS["GUN"]]), _bag([ITEMS["KNIFE"]])]  # both at x=0
    g._flag_at(32, BAG_Y)
    assert g.bags[1].flagged is True
    assert g.bags[0].flagged is False


# --- Game over ---


def test_game_over_on_security_breach():
    g = _make_game()
    g.security = 0
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER
    assert g.end_reason == "SECURITY BREACH"


def test_game_over_on_shift_complete():
    g = _make_game()
    g.frame = SHIFT_FRAMES
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER
    assert g.end_reason == "SHIFT COMPLETE"


def test_game_over_updates_best_score():
    g = _make_game()
    g.score = 500
    g.frame = SHIFT_FRAMES
    g._check_game_over()
    assert g.best_score == 500


def test_no_game_over_mid_shift():
    g = _make_game()
    g.security = 30
    g.frame = 1000
    g._check_game_over()
    assert g.phase == Phase.PLAYING


# --- Bag movement / spawning ---


def test_update_bags_moves_bags_right():
    g = _make_game()
    g.bags = [_bag([ITEMS["BOOK"]])]
    start_x = g.bags[0].x
    g._update_bags()
    assert g.bags[0].x > start_x


def test_update_bags_resolves_bag_at_edge():
    g = _make_game()
    g.bags = [_bag([ITEMS["GUN"]], flagged=True)]
    g.bags[0].x = 320 - BAG_W  # right edge == RESOLVE_X
    g._update_bags()
    assert g.bags == []  # resolved and removed
    assert g.caught == 1


def test_update_bags_spawns_on_timer():
    g = _make_game()
    g.spawn_timer = 1
    g._update_bags()
    assert len(g.bags) == 1
    assert g.spawn_timer > 0  # reset after spawn


# --- Particle / floating text lifecycle ---


def test_particles_decay_and_removed():
    g = _make_game()
    g.particles = [Particle(10.0, 10.0, 0.0, 0.0, 1, 8)]
    g._update_particles()
    assert g.particles == []


def test_floating_texts_decay_and_removed():
    g = _make_game()
    g.floating_texts = [FloatingText(10.0, 10.0, "+100", 1, 10)]
    g._update_floating_texts()
    assert g.floating_texts == []


def test_apply_outcome_spawns_particles_and_text():
    g = _make_game()
    g._resolve_bag(_bag([ITEMS["GUN"]], flagged=True))
    assert len(g.particles) > 0
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "+100"


def _run_all():
    tests = [
        test_combo_multiplier_basic,
        test_combo_multiplier_caps_at_4,
        test_resolve_outcome_all_cases,
        test_spawn_interval_decreases_with_min,
        test_bag_speed_increases,
        test_max_items_increases_and_caps,
        test_contraband_chance_increases_and_caps,
        test_item_defs_are_correct,
        test_bag_has_contraband,
        test_start_game_initializes_state,
        test_reset_preserves_best_score,
        test_reset_preserves_seeded_rng,
        test_spawn_bag_adds_a_bag,
        test_spawn_bag_respects_item_count_bounds,
        test_caught_grants_score_and_combo,
        test_caught_combo_multiplier_scales_score,
        test_caught_security_clamps_at_100,
        test_false_alarm_resets_combo_and_penalizes,
        test_miss_resets_combo_and_penalizes_more,
        test_pass_grants_small_score_and_combo,
        test_risk_reward_caught_beats_pass,
        test_flag_at_toggles_flag,
        test_flag_at_misses_outside_bounds,
        test_flag_at_targets_topmost_bag,
        test_game_over_on_security_breach,
        test_game_over_on_shift_complete,
        test_game_over_updates_best_score,
        test_no_game_over_mid_shift,
        test_update_bags_moves_bags_right,
        test_update_bags_resolves_bag_at_edge,
        test_update_bags_spawns_on_timer,
        test_particles_decay_and_removed,
        test_floating_texts_decay_and_removed,
        test_apply_outcome_spawns_particles_and_text,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  PASS  {test.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  FAIL  {test.__name__}: {e!r}")
    print(f"\n{passed} passed, {failed} failed out of {len(tests)}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    _run_all()
