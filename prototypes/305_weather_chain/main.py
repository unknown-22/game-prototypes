from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

import pyxel

WEATHER_NAMES = ("SUN", "RAIN", "SNOW", "THUNDER")
WEATHER_COLORS = (10, 6, 7, 2)

LINE_X = 56
SCREEN_W = 320
SCREEN_H = 240


class Phase(Enum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


@dataclass
class WeatherFront:
    x: float
    y: int
    color: int
    speed: float
    shift_timer: int = 120
    flash_timer: int = 0


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
    x: int
    y: int
    text: str
    life: int
    color: int


class Game:
    def __init__(self) -> None:
        self._rng = random.Random()
        self.reset()

    def reset(self) -> None:
        if not hasattr(self, "_rng"):
            self._rng = random.Random()
        self.forecast_color = 0
        self.fronts: list[WeatherFront] = []
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = 3600
        self.super_timer = 0
        self.shake_frames = 0
        self.cycle_interval = 20
        self.spawn_interval = 90
        self.elapsed = 0
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self.phase = Phase.TITLE
        self.cycle_timer = self.cycle_interval
        self.spawn_timer = self.spawn_interval

    def _update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
                self.phase = Phase.PLAYING
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
                self.phase = Phase.PLAYING
        elif self.phase == Phase.PLAYING:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self._forecast_armed()
            self._update_timer()
            self._update_difficulty()
            self._update_cycle()
            self._update_fronts()
            self._update_heat()
            self._update_particles()
            self._update_floats()
            if self.super_timer > 0:
                self.super_timer -= 1
            if self.shake_frames > 0:
                self.shake_frames -= 1
            self._check_game_over()

    def _update_cycle(self) -> None:
        self.cycle_timer -= 1
        if self.cycle_timer <= 0:
            self.forecast_color = (self.forecast_color + 1) % 4
            self.cycle_timer = self.cycle_interval

    def _spawn_front(self) -> None:
        if len(self.fronts) >= 14:
            return
        elapsed = 3600 - self.timer
        speed = 1.0 + 1.5 * (elapsed / 3600.0)
        y = self._rng.randint(24, 216)
        color = self._rng.randrange(4)
        self.fronts.append(
            WeatherFront(x=320.0, y=y, color=color, speed=speed)
        )

    def _update_fronts(self) -> None:
        self.spawn_timer -= 1
        if self.spawn_timer <= 0 and len(self.fronts) < 14:
            self._spawn_front()
            self.spawn_timer = self.spawn_interval

        for f in self.fronts:
            f.x -= f.speed
            f.shift_timer -= 1
            if f.shift_timer <= 0:
                if f.flash_timer <= 0:
                    f.flash_timer = 15
                else:
                    f.flash_timer -= 1
                    if f.flash_timer <= 0:
                        if self._rng.random() < 0.3:
                            f.color = (f.color + 1 + self._rng.randrange(3)) % 4
                        f.shift_timer = 120

        remaining: list[WeatherFront] = []
        for f in self.fronts:
            if f.x < -20:
                self.heat += 5
                self.combo = 0
            else:
                remaining.append(f)
        self.fronts = remaining

    def _update_heat(self) -> None:
        if self.heat >= 100:
            self.phase = Phase.GAME_OVER
            return
        if self.super_timer <= 0:
            self.heat = max(0.0, self.heat - 0.02)

    def _update_timer(self) -> None:
        if self.timer > 0:
            self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self.phase = Phase.GAME_OVER

    def _update_difficulty(self) -> None:
        self.elapsed = 3600 - self.timer
        self.cycle_interval = max(12, 20 - (self.elapsed // 120))
        self.spawn_interval = max(30, 90 - (self.elapsed // 60))

    def _forecast_armed(self) -> None:
        armed: WeatherFront | None = None
        for f in self.fronts:
            if f.x <= LINE_X and f.x > -20:
                if armed is None or f.x < armed.x:
                    armed = f
        if armed is None:
            return

        if self.super_timer > 0:
            correct = True
        else:
            correct = self.forecast_color == armed.color

        if correct:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            mult = 3 if self.super_timer > 0 else 1
            points = 10 * self.combo * mult
            self.score += points
            self._burst(armed.x, armed.y)
            self.floats.append(
                FloatingText(
                    int(armed.x), int(armed.y), f"+{points}", 30,
                    WEATHER_COLORS[armed.color],
                )
            )
            if self.combo >= 4 and self.super_timer == 0:
                self.super_timer = 300
                self.floats.append(
                    FloatingText(
                        int(armed.x), int(armed.y) - 10, "SUPER FORECAST!",
                        40, 11,
                    )
                )
        else:
            self.heat += 15
            self.combo = 0
            self.floats.append(
                FloatingText(int(armed.x), int(armed.y), "WRONG!", 30, 8)
            )
            self.shake_frames = 8

        self.fronts.remove(armed)

    def _burst(self, x: float, y: float) -> None:
        for _ in range(8):
            vx = self._rng.uniform(-2.0, 2.0)
            vy = self._rng.uniform(-2.0, 0.5)
            color = WEATHER_COLORS[self._rng.randrange(4)]
            self.particles.append(
                Particle(
                    x=x, y=y, vx=vx, vy=vy,
                    life=20 + self._rng.randrange(10), color=color,
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floats(self) -> None:
        for f in self.floats:
            f.y -= 1
            f.life -= 1
        self.floats = [f for f in self.floats if f.life > 0]

    def _check_game_over(self) -> None:
        if self.timer <= 0 or self.heat >= 100:
            self.phase = Phase.GAME_OVER

    def _draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        else:
            self._draw_playing()

    def _draw_title(self) -> None:
        pyxel.cls(1)
        pyxel.text(112, 60, "WEATHER CHAIN", 10)
        pyxel.text(88, 80, "Weather Forecasting", 7)
        pyxel.text(56, 120, "SPACE: forecast   R: restart", 7)
        pyxel.text(52, 132, "Match the color of the arriving front!", 7)
        pyxel.text(100, 160, "PRESS SPACE TO START", 11)

    def _draw_game_over(self) -> None:
        pyxel.cls(1)
        pyxel.text(132, 80, "GAME OVER", 8)
        pyxel.text(116, 120, f"SCORE {self.score}", 7)
        pyxel.text(116, 132, f"MAX COMBO {self.max_combo}", 7)
        pyxel.text(132, 160, "R: restart", 11)

    def _draw_playing(self) -> None:
        if self.shake_frames > 0:
            pyxel.camera(
                self._rng.randint(-2, 2), self._rng.randint(-2, 2)
            )
        else:
            pyxel.camera(0, 0)

        pyxel.cls(5)
        pyxel.circ(296, 34, 12, 10)

        for f in self.fronts:
            self._draw_cloud(f)

        pyxel.line(LINE_X, 8, LINE_X, 208, 7)
        self._draw_station()
        self._draw_hud()

        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)
        for ft in self.floats:
            pyxel.text(ft.x, ft.y, ft.text, ft.color)

        if self.super_timer > 0:
            for i in range(4):
                col = WEATHER_COLORS[(pyxel.frame_count // 4 + i) % 4]
                pyxel.rectb(i, i, SCREEN_W - 2 * i, SCREEN_H - 2 * i, col)

    def _draw_cloud(self, f: WeatherFront) -> None:
        c = WEATHER_COLORS[f.color]
        x = int(f.x)
        y = f.y
        pyxel.circ(x, y, 8, c)
        pyxel.circ(x - 8, y + 3, 6, c)
        pyxel.circ(x + 8, y + 3, 6, c)
        pyxel.rect(x - 8, y, 16, 6, c)
        if f.flash_timer > 0:
            if (pyxel.frame_count // 4) % 2 == 0:
                pyxel.text(x - 2, y - 16, "!", 8)

    def _draw_station(self) -> None:
        c = WEATHER_COLORS[self.forecast_color]
        name = WEATHER_NAMES[self.forecast_color]
        pyxel.rect(LINE_X - 22, 208, 44, 20, c)
        pyxel.rectb(LINE_X - 22, 208, 44, 20, 7)
        pyxel.text(LINE_X - len(name) * 2, 230, name, 7)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE {self.score}", 7)
        combo_col = 11 if self.combo >= 4 else 7
        pyxel.text(4, 12, f"COMBO {self.combo}", combo_col)

        bar_w = 120
        frac = self.timer / 3600.0
        pyxel.rectb(156, 4, bar_w, 6, 7)
        pyxel.rect(156, 4, int(bar_w * frac), 6, 9 if frac > 0.3 else 8)
        pyxel.text(156 + bar_w + 4, 4, f"{self.timer // 60}s", 7)

        hx = 310
        hy = 40
        hh = 160
        pyxel.text(282, hy, "HEAT", 7)
        pyxel.rectb(hx, hy, 8, hh, 7)
        fill = int(hh * (self.heat / 100.0))
        heat_col = 3 if self.heat < 40 else (9 if self.heat < 70 else 8)
        pyxel.rect(hx + 1, hy + hh - fill, 6, fill, heat_col)


_game = Game()


def update() -> None:
    _game._update()


def draw() -> None:
    _game._draw()


if __name__ == "__main__":
    pyxel.init(SCREEN_W, SCREEN_H, title="WEATHER CHAIN")
    pyxel.run(update, draw)
