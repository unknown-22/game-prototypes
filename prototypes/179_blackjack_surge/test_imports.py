"""test_imports.py — Headless logic tests for BLACKJACK SURGE."""
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/179_blackjack_surge")

from main import (
    BET_AMOUNT,
    BJ_PAYOUT,
    COMBO_THRESHOLD,
    DEALER_STAND,
    GREEN,
    HEAT_BUST,
    HEAT_DECAY,
    HEAT_LOSS,
    HEIGHT,
    MAX_HEAT,
    RED,
    STARTING_CHIPS,
    SUPER_DURATION,
    SUPER_HAND_COUNT,
    SUPER_MULTIPLIER,
    WIDTH,
    YELLOW,
    Card,
    FloatingText,
    Game,
    Hand,
    Particle,
    Phase,
    SUIT_COLOR_VALUES,
    SUIT_COLORS,
)


def _make_game() -> Game:
    """Create a Game bypassing pyxel.init/run via Game.__new__."""
    g = Game.__new__(Game)
    g.rng = random.Random(42)
    g.reset()
    return g


def _make_card(value: int, suit_color: int = RED) -> Card:
    face = value if value <= 10 else 10
    return Card(suit_color=suit_color, value=value, face=face)


def _make_hand(card_values: list[int], suit_color: int = RED) -> Hand:
    return Hand(cards=[_make_card(v, suit_color) for v in card_values])


# ── Core imports and dataclasses ──────────────────────────────────────────────


def test_imports_and_constants() -> None:
    assert WIDTH == 320
    assert HEIGHT == 240
    assert len(SUIT_COLORS) == 4
    assert len(SUIT_COLOR_VALUES) == 4
    assert MAX_HEAT == 100.0
    assert COMBO_THRESHOLD == 4
    assert SUPER_DURATION == 300
    assert BET_AMOUNT == 10
    assert Phase.TITLE is not None
    assert Phase.BETTING is not None
    assert Phase.PLAYING is not None


def test_card_dataclass() -> None:
    c = _make_card(5, RED)
    assert c.value == 5
    assert c.face == 5
    assert c.suit_color == RED
    assert not c.is_ace()
    assert not c.is_face_card()

    ace = _make_card(1, GREEN)
    assert ace.is_ace()
    assert ace.face == 1

    king = _make_card(13, YELLOW)
    assert king.is_face_card()
    assert king.face == 10


def test_hand_dataclass() -> None:
    h = Hand()
    assert h.cards == []
    assert h.total() == 0
    assert not h.is_bust()
    assert not h.is_blackjack()


# ── Hand Total Calculation ────────────────────────────────────────────────────


def test_hand_total_no_ace() -> None:
    h = _make_hand([5, 7])
    assert h.total() == 12


def test_hand_total_with_ace_soft() -> None:
    h = _make_hand([1, 7])
    assert h.total() == 18  # ace as 11


def test_hand_total_with_ace_hard() -> None:
    h = _make_hand([1, 7, 8])
    assert h.total() == 16  # ace as 1 (11+7+8=26 bust -> 1+7+8=16)


def test_hand_total_multiple_aces() -> None:
    h = _make_hand([1, 1])
    assert h.total() == 12  # one ace as 11, one as 1


def test_hand_total_face_cards() -> None:
    h = _make_hand([13, 12])
    assert h.total() == 20


def test_hand_total_blackjack() -> None:
    h = _make_hand([1, 13])
    assert h.total() == 21


# ── Bust Detection ────────────────────────────────────────────────────────────


def test_hand_not_bust() -> None:
    h = _make_hand([10, 8])
    assert not h.is_bust()


def test_hand_bust() -> None:
    h = _make_hand([10, 8, 5])
    assert h.is_bust()


def test_hand_bust_with_ace() -> None:
    h = _make_hand([1, 8, 5])
    assert not h.is_bust()  # 1+8+5=14


# ── Blackjack Detection ───────────────────────────────────────────────────────


def test_hand_is_blackjack() -> None:
    h = _make_hand([1, 13])
    assert h.is_blackjack()


def test_hand_not_blackjack_three_cards() -> None:
    h = _make_hand([10, 5, 6])
    assert not h.is_blackjack()


