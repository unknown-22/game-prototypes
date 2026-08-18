"""RULE FLUX — single-button GO/NO-GO reflex game with mutating rules.

A token (number 0-9 + one of four colors) cycles in the center. A rule banner
(HIGH / EVEN / WARM / COOL) declares the current clearance rule and mutates on a
timer. Press SPACE/CLICK only when the token matches the rule (GO), refrain
otherwise (NO-GO). The challenge is re-reading the rule after each mutation and
suppressing the previous rule's reflex under time pressure.

Core fun moment: the 1-2 tokens right after a rule switch, where you fight the
old reflex, re-read the rule, and just barely press (or hold back) correctly.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ──────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
DISPLAY_SCALE = 2
FPS = 60

# Palette (Pyxel raw ints)
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

TOKEN_COLORS: tuple[int, ...] = (RED, YELLOW, LIGHT_BLUE, GREEN)
WARM_COLORS: frozenset[int] = frozenset({RED, YELLOW})
COOL_COLORS: frozenset[int] = frozenset({LIGHT_BLUE, GREEN})

HEAT_MAX = 100.0
HEAT_DECAY = 0.02
HEAT_FALSE_ALARM = 15.0
HEAT_MISS = 8.0
TIMER_MAX = 3600  # 60s at 60fps

FLUX_THRESHOLD = 4
FLUX_DURATION = 300
RULE_WARNING = 60

GRAVITY = 0.2

TOKEN_CX = 160
TOKEN_CY = 120
TOKEN_SIZE = 40

HEAT_BAR_X = 300
HEAT_BAR_W = 10
HEAT_BAR_TOP = 30
HEAT_BAR_BOTTOM = 210

TIMER_BAR_X = 10
TIMER_BAR_W = 300
TIMER_BAR_Y = 2
TIMER_BAR_H = 4

BANNER_Y = 8


# ── Enums ──────────────────────────────────────────────────────────────


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class Rule(Enum):
    HIGH = auto()  # number >= 5
    EVEN = auto()  # number % 2 == 0
    WARM = auto()  # color in {RED, YELLOW}
    COOL = auto()  # color in {LIGHT_BLUE, GREEN}


RULE_ORDER: tuple[Rule, ...] = (Rule.HIGH, Rule.EVEN, Rule.WARM, Rule.COOL)
RULE_NAMES: dict[Rule, str] = {
    Rule.HIGH: "HIGH",
    Rule.EVEN: "EVEN",
    Rule.WARM: "WARM",
    Rule.COOL: "COOL",
}


# ── Data Classes ───────────────────────────────────────────────────────


@dataclass
class Token:
    number: int  # 0-9
    color: int   # one of TOKEN_COLORS


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


# ── Game Class ─────────────────────────────────────────────────────────


class Game:
    phase: Phase
    score: int
    best_score: int
    combo: int
    max_combo: int
    heat: float
    timer: int
    elapsed: int
    rule: Rule
    rule_timer: int
    rule_warning: int
    token: Token
    cycle_timer: int
    token_elapsed: int
    flux_active: bool
    flux_timer: int
    overloaded: bool
    particles: list[Particle]
    floats: list[FloatingText]
    shake_frames: int
    rng: random.Random

    def __init__(self) -> None:
        pyxel.init(
            SCREEN_W, SCREEN_H, title="RULE FLUX", display_scale=DISPLAY_SCALE, fps=FPS
        )
        pyxel.mouse(False)
        self.rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        """Reset all play state (rng is preserved for determinism in tests)."""
        self.phase = Phase.TITLE
        self.score = 0
        self.best_score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = TIMER_MAX
        self.elapsed = 0
        self.rule = Rule.HIGH
        self.rule_timer = self._rule_interval()
        self.rule_warning = 0
        self.token = self._make_token()
        self.cycle_timer = self._cycle_interval()
        self.token_elapsed = 0
        self.flux_active = False
        self.flux_timer = 0
        self.overloaded = False
        self.particles = []
        self.floats = []
        self.shake_frames = 0

    # ── Update ─────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if self._start_pressed():
                self.phase = Phase.PLAYING
            return
        if self.phase == Phase.GAME_OVER:
            if self._start_pressed():
                self.reset()
                self.phase = Phase.PLAYING
            return
        self._update_playing()

    @staticmethod
    def _start_pressed() -> bool:
        return (
            pyxel.btnp(pyxel.KEY_SPACE)
            or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            or pyxel.btnp(pyxel.KEY_RETURN)
        )

    def _update_playing(self) -> None:
        self.elapsed += 1
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self.phase = Phase.GAME_OVER
            self.overloaded = False
            self.best_score = max(self.best_score, self.score)
            return

        self._update_heat()
        if self.phase == Phase.GAME_OVER:
            return

        self._maybe_mutate_rule()
        self._update_flux()

        self.token_elapsed += 1
        self.cycle_timer -= 1
        if self.cycle_timer <= 0:
            self._handle_token_expiry()

        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._handle_press()

        self._update_particles()
        self._update_floats()
        if self.shake_frames > 0:
            self.shake_frames -= 1

    # ── Rule / Token logic (pure, no pyxel) ────────────────────────

    @staticmethod
    def _is_go(token: Token, rule: Rule) -> bool:
        if rule is Rule.HIGH:
            return token.number >= 5
        if rule is Rule.EVEN:
            return token.number % 2 == 0
        if rule is Rule.WARM:
            return token.color in WARM_COLORS
        if rule is Rule.COOL:
            return token.color in COOL_COLORS
        return False

    @staticmethod
    def _next_rule(rule: Rule) -> Rule:
        idx = RULE_ORDER.index(rule)
        return RULE_ORDER[(idx + 1) % len(RULE_ORDER)]

    def _make_token(self) -> Token:
        return Token(number=self.rng.randrange(10), color=self.rng.choice(TOKEN_COLORS))

    def _cycle_interval(self) -> int:
        return max(12, 30 - self.elapsed // 200)

    def _rule_interval(self) -> int:
        return max(240, 480 - self.elapsed // 15)

    def _handle_press(self) -> None:
        if self._is_go(self.token, self.rule):
            self.combo += 1
            mult = 3 if self.flux_active else 1
            speed_bonus = 5 if self.token_elapsed < self._cycle_interval() // 2 else 0
            points = 10 * self.combo * mult + speed_bonus
            self.score += points
            self.max_combo = max(self.max_combo, self.combo)
            self._spawn_particles(TOKEN_CX, TOKEN_CY, self.token.color, 8, 2.0, 15, 25)
            self._spawn_float(TOKEN_CX, TOKEN_CY - 28, f"+{points}", WHITE)
            if self.combo >= FLUX_THRESHOLD and not self.flux_active:
                self._start_flux()
        else:
            self.heat += HEAT_FALSE_ALARM
            self.combo = 0
            self.shake_frames = 8
            self._spawn_particles(TOKEN_CX, TOKEN_CY, ORANGE, 4, 1.5, 10, 15)
            self._spawn_float(TOKEN_CX, TOKEN_CY - 28, "NO!", ORANGE)
        self._next_token()

    def _handle_token_expiry(self) -> None:
        if self._is_go(self.token, self.rule):
            self.heat += HEAT_MISS
            self.combo = 0
            self._spawn_particles(TOKEN_CX, TOKEN_CY, GRAY, 4, 1.5, 10, 15)
            self._spawn_float(TOKEN_CX, TOKEN_CY - 28, "MISS", GRAY)
        else:
            self.score += 5
            self._spawn_float(TOKEN_CX, TOKEN_CY - 28, "+5", CYAN)
        self._next_token()

    def _next_token(self) -> None:
        self.token = self._make_token()
        self.cycle_timer = self._cycle_interval()
        self.token_elapsed = 0

    def _update_heat(self) -> None:
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            self.overloaded = True
            self.best_score = max(self.best_score, self.score)
            return
        if not self.flux_active:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _maybe_mutate_rule(self) -> None:
        if self.flux_active:
            return
        self.rule_timer -= 1
        if self.rule_timer <= 0:
            self.rule = self._next_rule(self.rule)
            self.rule_timer = self._rule_interval()
            self.rule_warning = 0
            self._spawn_float(TOKEN_CX, BANNER_Y + 20, "RULE CHANGED", ORANGE)
            return
        self.rule_warning = self.rule_timer if self.rule_timer <= RULE_WARNING else 0

    def _update_flux(self) -> None:
        if not self.flux_active:
            return
        self.flux_timer -= 1
        if self.flux_timer <= 0:
            self.flux_active = False
            self.combo = 0

    def _start_flux(self) -> None:
        self.flux_active = True
        self.flux_timer = FLUX_DURATION
        self._spawn_particles(TOKEN_CX, TOKEN_CY, CYAN, 20, 3.0, 20, 30)
        self._spawn_float(TOKEN_CX, TOKEN_CY - 40, "FLUX!", CYAN)

    # ── Feedback helpers ───────────────────────────────────────────

    def _spawn_particles(
        self,
        x: float,
        y: float,
        color: int,
        count: int,
        vmax: float,
        life_min: int = 15,
        life_max: int = 25,
    ) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0.0, math.tau)
            speed = self.rng.uniform(0.0, vmax)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=self.rng.randint(life_min, life_max),
                    color=color,
                )
            )

    def _spawn_float(self, x: float, y: float, text: str, color: int) -> None:
        self.floats.append(FloatingText(x=x, y=y, text=text, life=40, color=color))

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.vy += GRAVITY
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floats(self) -> None:
        for ft in self.floats[:]:
            ft.y -= 1.0
            ft.life -= 1
            if ft.life <= 0:
                self.floats.remove(ft)

    # ── Draw ───────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(NAVY)
        if self.phase == Phase.TITLE:
            self._draw_title()
            return
        self._draw_playing()
        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        self._draw_cursor()

    def _draw_playing(self) -> None:
        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0:
            shake_x = self.rng.randint(-3, 3)
            shake_y = self.rng.randint(-3, 3)

        self._draw_rule_banner(shake_x, shake_y)
        self._draw_token(shake_x, shake_y)
        self._draw_heat_bar()
        self._draw_timer_bar()
        self._draw_hud()

        for p in self.particles:
            pyxel.pset(int(p.x) + shake_x, int(p.y) + shake_y, p.color)
        for ft in self.floats:
            pyxel.text(int(ft.x) + shake_x, int(ft.y) + shake_y, ft.text, ft.color)

        if self.flux_active:
            self._draw_flux_border()

    def _draw_rule_banner(self, shake_x: int, shake_y: int) -> None:
        label = f"RULE: {RULE_NAMES[self.rule]}"
        x = SCREEN_W // 2 - len(label) * 2
        if self.rule_warning > 0:
            color = ORANGE if (pyxel.frame_count // 10) % 2 == 0 else WHITE
            warn = "RULE CHANGE!"
            pyxel.text(
                SCREEN_W // 2 - len(warn) * 2 + shake_x, BANNER_Y + 14 + shake_y, warn, RED
            )
        else:
            color = WHITE
        pyxel.text(x + shake_x, BANNER_Y + shake_y, label, color)

    def _draw_token(self, shake_x: int, shake_y: int) -> None:
        x0 = TOKEN_CX - TOKEN_SIZE // 2 + shake_x
        y0 = TOKEN_CY - TOKEN_SIZE // 2 + shake_y
        pyxel.rect(x0, y0, TOKEN_SIZE, TOKEN_SIZE, self.token.color)
        number_color = PINK if self.flux_active else WHITE
        pyxel.text(
            TOKEN_CX - 2 + shake_x, TOKEN_CY - 3 + shake_y, str(self.token.number), number_color
        )

    def _draw_heat_bar(self) -> None:
        bar_h = HEAT_BAR_BOTTOM - HEAT_BAR_TOP
        fill = int(bar_h * min(self.heat, HEAT_MAX) / HEAT_MAX)
        color = ORANGE if self.heat > 50 else YELLOW
        pyxel.rectb(HEAT_BAR_X - 1, HEAT_BAR_TOP - 1, HEAT_BAR_W + 2, bar_h + 2, WHITE)
        if fill > 0:
            pyxel.rect(HEAT_BAR_X, HEAT_BAR_BOTTOM - fill, HEAT_BAR_W, fill, color)
        pyxel.text(HEAT_BAR_X - 8, HEAT_BAR_BOTTOM + 4, "HEAT", GRAY)

    def _draw_timer_bar(self) -> None:
        pyxel.rect(TIMER_BAR_X, TIMER_BAR_Y, TIMER_BAR_W, TIMER_BAR_H, DARK_BLUE)
        w = int(TIMER_BAR_W * max(self.timer, 0) / TIMER_MAX)
        if w > 0:
            pyxel.rect(TIMER_BAR_X, TIMER_BAR_Y, w, TIMER_BAR_H, CYAN)

    def _draw_hud(self) -> None:
        pyxel.text(8, 12, f"SCORE {self.score}", WHITE)
        combo_color = YELLOW if self.combo >= FLUX_THRESHOLD else WHITE
        pyxel.text(8, 24, f"COMBO x{self.combo}", combo_color)
        pyxel.text(8, 36, f"BEST {self.best_score}", GRAY)

    def _draw_flux_border(self) -> None:
        color = (pyxel.frame_count // 4) % 16
        pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, color)
        pyxel.rectb(1, 1, SCREEN_W - 2, SCREEN_H - 2, color)

    def _draw_cursor(self) -> None:
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        color = CYAN if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT) else WHITE
        pyxel.line(mx - 5, my, mx - 2, my, color)
        pyxel.line(mx + 2, my, mx + 5, my, color)
        pyxel.line(mx, my - 5, mx, my - 2, color)
        pyxel.line(mx, my + 2, mx, my + 5, color)
        pyxel.pset(mx, my, color)

    def _draw_title(self) -> None:
        self._center_text("RULE FLUX", SCREEN_H // 2 - 70, WHITE)
        self._center_text("PRESS WHEN THE TOKEN", SCREEN_H // 2 - 40, GRAY)
        self._center_text("MATCHES THE RULE", SCREEN_H // 2 - 30, GRAY)
        self._center_text("RULES: HIGH EVEN WARM COOL", SCREEN_H // 2 - 8, CYAN)
        self._center_text("SPACE / CLICK TO START", SCREEN_H // 2 + 14, WHITE)

    def _draw_game_over(self) -> None:
        pyxel.rect(0, SCREEN_H // 2 - 60, SCREEN_W, 120, BLACK)
        pyxel.rectb(0, SCREEN_H // 2 - 60, SCREEN_W, 120, WHITE)
        title = "OVERLOAD" if self.overloaded else "TIME UP"
        self._center_text(title, SCREEN_H // 2 - 48, RED)
        self._center_text(f"SCORE {self.score}", SCREEN_H // 2 - 24, WHITE)
        self._center_text(f"BEST {self.best_score}", SCREEN_H // 2 - 12, YELLOW)
        self._center_text(f"MAX COMBO x{self.max_combo}", SCREEN_H // 2, GRAY)
        self._center_text("SPACE / CLICK TO RETRY", SCREEN_H // 2 + 20, WHITE)

    def _center_text(self, s: str, y: int, color: int) -> None:
        pyxel.text(SCREEN_W // 2 - len(s) * 2, y, s, color)


# ── Entry Point ────────────────────────────────────────────────────────


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
