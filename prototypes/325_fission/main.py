"""FISSION — Nuclear Reactor Press-Your-Luck.

Operate a nuclear reactor. CHARGE injects a random 1-6 energy burst into the
core accumulator; a hidden meltdown threshold T makes overcharging deadly. A
sensor gauge shows only an approximate "danger band" around T, narrowing with
each charge. BANK near the true T pays a 2x CLOSE CALL! bonus.
"""
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Config constants ──
WIDTH = 320
HEIGHT = 240
FPS = 60

MIN_T = 12
MAX_T_BASE = 22
MAX_ENERGY = 36
CHARGE_MIN = 1
CHARGE_MAX = 6
SENSOR_START = 6
SENSOR_MIN = 2
EDGE_MARGIN = 2
EDGE_MULT = 2
LIVES = 3
TIMER_MAX = 3600

CORE_X = 160
CORE_Y = 80
CORE_R = 28
GAUGE_X = 60
GAUGE_Y = 150
GAUGE_W = 200
GAUGE_H = 24

CHARGE_BTN = (20, 200, 110, 30)
BANK_BTN = (190, 200, 110, 30)

# Colors (raw ints)
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


class Phase(Enum):
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


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


class Game:
    def __init__(self) -> None:
        pyxel.init(WIDTH, HEIGHT, title="FISSION", fps=FPS)
        pyxel.mouse(True)
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── State management ──

    def reset(self) -> None:
        self.rng: random.Random = getattr(self, "rng", random.Random())
        self.best_score: int = getattr(self, "best_score", 0)
        self._sfx_enabled: bool = getattr(self, "_sfx_enabled", True)
        self.phase = Phase.TITLE
        self.frame = 0
        self.energy = 0
        self.threshold = 0
        self.sensor_window = SENSOR_START
        self.score = 0
        self.lives = LIVES
        self.last_roll = 0
        self.last_bank = 0
        self.close_calls = 0
        self.total_banks = 0
        self.shake = 0
        self.flash = 0
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self._game_over_reason = ""
        self._spawn_reactor()

    def _spawn_reactor(self) -> None:
        self.threshold = self.rng.randint(MIN_T, self._max_t())
        self.energy = 0
        self.sensor_window = SENSOR_START
        self.last_roll = 0

    # ── Pure / logic helpers (testable, no pyxel input) ──

    def _max_t(self) -> int:
        return MAX_T_BASE + self.frame // 600

    @staticmethod
    def _bank_value(energy: int, threshold: int) -> int:
        return energy * (EDGE_MULT if energy >= threshold - EDGE_MARGIN else 1)

    def sensor_band(self) -> tuple[int, int]:
        return (self.threshold - self.sensor_window, self.threshold + self.sensor_window)

    def in_danger(self) -> bool:
        return self.energy >= self.threshold - self.sensor_window

    # ── Core actions (testable) ──

    def charge(self) -> str:
        roll = self.rng.randint(CHARGE_MIN, CHARGE_MAX)
        self.energy += roll
        self.last_roll = roll
        self.sensor_window = max(SENSOR_MIN, self.sensor_window - 1)
        if self.energy > self.threshold:
            self._meltdown()
            return "meltdown"
        self._burst(CORE_X, CORE_Y, YELLOW, 4, 1.5, 8, 16)
        self._spawn_float(CORE_X + 18, CORE_Y - 28, "+%d" % roll, YELLOW)
        return "charged"

    def bank(self) -> str:
        if self.energy <= 0:
            return "empty"
        bv = self._bank_value(self.energy, self.threshold)
        edge = self.energy >= self.threshold - EDGE_MARGIN
        self.score += bv
        self.last_bank = bv
        if edge:
            self.close_calls += 1
        self.total_banks += 1
        if edge:
            self._spawn_float(CORE_X, CORE_Y - 40, "CLOSE CALL! x%d" % EDGE_MULT, PINK)
            self._burst(CORE_X, CORE_Y, PINK, 20, 3.0, 12, 24)
        else:
            self._spawn_float(CORE_X, CORE_Y - 40, "+%d" % bv, LIME)
            self._burst(CORE_X, CORE_Y, LIME, 12, 3.0, 12, 24)
        self._spawn_reactor()
        return "banked"

    def _meltdown(self) -> None:
        self.lives -= 1
        self.energy = 0
        self.shake = 12
        self.flash = 20
        self._spawn_float(CORE_X, CORE_Y - 44, "MELTDOWN!", RED)
        for i in range(40):
            color = ORANGE if i % 2 == 0 else RED
            self._spawn_particle(CORE_X, CORE_Y, color, 4.0, 20, 40)
        if self.lives <= 0:
            self.phase = Phase.GAME_OVER
            self._game_over_reason = "MELTDOWN"
            self.best_score = max(self.best_score, self.score)
        else:
            self._spawn_reactor()

    def _game_over(self, reason: str) -> None:
        self._game_over_reason = reason
        self.best_score = max(self.best_score, self.score)
        self.phase = Phase.GAME_OVER

    # ── Effects (testable, list-only) ──

    def _spawn_particle(
        self, x: float, y: float, color: int, speed: float, life_min: int, life_max: int
    ) -> None:
        self.particles.append(
            Particle(
                x=x,
                y=y,
                vx=self.rng.uniform(-speed, speed),
                vy=self.rng.uniform(-speed, speed),
                life=self.rng.randint(life_min, life_max),
                color=color,
            )
        )

    def _burst(
        self, x: float, y: float, color: int, count: int, speed: float, life_min: int, life_max: int
    ) -> None:
        for _ in range(count):
            self._spawn_particle(x, y, color, speed, life_min, life_max)

    def _spawn_float(self, x: float, y: float, text: str, color: int) -> None:
        self.floats.append(FloatingText(x=x, y=y, text=text, life=45, color=color))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floats(self) -> None:
        for f in self.floats:
            f.y -= 1.0
            f.life -= 1
        self.floats = [f for f in self.floats if f.life > 0]

    # ── Input helpers (testable) ──

    def _button_charge_contains(self, mx: int, my: int) -> bool:
        x, y, w, h = CHARGE_BTN
        return x <= mx <= x + w and y <= my <= y + h

    def _button_bank_contains(self, mx: int, my: int) -> bool:
        x, y, w, h = BANK_BTN
        return x <= mx <= x + w and y <= my <= y + h

    # ── Update / phase machine ──

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if (
                pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            ):
                self.reset()
                self.phase = Phase.PLAYING
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            if (
                pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.KEY_R)
                or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            ):
                self.reset()
                self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self.frame += 1

        if pyxel.btnp(pyxel.KEY_SPACE):
            self.charge()
        if pyxel.btnp(pyxel.KEY_B):
            self.bank()

        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if self._button_charge_contains(mx, my):
                self.charge()
            elif self._button_bank_contains(mx, my):
                self.bank()

        self._update_particles()
        self._update_floats()

        if self.shake > 0:
            self.shake -= 1
        if self.flash > 0:
            self.flash -= 1

        if self.phase == Phase.PLAYING and self.frame >= TIMER_MAX:
            self._game_over("TIME UP")

    # ── Draw ──

    def draw(self) -> None:
        if self.shake > 0:
            ox = self.rng.randint(-2, 2)
            oy = self.rng.randint(-2, 2)
        else:
            ox = 0
            oy = 0

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing(ox, oy)
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.cls(NAVY)
        pyxel.text(WIDTH // 2 - 26, 60, "FISSION", RED)
        pyxel.text(WIDTH // 2 - 88, 92, "Run the reactor. Thread the needle.", GRAY)
        pyxel.text(WIDTH // 2 - 84, 116, "SPACE / CLICK  = CHARGE (add 1-6)", WHITE)
        pyxel.text(WIDTH // 2 - 84, 128, "B     / CLICK  = BANK  (cash out)", WHITE)
        pyxel.text(WIDTH // 2 - 66, 148, "Bank near the meltdown line", YELLOW)
        pyxel.text(WIDTH // 2 - 66, 158, "for a 2x CLOSE CALL! bonus", YELLOW)
        if self.best_score > 0:
            pyxel.text(WIDTH // 2 - 40, 182, "BEST %d" % self.best_score, PINK)
        pyxel.text(WIDTH // 2 - 64, 206, "PRESS SPACE TO START", LIME)

    def _draw_playing(self, ox: int, oy: int) -> None:
        pyxel.cls(NAVY)

        self._draw_timer_bar()
        pyxel.text(8, 10, "SCORE %d" % self.score, WHITE)
        self._draw_lives()

        if self.in_danger():
            if pyxel.frame_count % 12 < 6:
                pyxel.text(WIDTH // 2 - 24, 10, "DANGER", RED)

        self._draw_core(ox, oy)
        self._draw_gauge()
        self._draw_roll_pips()
        self._draw_buttons()

        pyxel.text(8, HEIGHT - 40, "W %d" % self.sensor_window, GRAY)
        pyxel.text(WIDTH - 70, HEIGHT - 40, "CLOSE x%d" % self.close_calls, PINK)

        for f in self.floats:
            pyxel.text(int(f.x), int(f.y), f.text, f.color)
        for p in self.particles:
            pyxel.pset(int(p.x) + ox, int(p.y) + oy, p.color)

        if self.flash > 0:
            self._draw_flash()

    def _draw_timer_bar(self) -> None:
        remaining = max(0, TIMER_MAX - self.frame)
        frac = remaining / TIMER_MAX
        fill = int(frac * WIDTH)
        color = GREEN if frac > 0.5 else (YELLOW if frac > 0.25 else RED)
        pyxel.rect(0, 0, WIDTH, 5, GRAY)
        if fill > 0:
            pyxel.rect(0, 0, fill, 5, color)

    def _draw_lives(self) -> None:
        for i in range(LIVES):
            color = PEACH if i < self.lives else GRAY
            pyxel.circ(WIDTH - 24 + i * 14, 14, 4, color)

    def _core_color(self) -> int:
        if self.energy >= self.threshold - EDGE_MARGIN:
            return RED
        if self.in_danger():
            return YELLOW
        return GREEN

    def _draw_core(self, ox: int, oy: int) -> None:
        r = CORE_R + self.energy // 4
        color = self._core_color()
        if self.energy >= self.threshold - EDGE_MARGIN and pyxel.frame_count % 12 < 6:
            color = WHITE
        pyxel.circ(CORE_X + ox, CORE_Y + oy, r, color)
        pyxel.circb(CORE_X + ox, CORE_Y + oy, r + 2, GRAY)
        pyxel.text(CORE_X - 4 + ox, CORE_Y - 4 + oy, "%d" % self.energy, NAVY)

    def _draw_gauge(self) -> None:
        pyxel.rect(GAUGE_X, GAUGE_Y, GAUGE_W, GAUGE_H, GRAY)

        lo, hi = self.sensor_band()
        lo = max(0, lo)
        hi = min(MAX_ENERGY, hi)
        x0 = GAUGE_X + int(lo / MAX_ENERGY * GAUGE_W)
        x1 = GAUGE_X + int(hi / MAX_ENERGY * GAUGE_W)
        for yy in range(GAUGE_Y, GAUGE_Y + GAUGE_H):
            for xx in range(x0, x1):
                if (xx + yy) % 2 == 0:
                    pyxel.pset(xx, yy, RED)
        pyxel.rectb(x0, GAUGE_Y, x1 - x0, GAUGE_H, RED)

        ex = GAUGE_X + int(self.energy / MAX_ENERGY * GAUGE_W)
        if ex > GAUGE_X:
            pyxel.rect(GAUGE_X, GAUGE_Y + 3, ex - GAUGE_X, GAUGE_H - 6, self._gauge_color())
        pyxel.rectb(GAUGE_X, GAUGE_Y, GAUGE_W, GAUGE_H, WHITE)

    def _gauge_color(self) -> int:
        if self.energy >= self.threshold - EDGE_MARGIN:
            return RED
        if self.in_danger():
            return ORANGE
        return YELLOW

    def _draw_roll_pips(self) -> None:
        if self.last_roll <= 0:
            return
        base_x = WIDTH // 2 - 14
        base_y = 116
        for i in range(self.last_roll):
            px = base_x + (i % 3) * 14
            py = base_y + (i // 3) * 14
            pyxel.circ(px, py, 3, WHITE)

    def _draw_buttons(self) -> None:
        mx = pyxel.mouse_x
        my = pyxel.mouse_y

        charge_hover = self._button_charge_contains(mx, my)
        bank_hover = self._button_bank_contains(mx, my)

        self._draw_button(CHARGE_BTN, "CHARGE", GREEN, charge_hover)
        self._draw_button(BANK_BTN, "BANK", DARK_BLUE, bank_hover)

    def _draw_button(
        self, rect: tuple[int, int, int, int], label: str, color: int, hover: bool
    ) -> None:
        x, y, w, h = rect
        pyxel.rectb(x, y, w, h, WHITE)
        if hover:
            pyxel.rect(x + 1, y + 1, w - 2, h - 2, color)
        pyxel.text(x + w // 2 - len(label) * 2, y + h // 2 - 4, label, WHITE if not hover else BLACK)

    def _draw_flash(self) -> None:
        for yy in range(0, HEIGHT, 2):
            pyxel.rect(0, yy, WIDTH, 1, RED)

    def _draw_game_over(self) -> None:
        pyxel.cls(NAVY)
        reason = self._game_over_reason or "TIME UP"
        pyxel.text(WIDTH // 2 - 32, 56, reason, RED)
        pyxel.text(WIDTH // 2 - 42, 88, "SCORE %d" % self.score, WHITE)
        pyxel.text(WIDTH // 2 - 42, 104, "BEST  %d" % self.best_score, YELLOW)
        pyxel.text(WIDTH // 2 - 50, 130, "CLOSE CALLS x%d" % self.close_calls, PINK)
        pyxel.text(WIDTH // 2 - 52, 160, "PRESS SPACE TO RETRY", LIME)


if __name__ == "__main__":
    Game()
