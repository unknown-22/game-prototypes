"""TETRA SURGE — Color-Match Tetris with Chain Reactions.

Core fun moment: clearing a row sets off a BFS chain reaction that
propagates through same-colored blocks, building a cascading COMBO.
COMBO >= 5 unlocks a SURGE rainbow bomb that obliterates a 5×5 area.
"""
from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass
from enum import IntEnum

import pyxel

# ── Constants ──────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
DISPLAY_SCALE = 2
FPS = 60

COLS = 10
ROWS = 20
CELL = 12
PLAYFIELD_X = 8
PLAYFIELD_Y = 0
PLAYFIELD_W = COLS * CELL  # 120
PLAYFIELD_H = ROWS * CELL  # 240
HUD_X = PLAYFIELD_X + PLAYFIELD_W + 12  # 140
HUD_W = SCREEN_W - HUD_X - 8  # ~172

COLOR_BLACK = 0
COLOR_NAVY = 1
COLOR_PURPLE = 2
COLOR_GREEN = 3
COLOR_DARK_BLUE = 5
COLOR_LIGHT_BLUE = 6
COLOR_WHITE = 7
COLOR_RED = 8
COLOR_ORANGE = 9
COLOR_YELLOW = 10
COLOR_LIME = 11
COLOR_CYAN = 12
COLOR_GRAY = 13
COLOR_PINK = 14

PIECE_TYPES = 7
BOMB_TYPE = 7

PIECE_COLORS: tuple[int, int, int, int, int, int, int, int] = (
    COLOR_CYAN,        # I = 0
    COLOR_YELLOW,      # O = 1
    COLOR_PURPLE,      # T = 2
    COLOR_GREEN,       # S = 3
    COLOR_RED,         # Z = 4
    COLOR_LIGHT_BLUE,  # J = 5
    COLOR_ORANGE,      # L = 6
    COLOR_PINK,        # BOMB = 7
)

PIECE_NAMES: tuple[str, str, str, str, str, str, str, str] = (
    "I", "O", "T", "S", "Z", "J", "L", "BOMB",
)

# SRS shape definitions: SHAPES[piece_type][rotation_state] = list of (col_offset, row_offset)
SHAPES: tuple[tuple[tuple[tuple[int, int], ...], ...], ...] = (
    # I (0) — 4×4 bounding box
    (
        ((0, 1), (1, 1), (2, 1), (3, 1)),  # state 0: horizontal
        ((2, 0), (2, 1), (2, 2), (2, 3)),  # state 1: vertical
        ((0, 2), (1, 2), (2, 2), (3, 2)),  # state 2: horizontal
        ((1, 0), (1, 1), (1, 2), (1, 3)),  # state 3: vertical
    ),
    # O (1) — 3×3 bounding box
    (
        ((0, 0), (1, 0), (0, 1), (1, 1)),
        ((0, 0), (1, 0), (0, 1), (1, 1)),
        ((0, 0), (1, 0), (0, 1), (1, 1)),
        ((0, 0), (1, 0), (0, 1), (1, 1)),
    ),
    # T (2) — 3×3
    (
        ((1, 0), (0, 1), (1, 1), (2, 1)),  # pointing up
        ((1, 0), (1, 1), (2, 1), (1, 2)),  # pointing right
        ((0, 1), (1, 1), (2, 1), (1, 2)),  # pointing down
        ((1, 0), (0, 1), (1, 1), (1, 2)),  # pointing left
    ),
    # S (3) — 3×3
    (
        ((1, 0), (2, 0), (0, 1), (1, 1)),
        ((1, 0), (1, 1), (2, 1), (2, 2)),
        ((1, 0), (2, 0), (0, 1), (1, 1)),
        ((1, 0), (1, 1), (2, 1), (2, 2)),
    ),
    # Z (4) — 3×3
    (
        ((0, 0), (1, 0), (1, 1), (2, 1)),
        ((2, 0), (1, 1), (2, 1), (1, 2)),
        ((0, 0), (1, 0), (1, 1), (2, 1)),
        ((2, 0), (1, 1), (2, 1), (1, 2)),
    ),
    # J (5) — 3×3
    (
        ((0, 0), (0, 1), (1, 1), (2, 1)),
        ((1, 0), (2, 0), (1, 1), (1, 2)),
        ((0, 1), (1, 1), (2, 1), (2, 2)),
        ((1, 0), (1, 1), (0, 2), (1, 2)),
    ),
    # L (6) — 3×3
    (
        ((2, 0), (0, 1), (1, 1), (2, 1)),
        ((1, 0), (1, 1), (1, 2), (2, 2)),
        ((0, 1), (1, 1), (2, 1), (0, 2)),
        ((0, 0), (1, 0), (1, 1), (1, 2)),
    ),
    # BOMB (7) — 3×3 full block
    (
        ((0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1), (0, 2), (1, 2), (2, 2)),
        ((0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1), (0, 2), (1, 2), (2, 2)),
        ((0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1), (0, 2), (1, 2), (2, 2)),
        ((0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1), (0, 2), (1, 2), (2, 2)),
    ),
)

