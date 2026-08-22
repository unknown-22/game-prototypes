"""BEACON — Avalanche Beacon Search & Rescue.

A single-scalar signal-strength meter is your only clue to the location of
buried victims. Walk the snowfield by feel, triangulate the strongest signal,
and DIG at exactly the right spot before the avalanche closes in.
"""

import math
import random
from dataclasses import dataclass
from enum import Enum

import pyxel


# --- Screen / game constants -------------------------------------------------
SCREEN_W = 320
SCREEN_H = 240
DISPLAY_SCALE = 2
FPS = 60

GAME_DURATION = 5400  # avalanche timer (90s)

PLAYER_RADIUS = 5
PLAYER_SPEED = 2.0
_INV_SQRT2 = 1.0 / math.sqrt(2.0)

VICTIM_START = 5
VICTIM_MAX = 8
VICTIM_RADIUS = 6
VICTIM_X_MIN = 20
VICTIM_X_MAX = 300
VICTIM_Y_MIN = 20
VICTIM_Y_MAX = 220

DIG_RADIUS = 14
DIG_TIME = 30
RESCUE_TIME_BONUS = 300
MISS_TIME_PENALTY = 180

ROCK_RADIUS = 10
ROCK_POSITIONS = ((80, 60), (240, 80), (160, 160), (80, 200))
SPECKLE_COUNT = 80


# --- Palette (raw ints) ------------------------------------------------------
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


# --- Pure scoring / timing formulas (module-level, testable) -----------------
def signal_strength(dist: float) -> int:
    """Scalar 0..100 strength for a given distance (no direction)."""
    return max(0, min(100, int(100 - dist * 0.8)))


def combo_multiplier(combo: int) -> float:
    return min(1.0 + combo * 0.5, 4.0)


def rescue_score(combo: int) -> int:
    return int(100 * combo_multiplier(combo))


