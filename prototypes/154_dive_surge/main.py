"""
DIVE SURGE — Cliff Diving / High Diving
Color-coded splash zone combo chaining with SUPER DIVE activation.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ───────────────────────────────────────────────────────────────
WIDTH = 320
HEIGHT = 240
WATER_Y = 190
PLATFORM_X = 160
PLATFORM_WIDTH = 60
PLATFORM_HEIGHT = 8
INITIAL_PLATFORM_Y = 60
PLATFORM_RISE = 8
MIN_PLATFORM_Y = 15
DIVER_WIDTH = 6
DIVER_HEIGHT = 10
ZONE_WIDTH = 48.0
ZONE_HEIGHT = 16.0
ZONE_Y = WATER_Y + 6
GRAVITY = 0.3
ROTATION_SPEED = 3.0
HORIZONTAL_DRIFT = 0.1
MAX_HEAT = 100.0
HEAT_DECAY = 0.05
SUPER_DURATION = 150
SPLASH_DELAY = 30
COMBO_SUPER_THRESHOLD = 5
SUPER_SCORE_MULT = 3
GHOST_POINT_INTERVAL = 2
GHOST_LIFE = 90
PARTICLE_GRAVITY = 0.1
SPLASH_FLASH_FRAMES = 10

# Colors
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

ZONE_COLORS = [GREEN, RED, LIGHT_BLUE, YELLOW]
SUPER_RAINBOW = [RED, ORANGE, YELLOW, GREEN, CYAN, LIGHT_BLUE, PURPLE]


# ── Enums ───────────────────────────────────────────────────────────────────
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class DiveState(Enum):
    READY = auto()
    AIRBORNE = auto()
    SPLASH = auto()


# ── Data Classes ────────────────────────────────────────────────────────────
@dataclass
class SplashZone:
    x: float
    y: float
    width: float = ZONE_WIDTH
    height: float = ZONE_HEIGHT
    color: int = GREEN


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


@dataclass
class TrailPoint:
    x: float
    y: float
    life: int


# ── Game Class ──────────────────────────────────────────────────────────────
class Game:
    def __init__(self) -> None:
        pyxel.init(WIDTH, HEIGHT, title="DIVE SURGE")
        self.rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self, seed: int | None = None) -> None:
        if seed is not None:
            self.rng = random.Random(seed)

        self.phase: Phase = Phase.TITLE
        self.dive_state: DiveState = DiveState.READY
        self.diver_x: float = float(PLATFORM_X)
        self.diver_y: float = float(INITIAL_PLATFORM_Y - DIVER_HEIGHT)
        self.diver_vx: float = 0.0
        self.diver_vy: float = 0.0
        self.diver_rotation: float = 0.0
        self.diver_rotation_speed: float = 0.0
        self.platform_y: float = float(INITIAL_PLATFORM_Y)
        self.dive_count: int = 0
        self.zones: list[SplashZone] = []
        self.zone_count: int = 5
        self.last_zone_color: int = -1
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.high_score: int = 0
        self.base_height_points: int = 10
        self.super_dive: bool = False
        self.super_timer: int = 0
        self.heat: float = 0.0
        self.particles: list[Particle] = []
        self.ghost_trail: list[TrailPoint] = []
        self.splash_flash: int = 0
        self.text_popups: list[tuple[str, float, float, int]] = []
        self.splash_delay: int = 0
        self.frame: int = 0

        self._spawn_zones_for_current_dive()

    # ── Zone Generation ─────────────────────────────────────────────────
    def _spawn_zones(self, seed: int | None = None) -> list[SplashZone]:
        """Generate splash zones deterministically."""
        rng = random.Random(seed) if seed is not None else self.rng
        count = rng.randint(4, 6)
        zones: list[SplashZone] = []
        zy = float(ZONE_Y)
        min_x = 30.0
        max_x = 290.0
        available_width = max_x - min_x
        spacing = (available_width - ZONE_WIDTH * count) / max(count - 1, 1)
        spacing = max(spacing, 0.0)
        spacing = min(spacing, ZONE_WIDTH)
        for i in range(count):
            x = min_x + i * (ZONE_WIDTH + spacing) + ZONE_WIDTH / 2
            x += rng.uniform(-spacing * 0.3, spacing * 0.3)
            x = max(min_x + ZONE_WIDTH / 2, min(x, max_x - ZONE_WIDTH / 2))
            color = rng.choice(ZONE_COLORS)
            zones.append(SplashZone(x=x, y=zy, width=ZONE_WIDTH, height=ZONE_HEIGHT, color=color))
        return zones

    def _spawn_zones_for_current_dive(self) -> None:
        self.zones = self._spawn_zones()

    # ── Jump ────────────────────────────────────────────────────────────
    def _jump(self) -> None:
        self.dive_state = DiveState.AIRBORNE
        self.diver_vy = 0.0
        self.diver_vx = 0.0
        self.base_height_points = max(1, int((INITIAL_PLATFORM_Y - self.platform_y) / 2) + 10)

    # ── Airborne Update ─────────────────────────────────────────────────
    def _update_airborne(self, dt: float = 1.0) -> None:
        self.diver_vy += GRAVITY * dt
        self.diver_x += self.diver_vx * dt
        self.diver_y += self.diver_vy * dt
        self.diver_rotation += self.diver_rotation_speed * dt
        self.diver_rotation %= 360.0
        if self.diver_rotation < 0:
            self.diver_rotation += 360.0
        self.diver_vx += self.diver_rotation_speed * HORIZONTAL_DRIFT * dt

    # ── Landing Check ───────────────────────────────────────────────────
    def _check_landing(self) -> int | None:
        """Returns zone index if diver center overlaps a splash zone, else None."""
        cx = self.diver_x
        cy = self.diver_y + DIVER_HEIGHT / 2
        water_surface = float(WATER_Y)
        if cy < water_surface:
            return None
        for i, zone in enumerate(self.zones):
            left = zone.x - zone.width / 2
            right = zone.x + zone.width / 2
            top = zone.y - zone.height / 2
            bottom = zone.y + zone.height / 2
            if left <= cx <= right and top <= cy <= bottom:
                return i
        return None

    # ── Apply Landing ───────────────────────────────────────────────────
    def _apply_landing(self, zone_idx: int | None) -> None:
        if zone_idx is not None:
            zone = self.zones[zone_idx]
            color = zone.color
            is_super = self._is_super_dive_active()

            if is_super or self.last_zone_color == -1 or color == self.last_zone_color:
                self.combo += 1
                if self.combo > self.max_combo:
                    self.max_combo = self.combo
                self.last_zone_color = color
            else:
                self.combo = 1
                self.last_zone_color = color

            earned = self._compute_score(color)
            self.score += earned
            self._spawn_splash_particles(zone.x, zone.y, color)
            text = f"+{earned}"
            if self.combo >= 3:
                text = f"COMBO x{self.combo}! +{earned}"
            self.text_popups.append((text, float(zone.x), float(zone.y - 10), 40))
            self.splash_flash = SPLASH_FLASH_FRAMES

            if self.combo >= COMBO_SUPER_THRESHOLD and not self.super_dive:
                self._activate_super_dive()
        else:
            self.combo = 0
            self.last_zone_color = -1
            self.heat = min(self.heat + 25.0, MAX_HEAT)
            self._spawn_splash_particles(self.diver_x, float(WATER_Y + 20), WHITE)
            self.text_popups.append(("MISS! +25 HEAT", self.diver_x - 30, float(WATER_Y - 5), 40))

    def _compute_score(self, zone_color: int) -> int:
        multiplier = 1.0 + self.combo * 0.5
        if self._is_super_dive_active():
            multiplier *= SUPER_SCORE_MULT
        return max(1, int(self.base_height_points * multiplier))

    def _is_super_dive_active(self) -> bool:
        return self.super_dive and self.super_timer > 0

    def _activate_super_dive(self) -> None:
        self.super_dive = True
        self.super_timer = SUPER_DURATION
        self.text_popups.append(("SUPER DIVE!", float(WIDTH / 2 - 30), float(HEIGHT / 2), 60))

    # ── Splash Particles ────────────────────────────────────────────────
    def _spawn_splash_particles(self, x: float, y: float, color: int) -> list[Particle]:
        count = 20 if self.super_dive else (8 + self.rng.randint(0, 4))
        particles: list[Particle] = []
        for _ in range(count):
            vx = self.rng.uniform(-2.0, 2.0)
            vy = self.rng.uniform(-3.0, -1.0)
            life = self.rng.randint(15, 30)
            p_color = color if not self.super_dive else self.rng.choice(SUPER_RAINBOW)
            particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=p_color))
        self.particles.extend(particles)
        return particles

    def _update_particles(self) -> None:
        for p in self.particles:
            p.vy += PARTICLE_GRAVITY
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ── Ghost Trail ─────────────────────────────────────────────────────
    def _update_ghost_trail(self) -> None:
        if self.dive_state == DiveState.AIRBORNE and self.frame % GHOST_POINT_INTERVAL == 0:
            self.ghost_trail.append(TrailPoint(x=self.diver_x, y=self.diver_y, life=GHOST_LIFE))
        for t in self.ghost_trail:
            t.life -= 1
        self.ghost_trail = [t for t in self.ghost_trail if t.life > 0]

    # ── Heat ─────────────────────────────────────────────────────────────
    def _update_heat(self) -> None:
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    # ── Super Dive Timer ────────────────────────────────────────────────
    def _update_super_dive(self) -> None:
        if self.super_dive:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_dive = False
                self.super_timer = 0
                self.text_popups.append(("SUPER ENDED", float(WIDTH / 2 - 35), float(HEIGHT / 2), 30))

    # ── Start Playing ───────────────────────────────────────────────────
    def _start_playing(self) -> None:
        self.reset()
        self.phase = Phase.PLAYING
        self.dive_state = DiveState.READY
        self.diver_x = float(PLATFORM_X)
        self.platform_y = float(INITIAL_PLATFORM_Y)
        self.diver_y = self.platform_y - float(DIVER_HEIGHT)
        self._spawn_zones_for_current_dive()

    # ── Next Dive ───────────────────────────────────────────────────────
    def _next_dive(self) -> None:
        self.dive_count += 1
        self.platform_y = max(float(MIN_PLATFORM_Y), self.platform_y - float(PLATFORM_RISE))
        self.diver_x = float(PLATFORM_X)
        self.diver_y = self.platform_y - float(DIVER_HEIGHT)
        self.diver_vx = 0.0
        self.diver_vy = 0.0
        self.diver_rotation = 0.0
        self.diver_rotation_speed = 0.0
        self.ghost_trail.clear()
        self.dive_state = DiveState.READY
        self._spawn_zones_for_current_dive()

    # ── Title / Game Over helper ────────────────────────────────────────
    def _title_screen_animation(self) -> float:
        return math.sin(pyxel.frame_count * 0.05) * 2.0

    # ── Update ──────────────────────────────────────────────────────────
    def update(self) -> None:
        self.frame += 1

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self._start_playing()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
                self.phase = Phase.TITLE
            return

        # PLAYING phase
        self._update_particles()
        self._update_ghost_trail()
        self._update_heat()
        self._update_super_dive()

        if self.splash_flash > 0:
            self.splash_flash -= 1

        for i, (text, _, _, life) in enumerate(self.text_popups):
            self.text_popups[i] = (text, self.text_popups[i][1], self.text_popups[i][2], life - 1)
        self.text_popups = [(t, x, y, life) for t, x, y, life in self.text_popups if life > 0]

        if self.dive_state == DiveState.READY:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self._jump()

        elif self.dive_state == DiveState.AIRBORNE:
            self.diver_rotation_speed = 0.0
            if pyxel.btn(pyxel.KEY_LEFT):
                self.diver_rotation_speed -= ROTATION_SPEED
            if pyxel.btn(pyxel.KEY_RIGHT):
                self.diver_rotation_speed += ROTATION_SPEED
            self._update_airborne(1.0)
            if self.diver_y + DIVER_HEIGHT / 2 >= WATER_Y:
                zone_idx = self._check_landing()
                self._apply_landing(zone_idx)
                if self.heat >= MAX_HEAT:
                    self.phase = Phase.GAME_OVER
                    if self.score > self.high_score:
                        self.high_score = self.score
                self.dive_state = DiveState.SPLASH
                self.splash_delay = SPLASH_DELAY

        elif self.dive_state == DiveState.SPLASH:
            self.splash_delay -= 1
            if self.splash_delay <= 0:
                if self.phase == Phase.GAME_OVER:
                    return
                self._next_dive()

    # ── Draw ────────────────────────────────────────────────────────────
    def draw(self) -> None:
        pyxel.cls(NAVY)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game()
            self._draw_game_over()

    def _draw_sky(self) -> None:
        for y in range(WATER_Y):
            t = y / WATER_Y
            r = int(NAVY + (DARK_BLUE - NAVY) * t) if DARK_BLUE > NAVY else int(NAVY - (NAVY - DARK_BLUE) * t)
            r = max(0, min(15, r))
            pyxel.rect(0, y, WIDTH, 1, r)

    def _draw_water(self) -> None:
        pyxel.rect(0, WATER_Y, WIDTH, HEIGHT - WATER_Y, DARK_BLUE)
        pyxel.line(0, WATER_Y, WIDTH, WATER_Y, WHITE)
        for x in range(0, WIDTH, 8):
            wave = int(math.sin((x + pyxel.frame_count * 2) * 0.1) * 2)
            pyxel.pset(x, WATER_Y + wave, WHITE)

    def _draw_diver(self, x: float, y: float, rotation: float, color: int, alpha: bool = False) -> None:
        rad = math.radians(rotation)
        half_w = DIVER_WIDTH / 2
        half_h = DIVER_HEIGHT / 2
        cx = x
        cy = y + half_h

        corners = [
            (-half_w, -half_h),
            (half_w, -half_h),
            (half_w, half_h),
            (-half_w, half_h),
        ]

        pts: list[tuple[float, float]] = []
        for dx, dy in corners:
            rx = dx * math.cos(rad) - dy * math.sin(rad)
            ry = dx * math.sin(rad) + dy * math.cos(rad)
            pts.append((cx + rx, cy + ry))

        if alpha:
            pyxel.tri(
                pts[0][0], pts[0][1],
                pts[1][0], pts[1][1],
                pts[2][0], pts[2][1],
                color,
            )
            pyxel.tri(
                pts[0][0], pts[0][1],
                pts[2][0], pts[2][1],
                pts[3][0], pts[3][1],
                color,
            )
        else:
            pyxel.tri(
                pts[0][0], pts[0][1],
                pts[1][0], pts[1][1],
                pts[2][0], pts[2][1],
                color,
            )
            pyxel.tri(
                pts[0][0], pts[0][1],
                pts[2][0], pts[2][1],
                pts[3][0], pts[3][1],
                color,
            )

    def _draw_ghost_trail(self) -> None:
        for t in self.ghost_trail:
            alpha = t.life / GHOST_LIFE
            radius = 3.0 * alpha
            if radius >= 1:
                pyxel.circ(int(t.x), int(t.y), max(1, int(radius)), GRAY)

    def _draw_zones(self) -> None:
        for zone in self.zones:
            left = int(zone.x - zone.width / 2)
            top = int(zone.y - zone.height / 2)
            pyxel.rect(left, top, int(zone.width), int(zone.height), zone.color)
            pyxel.rectb(left, top, int(zone.width), int(zone.height), WHITE)

    def _draw_platform(self) -> None:
        py = int(self.platform_y)
        left = PLATFORM_X - PLATFORM_WIDTH // 2
        bob = 0
        if self.phase == Phase.TITLE:
            bob = int(self._title_screen_animation())
        elif self.dive_state == DiveState.READY:
            bob = int(math.sin(pyxel.frame_count * 0.1) * 2)
        pyxel.rect(left, py + bob, PLATFORM_WIDTH, PLATFORM_HEIGHT, BROWN)
        pyxel.rect(left + 2, py + bob - 2, PLATFORM_WIDTH - 4, 2, PEACH)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)
        combo_text = f"COMBO: {self.combo}"
        pyxel.text(WIDTH // 2 - len(combo_text) * 2, 4, combo_text, WHITE)

        bar_x = WIDTH - 84
        bar_y = 4
        bar_w = 80
        bar_h = 6
        pyxel.rectb(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2, WHITE)
        fill = int(bar_w * (self.heat / MAX_HEAT))
        pyxel.rect(bar_x, bar_y, fill, bar_h, RED)
        pyxel.text(bar_x, bar_y + 8, "HEAT", GRAY)

        if self.super_dive and self.super_timer > 0:
            color_idx = (pyxel.frame_count // 4) % len(SUPER_RAINBOW)
            pyxel.text(WIDTH // 2 - 22, 16, "SUPER!", SUPER_RAINBOW[color_idx])

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 30.0
            size = max(1, int(p.size * alpha))
            pyxel.circ(int(p.x), int(p.y), size, p.color)

    def _draw_text_popups(self) -> None:
        for text, x, y, _life in self.text_popups:
            tx = int(x - len(text) * 2)
            ty = int(y)
            is_combo = text.startswith("COMBO")
            is_super = text.startswith("SUPER")
            is_miss = text.startswith("MISS")
            if is_super:
                cidx = (pyxel.frame_count // 4) % len(SUPER_RAINBOW)
                pyxel.text(tx, ty, text, SUPER_RAINBOW[cidx])
            elif is_combo:
                pyxel.text(tx, ty, text, YELLOW)
            elif is_miss:
                pyxel.text(tx, ty, text, RED)
            else:
                pyxel.text(tx, ty, text, WHITE)

    def _draw_splash_flash(self) -> None:
        if self.splash_flash > 0 and self.splash_flash % 2 == 0:
            pyxel.rect(0, WATER_Y, WIDTH, HEIGHT - WATER_Y, WHITE)

    def _draw_title(self) -> None:
        self._draw_sky()
        self._draw_platform()
        bob = self._title_screen_animation()
        self._draw_diver(PLATFORM_X, self.platform_y - DIVER_HEIGHT + bob, 0, WHITE)
        self._draw_water()
        self._draw_zones()
        self._draw_particles()

        pyxel.text(WIDTH // 2 - 22, 60, "DIVE SURGE", WHITE)
        if self.high_score > 0:
            hs_text = f"HIGH SCORE: {self.high_score}"
            pyxel.text(WIDTH // 2 - len(hs_text) * 2, 80, hs_text, YELLOW)
        pyxel.text(WIDTH // 2 - 55, 110, "Press SPACE to play", GRAY)
        pyxel.text(WIDTH // 2 - 70, 130, "LEFT/RIGHT: Rotate in air", GRAY)
        pyxel.text(WIDTH // 2 - 45, 145, "Land in same color", GRAY)
        pyxel.text(WIDTH // 2 - 50, 160, "to build COMBO chain!", GRAY)
        pyxel.text(WIDTH // 2 - 42, 180, "COMBO x5 = SUPER!", YELLOW)

    def _draw_game(self) -> None:
        self._draw_sky()
        self._draw_platform()

        if self.dive_state == DiveState.READY:
            bob = math.sin(pyxel.frame_count * 0.1) * 2
            self._draw_diver(PLATFORM_X, self.platform_y - DIVER_HEIGHT + bob, 0, WHITE)

        self._draw_ghost_trail()

        diver_color = WHITE
        if self.super_dive and self.super_timer > 0:
            diver_color = SUPER_RAINBOW[(pyxel.frame_count // 4) % len(SUPER_RAINBOW)]

        if self.dive_state == DiveState.AIRBORNE or self.dive_state == DiveState.SPLASH:
            self._draw_diver(self.diver_x, self.diver_y, self.diver_rotation, diver_color)

        self._draw_water()
        self._draw_zones()
        self._draw_splash_flash()
        self._draw_particles()
        self._draw_text_popups()
        self._draw_hud()

    def _draw_game_over(self) -> None:
        pyxel.rect(WIDTH // 2 - 52, 50, 104, 85, BLACK)
        pyxel.rectb(WIDTH // 2 - 52, 50, 104, 85, RED)
        pyxel.text(WIDTH // 2 - 20, 57, "GAME OVER", RED)
        score_text = f"SCORE: {self.score}"
        pyxel.text(WIDTH // 2 - len(score_text) * 2, 75, score_text, WHITE)
        combo_text = f"MAX COMBO: {self.max_combo}"
        pyxel.text(WIDTH // 2 - len(combo_text) * 2, 90, combo_text, YELLOW)
        dive_text = f"DEPTH: {self.dive_count}"
        pyxel.text(WIDTH // 2 - len(dive_text) * 2, 105, dive_text, WHITE)
        pyxel.text(WIDTH // 2 - 40, 125, "SPACE to retry", GRAY)


# ── Entry Point ─────────────────────────────────────────────────────────────
def main() -> None:
    Game()


if __name__ == "__main__":
    main()
