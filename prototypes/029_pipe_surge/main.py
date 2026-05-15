#!/usr/bin/env python3
"""PIPE SURGE — Pipe connection puzzle with chain propagation.

Reinterpreted from game idea #1 (score 32.2):
  Hooks: log/replay as asset → placed pipes persist as infrastructure
         chain collapse/amplification → same-color adjacent pipes chain-propagate
The most fun moment: watching your pipe network erupt in a cascading
chain reaction when you complete the path — same-colored pipes flashing
one by one and then all SURGING in a burst for multiplied score.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import NamedTuple

import pyxel

# ═══════════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════════
SCREEN_W = 256
SCREEN_H = 256
GRID_ROWS = 8
GRID_COLS = 8
CELL_SIZE = 28
GRID_X = 16
GRID_Y = 8
GRID_W = GRID_COLS * CELL_SIZE  # 224
GRID_H = GRID_ROWS * CELL_SIZE  # 224
GRID_RIGHT = GRID_X + GRID_W     # 240
GRID_BOTTOM = GRID_Y + GRID_H    # 232

NUM_COLORS = 4
PIPE_COLORS: tuple[int, int, int, int] = (
    pyxel.COLOR_RED,     # 0
    pyxel.COLOR_CYAN,    # 1
    pyxel.COLOR_GREEN,   # 2
    pyxel.COLOR_YELLOW,  # 3
)
COLOR_NAMES: tuple[str, str, str, str] = (
    "RED", "CYAN", "GREEN", "YELLOW",
)

HAND_SIZE = 3
COMBO_THRESHOLD = 4  # SURGE when chain >= threshold
SURGE_BONUS = 200
PATH_SCORE_BASE = 100
PRESSURE_MAX = 10

# Timing (frames at 30fps)
FLOW_ANIM_FRAMES = 3    # frames between each pipe lighting up
SURGE_ANIM_FRAMES = 20  # surge particle burst duration
TURN_TIME = 20 * 30     # 20 seconds per round

PIPE_THICKNESS = 6
HALF_CELL = CELL_SIZE // 2
HALF_THICK = PIPE_THICKNESS // 2


# ═══════════════════════════════════════════════════════════════════
# Enums / Direction
# ═══════════════════════════════════════════════════════════════════

class Dir(Enum):
    UP = 0
    RIGHT = 1
    DOWN = 2
    LEFT = 3


DIR_VEC: dict[Dir, tuple[int, int]] = {
    Dir.UP: (-1, 0),
    Dir.RIGHT: (0, 1),
    Dir.DOWN: (1, 0),
    Dir.LEFT: (0, -1),
}
DIR_OPPOSITE: dict[Dir, Dir] = {
    Dir.UP: Dir.DOWN,
    Dir.RIGHT: Dir.LEFT,
    Dir.DOWN: Dir.UP,
    Dir.LEFT: Dir.RIGHT,
}


class Phase(Enum):
    PLACING = auto()
    FLOWING = auto()
    SURGING = auto()
    GAME_OVER = auto()


# ═══════════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PipeTile:
    """A pipe tile with a color and four boolean openings (UP, RIGHT, DOWN, LEFT)."""
    color: int
    opens: tuple[bool, bool, bool, bool]

    def has_open(self, d: Dir) -> bool:
        return self.opens[d.value]


# Predefined pipe shapes
PIPE_SHAPES: dict[str, tuple[bool, bool, bool, bool]] = {
    "H":  (False, True,  False, True),    # horizontal
    "V":  (True,  False, True,  False),   # vertical
    "UR": (True,  True,  False, False),   # bend up-right
    "RD": (False, True,  True,  False),   # bend right-down
    "DL": (False, False, True,  True),    # bend down-left
    "LU": (True,  False, False, True),    # bend left-up
}
PIPE_SHAPE_KEYS = list(PIPE_SHAPES.keys())


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


class CellPos(NamedTuple):
    row: int
    col: int


# ═══════════════════════════════════════════════════════════════════
# Pipe Surge Game
# ═══════════════════════════════════════════════════════════════════

class PipeSurge:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="PIPE SURGE", display_scale=2, fps=30)
        self._reset()
        pyxel.run(self._update, self._draw)

    # ── State reset ──
    def _reset(self) -> None:
        self.grid: list[list[PipeTile | None]] = [
            [None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)
        ]
        self.phase: Phase = Phase.PLACING
        self.score: int = 0
        self.pressure: int = 0
        self.combo: int = 0
        self.turn_timer: int = TURN_TIME
        self.hand: list[PipeTile] = []
        self.selected_idx: int = 0
        self._spawn_source_drain()
        self._draw_hand()

        # Flow animation state
        self.flow_path: list[CellPos] = []
        self.flow_idx: int = 0
        self.flow_tick: int = 0
        self.active_cells: set[tuple[int, int]] = set()
        self.surge_cells: list[tuple[int, int]] = []
        self.surge_timer: int = 0

        # Particles & floating text
        self.particles: list[Particle] = []
        self.float_texts: list[FloatingText] = []

        # Hovered cell
        self.hover_cell: tuple[int, int] | None = None

    def _spawn_source_drain(self) -> None:
        """Place source and drain at random edges of the grid."""
        edges = ["top", "bottom", "left", "right"]
        src_edge = random.choice(edges)
        edges.remove(src_edge)
        drn_edge = random.choice(edges)

        def _edge_pos(edge: str) -> tuple[int, int]:
            if edge == "top":
                return (-1, random.randint(0, GRID_COLS - 1))
            elif edge == "bottom":
                return (GRID_ROWS, random.randint(0, GRID_COLS - 1))
            elif edge == "left":
                return (random.randint(0, GRID_ROWS - 1), -1)
            else:  # right
                return (random.randint(0, GRID_ROWS - 1), GRID_COLS)

        self.source_pos: tuple[int, int] = _edge_pos(src_edge)
        self.source_dir: Dir = self._edge_in_dir(src_edge)
        self.drain_pos: tuple[int, int] = _edge_pos(drn_edge)
        self.drain_dir: Dir = self._edge_in_dir(drn_edge)

    @staticmethod
    def _edge_in_dir(edge: str) -> Dir:
        """Direction flow comes FROM when entering the grid from an edge."""
        if edge == "top":
            return Dir.DOWN
        elif edge == "bottom":
            return Dir.UP
        elif edge == "left":
            return Dir.RIGHT
        else:
            return Dir.LEFT

    def _draw_hand(self) -> None:
        """Refill hand with random pipe tiles."""
        self.hand.clear()
        for _ in range(HAND_SIZE):
            shape_key = random.choice(PIPE_SHAPE_KEYS)
            color = random.randrange(NUM_COLORS)
            self.hand.append(PipeTile(color=color, opens=PIPE_SHAPES[shape_key]))
        self.selected_idx = 0

    # ═══════════════════════════════════════════════════════════════
    # Grid / cell helpers
    # ═══════════════════════════════════════════════════════════════

    def _cell_rect(self, row: int, col: int) -> tuple[int, int, int, int]:
        """Return pixel rect (x, y, w, h) for a grid cell."""
        return (
            GRID_X + col * CELL_SIZE,
            GRID_Y + row * CELL_SIZE,
            CELL_SIZE,
            CELL_SIZE,
        )

    def _cell_center(self, row: int, col: int) -> tuple[int, int]:
        return (
            GRID_X + col * CELL_SIZE + HALF_CELL,
            GRID_Y + row * CELL_SIZE + HALF_CELL,
        )

    def _cell_at_pixel(self, px: int, py: int) -> tuple[int, int] | None:
        """Return (row, col) if pixel is inside the grid, else None."""
        gx = px - GRID_X
        gy = py - GRID_Y
        if gx < 0 or gy < 0:
            return None
        col = gx // CELL_SIZE
        row = gy // CELL_SIZE
        if col >= GRID_COLS or row >= GRID_ROWS:
            return None
        return (row, col)

    def _is_valid_cell(self, row: int, col: int) -> bool:
        return 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS

    def _grid_entry_cell(self, pos: tuple[int, int], in_dir: Dir) -> tuple[int, int] | None:
        """From an edge position, compute the first grid cell the flow enters.
        in_dir is the direction flow is coming FROM (into the grid).
        Returns (row, col) or None if not valid."""
        r, c = pos
        dr, dc = DIR_VEC[in_dir]
        nr, nc = r + dr, c + dc
        if self._is_valid_cell(nr, nc):
            return (nr, nc)
        return None

    # ═══════════════════════════════════════════════════════════════
    # Pathfinding: BFS from source
    # ═══════════════════════════════════════════════════════════════

    def _find_path(self) -> list[CellPos] | None:
        """BFS from source to drain through connected pipes. Returns path or None."""
        entry = self._grid_entry_cell(self.source_pos, self.source_dir)
        if entry is None:
            return None
        er, ec = entry
        pipe = self.grid[er][ec]
        if pipe is None:
            return None
        # Source direction is the direction flow comes FROM.
        # Pipe must open toward the source (opposite of source_dir).
        needed_open = DIR_OPPOSITE[self.source_dir]
        if not pipe.has_open(needed_open):
            return None

        # BFS: each entry is (row, col, path_so_far)
        queue: list[tuple[int, int, list[CellPos]]] = [(er, ec, [CellPos(er, ec)])]
        visited: set[tuple[int, int]] = {(er, ec)}

        # Drain target: the cell adjacent to the drain position in drain_dir
        drain_entry = self._grid_entry_cell(self.drain_pos, self.drain_dir)
        # We win if we reach drain_entry AND its pipe opens toward drain

        while queue:
            r, c, path = queue.pop(0)
            pipe = self.grid[r][c]
            if pipe is None:
                continue

            # Check if this cell connects to the drain
            if drain_entry is not None and (r, c) == drain_entry:
                # Pipe must open toward drain (in drain_dir direction)
                if pipe.has_open(self.drain_dir):
                    return path

            # Explore through this pipe's openings
            for d in Dir:
                if not pipe.has_open(d):
                    continue
                dr, dc = DIR_VEC[d]
                nr, nc = r + dr, c + dc
                if not self._is_valid_cell(nr, nc):
                    continue
                if (nr, nc) in visited:
                    continue
                neighbor = self.grid[nr][nc]
                if neighbor is None:
                    continue
                # Neighbor must open toward us
                if neighbor.has_open(DIR_OPPOSITE[d]):
                    visited.add((nr, nc))
                    queue.append((nr, nc, path + [CellPos(nr, nc)]))

        return None

    # ═══════════════════════════════════════════════════════════════
    # Combo calculation
    # ═══════════════════════════════════════════════════════════════

    def _calc_combo(self, path: list[CellPos]) -> int:
        """Count the longest chain of same-color adjacent active pipes on the path."""
        if not path:
            return 0
        # Mark all path cells as active
        active_set = {(p.row, p.col) for p in path}
        # Find connected components of same-color active pipes
        visited: set[tuple[int, int]] = set()
        max_chain = 0

        for cp in path:
            r, c = cp.row, cp.col
            if (r, c) in visited:
                continue
            pipe = self.grid[r][c]
            if pipe is None:
                continue
            color = pipe.color
            # BFS to find same-color component
            comp: list[tuple[int, int]] = []
            q: list[tuple[int, int]] = [(r, c)]
            visited.add((r, c))
            while q:
                cr, cc = q.pop(0)
                comp.append((cr, cc))
                for d in Dir:
                    dr, dc = DIR_VEC[d]
                    nr, nc = cr + dr, cc + dc
                    if (nr, nc) in visited:
                        continue
                    if (nr, nc) not in active_set:
                        continue
                    np_pipe = self.grid[nr][nc]
                    if np_pipe is not None and np_pipe.color == color:
                        visited.add((nr, nc))
                        q.append((nr, nc))
            if len(comp) > max_chain:
                max_chain = len(comp)

        return max_chain

    # ═══════════════════════════════════════════════════════════════
    # Flow / Surge
    # ═══════════════════════════════════════════════════════════════

    def _trigger_flow(self) -> None:
        """Start the flow animation after player clicks FLOW."""
        path = self._find_path()
        if path is None:
            # No valid path — fizzle, gain pressure
            self.pressure += 1
            self._spawn_fizzle()
            if self.pressure >= PRESSURE_MAX:
                self.phase = Phase.GAME_OVER
            else:
                # Respawn source/drain, keep existing pipes, draw new hand
                self._spawn_source_drain()
                self._draw_hand()
            return

        self.flow_path = path
        self.flow_idx = 0
        self.flow_tick = 0
        self.combo = self._calc_combo(path)
        self.phase = Phase.FLOWING

    def _spawn_fizzle(self) -> None:
        """Visual feedback when no path connects."""
        for _ in range(12):
            cx = GRID_X + random.randint(0, GRID_W)
            cy = GRID_Y + random.randint(0, GRID_H)
            self.particles.append(Particle(
                x=float(cx), y=float(cy),
                vx=random.uniform(-1.5, 1.5),
                vy=random.uniform(-1.5, 1.5),
                life=15,
                color=pyxel.COLOR_GRAY,
            ))

    def _spawn_surge_particles(self, r: int, c: int, color: int) -> None:
        """Particle burst at a cell position."""
        cx, cy = self._cell_center(r, c)
        for _ in range(6):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(1.0, 3.0)
            self.particles.append(Particle(
                x=float(cx), y=float(cy),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=random.randint(10, 20),
                color=color,
            ))

    def _update_flowing(self) -> None:
        """Animate pipes lighting up along the path."""
        self.flow_tick += 1
        if self.flow_tick >= FLOW_ANIM_FRAMES:
            self.flow_tick = 0
            if self.flow_idx < len(self.flow_path):
                cp = self.flow_path[self.flow_idx]
                self.active_cells.add((cp.row, cp.col))
                pipe = self.grid[cp.row][cp.col]
                pipe_color = pipe.color if pipe is not None else pyxel.COLOR_WHITE
                self._spawn_surge_particles(cp.row, cp.col, pipe_color)
                self.flow_idx += 1
            else:
                # Flow animation complete
                path_len = len(self.flow_path)
                multiplier = max(1, self.combo // 2)  # combo 4 → 2x, combo 8 → 4x
                bonus = SURGE_BONUS if self.combo >= COMBO_THRESHOLD else 0
                base = PATH_SCORE_BASE + path_len * 25
                earned = (base + bonus) * multiplier
                self.score += earned

                # Floating score text
                last_cp = self.flow_path[-1]
                cx, cy = self._cell_center(last_cp.row, last_cp.col)
                txt = f"+{earned}"
                if self.combo >= COMBO_THRESHOLD:
                    txt += " SURGE!"
                self.float_texts.append(FloatingText(
                    x=float(cx), y=float(cy),
                    text=txt, life=40,
                    color=pyxel.COLOR_YELLOW if self.combo >= COMBO_THRESHOLD else pyxel.COLOR_WHITE,
                ))

                # Start SURGE animation
                if self.combo >= COMBO_THRESHOLD:
                    self.surge_cells = list(self.active_cells)
                    self.surge_timer = SURGE_ANIM_FRAMES
                    self.phase = Phase.SURGING
                else:
                    self._finish_round()

    def _update_surging(self) -> None:
        """SURGE animation: burst particles from all active pipes, then clear."""
        self.surge_timer -= 1
        if self.surge_timer <= 0:
            # Clear surged pipes from grid
            for r, c in self.surge_cells:
                self.grid[r][c] = None
                # Big particle burst
                for _ in range(3):
                    cx, cy = self._cell_center(r, c)
                    angle = random.uniform(0, math.tau)
                    speed = random.uniform(0.5, 2.0)
                    self.particles.append(Particle(
                        x=float(cx), y=float(cy),
                        vx=math.cos(angle) * speed,
                        vy=math.sin(angle) * speed,
                        life=random.randint(8, 15),
                        color=pyxel.COLOR_WHITE,
                    ))
            self._finish_round()
        elif self.surge_timer % 6 == 0:
            # Periodic particle bursts during surge
            for r, c in self.surge_cells:
                pipe = self.grid[r][c]
                if pipe is not None:
                    self._spawn_surge_particles(r, c, pipe.color)

    def _finish_round(self) -> None:
        """End current round: reset flow state, spawn new source/drain, draw hand."""
        self.flow_path.clear()
        self.flow_idx = 0
        self.flow_tick = 0
        self.active_cells.clear()
        self.surge_cells.clear()
        self.surge_timer = 0
        self.pressure = max(0, self.pressure - 1)  # successfully completing reduces pressure
        self.turn_timer = TURN_TIME
        self._spawn_source_drain()
        self._draw_hand()
        self.phase = Phase.PLACING

    # ═══════════════════════════════════════════════════════════════
    # Place tile
    # ═══════════════════════════════════════════════════════════════

    def _place_tile(self, row: int, col: int) -> None:
        """Place selected hand tile at grid position."""
        if self.phase != Phase.PLACING:
            return
        if self.grid[row][col] is not None:
            return
        if not self.hand:
            return
        tile = self.hand.pop(self.selected_idx)
        self.grid[row][col] = tile
        # Adjust selection
        if self.hand:
            if self.selected_idx >= len(self.hand):
                self.selected_idx = len(self.hand) - 1

    def _rotate_selected(self) -> None:
        """Rotate the selected hand tile 90 degrees clockwise."""
        if not self.hand or self.selected_idx >= len(self.hand):
            return
        tile = self.hand[self.selected_idx]
        # Rotate opens: UP→RIGHT→DOWN→LEFT→UP
        o = tile.opens
        new_opens = (o[3], o[0], o[1], o[2])  # LEFT → UP, UP → RIGHT, RIGHT → DOWN, DOWN → LEFT
        self.hand[self.selected_idx] = PipeTile(color=tile.color, opens=new_opens)

    # ═══════════════════════════════════════════════════════════════
    # Pyxel update
    # ═══════════════════════════════════════════════════════════════

    def _update(self) -> None:
        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self._reset()
            return

        # Update hover
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        cell = self._cell_at_pixel(mx, my)
        self.hover_cell = cell if cell is not None and self.grid[cell[0]][cell[1]] is None else None

        # Update floating texts
        self.float_texts = [ft for ft in self.float_texts if ft.life > 0]
        for ft in self.float_texts:
            ft.life -= 1
            ft.y -= 0.8

        # Update particles
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1

        if self.phase == Phase.PLACING:
            self._update_placing()
        elif self.phase == Phase.FLOWING:
            self._update_flowing()
        elif self.phase == Phase.SURGING:
            self._update_surging()

    def _update_placing(self) -> None:
        """Handle input during PLACING phase."""
        # Timer
        self.turn_timer -= 1
        if self.turn_timer <= 0:
            self.pressure += 1
            self.turn_timer = TURN_TIME
            self._spawn_source_drain()
            self._draw_hand()
            if self.pressure >= PRESSURE_MAX:
                self.phase = Phase.GAME_OVER
            return

        # Place tile on click
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            # Check FLOW button
            if self._inside_flow_button(mx, my):
                self._trigger_flow()
            elif self.hand and self.selected_idx < len(self.hand):
                cell = self._cell_at_pixel(mx, my)
                if cell is not None and self.grid[cell[0]][cell[1]] is None:
                    self._place_tile(cell[0], cell[1])

        # Select hand tile
        if pyxel.btnp(pyxel.KEY_1):
            self.selected_idx = 0
        elif pyxel.btnp(pyxel.KEY_2):
            self.selected_idx = min(1, len(self.hand) - 1)
        elif pyxel.btnp(pyxel.KEY_3):
            self.selected_idx = min(2, len(self.hand) - 1)

        # Click on hand tile to select
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and self.hand:
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            for i in range(len(self.hand)):
                hx, hy, hw, hh = self._hand_rect(i)
                if hx <= mx < hx + hw and hy <= my < hy + hh:
                    if i == self.selected_idx:
                        self._rotate_selected()
                    else:
                        self.selected_idx = i
                    break

        # Rotate selected with R or right-click
        if pyxel.btnp(pyxel.KEY_R):
            self._rotate_selected()
        if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            self._rotate_selected()

        # Trigger flow with SPACE or ENTER
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._trigger_flow()

    # ═══════════════════════════════════════════════════════════════
    # Pyxel draw
    # ═══════════════════════════════════════════════════════════════

    def _draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        # Draw grid background
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                x, y, w, h = self._cell_rect(row, col)
                is_active = (row, col) in self.active_cells
                is_surge = self.phase == Phase.SURGING and (row, col) in self.surge_cells
                if is_surge:
                    bg_color = pyxel.COLOR_NAVY
                elif is_active:
                    bg_color = pyxel.COLOR_DARK_BLUE
                else:
                    bg_color = pyxel.COLOR_BLACK
                pyxel.rect(x, y, w, h, bg_color)

        # Draw cell borders (grid lines)
        border_col = pyxel.COLOR_NAVY
        for row in range(GRID_ROWS + 1):
            y = GRID_Y + row * CELL_SIZE
            pyxel.line(GRID_X, y, GRID_RIGHT, y, border_col)
        for col in range(GRID_COLS + 1):
            x = GRID_X + col * CELL_SIZE
            pyxel.line(x, GRID_Y, x, GRID_BOTTOM, border_col)

        # Draw placed pipes
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                tile = self.grid[row][col]
                if tile is not None:
                    self._draw_pipe(row, col, tile)

        # Draw source indicator
        self._draw_source()
        # Draw drain indicator
        self._draw_drain()

        # Draw hover highlight
        if self.hover_cell is not None and self.phase == Phase.PLACING:
            hr, hc = self.hover_cell
            if self.grid[hr][hc] is None and self.hand:
                hx, hy, _, _ = self._cell_rect(hr, hc)
                preview_color = PIPE_COLORS[self.hand[self.selected_idx].color]
                pyxel.rectb(hx + 1, hy + 1, CELL_SIZE - 2, CELL_SIZE - 2, preview_color)

        # Draw hand
        self._draw_hand_ui()

        # Draw flow button
        self._draw_flow_button()

        # Draw UI
        self._draw_ui()

        # Draw floating texts
        for ft in self.float_texts:
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

        # Draw particles
        for p in self.particles:
            px = int(p.x)
            py = int(p.y)
            pyxel.pset(px, py, p.color)
            if p.life > 3:
                pyxel.pset(px + 1, py, p.color)
                pyxel.pset(px, py + 1, p.color)

        # Game over screen
        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_pipe(self, row: int, col: int, tile: PipeTile) -> None:
        """Draw a pipe tile at grid position."""
        cx, cy = self._cell_center(row, col)
        color = PIPE_COLORS[tile.color]
        is_active = (row, col) in self.active_cells
        is_surge = self.phase == Phase.SURGING and (row, col) in self.surge_cells

        if is_surge:
            draw_color = pyxel.COLOR_WHITE
        elif is_active:
            draw_color = pyxel.COLOR_WHITE
        else:
            draw_color = color

        o = tile.opens
        # Draw horizontal segment
        if o[Dir.LEFT.value] or o[Dir.RIGHT.value]:
            x1 = cx - HALF_CELL if o[Dir.LEFT.value] else cx
            x2 = cx + HALF_CELL if o[Dir.RIGHT.value] else cx
            pyxel.rect(x1, cy - HALF_THICK, x2 - x1, PIPE_THICKNESS, draw_color)
        # Draw vertical segment
        if o[Dir.UP.value] or o[Dir.DOWN.value]:
            y1 = cy - HALF_CELL if o[Dir.UP.value] else cy
            y2 = cy + HALF_CELL if o[Dir.DOWN.value] else cy
            pyxel.rect(cx - HALF_THICK, y1, PIPE_THICKNESS, y2 - y1, draw_color)
        # Center dot
        if sum(o) >= 2:
            pyxel.circ(cx, cy, HALF_THICK, draw_color)

    def _draw_source(self) -> None:
        """Draw source indicator on the edge of the grid."""
        sr, sc = self.source_pos
        if sr == -1:  # top edge
            x = GRID_X + sc * CELL_SIZE
            y = GRID_Y - 6
            pyxel.tri(x + HALF_CELL, y, x + HALF_CELL - 4, y + 6, x + HALF_CELL + 4, y + 6, pyxel.COLOR_WHITE)
        elif sr == GRID_ROWS:  # bottom edge
            x = GRID_X + sc * CELL_SIZE
            y = GRID_BOTTOM + 6
            pyxel.tri(x + HALF_CELL, y, x + HALF_CELL - 4, y - 6, x + HALF_CELL + 4, y - 6, pyxel.COLOR_WHITE)
        elif sc == -1:  # left edge
            x = GRID_X - 6
            y = GRID_Y + sr * CELL_SIZE
            pyxel.tri(x, y + HALF_CELL, x + 6, y + HALF_CELL - 4, x + 6, y + HALF_CELL + 4, pyxel.COLOR_WHITE)
        else:  # right edge
            x = GRID_RIGHT + 6
            y = GRID_Y + sr * CELL_SIZE
            pyxel.tri(x, y + HALF_CELL, x - 6, y + HALF_CELL - 4, x - 6, y + HALF_CELL + 4, pyxel.COLOR_WHITE)

    def _draw_drain(self) -> None:
        """Draw drain indicator on the edge of the grid."""
        dr, dc = self.drain_pos
        if dr == -1:  # top edge
            x = GRID_X + dc * CELL_SIZE
            y = GRID_Y - 6
            pyxel.rect(x + HALF_CELL - 4, y - 2, 8, 8, pyxel.COLOR_LIME)
        elif dr == GRID_ROWS:  # bottom edge
            x = GRID_X + dc * CELL_SIZE
            y = GRID_BOTTOM + 6
            pyxel.rect(x + HALF_CELL - 4, y - 6, 8, 8, pyxel.COLOR_LIME)
        elif dc == -1:  # left edge
            x = GRID_X - 6
            y = GRID_Y + dr * CELL_SIZE
            pyxel.rect(x - 2, y + HALF_CELL - 4, 8, 8, pyxel.COLOR_LIME)
        else:  # right edge
            x = GRID_RIGHT + 6
            y = GRID_Y + dr * CELL_SIZE
            pyxel.rect(x - 6, y + HALF_CELL - 4, 8, 8, pyxel.COLOR_LIME)

    def _hand_rect(self, idx: int) -> tuple[int, int, int, int]:
        """Pixel rect for hand tile at index."""
        base_x = GRID_X
        base_y = GRID_BOTTOM + 10
        spacing = CELL_SIZE + 4
        return (base_x + idx * spacing, base_y, CELL_SIZE, CELL_SIZE)

    def _draw_hand_ui(self) -> None:
        """Draw the hand tiles below the grid."""
        if not self.hand:
            return
        pyxel.text(GRID_X, GRID_BOTTOM + 2, "HAND:", pyxel.COLOR_GRAY)

        for i, tile in enumerate(self.hand):
            hx, hy, _, _ = self._hand_rect(i)
            # Selection highlight
            if i == self.selected_idx and self.phase == Phase.PLACING:
                pyxel.rectb(hx - 2, hy - 2, CELL_SIZE + 4, CELL_SIZE + 4, pyxel.COLOR_WHITE)
            # Draw mini pipe
            mx = hx + HALF_CELL
            my = hy + HALF_CELL
            color = PIPE_COLORS[tile.color]
            o = tile.opens
            half = HALF_CELL - 2
            half_t = HALF_THICK - 1
            if o[Dir.LEFT.value] or o[Dir.RIGHT.value]:
                x1 = mx - half if o[Dir.LEFT.value] else mx
                x2 = mx + half if o[Dir.RIGHT.value] else mx
                pyxel.rect(x1, my - half_t, x2 - x1, PIPE_THICKNESS - 2, color)
            if o[Dir.UP.value] or o[Dir.DOWN.value]:
                y1 = my - half if o[Dir.UP.value] else my
                y2 = my + half if o[Dir.DOWN.value] else my
                pyxel.rect(mx - half_t, y1, PIPE_THICKNESS - 2, y2 - y1, color)
            if sum(o) >= 2:
                pyxel.circ(mx, my, half_t, color)

    def _inside_flow_button(self, mx: int, my: int) -> bool:
        """Check if mouse is over the FLOW button."""
        bx = GRID_X + HAND_SIZE * (CELL_SIZE + 4) + 8
        by = GRID_BOTTOM + 10
        bw = 50
        bh = CELL_SIZE
        return bx <= mx < bx + bw and by <= my < by + bh

    def _draw_flow_button(self) -> None:
        """Draw the FLOW button."""
        bx = GRID_X + HAND_SIZE * (CELL_SIZE + 4) + 8
        by = GRID_BOTTOM + 10
        bw = 50
        bh = CELL_SIZE
        hover = (
            self.phase == Phase.PLACING
            and self._inside_flow_button(pyxel.mouse_x, pyxel.mouse_y)
        )
        btn_color = pyxel.COLOR_GREEN if hover else pyxel.COLOR_LIME
        pyxel.rect(bx, by, bw, bh, btn_color)
        pyxel.text(bx + 5, by + 10, "FLOW", pyxel.COLOR_BLACK)

    def _draw_ui(self) -> None:
        """Draw score, pressure, combo, timer at top."""
        # Timer bar at top
        bar_w = int(GRID_W * self.turn_timer / TURN_TIME)
        bar_color = pyxel.COLOR_RED if self.turn_timer < TURN_TIME // 3 else (
            pyxel.COLOR_YELLOW if self.turn_timer < TURN_TIME // 2 else pyxel.COLOR_GREEN
        )
        pyxel.rect(GRID_X, 2, bar_w, 4, bar_color)

        # Score
        pyxel.text(2, 2, f"SC:{self.score}", pyxel.COLOR_WHITE)
        # Pressure
        pressure_color = pyxel.COLOR_RED if self.pressure >= PRESSURE_MAX - 2 else pyxel.COLOR_GRAY
        pyxel.text(2, 10, f"PR:{self.pressure}/{PRESSURE_MAX}", pressure_color)
        # Combo
        if self.combo > 0:
            combo_text = f"CB:{self.combo}"
            combo_color = pyxel.COLOR_YELLOW if self.combo >= COMBO_THRESHOLD else pyxel.COLOR_WHITE
            pyxel.text(SCREEN_W - len(combo_text) * 4 - 2, 2, combo_text, combo_color)

    def _draw_game_over(self) -> None:
        """Draw game over overlay."""
        # Darken
        for y in range(0, SCREEN_H, 4):
            pyxel.rect(0, y, SCREEN_W, 2, pyxel.COLOR_BLACK)
        pyxel.text(SCREEN_W // 2 - 40, SCREEN_H // 2 - 20, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(SCREEN_W // 2 - 55, SCREEN_H // 2, f"FINAL SCORE: {self.score}", pyxel.COLOR_WHITE)
        pyxel.text(SCREEN_W // 2 - 50, SCREEN_H // 2 + 20, "CLICK or R to RESTART", pyxel.COLOR_GRAY)


# ═══════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    PipeSurge()
