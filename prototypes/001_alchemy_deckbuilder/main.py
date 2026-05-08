"""
Alchemy Deckbuilder — Pyxel Prototype
======================================
Concept: Deck-building roguelite where you can only play cards
of ONE color per turn. Same-color cards synthesize for bonus effects.

Score 31.85 idea from Game Idea Factory.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import pyxel

# ── Config ────────────────────────────────────────────────────────────────
W, H = 400, 300
FPS = 30
CARD_W, CARD_H = 56, 76
HAND_Y = 212
HAND_CAP = 7
MAX_MANA = 6
START_HP = 30
START_MANA = 3

# Pyxel 16-color palette indices
C_BG = 0
C_DARK = 5
C_LIGHT = 6
C_WHITE = 7
C_RED = 8
C_ORANGE = 9
C_YELLOW = 10
C_GREEN = 11
C_BLUE = 12
C_PURPLE = 13
C_PINK = 14
C_PEACH = 15

# ── Element Data ──────────────────────────────────────────────────────────
ELEMENTS: dict[str, dict] = {
    "fire":   {"col": C_RED,    "label": "Fire",   "short": "FIR",
               "synth_label": "Conflagrate", "bonus": "dmg"},
    "water":  {"col": C_BLUE,   "label": "Water",  "short": "WAT",
               "synth_label": "Deluge",      "bonus": "block"},
    "earth":  {"col": C_GREEN,  "label": "Earth",  "short": "ERT",
               "synth_label": "Bounty",      "bonus": "mana"},
    "air":    {"col": C_YELLOW, "label": "Air",    "short": "AIR",
               "synth_label": "Tempest",     "bonus": "draw"},
    "aether": {"col": C_PURPLE, "label": "Aether", "short": "AET",
               "synth_label": "Prism",       "bonus": "all"},
}

ELEMENT_ORDER = ["fire", "water", "earth", "air", "aether"]
ELEMENT_NAMES = [e["label"] for e in ELEMENTS.values()]

# ── Card Definitions ──────────────────────────────────────────────────────
CARD_DEFS: list[dict] = [
    # (name, element, cost, effect_type, value, desc)
    {"name": "Fireball",    "elem": "fire",   "cost": 2, "type": "dmg",   "val": 6,  "desc": "6 dmg"},
    {"name": "Inferno",     "elem": "fire",   "cost": 4, "type": "dmg",   "val": 11, "desc": "11 dmg"},
    {"name": "Ember",       "elem": "fire",   "cost": 1, "type": "dmg",   "val": 3,  "desc": "3 dmg"},
    {"name": "Ice Shield",  "elem": "water",  "cost": 2, "type": "block", "val": 5,  "desc": "5 block"},
    {"name": "Freeze",      "elem": "water",  "cost": 3, "type": "stun",  "val": 1,  "desc": "Stun"},
    {"name": "Tear",        "elem": "water",  "cost": 1, "type": "heal",  "val": 3,  "desc": "3 HP"},
    {"name": "Mana Root",   "elem": "earth",  "cost": 1, "type": "mana",  "val": 3,  "desc": "+3 mana"},
    {"name": "Quake",       "elem": "earth",  "cost": 3, "type": "dmg",   "val": 7,  "desc": "7 dmg"},
    {"name": "Stone Armor", "elem": "earth",  "cost": 2, "type": "block", "val": 7,  "desc": "7 block"},
    {"name": "Lightning",   "elem": "air",    "cost": 3, "type": "dmg",   "val": 8,  "desc": "8 dmg"},
    {"name": "Gust",        "elem": "air",    "cost": 1, "type": "draw",  "val": 1,  "desc": "Draw 1"},
    {"name": "Tornado",     "elem": "air",    "cost": 4, "type": "dmg",   "val": 12, "desc": "12 dmg"},
    {"name": "Prism",       "elem": "aether", "cost": 3, "type": "buff",  "val": 2,  "desc": "×2 synth"},
    {"name": "Transmute",   "elem": "aether", "cost": 2, "type": "wild",  "val": 1,  "desc": "Flex"},
    {"name": "Philosopher Stone", "elem": "aether", "cost": 4, "type": "draw", "val": 2, "desc": "Draw 2"},
]


# ── Data classes ──────────────────────────────────────────────────────────
@dataclass
class Card:
    name: str
    elem: str
    cost: int
    type: str
    val: int
    desc: str
    uid: int = 0  # unique id for keying

    @property
    def color(self) -> int:
        return ELEMENTS[self.elem]["col"]

    @classmethod
    def from_def(cls, d: dict, uid: int) -> "Card":
        return cls(name=d["name"], elem=d["elem"], cost=d["cost"],
                   type=d["type"], val=d["val"], desc=d["desc"], uid=uid)

    def copy(self, new_uid: int) -> "Card":
        return Card(self.name, self.elem, self.cost, self.type,
                    self.val, self.desc, new_uid)


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    max_life: int
    color: int
    size: int = 2


class Phase(Enum):
    DRAW = "draw"
    PLAYER_TURN = "player_turn"
    ANIM_SYNTH = "anim_synth"
    RESOLVE = "resolve"
    ENEMY_TURN = "enemy_turn"
    ANIM_HIT = "anim_hit"
    VICTORY = "victory"
    DEFEAT = "defeat"


# ── Game ──────────────────────────────────────────────────────────────────
class Game:
    def __init__(self) -> None:
        pyxel.init(W, H, title="Alchemy Deckbuilder — Prototype", fps=FPS,
                   display_scale=2)
        pyxel.mouse(True)

        self.reset()
        pyxel.run(self.update, self.draw)

    # ── State ──────────────────────────────────────────────────────────
    def reset(self) -> None:
        self.phase: Phase = Phase.PLAYER_TURN
        self.turn = 1

        # Player
        self.player_hp = START_HP
        self.player_max_hp = START_HP
        self.player_block = 0
        self.mana = START_MANA
        self.max_mana = MAX_MANA

        # Enemy
        self.enemy_hp = 45
        self.enemy_max_hp = 45
        self.enemy_intent = 0  # damage this turn

        # Deck & hand
        self.deck: list[Card] = []
        self.hand: list[Card] = []
        self.discard: list[Card] = []
        self.played_this_turn: list[Card] = []
        self.card_uid_counter = 0
        self.msg_log: list[str] = []
        self._init_deck()

        # Turn state
        self.locked_color: Optional[str] = None
        self.synth_tier = 0
        self.synth_element = ""
        self.total_damage = 0
        self.total_block = 0
        self.extra_draw = 0
        self.mana_refund = 0
        self.attack_bonus = 1.0

        # Animations
        self.particles: list[Particle] = []
        self.anim_timer = 0
        self.anim_text: list[tuple[str, int, int, int]] = []  # (text, x, y, col)
        self.synth_display = ""
        self.synth_display_col = C_WHITE

        # UI state
        self.hovered_card: Optional[int] = None  # index in hand
        self._add_msg("⚗️ Draw your opening hand!")
        self._add_msg(f"─── Turn {self.turn} ───")

    def _gen_uid(self) -> int:
        self.card_uid_counter += 1
        return self.card_uid_counter

    def _init_deck(self) -> None:
        self.deck = []
        for d in CARD_DEFS:
            self.deck.append(Card.from_def(d, self._gen_uid()))
        random.shuffle(self.deck)
        # starter hand
        for _ in range(5):
            self._draw_card()

    def _draw_card(self) -> Optional[Card]:
        if len(self.hand) >= HAND_CAP:
            return None
        if not self.deck:
            self.deck = self.discard.copy()
            random.shuffle(self.deck)
            self.discard = []
            self._add_msg("🔄 Deck reshuffled!")
        if not self.deck:
            return None
        card = self.deck.pop()
        self.hand.append(card)
        return card

    def _add_msg(self, msg: str) -> None:
        self.msg_log.append(msg)
        if len(self.msg_log) > 6:
            self.msg_log.pop(0)

    # ── Particles ──────────────────────────────────────────────────────
    def _spawn_particles(self, x: float, y: float, col: int,
                         count: int = 20) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(1.0, 3.5)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 1,
                life=random.randint(15, 35),
                max_life=35,
                color=col,
                size=random.randint(2, 4),
            ))

    def _update_particles(self) -> None:
        dead = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.08  # gravity
            p.life -= 1
            if p.life <= 0:
                dead.append(p)
        for p in dead:
            self.particles.remove(p)

    # ── Game Logic ─────────────────────────────────────────────────────
    def _calc_synth_tier(self, count: int) -> tuple[int, str]:
        """Return (multiplier, label) for a given count of same-element cards."""
        if count >= 5:
            return (5, "MAGNUM OPUS ★★★★★")
        elif count == 4:
            return (3, "ELIXIR ★★★★")
        elif count == 3:
            return (2, "COMPOUND ★★★")
        elif count == 2:
            return (1, "DISTILL ★★")
        else:
            return (1, "")

    def _total_base_value(self, cards: list[Card]) -> int:
        """Sum the base values of cards (ignoring mana/draw utility cards)."""
        total = 0
        for c in cards:
            if c.type in ("dmg", "block", "heal"):
                total += c.val
        return total

    def _resolve_turn(self) -> None:
        if not self.played_this_turn:
            self._end_player_turn()
            return

        # Count elements played
        elem_counts: Counter = Counter(c.elem for c in self.played_this_turn)
        primary_elem = elem_counts.most_common(1)[0][0]
        count = elem_counts[primary_elem]
        self.synth_element = primary_elem

        # Calculate synthesis multiplier
        mult, synth_name = self._calc_synth_tier(count)
        self.synth_tier = count
        self.synth_display = synth_name
        self.synth_display_col = ELEMENTS[primary_elem]["col"]

        # Compute base values
        base_dmg = sum(c.val for c in self.played_this_turn
                       if c.type == "dmg")
        base_block = sum(c.val for c in self.played_this_turn
                         if c.type == "block")
        base_heal = sum(c.val for c in self.played_this_turn
                        if c.type == "heal")
        mana_gain = sum(c.val for c in self.played_this_turn
                        if c.type == "mana")
        extra_draw = sum(c.val for c in self.played_this_turn
                         if c.type == "draw")
        buff_tier = 0
        for c in self.played_this_turn:
            if c.type == "buff":
                buff_tier = c.val
            if c.type == "wild":
                buff_tier = max(buff_tier, 0.5)

        total_mult = mult * (1.0 + 0.5 * buff_tier)
        color = ELEMENTS[primary_elem]

        # Apply synthesis bonus based on element
        if count >= 3:
            attr = color["bonus"]
            if attr == "dmg":
                base_dmg = int(base_dmg * 1.3)
            elif attr == "block":
                base_block = int(base_block * 1.3)
            elif attr == "mana":
                mana_gain += 2
            elif attr == "draw":
                extra_draw += 1
            elif attr == "all":
                if base_dmg > 0:
                    base_dmg = int(base_dmg * 1.5)
                if base_block > 0:
                    base_block = int(base_block * 1.5)
                extra_draw += 1
                mana_gain += 2

        # Apply synthesis multiplier
        dmg = int(base_dmg * total_mult) if base_dmg > 0 else 0
        block = int(base_block * total_mult) if base_block > 0 else 0
        heal = int(base_heal * total_mult) if base_heal > 0 else 0

        # Apply effects
        self.total_damage = dmg
        self.total_block = block
        self.extra_draw = extra_draw
        self.mana_refund = mana_gain

        # Visual
        if dmg > 0:
            self._add_msg(f"⚡ {dmg} damage ({color['label']} ×{total_mult:.1f})")
            self._spawn_particles(80, 80, color["col"], 30)
        if block > 0:
            self._add_msg(f"🛡️ {block} block")
            self._spawn_particles(200, 80, C_LIGHT, 15)
        if heal > 0:
            self._add_msg(f"💚 +{heal} HP")
        if mana_gain > 0:
            self._add_msg(f"💎 +{mana_gain} mana")
        if extra_draw > 0:
            self._add_msg(f"📜 Draw {extra_draw} extra")

        # Go to animation phase
        self.phase = Phase.ANIM_SYNTH
        self.anim_timer = 60  # frames

    def _apply_resolve(self) -> None:
        """Apply all accumulated effects at once."""
        # Block
        self.player_block += self.total_block

        # Damage to enemy
        dmg = self.total_damage
        if dmg > 0:
            self.enemy_hp -= dmg
            self._spawn_particles(320, 80, C_RED, 20)

        # Heal
        if any(c.type == "heal" for c in self.played_this_turn):
            heal_amt = sum(c.val for c in self.played_this_turn
                           if c.type == "heal")
            # Recalculate with synth
            elem_counts = Counter(c.elem for c in self.played_this_turn)
            primary = elem_counts.most_common(1)[0][0]
            count = elem_counts[primary]
            mult, _ = self._calc_synth_tier(count)
            heal_amt = int(heal_amt * mult)
            self.player_hp = min(self.player_max_hp, self.player_hp + heal_amt)

        # Mana
        if self.mana_refund > 0:
            self.mana = min(self.max_mana, self.mana + self.mana_refund)

        # Draw
        for _ in range(self.extra_draw):
            self._draw_card()

        # Stun check
        stun = any(c.type == "stun" for c in self.played_this_turn)

        # Discard played cards
        self.discard.extend(self.played_this_turn)
        self.played_this_turn.clear()

        # Reset turn-lock
        self.locked_color = None

        # Check victory
        if self.enemy_hp <= 0:
            self.enemy_hp = 0
            self.phase = Phase.VICTORY
            self._add_msg("🏆 VICTORY! Enemy defeated!")
            return

        # Enemy turn
        if stun:
            self._add_msg("🌀 Enemy is stunned! They skip their turn.")
            self.phase = Phase.DRAW
            self._start_new_turn()
        else:
            self.phase = Phase.ENEMY_TURN
            self.anim_timer = 40

    def _enemy_attack(self) -> None:
        base_damage = 4 + self.turn * 2  # scales with turn
        dmg = max(base_damage - self.player_block, 0)
        self.player_block = max(self.player_block - base_damage, 0)
        if dmg > 0:
            self.player_hp -= dmg
            self._add_msg(f"💥 Enemy deals {dmg} damage!")
            self._spawn_particles(200, 200, C_RED, 15)
        else:
            self._add_msg("🛡️ Block absorbs the hit!")

        if self.player_hp <= 0:
            self.player_hp = 0
            self.phase = Phase.DEFEAT
            self._add_msg("💀 DEFEAT...")
            return

        self.phase = Phase.DRAW
        self._start_new_turn()

    def _start_new_turn(self) -> None:
        self.turn += 1
        # Increase mana capacity over time
        if self.turn > 1 and self.turn % 2 == 0:
            self.max_mana = min(10, self.max_mana + 1)
        self.mana = min(self.max_mana, self.mana + 3 + self.turn // 2)

        self.total_damage = 0
        self.total_block = 0
        self.extra_draw = 0
        self.mana_refund = 0
        self.synth_display = ""
        self.locked_color = None

        # Draw 2 cards per turn + more if stun last turn etc.
        for _ in range(3):
            self._draw_card()

        self.phase = Phase.PLAYER_TURN
        self._add_msg(f"─── Turn {self.turn} ───")

    def _end_player_turn(self) -> None:
        self.phase = Phase.DRAW
        self._start_new_turn()

    # ── Input ──────────────────────────────────────────────────────────
    def _handle_click(self) -> None:
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        if not pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            return

        if self.phase == Phase.PLAYER_TURN:
            # Check card clicks
            for i, card in enumerate(self.hand):
                cx = self._card_x(i)
                cy = HAND_Y
                if (cx <= mx <= cx + CARD_W and
                        cy <= my <= cy + CARD_H):
                    self._play_card(i)
                    return

            # Check "End Turn" button
            if (W - 90 <= mx <= W - 10 and H - 30 <= my <= H - 10):
                self.phase = Phase.RESOLVE
                self._resolve_turn()
                return

        elif self.phase in (Phase.VICTORY, Phase.DEFEAT):
            # Click to restart
            if (W // 2 - 60 <= mx <= W // 2 + 60 and
                    H // 2 + 30 <= my <= H // 2 + 50):
                self.reset()
                return

    def _play_card(self, idx: int) -> None:
        card = self.hand[idx]
        if card.cost > self.mana:
            return
        if self.locked_color is not None and card.elem != self.locked_color:
            return

        # Pay cost
        self.mana -= card.cost

        # Lock color
        if self.locked_color is None:
            self.locked_color = card.elem

        # Move to played pile
        self.hand.pop(idx)
        self.played_this_turn.append(card)

        # Immediate effects for certain card types
        if card.type == "draw":
            for _ in range(card.val):
                self._draw_card()

        self._add_msg(f"▶ {card.name} ({card.cost} mana)")
        self._spawn_particles(
            self._card_x(len(self.hand)) + CARD_W // 2, HAND_Y + CARD_H // 2,
            card.color, 10
        )

    # ── Drawing helpers ────────────────────────────────────────────────
    @staticmethod
    def _card_x(idx: int) -> int:
        total_w = HAND_CAP * (CARD_W + 4) - 4
        start_x = (W - total_w) // 2
        return start_x + idx * (CARD_W + 4)

    def _draw_card_ui(self, card: Card, x: int, y: int, idx: int) -> None:
        hovered = idx == self.hovered_card
        playable = (card.cost <= self.mana and
                    (self.locked_color is None or card.elem == self.locked_color))
        is_locked_out = (self.locked_color is not None and
                         card.elem != self.locked_color)

        # Dim if locked out
        if is_locked_out:
            col = C_DARK
        else:
            col = card.color

        # Card background
        bg = C_BG  # default
        if hovered and playable:
            bg = C_LIGHT
        elif hovered and not playable:
            bg = C_DARK

        pyxel.rect(x, y, CARD_W, CARD_H, bg)
        pyxel.rectb(x, y, CARD_W, CARD_H, col)

        # Element color stripe
        pyxel.rect(x + 2, y + 2, CARD_W - 4, 4, card.color)

        # Name
        name = card.name[:10]
        pyxel.text(x + 3, y + 10, name,
                   C_WHITE if not is_locked_out else C_DARK)

        # Cost
        pyxel.text(x + 3, y + 24, f"⚡{card.cost}",
                   C_WHITE if not is_locked_out else C_DARK)

        # Description
        pyxel.text(x + 3, y + 38, card.desc,
                   C_LIGHT if not is_locked_out else C_DARK)

        # Element label at bottom
        pyxel.text(x + 3, y + CARD_H - 12,
                   ELEMENTS[card.elem]["short"],
                   col)

        # Dim overlay if locked out
        if is_locked_out:
            pyxel.rect(x, y, CARD_W, CARD_H, 1)  # transparent dark

        # Highlight border if playable + hovered
        if hovered and playable:
            pyxel.rectb(x - 1, y - 1, CARD_W + 2, CARD_H + 2, C_WHITE)

    def _draw_button(self, x: int, y: int, w: int, h: int,
                     text: str, color: int) -> None:
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        hovered = (x <= mx <= x + w and y <= my <= y + h)
        bg = color if not hovered else C_WHITE
        fg = C_BG if hovered else C_WHITE
        pyxel.rect(x, y, w, h, bg)
        pyxel.rectb(x, y, w, h, C_WHITE)
        tw = len(text) * 4
        pyxel.text(x + (w - tw) // 2, y + 2, text, fg)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = max(0, p.life / p.max_life)
            size = max(1, int(p.size * alpha))
            col_ = p.color if p.life > p.max_life // 2 else C_DARK
            pyxel.rect(int(p.x), int(p.y), size, size, col_)

    def _draw_enemy(self) -> None:
        # Enemy portrait (just a shape)
        ex, ey = 300, 60
        pyxel.rect(ex - 20, ey, 40, 50, C_PURPLE)
        pyxel.rect(ex - 30, ey - 10, 60, 15, C_RED)
        pyxel.text(ex - 8, ey - 5, "??", C_WHITE)
        # Eyes
        pyxel.rect(ex - 10, ey + 15, 6, 6, C_WHITE)
        pyxel.rect(ex + 4, ey + 15, 6, 6, C_WHITE)
        pyxel.rect(ex - 8, ey + 17, 2, 2, C_BG)
        pyxel.rect(ex + 6, ey + 17, 2, 2, C_BG)

        # HP bar
        bar_x, bar_y = 250, 30
        bar_w = 120
        hp_pct = self.enemy_hp / self.enemy_max_hp
        pyxel.rect(bar_x, bar_y, bar_w, 6, C_DARK)
        hp_col = C_RED if hp_pct < 0.3 else C_ORANGE if hp_pct < 0.6 else C_GREEN
        pyxel.rect(bar_x, bar_y, int(bar_w * hp_pct), 6, hp_col)
        pyxel.text(bar_x, bar_y - 8, "Alchemy Golem", C_WHITE)
        pyxel.text(bar_x, bar_y + 8,
                   f"HP: {self.enemy_hp}/{self.enemy_max_hp}", C_LIGHT)

        # Intent
        if self.phase in (Phase.PLAYER_TURN, Phase.DRAW):
            dmg = 4 + self.turn * 2
            pyxel.text(bar_x, bar_y + 20,
                       f"Next: {dmg} dmg", C_RED)

    def _draw_player_stats(self) -> None:
        x, y = 10, 10
        # HP
        pyxel.text(x, y, f"HP: {self.player_hp}/{self.player_max_hp}",
                   C_WHITE)
        hp_pct = self.player_hp / self.player_max_hp
        pyxel.rect(x, y + 8, 80, 5, C_DARK)
        hp_col = C_RED if hp_pct < 0.3 else C_GREEN
        pyxel.rect(x, y + 8, int(80 * hp_pct), 5, hp_col)

        # Mana
        y2 = y + 20
        pyxel.text(x, y2, f"Mana: {self.mana}/{self.max_mana}", C_YELLOW)
        for i in range(self.max_mana):
            cx = x + i * 8
            cy = y2 + 8
            pyxel.rect(cx, cy, 6, 6, C_YELLOW if i < self.mana else C_DARK)

        # Block
        if self.player_block > 0:
            pyxel.text(x, y2 + 16, f"Block: {self.player_block}", C_BLUE)

        # Locked color
        if self.locked_color:
            col = ELEMENTS[self.locked_color]["col"]
            pyxel.text(x, y2 + 28, f"Locked: {ELEMENTS[self.locked_color]['label']}", col)

        # Synthesis info (played cards area)
        if self.played_this_turn:
            elem_counts = Counter(c.elem for c in self.played_this_turn)
            primary = elem_counts.most_common(1)[0][0]
            count = elem_counts[primary]
            pyxel.text(x, y2 + 40,
                       f"Synth: {count}x {ELEMENTS[primary]['label']}",
                       ELEMENTS[primary]["col"])

    def _draw_hand(self) -> None:
        for i, card in enumerate(self.hand):
            x = self._card_x(i)
            self._draw_card_ui(card, x, HAND_Y, i)

    def _draw_played_area(self) -> None:
        if not self.played_this_turn:
            return
        text = f"Played: {len(self.played_this_turn)} cards"
        pyxel.text(W // 2 - len(text) * 2, HAND_Y - 16, text, C_LIGHT)

        # Draw played cards mini
        for i, card in enumerate(self.played_this_turn):
            cx = W // 2 - (len(self.played_this_turn) * 30) // 2 + i * 30
            pyxel.rect(cx, HAND_Y - 36, 24, 12, card.color)
            pyxel.rectb(cx, HAND_Y - 36, 24, 12, C_WHITE)

    def _draw_synth_anim(self) -> None:
        # Drawn during ANIM_SYNTH phase
        if self.synth_display:
            cx, cy = W // 2, H // 2 - 40
            col = self.synth_display_col
            # Pulsing effect
            pulse = abs(math.sin(pyxel.frame_count * 0.1))
            size_off = int(pulse * 20)

            bg_col = pyxel.frame_count % 6 < 3 and col or C_BG
            # Big circle synth effect
            pyxel.circ(cx, cy, 40 + size_off, bg_col if bg_col != C_BG else col)
            pyxel.circb(cx, cy, 50 + size_off, C_WHITE)

            text = self.synth_display
            tw = len(text) * 4
            pyxel.text(cx - tw // 2, cy - 10, text, C_WHITE)
            pyxel.text(cx - tw // 2 + 1, cy - 9, text, col)

            # Element name
            if self.synth_element:
                el = ELEMENTS[self.synth_element]["label"]
                tw2 = len(el) * 4
                pyxel.text(cx - tw2 // 2, cy + 10, el.upper(), col)

    def _draw_phase_text(self) -> None:
        if self.phase == Phase.VICTORY:
            pyxel.text(W // 2 - 40, H // 2 - 30, "VICTORY!", C_YELLOW)
            pyxel.text(W // 2 - 36, H // 2 - 10, f"Turn {self.turn}", C_LIGHT)
            self._draw_button(W // 2 - 60, H // 2 + 30, 120, 20,
                              "Play Again", C_GREEN)
        elif self.phase == Phase.DEFEAT:
            pyxel.text(W // 2 - 36, H // 2 - 30, "DEFEAT", C_RED)
            self._draw_button(W // 2 - 60, H // 2 + 30, 120, 20,
                              "Retry", C_RED)
        elif self.phase == Phase.PLAYER_TURN:
            self._draw_button(W - 90, H - 30, 80, 20,
                              "End Turn", C_PURPLE)

    def _draw_log(self) -> None:
        for i, msg in enumerate(self.msg_log[-5:]):
            pyxel.text(4, H - 8 * (5 - i), msg, C_LIGHT)

    # ── Update ─────────────────────────────────────────────────────────
    def update(self) -> None:
        self._handle_click()
        self._update_particles()

        # Hover tracking
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        if self.phase == Phase.PLAYER_TURN:
            self.hovered_card = None
            for i in range(len(self.hand)):
                cx = self._card_x(i)
                if (cx <= mx <= cx + CARD_W and
                        HAND_Y <= my <= HAND_Y + CARD_H):
                    self.hovered_card = i
                    break
        else:
            self.hovered_card = None

        # Animation phases
        if self.phase == Phase.ANIM_SYNTH:
            self.anim_timer -= 1
            if self.anim_timer <= 0:
                self._apply_resolve()

        elif self.phase == Phase.ENEMY_TURN:
            self.anim_timer -= 1
            if self.anim_timer <= 0:
                self._enemy_attack()

    # ── Draw ───────────────────────────────────────────────────────────
    def draw(self) -> None:
        pyxel.cls(C_BG)

        self._draw_enemy()
        self._draw_player_stats()
        self._draw_hand()
        self._draw_played_area()
        self._draw_particles()
        self._draw_phase_text()
        self._draw_log()

        if self.phase == Phase.ANIM_SYNTH:
            self._draw_synth_anim()

        # Turn counter
        pyxel.text(W - 50, 4, f"T{self.turn}", C_DARK)

        # Instructions (first turn only)
        if self.turn <= 1 and self.phase == Phase.PLAYER_TURN:
            pyxel.text(4, H // 2 - 20,
                       "Click a card to play it.", C_LIGHT)
            pyxel.text(4, H // 2 - 12,
                       "You can only play ONE color per turn!", C_ORANGE)
            pyxel.text(4, H // 2 - 4,
                       "Same-color cards SYNTHESIZE for bonus!", C_YELLOW)
            pyxel.text(4, H // 2 + 4,
                       "Then click End Turn.", C_LIGHT)


if __name__ == "__main__":
    Game()