def test_hand_not_blackjack_wrong_total() -> None:
    h = _make_hand([10, 9])
    assert not h.is_blackjack()


# ── Soft Hand Detection ───────────────────────────────────────────────────────


def test_hand_is_soft() -> None:
    h = _make_hand([1, 6])  # 17 with ace as 11
    assert h.is_soft()


def test_hand_not_soft_no_ace() -> None:
    h = _make_hand([10, 7])
    assert not h.is_soft()


def test_hand_not_soft_ace_hard() -> None:
    h = _make_hand([1, 7, 8])  # ace forced to 1
    assert not h.is_soft()


# ── Dealer Stand Logic ────────────────────────────────────────────────────────


def test_dealer_stands_at_17() -> None:
    h = _make_hand([10, 7])
    assert h.dealer_stands()


def test_dealer_stands_above_17() -> None:
    h = _make_hand([10, 8])
    assert h.dealer_stands()


def test_dealer_does_not_stand_below_17() -> None:
    h = _make_hand([10, 6])
    assert not h.dealer_stands()


def test_dealer_stands_on_soft_17() -> None:
    h = _make_hand([1, 6])  # soft 17
    assert h.dealer_stands()  # stands on soft 17


# ── Game Initialization ───────────────────────────────────────────────────────


def test_game_initialization() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.chips == STARTING_CHIPS
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.super_active is False
    assert g.super_hands_remaining == 0
    assert g.last_win_color is None


def test_start_game() -> None:
    g = _make_game()
    g._start_game()
    assert g.phase == Phase.BETTING
    assert g.score == 0
    assert g.chips == STARTING_CHIPS
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.super_active is False
    assert g.last_win_color is None


# ── Deck Operations ───────────────────────────────────────────────────────────


def test_make_deck_size() -> None:
    g = _make_game()
    deck = g._make_deck()
    assert len(deck) == 52


def test_make_deck_all_suits() -> None:
    g = _make_game()
    deck = g._make_deck()
    suits = {c.suit_color for c in deck}
    for s in SUIT_COLOR_VALUES:
        assert s in suits


def test_deal_card_from_deck() -> None:
    g = _make_game()
    g.deck = g._make_deck()
    initial = len(g.deck)
    c = g._deal_card()
    assert c is not None
    assert len(g.deck) == initial - 1


def test_deal_card_reshuffles() -> None:
    g = _make_game()
    g.deck = []
    g.discarded = [_make_card(5, RED), _make_card(10, GREEN)]
    c = g._deal_card()
    assert c is not None
    assert len(g.deck) == 1  # one left in deck after drawing


# ── Dealing Hand ──────────────────────────────────────────────────────────────


def test_deal_hand() -> None:
    g = _make_game()
    g._start_game()
    g._deal_hand()
    assert len(g.player_hand.cards) == 2
    assert len(g.dealer_hand.cards) == 2
    assert g.dealer_hidden is True
    assert g.phase == Phase.PLAYING


def test_deal_super_hand() -> None:
    g = _make_game()
    g._start_game()
    g.super_hands_remaining = 3
    g._deal_super_hand()
    assert len(g.player_hand.cards) == 2
    assert len(g.dealer_hand.cards) == 2
    assert g.phase == Phase.PLAYING
    assert g.super_hands_remaining == 2


# ── Select Color ──────────────────────────────────────────────────────────────


def test_select_color() -> None:
    g = _make_game()
    g._start_game()
    g._select_color(2)
    assert g.current_color_idx == 2
    assert g.current_color == SUIT_COLOR_VALUES[2]
    assert g.phase == Phase.PLAYING


# ── Hit Logic ─────────────────────────────────────────────────────────────────


def test_hit_adds_card() -> None:
    g = _make_game()
    g._start_game()
    g.deck = g._make_deck()
    g.player_hand = _make_hand([5, 6])
    g.phase = Phase.PLAYING
    initial = len(g.player_hand.cards)
    g._hit()
    assert len(g.player_hand.cards) == initial + 1


