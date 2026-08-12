"""GARDEN CHAIN -- Harvest same-color plant clusters before the garden overgrows.

一番面白い瞬間: 増え続ける庭で同色の大きなクラスタを見極めて一気に収穫し、
COMBO 連鎖と SUPER HARVEST の虹色モードで次々と刈り取っていく快感。
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

# -- Screen shake --
SHAKE_DURATION = 6
SHAKE_AMPLITUDE = 2

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

    GRID_COLS = 10
    GRID_ROWS = 8
    CELL = 24
    GRID_X = 40
    GRID_Y = 24
    EMPTY = -1
    PLANT_COLORS = (RED, LIME, DARK_BLUE, YELLOW)

    MISMATCH_HEAT = 15.0
    MISS_HEAT = 5.0
    OVERGROW_HEAT = 0.03
    HEAT_DECAY = 0.02
    HEAT_CAP = 100.0

    SUPER_THRESHOLD = 4
    SUPER_DURATION = 300
    GAME_DURATION = 3600  # 60s @ 60fps
    INITIAL_PLANTS = 14
    SPREAD_CHANCE = 0.5
    POINTS_PER_PLANT = 10

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="GARDEN CHAIN", fps=FPS, display_scale=2)
        self._rng = random.Random()
        self._init_attrs()
        pyxel.run(self.update, self.draw)

    def _init_attrs(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.best_score = 0
        self.combo = 0
        self.max_combo = 0
        self.last_color: int | None = None
        self.super_active = False
        self.super_timer = 0
        self.heat = 0.0
        self.time_left = self.GAME_DURATION
        self.elapsed = 0
        self.grid = [[self.EMPTY] * self.GRID_COLS for _ in range(self.GRID_ROWS)]
        self.particles: list[Particle] = []
        self.texts: list[FloatingText] = []
        self._grow_counter = self._grow_interval()
        self._sprout_counter = self._sprout_interval()
        self._shake = 0
        self.game_over_reason = ""

    def reset(self) -> None:
        best = self.best_score
        self._init_attrs()
        self.best_score = best
        self.phase = Phase.PLAYING
        for _ in range(self.INITIAL_PLANTS):
            self._sprout()

    # -- Grid helpers --
    def _plant_count(self) -> int:
        return sum(
            1
            for row in self.grid
            for cell in row
            if cell != self.EMPTY
        )

    def _occupancy(self) -> float:
        return self._plant_count() / (self.GRID_COLS * self.GRID_ROWS)

    def _bfs_cluster(self, col: int, row: int, color: int) -> set[tuple[int, int]]:
        if not (0 <= row < self.GRID_ROWS and 0 <= col < self.GRID_COLS):
            return set()
        if self.grid[row][col] != color:
            return set()
        seen: set[tuple[int, int]] = {(col, row)}
        stack = [(col, row)]
        while stack:
            c, r = stack.pop()
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nc, nr = c + dc, r + dr
                if 0 <= nc < self.GRID_COLS and 0 <= nr < self.GRID_ROWS:
                    if (nc, nr) not in seen and self.grid[nr][nc] == color:
                        seen.add((nc, nr))
                        stack.append((nc, nr))
        return seen

    def _cell_from_xy(self, x: int, y: int) -> tuple[int, int] | None:
        col = (x - self.GRID_X) // self.CELL
        row = (y - self.GRID_Y) // self.CELL
        if 0 <= col < self.GRID_COLS and 0 <= row < self.GRID_ROWS:
            return (col, row)
        return None

    def _cell_center(self, col: int, row: int) -> tuple[float, float]:
        return (
            self.GRID_X + col * self.CELL + self.CELL / 2,
            self.GRID_Y + row * self.CELL + self.CELL / 2,
        )

    def _cluster_center(self, cluster: set[tuple[int, int]]) -> tuple[float, float]:
        xs = [self._cell_center(c, r)[0] for c, r in cluster]
        ys = [self._cell_center(c, r)[1] for c, r in cluster]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    # -- CA growth --
    def _grow(self) -> None:
        plants = [
            (c, r, self.grid[r][c])
            for r in range(self.GRID_ROWS)
            for c in range(self.GRID_COLS)
            if self.grid[r][c] != self.EMPTY
        ]
        for c, r, color in plants:
            if self._rng.random() > self.SPREAD_CHANCE:
                continue
            empties = [
                (nc, nr)
                for nc, nr in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1))
                if 0 <= nc < self.GRID_COLS
                and 0 <= nr < self.GRID_ROWS
                and self.grid[nr][nc] == self.EMPTY
            ]
            if empties:
                nc, nr = self._rng.choice(empties)
                self.grid[nr][nc] = color

    def _sprout(self) -> None:
        empties = [
            (c, r)
            for r in range(self.GRID_ROWS)
            for c in range(self.GRID_COLS)
            if self.grid[r][c] == self.EMPTY
        ]
        if not empties:
            return
        c, r = self._rng.choice(empties)
        self.grid[r][c] = self._rng.choice(self.PLANT_COLORS)

    # -- Harvest --
    def _harvest(self, col: int, row: int) -> int:
        color = self.grid[row][col]

        if color == self.EMPTY:
            self.combo = 0
            self.last_color = None
            self.heat = min(self.HEAT_CAP, self.heat + self.MISS_HEAT)
            cx, cy = self._cell_center(col, row)
            self._spawn_particles(cx, cy, GRAY, 4, 10, 10, 1.5)
            self._spawn_text(cx, cy - 6, "EMPTY!", GRAY)
            return 0

        matched = (
            self.last_color is None
            or self.super_active
            or self.last_color == color
        )

        if matched:
            self.combo += 1
        else:
            self.combo = 1
            self.heat = min(self.HEAT_CAP, self.heat + self.MISMATCH_HEAT)
            cx0, cy0 = self._cell_center(col, row)
            self._spawn_particles(cx0, cy0, RED, 4, 10, 10, 1.5)
            self._spawn_text(cx0, cy0 - 6, "WRONG!", RED)
            self._shake = SHAKE_DURATION

        self.max_combo = max(self.max_combo, self.combo)
        self.last_color = color

        cluster = self._bfs_cluster(col, row, color)
        size = len(cluster)
        for c, r in cluster:
            self.grid[r][c] = self.EMPTY

        mult = self.combo * (3 if self.super_active else 1)
        gain = size * self.POINTS_PER_PLANT * mult
        self.score += gain

        if self.combo >= self.SUPER_THRESHOLD and not self.super_active:
            self._activate_super()

        cx, cy = self._cluster_center(cluster)
        self._spawn_particles(cx, cy, color, 8, 15, 25, 1.5)
        self._spawn_text(cx, cy - 8, f"+{gain}", WHITE if self.super_active else color)
        if self.combo > 1:
            self._spawn_text(cx, cy - 20, f"COMBO x{self.combo}", YELLOW)

        return gain

    def _activate_super(self) -> None:
        self.super_active = True
        self.super_timer = self.SUPER_DURATION
        self._shake = SHAKE_DURATION
        cx = self.GRID_X + self.GRID_COLS * self.CELL / 2
        cy = self.GRID_Y + self.GRID_ROWS * self.CELL / 2
        for _ in range(20):
            color = RAINBOW[self._rng.randrange(len(RAINBOW))]
            self._spawn_particles(cx, cy, color, 1, 20, 30, 1.5)
        self._spawn_text(cx, cy - 20, "SUPER HARVEST!", YELLOW)

    # -- Heat / overgrow --
    def _update_heat(self) -> None:
        if self.heat >= self.HEAT_CAP:
            self._game_over("OVERGROWN!")
            return
        self.heat = max(0.0, self.heat - self.HEAT_DECAY)

    def _update_overgrow(self) -> None:
        if self._occupancy() >= self._overgrow_threshold():
            self.heat = min(self.HEAT_CAP, self.heat + self.OVERGROW_HEAT)

    # -- Timers --
    def _update_timers(self) -> None:
        self.time_left -= 1
        self.elapsed += 1

        self._grow_counter -= 1
        if self._grow_counter <= 0:
            self._grow()
            self._grow_counter = self._grow_interval()

        self._sprout_counter -= 1
        if self._sprout_counter <= 0:
            self._sprout()
            self._sprout_counter = self._sprout_interval()

        if self.super_active:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_active = False
                self.super_timer = 0

        self._update_particles()
        self._update_texts()

        if self.time_left <= 0:
            self._game_over("TIME UP!")

    def _grow_interval(self) -> int:
        t = min(1.0, self.elapsed / self.GAME_DURATION)
        return max(20, int(45 - 25 * t))

    def _sprout_interval(self) -> int:
        t = min(1.0, self.elapsed / self.GAME_DURATION)
        return max(35, int(60 - 25 * t))

    def _overgrow_threshold(self) -> float:
        t = min(1.0, self.elapsed / self.GAME_DURATION)
        return 0.8 - 0.2 * t

    def _game_over(self, reason: str) -> None:
        self.phase = Phase.GAME_OVER
        self.game_over_reason = reason
        if self.score > self.best_score:
            self.best_score = self.score

    # -- Particles / texts --
    def _spawn_particles(
        self,
        cx: float,
        cy: float,
        color: int,
        count: int,
        min_life: int,
        max_life: int,
        speed: float,
    ) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-speed, speed)
            vy = self._rng.uniform(-speed, speed)
            life = self._rng.randint(min_life, max_life)
            self.particles.append(Particle(cx, cy, vx, vy, life, color))

    def _spawn_text(self, cx: float, cy: float, text: str, color: int) -> None:
        self.texts.append(FloatingText(cx, cy, text, 30, color))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_texts(self) -> None:
        for t in self.texts:
            t.y -= 0.5
            t.life -= 1
        self.texts = [t for t in self.texts if t.life > 0]

    # -- Update --
    def update(self) -> None:
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            pyxel.quit()

        if self.phase == Phase.TITLE:
            if (
                pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            ):
                self.reset()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            cell = self._cell_from_xy(pyxel.mouse_x, pyxel.mouse_y)
            if cell is not None:
                self._harvest(cell[0], cell[1])

        self._update_timers()
        self._update_overgrow()
        self._update_heat()

        if self._shake > 0:
            self._shake -= 1

    # -- Draw --
    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
            return

        cam_x = cam_y = 0
        if self._shake > 0:
            cam_x = self._rng.randint(-SHAKE_AMPLITUDE, SHAKE_AMPLITUDE)
            cam_y = self._rng.randint(-SHAKE_AMPLITUDE, SHAKE_AMPLITUDE)
        pyxel.camera(cam_x, cam_y)
        self._draw_playing()
        pyxel.camera(0, 0)

    def _rainbow_color(self) -> int:
        return RAINBOW[(pyxel.frame_count // 8) % len(RAINBOW)]

    def _draw_title(self) -> None:
        title = "GARDEN CHAIN"
        pyxel.text(SCREEN_W // 2 - len(title) * FONT_W // 2, 60, title, YELLOW)

        legend = ("RED", "LIME", "BLUE", "YELLOW")
        for i, (name, color) in enumerate(zip(legend, self.PLANT_COLORS)):
            x = 76 + i * 44
            pyxel.circ(x, 100, 7, color)
            pyxel.text(x - len(name) * FONT_W // 2, 112, name, color)

        lines = (
            "CLICK TO HARVEST CLUSTERS",
            "SAME COLOR = COMBO UP",
            "COMBO x4 = SUPER HARVEST!",
            "DONT LET THE GARDEN OVERGROW!",
            "",
            "CLICK / SPACE TO START",
        )
        for i, line in enumerate(lines):
            pyxel.text(
                SCREEN_W // 2 - len(line) * FONT_W // 2,
                140 + i * 12,
                line,
                WHITE,
            )

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 24, 60, "GAME OVER", RED)
        lines = (
            self.game_over_reason,
            f"SCORE {self.score}",
            f"BEST {self.best_score}",
            f"MAX COMBO x{self.max_combo}",
            "",
            "SPACE TO RETRY",
        )
        for i, line in enumerate(lines):
            pyxel.text(
                SCREEN_W // 2 - len(line) * FONT_W // 2,
                100 + i * 14,
                line,
                WHITE,
            )

    def _draw_playing(self) -> None:
        # Score
        pyxel.text(4, 4, f"SCORE {self.score}", WHITE)

        # Combo
        if self.combo > 1:
            combo_str = f"COMBO x{self.combo}"
            combo_col = self._rainbow_color() if self.super_active else YELLOW
            pyxel.text(
                SCREEN_W // 2 - len(combo_str) * FONT_W // 2, 4, combo_str, combo_col
            )

        # SUPER indicator
        if self.super_active:
            s = f"SUPER HARVEST {self.super_timer // FPS}s"
            pyxel.text(
                SCREEN_W // 2 - len(s) * FONT_W // 2, 14, s, self._rainbow_color()
            )

        # Timer bar (horizontal, above grid)
        ratio = self.time_left / self.GAME_DURATION
        bar_w = self.GRID_COLS * self.CELL
        pyxel.rectb(self.GRID_X, 16, bar_w, 5, WHITE)
        fill = int(bar_w * ratio)
        bar_col = LIME if ratio > 0.5 else (YELLOW if ratio > 0.25 else RED)
        if fill > 0:
            pyxel.rect(self.GRID_X, 16, fill, 5, bar_col)
        pyxel.text(
            self.GRID_X + bar_w + 4,
            14,
            f"{max(0, self.time_left // FPS)}s",
            WHITE,
        )

        # HEAT bar (vertical, right side)
        hx = SCREEN_W - 16
        hy = self.GRID_Y
        hh = self.GRID_ROWS * self.CELL
        pyxel.rectb(hx, hy, 10, hh, WHITE)
        heat_ratio = self.heat / self.HEAT_CAP
        heat_fill = int(hh * heat_ratio)
        heat_col = LIME if heat_ratio < 0.5 else (YELLOW if heat_ratio < 0.75 else RED)
        if heat_fill > 0:
            pyxel.rect(hx, hy + hh - heat_fill, 10, heat_fill, heat_col)
        pyxel.text(hx, hy - 10, "HEAT", WHITE)

        # Playfield border (rainbow during super)
        border_col = self._rainbow_color() if self.super_active else BLACK
        pyxel.rectb(
            self.GRID_X - 3,
            self.GRID_Y - 3,
            self.GRID_COLS * self.CELL + 6,
            self.GRID_ROWS * self.CELL + 6,
            border_col,
        )

        # Soil + plants
        for r in range(self.GRID_ROWS):
            for c in range(self.GRID_COLS):
                x = self.GRID_X + c * self.CELL
                y = self.GRID_Y + r * self.CELL
                pyxel.rect(x + 3, y + 3, self.CELL - 6, self.CELL - 6, BROWN)
                color = self.grid[r][c]
                if color != self.EMPTY:
                    cx = x + self.CELL // 2
                    cy = y + self.CELL // 2
                    rad = 7
                    if self.super_active:
                        rad = 7 + int(math.sin(pyxel.frame_count * 0.2 + c + r))
                    pyxel.circ(cx, cy, rad, color)
                    pyxel.circ(cx - 2, cy - 2, 1, LIME)

        # Particles
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

        # Floating texts
        for t in self.texts:
            pyxel.text(int(t.x) - len(t.text) * FONT_W // 2, int(t.y), t.text, t.color)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
