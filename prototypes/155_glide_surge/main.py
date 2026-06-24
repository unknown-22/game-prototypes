from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel

COLOR_VALS: tuple[int, int, int, int] = (8, 3, 6, 10)

SCREEN_W = 320
SCREEN_H = 240
MOUNTAIN_H = 20
PLAYER_W = 12
PLAYER_H = 8
PLAYER_SPEED = 2.5
GRAVITY = 0.3
THERMAL_LIFT = 3.0
WORLD_SCROLL_SPEED = 1.5
SUPER_DURATION = 300
MAX_HEAT = 100.0
HEAT_PER_MISMATCH = 15.0
HEAT_PER_BIRD = 20.0
TURBULENCE_DURATION = 120
COMBO_FOR_SUPER = 5
SCORE_PER_THERMAL = 100
SCORE_PER_RING = 50
MAX_THERMALS = 6
MAX_RINGS = 8
MAX_BIRDS = 3
COLOR_CYCLE_FRAMES = 180
THERMAL_SPAWN_MIN = 90
THERMAL_SPAWN_MAX = 150
RING_SPAWN_MIN = 60
RING_SPAWN_MAX = 120
BIRD_SPAWN_MIN = 180
BIRD_SPAWN_MAX = 300
SUPER_COLLECT_RADIUS = 60.0
TURBULENCE_KNOCKBACK_X = 3.0
TURBULENCE_KNOCKBACK_Y = 5.0

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


class ThermalColor(Enum):
    RED = 0
    GREEN = 1
    BLUE = 2
    YELLOW = 3

    def color_val(self) -> int:
        return COLOR_VALS[self.value]

    def next_color(self) -> ThermalColor:
        return ThermalColor((self.value + 1) % 4)


@dataclass
class Thermal:
    x: float
    width: int
    color: ThermalColor


@dataclass
class Ring:
    x: float
    y: float
    color: ThermalColor
    collected: bool = False


@dataclass
class Bird:
    x: float
    y: float
    vx: float
    base_y: float
    timer: float = 0.0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


