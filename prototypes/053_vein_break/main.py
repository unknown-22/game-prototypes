"""VEIN BREAK — Color-chain drilling game.

Reinterpreted from game_idea_factory #1 (Score 32.35):
  "circuit/pipe visualization (flow + amplify)" → color veins in the rock grid
  "synthesis compression" → BFS chain-clearing connected same-color blocks,
     gravity compacts above

Core mechanic: Drill through same-color blocks consecutively to build COMBO.
COMBO >= 3 on a connected cluster triggers CHAIN BREAK —
all same-color adjacent blocks BFS-clear with cascading gravity.
"""
import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


# ── Config ──
SCREEN_W = 200
SCREEN_H = 240
COLS = 10
ROWS = 10
CELL = 20
GRID_TOP = 40
NUM_COLORS = 4
COLOR_NAMES = ("RED", "GREEN", "BLUE", "YELLOW")
# pyxel color constants: RED=8, GREEN=11, DARK_BLUE=5, YELLOW=10
COLOR_VALS: tuple[int, int, int, int] = (8, 11, 5, 10)
MAX_FUEL = 100
FUEL_PER_DRILL = 3
FUEL_PICKUP_CHANCE = 0.2
FUEL_PICKUP_AMOUNT = 15
COMBO_THRESHOLD = 3
BASE_SCORE = 10
COMBO_MULT_STEP = 0.5
CHAIN_BONUS_MULT = 1.5
SPAWN_INTERVAL = 150  # frames between new-block spawns
SPAWN_COUNT = 2  # blocks per spawn
DRILL_COOLDOWN = 6  # frames between drills
PLAYER_Y = 28  # drill visual Y position (above grid)
PARTICLE_COUNT_SMALL = 4
PARTICLE_COUNT_BIG = 10
MAX_PARTICLES = 60


class Phase(Enum):
    PLAYING = auto()
    CHAIN_ANIM = auto()
    GAME_OVER = auto()


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int


