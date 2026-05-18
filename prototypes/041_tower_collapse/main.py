"""041_tower_collapse — Tower Collapse Puzzle

Drop blocks onto a tower. Same-color adjacent blocks that form 3+ chains
collapse for score. Chain reactions multiply combo. Game over if the tower
reaches the danger line.

Controls:
  Arrow keys / A,D — move block left/right
  Space / Click — drop block
  R — restart after game over
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import IntEnum, auto

import pyxel

# ── Config ──
SCREEN_W = 128
SCREEN_H = 160
COLS = 10
ROWS = 16
CELL = 12
GRID_X = (SCREEN_W - COLS * CELL) // 2
GRID_Y = 30
BLOCK_COLORS: tuple[int, ...] = (
    pyxel.COLOR_RED,    # 0
    pyxel.COLOR_YELLOW, # 1
    pyxel.COLOR_GREEN,  # 2
    pyxel.COLOR_CYAN,   # 3
    pyxel.COLOR_PINK,   # 4
)
NUM_COLORS = len(BLOCK_COLORS)
DANGER_ROW = 2  # top 2 rows = danger zone
MATCH_MIN = 3
DROP_SPEED = 3.0  # cells per second
COMBO_TIMEOUT = 2.0  # seconds to maintain combo chain
TOWER_START = 4  # initial rows of blocks


class Phase(IntEnum):
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
    size: int = 2


@dataclass
class FloatingText:
    x: int
    y: int
    text: str
    life: int
    color: int


@dataclass
class Game:
    # State
    phase: Phase = Phase.TITLE
    grid: list[list[int | None]] = field(default_factory=list)
    score: int = 0
    combo: int = 0
    max_combo: int = 0
    chain_count: int = 0
    total_cleared: int = 0

    # Dropping block
    drop_col: int = COLS // 2
    drop_color: int = 0
    drop_y: float = 0.0  # floating point row position
    drop_active: bool = False
    _rng: random.Random = field(default_factory=lambda: random.Random(42))

    # Animation
    particles: list[Particle] = field(default_factory=list)
    floating_texts: list[FloatingText] = field(default_factory=list)
    shake_frames: int = 0
    combo_timer: float = 0.0

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.chain_count = 0
        self.total_cleared = 0
        self.particles.clear()
        self.floating_texts.clear()
        self.shake_frames = 0
        self.combo_timer = 0.0
        self.drop_active = False

        # Init empty grid (None = empty)
        self.grid = [[None] * COLS for _ in range(ROWS)]

        # Fill bottom rows with random blocks
        for r in range(TOWER_START):
            for c in range(COLS):
                self.grid[r][c] = self._rng.randint(0, NUM_COLORS - 1)

        self._spawn_drop()

    def _spawn_drop(self) -> None:
        self.drop_col = COLS // 2
        self.drop_color = self._rng.randint(0, NUM_COLORS - 1)
        self.drop_y = -1.0
        self.drop_active = True

    # ── Grid helpers ──

    def _get(self, r: int, c: int) -> int | None:
        if 0 <= r < ROWS and 0 <= c < COLS:
            return self.grid[r][c]
        return None

    def _set(self, r: int, c: int, v: int | None) -> None:
        if 0 <= r < ROWS and 0 <= c < COLS:
            self.grid[r][c] = v

    def _adjacent(self, r: int, c: int) -> list[tuple[int, int]]:
        result: list[tuple[int, int]] = []
        for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                result.append((nr, nc))
        return result

    def _find_cluster(self, r: int, c: int) -> list[tuple[int, int]]:
        """BFS flood-fill to find connected same-color cluster."""
        color = self._get(r, c)
        if color is None:
            return []
        visited: set[tuple[int, int]] = set()
        queue: list[tuple[int, int]] = [(r, c)]
        visited.add((r, c))
        while queue:
            cr, cc = queue.pop(0)
            for nr, nc in self._adjacent(cr, cc):
                if (nr, nc) not in visited and self._get(nr, nc) == color:
                    visited.add((nr, nc))
                    queue.append((nr, nc))
        return sorted(visited)

    def _apply_gravity(self) -> None:
        """Let blocks fall into empty spaces below."""
        for c in range(COLS):
            write_row = ROWS - 1
            for r in range(ROWS - 1, -1, -1):
                if self.grid[r][c] is not None:
                    if write_row != r:
                        self.grid[write_row][c] = self.grid[r][c]
                        self.grid[r][c] = None
                    write_row -= 1

    def _find_all_matches(self) -> list[list[tuple[int, int]]]:
        """Find all clusters of MATCH_MIN or more same-color blocks."""
        found: set[tuple[int, int]] = set()
        clusters: list[list[tuple[int, int]]] = []
        for r in range(ROWS):
            for c in range(COLS):
                if (r, c) not in found and self._get(r, c) is not None:
                    cluster = self._find_cluster(r, c)
                    if len(cluster) >= MATCH_MIN:
                        clusters.append(cluster)
                        found.update(cluster)
        return clusters

    # ── Game logic ──

    def _place_block(self, r: int, c: int, color: int) -> None:
        """Place a block at (r,c) and resolve any chain reactions."""
        self._set(r, c, color)
        self._resolve_chains()
        self._check_game_over()

    def _resolve_chains(self) -> None:
        """Clear matching clusters, apply gravity, repeat until stable."""
        self.chain_count = 0
        while True:
            clusters = self._find_all_matches()
            if not clusters:
                break

            self.chain_count += 1
            if self.chain_count > 1:
                self.combo += 1
            else:
                self.combo = max(self.combo, 1)

            self.max_combo = max(self.max_combo, self.combo)
            self.combo_timer = COMBO_TIMEOUT

            total_cleared_this_chain = 0
            for cluster in clusters:
                for cr, cc in cluster:
                    cell_color = self._get(cr, cc)
                    if cell_color is not None:
                        sx = GRID_X + cc * CELL + CELL // 2
                        sy = GRID_Y + cr * CELL + CELL // 2
                        self._spawn_burst(sx, sy, BLOCK_COLORS[cell_color])
                    self._set(cr, cc, None)
                    total_cleared_this_chain += 1

            self.total_cleared += total_cleared_this_chain

            # Score: base * chain * combo multiplier
            multiplier = self.chain_count * (1 + self.combo * 0.5)
            pts = int(total_cleared_this_chain * 10 * multiplier)
            self.score += pts

            # Floating text at cluster center
            center_r = sum(r for r, _ in clusters[0]) // len(clusters[0])
            center_c = sum(c for _, c in clusters[0]) // len(clusters[0])
            txt = f"+{pts}"
            if self.chain_count > 1:
                txt = f"x{self.chain_count} +{pts}"
            self.floating_texts.append(
                FloatingText(
                    x=GRID_X + center_c * CELL,
                    y=GRID_Y + center_r * CELL,
                    text=txt,
                    life=40,
                    color=pyxel.COLOR_YELLOW,
                )
            )

            self.shake_frames = 4

            # Apply gravity for next iteration
            self._apply_gravity()

    def _check_game_over(self) -> None:
        """Check if tower reached danger zone."""
        for c in range(COLS):
            if self._get(DANGER_ROW, c) is not None:
                self.phase = Phase.GAME_OVER
                return

    def _spawn_burst(self, x: int, y: int, color: int) -> None:
        for _ in range(6):
            vx = random.uniform(-2, 2)
            vy = random.uniform(-3, 1)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=vx,
                    vy=vy,
                    life=15 + self._rng.randint(0, 10),
                    color=color,
                    size=2,
                )
            )

    def _update_particles(self) -> None:
        new_particles: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.15
            p.life -= 1
            if p.life > 0:
                new_particles.append(p)
        self.particles = new_particles

    def _update_floating_texts(self) -> None:
        new_texts: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life > 0:
                new_texts.append(ft)
        self.floating_texts = new_texts

    def _update(self) -> None:
        if self.phase != Phase.PLAYING:
            return

        # Combo timer decay
        if self.combo_timer > 0:
            self.combo_timer -= 1 / 60
            if self.combo_timer <= 0:
                self.combo = 0

        # Drop falling block
        if self.drop_active:
            self.drop_y += DROP_SPEED / 60
            current_row = int(self.drop_y)

            # Check if next row is occupied or out of bounds
            next_row = current_row + 1
            if next_row >= ROWS or self._get(next_row, self.drop_col) is not None:
                # Land at current_row
                if 0 <= current_row < ROWS and self._get(current_row, self.drop_col) is None:
                    self._place_block(current_row, self.drop_col, self.drop_color)
                elif current_row < 0:
                    # Block is above grid, place at row 0
                    if self._get(0, self.drop_col) is None:
                        self._place_block(0, self.drop_col, self.drop_color)
                    else:
                        self.phase = Phase.GAME_OVER
                else:
                    self.phase = Phase.GAME_OVER
                    return

                if self.phase == Phase.PLAYING:
                    self._spawn_drop()

        self._update_particles()
        self._update_floating_texts()

        if self.shake_frames > 0:
            self.shake_frames -= 1

    # ── Input ──

    def _input(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
            return

        # Playing — move dropping block
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            if self.drop_active and self.drop_col > 0:
                check_row = max(0, int(self.drop_y))
                if self._get(check_row, self.drop_col - 1) is None:
                    self.drop_col -= 1
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            if self.drop_active and self.drop_col < COLS - 1:
                check_row = max(0, int(self.drop_y))
                if self._get(check_row, self.drop_col + 1) is None:
                    self.drop_col += 1

        # Drop block instantly
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if self.drop_active:
                # Find landing row
                landed = False
                for r in range(ROWS):
                    if self._get(r, self.drop_col) is not None:
                        land_row = r - 1
                        landed = True
                        break
                if not landed:
                    land_row = ROWS - 1
                    landed = True

                if landed and 0 <= land_row < ROWS:
                    if self._get(land_row, self.drop_col) is None:
                        self._place_block(land_row, self.drop_col, self.drop_color)
                        if self.phase == Phase.PLAYING:
                            self._spawn_drop()
                    else:
                        self.phase = Phase.GAME_OVER
                else:
                    self.phase = Phase.GAME_OVER

    # ── Drawing ──

    def _draw(self) -> None:
        pyxel.cls(pyxel.COLOR_NAVY)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game()
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 40, 50, "TOWER COLLAPSE", pyxel.COLOR_YELLOW)
        pyxel.text(SCREEN_W // 2 - 30, 70, "Drop blocks.", pyxel.COLOR_WHITE)
        pyxel.text(SCREEN_W // 2 - 42, 80, "Match 3+ to clear.", pyxel.COLOR_WHITE)
        pyxel.text(SCREEN_W // 2 - 40, 95, "SPACE / Click", pyxel.COLOR_PINK)
        pyxel.text(SCREEN_W // 2 - 35, 105, "A/D or arrows", pyxel.COLOR_LIGHT_BLUE)
        pyxel.text(SCREEN_W // 2 - 20, 120, "PRESS SPACE", pyxel.COLOR_LIME)

    def _draw_game(self) -> None:
        ox = 0
        oy = 0
        if self.shake_frames > 0:
            ox = random.randint(-2, 2)
            oy = random.randint(-2, 2)

        # Danger zone highlight
        for r in range(DANGER_ROW):
            for c in range(COLS):
                pyxel.rect(
                    GRID_X + c * CELL + ox,
                    GRID_Y + r * CELL + oy,
                    CELL,
                    CELL,
                    pyxel.COLOR_DARK_BLUE,
                )

        # Grid border
        pyxel.rectb(
            GRID_X - 1 + ox,
            GRID_Y - 1 + oy,
            COLS * CELL + 2,
            ROWS * CELL + 2,
            pyxel.COLOR_GRAY,
        )

        # Grid cells
        for r in range(ROWS):
            for c in range(COLS):
                cell_color = self._get(r, c)
                if cell_color is not None:
                    px = GRID_X + c * CELL + ox
                    py = GRID_Y + r * CELL + oy
                    pyxel.rect(px, py, CELL, CELL, BLOCK_COLORS[cell_color])
                    pyxel.rect(px + 1, py + 1, CELL - 2, 2, pyxel.COLOR_WHITE)

        # Dropping block
        if self.drop_active and self.phase == Phase.PLAYING:
            drop_screen_y = GRID_Y + int(self.drop_y) * CELL + oy
            px = GRID_X + self.drop_col * CELL + ox
            pyxel.rect(px, drop_screen_y, CELL, CELL, BLOCK_COLORS[self.drop_color])
            pyxel.rect(px + 1, drop_screen_y + 1, CELL - 2, 2, pyxel.COLOR_WHITE)

            # Drop guide line
            guide_x = GRID_X + self.drop_col * CELL + CELL // 2 + ox
            pyxel.line(
                guide_x,
                drop_screen_y + CELL + oy,
                guide_x,
                GRID_Y + ROWS * CELL - 1 + oy,
                BLOCK_COLORS[self.drop_color],
            )

        # Particles
        for p in self.particles:
            pyxel.rect(int(p.x) + ox, int(p.y) + oy, p.size, p.size, p.color)

        # Floating texts
        for ft in self.floating_texts:
            pyxel.text(int(ft.x) + ox, int(ft.y) + oy, ft.text, ft.color)

        # HUD
        pyxel.text(4, 4, f"SCORE {self.score}", pyxel.COLOR_WHITE)
        pyxel.text(4, 12, f"COMBO x{self.combo}", pyxel.COLOR_YELLOW)
        pyxel.text(4, 20, f"CHAIN {self.chain_count}", pyxel.COLOR_PINK)

    def _draw_game_over(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, pyxel.COLOR_BLACK)
        pyxel.text(SCREEN_W // 2 - 24, 50, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(SCREEN_W // 2 - 24, 65, f"SCORE {self.score}", pyxel.COLOR_YELLOW)
        pyxel.text(
            SCREEN_W // 2 - 30, 75, f"MAX COMBO x{self.max_combo}", pyxel.COLOR_PINK
        )
        pyxel.text(
            SCREEN_W // 2 - 24, 85, f"CLEARED {self.total_cleared}", pyxel.COLOR_WHITE
        )
        pyxel.text(SCREEN_W // 2 - 28, 100, "R TO RETRY", pyxel.COLOR_LIME)


# ── Entry ──

def main() -> None:
    game = Game()
    game.reset()
    game.phase = Phase.TITLE

    def update() -> None:
        game._input()
        if game.phase == Phase.PLAYING:
            game._update()
        elif game.phase == Phase.GAME_OVER:
            game._update_particles()
            game._update_floating_texts()

    def draw() -> None:
        game._draw()

    pyxel.init(SCREEN_W, SCREEN_H, title="Tower Collapse", display_scale=3)
    pyxel.run(update, draw)


if __name__ == "__main__":
    main()
