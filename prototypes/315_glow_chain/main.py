import math
import random
from dataclasses import dataclass
from enum import Enum

import pyxel

# ---------------------------------------------------------------------------
# Screen / timing constants
# ---------------------------------------------------------------------------
SCREEN_W = 320
SCREEN_H = 240
FPS = 60

# ---------------------------------------------------------------------------
# Color constants (raw ints)
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

# Temperature bands, cold -> hot. Each maps to a color the glass GLOWS with.
BAND_COLORS: tuple[int, ...] = (DARK_BLUE, GREEN, YELLOW, RED)
BAND_NAMES: tuple[str, ...] = ("COLD", "COOL", "WARM", "HOT")

RAINBOW: tuple[int, ...] = (
    RED,
    ORANGE,
    YELLOW,
    LIME,
    GREEN,
    CYAN,
    LIGHT_BLUE,
    DARK_BLUE,
    PURPLE,
    PINK,
    PEACH,
    WHITE,
    GRAY,
    BROWN,
    NAVY,
)

# ---------------------------------------------------------------------------
# Gameplay constants
# ---------------------------------------------------------------------------
TEMP_MIN = 0.0
TEMP_MAX = 100.0
HEAT_RATE = 0.8
COOL_BASE = 0.25
COOL_RANGE = 0.30
START_TEMP_MIN = 15.0
START_TEMP_MAX = 35.0

HEAT_MISMATCH = 15
HEAT_OVERHEAT = 20
HEAT_FREEZE = 15
HEAT_DECAY = 0.02
HEAT_CAP = 100.0

SUPER_THRESHOLD = 4
SUPER_DURATION = 300
SCORE_BASE = 10
SUPER_MULT = 3

TIMER_FRAMES = 3600

# Layout
GLASS_X = 160
GLASS_Y = 150
FURNACE_X = 290
FURNACE_FLAME_Y = 190


