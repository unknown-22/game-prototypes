"""GEM CHAIN — Color-match swap puzzle with chain-reaction spread.

Reinterpreted from alchemy synthesis deckbuilder idea #1 (score 32.75).
Hooks: "synthesis compression" → chain cascade, "CA spread" → BFS color propagation.
Genre: Match-3 swap puzzle (novel for this collection).

Controls:
  - Click gem to select (yellow highlight)
  - Click adjacent gem to swap
  - R: restart (game over screen)

The fun moment: setting off a cascading chain that sweeps the board,
watching the combo counter climb and score explode.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import pyxel

# ── Config ──────────────────────────────────────────────────────────────────
SCREEN_W = 256
SCREEN_H = 280
GRID_COLS = 8
GRID_ROWS = 8
CELL_SIZE = 28
GRID_X = 16
GRID_Y = 44
NUM_COLORS = 5
GAME_SECONDS = 60
FPS = 30
MATCH_MIN = 3
HEAT_MAX = 100
HEAT_PER_WAVE = 15
HEAT_QUAKE_THRESHOLD = 80
HEAT_DECAY = 0.3  # per frame
COMBO_DECAY_FRAMES = 45  # combo resets after this many frames with no new match

# Gem colors from Pyxel palette (http-friendly)
GEM_COLORS: list[int] = [
    pyxel.COLOR_RED,     # 0 = fire
    pyxel.COLOR_CYAN,    # 1 = ice
    pyxel.COLOR_LIME,    # 2 = nature
    pyxel.COLOR_YELLOW,  # 3 = light
    pyxel.COLOR_PURPLE,  # 4 = void
]

GEM_COLORS_DARK: list[int] = [
    pyxel.COLOR_BROWN,     # dark fire
    pyxel.COLOR_DARK_BLUE, # dark ice
    pyxel.COLOR_GREEN,     # dark nature
    pyxel.COLOR_ORANGE,    # dark light
    pyxel.COLOR_PINK,      # dark void
]

GEM_NAMES: list[str] = ["FIRE", "ICE", "NATR", "LITE", "VOID"]


# ── Data classes ────────────────────────────────────────────────────────────

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


@dataclass
class FloatText:
    x: float
    y: float
    text: str
    life: int
    color: int


class Phase(Enum):
    IDLE = auto()
    SWAP_ANIM = auto()
    CLEAR = auto()
    FALL = auto()
    GAME_OVER = auto()


# ── Board: pure logic (testable without Pyxel) ────────────────────────────

class Board:
    """Pure-logic match-3 board: grid state, matching, clearing, gravity."""

    def __init__(
        self,
        cols: int = GRID_COLS,
        rows: int = GRID_ROWS,
        colors: int = NUM_COLORS,
        rng: Optional[random.Random] = None,
    ):
        self.cols = cols
        self.rows = rows
        self.colors = colors
        self.rng = rng if rng is not None else random.Random()
        self.grid: list[list[int]] = []
        self._init_grid()

    def _randint(self, lo: int, hi: int) -> int:
        return self.rng.randint(lo, hi)

    def _init_grid(self) -> None:
        """Fill grid with random gems, avoiding initial matches."""
        self.grid = [[-1] * self.cols for _ in range(self.rows)]
        for r in range(self.rows):
            for c in range(self.cols):
                forbidden: set[int] = set()
                if c >= 2 and self.grid[r][c - 1] == self.grid[r][c - 2] != -1:
                    forbidden.add(self.grid[r][c - 1])
                if r >= 2 and self.grid[r - 1][c] == self.grid[r - 2][c] != -1:
                    forbidden.add(self.grid[r - 1][c])
                available = [clr for clr in range(self.colors) if clr not in forbidden]
                self.grid[r][c] = self._randint(0, self.colors - 1) if not available else self.rng.choice(available)

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.rows and 0 <= c < self.cols

    def is_adjacent(self, r1: int, c1: int, r2: int, c2: int) -> bool:
        return abs(r1 - r2) + abs(c1 - c2) == 1

    def swap(self, r1: int, c1: int, r2: int, c2: int) -> None:
        self.grid[r1][c1], self.grid[r2][c2] = self.grid[r2][c2], self.grid[r1][c1]

    def find_all_matches(self) -> set[tuple[int, int]]:
        """Find cells in 3+ horizontal or vertical runs."""
        matched: set[tuple[int, int]] = set()
        # horizontal
        for r in range(self.rows):
            c = 0
            while c < self.cols:
                clr = self.grid[r][c]
                if clr < 0:
                    c += 1
                    continue
                start = c
                while c < self.cols and self.grid[r][c] == clr:
                    c += 1
                if c - start >= MATCH_MIN:
                    for cc in range(start, c):
                        matched.add((r, cc))
        # vertical
        for c in range(self.cols):
            r = 0
            while r < self.rows:
                clr = self.grid[r][c]
                if clr < 0:
                    r += 1
                    continue
                start = r
                while r < self.rows and self.grid[r][c] == clr:
                    r += 1
                if r - start >= MATCH_MIN:
                    for rr in range(start, r):
                        matched.add((rr, c))
        return matched

    def spread(self, cells: set[tuple[int, int]]) -> set[tuple[int, int]]:
        """BFS: adjacent same-color cells also get consumed (CA spread hook)."""
        result = set(cells)
        queue = list(cells)
        while queue:
            r, c = queue.pop(0)
            clr = self.grid[r][c]
            if clr < 0:
                continue
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if self.in_bounds(nr, nc) and (nr, nc) not in result:
                    if self.grid[nr][nc] == clr:
                        result.add((nr, nc))
                        queue.append((nr, nc))
        return result

    def clear_cells(self, cells: set[tuple[int, int]]) -> int:
        """Set cells to -1 (empty). Returns count cleared."""
        for r, c in cells:
            self.grid[r][c] = -1
        return len(cells)

    def apply_gravity(self) -> int:
        """Drop gems down. Returns number of gems that moved."""
        moved = 0
        for c in range(self.cols):
            write = self.rows - 1
            for r in range(self.rows - 1, -1, -1):
                if self.grid[r][c] >= 0:
                    if r != write:
                        self.grid[write][c] = self.grid[r][c]
                        self.grid[r][c] = -1
                        moved += 1
                    write -= 1
        return moved

    def fill_empty(self) -> list[tuple[int, int, int]]:
        """Fill -1 cells with random gems. Returns [(r, c, color), ...]."""
        filled: list[tuple[int, int, int]] = []
        for c in range(self.cols):
            for r in range(self.rows):
                if self.grid[r][c] < 0:
                    clr = self._randint(0, self.colors - 1)
                    self.grid[r][c] = clr
                    filled.append((r, c, clr))
        return filled

    def has_valid_moves(self) -> bool:
        """Check if any swap produces a match."""
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] < 0:
                    continue
                for dr, dc in ((0, 1), (1, 0)):
                    nr, nc = r + dr, c + dc
                    if not self.in_bounds(nr, nc) or self.grid[nr][nc] < 0:
                        continue
                    self.swap(r, c, nr, nc)
                    has = bool(self.find_all_matches())
                    self.swap(r, c, nr, nc)
                    if has:
                        return True
        return False

    def shuffle(self) -> None:
        """Randomly shuffle the grid (for no-moves-left situations)."""
        cells: list[int] = []
        for r in range(self.rows):
            for c in range(self.cols):
                cells.append(self.grid[r][c])
        self.rng.shuffle(cells)
        idx = 0
        for r in range(self.rows):
            for c in range(self.cols):
                self.grid[r][c] = cells[idx]
                idx += 1


# ── Game ────────────────────────────────────────────────────────────────────

class Game:
    """Pyxel match-3 swap puzzle game."""

    def __init__(self) -> None:
        self.reset()
        pyxel.init(SCREEN_W, SCREEN_H, title="GEM CHAIN", fps=FPS)
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.board = Board()
        self.selected: Optional[tuple[int, int]] = None
        self.score = 0
        self.combo = 0
        self.combo_timer = 0
        self.heat = 0.0
        self.timer = GAME_SECONDS * FPS
        self.phase = Phase.IDLE
        self.best_score = 0
        self.game_over = False
        self.particles: list[Particle] = []
        self.floats: list[FloatText] = []
        # swap animation state
        self._swap_a: Optional[tuple[int, int]] = None
        self._swap_b: Optional[tuple[int, int]] = None
        self._swap_frame = 0
        self._swap_total = 6
        # clear animation
        self._clear_cells: set[tuple[int, int]] = set()
        self._clear_frame = 0
        self._clear_total = 8
        # cascade loop state
        self._cascade_wave = 0
        # quake
        self._quake_frames = 0
        self._invalid_flash = 0

    # ── Helpers ─────────────────────────────────────────────────────────

    def _cell_to_px(self, r: int, c: int) -> tuple[int, int]:
        return GRID_X + c * CELL_SIZE, GRID_Y + r * CELL_SIZE

    def _px_to_cell(self, px: int, py: int) -> Optional[tuple[int, int]]:
        c = (px - GRID_X) // CELL_SIZE
        r = (py - GRID_Y) // CELL_SIZE
        if 0 <= c < GRID_COLS and 0 <= r < GRID_ROWS:
            return r, c
        return None

    def _spawn_particles(self, r: int, c: int, color: int, count: int = 8) -> None:
        cx, cy = self._cell_to_px(r, c)
        cx += CELL_SIZE // 2
        cy += CELL_SIZE // 2
        for _ in range(count):
            angle = random.random() * math.pi * 2
            speed = 1.0 + random.random() * 2.0
            self.particles.append(Particle(
                x=float(cx), y=float(cy),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=15 + random.randint(0, 10),
                color=color,
                size=1 + random.randint(0, 2),
            ))

    def _add_float(self, r: int, c: int, text: str, color: int) -> None:
        cx, cy = self._cell_to_px(r, c)
        self.floats.append(FloatText(
            x=float(cx + CELL_SIZE // 2),
            y=float(cy),
            text=text,
            life=30,
            color=color,
        ))

    def _add_score_float(self, x: float, y: float, text: str, color: int) -> None:
        self.floats.append(FloatText(x=x, y=y, text=text, life=30, color=color))

    # ── Update ──────────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
                self.phase = Phase.IDLE
            return

        # Timer
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self.phase = Phase.GAME_OVER
            self.game_over = True
            if self.score > self.best_score:
                self.best_score = self.score
            return

        # Heat decay
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

        # Quake
        if self._quake_frames > 0:
            self._quake_frames -= 1

        # Combo decay
        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer == 0:
                self.combo = 0

        # Update particles
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

        # Update floating texts
        for ft in self.floats:
            ft.y += -1.0
            ft.life -= 1
        self.floats = [ft for ft in self.floats if ft.life > 0]

        # Invalid flash
        if self._invalid_flash > 0:
            self._invalid_flash -= 1

        # Phase-specific updates
        if self.phase == Phase.IDLE:
            self._update_idle()
        elif self.phase == Phase.SWAP_ANIM:
            self._update_swap_anim()
        elif self.phase == Phase.CLEAR:
            self._update_clear()
        elif self.phase == Phase.FALL:
            self._update_fall()

    def _update_idle(self) -> None:
        if not pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            return
        cell = self._px_to_cell(pyxel.mouse_x, pyxel.mouse_y)
        if cell is None:
            self.selected = None
            return
        r, c = cell
        if self.selected is None:
            # Select
            if self.board.grid[r][c] >= 0:
                self.selected = (r, c)
        elif self.selected == (r, c):
            # Deselect
            self.selected = None
        elif self.board.is_adjacent(self.selected[0], self.selected[1], r, c):
            # Attempt swap
            self._try_swap(self.selected[0], self.selected[1], r, c)
            self.selected = None
        else:
            # Select different gem
            if self.board.grid[r][c] >= 0:
                self.selected = (r, c)
            else:
                self.selected = None

    def _try_swap(self, r1: int, c1: int, r2: int, c2: int) -> None:
        self.board.swap(r1, c1, r2, c2)
        matches = self.board.find_all_matches()
        if matches:
            self._swap_a = (r1, c1)
            self._swap_b = (r2, c2)
            self._swap_frame = 0
            self.phase = Phase.SWAP_ANIM
        else:
            # Invalid swap — flash and revert
            self.board.swap(r1, c1, r2, c2)
            self._invalid_flash = 15

    def _update_swap_anim(self) -> None:
        self._swap_frame += 1
        if self._swap_frame >= self._swap_total:
            self._swap_a = None
            self._swap_b = None
            self._cascade_wave = 0
            self._start_clear_phase()

    def _start_clear_phase(self) -> None:
        base = self.board.find_all_matches()
        spread = self.board.spread(base) if base else set()
        self._clear_cells = base | spread
        if self._clear_cells:
            self._clear_frame = 0
            self.phase = Phase.CLEAR
            self._cascade_wave += 1
            self.combo_timer = COMBO_DECAY_FRAMES
        else:
            # No matches — check if valid moves exist
            if not self.board.has_valid_moves():
                self.board.shuffle()
            self.combo = 0
            self.phase = Phase.IDLE

    def _update_clear(self) -> None:
        self._clear_frame += 1
        if self._clear_frame >= self._clear_total:
            # Actually clear cells
            cleared = self._clear_cells
            count = self.board.clear_cells(cleared)

            # Score: base + combo bonus
            wave_mult = 1.0 + self._cascade_wave * 0.5
            points = int(count * 10 * wave_mult * max(1, self.combo + 1))
            self.score += points

            # Combo tracking
            if self._cascade_wave > 1:
                self.combo += 1
            else:
                self.combo = max(self.combo, 1)
            self.combo_timer = COMBO_DECAY_FRAMES

            # Heat
            self.heat = min(float(HEAT_MAX), self.heat + HEAT_PER_WAVE * self._cascade_wave)

            # Quake check
            if self.heat >= HEAT_QUAKE_THRESHOLD:
                self._quake_frames = 10
                self.heat = max(0.0, self.heat - HEAT_QUAKE_THRESHOLD)
                # Randomly swap two gems
                self._random_quake_swap()

            # Particles
            for r, c in cleared:
                clr = self.board.grid[r][c] if self.board.in_bounds(r, c) else 0
                self._spawn_particles(r, c, clr if clr >= 0 else pyxel.COLOR_WHITE, count=5)

            # Score float
            if cleared:
                cr, cc = list(cleared)[0]
                cx, cy = self._cell_to_px(cr, cc)
                text = f"+{points}"
                if self._cascade_wave > 1:
                    text = f"x{self.combo + 1} {text}"
                self._add_score_float(float(cx), float(cy), text, pyxel.COLOR_YELLOW)

            # Apply gravity
            self.board.apply_gravity()
            self.board.fill_empty()

            self._clear_cells = set()
            self.phase = Phase.FALL

    def _random_quake_swap(self) -> None:
        """Swap two random gems on the board."""
        cells = [(r, c) for r in range(self.board.rows) for c in range(self.board.cols)]
        a, b = random.sample(cells, 2)
        self.board.swap(a[0], a[1], b[0], b[1])

    def _update_fall(self) -> None:
        # Falling is instant for now (could animate later)
        self._start_clear_phase()

    # ── Draw ────────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
            return

        # Quake offset
        ox = random.randint(-2, 2) if self._quake_frames > 0 else 0
        oy = random.randint(-2, 2) if self._quake_frames > 0 else 0

        # Draw grid
        self._draw_grid(ox, oy)

        # Draw UI
        self._draw_ui()

        # Draw particles
        for p in self.particles:
            pyxel.pset(int(p.x) + ox, int(p.y) + oy, p.color if p.life > 5 else pyxel.COLOR_GRAY)

        # Draw floating texts
        for ft in self.floats:
            col = ft.color if ft.life > 10 else pyxel.COLOR_GRAY
            x = int(ft.x) - len(ft.text) * 2 + ox
            y = int(ft.y) + oy
            pyxel.text(x, y, ft.text, col)

    def _draw_grid(self, ox: int, oy: int) -> None:
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                clr = self.board.grid[r][c]
                x = GRID_X + c * CELL_SIZE + ox
                y = GRID_Y + r * CELL_SIZE + oy

                if clr < 0:
                    continue

                # Swap animation: lerp positions
                draw_x, draw_y = x, y
                if self.phase == Phase.SWAP_ANIM and self._swap_a and self._swap_b:
                    t = self._swap_frame / self._swap_total
                    if (r, c) == self._swap_a:
                        ar, ac = self._swap_a
                        br, bc = self._swap_b
                        draw_x = GRID_X + (ac + (bc - ac) * t) * CELL_SIZE + ox
                        draw_y = GRID_Y + (ar + (br - ar) * t) * CELL_SIZE + oy
                    elif (r, c) == self._swap_b:
                        ar, ac = self._swap_a
                        br, bc = self._swap_b
                        draw_x = GRID_X + (bc + (ac - bc) * t) * CELL_SIZE + ox
                        draw_y = GRID_Y + (br + (ar - br) * t) * CELL_SIZE + oy

                # Draw gem
                is_clearing = (r, c) in self._clear_cells
                is_selected = self.selected == (r, c) and self.phase == Phase.IDLE

                if is_clearing:
                    # Flash white during clear
                    flash = (self._clear_frame // 2) % 2
                    col = pyxel.COLOR_WHITE if flash else GEM_COLORS[clr]
                else:
                    col = GEM_COLORS[clr]

                # Gem body
                pyxel.rect(int(draw_x) + 2, int(draw_y) + 2, CELL_SIZE - 4, CELL_SIZE - 4, col)
                # Highlight top-left (3D-ish)
                pyxel.rect(int(draw_x) + 2, int(draw_y) + 2, CELL_SIZE - 4, 3, pyxel.COLOR_WHITE)
                pyxel.rect(int(draw_x) + 2, int(draw_y) + 2, 3, CELL_SIZE - 4, pyxel.COLOR_WHITE)
                # Shadow bottom-right
                pyxel.rect(
                    int(draw_x) + 2, int(draw_y) + CELL_SIZE - 5,
                    CELL_SIZE - 4, 3, GEM_COLORS_DARK[clr],
                )
                pyxel.rect(
                    int(draw_x) + CELL_SIZE - 5, int(draw_y) + 2,
                    3, CELL_SIZE - 4, GEM_COLORS_DARK[clr],
                )

                # Selection highlight
                if is_selected:
                    pyxel.rectb(int(x) + 1, int(y) + 1, CELL_SIZE - 2, CELL_SIZE - 2, pyxel.COLOR_YELLOW)

                # Invalid flash
                if self._invalid_flash > 0:
                    flash_col = pyxel.COLOR_RED if (self._invalid_flash // 3) % 2 else pyxel.COLOR_WHITE
                    pyxel.rectb(int(x) + 1, int(y) + 1, CELL_SIZE - 2, CELL_SIZE - 2, flash_col)

    def _draw_ui(self) -> None:
        # Header bar
        pyxel.rect(0, 0, SCREEN_W, 20, pyxel.COLOR_NAVY)
        pyxel.text(4, 6, f"SCORE:{self.score:>6d}", pyxel.COLOR_YELLOW)
        secs = max(0, self.timer // FPS)
        timer_text = f"TIME:{secs:>2d}"
        timer_col = pyxel.COLOR_RED if secs <= 10 else pyxel.COLOR_WHITE
        pyxel.text(SCREEN_W - 50, 6, timer_text, timer_col)

        # Combo display
        if self.combo >= 2:
            combo_text = f"COMBO x{self.combo}"
            cw = len(combo_text) * 4
            pyxel.text((SCREEN_W - cw) // 2, SCREEN_H - 10, combo_text, pyxel.COLOR_YELLOW)

        # Heat bar
        bar_x = 4
        bar_y = 24
        bar_w = 80
        bar_h = 6
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, pyxel.COLOR_GRAY)
        heat_w = int(bar_w * self.heat / HEAT_MAX)
        heat_col = pyxel.COLOR_ORANGE if self.heat < HEAT_QUAKE_THRESHOLD else pyxel.COLOR_RED
        if heat_w > 0:
            pyxel.rect(bar_x, bar_y, heat_w, bar_h, heat_col)
        pyxel.text(bar_x + bar_w + 4, bar_y - 1, "HEAT", pyxel.COLOR_WHITE)

        # Danger line on heat bar
        danger_x = bar_x + int(bar_w * HEAT_QUAKE_THRESHOLD / HEAT_MAX)
        pyxel.rect(danger_x, bar_y, 1, bar_h, pyxel.COLOR_WHITE)

    def _draw_game_over(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)
        msg = "GAME OVER"
        pyxel.text((SCREEN_W - len(msg) * 4) // 2, 80, msg, pyxel.COLOR_RED)

        score_msg = f"SCORE: {self.score}"
        pyxel.text((SCREEN_W - len(score_msg) * 4) // 2, 110, score_msg, pyxel.COLOR_WHITE)

        best_msg = f"BEST:  {self.best_score}"
        pyxel.text((SCREEN_W - len(best_msg) * 4) // 2, 130, best_msg, pyxel.COLOR_YELLOW)

        if self.score >= self.best_score and self.score > 0:
            new_msg = "NEW BEST!"
            pyxel.text((SCREEN_W - len(new_msg) * 4) // 2, 150, new_msg, pyxel.COLOR_LIME)

        restart_msg = "PRESS R TO RETRY"
        pyxel.text((SCREEN_W - len(restart_msg) * 4) // 2, 190, restart_msg, pyxel.COLOR_GRAY)


# ── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    Game()
