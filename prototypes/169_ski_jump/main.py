"""Ski Jump — Chain same-color gates to trigger SUPER JUMP for 3x distance."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum

import pyxel

# ── Constants ────────────────────────────────────────────────────────────────
BLACK, NAVY, PURPLE, GREEN, BROWN, DARK_BLUE = 0, 1, 2, 3, 4, 5
LIGHT_BLUE, WHITE, RED, ORANGE, YELLOW = 6, 7, 8, 9, 10
LIME, CYAN, GRAY, PINK, PEACH = 11, 12, 13, 14, 15
GATE_COLORS = (RED, GREEN, DARK_BLUE, YELLOW)  # 8, 3, 5, 10

WIDTH, HEIGHT = 320, 240
FONT_W = 4

# Ramp geometry
RAMP_START_X, RAMP_START_Y = 60, 180
RAMP_MID_X, RAMP_MID_Y = 220, 100
RAMP_TAKEOFF_X, RAMP_TAKEOFF_Y = 260, 60

# Physics
GRAVITY = 0.15
APPROACH_SPEED_FACTOR = 0.3
DEFAULT_SPEED = 3.0
MAX_SPEED = 6.0
MIN_SPEED = 1.5
COMBO_SUPER_THRESHOLD = 4
SUPER_DURATION = 300  # frames (5s @ 60fps)
HEAT_PER_MISMATCH = 15
MAX_HEAT = 100
GATE_SPAWN_SPACING = (40, 70)  # min, max


# ── Enums / Data ─────────────────────────────────────────────────────────────
class Phase(Enum):
    TITLE = 0
    APPROACH = 1
    FLIGHT = 2
    LANDING = 3
    GAME_OVER = 4


@dataclass
class Gate:
    x: float
    y: float
    color: int
    width: int = 24
    height: int = 32
    passed: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


# ── Game ─────────────────────────────────────────────────────────────────────
class Game:
    def __init__(self) -> None:
        self._rng = random.Random()
        self._reset()

    # ── Resets ──────────────────────────────────────────────────────────
    def _reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.best_score = 0
        self.combo = 0
        self.max_combo = 0
        self.last_gate_color: int | None = None

        self.heat = 0.0
        self.wobble = False
        self.super_jump = False
        self.super_timer = 0

        self.player_x: float = float(RAMP_START_X)
        self.player_y: float = float(RAMP_START_Y)
        self.player_speed: float = DEFAULT_SPEED
        self.player_vx: float = 0.0
        self.player_vy: float = 0.0
        self.player_angle: float = 0.0
        self.player_on_ramp: bool = True

        self.flight_distance: float = 0.0
        self.landing_quality: float = 0.0

        self.gates: list[Gate] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []

        self.game_timer: float = 90.0
        self.landing_timer: int = 0

    def _reset_for_run(self) -> None:
        """Reset everything except best_score for a new run."""
        best = self.best_score
        self._reset()
        self.best_score = best
        self.phase = Phase.APPROACH
        self._spawn_gates()

    # ── Geometry ─────────────────────────────────────────────────────────
    @staticmethod
    def _ramp_y(x: float) -> float:
        if x < RAMP_START_X:
            return float(RAMP_START_Y)
        if x < RAMP_MID_X:
            t = (x - RAMP_START_X) / (RAMP_MID_X - RAMP_START_X)
            return RAMP_START_Y + t * (RAMP_MID_Y - RAMP_START_Y)
        if x <= RAMP_TAKEOFF_X:
            t = (x - RAMP_MID_X) / (RAMP_TAKEOFF_X - RAMP_MID_X)
            return RAMP_MID_Y + t * (RAMP_TAKEOFF_Y - RAMP_MID_Y)
        return float(RAMP_TAKEOFF_Y)

    @staticmethod
    def _ground_y(x: float) -> float:
        return RAMP_TAKEOFF_Y + 30 + (x - RAMP_TAKEOFF_X) * 0.5

    # ── Gate spawning ────────────────────────────────────────────────────
    def _spawn_gates(self) -> None:
        self.gates.clear()
        x = RAMP_START_X + 20.0
        while x < RAMP_TAKEOFF_X - 20 and len(self.gates) < 12:
            x += self._rng.uniform(*GATE_SPAWN_SPACING)
            if x >= RAMP_TAKEOFF_X - 20:
                break
            y = self._ramp_y(x)
            color = self._rng.choice(GATE_COLORS)
            self.gates.append(Gate(x=x, y=y, color=color))

    # ── Gate passing ─────────────────────────────────────────────────────
    def _pass_gate(self, gate: Gate) -> None:
        gate.passed = True
        if self.last_gate_color is None:
            self.combo = 1
            self.score += 50
            self._spawn_particles(gate.x, gate.y, gate.color, 8)
            self.floating_texts.append(
                FloatingText(gate.x, gate.y - 15, "+50", 20, WHITE)
            )
        elif self.last_gate_color == gate.color:
            self.combo += 1
            pts = 50 * self.combo
            self.score += pts
            self._spawn_particles(gate.x, gate.y, gate.color, 10)
            self.floating_texts.append(
                FloatingText(gate.x, gate.y - 20, f"+{pts}", 20, WHITE)
            )
            self.floating_texts.append(
                FloatingText(gate.x, gate.y - 10, f"COMBO x{self.combo}", 30, gate.color)
            )
        else:
            self.combo = 1
            self.heat = min(self.heat + HEAT_PER_MISMATCH, MAX_HEAT)
            self.floating_texts.append(
                FloatingText(gate.x, gate.y - 10, "MISS!", 25, ORANGE)
            )
        self.last_gate_color = gate.color
        self.max_combo = max(self.max_combo, self.combo)

    # ── Particles ────────────────────────────────────────────────────────
    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.tau)
            speed = self._rng.uniform(0.5, 2.5)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=self._rng.randint(10, 25),
                    color=color,
                )
            )

    # ── Phase transitions ────────────────────────────────────────────────
    def _takeoff(self) -> None:
        self.player_on_ramp = False
        combo = self.combo if self.combo > 0 else 1
        self.player_vx = self.player_speed * (1.0 + combo * 0.25) * 0.5
        self.player_vy = -3.0 - combo * 0.5

        if self.combo >= COMBO_SUPER_THRESHOLD:
            self.player_vx *= 1.5
            self.player_vy *= 1.5
            self.super_jump = True
            self.super_timer = SUPER_DURATION
            self._spawn_particles(self.player_x, self.player_y, YELLOW, 25)
            self.floating_texts.append(
                FloatingText(160, 90, "SUPER JUMP!", 60, YELLOW)
            )

        self.phase = Phase.FLIGHT

    def _land(self) -> None:
        slope_angle = math.atan(0.5)
        max_diff = 1.0
        self.landing_quality = max(
            0.0, min(1.0, 1.0 - abs(self.player_angle - slope_angle) / max_diff)
        )

        dist_score = self.flight_distance * 10
        multiplier = 3.0 if self.super_jump else 1.0
        final_add = int(dist_score * (1.0 + self.landing_quality) * multiplier)
        self.score += final_add

        self._spawn_particles(self.player_x, self.player_y, WHITE, 15)
        self.floating_texts.append(
            FloatingText(160, 80, f"+{final_add}", 40, WHITE)
        )

        if self.score > self.best_score:
            self.best_score = self.score

        self.phase = Phase.LANDING
        self.landing_timer = 120  # 2 seconds

    # ── Update phases ────────────────────────────────────────────────────
    def _update_approach(self) -> None:
        # Speed control
        target = DEFAULT_SPEED
        if pyxel.btn(pyxel.KEY_UP):
            target = MAX_SPEED
        elif pyxel.btn(pyxel.KEY_DOWN):
            target = MIN_SPEED
        self.player_speed += (target - self.player_speed) * 0.06

        # Move along ramp
        self.player_x += self.player_speed * APPROACH_SPEED_FACTOR
        self.player_x = max(self.player_x, RAMP_START_X)
        self.player_y = self._ramp_y(self.player_x)

        # Check gate passing
        for gate in self.gates:
            if not gate.passed and self.player_x >= gate.x:
                self._pass_gate(gate)

        # Check heat -> wobble
        self.wobble = self.heat >= MAX_HEAT

        # Check takeoff
        if self.player_x >= RAMP_TAKEOFF_X:
            self.player_x = float(RAMP_TAKEOFF_X)
            self.player_y = float(RAMP_TAKEOFF_Y)
            self._takeoff()

        # Timer
        self.game_timer -= 1.0 / 60.0
        if self.game_timer <= 0 and self.player_on_ramp:
            self._takeoff()

    def _update_flight(self) -> None:
        self.player_vy += GRAVITY
        self.player_x += self.player_vx
        self.player_y += self.player_vy

        # Pitch control
        if pyxel.btn(pyxel.KEY_UP):
            self.player_angle = max(-0.5, self.player_angle - 0.05)
        if pyxel.btn(pyxel.KEY_DOWN):
            self.player_angle = min(0.5, self.player_angle + 0.05)

        # Wobble
        if self.wobble:
            self.player_y += math.sin(pyxel.frame_count * 0.3) * 2.0

        # SUPER timer
        if self.super_jump and self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer == 0:
                self.super_jump = False

        # Trail particles
        if pyxel.frame_count % 2 == 0:
            tc = (
                self._rng.choice(GATE_COLORS)
                if self.super_jump
                else WHITE
            )
            self.particles.append(
                Particle(
                    x=self.player_x,
                    y=self.player_y,
                    vx=self._rng.uniform(-0.3, 0.3),
                    vy=self._rng.uniform(-0.3, 0.3),
                    life=15,
                    color=tc,
                )
            )

        # Distance tracking
        self.flight_distance = self.player_x - RAMP_TAKEOFF_X

        # Check landing
        if self.player_y >= self._ground_y(self.player_x) or self.player_x >= WIDTH:
            self._land()

    # ── Main update / draw ───────────────────────────────────────────────
    def update(self) -> None:
        # Particles
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

        # Floating texts
        for ft in self.floating_texts[:]:
            ft.y -= 0.6
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self._reset_for_run()

        elif self.phase == Phase.APPROACH:
            self._update_approach()

        elif self.phase == Phase.FLIGHT:
            self._update_flight()

        elif self.phase == Phase.LANDING:
            self.landing_timer -= 1
            if self.landing_timer <= 0:
                self.phase = Phase.GAME_OVER

        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self._reset_for_run()

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        else:
            self._draw_game()
            if self.phase == Phase.GAME_OVER:
                self._draw_game_over()

    # ── Drawing helpers ───────────────────────────────────────────────────
    @staticmethod
    def _draw_sky() -> None:
        for iy in range(0, 100):
            pyxel.rect(0, iy, WIDTH, 1, NAVY)
        for iy in range(100, 240):
            pyxel.rect(0, iy, WIDTH, 1, LIGHT_BLUE)

    @staticmethod
    def _draw_ramp() -> None:
        prev_x, prev_y = RAMP_START_X, Game._ramp_y(RAMP_START_X)
        for rx in range(RAMP_START_X + 1, RAMP_TAKEOFF_X + 1):
            ry = Game._ramp_y(float(rx))
            pyxel.line(int(prev_x), int(prev_y), int(rx), int(ry), BROWN)
            prev_x, prev_y = float(rx), ry

    def _draw_ground(self) -> None:
        if self.phase == Phase.APPROACH:
            for x in range(0, WIDTH, 3):
                ramp_y = self._ramp_y(min(float(x), RAMP_TAKEOFF_X))
                gy = int(ramp_y + 40)
                if gy < HEIGHT:
                    pyxel.rect(x, gy, 3, HEIGHT - gy, WHITE)
        else:
            for x in range(0, WIDTH, 3):
                gy = int(self._ground_y(float(x)))
                if gy < HEIGHT:
                    pyxel.rect(x, max(0, gy), 3, HEIGHT - max(0, gy), WHITE)

    def _draw_gates(self) -> None:
        for gate in self.gates:
            c = gate.color if not gate.passed else GRAY
            gx, gy = int(gate.x), int(gate.y)
            hw = gate.width // 2
            hh = gate.height // 2
            # Left post
            pyxel.rect(gx - hw, gy - hh, 2, gate.height, c)
            # Right post
            pyxel.rect(gx + hw - 2, gy - hh, 2, gate.height, c)
            # Top bar
            pyxel.rect(gx - hw, gy - hh, gate.width, 2, c)

    def _draw_player(self) -> None:
        px, py = int(self.player_x), int(self.player_y)
        if self.phase == Phase.APPROACH:
            # Skier on ramp — triangle pointing right+up
            pyxel.tri(px + 5, py, px - 5, py - 6, px - 5, py + 6, RED)
            pyxel.tri(px + 3, py, px - 3, py - 3, px - 3, py + 3, WHITE)
        else:
            # In flight — triangle with skis
            if self.super_jump and (pyxel.frame_count // 4) % 2 == 0:
                body_color = YELLOW
            else:
                body_color = RED
            pyxel.tri(px, py - 8, px - 5, py + 4, px + 5, py + 4, body_color)
            pyxel.tri(px, py - 5, px - 3, py + 1, px + 3, py + 1, WHITE)
            # Skis
            pyxel.line(px - 9, py + 4, px + 9, py + 8, BROWN)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.text == "SUPER JUMP!":
                c = GATE_COLORS[(pyxel.frame_count // 6) % len(GATE_COLORS)]
            else:
                c = ft.color
            tx = int(ft.x) - FONT_W * len(ft.text) // 2
            pyxel.text(tx, int(ft.y), ft.text, c)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)
        combo_color = (
            self.last_gate_color if self.last_gate_color is not None else WHITE
        )
        pyxel.text(4, 13, f"COMBO: x{self.combo}", combo_color)
        # Heat
        pyxel.text(4, 22, f"HEAT: {self.heat:.0f}/100", ORANGE)
        pyxel.rect(80, 22, 50, 5, GRAY)
        pyxel.rect(80, 22, int(50 * self.heat / MAX_HEAT), 5, ORANGE)
        # Timer
        pyxel.text(WIDTH - FONT_W * 10, 4, f"TIME: {int(self.game_timer)}", WHITE)
        # SUPER indicator
        if self.super_jump and self.super_timer > 0:
            s = f"SUPER {self.super_timer // 60 + 1}s"
            pyxel.text(WIDTH // 2 - FONT_W * len(s) // 2, 18, s, YELLOW)

    # ── Full-screen draw ─────────────────────────────────────────────────
    def _draw_title(self) -> None:
        pyxel.cls(NAVY)
        title = "SKI JUMP"
        pyxel.text(WIDTH // 2 - FONT_W * len(title) // 2, 70, title, WHITE)

        if (pyxel.frame_count // 30) % 2 == 0:
            msg = "Press SPACE to Start"
            pyxel.text(WIDTH // 2 - FONT_W * len(msg) // 2, 130, msg, WHITE)

        lines = [
            "UP: Tuck (faster)  DOWN: Stand (slower)",
            "Chain SAME COLOR gates for COMBO!",
            "COMBO>=4 = SUPER JUMP (3x distance!)",
        ]
        for i, line in enumerate(lines):
            pyxel.text(WIDTH // 2 - FONT_W * len(line) // 2, 170 + i * 14, line, WHITE)

    def _draw_game(self) -> None:
        self._draw_sky()
        self._draw_ground()

        if self.phase == Phase.APPROACH:
            self._draw_ramp()
            self._draw_gates()

        self._draw_player()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_game_over(self) -> None:
        # Semi-transparent overlay
        pyxel.rect(50, 40, 220, 170, BLACK)
        pyxel.rectb(50, 40, 220, 170, WHITE)

        lines_and_colors = [
            ("GAME OVER", RED),
            (f"Distance: {self.flight_distance:.0f}m", WHITE),
            (f"Landing: {self.landing_quality * 100:.0f}%", WHITE),
            (f"Score: {self.score}", WHITE),
        ]
        if self.super_jump:
            lines_and_colors.append(("SUPER JUMP! (3x)", YELLOW))

        lines_and_colors.append((f"Best: {self.best_score}", WHITE))

        for i, (text, color) in enumerate(lines_and_colors):
            pyxel.text(WIDTH // 2 - FONT_W * len(text) // 2, 65 + i * 18, text, color)

        if (pyxel.frame_count // 30) % 2 == 0:
            msg = "Press SPACE to Retry"
            pyxel.text(WIDTH // 2 - FONT_W * len(msg) // 2, 190, msg, WHITE)


# ── Entry point ──────────────────────────────────────────────────────────────
def run() -> None:
    game = Game()
    pyxel.init(WIDTH, HEIGHT, title="SKI JUMP", display_scale=2)
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    run()
