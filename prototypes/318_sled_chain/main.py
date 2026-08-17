"""SLED RUNAWAY — Bobsled color-match momentum run (Pyxel Prototype).

The sled's color auto-cycles. Click (or SPACE) a gate whose color matches the
sled to build COMBO and MOMENTUM. Push MOMENTUM past the runaway threshold for
3x score, but the color cycle halves and momentum drains fast — greed vs control.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

SCREEN_W = 320
SCREEN_H = 240

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

GATE_COLORS: tuple[int, ...] = (8, 11, 5, 10)  # RED, LIME, DARK_BLUE, YELLOW
GATE_XS: tuple[int, ...] = (40, 84, 128, 172, 216, 260)
GATE_YS: tuple[int, ...] = (130, 100, 82, 82, 100, 130)
GATE_RADIUS = 12
GATE_COUNT = 6

SLED_X = 160
SLED_Y = 210

HEAT_MAX = 100.0
HEAT_MISMATCH = 15.0
HEAT_DECAY = 0.02

MOMENTUM_GAIN = 8.0
MOMENTUM_MAX = 100.0
RUNAWAY_THRESHOLD = 70.0
MOMENTUM_DECAY_IDLE = 0.1
MOMENTUM_DECAY_RUNAWAY = 0.35

COMBO_SUPER = 4
SUPER_DURATION = 300

TIMER_MAX = 3600

CYCLE_BASE = 20
CYCLE_MIN = 12


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass(frozen=True)
class Gate:
    x: int
    y: int
    color: int
    radius: int = GATE_RADIUS
    active: bool = True
    respawn_timer: int = 0


@dataclass(frozen=True)
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


@dataclass(frozen=True)
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="SLED RUNAWAY", fps=60)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.rng = random.Random(42)
        self.sled_color = GATE_COLORS[0]
        self.color_timer = CYCLE_BASE
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.best_score = getattr(self, "best_score", 0)
        self.heat = 0.0
        self.momentum = 0.0
        self.runaway = False
        self.super_timer = 0
        self.timer = TIMER_MAX
        self.elapsed = 0
        self.shake = 0
        self.phase = Phase.TITLE
        self.gates: list[Gate] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._spawn_gates()

    # ---- spawning ----

    def _spawn_gates(self) -> None:
        for i in range(GATE_COUNT):
            self.gates.append(
                Gate(
                    x=GATE_XS[i],
                    y=GATE_YS[i],
                    color=self.rng.choice(GATE_COLORS),
                )
            )

    def _respawn_delay(self) -> int:
        return max(25, 60 - self.elapsed // 120)

    def _update_gates(self) -> None:
        for i, gate in enumerate(self.gates):
            if gate.active:
                continue
            timer = gate.respawn_timer - 1
            if timer <= 0:
                self.gates[i] = Gate(
                    x=gate.x,
                    y=gate.y,
                    color=self.rng.choice(GATE_COLORS),
                )
            else:
                self.gates[i] = Gate(
                    x=gate.x,
                    y=gate.y,
                    color=gate.color,
                    active=False,
                    respawn_timer=timer,
                )

    # ---- cycle / momentum / heat ----

    def _cycle_interval(self) -> int:
        return max(CYCLE_MIN, CYCLE_BASE - self.elapsed // 120)

    def _current_cycle(self) -> int:
        return (self._cycle_interval() // 2) if self.runaway else self._cycle_interval()

    def _update_sled_color(self) -> None:
        self.color_timer -= 1
        if self.color_timer <= 0:
            idx = GATE_COLORS.index(self.sled_color)
            self.sled_color = GATE_COLORS[(idx + 1) % len(GATE_COLORS)]
            self.color_timer = self._current_cycle()

    def _update_momentum(self) -> None:
        was_runaway = self.runaway
        if self.super_timer <= 0:
            decay = MOMENTUM_DECAY_RUNAWAY if self.runaway else MOMENTUM_DECAY_IDLE
            self.momentum = max(0.0, self.momentum - decay)
        self.runaway = self.momentum >= RUNAWAY_THRESHOLD
        if self.runaway and not was_runaway:
            self.shake = 6
            self._spawn_float_text(SLED_X - 30, SLED_Y - 40, "RUNAWAY!", PINK)
            self._spawn_particles(SLED_X, SLED_Y, 16, CYAN)

    def _update_heat(self) -> None:
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            return
        if self.super_timer <= 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    # ---- core action ----

    def _hit_gate(self, idx: int) -> bool:
        gate = self.gates[idx]
        if not gate.active:
            return False

        matched = (gate.color == self.sled_color) or (self.super_timer > 0)

        if matched:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            mult = 3 if (self.runaway or self.super_timer > 0) else 1
            gained = 10 * self.combo * mult
            self.score += gained
            self.momentum = min(MOMENTUM_MAX, self.momentum + MOMENTUM_GAIN)

            triggered_super = self.combo >= COMBO_SUPER and self.super_timer <= 0
            if triggered_super:
                self.super_timer = SUPER_DURATION

            self.gates[idx] = Gate(
                x=gate.x,
                y=gate.y,
                color=gate.color,
                active=False,
                respawn_timer=self._respawn_delay(),
            )

            self._spawn_particles(gate.x, gate.y, 8, gate.color)
            if triggered_super:
                self._spawn_float_text(gate.x - 24, gate.y - 16, "SUPER SLIDE!", PINK)
            else:
                self._spawn_float_text(gate.x - 20, gate.y - 16, f"+{gained}", YELLOW)
            return True

        self.heat = min(HEAT_MAX, self.heat + HEAT_MISMATCH)
        self.combo = 0
        self.momentum = 0.0
        self._spawn_particles(gate.x, gate.y, 4, RED)
        self._spawn_float_text(gate.x - 18, gate.y - 16, "WRONG!", RED)
        return False

    # ---- per-frame updates ----

    def _update_timer(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER

    def _update_particles(self) -> None:
        self.particles = [
            Particle(
                x=p.x + p.vx,
                y=p.y + p.vy,
                vx=p.vx,
                vy=p.vy,
                color=p.color,
                life=p.life - 1,
            )
            for p in self.particles
            if p.life - 1 > 0
        ]

    def _update_floating_texts(self) -> None:
        self.floating_texts = [
            FloatingText(
                x=t.x,
                y=t.y - 0.5,
                text=t.text,
                color=t.color,
                life=t.life - 1,
            )
            for t in self.floating_texts
            if t.life - 1 > 0
        ]

    def _update_playing(self) -> None:
        self._update_sled_color()
        self._update_momentum()
        self._update_heat()
        self._update_gates()
        self._update_timer()
        self._update_particles()
        self._update_floating_texts()
        if self.super_timer > 0:
            self.super_timer -= 1

    # ---- effects ----

    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, 6.2832)
            speed = self.rng.uniform(0.5, 2.5)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    color=color,
                    life=int(self.rng.uniform(10, 25)),
                )
            )

    def _spawn_float_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, color=color, life=40))

    # ---- input / update ----

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.PLAYING
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R):
                self.best_score = max(self.best_score, self.score)
                self.reset()
        elif self.phase == Phase.PLAYING:
            self.elapsed += 1
            self._update_playing()
            if self.phase != Phase.PLAYING:
                return

            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                mx = pyxel.mouse_x
                my = pyxel.mouse_y
                for i, gate in enumerate(self.gates):
                    if not gate.active:
                        continue
                    if (mx - gate.x) ** 2 + (my - gate.y) ** 2 <= gate.radius ** 2:
                        self._hit_gate(i)
                        break
            elif pyxel.btnp(pyxel.KEY_SPACE):
                front = min(
                    (g for g in self.gates if g.active),
                    key=lambda g: g.x,
                    default=None,
                )
                if front is not None:
                    self._hit_gate(self.gates.index(front))

            if self.shake > 0:
                self.shake -= 1

    # ---- draw ----

    def draw(self) -> None:
        pyxel.cls(NAVY)
        if self.shake > 0:
            pyxel.camera(self.rng.randint(-2, 2), self.rng.randint(-2, 2))
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(96, 60, "SLED RUNAWAY", YELLOW)
        pyxel.text(56, 84, "Match gates to your sled color", WHITE)
        pyxel.text(44, 96, "Build MOMENTUM to go RUNAWAY", WHITE)
        pyxel.text(44, 108, "for 3x score (but faster cycling!)", WHITE)
        pyxel.text(72, 142, "CLICK: hit gate", GRAY)
        pyxel.text(72, 154, "SPACE: hit front gate", GRAY)
        pyxel.text(72, 166, "ENTER: start", GRAY)
        pyxel.text(72, 198, "COMBO x4 = SUPER SLIDE", PINK)

    def _draw_playing(self) -> None:
        pyxel.rect(0, 24, SCREEN_W, 200, LIGHT_BLUE)

        pyxel.text(4, 4, f"SCORE {self.score}", WHITE)
        pyxel.text(4, 14, f"COMBO x{self.combo}", PINK)

        frac = max(0.0, self.timer / TIMER_MAX)
        pyxel.rect(150, 4, int(80 * frac), 6, GREEN)
        pyxel.rectb(150, 4, 80, 6, GRAY)

        for gate in self.gates:
            color = GRAY if not gate.active else gate.color
            pyxel.circ(gate.x, gate.y, gate.radius, color)
            pyxel.circb(gate.x, gate.y, gate.radius, WHITE if gate.active else GRAY)

        self._draw_sled()

        heat_color = GREEN if self.heat < 40 else YELLOW if self.heat < 70 else RED
        pyxel.rect(306, 30, 6, int(170 * self.heat / HEAT_MAX), heat_color)
        pyxel.rectb(306, 30, 6, 170, GRAY)

        pyxel.rect(4, 232, int(312 * self.momentum / MOMENTUM_MAX), 6, CYAN)
        pyxel.rectb(4, 232, 312, 6, GRAY)
        pyxel.rect(4 + int(312 * RUNAWAY_THRESHOLD / MOMENTUM_MAX), 230, 1, 10, WHITE)

        if self.runaway:
            pyxel.text(120, 4, "RUNAWAY!", PINK)

        self._draw_particles()
        self._draw_floats()

    def _draw_sled(self) -> None:
        color = GATE_COLORS[self.elapsed % len(GATE_COLORS)] if self.super_timer > 0 else self.sled_color
        pyxel.tri(SLED_X, SLED_Y - 12, SLED_X - 8, SLED_Y + 6, SLED_X + 8, SLED_Y + 6, color)
        pyxel.rectb(SLED_X - 8, SLED_Y - 12, 16, 18, WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floats(self) -> None:
        for t in self.floating_texts:
            pyxel.text(int(t.x), int(t.y), t.text, t.color)

    def _draw_game_over(self) -> None:
        pyxel.text(112, 60, "GAME OVER", RED)
        reason = "HEAT CRASH!" if self.heat >= HEAT_MAX else "TIME UP"
        pyxel.text(124, 80, reason, WHITE)
        pyxel.text(96, 112, f"SCORE {self.score}", YELLOW)
        pyxel.text(96, 132, f"BEST {self.best_score}", PINK)
        pyxel.text(96, 152, f"MAX COMBO x{self.max_combo}", WHITE)
        pyxel.text(96, 184, "R: retry", GRAY)


if __name__ == "__main__":
    Game()
