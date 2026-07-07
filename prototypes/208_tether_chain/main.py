"""Tether Chain — top-down tetherball arcade game."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

import pyxel

if TYPE_CHECKING:
    pass


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
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
    vy: float


class Game:
    CENTER_X: int = 160
    CENTER_Y: int = 120
    ROPE_LENGTH: int = 90
    BALL_RADIUS: int = 10
    POLE_RADIUS: int = 6
    COLOR_CYCLE_INTERVAL: int = 90
    SUPER_DURATION: int = 300
    GAME_DURATION: int = 3600
    HEAT_MAX: float = 100.0
    HEAT_WRONG: float = 15.0
    HEAT_MISS: float = 5.0
    HEAT_DECAY: float = 0.05
    SPEED_INITIAL: float = 0.02
    SPEED_ACCEL: float = 0.001
    HIT_COOLDOWN_FRAMES: int = 10
    BALL_COLORS: list[int] = [8, 3, 5, 10]
    RAINBOW_COLORS: list[int] = [8, 9, 10, 11, 12, 6]

    def __init__(self) -> None:
        pyxel.init(320, 240, title="Tether Chain", display_scale=2)
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.timer: int = self.GAME_DURATION
        self.ball_angle: float = 0.0
        self.ball_speed: float = self.SPEED_INITIAL
        self.ball_color: int = 0
        self.color_timer: int = self.COLOR_CYCLE_INTERVAL
        self.super_timer: int = 0
        self.prev_color: int | None = None
        self.last_hit_in_half: bool = False
        self.last_angle: float = 0.0
        self.hit_cooldown: int = 0
        self.particles.clear()
        self.floating_texts.clear()
        self.shake_frames: int = 0
        self.frame: int = 0

    def _update_ball(self) -> None:
        self.ball_angle += self.ball_speed
        if self.ball_angle >= math.pi * 2:
            self.ball_angle -= math.pi * 2
        elif self.ball_angle < 0:
            self.ball_angle += math.pi * 2

        self.color_timer -= 1
        if self.color_timer <= 0:
            self.color_timer = self.COLOR_CYCLE_INTERVAL
            self.ball_color = (self.ball_color + 1) % len(self.BALL_COLORS)

        self.ball_speed += self.SPEED_ACCEL / 60.0

        if self.super_timer > 0:
            self.super_timer -= 1

    def _is_ball_in_player_half(self) -> bool:
        return 0.0 <= self.ball_angle <= math.pi

    def _player_hit(self) -> None:
        ball_x = self.CENTER_X + self.ROPE_LENGTH * math.sin(self.ball_angle)
        ball_y = self.CENTER_Y + self.ROPE_LENGTH * math.cos(self.ball_angle)

        if self.super_timer > 0:
            pts = int(10 * 3)
            self.score += pts
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            self.super_timer = self.SUPER_DURATION
            self._spawn_particles(ball_x, ball_y, 11, 20)
            self._spawn_floating_text(ball_x, ball_y - 10, f"+{pts}", 11)
            if self.combo > 0:
                self._spawn_floating_text(
                    self.CENTER_X, 40, f"COMBO x{self.combo}!", 9
                )
            return

        current_color: int = self.BALL_COLORS[self.ball_color]

        if self.prev_color is not None and current_color == self.prev_color:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            pts = int(10 * (1 + self.combo * 0.5))
            self.score += pts
            self._spawn_particles(ball_x, ball_y, current_color, 10)
            self._spawn_floating_text(ball_x, ball_y - 10, f"+{pts}", current_color)
            if self.combo > 0:
                self._spawn_floating_text(
                    self.CENTER_X, 40, f"COMBO x{self.combo}!", 9
                )
            if self.combo >= 4:
                self.super_timer = self.SUPER_DURATION
        else:
            self.combo = 0
            self.heat = min(self.HEAT_MAX, self.heat + self.HEAT_WRONG)
            self._spawn_particles(ball_x, ball_y, 8, 5)
            self._spawn_floating_text(ball_x, ball_y - 10, "WRONG!", 8)
            if self.heat >= self.HEAT_MAX:
                self.phase = Phase.GAME_OVER

        self.prev_color = current_color
        self.hit_cooldown = self.HIT_COOLDOWN_FRAMES

    def _update_heat(self) -> None:
        if self.heat > 0:
            self.heat -= self.HEAT_DECAY
            if self.heat < 0:
                self.heat = 0.0

    def _check_game_over(self) -> bool:
        return self.heat >= self.HEAT_MAX or self.timer <= 0

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(0.5, 2.5)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = random.randint(15, 30)
            self.particles.append(Particle(x, y, vx, vy, life, color))

    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        self.floating_texts.append(FloatingText(x, y, text, 30, color, -1.0))

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def _update_floating_texts(self) -> None:
        alive: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life > 0:
                alive.append(ft)
        self.floating_texts = alive

    def _update_playing(self) -> None:
        self._update_ball()

        prev_in_half = self._is_ball_in_player_half()
        was_in_half = (
            0.0 <= self.last_angle <= math.pi
        )

        if prev_in_half and not was_in_half:
            self.last_hit_in_half = False

        if (
            not prev_in_half
            and was_in_half
            and not self.last_hit_in_half
            and self.hit_cooldown <= 0
        ):
            self.heat = min(self.HEAT_MAX, self.heat + self.HEAT_MISS)
            self.last_hit_in_half = True

        self.last_angle = self.ball_angle

        if self.hit_cooldown > 0:
            self.hit_cooldown -= 1

        if pyxel.btnp(pyxel.KEY_SPACE):
            if self._is_ball_in_player_half() and self.hit_cooldown <= 0:
                self.last_hit_in_half = True
                self._player_hit()

        self._update_heat()
        self._update_particles()
        self._update_floating_texts()

        self.timer -= 1
        if self._check_game_over():
            self.phase = Phase.GAME_OVER

    def update(self) -> None:
        self.frame += 1

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
                self.phase = Phase.PLAYING
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
                self.phase = Phase.TITLE

    def _get_ball_pos(self) -> tuple[float, float]:
        x = self.CENTER_X + self.ROPE_LENGTH * math.sin(self.ball_angle)
        y = self.CENTER_Y + self.ROPE_LENGTH * math.cos(self.ball_angle)
        return x, y

    def _draw_tether(self) -> None:
        bx, by = self._get_ball_pos()
        pyxel.line(self.CENTER_X, self.CENTER_Y, bx, by, 13)

        pyxel.circ(self.CENTER_X, self.CENTER_Y, self.POLE_RADIUS, 13)
        pyxel.circb(self.CENTER_X, self.CENTER_Y, self.POLE_RADIUS, 7)

    def _draw_ball(self) -> None:
        bx, by = self._get_ball_pos()

        if self.super_timer > 0:
            ci = (self.frame // 8) % len(self.RAINBOW_COLORS)
            color = self.RAINBOW_COLORS[ci]
            for r_offset in (3, 5):
                pyxel.circb(bx, by, self.BALL_RADIUS + r_offset, color)
        else:
            color = self.BALL_COLORS[self.ball_color]

        pyxel.circ(bx, by, self.BALL_RADIUS, color)
        pyxel.circb(bx, by, self.BALL_RADIUS, 7)

        for dx, dy in (
            (self.BALL_RADIUS, 0),
            (-self.BALL_RADIUS, 0),
            (0, self.BALL_RADIUS),
            (0, -self.BALL_RADIUS),
        ):
            pyxel.pset(bx + dx, by + dy, 7)

    def _draw_player_zone(self) -> None:
        for ang in range(181):
            rad = math.radians(ang)
            sx = self.CENTER_X + self.ROPE_LENGTH * math.sin(rad)
            sy = self.CENTER_Y + self.ROPE_LENGTH * math.cos(rad)
            pyxel.pset(sx, sy, 1)

        for px in range(0, 320, 4):
            pyxel.pset(px, 230, 1)
        pyxel.pset(159, 230, 1)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", 7)
        time_s = self.timer // 60
        time_str = f"TIME: {time_s}s"
        pyxel.text(320 - len(time_str) * 4 - 4, 4, time_str, 7)

        if self.combo > 0:
            combo_text = f"x{self.combo}"
            x_off = self.CENTER_X - len(combo_text) * 2
            color = 9
            if self.super_timer > 0:
                color = self.RAINBOW_COLORS[(self.frame // 8) % len(self.RAINBOW_COLORS)]
            pyxel.text(x_off, 20, combo_text, color)

        if self.super_timer > 0:
            super_text = "SUPER!"
            ci = self.RAINBOW_COLORS[(self.frame // 8) % len(self.RAINBOW_COLORS)]
            x_off = self.CENTER_X - len(super_text) * 2
            pyxel.text(x_off, 32, super_text, ci)

        bar_width = 200
        bar_height = 6
        bar_x = (320 - bar_width) // 2
        bar_y = 224
        fill = int(bar_width * (self.heat / self.HEAT_MAX))

        if fill > 0:
            heat_color = 8
            if self.heat / self.HEAT_MAX > 0.5:
                heat_color = 9
            if self.heat / self.HEAT_MAX > 0.8:
                heat_color = 10
            pyxel.rect(bar_x, bar_y, fill, bar_height, heat_color)

        pyxel.rectb(bar_x, bar_y, bar_width, bar_height, 7)
        heat_label = "HEAT"
        pyxel.text(bar_x - 22, bar_y - 1, heat_label, 7)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            pyxel.text(int(ft.x - len(ft.text) * 2), int(ft.y), ft.text, ft.color)

    def _draw_title(self) -> None:
        title = "TETHER CHAIN"
        x_off = self.CENTER_X - len(title) * 2
        pyxel.text(x_off, 60, title, 7)

        pyxel.text(self.CENTER_X - 42, 130, "Press SPACE to start", 13)

        pyxel.text(self.CENTER_X - 36, 170, "SPACE = Hit Ball", 13)

        preview_angle = (self.frame * 0.02) % (math.pi * 2)
        px = self.CENTER_X + self.ROPE_LENGTH * math.sin(preview_angle)
        py = self.CENTER_Y + self.ROPE_LENGTH * math.cos(preview_angle)
        pyxel.line(self.CENTER_X, self.CENTER_Y, px, py, 13)
        pyxel.circ(self.CENTER_X, self.CENTER_Y, self.POLE_RADIUS, 13)
        pyxel.circb(self.CENTER_X, self.CENTER_Y, self.POLE_RADIUS, 7)

        ci = (self.frame // 8) % len(self.RAINBOW_COLORS)
        pyxel.circ(px, py, self.BALL_RADIUS, self.RAINBOW_COLORS[ci])
        pyxel.circb(px, py, self.BALL_RADIUS, 7)

    def _draw_game_over(self) -> None:
        game_over = "GAME OVER"
        x_off = self.CENTER_X - len(game_over) * 2
        pyxel.text(x_off, 80, game_over, 8)

        score_text = f"SCORE: {self.score}"
        x_off = self.CENTER_X - len(score_text) * 2
        pyxel.text(x_off, 110, score_text, 7)

        combo_text = f"MAX COMBO: {self.max_combo}"
        x_off = self.CENTER_X - len(combo_text) * 2
        pyxel.text(x_off, 130, combo_text, 9)

        pyxel.text(self.CENTER_X - 48, 170, "Press SPACE to restart", 13)

    def draw(self) -> None:
        pyxel.cls(0)

        if self.phase == Phase.TITLE:
            self._draw_tether()
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_player_zone()
            self._draw_tether()
            self._draw_ball()
            self._draw_hud()
            self._draw_particles()
            self._draw_floating_texts()
        elif self.phase == Phase.GAME_OVER:
            self._draw_tether()
            self._draw_game_over()


if __name__ == "__main__":
    Game()
