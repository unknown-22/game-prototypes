"""FORGE CHAIN — a single-file Pyxel prototype.

Forge blades by striking a color-matched billet, build combo and temper, then
quench to bank a large score bonus. Mismatches heat the forge; let heat hit 100
and the forge melts down.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

import pyxel


# --- color constants -------------------------------------------------------

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
    color: int
    life: int


class Phase(Enum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


class Game:
    SCREEN_W = 320
    SCREEN_H = 240
    METAL_COLORS: tuple[int, ...] = (RED, LIME, DARK_BLUE, YELLOW)
    METAL_NAMES: tuple[str, ...] = ("IRON", "COPPER", "STEEL", "GOLD")

    TIMER_START = 3600
    SUPER_DURATION = 300
    MELTDOWN_HEAT = 100

    def __init__(self) -> None:
        pyxel.init(
            self.SCREEN_W,
            self.SCREEN_H,
            title="FORGE CHAIN",
            fps=60,
            display_scale=2,
        )
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.temper: int = 0
        self.heat: float = 0.0
        self.timer: int = self.TIMER_START
        self.billet_color: int = 0
        self.hammer_color: int = 0
        self.frame: int = 0
        self.hammer_timer: int = self._cycle_interval()
        self.super_timer: int = 0
        self.particles: list[Particle] = []
        self.texts: list[FloatingText] = []
        self.shake_frames: int = 0
        self.best_score: int = 0
        self.rng: random.Random = random.Random()

    # ------------------------------------------------------------------ logic

    def _cycle_interval(self) -> int:
        """Hammer color cycle interval, shrinking from 20f to 12f over time."""
        return max(12, 20 - (self.frame // 450))

    def _advance_hammer(self) -> None:
        self.hammer_timer -= 1
        if self.hammer_timer <= 0:
            self.hammer_color = (self.hammer_color + 1) % len(self.METAL_COLORS)
            self.hammer_timer = self._cycle_interval()

    def _strike(self) -> None:
        if self.phase != Phase.PLAYING:
            return
        match = (
            self.super_timer > 0 or self.hammer_color == self.billet_color
        )
        if match:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            self.temper += 1
            multiplier = 3 if self.super_timer > 0 else 1
            gained = 10 * self.combo * (1 + self.temper // 3) * multiplier
            self.score += gained
            self._spawn_match_particles()
            self._spawn_text(
                f"+{gained}", YELLOW, 190, 150
            )
            if self.combo >= 4 and self.super_timer <= 0:
                self.super_timer = self.SUPER_DURATION
                self._spawn_text("SUPER FORGE!", PINK, 160, 110)
        else:
            self.heat += 15
            self.combo = 0
            self.temper = max(0, self.temper - 1)
            self._spawn_mismatch_particles()
            self._spawn_text("MISS", GRAY, 190, 150)

    def _quench(self) -> None:
        if self.phase != Phase.PLAYING or self.temper < 1:
            return
        gained = self.temper * 100 + self.combo * 20
        self.score += gained
        self.heat = max(0.0, self.heat - 30)
        self.combo = 0
        self.temper = 0
        self.super_timer = 0
        self._spawn_quench_particles()
        self._spawn_text(f"QUENCH! +{gained}", CYAN, 160, 110)
        self._spawn_billet()

    def _spawn_billet(self) -> None:
        self.billet_color = self.rng.randrange(len(self.METAL_COLORS))

    def _update_heat(self) -> None:
        if self.heat >= self.MELTDOWN_HEAT:
            self._game_over_meltdown()
            return
        self.heat = max(0.0, self.heat - 0.03)

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.2
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_texts(self) -> None:
        for t in self.texts:
            t.y -= 0.5
            t.life -= 1
        self.texts = [t for t in self.texts if t.life > 0]

    def _best_score_update(self) -> None:
        self.best_score = max(self.best_score, self.score)

    def _game_over_meltdown(self) -> None:
        self.phase = Phase.GAME_OVER
        self._best_score_update()
        self.shake_frames = 20

    def _game_over_timeup(self) -> None:
        self.phase = Phase.GAME_OVER
        self._best_score_update()

    # ------------------------------------------------------------- particles

    def _spawn_match_particles(self) -> None:
        color = self.METAL_COLORS[self.billet_color]
        if self.super_timer > 0:
            for _ in range(20):
                self.particles.append(
                    Particle(
                        190,
                        160,
                        self.rng.uniform(-3, 3),
                        self.rng.uniform(-4, -1),
                        self.rng.randint(15, 25),
                        self.rng.choice(list(range(16))),
                    )
                )
        else:
            for _ in range(8):
                self.particles.append(
                    Particle(
                        190,
                        160,
                        self.rng.uniform(-2.5, 2.5),
                        self.rng.uniform(-3.5, -1),
                        self.rng.randint(10, 20),
                        color,
                    )
                )

    def _spawn_mismatch_particles(self) -> None:
        for _ in range(4):
            self.particles.append(
                Particle(
                    190,
                    160,
                    self.rng.uniform(-1, 1),
                    self.rng.uniform(-1.5, 0),
                    self.rng.randint(10, 20),
                    GRAY,
                )
            )

    def _spawn_quench_particles(self) -> None:
        for _ in range(16):
            self.particles.append(
                Particle(
                    190,
                    160,
                    self.rng.uniform(-3, 3),
                    self.rng.uniform(-4, -0.5),
                    self.rng.randint(10, 25),
                    self.rng.choice([CYAN, LIGHT_BLUE]),
                )
            )

    def _spawn_text(self, text: str, color: int, x: float, y: float) -> None:
        self.texts.append(FloatingText(x, y, text, color, 40))

    # ----------------------------------------------------------------- input

    def _handle_input(self) -> None:
        if self.phase == Phase.TITLE:
            if (
                pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            ):
                self.start()
        elif self.phase == Phase.PLAYING:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self._strike()
            if pyxel.btnp(pyxel.KEY_Q):
                self._quench()
        elif self.phase == Phase.GAME_OVER:
            if (
                pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.KEY_R)
            ):
                self.start()

    def start(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.temper = 0
        self.heat = 0.0
        self.timer = self.TIMER_START
        self.billet_color = 0
        self.hammer_color = 0
        self.frame = 0
        self.hammer_timer = self._cycle_interval()
        self.super_timer = 0
        self.particles = []
        self.texts = []
        self.shake_frames = 0
        self.phase = Phase.PLAYING
        self._spawn_billet()

    # ----------------------------------------------------------------- update

    def update(self) -> None:
        self._handle_input()
        if self.phase == Phase.PLAYING:
            self.frame += 1
            self.timer -= 1
            self._advance_hammer()
            self._update_heat()
            self._update_super()
            self._update_particles()
            self._update_texts()
            if self.shake_frames > 0:
                self.shake_frames -= 1
            if self.timer <= 0:
                self._game_over_timeup()
        else:
            if self.shake_frames > 0:
                self.shake_frames -= 1
            self._update_particles()
            self._update_texts()

    # ------------------------------------------------------------------- draw

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(96, 70, "FORGE CHAIN", RED)
        pyxel.text(100, 95, "STRIKE: SPACE/CLICK", WHITE)
        pyxel.text(112, 107, "QUENCH: Q", WHITE)
        pyxel.text(88, 130, "Press SPACE to start", YELLOW)
        pyxel.text(70, 200, "Match the hammer to the billet", GRAY)
        pyxel.text(60, 212, "Build combo, quench before meltdown", GRAY)

    def _draw_playing(self) -> None:
        offset_x = self.rng.randint(-self.shake_frames, self.shake_frames) if self.shake_frames > 0 else 0
        offset_y = self.rng.randint(-self.shake_frames, self.shake_frames) if self.shake_frames > 0 else 0

        # anvil
        pyxel.rect(90 + offset_x, 180 + offset_y, 140, 14, GRAY)
        pyxel.rect(100 + offset_x, 194 + offset_y, 120, 8, DARK_BLUE)

        # billet glow grows with temper
        color = self.METAL_COLORS[self.billet_color]
        glow = min(20, self.temper * 3)
        for r in range(glow, 0, -1):
            pyxel.circb(160 + offset_x, 178 + offset_y, r, color)
        pyxel.rect(140 + offset_x, 170 + offset_y, 40, 12, color)

        # hammer indicator top-right
        pyxel.rect(250, 20, 60, 24, GRAY)
        pyxel.rect(252, 22, 56, 20, self.METAL_COLORS[self.hammer_color])
        pyxel.text(252, 26, self.METAL_NAMES[self.hammer_color], BLACK)

        # HUD
        pyxel.text(8, 8, f"SCORE {self.score}", WHITE)
        pyxel.text(8, 18, f"COMBO {self.combo}", YELLOW)
        pyxel.text(8, 28, f"TEMPER {self.temper}", LIME)
        pyxel.text(8, 38, self.METAL_NAMES[self.billet_color], color)

        # temper bar
        pyxel.rect(8, 50, 100, 6, GRAY)
        pyxel.rect(8, 50, min(100, self.temper * 5), 6, LIME)

        # heat bar (right, vertical)
        hx = 300
        pyxel.rect(hx, 60, 12, 120, GRAY)
        heat_level = int(min(120, self.heat / self.MELTDOWN_HEAT * 120))
        heat_color = GREEN if self.heat < 40 else (YELLOW if self.heat < 70 else RED)
        pyxel.rect(hx, 180 - heat_level, 12, heat_level, heat_color)
        pyxel.text(hx - 4, 44, "HEAT", RED)

        # timer bar top
        pyxel.rect(8, 4, 0, 0, BLACK)
        pyxel.rect(110, 8, 180, 6, GRAY)
        pyxel.rect(110, 8, int(180 * self.timer / self.TIMER_START), 6, WHITE)

        # super forge
        if self.super_timer > 0:
            for i in range(4):
                pyxel.rectb(i, i, self.SCREEN_W - 2 * i, self.SCREEN_H - 2 * i, (pyxel.frame_count // 4 + i) % 16)
            pyxel.text(110, 60, "SUPER FORGE!", PINK)

        # particles
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

        # floating text
        for t in self.texts:
            pyxel.text(int(t.x), int(t.y), t.text, t.color)

    def _draw_game_over(self) -> None:
        pyxel.text(110, 80, "MELTDOWN!" if self.heat >= self.MELTDOWN_HEAT else "TIME UP!", RED)
        pyxel.text(110, 100, f"SCORE {self.score}", WHITE)
        pyxel.text(110, 112, f"BEST {self.best_score}", YELLOW)
        pyxel.text(110, 124, f"MAX COMBO {self.max_combo}", LIME)
        pyxel.text(88, 150, "Press SPACE to restart", WHITE)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
