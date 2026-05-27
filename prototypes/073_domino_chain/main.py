"""073_domino_chain — Color-match domino chain reaction simulator.

Core fun moment: 分岐したドミノの連鎖が両経路を走り、合流点で爆発的なSUPER BURSTが起きて画面全体が連鎖する瞬間
"""
from __future__ import annotations

import enum
import math
import random
from collections import deque
from dataclasses import dataclass


import pyxel

# ── Constants ──────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
CELL_SIZE = 20
GRID_COLS = 16
GRID_ROWS = 12
START_COL = 7
START_ROW = 0
ANIM_SPEED = 3  # frames between two topples
CONVERGE_BONUS = 1000
SPLIT_BONUS = 200

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

DOMINO_COLORS: tuple[int, int, int, int] = (RED, GREEN, DARK_BLUE, YELLOW)
COLOR_NAMES: dict[int, str] = {
    RED: "RED",
    GREEN: "GREEN",
    DARK_BLUE: "BLUE",
    YELLOW: "YELLOW",
}

NEIGHBOR_DIRS: list[tuple[int, int]] = [(0, -1), (0, 1), (-1, 0), (1, 0)]


# ── Enums ──────────────────────────────────────────────────────────────

class Phase(enum.IntEnum):
    TITLE = 0
    PLACING = 1
    ANIMATING = 2
    SCORING = 3
    GAME_OVER = 4


# ── Data Classes ───────────────────────────────────────────────────────

@dataclass
class Cell:
    color: int  # 0=empty, else pyxel color index
    toppled: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class Flash:
    col: int
    row: int
    life: int
    color: int = WHITE


# ── Game Class ─────────────────────────────────────────────────────────

