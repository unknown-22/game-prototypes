"""
CELL SURGE — Grid Territory Control Game
=========================================
Reinterpreted from game idea #1 (score 32.35): dice/bag roguelite + CA grid spread + synthesis compression.

Core mechanic: Place colored seeds that spread across the grid (CA). Contiguous same-color regions
synthesize into fortress NODES. Compete against enemy spread from the edges.

Engine: Pyxel 2.x, 300×300, display_scale=2
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

import pyxel

if TYPE_CHECKING:
    pass

# ── Config ──
GRID_W = 12
GRID_H = 12
CELL_SIZE = 25
SCREEN_W = GRID_W * CELL_SIZE  # 300
SCREEN_H = GRID_H * CELL_SIZE  # 300
UI_HEIGHT = 40
WINDOW_H = SCREEN_H + UI_HEIGHT  # 340
SYNTHESIS_THRESHOLD = 6  # cells needed to form a node
MAX_ENERGY = 10
ENERGY_REGEN_RATE = 1  # per tick
SEED_COST = 2
TICK_INTERVAL = 60  # frames
ENEMY_SPREAD_INTERVAL = 2  # ticks (enemy spreads every 2 ticks)
MAX_PARTICLES = 50

# Colors (Pyxel palette)
CELL_COLORS: dict[int, int] = {
    1: pyxel.COLOR_RED,
    2: pyxel.COLOR_CYAN,
    3: pyxel.COLOR_LIME,
    4: pyxel.COLOR_YELLOW,
}
NODE_COLORS: dict[int, int] = {
    1: pyxel.COLOR_PURPLE,
    2: pyxel.COLOR_DARK_BLUE,
    3: pyxel.COLOR_GREEN,
    4: pyxel.COLOR_ORANGE,
}
ENEMY_COLOR = pyxel.COLOR_GRAY
EMPTY_COLOR = pyxel.COLOR_BLACK
GRID_LINE_COLOR = pyxel.COLOR_NAVY
CURSOR_COLOR = pyxel.COLOR_WHITE


# ── Enums ──
class Phase(Enum):
    PLAYING = auto()
    VICTORY = auto()
    DEFEAT = auto()


# ── Data Classes ──
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
class CellState:
    owner: int  # 0=empty, 1-4=player colors, 5=enemy, 6-9=nodes (color+5)
    is_node: bool = False

    @property
    def is_player(self) -> bool:
        return 1 <= self.owner <= 4

    @property
    def is_enemy(self) -> bool:
        return self.owner == 5

    @property
    def is_empty(self) -> bool:
        return self.owner == 0


# ── Game Class ──
class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, WINDOW_H, title="CELL SURGE", display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        """Initialize or reset game state."""
        self.grid: list[list[CellState]] = [
            [CellState(owner=0) for _ in range(GRID_W)] for _ in range(GRID_H)
        ]
        self.phase = Phase.PLAYING
        self.cursor_x = GRID_W // 2
        self.cursor_y = GRID_H // 2
        self.energy: float = MAX_ENERGY
        self.score = 0
        self.tick_timer = 0
        self.tick_count = 0
        self.particles: list[Particle] = []
        self.flash_cells: list[tuple[int, int, int]] = []  # (x, y, remaining_frames)
        self.message: str = ""
        self.message_timer = 0
        self.combo = 1
        self.combo_timer = 0
        self.nodes_created = 0
        self.total_enemy_killed = 0

        # Seed initial enemy cells on edges
        for x in range(GRID_W):
            if random.random() < 0.3:
                self.grid[0][x] = CellState(owner=5)
            if random.random() < 0.3:
                self.grid[GRID_H - 1][x] = CellState(owner=5)
        for y in range(1, GRID_H - 1):
            if random.random() < 0.2:
                self.grid[y][0] = CellState(owner=5)
            if random.random() < 0.2:
                self.grid[y][GRID_W - 1] = CellState(owner=5)

    # ── Update ──
    def update(self) -> None:
        if self.phase == Phase.VICTORY or self.phase == Phase.DEFEAT:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
            return

        self._update_input()
        self._update_tick()
        self._update_particles()
        self._update_flash()
        self._update_message()
        self._check_win_lose()

    def _update_input(self) -> None:
        """Handle cursor movement and seed placement."""
        if pyxel.btnp(pyxel.KEY_W) or pyxel.btnp(pyxel.KEY_UP):
            self.cursor_y = max(0, self.cursor_y - 1)
        if pyxel.btnp(pyxel.KEY_S) or pyxel.btnp(pyxel.KEY_DOWN):
            self.cursor_y = min(GRID_H - 1, self.cursor_y + 1)
        if pyxel.btnp(pyxel.KEY_A) or pyxel.btnp(pyxel.KEY_LEFT):
            self.cursor_x = max(0, self.cursor_x - 1)
        if pyxel.btnp(pyxel.KEY_D) or pyxel.btnp(pyxel.KEY_RIGHT):
            self.cursor_x = min(GRID_W - 1, self.cursor_x + 1)

        # Mouse input: click to place seed
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx = pyxel.mouse_x // CELL_SIZE
            my = pyxel.mouse_y // CELL_SIZE
            if 0 <= mx < GRID_W and 0 <= my < GRID_H:
                self.cursor_x = mx
                self.cursor_y = my
                self._place_seed(mx, my)

        # Space to place seed at cursor
        if pyxel.btnp(pyxel.KEY_SPACE):
            self._place_seed(self.cursor_x, self.cursor_y)

    def _place_seed(self, x: int, y: int) -> None:
        """Place a seed of random player color at (x, y)."""
        if self.energy < SEED_COST:
            self._show_message("NO ENERGY")
            return
        cell = self.grid[y][x]
        if not cell.is_empty:
            self._show_message("OCCUPIED")
            return
        if cell.is_enemy:
            self._show_message("ENEMY ZONE")
            return

        color = random.randint(1, 4)
        self.grid[y][x] = CellState(owner=color)
        self.energy -= SEED_COST
        self._spawn_particles(x * CELL_SIZE + CELL_SIZE // 2, y * CELL_SIZE + CELL_SIZE // 2, CELL_COLORS[color], 6)
        self._show_message(f"SEED {color}")

    def _update_tick(self) -> None:
        """Update game logic on tick interval."""
        self.tick_timer += 1
        if self.tick_timer < TICK_INTERVAL:
            return
        self.tick_timer = 0
        self.tick_count += 1

        # Regenerate energy
        self.energy = min(MAX_ENERGY, self.energy + ENERGY_REGEN_RATE)

        # Combo decay
        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer == 0:
                self.combo = 1

        # Player cell spread (CA)
        self._spread_player_cells()

        # Check for synthesis
        self._check_synthesis()

        # Enemy spread (every ENEMY_SPREAD_INTERVAL ticks)
        if self.tick_count % ENEMY_SPREAD_INTERVAL == 0:
            self._spread_enemy_cells()

        # Score update
        self._update_score()

    def _spread_player_cells(self) -> None:
        """CA spread: player cells spread to adjacent empty cells."""
        new_cells: list[tuple[int, int, int]] = []
        for y in range(GRID_H):
            for x in range(GRID_W):
                cell = self.grid[y][x]
                if not cell.is_player or cell.is_node:
                    continue
                owner = cell.owner
                for nx, ny in self._neighbors(x, y):
                    if self.grid[ny][nx].is_empty:
                        new_cells.append((nx, ny, owner))

        for x, y, owner in new_cells:
            self.grid[y][x] = CellState(owner=owner)
            if random.random() < 0.2:
                self._spawn_particles(
                    x * CELL_SIZE + CELL_SIZE // 2,
                    y * CELL_SIZE + CELL_SIZE // 2,
                    CELL_COLORS[owner],
                    3,
                )

    def _spread_enemy_cells(self) -> None:
        """Enemy cells spread to adjacent non-enemy, non-node cells."""
        new_cells: list[tuple[int, int]] = []
        for y in range(GRID_H):
            for x in range(GRID_W):
                if not self.grid[y][x].is_enemy:
                    continue
                for nx, ny in self._neighbors(x, y):
                    target = self.grid[ny][nx]
                    if target.is_node:
                        continue  # nodes resist enemy
                    if target.is_empty or target.is_player:
                        new_cells.append((nx, ny))

        # Limit enemy spread per tick
        max_spread = 3 + self.tick_count // 10
        if len(new_cells) > max_spread:
            new_cells = random.sample(new_cells, max_spread)

        for x, y in new_cells:
            old_owner = self.grid[y][x].owner
            if 1 <= old_owner <= 4:
                self.total_enemy_killed += 1
            self.grid[y][x] = CellState(owner=5)

    def _check_synthesis(self) -> None:
        """Check for contiguous same-color regions of size >= SYNTHESIS_THRESHOLD."""
        visited: set[tuple[int, int]] = set()
        for y in range(GRID_H):
            for x in range(GRID_W):
                if (x, y) in visited:
                    continue
                cell = self.grid[y][x]
                if not cell.is_player or cell.is_node:
                    visited.add((x, y))
                    continue
                owner = cell.owner
                region = self._flood_fill(x, y, owner, visited)
                if len(region) >= SYNTHESIS_THRESHOLD:
                    self._synthesize_region(region, owner)
                visited.update(region)

    def _flood_fill(
        self, sx: int, sy: int, owner: int, visited: set[tuple[int, int]]
    ) -> list[tuple[int, int]]:
        """BFS to find contiguous region of same owner."""
        region: list[tuple[int, int]] = []
        queue = [(sx, sy)]
        local_visited: set[tuple[int, int]] = {(sx, sy)}
        while queue:
            x, y = queue.pop(0)
            region.append((x, y))
            for nx, ny in self._neighbors(x, y):
                if (nx, ny) in local_visited:
                    continue
                if (nx, ny) in visited:
                    continue
                c = self.grid[ny][nx]
                if c.owner == owner and not c.is_node:
                    local_visited.add((nx, ny))
                    queue.append((nx, ny))
        return region

    def _synthesize_region(self, region: list[tuple[int, int]], owner: int) -> None:
        """Convert a region into nodes (1 node per region, rest become empty)."""
        # Pick center cell as node
        center_idx = len(region) // 2
        cx, cy = region[center_idx]
        # Score bonus
        bonus = len(region) * 10 * self.combo
        self.score += bonus
        self.nodes_created += 1
        self.combo += 1
        self.combo_timer = 3
        self._show_message(f"SYNTH {len(region)}! +{bonus}")
        # Flash all cells in region
        for x, y in region:
            self.flash_cells.append((x, y, 15))
        # Spawn particles
        for x, y in region:
            px = x * CELL_SIZE + CELL_SIZE // 2
            py = y * CELL_SIZE + CELL_SIZE // 2
            self._spawn_particles(px, py, NODE_COLORS[owner], 4)
        # Convert region: center becomes node, rest empty
        for x, y in region:
            if (x, y) == (cx, cy):
                self.grid[y][x] = CellState(owner=owner, is_node=True)
            else:
                self.grid[y][x] = CellState(owner=0)

    def _update_score(self) -> None:
        """Update score based on current territory."""
        player_cells = 0
        node_cells = 0
        for y in range(GRID_H):
            for x in range(GRID_W):
                cell = self.grid[y][x]
                if cell.is_node:
                    node_cells += 1
                elif cell.is_player:
                    player_cells += 1
        self.score += player_cells + node_cells * 3

    def _check_win_lose(self) -> None:
        """Check victory or defeat conditions."""
        enemy_count = 0
        player_count = 0
        total = GRID_W * GRID_H
        for y in range(GRID_H):
            for x in range(GRID_W):
                cell = self.grid[y][x]
                if cell.is_enemy:
                    enemy_count += 1
                elif cell.is_player or cell.is_node:
                    player_count += 1

        # Enemy controls >= 50%
        if enemy_count >= total // 2:
            self.phase = Phase.DEFEAT
            self._show_message("DEFEAT!")
            return

        # All enemy eliminated
        if enemy_count == 0 and player_count > 0:
            self.phase = Phase.VICTORY
            self._show_message("VICTORY!")

    # ── Particles & Effects ──
    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            if len(self.particles) >= MAX_PARTICLES:
                break
            vx = random.uniform(-1.5, 1.5)
            vy = random.uniform(-1.5, 1.5)
            life = random.randint(10, 25)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def _update_particles(self) -> None:
        alive = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def _update_flash(self) -> None:
        self.flash_cells = [(x, y, t - 1) for x, y, t in self.flash_cells if t > 0]

    def _show_message(self, msg: str) -> None:
        self.message = msg
        self.message_timer = 45

    def _update_message(self) -> None:
        if self.message_timer > 0:
            self.message_timer -= 1
        else:
            self.message = ""

    # ── Helpers ──
    @staticmethod
    def _neighbors(x: int, y: int) -> list[tuple[int, int]]:
        """Get 4-directional neighbors within grid bounds."""
        result: list[tuple[int, int]] = []
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                result.append((nx, ny))
        return result

    # ── Draw ──
    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)
        self._draw_grid()
        self._draw_cursor()
        self._draw_particles()
        self._draw_ui()
        self._draw_message()
        if self.phase == Phase.VICTORY:
            self._draw_overlay("VICTORY!", pyxel.COLOR_LIME)
        elif self.phase == Phase.DEFEAT:
            self._draw_overlay("DEFEAT", pyxel.COLOR_RED)

    def _draw_grid(self) -> None:
        for y in range(GRID_H):
            for x in range(GRID_W):
                cell = self.grid[y][x]
                px = x * CELL_SIZE
                py = y * CELL_SIZE
                # Flash effect
                is_flashing = any(fx == x and fy == y for fx, fy, _ in self.flash_cells)
                if is_flashing:
                    flash_frame = next(t for fx, fy, t in self.flash_cells if fx == x and fy == y)
                    flash_color = pyxel.COLOR_WHITE if flash_frame % 4 < 2 else pyxel.COLOR_BLACK

                if cell.is_node:
                    color = NODE_COLORS.get(cell.owner, pyxel.COLOR_PURPLE)
                    if is_flashing:
                        color = flash_color
                    pyxel.rect(px + 2, py + 2, CELL_SIZE - 4, CELL_SIZE - 4, color)
                    # Node indicator: thicker border
                    pyxel.rectb(px + 1, py + 1, CELL_SIZE - 2, CELL_SIZE - 2, pyxel.COLOR_WHITE)
                    # Inner marker
                    pyxel.text(px + 8, py + 8, "N", pyxel.COLOR_WHITE)
                elif cell.is_player:
                    color = CELL_COLORS.get(cell.owner, pyxel.COLOR_WHITE)
                    if is_flashing:
                        color = flash_color
                    pyxel.rect(px + 2, py + 2, CELL_SIZE - 4, CELL_SIZE - 4, color)
                elif cell.is_enemy:
                    color = ENEMY_COLOR
                    if is_flashing:
                        color = flash_color
                    pyxel.rect(px + 2, py + 2, CELL_SIZE - 4, CELL_SIZE - 4, color)
                    # Enemy marker: small X
                    pyxel.text(px + 8, py + 8, "E", pyxel.COLOR_RED)
                else:
                    pyxel.rect(px + 2, py + 2, CELL_SIZE - 4, CELL_SIZE - 4, pyxel.COLOR_NAVY)

                # Grid lines
                pyxel.rectb(px, py, CELL_SIZE, CELL_SIZE, GRID_LINE_COLOR)

    def _draw_cursor(self) -> None:
        px = self.cursor_x * CELL_SIZE
        py = self.cursor_y * CELL_SIZE
        # Pulsing cursor
        pulse = (pyxel.frame_count // 15) % 2
        color = CURSOR_COLOR if pulse else pyxel.COLOR_ORANGE
        pyxel.rectb(px + 1, py + 1, CELL_SIZE - 2, CELL_SIZE - 2, color)
        pyxel.rectb(px, py, CELL_SIZE, CELL_SIZE, color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = min(1.0, p.life / 20.0)
            if alpha > 0.3:
                pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_ui(self) -> None:
        ui_y = SCREEN_H + 4
        # Energy bar
        bar_w = 80
        bar_h = 6
        pyxel.rect(4, ui_y, bar_w, bar_h, pyxel.COLOR_NAVY)
        energy_pct = self.energy / MAX_ENERGY
        fill_w = int(bar_w * energy_pct)
        bar_color = pyxel.COLOR_CYAN if energy_pct > 0.3 else pyxel.COLOR_RED
        pyxel.rect(4, ui_y, fill_w, bar_h, bar_color)
        pyxel.text(88, ui_y - 1, f"E:{self.energy:.0f}", pyxel.COLOR_CYAN)

        # Score
        pyxel.text(4, ui_y + 10, f"SCORE:{self.score}", pyxel.COLOR_WHITE)

        # Combo
        if self.combo > 1:
            pyxel.text(4, ui_y + 20, f"COMBO x{self.combo}", pyxel.COLOR_YELLOW)

        # Nodes
        pyxel.text(140, ui_y - 1, f"NODES:{self.nodes_created}", pyxel.COLOR_PURPLE)

        # Tick
        pyxel.text(140, ui_y + 10, f"TICK:{self.tick_count}", pyxel.COLOR_GRAY)

        # Controls hint
        pyxel.text(4, ui_y + 30, "WASD:move SPACE:seed CLICK:seed", pyxel.COLOR_GRAY)

    def _draw_message(self) -> None:
        if self.message and self.message_timer > 0:
            alpha = min(1.0, self.message_timer / 15.0)
            if alpha > 0.3:
                msg_w = len(self.message) * 4 + 8
                msg_x = (SCREEN_W - msg_w) // 2
                msg_y = SCREEN_H // 2 - 4
                msg_color = pyxel.COLOR_YELLOW if self.message_timer % 6 < 3 else pyxel.COLOR_WHITE
                pyxel.text(msg_x, msg_y, self.message, msg_color)

    def _draw_overlay(self, text: str, color: int) -> None:
        """Draw game-over overlay."""
        # Darken screen
        for y in range(0, SCREEN_H, 4):
            for x in range(0, SCREEN_W, 4):
                pyxel.pset(x, y, pyxel.COLOR_BLACK)

        # Big text
        text_x = (SCREEN_W - len(text) * 4) // 2
        text_y = SCREEN_H // 2 - 6
        pyxel.text(text_x, text_y, text, color)
        # Restart hint
        hint = "CLICK or SPACE to retry"
        hint_x = (SCREEN_W - len(hint) * 4) // 2
        pyxel.text(hint_x, text_y + 12, hint, pyxel.COLOR_GRAY)

        # Score summary
        score_text = f"FINAL SCORE: {self.score}"
        score_x = (SCREEN_W - len(score_text) * 4) // 2
        pyxel.text(score_x, text_y + 24, score_text, pyxel.COLOR_WHITE)


# ── Entry Point ──
def main() -> None:
    Game()


if __name__ == "__main__":
    main()
