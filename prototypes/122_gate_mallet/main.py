"""
GATE MALLET — Color-Match Croquet

Top-down croquet with color-matched gate passing.
Each stroke, the ball carries ONE color. Only gates of that color can be passed.
Same-color consecutive gate passes build COMBO chain.
COMBO >= 4 triggers SUPER SHOT (rainbow ball, all colors active, 3x score).
Heat builds with every stroke — miss too many and you lose.

Core fun: 「同じ色のフープを連続で通過し、COMBOを伸ばすのが面白い」
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# --- Colors (Pyxel palette) ---
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

# Game colors mapped to ball/gate colors
BALL_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]  # indices 0-3
N_COLORS = 4

# Screen
SCREEN_W = 320
SCREEN_H = 240

# Physics
FRICTION = 0.95
MAX_SPEED = 8.0
MIN_SPEED = 0.1
MAX_POWER_DIST = 80.0

# Gameplay
COMBO_THRESHOLD = 4
SUPER_DURATION = 150  # frames (5 seconds at 30fps)
SUPER_SCORE_MULT = 3
MAX_HEAT = 100.0
HEAT_PER_STROKE = 3.0
HEAT_PER_MISS = 10.0
HEAT_DECAY_RATE = 0.5
BASE_GATE_SCORE = 10

# Gates
TOTAL_GATES = 8
GATE_RADIUS = 12

# Gate layout (S-curve course): (x, y, color_index)
GATE_LAYOUT: list[tuple[int, int, int]] = [
    (60, 40, 0),
    (160, 80, 1),
    (260, 60, 2),
    (260, 140, 3),
    (160, 120, 0),
    (60, 160, 1),
    (160, 200, 2),
    (260, 180, 3),
]

# --- Data Classes ---

@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    color: int  # 0-3
    radius: float = 4.0
    moving: bool = False


@dataclass
class Gate:
    x: float
    y: float
    color: int  # 0-3
    active: bool = True
    passed: bool = False
    score_value: int = BASE_GATE_SCORE
    flash_timer: int = 0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


# --- Enums ---

class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class PlaySubPhase(Enum):
    IDLE = auto()
    AIMING = auto()
    MOVING = auto()


# --- Game Class ---

class Game:
    _rng: random.Random

    def __new__(cls) -> Game:
        obj = super().__new__(cls)
        obj.phase: Phase = Phase.TITLE
        obj.sub_phase: PlaySubPhase = PlaySubPhase.IDLE
        obj.ball: Ball = Ball(x=0.0, y=0.0, vx=0.0, vy=0.0, color=0)
        obj.gates: list[Gate] = []
        obj.particles: list[Particle] = []
        obj.floating_texts: list[dict] = []
        obj.score: int = 0
        obj.combo: int = 0
        obj.max_combo: int = 0
        obj.gates_passed: int = 0
        obj.heat: float = 0.0
        obj.super_mode: bool = False
        obj.super_timer: int = 0
        obj.aiming: bool = False
        obj.aim_start_x: float = 0.0
        obj.aim_start_y: float = 0.0
        obj.shake_frames: int = 0
        obj.high_score: int = 0
        obj.stroke_gate_passed: bool = False
        obj._rng = random.Random()
        return obj

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="GATE MALLET", display_scale=2, fps=30)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.sub_phase = PlaySubPhase.IDLE
        self.ball = Ball(x=160.0, y=200.0, vx=0.0, vy=0.0, color=0)
        self.gates = []
        self.particles = []
        self.floating_texts = []
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.gates_passed = 0
        self.heat = 0.0
        self.super_mode = False
        self.super_timer = 0
        self.aiming = False
        self.aim_start_x = 0.0
        self.aim_start_y = 0.0
        self.shake_frames = 0
        self.high_score = 0
        self.stroke_gate_passed = False
        self._spawn_gates()

    # --- Testable Logic Methods ---

    def _do_strike(self, dir_x: float, dir_y: float, power: float) -> None:
        """Launch ball in direction with given power (drag distance pixels).
        Advance heat for the stroke. Cycle ball color.
        """
        if power <= 0.0:
            return
        norm = math.sqrt(dir_x * dir_x + dir_y * dir_y)
        if norm < 0.001:
            return
        speed = min(MAX_SPEED, power / MAX_POWER_DIST * MAX_SPEED)
        self.ball.vx = dir_x / norm * speed
        self.ball.vy = dir_y / norm * speed
        self.ball.moving = True
        self.ball.color = (self.ball.color + 1) % N_COLORS
        self.heat = min(MAX_HEAT, self.heat + HEAT_PER_STROKE)
        self.stroke_gate_passed = False

    def _update_ball(self) -> None:
        """Apply velocity, friction, stop if below MIN_SPEED."""
        if not self.ball.moving:
            return
        self.ball.vx *= FRICTION
        self.ball.vy *= FRICTION
        self.ball.x += self.ball.vx
        self.ball.y += self.ball.vy

        # Screen bounds (bounce with energy loss)
        r = self.ball.radius
        if self.ball.x - r < 0:
            self.ball.x = r
            self.ball.vx = abs(self.ball.vx) * 0.6
        elif self.ball.x + r > SCREEN_W:
            self.ball.x = SCREEN_W - r
            self.ball.vx = -abs(self.ball.vx) * 0.6
        if self.ball.y - r < 0:
            self.ball.y = r
            self.ball.vy = abs(self.ball.vy) * 0.6
        elif self.ball.y + r > SCREEN_H:
            self.ball.y = SCREEN_H - r
            self.ball.vy = -abs(self.ball.vy) * 0.6

        speed = math.sqrt(self.ball.vx * self.ball.vx + self.ball.vy * self.ball.vy)
        if speed < MIN_SPEED:
            self.ball.vx = 0.0
            self.ball.vy = 0.0
            self.ball.moving = False

    def _check_gate_pass(self) -> tuple[int, int]:
        """Check if ball passes through any gate.
        Returns (gates_passed_this_frame, score_earned).
        Same-color pass: COMBO++, score+, gate marked passed.
        Wrong-color pass: combo reset to 0, gate NOT marked passed.
        Already-passed gate: no-op.
        """
        passed_count = 0
        earned = 0
        for gate in self.gates:
            if gate.passed:
                continue
            dx = self.ball.x - gate.x
            dy = self.ball.y - gate.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < GATE_RADIUS:
                # Color match: super_mode means all colors pass
                matches = self.super_mode or self.ball.color == gate.color
                if matches:
                    gate.passed = True
                    gate.flash_timer = 8
                    self.combo += 1
                    self.max_combo = max(self.max_combo, self.combo)
                    self.gates_passed += 1
                    self.stroke_gate_passed = True
                    mult = SUPER_SCORE_MULT if self.super_mode else 1
                    points = BASE_GATE_SCORE * self.combo * mult
                    self.score += points
                    earned += points
                    passed_count += 1

                    # Spawn effects
                    self._spawn_particles(gate.x, gate.y, BALL_COLORS[gate.color], 8)
                    combo_text = f"+{points}"
                    if self.combo >= COMBO_THRESHOLD and not self.super_mode:
                        self.super_mode = True
                        self.super_timer = SUPER_DURATION
                        self._spawn_particles(self.ball.x, self.ball.y, WHITE, 20)
                        self._add_floating_text(self.ball.x, self.ball.y - 16, "SUPER!", YELLOW, 60)
                        self.shake_frames = 10
                    self._add_floating_text(gate.x, gate.y - 8, combo_text, BALL_COLORS[gate.color], 30)
                else:
                    # Wrong color: combo reset, gate stays active (not passed)
                    self.combo = 0
        return (passed_count, earned)

    def _update_heat(self) -> None:
        """Trigger game over if heat >= MAX_HEAT, otherwise decay when idle."""
        if self.heat >= MAX_HEAT:
            self.heat = MAX_HEAT
            if self.score > self.high_score:
                self.high_score = self.score
            self.phase = Phase.GAME_OVER
            return
        if not self.ball.moving and self.sub_phase == PlaySubPhase.IDLE:
            self.heat = max(0.0, self.heat - HEAT_DECAY_RATE)

    def _update_super_mode(self) -> None:
        """Count down super_timer. Disable super_mode when expired."""
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0

    def _update_particles(self) -> None:
        """Age and remove dead particles."""
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def _update_floating_texts(self) -> None:
        """Age and remove dead floating texts."""
        alive: list[dict] = []
        for ft in self.floating_texts:
            ft["life"] -= 1
            ft["y"] -= 0.5
            if ft["life"] > 0:
                alive.append(ft)
        self.floating_texts = alive

    def _update_gate_flash(self) -> None:
        """Decrement gate flash timers."""
        for gate in self.gates:
            if gate.flash_timer > 0:
                gate.flash_timer -= 1

    def _spawn_gates(self) -> None:
        """Generate gates in a winding course pattern with slight random offset."""
        self.gates.clear()
        for x, y, color in GATE_LAYOUT:
            ox = self._rng.uniform(-6.0, 6.0)
            oy = self._rng.uniform(-6.0, 6.0)
            self.gates.append(
                Gate(x=float(x) + ox, y=float(y) + oy, color=color, active=True, passed=False)
            )

    def _reset_course(self) -> None:
        """Reset all gates to active=True, passed=False."""
        for gate in self.gates:
            gate.active = True
            gate.passed = False
            gate.flash_timer = 0

    def _all_gates_passed(self) -> bool:
        """Check if all gates have been passed."""
        return all(gate.passed for gate in self.gates)

    def _spawn_particles(self, x: float, y: float, color: int, count: int = 8) -> None:
        """Spawn colored particles at position."""
        for _ in range(count):
            angle = self._rng.uniform(0.0, math.pi * 2)
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=15,
                    color=color,
                )
            )

    def _add_floating_text(self, x: float, y: float, text: str, color: int, life: int = 30) -> None:
        """Add floating score/text popup."""
        self.floating_texts.append({"x": x, "y": y, "text": text, "life": life, "color": color})

    # --- Update ---

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE):
                self.phase = Phase.PLAYING
                self.sub_phase = PlaySubPhase.IDLE
                # Re-initialize playing state from fresh
                self.score = 0
                self.combo = 0
                self.max_combo = 0
                self.gates_passed = 0
                self.heat = 0.0
                self.super_mode = False
                self.super_timer = 0
                self.ball = Ball(x=160.0, y=200.0, vx=0.0, vy=0.0, color=0)
                self.particles = []
                self.floating_texts = []
                self.shake_frames = 0
                self.stroke_gate_passed = False
                self._spawn_gates()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R):
                self.phase = Phase.TITLE
                self.reset()
            return

        # PLAYING
        if self.phase == Phase.PLAYING:
            # Always update effects and timers
            self._update_particles()
            self._update_floating_texts()
            self._update_heat()
            self._update_super_mode()
            self._update_gate_flash()
            if self.shake_frames > 0:
                self.shake_frames -= 1

            # GAME_OVER may be set by _update_heat
            if self.phase == Phase.GAME_OVER:
                return

            # Sub-phase logic
            if self.sub_phase == PlaySubPhase.MOVING:
                self._update_ball()
                self._check_gate_pass()

                # All gates passed → course reset with bonus
                if self._all_gates_passed():
                    self._spawn_particles(self.ball.x, self.ball.y, WHITE, 16)
                    self._add_floating_text(self.ball.x, self.ball.y - 16, "LAP +100", YELLOW, 40)
                    self.score += 100
                    self._reset_course()

                if not self.ball.moving:
                    # Stroke ended — apply miss penalty if no gate passed
                    if not self.stroke_gate_passed:
                        self.heat = min(MAX_HEAT, self.heat + HEAT_PER_MISS)
                    self.sub_phase = PlaySubPhase.IDLE

            elif self.sub_phase == PlaySubPhase.IDLE:
                if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
                    self.sub_phase = PlaySubPhase.AIMING
                    self.aiming = True
                    self.aim_start_x = float(pyxel.mouse_x)
                    self.aim_start_y = float(pyxel.mouse_y)

            elif self.sub_phase == PlaySubPhase.AIMING:
                if not pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
                    # Mouse released — attempt strike
                    mx = float(pyxel.mouse_x)
                    my = float(pyxel.mouse_y)
                    dx = mx - self.ball.x
                    dy = my - self.ball.y
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist > 0.0:
                        self._do_strike(dx, dy, dist)
                        self.sub_phase = PlaySubPhase.MOVING
                    else:
                        self.sub_phase = PlaySubPhase.IDLE
                    self.aiming = False

    # --- Draw ---

    def draw(self) -> None:
        pyxel.cls(GREEN)

        if self.shake_frames > 0:
            sx = self._rng.randint(-3, 3)
            sy = self._rng.randint(-3, 3)
            pyxel.camera(sx, sy)
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
            return

        # PLAYING
        self._draw_lawn()
        self._draw_gates()
        self._draw_ball()
        if self.sub_phase == PlaySubPhase.AIMING and self.aiming:
            self._draw_aim_line()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_title(self) -> None:
        pyxel.text(105, 50, "GATE MALLET", WHITE)
        pyxel.text(85, 70, "Color-Match Croquet", GRAY)

        # Instructions
        lines: list[tuple[str, int]] = [
            ("CLICK to START", YELLOW),
            ("", WHITE),
            ("Click & Drag : Aim + Strike", GRAY),
            ("Same color gate = COMBO", GRAY),
            ("COMBO x4     = SUPER SHOT", GRAY),
            ("Each stroke  = HEAT +3", GRAY),
            ("Stay cool, shoot smart!", GRAY),
        ]
        for i, (line, col) in enumerate(lines):
            pyxel.text(60, 110 + i * 14, line, col)

        # Blinking start text
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(118, 110, "CLICK to START", YELLOW)

    def _draw_game_over(self) -> None:
        pyxel.text(100, 50, "GAME OVER", WHITE)

        info: list[tuple[str, str]] = [
            (f"SCORE: {self.score}", ""),
            (f"MAX COMBO: {self.max_combo}", ""),
            (f"GATES PASSED: {self.gates_passed}", ""),
            (f"HIGH SCORE: {self.high_score}", ""),
        ]
        for i, (text, _) in enumerate(info):
            pyxel.text(90, 90 + i * 20, text, WHITE)

        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(95, 190, "R to Retry", YELLOW)
        else:
            pyxel.text(95, 190, "R to Retry", WHITE)

    def _draw_lawn(self) -> None:
        # Horizontal grid lines
        for y in range(0, SCREEN_H, 40):
            pyxel.line(0, y, SCREEN_W, y, BROWN)
        # Vertical grid lines
        for x in range(0, SCREEN_W, 40):
            pyxel.line(x, 0, x, SCREEN_H, BROWN)

    def _draw_gates(self) -> None:
        for gate in self.gates:
            if gate.passed:
                col = GRAY
            elif self.super_mode:
                col = BALL_COLORS[(pyxel.frame_count // 4) % N_COLORS]
            else:
                col = BALL_COLORS[gate.color]

            # Flash when just passed (still draws with original color briefly)
            if gate.flash_timer > 0 and not gate.passed:
                col = WHITE

            # U-shaped gate (croquet hoop)
            half_w = 8
            gx = int(gate.x)
            gy = int(gate.y)
            # Two vertical posts
            pyxel.line(gx - half_w, gy - 8, gx - half_w, gy + 8, col)
            pyxel.line(gx + half_w, gy - 8, gx + half_w, gy + 8, col)
            # Top crossbar
            pyxel.line(gx - half_w - 2, gy - 8, gx + half_w + 2, gy - 8, col)

    def _draw_ball(self) -> None:
        bx = int(self.ball.x)
        by = int(self.ball.y)
        # Shadow
        pyxel.circ(bx + 2, by + 2, int(self.ball.radius), BLACK)
        # Ball color
        if self.super_mode:
            col = BALL_COLORS[(pyxel.frame_count // 4) % N_COLORS]
        else:
            col = BALL_COLORS[self.ball.color]
        pyxel.circ(bx, by, int(self.ball.radius), col)
        # Outline
        pyxel.circb(bx, by, int(self.ball.radius), WHITE)

    def _draw_aim_line(self) -> None:
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        dx = mx - self.ball.x
        dy = my - self.ball.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 1.0:
            return
        nx = dx / dist
        ny = dy / dist

        power = min(1.0, dist / MAX_POWER_DIST)
        col = YELLOW if power > 0.3 else ORANGE

        # Dotted line toward mouse
        step_count = int(dist / 6)
        for i in range(0, step_count, 2):
            x1 = int(self.ball.x + nx * i * 6)
            y1 = int(self.ball.y + ny * i * 6)
            x2 = int(self.ball.x + nx * (i + 1) * 6)
            y2 = int(self.ball.y + ny * (i + 1) * 6)
            pyxel.line(x1, y1, x2, y2, col)

        # Power indicator bar
        bar_len = int(power * 30)
        pnx = -ny
        pny = nx
        bx = int(self.ball.x + nx * 20)
        by = int(self.ball.y + ny * 20)
        ex = int(bx + pnx * bar_len)
        ey = int(by + pny * bar_len)
        pyxel.line(bx, by, ex, ey, col)

    def _draw_particles(self) -> None:
        for p in self.particles:
            col = p.color
            if p.life < 5:
                col = GRAY
            pyxel.pset(int(p.x), int(p.y), col)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            col = ft["color"] if ft["life"] > 10 else GRAY
            pyxel.text(int(ft["x"]), int(ft["y"]), str(ft["text"]), col)

    def _draw_hud(self) -> None:
        # Heat bar background
        pyxel.rect(5, 3, 104, 10, NAVY)
        # Heat bar fill
        heat_pct = self.heat / MAX_HEAT
        heat_width = int(heat_pct * 100)
        if heat_width > 0:
            if heat_pct > 0.75:
                heat_col = RED
            elif heat_pct > 0.5:
                heat_col = YELLOW
            else:
                heat_col = GREEN
            pyxel.rect(7, 5, heat_width, 6, heat_col)

        pyxel.text(5, 16, f"SCORE:{self.score}", WHITE)
        pyxel.text(5, 26, f"COMBO:{self.combo}", WHITE)
        if self.super_mode:
            super_sec = self.super_timer // 30 + 1
            pyxel.text(5, 36, f"SUPER! {super_sec}s", YELLOW)
        # Ball color indicator
        ball_col_name = ["RED", "GRN", "BLU", "YEL"][self.ball.color]
        pyxel.text(5, 46, f"COLOR:{ball_col_name}", BALL_COLORS[self.ball.color])


if __name__ == "__main__":
    Game()