class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Domino Chain", display_scale=2)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── Reset / Init ─────────────────────────────────────────────────

    def reset(self) -> None:
        """Full state reset for new game or replay."""
        self.phase: Phase = Phase.TITLE
        self._init_grid()
        self._init_anim_state()
        self.score: int = 0
        self.best_score: int = 0
        self.selected_color_idx: int = 0
        self.hover_col: int = 0
        self.hover_row: int = 0

    def _init_grid(self) -> None:
        """Create empty grid of cells."""
        self.grid: list[list[Cell]] = [
            [Cell(color=0) for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)
        ]

    def _init_anim_state(self) -> None:
        """Reset animation-related state."""
        self.chain_length: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.combo_steps: int = 0
        self.converge_count: int = 0
        self.split_count: int = 0
        self.last_topple_color: int = 0
        self.anim_queue: deque[tuple[int, int]] = deque()
        self.in_queue: set[tuple[int, int]] = set()
        self.converged_cells: set[tuple[int, int]] = set()
        self.split_cells: set[tuple[int, int]] = set()
        self.particles: list[Particle] = []
        self.flashes: list[Flash] = []
        self.anim_timer: int = 0  # countdown to next topple
        self.anim_window: list[tuple[int, int]] = []  # recently toppled (for flash)

    # ── Helpers ──────────────────────────────────────────────────────

    @property
    def selected_color(self) -> int:
        return DOMINO_COLORS[self.selected_color_idx]

    def _cell_center(self, col: int, row: int) -> tuple[float, float]:
        return (
            float(col * CELL_SIZE + CELL_SIZE // 2),
            float(row * CELL_SIZE + CELL_SIZE // 2),
        )

    def _cell_rect(self, col: int, row: int) -> tuple[int, int, int, int]:
        """Return (x, y, w, h) for a cell's draw region."""
        return (col * CELL_SIZE + 1, row * CELL_SIZE + 1, CELL_SIZE - 2, CELL_SIZE - 2)

    def _pixel_to_cell(self, px: int, py: int) -> tuple[int, int] | None:
        """Convert pixel coords to grid (col, row), clamped."""
        col = px // CELL_SIZE
        row = py // CELL_SIZE
        if 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS:
            return col, row
        return None

    # ── Pure Logic: Placement ────────────────────────────────────────

    def _can_place(self, col: int, row: int) -> bool:
        """Check if a domino can be placed at the given cell."""
        if not (0 <= col < GRID_COLS and 0 <= row < GRID_ROWS):
            return False
        cell = self.grid[row][col]
        return cell.color == 0 and not cell.toppled

    def _place_domino(self, col: int, row: int) -> bool:
        """Place a domino of the selected color. Returns success."""
        if not self._can_place(col, row):
            return False
        self.grid[row][col].color = self.selected_color
        return True

    def _count_placed_dominoes(self) -> int:
        """Count total placed (non-empty) dominoes."""
        return sum(
            1 for row in self.grid for cell in row if cell.color != 0
        )

    # ── Pure Logic: Chain Propagation ────────────────────────────────

    def _start_chain(self) -> None:
        """Initialize BFS chain reaction from the start cell."""
        if self.grid[START_ROW][START_COL].color == 0:
            return
        self._init_anim_state()
        self.anim_queue.append((START_COL, START_ROW))
        self.in_queue.add((START_COL, START_ROW))
        self.anim_timer = 0
        self.phase = Phase.ANIMATING

    def _get_non_toppled_neighbors(self, col: int, row: int) -> list[tuple[int, int]]:
        """Return list of adjacent non-toppled cells that have a domino placed."""
        result: list[tuple[int, int]] = []
        for dc, dr in NEIGHBOR_DIRS:
            nc, nr = col + dc, row + dr
            if 0 <= nc < GRID_COLS and 0 <= nr < GRID_ROWS:
                cell = self.grid[nr][nc]
                if not cell.toppled and cell.color != 0:
                    result.append((nc, nr))
        return result

    def _count_adjacent(self, col: int, row: int) -> int:
        """Count non-toppled adjacent dominoes (for split detection)."""
        return len(self._get_non_toppled_neighbors(col, row))

    def _propagate_tick(self) -> bool:
        """Process one cell topple. Returns True if still animating."""
        if not self.anim_queue:
            return False

        col, row = self.anim_queue.popleft()
        self.in_queue.discard((col, row))

        cell = self.grid[row][col]
        if cell.toppled:
            return bool(self.anim_queue)

        # Topple
        cell.toppled = True
        self.chain_length += 1
        self.anim_window.append((col, row))
        if len(self.anim_window) > 3:
            self.anim_window.pop(0)

        # Combo
        if cell.color == self.last_topple_color and self.last_topple_color != 0:
            self.combo += 1
            self.combo_steps += 1
        else:
            self.combo = 1
        self.last_topple_color = cell.color
        self.max_combo = max(self.max_combo, self.combo)

        # Spawn topple particles
        cx, cy = self._cell_center(col, row)
        self._spawn_particles(cx, cy, cell.color, self._rng.randint(4, 8))
        self.flashes.append(Flash(col=col, row=row, life=6, color=cell.color))

        # Check SPLIT: outgoing count ≥ 2
        neighbors = self._get_non_toppled_neighbors(col, row)
        if len(neighbors) >= 2:
            self.split_cells.add((col, row))
            self.split_count += 1
            self._spawn_particles(cx, cy, ORANGE, 6)

        # Add neighbors to queue, detect CONVERGE
        for nc, nr in neighbors:
            if (nc, nr) in self.in_queue:
                # CONVERGE: two propagation waves meet
                if (nc, nr) not in self.converged_cells:
                    self.converged_cells.add((nc, nr))
                    self.converge_count += 1
                    ncx, ncy = self._cell_center(nc, nr)
                    self._spawn_converge_particles(ncx, ncy)
                    self.flashes.append(Flash(col=nc, row=nr, life=12, color=PINK))
            else:
                self.anim_queue.append((nc, nr))
                self.in_queue.add((nc, nr))

        return bool(self.anim_queue)

    # ── Pure Logic: Scoring ──────────────────────────────────────────

    def _calculate_score(self) -> int:
        """Compute final score for this run."""
        converge_bonus = self.converge_count * CONVERGE_BONUS
        split_bonus = self.split_count * SPLIT_BONUS
        return (
            self.chain_length * 10
            + self.combo_steps * 50
            + converge_bonus
            + split_bonus
        )

    # ── Particles ────────────────────────────────────────────────────

    def _spawn_particles(
        self, x: float, y: float, color: int, count: int
    ) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.5)
            life = self._rng.randint(8, 15)
            self.particles.append(Particle(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=life,
                color=color,
            ))

    def _spawn_converge_particles(self, x: float, y: float) -> None:
        """Spawn large burst for CONVERGE event."""
        count = self._rng.randint(12, 20)
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.5, 4.0)
            life = self._rng.randint(15, 25)
            self.particles.append(Particle(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=life,
                color=self._rng.choice([PINK, YELLOW, WHITE]),
            ))

    def _update_particles(self) -> None:
        """Update particle positions; remove dead."""
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.2  # gravity
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_flashes(self) -> None:
        for f in self.flashes[:]:
            f.life -= 1
            if f.life <= 0:
                self.flashes.remove(f)

    # ── Update ───────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLACING:
            self._update_placing()
        elif self.phase == Phase.ANIMATING:
            self._update_animating()
        elif self.phase == Phase.SCORING:
            self._update_scoring()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._init_grid()
            self._init_anim_state()
            self.score = 0
            self.selected_color_idx = 0
            self.phase = Phase.PLACING

    def _update_placing(self) -> None:
        self._update_particles()
        self._update_flashes()

        # ESC -> game over
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            self.phase = Phase.GAME_OVER
            return

        # Hover
        cell = self._pixel_to_cell(pyxel.mouse_x, pyxel.mouse_y)
        if cell is not None:
            self.hover_col, self.hover_row = cell

        # Change color: 1/2/3/4 keys
        if pyxel.btnp(pyxel.KEY_1):
            self.selected_color_idx = 0
        elif pyxel.btnp(pyxel.KEY_2):
            self.selected_color_idx = 1
        elif pyxel.btnp(pyxel.KEY_3):
            self.selected_color_idx = 2
        elif pyxel.btnp(pyxel.KEY_4):
            self.selected_color_idx = 3

        # Mouse click to place
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if cell is not None:
                self._place_domino(*cell)

        # SPACE to trigger chain
        if pyxel.btnp(pyxel.KEY_SPACE):
            if self._count_placed_dominoes() > 0:
                self._start_chain()

    def _update_animating(self) -> None:
        self._update_particles()
        self._update_flashes()

        # ESC -> game over
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            self.phase = Phase.GAME_OVER
            return

        # Timer for animation speed
        self.anim_timer += 1
        if self.anim_timer >= ANIM_SPEED:
            self.anim_timer = 0
            still_going = self._propagate_tick()
            if not still_going:
                # Chain complete
                self.score = self._calculate_score()
                self.best_score = max(self.best_score, self.score)
                self.phase = Phase.SCORING

    def _update_scoring(self) -> None:
        self._update_particles()
        self._update_flashes()

        if pyxel.btnp(pyxel.KEY_SPACE):
            # Restart: new grid, back to placing
            self._init_grid()
            self._init_anim_state()
            self.score = 0
            self.selected_color_idx = 0
            self.phase = Phase.PLACING

        if pyxel.btnp(pyxel.KEY_ESCAPE):
            self.phase = Phase.GAME_OVER

    def _update_game_over(self) -> None:
        self._update_particles()
        self._update_flashes()

        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()

    # ── Draw ─────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLACING:
            self._draw_grid()
            self._draw_placing_overlay()
            self._draw_particles()
            self._draw_hud()
        elif self.phase == Phase.ANIMATING:
            self._draw_grid()
            self._draw_particles()
            self._draw_hud()
            self._draw_converge_labels()
        elif self.phase == Phase.SCORING:
            self._draw_grid()
            self._draw_particles()
            self._draw_scoring_overlay()
            self._draw_hud()
        elif self.phase == Phase.GAME_OVER:
            self._draw_grid()
            self._draw_particles()
            self._draw_game_over_overlay()

    # ── Draw: Title ──────────────────────────────────────────────────

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 50, 36, "DOMINO CHAIN", WHITE)
        pyxel.text(SCREEN_W // 2 - 68, 54, "Color-Match Chain Reaction", GRAY)

        lines: list[tuple[str, int]] = [
            ("Place colored dominoes on the grid.", WHITE),
            ("Same-color consecutive topples = COMBO!", LIME),
            ("Split paths + Converge = SUPER BURST!", YELLOW),
            ("", WHITE),
            ("CONTROLS:", CYAN),
            ("Mouse: Place domino  |  SPACE: Trigger", WHITE),
            ("1/2/3/4: Select color  |  ESC: Quit", WHITE),
            ("", WHITE),
            ("SPACE / ENTER to start", WHITE),
        ]
        y = 80
        for text, color in lines:
            if text:
                pyxel.text(SCREEN_W // 2 - len(text) * 4 // 2, y, text, color)
            y += 13

        # Color preview
        for i, c in enumerate(DOMINO_COLORS):
            cx = SCREEN_W // 2 - 42 + i * 22
            pyxel.rect(cx, 188, 16, 16, c)
            pyxel.rectb(cx, 188, 16, 16, WHITE)
            pyxel.text(cx + 3, 206, str(i + 1), GRAY)

    # ── Draw: Grid ───────────────────────────────────────────────────

    def _draw_grid(self) -> None:
        # Draw cell backgrounds
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                self._draw_cell(col, row)

    def _draw_cell(self, col: int, row: int) -> None:
        cell = self.grid[row][col]
        x, y, w, h = self._cell_rect(col, row)

        # Empty cell: dark background with subtle border
        if cell.color == 0:
            pyxel.rect(x - 1, y - 1, w + 2, h + 2, NAVY)
            return

        # Flash override (active topple/converge flash)
        for f in self.flashes:
            if f.col == col and f.row == row:
                if f.color == PINK:
                    pyxel.rect(x - 1, y - 1, w + 2, h + 2, PINK)
                    pyxel.rect(x, y, w, h, WHITE)
                else:
                    pyxel.rect(x - 1, y - 1, w + 2, h + 2, WHITE)
                    pyxel.rect(x, y, w, h, f.color)
                return

        # Converged cell glow
        if (col, row) in self.converged_cells:
            pyxel.rect(x - 2, y - 2, w + 4, h + 4, PINK)
            pyxel.rect(x, y, w, h, cell.color)
            return

        if cell.toppled:
            # Toppled: dim / flat version
            pyxel.rect(x, y, w, h, GRAY)
            pyxel.rectb(x, y, w, h, DARK_BLUE)
            # Show original color as a small inner dot
            inner = 4
            ix = x + (w - inner) // 2
            iy = y + (h - inner) // 2
            pyxel.rect(ix, iy, inner, inner, cell.color)
        else:
            # Placed, standing
            pyxel.rect(x, y, w, h, cell.color)
            pyxel.rectb(x, y, w, h, WHITE)
            # Small highlight
            pyxel.rect(x + 2, y + 2, w - 4, h // 3, WHITE)
            pyxel.rect(x + 2, y + 2, w - 4, 2, WHITE)

        # Split indicator
        if (col, row) in self.split_cells and not any(
            f.col == col and f.row == row for f in self.flashes
        ):
            pyxel.rectb(x - 2, y - 2, w + 4, h + 4, ORANGE)

    # ── Draw: Overlays ───────────────────────────────────────────────

    def _draw_placing_overlay(self) -> None:
        # Cursor: highlight hovered cell with selected color
        col, row = self.hover_col, self.hover_row
        cell = self.grid[row][col]
        x, y, w, h = self._cell_rect(col, row)
        if cell.color == 0:
            # Show transparent preview
            pyxel.rectb(x, y, w, h, self.selected_color)
            # Pulsing fill
            if (pyxel.frame_count // 15) % 2 == 0:
                pyxel.rect(x + 3, y + 3, w - 6, h - 6, self.selected_color)

        # Start cell indicator
        sx, sy = START_COL * CELL_SIZE + CELL_SIZE // 2, START_ROW * CELL_SIZE + CELL_SIZE // 2
        if (pyxel.frame_count // 20) % 2 == 0:
            pyxel.circb(sx, sy, 10, YELLOW)

    def _draw_scoring_overlay(self) -> None:
        # Semi-transparent overlay
        for yy in range(0, SCREEN_H, 4):
            for xx in range(0, SCREEN_W, 4):
                if (xx // 4 + yy // 4) % 2 == 0:
                    pyxel.pset(xx, yy, BLACK)

        px = SCREEN_W // 2 - 85
        py = SCREEN_H // 2 - 65
        pyxel.rect(px, py, 170, 130, NAVY)
        pyxel.rectb(px, py, 170, 130, WHITE)

        pyxel.text(SCREEN_W // 2 - 30, py + 8, "CHAIN COMPLETE!", LIME)
        pyxel.text(SCREEN_W // 2 - 50, py + 26, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 50, py + 40,
                   f"Chain Length: {self.chain_length}", GRAY)
        pyxel.text(SCREEN_W // 2 - 50, py + 54,
                   f"Max COMBO: {self.max_combo}", YELLOW)
        pyxel.text(SCREEN_W // 2 - 50, py + 66,
                   f"COMBO Steps: {self.combo_steps}", LIME)
        pyxel.text(SCREEN_W // 2 - 50, py + 78,
                   f"Converges: {self.converge_count} (x{CONVERGE_BONUS})", PINK)
        pyxel.text(SCREEN_W // 2 - 50, py + 90,
                   f"Splits: {self.split_count}", ORANGE)
        pyxel.text(SCREEN_W // 2 - 50, py + 106,
                   f"BEST: {self.best_score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 40, py + 118, "SPACE to Replay", CYAN)

    def _draw_game_over_overlay(self) -> None:
        for yy in range(0, SCREEN_H, 4):
            for xx in range(0, SCREEN_W, 4):
                if (xx // 4 + yy // 4) % 2 == 0:
                    pyxel.pset(xx, yy, BLACK)

        px = SCREEN_W // 2 - 85
        py = SCREEN_H // 2 - 50
        pyxel.rect(px, py, 170, 100, NAVY)
        pyxel.rectb(px, py, 170, 100, WHITE)

        pyxel.text(SCREEN_W // 2 - 28, py + 8, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 50, py + 26, f"FINAL SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 50, py + 42, f"BEST SCORE: {self.best_score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 50, py + 58,
                   f"Max COMBO: {self.max_combo}", YELLOW)
        pyxel.text(SCREEN_W // 2 - 40, py + 76, "SPACE for Title", CYAN)

    # ── Draw: HUD ────────────────────────────────────────────────────

    def _draw_hud(self) -> None:
        # During ANIMATING: show combo/counts
        if self.phase == Phase.ANIMATING:
            # Chain length top-left
            pyxel.text(2, 2, f"CHAIN:{self.chain_length}", WHITE)

            # Combo top-right
            combo_str = f"COMBO:{self.combo}"
            combo_color = YELLOW if self.combo >= 5 else WHITE
            pyxel.text(SCREEN_W - len(combo_str) * 4 - 2, 2, combo_str, combo_color)

            # Max combo
            pyxel.text(2, 12, f"MAX:{self.max_combo}", GRAY)

            # Converge count
            if self.converge_count > 0:
                conv_str = f"BURST!x{self.converge_count}"
                pyxel.text(
                    SCREEN_W - len(conv_str) * 4 - 2, 12, conv_str, PINK
                )

        # During PLACING: show score
        elif self.phase == Phase.PLACING:
            pyxel.text(2, 2, f"SCORE:{self.score:05d}", WHITE)
            pyxel.text(2, 12, f"BEST:{self.best_score:05d}", GRAY)
            count = self._count_placed_dominoes()
            pyxel.text(2, 22, f"DOMINOES:{count}", WHITE)

        # Color bar at bottom
        self._draw_color_bar()

    def _draw_color_bar(self) -> None:
        """Draw current color selection bar at bottom of screen."""
        bar_y = SCREEN_H - 18
        # Background
        pyxel.rect(0, bar_y, SCREEN_W, 18, NAVY)
        pyxel.line(0, bar_y, SCREEN_W, bar_y, DARK_BLUE)

        # Color swatches
        sw_x = SCREEN_W // 2 - 42
        for i, c in enumerate(DOMINO_COLORS):
            cx = sw_x + i * 22
            if i == self.selected_color_idx:
                pyxel.rect(cx - 1, bar_y + 1, 18, 16, WHITE)
            pyxel.rect(cx, bar_y + 2, 16, 14, c)
            pyxel.text(cx + 5, bar_y + 3, str(i + 1), BLACK if c == YELLOW else WHITE)

        if self.phase == Phase.PLACING:
            pyxel.text(SCREEN_W // 2 - 50, bar_y + 3,
                       "SPACE to trigger!", CYAN)

    def _draw_converge_labels(self) -> None:
        """Draw converge flash text during animation."""
        for ccol, crow in self.converged_cells:
            for f in self.flashes:
                if f.col == ccol and f.row == crow and f.life > 3:
                    cx, cy = self._cell_center(ccol, crow)
                    text = "SUPER BURST!"
                    pyxel.text(
                        int(cx) - len(text) * 4 // 2,
                        int(cy) - 18,
                        text,
                        PINK,
                    )

    # ── Draw: Particles ──────────────────────────────────────────────

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 25.0
            if alpha > 0.15:
                pyxel.pset(int(p.x), int(p.y), p.color)


# ── Entry Point ────────────────────────────────────────────────────────

def main() -> None:
    Game()


if __name__ == "__main__":
    main()
