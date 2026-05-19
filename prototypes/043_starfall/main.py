"""STARFALL — Color-match Missile Command defense game.

Reinterpreted from game_idea_factory idea #1 (score 32.0):
  Theme: Calamity Sealing (runaway control)
  Hooks: synthesis compression (COMBO chains compress consecutive same-color
         hits into amplified score) + chain visualization (COMBO counter
         prominently displayed, accelerates with wave intensity)

Core mechanic: Click to launch color-coded interceptors from cities.
Same-color consecutive intercepts build COMBO → score multiplier surges.
Let stars get close for risky bonus points, or play safe and lose the chain.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if not TYPE_CHECKING:
    import pyxel

# ═══════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════

SCREEN_W = 256
SCREEN_H = 256
DISPLAY_SCALE = 3
FPS = 60

NUM_COLORS = 5
# Pyxel color constants: RED(8), DARK_BLUE(5), GREEN(3), YELLOW(9), PURPLE(2)
COLOR_VALS: tuple[int, int, int, int, int] = (8, 5, 3, 9, 2)

CITY_COUNT = 5
CITY_Y = 224
CITY_W = 28
CITY_H = 12
CITY_HP = 3
CITY_MARGIN = 20
CITY_SPACING = (SCREEN_W - 2 * CITY_MARGIN) // (CITY_COUNT - 1)

INTERCEPTOR_SPEED = 6.0
EXPLOSION_RADIUS = 26.0
EXPLOSION_DURATION = 14  # frames

STAR_SPEED_BASE = 0.7
STAR_RADIUS = 4.0
STAR_SPAWN_INTERVAL = 28  # frames between spawns
WAVE_PAUSE = 50  # frames between waves
STARS_PER_WAVE_BASE = 7
STARS_PER_WAVE_INC = 2
SPEED_INC_PER_WAVE = 0.12

MAX_HEAT = 100
HEAT_PER_MISS = 18
HEAT_PER_HIT = -6
HEAT_DECAY = 0.4  # per frame

COMBO_THRESHOLD_SURGE = 4
SURGE_DURATION = 180  # 3 seconds at 60fps
SURGE_RADIUS_BONUS = 12.0

INTERCEPTOR_COOLDOWN = 6  # frames

CLOSE_BONUS_THRESHOLD = 180  # y below this = risky close intercept, bonus pts

# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════


class Phase(Enum):
    PLAYING = auto()
    WAVE_CLEAR = auto()
    GAME_OVER = auto()


# ═══════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════


@dataclass
class City:
    x: int
    y: int
    color: int
    hp: int = CITY_HP
    cooldown: int = 0

    @property
    def alive(self) -> bool:
        return self.hp > 0


@dataclass
class Star:
    x: float
    y: float
    color: int
    speed: float


@dataclass
class Interceptor:
    x: float
    y: float
    target_x: float
    target_y: float
    city_color: int
    alive: bool = True


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


# ═══════════════════════════════════════════════════════════
# Game
# ═══════════════════════════════════════════════════════════


class Game:
    """STARFALL main game class — color-match defense against falling stars."""

    def __init__(self) -> None:
        pyxel.init(
            SCREEN_W, SCREEN_H, title="STARFALL", display_scale=DISPLAY_SCALE, fps=FPS
        )
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        # Cities along the bottom
        self.cities: list[City] = []
        for i in range(CITY_COUNT):
            x = CITY_MARGIN + i * CITY_SPACING
            self.cities.append(City(x=x, y=CITY_Y, color=i % NUM_COLORS))

        self.stars: list[Star] = []
        self.interceptors: list[Interceptor] = []
        self.particles: list[Particle] = []

        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.surge_timer: int = 0

        self.wave: int = 1
        self.stars_spawned: int = 0
        self.stars_to_spawn: int = STARS_PER_WAVE_BASE
        self.spawn_timer: int = 0
        self.wave_pause_timer: int = 0
        self.phase: Phase = Phase.PLAYING

        self._shake_frames: int = 0
        self._shake_x: int = 0
        self._shake_y: int = 0

        self._rng: random.Random = random.Random()

        # Spawn a star right away so the player has something to shoot
        self._spawn_star()
        self.stars_spawned += 1
        self.spawn_timer = STAR_SPAWN_INTERVAL

    # ═══ Update ═══

    def update(self) -> None:
        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
            return

        if self.phase == Phase.WAVE_CLEAR:
            self.wave_pause_timer -= 1
            if self.wave_pause_timer <= 0:
                self._start_next_wave()
            return

        # ── PLAYING phase ──
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._launch_interceptor(pyxel.mouse_x, pyxel.mouse_y)

        self._update_stars()
        self._update_interceptors()
        self._update_particles()
        self._update_cooldowns()
        self._update_heat()
        self._update_shake()
        self._update_surge()

        if all(not c.alive for c in self.cities):
            self.phase = Phase.GAME_OVER

    def _start_next_wave(self) -> None:
        self.phase = Phase.PLAYING
        self.wave += 1
        self.stars_to_spawn = STARS_PER_WAVE_BASE + (self.wave - 1) * STARS_PER_WAVE_INC
        self.stars_spawned = 0
        self.spawn_timer = max(8, STAR_SPAWN_INTERVAL - self.wave * 2)
        # Bonus: reset city cooldowns between waves
        for c in self.cities:
            c.cooldown = 0

    def _launch_interceptor(self, tx: int, ty: int) -> None:
        """Find the nearest alive city with no cooldown and launch."""
        best: City | None = None
        best_dist = float("inf")
        for c in self.cities:
            if c.alive and c.cooldown <= 0:
                d = (c.x - tx) ** 2 + (c.y - ty) ** 2
                if d < best_dist:
                    best_dist = d
                    best = c
        if best is None:
            return
        best.cooldown = INTERCEPTOR_COOLDOWN
        self.interceptors.append(
            Interceptor(
                x=float(best.x),
                y=float(best.y),
                target_x=float(tx),
                target_y=float(ty),
                city_color=best.color,
            )
        )

    def _update_cooldowns(self) -> None:
        for c in self.cities:
            if c.cooldown > 0:
                c.cooldown -= 1

    def _update_stars(self) -> None:
        # Spawn
        if self.stars_spawned < self.stars_to_spawn:
            self.spawn_timer -= 1
            if self.spawn_timer <= 0:
                self._spawn_star()
                self.stars_spawned += 1
                self.spawn_timer = max(6, STAR_SPAWN_INTERVAL - self.wave * 3)

        # Move
        star_speed = STAR_SPEED_BASE + (self.wave - 1) * SPEED_INC_PER_WAVE
        remaining: list[Star] = []
        for s in self.stars:
            s.y += star_speed * (0.8 + 0.4 * self._rng.random())

            # Hit ground?
            if s.y >= CITY_Y - STAR_RADIUS:
                self._star_hit_ground(s)
            else:
                remaining.append(s)
        self.stars = remaining

        # Wave complete?
        if (
            self.stars_spawned >= self.stars_to_spawn
            and len(self.stars) == 0
            and len(self.interceptors) == 0
        ):
            self.phase = Phase.WAVE_CLEAR
            self.wave_pause_timer = WAVE_PAUSE

    def _star_hit_ground(self, s: Star) -> None:
        """A star reached the ground — check if it hits a city."""
        hit = False
        for c in self.cities:
            if c.alive and abs(s.x - c.x) < CITY_W // 2 + STAR_RADIUS:
                c.hp -= 1
                hit = True
                self.heat = min(MAX_HEAT, self.heat + HEAT_PER_MISS)
                self._shake_frames = 12
                # Spawn red particles on city hit
                for _ in range(6):
                    self.particles.append(
                        Particle(
                            x=s.x,
                            y=CITY_Y - CITY_H // 2,
                            vx=self._rng.uniform(-1.5, 1.5),
                            vy=self._rng.uniform(-2, 0),
                            life=10,
                            color=pyxel.COLOR_RED,
                        )
                    )
                break
        if not hit:
            # Missed all cities — star hits bare ground, combo reset
            pass
        self.combo = 0  # Any ground hit resets combo

    def _spawn_star(self) -> None:
        x = self._rng.uniform(STAR_RADIUS * 3, SCREEN_W - STAR_RADIUS * 3)
        color = self._rng.randint(0, NUM_COLORS - 1)
        self.stars.append(Star(x=x, y=-STAR_RADIUS * 2, color=color, speed=STAR_SPEED_BASE))

    def _update_interceptors(self) -> None:
        new_invs: list[Interceptor] = []
        for inv in self.interceptors:
            if not inv.alive:
                continue
            dx = inv.target_x - inv.x
            dy = inv.target_y - inv.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < INTERCEPTOR_SPEED:
                self._explode(inv.target_x, inv.target_y, inv.city_color)
                inv.alive = False
            else:
                inv.x += dx / dist * INTERCEPTOR_SPEED
                inv.y += dy / dist * INTERCEPTOR_SPEED
                new_invs.append(inv)
        self.interceptors = new_invs

    def _explode(self, x: float, y: float, color: int) -> None:
        """Explosion at (x, y). Check stars in radius, apply combo logic."""
        # Spawn particles
        for _ in range(14):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 3.5)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=EXPLOSION_DURATION,
                    color=COLOR_VALS[color],
                )
            )

        # Surge bonus radius
        radius = EXPLOSION_RADIUS
        if self.surge_timer > 0:
            radius += SURGE_RADIUS_BONUS

        # Separate hit stars from missed stars
        hit_stars: list[Star] = []
        remaining: list[Star] = []
        for s in self.stars:
            d = math.sqrt((s.x - x) ** 2 + (s.y - y) ** 2)
            if d < radius:
                hit_stars.append(s)
            else:
                remaining.append(s)
        self.stars = remaining

        if not hit_stars:
            self.combo = 0
            return

        # Color match check
        matched = any(s.color == color for s in hit_stars)
        if matched:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            if self.combo >= COMBO_THRESHOLD_SURGE:
                self.surge_timer = SURGE_DURATION
        else:
            self.combo = 0

        # Score
        combo_mult = 1.0 + (self.combo - 1) * 0.5 if self.combo > 0 else 1.0
        combo_mult = min(combo_mult, 10.0)
        for s in hit_stars:
            pts = 100
            if s.y > CLOSE_BONUS_THRESHOLD:
                pts += 80  # risky close intercept bonus
            self.score += int(pts * combo_mult)

        self.heat = max(0, self.heat + HEAT_PER_HIT)

    def _update_particles(self) -> None:
        new_p: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vx *= 0.96
            p.vy *= 0.96
            p.life -= 1
            if p.life > 0:
                new_p.append(p)
        self.particles = new_p

    def _update_heat(self) -> None:
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_shake(self) -> None:
        if self._shake_frames > 0:
            self._shake_frames -= 1
            self._shake_x = self._rng.randint(-4, 4)
            self._shake_y = self._rng.randint(-4, 4)
        else:
            self._shake_x = 0
            self._shake_y = 0

    def _update_surge(self) -> None:
        if self.surge_timer > 0:
            self.surge_timer -= 1

    # ═══ Draw ═══

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        cx = self._shake_x
        cy = self._shake_y

        # Starfield background (static dots)
        for i in range(24):
            sx = (i * 43 + pyxel.frame_count * 0.2) % SCREEN_W
            sy = (i * 29) % SCREEN_H
            pyxel.pset(int(sx) + cx, int(sy) + cy, pyxel.COLOR_NAVY)

        # Stars (falling enemies)
        for s in self.stars:
            col = COLOR_VALS[s.color]
            # Trail
            trail_len = min(12, int(s.y + STAR_RADIUS))
            ty = max(0, int(s.y) - trail_len)
            pyxel.line(int(s.x) + cx, int(s.y) + cy, int(s.x) + cx, ty + cy, col)
            # Body
            pyxel.circ(int(s.x) + cx, int(s.y) + cy, STAR_RADIUS, col)
            # Highlight
            if self.surge_timer > 0 and s.color == self._active_surge_color():
                pyxel.circb(int(s.x) + cx, int(s.y) + cy, STAR_RADIUS + 2, pyxel.COLOR_WHITE)

        # Interceptors (flying up)
        for inv in self.interceptors:
            if inv.alive:
                col = COLOR_VALS[inv.city_color]
                pyxel.tri(
                    int(inv.x) + cx,
                    int(inv.y - 4) + cy,
                    int(inv.x - 3) + cx,
                    int(inv.y + 2) + cy,
                    int(inv.x + 3) + cx,
                    int(inv.y + 2) + cy,
                    col,
                )

        # Explosion flash circles (drawn for interceptors reaching target this frame)
        # We approximate by drawing a ring for surge-mode interceptors
        if self.surge_timer > 0:
            for inv in self.interceptors:
                if inv.alive:
                    flash_alpha = (pyxel.frame_count // 3) % 2
                    if flash_alpha:
                        pyxel.circb(
                            int(inv.target_x) + cx,
                            int(inv.target_y) + cy,
                            int(EXPLOSION_RADIUS + SURGE_RADIUS_BONUS),
                            pyxel.COLOR_PINK,
                        )

        # Particles
        for p in self.particles:
            alpha = p.life / EXPLOSION_DURATION
            col = p.color if alpha > 0.4 else pyxel.COLOR_WHITE
            pyxel.pset(int(p.x) + cx, int(p.y) + cy, col)

        # Ground line
        pyxel.rect(0, CITY_Y - 2 + cy, SCREEN_W, 4, pyxel.COLOR_GRAY)

        # Cities
        for c in self.cities:
            if not c.alive:
                # Rubble
                pyxel.rect(
                    c.x - CITY_W // 2 + cx,
                    c.y - CITY_H // 2 + cy,
                    CITY_W,
                    CITY_H // 2,
                    pyxel.COLOR_BROWN,
                )
                continue
            col = COLOR_VALS[c.color]
            # City body
            pyxel.rect(c.x - CITY_W // 2 + cx, c.y - CITY_H + cy, CITY_W, CITY_H, col)
            # Base
            pyxel.rect(
                c.x - CITY_W // 2 - 2 + cx, c.y + cy, CITY_W + 4, 4, pyxel.COLOR_GRAY
            )
            # HP bar
            hp_w = max(1, (CITY_W - 4) * c.hp // CITY_HP)
            pyxel.rect(
                c.x - CITY_W // 2 + 2 + cx,
                c.y - CITY_H + 2 + cy,
                hp_w,
                3,
                pyxel.COLOR_WHITE,
            )
            # Cooldown overlay
            if c.cooldown > 0:
                cd_frac = c.cooldown / INTERCEPTOR_COOLDOWN
                cd_h = max(1, int(CITY_H * cd_frac))
                pyxel.rect(
                    c.x - CITY_W // 2 + cx,
                    c.y - CITY_H + cy,
                    CITY_W,
                    cd_h,
                    pyxel.COLOR_BLACK,
                )

        # ═══ HUD ═══

        # Score
        pyxel.text(4, 4, f"SCORE:{self.score:06d}", pyxel.COLOR_WHITE)

        # Combo
        if self.combo > 1:
            combo_col = pyxel.COLOR_YELLOW
            if self.combo >= 3:
                combo_col = pyxel.COLOR_ORANGE
            if self.combo >= 5:
                combo_col = pyxel.COLOR_RED
            if self.surge_timer > 0:
                blink = (pyxel.frame_count // 4) % 2 == 0
                combo_col = pyxel.COLOR_PINK if blink else pyxel.COLOR_WHITE
            mult_text = f"x{1 + (self.combo - 1) * 0.5:.1f}"
            pyxel.text(4, 14, f"COMBO:{mult_text}", combo_col)

        # Wave
        pyxel.text(SCREEN_W - 55, 4, f"WAVE:{self.wave:02d}", pyxel.COLOR_CYAN)

        # Max combo
        pyxel.text(SCREEN_W - 70, SCREEN_H - 10, f"MAX:{self.max_combo}", pyxel.COLOR_LIGHT_BLUE)

        # Heat bar
        heat_col = pyxel.COLOR_GREEN
        if self.heat > 50:
            heat_col = pyxel.COLOR_YELLOW
        if self.heat > 75:
            heat_col = pyxel.COLOR_RED
        bar_w = int(56 * self.heat / MAX_HEAT)
        pyxel.rect(4, SCREEN_H - 8, 56, 4, pyxel.COLOR_GRAY)
        if bar_w > 0:
            pyxel.rect(4, SCREEN_H - 8, bar_w, 4, heat_col)

        # Surge banner
        if self.surge_timer > 0:
            sec = self.surge_timer // FPS + 1
            pyxel.text(
                SCREEN_W // 2 - 26,
                SCREEN_H // 2 - 30,
                f"SURGE! {sec}s",
                pyxel.COLOR_PINK,
            )

        # Wave clear message
        if self.phase == Phase.WAVE_CLEAR:
            pyxel.text(
                SCREEN_W // 2 - 30, SCREEN_H // 2, "WAVE CLEAR!", pyxel.COLOR_LIME
            )

        # Game over
        if self.phase == Phase.GAME_OVER:
            pyxel.text(SCREEN_W // 2 - 25, SCREEN_H // 2 - 12, "GAME OVER", pyxel.COLOR_RED)
            pyxel.text(
                SCREEN_W // 2 - 42,
                SCREEN_H // 2 + 8,
                "CLICK TO RETRY",
                pyxel.COLOR_WHITE,
            )
            pyxel.text(
                SCREEN_W // 2 - 46,
                SCREEN_H // 2 + 20,
                f"FINAL SCORE: {self.score}",
                pyxel.COLOR_YELLOW,
            )

        # Crosshair (only when playing, not wave clear)
        if self.phase == Phase.PLAYING:
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            pyxel.pset(mx, my - 4, pyxel.COLOR_WHITE)
            pyxel.pset(mx, my + 4, pyxel.COLOR_WHITE)
            pyxel.pset(mx - 4, my, pyxel.COLOR_WHITE)
            pyxel.pset(mx + 4, my, pyxel.COLOR_WHITE)

    def _active_surge_color(self) -> int:
        """Return a color index for surge-mode highlight (cycles)."""
        return (pyxel.frame_count // 10) % NUM_COLORS