class Phase(Enum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="GLOW CHAIN", fps=FPS)
        pyxel.mouse(True)
        self.best_score = 0
        self.reset()
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------ logic
    @staticmethod
    def band_index(temp: float) -> int:
        return min(3, int(temp // 25))

    @staticmethod
    def band_color(temp: float) -> int:
        return BAND_COLORS[Game.band_index(temp)]

    def _cool_rate(self) -> float:
        return COOL_BASE + COOL_RANGE * (self.frame / TIMER_FRAMES)

    def _new_start_temp(self) -> float:
        return self._rng.uniform(START_TEMP_MIN, START_TEMP_MAX)

    def _advance_order(self) -> None:
        self.order_color = int(self._rng.choice(BAND_COLORS))

    def _start_super(self) -> None:
        self.super_timer = SUPER_DURATION

    # ------------------------------------------------------------------ state
    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.frame = 0
        self._rng = random.Random(42)
        self.temp = self._new_start_temp()
        self.order_color = int(self._rng.choice(BAND_COLORS))
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_timer = 0
        self.reheating = False
        self.vessels_made = 0
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self.shake_frames = 0
        self.game_over_reason = ""

    def _add_float(self, text: str, x: float, y: float, color: int, life: int = 40) -> None:
        self.floats.append(FloatingText(x, y, text, life, color))

    def _spawn_burst(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            ang = self._rng.uniform(0.0, math.tau)
            spd = self._rng.uniform(0.5, 3.0)
            self.particles.append(
                Particle(
                    x,
                    y,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    self._rng.randint(20, 45),
                    color,
                    self._rng.randint(1, 3),
                )
            )

    def _spawn_rainbow_burst(self, x: float, y: float, count: int) -> None:
        for i in range(count):
            ang = self._rng.uniform(0.0, math.tau)
            spd = self._rng.uniform(1.0, 3.5)
            self.particles.append(
                Particle(
                    x,
                    y,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    self._rng.randint(30, 55),
                    RAINBOW[i % len(RAINBOW)],
                    self._rng.randint(1, 3),
                )
            )

    # ------------------------------------------------------------------ update
    def _update_temp(self, reheating: bool) -> None:
        if reheating:
            if self.temp >= TEMP_MAX:
                self.heat += HEAT_OVERHEAT
                self.combo = 0
                self.temp = self._new_start_temp()
                self._add_float("SAG!", GLASS_X, GLASS_Y - 24, RED)
                self._spawn_burst(GLASS_X, GLASS_Y, ORANGE, 12)
                self.shake_frames = 8
            else:
                self.temp = min(TEMP_MAX, self.temp + HEAT_RATE)
        else:
            self.temp -= self._cool_rate()
            if self.temp <= TEMP_MIN:
                self.heat += HEAT_FREEZE
                self.combo = 0
                self.temp = self._new_start_temp()
                self._add_float("CRACK!", GLASS_X, GLASS_Y - 24, CYAN)

    def _blow(self) -> bool:
        if self.super_timer > 0 or self.band_color(self.temp) == self.order_color:
            matched_color = self.order_color
            self.combo += 1
            mult = SUPER_MULT if self.super_timer > 0 else 1
            gained = SCORE_BASE * self.combo * mult
            self.score += gained
            self.max_combo = max(self.max_combo, self.combo)
            self.vessels_made += 1
            self.temp = self._new_start_temp()
            self._advance_order()
            if self.super_timer > 0:
                self._spawn_rainbow_burst(GLASS_X, GLASS_Y, 24)
            else:
                self._spawn_burst(GLASS_X, GLASS_Y, matched_color, 12)
            self._add_float(f"+{gained}", GLASS_X, GLASS_Y - 28, WHITE)
            if self.combo >= SUPER_THRESHOLD and self.super_timer == 0:
                self._start_super()
                self._add_float("SUPER BLOW!", GLASS_X, GLASS_Y - 48, YELLOW, 60)
            return True
        self.heat += HEAT_MISMATCH
        self.combo = 0
        self.temp = self._new_start_temp()
        self._add_float("WRONG!", GLASS_X, GLASS_Y - 24, RED)
        return False

    def _update_heat(self) -> None:
        if self.heat >= HEAT_CAP:
            self._game_over("MELTDOWN")
            return
        self.heat = max(0.0, self.heat - (0.0 if self.super_timer > 0 else HEAT_DECAY))

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floats(self) -> None:
        for f in self.floats:
            f.y -= 0.5
            f.life -= 1
        self.floats = [f for f in self.floats if f.life > 0]

    def _game_over(self, reason: str) -> None:
        self.phase = Phase.GAME_OVER
        self.game_over_reason = reason
        self.best_score = max(getattr(self, "best_score", 0), self.score)

    def _spawn_flame(self) -> None:
        self.particles.append(
            Particle(
                FURNACE_X + self._rng.uniform(-6.0, 6.0),
                FURNACE_FLAME_Y,
                self._rng.uniform(-0.3, 0.3),
                self._rng.uniform(-2.5, -0.5),
                self._rng.randint(15, 40),
                int(self._rng.choice((ORANGE, YELLOW, RED))),
                self._rng.randint(1, 3),
            )
        )

    # ------------------------------------------------------------------ input
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if (
                pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            ):
                self.reset()
                self.phase = Phase.PLAYING
            return

        if self.phase == Phase.GAME_OVER:
            if (
                pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            ):
                self.phase = Phase.TITLE
            return

        self.reheating = pyxel.btn(pyxel.KEY_R)
        if pyxel.btnp(pyxel.KEY_SPACE):
            self._blow()
        if self.reheating:
            self._spawn_flame()
        self._update_temp(self.reheating)
        self._update_super()
        self._update_heat()
        self._update_particles()
        self._update_floats()
        if self.shake_frames > 0:
            self.shake_frames -= 1
        self.frame += 1
        if self.frame >= TIMER_FRAMES:
            self._game_over("TIME UP")

    # ------------------------------------------------------------------ draw
    def _center_text(self, text: str, y: int, color: int) -> None:
        pyxel.text((SCREEN_W - len(text) * 4) // 2, y, text, color)

    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        else:
            self._draw_playing()

    def _draw_title(self) -> None:
        pyxel.cls(NAVY)
        self._center_text("GLOW CHAIN", 60, YELLOW)
        self._center_text("GLASSBLOWING", 78, WHITE)
        self._center_text("R = REHEAT  SPACE = BLOW", 112, WHITE)
        self._center_text("MATCH THE ORDER COLOR", 130, CYAN)
        self._center_text("COMBO x4 = SUPER BLOW", 146, LIME)
        if (pyxel.frame_count // 30) % 2 == 0:
            self._center_text("PRESS SPACE TO START", 186, GREEN)

    def _draw_game_over(self) -> None:
        pyxel.cls(NAVY)
        self._center_text("GAME OVER", 60, RED)
        self._center_text(self.game_over_reason, 84, YELLOW)
        self._center_text(f"SCORE {self.score}", 108, WHITE)
        self._center_text(f"BEST {self.best_score}", 124, YELLOW)
        self._center_text(f"VESSELS {self.vessels_made}", 140, CYAN)
        self._center_text("PRESS SPACE TO RETRY", 176, GREEN)

    def _draw_playing(self) -> None:
        ox = oy = 0
        if self.shake_frames > 0:
            ox = (pyxel.frame_count * 7) % 6 - 3
            oy = (pyxel.frame_count * 11) % 6 - 3

        pyxel.cls(NAVY)

        self._draw_furnace()
        self._draw_order()
        self._draw_glass(ox, oy)
        self._draw_hud()

        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

        for f in self.floats:
            pyxel.text(int(f.x), int(f.y), f.text, f.color)

        if self.super_timer > 0:
            border_color = RAINBOW[pyxel.frame_count % len(RAINBOW)]
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, border_color)
            self._center_text("SUPER BLOW!", 100, border_color)

    def _draw_furnace(self) -> None:
        pyxel.rect(268, 200, 44, 40, GRAY)
        pyxel.rect(272, 196, 36, 6, BROWN)
        if self.reheating:
            h = 24 + (pyxel.frame_count % 8)
            pyxel.tri(274, 196, 306, 196, 290, 196 - h, ORANGE)
            pyxel.tri(280, 196, 300, 196, 290, 196 - int(h * 0.6), YELLOW)
        else:
            pyxel.tri(282, 196, 298, 196, 290, 186, ORANGE)
            pyxel.tri(286, 196, 294, 196, 290, 190, YELLOW)

    def _draw_vessel(self, x: int, y: int, color: int) -> None:
        pyxel.rect(x - 2, y, 4, 6, color)
        pyxel.tri(x - 6, y + 6, x + 6, y + 6, x - 10, y + 18, color)
        pyxel.tri(x - 6, y + 6, x + 6, y + 6, x + 10, y + 18, color)

    def _draw_order(self) -> None:
        self._center_text("ORDER", 16, WHITE)
        self._draw_vessel(160, 28, self.order_color)
        band = BAND_NAMES[BAND_COLORS.index(self.order_color)]
        self._center_text(band, 52, self.order_color)

    def _draw_glass(self, ox: int, oy: int) -> None:
        radius = int(10 + self.temp * 0.3)
        color = self.band_color(self.temp)
        x = GLASS_X + ox
        y = GLASS_Y + oy
        pyxel.circ(x, y, radius, color)
        pyxel.circb(x, y, radius, WHITE)
        pyxel.circ(x - radius // 3, y - radius // 3, 2, WHITE)
        pyxel.line(x, y + radius, x, SCREEN_H, GRAY)
        pyxel.line(x + 1, y + radius, x + 1, SCREEN_H, GRAY)
        band = BAND_NAMES[self.band_index(self.temp)]
        pyxel.text(x - len(band) * 2, y + radius + 8, band, color)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE {self.score}", WHITE)
        combo_color = YELLOW if self.combo >= 1 else GRAY
        pyxel.text(4, 16, f"COMBO x{self.combo}", combo_color)

        pyxel.text(4, 30, "HEAT", WHITE)
        pyxel.rectb(34, 30, 60, 6, GRAY)
        heat_color = GREEN if self.heat < 50 else (YELLOW if self.heat < 80 else RED)
        fill_w = int(58 * (self.heat / HEAT_CAP))
        if fill_w > 0:
            pyxel.rect(35, 31, fill_w, 4, heat_color)

        remaining = max(0, TIMER_FRAMES - self.frame)
        pyxel.rectb(110, 5, 100, 6, GRAY)
        timer_color = GREEN if remaining > 1800 else (YELLOW if remaining > 600 else RED)
        tfill = int(98 * (remaining / TIMER_FRAMES))
        if tfill > 0:
            pyxel.rect(111, 6, tfill, 4, timer_color)


if __name__ == "__main__":
    Game()
