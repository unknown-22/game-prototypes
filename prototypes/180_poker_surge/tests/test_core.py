"""Tests for 180_poker_surge core logic."""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import (  # type: ignore[import-untyped]
    BET,
    HEAT_FOLD,
    HEAT_LOSE,
    HEAT_MAX,
    MAX_REDRAWS,
    START_CHIPS,
    SUPER_HANDS,
    SUPER_MULTIPLIER,
    WIN_MULTIPLIERS,
    Card,
    Game,
    Particle,
    Phase,
)


def make_game() -> Game:
    """Create a headless Game instance for testing."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.score = 0
    g.chips = START_CHIPS
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.player_hand = []
    g.dealer_hand = []
    g.held = []
    g.redraws_remaining = 0
    g.result_timer = 0
    g.result_text = ""
    g.result_color = 7
    g.super_hands_remaining = 0
    g._last_win_suit = None
    g.particles = []
    g._shake_timer = 0
    g._prev_mouse_pressed = False
    g._folded = False
    g.high_score = 0
    g.high_combo = 0
    g._first_hand = True
    g._deck = []
    g._player_wins = False
    g._win_amount = 0
    g.reset()
    return g


def _c(suit: int, rank: int) -> Card:
    return Card(suit, rank)


# ═══════════════════════════════════════════════════════════════
# Hand Evaluation
# ═══════════════════════════════════════════════════════════════

def test_eval_royal_flush() -> None:
    g = make_game()
    cards = [_c(0, 14), _c(0, 13), _c(0, 12), _c(0, 11), _c(0, 10)]
    h = g._eval_hand(cards)
    assert h.rank == 9
    assert h.name == "Royal"


def test_eval_straight_flush() -> None:
    g = make_game()
    cards = [_c(1, 9), _c(1, 8), _c(1, 7), _c(1, 6), _c(1, 5)]
    h = g._eval_hand(cards)
    assert h.rank == 8
    assert h.name == "StrFlush"
    assert h.value == 9


def test_eval_straight_flush_ace_low() -> None:
    g = make_game()
    cards = [_c(2, 14), _c(2, 2), _c(2, 3), _c(2, 4), _c(2, 5)]
    h = g._eval_hand(cards)
    assert h.rank == 8
    assert h.value == 5


def test_eval_four_kind() -> None:
    g = make_game()
    cards = [_c(0, 7), _c(1, 7), _c(2, 7), _c(3, 7), _c(0, 3)]
    h = g._eval_hand(cards)
    assert h.rank == 7
    assert h.name == "Quads"


def test_eval_full_house() -> None:
    g = make_game()
    cards = [_c(0, 10), _c(1, 10), _c(2, 10), _c(3, 5), _c(0, 5)]
    h = g._eval_hand(cards)
    assert h.rank == 6
    assert h.name == "FullHouse"


def test_eval_flush() -> None:
    g = make_game()
    cards = [_c(0, 14), _c(0, 8), _c(0, 5), _c(0, 3), _c(0, 2)]
    h = g._eval_hand(cards)
    assert h.rank == 5
    assert h.name == "Flush"


def test_eval_straight() -> None:
    g = make_game()
    cards = [_c(0, 9), _c(1, 8), _c(2, 7), _c(3, 6), _c(0, 5)]
    h = g._eval_hand(cards)
    assert h.rank == 4
    assert h.name == "Straight"
    assert h.value == 9


def test_eval_straight_ace_low() -> None:
    g = make_game()
    cards = [_c(0, 14), _c(1, 2), _c(2, 3), _c(3, 4), _c(0, 5)]
    h = g._eval_hand(cards)
    assert h.rank == 4
    assert h.value == 5


def test_eval_three_kind() -> None:
    g = make_game()
    cards = [_c(0, 8), _c(1, 8), _c(2, 8), _c(3, 5), _c(0, 2)]
    h = g._eval_hand(cards)
    assert h.rank == 3
    assert h.name == "Trips"


def test_eval_two_pair() -> None:
    g = make_game()
    cards = [_c(0, 10), _c(1, 10), _c(2, 5), _c(3, 5), _c(0, 2)]
    h = g._eval_hand(cards)
    assert h.rank == 2
    assert h.name == "Two Pair"


def test_eval_one_pair() -> None:
    g = make_game()
    cards = [_c(0, 11), _c(1, 11), _c(2, 7), _c(3, 4), _c(0, 2)]
    h = g._eval_hand(cards)
    assert h.rank == 1
    assert h.name == "One Pair"


def test_eval_high_card() -> None:
    g = make_game()
    cards = [_c(0, 14), _c(1, 9), _c(2, 6), _c(3, 3), _c(0, 2)]
    h = g._eval_hand(cards)
    assert h.rank == 0
    assert h.name == "High Card"


# ═══════════════════════════════════════════════════════════════
# Hand Comparison / Tiebreaking
# ═══════════════════════════════════════════════════════════════

def test_compare_hands_rank_beats_lower() -> None:
    g = make_game()
    flush = g._eval_hand([_c(0, 14), _c(0, 8), _c(0, 5), _c(0, 3), _c(0, 2)])
    straight = g._eval_hand([_c(0, 9), _c(1, 8), _c(2, 7), _c(3, 6), _c(1, 5)])
    assert g._compare_hands(flush, straight) == 1


def test_compare_hands_pair_tiebreaker() -> None:
    g = make_game()
    hi_pair = g._eval_hand([_c(0, 14), _c(1, 14), _c(2, 5), _c(3, 3), _c(0, 2)])
    lo_pair = g._eval_hand([_c(0, 13), _c(1, 13), _c(2, 5), _c(3, 3), _c(0, 2)])
    assert g._compare_hands(hi_pair, lo_pair) == 1
    assert g._compare_hands(lo_pair, hi_pair) == -1


def test_compare_hands_pair_kicker() -> None:
    g = make_game()
    hi_kick = g._eval_hand([_c(0, 14), _c(1, 14), _c(2, 13), _c(3, 3), _c(0, 2)])
    lo_kick = g._eval_hand([_c(0, 14), _c(1, 14), _c(2, 12), _c(3, 3), _c(0, 2)])
    assert g._compare_hands(hi_kick, lo_kick) == 1


def test_compare_hands_two_pair() -> None:
    g = make_game()
    hp = g._eval_hand([_c(0, 14), _c(1, 14), _c(2, 10), _c(3, 10), _c(0, 2)])
    lp = g._eval_hand([_c(0, 14), _c(1, 14), _c(2, 9), _c(3, 9), _c(0, 2)])
    assert g._compare_hands(hp, lp) == 1


def test_compare_hands_full_house() -> None:
    g = make_game()
    hi_trips = g._eval_hand([_c(0, 10), _c(1, 10), _c(2, 10), _c(3, 5), _c(0, 5)])
    lo_trips = g._eval_hand([_c(0, 9), _c(1, 9), _c(2, 9), _c(3, 14), _c(0, 14)])
    assert g._compare_hands(hi_trips, lo_trips) == 1


def test_compare_hands_straight_ace_low() -> None:
    g = make_game()
    ace_low = g._eval_hand([_c(0, 14), _c(1, 2), _c(2, 3), _c(3, 4), _c(1, 5)])
    low = g._eval_hand([_c(0, 6), _c(1, 5), _c(2, 4), _c(3, 3), _c(0, 2)])
    assert g._compare_hands(low, ace_low) == 1  # 6-high beats 5-high
    assert g._compare_hands(ace_low, low) == -1


# ═══════════════════════════════════════════════════════════════
# Hand suit detection
# ═══════════════════════════════════════════════════════════════

def test_hand_suit_majority() -> None:
    g = make_game()
    cards = [_c(0, 14), _c(0, 8), _c(0, 5), _c(1, 3), _c(2, 2)]
    assert g._hand_suit(cards) == 0


def test_hand_suit_tie_uses_highest_rank() -> None:
    g = make_game()
    cards = [_c(0, 14), _c(1, 14), _c(2, 5), _c(3, 5), _c(0, 2)]
    assert g._hand_suit(cards) == 0  # tied, highest rank is suit 0


# ═══════════════════════════════════════════════════════════════
# COMBO Chain Logic
# ═══════════════════════════════════════════════════════════════

def test_combo_starts_at_one_on_first_win() -> None:
    g = make_game()
    g.combo = 0
    g._last_win_suit = None
    g.player_hand = [_c(0, 14), _c(0, 8), _c(0, 5), _c(0, 3), _c(0, 2)]
    g.dealer_hand = [_c(1, 10), _c(1, 7), _c(1, 4), _c(1, 2), _c(2, 2)]
    g._resolve_hand()
    assert g.combo == 1
    assert g._last_win_suit == 0


def test_combo_increments_on_same_suit_win() -> None:
    g = make_game()
    g._last_win_suit = 0  # previous win with suit 0
    g.player_hand = [_c(0, 14), _c(0, 8), _c(0, 5), _c(0, 3), _c(0, 2)]
    g.dealer_hand = [_c(1, 10), _c(1, 7), _c(1, 4), _c(1, 2), _c(2, 2)]
    g._resolve_hand()
    assert g.combo == 1  # starts fresh combo; _resolve_hand sets to 1 on match, not incrementing previous
    # Re-test with pre-set combo
    g.combo = 2
    g._last_win_suit = 0
    g._resolve_hand()
    assert g.combo == 3


def test_combo_resets_on_different_suit_win() -> None:
    g = make_game()
    g._last_win_suit = 0
    g.combo = 3
    g.player_hand = [_c(1, 14), _c(1, 8), _c(1, 5), _c(0, 3), _c(0, 2)]  # suit 1 majority, high card Ace
    g.dealer_hand = [_c(2, 9), _c(3, 8), _c(2, 6), _c(3, 5), _c(2, 3)]  # high card 9, all different = no pair
    g._resolve_hand()
    assert g.combo == 1
    assert g._last_win_suit == 1


def test_combo_resets_on_loss() -> None:
    g = make_game()
    g._last_win_suit = 0
    g.combo = 3
    g.player_hand = [_c(1, 5), _c(1, 4), _c(1, 3), _c(2, 2), _c(3, 2)]
    g.dealer_hand = [_c(0, 14), _c(0, 13), _c(0, 12), _c(0, 11), _c(0, 10)]  # royal flush
    g._resolve_hand()
    assert g.combo == 0
    assert g._last_win_suit is None


def test_max_combo_tracked() -> None:
    g = make_game()
    g._last_win_suit = 0
    g.combo = 3
    g.max_combo = 3
    g.player_hand = [_c(0, 14), _c(0, 13), _c(0, 12), _c(0, 11), _c(0, 10)]
    g.dealer_hand = [_c(1, 7), _c(1, 6), _c(1, 5), _c(2, 3), _c(3, 2)]
    g._resolve_hand()
    assert g.combo == 4
    assert g.max_combo == 4


# ═══════════════════════════════════════════════════════════════
# SUPER Mode
# ═══════════════════════════════════════════════════════════════

def test_super_activates_at_combo_threshold() -> None:
    g = make_game()
    g._last_win_suit = 0
    g.combo = 3
    g.player_hand = [_c(0, 14), _c(0, 13), _c(0, 12), _c(1, 2), _c(2, 2)]  # pair of 2s
    g.dealer_hand = [_c(1, 9), _c(2, 8), _c(3, 6), _c(1, 4), _c(2, 2)]  # high card 9, no pair (only one 2)
    assert g.super_hands_remaining == 0
    g._resolve_hand()
    assert g.combo == 4
    assert g.super_hands_remaining == SUPER_HANDS
    assert g._shake_timer == 30


def test_super_mode_auto_wins() -> None:
    g = make_game()
    g.super_hands_remaining = 3
    g.chips = 500
    g.score = 0
    g.player_hand = [_c(0, 5), _c(1, 4), _c(2, 3), _c(3, 2), _c(0, 2)]  # terrible hand
    g.dealer_hand = [_c(0, 14), _c(0, 13), _c(0, 12), _c(0, 11), _c(0, 10)]  # royal flush
    prev_chips = g.chips
    g._resolve_hand()
    assert g._player_wins is True
    assert g.chips > prev_chips
    assert g.super_hands_remaining == 2


def test_super_mode_3x_score() -> None:
    g = make_game()
    g.super_hands_remaining = 1
    g.chips = 500
    g.player_hand = [_c(0, 14), _c(0, 13), _c(0, 12), _c(0, 11), _c(0, 10)]  # royal flush
    g.dealer_hand = [_c(1, 7), _c(1, 6), _c(1, 5), _c(2, 4), _c(3, 3)]
    prev = g.chips
    g._resolve_hand()
    gain = g.chips - prev
    normal_gain = BET * WIN_MULTIPLIERS[9]
    assert gain == normal_gain * SUPER_MULTIPLIER


def test_super_mode_expires() -> None:
    g = make_game()
    g.super_hands_remaining = 1
    g.chips = 500
    g.player_hand = [_c(0, 14), _c(0, 13), _c(0, 12), _c(0, 11), _c(0, 10)]
    g.dealer_hand = [_c(1, 7), _c(1, 6), _c(1, 5), _c(2, 4), _c(3, 3)]
    g._resolve_hand()
    assert g.super_hands_remaining == 0
    assert g.combo == 0
    assert g._last_win_suit is None


# ═══════════════════════════════════════════════════════════════
# HEAT & Game Over
# ═══════════════════════════════════════════════════════════════

def test_heat_increases_on_lose() -> None:
    g = make_game()
    g.heat = 0.0
    g.player_hand = [_c(0, 5), _c(1, 4), _c(2, 3), _c(3, 2), _c(0, 2)]
    g.dealer_hand = [_c(0, 14), _c(0, 13), _c(0, 12), _c(0, 11), _c(0, 10)]
    g._resolve_hand()
    assert g.heat == HEAT_LOSE


def test_heat_increases_on_fold() -> None:
    g = make_game()
    g.chips = 500
    g._start_deal()
    g.heat = 0.0
    g._do_fold()
    assert g.heat == HEAT_FOLD
    assert g.combo == 0


def test_heat_100_triggers_game_over() -> None:
    g = make_game()
    g.heat = HEAT_MAX
    g.chips = 500
    g._start_deal()
    g._go_next_hand()
    assert g.phase == Phase.GAME_OVER


def test_no_chips_triggers_game_over() -> None:
    g = make_game()
    g.chips = 5
    g.heat = 0
    g._go_next_hand()
    assert g.phase == Phase.GAME_OVER


def test_heat_decay() -> None:
    g = make_game()
    g.heat = 50.0
    g._update_heat_decay()
    assert g.heat == 50.0 - 0.02


def test_heat_never_negative() -> None:
    g = make_game()
    g.heat = 0.0
    g._update_heat_decay()
    assert g.heat == 0.0


# ═══════════════════════════════════════════════════════════════
# Win Multipliers
# ═══════════════════════════════════════════════════════════════

def test_win_multiplier_royal_flush() -> None:
    g = make_game()
    g.chips = 500
    g.player_hand = [_c(0, 14), _c(0, 13), _c(0, 12), _c(0, 11), _c(0, 10)]
    g.dealer_hand = [_c(1, 7), _c(1, 6), _c(1, 5), _c(2, 4), _c(3, 3)]
    prev = g.chips
    g._resolve_hand()
    assert g.chips - prev == BET * WIN_MULTIPLIERS[9]  # 25x


def test_win_multiplier_pair() -> None:
    g = make_game()
    g.chips = 500
    g.player_hand = [_c(0, 14), _c(1, 14), _c(2, 7), _c(3, 4), _c(0, 2)]
    g.dealer_hand = [_c(1, 7), _c(1, 6), _c(1, 5), _c(1, 3), _c(2, 2)]
    prev = g.chips
    g._resolve_hand()
    assert g.chips - prev == BET * WIN_MULTIPLIERS[1]  # 1x


# ═══════════════════════════════════════════════════════════════
# Chip Management
# ═══════════════════════════════════════════════════════════════

def test_chips_deducted_on_auto_bet() -> None:
    g = make_game()
    g.chips = 100
    g.heat = 0
    g._start_deal()
    g._go_next_hand()
    assert g.chips == 90  # 100 - BET
    assert g.phase == Phase.DEAL_HOLD


def test_chips_start_at_100() -> None:
    g = make_game()
    assert g.chips == START_CHIPS


# ═══════════════════════════════════════════════════════════════
# Deck & Redraw
# ═══════════════════════════════════════════════════════════════

def test_deck_has_52_cards() -> None:
    g = make_game()
    deck = g._make_deck()
    assert len(deck) == 52


def test_start_deal_gives_5_cards_each() -> None:
    g = make_game()
    g._start_deal()
    assert len(g.player_hand) == 5
    assert len(g.dealer_hand) == 5
    assert len(g._deck) == 42
    assert g.held == [False] * 5
    assert g.redraws_remaining == MAX_REDRAWS


def test_redraw_replaces_unheld_cards() -> None:
    g = make_game()
    g._rng = random.Random(42)
    g._start_deal()
    original = [c for c in g.player_hand]
    g.held[0] = True
    g.held[1] = True
    g._do_redraw()
    assert g.player_hand[0] == original[0]
    assert g.player_hand[1] == original[1]
    assert g.redraws_remaining == MAX_REDRAWS - 1


def test_held_resets_after_redraw() -> None:
    g = make_game()
    g._start_deal()
    g.held = [True] * 5
    g._do_redraw()
    assert g.held == [False] * 5


# ═══════════════════════════════════════════════════════════════
# Fold
# ═══════════════════════════════════════════════════════════════

def test_fold_resets_combo() -> None:
    g = make_game()
    g.chips = 500
    g.combo = 3
    g._last_win_suit = 0
    g._start_deal()
    g._do_fold()
    assert g.combo == 0
    assert g._last_win_suit is None
    assert g._folded is True
    assert g.phase == Phase.RESULT


# ═══════════════════════════════════════════════════════════════
# Reset
# ═══════════════════════════════════════════════════════════════

def test_reset_restores_initial_state() -> None:
    g = make_game()
    g.score = 500
    g.chips = 50
    g.combo = 3
    g.max_combo = 3
    g.heat = 80.0
    g.super_hands_remaining = 2
    g._last_win_suit = 1
    g.particles.append(Particle(10, 10, 1, 1, 20, 7))
    g.phase = Phase.GAME_OVER
    g._folded = True
    g._first_hand = False

    g.reset()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.chips == START_CHIPS
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_hands_remaining == 0
    assert g._last_win_suit is None
    assert g.particles == []
    assert g._folded is False
    assert g._first_hand is True


# ═══════════════════════════════════════════════════════════════
# Score Tracking
# ═══════════════════════════════════════════════════════════════

def test_score_accumulates_on_win() -> None:
    g = make_game()
    g.chips = 500
    g.score = 100
    g.player_hand = [_c(0, 14), _c(1, 14), _c(2, 7), _c(3, 4), _c(0, 2)]
    g.dealer_hand = [_c(1, 7), _c(1, 6), _c(1, 5), _c(1, 3), _c(2, 2)]
    g._resolve_hand()
    assert g.score > 100


def test_score_does_not_change_on_loss() -> None:
    g = make_game()
    g.chips = 500
    g.score = 100
    g.player_hand = [_c(1, 5), _c(1, 4), _c(1, 3), _c(2, 2), _c(3, 2)]
    g.dealer_hand = [_c(0, 14), _c(0, 13), _c(0, 12), _c(0, 11), _c(0, 10)]
    g._resolve_hand()
    assert g.score == 100


# ═══════════════════════════════════════════════════════════════
# Edge Cases
# ═══════════════════════════════════════════════════════════════

def test_no_duplicate_cards_in_deck() -> None:
    g = make_game()
    deck = g._make_deck()
    cards_set = {(c.suit, c.rank) for c in deck}
    assert len(cards_set) == 52


def test_all_suits_have_13_cards() -> None:
    g = make_game()
    deck = g._make_deck()
    for suit in range(4):
        assert len([c for c in deck if c.suit == suit]) == 13


def test_royal_flush_beats_straight_flush() -> None:
    g = make_game()
    royal = g._eval_hand([_c(0, 14), _c(0, 13), _c(0, 12), _c(0, 11), _c(0, 10)])
    straight = g._eval_hand([_c(0, 9), _c(0, 8), _c(0, 7), _c(0, 6), _c(0, 5)])
    assert royal.rank > straight.rank


def test_hand_with_5_cards_required() -> None:
    g = make_game()
    try:
        g._eval_hand([_c(0, 14)])
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_player_win_updates_last_win_suit() -> None:
    g = make_game()
    g.player_hand = [_c(0, 14), _c(0, 13), _c(0, 12), _c(0, 11), _c(0, 10)]
    g.dealer_hand = [_c(1, 7), _c(1, 6), _c(1, 5), _c(2, 4), _c(3, 3)]
    g._last_win_suit = None
    g._resolve_hand()
    assert g._last_win_suit == 0
    assert g.combo == 1


def test_super_not_reactivated_during_super() -> None:
    g = make_game()
    g.super_hands_remaining = 2
    g.combo = 5  # above threshold
    g._last_win_suit = 0
    prev_super = g.super_hands_remaining
    g.player_hand = [_c(0, 14), _c(0, 13), _c(0, 12), _c(0, 11), _c(0, 10)]
    g.dealer_hand = [_c(1, 7), _c(1, 6), _c(1, 5), _c(2, 4), _c(3, 3)]
    g._resolve_hand()
    assert g.super_hands_remaining == prev_super - 1


def test_high_score_persists_across_game_over() -> None:
    g = make_game()
    g.score = 500
    g.max_combo = 3
    g.high_score = 0
    g.high_combo = 0
    g.chips = 5
    g.heat = 0
    g._go_next_hand()
    assert g.high_score == 500
    assert g.high_combo == 3
    assert g.phase == Phase.GAME_OVER


# ═══════════════════════════════════════════════════════════════
# Particles
# ═══════════════════════════════════════════════════════════════

def test_particles_spawn_on_fold() -> None:
    g = make_game()
    g.chips = 500
    g._start_deal()
    assert len(g.particles) == 0
    g._do_fold()
    assert len(g.particles) == 12


def test_particles_decay_life() -> None:
    g = make_game()
    g.particles.append(Particle(10, 10, 1, 1, 30, 7))
    g._update_particles()
    assert g.particles[0].life == 29


def test_particles_removed_when_life_zero() -> None:
    g = make_game()
    g.particles.append(Particle(10, 10, 1, 1, 0, 7))
    g._update_particles()
    assert len(g.particles) == 0


def test_particles_move() -> None:
    g = make_game()
    g.particles.append(Particle(10.0, 10.0, 2.0, 3.0, 30, 7))
    g._update_particles()
    assert g.particles[0].x == 12.0
    assert g.particles[0].y == 13.0
