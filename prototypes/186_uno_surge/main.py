from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import pyxel

SCREEN_W = 320
SCREEN_H = 240
CARD_W = 40
CARD_H = 22
CARD_GAP = 5
TOP_CARD_W = 60
TOP_CARD_H = 30
MAX_HAND = 7
AI_HAND_MAX = 5
AI_HAND_Y = 30
HAND_Y = 208
DISCARD_X = SCREEN_W // 2 - TOP_CARD_W // 2
DISCARD_Y = 86
DRAW_X = SCREEN_W // 2 + TOP_CARD_W // 2 + 16
DRAW_Y = 90
COMBO_X = 4
COMBO_Y = 80
MESSAGE_Y = 62
HEAT_BAR_X = 4
HEAT_BAR_Y = 2
HEAT_BAR_W = 60
HEAT_BAR_H = 6
SCORE_X = SCREEN_W // 2
SCORE_Y = 2
TIMER_X = SCREEN_W - 52
TIMER_Y = 2

COLORS = [8, 3, 5, 10]  # RED, GREEN, DARK_BLUE, YELLOW
COLOR_RED = 8
COLOR_GREEN = 3
COLOR_DARK_BLUE = 5
COLOR_YELLOW = 10
COLOR_WHITE = 7
COLOR_GRAY = 13
COLOR_BLACK = 0
COLOR_ORANGE = 9
COLOR_CYAN = 12
COLOR_NAVY = 1
COLOR_LIGHT_BLUE = 6
COLOR_PINK = 14

HEAT_MISMATCH = 15.0
HEAT_DRAW = 10.0
HEAT_MAX = 100.0
HEAT_DECAY = 0.02
COMBO_FOR_SUPER = 4
SUPER_DURATION = 180
GAME_DURATION = 1800
AI_DELAY = 30

COLOR_NAMES: dict[int, str] = {
    8: "RED",
    3: "GREEN",
    5: "BLUE",
    10: "YELLOW",
}


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Card:
    color: int
    number: int


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int
    vy: float = -1.0