class Game:
    """Main game class for VEIN BREAK."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="VEIN BREAK")
        self._rng = random.Random()
        self.reset()
        pyxel.run(self._update, self._draw)

    def reset(self) -> None:
        """Reset all game state for a new game."""
        self.grid: list[list[int]] = [[0] * COLS for _ in range(ROWS)]
        self._init_grid()
        self.player_col = COLS // 2
        self.fuel = MAX_FUEL
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.last_color: int | None = None
        self.phase = Phase.PLAYING
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._drill_cooldown = 0
        self._spawn_timer = SPAWN_INTERVAL
        self._chain_queue: list[tuple[int, int]] = []
        self._chain_color: int = 0
        self._chain_score_multi: float = 1.0
        self._chain_timer = 0
        self._blocks_cleared = 0
        self._game_over_timer = 0
        self._shake_frames = 0

    def _init_grid(self) -> None:
        """Fill grid with colored blocks."""
        for r in range(ROWS):
            for c in range(COLS):
                self.grid[r][c] = self._rng.randint(1, NUM_COLORS)

    # ── Update ──

    def _update(self) -> None:
        """Main update loop called by Pyxel each frame."""
        if self.phase == Phase.GAME_OVER:
            self._game_over_timer += 1
            if self._game_over_timer > 60 and pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
            return

        self._update_particles()
        self._update_floating_texts()

        if self._shake_frames > 0:
            self._shake_frames -= 1

        if self.phase == Phase.CHAIN_ANIM:
            self._update_chain_anim()
            return

        if self.phase == Phase.PLAYING:
            self._update_playing()

    def _update_playing(self) -> None:
        """Handle input and game logic during PLAYING phase."""
        if self._drill_cooldown > 0:
            self._drill_cooldown -= 1

        # Movement
        if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A):
            if self.player_col > 0:
                self.player_col -= 1
        if pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D):
            if self.player_col < COLS - 1:
                self.player_col += 1

        # Drill
        drill_key = (
            pyxel.btnp(pyxel.KEY_DOWN)
            or pyxel.btnp(pyxel.KEY_SPACE)
            or pyxel.btnp(pyxel.KEY_S)
        )
        if drill_key and self._drill_cooldown <= 0 and self.fuel >= FUEL_PER_DRILL:
            self._drill()

        # Spawn new blocks
        self._spawn_timer -= 1
        if self._spawn_timer <= 0:
            self._spawn_timer = SPAWN_INTERVAL
            self._spawn_blocks()

        # Game over check
        if self.fuel <= 0:
            self.phase = Phase.GAME_OVER
            self._game_over_timer = 0

    def _find_topmost_block(self, col: int) -> int:
        """Return the row index of the topmost block in column `col`, or -1 if empty."""
        for r in range(ROWS):
            if self.grid[r][col] != 0:
                return r
        return -1

    def _drill(self) -> None:
        """Drill the topmost block in the player's column."""
        col = self.player_col
        target_row = self._find_topmost_block(col)
        if target_row == -1:
            return  # Column is empty

        color = self.grid[target_row][col]

        # Predict new combo value
        will_match = self.last_color is not None and color == self.last_color
        new_combo = self.combo + 1 if will_match else 1

        # Check for chain break BEFORE clearing (must read grid while block exists)
        if new_combo >= COMBO_THRESHOLD:
            cluster = self._bfs_cluster(col, target_row, color)
        else:
            cluster: set[tuple[int, int]] = set()

        # Clear the drilled block
        self.grid[target_row][col] = 0
        self.fuel -= FUEL_PER_DRILL
        self._drill_cooldown = DRILL_COOLDOWN

        # Update combo state
        self.combo = new_combo
        self.last_color = color
        if self.combo > self.max_combo:
            self.max_combo = self.combo

        # Score for drilled block
        combo_mult = 1.0 + (self.combo - 1) * COMBO_MULT_STEP
        self.score += int(BASE_SCORE * combo_mult)

        # Fuel pickup
        if self._rng.random() < FUEL_PICKUP_CHANCE:
            self.fuel = min(MAX_FUEL, self.fuel + FUEL_PICKUP_AMOUNT)
            self._add_floating_text(
                col * CELL + CELL // 2,
                GRID_TOP + target_row * CELL + CELL // 2,
                f"+{FUEL_PICKUP_AMOUNT}F",
                10,  # raw YELLOW
            )

        # Particles
        self._spawn_particles(
            col * CELL + CELL // 2,
            GRID_TOP + target_row * CELL + CELL // 2,
            color,
            PARTICLE_COUNT_SMALL,
        )

        # Trigger chain break if cluster exists (excluding the drilled cell)
        chain_cells = [(c, r) for (c, r) in cluster if (c, r) != (col, target_row)]
        if chain_cells:
            self._chain_queue = chain_cells
            self._chain_color = color
            self._chain_score_multi = combo_mult
            self._chain_timer = 0
            self.phase = Phase.CHAIN_ANIM
            return

        # No chain — apply gravity
        self._apply_gravity()

    def _bfs_cluster(self, col: int, row: int, color: int) -> set[tuple[int, int]]:
        """BFS flood-fill: find all connected same-color blocks from (col, row)."""
        visited: set[tuple[int, int]] = set()
        queue: list[tuple[int, int]] = [(col, row)]
        while queue:
            c, r = queue.pop(0)
            if (c, r) in visited:
                continue
            if not (0 <= c < COLS and 0 <= r < ROWS):
                continue
            if self.grid[r][c] != color:
                continue
            visited.add((c, r))
            for dc, dr in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nc, nr = c + dc, r + dr
                if (nc, nr) not in visited:
                    queue.append((nc, nr))
        return visited

    def _update_chain_anim(self) -> None:
        """Animate chain break — clear one cell per 2 ticks."""
        self._chain_timer += 1
        if self._chain_timer % 2 != 0:
            return

        if self._chain_queue:
            c, r = self._chain_queue.pop(0)
            if self.grid[r][c] == self._chain_color:
                self.grid[r][c] = 0
                self.score += int(BASE_SCORE * self._chain_score_multi * CHAIN_BONUS_MULT)
                self._blocks_cleared += 1
                self._spawn_particles(
                    c * CELL + CELL // 2,
                    GRID_TOP + r * CELL + CELL // 2,
                    self._chain_color,
                    PARTICLE_COUNT_SMALL,
                )
                # Chain fuel pickups
                if self._rng.random() < FUEL_PICKUP_CHANCE * 0.5:
                    self.fuel = min(MAX_FUEL, self.fuel + FUEL_PICKUP_AMOUNT // 2)
        else:
            # Chain complete — apply gravity + feedback
            self._apply_gravity()
            self._shake_frames = 6
            self._add_floating_text(
                self.player_col * CELL + CELL // 2,
                PLAYER_Y - 10,
                f"CHAIN x{self.combo}!",
                self._chain_color,
            )
            self.phase = Phase.PLAYING

    def _apply_gravity(self) -> None:
        """Compact blocks downward in each column, filling gaps."""
        for c in range(COLS):
            write_row = ROWS - 1
            for r in range(ROWS - 1, -1, -1):
                if self.grid[r][c] != 0:
                    if r != write_row:
                        self.grid[write_row][c] = self.grid[r][c]
                        self.grid[r][c] = 0
                    write_row -= 1

    def _spawn_blocks(self) -> None:
        """Spawn new blocks at the top of random columns."""
        for _ in range(SPAWN_COUNT):
            col = self._rng.randint(0, COLS - 1)
            # Find the topmost empty cell in this column
            for r in range(ROWS):
                if self.grid[r][col] == 0:
                    self.grid[r][col] = self._rng.randint(1, NUM_COLORS)
                    break

    # ── Particle / Text systems ──

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        """Spawn particles at (x, y) with the given color index (1-4)."""
        pyxel_color = COLOR_VALS[color - 1]
        for _ in range(count):
            angle = self._rng.random() * math.pi * 2
            speed = self._rng.random() * 2.0 + 0.5
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 1.0,
                color=pyxel_color,
                life=self._rng.randint(8, 20),
            ))
        # Trim excess particles
        while len(self.particles) > MAX_PARTICLES:
            self.particles.pop(0)

    def _update_particles(self) -> None:
        """Update particle positions and lifetimes."""
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        """Add floating feedback text. `color` is either a COLOR_VALS index (1-4) or
        a raw pyxel color constant."""
        if 1 <= color <= NUM_COLORS:
            pyxel_color = COLOR_VALS[color - 1]
        else:
            pyxel_color = color
        self.floating_texts.append(FloatingText(
            x=x - len(text) * 2,
            y=y,
            text=text,
            color=pyxel_color,
            life=30,
        ))

    def _update_floating_texts(self) -> None:
        """Update floating text positions and lifetimes."""
        for ft in self.floating_texts[:]:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    # ── Draw ──

    def _draw(self) -> None:
        """Main draw loop called by Pyxel each frame."""
        pyxel.cls(0)

        # Screen shake
        shake_x = 0
        shake_y = 0
        if self._shake_frames > 0:
            shake_x = self._rng.randint(-2, 2)
            shake_y = self._rng.randint(-2, 2)

        # Grid background
        pyxel.rect(0, GRID_TOP, COLS * CELL, ROWS * CELL, 1)

        # Draw blocks
        for r in range(ROWS):
            for c in range(COLS):
                color = self.grid[r][c]
                if color != 0:
                    x = c * CELL + shake_x
                    y = GRID_TOP + r * CELL + shake_y
                    pyxel.rect(x + 1, y + 1, CELL - 2, CELL - 2, COLOR_VALS[color - 1])
                    pyxel.rectb(x + 1, y + 1, CELL - 2, CELL - 2, COLOR_VALS[color - 1])

        # Grid lines
        for r in range(ROWS + 1):
            pyxel.line(
                0, GRID_TOP + r * CELL + shake_y,
                COLS * CELL, GRID_TOP + r * CELL + shake_y,
                5,
            )
        for c in range(COLS + 1):
            pyxel.line(
                c * CELL + shake_x, GRID_TOP,
                c * CELL + shake_x, GRID_TOP + ROWS * CELL + shake_y,
                5,
            )

        # Draw player drill
        px = self.player_col * CELL + CELL // 2 + shake_x
        py = PLAYER_Y + shake_y
        drill_color = COLOR_VALS[self.last_color - 1] if self.last_color else 7
        pyxel.tri(px, py - 6, px - 7, py + 4, px + 7, py + 4, drill_color)
        pyxel.tri(px, py - 3, px - 4, py + 6, px + 4, py + 6, 7)

        # Combo glow
        if self.combo >= COMBO_THRESHOLD:
            glow_radius = 4 + self.combo * 2
            glow_col = COLOR_VALS[self.last_color - 1] if self.last_color else 7
            pyxel.circb(px, GRID_TOP + shake_y, glow_radius, glow_col)

        # Draw particles
        for p in self.particles:
            alpha = p.life / 20.0
            if alpha > 0:
                sz = max(1, int(3 * alpha))
                pyxel.rect(
                    int(p.x) + shake_x, int(p.y) + shake_y, sz, sz, p.color,
                )

        # Draw floating texts
        for ft in self.floating_texts:
            alpha = ft.life / 30.0
            if alpha > 0.2:
                pyxel.text(
                    int(ft.x) + shake_x, int(ft.y) + shake_y, ft.text, ft.color,
                )

        # ── UI ──
        pyxel.rect(0, 0, SCREEN_W, GRID_TOP, 1)
        pyxel.text(4, 2, f"SCORE:{self.score:06d}", 7)

        if self.combo >= 2:
            combo_txt = f"COMBO x{self.combo}"
            combo_col = COLOR_VALS[self.last_color - 1] if self.last_color else 7
            pyxel.text(4, 12, combo_txt, combo_col)
        else:
            pyxel.text(4, 12, "COMBO x1", 13)

        pyxel.text(4, 22, f"MAX:{self.max_combo}", 6)

        # Fuel bar
        pyxel.text(SCREEN_W - 50, 2, "FUEL", 7)
        bar_x = SCREEN_W - 48
        bar_y = 12
        bar_w = 44
        bar_h = 6
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, 5)
        fuel_w = int(bar_w * self.fuel / MAX_FUEL)
        if fuel_w > 0:
            if self.fuel > 30:
                fuel_col = 11  # GREEN
            elif self.fuel > 15:
                fuel_col = 8  # RED
            else:
                fuel_col = 2  # PURPLE (danger)
            pyxel.rect(bar_x + 1, bar_y + 1, fuel_w - 2, bar_h - 2, fuel_col)
        pyxel.text(bar_x, bar_y + 8, f"{self.fuel}/{MAX_FUEL}", 5)

        # Controls
        pyxel.text(4, GRID_TOP + ROWS * CELL + 2, "ARROWS:MOVE  SPACE:DRILL", 13)

        # Game Over overlay
        if self.phase == Phase.GAME_OVER:
            pyxel.rect(30, 80, 140, 60, 0)
            pyxel.rectb(30, 80, 140, 60, 7)
            pyxel.text(50, 95, "GAME OVER", 8)
            pyxel.text(40, 115, f"SCORE: {self.score}", 7)
            if self._game_over_timer > 60:
                pyxel.text(35, 128, "SPACE: RETRY", 13)
