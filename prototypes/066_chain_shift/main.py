import pyxel
import math
import random
from dataclasses import dataclass
from enum import Enum, auto

SCREEN_W = 320
SCREEN_H = 240
GRID_COLS = 5
GRID_ROWS = 5
CELL_SIZE = 48
GRID_X = 40
GRID_Y = 0

COLOR_RED = 8
COLOR_GREEN = 3
COLOR_LIGHT_BLUE = 6
COLOR_YELLOW = 10
COLORS: tuple[int, ...] = (COLOR_RED, COLOR_GREEN, COLOR_LIGHT_BLUE, COLOR_YELLOW)

INITIAL_MOVES = 40
BONUS_MOVE_THRESHOLD = 5
BONUS_MOVES = 2
TARGET_SCORE = 2000
BASE_POINTS_PER_TILE = 10

ANIM_CHAIN_DURATION = 20


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    ANIM_CHAIN = auto()
    GAME_OVER = auto()


@dataclass
class Tile:
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
class FloatText:
    x: float
    y: float
    text: str
    life: int
    color: int


class Game:
    def __init__(self) -> None:
        self._rng = random.Random()
        self.grid: list[list[Tile | None]] = []
        self.empty_col: int = 0
        self.empty_row: int = 0
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.moves_left: int = INITIAL_MOVES
        self.particles: list[Particle] = []
        self.floats: list[FloatText] = []
        self.target_score: int = TARGET_SCORE
        self.phase: Phase = Phase.TITLE
        self.anim_timer: int = 0
        self.won: bool = False
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.moves_left = INITIAL_MOVES
        self.particles.clear()
        self.floats.clear()
        self.anim_timer = 0
        self.won = False
        self.phase = Phase.TITLE
        self._init_grid()

    def _init_grid(self) -> None:
        self.grid = [
            [Tile(self._rng.choice(COLORS)) for _ in range(GRID_COLS)]
            for _ in range(GRID_ROWS)
        ]
        self.empty_col = self._rng.randrange(GRID_COLS)
        self.empty_row = self._rng.randrange(GRID_ROWS)
        self.grid[self.empty_row][self.empty_col] = None

    # ── BFS / Chain Logic ──

    def _bfs_adjacent(self, sx: int, sy: int, color: int) -> set[tuple[int, int]]:
        start_tile = self.grid[sy][sx]
        if start_tile is None or start_tile.color != color:
            return set()
        visited: set[tuple[int, int]] = set()
        queue: list[tuple[int, int]] = [(sx, sy)]
        visited.add((sx, sy))
        while queue:
            cx, cy = queue.pop(0)
            for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                if 0 <= nx < GRID_COLS and 0 <= ny < GRID_ROWS:
                    if (nx, ny) not in visited:
                        tile = self.grid[ny][nx]
                        if tile is not None and tile.color == color:
                            visited.add((nx, ny))
                            queue.append((nx, ny))
        return visited

    def _find_all_chains(self) -> list[set[tuple[int, int]]]:
        visited: set[tuple[int, int]] = set()
        chains: list[set[tuple[int, int]]] = []
        for y in range(GRID_ROWS):
            for x in range(GRID_COLS):
                if (x, y) in visited:
                    continue
                tile = self.grid[y][x]
                if tile is None:
                    continue
                group = self._bfs_adjacent(x, y, tile.color)
                visited.update(group)
                if len(group) >= 3:
                    chains.append(group)
        return chains

    def _clear_chains(self, chains: list[set[tuple[int, int]]]) -> int:
        total_cleared = 0
        for chain in chains:
            for cx, cy in chain:
                tile = self.grid[cy][cx]
                if tile is not None:
                    total_cleared += 1
                    self._spawn_particles(cx, cy, tile.color)
                    self.grid[cy][cx] = None
            if len(chain) >= BONUS_MOVE_THRESHOLD:
                self.moves_left += BONUS_MOVES
                gx = GRID_X + min(x for x, _ in chain) * CELL_SIZE + CELL_SIZE // 2
                gy = GRID_Y + min(y for _, y in chain) * CELL_SIZE + CELL_SIZE // 2
                self._spawn_float_text(gx, gy, f"+{BONUS_MOVES}MOVES", COLOR_YELLOW)
        return total_cleared

    def _fill_empty(self) -> None:
        for y in range(GRID_ROWS):
            for x in range(GRID_COLS):
                if self.grid[y][x] is None and not (x == self.empty_col and y == self.empty_row):
                    self.grid[y][x] = Tile(self._rng.choice(COLORS))

    def _check_and_cascade(self) -> int:
        cascade_count = 0
        self.combo = 0
        while True:
            chains = self._find_all_chains()
            if not chains:
                break
            cascade_count += 1
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            tiles_cleared = self._clear_chains(chains)
            multiplier = self.combo
            self.score += tiles_cleared * BASE_POINTS_PER_TILE * multiplier
            self._fill_empty()
        return cascade_count

    def _adjacent_to_empty(self, col: int, row: int) -> bool:
        return (
            (col == self.empty_col and abs(row - self.empty_row) == 1)
            or (row == self.empty_row and abs(col - self.empty_col) == 1)
        )

    def _slide(self, col: int, row: int) -> bool:
        if not self._adjacent_to_empty(col, row):
            return False
        self.grid[self.empty_row][self.empty_col] = self.grid[row][col]
        self.grid[row][col] = None
        self.empty_col, self.empty_row = col, row
        return True

    def _is_game_over(self) -> bool:
        return self.moves_left <= 0

    # ── Effects ──

    def _spawn_particles(self, col: int, row: int, color: int) -> None:
        cx = GRID_X + col * CELL_SIZE + CELL_SIZE // 2
        cy = GRID_Y + row * CELL_SIZE + CELL_SIZE // 2
        for _ in range(6):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.5)
            self.particles.append(Particle(
                x=float(cx), y=float(cy),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 1.0,
                life=self._rng.randint(10, 25),
                color=color,
            ))

    def _spawn_float_text(self, x: int, y: int, text: str, color: int) -> None:
        self.floats.append(FloatText(
            x=float(x), y=float(y), text=text, life=25, color=color,
        ))

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floats(self) -> None:
        for ft in self.floats[:]:
            ft.y -= 0.6
            ft.life -= 1
            if ft.life <= 0:
                self.floats.remove(ft)

    # ── Update ──

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.ANIM_CHAIN:
            self._update_anim_chain()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._start_game()

    def _start_game(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.moves_left = INITIAL_MOVES
        self.particles.clear()
        self.floats.clear()
        self.anim_timer = 0
        self.won = False
        self._init_grid()
        self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            col = (mx - GRID_X) // CELL_SIZE
            row = my // CELL_SIZE
            if 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS:
                if self._slide(col, row):
                    self.moves_left -= 1
                    cascades = self._check_and_cascade()
                    if cascades > 0:
                        self.phase = Phase.ANIM_CHAIN
                        self.anim_timer = ANIM_CHAIN_DURATION
                        gx = GRID_X + GRID_COLS * CELL_SIZE // 2
                        gy = GRID_Y + GRID_ROWS * CELL_SIZE // 2
                        self._spawn_float_text(
                            gx, gy, f"x{self.combo} COMBO!", COLOR_YELLOW,
                        )
        if self.score >= TARGET_SCORE:
            self.won = True
            self.phase = Phase.GAME_OVER
        elif self._is_game_over():
            self.phase = Phase.GAME_OVER

    def _update_anim_chain(self) -> None:
        self._update_particles()
        self._update_floats()
        self.anim_timer -= 1
        if self.anim_timer <= 0:
            if self.score >= TARGET_SCORE:
                self.won = True
                self.phase = Phase.GAME_OVER
            elif self._is_game_over():
                self.phase = Phase.GAME_OVER
            else:
                self.phase = Phase.PLAYING

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()

    # ── Draw ──

    def draw(self) -> None:
        pyxel.cls(0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        else:
            self._draw_grid()
            self._draw_ui()
            self._draw_particles()
            self._draw_floats()

            if self.phase == Phase.GAME_OVER:
                self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(110, 40, "CHAIN SHIFT", COLOR_YELLOW)
        pyxel.text(60, 70, "Color-Match Sliding Puzzle", 7)
        pyxel.text(80, 110, "CLICK to START", COLOR_LIGHT_BLUE)
        pyxel.text(45, 145, "Click tiles next to empty cell", 7)
        pyxel.text(45, 157, "to slide. 3+ same-color chain!", 7)
        pyxel.text(45, 175, "Big chains (5+) = bonus moves", 7)
        pyxel.text(45, 187, "Cascades = combo multiplier", 7)
        pyxel.text(45, 205, "Target: 2000 points in 40 moves", 7)
        for i, c in enumerate(COLORS):
            cx = 120 + i * 24
            pyxel.rect(cx, 225, 14, 10, c)

    def _draw_grid(self) -> None:
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                x = GRID_X + col * CELL_SIZE
                y = GRID_Y + row * CELL_SIZE
                tile = self.grid[row][col]
                if tile is not None:
                    pyxel.rect(x + 1, y + 1, CELL_SIZE - 2, CELL_SIZE - 2, tile.color)
                    pyxel.rectb(x, y, CELL_SIZE, CELL_SIZE, 7)
                elif col == self.empty_col and row == self.empty_row:
                    pyxel.rectb(x, y, CELL_SIZE, CELL_SIZE, 7)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 25.0
            if alpha > 0.3:
                pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floats(self) -> None:
        for ft in self.floats:
            alpha = ft.life / 25.0
            if alpha > 0.15:
                tw = len(ft.text) * 4
                pyxel.text(int(ft.x - tw), int(ft.y), ft.text, ft.color)

    def _draw_ui(self) -> None:
        pyxel.text(2, 2, f"Score: {self.score}", 7)
        pyxel.text(2, 12, f"Moves: {self.moves_left}", 7)
        pyxel.text(2, 22, f"Combo: {self.combo}", COLOR_YELLOW)
        pyxel.text(2, 32, f"Target: {TARGET_SCORE}", 7)
        if self.max_combo > 0:
            pyxel.text(2, 42, f"MaxCmbo: {self.max_combo}", 5)

    def _draw_game_over(self) -> None:
        for y in range(0, SCREEN_H, 2):
            for x in range(0, SCREEN_W, 2):
                if (x // 2 + y // 2) % 2 == 0:
                    pyxel.pset(x, y, 0)

        if self.won:
            pyxel.text(110, 50, "YOU WIN!", COLOR_YELLOW)
            pyxel.text(75, 70, "Target score reached!", 7)
        else:
            pyxel.text(100, 50, "GAME OVER", COLOR_RED)
            pyxel.text(75, 70, "Out of moves!", 7)

        pyxel.text(68, 95, f"FINAL SCORE: {self.score}", 7)
        pyxel.text(68, 110, f"MAX COMBO: {self.max_combo}", COLOR_YELLOW)
        pyxel.text(72, 140, "Press R or CLICK to Retry", COLOR_LIGHT_BLUE)


class App:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Chain Shift", display_scale=2)
        self.game = Game()
        pyxel.run(self.game.update, self.game.draw)


if __name__ == "__main__":
    App()
