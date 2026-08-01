from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import pyxel


class Phase(Enum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


@dataclass
class Dot:
    col: int
    row: int
    color: int


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: float = 2.0


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int
    vy: float = -1.0


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

SCREEN_W = 320
SCREEN_H = 240
COLS = 8
ROWS = 7
CELL = 28
GRID_X = (SCREEN_W - COLS * CELL) // 2
GRID_Y = 20
DOT_RADIUS = 10
COLORS = [RED, LIME, DARK_BLUE, YELLOW]
COLOR_NAMES: dict[int, str] = {RED: "RED", LIME: "LIME", DARK_BLUE: "BLUE", YELLOW: "YELLOW"}
MIN_CHAIN_LEN = 3
SUPER_DURATION = 300
HEAT_MAX = 100
HEAT_DECAY = 0.02
HEAT_MISMATCH = 15
HEAT_SHORT = 5
GAME_TIME = 60 * 60


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Dot Chain")
        pyxel.mouse(True)

        font_path = Path(__file__).with_name("k8x12.bdf")
        if font_path.exists():
            pyxel.load(str(font_path), exclude_images=False, exclude_tilemaps=False, exclude_sounds=False, exclude_musics=False)

        self._rng = random.Random()
        self._headless = False
        self._frame_count = 0
        self._init_state()
        self._load_best_score()

        pyxel.run(self._update, self._draw)

    def __new__(cls) -> Game:
        instance = object.__new__(cls)
        instance._rng = random.Random()
        instance._headless = True
        instance._frame_count = 0
        instance._init_state()
        return instance

    def _init_state(self) -> None:
        self.phase = Phase.TITLE
        self.dots: list[Dot] = []
        self.grid: list[list[Dot | None]] = [[None] * COLS for _ in range(ROWS)]
        self.dragging = False
        self.chain_path: list[tuple[int, int]] = []
        self.chain_color = 0
        self.score = 0
        self.combo = -1
        self.max_combo = 0
        self.best_score = 0
        self.heat = 0.0
        self.super_timer = 0
        self.timer = GAME_TIME
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.ghost_trail: list[tuple[float, float, int]] = []
        self._last_combo_color = -1

    def _load_best_score(self) -> None:
        pass

    def reset(self) -> None:
        self._init_state()
        self._init_grid()
        self.phase = Phase.PLAYING

    def _init_grid(self) -> None:
        self.dots.clear()
        self.grid = [[None] * COLS for _ in range(ROWS)]
        for row in range(ROWS):
            for col in range(COLS):
                color = self._rng.choice(COLORS)
                dot = Dot(col, row, color)
                self.grid[row][col] = dot
                self.dots.append(dot)

    @property
    def super_active(self) -> bool:
        return self.super_timer > 0

    def _grid_to_screen(self, col: int, row: int) -> tuple[float, float]:
        x = GRID_X + col * CELL + CELL // 2
        y = GRID_Y + row * CELL + CELL // 2
        return x, y

    def _screen_to_grid(self, mx: int, my: int) -> tuple[int, int]:
        col = (mx - GRID_X) // CELL
        row = (my - GRID_Y) // CELL
        return col, row

    def _find_nearest_dot(self, mx: int, my: int) -> Dot | None:
        best_dot: Dot | None = None
        best_dist = float("inf")
        for dot in self.dots:
            sx, sy = self._grid_to_screen(dot.col, dot.row)
            dist = math.hypot(mx - sx, my - sy)
            if dist <= DOT_RADIUS + 2 and dist < best_dist:
                best_dot = dot
                best_dist = dist
        return best_dot

    def _is_adjacent(self, c1: int, r1: int, c2: int, r2: int) -> bool:
        return max(abs(c1 - c2), abs(r1 - r2)) <= 1 and not (c1 == c2 and r1 == r2)

    def _is_visited(self, col: int, row: int) -> bool:
        return (col, row) in self.chain_path

    def _try_add_to_chain(self, col: int, row: int) -> bool:
        if col < 0 or col >= COLS or row < 0 or row >= ROWS:
            return False
        if self._is_visited(col, row):
            return False
        if self.grid[row][col] is None:
            return False
        dot = self.grid[row][col]
        if dot is None:
            return False
        if not self.super_active and dot.color != self.chain_color:
            self.heat = min(self.heat + HEAT_MISMATCH, HEAT_MAX)
            self._spawn_floating_text(
                GRID_X + col * CELL + CELL // 2,
                GRID_Y + row * CELL + CELL // 2,
                "WRONG!",
                RED,
            )
            return False
        if len(self.chain_path) > 0:
            last_col, last_row = self.chain_path[-1]
            if not self._is_adjacent(last_col, last_row, col, row):
                return False
        self.chain_path.append((col, row))
        self.chain_color = dot.color
        return True

    def _score_chain(self) -> int:
        chain_len = len(self.chain_path)
        if chain_len < MIN_CHAIN_LEN:
            self.heat = min(self.heat + HEAT_SHORT, HEAT_MAX)
            self._spawn_floating_text(
                self._chain_mid_x(),
                self._chain_mid_y(),
                "SHORT!",
                ORANGE,
            )
            self.combo = -1
            self._last_combo_color = -1
            self.chain_path.clear()
            return 0

        if self.combo == -1 or self._last_combo_color != self.chain_color:
            self.combo = 0
            self._last_combo_color = self.chain_color
        else:
            self.combo += 1

        base_score = chain_len * 10
        multiplier = 1.0 + self.combo * 0.5
        super_mult = 3.0 if self.super_active else 1.0
        final_score = int(base_score * multiplier * super_mult)
        self.score += final_score

        if self.combo > self.max_combo:
            self.max_combo = self.combo

        if self.combo >= 4 and not self.super_active:
            self.super_timer = SUPER_DURATION
            self._spawn_floating_text(self._chain_mid_x(), self._chain_mid_y(), "SUPER DOT!", YELLOW)

        combo_text = f"COMBO x{self.combo}!" if self.combo >= 1 else ""
        text = f"+{final_score}"
        popup_color = YELLOW if self.super_active else WHITE
        self._spawn_floating_text(self._chain_mid_x(), self._chain_mid_y(), text, popup_color)
        if combo_text:
            self._spawn_floating_text(self._chain_mid_x(), self._chain_mid_y() - 12, combo_text, CYAN)

        for col, row in self.chain_path:
            dot = self.grid[row][col]
            if dot is not None:
                color = dot.color
            else:
                color = WHITE
            sx, sy = self._grid_to_screen(col, row)
            self.ghost_trail.append((sx, sy, color))
            self._spawn_particles(sx, sy, color, 6)

        if len(self.ghost_trail) > 200:
            self.ghost_trail = self.ghost_trail[-200:]

        return final_score

    def _chain_mid_x(self) -> float:
        if not self.chain_path:
            return SCREEN_W / 2
        xs = [GRID_X + c * CELL + CELL // 2 for c, _ in self.chain_path]
        return sum(xs) / len(xs)

    def _chain_mid_y(self) -> float:
        if not self.chain_path:
            return SCREEN_H / 2
        ys = [GRID_Y + r * CELL + CELL // 2 for _, r in self.chain_path]
        return sum(ys) / len(ys)

    def _clear_chain(self) -> None:
        for col, row in self.chain_path:
            dot = self.grid[row][col]
            if dot is not None and dot in self.dots:
                self.dots.remove(dot)
            self.grid[row][col] = None

    def _apply_gravity(self) -> None:
        for col in range(COLS):
            write_row = ROWS - 1
            for row in range(ROWS - 1, -1, -1):
                dot = self.grid[row][col]
                if dot is not None:
                    if write_row != row:
                        self.grid[row][col] = None
                        self.grid[write_row][col] = dot
                        dot.row = write_row
                        dot.col = col
                    write_row -= 1

    def _fill_empty(self) -> None:
        for col in range(COLS):
            for row in range(ROWS):
                if self.grid[row][col] is None:
                    color = self._rng.choice(COLORS)
                    dot = Dot(col, row, color)
                    self.grid[row][col] = dot
                    self.dots.append(dot)

    def _update_heat(self) -> bool:
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            if self.score > self.best_score:
                self.best_score = self.score
            return True
        self.heat = max(0.0, self.heat - HEAT_DECAY)
        return False

    def _update_particles(self) -> None:
        new_particles: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                new_particles.append(p)
        self.particles = new_particles

    def _update_floating_texts(self) -> None:
        new_texts: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life > 0:
                new_texts.append(ft)
        self.floating_texts = new_texts

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.5)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = self._rng.randint(10, 25)
            self.particles.append(Particle(x, y, vx, vy, life, color))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x, y, text, 30, color))

    def _start_chain(self, mx: int, my: int) -> None:
        dot = self._find_nearest_dot(mx, my)
        if dot is None:
            return
        self.dragging = True
        self.chain_path = [(dot.col, dot.row)]
        self.chain_color = dot.color

    def _extend_chain(self, mx: int, my: int) -> None:
        if not self.chain_path:
            return
        col, row = self._screen_to_grid(mx, my)
        if col < 0 or col >= COLS or row < 0 or row >= ROWS:
            return
        if self._is_visited(col, row):
            return
        if self.grid[row][col] is None:
            return
        dot = self.grid[row][col]
        if dot is None:
            return
        if not self.super_active and dot.color != self.chain_color:
            return
        last_col, last_row = self.chain_path[-1]
        if not self._is_adjacent(last_col, last_row, col, row):
            return
        self.chain_path.append((col, row))

    def _end_chain(self) -> None:
        self.dragging = False
        _ = self._score_chain()
        if len(self.chain_path) >= MIN_CHAIN_LEN:
            self._clear_chain()
            self._apply_gravity()
            self._fill_empty()
        else:
            self.chain_path.clear()

    def _update(self) -> None:
        self._frame_count += 1

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        if self.phase == Phase.PLAYING:
            self.timer -= 1
            if self.timer <= 0:
                self.timer = 0
                self.phase = Phase.GAME_OVER
                if self.score > self.best_score:
                    self.best_score = self.score
                return

            if self.super_timer > 0:
                self.super_timer -= 1

            self._update_heat()
            if self.phase == Phase.GAME_OVER:
                return

            self._update_particles()
            self._update_floating_texts()

            mx = pyxel.mouse_x
            my = pyxel.mouse_y

            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self._start_chain(mx, my)

            if self.dragging:
                if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
                    self._extend_chain(mx, my)
                else:
                    self._end_chain()

    def _draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        title_x = SCREEN_W // 2 - 40
        pyxel.text(title_x, 40, "DOT CHAIN", WHITE)

        lines = [
            "Click & drag to connect",
            "same-color dots!",
            "",
            "COMBO >= 4 -> SUPER DOT!",
            "HEAT = risk!",
            "",
            "Click or Enter to start",
        ]
        y = 80
        for line in lines:
            text_w = len(line) * 4
            if line:
                pyxel.text(SCREEN_W // 2 - text_w // 2, y, line, GRAY)
            y += 14

    def _draw_playing(self) -> None:
        self._draw_grid()

        self._draw_ghost_trail()

        if len(self.chain_path) >= 2:
            self._draw_chain_lines()

        for dot in self.dots:
            self._draw_dot(dot.col, dot.row, dot.color)

        if len(self.chain_path) >= 1:
            for col, row in self.chain_path:
                self._draw_dot_highlight(col, row)

        self._draw_hud()

        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

        for ft in self.floating_texts:
            text_w = len(ft.text) * 4
            pyxel.text(int(ft.x) - text_w // 2, int(ft.y), ft.text, ft.color)

        if self.super_active:
            self._draw_super_overlay()

    def _draw_grid(self) -> None:
        lx = GRID_X
        ly = GRID_Y
        rx = GRID_X + COLS * CELL - 1
        ry = GRID_Y + ROWS * CELL - 1
        pyxel.rectb(lx - 1, ly - 1, rx - lx + 3, ry - ly + 3, GRAY)

        if self.dragging and len(self.chain_path) > 0:
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            col, row = self._screen_to_grid(mx, my)
            if 0 <= col < COLS and 0 <= row < ROWS:
                dot = self.grid[row][col]
                if dot is not None and not self._is_visited(col, row):
                    if len(self.chain_path) > 0:
                        last_col, last_row = self.chain_path[-1]
                        if self._is_adjacent(last_col, last_row, col, row):
                            valid = self.super_active or dot.color == self.chain_color
                            cursor_color = CYAN if valid else RED
                            cursor_x = GRID_X + col * CELL + CELL // 2
                            cursor_y = GRID_Y + row * CELL + CELL // 2
                            pyxel.circb(cursor_x, cursor_y, DOT_RADIUS + 2, cursor_color)
                    else:
                        valid = self.super_active or dot.color == self.chain_color
                        cursor_color = CYAN if valid else RED
                        cursor_x = GRID_X + col * CELL + CELL // 2
                        cursor_y = GRID_Y + row * CELL + CELL // 2
                        pyxel.circb(cursor_x, cursor_y, DOT_RADIUS + 2, cursor_color)

    def _draw_dot(self, col: int, row: int, color: int) -> None:
        x = GRID_X + col * CELL + CELL // 2
        y = GRID_Y + row * CELL + CELL // 2
        pyxel.circ(x, y, DOT_RADIUS, color)
        pyxel.circb(x, y, DOT_RADIUS, WHITE)

    def _draw_dot_highlight(self, col: int, row: int) -> None:
        x = GRID_X + col * CELL + CELL // 2
        y = GRID_Y + row * CELL + CELL // 2
        pyxel.circb(x, y, DOT_RADIUS + 2, WHITE)
        pyxel.circb(x, y, DOT_RADIUS + 3, WHITE)

    def _draw_chain_lines(self) -> None:
        for i in range(len(self.chain_path) - 1):
            c1, r1 = self.chain_path[i]
            c2, r2 = self.chain_path[i + 1]
            x1 = GRID_X + c1 * CELL + CELL // 2
            y1 = GRID_Y + r1 * CELL + CELL // 2
            x2 = GRID_X + c2 * CELL + CELL // 2
            y2 = GRID_Y + r2 * CELL + CELL // 2
            pyxel.line(x1, y1, x2, y2, WHITE)

    def _draw_ghost_trail(self) -> None:
        for x, y, color in self.ghost_trail:
            pyxel.pset(int(x), int(y), color)

    def _draw_hud(self) -> None:
        pyxel.text(4, 2, f"SCORE: {self.score}", WHITE)
        combo_text = f"COMBO: {self.combo}" if self.combo >= 0 else "COMBO: 0"
        combo_color = YELLOW if self.combo >= 2 else GRAY
        pyxel.text(4, 10, combo_text, combo_color)
        pyxel.text(4, 18, f"BEST: {self.best_score}", ORANGE)

        seconds = max(0, self.timer // 60)
        timer_text = f"TIME: {seconds}s"
        pyxel.text(SCREEN_W - 60, 2, timer_text, WHITE if seconds > 10 else RED)

        bar_w = 80
        bar_x = SCREEN_W - bar_w - 4
        bar_y = 10
        bar_h = 4
        fill = max(0, int(bar_w * self.timer / GAME_TIME))
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, DARK_BLUE)
        pyxel.rect(bar_x, bar_y, fill, bar_h, LIME if self.timer > 600 else RED)

        heat_bar_x = 4
        heat_bar_y = GRID_Y + ROWS * CELL + 8
        heat_bar_w = COLS * CELL
        heat_bar_h = 6
        heat_fill = int(heat_bar_w * self.heat / HEAT_MAX)
        heat_color = GREEN
        if self.heat > 70:
            heat_color = RED
        elif self.heat > 40:
            heat_color = ORANGE
        pyxel.rectb(heat_bar_x - 1, heat_bar_y - 1, heat_bar_w + 2, heat_bar_h + 2, GRAY)
        pyxel.rect(heat_bar_x, heat_bar_y, heat_bar_w, heat_bar_h, DARK_BLUE)
        pyxel.rect(heat_bar_x, heat_bar_y, heat_fill, heat_bar_h, heat_color)
        pyxel.text(heat_bar_x, heat_bar_y - 8, "HEAT", GRAY)

        if self.dragging:
            chain_len_text = f"LEN: {len(self.chain_path)}"
            pyxel.text(SCREEN_W - 50, 18, chain_len_text, WHITE)

    def _draw_super_overlay(self) -> None:
        sec = self.super_timer // 60
        super_text = f"SUPER! {sec}s"
        text_w = len(super_text) * 4
        x = SCREEN_W // 2 - text_w // 2
        y = 2

        hue = (self._frame_count // 4) % 16
        pyxel.text(x, y, super_text, hue if hue != 0 else WHITE)

        border_color = (self._frame_count // 2) % 16
        lx = GRID_X
        ly = GRID_Y
        rx = GRID_X + COLS * CELL - 1
        ry = GRID_Y + ROWS * CELL - 1
        pyxel.rectb(lx - 2, ly - 2, rx - lx + 5, ry - ly + 5, border_color if border_color != 0 else WHITE)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 28, 60, "GAME OVER", RED)

        lines = [
            f"Score: {self.score}",
            f"Max Combo: {self.max_combo}",
            f"Best: {self.best_score}",
            "",
            "Click or Enter to retry",
        ]
        y = 100
        for line in lines:
            text_w = len(line) * 4
            if line:
                color = YELLOW if "Score" in line else GRAY
                pyxel.text(SCREEN_W // 2 - text_w // 2, y, line, color)
            y += 14


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
