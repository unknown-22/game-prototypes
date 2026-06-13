"""Skee Chain - Color-matching Skee-Ball arcade game."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from random import Random

import pyxel


class Phase(Enum):
    TITLE = auto()
    AIMING = auto()
    ROLLING = auto()
    SCORING = auto()
    GAME_OVER = auto()


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


class Game:
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

    RING_CX = 160
    RING_CY = 60
    RING_RADII = [40, 32, 24, 16, 8]
    RING_SCORES = [10, 20, 30, 50, 100]
    RING_COLORS_POOL = [8, 3, 10, 6]  # RED, GREEN, YELLOW, LIGHT_BLUE

    SCREEN_W = 320
    SCREEN_H = 240
    MAX_BALLS = 30
    MAX_HEAT = 100
    POWER_CHARGE_RATE = 0.02
    HEAT_DECAY_RATE = 0.05
    HEAT_MISS_AMOUNT = 20
    GRAVITY = 0.3
    BALL_RADIUS = 4
    RAMP_LEFT = 100
    RAMP_RIGHT = 220
    RAMP_TOP_Y = 60
    RAMP_BOTTOM_Y = 220
    BALL_START_X = 160.0
    BALL_START_Y = 210.0
    SCORING_FRAMES = 30
    RING_COLOR_ROTATE_INTERVAL = 8
    COMBO_SUPER_THRESHOLD = 5
    SUPER_MULTIPLIER = 3

    def __new__(cls, *_args: object, **_kwargs: object) -> Game:
        instance = super().__new__(cls)
        instance.phase: Phase = Phase.TITLE
        instance.score: int = 0
        instance.combo: int = 0
        instance.max_combo: int = 0
        instance.heat: float = 0.0
        instance.balls_remaining: int = 0
        instance.power: float = 0.0
        instance.aim_x: float = 160.0
        instance.charging: bool = False
        instance.super_mode: bool = False
        instance.last_color: int | None = None
        instance.ball_x: float = 0.0
        instance.ball_y: float = 0.0
        instance.ball_vx: float = 0.0
        instance.ball_vy: float = 0.0
        instance.ball_active: bool = False
        instance.ball_color: int = instance.WHITE
        instance.ball_super: bool = False
        instance.particles: list[Particle] = []
        instance.floating_texts: list[FloatingText] = []
        instance.ring_colors: list[int] = []
        instance.ring_colors_timer: int = 0
        instance.score_flash: int = 0
        instance.shake_frames: int = 0
        instance.scoring_timer: int = 0
        instance.balls_thrown: int = 0
        instance.rng: Random = Random()
        return instance

    def __init__(self) -> None:
        pyxel.init(self.SCREEN_W, self.SCREEN_H, title="Skee Chain", display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.balls_remaining = self.MAX_BALLS
        self.power = 0.0
        self.aim_x = self.BALL_START_X
        self.charging = False
        self.super_mode = False
        self.last_color = None
        self.ball_x = 0.0
        self.ball_y = 0.0
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.ball_active = False
        self.ball_color = self.WHITE
        self.ball_super = False
        self.particles = []
        self.floating_texts = []
        self.ring_colors = []
        self.ring_colors_timer = 0
        self.score_flash = 0
        self.shake_frames = 0
        self.scoring_timer = 0
        self.balls_thrown = 0
        self.rng = Random()
        self._init_ring_colors()

    def _init_ring_colors(self) -> None:
        self.ring_colors = [
            self.RING_COLORS_POOL[i % len(self.RING_COLORS_POOL)]
            for i in range(5)
        ]

    # === Testable logic methods ===

    def _spawn_ball(self) -> None:
        self.ball_x = self.BALL_START_X
        self.ball_y = self.BALL_START_Y
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.ball_active = True
        self.ball_super = self.super_mode
        if self.super_mode:
            self.ball_color = self.PINK
            self.super_mode = False
        else:
            self.ball_color = self.WHITE

    def _charge_power(self) -> None:
        if self.power < 1.0:
            self.power = min(1.0, self.power + self.POWER_CHARGE_RATE)

    def _launch_ball(self) -> None:
        aim_offset = (self.aim_x - self.BALL_START_X) * 0.15
        self.ball_vx = aim_offset
        self.ball_vy = -self.power * 12.0
        self.power = 0.0
        self.charging = False

    def _update_ball(self) -> None:
        if not self.ball_active:
            return
        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy
        self.ball_vy += self.GRAVITY
        if self.ball_x - self.BALL_RADIUS < self.RAMP_LEFT:
            self.ball_x = float(self.RAMP_LEFT + self.BALL_RADIUS)
            self.ball_vx = abs(self.ball_vx) * 0.6
        elif self.ball_x + self.BALL_RADIUS > self.RAMP_RIGHT:
            self.ball_x = float(self.RAMP_RIGHT - self.BALL_RADIUS)
            self.ball_vx = -abs(self.ball_vx) * 0.6

    def _check_ring_hit(self) -> int | None:
        if not self.ball_active:
            return None
        dx = self.ball_x - self.RING_CX
        dy = self.ball_y - self.RING_CY
        dist = (dx * dx + dy * dy) ** 0.5
        for i in range(len(self.RING_RADII) - 1, -1, -1):
            if dist <= self.RING_RADII[i]:
                return i
        return None

    def _score_ring(self, ring_idx: int) -> int:
        if self.ball_super:
            total = 0
            for i in range(5):
                total += self.RING_SCORES[i] * self.SUPER_MULTIPLIER
            self.score += int(total)
            self.combo = 0
            self.max_combo = max(self.max_combo, self.combo)
            self.last_color = None
            self.super_mode = False
            return int(total)

        color = self.ring_colors[ring_idx]
        base = self.RING_SCORES[ring_idx]

        if self.last_color == color:
            multiplier = self._apply_combo()
            self.combo += 1
        else:
            multiplier = 1.0
            self.combo = 1
            self.last_color = color

        points = int(base * multiplier)
        self.score += points
        self.max_combo = max(self.max_combo, self.combo)

        if self.combo >= self.COMBO_SUPER_THRESHOLD:
            self.super_mode = True

        return points

    def _apply_combo(self) -> float:
        if self.combo <= 0:
            return 1.0
        return 1.0 + (self.combo - 1) * 0.5

    def _update_heat(self, amount: float) -> None:
        self.heat = min(float(self.MAX_HEAT), max(0.0, self.heat + amount))

    def _rotate_ring_colors(self) -> None:
        if not self.ring_colors:
            return
        last = self.ring_colors[-1]
        for i in range(len(self.ring_colors) - 1, 0, -1):
            self.ring_colors[i] = self.ring_colors[i - 1]
        self.ring_colors[0] = last

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self.rng.uniform(-2.0, 2.0),
                    vy=self.rng.uniform(-2.0, 2.0),
                    life=self.rng.randint(10, 30),
                    color=color,
                )
            )

    def _spawn_super_particles(self, x: float, y: float) -> None:
        for _ in range(30):
            color = self.rng.choice(self.RING_COLORS_POOL)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self.rng.uniform(-4.0, 4.0),
                    vy=self.rng.uniform(-4.0, 4.0),
                    life=self.rng.randint(15, 40),
                    color=color,
                )
            )

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=30, color=color)
        )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 1.0
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # === Phase machine ===

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.AIMING:
            self._update_aiming()
        elif self.phase == Phase.ROLLING:
            self._update_rolling()
        elif self.phase == Phase.SCORING:
            self._update_scoring()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.AIMING

    def _update_aiming(self) -> None:
        self.aim_x = max(
            float(self.RAMP_LEFT + self.BALL_RADIUS),
            min(float(self.RAMP_RIGHT - self.BALL_RADIUS), float(pyxel.mouse_x)),
        )

        if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
            if not self.charging:
                self.charging = True
                self.power = 0.0
            self._charge_power()
        elif self.charging:
            self._launch_ball()
            self._spawn_ball()
            self.balls_remaining -= 1
            self.balls_thrown += 1
            if self.balls_thrown % self.RING_COLOR_ROTATE_INTERVAL == 0:
                self._rotate_ring_colors()
            self.phase = Phase.ROLLING

        self._update_heat(-self.HEAT_DECAY_RATE)

    def _update_rolling(self) -> None:
        self._update_heat(-self.HEAT_DECAY_RATE)
        self._update_ball()

        if self.ball_y <= self.RAMP_TOP_Y or self.ball_y >= self.RAMP_BOTTOM_Y + 30:
            ring_idx = self._check_ring_hit()
            if ring_idx is not None:
                points = self._score_ring(ring_idx)
                if self.ball_super:
                    self._spawn_super_particles(self.RING_CX, self.RING_CY)
                    self._spawn_floating_text(
                        self.RING_CX, self.RING_CY - 10, f"+{points}", self.PINK
                    )
                    self.score_flash = 15
                    self.shake_frames = 15
                else:
                    color = self.ring_colors[ring_idx]
                    self._spawn_particles(self.ball_x, self.ball_y, color, 12)
                    self._spawn_floating_text(
                        self.ball_x, self.ball_y - 5, f"+{points}", color
                    )
            else:
                self._update_heat(float(self.HEAT_MISS_AMOUNT))
                self._spawn_floating_text(
                    self.ball_x, self.ball_y - 5, "MISS", self.RED
                )
            self.ball_active = False
            self.phase = Phase.SCORING
            self.scoring_timer = self.SCORING_FRAMES

    def _update_scoring(self) -> None:
        self._update_particles()
        self._update_floating_texts()
        self._update_heat(-self.HEAT_DECAY_RATE)

        if self.score_flash > 0:
            self.score_flash -= 1
        if self.shake_frames > 0:
            self.shake_frames -= 1

        self.scoring_timer -= 1
        if self.scoring_timer <= 0:
            self.particles.clear()
            self.floating_texts.clear()
            if self.balls_remaining <= 0 or self.heat >= self.MAX_HEAT:
                self.phase = Phase.GAME_OVER
            else:
                self.phase = Phase.AIMING

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.TITLE

    # === Draw methods ===

    def draw(self) -> None:
        pyxel.cls(self.NAVY)

        if self.shake_frames > 0:
            amp = self.shake_frames / 5.0
            ox = int(self.rng.uniform(-amp, amp))
            oy = int(self.rng.uniform(-amp, amp))
            pyxel.camera(ox, oy)
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.AIMING, Phase.ROLLING, Phase.SCORING):
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game()
            self._draw_game_over_overlay()

    def _draw_title(self) -> None:
        pyxel.text(85, 80, "SKEE CHAIN", self.YELLOW)
        pyxel.text(65, 100, "Color-match Skee-Ball", self.WHITE)
        pyxel.text(80, 140, "Click to Start", self.WHITE)
        pyxel.text(50, 165, "Aim: Mouse", self.GRAY)
        pyxel.text(50, 175, "Hold & Release: Power", self.GRAY)
        pyxel.text(50, 185, "Same color rings = COMBO", self.GRAY)
        pyxel.text(50, 195, "COMBO x5 = SUPER BALL!", self.GRAY)
        pyxel.text(50, 205, "Miss = HEAT up", self.GRAY)

    def _draw_game(self) -> None:
        self._draw_ramp()
        self._draw_target_rings()
        self._draw_ball()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_power_gauge()
        self._draw_hud()
        self._draw_aim_cursor()

    def _draw_ramp(self) -> None:
        left = self.RAMP_LEFT
        right = self.RAMP_RIGHT
        top = self.RAMP_TOP_Y
        bottom = self.RAMP_BOTTOM_Y

        pyxel.tri(left, bottom, right, bottom, right, top, self.GRAY)
        pyxel.tri(left, bottom, right, top, left, top, self.GRAY)

        pyxel.line(left, top, left, bottom, self.BROWN)
        pyxel.line(right, top, right, bottom, self.BROWN)
        pyxel.line(left, top, right, top, self.BROWN)

        for i in range(1, 4):
            xb = left + i * 30
            xt = left + 20 + i * 20
            pyxel.line(xb, bottom, xt, top, self.WHITE)

    def _draw_target_rings(self) -> None:
        flash_on = self.score_flash > 0 and self.score_flash % 2 == 0
        for i, r in enumerate(self.RING_RADII):
            if flash_on:
                c = self.RING_COLORS_POOL[
                    (i + pyxel.frame_count // 4) % len(self.RING_COLORS_POOL)
                ]
            else:
                c = self.ring_colors[i]
            pyxel.circ(self.RING_CX, self.RING_CY, r, c)
            pyxel.circb(self.RING_CX, self.RING_CY, r, self.WHITE)
            score_text = str(self.RING_SCORES[i])
            pyxel.text(self.RING_CX + r - 6, self.RING_CY - 3, score_text, self.BLACK)

    def _draw_ball(self) -> None:
        if not self.ball_active:
            return
        if self.ball_super:
            color = self.RING_COLORS_POOL[
                (pyxel.frame_count // 4) % len(self.RING_COLORS_POOL)
            ]
        else:
            color = self.ball_color
        pyxel.circ(int(self.ball_x), int(self.ball_y), self.BALL_RADIUS, color)
        pyxel.circb(
            int(self.ball_x), int(self.ball_y), self.BALL_RADIUS, self.WHITE
        )

    def _draw_power_gauge(self) -> None:
        gx, gy, gw, gh = 10, 60, 8, 140
        pyxel.rect(gx, gy, gw, gh, self.DARK_BLUE)
        pyxel.rectb(gx, gy, gw, gh, self.WHITE)

        fill_h = int(self.power * gh)
        fill_y = gy + gh - fill_h

        if self.power < 0.5:
            color = self.GREEN
        elif self.power < 0.8:
            color = self.YELLOW
        else:
            color = self.RED

        if fill_h > 0:
            pyxel.rect(gx, fill_y, gw, fill_h, color)

        pyxel.text(gx, gy - 8, "PWR", self.GRAY)

    def _draw_hud(self) -> None:
        pyxel.text(5, 2, f"SCORE: {self.score}", self.YELLOW)

        combo_color = self.WHITE
        if self.super_mode:
            combo_color = self.PINK
        elif self.combo >= 3:
            combo_color = self.YELLOW
        pyxel.text(5, 12, f"COMBO: {self.combo}", combo_color)

        if self.super_mode:
            pyxel.text(95, 14, "SUPER BALL READY!", self.PINK)

        heat_x, heat_y, heat_w, heat_h = 120, 2, 80, 6
        pyxel.rect(heat_x, heat_y, heat_w, heat_h, self.DARK_BLUE)
        pyxel.rectb(heat_x, heat_y, heat_w, heat_h, self.WHITE)
        heat_fill = int((self.heat / self.MAX_HEAT) * heat_w)
        pyxel.rect(heat_x, heat_y, heat_fill, heat_h, self.RED)
        pyxel.text(heat_x + 2, heat_y + 8, f"HEAT: {int(self.heat)}", self.GRAY)

        pyxel.text(245, 2, f"BALLS: {self.balls_remaining}", self.WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            if p.life > 5:
                pyxel.circ(int(p.x), int(p.y), 1, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life > 0:
                pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

    def _draw_aim_cursor(self) -> None:
        if self.phase != Phase.AIMING:
            return
        ax = int(self.aim_x)
        ay = self.RAMP_BOTTOM_Y - 15
        color = self.YELLOW if self.charging else self.WHITE
        pyxel.line(ax - 6, ay, ax + 6, ay, color)
        pyxel.line(ax, ay - 6, ax, ay + 6, color)
        if self.charging:
            dot_r = int(self.power * 8) + 2
            pyxel.circb(ax, ay, dot_r, self.YELLOW)

    def _draw_game_over_overlay(self) -> None:
        for y in range(1, self.SCREEN_H, 4):
            pyxel.rect(0, y, self.SCREEN_W, 1, self.BLACK)

        pyxel.text(100, 80, "GAME OVER", self.RED)
        pyxel.text(75, 100, f"Final Score: {self.score}", self.YELLOW)
        pyxel.text(75, 115, f"Max Combo: {self.max_combo}", self.WHITE)
        pyxel.text(80, 135, "Click to Retry", self.WHITE)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
