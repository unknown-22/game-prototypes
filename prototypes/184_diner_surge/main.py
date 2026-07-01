from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import pyxel


SCREEN_W = 320
SCREEN_H = 240
TABLE_COLS = 4
TABLE_ROWS = 3
TABLE_W = 64
TABLE_H = 56
GRID_X = 28
GRID_Y = 32
TABLE_GAP = 8
PATIENCE_MAX = 300
HEAT_MAX = 100.0
HEAT_MISMATCH = 15.0
HEAT_TIMEOUT = 10.0
HEAT_DECAY = 0.03
COMBO_FOR_SUPER = 4
SUPER_DURATION = 90
GAME_DURATION = 1800
MAX_ORDERS = 8
SPAWN_INTERVAL_MIN = 60
SPAWN_INTERVAL_MAX = 120
COLORS = [8, 3, 5, 10]
COLOR_RED = 8
COLOR_GREEN = 3
COLOR_DARK_BLUE = 5
COLOR_YELLOW = 10
COLOR_WHITE = 7
COLOR_GRAY = 13
COLOR_BLACK = 0
COLOR_ORANGE = 9
COLOR_CYAN = 12
COLOR_PINK = 14


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Order:
    col: int
    row: int
    color: int
    timer: int = PATIENCE_MAX


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
    vy: float = -1.5


