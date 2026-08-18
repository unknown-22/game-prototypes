"""STEADY CHAIN - Surgical Steady-Hand Arcade."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

import pyxel


class Phase(Enum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


@dataclass
class Segment:
    x1: float
    y1: float
    x2: float
    y2: float
    color: int
    cut: bool = False


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
    SCREEN_W = 320
    SCREEN_H = 240
    COLORS = (RED, LIME, DARK_BLUE, YELLOW) = (8, 11, 5, 10)
    WHITE = 7
    ORANGE = 9
    CYAN = 12
    PINK = 14
    WAYPOINTS = [
        (30, 130),
        (70, 80),
        (110, 170),
        (150, 90),
        (190, 170),
        (230, 80),
        (270, 130),
    ]
    HALF_WIDTH_BASE = 10
    HALF_WIDTH_MIN = 7
    MAX_HEAT = 100
    SUPER_DURATION = 300
    TIMER_START = 3600

    def __init__(self) -> None:
        pyxel.init(self.SCREEN_W, self.SCREEN_H, title="STEADY CHAIN", fps=60)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.rng: random.Random = getattr(self, "rng", random.Random())
        self.best_score: int = getattr(self, "best_score", 0)
        self._sfx_enabled: bool = getattr(self, "_sfx_enabled", True)

        self.segments: list[Segment] = []
        self.active_idx: int = 0
        self.scalpel_color: int = self.COLORS[0]
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.heat: float = 0.0
        self.time_left: int = self.TIMER_START
        self.elapsed: int = 0
        self.scalpel_timer: int = self._cycle_interval()
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shake_frames: int = 0
        self.cursor_x: int = 160
        self.cursor_y: int = 120

        self._spawn_incision()

    def _cycle_interval(self) -> int:
        return max(12, 20 - self.elapsed // 150)

    def _half_width(self) -> float:
        return max(self.HALF_WIDTH_MIN, self.HALF_WIDTH_BASE - self.elapsed // 450)

    def _distance_point_segment(self, px: float, py: float, s: Segment) -> float:
        dx = s.x2 - s.x1
        dy = s.y2 - s.y1
        length_sq = dx * dx + dy * dy
        if length_sq == 0:
            return ((px - s.x1) ** 2 + (py - s.y1) ** 2) ** 0.5
        t = ((px - s.x1) * dx + (py - s.y1) * dy) / length_sq
        t = max(0.0, min(1.0, t))
        cx = s.x1 + t * dx
        cy = s.y1 + t * dy
        return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5

    def _active_segment(self) -> Segment | None:
        if self.active_idx < len(self.segments):
            return self.segments[self.active_idx]
        return None

    def _try_cut(self, px: float, py: float) -> str:
        if self.phase != Phase.PLAYING:
            return "none"
        active = self._active_segment()
        if active is None:
            return "none"
        d = self._distance_point_segment(px, py, active)
        if d > self._half_width():
            self.combo = 0
            self.heat += 15
            self._spawn_particles(px, py, 6, self.RED)
            self._shake(8)
            self._add_floating_text(px, py, "SLIP!", self.RED)
            self._sfx(0, 3)
            return "slip"
        match = (active.color == self.scalpel_color) or self.super_mode
        if match:
            self._cut_active(px, py)
            return "cut"
        self.combo = 0
        self.heat += 15
        self._add_floating_text(px, py, "WRONG!", self.RED)
        self._sfx(0, 2)
        return "wrong"

    def _cut_active(self, px: float, py: float) -> None:
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        mult = 3 if self.super_mode else 1
        gained = 10 * self.combo * mult
        self.score += gained
        self.segments[self.active_idx].cut = True
        seg_color = self.segments[self.active_idx].color
        self._spawn_particles(px, py, 8, seg_color)
        self._add_floating_text(px, py, f"+{gained}", seg_color)
        self._sfx(1, 5)
        self.active_idx += 1
        self._update_super_for_cut()
        if self.active_idx >= len(self.segments):
            self.score += 100 * self.combo
            self._add_floating_text(
                self.SCREEN_W // 2, self.SCREEN_H // 2, "INCISION COMPLETE!", self.WHITE
            )
            self._spawn_incision()

    def _update_super_for_cut(self) -> None:
        if self.combo >= 4 and not self.super_mode:
            self.super_mode = True
            self.super_timer = self.SUPER_DURATION
            self._add_floating_text(
                self.SCREEN_W // 2, self.SCREEN_H // 2 - 20, "SUPER STEADY!", self.PINK
            )
            self._sfx(2, 7)

    def _spawn_incision(self) -> None:
        self.segments = []
        for i in range(len(self.WAYPOINTS) - 1):
            x1, y1 = self.WAYPOINTS[i]
            x2, y2 = self.WAYPOINTS[i + 1]
            self.segments.append(
                Segment(x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2), color=self.rng.choice(self.COLORS))
            )
        self.active_idx = 0

    def _cycle_color(self) -> None:
        if self.super_mode:
            return
        self.scalpel_timer -= 1
        if self.scalpel_timer <= 0:
            idx = self.COLORS.index(self.scalpel_color)
            self.scalpel_color = self.COLORS[(idx + 1) % len(self.COLORS)]
            self.scalpel_timer = self._cycle_interval()

    def _update_heat(self) -> None:
        if self.heat >= self.MAX_HEAT:
            self.phase = Phase.GAME_OVER
            return
        if not self.super_mode:
            self.heat = max(0.0, self.heat - 0.02)

    def _update_super(self) -> None:
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False

    def _update_timer(self) -> None:
        self.elapsed += 1
        self.time_left -= 1
        if self.time_left <= 0:
            self.phase = Phase.GAME_OVER

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for t in self.floating_texts:
            t.y -= 0.5
            t.life -= 1
        self.floating_texts = [t for t in self.floating_texts if t.life > 0]

    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0.0, 6.28318)
            speed = self.rng.uniform(0.5, 2.5)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self.rng.uniform(-2.5, 2.5) + self._cos(angle) * speed,
                    vy=self.rng.uniform(-2.5, 2.5) + self._sin(angle) * speed,
                    life=self.rng.randint(20, 40),
                    color=color,
                )
            )

    def _cos(self, a: float) -> float:
        import math

        return math.cos(a)

    def _sin(self, a: float) -> float:
        import math

        return math.sin(a)

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=40, color=color))

    def _shake(self, frames: int) -> None:
        self.shake_frames = max(self.shake_frames, frames)

    def _sfx(self, ch: int, s: int) -> None:
        if self._sfx_enabled:
            pyxel.play(ch, s)

    def start(self) -> None:
        self.reset()
        self.phase = Phase.PLAYING

    def _restart(self) -> None:
        self.best_score = max(self.best_score, self.score)
        self.reset()
        self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self.cursor_x = pyxel.mouse_x
        self.cursor_y = pyxel.mouse_y
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._try_cut(self.cursor_x, self.cursor_y)
        self._cycle_color()
        self._update_heat()
        self._update_super()
        self._update_timer()
        self._update_particles()
        self._update_floating_texts()
        if self.shake_frames > 0:
            self.shake_frames -= 1

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if (
                pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            ):
                self.start()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            if (
                pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.KEY_R)
            ):
                self._restart()

    def draw(self) -> None:
        if self.shake_frames > 0:
            pyxel.camera(
                self.rng.randint(-3, 3),
                self.rng.randint(-3, 3),
            )
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.cls(1)
        cx = self.SCREEN_W // 2
        pyxel.text(cx - 34, 60, "STEADY CHAIN", 7)
        pyxel.text(cx - 52, 74, "SURGICAL STEADY HAND", 13)
        pyxel.text(cx - 80, 110, "CLICK: cut matching segment", 7)
        pyxel.text(cx - 84, 124, "Stay on the incision - don't slip!", 7)
        pyxel.text(cx - 56, 150, "PRESS SPACE TO START", 10)

    def _draw_playing(self) -> None:
        pyxel.cls(1)
        self._draw_incision()
        self._draw_scalpel()
        self._draw_hud()
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)
        for t in self.floating_texts:
            pyxel.text(int(t.x) - len(t.text) * 2, int(t.y), t.text, t.color)

    def _draw_incision(self) -> None:
        half = self._half_width()
        for i, seg in enumerate(self.segments):
            color = seg.color if not seg.cut else 13
            if i == self.active_idx and not seg.cut:
                pulse = 2 if (pyxel.frame_count // 15) % 2 == 0 else 0
                color = min(15, color + pulse)
            pyxel.line(
                int(seg.x1), int(seg.y1), int(seg.x2), int(seg.y2), 5
            )
            pyxel.line(
                int(seg.x1), int(seg.y1), int(seg.x2), int(seg.y2), color
            )
        if self._active_segment() is not None:
            active = self._active_segment()
            if active is not None:
                pyxel.circb(int(active.x1), int(active.y1), int(half), 7)

    def _draw_scalpel(self) -> None:
        x = self.cursor_x
        y = self.cursor_y
        if self.super_mode:
            color = self._rainbow()
        else:
            color = self.scalpel_color
        pyxel.line(x - 6, y - 6, x + 6, y + 6, color)
        pyxel.line(x - 6, y + 6, x + 6, y - 6, color)
        pyxel.circb(x, y, 8, color)

    def _rainbow(self) -> int:
        colors = [self.RED, self.ORANGE, self.YELLOW, self.LIME, self.CYAN, self.PINK]
        return colors[(pyxel.frame_count // 4) % len(colors)]

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE {self.score}", 7)
        pyxel.text(4, 14, f"COMBO x{self.combo}", 11)
        if self.super_mode:
            pyxel.text(4, 26, "SUPER STEADY!", self.PINK)

        self._draw_timer_bar()
        self._draw_heat_bar()

    def _draw_timer_bar(self) -> None:
        x = 4
        y = 40
        w = 100
        frac = max(0.0, min(1.0, self.time_left / self.TIMER_START))
        pyxel.rectb(x, y, w, 6, 7)
        pyxel.rect(x + 1, y + 1, int((w - 2) * frac), 4, 6)

    def _draw_heat_bar(self) -> None:
        x = self.SCREEN_W - 16
        y = 40
        h = 160
        frac = max(0.0, min(1.0, self.heat / self.MAX_HEAT))
        if frac < 0.5:
            color = 3
        elif frac < 0.8:
            color = 10
        else:
            color = 8
        pyxel.rectb(x, y, 10, h, 7)
        pyxel.rect(x + 1, y + 1, 8, int((h - 2) * frac), color)
        pyxel.text(x - 20, y + h + 4, "HEAT", 7)

    def _draw_game_over(self) -> None:
        pyxel.cls(1)
        cx = self.SCREEN_W // 2
        pyxel.text(cx - 24, 60, "GAME OVER", 8)
        cause = "PATIENT LOST" if self.heat >= self.MAX_HEAT else "TIME UP"
        pyxel.text(cx - len(cause) * 2, 80, cause, 7)
        pyxel.text(cx - 40, 110, f"SCORE {self.score}", 7)
        pyxel.text(cx - 40, 124, f"BEST {self.best_score}", 11)
        pyxel.text(cx - 44, 150, "PRESS R TO RETRY", 10)


if __name__ == "__main__":
    Game()
