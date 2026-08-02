from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WIDTH = 320
HEIGHT = 240
FPS = 30

SHIFT_DURATION = 900  # 30s
SUPER_DURATION = 150  # 5s
GAME_DURATION = 1800  # 60s
AUTO_TICK_INTERVAL = 30
SUPER_AUTO_TICK = 15
HEAT_MISMATCH = 15.0
HEAT_AUTO_RATE = 0.02
HEAT_DECAY_RATE = 0.02
HEAT_CAP = 100.0

SCORE_BASE = 10.0
COMBO_MULT = 0.5
SUPER_MULT = 3.0
COMBO_THRESHOLD = 4

# Pyxel color palette (int constants)
COLOR_BLACK = 0
COLOR_NAVY = 1
COLOR_PURPLE = 2
COLOR_GREEN = 3
COLOR_BROWN = 4
COLOR_DARK_BLUE = 5
COLOR_LIGHT_BLUE = 6
COLOR_WHITE = 7
COLOR_RED = 8
COLOR_ORANGE = 9
COLOR_YELLOW = 10
COLOR_LIME = 11
COLOR_CYAN = 12
COLOR_GRAY = 13
COLOR_PINK = 14
COLOR_PEACH = 15

GEN_COLORS = (COLOR_RED, COLOR_LIME, COLOR_DARK_BLUE, COLOR_YELLOW)

# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class Generator:
    x: int
    y: int
    w: int = 48
    h: int = 48
    color: int = 8
    clicks: int = 0
    auto: bool = False
    auto_timer: int = 0
    pulse: float = 0.0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int
    size: int = 2


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int
    vy: float = -0.5


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------