class Game:
    def __init__(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.orders: list[Order] = []
        self.last_color: int = -1
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.heat: float = 0.0
        self.super_timer: int = 0
        self.game_timer: int = GAME_DURATION
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.rng: random.Random = random.Random()
        self.regular_positions: list[tuple[int, int]] = []
        self.spawn_timer: int = 0
        self.served_this_frame: bool = False
        self.super_rainbow_tick: int = 0
        self.font: pyxel.Font | None = None
        self._init_font()

    def _init_font(self) -> None:
        bdf_path = Path(__file__).with_name("k8x12.bdf")
        if not bdf_path.exists():
            return
        self.font = pyxel.Font(str(bdf_path))

    def _text(self, x: int, y: int, s: str, col: int) -> None:
        if self.font:
            pyxel.text(x, y, s, col, self.font)
        else:
            pyxel.text(x, y, s, col)

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.orders.clear()
        self.last_color = -1
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.heat = 0.0
        self.super_timer = 0
        self.game_timer = GAME_DURATION
        self.particles.clear()
        self.floating_texts.clear()
        self.rng = random.Random()
        self.regular_positions.clear()
        self.spawn_timer = 0
        self.served_this_frame = False
        self.super_rainbow_tick = 0
        for _ in range(4):
            self._spawn_order()

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
        elif self.phase == Phase.PLAYING:
            self.served_this_frame = False
            self.tick()
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and not self.served_this_frame:
                mx = pyxel.mouse_x
                my = pyxel.mouse_y
                clicked = self._get_clicked_table(mx, my)
                if clicked is not None:
                    col, row = clicked
                    self.served_this_frame = True
                    self._handle_serve(col, row)
            if self.game_timer <= 0 or self.heat >= HEAT_MAX:
                self.phase = Phase.GAME_OVER
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()

    def draw(self) -> None:
        pyxel.cls(COLOR_BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_gameover()

    # ---------- game logic (pure, testable) ----------

    def _spawn_order(self) -> None:
        if len(self.orders) >= MAX_ORDERS:
            return

        occupied = {(o.col, o.row) for o in self.orders}
        available = [
            (c, r)
            for c in range(TABLE_COLS)
            for r in range(TABLE_ROWS)
            if (c, r) not in occupied
        ]
        if not available:
            return

        if self.regular_positions and self.rng.random() < 0.4:
            regs = [p for p in self.regular_positions if p not in occupied]
            if regs:
                col, row = self.rng.choice(regs)
                color = self.last_color if self.last_color in COLORS else self.rng.choice(COLORS)
                self.orders.append(Order(col, row, color))
                return

        col, row = self.rng.choice(available)
        color = self.rng.choice(COLORS)
        self.orders.append(Order(col, row, color))

    def _get_table_center(self, col: int, row: int) -> tuple[int, int]:
        x = GRID_X + col * (TABLE_W + TABLE_GAP) + TABLE_W // 2
        y = GRID_Y + row * (TABLE_H + TABLE_GAP) + TABLE_H // 2
        return x, y

    def _get_clicked_table(self, mx: int, my: int) -> tuple[int, int] | None:
        for col in range(TABLE_COLS):
            for row in range(TABLE_ROWS):
                x = GRID_X + col * (TABLE_W + TABLE_GAP)
                y = GRID_Y + row * (TABLE_H + TABLE_GAP)
                if x <= mx < x + TABLE_W and y <= my < y + TABLE_H:
                    return col, row
        return None

    def _handle_serve(self, col: int, row: int) -> int:
        target = next((o for o in self.orders if o.col == col and o.row == row), None)
        if target is None:
            return 0
        order_color = target.color
        self.orders.remove(target)
        cx, cy = self._get_table_center(col, row)

        is_super_active = self.super_timer > 0

        if is_super_active:
            points = 30
            if order_color == self.last_color:
                self.combo += 1
            else:
                self.last_color = order_color
                self.combo = 1
        else:
            if self.last_color == order_color:
                self.combo += 1
                points = (10 + self.combo * 5)
            else:
                self.combo = 1
                self.last_color = order_color
                self.heat = min(HEAT_MAX, self.heat + HEAT_MISMATCH)
                self.regular_positions.clear()
                points = 10

        if self.combo > self.max_combo:
            self.max_combo = self.combo

        self.score += points
        self.regular_positions.append((col, row))

        self._spawn_particles(cx, cy, order_color, 12)
        self._add_floating_text(cx, cy - 10, f"+{points}", order_color)

        if self.combo >= 3:
            self._add_floating_text(cx, cy + 10, f"COMBO x{self.combo}!", COLOR_YELLOW)

        if self.combo >= COMBO_FOR_SUPER and not is_super_active:
            self._activate_super()

        return points

    def _can_serve(self, col: int, row: int) -> bool:
        return any(o.col == col and o.row == row for o in self.orders)

    def _update_orders(self) -> None:
        survived: list[Order] = []
        for o in self.orders:
            o.timer -= 1
            if o.timer <= 0:
                cx, cy = self._get_table_center(o.col, o.row)
                self.heat = min(HEAT_MAX, self.heat + HEAT_TIMEOUT)
                self._add_floating_text(cx, cy, "MISS!", COLOR_RED)
                self._spawn_particles(cx, cy, COLOR_RED, 6)
            else:
                survived.append(o)
        self.orders = survived

    def _update_particles(self) -> None:
        survived: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.15
            p.life -= 1
            if p.life > 0:
                survived.append(p)
        self.particles = survived

    def _update_floating_texts(self) -> None:
        survived: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life > 0:
                survived.append(ft)
        self.floating_texts = survived

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        for o in self.orders:
            cx, cy = self._get_table_center(o.col, o.row)
            self._spawn_particles(cx, cy, self.rng.choice(COLORS), 8)
        self._add_floating_text(SCREEN_W // 2, SCREEN_H // 2, "SUPER!", COLOR_YELLOW)

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            vx = self.rng.uniform(-2.5, 2.5)
            vy = self.rng.uniform(-3.5, -0.5)
            life = self.rng.randint(12, 24)
            self.particles.append(Particle(x, y, vx, vy, life, color))

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x, y, text, 30, color))

    def tick(self) -> None:
        self.heat = max(0.0, self.heat - HEAT_DECAY)
        self._update_orders()
        self.spawn_timer += 1
        if self.spawn_timer >= self.rng.randint(SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX):
            self.spawn_timer = 0
            self._spawn_order()
        if self.super_timer > 0:
            self.super_timer -= 1
            self.super_rainbow_tick += 1
        self.game_timer -= 1
        self._update_particles()
        self._update_floating_texts()

    # ---------- drawing ----------

    def _draw_title(self) -> None:
        title_x = SCREEN_W // 2 - 60
        self._text(title_x, 60, "DINER SURGE", COLOR_YELLOW)

        lines = [
            "Grid serving game!",
            "",
            "Click matching-color tables",
            "to build COMBO chain.",
            "COMBO x4 = SUPER SERVE!",
            "(rainbow auto-match, 3x score)",
            "",
            "Click to Start",
        ]
        for i, line in enumerate(lines):
            if line:
                w = len(line) * 4
                self._text(SCREEN_W // 2 - w, 100 + i * 16, line, COLOR_WHITE)
            else:
                self._text(SCREEN_W // 2, 100 + i * 16, line, COLOR_WHITE)

        info_lines = [
            "4 colors: RED, GREEN, BLUE, YELLOW",
            "Mismatch = HEAT + combo reset",
            "Timeout = HEAT (watch patience bar!)",
            "HEAT full or 60s = Game Over",
        ]
        for i, line in enumerate(info_lines):
            w = len(line) * 4
            self._text(SCREEN_W // 2 - w, 200 + i * 10, line, COLOR_GRAY)

    def _draw_playing(self) -> None:
        self._draw_ui_bar()
        self._draw_grid()
        self._draw_orders()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_player_color()

    def _draw_ui_bar(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, 26, COLOR_BLACK)
        self._text(4, 4, f"SCORE:{self.score:06d}", COLOR_WHITE)
        self._text(136, 4, f"COMBO:{self.combo}", COLOR_WHITE)

        bar_x = 216
        bar_w = 50
        bar_y = 4
        bar_h = 10
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, COLOR_GRAY)
        heat_fill = int((self.heat / HEAT_MAX) * bar_w)
        if heat_fill > 0:
            pyxel.rect(bar_x, bar_y, heat_fill, bar_h, COLOR_ORANGE)

        secs = self.game_timer // 30
        timer_text = f"{secs}s"
        self._text(272, 4, timer_text, COLOR_WHITE)

        if self.super_timer > 0:
            rainbow_color = COLORS[self.super_rainbow_tick // 5 % len(COLORS)]
            self._text(60, 16, "SUPER!", rainbow_color)

    def _draw_grid(self) -> None:
        for col in range(TABLE_COLS):
            for row in range(TABLE_ROWS):
                x = GRID_X + col * (TABLE_W + TABLE_GAP)
                y = GRID_Y + row * (TABLE_H + TABLE_GAP)
                pyxel.rect(x, y, TABLE_W, TABLE_H, COLOR_GRAY)
                pyxel.rectb(x, y, TABLE_W, TABLE_H, COLOR_BLACK)

    def _draw_orders(self) -> None:
        for o in self.orders:
            x = GRID_X + o.col * (TABLE_W + TABLE_GAP)
            y = GRID_Y + o.row * (TABLE_H + TABLE_GAP)
            cx = x + TABLE_W // 2
            cy = y + TABLE_H // 2 - 4

            border_color = COLOR_WHITE
            if self.super_timer > 0:
                border_color = COLORS[self.super_rainbow_tick // 5 % len(COLORS)]
            pyxel.rectb(x, y, TABLE_W, TABLE_H, border_color)

            r = 12
            pyxel.circ(cx, cy, r, o.color)
            pyxel.circb(cx, cy, r, COLOR_BLACK)

            bar_y = y + TABLE_H - 10
            bar_w = TABLE_W - 8
            pyxel.rect(x + 4, bar_y, bar_w, 6, COLOR_GRAY)
            pct = o.timer / PATIENCE_MAX
            fill_w = int(bar_w * pct)
            if pct > 0.5:
                bar_col = COLOR_GREEN
            elif pct > 0.25:
                bar_col = COLOR_YELLOW
            else:
                bar_col = COLOR_RED
            if fill_w > 0:
                pyxel.rect(x + 4, bar_y, fill_w, 6, bar_col)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 20
            if alpha > 1:
                alpha = 1
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = min(ft.life / 30, 1.0)
            col = ft.color if alpha > 0.4 else COLOR_GRAY
            w = len(ft.text) * 4
            self._text(int(ft.x) - w, int(ft.y), ft.text, col)

    def _draw_player_color(self) -> None:
        cx = SCREEN_W // 2
        cy = SCREEN_H - 12
        if self.last_color in COLORS:
            current_color = self.last_color
        else:
            current_color = COLOR_WHITE
        pyxel.circ(cx, cy, 8, current_color)
        pyxel.circb(cx, cy, 8, COLOR_BLACK)
        self._text(cx + 14, cy - 4, "= YOUR COLOR", COLOR_WHITE)

    def _draw_gameover(self) -> None:
        self._text(SCREEN_W // 2 - 40, 50, "GAME OVER", COLOR_RED)
        self._text(SCREEN_W // 2 - 70, 80, f"SCORE: {self.score:06d}", COLOR_WHITE)
        self._text(SCREEN_W // 2 - 70, 100, f"MAX COMBO: {self.max_combo}", COLOR_YELLOW)

        if self.heat >= HEAT_MAX:
            self._text(SCREEN_W // 2 - 70, 120, "Failed by HEAT overload!", COLOR_ORANGE)
        else:
            self._text(SCREEN_W // 2 - 70, 120, "Time's up!", COLOR_CYAN)

        self._text(SCREEN_W // 2 - 60, 160, "Click to Restart", COLOR_WHITE)


def main() -> None:
    pyxel.init(SCREEN_W, SCREEN_H, title="Diner Surge", display_scale=2)
    game = Game()
    pyxel.mouse(True)
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
