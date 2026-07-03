from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel

# Color constants
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

# Ring colors
RING_COLORS: list[int] = [RED, GREEN, LIGHT_BLUE, YELLOW]
RING_COLOR_NAMES: list[str] = ["Red", "Green", "Blue", "Yellow"]

# Game constants
SCREEN_W = 320
SCREEN_H = 240
KITE_X = 80.0
KITE_SIZE = 12
RING_RADIUS = 10
MAX_HEAT = 100.0
HEAT_DECAY = 0.05
HEAT_PER_HIT = 20.0
SUPER_THRESHOLD = 5
SUPER_DURATION = 300
SUPER_SCORE_MULT = 3
BASE_RING_SCORE = 100
INVULN_DURATION = 60
WIND_BASE = 1.0
WIND_MAX = 3.5
WIND_INCREASE = 0.0002
KITE_GRAVITY = 0.15
KITE_MAX_VY = 4.0
KITE_ACCEL = 0.5
RING_SPAWN_INTERVAL_INIT = 90
RING_SPAWN_INTERVAL_MIN = 30
BIRD_SPAWN_INTERVAL_INIT = 180
BIRD_SPAWN_INTERVAL_MIN = 80
PARTICLE_MAX = 80
ECHO_MAX = 60
ECHO_INTERVAL = 3
ECHO_LIFE = 30


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Ring:
    x: float
    y: float
    color: int
    collected: bool = False


@dataclass
class Bird:
    x: float
    y: float
    vy: float
    width: int = 16
    height: int = 12
    alive: bool = True


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class EchoDot:
    x: float
    y: float
    life: int
    color: int


def darken_color(c: int) -> int:
    darker_map: dict[int, int] = {
        RED: PURPLE,
        GREEN: NAVY,
        LIGHT_BLUE: DARK_BLUE,
        YELLOW: BROWN,
        WHITE: GRAY,
        ORANGE: RED,
    }
    return darker_map.get(c, NAVY)


