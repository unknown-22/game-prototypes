"""
Circuit Breaker — Hacking Deckbuilder Prototype
=================================================
Concept: Stack same-type code cards to build a payload.
When a stack reaches its threshold (burden), it COLLAPSES
for amplified burst damage/effect. Manage enemy trace level
before they trace your location and counterattack.

Theme: Hacking / Circuit / Log — netrunner-style digital warfare.
Score 31.2 idea (#3) from Game Idea Factory.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


# ── Configuration ─────────────────────────────────────────────────────────────
W, H = 400, 300
FPS = 30
SCALE = 2

CARD_W = 56
CARD_H = 72
CARD_X0 = 14
CARD_Y = 178
CARD_GAP = 8

BTN_X, BTN_Y = 350, 180
BTN_W, BTN_H = 38, 18

ENEMY_X, ENEMY_Y = 100, 36
ENEMY_W, ENEMY_H = 200, 60

STACK_Y = 148

# Colors
C_BG = 0
C_DARK = 1
C_MUTED = 5
C_TEXT = 7
C_DANGER = 8
C_ORANGE = 9
C_ACCENT = 11
C_BLUE = 12
C_GOLD = 14
C_WHITE = 7


# ── Phase Enum ────────────────────────────────────────────────────────────────
class Phase(Enum):
    """Game phase state machine."""

    DRAW = auto()
    PLAYER_TURN = auto()
    ENEMY_TURN = auto()
    VICTORY = auto()
    DEFEAT = auto()


# ── Card Data ─────────────────────────────────────────────────────────────────
class CardType(Enum):
    """Five code card types for the hacking deck."""

    VIRUS = "Virus"
    FIREWALL = "Firewall"
    SPIDER = "Spider"
    DAEMON = "Daemon"
    WORM = "Worm"


@dataclass(frozen=True)
class CardDef:
    """Static definition for a card type."""

    abbr: str
    threshold: int
    color: int
    desc: str
    effect_type: str
    effect_value: int


CARD_DEFS: dict[CardType, CardDef] = {
    CardType.VIRUS: CardDef("VRS", 3, 8, "6 DMG", "dmg", 6),
    CardType.FIREWALL: CardDef("FWL", 3, 12, "6 BLK", "blk", 6),
    CardType.SPIDER: CardDef("SPD", 2, 11, "+2 DRAW", "draw", 2),
    CardType.DAEMON: CardDef("DMN", 2, 9, "-2 TRC", "trace", -2),
    CardType.WORM: CardDef("WRM", 4, 14, "10 DMG", "dmg", 10),
}


@dataclass
class Card:
    """A single card instance in the deck."""

    card_type: CardType

    @property
    def defn(self) -> CardDef:
        return CARD_DEFS[self.card_type]


# ── Particle ──────────────────────────────────────────────────────────────────
@dataclass
class Particle:
    """Visual particle for collapse effects."""

    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


# ── Game ──────────────────────────────────────────────────────────────────────
class App:
    """Circuit Breaker — Main game class."""

    # Deck composition: 3 copies of each card type = 15 total
    COPIES_PER_TYPE: int = 3
    HAND_SIZE: int = 5
    TRACE_MAX: int = 8
    TRACE_GAIN: int = 2
    ENEMY_ATTACK_DMG: int = 5

    def __init__(self) -> None:
        pyxel.init(W, H, title="Circuit Breaker", fps=FPS, display_scale=SCALE)
        pyxel.mouse(True)
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── State ──

    def reset(self) -> None:
        """Reset all game state to initial values."""
        self.phase: Phase = Phase.DRAW
        self.turn: int = 0
        self.frame: int = 0

        # Player
        self.player_hp: int = 20
        self.player_max_hp: int = 20
        self.player_block: int = 0

        # Enemy
        self.enemy_hp: int = 30
        self.enemy_max_hp: int = 30
        self.trace: int = 0

        # Stacks: how many cards of each type played since last collapse
        self.stacks: dict[CardType, int] = {ct: 0 for ct in CardType}

        # Deck
        self.deck: list[Card] = []
        self.discard: list[Card] = []
        self.hand: list[Card] = []
        self.extra_draws: int = 0
        self._build_deck()

        # UI
        self.messages: list[tuple[str, int, int]] = []  # (text, color, timer)
        self.particles: list[Particle] = []

        self.hovered_card: int | None = None

    def _build_deck(self) -> None:
        """Create and shuffle the initial deck."""
        self.deck = [
            Card(ct) for ct in CardType for _ in range(self.COPIES_PER_TYPE)
        ]
        random.shuffle(self.deck)
        self.discard.clear()
        self.hand.clear()

    def _reshuffle(self) -> None:
        """Move discard pile into deck and shuffle."""
        self.deck = self.discard[:]
        self.discard.clear()
        random.shuffle(self.deck)

    def _draw_cards(self, count: int) -> None:
        """Draw `count` cards from deck into hand, reshuffling if needed."""
        drawn = 0
        while drawn < count:
            if not self.deck:
                if not self.discard:
                    break
                self._reshuffle()
            self.hand.append(self.deck.pop())
            drawn += 1

    # ── Messages ──

    def _msg(self, text: str, color: int = C_TEXT) -> None:
        """Add a timed message to the message area."""
        self.messages.append((text, color, 60))
        if len(self.messages) > 4:
            self.messages.pop(0)

    # ── Collapse ──

    def _trigger_collapse(self, ct: CardType) -> None:
        """Execute a stack collapse effect for the given card type."""
        defn = CARD_DEFS[ct]
        effect_type = defn.effect_type
        value = defn.effect_value

        if effect_type == "dmg":
            actual = min(value, self.enemy_hp)
            self.enemy_hp -= actual
            self._msg(f"{defn.abbr} COLLAPSE: -{actual} HP!", C_DANGER)
        elif effect_type == "blk":
            self.player_block += value
            self._msg(f"{defn.abbr} COLLAPSE: +{value} BLK!", C_BLUE)
        elif effect_type == "draw":
            self.extra_draws += value
            self._msg(f"{defn.abbr} COLLAPSE: +{value} DRAW!", C_ACCENT)
        elif effect_type == "trace":
            self.trace = max(0, self.trace + value)
            self._msg(f"{defn.abbr} COLLAPSE: -{-value} TRC!", C_ACCENT)

        # Particles
        cx, cy = ENEMY_X + ENEMY_W // 2, ENEMY_Y + ENEMY_H // 2
        for _ in range(6):
            self.particles.append(Particle(
                x=cx, y=cy,
                vx=random.uniform(-2.5, 2.5),
                vy=random.uniform(-4.0, -0.5),
                life=24, color=defn.color,
            ))

        if self.enemy_hp <= 0:
            self.enemy_hp = 0
            self.phase = Phase.VICTORY
            self._msg("SYSTEM BREACHED!", C_GOLD)

    def _enemy_attack(self) -> None:
        """Enemy attacks when trace is full."""
        dmg = self.ENEMY_ATTACK_DMG
        if self.player_block > 0:
            soaked = min(self.player_block, dmg)
            self.player_block -= soaked
            dmg -= soaked
        self.player_hp -= dmg
        self._msg(f"TRACE LOCKED! -{dmg} HP", C_DANGER)

        if self.player_hp <= 0:
            self.player_hp = 0
            self.phase = Phase.DEFEAT
            self._msg("SYSTEM OVERLOADED...", C_DANGER)

    # ── Player Actions ──

    def _play_card(self, index: int) -> None:
        """Play the card at the given hand index."""
        card = self.hand.pop(index)
        ct = card.card_type
        defn = CARD_DEFS[ct]

        self.stacks[ct] += 1
        self._msg(f"Play {defn.abbr} [{self.stacks[ct]}/{defn.threshold}]", defn.color)
        self.discard.append(card)

        # Check collapse
        if self.stacks[ct] >= defn.threshold:
            self.stacks[ct] = 0
            self._trigger_collapse(ct)

    def _end_turn(self) -> None:
        """End the player's turn."""
        self.discard.extend(self.hand)
        self.hand.clear()
        self.phase = Phase.ENEMY_TURN

    # ── Hit Testing ──

    @staticmethod
    def _in_rect(mx: int, my: int, rx: int, ry: int, rw: int, rh: int) -> bool:
        """Check if (mx, my) is inside the rectangle."""
        return rx <= mx <= rx + rw and ry <= my <= ry + rh

    # ── Update ──

    def update(self) -> None:
        """Main update — driven by phase state machine."""
        self.frame += 1

        # Tick message timers
        self.messages = [(t, c, tm - 1) for t, c, tm in self.messages if tm > 1]

        # Tick particles
        self.particles = [p for p in self.particles if p.life > 1]
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.15  # gravity
            p.life -= 1

        match self.phase:
            case Phase.DRAW:
                self._draw_phase()
            case Phase.PLAYER_TURN:
                self._player_turn_phase()
            case Phase.ENEMY_TURN:
                self._enemy_turn_phase()
            case Phase.VICTORY | Phase.DEFEAT:
                if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                    self.reset()

    def _draw_phase(self) -> None:
        """Draw phase: draw cards for the new turn."""
        self.turn += 1
        count = self.HAND_SIZE + self.extra_draws
        self.extra_draws = 0
        self._draw_cards(count)
        self._msg(f"--- Turn {self.turn} ---", C_MUTED)
        self.phase = Phase.PLAYER_TURN

    def _player_turn_phase(self) -> None:
        """Player turn: handle card clicks and end-turn button."""
        mx, my = pyxel.mouse_x, pyxel.mouse_y

        self.hovered_card = None
        for i in range(len(self.hand)):
            cx = CARD_X0 + i * (CARD_W + CARD_GAP)
            if self._in_rect(mx, my, cx, CARD_Y, CARD_W, CARD_H):
                self.hovered_card = i
                if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                    self._play_card(i)
                    return

        # End turn button
        if self._in_rect(mx, my, BTN_X, BTN_Y, BTN_W, BTN_H):
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self._end_turn()

    def _enemy_turn_phase(self) -> None:
        """Enemy turn: gain trace, possibly attack, then back to draw."""
        self.trace += self.TRACE_GAIN
        if self.trace >= self.TRACE_MAX:
            self.trace = 0
            self._enemy_attack()
        self.phase = Phase.DRAW

    # ── Draw ──

    def draw(self) -> None:
        """Main draw — all rendering."""
        pyxel.cls(C_BG)

        self._draw_hud()
        self._draw_enemy()
        self._draw_stacks()
        self._draw_messages()
        self._draw_particles()
        self._draw_hand()
        self._draw_ui_button()
        self._draw_overlay()

    def _draw_hud(self) -> None:
        """Draw top HUD bar with HP, Block, Turn."""
        # Player HP bar
        hp_pct = self.player_hp / self.player_max_hp
        pyxel.text(8, 6, "HP", C_TEXT)
        pyxel.rect(22, 4, 80, 8, C_DARK)
        pyxel.rect(22, 4, int(80 * hp_pct), 8, C_DANGER if hp_pct < 0.35 else C_ACCENT)
        pyxel.text(32, 5, f"{self.player_hp}/{self.player_max_hp}", C_TEXT)

        # Block
        if self.player_block > 0:
            pyxel.text(108, 6, f"BLK {self.player_block}", C_BLUE)

        # Turn
        pyxel.text(W - 60, 6, f"TURN {self.turn}", C_MUTED)

    def _draw_enemy(self) -> None:
        """Draw enemy panel with HP and trace bars."""
        # Panel
        pyxel.rect(ENEMY_X, ENEMY_Y, ENEMY_W, ENEMY_H, C_DARK)
        pyxel.rectb(ENEMY_X, ENEMY_Y, ENEMY_W, ENEMY_H, C_MUTED)

        # Name
        pyxel.text(ENEMY_X + 6, ENEMY_Y + 4, "FIREWALL v3.2.1", C_TEXT)

        # HP bar
        bar_x, bar_y = ENEMY_X + 6, ENEMY_Y + 16
        bar_w = ENEMY_W - 12
        hp_pct = self.enemy_hp / self.enemy_max_hp
        pyxel.text(bar_x, bar_y + 8, "HP", C_TEXT)
        pyxel.rect(bar_x + 14, bar_y + 8, bar_w - 14, 6, C_DARK)
        pyxel.rect(bar_x + 14, bar_y + 8, int((bar_w - 14) * hp_pct), 6, C_DANGER)
        pyxel.text(bar_x + bar_w - 40, bar_y + 8, f"{self.enemy_hp}", C_TEXT)

        # Trace bar
        trace_pct = self.trace / self.TRACE_MAX
        pyxel.text(bar_x, bar_y + 20, "TRC", C_ORANGE)
        pyxel.rect(bar_x + 14, bar_y + 20, bar_w - 14, 6, C_DARK)
        fill_w = int((bar_w - 14) * trace_pct)
        pyxel.rect(bar_x + 14, bar_y + 20, fill_w, 6, C_ORANGE)
        pyxel.text(bar_x + bar_w - 40, bar_y + 20, f"{self.trace}/{self.TRACE_MAX}", C_TEXT)

        # Warning if trace is high
        if self.trace >= self.TRACE_MAX - 2:
            pyxel.text(ENEMY_X + ENEMY_W // 2 - 16, ENEMY_Y + ENEMY_H - 10,
                       "! WARNING !", C_DANGER)

    def _draw_stacks(self) -> None:
        """Draw the per-element stack counters."""
        pyxel.text(8, STACK_Y - 10, "STACKS:", C_MUTED)
        total_w = 5 * 68 - 8  # ~332
        x_off = (W - total_w) // 2

        for i, ct in enumerate(CardType):
            defn = CARD_DEFS[ct]
            sx = x_off + i * 68
            current = self.stacks[ct]
            ready = current >= defn.threshold

            # Background
            pyxel.rect(sx, STACK_Y, 64, 18, C_DARK)
            color = defn.color if not ready else C_GOLD
            pyxel.rectb(sx, STACK_Y, 64, 18, color)

            # Text
            label = f"{defn.abbr} [{current}/{defn.threshold}]"
            if ready:
                label = f"{defn.abbr} !COLLAPSE!"
            pyxel.text(sx + 3, STACK_Y + 3, label, color)
            # Mini progress bar
            pw = int(58 * (current / defn.threshold))
            pyxel.rect(sx + 3, STACK_Y + 12, pw, 3, color)

    def _draw_messages(self) -> None:
        """Draw timed messages in the message area."""
        if not self.messages:
            return
        for i, (text, color, _timer) in enumerate(self.messages):
            pyxel.text(10, 92 + i * 10, text, color)

    def _draw_particles(self) -> None:
        """Draw all active particles."""
        for p in self.particles:
            pyxel.rect(int(p.x), int(p.y), p.size, p.size, p.color)

    def _draw_hand(self) -> None:
        """Draw the card hand at the bottom of the screen."""
        for i, card in enumerate(self.hand):
            cx = CARD_X0 + i * (CARD_W + CARD_GAP)
            self._draw_card(cx, CARD_Y, card, i == self.hovered_card)

    def _draw_card(self, x: int, y: int, card: Card, hovered: bool) -> None:
        """Draw a single card at position (x, y)."""
        defn = card.defn
        # Background
        pyxel.rect(x, y, CARD_W, CARD_H, C_DARK)
        border_col = defn.color if not hovered else C_GOLD
        pyxel.rectb(x, y, CARD_W, CARD_H, border_col)

        # Color accent bar at top
        pyxel.rect(x + 2, y + 2, CARD_W - 4, 4, defn.color)

        # Card abbreviation (centered)
        abbr_w = len(defn.abbr) * 4
        pyxel.text(x + (CARD_W - abbr_w) // 2, y + 14, defn.abbr, defn.color)

        # Card type full name
        name = card.card_type.value
        name_w = len(name) * 4
        pyxel.text(x + (CARD_W - name_w) // 2, y + 26, name, C_MUTED)

        # Threshold display
        thr_txt = f"[{defn.threshold}]"
        thr_w = len(thr_txt) * 4
        pyxel.text(x + (CARD_W - thr_w) // 2, y + 38, thr_txt, C_TEXT)

        # Collapse description
        desc_w = len(defn.desc) * 4
        pyxel.text(x + (CARD_W - desc_w) // 2, y + 52, defn.desc, defn.color)

    def _draw_ui_button(self) -> None:
        """Draw the End Turn button."""
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        hover = self._in_rect(mx, my, BTN_X, BTN_Y, BTN_W, BTN_H)
        bg = C_DARK if not hover else C_MUTED
        pyxel.rect(BTN_X, BTN_Y, BTN_W, BTN_H, bg)
        pyxel.rectb(BTN_X, BTN_Y, BTN_W, BTN_H, C_TEXT)
        pyxel.text(BTN_X + 4, BTN_Y + 4, "END", C_TEXT)
        pyxel.text(BTN_X + 2, BTN_Y + 11, "TURN", C_TEXT)

    def _draw_overlay(self) -> None:
        """Draw victory/defeat overlay."""
        if self.phase == Phase.VICTORY:
            pyxel.rect(0, 0, W, H, 0)
            pyxel.text(W // 2 - 48, H // 2 - 10, "  SYSTEM  ", C_DARK)
            pyxel.text(W // 2 - 48, H // 2, " BREACHED! ", C_GOLD)
            pyxel.text(W // 2 - 48, H // 2 + 10, "  VICTORY  ", C_GOLD)
            pyxel.text(W // 2 - 60, H // 2 + 28, "Click or [R] to restart", C_MUTED)
        elif self.phase == Phase.DEFEAT:
            pyxel.rect(0, 0, W, H, 0)
            pyxel.text(W // 2 - 52, H // 2 - 10, "  SYSTEM  ", C_DARK)
            pyxel.text(W // 2 - 52, H // 2, " OVERLOAD  ", C_DANGER)
            pyxel.text(W // 2 - 52, H // 2 + 10, "  DEFEAT   ", C_DANGER)
            pyxel.text(W // 2 - 60, H // 2 + 28, "Click or [R] to restart", C_MUTED)


if __name__ == "__main__":
    App()
