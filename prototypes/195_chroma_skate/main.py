"""CHROMA SKATE — Top-down figure skating with color-matching combos.

Core fun moment: gliding across the ice, chaining same-color rings to build
COMBO, then activating SUPER SPIN for a rainbow trail and massive score burst.
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


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Ring:
    x: float
    y: float
    color: int
    radius: int = 20
    collected: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


RING_COLORS: tuple[int, ...] = (RED, GREEN, LIGHT_BLUE, YELLOW)
RING_COUNT = 6
RING_RADIUS = 20
RINK_LEFT = 20
RINK_TOP = 20
RINK_RIGHT = 300
RINK_BOTTOM = 220
SKATER_RADIUS = 8
ACCEL = 0.15
FRICTION = 0.98
MAX_SPEED = 3.0
SUPER_DURATION = 300
GAME_DURATION = 3600
STUN_FRAMES = 15
COMBO_THRESHOLD = 5
TRAIL_MAX = 60
PARTICLE_COUNT = 8


class Game:
    def __init__(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.skater_x: float = 160.0
        self.skater_y: float = 120.0
        self.skater_vx: float = 0.0
        self.skater_vy: float = 0.0
        self.trail_color: int = WHITE
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.game_timer: int = GAME_DURATION
        self.stun_timer: int = 0
        self.rings: list[Ring] = []
        self.particles: list[Particle] = []
        self.trail_positions: list[tuple[float, float, int]] = []
        self.rng: random.Random = random.Random()
        self.high_score: int = 0
        pyxel.init(SCREEN_W, SCREEN_H, title="CHROMA SKATE", display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.skater_x = 160.0
        self.skater_y = 120.0
        self.skater_vx = 0.0
        self.skater_vy = 0.0
        self.trail_color = self.rng.choice(RING_COLORS)
        self.super_mode = False
        self.super_timer = 0
        self.game_timer = GAME_DURATION
        self.stun_timer = 0
        self.rings = []
        self.particles = []
        self.trail_positions = []
        self._spawn_rings(RING_COUNT)

    def _spawn_ring(self) -> Ring:
        for _ in range(100):
            x = self.rng.uniform(
                RINK_LEFT + RING_RADIUS + 2,
                RINK_RIGHT - RING_RADIUS - 2,
            )
            y = self.rng.uniform(
                RINK_TOP + RING_RADIUS + 2,
                RINK_BOTTOM - RING_RADIUS - 2,
            )
            color = self.rng.choice(RING_COLORS)
            too_close = any(
                math.hypot(r.x - x, r.y - y) < RING_RADIUS * 2.5
                for r in self.rings
                if not r.collected
            )
            if not too_close:
                return Ring(x=x, y=y, color=color)
        x = self.rng.uniform(
            RINK_LEFT + RING_RADIUS + 2,
            RINK_RIGHT - RING_RADIUS - 2,
        )
        y = self.rng.uniform(
            RINK_TOP + RING_RADIUS + 2,
            RINK_BOTTOM - RING_RADIUS - 2,
        )
        color = self.rng.choice(RING_COLORS)
        return Ring(x=x, y=y, color=color)

    def _spawn_rings(self, count: int) -> None:
        for _ in range(count):
            ring = self._spawn_ring()
            self.rings.append(ring)

    def _update_skater(self, ax: float, ay: float) -> None:
        if self.stun_timer > 0:
            return
        self.skater_vx += ax * ACCEL
        self.skater_vy += ay * ACCEL
        speed = math.hypot(self.skater_vx, self.skater_vy)
        if speed > MAX_SPEED:
            self.skater_vx = self.skater_vx / speed * MAX_SPEED
            self.skater_vy = self.skater_vy / speed * MAX_SPEED
        self.skater_vx *= FRICTION
        self.skater_vy *= FRICTION
        self.skater_x += self.skater_vx
        self.skater_y += self.skater_vy
        hit_wall = False
        if self.skater_x - SKATER_RADIUS < RINK_LEFT:
            self.skater_x = RINK_LEFT + SKATER_RADIUS
            self.skater_vx = abs(self.skater_vx) * 0.5
            hit_wall = True
        elif self.skater_x + SKATER_RADIUS > RINK_RIGHT:
            self.skater_x = RINK_RIGHT - SKATER_RADIUS
            self.skater_vx = -abs(self.skater_vx) * 0.5
            hit_wall = True
        if self.skater_y - SKATER_RADIUS < RINK_TOP:
            self.skater_y = RINK_TOP + SKATER_RADIUS
            self.skater_vy = abs(self.skater_vy) * 0.5
            hit_wall = True
        elif self.skater_y + SKATER_RADIUS > RINK_BOTTOM:
            self.skater_y = RINK_BOTTOM - SKATER_RADIUS
            self.skater_vy = -abs(self.skater_vy) * 0.5
            hit_wall = True
        if hit_wall and self.stun_timer <= 0:
            self.stun_timer = STUN_FRAMES
            self.combo = 0

    def _check_ring_collision(self) -> tuple[int, bool]:
        score_change = 0
        combo_reset = False
        for ring in self.rings:
            if ring.collected:
                continue
            dist = math.hypot(self.skater_x - ring.x, self.skater_y - ring.y)
            if dist < SKATER_RADIUS + ring.radius:
                ring.collected = True
                if self.super_mode or ring.color == self.trail_color:
                    multiplier = 3 if self.super_mode else 1
                    self.combo += 1
                    if self.combo > self.max_combo:
                        self.max_combo = self.combo
                    combo_multiplier = max(1, min(self.combo, 10))
                    score_change += 100 * combo_multiplier * multiplier
                    if not self.super_mode:
                        available = [c for c in RING_COLORS if c != self.trail_color]
                        self.trail_color = self.rng.choice(available)
                    if self.combo >= COMBO_THRESHOLD and not self.super_mode:
                        self.super_mode = True
                        self.super_timer = SUPER_DURATION
                    self._spawn_collect_particles(ring.x, ring.y, ring.color)
                else:
                    self.combo = 0
                    score_change -= 50
                    combo_reset = True
        collected_count = sum(1 for r in self.rings if r.collected)
        if collected_count >= RING_COUNT // 2:
            self.rings = [r for r in self.rings if not r.collected]
            self._spawn_rings(RING_COUNT - len(self.rings))
        return score_change, combo_reset

    def _spawn_collect_particles(self, x: float, y: float, color: int) -> None:
        particle_colors = RING_COLORS if self.super_mode else (color,)
        for _ in range(PARTICLE_COUNT):
            angle = self.rng.uniform(0, math.pi * 2)
            speed = self.rng.uniform(1.0, 3.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = self.rng.randint(20, 40)
            pc = self.rng.choice(particle_colors)
            self.particles.append(Particle(x, y, vx, vy, life, pc))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_super_mode(self) -> None:
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0

    def _update_trail(self) -> None:
        self.trail_positions.append((self.skater_x, self.skater_y, self.trail_color))
        if len(self.trail_positions) > TRAIL_MAX:
            self.trail_positions = self.trail_positions[-TRAIL_MAX:]

    def _update_hud_timer(self) -> None:
        if self.game_timer > 0:
            self.game_timer -= 1
            if self.game_timer <= 0:
                self.game_timer = 0
                self.phase = Phase.GAME_OVER
                if self.score > self.high_score:
                    self.high_score = self.score

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
        elif self.phase == Phase.PLAYING:
            if self.stun_timer > 0:
                self.stun_timer -= 1
            ax = 0.0
            ay = 0.0
            if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
                ax = -1.0
            if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
                ax = 1.0
            if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
                ay = -1.0
            if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
                ay = 1.0
            if ax != 0.0 and ay != 0.0:
                inv = 1.0 / math.sqrt(2.0)
                ax *= inv
                ay *= inv
            self._update_skater(ax, ay)
            sc, _ = self._check_ring_collision()
            self.score += sc
            if self.score < 0:
                self.score = 0
            self._update_super_mode()
            self._update_trail()
            self._update_particles()
            self._update_hud_timer()
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()

    def _draw_rink(self) -> None:
        pyxel.rect(RINK_LEFT, RINK_TOP, RINK_RIGHT - RINK_LEFT, RINK_BOTTOM - RINK_TOP, CYAN)
        pyxel.rectb(RINK_LEFT, RINK_TOP, RINK_RIGHT - RINK_LEFT, RINK_BOTTOM - RINK_TOP, WHITE)

    def _draw_trail(self) -> None:
        for i, (tx, ty, tc) in enumerate(self.trail_positions):
            color = tc
            if self.super_mode:
                color = RING_COLORS[i % len(RING_COLORS)]
            pyxel.pset(int(tx), int(ty), color)

    def _draw_rings(self) -> None:
        for ring in self.rings:
            if ring.collected:
                continue
            if self.super_mode:
                pyxel.circb(int(ring.x), int(ring.y), ring.radius, ring.color)
                pulse_r = ring.radius + int(math.sin(pyxel.frame_count * 0.1) * 3)
                pyxel.circb(int(ring.x), int(ring.y), pulse_r, WHITE)
            else:
                pyxel.circb(int(ring.x), int(ring.y), ring.radius, ring.color)

    def _draw_skater(self) -> None:
        if self.stun_timer > 0 and self.stun_timer % 4 < 2:
            return
        sx = int(self.skater_x)
        sy = int(self.skater_y)
        angle = math.atan2(self.skater_vy, self.skater_vx)
        if abs(self.skater_vx) < 0.01 and abs(self.skater_vy) < 0.01:
            angle = 0.0
        tip_x = int(sx + math.cos(angle) * SKATER_RADIUS)
        tip_y = int(sy + math.sin(angle) * SKATER_RADIUS)
        back_angle1 = angle + math.pi * 0.75
        back_angle2 = angle - math.pi * 0.75
        bx1 = int(sx + math.cos(back_angle1) * SKATER_RADIUS * 0.8)
        by1 = int(sy + math.sin(back_angle1) * SKATER_RADIUS * 0.8)
        bx2 = int(sx + math.cos(back_angle2) * SKATER_RADIUS * 0.8)
        by2 = int(sy + math.sin(back_angle2) * SKATER_RADIUS * 0.8)
        color = self.trail_color
        if self.super_mode:
            color = RING_COLORS[(pyxel.frame_count // 4) % len(RING_COLORS)]
        pyxel.tri(tip_x, tip_y, bx1, by1, bx2, by2, color)
        inner = int(SKATER_RADIUS * 0.4)
        pyxel.circ(sx, sy, inner, WHITE)
        if self.super_mode:
            glow = int(SKATER_RADIUS * 1.5)
            pyxel.circb(sx, sy, glow, RING_COLORS[(pyxel.frame_count // 8) % len(RING_COLORS)])

    def _draw_particles(self) -> None:
        for p in self.particles:
            fade_color = p.color
            if p.life < 10:
                if p.life % 2 == 0:
                    continue
            pyxel.pset(int(p.x), int(p.y), fade_color)

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, 14, BLACK)
        pyxel.text(2, 3, f"SCORE:{self.score:06d}", WHITE)
        pyxel.text(100, 3, f"COMBO:x{min(self.combo, 10)}", self.trail_color)
        if self.super_mode:
            pyxel.text(180, 3, "SUPER SPIN!", YELLOW)
        sec = self.game_timer // 60
        timer_str = f"TIME:{sec:02d}"
        timer_col = WHITE if sec > 10 else RED
        pyxel.text(270, 3, timer_str, timer_col)
        if self.super_mode:
            bar_w = int(60 * self.super_timer / SUPER_DURATION)
            pyxel.rect(180, 12, 60, 2, GRAY)
            pyxel.rect(180, 12, bar_w, 2, YELLOW)
        pyxel.line(0, 14, SCREEN_W, 14, WHITE)

    def _draw_title(self) -> None:
        pyxel.cls(BLACK)
        pyxel.text(110, 60, "CHROMA SKATE", WHITE)
        pyxel.text(60, 90, "Arrow keys / WASD to skate", WHITE)
        pyxel.text(55, 105, "Match ring color to build COMBO", WHITE)
        pyxel.text(55, 120, f"COMBO x{COMBO_THRESHOLD} = SUPER SPIN! (3x score)", WHITE)
        pyxel.text(55, 135, "Hitting walls resets COMBO + stuns", WHITE)
        pyxel.text(95, 165, "Press ENTER to start", YELLOW)
        if self.high_score > 0:
            pyxel.text(100, 185, f"HIGH SCORE: {self.high_score:06d}", WHITE)

    def _draw_game_over(self) -> None:
        pyxel.cls(BLACK)
        pyxel.text(115, 70, "GAME OVER", WHITE)
        pyxel.text(90, 100, f"SCORE: {self.score:06d}", WHITE)
        pyxel.text(90, 115, f"MAX COMBO: x{min(self.max_combo, 10)}", WHITE)
        pyxel.text(90, 130, f"HIGH SCORE: {self.high_score:06d}", WHITE)
        pyxel.text(95, 165, "Press ENTER to retry", YELLOW)

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_rink()
            self._draw_trail()
            self._draw_rings()
            self._draw_particles()
            self._draw_skater()
            self._draw_hud()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
