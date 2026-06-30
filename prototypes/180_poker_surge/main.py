"""
POKER SURGE -- 5-card draw poker with color-match COMBO chain.

Concept: same-suit consecutive wins build COMBO. COMBO>=4 triggers SUPER MODE
(5 hands of rainbow mode: any suit auto-wins, 3x score).
"""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import pyxel

# --- Color constants ---
BLACK = 0
NAVY = 1
PURPLE = 2
GREEN = 3
BROWN = 4
DARK_BLUE = 5
LIGHT_BLUE = 6
WHITE = 7
RED = 8
ORANGE = 9
YELLOW = 10
LIME = 11
CYAN = 12
GRAY = 13
PINK = 14
PEACH = 15

SUIT_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
SUIT_SYMBOLS: list[str] = ["H", "C", "S", "D"]

# --- Game constants ---
SCREEN_W = 320
SCREEN_H = 240
FPS = 60
CARD_W = 40
CARD_H = 56
CARD_XS: list[int] = [60, 100, 140, 180, 220]
PLAYER_Y = 140
DEALER_Y = 30
START_CHIPS = 100
BET = 10
MAX_REDRAWS = 2
COMBO_THRESHOLD = 4
SUPER_HANDS = 5
SUPER_MULTIPLIER = 3
HEAT_MAX = 100
HEAT_FOLD = 10
HEAT_LOSE = 15
HEAT_DECAY = 0.02
RESULT_DURATION = 120

HAND_NAMES: list[str] = [
    "High Card", "One Pair", "Two Pair", "Trips", "Straight",
    "Flush", "FullHouse", "Quads", "StrFlush", "Royal",
]
WIN_MULTIPLIERS: list[int] = [1, 1, 2, 3, 4, 5, 6, 8, 10, 25]

RANK_NAMES: dict[int, str] = {
    14: "A", 13: "K", 12: "Q", 11: "J",
    10: "10", 9: "9", 8: "8", 7: "7",
    6: "6", 5: "5", 4: "4", 3: "3", 2: "2",
}


class Phase(Enum):
    TITLE = auto()
    BETTING = auto()
    DEAL_HOLD = auto()
    RESULT = auto()
    GAME_OVER = auto()


@dataclass
class Card:
    suit: int
    rank: int


