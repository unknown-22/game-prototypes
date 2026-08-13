"""CLAY CHAIN -- pottery wheel color-match game.

一番面白い瞬間: 回転する轆轤(ろくろ)の上で、手の色と合う粘土が頂点に来た一瞬を狙って投げ、
同じ色を連続で投げてCOMBOが伸び、SUPER THROWで虹色に変わり全粘土が自動マッチする瞬間。
色が合わない粘土が迫る時、時間を削って窯で焼いて得点を確保するか、ミスを覚悟して
投げるか迷う駆け引きが面白い。
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

    SCREEN_W = SCREEN_W
    SCREEN_H = SCREEN_H
    FPS = FPS

    WHEEL_CX = 160
    WHEEL_CY = 120
    WHEEL_RADIUS = 60

    CLAY_COUNT = 8
    CLAY_RADIUS = 14
    CLAY_COLORS = [RED, LIME, DARK_BLUE, YELLOW]  # index 0..3

    MARKER_ANGLE = 270.0  # top of wheel

    WHEEL_SPEED_START = 2.0
    WHEEL_SPEED_END = 5.0

    CYCLE_INTERVAL_START = 20
    CYCLE_INTERVAL_END = 12

    HEAT_MISMATCH = 15
    HEAT_DECAY = 0.02
    HEAT_CAP = 100

    SUPER_THRESHOLD = 4
    SUPER_DURATION = 300

    KILN_COST = 240  # frames = 4 seconds
    KILN_BONUS_PER_POT = 25
    GAME_TIME = 3600  # 60 seconds

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CLAY CHAIN", fps=FPS, display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self._rng = random.Random(42)
        self.phase = Phase.TITLE
        self.clay: list[int] = [self._rng.randint(0, 3) for _ in range(self.CLAY_COUNT)]
        self.wheel_angle: float = 0.0
        self.hand_color: int = 0
        self.cycle_timer: int = self.CYCLE_INTERVAL_START
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.best_score = 0
        self.heat: float = 0.0
        self.timer: int = self.GAME_TIME
        self.super_timer: int = 0
        self.elapsed: int = 0
        self.shelf: list[int] = []  # completed pots (colors)
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shake: int = 0
        self.last_color: int | None = None

    # -- Core logic (pure, headless testable) --
    def _spawn_clay(self) -> int:
        return self._rng.randint(0, 3)

    def _cycle_interval(self) -> int:
        return int(
            self.CYCLE_INTERVAL_START
            + (self.CYCLE_INTERVAL_END - self.CYCLE_INTERVAL_START)
            * (self.elapsed / self.GAME_TIME)
        )

    def _wheel_speed(self) -> float:
        return self.WHEEL_SPEED_START + (
            self.WHEEL_SPEED_END - self.WHEEL_SPEED_START
        ) * (self.elapsed / self.GAME_TIME)

    def _slot_angle(self, i: int) -> float:
        return (self.wheel_angle + i * (360.0 / self.CLAY_COUNT)) % 360.0

    def _angular_distance(self, a: float, b: float) -> float:
        d = abs(a - b) % 360.0
        return min(d, 360.0 - d)

    def _active_index(self) -> int:
        best = 0
        best_d = self._angular_distance(self._slot_angle(0), self.MARKER_ANGLE)
        for i in range(1, self.CLAY_COUNT):
            d = self._angular_distance(self._slot_angle(i), self.MARKER_ANGLE)
            if d < best_d:
                best_d = d
                best = i
        return best

    def _is_match(self, color: int) -> bool:
        return self.super_timer > 0 or color == self.hand_color

    def _advance_wheel(self) -> None:
        self.wheel_angle = (self.wheel_angle + self._wheel_speed()) % 360.0

    def _advance_hand_color(self) -> None:
        if self.cycle_timer <= 0:
            self.hand_color = (self.hand_color + 1) % 4
            self.cycle_timer = self._cycle_interval()
        else:
            self.cycle_timer -= 1

    def _throw(self) -> bool:
        idx = self._active_index()
        color = self.clay[idx]
        if self._is_match(color):
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            mult = 3 if self.super_timer > 0 else 1
            self.score += 10 * self.combo * mult
            self.shelf.append(color)
            self.last_color = color
            if self.combo >= self.SUPER_THRESHOLD and self.super_timer <= 0:
                self.super_timer = self.SUPER_DURATION
            self.clay[idx] = self._spawn_clay()
            return True
        self.heat += self.HEAT_MISMATCH
        self.combo = 0
        self.last_color = None
        self.clay[idx] = self._spawn_clay()
        return False

    def _kiln_fire(self) -> bool:
        if len(self.shelf) == 0 or self.super_timer > 0:
            return False
        self.timer -= self.KILN_COST
        self.score += len(self.shelf) * self.KILN_BONUS_PER_POT
        self.shelf.clear()
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
            idx = self._active_index()
            blob_color = self.clay[idx]
            was_super = self.super_timer > 0
            matched = self._throw()
            bx = self.WHEEL_CX + self.WHEEL_RADIUS * math.cos(
                math.radians(self._slot_angle(idx))
            )
            by = self.WHEEL_CY + self.WHEEL_RADIUS * math.sin(
                math.radians(self._slot_angle(idx))
            )
            if matched:
                if not was_super and self.super_timer > 0:
                    self._spawn_text(160, 160, "SUPER! RAINBOW", YELLOW)
                self._spawn_burst(bx, by, self.CLAY_COLORS[blob_color], 8)
                self._spawn_text(bx, by, "+%d" % (10 * self.combo * (3 if was_super else 1)), YELLOW)
            else:
                self._spawn_burst(bx, by, RED, 6)
                self._spawn_text(bx, by, "MISS +HEAT", RED)
                self.shake = 6

        if pyxel.btnp(pyxel.KEY_F):
            pots = len(self.shelf)
            if self._kiln_fire():
                self._spawn_text(
                    40,
                    210,
                    "KILN +%d (%d pots)" % (pots * self.KILN_BONUS_PER_POT, pots),
                    ORANGE,
                )
                self._spawn_burst(40, 205, ORANGE, 6)

        self.elapsed += 1
        self._advance_wheel()
        self._advance_hand_color()
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

    def _draw_title(self) -> None:
        title = "CLAY CHAIN"
        pyxel.text(SCREEN_W // 2 - len(title) * FONT_W // 2, 50, title, YELLOW)

        names = ("RED", "LIME", "BLUE", "YELLOW")
        for i, (name, color) in enumerate(zip(names, self.CLAY_COLORS)):
            x = 60 + i * 50
            pyxel.circ(x, 90, 8, color)
            pyxel.text(x - len(name) * FONT_W // 2, 102, name, color)

        lines = (
            "THROW CLAY MATCHING YOUR HAND COLOR",
            "SPACE / CLICK: THROW THE TOP BLOB",
            "F: KILN FIRE (BAKE SHELF, COST 4s)",
            "COMBO x4 = SUPER THROW (RAINBOW)",
            "MISMATCH = CRACK + HEAT",
            "DONT OVERHEAT OR RUN OUT OF TIME",
            "",
            "ENTER: START",
        )
        for i, line in enumerate(lines):
            pyxel.text(
                SCREEN_W // 2 - len(line) * FONT_W // 2,
                126 + i * 12,
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

        # Hand color swatch + score (top-left)
        pyxel.rect(4, 14, 12, 12, self.CLAY_COLORS[self.hand_color])
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

        # Pottery wheel
        cx, cy = self.WHEEL_CX, self.WHEEL_CY
        if self.super_timer > 0:
            wheel_color = self._rainbow_color()
        else:
            wheel_color = WHITE
        pyxel.circb(cx, cy, self.WHEEL_RADIUS, wheel_color)
        pyxel.circ(cx, cy, 10, GRAY)

        # Clay blobs
        for i in range(self.CLAY_COUNT):
            a = math.radians(self._slot_angle(i))
            x = cx + self.WHEEL_RADIUS * math.cos(a)
            y = cy + self.WHEEL_RADIUS * math.sin(a)
            pyxel.circ(int(x), int(y), self.CLAY_RADIUS, self.CLAY_COLORS[self.clay[i]])

        # Marker at top (pointing down)
        mx = cx
        my = cy - self.WHEEL_RADIUS - 14
        pyxel.tri(mx - 6, my, mx + 6, my, mx, my + 10, YELLOW)

        # Shelf (completed pots) along bottom-left
        for i, c in enumerate(self.shelf):
            px = 6 + i * 12
            py = 222
            if i >= 16:
                break
            pyxel.circ(px, py, 4, self.CLAY_COLORS[c])
            pyxel.circb(px, py, 4, WHITE)
        if self.shelf:
            pyxel.text(6, 210, "SHELF %d" % len(self.shelf), WHITE)

        # SUPER indicator
        if self.super_timer > 0:
            s = "SUPER!"
            pyxel.text(
                SCREEN_W // 2 - len(s) * FONT_W // 2, 28, s, self._rainbow_color()
            )

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
