"""WELD CHAIN — Arc-welding color-match arcade (Pyxel Prototype).

Torch color auto-cycles; weld the glowing tip of each crack when colors match.
COMBO x4 triggers SUPER ARC (any color, 3x score). Unwelded cracks grow over
time, so waiting makes more work.
"""

from __future__ import annotations

import enum
import math
import random
from dataclasses import dataclass

import pyxel

SCREEN_W = 320
SCREEN_H = 240

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

COLORS: tuple[int, ...] = (RED, LIME, DARK_BLUE, YELLOW)

SEAM_ROWS = [40, 75, 110, 145, 180]
MAX_SEAMS = 5
SEG_W = 22
SEG_H = 16
SEG_X_START = 40
SEGS_START = 4
SEGS_MAX = 7
HEAT_MAX = 100.0
GAME_TIME = 3600
CRACK_INTERVAL_START = 240
SUPER_THRESHOLD = 4
SUPER_DURATION = 300


class Phase(enum.Enum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


@dataclass
class Segment:
    color: int
    welded: bool = False


@dataclass
class Seam:
    y: int
    segments: list[Segment]

    @property
    def length(self) -> int:
        return len(self.segments)

    @property
    def color(self) -> int:
        return self.segments[0].color

    @property
    def complete(self) -> bool:
        return all(seg.welded for seg in self.segments)

    @property
    def active_index(self) -> int | None:
        for i, seg in enumerate(self.segments):
            if not seg.welded:
                return i
        return None


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
        pyxel.init(SCREEN_W, SCREEN_H, "WELD CHAIN", fps=60)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed) if seed is not None else random.Random()
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = GAME_TIME
        self.frame = 0
        self.torch_index = 0
        self.torch_timer = 0
        self.super_timer = 0
        self.crack_timer = CRACK_INTERVAL_START
        self.shake = 0
        self.phase = Phase.TITLE
        self.seams: list[Seam] = []
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        for row in range(4):
            self._spawn_seam(row)

    # ---- spawning ----

    def _spawn_seam(
        self, row: int, color: int | None = None, length: int | None = None
    ) -> Seam:
        color_index = self.rng.randint(0, 3) if color is None else color
        seg_count = SEGS_START if length is None else length
        seg_count = min(seg_count, SEGS_MAX)
        seam = Seam(
            y=SEAM_ROWS[row],
            segments=[
                Segment(color=COLORS[color_index], welded=False)
                for _ in range(seg_count)
            ],
        )
        self.seams.append(seam)
        return seam

    # ---- torch / cracks ----

    def _torch_color(self) -> int:
        return COLORS[self.torch_index]

    def _cycle_interval(self) -> int:
        return max(12, 20 - self.frame // 360)

    def _crack_interval(self) -> int:
        return max(100, 240 - self.frame // 25)

    def _update_torch(self) -> None:
        self.torch_timer -= 1
        if self.torch_timer <= 0:
            self.torch_index = (self.torch_index + 1) % len(COLORS)
            self.torch_timer = self._cycle_interval()

    def _update_cracks(self) -> int:
        self.crack_timer -= 1
        if self.crack_timer <= 0:
            self.crack_timer = self._crack_interval()
            grown = 0
            for seam in self.seams:
                if not seam.complete and seam.length < SEGS_MAX:
                    seam.segments.append(Segment(color=seam.color, welded=False))
                    grown += 1
            return grown
        return 0

    # ---- core action ----

    def _seam_at(self, x: int, y: int) -> Seam | None:
        for seam in self.seams:
            idx = seam.active_index
            if idx is None:
                continue
            sx = SEG_X_START + idx * SEG_W
            sy = seam.y
            if sx <= x < sx + SEG_W and sy <= y < sy + SEG_H:
                return seam
        return None

    def _weld_seam(self, seam: Seam) -> str:
        idx = seam.active_index
        if idx is None:
            return "none"
        segment = seam.segments[idx]
        matched = (self.super_timer > 0) or (segment.color == self._torch_color())
        cx = SEG_X_START + idx * SEG_W + SEG_W // 2
        cy = seam.y + SEG_H // 2

        if matched:
            segment.welded = True
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            mult = 3 if self.super_timer > 0 else 1
            gained = 10 * self.combo * mult
            self.score += gained
            self._spawn_particles(cx, cy, 8, segment.color)
            if seam.complete:
                bonus = 50 * self.combo * mult
                self.score += bonus
                self._spawn_particles(cx, cy, 16, WHITE)
                self._spawn_float_text(
                    SEG_X_START + idx * SEG_W,
                    seam.y - 4,
                    f"SEAM COMPLETE! +{bonus}",
                    YELLOW,
                )
                self.seams.remove(seam)
                self._spawn_seam(SEAM_ROWS.index(seam.y))
                return "complete"
            return "match"

        self.heat += 15.0
        self.combo = 0
        self._spawn_particles(cx, cy, 4, RED)
        self._spawn_float_text(SEG_X_START + idx * SEG_W, seam.y - 4, "WRONG!", RED)
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
        return "mismatch"

    # ---- per-frame updates ----

    def _update_heat(self) -> None:
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            return
        if self.super_timer <= 0:
            self.heat = max(0.0, self.heat - 0.02)

    def _update_timer(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
        self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floats(self) -> None:
        for t in self.floats:
            t.y -= 0.5
            t.life -= 1
        self.floats = [t for t in self.floats if t.life > 0]

    # ---- effects ----

    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, 6.2832)
            speed = self.rng.uniform(0.5, 2.5)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=int(self.rng.uniform(10, 25)),
                    color=color,
                )
            )

    def _spawn_float_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floats.append(FloatingText(x=x, y=y, text=text, life=40, color=color))

    # ---- input / update ----

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
                self.phase = Phase.PLAYING
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.TITLE
        elif self.phase == Phase.PLAYING:
            self.frame += 1
            self._update_torch()
            self._update_cracks()
            self._update_heat()
            self._update_timer()
            self._update_particles()
            self._update_floats()
            if self.phase != Phase.PLAYING:
                return

            result = "none"
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                seam = self._seam_at(pyxel.mouse_x, pyxel.mouse_y)
                if seam is not None:
                    result = self._weld_seam(seam)
            elif pyxel.btnp(pyxel.KEY_SPACE):
                seam = next((s for s in self.seams if s.active_index is not None), None)
                if seam is not None:
                    result = self._weld_seam(seam)

            if result in ("match", "complete") and self.combo >= SUPER_THRESHOLD and self.super_timer <= 0:
                self.super_timer = SUPER_DURATION
                self._spawn_particles(160, 120, 20, PINK)

            if self.shake > 0:
                self.shake -= 1

    # ---- draw ----

    def draw(self) -> None:
        pyxel.cls(NAVY)
        if self.shake > 0:
            pyxel.camera(self.rng.randint(-2, 2), self.rng.randint(-2, 2))
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(100, 60, "WELD CHAIN", YELLOW)
        pyxel.text(60, 84, "Arc-weld the cracks shut!", WHITE)
        pyxel.text(44, 98, "Match the torch color to the", WHITE)
        pyxel.text(44, 110, "crack's glowing tip.", WHITE)
        pyxel.text(64, 142, "CLICK: weld crack", GRAY)
        pyxel.text(64, 154, "SPACE: weld topmost crack", GRAY)
        pyxel.text(64, 166, "ENTER: start", GRAY)
        pyxel.text(60, 198, "COMBO x4 = SUPER ARC", PINK)

    def _draw_playing(self) -> None:
        pyxel.rect(0, 20, SCREEN_W, 200, BROWN)

        pyxel.text(4, 4, f"SCORE {self.score}", WHITE)
        pyxel.text(110, 4, f"COMBO x{self.combo}", PINK)
        frac = max(0.0, self.timer / GAME_TIME)
        pyxel.rect(230, 4, int(86 * frac), 6, GREEN)
        pyxel.rectb(230, 4, 86, 6, GRAY)

        for seam in self.seams:
            for i, seg in enumerate(seam.segments):
                color = GRAY if seg.welded else seg.color
                pyxel.rect(SEG_X_START + i * SEG_W, seam.y, SEG_W, SEG_H, color)
            idx = seam.active_index
            if idx is not None:
                pyxel.rectb(SEG_X_START + idx * SEG_W, seam.y, SEG_W, SEG_H, WHITE)

        pyxel.text(8, 226, "TORCH", WHITE)
        pyxel.rect(48, 224, 16, 16, self._torch_color())
        pyxel.rectb(48, 224, 16, 16, WHITE)
        pyxel.rect(68, 228, 8, 8, COLORS[(self.torch_index + 1) % len(COLORS)])

        pyxel.text(100, 226, "HEAT", WHITE)
        heat_color = GREEN if self.heat < 40 else YELLOW if self.heat < 70 else RED
        pyxel.rect(140, 226, int(self.heat * 1.5), 8, heat_color)
        pyxel.rectb(140, 226, 150, 8, GRAY)

        if self.super_timer > 0:
            c = COLORS[self.frame % len(COLORS)]
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, c)
            pyxel.text(116, 210, "SUPER ARC!", c)

        self._draw_particles()
        self._draw_floats()

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floats(self) -> None:
        for t in self.floats:
            pyxel.text(int(t.x), int(t.y), t.text, t.color)

    def _draw_game_over(self) -> None:
        pyxel.text(112, 60, "GAME OVER", RED)
        reason = "BURN THROUGH!" if self.heat >= HEAT_MAX else "TIME UP"
        pyxel.text(116, 80, reason, WHITE)
        pyxel.text(96, 112, f"SCORE {self.score}", YELLOW)
        pyxel.text(96, 132, f"MAX COMBO x{self.max_combo}", PINK)
        pyxel.text(96, 184, "ENTER: retry", GRAY)


if __name__ == "__main__":
    Game()
