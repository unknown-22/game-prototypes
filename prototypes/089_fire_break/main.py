from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


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


FIRE_COLORS: list[int] = [8, 3, 1, 10]
FIRE_NAMES: list[str] = ["RED", "GREEN", "BLUE", "YELLOW"]
GRID_COLS = 16
GRID_ROWS = 12
CELL_SIZE = 18
GRID_X = 16
GRID_Y = 16
SCREEN_W = 320
SCREEN_H = 240
GAME_DURATION = 90 * 30
MAX_HEAT = 100.0
SPREAD_INITIAL = 30
SPREAD_MIN = 8
SPAWN_INTERVAL = 60
SPREAD_CHANCE = 0.30
COMBO_SURGE_THRESHOLD = 4
HEAT_PER_CELL = 0.033
HEAT_PENALTY_WRONG = 5.0
SURGE_FLASH_FRAMES = 5
SHAKE_FRAMES = 8


class FireBreak:
    def __init__(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.fire_color: int = 1
        self.grid: list[list[int]] = []
        self.next_grid: list[list[int]] = []
        self.spawn_timer: int = 0
        self.spread_timer: int = 0
        self.spread_interval: int = SPREAD_INITIAL
        self.game_timer: int = 0
        self.particles: list[Particle] = []
        self.shake_frames: int = 0
        self.surge_flash: int = 0
        self._rng: random.Random = random.Random()
        self.surge_count: int = 0
        self._last_click_surge: bool = False
        self._last_surge_cells: int = 0
        self._last_score_gained: int = 0
        self._last_click_combo_broke: bool = False

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.fire_color = 1
        self.grid = self._make_grid()
        self.next_grid = self._make_grid()
        self.spawn_timer = 0
        self.spread_timer = 0
        self.spread_interval = SPREAD_INITIAL
        self.game_timer = GAME_DURATION
        self.particles.clear()
        self.shake_frames = 0
        self.surge_flash = 0
        self.surge_count = 0
        self._last_click_surge = False
        self._last_surge_cells = 0
        self._last_score_gained = 0
        self._last_click_combo_broke = False
        self._spawn_fires(8)

    def _make_grid(self) -> list[list[int]]:
        return [[0] * GRID_COLS for _ in range(GRID_ROWS)]

    def _spawn_fires(self, count: int) -> None:
        for _ in range(count):
            empty = [
                (r, c)
                for r in range(GRID_ROWS)
                for c in range(GRID_COLS)
                if self.grid[r][c] == 0
            ]
            if not empty:
                break
            r, c = self._rng.choice(empty)
            self.grid[r][c] = self._rng.randint(1, 4)

    def _spread_fires(self) -> None:
        self.next_grid = [row[:] for row in self.grid]
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.grid[r][c] != 0:
                    continue
                neighbor_colors: list[int] = []
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < GRID_ROWS and 0 <= nc < GRID_COLS:
                        fc = self.grid[nr][nc]
                        if fc != 0:
                            neighbor_colors.append(fc)
                if neighbor_colors and self._rng.random() < SPREAD_CHANCE:
                    self.next_grid[r][c] = self._rng.choice(neighbor_colors)
        self.grid = self.next_grid

    def _handle_click(self, col: int, row: int) -> tuple[int, bool, bool, int]:
        if not (0 <= col < GRID_COLS and 0 <= row < GRID_ROWS):
            return (0, False, False, 0)
        cell_color = self.grid[row][col]
        if cell_color == 0:
            return (0, False, False, 0)

        self._last_click_combo_broke = False

        if cell_color == self.fire_color:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            gained = 10 * self.combo
            self.grid[row][col] = 0
            self._spawn_particles(
                GRID_X + col * CELL_SIZE + CELL_SIZE / 2,
                GRID_Y + row * CELL_SIZE + CELL_SIZE / 2,
                FIRE_COLORS[cell_color - 1],
                4,
            )

            surge_triggered = self.combo >= COMBO_SURGE_THRESHOLD
            surge_cells = 0
            if surge_triggered:
                cluster = self._bfs_cluster(col, row, cell_color)
                surge_cells = len(cluster)
                for c, r in cluster:
                    self.grid[r][c] = 0
                gained += surge_cells * 50 * self.combo
                self.surge_count += 1
                self.surge_flash = SURGE_FLASH_FRAMES
                self.shake_frames = SHAKE_FRAMES
                self._spawn_particles(
                    GRID_X + col * CELL_SIZE + CELL_SIZE / 2,
                    GRID_Y + row * CELL_SIZE + CELL_SIZE / 2,
                    FIRE_COLORS[cell_color - 1],
                    min(20 + surge_cells * 2, 60),
                )
                self.combo = 0

            self._last_surge_cells = surge_cells
            self._last_click_surge = surge_triggered
            self._last_score_gained = gained
            self.score += gained
            return (gained, True, surge_triggered, surge_cells)
        else:
            self._last_click_combo_broke = True
            self.heat = min(MAX_HEAT, self.heat + HEAT_PENALTY_WRONG)
            self.grid[row][col] = 0
            self._spawn_particles(
                GRID_X + col * CELL_SIZE + CELL_SIZE / 2,
                GRID_Y + row * CELL_SIZE + CELL_SIZE / 2,
                FIRE_COLORS[cell_color - 1],
                2,
            )
            self.combo = 0
            self._last_click_surge = False
            self._last_surge_cells = 0
            self._last_score_gained = 0
            return (0, True, False, 0)

    def _bfs_cluster(self, col: int, row: int, color: int) -> set[tuple[int, int]]:
        visited: set[tuple[int, int]] = set()
        queue: list[tuple[int, int]] = [(col, row)]
        visited.add((col, row))
        while queue:
            c, r = queue.pop(0)
            for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nc, nr = c + dc, r + dr
                if (
                    0 <= nc < GRID_COLS
                    and 0 <= nr < GRID_ROWS
                    and (nc, nr) not in visited
                    and self.grid[nr][nc] == color
                ):
                    visited.add((nc, nr))
                    queue.append((nc, nr))
        return visited

    def _update_heat(self) -> None:
        fire_count = sum(1 for row in self.grid for cell in row if cell != 0)
        self.heat = min(MAX_HEAT, self.heat + fire_count * HEAT_PER_CELL)
        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER

    def _cycle_color(self) -> None:
        self.fire_color = self.fire_color % 4 + 1

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.tau)
            speed = self._rng.uniform(0.5, 3.0)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=self._rng.randint(15, 30),
                    color=color,
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _advance_timers(self) -> None:
        self.game_timer -= 1
        if self.game_timer <= 0:
            self.game_timer = 0
            self.phase = Phase.GAME_OVER
            return

        self.spread_timer -= 1
        if self.spread_timer <= 0:
            self._spread_fires()
            self.spread_timer = self.spread_interval
            self.spread_interval = max(SPREAD_MIN, self.spread_interval - 1)

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            fire_count = sum(1 for row in self.grid for cell in row if cell != 0)
            if fire_count < 10:
                self._spawn_fires(3)
            self.spawn_timer = SPAWN_INTERVAL

    def _grid_coords(self, mx: int, my: int) -> tuple[int, int]:
        col = (mx - GRID_X) // CELL_SIZE
        row = (my - GRID_Y) // CELL_SIZE
        return (col, row)

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.phase = Phase.TITLE
            return

        if self.phase == Phase.PLAYING:
            if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
                self._cycle_color()

            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                mx = pyxel.mouse_x
                my = pyxel.mouse_y
                col, row = self._grid_coords(mx, my)
                if 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS:
                    self._handle_click(col, row)

            self._advance_timers()

            if self.phase == Phase.PLAYING:
                self._update_heat()

            self._update_particles()

            if self.surge_flash > 0:
                self.surge_flash -= 1
            if self.shake_frames > 0:
                self.shake_frames -= 1

    def draw(self) -> None:
        if self.shake_frames > 0:
            shake_x = random.randint(-3, 3)
            shake_y = random.randint(-3, 3)
            pyxel.camera(shake_x, shake_y)
        else:
            pyxel.camera()

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

        if self.surge_flash > 0:
            pyxel.dither(0.5)
            pyxel.rect(0, 0, SCREEN_W, SCREEN_H, 7)
            pyxel.dither(1.0)

    def _draw_title(self) -> None:
        pyxel.cls(0)
        pyxel.text(100, 30, "FIRE BREAK", 8)
        pyxel.rect(102, 39, 116, 1, 8)

        pyxel.text(70, 60, "CLICK CELLS TO EXTINGUISH FIRES", 7)
        pyxel.text(78, 75, "SAME COLOR = COMBO CHAIN", 3)
        pyxel.text(70, 90, "COMBO x4+ = SURGE BLAST!", 10)

        pyxel.text(60, 120, "FIRE COLORS:", 7)
        for i, (name, col) in enumerate(zip(FIRE_NAMES, FIRE_COLORS)):
            px = 60 + i * 68
            pyxel.rect(px, 135, 20, 14, col)
            pyxel.text(px + 2, 139, name[0], 0)
            pyxel.text(px, 152, name, col)

        pyxel.text(70, 175, "RIGHT CLICK or R: CHANGE COLOR", 7)
        pyxel.text(100, 192, "SURVIVE 90 SECONDS", 9)

        pyxel.text(80, 220, "SPACE or CLICK TO START", 7)
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(80, 220, "SPACE or CLICK TO START", 10)

    def _draw_playing(self) -> None:
        pyxel.cls(0)

        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                x = GRID_X + col * CELL_SIZE
                y = GRID_Y + row * CELL_SIZE
                cell_val = self.grid[row][col]
                if cell_val == 0:
                    pyxel.rect(x, y, CELL_SIZE, CELL_SIZE, 13)
                    pyxel.rectb(x, y, CELL_SIZE, CELL_SIZE, 5)
                else:
                    fire_col = FIRE_COLORS[cell_val - 1]
                    if pyxel.frame_count % 8 < 4:
                        pyxel.rect(x, y, CELL_SIZE, CELL_SIZE, fire_col)
                    else:
                        bright_col = fire_col
                        if fire_col == 8:
                            bright_col = 9
                        elif fire_col == 3:
                            bright_col = 11
                        elif fire_col == 1:
                            bright_col = 6
                        elif fire_col == 10:
                            bright_col = 9
                        pyxel.rect(x, y, CELL_SIZE, CELL_SIZE, min(15, bright_col))

        self._draw_heat_bar()
        self._draw_hud()

        for p in self.particles:
            if p.life > 0:
                alpha = p.life / 30.0
                if alpha > 0.3:
                    pyxel.pset(int(p.x), int(p.y), p.color)

        grid_bottom = GRID_Y + GRID_ROWS * CELL_SIZE
        color_indicator_x = SCREEN_W // 2 - 10
        pyxel.rect(color_indicator_x, grid_bottom + 4, 20, 14, FIRE_COLORS[self.fire_color - 1])
        pyxel.rectb(color_indicator_x, grid_bottom + 4, 20, 14, 7)
        pyxel.text(color_indicator_x + 25, grid_bottom + 6, FIRE_NAMES[self.fire_color - 1], 7)

        if self._last_click_surge and self._last_surge_cells > 0:
            tx = GRID_X + GRID_COLS * CELL_SIZE // 2
            ty = GRID_Y + GRID_ROWS * CELL_SIZE // 2
            if self.surge_flash > 0:
                pyxel.text(tx - 30, ty, f"SURGE x{self._last_surge_cells}!", 10)

    def _draw_heat_bar(self) -> None:
        bar_w = 288
        bar_h = 8
        bar_x = GRID_X
        bar_y = 4
        fill = int(bar_w * (self.heat / MAX_HEAT))

        pyxel.rect(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2, 13)
        if fill > 0:
            if self.heat > 70:
                hc = 8
            elif self.heat > 40:
                hc = 9
            else:
                hc = 3
            pyxel.rect(bar_x, bar_y, fill, bar_h, hc)

        pyxel.text(GRID_X + bar_w + 4, bar_y - 1, f"HEAT {int(self.heat)}", 7)

    def _draw_hud(self) -> None:
        combo_text = f"COMBO x{self.combo}"
        combo_color = 7
        if self.combo >= COMBO_SURGE_THRESHOLD:
            combo_color = 10
        elif self.combo >= 2:
            combo_color = 9
        pyxel.text(4, SCREEN_H - 20, combo_text, combo_color)

        seconds = self.game_timer // 30
        timer_color = 7
        if seconds <= 15:
            timer_color = 8
        elif seconds <= 30:
            timer_color = 9
        pyxel.text(SCREEN_W - 70, 4, f"TIME: {seconds:2d}s", timer_color)

        pyxel.text(SCREEN_W - 70, SCREEN_H - 20, f"SCORE: {self.score}", 7)

    def _draw_game_over(self) -> None:
        pyxel.cls(0)
        pyxel.text(100, 40, "GAME OVER", 8)
        pyxel.rect(102, 49, 116, 1, 8)

        pyxel.text(100, 70, f"FINAL SCORE: {self.score}", 7)
        pyxel.text(100, 90, f"MAX COMBO: {self.max_combo}", 9)
        pyxel.text(100, 110, f"SURGES: {self.surge_count}", 10)

        survived = (GAME_DURATION - self.game_timer) // 30
        pyxel.text(100, 135, f"SURVIVED: {survived}s / 90s", 3)

        pyxel.text(80, 220, "SPACE or CLICK TO RETRY", 7)
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(80, 220, "SPACE or CLICK TO RETRY", 10)


class App:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Fire Break", display_scale=2)
        pyxel.mouse(True)
        self.game = FireBreak()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        self.game.update()

    def draw(self) -> None:
        self.game.draw()


if __name__ == "__main__":
    App()
