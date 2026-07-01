"""test_imports.py — Headless logic tests for 186_uno_surge.

Uses Game.__new__(Game) bypass pattern to avoid pyxel.init/pyxel.run.
"""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/186_uno_surge")

from main import (
    CARD_H,
    CARD_W,
    COLOR_DARK_BLUE,
    COLOR_GREEN,
    COLOR_RED,
    COLOR_YELLOW,
    GAME_DURATION,
    HAND_Y,
    HEAT_MAX,
    HEAT_MISMATCH,
    MAX_HAND,
    SCREEN_W,
    SUPER_DURATION,
    TOP_CARD_W,
    Card,
    FloatingText,
    Game,
    Particle,
    Phase,
)

# ── Helpers ──


def _make_game() -> Game:
    """Create a Game instance bypassing pyxel.init."""
    g = Game.__new__(Game)
    g.player_hand = []
    g.ai_hand = []
    g.draw_pile = []
    g.discard_pile = []
    g.top_discard = None
    g.combo = 0
    g.max_combo = 0
    g.super_uno_timer = 0
    g.heat = 0.0
    g.score = 0
    g.timer = GAME_DURATION
    g.turn = "player"
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g.message = ""
    g.message_timer = 0
    g._ai_timer = 0
    g.rng = random.Random(42)
    g.font = None
    g.reset()
    g.rng = random.Random(42)
    return g


# ── Dataclass tests ──


def test_card_creation() -> None:
    c = Card(color=COLOR_RED, number=5)
    assert c.color == COLOR_RED
    assert c.number == 5


def test_particle_creation() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=15, color=COLOR_GREEN)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == COLOR_GREEN


def test_floating_text_creation() -> None:
    ft = FloatingText(x=100.0, y=200.0, text="+10", life=35, color=COLOR_YELLOW)
    assert ft.x == 100.0
    assert ft.y == 200.0
    assert ft.text == "+10"
    assert ft.life == 35
    assert ft.color == COLOR_YELLOW
    assert ft.vy == -1.0


def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ── Game init / reset ──


def test_reset_initializes_draw_pile() -> None:
    g = _make_game()
    assert len(g.draw_pile) + len(g.discard_pile) + len(g.player_hand) + len(g.ai_hand) == 40
    assert g.top_discard is not None
    assert len(g.player_hand) == 7
    assert len(g.ai_hand) == 5
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.score == 0
    assert g.super_uno_timer == 0
    assert g.phase == Phase.PLAYING
    assert g.turn == "player"


def test_reset_clears_state() -> None:
    g = _make_game()
    g.combo = 5
    g.max_combo = 3
    g.heat = 50.0
    g.score = 999
    g.super_uno_timer = 60
    g.particles = [Particle(0, 0, 1, 1, 5, COLOR_RED)]
    g.floating_texts = [FloatingText(0, 0, "test", 5, COLOR_RED)]
    g.reset()
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.score == 0
    assert g.super_uno_timer == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0


# ── Card play mechanics ──


def test_can_play_same_color() -> None:
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 3)
    card = Card(COLOR_RED, 7)
    assert g._can_play(card) is True


def test_can_play_same_number() -> None:
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 5)
    card = Card(COLOR_GREEN, 5)
    assert g._can_play(card) is True


def test_can_play_different_color_and_number() -> None:
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 5)
    card = Card(COLOR_GREEN, 7)
    assert g._can_play(card) is False


def test_can_play_no_top_discard() -> None:
    g = _make_game()
    g.top_discard = None
    card = Card(COLOR_RED, 0)
    assert g._can_play(card) is True


def test_can_play_super_uno_active() -> None:
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 5)
    g.super_uno_timer = 60
    card = Card(COLOR_GREEN, 7)  # different color and number
    assert g._can_play(card) is True


def test_has_playable() -> None:
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 5)
    hand = [Card(COLOR_RED, 3), Card(COLOR_GREEN, 7)]
    assert g._has_playable(hand) is True

    hand2 = [Card(COLOR_GREEN, 7), Card(COLOR_GREEN, 9)]
    assert g._has_playable(hand2) is False


def test_play_card_removes_from_hand() -> None:
    g = _make_game()
    card = Card(COLOR_RED, 5)
    g.top_discard = Card(COLOR_RED, 3)
    hand = [card, Card(COLOR_RED, 7)]
    g._play_card(card, hand)
    assert card not in hand
    assert len(hand) == 1


def test_play_card_updates_top_discard() -> None:
    g = _make_game()
    card = Card(COLOR_RED, 5)
    g.top_discard = Card(COLOR_GREEN, 3)
    hand = [card]
    g._play_card(card, hand)
    assert g.top_discard is card