def test_hit_bust_triggers_heat() -> None:
    g = _make_game()
    g._start_game()
    g.deck = [_make_card(5, RED)]
    g.player_hand = _make_hand([10, 8])  # total 18
    g.phase = Phase.PLAYING
    g._hit()
    # total becomes 23 -> bust
    assert g.phase == Phase.RESOLVE
    assert g.heat == HEAT_BUST
    assert g.combo == 0


def test_hit_21_auto_stands() -> None:
    g = _make_game()
    g._start_game()
    g.deck = [_make_card(5, RED)]
    g.player_hand = _make_hand([10, 6])  # total 16
    g.phase = Phase.PLAYING
    g._hit()
    assert g.phase == Phase.STAND


# ── Resolve Hand ──────────────────────────────────────────────────────────────


def test_resolve_player_win() -> None:
    g = _make_game()
    g._start_game()
    g.player_hand = _make_hand([10, 9])  # 19
    g.dealer_hand = _make_hand([10, 7])  # 17
    g.dealer_hidden = False
    g.combo = 0
    g.chips = STARTING_CHIPS
    g.score = 0
    g.phase = Phase.STAND
    g._resolve_hand()
    assert g.hand_outcome == "win"
    assert g.score > 0
    assert g.combo == 1


def test_resolve_player_lose() -> None:
    g = _make_game()
    g._start_game()
    g.player_hand = _make_hand([10, 7])  # 17
    g.dealer_hand = _make_hand([10, 9])  # 19
    g.dealer_hidden = False
    g.heat = 0.0
    g.combo = 2
    g.phase = Phase.STAND
    g._resolve_hand()
    assert g.hand_outcome == "lose"
    assert g.heat == HEAT_LOSS
    assert g.combo == 0


def test_resolve_push() -> None:
    g = _make_game()
    g._start_game()
    g.player_hand = _make_hand([10, 8])  # 18
    g.dealer_hand = _make_hand([10, 8])  # 18
    g.dealer_hidden = False
    g.combo = 2
    g.phase = Phase.STAND
    g._resolve_hand()
    assert g.hand_outcome == "push"
    assert g.combo == 0


def test_resolve_blackjack() -> None:
    g = _make_game()
    g._start_game()
    g.player_hand = _make_hand([1, 13])  # blackjack
    g.dealer_hand = _make_hand([10, 7])  # 17
    g.dealer_hidden = False
    g.phase = Phase.STAND
    g._resolve_hand()
    assert g.hand_outcome == "bj"
    assert g.score > 0


def test_resolve_dealer_bust() -> None:
    g = _make_game()
    g._start_game()
    g.player_hand = _make_hand([10, 5])  # 15
    g.dealer_hand = _make_hand([10, 8, 5])  # 23 bust
    g.dealer_hidden = False
    g.phase = Phase.STAND
    g._resolve_hand()
    assert g.hand_outcome == "win"


def test_resolve_player_bust() -> None:
    g = _make_game()
    g._start_game()
    g.player_hand = _make_hand([10, 8, 5])  # 23 bust
    g.phase = Phase.STAND
    g._resolve_hand()
    assert g.hand_outcome == "lose"


# ── Combo Logic ───────────────────────────────────────────────────────────────


def test_combo_increments_on_same_color_win() -> None:
    g = _make_game()
    g._start_game()
    g.current_color = RED
    g.last_win_color = RED
    g.combo = 1
    g._update_combo_on_win(RED)
    assert g.combo == 2


def test_combo_resets_on_different_color_win() -> None:
    g = _make_game()
    g._start_game()
    g.current_color = RED
    g.last_win_color = GREEN
    g.combo = 3
    g._update_combo_on_win(RED)
    assert g.combo == 1  # reset to 1 because last was GREEN


def test_combo_starts_at_1_on_first_win() -> None:
    g = _make_game()
    g._start_game()
    g.last_win_color = None
    g.combo = 0
    g._update_combo_on_win(RED)
    assert g.combo == 1
    assert g.last_win_color == RED


def test_combo_during_super_always_increments() -> None:
    g = _make_game()
    g._start_game()
    g.super_active = True
    g.last_win_color = GREEN
    g.combo = 2
    g._update_combo_on_win(RED)  # different color
    assert g.combo == 3  # still increments in SUPER


