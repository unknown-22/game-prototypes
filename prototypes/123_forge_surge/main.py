"""
FORGE SURGE — Color-Match Metallurgy

Place same-color metal ingots on a forge grid.
Same-color adjacent ingots SYNTHESIZE into higher-tier alloys.
Chain consecutive syntheses for COMBO multipliers.
Manage HEAT — overheat and the forge destroys random ingots.

Core fun: 「同じ色の金属を連続で配置してCOMBOを決め、
一気に高Tierの合金に合成される瞬間が気持ちいい」
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import pyxel

# --- Colors (Pyxel palette) ---
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

# --- Screen ---
SCREEN_W = 320
SCREEN_H = 240

# --- Grid ---
COLS = 6
ROWS = 5
CELL = 32
GRID_X = 32
GRID_Y = 24

# --- Gameplay ---
INGOT_COLORS: list[int] = [RED, GREEN, LIGHT_BLUE, YELLOW]
N_COLORS = 4
MAX_TIER = 3
MAX_HEAT = 100.0
BURN_THRESHOLD = 90.0
CRITICAL_TICKS_LIMIT = 3
FREE_CELLS_LIMIT = 3
SYNTHESES_PER_COLOR_CHANGE = 2
BASE_HEAT_PER_PLACE = 5.0
HEAT_PER_NO_SYNTH = 12.0
HEAT_DECAY_RATE = 0.3
COMBO_HEAT_BONUS = 1.0
BASE_SCORE = 10

# --- UI ---
UI_X = 250


# --- Data Classes ---
@dataclass
class Ingot:
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


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# --- Game Class ---
class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Forge Surge", display_scale=2)
        self._rng: random.Random = random.Random()
        self._setup_font()
        self.reset()
        pyxel.run(self.update, self.draw)

    def _setup_font(self) -> None:
        font_path = Path(__file__).with_name("k8x12.bdf")
        if font_path.exists():
            pyxel.load(str(font_path))

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.grid: list[list[Ingot | None]] = [
            [None for _ in range(COLS)] for _ in range(ROWS)
        ]
        self.color_index: int = 0
        self.active_color: int = INGOT_COLORS[0]
        self.syntheses_this_color: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.heat_critical_ticks: int = 0
        self.shake_frames: int = 0
        self.game_timer: int = 0
        self._rng = random.Random()

    # --- Update ---
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self.game_timer += 1

        if self.shake_frames > 0:
            self.shake_frames -= 1

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            col = (pyxel.mouse_x - GRID_X) // CELL
            row = (pyxel.mouse_y - GRID_Y) // CELL
            if 0 <= col < COLS and 0 <= row < ROWS:
                self._place_ingot(col, row)

        self._update_heat()
        self._update_particles()
        self._update_floating_texts()

        free = self._count_free_cells()
        if free < FREE_CELLS_LIMIT or self.heat_critical_ticks >= CRITICAL_TICKS_LIMIT:
            self.phase = Phase.GAME_OVER

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.PLAYING

    # --- Core Logic ---
    def _place_ingot(self, col: int, row: int) -> bool:
        if self.grid[row][col] is not None:
            return False

        self.grid[row][col] = Ingot(color=self.active_color, tier=1)
        self.heat += BASE_HEAT_PER_PLACE

        cluster = self._find_cluster(col, row)
        if len(cluster) >= 2:
            self.score += self._synthesize(cluster)
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            self.heat += self.combo * COMBO_HEAT_BONUS
            self.syntheses_this_color += 1
            if self.syntheses_this_color >= SYNTHESES_PER_COLOR_CHANGE:
                self._change_active_color()
        else:
            self.combo = 0
            self.heat += HEAT_PER_NO_SYNTH

        return True

    def _find_cluster(self, col: int, row: int) -> set[tuple[int, int]]:
        target = self.grid[row][col]
        if target is None:
            return set()

        visited: set[tuple[int, int]] = set()
        queue: list[tuple[int, int]] = [(col, row)]
        visited.add((col, row))

        while queue:
            c, r = queue.pop(0)
            for dc, dr in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nc, nr = c + dc, r + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS and (nc, nr) not in visited:
                    neighbor = self.grid[nr][nc]
                    if (
                        neighbor is not None
                        and neighbor.color == target.color
                        and neighbor.tier == target.tier
                    ):
                        visited.add((nc, nr))
                        queue.append((nc, nr))

        return visited

    def _synthesize(self, cluster: set[tuple[int, int]]) -> int:
        tier = -1
        color = -1
        for c, r in cluster:
            ingot = self.grid[r][c]
            if ingot is not None:
                tier = ingot.tier
                color = ingot.color
                break

        new_tier = tier + 1
        if new_tier > MAX_TIER:
            return 0

        cx = sum(c for c, _ in cluster) / len(cluster)
        cy = sum(r for _, r in cluster) / len(cluster)
        centroid_col = max(0, min(COLS - 1, round(cx)))
        centroid_row = max(0, min(ROWS - 1, round(cy)))

        for c, r in cluster:
            self.grid[r][c] = None

        self.grid[centroid_row][centroid_col] = Ingot(color=color, tier=new_tier)

        px = GRID_X + centroid_col * CELL + CELL // 2
        py = GRID_Y + centroid_row * CELL + CELL // 2
        self._spawn_particles(px, py, color, 10)
        self._spawn_floating_text(
            px, py - 10, f"+{new_tier * (self.combo + 1) * BASE_SCORE}", WHITE
        )

        return new_tier * (self.combo + 1) * BASE_SCORE

    def _update_heat(self) -> None:
        if self.heat >= MAX_HEAT:
            self.heat_critical_ticks += 1
        else:
            self.heat = max(0.0, self.heat - HEAT_DECAY_RATE)
            self.heat_critical_ticks = max(0, self.heat_critical_ticks - 1)

        if self.heat > BURN_THRESHOLD:
            if self._rng.random() < 0.02:
                self._burn_random_ingot()

    def _burn_random_ingot(self) -> None:
        occupied: list[tuple[int, int]] = [
            (c, r)
            for r in range(ROWS)
            for c in range(COLS)
            if self.grid[r][c] is not None
        ]
        if not occupied:
            return
        c, r = self._rng.choice(occupied)
        self.grid[r][c] = None
        px = GRID_X + c * CELL + CELL // 2
        py = GRID_Y + r * CELL + CELL // 2
        self._spawn_particles(px, py, ORANGE, 6)
        self._spawn_floating_text(px, py, "BURN!", RED)
        self.shake_frames = 8
        self.combo = 0

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-2, 2)
            vy = self._rng.uniform(-2, 2)
            life = self._rng.randint(8, 20)
            self.particles.append(Particle(x, y, vx, vy, life, color))

    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        self.floating_texts.append(FloatingText(x, y, text, 30, color))

    def _count_free_cells(self) -> int:
        return sum(1 for r in range(ROWS) for c in range(COLS) if self.grid[r][c] is None)

    def _change_active_color(self) -> None:
        self.syntheses_this_color = 0
        self.color_index = (self.color_index + 1) % N_COLORS
        self.active_color = INGOT_COLORS[self.color_index]

    def _update_particles(self) -> None:
        for p in self.particles:
            p.vy += 0.15
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.8
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # --- Draw ---
    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 40, SCREEN_H // 2 - 30, "FORGE SURGE", WHITE)
        pyxel.text(
            SCREEN_W // 2 - 52,
            SCREEN_H // 2,
            "Click or press ENTER to start",
            WHITE,
        )
        pyxel.text(
            SCREEN_W // 2 - 68,
            SCREEN_H // 2 + 20,
            "Place same-color ingots to SYNTHESIZE",
            GREEN,
        )

    def _draw_playing(self) -> None:
        if self.shake_frames > 0:
            ox = self._rng.randint(-2, 2)
            oy = self._rng.randint(-2, 2)
            try:
                pyxel.camera(ox, oy)
            except BaseException:
                pass
        else:
            try:
                pyxel.camera(0, 0)
            except BaseException:
                pass

        self._draw_grid()
        self._draw_ui()
        self._draw_particles()
        self._draw_floating_texts()

    def _draw_grid(self) -> None:
        for r in range(ROWS):
            for c in range(COLS):
                x = GRID_X + c * CELL
                y = GRID_Y + r * CELL
                pyxel.rect(x, y, CELL, CELL, NAVY)
                pyxel.rectb(x, y, CELL, CELL, DARK_BLUE)

                ingot = self.grid[r][c]
                if ingot is not None:
                    self._draw_ingot(x, y, ingot)

    def _draw_ingot(self, x: int, y: int, ingot: Ingot) -> None:
        if ingot.tier == 1:
            pyxel.rect(x + 2, y + 2, CELL - 4, CELL - 4, ingot.color)
        elif ingot.tier == 2:
            pyxel.rect(x + 1, y + 1, CELL - 2, CELL - 2, ingot.color)
            pyxel.rectb(x + 1, y + 1, CELL - 2, CELL - 2, WHITE)
        elif ingot.tier >= 3:
            glow_color = PINK if pyxel.frame_count % 30 < 15 else ORANGE
            pyxel.rect(x + 1, y + 1, CELL - 2, CELL - 2, glow_color)
            pyxel.rect(x + 4, y + 4, CELL - 8, CELL - 8, ingot.color)

    def _draw_ui(self) -> None:
        # Active color swatch
        pyxel.rect(UI_X, 10, 40, 40, self.active_color)
        pyxel.text(UI_X + 45, 26, "ACTIVE", WHITE)

        # Heat bar background
        bar_x = UI_X
        bar_y = 60
        bar_w = 20
        bar_h = 100
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)

        # Heat bar fill
        fill_h = int((self.heat / MAX_HEAT) * bar_h)
        fill_y = bar_y + bar_h - fill_h
        if self.heat < 50:
            hc = GREEN
        elif self.heat < BURN_THRESHOLD:
            hc = YELLOW
        elif self.heat < MAX_HEAT:
            hc = ORANGE
        else:
            hc = RED
        pyxel.rect(bar_x, fill_y, bar_w, fill_h, hc)
        pyxel.text(bar_x, bar_y + bar_h + 2, f"HEAT {int(self.heat)}%", WHITE)

        # Score
        pyxel.text(UI_X, 170, f"SCORE: {self.score}", WHITE)

        # Combo
        combo_color = YELLOW if self.combo >= 4 else WHITE
        pyxel.text(UI_X, 182, f"COMBO x{self.combo}", combo_color)

        # Max combo
        pyxel.text(UI_X, 194, f"MAX: x{self.max_combo}", GRAY)

        # Free cells
        free = self._count_free_cells()
        free_color = RED if free < FREE_CELLS_LIMIT + 2 else WHITE
        pyxel.text(UI_X, 210, f"FREE: {free}", free_color)

        # Warning for critical heat
        if self.heat >= MAX_HEAT:
            warn_text = f"CRITICAL! {self.heat_critical_ticks}/{CRITICAL_TICKS_LIMIT}"
            pyxel.text(UI_X, 158, warn_text, RED)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 20.0
            if alpha > 0.3:
                pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 30.0
            if alpha > 0.2:
                pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 35, SCREEN_H // 2 - 30, "FORGE OVER", RED)
        pyxel.text(
            SCREEN_W // 2 - 40,
            SCREEN_H // 2,
            f"Score: {self.score}",
            WHITE,
        )
        pyxel.text(
            SCREEN_W // 2 - 40,
            SCREEN_H // 2 + 12,
            f"Max Combo: x{self.max_combo}",
            YELLOW,
        )
        pyxel.text(
            SCREEN_W // 2 - 52,
            SCREEN_H // 2 + 34,
            "Click or press ENTER to retry",
            WHITE,
        )


if __name__ == "__main__":
    Game()