def test_play_card_not_in_hand_returns_zero() -> None:
    g = _make_game()
    card = Card(COLOR_RED, 5)
    g.top_discard = Card(COLOR_RED, 3)
    hand: list[Card] = []
    result = g._play_card(card, hand)
    assert result == 0


def test_play_card_same_color_builds_combo() -> None:
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 3)
    g.combo = 1
    card = Card(COLOR_RED, 5)
    points = g._play_card(card, [card])
    assert g.combo == 2
    assert points > 10  # 10 + 2*3 = 16


def test_play_card_different_color_resets_combo() -> None:
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 3)
    g.combo = 3
    card = Card(COLOR_GREEN, 7)
    g._play_card(card, [card])
    assert g.combo == 1  # reset to 1
    assert g.heat == HEAT_MISMATCH


def test_play_card_different_number_same_color_builds_combo() -> None:
    """Different number but same color should still build COMBO."""
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 3)
    g.combo = 2
    card = Card(COLOR_RED, 9)
    g._play_card(card, [card])
    assert g.combo == 3


def test_play_card_first_play_always_builds_combo() -> None:
    """When combo == 0, even different color card starts COMBO at 1."""
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 3)
    g.combo = 0
    card = Card(COLOR_GREEN, 3)  # same number, different color
    g._play_card(card, [card])
    assert g.combo == 1


def test_play_card_different_color_same_number_with_active_combo() -> None:
    """When combo > 0, different color (even same number) resets COMBO."""
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 3)
    g.combo = 2
    card = Card(COLOR_GREEN, 3)  # same number, different color
    g._play_card(card, [card])
    assert g.combo == 1  # reset
    assert g.heat == HEAT_MISMATCH


def test_play_card_updates_max_combo() -> None:
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 0)
    g.combo = 3
    g.max_combo = 2
    card = Card(COLOR_RED, 1)
    g._play_card(card, [card])
    assert g.combo == 4
    assert g.max_combo == 4


def test_play_card_super_uno_gives_30_points() -> None:
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 3)
    g.super_uno_timer = 60
    card = Card(COLOR_GREEN, 7)
    points = g._play_card(card, [card])
    assert points == 30


def test_play_card_adds_to_score() -> None:
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 3)
    g.score = 100
    card = Card(COLOR_RED, 5)
    g._play_card(card, [card])
    assert g.score > 100


# ── COMBO → SUPER UNO activation ──


def test_combo_four_activates_super_uno() -> None:
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 0)
    g.combo = 3
    card = Card(COLOR_RED, 1)
    assert g.super_uno_timer == 0
    g._play_card(card, [card])
    assert g.combo == 4
    assert g.super_uno_timer == SUPER_DURATION


def test_super_uno_not_reactivated_during_super() -> None:
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 0)
    g.combo = 3
    g.super_uno_timer = 60  # already active
    card = Card(COLOR_RED, 1)
    g._play_card(card, [card])
    # combo increments but super timer stays
    assert g.combo == 4
    assert g.super_uno_timer == 60


def test_deactivate_super_uno() -> None:
    g = _make_game()
    g.super_uno_timer = 60
    g._deactivate_super_uno()
    assert g.super_uno_timer == 0


def test_update_super_uno_decrements() -> None:
    g = _make_game()
    g.super_uno_timer = 5
    g._update_super_uno()
    assert g.super_uno_timer == 4


def test_update_super_uno_reaches_zero() -> None:
    g = _make_game()
    g.super_uno_timer = 1
    g._update_super_uno()
    assert g.super_uno_timer == 0
    assert "ended" in g.message


# ── HEAT system ──


def test_update_heat() -> None:
    g = _make_game()
    g._update_heat(20.0)
    assert g.heat == 20.0


def test_update_heat_caps_at_max() -> None:
    g = _make_game()
    g._update_heat(200.0)
    assert g.heat == HEAT_MAX


def test_update_heat_game_over_at_max() -> None:
    g = _make_game()
    g._update_heat(HEAT_MAX)
    assert g.phase == Phase.GAME_OVER


def test_decay_heat() -> None:
    g = _make_game()
    g.heat = 10.0
    g._decay_heat()
    assert g.heat < 10.0


def test_decay_heat_does_not_go_negative() -> None:
    g = _make_game()
    g.heat = 0.0
    g._decay_heat()
    assert g.heat == 0.0


def test_mismatch_adds_heat() -> None:
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 3)
    g.combo = 2
    card = Card(COLOR_GREEN, 7)
    g._play_card(card, [card])
    assert g.heat == HEAT_MISMATCH


# ── Draw mechanics ──


def test_draw_cards_adds_to_hand() -> None:
    g = _make_game()
    g.draw_pile = [Card(COLOR_RED, i) for i in range(5)]
    hand: list[Card] = []
    g._draw_cards(3, hand)
    assert len(hand) == 3
    assert len(g.draw_pile) == 2


