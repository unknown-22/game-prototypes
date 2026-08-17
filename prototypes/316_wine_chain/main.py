"""WINE CHAIN — Grape Crush & Wine Fermentation (Pyxel Prototype)."""

from __future__ import annotations

import enum
import math
import random
from dataclasses import dataclass

import pyxel

SCREEN_W = 320
SCREEN_H = 240
COLORS: tuple[int, ...] = (8, 11, 5, 10)  # RED, LIME, DARK_BLUE, YELLOW
COLOR_NAMES: tuple[str, ...] = ("RED", "LIME", "BLUE", "GOLD")
NUM_GRAPES = 8
GRAPE_XS = (24, 60, 96, 132, 168, 204, 240, 276)
GRAPE_Y = 120
GRAPE_RADIUS = 10
CRUSHER_Y = 50
TANK_MAX = 6
BOTTLE_COOLDOWN = 45
SUPER_DURATION = 300
SUPER_THRESHOLD = 4
HEAT_MAX = 100
GAME_DURATION = 3600
HEAT_DECAY = 0.02
MISMATCH_HEAT = 15
OVERFLOW_HEAT = 20
BASE_SCORE = 10

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


class Phase(enum.Enum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


@dataclass
class Grape:
    color: int
    x: int
    y: int
    alive: bool = True
    respawn_timer: int = 0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class FloatText:
    x: float
    y: float
    text: str
    life: int
    color: int


class Game:
    def __init__(self) -> None:
        self._rng = random.Random()
        self._init_state()

    def _init_state(self) -> None:
        self.phase = Phase.TITLE
        self.frame = 0
        self.score = 0
        self.best_score = getattr(self, "best_score", 0)
        self.combo = 0
        self.max_combo = 0
        self.juice = 0
        self.heat = 0.0
        self.crusher_index = 0
        self.crusher_color = COLORS[0]
        self.cycle_timer = self._cycle_interval()
        self.super_mode = False
        self.super_timer = 0
        self.bottle_cooldown = 0
        self.grapes = [
            Grape(color=self._rng.choice(COLORS), x=GRAPE_XS[i], y=GRAPE_Y)
            for i in range(NUM_GRAPES)
        ]
        self.particles = []
        self.float_texts = []
        self.shake_frames = 0

    # ---- escalation ----

    def _cycle_interval(self) -> int:
        return max(12, 20 - (self.frame // 450))

    def _respawn_delay(self) -> int:
        return max(25, 60 - (self.frame // 100))

    # ---- core logic (pure, testable) ----

    def _handle_crush(self, index: int) -> str:
        if self.phase != Phase.PLAYING:
            return "blocked"
        if self.bottle_cooldown > 0:
            return "blocked"
        if not (0 <= index < NUM_GRAPES):
            return "blocked"
        grape = self.grapes[index]
        if not grape.alive:
            return "blocked"

        matched = (grape.color == self.crusher_color) or self.super_mode

        if self.juice >= TANK_MAX:
            self.heat += OVERFLOW_HEAT
            self.combo = 0
            self._kill_grape(index)
            self._spawn_particles(grape.x, grape.y, 12, ORANGE)
            self._spawn_float_text(grape.x, grape.y, "OVERFLOW!", ORANGE)
            self.shake_frames = 8
            self._check_game_over()
            return "overflow"

        if matched:
            self.juice += 1
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            mult = 3 if self.super_mode else 1
            gained = BASE_SCORE * self.combo * mult
            self.score += gained
            self._kill_grape(index)
            self._spawn_particles(grape.x, grape.y, 8, self.crusher_color)
            self._spawn_float_text(grape.x, grape.y, f"+{gained}", self.crusher_color)
            if (not self.super_mode) and self.combo >= SUPER_THRESHOLD:
                self._activate_super()
                self._super_bloom()
            self._check_game_over()
            return "match"

        self.heat += MISMATCH_HEAT
        self.combo = 0
        self._spawn_particles(grape.x, grape.y, 4, RED)
        self._spawn_float_text(grape.x, grape.y, "WRONG!", RED)
        self._check_game_over()
        return "mismatch"

    def _bottle(self) -> int:
        if self.phase != Phase.PLAYING or self.bottle_cooldown > 0:
            return 0
        gained = self.juice * self.combo * BASE_SCORE
        if gained > 0:
            self.score += gained
            self._spawn_float_text(296, 80, f"+{gained} BOTTLED!", LIME)
            self._spawn_particles(302, 180, 16, LIME)
        self.juice = 0
        self.combo = 0
        self.bottle_cooldown = BOTTLE_COOLDOWN
        self.shake_frames = 12
        return gained

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self._spawn_particles(160, 80, 20, PINK)

    def _super_bloom(self) -> None:
        alive = [i for i in range(NUM_GRAPES) if self.grapes[i].alive]
        self._rng.shuffle(alive)
        for index in alive[:2]:
            if self.juice >= TANK_MAX:
                break
            self.juice += 1
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            self.score += BASE_SCORE * self.combo * 3
            grape = self.grapes[index]
            self._kill_grape(index)
            self._spawn_particles(grape.x, grape.y, 6, grape.color)
            self._spawn_float_text(grape.x, grape.y, "BLOOM!", grape.color)

    def _check_game_over(self) -> None:
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            self.best_score = max(self.best_score, self.score)

    def _update_heat(self) -> None:
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            self.best_score = max(self.best_score, self.score)
            return
        if not self.super_mode:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_timer(self) -> None:
        self.frame += 1
        if self.frame >= GAME_DURATION:
            self.phase = Phase.GAME_OVER
            self.best_score = max(self.best_score, self.score)

    def _kill_grape(self, index: int) -> None:
        grape = self.grapes[index]
        grape.alive = False
        grape.respawn_timer = self._respawn_delay()

    def _spawn_grape(self, index: int) -> None:
        grape = self.grapes[index]
        grape.color = self._rng.choice(COLORS)
        grape.alive = True
        grape.respawn_timer = 0

    def _update_grapes(self) -> None:
        for i in range(NUM_GRAPES):
            grape = self.grapes[i]
            if not grape.alive:
                grape.respawn_timer -= 1
                if grape.respawn_timer <= 0:
                    self._spawn_grape(i)

    def _update_cycle(self) -> None:
        self.cycle_timer -= 1
        if self.cycle_timer <= 0:
            self.crusher_index = (self.crusher_index + 1) % len(COLORS)
            self.crusher_color = COLORS[self.crusher_index]
            self.cycle_timer = self._cycle_interval()

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_float_texts(self) -> None:
        for t in self.float_texts:
            t.y -= 0.5
            t.life -= 1
        self.float_texts = [t for t in self.float_texts if t.life > 0]

    def _update_super(self) -> None:
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False

    def _update_bottle_cooldown(self) -> None:
        if self.bottle_cooldown > 0:
            self.bottle_cooldown -= 1

    # ---- effects helpers ----

    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, 6.2832)
            speed = self._rng.uniform(0.5, 2.5)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=int(self._rng.uniform(10, 25)),
                    color=color,
                )
            )

    def _spawn_float_text(self, x: float, y: float, text: str, color: int) -> None:
        self.float_texts.append(FloatText(x=x, y=y, text=text, life=40, color=color))

    # ---- input ----

    def _grape_at(self, x: int, y: int) -> int | None:
        for i in range(NUM_GRAPES):
            grape = self.grapes[i]
            dx = x - grape.x
            dy = y - grape.y
            if dx * dx + dy * dy <= (GRAPE_RADIUS + 4) ** 2:
                return i
        return None

    # ---- update / draw ----

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self._init_state()
                self.phase = Phase.PLAYING
        elif self.phase == Phase.PLAYING:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                idx = self._grape_at(pyxel.mouse_x, pyxel.mouse_y)
                if idx is not None:
                    self._handle_crush(idx)
            if pyxel.btnp(pyxel.KEY_B):
                self._bottle()
            self._update_cycle()
            self._update_grapes()
            self._update_heat()
            self._update_timer()
            self._update_super()
            self._update_bottle_cooldown()
            self._update_particles()
            self._update_float_texts()
            if self.shake_frames > 0:
                self.shake_frames -= 1
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_R):
                self._init_state()
                self.phase = Phase.PLAYING

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.shake_frames > 0:
            ox = self._rng.randint(-2, 2)
            oy = self._rng.randint(-2, 2)
            pyxel.camera(ox, oy)
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(96, 60, "WINE CHAIN", YELLOW)
        pyxel.text(56, 84, "Crush grapes, fill the tank,", WHITE)
        pyxel.text(56, 96, "BOTTLE the wine!", WHITE)
        pyxel.text(60, 130, "CLICK: crush grape", GRAY)
        pyxel.text(60, 142, "B: bottle", GRAY)
        pyxel.text(60, 154, "ENTER: start", GRAY)
        pyxel.text(40, 180, "Match the crusher color to", WHITE)
        pyxel.text(40, 192, "build COMBO!", WHITE)

    def _draw_playing(self) -> None:
        pyxel.text(4, 4, f"SCORE {self.score}", WHITE)
        pyxel.text(4, 14, f"COMBO x{self.combo}", PINK)
        pyxel.text(4, 24, f"BEST {self.best_score}", GRAY)

        # timer bar
        pyxel.text(4, 34, "TIME", WHITE)
        frac = max(0.0, 1.0 - self.frame / GAME_DURATION)
        pyxel.rect(40, 34, int(200 * frac), 6, GREEN)

        # crusher
        pyxel.text(140, CRUSHER_Y - 14, "PRESS", WHITE)
        pyxel.rect(144, CRUSHER_Y, 32, 32, self.crusher_color)
        pyxel.rectb(144, CRUSHER_Y, 32, 32, WHITE)

        # grapes
        for grape in self.grapes:
            if grape.alive:
                pyxel.circ(grape.x, grape.y, GRAPE_RADIUS, grape.color)
                pyxel.circb(grape.x, grape.y, GRAPE_RADIUS, WHITE)
            else:
                pyxel.circb(grape.x, grape.y, GRAPE_RADIUS, GRAY)

        # tank
        pyxel.text(288, 160, "TANK", WHITE)
        pyxel.rectb(296, 172, 12, 60, WHITE)
        for i in range(self.juice):
            pyxel.rect(297, 229 - i * 9, 10, 8, LIME)
        if self.juice >= TANK_MAX:
            pyxel.text(280, 200, "FULL!", RED)

        # heat bar
        pyxel.text(4, 220, "HEAT", WHITE)
        heat_color = GREEN if self.heat < 40 else YELLOW if self.heat < 70 else RED
        pyxel.rect(40, 220, int(self.heat * 2), 6, heat_color)
        pyxel.rectb(40, 220, 200, 6, GRAY)

        # super
        if self.super_mode:
            pyxel.text(120, 60, "SUPER FERMENT!", PINK)

        # cooldown
        if self.bottle_cooldown > 0:
            pyxel.text(200, 4, "COOLING...", CYAN)

        self._draw_particles()
        self._draw_float_texts()

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_float_texts(self) -> None:
        for t in self.float_texts:
            pyxel.text(int(t.x), int(t.y), t.text, t.color)

    def _draw_game_over(self) -> None:
        pyxel.text(112, 60, "GAME OVER", RED)
        reason = "VINEGAR RUIN!" if self.heat >= HEAT_MAX else "TIME UP"
        pyxel.text(120, 80, reason, WHITE)
        pyxel.text(96, 110, f"SCORE {self.score}", YELLOW)
        pyxel.text(96, 130, f"BEST {self.best_score}", WHITE)
        pyxel.text(96, 150, f"COMBO x{self.max_combo}", PINK)
        pyxel.text(96, 180, "ENTER/R: retry", GRAY)


def run() -> None:
    pyxel.init(SCREEN_W, SCREEN_H, title="WINE CHAIN")
    game = Game()
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    run()
