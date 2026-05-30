from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel


class Phase(Enum):
    TITLE = auto()
    AIMING = auto()
    SHOOTING = auto()
    RESULT = auto()
    GAME_OVER = auto()


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    active: bool = True


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


class HoopChain:
    COLORS: ClassVar[list[int]] = [8, 3, 5, 10]
    COLOR_NAMES: ClassVar[list[str]] = ["RED", "GREEN", "BLUE", "YELLOW"]
    SCREEN_W: ClassVar[int] = 320
    SCREEN_H: ClassVar[int] = 240
    SHOOT_X: ClassVar[int] = 60
    SHOOT_Y: ClassVar[int] = 200
    HOOP_LEFT: ClassVar[int] = 250
    HOOP_RIGHT: ClassVar[int] = 270
    HOOP_TOP: ClassVar[int] = 115
    HOOP_BOTTOM: ClassVar[int] = 125
    BALL_RADIUS: ClassVar[int] = 6
    GRAVITY: ClassVar[float] = 0.4
    MAX_POWER: ClassVar[float] = 15.0
    SUPER_THRESHOLD: ClassVar[int] = 3
    MAX_HEAT: ClassVar[int] = 10
    TOTAL_SHOTS: ClassVar[int] = 15
    MISS_HEAT: ClassVar[int] = 2

    def __init__(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: int = 0
        self.shots_taken: int = 0
        self.super_count: int = 0
        self.ball: Ball | None = None
        self.current_color: int = 8
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.drag_start_x: float = 0.0
        self.drag_start_y: float = 0.0
        self.drag_current_x: float = 0.0
        self.drag_current_y: float = 0.0
        self.is_dragging: bool = False
        self.shake_frames: int = 0
        self.result_timer: int = 0
        self._result_score_gained: int = 0
        self._result_is_super: bool = False
        self._result_is_miss: bool = False
        self._result_is_wrong_color: bool = False

    def reset(self) -> None:
        self.phase = Phase.AIMING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0
        self.shots_taken = 0
        self.super_count = 0
        self.ball = None
        self.current_color = random.choice(self.COLORS)
        self.particles.clear()
        self.floating_texts.clear()
        self.is_dragging = False
        self.shake_frames = 0
        self.result_timer = 0
        self._result_score_gained = 0
        self._result_is_super = False
        self._result_is_miss = False
        self._result_is_wrong_color = False

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        if self.phase == Phase.AIMING:
            self._update_aiming()
        elif self.phase == Phase.SHOOTING:
            self._update_shooting()
        elif self.phase == Phase.RESULT:
            self._update_result()

        self._update_particles()
        self._update_floating_texts()
        if self.shake_frames > 0:
            self.shake_frames -= 1

    def _update_aiming(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.is_dragging = True
            self.drag_start_x = float(pyxel.mouse_x)
            self.drag_start_y = float(pyxel.mouse_y)
            self.drag_current_x = self.drag_start_x
            self.drag_current_y = self.drag_start_y

        if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT) and self.is_dragging:
            self.drag_current_x = float(pyxel.mouse_x)
            self.drag_current_y = float(pyxel.mouse_y)

        if pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT) and self.is_dragging:
            self.is_dragging = False
            dx = self.drag_start_x - self.drag_current_x
            dy = self.drag_start_y - self.drag_current_y
            vx = dx * 0.2
            vy = dy * 0.2
            if abs(vx) < 0.5 and abs(vy) < 0.5:
                vx = 2.0
                vy = -3.0 + (self.SHOOT_Y - self.HOOP_TOP) * 0.02
            vx = max(-self.MAX_POWER, min(self.MAX_POWER, vx))
            vy = max(-self.MAX_POWER, min(self.MAX_POWER, vy))
            self.ball = Ball(
                x=float(self.SHOOT_X),
                y=float(self.SHOOT_Y),
                vx=vx,
                vy=vy,
                color=self.current_color,
            )
            self.phase = Phase.SHOOTING

    def _update_shooting(self) -> None:
        if self.ball is None:
            return
        ball = self.ball
        ball.x += ball.vx
        ball.y += ball.vy
        ball.vy += self.GRAVITY

        if self._is_in_hoop(ball.x, ball.y):
            self._handle_score()
            return

        if ball.y > self.SCREEN_H or ball.x > self.SCREEN_W or ball.x < -20:
            self._handle_miss()
            return

    def _handle_score(self) -> None:
        assert self.ball is not None
        ball_color = self.ball.color
        gained = self._on_score()
        self._result_score_gained = gained
        self._result_is_super = self.combo >= self.SUPER_THRESHOLD and self._check_color_match(ball_color)
        self._result_is_miss = False
        self._result_is_wrong_color = False
        if self._result_is_super:
            self.shake_frames = 20
            self._spawn_particles(self.HOOP_LEFT + 10, self.HOOP_TOP + 5, ball_color, 30)
        else:
            self._spawn_particles(self.HOOP_LEFT + 10, self.HOOP_TOP + 5, ball_color, 8)
        self.ball = None
        self.phase = Phase.RESULT
        self.result_timer = 30

    def _handle_miss(self) -> None:
        self._on_miss()
        self._result_score_gained = 0
        self._result_is_super = False
        self._result_is_miss = True
        self._result_is_wrong_color = False
        self.ball = None
        self.phase = Phase.RESULT
        self.result_timer = 30

    def _on_score(self) -> int:
        if self.ball is None:
            return 0
        ball_color = self.ball.color
        color_matches = self._check_color_match(ball_color)
        if color_matches:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            gained = 10 * self.combo
            if self.combo >= self.SUPER_THRESHOLD:
                gained *= 3
                self.super_count += 1
        else:
            self._on_wrong_color()
            gained = 10
        self.score += gained
        self.shots_taken += 1
        if self.shots_taken >= self.TOTAL_SHOTS or self.heat >= self.MAX_HEAT:
            self.phase = Phase.RESULT
            self.result_timer = 60
        return gained

    def _on_wrong_color(self) -> None:
        self.combo = 0

    def _on_miss(self) -> None:
        self.heat = min(self.MAX_HEAT, self.heat + self.MISS_HEAT)
        self.combo = 0
        self.shots_taken += 1

    def _check_color_match(self, ball_color: int) -> bool:
        return ball_color == self.current_color

    def _is_in_hoop(self, x: float, y: float) -> bool:
        return (
            self.HOOP_LEFT <= x <= self.HOOP_RIGHT
            and self.HOOP_TOP <= y <= self.HOOP_BOTTOM
        )

    def _compute_trajectory(self, vx: float, vy: float, steps: int = 60) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        x = float(self.SHOOT_X)
        y = float(self.SHOOT_Y)
        for _ in range(steps):
            x += vx
            y += vy
            vy += self.GRAVITY
            points.append((x, y))
        return points

    def _next_ball(self) -> None:
        self.current_color = random.choice(self.COLORS)

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(0.5, 3.0)
            particle_color = color
            if count >= 20:
                particle_color = random.choice(self.COLORS)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=random.randint(15, 40),
                    color=particle_color,
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 1.0
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _update_result(self) -> None:
        self.result_timer -= 1
        if self.result_timer <= 0:
            if self.shots_taken >= self.TOTAL_SHOTS or self.heat >= self.MAX_HEAT:
                self.phase = Phase.GAME_OVER
                return
            self._next_ball()
            self.phase = Phase.AIMING

    def draw(self) -> None:
        if self.shake_frames > 0:
            shake_x = random.randint(-3, 3)
            shake_y = random.randint(-3, 3)
            pyxel.camera(shake_x, shake_y)
        else:
            pyxel.camera()

        if self.phase == Phase.TITLE:
            self._draw_title()
        else:
            self._draw_court()
            self._draw_hud()

            if self.phase == Phase.AIMING:
                self._draw_aiming()
            elif self.phase == Phase.SHOOTING:
                self._draw_shooting()
            elif self.phase == Phase.RESULT:
                self._draw_result()
            elif self.phase == Phase.GAME_OVER:
                self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.cls(1)
        pyxel.text(105, 40, "HOOP CHAIN", 7)
        pyxel.rect(108, 49, 104, 1, 7)

        pyxel.text(80, 80, "CLICK & DRAG TO SHOOT", 7)
        pyxel.text(88, 95, "SAME COLOR = COMBO", 3)
        pyxel.text(72, 110, "COMBO x3+ = SUPER SHOT!", 10)

        self._draw_tiny_hoop(260, 70)

        pyxel.text(86, 150, "COLOR BALL VALUES:", 7)
        for i, (name, col) in enumerate(zip(self.COLOR_NAMES, self.COLORS)):
            px = 80 + i * 72
            pyxel.circ(px + 6, 170, 6, col)
            pyxel.text(px - 4, 182, name, col)

        pyxel.text(88, 210, "PRESS ENTER TO START", 7)
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(88, 210, "PRESS ENTER TO START", 10)

    def _draw_court(self) -> None:
        pyxel.cls(1)
        pyxel.rect(0, 210, self.SCREEN_W, 30, 4)

        pyxel.rect(270, 100, 10, 60, 7)
        pyxel.rect(268, 98, 14, 64, 9)

        pyxel.rect(250, 115, 20, 2, 8)
        pyxel.rect(250, 123, 20, 2, 8)

        net_x = self.HOOP_LEFT
        for ny in range(self.HOOP_BOTTOM + 2, 215, 4):
            pyxel.line(net_x, ny, net_x + 4, ny + 4, 7)

    def _draw_hud(self) -> None:
        combo_text = f"COMBO x{self.combo}"
        combo_color = 7
        if self.combo >= self.SUPER_THRESHOLD:
            combo_color = 10
        elif self.combo >= 2:
            combo_color = 9
        pyxel.text(4, 4, combo_text, combo_color)

        heat_bar_w = self.heat * 20
        pyxel.rect(4, 18, 200, 8, 5)
        if self.heat > 0:
            heat_color = 8 if self.heat >= 7 else 9
            pyxel.rect(4, 18, heat_bar_w, 8, heat_color)
        pyxel.text(4, 28, f"HEAT {self.heat}/{self.MAX_HEAT}", 8)

        pyxel.text(self.SCREEN_W - 55, 4, f"SCORE:{self.score:5d}", 7)

        remaining = self.TOTAL_SHOTS - self.shots_taken
        pyxel.text(self.SCREEN_W - 40, self.SCREEN_H - 16, f"BALLS:{remaining:2d}", 7)

    def _draw_aiming(self) -> None:
        if self.is_dragging:
            dx = self.drag_current_x - self.SHOOT_X
            dy = self.drag_current_y - self.SHOOT_Y
            steps = 12
            for i in range(steps):
                t = i / steps
                px = self.SHOOT_X + dx * t
                py = self.SHOOT_Y + dy * t
                if i % 3 == 0:
                    pyxel.pset(int(px), int(py), 7)

            power = math.sqrt(
                (self.drag_start_x - self.drag_current_x) ** 2
                + (self.drag_start_y - self.drag_current_y) ** 2
            )
            power_ratio = min(1.0, power / 60.0)
            bar_h = int(power_ratio * 60)
            bar_x = self.SHOOT_X + 20
            bar_y = self.SHOOT_Y - bar_h
            bar_color = 3 if power_ratio < 0.5 else (9 if power_ratio < 0.8 else 8)
            pyxel.rect(bar_x, bar_y, 6, bar_h, bar_color)
            pyxel.rectb(bar_x, self.SHOOT_Y - 60, 6, 60, 7)

        self._draw_ball(self.SHOOT_X, self.SHOOT_Y, self.current_color)

    def _draw_shooting(self) -> None:
        if self.ball is not None:
            self._draw_ball(int(self.ball.x), int(self.ball.y), self.ball.color)

    def _draw_result(self) -> None:
        if self.ball is None:
            self._draw_ball(self.SHOOT_X, self.SHOOT_Y, self.current_color)

        for ft in self.floating_texts:
            pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

        if self.result_timer > 0:
            if self._result_is_miss:
                pyxel.text(140, 80, "MISS!", 8)
            elif self._result_is_super:
                pyxel.text(128, 80, "SUPER!", 10)
            elif not self._result_is_wrong_color and self._result_score_gained > 0:
                pyxel.text(128, 80, f"+{self._result_score_gained}", 7)
            else:
                pyxel.text(130, 80, "GOAL!", 3)

    def _draw_game_over(self) -> None:
        pyxel.cls(1)
        pyxel.text(90, 40, "GAME OVER", 8)
        pyxel.rect(92, 49, 136, 1, 8)

        pyxel.text(100, 70, f"FINAL SCORE: {self.score}", 7)
        pyxel.text(100, 90, f"MAX COMBO: {self.max_combo}", 9)
        pyxel.text(100, 108, f"SUPER SHOTS: {self.super_count}", 10)

        self._draw_tiny_hoop(260, 170)

        pyxel.text(68, 210, "PRESS ENTER TO RETRY", 7)
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(68, 210, "PRESS ENTER TO RETRY", 10)

    def _draw_ball(self, x: int, y: int, color: int) -> None:
        r = self.BALL_RADIUS
        pyxel.circ(x, y, r, color)
        pyxel.circ(x, y, r, 0)
        pyxel.line(x - r, y, x + r, y, 0)
        pyxel.line(x, y - r, x, y + r, 0)

    def _draw_tiny_hoop(self, x: int, y: int) -> None:
        pyxel.rect(x + 10, y - 5, 4, 30, 7)
        pyxel.rect(x, y + 5, 12, 2, 8)


class App:
    def __init__(self) -> None:
        pyxel.init(
            HoopChain.SCREEN_W,
            HoopChain.SCREEN_H,
            title="Hoop Chain",
            display_scale=2,
        )
        pyxel.mouse(True)
        self.game = HoopChain()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        self.game.update()

    def draw(self) -> None:
        self.game.draw()


if __name__ == "__main__":
    App()