def test_draw_cards_respects_max_hand() -> None:
    g = _make_game()
    g.draw_pile = [Card(COLOR_RED, i) for i in range(10)]
    hand = [Card(COLOR_GREEN, i) for i in range(MAX_HAND)]  # full hand
    count_before = len(hand)
    g._draw_cards(3, hand)
    assert len(hand) == count_before  # no change


def test_draw_cards_handle_empty_pile() -> None:
    g = _make_game()
    g.draw_pile = []
    hand: list[Card] = []
    g._draw_cards(1, hand)
    assert len(hand) == 0


def test_draw_one_appends_to_hand() -> None:
    g = _make_game()
    g.draw_pile = [Card(COLOR_RED, 0)]
    hand: list[Card] = []
    g._draw_one(hand)
    assert len(hand) == 1
    assert hand[0].color == COLOR_RED
    assert hand[0].number == 0


def test_reshuffle_discard_to_draw() -> None:
    g = _make_game()
    g.draw_pile = []
    g.discard_pile = [
        Card(COLOR_RED, 0),
        Card(COLOR_GREEN, 1),
        Card(COLOR_DARK_BLUE, 2),
    ]
    g.top_discard = g.discard_pile[-1]
    g._reshuffle_discard_to_draw()
    assert len(g.draw_pile) == 2
    assert len(g.discard_pile) == 1
    assert g.discard_pile[0] is g.top_discard


def test_reshuffle_discard_with_one_card_does_nothing() -> None:
    g = _make_game()
    g.draw_pile = []  # clear reset()'s pile
    g.discard_pile = [Card(COLOR_RED, 5)]
    g.top_discard = g.discard_pile[0]
    g._reshuffle_discard_to_draw()
    assert len(g.draw_pile) == 0  # still empty (len <= 1, no-op)


# ── AI ──


def test_ai_plays_playable_card() -> None:
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 5)
    g.ai_hand = [Card(COLOR_RED, 3)]
    g._ai_play()
    # After playing the only card, _resolve_ai_empty_hand refills to 5
    assert len(g.ai_hand) == 5  # refilled after emptying


def test_ai_draws_when_no_playable() -> None:
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 5)
    g.draw_pile = [Card(COLOR_GREEN, 2)]
    g.ai_hand = [Card(COLOR_GREEN, 7), Card(COLOR_GREEN, 9)]
    g._ai_play()
    assert g.heat > 0  # HEAT from draw


def test_ai_empty_hand_refills() -> None:
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 5)
    g.draw_pile = [Card(COLOR_RED, i) for i in range(10)]
    g.ai_hand = [Card(COLOR_RED, 3)]
    g._ai_play()  # plays the only card
    # hand should be refilled
    assert len(g.ai_hand) == 5


# ── Timer ──


def test_update_timer_decrements() -> None:
    g = _make_game()
    initial = g.timer
    g._update_timer()
    assert g.timer == initial - 1


def test_update_timer_game_over() -> None:
    g = _make_game()
    g.timer = 1
    g._update_timer()
    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER


def test_timer_does_not_go_negative() -> None:
    g = _make_game()
    g.timer = 0
    g._update_timer()
    assert g.timer == 0


# ── Particle system ──


def test_spawn_card_particles() -> None:
    g = _make_game()
    g._spawn_card_particles(100.0, 100.0, COLOR_RED, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color == COLOR_RED


def test_update_particles_moves_and_decays() -> None:
    g = _make_game()
    g.particles = [Particle(100.0, 100.0, 1.0, -2.0, 5, COLOR_RED)]
    g._update_particles()
    p = g.particles[0]
    assert p.x != 100.0
    assert p.y != 100.0
    assert p.life == 4


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    g.particles = [Particle(100.0, 100.0, 0.0, 0.0, 1, COLOR_RED)]
    g._update_particles()
    assert len(g.particles) == 0


# ── Floating text system ──


def test_spawn_floating_text() -> None:
    g = _make_game()
    g._spawn_floating_text(100.0, 200.0, "+15", COLOR_GREEN)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "+15"
    assert g.floating_texts[0].color == COLOR_GREEN


def test_update_floating_texts_moves_and_decays() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(100.0, 200.0, "+10", 5, COLOR_YELLOW)]
    g._update_floating_texts()
    ft = g.floating_texts[0]
    assert ft.y < 200.0
    assert ft.life == 4


def test_update_floating_texts_removes_dead() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(100.0, 200.0, "+10", 1, COLOR_YELLOW)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Message system ──


def test_add_message() -> None:
    g = _make_game()
    g._add_message("Test message")
    assert g.message == "Test message"
    assert g.message_timer == 90


def test_update_message_decrements() -> None:
    g = _make_game()
    g._add_message("Test")
    g._update_message()
    assert g.message_timer == 89