# Wall-kick offsets to try when rotation collides (col_shift, row_shift)
WALL_KICKS: tuple[tuple[int, int], ...] = (
    (0, 0), (-1, 0), (1, 0), (0, -1), (-2, 0), (2, 0),
)

# Scoring
LINE_SCORES: tuple[int, int, int, int, int] = (0, 100, 300, 500, 800)
CHAIN_CELL_SCORE = 50
SURGE_THRESHOLD = 5
LINES_PER_LEVEL = 10

# Timings (frames)
LINE_CLEAR_FRAMES = 15
SPAWN_FRAMES = 8

# Drop speeds: frames per auto-drop step at each level
DROP_SPEEDS = (
    48, 43, 38, 33, 28, 23, 18, 13, 8, 6,
    5, 5, 5, 4, 4, 4, 3, 3, 3, 2,
)
DAS_INITIAL = 12  # Delayed Auto Shift: frames before repeat starts
DAS_REPEAT = 2    # frames between repeated moves
SOFT_DROP_FRAMES = 3


# ── Phase Enum ─────────────────────────────────────────────────────────

class Phase(IntEnum):
    TITLE = 0
    PLAYING = 1
    LINE_CLEAR = 2
    SPAWN = 3
    GAME_OVER = 4


# ── Dataclasses ────────────────────────────────────────────────────────

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


# ── Game Class ─────────────────────────────────────────────────────────