@dataclass
class PokerHand:
    rank: int
    name: str
    value: int


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="POKER SURGE", fps=FPS, display_scale=2)
        self._rng: random.Random = random.Random()
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.chips: int = START_CHIPS
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.player_hand: list[Card] = []
        self.dealer_hand: list[Card] = []
        self.held: list[bool] = []
        self.redraws_remaining: int = 0
        self.result_timer: int = 0
        self.result_text: str = ""
        self.result_color: int = WHITE
        self.super_hands_remaining: int = 0
        self._last_win_suit: Optional[int] = None
        self.particles: list[Particle] = []
        self._shake_timer: int = 0
        self._prev_mouse_pressed: bool = False
        self._folded: bool = False
        self.high_score: int = 0
        self.high_combo: int = 0
        self._first_hand: bool = True
        self._deck: list[Card] = []
        self._player_wins: bool = False
        self._win_amount: int = 0
        pyxel.run(self.update, self.draw)

    # ---------- Reset ----------
    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.chips = START_CHIPS
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.player_hand = []
        self.dealer_hand = []
        self.held = []
        self.redraws_remaining = 0
        self.result_timer = 0
        self.result_text = ""
        self.result_color = WHITE
        self.super_hands_remaining = 0
        self._last_win_suit = None
        self.particles.clear()
        self._shake_timer = 0
        self._prev_mouse_pressed = False
        self._folded = False
        self._first_hand = True
        self._deck = []
        self._player_wins = False
        self._win_amount = 0

    # ---------- Helpers ----------
    def _just_pressed(self, key: int) -> bool:
        return bool(pyxel.btnp(key))

    def _mouse_clicked(self) -> bool:
        return bool(pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT))

    def _card_hit(self, mx: int, my: int, cx: int, cy: int) -> bool:
        return cx <= mx < cx + CARD_W and cy <= my < cy + CARD_H

    def _button_hit(self, mx: int, my: int, bx: int, by: int, bw: int, bh: int) -> bool:
        return bx <= mx < bx + bw and by <= my < by + bh

    # ---------- Deck & Card Logic ----------
    def _make_deck(self) -> list[Card]:
        deck = [Card(s, r) for s in range(4) for r in range(2, 15)]
        self._rng.shuffle(deck)
        return deck

    def _hand_suit(self, hand: list[Card]) -> int:
        cnt = Counter(c.suit for c in hand)
        max_n = max(cnt.values())
        modes = [s for s, n in cnt.items() if n == max_n]
        if len(modes) == 1:
            return modes[0]
        return max(hand, key=lambda c: c.rank).suit

    def _eval_hand(self, cards: list[Card]) -> PokerHand:
        """Evaluate a 5-card poker hand. Pure logic, no Pyxel deps."""
        if len(cards) != 5:
            raise ValueError("Need exactly 5 cards")

        ranks = sorted((c.rank for c in cards), reverse=True)
        is_flush = len({c.suit for c in cards}) == 1

        is_straight = False
        straight_high = 0
        if all(ranks[i] - ranks[i + 1] == 1 for i in range(4)):
            is_straight = True
            straight_high = ranks[0]
        elif ranks == [14, 5, 4, 3, 2]:
            is_straight = True
            straight_high = 5

        cnt = Counter(ranks)
        counts = sorted(cnt.values(), reverse=True)
        groups: dict[int, list[int]] = {}
        for r, n in cnt.items():
            groups.setdefault(n, []).append(r)
        for v in groups:
            groups[v].sort(reverse=True)

        def _b15(*vals: int) -> int:
            v = 0
            for x in vals:
                v = v * 15 + x
            return v

        # Royal flush
        if is_flush and is_straight and straight_high == 14:
            return PokerHand(9, HAND_NAMES[9], 0)

        # Straight flush
        if is_flush and is_straight:
            return PokerHand(8, HAND_NAMES[8], straight_high)

        # Four of a kind
        if counts == [4, 1]:
            return PokerHand(7, HAND_NAMES[7], groups[4][0] * 15 + groups[1][0])

        # Full house
        if counts == [3, 2]:
            return PokerHand(6, HAND_NAMES[6], groups[3][0] * 15 + groups[2][0])

        # Flush
        if is_flush:
            return PokerHand(5, HAND_NAMES[5], _b15(*ranks))

        # Straight
        if is_straight:
            return PokerHand(4, HAND_NAMES[4], straight_high)

        # Three of a kind
        if counts == [3, 1, 1]:
            k = groups[1]
            return PokerHand(3, HAND_NAMES[3], groups[3][0] * 225 + k[0] * 15 + k[1])

        # Two pair
        if counts == [2, 2, 1]:
            p = groups[2]
            return PokerHand(2, HAND_NAMES[2], p[0] * 225 + p[1] * 15 + groups[1][0])

        # One pair
        if counts == [2, 1, 1, 1]:
            p = groups[2][0]
            k = groups[1]
            return PokerHand(1, HAND_NAMES[1], p * 3375 + k[0] * 225 + k[1] * 15 + k[2])

        # High card
        return PokerHand(0, HAND_NAMES[0], _b15(*ranks))

    def _compare_hands(self, ph: PokerHand, dh: PokerHand) -> int:
        """Return 1 if player wins, -1 if dealer wins, 0 if tie."""
        if ph.rank != dh.rank:
            return 1 if ph.rank > dh.rank else -1
        if ph.value != dh.value:
            return 1 if ph.value > dh.value else -1
        return 0

    # ---------- Phase Transitions ----------
    def _start_deal(self) -> None:
        deck = self._make_deck()
        self.player_hand = [deck.pop() for _ in range(5)]
        self.dealer_hand = [deck.pop() for _ in range(5)]
        self._deck = deck
        self.held = [False] * 5
        self.redraws_remaining = MAX_REDRAWS
        self._folded = False

    def _do_fold(self) -> None:
        cx = sum(CARD_XS) // 5 + CARD_W // 2
        self._spawn_particles(cx, PLAYER_Y + CARD_H // 2, 12, GRAY)
        self.heat += HEAT_FOLD
        self.combo = 0
        self._last_win_suit = None
        self._folded = True
        self.result_text = "FOLDED"
        self.result_color = GRAY
        self.result_timer = 60
        self._player_wins = False
        self._win_amount = 0
        self.phase = Phase.RESULT

    def _do_redraw(self) -> None:
        for i in range(5):
            if not self.held[i]:
                old = self.player_hand[i]
                self.player_hand[i] = self._deck.pop()
                self._deck.append(old)
        self.held = [False] * 5
        self.redraws_remaining -= 1

    def _resolve_hand(self) -> None:
        ph = self._eval_hand(self.player_hand)
        dh = self._eval_hand(self.dealer_hand)

        in_super = self.super_hands_remaining > 0

        if in_super:
            self._player_wins = True
            mult = WIN_MULTIPLIERS[ph.rank] * SUPER_MULTIPLIER
            self._win_amount = BET * mult
            self.chips += self._win_amount
            self.score += self._win_amount
            self.result_text = f"{ph.name} x{SUPER_MULTIPLIER}!"
            self.result_color = YELLOW
            self.super_hands_remaining -= 1
            if self.super_hands_remaining == 0:
                self.combo = 0
                self._last_win_suit = None
        else:
            result = self._compare_hands(ph, dh)
            if result == 1:
                self._player_wins = True
                mult = WIN_MULTIPLIERS[ph.rank]
                self._win_amount = BET * mult
                self.chips += self._win_amount
                self.score += self._win_amount
                self.result_text = f"{ph.name} WIN!"
                self.result_color = LIME

                ws = self._hand_suit(self.player_hand)
                if self._last_win_suit == ws:
                    self.combo += 1
                else:
                    self.combo = 1
                    self._last_win_suit = ws

                if self.combo > self.max_combo:
                    self.max_combo = self.combo

                if self.combo >= COMBO_THRESHOLD and self.super_hands_remaining == 0:
                    self.super_hands_remaining = SUPER_HANDS
                    self._shake_timer = 30
            elif result == -1:
                self._player_wins = False
                self._win_amount = 0
                self.result_text = f"{dh.name} LOSE"
                self.result_color = RED
                self.heat += HEAT_LOSE
                self.combo = 0
                self._last_win_suit = None
            else:
                self._player_wins = False
                self._win_amount = 0
                self.result_text = "DRAW"
                self.result_color = WHITE

        self.result_timer = RESULT_DURATION

    def _go_next_hand(self) -> None:
        if self.chips < BET or self.heat >= HEAT_MAX:
            if self.score > self.high_score:
                self.high_score = self.score
            if self.max_combo > self.high_combo:
                self.high_combo = self.max_combo
            self.phase = Phase.GAME_OVER
            return
        self.chips -= BET
        self._start_deal()
        self.phase = Phase.DEAL_HOLD

    # ---------- Particles ----------
    def _spawn_particles(self, cx: float, cy: float, count: int, color: int) -> None:
        for _ in range(count):
            angle = self._rng.random() * 2 * math.pi
            speed = self._rng.random() * 3 + 1
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 1
            self.particles.append(Particle(cx, cy, vx, vy, 30, color))

    def _update_particles(self) -> None:
        new: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
            if p.life > 0:
                new.append(p)
        self.particles = new

    # ---------- Update ----------
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if self._just_pressed(pyxel.KEY_SPACE):
                self.phase = Phase.BETTING
            return

        if self.phase == Phase.BETTING:
            mx, my = pyxel.mouse_x, pyxel.mouse_y
            btn_x, btn_y, btn_w, btn_h = 110, 110, 100, 28
            clicked = self._mouse_clicked()
            if self._just_pressed(pyxel.KEY_SPACE) or (clicked and self._button_hit(mx, my, btn_x, btn_y, btn_w, btn_h)):
                self.chips -= BET
                self._start_deal()
                self._first_hand = False
                self.phase = Phase.DEAL_HOLD
            return

        if self.phase == Phase.DEAL_HOLD:
            self._update_particles()
            self._update_heat_decay()

            mx, my = pyxel.mouse_x, pyxel.mouse_y
            if self._mouse_clicked():
                for i in range(5):
                    if self._card_hit(mx, my, CARD_XS[i], PLAYER_Y):
                        self.held[i] = not self.held[i]

            if self._just_pressed(pyxel.KEY_F):
                self._do_fold()
                return

            if self._just_pressed(pyxel.KEY_SPACE):
                if self.redraws_remaining > 0 and not all(self.held):
                    self._do_redraw()
                    if self.redraws_remaining == 0:
                        self._resolve_hand()
                        self.phase = Phase.RESULT
                else:
                    self._resolve_hand()
                    self.phase = Phase.RESULT
            return

        if self.phase == Phase.RESULT:
            self._update_particles()
            if self._shake_timer > 0:
                self._shake_timer -= 1

            self.result_timer -= 1
            if self.result_timer <= 0 or self._just_pressed(pyxel.KEY_SPACE):
                self._go_next_hand()
            return

        if self.phase == Phase.GAME_OVER:
            self._update_particles()
            if self._just_pressed(pyxel.KEY_R):
                self.reset()
            return

    def _update_heat_decay(self) -> None:
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    # ---------- Draw ----------
    def draw(self) -> None:
        pyxel.cls(NAVY)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.BETTING:
            self._draw_betting()
        elif self.phase in (Phase.DEAL_HOLD, Phase.RESULT):
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

        self._draw_particles()

    def _draw_title(self) -> None:
        pyxel.text(110, 50, "POKER SURGE", YELLOW)
        pyxel.text(82, 68, "5-Card Draw COMBO", WHITE)
        pyxel.text(80, 90, "Same-suit consecutive wins", LIGHT_BLUE)
        pyxel.text(70, 102, "build COMBO chain!", LIGHT_BLUE)
        pyxel.text(65, 122, "COMBO>=4: SUPER MODE (3x!)", YELLOW)
        pyxel.text(100, 160, "F to Fold a hand", WHITE)
        pyxel.text(70, 175, "Click cards to HOLD them", WHITE)
        pyxel.text(75, 190, "SPACE to Redraw / Advance", WHITE)
        pyxel.text(105, 215, "Press SPACE to Start", GREEN)

    def _draw_betting(self) -> None:
        pyxel.text(105, 40, "POKER SURGE", YELLOW)
        pyxel.text(120, 70, f"Chips: {self.chips}", WHITE)
        pyxel.text(125, 85, f"Bet: {BET}", WHITE)

        bx, by, bw, bh = 110, 110, 100, 28
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        hover = self._button_hit(mx, my, bx, by, bw, bh)
        btn_color = LIME if hover else GREEN
        pyxel.rect(bx, by, bw, bh, btn_color)
        pyxel.rectb(bx, by, bw, bh, WHITE)
        pyxel.text(bx + 10, by + 10, "CONFIRM BET", DARK_BLUE)

        pyxel.text(105, 155, "SPACE or Click", WHITE)
        pyxel.text(108, 170, "to confirm bet", WHITE)

    def _draw_game(self) -> None:
        if self._shake_timer > 0:
            sx = self._rng.randint(-2, 2)
            sy = self._rng.randint(-2, 2)
        else:
            sx = 0
            sy = 0
        try:
            pyxel.camera(sx, sy)
        except BaseException:
            pass

        self._draw_hud()

        # Dealer cards
        dealer_face_up = self.phase == Phase.RESULT
        for i, card in enumerate(self.dealer_hand):
            self._draw_card(CARD_XS[i], DEALER_Y, card, face_up=dealer_face_up)

        # Player cards
        for i, card in enumerate(self.player_hand):
            self._draw_card(CARD_XS[i], PLAYER_Y, card, face_up=True, held=self.held[i])

        # Phase-specific UI
        if self.phase == Phase.DEAL_HOLD:
            remain = self.redraws_remaining
            pyxel.text(10, 108, f"Redraws: {remain}", WHITE)
            held_count = sum(self.held)
            pyxel.text(10, 120, f"Held: {held_count}", WHITE)
            pyxel.text(200, 108, "F: Fold", GRAY)
            if remain > 0:
                pyxel.text(190, 120, "SPACE: Redraw", LIME)
            else:
                pyxel.text(188, 120, "SPACE: Result", LIME)

        if self.phase == Phase.RESULT:
            pyxel.text(10, 108, self.result_text, self.result_color)
            pyxel.text(155, 108, "[SPACE]", LIGHT_BLUE)
            if self._player_wins:
                dealer_label = "DEALER"
            else:
                dealer_label = "DEALER"

            pyxel.text(120, DEALER_Y - 12, dealer_label, LIGHT_BLUE)
            pyxel.text(120, PLAYER_Y + CARD_H + 4, "YOU", LIGHT_BLUE)

            if self._win_amount > 0:
                pyxel.text(10, 120, f"+{self._win_amount} chips", LIME)

        try:
            pyxel.camera(0, 0)
        except BaseException:
            pass

    def _draw_card(self, x: int, y: int, card: Card, *, face_up: bool = True, held: bool = False) -> None:
        if face_up:
            color = SUIT_COLORS[card.suit]
            pyxel.rect(x, y, CARD_W, CARD_H, DARK_BLUE)
            pyxel.rect(x + 1, y + 1, CARD_W - 2, CARD_H - 2, color)
            rank_str = RANK_NAMES[card.rank]
            pyxel.text(x + 3, y + 3, rank_str, BLACK if color == YELLOW else WHITE)
            pyxel.text(x + 16, y + 24, SUIT_SYMBOLS[card.suit], BLACK if color == YELLOW else WHITE)
        else:
            pyxel.rect(x, y, CARD_W, CARD_H, DARK_BLUE)
            pyxel.rectb(x, y, CARD_W, CARD_H, LIGHT_BLUE)
            pyxel.text(x + 14, y + 24, "?", WHITE)

        if held:
            pyxel.rectb(x - 1, y - 1, CARD_W + 2, CARD_H + 2, YELLOW)
            pyxel.rectb(x - 2, y - 2, CARD_W + 4, CARD_H + 4, LIME)

    def _draw_hud(self) -> None:
        pyxel.text(4, 2, f"Score: {self.score}", WHITE)
        pyxel.text(120, 2, f"Combo: x{self.combo}", YELLOW)
        pyxel.text(240, 2, f"Chips: {self.chips}", WHITE)

        bar_x, bar_y, bar_w, bar_h = 4, 14, 100, 6
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, DARK_BLUE)
        heat_w = int(bar_w * min(self.heat / HEAT_MAX, 1.0))
        heat_color = RED if self.heat >= 70 else ORANGE if self.heat >= 40 else YELLOW
        pyxel.rect(bar_x, bar_y, heat_w, bar_h, heat_color)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        pyxel.text(bar_x - 2, bar_y + 8, "HEAT", WHITE)

        if self.super_hands_remaining > 0:
            pyxel.text(120, 12, f"SUPER x{self.super_hands_remaining}", YELLOW)
            # Rainbow border
            rainbow = [RED, ORANGE, YELLOW, GREEN, CYAN, LIGHT_BLUE, PURPLE, PINK]
            t = pyxel.frame_count
            for i, clr in enumerate(rainbow):
                seg = t // 4 + i
                x0 = (-seg) % SCREEN_W
                y0 = 0
                pyxel.rect(x0, y0, 4, SCREEN_H, clr)

    def _draw_game_over(self) -> None:
        pyxel.text(115, 40, "GAME OVER", RED)
        pyxel.text(100, 70, f"Score: {self.score}", WHITE)
        pyxel.text(100, 85, f"Max Combo: x{self.max_combo}", YELLOW)
        pyxel.text(100, 100, f"High Score: {self.high_score}", WHITE)
        pyxel.text(100, 115, f"Max Combo: x{self.high_combo}", YELLOW)

        if self.heat >= HEAT_MAX:
            pyxel.text(80, 140, "OVERHEATED!", RED)
        else:
            pyxel.text(85, 140, "OUT OF CHIPS!", RED)

        pyxel.text(105, 175, "Press R to Restart", LIME)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = min(p.life / 30, 1.0)
            if alpha > 0.2:
                pyxel.rect(int(p.x), int(p.y), 2, 2, p.color)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