class Game:
    _ALL_COLORS: ClassVar[list[int]] = [RED, GREEN, LIGHT_BLUE, YELLOW]

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="GLIDE SURGE", display_scale=2)
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.super_timer: int = 0
        self.player_x: float = 160.0
        self.player_y: float = 120.0
        self.player_color: ThermalColor = ThermalColor.RED
        self.scroll_x: float = 0.0
        self.thermals: list[Thermal] = []
        self.rings: list[Ring] = []
        self.birds: list[Bird] = []
        self.particles: list[Particle] = []
        self.turbulence_timer: int = 0
        self.screen_shake: int = 0
        self.game_timer: int = 0
        self.color_cycle_timer: int = COLOR_CYCLE_FRAMES
        self._rng: random.Random = random.Random()
        self._thermal_spawn_timer: int = 0
        self._ring_spawn_timer: int = 0
        self._bird_spawn_timer: int = 0
        self._in_thermal_this_frame: bool = False
        self._combo_flash_timer: int = 0
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_timer = 0
        self.player_x = 160.0
        self.player_y = 120.0
        self.player_color = ThermalColor.RED
        self.scroll_x = 0.0
        self.thermals = []
        self.rings = []
        self.birds = []
        self.particles = []
        self.turbulence_timer = 0
        self.screen_shake = 0
        self.game_timer = 0
        self.color_cycle_timer = COLOR_CYCLE_FRAMES
        self._thermal_spawn_timer = self._rng.randint(THERMAL_SPAWN_MIN, THERMAL_SPAWN_MAX)
        self._ring_spawn_timer = self._rng.randint(RING_SPAWN_MIN, RING_SPAWN_MAX)
        self._bird_spawn_timer = self._rng.randint(BIRD_SPAWN_MIN, BIRD_SPAWN_MAX)
        self._in_thermal_this_frame = False
        self._combo_flash_timer = 0

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.phase = Phase.TITLE
            return
        elif self.phase == Phase.PLAYING:
            self._update_playing()

    def _update_playing(self) -> None:
        self.game_timer += 1
        self._in_thermal_this_frame = False

        dx: float = 0.0
        dy: float = 0.0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx = -PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx = PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy = -PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy = PLAYER_SPEED

        if self.turbulence_timer > 0:
            dx += self._rng.uniform(-TURBULENCE_KNOCKBACK_X, TURBULENCE_KNOCKBACK_X)
            dy += self._rng.uniform(-TURBULENCE_KNOCKBACK_Y, TURBULENCE_KNOCKBACK_Y)

        self._update_player(dx, dy)
        self._update_physics()
        self._update_thermals()
        self._update_rings()
        self._update_birds()
        self._update_particles()

        if self.super_timer > 0:
            self._handle_super_tick()

        if self.turbulence_timer > 0:
            self._handle_turbulence_tick()

        self._update_heat()

        self.scroll_x += WORLD_SCROLL_SPEED

        self._cycle_player_color()

        if self._combo_flash_timer > 0:
            self._combo_flash_timer -= 1

        if self.screen_shake > 0:
            self.screen_shake -= 1

        if self._check_game_over():
            self.phase = Phase.GAME_OVER

    def _update_player(self, dx: float, dy: float) -> None:
        self.player_x += dx
        self.player_y += dy
        self.player_x = max(10.0, min(float(SCREEN_W - 10), self.player_x))
        self.player_y = max(10.0, min(float(SCREEN_H - MOUNTAIN_H - 5), self.player_y))

    def _update_physics(self) -> None:
        if self.super_timer > 0:
            return
        self.player_y += GRAVITY
        self.player_y = min(float(SCREEN_H - MOUNTAIN_H - 5), self.player_y)

        thermal = self._check_thermal_collision()
        if thermal is not None and not self._in_thermal_this_frame:
            self._in_thermal_this_frame = True
            self._handle_thermal_entry(thermal)

    def _spawn_thermal(self) -> Thermal:
        color = ThermalColor(self._rng.randint(0, 3))
        width = self._rng.randint(24, 40)
        x = SCREEN_W + self._rng.randint(10, 80)
        return Thermal(x=x, width=width, color=color)

    def _spawn_ring(self) -> Ring:
        color = ThermalColor(self._rng.randint(0, 3))
        x = SCREEN_W + self._rng.randint(20, 100)
        y = self._rng.uniform(30.0, float(SCREEN_H - MOUNTAIN_H - 30))
        return Ring(x=x, y=y, color=color)

    def _spawn_bird(self) -> Bird:
        base_y = self._rng.uniform(30.0, float(SCREEN_H - MOUNTAIN_H - 40))
        x = SCREEN_W + self._rng.randint(20, 60)
        vx = self._rng.uniform(-2.0, -1.0)
        return Bird(x=x, y=base_y, vx=vx, base_y=base_y, timer=self._rng.uniform(0.0, 6.28))

    def _update_thermals(self) -> None:
        self._thermal_spawn_timer -= 1
        if self._thermal_spawn_timer <= 0 and len(self.thermals) < MAX_THERMALS:
            self.thermals.append(self._spawn_thermal())
            self._thermal_spawn_timer = self._rng.randint(THERMAL_SPAWN_MIN, THERMAL_SPAWN_MAX)

        for t in self.thermals:
            t.x -= WORLD_SCROLL_SPEED
        self.thermals = [t for t in self.thermals if t.x + t.width > 0]

    def _update_rings(self) -> None:
        self._ring_spawn_timer -= 1
        if self._ring_spawn_timer <= 0 and len(self.rings) < MAX_RINGS:
            self.rings.append(self._spawn_ring())
            self._ring_spawn_timer = self._rng.randint(RING_SPAWN_MIN, RING_SPAWN_MAX)

        for r in self.rings:
            r.x -= WORLD_SCROLL_SPEED
        self.rings = [r for r in self.rings if r.x > -20]

        collected = self._check_ring_collision()
        for r in collected:
            r.collected = True
            self.rings.remove(r)

    def _update_birds(self) -> None:
        self._bird_spawn_timer -= 1
        if self._bird_spawn_timer <= 0 and len(self.birds) < MAX_BIRDS:
            self.birds.append(self._spawn_bird())
            self._bird_spawn_timer = self._rng.randint(BIRD_SPAWN_MIN, BIRD_SPAWN_MAX)

        for b in self.birds:
            b.x += b.vx
            b.timer += 0.03
            b.y = b.base_y + pyxel.sin(b.timer) * 15.0
        self.birds = [b for b in self.birds if b.x > -30]

        hit = self._check_bird_collision()
        if hit is not None:
            self.birds.remove(hit)  # type: ignore[arg-type]
            self.heat += HEAT_PER_BIRD
            self._spawn_particles(hit.x, hit.y, GRAY, 5)

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _check_thermal_collision(self) -> Thermal | None:
        for t in self.thermals:
            if (
                self.player_x > t.x
                and self.player_x < t.x + t.width
                and self.player_y < SCREEN_H - MOUNTAIN_H
            ):
                return t
        return None

    def _handle_thermal_entry(self, thermal: Thermal) -> None:
        if thermal.color == self.player_color:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            multiplier = self.combo
            gained = SCORE_PER_THERMAL * multiplier
            if self.super_timer > 0:
                gained *= 2
            self.score += gained
            self._spawn_particles(self.player_x, self.player_y, thermal.color.color_val(), 4)
            self._combo_flash_timer = 30
            if self.combo >= COMBO_FOR_SUPER and self.super_timer <= 0:
                self.super_timer = SUPER_DURATION
                self.turbulence_timer = 0
                self._spawn_super_particles()
                self.screen_shake = 5
        else:
            self.combo = 0
            self._combo_flash_timer = 0
            if self.super_timer <= 0:
                self.heat += HEAT_PER_MISMATCH
                self._spawn_particles(self.player_x, self.player_y, thermal.color.color_val(), 2)

    def _check_ring_collision(self) -> list[Ring]:
        collected: list[Ring] = []
        radius = SUPER_COLLECT_RADIUS if self.super_timer > 0 else 12.0
        for r in self.rings:
            dx = self.player_x - r.x
            dy = self.player_y - r.y
            if (dx * dx + dy * dy) < radius * radius:
                r.collected = True
                multiplier = 2 if self.super_timer > 0 else 1
                self.score += SCORE_PER_RING * multiplier
                self._spawn_particles(r.x, r.y, r.color.color_val(), 3)
                collected.append(r)
        return collected

    def _check_bird_collision(self) -> Bird | None:
        for b in self.birds:
            dx = self.player_x - b.x
            dy = self.player_y - b.y
            if abs(dx) < 10.0 and abs(dy) < 8.0:
                return b
        return None

    def _handle_super_tick(self) -> None:
        self.super_timer -= 1
        auto_collected = self._check_ring_collision()
        for r in auto_collected:
            if r in self.rings:
                self.rings.remove(r)

    def _handle_turbulence_tick(self) -> None:
        self.turbulence_timer -= 1
        self.screen_shake = self.turbulence_timer
        if self.turbulence_timer <= 0:
            self.screen_shake = 0

    def _update_heat(self) -> None:
        if self.heat >= MAX_HEAT and self.turbulence_timer <= 0 and self.super_timer <= 0:
            self.turbulence_timer = TURBULENCE_DURATION
            self.screen_shake = TURBULENCE_DURATION
            self.combo = 0
            self._combo_flash_timer = 0
        if self.turbulence_timer <= 0:
            self.heat = max(0.0, self.heat - 0.1)
        else:
            self.heat = 0.0

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-1.0, 1.0)
            vy = self._rng.uniform(-3.0, -1.0)
            life = self._rng.randint(15, 30)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def _spawn_super_particles(self) -> None:
        for c in [RED, GREEN, LIGHT_BLUE, YELLOW]:
            for _ in range(3):
                vx = self._rng.uniform(-2.0, 2.0)
                vy = self._rng.uniform(-4.0, -1.0)
                life = self._rng.randint(20, 40)
                self.particles.append(
                    Particle(x=self.player_x, y=self.player_y, vx=vx, vy=vy, life=life, color=c)
                )

    def _cycle_player_color(self) -> None:
        self.color_cycle_timer -= 1
        if self.color_cycle_timer <= 0:
            self.player_color = self.player_color.next_color()
            self.color_cycle_timer = COLOR_CYCLE_FRAMES

    def _check_game_over(self) -> bool:
        return self.player_y >= SCREEN_H - MOUNTAIN_H

    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.cls(LIGHT_BLUE)
        pyxel.text(110, 50, "GLIDE SURGE", WHITE)
        pyxel.text(115, 52, "GLIDE SURGE", ORANGE)

        px = 160.0
        py = 95.0
        pc = self.player_color.color_val()
        pyxel.tri(px, py - 4, px - 6, py + 4, px + 6, py + 4, pc)

        pyxel.text(85, 130, "PRESS SPACE TO START", WHITE)
        pyxel.text(60, 150, "Arrow keys to fly", WHITE)
        pyxel.text(40, 168, "Match thermal colors for COMBO", WHITE)
        pyxel.text(45, 186, "COMBO x5 = SUPER GLIDE!", YELLOW)

    def _draw_playing(self) -> None:
        shake_x: int = 0
        shake_y: int = 0
        if self.screen_shake > 0:
            shake_x = self._rng.randint(-2, 2)
            shake_y = self._rng.randint(-2, 2)

        pyxel.cls(CYAN)

        # Sky gradient bands
        for i in range(6):
            band_y = i * 35
            pyxel.rect(0, band_y, SCREEN_W, 10, LIGHT_BLUE if i % 2 == 0 else CYAN)

        # Mountains
        mountain_base_y = SCREEN_H - MOUNTAIN_H
        x: float = -(self.scroll_x % 40)
        while x < SCREEN_W + 40:
            h = self._mountain_height(x)
            peak_y = mountain_base_y - h
            pyxel.tri(
                x + shake_x, mountain_base_y + shake_y,
                x - 20 + shake_x, peak_y + shake_y,
                x + 20 + shake_x, peak_y + shake_y,
                BROWN,
            )
            pyxel.tri(
                x + shake_x, mountain_base_y + shake_y,
                x - 10 + shake_x, int(peak_y * 0.7 + mountain_base_y * 0.3) + shake_y,
                x + 10 + shake_x, int(peak_y * 0.7 + mountain_base_y * 0.3) + shake_y,
                BROWN,
            )
            x += 40

        # Ground
        pyxel.rect(0 + shake_x, mountain_base_y + shake_y, SCREEN_W, MOUNTAIN_H, DARK_BLUE)

        # Thermals
        for t in self.thermals:
            col = t.color.color_val()
            tx = int(t.x) + shake_x
            tw = t.width
            th = SCREEN_H - MOUNTAIN_H
            # Semi-transparent look: alternating vertical lines
            pyxel.rect(tx, shake_y, tw, th, col)
            for ly in range(shake_y, shake_y + th, 6):
                if (ly // 6) % 3 != 0:
                    pyxel.rect(tx, ly, tw, 4, BLACK)

            # Rising particles inside thermal
            p_count = int(tw * 0.3)
            for pi in range(p_count):
                p_x = tx + 3 + (pi * tw // max(p_count, 1))
                p_y = (shake_y + th - ((pyxel.frame_count * 2 + pi * 30) % th))
                pyxel.rect(p_x, p_y, 2, 2, WHITE if col == LIGHT_BLUE or col == YELLOW else col)

        # Rings
        for r in self.rings:
            if r.collected:
                continue
            pyxel.circb(int(r.x) + shake_x, int(r.y) + shake_y, 8, r.color.color_val())
            pyxel.circb(int(r.x) + shake_x, int(r.y) + shake_y, 7, WHITE)

        # Birds
        for b in self.birds:
            bx = int(b.x) + shake_x
            by = int(b.y) + shake_y
            pyxel.tri(bx - 4, by + 3, bx, by - 3, bx + 4, by + 3, NAVY)
            pyxel.tri(bx + 4, by + 3, bx, by - 3, bx + 8, by + 3, NAVY)

        # Player glider
        px = int(self.player_x) + shake_x
        py = int(self.player_y) + shake_y
        if self.super_timer > 0:
            color_idx = (pyxel.frame_count // 4) % 4
            pc = COLOR_VALS[color_idx]
        else:
            pc = self.player_color.color_val()
        pyxel.tri(px, py - 4, px - 6, py + 4, px + 6, py + 4, pc)
        pyxel.tri(px, py - 2, px - 4, py + 2, px + 4, py + 2, WHITE)

        if self.super_timer > 0:
            glow_colors = [RED, YELLOW, GREEN, LIGHT_BLUE]
            for gi, gc in enumerate(glow_colors):
                angle = pyxel.frame_count * 0.1 + gi * 1.57
                gx = px + int(pyxel.cos(angle) * 8)
                gy = py + int(pyxel.sin(angle) * 8)
                pyxel.rect(gx, gy, 2, 2, gc)

        # Particles
        for p in self.particles:
            pyxel.rect(int(p.x) + shake_x, int(p.y) + shake_y, 2, 2, p.color)

        # HUD
        pyxel.rect(0, 0, SCREEN_W, 28, BLACK)

        # Score
        pyxel.text(4, 2, f"SCORE: {self.score}", WHITE)

        # Player color indicator
        color_indicator_x = 4
        color_indicator_y = 12
        pyxel.text(color_indicator_x, color_indicator_y, "TARGET:", WHITE)
        pc2 = self.player_color.color_val()
        pyxel.rect(color_indicator_x + 38, color_indicator_y, 8, 8, pc2)

        # COMBO
        combo_text = f"COMBO: {self.combo}"
        combo_color = YELLOW
        if self._combo_flash_timer > 0 and self._combo_flash_timer % 6 < 3:
            combo_color = ORANGE
        pyxel.text(120, 2, combo_text, combo_color)

        # Max COMBO
        pyxel.text(120, 12, f"MAX: {self.max_combo}", GRAY)

        # HEAT bar
        heat_bar_x = 210
        heat_bar_w = 100
        pyxel.text(heat_bar_x, 2, "HEAT", WHITE)
        pyxel.rectb(heat_bar_x, 12, heat_bar_w, 10, WHITE)
        heat_ratio = min(1.0, self.heat / MAX_HEAT)
        heat_fill_w = int(heat_bar_w * heat_ratio)
        if heat_fill_w > 0:
            if heat_ratio < 0.35:
                heat_color = GREEN
            elif heat_ratio < 0.65:
                heat_color = YELLOW
            elif heat_ratio < 0.85:
                heat_color = ORANGE
            else:
                heat_color = RED
            pyxel.rect(heat_bar_x + 1, 13, heat_fill_w, 8, heat_color)

        # SUPER timer
        if self.super_timer > 0:
            super_bar_x = 80
            super_bar_w = 160
            super_ratio = self.super_timer / SUPER_DURATION
            super_fill_w = int(super_bar_w * super_ratio)
            super_label = "SUPER GLIDE!"
            pyxel.text(130, 22, super_label, YELLOW)
            color_idx2 = (pyxel.frame_count // 8) % 4
            pyxel.rect(super_bar_x + super_fill_w - 1, 34, 2, 4, COLOR_VALS[color_idx2])

        # TURBULENCE warning
        if self.turbulence_timer > 0:
            t_label = "TURBULENCE!"
            t_flash = WHITE if (pyxel.frame_count // 10) % 2 == 0 else RED
            pyxel.text(250, 22, t_label, t_flash)

    @staticmethod
    def _mountain_height(x: float) -> float:
        return 8.0 + abs(pyxel.sin(x * 0.05) * 12.0) + abs(pyxel.cos(x * 0.13) * 5.0)

    def _draw_game_over(self) -> None:
        pyxel.cls(BLACK)
        pyxel.text(95, 60, "GAME OVER", RED)
        pyxel.text(90, 62, "GAME OVER", WHITE)

        pyxel.text(100, 100, f"SCORE: {self.score}", WHITE)
        pyxel.text(85, 120, f"MAX COMBO: {self.max_combo}", YELLOW)

        pyxel.text(70, 160, "PRESS SPACE TO RETRY", WHITE)

        pyxel.text(75, 190, "GLIDE SURGE", GRAY)


if __name__ == "__main__":
    Game()
