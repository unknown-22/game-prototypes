"""DIG CHAIN -- Archaeology excavation COMBO chain game.

一番面白い瞬間: 同じ色の地層を連続で掘り当ててCOMBOを4以上に伸ばし、
SUPER EXCAVATIONが発動して広範囲のセルが虹色に光り、
次々と化石ボーナスが出現してスコアが爆発する瞬間
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import pyxel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCREEN_W = 320
SCREEN_H = 240
FPS = 30
FONT_PATH = Path(__file__).with_name("k8x12.bdf")
FONT_W = 8
FONT_H = 12

COLS = 8
ROWS = 6
CELL = 28
GRID_X = (SCREEN_W - COLS * CELL) // 2
GRID_Y = (SCREEN_H - ROWS * CELL) // 2 - 14

TIMER_MAX = 1800
SUPER_DURATION = 300
COMBO_THRESHOLD = 4
NUM_COLORS = 4

DIRT_COLORS = (8, 11, 12, 10)  # RED, LIME, CYAN, YELLOW

HEAT_MISMATCH = 15.0
HEAT_DECAY = 0.02
HEAT_MAX = 100.0

FOSSIL_BONUS = 50
FOSSIL_CHANCE = 0.15
FOSSIL_SPAWN_INTERVAL = 120

PARTICLE_COUNT_DIG = 8
PARTICLE_COUNT_SUPER = 20
PARTICLE_COUNT_FOSSIL = 4
FLOAT_TEXT_LIFE = 45

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

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------
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
    x: float
    y: float
    text: str
    life: int
    color: int
    vy: float = -1.0


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    """Pure game logic -- no pyxel calls for testable methods."""

    def __init__(self) -> None:
        self.rng = random.Random()
        self.best_score = 0
        self._init_state()

    def _init_state(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.last_color: int | None = None
        self.timer = TIMER_MAX
        self.super_timer = 0
        self.super_mode = False
        self.cells: list[list[dict]] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._shake_frames = 0
        self._fossil_spawn_counter = 0
        self._frame = 0

    def reset(self) -> None:
        best = self.best_score
        self.rng = random.Random()
        self._init_state()
        self.best_score = best
        self.phase = Phase.PLAYING
        self._init_grid()

    # ── Grid ───────────────────────────────────────────────────────────────
    def _init_grid(self) -> None:
        self.cells = []
        for col in range(COLS):
            column: list[dict] = []
            for row in range(ROWS):
                color = self.rng.randint(0, NUM_COLORS - 1)
                fossil = self.rng.random() < FOSSIL_CHANCE
                column.append({
                    "color": color,
                    "excavated": False,
                    "fossil_bonus": fossil,
                })
            self.cells.append(column)

    def _get_cell(self, col: int, row: int) -> dict | None:
        if 0 <= col < COLS and 0 <= row < ROWS:
            return self.cells[col][row]
        return None

    # ── Click Handling ─────────────────────────────────────────────────────
    def _handle_click(self, col: int, row: int) -> tuple[bool, int]:
        """Returns (was_valid, score_gained)."""
        if not (0 <= col < COLS and 0 <= row < ROWS):
            return (False, 0)

        cell = self.cells[col][row]
        if cell["excavated"]:
            return (False, 0)

        cell_color = cell["color"]
        cell["excavated"] = True

        match = self.super_mode or self.last_color is None or self.last_color == cell_color

        gx, gy = self._cell_center(col, row)

        if match:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            base = 10 * self.combo
            score_gain = base * 3 if self.super_mode else base

            if cell["fossil_bonus"]:
                score_gain += FOSSIL_BONUS
                cell["fossil_bonus"] = False
                self._add_floating_text(f"FOSSIL! +{FOSSIL_BONUS}", gx, gy - 10, YELLOW)
                self._spawn_particles(gx, gy, YELLOW, PARTICLE_COUNT_FOSSIL, 0.1)

            self.score += score_gain
            self.last_color = cell_color

            if self.super_mode:
                self._spawn_particles(gx, gy, WHITE, PARTICLE_COUNT_SUPER, 0.05)
                self._add_floating_text(f"+{score_gain}", gx, gy - 6, WHITE)
            else:
                self._spawn_particles(gx, gy, DIRT_COLORS[cell_color], PARTICLE_COUNT_DIG, 0.1)
                self._add_floating_text(f"+{score_gain}", gx, gy - 6, DIRT_COLORS[cell_color])

            if self.combo > 1:
                combo_color = RED if self.combo >= COMBO_THRESHOLD else YELLOW
                self._add_floating_text(f"COMBO x{self.combo}!", SCREEN_W // 2, 24, combo_color)

            if self.combo >= COMBO_THRESHOLD and not self.super_mode:
                self._activate_super()

            return (True, score_gain)
        else:
            self.combo = 0
            self.last_color = None
            self.heat += HEAT_MISMATCH
            self._shake_frames = 10
            self._spawn_particles(gx, gy, GRAY, 4, 0.2)
            self._add_floating_text("WRONG COLOR!", gx, gy - 6, RED)
            return (True, 0)

    # ── SUPER EXCAVATION ──────────────────────────────────────────────────
    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self._add_floating_text("SUPER EXCAVATION!", SCREEN_W // 2, 12, YELLOW)

    def _end_super(self) -> None:
        self.super_mode = False
        self.super_timer = 0

    # ── Heat ──────────────────────────────────────────────────────────────
    def _update_heat(self, mismatch: bool) -> None:
        if mismatch:
            self.heat = min(self.heat + HEAT_MISMATCH, HEAT_MAX)
        else:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    # ── Timer ─────────────────────────────────────────────────────────────
    def _update_timer(self) -> None:
        self.timer = max(0, self.timer - 1)

    # ── Game Over ─────────────────────────────────────────────────────────
    def _check_game_over(self) -> bool:
        return self.timer <= 0 or self.heat >= HEAT_MAX

    def _end_game(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score

    # ── Fossil Spawn ──────────────────────────────────────────────────────
    def _spawn_fossil(self) -> None:
        undug = [
            (col, row)
            for col in range(COLS)
            for row in range(ROWS)
            if not self.cells[col][row]["excavated"] and not self.cells[col][row]["fossil_bonus"]
        ]
        if undug:
            col, row = self.rng.choice(undug)
            self.cells[col][row]["fossil_bonus"] = True

    # ── Cell Center ───────────────────────────────────────────────────────
    def _cell_center(self, col: int, row: int) -> tuple[float, float]:
        return (
            GRID_X + col * CELL + CELL // 2,
            GRID_Y + row * CELL + CELL // 2,
        )

    # ── Particles ─────────────────────────────────────────────────────────
    def _spawn_particles(self, x: float, y: float, color: int, count: int, gravity: float) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=x + self.rng.uniform(-4, 4),
                    y=y + self.rng.uniform(-4, 4),
                    vx=self.rng.uniform(-2, 2),
                    vy=self.rng.uniform(-4, -2),
                    life=self.rng.randint(15, 25),
                    color=color,
                )
            )

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

    # ── Floating Text ─────────────────────────────────────────────────────
    def _add_floating_text(self, text: str, x: float, y: float, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=FLOAT_TEXT_LIFE, color=color))

    def _update_floating_texts(self) -> None:
        alive: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life > 0:
                alive.append(ft)
        self.floating_texts = alive

    # ── Grid Query ──────────────────────────────────────────────────────
    def _has_nearby_fossil(self, col: int, row: int, distance: int = 2) -> bool:
        for dc in range(-distance, distance + 1):
            for dr in range(-distance, distance + 1):
                if dc == 0 and dr == 0:
                    continue
                nc, nr = col + dc, row + dr
                cell = self._get_cell(nc, nr)
                if cell and cell["fossil_bonus"] and not cell["excavated"]:
                    return True
        return False

    # ── Update ────────────────────────────────────────────────────────────
    def update(self) -> None:
        if self.phase != Phase.PLAYING:
            return

        self._frame += 1
        self._update_timer()

        if self.timer <= 0:
            self._end_game()
            return

        if self.heat >= HEAT_MAX:
            self._end_game()
            return

        self.heat = max(0.0, self.heat - HEAT_DECAY)

        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self._end_super()

        if self._shake_frames > 0:
            self._shake_frames -= 1

        self._fossil_spawn_counter += 1
        if self._fossil_spawn_counter >= FOSSIL_SPAWN_INTERVAL:
            self._fossil_spawn_counter = 0
            self._spawn_fossil()

        self._update_particles()
        self._update_floating_texts()

    # ── Draw ──────────────────────────────────────────────────────────────
    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = "DIG CHAIN"
        tw = len(title) * FONT_W
        pyxel.text(SCREEN_W // 2 - tw // 2, 30, title, WHITE)

        subtitle = "ARCHAEOLOGY EXCAVATION"
        sw = len(subtitle) * FONT_W
        pyxel.text(SCREEN_W // 2 - sw // 2, 46, subtitle, YELLOW)

        lines = [
            "Click cells to excavate!",
            "",
            "Same color = COMBO!",
            "COMBO x4 = SUPER EXCAVATION!",
            "(3x score, any color match)",
            "",
            "Wrong color = HEAT +15",
            "HEAT 100 = GAME OVER",
            "",
            "TIMER: 60 seconds",
            "",
            "CLICK or ENTER to start",
        ]
        for i, line in enumerate(lines):
            y = 72 + i * (FONT_H + 2)
            lw = len(line) * FONT_W
            pyxel.text(SCREEN_W // 2 - lw // 2, y, line, GRAY)

        if self.best_score > 0:
            best_text = f"BEST SCORE: {self.best_score}"
            bw = len(best_text) * FONT_W
            pyxel.text(SCREEN_W // 2 - bw // 2, SCREEN_H - FONT_H - 4, best_text, CYAN)

    def _draw_game_over(self) -> None:
        go_text = "GAME OVER"
        tw = len(go_text) * FONT_W
        pyxel.text(SCREEN_W // 2 - tw // 2, 40, go_text, RED)

        score_text = f"SCORE: {self.score}"
        sw = len(score_text) * FONT_W
        pyxel.text(SCREEN_W // 2 - sw // 2, 66, score_text, WHITE)

        if self.score >= self.best_score and self.best_score > 0:
            new_best = "NEW BEST!"
            nbw = len(new_best) * FONT_W
            pyxel.text(SCREEN_W // 2 - nbw // 2, 82, new_best, YELLOW)

        best_text = f"BEST: {self.best_score}"
        bw = len(best_text) * FONT_W
        pyxel.text(SCREEN_W // 2 - bw // 2, 98, best_text, GRAY)

        combo_text = f"MAX COMBO: x{self.max_combo}"
        cw = len(combo_text) * FONT_W
        pyxel.text(SCREEN_W // 2 - cw // 2, 116, combo_text, YELLOW)

        if self.heat >= HEAT_MAX:
            reason = "CAUSE: OVERHEAT"
        else:
            reason = "CAUSE: TIME'S UP"
        rw = len(reason) * FONT_W
        pyxel.text(SCREEN_W // 2 - rw // 2, 144, reason, RED)

        if (pyxel.frame_count // FPS) % 2 == 0:
            retry = "PRESS ENTER OR R TO RETRY"
            rtw = len(retry) * FONT_W
            pyxel.text(SCREEN_W // 2 - rtw // 2, 180, retry, YELLOW)

    def _draw_playing(self) -> None:
        self._draw_grid()
        self._draw_cells()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_grid(self) -> None:
        border_color = WHITE
        if self.super_mode:
            border_color = DIRT_COLORS[(pyxel.frame_count // 8) % NUM_COLORS]

        pyxel.rectb(GRID_X - 1, GRID_Y - 1, COLS * CELL + 2, ROWS * CELL + 2, border_color)

    def _draw_cells(self) -> None:
        for col in range(COLS):
            for row in range(ROWS):
                cell = self.cells[col][row]
                x = GRID_X + col * CELL
                y = GRID_Y + row * CELL

                if cell["excavated"]:
                    color = DIRT_COLORS[cell["color"]]
                    pyxel.rect(x + 1, y + 1, CELL - 2, CELL - 2, color)
                    if cell["fossil_bonus"]:
                        cx = x + CELL // 2
                        cy = y + CELL // 2
                        pyxel.circ(cx, cy, 4, YELLOW)
                else:
                    pyxel.rect(x + 1, y + 1, CELL - 2, CELL - 2, DARK_BLUE)
                    light = PINK if self._has_nearby_fossil(col, row) and self.super_mode else DARK_BLUE
                    if light != DARK_BLUE:
                        pyxel.rect(x + 3, y + 3, CELL - 6, CELL - 6, light)

                pyxel.rectb(x, y, CELL, CELL, GRAY)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 25.0
            color = p.color if alpha > 0.3 else GRAY
            pyxel.rect(int(p.x), int(p.y), p.size, p.size, color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / FLOAT_TEXT_LIFE
            if alpha < 0.15:
                continue
            color = ft.color if alpha > 0.3 else GRAY
            tw = len(ft.text) * FONT_W
            pyxel.text(int(ft.x) - tw // 2, int(ft.y), ft.text, color)

    def _draw_hud(self) -> None:
        score_text = f"SCORE: {self.score}"
        pyxel.text(4, 4, score_text, WHITE)

        if self.combo > 1:
            combo_text = f"COMBO x{self.combo}"
            combo_color = RED if self.combo >= COMBO_THRESHOLD else YELLOW
            pyxel.text(SCREEN_W // 2 - len(combo_text) * FONT_W // 2, 4, combo_text, combo_color)

        if self.super_mode:
            super_text = f"SUPER! {self.super_timer // FPS + 1}s"
            super_color = DIRT_COLORS[(pyxel.frame_count // 8) % NUM_COLORS]
            stw = len(super_text) * FONT_W
            pyxel.text(SCREEN_W // 2 - stw // 2, FONT_H + 6, super_text, super_color)

        self._draw_heat_bar()
        self._draw_timer_bar()

    def _draw_heat_bar(self) -> None:
        bar_x = SCREEN_W - 20
        bar_y = GRID_Y
        bar_w = 10
        bar_h = ROWS * CELL

        pyxel.rect(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2, GRAY)

        fill_h = int(bar_h * (self.heat / HEAT_MAX))
        fill_y = bar_y + bar_h - fill_h
        if self.heat < 33:
            heat_c = GREEN
        elif self.heat < 66:
            heat_c = YELLOW
        else:
            heat_c = RED
        if fill_h > 0:
            pyxel.rect(bar_x, fill_y, bar_w, fill_h, heat_c)

        label = "HEAT"
        pyxel.text(bar_x - len(label) * FONT_W - 4, bar_y - 2, label, GRAY)

    def _draw_timer_bar(self) -> None:
        bar_w = GRID_X - 8
        bar_h = 6
        bar_x = 4
        bar_y = GRID_Y - FONT_H - 4

        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        fill_w = int(bar_w * (self.timer / TIMER_MAX))
        if fill_w > 0:
            pyxel.rect(bar_x, bar_y, fill_w, bar_h, CYAN)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)

        time_s = self.timer // FPS
        time_text = f"TIME: {time_s}s"
        pyxel.text(bar_x + bar_w + 4, bar_y - 2, time_text, WHITE)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
class App:
    """Pyxel entry point -- wires input to Game."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="DIG CHAIN", fps=FPS)
        if FONT_PATH.exists():
            pyxel.load(str(FONT_PATH))
        self.game = Game()
        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        g = self.game

        if g.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                g.reset()
        elif g.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_R):
                g.reset()
        elif g.phase == Phase.PLAYING:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                mx = pyxel.mouse_x
                my = pyxel.mouse_y
                col = (mx - GRID_X) // CELL
                row = (my - GRID_Y) // CELL
                if 0 <= col < COLS and 0 <= row < ROWS:
                    g._handle_click(col, row)

            g.update()

    def draw(self) -> None:
        g = self.game

        if g._shake_frames > 0 and g.phase == Phase.PLAYING:
            sx = g.rng.randint(-2, 2)
            sy = g.rng.randint(-2, 2)
        else:
            sx = 0
            sy = 0

        if sx != 0 or sy != 0:
            try:
                pyxel.camera(sx, sy)
                g.draw()
                pyxel.camera(0, 0)
            except Exception:
                g.draw()
        else:
            g.draw()


def main() -> None:
    App()


if __name__ == "__main__":
    main()
