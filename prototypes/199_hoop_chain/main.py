from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pyxel

RED = 8
GREEN = 3
DARK_BLUE = 5
YELLOW = 10
HOOP_COLORS = (RED, GREEN, DARK_BLUE, YELLOW)
COLOR_NAMES = ("RED", "GREEN", "BLUE", "YELLOW")


@dataclass
class Hoop:
    x: float
    y: float
    color: int
    radius: int = 12


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    active: bool = True
    radius: int = 3


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
    vy: float = -1.0


class Game:
    SCREEN_W = 320
    SCREEN_H = 240
    FLOOR_Y = 210
    HOOP_Y = 50
    PLAYER_SPEED = 3
    GRAVITY = 0.3
    MAX_POWER = 15
    POWER_CHARGE_RATE = 0.3
    HEAT_MAX = 100
    HEAT_DECAY = 0.03
    HEAT_MISS = 15
    HEAT_WRONG = 8
    COMBO_SUPER = 4
    SUPER_DURATION = 300
    GAME_TIME = 3600

    def __init__(self) -> None:
        pyxel.init(self.SCREEN_W, self.SCREEN_H, title="HOOP CHAIN", display_scale=2, fps=60)
        self._reset()
        pyxel.run(self._update_wrapper, self._draw_wrapper)

    def _reset(self) -> None:
        self.phase: str = "TITLE"
        self.player_x: float = 160.0
        self.ball_color: int = 0
        self.hoops: list[Hoop] = self._create_hoops()
        self.ball: Ball | None = None
        self.charging: bool = False
        self.charge_power: float = 0.0
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.shots_made: int = 0
        self.total_shots: int = 0
        self.super_timer: int = 0
        self.timer: int = self.GAME_TIME
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.frame: int = 0
        self.mouse_was_pressed: bool = False

    def _create_hoops(self) -> list[Hoop]:
        xs = [60, 130, 200, 270]
        return [
            Hoop(x=float(xs[i]), y=float(self.HOOP_Y), color=HOOP_COLORS[i], radius=14)
            for i in range(4)
        ]

    def _update_wrapper(self) -> None:
        self.frame = pyxel.frame_count
        if self.phase == "TITLE":
            self._update_title()
        elif self.phase == "PLAYING":
            self._update_playing()
        elif self.phase == "GAME_OVER":
            self._update_game_over()

    def _draw_wrapper(self) -> None:
        if self.phase == "TITLE":
            self._draw_title()
        elif self.phase == "PLAYING":
            self._draw_playing()
        elif self.phase == "GAME_OVER":
            self._draw_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN):
            self._reset()
            self.phase = "PLAYING"

    def _update_playing(self) -> None:
        self._update_player()
        self._update_ball()
        self._update_particles()
        self._update_floating_texts()
        self._update_heat()
        self._update_timer()
        self._update_hoop_shift()
        self._update_super()

        if self.heat >= self.HEAT_MAX:
            self.phase = "GAME_OVER"

        if self.timer <= 0:
            self.phase = "GAME_OVER"

    def _update_player(self) -> None:
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            self.player_x -= self.PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            self.player_x += self.PLAYER_SPEED
        self.player_x = max(10.0, min(float(self.SCREEN_W - 26), self.player_x))

        if self.ball is None or not self.ball.active:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.charging = True
                self.charge_power = 0.0

        if self.charging:
            if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
                self.charge_power = min(self.MAX_POWER, self.charge_power + self.POWER_CHARGE_RATE)
            else:
                self._shoot()
                self.charging = False

    def _shoot(self) -> None:
        ball_x = self.player_x + 8.0
        ball_y = self.FLOOR_Y - 25.0
        mouse_x = pyxel.mouse_x
        target_x = mouse_x
        target_y = self.FLOOR_Y - 60.0

        dx = target_x - ball_x
        dy = target_y - ball_y
        dist = math.hypot(dx, dy)
        if dist < 0.001:
            dist = 1.0
        nx = dx / dist
        ny = dy / dist

        self.ball = Ball(
            x=ball_x,
            y=ball_y,
            vx=nx * self.charge_power,
            vy=ny * self.charge_power,
            color=HOOP_COLORS[self.ball_color],
            active=True,
        )
        self.total_shots += 1
        self.charge_power = 0.0

    def _update_ball(self) -> None:
        if self.ball is None or not self.ball.active:
            return
        self.ball.vy += self.GRAVITY
        self.ball.x += self.ball.vx
        self.ball.y += self.ball.vy

        if self.ball.y > self.FLOOR_Y + 20 or self.ball.x < -10 or self.ball.x > self.SCREEN_W + 10:
            self._on_miss()
            return

        for hoop in self.hoops:
            dist = math.hypot(self.ball.x - hoop.x, self.ball.y - hoop.y)
            if dist < hoop.radius + self.ball.radius:
                if self.super_timer > 0 or self.ball.color == hoop.color:
                    self._on_score(hoop)
                else:
                    self._on_wrong(hoop)
                return

    def _on_score(self, hoop: Hoop) -> None:
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        if self.super_timer > 0:
            multiplier = 1 + self.combo * 0.5 * 3
        else:
            multiplier = 1 + self.combo * 0.5
        gained = max(1, int(10 * multiplier))
        self.score += gained
        self.shots_made += 1

        self._spawn_score_particles(hoop, self.ball.color if self.ball else HOOP_COLORS[self.ball_color])
        self._spawn_floating_text(hoop.x, hoop.y, f"+{gained}", hoop.color)

        if self.combo > 1:
            self._spawn_floating_text(hoop.x, hoop.y - 10, f"COMBO x{self.combo}", pyxel.COLOR_YELLOW)

        if self.combo >= self.COMBO_SUPER and self.super_timer == 0:
            self._activate_super()

        self.ball = None
        self.ball_color = (self.ball_color + 1) % 4

    def _on_wrong(self, hoop: Hoop) -> None:
        self.combo = 0
        self.heat += self.HEAT_WRONG
        self._spawn_miss_particles(hoop.x, hoop.y)
        self._spawn_floating_text(hoop.x, hoop.y, "WRONG!", pyxel.COLOR_GRAY)
        self.ball = None

    def _on_miss(self) -> None:
        self.combo = 0
        self.heat += self.HEAT_MISS
        if self.ball is not None:
            self._spawn_miss_particles(self.ball.x, self.ball.y)
        self.ball = None

    def _activate_super(self) -> None:
        self.super_timer = self.SUPER_DURATION
        self._spawn_floating_text(
            self.SCREEN_W / 2, self.SCREEN_H / 2 - 20, "SUPER DUNK!", pyxel.COLOR_YELLOW
        )
        for _ in range(30):
            color = HOOP_COLORS[random.randint(0, 3)]
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, 6)
            self.particles.append(
                Particle(
                    x=self.SCREEN_W / 2,
                    y=self.SCREEN_H / 2,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=random.randint(15, 25),
                    color=color,
                )
            )

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1

    def _update_heat(self) -> None:
        self.heat = max(0.0, self.heat - self.HEAT_DECAY)
        self.heat = min(float(self.HEAT_MAX), self.heat)

    def _update_timer(self) -> None:
        self.timer = max(0, self.timer - 1)

    def _update_hoop_shift(self) -> None:
        # Shift every 900 frames (~15s), starting at frame 900, not frame 0
        if self.frame > 0 and self.frame % 900 == 0:
            self._shift_hoops()

    def _shift_hoops(self) -> None:
        for hoop in self.hoops:
            for _ in range(5):
                self.particles.append(
                    Particle(
                        x=hoop.x + random.uniform(-5, 5),
                        y=hoop.y + random.uniform(-5, 5),
                        vx=random.uniform(-1, 1),
                        vy=random.uniform(-1, 1),
                        life=random.randint(10, 20),
                        color=hoop.color,
                    )
                )

        sorted_hoops = sorted(self.hoops, key=lambda h: h.x)
        min_x = 40.0
        max_x = 280.0
        total_range = max_x - min_x
        min_gap = 50.0
        reserved = min_gap * 3
        available = total_range - reserved

        if available < 0:
            available = 0

        positions: list[float] = []
        current = min_x
        for i in range(4):
            if i == 3:
                positions.append(max_x)
            else:
                remaining = 4 - i - 1
                remaining_gap = min_gap * remaining
                max_pos = max_x - remaining_gap
                if max_pos <= current:
                    pos = current
                else:
                    pos = current + random.uniform(0, max_pos - current)
                positions.append(pos)
                current = pos + min_gap

        for i, hoop in enumerate(sorted_hoops):
            hoop.x = max(min_x, min(max_x, positions[i]))

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
            ft.y += ft.vy
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    def _spawn_score_particles(self, hoop: Hoop, color: int) -> None:
        for _ in range(random.randint(10, 15)):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1, 4)
            self.particles.append(
                Particle(
                    x=hoop.x,
                    y=hoop.y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=random.randint(15, 25),
                    color=color,
                )
            )

    def _spawn_miss_particles(self, x: float, y: float) -> None:
        for _ in range(5):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(0.5, 2)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=random.randint(10, 20),
                    color=pyxel.COLOR_GRAY,
                )
            )

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=30, color=color, vy=-1.0))

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self._reset()
            self.phase = "PLAYING"

    def _draw_title(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)
        pyxel.text(self.SCREEN_W // 2 - 40, 60, "HOOP CHAIN", pyxel.COLOR_WHITE)
        pyxel.text(self.SCREEN_W // 2 - 90, 100, "ARROWS: Move", pyxel.COLOR_WHITE)
        pyxel.text(self.SCREEN_W // 2 - 90, 110, "CLICK+HOLD: Charge", pyxel.COLOR_WHITE)
        pyxel.text(self.SCREEN_W // 2 - 90, 120, "RELEASE: Shoot", pyxel.COLOR_WHITE)
        if self.frame % 60 < 30:
            pyxel.text(self.SCREEN_W // 2 - 40, 160, "PRESS ENTER", pyxel.COLOR_YELLOW)

    def _draw_playing(self) -> None:
        pyxel.cls(pyxel.COLOR_NAVY)
        pyxel.rect(0, self.FLOOR_Y, self.SCREEN_W, self.SCREEN_H - self.FLOOR_Y, pyxel.COLOR_BROWN)
        pyxel.rectb(
            10, self.FLOOR_Y, self.SCREEN_W - 20, self.SCREEN_H - self.FLOOR_Y, pyxel.COLOR_ORANGE
        )

        self._draw_hoops()
        self._draw_player()
        self._draw_ball()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_hoops(self) -> None:
        for hoop in self.hoops:
            if self.super_timer > 0:
                color = HOOP_COLORS[self.frame % 4]
            else:
                color = hoop.color
            pyxel.circb(int(hoop.x), int(hoop.y), hoop.radius, color)
            pyxel.circb(int(hoop.x), int(hoop.y), hoop.radius - 1, color)
            net_top = int(hoop.y) + hoop.radius
            pyxel.line(int(hoop.x) - hoop.radius, net_top, int(hoop.x) - hoop.radius + 4, net_top + 8, color)
            pyxel.line(int(hoop.x), net_top, int(hoop.x), net_top + 8, color)
            pyxel.line(int(hoop.x) + hoop.radius, net_top, int(hoop.x) + hoop.radius - 4, net_top + 8, color)

    def _draw_player(self) -> None:
        px = int(self.player_x)
        pyxel.rect(px + 4, self.FLOOR_Y - 15, 8, 10, pyxel.COLOR_WHITE)
        pyxel.rect(px + 2, self.FLOOR_Y - 5, 12, 5, pyxel.COLOR_WHITE)
        pyxel.circ(px + 8, self.FLOOR_Y - 19, 4, pyxel.COLOR_WHITE)

        if self.ball is None or not self.ball.active:
            color = HOOP_COLORS[self.ball_color]
            pyxel.circ(px + 8, self.FLOOR_Y - 26, 4, color)

        if self.charging:
            bar_width = int((self.charge_power / self.MAX_POWER) * 30)
            pyxel.rect(px + 1, self.FLOOR_Y + 2, 30, 4, pyxel.COLOR_GRAY)
            if bar_width > 0:
                pyxel.rect(px + 1, self.FLOOR_Y + 2, bar_width, 4, pyxel.COLOR_YELLOW)

    def _draw_ball(self) -> None:
        if self.ball is not None and self.ball.active:
            pyxel.circ(int(self.ball.x), int(self.ball.y), self.ball.radius, self.ball.color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        pyxel.text(5, 5, f"SCORE: {self.score}", pyxel.COLOR_WHITE)

        combo_color = pyxel.COLOR_YELLOW if self.combo > 0 else pyxel.COLOR_GRAY
        if self.super_timer > 0:
            combo_color = HOOP_COLORS[self.frame % 4]
        pyxel.text(5, 15, f"COMBO: x{self.combo}", combo_color)

        heat_bar_x = self.SCREEN_W - 70
        pyxel.text(heat_bar_x, 5, "HEAT", pyxel.COLOR_WHITE)
        pyxel.rect(heat_bar_x, 12, 60, 6, pyxel.COLOR_DARK_BLUE)
        heat_width = int((self.heat / self.HEAT_MAX) * 60)
        if heat_width > 0:
            pyxel.rect(heat_bar_x, 12, heat_width, 6, pyxel.COLOR_RED)

        pyxel.text(
            self.SCREEN_W // 2 - 30, 5, f"TIME: {self.timer // 60}", pyxel.COLOR_WHITE
        )

        if self.super_timer > 0:
            super_color = HOOP_COLORS[self.frame % 4]
            pyxel.text(self.SCREEN_W // 2 - 35, 20, "SUPER DUNK!", super_color)

    def _draw_game_over(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)
        pyxel.text(self.SCREEN_W // 2 - 30, 60, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(self.SCREEN_W // 2 - 30, 100, f"SCORE: {self.score}", pyxel.COLOR_WHITE)
        pyxel.text(self.SCREEN_W // 2 - 40, 120, f"MAX COMBO: x{self.max_combo}", pyxel.COLOR_WHITE)
        pyxel.text(
            self.SCREEN_W // 2 - 30,
            140,
            f"SHOTS: {self.shots_made}/{self.total_shots}",
            pyxel.COLOR_WHITE,
        )
        if self.frame % 60 < 30:
            pyxel.text(self.SCREEN_W // 2 - 50, 180, "PRESS R TO RESTART", pyxel.COLOR_YELLOW)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