class Game:
    def __init__(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.player_hand: list[Card] = []
        self.ai_hand: list[Card] = []
        self.draw_pile: list[Card] = []
        self.discard_pile: list[Card] = []
        self.top_discard: Card | None = None
        self.combo: int = 0
        self.max_combo: int = 0
        self.super_uno_timer: int = 0
        self.heat: float = 0.0
        self.score: int = 0
        self.timer: int = GAME_DURATION
        self.turn: str = "player"
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shake_frames: int = 0
        self.message: str = ""
        self.message_timer: int = 0
        self._ai_timer: int = 0
        self.rng: random.Random = random.Random()
        self.font: pyxel.Font | None = None
        self._init_font()

    def _init_font(self) -> None:
        bdf_path = Path(__file__).with_name("k8x12.bdf")
        if not bdf_path.exists():
            return
        self.font = pyxel.Font(str(bdf_path))

    def _text(self, x: int, y: int, s: str, col: int) -> None:
        if self.font:
            pyxel.text(x, y, s, col, self.font)
        else:
            pyxel.text(x, y, s, col)

    def _card_x(self, idx: int, count: int, card_w: int = CARD_W) -> int:
        gap = max(3, CARD_GAP - max(0, count - 5))
        total_w = count * card_w + (count - 1) * gap
        start_x = (SCREEN_W - total_w) // 2
        return start_x + idx * (card_w + gap)

    # ---------- pure game logic (testable, no pyxel) ----------

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.draw_pile = [
            Card(c, n)
            for c in COLORS
            for n in range(10)
        ]
        self._shuffle_draw_pile()
        self.discard_pile = [self.draw_pile.pop()]
        self.top_discard = self.discard_pile[-1]
        self.player_hand = []
        self.ai_hand = []
        self._draw_cards(7, self.player_hand)
        self._draw_cards(5, self.ai_hand)
        self.combo = 0
        self.max_combo = 0
        self.super_uno_timer = 0
        self.heat = 0.0
        self.score = 0
        self.timer = GAME_DURATION
        self.turn = "player"
        self.particles.clear()
        self.floating_texts.clear()
        self.shake_frames = 0
        self.message = ""
        self.message_timer = 0
        self._ai_timer = 0
        self.rng = random.Random()

    def _shuffle_draw_pile(self) -> None:
        for i in range(len(self.draw_pile) - 1, 0, -1):
            j = self.rng.randint(0, i)
            self.draw_pile[i], self.draw_pile[j] = self.draw_pile[j], self.draw_pile[i]

    def _draw_cards(self, n: int, hand: list[Card]) -> None:
        for _ in range(n):
            if len(hand) >= MAX_HAND:
                break
            self._draw_one(hand)
            if not self.draw_pile:
                break

    def _draw_one(self, hand: list[Card]) -> None:
        if not self.draw_pile:
            self._reshuffle_discard_to_draw()
        if not self.draw_pile:
            return
        hand.append(self.draw_pile.pop())

    def _reshuffle_discard_to_draw(self) -> None:
        if len(self.discard_pile) <= 1:
            return
        self.draw_pile = self.discard_pile[:-1]
        self.discard_pile = [self.discard_pile[-1]]
        self._shuffle_draw_pile()

    def _can_play(self, card: Card) -> bool:
        if self.top_discard is None:
            return True
        if self.super_uno_timer > 0:
            return True
        return (
            card.color == self.top_discard.color
            or card.number == self.top_discard.number
        )

    def _has_playable(self, hand: list[Card]) -> bool:
        return any(self._can_play(c) for c in hand)

    def _play_card(self, card: Card, hand: list[Card]) -> int:
        if card not in hand:
            return 0
        hand.remove(card)
        old_top = self.top_discard
        self.top_discard = card
        self.discard_pile.append(card)

        if self.super_uno_timer > 0:
            self.combo += 1
            points = 30
        else:
            is_same_color = old_top is not None and card.color == old_top.color
            if is_same_color or self.combo == 0:
                self.combo += 1
                points = (10 + self.combo * 3)
            else:
                self.combo = 1
                self.heat = min(HEAT_MAX, self.heat + HEAT_MISMATCH)
                points = 10
                self._add_message("Mismatch! +15 HEAT")

        if self.combo > self.max_combo:
            self.max_combo = self.combo

        if self.combo >= COMBO_FOR_SUPER and self.super_uno_timer == 0:
            self._activate_super_uno()

        self.score += points
        return points

    def _resolve_combo(self, card: Card) -> None:
        pass

    def _activate_super_uno(self) -> None:
        self.super_uno_timer = SUPER_DURATION
        self._add_message("SUPER UNO!")
        cx = SCREEN_W // 2
        cy = DISCARD_Y + TOP_CARD_H // 2
        for c in COLORS:
            self._spawn_card_particles(cx, cy, c, 5)

    def _deactivate_super_uno(self) -> None:
        self.super_uno_timer = 0

    def _update_heat(self, amount: float) -> None:
        self.heat = min(HEAT_MAX, self.heat + amount)
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER

    def _decay_heat(self) -> None:
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _ai_play(self) -> None:
        for card in self.ai_hand:
            if self._can_play(card):
                self._play_card(card, self.ai_hand)
                cx = self._card_x(0, len(self.ai_hand) + 1)
                cy = AI_HAND_Y + CARD_H // 2
                self._spawn_card_particles(cx, cy, card.color, 8)
                self._spawn_floating_text(
                    cx, cy - 10,
                    f"AI: {card.number}",
                    card.color,
                )
                self._resolve_ai_empty_hand()
                return

        cx = DRAW_X + CARD_W // 2
        cy = DRAW_Y + CARD_H // 2
        self._draw_one(self.ai_hand)
        self.heat = min(HEAT_MAX, self.heat + HEAT_DRAW)
        self._spawn_floating_text(cx, cy, "AI DRAW +10", COLOR_ORANGE)
        self._resolve_ai_empty_hand()

    def _resolve_ai_empty_hand(self) -> None:
        if not self.ai_hand:
            self._draw_cards(5, self.ai_hand)

    def _resolve_player_empty_hand(self) -> None:
        if not self.player_hand:
            self._draw_cards(7, self.player_hand)

    def _update_timer(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self.phase = Phase.GAME_OVER

    def _update_super_uno(self) -> None:
        if self.super_uno_timer > 0:
            self.super_uno_timer -= 1
            if self.super_uno_timer == 0:
                self._add_message("SUPER UNO ended")

    def _update_particles(self) -> None:
        survived: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.15
            p.life -= 1
            if p.life > 0:
                survived.append(p)
        self.particles = survived

    def _update_floating_texts(self) -> None:
        survived: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life > 0:
                survived.append(ft)
        self.floating_texts = survived

    def _update_message(self) -> None:
        if self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer == 0:
                self.message = ""

    def _add_message(self, msg: str) -> None:
        self.message = msg
        self.message_timer = 90

    def _spawn_card_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            vx = self.rng.uniform(-2.5, 2.5)
            vy = self.rng.uniform(-3.5, -0.5)
            life = self.rng.randint(10, 25)
            self.particles.append(Particle(x, y, vx, vy, life, color))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x, y, text, 35, color))

    def _handle_click(self, x: int, y: int) -> None:
        if self.phase != Phase.PLAYING:
            return
        if self.turn != "player":
            return

        has_playable = self._has_playable(self.player_hand)

        for i, card in enumerate(self.player_hand):
            cx = self._card_x(i, len(self.player_hand))
            cy = HAND_Y
            if cx <= x <= cx + CARD_W and cy <= y <= cy + CARD_H:
                if self._can_play(card):
                    points = self._play_card(card, self.player_hand)
                    self._spawn_card_particles(
                        cx + CARD_W // 2,
                        cy + CARD_H // 2,
                        card.color,
                        8,
                    )
                    self._spawn_floating_text(
                        cx + CARD_W // 2,
                        cy - 5,
                        f"+{points}",
                        card.color,
                    )
                    if self.combo >= 2:
                        self._spawn_floating_text(
                            SCREEN_W // 2,
                            MESSAGE_Y + 10,
                            f"COMBO x{self.combo}!",
                            COLOR_YELLOW,
                        )
                    self._resolve_player_empty_hand()
                    if self.heat >= HEAT_MAX or self.timer <= 0:
                        return
                    self.turn = "ai"
                    self._ai_timer = AI_DELAY
                    return

        if (
            DRAW_X <= x <= DRAW_X + CARD_W
            and DRAW_Y <= y <= DRAW_Y + CARD_H
            and not has_playable
        ):
            self._draw_one(self.player_hand)
            self._update_heat(HEAT_DRAW)
            self._spawn_floating_text(
                DRAW_X + CARD_W // 2,
                DRAW_Y - 5,
                "DRAW +10",
                COLOR_ORANGE,
            )
            self._resolve_player_empty_hand()
            if self.heat >= HEAT_MAX or self.timer <= 0:
                return
            self.turn = "ai"
            self._ai_timer = AI_DELAY

    # ---------- update / draw ----------

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
        elif self.phase == Phase.PLAYING:
            self._decay_heat()
            self._update_timer()
            self._update_super_uno()
            self._update_particles()
            self._update_floating_texts()
            self._update_message()
            if self.shake_frames > 0:
                self.shake_frames -= 1

            if self.heat >= HEAT_MAX or self.timer <= 0:
                if self.phase != Phase.GAME_OVER:
                    self.phase = Phase.GAME_OVER
                return

            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self._handle_click(pyxel.mouse_x, pyxel.mouse_y)

            if self.turn == "ai" and self.phase == Phase.PLAYING:
                self._ai_timer -= 1
                if self._ai_timer <= 0:
                    self._ai_play()
                    if self.heat >= HEAT_MAX or self.timer <= 0:
                        if self.phase != Phase.GAME_OVER:
                            self.phase = Phase.GAME_OVER
                        return
                    self.turn = "player"

        elif self.phase == Phase.GAME_OVER:
            self._update_particles()
            self._update_floating_texts()
            if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()

    def draw(self) -> None:
        pyxel.cls(COLOR_BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_gameover()

    def _draw_title(self) -> None:
        title = "UNO SURGE"
        tw = len(title) * 4
        self._text(SCREEN_W // 2 - tw, 50, title, COLOR_YELLOW)
        self._text(SCREEN_W // 2 - tw + 1, 49, title, COLOR_ORANGE)

        lines = [
            "Color-match card shedding game",
            "",
            "Match color or number",
            "Same-color chain = COMBO",
            "COMBO x4 = SUPER UNO!",
            "(rainbow wild, 3x points)",
            "",
            "Beware: HEAT builds up!",
            "",
            "Press SPACE to Start",
        ]
        for i, line in enumerate(lines):
            if not line:
                continue
            lnw = len(line) * 4
            y = 88 + i * 14
            if i == len(lines) - 1:
                shade = 7 if (pyxel.frame_count // 15) % 2 == 0 else COLOR_GRAY
                self._text(SCREEN_W // 2 - lnw, y, line, shade)
            else:
                self._text(SCREEN_W // 2 - lnw, y, line, COLOR_WHITE)

        info = [
            f"Colors: RED(8) GREEN(3) BLUE(5) YELLOW({COLOR_YELLOW})",
            "Mismatch play: HEAT +15",
            "No match = draw: HEAT +10",
            "HEAT full or 60s = Game Over",
        ]
        for i, line in enumerate(info):
            lnw = len(line) * 4
            self._text(SCREEN_W // 2 - lnw, 220 + i * 9, line, COLOR_GRAY)

    def _draw_playing(self) -> None:
        self._draw_ui_bar()
        self._draw_ai_hand()
        self._draw_discard()
        self._draw_draw_pile()
        self._draw_player_hand()
        self._draw_combo()
        self._draw_message_area()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_turn_indicator()

    def _draw_ui_bar(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, 11, COLOR_NAVY)
        pyxel.rect(HEAT_BAR_X, HEAT_BAR_Y, HEAT_BAR_W, HEAT_BAR_H, COLOR_GRAY)
        heat_fill = int((self.heat / HEAT_MAX) * (HEAT_BAR_W - 2))
        if heat_fill > 0:
            heat_col = COLOR_RED if self.heat > 60 else COLOR_ORANGE
            pyxel.rect(HEAT_BAR_X + 1, HEAT_BAR_Y + 1, heat_fill, HEAT_BAR_H - 2, heat_col)
        self._text(HEAT_BAR_X + HEAT_BAR_W + 4, HEAT_BAR_Y, "HEAT", COLOR_WHITE)

        score_text = f"SCORE: {self.score:05d}"
        sw = len(score_text) * 4
        self._text(SCORE_X - sw, SCORE_Y, score_text, COLOR_WHITE)

        secs = self.timer // 30
        timer_text = f"{secs}s"
        tw = len(timer_text) * 4
        self._text(TIMER_X - tw, TIMER_Y, timer_text, COLOR_WHITE if secs > 10 else COLOR_RED)

        if self.super_uno_timer > 0:
            rainbow = COLORS[(pyxel.frame_count // 4) % len(COLORS)]
            self._text(SCREEN_W // 2 - 30, 14, "SUPER UNO!", rainbow)

    def _draw_ai_hand(self) -> None:
        n = len(self.ai_hand)
        if n == 0:
            return
        for i, card in enumerate(self.ai_hand):
            x = self._card_x(i, n)
            y = AI_HAND_Y
            pyxel.rect(x, y, CARD_W, CARD_H, card.color)
            pyxel.rectb(x, y, CARD_W, CARD_H, COLOR_WHITE)
            num_str = str(card.number)
            nw = len(num_str) * 4
            pyxel.text(x + (CARD_W - nw) // 2, y + (CARD_H - 8) // 2, num_str, COLOR_WHITE)

        label = f"AI ({n})"
        self._text(4, AI_HAND_Y - 10, label, COLOR_GRAY)

    def _draw_discard(self) -> None:
        label = "DISCARD"
        lw = len(label) * 4
        self._text(DISCARD_X + (TOP_CARD_W - lw) // 2, DISCARD_Y - 10, label, COLOR_GRAY)

        if self.top_discard is None:
            pyxel.rectb(DISCARD_X, DISCARD_Y, TOP_CARD_W, TOP_CARD_H, COLOR_GRAY)
            return

        pyxel.rect(DISCARD_X, DISCARD_Y, TOP_CARD_W, TOP_CARD_H, self.top_discard.color)
        border_col = COLOR_WHITE
        if self.super_uno_timer > 0:
            border_col = COLORS[(pyxel.frame_count // 5) % len(COLORS)]
        pyxel.rectb(DISCARD_X, DISCARD_Y, TOP_CARD_W, TOP_CARD_H, border_col)

        num_str = str(self.top_discard.number)
        nw = len(num_str) * 4
        pyxel.text(
            DISCARD_X + (TOP_CARD_W - nw) // 2,
            DISCARD_Y + (TOP_CARD_H - 8) // 2,
            num_str,
            COLOR_WHITE,
        )

    def _draw_draw_pile(self) -> None:
        if not self.draw_pile:
            pyxel.rectb(DRAW_X, DRAW_Y, CARD_W, CARD_H, COLOR_DARK_BLUE)
            return

        pyxel.rect(DRAW_X, DRAW_Y, CARD_W, CARD_H, COLOR_DARK_BLUE)
        pyxel.rectb(DRAW_X, DRAW_Y, CARD_W, CARD_H, COLOR_WHITE)
        label = "DRAW"
        lw = len(label) * 4
        pyxel.text(
            DRAW_X + (CARD_W - lw) // 2,
            DRAW_Y + (CARD_H - 8) // 2,
            label,
            COLOR_WHITE,
        )

        count_str = str(len(self.draw_pile))
        cw = len(count_str) * 4
        pyxel.text(
            DRAW_X + (CARD_W - cw) // 2,
            DRAW_Y + CARD_H + 4,
            count_str,
            COLOR_GRAY,
        )

    def _draw_player_hand(self) -> None:
        n = len(self.player_hand)
        if n == 0:
            return
        for i, card in enumerate(self.player_hand):
            x = self._card_x(i, n)
            y = HAND_Y
            playable = self._can_play(card)
            is_playing = self.turn == "player" and self.phase == Phase.PLAYING

            pyxel.rect(x, y, CARD_W, CARD_H, card.color if playable or not is_playing else COLOR_DARK_BLUE)
            border_col = COLOR_WHITE if playable else COLOR_DARK_BLUE
            if playable and self.super_uno_timer > 0:
                border_col = COLORS[(pyxel.frame_count // 5) % len(COLORS)]
            pyxel.rectb(x, y, CARD_W, CARD_H, border_col)

            num_str = str(card.number)
            nw = len(num_str) * 4
            text_col = COLOR_WHITE if playable or not is_playing else COLOR_GRAY
            pyxel.text(x + (CARD_W - nw) // 2, y + (CARD_H - 8) // 2, num_str, text_col)

            if not playable and is_playing:
                pyxel.line(x, y, x + CARD_W, y + CARD_H, COLOR_RED)
                pyxel.line(x + CARD_W, y, x, y + CARD_H, COLOR_RED)

    def _draw_combo(self) -> None:
        if self.combo == 0:
            return
        combo_str = f"COMBO: {self.combo}"
        self._text(COMBO_X, COMBO_Y, combo_str, COLOR_WHITE)
        mult = min(3.0, 1.0 + (self.combo - 1) * 0.5)
        mult_str = f"x{mult:.1f}"
        self._text(COMBO_X, COMBO_Y + 10, mult_str, COLOR_YELLOW)

    def _draw_message_area(self) -> None:
        if self.message and self.message_timer > 0:
            w = len(self.message) * 4
            self._text(SCREEN_W // 2 - w, MESSAGE_Y, self.message, COLOR_YELLOW)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            col = ft.color if ft.life > 8 else COLOR_GRAY
            w = len(ft.text) * 4
            self._text(int(ft.x) - w, int(ft.y), ft.text, col)

    def _draw_turn_indicator(self) -> None:
        if self.turn == "player":
            indicator = "YOUR TURN"
            col = COLOR_WHITE
        else:
            indicator = "AI THINKING..."
            col = COLOR_GRAY
        w = len(indicator) * 4
        self._text(SCREEN_W // 2 - w, SCREEN_H - 12, indicator, col)

    def _draw_gameover(self) -> None:
        self._text(SCREEN_W // 2 - 44, 50, "GAME OVER", COLOR_RED)
        self._text(SCREEN_W // 2 - 68, 80, f"SCORE: {self.score:05d}", COLOR_WHITE)
        self._text(SCREEN_W // 2 - 68, 100, f"MAX COMBO: {self.max_combo}", COLOR_YELLOW)

        if self.heat >= HEAT_MAX:
            reason = "Failed by HEAT overload!"
            rcol = COLOR_ORANGE
        elif self.timer <= 0:
            reason = "Time's up!"
            rcol = COLOR_CYAN
        else:
            reason = ""
            rcol = COLOR_WHITE
        if reason:
            rw = len(reason) * 4
            self._text(SCREEN_W // 2 - rw, 120, reason, rcol)

        restart = "Press R to Restart"
        rw = len(restart) * 4
        shade = COLOR_WHITE if (pyxel.frame_count // 15) % 2 == 0 else COLOR_GRAY
        self._text(SCREEN_W // 2 - rw, 160, restart, shade)


def main() -> None:
    pyxel.init(SCREEN_W, SCREEN_H, title="UNO SURGE", display_scale=2)
    game = Game()
    pyxel.mouse(True)
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
