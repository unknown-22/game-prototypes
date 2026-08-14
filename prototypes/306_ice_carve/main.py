"""ICE CARVE — Color-match chisel sculptor.

Chisel colored ice shards. Match the chisel's color to build COMBO chains;
reach COMBO >= 4 to trigger SUPER CHISEL (rainbow, 3x score, heat frozen).
Wrong-color chisels overheat the blade and melt the block, and melt SPREADS
across the ice via a cellular-automaton rule, destroying your material.

Core fun moment: 同色の氷片を次々に削ってコンボを伸ばし、SUPER CHISEL の虹色で
一気にブロックを削ってスコアが爆発する。色を間違えると熱でブロックが溶け広がる緊張感。
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ──────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
DISPLAY_SCALE = 2
FPS = 60

GRID_SIZE = 8
CELL = 24
GRID_X = 64
GRID_Y = 24
GRID_PIXELS = GRID_SIZE * CELL  # 192

# Cell states (0..3 are shard color indices; negatives are dead/empty)
EMPTY = -1
MELTED = -2
NUM_COLORS = 4

# Shard color indices -> pyxel palette color
SHARD_COLORS: tuple[int, int, int, int] = (
    pyxel.COLOR_RED,        # 0
    pyxel.COLOR_LIME,       # 1
    pyxel.COLOR_DARK_BLUE,  # 2
    pyxel.COLOR_YELLOW,     # 3
)

# Timing (60 fps)
TOTAL_FRAMES = 3600  # 60 seconds
SUPER_FRAMES = 300
SUPER_THRESHOLD = 4
SUPER_MULT = 3.0

# Heat
HEAT_MISMATCH = 15
HEAT_MAX = 100.0
HEAT_DECAY = 0.02

# Melt cellular automaton
MELT_INTERVAL_START = 45
MELT_INTERVAL_END = 20
MELT_SPREAD_CHANCE = 0.2

# Spawning
SPAWN_INTERVAL_START = 60
SPAWN_INTERVAL_END = 30
TARGET_SHARDS = 24

# Scoring
BASE_SCORE = 10

# SUPER border rainbow cycle
RAINBOW: tuple[int, ...] = (8, 11, 5, 10, 9, 12, 14, 15)


# ── Data Classes ───────────────────────────────────────────────────────


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


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


# ── Game Class ─────────────────────────────────────────────────────────


class Game:
    def __init__(self) -> None:
        pyxel.init(
            SCREEN_W, SCREEN_H, title="ICE CARVE",
            display_scale=DISPLAY_SCALE, fps=FPS,
        )
        pyxel.mouse(False)
        self.best_score = 0
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.rng: random.Random = random.Random()
        self.phase: Phase = Phase.TITLE
        self.chisel_color: int = 0
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.super_timer: int = 0
        self.timer: int = TOTAL_FRAMES
        self.melt_interval: int = MELT_INTERVAL_START
        self.melt_countdown: int = MELT_INTERVAL_START
        self.spawn_interval: int = SPAWN_INTERVAL_START
        self.spawn_countdown: int = SPAWN_INTERVAL_START
        self.target_shards: int = TARGET_SHARDS
        self.particles: list[Particle] = []
        self.floats: list[FloatText] = []
        self.shake: int = 0
        self.shake_mag: int = 0
        self.last_color: int | None = None
        # NOTE: best_score intentionally NOT reset (persists across runs).
        self._init_board()

    def _init_board(self) -> None:
        self.grid: list[list[int]] = [
            [EMPTY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)
        ]
        for _ in range(self.target_shards):
            self._spawn_shard()

    # ── Testable Logic (no pyxel input) ───────────────────────────

    def _shard_color_at(self, col: int, row: int) -> int:
        return self.grid[row][col]

    def _click_cell(self, col: int, row: int) -> None:
        if not (0 <= col < GRID_SIZE and 0 <= row < GRID_SIZE):
            return
        color = self._shard_color_at(col, row)  # capture BEFORE mutation
        if color == EMPTY or color == MELTED:
            return
        self.last_color = color

        if self.super_timer > 0 or color == self.chisel_color:
            self._resolve_match(col, row, color)
        else:
            self._resolve_mismatch(col, row)

    def _resolve_match(self, col: int, row: int, color: int) -> None:
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        mult = SUPER_MULT if self.super_timer > 0 else 1.0
        points = int(BASE_SCORE * self.combo * mult)
        self.score += points
        self.grid[row][col] = EMPTY
        self.chisel_color = color
        self._spawn_shard()

        self._spawn_match_particles(col, row, color)
        self._add_float(col, row, f"+{points}", pyxel.COLOR_WHITE)
        if self.combo >= 2:
            self._add_float(
                col, row - 1, f"COMBO X{self.combo}", pyxel.COLOR_ORANGE,
            )
        if self.combo >= SUPER_THRESHOLD and self.super_timer == 0:
            self._activate_super()

    def _resolve_mismatch(self, col: int, row: int) -> None:
        self.combo = 0
        self.heat = min(HEAT_MAX, self.heat + HEAT_MISMATCH)
        self.grid[row][col] = MELTED
        self.shake = 8
        self.shake_mag = 2
        self._spawn_mismatch_particles(col, row)
        self._add_float(col, row, "WRONG!", pyxel.COLOR_CYAN)

    def _spawn_shard(self) -> None:
        empty: list[tuple[int, int]] = [
            (c, r)
            for r in range(GRID_SIZE)
            for c in range(GRID_SIZE)
            if self.grid[r][c] == EMPTY
        ]
        if not empty:
            return
        c, r = self.rng.choice(empty)
        self.grid[r][c] = self.rng.randrange(NUM_COLORS)

    def _maintain_board(self) -> None:
        for _ in range(self.target_shards):
            if self._shard_count() >= self.target_shards:
                break
            self._spawn_shard()

    def _shard_count(self) -> int:
        return sum(1 for row in self.grid for cell in row if cell >= 0)

    def _spread_melt(self) -> None:
        melted_cells = [
            (c, r)
            for r in range(GRID_SIZE)
            for c in range(GRID_SIZE)
            if self.grid[r][c] == MELTED
        ]
        for c, r in melted_cells:
            if self.rng.random() >= MELT_SPREAD_CHANCE:
                continue
            neighbors = [
                (nc, nr)
                for nc, nr in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1))
                if 0 <= nc < GRID_SIZE
                and 0 <= nr < GRID_SIZE
                and self.grid[nr][nc] != MELTED
            ]
            if neighbors:
                nc, nr = self.rng.choice(neighbors)
                self.grid[nr][nc] = MELTED

    def _update_heat(self) -> None:
        if self.heat >= HEAT_MAX:
            self._check_game_over()
            return
        if self.super_timer == 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _tick_timer(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self._check_game_over()

    def _escalate(self) -> None:
        progress = (TOTAL_FRAMES - self.timer) / TOTAL_FRAMES
        self.melt_interval = int(
            MELT_INTERVAL_START
            + (MELT_INTERVAL_END - MELT_INTERVAL_START) * progress
        )
        self.spawn_interval = int(
            SPAWN_INTERVAL_START
            + (SPAWN_INTERVAL_END - SPAWN_INTERVAL_START) * progress
        )

    def _activate_super(self) -> None:
        self.super_timer = SUPER_FRAMES
        self.floats.append(FloatText(
            x=float(GRID_X + GRID_PIXELS // 2),
            y=float(GRID_Y - 10),
            text="SUPER CHISEL!",
            life=40,
            color=pyxel.COLOR_RED,
        ))

    def _check_game_over(self) -> None:
        if self.heat >= HEAT_MAX or self.timer <= 0:
            self.phase = Phase.GAME_OVER
            self.best_score = max(self.best_score, self.score)
            self.shake = 12
            self.shake_mag = 3

    # ── VFX helpers ────────────────────────────────────────────────

    def _cell_cx(self, col: int) -> float:
        return float(GRID_X + col * CELL + CELL // 2)

    def _cell_cy(self, row: int) -> float:
        return float(GRID_Y + row * CELL + CELL // 2)

    def _spawn_match_particles(self, col: int, row: int, color: int) -> None:
        cx = self._cell_cx(col)
        cy = self._cell_cy(row)
        super_mode = self.super_timer > 0
        count = 20 if super_mode else 8
        speed = 3.0 if super_mode else 1.5
        for _ in range(count):
            self.particles.append(Particle(
                x=cx,
                y=cy,
                vx=self.rng.uniform(-speed, speed),
                vy=self.rng.uniform(-speed, speed),
                life=self.rng.randint(20, 35) if super_mode else self.rng.randint(15, 25),
                color=self.rng.choice(SHARD_COLORS) if super_mode else SHARD_COLORS[color],
            ))

    def _spawn_mismatch_particles(self, col: int, row: int) -> None:
        cx = self._cell_cx(col)
        cy = self._cell_cy(row)
        for _ in range(4):
            self.particles.append(Particle(
                x=cx + self.rng.uniform(-6, 6),
                y=cy + self.rng.uniform(-6, 6),
                vx=self.rng.uniform(-0.3, 0.3),
                vy=self.rng.uniform(0.2, 0.8),
                life=self.rng.randint(20, 40),
                color=pyxel.COLOR_CYAN,
            ))

    def _add_float(self, col: int, row: int, text: str, color: int) -> None:
        self.floats.append(FloatText(
            x=self._cell_cx(col),
            y=self._cell_cy(row) - 8,
            text=text,
            life=40,
            color=color,
        ))

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floats(self) -> None:
        for ft in self.floats[:]:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life <= 0:
                self.floats.remove(ft)

    # ── Update ─────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()
        else:
            self._update_playing()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self._tick_timer()
        if self.phase != Phase.PLAYING:
            return

        self._escalate()

        if self.super_timer > 0:
            self.super_timer -= 1

        # Melt CA is paused during SUPER
        if self.super_timer == 0:
            self.melt_countdown -= 1
            if self.melt_countdown <= 0:
                self._spread_melt()
                self.melt_countdown = self.melt_interval

        self.spawn_countdown -= 1
        if self.spawn_countdown <= 0:
            self._maintain_board()
            self.spawn_countdown = self.spawn_interval

        self._update_heat()
        self._check_game_over()
        if self.phase != Phase.PLAYING:
            return

        self._update_particles()
        self._update_floats()
        if self.shake > 0:
            self.shake -= 1

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            col = (pyxel.mouse_x - GRID_X) // CELL
            row = (pyxel.mouse_y - GRID_Y) // CELL
            self._click_cell(col, row)

    # ── Draw ───────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_NAVY)
        if self.phase == Phase.TITLE:
            self._draw_title()
            self._draw_cursor()
            return

        ox = oy = 0
        if self.shake > 0:
            ox = self.rng.randint(-self.shake_mag, self.shake_mag)
            oy = self.rng.randint(-self.shake_mag, self.shake_mag)
        pyxel.camera(ox, oy)

        self._draw_board()
        self._draw_particles()
        self._draw_floats()
        self._draw_hud()
        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()

        pyxel.camera(0, 0)
        self._draw_cursor()

    def _draw_board(self) -> None:
        pyxel.rect(
            GRID_X - 4, GRID_Y - 4, GRID_PIXELS + 8, GRID_PIXELS + 8,
            pyxel.COLOR_GRAY,
        )
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                cell = self.grid[r][c]
                x = GRID_X + c * CELL
                y = GRID_Y + r * CELL
                if cell == MELTED:
                    pyxel.rect(x + 2, y + 2, CELL - 4, CELL - 4, pyxel.COLOR_GRAY)
                    pyxel.rectb(x + 2, y + 2, CELL - 4, CELL - 4, pyxel.COLOR_CYAN)
                elif cell >= 0:
                    color = SHARD_COLORS[cell]
                    pyxel.rect(x + 2, y + 2, CELL - 4, CELL - 4, color)
                    pyxel.line(x + 2, y + 2, x + CELL - 3, y + 2, pyxel.COLOR_WHITE)
                    pyxel.line(x + 2, y + 2, x + 2, y + CELL - 3, pyxel.COLOR_WHITE)
                else:
                    pyxel.rectb(x + 2, y + 2, CELL - 4, CELL - 4, pyxel.COLOR_DARK_BLUE)

        if self.super_timer > 0:
            idx = (pyxel.frame_count // 4) % len(RAINBOW)
            pyxel.rectb(
                GRID_X - 4, GRID_Y - 4, GRID_PIXELS + 8, GRID_PIXELS + 8,
                RAINBOW[idx],
            )

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floats(self) -> None:
        for ft in self.floats:
            pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        # Timer bar (top)
        pyxel.rect(GRID_X, 8, GRID_PIXELS, 6, pyxel.COLOR_GRAY)
        w = int(self.timer / TOTAL_FRAMES * GRID_PIXELS)
        pyxel.rect(GRID_X, 8, w, 6, pyxel.COLOR_CYAN)

        # Chisel indicator (top-left)
        chisel_color = (
            RAINBOW[(pyxel.frame_count // 4) % len(RAINBOW)]
            if self.super_timer > 0
            else SHARD_COLORS[self.chisel_color]
        )
        pyxel.rect(12, 14, 22, 22, chisel_color)
        pyxel.rectb(12, 14, 22, 22, pyxel.COLOR_WHITE)
        pyxel.text(12, 38, "CHISEL", pyxel.COLOR_GRAY)

        # Score / combo
        pyxel.text(8, 52, f"SCORE {self.score}", pyxel.COLOR_WHITE)
        combo_color = pyxel.COLOR_YELLOW if self.combo >= 2 else pyxel.COLOR_GRAY
        pyxel.text(8, 62, f"COMBO X{self.combo}", combo_color)

        # Heat bar (right, vertical)
        heat_x = SCREEN_W - 12
        pyxel.rect(heat_x, 24, 6, 180, pyxel.COLOR_GRAY)
        fill_h = int(min(self.heat, HEAT_MAX) / HEAT_MAX * 180)
        pyxel.rect(heat_x, 24 + 180 - fill_h, 6, fill_h, pyxel.COLOR_RED)
        pyxel.text(heat_x - 22, 24, "HEAT", pyxel.COLOR_GRAY)

        # SUPER indicator
        if self.super_timer > 0:
            self._text_center(16, "SUPER!", pyxel.COLOR_RED)

    def _draw_title(self) -> None:
        self._text_center(48, "ICE CARVE", pyxel.COLOR_WHITE)
        self._text_center(72, "COLOR-MATCH CHISEL SCULPTOR", pyxel.COLOR_GRAY)
        self._text_center(104, "CLICK SAME-COLOR ICE SHARDS", pyxel.COLOR_WHITE)
        self._text_center(114, "COMBO>=4 = SUPER CHISEL", pyxel.COLOR_YELLOW)
        self._text_center(124, "WRONG COLOR MELTS THE BLOCK", pyxel.COLOR_RED)
        self._text_center(148, "ENTER TO START", pyxel.COLOR_WHITE)
        self._text_center(168, f"BEST {self.best_score}", pyxel.COLOR_GRAY)

    def _draw_game_over(self) -> None:
        pyxel.rect(0, 70, SCREEN_W, 100, pyxel.COLOR_BLACK)
        pyxel.rectb(0, 70, SCREEN_W, 100, pyxel.COLOR_WHITE)

        title = "MELTDOWN!" if self.heat >= HEAT_MAX else "GAME OVER"
        self._text_center(86, title, pyxel.COLOR_RED)
        self._text_center(106, f"SCORE {self.score}", pyxel.COLOR_WHITE)
        self._text_center(116, f"BEST {self.best_score}", pyxel.COLOR_GRAY)
        self._text_center(126, f"MAX COMBO X{self.max_combo}", pyxel.COLOR_YELLOW)
        self._text_center(146, "ENTER TO RETRY", pyxel.COLOR_WHITE)

    def _draw_cursor(self) -> None:
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        pyxel.rectb(mx - 3, my - 3, 7, 7, pyxel.COLOR_WHITE)
        pyxel.pset(mx, my, SHARD_COLORS[self.chisel_color])

    def _text_center(self, y: int, s: str, color: int) -> None:
        w = len(s) * pyxel.FONT_WIDTH
        pyxel.text((SCREEN_W - w) // 2, y, s, color)


# ── Entry Point ────────────────────────────────────────────────────────


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
