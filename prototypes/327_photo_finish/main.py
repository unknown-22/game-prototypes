"""Photo Finish — pari-mutuel horse racing value betting prototype.

Spot the gap between a horse's HIDDEN true form and its PUBLIC odds, bet on the
undervalued long-shot, then watch it charge from behind to WIN at the finish.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum

import pyxel

# --- Screen & timing ---
SCREEN_W = 320
SCREEN_H = 240
FPS = 60
GAME_DURATION = 3600  # 60 seconds

# --- Track layout ---
HORSES = 5
LANE_Y = [40, 78, 116, 154, 192]
LANE_HEIGHT = 38
START_X = 24
FINISH_X = 280
HORSE_COLORS = [8, 11, 5, 10, 2]  # RED, LIME, DARK_BLUE, YELLOW, PURPLE

# --- Betting ---
START_BANK = 1000
MIN_BET = 50
MAX_BET = 1000
STAKE_STEP = 50

# --- Hidden form ---
FORM_MIN = 50.0
FORM_MAX = 100.0

# --- Gauge / odds dynamics ---
GAUGE_BAND_START = 25.0
GAUGE_BAND_MIN = 8.0
ODDS_DRIFT = 0.004

# --- Race dynamics ---
SPEED_K = 0.008
RACE_SPREAD_MIN = 14.0
RACE_SPREAD_MAX = 20.0
PADDOCK_FRAMES_START = 240
PADDOCK_FRAMES_MIN = 160

# --- Result pause ---
RESULT_FRAMES = 90

# --- Palette (raw ints) ---
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
    TITLE = "title"
    PADDOCK = "paddock"
    RACE = "race"
    RESULT = "result"
    GAME_OVER = "game_over"


@dataclass
class Horse:
    lane: int
    color: int
    form: float
    true_odds: float
    odds: float
    gauge_lo: float
    gauge_hi: float
    race_speed: float
    pos_x: float


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


def _make_game(seed: int | None = None) -> "Game":
    """Factory for tests: builds a Game without running pyxel."""
    game = Game.__new__(Game)
    game.reset(seed)
    return game


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, "Photo Finish", fps=FPS)
        self.reset()
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    def reset(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)
        self.phase: Phase = Phase.TITLE
        self.frame: int = 0
        self.bankroll: int = START_BANK
        self.stake: int = 200
        self.selected: int = 0
        self.horses: list[Horse] = []
        self.best_bankroll: int = START_BANK
        self.score: int = 0
        self.paddock_frames: int = 0
        self._paddock_start_frames: int = PADDOCK_FRAMES_START
        self.result_frames: int = RESULT_FRAMES
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.winner_lane: int | None = None
        self._last_result: str = ""
        self._game_over_reason: str = ""
        self._bet_placed: bool = False
        self._bet_stake: int = 0
        self._bet_odds: float = 1.0
        self._shake: int = 0
        self._start_paddock()
        self.phase = Phase.TITLE

    # ------------------------------------------------------------------
    # Core logic (no pyxel input)
    # ------------------------------------------------------------------
    def _generate_horses(self) -> None:
        horses: list[Horse] = []
        for lane in range(HORSES):
            form = self.rng.uniform(FORM_MIN, FORM_MAX)
            true_odds = round(
                8.0 - (form - FORM_MIN) * (6.5 / (FORM_MAX - FORM_MIN)), 1
            )
            odds = round(
                self._clamp(true_odds * self.rng.uniform(0.75, 1.45), 1.5, 8.0), 1
            )
            horses.append(
                Horse(
                    lane=lane,
                    color=HORSE_COLORS[lane],
                    form=form,
                    true_odds=true_odds,
                    odds=odds,
                    gauge_lo=FORM_MIN,
                    gauge_hi=FORM_MAX,
                    race_speed=0.0,
                    pos_x=float(START_X),
                )
            )
        self.horses = horses

    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    def _gauge_band(self) -> float:
        if self._paddock_start_frames <= 0:
            progress = 1.0
        else:
            progress = 1.0 - self.paddock_frames / self._paddock_start_frames
        progress = self._clamp(progress, 0.0, 1.0)
        band = GAUGE_BAND_START - (GAUGE_BAND_START - GAUGE_BAND_MIN) * progress
        return max(GAUGE_BAND_MIN, band)

    def _narrow_gauges(self) -> None:
        band = self._gauge_band()
        for h in self.horses:
            h.gauge_lo = max(h.gauge_lo, h.form - band)
            h.gauge_hi = min(h.gauge_hi, h.form + band)

    def _drift_odds(self) -> None:
        for h in self.horses:
            h.odds += (h.true_odds - h.odds) * ODDS_DRIFT
            h.odds = self._clamp(h.odds, 1.5, 8.0)

    def _lock_bet(self) -> None:
        stake = min(self.stake, self.bankroll)
        self.bankroll -= stake
        self._bet_stake = stake
        self._bet_odds = self.horses[self.selected].odds
        spread = self._race_spread()
        for h in self.horses:
            h.race_speed = h.form + self.rng.uniform(-spread, spread)
        self._bet_placed = True
        self._last_result = ""
        self.winner_lane = None
        self.result_frames = RESULT_FRAMES
        self._spawn_burst(
            START_X + 6,
            LANE_Y[self.selected] + LANE_HEIGHT // 2,
            self.horses[self.selected].color,
            n=10,
        )
        self.phase = Phase.RACE

    def _race_spread(self) -> float:
        t = self._clamp(self.frame / GAME_DURATION, 0.0, 1.0)
        return RACE_SPREAD_MIN + (RACE_SPREAD_MAX - RACE_SPREAD_MIN) * t

    def _paddock_frames_start(self) -> int:
        t = self._clamp(self.frame / GAME_DURATION, 0.0, 1.0)
        return int(PADDOCK_FRAMES_START - (PADDOCK_FRAMES_START - PADDOCK_FRAMES_MIN) * t)

    def _update_paddock(self) -> None:
        self.paddock_frames -= 1
        self._narrow_gauges()
        self._drift_odds()
        if self.paddock_frames <= 0:
            self._lock_bet()

    def _update_race(self) -> None:
        for h in self.horses:
            h.pos_x += h.race_speed * SPEED_K * self.rng.uniform(0.98, 1.02)
            if h.pos_x >= FINISH_X:
                h.pos_x = float(FINISH_X)
                self.winner_lane = h.lane
                self._resolve_result()
                return

    def _resolve_result(self) -> None:
        self.phase = Phase.RESULT
        self.result_frames = RESULT_FRAMES
        if self.winner_lane == self.selected:
            net = round(self._bet_stake * self._bet_odds)
            self.bankroll += net
            self._last_result = "WIN"
            y = LANE_Y[self.selected] + LANE_HEIGHT // 2
            self._spawn_burst(FINISH_X - 6, y, self.horses[self.selected].color, n=16)
            self.floating_texts.append(
                FloatingText(FINISH_X - 10, y - 14, f"+{net}", 70, LIME)
            )
            self.best_bankroll = max(self.best_bankroll, self.bankroll)
        else:
            self._last_result = "LOSE"
            y = LANE_Y[self.selected] + LANE_HEIGHT // 2
            self.floating_texts.append(
                FloatingText(START_X + 4, y - 14, f"-{self._bet_stake}", 70, RED)
            )
            self._shake = 12
        if self.bankroll < MIN_BET:
            self._game_over_reason = "BANKRUPT"
            self.score = self.bankroll
            self.phase = Phase.GAME_OVER

    def _update_result(self) -> None:
        self.result_frames -= 1
        if self.result_frames <= 0:
            if self.bankroll < MIN_BET:
                self._game_over_reason = "BANKRUPT"
                self.score = self.bankroll
                self.phase = Phase.GAME_OVER
            else:
                self._start_paddock()

    def _start_paddock(self) -> None:
        self._generate_horses()
        self._paddock_start_frames = self._paddock_frames_start()
        self.paddock_frames = self._paddock_start_frames
        self._bet_placed = False
        self.winner_lane = None
        self._last_result = ""
        self.phase = Phase.PADDOCK

    def _update_timer(self) -> None:
        self.frame += 1
        if self.frame >= GAME_DURATION:
            self._game_over_reason = "TIME UP"
            self.score = self.bankroll
            self.phase = Phase.GAME_OVER

    def game_over_reason(self) -> str:
        return self._game_over_reason

    def _update_fx(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]
        for t in self.floating_texts:
            t.y -= 0.5
            t.life -= 1
        self.floating_texts = [t for t in self.floating_texts if t.life > 0]
        if self._shake > 0:
            self._shake -= 1

    def _spawn_burst(self, x: float, y: float, color: int, n: int = 12) -> None:
        for _ in range(n):
            ang = self.rng.uniform(0.0, math.tau)
            spd = self.rng.uniform(0.4, 2.0)
            self.particles.append(
                Particle(
                    x,
                    y,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    self.rng.randint(10, 25),
                    color,
                )
            )

    # ------------------------------------------------------------------
    # Input (thin wrappers — the ONLY place pyxel input is read)
    # ------------------------------------------------------------------
    def update(self) -> None:
        if self.phase is Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.PADDOCK
        elif self.phase is Phase.PADDOCK:
            if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A):
                self.selected = (self.selected - 1) % HORSES
            elif pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D):
                self.selected = (self.selected + 1) % HORSES
            if pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.KEY_W):
                self.stake = min(self.stake + STAKE_STEP, MAX_BET, self.bankroll)
            elif pyxel.btnp(pyxel.KEY_DOWN) or pyxel.btnp(pyxel.KEY_S):
                self.stake = max(self.stake - STAKE_STEP, MIN_BET)
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self._lock_bet()
            self._update_paddock()
            self._update_fx()
            self._update_timer()
        elif self.phase is Phase.RACE:
            self._update_race()
            self._update_fx()
            self._update_timer()
        elif self.phase is Phase.RESULT:
            self._update_result()
            self._update_fx()
            self._update_timer()
        elif self.phase is Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def _shake_offset(self) -> tuple[int, int]:
        if self._shake <= 0:
            return 0, 0
        ox = (self._shake * 7 + self.frame) % 5 - 2
        oy = (self._shake * 11 + self.frame) % 3 - 1
        return ox, oy

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase is Phase.TITLE:
            self._draw_title()
        elif self.phase is Phase.PADDOCK:
            self._draw_paddock()
        elif self.phase is Phase.RACE:
            self._draw_race()
        elif self.phase is Phase.RESULT:
            self._draw_result()
        elif self.phase is Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 42, 60, "PHOTO FINISH", YELLOW)
        pyxel.text(SCREEN_W // 2 - 60, 80, "Value betting on the turf", GRAY)
        pyxel.text(SCREEN_W // 2 - 70, 120, "SPACE: start / lock bet", WHITE)
        pyxel.text(SCREEN_W // 2 - 70, 132, "LEFT/RIGHT: select horse", WHITE)
        pyxel.text(SCREEN_W // 2 - 70, 144, "UP/DOWN: change stake", WHITE)
        pyxel.text(SCREEN_W // 2 - 70, 176, "Find the long-shot hiding", LIME)
        pyxel.text(SCREEN_W // 2 - 70, 188, "behind the public odds.", LIME)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"BANK ${self.bankroll}", WHITE)
        pyxel.text(160, 4, f"STAKE ${self.stake}", WHITE)
        remain = max(0, GAME_DURATION - self.frame)
        secs = remain / FPS
        pyxel.text(280, 4, f"{secs:4.1f}s", WHITE)
        bar_w = int(140 * remain / GAME_DURATION)
        pyxel.rect(4, 14, 140, 4, GRAY)
        pyxel.rect(4, 14, bar_w, 4, CYAN)

    def _draw_gauge(self, h: Horse, x: int, y: int, w: int) -> None:
        def tx(form: float) -> int:
            return x + int((form - FORM_MIN) / (FORM_MAX - FORM_MIN) * w)

        pyxel.rect(x, y, w, 6, GRAY)
        lo_x = tx(max(FORM_MIN, h.gauge_lo))
        hi_x = tx(min(FORM_MAX, h.gauge_hi))
        pyxel.rect(lo_x, y, hi_x - lo_x, 6, GREEN)
        mid = tx((h.gauge_lo + h.gauge_hi) / 2.0)
        pyxel.rect(mid, y - 1, 1, 8, WHITE)

    def _draw_paddock(self) -> None:
        self._draw_hud()
        for i, h in enumerate(self.horses):
            y = LANE_Y[i]
            if i == self.selected:
                pyxel.rectb(START_X - 6, y - 4, 120, LANE_HEIGHT - 2, WHITE)
            pyxel.rect(START_X, y, 12, 16, h.color)
            pyxel.text(START_X + 18, y + 4, f"x{h.odds:.1f}", YELLOW)
            self._draw_gauge(h, START_X + 60, y + 6, 110)
        pyxel.text(4, 226, "Horse / odds / form gauge", GRAY)
        pyxel.text(200, 226, "SPACE to lock bet", WHITE)

    def _draw_race(self) -> None:
        ox, oy = self._shake_offset()
        self._draw_hud()
        pyxel.line(FINISH_X + ox, 20 + oy, FINISH_X + ox, 210 + oy, WHITE)
        for h in self.horses:
            y = LANE_Y[h.lane]
            pyxel.rect(int(h.pos_x - 10) + ox, y + oy, 8, 16, GRAY)
            pyxel.rect(int(h.pos_x) + ox, y + oy, 12, 16, h.color)
        self._draw_fx(ox, oy)

    def _draw_result(self) -> None:
        self._draw_race()
        if self._last_result == "WIN":
            net = round(self._bet_stake * self._bet_odds)
            pyxel.text(SCREEN_W // 2 - 34, 12, f"WIN +{net}", LIME)
        else:
            pyxel.text(SCREEN_W // 2 - 34, 12, f"LOSE -{self._bet_stake}", RED)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 46, 90, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 46, 104, self._game_over_reason, YELLOW)
        pyxel.text(SCREEN_W // 2 - 46, 116, f"FINAL SCORE ${self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 46, 128, f"BEST BANK ${self.best_bankroll}", GRAY)
        pyxel.text(SCREEN_W // 2 - 46, 152, "SPACE: retry", WHITE)

    def _draw_fx(self, ox: int = 0, oy: int = 0) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x) + ox, int(p.y) + oy, p.color)
        for t in self.floating_texts:
            pyxel.text(int(t.x) + ox, int(t.y) + oy, t.text, t.color)


if __name__ == "__main__":
    Game()
