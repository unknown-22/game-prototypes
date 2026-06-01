from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ---------------------------------------------------------------------------
# Constants
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

SCREEN_W = 320
SCREEN_H = 240

GEM_RADIUS = 6
ROCK_RADIUS = 8
PLAYER_RADIUS = 8

SUPER_DURATION = 300
MAX_HEAT = 5
GAME_DURATION = 3600
WAVE_AMPLITUDE_BASE = 30
WAVE_FREQUENCY = 0.02
GEM_SPAWN_INTERVAL = 45
ROCK_SPAWN_INTERVAL = 120
COMBO_SUPER_THRESHOLD = 5
PLAYER_X = 80
PLAYER_OFFSET_RANGE = 20
PLAYER_SPEED = 2.0

GEM_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
RAINBOW: list[int] = [RED, ORANGE, YELLOW, GREEN, CYAN, PURPLE]


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Gem:
    x: float
    y: float
    color: int
    collected: bool = False
    radius: int = GEM_RADIUS


@dataclass
class Rock:
    x: float
    y: float
    radius: int = ROCK_RADIUS


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


# ---------------------------------------------------------------------------
# Game — core logic (testable without Pyxel)
# ---------------------------------------------------------------------------


class Game:
    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.reset()

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.combo_color: int | None = None
        self.max_combo: int = 0
        self.heat: int = 0
        self.timer: int = GAME_DURATION
        self.elapsed: int = 0
        self.player_offset: float = 0.0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.gems: list[Gem] = []
        self.rocks: list[Rock] = []
        self.particles: list[Particle] = []
        self.gem_spawn_timer: int = 0
        self.rock_spawn_timer: int = 0
        self.wave_phase_offset: float = 0.0

    # --- Wave ---

    def wave_amplitude(self) -> float:
        amp = WAVE_AMPLITUDE_BASE + self.elapsed / 120.0
        return min(amp, 60.0)

    def wave_y_at(self, x: float) -> float:
        amp = self.wave_amplitude()
        return SCREEN_H // 2 + amp * math.sin(WAVE_FREQUENCY * (x + self.wave_phase_offset))

    def player_y(self) -> float:
        return self.wave_y_at(PLAYER_X) + self.player_offset

    # --- Spawning ---

    def _spawn_speed(self) -> float:
        return 1.0 + self.elapsed / 800.0

    def spawn_gem(self) -> None:
        x = SCREEN_W + 10.0
        y = self.wave_y_at(x) + self.rng.uniform(-15, 15)
        color = self.rng.choice(GEM_COLORS)
        self.gems.append(Gem(x=x, y=y, color=color))

    def spawn_rock(self) -> None:
        x = SCREEN_W + 10.0
        y = self.wave_y_at(x) + self.rng.uniform(-10, 10)
        self.rocks.append(Rock(x=x, y=y))

    # --- Collision ---

    def _circle_collision(
        self, x1: float, y1: float, r1: float, x2: float, y2: float, r2: float
    ) -> bool:
        dx = x1 - x2
        dy = y1 - y2
        return dx * dx + dy * dy < (r1 + r2) * (r1 + r2)

    # --- Collect Gem ---

    def _spawn_collect_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(1.0, 3.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = self.rng.randint(10, 15)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def collect_gem(self, idx: int) -> None:
        gem = self.gems[idx]
        gem.collected = True

        if self.super_mode:
            points = (10 + self.combo * 5) * 3
            self.score += points
            self._spawn_collect_particles(gem.x, gem.y, gem.color, 6)
            return

        if self.combo_color is None:
            self.combo_color = gem.color
            self.combo = 1
            self.score += 10
        elif gem.color == self.combo_color:
            self.combo += 1
            self.score += 10 + self.combo * 5
        else:
            self.combo = 0
            self.combo_color = gem.color
            self.combo = 1
            self.score += 10

        if self.combo > self.max_combo:
            self.max_combo = self.combo

        self._spawn_collect_particles(gem.x, gem.y, gem.color, 6)

        if not self.super_mode and self.combo >= COMBO_SUPER_THRESHOLD:
            self._activate_super()

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        for c in RAINBOW:
            self.particles.append(
                Particle(
                    x=self.player_y_to_screen_x(),
                    y=self.player_y(),
                    vx=self.rng.uniform(-2, 2),
                    vy=self.rng.uniform(-3, -1),
                    life=20,
                    color=c,
                )
            )

    # --- Hit Rock ---

    def _spawn_rock_particles(self, x: float, y: float) -> None:
        for _ in range(10):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(1.5, 4.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = self.rng.randint(10, 18)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=RED))

    def hit_rock(self, idx: int) -> bool:
        rock = self.rocks[idx]
        if self.super_mode:
            self.score += 50
            self._spawn_rock_particles(rock.x, rock.y)
            return True
        else:
            self.heat += 1
            self.combo = 0
            self.combo_color = None
            self._spawn_rock_particles(rock.x, rock.y)
            return True

    def player_y_to_screen_x(self) -> float:
        return PLAYER_X

    # --- Update (game tick, called each frame from Pyxel) ---

    def update(self) -> None:
        if self.phase != Phase.PLAYING:
            return

        self.elapsed += 1
        self.timer -= 1
        self.wave_phase_offset += 0.3

        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.combo = 0
                self.combo_color = None

        # Spawn gems
        self.gem_spawn_timer += 1
        if self.gem_spawn_timer >= GEM_SPAWN_INTERVAL and len(self.gems) < 8:
            self.gem_spawn_timer = 0
            self.spawn_gem()

        # Spawn rocks
        self.rock_spawn_timer += 1
        if self.rock_spawn_timer >= ROCK_SPAWN_INTERVAL and self._count_active_rocks() < 3:
            self.rock_spawn_timer = 0
            self.spawn_rock()

        # Move gems
        speed = self._spawn_speed()
        for gem in self.gems:
            if not gem.collected:
                gem.x -= speed
                gem.y = self.wave_y_at(gem.x) + (gem.y - self.wave_y_at(gem.x + speed))

        # Move rocks
        for rock in self.rocks:
            rock.x -= speed
            rock.y = self.wave_y_at(rock.x) + (rock.y - self.wave_y_at(rock.x + speed))

        # Check gem collection
        px = PLAYER_X
        py = self.player_y()
        for i, gem in enumerate(self.gems):
            if gem.collected:
                continue
            if self._circle_collision(px, py, PLAYER_RADIUS, gem.x, gem.y, gem.radius):
                self.collect_gem(i)

        # Check rock collision
        for i, rock in enumerate(self.rocks):
            if self._circle_collision(px, py, PLAYER_RADIUS, rock.x, rock.y, rock.radius):
                if self.hit_rock(i):
                    self.rocks.pop(i)
                    break  # Only one rock per frame

        # Update particles
        for p in self.particles:
            p.life -= 1
            p.x += p.vx
            p.y += p.vy

        # Cleanup
        self.gems = [g for g in self.gems if not g.collected and g.x > -10]
        self.rocks = [r for r in self.rocks if r.x > -15]
        self.particles = [p for p in self.particles if p.life > 0]

        # Game over checks
        if self.heat >= MAX_HEAT or self.timer <= 0:
            self.phase = Phase.GAME_OVER

    def _count_active_rocks(self) -> int:
        return len(self.rocks)

    def update_player(self, up: bool, down: bool) -> None:
        if up and not down:
            self.player_offset = min(self.player_offset + PLAYER_SPEED, PLAYER_OFFSET_RANGE)
        elif down and not up:
            self.player_offset = max(self.player_offset - PLAYER_SPEED, -PLAYER_OFFSET_RANGE)
        self.player_offset = max(-PLAYER_OFFSET_RANGE, min(PLAYER_OFFSET_RANGE, self.player_offset))


