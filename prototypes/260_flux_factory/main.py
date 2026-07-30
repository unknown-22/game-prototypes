"""FLUX FACTORY — Conveyor belt factory routing puzzle.

Core fun moment: Same-color items converge at a junction and SYNTHESIZE
into a higher-value product, triggering a chain reaction of combos.

Risk/Reward: Route same-color items to junctions for COMBO + high scores,
but more items on belts = higher chance of color collision = HEAT.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ──────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
FPS = 30
GAME_TIME = 60  # seconds
TOTAL_FRAMES = GAME_TIME * FPS  # 1800

# Grid
COLS = 6
ROWS = 5
CELL = 40
GRID_X = 40
GRID_Y = 20
INITIAL_SPAWN_DELAY = 60  # first 60f: no items spawn (time to build belts)

# Direction constants
EMPTY = -1
N = 0
E = 1
S = 2
W = 3
JUNCTION = 4

DIRECTION_NAMES = ("N", "E", "S", "W", "J")

# Item colors (Pyxel palette integers)
ITEM_COLORS = (pyxel.COLOR_RED, pyxel.COLOR_LIME, pyxel.COLOR_DARK_BLUE, pyxel.COLOR_YELLOW)
NUM_COLORS = 4

# Conveyor timing
SPAWN_INTERVAL_START = 60
SPAWN_INTERVAL_END = 30
TICK_INTERVAL_START = 30
TICK_INTERVAL_END = 15
JUNCTION_PAUSE = 10  # frames item pauses at junction

# Scoring
EXIT_SCORE = 10
SYNTHESIS_BASE = 100
SUPER_MULTIPLIER = 3

# HEAT
MAX_HEAT = 100.0
HEAT_MISMATCH = 15.0
HEAT_LOST = 5.0
HEAT_DECAY = 0.02  # per frame

# Combo
SUPER_COMBO_THRESHOLD = 4
SUPER_DURATION = 300  # 10 seconds

# Particles
ITEM_SIZE = 8


# ── Data Classes ───────────────────────────────────────────────────────

class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Item:
    x: float
    y: float
    color: int
    grid_col: int
    grid_row: int
    arrived_time: int = 0


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
    vy: float = -1.5


# ── Game Class ─────────────────────────────────────────────────────────


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="FLUX FACTORY", fps=FPS)
        pyxel.mouse(True)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.grid: list[list[int]] = [[EMPTY for _ in range(ROWS)] for _ in range(COLS)]
        self.items: list[Item] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.timer: int = TOTAL_FRAMES
        self.super_timer: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.tick_timer: int = TICK_INTERVAL_START
        self.tick_interval: int = TICK_INTERVAL_START
        self.spawn_timer: int = SPAWN_INTERVAL_START + INITIAL_SPAWN_DELAY
        self.spawn_interval: int = SPAWN_INTERVAL_START
        self.frame: int = 0
        self._idle_flow_timer: int = 0
        self._idle_items: list[Item] = []

    @property
    def super_mode(self) -> bool:
        return self.super_timer > 0

    # ── Core Logic (testable, no Pyxel calls) ───────────────────────

    def _spawn_item(self) -> None:
        row = self._rng.randrange(ROWS)
        color_idx = self._rng.randrange(NUM_COLORS)
        color = ITEM_COLORS[color_idx]
        self.items.append(Item(
            x=float(GRID_X),
            y=float(GRID_Y + row * CELL + CELL // 2),
            color=color,
            grid_col=0,
            grid_row=row,
            arrived_time=0,
        ))

    def _move_items(self) -> None:
        for item in self.items[:]:
            item.arrived_time += 1
            col, row = item.grid_col, item.grid_row

            if col < 0 or col >= COLS or row < 0 or row >= ROWS:
                if col >= COLS:
                    self.score += EXIT_SCORE
                    self.items.remove(item)
                elif col < 0:
                    self.items.remove(item)
                continue

            cell_dir = self.grid[col][row]

            if cell_dir == EMPTY:
                self.heat += HEAT_LOST
                self.items.remove(item)
                continue

            if cell_dir == JUNCTION:
                if item.arrived_time < JUNCTION_PAUSE:
                    continue
                out_dir = (self.frame // 30 + row + col) % 4

                target_col, target_row = self._next_cell(col, row, out_dir)
                if target_col >= COLS:
                    self.score += EXIT_SCORE
                    self.items.remove(item)
                    continue
                elif target_col < 0:
                    self.items.remove(item)
                    continue
                if 0 <= target_col < COLS and 0 <= target_row < ROWS:
                    item.grid_col = target_col
                    item.grid_row = target_row
                else:
                    self.heat += HEAT_LOST
                    self.items.remove(item)
                continue

            if item.arrived_time < self.tick_interval:
                continue

            target_col, target_row = self._next_cell(col, row, cell_dir)
            if target_col >= COLS:
                self.score += EXIT_SCORE
                self.items.remove(item)
                continue
            elif target_col < 0 or target_row < 0 or target_row >= ROWS:
                self.heat += HEAT_LOST
                self.items.remove(item)
                continue

            item.grid_col = target_col
            item.grid_row = target_row
            item.arrived_time = 0

    def _next_cell(self, col: int, row: int, direction: int) -> tuple[int, int]:
        if direction == N:
            return (col, row - 1)
        elif direction == E:
            return (col + 1, row)
        elif direction == S:
            return (col, row + 1)
        elif direction == W:
            return (col - 1, row)
        return (col, row)

    def _check_synthesis(self) -> None:
        cell_items: dict[tuple[int, int], list[Item]] = {}
        for item in self.items:
            key = (item.grid_col, item.grid_row)
            cell_items.setdefault(key, []).append(item)

        for (col, row), items_at_cell in cell_items.items():
            if len(items_at_cell) < 2:
                continue

            colors = {it.color for it in items_at_cell}

            if self.super_mode:
                self._do_synthesis(col, row, items_at_cell)
            elif len(colors) == 1:
                self._do_synthesis(col, row, items_at_cell)
            else:
                self._do_mismatch(col, row, items_at_cell)

    def _do_synthesis(self, col: int, row: int, items_at_cell: list[Item]) -> None:
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        multiplier = SUPER_MULTIPLIER if self.super_mode else 1
        points = SYNTHESIS_BASE * self.combo * multiplier
        self.score += points

        px = float(GRID_X + col * CELL + CELL // 2)
        py = float(GRID_Y + row * CELL + CELL // 2)

        for it in items_at_cell:
            if it in self.items:
                self.items.remove(it)

        num_p = 15 if self.super_mode else 10
        for _ in range(num_p):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 3.0)
            p_color = (
                ITEM_COLORS[self._rng.randrange(NUM_COLORS)]
                if self.super_mode
                else items_at_cell[0].color
            )
            self.particles.append(Particle(
                x=px, y=py,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=20, color=p_color,
            ))

        self.floating_texts.append(FloatingText(
            x=px, y=py - 8,
            text=f"+{points}",
            life=25,
            color=pyxel.COLOR_YELLOW if points >= 500 else pyxel.COLOR_WHITE,
        ))
        if self.combo >= 2:
            self.floating_texts.append(FloatingText(
                x=px, y=py - 20,
                text=f"x{self.combo}",
                life=25,
                color=pyxel.COLOR_ORANGE,
            ))

        if self.combo >= SUPER_COMBO_THRESHOLD:
            self.super_timer = SUPER_DURATION

    def _do_mismatch(self, col: int, row: int, items_at_cell: list[Item]) -> None:
        self.heat += HEAT_MISMATCH
        self.combo = 0

        px = float(GRID_X + col * CELL + CELL // 2)
        py = float(GRID_Y + row * CELL + CELL // 2)

        for it in items_at_cell:
            if it in self.items:
                self.items.remove(it)

        for _ in range(5):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.0)
            self.particles.append(Particle(
                x=px, y=py,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=12, color=pyxel.COLOR_RED,
            ))

        self.floating_texts.append(FloatingText(
            x=px, y=py - 8,
            text="HEAT!",
            life=20,
            color=pyxel.COLOR_RED,
        ))

    def _update_heat(self) -> None:
        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER
            return
        if not self.super_mode:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_spawn_timer(self) -> None:
        progress = 1.0 - (self.timer / TOTAL_FRAMES)
        self.spawn_interval = int(SPAWN_INTERVAL_START + (SPAWN_INTERVAL_END - SPAWN_INTERVAL_START) * progress)
        self.tick_interval = int(TICK_INTERVAL_START + (TICK_INTERVAL_END - TICK_INTERVAL_START) * progress)

    def _cycle_cell(self, col: int, row: int) -> None:
        current = self.grid[col][row]
        if current == EMPTY:
            self.grid[col][row] = N
        elif current == N:
            self.grid[col][row] = E
        elif current == E:
            self.grid[col][row] = S
        elif current == S:
            self.grid[col][row] = W
        elif current == W:
            self.grid[col][row] = JUNCTION
        elif current == JUNCTION:
            self.grid[col][row] = EMPTY

    def _handle_click(self, mx: int, my: int) -> None:
        col = (mx - GRID_X) // CELL
        row = (my - GRID_Y) // CELL
        if 0 <= col < COLS and 0 <= row < ROWS:
            self._cycle_cell(col, row)
            self._spawn_click_particles(col, row)

    def _spawn_click_particles(self, col: int, row: int) -> None:
        cx = GRID_X + col * CELL + CELL // 2
        cy = GRID_Y + row * CELL + CELL // 2
        for _ in range(3):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 1.5)
            self.particles.append(Particle(
                x=float(cx), y=float(cy),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=8, color=pyxel.COLOR_GRAY,
            ))

    # ── Update ─────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self._start_game()
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self._start_game()
            self.frame += 1
            self._update_idle_items()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
            return

        self.frame += 1

        # Timer
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self.phase = Phase.GAME_OVER
            return

        # R to restart
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()
            return

        # SUPER timer
        if self.super_timer > 0:
            self.super_timer -= 1

        # Difficulty escalation
        self._update_spawn_timer()

        # Spawn items
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self._spawn_item()
            self.spawn_timer = self.spawn_interval

        # Move items
        self.tick_timer -= 1
        if self.tick_timer <= 0:
            self._move_items()
            self.tick_timer = self.tick_interval

        # Check synthesis
        self._check_synthesis()

        # Update heat
        self._update_heat()

        # Update particles
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.2
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

        # Update floating texts
        for ft in self.floating_texts[:]:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

        # Mouse click to cycle cells
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._handle_click(pyxel.mouse_x, pyxel.mouse_y)

    def _start_game(self) -> None:
        self.phase = Phase.PLAYING
        self.frame = 0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = TOTAL_FRAMES
        self.super_timer = 0
        self.particles.clear()
        self.floating_texts.clear()
        self.items.clear()
        self.grid = [[EMPTY for _ in range(ROWS)] for _ in range(COLS)]
        self.tick_timer = TICK_INTERVAL_START
        self.tick_interval = TICK_INTERVAL_START
        self.spawn_timer = SPAWN_INTERVAL_START + INITIAL_SPAWN_DELAY
        self.spawn_interval = SPAWN_INTERVAL_START

    def _update_idle_items(self) -> None:
        if self.frame % 60 == 0:
            color = ITEM_COLORS[self._rng.randrange(NUM_COLORS)]
            self._idle_items = []
            self._idle_items.append(Item(
                x=float(GRID_X),
                y=float(GRID_Y + self._rng.randrange(ROWS) * CELL + CELL // 2),
                color=color,
                grid_col=0,
                grid_row=0,
                arrived_time=0,
            ))
        for it in self._idle_items[:]:
            it.x += 1.0
            if it.x > SCREEN_W:
                self._idle_items.remove(it)

    # ── Draw ───────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        self._draw_grid()
        self._draw_items()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

        if self.super_mode:
            self._draw_super_border()

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.cls(pyxel.COLOR_NAVY)

        # Title
        title = "FLUX FACTORY"
        tx = SCREEN_W // 2 - len(title) * 4
        pyxel.text(tx, 30, title, pyxel.COLOR_YELLOW)

        # Subtitle
        pyxel.text(SCREEN_W // 2 - 100, 60, "Click grid cells to build", pyxel.COLOR_WHITE)
        pyxel.text(SCREEN_W // 2 - 100, 70, "conveyor belts!", pyxel.COLOR_WHITE)

        pyxel.text(SCREEN_W // 2 - 100, 90, "Same-color items combine", pyxel.COLOR_LIME)
        pyxel.text(SCREEN_W // 2 - 100, 100, "at junctions for COMBOS!", pyxel.COLOR_LIME)

        pyxel.text(SCREEN_W // 2 - 100, 120, "Different colors = HEAT up!", pyxel.COLOR_RED)

        pyxel.text(SCREEN_W // 2 - 75, 150, "Press SPACE or click", pyxel.COLOR_WHITE)
        pyxel.text(SCREEN_W // 2 - 75, 160, "to start", pyxel.COLOR_WHITE)

        # Color legend
        color_names = ("RED", "LIME", "BLUE", "YELLOW")
        color_vals = (pyxel.COLOR_RED, pyxel.COLOR_LIME, pyxel.COLOR_DARK_BLUE, pyxel.COLOR_YELLOW)
        for i in range(NUM_COLORS):
            cx = 60 + i * 60
            pyxel.rect(cx - 5, 185, 10, 10, color_vals[i])
            pyxel.text(cx - 10, 198, color_names[i], color_vals[i])

        # Idle flowing items
        for it in self._idle_items:
            pyxel.rect(int(it.x) - ITEM_SIZE // 2, int(it.y) - ITEM_SIZE // 2, ITEM_SIZE, ITEM_SIZE, it.color)

    def _draw_grid(self) -> None:
        for col in range(COLS):
            for row in range(ROWS):
                gx = GRID_X + col * CELL
                gy = GRID_Y + row * CELL
                cell_dir = self.grid[col][row]

                if cell_dir == EMPTY:
                    pyxel.rect(gx, gy, CELL, CELL, pyxel.COLOR_DARK_BLUE)
                else:
                    pyxel.rect(gx, gy, CELL, CELL, pyxel.COLOR_NAVY)

                pyxel.rectb(gx, gy, CELL, CELL, pyxel.COLOR_GRAY)

                self._draw_cell_direction(gx, gy, cell_dir)

    def _draw_cell_direction(self, gx: int, gy: int, direction: int) -> None:
        cx = gx + CELL // 2
        cy = gy + CELL // 2
        s = CELL // 4  # half-size of triangle

        color = pyxel.COLOR_GRAY
        if direction == N:
            pyxel.tri(cx, cy - s, cx - s, cy + s, cx + s, cy + s, color)
        elif direction == E:
            pyxel.tri(cx + s, cy, cx - s, cy - s, cx - s, cy + s, color)
        elif direction == S:
            pyxel.tri(cx, cy + s, cx - s, cy - s, cx + s, cy - s, color)
        elif direction == W:
            pyxel.tri(cx - s, cy, cx + s, cy - s, cx + s, cy + s, color)
        elif direction == JUNCTION:
            junction_color = pyxel.COLOR_YELLOW
            pyxel.tri(cx, cy - s, cx - s, cy, cx + s, cy, junction_color)
            pyxel.tri(cx, cy + s, cx - s, cy, cx + s, cy, junction_color)
            pyxel.tri(cx - s, cy, cx, cy - s, cx, cy + s, junction_color)
            pyxel.tri(cx + s, cy, cx, cy - s, cx, cy + s, junction_color)

    def _draw_items(self) -> None:
        for item in self.items:
            px = int(item.x) - ITEM_SIZE // 2
            py = int(item.y) - ITEM_SIZE // 2
            if 0 <= item.grid_col < COLS and 0 <= item.grid_row < ROWS:
                gx = GRID_X + item.grid_col * CELL + CELL // 2 - ITEM_SIZE // 2
                gy = GRID_Y + item.grid_row * CELL + CELL // 2 - ITEM_SIZE // 2
                px = int(gx)
                py = int(gy)
            pyxel.rect(px, py, ITEM_SIZE, ITEM_SIZE, item.color)
            pyxel.rectb(px, py, ITEM_SIZE, ITEM_SIZE, pyxel.COLOR_BLACK)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, 19, pyxel.COLOR_DARK_BLUE)

        # Score
        pyxel.text(4, 2, f"SCORE:{self.score:>7d}", pyxel.COLOR_WHITE)

        # Combo
        combo_col = pyxel.COLOR_WHITE
        if self.combo >= SUPER_COMBO_THRESHOLD:
            combo_col = pyxel.COLOR_YELLOW
        elif self.combo >= 2:
            combo_col = pyxel.COLOR_ORANGE
        pyxel.text(4, 10, f"COMBO: x{self.combo}", combo_col)

        # Timer
        secs = int(self.timer / FPS + 1)
        timer_col = pyxel.COLOR_RED if secs <= 10 else pyxel.COLOR_WHITE
        pyxel.text(SCREEN_W - 60, 2, f"TIME:{secs:>3d}", timer_col)

        # HEAT bar
        bar_x = 140
        bar_y = 2
        bar_w = 80
        bar_h = 7
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, pyxel.COLOR_GRAY)

        heat_ratio = min(1.0, self.heat / MAX_HEAT)
        fill_w = int(bar_w * heat_ratio)

        if heat_ratio < 0.33:
            bar_color = pyxel.COLOR_GREEN
        elif heat_ratio < 0.66:
            bar_color = pyxel.COLOR_YELLOW
        else:
            bar_color = pyxel.COLOR_RED

        if fill_w > 0:
            pyxel.rect(bar_x, bar_y, fill_w, bar_h, bar_color)

        pyxel.text(bar_x + 2, bar_y + 9, "HEAT", pyxel.COLOR_RED)

        # SUPER indicator
        if self.super_mode:
            super_secs = self.super_timer / FPS
            pyxel.text(SCREEN_W - 60, 10, f"FLUX:{super_secs:4.1f}", pyxel.COLOR_YELLOW)

    def _draw_super_border(self) -> None:
        rainbow = (pyxel.COLOR_RED, pyxel.COLOR_ORANGE, pyxel.COLOR_YELLOW,
                    pyxel.COLOR_LIME, pyxel.COLOR_CYAN, pyxel.COLOR_PURPLE)
        offset = (self.frame // 10) % len(rainbow)

        grid_x = GRID_X
        grid_y = GRID_Y
        grid_w = COLS * CELL
        grid_h = ROWS * CELL

        for i in range(4):
            color = rainbow[(offset + i) % len(rainbow)]
            pyxel.rectb(grid_x - i, grid_y - i, grid_w + i * 2, grid_h + i * 2, color)

    def _draw_game_over(self) -> None:
        pyxel.rect(40, SCREEN_H // 2 - 50, SCREEN_W - 80, 100, pyxel.COLOR_BLACK)
        pyxel.rectb(40, SCREEN_H // 2 - 50, SCREEN_W - 80, 100, pyxel.COLOR_WHITE)

        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 - 40, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(SCREEN_W // 2 - 50, SCREEN_H // 2 - 20, f"SCORE: {self.score}", pyxel.COLOR_WHITE)
        pyxel.text(SCREEN_W // 2 - 50, SCREEN_H // 2 - 8, f"MAX COMBO: x{self.max_combo}", pyxel.COLOR_YELLOW)
        pyxel.text(SCREEN_W // 2 - 65, SCREEN_H // 2 + 20, "SPACE to restart", pyxel.COLOR_WHITE)


# ── Entry Point ────────────────────────────────────────────────────────


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
