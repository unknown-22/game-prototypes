"""082_chain_fleet — CHAIN FLEET
Battleship-style grid deduction with color-match combo chains.

Click a 10x8 grid to find hidden enemy ships. Each ship cell has a color
(RED, GREEN, BLUE, YELLOW). Same-color consecutive hits build COMBO.
COMBO >= 3 triggers SURGE: BFS flood-fill reveals all orthogonally
adjacent same-color cells. Miss builds HEAT; when HEAT >= 8, enemy
fires back (-1 HP of 3).

Core fun: "Chaining same-color hits to hit COMBO 3+, unleashing SURGE
that cascades through the fleet — revealing half the grid at once."
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import pyxel

# ── Constants ──────────────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
FPS = 60

GRID_W = 10
GRID_H = 8
CELL_SIZE = 24
GRID_OX = 40
GRID_OY = 24

SHIP_SIZES: tuple[int, ...] = (4, 3, 3, 2, 2)
SHIP_COLORS: tuple[int, ...] = (8, 3, 6, 10)  # RED, GREEN, BLUE, YELLOW
COLOR_NAMES: tuple[str, ...] = ("RED", "GREEN", "BLUE", "YELLOW")

MAX_HEAT = 8
MAX_HP = 3

SURGE_DURATION = 20


# ── Data Classes ───────────────────────────────────────────────────────────────


@dataclass
class ShipCell:
    x: int
    y: int
    color: int


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
    life: int
    color: int


# ── Game ───────────────────────────────────────────────────────────────────────


class Game:
    """CHAIN FLEET — Battleship with Color-Match Combo Chains."""

    def __init__(self) -> None:
        pyxel.init(
            SCREEN_W, SCREEN_H,
            title="CHAIN FLEET",
            fps=FPS,
            display_scale=2,
        )
        font_path = str(Path(__file__).with_name("k8x12.bdf"))
        pyxel.load(font_path, True, True)

        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── State Management ──────────────────────────────────────────────────

    def reset(self) -> None:
        self.grid_w: int = GRID_W
        self.grid_h: int = GRID_H
        self.cell_size: int = CELL_SIZE
        self.grid_ox: int = GRID_OX
        self.grid_oy: int = GRID_OY
        self.cells: list[list[ShipCell | None]] = [
            [None for _ in range(GRID_W)] for _ in range(GRID_H)
        ]
        self.revealed: list[list[bool]] = [
            [False for _ in range(GRID_W)] for _ in range(GRID_H)
        ]
        self.combo: int = 0
        self.max_combo: int = 0
        self.last_hit_color: int | None = None
        self.heat: int = 0
        self.max_heat: int = MAX_HEAT
        self.hp: int = MAX_HP
        self.max_hp: int = MAX_HP
        self.score: int = 0
        self.ships_remaining: int = 0
        self.total_ship_cells: int = 0
        self.phase: str = "TITLE"
        self.surge_cells: list[tuple[int, int]] = []
        self.surge_timer: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._rng: random.Random = random.Random()
        self._mouse_was_pressed: bool = False
        self._title_blink: int = 0
        self._enemy_strike_timer: int = 0
        self._enemy_strike_text: str = ""
        self._win_result: str = ""

    def _start_game(self) -> None:
        self.phase = "PLAYING"
        self.combo = 0
        self.max_combo = 0
        self.last_hit_color = None
        self.heat = 0
        self.hp = MAX_HP
        self.score = 0
        self.surge_cells.clear()
        self.surge_timer = 0
        self.particles.clear()
        self.floating_texts.clear()
        self._mouse_was_pressed = False
        self._enemy_strike_timer = 0
        self._enemy_strike_text = ""
        self.cells = [[None for _ in range(GRID_W)] for _ in range(GRID_H)]
        self.revealed = [[False for _ in range(GRID_W)] for _ in range(GRID_H)]
        self._generate_fleet()

    # ── Fleet Generation ──────────────────────────────────────────────────

    def _generate_fleet(self) -> None:
        ships: list[list[tuple[int, int]]] = []
        for size in SHIP_SIZES:
            color = self._rng.choice(SHIP_COLORS)
            placed = False
            for _attempt in range(200):
                horizontal = self._rng.random() < 0.5
                if horizontal:
                    x = self._rng.randint(0, GRID_W - size)
                    y = self._rng.randint(0, GRID_H - 1)
                else:
                    x = self._rng.randint(0, GRID_W - 1)
                    y = self._rng.randint(0, GRID_H - size)

                positions: list[tuple[int, int]] = []
                if horizontal:
                    positions = [(x + i, y) for i in range(size)]
                else:
                    positions = [(x, y + i) for i in range(size)]

                occupied = False
                for px, py in positions:
                    if self.cells[py][px] is not None:
                        occupied = True
                        break

                if not occupied:
                    ships.append(positions)
                    for px, py in positions:
                        self.cells[py][px] = ShipCell(x=px, y=py, color=color)
                    placed = True
                    break

            if not placed:
                break

        self.total_ship_cells = sum(
            1 for row in self.cells for c in row if c is not None
        )
        self.ships_remaining = self.total_ship_cells

    # ── Update ────────────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == "TITLE":
            self._update_title()
        elif self.phase == "PLAYING":
            self._update_playing()
        elif self.phase == "GAME_OVER":
            self._update_game_over()

    def _update_title(self) -> None:
        self._title_blink += 1
        if pyxel.btnp(pyxel.KEY_RETURN) or (
            pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and not self._mouse_was_pressed
        ):
            self._rng = random.Random()
            self._start_game()

    def _update_playing(self) -> None:
        self._update_particles()
        self._update_floating_texts()

        if self._enemy_strike_timer > 0:
            self._enemy_strike_timer -= 1

        if self.surge_timer > 0:
            self.surge_timer -= 1
            if self.surge_timer == 0:
                self.surge_cells.clear()

        mouse_pressed = pyxel.btn(pyxel.MOUSE_BUTTON_LEFT)
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and not self._mouse_was_pressed:
            gx = (pyxel.mouse_x - self.grid_ox) // self.cell_size
            gy = (pyxel.mouse_y - self.grid_oy) // self.cell_size
            if 0 <= gx < self.grid_w and 0 <= gy < self.grid_h:
                self._handle_click(gx, gy)

        self._mouse_was_pressed = mouse_pressed

    def _update_game_over(self) -> None:
        self._update_particles()
        self._update_floating_texts()
        mouse_pressed = pyxel.btn(pyxel.MOUSE_BUTTON_LEFT)
        if pyxel.btnp(pyxel.KEY_RETURN) or (
            pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and not self._mouse_was_pressed
        ):
            self.reset()
        self._mouse_was_pressed = mouse_pressed

    # ── Click Handling ────────────────────────────────────────────────────

    def _handle_click(self, gx: int, gy: int) -> None:
        if self.revealed[gy][gx]:
            return

        self.revealed[gy][gx] = True
        cell = self.cells[gy][gx]

        if cell is not None:
            if cell.color == self.last_hit_color:
                self.combo += 1
                points = 10 * (1 + self.combo)
                self.score += points
            else:
                self.combo = 1
                points = 10
                self.score += points

            self.last_hit_color = cell.color
            self.max_combo = max(self.max_combo, self.combo)
            self.ships_remaining -= 1

            cx = self.grid_ox + gx * self.cell_size + self.cell_size // 2
            cy = self.grid_oy + gy * self.cell_size + self.cell_size // 2
            self._spawn_hit_particles(cx, cy, cell.color)
            self._spawn_floating_text(cx, cy, f"+{points}", cell.color)

            if self.combo >= 3:
                self._surge(gx, gy, cell.color)

            if self.ships_remaining <= 0:
                self.phase = "GAME_OVER"
                self._win_result = "VICTORY"

        else:
            self.combo = 0
            self.last_hit_color = None
            self.heat += 1

            cx = self.grid_ox + gx * self.cell_size + self.cell_size // 2
            cy = self.grid_oy + gy * self.cell_size + self.cell_size // 2
            self._spawn_miss_particles(cx, cy)
            self._spawn_floating_text(cx, cy, "MISS", 13)

            if self.heat >= self.max_heat:
                self.hp -= 1
                self.heat = 0
                self._enemy_strike_timer = 30
                self._enemy_strike_text = "ENEMY STRIKE!"
                if self.hp <= 0:
                    self.phase = "GAME_OVER"
                    self._win_result = "DEFEATED"

    # ── SURGE ─────────────────────────────────────────────────────────────

    def _surge(self, sx: int, sy: int, color: int) -> None:
        to_reveal = self._bfs_surge(sx, sy, color)
        for gx, gy in to_reveal:
            if not self.revealed[gy][gx]:
                self.revealed[gy][gx] = True
                self.ships_remaining -= 1
                points = 15 * self.combo
                self.score += points
                cx = self.grid_ox + gx * self.cell_size + self.cell_size // 2
                cy = self.grid_oy + gy * self.cell_size + self.cell_size // 2
                self._spawn_surge_particles(cx, cy, color)

        self.surge_cells = to_reveal
        self.surge_timer = SURGE_DURATION

        if self.ships_remaining <= 0:
            self.phase = "GAME_OVER"
            self._win_result = "VICTORY"

    def _bfs_surge(self, sx: int, sy: int, color: int) -> list[tuple[int, int]]:
        result: list[tuple[int, int]] = []
        visited: set[tuple[int, int]] = set()
        queue: list[tuple[int, int]] = [(sx, sy)]
        visited.add((sx, sy))

        while queue:
            cx, cy = queue.pop(0)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if (
                    0 <= nx < self.grid_w
                    and 0 <= ny < self.grid_h
                    and (nx, ny) not in visited
                ):
                    visited.add((nx, ny))
                    if not self.revealed[ny][nx]:
                        cell = self.cells[ny][nx]
                        if cell is not None and cell.color == color:
                            result.append((nx, ny))
                            queue.append((nx, ny))

        return result

    # ── Particles ─────────────────────────────────────────────────────────

    def _spawn_hit_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(6):
            self.particles.append(Particle(
                x=x, y=y,
                vx=self._rng.uniform(-1.5, 1.5),
                vy=self._rng.uniform(-1.5, 1.5),
                life=12,
                color=color,
            ))

    def _spawn_miss_particles(self, x: float, y: float) -> None:
        for _ in range(4):
            self.particles.append(Particle(
                x=x, y=y,
                vx=self._rng.uniform(-1.0, 1.0),
                vy=self._rng.uniform(-1.0, 1.0),
                life=8,
                color=13,  # GRAY
            ))

    def _spawn_surge_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(4):
            self.particles.append(Particle(
                x=x, y=y,
                vx=self._rng.uniform(-2.0, 2.0),
                vy=self._rng.uniform(-2.0, 2.0),
                life=15,
                color=7,  # WHITE flash
            ))

    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        self.floating_texts.append(FloatingText(
            x=x - len(text) * 2,
            y=y - 8,
            text=text,
            life=30,
            color=color,
        ))

    def _update_particles(self) -> None:
        survivors: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                survivors.append(p)
        self.particles = survivors

    def _update_floating_texts(self) -> None:
        survivors: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life > 0:
                survivors.append(ft)
        self.floating_texts = survivors

    # ── Draw ──────────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(1)  # NAVY background

        if self.phase == "TITLE":
            self._draw_title()
        elif self.phase == "PLAYING":
            self._draw_playing()
        elif self.phase == "GAME_OVER":
            self._draw_game_over()

    def _draw_title(self) -> None:
        self._draw_text_center("CHAIN FLEET", SCREEN_H // 2 - 60, 8)
        self._draw_text_center("Battleship Color Combo", SCREEN_H // 2 - 40, 7)

        y = SCREEN_H // 2 - 10
        self._draw_text_center("Click grid cells to find ships", y, 7)
        y += 16
        self._draw_text_center("Same-color hits build COMBO", y, 7)
        y += 16
        self._draw_text_center("COMBO x3 = SURGE chain reveal!", y, 10)
        y += 16
        self._draw_text_center("Misses build HEAT - enemy strikes back", y, 7)

        y += 30
        self._draw_text_center("Ships: 14 cells / 4 colors", y, 13)

        if (self._title_blink // 30) % 2 == 0:
            self._draw_text_center("CLICK TO START", SCREEN_H - 40, 7)

        # Color legend
        for i, (name, col) in enumerate(zip(COLOR_NAMES, SHIP_COLORS)):
            x = 44 + i * 64
            yy = SCREEN_H - 50
            pyxel.rect(x, yy, 12, 12, col)
            pyxel.text(x + 16, yy + 2, name, col)

    def _draw_playing(self) -> None:
        self._draw_grid()
        self._draw_hud()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_enemy_strike()
        self._draw_surge_flash()

    def _draw_grid(self) -> None:
        for gy in range(self.grid_h):
            for gx in range(self.grid_w):
                x = self.grid_ox + gx * self.cell_size
                y = self.grid_oy + gy * self.cell_size

                if self.revealed[gy][gx]:
                    cell = self.cells[gy][gx]
                    if cell is not None:
                        col = cell.color
                    else:
                        col = 5  # DARK_BLUE for miss
                else:
                    col = 13  # GRAY for unrevealed

                pyxel.rect(x + 1, y + 1, self.cell_size - 2, self.cell_size - 2, col)

        for gy in range(self.grid_h + 1):
            y = self.grid_oy + gy * self.cell_size
            pyxel.line(self.grid_ox, y, self.grid_ox + self.grid_w * self.cell_size, y, 7)
        for gx in range(self.grid_w + 1):
            x = self.grid_ox + gx * self.cell_size
            pyxel.line(x, self.grid_oy, x, self.grid_oy + self.grid_h * self.cell_size, 7)

    def _draw_surge_flash(self) -> None:
        if self.surge_timer <= 0:
            return
        for gx, gy in self.surge_cells:
            x = self.grid_ox + gx * self.cell_size
            y = self.grid_oy + gy * self.cell_size
            pulse = self.surge_timer % 6 < 3
            if pulse:
                pyxel.rectb(x, y, self.cell_size, self.cell_size, 7)

    def _draw_hud(self) -> None:
        # Top bar background
        pyxel.rect(0, 0, SCREEN_W, 22, 5)
        pyxel.line(0, 22, SCREEN_W, 22, 7)

        # COMBO
        combo_color = 12 if self.combo >= 3 else 7  # CYAN if active, else WHITE
        pyxel.text(4, 5, f"COMBO:{self.combo}", combo_color)

        # HEAT
        heat_color = 8 if self.heat >= self.max_heat - 2 else 7
        pyxel.text(80, 5, f"HEAT:{self.heat}", heat_color)

        # HP
        hp_color = 8 if self.hp <= 1 else 7
        pyxel.text(136, 5, f"HP:{self.hp}", hp_color)

        # SCORE
        pyxel.text(192, 5, f"SCORE:{self.score}", 10)

        # Right panel
        px = self.grid_ox + self.grid_w * self.cell_size + 8
        pyxel.text(px, 26, "SHIPS", 7)
        pyxel.text(px, 38, f"{self.ships_remaining}", 10)

        # Last hit color indicator
        if self.last_hit_color is not None:
            pyxel.rect(px, 56, 16, 16, self.last_hit_color)
            pyxel.rectb(px, 56, 16, 16, 7)

        # HEAT bar
        bar_x = 4
        bar_y = SCREEN_H - 20
        bar_w = 120
        bar_h = 10
        pyxel.rectb(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2, 7)
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, 5)
        heat_w = int(bar_w * self.heat / self.max_heat)
        if heat_w > 0:
            heat_bar_color = 8 if self.heat >= self.max_heat - 2 else 9
            pyxel.rect(bar_x, bar_y, heat_w, bar_h, heat_bar_color)
        pyxel.text(bar_x + 2, bar_y - 10, "HEAT", 7)

        # HP hearts
        for i in range(self.max_hp):
            hx = SCREEN_W - 30 - i * 16
            hy = SCREEN_H - 20
            if i < self.hp:
                pyxel.rect(hx, hy, 12, 12, 8)
            else:
                pyxel.rectb(hx, hy, 12, 12, 13)
            pyxel.rectb(hx, hy, 12, 12, 7)

    def _draw_enemy_strike(self) -> None:
        if self._enemy_strike_timer > 0:
            pulse = self._enemy_strike_timer % 10 < 5
            col = 8 if pulse else 10
            tw = len("ENEMY STRIKE!") * 4
            pyxel.text(
                SCREEN_W // 2 - tw // 2,
                SCREEN_H // 2 - 30,
                self._enemy_strike_text,
                col,
            )

    def _draw_particles(self) -> None:
        for p in self.particles:
            px = int(p.x)
            py = int(p.y)
            alpha = p.life / 12.0
            col = p.color if alpha > 0.5 else (13 if alpha > 0.25 else 1)
            if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
                pyxel.pset(px, py, col)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 30.0
            col = ft.color if alpha > 0.5 else 13
            px = int(ft.x)
            py = int(ft.y)
            if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
                pyxel.text(px, py, ft.text, col)

    def _draw_game_over(self) -> None:
        self._draw_grid()
        self._draw_hud()
        self._draw_particles()
        self._draw_floating_texts()

        # Dark overlay
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, 1)

        if self._win_result == "VICTORY":
            result = "VICTORY!"
            col = 10  # YELLOW
        else:
            result = "DEFEATED"
            col = 8  # RED

        self._draw_text_center(result, 50, col)

        lines = [
            f"SCORE: {self.score}",
            f"MAX COMBO: {self.max_combo}",
        ]
        y = 90
        for line in lines:
            self._draw_text_center(line, y, 7)
            y += 24

        y += 10
        if (pyxel.frame_count // 30) % 2 == 0:
            self._draw_text_center("CLICK TO RETRY", y + 20, 7)

    def _draw_text_center(self, text: str, y: int, color: int) -> None:
        tx = SCREEN_W // 2 - len(text) * 2
        pyxel.text(tx + 1, y + 1, text, 5)
        pyxel.text(tx, y, text, color)

    # ── Overridable for testing ───────────────────────────────────────────
    __test__: bool = False


if __name__ == "__main__":
    Game()
