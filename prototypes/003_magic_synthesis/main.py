"""
Magic Academy: Spell Synthesis - Pyxel Prototype
==================================================
Concept: A turn-based magic card battle where playing same-type
spells synthesizes them into amplified effects.
Score 31.6 idea from Game Idea Factory.
Theme: Magic Academy (rule modification) / Vampire Survivor variant.
Core: Effects 'synthesize' into 1 card when same element is played.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import pyxel


# ── Config ──────────────────────────────────────────────────────────────────
W, H = 400, 300
FPS = 30
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

HAND_SIZE = 5
DECK_SIZE = 15
INITIAL_HEAT = 5
MAX_HEAT = 10
INITIAL_HP = 25
ENEMY_BASE_HP = 30


# ── Element Definitions ─────────────────────────────────────────────────────
class Element(Enum):
    FIRE = ("Fire", C_RED, 3, 5, "High damage")
    WATER = ("Water", C_BLUE, 2, 3, "Draw +1 card")
    EARTH = ("Earth", C_GREEN, 2, 2, "Gain 2 Block")
    WIND = ("Wind", C_PEACH, 1, 2, "Reduce Risk by 2")
    ARCANE = ("Arcane", C_PURPLE, 4, 6, "Scales with synthesis")

    def __init__(self, label: str, color: int, cost: int, base_dmg: int, desc: str) -> None:
        self.label: str = label
        self.color: int = color
        self.cost: int = cost
        self.base_dmg: int = base_dmg
        self.desc: str = desc


# ── Data Classes ────────────────────────────────────────────────────────────
@dataclass
class Card:
    element: Element
    synthesize_count: int = 1  # 1 = normal, 2+ = synthesized

    @property
    def display_name(self) -> str:
        if self.synthesize_count >= 2:
            return f"{self.element.label}x{self.synthesize_count}"
        return self.element.label

    @property
    def cost(self) -> int:
        return self.element.cost

    @property
    def color(self) -> int:
        return self.element.color

    @property
    def damage(self) -> int:
        """Calculate damage with synthesis multiplier."""
        base = self.element.base_dmg
        if self.synthesize_count >= 4:
            return int(base * 5)
        if self.synthesize_count >= 3:
            return int(base * 3)
        if self.synthesize_count >= 2:
            return int(base * 1.5)
        return base

    @property
    def block_gain(self) -> int:
        """Block gained from Earth cards."""
        if self.element != Element.EARTH:
            return 0
        if self.synthesize_count >= 4:
            return 10
        if self.synthesize_count >= 3:
            return 6
        if self.synthesize_count >= 2:
            return 4
        return 2

    @property
    def wind_effect(self) -> int:
        """Risk reduction from Wind cards."""
        if self.element != Element.WIND:
            return 0
        if self.synthesize_count >= 4:
            return 8
        if self.synthesize_count >= 3:
            return 5
        if self.synthesize_count >= 2:
            return 3
        return 2

    @property
    def draw_bonus(self) -> int:
        """Extra cards drawn from Water cards."""
        if self.element != Element.WATER:
            return 0
        if self.synthesize_count >= 4:
            return 3
        if self.synthesize_count >= 3:
            return 2
        if self.synthesize_count >= 2:
            return 1
        return 0


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
    text: str = ""


# ── Game Phases ─────────────────────────────────────────────────────────────
class Phase(Enum):
    PLAYER = auto()
    RESOLVE = auto()
    ENEMY = auto()
    VICTORY = auto()
    DEFEAT = auto()


# ── Game Class ──────────────────────────────────────────────────────────────
class Game:
    def __init__(self) -> None:
        pyxel.init(W, H, title="Magic Academy - Spell Synthesis", fps=FPS, display_scale=2)
        pyxel.mouse(True)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        # Player stats
        self.player_hp = INITIAL_HP
        self.player_max_hp = INITIAL_HP
        self.heat = INITIAL_HEAT
        self.max_heat = MAX_HEAT
        self.block = 0
        self.risk = 0
        self.max_risk = 10

        # Enemy
        self.enemy_hp = ENEMY_BASE_HP
        self.enemy_max_hp = ENEMY_BASE_HP
        self.enemy_name = "Grimoire Golem"
        self.turn = 1

        # Deck & Hand
        self.deck: list[Card] = self.make_deck()
        random.shuffle(self.deck)
        self.hand: list[Card] = []
        self.discard: list[Card] = []
        self.draw_pile: list[Card] = []

        # Play state
        self.played_this_turn: list[Card] = []
        self.phase = Phase.PLAYER
        self.selected_card_idx = -1

        # UI
        self.message = ""
        self.message_timer = 0
        self.synth_flash = 0
        self.hit_flash = 0
        self.particles: list[Particle] = []

        self.draw_to_hand()

    def make_deck(self) -> list[Card]:
        """15-card deck: 3 of each element."""
        deck: list[Card] = []
        for e in Element:
            for _ in range(3):
                deck.append(Card(element=e))
        return deck

    def draw_to_hand(self) -> None:
        while len(self.hand) < HAND_SIZE:
            if not self.deck:
                if not self.discard:
                    break
                self.deck = self.discard
                random.shuffle(self.deck)
                self.discard = []
                self.show_message("Deck reshuffled!")
            self.hand.append(self.deck.pop())

    def show_message(self, text: str) -> None:
        self.message = text
        self.message_timer = 90

    def add_particles(
        self, x: float, y: float, color: int, count: int = 8, text: str = ""
    ) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x + random.uniform(-4, 4),
                    y + random.uniform(-4, 4),
                    random.uniform(-1.5, 1.5),
                    random.uniform(-2.5, -0.5),
                    random.randint(15, 35),
                    35,
                    color,
                    random.randint(1, 3),
                    text,
                )
            )

    def add_explosion(self, x: float, y: float, color: int, count: int = 15) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.5, 4.5)
            self.particles.append(
                Particle(
                    x,
                    y,
                    math.cos(angle) * speed,
                    math.sin(angle) * speed,
                    random.randint(10, 25),
                    25,
                    color,
                    random.randint(2, 5),
                )
            )

    # ── Card Interaction ────────────────────────────────────────────────────

    def play_card(self, idx: int) -> None:
        if idx < 0 or idx >= len(self.hand):
            return
        card = self.hand[idx]
        if card.cost > self.heat:
            self.show_message(f"Need {card.cost} HEAT! (have {self.heat})")
            return

        self.heat -= card.cost
        played = self.hand.pop(idx)

        # Check if we already played this element this turn → synthesize
        merge_target: Optional[int] = None
        for i, pc in enumerate(self.played_this_turn):
            if pc.element == played.element:
                merge_target = i
                break

        if merge_target is not None:
            existing = self.played_this_turn[merge_target]
            existing.synthesize_count += 1
            self.synth_flash = 20
            dmg = existing.damage
            self.show_message(
                f"Synthesis! {existing.display_name} → {dmg}dmg"
            )
            self.add_explosion(W // 2, 120, C_YELLOW, 20)
        else:
            self.played_this_turn.append(played)
            self.show_message(f"{played.display_name} cast!")

        # Risk: playing cards generates risk
        self.risk = min(self.max_risk, self.risk + 1)

        # Element-specific effects on play
        if played.element == Element.WIND:
            self.risk = max(0, self.risk - played.wind_effect)
        elif played.element == Element.EARTH:
            self.block += played.block_gain
        elif played.element == Element.WATER:
            bonus = played.draw_bonus
            # Draw extra cards
            if bonus > 0 and self.deck:
                drawn = self.deck[:bonus]
                self.deck = self.deck[bonus:]
                self.hand.extend(drawn)
                self.show_message(f"Drew {len(drawn)} extra card(s)!")

        # Visual feedback
        cx = 50 + idx * 65
        self.add_particles(cx, 230, card.color, 5)

    def resolve_player_turn(self) -> None:
        """Apply all card effects to the enemy."""
        total_damage = 0
        total_block = 0
        for card in self.played_this_turn:
            dmg = card.damage
            total_damage += dmg
            total_block += card.block_gain
            if dmg > 0:
                self.add_explosion(W // 2 + random.randint(-30, 30), 50, card.color, 10)

        # Apply block
        if total_block > 0:
            self.block += total_block

        # Apply damage
        if total_damage > 0:
            self.enemy_hp -= total_damage
            self.hit_flash = 15
            self.show_message(f"Total damage: {total_damage}!")
            self.add_explosion(W // 2, 50, C_RED, 25)
        else:
            self.show_message("No spells to resolve!")

        # Discard played cards
        self.discard.extend(self.played_this_turn)
        self.played_this_turn = []

    def enemy_turn(self) -> None:
        """Enemy attacks based on turn count and risk."""
        if self.enemy_hp <= 0:
            return

        base_attack = 2 + self.turn // 2
        risk_bonus = self.risk  # risk directly adds to enemy damage
        total_attack = base_attack + risk_bonus

        # Block absorbs damage
        if self.block > 0:
            absorbed = min(self.block, total_attack)
            self.block -= absorbed
            total_attack -= absorbed
            if absorbed > 0:
                self.show_message(f"Block absorbed {absorbed} damage!")

        if total_attack > 0:
            self.player_hp -= total_attack
            self.show_message(f"Enemy attacks for {total_attack} dmg! (risk +{risk_bonus})")
            self.add_explosion(50, 170, C_RED, 20)
        else:
            self.show_message("Enemy attack blocked!")

        # Reduce risk slightly each turn (enemy dissipates some)
        self.risk = max(0, self.risk - 1)

    def end_player_turn(self) -> None:
        self.resolve_player_turn()
        self.enemy_turn()
        self.turn += 1
        # Regenerate heat
        self.heat = min(self.max_heat, self.heat + 3)
        self.draw_to_hand()

    def check_game_over(self) -> Optional[str]:
        if self.enemy_hp <= 0:
            return "win"
        if self.player_hp <= 0:
            return "lose"
        if self.risk >= self.max_risk:
            self.show_message("Risk overflow! You lose control!")
            return "lose"
        return None

    # ── Update ──────────────────────────────────────────────────────────────

    def update(self) -> None:
        if self.message_timer > 0:
            self.message_timer -= 1
        if self.synth_flash > 0:
            self.synth_flash -= 1
        if self.hit_flash > 0:
            self.hit_flash -= 1

        # Update particles
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05  # gravity
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

        # Check game over
        result = self.check_game_over()
        if result == "win":
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
            return
        if result == "lose":
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
            return

        # Player turn input
        if self.phase == Phase.PLAYER:
            mx, my = pyxel.mouse_x, pyxel.mouse_y

            # Card hover/click
            for i in range(len(self.hand)):
                cx, cy, cw, ch = self.card_rect(i)
                if cx <= mx <= cx + cw and cy <= my <= cy + ch:
                    self.selected_card_idx = i
                    if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                        self.play_card(i)
                    break
            else:
                self.selected_card_idx = -1

            # End turn button
            ex, ey, ew, eh = 320, 270, 70, 22
            if ex <= mx <= ex + ew and ey <= my <= ey + eh:
                if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and self.hand:
                    self.end_player_turn()

        # R key to restart at any time
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()

    def card_rect(self, idx: int) -> tuple[int, int, int, int]:
        cw, ch = 58, 45
        start_x = 12
        gap = 5
        x = start_x + idx * (cw + gap)
        y = 246
        return x, y, cw, ch

    # ── Draw ────────────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(C_BG)

        self.draw_title()
        self.draw_enemy_area()
        self.draw_player_info()
        self.draw_hand()
        self.draw_end_turn_button()
        self.draw_synth_area()
        self.draw_particles()
        self.draw_message()
        self.draw_game_over()

    def draw_title(self) -> None:
        pyxel.text(10, 6, "Magic Academy - Spell Synthesis", C_PURPLE)
        pyxel.text(10, 16, f"Turn {self.turn}", C_LIGHT)

    def draw_enemy_area(self) -> None:
        # Enemy name
        pyxel.text(10, 40, f"{self.enemy_name}", C_RED)

        # Enemy HP bar
        bar_x, bar_y = 90, 40
        bar_w, bar_h = 200, 14
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, C_DARK)
        hp_pct = max(0, self.enemy_hp / self.enemy_max_hp)
        if hp_pct > 0.5:
            hp_color = C_GREEN
        elif hp_pct > 0.25:
            hp_color = C_ORANGE
        else:
            hp_color = C_RED
        pyxel.rect(bar_x, bar_y, int(bar_w * hp_pct), bar_h, hp_color)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, C_LIGHT)
        pyxel.text(
            bar_x + 5, bar_y + 3,
            f"{max(0, self.enemy_hp)}/{self.enemy_max_hp}",
            C_WHITE,
        )

        # Enemy damage preview
        preview_atk = 2 + self.turn // 2 + self.risk
        pyxel.text(bar_x + bar_w + 8, bar_y + 1, "ATK:", C_LIGHT)
        pyxel.text(bar_x + bar_w + 8, bar_y + 10, f"{preview_atk}", C_RED)

        # Grimoire visual (spinning book)
        book_x, book_y = 330, 35
        page_offset = int(pyxel.frame_count / 10) % 4  # Simple animation
        if self.hit_flash > 0:
            # Flash white on hit
            pyxel.rect(book_x - 10, book_y - 5, 28, 28, C_WHITE)
        pyxel.rect(book_x, book_y, 12, 18, C_DARK)
        pyxel.rectb(book_x, book_y, 12, 18, C_RED)
        # Pages
        for i in range(3):
            px = book_x + 2 + i * 3 + page_offset
            pyxel.line(px, book_y + 2, px, book_y + 16, C_WHITE)
        pyxel.text(book_x - 4, book_y + 22, "GRIMOIRE", C_RED)

    def draw_player_info(self) -> None:
        # HP
        info_x = 10
        info_y = 68
        pyxel.text(info_x, info_y, f"HP: {self.player_hp}/{self.player_max_hp}", C_GREEN)

        # HP bar
        bar_w = 100
        pyxel.rect(info_x, info_y + 10, bar_w, 8, C_DARK)
        hp_pct = max(0, self.player_hp / self.player_max_hp)
        pyxel.rect(info_x, info_y + 10, int(bar_w * hp_pct), 8, C_GREEN)
        pyxel.rectb(info_x, info_y + 10, bar_w, 8, C_LIGHT)

        # Heat
        heat_y = info_y + 25
        pyxel.text(info_x, heat_y, f"HEAT: {self.heat}/{self.max_heat}", C_ORANGE)
        pyxel.rect(info_x, heat_y + 10, bar_w, 6, C_DARK)
        heat_pct = self.heat / self.max_heat
        pyxel.rect(info_x, heat_y + 10, int(bar_w * heat_pct), 6,
                    C_YELLOW if heat_pct > 0.4 else C_RED)
        pyxel.rectb(info_x, heat_y + 10, bar_w, 6, C_LIGHT)

        # Risk
        risk_y = heat_y + 22
        risk_label = f"RISK: {self.risk}/{self.max_risk}"
        risk_color = C_RED if self.risk >= 7 else (C_ORANGE if self.risk >= 4 else C_PEACH)
        pyxel.text(info_x, risk_y, risk_label, risk_color)
        pyxel.rect(info_x, risk_y + 10, bar_w, 6, C_DARK)
        risk_pct = self.risk / self.max_risk
        pyxel.rect(info_x, risk_y + 10, int(bar_w * risk_pct), 6, risk_color)
        pyxel.rectb(info_x, risk_y + 10, bar_w, 6, C_LIGHT)

        # Block indicator
        if self.block > 0:
            block_y = risk_y + 22
            pyxel.text(info_x, block_y, f"BLOCK: {self.block}", C_BLUE)

        # Deck info
        deck_y = 210
        pyxel.text(info_x, deck_y, f"Deck: {len(self.deck)}", C_LIGHT)
        pyxel.text(info_x + 60, deck_y, f"Discard: {len(self.discard)}", C_DARK)

    def draw_synth_area(self) -> None:
        """Draw the synthesis box showing played cards this turn."""
        if not self.played_this_turn:
            return

        syn_x, syn_y = 120, 68
        syn_w = 260
        syn_h = 55

        # Background highlight when synthesis active
        if self.synth_flash > 0:
            flash_color = C_YELLOW if (self.synth_flash // 5) % 2 == 0 else C_ORANGE
            pyxel.rect(syn_x - 2, syn_y - 2, syn_w + 4, syn_h + 4, flash_color)

        pyxel.rect(syn_x, syn_y, syn_w, syn_h, C_DARK)
        pyxel.rectb(syn_x, syn_y, syn_w, syn_h, C_PURPLE)
        pyxel.text(syn_x + 4, syn_y + 2, "Active Syntheses:", C_PURPLE)

        for i, card in enumerate(self.played_this_turn):
            cx = syn_x + 10 + i * 80
            cy = syn_y + 14
            # Card mini representation
            pyxel.rect(cx, cy, 70, 34, card.color)
            pyxel.rectb(cx, cy, 70, 34, C_WHITE)
            pyxel.text(cx + 3, cy + 2, card.display_name, C_WHITE)
            pyxel.text(cx + 3, cy + 12, f"DMG:{card.damage}", C_WHITE)
            if card.block_gain > 0:
                pyxel.text(cx + 3, cy + 22, f"BLK:{card.block_gain}", C_WHITE)
            elif card.element == Element.WIND:
                pyxel.text(cx + 3, cy + 22, f"RISK:{card.wind_effect}", C_WHITE)
            elif card.element == Element.WATER:
                pyxel.text(cx + 3, cy + 22, f"DRAW:{card.draw_bonus}", C_WHITE)
            else:
                pyxel.text(cx + 3, cy + 22, card.element.desc[:12], C_WHITE)

            if card.synthesize_count >= 2:
                # Synthesis indicator
                synth_x = cx + 50
                synth_y = cy - 4
                pyxel.text(synth_x, synth_y, f"x{card.synthesize_count}", C_YELLOW)

    def draw_hand(self) -> None:
        for i, card in enumerate(self.hand):
            cx, cy, cw, ch = self.card_rect(i)
            selected = i == self.selected_card_idx
            can_afford = card.cost <= self.heat

            # Card background
            if selected:
                pyxel.rect(cx - 2, cy - 2, cw + 4, ch + 4, C_WHITE)
            pyxel.rect(cx, cy, cw, ch, card.color)
            if not can_afford:
                # Dim if can't afford
                pyxel.rect(cx, cy, cw, ch, C_DARK)

            pyxel.rectb(cx, cy, cw, ch, C_WHITE if selected else C_DARK)

            # Element name
            name_color = C_WHITE if can_afford else C_DARK
            pyxel.text(cx + 3, cy + 2, card.element.label, name_color)

            # Cost
            cost_str = f"HEAT:{card.cost}"
            pyxel.text(cx + 3, cy + 14, cost_str, C_YELLOW if can_afford else C_DARK)

            # Damage/effect
            eff_str = f"DMG:{card.damage}"
            pyxel.text(cx + 3, cy + 26, eff_str, C_WHITE if can_afford else C_DARK)

            # Additional info for non-Fire elements
            if card.element == Element.EARTH:
                pyxel.text(cx + 2, cy + 36, f"BLK:{card.block_gain}",
                           C_WHITE if can_afford else C_DARK)
            elif card.element == Element.WIND:
                pyxel.text(cx + 2, cy + 36, f"RSK:{card.wind_effect}",
                           C_WHITE if can_afford else C_DARK)
            elif card.element == Element.WATER:
                pyxel.text(cx + 2, cy + 36, f"DRW:{card.draw_bonus if card.draw_bonus > 0 else 1}",
                           C_WHITE if can_afford else C_DARK)
            elif card.element == Element.ARCANE:
                pyxel.text(cx + 2, cy + 36, "SCALES",
                           C_WHITE if can_afford else C_DARK)

    def draw_end_turn_button(self) -> None:
        ex, ey, ew, eh = 320, 270, 70, 22
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        hovered = ex <= mx <= ex + ew and ey <= my <= ey + eh
        color = C_LIGHT if hovered else C_DARK
        pyxel.rect(ex, ey, ew, eh, color)
        pyxel.rectb(ex, ey, ew, eh, C_WHITE)
        txt_color = C_WHITE if not hovered else C_BG
        pyxel.text(ex + 8, ey + 6, "END TURN", txt_color)

        # Restart hint
        pyxel.text(10, 282, "[R] Restart", C_DARK)

    def draw_particles(self) -> None:
        for p in self.particles:
            alpha = max(0, p.life / p.max_life)
            size = int(p.size * alpha)
            if size > 0:
                px, py_int = int(p.x), int(p.y)
                if p.text:
                    pyxel.text(px, py_int, p.text, p.color)
                else:
                    pyxel.rect(px - size // 2, py_int - size // 2, size, size, p.color)

    def draw_message(self) -> None:
        if self.message_timer > 0:
            x = W // 2 - len(self.message) * 2
            centered_x = max(5, min(x, W - len(self.message) * 4 - 5))
            pyxel.text(centered_x, H - 30, self.message, C_WHITE)

    def draw_game_over(self) -> None:
        result = self.check_game_over()
        if result == "win":
            pyxel.rect(0, H // 2 - 30, W, 60, C_DARK)
            pyxel.rectb(0, H // 2 - 30, W, 60, C_YELLOW)
            pyxel.text(W // 2 - 50, H // 2 - 20, "=== VICTORY ===", C_GREEN)
            pyxel.text(W // 2 - 60, H // 2, "Grimoire Golem defeated!", C_WHITE)
            pyxel.text(W // 2 - 40, H // 2 + 16, "[R] Restart", C_LIGHT)
        elif result == "lose":
            pyxel.rect(0, H // 2 - 30, W, 60, C_DARK)
            pyxel.rectb(0, H // 2 - 30, W, 60, C_RED)
            pyxel.text(W // 2 - 50, H // 2 - 20, "=== DEFEAT ===", C_RED)
            if self.risk >= self.max_risk:
                pyxel.text(W // 2 - 60, H // 2, "Risk overflow! Magic out of control!", C_WHITE)
            else:
                pyxel.text(W // 2 - 50, H // 2, "You were defeated...", C_WHITE)
            pyxel.text(W // 2 - 40, H // 2 + 16, "[R] Restart", C_LIGHT)


if __name__ == "__main__":
    Game()
