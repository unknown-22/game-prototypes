"""
BELT SURGE - Conveyor belt color-match chain reaction game
==========================================================
Items of 4 colors flow left->right on a belt.
Position the scanner gate, match its color to tag passing items.
Consecutive same-color tags build COMBO chains.
COMBO >= 5 triggers SURGE: all tagged items burst into particles for massive score.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel

# Color constants (raw ints, Pyxel 16-color palette)
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

# Item colors
ITEM_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
COLOR_NAMES: list[str] = ["RED", "GREEN", "BLUE", "YELLOW"]

# Screen
SCREEN_W = 320
SCREEN_H = 240
FPS = 60

# Layout
BELT_Y = 160
ITEM_W = 20
ITEM_H = 16
GATE_W = 4
GATE_H = 240

# Game constants
MAX_HEAT = 100
SURGE_THRESHOLD = 5
BASE_SPEED = 1.0
SPEED_INCREMENT = 0.05
SPEED_INCREMENT_INTERVAL = 900  # frames (15 sec at 60fps)
ITEM_SPAWN_MIN = 40
ITEM_SPAWN_MAX = 90
SURGE_DURATION = 30  # frames
SHAKE_DURATION = 20  # frames
AUTO_CYCLE_SCORE = 300
INITIAL_GATE_X = 160
GATE_SPEED = 3
GATE_X_MIN = 10
GATE_X_MAX = 310

# Key mapping: 1=RED(0), 2=GREEN(1), 3=BLUE(2), 4=YELLOW(3)
KEY_TO_COLOR: dict[int, int] = {
    pyxel.KEY_1: 0,
    pyxel.KEY_2: 1,
    pyxel.KEY_3: 2,
    pyxel.KEY_4: 3,
}


@dataclass
class Item:
    x: float
    y: float
    color: int
    color_idx: int = 0
    tagged: bool = False
    alive: bool = True


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int
    max_life: int = 20


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    SURGE_ANIM = auto()
    GAME_OVER = auto()


class Game:
    SCREEN_W: ClassVar[int] = SCREEN_W
    SCREEN_H: ClassVar[int] = SCREEN_H
    MAX_HEAT: ClassVar[int] = MAX_HEAT
    SURGE_THRESHOLD: ClassVar[int] = SURGE_THRESHOLD
    BASE_SPEED: ClassVar[float] = BASE_SPEED
    SPEED_INCREMENT: ClassVar[float] = SPEED_INCREMENT
    SPEED_INCREMENT_INTERVAL: ClassVar[int] = SPEED_INCREMENT_INTERVAL
    ITEM_SPAWN_MIN: ClassVar[int] = ITEM_SPAWN_MIN
    ITEM_SPAWN_MAX: ClassVar[int] = ITEM_SPAWN_MAX
    SURGE_DURATION: ClassVar[int] = SURGE_DURATION
    SHAKE_DURATION: ClassVar[int] = SHAKE_DURATION
    AUTO_CYCLE_SCORE: ClassVar[int] = AUTO_CYCLE_SCORE

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="BELT SURGE", fps=FPS, display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    # ══════════════════════════════════════════════════
    # State initialization (testable)
    # ══════════════════════════════════════════════════
    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.gate_x: float = INITIAL_GATE_X
        self.gate_color: int = 0  # 0-3 index
        self.items: list[Item] = []
        self.particles: list[Particle] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.belt_speed: float = self.BASE_SPEED
        self._spawn_timer: int = 0
        self._surge_timer: int = 0
        self._shake_timer: int = 0
        self._shake_offset_x: int = 0
        self._shake_offset_y: int = 0
        self._surge_score_popup: int = 0
        self._surge_popup_timer: int = 0
        self._last_tagged_color_idx: int | None = None
        self._score_since_cycle: int = 0
        self._frame: int = 0
        self._passed_gate: set[int] = set()
        self._popup_texts: list[tuple[str, float, float, int, int]] = []
        self._rng: random.Random = random.Random()

    # ══════════════════════════════════════════════════
    # Core game logic (testable, no pyxel calls)
    # ══════════════════════════════════════════════════
    def _spawn_item(self, rng: random.Random | None = None) -> Item | None:
        """Spawn an item at left edge with random color."""
        if rng is None:
            rng = self._rng
        color_idx = rng.randint(0, len(ITEM_COLORS) - 1)
        return Item(
            x=float(-ITEM_W),
            y=float(BELT_Y - ITEM_H // 2),
            color=ITEM_COLORS[color_idx],
            color_idx=color_idx,
        )

    def _update_items(self) -> None:
        """Move items right, process gate passes, remove off-screen items."""
        for i, item in enumerate(self.items):
            if not item.alive:
                continue
            prev_x = item.x
            item.x += self.belt_speed

            # Check gate pass: item crossed gate_x this frame
            if not item.tagged and prev_x < self.gate_x and item.x >= self.gate_x:
                self._handle_gate_pass(item)

            # Untagged items reaching right edge
            if not item.tagged and item.x >= self.SCREEN_W:
                self.heat = min(self.MAX_HEAT, self.heat + 10)
                item.alive = False

        # Clean up dead items
        self.items = [it for it in self.items if it.alive]

    def _handle_gate_pass(self, item: Item) -> None:
        """Handle an item passing through the scanner gate."""
        if item.color_idx == self.gate_color:
            # Match! Tag the item
            item.tagged = True

            # Combo logic
            if (
                self._last_tagged_color_idx is None
                or self._last_tagged_color_idx == item.color_idx
            ):
                self.combo += 1
            else:
                self.combo = 1
            self._last_tagged_color_idx = item.color_idx

            if self.combo > self.max_combo:
                self.max_combo = self.combo

            # Score: base 10 * (1 + item_x/SCREEN_W) — risk/reward
            earned = int(10 * (1.0 + item.x / self.SCREEN_W))
            self.score += earned
            self._score_since_cycle += earned

            # Auto color cycle check
            if self._score_since_cycle >= self.AUTO_CYCLE_SCORE:
                self._score_since_cycle -= self.AUTO_CYCLE_SCORE
                self.gate_color = (self.gate_color + 1) % len(ITEM_COLORS)
                self._popup_texts.append(
                    (f"COLOR CYCLE! -> {COLOR_NAMES[self.gate_color]}",
                     float(self.SCREEN_W // 2), float(BELT_Y - 40), ITEM_COLORS[self.gate_color], 45)
                )

            # Surge check
            if self.combo >= self.SURGE_THRESHOLD:
                self._handle_surge()

            # Spawn particles for tag
            self._spawn_particles(item.x, item.y, ITEM_COLORS[item.color_idx], 4)
            self._popup_texts.append(
                (f"+{earned}", item.x, item.y - 10, WHITE, 20)
            )
        else:
            # No match: combo resets
            if self._last_tagged_color_idx is not None:
                self._last_tagged_color_idx = None
            if self.combo > 0:
                self.combo = 0

    def _handle_surge(self) -> None:
        """Trigger SURGE: all tagged items burst into particles."""
        tagged_items = [it for it in self.items if it.tagged and it.alive]
        tagged_count = len(tagged_items)
        if tagged_count == 0:
            return

        # Score bonus
        bonus = int(self.combo * 100 * (1 + tagged_count * 0.5))
        self.score += bonus
        self._score_since_cycle += bonus
        self._surge_score_popup = bonus
        self._surge_popup_timer = 45

        # Spawn particles for each tagged item
        for item in tagged_items:
            self._spawn_particles(
                item.x, item.y, ITEM_COLORS[item.color_idx], 10
            )
            item.alive = False

        # Enter surge animation phase
        self.phase = Phase.SURGE_ANIM
        self._surge_timer = self.SURGE_DURATION
        self._shake_timer = self.SHAKE_DURATION

        # Surge popup
        self._popup_texts.append(
            (f"SURGE! +{bonus}",
             float(self.SCREEN_W // 2), float(self.SCREEN_H // 2), YELLOW, 45)
        )

    def _update_heat(self) -> float:
        """Return current heat ratio for display."""
        return min(1.0, self.heat / self.MAX_HEAT)

    def _update_difficulty(self) -> None:
        """Increase belt speed every SPEED_INCREMENT_INTERVAL frames."""
        self._frame += 1
        if self._frame % self.SPEED_INCREMENT_INTERVAL == 0:
            self.belt_speed += self.SPEED_INCREMENT

    def _spawn_particles(
        self, x: float, y: float, color: int, count: int
    ) -> None:
        """Spawn particles around a point."""
        for _ in range(count):
            angle = self._rng.uniform(0, math.tau)
            speed = self._rng.uniform(1.0, 3.5)
            life = self._rng.randint(10, 25)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed - 1.0,
                    color=color,
                    life=life,
                    max_life=life,
                )
            )

    def _update_particles(self) -> None:
        """Move particles, decrement life, remove dead."""
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_popups(self) -> None:
        """Decrement popup text lifetimes, remove expired."""
        self._popup_texts = [
            (text, x, y, col, life - 1)
            for text, x, y, col, life in self._popup_texts
            if life > 0
        ]

    def _get_spawn_interval(self) -> int:
        """Get randomized spawn interval based on difficulty."""
        reduction = int(self._frame / self.SPEED_INCREMENT_INTERVAL) * 5
        base = max(self.ITEM_SPAWN_MIN, self.ITEM_SPAWN_MAX - reduction)
        return self._rng.randint(max(self.ITEM_SPAWN_MIN, base - 10), base)

    def _check_game_over(self) -> bool:
        """Check if heat >= MAX_HEAT."""
        if self.heat >= self.MAX_HEAT:
            self.phase = Phase.GAME_OVER
            self._shake_timer = self.SHAKE_DURATION
            return True
        return False

    # ══════════════════════════════════════════════════
    # Update (pyxel-bound)
    # ══════════════════════════════════════════════════
    def update(self) -> None:
        # Shake timer tick
        if self._shake_timer > 0:
            self._shake_timer -= 1

        # Popup timer tick
        if self._surge_popup_timer > 0:
            self._surge_popup_timer -= 1

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.SURGE_ANIM:
            self._update_surge_anim()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._start_game()

    def _start_game(self) -> None:
        self.phase = Phase.PLAYING
        self.gate_x = INITIAL_GATE_X
        self.gate_color = 0
        self.items.clear()
        self.particles.clear()
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.belt_speed = self.BASE_SPEED
        self._spawn_timer = 0
        self._surge_timer = 0
        self._shake_timer = 0
        self._surge_score_popup = 0
        self._surge_popup_timer = 0
        self._last_tagged_color_idx = None
        self._score_since_cycle = 0
        self._frame = 0
        self._passed_gate.clear()
        self._popup_texts.clear()
        self._rng = random.Random()

    def _update_playing(self) -> None:
        # Gate movement (continuous)
        if pyxel.btn(pyxel.KEY_LEFT):
            self.gate_x = max(GATE_X_MIN, self.gate_x - GATE_SPEED)
        if pyxel.btn(pyxel.KEY_RIGHT):
            self.gate_x = min(GATE_X_MAX, self.gate_x + GATE_SPEED)

        # Gate color change (single press)
        for key, color_idx in KEY_TO_COLOR.items():
            if pyxel.btnp(key):
                self.gate_color = color_idx

        # Difficulty scaling
        self._update_difficulty()

        # Spawn items
        if self._spawn_timer <= 0:
            item = self._spawn_item()
            if item is not None:
                self.items.append(item)
            self._spawn_timer = self._get_spawn_interval()
        else:
            self._spawn_timer -= 1

        # Update items
        self._update_items()

        # Update particles
        self._update_particles()

        # Update popups
        self._update_popups()

        # Check game over
        self._check_game_over()

    def _update_surge_anim(self) -> None:
        """Update during SURGE animation phase."""
        # Still update particles
        self._update_particles()

        # Update popups
        self._update_popups()

        # Shake
        if self._shake_timer > 0:
            self._shake_offset_x = self._rng.randint(-4, 4)
            self._shake_offset_y = self._rng.randint(-3, 3)
        else:
            self._shake_offset_x = 0
            self._shake_offset_y = 0

        # Surge timer
        self._surge_timer -= 1
        if self._surge_timer <= 0:
            # Reset combo after surge
            self.combo = 0
            self._last_tagged_color_idx = None
            self._shake_offset_x = 0
            self._shake_offset_y = 0
            self.phase = Phase.PLAYING

    def _update_game_over(self) -> None:
        # Shake decay
        if self._shake_timer > 0:
            self._shake_offset_x = self._rng.randint(-3, 3)
            self._shake_offset_y = self._rng.randint(-2, 2)
        else:
            self._shake_offset_x = 0
            self._shake_offset_y = 0

        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()

    # ══════════════════════════════════════════════════
    # Draw
    # ══════════════════════════════════════════════════
    def draw(self) -> None:
        shake_x = self._shake_offset_x
        shake_y = self._shake_offset_y

        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing(shake_x, shake_y)
        elif self.phase == Phase.SURGE_ANIM:
            self._draw_playing(shake_x, shake_y)
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over(shake_x, shake_y)

    def _draw_title(self) -> None:
        # Title
        title = "BELT SURGE"
        tx = self.SCREEN_W // 2 - len(title) * 4 // 2
        pyxel.text(tx, 30, title, WHITE)

        # Subtitle
        subtitle = "Color-Match Chain Reaction"
        sx = self.SCREEN_W // 2 - len(subtitle) * 4 // 2
        pyxel.text(sx, 46, subtitle, GRAY)

        # Instructions
        instructions = [
            "Match gate color to tag passing items",
            "Consecutive same-color tags = COMBO",
            "COMBO >= 5 triggers SURGE!",
            "Items reaching right = +HEAT",
            "HEAT >= 100 = GAME OVER",
        ]
        for i, instr in enumerate(instructions):
            pyxel.text(20, 75 + i * 14, instr, GRAY)

        # Controls
        controls = [
            "LEFT/RIGHT - Move gate",
            "1/2/3/4   - Change gate color",
            "SPACE     - Start / Retry",
        ]
        for i, ctrl in enumerate(controls):
            pyxel.text(20, 155 + i * 14, ctrl, WHITE)

        # Key preview
        key_x = 180
        for i in range(4):
            pyxel.text(key_x, 120 + i * 16, f"[{i + 1}]", WHITE)
            pyxel.rect(key_x + 16, 120 + i * 16, 12, 10, ITEM_COLORS[i])
            pyxel.text(key_x + 32, 120 + i * 16, COLOR_NAMES[i], ITEM_COLORS[i])

        # Belt preview
        pyxel.line(10, BELT_Y + 20, self.SCREEN_W - 10, BELT_Y + 20, GRAY)
        for bx in range(10, self.SCREEN_W - 10, 40):
            pyxel.text(bx, BELT_Y + 24, ">", GRAY)

        # Start prompt
        prompt = "Press SPACE to start"
        px = self.SCREEN_W // 2 - len(prompt) * 4 // 2
        pyxel.text(px, 220, prompt, WHITE)

    def _draw_playing(self, shake_x: int, shake_y: int) -> None:
        # Belt line
        by = BELT_Y + shake_y
        pyxel.line(0 + shake_x, by, self.SCREEN_W + shake_x, by, GRAY)
        # Belt arrows
        for ax in range(0, self.SCREEN_W, 40):
            pyxel.text(ax + shake_x + 10, by + 2, ">", GRAY)

        # Danger zone (right edge)
        danger_x = self.SCREEN_W - 10
        pyxel.rect(danger_x + shake_x, 0 + shake_y, 10, self.SCREEN_H, RED)

        # Items
        for item in self.items:
            if not item.alive:
                continue
            ix = int(item.x) + shake_x
            iy = int(item.y) + shake_y

            if item.tagged:
                # Glowing outline
                glow_col = WHITE if (pyxel.frame_count // 8) % 2 == 0 else ITEM_COLORS[item.color_idx]
                pyxel.rectb(ix, iy, ITEM_W, ITEM_H, glow_col)
            else:
                pyxel.rectb(ix, iy, ITEM_W, ITEM_H, GRAY)

            # Fill
            pyxel.rect(ix + 1, iy + 1, ITEM_W - 2, ITEM_H - 2, ITEM_COLORS[item.color_idx])

        # Gate
        gx = int(self.gate_x) + shake_x
        gate_col = ITEM_COLORS[self.gate_color]
        # Semi-transparent effect: alternating pixel pattern
        for gy in range(0, self.SCREEN_H, 4):
            pyxel.rect(gx, gy + shake_y, 2, 2, gate_col)
        # Center indicator on belt
        pyxel.circ(gx + 1, BELT_Y + shake_y, 4, gate_col)

        # Particles
        for p in self.particles:
            alpha = max(0.1, p.life / p.max_life)
            size = max(1, int(3 * alpha))
            col = p.color if p.life > p.max_life // 3 else GRAY
            px = int(p.x) + shake_x
            py = int(p.y) + shake_y
            pyxel.rect(px, py, size, size, col)

        # Popup texts
        for text, x, y, col, life in self._popup_texts:
            tx = int(x) + shake_x - len(text) * 2
            ty = int(y) + shake_y
            if life > 30 or (pyxel.frame_count // 4) % 2 == 0:
                pyxel.text(tx, ty, text, col)

        # HUD
        self._draw_hud(shake_x, shake_y)

        # Surge popup
        if self._surge_popup_timer > 0:
            popup_text = f"+{self._surge_score_popup}"
            px = self.SCREEN_W // 2 - len(popup_text) * 4 // 2 + shake_x
            popup_col = YELLOW if (pyxel.frame_count // 3) % 2 == 0 else WHITE
            pyxel.text(px, self.SCREEN_H // 2 - 10 + shake_y, popup_text, popup_col)

    def _draw_hud(self, shake_x: int, shake_y: int) -> None:
        # Score
        pyxel.text(4 + shake_x, 4 + shake_y, f"SCORE: {self.score}", WHITE)

        # Combo
        if self.combo >= 2:
            combo_text = f"COMBO x{self.combo}"
            if self.combo >= self.SURGE_THRESHOLD:
                combo_col = YELLOW if (pyxel.frame_count // 8) % 2 == 0 else WHITE
            elif self.combo >= 3:
                combo_col = ORANGE
            else:
                combo_col = WHITE
            cx = self.SCREEN_W // 2 - len(combo_text) * 2 + shake_x
            pyxel.text(cx, 4 + shake_y, combo_text, combo_col)

        # Gate color indicator
        gate_label = f"GATE: {COLOR_NAMES[self.gate_color]}"
        pyxel.text(self.SCREEN_W - 60 + shake_x, 4 + shake_y, gate_label, ITEM_COLORS[self.gate_color])

        # Heat bar
        bar_x = 4 + shake_x
        bar_y = 16 + shake_y
        bar_w = self.SCREEN_W - 8
        bar_h = 6

        pyxel.rect(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2, BLACK)
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, DARK_BLUE)

        heat_pct = min(1.0, self.heat / self.MAX_HEAT)
        fill_w = int(bar_w * heat_pct)
        if fill_w > 0:
            if heat_pct < 0.5:
                heat_col = GREEN
            elif heat_pct < 0.8:
                heat_col = ORANGE
            else:
                heat_col = RED
            pyxel.rect(bar_x, bar_y, fill_w, bar_h, heat_col)

        pyxel.text(bar_x, bar_y + bar_h + 2, f"HEAT {int(self.heat)}/{self.MAX_HEAT}", GRAY)

        # Speed
        speed_text = f"SPD: {self.belt_speed:.1f}"
        pyxel.text(self.SCREEN_W - 60 + shake_x, bar_y + bar_h + 2, speed_text, GRAY)

        # Max combo
        pyxel.text(bar_x + 120, bar_y + bar_h + 2, f"MAX COMBO: {self.max_combo}", GRAY)

    def _draw_game_over(self, shake_x: int, shake_y: int) -> None:
        # Title
        title = "BELT OVERHEAT"
        tx = self.SCREEN_W // 2 - len(title) * 4 // 2 + shake_x
        pyxel.text(tx, 40 + shake_y, title, RED)

        # Stats
        score_text = f"FINAL SCORE: {self.score}"
        sx = self.SCREEN_W // 2 - len(score_text) * 4 // 2 + shake_x
        pyxel.text(sx, 70 + shake_y, score_text, WHITE)

        combo_text = f"MAX COMBO: {self.max_combo}"
        cx = self.SCREEN_W // 2 - len(combo_text) * 4 // 2 + shake_x
        pyxel.text(cx, 90 + shake_y, combo_text, WHITE)

        heat_text = f"FINAL HEAT: {int(self.heat)}"
        hx = self.SCREEN_W // 2 - len(heat_text) * 4 // 2 + shake_x
        pyxel.text(hx, 110 + shake_y, heat_text, GRAY)

        speed_text = f"BELT SPEED: {self.belt_speed:.1f}"
        spx = self.SCREEN_W // 2 - len(speed_text) * 4 // 2 + shake_x
        pyxel.text(spx, 130 + shake_y, speed_text, GRAY)

        # Surge indicator
        if self.max_combo >= self.SURGE_THRESHOLD:
            surge_msg = "SURGE ACTIVATED!"
            smx = self.SCREEN_W // 2 - len(surge_msg) * 4 // 2 + shake_x
            pyxel.text(smx, 150 + shake_y, surge_msg, YELLOW)

        # Retry prompt
        retry = "Press SPACE to retry"
        rx = self.SCREEN_W // 2 - len(retry) * 4 // 2 + shake_x
        pyxel.text(rx, 200 + shake_y, retry, WHITE)


if __name__ == "__main__":
    Game()
