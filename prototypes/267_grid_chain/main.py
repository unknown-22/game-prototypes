"""GRID CHAIN — Color Sudoku with COMBO Chain Mechanics

The most fun moment:
    同色を連続で正しく配置してCOMBOを4以上に積み上げ、
    SUPER PLACEが発動して虹色の盤面で一気にスコア3倍になる瞬間が面白い。

Core loop: Select a color, place it in the 4x4 grid satisfying Sudoku rules.
Same-color consecutive valid placements build COMBO chain.
COMBO>=4 triggers SUPER PLACE (rainbow mode, all placements auto-valid, 3x score).
HEAT punishes mismatches and accumulates with time.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

SCREEN_W = 320
SCREEN_H = 240
FPS = 30
CELL_SIZE = 36
CELL_GAP = 2
GRID_X = 88
GRID_Y = 32
GRID_COLS = 4
GRID_ROWS = 4
COLORS: list[int] = [8, 11, 5, 10]  # RED, LIME, DARK_BLUE, YELLOW
COLOR_NAMES: list[str] = ["RED", "LIME", "DARK_BLUE", "YELLOW"]
PALETTE_Y = 200
PALETTE_BTN_W = 48
PALETTE_BTN_H = 28
SUPER_DURATION = 300
GAME_DURATION = 1800
GIVENS_COUNT = 5
HEAT_MAX = 100.0
HEAT_DECAY = 0.02
HEAT_MISMATCH = 15.0
HEAT_TIME_PRESSURE = 0.05

ROUND_CLEAR_FRAMES = 60
RESTART_KEYS = {pyxel.KEY_R}


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    ROUND_CLEAR = auto()
    GAME_OVER = auto()


@dataclass
class Cell:
    color: int = 0
    locked: bool = False


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
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="GRID CHAIN", fps=FPS)
        self._rng = random.Random()
        self.best_score = 0
        self._reset_game()
        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    def _reset_game(self) -> None:
        self.phase = Phase.TITLE
        self.grid: list[list[Cell]] = []
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.round_num = 0
        self.super_timer = 0
        self.round_clear_timer = 0
        self.timer = GAME_DURATION
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._selected_color = 0
        self._prev_color = 0
        self._new_round()

    def _new_round(self) -> None:
        self.grid = [[Cell() for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        self.round_num += 1
        self.combo = 0
        self.super_timer = 0
        self._generate_givens()

    def _generate_givens(self) -> None:
        placed = 0
        attempts = 0
        while placed < GIVENS_COUNT and attempts < 200:
            col = self._rng.randint(0, GRID_COLS - 1)
            row = self._rng.randint(0, GRID_ROWS - 1)
            if self.grid[row][col].color != 0:
                attempts += 1
                continue
            available = [c for c in COLORS if self._is_valid_placement(col, row, c)]
            if available:
                color = self._rng.choice(available)
                self.grid[row][col].color = color
                self.grid[row][col].locked = True
                placed += 1
            attempts += 1

        if placed < GIVENS_COUNT:
            self._generate_givens()

    def _is_valid_placement(self, col: int, row: int, color: int) -> bool:
        if color == 0:
            return False
        for c in range(GRID_COLS):
            if c != col and self.grid[row][c].color == color:
                return False
        for r in range(GRID_ROWS):
            if r != row and self.grid[r][col].color == color:
                return False
        return True

    def _is_grid_complete(self) -> bool:
        for row in self.grid:
            for cell in row:
                if cell.color == 0:
                    return False
        return True

    def _place_color(self, col: int, row: int) -> None:
        cell = self.grid[row][col]
        if cell.locked or cell.color != 0:
            return

        color = COLORS[self._selected_color]
        gx = GRID_X + col * (CELL_SIZE + CELL_GAP) + CELL_SIZE // 2
        gy = GRID_Y + row * (CELL_SIZE + CELL_GAP) + CELL_SIZE // 2

        if self.super_timer > 0:
            cell.color = color
            base_score = 10 * max(1, self.combo) * 3
            self.score += base_score
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            self._prev_color = self._selected_color
            self._spawn_particles(gx, gy, color, 10)
            self._spawn_floating_text(gx, gy - 10, f"+{base_score} SUPER", 9)
        elif self._is_valid_placement(col, row, color):
            cell.color = color
            same_color = self._selected_color == self._prev_color
            if same_color:
                self.combo += 1
            else:
                self.combo = 1
            base_score = 10 * self.combo
            self.score += base_score
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            self._prev_color = self._selected_color
            self._spawn_particles(gx, gy, color, 4)
            self._spawn_floating_text(gx, gy - 10, f"+{base_score}", 7)
            if self.combo >= 4:
                self.super_timer = SUPER_DURATION
                self._spawn_floating_text(gx + 20, gy - 20, "SUPER!", 10)
        else:
            self.combo = 0
            self._prev_color = 0
            self.heat = min(HEAT_MAX, self.heat + HEAT_MISMATCH)
            self._spawn_particles(gx, gy, 8, 3)
            self._spawn_floating_text(gx, gy - 10, "NO!", 8)

    def _step_game_logic(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
        self.timer -= 1
        self._update_heat()
        if self.heat >= HEAT_MAX or self.timer <= 0:
            self.phase = Phase.GAME_OVER
            if self.score > self.best_score:
                self.best_score = self.score

    def _update_heat(self) -> None:
        if self.super_timer > 0:
            return
        self.heat = max(0.0, self.heat - HEAT_DECAY)
        self.heat = min(HEAT_MAX, self.heat + HEAT_TIME_PRESSURE)

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = self._rng.randint(10, 20)
            self.particles.append(Particle(x, y, vx, vy, life, color))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x, y, text, 30, color))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def update(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self._reset_game()
            return

        self._update_particles()
        self._update_floating_texts()

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.ROUND_CLEAR:
            self._update_round_clear()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self.phase = Phase.PLAYING
            self._reset_game()
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self._step_game_logic()
        if self.phase == Phase.GAME_OVER:
            return

        for i in range(4):
            key = getattr(pyxel, f"KEY_{i + 1}")
            if pyxel.btnp(key):
                self._selected_color = i
                break

        mx = pyxel.mouse_x
        my = pyxel.mouse_y

        for i in range(4):
            bx = 48 + i * 64
            if bx <= mx < bx + PALETTE_BTN_W and PALETTE_Y <= my < PALETTE_Y + PALETTE_BTN_H:
                if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                    self._selected_color = i
                    break

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            for row in range(GRID_ROWS):
                for col in range(GRID_COLS):
                    cx = GRID_X + col * (CELL_SIZE + CELL_GAP)
                    cy = GRID_Y + row * (CELL_SIZE + CELL_GAP)
                    if cx <= mx < cx + CELL_SIZE and cy <= my < cy + CELL_SIZE:
                        self._place_color(col, row)
                        if self._is_grid_complete() and self.phase == Phase.PLAYING:
                            bonus = 500 * self.round_num
                            self.score += bonus
                            self._spawn_floating_text(160, 120, f"BONUS +{bonus}", 10)
                            self._spawn_particles(160, 120, 10, 18)
                            self.phase = Phase.ROUND_CLEAR
                            self.round_clear_timer = ROUND_CLEAR_FRAMES
                        return
                    continue

    def _update_round_clear(self) -> None:
        self.round_clear_timer -= 1
        if self.round_clear_timer <= 0:
            self._new_round()
            self.phase = Phase.PLAYING
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self._new_round()
            self.phase = Phase.PLAYING

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self._reset_game()
            self.phase = Phase.PLAYING

    def draw(self) -> None:
        pyxel.cls(0)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.ROUND_CLEAR:
            self._draw_playing()
            self._draw_round_clear()
        elif self.phase == Phase.GAME_OVER:
            self._draw_playing()
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(112, 80, "GRID CHAIN", 7)
        pyxel.text(96, 100, "Color Sudoku Puzzle", 5)
        pyxel.text(72, 130, "Match 4 colors in each row and column", 6)
        pyxel.text(80, 150, "Same-color chains build COMBO!", 11)
        pyxel.text(60, 170, "COMBO>=4 triggers SUPER PLACE mode", 10)
        pyxel.text(96, 200, "Press ENTER to start", 7)
        pyxel.text(80, 218, "Keys 1-4 or click palette to select color", 13)

    def _draw_playing(self) -> None:
        self._draw_grid()
        self._draw_palette()
        self._draw_hud()
        for p in self.particles:
            alpha = p.life / 20
            r = max(1, int(3 * alpha))
            pyxel.circ(int(p.x), int(p.y), r, p.color)
        for ft in self.floating_texts:
            alpha = ft.life / 30
            col = ft.color if alpha > 0.4 else 13
            pyxel.text(int(ft.x), int(ft.y), ft.text, col)

    def _draw_grid(self) -> None:
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                cx = GRID_X + col * (CELL_SIZE + CELL_GAP)
                cy = GRID_Y + row * (CELL_SIZE + CELL_GAP)
                cell = self.grid[row][col]
                if cell.color != 0:
                    pyxel.rect(cx, cy, CELL_SIZE, CELL_SIZE, cell.color)
                else:
                    pyxel.rect(cx, cy, CELL_SIZE, CELL_SIZE, 1)
                if cell.locked:
                    pyxel.rectb(cx, cy, CELL_SIZE, CELL_SIZE, 7)
                    pyxel.rectb(cx + 1, cy + 1, CELL_SIZE - 2, CELL_SIZE - 2, 7)
                else:
                    pyxel.rectb(cx, cy, CELL_SIZE, CELL_SIZE, 5)
        if self.super_timer > 0:
            hue = (pyxel.frame_count // 4) % 4
            rainbow = [8, 10, 11, 12]
            color = rainbow[hue]
            bx = GRID_X - 2
            by = GRID_Y - 2
            bw = GRID_COLS * (CELL_SIZE + CELL_GAP) - CELL_GAP + 4
            bh = GRID_ROWS * (CELL_SIZE + CELL_GAP) - CELL_GAP + 4
            pyxel.rectb(bx, by, bw, bh, color)

    def _draw_palette(self) -> None:
        for i, color in enumerate(COLORS):
            bx = 48 + i * 64
            pyxel.rect(bx, PALETTE_Y, PALETTE_BTN_W, PALETTE_BTN_H, color)
            if i == self._selected_color:
                pyxel.rectb(bx - 1, PALETTE_Y - 1, PALETTE_BTN_W + 2, PALETTE_BTN_H + 2, 7)
                pyxel.rectb(bx - 2, PALETTE_Y - 2, PALETTE_BTN_W + 4, PALETTE_BTN_H + 4, 7)
            else:
                pyxel.rectb(bx, PALETTE_Y, PALETTE_BTN_W, PALETTE_BTN_H, 5)
            pyxel.text(bx + 4, PALETTE_Y + PALETTE_BTN_H + 4, str(i + 1), 13)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", 7)
        pyxel.text(4, 14, f"ROUND: {self.round_num}", 7)
        combo_color = 10 if self.combo >= 4 else (11 if self.combo >= 2 else 7)
        pyxel.text(SCREEN_W - 100, 4, f"COMBO: {self.combo}", combo_color)
        secs = max(0, self.timer // FPS)
        timer_color = 8 if secs <= 10 else 7
        pyxel.text(4, 24, f"TIME: {secs}s", timer_color)
        if self.super_timer > 0:
            super_secs = self.super_timer // FPS
            pyxel.text(SCREEN_W - 100, 14, f"SUPER: {super_secs}s", 10)
        pyxel.text(4, 38, "HEAT", 7)
        bar_w = 100
        bar_x = 40
        bar_y = 36
        pyxel.rectb(bar_x, bar_y, bar_w, 6, 13)
        heat_w = int(bar_w * self.heat / HEAT_MAX)
        heat_color = 8 if self.heat >= 70 else (9 if self.heat >= 40 else 10)
        pyxel.rect(bar_x, bar_y, heat_w, 6, heat_color)

    def _draw_round_clear(self) -> None:
        mask_color = 1 if (pyxel.frame_count // 15) % 2 == 0 else 0
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, mask_color)
        pyxel.text(100, 80, "ROUND CLEAR!", 10)
        pyxel.text(60, 100, f"Bonus: +{500 * self.round_num}", 7)
        pyxel.text(80, 130, "Press SPACE to continue", 7)

    def _draw_game_over(self) -> None:
        mask_color = 1 if (pyxel.frame_count // 15) % 2 == 0 else 0
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, mask_color)
        pyxel.text(108, 60, "GAME OVER", 8)
        if self.heat >= HEAT_MAX:
            pyxel.text(112, 76, "OVERHEAT!", 8)
        pyxel.text(100, 100, f"Score: {self.score}", 7)
        pyxel.text(80, 120, f"Max Combo: {self.max_combo}", 7)
        pyxel.text(80, 140, f"Rounds: {self.round_num - 1}", 7)
        pyxel.text(100, 170, "Press ENTER to retry", 7)


if __name__ == "__main__":
    Game()