# ---------------------------------------------------------------------------
# App — Pyxel rendering wrapper
# ---------------------------------------------------------------------------


class App:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Wave Chain", display_scale=2)
        self.game = Game()
        pyxel.run(self.update, self.draw)

    # --- Update ---

    def update(self) -> None:
        game = self.game

        if game.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                game.reset()
                game.phase = Phase.PLAYING
            return

        if game.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                game.reset()
                game.phase = Phase.PLAYING
            return

        if game.phase == Phase.PLAYING:
            up = pyxel.btn(pyxel.KEY_UP)
            down = pyxel.btn(pyxel.KEY_DOWN)
            game.update_player(up, down)
            game.update()

    # --- Draw ---

    def draw(self) -> None:
        pyxel.cls(BLACK)
        game = self.game

        if game.phase == Phase.TITLE:
            self._draw_title()
        elif game.phase == Phase.PLAYING:
            self._draw_playing()
        elif game.phase == Phase.GAME_OVER:
            self._draw_playing()
            self._draw_game_over()

    def _draw_background(self) -> None:
        wave_y_center = SCREEN_H // 2

        # Sky gradient (top half)
        for y in range(0, wave_y_center):
            t = y / wave_y_center
            r = int(LIGHT_BLUE + (WHITE - LIGHT_BLUE) * t)
            r = max(0, min(15, r))
            pyxel.rect(0, y, SCREEN_W, 1, LIGHT_BLUE)

        # Water (bottom half)
        pyxel.rect(0, wave_y_center, SCREEN_W, SCREEN_H - wave_y_center, DARK_BLUE)

    def _draw_wave(self) -> None:
        game = self.game
        amp = game.wave_amplitude()
        center_y = SCREEN_H // 2

        # Draw wave surface as a line
        prev_x = 0
        prev_y = center_y + amp * math.sin(WAVE_FREQUENCY * (0 + game.wave_phase_offset))
        for x in range(1, SCREEN_W + 1):
            y = center_y + amp * math.sin(WAVE_FREQUENCY * (x + game.wave_phase_offset))
            pyxel.line(prev_x, int(prev_y), x, int(y), WHITE)
            prev_x, prev_y = x, y

        # Fill water below the wave
        for x in range(SCREEN_W):
            wy = int(center_y + amp * math.sin(WAVE_FREQUENCY * (x + game.wave_phase_offset)))
            if wy < SCREEN_H:
                pyxel.line(x, wy, x, SCREEN_H, DARK_BLUE)

    def _draw_player(self) -> None:
        game = self.game
        px = PLAYER_X
        py = int(game.player_y())

        if game.super_mode:
            idx = (pyxel.frame_count // 4) % len(RAINBOW)
            color = RAINBOW[idx]
        else:
            color = WHITE

        pyxel.circ(px, py, PLAYER_RADIUS, color)
        # Surfboard
        pyxel.rect(px - 10, py + PLAYER_RADIUS, 20, 2, color)

    def _draw_gems(self) -> None:
        for gem in self.game.gems:
            if not gem.collected:
                gx = int(gem.x)
                gy = int(gem.y)
                if -GEM_RADIUS < gx < SCREEN_W + GEM_RADIUS:
                    pyxel.circ(gx, gy, GEM_RADIUS, gem.color)
                    pyxel.circ(gx - 2, gy - 2, 1, WHITE)

    def _draw_rocks(self) -> None:
        for rock in self.game.rocks:
            rx = int(rock.x)
            ry = int(rock.y)
            if -ROCK_RADIUS < rx < SCREEN_W + ROCK_RADIUS:
                pyxel.circ(rx, ry, ROCK_RADIUS, BROWN)
                pyxel.circ(rx - 2, ry - 2, 2, BLACK)

    def _draw_particles(self) -> None:
        for p in self.game.particles:
            px = int(p.x)
            py = int(p.y)
            if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
                pyxel.circ(px, py, 1, p.color)

    def _draw_hud(self) -> None:
        game = self.game

        # Score (top-left)
        pyxel.text(4, 4, f"SCORE:{game.score}", WHITE)

        # Combo (top-center)
        if game.combo > 0:
            combo_str = f"COMBO x{game.combo}"
            combo_color = game.combo_color if game.combo_color else WHITE
            w = len(combo_str) * 4
            pyxel.text(SCREEN_W // 2 - w, 4, combo_str, combo_color)

        # Timer (top-right)
        seconds = max(0, game.timer // 60)
        timer_str = f"{seconds:02d}s"
        pyxel.text(SCREEN_W - 30, 4, timer_str, WHITE)

        # SUPER SURF indicator
        if game.super_mode:
            s = game.super_timer // 60
            super_str = f"SUPER {s}s"
            pyxel.text(SCREEN_W - 60, 14, super_str, CYAN)

        # HEAT (bottom-left)
        heat_str = "HEAT:" + ">" * game.heat + "-" * (MAX_HEAT - game.heat)
        pyxel.text(4, SCREEN_H - 10, heat_str, RED)

    def _draw_title(self) -> None:
        self._draw_background()
        self._draw_wave()

        pyxel.text(SCREEN_W // 2 - 40, 60, "WAVE CHAIN", WHITE)
        pyxel.text(SCREEN_W // 2 - 44, 80, "Ride the wave!", CYAN)
        pyxel.text(SCREEN_W // 2 - 68, 100, "Collect same-color gems", WHITE)
        pyxel.text(SCREEN_W // 2 - 68, 110, "COMBO x5 -> SUPER SURF!", YELLOW)
        pyxel.text(SCREEN_W // 2 - 44, 130, "Avoid rocks!", RED)
        pyxel.text(SCREEN_W // 2 - 78, 150, "UP/DOWN to move", WHITE)
        pyxel.text(SCREEN_W // 2 - 78, 160, "60 seconds time limit", WHITE)
        pyxel.text(SCREEN_W // 2 - 44, 190, "SPACE to start", LIGHT_BLUE)

    def _draw_playing(self) -> None:
        self._draw_background()
        self._draw_wave()
        self._draw_rocks()
        self._draw_gems()
        self._draw_player()
        self._draw_particles()
        self._draw_hud()

    def _draw_game_over(self) -> None:
        pyxel.rect(SCREEN_W // 2 - 80, SCREEN_H // 2 - 40, 160, 80, BLACK)
        pyxel.rectb(SCREEN_W // 2 - 80, SCREEN_H // 2 - 40, 160, 80, WHITE)
        pyxel.text(SCREEN_W // 2 - 28, SCREEN_H // 2 - 30, "GAME OVER", RED)
        pyxel.text(
            SCREEN_W // 2 - 50, SCREEN_H // 2 - 15, f"SCORE: {self.game.score}", WHITE
        )
        pyxel.text(
            SCREEN_W // 2 - 50,
            SCREEN_H // 2 - 5,
            f"MAX COMBO: {self.game.max_combo}",
            YELLOW,
        )
        pyxel.text(SCREEN_W // 2 - 40, SCREEN_H // 2 + 15, "SPACE to retry", LIGHT_BLUE)


def main() -> None:
    App()


if __name__ == "__main__":
    main()
