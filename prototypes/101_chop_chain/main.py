"""
Chop Chain — Karate Board Breaking Arcade Game

COLORED BOARDS STACK IN 4 COLUMNS. MATCH SAME COLOR CONSECUTIVE BREAKS
TO BUILD COMBO. COMBO >= 5 TRIGGERS SUPER CHOP (5s, 3x SCORE, NO PENALTY).
WRONG COLOR OR MISS = HEAT. HEAT >= 10 OR COLUMN OVERFLOW = GAME OVER.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ──────────────────────────────────────────────────────────────

WIDTH = 320
HEIGHT = 240
FPS = 60
DISPLAY_SCALE = 2

# Raw color ints
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

BOARD_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
NUM_COLUMNS = 4
COLUMN_WIDTH = 52
COLUMN_GAP = 20

_TOTAL_COLS = NUM_COLUMNS * COLUMN_WIDTH + (NUM_COLUMNS - 1) * COLUMN_GAP
_SIDE_PAD = (WIDTH - _TOTAL_COLS) // 2

COLUMN_LEFT_X: list[int] = [
    _SIDE_PAD + i * (COLUMN_WIDTH + COLUMN_GAP) for i in range(NUM_COLUMNS)
]
COLUMN_CENTER_X: list[int] = [lx + COLUMN_WIDTH // 2 for lx in COLUMN_LEFT_X]

BOARD_HEIGHT = 14
BOARD_STACK_STEP = BOARD_HEIGHT + 2  # 16px

HEAT_BAR_HEIGHT = 8
COLUMN_TOP_Y = HEAT_BAR_HEIGHT + 10
COLUMN_BOTTOM_Y = 220

AVAILABLE_SPACE = COLUMN_BOTTOM_Y - COLUMN_TOP_Y
# Board at index 0: bottom at COLUMN_BOTTOM_Y, top at COLUMN_BOTTOM_Y - 14
# Board at index n: bottom at COLUMN_BOTTOM_Y - n*16
# For n boards to fit: n*14 + (n-1)*2 <= AVAILABLE_SPACE
# n*16 - 2 <= AVAILABLE_SPACE  →  n <= (AVAILABLE_SPACE + 2) / 16
MAX_BOARDS_PER_COLUMN = (AVAILABLE_SPACE + 2) // BOARD_STACK_STEP

BOARD_SCORE = 10
SUPER_SCORE_MULTIPLIER = 3
SUPER_DURATION = 300  # 5 seconds * 60 fps
MAX_HEAT = 10
HEAT_WRONG_COLOR = 2
HEAT_EMPTY_CHOP = 3
HEAT_DECAY_INTERVAL = 120
INITIAL_SPAWN_INTERVAL = 90
MIN_SPAWN_INTERVAL = 25
SPAWN_DECREASE_INTERVAL = 300
SPAWN_DECREASE_AMOUNT = 3
SUPER_COMBO_THRESHOLD = 5
PARTICLES_PER_CHOP_MIN = 6
PARTICLES_PER_CHOP_MAX = 12
PARTICLE_LIFE_MIN = 15
PARTICLE_LIFE_MAX = 30
PARTICLE_GRAVITY = 0.1
FLOAT_LIFE_MIN = 30
FLOAT_LIFE_MAX = 45
FLOAT_VY = -1.0
COMBO_FLOAT_THRESHOLD = 3
SHAKE_DURATION = 8
SHAKE_POWER = 2
EMPTY_CHOP_PARTICLES = 4


# ── Data Classes ───────────────────────────────────────────────────────────

class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Board:
    color: int
    hp: int = 1


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


# ── Game Class ─────────────────────────────────────────────────────────────

class Game:
    """Core game logic. Testable without pyxel input.

    Use ``Game.__new__(Game)`` for headless testing — avoids pyxel.init panic.
    Pre-init ALL attributes before calling reset().
    """

    def __init__(self) -> None:
        self._init_state()
        self.reset()

    def __new__(cls) -> Game:
        obj = super().__new__(cls)
        # Pre-init EVERYTHING so headless tests can skip __init__
        obj.phase = Phase.TITLE
        obj.columns: list[list[Board]] = [[], [], [], []]
        obj.cursor_col = 0
        obj.score = 0
        obj.combo = 0
        obj.max_combo = 0
        obj.heat = 0
        obj.super_mode = False
        obj.super_timer = 0
        obj.spawn_timer = INITIAL_SPAWN_INTERVAL
        obj.spawn_interval = INITIAL_SPAWN_INTERVAL
        obj.heat_decay_timer = HEAT_DECAY_INTERVAL
        obj.last_broken_color: int = -1
        obj.particles: list[Particle] = []
        obj.floating_texts: list[FloatingText] = []
        obj.flash_timer = 0
        obj._rng: random.Random = random.Random()
        obj.game_timer = 0
        obj.shake_timer = 0
        obj.difficulty_timer = 0
        return obj

    def _init_state(self) -> None:
        self.phase = Phase.TITLE
        self.columns = [[], [], [], []]
        self.cursor_col = 0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0
        self.super_mode = False
        self.super_timer = 0
        self.spawn_timer = INITIAL_SPAWN_INTERVAL
        self.spawn_interval = INITIAL_SPAWN_INTERVAL
        self.heat_decay_timer = HEAT_DECAY_INTERVAL
        self.last_broken_color = -1
        self.particles = []
        self.floating_texts = []
        self.flash_timer = 0
        self._rng = random.Random()
        self.game_timer = 0
        self.shake_timer = 0
        self.difficulty_timer = 0

    def reset(self) -> None:
        """Reset to initial state for a new game."""
        self.columns = [[], [], [], []]
        self.cursor_col = 0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0
        self.super_mode = False
        self.super_timer = 0
        self.spawn_timer = INITIAL_SPAWN_INTERVAL
        self.spawn_interval = INITIAL_SPAWN_INTERVAL
        self.heat_decay_timer = HEAT_DECAY_INTERVAL
        self.last_broken_color = -1
        self.particles.clear()
        self.floating_texts.clear()
        self.flash_timer = 0
        self.game_timer = 0
        self.shake_timer = 0
        self.difficulty_timer = 0

    # ── Helpers ────────────────────────────────────────────────────────

    def _board_bottom_y(self, col_idx: int, board_idx: int) -> float:
        """Y coordinate of the BOTTOM edge of a board (0 = bottommost)."""
        return float(COLUMN_BOTTOM_Y - board_idx * BOARD_STACK_STEP)

    def _board_center_y(self, col_idx: int, board_idx: int) -> float:
        """Y coordinate of the center of a board."""
        return self._board_bottom_y(col_idx, board_idx) - BOARD_HEIGHT / 2

    # ── Core Mechanics ─────────────────────────────────────────────────

    def _score_for_break(self, board: Board, combo: int) -> int:
        """Pure: compute score for breaking a board at given combo level."""
        score = BOARD_SCORE * combo
        if self.super_mode:
            score *= SUPER_SCORE_MULTIPLIER
        return score

    def _chop(self, col_idx: int) -> int:
        """Break top board in column. Returns score earned.

        Updates combo, heat, last_broken_color. Spawns particles and
        floating texts. Activates SUPER mode at combo threshold.
        """
        if col_idx < 0 or col_idx >= NUM_COLUMNS:
            return 0

        column = self.columns[col_idx]

        # Empty column — miss penalty
        if not column:
            self.heat += HEAT_EMPTY_CHOP
            self.combo = 0
            self.last_broken_color = -1
            self._spawn_empty_chop_fx(col_idx)
            self.shake_timer = SHAKE_DURATION
            return 0

        board = column.pop()

        is_match = (
            self.last_broken_color == -1
            or board.color == self.last_broken_color
            or self.super_mode
        )

        if is_match:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
        else:
            self.heat += HEAT_WRONG_COLOR
            self.combo = 0

        if self.combo >= SUPER_COMBO_THRESHOLD and not self.super_mode:
            self.super_mode = True
            self.super_timer = SUPER_DURATION

        self.last_broken_color = board.color

        effective_combo = self.combo if is_match else 1
        earned = self._score_for_break(board, effective_combo)
        self.score += earned

        # FX
        center_y = self._board_center_y(col_idx, len(column))
        self._spawn_particles(float(COLUMN_CENTER_X[col_idx]), center_y, board.color)
        self._spawn_floating_score(float(COLUMN_CENTER_X[col_idx]), center_y, earned, board.color)
        if self.combo >= COMBO_FLOAT_THRESHOLD and is_match:
            self._spawn_combo_text(float(COLUMN_CENTER_X[col_idx]), center_y - 10)

        self.shake_timer = SHAKE_DURATION
        self.flash_timer = 4

        return earned

    def _spawn_board(self) -> None:
        col_idx = self._rng.randint(0, NUM_COLUMNS - 1)
        color = self._rng.choice(BOARD_COLORS)
        self.columns[col_idx].append(Board(color=color))

    def _update_spawn(self, dt: int) -> None:
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_timer += self.spawn_interval
            self._spawn_board()

    def _update_heat_decay(self, dt: int) -> None:
        if self.heat == 0:
            self.heat_decay_timer = HEAT_DECAY_INTERVAL
            return
        self.heat_decay_timer -= dt
        while self.heat_decay_timer <= 0:
            self.heat_decay_timer += HEAT_DECAY_INTERVAL
            self.heat = max(0, self.heat - 1)

    def _update_super_timer(self, dt: int) -> None:
        if not self.super_mode:
            return
        self.super_timer -= dt
        if self.super_timer <= 0:
            self.super_mode = False
            self.super_timer = 0

    def _update_difficulty(self, dt: int) -> None:
        self.difficulty_timer += dt
        while self.difficulty_timer >= SPAWN_DECREASE_INTERVAL:
            self.difficulty_timer -= SPAWN_DECREASE_INTERVAL
            self.spawn_interval = max(
                MIN_SPAWN_INTERVAL,
                self.spawn_interval - SPAWN_DECREASE_AMOUNT,
            )

    def _check_game_over(self) -> bool:
        if self.heat >= MAX_HEAT:
            return True
        for col in self.columns:
            if len(col) > MAX_BOARDS_PER_COLUMN:
                return True
        return False

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += PARTICLE_GRAVITY
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def _update_floating_texts(self) -> None:
        alive: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y += FLOAT_VY
            ft.life -= 1
            if ft.life > 0:
                alive.append(ft)
        self.floating_texts = alive

    def update(self, dt: int) -> None:
        """Tick game logic (1 frame). Does NOT read pyxel input."""
        if self.phase != Phase.PLAYING:
            return

        self.game_timer += dt

        self._update_difficulty(dt)
        self._update_spawn(dt)
        self._update_heat_decay(dt)
        self._update_super_timer(dt)
        self._update_particles()
        self._update_floating_texts()

        if self.heat > MAX_HEAT:
            self.heat = MAX_HEAT

        if self.flash_timer > 0:
            self.flash_timer -= dt
        if self.shake_timer > 0:
            self.shake_timer -= dt

        if self._check_game_over():
            self.phase = Phase.GAME_OVER

    # ── FX Spawners ────────────────────────────────────────────────────

    def _spawn_particles(self, x: float, y: float, color: int) -> None:
        count = self._rng.randint(PARTICLES_PER_CHOP_MIN, PARTICLES_PER_CHOP_MAX)
        for _ in range(count):
            vx = self._rng.uniform(-2.0, 2.0)
            vy = self._rng.uniform(-3.0, -1.0)
            life = self._rng.randint(PARTICLE_LIFE_MIN, PARTICLE_LIFE_MAX)
            self.particles.append(Particle(x, y, vx, vy, life, color))

    def _spawn_empty_chop_fx(self, col_idx: int) -> None:
        cx = float(COLUMN_CENTER_X[col_idx])
        cy = float(COLUMN_TOP_Y + 30)
        for _ in range(EMPTY_CHOP_PARTICLES):
            vx = self._rng.uniform(-1.0, 1.0)
            vy = self._rng.uniform(-2.0, -0.5)
            self.particles.append(Particle(cx, cy, vx, vy, 15, GRAY))

    def _spawn_floating_score(self, x: float, y: float, score: int, color: int) -> None:
        life = self._rng.randint(FLOAT_LIFE_MIN, FLOAT_LIFE_MAX)
        self.floating_texts.append(
            FloatingText(x, y - 6, f"+{score}", life, color)
        )

    def _spawn_combo_text(self, x: float, y: float) -> None:
        life = self._rng.randint(FLOAT_LIFE_MIN, FLOAT_LIFE_MAX)
        self.floating_texts.append(
            FloatingText(x, y, f"COMBO x{self.combo}", life, YELLOW)
        )

    # ── Rendering ─────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        title_y = 50
        pyxel.text(118, title_y, "CHOP CHAIN", WHITE)
        pyxel.text(87, title_y + 20, "KARATE BOARD BREAKER", GRAY)

        info_start = title_y + 50
        pyxel.text(70, info_start, "Match colors for COMBO!", CYAN)
        pyxel.text(90, info_start + 18, "LEFT/RIGHT : Select column", GRAY)
        pyxel.text(98, info_start + 30, "SPACE      : Chop!", GRAY)
        pyxel.text(63, info_start + 50, "COMBO x5   : SUPER CHOP!", YELLOW)
        pyxel.text(68, info_start + 68, "Wrong color = HEAT", ORANGE)
        pyxel.text(55, info_start + 88, "HEAT=10 / Overflow = GAMEOVER", RED)
        pyxel.text(90, info_start + 120, "Press SPACE to START", WHITE)

    def _draw_game(self) -> None:
        # Camera shake
        if self.shake_timer > 0:
            sx = self._rng.randint(-SHAKE_POWER, SHAKE_POWER)
            sy = self._rng.randint(-SHAKE_POWER, SHAKE_POWER)
            pyxel.camera(sx, sy)
        else:
            pyxel.camera(0, 0)

        self._draw_heat_bar()
        self._draw_columns()
        self._draw_cursor()
        self._draw_hud()
        self._draw_super_indicator()
        self._draw_particles()
        self._draw_floating_texts()

    def _draw_heat_bar(self) -> None:
        bar_w = WIDTH
        bar_h = HEAT_BAR_HEIGHT
        # Background
        pyxel.rect(0, 0, bar_w, bar_h, DARK_BLUE)
        # Fill
        fill_w = int(bar_w * self.heat / MAX_HEAT)
        if fill_w > 0:
            if self.heat >= 7:
                color = RED
            elif self.heat >= 4:
                color = ORANGE
            else:
                color = GREEN
            pyxel.rect(0, 0, fill_w, bar_h, color)

    def _draw_columns(self) -> None:
        for col_idx, column in enumerate(self.columns):
            lx = COLUMN_LEFT_X[col_idx]
            # Column outline
            pyxel.rectb(
                lx,
                COLUMN_TOP_Y - 2,
                COLUMN_WIDTH,
                COLUMN_BOTTOM_Y - COLUMN_TOP_Y + 4,
                GRAY,
            )
            # Boards (0 = bottom, last = top)
            for bidx, board in enumerate(column):
                if bidx > MAX_BOARDS_PER_COLUMN:
                    break
                by = int(self._board_bottom_y(col_idx, bidx))
                # Board fill
                pyxel.rect(
                    lx + 2,
                    by - BOARD_HEIGHT + 2,
                    COLUMN_WIDTH - 4,
                    BOARD_HEIGHT - 4,
                    board.color,
                )
                # Board border (darker)
                bcol = max(board.color - 1, 0) if board.color > 0 else 0
                pyxel.rectb(
                    lx + 2,
                    by - BOARD_HEIGHT + 2,
                    COLUMN_WIDTH - 4,
                    BOARD_HEIGHT - 4,
                    bcol,
                )

    def _draw_cursor(self) -> None:
        col_idx = self.cursor_col
        lx = COLUMN_LEFT_X[col_idx]
        pulse = (pyxel.frame_count // 10) % 2

        if self.super_mode:
            rainbow = [RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK]
            color = rainbow[(pyxel.frame_count // 5) % len(rainbow)]
        else:
            color = CYAN if pulse else WHITE

        t = 2
        x1 = lx - t
        y1 = COLUMN_TOP_Y - 2 - t
        w = COLUMN_WIDTH + t * 2
        h = COLUMN_BOTTOM_Y - COLUMN_TOP_Y + 4 + t * 2
        pyxel.rectb(x1, y1, w, h, color)
        # Double border for glow
        if not self.super_mode:
            pyxel.rectb(x1 + 1, y1 + 1, w - 2, h - 2, color)

    def _draw_hud(self) -> None:
        y0 = HEAT_BAR_HEIGHT + 2
        pyxel.text(2, y0, f"SCORE:{self.score}", WHITE)
        combo_color = YELLOW if self.combo > 0 else GRAY
        pyxel.text(2, y0 + 10, f"COMBO:{self.combo}", combo_color)
        pyxel.text(2, y0 + 20, f"MAX:{self.max_combo}", GRAY)

    def _draw_super_indicator(self) -> None:
        if not self.super_mode:
            return
        rainbow = [RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK]
        color = rainbow[(pyxel.frame_count // 3) % len(rainbow)]
        sec = self.super_timer // FPS + 1
        label = f"SUPER CHOP! {sec}s"
        pyxel.text(WIDTH // 2 - len(label) * 4 // 2, HEAT_BAR_HEIGHT + 2, label, color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            dim = max(0, p.color - (PARTICLE_LIFE_MAX - p.life) // 6)
            pyxel.rect(int(p.x) - 1, int(p.y) - 1, 3, 3, dim)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            life_ratio = ft.life / FLOAT_LIFE_MAX
            if life_ratio < 0.4:
                color = GRAY
            elif life_ratio < 0.7:
                color = ft.color
            else:
                color = ft.color
            tx = int(ft.x) - len(ft.text) * 2
            ty = int(ft.y)
            pyxel.text(tx, ty, ft.text, color)

    def _draw_game_over(self) -> None:
        pyxel.text(115, 60, "GAME OVER", RED)
        pyxel.text(98, 90, f"FINAL SCORE: {self.score}", WHITE)
        pyxel.text(98, 110, f"MAX COMBO:  {self.max_combo}", YELLOW)
        pyxel.text(85, 135, f"SURVIVED: {self.game_timer // FPS}s", GRAY)

        if self.heat >= MAX_HEAT:
            reason = "HEAT OVERLOAD"
        else:
            reason = "BOARD OVERFLOW"
        pyxel.text(98, 155, f"REASON: {reason}", ORANGE)

        pyxel.text(88, 200, "Press SPACE to RETRY", WHITE)


# ── Pyxel Application Layer ────────────────────────────────────────────────

_game: Game | None = None


def _get_game() -> Game:
    global _game
    if _game is None:
        _game = Game.__new__(Game)
        _game._init_state()
    return _game


def update() -> None:
    g = _get_game()

    if g.phase == Phase.TITLE:
        if pyxel.btnp(pyxel.KEY_SPACE):
            g.reset()
            g.phase = Phase.PLAYING
            for _ in range(3):
                g._spawn_board()
    elif g.phase == Phase.PLAYING:
        _handle_input(g)
        g.update(1)
    elif g.phase == Phase.GAME_OVER:
        if pyxel.btnp(pyxel.KEY_SPACE):
            g.reset()
            g.phase = Phase.TITLE


def _handle_input(g: Game) -> None:
    if pyxel.btnp(pyxel.KEY_LEFT):
        g.cursor_col = (g.cursor_col - 1) % NUM_COLUMNS
    if pyxel.btnp(pyxel.KEY_RIGHT):
        g.cursor_col = (g.cursor_col + 1) % NUM_COLUMNS
    if pyxel.btnp(pyxel.KEY_SPACE):
        g._chop(g.cursor_col)


def draw() -> None:
    _get_game().draw()


def main() -> None:
    pyxel.init(WIDTH, HEIGHT, title="Chop Chain", fps=FPS, display_scale=DISPLAY_SCALE)
    pyxel.run(update, draw)


if __name__ == "__main__":
    main()
