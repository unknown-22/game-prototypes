from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import NamedTuple

import pyxel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WIDTH = 320
HEIGHT = 240
FPS = 30

GAME_DURATION = 1800  # 60s = 1800 frames
SUPER_DURATION = 300  # 10s = 300 frames
CELL_SIZE = 36
CELL_GAP = 2
GRID_COLS = 6
GRID_ROWS = 5
GRID_OFFSET_X = (WIDTH - GRID_COLS * (CELL_SIZE + CELL_GAP) + CELL_GAP) // 2  # 46
GRID_OFFSET_Y = 64

RESPAWN_DELAY_MIN = 30
RESPAWN_DELAY_MAX = 60

HEAT_MISMATCH = 15.0
HEAT_TIME_RATE = 0.03
HEAT_DECAY_RATE = 0.02
HEAT_CAP = 100.0

COMBO_THRESHOLD = 4
SUPER_MULT = 3.0
SCORE_BASE = 10
SCORE_CHAIN = 5

# Pyxel color palette (int constants)
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

ELEMENT_COLORS = (RED, LIME, DARK_BLUE, YELLOW)


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class XY(NamedTuple):
    x: int
    y: int


@dataclass
class PuzzleElement:
    col: int
    row: int
    color: int
    alive: bool = True
    respawn_timer: int = 0


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
    color: int
    life: int


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------


