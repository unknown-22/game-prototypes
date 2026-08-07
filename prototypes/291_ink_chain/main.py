"""Ink Chain — Calligraphy Brush COMBO puzzle prototype."""

from __future__ import annotations

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


INK_COLORS: tuple[int, int, int, int] = (8, 11, 5, 10)  # RED, LIME, DARK_BLUE, YELLOW

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

COLS = 10
ROWS = 8
CELL = 24
GRID_ORIGIN_X = 40
GRID_ORIGIN_Y = 24
GRID_W = COLS * CELL  # 240
GRID_H = ROWS * CELL  # 192

TIMER_FRAMES = 1800  # 60s at 30fps
HEAT_CAP = 100.0
SUPER_THRESHOLD = 4
SUPER_DURATION = 300
COLOR_CYCLE_INITIAL = 25
COLOR_CYCLE_MIN = 12
CA_INTERVAL_INITIAL = 25
CA_INTERVAL_MIN = 12
CA_SPREAD_CHANCE = 0.20
HEAT_PER_MISMATCH = 15.0
HEAT_DECAY_PER_FRAME = 0.02


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    max_life: int = 0


class Game:
    def __init__(self) -> None:
        pyxel.init(320, 240, "Ink Chain", fps=30, display_scale=2)
        self._rng = random.Random()
        self._init_attrs()
        self.reset()
        pyxel.run(self.update, self.draw)

    def _init_attrs(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.best_score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.timer: int = TIMER_FRAMES
        self.grid: list[list[int]] = [[0] * COLS for _ in range(ROWS)]
        self.color_idx: int = 0
        self.last_painted_color: int = 0
        self.super_timer: int = 0
        self._color_cycle_timer: int = COLOR_CYCLE_INITIAL
        self._ca_timer: int = CA_INTERVAL_INITIAL
        self.particles: list[Particle] = []
        self._elapsed_frames: int = 0
        self._shake_frames: int = 0
        # CA bleed visual helpers
        self._bleed_cells: list[tuple[int, int, int]] = []  # (col, row, remaining frames)
        # For replay log
        self._stroke_log: list[tuple[int, int, int]] = []  # (col, row, color)

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = TIMER_FRAMES
        self.grid = [[0] * COLS for _ in range(ROWS)]
        self.color_idx = 0
        self.last_painted_color = 0
        self.super_timer = 0
        self._color_cycle_timer = COLOR_CYCLE_INITIAL
        self._ca_timer = CA_INTERVAL_INITIAL
        self.particles = []
        self._elapsed_frames = 0
        self._shake_frames = 0
        self._bleed_cells = []
        self._stroke_log = []

    # ------------------------------------------------------------------
    # Mouse helpers
    # ------------------------------------------------------------------
    @staticmethod
    def mouse_to_grid(mx: int, my: int) -> tuple[int, int] | None:
        col = (mx - GRID_ORIGIN_X) // CELL
        row = (my - GRID_ORIGIN_Y) // CELL
        if 0 <= col < COLS and 0 <= row < ROWS:
            return col, row
        return None

    def cell_screen_xy(self, col: int, row: int) -> tuple[int, int]:
        return GRID_ORIGIN_X + col * CELL, GRID_ORIGIN_Y + row * CELL

    # ------------------------------------------------------------------
    # Core logic (testable)
    # ------------------------------------------------------------------
    def _handle_click(self, col: int, row: int) -> bool:
        if self.grid[row][col] != 0:
            return False

        ink_color = INK_COLORS[self.color_idx]
        is_mismatch = (self.last_painted_color != 0 and ink_color != self.last_painted_color and self.super_timer == 0)

        if is_mismatch:
            # Wrong color stroke
            self.heat = min(HEAT_CAP, self.heat + HEAT_PER_MISMATCH)
            self.combo = 0
            self._spawn_particles(*self.cell_center(col, row), 4, GRAY)
        else:
            # Same color (or SUPER BRUSH active)
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            multiplier = 3 if self.super_timer > 0 else 1
            self._add_score(10 * self.combo * multiplier)
            if self.super_timer > 0:
                self._spawn_particles(*self.cell_center(col, row), 16, self._rng.choice(INK_COLORS))
            else:
                self._spawn_particles(*self.cell_center(col, row), 8, ink_color)

            if self.combo >= SUPER_THRESHOLD and self.super_timer == 0:
                self.super_timer = SUPER_DURATION

        self.grid[row][col] = ink_color
        self.last_painted_color = ink_color
        self._stroke_log.append((col, row, ink_color))
        return True

    def _update_playing(self) -> None:
        self._elapsed_frames += 1
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self.phase = Phase.GAME_OVER
            if self.score > self.best_score:
                self.best_score = self.score
            return

        # Color cycle
        self._color_cycle_timer -= 1
        if self._color_cycle_timer <= 0:
            self.color_idx = (self.color_idx + 1) % 4
            pct = self._elapsed_frames / TIMER_FRAMES
            interval = int(COLOR_CYCLE_INITIAL - (COLOR_CYCLE_INITIAL - COLOR_CYCLE_MIN) * pct)
            self._color_cycle_timer = max(1, interval)

        # SUPER BRUSH decay
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer == 0:
                self.last_painted_color = 0
                self.combo = 0

        # CA bleed
        self._ca_timer -= 1
        if self._ca_timer <= 0:
            self._ca_bleed()
            pct = self._elapsed_frames / TIMER_FRAMES
            interval = int(CA_INTERVAL_INITIAL - (CA_INTERVAL_INITIAL - CA_INTERVAL_MIN) * pct)
            self._ca_timer = max(1, interval)

        # Heat decay
        self._update_heat()

        # Bleed cell animation decay
        self._bleed_cells = [(c, r, f - 1) for (c, r, f) in self._bleed_cells if f > 1]

        self._update_particles()

    def _ca_bleed(self) -> None:
        candidates: list[tuple[int, int, int]] = []
        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] != 0 and self._rng.random() < CA_SPREAD_CHANCE:
                    candidates.append((c, r, self.grid[r][c]))

        self._rng.shuffle(candidates)
        for cx, cy, color in candidates:
            dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
            self._rng.shuffle(dirs)
            for dx, dy in dirs:
                nx, ny = cx + dx, cy + dy
                if 0 <= ny < ROWS and 0 <= nx < COLS and self.grid[ny][nx] == 0:
                    self.grid[ny][nx] = color
                    self._bleed_cells.append((nx, ny, 3))
                    break

    def _update_heat(self) -> None:
        if self.heat >= HEAT_CAP:
            self.phase = Phase.GAME_OVER
            self._shake_frames = 15
            if self.score > self.best_score:
                self.best_score = self.score
            return
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY_PER_FRAME)

    def _add_score(self, base_points: int) -> None:
        if isinstance(base_points, int) and base_points > 0:
            self.score += base_points

    def _spawn_particles(self, x: int, y: int, count: int, color: int) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-1.5, 1.5)
            vy = self._rng.uniform(-1.5, 1.5)
            life = self._rng.randint(15, 25)
            self.particles.append(Particle(float(x), float(y), vx, vy, life, color, life))

    def cell_center(self, col: int, row: int) -> tuple[int, int]:
        return (
            GRID_ORIGIN_X + col * CELL + CELL // 2,
            GRID_ORIGIN_Y + row * CELL + CELL // 2,
        )

    def _update_particles(self) -> None:
        updated: list[Particle] = []
        for p in self.particles:
            p.vy += 0.08  # gravity
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                updated.append(p)
        self.particles = updated

    # ------------------------------------------------------------------
    # Pyxel update
    # ------------------------------------------------------------------
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
        elif self.phase == Phase.PLAYING:
            self._handle_input_playing()
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            if self._shake_frames > 0:
                self._shake_frames -= 1
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()

    def _handle_input_playing(self) -> None:
        # Keyboard color select
        if pyxel.btnp(pyxel.KEY_1):
            self.color_idx = 0
        elif pyxel.btnp(pyxel.KEY_2):
            self.color_idx = 1
        elif pyxel.btnp(pyxel.KEY_3):
            self.color_idx = 2
        elif pyxel.btnp(pyxel.KEY_4):
            self.color_idx = 3

        # Mouse click paint
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            cell = self.mouse_to_grid(pyxel.mouse_x, pyxel.mouse_y)
            if cell is not None:
                self._handle_click(*cell)

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------
    def draw(self) -> None:
        if self._shake_frames > 0:
            sx = self._rng.randint(-3, 3)
            sy = self._rng.randint(-3, 3)
            pyxel.camera(sx, sy)
        else:
            pyxel.camera(0, 0)

        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.PLAYING, Phase.GAME_OVER):
            self._draw_grid()
            self._draw_brush_cursor()
            self._draw_bleed_highlights()
            self._draw_hud()
            self._draw_particles()
            if self.super_timer > 0 and self.phase == Phase.PLAYING:
                self._draw_super_border()
            if self.phase == Phase.GAME_OVER:
                self._draw_game_over_overlay()

    # ---- Title ----
    def _draw_title(self) -> None:
        pyxel.text(120, 80, "INK CHAIN", WHITE)
        pyxel.text(145, 92, "(Calligraphy Brush COMBO)", LIGHT_BLUE)
        pyxel.text(125, 120, "Click to Start", WHITE)
        pyxel.text(82, 140, "Same-color COMBO -> SUPER BRUSH!", GREEN)
        pyxel.text(110, 160, "1-4 Keys: Pick Color", YELLOW)
        pyxel.text(95, 180, "Wrong color = HEAT -> Game Over", ORANGE)

    # ---- Grid ----
    def _draw_grid(self) -> None:
        # Grid background
        for r in range(ROWS):
            for c in range(COLS):
                x = GRID_ORIGIN_X + c * CELL
                y = GRID_ORIGIN_Y + r * CELL
                cell_color = self.grid[r][c]
                if cell_color == 0:
                    pyxel.rectb(x, y, CELL, CELL, DARK_BLUE)
                else:
                    pyxel.rect(x + 1, y + 1, CELL - 2, CELL - 2, cell_color)

    def _draw_brush_cursor(self) -> None:
        cell = self.mouse_to_grid(pyxel.mouse_x, pyxel.mouse_y)
        if cell is None:
            return
        col, row = cell
        if self.grid[row][col] != 0:
            return
        x = GRID_ORIGIN_X + col * CELL
        y = GRID_ORIGIN_Y + row * CELL
        ink_color = INK_COLORS[self.color_idx]
        pyxel.rectb(x + 1, y + 1, CELL - 2, CELL - 2, ink_color)
        pyxel.rectb(x + 2, y + 2, CELL - 4, CELL - 4, ink_color)
        # Small ink indicator
        pyxel.rect(x + CELL - 7, y + 2, 4, 4, ink_color)

    def _draw_bleed_highlights(self) -> None:
        for col, row, _ in self._bleed_cells:
            x = GRID_ORIGIN_X + col * CELL
            y = GRID_ORIGIN_Y + row * CELL
            color = self.grid[row][col]
            # draw lighter overlay
            pyxel.rectb(x + 1, y + 1, CELL - 2, CELL - 2, YELLOW if color != YELLOW else WHITE)

    # ---- HUD ----
    def _draw_hud(self) -> None:
        # Timer bar (top)
        bar_w = int(280 * (self.timer / TIMER_FRAMES))
        if bar_w > 0:
            pct = self.timer / TIMER_FRAMES
            if pct > 0.5:
                tcolor = CYAN
            elif pct > 0.25:
                tcolor = YELLOW
            else:
                tcolor = RED
            pyxel.rect(20, 8, bar_w, 6, tcolor)
        pyxel.rectb(20, 8, 280, 6, WHITE)
        pyxel.text(14, 9, "T", WHITE)

        # Score
        pyxel.text(6, 18, f"SCORE: {self.score}", WHITE)
        # Combo
        combo_color = YELLOW if self.combo >= SUPER_THRESHOLD else WHITE
        pyxel.text(6, 28, f"COMBO: {self.combo}", combo_color)
        # Timer text
        pyxel.text(252, 18, str(self.timer // 30), WHITE)
        # Ink indicator HUD
        pyxel.text(200, 28, "INK:", WHITE)
        pyxel.rect(226, 28, 8, 8, INK_COLORS[self.color_idx])

        # Heat bar (bottom)
        heat_w = int(280 * (self.heat / HEAT_CAP))
        if heat_w > 0:
            heat_pct = self.heat / HEAT_CAP
            if heat_pct < 0.33:
                hcolor = GREEN
            elif heat_pct < 0.66:
                hcolor = YELLOW
            else:
                hcolor = RED
            pyxel.rect(20, 216, heat_w, 12, hcolor)
        pyxel.rectb(20, 216, 280, 12, WHITE)
        # HEAT label
        for i, ch in enumerate("HEAT"):
            pyxel.text(5 + i * 4, 218, ch, RED)

        # SUPER BRUSH indicator
        if self.super_timer > 0:
            pyxel.text(140, 222, "SUPER!", YELLOW)

        # Best score
        pyxel.text(280, 18, f"BEST:{self.best_score}", LIGHT_BLUE)

    def _draw_super_border(self) -> None:
        # Rainbow flashing border around canvas
        colors = [RED, LIME, DARK_BLUE, YELLOW]
        idx = (pyxel.frame_count // 10) % 4
        c = colors[idx]
        # Top-left / Top-right / Bottom-left / Bottom-right
        gx = GRID_ORIGIN_X
        gy = GRID_ORIGIN_Y
        gw = GRID_W
        gh = GRID_H
        pyxel.rectb(gx - 1, gy - 1, gw + 2, gh + 2, c)
        pyxel.rectb(gx - 2, gy - 2, gw + 4, gh + 4, c)

    # ---- Game Over Overlay ----
    def _draw_game_over_overlay(self) -> None:
        pyxel.rect(90, 70, 140, 60, BLACK)
        pyxel.rectb(90, 70, 140, 60, WHITE)
        pyxel.text(130, 78, "GAME OVER", RED)
        pyxel.text(107, 94, f"Score: {self.score}  Best: {self.best_score}", WHITE)
        pyxel.text(118, 110, "Click to Retry", YELLOW)

    # ---- Particles ----
    def _draw_particles(self) -> None:
        for p in self.particles:
            ratio = p.life / max(1, p.max_life)
            if ratio < 0.3:
                continue
            c = p.color
            pyxel.pset(int(p.x), int(p.y), c)


if __name__ == "__main__":
    Game()
