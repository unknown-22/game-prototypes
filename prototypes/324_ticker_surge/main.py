import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Config constants (raw ints/floats) ──
START_PRICE = 100.0
MIN_PRICE = 40.0
MAX_PRICE = 200.0
TREND_SPEED = 0.4
VOLATILITY = 0.22
MEAN_REV = 0.008  # mean-reversion pull toward START_PRICE (keeps price bounded)
BUBBLE_MAX = 100.0
BUBBLE_FILL = 0.9
BUBBLE_DRAIN = 0.7
CRASH_WARN_MIN = 40
CRASH_WARN_MAX = 90
CRASH_MULT = 2.2
CRASH_FRAMES = 45
GAME_DURATION = 3600
START_CASH = 1000.0
MARGIN_CALL = 400.0

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

WIDTH = 320
HEIGHT = 240


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
        pyxel.init(WIDTH, HEIGHT, title="TICKER SURGE")
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.cash = START_CASH
        self.shares = 0
        self.cost_basis = 0.0
        self.last_profit = 0.0
        self.price = START_PRICE
        self.trend = 1
        self.bubble = 0.0
        self.warning = False
        self.warn_frames = 0
        self.crashing = False
        self.crash_frames = 0
        self.frame = 0
        self.score = int(self._portfolio_value())
        self.best_score = getattr(self, "best_score", 0)
        self.rng = getattr(self, "rng", random.Random())
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self.shake_frames = 0
        self.last_action = ""
        self._sfx_enabled = getattr(self, "_sfx_enabled", True)
        self.price_history: list[float] = []
        self.phase = Phase.TITLE

    def _make_sound(self, *a, **k) -> None:  # noqa: ANN002, ANN003
        if self._sfx_enabled:
            pyxel.play(*a, **k)

    def _trend_speed(self) -> float:
        return TREND_SPEED * (1.0 + self.frame / GAME_DURATION * 0.8)

    def _volatility(self) -> float:
        return VOLATILITY * (1.0 + self.frame / GAME_DURATION * 1.0)

    def _portfolio_value(self) -> float:
        return self.cash + self.shares * self.price

    def _update_market(self) -> None:
        if self.crashing:
            drift = -CRASH_MULT * self._trend_speed()
        else:
            drift = self.trend * self._trend_speed()
        drift += MEAN_REV * (START_PRICE - self.price)
        self.price += drift + self.rng.uniform(-self._volatility(), self._volatility())
        if self.price < MIN_PRICE:
            self.price = MIN_PRICE
        elif self.price > MAX_PRICE:
            self.price = MAX_PRICE

        if self.trend > 0:
            self.bubble = min(BUBBLE_MAX, self.bubble + BUBBLE_FILL)
        else:
            self.bubble = max(0.0, self.bubble - BUBBLE_DRAIN)

        if not self.warning and not self.crashing and self.trend > 0 and self.bubble >= BUBBLE_MAX:
            self.warning = True
            self.warn_frames = self.rng.randint(CRASH_WARN_MIN, CRASH_WARN_MAX)
        elif self.warning:
            self.warn_frames -= 1
            if self.warn_frames <= 0:
                self.warning = False
                self.crashing = True
                self.crash_frames = CRASH_FRAMES
        elif self.crashing:
            self.crash_frames -= 1
            if self.crash_frames <= 0:
                self.crashing = False
                self.trend = -1
        elif self.trend < 0 and self.bubble <= 0.0:
            self.trend = 1

    def _buy(self) -> None:
        if self.cash >= self.price:
            qty = int(self.cash // self.price)
            if qty <= 0:
                return
            self.shares += qty
            self.cost_basis += qty * self.price
            self.cash -= qty * self.price
            self.last_action = "BUY"

    def _sell(self) -> None:
        if self.shares <= 0:
            return
        proceeds = self.shares * self.price
        self.last_profit = proceeds - self.cost_basis
        self.cash += proceeds
        self.shares = 0
        self.cost_basis = 0.0
        self.last_action = "SELL"

    def _spawn_particle(self, x: float, y: float, color: int, count: int = 16) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0.0, 2.0 * math.pi)
            speed = self.rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.sin(angle) * speed,
                    vy=math.cos(angle) * speed,
                    life=self.rng.randint(20, 50),
                    color=color,
                )
            )

    def _spawn_float(self, x: float, y: float, text: str, color: int) -> None:
        self.floats.append(FloatingText(x=x, y=y, text=text, life=60, color=color))

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self.phase = Phase.PLAYING
                self.reset()
                self.phase = Phase.PLAYING
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
                self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self.frame += 1
        self._update_market()

        if pyxel.btnp(pyxel.KEY_SPACE):
            self._buy()
            self._spawn_float(self.price, 80.0, "BUY", WHITE)
        if pyxel.btnp(pyxel.KEY_B):
            self._sell()
            if self.last_action == "SELL":
                pnl = self.last_profit
                color = LIME if pnl >= 0 else RED
                self._spawn_float(self.price, 80.0, ("+$%d" % int(pnl)), color)
                if pnl < 0:
                    self.shake_frames = 8

        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if self._button_buy_contains(mx, my):
                self._buy()
                self._spawn_float(self.price, 80.0, "BUY", WHITE)
            elif self._button_sell_contains(mx, my):
                self._sell()
                if self.last_action == "SELL":
                    pnl = self.last_profit
                    color = LIME if pnl >= 0 else RED
                    self._spawn_float(self.price, 80.0, ("+$%d" % int(pnl)), color)
                    if pnl < 0:
                        self.shake_frames = 8

        if self.warning and pyxel.frame_count % 12 < 6:
            self.shake_frames = max(self.shake_frames, 1)
        if self.crashing:
            self.shake_frames = max(self.shake_frames, 3)
            if self.rng.random() < 0.4:
                self._spawn_particle(
                    self.rng.uniform(0, WIDTH),
                    self.rng.uniform(0, HEIGHT - 80),
                    RED,
                    count=3,
                )

        self.score = int(self._portfolio_value())
        self.price_history.append(self.price)
        if len(self.price_history) > 120:
            self.price_history = self.price_history[-120:]

        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

        for f in self.floats:
            f.y -= 1.0
            f.life -= 1
        self.floats = [f for f in self.floats if f.life > 0]

        if self.shake_frames > 0:
            self.shake_frames -= 1

        reason = self._game_over_reason()
        if reason is not None:
            self._game_over(reason)

    def _game_over_reason(self) -> str | None:
        if self._portfolio_value() < MARGIN_CALL:
            return "MARGIN CALL!"
        if self.frame >= GAME_DURATION:
            return "TIME UP!"
        return None

    def _game_over(self, reason: str) -> None:
        self.best_score = max(self.best_score, self.score)
        self.phase = Phase.GAME_OVER
        self.game_over_reason = reason

    def _button_buy_contains(self, mx: int, my: int) -> bool:
        return 10 <= mx <= 90 and HEIGHT - 34 <= my <= HEIGHT - 10

    def _button_sell_contains(self, mx: int, my: int) -> bool:
        return 100 <= mx <= 180 and HEIGHT - 34 <= my <= HEIGHT - 10

    def draw(self) -> None:
        if self.shake_frames > 0:
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
        pyxel.text(WIDTH // 2 - 42, 70, "TICKER SURGE", LIME)
        pyxel.text(WIDTH // 2 - 52, 100, "SPACE BUY   B SELL", WHITE)
        pyxel.text(WIDTH // 2 - 34, 130, "PRESS ENTER", YELLOW)
        pyxel.text(WIDTH // 2 - 60, 160, "Buy low, sell high.", GRAY)

    def _draw_playing(self, ox: int, oy: int) -> None:
        pyxel.cls(NAVY)

        chart_top = HEIGHT - 80
        chart_bottom = HEIGHT - 1

        if len(self.price_history) >= 2:
            mn = min(self.price_history)
            mxp = max(self.price_history)
            span = mxp - mn if mxp > mn else 1.0
            prev_x = 0
            prev_y = None
            prev_price = None
            for i, p in enumerate(self.price_history):
                x = int(i / 119 * (WIDTH - 68)) + 8
                y = chart_bottom - int((p - mn) / span * (chart_top - 20))
                if prev_y is not None and prev_price is not None:
                    color = LIME if p > prev_price else RED
                    pyxel.line(x, y, prev_x, prev_y, color)
                prev_x = x
                prev_y = y
                prev_price = p

        pyxel.rectb(8, chart_top, WIDTH - 60, chart_bottom - chart_top, GRAY)

        self._draw_bubble_meter()

        pnl = self.score - int(START_CASH)
        pnl_text = "P&L %+d" % pnl
        pnl_color = LIME if pnl >= 0 else RED
        pyxel.text(WIDTH // 2 - 20, 6, pnl_text, pnl_color)

        pyxel.text(8, 24, "CASH %d" % int(self.cash), WHITE)
        pyxel.text(8, 32, "SHARES %d" % self.shares, WHITE)
        pyxel.text(8, 40, "PRICE %d" % round(self.price), WHITE)

        remaining = max(0, GAME_DURATION - self.frame)
        seconds = remaining // 60
        pyxel.text(WIDTH - 48, 24, "TIME %d" % seconds, WHITE)

        if self.warning:
            if pyxel.frame_count % 12 < 6:
                pyxel.text(WIDTH // 2 - 20, 50, "CRASH!", RED)

        self._draw_buttons()

        for f in self.floats:
            pyxel.text(int(f.x), int(f.y), f.text, f.color)

        for p in self.particles:
            pyxel.pset(int(p.x) + ox, int(p.y) + oy, p.color)

    def _draw_bubble_meter(self) -> None:
        bx = WIDTH - 30
        pyxel.text(bx - 6, 6, "BUBBLE", WHITE)
        bar_top = 16
        bar_bottom = HEIGHT - 80
        pyxel.rectb(bx, bar_top, 14, bar_bottom - bar_top, GRAY)
        fill = int((self.bubble / BUBBLE_MAX) * (bar_bottom - bar_top - 2))
        if fill > 0:
            if self.bubble >= 80:
                color = RED
            elif self.bubble >= 50:
                color = ORANGE
            else:
                color = YELLOW
            pyxel.rect(bx + 1, bar_bottom - 1 - fill, 12, fill, color)

    def _draw_buttons(self) -> None:
        mx = pyxel.mouse_x
        my = pyxel.mouse_y

        buy_hover = self._button_buy_contains(mx, my)
        sell_hover = self._button_sell_contains(mx, my)

        pyxel.rectb(10, HEIGHT - 34, 80, 24, WHITE)
        if buy_hover:
            pyxel.rect(11, HEIGHT - 33, 78, 22, GREEN)
        pyxel.text(22, HEIGHT - 28, "BUY", GREEN if not buy_hover else BLACK)

        pyxel.rectb(100, HEIGHT - 34, 80, 24, WHITE)
        if sell_hover:
            pyxel.rect(101, HEIGHT - 33, 78, 22, RED)
        pyxel.text(112, HEIGHT - 28, "SELL", RED if not sell_hover else BLACK)

    def _draw_game_over(self) -> None:
        pyxel.cls(NAVY)
        reason = getattr(self, "game_over_reason", "TIME UP!")
        pyxel.text(WIDTH // 2 - 30, 60, reason, RED)
        pyxel.text(WIDTH // 2 - 50, 90, "SCORE %d" % self.score, WHITE)
        pyxel.text(WIDTH // 2 - 50, 110, "BEST %d" % self.best_score, YELLOW)
        pyxel.text(WIDTH // 2 - 55, 140, "PRESS R TO RESTART", LIME)


if __name__ == "__main__":
    Game()
