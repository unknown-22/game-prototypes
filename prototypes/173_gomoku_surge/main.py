"""173_gomoku_surge - GOMOKU SURGE

Color-match Gomoku (五目並べ / 5-in-a-row). Player places colored stones on an
8x8 grid against an AI opponent. Same-color consecutive placements build COMBO.
COMBO >= 5 triggers SUPER STONE (rainbow mode, free placement anywhere, 3x score).

面白い瞬間 (core fun moment):
同色の石を連続で置いてCOMBOを5まで積み上げ、SUPER STONEが炸裂して
虹色で任意の場所に置け、一気に5連を作って勝利する瞬間。
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any

import pyxel

# ── Constants ──────────────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
FPS = 30
DISPLAY_SCALE = 2

GRID_SIZE = 8
CELL_SIZE = 28
GRID_OFFSET_X = 20
GRID_OFFSET_Y = 20

SUPER_DURATION = 300  # frames (5 seconds at 30 FPS)
SUPER_BONUS_PER_STONE = 200
SUPER_COMBO_THRESHOLD = 5
BASE_SCORE = 100
COMBO_BONUS = 50
WIN_BONUS = 500
HEAT_PER_WRONG = 15
MAX_HEAT = 100
HEAT_DECAY_PER_FRAME = 0.005

# Colors
COL_BLACK = 0
COL_NAVY = 1
COL_PURPLE = 2
COL_GREEN = 3
COL_BROWN = 4
COL_DARK_BLUE = 5
COL_LIGHT_BLUE = 6
COL_WHITE = 7
COL_RED = 8
COL_ORANGE = 9
COL_YELLOW = 10
COL_LIME = 11
COL_CYAN = 12
COL_GRAY = 13
COL_PINK = 14
COL_PEACH = 15

PLAYER_COLORS: tuple[int, ...] = (COL_RED, COL_GREEN, COL_DARK_BLUE, COL_YELLOW)
AI_COLOR = COL_GRAY

RAINBOW_COLORS: tuple[int, ...] = (COL_RED, COL_ORANGE, COL_YELLOW, COL_GREEN, COL_CYAN, COL_PINK)

FONT_PATH = Path(__file__).with_name("k8x12.bdf")


# ── Enums ──────────────────────────────────────────────────────────────────────
class Phase(IntEnum):
    TITLE = 0
    PLAYING = 1
    VICTORY = 2
    GAME_OVER = 3


# ── Data Classes ───────────────────────────────────────────────────────────────
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
    x: float
    y: float
    text: str
    color: int
    life: int
    vy: float


# ── Game ───────────────────────────────────────────────────────────────────────
class Game:
    def __init__(self) -> None:
        pyxel.init(
            SCREEN_W, SCREEN_H,
            title="GOMOKU SURGE",
            display_scale=DISPLAY_SCALE,
            fps=FPS,
        )
        self._font: pyxel.Font | None = None
        if FONT_PATH.exists():
            self._font = pyxel.Font(str(FONT_PATH))
        self._rng = random.Random()
        self._ai_difficulty: float = 0.7
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── Reset ──────────────────────────────────────────────────────────────
    def reset(self) -> None:
        self._rng = random.Random()
        self.grid: list[list[int]] = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.current_color_index: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.heat: float = 0.0
        self.phase: Phase = Phase.TITLE
        self.turn: int = 0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.winner: str = ""
        self.last_move: tuple[int, int] | None = None
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self._frame_count: int = 0
        self._prev_btn: bool = False

    # ── Public helpers for tests ───────────────────────────────────────────
    def _init_state(self) -> None:
        """Initialize state for a new round (callable from tests)."""
        self.grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.current_color_index = 0
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.heat = 0.0
        self.phase = Phase.PLAYING
        self.turn = 0
        self.super_mode = False
        self.super_timer = 0
        self.winner = ""
        self.last_move = None
        self.particles.clear()
        self.floats.clear()
        self._frame_count = 0

    # ── Input ──────────────────────────────────────────────────────────────
    @staticmethod
    def _read_confirm() -> bool:
        return pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN)

    @staticmethod
    def _read_click() -> bool:
        return pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)

    # ── Grid Helpers ───────────────────────────────────────────────────────
    @staticmethod
    def _pos_to_cell(mx: int, my: int) -> tuple[int, int]:
        col = (mx - GRID_OFFSET_X) // CELL_SIZE
        row = (my - GRID_OFFSET_Y) // CELL_SIZE
        return (col, row)

    @staticmethod
    def _cell_to_pos(col: int, row: int) -> tuple[int, int]:
        x = GRID_OFFSET_X + col * CELL_SIZE + CELL_SIZE // 2
        y = GRID_OFFSET_Y + row * CELL_SIZE + CELL_SIZE // 2
        return (x, y)

    def _is_valid_cell(self, col: int, row: int) -> bool:
        if not (0 <= col < GRID_SIZE and 0 <= row < GRID_SIZE):
            return False
        return self.grid[row][col] == 0

    # ── Current Player Color ───────────────────────────────────────────────
    def _current_player_color(self) -> int:
        return PLAYER_COLORS[self.current_color_index]

    def _cycle_color(self) -> None:
        self.current_color_index = (self.current_color_index + 1) % len(PLAYER_COLORS)

    # ── Place Stone ────────────────────────────────────────────────────────
    def _place_stone(self, col: int, row: int, color: int) -> dict[str, Any]:
        """Place a stone and return info dict. Testable pure logic."""
        self.grid[row][col] = color
        info: dict[str, Any] = {"col": col, "row": row, "color": color, "combo_added": 0, "score_added": 0, "super_activated": False}

        current = self._current_player_color()
        matched = self.super_mode or (color == current)

        if matched:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            multiplier = self.combo
            points = BASE_SCORE + multiplier * COMBO_BONUS
            if self.super_mode:
                points *= 3
                points += SUPER_BONUS_PER_STONE
            self.score += points
            info["score_added"] = points
            info["combo_added"] = 1

            if not self.super_mode and self.combo >= SUPER_COMBO_THRESHOLD:
                self.super_mode = True
                self.super_timer = SUPER_DURATION
                info["super_activated"] = True
        else:
            self.combo = 0
            self.heat += HEAT_PER_WRONG
            info["heat_added"] = HEAT_PER_WRONG

        self.last_move = (col, row)
        return info

    # ── Win Detection ──────────────────────────────────────────────────────
    @staticmethod
    def _count_direction(grid: list[list[int]], col: int, row: int, dc: int, dr: int, color: int) -> int:
        count = 0
        c, r = col + dc, row + dr
        while 0 <= c < GRID_SIZE and 0 <= r < GRID_SIZE and grid[r][c] == color:
            count += 1
            c += dc
            r += dr
        return count

    @staticmethod
    def _check_win(grid: list[list[int]], col: int, row: int, color: int) -> bool:
        """Check if placing stone at (col,row) with given color creates 5-in-a-row."""
        if color == 0:
            return False
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
        for dc, dr in directions:
            total = 1 + Game._count_direction(grid, col, row, dc, dr, color) + Game._count_direction(grid, col, row, -dc, -dr, color)
            if total >= 5:
                return True
        return False

    # ── Board Full Check ───────────────────────────────────────────────────
    @staticmethod
    def _is_board_full(grid: list[list[int]]) -> bool:
        for row in grid:
            for cell in row:
                if cell == 0:
                    return False
        return True

    # ── AI Logic ───────────────────────────────────────────────────────────
    @staticmethod
    def _ai_find_best_move(
        grid: list[list[int]],
        ai_color: int,
        player_colors: tuple[int, ...],
        difficulty: float,
        rng: random.Random,
    ) -> tuple[int, int] | None:
        """Find best AI move. Returns (col, row) or None if no valid move."""
        empty_cells: list[tuple[int, int]] = []
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                if grid[row][col] == 0:
                    empty_cells.append((col, row))

        if not empty_cells:
            return None

        # Priority 1: AI has 4-in-a-row, complete to 5
        for col, row in empty_cells:
            # Temporarily place
            grid[row][col] = ai_color
            won = Game._check_win(grid, col, row, ai_color)
            grid[row][col] = 0
            if won:
                return (col, row)

        # Priority 2: Block player's 4-in-a-row (any player color)
        for col, row in empty_cells:
            for p_color in player_colors:
                grid[row][col] = p_color
                won = Game._check_win(grid, col, row, p_color)
                grid[row][col] = 0
                if won:
                    return (col, row)

        # Priority 3: Block player's 3-in-a-row with probability
        if difficulty > 0 and rng.random() < difficulty:
            for col, row in empty_cells:
                for p_color in player_colors:
                    # Check if this placement makes it 4 (player has 3 already)
                    grid[row][col] = p_color
                    # Count how many in a row this creates
                    if any(
                        1 + Game._count_direction(grid, col, row, dc, dr, p_color)
                        + Game._count_direction(grid, col, row, -dc, -dr, p_color) >= 4
                        for dc, dr in [(1, 0), (0, 1), (1, 1), (1, -1)]
                    ):
                        grid[row][col] = 0
                        return (col, row)
                    grid[row][col] = 0

        # Priority 4: Prefer center and near existing stones
        center = GRID_SIZE // 2
        candidates: list[tuple[float, tuple[int, int]]] = []
        for col, row in empty_cells:
            dist_center = (col - center) ** 2 + (row - center) ** 2
            # Count nearby stones
            nearby = 0
            for dc in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    nc, nr = col + dc, row + dr
                    if 0 <= nc < GRID_SIZE and 0 <= nr < GRID_SIZE and grid[nr][nc] != 0:
                        nearby += 1
            score = -dist_center * 0.5 + nearby * 2 + rng.uniform(0, 3)
            candidates.append((score, (col, row)))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    # ── AI Turn ────────────────────────────────────────────────────────────
    def _ai_turn(self) -> dict[str, Any] | None:
        move = self._ai_find_best_move(
            self.grid, AI_COLOR, PLAYER_COLORS, self._ai_difficulty, self._rng,
        )
        if move is None:
            return None
        col, row = move
        self.grid[row][col] = AI_COLOR
        info: dict[str, Any] = {"col": col, "row": row, "ai_win": False}
        if self._check_win(self.grid, col, row, AI_COLOR):
            info["ai_win"] = True
            self.winner = "ai"
            self.phase = Phase.GAME_OVER
        return info

    # ── Particles ──────────────────────────────────────────────────────────
    def _spawn_placement_particles(self, col: int, row: int, color: int, count: int = 10) -> None:
        cx, cy = self._cell_to_pos(col, row)
        for _ in range(count):
            angle = self._rng.uniform(0, 6.283)
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(Particle(
                x=cx, y=cy,
                vx=0.0, vy=0.0,
                color=color,
                life=self._rng.randint(20, 40),
            ))
            self.particles[-1].vx = math.cos(angle) * speed
            self.particles[-1].vy = math.sin(angle) * speed

    def _spawn_super_particles(self) -> None:
        for _ in range(40):
            side = self._rng.randint(0, 3)
            if side == 0:
                px = float(GRID_OFFSET_X + self._rng.randint(0, GRID_SIZE * CELL_SIZE))
                py = float(GRID_OFFSET_Y)
            elif side == 1:
                px = float(GRID_OFFSET_X + self._rng.randint(0, GRID_SIZE * CELL_SIZE))
                py = float(GRID_OFFSET_Y + GRID_SIZE * CELL_SIZE)
            elif side == 2:
                px = float(GRID_OFFSET_X)
                py = float(GRID_OFFSET_Y + self._rng.randint(0, GRID_SIZE * CELL_SIZE))
            else:
                px = float(GRID_OFFSET_X + GRID_SIZE * CELL_SIZE)
                py = float(GRID_OFFSET_Y + self._rng.randint(0, GRID_SIZE * CELL_SIZE))
            self.particles.append(Particle(
                x=px, y=py,
                vx=self._rng.uniform(-2.0, 2.0),
                vy=self._rng.uniform(-2.0, 2.0),
                color=self._rng.choice(RAINBOW_COLORS),
                life=self._rng.randint(15, 35),
            ))

    def _spawn_floating_text(self, col: int, row: int, text: str, color: int, life: int = 45) -> None:
        cx, cy = self._cell_to_pos(col, row)
        self.floats.append(FloatingText(
            x=cx, y=cy - 10, text=text, color=color, life=life, vy=-0.5,
        ))

    def _update_particles(self) -> None:
        survived: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                survived.append(p)
        self.particles = survived

    def _update_floats(self) -> None:
        survived: list[FloatingText] = []
        for f in self.floats:
            f.y += f.vy
            f.life -= 1
            if f.life > 0:
                survived.append(f)
        self.floats = survived

    # ── Text Helpers ───────────────────────────────────────────────────────
    def _text_center(self, s: str, y: int, col: int) -> None:
        if self._font is not None:
            w = self._font.text_width(s)
            x = (SCREEN_W - w) // 2
            pyxel.text(x + 1, y + 1, s, COL_BLACK, self._font)
            pyxel.text(x, y, s, col, self._font)
        else:
            pyxel.text((SCREEN_W - len(s) * 4) // 2, y, s, col)

    def _text(self, s: str, x: int, y: int, col: int) -> None:
        if self._font is not None:
            pyxel.text(x + 1, y + 1, s, COL_BLACK, self._font)
            pyxel.text(x, y, s, col, self._font)
        else:
            pyxel.text(x, y, s, col)

    # ── Update ─────────────────────────────────────────────────────────────
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if self._read_confirm():
                self._init_state()
            return

        if self.phase == Phase.VICTORY or self.phase == Phase.GAME_OVER:
            self._update_particles()
            self._update_floats()
            if self._read_confirm():
                self._init_state()
            return

        # ── PLAYING ──
        self._frame_count += 1

        # Heat decay
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY_PER_FRAME)

        # Super mode timer
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0

        # Player click
        if self._read_click():
            col, row = self._pos_to_cell(pyxel.mouse_x, pyxel.mouse_y)
            if self._is_valid_cell(col, row):
                color = self._current_player_color()
                info = self._place_stone(col, row, color)
                self._spawn_placement_particles(col, row, color)

                if info.get("super_activated"):
                    self._spawn_super_particles()
                    self._spawn_floating_text(col, row, "SUPER STONE!", COL_CYAN, 60)

                if info.get("combo_added"):
                    self._spawn_floating_text(col, row, f"+{info['score_added']}", COL_WHITE, 45)
                    if self.combo >= SUPER_COMBO_THRESHOLD:
                        self._spawn_floating_text(col, row, f"COMBO x{self.combo}!", color, 45)
                    elif self.combo > 1:
                        self._spawn_floating_text(col, row, f"COMBO x{self.combo}", color, 35)
                elif info.get("heat_added"):
                    self._spawn_floating_text(col, row, "WRONG COLOR", COL_RED, 30)

                # Check player win
                if self._check_win(self.grid, col, row, color):
                    self.winner = "player"
                    self.score += WIN_BONUS
                    self.phase = Phase.VICTORY
                    self._spawn_super_particles()
                else:
                    # Check board full
                    if self._is_board_full(self.grid):
                        self.phase = Phase.GAME_OVER
                    elif self.phase == Phase.PLAYING:
                        # AI turn
                        ai_info = self._ai_turn()
                        if ai_info and not ai_info.get("ai_win"):
                            # Check board full after AI
                            if self._is_board_full(self.grid):
                                self.phase = Phase.GAME_OVER

                # Check heat
                if self.heat >= MAX_HEAT:
                    self.phase = Phase.GAME_OVER

                # Cycle player color
                self._cycle_color()

                self.turn += 1

        self._update_particles()
        self._update_floats()

    # ── Draw ───────────────────────────────────────────────────────────────
    def draw(self) -> None:
        pyxel.cls(COL_NAVY)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        self._draw_grid()
        self._draw_stones()
        self._draw_particles()
        self._draw_hud()

        if self.phase == Phase.VICTORY:
            self._draw_game_over("YOU WIN!")
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over("GAME OVER")

    def _draw_title(self) -> None:
        self._text_center("GOMOKU SURGE", 30, COL_CYAN)
        self._text_center("Click: Place Stone", 80, COL_WHITE)
        self._text_center("Match colors for COMBO chain", 100, COL_WHITE)
        self._text_center("5-in-a-row to WIN", 125, COL_YELLOW)
        self._text_center("COMBO 5 = SUPER STONE", 145, COL_CYAN)
        self._text_center("Rainbow mode / Score x3", 160, COL_CYAN)
        self._text_center("Wrong color adds HEAT", 180, COL_RED)
        self._text_center("HEAT 100 = Game Over", 195, COL_RED)
        self._text_center("SPACE: Start / Restart", 220, COL_LIME)

    def _draw_game_over(self, title: str) -> None:
        overlay_col = COL_BLACK if self.phase == Phase.GAME_OVER else COL_NAVY
        pyxel.rect(60, 40, 200, 120, overlay_col)
        pyxel.rectb(60, 40, 200, 120, COL_WHITE)
        self._text_center(title, 55, COL_CYAN if "WIN" in title else COL_RED)
        self._text_center(f"Score: {self.score}", 85, COL_WHITE)
        self._text_center(f"Max Combo: x{self.max_combo}", 105, COL_YELLOW)
        self._text_center(f"Turns: {self.turn}", 125, COL_GRAY)
        self._text_center("SPACE to Restart", 150, COL_LIME)

    # ── Grid Drawing ───────────────────────────────────────────────────────
    def _draw_grid(self) -> None:
        # Draw grid background
        grid_px = GRID_SIZE * CELL_SIZE
        pyxel.rect(GRID_OFFSET_X, GRID_OFFSET_Y, grid_px, grid_px, COL_DARK_BLUE)

        # Super mode rainbow border
        if self.super_mode:
            flash_idx = (self._frame_count // 4) % len(RAINBOW_COLORS)
            border_color = RAINBOW_COLORS[flash_idx]
            pyxel.rectb(GRID_OFFSET_X - 2, GRID_OFFSET_Y - 2, grid_px + 4, grid_px + 4, border_color)
        else:
            pyxel.rectb(GRID_OFFSET_X, GRID_OFFSET_Y, grid_px, grid_px, COL_WHITE)

        # Grid lines
        for i in range(GRID_SIZE + 1):
            line_pos = GRID_OFFSET_X + i * CELL_SIZE
            pyxel.line(line_pos, GRID_OFFSET_Y, line_pos, GRID_OFFSET_Y + grid_px, COL_LIGHT_BLUE)
        for i in range(GRID_SIZE + 1):
            line_pos = GRID_OFFSET_Y + i * CELL_SIZE
            pyxel.line(GRID_OFFSET_X, line_pos, GRID_OFFSET_X + grid_px, line_pos, COL_LIGHT_BLUE)

        # Hover highlight
        if self.phase == Phase.PLAYING:
            col, row = self._pos_to_cell(pyxel.mouse_x, pyxel.mouse_y)
            if self._is_valid_cell(col, row):
                cx = GRID_OFFSET_X + col * CELL_SIZE
                cy = GRID_OFFSET_Y + row * CELL_SIZE
                pyxel.rectb(cx, cy, CELL_SIZE, CELL_SIZE, COL_WHITE)

    def _draw_stones(self) -> None:
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                color = self.grid[row][col]
                if color == 0:
                    # Empty cell indicator
                    cx = GRID_OFFSET_X + col * CELL_SIZE + CELL_SIZE // 2
                    cy = GRID_OFFSET_Y + row * CELL_SIZE + CELL_SIZE // 2
                    pyxel.circb(cx, cy, CELL_SIZE // 2 - 2, COL_LIGHT_BLUE)
                else:
                    cx = GRID_OFFSET_X + col * CELL_SIZE + CELL_SIZE // 2
                    cy = GRID_OFFSET_Y + row * CELL_SIZE + CELL_SIZE // 2
                    pyxel.circ(cx, cy, CELL_SIZE // 2 - 2, color)
                    pyxel.circb(cx, cy, CELL_SIZE // 2 - 2, COL_WHITE)

                # Highlight last move
                if self.last_move and self.last_move == (col, row):
                    cx = GRID_OFFSET_X + col * CELL_SIZE + CELL_SIZE // 2
                    cy = GRID_OFFSET_Y + row * CELL_SIZE + CELL_SIZE // 2
                    pyxel.circb(cx, cy, CELL_SIZE // 2, COL_WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 40
            radius = max(1, int(2 * alpha))
            pyxel.circ(int(p.x), int(p.y), radius, p.color)

    def _draw_hud(self) -> None:
        # Score
        self._text(f"SCORE: {self.score}", 4, 4, COL_WHITE)

        # Current color
        color = self._current_player_color()
        x_start = SCREEN_W - 40
        self._text("COLOR:", 250, 4, COL_GRAY)
        pyxel.rect(x_start - 4, 4, 20 + 4, 10 + 4, COL_BLACK)
        pyxel.rect(x_start, 6, 20, 10, color)
        pyxel.rectb(x_start, 6, 20, 10, COL_WHITE)

        # Combo
        if self.combo > 0:
            combo_color = COL_YELLOW if self.combo >= SUPER_COMBO_THRESHOLD else COL_CYAN
            self._text(f"COMBO: x{self.combo}", 4, 22, combo_color)

        # Max combo
        if self.max_combo > 0:
            self._text(f"MAX: x{self.max_combo}", 4, 36, COL_GRAY)

        # Super mode indicator
        if self.super_mode:
            flash_idx = (self._frame_count // 6) % len(RAINBOW_COLORS)
            sc = RAINBOW_COLORS[flash_idx]
            sec_left = self.super_timer / FPS
            self._text(f"SUPER STONE! {sec_left:.1f}s", 120, 4, sc)

        # Turn
        self._text(f"TURN: {self.turn}", SCREEN_W - 70, 22, COL_GRAY)

        # Heat bar
        bar_x = 4
        bar_y = SCREEN_H - 16
        bar_w = 100
        bar_h = 6
        self._text("HEAT", bar_x, bar_y - 10, COL_GRAY)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, COL_WHITE)
        ratio = min(1.0, self.heat / MAX_HEAT)
        fill_w = int(bar_w * ratio)
        bar_col = COL_GREEN if ratio < 0.5 else (COL_YELLOW if ratio < 0.8 else COL_RED)
        pyxel.rect(bar_x, bar_y, fill_w, bar_h, bar_col)
        self._text(f"{self.heat:.0f}", bar_x + bar_w + 4, bar_y - 1, bar_col)

    # ── Change font ────────────────────────────────────────────────────────
    def change_font(self, font: pyxel.Font) -> None:
        self._font = font


# ── Make game (for tests) ────────────────────────────────────────────────────
def _make_game(rng: random.Random | None = None) -> Game:
    """Create a minimal Game instance for testing (no pyxel.init/run)."""
    g = Game.__new__(Game)  # bypass __init__
    g._font = None
    g._rng = rng if rng is not None else random.Random(42)
    g.reset()
    return g


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
