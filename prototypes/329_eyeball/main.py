"""EYEBALL — Carnival Estimation Arcade (prototype 329_eyeball).

A quick-estimation arcade game: a quantity flashes briefly (a count of dots or a
bar fill percentage), then the player sets a slider estimate and commits it with a
confidence bet. SAFE nets 1x with a loose tolerance; RISKY nets 3x with a tight
tolerance. Streaks reward sustained accuracy.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum

import pyxel

# Screen
WIDTH = 320
HEIGHT = 240

# Color constants
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

# Game constants
MAX_COUNT = 40
GAME_DURATION = 3600
REVEAL_FRAMES = 45

# UI layout
TIMER_X = 8
TIMER_Y = 6
TIMER_W = 304
TIMER_H = 8
STIMULUS_TOP = 60
STIMULUS_BOTTOM = 130
FRACTION_BAR_X = 40
FRACTION_BAR_Y = 95
FRACTION_BAR_W = 240
FRACTION_BAR_H = 20
SLIDER_X = 40
SLIDER_Y = 150
SLIDER_W = 240
SLIDER_H = 10
SAFE_BTN_X = 60
SAFE_BTN_Y = 170
SAFE_BTN_W = 80
BTN_H = 22
RISKY_BTN_X = 180
RISKY_BTN_Y = 170
RISKY_BTN_W = 80
LOCK_BTN_X = 110
LOCK_BTN_Y = 200
LOCK_BTN_W = 100
LOCK_BTN_H = 24


class Phase(Enum):
    TITLE = "title"
    PLAYING = "playing"
    GAME_OVER = "game_over"


class TaskState(Enum):
    SHOW = "show"
    GUESS = "guess"
    REVEAL = "reveal"


class TaskType(Enum):
    COUNT = "count"
    FRACTION = "fraction"


class Confidence(Enum):
    SAFE = "safe"
    RISKY = "risky"


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


# --------------------------------------------------------------------------
# Pure, testable helpers
# --------------------------------------------------------------------------


def _flash_frames(frame: int) -> int:
    """Frames the stimulus stays visible, shrinking over time (40f -> 12f)."""
    return max(12, 40 - frame // 90)


def _count_range(frame: int) -> tuple[int, int]:
    """Truth range for COUNT tasks, widening over time (5..16 -> 5..34)."""
    return (5, min(40, 16 + frame // 200))


def _solve_window(frame: int) -> int:
    """Frames allowed to answer a task (260f -> 120f)."""
    return max(120, 260 - frame // 30)


def _tolerance_for(confidence: Confidence) -> int:
    return 4 if confidence is Confidence.SAFE else 1


def _score_guess(
    estimate: int, truth: int, confidence: Confidence, streak: int
) -> tuple[int, str]:
    """Pure scoring function. Returns (points, label) without mutating state."""
    tol = _tolerance_for(confidence)
    if abs(estimate - truth) <= tol:
        mult = 3 if confidence is Confidence.RISKY else 1
        new_streak = streak + 1
        points = 20 * mult + new_streak * 10
        label = "HIT!"
        if estimate == truth:
            points += 30
            label = "PERFECT!"
        return points, label
    return 0, "MISS"


class Game:
    def __init__(self) -> None:
        self.rng: random.Random = random.Random()
        self.best_score = 0
        self.reset()

    def reset(self) -> None:
        # rng is injected before reset() in headless tests; never overwrite it.
        rng = getattr(self, "rng", None)
        if rng is None:
            rng = random.Random()
        self.rng = rng
        self.best_score = getattr(self, "best_score", 0)
        self.frame = 0
        self.score = 0
        self.streak = 0
        self.tasks_done = 0
        self.phase = Phase.TITLE
        self.task_type = TaskType.COUNT
        self.truth = 0
        self.estimate = 0
        self.confidence = Confidence.SAFE
        self.task_state = TaskState.SHOW
        self.task_clock = 0
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self.dots: list[tuple[int, int]] = []
        self.result_label = ""
        self.result_points = 0

    # -- task lifecycle (no pyxel) --------------------------------------

    def _slider_max(self) -> int:
        return MAX_COUNT if self.task_type is TaskType.COUNT else 100

    def _new_task(self) -> None:
        self.task_state = TaskState.SHOW
        self.task_clock = 0
        self.result_label = ""
        self.result_points = 0
        self.estimate = 0
        if self.tasks_done % 2 == 0:
            self.task_type = TaskType.COUNT
            lo, hi = _count_range(self.frame)
            self.truth = self.rng.randint(lo, hi)
            self.dots = [
                (self.rng.randint(20, 300), self.rng.randint(60, 120))
                for _ in range(self.truth)
            ]
        else:
            self.task_type = TaskType.FRACTION
            self.truth = self.rng.randint(10, 90)
            self.dots = []

    def _resolve_guess(self) -> None:
        points, label = _score_guess(
            self.estimate, self.truth, self.confidence, self.streak
        )
        if points > 0:
            self.streak += 1
            self.score += points
            self.best_score = max(self.best_score, self.score)
        else:
            self.streak = 0
        self.result_label = label
        self.result_points = points
        self.tasks_done += 1
        self.task_state = TaskState.REVEAL
        self.task_clock = 0
        self._spawn_reveal(points)

    def _advance(self) -> None:
        if self.frame >= GAME_DURATION:
            self.phase = Phase.GAME_OVER
        else:
            self._new_task()

    def _spawn_reveal(self, points: int) -> None:
        cx, cy = 160.0, 95.0
        n = 8 if points > 0 else 4
        color = YELLOW if points > 0 else RED
        for _ in range(n):
            angle = self.rng.random() * 2 * math.pi
            speed = self.rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    cx,
                    cy,
                    math.cos(angle) * speed,
                    math.sin(angle) * speed,
                    30,
                    color,
                )
            )
        if points > 0:
            self.floats.append(FloatingText(cx, cy - 12, f"+{points}", 45, YELLOW))
        else:
            self.floats.append(FloatingText(cx, cy - 12, "MISS", 45, RED))

    # -- updates ---------------------------------------------------------

    def update(self) -> None:
        if self.phase is Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
                self.phase = Phase.PLAYING
                self._new_task()
        elif self.phase is Phase.PLAYING:
            self._update_playing()
        elif self.phase is Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()

    def _update_playing(self) -> None:
        self.frame += 1
        self._update_particles()
        if self.task_state is TaskState.SHOW:
            self.task_clock += 1
            if self.task_clock >= _flash_frames(self.frame):
                self.task_state = TaskState.GUESS
                self.task_clock = 0
        elif self.task_state is TaskState.GUESS:
            self.task_clock += 1
            self._handle_guess_input()
            if (
                self.task_state is TaskState.GUESS
                and self.task_clock >= _solve_window(self.frame)
            ):
                self.streak = 0
                self.tasks_done += 1
                self._advance()
        elif self.task_state is TaskState.REVEAL:
            self.task_clock += 1
            if self.task_clock >= REVEAL_FRAMES:
                self._advance()

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]
        for f in self.floats:
            f.y -= 0.5
            f.life -= 1
        self.floats = [f for f in self.floats if f.life > 0]

    def _handle_guess_input(self) -> None:
        # Estimate adjustment via keyboard.
        if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A):
            self.estimate -= 1
        if pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D):
            self.estimate += 1
        self.estimate = max(0, min(self.estimate, self._slider_max()))

        # Confidence toggle.
        if (
            pyxel.btnp(pyxel.KEY_UP)
            or pyxel.btnp(pyxel.KEY_DOWN)
            or pyxel.btnp(pyxel.KEY_W)
            or pyxel.btnp(pyxel.KEY_S)
        ):
            self.confidence = (
                Confidence.RISKY
                if self.confidence is Confidence.SAFE
                else Confidence.SAFE
            )

        # Lock.
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._resolve_guess()
            return

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            if LOCK_BTN_X <= mx <= LOCK_BTN_X + LOCK_BTN_W and LOCK_BTN_Y <= my <= LOCK_BTN_Y + LOCK_BTN_H:
                self._resolve_guess()
                return
            if SAFE_BTN_Y <= my <= SAFE_BTN_Y + BTN_H:
                if SAFE_BTN_X <= mx <= SAFE_BTN_X + SAFE_BTN_W:
                    self.confidence = Confidence.SAFE
                    return
                if RISKY_BTN_X <= mx <= RISKY_BTN_X + RISKY_BTN_W:
                    self.confidence = Confidence.RISKY
                    return
            if SLIDER_Y <= my <= SLIDER_Y + SLIDER_H and SLIDER_X <= mx <= SLIDER_X + SLIDER_W:
                frac = (mx - SLIDER_X) / SLIDER_W
                self.estimate = int(round(frac * self._slider_max()))
                self.estimate = max(0, min(self.estimate, self._slider_max()))

    # -- drawing ---------------------------------------------------------

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase is Phase.TITLE:
            self._draw_title()
        elif self.phase is Phase.PLAYING:
            self._draw_playing()
        elif self.phase is Phase.GAME_OVER:
            self._draw_game_over()

    def _center(self, text: str, y: int, color: int) -> None:
        pyxel.text((WIDTH - len(text) * pyxel.FONT_WIDTH) // 2, y, text, color)

    def _draw_title(self) -> None:
        self._center("EYEBALL", 56, WHITE)
        self._center("Carnival Estimation Arcade", 74, GRAY)
        self._center("Eyeball a flashed quantity.", 108, LIGHT_BLUE)
        self._center("Count the dots or guess the bar %.", 120, LIGHT_BLUE)
        self._center("Bet SAFE (1x) or RISKY (3x).", 132, LIGHT_BLUE)
        self._center("SPACE / CLICK to start", 172, YELLOW)

    def _draw_playing(self) -> None:
        self._draw_timer()
        self._draw_hud()
        self._draw_stimulus()
        self._draw_slider()
        self._draw_buttons()
        self._draw_effects()

    def _draw_timer(self) -> None:
        frac = max(0.0, 1.0 - self.frame / GAME_DURATION)
        fill_w = int(TIMER_W * frac)
        if frac > 0.5:
            color = GREEN
        elif frac > 0.25:
            color = YELLOW
        else:
            color = RED
        pyxel.rect(TIMER_X, TIMER_Y, TIMER_W, TIMER_H, DARK_BLUE)
        pyxel.rect(TIMER_X, TIMER_Y, fill_w, TIMER_H, color)
        pyxel.rectb(TIMER_X, TIMER_Y, TIMER_W, TIMER_H, WHITE)

    def _draw_hud(self) -> None:
        pyxel.text(8, 18, f"SCORE {self.score}", WHITE)
        self._center(f"BEST {self.best_score}", 18, YELLOW)
        streak_text = f"STREAK {self.streak}"
        pyxel.text(WIDTH - 8 - len(streak_text) * pyxel.FONT_WIDTH, 18, streak_text, CYAN)

    def _draw_stimulus(self) -> None:
        if self.task_type is TaskType.COUNT:
            self._center("COUNT THE DOTS", 42, GRAY)
            if self.task_state is TaskState.SHOW:
                for x, y in self.dots:
                    pyxel.circ(x, y, 4, WHITE)
        else:
            self._center("GUESS THE %", 42, GRAY)
            pyxel.rectb(FRACTION_BAR_X, FRACTION_BAR_Y, FRACTION_BAR_W, FRACTION_BAR_H, GRAY)
            if self.task_state is TaskState.SHOW:
                fill_w = int(FRACTION_BAR_W * self.truth / 100)
                pyxel.rect(FRACTION_BAR_X, FRACTION_BAR_Y, fill_w, FRACTION_BAR_H, YELLOW)

    def _draw_slider(self) -> None:
        smax = self._slider_max()
        frac = self.estimate / smax if smax else 0.0
        marker_x = SLIDER_X + int(SLIDER_W * frac)
        pyxel.rect(SLIDER_X, SLIDER_Y, SLIDER_W, SLIDER_H, GRAY)
        pyxel.rect(SLIDER_X, SLIDER_Y, int(SLIDER_W * frac), SLIDER_H, LIGHT_BLUE)
        pyxel.rect(marker_x - 1, SLIDER_Y - 2, 3, SLIDER_H + 4, WHITE)
        pyxel.text(SLIDER_X - 6, SLIDER_Y + 2, "0", GRAY)
        label = f"{smax}"
        pyxel.text(SLIDER_X + SLIDER_W + 2, SLIDER_Y + 2, label, GRAY)

    def _draw_buttons(self) -> None:
        # SAFE button
        safe_fill = GREEN if self.confidence is Confidence.SAFE else GRAY
        pyxel.rect(SAFE_BTN_X, SAFE_BTN_Y, SAFE_BTN_W, BTN_H, safe_fill)
        pyxel.rectb(SAFE_BTN_X, SAFE_BTN_Y, SAFE_BTN_W, BTN_H, WHITE)
        self._center_in("SAFE 1x", SAFE_BTN_X, SAFE_BTN_Y, SAFE_BTN_W, BTN_H, BLACK if self.confidence is Confidence.SAFE else WHITE)

        # RISKY button
        risky_fill = GREEN if self.confidence is Confidence.RISKY else GRAY
        pyxel.rect(RISKY_BTN_X, RISKY_BTN_Y, RISKY_BTN_W, BTN_H, risky_fill)
        pyxel.rectb(RISKY_BTN_X, RISKY_BTN_Y, RISKY_BTN_W, BTN_H, WHITE)
        self._center_in("RISKY 3x", RISKY_BTN_X, RISKY_BTN_Y, RISKY_BTN_W, BTN_H, BLACK if self.confidence is Confidence.RISKY else WHITE)

        # LOCK button
        hover = (
            LOCK_BTN_X <= pyxel.mouse_x <= LOCK_BTN_X + LOCK_BTN_W
            and LOCK_BTN_Y <= pyxel.mouse_y <= LOCK_BTN_Y + LOCK_BTN_H
        )
        pyxel.rect(LOCK_BTN_X, LOCK_BTN_Y, LOCK_BTN_W, LOCK_BTN_H, ORANGE if hover else PURPLE)
        pyxel.rectb(LOCK_BTN_X, LOCK_BTN_Y, LOCK_BTN_W, LOCK_BTN_H, WHITE)
        self._center_in("LOCK (SPACE)", LOCK_BTN_X, LOCK_BTN_Y, LOCK_BTN_W, LOCK_BTN_H, WHITE)

    def _center_in(self, text: str, x: int, y: int, w: int, h: int, color: int) -> None:
        tx = x + (w - len(text) * pyxel.FONT_WIDTH) // 2
        ty = y + (h - pyxel.FONT_HEIGHT) // 2
        pyxel.text(tx, ty, text, color)

    def _draw_effects(self) -> None:
        for p in self.particles:
            pyxel.circ(int(p.x), int(p.y), 2, p.color)
        for f in self.floats:
            pyxel.text(int(f.x - len(f.text) * pyxel.FONT_WIDTH / 2), int(f.y), f.text, f.color)
        if self.task_state is TaskState.REVEAL and self.result_label:
            if self.result_label == "PERFECT!":
                color = YELLOW
            elif self.result_label == "HIT!":
                color = LIME
            else:
                color = RED
            self._center(self.result_label, 66, color)

    def _draw_game_over(self) -> None:
        self._center("TIME UP", 70, RED)
        self._center(f"SCORE: {self.score}", 100, WHITE)
        self._center(f"BEST: {self.best_score}", 112, YELLOW)
        self._center(f"TASKS: {self.tasks_done}", 124, GRAY)
        self._center("SPACE to retry", 160, CYAN)


def run() -> None:
    pyxel.init(WIDTH, HEIGHT, title="EYEBALL", fps=60)
    pyxel.mouse(True)
    game = Game()
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    run()
