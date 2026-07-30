from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


@dataclass
class Ring:
    x: float
    y: float
    color: int
    collected: bool = False


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


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class Game:
    PLAYER_COLORS: tuple[int, ...] = (8, 11, 5, 10)
    CLOUD_COLS: int = 10
    CLOUD_ROWS: int = 7
    CELL: int = 32
    CLOUD_OFFSET_Y: int = 8
    PLAYER_Y: int = 60
    RING_RADIUS: int = 10
    PLAYER_RADIUS: int = 8
    MAX_RINGS: int = 8
    HEAT_MAX: int = 100
    TIMER_MAX: int = 1800
    SUPER_DURATION: int = 300
    COLOR_CYCLE_FRAMES: int = 20
    PLAYER_SPEED: float = 3.0
    RING_SPEED: float = 1.5

    def __init__(self) -> None:
        pyxel.init(320, 240, "SKY CHAIN", fps=30, display_scale=2)
        self._rng = random.Random()
        self.best_score: int = 0
        self.best_ghost: list[tuple[float, float]] = []

        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.player_x: float = 160.0
        self.player_color_idx: int = 0
        self.player_color: int = self.PLAYER_COLORS[0]
        self.color_timer: int = self.COLOR_CYCLE_FRAMES
        self.rings: list[Ring] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.clouds: set[tuple[int, int]] = set()
        self.heat: float = 0.0
        self.super_timer: int = 0
        self.super_mode: bool = False
        self.stun_timer: int = 0
        self.timer: int = self.TIMER_MAX
        self.frame_count: int = 0
        self.ring_spawn_timer: int = 0
        self.ring_spawn_interval: int = 60
        self.cloud_spread_timer: int = 0
        self.cloud_spread_interval: int = 60
        self.ghost_trail: list[tuple[float, float]] = []
        self.shake_frames: int = 0
        self._last_cloud_hit_frame: int = -100

        pyxel.run(self.update, self.draw)

    def _reset_playing(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.player_x = 160.0
        self.player_color_idx = 0
        self.player_color = self.PLAYER_COLORS[0]
        self.color_timer = self.COLOR_CYCLE_FRAMES
        self.rings.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.clouds.clear()
        self.heat = 0.0
        self.super_timer = 0
        self.super_mode = False
        self.stun_timer = 0
        self.timer = self.TIMER_MAX
        self.frame_count = 0
        self.ring_spawn_timer = 0
        self.ring_spawn_interval = 60
        self.cloud_spread_timer = 0
        self.cloud_spread_interval = 60
        self.ghost_trail.clear()
        self.shake_frames = 0
        self._last_cloud_hit_frame = -100

    # -- Update ----------------------------------------------------------------

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._reset_playing()

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.phase = Phase.TITLE

    def _update_playing(self) -> None:
        self.frame_count += 1
        self.timer -= 1

        elapsed_ratio = self.frame_count / self.TIMER_MAX

        self.color_timer -= 1
        if self.color_timer <= 0:
            self.color_timer = self.COLOR_CYCLE_FRAMES
            self.player_color_idx = (self.player_color_idx + 1) % 4
            self.player_color = self.PLAYER_COLORS[self.player_color_idx]

        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0

        if self.stun_timer > 0:
            self.stun_timer -= 1
        else:
            if pyxel.btn(pyxel.KEY_LEFT):
                self.player_x -= self.PLAYER_SPEED
            if pyxel.btn(pyxel.KEY_RIGHT):
                self.player_x += self.PLAYER_SPEED

            if self.super_mode:
                nearest = self._find_nearest_ring()
                if nearest is not None:
                    dx = nearest.x - self.player_x
                    steer = max(-self.PLAYER_SPEED * 1.5, min(self.PLAYER_SPEED * 1.5, dx * 0.2))
                    self.player_x += steer

        self.player_x = max(float(self.PLAYER_RADIUS), min(320.0 - self.PLAYER_RADIUS, self.player_x))

        self.ring_spawn_timer -= 1
        if self.ring_spawn_timer <= 0:
            self._spawn_ring()
            self.ring_spawn_interval = max(25, int(60 - 35 * elapsed_ratio))
            self.ring_spawn_timer = self.ring_spawn_interval

        self._update_rings()
        self._check_ring_collisions()

        self.cloud_spread_timer -= 1
        if self.cloud_spread_timer <= 0:
            self._update_clouds()
            self.cloud_spread_interval = max(30, int(60 - 30 * elapsed_ratio))
            self.cloud_spread_timer = self.cloud_spread_interval

        self._check_cloud_collision()
        self._update_heat()
        self._update_particles()
        self._update_floating_texts()

        if self.shake_frames > 0:
            self.shake_frames -= 1

        if self.frame_count % 5 == 0:
            self.ghost_trail.append((self.player_x, float(self.PLAYER_Y)))

        if self.heat >= self.HEAT_MAX or self.timer <= 0:
            self.phase = Phase.GAME_OVER
            if self.score > self.best_score:
                self.best_score = self.score
                self.best_ghost = self.ghost_trail.copy()

    # -- Game logic (testable) ------------------------------------------------

    def _spawn_ring(self) -> None:
        if len(self.rings) >= self.MAX_RINGS:
            return
        x = self._rng.uniform(self.RING_RADIUS, 320 - self.RING_RADIUS)
        color = self._rng.choice(self.PLAYER_COLORS)
        self.rings.append(Ring(x=x, y=240.0 + self.RING_RADIUS, color=color))

    def _find_nearest_ring(self) -> Ring | None:
        nearest: Ring | None = None
        min_dist = float("inf")
        for ring in self.rings:
            if ring.collected:
                continue
            dx = ring.x - self.player_x
            dy = ring.y - self.PLAYER_Y
            dist = dx * dx + dy * dy
            if dist < min_dist:
                min_dist = dist
                nearest = ring
        return nearest

    def _update_rings(self) -> None:
        for ring in self.rings:
            ring.y -= self.RING_SPEED
        self.rings = [r for r in self.rings if r.y > -self.RING_RADIUS and not r.collected]

    def _check_ring_collisions(self) -> None:
        px = self.player_x
        py = float(self.PLAYER_Y)
        pr = self.PLAYER_RADIUS
        threshold_sq = (pr + self.RING_RADIUS) ** 2

        for ring in self.rings:
            if ring.collected:
                continue
            dx = px - ring.x
            dy = py - ring.y
            if dx * dx + dy * dy < threshold_sq:
                ring.collected = True
                if self.super_mode or ring.color == self.player_color:
                    self.combo += 1
                    if self.combo > self.max_combo:
                        self.max_combo = self.combo
                    multiplier = 3 if self.super_mode else 1
                    points = 10 * self.combo * multiplier
                    self.score += points
                    self._add_particles(ring.x, ring.y, 8, ring.color)
                    self._add_floating_text(ring.x, ring.y - 12, f"+{points}", ring.color)
                    if self.combo >= 4 and not self.super_mode:
                        self._activate_super()
                else:
                    self.combo = 0
                    if not self.super_mode:
                        self.heat = min(float(self.HEAT_MAX), self.heat + 15)
                    self.stun_timer = 15
                    self._add_particles(ring.x, ring.y, 5, 8)
                    self._add_floating_text(ring.x, ring.y - 12, "MISS!", 8)
                    self.shake_frames = 5

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = self.SUPER_DURATION
        for _i in range(20):
            color = self.PLAYER_COLORS[self._rng.randint(0, 3)]
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1, 3)
            self.particles.append(
                Particle(
                    x=self.player_x,
                    y=float(self.PLAYER_Y),
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=self._rng.randint(20, 30),
                    color=color,
                )
            )
        self._add_floating_text(self.player_x, float(self.PLAYER_Y - 20), "SUPER!", 10)

    def _update_clouds(self) -> None:
        count = self._rng.randint(2, 3)
        for _ in range(count):
            col = self._rng.randint(0, self.CLOUD_COLS - 1)
            self.clouds.add((col, 0))

        if self._rng.random() < 0.3:
            side_col = 0 if self._rng.random() < 0.5 else self.CLOUD_COLS - 1
            row = self._rng.randint(0, self.CLOUD_ROWS - 1)
            self.clouds.add((side_col, row))

        existing = list(self.clouds)
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        for col, row in existing:
            if self._rng.random() < 0.3:
                self._rng.shuffle(directions)
                for dc, dr in directions:
                    nc, nr = col + dc, row + dr
                    if 0 <= nc < self.CLOUD_COLS and 0 <= nr < self.CLOUD_ROWS:
                        if (nc, nr) not in self.clouds:
                            self.clouds.add((nc, nr))
                            break

    def _check_cloud_collision(self) -> None:
        if self.frame_count - self._last_cloud_hit_frame < 30:
            return

        px = self.player_x
        py = float(self.PLAYER_Y)
        pr = self.PLAYER_RADIUS

        for col, row in list(self.clouds):
            rx = float(col * self.CELL)
            ry = float(row * self.CELL + self.CLOUD_OFFSET_Y)
            cx = max(rx, min(px, rx + self.CELL))
            cy = max(ry, min(py, ry + self.CELL))
            if (px - cx) ** 2 + (py - cy) ** 2 < pr**2:
                self.combo = 0
                if not self.super_mode:
                    self.heat = min(float(self.HEAT_MAX), self.heat + 25)
                self.stun_timer = 20
                self._add_particles(px, py, 10, 7)
                self._add_floating_text(px, py - 10, "HIT!", 8)
                self.shake_frames = 10
                self._last_cloud_hit_frame = self.frame_count
                break

    def _update_heat(self) -> None:
        if self.heat > 0:
            self.heat = max(0.0, self.heat - 0.02)

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _add_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.0)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=self._rng.randint(10, 25),
                    color=color,
                )
            )

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 1.0
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=40, color=color))

    # -- Draw ------------------------------------------------------------------

    def draw(self) -> None:
        pyxel.cls(6)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(136, 60, "SKY CHAIN", 7)
        pyxel.text(96, 80, "Skydive through colored rings!", 3)
        pyxel.text(48, 96, "Match colors -> COMBO chain -> SUPER SKYDIVE!", 7)
        pyxel.text(104, 120, "LEFT / RIGHT: Move laterally", 7)
        pyxel.text(92, 132, "Auto color-cycle every 0.7s", 7)
        pyxel.text(112, 148, "Match 4 in a row for SUPER!", 10)
        pyxel.text(132, 170, "COMBO >= 4 = SUPER x3!", 2)
        pyxel.text(120, 200, "Press SPACE to start", 11)

    def _draw_playing(self) -> None:
        if self.shake_frames > 0:
            sx = self._rng.randint(-2, 2)
            sy = self._rng.randint(-2, 2)
            pyxel.camera(sx, sy)

        for gx, gy in self.best_ghost:
            pyxel.circ(int(gx), int(gy), 1, 12)

        for col, row in self.clouds:
            px = col * self.CELL
            py = row * self.CELL + self.CLOUD_OFFSET_Y
            pyxel.rect(px, py, self.CELL, self.CELL, 7)

        for ring in self.rings:
            if not ring.collected:
                pyxel.circb(int(ring.x), int(ring.y), self.RING_RADIUS, ring.color)

        for p in self.particles:
            pyxel.circ(int(p.x), int(p.y), 1, p.color)

        for ft in self.floating_texts:
            tw = len(ft.text) * 4
            pyxel.text(int(ft.x) - tw // 2, int(ft.y), ft.text, ft.color)

        if self.stun_timer > 0 and self.stun_timer % 4 < 2:
            pass
        else:
            if self.super_mode:
                for i in range(7):
                    angle = self.frame_count * 0.15 + i * math.pi * 2 / 7
                    ox = math.cos(angle) * (self.PLAYER_RADIUS + 3)
                    oy = math.sin(angle) * (self.PLAYER_RADIUS + 3)
                    color = 8 + ((i + self.frame_count // 4) % 7)
                    pyxel.circ(int(self.player_x + ox), int(self.PLAYER_Y + oy), 1, color)
            pyxel.circ(int(self.player_x), self.PLAYER_Y, self.PLAYER_RADIUS, self.player_color)
            pyxel.circb(int(self.player_x), self.PLAYER_Y, self.PLAYER_RADIUS + 1, 0)

        pyxel.camera(0, 0)

        pyxel.rect(0, 216, 320, 24, 0)
        pyxel.text(4, 218, f"SC:{self.score:05d}", 7)
        pyxel.text(66, 218, f"C:{self.combo}", 7)
        pyxel.text(100, 218, f"MX:{self.max_combo}", 7)

        heat_w = int(self.heat * 80 / self.HEAT_MAX)
        pyxel.rect(4, 226, 82, 5, 5)
        pyxel.rect(5, 227, heat_w, 3, 8)
        heat_pct = int(self.heat)
        pyxel.text(90, 225, f"HT:{heat_pct}%", 7)

        secs = self.timer // 30
        tc = 8 if secs <= 10 else 7
        pyxel.text(148, 225, f"T:{secs:02d}s", tc)

        if self.super_mode:
            super_w = int(self.super_timer * 320 / self.SUPER_DURATION)
            pyxel.rect(0, 0, 320, 8, 0)
            pyxel.rect(0, 0, super_w, 8, 2)
            pyxel.text(135, 0, "SUPER x3!", 10)

    def _draw_game_over(self) -> None:
        if self.heat >= self.HEAT_MAX:
            reason = "OVERHEATED!"
            rc = 8
        else:
            reason = "TIME UP!"
            rc = 10
        pyxel.text(136, 60, reason, rc)
        pyxel.text(120, 80, f"SCORE: {self.score}", 7)
        pyxel.text(120, 92, f"BEST: {self.best_score}", 7)
        pyxel.text(108, 104, f"MAX COMBO: {self.max_combo}", 7)
        pyxel.text(120, 130, "SPACE to retry", 11)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
