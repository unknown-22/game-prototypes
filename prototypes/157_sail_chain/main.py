"""SAIL CHAIN — Top-down sailing race prototype.

Core fun moment:
同じ色のブイを連続で回航してCOMBOチェインを繋ぎ、
SUPER SAILで爆速加速しながら一気に大量得点を稼ぐ瞬間。
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ============================================================
# Constants
# ============================================================
SCREEN_W = 320
SCREEN_H = 240
FPS = 60

# Colors (Pyxel 16-color palette)
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

BUOY_COLORS: tuple[int, ...] = (RED, GREEN, YELLOW, LIGHT_BLUE)
WATER_COLOR = DARK_BLUE
BOAT_COLOR_DEFAULT = WHITE
HEAT_COLOR = RED
HUD_COLOR = WHITE
GHOST_COLOR = GRAY

# Gameplay
BOAT_BASE_SPEED: float = 1.5
WIND_POWER: float = 0.5
RUDDER_SPEED: float = 0.04  # radians per frame
SAIL_SPEED: float = 0.03  # radians per frame
SAIL_MAX: float = math.pi / 2
SAIL_MIN: float = 0.0
WIND_CHANGE_MIN: int = 300  # frames (5s)
WIND_CHANGE_MAX: int = 480  # frames (8s)
WIND_ANGLES: tuple[float, ...] = (0.0, math.pi / 2, math.pi, 3 * math.pi / 2)

BOAT_LENGTH: float = 16.0
BOAT_WIDTH: float = 10.0
BUOY_RADIUS: float = 8.0
COLLISION_RADIUS: float = 14.0  # boat-buoy collision

COMBO_THRESHOLD: int = 4
SUPER_DURATION: int = 300  # frames (5s)
MAX_HEAT: int = 5
GAME_TIMER_FRAMES: int = 3600  # frames (60s)

NUM_BUOYS: int = 8
BUOYS_PER_COLOR: int = 2

PARTICLE_GRAVITY: float = 0.05

# ============================================================
# Enums
# ============================================================
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ============================================================
# Data Classes
# ============================================================
@dataclass
class Buoy:
    x: float
    y: float
    color: int
    rounded: bool = False
    radius: float = BUOY_RADIUS


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: float = 2.0


@dataclass
class GhostPoint:
    x: float
    y: float
    angle: float


# ============================================================
# Game
# ============================================================
class Game:
    """Top-down sailing race. Round same-color buoys to build combos."""

    # Pre-initialized state (required for Game.__new__ bypass in tests)
    phase: Phase = Phase.TITLE
    score: int = 0
    high_score: int = 0
    combo: int = 0
    max_combo: int = 0
    heat: int = 0
    boat_x: float = float(SCREEN_W // 2)
    boat_y: float = float(SCREEN_H // 2)
    boat_angle: float = 0.0  # radians, 0=right, pi/2=down
    sail_angle: float = math.pi / 4  # relative to boat heading
    rudder_input: float = 0.0  # -1..1
    sail_input: float = 0.0  # -1..1
    boat_speed: float = BOAT_BASE_SPEED
    wind_angle: float = 0.0
    wind_timer: int = WIND_CHANGE_MIN
    buoys: list[Buoy] = []
    particles: list[Particle] = []
    ghost_trail: list[GhostPoint] = []
    ghost_recording: list[GhostPoint] = []
    best_ghost: list[GhostPoint] = []
    super_timer: int = 0
    game_timer: int = GAME_TIMER_FRAMES
    last_buoy_color: int = -1
    shake_frames: int = 0
    nearest_buoy_idx: int = -1
    camera_y: float = 0.0
    _wave_offset: float = 0.0
    _flash_timer: int = 0

    def __init__(self) -> None:
        self.rng = random.Random()
        pyxel.init(SCREEN_W, SCREEN_H, title="SAIL CHAIN", fps=FPS, display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    # ============================================================
    # Main Loop
    # ============================================================
    def update(self) -> None:
        if self.shake_frames > 0:
            self.shake_frames -= 1
            try:
                pyxel.camera(random.randint(-2, 2), random.randint(-2, 2))
            except BaseException:
                pass
        else:
            try:
                pyxel.camera(0, 0)
            except BaseException:
                pass

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def draw(self) -> None:
        pyxel.cls(WATER_COLOR)
        self._draw_water_waves()

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    # ============================================================
    # Phase Updates
    # ============================================================
    def _update_title(self) -> None:
        self._wave_offset = (self._wave_offset + 0.3) % 40.0
        self._flash_timer += 1
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self._read_input()
        self._update_physics()
        self._update_wind()
        self._update_buoys()
        self._update_super()
        self._update_particles()
        self._update_timer()
        self._update_ghost()
        self._add_wake_particles()
        self._update_nearest_buoy()
        self._flash_timer += 1
        if self._check_game_over():
            self._on_game_over()

    def _update_game_over(self) -> None:
        self._flash_timer += 1
        self._update_particles()
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.TITLE

    # ============================================================
    # Input Reading (pyxel-dependent — NOT in testable methods)
    # ============================================================
    def _read_input(self) -> None:
        self.rudder_input = 0.0
        self.sail_input = 0.0
        if pyxel.btn(pyxel.KEY_LEFT):
            self.rudder_input = -1.0
        if pyxel.btn(pyxel.KEY_RIGHT):
            self.rudder_input = 1.0
        if pyxel.btn(pyxel.KEY_UP):
            self.sail_input = 1.0
        if pyxel.btn(pyxel.KEY_DOWN):
            self.sail_input = -1.0

    # ============================================================
    # Testable Game Logic
    # ============================================================
    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0
        self.boat_x = float(SCREEN_W // 2)
        self.boat_y = float(SCREEN_H - 40)
        self.boat_angle = 0.0
        self.sail_angle = math.pi / 4
        self.rudder_input = 0.0
        self.sail_input = 0.0
        self.boat_speed = BOAT_BASE_SPEED
        self.wind_angle = 0.0
        self.wind_timer = self.rng.randint(WIND_CHANGE_MIN, WIND_CHANGE_MAX)
        self.super_timer = 0
        self.game_timer = GAME_TIMER_FRAMES
        self.last_buoy_color = -1
        self.shake_frames = 0
        self.nearest_buoy_idx = -1
        self.camera_y = 0.0
        self._wave_offset = 0.0
        self._flash_timer = 0
        self.buoys = []
        self.particles = []
        self.ghost_trail = []
        self.ghost_recording = []
        self._spawn_buoys()

    def _spawn_buoys(self) -> None:
        """Generate buoy layout — 8 buoys, 2 of each color."""
        colors = list(BUOY_COLORS) * BUOYS_PER_COLOR
        self.rng.shuffle(colors)
        margin = int(BUOY_RADIUS + 8)
        self.buoys.clear()
        for color in colors:
            x = self.rng.uniform(margin, SCREEN_W - margin)
            y = self.rng.uniform(40, SCREEN_H - 40)
            self.buoys.append(Buoy(x=x, y=y, color=color, rounded=False))

    def _respawn_buoy(self, buoy: Buoy) -> None:
        """Move a rounded buoy to a new random position."""
        margin = int(BUOY_RADIUS + 8)
        buoy.x = self.rng.uniform(margin, SCREEN_W - margin)
        buoy.y = self.rng.uniform(40, SCREEN_H - 40)
        buoy.rounded = False

    def _update_physics(self) -> None:
        """Move boat based on speed, angle, rudder, and wind."""
        # Rudder turns the boat
        self.boat_angle += self.rudder_input * RUDDER_SPEED
        # Normalize angle to [0, 2pi)
        self.boat_angle %= 2 * math.pi

        # Sail angle adjustment
        self.sail_angle += self.sail_input * SAIL_SPEED
        self.sail_angle = max(SAIL_MIN, min(SAIL_MAX, self.sail_angle))

        # Compute wind effect
        if self._is_super():
            wind_effect = 1.0  # Wind immunity in super mode
        else:
            sail_abs = self.boat_angle + self.sail_angle
            wind_effect = math.cos(sail_abs - self.wind_angle)

        self.boat_speed = BOAT_BASE_SPEED + wind_effect * WIND_POWER
        self.boat_speed = max(0.3, self.boat_speed)

        # Super speed boost
        if self._is_super():
            self.boat_speed = BOAT_BASE_SPEED * 3.0 + WIND_POWER

        # Move boat
        self.boat_x += math.cos(self.boat_angle) * self.boat_speed
        self.boat_y += math.sin(self.boat_angle) * self.boat_speed

        # Vertical wrapping
        if self.boat_y < -BOAT_LENGTH:
            self.boat_y += SCREEN_H + BOAT_LENGTH * 2
        elif self.boat_y > SCREEN_H + BOAT_LENGTH:
            self.boat_y -= SCREEN_H + BOAT_LENGTH * 2

        # Horizontal wrapping
        if self.boat_x < -BOAT_LENGTH:
            self.boat_x += SCREEN_W + BOAT_LENGTH * 2
        elif self.boat_x > SCREEN_W + BOAT_LENGTH:
            self.boat_x -= SCREEN_W + BOAT_LENGTH * 2

    def _update_wind(self) -> None:
        """Manage wind direction changes."""
        if self._is_super():
            return  # Wind immunity
        self.wind_timer -= 1
        if self.wind_timer <= 0:
            self.wind_angle = self.rng.choice(WIND_ANGLES)
            self.wind_timer = self.rng.randint(WIND_CHANGE_MIN, WIND_CHANGE_MAX)

    def _update_buoys(self) -> None:
        """Check boat-buoy collisions, handle scoring/combo/heat."""
        is_super = self._is_super()
        for b in self.buoys:
            if b.rounded:
                continue
            dx = self.boat_x - b.x
            dy = self.boat_y - b.y
            dist = math.hypot(dx, dy)
            if dist < COLLISION_RADIUS:
                self._round_buoy(b, is_super)

    def _round_buoy(self, buoy: Buoy, is_super: bool) -> None:
        """Handle single buoy rounding logic."""
        if is_super:
            # Super mode: auto-collect all, same-color bonus implicitly
            buoy.rounded = True
            pts = self._compute_score(buoy, True)
            self.score += pts
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            self._spawn_collect_particles(buoy.x, buoy.y, buoy.color, 8)
            self.last_buoy_color = buoy.color
            self._respawn_buoy(buoy)
            return

        # Normal mode
        if self.combo == 0 or buoy.color == self.last_buoy_color:
            # Same color or first buoy: combo up
            buoy.rounded = True
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            pts = self._compute_score(buoy, False)
            self.score += pts
            self.last_buoy_color = buoy.color
            self._spawn_collect_particles(buoy.x, buoy.y, buoy.color, 5)
            self._respawn_buoy(buoy)

            # Check super activation
            if self.combo >= COMBO_THRESHOLD and not self._is_super():
                self._activate_super()
        else:
            # Wrong color: combo reset, heat up
            buoy.rounded = True
            self.combo = 0
            self.heat += 1
            self.last_buoy_color = buoy.color
            self._spawn_wrong_particles(buoy.x, buoy.y, buoy.color)
            self._respawn_buoy(buoy)

    def _compute_score(self, buoy: Buoy, is_super: bool) -> int:
        """Calculate points for a buoy rounding."""
        base = 10
        multiplier = 3 if is_super else 1
        combo_bonus = self.combo + 1
        return base * combo_bonus * multiplier

    def _activate_super(self) -> None:
        """Enter SUPER SAIL mode."""
        self.super_timer = SUPER_DURATION
        self.shake_frames = 5
        # Burst particles
        for _ in range(30):
            angle = self.rng.uniform(0, math.pi * 2)
            speed = self.rng.uniform(2, 5)
            self.particles.append(
                Particle(
                    x=self.boat_x,
                    y=self.boat_y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=self.rng.randint(20, 40),
                    color=self.rng.choice(BUOY_COLORS),
                    size=self.rng.uniform(1, 3),
                )
            )

    def _deactivate_super(self) -> None:
        """Exit SUPER SAIL mode."""
        self.super_timer = 0

    def _update_super(self) -> None:
        """Tick super timer down."""
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self._deactivate_super()

    def _is_super(self) -> bool:
        return self.super_timer > 0

    def _update_particles(self) -> None:
        """Age and move particles, remove dead ones."""
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += PARTICLE_GRAVITY
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _add_wake_particles(self) -> None:
        """Spawn wake trail particles behind the boat."""
        is_super = self._is_super()
        count = self.rng.randint(8, 12) if is_super else self.rng.randint(3, 5)
        wake_color = (
            self.rng.choice(BUOY_COLORS) if is_super
            else self.last_buoy_color if self.last_buoy_color >= 0
            else WHITE
        )
        for _ in range(count):
            offset_x = -math.cos(self.boat_angle) * (BOAT_LENGTH // 2)
            offset_y = -math.sin(self.boat_angle) * (BOAT_LENGTH // 2)
            px = self.boat_x + offset_x
            py = self.boat_y + offset_y
            perp_angle = self.boat_angle + math.pi / 2
            spread = self.rng.uniform(-0.5, 0.5)
            self.particles.append(
                Particle(
                    x=px,
                    y=py,
                    vx=math.cos(perp_angle) * spread,
                    vy=math.sin(perp_angle) * spread,
                    life=self.rng.randint(15, 30),
                    color=wake_color,
                    size=self.rng.uniform(1, 2.5),
                )
            )

    def _spawn_collect_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.pi * 2)
            speed = self.rng.uniform(1, 3)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed - 1.0,
                    life=self.rng.randint(10, 20),
                    color=color,
                    size=self.rng.uniform(1, 2),
                )
            )

    def _spawn_wrong_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(self.rng.randint(4, 6)):
            vx = self.rng.uniform(-1.5, 1.5)
            vy = self.rng.uniform(-1.5, 1.5)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=vx,
                    vy=vy,
                    life=self.rng.randint(8, 15),
                    color=color,
                    size=1.0,
                )
            )

    def _update_timer(self) -> None:
        """Countdown game timer."""
        if self.game_timer > 0:
            self.game_timer -= 1

    def _check_game_over(self) -> bool:
        """Return True if heat or timer says game over."""
        return self.heat >= MAX_HEAT or self.game_timer <= 0

    def _update_ghost(self) -> None:
        """Record current boat position for ghost trail."""
        self.ghost_recording.append(
            GhostPoint(x=self.boat_x, y=self.boat_y, angle=self.boat_angle)
        )

    def _update_nearest_buoy(self) -> None:
        """Find nearest unrounded buoy for HUD indicator."""
        best_idx = -1
        best_dist = float("inf")
        for i, b in enumerate(self.buoys):
            if b.rounded:
                continue
            dx = self.boat_x - b.x
            dy = self.boat_y - b.y
            dist = math.hypot(dx, dy)
            if dist < best_dist:
                best_dist = dist
                best_idx = i
        self.nearest_buoy_idx = best_idx

    def _on_game_over(self) -> None:
        """Handle transition to game over."""
        self.phase = Phase.GAME_OVER
        self.shake_frames = 5
        if self.score > self.high_score:
            self.high_score = self.score
            self.best_ghost = list(self.ghost_recording)
        # Spawn death particles
        for _ in range(20):
            angle = self.rng.uniform(0, math.pi * 2)
            speed = self.rng.uniform(1, 4)
            self.particles.append(
                Particle(
                    x=self.boat_x,
                    y=self.boat_y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=self.rng.randint(15, 30),
                    color=RED,
                    size=self.rng.uniform(1, 3),
                )
            )

    # ============================================================
    # Drawing
    # ============================================================
    def _draw_water_waves(self) -> None:
        """Draw subtle wave lines on water background."""
        offset = int(self._wave_offset) if self.phase == Phase.TITLE else 0
        for i in range(10):
            wave_y = 30 + i * 20
            wave_y = (wave_y + offset) % SCREEN_H
            for x in range(0, SCREEN_W, 16):
                wx = (x + offset + (i % 2) * 8) % SCREEN_W
                if self.rng.random() < 0.3:  # only for title screen, avoid rng in draw
                    pass
                pyxel.pset(wx, wave_y, LIGHT_BLUE)

    def _draw_boat(self, x: int, y: int, angle: float, color: int) -> None:
        """Draw a triangle boat at position facing given angle."""
        tip_x = x + int(math.cos(angle) * BOAT_LENGTH // 2)
        tip_y = y + int(math.sin(angle) * BOAT_LENGTH // 2)
        left_angle = angle + math.pi * 0.75
        right_angle = angle - math.pi * 0.75
        left_x = x + int(math.cos(left_angle) * BOAT_WIDTH // 2)
        left_y = y + int(math.sin(left_angle) * BOAT_WIDTH // 2)
        right_x = x + int(math.cos(right_angle) * BOAT_WIDTH // 2)
        right_y = y + int(math.sin(right_angle) * BOAT_WIDTH // 2)
        pyxel.tri(left_x, left_y, right_x, right_y, tip_x, tip_y, color)

    def _draw_title(self) -> None:
        """Draw title screen."""
        title = "SAIL CHAIN"
        tx = SCREEN_W // 2 - len(title) * 2
        pyxel.text(tx, 60, title, WHITE)

        # Decorative buoys
        buoy_y_positions = [100, 125]
        for i, c in enumerate(BUOY_COLORS):
            bx = SCREEN_W // 2 - 30 + i * 20
            by = buoy_y_positions[i % 2]
            pyxel.circ(bx, by, BUOY_RADIUS, c)
            pyxel.circb(bx, by, int(BUOY_RADIUS), WHITE)

        subtitle = "Round same-color buoys for COMBO!"
        sx = SCREEN_W // 2 - len(subtitle) * 2
        pyxel.text(sx, 145, subtitle, YELLOW)

        inst1 = "LEFT/RIGHT: Steer (Rudder)"
        ix1 = SCREEN_W // 2 - len(inst1) * 2
        pyxel.text(ix1, 162, inst1, LIGHT_BLUE)

        inst2 = "UP/DOWN: Adjust Sail Angle"
        ix2 = SCREEN_W // 2 - len(inst2) * 2
        pyxel.text(ix2, 174, inst2, LIGHT_BLUE)

        start = "Press ENTER or SPACE to Start"
        sx2 = SCREEN_W // 2 - len(start) * 2
        blink = self._flash_timer % 60 < 40
        if blink:
            pyxel.text(sx2, 205, start, WHITE)

        if self.high_score > 0:
            hs = f"HIGH SCORE: {self.high_score}"
            hsx = SCREEN_W // 2 - len(hs) * 2
            pyxel.text(hsx, 220, hs, ORANGE)

    def _draw_playing(self) -> None:
        """Draw game screen."""
        is_super = self._is_super()
        rainbow_idx = pyxel.frame_count % len(BUOY_COLORS)

        # Ghost trail (best previous run)
        if self.best_ghost:
            ghost_frame = pyxel.frame_count % len(self.best_ghost)
            gp = self.best_ghost[ghost_frame]
            if ghost_frame % 2 == 0:  # 50% opacity via frame skipping
                self._draw_boat(int(gp.x), int(gp.y), gp.angle, GRAY)

        # Particles (wake and effects)
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

        # Buoys
        for i, b in enumerate(self.buoys):
            if b.rounded:
                continue
            # Flash nearest target buoy
            if i == self.nearest_buoy_idx:
                flash = self._flash_timer % 30 < 15
                if flash:
                    pyxel.circ(int(b.x), int(b.y), int(BUOY_RADIUS + 2), b.color)
                else:
                    pyxel.circ(int(b.x), int(b.y), int(BUOY_RADIUS), b.color)
            else:
                pyxel.circ(int(b.x), int(b.y), int(BUOY_RADIUS), b.color)
            pyxel.circb(int(b.x), int(b.y), int(BUOY_RADIUS), WHITE)

            # Color indicator dot in center
            is_target = (self.combo > 0 and b.color == self.last_buoy_color) or self.combo == 0
            if is_target and not is_super:
                pyxel.circb(int(b.x), int(b.y), int(BUOY_RADIUS) + 3, b.color)

        # Boat
        if is_super:
            boat_color = BUOY_COLORS[rainbow_idx]
        elif self.combo > 0 and self.last_buoy_color >= 0:
            boat_color = self.last_buoy_color
        else:
            boat_color = WHITE
        self._draw_boat(int(self.boat_x), int(self.boat_y), self.boat_angle, boat_color)

        # Sail indicator line
        sail_len = 10.0
        sail_abs = self.boat_angle + self.sail_angle
        sail_tip_x = int(self.boat_x + math.cos(sail_abs) * sail_len)
        sail_tip_y = int(self.boat_y + math.sin(sail_abs) * sail_len)
        pyxel.line(int(self.boat_x), int(self.boat_y), sail_tip_x, sail_tip_y, WHITE)

        # Wind direction arrow (top-right)
        arrow_x = SCREEN_W - 24
        arrow_y = 16
        aw_tip_x = arrow_x + int(math.cos(self.wind_angle) * 10)
        aw_tip_y = arrow_y + int(math.sin(self.wind_angle) * 10)
        pyxel.line(arrow_x, arrow_y, aw_tip_x, aw_tip_y, WHITE)
        pyxel.text(SCREEN_W - 46, 2, "WIND", LIGHT_BLUE)

        # HUD
        # Score top-left
        shadow_text(4, 4, f"SCORE: {self.score}", WHITE)

        # COMBO top-center
        combo_label = f"COMBO x{self.combo}"
        cw = len(combo_label) * 4
        if self.combo > 0:
            combo_color = self.last_buoy_color if self.last_buoy_color >= 0 else WHITE
        else:
            combo_color = WHITE
        shadow_text(SCREEN_W // 2 - cw // 2, 4, combo_label, combo_color)

        # SUPER indicator
        if is_super:
            super_text = "SUPER SAIL!"
            sx = SCREEN_W // 2 - len(super_text) * 2
            pyxel.text(sx, 16, super_text, BUOY_COLORS[rainbow_idx])

        # HEAT bar top-right
        heat_bar_x = SCREEN_W - 64
        heat_bar_y = 4
        heat_bar_w = 56
        heat_bar_h = 6
        pyxel.rect(heat_bar_x - 1, heat_bar_y - 1, heat_bar_w + 2, heat_bar_h + 2, BLACK)
        for seg in range(MAX_HEAT):
            seg_x = heat_bar_x + seg * (heat_bar_w // MAX_HEAT)
            seg_w = (heat_bar_w // MAX_HEAT) - 2
            fill_color = RED if seg < self.heat else GRAY
            pyxel.rect(seg_x, heat_bar_y, seg_w, heat_bar_h, fill_color)
        pyxel.text(heat_bar_x - 22, heat_bar_y, "HEAT", RED)

        # Timer bottom-center
        secs = max(0, self.game_timer // FPS)
        timer_text = f"TIME: {secs}s"
        tw = len(timer_text) * 4
        timer_color = RED if secs <= 10 else WHITE
        shadow_text(SCREEN_W // 2 - tw // 2, SCREEN_H - 12, timer_text, timer_color)

        # SUPER mode border flash
        if is_super:
            border_color = BUOY_COLORS[rainbow_idx]
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, border_color)

    def _draw_game_over(self) -> None:
        """Draw game over screen."""
        # Particles still visible
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

        go_text = "GAME OVER"
        gox = SCREEN_W // 2 - len(go_text) * 2
        pyxel.text(gox, 60, go_text, RED)

        score_text = f"FINAL SCORE: {self.score}"
        sx = SCREEN_W // 2 - len(score_text) * 2
        pyxel.text(sx, 85, score_text, WHITE)

        combo_text = f"MAX COMBO: {self.max_combo}"
        cx = SCREEN_W // 2 - len(combo_text) * 2
        pyxel.text(cx, 100, combo_text, ORANGE)

        if self.score >= self.high_score > 0:
            nhs = "NEW HIGH SCORE!"
            nhsx = SCREEN_W // 2 - len(nhs) * 2
            pyxel.text(nhsx, 120, nhs, YELLOW)
        elif self.high_score > 0:
            hs = f"HIGH SCORE: {self.high_score}"
            hsx = SCREEN_W // 2 - len(hs) * 2
            pyxel.text(hsx, 120, hs, GRAY)

        # Reason
        if self.game_timer <= 0:
            reason = "Time's up!"
        else:
            reason = "Overheated!"
        rx = SCREEN_W // 2 - len(reason) * 2
        pyxel.text(rx, 140, reason, RED)

        restart = "Press ENTER or SPACE to Retry"
        rsx = SCREEN_W // 2 - len(restart) * 2
        blink = self._flash_timer % 60 < 40
        if blink:
            pyxel.text(rsx, 170, restart, WHITE)

    # ============================================================
    # Factory for headless tests
    # ============================================================
    @classmethod
    def _make_game(cls, seed: int = 42) -> Game:
        """Create a Game instance without pyxel.init for headless testing."""
        game = cls.__new__(cls)
        game.rng = random.Random(seed)
        game.reset()
        game.phase = Phase.PLAYING
        return game


# ============================================================
# Helpers
# ============================================================
def shadow_text(x: int, y: int, text: str, color: int) -> None:
    """Draw text with a black shadow."""
    pyxel.text(x + 1, y + 1, text, BLACK)
    pyxel.text(x, y, text, color)


# ============================================================
# Entry Point
# ============================================================
def main() -> None:
    Game()


if __name__ == "__main__":
    main()
