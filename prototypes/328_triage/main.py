"""TRIAGE: ER Shift — hidden-severity triage prototype.

You are an ER triage nurse on a 60-second shift. Patients keep arriving in a
6-slot waiting room. Each has a HIDDEN true severity (minor / moderate /
critical) and a VISIBLE noisy "symptom pips" readout (1-4 pips) that
CORRELATES with severity but never reveals it. You have ONE treatment slot:
click a patient to start treating; treatment freezes their crash timer for a
fixed duration, then reveals their true severity and awards score. Every
untreated patient's crash timer drains; when it hits zero they crash and cost
you reputation (a critical crash is catastrophic). Read the noisy signal,
gamble on the ambiguous patients, and save the criticals before they crash.
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

# --- Waiting room layout ---
SLOTS = 6
COLS = 3
ROWS = 2
COL_X = [16, 116, 216]
ROW_Y = [64, 140]
COL_SPACING = 100
ROW_SPACING = 76
CARD_W = 88
CARD_H = 64

# --- Gameplay constants ---
START_REP = 100
TREAT_TIME = 40
REVEAL_FRAMES = 25
CRASH_FRAMES = 30
JUST_IN_TIME = 90
CRASH_WARN = 150
CRASH_BAR_MAX = 1500.0  # reference for crash-bar fraction/color

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

# Per-severity reputation penalty on crash.
CRASH_PENALTY = {1: -4, 2: -12, 3: -25}
CRASH_TEXT = {1: "CRASH", 2: "CRASH", 3: "CODE BLUE"}
SEVERITY_LABEL = {1: "MINOR", 2: "MODERATE", 3: "CRITICAL"}


class Phase(Enum):
    TITLE = "title"
    PLAYING = "playing"
    GAME_OVER = "game_over"


class Severity(Enum):
    MINOR = 1
    MODERATE = 2
    CRITICAL = 3


class PatientState(Enum):
    WAITING = 0
    TREATING = 1
    TREATED = 2
    CRASHED = 3


@dataclass
class Patient:
    severity: Severity  # hidden true severity
    pips: int  # 1..4 noisy visible signal
    crash_timer: int  # frames until crash if untreated
    state: PatientState = PatientState.WAITING
    flash: int = 0  # remaining reveal/crash flash frames


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
    if seed is not None:
        game.rng = random.Random(seed)
    game.reset()
    return game


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, "TRIAGE: ER Shift", fps=FPS, display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    def reset(self, seed: int | None = None) -> None:
        if seed is not None:
            self.rng = random.Random(seed)
        elif not hasattr(self, "rng"):
            self.rng = random.Random()
        self.best_score = getattr(self, "best_score", 0)
        self.phase = Phase.TITLE
        self.slots: list[Patient | None] = [None] * SLOTS
        self.treating_slot: int | None = None
        self.treat_timer = 0
        self.score = 0
        self.rep = START_REP
        self.frame = 0
        self.spawn_timer = self._spawn_interval()
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self.shake = 0
        self.saved_count = 0
        self.crashed_count = 0
        self.game_over_reason = ""

    def _start_run(self) -> None:
        self.phase = Phase.PLAYING

    # ------------------------------------------------------------------
    # Pure logic (no pyxel input)
    # ------------------------------------------------------------------
    @staticmethod
    def _clamp(value: int, lo: int, hi: int) -> int:
        return max(lo, min(hi, value))

    def _make_patient(self, severity: Severity, rng: random.Random) -> Patient:
        pips = self._clamp(severity.value + rng.choice([-1, 0, 1]), 1, 4)
        base = {
            Severity.MINOR: rng.randint(900, 1500),
            Severity.MODERATE: rng.randint(500, 800),
            Severity.CRITICAL: rng.randint(240, 420),
        }[severity]
        crash_timer = int(base * self._timer_scale())
        return Patient(severity=severity, pips=pips, crash_timer=crash_timer)

    def _timer_scale(self) -> float:
        return 1.0 - 0.3 * (self.frame / GAME_DURATION)

    def _spawn_interval(self) -> int:
        return max(30, 90 - self.frame // 60)

    def _severity_weights(self) -> tuple[float, float, float]:
        minor = 5 - self.frame // 1200
        moderate = 3.0
        critical = 2 + self.frame // 900
        return (float(minor), moderate, float(critical))

    def _spawn_patient(self) -> None:
        empty = [i for i in range(SLOTS) if self.slots[i] is None]
        if not empty:
            return
        idx = self.rng.choice(empty)
        severity = self.rng.choices(
            [Severity.MINOR, Severity.MODERATE, Severity.CRITICAL],
            weights=self._severity_weights(),
            k=1,
        )[0]
        self.slots[idx] = self._make_patient(severity, self.rng)

    def _start_treatment(self, idx: int) -> bool:
        if self.treating_slot is not None:
            return False
        if not 0 <= idx < SLOTS:
            return False
        p = self.slots[idx]
        if p is None or p.state is not PatientState.WAITING:
            return False
        p.state = PatientState.TREATING
        self.treating_slot = idx
        self.treat_timer = TREAT_TIME
        return True

    def _update_treatment(self) -> None:
        if self.treating_slot is None:
            return
        self.treat_timer -= 1
        if self.treat_timer <= 0:
            self._resolve_treatment()

    def _card_center(self, idx: int) -> tuple[int, int]:
        col = idx % COLS
        row = idx // COLS
        return COL_X[col] + CARD_W // 2, ROW_Y[row] + CARD_H // 2

    @staticmethod
    def _reveal_color(severity: Severity) -> int:
        return {Severity.MINOR: LIME, Severity.MODERATE: YELLOW, Severity.CRITICAL: RED}[
            severity
        ]

    @staticmethod
    def _crash_color(severity: Severity) -> int:
        return {Severity.MINOR: GRAY, Severity.MODERATE: ORANGE, Severity.CRITICAL: RED}[
            severity
        ]

    def _resolve_treatment(self) -> None:
        idx = self.treating_slot
        if idx is None:
            return
        p = self.slots[idx]
        if p is None:
            self.treating_slot = None
            self.treat_timer = 0
            return
        p.state = PatientState.TREATED
        p.flash = REVEAL_FRAMES
        gain = p.severity.value * 100
        if p.severity is Severity.CRITICAL:
            self.rep = min(START_REP, self.rep + 5)
        just_in_time = False
        if p.crash_timer < JUST_IN_TIME:
            gain += 100
            just_in_time = True
        self.score += gain
        self.saved_count += 1
        cx, cy = self._card_center(idx)
        self._spawn_burst(cx, cy, self._reveal_color(p.severity), 6 + p.severity.value * 4)
        if just_in_time:
            self.floats.append(FloatingText(cx, cy - 20, "JUST IN TIME +100", 60, LIME))
        self.floats.append(FloatingText(cx, cy - 8, f"+{gain}", 60, self._reveal_color(p.severity)))
        self.treating_slot = None
        self.treat_timer = 0

    def _update_patients(self) -> None:
        for idx in range(SLOTS):
            p = self.slots[idx]
            if p is None or p.state is not PatientState.WAITING:
                continue
            p.crash_timer -= 1
            if p.crash_timer <= 0:
                p.state = PatientState.CRASHED
                p.flash = CRASH_FRAMES
                self.rep = max(0, self.rep + CRASH_PENALTY[p.severity.value])
                self.crashed_count += 1
                self.shake = 10 if p.severity is Severity.CRITICAL else max(self.shake, 5)
                cx, cy = self._card_center(idx)
                self._spawn_burst(cx, cy, self._crash_color(p.severity), 8)
                self.floats.append(FloatingText(cx, cy - 8, "CRASH!", 60, RED))

    def _cleanup_flashes(self) -> None:
        for idx in range(SLOTS):
            p = self.slots[idx]
            if p is None:
                continue
            if p.state in (PatientState.TREATED, PatientState.CRASHED):
                p.flash -= 1
                if p.flash <= 0:
                    self.slots[idx] = None

    def _tick(self) -> None:
        self.frame += 1
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self._spawn_patient()
            self.spawn_timer = self._spawn_interval()
        self._update_treatment()
        self._update_patients()
        self._cleanup_flashes()
        self._check_game_over()

    def _check_game_over(self) -> None:
        if self.rep <= 0:
            self.rep = 0
            self.game_over_reason = "MALPRACTICE"
            self.phase = Phase.GAME_OVER
            self.best_score = max(self.best_score, self.score)
        elif self.frame >= GAME_DURATION:
            self.game_over_reason = "SHIFT OVER"
            self.phase = Phase.GAME_OVER
            self.best_score = max(self.best_score, self.score)

    def _update_fx(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]
        for t in self.floats:
            t.y -= 0.5
            t.life -= 1
        self.floats = [t for t in self.floats if t.life > 0]
        if self.shake > 0:
            self.shake -= 1

    def _spawn_burst(self, x: float, y: float, color: int, n: int) -> None:
        for _ in range(n):
            ang = self.rng.uniform(0.0, math.tau)
            spd = self.rng.uniform(0.5, 2.0)
            self.particles.append(
                Particle(
                    x,
                    y,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    self.rng.randint(15, 35),
                    color,
                )
            )

    def _slot_at(self, mx: int, my: int) -> int | None:
        col = (mx - COL_X[0]) // COL_SPACING
        row = (my - ROW_Y[0]) // ROW_SPACING
        if not (0 <= col < COLS and 0 <= row < ROWS):
            return None
        x = COL_X[col]
        y = ROW_Y[row]
        if not (x <= mx <= x + CARD_W and y <= my <= y + CARD_H):
            return None
        return row * COLS + col

    # ------------------------------------------------------------------
    # Input (thin wrappers — the ONLY place pyxel input is read)
    # ------------------------------------------------------------------
    def update(self) -> None:
        if self.phase is Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self._start_run()
        elif self.phase is Phase.PLAYING:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                idx = self._slot_at(pyxel.mouse_x, pyxel.mouse_y)
                if idx is not None:
                    self._start_treatment(idx)
            self._tick()
            self._update_fx()
        elif self.phase is Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
                self._start_run()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(self) -> None:
        pyxel.cls(DARK_BLUE)
        if self.phase is Phase.TITLE:
            self._draw_title()
        elif self.phase is Phase.PLAYING:
            self._draw_play()
        elif self.phase is Phase.GAME_OVER:
            self._draw_game_over()

    @staticmethod
    def _center(text: str) -> int:
        return (SCREEN_W - len(text) * 4) // 2

    def _draw_title(self) -> None:
        pyxel.text(self._center("TRIAGE: ER SHIFT"), 70, "TRIAGE: ER SHIFT", YELLOW)
        pyxel.text(
            self._center("Save the criticals. Read the signs."),
            88,
            "Save the criticals. Read the signs.",
            GRAY,
        )
        pyxel.text(self._center("CLICK a patient to treat"), 130, "CLICK a patient to treat", WHITE)
        pyxel.text(self._center("ENTER to start"), 142, "ENTER to start", WHITE)
        pyxel.text(
            self._center("1-4 pips hint severity. Save the RED."),
            172,
            "1-4 pips hint severity. Save the RED.",
            LIME,
        )

    def _rep_color(self) -> int:
        if self.rep > 60:
            return LIME
        if self.rep > 30:
            return YELLOW
        if self.rep > 15:
            return ORANGE
        return RED

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE {self.score}", WHITE)
        pyxel.text(4, 14, f"SAVED {self.saved_count}", LIME)
        pyxel.text(4, 24, f"CRASHED {self.crashed_count}", ORANGE)

        # Reputation bar (top center).
        pyxel.text(self._center("REP"), 4, "REP", GRAY)
        pyxel.rect(110, 4, 100, 6, GRAY)
        pyxel.rect(110, 4, self.rep, 6, self._rep_color())

        # Timer bar (top right).
        remain = max(0, GAME_DURATION - self.frame)
        pyxel.text(280, 4, f"{remain // 60}s", WHITE)
        pyxel.rect(4, 34, 300, 4, GRAY)
        bar_w = int(300 * remain / GAME_DURATION)
        pyxel.rect(4, 34, bar_w, 4, CYAN)

    def _crash_bar_color(self, frac: float) -> int:
        if frac > 0.5:
            return LIME
        if frac > 0.25:
            return YELLOW
        if frac > 0.1:
            return ORANGE
        return RED

    def _draw_card(self, idx: int) -> None:
        p = self.slots[idx]
        col = idx % COLS
        row = idx // COLS
        x = COL_X[col]
        y = ROW_Y[row]

        if p is None:
            pyxel.rect(x, y, CARD_W, CARD_H, GRAY)
            pyxel.rectb(x, y, CARD_W, CARD_H, NAVY)
            return

        if p.state is PatientState.TREATED:
            fill = self._reveal_color(p.severity)
            border = WHITE
        elif p.state is PatientState.CRASHED:
            fill = RED
            border = WHITE
        elif p.state is PatientState.TREATING:
            fill = GRAY
            border = LIGHT_BLUE
        else:
            fill = GRAY
            border = WHITE

        pyxel.rect(x, y, CARD_W, CARD_H, fill)
        pyxel.rectb(x, y, CARD_W, CARD_H, border)

        if p.state in (PatientState.WAITING, PatientState.TREATING):
            for i in range(p.pips):
                pyxel.rect(x + 4 + i * 6, y + 4, 4, 4, YELLOW)
            if p.state is PatientState.WAITING and p.crash_timer < CRASH_WARN:
                if (pyxel.frame_count // 15) % 2 == 0:
                    pyxel.text(x + CARD_W - 10, y + 4, "!", RED)

        if p.state is PatientState.TREATING:
            prog = max(0.0, self.treat_timer / TREAT_TIME)
            pw = int((CARD_W - 8) * prog)
            pyxel.rect(x + 4, y + CARD_H - 8, CARD_W - 8, 4, NAVY)
            pyxel.rect(x + 4, y + CARD_H - 8, pw, 4, LIGHT_BLUE)
        elif p.state is PatientState.WAITING:
            frac = max(0.0, min(1.0, p.crash_timer / CRASH_BAR_MAX))
            bar_w = int((CARD_W - 8) * frac)
            pyxel.rect(x + 4, y + CARD_H - 8, CARD_W - 8, 4, NAVY)
            pyxel.rect(x + 4, y + CARD_H - 8, bar_w, 4, self._crash_bar_color(frac))

        if p.state is PatientState.TREATED:
            pyxel.text(x + 8, y + CARD_H // 2 - 4, SEVERITY_LABEL[p.severity.value], WHITE)
        elif p.state is PatientState.CRASHED:
            pyxel.text(x + 8, y + CARD_H // 2 - 4, CRASH_TEXT[p.severity.value], WHITE)

    def _draw_play(self) -> None:
        self._draw_hud()
        ox, oy = self._shake_offset()
        pyxel.camera(ox, oy)
        for idx in range(SLOTS):
            self._draw_card(idx)
        self._draw_fx()
        pyxel.camera(0, 0)

    def _shake_offset(self) -> tuple[int, int]:
        if self.shake <= 0:
            return 0, 0
        ox = (self.shake * 7 + self.frame) % 5 - 2
        oy = (self.shake * 11 + self.frame) % 3 - 1
        return ox, oy

    def _draw_fx(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)
        for t in self.floats:
            pyxel.text(int(t.x) - len(t.text) * 2, int(t.y), t.text, t.color)

    def _draw_game_over(self) -> None:
        pyxel.text(self._center("GAME OVER"), 88, "GAME OVER", RED)
        pyxel.text(self._center(self.game_over_reason), 104, self.game_over_reason, YELLOW)
        pyxel.text(self._center(f"SCORE {self.score}"), 116, f"SCORE {self.score}", WHITE)
        pyxel.text(self._center(f"BEST {self.best_score}"), 128, f"BEST {self.best_score}", GRAY)
        pyxel.text(
            self._center(f"SAVED {self.saved_count}  CRASHED {self.crashed_count}"),
            140,
            f"SAVED {self.saved_count}  CRASHED {self.crashed_count}",
            GRAY,
        )
        pyxel.text(self._center("ENTER to retry"), 168, "ENTER to retry", WHITE)


if __name__ == "__main__":
    Game()
