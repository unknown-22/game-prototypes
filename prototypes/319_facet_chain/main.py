"""FACET CHAIN — Gem cutting / lapidary color-match combo (Pyxel Prototype).

Polish the facets of a rough gem on a spinning lap wheel. Match the lap's color
to build a COMBO, but the score multiplier (BRILLIANCE) is gated by the WEAKEST
facet — so you must eventually balance every facet to raise it, even though
switching colors breaks the COMBO chain. That tension is the core risk/reward.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

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

FACET_COLORS: tuple[int, ...] = (8, 11, 5, 10)  # RED, LIME, DARK_BLUE, YELLOW (indices 0..3)

FACET_COUNT = 6
MAX_DEPTH = 3

GEM_CX = 160
GEM_CY = 120
GEM_OUTER_R = 60.0
GEM_INNER_R = 34.0
GEM_MID_R = (GEM_OUTER_R + GEM_INNER_R) / 2.0
FACET_HIT_RADIUS = 24

HEAT_MAX = 100.0
HEAT_MISMATCH = 15.0
HEAT_DECAY = 0.02

COMBO_SUPER = 4
SUPER_DURATION = 300

TIMER_MAX = 3600

CYCLE_BASE = 20
CYCLE_MIN = 12

GEM_BONUS = 100


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Facet:
    color: int  # index 0..3 into FACET_COLORS
    depth: int  # 0..MAX_DEPTH


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    gravity: float = 0.0


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="FACET CHAIN", fps=60)
        pyxel.sounds[0].set("c2e2g2", "p", "4", "n", 10)
        pyxel.sounds[1].set("c1", "t", "3", "n", 10)
        pyxel.sounds[2].set("e3g3b3e4", "p", "5", "n", 20)
        self.reset()
        self._sfx_enabled = True
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.rng = getattr(self, "rng", random.Random())
        self.best_score = getattr(self, "best_score", 0)
        self._sfx_enabled = getattr(self, "_sfx_enabled", False)
        self.frame = 0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.gems_completed = 0
        self.super_timer = 0
        self.lap_color = 0
        self.lap_timer = self._cycle_interval()
        self.shake_frames = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.phase = Phase.TITLE
        self.facets = self._new_gem()

    # ---- gem / geometry ----

    def _new_gem(self) -> list[Facet]:
        return [Facet(color=self.rng.randrange(len(FACET_COLORS)), depth=0) for _ in range(FACET_COUNT)]

    def _cycle_interval(self) -> int:
        return max(CYCLE_MIN, CYCLE_BASE - self.frame // 150)

    def brilliance(self) -> int:
        return min(f.depth for f in self.facets) + 1

    def _point(self, angle_rad: float, radius: float) -> tuple[float, float]:
        return (GEM_CX + math.cos(angle_rad) * radius, GEM_CY + math.sin(angle_rad) * radius)

    def _facet_point(self, idx: int, radius: float) -> tuple[float, float]:
        return self._point(math.radians(idx * 60 - 90), radius)

    def _facet_at(self, mx: int, my: int) -> int | None:
        for i in range(FACET_COUNT):
            x, y = self._facet_point(i, GEM_OUTER_R)
            if (mx - x) ** 2 + (my - y) ** 2 <= FACET_HIT_RADIUS ** 2:
                return i
        return None

    # ---- core action ----

    def _polish_facet(self, idx: int) -> None:
        facet = self.facets[idx]
        if facet.depth >= MAX_DEPTH:
            return
        was_super = self.super_timer > 0
        if facet.color == self.lap_color or was_super:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            facet.depth = min(MAX_DEPTH, facet.depth + 1)
            mult = 3 if was_super else 1
            gained = 10 * self.combo * self.brilliance() * mult
            self.score += gained
            self._spawn_float_text(*self._facet_point(idx, GEM_MID_R), f"+{gained}", YELLOW)
            if self.combo >= COMBO_SUPER and not was_super:
                self.super_timer = SUPER_DURATION
                self._spawn_super_particles()
                self._spawn_float_text(GEM_CX - 44, GEM_CY - 80, "SUPER BRILLIANCE!", PINK)
                self._sfx(2)
            else:
                self._spawn_match_particles(idx)
                self._sfx(0)
            if facet.depth >= MAX_DEPTH and all(f.depth >= MAX_DEPTH for f in self.facets):
                self._complete_gem()
        else:
            self.heat = min(HEAT_MAX, self.heat + HEAT_MISMATCH)
            self.combo = 0
            facet.depth = max(0, facet.depth - 1)
            self.shake_frames = 6
            self._spawn_mismatch_particles(idx)
            self._spawn_float_text(*self._facet_point(idx, GEM_MID_R), "MISS +HEAT", RED)
            self._sfx(1)

    def _complete_gem(self) -> None:
        self.gems_completed += 1
        self.score += GEM_BONUS * self.combo
        self.facets = self._new_gem()

    # ---- per-frame updates ----

    def _update_lap(self) -> None:
        if self.super_timer > 0:
            return
        self.lap_timer -= 1
        if self.lap_timer <= 0:
            self.lap_color = (self.lap_color + 1) % len(FACET_COLORS)
            self.lap_timer = self._cycle_interval()

    def _update_heat(self) -> None:
        if self.super_timer > 0:
            return
        if self.heat >= HEAT_MAX:
            self.best_score = max(self.best_score, self.score)
            self.phase = Phase.GAME_OVER
            return
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_timer(self) -> None:
        self.frame += 1
        if self.frame >= TIMER_MAX:
            self.best_score = max(self.best_score, self.score)
            self.phase = Phase.GAME_OVER

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1

    def _update_particles(self) -> None:
        self.particles = [
            Particle(
                x=p.x + p.vx,
                y=p.y + p.vy,
                vx=p.vx,
                vy=p.vy + p.gravity,
                life=p.life - 1,
                color=p.color,
                gravity=p.gravity,
            )
            for p in self.particles
            if p.life - 1 > 0
        ]

    def _update_floating_texts(self) -> None:
        self.floating_texts = [
            FloatingText(x=t.x, y=t.y - 0.5, text=t.text, life=t.life - 1, color=t.color)
            for t in self.floating_texts
            if t.life - 1 > 0
        ]

    # ---- effects ----

    def _spawn_particles(self, x: float, y: float, count: int, color: int, gravity: float = 0.0) -> None:
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
                    gravity=gravity,
                )
            )

    def _spawn_match_particles(self, idx: int) -> None:
        x, y = self._facet_point(idx, GEM_MID_R)
        self._spawn_particles(x, y, 10, FACET_COLORS[self.facets[idx].color], gravity=0.05)

    def _spawn_mismatch_particles(self, idx: int) -> None:
        x, y = self._facet_point(idx, GEM_MID_R)
        self._spawn_particles(x, y, 8, RED, gravity=0.1)

    def _spawn_super_particles(self) -> None:
        for i in range(24):
            angle = self.rng.uniform(0, 6.2832)
            speed = self.rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x=GEM_CX,
                    y=GEM_CY,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=int(self.rng.uniform(15, 30)),
                    color=FACET_COLORS[i % len(FACET_COLORS)],
                    gravity=0.0,
                )
            )

    def _spawn_float_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=40, color=color))

    def _sfx(self, ch: int) -> None:
        if self._sfx_enabled:
            pyxel.play(ch, 0)

    # ---- input / update ----

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
                self.phase = Phase.PLAYING
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
            elif pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
                self.phase = Phase.PLAYING
        elif self.phase == Phase.PLAYING:
            self._update_timer()
            self._update_lap()
            self._update_super()
            self._update_heat()
            self._update_particles()
            self._update_floating_texts()
            if self.phase != Phase.PLAYING:
                return
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                idx = self._facet_at(pyxel.mouse_x, pyxel.mouse_y)
                if idx is not None:
                    self._polish_facet(idx)
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
            if self.shake_frames > 0:
                self.shake_frames -= 1

    # ---- draw ----

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.shake_frames > 0:
            pyxel.camera(self.rng.randint(-2, 2), self.rng.randint(-2, 2))
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        else:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(104, 40, "FACET CHAIN", YELLOW)
        pyxel.text(96, 58, "Gem Cutting Puzzle", WHITE)
        pyxel.text(60, 92, "CLICK a facet to polish it", GRAY)
        pyxel.text(64, 104, "Match the LAP wheel color", GRAY)
        pyxel.text(40, 120, "Same color = COMBO", GRAY)
        pyxel.text(32, 132, "Balance all facets = BRILLIANCE", GRAY)
        pyxel.text(60, 156, "COMBO>=4 : SUPER BRILLIANCE", PINK)
        pyxel.text(80, 188, "SPACE or R to start", WHITE)

    def _draw_playing(self) -> None:
        frac = max(0.0, 1.0 - self.frame / TIMER_MAX)
        pyxel.rect(0, 0, int(SCREEN_W * frac), 4, GREEN)
        pyxel.rectb(0, 0, SCREEN_W, 4, GRAY)

        pyxel.text(4, 6, f"SCORE {self.score}", WHITE)
        if self.combo > 0:
            pyxel.text(4, 16, f"COMBO x{self.combo}", YELLOW)
        pyxel.text(4, 26, f"BRILL x{self.brilliance()}", CYAN)
        pyxel.text(4, 36, f"GEMS {self.gems_completed}", GRAY)

        self._draw_gem()
        self._draw_lap()
        self._draw_heat_bar()
        self._draw_particles()
        self._draw_floating_texts()

        if self.super_timer > 0:
            self._draw_super_border()

    def _draw_gem(self) -> None:
        pyxel.circ(GEM_CX, GEM_CY, int(GEM_INNER_R), DARK_BLUE)
        pyxel.circb(GEM_CX, GEM_CY, int(GEM_INNER_R), GRAY)
        for i in range(FACET_COUNT):
            self._draw_facet(i)

    def _draw_facet(self, idx: int) -> None:
        facet = self.facets[idx]
        a0 = math.radians(idx * 60 - 90)
        a1 = math.radians((idx + 1) * 60 - 90)
        p_out0 = self._point(a0, GEM_OUTER_R)
        p_out1 = self._point(a1, GEM_OUTER_R)
        p_in1 = self._point(a1, GEM_INNER_R)
        p_in0 = self._point(a0, GEM_INNER_R)

        fill = GRAY if facet.depth == 0 else FACET_COLORS[facet.color]
        pyxel.tri(*p_out0, *p_out1, *p_in1, fill)
        pyxel.tri(*p_out0, *p_in1, *p_in0, fill)

        mid = (a0 + a1) / 2
        if facet.depth == MAX_DEPTH:
            pyxel.trib(*p_out0, *p_out1, *p_in1, WHITE)
            pyxel.trib(*p_out0, *p_in1, *p_in0, WHITE)
            mx, my = self._point(mid, GEM_MID_R)
            pyxel.line(mx - 4, my, mx + 4, my, WHITE)
            pyxel.line(mx, my - 4, mx, my + 4, WHITE)
        else:
            for d in range(facet.depth):
                px, py = self._point(mid, GEM_INNER_R + 6 + d * 6)
                pyxel.circ(int(px), int(py), 2, WHITE)

    def _draw_lap(self) -> None:
        color = FACET_COLORS[self.lap_color]
        pyxel.circ(160, 212, 16, color)
        pyxel.circb(160, 212, 16, WHITE)
        pyxel.text(182, 206, "LAP", WHITE)

    def _draw_heat_bar(self) -> None:
        pyxel.rectb(306, 30, 6, 170, GRAY)
        h = int(170 * min(1.0, self.heat / HEAT_MAX))
        color = GREEN if self.heat < 40 else YELLOW if self.heat < 70 else RED
        pyxel.rect(306, 30 + (170 - h), 6, h, color)
        pyxel.text(296, 22, "HEAT", WHITE)

    def _draw_super_border(self) -> None:
        c = FACET_COLORS[(self.frame // 8) % len(FACET_COLORS)]
        pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, c)
        if self.frame // 15 % 2 == 0:
            pyxel.text(92, 168, "SUPER BRILLIANCE!", PINK)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for t in self.floating_texts:
            pyxel.text(int(t.x), int(t.y), t.text, t.color)

    def _draw_game_over(self) -> None:
        pyxel.text(112, 50, "GAME OVER", RED)
        reason = "GEM SHATTERED" if self.heat >= HEAT_MAX else "TIME UP"
        pyxel.text(108, 70, reason, WHITE)
        pyxel.text(96, 100, f"SCORE {self.score}", YELLOW)
        pyxel.text(96, 112, f"BEST {self.best_score}", PINK)
        pyxel.text(96, 124, f"GEMS {self.gems_completed}", WHITE)
        pyxel.text(104, 160, "R to restart", GRAY)


if __name__ == "__main__":
    Game()
