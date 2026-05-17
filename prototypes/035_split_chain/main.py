"""SPLIT CHAIN — Asteroids-like with color-match chain splitting.

Reinterpreted from game_idea_factory idea #1 (score 31.85):
  "log/replay as asset" → COMBO carries forward into split behavior
  "one-color-per-turn" → bullet color cycling constraint
Also incorporates idea #3's "split across paths → converge → explode" hook:
  same-color asteroid kills produce extra split fragments for chain potential.

Genre: Asteroids-like shooter (not previously in the prototype collection).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


# ── Constants ──
SCREEN_W = 256
SCREEN_H = 256
DISPLAY_SCALE = 2
FPS = 60

# Asteroid sizes
SIZE_LARGE = 0
SIZE_MEDIUM = 1
SIZE_SMALL = 2
ASTEROID_RADII: dict[int, int] = {SIZE_LARGE: 14, SIZE_MEDIUM: 9, SIZE_SMALL: 5}
ASTEROID_SCORES: dict[int, int] = {SIZE_LARGE: 100, SIZE_MEDIUM: 50, SIZE_SMALL: 20}

# Asteroid colors (Pyxel color indices)
COLORS: list[int] = [pyxel.COLOR_RED, pyxel.COLOR_YELLOW, pyxel.COLOR_LIME, pyxel.COLOR_CYAN]
NUM_COLORS: int = len(COLORS)

# Ship
SHIP_RADIUS = 8
SHIP_ROTATE_SPEED = 4.0  # degrees per frame
SHIP_THRUST = 0.12
SHIP_DRAG = 0.99
SHIP_MAX_SPEED = 5.0
SHIP_INVULN_FRAMES = 90
STARTING_LIVES = 3

# Bullet
BULLET_SPEED = 7.0
BULLET_LIFETIME = 50
BULLET_SIZE = 2
SHOOT_COOLDOWN = 12  # frames between shots

# Particles
PARTICLE_COUNT_SMALL = 6
PARTICLE_COUNT_LARGE = 15
PARTICLE_SPEED = 2.5
PARTICLE_LIFE = 25

# Spawning
INITIAL_ASTEROIDS = 5
SPAWN_INTERVAL = 600  # frames (10 seconds)
MAX_ASTEROIDS = 25

# COMBO
COMBO_EXTRA_SPLIT_THRESHOLD = 3
COMBO_BURST_THRESHOLD = 5


# ── Data Classes ──
@dataclass
class Asteroid:
    x: float
    y: float
    vx: float
    vy: float
    radius: int
    color: int
    size: int


@dataclass
class Bullet:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int = BULLET_LIFETIME


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


# ── Phase ──
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    DEATH = auto()
    GAME_OVER = auto()


# ── Game ──
class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="SPLIT CHAIN", fps=FPS, display_scale=DISPLAY_SCALE)
        self.reset()
        pyxel.run(self._update, self._draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.high_score: int = 0
        self.lives: int = STARTING_LIVES
        self.combo: int = 0
        self.combo_color: int = 0
        self.bullet_color: int = 0
        self.shoot_timer: int = 0
        self.invuln_timer: int = 0
        self.spawn_timer: int = SPAWN_INTERVAL
        self.frame: int = 0

        # Ship state
        self.ship_x: float = SCREEN_W / 2
        self.ship_y: float = SCREEN_H / 2
        self.ship_vx: float = 0.0
        self.ship_vy: float = 0.0
        self.ship_angle: float = 0.0  # degrees, 0 = pointing up

        # Entities
        self.asteroids: list[Asteroid] = []
        self.bullets: list[Bullet] = []
        self.particles: list[Particle] = []

        # Key state tracking (for continuous rotation/thrust, also used by draw)
        self._key_up: bool = False
        self._thrust_visual: bool = False

    # ── Spawning ──
    def _spawn_asteroid(
        self,
        size: int = SIZE_LARGE,
        x: float | None = None,
        y: float | None = None,
        color: int | None = None,
    ) -> None:
        if len(self.asteroids) >= MAX_ASTEROIDS:
            return
        if x is None:
            edge = random.randint(0, 3)
            if edge == 0:  # top
                x = random.uniform(0, SCREEN_W)
                y = -20.0
            elif edge == 1:  # right
                x = SCREEN_W + 20.0
                y = random.uniform(0, SCREEN_H)
            elif edge == 2:  # bottom
                x = random.uniform(0, SCREEN_W)
                y = SCREEN_H + 20.0
            else:  # left
                x = -20.0
                y = random.uniform(0, SCREEN_H)
        if y is None:
            y = 0.0
        if color is None:
            color = random.randint(0, NUM_COLORS - 1)

        speed_base = 1.5 if size == SIZE_LARGE else 2.5
        angle = random.uniform(0, 2 * math.pi)
        # Bias toward center
        cx = SCREEN_W / 2
        cy = SCREEN_H / 2
        bias_angle = math.atan2(cy - y, cx - x)
        final_angle = angle * 0.6 + bias_angle * 0.4

        radius = ASTEROID_RADII[size]
        self.asteroids.append(
            Asteroid(
                x=x,
                y=y,
                vx=math.cos(final_angle) * speed_base,
                vy=math.sin(final_angle) * speed_base,
                radius=radius,
                color=color,
                size=size,
            )
        )

    def _spawn_initial_asteroids(self) -> None:
        for _ in range(INITIAL_ASTEROIDS):
            self._spawn_asteroid(SIZE_LARGE)

    def _split_asteroid(self, asteroid: Asteroid) -> None:
        """Split asteroid into smaller pieces, with COMBO bonus."""
        if asteroid.size == SIZE_SMALL:
            self._spawn_particles(asteroid.x, asteroid.y, asteroid.color, PARTICLE_COUNT_SMALL)
            return

        # Determine child size and base count
        child_size = SIZE_MEDIUM if asteroid.size == SIZE_LARGE else SIZE_SMALL
        base_count = 2

        # COMBO bonus: extra children when same-color combo is active
        extra = 0
        if asteroid.color == self.combo_color and self.combo >= COMBO_EXTRA_SPLIT_THRESHOLD:
            extra = 1
        count = min(base_count + extra, 4)  # cap at 4 children

        # COMBO burst particles
        if asteroid.color == self.combo_color and self.combo >= COMBO_BURST_THRESHOLD:
            self._spawn_particles(asteroid.x, asteroid.y, asteroid.color, PARTICLE_COUNT_LARGE)

        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2.0, 4.0)
            radius = ASTEROID_RADII[child_size]
            self.asteroids.append(
                Asteroid(
                    x=asteroid.x + random.uniform(-5, 5),
                    y=asteroid.y + random.uniform(-5, 5),
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    radius=radius,
                    color=asteroid.color,
                    size=child_size,
                )
            )

        self._spawn_particles(asteroid.x, asteroid.y, asteroid.color, PARTICLE_COUNT_SMALL)

    # ── Particles ──
    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.5, PARTICLE_SPEED)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=PARTICLE_LIFE,
                    color=color,
                )
            )

    # ── Collision ──
    def _check_bullet_asteroid_collisions(self) -> None:
        bullets_to_remove: list[int] = []
        asteroids_to_remove: list[int] = []

        for bi, bullet in enumerate(self.bullets):
            for ai, asteroid in enumerate(self.asteroids):
                if ai in asteroids_to_remove:
                    continue
                dx = bullet.x - asteroid.x
                dy = bullet.y - asteroid.y
                dist_sq = dx * dx + dy * dy
                hit_dist = asteroid.radius + BULLET_SIZE
                if dist_sq < hit_dist * hit_dist:
                    bullets_to_remove.append(bi)
                    asteroids_to_remove.append(ai)

                    # COMBO logic
                    if bullet.color == asteroid.color:
                        if self.combo > 0 and self.combo_color == asteroid.color:
                            self.combo += 1
                        else:
                            self.combo = 1
                            self.combo_color = asteroid.color
                        multiplier = 1.0 + self.combo * 0.5
                    else:
                        self.combo = 0
                        multiplier = 1.0

                    self.score += int(ASTEROID_SCORES[asteroid.size] * multiplier)
                    self._split_asteroid(asteroid)
                    break

        # Remove in reverse order
        for bi in sorted(set(bullets_to_remove), reverse=True):
            if bi < len(self.bullets):
                del self.bullets[bi]
        for ai in sorted(set(asteroids_to_remove), reverse=True):
            if ai < len(self.asteroids):
                del self.asteroids[ai]

    def _check_ship_asteroid_collisions(self) -> None:
        if self.invuln_timer > 0:
            return
        for asteroid in self.asteroids:
            dx = self.ship_x - asteroid.x
            dy = self.ship_y - asteroid.y
            dist_sq = dx * dx + dy * dy
            hit_dist = asteroid.radius + SHIP_RADIUS
            if dist_sq < hit_dist * hit_dist:
                self._on_ship_hit()
                return

    def _on_ship_hit(self) -> None:
        self._spawn_particles(self.ship_x, self.ship_y, pyxel.COLOR_WHITE, PARTICLE_COUNT_LARGE)
        self.lives -= 1
        self.combo = 0
        if self.lives <= 0:
            if self.score > self.high_score:
                self.high_score = self.score
            self.phase = Phase.GAME_OVER
        else:
            self.phase = Phase.DEATH
            self.invuln_timer = SHIP_INVULN_FRAMES
            # Reset ship position to center
            self.ship_x = SCREEN_W / 2
            self.ship_y = SCREEN_H / 2
            self.ship_vx = 0.0
            self.ship_vy = 0.0
            self.ship_angle = 0.0
            self._thrust_visual = False
            self.bullets.clear()

    # ── Movement helpers ──
    def _wrap_position(self, x: float, y: float) -> tuple[float, float]:
        """Screen-wrap a position."""
        return x % SCREEN_W, y % SCREEN_H

    def _update_entity_positions(self) -> None:
        """Move and wrap all entities."""
        # Bullets
        for bullet in self.bullets:
            bullet.x += bullet.vx
            bullet.y += bullet.vy
            bullet.life -= 1
            bullet.x, bullet.y = self._wrap_position(bullet.x, bullet.y)
        self.bullets = [b for b in self.bullets if b.life > 0]

        # Asteroids
        for asteroid in self.asteroids:
            asteroid.x += asteroid.vx
            asteroid.y += asteroid.vy
            asteroid.x, asteroid.y = self._wrap_position(asteroid.x, asteroid.y)

        # Particles
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ── Update ──
    def _update(self) -> None:
        self.frame += 1

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.DEATH:
            self._update_death()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_Z) or pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.phase = Phase.PLAYING
            self._spawn_initial_asteroids()

    def _update_playing(self) -> None:
        # Input
        key_left = pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A)
        key_right = pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D)
        self._key_up = pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W)
        self._thrust_visual = self._key_up

        # Bullet color cycling
        if pyxel.btnp(pyxel.KEY_C):
            self.bullet_color = (self.bullet_color + 1) % NUM_COLORS
            self.combo = 0  # changing color resets combo

        # Shooting
        if self.shoot_timer > 0:
            self.shoot_timer -= 1
        if (pyxel.btn(pyxel.KEY_Z) or pyxel.btn(pyxel.KEY_SPACE)) and self.shoot_timer <= 0:
            self._shoot()
            self.shoot_timer = SHOOT_COOLDOWN

        # Rotation
        if key_left:
            self.ship_angle -= SHIP_ROTATE_SPEED
        if key_right:
            self.ship_angle += SHIP_ROTATE_SPEED
        self.ship_angle %= 360.0

        # Thrust
        if self._key_up:
            rad = math.radians(self.ship_angle)
            self.ship_vx += math.sin(rad) * SHIP_THRUST
            self.ship_vy -= math.cos(rad) * SHIP_THRUST

        # Drag
        self.ship_vx *= SHIP_DRAG
        self.ship_vy *= SHIP_DRAG

        # Speed limit
        speed = math.sqrt(self.ship_vx * self.ship_vx + self.ship_vy * self.ship_vy)
        if speed > SHIP_MAX_SPEED:
            scale = SHIP_MAX_SPEED / speed
            self.ship_vx *= scale
            self.ship_vy *= scale

        # Move ship
        self.ship_x += self.ship_vx
        self.ship_y += self.ship_vy
        self.ship_x, self.ship_y = self._wrap_position(self.ship_x, self.ship_y)

        # Move entities
        self._update_entity_positions()

        # Collisions
        self._check_bullet_asteroid_collisions()
        self._check_ship_asteroid_collisions()

        # Spawn new asteroids over time
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            wave = self.frame // SPAWN_INTERVAL
            count = 1 + wave // 3
            for _ in range(count):
                size = SIZE_LARGE if random.random() < 0.6 else SIZE_MEDIUM
                self._spawn_asteroid(size)
            self.spawn_timer = SPAWN_INTERVAL

    def _update_death(self) -> None:
        self.invuln_timer -= 1
        self._thrust_visual = False
        self._update_entity_positions()

        if self.invuln_timer <= 0:
            self.phase = Phase.PLAYING

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_Z) or pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.phase = Phase.PLAYING
            self._spawn_initial_asteroids()

    # ── Shooting ──
    def _shoot(self) -> None:
        rad = math.radians(self.ship_angle)
        # Bullet fires in ship's facing direction (angle 0 = up)
        vx = math.sin(rad) * BULLET_SPEED
        vy = -math.cos(rad) * BULLET_SPEED
        # Spawn slightly ahead of ship
        spawn_x = self.ship_x + vx * 2.0 / BULLET_SPEED * 2
        spawn_y = self.ship_y + vy * 2.0 / BULLET_SPEED * 2
        self.bullets.append(
            Bullet(
                x=spawn_x,
                y=spawn_y,
                vx=vx,
                vy=vy,
                color=self.bullet_color,
            )
        )

    # ── Draw ──
    def _draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.PLAYING, Phase.DEATH):
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        cx = SCREEN_W // 2
        cy = SCREEN_H // 2
        pyxel.text(cx - 40, cy - 30, "SPLIT CHAIN", pyxel.COLOR_WHITE)
        pyxel.text(cx - 55, cy, "Asteroids + Color Combo", pyxel.COLOR_GRAY)
        pyxel.text(cx - 45, cy + 20, "Match color = COMBO!", pyxel.COLOR_CYAN)
        pyxel.text(cx - 50, cy + 35, "COMBO 3+ = Extra Splits", pyxel.COLOR_LIME)
        pyxel.text(cx - 40, cy + 55, "Z: Shoot  C: Cycle", pyxel.COLOR_YELLOW)
        pyxel.text(cx - 40, cy + 70, "Arrows: Move/Rotate", pyxel.COLOR_ORANGE)
        blink = (self.frame // 30) % 2 == 0
        if blink:
            pyxel.text(cx - 45, cy + 95, "PRESS Z TO START", pyxel.COLOR_WHITE)

    def _draw_game(self) -> None:
        # Draw particles (behind everything)
        for p in self.particles:
            alpha = p.life / PARTICLE_LIFE
            col = p.color if alpha > 0.3 else pyxel.COLOR_GRAY
            pyxel.pset(int(p.x), int(p.y), col)

        # Draw asteroids
        for asteroid in self.asteroids:
            col = COLORS[asteroid.color]
            self._draw_asteroid(asteroid, col)

        # Draw bullets
        for bullet in self.bullets:
            col = COLORS[bullet.color]
            pyxel.rect(int(bullet.x) - 1, int(bullet.y) - 1, 2, 2, col)

        # Draw ship (blink during invulnerability)
        if self.phase == Phase.DEATH and (self.invuln_timer // 4) % 2 == 0:
            pass
        else:
            self._draw_ship()

        # HUD
        pyxel.text(4, 4, f"SCORE:{self.score}", pyxel.COLOR_WHITE)
        pyxel.text(4, 12, f"HI:{self.high_score}", pyxel.COLOR_GRAY)

        # Lives
        for i in range(self.lives):
            pyxel.rect(SCREEN_W - 30 + i * 10, 4, 4, 8, pyxel.COLOR_WHITE)

        # COMBO display
        if self.combo >= 2:
            combo_text = f"COMBO x{self.combo}"
            combo_col = COLORS[self.combo_color]
            pyxel.text(SCREEN_W // 2 - 25, 4, combo_text, combo_col)

        # Bullet color indicator
        col = COLORS[self.bullet_color]
        pyxel.rect(4, SCREEN_H - 12, 8, 8, col)
        pyxel.text(14, SCREEN_H - 10, "C", pyxel.COLOR_WHITE)

    def _draw_ship(self) -> None:
        """Draw the triangular ship at its position and angle."""
        rad = math.radians(self.ship_angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        # Triangle points (pointing up when angle=0)
        # Nose
        nx = self.ship_x + sin_a * SHIP_RADIUS
        ny = self.ship_y - cos_a * SHIP_RADIUS
        # Left wing
        wing_len = SHIP_RADIUS * 0.7
        wing_width = SHIP_RADIUS * 0.6
        lx = self.ship_x - sin_a * wing_len - cos_a * wing_width
        ly = self.ship_y + cos_a * wing_len - sin_a * wing_width
        # Right wing
        rx = self.ship_x - sin_a * wing_len + cos_a * wing_width
        ry = self.ship_y + cos_a * wing_len + sin_a * wing_width

        pyxel.tri(int(nx), int(ny), int(lx), int(ly), int(rx), int(ry), pyxel.COLOR_WHITE)

        # Thrust flame
        if self._thrust_visual and self.phase == Phase.PLAYING:
            flame_base_x = self.ship_x - sin_a * SHIP_RADIUS * 0.5
            flame_base_y = self.ship_y + cos_a * SHIP_RADIUS * 0.5
            flame_len = 3.0 + random.uniform(0, 4)
            fx = flame_base_x - sin_a * flame_len
            fy = flame_base_y + cos_a * flame_len
            pyxel.line(
                int(flame_base_x), int(flame_base_y),
                int(fx), int(fy),
                pyxel.COLOR_ORANGE,
            )

    def _draw_asteroid(self, asteroid: Asteroid, col: int) -> None:
        """Draw an asteroid as a jagged polygon."""
        if asteroid.size == SIZE_SMALL:
            pyxel.circb(int(asteroid.x), int(asteroid.y), asteroid.radius, col)
            return

        segments = 12 if asteroid.size == SIZE_LARGE else 8
        # Use a deterministic seed per asteroid for consistent jagged shape
        seed = int(asteroid.x * 7919 + asteroid.y * 6271) % 10000
        rng = random.Random(seed)
        points: list[tuple[int, int]] = []
        for i in range(segments):
            angle = i * 2 * math.pi / segments
            jitter_range = asteroid.radius * 0.6
            jitter = asteroid.radius * 0.4 + rng.uniform(-jitter_range, jitter_range)
            px = int(asteroid.x + math.cos(angle) * jitter)
            py = int(asteroid.y + math.sin(angle) * jitter)
            points.append((px, py))
        for i in range(segments):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % segments]
            pyxel.line(x1, y1, x2, y2, col)

    def _draw_game_over(self) -> None:
        cx = SCREEN_W // 2
        cy = SCREEN_H // 2
        pyxel.text(cx - 30, cy - 20, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(cx - 40, cy + 5, f"SCORE: {self.score}", pyxel.COLOR_WHITE)
        pyxel.text(cx - 40, cy + 20, f"HIGH: {self.high_score}", pyxel.COLOR_YELLOW)
        blink = (self.frame // 30) % 2 == 0
        if blink:
            pyxel.text(cx - 45, cy + 45, "PRESS Z TO RETRY", pyxel.COLOR_WHITE)


if __name__ == "__main__":
    Game()
