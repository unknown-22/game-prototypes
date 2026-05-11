"""Alchemy Drop — Falling-block puzzle prototype.

Core mechanic: Stack elemental blocks near the limit, then trigger
cascading chain reactions for massive score multipliers.

Based on: game_idea_factory idea #2 (Score 31.4)
  Theme: Alchemy (synthesis)
  Hook: Gravity/collapse chain reactions, puzzle-like crumbling
  Reinterpreted from dice/bag-builder to falling-block puzzle.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import IntEnum
from typing import Final

import pyxel

# ── Constants ────────────────────────────────────────────────────────
SCREEN_W: Final = 256
SCREEN_H: Final = 256
GRID_COLS: Final = 8
GRID_ROWS: Final = 16  # rows 0-1 hidden (spawn), rows 2-15 visible
VISIBLE_OFFSET: Final = 2
CELL_SIZE: Final = 16
GRID_X: Final = 16
GRID_Y: Final = 16
PANEL_X: Final = GRID_X + GRID_COLS * CELL_SIZE + 8

DROP_BASE_SPEED: Final = 40  # frames between auto-drop steps
DROP_MIN_SPEED: Final = 6
SPEED_UP_SCORE: Final = 200  # level up every N points
SOFT_DROP_DELAY: Final = 3  # frames between soft-drop steps
CLEAR_ANIM_FRAMES: Final = 12
MATCH_MIN: Final = 3  # minimum matching run length

SCORE_PER_BLOCK: Final = 10
SOFT_DROP_BONUS: Final = 1
HARD_DROP_BONUS: Final = 2


# ── Element Types ────────────────────────────────────────────────────
class Element(IntEnum):
    FIRE = 0
    WATER = 1
    EARTH = 2
    AIR = 3
    AETHER = 4


ELEMENT_COLORS: Final = {
    Element.FIRE: 8,  # red
    Element.WATER: 12,  # blue
    Element.EARTH: 4,  # tan
    Element.AIR: 7,  # white
    Element.AETHER: 5,  # purple
}

ELEMENT_LABELS: Final = {
    Element.FIRE: "FIR",
    Element.WATER: "WTR",
    Element.EARTH: "ERT",
    Element.AIR: "AIR",
    Element.AETHER: "ATH",
}

ELEMENT_CHARS: Final = {
    Element.FIRE: "F",
    Element.WATER: "W",
    Element.EARTH: "E",
    Element.AIR: "A",
    Element.AETHER: "X",
}

ALL_ELEMENTS: Final = list(Element)


# ── Particle ─────────────────────────────────────────────────────────
@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


# ── Game ─────────────────────────────────────────────────────────────
class Game:
    """Falling-block puzzle with alchemy-themed element matching."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Alchemy Drop",
                   display_scale=3, fps=60)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        """Reset all game state for a fresh game."""
        self.grid: list[list[int | None]] = [
            [None] * GRID_COLS for _ in range(GRID_ROWS)
        ]
        self.score: int = 0
        self.level: int = 1
        self.drop_speed: int = DROP_BASE_SPEED
        self.drop_timer: int = 0
        self.soft_drop_timer: int = 0

        self.falling_type: int | None = None
        self.falling_col: int = 0
        self.falling_row: int = 0

        self.chain_mult: int = 1
        self.clearing: list[tuple[int, int]] = []
        self.clear_timer: int = 0
        self.resolving: bool = False

        self.particles: list[Particle] = []
        self.game_over: bool = False
        self.combo_text: str = ""
        self.combo_timer: int = 0
        self.speed_text: str = ""
        self.speed_timer: int = 0

        self._spawn_block()

    # ── Block Management ─────────────────────────────────────────

    def _spawn_block(self) -> None:
        """Create a new falling block at the top spawn row."""
        self.falling_type = random.choice(ALL_ELEMENTS).value
        self.falling_col = GRID_COLS // 2
        self.falling_row = 0
        self.drop_timer = 0
        self.soft_drop_timer = 0

        if self.grid[0][self.falling_col] is not None:
            self.game_over = True
            self.falling_type = None

    def _can_place(self, col: int, row: int) -> bool:
        """Check if a block can be at grid position (col, row)."""
        if col < 0 or col >= GRID_COLS:
            return False
        if row >= GRID_ROWS:
            return False
        if row < 0:
            return True
        return self.grid[row][col] is None

    def _lock_block(self) -> None:
        """Lock the falling block into the grid and start match resolution."""
        r = self.falling_row
        if r < 0:
            self.game_over = True
            return
        self.grid[r][self.falling_col] = self.falling_type
        self.falling_type = None
        self.resolving = True
        self.chain_mult = 1
        self._scan_matches()

    # ── Match Resolution ─────────────────────────────────────────

    def _scan_matches(self) -> None:
        """Find all 3+ runs in grid; start clear animation or end chain."""
        matched: set[tuple[int, int]] = set()

        # Horizontal scan
        for row in range(GRID_ROWS):
            c = 0
            while c < GRID_COLS:
                val = self.grid[row][c]
                if val is None:
                    c += 1
                    continue
                end = c + 1
                while end < GRID_COLS and self.grid[row][end] == val:
                    end += 1
                if end - c >= MATCH_MIN:
                    for mc in range(c, end):
                        matched.add((row, mc))
                c = end

        # Vertical scan
        for col in range(GRID_COLS):
            r = 0
            while r < GRID_ROWS:
                val = self.grid[r][col]
                if val is None:
                    r += 1
                    continue
                end = r + 1
                while end < GRID_ROWS and self.grid[end][col] == val:
                    end += 1
                if end - r >= MATCH_MIN:
                    for mr in range(r, end):
                        matched.add((mr, col))
                r = end

        if matched:
            self.clearing = list(matched)
            self.clear_timer = CLEAR_ANIM_FRAMES
        else:
            # No matches — chain ends, spawn next block
            self.chain_mult = 1
            self.resolving = False
            self._spawn_block()

    def _resolve_clear(self) -> None:
        """Remove matched cells, add score, spawn particles."""
        blocks = len(self.clearing)
        gain = blocks * SCORE_PER_BLOCK * self.chain_mult
        self.score += gain

        # Show combo text for chains (mult >= 2)
        if self.chain_mult >= 2:
            self.combo_text = f"x{self.chain_mult} CHAIN!"
            self.combo_timer = 45

        # Spawn particles for each cleared cell
        for r, c in self.clearing:
            elem = self.grid[r][c]
            color = ELEMENT_COLORS.get(Element(elem), 7) if elem is not None else 7
            px = GRID_X + c * CELL_SIZE + CELL_SIZE // 2
            py = GRID_Y + (r - VISIBLE_OFFSET) * CELL_SIZE + CELL_SIZE // 2
            for _ in range(4):
                self.particles.append(Particle(
                    x=float(px),
                    y=float(py),
                    vx=random.uniform(-1.5, 1.5),
                    vy=random.uniform(-2.5, -0.5),
                    life=random.randint(15, 30),
                    color=color,
                ))
            self.grid[r][c] = None

        self.clearing = []
        self.chain_mult += 1

    def _apply_gravity(self) -> bool:
        """Drop floating blocks down to fill gaps. Returns True if anything moved."""
        moved = False
        for col in range(GRID_COLS):
            write = GRID_ROWS - 1
            for read in range(GRID_ROWS - 1, -1, -1):
                if self.grid[read][col] is not None:
                    if read != write:
                        self.grid[write][col] = self.grid[read][col]
                        self.grid[read][col] = None
                        moved = True
                    write -= 1
        return moved

    # ── Update ───────────────────────────────────────────────────

    def _update_drop_speed(self) -> None:
        """Recalculate level and drop speed from score."""
        new_level = 1 + self.score // SPEED_UP_SCORE
        if new_level > self.level:
            self.level = new_level
            self.speed_text = f"LEVEL {self.level}!"
            self.speed_timer = 60
        self.drop_speed = max(DROP_MIN_SPEED, DROP_BASE_SPEED - (self.level - 1) * 3)

    def _update_particles(self) -> None:
        """Animate particles; remove expired ones."""
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.08
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _handle_input(self) -> None:
        """Process keyboard input for the falling block."""
        # Horizontal movement (button-press for discrete steps)
        if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A):
            if self._can_place(self.falling_col - 1, self.falling_row):
                self.falling_col -= 1

        if pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D):
            if self._can_place(self.falling_col + 1, self.falling_row):
                self.falling_col += 1

        # Soft drop (held down)
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            self.soft_drop_timer += 1
            if self.soft_drop_timer >= SOFT_DROP_DELAY:
                self.soft_drop_timer = 0
                if self._can_place(self.falling_col, self.falling_row + 1):
                    self.falling_row += 1
                    self.score += SOFT_DROP_BONUS
        else:
            self.soft_drop_timer = 0

        # Hard drop (instant)
        if pyxel.btnp(pyxel.KEY_SPACE):
            while self._can_place(self.falling_col, self.falling_row + 1):
                self.falling_row += 1
                self.score += HARD_DROP_BONUS
            self._lock_block()
            return

        # Auto-drop by timer
        self.drop_timer += 1
        if self.drop_timer >= self.drop_speed:
            self.drop_timer = 0
            if self._can_place(self.falling_col, self.falling_row + 1):
                self.falling_row += 1
            else:
                self._lock_block()

    def update(self) -> None:
        """Frame update: input, match resolution, particles."""
        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()
            return

        # Timed text displays
        if self.combo_timer > 0:
            self.combo_timer -= 1
        if self.speed_timer > 0:
            self.speed_timer -= 1

        self._update_particles()

        if self.game_over:
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
            return

        # Resolving: clear animation → remove → gravity → check chains
        if self.resolving:
            if self.clear_timer > 0:
                self.clear_timer -= 1
                if self.clear_timer == 0:
                    self._resolve_clear()
                    self._apply_gravity()
                    self._scan_matches()
            return

        # Normal play
        self._update_drop_speed()
        self._handle_input()

    # ── Draw ─────────────────────────────────────────────────────

    def _cell_rect(self, r: int, c: int) -> tuple[int, int]:
        """Return pixel coords for top-left of visible cell (r, c)."""
        return (
            GRID_X + c * CELL_SIZE,
            GRID_Y + (r - VISIBLE_OFFSET) * CELL_SIZE,
        )

    def _draw_grid(self) -> None:
        """Render the grid, clearing cells, and falling block."""
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                x, y = self._cell_rect(r, c)
                # Cell BG
                pyxel.rect(x, y, CELL_SIZE, CELL_SIZE, 1)

                val = self.grid[r][c]
                if val is None:
                    continue

                elem = Element(val)
                color = ELEMENT_COLORS[elem]
                is_clearing = (r, c) in self.clearing

                if is_clearing:
                    # Flash between color and white
                    blink = (pyxel.frame_count // 3) % 2 == 0
                    draw_color: int = color if blink else 7
                    pyxel.rect(x + 1, y + 1, CELL_SIZE - 2, CELL_SIZE - 2, draw_color)
                else:
                    pyxel.rect(x + 1, y + 1, CELL_SIZE - 2, CELL_SIZE - 2, color)

                # Element initial letter (small, centered)
                ch = ELEMENT_CHARS[elem]
                pyxel.text(x + 6, y + 5, ch, 0 if not is_clearing else 1)

        # Draw the active falling block (if not in resolving state)
        if self.falling_type is not None and not self.resolving:
            fr = self.falling_row
            if fr >= VISIBLE_OFFSET:
                x, y = self._cell_rect(fr, self.falling_col)
                color = ELEMENT_COLORS[Element(self.falling_type)]
                pyxel.rect(x + 1, y + 1, CELL_SIZE - 2, CELL_SIZE - 2, color)
                pyxel.rectb(x, y, CELL_SIZE, CELL_SIZE, 10)
                ch = ELEMENT_CHARS[Element(self.falling_type)]
                pyxel.text(x + 6, y + 5, ch, 0)

    def _draw_panel(self) -> None:
        """Render the info panel (right side of screen)."""
        ux = PANEL_X
        pyxel.text(ux, 16, "SCORE", 6)
        pyxel.text(ux, 24, str(self.score), 7)

        pyxel.text(ux, 38, "LEVEL", 6)
        pyxel.text(ux, 46, str(self.level), 7)

        pyxel.text(ux, 60, "NEXT", 6)
        if self.falling_type is not None:
            elem = Element(self.falling_type)
            color = ELEMENT_COLORS[elem]
            pyxel.rect(ux, 68, 14, 14, color)
            pyxel.text(ux + 4, 71, ELEMENT_CHARS[elem], 0)

        # Legend
        pyxel.text(ux, 90, "ELEMENTS", 6)
        for i, elem in enumerate(ALL_ELEMENTS):
            ey = 100 + i * 12
            pyxel.rect(ux, ey, 8, 8, ELEMENT_COLORS[elem])
            pyxel.text(ux + 10, ey, ELEMENT_LABELS[elem], ELEMENT_COLORS[elem])

    def _draw_overlays(self) -> None:
        """Render combo text, game over screen, particles."""
        # Particles
        for p in self.particles:
            if p.life > 10:
                pyxel.pset(int(p.x), int(p.y), p.color)
            else:
                pyxel.pset(int(p.x), int(p.y), 7 if p.life % 2 == 0 else p.color)

        # Chain combo popup
        if self.combo_timer > 0:
            cx = (SCREEN_W - len(self.combo_text) * 4) // 2
            cy = (SCREEN_H // 2) - 30
            flash_color: int = 10 if self.combo_timer % 6 < 3 else 8
            pyxel.text(cx, cy, self.combo_text, flash_color)

        # Level up popup
        if self.speed_timer > 0:
            tx = (SCREEN_W - len(self.speed_text) * 4) // 2
            pyxel.text(tx, SCREEN_H // 2 - 50, self.speed_text, 9)

        # Game over screen
        if self.game_over:
            pyxel.rect(44, 80, 168, 72, 0)
            pyxel.rectb(44, 80, 168, 72, 8)
            pyxel.text(68, 92, "GAME OVER", 8)
            pyxel.text(68, 108, f"SCORE: {self.score}", 7)
            pyxel.text(68, 120, f"LEVEL: {self.level}", 7)
            pyxel.text(56, 136, "PRESS R TO RETRY", 10)

    def draw(self) -> None:
        """Render the full frame."""
        pyxel.cls(0)

        self._draw_grid()
        self._draw_panel()
        self._draw_overlays()

        # Controls hint (bottom)
        hint = "ARROWS:MOVE  DOWN:FAST  SPACE:DROP  R:RETRY  Q:QUIT"
        pyxel.text(
            (SCREEN_W - len(hint) * 4) // 2,
            SCREEN_H - 8,
            hint,
            5,
        )


if __name__ == "__main__":
    Game()