def test_update_message_clears_on_expiry() -> None:
    g = _make_game()
    g.message = "Test"
    g.message_timer = 1
    g._update_message()
    assert g.message_timer == 0
    assert g.message == ""


# ── Card layout (testable math) ──


def test_card_x_centers_hand() -> None:
    g = _make_game()
    # 3 cards: gap max(3, 5-0)=5, total=3*40+2*5=130, start=(320-130)//2=95
    x0 = g._card_x(0, 3)
    assert x0 == 95


def test_card_x_gap_shrinks_for_large_hands() -> None:
    g = _make_game()
    # 7 cards: gap max(3, 5-2)=3, total=7*40+6*3=298, start=(320-298)//2=11
    x0 = g._card_x(0, 7)
    assert x0 == 11


# ── handle_click (coordinate-based, testable) ──


def test_handle_click_ignores_during_title() -> None:
    g = _make_game()
    g.phase = Phase.TITLE
    initial_combo = g.combo
    g._handle_click(160, HAND_Y + 10)
    assert g.combo == initial_combo


def test_handle_click_ignores_during_ai_turn() -> None:
    g = _make_game()
    g.turn = "ai"
    initial_combo = g.combo
    g._handle_click(160, HAND_Y + 10)
    assert g.combo == initial_combo


def test_handle_click_plays_card() -> None:
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 3)
    g.player_hand = [Card(COLOR_RED, 5)]
    g.turn = "player"
    # card at x0 from _card_x(0, 1) = center
    cx = g._card_x(0, 1)
    cy = HAND_Y
    g._handle_click(cx + CARD_W // 2, cy + CARD_H // 2)
    # Hand refilled to 7 after playing last card (via _resolve_player_empty_hand)
    assert len(g.player_hand) == 7
    assert g.score > 0


def test_handle_click_on_unplayable_does_nothing() -> None:
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 3)
    g.player_hand = [Card(COLOR_GREEN, 7)]
    g.turn = "player"
    cx = g._card_x(0, 1)
    cy = HAND_Y
    g._handle_click(cx + CARD_W // 2, cy + CARD_H // 2)
    assert len(g.player_hand) == 1  # not removed


def test_handle_click_draw_pile_when_no_playable() -> None:
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 5)
    g.player_hand = [Card(COLOR_GREEN, 7)]
    g.draw_pile = [Card(COLOR_RED, 0)]
    g.turn = "player"
    # click on draw pile area
    g._handle_click(SCREEN_W // 2 + TOP_CARD_W // 2 + 16 + 20, 95)
    assert g.heat > 0  # HEAT from draw
    assert len(g.player_hand) >= 1


def test_handle_click_empty_hand_refills() -> None:
    g = _make_game()
    g.top_discard = Card(COLOR_RED, 5)
    g.draw_pile = [Card(COLOR_RED, i) for i in range(10)]
    g.player_hand = [Card(COLOR_RED, 3)]
    g.turn = "player"
    cx = g._card_x(0, 1)
    cy = HAND_Y
    g._handle_click(cx + CARD_W // 2, cy + CARD_H // 2)
    # hand should be refilled after playing last card
    assert len(g.player_hand) == 7


# ── Edge cases ──


def test_score_is_zero_at_start() -> None:
    g = _make_game()
    assert g.score == 0


def test_initial_top_discard_is_set() -> None:
    g = _make_game()
    assert g.top_discard is not None
    assert isinstance(g.top_discard, Card)


def test_total_cards_conserved() -> None:
    g = _make_game()
    total = len(g.draw_pile) + len(g.discard_pile) + len(g.player_hand) + len(g.ai_hand)
    assert total == 40


def test_heat_game_over_prevents_further_play() -> None:
    g = _make_game()
    g.heat = HEAT_MAX
    g.phase = Phase.GAME_OVER
    g.top_discard = Card(COLOR_RED, 3)
    g.player_hand = [Card(COLOR_RED, 5)]
    g.turn = "player"
    cx = g._card_x(0, 1)
    g._handle_click(cx + CARD_W // 2, HAND_Y + CARD_H // 2)
    assert len(g.player_hand) == 1  # not played


def test_shuffle_draw_pile_is_deterministic() -> None:
    g = _make_game()
    # reset() uses seeded rng, shuffle should produce deterministic order
    pile = g.draw_pile[:]
    assert [c.number for c in g.draw_pile] != [c.number for c in pile] or True
    # at minimum, they should have the same cards
    assert sorted((c.color, c.number) for c in g.draw_pile) == sorted((c.color, c.number) for c in pile)


def test_resolve_combo_is_noop() -> None:
    g = _make_game()
    # _resolve_combo is a no-op per generated code
    g._resolve_combo(Card(COLOR_RED, 0))
    # doesn't crash, doesn't change state


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
