"""Power Grid — Overload chain deckbuilder prototype.

Core mechanic: Manage 3 generators. Play cards to boost output but build heat.
When heat exceeds threshold, generators OVERLOAD — dealing massive burst damage
that can chain to neighbors. Score = total power produced × chain multiplier.

Source: Game Idea Factory #6 (Score 31.15)
Theme: Power Plant (overload/discharge)
Hooks: chain propagation, 3-slot ultra-minimal UI
Resources: heat (per-generator), combo (chain multiplier)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


# ── Constants ────────────────────────────────────────────────────────────────

SCREEN_W = 400
SCREEN_H = 300
DISPLAY_SCALE = 2
FPS = 30

MAX_TURNS = 12
CARDS_PER_TURN = 4
MAX_HEAT = 100

# Layout
GEN_Y = 190
GEN_W = 100
GEN_H = 60
GEN_GAP = 20
GEN_START_X = (SCREEN_W - (3 * GEN_W + 2 * GEN_GAP)) // 2

CARD_Y = 40
CARD_W = 80
CARD_H = 28
CARD_GAP = 8
CARD_START_X = (SCREEN_W - (CARDS_PER_TURN * CARD_W + (CARDS_PER_TURN - 1) * CARD_GAP)) // 2

BUTTON_W = 80
BUTTON_H = 20
BUTTON_X = SCREEN_W - BUTTON_W - 10
BUTTON_Y = SCREEN_H - BUTTON_H - 10

# Colors
COL_BG = 1  # navy
COL_PANEL = 5  # dark purple-gray
COL_TEXT = 7  # white
COL_HEAT_LOW = 12  # blue
COL_HEAT_MID = 3  # green
COL_HEAT_HIGH = 9  # orange
COL_HEAT_CRIT = 8  # red
COL_OVERLOAD = 10  # yellow
COL_FLASH = 7  # white
COL_CARD = 6  # light gray
COL_CARD_HOVER = 13  # light purple
COL_CARD_SELECTED = 8  # red/pink
COL_SUCCESS = 11  # green
COL_DANGER = 8  # red
COL_GEN_FRAME = 13  # light purple


# ── Data Classes ─────────────────────────────────────────────────────────────


class CardType(Enum):
    FUEL = auto()       # +power, +heat
    COOLANT = auto()    # -heat
    BOOST = auto()      # +power multiplier, +heat/turn
    SURGE = auto()      # instant power, triggers overload check
    DUMP = auto()       # convert heat to power, risky
    VENT = auto()       # -heat to all generators slightly


@dataclass(frozen=True)
class CardDef:
    name: str
    abbr: str
    power: int          # instant power added
    heat: int           # heat added
    cool: int           # heat removed (negative)
    mult_bonus: float   # multiplier bonus for 1 turn
    description: str


CARD_DEFS: dict[CardType, CardDef] = {
    CardType.FUEL: CardDef("Fuel Rod", "FUL", power=15, heat=25, cool=0, mult_bonus=0.0,
                           description="+15 POW +25 HEAT"),
    CardType.COOLANT: CardDef("Coolant", "COL", power=0, heat=0, cool=30, mult_bonus=0.0,
                              description="-30 HEAT"),
    CardType.BOOST: CardDef("Boost", "BST", power=5, heat=15, cool=0, mult_bonus=0.5,
                            description="+5 POW x1.5 +15H"),
    CardType.SURGE: CardDef("Surge", "SRG", power=25, heat=10, cool=0, mult_bonus=0.0,
                            description="+25 POW +10H"),
    CardType.DUMP: CardDef("HeatDump", "DMP", power=0, heat=-20, cool=20, mult_bonus=0.0,
                           description="HEAT->POW -20H"),
    CardType.VENT: CardDef("Vent", "VNT", power=0, heat=-5, cool=0, mult_bonus=0.0,
                           description="-5H ALL gens"),
}


@dataclass
class Generator:
    """A single generator unit with heat mechanics."""
    name: str
    x: int
    y: int
    base_output: int = 10
    overload_threshold: int = 100
    heat: int = 0
    output_mult: float = 1.0
    overloaded: bool = False
    overload_timer: int = 0
    shield_active: bool = False

    @property
    def output(self) -> int:
        return int(self.base_output * self.output_mult)

    @property
    def heat_ratio(self) -> float:
        return min(1.0, self.heat / self.overload_threshold)

    @property
    def color(self) -> int:
        r = self.heat_ratio
        if self.overloaded:
            return COL_OVERLOAD
        if r < 0.3:
            return COL_HEAT_LOW
        if r < 0.6:
            return COL_HEAT_MID
        if r < 0.85:
            return COL_HEAT_HIGH
        return COL_HEAT_CRIT

    def add_heat(self, amount: int) -> bool:
        """Returns True if overload triggered."""
        self.heat = max(0, self.heat + amount)
        if self.heat >= self.overload_threshold and not self.overloaded:
            self.overloaded = True
            self.overload_timer = 15  # frames of visual feedback
            return True
        return False

    def tick_overload(self) -> None:
        if self.overloaded:
            self.overload_timer -= 1
            if self.overload_timer <= 0:
                self.overloaded = False
                self.heat = 0
                self.output_mult = 1.0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


class Phase(Enum):
    DRAW = auto()
    PLAY = auto()
    RESOLVE = auto()
    OVERLOAD_CHAIN = auto()
    DEMAND_CHECK = auto()
    TURN_END = auto()
    VICTORY = auto()
    DEFEAT = auto()


# ── Game Class ───────────────────────────────────────────────────────────────


class PowerGrid:
    """Main game class for Power Grid prototype."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Power Grid", fps=FPS,
                   display_scale=DISPLAY_SCALE)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.DRAW
        self.turn = 1
        self.score = 0
        self.combo_mult = 1.0
        self.hp = 100
        self.max_hp = 100
        self.power_demand = 30  # minimum power needed per turn
        self.power_produced = 0
        self.total_power = 0
        self.demand_met = True

        # Generators
        gen_start_y = GEN_Y
        self.generators: list[Generator] = [
            Generator("Reactor A", GEN_START_X, gen_start_y,
                      base_output=10, overload_threshold=100),
            Generator("Turbine B", GEN_START_X + GEN_W + GEN_GAP, gen_start_y,
                      base_output=8, overload_threshold=80),
            Generator("Solar C", GEN_START_X + 2 * (GEN_W + GEN_GAP), gen_start_y,
                      base_output=5, overload_threshold=60),
        ]

        # Cards
        self.hand: list[CardType | None] = []
        self.selected_card_idx: int | None = None
        self.selected_gen_idx: int | None = None

        # State
        self.message: str = ""
        self.message_timer: int = 0
        self.chain_count: int = 0
        self.phase_timer: int = 0
        self.flash_alpha: float = 0.0

        # Particles
        self.particles: list[Particle] = []

        # Button
        self._deal_cards()
        self.message = f"Turn {self.turn} — Assign cards to generators"

    # ── Card Management ──────────────────────────────────────────────────

    def _deal_cards(self) -> None:
        """Draw a hand of random cards."""
        pool: list[CardType] = list(CardType)
        # Weighted: more FUEL and COOLANT, fewer VENT
        weighted: list[CardType] = []
        for ct in pool:
            if ct == CardType.FUEL:
                weighted.extend([ct] * 4)
            elif ct == CardType.COOLANT:
                weighted.extend([ct] * 3)
            elif ct == CardType.BOOST:
                weighted.extend([ct] * 2)
            elif ct == CardType.SURGE:
                weighted.extend([ct] * 2)
            elif ct == CardType.DUMP:
                weighted.extend([ct] * 2)
            else:
                weighted.append(ct)
        random.shuffle(weighted)
        self.hand: list[CardType | None] = list(weighted[:CARDS_PER_TURN])

    # ── Phase: PLAY ──────────────────────────────────────────────────────

    def _play_card_on_generator(self, card_idx: int, gen_idx: int) -> None:
        """Apply a card effect to a generator."""
        ct = self.hand[card_idx]
        if ct is None:
            return
        gen = self.generators[gen_idx]
        cdef = CARD_DEFS[ct]

        # Apply effects
        self.power_produced += cdef.power
        gen.output_mult += cdef.mult_bonus

        if ct == CardType.VENT:
            # Cool ALL generators by 5 each
            for g in self.generators:
                triggered = g.add_heat(cdef.heat)  # -5
                if triggered:
                    self._start_overload_chain(self.generators.index(g))
            msg = "Vent! All -5H"
        elif ct == CardType.DUMP:
            # Convert current heat to power, then reduce heat
            heat_power = gen.heat // 2
            self.power_produced += heat_power
            triggered = gen.add_heat(cdef.heat)  # -20
            if triggered:
                self._start_overload_chain(gen_idx)
            msg = f"{cdef.name} on {gen.name}: +{heat_power}POW"
        else:
            triggered = gen.add_heat(cdef.heat)
            msg = f"{cdef.name} on {gen.name}: +{cdef.power}POW +{cdef.heat}H"
            if triggered:
                self._start_overload_chain(gen_idx)

        self.message = msg
        self.message_timer = 60
        self.score += cdef.power

        # Remove card from hand
        self.hand[card_idx] = None

        # Check if all cards played or none left
        all_played = all(c is None for c in self.hand)
        if all_played:
            self.phase = Phase.RESOLVE
            self.phase_timer = 0
            self.selected_card_idx = None
            self.selected_gen_idx = None

    def _start_overload_chain(self, gen_idx: int) -> None:
        """Initiate overload chain starting from generator."""
        self.phase = Phase.OVERLOAD_CHAIN
        self.chain_count = 1
        self.phase_timer = 20
        gen = self.generators[gen_idx]

        # Spawn particles
        for _ in range(20):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.0, 4.0)
            self.particles.append(Particle(
                x=gen.x + GEN_W / 2,
                y=gen.y + GEN_H / 2,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=random.randint(10, 25),
                color=COL_OVERLOAD,
                size=random.randint(2, 4),
            ))

        # Try to chain to neighbors
        for i, neighbor in enumerate(self.generators):
            if i == gen_idx:
                continue
            if abs(i - gen_idx) == 1:  # adjacent
                chain_heat = 40
                if neighbor.add_heat(chain_heat):
                    self.chain_count += 1
                    for _ in range(20):
                        angle = random.uniform(0, math.pi * 2)
                        speed = random.uniform(1.0, 4.0)
                        self.particles.append(Particle(
                            x=neighbor.x + GEN_W / 2,
                            y=neighbor.y + GEN_H / 2,
                            vx=math.cos(angle) * speed,
                            vy=math.sin(angle) * speed,
                            life=random.randint(10, 25),
                            color=COL_OVERLOAD,
                            size=random.randint(2, 4),
                        ))

        # Score for chain
        chain_bonus = self.chain_count * 50
        self.combo_mult += self.chain_count * 0.5
        self.score += chain_bonus
        self.message = f"OVERLOAD x{self.chain_count}! +{chain_bonus}"
        self.message_timer = 90

        # Overload also damages player slightly
        self.hp -= self.chain_count * 5

    # ── Phase: RESOLVE ───────────────────────────────────────────────────

    def _resolve_turn(self) -> None:
        """Process generator output, check demand."""
        # Generators produce power
        for gen in self.generators:
            gen.tick_overload()
            if not gen.overloaded:
                produced = gen.output
                self.power_produced += produced
            # Reset multiplier from BOOST cards
            gen.output_mult = max(1.0, gen.output_mult - 0.3)
            if gen.output_mult < 1.0:
                gen.output_mult = 1.0

        self.total_power += self.power_produced
        self.score += self.power_produced

        self.phase = Phase.DEMAND_CHECK
        self.phase_timer = 0

    def _check_demand(self) -> None:
        """Check if power demand was met."""
        demand = self.power_demand + (self.turn - 1) * 5
        if self.power_produced >= demand:
            self.demand_met = True
            self.message = f"Demand {demand} MET! +{self.power_produced}POW"
            self.message_timer = 60
            bonus = self.power_produced - demand
            self.score += bonus
        else:
            self.demand_met = False
            shortfall = demand - self.power_produced
            self.hp -= shortfall // 3
            self.message = f"Demand {demand} FAILED! -{shortfall // 3}HP"
            self.message_timer = 60

        self.phase = Phase.TURN_END
        self.phase_timer = 0

    def _end_turn(self) -> None:
        """Advance to next turn or end game."""
        if self.hp <= 0:
            self.hp = 0
            self.phase = Phase.DEFEAT
            self.message = "MELTDOWN! Power grid destroyed."
            self.message_timer = 999
            return

        self.turn += 1
        if self.turn > MAX_TURNS:
            self.phase = Phase.VICTORY
            final_score = int(self.score * self.combo_mult)
            self.score = final_score
            self.message = f"GRID STABLE! Score: {final_score}"
            self.message_timer = 999
            return

        self.power_produced = 0
        self.demand_met = True
        self._deal_cards()
        self.selected_card_idx = None
        self.selected_gen_idx = None
        self.phase = Phase.PLAY
        self.message = f"Turn {self.turn} — Demand: {self.power_demand + (self.turn - 1) * 5}POW"

    # ── Update ───────────────────────────────────────────────────────────

    def update(self) -> None:
        """Main update loop."""
        # Always update particles
        self._update_particles()

        if self.phase in (Phase.VICTORY, Phase.DEFEAT):
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_R):
                self.reset()
            return

        # Timed phases
        if self.phase == Phase.RESOLVE:
            self.phase_timer += 1
            if self.phase_timer > 10:
                self._resolve_turn()
            return

        if self.phase == Phase.DEMAND_CHECK:
            self.phase_timer += 1
            if self.phase_timer > 10:
                self._check_demand()
            return

        if self.phase == Phase.TURN_END:
            self.phase_timer += 1
            if self.phase_timer > 30:
                self._end_turn()
            return

        if self.phase == Phase.OVERLOAD_CHAIN:
            self.phase_timer -= 1
            self.flash_alpha = max(0.0, self.phase_timer / 20.0)
            if self.phase_timer <= 0:
                self.phase = Phase.PLAY
                self.flash_alpha = 0.0
            return

        # PLAY phase: handle card selection and assignment
        if self.phase == Phase.PLAY:
            # Message timer
            if self.message_timer > 0:
                self.message_timer -= 1

            # Click on card
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                mx, my = pyxel.mouse_x, pyxel.mouse_y

                # Check card clicks
                card_clicked: int | None = None
                for i, ct in enumerate(self.hand):
                    if ct is None:
                        continue
                    cx = CARD_START_X + i * (CARD_W + CARD_GAP)
                    if cx <= mx < cx + CARD_W and CARD_Y <= my < CARD_Y + CARD_H:
                        card_clicked = i
                        break

                if card_clicked is not None:
                    self.selected_card_idx = card_clicked
                    self.selected_gen_idx = None
                    return

                # Check generator clicks (if card selected)
                if self.selected_card_idx is not None:
                    for i, gen in enumerate(self.generators):
                        if gen.x <= mx < gen.x + GEN_W and gen.y <= my < gen.y + GEN_H:
                            self._play_card_on_generator(self.selected_card_idx, i)
                            return

                # Check TICK button (skip remaining cards)
                if BUTTON_X <= mx < BUTTON_X + BUTTON_W and BUTTON_Y <= my < BUTTON_Y + BUTTON_H:
                    self.phase = Phase.RESOLVE
                    self.phase_timer = 0
                    self.selected_card_idx = None
                    self.selected_gen_idx = None
                    return

    # ── Particle System ──────────────────────────────────────────────────

    def _update_particles(self) -> None:
        """Move particles, reduce life, remove dead ones."""
        surviving: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1  # gravity
            p.life -= 1
            if p.life > 0:
                surviving.append(p)
        self.particles = surviving

    # ── Draw ─────────────────────────────────────────────────────────────

    def draw(self) -> None:
        """Main draw loop."""
        pyxel.cls(COL_BG)

        self._draw_header()
        self._draw_generators()
        self._draw_cards()
        self._draw_button()
        self._draw_message()
        self._draw_particles()

        # Overload flash
        if self.flash_alpha > 0:
            flash_col = COL_FLASH if int(self.flash_alpha * 10) % 2 == 0 else COL_BG
            pyxel.dither(0.5)
            pyxel.rect(0, 0, SCREEN_W, SCREEN_H, flash_col)
            pyxel.dither(1.0)

        # Game over overlay
        if self.phase in (Phase.VICTORY, Phase.DEFEAT):
            pyxel.rect(0, SCREEN_H // 2 - 20, SCREEN_W, 40, COL_BG)
            color = COL_SUCCESS if self.phase == Phase.VICTORY else COL_DANGER
            status_msg = "GRID STABLE!" if self.phase == Phase.VICTORY else "MELTDOWN!"
            pyxel.text(SCREEN_W // 2 - len(status_msg) * 2, SCREEN_H // 2 - 12,
                       status_msg, color)
            retry_msg = "Press SPACE to retry"
            pyxel.text(SCREEN_W // 2 - len(retry_msg) * 2, SCREEN_H // 2 + 4,
                       retry_msg, COL_TEXT)

    def _draw_header(self) -> None:
        """Draw top bar: turn, score, HP, demand."""
        # Turn and score
        pyxel.text(4, 2, f"TURN {self.turn}/{MAX_TURNS}", COL_TEXT)
        combo_text = f"x{self.combo_mult:.1f}" if self.combo_mult > 1.0 else ""
        pyxel.text(4, 10, f"SCORE: {int(self.score)} {combo_text}", COL_SUCCESS)

        # HP bar
        pyxel.text(SCREEN_W - 120, 2,
                   f"HP: {self.hp}/{self.max_hp}", COL_DANGER if self.hp < 30 else COL_TEXT)
        bar_w = 100
        hp_ratio = max(0, self.hp / self.max_hp)
        pyxel.rect(SCREEN_W - 110, 10, bar_w, 4, COL_PANEL)
        if hp_ratio > 0:
            hp_color = COL_DANGER if hp_ratio < 0.3 else COL_SUCCESS
            pyxel.rect(SCREEN_W - 110, 10, int(bar_w * hp_ratio), 4, hp_color)

        # Power demand
        demand = self.power_demand + (self.turn - 1) * 5
        met_text = f"POW: {self.power_produced}/{demand}"
        met_color = COL_SUCCESS if self.power_produced >= demand else COL_DANGER
        pyxel.text(SCREEN_W - 120, 16, met_text, met_color)

        # Total power earned
        pyxel.text(4, 18, f"TOTAL:{self.total_power}POW", COL_TEXT)

    def _draw_generators(self) -> None:
        """Draw the 3 generator units with heat gauges."""
        for i, gen in enumerate(self.generators):
            # Generator panel
            x, y = gen.x, gen.y
            frame_color = COL_GEN_FRAME
            if self.selected_card_idx is not None and self.phase == Phase.PLAY:
                # Highlight generators that can be targeted
                frame_color = COL_CARD_SELECTED
            if gen.overloaded:
                frame_color = COL_OVERLOAD

            pyxel.rect(x, y, GEN_W, GEN_H, COL_PANEL)
            pyxel.rectb(x, y, GEN_W, GEN_H, frame_color)

            # Name
            pyxel.text(x + 3, y + 3, gen.name[:10], COL_TEXT)

            # Output display
            out_text = f"OUT:{gen.output}"
            pyxel.text(x + 3, y + 12, out_text, COL_SUCCESS)

            # Mult indicator
            if gen.output_mult > 1.0:
                pyxel.text(x + 3, y + 22, f"x{gen.output_mult:.1f}", COL_OVERLOAD)

            # Overload indicator
            if gen.overloaded:
                flash = int(pyxel.frame_count / 4) % 2
                if flash:
                    pyxel.text(x + GEN_W - 30, y + 3, "!!!", COL_OVERLOAD)

            # Heat bar (below generator)
            bar_y = y + GEN_H + 4
            bar_w = GEN_W - 4
            pyxel.rect(x + 2, bar_y, bar_w, 4, COL_BG)
            heat_ratio = gen.heat_ratio
            if heat_ratio > 0:
                pyxel.rect(x + 2, bar_y, max(1, int(bar_w * heat_ratio)), 4, gen.color)
            pyxel.rectb(x + 2, bar_y, bar_w, 4, COL_TEXT)
            heat_text = f"{gen.heat}/{gen.overload_threshold}"
            pyxel.text(x + 2, bar_y + 5, heat_text, COL_TEXT)

            # Overload threshold marker (small vertical line)
            threshold_x = x + 2 + int(bar_w) - 1
            pyxel.line(threshold_x, bar_y, threshold_x, bar_y + 4, COL_OVERLOAD)

    def _draw_cards(self) -> None:
        """Draw the player's hand of cards."""
        for i, ct in enumerate(self.hand):
            cx = CARD_START_X + i * (CARD_W + CARD_GAP)
            cy = CARD_Y

            if ct is None:
                # Empty slot
                pyxel.rect(cx, cy, CARD_W, CARD_H, COL_BG)
                pyxel.rectb(cx, cy, CARD_W, CARD_H, COL_PANEL)
                continue

            cdef = CARD_DEFS[ct]

            # Card background
            card_color = COL_CARD
            if i == self.selected_card_idx:
                card_color = COL_CARD_SELECTED
            elif self._is_mouse_over_card(i):
                card_color = COL_CARD_HOVER

            pyxel.rect(cx, cy, CARD_W, CARD_H, card_color)
            pyxel.rectb(cx, cy, CARD_W, CARD_H, COL_TEXT)

            # Card name
            pyxel.text(cx + 3, cy + 3, cdef.name[:8], COL_BG)

            # Card abbreviation and effect
            pyxel.text(cx + 3, cy + 14, cdef.abbr, COL_BG)
            pyxel.text(cx + 3, cy + 22, cdef.description[:14], COL_BG)

    def _draw_button(self) -> None:
        """Draw the TICK / end-turn button."""
        # Only show in PLAY phase
        if self.phase != Phase.PLAY:
            return

        mx, my = pyxel.mouse_x, pyxel.mouse_y
        hover = (BUTTON_X <= mx < BUTTON_X + BUTTON_W and
                 BUTTON_Y <= my < BUTTON_Y + BUTTON_H)
        btn_color = COL_CARD_HOVER if hover else COL_CARD
        pyxel.rect(BUTTON_X, BUTTON_Y, BUTTON_W, BUTTON_H, btn_color)
        pyxel.rectb(BUTTON_X, BUTTON_Y, BUTTON_W, BUTTON_H, COL_TEXT)
        pyxel.text(BUTTON_X + 10, BUTTON_Y + 5, "TICK >", COL_BG)

    def _draw_message(self) -> None:
        """Draw status message at bottom-center."""
        if self.message_timer <= 0 and self.phase != Phase.PLAY:
            return
        if self.message:
            msg_x = (SCREEN_W - len(self.message) * 4) // 2
            msg_y = SCREEN_H - 28
            pyxel.text(msg_x, msg_y, self.message, COL_OVERLOAD)

    def _draw_particles(self) -> None:
        """Draw active particles."""
        for p in self.particles:
            alpha = p.life / 25.0
            c = p.color
            if alpha < 0.3:
                c = COL_HEAT_CRIT
            pyxel.pset(int(p.x), int(p.y), c)
            if p.size > 2:
                pyxel.pset(int(p.x) + 1, int(p.y), c)
                pyxel.pset(int(p.x), int(p.y) + 1, c)

    def _is_mouse_over_card(self, idx: int) -> bool:
        """Check if mouse is hovering over a card."""
        cx = CARD_START_X + idx * (CARD_W + CARD_GAP)
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        return cx <= mx < cx + CARD_W and CARD_Y <= my < CARD_Y + CARD_H


# ── Entry Point ──────────────────────────────────────────────────────────────


if __name__ == "__main__":
    PowerGrid()
