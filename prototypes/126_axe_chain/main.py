"""
Axe Chain - Axe Throwing with Color Chain Combo

When the player lands consecutive same-color axe hits, COMBO builds.
At COMBO>=5, the next axe becomes a SUPER AXE (rainbow, 3x multiplier).
The "Most Fun Moment": chaining same-color bullseye hits to activate SUPER AXE
and scoring massive points all at once.
"""
from __future__ import annotations

import math
import random as _random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


# === Enums ===

class Phase(Enum):
    TITLE = auto()
    AIMING = auto()
    FLYING = auto()
    SCORING = auto()
    GAME_OVER = auto()


# === Data Classes ===

@dataclass
class Axe:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    rotation: float = 0.0
    spin_speed: float = 0.15
    flying: bool = False
    landed: bool = False
    landed_ring: int = -1


@dataclass
class TargetRing:
    radius: float
    color: int
    points: int


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int = 7


# === Color Constants ===

RED = 8
GREEN = 3
DARK_BLUE = 5
YELLOW = 10
WHITE = 7
BLACK = 0
GRAY = 13
NAVY = 1
LIGHT_BLUE = 6
AXE_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]


class Game:
    """Core game logic.  Use Game.__new__(Game) + _pre_init_attributes for headless testing."""

    GRAVITY: float = 0.15
    MAX_POWER: float = 12.0
    AXES_PER_GAME: int = 15
    HEAT_PER_MISS: float = 15.0
    HEAT_COOL_PER_HIT: float = 5.0
    COMBO_FOR_SUPER: int = 5
    SUPER_DURATION: int = 1
    SCORING_DELAY: int = 45
    TARGET_CX: int = 160
    TARGET_CY: int = 90
    TARGET_MAX_RADIUS: int = 70
    AXE_SPAWN_X: int = 160
    AXE_SPAWN_Y: int = 220

    def __new__(cls, headless: bool = False) -> Game:
        obj = super().__new__(cls)
        obj._headless = headless
        return obj

    def _pre_init_attributes(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.best_ring: int = -1
        self.axes_thrown: int = 0
        self.heat: float = 0.0
        self.super_active: bool = False
        self.super_remaining: int = 0
        self.axe: Axe = Axe(
            x=float(self.AXE_SPAWN_X), y=float(self.AXE_SPAWN_Y),
            vx=0.0, vy=0.0, color=RED,
        )
        self.target_rings: list[TargetRing] = [
            TargetRing(70.0, RED, 10),      # outer
            TargetRing(52.5, GREEN, 25),    # mid-outer
            TargetRing(35.0, DARK_BLUE, 50),  # mid-inner
            TargetRing(17.5, YELLOW, 100),  # bullseye
        ]
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.drag_start_x: float = 0.0
        self.drag_start_y: float = 0.0
        self.drag_current_x: float = 0.0
        self.drag_current_y: float = 0.0
        self.dragging: bool = False
        self.scoring_timer: int = 0
        self.super_timer: int = 0
        self.colour_index: int = 0
        self.shake_frames: int = 0
        self.last_axe_color: int = -1
        self.rng: _random.Random = _random.Random()
        self.title_spin: float = 0.0

    def reset(self) -> None:
        self._pre_init_attributes()

    def start_game(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.best_ring = -1
        self.axes_thrown = 0
        self.heat = 0.0
        self.super_active = False
        self.super_remaining = 0
        self.last_axe_color = -1
        self.scoring_timer = 0
        self.shake_frames = 0
        self.colour_index = 0
        self.dragging = False
        self.particles.clear()
        self.floating_texts.clear()
        self._spawn_axe()
        self.phase = Phase.AIMING

    def set_seed(self, seed: int) -> None:
        self.rng = _random.Random(seed)

    # ------------------------------------------------------------------ #
    #  Axe spawning / aiming                                              #
    # ------------------------------------------------------------------ #

    def _spawn_axe(self) -> None:
        color = self._random_axe_color()
        self.axe = Axe(
            x=float(self.AXE_SPAWN_X),
            y=float(self.AXE_SPAWN_Y),
            vx=0.0, vy=0.0,
            color=color,
        )

    def _random_axe_color(self) -> int:
        return self.rng.choice(AXE_COLORS)

    def _start_aim(self, x: float, y: float) -> None:
        if self.phase != Phase.AIMING:
            return
        dx = x - self.axe.x
        dy = y - self.axe.y
        if abs(dx) < 20 and abs(dy) < 20:
            self.dragging = True
            self.drag_start_x = x
            self.drag_start_y = y
            self.drag_current_x = x
            self.drag_current_y = y

    def _update_aim(self, x: float, y: float) -> None:
        if self.dragging:
            self.drag_current_x = x
            self.drag_current_y = y

    def _release_aim(self, x: float, y: float) -> None:
        if not self.dragging or self.phase != Phase.AIMING:
            return
        self.dragging = False
        dx = self.axe.x - x
        dy = self.axe.y - y
        power = math.sqrt(dx * dx + dy * dy)
        if power <= 0:
            self.axe.vx = 0.0
            self.axe.vy = 0.0
        elif power > self.MAX_POWER:
            scale = self.MAX_POWER / power
            self.axe.vx = dx * scale
            self.axe.vy = dy * scale
        else:
            self.axe.vx = dx
            self.axe.vy = dy
        self.axe.flying = True
        self.last_axe_color = self.axe.color
        self.axes_thrown += 1
        self.phase = Phase.FLYING

    # ------------------------------------------------------------------ #
    #  Physics                                                            #
    # ------------------------------------------------------------------ #

    def _update_axe(self) -> None:
        if not self.axe.flying:
            return
        self.axe.vy += self.GRAVITY
        self.axe.x += self.axe.vx
        self.axe.y += self.axe.vy
        self.axe.rotation += self.axe.spin_speed
        # Off-screen check
        if (
            self.axe.x < -50
            or self.axe.x > 370
            or self.axe.y < -50
            or self.axe.y > 290
        ):
            self.axe.flying = False
            self._handle_miss()
            return
        # Target collision
        ring = self._check_target_hit()
        if ring >= 0:
            self.axe.flying = False
            self.axe.landed = True
            self.axe.landed_ring = ring
            self._resolve_hit(ring)

    def _check_target_hit(self) -> int:
        dist = self._ring_center_distance(self.axe.x, self.axe.y)
        # Check inner rings first so that boundary overlaps favour inner ring
        for i in range(len(self.target_rings) - 1, -1, -1):
            if dist <= self.target_rings[i].radius:
                return i
        return -1

    def _ring_center_distance(self, x: float, y: float) -> float:
        dx = x - self.TARGET_CX
        dy = y - self.TARGET_CY
        return math.sqrt(dx * dx + dy * dy)

    # ------------------------------------------------------------------ #
    #  Hit / miss resolution                                              #
    # ------------------------------------------------------------------ #

    def _handle_miss(self) -> None:
        self.combo = 0
        self._apply_heat(self.HEAT_PER_MISS)
        self.phase = Phase.SCORING
        self.scoring_timer = self.SCORING_DELAY
        self._add_floating_text(self.axe.x, max(0.0, self.axe.y), "MISS", RED)

    def _resolve_hit(self, ring_index: int) -> None:
        ring = self.target_rings[ring_index]
        base_points = ring.points
        was_super = self.super_active and self.super_remaining > 0
        if ring_index > self.best_ring:
            self.best_ring = ring_index
        if was_super:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            points = int(base_points * (1 + self.combo) * 3)
            self._add_score(points)
            self._spawn_particles(self.axe.x, self.axe.y, YELLOW, 15)
            self._add_floating_text(self.axe.x, self.axe.y - 10, f"+{points}", YELLOW)
            self._add_floating_text(self.axe.x, self.axe.y - 22, "SUPER!", YELLOW)
            self.shake_frames = 8
            self.combo = 0
            self.super_remaining -= 1
            if self.super_remaining <= 0:
                self.super_active = False
        elif self.axe.color == ring.color:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            points = int(base_points * (1 + self.combo))
            self._add_score(points)
            self._spawn_particles(self.axe.x, self.axe.y, self.axe.color, 8)
            self._add_floating_text(self.axe.x, self.axe.y - 10, f"+{points}", WHITE)
        else:
            self.combo = 0
            points = base_points
            self._add_score(points)
            self._spawn_particles(self.axe.x, self.axe.y, GRAY, 4)
            self._add_floating_text(self.axe.x, self.axe.y - 10, f"+{points}", GRAY)
        self._apply_heat(-self.HEAT_COOL_PER_HIT)
        self.phase = Phase.SCORING
        self.scoring_timer = self.SCORING_DELAY
        if not was_super and self._check_super_activation():
            self.super_active = True
            self.super_remaining = self.SUPER_DURATION

    def _check_super_activation(self) -> bool:
        return self.combo >= self.COMBO_FOR_SUPER

    # ------------------------------------------------------------------ #
    #  Score / heat helpers                                               #
    # ------------------------------------------------------------------ #

    def _add_score(self, points: int) -> None:
        self.score += points

    def _apply_heat(self, delta: float) -> None:
        self.heat = max(0.0, min(100.0, self.heat + delta))

    # ------------------------------------------------------------------ #
    #  Particles & floating text                                          #
    # ------------------------------------------------------------------ #

    def _spawn_particles(
        self, x: float, y: float, color: int, count: int
    ) -> None:
        for _ in range(count):
            vx = (self.rng.random() - 0.5) * 3.0
            vy = (self.rng.random() - 0.5) * 3.0 - 1.0
            life = self.rng.randint(8, 20)
            self.particles.append(Particle(x, y, vx, vy, life, color))

    def _add_floating_text(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        self.floating_texts.append(FloatingText(x, y, text, 25, color))

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y -= 1.0
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    def _update_scoring(self) -> None:
        if self.phase != Phase.SCORING:
            return
        self.scoring_timer -= 1
        if self.scoring_timer <= 0:
            if self.heat >= 100.0 or self.axes_thrown >= self.AXES_PER_GAME:
                self.phase = Phase.GAME_OVER
            else:
                self._spawn_axe()
                self.phase = Phase.AIMING

    # ------------------------------------------------------------------ #
    #  Arc preview helper                                                 #
    # ------------------------------------------------------------------ #

    def _compute_throw_velocity(self) -> tuple[float, float]:
        """Return (vx, vy) for the current drag state."""
        if not self.dragging:
            return (0.0, 0.0)
        dx = self.axe.x - self.drag_current_x
        dy = self.axe.y - self.drag_current_y
        power = math.sqrt(dx * dx + dy * dy)
        if power <= 0:
            return (0.0, 0.0)
        if power > self.MAX_POWER:
            scale = self.MAX_POWER / power
            dx *= scale
            dy *= scale
        return (dx, dy)

    # ================================================================== #
    #  Pyxel update / draw                                                #
    # ================================================================== #

    def update(self) -> None:
        self._update_particles()
        self._update_floating_texts()
        # Screen shake
        if self.shake_frames > 0:
            self.shake_frames -= 1
            offset = 2 if (self.shake_frames // 2) % 2 == 0 else -2
            pyxel.camera(offset, 0)
        else:
            pyxel.camera(0, 0)
        # Phase machine
        if self.phase == Phase.TITLE:
            self.title_spin += 0.05
            if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.start_game()
        elif self.phase == Phase.AIMING:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self._start_aim(float(pyxel.mouse_x), float(pyxel.mouse_y))
            if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT) and self.dragging:
                self._update_aim(float(pyxel.mouse_x), float(pyxel.mouse_y))
            if pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT):
                self._release_aim(float(pyxel.mouse_x), float(pyxel.mouse_y))
        elif self.phase == Phase.FLYING:
            self._update_axe()
        elif self.phase == Phase.SCORING:
            self._update_scoring()
            if self.super_active:
                self.super_timer += 1
                if self.super_timer % 3 == 0:
                    self.colour_index = (self.colour_index + 1) % 4
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.AIMING, Phase.FLYING, Phase.SCORING):
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    # ------------------------------------------------------------------ #
    #  Title screen                                                       #
    # ------------------------------------------------------------------ #

    def _draw_title(self) -> None:
        title = "AXE CHAIN"
        pyxel.text(160 - len(title) * 4 // 2, 50, title, WHITE)
        # Spinning axe icon
        cx, cy = 160.0, 95.0
        c = math.cos(self.title_spin)
        s = math.sin(self.title_spin)
        pts = [(-10.0, 10.0), (10.0, 10.0), (0.0, -14.0)]
        rx = [(cx + px * c - py * s) for px, py in pts]
        ry = [(cy + px * s + py * c) for px, py in pts]
        pyxel.tri(rx[0], ry[0], rx[1], ry[1], rx[2], ry[2], YELLOW)
        # Instructions
        lines = [
            "Click & drag to throw",
            "Match colors for COMBO!",
            "COMBO x5 = SUPER AXE! (3x score)",
            "",
            "Press R or click to start",
        ]
        for i, line in enumerate(lines):
            pyxel.text(160 - len(line) * 4 // 2, 120 + i * 14, line, LIGHT_BLUE if i < 2 else WHITE)

    # ------------------------------------------------------------------ #
    #  Game screen                                                        #
    # ------------------------------------------------------------------ #

    def _draw_game(self) -> None:
        self._draw_target()
        self._draw_axe()
        # Drag indicator
        if self.dragging and self.phase == Phase.AIMING:
            pyxel.line(
                int(self.axe.x), int(self.axe.y),
                int(self.drag_current_x), int(self.drag_current_y),
                WHITE,
            )
            self._draw_arc_preview()
        # Particles
        for p in self.particles:
            alpha = p.life / 20.0
            if alpha > 0.2:
                pyxel.pset(int(p.x), int(p.y), p.color)
        # Floating texts
        for ft in self.floating_texts:
            alpha = ft.life / 25.0
            col = ft.color if alpha > 0.3 else GRAY
            tx = int(ft.x - len(ft.text) * 2)
            pyxel.text(tx, int(ft.y), ft.text, col)
        # HUD
        self._draw_hud()

    def _draw_target(self) -> None:
        cx, cy = self.TARGET_CX, self.TARGET_CY
        rings: list[tuple[float, int]] = [
            (70.0, RED),
            (52.5, GREEN),
            (35.0, DARK_BLUE),
            (17.5, YELLOW),
        ]
        for radius, color in rings:
            pyxel.circ(cx, cy, int(radius), color)
            pyxel.circb(cx, cy, int(radius), BLACK)

    def _draw_axe(self) -> None:
        if self.axe.landed:
            return
        ax, ay = self.axe.x, self.axe.y
        rot = self.axe.rotation
        c = math.cos(rot)
        s = math.sin(rot)
        size = 8.0
        pts = [(-size, size), (size, size), (0.0, -size)]
        rx = [ax + px * c - py * s for px, py in pts]
        ry = [ay + px * s + py * c for px, py in pts]
        color = self.axe.color
        if (
            self.super_active
            and self.phase in (Phase.AIMING, Phase.FLYING)
            and self.super_remaining > 0
        ):
            super_colors = [RED, GREEN, DARK_BLUE, YELLOW]
            color = super_colors[self.colour_index % 4]
        pyxel.tri(rx[0], ry[0], rx[1], ry[1], rx[2], ry[2], color)

    def _draw_arc_preview(self) -> None:
        vx, vy = self._compute_throw_velocity()
        if vx == 0.0 and vy == 0.0:
            return
        px, py = float(self.axe.x), float(self.axe.y)
        pvx, pvy = vx, vy
        for _i in range(40):
            pvx = vx  # gravity only affects vy (vx stays constant for preview)
            px += pvx
            py += pvy
            pvy += self.GRAVITY
            if 0 <= px < 320 and 0 <= py < 240:
                if _i % 2 == 0:
                    pyxel.pset(int(px), int(py), GRAY)

    def _draw_hud(self) -> None:
        # Score (top-left)
        pyxel.text(4, 2, f"SCORE {self.score}", WHITE)
        # Combo (top-right)
        combo_str = f"COMBO {self.combo}"
        combo_col = YELLOW if self.combo >= self.COMBO_FOR_SUPER else WHITE
        pyxel.text(320 - len(combo_str) * 4 - 4, 2, combo_str, combo_col)
        # Axes remaining
        remaining = self.AXES_PER_GAME - self.axes_thrown
        pyxel.text(4, 230, f"Axes: {remaining}", WHITE)
        # Heat bar
        self._draw_heat_bar()
        # SUPER indicator
        if self.super_active and self.super_remaining > 0:
            super_colors = [RED, GREEN, DARK_BLUE, YELLOW]
            c = super_colors[self.colour_index % 4]
            pyxel.text(130, 2, "SUPER READY", c)

    def _draw_heat_bar(self) -> None:
        x, y = 280, 228
        w, h = 36, 6
        pyxel.rect(x, y, w, h, NAVY)
        fill_w = int(w * self.heat / 100.0)
        if self.heat < 33:
            color = GREEN
        elif self.heat < 67:
            color = YELLOW
        else:
            color = RED
        if fill_w > 0:
            pyxel.rect(x, y, fill_w, h, color)
        pyxel.text(x, y + 8, "HEAT", WHITE)

    # ------------------------------------------------------------------ #
    #  Game Over screen                                                   #
    # ------------------------------------------------------------------ #

    def _draw_game_over(self) -> None:
        pyxel.text(160 - len("GAME OVER") * 4 // 2, 60, "GAME OVER", RED)
        pyxel.text(100, 90, f"SCORE      {self.score}", WHITE)
        pyxel.text(100, 105, f"MAX COMBO  {self.max_combo}", WHITE)
        ring_names = ["Outer", "Mid-Outer", "Mid-Inner", "Bullseye"]
        best = ring_names[self.best_ring] if self.best_ring >= 0 else "None"
        pyxel.text(100, 120, f"BEST RING  {best}", WHITE)
        pyxel.text(160 - len("Press R to retry") * 4 // 2, 160, "Press R to retry", LIGHT_BLUE)


# ====================================================================== #
#  App entry point                                                       #
# ====================================================================== #

class App:
    def __init__(self) -> None:
        pyxel.init(320, 240, title="Axe Chain")
        self.game = Game(headless=False)
        self.game._pre_init_attributes()
        self.game.reset()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        self.game.update()

    def draw(self) -> None:
        self.game.draw()


if __name__ == "__main__":
    App()
