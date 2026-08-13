"""STAR CHAIN -- stargazing / constellation-observation combo game.

一番面白い瞬間: 同じ色の星を次々に観測して星座のラインが夜空を横切るように伸び、
SUPER TELESCOPE の虹色で一気にすべての星を掴み取る瞬間。
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

STAR_COLORS: tuple[int, int, int, int] = (RED, LIME, DARK_BLUE, YELLOW)


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Star:
    x: float
    y: float
    color: int
    life: int
    vx: float
    vy: float
    twinkle: int


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
    """Pure game logic -- pyxel calls only in update/draw/__init__."""

    SCREEN_W = SCREEN_W
    SCREEN_H = SCREEN_H
    FPS = FPS

    STAR_RADIUS = 3
    CLICK_RADIUS = 10

    HEAT_MAX = 100
    HEAT_DECAY = 0.02
    HEAT_MISMATCH = 15
    SUPER_DURATION = 300
    COMBO_SUPER_THRESHOLD = 4
    SUPER_MULT = 3

    GAME_DURATION = 3600  # 60 seconds

    MAX_CONSTELLATION = 80
    NUM_BACKGROUND_STARS = 40
    INITIAL_STARS = 8

    SPAWN_INTERVAL_START = 60
    SPAWN_INTERVAL_END = 25
    MAX_STARS_START = 12
    MAX_STARS_END = 24
    STAR_LIFETIME_START = 300
    STAR_LIFETIME_END = 150
    STAR_LIFETIME_WINDOW = 2700  # 45 seconds

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="STAR CHAIN", fps=FPS, display_scale=2)
        pyxel.mouse(True)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.align_color = RED
        self.rng: random.Random = random.Random()
        self.phase = Phase.TITLE
        self.score = 0
        self.best_score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat: float = 0.0
        self.super_timer = 0
        self.timer: int = self.GAME_DURATION
        self.elapsed: int = 0
        self.stars: list[Star] = []
        self.constellation: list[tuple[float, float, float, float, int]] = []
        self.last_obs_x: float | None = None
        self.last_obs_y: float | None = None
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shake_frames: int = 0
        self.spawn_timer: int = self.SPAWN_INTERVAL_START
        self.mouse_x: int = 0
        self.mouse_y: int = 0
        self.update_difficulty()
        self.background_stars: list[tuple[float, float, int]] = [
            (self.rng.uniform(0, SCREEN_W), self.rng.uniform(0, SCREEN_H),
             self.rng.choice((GRAY, LIGHT_BLUE)))
            for _ in range(self.NUM_BACKGROUND_STARS)
        ]

    def start_playing(self) -> None:
        self.align_color = RED
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_timer = 0
        self.timer = self.GAME_DURATION
        self.elapsed = 0
        self.stars = []
        self.constellation = []
        self.last_obs_x = None
        self.last_obs_y = None
        self.particles = []
        self.floating_texts = []
        self.shake_frames = 0
        self.spawn_timer = self.SPAWN_INTERVAL_START
        self.update_difficulty()
        for _ in range(self.INITIAL_STARS):
            self.spawn_star()

    def spawn_star(self) -> None:
        if len(self.stars) >= self.max_stars:
            return
        self.stars.append(
            Star(
                self.rng.uniform(0, SCREEN_W),
                self.rng.uniform(0, SCREEN_H),
                self.rng.choice(STAR_COLORS),
                self.star_lifetime,
                self.rng.uniform(-0.2, 0.2),
                self.rng.uniform(-0.2, 0.2),
                self.rng.randint(0, 31),
            )
        )

    def update_stars(self) -> None:
        for s in self.stars:
            s.x = (s.x + s.vx) % SCREEN_W
            s.y = (s.y + s.vy) % SCREEN_H
            s.twinkle = (s.twinkle + 1) % 32
            s.life -= 1
        self.stars = [s for s in self.stars if s.life > 0]

    def observe_star(self, star: Star) -> int:
        was_super = self.super_timer > 0
        matched = (star.color == self.align_color) or was_super
        multiplier = self.SUPER_MULT if was_super else 1
        if matched:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            gained = int(10 * self.combo * multiplier)
            self.score += gained
            if not was_super and self.combo >= self.COMBO_SUPER_THRESHOLD:
                self.super_timer = self.SUPER_DURATION
                self._spawn_text(SCREEN_W / 2, 24, "SUPER TELESCOPE!", YELLOW, 40)
            if self.last_obs_x is not None and self.last_obs_y is not None:
                self.constellation.append(
                    (self.last_obs_x, self.last_obs_y, star.x, star.y, star.color)
                )
                if len(self.constellation) > self.MAX_CONSTELLATION:
                    self.constellation.pop(0)
            self.last_obs_x = star.x
            self.last_obs_y = star.y
            if was_super:
                self._spawn_super_particles(star.x, star.y)
            else:
                self._spawn_match_particles(star.x, star.y, star.color)
            self._spawn_text(star.x, star.y - 8, "+%d" % gained, star.color, 20)
            if self.combo % 3 == 0:
                self._spawn_text(star.x, star.y - 16, "COMBO x%d" % self.combo, WHITE, 25)
            return gained
        self.combo = 0
        self.heat += self.HEAT_MISMATCH
        self.align_color = star.color
        self.last_obs_x = None
        self.last_obs_y = None
        self._spawn_mismatch_particles(star.x, star.y)
        self._spawn_text(star.x, star.y - 8, "WRONG!", GRAY, 20)
        self.shake_frames = 8
        return 0

    def handle_click(self, x: int, y: int) -> None:
        best: Star | None = None
        best_d = float("inf")
        for s in self.stars:
            d = math.hypot(x - s.x, y - s.y)
            if d <= self.CLICK_RADIUS and d < best_d:
                best = s
                best_d = d
        if best is not None:
            self.observe_star(best)
            self.stars.remove(best)

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
        self.spawn_interval = int(
            self.SPAWN_INTERVAL_START
            + (self.SPAWN_INTERVAL_END - self.SPAWN_INTERVAL_START) * t
        )
        self.max_stars = int(
            self.MAX_STARS_START + (self.MAX_STARS_END - self.MAX_STARS_START) * t
        )
        lt = min(self.elapsed / self.STAR_LIFETIME_WINDOW, 1.0)
        self.star_lifetime = int(
            self.STAR_LIFETIME_START
            + (self.STAR_LIFETIME_END - self.STAR_LIFETIME_START) * lt
        )

    def update_spawning(self) -> None:
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_star()
            self.spawn_timer = self.spawn_interval

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
            color = self.rng.choice(STAR_COLORS)
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

        self.mouse_x = pyxel.mouse_x
        self.mouse_y = pyxel.mouse_y
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.handle_click(self.mouse_x, self.mouse_y)

        self.elapsed += 1
        self.update_difficulty()
        self.update_spawning()
        self.update_stars()
        self.update_super()
        self.update_timer()
        self.update_heat()
        self._update_particles()
        self._update_floating_texts()

        if self.phase == Phase.GAME_OVER:
            self.best_score = max(self.best_score, self.score)

    def draw(self) -> None:
        pyxel.cls(BLACK)

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

    def _rainbow_color(self) -> int:
        return STAR_COLORS[(pyxel.frame_count // 4) % len(STAR_COLORS)]

    def _draw_star(self, s: Star) -> None:
        radius = self.STAR_RADIUS if ((pyxel.frame_count // 8 + s.twinkle) % 2 == 0) else 2
        if self.super_timer > 0:
            color = STAR_COLORS[(pyxel.frame_count + s.twinkle) % len(STAR_COLORS)]
        else:
            color = s.color
        pyxel.circ(int(s.x), int(s.y), radius, color)

    def _draw_crosshair(self) -> None:
        mx, my = self.mouse_x, self.mouse_y
        color = self._rainbow_color() if self.super_timer > 0 else self.align_color
        pyxel.line(mx - 9, my, mx - 4, my, color)
        pyxel.line(mx + 4, my, mx + 9, my, color)
        pyxel.line(mx, my - 9, mx, my - 4, color)
        pyxel.line(mx, my + 4, mx, my + 9, color)
        pyxel.circ(mx, my, 1, WHITE)

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
        pyxel.rect(5, 33, 8, 8, self.align_color)

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
        pyxel.rect(-8, -8, SCREEN_W + 16, SCREEN_H + 16, NAVY)

        for sx, sy, scol in self.background_stars:
            pyxel.pset(int(sx), int(sy), scol)

        if self.super_timer > 0:
            pyxel.rectb(0, 0, SCREEN_W - 1, SCREEN_H - 1, self._rainbow_color())

        for x1, y1, x2, y2, c in self.constellation:
            pyxel.line(int(x1), int(y1), int(x2), int(y2), c)

        for s in self.stars:
            self._draw_star(s)

        self._draw_crosshair()
        self._draw_hud()

        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

        for t in self.floating_texts:
            pyxel.text(int(t.x) - len(t.text) * FONT_W // 2, int(t.y), t.text, t.color)

    def _draw_title(self) -> None:
        title = "STAR CHAIN"
        pyxel.text(SCREEN_W // 2 - len(title) * FONT_W // 2, 50, title, YELLOW)
        sub = "STARGAZING CONSTELLATION COMBO"
        pyxel.text(SCREEN_W // 2 - len(sub) * FONT_W // 2, 66, sub, WHITE)

        for i, color in enumerate(STAR_COLORS):
            x = 70 + i * 48
            pyxel.circ(x, 90, 8, color)
            pyxel.circ(x, 90, 3, NAVY)

        lines = (
            "CLICK SAME-COLOR STARS TO OBSERVE",
            "CHAIN SAME COLORS TO BUILD A COMBO",
            "4+ COMBO = SUPER TELESCOPE (RAINBOW x3)",
            "WRONG COLOR = RE-ALIGN + HEAT UP",
            "HEAT UP OR TIME UP = GAME OVER",
            "",
            "MOUSE: AIM / CLICK",
            "ENTER OR SPACE: START",
        )
        for i, line in enumerate(lines):
            pyxel.text(SCREEN_W // 2 - len(line) * FONT_W // 2, 108 + i * 12, line, WHITE)

    def _draw_game_over(self) -> None:
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


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
