"""ANTIQUE AUCTION — Hidden-Value Appraisal Timing Game.

Antique lots of hidden true value V come up one at a time. The player bids at
the right moment to earn a profit. The true value is only partially observable:
an appraisal band [lo, hi] NARROWS toward V over time but never fully reveals it.
Meanwhile the auction price climbs continuously. Bid early = cheap but blind
(high variance). Bid late = informed but expensive (price may exceed value).
Pure value-estimation + timing risk/reward. No color matching, no COMBO, no HEAT.
"""
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Config constants ──
WIDTH = 320
HEIGHT = 240
FPS = 60

MIN_V = 40
MAX_V = 200
BAND_LO_START = 10
BAND_HI_START = 230
RESIDUAL = 25
PRICE_START = 120
PRICE_END = 220
OBSERVE_FRAMES = 90
LOT_FRAMES = 150
START_BANKROLL = 1000
GAME_DURATION = 3600
VALUE_SCALE_MAX = 250
RESULT_MAX = 12

LOT_X = 160
LOT_Y = 80
BAND_X0 = 40
BAND_X1 = 280
BAND_Y = 150

BID_BTN = (232, 204, 80, 28)

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
class Lot:
    value: int
    age: int


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    gravity: float = 0.2


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int


class Game:
    def __init__(self) -> None:
        pyxel.init(WIDTH, HEIGHT, title="ANTIQUE AUCTION", fps=FPS)
        pyxel.mouse(True)
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── State management ──

    def reset(self) -> None:
        self.rng: random.Random = getattr(self, "rng", random.Random())
        self.best_bankroll: int = getattr(self, "best_bankroll", 0)
        self.phase = Phase.TITLE
        self.frame = 0
        self.bankroll = START_BANKROLL
        self.lots_bid = 0
        self.lots_passed = 0
        self.lot: Lot | None = None
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self.shake = 0
        self.flash = 0
        self.results: list[int | None] = []
        self._reveal_value = 0
        self._reveal_timer = 0
        self._last_profit = 0
        self._game_over_reason_str = ""
        self._new_lot()

    def _new_lot(self) -> None:
        self.lot = Lot(value=self.rng.randint(MIN_V, MAX_V), age=0)

    # ── Pure logic helpers (testable, no pyxel input/sound) ──

    def _residual(self, frame: int) -> int:
        return int(RESIDUAL + 15 * (frame / GAME_DURATION))

    def _lot_frames(self, frame: int) -> int:
        return int(LOT_FRAMES - 50 * (frame / GAME_DURATION))

    def _observe_frames(self, frame: int) -> int:
        return int(OBSERVE_FRAMES - 40 * (frame / GAME_DURATION))

    def _band(self, lot: Lot, frame: int) -> tuple[int, int]:
        observe = self._observe_frames(frame)
        residual = self._residual(frame)
        p = min(1.0, lot.age / observe)
        start_half = (BAND_HI_START - BAND_LO_START) / 2.0
        start_center = (BAND_LO_START + BAND_HI_START) / 2.0
        half_width = start_half + (residual - start_half) * p
        center = start_center + (float(lot.value) - start_center) * p
        lo = int(center - half_width)
        hi = int(center + half_width)
        return lo, hi

    def _band_lo(self, lot: Lot, frame: int) -> int:
        return self._band(lot, frame)[0]

    def _band_hi(self, lot: Lot, frame: int) -> int:
        return self._band(lot, frame)[1]

    def _current_price(self, lot: Lot, frame: int) -> int:
        lf = self._lot_frames(frame)
        p = PRICE_START + (PRICE_END - PRICE_START) * (lot.age / lf)
        return min(PRICE_END, int(p))

    def _game_over_reason(self) -> str:
        return "BANKRUPT" if self.bankroll <= 0 else "TIME UP"

    # ── Core actions (testable) ──

    def _bid(self) -> None:
        if self.phase != Phase.PLAYING or self.lot is None:
            return
        lot = self.lot
        price = self._current_price(lot, self.frame)
        profit = lot.value - price
        self.bankroll += profit
        self.lots_bid += 1
        self._last_profit = profit
        self._reveal_value = lot.value
        self._reveal_timer = 45
        self._record_result(profit)
        if profit >= 0:
            self._spawn_float(LOT_X, LOT_Y - 44, "+$%d" % profit, LIME)
            self._burst(LOT_X, LOT_Y, LIME, 6, 2.0, 20, 40)
            self._burst(LOT_X, LOT_Y, YELLOW, 6, 2.0, 20, 40)
        else:
            self._spawn_float(LOT_X, LOT_Y - 44, "-$%d" % abs(profit), RED)
            self._burst(LOT_X, LOT_Y, RED, 8, 2.0, 20, 40)
            self.shake = 8
        self._new_lot()
        if self.bankroll <= 0:
            self._game_over("BANKRUPT")

    def _resolve_sold_to_rival(self) -> None:
        if self.lot is None:
            return
        self.lots_passed += 1
        self._spawn_float(LOT_X, LOT_Y - 44, "SOLD", GRAY)
        self._burst(LOT_X, LOT_Y, GRAY, 4, 1.0, 15, 30, gravity=0.1)
        self._record_result(None)
        self._new_lot()

    def _record_result(self, profit: int | None) -> None:
        self.results.append(profit)
        if len(self.results) > RESULT_MAX:
            self.results = self.results[-RESULT_MAX:]

    def _game_over(self, reason: str) -> None:
        self._game_over_reason_str = reason
        self.best_bankroll = max(self.best_bankroll, self.bankroll)
        self.phase = Phase.GAME_OVER
        if reason == "BANKRUPT":
            self.flash = 30
            self.shake = 12

    # ── Effects (testable, list-only) ──

    def _spawn_particle(
        self,
        x: float,
        y: float,
        color: int,
        speed: float,
        life_min: int,
        life_max: int,
        gravity: float = 0.2,
    ) -> None:
        self.particles.append(
            Particle(
                x=x,
                y=y,
                vx=self.rng.uniform(-speed, speed),
                vy=self.rng.uniform(-speed, speed),
                life=self.rng.randint(life_min, life_max),
                color=color,
                gravity=gravity,
            )
        )

    def _burst(
        self,
        x: float,
        y: float,
        color: int,
        count: int,
        speed: float,
        life_min: int,
        life_max: int,
        gravity: float = 0.2,
    ) -> None:
        for _ in range(count):
            self._spawn_particle(x, y, color, speed, life_min, life_max, gravity)

    def _spawn_float(self, x: float, y: float, text: str, color: int) -> None:
        self.floats.append(FloatingText(x=x, y=y, text=text, life=30, color=color))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.vy += p.gravity
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floats(self) -> None:
        for f in self.floats:
            f.y -= 1.0
            f.life -= 1
        self.floats = [f for f in self.floats if f.life > 0]

    # ── Input / geometry helpers (testable) ──

    def _button_bid_contains(self, mx: int, my: int) -> bool:
        x, y, w, h = BID_BTN
        return x <= mx <= x + w and y <= my <= y + h

    def _scale_x(self, v: float) -> int:
        return BAND_X0 + int(v / VALUE_SCALE_MAX * (BAND_X1 - BAND_X0))

    # ── Update / phase machine ──

    def update(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()
            self.phase = Phase.PLAYING
            return
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
                or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            ):
                self.reset()
                self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self.frame += 1

        if self.lot is not None:
            self.lot.age += 1
            if self.lot.age >= self._lot_frames(self.frame):
                self._resolve_sold_to_rival()

        if pyxel.btnp(pyxel.KEY_SPACE):
            self._bid()
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and self._button_bid_contains(mx, my):
            self._bid()

        if self._reveal_timer > 0:
            self._reveal_timer -= 1
        self._update_particles()
        self._update_floats()

        if self.shake > 0:
            self.shake -= 1
        if self.flash > 0:
            self.flash -= 1

        if self.bankroll <= 0 or self.frame >= GAME_DURATION:
            self._game_over(self._game_over_reason())

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
        pyxel.text(WIDTH // 2 - 52, 56, "ANTIQUE AUCTION", YELLOW)
        pyxel.text(WIDTH // 2 - 56, 84, "BID LOW. BUY TREASURE.", GRAY)
        pyxel.text(WIDTH // 2 - 80, 116, "A lot hides a true value V.", WHITE)
        pyxel.text(WIDTH // 2 - 80, 128, "The appraisal band narrows toward V", WHITE)
        pyxel.text(WIDTH // 2 - 80, 140, "while the price keeps climbing.", WHITE)
        pyxel.text(WIDTH // 2 - 56, 162, "SPACE / CLICK = BID", LIME)
        pyxel.text(WIDTH // 2 - 56, 174, "R            = RESTART", WHITE)
        if self.best_bankroll > 0:
            pyxel.text(WIDTH // 2 - 40, 196, "BEST $%d" % self.best_bankroll, PINK)
        pyxel.text(WIDTH // 2 - 64, 216, "PRESS SPACE TO START", LIME)

    def _draw_playing(self, ox: int, oy: int) -> None:
        pyxel.cls(NAVY)

        self._draw_timer_bar()

        cash_color = RED if self.bankroll < 300 else WHITE
        pyxel.text(8, 10, "CASH $%d" % self.bankroll, cash_color)
        pyxel.text(8, 22, "BID %d  PASS %d" % (self.lots_bid, self.lots_passed), GRAY)

        self._draw_lot(ox, oy)
        self._draw_band(ox, oy)
        self._draw_results()
        self._draw_button()

        for f in self.floats:
            pyxel.text(int(f.x) + ox, int(f.y) + oy, f.text, f.color)
        for p in self.particles:
            pyxel.pset(int(p.x) + ox, int(p.y) + oy, p.color)

        if self.flash > 0:
            self._draw_flash()

    def _draw_timer_bar(self) -> None:
        remaining = max(0, GAME_DURATION - self.frame)
        frac = remaining / GAME_DURATION
        bar_w = 300
        fill = int(frac * bar_w)
        color = GREEN if frac > 0.5 else (YELLOW if frac > 0.25 else RED)
        pyxel.rect(10, 0, bar_w, 5, GRAY)
        if fill > 0:
            pyxel.rect(10, 0, fill, 5, color)

    def _draw_lot(self, ox: int, oy: int) -> None:
        pyxel.text(LOT_X - 12, LOT_Y - 34, "LOT", GRAY)
        pyxel.rectb(LOT_X - 42 + ox, LOT_Y - 26 + oy, 84, 52, WHITE)
        pyxel.rect(LOT_X - 40 + ox, LOT_Y - 24 + oy, 80, 48, BROWN)
        pyxel.text(LOT_X - 3 + ox, LOT_Y - 6 + oy, "?", WHITE)

    def _draw_band(self, ox: int, oy: int) -> None:
        pyxel.line(BAND_X0, BAND_Y, BAND_X1, BAND_Y, WHITE)
        pyxel.text(BAND_X0 - 2, BAND_Y + 8, "0", GRAY)
        pyxel.text(BAND_X1 - 8, BAND_Y + 8, "250", GRAY)
        pyxel.text(BAND_X0 - 2, BAND_Y - 20, "VALUE", GRAY)

        if self.lot is not None:
            lo = max(0, self._band_lo(self.lot, self.frame))
            hi = min(VALUE_SCALE_MAX, self._band_hi(self.lot, self.frame))
            x0 = self._scale_x(lo)
            x1 = self._scale_x(hi)
            pyxel.rect(x0, BAND_Y - 6, x1 - x0, 12, CYAN)
            pyxel.rectb(x0, BAND_Y - 6, x1 - x0, 12, LIGHT_BLUE)

            price = self._current_price(self.lot, self.frame)
            px = self._scale_x(price)
            pyxel.line(px, BAND_Y - 10, px, BAND_Y + 10, YELLOW)
            pyxel.text(BAND_X0, BAND_Y - 40, "PRICE $%d" % price, YELLOW)

            if self._reveal_timer > 0:
                vx = self._scale_x(self._reveal_value)
                color = LIME if self._last_profit >= 0 else RED
                pyxel.tri(vx, BAND_Y - 16, vx - 4, BAND_Y - 8, vx + 4, BAND_Y - 8, color)
                pyxel.text(vx - 12, BAND_Y - 30, "$%d" % self._reveal_value, color)

    def _draw_results(self) -> None:
        pyxel.text(8, HEIGHT - 28, "RESULTS", GRAY)
        y = HEIGHT - 14
        for i, r in enumerate(self.results):
            if r is None:
                color = GRAY
            elif r >= 0:
                color = LIME
            else:
                color = RED
            pyxel.rect(8 + i * 10, y, 8, 8, color)

    def _draw_button(self) -> None:
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        hover = self._button_bid_contains(mx, my)
        x, y, w, h = BID_BTN
        pyxel.rectb(x, y, w, h, WHITE)
        if hover:
            pyxel.rect(x + 1, y + 1, w - 2, h - 2, DARK_BLUE)
        pyxel.text(x + w // 2 - 8, y + h // 2 - 4, "BID", WHITE if not hover else BLACK)

    def _draw_flash(self) -> None:
        for yy in range(0, HEIGHT, 2):
            pyxel.rect(0, yy, WIDTH, 1, RED)

    def _draw_game_over(self) -> None:
        pyxel.cls(NAVY)
        reason = self._game_over_reason_str or "TIME UP"
        pyxel.text(WIDTH // 2 - 32, 56, reason, RED)
        pyxel.text(WIDTH // 2 - 52, 88, "FINAL CASH $%d" % self.bankroll, WHITE)
        pyxel.text(WIDTH // 2 - 52, 104, "BEST       $%d" % self.best_bankroll, YELLOW)
        pyxel.text(WIDTH // 2 - 52, 124, "LOTS BID    %d" % self.lots_bid, GRAY)
        pyxel.text(WIDTH // 2 - 52, 136, "LOTS PASSED %d" % self.lots_passed, GRAY)
        pyxel.text(WIDTH // 2 - 56, 168, "PRESS SPACE TO RETRY", LIME)


if __name__ == "__main__":
    Game()
