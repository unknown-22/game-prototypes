from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import ClassVar

import pyxel

# ── Constants ────────────────────────────────────────────────────────────────
WIDTH: int = 320
HEIGHT: int = 240
MAX_HEAT: float = 100.0
HEAT_BUST: float = 20.0
HEAT_LOSS: float = 10.0
HEAT_DECAY: float = 0.02
COMBO_THRESHOLD: int = 4
SUPER_DURATION: int = 300
SUPER_HAND_COUNT: int = 5
SUPER_MULTIPLIER: int = 3
BET_AMOUNT: int = 10
BJ_PAYOUT: float = 1.5
DEALER_STAND: int = 17
STARTING_CHIPS: int = 100
RESOLVE_DELAY: int = 90
MESSAGE_DURATION: int = 90

# Color palette (raw ints)
BLACK: int = 0
NAVY: int = 1
PURPLE: int = 2
GREEN: int = 3
BROWN: int = 4
DARK_BLUE: int = 5
LIGHT_BLUE: int = 6
WHITE: int = 7
RED: int = 8
ORANGE: int = 9
YELLOW: int = 10
LIME: int = 11
CYAN: int = 12
GRAY: int = 13
PINK: int = 14
PEACH: int = 15

SUIT_COLORS: list[tuple[int, str]] = [
    (RED, "RED"),
    (GREEN, "GRN"),
    (DARK_BLUE, "BLU"),
    (YELLOW, "YLW"),
]
SUIT_COLOR_VALUES: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
SUPER_RAINBOW: list[int] = [RED, YELLOW, LIME, GREEN, CYAN, DARK_BLUE]

# Card layout
CARD_W: int = 32
CARD_H: int = 48
CARD_GAP: int = 6
CARD_RADIUS: int = 2
DEALER_CARDS_Y: int = 45
PLAYER_CARDS_Y: int = 150
DECK_X: int = 280
DECK_Y: int = 10


# ── Enums & Data Classes ─────────────────────────────────────────────────────


class Phase(Enum):
    TITLE = auto()
    BETTING = auto()
    PLAYING = auto()
    STAND = auto()
    RESOLVE = auto()
    GAME_OVER = auto()


@dataclass
class Card:
    suit_color: int
    value: int
    face: int

    def is_ace(self) -> bool:
        return self.value == 1

    def is_face_card(self) -> bool:
        return self.value >= 11


@dataclass
class Hand:
    cards: list[Card] = field(default_factory=list)

    def total(self) -> int:
        total_val = 0
        aces = 0
        for c in self.cards:
            if c.value >= 10:
                total_val += 10
            else:
                total_val += c.value
            if c.value == 1:
                aces += 1
        while aces > 0 and total_val + 10 <= 21:
            total_val += 10
            aces -= 1
        return total_val

    def is_bust(self) -> bool:
        return self.total() > 21

    def is_blackjack(self) -> bool:
        return len(self.cards) == 2 and self.total() == 21

    def is_soft(self) -> bool:
        """Check if hand has an ace counted as 11."""
        total_val = 0
        aces = 0
        for c in self.cards:
            if c.value >= 10:
                total_val += 10
            else:
                total_val += c.value
            if c.value == 1:
                aces += 1
        return aces > 0 and total_val + 10 <= 21

    def dealer_stands(self) -> bool:
        t = self.total()
        if t > 21:
            return True
        if t >= DEALER_STAND:
            return True
        return False


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


# ── Game Class ───────────────────────────────────────────────────────────────


