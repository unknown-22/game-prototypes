"""Chain Reactor — Color-matching incremental reactor grid game."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum

import pyxel


class Phase(Enum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


@dataclass
class Reactor:
    col: int
    row: int
    color: int
    tier: int = 1


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


class Game:
    GRID_COLS = 4
    GRID_ROWS = 4
    CELL_SIZE = 48
    GRID_OFFSET_X = 64
    GRID_OFFSET_Y = 60
    TARGET_ENERGY = 1000
    MAX_HEAT = 100
    TICK_INTERVAL = 30
    SUPER_COMBO_THRESHOLD = 5
    SUPER_DURATION = 300
    HEAT_PER_TICK = 2
    HEAT_DECAY = 0.5
    ENERGY_PER_TIER = [1, 3, 7]
    UPGRADE_COST = [20, 60]
    PLACE_COST = 10
    COOLING_COST = 30
    COLORS = [8, 3, 5, 10]
    COLOR_NAMES = ["RED", "GREEN", "BLUE", "YELLOW"]

    def __init__(self) -> None:
        self._rng: random.Random = random.Random()
        self.reset()

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.grid: list[list[Reactor | None]] = [[None] * 4 for _ in range(4)]
        self.energy: float = 50.0
        self.total_energy: float = 0.0
        self.heat: float = 0.0
        self.combo: int = 0
        self.max_combo: int = 0
        self.last_color: int = -1
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.tick_timer: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.hover_col: int = -1
        self.hover_row: int = -1
        self.selected_col: int = -1
        self.selected_row: int = -1
        self.win: bool = False
        self._rng = random.Random()

    # --- Grid helpers ---

    def _get_grid_rect(self, col: int, row: int) -> tuple[int, int, int, int]:
        x = self.GRID_OFFSET_X + col * self.CELL_SIZE
        y = self.GRID_OFFSET_Y + row * self.CELL_SIZE
        return (x, y, self.CELL_SIZE, self.CELL_SIZE)

    def _screen_to_grid(self, mx: int, my: int) -> tuple[int, int]:
        if (
            mx < self.GRID_OFFSET_X
            or my < self.GRID_OFFSET_Y
            or mx >= self.GRID_OFFSET_X + self.GRID_COLS * self.CELL_SIZE
            or my >= self.GRID_OFFSET_Y + self.GRID_ROWS * self.CELL_SIZE
        ):
            return (-1, -1)
        col = (mx - self.GRID_OFFSET_X) // self.CELL_SIZE
        row = (my - self.GRID_OFFSET_Y) // self.CELL_SIZE
        return (col, row)

    # --- Combo / Neighbor logic ---

    def _count_same_color_neighbors(self, col: int, row: int, color: int) -> int:
        count = 0
        for dc, dr in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nc, nr = col + dc, row + dr
            if 0 <= nc < self.GRID_COLS and 0 <= nr < self.GRID_ROWS:
                neighbor = self.grid[nr][nc]
                if neighbor is not None and neighbor.color == color:
                    count += 1
        return count

    def _check_chain(self, color: int) -> None:
        if self.last_color == -1 or self.last_color != color:
            self.combo = 1
            self.last_color = color
            return
        self.combo += 1
        self.last_color = color
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        if self.combo >= self.SUPER_COMBO_THRESHOLD and not self.super_mode:
            self.super_mode = True
            self.super_timer = self.SUPER_DURATION
            self._spawn_super_particles()
            self.floating_texts.append(
                FloatingText(160, 100, "SUPER!", 40, 10)
            )
        elif self.combo >= 3:
            self.floating_texts.append(
                FloatingText(260, 30, f"COMBO! {self.combo}x", 30, 10)
            )

    # --- Actions ---

    def _place_reactor(self, col: int, row: int) -> None:
        color = self._rng.randint(0, 3)
        self.grid[row][col] = Reactor(col, row, color, 1)
        self.energy -= self.PLACE_COST
        x, y, _, _ = self._get_grid_rect(col, row)
        cx = x + self.CELL_SIZE // 2
        cy = y + self.CELL_SIZE // 2
        self._spawn_particles(cx, cy, self.COLORS[color], 8)
        self._check_chain(color)
        self.floating_texts.append(
            FloatingText(cx, cy - 10, f"-{self.PLACE_COST}", 20, 7)
        )

    def _upgrade_reactor(self, col: int, row: int) -> None:
        reactor = self.grid[row][col]
        if reactor is None or reactor.tier >= 3:
            return
        cost = self.UPGRADE_COST[reactor.tier - 1]
        if self.energy < cost:
            return
        reactor.tier += 1
        self.energy -= cost
        x, y, _, _ = self._get_grid_rect(col, row)
        cx = x + self.CELL_SIZE // 2
        cy = y + self.CELL_SIZE // 2
        self._spawn_particles(cx, cy, self.COLORS[reactor.color], 12)
        self.floating_texts.append(
            FloatingText(cx, cy - 10, "UPGRADE!", 25, 7)
        )

    def _cool_down(self) -> None:
        if self.energy < self.COOLING_COST:
            return
        self.energy -= self.COOLING_COST
        self.heat = max(0.0, self.heat - 20.0)
        self.floating_texts.append(
            FloatingText(160, 200, "-HEAT", 25, 12)
        )

    def _handle_click(self, col: int, row: int) -> None:
        if self.grid[row][col] is None:
            if self.energy >= self.PLACE_COST:
                self._place_reactor(col, row)
        else:
            reactor = self.grid[row][col]
            if reactor is not None and reactor.tier < 3:
                cost = self.UPGRADE_COST[reactor.tier - 1]
                if self.energy >= cost:
                    self._upgrade_reactor(col, row)

    # --- Production / Update ---

    def _all_reactors(self) -> list[Reactor]:
        result: list[Reactor] = []
        for row in range(self.GRID_ROWS):
            for col in range(self.GRID_COLS):
                r = self.grid[row][col]
                if r is not None:
                    result.append(r)
        return result

    def _chain_multiplier(self, col: int, row: int, color: int) -> float:
        neighbors = self._count_same_color_neighbors(col, row, color)
        if neighbors >= 2:
            return 1.0 + 0.5 * (neighbors - 1)
        return 1.0

    def _update_production(self) -> None:
        reactors = self._all_reactors()
        total_produced = 0.0
        for reactor in reactors:
            base = float(self.ENERGY_PER_TIER[reactor.tier - 1])
            chain = self._chain_multiplier(reactor.col, reactor.row, reactor.color)
            super_mult = 3.0 if self.super_mode else 1.0
            produced = base * chain * super_mult
            total_produced += produced
            x, y, _, _ = self._get_grid_rect(reactor.col, reactor.row)
            cx = x + self.CELL_SIZE // 2
            cy = y + self.CELL_SIZE // 2
            self.floating_texts.append(
                FloatingText(cx + self._rng.uniform(-6, 6), cy - 5,
                             f"+{produced:.0f}", 15, self.COLORS[reactor.color])
            )
            self._spawn_particles(cx, cy, self.COLORS[reactor.color], 2)
        self.energy += total_produced
        self.total_energy += total_produced
        self.heat += self.HEAT_PER_TICK * len(reactors)
        if self.heat >= self.MAX_HEAT:
            self.heat = self.MAX_HEAT
            self.phase = Phase.GAME_OVER
            self.win = False
            return
        if self.total_energy >= self.TARGET_ENERGY:
            self.phase = Phase.GAME_OVER
            self.win = True

    def _update_tick(self) -> None:
        self.tick_timer += 1
        if self.tick_timer >= self.TICK_INTERVAL:
            self.tick_timer = 0
            self._update_production()

    def _update_heat(self) -> None:
        # Check threshold BEFORE decaying (avoid decay-below-threshold pitfall)
        if self.heat >= self.MAX_HEAT:
            self.heat = self.MAX_HEAT
            self.phase = Phase.GAME_OVER
            self.win = False
            return
        self.heat = max(0.0, self.heat - self.HEAT_DECAY)

    def _update_super(self) -> None:
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0

    # --- Particles ---

    def _spawn_particles(self, x: float, y: float, color: int, count: int = 8) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 1.5)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = self._rng.randint(15, 30)
            self.particles.append(Particle(x, y, vx, vy, life, color))

    def _spawn_super_particles(self) -> None:
        reactors = self._all_reactors()
        for reactor in reactors:
            x, y, _, _ = self._get_grid_rect(reactor.col, reactor.row)
            cx = x + self.CELL_SIZE // 2
            cy = y + self.CELL_SIZE // 2
            self._spawn_particles(cx, cy, self._rng.choice(self.COLORS), 5)

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    # --- Floating texts ---

    def _update_floating_texts(self) -> None:
        alive: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= 1.0
            ft.life -= 1
            if ft.life > 0:
                alive.append(ft)
        self.floating_texts = alive

    # --- Full update cycle (called from App.update) ---

    def update_playing(self) -> None:
        self._update_tick()
        self._update_heat()
        self._update_super()
        self._update_particles()
        self._update_floating_texts()


class App:
    def __init__(self) -> None:
        pyxel.init(320, 240, title="Chain Reactor", display_scale=2)
        self.game = Game()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        if self.game.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.game.reset()
                self.game.phase = Phase.PLAYING
            return

        if self.game.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_R):
                self.game.reset()
                self.game.phase = Phase.PLAYING
            return

        if self.game.phase == Phase.PLAYING:
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            col, row = self.game._screen_to_grid(mx, my)
            self.game.hover_col = col
            self.game.hover_row = row

            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                if col >= 0 and row >= 0:
                    self.game._handle_click(col, row)

            if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT) or pyxel.btnp(pyxel.KEY_SPACE):
                self.game._cool_down()

            self.game.update_playing()

    def draw(self) -> None:
        pyxel.cls(0)

        if self.game.phase == Phase.TITLE:
            self._draw_title()
        elif self.game.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.game.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(115, 60, "CHAIN REACTOR", 7)
        pyxel.text(55, 90, "Place reactors. Chain colors. Reach 1000 energy!", 13)
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(125, 150, "Click to start", 7)
        pyxel.text(20, 180, "Click: place/upgrade  |  Right-click: cool  |  SPACE: cool", 13)

    def _draw_playing(self) -> None:
        g = self.game

        pyxel.text(10, 4, f"ENERGY: {g.energy:.0f}", 7)
        pyxel.text(10, 16, f"TOTAL: {g.total_energy:.0f} / {g.TARGET_ENERGY}", 13)

        bar_w = 300
        heat_ratio = g.heat / g.MAX_HEAT
        heat_color = 8 if g.heat > 70 else 7
        pyxel.rect(10, 220, bar_w, 12, 13)
        pyxel.rect(10, 220, int(bar_w * heat_ratio), 12, 8)
        pyxel.text(14, 222, f"HEAT: {g.heat:.0f}%", heat_color)

        if g.combo > 1:
            pyxel.text(250, 30, f"COMBO: {g.combo}x", 10)

        if g.super_mode:
            super_color = (pyxel.frame_count // 4) % 4 + 8
            pyxel.text(120, 46, "SUPER! 3x", super_color)

        for row in range(g.GRID_ROWS):
            for col in range(g.GRID_COLS):
                x, y, w, h = g._get_grid_rect(col, row)
                reactor = g.grid[row][col]
                if reactor is None:
                    pyxel.rectb(x, y, w, h, 13)
                    pyxel.rect(x + 2, y + 2, w - 4, h - 4, 5)
                else:
                    color = g.COLORS[reactor.color]
                    pyxel.rectb(x, y, w, h, color)
                    pyxel.rect(x + 2, y + 2, w - 4, h - 4, color)
                    tier_str = str(reactor.tier)
                    pyxel.text(x + w // 2 - 2, y + h // 2 - 4, tier_str, 7)

        if g.hover_col >= 0 and g.hover_row >= 0:
            x, y, w, h = g._get_grid_rect(g.hover_col, g.hover_row)
            pyxel.rectb(x, y, w, h, 6)

        for p in g.particles:
            alpha = p.life / 30.0
            if alpha > 0:
                pyxel.pset(int(p.x), int(p.y), p.color if alpha > 0.3 else 13)

        for ft in g.floating_texts:
            if ft.life > 0:
                pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_game_over(self) -> None:
        g = self.game
        if g.win:
            pyxel.text(130, 80, "YOU WIN!", 7)
        else:
            pyxel.text(115, 80, "GAME OVER", 7)

        pyxel.text(90, 110, f"Total Energy: {g.total_energy:.0f}", 13)
        pyxel.text(105, 130, f"Max Combo: {g.max_combo}x", 10)
        pyxel.text(85, 150, f"Final Heat: {g.heat:.0f}%", 13)

        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(115, 190, "Click to retry", 7)


def main() -> None:
    App()


if __name__ == "__main__":
    main()
