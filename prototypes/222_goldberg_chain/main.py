from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ---------------------------------------------------------------------------
# Color constants (pyxel raw ints)
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Game constants
# ---------------------------------------------------------------------------
SCREEN_W = 320
SCREEN_H = 240
CELL = 20
COLS = 10
ROWS = 8
GRID_X = 60
GRID_Y = 40

COLOR_NAMES: tuple[str, ...] = ("RED", "LIME", "DARK_BLUE", "YELLOW")
COLOR_VALS: tuple[int, ...] = (RED, LIME, DARK_BLUE, YELLOW)
NUM_COLORS = 4

MAX_PLACES = 3
SUPER_THRESHOLD = 5
SUPER_DURATION = 300
HEAT_CAP = 100.0
GAME_TIME = 3600
HEAT_MISMATCH = 15.0
HEAT_UNTRIGGERED = 5.0
HEAT_DECAY = 0.02
BFS_ANIM_SPEED = 6
MIN_CHAIN_SIZE = 2


# ---------------------------------------------------------------------------
# Phase enum
# ---------------------------------------------------------------------------
class Phase(Enum):
    TITLE = auto()
    BUILD = auto()
    REACT = auto()
    RESOLVE = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class Node:
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


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    phase: Phase
    grid: list[list[Node | None]]
    selected_color: int
    combo: int
    max_combo: int
    score: int
    heat: float
    timer: int
    turn: int
    places_remaining: int
    chain_queue: list[tuple[int, int]]
    chain_visited: set[tuple[int, int]]
    chain_anim_timer: int
    chain_color: int
    chain_order: list[tuple[int, int]]
    particles: list[Particle]
    floating_texts: list[FloatingText]
    super_mode: bool
    super_timer: int
    shake_frames: int
    resolve_score_gained: int
    resolve_nodes_triggered: int
    _rng: random.Random

    def __new__(cls) -> Game:
        instance = super().__new__(cls)
        instance.phase = Phase.TITLE
        instance.grid = [[None for _ in range(COLS)] for _ in range(ROWS)]
        instance.selected_color = 0
        instance.combo = 0
        instance.max_combo = 0
        instance.score = 0
        instance.heat = 0.0
        instance.timer = GAME_TIME
        instance.turn = 0
        instance.places_remaining = MAX_PLACES
        instance.chain_queue = []
        instance.chain_visited = set()
        instance.chain_anim_timer = 0
        instance.chain_color = -1
        instance.chain_order = []
        instance.particles = []
        instance.floating_texts = []
        instance.super_mode = False
        instance.super_timer = 0
        instance.shake_frames = 0
        instance.resolve_score_gained = 0
        instance.resolve_nodes_triggered = 0
        instance._rng = random.Random()
        return instance

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="GOLDBERG CHAIN", fps=60)
        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    # -----------------------------------------------------------------------
    # State initialization
    # -----------------------------------------------------------------------
    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.grid = [[None for _ in range(COLS)] for _ in range(ROWS)]
        self.selected_color = 0
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.heat = 0.0
        self.timer = GAME_TIME
        self.turn = 0
        self.places_remaining = MAX_PLACES
        self.chain_queue = []
        self.chain_visited = set()
        self.chain_anim_timer = 0
        self.chain_color = -1
        self.chain_order = []
        self.particles = []
        self.floating_texts = []
        self.super_mode = False
        self.super_timer = 0
        self.shake_frames = 0
        self.resolve_score_gained = 0
        self.resolve_nodes_triggered = 0

    def _start_game(self) -> None:
        self.reset()
        self.phase = Phase.BUILD
        self._spawn_nodes()

    # -----------------------------------------------------------------------
    # BFS chain algorithm
    # -----------------------------------------------------------------------
    def _bfs_chain(self, start_col: int, start_row: int, color: int) -> set[tuple[int, int]]:
        if self.grid[start_row][start_col] is None:
            return set()
        visited: set[tuple[int, int]] = set()
        queue: list[tuple[int, int]] = [(start_col, start_row)]
        while queue:
            c, r = queue.pop(0)
            if (c, r) in visited:
                continue
            visited.add((c, r))
            for dc, dr in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nc, nr = c + dc, r + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS:
                    node = self.grid[nr][nc]
                    if node is not None and node.color == color and (nc, nr) not in visited:
                        queue.append((nc, nr))
        return visited

    # -----------------------------------------------------------------------
    # Resolve chains
    # -----------------------------------------------------------------------
    def _resolve_chains(self) -> int:
        all_triggered: set[tuple[int, int]] = set()
        total_score = 0
        total_nodes_triggered = 0

        for r in range(ROWS):
            for c in range(COLS):
                if (c, r) not in all_triggered:
                    node = self.grid[r][c]
                    if node is None:
                        continue
                    cluster = self._bfs_chain(c, r, node.color)
                    if len(cluster) >= MIN_CHAIN_SIZE:
                        multiplier = self.combo + 1
                        if self.super_mode:
                            multiplier *= 3
                        chain_score = len(cluster) * multiplier * 10
                        total_score += chain_score
                        all_triggered.update(cluster)
                        total_nodes_triggered += len(cluster)

        for c, r in all_triggered:
            self.grid[r][c] = None

        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] is not None and (c, r) not in all_triggered:
                    self.heat += HEAT_UNTRIGGERED

        self.resolve_score_gained = total_score
        self.resolve_nodes_triggered = total_nodes_triggered
        return total_score

    # -----------------------------------------------------------------------
    # BFS animation preparation
    # -----------------------------------------------------------------------
    def _prepare_chain_animation(self) -> None:
        all_triggered: set[tuple[int, int]] = set()
        chain_order: list[tuple[int, int]] = []

        for r in range(ROWS):
            for c in range(COLS):
                if (c, r) not in all_triggered:
                    node = self.grid[r][c]
                    if node is None:
                        continue
                    cluster = self._bfs_chain(c, r, node.color)
                    if len(cluster) >= MIN_CHAIN_SIZE:
                        queue = [(c, r)]
                        visited_bfs: set[tuple[int, int]] = set()
                        while queue:
                            cc, cr = queue.pop(0)
                            if (cc, cr) in visited_bfs:
                                continue
                            visited_bfs.add((cc, cr))
                            chain_order.append((cc, cr))
                            for dc, dr in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                                nc, nr = cc + dc, cr + dr
                                if 0 <= nc < COLS and 0 <= nr < ROWS:
                                    n = self.grid[nr][nc]
                                    if n is not None and n.color == node.color and (nc, nr) not in visited_bfs:
                                        queue.append((nc, nr))
                        all_triggered.update(cluster)

        self.chain_order = chain_order
        self.chain_anim_timer = 0
        self.chain_visited = set()

    # -----------------------------------------------------------------------
    # Spawn new nodes
    # -----------------------------------------------------------------------
    def _spawn_nodes(self) -> None:
        count = min(2 + self.turn // 3, COLS * ROWS // 2)
        empty_cells = [(c, r) for r in range(ROWS) for c in range(COLS) if self.grid[r][c] is None]
        self._rng.shuffle(empty_cells)
        for i in range(min(count, len(empty_cells))):
            col, row = empty_cells[i]
            color = self._rng.randint(0, NUM_COLORS - 1)
            self.grid[row][col] = Node(col=col, row=row, color=color)

    # -----------------------------------------------------------------------
    # Utility
    # -----------------------------------------------------------------------
    def _mouse_to_grid(self) -> tuple[int, int] | None:
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        col = (mx - GRID_X) // CELL
        row = (my - GRID_Y) // CELL
        if 0 <= col < COLS and 0 <= row < ROWS:
            return (col, row)
        return None

    def _spawn_particles(self, col: int, row: int, color: int, count: int = 8) -> None:
        cx = GRID_X + col * CELL + CELL // 2
        cy = GRID_Y + row * CELL + CELL // 2
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(Particle(
                cx, cy,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                self._rng.randint(10, 20),
                color,
            ))

    def _update_heat(self) -> None:
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_particles(self) -> None:
        surviving: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                surviving.append(p)
        self.particles = surviving

    def _update_floating_texts(self) -> None:
        surviving: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= 1
            ft.life -= 1
            if ft.life > 0:
                surviving.append(ft)
        self.floating_texts = surviving

    def _rainbow_color(self, offset: int = 0) -> int:
        colors: list[int] = [RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, DARK_BLUE, PURPLE, PINK]
        return colors[(pyxel.frame_count // 4 + offset) % len(colors)]

    # -----------------------------------------------------------------------
    # Pyxel update
    # -----------------------------------------------------------------------
    def update(self) -> None:
        self._update_heat()
        self._update_particles()
        self._update_floating_texts()

        if self.shake_frames > 0:
            self.shake_frames -= 1

        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self._start_game()
            return

        if self.phase == Phase.GAME_OVER:
            if (
                pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.KEY_R)
            ):
                self._start_game()
            return

        if self.phase == Phase.BUILD:
            self._update_build()
        elif self.phase == Phase.REACT:
            self._update_react()
        elif self.phase == Phase.RESOLVE:
            self._update_resolve()

    def _update_build(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self.phase = Phase.GAME_OVER
            return

        if self.heat >= HEAT_CAP:
            self.heat = HEAT_CAP
            self.phase = Phase.GAME_OVER
            return

        # Color selection via keys
        if pyxel.btnp(pyxel.KEY_1):
            self._select_color(0)
        elif pyxel.btnp(pyxel.KEY_2):
            self._select_color(1)
        elif pyxel.btnp(pyxel.KEY_3):
            self._select_color(2)
        elif pyxel.btnp(pyxel.KEY_4):
            self._select_color(3)

        # Mouse click
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx = pyxel.mouse_x
            my = pyxel.mouse_y

            # Palette click
            if self._check_palette_click(mx, my):
                return

            # GO button click
            if self._check_go_button_click(mx, my):
                self._start_reaction()
                return

            # Grid click
            cell = self._mouse_to_grid()
            if cell is not None:
                self._place_node(cell[0], cell[1])

        # Trigger via keyboard
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self._start_reaction()

    def _select_color(self, color: int) -> None:
        if color == self.selected_color:
            return
        self.selected_color = color
        self.combo = 0
        self.heat += HEAT_MISMATCH

    def _check_palette_click(self, mx: int, my: int) -> bool:
        palette_x = GRID_X + COLS * CELL + 15
        for i in range(NUM_COLORS):
            py = 50 + i * 30
            if palette_x <= mx <= palette_x + 20 and py <= my <= py + 20:
                self._select_color(i)
                return True
        return False

    def _check_go_button_click(self, mx: int, my: int) -> bool:
        go_x = GRID_X + COLS * CELL + 5
        go_y = 190
        go_w = 50
        go_h = 20
        return go_x <= mx <= go_x + go_w and go_y <= my <= go_y + go_h

    def _place_node(self, col: int, row: int) -> None:
        if self.places_remaining <= 0:
            return
        if self.grid[row][col] is not None:
            return
        self.grid[row][col] = Node(col=col, row=row, color=self.selected_color)
        self.places_remaining -= 1

    def _start_reaction(self) -> None:
        self.phase = Phase.REACT
        self._prepare_chain_animation()

    def _update_react(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self.phase = Phase.GAME_OVER
            return

        self.chain_anim_timer += 1
        if self.chain_anim_timer >= BFS_ANIM_SPEED and self.chain_order:
            self.chain_anim_timer = 0
            idx = len(self.chain_visited)
            if idx < len(self.chain_order):
                cell = self.chain_order[idx]
                self.chain_visited.add(cell)
                node = self.grid[cell[1]][cell[0]]
                if node is not None:
                    self._spawn_particles(cell[0], cell[1], node.color)
            else:
                self.phase = Phase.RESOLVE

        # If no nodes to animate, skip to resolve
        if not self.chain_order:
            self.phase = Phase.RESOLVE

    def _update_resolve(self) -> None:
        score_gained = self._resolve_chains()
        self.score += score_gained

        if self.resolve_nodes_triggered >= 5:
            self.shake_frames = 15

        # Floating text for score
        if score_gained > 0:
            mid_x = GRID_X + COLS * CELL // 2
            mid_y = GRID_Y + ROWS * CELL // 2
            self.floating_texts.append(FloatingText(
                mid_x, mid_y,
                f"+{score_gained}",
                45, YELLOW,
            ))

        if self.heat >= HEAT_CAP:
            self.heat = HEAT_CAP
            self.phase = Phase.GAME_OVER
            return

        self.timer -= 1

        # Next turn
        self.turn += 1
        self._spawn_nodes()
        self.places_remaining = MAX_PLACES

        # COMBO logic: same color continues
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo

        # SUPER MODE check
        if self.combo >= SUPER_THRESHOLD and self.super_timer <= 0:
            self.super_mode = True
            self.super_timer = SUPER_DURATION

        self.chain_order = []
        self.chain_visited = set()
        self.phase = Phase.BUILD

    # -----------------------------------------------------------------------
    # Pyxel draw
    # -----------------------------------------------------------------------
    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        else:
            self._draw_game()

    def _draw_title(self) -> None:
        pyxel.cls(BLACK)
        pyxel.text(SCREEN_W // 2 - 44, 30, "GOLDBERG CHAIN", YELLOW)
        pyxel.text(SCREEN_W // 2 - 50, 48, "Build chain reactions!", WHITE)
        pyxel.text(SCREEN_W // 2 - 58, 68, "Click grid to place nodes", LIGHT_BLUE)
        pyxel.text(SCREEN_W // 2 - 78, 84, "1-4: select color | SPACE: trigger", GREEN)
        pyxel.text(SCREEN_W // 2 - 64, 100, "Same color chains = COMBO!", LIME)
        pyxel.text(SCREEN_W // 2 - 70, 116, "COMBO x5 = SUPER MODE (3x score)", ORANGE)
        pyxel.text(SCREEN_W // 2 - 56, 136, "Switch color = COMBO reset +HEAT", PINK)
        pyxel.text(SCREEN_W // 2 - 48, 152, "Untriggered nodes = +HEAT", GRAY)
        pyxel.text(SCREEN_W // 2 - 52, 168, "HEAT 100 or 60s = GAME OVER", RED)

        if pyxel.frame_count % 60 < 30:
            pyxel.text(SCREEN_W // 2 - 52, 200, "PRESS ENTER TO START", YELLOW)

    def _draw_game_over(self) -> None:
        pyxel.cls(NAVY)
        pyxel.text(SCREEN_W // 2 - 30, 55, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 44, 80, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 52, 95, f"MAX COMBO: {self.max_combo}", YELLOW)
        pyxel.text(SCREEN_W // 2 - 38, 110, f"TURNS: {self.turn}", LIME)
        cause = "HEAT" if self.heat >= HEAT_CAP else "TIME"
        pyxel.text(SCREEN_W // 2 - 50, 125, f"FAILED BY: {cause}", ORANGE)

        if pyxel.frame_count % 60 < 30:
            pyxel.text(SCREEN_W // 2 - 60, 200, "PRESS ENTER TO RETRY", YELLOW)

    def _draw_game(self) -> None:
        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0:
            shake_x = self._rng.randint(-4, 4)
            shake_y = self._rng.randint(-4, 4)

        pyxel.cls(BLACK)

        # Super mode border
        if self.super_mode:
            self._draw_super_border()

        # Grid area background
        pyxel.rect(GRID_X + shake_x, GRID_Y + shake_y, COLS * CELL, ROWS * CELL, NAVY)

        # Grid lines
        for r in range(ROWS + 1):
            py = GRID_Y + r * CELL + shake_y
            pyxel.line(GRID_X + shake_x, py, GRID_X + COLS * CELL + shake_x, py, GRAY)
        for c in range(COLS + 1):
            px = GRID_X + c * CELL + shake_x
            pyxel.line(px, GRID_Y + shake_y, px, GRID_Y + ROWS * CELL + shake_y, GRAY)

        # Cell hover highlight (BUILD only)
        if self.phase == Phase.BUILD:
            cell = self._mouse_to_grid()
            if cell is not None and self.grid[cell[1]][cell[0]] is None:
                cx = GRID_X + cell[0] * CELL + shake_x
                cy = GRID_Y + cell[1] * CELL + shake_y
                color = COLOR_VALS[self.selected_color]
                pyxel.rectb(cx, cy, CELL, CELL, color)

        # Nodes
        for r in range(ROWS):
            for c in range(COLS):
                node = self.grid[r][c]
                if node is None:
                    continue
                if self.phase == Phase.REACT and (c, r) not in self.chain_visited:
                    continue
                self._draw_node(c, r, node.color, shake_x, shake_y)

        # BFS animation chain visited
        if self.phase == Phase.REACT:
            for c, r in self.chain_visited:
                node = self.grid[r][c]
                if node is None:
                    continue
                self._draw_node(c, r, node.color, shake_x, shake_y, glow=True)

        # Particles
        for p in self.particles:
            if p.life > 0:
                px = int(p.x) + shake_x
                pY = int(p.y) + shake_y
                pyxel.rect(px, pY, 2, 2, p.color)

        # Floating texts
        for ft in self.floating_texts:
            if ft.life > 0:
                ftx = int(ft.x) + shake_x
                fty = int(ft.y) + shake_y
                pyxel.text(ftx, fty, ft.text, ft.color)

        # Right panel
        self._draw_panel()

        # HUD
        self._draw_hud()

    def _draw_node(self, col: int, row: int, color: int, shake_x: int, shake_y: int, glow: bool = False) -> None:
        cx = GRID_X + col * CELL + CELL // 2 + shake_x
        cy = GRID_Y + row * CELL + CELL // 2 + shake_y
        color_val = COLOR_VALS[color]
        if glow:
            pyxel.circ(cx, cy, 10, color_val)
        pyxel.circ(cx, cy, 8, WHITE)
        pyxel.circ(cx, cy, 6, color_val)
        pyxel.circ(cx, cy, 3, WHITE)

    def _draw_panel(self) -> None:
        px = GRID_X + COLS * CELL + 10
        palette_x = px + 5

        pyxel.text(px, 32, "COLOR", WHITE)

        # Color palette
        for i in range(NUM_COLORS):
            py = 50 + i * 30
            color = COLOR_VALS[i]
            pyxel.rect(palette_x, py, 20, 20, color)
            pyxel.rectb(palette_x, py, 20, 20, WHITE)

            if i == self.selected_color:
                pyxel.rectb(palette_x - 1, py - 1, 22, 22, WHITE)

            pyxel.text(palette_x + 25, py + 6, str(i + 1), WHITE)

        # GO button
        go_x = px
        go_y = 190
        pyxel.rect(go_x, go_y, 45, 18, LIME)
        pyxel.rectb(go_x, go_y, 45, 18, WHITE)
        pyxel.text(go_x + 14, go_y + 5, "GO!", BLACK)

        # Places remaining
        pyxel.text(px, 165, f"Left:{self.places_remaining}", WHITE)

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, 20, BLACK)

        pyxel.text(4, 4, f"SCORE:{self.score}", WHITE)
        pyxel.text(85, 4, f"COMBO:{self.combo}", YELLOW)

        # Super mode indicator
        if self.super_mode:
            sc = self._rainbow_color()
            pyxel.text(155, 4, "SUPER!", sc)

        # Heat bar
        hx = 200
        hy = 4
        hw = 50
        hh = 8
        pyxel.rect(hx, hy, hw, hh, GRAY)
        fill_w = int((self.heat / HEAT_CAP) * (hw - 2))
        hc = GREEN if self.heat < 50 else ORANGE if self.heat < 75 else RED
        if fill_w > 0:
            pyxel.rect(hx + 1, hy + 1, fill_w, hh - 2, hc)
        pyxel.rectb(hx, hy, hw, hh, WHITE)
        pyxel.text(hx - 10, 4, "H", RED)

        # Timer
        sec = max(0, self.timer // 60)
        ts = f"{sec}s"
        tc = LIME if sec > 20 else ORANGE if sec > 10 else RED
        pyxel.text(256, 4, ts, tc)

        # Turn
        pyxel.text(295, 4, f"T{self.turn}", WHITE)

        # Phase indicator
        pyxel.rect(0, SCREEN_H - 14, SCREEN_W, 14, BLACK)
        phase_text = str(self.phase.name).replace("_", " ")
        pyxel.text(4, SCREEN_H - 12, phase_text, LIGHT_BLUE)

    def _draw_super_border(self) -> None:
        colors: list[int] = [RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, DARK_BLUE, PURPLE, PINK]
        for i in range(4):
            idx = (pyxel.frame_count // 4 + i) % len(colors)
            pyxel.rectb(i, i, SCREEN_W - i * 2, SCREEN_H - i * 2, colors[idx])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    Game()
