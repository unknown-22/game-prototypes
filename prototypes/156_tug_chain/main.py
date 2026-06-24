"""
Tug Chain — Tug of War Color-Match Prototype
=============================================
体験仮説: 同じ色でリズムよく引き続けると気持ちよく、判断ミスで連鎖崩壊するヒリつきが面白い
"""

from __future__ import annotations

import math
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
DISPLAY_SCALE = 2

SEGMENT_W = 28
SEGMENTS = 10
ROPE_Y = 140
COMBO_THRESHOLD = 4
SUPER_DURATION = 150  # frames (5 seconds at 30fps)
MAX_HEAT = 100
FRAY_SPREAD_CHANCE = 0.4
HEAT_PER_MISS = 20
GAME_DURATION = 1800  # 60s * 30fps = 1800 frames

# Pyxel color constants
C_BLACK = 0
C_NAVY = 1
C_GREEN = 3
C_BROWN = 4
C_LIGHT_BLUE = 6
C_WHITE = 7
C_RED = 8
C_ORANGE = 9
C_YELLOW = 10
C_GRAY = 13
C_PINK = 14

COLOR_ORDER = (C_RED, C_GREEN, C_YELLOW, C_LIGHT_BLUE)
COLOR_NAMES: dict[int, str] = {
    C_RED: "RED",
    C_GREEN: "GREEN",
    C_YELLOW: "YELLOW",
    C_LIGHT_BLUE: "BLUE",
}

