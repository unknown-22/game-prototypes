from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import ClassVar

import pyxel

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

COLORS: list[int] = [RED, LIME, DARK_BLUE, YELLOW]
COLOR_NAMES: list[str] = ["RED", "LIME", "DARK_BLUE", "YELLOW"]

SCREEN_W = 320
SCREEN_H = 240
COLS = 5
ROWS = 12
CELL = 20
GRID_X = 10
GRID_Y = 10
GAME_TIME = 60 * 30
MAX_HEAT = 100.0
SUPER_DURATION = 5 * 30
COMBO_THRESHOLD = 4
MAX_GUMBALLS = 30
BASE_SCORE = 10
HEAT_MISMATCH = 15.0
HEAT_DECAY_BASE = 0.05
HEAT_DECAY_MIN = 0.02
SPAWN_INTERVAL_BASE = 45
SPAWN_INTERVAL_MIN = 15
FPS = 30
CA_SPREAD_CHANCE = 0.20
MAX_SPREADS = 2
INFECTED_SCORE_MULT = 0.5
SUPER_SCORE_MULT = 3
MISMATCH_SCORE = 5


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Gumball:
    col: int
    row: int
    color: int
    alive: bool = True
    y: float = 0.0
    scale: float = 1.0
    infected: bool = False
    spread_count: int = 0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: float = 4.0


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int = 7


