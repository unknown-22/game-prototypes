"""099_harvest_chain -- Color-Match Farming Chain Harvest Prototype

The most fun moment:
  作物をギリギリまで増やして、一気に巨大チェーンで収穫するのが気持ちいい
  (Let crops multiply to the brink, then harvest a massive connected cluster for a huge COMBO)

Core loop: Click on grid cells to harvest connected same-color crops via BFS flood-fill.
CA spread increases crop density every turn. Bigger clusters = higher score.
Same-color consecutive harvests build COMBO. COMBO >= 4 triggers SUPER MODE
(harvests ALL crops of that color regardless of connectivity).
Grid >85% full = game over (overgrowth).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path

import pyxel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCREEN_W = 320
SCREEN_H = 240

COLS = 8
ROWS = 6
CELL_SIZE = 30
GRID_W = COLS * CELL_SIZE  # 240
GRID_H = ROWS * CELL_SIZE  # 180
GRID_OX = (SCREEN_W - GRID_W) // 2  # 40
GRID_OY = (SCREEN_H - GRID_H) // 2  # 30

# pyxel palette ints
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

CROP_COLORS = [RED, GREEN, DARK_BLUE, YELLOW]  # 8, 3, 5, 10
CROP_NAMES = ["TOMATO", "LETTUCE", "BERRY", "CORN"]

SUPER_COMBO = 4
OVERGROWTH_THRESHOLD = 0.85
INITIAL_CROPS = 12
SEEDS_PER_TURN = 2
SPREAD_CHANCE = 0.5

DIRS_4 = [(0, -1), (0, 1), (-1, 0), (1, 0)]

FONT_PATH = Path(__file__).with_name("k8x12.bdf")


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


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    """Core game logic. Headless-testable by using Game.__new__ bypass."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="099 Harvest Chain", display_scale=2)
        if FONT_PATH.exists():
            pyxel.load(str(FONT_PATH))
        pyxel.mouse(True)
        self._rng: random.Random = random.Random()
        self._init_state()
        pyxel.run(self._update, self._draw)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def _init_state(self) -> None:
        """Initialize all state variables. Callable from headless tests."""
        self.phase: str = "title"
        self.grid: list[list[int]] = [[0] * COLS for _ in range(ROWS)]
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.last_color: int = 0  # 0 = none yet
        self.super_mode: bool = False
        self.game_over: bool = False
        self.particles: list[Particle] = []
        self._turn_count: int = 0

    def reset(self) -> None:
        """Reset game for a new play."""
        self._init_state()
        self._place_initial_crops()

    def _place_initial_crops(self) -> None:
        """Place INITIAL_CROPS random crops on the grid."""
        empty_cells = [(c, r) for r in range(ROWS) for c in range(COLS)]
        for _ in range(INITIAL_CROPS):
            if not empty_cells:
                break
            idx = self._rng.randint(0, len(empty_cells) - 1)
            col, row = empty_cells.pop(idx)
            self.grid[row][col] = self._rng.choice(CROP_COLORS)

    # ------------------------------------------------------------------
    # Testable logic (no pyxel dependency)
    # ------------------------------------------------------------------

    def _bfs_cluster(self, col: int, row: int, color: int) -> set[tuple[int, int]]:
        """BFS flood-fill: 4-connected same-color crops from (col, row)."""
        if self.grid[row][col] != color or color == 0:
            return set()
        visited: set[tuple[int, int]] = {(col, row)}
        queue: list[tuple[int, int]] = [(col, row)]
        while queue:
            cc, rr = queue.pop()
            for dc, dr in DIRS_4:
                nc, nr = cc + dc, rr + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS:
                    if (nc, nr) not in visited and self.grid[nr][nc] == color:
                        visited.add((nc, nr))
                        queue.append((nc, nr))
        return visited

    def _count_occupied(self) -> int:
        """Count number of occupied cells in the grid."""
        return sum(1 for row in self.grid for cell in row if cell != 0)

    def _check_overgrowth(self) -> bool:
        """Returns True if occupied/total > OVERGROWTH_THRESHOLD."""
        total = COLS * ROWS
        occ = self._count_occupied()
        return occ / total > OVERGROWTH_THRESHOLD

    def _compute_score(self, cluster_size: int) -> int:
        """Score = cluster_size * (1 + max(0, combo-1) * 0.5).  Uses pre-update combo."""
        mult = 1.0 + max(0, self.combo - 1) * 0.5
        return int(cluster_size * mult)

    def _ca_spread(self) -> list[tuple[int, int, int]]:
        """For each remaining crop, SPREAD_CHANCE to spread to empty 4-dir neighbors.
        Returns list of (col, row, color) for newly added crops."""
        new_crops: list[tuple[int, int, int]] = []
        for row in range(ROWS):
            for col in range(COLS):
                c = self.grid[row][col]
                if c == 0:
                    continue
                for dc, dr in DIRS_4:
                    nc, nr = col + dc, row + dr
                    if 0 <= nc < COLS and 0 <= nr < ROWS and self.grid[nr][nc] == 0:
                        if self._rng.random() < SPREAD_CHANCE:
                            self.grid[nr][nc] = c
                            new_crops.append((nc, nr, c))
        return new_crops

    def _spawn_seeds(self, count: int) -> int:
        """Spawn `count` random crops in empty cells. Returns number actually spawned."""
        empty_cells = [(c, r) for r in range(ROWS) for c in range(COLS) if self.grid[r][c] == 0]
        spawned = 0
        for _ in range(count):
            if not empty_cells:
                break
            idx = self._rng.randint(0, len(empty_cells) - 1)
            col, row = empty_cells.pop(idx)
            self.grid[row][col] = self._rng.choice(CROP_COLORS)
            spawned += 1
        return spawned

    def _harvest(self, col: int, row: int) -> int:
        """Main harvest logic. Returns cluster size (0 if empty cell).

        Steps: BFS cluster → score (pre-combo) → update combo →
        super-mode check → remove crops → particles → CA spread →
        seeds → overgrowth check.
        """
        color = self.grid[row][col]
        if color == 0:
            return 0

        # 1. Compute cluster BEFORE clearing (BFS flood-fill)
        cluster = self._bfs_cluster(col, row, color)

        # Super mode: harvest ALL crops of that color, not just connected
        if self.super_mode:
            for rr in range(ROWS):
                for cc in range(COLS):
                    if self.grid[rr][cc] == color:
                        cluster.add((cc, rr))
        cluster_size = len(cluster)

        # 2. Score (uses combo value BEFORE the update below)
        gained = self._compute_score(cluster_size)
        self.score += gained

        # 3. Update combo (same-color chain check)
        if color == self.last_color:
            self.combo += 1
        else:
            self.combo = 1
        self.last_color = color

        # 4. Track max combo
        if self.combo > self.max_combo:
            self.max_combo = self.combo

        # 5. Super mode activation (for NEXT harvest)
        self.super_mode = self.combo >= SUPER_COMBO

        # 6. Remove harvested crops
        for cc, rr in cluster:
            self.grid[rr][cc] = 0

        # 7. Particles
        self._spawn_harvest_particles(cluster, color)

        # 8. CA spread
        self._ca_spread()

        # 9. New seeds
        self._spawn_seeds(SEEDS_PER_TURN)

        # 10. Overgrowth check
        if self._check_overgrowth():
            self.game_over = True

        self._turn_count += 1
        return cluster_size

    def _spawn_harvest_particles(
        self, cluster: set[tuple[int, int]], color: int
    ) -> None:
        """Spawn burst particles for each harvested cell."""
        for cc, rr in cluster:
            px = GRID_OX + cc * CELL_SIZE + CELL_SIZE // 2
            py = GRID_OY + rr * CELL_SIZE + CELL_SIZE // 2
            count = self._rng.randint(5, 8)
            for _ in range(count):
                angle = self._rng.uniform(0, math.pi * 2)
                speed = self._rng.uniform(0.5, 2.5)
                self.particles.append(
                    Particle(
                        x=px,
                        y=py,
                        vx=math.cos(angle) * speed,
                        vy=math.sin(angle) * speed,
                        life=self._rng.randint(12, 22),
                        color=color,
                    )
                )

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def _update(self) -> None:
        if self.phase == "title":
            self._update_title()
        elif self.phase == "playing":
            self._update_playing()
        elif self.phase == "game_over":
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = "playing"

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = "playing"

    def _update_playing(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            col = (mx - GRID_OX) // CELL_SIZE
            row = (my - GRID_OY) // CELL_SIZE
            if 0 <= col < COLS and 0 <= row < ROWS:
                self._harvest(col, row)
                if self.game_over:
                    self.phase = "game_over"

        self._update_particles()

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vx *= 0.96
            p.vy *= 0.96
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def _draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == "title":
            self._draw_title()
        elif self.phase == "playing":
            self._draw_playing()
        elif self.phase == "game_over":
            self._draw_game_over()

    def _draw_grid_bg(self) -> None:
        """Draw the grid background."""
        pyxel.rect(GRID_OX - 1, GRID_OY - 1, GRID_W + 2, GRID_H + 2, WHITE)
        pyxel.rect(GRID_OX, GRID_OY, GRID_W, GRID_H, DARK_BLUE)
        for row in range(ROWS):
            for col in range(COLS):
                cx = GRID_OX + col * CELL_SIZE + 1
                cy = GRID_OY + row * CELL_SIZE + 1
                pyxel.rect(cx, cy, CELL_SIZE - 2, CELL_SIZE - 2, BROWN)

    def _draw_crops(self) -> None:
        """Draw all crops on the grid."""
        for row in range(ROWS):
            for col in range(COLS):
                c = self.grid[row][col]
                if c == 0:
                    continue
                cx = GRID_OX + col * CELL_SIZE + 2
                cy = GRID_OY + row * CELL_SIZE + 2
                size = CELL_SIZE - 4
                # Crop body
                pyxel.rect(cx, cy, size, size, c)
                # Border
                if self.super_mode:
                    pyxel.rectb(cx, cy, size, size, YELLOW)
                else:
                    pyxel.rectb(cx, cy, size, size, WHITE)
                # Crop icon
                self._draw_crop_icon(cx + size // 2, cy + size // 2, c)

    def _draw_crop_icon(self, icx: int, icy: int, color: int) -> None:
        """Draw a small distinguishing icon inside a crop cell."""
        if color == RED:  # tomato: circle
            pyxel.circ(icx, icy, 4, WHITE)
        elif color == GREEN:  # lettuce: triangle
            pyxel.tri(icx, icy - 4, icx - 4, icy + 4, icx + 4, icy + 4, WHITE)
        elif color == DARK_BLUE:  # berry: diamond
            pyxel.line(icx, icy - 4, icx + 4, icy, WHITE)
            pyxel.line(icx + 4, icy, icx, icy + 4, WHITE)
            pyxel.line(icx, icy + 4, icx - 4, icy, WHITE)
            pyxel.line(icx - 4, icy, icx, icy - 4, WHITE)
        elif color == YELLOW:  # corn: star/cross
            pyxel.line(icx - 3, icy - 3, icx + 3, icy + 3, BROWN)
            pyxel.line(icx + 3, icy - 3, icx - 3, icy + 3, BROWN)
            pyxel.line(icx, icy - 4, icx, icy + 4, BROWN)
            pyxel.line(icx - 4, icy, icx + 4, icy, BROWN)

    def _draw_particles(self) -> None:
        """Draw harvest burst particles."""
        for p in self.particles:
            alpha = p.life / 25.0
            c = p.color if alpha > 0.3 else GRAY
            pyxel.rect(int(p.x), int(p.y), 2, 2, c)

    def _draw_ui(self) -> None:
        """Draw HUD: fill% bar, score, combo, super indicator."""
        # Fill % bar (top-left)
        occupied = self._count_occupied()
        total = COLS * ROWS
        ratio = occupied / total
        bar_x = 5
        bar_y = 5
        bar_w = 80
        bar_h = 8
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, DARK_BLUE)
        fill_w = int(bar_w * ratio)
        bar_color = GREEN if ratio < 0.6 else (ORANGE if ratio < 0.85 else RED)
        pyxel.rect(bar_x, bar_y, fill_w, bar_h, bar_color)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        pyxel.text(bar_x + bar_w + 3, bar_y, f"{int(ratio * 100)}%", WHITE)

        # Score (top-center)
        score_text = f"SCORE:{self.score}"
        tw = len(score_text) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 5, score_text, WHITE)

        # COMBO (top-right)
        combo_text = f"COMBO:{self.combo}"
        cw = len(combo_text) * 4
        if self.combo >= SUPER_COMBO:
            cc = YELLOW
        elif self.combo >= 2:
            cc = ORANGE
        else:
            cc = WHITE
        pyxel.text(SCREEN_W - cw - 5, 5, combo_text, cc)

        # SUPER MODE indicator
        if self.super_mode:
            super_text = "SUPER!"
            sw = len(super_text) * 4
            sx = SCREEN_W - sw - 5
            flash = (pyxel.frame_count // 4) % 2 == 0
            if flash:
                pyxel.text(sx, 18, super_text, YELLOW)

        # Hint (bottom)
        if pyxel.frame_count % 60 < 30 and self._turn_count == 0:
            hx = GRID_OX
            hy = GRID_OY + GRID_H + 4
            pyxel.text(hx, hy, "Click crop to harvest", GRAY)

    def _draw_title(self) -> None:
        """Draw title screen."""
        title = "HARVEST CHAIN"
        tw = len(title) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 35, title, WHITE)

        sub = "Color-Match Farm Chain"
        sw = len(sub) * 4
        pyxel.text(SCREEN_W // 2 - sw // 2, 50, sub, LIME)

        # Color legend boxes
        for i, (col, name) in enumerate(zip(CROP_COLORS, CROP_NAMES)):
            bx = 40 + i * 65
            pyxel.rect(bx - 6, 72, 16, 16, col)
            pyxel.rectb(bx - 6, 72, 16, 16, WHITE)
            nw = len(name) * 4
            pyxel.text(bx + 2 - nw // 2, 92, name, WHITE)

        # Instructions
        lines = [
            "Click crops to harvest.",
            "Harvest connected same-color",
            "crops in one chain (BFS fill).",
            "",
            "Same-color chain -> COMBO UP!",
            f"COMBO>={SUPER_COMBO} -> SUPER MODE!",
            "  (harvest ALL of that color)",
            "",
            "Crops spread every harvest (CA).",
            ">85% = OVERGROWTH (game over)",
            "",
            "Click to START",
        ]
        for i, ln in enumerate(lines):
            pyxel.text(25, 110 + i * 11, ln, GRAY)

    def _draw_playing(self) -> None:
        """Draw playing screen."""
        self._draw_grid_bg()
        self._draw_crops()
        self._draw_particles()
        self._draw_ui()

    def _draw_game_over(self) -> None:
        """Draw game over screen."""
        # Draw the final grid state dimmed
        self._draw_grid_bg()
        self._draw_crops()
        self._draw_particles()

        # Overlay
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, BLACK)

        go_text = "GAME OVER"
        gw = len(go_text) * 4
        pyxel.text(SCREEN_W // 2 - gw // 2, 50, go_text, RED)

        def _ctr(y: int, text: str, color: int) -> None:
            pyxel.text(SCREEN_W // 2 - len(text) * 2, y, text, color)

        _ctr(80, f"SCORE: {self.score}", WHITE)
        _ctr(100, f"MAX COMBO: {self.max_combo}", ORANGE)
        _ctr(120, f"TURNS: {self._turn_count}", GRAY)
        super_yes = "YES" if self.max_combo >= SUPER_COMBO else "NO"
        _ctr(140, f"SUPER REACHED: {super_yes}", YELLOW)

        _ctr(175, "Click to RETRY", GRAY)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    Game()


if __name__ == "__main__":
    main()
