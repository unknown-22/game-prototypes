"""HONEY CHAIN -- beekeeping / pollination combo game.

一番面白い瞬間: 同じ色の花を次々に辿ってCOMBOを重ね、SUPER POLLENで虹色に咲き乱れる
花畑を一気に塗り替えるのが面白い。間違った色の花を横切るとコンボが切れて熱が上がるので、
危険を避けて遠回りするか、欲張って突っ切るか迷う駆け引きが面白い。
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

# Flower colors (index 0..3)
FLOWER_COLORS: tuple[int, int, int, int] = (RED, LIME, DARK_BLUE, YELLOW)


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Flower:
    col: int
    row: int
    color: int  # one of FLOWER_COLORS


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

    # Grid layout
    COLS = 10
    ROWS = 8
    CELL = 24
    OX = 40
    OY = 36

    # Bee
    BEE_SPEED = 2.0
    BEE_R = 7
    COLLIDE_RADIUS = 13

    # Heat / combo / super
    HEAT_MAX = 100
    HEAT_DECAY = 0.02
    HEAT_MISMATCH = 15
    SUPER_DURATION = 300
    COMBO_SUPER_THRESHOLD = 4
    SUPER_MULT = 3

    # Timing
    GAME_DURATION = 3600  # 60 seconds

    # Flower spawning / CA
    MAX_FLOWERS = 16
    MAX_FLOWERS_START = 10
    SPAWN_INTERVAL = 60
    SPAWN_INTERVAL_END = 30
    CA_INTERVAL = 45
    CA_INTERVAL_END = 20
    CA_CHANCE = 0.25
    INITIAL_FLOWERS = 6

    # Particles
    GRAVITY = 0.05

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="HONEY CHAIN", fps=FPS, display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.rng: random.Random = random.Random()
        self.phase = Phase.TITLE
        self.score = 0
        self.best_score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat: float = 0.0
        self.timer: int = self.GAME_DURATION
        self.elapsed: int = 0
        self.super_mode = False
        self.super_timer: int = 0
        self.bee_x: float = self.OX + self.COLS * self.CELL / 2
        self.bee_y: float = self.OY + self.ROWS * self.CELL / 2
        self.pollen_color: int | None = None
        self.flowers: list[Flower] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.chain_log: list[int] = []
        self.spawn_timer: int = self.SPAWN_INTERVAL
        self.ca_timer: int = self.CA_INTERVAL
        self.game_over_reason: str = ""
        self.shake: int = 0
        for _ in range(self.INITIAL_FLOWERS):
            self._spawn_flower()

    # -- Geometry / grid helpers --
    def _make_grid_pos(self, col: int, row: int) -> tuple[int, int]:
        return (
            self.OX + col * self.CELL + self.CELL // 2,
            self.OY + row * self.CELL + self.CELL // 2,
        )

    def _empty_cells(self) -> list[tuple[int, int]]:
        occupied = {(f.col, f.row) for f in self.flowers}
        return [
            (c, r)
            for r in range(self.ROWS)
            for c in range(self.COLS)
            if (c, r) not in occupied
        ]

    def _flower_at(self, col: int, row: int) -> Flower | None:
        for f in self.flowers:
            if f.col == col and f.row == row:
                return f
        return None

    # -- Difficulty interpolation (linear by elapsed) --
    def _max_flowers(self) -> int:
        return int(
            self.MAX_FLOWERS_START
            + (self.MAX_FLOWERS - self.MAX_FLOWERS_START)
            * (self.elapsed / self.GAME_DURATION)
        )

    def _spawn_interval(self) -> int:
        return int(
            self.SPAWN_INTERVAL
            + (self.SPAWN_INTERVAL_END - self.SPAWN_INTERVAL)
            * (self.elapsed / self.GAME_DURATION)
        )

    def _ca_interval(self) -> int:
        return int(
            self.CA_INTERVAL
            + (self.CA_INTERVAL_END - self.CA_INTERVAL)
            * (self.elapsed / self.GAME_DURATION)
        )

    # -- Spawning --
    def _spawn_flower(self) -> None:
        if len(self.flowers) >= self._max_flowers():
            return
        empty = self._empty_cells()
        if not empty:
            return
        col, row = self.rng.choice(empty)
        self.flowers.append(Flower(col, row, self.rng.choice(FLOWER_COLORS)))

    def _update_ca_spread(self) -> None:
        if len(self.flowers) >= self._max_flowers():
            return
        for flower in list(self.flowers):
            if self.rng.random() >= self.CA_CHANCE:
                continue
            candidates: list[tuple[int, int]] = []
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nc, nr = flower.col + dc, flower.row + dr
                if 0 <= nc < self.COLS and 0 <= nr < self.ROWS and self._flower_at(nc, nr) is None:
                    candidates.append((nc, nr))
            if candidates:
                nc, nr = self.rng.choice(candidates)
                self.flowers.append(Flower(nc, nr, flower.color))
                if len(self.flowers) >= self._max_flowers():
                    break

    # -- Collection / matching --
    def _try_collect(self, flower: Flower) -> bool:
        was_super = self.super_mode
        matched = (
            self.super_mode
            or self.pollen_color is None
            or flower.color == self.pollen_color
        )
        fx, fy = self._make_grid_pos(flower.col, flower.row)
        if matched:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            mult = self.SUPER_MULT if self.super_mode else 1
            gained = 10 * self.combo * mult
            self.score += gained
            self.chain_log.append(flower.color)
            if len(self.chain_log) > 20:
                self.chain_log.pop(0)
            if self.super_mode:
                self._spawn_super_particles(fx, fy)
            else:
                self._spawn_match_particles(fx, fy, flower.color)
            self._spawn_text(fx, fy - 12, "+%d" % gained, YELLOW)
            if self.combo >= self.COMBO_SUPER_THRESHOLD:
                if not was_super:
                    self._spawn_text(self.bee_x, self.bee_y - 22, "SUPER POLLEN!", PINK)
                self.super_mode = True
                self.super_timer = self.SUPER_DURATION
        else:
            self.heat += self.HEAT_MISMATCH
            self.combo = 0
            self.chain_log.clear()
            self._spawn_mismatch_particles(fx, fy)
            self._spawn_text(fx, fy - 12, "WRONG!", RED)
            self.shake = 6
        self.pollen_color = flower.color
        self.flowers.remove(flower)
        return matched

    # -- Bee movement --
    def _update_bee(self, dx: float, dy: float) -> None:
        if dx != 0.0 or dy != 0.0:
            length = math.hypot(dx, dy)
            self.bee_x += dx / length * self.BEE_SPEED
            self.bee_y += dy / length * self.BEE_SPEED
        self.bee_x = min(
            max(self.bee_x, self.OX + self.BEE_R),
            self.OX + self.COLS * self.CELL - self.BEE_R,
        )
        self.bee_y = min(
            max(self.bee_y, self.OY + self.BEE_R),
            self.OY + self.ROWS * self.CELL - self.BEE_R,
        )
        for flower in list(self.flowers):
            fx, fy = self._make_grid_pos(flower.col, flower.row)
            if math.hypot(self.bee_x - fx, self.bee_y - fy) <= self.COLLIDE_RADIUS:
                self._try_collect(flower)

    # -- Timer / heat --
    def _update_timer(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self.phase = Phase.GAME_OVER

    def _update_heat(self) -> None:
        if self.heat >= self.HEAT_MAX:
            self.phase = Phase.GAME_OVER
            return
        if self.super_mode:
            return
        self.heat = max(0.0, self.heat - self.HEAT_DECAY)

    def _game_over_reason(self) -> str:
        return "HEAT" if self.heat >= self.HEAT_MAX else "TIME"

    # -- Particles / floating texts --
    def _spawn_match_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(8):
            angle = self.rng.uniform(0.0, 2.0 * math.pi)
            speed = self.rng.uniform(1.0, 2.5)
            life = self.rng.randint(20, 35)
            self.particles.append(
                Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed, life, color)
            )

    def _spawn_super_particles(self, x: float, y: float) -> None:
        for _ in range(20):
            angle = self.rng.uniform(0.0, 2.0 * math.pi)
            speed = self.rng.uniform(1.0, 2.5)
            life = self.rng.randint(20, 35)
            color = self.rng.choice(RAINBOW)
            self.particles.append(
                Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed, life, color)
            )

    def _spawn_mismatch_particles(self, x: float, y: float) -> None:
        for _ in range(4):
            angle = self.rng.uniform(0.0, 2.0 * math.pi)
            speed = self.rng.uniform(1.0, 2.0)
            life = self.rng.randint(15, 25)
            self.particles.append(
                Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed, life, GRAY)
            )

    def _spawn_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x, y, text, 30, color))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.vy += self.GRAVITY
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
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.PLAYING
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.PLAYING
            return

        dx = 0.0
        dy = 0.0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx -= 1.0
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx += 1.0
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy -= 1.0
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy += 1.0
        self._update_bee(dx, dy)

        self.elapsed += 1
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self._spawn_flower()
            self.spawn_timer = self._spawn_interval()
        self.ca_timer -= 1
        if self.ca_timer <= 0:
            self._update_ca_spread()
            self.ca_timer = self._ca_interval()

        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0

        self._update_timer()
        self._update_heat()
        self._update_particles()
        self._update_floating_texts()

        if self.phase == Phase.GAME_OVER:
            self.game_over_reason = self._game_over_reason()
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
            pyxel.camera(self.rng.randint(-2, 2), self.rng.randint(-2, 2))
            self.shake -= 1
        else:
            pyxel.camera(0, 0)
        self._draw_playing()
        pyxel.camera(0, 0)

    def _rainbow_color(self) -> int:
        return RAINBOW[(pyxel.frame_count // 8) % len(RAINBOW)]

    def _draw_title(self) -> None:
        title = "HONEY CHAIN"
        pyxel.text(SCREEN_W // 2 - len(title) * FONT_W // 2, 50, title, YELLOW)

        for i, color in enumerate(FLOWER_COLORS):
            x = 70 + i * 48
            pyxel.circ(x, 90, 8, color)
            pyxel.circ(x, 90, 3, NAVY)

        lines = (
            "STEER THE BEE THROUGH THE FLOWERS",
            "TOUCH SAME-COLOR FLOWERS TO POLLINATE",
            "CHAIN SAME COLORS TO BUILD A COMBO",
            "WRONG COLOR = COMBO LOST + HEAT UP",
            "COMBO x4 = SUPER POLLEN (RAINBOW x3)",
            "HEAT UP OR TIME UP = GAME OVER",
            "",
            "ARROWS / WASD: MOVE",
            "SPACE: START",
        )
        for i, line in enumerate(lines):
            pyxel.text(
                SCREEN_W // 2 - len(line) * FONT_W // 2,
                110 + i * 12,
                line,
                WHITE,
            )

    def _draw_game_over(self) -> None:
        title = "GAME OVER"
        pyxel.text(SCREEN_W // 2 - len(title) * FONT_W // 2, 60, title, RED)
        reason = "CAUSE: %s" % self.game_over_reason
        lines = (
            reason,
            "SCORE %d" % self.score,
            "BEST %d" % self.best_score,
            "MAX COMBO x%d" % self.max_combo,
            "",
            "SPACE: RETRY",
        )
        for i, line in enumerate(lines):
            pyxel.text(
                SCREEN_W // 2 - len(line) * FONT_W // 2,
                100 + i * 14,
                line,
                WHITE,
            )

    def _draw_playing(self) -> None:
        # Grid
        for r in range(self.ROWS):
            for c in range(self.COLS):
                pyxel.rectb(
                    self.OX + c * self.CELL, self.OY + r * self.CELL, self.CELL, self.CELL, NAVY
                )

        # Timer bar (across top)
        ratio = self.timer / self.GAME_DURATION
        bar_w = SCREEN_W - 8
        pyxel.rectb(4, 4, bar_w, 6, WHITE)
        fill = int(bar_w * ratio)
        tcol = LIME if ratio > 0.5 else (YELLOW if ratio > 0.25 else RED)
        if fill > 0:
            pyxel.rect(4, 4, fill, 6, tcol)

        # Score (top-left)
        pyxel.text(4, 14, "SCORE %d" % self.score, WHITE)

        # Combo (top-center)
        combo_str = "COMBO x%d" % self.combo
        pyxel.text(SCREEN_W // 2 - len(combo_str) * FONT_W // 2, 14, combo_str, YELLOW)

        # HEAT bar (vertical right side)
        hx = SCREEN_W - 16
        hy = 30
        hh = 180
        pyxel.rectb(hx, hy, 10, hh, WHITE)
        hr = self.heat / self.HEAT_MAX
        hfill = int(hh * hr)
        hcol = LIME if hr < 0.5 else (YELLOW if hr < 0.75 else RED)
        if hfill > 0:
            pyxel.rect(hx, hy + hh - hfill, 10, hfill, hcol)
        pyxel.text(hx - 4, hy - 8, "HEAT", WHITE)

        # Flowers
        for f in self.flowers:
            x, y = self._make_grid_pos(f.col, f.row)
            pyxel.circ(x, y, 8, f.color)
            pyxel.circ(x, y, 3, NAVY)
            if self.super_mode:
                pyxel.circb(x, y, 9, self._rainbow_color())

        # Bee
        bx, by = int(self.bee_x), int(self.bee_y)
        if self.super_mode:
            pyxel.circb(bx, by, self.BEE_R + 2, self._rainbow_color())
        pyxel.circ(bx, by, self.BEE_R, WHITE)
        pyxel.circ(bx, by, 3, self.pollen_color if self.pollen_color is not None else GRAY)

        # Honeycomb log (bottom strip)
        for i, color in enumerate(self.chain_log):
            if i >= 20:
                break
            pyxel.circ(8 + i * 8, SCREEN_H - 6, 3, color)

        # SUPER indicator
        if self.super_mode:
            s = "SUPER!"
            pyxel.text(SCREEN_W // 2 - len(s) * FONT_W // 2, 26, s, self._rainbow_color())

        # Particles
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

        # Floating texts
        for t in self.floating_texts:
            pyxel.text(int(t.x) - len(t.text) * FONT_W // 2, int(t.y), t.text, t.color)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