class Game:
    """TETRA SURGE — color-match Tetris with BFS chain-reaction clearing."""

    def __init__(self) -> None:
        pyxel.init(
            SCREEN_W, SCREEN_H,
            title="TETRA SURGE",
            display_scale=DISPLAY_SCALE,
            fps=FPS,
        )
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── State initialisation ────────────────────────────────────────

    def reset(self) -> None:
        self._rng = random.Random()
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.level: int = 0
        self.lines: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.surge: bool = False
        self.grid: list[list[int]] = [[0] * COLS for _ in range(ROWS)]
        self.piece_type: int = 0
        self.piece_rot: int = 0
        self.piece_x: int = 0
        self.piece_y: int = 0
        self.piece_color: int = 0
        self.next_type: int = self._rng.randint(0, PIECE_TYPES - 1)
        self._bag: list[int] = []
        self._drop_timer: int = 0
        self._das_timer: int = 0
        self._das_dir: int = 0
        self._phase_timer: int = 0
        self._cleared_flash: list[tuple[int, int, int]] = []  # (row, col, color)
        self._chain_cells: list[tuple[int, int, int]] = []  # (row, col, color) for chain animation
        self._current_chain_combo: int = 0
        self._chain_step: int = 0
        self.particles: list[Particle] = []
        self._shake_frames: int = 0
        self._auto_repeat_timer: int = 0

    # ── Piece management ────────────────────────────────────────────

    def _next_from_bag(self) -> int:
        """Draw next piece type using 7-bag randomiser."""
        if not self._bag:
            self._bag = list(range(PIECE_TYPES))
            self._rng.shuffle(self._bag)
        return self._bag.pop()

    def _spawn_piece(self) -> None:
        """Spawn the next piece at top-centre. Sets self.piece_* fields."""
        self.piece_type = self.next_type
        self.piece_rot = 0
        self.piece_color = PIECE_COLORS[self.piece_type]

        shape = SHAPES[self.piece_type][0]
        max_col = max(c for c, _ in shape)
        piece_w = max_col + 1
        self.piece_x = (COLS - piece_w) // 2
        self.piece_y = 0

        self.next_type = self._next_from_bag()

    def _spawn_bomb(self) -> None:
        """Spawn a SURGE rainbow bomb piece."""
        self.piece_type = BOMB_TYPE
        self.piece_rot = 0
        self.piece_color = PIECE_COLORS[BOMB_TYPE]
        self.piece_x = (COLS - 3) // 2  # 3-wide bomb
        self.piece_y = 0

    def _piece_cells(self) -> list[tuple[int, int]]:
        """Return list of (col, row) absolute grid positions for current piece."""
        shape = SHAPES[self.piece_type][self.piece_rot]
        return [(self.piece_x + dx, self.piece_y + dy) for dx, dy in shape]

    def _collides(self, piece_type: int, piece_rot: int, px: int, py: int) -> bool:
        """Check if piece at given position collides with walls or locked blocks."""
        shape = SHAPES[piece_type][piece_rot]
        for dx, dy in shape:
            col = px + dx
            row = py + dy
            if col < 0 or col >= COLS or row < 0 or row >= ROWS:
                return True
            if self.grid[row][col] != 0:
                return True
        return False

    def _move_piece(self, dx: int, dy: int) -> bool:
        """Try to move piece by (dx, dy). Return True on success."""
        if self.phase != Phase.PLAYING:
            return False
        new_x = self.piece_x + dx
        new_y = self.piece_y + dy
        if not self._collides(self.piece_type, self.piece_rot, new_x, new_y):
            self.piece_x = new_x
            self.piece_y = new_y
            return True
        return False

    def _rotate_piece(self) -> bool:
        """Try SRS rotation (clockwise). Return True on success."""
        if self.phase != Phase.PLAYING:
            return False
        new_rot = (self.piece_rot + 1) % 4
        for kick_dx, kick_dy in WALL_KICKS:
            new_x = self.piece_x + kick_dx
            new_y = self.piece_y + kick_dy
            if not self._collides(self.piece_type, new_rot, new_x, new_y):
                self.piece_rot = new_rot
                self.piece_x = new_x
                self.piece_y = new_y
                return True
        return False

    def _hard_drop(self) -> None:
        """Instantly drop piece to lowest valid row and lock."""
        if self.phase != Phase.PLAYING:
            return
        while not self._collides(self.piece_type, self.piece_rot, self.piece_x, self.piece_y + 1):
            self.piece_y += 1
        self._lock_piece()

    def _lock_piece(self) -> None:
        """Lock current piece onto grid and trigger clear/chain processing."""
        cells = self._piece_cells()
        piece_type = self.piece_type
        piece_color = self.piece_color

        for col, row in cells:
            if 0 <= row < ROWS and 0 <= col < COLS:
                self.grid[row][col] = piece_color

        if piece_type == BOMB_TYPE:
            self._bomb_explode(cells)

        filled_rows = self._find_filled_rows()
        if filled_rows:
            self._process_line_clear(filled_rows)
            self._phase_timer = LINE_CLEAR_FRAMES
            self.phase = Phase.LINE_CLEAR
        else:
            self._phase_timer = SPAWN_FRAMES
            self.phase = Phase.SPAWN

    def _bomb_explode(self, cells: list[tuple[int, int]]) -> None:
        """Clear 5×5 area around the bomb placement."""
        if not cells:
            return
        min_c = min(c for c, _ in cells)
        max_c = max(c for c, _ in cells)
        min_r = min(r for _, r in cells)
        max_r = max(r for _, r in cells)
        cx = (min_c + max_c) // 2
        cy = (min_r + max_r) // 2

        cleared = []
        for r in range(cy - 2, cy + 3):
            for c in range(cx - 2, cx + 3):
                if 0 <= r < ROWS and 0 <= c < COLS and self.grid[r][c] != 0:
                    cleared.append((r, c, self.grid[r][c]))
                    self._spawn_particles_at_cell(r, c, self.grid[r][c], 3)
                    self.grid[r][c] = 0

        self._chain_cells.extend(cleared)
        self._shake_frames = 10
        self.combo = max(self.combo, 5)

    def _find_filled_rows(self) -> list[int]:
        return [r for r in range(ROWS) if all(self.grid[r][c] != 0 for c in range(COLS))]

    def _process_line_clear(self, filled_rows: list[int]) -> None:
        """Clear filled rows, BFS chain propagate, gravity compact, compute score."""
        # Save seeds for BFS before removing rows: (row, col, color)
        seeds: list[tuple[int, int, int]] = []
        for r in filled_rows:
            for c in range(COLS):
                if self.grid[r][c] != 0:
                    seeds.append((r, c, self.grid[r][c]))

        # Remove filled rows (descending order) and insert empty rows at top
        for r in sorted(filled_rows, reverse=True):
            del self.grid[r]
            self.grid.insert(0, [0] * COLS)

        # Map original row to current row: current = orig + count(filled_rows > orig)
        def orig_to_curr(orow: int) -> int:
            return orow + sum(1 for fr in filled_rows if fr > orow)

        # Score calculation
        combo = 1
        num_lines = len(filled_rows)
        line_score = LINE_SCORES[num_lines] * (self.level + 1) * combo
        chain_score = 0

        # BFS propagation from cleared row cells
        visited: set[tuple[int, int]] = set()
        queue: deque[tuple[int, int, int]] = deque()  # (current_row, col, color)

        for seed_r, seed_c, seed_color in seeds:
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr_orig = seed_r + dr
                nc = seed_c + dc
                if nr_orig < 0 or nr_orig >= ROWS or nc < 0 or nc >= COLS:
                    continue
                if nr_orig in filled_rows:
                    continue
                nr_curr = orig_to_curr(nr_orig)
                if nr_curr < 0 or nr_curr >= ROWS:
                    continue
                if (nr_curr, nc) in visited:
                    continue
                cell_color = self.grid[nr_curr][nc]
                if cell_color != 0 and cell_color == seed_color:
                    visited.add((nr_curr, nc))
                    queue.append((nr_curr, nc, seed_color))

        # BFS expand
        while queue:
            r, c, color = queue.popleft()
            combo += 1
            chain_score += CHAIN_CELL_SCORE * (self.level + 1) * combo
            self.grid[r][c] = 0
            self._chain_cells.append((r, c, color))

            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < ROWS and 0 <= nc < COLS:
                    if (nr, nc) in visited:
                        continue
                    if self.grid[nr][nc] == color:
                        visited.add((nr, nc))
                        queue.append((nr, nc, color))

        # Extra chain from bomb-exploded cells
        for br, bc, bcolor in self._chain_cells:
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr_orig = br + dr
                nc = bc + dc
                if 0 <= nr_orig < ROWS and 0 <= nc < COLS:
                    nr_curr = nr_orig  # _chain_cells already stores current positions
                    if (nr_curr, nc) in visited:
                        continue
                    cell_color = self.grid[nr_curr][nc]
                    if cell_color != 0 and cell_color == bcolor:
                        visited.add((nr_curr, nc))
                        queue.append((nr_curr, nc, bcolor))

        # Process additional queue items from bomb chain
        while queue:
            r, c, color = queue.popleft()
            combo += 1
            chain_score += CHAIN_CELL_SCORE * (self.level + 1) * combo
            self.grid[r][c] = 0
            self._chain_cells.append((r, c, color))

            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < ROWS and 0 <= nc < COLS:
                    if (nr, nc) in visited:
                        continue
                    if self.grid[nr][nc] == color:
                        visited.add((nr, nc))
                        queue.append((nr, nc, color))

        total_score = line_score + chain_score
        self.score += total_score
        self.combo = combo
        self.max_combo = max(self.max_combo, combo)
        self._current_chain_combo = combo

        # SURGE check
        if combo >= SURGE_THRESHOLD:
            self.surge = True

        # Update lines and level
        chain_lines = len(self._chain_cells) // COLS  # approximate lines from chain
        total_lines = num_lines + chain_lines
        self.lines += total_lines
        self.level = self.lines // LINES_PER_LEVEL

        # Store cleared rows for flash animation
        self._cleared_flash = [(r, c, PIECE_COLORS[0]) for r in filled_rows for c in range(COLS)]

        # Gravity compact
        self._gravity_compact()

        # Check for cascaded filled rows (after gravity)
        more_filled = self._find_filled_rows()
        if more_filled:
            # Recursively process — but cap to avoid infinite loops
            self._process_line_clear(more_filled)

    def _gravity_compact(self) -> None:
        """Shift all floating blocks down to fill gaps."""
        for c in range(COLS):
            write_row = ROWS - 1
            for r in range(ROWS - 1, -1, -1):
                if self.grid[r][c] != 0:
                    if r != write_row:
                        self.grid[write_row][c] = self.grid[r][c]
                        self.grid[r][c] = 0
                    write_row -= 1

    def _is_game_over(self) -> bool:
        """Check if spawn position collides with existing blocks."""
        next_type = self.next_type
        shape = SHAPES[next_type][0]
        max_col = max(c for c, _ in shape)
        piece_w = max_col + 1
        px = (COLS - piece_w) // 2
        py = 0
        for dx, dy in shape:
            col, row = px + dx, py + dy
            if 0 <= col < COLS and 0 <= row < ROWS:
                if self.grid[row][col] != 0:
                    return True
        return False

    def _get_drop_speed(self) -> int:
        """Return frames between auto-drop steps for current level."""
        lvl = min(self.level, len(DROP_SPEEDS) - 1)
        return DROP_SPEEDS[lvl]

    # ── Particles ────────────────────────────────────────────────────

    def _spawn_particles_at_cell(self, row: int, col: int, color: int, count: int) -> None:
        """Spawn particles at a grid cell's screen position."""
        cx = PLAYFIELD_X + col * CELL + CELL // 2
        cy = PLAYFIELD_Y + row * CELL + CELL // 2
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.5)
            self.particles.append(
                Particle(
                    x=float(cx), y=float(cy),
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=15 + self._rng.randint(0, 10),
                    color=color,
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    # ── Input helpers ────────────────────────────────────────────────

    @staticmethod
    def _read_confirm() -> bool:
        return pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE)

    # ── Update ───────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if self._read_confirm():
                self.reset()
                self.phase = Phase.SPAWN
                self._phase_timer = 1
            return

        if self.phase == Phase.GAME_OVER:
            if self._read_confirm():
                self.reset()
                self.phase = Phase.SPAWN
                self._phase_timer = 1
            return

        # Phase timers
        if self.phase == Phase.LINE_CLEAR:
            self._phase_timer -= 1
            # Spawn particles for chain cells while animating
            if self._chain_step < len(self._chain_cells) and self._phase_timer % 2 == 0:
                r, c, color = self._chain_cells[self._chain_step]
                self._spawn_particles_at_cell(r, c, color, 4)
                self._chain_step += 1
            if self._phase_timer <= 0:
                self._chain_cells.clear()
                self._chain_step = 0
                self._cleared_flash.clear()
                self._phase_timer = SPAWN_FRAMES
                self.phase = Phase.SPAWN
            self._update_particles()
            if self._shake_frames > 0:
                self._shake_frames -= 1
            return

        if self.phase == Phase.SPAWN:
            self._phase_timer -= 1
            if self._phase_timer <= 0:
                if self._is_game_over():
                    self.phase = Phase.GAME_OVER
                else:
                    if self.surge:
                        self._spawn_bomb()
                        self.surge = False
                    else:
                        self._spawn_piece()
                    self._drop_timer = 0
                    self._das_timer = 0
                    self._auto_repeat_timer = 0
                    self.phase = Phase.PLAYING
            self._update_particles()
            if self._shake_frames > 0:
                self._shake_frames -= 1
            return

        # ────── PLAYING ──────
        self._handle_input()
        self._update_drop()
        self._update_particles()
        if self._shake_frames > 0:
            self._shake_frames -= 1

    def _handle_input(self) -> None:
        """Read DAS-based horizontal movement, rotation, and drop inputs."""
        left = pyxel.btn(pyxel.KEY_LEFT)
        right = pyxel.btn(pyxel.KEY_RIGHT)

        if left and not right:
            if self._das_dir != -1:
                self._das_dir = -1
                self._das_timer = 0
                self._auto_repeat_timer = 0
                self._move_piece(-1, 0)
            else:
                self._das_timer += 1
                if self._das_timer >= DAS_INITIAL:
                    self._auto_repeat_timer += 1
                    if self._auto_repeat_timer >= DAS_REPEAT:
                        self._auto_repeat_timer = 0
                        self._move_piece(-1, 0)
        elif right and not left:
            if self._das_dir != 1:
                self._das_dir = 1
                self._das_timer = 0
                self._auto_repeat_timer = 0
                self._move_piece(1, 0)
            else:
                self._das_timer += 1
                if self._das_timer >= DAS_INITIAL:
                    self._auto_repeat_timer += 1
                    if self._auto_repeat_timer >= DAS_REPEAT:
                        self._auto_repeat_timer = 0
                        self._move_piece(1, 0)
        else:
            self._das_dir = 0
            self._das_timer = 0
            self._auto_repeat_timer = 0

        if pyxel.btnp(pyxel.KEY_UP):
            self._rotate_piece()
            self._das_timer = 0

        if pyxel.btnp(pyxel.KEY_SPACE):
            self._hard_drop()

        if pyxel.btn(pyxel.KEY_DOWN):
            self._drop_timer = max(self._drop_timer, self._get_drop_speed() - SOFT_DROP_FRAMES)

    def _update_drop(self) -> None:
        """Auto-drop piece based on timer."""
        self._drop_timer += 1
        speed = self._get_drop_speed()
        is_soft = pyxel.btn(pyxel.KEY_DOWN)
        effective_speed = max(SOFT_DROP_FRAMES, speed) if is_soft else speed

        if self._drop_timer >= effective_speed:
            self._drop_timer = 0
            if not self._move_piece(0, 1):
                self._lock_piece()
                if is_soft:
                    self.score += 1

    # ── Draw ─────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(COLOR_BLACK)

        sx = 0
        sy = 0
        if self._shake_frames > 0:
            sx = self._rng.randint(-3, 3)
            sy = self._rng.randint(-3, 3)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        self._draw_playfield_bg(sx, sy)
        self._draw_grid(sx, sy)

        if self.phase == Phase.PLAYING:
            self._draw_ghost_piece(sx, sy)
            self._draw_piece(sx, sy)

        self._draw_particles(sx, sy)
        self._draw_hud()

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        cx = SCREEN_W // 2
        y = 30
        pyxel.text(cx - 47, y, "TETRA SURGE", COLOR_CYAN)
        y += 20
        pyxel.text(cx - 67, y, "Color-Match Chain Tetris", COLOR_GRAY)
        y += 30
        pyxel.text(cx - 50, y, "LEFT / RIGHT: Move", COLOR_WHITE)
        y += 12
        pyxel.text(cx - 50, y, "UP: Rotate", COLOR_WHITE)
        y += 12
        pyxel.text(cx - 50, y, "DOWN: Soft Drop", COLOR_WHITE)
        y += 12
        pyxel.text(cx - 50, y, "SPACE: Hard Drop", COLOR_WHITE)
        y += 28
        pyxel.text(cx - 42, y, "Clear matching-color", COLOR_GREEN)
        y += 12
        pyxel.text(cx - 42, y, "chains for COMBO!", COLOR_GREEN)
        y += 12
        pyxel.text(cx - 42, y, "COMBO >= 5 = SURGE!", COLOR_PINK)
        y += 30
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(cx - 35, y, "PRESS ENTER", COLOR_YELLOW)

    def _draw_playfield_bg(self, sx: int, sy: int) -> None:
        px = PLAYFIELD_X + sx
        py = PLAYFIELD_Y + sy
        pyxel.rect(px - 1, py - 1, PLAYFIELD_W + 2, PLAYFIELD_H + 2, COLOR_WHITE)
        pyxel.rect(px, py, PLAYFIELD_W, PLAYFIELD_H, COLOR_BLACK)

    def _draw_grid(self, sx: int, sy: int) -> None:
        for r in range(ROWS):
            for c in range(COLS):
                color = self.grid[r][c]
                if color != 0:
                    px = PLAYFIELD_X + c * CELL + sx
                    py = PLAYFIELD_Y + r * CELL + sy
                    pyxel.rect(px, py, CELL, CELL, color)
                    pyxel.rectb(px, py, CELL, CELL, COLOR_BLACK)

    def _draw_ghost_piece(self, sx: int, sy: int) -> None:
        """Draw translucent ghost piece at hard-drop target."""
        ghost_y = self.piece_y
        while not self._collides(self.piece_type, self.piece_rot, self.piece_x, ghost_y + 1):
            ghost_y += 1

        if ghost_y == self.piece_y:
            return

        shape = SHAPES[self.piece_type][self.piece_rot]
        for dx, dy in shape:
            col = self.piece_x + dx
            row = ghost_y + dy
            if 0 <= row < ROWS and 0 <= col < COLS:
                px = PLAYFIELD_X + col * CELL + sx
                py = PLAYFIELD_Y + row * CELL + sy
                pyxel.rectb(px, py, CELL, CELL, COLOR_GRAY)

    def _draw_piece(self, sx: int, sy: int) -> None:
        shape = SHAPES[self.piece_type][self.piece_rot]
        color = self.piece_color
        for dx, dy in shape:
            col = self.piece_x + dx
            row = self.piece_y + dy
            if 0 <= row < ROWS and 0 <= col < COLS:
                px = PLAYFIELD_X + col * CELL + sx
                py = PLAYFIELD_Y + row * CELL + sy
                pyxel.rect(px, py, CELL, CELL, color)
                pyxel.rectb(px, py, CELL, CELL, COLOR_BLACK)

    def _draw_particles(self, sx: int, sy: int) -> None:
        for p in self.particles:
            px = int(p.x) + sx
            py = int(p.y) + sy
            if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
                pyxel.pset(px, py, p.color)

    def _draw_hud(self) -> None:
        x = HUD_X
        pyxel.rect(x - 4, 0, HUD_W + 8, SCREEN_H, COLOR_NAVY)

        y = 6
        pyxel.text(x, y, "NEXT", COLOR_GRAY)
        y += 10

        # Draw next piece preview
        self._draw_next_piece(x, y)
        y += 50

        pyxel.text(x, y, "SCORE", COLOR_GRAY)
        y += 10
        pyxel.text(x, y, f"{self.score:>8d}", COLOR_WHITE)
        y += 16

        pyxel.text(x, y, "LEVEL", COLOR_GRAY)
        y += 10
        pyxel.text(x, y, f"{self.level:>8d}", COLOR_WHITE)
        y += 16

        pyxel.text(x, y, "LINES", COLOR_GRAY)
        y += 10
        pyxel.text(x, y, f"{self.lines:>8d}", COLOR_WHITE)
        y += 16

        combo_col = COLOR_PINK if self.combo >= SURGE_THRESHOLD else COLOR_YELLOW
        pyxel.text(x, y, "COMBO", COLOR_GRAY)
        y += 10
        pyxel.text(x, y, f"x{self.combo}", combo_col)
        y += 20

        if self.surge:
            if (pyxel.frame_count // 16) % 2 == 0:
                pyxel.text(x - 4, y, "SURGE!", COLOR_PINK)

    def _draw_next_piece(self, x: int, y: int) -> None:
        """Draw next piece preview in the HUD."""
        ptype = self.next_type
        shape = SHAPES[ptype][0]
        color = PIECE_COLORS[ptype]
        preview_cell = 8

        min_dx = min(dx for dx, _ in shape)
        max_dx = max(dx for dx, _ in shape)
        min_dy = min(dy for _, dy in shape)
        max_dy = max(dy for _, dy in shape)
        w = (max_dx - min_dx + 1) * preview_cell
        h = (max_dy - min_dy + 1) * preview_cell

        offset_x = x + (48 - w) // 2  # center in ~48px wide preview area
        offset_y = y + (32 - h) // 2

        for dx, dy in shape:
            px = offset_x + (dx - min_dx) * preview_cell
            py = offset_y + (dy - min_dy) * preview_cell
            pyxel.rect(px, py, preview_cell, preview_cell, color)
            pyxel.rectb(px, py, preview_cell, preview_cell, COLOR_BLACK)

    def _draw_game_over(self) -> None:
        cx = SCREEN_W // 2
        cy = SCREEN_H // 2

        pyxel.rect(cx - 80, cy - 50, 160, 100, COLOR_BLACK)
        pyxel.rectb(cx - 80, cy - 50, 160, 100, COLOR_WHITE)

        pyxel.text(cx - 30, cy - 40, "GAME OVER", COLOR_RED)
        pyxel.text(cx - 55, cy - 24, f"SCORE: {self.score}", COLOR_WHITE)
        pyxel.text(cx - 55, cy - 12, f"LINES: {self.lines}", COLOR_WHITE)
        pyxel.text(cx - 55, cy, f"MAX COMBO: {self.max_combo}", COLOR_YELLOW)
        pyxel.text(cx - 55, cy + 20, "PRESS ENTER TO RETRY", COLOR_WHITE)


# ── Entry point ────────────────────────────────────────────────────────

def main() -> None:
    Game()


if __name__ == "__main__":
    main()
