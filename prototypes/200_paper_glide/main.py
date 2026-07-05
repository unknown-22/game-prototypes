from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
import pyxel

# --- Color Constants ---
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

# --- Enums ---


class Phase(Enum):
    TITLE = auto()
    AIMING = auto()
    FLYING = auto()
    GAME_OVER = auto()


# --- Data Classes ---


@dataclass
class Ring:
    x: int
    y: int
    color: int
    active: bool = True


@dataclass
class Plane:
    x: float
    y: float
    vx: float
    vy: float
    alive: bool = True
    super_timer: int = 0
    rainbow_phase: float = 0.0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class GhostPoint:
    x: float
    y: float


RAINBOW_COLORS = [RED, ORANGE, YELLOW, GREEN, CYAN, LIGHT_BLUE, PURPLE, PINK]


# --- Game ---


class Game:
    # Class-level constants
    RING_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
    GRAVITY: float = 0.15
    DRAG: float = 0.995
    MAX_POWER: float = 8.0
    RING_COUNT: int = 5
    HEAT_MAX: float = 100.0
    HEAT_MISMATCH: float = 10.0
    HEAT_MISS: float = 5.0
    HEAT_DECAY: float = 0.02
    SUPER_DURATION: int = 300
    COMBO_SUPER: int = 4
    TIMER_FRAMES: int = 1800
    LAUNCH_X: int = 40
    LAUNCH_Y: int = 120

    # Instance attribute type annotations (for type checker)
    phase: Phase
    score: int
    combo: int
    max_combo: int
    heat: float
    timer: int
    game_over: bool
    plane: Plane
    rings: list[Ring]
    particles: list[Particle]
    ghost_trail: list[GhostPoint]
    ghost_active: bool
    aim_start_x: int
    aim_start_y: int
    drag_power: float
    drag_angle: float
    throw_count: int
    super_active: bool
    super_timer: int
    combo_ring_color: int | None
    _flight_path: list[GhostPoint]
    _mouse_pressed: bool
    rng: random.Random

    def __new__(cls) -> Game:
        instance: Game = super().__new__(cls)
        # Pre-init ALL instance attributes (for headless testing)
        instance.phase = Phase.TITLE
        instance.score = 0
        instance.combo = 0
        instance.max_combo = 0
        instance.heat = 0.0
        instance.timer = cls.TIMER_FRAMES
        instance.game_over = False
        instance.plane = Plane(0, 0, 0, 0)
        instance.rings: list[Ring] = []
        instance.particles: list[Particle] = []
        instance.ghost_trail: list[GhostPoint] = []
        instance.ghost_active = False
        instance.aim_start_x = 0
        instance.aim_start_y = 0
        instance.drag_power = 0.0
        instance.drag_angle = 0.0
        instance.throw_count = 0
        instance.super_active = False
        instance.super_timer = 0
        instance.combo_ring_color: int | None = None
        instance._flight_path: list[GhostPoint] = []
        instance._mouse_pressed: bool = False
        instance.rng = random.Random()
        return instance

    def __init__(self) -> None:
        pyxel.init(320, 240, title="Paper Glide", display_scale=2)
        pyxel.mouse(True)
        pyxel.run(self._update, self._draw)

    # --- State Management ---

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = self.TIMER_FRAMES
        self.game_over = False
        self.plane = Plane(self.LAUNCH_X, self.LAUNCH_Y, 0, 0)
        self.rings = []
        self.particles = []
        self.ghost_trail = []
        self.ghost_active = False
        self.throw_count = 0
        self.super_active = False
        self.super_timer = 0
        self.combo_ring_color = None
        self._flight_path = []
        self._mouse_pressed = False
        self._spawn_rings()

    # --- Throwing ---

    def _throw_plane(self, angle: float, power: float) -> None:
        vx = math.cos(angle) * power
        vy = math.sin(angle) * power
        self.plane = Plane(self.LAUNCH_X, self.LAUNCH_Y, vx, vy)
        self.combo_ring_color = None
        self.throw_count += 1
        self._flight_path = []

    # --- Plane Physics & Collision ---

    def _update_plane(self) -> None:
        p = self.plane
        if not p.alive:
            return

        if pyxel.frame_count % 4 == 0:
            self._flight_path.append(GhostPoint(p.x, p.y))

        p.vy += self.GRAVITY
        p.vx *= self.DRAG
        p.vy *= self.DRAG
        p.x += p.vx
        p.y += p.vy

        if p.super_timer > 0:
            p.super_timer -= 1
            p.rainbow_phase += 0.1
            if p.super_timer == 0:
                self.super_active = False
                self.super_timer = 0

        for ring in self.rings:
            if ring.active and self._check_ring_collision(ring):
                ring.active = False
                self._handle_ring_pass(ring)

        if p.x < -20 or p.x > 340 or p.y < -20 or p.y > 260:
            p.alive = False
            self.heat += self.HEAT_MISS
            self._add_miss_particles(p.x, p.y)
            self.combo = 0
            self.combo_ring_color = None
            self.super_active = False
            self.super_timer = 0
            if self.heat >= self.HEAT_MAX:
                self.game_over = True
                self.phase = Phase.GAME_OVER
            else:
                self.ghost_trail = self._flight_path[:]
                self._flight_path = []
                self.phase = Phase.AIMING
                self._spawn_rings()

    def _check_ring_collision(self, ring: Ring) -> bool:
        dx = self.plane.x - ring.x
        dy = self.plane.y - ring.y
        dist = math.sqrt(dx * dx + dy * dy)
        return dist < 18

    def _handle_ring_pass(self, ring: Ring) -> None:
        p = self.plane
        is_match = p.super_timer > 0
        if not is_match:
            if self.combo_ring_color is None:
                is_match = True
                self.combo_ring_color = ring.color
            else:
                is_match = ring.color == self.combo_ring_color

        if is_match:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            base = 10
            multiplier = 1 + self.combo * 0.5
            pts = int(base * multiplier)
            if p.super_timer > 0:
                pts *= 3
            self.score += pts
            self._add_ring_pass_particles(ring.x, ring.y, ring.color)
            if self.combo >= self.COMBO_SUPER and not self.super_active:
                self._activate_super()
        else:
            self.combo = 0
            self.combo_ring_color = None
            self.heat += self.HEAT_MISMATCH
            self._add_mismatch_particles(ring.x, ring.y)
            if self.heat >= self.HEAT_MAX:
                self.game_over = True
                self.phase = Phase.GAME_OVER

    # --- Ring Spawning ---

    def _spawn_rings(self) -> None:
        self.rings = []
        x = 100
        count = self.rng.randint(4, 6)
        for _ in range(count):
            color = self.rng.choice(self.RING_COLORS)
            y = self.rng.randint(40, 200)
            self.rings.append(Ring(x, y, color))
            x += self.rng.randint(60, 100)
            if x > 290:
                break
        if len(self.rings) < 2:
            self._spawn_rings()

    # --- Particle System ---

    def _add_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            vx = self.rng.uniform(-2, 2)
            vy = self.rng.uniform(-2, 2)
            life = self.rng.randint(15, 30)
            self.particles.append(Particle(x, y, vx, vy, life, color))

    def _add_ring_pass_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(8):
            vx = self.rng.uniform(-2, 2)
            vy = self.rng.uniform(-2, 2)
            life = self.rng.randint(15, 30)
            self.particles.append(Particle(float(x), float(y), vx, vy, life, color))

    def _add_super_particles(self, x: float, y: float) -> None:
        for _ in range(20):
            color = self.rng.choice(RAINBOW_COLORS)
            vx = self.rng.uniform(-4, 4)
            vy = self.rng.uniform(-4, 4)
            life = self.rng.randint(20, 40)
            self.particles.append(Particle(x, y, vx, vy, life, color))

    def _add_miss_particles(self, x: float, y: float) -> None:
        for _ in range(4):
            vx = self.rng.uniform(-1, 1)
            vy = self.rng.uniform(-1, 1)
            life = self.rng.randint(10, 20)
            self.particles.append(Particle(x, y, vx, vy, life, ORANGE))

    def _add_mismatch_particles(self, x: float, y: float) -> None:
        for _ in range(4):
            vx = self.rng.uniform(-1, 1)
            vy = self.rng.uniform(-1, 1)
            life = self.rng.randint(10, 20)
            self.particles.append(Particle(float(x), float(y), vx, vy, life, ORANGE))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # --- SUPER GLIDE ---

    def _activate_super(self) -> None:
        self.super_active = True
        self.super_timer = self.SUPER_DURATION
        self.plane.super_timer = self.SUPER_DURATION
        self._add_super_particles(self.plane.x, self.plane.y)

    # --- HEAT ---

    def _update_heat(self) -> None:
        if self.game_over:
            return
        if self.heat >= self.HEAT_MAX:
            self.game_over = True
            self.phase = Phase.GAME_OVER
            return
        self.heat = max(0.0, self.heat - self.HEAT_DECAY)

    # --- Update ---

    def _update(self) -> None:
        if self.phase in (Phase.AIMING, Phase.FLYING) and not self.game_over:
            self.timer -= 1
            if self.timer <= 0:
                self.timer = 0
                self.phase = Phase.GAME_OVER
                return

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
                self.phase = Phase.AIMING
                self.timer = self.TIMER_FRAMES

        elif self.phase == Phase.AIMING:
            self._update_particles()
            self._update_heat()
            if self.game_over:
                return
            self._update_aiming_input()

        elif self.phase == Phase.FLYING:
            self._update_plane()
            self._update_particles()
            self._update_heat()

        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
                self.phase = Phase.TITLE

    def _update_aiming_input(self) -> None:
        if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
            if not self._mouse_pressed:
                self._mouse_pressed = True
                self.aim_start_x = pyxel.mouse_x
                self.aim_start_y = pyxel.mouse_y
            self._update_drag()
        else:
            if self._mouse_pressed:
                self._mouse_pressed = False
                self._on_mouse_release()

    def _update_drag(self) -> None:
        dx = pyxel.mouse_x - self.aim_start_x
        dy = pyxel.mouse_y - self.aim_start_y
        self.drag_power = min(math.sqrt(dx * dx + dy * dy) * 0.1, self.MAX_POWER)
        self.drag_angle = math.atan2(dy, dx)

    def _on_mouse_release(self) -> None:
        if self.drag_power > 0.5:
            self._throw_plane(self.drag_angle, self.drag_power)
            self.phase = Phase.FLYING
        self.drag_power = 0.0

    # --- Draw ---

    def _draw(self) -> None:
        pyxel.cls(NAVY)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.AIMING, Phase.FLYING):
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(110, 80, "PAPER GLIDE", WHITE)
        pyxel.text(70, 110, "Click-drag to aim & throw", GRAY)
        pyxel.text(75, 125, "Same-color rings = COMBO!", GRAY)
        pyxel.text(50, 140, "COMBO x4 = SUPER GLIDE (rainbow mode)", GRAY)
        pyxel.text(80, 160, "Avoid wrong colors & misses", GRAY)
        pyxel.text(110, 180, "60 seconds to score!", GRAY)
        if pyxel.frame_count % 60 < 30:
            pyxel.text(95, 210, "PRESS SPACE TO START", YELLOW)

    def _draw_game(self) -> None:
        self._draw_ghost_trail()
        self._draw_rings()
        self._draw_drag_indicator()
        self._draw_plane()
        self._draw_particles()
        self._draw_hud()

    def _draw_ghost_trail(self) -> None:
        trail = self.ghost_trail
        for gp in trail:
            pyxel.circ(int(gp.x), int(gp.y), 2, GRAY)

    def _draw_rings(self) -> None:
        for ring in self.rings:
            if not ring.active:
                continue
            if self.super_active:
                pyxel.circb(ring.x, ring.y, 16, YELLOW)
                pyxel.circb(ring.x, ring.y, 14, YELLOW)
            else:
                pyxel.circb(ring.x, ring.y, 16, ring.color)
                pyxel.circb(ring.x, ring.y, 14, ring.color)

    def _draw_drag_indicator(self) -> None:
        if self.phase == Phase.AIMING and self._mouse_pressed and self.drag_power > 0.5:
            pyxel.line(self.LAUNCH_X, self.LAUNCH_Y, pyxel.mouse_x, pyxel.mouse_y, WHITE)

    def _draw_plane(self) -> None:
        p = self.plane
        if self.phase == Phase.FLYING:
            color = self._plane_color()
            px, py = int(p.x), int(p.y)
            pyxel.tri(px + 10, py, px - 10, py - 4, px - 10, py + 4, color)
        else:
            pyxel.tri(
                self.LAUNCH_X + 10,
                self.LAUNCH_Y,
                self.LAUNCH_X - 10,
                self.LAUNCH_Y - 4,
                self.LAUNCH_X - 10,
                self.LAUNCH_Y + 4,
                WHITE,
            )

    def _plane_color(self) -> int:
        if self.super_active:
            idx = int(self.plane.rainbow_phase) % len(RAINBOW_COLORS)
            return RAINBOW_COLORS[idx]
        return WHITE

    def _draw_particles(self) -> None:
        for pt in self.particles:
            pyxel.pset(int(pt.x), int(pt.y), pt.color)

    def _draw_hud(self) -> None:
        pyxel.text(5, 5, f"SCORE: {self.score}", WHITE)
        pyxel.text(240, 5, f"TIME: {self.timer // 30}", WHITE)
        pyxel.text(5, 220, f"COMBO: {self.combo}", WHITE)
        heat_color = ORANGE if self.heat > 70 else WHITE
        pyxel.text(220, 220, f"HEAT: {int(self.heat)}/{int(self.HEAT_MAX)}", heat_color)
        if self.super_active:
            pyxel.text(130, 200, "SUPER GLIDE!", YELLOW)

    def _draw_game_over(self) -> None:
        pyxel.text(100, 70, "GAME OVER", RED)
        pyxel.text(90, 100, f"SCORE: {self.score}", WHITE)
        pyxel.text(80, 115, f"MAX COMBO: {self.max_combo}", WHITE)
        pyxel.text(80, 130, f"THROWS: {self.throw_count}", WHITE)
        if pyxel.frame_count % 60 < 30:
            pyxel.text(70, 170, "PRESS SPACE TO RESTART", YELLOW)


if __name__ == "__main__":
    Game()