class Game:
    def __init__(self) -> None:
        self._frame_count: int = 0
        self.generators: list[Generator] = []
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.best_score: int = 0
        self.heat: float = 0.0
        self.super_timer: int = 0
        self.super_mult: float = 1.0
        self.game_timer: int = 0
        self.shift_timer: int = 0
        self.active_color: int = -1
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.phase: Phase = Phase.TITLE
        self._rng: random.Random = random.Random()

        pyxel.init(WIDTH, HEIGHT, title="IDLE SURGE", fps=FPS)
        self.reset()
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------
    # Reset / state
    # ------------------------------------------------------------------

    def reset(self) -> None:
        self._frame_count = 0
        self.generators = [
            Generator(x=40, y=120, color=GEN_COLORS[0]),
            Generator(x=100, y=120, color=GEN_COLORS[1]),
            Generator(x=160, y=120, color=GEN_COLORS[2]),
            Generator(x=220, y=120, color=GEN_COLORS[3]),
        ]
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.heat = 0.0
        self.super_timer = 0
        self.super_mult = 1
        self.game_timer = GAME_DURATION
        self.shift_timer = SHIFT_DURATION
        self.active_color = -1
        self.particles.clear()
        self.floating_texts.clear()

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------

    def update(self) -> None:
        if self.phase is Phase.TITLE:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.phase = Phase.PLAYING
                self.reset()
            return

        if self.phase is Phase.GAME_OVER:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.phase = Phase.PLAYING
                self.reset()
            return

        # --- PLAYING --------------------------------------------------
        self._frame_count += 1
        mx = pyxel.mouse_x
        my = pyxel.mouse_y

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            gen = self._find_gen_at(mx, my)
            if gen is not None:
                self._click_gen(gen)

        self._update_timers()
        self._update_auto_gens()
        self._update_super_surge_tick()
        self._update_heat()
        self._update_particles()
        self._update_floating_texts()

        for gen in self.generators:
            gen.pulse = max(0.0, gen.pulse - 0.1)

    # ------------------------------------------------------------------
    # Game-logic methods  (testable — no pyxel calls)
    # ------------------------------------------------------------------

    def _find_gen_at(self, mx: int, my: int) -> Generator | None:
        for gen in self.generators:
            left = gen.x - gen.w // 2
            right = gen.x + gen.w // 2
            top = gen.y - gen.h // 2
            bottom = gen.y + gen.h // 2
            if left <= mx <= right and top <= my <= bottom:
                return gen
        return None

    def _click_gen(self, gen: Generator) -> None:
        if self.super_timer > 0:
            self._score_hit(gen)
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            self._spawn_click_particles(gen)
            self._spawn_floating_score(gen)
            if self.combo > 0:
                self._spawn_combo_text(gen)
            self._check_super_trigger()
        elif self.active_color == gen.color:
            self._score_hit(gen)
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            gen.clicks += 1
            self._spawn_click_particles(gen)
            self._spawn_floating_score(gen)
            if self.combo > 0:
                self._spawn_combo_text(gen)
            self._check_super_trigger()
        else:
            self.combo = 0
            self.heat = min(HEAT_CAP, self.heat + HEAT_MISMATCH)
            ft = FloatingText(
                x=float(gen.x),
                y=float(gen.y),
                text="WRONG!",
                color=COLOR_RED,
                life=25,
            )
            self.floating_texts.append(ft)

        self.active_color = gen.color
        gen.pulse = 1.0

    def _score_hit(self, gen: Generator) -> None:
        mult = 1.0 + self.combo * COMBO_MULT
        points = SCORE_BASE * mult * self.super_mult
        self.score += int(points)
        gen.clicks += 1

    def _check_super_trigger(self) -> None:
        if self.combo >= COMBO_THRESHOLD and self.super_timer == 0:
            self.super_timer = SUPER_DURATION
            self.super_mult = SUPER_MULT
            if self.phase is Phase.PLAYING:
                ft = FloatingText(
                    x=float(WIDTH // 2),
                    y=float(HEIGHT // 2),
                    text="SUPER SURGE!",
                    color=COLOR_YELLOW,
                    life=45,
                )
                self.floating_texts.append(ft)

    def _update_timers(self) -> None:
        self.game_timer -= 1
        if self.game_timer <= 0:
            self.phase = Phase.GAME_OVER
            if self.score > self.best_score:
                self.best_score = self.score
            return

        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer == 0:
                self.super_mult = 1.0

        self.shift_timer -= 1
        if self.shift_timer <= 0:
            self._assign_auto()
            self.shift_timer = SHIFT_DURATION

    def _update_auto_gens(self) -> None:
        for gen in self.generators:
            if gen.auto:
                gen.auto_timer -= 1
                if gen.auto_timer <= 0:
                    gen.auto_timer = AUTO_TICK_INTERVAL
                    self._score_hit(gen)
                    self.combo += 1
                    self.max_combo = max(self.max_combo, self.combo)
                    self.active_color = gen.color
                    self._check_super_trigger()
                    self._spawn_auto_particles(gen)

    def _update_super_surge_tick(self) -> None:
        if self.super_timer <= 0:
            return
        if self._frame_count % SUPER_AUTO_TICK != 0:
            return
        for gen in self.generators:
            self._score_hit(gen)
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            self.active_color = gen.color
            self._spawn_auto_particles(gen)
        self._check_super_trigger()

    def _update_heat(self) -> None:
        if self.super_timer > 0:
            return

        if self.heat >= HEAT_CAP:
            self.phase = Phase.GAME_OVER
            if self.score > self.best_score:
                self.best_score = self.score
            ft = FloatingText(
                x=float(WIDTH // 2),
                y=float(HEIGHT // 2),
                text="MELTDOWN!",
                color=COLOR_RED,
                life=60,
            )
            self.floating_texts.append(ft)
            return

        auto_count = sum(1 for g in self.generators if g.auto)
        self.heat -= HEAT_DECAY_RATE
        self.heat += HEAT_AUTO_RATE * auto_count
        self.heat = max(0.0, min(HEAT_CAP, self.heat))

    def _assign_auto(self) -> None:
        if not self.generators:
            return
        best = max(self.generators, key=lambda g: g.clicks)
        if best.clicks > 0:
            best.auto = True
            best.auto_timer = AUTO_TICK_INTERVAL
            ft = FloatingText(
                x=float(best.x),
                y=float(best.y),
                text="AUTO!",
                color=COLOR_CYAN,
                life=40,
            )
            self.floating_texts.append(ft)
        for g in self.generators:
            g.clicks = 0

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.vy -= 0.1
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    # ------------------------------------------------------------------
    # Particle spawn helpers
    # ------------------------------------------------------------------

    def _spawn_click_particles(self, gen: Generator) -> None:
        count = self._rng.randint(5, 8)
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x=float(gen.x),
                    y=float(gen.y),
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    color=gen.color,
                    life=self._rng.randint(15, 25),
                )
            )

    def _spawn_auto_particles(self, gen: Generator) -> None:
        count = self._rng.randint(3, 5)
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 1.5)
            self.particles.append(
                Particle(
                    x=float(gen.x),
                    y=float(gen.y),
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    color=gen.color,
                    life=self._rng.randint(10, 18),
                    size=1,
                )
            )

    def _spawn_floating_score(self, gen: Generator) -> None:
        mult = 1.0 + self.combo * COMBO_MULT
        pts = int(SCORE_BASE * mult * self.super_mult)
        self.floating_texts.append(
            FloatingText(
                x=float(gen.x),
                y=float(gen.y),
                text=f"+{pts}",
                color=gen.color,
                life=30,
            )
        )

    def _spawn_combo_text(self, gen: Generator) -> None:
        self.floating_texts.append(
            FloatingText(
                x=float(gen.x),
                y=float(gen.y) - 10,
                text=f"COMBO x{self.combo}",
                color=COLOR_YELLOW,
                life=25,
            )
        )

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self) -> None:
        pyxel.cls(COLOR_BLACK)

        if self.phase is Phase.TITLE:
            self._draw_title()
            return

        if self.phase is Phase.GAME_OVER:
            self._draw_game_over()
            return

        self._draw_playing()

    def _draw_title(self) -> None:
        pyxel.cls(COLOR_NAVY)
        x = WIDTH // 2
        pyxel.text(x - 40, 60, "IDLE SURGE", COLOR_YELLOW)
        pyxel.text(x - 56, 80, "POWER PLANT CLICKER", COLOR_WHITE)
        pyxel.text(x - 68, 110, "Same-color clicks = COMBO!", COLOR_LIME)
        pyxel.text(x - 80, 124, "COMBO x4 = SUPER SURGE (3x score!)", COLOR_CYAN)
        pyxel.text(x - 68, 138, "Top generator = AUTO (idle income!)", COLOR_PEACH)
        pyxel.text(x - 48, 155, "Wrong click = HEAT +" + str(int(HEAT_MISMATCH)), COLOR_RED)
        pyxel.text(x - 52, 172, "HEAT at 100 = MELTDOWN!", COLOR_ORANGE)
        pyxel.text(x - 52, 200, "CLICK TO START", COLOR_WHITE)

    def _draw_playing(self) -> None:
        pyxel.cls(COLOR_NAVY)

        # HUD bar
        pyxel.rect(0, 0, WIDTH, 30, COLOR_BROWN)
        pyxel.text(4, 4, f"SCORE: {self.score}", COLOR_WHITE)
        pyxel.text(4, 14, f"COMBO: x{self.combo}", COLOR_WHITE)
        pyxel.text(4, 12, "", COLOR_WHITE)

        secs = max(0, self.game_timer // FPS)
        pyxel.text(265, 4, f"{secs}s", COLOR_WHITE)

        # Heat bar
        bar_x = 265
        bar_y = 14
        bar_w = 45
        pyxel.rectb(bar_x, bar_y, bar_w, 6, COLOR_WHITE)
        fill = int(bar_w * self.heat / HEAT_CAP)
        hcolor = COLOR_RED if self.heat > 70 else COLOR_ORANGE
        if fill > 0:
            pyxel.rect(bar_x + 1, bar_y + 1, fill - 1, 4, hcolor)

        pyxel.text(bar_x - 30, 14, "HEAT", COLOR_WHITE)

        # SUPER indicator
        if self.super_timer > 0:
            s = self.super_timer / FPS
            pyxel.text(100, 4, f"SUPER {s:.1f}s", COLOR_YELLOW)

        # Generators
        for gen in self.generators:
            pw = gen.w
            ph = gen.h
            if gen.pulse > 0:
                pw = int(gen.w + gen.pulse * 8)
                ph = int(gen.h + gen.pulse * 8)

            left = gen.x - pw // 2
            top = gen.y - ph // 2

            pyxel.rect(left, top, pw, ph, gen.color)

            border_color = COLOR_WHITE if gen.auto else COLOR_GRAY
            pyxel.rectb(left, top, pw, ph, border_color)

            # AUTO orbiting indicator
            if gen.auto:
                orbit_r = 10
                ox = gen.x + int(math.cos(self._frame_count * 0.15) * orbit_r)
                oy = gen.y + int(math.sin(self._frame_count * 0.15) * orbit_r)
                pyxel.circ(ox, oy, 2, COLOR_WHITE)

            # Label
            pyxel.text(gen.x - 6, gen.y - 4, "GEN", COLOR_WHITE)

        # Particles
        for p in self.particles:
            pyxel.circ(int(p.x), int(p.y), p.size, p.color)

        # Floating texts
        for ft in self.floating_texts:
            pyxel.text(int(ft.x - len(ft.text) * 2), int(ft.y), ft.text, ft.color)

    def _draw_game_over(self) -> None:
        pyxel.cls(COLOR_NAVY)
        x = WIDTH // 2
        pyxel.text(x - 30, 80, "GAME OVER", COLOR_RED)
        pyxel.text(x - 48, 100, f"SCORE: {self.score}", COLOR_WHITE)
        pyxel.text(x - 56, 120, f"BEST: {self.best_score}", COLOR_YELLOW)
        pyxel.text(x - 52, 200, "CLICK TO RETRY", COLOR_WHITE)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    Game()