class Game:
    phase: Phase
    score: int
    best_score: int
    combo: int
    max_combo: int
    heat: float
    super_timer: int
    timer: int
    grid: list[list[PuzzleElement | None]]
    last_color: int | None
    particles: list[Particle]
    floating_texts: list[FloatingText]
    shake_frames: int
    _frame_count: int
    _rng: random.Random

    def __new__(cls) -> Game:
        obj = object.__new__(cls)
        obj.phase = Phase.TITLE
        obj.score = 0
        obj.best_score = 0
        obj.combo = 0
        obj.max_combo = 0
        obj.heat = 0.0
        obj.super_timer = 0
        obj.timer = 0
        obj.grid = []
        obj.last_color = None
        obj.particles = []
        obj.floating_texts = []
        obj.shake_frames = 0
        obj._frame_count = 0
        obj._rng = random.Random()
        return obj

    def __init__(self) -> None:
        pyxel.init(WIDTH, HEIGHT, "CHROMA ESCAPE", fps=FPS)
        pyxel.mouse(True)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_timer = 0
        self.timer = GAME_DURATION
        self.last_color = None
        self.particles.clear()
        self.floating_texts.clear()
        self.shake_frames = 0
        self._frame_count = 0
        self._init_grid()

    # ------------------------------------------------------------------
    # Grid
    # ------------------------------------------------------------------

    def _init_grid(self) -> None:
        self.grid = []
        for row in range(GRID_ROWS):
            row_data: list[PuzzleElement | None] = []
            for col in range(GRID_COLS):
                color = self._rng.choice(ELEMENT_COLORS)
                row_data.append(PuzzleElement(col=col, row=row, color=color))
            self.grid.append(row_data)

    def cell_xy(self, col: int, row: int) -> tuple[int, int]:
        x = GRID_OFFSET_X + col * (CELL_SIZE + CELL_GAP)
        y = GRID_OFFSET_Y + row * (CELL_SIZE + CELL_GAP)
        return x, y

    def grid_pos_from_screen(self, sx: int, sy: int) -> tuple[int, int] | None:
        if sx < GRID_OFFSET_X or sy < GRID_OFFSET_Y:
            return None
        col = (sx - GRID_OFFSET_X) // (CELL_SIZE + CELL_GAP)
        row = (sy - GRID_OFFSET_Y) // (CELL_SIZE + CELL_GAP)
        if col < 0 or col >= GRID_COLS or row < 0 or row >= GRID_ROWS:
            return None
        cell_x = GRID_OFFSET_X + col * (CELL_SIZE + CELL_GAP)
        cell_y = GRID_OFFSET_Y + row * (CELL_SIZE + CELL_GAP)
        if sx >= cell_x + CELL_SIZE or sy >= cell_y + CELL_SIZE:
            return None
        return col, row

    # ------------------------------------------------------------------
    # BFS Cluster
    # ------------------------------------------------------------------

    def _bfs_cluster(self, col: int, row: int, color: int) -> set[tuple[int, int]]:
        cluster: set[tuple[int, int]] = set()
        queue: list[tuple[int, int]] = [(col, row)]
        visited: set[tuple[int, int]] = set()

        while queue:
            c, r = queue.pop(0)
            if (c, r) in visited:
                continue
            visited.add((c, r))

            if c < 0 or c >= GRID_COLS or r < 0 or r >= GRID_ROWS:
                continue

            elem = self.grid[r][c]
            if elem is None or not elem.alive or elem.color != color:
                continue

            cluster.add((c, r))
            for dc, dr in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                nc, nr = c + dc, r + dr
                if (nc, nr) not in visited:
                    queue.append((nc, nr))

        return cluster

    # ------------------------------------------------------------------
    # Solve
    # ------------------------------------------------------------------

    def _solve_element(self, col: int, row: int) -> int:
        elem = self.grid[row][col]
        if elem is None or not elem.alive:
            return 0

        color = elem.color
        is_same = self.last_color is not None and color == self.last_color
        is_super = self.super_timer > 0

        if is_same or is_super or self.last_color is None:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            mult = SUPER_MULT if is_super else 1.0
            score_gained = int(SCORE_BASE * self.combo * mult)

            if self.combo >= COMBO_THRESHOLD and self.combo % COMBO_THRESHOLD == 0:
                self.super_timer = SUPER_DURATION
                self._add_floating_text(
                    float(GRID_OFFSET_X + GRID_COLS * (CELL_SIZE + CELL_GAP) // 2),
                    float(GRID_OFFSET_Y - 10),
                    "SUPER SOLVE!",
                    YELLOW,
                )
        else:
            self.combo = 0
            self.heat += HEAT_MISMATCH
            score_gained = SCORE_BASE
            self.shake_frames = 8
            self._add_floating_text(
                float(GRID_OFFSET_X + col * (CELL_SIZE + CELL_GAP) + CELL_SIZE // 2),
                float(GRID_OFFSET_Y + row * (CELL_SIZE + CELL_GAP)),
                "WRONG!",
                RED,
            )

        self.last_color = color
        self.score += score_gained

        # BFS cluster
        cluster = self._bfs_cluster(col, row, color)
        chain_count = len(cluster) - 1  # minus the clicked element
        if chain_count > 0:
            self.score += chain_count * SCORE_CHAIN
            score_gained += chain_count * SCORE_CHAIN

        # Mark solved, spawn respawn timers, spawn particles
        for c, r in cluster:
            e = self.grid[r][c]
            if e is not None:
                e.alive = False
                e.respawn_timer = self._rng.randint(RESPAWN_DELAY_MIN, RESPAWN_DELAY_MAX)
            cx, cy = self.cell_xy(c, r)
            px = float(cx + CELL_SIZE // 2)
            py = float(cy + CELL_SIZE // 2)
            count = 6 if (c == col and r == row) else 3
            self._spawn_particles(px, py, color, count)

        # Float text at clicked position
        cx, cy = self.cell_xy(col, row)
        if self.combo > 1:
            self._add_floating_text(
                float(cx + CELL_SIZE // 2),
                float(cy),
                f"COMBO x{self.combo}",
                YELLOW,
            )
        self._add_floating_text(
            float(cx + CELL_SIZE // 2),
            float(cy + CELL_SIZE // 2),
            f"+{score_gained}",
            WHITE,
        )

        # SUPER SOLVE special particles
        if self.super_timer > 0:
            px = float(GRID_OFFSET_X + GRID_COLS * (CELL_SIZE + CELL_GAP) // 2)
            py = float(GRID_OFFSET_Y + GRID_ROWS * (CELL_SIZE + CELL_GAP) // 2)
            for _ in range(8):
                c = self._rng.choice(ELEMENT_COLORS)
                self.particles.append(
                    Particle(
                        x=px,
                        y=py,
                        vx=self._rng.uniform(-2, 2),
                        vy=self._rng.uniform(-2, 2),
                        life=self._rng.randint(20, 35),
                        color=c,
                    )
                )

        return score_gained

    # ------------------------------------------------------------------
    # Update helpers
    # ------------------------------------------------------------------

    def _update_heat(self) -> None:
        self.heat += HEAT_TIME_RATE
        self.heat -= HEAT_DECAY_RATE
        if self.heat < 0:
            self.heat = 0.0
        if self.heat >= HEAT_CAP:
            self.heat = HEAT_CAP
            self.phase = Phase.GAME_OVER
            if self.score > self.best_score:
                self.best_score = self.score

    def _update_respawns(self) -> None:
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                elem = self.grid[row][col]
                if elem is None or elem.alive:
                    continue
                elem.respawn_timer -= 1
                if elem.respawn_timer <= 0:
                    elem.color = self._rng.choice(ELEMENT_COLORS)
                    elem.alive = True
                    elem.respawn_timer = 0

    def _update_particles(self) -> None:
        for p in self.particles:
            p.vy += 0.1  # gravity
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 1.0
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-1.5, 1.5),
                    vy=self._rng.uniform(-1.5, 1.5),
                    life=self._rng.randint(15, 25),
                    color=color,
                )
            )

    def _add_floating_text(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, color=color, life=40)
        )

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self) -> None:
        if self.phase is Phase.TITLE:
            self._update_title()
            return

        if self.phase is Phase.PLAYING:
            self._frame_count += 1
            self._update_playing()
            return

        if self.phase is Phase.GAME_OVER:
            self._update_game_over()
            return

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.phase = Phase.PLAYING
            self.score = 0
            self.combo = 0
            self.max_combo = 0
            self.heat = 0.0
            self.super_timer = 0
            self.timer = GAME_DURATION
            self.last_color = None
            self.particles.clear()
            self.floating_texts.clear()
            self.shake_frames = 0
            self._frame_count = 0
            self._init_grid()

    def _update_playing(self) -> None:
        if self.shake_frames > 0:
            self.shake_frames -= 1
            pyxel.camera(
                self._rng.randint(-4, 4) if self.shake_frames > 0 else 0,
                self._rng.randint(-4, 4) if self.shake_frames > 0 else 0,
            )
            if self.shake_frames == 0:
                pyxel.camera(0, 0)

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
        if self.phase is Phase.GAME_OVER:
            return

        self._update_respawns()
        self._update_particles()
        self._update_floating_texts()

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            pos = self.grid_pos_from_screen(pyxel.mouse_x, pyxel.mouse_y)
            if pos is not None:
                col, row = pos
                self._solve_element(col, row)

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.phase = Phase.TITLE

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase is Phase.TITLE:
            self._draw_title()
            return

        if self.phase is Phase.GAME_OVER:
            self._draw_game_over()
            return

        self._draw_playing()

    def _draw_title(self) -> None:
        pyxel.cls(NAVY)
        x = WIDTH // 2
        pyxel.text(x - 52, 40, "CHROMA ESCAPE", YELLOW)
        pyxel.text(x - 60, 60, "Color-Match Puzzle Room", WHITE)

        pyxel.text(x - 72, 90, "Same-color clicks = COMBO!", LIME)
        pyxel.text(x - 68, 104, "Adjacent same-colors chain!", CYAN)
        pyxel.text(x - 76, 118, "COMBO x4 = SUPER SOLVE (3x score!)", YELLOW)
        pyxel.text(x - 60, 132, f"Wrong click = HEAT +{int(HEAT_MISMATCH)}", RED)
        pyxel.text(x - 54, 146, "HEAT at 100 = MELTDOWN!", ORANGE)
        pyxel.text(x - 74, 160, "Solve for 60s = escape!", WHITE)

        if self.best_score > 0:
            pyxel.text(x - 40, 180, f"BEST: {self.best_score}", PINK)

        pyxel.text(x - 52, 210, "CLICK TO START", WHITE)

    def _draw_playing(self) -> None:
        # HUD
        pyxel.rect(0, 0, WIDTH, 36, NAVY)
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)
        pyxel.text(4, 16, f"COMBO: x{self.combo}", WHITE)
        pyxel.text(120, 4, f"MAX COMBO: x{self.max_combo}", PINK)

        secs = max(0, self.timer // FPS)
        timer_color = RED if secs <= 10 else WHITE
        pyxel.text(260, 4, f"{secs}s", timer_color)

        if self.super_timer > 0:
            s = self.super_timer / FPS
            pyxel.text(120, 16, f"SUPER {s:.1f}s", YELLOW)

        # Heat bar (bottom)
        bar_x = 20
        bar_y = 220
        bar_w = 280
        bar_h = 12
        pyxel.rectb(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2, WHITE)
        heat_ratio = self.heat / HEAT_CAP
        fill = int(bar_w * heat_ratio)
        if heat_ratio < 0.4:
            hcolor = GREEN
        elif heat_ratio < 0.75:
            hcolor = YELLOW
        else:
            hcolor = RED
        if fill > 0:
            pyxel.rect(bar_x, bar_y, fill, bar_h, hcolor)
        pyxel.text(bar_x + bar_w // 2 - 8, bar_y + 2, f"HEAT {int(self.heat)}%", WHITE)

        # Grid
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                elem = self.grid[row][col]
                x, y = self.cell_xy(col, row)

                if elem is not None and elem.alive:
                    # Draw element
                    pyxel.rect(x, y, CELL_SIZE, CELL_SIZE, elem.color)

                    # Border (darker = color - 1 or dark color)
                    border = elem.color - 1 if elem.color > 0 else GRAY
                    pyxel.rectb(x, y, CELL_SIZE, CELL_SIZE, border)

                    # SUPER SOLVE rainbow border
                    if self.super_timer > 0:
                        r_color = ELEMENT_COLORS[self._frame_count // 6 % len(ELEMENT_COLORS)]
                        pyxel.rectb(x - 1, y - 1, CELL_SIZE + 2, CELL_SIZE + 2, r_color)

                    # Icon in center
                    self._draw_element_icon(x, y, elem.color)
                elif elem is not None and not elem.alive:
                    # Fading solved element
                    fade = elem.respawn_timer * 15 // RESPAWN_DELAY_MAX
                    fade_color = GRAY if fade > 5 else BLACK
                    pyxel.rect(x, y, CELL_SIZE, CELL_SIZE, fade_color)

        # Particles
        for p in self.particles:
            pyxel.circ(int(p.x), int(p.y), 2, p.color)

        # Floating texts
        for ft in self.floating_texts:
            alpha = ft.life / 40.0
            c = ft.color
            if alpha < 0.3:
                c = GRAY
            elif alpha < 0.6:
                pass  # keep original color
            x_pos = int(ft.x - len(ft.text) * 2)
            pyxel.text(x_pos, int(ft.y), ft.text, c)

        # Mouse cursor
        pyxel.circ(pyxel.mouse_x, pyxel.mouse_y, 3, WHITE)
        pyxel.circb(pyxel.mouse_x, pyxel.mouse_y, 4, BLACK)

    def _draw_element_icon(self, x: int, y: int, color: int) -> None:
        cx = x + CELL_SIZE // 2
        cy = y + CELL_SIZE // 2
        dark = max(color - 2, 0)

        if color == RED:  # key
            pyxel.rect(cx - 1, cy - 4, 2, 10, dark)
            pyxel.rect(cx - 1, cy - 4, 6, 2, dark)
            pyxel.rect(cx - 1, cy + 4, 6, 2, dark)
        elif color == LIME:  # switch
            pyxel.rect(cx - 5, cy - 5, 10, 10, dark)
            pyxel.rect(cx - 1, cy - 5, 2, 10, color)
        elif color == DARK_BLUE:  # lock
            pyxel.rectb(cx - 4, cy - 4, 8, 8, dark)
            pyxel.rect(cx - 1, cy - 1, 2, 3, dark)
        elif color == YELLOW:  # wire
            pyxel.rect(cx - 5, cy - 1, 10, 2, dark)
            pyxel.rect(cx - 1, cy - 3, 2, 6, dark)

    def _draw_game_over(self) -> None:
        pyxel.cls(NAVY)
        x = WIDTH // 2

        if self.heat >= HEAT_CAP:
            pyxel.text(x - 36, 60, "MELTDOWN!", RED)
        elif self.timer <= 0:
            pyxel.text(x - 48, 60, "TIME'S UP!", YELLOW)
        else:
            pyxel.text(x - 52, 60, "ESCAPE FAILED!", ORANGE)

        pyxel.text(x - 40, 90, f"SCORE: {self.score}", WHITE)
        pyxel.text(x - 44, 110, f"MAX COMBO: x{self.max_combo}", PINK)

        if self.score >= self.best_score and self.best_score > 0:
            pyxel.text(x - 46, 130, "NEW BEST!", YELLOW)
        pyxel.text(x - 40, 150, f"BEST: {self.best_score}", WHITE)

        pyxel.text(x - 52, 200, "CLICK TO RETRY", WHITE)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    Game()
