from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

WIDTH = 320
HEIGHT = 240

COLS = 6
ROWS = 4
SLOTS = COLS * ROWS
CELL = 36
TRAY_X = 40
TRAY_Y = 64

MIN_BALLS = 8
SUPER_FRAMES = 300
TIME_LIMIT = 3600
MAX_HEAT = 100.0

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

DOUGH_COLORS = (RED, LIME, DARK_BLUE, YELLOW)
RAINBOW = (RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK)


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Dough:
    color: int  # 0..3 (index into DOUGH_COLORS)
    rise: float  # 0.0 .. 1.0


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
        pyxel.init(WIDTH, HEIGHT, title="BAKE CHAIN")
        self.best_score = 0
        self.phase = Phase.TITLE
        self.reset()
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------ setup

    def reset(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = TIME_LIMIT
        self.elapsed = 0
        self.oven_color = 0
        self.grid: list[Dough | None] = [None] * SLOTS
        self.mold: list[bool] = [False] * SLOTS
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self.shake = 0
        self.rng = random.Random()
        self.cycle_timer = self._cycle_interval()
        self.spawn_timer = self._spawn_interval()
        self.mold_timer = self._mold_interval()
        self.super_timer = 0
        for _ in range(MIN_BALLS):
            self._spawn_ball()

    # ------------------------------------------------------- testable logic

    def _cycle_interval(self) -> int:
        return max(12, 20 - self.elapsed // 120)

    def _spawn_interval(self) -> int:
        return max(25, 60 - self.elapsed // 90)

    def _mold_interval(self) -> int:
        return max(40, 90 - self.elapsed // 60)

    def _rise_rate(self) -> float:
        return 0.0035 + (self.elapsed / 3600.0) * 0.0025

    def _max_balls(self) -> int:
        return min(14, 8 + self.elapsed // 180)

    def _value_mult(self, rise: float) -> int:
        return min(3, 1 + int(rise * 3))

    def _count_dough(self) -> int:
        return sum(1 for d in self.grid if d is not None)

    def _slot_center(self, index: int) -> tuple[int, int]:
        row, col = divmod(index, COLS)
        return (
            TRAY_X + col * CELL + CELL // 2,
            TRAY_Y + row * CELL + CELL // 2,
        )

    def _neighbors(self, index: int) -> list[int]:
        row, col = divmod(index, COLS)
        result: list[int] = []
        if row > 0:
            result.append(index - COLS)
        if row < ROWS - 1:
            result.append(index + COLS)
        if col > 0:
            result.append(index - 1)
        if col < COLS - 1:
            result.append(index + 1)
        return result

    def _slot_at(self, x: int, y: int) -> int | None:
        if x < TRAY_X or y < TRAY_Y:
            return None
        col = (x - TRAY_X) // CELL
        row = (y - TRAY_Y) // CELL
        if 0 <= col < COLS and 0 <= row < ROWS:
            return row * COLS + col
        return None

    def _spawn_ball(self) -> bool:
        empty = [i for i in range(SLOTS) if self.grid[i] is None and not self.mold[i]]
        if not empty:
            return False
        idx = self.rng.choice(empty)
        self.grid[idx] = Dough(color=self.rng.randrange(4), rise=0.0)
        return True

    def _advance_rise(self) -> int:
        rate = self._rise_rate()
        collapsed = 0
        for i in range(SLOTS):
            d = self.grid[i]
            if d is None:
                continue
            d.rise += rate
            if d.rise >= 1.0:
                self.grid[i] = None
                self.mold[i] = True
                self.heat += 10
                self.combo = 0
                self._spawn_collapse_particles(i)
                collapsed += 1
        return collapsed

    def _update_oven_color(self) -> None:
        self.cycle_timer -= 1
        if self.cycle_timer <= 0:
            self.cycle_timer = self._cycle_interval()
            self.oven_color = (self.oven_color + 1) % 4

    def _bake(self, index: int) -> bool:
        d = self.grid[index]
        if d is None:
            return False
        cx, cy = self._slot_center(index)
        if self.super_timer > 0 or d.color == self.oven_color:
            mult = self._value_mult(d.rise)
            gain = 10 * self.combo * mult
            if self.super_timer > 0:
                gain *= 3
            self.score += gain
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            self.grid[index] = None
            self._spawn_match_particles(index, DOUGH_COLORS[d.color])
            self.floats.append(FloatingText(cx, cy, f"+{gain}", 30, WHITE))
            if self.combo >= 2:
                self.floats.append(
                    FloatingText(cx, cy - 12, f"COMBO x{self.combo}", 40, YELLOW)
                )
            if self.combo >= 4 and self.super_timer == 0:
                self._activate_super()
            return True
        self.heat += 15
        self.combo = 0
        self.grid[index] = None
        self._spawn_mismatch_particles(index)
        self.floats.append(FloatingText(cx, cy, "WRONG!", 30, RED))
        self.shake = 8
        return False

    def _activate_super(self) -> None:
        self.super_timer = SUPER_FRAMES
        self.mold = [False] * SLOTS
        self._spawn_super_particles()
        self.floats.append(
            FloatingText(WIDTH // 2, HEIGHT // 2 - 10, "SUPER BAKE!", 60, WHITE)
        )

    def _spread_mold(self) -> int:
        self.mold_timer -= 1
        if self.mold_timer > 0:
            return 0
        self.mold_timer = self._mold_interval()
        changed = 0
        snapshot = [i for i in range(SLOTS) if self.mold[i]]
        for idx in snapshot:
            for n in self._neighbors(idx):
                if self.mold[n]:
                    continue
                if self.grid[n] is not None:
                    self.grid[n] = None
                    self.heat += 5
                    changed += 1
                else:
                    self.mold[n] = True
                    changed += 1
        return changed

    def _update_heat(self) -> None:
        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER
            self.best_score = max(self.best_score, self.score)
            return
        if self.super_timer == 0:
            self.heat = max(0.0, self.heat - 0.02)

    def _update_spawns(self) -> None:
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_timer = self._spawn_interval()
            if self._count_dough() < self._max_balls():
                self._spawn_ball()

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floats(self) -> None:
        for f in self.floats:
            f.life -= 1
        self.floats = [f for f in self.floats if f.life > 0]

    # ------------------------------------------------------------ particles

    def _spawn_match_particles(self, index: int, color: int) -> None:
        cx, cy = self._slot_center(index)
        for _ in range(8):
            ang = self.rng.uniform(0.0, math.tau)
            spd = self.rng.uniform(0.5, 1.5)
            self.particles.append(
                Particle(
                    cx, cy, math.cos(ang) * spd, math.sin(ang) * spd,
                    self.rng.randint(15, 30), color,
                )
            )

    def _spawn_mismatch_particles(self, index: int) -> None:
        cx, cy = self._slot_center(index)
        for _ in range(4):
            ang = self.rng.uniform(0.0, math.tau)
            spd = self.rng.uniform(0.5, 1.5)
            self.particles.append(
                Particle(
                    cx, cy, math.cos(ang) * spd, math.sin(ang) * spd,
                    self.rng.randint(15, 30), RED,
                )
            )

    def _spawn_collapse_particles(self, index: int) -> None:
        cx, cy = self._slot_center(index)
        for _ in range(6):
            ang = self.rng.uniform(0.0, math.tau)
            spd = self.rng.uniform(0.3, 0.8)
            self.particles.append(
                Particle(
                    cx, cy, math.cos(ang) * spd, math.sin(ang) * spd,
                    self.rng.randint(15, 30), GRAY,
                )
            )

    def _spawn_super_particles(self) -> None:
        for i in range(24):
            color = RAINBOW[i % len(RAINBOW)]
            ang = self.rng.uniform(0.0, math.tau)
            spd = self.rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    WIDTH / 2, HEIGHT / 2,
                    math.cos(ang) * spd, math.sin(ang) * spd,
                    self.rng.randint(30, 60), color,
                )
            )

    # ------------------------------------------------------------- update

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        else:
            self._update_gameover()

    def _update_title(self) -> None:
        if (
            pyxel.btnp(pyxel.KEY_SPACE)
            or pyxel.btnp(pyxel.KEY_RETURN)
            or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
        ):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self.elapsed += 1
        self.timer -= 1
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            idx = self._slot_at(pyxel.mouse_x, pyxel.mouse_y)
            if idx is not None:
                self._bake(idx)
        self._update_oven_color()
        self._advance_rise()
        self._update_spawns()
        self._spread_mold()
        self._update_heat()
        if self.timer <= 0 and self.phase == Phase.PLAYING:
            self.phase = Phase.GAME_OVER
            self.best_score = max(self.best_score, self.score)
        self._update_particles()
        self._update_floats()
        if self.super_timer > 0:
            self.super_timer -= 1
        if self.shake > 0:
            self.shake -= 1

    def _update_gameover(self) -> None:
        if (
            pyxel.btnp(pyxel.KEY_SPACE)
            or pyxel.btnp(pyxel.KEY_RETURN)
            or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
        ):
            self.reset()
            self.phase = Phase.PLAYING

    # --------------------------------------------------------------- draw

    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        else:
            self._draw_gameover()

    def _draw_title(self) -> None:
        pyxel.cls(NAVY)
        pyxel.text(96, 60, "BAKE CHAIN", WHITE)
        pyxel.text(128, 76, "Bakery", YELLOW)
        pyxel.text(78, 110, "CLICK matching dough", WHITE)
        pyxel.text(72, 122, "COMBO>=4 = SUPER BAKE", LIME)
        pyxel.text(104, 150, "SPACE to start", CYAN)
        for i, c in enumerate(DOUGH_COLORS):
            pyxel.circ(80 + i * 40, 180, 8, c)

    def _draw_playing(self) -> None:
        ox = oy = 0
        if self.shake > 0:
            ox = self.rng.randint(-3, 3)
            oy = self.rng.randint(-3, 3)
        pyxel.cls(NAVY)
        for i in range(SLOTS):
            row, col = divmod(i, COLS)
            x = TRAY_X + col * CELL
            y = TRAY_Y + row * CELL
            if self.mold[i]:
                pyxel.rect(x + ox, y + oy, CELL, CELL, GRAY)
                pyxel.line(x + ox, y + oy, x + CELL + ox, y + CELL + oy, BLACK)
                pyxel.line(x + CELL + ox, y + oy, x + ox, y + CELL + oy, BLACK)
            else:
                pyxel.rectb(x + ox, y + oy, CELL, CELL, BROWN)
            d = self.grid[i]
            if d is not None:
                cx = x + CELL // 2 + ox
                cy = y + CELL // 2 + oy
                r = 8 + int(d.rise * 8)
                pyxel.circ(cx, cy, r, DOUGH_COLORS[d.color])
                if d.rise >= 0.66:
                    pyxel.circ(cx, cy, max(2, r // 3), WHITE)
        self._draw_oven_bar()
        self._draw_heat_bar()
        self._draw_timer_bar()
        self._draw_hud()
        for p in self.particles:
            pyxel.rect(int(p.x + ox), int(p.y + oy), 2, 2, p.color)
        for f in self.floats:
            pyxel.text(f.x + ox, f.y + oy, f.text, f.color)
        if self.super_timer > 0:
            self._draw_super_border()

    def _draw_oven_bar(self) -> None:
        pyxel.text(146, 6, "OVEN", WHITE)
        pyxel.rect(150, 20, 20, 14, DOUGH_COLORS[self.oven_color])

    def _draw_heat_bar(self) -> None:
        bx = 312
        by = 64
        bh = 160
        pyxel.rectb(bx, by, 6, bh, WHITE)
        h = int(bh * min(1.0, self.heat / 100.0))
        if self.heat < 33:
            color = GREEN
        elif self.heat < 66:
            color = YELLOW
        else:
            color = RED
        pyxel.rect(bx + 1, by + bh - h, 4, h, color)

    def _draw_timer_bar(self) -> None:
        tw = int(120 * max(0, self.timer) / TIME_LIMIT)
        pyxel.rectb(8, 24, 122, 6, WHITE)
        pyxel.rect(9, 25, tw, 4, CYAN)

    def _draw_hud(self) -> None:
        pyxel.text(8, 8, f"SCORE {self.score}", WHITE)
        pyxel.text(8, 224, f"COMBO x{self.combo}", YELLOW)
        if self.super_timer > 0:
            pyxel.text(8, 236, "SUPER", LIME)

    def _draw_super_border(self) -> None:
        c = RAINBOW[(pyxel.frame_count // 4) % len(RAINBOW)]
        pyxel.rectb(0, 0, WIDTH, HEIGHT, c)

    def _draw_gameover(self) -> None:
        pyxel.cls(NAVY)
        if self.heat >= MAX_HEAT:
            pyxel.text(120, 80, "OVEN FIRE!", RED)
        else:
            pyxel.text(124, 80, "TIME UP!", WHITE)
        pyxel.text(120, 110, f"SCORE {self.score}", WHITE)
        pyxel.text(116, 122, f"BEST {self.best_score}", YELLOW)
        pyxel.text(112, 150, "SPACE to retry", CYAN)


if __name__ == "__main__":
    Game()
