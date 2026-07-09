from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ---------------------------------------------------------------------------
# Color constants
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

FLOWER_COLORS: tuple[int, ...] = (RED, LIME, DARK_BLUE, YELLOW)
GRASS_COLOR: int = GREEN
CUT_COLOR: int = GRAY
UI_BG: int = DARK_BLUE
UI_TEXT: int = WHITE


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
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
# Phase enum
# ---------------------------------------------------------------------------
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    CELL: int = 20
    COLS: int = 16
    ROWS: int = 12
    GRID_Y: int = 30
    SCREEN_W: int = 320
    SCREEN_H: int = 240

    SUPER_DURATION: int = 150  # 5 seconds at 30fps
    HEAT_MAX: float = 100.0
    HEAT_PER_CUT: float = 1.0
    HEAT_MISMATCH: float = 15.0
    HEAT_DECAY: float = 0.05
    COMBO_SUPER_THRESHOLD: int = 4
    TRAIL_LENGTH: int = 5

    def __init__(self) -> None:
        pyxel.init(self.SCREEN_W, self.SCREEN_H, title="MOW CHAIN", display_scale=2)
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    # -----------------------------------------------------------------------
    # State initialization (testable)
    # -----------------------------------------------------------------------
    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.grid: list[list[int]] = []  # 0=uncut, -1=cut
        self.flowers: list[list[int]] = []  # 0-3 color index
        self.mower_col: int = 0
        self.mower_row: int = 0
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.timer: int = 60 * 30  # frames
        self.super_timer: int = 0
        self.last_color: int = -1
        self.multiplier: int = 1
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.frame: int = 0
        self.mower_dir: int = 0  # 0=right, 1=down, 2=left, 3=up
        self.shake_frames: int = 0
        self.trail: list[tuple[int, int]] = []

        self._init_grid()
        self.mower_col = self.COLS // 2
        self.mower_row = self.ROWS // 2

    def _init_grid(self) -> None:
        self.grid = [[0] * self.COLS for _ in range(self.ROWS)]
        self.flowers = [
            [self._rng.randrange(0, len(FLOWER_COLORS)) for _ in range(self.COLS)]
            for _ in range(self.ROWS)
        ]

    # -----------------------------------------------------------------------
    # Movement & cutting (testable)
    # -----------------------------------------------------------------------
    def _move_mower(self, dx: int, dy: int) -> bool:
        new_col = self.mower_col + dx
        new_row = self.mower_row + dy
        if new_col < 0 or new_col >= self.COLS or new_row < 0 or new_row >= self.ROWS:
            return False

        self.mower_col = new_col
        self.mower_row = new_row

        if dx > 0:
            self.mower_dir = 0
        elif dy > 0:
            self.mower_dir = 1
        elif dx < 0:
            self.mower_dir = 2
        elif dy < 0:
            self.mower_dir = 3

        already_cut = self.grid[self.mower_row][self.mower_col] == -1
        if not already_cut:
            self._cut_tile(self.mower_col, self.mower_row)
        return True

    def _cut_tile(self, col: int, row: int) -> None:
        self.grid[row][col] = -1
        color_idx = self.flowers[row][col]
        color = FLOWER_COLORS[color_idx]  # pyxel color value
        self._update_combo(color_idx)
        self.heat = min(self.heat + self.HEAT_PER_CUT, self.HEAT_MAX)
        points = 10 * self.combo * self.multiplier if self.combo > 0 else 10 * self.multiplier
        self.score += points
        self._spawn_particles(col, row, color)
        self._spawn_floating_text(col, row, f"+{points}", color)
        if self.combo >= 2:
            self._spawn_floating_text(col, row - 0.5, f"x{self.combo}", YELLOW)
        self.trail.append((col, row))
        if len(self.trail) > self.TRAIL_LENGTH:
            self.trail.pop(0)
        if self.heat >= self.HEAT_MAX:
            self.shake_frames = 15

    def _update_combo(self, color_idx: int) -> None:
        if self.super_timer > 0:
            match = True
        elif self.last_color == -1:
            match = True
        else:
            match = (color_idx == self.last_color)

        if match:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            if self.combo >= self.COMBO_SUPER_THRESHOLD:
                self._activate_super()
        else:
            self.combo = 0
            self.heat = min(self.heat + self.HEAT_MISMATCH, self.HEAT_MAX)
            self._spawn_floating_text(
                self.mower_col, self.mower_row - 1, "JAM!", RED
            )
            self.shake_frames = 5

        self.last_color = color_idx

    def _activate_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer = self.SUPER_DURATION
        else:
            self.super_timer = self.SUPER_DURATION
            self.multiplier = 3
            self._spawn_floating_text(
                self.mower_col, self.mower_row - 2, "SUPER!", ORANGE
            )

    # -----------------------------------------------------------------------
    # Particles & floating text (testable)
    # -----------------------------------------------------------------------
    def _spawn_particles(self, col: int, row: int, color: int) -> None:
        px = col * self.CELL + self.CELL / 2
        py = row * self.CELL + self.CELL / 2 + self.GRID_Y
        count = self._rng.randint(8, 12)
        for _ in range(count):
            p_color = color
            if self.super_timer > 0 and self._rng.random() < 0.5:
                p_color = self._rng.choice(FLOWER_COLORS)
            self.particles.append(
                Particle(
                    x=px,
                    y=py,
                    vx=self._rng.uniform(-1.0, 1.0),
                    vy=self._rng.uniform(-2.0, -0.5),
                    life=self._rng.randint(15, 25),
                    color=p_color,
                )
            )

    def _spawn_floating_text(self, col: float, row: float, text: str, color: int) -> None:
        px = col * self.CELL + self.CELL / 2
        py = row * self.CELL + self.CELL / 2 + self.GRID_Y
        self.floating_texts.append(
            FloatingText(
                x=px,
                y=py,
                text=text,
                life=self._rng.randint(30, 45),
                color=color,
            )
        )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.life -= 1
            p.vy += 0.1  # gravity
            p.x += p.vx
            p.y += p.vy
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.life -= 1
            ft.y -= 0.5
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # -----------------------------------------------------------------------
    # Timer & heat (testable)
    # -----------------------------------------------------------------------
    def _update_timer(self) -> None:
        if self.timer > 0:
            self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER

    def _update_heat(self) -> None:
        if self.heat >= self.HEAT_MAX:
            self.phase = Phase.GAME_OVER

    # -----------------------------------------------------------------------
    # Pyxel update
    # -----------------------------------------------------------------------
    def update(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()
            self.phase = Phase.TITLE
            return

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.phase = Phase.PLAYING
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.TITLE
            return

        if self.phase == Phase.PLAYING:
            self.frame += 1

            # Movement
            moved = False
            if pyxel.btnp(pyxel.KEY_RIGHT):
                moved = self._move_mower(1, 0)
            elif pyxel.btnp(pyxel.KEY_DOWN):
                moved = self._move_mower(0, 1)
            elif pyxel.btnp(pyxel.KEY_LEFT):
                moved = self._move_mower(-1, 0)
            elif pyxel.btnp(pyxel.KEY_UP):
                moved = self._move_mower(0, -1)

            # Heat decay when not moving
            if not moved:
                self.heat = max(self.heat - self.HEAT_DECAY, 0.0)

            # SUPER timer
            if self.super_timer > 0:
                self.super_timer -= 1
                if self.super_timer <= 0:
                    self.multiplier = 1

            # Shake
            if self.shake_frames > 0:
                self.shake_frames -= 1

            # Updates
            self._update_particles()
            self._update_floating_texts()
            self._update_timer()
            self._update_heat()

    # -----------------------------------------------------------------------
    # Pyxel draw
    # -----------------------------------------------------------------------
    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.cls(DARK_BLUE)
        pyxel.text(self.SCREEN_W // 2 - 32, 50, "MOW CHAIN", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 54, 90, "Arrow Keys: Move", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 64, 102, "Cut grass, match colors!", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 72, 114, "COMBO>=4: SUPER MOWER", ORANGE)
        pyxel.text(self.SCREEN_W // 2 - 68, 134, "Press SPACE to Start", LIME)

    def _draw_game_over(self) -> None:
        pyxel.cls(DARK_BLUE)
        pyxel.text(self.SCREEN_W // 2 - 28, 70, "GAME OVER", RED)
        pyxel.text(self.SCREEN_W // 2 - 42, 100, f"SCORE: {self.score}", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 54, 114, f"MAX COMBO: {self.max_combo}", YELLOW)
        pyxel.text(self.SCREEN_W // 2 - 72, 140, "Press SPACE to Retry", LIME)

    def _draw_playing(self) -> None:
        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0:
            shake_x = self._rng.randint(-2, 2)
            shake_y = self._rng.randint(-2, 2)

        # SUPER rainbow border
        if self.super_timer > 0:
            self._draw_super_border()

        # Apply shake to grid area only
        offset_x = shake_x
        offset_y = self.GRID_Y + shake_y

        # Draw grid
        for row in range(self.ROWS):
            for col in range(self.COLS):
                x = col * self.CELL + offset_x
                y = row * self.CELL + offset_y
                if self.grid[row][col] == 0:
                    # Uncut grass
                    pyxel.rect(x, y, self.CELL, self.CELL, GRASS_COLOR)
                    # Texture dots
                    if (row + col) % 3 == 0:
                        pyxel.pset(x + 5, y + 5, GREEN - 1)
                    if (row + col) % 5 == 2:
                        pyxel.pset(x + 14, y + 14, GREEN - 1)
                else:
                    # Cut grass
                    pyxel.rect(x, y, self.CELL, self.CELL, CUT_COLOR)
                    # Flower dot
                    flower_idx = self.flowers[row][col]
                    flower_color = FLOWER_COLORS[flower_idx]
                    fx = x + self.CELL // 2 - 3
                    fy = y + self.CELL // 2 - 3
                    pyxel.rect(fx, fy, 6, 6, flower_color)

        # Mower trail
        for idx, (tc, tr) in enumerate(self.trail):
            alpha = (idx + 1) / len(self.trail)
            bright_color = 7 if alpha > 0.6 else 5
            tx = tc * self.CELL + offset_x + 1
            ty = tr * self.CELL + offset_y + 1
            pyxel.rectb(tx, ty, self.CELL - 2, self.CELL - 2, bright_color)

        # Mower
        mx = self.mower_col * self.CELL + offset_x + 1
        my = self.mower_row * self.CELL + offset_y + 1
        mower_color = WHITE
        if self.last_color >= 0:
            mower_color = FLOWER_COLORS[self.last_color]
        if self.super_timer > 0:
            rainbow_idx = (pyxel.frame_count // 4) % 4
            mower_color = FLOWER_COLORS[rainbow_idx]
        pyxel.rect(mx, my, self.CELL - 2, self.CELL - 2, mower_color)

        # Direction indicator on mower
        cx = mx + (self.CELL - 2) // 2
        cy = my + (self.CELL - 2) // 2
        if self.mower_dir == 0:
            pyxel.rect(cx + 4, cy - 1, 4, 2, BLACK)
        elif self.mower_dir == 1:
            pyxel.rect(cx - 1, cy + 4, 2, 4, BLACK)
        elif self.mower_dir == 2:
            pyxel.rect(cx - 8, cy - 1, 4, 2, BLACK)
        elif self.mower_dir == 3:
            pyxel.rect(cx - 1, cy - 8, 2, 4, BLACK)

        # Particles
        for p in self.particles:
            px = int(p.x) + offset_x
            py = int(p.y) + offset_y - self.GRID_Y
            if 0 <= px < self.SCREEN_W and 0 <= py < self.SCREEN_H:
                pyxel.pset(px, py, p.color)

        # Floating texts
        for ft in self.floating_texts:
            tx = int(ft.x) + offset_x - len(ft.text) * 2
            ty = int(ft.y) + offset_y - self.GRID_Y
            pyxel.text(tx, ty, ft.text, ft.color)

        # UI bar
        self._draw_ui_bar()

    def _draw_ui_bar(self) -> None:
        # Background
        pyxel.rect(0, 0, self.SCREEN_W, self.GRID_Y, UI_BG)

        # Score
        pyxel.text(4, 4, f"SCORE:{self.score:6d}", UI_TEXT)

        # Combo
        combo_text = f"COMBO:{self.combo}"
        combo_color = YELLOW if self.combo >= self.COMBO_SUPER_THRESHOLD else UI_TEXT
        pyxel.text(90, 4, combo_text, combo_color)

        # Timer
        seconds = max(0, self.timer // 30)
        timer_color = RED if seconds <= 10 else UI_TEXT
        pyxel.text(150, 4, f"TIME:{seconds:2d}", timer_color)

        # SUPER indicator
        if self.super_timer > 0:
            super_secs = self.super_timer // 30 + 1
            rainbow_idx = (pyxel.frame_count // 4) % 4
            pyxel.text(210, 4, f"SUPER:{super_secs}", FLOWER_COLORS[rainbow_idx])

        # HEAT bar
        bar_x = 270
        bar_y = 4
        bar_w = 46
        bar_h = 8
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        fill_w = int((self.heat / self.HEAT_MAX) * (bar_w - 2))
        heat_color = RED if self.heat >= 80 else ORANGE if self.heat >= 50 else LIME
        if fill_w > 0:
            pyxel.rect(bar_x + 1, bar_y + 1, fill_w, bar_h - 2, heat_color)

        # HEAT label
        pyxel.text(bar_x - 16, bar_y + 1, "H", RED)

        # Bottom separator line
        pyxel.line(0, self.GRID_Y, self.SCREEN_W, self.GRID_Y, WHITE)

    def _draw_super_border(self) -> None:
        rainbow_offset = pyxel.frame_count // 4
        for i in range(4):
            color = FLOWER_COLORS[(rainbow_offset + i) % 4]
            pyxel.rectb(i, i, self.SCREEN_W - i * 2, self.SCREEN_H - i * 2, color)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    Game()