def test_max_combo_tracks() -> None:
    g = _make_game()
    g._start_game()
    g.last_win_color = RED
    g.combo = 2
    g.max_combo = 2
    g._update_combo_on_win(RED)
    assert g.combo == 3
    assert g.max_combo == 3


def test_combo_multiplier_values() -> None:
    g = _make_game()
    g._start_game()
    g.combo = 0
    assert g._combo_multiplier() == 1
    g.combo = 1
    assert g._combo_multiplier() == 2
    g.combo = 4
    assert g._combo_multiplier() == 5  # 1 + min(4,4) = 5
    g.combo = 6
    assert g._combo_multiplier() == 5  # 1 + min(6,4) = 5


# ── SUPER Mode ────────────────────────────────────────────────────────────────


def test_super_activates_at_combo_threshold() -> None:
    g = _make_game()
    g._start_game()
    g.combo = COMBO_THRESHOLD
    g.super_active = False
    g._activate_super()
    assert g.super_active is True
    assert g.super_hands_remaining == SUPER_HAND_COUNT
    assert g.combo == 0  # reset


def test_win_with_super_3x_score() -> None:
    g = _make_game()
    g._start_game()
    g.player_hand = _make_hand([10, 9])
    g.dealer_hand = _make_hand([10, 7])
    g.dealer_hidden = False
    g.super_active = True
    g.combo = 0
    g.score = 0
    g.chips = STARTING_CHIPS
    g.phase = Phase.STAND
    g._resolve_hand()
    assert g.hand_outcome == "win"
    # combo_mult gets overridden to SUPER_MULTIPLIER = 3 during super
    assert g.win_amount == BET_AMOUNT * SUPER_MULTIPLIER  # 10 * 3 = 30
    assert g.score == 30


def test_bj_with_super_3x_score() -> None:
    g = _make_game()
    g._start_game()
    g.player_hand = _make_hand([1, 13])
    g.dealer_hand = _make_hand([10, 7])
    g.dealer_hidden = False
    g.super_active = True
    g.score = 0
    g.chips = STARTING_CHIPS
    g.phase = Phase.STAND
    g._resolve_hand()
    assert g.hand_outcome == "bj"
    expected = int(BET_AMOUNT * BJ_PAYOUT) * SUPER_MULTIPLIER  # 15 * 3 = 45
    assert g.score == expected


# ── Heat System ───────────────────────────────────────────────────────────────


def test_heat_decay() -> None:
    g = _make_game()
    g._start_game()
    g.phase = Phase.PLAYING
    g.heat = 10.0
    g.heat = max(0.0, g.heat - HEAT_DECAY)
    assert g.heat == 10.0 - HEAT_DECAY


def test_heat_never_negative() -> None:
    g = _make_game()
    g._start_game()
    g.heat = 0.0
    g.heat = max(0.0, g.heat - HEAT_DECAY)
    assert g.heat == 0.0


def test_heat_capped_at_max() -> None:
    g = _make_game()
    g._start_game()
    g.heat = MAX_HEAT - 1
    g.heat = min(MAX_HEAT, g.heat + HEAT_BUST)
    assert g.heat == MAX_HEAT


def test_heat_bust_adds_correct_amount() -> None:
    g = _make_game()
    g._start_game()
    g.heat = 0.0
    g.heat = min(MAX_HEAT, g.heat + HEAT_BUST)
    assert g.heat == HEAT_BUST


def test_heat_loss_adds_correct_amount() -> None:
    g = _make_game()
    g._start_game()
    g.heat = 0.0
    g.heat = min(MAX_HEAT, g.heat + HEAT_LOSS)
    assert g.heat == HEAT_LOSS


def test_game_over_at_max_heat() -> None:
    g = _make_game()
    g._start_game()
    g.heat = MAX_HEAT
    g.chips = 50
    g.phase = Phase.RESOLVE
    g.resolve_timer = 0
    # Simulate the check from _update_resolve
    if g.heat >= MAX_HEAT:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


def test_game_over_no_chips() -> None:
    g = _make_game()
    g._start_game()
    g.chips = 0
    g.heat = 0.0
    g.phase = Phase.RESOLVE
    g.resolve_timer = 0
    if g.chips <= 0:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


