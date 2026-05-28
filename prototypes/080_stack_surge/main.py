"""080_stack_surge - Stack Surge

Jenga-style tower pulling game with color-match COMBO and CA instability spread.
Pull same-color blocks to build COMBO. COMBO >= 3 triggers SYNTHESIS
(stabilizes all unstable blocks + bonus score). Wrong-color pull destabilizes
adjacent blocks (CA spread) and resets COMBO. Too many unstable blocks -> collapse.

面白い瞬間 is when same-color blocks are pulled consecutively, COMBO hits 3,
SYNTHESIS triggers, and all unstable blocks stabilize at once for massive score.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import IntEnum, auto
from pathlib import Path

import pyxel

# ── Constants ──────────────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
FPS = 30
DISPLAY_SCALE = 3

# Tower layout
TOWER_TOP = 20
TOWER_LEFT = 80
TOWER_RIGHT = 240
BLOCK_W = 48
BLOCK_H = 20
BLOCK_GAP = 2
ROWS_VISIBLE = 8
MAX_ROWS = 12
BLOCK_COLS = 3

# Game balance
INITIAL_ROWS = 8
SYNTHESIS_THRESHOLD = 3
SYNTHESIS_BONUS_PER_COMBO = 100
BASE_SCORE = 10
COLLAPSE_RATIO = 0.5
HEAT_PER_UNSTABLE_PULL = 1
MAX_HEAT = 10

# Animation
UNSTABLE_FLASH_INTERVAL = 15
SYNTHESIS_FLASH_FRAMES = 8
COLLAPSE_SHAKE_FRAMES = 15
COLLAPSE_PARTICLES_PER_BLOCK = 8
SYNTHESIS_PARTICLES_PER_BLOCK = 12

# Particles
PARTICLE_LIFE_MIN = 8
PARTICLE_LIFE_MAX = 16

# Colors
COL_BLACK = 0
COL_NAVY = 1
COL_PURPLE = 2
COL_GREEN = 3
COL_BROWN = 4
COL_DARK_BLUE = 5
COL_LIGHT_BLUE = 6
COL_WHITE = 7
COL_RED = 8
COL_ORANGE = 9
COL_YELLOW = 10
COL_LIME = 11
COL_CYAN = 12
COL_GRAY = 13
COL_PINK = 14
COL_PEACH = 15

BLOCK_COLORS: tuple[int, ...] = (COL_RED, COL_GREEN, COL_YELLOW, COL_LIGHT_BLUE)
COLOR_NAMES: tuple[str, ...] = ("RED", "GREEN", "YELLOW", "BLUE")

FONT_PATH = Path(__file__).with_name("k8x12.bdf")


# ── Enums ──────────────────────────────────────────────────────────────────────
class BlockState(IntEnum):
    STABLE = auto()
    UNSTABLE = auto()
    GONE = auto()


class Phase(IntEnum):
    TITLE = 0
    PLAYING = 1
    SYNTHESIS_ANIM = 2
    COLLAPSE_ANIM = 3
    GAME_OVER = 4


# ── Data Classes ───────────────────────────────────────────────────────────────
@dataclass
class Block:
    color: int
    state: BlockState
    row: int
    col: int


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


# ── Game ───────────────────────────────────────────────────────────────────────
class Game:
    def __init__(self) -> None:
        pyxel.init(
            SCREEN_W, SCREEN_H,
            title="Stack Surge",
            display_scale=DISPLAY_SCALE,
            fps=FPS,
        )
        self._font: pyxel.Font | None = None
        if FONT_PATH.exists():
            self._font = pyxel.Font(str(FONT_PATH))
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── Init / Reset ───────────────────────────────────────────────────────
    def reset(self) -> None:
        self._rng = random.Random()
        self.phase: Phase = Phase.TITLE
        self.rows: list[list[Block]] = []
        self.score: int = 0
        self.best_score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.last_color: int = -1
        self.heat: int = 0
        self.blocks_pulled: int = 0
        self.particles: list[Particle] = []
        self.synthesis_flash: int = 0
        self.collapse_anim: int = 0
        self._shake_frames: int = 0
        self._frame_count: int = 0

    # ── State Init (callable from tests) ───────────────────────────────────
    def _init_state(self) -> None:
        self.rows = []
        for row_idx in range(INITIAL_ROWS):
            new_row: list[Block] = []
            for col_idx in range(BLOCK_COLS):
                color = self._rng.choice(BLOCK_COLORS)
                new_row.append(Block(color=color, state=BlockState.STABLE, row=row_idx, col=col_idx))
            self.rows.append(new_row)

    # ── Input ──────────────────────────────────────────────────────────────
    @staticmethod
    def _read_confirm() -> bool:
        return pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN)

    @staticmethod
    def _read_click() -> bool:
        return pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)

    # ── Block Hit Detection ────────────────────────────────────────────────
    def _block_at(self, mx: int, my: int) -> tuple[int, int] | None:
        row = (my - TOWER_TOP) // (BLOCK_H + BLOCK_GAP)
        col = (mx - TOWER_LEFT) // (BLOCK_W + BLOCK_GAP)
        if col < 0 or col >= BLOCK_COLS:
            return None
        if row < 0 or row >= len(self.rows):
            return None
        block = self.rows[row][col]
        if block.state == BlockState.GONE:
            return None
        return (row, col)

    # ── Pull Mechanics ─────────────────────────────────────────────────────
    def _pull_block(self, row: int, col: int) -> None:
        block = self.rows[row][col]
        was_unstable = block.state == BlockState.UNSTABLE
        block.state = BlockState.GONE
        self.blocks_pulled += 1

        if was_unstable:
            self.heat += HEAT_PER_UNSTABLE_PULL

        # COMBO logic
        if self.last_color == block.color:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
        else:
            if self.last_color != -1:
                self._spread_instability(row, col)
            self.combo = 0
        self.last_color = block.color

        # SYNTHESIS
        if self.combo >= SYNTHESIS_THRESHOLD:
            stabilized = 0
            for r in self.rows:
                for b in r:
                    if b.state == BlockState.UNSTABLE:
                        b.state = BlockState.STABLE
                        self._spawn_synthesis_particles(b)
                        stabilized += 1
            bonus = self.combo * SYNTHESIS_BONUS_PER_COMBO
            self.score += bonus
            self.synthesis_flash = SYNTHESIS_FLASH_FRAMES

        # Score
        multiplier = 1 + self.combo
        self.score += BASE_SCORE * multiplier

        # Compact & add row
        self._compact_tower()
        self._add_top_row()

        # Check collapse
        if self._check_collapse():
            self._spawn_collapse_particles()
            self.collapse_anim = COLLAPSE_SHAKE_FRAMES
            self.phase = Phase.COLLAPSE_ANIM
            if self.score > self.best_score:
                self.best_score = self.score

    # ── CA Instability Spread ──────────────────────────────────────────────
    def _spread_instability(self, row: int, col: int) -> None:
        neighbors: list[tuple[int, int]] = [
            (row, col - 1),
            (row, col + 1),
            (row - 1, col),
            (row + 1, col),
        ]
        for nr, nc in neighbors:
            if 0 <= nr < len(self.rows) and 0 <= nc < BLOCK_COLS:
                neighbor = self.rows[nr][nc]
                if neighbor.state == BlockState.STABLE:
                    neighbor.state = BlockState.UNSTABLE

    # ── Tower Compaction ───────────────────────────────────────────────────
    def _compact_tower(self) -> None:
        self.rows = [r for r in self.rows if any(b.state != BlockState.GONE for b in r)]

    def _add_top_row(self) -> None:
        new_row: list[Block] = []
        for col_idx in range(BLOCK_COLS):
            color = self._rng.choice(BLOCK_COLORS)
            new_row.append(Block(color=color, state=BlockState.STABLE, row=0, col=col_idx))
        self.rows.append(new_row)

        # Re-number rows
        for i, r in enumerate(self.rows):
            for b in r:
                b.row = i

        # Cap max rows (scroll from bottom)
        while len(self.rows) > MAX_ROWS:
            self.rows.pop(0)
            for i, r in enumerate(self.rows):
                for b in r:
                    b.row = i

    # ── Collapse Detection ─────────────────────────────────────────────────
    def _count_unstable_ratio(self) -> float:
        total = sum(1 for r in self.rows for b in r if b.state != BlockState.GONE)
        unstable = sum(1 for r in self.rows for b in r if b.state == BlockState.UNSTABLE)
        if total == 0:
            return 0.0
        return unstable / total

    def _check_collapse(self) -> bool:
        return self._count_unstable_ratio() > COLLAPSE_RATIO

    # ── Particles ──────────────────────────────────────────────────────────
    def _spawn_synthesis_particles(self, block: Block) -> None:
        bx = TOWER_LEFT + block.col * (BLOCK_W + BLOCK_GAP) + BLOCK_W / 2
        by = TOWER_TOP + block.row * (BLOCK_H + BLOCK_GAP) + BLOCK_H / 2
        for _ in range(SYNTHESIS_PARTICLES_PER_BLOCK):
            angle = self._rng.uniform(0, 6.283)
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(Particle(
                x=bx,
                y=by,
                vx=0.0,
                vy=0.0,
                life=self._rng.randint(PARTICLE_LIFE_MIN, PARTICLE_LIFE_MAX),
                color=COL_YELLOW,
            ))
            self.particles[-1].vx = math.cos(angle) * speed
            self.particles[-1].vy = math.sin(angle) * speed

    def _spawn_collapse_particles(self) -> None:
        for r in self.rows:
            for b in r:
                if b.state == BlockState.GONE:
                    continue
                bx = TOWER_LEFT + b.col * (BLOCK_W + BLOCK_GAP) + BLOCK_W / 2
                by = TOWER_TOP + b.row * (BLOCK_H + BLOCK_GAP) + BLOCK_H / 2
                for _ in range(COLLAPSE_PARTICLES_PER_BLOCK):
                    self.particles.append(Particle(
                        x=bx,
                        y=by,
                        vx=self._rng.uniform(-2.0, 2.0),
                        vy=self._rng.uniform(-4.0, -1.0),
                        life=self._rng.randint(PARTICLE_LIFE_MIN, PARTICLE_LIFE_MAX),
                        color=COL_ORANGE,
                    ))

    def _update_particles(self) -> None:
        survived: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.15  # gravity
            p.life -= 1
            if p.life > 0:
                survived.append(p)
        self.particles = survived

    # ── Text Helpers ───────────────────────────────────────────────────────
    def _text_center(self, s: str, y: int, col: int) -> None:
        if self._font is not None:
            w = self._font.text_width(s)
            x = (SCREEN_W - w) // 2
            pyxel.text(x + 1, y + 1, s, COL_BLACK, self._font)
            pyxel.text(x, y, s, col, self._font)
        else:
            pyxel.text((SCREEN_W - len(s) * 4) // 2, y, s, col)

    def _text(self, s: str, x: int, y: int, col: int) -> None:
        if self._font is not None:
            pyxel.text(x + 1, y + 1, s, COL_BLACK, self._font)
            pyxel.text(x, y, s, col, self._font)
        else:
            pyxel.text(x, y, s, col)

    # ── Update ─────────────────────────────────────────────────────────────
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if self._read_confirm():
                self._init_state()
                self.score = 0
                self.combo = 0
                self.max_combo = 0
                self.last_color = -1
                self.heat = 0
                self.blocks_pulled = 0
                self.particles.clear()
                self.synthesis_flash = 0
                self.collapse_anim = 0
                self._shake_frames = 0
                self.phase = Phase.PLAYING
            return

        if self.phase == Phase.GAME_OVER:
            if self._read_confirm():
                self._init_state()
                self.score = 0
                self.combo = 0
                self.max_combo = 0
                self.last_color = -1
                self.heat = 0
                self.blocks_pulled = 0
                self.particles.clear()
                self.synthesis_flash = 0
                self.collapse_anim = 0
                self._shake_frames = 0
                self.phase = Phase.PLAYING
            return

        if self.phase == Phase.COLLAPSE_ANIM:
            self.collapse_anim -= 1
            self._update_particles()
            if self.collapse_anim <= 0:
                self.phase = Phase.GAME_OVER
            return

        # ── PLAYING ──
        self._frame_count += 1

        if self.synthesis_flash > 0:
            self.synthesis_flash -= 1
            self._update_particles()
            return  # pause gameplay during synthesis flash

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            clicked = self._block_at(pyxel.mouse_x, pyxel.mouse_y)
            if clicked is not None:
                self._pull_block(*clicked)

        self._update_particles()

    # ── Draw ───────────────────────────────────────────────────────────────
    def draw(self) -> None:
        pyxel.cls(COL_NAVY)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        # Screen shake
        shake_x = shake_y = 0
        if self._shake_frames > 0:
            self._shake_frames -= 1
            shake_x = self._rng.randint(-3, 3)
            shake_y = self._rng.randint(-3, 3)
        pyxel.camera(shake_x, shake_y)

        self._draw_tower()
        self._draw_particles()
        self._draw_hud()

        pyxel.camera(0, 0)

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        elif self.phase == Phase.COLLAPSE_ANIM:
            # Collapse anim draws tower + particles too during shake
            pyxel.camera(self._rng.randint(-4, 4), self._rng.randint(-4, 4))

    def _draw_title(self) -> None:
        self._text_center("STACK SURGE", 40, COL_CYAN)
        self._text_center("Pull same-color blocks to", 90, COL_WHITE)
        self._text_center("build COMBO!", 104, COL_WHITE)
        self._text_center("COMBO x3+ = SYNTHESIS!", 130, COL_YELLOW)
        self._text_center("Wrong color = instability", 150, COL_PINK)
        self._text_center("Click a block to pull it out", 180, COL_GRAY)
        if self.best_score > 0:
            self._text_center(f"Best Score: {self.best_score}", 210, COL_ORANGE)
        self._text_center("Click or SPACE to Start", 230, COL_LIME)

    def _draw_game_over(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, COL_BLACK)
        self._text_center("TOWER COLLAPSED!", 60, COL_RED)
        self._text_center(f"Final Score: {self.score}", 100, COL_WHITE)
        self._text_center(f"Max Combo: x{self.max_combo}", 120, COL_CYAN)
        self._text_center(f"Blocks Pulled: {self.blocks_pulled}", 140, COL_GRAY)
        if self.best_score > 0:
            self._text_center(f"Best Score: {self.best_score}", 170, COL_YELLOW)
        self._text_center("Click or SPACE to Retry", 210, COL_LIME)

    # ── Tower Drawing ──────────────────────────────────────────────────────
    def _draw_tower(self) -> None:
        for r in self.rows:
            for b in r:
                if b.state == BlockState.GONE:
                    continue
                self._draw_block(b)

    def _draw_block(self, block: Block) -> None:
        bx = TOWER_LEFT + block.col * (BLOCK_W + BLOCK_GAP)
        by = TOWER_TOP + block.row * (BLOCK_H + BLOCK_GAP)

        draw_color = block.color

        if block.state == BlockState.UNSTABLE:
            flash = (self._frame_count // UNSTABLE_FLASH_INTERVAL) % 2 == 0
            draw_color = block.color if flash else COL_GRAY
            if self.synthesis_flash > 0:
                draw_color = COL_WHITE

        pyxel.rect(bx, by, BLOCK_W, BLOCK_H, draw_color)

        border_color = COL_WHITE if block.state == BlockState.STABLE else COL_PINK
        if self.synthesis_flash > 0 and block.state == BlockState.UNSTABLE:
            border_color = COL_WHITE
        pyxel.rectb(bx, by, BLOCK_W, BLOCK_H, border_color)

        # Highlight on hover
        if self.phase == Phase.PLAYING:
            hovered = self._block_at(pyxel.mouse_x, pyxel.mouse_y)
            if hovered is not None:
                hr, hc = hovered
                if hr == block.row and hc == block.col:
                    pyxel.rectb(bx - 1, by - 1, BLOCK_W + 2, BLOCK_H + 2, COL_YELLOW)

    # ── Particles Drawing ──────────────────────────────────────────────────
    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / PARTICLE_LIFE_MAX
            radius = max(1, int(2 * alpha))
            col = p.color if self._frame_count % 2 == 0 else COL_WHITE
            pyxel.circ(int(p.x), int(p.y), radius, col)

    # ── HUD Drawing ────────────────────────────────────────────────────────
    def _draw_hud(self) -> None:
        self._text(f"SCORE: {self.score}", 4, 4, COL_WHITE)

        # Last color indicator
        if self.last_color >= 0:
            pyxel.rect(4, 16, 8, 8, self.last_color)

        # Combo
        if self.combo > 0:
            self._text(f"COMBO: x{self.combo}", SCREEN_W // 2 - 30, 4, COL_CYAN)

        # Max combo
        if self.max_combo > 0:
            self._text(f"MAX: x{self.max_combo}", SCREEN_W - 70, 4, COL_GRAY)

        # Heat bar
        bar_w = 60
        bar_h = 4
        bar_x = 4
        bar_y = SCREEN_H - 16
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, COL_WHITE)
        ratio = min(1.0, self.heat / MAX_HEAT)
        fill_w = int(bar_w * ratio)
        bar_col = COL_GREEN if ratio < 0.5 else (COL_YELLOW if ratio < 0.8 else COL_RED)
        pyxel.rect(bar_x, bar_y, fill_w, bar_h, bar_col)
        self._text("HEAT", bar_x + bar_w + 4, bar_y - 1, COL_GRAY)

        # Instability ratio
        ratio_unstable = self._count_unstable_ratio()
        danger_col = COL_RED if ratio_unstable > 0.3 else COL_GREEN
        self._text(f"UNSTABLE: {ratio_unstable:.0%}", SCREEN_W - 90, SCREEN_H - 16, danger_col)

        # SYNTHESIS flash overlay
        if self.synthesis_flash > 0:
            alpha_flash = self.synthesis_flash / SYNTHESIS_FLASH_FRAMES
            flash_col = COL_YELLOW if alpha_flash > 0.5 else COL_WHITE
            self._text_center(f"SYNTHESIS! +{self.combo * SYNTHESIS_BONUS_PER_COMBO}", 60, flash_col)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
