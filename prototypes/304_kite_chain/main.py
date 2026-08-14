"""KITE CHAIN -- same-color wind-gust combo kite game.

一番面白い瞬間: 同色の突風を次々に捉えて凧のリボン軌跡が空に虹の帯を描き、
SUPER KITE の虹色で一気に風を掴みスコアが爆発する瞬間。
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

SCREEN_W = 320
SCREEN_H = 240
FPS = 60

FONT_W = 4
FONT_H = 6

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

KITE_COLORS: tuple[int, int, int, int] = (RED, LIME, DARK_BLUE, YELLOW)


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Gust:
    x: float
    y: float
    color: int
    vx: float
    length: int


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


@dataclass
class TrailPoint:
    x: float
    y: float
    life: int
    color: int


class Game:
    """Pure game logic -- pyxel calls only in update/draw/__init__."""

    SCREEN_W = SCREEN_W
    SCREEN_H = SCREEN_H
    FPS = FPS

    KITE_RADIUS = 5
    COLLIDE_RAD = 11
    KITE_SPEED = 2.0

    HEAT_MAX = 100.0
    HEAT_DECAY = 0.02
    HEAT_MISMATCH = 15.0
    SUPER_DURATION = 300
    COMBO_SUPER_THRESHOLD = 4
    SUPER_MULT = 3

    GAME_DURATION = 3600  # 60 seconds

    TRAIL_INTERVAL = 3
    TRAIL_CAP = 200
    TRAIL_LIFE = 45

    CYCLE_INTERVAL_START = 20
    CYCLE_INTERVAL_END = 12
    CYCLE_WINDOW = 2700  # 45 seconds

    GUST_SPEED_START = 1.5
    GUST_SPEED_END = 3.0
    SPAWN_INTERVAL_START = 60
    SPAWN_INTERVAL_END = 25
    MAX_GUSTS_START = 6
    MAX_GUSTS_END = 14

    GUST_LENGTH_MIN = 14
    GUST_LENGTH_MAX = 22

    INITIAL_GUSTS = 4
    NUM_CLOUDS = 6

    KITE_START_X = 160.0
    KITE_START_Y = 200.0

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="KITE CHAIN", fps=FPS, display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.rng: random.Random = random.Random()
        self.phase = Phase.TITLE
        self.kite_x: float = self.KITE_START_X
        self.kite_y: float = self.KITE_START_Y
        self.kite_color_idx: int = 0
        self.color_timer: int = self.CYCLE_INTERVAL_START
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.best_score: int = 0
        self.heat: float = 0.0
        self.super_timer: int = 0
        self.timer: int = self.GAME_DURATION
        self.elapsed: int = 0
        self.gusts: list[Gust] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.trail: list[TrailPoint] = []
        self.trail_tick: int = self.TRAIL_INTERVAL
        self.shake_frames: int = 0
        self.spawn_timer: int = self.SPAWN_INTERVAL_START
        self.update_difficulty()
        self.clouds: list[tuple[float, float, float]] = [
            (
                self.rng.uniform(0, SCREEN_W),
                self.rng.uniform(10, SCREEN_H - 60),
                self.rng.uniform(0.2, 0.6),
            )
            for _ in range(self.NUM_CLOUDS)
        ]

    def start_playing(self) -> None:
        self.phase = Phase.PLAYING
        self.kite_x = self.KITE_START_X
        self.kite_y = self.KITE_START_Y
        self.kite_color_idx = 0
        self.color_timer = self.CYCLE_INTERVAL_START
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.heat = 0.0
        self.super_timer = 0
        self.timer = self.GAME_DURATION
        self.elapsed = 0
        self.gusts = []
        self.particles = []
        self.floating_texts = []
        self.trail = []
        self.trail_tick = self.TRAIL_INTERVAL
        self.shake_frames = 0
        self.spawn_timer = self.SPAWN_INTERVAL_START
        self.update_difficulty()
        for _ in range(self.INITIAL_GUSTS):
            self.spawn_gust()

    def kite_color(self) -> int:
        return KITE_COLORS[self.kite_color_idx]

    def move_kite(self, dx: int, dy: int) -> None:
        if dx == 0 and dy == 0:
            return
        spd = self.KITE_SPEED
        if dx != 0 and dy != 0:
            spd /= math.sqrt(2)
        self.kite_x += dx * spd
        self.kite_y += dy * spd
        self.kite_x = max(0.0, min(float(SCREEN_W), self.kite_x))
        self.kite_y = max(0.0, min(float(SCREEN_H), self.kite_y))

    def advance_color(self) -> None:
        self.kite_color_idx = (self.kite_color_idx + 1) % len(KITE_COLORS)
        self.color_timer = self.cycle_interval

    def spawn_gust(self) -> None:
        if len(self.gusts) >= self.max_gusts:
            return
        self.gusts.append(
            Gust(
                SCREEN_W + 10.0,
                self.rng.uniform(20, SCREEN_H - 20),
                self.rng.choice(KITE_COLORS),
                -self.gust_speed,
                self.rng.randint(self.GUST_LENGTH_MIN, self.GUST_LENGTH_MAX),
            )
        )

    def update_gusts(self) -> None:
        for g in self.gusts:
            g.x += g.vx
        self.gusts = [g for g in self.gusts if g.x > -20]

    def update_trail(self) -> None:
        self.trail_tick -= 1
        if self.trail_tick <= 0:
            self.trail.append(
                TrailPoint(self.kite_x, self.kite_y, self.TRAIL_LIFE, self.kite_color())
            )
            if len(self.trail) > self.TRAIL_CAP:
                self.trail.pop(0)
            self.trail_tick = self.TRAIL_INTERVAL
        for p in self.trail:
            p.life -= 1
        self.trail = [p for p in self.trail if p.life > 0]

    def collide_gusts(self) -> None:
        for g in self.gusts:
            if math.hypot(self.kite_x - g.x, self.kite_y - g.y) <= self.COLLIDE_RAD:
                self.gusts.remove(g)
                self.resolve_collision(g)
                return

    def resolve_collision(self, gust: Gust) -> int:
        was_super = self.super_timer > 0
        matched = (gust.color == self.kite_color()) or was_super
        multiplier = self.SUPER_MULT if was_super else 1
        if matched:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            gained = int(10 * self.combo * multiplier)
            self.score += gained
            if not was_super and self.combo >= self.COMBO_SUPER_THRESHOLD:
                self.super_timer = self.SUPER_DURATION
                self._spawn_text(SCREEN_W / 2, 24, "SUPER KITE!", YELLOW, 40)
            if was_super:
                self._spawn_super_particles(gust.x, gust.y)
            else:
                self._spawn_match_particles(gust.x, gust.y, gust.color)
            self._spawn_text(gust.x, gust.y - 8, "+%d" % gained, gust.color, 20)
            if self.combo % 3 == 0:
                self._spawn_text(gust.x, gust.y - 16, "COMBO x%d" % self.combo, WHITE, 25)
            return gained
        self.combo = 0
        self.heat += self.HEAT_MISMATCH
        self._spawn_mismatch_particles(gust.x, gust.y)
        self._spawn_text(gust.x, gust.y - 8, "WRONG!", GRAY, 20)
        self.shake_frames = 8
        return 0

    def update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1

    def update_heat(self) -> None:
        if self.heat >= self.HEAT_MAX:
            self.phase = Phase.GAME_OVER
            return
        self.heat = max(0.0, self.heat - self.HEAT_DECAY)

    def update_timer(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self.phase = Phase.GAME_OVER

    def update_difficulty(self) -> None:
        t = min(self.elapsed / self.GAME_DURATION, 1.0)
        self.gust_speed = self.GUST_SPEED_START + (self.GUST_SPEED_END - self.GUST_SPEED_START) * t
        self.spawn_interval = int(
            self.SPAWN_INTERVAL_START
            + (self.SPAWN_INTERVAL_END - self.SPAWN_INTERVAL_START) * t
        )
        self.max_gusts = int(
            self.MAX_GUSTS_START + (self.MAX_GUSTS_END - self.MAX_GUSTS_START) * t
        )
        ct = min(self.elapsed / self.CYCLE_WINDOW, 1.0)
        self.cycle_interval = int(
            self.CYCLE_INTERVAL_START
            + (self.CYCLE_INTERVAL_END - self.CYCLE_INTERVAL_START) * ct
        )

    def update_spawning(self) -> None:
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_gust()
            self.spawn_timer = self.spawn_interval

    def update_color_cycle(self) -> None:
        self.color_timer -= 1
        if self.color_timer <= 0:
            self.advance_color()

    def _spawn_match_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(8):
            angle = self.rng.uniform(0.0, 2.0 * math.pi)
            speed = self.rng.uniform(0.5, 2.0)
            life = self.rng.randint(10, 20)
            self.particles.append(
                Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed, life, color)
            )

    def _spawn_super_particles(self, x: float, y: float) -> None:
        for _ in range(20):
            angle = self.rng.uniform(0.0, 2.0 * math.pi)
            speed = self.rng.uniform(1.0, 3.0)
            life = self.rng.randint(12, 24)
            color = self.rng.choice(KITE_COLORS)
            self.particles.append(
                Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed, life, color)
            )

    def _spawn_mismatch_particles(self, x: float, y: float) -> None:
        for _ in range(4):
            angle = self.rng.uniform(0.0, 2.0 * math.pi)
            speed = self.rng.uniform(0.5, 1.5)
            life = self.rng.randint(8, 14)
            self.particles.append(
                Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed, life, GRAY)
            )

    def _spawn_text(self, x: float, y: float, text: str, color: int, life: int) -> None:
        self.floating_texts.append(FloatingText(x, y, text, life, color))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for t in self.floating_texts:
            t.y -= 0.5
            t.life -= 1
        self.floating_texts = [t for t in self.floating_texts if t.life > 0]

    def _update_clouds(self) -> None:
        for i, (x, y, speed) in enumerate(self.clouds):
            x -= speed
            if x < -60:
                x = SCREEN_W + 60
            self.clouds[i] = (x, y, speed)

    def update(self) -> None:
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            pyxel.quit()

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self.start_playing()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
            return

        dx = 0
        dy = 0
        if pyxel.btn(pyxel.KEY_LEFT):
            dx -= 1
        if pyxel.btn(pyxel.KEY_RIGHT):
            dx += 1
        if pyxel.btn(pyxel.KEY_UP):
            dy -= 1
        if pyxel.btn(pyxel.KEY_DOWN):
            dy += 1
        self.move_kite(dx, dy)

        self.elapsed += 1
        self.update_difficulty()
        self.update_spawning()
        self.update_gusts()
        self.update_color_cycle()
        self.update_trail()
        self.collide_gusts()
        self.update_super()
        self.update_timer()
        self.update_heat()
        self._update_particles()
        self._update_floating_texts()
        self._update_clouds()

        if self.phase == Phase.GAME_OVER:
            self.best_score = max(self.best_score, self.score)

    def _rainbow_color(self) -> int:
        return KITE_COLORS[(pyxel.frame_count // 4) % len(KITE_COLORS)]

    def _draw_title(self) -> None:
        pyxel.cls(LIGHT_BLUE)
        title = "KITE CHAIN"
        pyxel.text(SCREEN_W // 2 - len(title) * FONT_W // 2, 50, title, YELLOW)
        sub = "WINDY SKY COMBO"
        pyxel.text(SCREEN_W // 2 - len(sub) * FONT_W // 2, 66, sub, WHITE)

        for i, color in enumerate(KITE_COLORS):
            x = 70 + i * 48
            pyxel.tri(x, 84, x - 8, 92, x + 8, 92, color)
            pyxel.tri(x, 100, x - 8, 92, x + 8, 92, color)

        lines = (
            "ARROWS: FLY KITE",
            "CATCH SAME-COLOR GUSTS TO COMBO",
            "4+ COMBO = SUPER KITE (RAINBOW x3)",
            "WRONG COLOR = HEAT UP + COMBO RESET",
            "HEAT FULL OR TIME UP = GAME OVER",
            "",
            "ENTER OR SPACE: START",
        )
        for i, line in enumerate(lines):
            pyxel.text(SCREEN_W // 2 - len(line) * FONT_W // 2, 116 + i * 12, line, WHITE)

    def _draw_game_over(self) -> None:
        pyxel.cls(LIGHT_BLUE)
        title = "GAME OVER"
        pyxel.text(SCREEN_W // 2 - len(title) * FONT_W // 2, 60, title, RED)
        lines = (
            "SCORE %d" % self.score,
            "BEST %d" % self.best_score,
            "MAX COMBO x%d" % self.max_combo,
            "",
            "ENTER OR SPACE: RESTART",
        )
        for i, line in enumerate(lines):
            pyxel.text(SCREEN_W // 2 - len(line) * FONT_W // 2, 100 + i * 14, line, WHITE)

    def _draw_clouds(self) -> None:
        for x, y, _speed in self.clouds:
            pyxel.circ(int(x), int(y), 10, WHITE)
            pyxel.circ(int(x) + 8, int(y) - 4, 8, WHITE)
            pyxel.circ(int(x) + 16, int(y), 9, WHITE)

    def _draw_gust(self, g: Gust) -> None:
        pyxel.rect(int(g.x), int(g.y) - 1, g.length, 3, g.color)
        pyxel.rect(int(g.x), int(g.y) - 2, 3, 5, WHITE)

    def _draw_kite(self) -> None:
        x = int(self.kite_x)
        y = int(self.kite_y)
        if self.super_timer > 0:
            color = self._rainbow_color()
        else:
            color = self.kite_color()
        pyxel.tri(x, y - 5, x - 4, y, x + 4, y, color)
        pyxel.tri(x, y + 5, x - 4, y, x + 4, y, color)
        pyxel.line(x, y + 5, x - 2, y + 9, color)
        pyxel.line(x - 2, y + 9, x + 1, y + 12, color)
        pyxel.line(x, y + 5, SCREEN_W // 2, SCREEN_H, GRAY)

    def _draw_hud(self) -> None:
        ratio = self.timer / self.GAME_DURATION
        bar_w = SCREEN_W - 8
        pyxel.rectb(4, 4, bar_w, 6, WHITE)
        fill = int(bar_w * ratio)
        tcol = LIME if ratio > 0.5 else (YELLOW if ratio > 0.25 else RED)
        if fill > 0:
            pyxel.rect(4, 4, fill, 6, tcol)

        pyxel.text(4, 14, "SCORE %d" % self.score, WHITE)
        pyxel.text(4, 22, "COMBO x%d" % self.combo, YELLOW)
        pyxel.rectb(4, 32, 10, 10, WHITE)
        pyxel.rect(5, 33, 8, 8, self.kite_color())

        hx = SCREEN_W - 16
        hy = 30
        hh = 180
        pyxel.rectb(hx, hy, 10, hh, WHITE)
        hr = min(self.heat / self.HEAT_MAX, 1.0)
        hfill = int(hh * hr)
        hcol = LIME if hr < 0.5 else (YELLOW if hr < 0.75 else RED)
        if hfill > 0:
            pyxel.rect(hx, hy + hh - hfill, 10, hfill, hcol)
        pyxel.text(hx - 4, hy - 8, "HEAT", WHITE)

        if self.super_timer > 0:
            s = "SUPER"
            pyxel.text(SCREEN_W // 2 - len(s) * FONT_W // 2, 26, s, self._rainbow_color())

    def _draw_playing(self) -> None:
        pyxel.rect(-8, -8, SCREEN_W + 16, SCREEN_H + 16, LIGHT_BLUE)
        self._draw_clouds()

        if self.super_timer > 0:
            pyxel.rectb(0, 0, SCREEN_W - 1, SCREEN_H - 1, self._rainbow_color())

        for p in self.trail:
            color = p.color if p.life > self.TRAIL_LIFE // 2 else LIGHT_BLUE
            pyxel.pset(int(p.x), int(p.y), color)

        for g in self.gusts:
            self._draw_gust(g)

        self._draw_kite()
        self._draw_hud()

        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

        for t in self.floating_texts:
            pyxel.text(int(t.x) - len(t.text) * FONT_W // 2, int(t.y), t.text, t.color)

    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
            return

        if self.shake_frames > 0:
            pyxel.camera(self.rng.randint(-2, 2), self.rng.randint(-2, 2))
            self.shake_frames -= 1
        else:
            pyxel.camera(0, 0)
        self._draw_playing()
        pyxel.camera(0, 0)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