class Game:
    _initialized: ClassVar[bool] = False

    def __init__(self) -> None:
        if Game._initialized:
            return
        Game._initialized = True

        pyxel.init(SCREEN_W, SCREEN_H, title="Gumball Surge", display_scale=2, fps=FPS)
        self._rng = random.Random()
        self._pre_init_state()
        try:
            pyxel.load(str(Path(__file__).with_name("k8x12.bdf")))
        except Exception:
            pass
        pyxel.run(self._update, self._draw)

    def _pre_init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.gumballs: list[Gumball] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.score: int = 0
        self.high_score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.game_timer: int = GAME_TIME
        self.super_timer: int = 0
        self.super_mode: bool = False
        self.super_flash: int = 0
        self.last_color: int = -1
        self.spawn_timer: int = SPAWN_INTERVAL_BASE
        self.spawn_interval: int = SPAWN_INTERVAL_BASE
        self.heat_decay: float = HEAT_DECAY_BASE
        self.col_heights: list[int] = [0] * COLS
        self.shake_frames: int = 0
        self.frame: int = 0
        self.grid: list[list[int | None]] = [[None] * ROWS for _ in range(COLS)]

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.gumballs = []
        self.particles = []
        self.floating_texts = []
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.game_timer = GAME_TIME
        self.super_timer = 0
        self.super_mode = False
        self.super_flash = 0
        self.last_color = -1
        self.spawn_timer = SPAWN_INTERVAL_BASE
        self.spawn_interval = SPAWN_INTERVAL_BASE
        self.heat_decay = HEAT_DECAY_BASE
        self.col_heights = [0] * COLS
        self.shake_frames = 0
        self.grid = [[None] * ROWS for _ in range(COLS)]

    # --- Update ---

    def _update(self) -> None:
        self.frame += 1

        if self.shake_frames > 0:
            self.shake_frames -= 1
            if self.shake_frames > 0:
                sx = self._rng.randint(-3, 3)
                sy = self._rng.randint(-3, 3)
                pyxel.camera(sx, sy)
            else:
                pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()

    def _update_game_over(self) -> None:
        self._update_heat()
        self._update_particles()
        self._update_floating_texts()
        if pyxel.btnp(pyxel.KEY_R):
            self.phase = Phase.TITLE

    def _update_playing(self) -> None:
        self.game_timer -= 1
        if self._check_game_over():
            if self.score > self.high_score:
                self.high_score = self.score
            self.phase = Phase.GAME_OVER
            return

        self._update_spawn_interval()
        self._update_super_mode()
        self._update_spawning()
        self._ca_spread()
        self._update_heat()
        self._update_particles()
        self._update_floating_texts()

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._handle_click(pyxel.mouse_x, pyxel.mouse_y)

    # --- Spawning ---

    def _update_spawn_interval(self) -> None:
        elapsed_frames = GAME_TIME - self.game_timer
        periods = elapsed_frames // (3 * FPS)
        self.spawn_interval = max(SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_BASE - periods)

    def _update_spawning(self) -> None:
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_timer = self.spawn_interval
            self._spawn_gumballs()

    def _spawn_gumballs(self) -> None:
        if len(self.gumballs) >= MAX_GUMBALLS:
            return
        col = self._rng.randint(0, COLS - 1)
        if self.col_heights[col] >= ROWS:
            return
        color = self._rng.randint(0, len(COLORS) - 1)
        row = ROWS - 1 - self.col_heights[col]
        gumball = Gumball(col=col, row=row, color=color)
        self.gumballs.append(gumball)
        self.grid[col][row] = color
        self.col_heights[col] += 1

    # --- CA Spread ---

    def _ca_spread(self) -> None:
        spread_candidates: list[Gumball] = []
        for g in self.gumballs:
            if g.alive and g.spread_count < MAX_SPREADS:
                spread_candidates.append(g)

        for g in spread_candidates:
            if not (g.alive and g.spread_count < MAX_SPREADS):
                continue
            if self._rng.random() >= CA_SPREAD_CHANCE:
                continue
            self._try_spread(g)

    def _try_spread(self, g: Gumball) -> None:
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        self._rng.shuffle(directions)
        for dc, dr in directions:
            nc, nr = g.col + dc, g.row + dr
            if 0 <= nc < COLS and 0 <= nr < ROWS and self.grid[nc][nr] is None:
                if len(self.gumballs) >= MAX_GUMBALLS:
                    return
                new_g = Gumball(col=nc, row=nr, color=g.color, infected=True)
                self.gumballs.append(new_g)
                self.grid[nc][nr] = g.color
                self.col_heights[nc] += 1
                g.spread_count += 1
                return

    # --- Click Handling ---

    def _handle_click(self, mouse_x: int, mouse_y: int) -> None:
        grid_pos = self._xy_to_grid(mouse_x, mouse_y)
        if grid_pos is None:
            return
        col, row = grid_pos
        if self.grid[col][row] is None:
            return
        g = self._find_gumball(col, row)
        if g is None:
            return
        self._collect_gumball(g)

    def _collect_gumball(self, g: Gumball) -> None:
        if not g.alive:
            return
        g.alive = False

        is_match = self.super_mode or self.last_color == -1 or g.color == self.last_color

        if is_match:
            self.combo += 1
            mult = self._compute_combo_multiplier(self.combo)
            if g.infected:
                mult = max(1, int(mult * INFECTED_SCORE_MULT))
            gain = BASE_SCORE * mult
            if self.super_mode:
                gain *= SUPER_SCORE_MULT
            self.score += gain

            if self.combo > self.max_combo:
                self.max_combo = self.combo

            if self.combo >= COMBO_THRESHOLD and not self.super_mode:
                self._activate_super()

            sx, sy = self._grid_to_xy(g.col, g.row)
            self._spawn_collect_particles(float(sx), float(sy), g.color, 8)
            self.floating_texts.append(
                FloatingText(float(sx), float(sy), f"+{gain}", 25, COLORS[g.color])
            )
        else:
            self.combo = 0
            self.heat += HEAT_MISMATCH
            if self.heat > MAX_HEAT:
                self.heat = MAX_HEAT
            self.score += MISMATCH_SCORE
            self.shake_frames = 6

            sx, sy = self._grid_to_xy(g.col, g.row)
            self.floating_texts.append(
                FloatingText(
                    float(sx), float(sy), f"JAM! +{int(HEAT_MISMATCH)}", 25, RED
                )
            )
            for _ in range(4):
                self.particles.append(
                    Particle(
                        x=float(sx),
                        y=float(sy),
                        vx=self._rng.uniform(-1.5, 1.5),
                        vy=self._rng.uniform(-2.0, -0.5),
                        life=self._rng.randint(8, 15),
                        color=GRAY,
                    )
                )

        self.last_color = g.color if is_match else -1

        self.grid[g.col][g.row] = None
        self.col_heights[g.col] -= 1
        self._shift_gumballs_down(g.col, g.row)

        self.gumballs = [gb for gb in self.gumballs if gb.alive]

    def _shift_gumballs_down(self, col: int, removed_row: int) -> None:
        for gb in self.gumballs:
            if gb.col == col and gb.row < removed_row:
                self.grid[gb.col][gb.row] = None
                gb.row += 1
                self.grid[gb.col][gb.row] = gb.color

    def _find_gumball(self, col: int, row: int) -> Gumball | None:
        for g in self.gumballs:
            if g.alive and g.col == col and g.row == row:
                return g
        return None

    def _compute_combo_multiplier(self, combo: int) -> int:
        if combo < 2:
            return 1
        if combo < 4:
            return 2
        if combo < 6:
            return 3
        return 5

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self.super_flash = 0

        for _ in range(20):
            self.particles.append(
                Particle(
                    x=float(GRID_X + COLS * CELL / 2),
                    y=float(GRID_Y + ROWS * CELL / 2),
                    vx=self._rng.uniform(-3.0, 3.0),
                    vy=self._rng.uniform(-4.0, -1.0),
                    life=self._rng.randint(20, 40),
                    color=self._rng.choice(COLORS),
                )
            )

        self.shake_frames = 8

        cx = GRID_X + COLS * CELL / 2
        cy = GRID_Y + ROWS * CELL / 2
        self.floating_texts.append(
            FloatingText(float(cx), float(cy) - 20, "SUPER DISPENSE!", 45, YELLOW)
        )

    def _update_super_mode(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
            self.super_flash += 1
            if self.super_timer == 0:
                self.super_mode = False
                self.super_flash = 0

    # --- Heat ---

    def _update_heat(self) -> None:
        if self.heat > 0:
            elapsed_frames = GAME_TIME - self.game_timer
            decay = max(HEAT_DECAY_MIN, HEAT_DECAY_BASE - elapsed_frames * 0.00001)
            self.heat -= max(decay, 0.01)
            if self.heat < 0:
                self.heat = 0.0

    # --- Particles ---

    def _spawn_collect_particles(
        self, x: float, y: float, color: int, count: int
    ) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-1.5, 1.5),
                    vy=self._rng.uniform(-2.5, -0.5),
                    life=self._rng.randint(10, 20),
                    color=color,
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # --- Floating Texts ---

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # --- Grid Conversions ---

    def _grid_to_xy(self, col: int, row: int) -> tuple[int, int]:
        x = GRID_X + col * CELL + CELL // 2
        y = GRID_Y + row * CELL + CELL // 2
        return x, y

    def _xy_to_grid(self, screen_x: int, screen_y: int) -> tuple[int, int] | None:
        col = (screen_x - GRID_X) // CELL
        row = (screen_y - GRID_Y) // CELL
        if 0 <= col < COLS and 0 <= row < ROWS:
            return col, row
        return None

    # --- Game Over ---

    def _check_game_over(self) -> bool:
        return self.game_timer <= 0 or self.heat >= MAX_HEAT

    # --- Draw ---

    def _draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        self._draw_grid_bg()
        self._draw_gumballs()
        self._draw_hud()
        self._draw_particles()
        self._draw_floating_texts()

        if self.super_mode:
            self._draw_super_overlay()

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over_overlay()

    def _draw_title(self) -> None:
        title = "GUMBALL SURGE"
        pyxel.text(SCREEN_W // 2 - len(title) * 4 // 2, 20, title, YELLOW)

        instructions = [
            "Click to collect gumballs!",
            "Same color = COMBO chain!",
            "COMBO 4+ = SUPER DISPENSE!",
            "Wrong color = HEAT (machine jams)",
            "HEAT >= 100 = Game Over",
            "60-second time limit",
        ]
        for i, line in enumerate(instructions):
            pyxel.text(SCREEN_W // 2 - len(line) * 4 // 2, 50 + i * 14, line, WHITE)

        rainbow_colors = COLORS
        bx = GRID_X + CELL
        by = 148
        for i, color in enumerate(rainbow_colors):
            gx = bx + i * (CELL + 4)
            gy = by
            pyxel.circ(gx + CELL // 2, gy + CELL // 2, 8, color)
            pyxel.circb(gx + CELL // 2, gy + CELL // 2, 8, WHITE)

        pyxel.text(SCREEN_W // 2 - 12, by + CELL + 10, "Collect!", WHITE)

        blink = (self.frame // 15) % 2 == 0
        if blink:
            prompt = "Click or press SPACE to start"
            pyxel.text(
                SCREEN_W // 2 - len(prompt) * 4 // 2, 220, prompt, YELLOW
            )

    def _draw_grid_bg(self) -> None:
        grid_w = COLS * CELL
        grid_h = ROWS * CELL
        pyxel.rect(GRID_X, GRID_Y, grid_w, grid_h, NAVY)

        for c in range(1, COLS):
            x = GRID_X + c * CELL
            pyxel.line(x, GRID_Y, x, GRID_Y + grid_h, GRAY)

        for r in range(1, ROWS):
            y = GRID_Y + r * CELL
            pyxel.line(GRID_X, y, GRID_X + grid_w, y, GRAY)

    def _draw_gumballs(self) -> None:
        for g in self.gumballs:
            if not g.alive:
                continue
            x, y = self._grid_to_xy(g.col, g.row)
            color = COLORS[g.color]

            if self.super_mode:
                color = self._super_rainbow_color()

            pyxel.circ(x, y, 8, color)
            pyxel.circb(x, y, 8, WHITE)

            if g.infected:
                pyxel.circb(x, y, 6, GRAY)

            if g.spread_count >= MAX_SPREADS:
                pyxel.pset(x - 5, y - 5, ORANGE)
                pyxel.pset(x + 5, y - 5, ORANGE)

    def _draw_hud(self) -> None:
        hud_x = GRID_X + COLS * CELL + 10
        hud_y = GRID_Y

        timer_sec = max(0, self.game_timer // FPS)
        timer_str = f"TIME:{timer_sec}s"
        timer_color = RED if timer_sec <= 10 else WHITE
        pyxel.text(hud_x, hud_y, timer_str, timer_color)

        score_str = f"SCORE:{self.score}"
        pyxel.text(hud_x, hud_y + 14, score_str, WHITE)

        combo_str = f"COMBO:{self.combo}"
        combo_color = (
            YELLOW if self.combo >= COMBO_THRESHOLD
            else GREEN if self.combo >= 3
            else WHITE
        )
        pyxel.text(hud_x, hud_y + 28, combo_str, combo_color)

        best_str = f"BEST:{self.max_combo}"
        pyxel.text(hud_x, hud_y + 42, best_str, GREEN)

        bar_w = 20
        bar_h = ROWS * CELL
        bar_x = hud_x + 50
        bar_y = GRID_Y
        pyxel.rect(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2, GRAY)
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, BLACK)

        heat_h = int(bar_h * (self.heat / MAX_HEAT))
        heat_fill_y = bar_y + bar_h - heat_h
        heat_color = GREEN
        if self.heat > 60:
            heat_color = ORANGE
        if self.heat > 80:
            heat_color = RED
        if heat_h > 0:
            pyxel.rect(bar_x, heat_fill_y, bar_w, heat_h, heat_color)

        heat_lbl = "HEAT"
        pyxel.text(bar_x + 2, bar_y - 8, heat_lbl, heat_color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 30.0
            if alpha > 0.1:
                s = max(1, int(p.size * alpha))
                pyxel.rect(int(p.x), int(p.y), s, s, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 30.0
            if alpha < 0.1:
                continue
            pyxel.text(
                int(ft.x) - len(ft.text) * 4 // 2,
                int(ft.y),
                ft.text,
                ft.color,
            )

    def _draw_super_overlay(self) -> None:
        idx = (self.super_flash // 8) % len(COLORS)
        border_color = COLORS[idx]
        pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, border_color)
        pyxel.rectb(1, 1, SCREEN_W - 2, SCREEN_H - 2, border_color)

        super_sec = self.super_timer / float(FPS)
        super_str = f"SUPER DISPENSE! {super_sec:.1f}s"
        pyxel.text(
            SCREEN_W // 2 - len(super_str) * 4 // 2, 2, super_str, YELLOW
        )

    def _super_rainbow_color(self) -> int:
        idx = (self.super_flash // 8) % len(COLORS)
        return COLORS[idx]

    def _draw_game_over_overlay(self) -> None:
        ox = SCREEN_W // 2 - 90
        oy = SCREEN_H // 2 - 55
        for row_offset in range(0, 110, 2):
            py = oy + row_offset
            for col_offset in range(0, 180, 2):
                px = ox + col_offset
                if (col_offset // 2 + row_offset // 2) % 2 == 0:
                    pyxel.pset(px, py, BLACK)

        pyxel.rectb(ox, oy, 180, 110, RED)
        go_text = "GAME OVER"
        pyxel.text(SCREEN_W // 2 - len(go_text) * 4 // 2, oy + 10, go_text, RED)

        score_str = f"Score: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_str) * 4 // 2, oy + 28, score_str, WHITE)

        hi_str = f"Best: {self.high_score}"
        pyxel.text(SCREEN_W // 2 - len(hi_str) * 4 // 2, oy + 42, hi_str, YELLOW)

        combo_str = f"Max Combo: {self.max_combo}"
        pyxel.text(
            SCREEN_W // 2 - len(combo_str) * 4 // 2, oy + 56, combo_str, GREEN
        )

        if self.heat >= MAX_HEAT:
            reason = "Overheated!"
            pyxel.text(
                SCREEN_W // 2 - len(reason) * 4 // 2, oy + 74, reason, RED
            )
        else:
            reason = "Time Up!"
            pyxel.text(
                SCREEN_W // 2 - len(reason) * 4 // 2, oy + 74, reason, WHITE
            )

        blink = (self.frame // 15) % 2 == 0
        if blink:
            prompt = "Press R to restart"
            pyxel.text(
                SCREEN_W // 2 - len(prompt) * 4 // 2, oy + 92, prompt, YELLOW
            )


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
