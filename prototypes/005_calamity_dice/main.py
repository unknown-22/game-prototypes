"""
Calamity Dice — Dice Battler Prototype
========================================
Concept: Roll elemental dice, pick ONE element to channel per turn.
Channeled dice enter your "log" and return next turn as bonus dice,
building an avalanche of power. But channeling builds HEAT — too much
heat and you take feedback damage. Balance power vs. safety.

Theme: Calamity Sealing (runaway control) — you're a sealer fighting
elemental disasters with unstable dice magic.

Score 31.45 idea (#1) from Game Idea Factory.
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

# Element definitions
ELEMENTS = 5
ELEM_NAMES = ["FIRE", "WATR", "ERTH", "AIR", "AETHR"]
ELEM_COLORS = [8, 12, 11, 7, 13]  # red, blue, green, white, purple
ELEM_DARK = [2, 1, 3, 6, 5]       # darker shades for inactive dice

# Dice
DICE_SIZE = 36
DICE_GAP = 8
DICE_Y = 64
LOG_DICE_SIZE = 20
LOG_DICE_Y = DICE_Y + DICE_SIZE + 14

# Element buttons
BTN_W = 56
BTN_H = 24
BTN_Y = 200
BTN_X0 = 10
BTN_GAP = 4

# Heat system
HEAT_BASE = 3       # passive heat per turn
HEAT_PER_DIE = 5    # heat per activated die
HEAT_COOL = 15      # natural cooling per turn
HEAT_WARN = 70      # warning threshold
HEAT_DANGER = 90    # damage threshold
HEAT_DAMAGE = 4     # damage taken when over danger

# Dice pool
BASE_DICE = 3
MAX_DICE = 7
MAX_LOG = 4

# Damage per die value
DAMAGE_PER_PIP = 2

# Enemy scaling
ENEMY_WAVES = [
    {"name": "Flame Sprite", "hp": 35, "atk": 3, "color": 8},
    {"name": "Tidal Wyrm",  "hp": 55, "atk": 5, "color": 12},
    {"name": "Earth Titan", "hp": 80, "atk": 7, "color": 11},
]

# Messages
MSG_DURATION = 45  # frames


# ── Phase Enum ────────────────────────────────────────────────────────────────
class Phase(Enum):
    ROLL = auto()
    SELECT = auto()
    ANIMATE = auto()
    ENEMY_TURN = auto()
    CHECK = auto()
    VICTORY = auto()
    DEFEAT = auto()


# ── Data Classes ──────────────────────────────────────────────────────────────
@dataclass
class Die:
    """A single elemental die."""
    element: int  # 0-4
    value: int    # 1-6
    active: bool = False
    x: int = 0
    y: int = 0
    anim_frame: int = 0  # for roll animation
    flash_timer: int = 0  # for activate flash

    @property
    def color(self) -> int:
        return ELEM_COLORS[self.element] if self.active else ELEM_DARK[self.element]

    @property
    def elem_name(self) -> str:
        return ELEM_NAMES[self.element]


@dataclass
class Particle:
    """Floating damage/heal number."""
    x: float
    y: float
    vy: float
    text: str
    color: int
    life: int = 30
    timer: int = 0

    @property
    def alive(self) -> bool:
        return self.timer < self.life


@dataclass
class Message:
    """Timed message display."""
    text: str
    color: int
    duration: int = MSG_DURATION
    timer: int = 0

    @property
    def alive(self) -> bool:
        return self.timer < self.duration

    @property
    def alpha(self) -> float:
        if self.timer < 10:
            return self.timer / 10
        if self.timer > self.duration - 10:
            return (self.duration - self.timer) / 10
        return 1.0


# ── Game Class ────────────────────────────────────────────────────────────────
class CalamityDice:
    """Main game class — dice battler with log/replay mechanic."""

    def __init__(self) -> None:
        pyxel.init(W, H, title="Calamity Dice", fps=FPS, display_scale=SCALE)
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── State Management ──────────────────────────────────────────────────
    def reset(self) -> None:
        """Initialize or reset all game state."""
        self.phase = Phase.ROLL
        self.turn: int = 0
        self.score: int = 0
        self.wave: int = 0
        self.hp: int = 30
        self.max_hp: int = 30
        self.heat: int = 0
        self.selected_element: int = -1
        self.streak: int = 0  # consecutive turns picking same element
        self.last_element: int = -1

        # Dice
        self.dice: list[Die] = []
        self.log_dice: list[Die] = []  # dice carried over from previous turn

        # Enemy
        self.enemy_hp: int = 0
        self.enemy_max_hp: int = 0
        self.enemy_atk: int = 0
        self.enemy_name: str = ""
        self.enemy_color: int = 8

        # Effects
        self.particles: list[Particle] = []
        self.messages: list[Message] = []

        # Animation substate
        self.anim_frame: int = 0
        self.anim_duration: int = 0
        self.pending_damage: int = 0
        self.pending_heat: int = 0

        self._spawn_enemy()

    def _spawn_enemy(self) -> None:
        """Spawn the next wave enemy."""
        if self.wave >= len(ENEMY_WAVES):
            self.phase = Phase.VICTORY
            return
        wave_data = ENEMY_WAVES[self.wave]
        self.enemy_name: str = str(wave_data["name"])
        self.enemy_hp: int = int(wave_data["hp"])
        self.enemy_max_hp: int = int(wave_data["hp"])
        self.enemy_atk: int = int(wave_data["atk"])
        self.enemy_color: int = int(wave_data["color"])

    # ── Dice Logic ────────────────────────────────────────────────────────
    def _roll_dice(self) -> None:
        """Roll all dice: base pool + log dice from previous turn."""
        self.dice.clear()

        # Base dice
        for _ in range(BASE_DICE):
            d = Die(
                element=random.randint(0, ELEMENTS - 1),
                value=random.randint(1, 6),
            )
            self.dice.append(d)

        # Log dice (bonus from previous turn)
        for ld in self.log_dice:
            d = Die(element=ld.element, value=ld.value, active=False)
            self.dice.append(d)

        # Cap at MAX_DICE
        if len(self.dice) > MAX_DICE:
            self.dice = self.dice[:MAX_DICE]

        # Assign screen positions
        total = len(self.dice)
        total_w = total * DICE_SIZE + (total - 1) * DICE_GAP
        start_x = (W - total_w) // 2
        for i, d in enumerate(self.dice):
            d.x = start_x + i * (DICE_SIZE + DICE_GAP)
            d.y = DICE_Y
            d.anim_frame = random.randint(0, 3)  # varied roll state

        # Clear the log (it's been consumed)
        self.log_dice.clear()
        self.selected_element = -1
        self.streak = 0

    def _activate_dice(self, element: int) -> tuple[int, int]:
        """Activate all dice matching the given element.
        Returns (total_damage, heat_generated)."""
        self.selected_element = element
        damage = 0
        heat = HEAT_BASE

        for d in self.dice:
            if d.element == element:
                d.active = True
                d.flash_timer = 15
                damage += d.value * DAMAGE_PER_PIP
                heat += HEAT_PER_DIE
                # Add to log for next turn (capped)
                if len(self.log_dice) < MAX_LOG:
                    self.log_dice.append(Die(element=d.element, value=d.value))

        return damage, heat

    # ── Update ────────────────────────────────────────────────────────────
    def update(self) -> None:
        """Main update loop — dispatch by phase."""
        # Update particles always
        for p in self.particles[:]:
            p.timer += 1
            p.y += p.vy
            p.vy += 0.1
            if not p.alive:
                self.particles.remove(p)

        # Update messages always
        for m in self.messages[:]:
            m.timer += 1
            if not m.alive:
                self.messages.remove(m)

        # Update dice flash timers
        for d in self.dice:
            if d.flash_timer > 0:
                d.flash_timer -= 1

        # Phase dispatch
        handlers = {
            Phase.ROLL: self._update_roll,
            Phase.SELECT: self._update_select,
            Phase.ANIMATE: self._update_animate,
            Phase.ENEMY_TURN: self._update_enemy_turn,
            Phase.CHECK: self._update_check,
            Phase.VICTORY: self._update_victory,
            Phase.DEFEAT: self._update_defeat,
        }
        handler = handlers.get(self.phase)
        if handler:
            handler()

    def _update_roll(self) -> None:
        """Roll animation phase."""
        if self.anim_frame == 0:
            self.turn += 1
            self._roll_dice()
        self.anim_frame += 1
        # Show roll animation for 20 frames then transition
        if self.anim_frame >= 20:
            self.anim_frame = 0
            self.phase = Phase.SELECT

    def _update_select(self) -> None:
        """Player selection phase — click element button."""
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx, my = pyxel.mouse_x, pyxel.mouse_y
            # Check element buttons
            for e in range(ELEMENTS):
                bx = BTN_X0 + e * (BTN_W + BTN_GAP)
                by = BTN_Y
                if bx <= mx < bx + BTN_W and by <= my < by + BTN_H:
                    # Check if at least one die of this element exists
                    has_die = any(d.element == e for d in self.dice)
                    if not has_die:
                        self._add_message(f"No {ELEM_NAMES[e]} dice!", 8)
                        continue
                    self._activate_and_animate(e)
                    return

    def _activate_and_animate(self, element: int) -> None:
        """Activate dice and start animation phase."""
        damage, heat = self._activate_dice(element)

        # Track streak
        if self.last_element == element:
            self.streak += 1
        else:
            self.streak = 1
            self.last_element = element

        # Apply damage
        self.enemy_hp = max(0, self.enemy_hp - damage)
        self.score += damage
        self.pending_damage = damage
        self.pending_heat = heat

        # Add particle for damage
        self.particles.append(Particle(
            x=W // 2, y=DICE_Y - 10,
            vy=-1.5, text=str(damage), color=ELEM_COLORS[element],
        ))

        if self.streak >= 3:
            self._add_message(f"{self.streak}x STREAK!", ELEM_COLORS[element])

        self.phase = Phase.ANIMATE
        self.anim_frame = 0

    def _update_animate(self) -> None:
        """Animation phase — show damage, heat, then transition."""
        self.anim_frame += 1
        if self.anim_frame == 5:
            # Apply heat
            self.heat += self.pending_heat
            if self.heat > 100:
                self.heat = 100
            if self.pending_heat > 20:
                self._add_message(f"+{self.pending_heat} HEAT!", 8)
        if self.anim_frame >= 20:
            self.anim_frame = 0
            self.phase = Phase.ENEMY_TURN

    def _update_enemy_turn(self) -> None:
        """Enemy attacks player."""
        self.anim_frame += 1
        if self.anim_frame == 5:
            # Enemy attack
            dmg = self.enemy_atk + self.turn // 5  # scaling
            self.hp -= dmg
            self.particles.append(Particle(
                x=W // 2, y=H // 3,
                vy=1.5, text=str(dmg), color=8,
            ))
            # Heat feedback damage
            if self.heat >= HEAT_DANGER:
                overheat_dmg = HEAT_DAMAGE
                self.hp -= overheat_dmg
                self.particles.append(Particle(
                    x=W // 2 + 30, y=H // 3,
                    vy=1.5, text=f"OVR{overheat_dmg}", color=8,
                ))
                self._add_message("OVERHEAT!", 8)
            # Heat warning
            elif self.heat >= HEAT_WARN:
                self._add_message("HEAT WARNING!", 9)

        if self.anim_frame >= 15:
            # Cooldown
            self.heat = max(0, self.heat - HEAT_COOL)
            self.anim_frame = 0
            self.phase = Phase.CHECK

    def _update_check(self) -> None:
        """Check win/lose conditions."""
        if self.hp <= 0:
            self.hp = 0
            self.score += self.turn * 5  # bonus for surviving turns
            self.phase = Phase.DEFEAT
            self._add_message("DEFEAT — Click to retry", 8)
        elif self.enemy_hp <= 0:
            self.score += (self.max_hp - self.hp) * 10  # health bonus
            self.wave += 1
            if self.wave >= len(ENEMY_WAVES):
                self.score += 100
                self.phase = Phase.VICTORY
                self._add_message("ALL CALAMITIES SEALED!", 11)
            else:
                self._add_message(f"Wave {self.wave + 1} incoming!", 7)
                self._spawn_enemy()
                self.heat = max(0, self.heat - 30)  # partial cooldown between waves
                self.phase = Phase.ROLL
                self.anim_frame = 0
        else:
            self.phase = Phase.ROLL
            self.anim_frame = 0

    def _update_victory(self) -> None:
        """Victory screen — click to restart."""
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()

    def _update_defeat(self) -> None:
        """Defeat screen — click to restart."""
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()

    def _add_message(self, text: str, color: int) -> None:
        """Add a timed message to the display queue."""
        self.messages.append(Message(text=text, color=color))

    # ── Draw ──────────────────────────────────────────────────────────────
    def draw(self) -> None:
        """Main draw loop."""
        pyxel.cls(0)

        if self.phase in (Phase.VICTORY, Phase.DEFEAT):
            self._draw_end_screen()
        else:
            self._draw_background()
            self._draw_enemy()
            self._draw_dice()
            self._draw_log_preview()
            self._draw_element_buttons()
            self._draw_player_panel()
            self._draw_messages()
            self._draw_particles()

    def _draw_background(self) -> None:
        """Subtle background elements."""
        # Divider lines
        pyxel.rect(0, 0, W, 22, 1)
        pyxel.text(4, 4, f"WAVE {self.wave + 1}/{len(ENEMY_WAVES)}", 7)
        pyxel.text(W - 60, 4, f"T:{self.turn}", 7)
        pyxel.text(W - 32, 4, f"S:{self.score}", 9)

    def _draw_enemy(self) -> None:
        """Draw enemy representation."""
        # Enemy name
        pyxel.text(W // 2 - len(self.enemy_name) * 2, 30, self.enemy_name, self.enemy_color)

        # Enemy HP bar
        bar_w = 180
        bar_x = (W - bar_w) // 2
        bar_y = 42
        bar_h = 6
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, 1)
        if self.enemy_max_hp > 0:
            hp_ratio = self.enemy_hp / self.enemy_max_hp
            fill_w = int(bar_w * hp_ratio)
            if fill_w > 0:
                pyxel.rect(bar_x, bar_y, fill_w, bar_h, self.enemy_color)
        pyxel.text(bar_x + 2, bar_y + 1, f"{self.enemy_hp}/{self.enemy_max_hp}", 7)

    def _draw_dice(self) -> None:
        """Draw the dice row."""
        for d in self.dice:
            if self.phase == Phase.ROLL and d.anim_frame > 0:
                # Show random face during roll animation
                rx = d.x + random.randint(-2, 2)
                ry = d.y + random.randint(-2, 2)
                c = random.choice(ELEM_COLORS)
                pyxel.rect(rx, ry, DICE_SIZE, DICE_SIZE, c)
                pyxel.rectb(rx, ry, DICE_SIZE, DICE_SIZE, 7)
                temp_val = random.randint(1, 6)
                pyxel.text(rx + DICE_SIZE // 2 - 2, ry + DICE_SIZE // 2 - 2, str(temp_val), 0)
                continue

            # Determine color
            if d.active and d.flash_timer > 0 and d.flash_timer % 4 < 2:
                bg = 7  # flash white briefly
            elif d.active:
                bg = ELEM_COLORS[d.element]
            elif self.phase == Phase.SELECT and self.selected_element == -1:
                bg = ELEM_DARK[d.element]
            else:
                bg = ELEM_DARK[d.element]

            # Draw die body
            pyxel.rect(d.x, d.y, DICE_SIZE, DICE_SIZE, bg)
            border = 10 if d.active else 5
            pyxel.rectb(d.x, d.y, DICE_SIZE, DICE_SIZE, border)

            # Draw value pip
            txt = str(d.value)
            tx = d.x + DICE_SIZE // 2 - len(txt) * 2 + 1
            ty = d.y + DICE_SIZE // 2 - 3
            pyxel.text(tx, ty, txt, 0 if d.active else 7)

            # Element indicator (small colored dot)
            if not d.active:
                dot_x = d.x + 2
                pyxel.pset(dot_x + 1, d.y + 2, ELEM_COLORS[d.element])

    def _draw_log_preview(self) -> None:
        """Draw the log preview — dice that will return next turn."""
        if not self.log_dice:
            return

        pyxel.text(10, LOG_DICE_Y - 8, "LOG:", 6)
        for i, ld in enumerate(self.log_dice):
            lx = 10 + i * (LOG_DICE_SIZE + 4)
            ly = LOG_DICE_Y
            pyxel.rect(lx, ly, LOG_DICE_SIZE, LOG_DICE_SIZE, ELEM_COLORS[ld.element])
            pyxel.rectb(lx, ly, LOG_DICE_SIZE, LOG_DICE_SIZE, 10)
            val_txt = str(ld.value)
            tx = lx + LOG_DICE_SIZE // 2 - len(val_txt) * 2 + 1
            ty = ly + LOG_DICE_SIZE // 2 - 3
            pyxel.text(tx, ty, val_txt, 0)

    def _draw_element_buttons(self) -> None:
        """Draw the 5 element selection buttons."""
        for e in range(ELEMENTS):
            bx = BTN_X0 + e * (BTN_W + BTN_GAP)
            by = BTN_Y

            # Hover highlight
            if self.phase == Phase.SELECT:
                mx, my = pyxel.mouse_x, pyxel.mouse_y
                hovered = bx <= mx < bx + BTN_W and by <= my < by + BTN_H
            else:
                hovered = False

            bg = ELEM_COLORS[e] if hovered else ELEM_DARK[e]
            if self.selected_element == e:
                bg = ELEM_COLORS[e]

            pyxel.rect(bx, by, BTN_W, BTN_H, bg)
            pyxel.rectb(bx, by, BTN_W, BTN_H, 7)

            # Element name
            name = ELEM_NAMES[e]
            tx = bx + BTN_W // 2 - len(name) * 2 + 1
            ty = by + BTN_H // 2 - 3
            pyxel.text(tx, ty, name, 0 if hovered or self.selected_element == e else 7)

            # Dice count badge
            if self.phase == Phase.SELECT:
                count = sum(1 for d in self.dice if d.element == e)
                if count > 0:
                    pyxel.text(bx + BTN_W - 14, by + 2, f"x{count}", 7)

    def _draw_player_panel(self) -> None:
        """Draw player stats: HP, Heat bar."""
        # HP
        px, py = W - 100, 100
        pyxel.text(px, py, "HP", 7)
        bar_w = 80
        pyxel.rect(px + 16, py, bar_w, 6, 1)
        hp_ratio = self.hp / self.max_hp
        fill_w = int(bar_w * hp_ratio)
        if fill_w > 0:
            hp_color = 11 if hp_ratio > 0.5 else (9 if hp_ratio > 0.25 else 8)
            pyxel.rect(px + 16, py, fill_w, 6, hp_color)
        pyxel.text(px + 16, py + 1, f"{self.hp}/{self.max_hp}", 7)

        # Heat bar
        hy = py + 20
        heat_color = 8 if self.heat >= HEAT_DANGER else (9 if self.heat >= HEAT_WARN else 12)
        pyxel.text(px, hy, "HEAT", heat_color)
        pyxel.rect(px + 20, hy, bar_w, 6, 1)
        heat_fill = int(bar_w * self.heat / 100)
        if heat_fill > 0:
            pyxel.rect(px + 20, hy, heat_fill, 6, heat_color)
        pyxel.text(px + 20, hy + 1, f"{self.heat}%", 7)

        # Danger lines on heat bar
        wx = px + 20 + int(bar_w * HEAT_WARN / 100)
        dx = px + 20 + int(bar_w * HEAT_DANGER / 100)
        pyxel.line(wx, hy, wx, hy + 6, 9)
        pyxel.line(dx, hy, dx, hy + 6, 8)

        # Streak
        if self.streak >= 2:
            sy = hy + 22
            pyxel.text(px, sy, f"STREAK x{self.streak}", ELEM_COLORS[self.last_element])

        # Log count
        ly = hy + (32 if self.streak >= 2 else 22)
        pyxel.text(px, ly, f"NEXT +{len(self.log_dice)} die", 6)

    def _draw_messages(self) -> None:
        """Draw floating messages."""
        for i, m in enumerate(self.messages):
            tx = W // 2 - len(m.text) * 2
            ty = H - 50 - i * 10
            pyxel.text(tx, ty, m.text, m.color)

    def _draw_particles(self) -> None:
        """Draw floating damage/heal particles."""
        for p in self.particles:
            alpha_fade = max(0, 1.0 - p.timer / p.life)
            if alpha_fade < 0.3:
                continue
            c = p.color
            tx = int(p.x) - len(p.text) * 2
            ty = int(p.y)
            pyxel.text(tx, ty, p.text, c)

    def _draw_end_screen(self) -> None:
        """Draw victory or defeat overlay."""
        is_victory = self.phase == Phase.VICTORY
        msg = "ALL CALAMITIES SEALED!" if is_victory else "SEALER DEFEATED"
        color = 11 if is_victory else 8

        # Darken background
        for y in range(0, H, 2):
            for x in range(0, W, 4):
                pyxel.pset(x, y, 1)

        pyxel.text(W // 2 - len(msg) * 2, H // 2 - 20, msg, color)
        pyxel.text(W // 2 - 32, H // 2, f"SCORE: {self.score}", 9)
        pyxel.text(W // 2 - 30, H // 2 + 12, f"TURNS: {self.turn}", 7)
        pyxel.text(W // 2 - 40, H // 2 + 24, f"WAVE: {self.wave + 1}/{len(ENEMY_WAVES)}", 6)

        # Blink "click to continue"
        if pyxel.frame_count % 40 < 30:
            pyxel.text(W // 2 - 38, H // 2 + 40, "CLICK TO PLAY AGAIN", 7)


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    CalamityDice()
