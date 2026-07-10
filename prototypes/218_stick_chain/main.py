from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ---------------------------------------------------------------------------
# Color constants
# ---------------------------------------------------------------------------
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

STICK_COLORS: tuple[int, ...] = (RED, LIME, DARK_BLUE, YELLOW)

# Screen
SCREEN_W = 320
SCREEN_H = 240
UI_HEIGHT = 20

# Gameplay
CLICK_TOLERANCE = 8.0
HEAT_MAX = 100.0
HEAT_MISMATCH = 15.0
HEAT_OVERLAP_FACTOR = 5.0
HEAT_DECAY = 0.02
COMBO_SUPER_THRESHOLD = 4
SUPER_DURATION = 300
GAME_TIMER_FRAMES = 3600
INITIAL_STICKS = 18
STICKS_PER_ROUND = 3
STICK_MIN_LEN = 40
STICK_MAX_LEN = 70
ROUND_CLEAR_FRAMES = 60


# ---------------------------------------------------------------------------
# Phase enum
# ---------------------------------------------------------------------------
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class Stick:
    x1: float
    y1: float
    x2: float
    y2: float
    color: int
    overlap_count: int = 0
    picked: bool = False


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


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    phase: Phase
    sticks: list[Stick]
    score: int
    combo: int
    max_combo: int
    heat: float
    super_timer: int
    game_timer: int
    round_num: int
    last_color: int
    particles: list[Particle]
    floating_texts: list[FloatingText]
    shake_frames: int
    round_clear_timer: int
    _rng: random.Random

    def __new__(cls) -> Game:
        instance = super().__new__(cls)
        instance.phase = Phase.TITLE
        instance.sticks = []
        instance.score = 0
        instance.combo = 0
        instance.max_combo = 0
        instance.heat = 0.0
        instance.super_timer = 0
        instance.game_timer = GAME_TIMER_FRAMES
        instance.round_num = 0
        instance.last_color = -1
        instance.particles = []
        instance.floating_texts = []
        instance.shake_frames = 0
        instance.round_clear_timer = 0
        instance._rng = random.Random()
        return instance

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="STICK CHAIN", fps=60)
        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    # -----------------------------------------------------------------------
    # State initialization
    # -----------------------------------------------------------------------
    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.sticks = []
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_timer = 0
        self.game_timer = GAME_TIMER_FRAMES
        self.round_num = 0
        self.last_color = -1
        self.particles = []
        self.floating_texts = []
        self.shake_frames = 0
        self.round_clear_timer = 0

    # -----------------------------------------------------------------------
    # Core Logic: Stick generation & overlap
    # -----------------------------------------------------------------------
    def _generate_sticks(self, n: int) -> list[Stick]:
        sticks: list[Stick] = []
        for _ in range(n):
            length = self._rng.randint(STICK_MIN_LEN, STICK_MAX_LEN)
            margin = length // 2 + 5
            cx = self._rng.uniform(margin, SCREEN_W - margin)
            cy = self._rng.uniform(UI_HEIGHT + margin, SCREEN_H - margin)
            angle = self._rng.uniform(0, math.pi)
            dx = math.cos(angle) * length / 2
            dy = math.sin(angle) * length / 2
            color = self._rng.choice(STICK_COLORS)
            sticks.append(Stick(x1=cx - dx, y1=cy - dy, x2=cx + dx, y2=cy + dy, color=color))
        return sticks

    def _compute_overlaps(self, sticks: list[Stick]) -> None:
        for s in sticks:
            s.overlap_count = 0
        for i in range(len(sticks)):
            for j in range(i + 1, len(sticks)):
                if self._segments_intersect(sticks[i], sticks[j]):
                    sticks[i].overlap_count += 1
                    sticks[j].overlap_count += 1

    @staticmethod
    def _orientation(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> float:
        return (by - ay) * (cx - bx) - (bx - ax) * (cy - by)

    def _segments_intersect(self, s1: Stick, s2: Stick) -> bool:
        o1 = self._orientation(s1.x1, s1.y1, s1.x2, s1.y2, s2.x1, s2.y1)
        o2 = self._orientation(s1.x1, s1.y1, s1.x2, s1.y2, s2.x2, s2.y2)
        o3 = self._orientation(s2.x1, s2.y1, s2.x2, s2.y2, s1.x1, s1.y1)
        o4 = self._orientation(s2.x1, s2.y1, s2.x2, s2.y2, s1.x2, s1.y2)

        if o1 * o2 < 0 and o3 * o4 < 0:
            return True

        eps = 1e-6
        if abs(o1) < eps and self._point_on_segment(s2.x1, s2.y1, s1.x1, s1.y1, s1.x2, s1.y2):
            return True
        if abs(o2) < eps and self._point_on_segment(s2.x2, s2.y2, s1.x1, s1.y1, s1.x2, s1.y2):
            return True
        if abs(o3) < eps and self._point_on_segment(s1.x1, s1.y1, s2.x1, s2.y1, s2.x2, s2.y2):
            return True
        if abs(o4) < eps and self._point_on_segment(s1.x2, s1.y2, s2.x1, s2.y1, s2.x2, s2.y2):
            return True

        return False

    @staticmethod
    def _point_on_segment(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> bool:
        eps = 1e-6
        return bool(
            min(x1, x2) - eps <= px <= max(x1, x2) + eps
            and min(y1, y2) - eps <= py <= max(y1, y2) + eps
        )

    @staticmethod
    def _point_to_segment_dist(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(px - x1, py - y1)
        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return math.hypot(px - proj_x, py - proj_y)

    def _find_clicked_stick(self, mx: int, my: int) -> int | None:
        best_idx: int | None = None
        best_dist = float("inf")
        for i, s in enumerate(self.sticks):
            if s.picked:
                continue
            d = self._point_to_segment_dist(float(mx), float(my), s.x1, s.y1, s.x2, s.y2)
            if d <= CLICK_TOLERANCE and d < best_dist:
                best_dist = d
                best_idx = i
        return best_idx

    # -----------------------------------------------------------------------
    # Core Logic: Picking sticks
    # -----------------------------------------------------------------------
    def _pick_stick(self, idx: int) -> int:
        stick = self.sticks[idx]
        stick.picked = True

        # Heat from overlap
        self.heat += stick.overlap_count * HEAT_OVERLAP_FACTOR

        # Check match (last_color==-1 means first pick, always matches)
        is_match = self.super_timer > 0 or self.last_color == -1 or stick.color == self.last_color

        gained = 0
        if is_match:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            multiplier = 3 if self.super_timer > 0 else 1
            gained = 10 * self.combo * multiplier
            self.score += gained

            # Trigger SUPER PICK at combo >= 4, but only if not already active
            if self.combo >= COMBO_SUPER_THRESHOLD and self.super_timer <= 0:
                self.super_timer = SUPER_DURATION
                mx = (stick.x1 + stick.x2) / 2
                my = (stick.y1 + stick.y2) / 2
                self.floating_texts.append(FloatingText(mx, my - 15, "SUPER!", 60, YELLOW))
        else:
            self.combo = 0
            self.heat += HEAT_MISMATCH

        self.last_color = stick.color

        if self.heat >= HEAT_MAX:
            self.heat = HEAT_MAX
            self.phase = Phase.GAME_OVER

        # Spawn particles
        mx = (stick.x1 + stick.x2) / 2
        my = (stick.y1 + stick.y2) / 2
        for _ in range(8):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(Particle(
                mx, my,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                self._rng.randint(10, 20),
                stick.color,
            ))

        # Floating score text
        if gained > 0:
            self.floating_texts.append(FloatingText(
                mx + self._rng.randint(-10, 10),
                my - self._rng.randint(5, 15),
                f"+{gained}", 30, WHITE,
            ))

        # Screen shake at heat thresholds
        if self.heat >= 75 and self.shake_frames < 20:
            self.shake_frames = 20
        elif self.heat >= 50 and self.shake_frames < 15:
            self.shake_frames = 15
        elif self.heat >= 25 and self.shake_frames < 10:
            self.shake_frames = 10

        return gained

    def _start_new_round(self) -> None:
        self.round_num += 1
        n_sticks = INITIAL_STICKS + (self.round_num - 1) * STICKS_PER_ROUND
        self.sticks = self._generate_sticks(n_sticks)
        self._compute_overlaps(self.sticks)
        self.last_color = -1
        self.round_clear_timer = 0

    def _update_heat(self) -> None:
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    # -----------------------------------------------------------------------
    # Particles & floating texts
    # -----------------------------------------------------------------------
    def _update_particles(self) -> None:
        surviving: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                surviving.append(p)
        self.particles = surviving

    def _update_floating_texts(self) -> None:
        surviving: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= 1
            ft.life -= 1
            if ft.life > 0:
                surviving.append(ft)
        self.floating_texts = surviving

    # -----------------------------------------------------------------------
    # Pyxel update
    # -----------------------------------------------------------------------
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if (
                pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            ):
                self.reset()
                self.phase = Phase.PLAYING
                self._start_new_round()
            return

        if self.phase == Phase.GAME_OVER:
            if (
                pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            ):
                self.reset()
                self.phase = Phase.TITLE
            return

        # PLAYING phase
        self._update_heat()

        if self.shake_frames > 0:
            self.shake_frames -= 1

        if self.round_clear_timer > 0:
            self.round_clear_timer -= 1
            if self.super_timer > 0:
                self.super_timer -= 1
            self._update_particles()
            self._update_floating_texts()
            if self.round_clear_timer <= 0:
                self._start_new_round()
            return

        self._update_particles()
        self._update_floating_texts()

        # Timer
        self.game_timer -= 1
        if self.game_timer <= 0:
            self.game_timer = 0
            self.phase = Phase.GAME_OVER
            return

        # SUPER timer
        if self.super_timer > 0:
            self.super_timer -= 1

        # Click to pick
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            idx = self._find_clicked_stick(mx, my)
            if idx is not None:
                self._pick_stick(idx)
                if all(s.picked for s in self.sticks):
                    self.round_clear_timer = ROUND_CLEAR_FRAMES

        # Heat game over check (also checked in _pick_stick)
        if self.heat >= HEAT_MAX:
            self.heat = HEAT_MAX
            self.phase = Phase.GAME_OVER

    # -----------------------------------------------------------------------
    # Pyxel draw
    # -----------------------------------------------------------------------
    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.cls(BROWN)
        pyxel.text(SCREEN_W // 2 - 36, 50, "STICK CHAIN", YELLOW)
        pyxel.text(SCREEN_W // 2 - 60, 80, "Click sticks to pick them up!", WHITE)
        pyxel.text(SCREEN_W // 2 - 68, 95, "Same color = COMBO +Score", LIME)
        pyxel.text(SCREEN_W // 2 - 68, 108, "Different color = COMBO reset +HEAT", RED)
        pyxel.text(SCREEN_W // 2 - 72, 121, "COMBO x4 = SUPER PICK (rainbow, 3x)", YELLOW)
        pyxel.text(SCREEN_W // 2 - 60, 134, "Overlapping sticks = +HEAT", ORANGE)
        pyxel.text(SCREEN_W // 2 - 54, 147, "HEAT 100 or 60s = GAME OVER", PINK)

        pyxel.text(SCREEN_W // 2 - 56, 175, "Left Click to pick", WHITE)
        pyxel.text(SCREEN_W // 2 - 42, 188, "Clear all sticks to advance round!", LIGHT_BLUE)

        if pyxel.frame_count % 60 < 30:
            pyxel.text(SCREEN_W // 2 - 60, 215, "CLICK TO START", YELLOW)

    def _draw_game_over(self) -> None:
        pyxel.cls(BLACK)
        pyxel.text(SCREEN_W // 2 - 32, 55, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 42, 80, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 52, 95, f"MAX COMBO: {self.max_combo}", YELLOW)
        pyxel.text(SCREEN_W // 2 - 38, 110, f"ROUND: {self.round_num}", LIME)
        cause = "HEAT" if self.heat >= HEAT_MAX else "TIME"
        pyxel.text(SCREEN_W // 2 - 54, 125, f"FAILED BY: {cause}", ORANGE)

        if pyxel.frame_count % 60 < 30:
            pyxel.text(SCREEN_W // 2 - 60, 200, "CLICK TO RETRY", YELLOW)

    def _draw_playing(self) -> None:
        # Tabletop
        pyxel.cls(BROWN)

        # Screen shake
        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0:
            shake_x = self._rng.randint(-4, 4)
            shake_y = self._rng.randint(-4, 4)

        # Draw sticks
        for s in self.sticks:
            if s.picked:
                continue
            x1 = int(s.x1) + shake_x
            y1 = int(s.y1) + shake_y
            x2 = int(s.x2) + shake_x
            y2 = int(s.y2) + shake_y

            color = s.color
            if self.super_timer > 0:
                color = self._rainbow_color()

            # Overlap glow
            if s.overlap_count > 0:
                gc = ORANGE if s.overlap_count >= 3 else GRAY if s.overlap_count >= 2 else NAVY
                pyxel.line(x1 - 1, y1, x2 - 1, y2, gc)
                pyxel.line(x1 + 1, y1, x2 + 1, y2, gc)
                pyxel.line(x1, y1 - 1, x2, y2 - 1, gc)
                pyxel.line(x1, y1 + 1, x2, y2 + 1, gc)

            pyxel.line(x1, y1, x2, y2, color)

        # Particles
        for p in self.particles:
            if p.life > 0:
                px = int(p.x) + shake_x
                py = int(p.y) + shake_y
                pyxel.circ(px, py, 1, p.color)

        # Floating texts
        for ft in self.floating_texts:
            if ft.life > 0:
                ftx = int(ft.x) + shake_x
                fty = int(ft.y) + shake_y
                pyxel.text(ftx, fty, ft.text, ft.color)

        # SUPER rainbow border
        if self.super_timer > 0:
            self._draw_super_border()

        # UI bar
        self._draw_ui_bar()

        # Round clear text
        if self.round_clear_timer > 0:
            pyxel.text(SCREEN_W // 2 - 40, SCREEN_H // 2 - 4, "ROUND CLEAR!", YELLOW)

    def _draw_ui_bar(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, UI_HEIGHT, BLACK)

        # Score
        pyxel.text(4, 4, f"SCORE:{self.score}", WHITE)

        # Combo
        cc = YELLOW if self.combo < COMBO_SUPER_THRESHOLD else RED
        if self.super_timer > 0:
            cc = LIME
        pyxel.text(90, 4, f"COMBO:{self.combo}", cc)

        # SUPER indicator
        if self.super_timer > 0:
            sec = self.super_timer // 60 + 1
            sc = self._rainbow_color()
            pyxel.text(170, 4, f"SUPER{sec}s", sc)

        # Heat bar
        hx = 230
        hy = 4
        hw = 50
        hh = 8
        pyxel.rect(hx, hy, hw, hh, GRAY)
        fill_w = int((self.heat / HEAT_MAX) * (hw - 2))
        hc = GREEN if self.heat < 50 else ORANGE if self.heat < 75 else RED
        if fill_w > 0:
            pyxel.rect(hx + 1, hy + 1, fill_w, hh - 2, hc)
        pyxel.rectb(hx, hy, hw, hh, WHITE)
        pyxel.text(hx - 8, 4, "H", RED)

        # Timer
        sec = max(0, self.game_timer // 60)
        ts = f"{sec}s"
        tc = LIME if sec > 20 else ORANGE if sec > 10 else RED
        pyxel.text(286, 4, ts, tc)

    def _draw_super_border(self) -> None:
        rainbow_offset = pyxel.frame_count // 4
        colors: list[int] = [RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, DARK_BLUE, PURPLE, PINK]
        for i in range(4):
            idx = (rainbow_offset + i) % len(colors)
            pyxel.rectb(i, i, SCREEN_W - i * 2, SCREEN_H - i * 2, colors[idx])

    def _rainbow_color(self) -> int:
        colors: list[int] = [RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, DARK_BLUE, PURPLE, PINK]
        return colors[(self.super_timer // 6) % len(colors)]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    Game()
