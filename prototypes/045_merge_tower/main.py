"""MERGE TOWER — Tower stacking merge puzzle.

Reinterpreted from game_idea_factory idea #1 (score 31.85):
  "synthesis compression" → 3+ same-color blocks MERGE into higher tier
  "split/converge numbers" → chain reactions cascade through tower

Core mechanic: Drop colored blocks that stack on a grid.
3+ same-color, same-tier adjacent blocks merge into a higher-tier block.
Chain reactions cascade upward. If the tower reaches the top, game over.

Controls:
  Left/Right — move block
  Down — fast drop
  Space — instant drop
  R — restart (on game over)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if not TYPE_CHECKING:
    import pyxel

# ── Config ──

SCREEN_W = 220
SCREEN_H = 300
GRID_COLS = 10
GRID_ROWS = 13
CELL_SIZE = 20
GRID_X = (SCREEN_W - GRID_COLS * CELL_SIZE) // 2  # 10
GRID_Y = 40  # room for score at top
COLORS = 5
MAX_TIER = 3
MERGE_THRESHOLD = 3
DROP_SPEED = 30  # frames per cell at normal speed
FAST_DROP_SPEED = 6  # frames per cell at fast drop

# Color values (Pyxel palette integers, used at runtime)
# Valid Pyxel colors: see AGENTS.md for full list
COLOR_VALS: tuple[int, int, int, int, int] = (
    pyxel.COLOR_RED,        # 8
    pyxel.COLOR_GREEN,      # 11
    pyxel.COLOR_LIGHT_BLUE, # 12
    pyxel.COLOR_YELLOW,     # 10
    pyxel.COLOR_PURPLE,     # 2
)

# Tier tint multipliers (lighter = higher tier)
TIER_TINTS: tuple[int, int, int] = (
    pyxel.COLOR_WHITE,   # tier 1 (bright)
    pyxel.COLOR_YELLOW,  # tier 2 (yellowish)
    pyxel.COLOR_ORANGE,  # tier 3 (orange/golden)
)

SCORE_PER_TIER: tuple[int, int, int] = (10, 30, 100)
COMBO_MULTIPLIER = 1.5


class Phase(Enum):
    DROP = auto()
    MERGE_ANIM = auto()
    GAME_OVER = auto()


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


@dataclass
class Cell:
    """A cell on the grid. None means empty."""
    color: int  # 0..COLORS-1
    tier: int   # 1..MAX_TIER


@dataclass
class Game:
    phase: Phase = Phase.DROP
    grid: list[list[Cell | None]] = field(default_factory=list)
    score: int = 0
    combo: int = 0
    max_combo: int = 0
    max_tier_reached: int = 1
    merge_count: int = 0
    blocks_dropped: int = 0

    # Falling block
    block_col: int = 0
    block_color: int = 0
    block_tier: int = 1
    block_y: float = 0.0  # pixel y position
    drop_timer: int = 0

    # Particles and effects
    particles: list[Particle] = field(default_factory=list)
    floating_texts: list[tuple[float, float, str, int, int]] = field(default_factory=list)
    # (x, y, text, color, life)
    shake_frames: int = 0
    shake_intensity: int = 3

    # Merge animation
    merge_cells: list[tuple[int, int]] = field(default_factory=list)
    merge_target: tuple[int, int, int, int] = (0, 0, 0, 1)  # row, col, color, tier
    merge_timer: int = 0
    MERGE_ANIM_FRAMES: int = 15  # class constant

    _rng: random.Random = field(default_factory=lambda: random.Random())

    def reset(self) -> None:
        """Initialize or reset game state."""
        self.phase = Phase.DROP
        self.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.max_tier_reached = 1
        self.merge_count = 0
        self.blocks_dropped = 0
        self.particles.clear()
        self.floating_texts.clear()
        self.shake_frames = 0
        self.merge_cells.clear()
        self._spawn_block()

    def _spawn_block(self) -> None:
        """Spawn a new falling block at the top."""
        self.block_col = GRID_COLS // 2
        self.block_color = self._rng.randint(0, COLORS - 1)
        self.block_tier = 1
        self.block_y = float(GRID_Y)
        self.drop_timer = 0

        # Check if spawn position is blocked
        if self.grid[0][self.block_col] is not None:
            self.phase = Phase.GAME_OVER

    def _cell_to_px(self, row: int, col: int) -> tuple[int, int]:
        """Convert grid coordinates to pixel position (top-left corner)."""
        return GRID_X + col * CELL_SIZE, GRID_Y + row * CELL_SIZE

    def _block_target_row(self) -> int:
        """Find the row where the falling block would land."""
        col = self.block_col
        for row in range(GRID_ROWS - 1, -1, -1):
            if self.grid[row][col] is None:
                return row
        return -1  # column is full

    def _update_drop(self) -> None:
        """Handle input and movement during DROP phase."""
        # Movement
        if pyxel.btnp(pyxel.KEY_LEFT):
            self.block_col = max(0, self.block_col - 1)
            # Adjust y if new column has different surface
            self._adjust_block_y()
        if pyxel.btnp(pyxel.KEY_RIGHT):
            self.block_col = min(GRID_COLS - 1, self.block_col + 1)
            self._adjust_block_y()

        # Fast drop or instant drop
        if pyxel.btn(pyxel.KEY_DOWN):
            self.drop_timer += DROP_SPEED // FAST_DROP_SPEED
        elif pyxel.btnp(pyxel.KEY_SPACE):
            # Instant drop
            target = self._block_target_row()
            if target >= 0:
                self.block_y = float(GRID_Y + target * CELL_SIZE)
                self._land_block()
                return
        else:
            self.drop_timer += 1

        # Descend
        if self.drop_timer >= DROP_SPEED:
            self.drop_timer = 0
            target = self._block_target_row()
            target_y = GRID_Y + target * CELL_SIZE
            if self.block_y >= target_y - 1:
                self._land_block()
            else:
                self.block_y += CELL_SIZE

    def _adjust_block_y(self) -> None:
        """Clamp block_y so it doesn't float above the surface of the new column."""
        target = self._block_target_row()
        max_y = GRID_Y + target * CELL_SIZE
        if self.block_y > max_y:
            self.block_y = float(max_y)

    def _land_block(self) -> None:
        """Place the falling block onto the grid and check for merges."""
        target = self._block_target_row()
        if target < 0:
            self.phase = Phase.GAME_OVER
            return

        self.grid[target][self.block_col] = Cell(
            color=self.block_color, tier=self.block_tier
        )
        self.blocks_dropped += 1
        self.combo = 0  # reset combo for new drop

        # Check for merges
        if self._check_and_merge():
            # Merges happened, stay in MERGE_ANIM phase
            pass
        else:
            # No merges, spawn next block
            self._spawn_block()

    def _check_and_merge(self) -> bool:
        """Find and execute one merge cluster. Returns True if merge found."""
        clusters = self._find_clusters()
        if not clusters:
            return False

        # Pick the largest cluster (most impactful first)
        largest: list[tuple[int, int]] = max(clusters, key=len)
        self.merge_cells = largest
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)

        # Determine merged block properties
        sample = self.grid[largest[0][0]][largest[0][1]]
        assert sample is not None
        new_color = sample.color
        new_tier = min(sample.tier + 1, MAX_TIER)
        self.max_tier_reached = max(self.max_tier_reached, new_tier)

        # Calculate center of cluster for merge target
        avg_r = sum(r for r, _ in largest) / len(largest)
        avg_c = sum(c for _, c in largest) / len(largest)
        center_r = int(avg_r)
        center_c = int(avg_c)

        self.merge_target = (center_r, center_c, new_color, new_tier)
        self.merge_timer = 0
        self.phase = Phase.MERGE_ANIM

        # Spawn merge particles
        for r, c in largest:
            px, py = self._cell_to_px(r, c)
            for _ in range(4):
                self.particles.append(Particle(
                    x=px + CELL_SIZE / 2,
                    y=py + CELL_SIZE / 2,
                    vx=self._rng.uniform(-2, 2),
                    vy=self._rng.uniform(-2, 2),
                    life=20,
                    color=sample.color,
                ))

        return True

    def _find_clusters(self) -> list[list[tuple[int, int]]]:
        """Find all merge-eligible clusters (3+ same-color, same-tier adjacent cells)."""
        visited: set[tuple[int, int]] = set()
        clusters: list[list[tuple[int, int]]] = []

        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                if (row, col) in visited:
                    continue
                cell = self.grid[row][col]
                if cell is None:
                    continue

                # BFS to find connected same-color, same-tier cells
                cluster: list[tuple[int, int]] = []
                stack = [(row, col)]
                visited.add((row, col))

                while stack:
                    r, c = stack.pop()
                    cluster.append((r, c))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < GRID_ROWS and 0 <= nc < GRID_COLS:
                            if (nr, nc) in visited:
                                continue
                            neighbor = self.grid[nr][nc]
                            if (neighbor is not None
                                    and neighbor.color == cell.color
                                    and neighbor.tier == cell.tier):
                                visited.add((nr, nc))
                                stack.append((nr, nc))

                if len(cluster) >= MERGE_THRESHOLD:
                    clusters.append(cluster)

        return clusters

    def _update_merge_anim(self) -> None:
        """Update merge animation and finalize when done."""
        self.merge_timer += 1

        if self.merge_timer >= Game.MERGE_ANIM_FRAMES:
            # Finalize merge
            target_r, target_c, new_color, new_tier = self.merge_target

            # Clear merged cells
            for r, c in self.merge_cells:
                self.grid[r][c] = None

            # Place new merged block
            self.grid[target_r][target_c] = Cell(color=new_color, tier=new_tier)
            self.merge_count += 1

            # Score (combo multiplier applies)
            base = SCORE_PER_TIER[min(new_tier, len(SCORE_PER_TIER)) - 1]
            combo_bonus = int(base * (COMBO_MULTIPLIER ** (self.combo - 1) - 1))
            points = base + combo_bonus
            self.score += points

            # Floating score text
            px, py = self._cell_to_px(target_r, target_c)
            self.floating_texts.append((
                float(px), py - 5,
                f"+{points}", pyxel.COLOR_WHITE, 30
            ))

            # Spawn tier-up particles
            for _ in range(8):
                self.particles.append(Particle(
                    x=px + CELL_SIZE / 2,
                    y=py + CELL_SIZE / 2,
                    vx=self._rng.uniform(-3, 3),
                    vy=self._rng.uniform(-3, 3),
                    life=25,
                    color=new_color,
                    size=3,
                ))

            # Screen shake for tier 3 merges
            if new_tier >= 3:
                self.shake_frames = 8
                self.shake_intensity = 4

            self.merge_cells.clear()

            # Check for chain merges
            if self._check_and_merge():
                # More merges found, stay in MERGE_ANIM
                pass
            else:
                # Chain done, spawn next block
                self.phase = Phase.DROP
                self._spawn_block()

    def _update_particles(self) -> None:
        """Update particle positions and lifetimes."""
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.2  # gravity
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        """Update floating text positions."""
        for i in range(len(self.floating_texts) - 1, -1, -1):
            x, y, text, color, life = self.floating_texts[i]
            life -= 1
            if life <= 0:
                self.floating_texts.pop(i)
            else:
                self.floating_texts[i] = (x, y - 0.5, text, color, life)

    def update(self) -> None:
        """Main update loop."""
        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
            return

        self._update_particles()
        self._update_floating_texts()

        if self.shake_frames > 0:
            self.shake_frames -= 1

        if self.phase == Phase.DROP:
            self._update_drop()
        elif self.phase == Phase.MERGE_ANIM:
            self._update_merge_anim()

    def draw(self) -> None:
        """Main draw loop."""
        pyxel.cls(pyxel.COLOR_BLACK)

        # Apply screen shake
        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0:
            shake_x = self._rng.randint(-self.shake_intensity, self.shake_intensity)
            shake_y = self._rng.randint(-self.shake_intensity, self.shake_intensity)

        # Draw grid background
        grid_bg_color = pyxel.COLOR_NAVY
        pyxel.rect(
            GRID_X + shake_x, GRID_Y + shake_y,
            GRID_COLS * CELL_SIZE, GRID_ROWS * CELL_SIZE,
            grid_bg_color,
        )

        # Draw grid lines
        for row in range(GRID_ROWS + 1):
            y = GRID_Y + row * CELL_SIZE + shake_y
            pyxel.line(GRID_X + shake_x, y,
                       GRID_X + GRID_COLS * CELL_SIZE + shake_x, y,
                       pyxel.COLOR_DARK_BLUE)
        for col in range(GRID_COLS + 1):
            x = GRID_X + col * CELL_SIZE + shake_x
            pyxel.line(x, GRID_Y + shake_y,
                       x, GRID_Y + GRID_ROWS * CELL_SIZE + shake_y,
                       pyxel.COLOR_DARK_BLUE)

        # Draw placed blocks
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                cell = self.grid[row][col]
                if cell is None:
                    continue
                # Check if this cell is being merged (fading)
                if (row, col) in self.merge_cells:
                    progress = self.merge_timer / Game.MERGE_ANIM_FRAMES
                    alpha = 1.0 - progress
                    if self._rng.random() < progress * 0.3:
                        continue  # flicker effect
                    px, py = self._cell_to_px(row, col)
                    self._draw_block(
                        px + shake_x, py + shake_y,
                        cell.color, cell.tier, alpha=alpha,
                    )
                else:
                    px, py = self._cell_to_px(row, col)
                    self._draw_block(
                        px + shake_x, py + shake_y,
                        cell.color, cell.tier,
                    )

        # Draw merge target preview
        if self.merge_cells and self.merge_timer < Game.MERGE_ANIM_FRAMES:
            tr, tc, tcolor, ttier = self.merge_target
            tpx, tpy = self._cell_to_px(tr, tc)
            progress = self.merge_timer / Game.MERGE_ANIM_FRAMES
            alpha = progress
            # Pulsing glow
            pulse = 1.0 + 0.2 * math.sin(self.merge_timer * 0.5)
            self._draw_block(
                tpx + shake_x, tpy + shake_y,
                tcolor, ttier, alpha=alpha, scale=pulse,
            )

        # Draw falling block
        if self.phase == Phase.DROP:
            bx = GRID_X + self.block_col * CELL_SIZE + shake_x
            by = int(self.block_y) + shake_y
            self._draw_block(bx, by, self.block_color, self.block_tier)

        # Draw particles
        for p in self.particles:
            alpha = p.life / 25
            c = p.color if alpha > 0.5 else pyxel.COLOR_WHITE
            pyxel.pset(
                int(p.x) + shake_x, int(p.y) + shake_y,
                COLOR_VALS[c % COLORS],
            )

        # Draw floating texts
        for x, y, text, color, life in self.floating_texts:
            alpha = min(life / 15, 1.0)
            if alpha > 0.3:
                pyxel.text(int(x) + shake_x, int(y) + shake_y, text, color)

        # Draw score
        pyxel.text(GRID_X, 4, f"SCORE:{self.score:>6d}", pyxel.COLOR_WHITE)
        pyxel.text(GRID_X, 14, f"COMBO:{self.combo}", pyxel.COLOR_YELLOW)
        pyxel.text(GRID_X + 80, 14,
                   f"MAX:{self.max_combo} TIER:{self.max_tier_reached}",
                   pyxel.COLOR_LIGHT_BLUE)
        pyxel.text(GRID_X + 50, 24,
                   f"MERGES:{self.merge_count}",
                   pyxel.COLOR_GREEN)

        # Draw game over screen
        if self.phase == Phase.GAME_OVER:
            pyxel.rect(0, SCREEN_H // 2 - 30, SCREEN_W, 60, pyxel.COLOR_BLACK)
            pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 - 20,
                       "GAME OVER", pyxel.COLOR_RED)
            pyxel.text(SCREEN_W // 2 - 35, SCREEN_H // 2,
                       f"SCORE: {self.score}", pyxel.COLOR_WHITE)
            pyxel.text(SCREEN_W // 2 - 40, SCREEN_H // 2 + 12,
                       "PRESS R TO RETRY", pyxel.COLOR_YELLOW)

    def _draw_block(
        self,
        x: int, y: int,
        color_idx: int, tier: int,
        alpha: float = 1.0,
        scale: float = 1.0,
    ) -> None:
        """Draw a single block at pixel position."""
        if alpha <= 0:
            return

        base_color = COLOR_VALS[color_idx]
        tier_color = TIER_TINTS[min(tier - 1, len(TIER_TINTS) - 1)]

        # Block body
        size = int(CELL_SIZE * scale)
        offset = (CELL_SIZE - size) // 2
        bx, by = x + offset, y + offset

        if alpha >= 0.95:
            pyxel.rect(bx, by, size, size, base_color)
        else:
            # Simulate alpha with dithering
            for dy in range(size):
                for dx in range(size):
                    if (dx + dy) % 2 < alpha * 2:
                        pyxel.pset(bx + dx, by + dy, base_color)

        # Tier indicators
        if tier >= 2:
            if alpha >= 0.5:
                # Draw tier number
                tx = bx + size // 2 - 2
                ty = by + size // 2 - 4
                pyxel.text(tx, ty, str(tier), tier_color)

        # Border for higher tiers
        if tier >= 2:
            pyxel.rectb(bx, by, size, size, tier_color)
        if tier >= 3:
            # Golden border corners
            pyxel.pset(bx, by, pyxel.COLOR_YELLOW)
            pyxel.pset(bx + size - 1, by, pyxel.COLOR_YELLOW)
            pyxel.pset(bx, by + size - 1, pyxel.COLOR_YELLOW)
            pyxel.pset(bx + size - 1, by + size - 1, pyxel.COLOR_YELLOW)

    def run(self) -> None:
        """Initialize Pyxel and start the game loop."""
        pyxel.init(SCREEN_W, SCREEN_H, title="MERGE TOWER")
        self.reset()
        pyxel.run(self.update, self.draw)


def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()