class Game:
    _patched: ClassVar[bool] = False

    # Class-level type annotations (for type checker; values set in __new__)
    phase: Phase
    player_hand: Hand
    dealer_hand: Hand
    deck: list[Card]
    discarded: list[Card]
    heat: float
    score: int
    chips: int
    current_color: int
    current_color_idx: int
    combo: int
    max_combo: int
    super_hand_timer: int
    super_hands_remaining: int
    super_active: bool
    last_win_color: int | None
    dealer_hidden: bool
    message: str
    message_timer: int
    resolve_timer: int
    particles: list[Particle]
    floating_texts: list[FloatingText]
    rainbow_idx: int
    rainbow_timer: int
    hand_outcome: str
    win_amount: int
    rng: random.Random

    def __new__(cls: type[Game]) -> Game:
        if not Game._patched:

            def _noop_init(
                w: int = 0,
                h: int = 0,
                title: str = "",
                fps: int = 60,
                display_scale: int = 1,
                capture_scale: int = 1,
                capture_sec: int = 0,
                quit_key: int = 0,
            ) -> None:
                pass

            setattr(pyxel, "init", _noop_init)  # type: ignore[arg-type]
            Game._patched = True

        obj = super().__new__(cls)
        obj.phase = Phase.TITLE
        obj.player_hand = Hand()
        obj.dealer_hand = Hand()
        obj.deck = []
        obj.discarded = []
        obj.heat = 0.0
        obj.score = 0
        obj.chips = STARTING_CHIPS
        obj.current_color = RED
        obj.current_color_idx = 0
        obj.combo = 0
        obj.max_combo = 0
        obj.super_hand_timer = 0
        obj.super_hands_remaining = 0
        obj.super_active = False
        obj.last_win_color = None
        obj.dealer_hidden = True
        obj.message = "SPACE to Start"
        obj.message_timer = 0
        obj.resolve_timer = 0
        obj.particles = []
        obj.floating_texts = []
        obj.rainbow_idx = 0
        obj.rainbow_timer = 0
        obj.hand_outcome = ""
        obj.win_amount = 0
        obj.rng = random.Random()
        return obj

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def __init__(self) -> None:
        pyxel.init(WIDTH, HEIGHT, title="BLACKJACK SURGE", display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.player_hand = Hand()
        self.dealer_hand = Hand()
        self.deck = []
        self.discarded = []
        self.heat = 0.0
        self.score = 0
        self.chips = STARTING_CHIPS
        self.current_color = RED
        self.current_color_idx = 0
        self.combo = 0
        self.max_combo = 0
        self.super_hand_timer = 0
        self.super_hands_remaining = 0
        self.super_active = False
        self.last_win_color = None
        self.dealer_hidden = True
        self.message = "SPACE to Start"
        self.message_timer = 0
        self.resolve_timer = 0
        self.particles = []
        self.floating_texts = []
        self.rainbow_idx = 0
        self.rainbow_timer = 0
        self.hand_outcome = ""
        self.win_amount = 0

    # ── Update ───────────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self._start_game()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
                self._start_game()
            return

        # Heat decay in BETTING and PLAYING phases
        if self.phase in (Phase.BETTING, Phase.PLAYING):
            self.heat = max(0.0, self.heat - HEAT_DECAY)

        # Update message timer
        if self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer == 0:
                self.message = ""

        # Update particles and floating texts
        self._update_particles()
        self._update_floating_texts()

        # Update rainbow for super mode
        if self.super_active:
            self.rainbow_timer -= 1
            if self.rainbow_timer <= 0:
                self.rainbow_timer = 4
                self.rainbow_idx = (self.rainbow_idx + 1) % len(SUPER_RAINBOW)

        if self.phase == Phase.BETTING:
            self._update_betting()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.STAND:
            self._update_stand()
        elif self.phase == Phase.RESOLVE:
            self._update_resolve()

    def _update_betting(self) -> None:
        # Check color selection keys
        for i in range(4):
            if pyxel.btnp(ord("1") + i):
                self._select_color(i)
                return
        # Mouse click on palette
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            palette_x = WIDTH - 60
            palette_y = HEIGHT - 60
            for i in range(4):
                bx = palette_x
                by = palette_y + i * 14
                if mx >= bx and mx <= bx + 54 and my >= by and my <= by + 12:
                    self._select_color(i)
                    return

    def _select_color(self, idx: int) -> None:
        self.current_color_idx = idx
        self.current_color = SUIT_COLOR_VALUES[idx]
        self._deal_hand()

    def _update_playing(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE):
            self._hit()
        elif pyxel.btnp(pyxel.KEY_RETURN):
            self._stand()

    def _update_stand(self) -> None:
        # Dealer draws until stand condition
        if self.dealer_hidden:
            self.dealer_hidden = False
            self.resolve_timer = 30
            return
        if self.resolve_timer > 0:
            self.resolve_timer -= 1
            return
        if not self.dealer_hand.dealer_stands():
            c = self._deal_card()
            if c is None:
                return
            self.dealer_hand.cards.append(c)
            self._spawn_deal_particles(DECK_X, DECK_Y, DEALER_CARDS_Y)
            return
        # Dealer done drawing
        self._resolve_hand()

    def _update_resolve(self) -> None:
        self.resolve_timer -= 1
        if self.resolve_timer <= 0:
            # Check game over
            if self.heat >= MAX_HEAT or self.chips <= 0:
                self.phase = Phase.GAME_OVER
                self.message = "GAME OVER"
                return
            # Check SUPER activation
            if not self.super_active and self.combo >= COMBO_THRESHOLD:
                self._activate_super()
                return
            # Advance to next hand
            if self.super_active and self.super_hands_remaining > 0:
                self._deal_super_hand()
            else:
                self.phase = Phase.BETTING
                self.deck = []
                self.discarded = []
                self.player_hand = Hand()
                self.dealer_hand = Hand()
                self.dealer_hidden = True
                self.message = "Press 1-4 to pick color"

    # ── Game Logic ────────────────────────────────────────────────────────

    def _start_game(self) -> None:
        self.phase = Phase.BETTING
        self.score = 0
        self.heat = 0.0
        self.combo = 0
        self.max_combo = 0
        self.super_active = False
        self.super_hands_remaining = 0
        self.particles.clear()
        self.floating_texts.clear()
        self.current_color = RED
        self.current_color_idx = 0
        self.last_win_color = None
        self.message = "Press 1-4 to pick color"
        self.message_timer = 0
        self.chips = STARTING_CHIPS

    def _make_deck(self) -> list[Card]:
        deck: list[Card] = []
        for suit_color in SUIT_COLOR_VALUES:
            for value in range(1, 14):  # 1=ace, 11=J, 12=Q, 13=K
                face = value if value <= 10 else 10
                deck.append(Card(suit_color=suit_color, value=value, face=face))
        self.rng.shuffle(deck)
        return deck

    def _deal_card(self) -> Card | None:
        if not self.deck:
            if not self.discarded:
                return None
            self.deck = list(self.discarded)
            self.discarded = []
            self.rng.shuffle(self.deck)
        return self.deck.pop()

    def _deal_hand(self) -> None:
        self.deck = self._make_deck()
        self.player_hand = Hand()
        self.dealer_hand = Hand()
        self.dealer_hidden = True
        self.discarded = []

        # Deal alternating: player, dealer, player, dealer
        c1 = self._deal_card()
        c2 = self._deal_card()
        c3 = self._deal_card()
        c4 = self._deal_card()
        assert c1 and c2 and c3 and c4
        self.player_hand.cards.append(c1)
        self.dealer_hand.cards.append(c2)
        self.player_hand.cards.append(c3)
        self.dealer_hand.cards.append(c4)
        self.phase = Phase.PLAYING
        self.message = "HIT(SPACE) or STAND(ENTER)"

        self._spawn_deal_particles(PLAYER_CARDS_Y)
        self._spawn_deal_particles(DEALER_CARDS_Y)

        # Check for natural blackjacks
        if self.player_hand.is_blackjack():
            self._stand()

    def _deal_super_hand(self) -> None:
        self.deck = self._make_deck()
        self.player_hand = Hand()
        self.dealer_hand = Hand()
        self.dealer_hidden = True
        self.discarded = []

        c1 = self._deal_card()
        c2 = self._deal_card()
        c3 = self._deal_card()
        c4 = self._deal_card()
        assert c1 and c2 and c3 and c4
        self.player_hand.cards.append(c1)
        self.dealer_hand.cards.append(c2)
        self.player_hand.cards.append(c3)
        self.dealer_hand.cards.append(c4)
        self.current_color = SUIT_COLOR_VALUES[self.rng.randint(0, 3)]
        self.phase = Phase.PLAYING
        self.super_hands_remaining -= 1
        self.message = f"SUPER {self.super_hands_remaining+1}/5 HIT(SPACE) or STAND(ENTER)"

    def _hit(self) -> None:
        c = self._deal_card()
        if c is None:
            return
        self.player_hand.cards.append(c)
        self._spawn_deal_particles(DECK_X, DECK_Y, PLAYER_CARDS_Y)

        if self.player_hand.is_bust():
            self.heat = min(MAX_HEAT, self.heat + HEAT_BUST)
            self.combo = 0
            self.last_win_color = None
            self._add_floating_text("BUST!", RED)
            self._spawn_bust_particles()
            self.message = "BUST! +20 HEAT"
            self._resolve_with_delay()
            return
        if self.player_hand.total() == 21:
            self._stand()

    def _stand(self) -> None:
        self.phase = Phase.STAND
        self.message = "Dealer's turn..."
        self.resolve_timer = 0

    def _resolve_hand(self) -> None:
        player_total = self.player_hand.total()
        dealer_total = self.dealer_hand.total()
        player_bust = self.player_hand.is_bust()
        dealer_bust = self.dealer_hand.is_bust()
        player_bj = self.player_hand.is_blackjack()
        dealer_bj = self.dealer_hand.is_blackjack()

        # Determine win/loss
        if player_bust:
            self.hand_outcome = "lose"
        elif dealer_bust:
            self.hand_outcome = "win"
        elif player_bj and not dealer_bj:
            self.hand_outcome = "bj"
        elif dealer_bj and not player_bj:
            self.hand_outcome = "lose"
        elif dealer_bj and player_bj:
            self.hand_outcome = "push"
        elif player_total > dealer_total:
            self.hand_outcome = "win"
        elif dealer_total > player_total:
            self.hand_outcome = "lose"
        else:
            self.hand_outcome = "push"

        self._update_result()

    def _update_result(self) -> None:
        """Apply outcome: update score, combo, heat, floating text, particles."""
        player_color = self.current_color

        if self.hand_outcome == "bj":
            base_score = int(BET_AMOUNT * BJ_PAYOUT)
            combo_mult = self._combo_multiplier()
            if self.super_active:
                combo_mult = SUPER_MULTIPLIER
            self.win_amount = base_score * combo_mult
            self.score += self.win_amount
            self.chips += self.win_amount
            self._add_floating_text("BLACKJACK!", YELLOW)
            self._spawn_bj_particles()
            self._update_combo_on_win(player_color)
            self.message = f"BLACKJACK! +{self.win_amount}"
        elif self.hand_outcome == "win":
            combo_mult = self._combo_multiplier()
            if self.super_active:
                combo_mult = SUPER_MULTIPLIER
            self.win_amount = BET_AMOUNT * combo_mult
            self.score += self.win_amount
            self.chips += self.win_amount
            self._add_floating_text(f"+{self.win_amount}", WHITE)
            self._update_combo_on_win(player_color)
            self.message = f"WIN! +{self.win_amount}"
        elif self.hand_outcome == "lose":
            self.heat = min(MAX_HEAT, self.heat + HEAT_LOSS)
            self.combo = 0
            self.last_win_color = None
            self.chips = max(0, self.chips - BET_AMOUNT)
            self.win_amount = -BET_AMOUNT
            self._add_floating_text("LOSE", RED)
            self.message = f"LOSE -{BET_AMOUNT} +{HEAT_LOSS:.0f} HEAT"
        else:  # push
            self.combo = 0
            self.last_win_color = None
            self.win_amount = 0
            self.message = "PUSH"

        self._resolve_with_delay()

    def _update_combo_on_win(self, player_color: int) -> None:
        if self.super_active:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            self._add_floating_text(f"COMBO x{self.combo}", YELLOW)
            return
        if self.last_win_color is not None and self.last_win_color == player_color:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            self._add_floating_text(f"COMBO x{self.combo}", YELLOW)
        else:
            self.combo = 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
        self.last_win_color = player_color

    def _combo_multiplier(self) -> int:
        return 1 + min(self.combo, 4)

    def _resolve_with_delay(self) -> None:
        self.phase = Phase.RESOLVE
        self.resolve_timer = RESOLVE_DELAY

    def _activate_super(self) -> None:
        self.super_active = True
        self.super_hands_remaining = SUPER_HAND_COUNT
        self.combo = 0
        self._add_floating_text("SUPER BLACKJACK!", LIME)
        self._spawn_super_particles()
        self.message = "SUPER MODE! 5 hands, 3x score"
        self.resolve_timer = RESOLVE_DELAY
        # Will deal first super hand after delay

    # ── Particle System ───────────────────────────────────────────────────

    def _spawn_deal_particles(self, deck_x: int = DECK_X, deck_y: int = DECK_Y,
                              target_y: int = PLAYER_CARDS_Y) -> None:
        count = self.rng.randint(4, 6)
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=float(deck_x),
                    y=float(deck_y),
                    vx=self.rng.uniform(-1.0, 1.0),
                    vy=self.rng.uniform(0.5, 1.5),
                    life=self.rng.randint(10, 20),
                    color=WHITE,
                )
            )

    def _spawn_bj_particles(self) -> None:
        count = self.rng.randint(15, 20)
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=WIDTH / 2 + self.rng.uniform(-30, 30),
                    y=HEIGHT / 2,
                    vx=self.rng.uniform(-2.0, 2.0),
                    vy=self.rng.uniform(-2.0, 0.5),
                    life=self.rng.randint(15, 25),
                    color=YELLOW,
                )
            )

    def _spawn_bust_particles(self) -> None:
        count = self.rng.randint(10, 15)
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=WIDTH / 2 + self.rng.uniform(-40, 40),
                    y=PLAYER_CARDS_Y + CARD_H / 2,
                    vx=self.rng.uniform(-1.5, 1.5),
                    vy=self.rng.uniform(-2.0, 0.5),
                    life=self.rng.randint(10, 20),
                    color=RED,
                )
            )

    def _spawn_super_particles(self) -> None:
        count = self.rng.randint(25, 35)
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=WIDTH / 2 + self.rng.uniform(-50, 50),
                    y=HEIGHT / 2 + self.rng.uniform(-30, 30),
                    vx=self.rng.uniform(-3.0, 3.0),
                    vy=self.rng.uniform(-3.0, 1.0),
                    life=self.rng.randint(20, 35),
                    color=self.rng.choice(SUPER_RAINBOW),
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.vy += 0.05
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ── Floating Text ─────────────────────────────────────────────────────

    def _add_floating_text(self, text: str, color: int) -> None:
        self.floating_texts.append(
            FloatingText(
                x=WIDTH / 2,
                y=HEIGHT / 2 - 20,
                text=text,
                life=40,
                color=color,
            )
        )

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ── Drawing ──────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(GREEN)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        else:
            self._draw_game()

    # ── Title Screen ──────────────────────────────────────────────────────

    def _draw_title(self) -> None:
        title = "BLACKJACK SURGE"
        title_w = len(title) * 4
        pyxel.text(WIDTH // 2 - title_w // 2, 30, title, WHITE)

        instructions = [
            "Color-match Blackjack with COMBO!",
            "",
            "1-4 keys : Select suit color",
            "SPACE    : HIT (draw card)",
            "ENTER    : STAND (finish)",
            "",
            "Same-color consecutive wins = COMBO",
            "COMBO x4 = SUPER BLACKJACK!",
            "  (5 hands, 3x score, all colors match)",
            "",
            "Bust = +20 HEAT, Lose = +10 HEAT",
            "HEAT >= 100 = GAME OVER",
        ]
        for i, line in enumerate(instructions):
            line_w = len(line) * 4
            pyxel.text(WIDTH // 2 - line_w // 2, 60 + i * 10, line, GRAY)

        pyxel.text(WIDTH // 2 - 56, 195, "Press SPACE to start", WHITE)

        # Draw colored suit samples
        for i, (color, label) in enumerate(SUIT_COLORS):
            rx = 50 + i * 65
            ry = 210
            pyxel.rect(rx, ry, 22, 12, color)
            pyxel.rectb(rx, ry, 22, 12, WHITE)
            label_w = len(label) * 4
            pyxel.text(rx + 11 - label_w // 2, ry + 2, label, WHITE)

    # ── Game Screen ───────────────────────────────────────────────────────

    def _draw_game(self) -> None:
        # Draw felt texture lines
        for i in range(0, WIDTH, 40):
            pyxel.line(i, 0, i + 20, HEIGHT, BROWN)

        # Dealer area label
        pyxel.text(10, DEALER_CARDS_Y - 12, "DEALER", GRAY)

        # Dealer cards
        self._draw_cards(self.dealer_hand, DEALER_CARDS_Y, hide_first=self.dealer_hidden)
        dealer_total = self.dealer_hand.total()
        if not self.dealer_hidden and self.phase != Phase.BETTING:
            total_text = f"{dealer_total}"
            pyxel.text(
                WIDTH // 2 - len(total_text) * 2,
                DEALER_CARDS_Y + CARD_H + 4,
                total_text,
                WHITE,
            )

        # Player area label
        pyxel.text(10, PLAYER_CARDS_Y - 12, "PLAYER", GRAY)

        # Player cards
        self._draw_cards(self.player_hand, PLAYER_CARDS_Y, hide_first=False)
        player_total = self.player_hand.total()
        total_text = f"{player_total}"
        if self.player_hand.is_bust():
            total_text += " BUST!"
        total_color = RED if self.player_hand.is_bust() else WHITE
        pyxel.text(
            WIDTH // 2 - len(total_text) * 2,
            PLAYER_CARDS_Y + CARD_H + 4,
            total_text,
            total_color,
        )

        # Deck draw area
        if self.deck or self.discarded:
            pyxel.rectb(DECK_X, DECK_Y, CARD_W, CARD_H, WHITE)
            pyxel.text(DECK_X + 4, DECK_Y + CARD_H // 2 - 4, "DECK", GRAY)
        else:
            pyxel.rectb(DECK_X, DECK_Y, CARD_W, CARD_H, GRAY)
            pyxel.text(DECK_X + 2, DECK_Y + CARD_H // 2 - 4, "EMPTY", GRAY)

        # Color palette (right side)
        self._draw_palette()

        # HUD
        self._draw_hud()

        # Particles
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

        # Floating texts
        for ft in self.floating_texts:
            tx = int(ft.x - len(ft.text) * 2)
            ty = int(ft.y)
            pyxel.text(tx, ty, ft.text, ft.color)

    def _draw_cards(self, hand: Hand, y: int, hide_first: bool) -> None:
        num_cards = len(hand.cards)
        if num_cards == 0:
            return
        total_w = num_cards * CARD_W + (num_cards - 1) * CARD_GAP
        start_x = WIDTH // 2 - total_w // 2

        for i, card in enumerate(hand.cards):
            cx = start_x + i * (CARD_W + CARD_GAP)
            if hide_first and i == 0:
                # Draw face-down card
                pyxel.rect(cx, y, CARD_W, CARD_H, BROWN)
                pyxel.rectb(cx, y, CARD_W, CARD_H, WHITE)
                pyxel.rect(cx + 4, y + 4, CARD_W - 8, CARD_H - 8, DARK_BLUE)
            else:
                self._draw_card(cx, y, card)

    def _draw_card(self, x: int, y: int, card: Card) -> None:
        # Card background
        pyxel.rect(x, y, CARD_W, CARD_H, WHITE)
        pyxel.rectb(x, y, CARD_W, CARD_H, BLACK)

        # Suit color indicator (top-left corner triangle)
        pyxel.tri(x, y, x + 10, y, x, y + 10, card.suit_color)

        # Card value text
        face_chars = {1: "A", 11: "J", 12: "Q", 13: "K"}
        face_str = face_chars.get(card.value, str(card.value))
        face_w = len(face_str) * 4
        pyxel.text(
            int(x + CARD_W // 2 - face_w // 2),
            int(y + CARD_H // 2 - 4),
            face_str,
            BLACK,
        )

        # Suit color bar at bottom
        pyxel.rect(x + 2, y + CARD_H - 6, CARD_W - 4, 4, card.suit_color)

    def _draw_palette(self) -> None:
        palette_x = WIDTH - 60
        palette_y = HEIGHT - 60
        pyxel.text(palette_x - 4, palette_y - 12, "COLOR", GRAY)
        for i, (color, label) in enumerate(SUIT_COLORS):
            bx = palette_x
            by = palette_y + i * 14
            pyxel.rect(bx, by, 54, 12, color)
            border_color = WHITE if i == self.current_color_idx else GRAY
            pyxel.rectb(bx, by, 54, 12, border_color)
            key_label = f"{i+1}:"
            pyxel.text(bx + 2, by + 2, key_label, WHITE if i == 0 or i == 3 else BLACK)
            pyxel.text(bx + 14, by + 2, label, WHITE if i == 0 or i == 3 else BLACK)

    # ── HUD ──────────────────────────────────────────────────────────────

    def _draw_hud(self) -> None:
        # Score (top-left)
        pyxel.text(4, 2, f"SCORE:{self.score}", WHITE)

        # Chips (top-left below score)
        pyxel.text(4, 12, f"CHIPS:{self.chips}", YELLOW)

        # Combo (top-center)
        combo_text = f"COMBO:x{self.combo}"
        pyxel.text(WIDTH // 2 - len(combo_text) * 2, 2, combo_text, YELLOW)

        # Active color
        color_label = SUIT_COLORS[self.current_color_idx][1]
        pyxel.text(WIDTH // 2 - 14, 12, f"COL:{color_label}", self.current_color)

        # SUPER timer
        if self.super_active:
            super_text = f"SUPER:x{SUPER_MULTIPLIER} [{self.super_hands_remaining}]"
            pyxel.text(WIDTH // 2 - len(super_text) * 2, 22, super_text, LIME)

        # Heat bar (top-right)
        bar_x = WIDTH - 64
        bar_y = 2
        bar_w = 60
        bar_h = 6
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        heat_fill = int(bar_w * self.heat / MAX_HEAT)
        if heat_fill > 0:
            heat_color = ORANGE if self.heat < 80 else RED
            pyxel.rect(bar_x, bar_y, heat_fill, bar_h, heat_color)
        pyxel.text(bar_x, bar_y + 8, "HEAT", GRAY)

        # Message
        if self.message:
            msg_w = len(self.message) * 4
            msg_color = WHITE
            if "BUST" in self.message or "LOSE" in self.message:
                msg_color = RED
            elif "WIN" in self.message or "BLACKJACK" in self.message:
                msg_color = YELLOW
            elif "SUPER" in self.message:
                msg_color = LIME
            pyxel.text(WIDTH // 2 - msg_w // 2, HEIGHT - 20, self.message, msg_color)

    # ── Game Over Screen ─────────────────────────────────────────────────

    def _draw_game_over(self) -> None:
        title = "GAME OVER"
        title_w = len(title) * 4
        pyxel.text(WIDTH // 2 - title_w // 2, 50, title, RED)

        cause = "HEAT OVERLOAD" if self.heat >= MAX_HEAT else "OUT OF CHIPS"
        cause_w = len(cause) * 4
        pyxel.text(WIDTH // 2 - cause_w // 2, 70, cause, ORANGE)

        score_text = f"FINAL SCORE: {self.score}"
        score_w = len(score_text) * 4
        pyxel.text(WIDTH // 2 - score_w // 2, 100, score_text, WHITE)

        combo_text = f"MAX COMBO: x{self.max_combo}"
        combo_w = len(combo_text) * 4
        pyxel.text(WIDTH // 2 - combo_w // 2, 114, combo_text, YELLOW)

        chips_text = f"CHIPS: {self.chips}"
        chips_w = len(chips_text) * 4
        pyxel.text(WIDTH // 2 - chips_w // 2, 128, chips_text, GRAY)

        restart_text = "Press SPACE to retry"
        restart_w = len(restart_text) * 4
        pyxel.text(WIDTH // 2 - restart_w // 2, 170, restart_text, WHITE)


# ── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    Game()
