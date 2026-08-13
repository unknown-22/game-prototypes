"""CLOCK CHAIN -- clock-repair color-match game.

一番面白い瞬間: 歯車の色が合わずCOMBOが途切れそうな瞬間、未来の手札(時間と次の歯車)を
消費して巻き戻すか、素直にミスを受け入れるか迷う駆け引き。
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# -- Screen --
SCREEN_W = 320
SCREEN_H = 240
FPS = 60

# -- Font metrics (Pyxel default 4x6) --
FONT_W = 4
FONT_H = 6

# Color constants (Pyxel palette ints)
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

RAINBOW = (RED, ORANGE, YELLOW, LIME, CYAN, WHITE)


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
    color: int
    life: int


@dataclass
class FloatingText:
    text: str
    x: float
    y: float
    color: int
    life: int


class Game:
    """Pure game logic -- pyxel calls only in update/draw/__init__."""

    QUEUE_LEN = 6
    GEAR_COLORS = [RED, LIME, DARK_BLUE, YELLOW]  # index 0..3

    CYCLE_INTERVAL_START = 20
    CYCLE_INTERVAL_END = 12

    HEAT_MISMATCH = 15
    HEAT_DECAY = 0.02
    HEAT_CAP = 100

    SUPER_THRESHOLD = 4
    SUPER_DURATION = 300

    REWIND_COST = 120  # frames = 2 seconds
    GAME_TIME = 3600  # 60 seconds

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CLOCK CHAIN", fps=FPS, display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self._rng = random.Random(42)
        self.phase = Phase.TITLE
        self.queue: list[int] = [self._rng.randint(0, 3) for _ in range(self.QUEUE_LEN)]
        self.tool_color: int = 0
        self.cycle_timer: int = self.CYCLE_INTERVAL_START
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.best_score = 0
        self.heat: float = 0.0
        self.timer: int = self.GAME_TIME
        self.super_timer: int = 0
        self.elapsed: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shake: int = 0
        self.last_color: int | None = None

    # -- Core logic (pure, headless testable) --
    def _spawn_gear(self) -> int:
        return self._rng.randint(0, 3)

    def _cycle_interval(self) -> int:
        return int(
            self.CYCLE_INTERVAL_START
            + (self.CYCLE_INTERVAL_END - self.CYCLE_INTERVAL_START)
            * (self.elapsed / self.GAME_TIME)
        )

    def _advance_tool_color(self) -> None:
        if self.cycle_timer <= 0:
            self.tool_color = (self.tool_color + 1) % 4
            self.cycle_timer = self._cycle_interval()
        else:
            self.cycle_timer -= 1

    def _is_match(self, color: int) -> bool:
        return self.super_timer > 0 or color == self.tool_color

    def _repair(self) -> bool:
        color = self.queue[0]
        matched = self._is_match(color)
        if matched:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            mult = 3 if self.super_timer > 0 else 1
            self.score += 10 * self.combo * mult
            if self.combo >= self.SUPER_THRESHOLD and self.super_timer <= 0:
                self.super_timer = self.SUPER_DURATION
            self.last_color = color
        else:
            self.heat += self.HEAT_MISMATCH
            self.combo = 0
            self.last_color = None
        self.queue.pop(0)
        self.queue.append(self._spawn_gear())
        return matched

    def _rewind(self) -> bool:
        if len(self.queue) < 2 or self.super_timer > 0:
            return False
        self.timer -= self.REWIND_COST
        self.queue.pop(0)
        self.queue.append(self._spawn_gear())
        return True

    def _update_heat(self) -> None:
        if self.heat >= self.HEAT_CAP:
            self.phase = Phase.GAME_OVER
            return
        if self.super_timer > 0:
            return
        self.heat = max(0.0, self.heat - self.HEAT_DECAY)

    def _update_timer(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER

    # -- Particles / floating texts --
    def _spawn_burst(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-1.5, 1.5)
            vy = self._rng.uniform(-1.5, 1.5)
            life = self._rng.randint(8, 20)
            self.particles.append(Particle(x, y, vx, vy, color, life))

    def _spawn_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(text, x, y, color, 30))

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

    # -- Update --
    def update(self) -> None:
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            pyxel.quit()

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.PLAYING
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.PLAYING
            return

        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            was_super = self.super_timer > 0
            gear_color = self.queue[0]
            matched = self._repair()
            if matched:
                if not was_super and self.super_timer > 0:
                    self._spawn_text(160, 160, "SUPER! RAINBOW", YELLOW)
                self._spawn_burst(160, 200, self.GEAR_COLORS[gear_color], 8)
                self._spawn_text(160, 180, "COMBO x%d" % self.combo, YELLOW)
            else:
                self._spawn_burst(160, 200, RED, 6)
                self._spawn_text(160, 180, "MISS +HEAT", RED)
                self.shake = 6

        if pyxel.btnp(pyxel.KEY_R):
            if self._rewind():
                self._spawn_text(160, 180, "REWIND -2s", CYAN)

        self.elapsed += 1
        self._advance_tool_color()
        if self.super_timer > 0:
            self.super_timer -= 1
        self._update_timer()
        self._update_heat()
        self._update_particles()
        self._update_floating_texts()

        if self.heat >= self.HEAT_CAP or self.timer <= 0:
            self.best_score = max(self.best_score, self.score)

    # -- Draw --
    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
            return

        if self.shake > 0:
            pyxel.camera(self._rng.randint(-2, 2), self._rng.randint(-2, 2))
            self.shake -= 1
        else:
            pyxel.camera(0, 0)
        self._draw_playing()
        pyxel.camera(0, 0)

    def _rainbow_color(self) -> int:
        return RAINBOW[(pyxel.frame_count // 8) % len(RAINBOW)]

    def _draw_gear(self, x: int, y: int, radius: int, color: int) -> None:
        pyxel.circ(x, y, radius, color)
        pyxel.circb(x, y, radius, BLACK)
        pyxel.circ(x, y, max(1, radius // 3), BLACK)
        for i in range(8):
            a = i * math.pi / 4
            tx = x + int(math.cos(a) * radius)
            ty = y + int(math.sin(a) * radius)
            pyxel.rect(tx - 1, ty - 1, 3, 3, color)

    def _draw_title(self) -> None:
        title = "CLOCK CHAIN"
        pyxel.text(SCREEN_W // 2 - len(title) * FONT_W // 2, 50, title, YELLOW)

        names = ("RED", "LIME", "BLUE", "YELLOW")
        for i, (name, color) in enumerate(zip(names, self.GEAR_COLORS)):
            x = 60 + i * 50
            pyxel.circ(x, 90, 8, color)
            pyxel.text(x - len(name) * FONT_W // 2, 102, name, color)

        lines = (
            "MATCH THE TOOL COLOR TO THE GEAR",
            "SPACE: REPAIR (MISMATCH = HEAT)",
            "R: REWIND (SKIP GEAR, COST 2s)",
            "COMBO x4 = SUPER RAINBOW",
            "DONT OVERHEAT OR RUN OUT OF TIME",
            "",
            "ENTER: START",
        )
        for i, line in enumerate(lines):
            pyxel.text(
                SCREEN_W // 2 - len(line) * FONT_W // 2,
                130 + i * 12,
                line,
                WHITE,
            )

    def _draw_game_over(self) -> None:
        title = "GAME OVER"
        pyxel.text(SCREEN_W // 2 - len(title) * FONT_W // 2, 60, title, RED)
        lines = (
            "SCORE %d" % self.score,
            "BEST %d" % self.best_score,
            "MAX COMBO x%d" % self.max_combo,
            "",
            "ENTER: RETRY",
        )
        for i, line in enumerate(lines):
            pyxel.text(
                SCREEN_W // 2 - len(line) * FONT_W // 2,
                100 + i * 14,
                line,
                WHITE,
            )

    def _draw_playing(self) -> None:
        # Timer bar (across top)
        ratio = self.timer / self.GAME_TIME
        bar_w = SCREEN_W - 8
        pyxel.rectb(4, 4, bar_w, 6, WHITE)
        fill = int(bar_w * ratio)
        tcol = LIME if ratio > 0.5 else (YELLOW if ratio > 0.25 else RED)
        if fill > 0:
            pyxel.rect(4, 4, fill, 6, tcol)

        # Tool color swatch + score
        pyxel.rect(4, 14, 12, 12, self.GEAR_COLORS[self.tool_color])
        pyxel.rectb(4, 14, 12, 12, WHITE)
        pyxel.text(20, 16, "SCORE %d" % self.score, WHITE)

        # Combo (top-center)
        combo_str = "COMBO x%d" % self.combo
        pyxel.text(SCREEN_W // 2 - len(combo_str) * FONT_W // 2, 16, combo_str, YELLOW)

        # HEAT bar (vertical right side)
        hx = SCREEN_W - 16
        hy = 30
        hh = 180
        pyxel.rectb(hx, hy, 10, hh, WHITE)
        hr = self.heat / self.HEAT_CAP
        hfill = int(hh * hr)
        hcol = LIME if hr < 0.5 else (YELLOW if hr < 0.75 else RED)
        if hfill > 0:
            pyxel.rect(hx, hy + hh - hfill, 10, hfill, hcol)
        pyxel.text(hx - 1, hy - 8, "HEAT", WHITE)

        # Clock face
        cx, cy = 160, 120
        pyxel.circb(cx, cy, 90, WHITE)
        for i in range(4):
            a = i * math.pi / 2
            cos = math.cos(a)
            sin = math.sin(a)
            pyxel.line(
                cx + int(cos * 82),
                cy + int(sin * 82),
                cx + int(cos * 90),
                cy + int(sin * 90),
                WHITE,
            )

        # Clock hand (sweeps down as time runs out)
        ang = (self.timer / self.GAME_TIME) * math.tau - math.pi / 2
        pyxel.line(
            cx,
            cy,
            cx + int(math.cos(ang) * 68),
            cy + int(math.sin(ang) * 68),
            YELLOW,
        )
        pyxel.pset(cx, cy, WHITE)

        if self.super_timer > 0:
            s = "SUPER!"
            pyxel.text(
                SCREEN_W // 2 - len(s) * FONT_W // 2, 28, s, self._rainbow_color()
            )

        # Gear queue
        self._draw_gear(160, 200, 14, self.GEAR_COLORS[self.queue[0]])
        pyxel.text(205, 208, "NEXT", WHITE)
        for i in range(4, self.QUEUE_LEN):
            pyxel.circ(232 + (i - 4) * 10, 210, 2, self.GEAR_COLORS[self.queue[i]])
        for i in range(1, 4):
            self._draw_gear(205 + (i - 1) * 30, 225, 9, self.GEAR_COLORS[self.queue[i]])

        # Particles
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

        # Floating texts
        for t in self.floating_texts:
            pyxel.text(
                int(t.x) - len(t.text) * FONT_W // 2, int(t.y), t.text, t.color
            )


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