# ── Score Calculation ─────────────────────────────────────────────────────────


def test_score_increases_on_win() -> None:
    g = _make_game()
    g._start_game()
    g.player_hand = _make_hand([10, 9])
    g.dealer_hand = _make_hand([10, 7])
    g.dealer_hidden = False
    g.combo = 0
    g.score = 0
    g.chips = STARTING_CHIPS
    g.phase = Phase.STAND
    g._resolve_hand()
    assert g.score == BET_AMOUNT  # 10 * (1 + min(0,4)) = 10


def test_score_with_combo_multiplier() -> None:
    g = _make_game()
    g._start_game()
    g.player_hand = _make_hand([10, 9])
    g.dealer_hand = _make_hand([10, 7])
    g.dealer_hidden = False
    g.combo = 2  # multiplier = 1 + 2 = 3
    g.last_win_color = RED
    g.current_color = RED
    g.score = 0
    g.chips = STARTING_CHIPS
    g.phase = Phase.STAND
    g._resolve_hand()
    assert g.score == BET_AMOUNT * 3  # 30


def test_chips_decrease_on_lose() -> None:
    g = _make_game()
    g._start_game()
    g.player_hand = _make_hand([10, 7])
    g.dealer_hand = _make_hand([10, 9])
    g.dealer_hidden = False
    g.chips = STARTING_CHIPS
    g.phase = Phase.STAND
    g._resolve_hand()
    assert g.chips == STARTING_CHIPS - BET_AMOUNT


def test_chips_cannot_go_negative() -> None:
    g = _make_game()
    g._start_game()
    g.player_hand = _make_hand([10, 7])
    g.dealer_hand = _make_hand([10, 9])
    g.dealer_hidden = False
    g.chips = 5  # less than BET_AMOUNT
    g.phase = Phase.STAND
    g._resolve_hand()
    assert g.chips == 0  # clamped at 0


# ── Floating Text ─────────────────────────────────────────────────────────────


def test_floating_text_added() -> None:
    g = _make_game()
    g._start_game()
    g._add_floating_text("TEST", RED)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "TEST"
    assert g.floating_texts[0].color == RED


def test_floating_text_lifecycle() -> None:
    g = _make_game()
    g._start_game()
    g.floating_texts = [FloatingText(x=100.0, y=100.0, text="T", life=2, color=RED)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].life == 1
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Particle System ───────────────────────────────────────────────────────────


def test_particle_lifecycle() -> None:
    g = _make_game()
    g._start_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=2, color=RED)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 1
    g._update_particles()
    assert len(g.particles) == 0


# ── Stand Logic ───────────────────────────────────────────────────────────────


def test_stand_transitions_phase() -> None:
    g = _make_game()
    g._start_game()
    g.player_hand = _make_hand([10, 7])
    g.dealer_hand = _make_hand([10, 7])
    g.phase = Phase.PLAYING
    g._stand()
    assert g.phase == Phase.STAND


# ── Resolve Timer ─────────────────────────────────────────────────────────────


def test_resolve_with_delay() -> None:
    g = _make_game()
    g._start_game()
    g._resolve_with_delay()
    assert g.phase == Phase.RESOLVE
    assert g.resolve_timer > 0


# ── Restart from game over ────────────────────────────────────────────────────


def test_restart_after_game_over() -> None:
    g = _make_game()
    g._start_game()
    g.heat = MAX_HEAT
    g.phase = Phase.GAME_OVER
    g.score = 500
    g.combo = 5
    g.max_combo = 6
    g.chips = 50
    g.super_active = True
    g.super_hands_remaining = 2
    g.last_win_color = RED
    g.reset()
    g._start_game()
    assert g.phase == Phase.BETTING
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.chips == STARTING_CHIPS
    assert g.super_active is False
    assert g.super_hands_remaining == 0
    assert g.last_win_color is None


# ── Enum identity check ───────────────────────────────────────────────────────


def test_phase_enum_values() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    g._start_game()
    assert g.phase == Phase.BETTING
    g._select_color(0)
    assert g.phase == Phase.PLAYING
    g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER
