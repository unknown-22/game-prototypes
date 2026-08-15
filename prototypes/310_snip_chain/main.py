"""SNIP CHAIN — barber color-match arcade prototype.

A head sits at the bottom of the screen with colored hair locks growing UP from
the scalp. The scissors color auto-cycles. Click a matching lock to snip it and
build a combo; a 4+ combo triggers SUPER SNIP (rainbow, any color matches, 3x
score, HEAT frozen). Mismatching is a "nick" (HEAT +15, combo reset). Hair grows
back via a cellular automaton; if it overgrows the top row the game ends.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

import pyxel

# --- Constants ---------------------------------------------------------------

SCREEN_W = 320
SCREEN_H = 240
ROWS = 8
COLS = 10
CELL = 24
OFFSET_X = (SCREEN_W - COLS * CELL) // 2  # 40
OFFSET_Y = 8
GRID_W = COLS * CELL  # 240
GRID_H = ROWS * CELL  # 192

START_TIME = 3600  # 60s at 60fps
SUPER_DURATION = 300
SUPER_THRESHOLD = 4
GROW_CHANCE = 0.35
HEAT_NICK = 15.0
HEAT_MAX = 100.0
HEAT_DECAY = 0.02

# Colors
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

HAIR_COLORS: dict[int, int] = {
    1: RED,
    2: LIME,
    3: DARK_BLUE,
    4: YELLOW,
}

RAINBOW: list[int] = [RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE]


class Phase(Enum):
    TITLE = "title"
    PLAYING = "playing"
    GAME_OVER = "game_over"


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


class Game:
    """Main game object. Logic is kept pyxel-input-free for headless testing."""

    # All state is initialized here (and again in reset) so Game.__new__ can be
    # used headlessly without invoking pyxel.init/run.
    phase: Phase
    grid: list[list[int]]
    scissors_color: int
    color_timer: int
    cycle_interval: int
    grow_interval: int
    combo: int
    max_combo: int
    score: int
    best_score: int
    heat: float
    timer: int
    elapsed: int
    grow_timer: int
    super_mode: bool
    super_timer: int
    particles: list[Particle]
    floating_texts: list[FloatingText]
    shake_frames: int
    game_over_reason: str
    rng: random.Random

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="SNIP CHAIN", fps=60, display_scale=2)
        self.rng = random.Random()
        self.best_score = 0
        self.reset()
        self.phase = Phase.TITLE
        pyxel.run(self.update, self.draw)

    # --- State / reset -------------------------------------------------------

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.grid = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        self.scissors_color = 1
        self.color_timer = 20
        self.cycle_interval = 20
        self.grow_interval = 60
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.heat = 0.0
        self.timer = START_TIME
        self.elapsed = 0
        self.grow_timer = 60
        self.super_mode = False
        self.super_timer = 0
        self.particles = []
        self.floating_texts = []
        self.shake_frames = 0
        self.game_over_reason = ""
        for _ in range(4):
            col = self.rng.randint(0, COLS - 1)
            self.grid[ROWS - 1][col] = self.rng.randint(1, 4)

    # --- Difficulty helpers ---------------------------------------------------

    def _cycle_interval(self) -> int:
        return max(12, 20 - self.elapsed // 180)

    def _grow_interval(self) -> int:
        return max(30, 60 - self.elapsed // 120)

    # --- Core logic (testable, no pyxel input) --------------------------------

    def _update_color_cycle(self) -> None:
        self.color_timer -= 1
        if self.color_timer <= 0:
            self.scissors_color = self.scissors_color % 4 + 1
            self.color_timer = self.cycle_interval

    def _grow_hair(self) -> None:
        candidates: list[tuple[int, int]] = []
        for row in range(ROWS):
            for col in range(COLS):
                if self.grid[row][col] != 0:
                    continue
                if row == ROWS - 1:
                    candidates.append((row, col))
                elif self.grid[row + 1][col] != 0:
                    candidates.append((row, col))
        for row, col in candidates:
            if self.rng.random() < GROW_CHANCE:
                self.grid[row][col] = self.rng.randint(1, 4)

    def _snip(self, col: int, row: int) -> str:
        if not (0 <= col < COLS and 0 <= row < ROWS):
            return "EMPTY"
        color = self.grid[row][col]
        if color == 0:
            return "EMPTY"

        if self.super_mode or color == self.scissors_color:
            self.grid[row][col] = 0
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            mult = 3 if self.super_mode else 1
            gained = 10 * self.combo * mult
            self.score += gained
            self._spawn_match_particles(col, row, color)
            cx = OFFSET_X + col * CELL + CELL // 2
            cy = OFFSET_Y + row * CELL + CELL // 2
            text_color = YELLOW if self.super_mode else HAIR_COLORS[color]
            self._add_floating_text(cx, cy, f"+{gained}", text_color)
            if self.combo >= SUPER_THRESHOLD and not self.super_mode:
                self.super_mode = True
                self.super_timer = SUPER_DURATION
            return "MATCH"

        self.heat += HEAT_NICK
        self.combo = 0
        self._spawn_mismatch_particles(col, row)
        cx = OFFSET_X + col * CELL + CELL // 2
        cy = OFFSET_Y + row * CELL + CELL // 2
        self._add_floating_text(cx, cy, "WRONG!", RED)
        self.shake_frames = 6
        return "MISMATCH"

    def _check_overgrown(self) -> bool:
        return any(self.grid[0][col] != 0 for col in range(COLS))

    def _update_heat(self) -> None:
        if self.heat >= HEAT_MAX:
            self.game_over_reason = "NICKED OUT"
            self.phase = Phase.GAME_OVER
            return
        if not self.super_mode:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_timer(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.game_over_reason = "TIME UP"
            self.phase = Phase.GAME_OVER

    def _update_super(self) -> None:
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False

    # --- Particles / floating text -------------------------------------------

    def _spawn_match_particles(self, col: int, row: int, color: int) -> None:
        cx = OFFSET_X + col * CELL + CELL // 2
        cy = OFFSET_Y + row * CELL + CELL // 2
        n = 20 if self.super_mode else 8
        for _ in range(n):
            vx = self.rng.uniform(-1.5, 1.5)
            vy = self.rng.uniform(-1.5, 1.5)
            pcol = self.rng.choice(RAINBOW) if self.super_mode else HAIR_COLORS[color]
            self.particles.append(
                Particle(cx, cy, vx, vy, self.rng.randint(15, 30 if self.super_mode else 25), pcol)
            )

    def _spawn_mismatch_particles(self, col: int, row: int) -> None:
        cx = OFFSET_X + col * CELL + CELL // 2
        cy = OFFSET_Y + row * CELL + CELL // 2
        for _ in range(4):
            vx = self.rng.uniform(-1.5, 1.5)
            vy = self.rng.uniform(-1.5, 1.5)
            self.particles.append(Particle(cx, cy, vx, vy, self.rng.randint(10, 15), WHITE))

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x, y, text, color, 30))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for t in self.floating_texts:
            t.y -= 0.5
            t.life -= 1
        self.floating_texts = [t for t in self.floating_texts if t.life > 0]

    # --- Update ---------------------------------------------------------------

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
        elif self.phase == Phase.PLAYING:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                col = (pyxel.mouse_x - OFFSET_X) // CELL
                row = (pyxel.mouse_y - OFFSET_Y) // CELL
                if 0 <= col < COLS and 0 <= row < ROWS:
                    self._snip(col, row)
            self._update_playing()

    def _update_playing(self) -> None:
        self.elapsed += 1
        self.cycle_interval = self._cycle_interval()
        self.grow_interval = self._grow_interval()
        self._update_color_cycle()
        self._update_timer()
        self._update_heat()
        self._update_super()
        if self.phase == Phase.PLAYING:
            self.grow_timer -= 1
            if self.grow_timer <= 0:
                self._grow_hair()
                self.grow_timer = self.grow_interval
            if self._check_overgrown():
                self.game_over_reason = "OVERGROWN"
                self.phase = Phase.GAME_OVER
        self._update_particles()
        self._update_floating_texts()
        if self.shake_frames > 0:
            self.shake_frames -= 1
        if self.phase == Phase.GAME_OVER and self.score > self.best_score:
            self.best_score = self.score

    # --- Draw -----------------------------------------------------------------

    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _center_text(self, y: int, s: str, col: int) -> None:
        pyxel.text((SCREEN_W - len(s) * 4) // 2, y, s, col)

    def _draw_title(self) -> None:
        pyxel.cls(BLACK)
        self._center_text(60, "SNIP CHAIN", YELLOW)
        self._center_text(80, "CLICK matching-color hair to snip", WHITE)
        self._center_text(92, "Mismatch = HEAT up / combo reset", WHITE)
        self._center_text(104, "Don't let hair overgrow the top!", WHITE)
        self._center_text(116, "4x combo = SUPER SNIP (rainbow)", LIME)
        self._center_text(150, f"BEST {self.best_score}", ORANGE)
        self._center_text(170, "PRESS ENTER", WHITE)
        # color legend
        for i, color in enumerate(HAIR_COLORS.values()):
            x = 110 + i * 28
            pyxel.rect(x, 190, 16, 16, color)
            pyxel.rectb(x, 190, 16, 16, WHITE)

    def _draw_head(self) -> None:
        pyxel.rect(0, 200, SCREEN_W, 40, PEACH)
        pyxel.elli(120, 196, 80, 44, PEACH)
        pyxel.rect(140, 212, 5, 5, BLACK)
        pyxel.rect(175, 212, 5, 5, BLACK)
        pyxel.rect(150, 224, 20, 3, BLACK)

    def _draw_hair(self) -> None:
        for row in range(ROWS):
            for col in range(COLS):
                color = self.grid[row][col]
                if color != 0:
                    x = OFFSET_X + col * CELL + 1
                    y = OFFSET_Y + row * CELL + 1
                    pyxel.rect(x, y, CELL - 2, CELL - 2, HAIR_COLORS[color])

        # top-row warning (row 1 -> flashes to telegraph overgrowth)
        if any(self.grid[1][col] != 0 for col in range(COLS)) and (pyxel.frame_count // 8) % 2 == 0:
            for col in range(COLS):
                if self.grid[1][col] != 0:
                    pyxel.rectb(OFFSET_X + col * CELL, OFFSET_Y + CELL, CELL, CELL, WHITE)

    def _draw_rainbow_border(self) -> None:
        offset = (pyxel.frame_count // 4) % 7
        for i in range(7):
            color = RAINBOW[(offset + i) % 7]
            pyxel.rectb(OFFSET_X - i, OFFSET_Y - i, GRID_W + 2 * i, GRID_H + 2 * i, color)

    def _draw_hud(self) -> None:
        pyxel.text(2, 2, f"SCORE {self.score}", WHITE)
        pyxel.text(2, 10, f"COMBO {self.combo}", LIME if self.combo >= SUPER_THRESHOLD else WHITE)
        # scissors swatch
        pyxel.rect(2, 18, 14, 14, HAIR_COLORS[self.scissors_color])
        pyxel.rectb(2, 18, 14, 14, WHITE)
        if self.super_mode:
            pyxel.text(20, 21, "SUPER!", YELLOW)

        # timer bar (top center)
        bar_x = 110
        bar_w = 100
        pyxel.rect(bar_x, 2, bar_w, 6, GRAY)
        w = int(bar_w * self.timer / START_TIME)
        pyxel.rect(bar_x, 2, w, 6, LIGHT_BLUE)
        pyxel.rectb(bar_x, 2, bar_w, 6, WHITE)

        # HEAT bar (right vertical)
        bx = 312
        by = 40
        bh = 160
        pyxel.text(bx - 3, by - 8, "HEAT", WHITE)
        pyxel.rect(bx, by, 6, bh, GRAY)
        fill_h = int(bh * self.heat / HEAT_MAX)
        if fill_h > 0:
            if self.heat > 60:
                heat_col = RED
            elif self.heat > 40:
                heat_col = ORANGE
            else:
                heat_col = GREEN
            pyxel.rect(bx, by + bh - fill_h, 6, fill_h, heat_col)
        pyxel.rectb(bx, by, 6, bh, WHITE)

    def _draw_scissors_cursor(self) -> None:
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        pyxel.line(mx, my, mx + 8, my + 8, GRAY)
        pyxel.line(mx, my + 8, mx + 8, my, GRAY)
        pyxel.circ(mx - 3, my - 2, 2, WHITE)
        pyxel.circ(mx - 3, my + 10, 2, WHITE)

    def _draw_playing(self) -> None:
        if self.shake_frames > 0:
            pyxel.camera(self.rng.randint(-2, 2), self.rng.randint(-2, 2))
        else:
            pyxel.camera(0, 0)
        pyxel.cls(BLACK)
        self._draw_head()
        self._draw_hair()
        self._draw_hud()
        if self.super_mode:
            self._draw_rainbow_border()
        for p in self.particles:
            pyxel.rect(int(p.x), int(p.y), 2, 2, p.color)
        for t in self.floating_texts:
            pyxel.text(int(t.x), int(t.y), t.text, t.color)
        self._draw_scissors_cursor()

    def _draw_game_over(self) -> None:
        pyxel.cls(BLACK)
        self._center_text(70, "GAME OVER", RED)
        self._center_text(95, self.game_over_reason, WHITE)
        self._center_text(115, f"SCORE {self.score}", YELLOW)
        self._center_text(130, f"MAX COMBO {self.max_combo}", LIME)
        self._center_text(145, f"BEST {self.best_score}", ORANGE)
        self._center_text(170, "PRESS ENTER", WHITE)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