# ---------------------------------------------------------------------------
# Phase
# ---------------------------------------------------------------------------
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------
@dataclass
class RopeSegment:
    color: int
    frayed: bool = False
    x: float = 0.0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    max_life: int
    color: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    max_life: int
    color: int


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Tug Chain", fps=FPS,
                   display_scale=DISPLAY_SCALE)
        font_path = str(Path(__file__).with_name("k8x12.bdf"))
        pyxel.load(font_path, False, False, False, False)
        pyxel.mouse(True)

        self._rng: random.Random = random.Random()
        self._init_state()
        pyxel.run(self._update, self._draw)

    # ------------------------------------------------------------------
    # State initialization (shared by __init__ and headless testing)
    # ------------------------------------------------------------------
    def _init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.segments: list[RopeSegment] = []
        self.active_color: int = C_RED
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.pull_distance: float = 0.0
        self.super_timer: int = 0
        self.game_timer: int = GAME_DURATION
        self.heat: float = 0.0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shake_frames: int = 0
        self._pull_cooldown: int = 0
        self._color_idx: int = 0

    def reset(self) -> None:
        """Re-initialize for a new game (from PLAYING or GAME_OVER)."""
        self._init_state()
        self._build_segments()
        self.phase = Phase.PLAYING

    def _build_segments(self) -> None:
        """Create rope segments with random colors."""
        self.segments.clear()
        total_w = SEGMENTS * SEGMENT_W
        start_x = (SCREEN_W - total_w) / 2
        for i in range(SEGMENTS):
            col = self._rng.choice(COLOR_ORDER)
            self.segments.append(RopeSegment(
                color=col,
                frayed=False,
                x=start_x + i * SEGMENT_W + SEGMENT_W / 2,
            ))

    def _cycle_color(self) -> int:
        """Advance active color to next in order; returns new color."""
        self._color_idx = (self._color_idx + 1) % len(COLOR_ORDER)
        self.active_color = COLOR_ORDER[self._color_idx]
        return self.active_color

    # ------------------------------------------------------------------
    # Headless-testable pure-logic methods
    # ------------------------------------------------------------------

    def _center_segment(self) -> RopeSegment:
        """Return the center segment (the one clicked on)."""
        return self.segments[SEGMENTS // 2]

    def _resolve_pull(self, matched: bool) -> tuple[int, int, bool]:
        """Resolve one pull action.
        Returns: (score_add, combo_change, fray_triggered)
        """
        fray_triggered = False
        score_add = 0
        combo_change = 0

        if matched:
            self.combo += 1
            combo_change = 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            mult = 3 if self._is_super() else 1
            base_pts = 10 + self.combo * 5
            score_add = base_pts * mult
            self.score += score_add
            self.pull_distance += 2.0 + self.combo * 0.5

            # Check for super activation
            if self.combo >= COMBO_THRESHOLD and not self._is_super():
                self._activate_super()
        else:
            self.combo = 0
            combo_change = -999  # reset sentinel
            self.heat = min(MAX_HEAT, self.heat + HEAT_PER_MISS)
            self.super_timer = 0

            # Fray a random non-frayed segment
            non_frayed = [s for s in self.segments if not s.frayed]
            if non_frayed:
                seg = self._rng.choice(non_frayed)
                seg.frayed = True
                fray_triggered = True
            self.shake_frames = 10

        return score_add, combo_change, fray_triggered

    def _is_super(self) -> bool:
        return self.super_timer > 0

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION

    def _spread_fray(self) -> list[int]:
        """CA fray spread. Returns list of newly frayed indices."""
        newly_frayed: list[int] = []
        for i in range(len(self.segments)):
            if not self.segments[i].frayed:
                continue
            if self._rng.random() < FRAY_SPREAD_CHANCE:
                if i > 0 and not self.segments[i - 1].frayed:
                    self.segments[i - 1].frayed = True
                    newly_frayed.append(i - 1)
                if i < SEGMENTS - 1 and not self.segments[i + 1].frayed:
                    self.segments[i + 1].frayed = True
                    newly_frayed.append(i + 1)
        return newly_frayed

    def _check_game_over(self) -> bool:
        """Return True if rope is fully frayed or timer expired."""
        if self.game_timer <= 0:
            return True
        if all(s.frayed for s in self.segments):
            return True
        return False

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1  # gravity
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def _update_floating_texts(self) -> None:
        alive: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= 1.0
            ft.life -= 1
            if ft.life > 0:
                alive.append(ft)
        self.floating_texts = alive

    # ------------------------------------------------------------------
    # Particles / Visual effects helpers
    # ------------------------------------------------------------------
    def _spawn_pull_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(12):
            angle = self._rng.uniform(0, math.tau)
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 2,
                life=20, max_life=20, color=color,
            ))

    def _spawn_fray_particles(self, x: float, y: float) -> None:
        for _ in range(8):
            angle = self._rng.uniform(0, math.tau)
            speed = self._rng.uniform(1.0, 2.5)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 1,
                life=15, max_life=15, color=C_BROWN,
            ))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(
            x=x, y=y, text=text, life=40, max_life=40, color=color,
        ))

    # ------------------------------------------------------------------
    # Input handling (PLAYING phase)
    # ------------------------------------------------------------------
    def _handle_playing_input(self) -> None:
        if self._pull_cooldown > 0:
            self._pull_cooldown -= 1
            return

        clicked = False

        # Mouse click on rope area
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            _, my = pyxel.mouse_x, pyxel.mouse_y
            if ROPE_Y - 30 <= my <= ROPE_Y + 30:
                clicked = True

        # Keyboard pull
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            clicked = True

        if not clicked:
            return

        self._pull_cooldown = 8

        center = self._center_segment()
        matched = self._is_super() or (center.color == self.active_color)

        _, _score_add, fray_triggered = self._resolve_pull(matched)

        if matched:
            self._spawn_pull_particles(center.x, ROPE_Y, self.active_color)
            pts = 10 + max(1, self.combo) * 5
            mult = 3 if self._is_super() else 1
            self._spawn_floating_text(center.x, ROPE_Y - 20,
                                      f"+{pts * mult}", C_YELLOW)
            if self.combo >= COMBO_THRESHOLD and self.super_timer >= SUPER_DURATION - 1:
                self._spawn_floating_text(center.x, ROPE_Y - 35,
                                          "SUPER!", C_PINK)
        else:
            self._spawn_fray_particles(center.x, ROPE_Y)
            self._spawn_floating_text(center.x, ROPE_Y - 20, "MISS", C_RED)

        self._cycle_color()

    # ------------------------------------------------------------------
    # TITLE input
    # ------------------------------------------------------------------
    def _handle_title_input(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()

    # ------------------------------------------------------------------
    # GAME_OVER input
    # ------------------------------------------------------------------
    def _handle_game_over_input(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------
    def _update(self) -> None:
        if self.phase == Phase.TITLE:
            self._handle_title_input()
            return

        if self.phase == Phase.GAME_OVER:
            self._handle_game_over_input()
            return

        # PLAYING phase
        if self.game_timer > 0:
            self.game_timer -= 1

        if self.super_timer > 0:
            self.super_timer -= 1

        self._handle_playing_input()

        # CA fray spread
        if pyxel.frame_count % 4 == 0:
            self._spread_fray()

        self._update_particles()
        self._update_floating_texts()

        if self.shake_frames > 0:
            self.shake_frames -= 1

        if self._check_game_over():
            self.phase = Phase.GAME_OVER

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def _draw(self) -> None:
        pyxel.cls(C_BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        if self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_playing()  # show final state behind overlay
            self._draw_game_over()

    # ------------------------------------------------------------------
    # TITLE screen
    # ------------------------------------------------------------------
    def _draw_title(self) -> None:
        title = "TUG CHAIN"
        tw = len(title) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 60, title, C_YELLOW)

        subtitle = "Tug-of-War Color Match"
        sw = len(subtitle) * 4
        pyxel.text(SCREEN_W // 2 - sw // 2, 75, subtitle, C_WHITE)

        y = 110
        instructions = [
            "Match colors to pull the rope!",
            "Same-color combos = SUPER mode",
            "Wrong color = rope FRAYS!",
            "",
            "Controls:",
            "  Click rope / SPACE / ENTER = Pull",
            "",
            "Press ENTER or SPACE to start",
        ]
        for line in instructions:
            lw = len(line) * 4
            pyxel.text(SCREEN_W // 2 - lw // 2, y, line, C_GRAY)
            y += 10

    # ------------------------------------------------------------------
    # PLAYING screen
    # ------------------------------------------------------------------
    def _draw_playing(self) -> None:
        # Screen shake
        if self.shake_frames > 0:
            try:
                ox = self._rng.randint(-2, 2)
                oy = self._rng.randint(-2, 2)
                pyxel.camera(ox, oy)
            except BaseException:
                pass

        self._draw_hud()
        self._draw_rope()
        self._draw_center_indicator()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_heat_bar()
        self._draw_super_overlay()

        if self.shake_frames > 0:
            try:
                pyxel.camera(0, 0)
            except BaseException:
                pass

    def _draw_hud(self) -> None:
        # Score top-left
        pyxel.text(4, 4, f"SCORE: {self.score}", C_WHITE)

        # Timer top-right
        secs = max(0, self.game_timer // FPS)
        timer_text = f"TIME: {secs}s"
        tw = len(timer_text) * 4
        timer_col = C_YELLOW if secs > 15 else C_RED
        pyxel.text(SCREEN_W - tw - 4, 4, timer_text, timer_col)

        # Combo below time
        combo_text = f"COMBO: {self.combo}"
        combo_col = C_YELLOW if self.combo >= COMBO_THRESHOLD else C_WHITE
        if self.combo >= COMBO_THRESHOLD and pyxel.frame_count % 20 < 10:
            combo_col = C_ORANGE  # flash
        cw = len(combo_text) * 4
        pyxel.text(SCREEN_W - cw - 4, 14, combo_text, combo_col)

        # Max combo
        max_text = f"MAX: {self.max_combo}"
        mw = len(max_text) * 4
        pyxel.text(SCREEN_W - mw - 4, 24, max_text, C_GRAY)

        # Active color indicator top-left below score
        pyxel.text(4, 16, f"NEED: {COLOR_NAMES.get(self.active_color, '?')}",
                   self.active_color)

        # Pull distance
        dist_text = f"DIST: {self.pull_distance:.1f}"
        pyxel.text(4, 28, dist_text, C_LIGHT_BLUE)

    def _draw_rope(self) -> None:
        for seg in self.segments:
            sx = int(seg.x - SEGMENT_W / 2)
            sy = ROPE_Y - 6

            if seg.frayed:
                col = C_BROWN
            else:
                col = seg.color

            pyxel.rect(sx, sy, SEGMENT_W, 12, col)

            # Border
            pyxel.rectb(sx, sy, SEGMENT_W, 12, C_WHITE if not seg.frayed else C_GRAY)

            # Frayed cross-hatching
            if seg.frayed:
                for dx in range(0, SEGMENT_W, 5):
                    pyxel.line(sx + dx, sy, sx + dx + 3, sy + 12, C_GRAY)

    def _draw_center_indicator(self) -> None:
        """Draw indicator around the center segment."""
        center = self._center_segment()
        cx = int(center.x)
        cy = ROPE_Y

        # Highlight active color circle above rope
        if self._is_super():
            # Rainbow cycle during super
            col = self._rainbow_color(pyxel.frame_count // 3)
            pyxel.circb(cx, cy - 25, 14, col)
            pyxel.circb(cx, cy - 25, 12, col)
        else:
            pyxel.circb(cx, cy - 25, 14, self.active_color)

        # Center segment highlight rect
        blink = pyxel.frame_count % 30 < 20
        if blink:
            sx = int(center.x - SEGMENT_W / 2)
            pyxel.rectb(sx - 1, ROPE_Y - 7, SEGMENT_W + 2, 14, C_WHITE)

        # Click zone label
        if pyxel.frame_count % 60 < 40:
            txt = "CLICK!"
            if self._is_super():
                txt = "SUPER!"
            tw = len(txt) * 4
            col = self._rainbow_color(pyxel.frame_count // 2) if self._is_super() else C_WHITE
            pyxel.text(cx - tw // 2, cy - 40, txt, col)

    @staticmethod
    def _rainbow_color(t: int) -> int:
        colors = (C_RED, C_ORANGE, C_YELLOW, C_GREEN, C_LIGHT_BLUE, C_PINK)
        return colors[t % len(colors)]

    def _draw_heat_bar(self) -> None:
        bar_x = 20
        bar_y = SCREEN_H - 20
        bar_w = SCREEN_W - 40
        bar_h = 10

        # Background
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, C_NAVY)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, C_WHITE)

        # Fill
        fill_w = int(bar_w * (self.heat / MAX_HEAT))
        if fill_w > 0:
            if self.heat < 40:
                fill_col = C_GREEN
            elif self.heat < 70:
                fill_col = C_YELLOW
            else:
                fill_col = C_RED
            pyxel.rect(bar_x, bar_y, fill_w, bar_h, fill_col)

        # Label
        label = "ROPE HEALTH"
        lw = len(label) * 4
        pyxel.text(bar_x + bar_w // 2 - lw // 2, bar_y - 10, label, C_GRAY)

    def _draw_super_overlay(self) -> None:
        if not self._is_super():
            return

        # Rainbow border flash
        border_col = self._rainbow_color(pyxel.frame_count // 2)
        if pyxel.frame_count % 6 < 3:
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, border_col)
            pyxel.rectb(1, 1, SCREEN_W - 2, SCREEN_H - 2, border_col)

        # SUPER! text in center-top
        super_text = "SUPER!"
        tw = len(super_text) * 4
        col = self._rainbow_color(pyxel.frame_count // 4)
        pyxel.text(SCREEN_W // 2 - tw // 2, 38, super_text, col)

        # Timer bar
        secs_left = self.super_timer // FPS
        bar_x = SCREEN_W // 2 - 40
        bar_y = 48
        bar_w = 80
        progress = self.super_timer / SUPER_DURATION
        pyxel.rect(bar_x, bar_y, bar_w, 4, C_NAVY)
        pyxel.rect(bar_x, bar_y, int(bar_w * progress), 4, C_PINK)
        pyxel.text(bar_x + bar_w + 4, bar_y - 2, f"{secs_left}s", C_PINK)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / p.max_life
            size = max(1, int(3 * alpha))
            col = p.color if p.life > p.max_life // 2 else C_GRAY
            pyxel.rect(int(p.x), int(p.y), size, size, col)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / ft.max_life
            col = ft.color if alpha > 0.3 else C_GRAY
            tw = len(ft.text) * 4
            pyxel.text(int(ft.x) - tw // 2, int(ft.y), ft.text, col)

    # ------------------------------------------------------------------
    # GAME_OVER screen
    # ------------------------------------------------------------------
    def _draw_game_over(self) -> None:
        # Dim overlay
        for y in range(0, SCREEN_H, 4):
            pyxel.rect(0, y, SCREEN_W, 2, C_BLACK)

        # Game Over text
        go_text = "GAME OVER"
        tw = len(go_text) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 60, go_text, C_RED)

        # Score
        score_text = f"SCORE: {self.score}"
        sw = len(score_text) * 4
        pyxel.text(SCREEN_W // 2 - sw // 2, 90, score_text, C_YELLOW)

        # Pull distance
        dist_text = f"DISTANCE: {self.pull_distance:.1f}"
        dw = len(dist_text) * 4
        pyxel.text(SCREEN_W // 2 - dw // 2, 105, dist_text, C_WHITE)

        # Max combo
        combo_text = f"MAX COMBO: {self.max_combo}"
        cw = len(combo_text) * 4
        pyxel.text(SCREEN_W // 2 - cw // 2, 120, combo_text, C_ORANGE)

        # Reason
        if self.game_timer <= 0:
            reason = "Time's up!"
        else:
            reason = "Rope snapped!"
        rw = len(reason) * 4
        pyxel.text(SCREEN_W // 2 - rw // 2, 140, reason, C_GRAY)

        # Restart
        restart = "Press ENTER / SPACE to retry"
        rw2 = len(restart) * 4
        blink = pyxel.frame_count % 40 < 25
        if blink:
            pyxel.text(SCREEN_W // 2 - rw2 // 2, 170, restart, C_WHITE)

    # ------------------------------------------------------------------
    # Factory for headless tests
    # ------------------------------------------------------------------
    @classmethod
    def _make_game(cls, seed: int = 42) -> "Game":
        """Create a Game instance without pyxel.init for headless testing."""
        game = cls.__new__(cls)
        game._rng = random.Random(seed)
        game._init_state()
        game._build_segments()
        game.phase = Phase.PLAYING
        return game


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    Game()