class Game:
    _initialized: ClassVar[bool] = False

    def __init__(self) -> None:
        if Game._initialized:
            return
        Game._initialized = True

        pyxel.init(SCREEN_W, SCREEN_H, title="Kite Surge", display_scale=2)
        self._rng = random.Random()
        self._pre_init_state()
        pyxel.run(self._update, self._draw)

    def _pre_init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.super_timer: int = 0
        self.kite_x: float = KITE_X
        self.kite_y: float = 120.0
        self.kite_vy: float = 0.0
        self.wind_speed: float = WIND_BASE
        self.scroll_x: float = 0.0
        self.invuln_timer: int = 0
        self.last_color: int | None = None
        self.rings: list[Ring] = []
        self.birds: list[Bird] = []
        self.particles: list[Particle] = []
        self.echo_dots: list[EchoDot] = []
        self.spawn_timer: int = 0
        self.bird_timer: int = 0
        self.game_time: int = 0
        self.shake_timer: int = 0
        self.shake_intensity: int = 0
        self.super_mode: bool = False
        self.frame: int = 0
        self.echo_frame_counter: int = 0
        self.super_flash_counter: int = 0

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_timer = 0
        self.kite_x = KITE_X
        self.kite_y = 120.0
        self.kite_vy = 0.0
        self.wind_speed = WIND_BASE
        self.scroll_x = 0.0
        self.invuln_timer = 0
        self.last_color = None
        self.rings.clear()
        self.birds.clear()
        self.particles.clear()
        self.echo_dots.clear()
        self.spawn_timer = 0
        self.bird_timer = 0
        self.game_time = 0
        self.shake_timer = 0
        self.shake_intensity = 0
        self.super_mode = False
        self.frame = 0
        self.echo_frame_counter = 0
        self.super_flash_counter = 0

    # --- Update ---

    def _update(self) -> None:
        self.frame = self.frame + 1

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()

    def _update_playing(self) -> None:
        self._handle_input()
        self._update_physics()
        self._update_super_mode()
        self._update_heat()
        self._update_particles()
        self._update_echo()

        scroll_speed = self.wind_speed
        self.scroll_x += scroll_speed

        self._update_rings(scroll_speed)
        self._update_birds(scroll_speed)

        self._check_ring_collisions()
        self._check_bird_collisions()

        self._spawn_rings()
        self._spawn_birds()

        self._update_difficulty()

        self.game_time += 1

        if self._is_game_over():
            self.phase = Phase.GAME_OVER

        if self.invuln_timer > 0:
            self.invuln_timer -= 1

        if self.shake_timer > 0:
            self.shake_timer -= 1
            if self.shake_timer == 0:
                pyxel.camera(0, 0)

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.TITLE

    def _handle_input(self) -> None:
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            self.kite_vy -= KITE_ACCEL
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            self.kite_vy += KITE_ACCEL

        speed_mod: float = 0.0
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            speed_mod = 0.5
        elif pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            speed_mod = -0.3

        self.wind_speed = max(
            WIND_BASE, min(WIND_MAX, self.wind_speed + speed_mod * 0.01)
        )

    def _update_physics(self) -> None:
        self.kite_vy += KITE_GRAVITY
        self.kite_vy = max(-KITE_MAX_VY, min(KITE_MAX_VY, self.kite_vy))
        self.kite_y += self.kite_vy

        margin = KITE_SIZE
        self.kite_y = max(float(margin), min(float(SCREEN_H - margin), self.kite_y))
        if self.kite_y <= margin or self.kite_y >= SCREEN_H - margin:
            self.kite_vy *= -0.3

    def _update_super_mode(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
            self.super_flash_counter = (self.super_flash_counter + 1) % (4 * 8)
            if self.super_timer == 0:
                self.super_mode = False
                self.super_flash_counter = 0

    def _update_heat(self) -> None:
        if self.heat > 0:
            self.heat -= HEAT_DECAY
            if self.heat < 0:
                self.heat = 0.0

    def _update_rings(self, scroll_speed: float) -> None:
        for ring in self.rings:
            ring.x -= scroll_speed
        self.rings = [
            r for r in self.rings if r.x > -RING_RADIUS * 2 and not r.collected
        ]

    def _update_birds(self, scroll_speed: float) -> None:
        for bird in self.birds:
            bird.x -= scroll_speed
            bird.y += bird.vy
            if bird.y < 20 or bird.y > SCREEN_H - 20:
                bird.vy = -bird.vy
                bird.y = max(20.0, min(float(SCREEN_H - 20), bird.y))
            if not bird.alive:
                bird.x -= 999
        self.birds = [b for b in self.birds if b.x > -50 and b.alive]

    def _check_ring_collisions(self) -> None:
        for ring in self.rings:
            if ring.collected:
                continue
            dx = self.kite_x - ring.x
            dy = self.kite_y - ring.y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < RING_RADIUS + KITE_SIZE * 0.5:
                self._handle_ring_collect(ring)

    def _check_bird_collisions(self) -> None:
        if self.invuln_timer > 0:
            return
        for bird in self.birds:
            if not bird.alive:
                continue
            if (
                abs(self.kite_x - bird.x) < (KITE_SIZE + bird.width) * 0.5
                and abs(self.kite_y - bird.y) < (KITE_SIZE + bird.height) * 0.5
            ):
                self._handle_bird_hit()
                bird.alive = False
                break

    def _handle_ring_collect(self, ring: Ring) -> None:
        if ring.collected:
            return
        ring.collected = True

        if self.super_mode:
            self.combo += 1
            score_mult = SUPER_SCORE_MULT
            self._spawn_super_particles(ring.x, ring.y)
        else:
            if self.last_color is not None and ring.color == self.last_color:
                self.combo += 1
            else:
                self.combo = 1
            self.last_color = ring.color
            score_mult = 1
            self._spawn_collect_particles(ring.x, ring.y, ring.color)

        if self.combo > self.max_combo:
            self.max_combo = self.combo

        self.score += BASE_RING_SCORE * score_mult

        if self.combo >= SUPER_THRESHOLD and not self.super_mode:
            self.super_mode = True
            self.super_timer = SUPER_DURATION
            self.super_flash_counter = 0

    def _handle_bird_hit(self) -> None:
        self.heat += HEAT_PER_HIT
        if self.heat > MAX_HEAT:
            self.heat = MAX_HEAT
        self.combo = 0
        self.last_color = None
        self.invuln_timer = INVULN_DURATION
        self.shake_timer = 8
        self.shake_intensity = 3
        self._spawn_hit_particles(self.kite_x, self.kite_y)

    def _is_game_over(self) -> bool:
        return self.heat >= MAX_HEAT

    # --- Spawning ---

    def _get_spawn_interval_ring(self) -> int:
        ratio = min(1.0, self.game_time / 3600.0)
        return int(
            RING_SPAWN_INTERVAL_INIT
            - (RING_SPAWN_INTERVAL_INIT - RING_SPAWN_INTERVAL_MIN) * ratio
        )

    def _get_spawn_interval_bird(self) -> int:
        ratio = min(1.0, self.game_time / 3600.0)
        return int(
            BIRD_SPAWN_INTERVAL_INIT
            - (BIRD_SPAWN_INTERVAL_INIT - BIRD_SPAWN_INTERVAL_MIN) * ratio
        )

    def _spawn_rings(self) -> None:
        self.spawn_timer += 1
        interval = self._get_spawn_interval_ring()
        if self.spawn_timer >= interval:
            self.spawn_timer = 0
            ring = self._spawn_ring()
            self.rings.append(ring)

    def _spawn_ring(self) -> Ring:
        x = SCREEN_W + RING_RADIUS + self.wind_speed * 2
        y = self._rng.uniform(40, SCREEN_H - 40)
        if self.last_color is not None and self._rng.random() < 0.4:
            color = self.last_color
        else:
            color = self._rng.choice(RING_COLORS)
        return Ring(x=x, y=y, color=color)

    def _spawn_birds(self) -> None:
        self.bird_timer += 1
        interval = self._get_spawn_interval_bird()
        if self.bird_timer >= interval:
            self.bird_timer = 0
            bird = self._spawn_bird()
            self.birds.append(bird)

    def _spawn_bird(self) -> Bird:
        x = SCREEN_W + 30
        y = self._rng.uniform(60, SCREEN_H - 60)
        vy = self._rng.choice([-1.0, -2.0, 1.0, 2.0])
        return Bird(x=x, y=y, vy=vy)

    def _update_difficulty(self) -> None:
        self.wind_speed = min(
            WIND_MAX,
            self.wind_speed + WIND_INCREASE,
        )

    # --- Particles ---

    def _spawn_collect_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(5):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-2, 2),
                    vy=self._rng.uniform(-2, 2),
                    life=self._rng.randint(15, 25),
                    color=color,
                )
            )

    def _spawn_super_particles(self, x: float, y: float) -> None:
        for _ in range(8):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-3, 3),
                    vy=self._rng.uniform(-3, 3),
                    life=self._rng.randint(20, 30),
                    color=self._rng.choice(RING_COLORS),
                )
            )

    def _spawn_hit_particles(self, x: float, y: float) -> None:
        for _ in range(10):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-3, 3),
                    vy=self._rng.uniform(-3, 3),
                    life=self._rng.randint(20, 30),
                    color=self._rng.choice([RED, ORANGE]),
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]
        while len(self.particles) > PARTICLE_MAX:
            self.particles.pop(0)

    # --- Echo Trail ---

    def _update_echo(self) -> None:
        self.echo_frame_counter += 1
        if self.echo_frame_counter >= ECHO_INTERVAL:
            self.echo_frame_counter = 0
            color = self.last_color if self.last_color is not None else WHITE
            if self.super_mode:
                color = self._get_super_kite_color()
            self.echo_dots.append(
                EchoDot(x=self.kite_x, y=self.kite_y, life=ECHO_LIFE, color=color)
            )

        for dot in self.echo_dots:
            dot.life -= 1
        self.echo_dots = [d for d in self.echo_dots if d.life > 0]
        while len(self.echo_dots) > ECHO_MAX:
            self.echo_dots.pop(0)

    # --- Drawing ---

    def _draw(self) -> None:
        if self.shake_timer > 0:
            if not hasattr(self, "_shake_rng"):
                self._shake_rng = random.Random()
            shx = self._shake_rng.randint(-self.shake_intensity, self.shake_intensity)
            shy = self._shake_rng.randint(-self.shake_intensity, self.shake_intensity)
            pyxel.camera(shx, shy)
        else:
            pyxel.camera(0, 0)

        pyxel.cls(NAVY)
        self._draw_sky_gradient()

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game()
            self._draw_game_over_overlay()

    def _draw_sky_gradient(self) -> None:
        for y in range(0, SCREEN_H, 2):
            if y < 80:
                c = LIGHT_BLUE
            elif y < 160:
                c = NAVY
            else:
                c = DARK_BLUE
            pyxel.rect(0, y, SCREEN_W, 2, c)

    def _draw_title(self) -> None:
        title = "KITE SURGE"
        tw = len(title) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 60, title, WHITE)

        pyxel.text(SCREEN_W // 2 - 80, 100, "Fly through same-color rings!", WHITE)
        pyxel.text(SCREEN_W // 2 - 72, 112, "Build COMBO -> SUPER FLIGHT!", GREEN)
        pyxel.text(SCREEN_W // 2 - 56, 140, "SPACE to start", YELLOW)

        kite_dx = int((pyxel.frame_count * 0.5) % 40) - 20
        self._draw_kite_shape(SCREEN_W // 2 + kite_dx, 180, WHITE)

        pyxel.text(SCREEN_W // 2 - 64, 210, "UP/DOWN: move  LEFT/RIGHT: speed", GRAY)

    def _draw_game(self) -> None:
        self._draw_echo_trail()
        self._draw_rings()
        self._draw_birds()
        if self.invuln_timer == 0 or self.invuln_timer % 4 < 2:
            kite_color = (
                self._get_super_kite_color() if self.super_mode else WHITE
            )
            self._draw_kite_shape(self.kite_x, self.kite_y, kite_color)
        self._draw_particles()
        self._draw_hud()

    def _draw_game_over_overlay(self) -> None:
        pyxel.rect(SCREEN_W // 2 - 70, SCREEN_H // 2 - 40, 140, 80, BLACK)
        pyxel.rectb(SCREEN_W // 2 - 70, SCREEN_H // 2 - 40, 140, 80, RED)
        pyxel.text(SCREEN_W // 2 - 22, SCREEN_H // 2 - 30, "GAME OVER", RED)

        score_str = f"Score: {self.score}"
        pyxel.text(
            SCREEN_W // 2 - len(score_str) * 2, SCREEN_H // 2 - 10, score_str, WHITE
        )
        combo_str = f"Max Combo: {self.max_combo}"
        pyxel.text(
            SCREEN_W // 2 - len(combo_str) * 2, SCREEN_H // 2, combo_str, GREEN
        )
        pyxel.text(SCREEN_W // 2 - 44, SCREEN_H // 2 + 20, "SPACE to retry", YELLOW)

    def _draw_kite_shape(self, x: float, y: float, color: int) -> None:
        xi = int(x)
        yi = int(y)
        hs = KITE_SIZE // 2
        pyxel.tri(xi, yi - hs, xi - hs, yi, xi, yi + hs, color)
        pyxel.tri(xi, yi + hs, xi + hs, yi, xi, yi - hs, color)
        line_x = int(x) - 30
        line_y = int(y) + 30
        if line_y > SCREEN_H:
            line_y = SCREEN_H
        pyxel.line(xi, yi + hs, line_x, line_y, GRAY)
        pyxel.line(xi + 2, yi + hs, line_x + 2, line_y, GRAY)

    def _get_super_kite_color(self) -> int:
        colors = [RED, GREEN, LIGHT_BLUE, YELLOW]
        idx = (self.super_flash_counter // 8) % len(colors)
        return colors[idx]

    def _draw_rings(self) -> None:
        for ring in self.rings:
            if ring.collected:
                continue
            xi = int(ring.x)
            yi = int(ring.y)
            r = RING_RADIUS
            pyxel.circb(xi, yi, r, ring.color)
            pyxel.circb(xi, yi, r - 2, ring.color)

    def _draw_birds(self) -> None:
        for bird in self.birds:
            if not bird.alive:
                continue
            xi = int(bird.x)
            yi = int(bird.y)
            pyxel.tri(xi - 8, yi, xi, yi - 6, xi + 8, yi, DARK_BLUE)
            pyxel.rect(xi - 2, yi, 4, 3, DARK_BLUE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 30.0
            if alpha > 0.3:
                pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_echo_trail(self) -> None:
        for dot in self.echo_dots:
            alpha = dot.life / ECHO_LIFE
            if alpha > 0.3:
                shade = dot.color if alpha > 0.6 else darken_color(dot.color)
                pyxel.pset(int(dot.x), int(dot.y), shade)

    def _draw_hud(self) -> None:
        score_str = f"SCORE: {self.score}"
        pyxel.text(4, 4, score_str, WHITE)

        combo_str = f"COMBO: {self.combo}x"
        combo_color = WHITE
        if self.combo >= SUPER_THRESHOLD:
            combo_color = YELLOW
        elif self.combo >= 3:
            combo_color = GREEN
        pyxel.text(4, 14, combo_str, combo_color)

        bar_x = SCREEN_W - 70
        bar_y = 6
        bar_w = 60
        bar_h = 6
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        fill_w = int(bar_w * (1.0 - self.heat / MAX_HEAT))
        fill_color = GREEN
        if self.heat > 60:
            fill_color = ORANGE
        if self.heat > 80:
            fill_color = RED
        pyxel.rect(bar_x, bar_y, fill_w, bar_h, fill_color)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)

        heat_str = f"HEAT: {int(self.heat)}"
        pyxel.text(bar_x, bar_y + 8, heat_str, fill_color)

        if self.super_mode:
            super_sec = self.super_timer / 60.0
            super_str = f"SUPER! {super_sec:.1f}s"
            pyxel.text(SCREEN_W // 2 - len(super_str) * 2, 4, super_str, YELLOW)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
