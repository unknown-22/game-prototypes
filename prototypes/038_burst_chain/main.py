"""Burst Chain — Bubble Shooter with chain-propagation popping.

Reinterpreted from game idea #1 (score 31.55): dice/bag roguelite with
"chain propagation" and "one color per turn" hooks → bubble shooter.

Genre: Bubble Shooter / Puzzle (novel for this collection — prototype #38)
Core mechanic: Shoot same-color bubbles, match 3+ to pop via BFS cluster
detection. Floating bubbles cascade down for bonus. COMBO multiplier
rewards consecutive pops. HEAT system adds risk/reward tension.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if not TYPE_CHECKING:
    import pyxel


# ── Config ──
SCREEN_W = 240
SCREEN_H = 320
COLS = 8
BUBBLE_R = 11
BUBBLE_D = BUBBLE_R * 2
CELL_SPACING = BUBBLE_D + 2  # 24
GRID_LEFT = (SCREEN_W - COLS * CELL_SPACING) // 2 + CELL_SPACING // 2
GRID_TOP = 36
SHOOTER_X = SCREEN_W // 2
SHOOTER_Y = SCREEN_H - 36
AIM_LINE_LEN = 80
INITIAL_ROWS = 5
NUM_COLORS = 5
HEAT_MAX = 100.0
HEAT_PER_POP = 2.0
HEAT_DECAY = 0.8
HEAT_DANGER = 70.0
BASE_SHOTS_PER_DROP = 8
DEATH_Y = SCREEN_H - 56
FLY_SPEED = 7.0
COLOR_VALS: tuple[int, ...] = (8, 11, 10, 6, 2)  # RED, GREEN, YELLOW, LIGHT_BLUE, PURPLE
COLOR_NAMES: tuple[str, ...] = ("RED", "GRN", "YEL", "BLU", "PUR")


class Phase(Enum):
    AIM = auto()
    FLYING = auto()
    POPPING = auto()
    DROP = auto()
    OVER = auto()


@dataclass
class Bubble:
    """Flying bubble state."""
    x: float
    y: float
    vx: float
    vy: float
    color: int


@dataclass
class FloatText:
    """Floating score/feedback text."""
    x: float
    y: float
    text: str
    color: int
    life: int
    vy: float = -1.2


@dataclass
class Particle:
    """Visual particle."""
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


class BurstChain:
    """Bubble shooter game with chain propagation."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Burst Chain", display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self._rng = random.Random()
        self.grid: list[list[int | None]] = []
        self.phase = Phase.AIM
        self.angle: float = -math.pi / 2  # straight up
        self.cur_color: int = self._rng.randint(0, NUM_COLORS - 1)
        self.next_color: int = self._rng.randint(0, NUM_COLORS - 1)
        self.flying: Bubble | None = None
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.shot_count: int = 0
        self.total_pops: int = 0
        self.texts: list[FloatText] = []
        self.particles: list[Particle] = []
        self.pop_anim: list[tuple[int, int, int]] = []  # (r, c, timer)
        self._init_grid()

    # ── Grid ──

    def _init_grid(self) -> None:
        self.grid = []
        for r in range(INITIAL_ROWS):
            row: list[int | None] = []
            for _ in range(COLS):
                row.append(self._rng.randint(0, NUM_COLORS - 1))
            self.grid.append(row)

    def _cell(self, r: int, c: int) -> int | None:
        if 0 <= r < len(self.grid) and 0 <= c < COLS and c < len(self.grid[r]):
            return self.grid[r][c]
        return None

    def _grid_xy(self, r: int, c: int) -> tuple[float, float]:
        x = GRID_LEFT + c * CELL_SPACING
        if r % 2 == 1:
            x += CELL_SPACING / 2
        y = GRID_TOP + r * (CELL_SPACING * 0.866)
        return x, y

    def _neighbors(self, r: int, c: int) -> list[tuple[int, int]]:
        """Hex neighbors for a bubble at (r, c)."""
        out: list[tuple[int, int]] = []
        # horizontal
        if c > 0:
            out.append((r, c - 1))
        if c + 1 < COLS:
            out.append((r, c + 1))
        if r % 2 == 0:
            # even row: above=odd at c-1,c; below=odd at c-1,c
            if r > 0:
                if c > 0:
                    out.append((r - 1, c - 1))
                out.append((r - 1, c))
            if r + 1 < len(self.grid):
                if c > 0:
                    out.append((r + 1, c - 1))
                out.append((r + 1, c))
        else:
            # odd row: above=even at c,c+1; below=even at c,c+1
            if r > 0:
                out.append((r - 1, c))
                if c + 1 < COLS:
                    out.append((r - 1, c + 1))
            if r + 1 < len(self.grid):
                out.append((r + 1, c))
                if c + 1 < COLS:
                    out.append((r + 1, c + 1))
        return out

    def _find_cluster(self, r: int, c: int) -> set[tuple[int, int]]:
        """BFS: all same-color bubbles connected to (r, c)."""
        color = self._cell(r, c)
        if color is None:
            return set()
        visited: set[tuple[int, int]] = {(r, c)}
        queue = [(r, c)]
        while queue:
            cr, cc = queue.pop(0)
            for nr, nc in self._neighbors(cr, cc):
                if (nr, nc) not in visited:
                    if self._cell(nr, nc) == color:
                        visited.add((nr, nc))
                        queue.append((nr, nc))
        return visited

    def _find_floating(self) -> set[tuple[int, int]]:
        """Bubbles NOT connected to any row-0 bubble (floaters)."""
        anchored: set[tuple[int, int]] = set()
        queue: list[tuple[int, int]] = []
        for c in range(COLS):
            if self._cell(0, c) is not None:
                queue.append((0, c))
                anchored.add((0, c))
        while queue:
            r, c = queue.pop(0)
            for nr, nc in self._neighbors(r, c):
                if (nr, nc) not in anchored and self._cell(nr, nc) is not None:
                    anchored.add((nr, nc))
                    queue.append((nr, nc))
        floating: set[tuple[int, int]] = set()
        for r in range(len(self.grid)):
            for c in range(COLS):
                if self._cell(r, c) is not None and (r, c) not in anchored:
                    floating.add((r, c))
        return floating

    def _snap(self, x: float, y: float) -> tuple[int, int] | None:
        """Find closest empty grid cell within snap radius."""
        best: tuple[int, int] | None = None
        best_d = BUBBLE_D + 4
        for r in range(len(self.grid)):
            for c in range(COLS):
                if c >= len(self.grid[r]):
                    continue
                if self.grid[r][c] is not None:
                    continue
                gx, gy = self._grid_xy(r, c)
                d = math.hypot(x - gx, y - gy)
                if d < best_d:
                    best_d = d
                    best = (r, c)
        return best

    def _any_below_death_line(self) -> bool:
        for r in range(len(self.grid)):
            for c in range(COLS):
                if self._cell(r, c) is not None:
                    _, gy = self._grid_xy(r, c)
                    if gy + BUBBLE_R >= DEATH_Y:
                        return True
        return False

    # ── Actions ──

    def _shoot(self) -> None:
        if self.flying is not None:
            return
        vx = math.cos(self.angle) * FLY_SPEED
        vy = math.sin(self.angle) * FLY_SPEED
        self.flying = Bubble(
            x=float(SHOOTER_X), y=float(SHOOTER_Y),
            vx=vx, vy=vy, color=self.cur_color,
        )
        self.phase = Phase.FLYING

    def _stick(self, r: int, c: int) -> None:
        """Place flying bubble at (r,c) and resolve."""
        color = self.flying.color if self.flying else self.cur_color
        # Ensure row exists and has enough columns
        while r >= len(self.grid):
            self.grid.append([None] * COLS)
        while c >= len(self.grid[r]):
            self.grid[r].append(None)
        self.grid[r][c] = color
        self.flying = None

        cluster = self._find_cluster(r, c)
        if len(cluster) >= 3:
            self._pop_cluster(cluster)
        else:
            self.combo = 0

        self._advance_round()

    def _pop_cluster(self, cluster: set[tuple[int, int]]) -> None:
        popped = len(cluster)
        # Get first position and color for effects
        first: tuple[int, int] | None = None
        cluster_color = pyxel.COLOR_WHITE
        if cluster:
            first = next(iter(cluster))
            first_r, first_c = first
            col_idx = self._cell(first_r, first_c)
            if col_idx is not None and 0 <= col_idx < len(COLOR_VALS):
                cluster_color = COLOR_VALS[col_idx]
        for rr, cc in cluster:
            self.grid[rr][cc] = None
            gx, gy = self._grid_xy(rr, cc)
            for _ in range(3):
                a = random.random() * math.pi * 2
                s = random.random() * 2 + 0.5
                self.particles.append(Particle(
                    gx, gy, math.cos(a) * s, math.sin(a) * s,
                    12, cluster_color,
                ))

        # Find and pop floaters
        floaters = self._find_floating()
        fcount = len(floaters)
        for fr, fc in floaters:
            gx, gy = self._grid_xy(fr, fc)
            self.grid[fr][fc] = None
            for _ in range(2):
                a = random.random() * math.pi * 2
                s = random.random() * 1.5 + 0.3
                self.particles.append(Particle(
                    gx, gy, math.cos(a) * s, math.sin(a) * s,
                    10, pyxel.COLOR_WHITE,
                ))

        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        mult = 1.0 + self.combo * 0.5
        gain = int((popped * 10 + fcount * 15) * mult)
        self.score += gain
        self.total_pops += popped + fcount
        self.heat = min(HEAT_MAX, self.heat + HEAT_PER_POP * (popped + fcount * 0.5))

        # Feedback text
        if first is not None:
            cx, cy = self._grid_xy(first[0], first[1])
        else:
            cx, cy = SHOOTER_X, SHOOTER_Y
        self.texts.append(FloatText(cx, cy, f"+{gain}", pyxel.COLOR_WHITE, 30))
        if self.combo > 1:
            self.texts.append(FloatText(
                cx, cy - 12, f"x{self.combo}", pyxel.COLOR_YELLOW, 25,
            ))

    def _advance_round(self) -> None:
        self.shot_count += 1
        threshold = BASE_SHOTS_PER_DROP
        if self.heat >= HEAT_DANGER:
            threshold = max(3, BASE_SHOTS_PER_DROP - int(self.heat / 15))
        if self.shot_count >= threshold:
            self._add_row()
            self.shot_count = 0
        self.heat = max(0.0, self.heat - HEAT_DECAY)
        self.cur_color = self.next_color
        self.next_color = self._rng.randint(0, NUM_COLORS - 1)
        self.phase = Phase.AIM

    def _add_row(self) -> None:
        """Insert a new row at top, pushing everything down."""
        # Check death before adding
        if self._any_below_death_line():
            self.phase = Phase.OVER
            return
        # New row inserted at index 0; existing rows shift down
        new_row: list[int | None] = [
            self._rng.randint(0, NUM_COLORS - 1) for _ in range(COLS)
        ]
        self.grid.insert(0, new_row)
        # Limit total rows
        while len(self.grid) > 16:
            self.grid.pop()
        # Check death after adding
        if self._any_below_death_line():
            self.phase = Phase.OVER

    # ── Update ──

    def update(self) -> None:
        if self.phase == Phase.OVER:
            if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
            return

        # Update texts
        for t in self.texts[:]:
            t.y += t.vy
            t.life -= 1
            if t.life <= 0:
                self.texts.remove(t)

        # Update particles
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

        if self.phase == Phase.AIM:
            self._update_aim()
        elif self.phase == Phase.FLYING:
            self._update_flying()

    def _update_aim(self) -> None:
        # Mouse aim
        if pyxel.mouse_x >= 0:
            dx = pyxel.mouse_x - SHOOTER_X
            dy = pyxel.mouse_y - SHOOTER_Y
            if abs(dx) > 2 or abs(dy) > 2:
                self.angle = math.atan2(dy, dx)
        else:
            if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
                self.angle -= 0.04
            if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
                self.angle += 0.04
        # Clamp: roughly upward
        lo = -math.pi * 0.82
        hi = -math.pi * 0.18
        self.angle = max(lo, min(hi, self.angle))

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE):
            self._shoot()

    def _update_flying(self) -> None:
        if self.flying is None:
            self.phase = Phase.AIM
            return
        f = self.flying
        f.x += f.vx
        f.y += f.vy

        # Wall bounce
        if f.x - BUBBLE_R < 0:
            f.x = float(BUBBLE_R)
            f.vx = abs(f.vx)
        elif f.x + BUBBLE_R > SCREEN_W:
            f.x = float(SCREEN_W - BUBBLE_R)
            f.vx = -abs(f.vx)

        # Top: snap to grid
        if f.y - BUBBLE_R <= GRID_TOP:
            snap = self._snap(f.x, GRID_TOP + BUBBLE_R)
            if snap is not None:
                self._stick(snap[0], snap[1])
            else:
                # No spot — just stick at closest valid position in top row
                col = int((f.x - GRID_LEFT) / CELL_SPACING + 0.5)
                col = max(0, min(COLS - 1, col))
                if len(self.grid) == 0:
                    self.grid.append([None] * COLS)
                if self.grid[0][col] is None:
                    self._stick(0, col)
                else:
                    # find any empty in top row
                    for cc in range(COLS):
                        if self.grid[0][cc] is None:
                            self._stick(0, cc)
                            return
                    # all full: game over
                    self.phase = Phase.OVER
            return

        # Hit existing bubbles
        snap = self._snap(f.x, f.y)
        if snap is not None:
            self._stick(snap[0], snap[1])

    # ── Draw ──

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        # Grid bubbles
        for r in range(len(self.grid)):
            for c in range(COLS):
                if c < len(self.grid[r]) and self.grid[r][c] is not None:
                    gx, gy = self._grid_xy(r, c)
                    self._draw_bubble(gx, gy, self.grid[r][c])

        # Flying bubble
        if self.flying and self.phase == Phase.FLYING:
            self._draw_bubble(self.flying.x, self.flying.y, self.flying.color)

        # Aim line
        if self.phase == Phase.AIM:
            ax = SHOOTER_X + math.cos(self.angle) * AIM_LINE_LEN
            ay = SHOOTER_Y + math.sin(self.angle) * AIM_LINE_LEN
            pyxel.line(SHOOTER_X, SHOOTER_Y, ax, ay, pyxel.COLOR_WHITE)
            # Show cur/next bubbles at shooter area
            self._draw_bubble(SHOOTER_X - 26, SHOOTER_Y, self.cur_color)
            pyxel.text(SHOOTER_X - 26 - 8, SHOOTER_Y - 18, "NOW", pyxel.COLOR_WHITE)
            self._draw_bubble(SHOOTER_X + 26, SHOOTER_Y, self.next_color)
            pyxel.text(SHOOTER_X + 26 - 8, SHOOTER_Y - 18, "NXT", pyxel.COLOR_GRAY)

        # Shooter base
        pyxel.circb(SHOOTER_X, SHOOTER_Y, BUBBLE_R + 3, pyxel.COLOR_GRAY)

        # Death line
        pyxel.line(0, DEATH_Y, SCREEN_W, DEATH_Y, pyxel.COLOR_RED)

        # Particles
        for p in self.particles:
            c = p.color if p.color >= 0 else pyxel.COLOR_WHITE
            pyxel.pset(int(p.x), int(p.y), c)

        # Floating texts
        for t in self.texts:
            pyxel.text(int(t.x) - len(t.text) * 2, int(t.y), t.text, t.color)

        # HUD
        pyxel.text(4, 2, f"SCORE:{self.score}", pyxel.COLOR_WHITE)
        pyxel.text(4, 10, f"CMB:{self.combo}", pyxel.COLOR_YELLOW if self.combo > 1 else pyxel.COLOR_GRAY)

        # Heat bar
        bw, bh = 56, 4
        bx = SCREEN_W - bw - 4
        by = 6
        pyxel.rect(bx, by, bw, bh, pyxel.COLOR_GRAY)
        hw = int(bw * self.heat / HEAT_MAX)
        hc = pyxel.COLOR_GREEN if self.heat < HEAT_DANGER else pyxel.COLOR_ORANGE
        if self.heat >= HEAT_MAX:
            hc = pyxel.COLOR_RED
        pyxel.rect(bx, by, hw, bh, hc)
        pyxel.text(bx - 18, by - 1, "HT", pyxel.COLOR_GRAY)

        # Game over overlay
        if self.phase == Phase.OVER:
            pyxel.rect(0, SCREEN_H // 2 - 20, SCREEN_W, 50, pyxel.COLOR_BLACK)
            pyxel.text(SCREEN_W // 2 - 28, SCREEN_H // 2 - 12, "GAME OVER", pyxel.COLOR_RED)
            pyxel.text(SCREEN_W // 2 - 36, SCREEN_H // 2 + 2, f"SCORE: {self.score}", pyxel.COLOR_WHITE)
            pyxel.text(SCREEN_W // 2 - 48, SCREEN_H // 2 + 14, "R/SPACE: RETRY", pyxel.COLOR_GRAY)

    def _draw_bubble(self, x: float, y: float, color_idx: object) -> None:
        """Draw a single bubble."""
        c = int(color_idx) if isinstance(color_idx, int) else 0
        if 0 <= c < len(COLOR_VALS):
            col = COLOR_VALS[c]
            ix, iy = int(x), int(y)
            pyxel.circ(ix, iy, BUBBLE_R, col)
            pyxel.circ(ix, iy, BUBBLE_R - 1, col)
            # highlight
            pyxel.circ(ix - BUBBLE_R // 3, iy - BUBBLE_R // 3, BUBBLE_R // 4, pyxel.COLOR_WHITE)


def main() -> None:
    BurstChain()


if __name__ == "__main__":
    main()