def spawn_interval(frame: int) -> int:
    return max(300, 720 - frame // 15)


# --- Data types --------------------------------------------------------------
class Phase(Enum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2
    VICTORY = 3


@dataclass
class Victim:
    x: float
    y: float
    rescued: bool = False


@dataclass
class Rock:
    x: float
    y: float
    radius: int


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


# --- Game --------------------------------------------------------------------
class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="BEACON", fps=FPS, display_scale=DISPLAY_SCALE)
        self.reset()
        self.phase = Phase.TITLE
        pyxel.run(self.update, self.draw)

    # -- state ---------------------------------------------------------------
    def reset(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)
        self.phase = Phase.PLAYING
        self.frame = 0
        self.time_left = GAME_DURATION
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.rescued_count = 0
        self.dig_timer = 0
        self.player_x = float(SCREEN_W // 2)
        self.player_y = float(SCREEN_H // 2)
        self.victims: list[Victim] = []
        for _ in range(VICTIM_START):
            self._spawn_victim()
        self.spawn_timer = spawn_interval(0)
        self.rocks = [Rock(float(x), float(y), ROCK_RADIUS) for x, y in ROCK_POSITIONS]
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.speckles = [
            (self.rng.randint(0, SCREEN_W - 1), self.rng.randint(0, SCREEN_H - 1))
            for _ in range(SPECKLE_COUNT)
        ]

    # -- logic (no pyxel input) ----------------------------------------------
    def _move_player(self, dx: int, dy: int) -> None:
        if self.phase != Phase.PLAYING or self.dig_timer > 0:
            return
        if dx != 0 and dy != 0:
            dx = int(math.copysign(1, dx)) if dx else 0
            dy = int(math.copysign(1, dy)) if dy else 0
            self.player_x += dx * PLAYER_SPEED * _INV_SQRT2
            self.player_y += dy * PLAYER_SPEED * _INV_SQRT2
        else:
            self.player_x += dx * PLAYER_SPEED
            self.player_y += dy * PLAYER_SPEED

        self.player_x = min(max(self.player_x, PLAYER_RADIUS), SCREEN_W - PLAYER_RADIUS)
        self.player_y = min(max(self.player_y, PLAYER_RADIUS), SCREEN_H - PLAYER_RADIUS)

        for rock in self.rocks:
            ddx = self.player_x - rock.x
            ddy = self.player_y - rock.y
            dist = math.hypot(ddx, ddy)
            min_dist = PLAYER_RADIUS + rock.radius
            if dist < min_dist:
                if dist == 0:
                    ddx, ddy, dist = 1.0, 0.0, 1.0
                push = (min_dist - dist) / dist
                self.player_x += ddx * push
                self.player_y += ddy * push

        self.player_x = min(max(self.player_x, PLAYER_RADIUS), SCREEN_W - PLAYER_RADIUS)
        self.player_y = min(max(self.player_y, PLAYER_RADIUS), SCREEN_H - PLAYER_RADIUS)

    def _nearest_distance(self, px: float, py: float) -> float:
        best: float | None = None
        for v in self.victims:
            if v.rescued:
                continue
            d = math.hypot(px - v.x, py - v.y)
            if best is None or d < best:
                best = d
        return best if best is not None else float("inf")

    def _signal_at(self, px: float, py: float) -> int:
        d = self._nearest_distance(px, py)
        if math.isinf(d):
            return 0
        return signal_strength(d)

    def _start_dig(self) -> None:
        if self.dig_timer <= 0:
            self.dig_timer = DIG_TIME

    def _resolve_dig(self) -> None:
        nearest: Victim | None = None
        nearest_d: float | None = None
        for v in self.victims:
            if v.rescued:
                continue
            d = math.hypot(self.player_x - v.x, self.player_y - v.y)
            if nearest_d is None or d < nearest_d:
                nearest_d = d
                nearest = v

        if nearest is not None and nearest_d is not None and nearest_d <= DIG_RADIUS:
            nearest.rescued = True
            self.rescued_count += 1
            self.combo += 1
            self.score += rescue_score(self.combo)
            self.max_combo = max(self.max_combo, self.combo)
            self.time_left += RESCUE_TIME_BONUS
            self._spawn_particles(nearest.x, nearest.y, YELLOW, 24)
            self.floating_texts.append(
                FloatingText(nearest.x, nearest.y - 8, "RESCUED!", 45, YELLOW)
            )
        else:
            self.combo = 0
            self.time_left -= MISS_TIME_PENALTY
            self._spawn_particles(self.player_x, self.player_y, GRAY, 10)
            self.floating_texts.append(
                FloatingText(self.player_x, self.player_y - 10, "MISS", 45, GRAY)
            )

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            ang = self.rng.uniform(0.0, 2.0 * math.pi)
            spd = self.rng.uniform(0.5, 2.0)
            life = self.rng.randint(15, 30)
            self.particles.append(
                Particle(x, y, math.cos(ang) * spd, math.sin(ang) * spd, life, color)
            )

    def _spawn_victim(self) -> None:
        if len(self.victims) >= VICTIM_MAX:
            return
        self.victims.append(
            Victim(
                x=float(self.rng.randint(VICTIM_X_MIN, VICTIM_X_MAX)),
                y=float(self.rng.randint(VICTIM_Y_MIN, VICTIM_Y_MAX)),
            )
        )

    def _update_timers(self) -> None:
        if self.phase != Phase.PLAYING:
            return
        self.frame += 1
        self.time_left -= 1
        if self.dig_timer > 0:
            self.dig_timer -= 1
            if self.dig_timer == 0:
                self._resolve_dig()
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self._spawn_victim()
            self.spawn_timer = spawn_interval(self.frame)

    def _check_game_over(self) -> None:
        if self.phase != Phase.PLAYING:
            return
        if self.time_left <= 0:
            self.time_left = 0
            self.phase = Phase.GAME_OVER
        elif self.victims and all(v.rescued for v in self.victims):
            self.phase = Phase.VICTORY

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vx *= 0.95
            p.vy *= 0.95
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for t in self.floating_texts:
            t.y -= 0.5
            t.life -= 1
        self.floating_texts = [t for t in self.floating_texts if t.life > 0]

    # -- input + phase dispatch (pyxel input here only) -----------------------
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.phase = Phase.PLAYING
        elif self.phase == Phase.PLAYING:
            dx = 0
            dy = 0
            if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
                dx -= 1
            if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
                dx += 1
            if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
                dy -= 1
            if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
                dy += 1
            self._move_player(dx, dy)
            if pyxel.btnp(pyxel.KEY_SPACE):
                self._start_dig()
            self._update_timers()
            self._update_particles()
            self._update_floating_texts()
            self._check_game_over()
        elif self.phase in (Phase.GAME_OVER, Phase.VICTORY):
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.phase = Phase.TITLE
            elif pyxel.btnp(pyxel.KEY_R):
                self.reset()
                self.phase = Phase.PLAYING

    # -- rendering ------------------------------------------------------------
    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        else:
            self._draw_end()

    def _draw_snowfield(self) -> None:
        pyxel.cls(LIGHT_BLUE)
        for x, y in self.speckles:
            pyxel.pset(x, y, WHITE)
        for rock in self.rocks:
            pyxel.circ(int(rock.x), int(rock.y), rock.radius, BROWN)

    def _draw_title(self) -> None:
        pyxel.cls(BLACK)
        pyxel.text(128, 90, "BEACON", WHITE)
        pyxel.text(92, 120, "ARROWS move  SPACE dig", WHITE)
        pyxel.text(120, 140, "Press SPACE", YELLOW)

    def _draw_playing(self) -> None:
        self._draw_snowfield()

        signal = self._signal_at(self.player_x, self.player_y)

        if self.dig_timer > 0:
            pyxel.circb(int(self.player_x), int(self.player_y), DIG_RADIUS, CYAN)

        pyxel.circ(int(self.player_x), int(self.player_y), PLAYER_RADIUS, RED)

        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)
        for t in self.floating_texts:
            pyxel.text(int(t.x), int(t.y), t.text, t.color)

        self._draw_hud(signal)

    def _draw_hud(self, signal: int) -> None:
        pyxel.text(4, 10, f"SCORE {self.score}", WHITE)
        pyxel.text(4, 20, f"COMBO {self.combo}", WHITE)
        pyxel.text(4, 30, f"MAX {self.max_combo}", WHITE)
        pyxel.text(200, 10, f"RESCUED {self.rescued_count}/{len(self.victims)}", WHITE)

        # avalanche timer bar (top)
        pyxel.rect(4, 2, 312, 5, NAVY)
        frac = min(max(self.time_left / GAME_DURATION, 0.0), 1.0)
        tcolor = RED if self.time_left < 600 else GREEN
        pyxel.rect(4, 2, int(312 * frac), 5, tcolor)

        # signal bar (bottom)
        if signal < 33:
            bar_color = GREEN
        elif signal < 66:
            bar_color = YELLOW
        else:
            bar_color = RED
        pyxel.text(4, 226, "SIGNAL", WHITE)
        pyxel.rect(44, 226, 200, 8, NAVY)
        pyxel.rect(44, 226, int(200 * signal / 100), 8, bar_color)
        pyxel.rectb(44, 226, 200, 8, WHITE)

        # beep-rate pulse (flashes faster near target)
        beep_interval = max(4, 60 - signal // 2)
        if self.frame % beep_interval < 2:
            pyxel.rect(248, 226, 6, 8, WHITE)

    def _draw_end(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.VICTORY:
            pyxel.text(128, 80, "VICTORY!", YELLOW)
        else:
            pyxel.text(124, 80, "GAME OVER", RED)
        pyxel.text(100, 105, f"SCORE {self.score}", WHITE)
        pyxel.text(
            92, 115, f"RESCUED {self.rescued_count}/{len(self.victims)}", WHITE
        )
        pyxel.text(112, 125, f"MAX COMBO {self.max_combo}", WHITE)
        pyxel.text(80, 150, "SPACE menu  R retry", WHITE)


if __name__ == "__main__":
    Game()
