"""MINESWEEP CHAIN — Minesweeper-like deduction puzzle with COMBO chains.

Core fun moment: deducing and revealing same-color ore consecutively;
when COMBO hits 3, SYNTHESIS auto-reveals all adjacent same-color ore
in a cascading BFS chain reaction. Risk/reward: chase same-color combos
for explosive SYNTHESIS bursts vs. play safe with mixed colors.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto

import pyxel

# ── Constants ──────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
DISPLAY_SCALE = 2
FPS = 30
GAME_TIME_SEC = 90.0

# Grid
COLS = 10
ROWS = 8
CELL_W = 24
CELL_H = 24
GRID_X = 20
GRID_Y = 40

TOTAL_ORES = 12
ORES_PER_COLOR = 3
NUM_MINES = 8
NUM_COLORS = 4

# Cell states
HIDDEN = 0
REVEALED_ORE = 1
REVEALED_EMPTY = 2
FLAGGED = 3
MINE = 4

# Ore colors (Pyxel palette ints)
ORE_COLORS: tuple[int, int, int, int] = (
    pyxel.COLOR_RED,        # 8
    pyxel.COLOR_LIGHT_BLUE, # 6
    pyxel.COLOR_GREEN,      # 3
    pyxel.COLOR_YELLOW,     # 10
)
ORE_NAMES: tuple[str, str, str, str] = ("RED", "BLUE", "GREEN", "YELLOW")

# Color constants for drawing
BLACK = pyxel.COLOR_BLACK
NAVY = pyxel.COLOR_NAVY
PURPLE = pyxel.COLOR_PURPLE
GREEN = pyxel.COLOR_GREEN
BROWN = pyxel.COLOR_BROWN
DARK_BLUE = pyxel.COLOR_DARK_BLUE
LIGHT_BLUE = pyxel.COLOR_LIGHT_BLUE
WHITE = pyxel.COLOR_WHITE
RED = pyxel.COLOR_RED
ORANGE = pyxel.COLOR_ORANGE
YELLOW = pyxel.COLOR_YELLOW
LIME = pyxel.COLOR_LIME
CYAN = pyxel.COLOR_CYAN
GRAY = pyxel.COLOR_GRAY
PINK = pyxel.COLOR_PINK
PEACH = pyxel.COLOR_PEACH

# Scoring
BASE_ORE_SCORE = 10
SYNTHESIS_THRESHOLD = 3

# Directions for BFS (4-directional) and neighbor count (8-directional)
DIRS_4: tuple[tuple[int, int], ...] = ((0, -1), (0, 1), (-1, 0), (1, 0))
DIRS_8: tuple[tuple[int, int], ...] = (
    (-1, -1), (0, -1), (1, -1),
    (-1, 0),           (1, 0),
    (-1, 1),  (0, 1),  (1, 1),
)


# ── Data Classes ───────────────────────────────────────────────────────

@dataclass
class Cell:
    col: int
    row: int
    state: int = HIDDEN
    ore_color: int = 0
    is_mine: bool = False
    is_ore: bool = False

    @property
    def revealed(self) -> bool:
        return self.state in (REVEALED_ORE, REVEALED_EMPTY, MINE)


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


@dataclass
class SynthesisAnim:
    cells: list[tuple[int, int]] = field(default_factory=list)
    frame: int = 0
    total_frames: int = 15


# ── Phase Enum ─────────────────────────────────────────────────────────

class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    SYNTHESIS = auto()
    GAME_OVER = auto()


# ── Game Class ─────────────────────────────────────────────────────────

class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="MINESWEEP CHAIN", display_scale=DISPLAY_SCALE, fps=FPS)
        pyxel.mouse(False)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.time_left: float = GAME_TIME_SEC
        self.ores_revealed: int = 0
        self.frame: int = 0
        self._current_color: int | None = None
        self._synthesis_queue: set[tuple[int, int]] = set()
        self._synthesis_anim: SynthesisAnim | None = None
        self._shake_frames: int = 0
        self._flash_frames: int = 0
        self._win: bool = False

        self.grid: list[list[Cell]] = []
        for c in range(COLS):
            row_cells: list[Cell] = []
            for r in range(ROWS):
                row_cells.append(Cell(col=c, row=r))
            self.grid.append(row_cells)

        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []

        self._init_grid()

    # ── Pure Logic (Testable) ──────────────────────────────────────

    def _init_grid(self, seed: int | None = None) -> None:
        """Set up mines and ores with deterministic placement via seed."""
        rng = random.Random(seed) if seed is not None else self._rng

        total_cells = COLS * ROWS
        indices = list(range(total_cells))
        rng.shuffle(indices)

        # Reset all cells
        for c in range(COLS):
            for r in range(ROWS):
                cell = self.grid[c][r]
                cell.state = HIDDEN
                cell.ore_color = 0
                cell.is_mine = False
                cell.is_ore = False

        # Place mines
        for idx in indices[:NUM_MINES]:
            c, r = divmod(idx, ROWS)
            self.grid[c][r].is_mine = True

        # Place ores (3 of each color)
        ore_idx = NUM_MINES
        for color in range(NUM_COLORS):
            for _ in range(ORES_PER_COLOR):
                idx = indices[ore_idx]
                ore_idx += 1
                c, r = divmod(idx, ROWS)
                cell = self.grid[c][r]
                cell.is_ore = True
                cell.ore_color = color

        # Reset game state (but keep grid)
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.time_left = GAME_TIME_SEC
        self.ores_revealed = 0
        self.frame = 0
        self._current_color = None
        self._synthesis_queue.clear()
        self._synthesis_anim = None
        self._shake_frames = 0
        self._flash_frames = 0
        self._win = False
        self.particles.clear()
        self.floating_texts.clear()

    def _count_adjacent_ores(self, col: int, row: int) -> dict[int, int]:
        """Return dict of color→count for the 8 neighbors of a cell."""
        result: dict[int, int] = {}
        for dc, dr in DIRS_8:
            nc, nr = col + dc, row + dr
            if 0 <= nc < COLS and 0 <= nr < ROWS:
                cell = self.grid[nc][nr]
                if cell.is_ore:
                    result[cell.ore_color] = result.get(cell.ore_color, 0) + 1
        return result

    def _reveal_cell(self, col: int, row: int) -> tuple[int, int | None]:
        """Reveal a cell. Returns (result_state, ore_color_or_None)."""
        cell = self.grid[col][row]
        if cell.state != HIDDEN:
            return (cell.state, cell.ore_color if cell.state == REVEALED_ORE else None)

        if cell.is_mine:
            cell.state = MINE
            return (MINE, None)

        if cell.is_ore:
            cell.state = REVEALED_ORE
            return (REVEALED_ORE, cell.ore_color)

        cell.state = REVEALED_EMPTY
        return (REVEALED_EMPTY, None)

    def _toggle_flag(self, col: int, row: int) -> None:
        """Toggle flag on a hidden cell."""
        cell = self.grid[col][row]
        if cell.state == HIDDEN:
            cell.state = FLAGGED
        elif cell.state == FLAGGED:
            cell.state = HIDDEN

    def _bfs_synthesis(self, start_col: int, start_row: int, color: int) -> set[tuple[int, int]]:
        """BFS flood-fill: return all adjacent (4-dir) same-color ore cells not yet revealed."""
        result: set[tuple[int, int]] = set()
        visited: set[tuple[int, int]] = set()
        queue: list[tuple[int, int]] = [(start_col, start_row)]
        visited.add((start_col, start_row))

        while queue:
            c, r = queue.pop(0)
            for dc, dr in DIRS_4:
                nc, nr = c + dc, r + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS and (nc, nr) not in visited:
                    visited.add((nc, nr))
                    cell = self.grid[nc][nr]
                    if cell.is_ore and cell.ore_color == color and cell.state == HIDDEN:
                        result.add((nc, nr))
                        queue.append((nc, nr))
                    elif cell.is_ore and cell.ore_color == color and cell.state != REVEALED_ORE:
                        result.add((nc, nr))
                        queue.append((nc, nr))
        return result

    def _check_win(self) -> bool:
        """Return True if all ores have been revealed."""
        return self.ores_revealed >= TOTAL_ORES

    def _apply_synthesis(self, cells: set[tuple[int, int]]) -> int:
        """Reveal the given cells. Returns how many were newly revealed."""
        revealed = 0
        for c, r in cells:
            cell = self.grid[c][r]
            if cell.state != REVEALED_ORE:
                cell.state = REVEALED_ORE
                revealed += 1
        return revealed

    # ── Update Helpers ─────────────────────────────────────────────

    def _start_game(self) -> None:
        """Transition from TITLE to PLAYING."""
        self._init_grid()
        self.phase = Phase.PLAYING

    def _handle_click(self, mx: int, my: int) -> None:
        """Translate mouse coords to grid cell and reveal."""
        col = (mx - GRID_X) // CELL_W
        row = (my - GRID_Y) // CELL_H
        if not (0 <= col < COLS and 0 <= row < ROWS):
            return
        cell = self.grid[col][row]
        if cell.state != HIDDEN:
            return

        result, ore_color = self._reveal_cell(col, row)

        if result == MINE:
            self._spawn_particles(col, row, RED, 20)
            self._shake_frames = 15
            self.phase = Phase.GAME_OVER
            return

        if result == REVEALED_ORE:
            assert ore_color is not None
            self.ores_revealed += 1

            # Combo logic
            if self._current_color == ore_color:
                self.combo += 1
            else:
                self.combo = 1
                self._current_color = ore_color

            if self.combo > self.max_combo:
                self.max_combo = self.combo

            # Score
            points = BASE_ORE_SCORE * self.combo
            self.score += points
            self._spawn_floating_text(col, row, f"+{points}", ore_color)

            # Synthesis trigger
            if self.combo >= SYNTHESIS_THRESHOLD:
                synthesis_cells = self._bfs_synthesis(col, row, ore_color)
                if synthesis_cells:
                    self._synthesis_queue = synthesis_cells
                    self.phase = Phase.SYNTHESIS
                    self._synthesis_anim = SynthesisAnim(
                        cells=list(synthesis_cells),
                        frame=0,
                        total_frames=15,
                    )

            # Check win
            if self._check_win():
                self._win = True
                self.phase = Phase.GAME_OVER

        elif result == REVEALED_EMPTY:
            self.combo = 0
            self._current_color = None

    def _handle_right_click(self, mx: int, my: int) -> None:
        """Translate mouse coords and toggle flag."""
        col = (mx - GRID_X) // CELL_W
        row = (my - GRID_Y) // CELL_H
        if not (0 <= col < COLS and 0 <= row < ROWS):
            return
        self._toggle_flag(col, row)

    def _spawn_particles(self, col: int, row: int, color: int, count: int) -> None:
        """Spawn burst particles at a grid cell position."""
        cx = GRID_X + col * CELL_W + CELL_W // 2
        cy = GRID_Y + row * CELL_H + CELL_H // 2
        for _ in range(count):
            self.particles.append(Particle(
                x=float(cx),
                y=float(cy),
                vx=(self._rng.random() * 2 - 1) * 3.0,
                vy=(self._rng.random() * 2 - 1) * 3.0,
                life=20 + self._rng.randint(0, 10),
                color=color,
            ))

    def _spawn_floating_text(self, col: int, row: int, text: str, color: int) -> None:
        """Spawn a floating score text above a cell."""
        cx = GRID_X + col * CELL_W + CELL_W // 2
        cy = GRID_Y + row * CELL_H
        self.floating_texts.append(FloatingText(
            x=float(cx - len(text) * 2),
            y=float(cy),
            text=text,
            life=30,
            color=color,
        ))

    # ── Update ─────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self._start_game()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
            return

        if self.phase == Phase.SYNTHESIS:
            self._update_synthesis()
            return

        # PLAYING phase
        self.frame += 1

        # Timer
        self.time_left -= 1.0 / FPS
        if self.time_left <= 0:
            self.time_left = 0
            self.phase = Phase.GAME_OVER
            return

        # Shake decay
        if self._shake_frames > 0:
            self._shake_frames -= 1

        # Flash decay
        if self._flash_frames > 0:
            self._flash_frames -= 1

        # Update particles
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.15
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

        # Update floating texts
        for ft in self.floating_texts[:]:
            ft.y -= 0.8
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

        # Input
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._handle_click(pyxel.mouse_x, pyxel.mouse_y)
        if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            self._handle_right_click(pyxel.mouse_x, pyxel.mouse_y)

    def _update_synthesis(self) -> None:
        """Animate the BFS chain reveal during SYNTHESIS phase."""
        anim = self._synthesis_anim
        if anim is None:
            self.phase = Phase.PLAYING
            self.combo = 0
            self._current_color = None
            return

        anim.frame += 1

        # Reveal cells gradually (staggered)
        cells_per_frame = max(1, len(anim.cells) // anim.total_frames + 1)
        start_idx = anim.frame * cells_per_frame
        end_idx = min(start_idx + cells_per_frame, len(anim.cells))

        for i in range(start_idx, end_idx):
            if i < len(anim.cells):
                c, r = anim.cells[i]
                cell = self.grid[c][r]
                if cell.state != REVEALED_ORE:
                    cell.state = REVEALED_ORE
                    self.ores_revealed += 1
                    # Score during synthesis: bonus multiplier
                    points = BASE_ORE_SCORE * self.max_combo * 2
                    self.score += points
                    self._spawn_floating_text(c, r, f"+{points}", cell.ore_color)
                    self._spawn_particles(c, r, ORE_COLORS[cell.ore_color], 5)

        # Check if animation done
        if anim.frame >= anim.total_frames or end_idx >= len(anim.cells):
            self._synthesis_anim = None
            self.combo = 0
            self._current_color = None
            self._flash_frames = 10
            if self._check_win():
                self._win = True
                self.phase = Phase.GAME_OVER
            else:
                self.phase = Phase.PLAYING

    # ── Draw ────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
            return

        # Shake offset
        shake_x = 0
        shake_y = 0
        if self._shake_frames > 0:
            shake_x = self._rng.randint(-2, 2)
            shake_y = self._rng.randint(-2, 2)

        # Draw grid
        self._draw_grid(shake_x, shake_y)

        # Draw HUD
        self._draw_hud()

        # Draw particles
        for p in self.particles:
            pyxel.pset(int(p.x + shake_x), int(p.y + shake_y), p.color)

        # Draw floating texts
        for ft in self.floating_texts:
            pyxel.text(int(ft.x + shake_x), int(ft.y + shake_y), ft.text, ft.color)

        # Synthesis flash
        if self._flash_frames > 0:
            pyxel.cls(YELLOW)
            self._draw_grid(shake_x, shake_y)
            self._draw_hud()
            self._flash_frames -= 1

    def _draw_title(self) -> None:
        """Draw title screen."""
        title = "MINE SWEEP"
        title2 = "CHAIN"
        pyxel.text(SCREEN_W // 2 - len(title) * 4 // 2, 60, title, WHITE)
        pyxel.text(SCREEN_W // 2 - len(title2) * 4 // 2, 76, title2, YELLOW)

        instructions = [
            "LEFT CLICK: Reveal cell",
            "RIGHT CLICK: Flag mine",
            "",
            "Reveal same-color ore x3",
            "to trigger SYNTHESIS!",
            "Chain-reveal adjacent ore",
            "for massive score.",
            "",
            "Reveal all 12 ores",
            "before time runs out!",
        ]
        for i, line in enumerate(instructions):
            pyxel.text(SCREEN_W // 2 - len(line) * 4 // 2, 110 + i * 10, line, GRAY)

        pyxel.text(
            SCREEN_W // 2 - len("PRESS SPACE TO START") * 4 // 2,
            220,
            "PRESS SPACE TO START",
            WHITE,
        )

    def _draw_game_over(self) -> None:
        """Draw game over screen."""
        if self._win:
            pyxel.text(SCREEN_W // 2 - 4 * 4, 60, "CLEAR!", YELLOW)
        else:
            pyxel.text(SCREEN_W // 2 - len("GAME OVER") * 4 // 2, 60, "GAME OVER", RED)

        pyxel.text(SCREEN_W // 2 - len(f"SCORE: {self.score}") * 4 // 2, 90, f"SCORE: {self.score}", WHITE)
        pyxel.text(
            SCREEN_W // 2 - len(f"MAX COMBO: {self.max_combo}") * 4 // 2,
            106,
            f"MAX COMBO: {self.max_combo}",
            ORANGE,
        )
        pyxel.text(
            SCREEN_W // 2 - len(f"ORES FOUND: {self.ores_revealed}/{TOTAL_ORES}") * 4 // 2,
            122,
            f"ORES FOUND: {self.ores_revealed}/{TOTAL_ORES}",
            LIME,
        )

        pyxel.text(
            SCREEN_W // 2 - len("SPACE TO RETRY") * 4 // 2,
            200,
            "SPACE TO RETRY",
            WHITE,
        )

    def _draw_grid(self, shake_x: int, shake_y: int) -> None:
        """Draw the grid with all cells."""
        for c in range(COLS):
            for r in range(ROWS):
                cell = self.grid[c][r]
                x = GRID_X + c * CELL_W + shake_x
                y = GRID_Y + r * CELL_H + shake_y

                if cell.state == HIDDEN:
                    pyxel.rect(x, y, CELL_W, CELL_H, GRAY)
                    pyxel.rectb(x, y, CELL_W, CELL_H, DARK_BLUE)
                elif cell.state == FLAGGED:
                    pyxel.rect(x, y, CELL_W, CELL_H, GRAY)
                    pyxel.rectb(x, y, CELL_W, CELL_H, RED)
                    # Draw flag marker (X shape)
                    pyxel.line(x + 5, y + 5, x + CELL_W - 5, y + CELL_H - 5, RED)
                    pyxel.line(x + CELL_W - 5, y + 5, x + 5, y + CELL_H - 5, RED)
                elif cell.state == REVEALED_ORE:
                    clr = ORE_COLORS[cell.ore_color]
                    pyxel.rect(x, y, CELL_W, CELL_H, clr)
                    pyxel.rectb(x, y, CELL_W, CELL_H, WHITE)
                    # Bright center
                    pyxel.rect(x + 6, y + 6, CELL_W - 12, CELL_H - 12, WHITE)
                elif cell.state == REVEALED_EMPTY:
                    pyxel.rect(x, y, CELL_W, CELL_H, DARK_BLUE)
                    pyxel.rectb(x, y, CELL_W, CELL_H, NAVY)
                    # Draw colored number indicators
                    counts = self._count_adjacent_ores(c, r)
                    for ci, (clr_idx, cnt) in enumerate(sorted(counts.items())):
                        if cnt > 0:
                            clr = ORE_COLORS[clr_idx]
                            pyxel.text(
                                x + 3 + (ci % 2) * 10,
                                y + 3 + (ci // 2) * 8,
                                str(cnt),
                                clr,
                            )
                elif cell.state == MINE:
                    pyxel.rect(x, y, CELL_W, CELL_H, RED)
                    pyxel.rectb(x, y, CELL_W, CELL_H, WHITE)
                    # Draw mine (circle)
                    pyxel.circ(x + CELL_W // 2, y + CELL_H // 2, 6, BLACK)
                    pyxel.circ(x + CELL_W // 2, y + CELL_H // 2, 4, YELLOW)

    def _draw_hud(self) -> None:
        """Draw HUD at the top: score, combo, timer, ore count."""
        # Background bar
        pyxel.rect(0, 0, SCREEN_W, GRID_Y - 4, NAVY)

        # Score
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)

        # Combo
        combo_color = WHITE
        if self.combo >= 3:
            combo_color = ORANGE
        if self.combo >= 5:
            combo_color = RED
        pyxel.text(120, 4, f"COMBO: {self.combo}", combo_color)

        # Max combo
        pyxel.text(200, 4, f"MAX: {self.max_combo}", YELLOW)

        # Timer
        timer_color = WHITE
        if self.time_left <= 15:
            timer_color = RED
        elif self.time_left <= 30:
            timer_color = ORANGE
        pyxel.text(4, 16, f"TIME: {int(self.time_left)}s", timer_color)

        # Ore count
        pyxel.text(120, 16, f"ORE: {self.ores_revealed}/{TOTAL_ORES}", LIME)

        # Current combo color indicator
        if self._current_color is not None:
            pyxel.rect(260, 4, 8, 8, ORE_COLORS[self._current_color])
            pyxel.text(270, 4, ORE_NAMES[self._current_color][:1], WHITE)

        # Grid bottom border
        grid_bottom = GRID_Y + ROWS * CELL_H
        pyxel.rect(GRID_X - 2, grid_bottom, COLS * CELL_W + 4, 2, WHITE)


# ── Entry Point ────────────────────────────────────────────────────────

def main() -> None:
    Game()


if __name__ == "__main__":
    main()
