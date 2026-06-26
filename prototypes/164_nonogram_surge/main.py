"""NONOGRAM SURGE — Color Nonogram with COMBO chain mechanics."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pyxel

# --- Constants ---
SCREEN_W = 320
SCREEN_H = 240
DISPLAY_SCALE = 2
GRID_X = 80
GRID_Y = 55
CELL = 20
ROWS = 8
COLS = 8

# Color palette
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

CELL_COLORS: tuple[int, int, int, int] = (8, 3, 5, 10)  # RED, GREEN, DARK_BLUE, YELLOW
CELL_COLOR_NAMES: tuple[str, str, str, str] = ("RED", "GREEN", "BLUE", "YELLOW")

# Phases
TITLE = 0
PLAYING = 1
GAME_OVER = 2


# --- Data Classes ---
@dataclass
class HintRun:
    """A run of consecutive same-color cells in a row or column."""
    color_idx: int  # 0-3 index into CELL_COLORS
    count: int


@dataclass
class Puzzle:
    """A pre-defined nonogram puzzle."""
    name: str
    solution: list[list[int]]  # 8x8, -1=empty, 0-3=color index
    row_hints: list[list[HintRun]]
    col_hints: list[list[HintRun]]


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


# --- Pre-defined Puzzles ---
def _make_puzzle_solutions() -> list[list[list[int]]]:
    """Return list of 8x8 solution grids."""
    return [
        # Puzzle 0 — "DIAMOND"
        [
            [-1, -1, -1,  0, -1, -1, -1, -1],
            [-1, -1,  0,  0,  0, -1, -1, -1],
            [-1,  0,  0,  0,  0,  0, -1, -1],
            [ 0,  0,  0,  0,  0,  0,  0, -1],
            [-1,  0,  0,  0,  0,  0, -1, -1],
            [-1, -1,  0,  0,  0, -1,  1, -1],
            [-1, -1, -1,  0, -1, -1,  1,  1],
            [-1, -1, -1, -1, -1, -1, -1,  1],
        ],
        # Puzzle 1 — "HEART"
        [
            [-1,  0, -1, -1, -1,  0, -1, -1],
            [ 0,  0,  0, -1,  0,  0,  0, -1],
            [ 0,  0,  0,  0,  0,  0,  0,  0],
            [-1,  0,  0,  0,  0,  0,  0, -1],
            [-1, -1,  0,  0,  0,  0, -1, -1],
            [-1, -1, -1,  0,  0, -1, -1, -1],
            [-1, -1, -1, -1,  1, -1, -1, -1],
            [-1, -1, -1,  2,  2,  2, -1, -1],
        ],
        # Puzzle 2 — "CROSS"
        [
            [ 0, -1, -1, -1, -1, -1, -1,  0],
            [-1,  1, -1, -1, -1, -1,  1, -1],
            [-1, -1,  2,  2,  2,  2, -1, -1],
            [-1, -1,  2,  2,  2,  2, -1, -1],
            [-1, -1,  2,  2,  2,  2, -1, -1],
            [-1, -1,  2,  2,  2,  2, -1, -1],
            [-1,  1, -1, -1, -1, -1,  1, -1],
            [ 0, -1, -1, -1, -1, -1, -1,  0],
        ],
    ]


PUZZLE_NAMES = ["DIAMOND", "HEART", "CROSS"]


def _compute_hints(solution: list[list[int]]) -> tuple[list[list[HintRun]], list[list[HintRun]]]:
    """Compute row and column hints from a solution grid."""
    num_rows = len(solution)
    num_cols = len(solution[0]) if solution else 0

    row_hints: list[list[HintRun]] = []
    for row in solution:
        runs: list[HintRun] = []
        current_color = -1
        current_count = 0
        for cell in row:
            if cell == current_color and cell != -1:
                current_count += 1
            else:
                if current_color != -1 and current_count > 0:
                    runs.append(HintRun(color_idx=current_color, count=current_count))
                if cell != -1:
                    current_color = cell
                    current_count = 1
                else:
                    current_color = -1
                    current_count = 0
        if current_color != -1 and current_count > 0:
            runs.append(HintRun(color_idx=current_color, count=current_count))
        row_hints.append(runs)

    col_hints: list[list[HintRun]] = []
    for col_idx in range(num_cols):
        runs = []
        current_color = -1
        current_count = 0
        for row_idx in range(num_rows):
            cell = solution[row_idx][col_idx]
            if cell == current_color and cell != -1:
                current_count += 1
            else:
                if current_color != -1 and current_count > 0:
                    runs.append(HintRun(color_idx=current_color, count=current_count))
                if cell != -1:
                    current_color = cell
                    current_count = 1
                else:
                    current_color = -1
                    current_count = 0
        if current_color != -1 and current_count > 0:
            runs.append(HintRun(color_idx=current_color, count=current_count))
        col_hints.append(runs)

    return row_hints, col_hints


# --- Game Class ---
class Game:
    """Main game class for NONOGRAM SURGE."""

    SCREEN_W = SCREEN_W
    SCREEN_H = SCREEN_H
    DISPLAY_SCALE = DISPLAY_SCALE
    GRID_X = GRID_X
    GRID_Y = GRID_Y
    CELL = CELL
    ROWS = ROWS
    COLS = COLS

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="NONOGRAM SURGE", display_scale=DISPLAY_SCALE)
        pyxel.mouse(True)
        self._puzzles: list[Puzzle] = []
        self._load_all_puzzles()
        self.reset()

    def _load_all_puzzles(self) -> None:
        """Build Puzzle objects from solution data."""
        solutions = _make_puzzle_solutions()
        self._puzzles = []
        for i, sol in enumerate(solutions):
            row_hints, col_hints = _compute_hints(sol)
            self._puzzles.append(Puzzle(
                name=PUZZLE_NAMES[i],
                solution=sol,
                row_hints=row_hints,
                col_hints=col_hints,
            ))

    def reset(self) -> None:
        """Reset game state to initial values."""
        self.phase: int = TITLE
        self.grid: list[list[int]] = [[-1] * COLS for _ in range(ROWS)]
        self.puzzle_index: int = 0
        self.puzzle: Puzzle = self._puzzles[0]
        self.selected_color: int = 0
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.timer: float = 120.0
        self.super_active: bool = False
        self.super_timer: float = 0.0
        self.solved_count: int = 0
        self.total_cells: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shake_frames: int = 0
        self.flash_timer: float = 0.0
        self.frame: int = 0
        self._compute_total_cells()

    def _compute_total_cells(self) -> None:
        """Count non-empty cells in the current puzzle solution."""
        self.total_cells = sum(
            1 for row in self.puzzle.solution for cell in row if cell != -1
        )

    def _load_puzzle(self, idx: int) -> None:
        """Load a puzzle by index."""
        self.puzzle_index = idx
        self.puzzle = self._puzzles[idx]
        self.grid = [[-1] * COLS for _ in range(ROWS)]
        self.solved_count = 0
        self.combo = 0
        self.super_active = False
        self.super_timer = 0.0
        self._compute_total_cells()

    def _handle_click(self, row: int, col: int) -> None:
        """Handle a left-click on a grid cell."""
        if self.grid[row][col] != -1:
            return  # already filled

        sol_val = self.puzzle.solution[row][col]

        if sol_val == self.selected_color:
            # CORRECT
            prev_color = self._get_last_filled_color_from_state()
            if prev_color is not None and prev_color == self.selected_color:
                self.combo += 1
            else:
                self.combo = 1
            self._set_last_filled_color(self.selected_color)
            if self.combo > self.max_combo:
                self.max_combo = self.combo

            self.score += 10 + self.combo * 2
            self.solved_count += 1
            self.grid[row][col] = self.selected_color

            # Spawn particles
            cx = GRID_X + col * CELL + CELL / 2
            cy = GRID_Y + row * CELL + CELL / 2
            self._spawn_particles(cx, cy, CELL_COLORS[self.selected_color], 6)
            self._spawn_floating_text(cx, cy - 4, f"+{10 + self.combo * 2}", WHITE)

            # Check SUPER activation
            if self.combo >= 5 and not self.super_active:
                self._activate_super()

            # Check puzzle complete
            if self.solved_count >= self.total_cells:
                self._on_puzzle_complete()

        elif sol_val == -1:
            # WRONG — clicked empty cell
            self.heat += 15
            self.combo = 0
            self._set_last_filled_color(None)
            self.shake_frames = 10
            cx = GRID_X + col * CELL + CELL / 2
            cy = GRID_Y + row * CELL + CELL / 2
            self._spawn_floating_text(cx, cy, "X", RED)

        else:
            # WRONG COLOR
            self.heat += 10
            self.combo = 0
            self._set_last_filled_color(None)
            self.shake_frames = 5
            cx = GRID_X + col * CELL + CELL / 2
            cy = GRID_Y + row * CELL + CELL / 2
            self._spawn_floating_text(cx, cy, "X", RED)

        if self.heat > 100:
            self.heat = 100

    def _handle_right_click(self, row: int, col: int) -> None:
        """Handle a right-click on a grid cell (clear cell)."""
        if self.grid[row][col] == -1:
            return
        self.solved_count -= 1
        self.grid[row][col] = -1

    # Track last filled color for combo logic
    def _get_last_filled_color_from_state(self) -> int | None:
        """Return the color of the last filled cell, for combo color matching."""
        if not hasattr(self, '_last_filled_color'):
            self._last_filled_color: int | None = None
        return self._last_filled_color

    def _set_last_filled_color(self, color: int | None) -> None:
        self._last_filled_color = color

    def _activate_super(self) -> None:
        """Activate SUPER REVEAL mode."""
        self.super_active = True
        self.super_timer = 5.0
        self.flash_timer = 0.3

        # SUPER REVEAL: auto-reveal one unsolved cell per row in a random unsolved row
        unsolved_rows: list[int] = []
        for r in range(ROWS):
            if any(
                self.puzzle.solution[r][c] != -1 and self.grid[r][c] == -1
                for c in range(COLS)
            ):
                unsolved_rows.append(r)

        if unsolved_rows:
            target_row = random.choice(unsolved_rows)
            for c in range(COLS):
                if self.puzzle.solution[target_row][c] != -1 and self.grid[target_row][c] == -1:
                    color = self.puzzle.solution[target_row][c]
                    self.grid[target_row][c] = color
                    self.solved_count += 1
                    # 3x score for super reveal fills
                    bonus = (10 + self.combo * 2) * 3
                    self.score += bonus
                    cx = GRID_X + c * CELL + CELL / 2
                    cy = GRID_Y + target_row * CELL + CELL / 2
                    self._spawn_particles(cx, cy, CELL_COLORS[color], 10)
                    self._spawn_floating_text(cx, cy - 4, f"+{bonus}", YELLOW)

            if self.solved_count >= self.total_cells:
                self._on_puzzle_complete()

    def _update_super(self, dt: float) -> None:
        """Update SUPER mode timer."""
        self.super_timer -= dt
        if self.super_timer <= 0:
            self.super_timer = 0
            self.super_active = False

    def _update_heat(self) -> None:
        """Gradually cool down heat. Game over if heat reaches max."""
        if self.heat >= 100:
            self.phase = GAME_OVER
            return
        self.heat = max(0.0, self.heat - 0.02)

    def _on_puzzle_complete(self) -> None:
        """Handle puzzle completion."""
        self.score += 100 * (self.puzzle_index + 1)
        self.puzzle_index += 1
        if self.puzzle_index >= len(self._puzzles):
            # Wrap to puzzle 0
            self.puzzle_index = 0
        self._load_puzzle(self.puzzle_index)

    def _update_particles(self) -> None:
        """Update particle positions and lifetimes."""
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.2  # gravity
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        """Update floating text positions and lifetimes."""
        for ft in self.floating_texts:
            ft.y -= 1.0
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        """Spawn a burst of particles at a position."""
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(0.5, 2.5)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 1.0
            life = random.randint(8, 20)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, color=color, life=life))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        """Spawn a floating text element."""
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, color=color, life=30))

    def _select_color_from_palette(self, mx: int, my: int) -> int | None:
        """Check if mouse click is on a color palette button. Returns color index or None."""
        for i in range(4):
            bx = 20 + i * 75
            by = 225
            if bx <= mx < bx + 60 and by <= my < by + 15:
                return i
        return None

    def _grid_cell_from_mouse(self, mx: int, my: int) -> tuple[int, int] | None:
        """Convert mouse coordinates to grid cell (row, col). Returns None if outside grid."""
        if mx < GRID_X or my < GRID_Y:
            return None
        col = (mx - GRID_X) // CELL
        row = (my - GRID_Y) // CELL
        if 0 <= col < COLS and 0 <= row < ROWS:
            return (row, col)
        return None

    # --- Main Loop ---
    def update(self) -> None:
        """Update game state each frame."""
        if self.phase == TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self._start_game()
        elif self.phase == PLAYING:
            self.frame += 1
            dt = 1.0 / 60.0
            self.timer -= dt
            if self.timer <= 0:
                self.timer = 0
                self.phase = GAME_OVER
                return

            self._update_heat()
            self._update_particles()
            self._update_floating_texts()
            if self.super_active:
                self._update_super(dt)
            if self.flash_timer > 0:
                self.flash_timer -= dt
            if self.shake_frames > 0:
                self.shake_frames -= 1

            # Mouse input
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                mx = pyxel.mouse_x
                my = pyxel.mouse_y
                color = self._select_color_from_palette(mx, my)
                if color is not None:
                    self.selected_color = color
                else:
                    cell = self._grid_cell_from_mouse(mx, my)
                    if cell is not None:
                        self._handle_click(*cell)

            if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
                mx = pyxel.mouse_x
                my = pyxel.mouse_y
                cell = self._grid_cell_from_mouse(mx, my)
                if cell is not None:
                    self._handle_right_click(*cell)

            # Keyboard color shortcuts
            if pyxel.btnp(pyxel.KEY_1):
                self.selected_color = 0
            if pyxel.btnp(pyxel.KEY_2):
                self.selected_color = 1
            if pyxel.btnp(pyxel.KEY_3):
                self.selected_color = 2
            if pyxel.btnp(pyxel.KEY_4):
                self.selected_color = 3

        elif self.phase == GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
                self.phase = TITLE

    def _start_game(self) -> None:
        """Initialize a fresh game and start playing."""
        self.phase = PLAYING
        self.grid = [[-1] * COLS for _ in range(ROWS)]
        self.puzzle_index = 0
        self.puzzle = self._puzzles[0]
        self.selected_color = 0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = 120.0
        self.super_active = False
        self.super_timer = 0.0
        self.solved_count = 0
        self.particles = []
        self.floating_texts = []
        self.shake_frames = 0
        self.flash_timer = 0.0
        self.frame = 0
        self._last_filled_color = None
        self._compute_total_cells()

    def draw(self) -> None:
        """Render the current game screen."""
        pyxel.cls(BLACK)

        if self.phase == TITLE:
            self._draw_title()
        elif self.phase == PLAYING:
            self._draw_game()
        elif self.phase == GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        """Draw the title screen."""
        title = "NONOGRAM SURGE"
        tw = len(title) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 60, title, YELLOW)

        instructions = [
            "Color Picross with COMBO chains!",
            "",
            "HOW TO PLAY:",
            "  Click grid cells to fill with color",
            "  Match row/column hints to solve",
            "  Same-color chains build COMBO",
            "  COMBO x5 = SUPER REVEAL!",
            "  Right-click to clear a cell",
            "",
            "Keys 1-4 : Select color",
            "Click palette at bottom",
            "",
            "Wrong fills raise HEAT",
            "HEAT=100 = Game Over",
            "",
            "Press SPACE to start",
        ]
        y = 80
        for line in instructions:
            pyxel.text(SCREEN_W // 2 - len(line) * 2, y, line, WHITE)
            y += 9

    def _draw_game(self) -> None:
        """Draw the gameplay screen."""
        # Apply screen shake
        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0:
            shake_x = random.randint(-2, 2)
            shake_y = random.randint(-2, 2)
            pyxel.camera(shake_x, shake_y)

        # HUD background
        pyxel.rect(0, 0, SCREEN_W, 18, NAVY)
        pyxel.text(4, 2, f"SCORE:{self.score:06d}", WHITE)
        pyxel.text(104, 2, f"COMBO:{self.combo}", YELLOW)
        pyxel.text(174, 2, f"MAX:{self.max_combo}", ORANGE)
        timer_str = f"TIME:{int(self.timer):03d}"
        pyxel.text(254, 2, timer_str, WHITE)

        # Heat bar
        heat_bar_x = 4
        heat_bar_y = 13
        heat_bar_w = 72
        heat_bar_h = 4
        pyxel.rectb(heat_bar_x, heat_bar_y, heat_bar_w, heat_bar_h, WHITE)
        heat_fill = int(heat_bar_w * self.heat / 100)
        heat_color = GREEN if self.heat < 50 else (ORANGE if self.heat < 80 else RED)
        pyxel.rect(heat_bar_x, heat_bar_y, heat_fill, heat_bar_h, heat_color)
        pyxel.text(heat_bar_x, 2, "HEAT", WHITE)

        # Puzzle name / progress
        progress_text = f"P{self.puzzle_index + 1}:{self.puzzle.name} [{self.solved_count}/{self.total_cells}]"
        pyxel.text(80, 14, progress_text, GRAY)

        # SUPER indicator
        if self.super_active:
            super_text = f"SUPER! {self.super_timer:.1f}s"
            sx = SCREEN_W // 2 - len(super_text) * 2
            pyxel.text(sx, 22, super_text, YELLOW)

        # Grid background
        pyxel.rect(GRID_X, GRID_Y, COLS * CELL, ROWS * CELL, NAVY)

        # Draw filled cells
        for row in range(ROWS):
            for col in range(COLS):
                if self.grid[row][col] != -1:
                    color = CELL_COLORS[self.grid[row][col]]
                    x = GRID_X + col * CELL + 1
                    y = GRID_Y + row * CELL + 1
                    # SUPER flash effect: alternate bright/dim
                    if self.super_active and self.flash_timer > 0:
                        if (self.frame // 3) % 2 == 0:
                            pyxel.rect(x, y, CELL - 2, CELL - 2, WHITE)
                        else:
                            pyxel.rect(x, y, CELL - 2, CELL - 2, color)
                    else:
                        pyxel.rect(x, y, CELL - 2, CELL - 2, color)

        # Grid lines
        for i in range(ROWS + 1):
            y = GRID_Y + i * CELL
            pyxel.line(GRID_X, y, GRID_X + COLS * CELL, y, WHITE)
        for i in range(COLS + 1):
            x = GRID_X + i * CELL
            pyxel.line(x, GRID_Y, x, GRID_Y + ROWS * CELL, WHITE)

        # Row hints (left side)
        for row in range(ROWS):
            hints = self.puzzle.row_hints[row]
            y = GRID_Y + row * CELL + 5
            x = 4
            for hint in hints:
                color = CELL_COLORS[hint.color_idx]
                pyxel.rect(x, y, 6, 6, color)
                pyxel.text(x + 7, y - 1, str(hint.count), WHITE)
                x += 20

        # Column hints (above grid)
        for col in range(COLS):
            hints = self.puzzle.col_hints[col]
            x = GRID_X + col * CELL + 4
            y = 28
            for hint in hints:
                color = CELL_COLORS[hint.color_idx]
                pyxel.rect(x, y, 6, 6, color)
                pyxel.text(x + 7, y - 1, str(hint.count), WHITE)
                y += 9

        # Color palette at bottom
        palette_y = 225
        for i in range(4):
            bx = 20 + i * 75
            color = CELL_COLORS[i]
            # Button background
            if i == self.selected_color:
                pyxel.rectb(bx - 1, palette_y - 1, 62, 17, WHITE)
                pyxel.rect(bx, palette_y, 60, 15, WHITE)
                pyxel.rect(bx + 2, palette_y + 2, 56, 11, color)
            else:
                pyxel.rect(bx, palette_y, 60, 15, color)
            # Color label
            name = CELL_COLOR_NAMES[i]
            pyxel.text(bx + 30 - len(name) * 2, palette_y + 16, name, WHITE)

        # Particles
        for p in self.particles:
            pyxel.rect(int(p.x), int(p.y), 2, 2, p.color)

        # Floating texts
        for ft in self.floating_texts:
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

        # Reset camera
        if self.shake_frames > 0:
            pyxel.camera(0, 0)

    def _draw_game_over(self) -> None:
        """Draw the game over screen."""
        title = "GAME OVER"
        tw = len(title) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 60, title, RED)

        score_text = f"FINAL SCORE: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_text) * 2, 90, score_text, WHITE)

        combo_text = f"MAX COMBO: {self.max_combo}"
        pyxel.text(SCREEN_W // 2 - len(combo_text) * 2, 105, combo_text, YELLOW)

        heat_text = f"HEAT: {self.heat:.0f}/100" if self.heat < 100 else "HEAT: MAXED OUT!"
        pyxel.text(SCREEN_W // 2 - len(heat_text) * 2, 120, heat_text, RED)

        restart_text = "Press R or SPACE to restart"
        pyxel.text(SCREEN_W // 2 - len(restart_text) * 2, 160, restart_text, WHITE)


def run_game() -> None:
    """Entry point for NONOGRAM SURGE."""
    game = Game()
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    run_game()
