"""BULLSEYE CHAIN — Color-match dart throwing with gravity arcs and chain combos.

Reinterpreted from game_idea_factory #1 (Score 31.8):
  "log/replay as asset" → ghost trails of previous throws visible on board
  "gravity/collapse chain" → gravity-arc dart physics + COMBO chain burst

Core mechanic: Throw colored darts at targets. Same-color consecutive hits
build COMBO for score multipliers. Wrong-color hits reset combo.
COMBO >= 4 triggers SUPER DART (rainbow, auto-seeks nearest target, 3x score).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto

import pyxel

# ── Config ────────────────────────────────────────────────────────────────
SCREEN_W = 256
SCREEN_H = 256
DISPLAY_SCALE = 2
FPS = 30

GRAVITY = 0.35
MAX_POWER = 10.0
MIN_POWER = 3.0

DART_X = SCREEN_W // 2
DART_Y = SCREEN_H - 26

NUM_COLORS = 4
# pyxel color constants: RED=8, GREEN=11, YELLOW=10, LIGHT_BLUE=12
COLOR_VALS: tuple[int, int, int, int] = (8, 11, 10, 12)
COLOR_NAMES: tuple[str, str, str, str] = ("RED", "GREEN", "YELLOW", "BLUE")

# Target tiers: (radius, points, label)
TIERS: tuple[tuple[float, int, str], ...] = (
    (5.0, 50, "BULL"),
    (9.0, 25, "INNER"),
    (13.0, 10, "OUTER"),
)

MIN_TARGETS = 8
MAX_TARGETS = 12
TARGET_ZONE_TOP = 10
TARGET_ZONE_BOTTOM = 140
TARGET_ZONE_LEFT = 20
TARGET_ZONE_RIGHT = SCREEN_W - 20

COMBO_THRESHOLD = 4
SUPER_MULTIPLIER = 3
GHOST_TRAIL_COUNT = 3
ROUND_TIME = 60 * FPS  # 60 seconds
MAX_DARTS = 30

PARTICLE_COUNT = 8
PARTICLE_LIFE = 15

# ── Enums ──────────────────────────────────────────────────────────────────


class Phase(Enum):
    AIMING = auto()
    FLYING = auto()
    RESULT = auto()
    GAME_OVER = auto()


# ── Data Classes ───────────────────────────────────────────────────────────


@dataclass
class Target:
    x: float
    y: float
    radius: float
    color_idx: int
    points: int
    label: str
    alive: bool = True


@dataclass
class Dart:
    x: float
    y: float
    vx: float
    vy: float
    color_idx: int
    active: bool = True
    trail: list[tuple[float, float]] = field(default_factory=list)
    super_mode: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int


@dataclass
class GhostTrail:
    points: list[tuple[float, float]]
    color_idx: int
    life: int


# ── Game ───────────────────────────────────────────────────────────────────


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="BULLSEYE CHAIN", fps=FPS, display_scale=DISPLAY_SCALE)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.AIMING
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.dart_color_idx: int = 0
        self.darts_remaining: int = MAX_DARTS
        self.timer: int = ROUND_TIME
        self.super_active: bool = False
        self.super_timer: int = 0
        self.result_timer: int = 0

        # Aim state
        self._drag_start: tuple[float, float] | None = None
        self._drag_current: tuple[float, float] | None = None

        # Entities
        self.targets: list[Target] = []
        self.dart: Dart | None = None
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.ghost_trails: list[GhostTrail] = []

        self._spawn_initial_targets()

    # ── Spawning ───────────────────────────────────────────────────────

    def _spawn_initial_targets(self) -> None:
        for _ in range(MIN_TARGETS):
            self._spawn_target()

    def _spawn_target(self) -> Target | None:
        """Spawn one target at a random valid position. Returns None if no space."""
        for _ in range(50):
            tier = self._rng.choice(TIERS)
            radius, points, label = tier
            x = self._rng.uniform(TARGET_ZONE_LEFT + radius, TARGET_ZONE_RIGHT - radius)
            y = self._rng.uniform(TARGET_ZONE_TOP + radius, TARGET_ZONE_BOTTOM - radius)
            color_idx = self._rng.randrange(NUM_COLORS)

            # Check no overlap with existing targets
            if any(self._circle_overlap(x, y, radius + 4, t.x, t.y, t.radius) for t in self.targets):
                continue

            t = Target(x=x, y=y, radius=radius, color_idx=color_idx, points=points, label=label)
            self.targets.append(t)
            return t
        return None

    @staticmethod
    def _circle_overlap(x1: float, y1: float, r1: float, x2: float, y2: float, r2: float) -> bool:
        dx = x1 - x2
        dy = y1 - y2
        dist = math.sqrt(dx * dx + dy * dy)
        return dist < r1 + r2

    def _replenish_targets(self) -> None:
        while len(self.targets) < MIN_TARGETS:
            self._spawn_target()

    # ── Input ───────────────────────────────────────────────────────────

    def _handle_aiming(self) -> None:
        # Cycle dart color with SPACE
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.dart_color_idx = (self.dart_color_idx + 1) % NUM_COLORS

        # Mouse drag to aim
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._drag_start = (pyxel.mouse_x, pyxel.mouse_y)
            self._drag_current = self._drag_start

        if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT) and self._drag_start is not None:
            self._drag_current = (pyxel.mouse_x, pyxel.mouse_y)

        if pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT) and self._drag_start is not None and self._drag_current is not None:
            sx, sy = self._drag_start
            cx, cy = self._drag_current
            dx = sx - cx
            dy = sy - cy
            power = math.sqrt(dx * dx + dy * dy)
            if power < 2.0:
                self._drag_start = None
                self._drag_current = None
                return

            power = min(power, MAX_POWER * 10) / 10.0
            power = max(power, MIN_POWER)
            # Normalize and scale
            if power > 0:
                dx = dx / (power * 10) * power
                dy = dy / (power * 10) * power

            vx = dx * 0.8
            vy = dy * 0.8

            self.dart = Dart(
                x=DART_X, y=DART_Y, vx=vx, vy=vy,
                color_idx=self.dart_color_idx,
                super_mode=self.super_active,
            )
            self.darts_remaining -= 1
            self.phase = Phase.FLYING
            self._drag_start = None
            self._drag_current = None

    def _handle_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()

    # ── Update ──────────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.AIMING:
            self._handle_aiming()
        elif self.phase == Phase.FLYING:
            self._update_flying()
        elif self.phase == Phase.RESULT:
            self._update_result()
        elif self.phase == Phase.GAME_OVER:
            self._handle_game_over()

        # Timer countdown (during aiming/flying/result)
        if self.phase != Phase.GAME_OVER:
            self.timer -= 1
            if self.timer <= 0:
                self.timer = 0
                self.phase = Phase.GAME_OVER

        # Super mode timer
        if self.super_active:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_active = False

        # Update particles
        self._update_particles()

        # Update floating texts
        self._update_floating_texts()

        # Update ghost trails
        self._update_ghost_trails()

    def _update_flying(self) -> None:
        if self.dart is None or not self.dart.active:
            return

        d = self.dart
        d.trail.append((d.x, d.y))

        # Apply gravity
        d.vy += GRAVITY

        # Move
        d.x += d.vx
        d.y += d.vy

        # Check off-screen
        if d.y > SCREEN_H + 20 or d.x < -20 or d.x > SCREEN_W + 20:
            self._dart_missed()
            return

        # Check target collision
        hit_target = self._check_dart_collision(d)
        if hit_target is not None:
            self._dart_hit_target(d, hit_target)

    def _check_dart_collision(self, d: Dart) -> Target | None:
        for t in self.targets:
            if not t.alive:
                continue
            dx = d.x - t.x
            dy = d.y - t.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < t.radius + 2:  # dart tip radius ~2
                return t
        return None

    def _dart_hit_target(self, d: Dart, t: Target) -> None:
        t.alive = False

        if d.super_mode or d.color_idx == t.color_idx:
            # Same color: combo up, score multiplied
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            multiplier = self.combo
            if d.super_mode:
                multiplier *= SUPER_MULTIPLIER
            earned = t.points * multiplier
            self.score += earned

            # Floating text
            self.floating_texts.append(FloatingText(
                x=t.x, y=t.y - 5,
                text=f"+{earned}",
                color=COLOR_VALS[d.color_idx],
                life=30,
            ))

            # Combo milestone text
            if self.combo >= COMBO_THRESHOLD and self.combo % COMBO_THRESHOLD == 0:
                self.floating_texts.append(FloatingText(
                    x=SCREEN_W // 2, y=SCREEN_H // 2,
                    text=f"COMBO x{self.combo}!",
                    color=pyxel.COLOR_WHITE,
                    life=40,
                ))

            # Trigger SUPER DART
            if self.combo >= COMBO_THRESHOLD and not self.super_active:
                self.super_active = True
                self.super_timer = 90  # 3 seconds
                self.floating_texts.append(FloatingText(
                    x=SCREEN_W // 2, y=SCREEN_H // 2 - 15,
                    text="SUPER DART!",
                    color=pyxel.COLOR_YELLOW,
                    life=60,
                ))

            # Spawn particles
            self._spawn_hit_particles(t.x, t.y, COLOR_VALS[d.color_idx])
        else:
            # Wrong color: combo reset, base points
            self.combo = 0
            earned = t.points
            self.score += earned

            self.floating_texts.append(FloatingText(
                x=t.x, y=t.y - 5,
                text=f"+{earned}",
                color=pyxel.COLOR_GRAY,
                life=30,
            ))

            # Spawn particles (gray)
            self._spawn_hit_particles(t.x, t.y, pyxel.COLOR_GRAY)

        # Remove hit target from list
        self.targets = [tg for tg in self.targets if tg.alive]

        # Store ghost trail
        if d.trail:
            self.ghost_trails.append(GhostTrail(
                points=list(d.trail),
                color_idx=d.color_idx,
                life=90,
            ))
            # Keep only last N ghost trails
            if len(self.ghost_trails) > GHOST_TRAIL_COUNT:
                self.ghost_trails = self.ghost_trails[-GHOST_TRAIL_COUNT:]

        # Advance dart color for next throw
        self.dart_color_idx = (self.dart_color_idx + 1) % NUM_COLORS

        # Reset dart
        self.dart = None
        self.phase = Phase.RESULT
        self.result_timer = 15

        # Replenish if dart count still OK
        if self.darts_remaining <= 0:
            self.phase = Phase.GAME_OVER

    def _dart_missed(self) -> None:
        if self.dart and self.dart.trail:
            self.ghost_trails.append(GhostTrail(
                points=list(self.dart.trail),
                color_idx=self.dart.color_idx,
                life=90,
            ))
            if len(self.ghost_trails) > GHOST_TRAIL_COUNT:
                self.ghost_trails = self.ghost_trails[-GHOST_TRAIL_COUNT:]

        self.combo = 0
        self.dart = None
        self.dart_color_idx = (self.dart_color_idx + 1) % NUM_COLORS
        self.phase = Phase.RESULT
        self.result_timer = 10

    def _update_result(self) -> None:
        self.result_timer -= 1
        if self.result_timer <= 0:
            self._replenish_targets()
            if self.darts_remaining <= 0 or self.timer <= 0:
                self.phase = Phase.GAME_OVER
            else:
                self.phase = Phase.AIMING

    def _spawn_hit_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(PARTICLE_COUNT):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                color=color,
                life=PARTICLE_LIFE,
            ))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1  # slight gravity
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _update_ghost_trails(self) -> None:
        for gt in self.ghost_trails:
            gt.life -= 1
        self.ghost_trails = [gt for gt in self.ghost_trails if gt.life > 0]

    # ── Draw ────────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        # Background board texture (subtle grid)
        for gx in range(0, SCREEN_W, 16):
            for gy in range(0, SCREEN_H, 16):
                if (gx // 16 + gy // 16) % 2 == 0:
                    pyxel.pset(gx, gy, pyxel.COLOR_NAVY)

        # Target zone divider line
        pyxel.line(
            0, TARGET_ZONE_BOTTOM + 4, SCREEN_W, TARGET_ZONE_BOTTOM + 4,
            pyxel.COLOR_DARK_BLUE,
        )

        # Draw ghost trails
        self._draw_ghost_trails()

        # Draw targets
        self._draw_targets()

        # Draw dart (flying)
        if self.phase == Phase.FLYING and self.dart is not None:
            self._draw_dart_trail(self.dart)
            self._draw_dart(self.dart)

        # Draw aim line
        if self.phase == Phase.AIMING:
            self._draw_aim_line()

        # Draw particles
        self._draw_particles()

        # Draw floating texts
        self._draw_floating_texts()

        # Draw dart at rest (aiming phase)
        if self.phase == Phase.AIMING:
            self._draw_dart_rest()

        # Draw HUD
        self._draw_hud()

        # Draw game over screen
        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_targets(self) -> None:
        for t in self.targets:
            if not t.alive:
                continue
            color = COLOR_VALS[t.color_idx]
            # Outer ring
            pyxel.circb(int(t.x), int(t.y), int(t.radius), color)
            # Inner ring (half radius)
            pyxel.circb(int(t.x), int(t.y), int(t.radius * 0.5), color)
            # Bullseye dot
            pyxel.circ(int(t.x), int(t.y), 2, color)

    def _draw_dart(self, d: Dart) -> None:
        if d.super_mode:
            # Rainbow flash
            colors = (pyxel.COLOR_RED, pyxel.COLOR_GREEN, pyxel.COLOR_YELLOW, pyxel.COLOR_LIGHT_BLUE)
            c = colors[pyxel.frame_count // 4 % 4]
        else:
            c = COLOR_VALS[d.color_idx]

        # Dart shape: small triangle + line
        # Direction from trail
        if len(d.trail) >= 2:
            px, py = d.trail[-2]
            dx = d.x - px
            dy = d.y - py
            mag = math.sqrt(dx * dx + dy * dy)
            if mag > 0.01:
                dx /= mag
                dy /= mag
                tip_x = d.x + dx * 4
                tip_y = d.y + dy * 4
                # Perpendicular
                px1 = d.x - dy * 2
                py1 = d.y + dx * 2
                px2 = d.x + dy * 2
                py2 = d.y - dx * 2
                pyxel.tri(int(tip_x), int(tip_y), int(px1), int(py1), int(px2), int(py2), c)
            else:
                pyxel.circ(int(d.x), int(d.y), 2, c)
        else:
            pyxel.circ(int(d.x), int(d.y), 2, c)

    def _draw_dart_rest(self) -> None:
        """Draw the dart sitting at the bottom, ready to throw."""
        color = COLOR_VALS[self.dart_color_idx]
        if self.super_active:
            # Rainbow flash for super mode
            colors = (pyxel.COLOR_RED, pyxel.COLOR_GREEN, pyxel.COLOR_YELLOW, pyxel.COLOR_LIGHT_BLUE)
            color = colors[pyxel.frame_count // 4 % 4]

        # Draw dart as a small triangle pointing up (ready to launch)
        pyxel.tri(
            DART_X, DART_Y - 6,
            DART_X - 4, DART_Y + 2,
            DART_X + 4, DART_Y + 2,
            color,
        )
        # Shaft
        pyxel.line(DART_X, DART_Y - 6, DART_X, DART_Y - 12, pyxel.COLOR_WHITE)

    def _draw_dart_trail(self, d: Dart) -> None:
        if len(d.trail) < 2:
            return
        color = COLOR_VALS[d.color_idx] if not d.super_mode else pyxel.COLOR_WHITE
        for i in range(len(d.trail) - 1):
            alpha = i / len(d.trail)
            c = color if alpha > 0.5 else pyxel.COLOR_GRAY
            x1, y1 = d.trail[i]
            x2, y2 = d.trail[i + 1]
            pyxel.line(int(x1), int(y1), int(x2), int(y2), c)

    def _draw_ghost_trails(self) -> None:
        for gt in self.ghost_trails:
            if gt.life < 10:
                continue
            c = pyxel.COLOR_GRAY
            for i in range(len(gt.points) - 1):
                x1, y1 = gt.points[i]
                x2, y2 = gt.points[i + 1]
                if i % 2 == 0:  # dotted effect
                    pyxel.pset(int(x1), int(y1), c)

    def _draw_aim_line(self) -> None:
        if self._drag_start is None or self._drag_current is None:
            return
        sx, sy = self._drag_start
        cx, cy = self._drag_current
        dx = sx - cx
        dy = sy - cy
        power = math.sqrt(dx * dx + dy * dy) / 10.0
        power = min(max(power, 0), MAX_POWER)

        # Draw line from dart to mouse position
        pyxel.line(DART_X, DART_Y, int(cx), int(cy), pyxel.COLOR_GRAY)

        # Draw predicted trajectory dots
        if power >= 2.0:
            power_clamped = min(power, MAX_POWER)
            power_clamped = max(power_clamped, MIN_POWER)
            if power > 0:
                norm_x = dx / (power * 10)
                norm_y = dy / (power * 10)
                vx = norm_x * power_clamped * 0.8
                vy = norm_y * power_clamped * 0.8
                px, py = float(DART_X), float(DART_Y)
                for step in range(30):
                    px += vx
                    py += vy
                    vy += GRAVITY
                    if px < 0 or px > SCREEN_W or py > SCREEN_H:
                        break
                    if step % 2 == 0:
                        pyxel.pset(int(px), int(py), pyxel.COLOR_GRAY)
                # Draw final impact dot
                pyxel.circ(int(px), int(py), 3, pyxel.COLOR_WHITE)

        # Power bar
        bar_x = DART_X - 20
        bar_y = DART_Y + 10
        bar_w = 40
        bar_h = 4
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, pyxel.COLOR_DARK_BLUE)
        fill_w = int(bar_w * (power / MAX_POWER))
        bar_color = pyxel.COLOR_GREEN if power < MAX_POWER * 0.6 else pyxel.COLOR_YELLOW if power < MAX_POWER * 0.85 else pyxel.COLOR_RED
        pyxel.rect(bar_x, bar_y, fill_w, bar_h, bar_color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha_shift = max(0, p.life - 5)
            c = p.color if alpha_shift > 0 else pyxel.COLOR_GRAY
            pyxel.pset(int(p.x), int(p.y), c)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life > 10:
                pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        # Score top-left
        pyxel.text(4, 2, f"SCORE:{self.score}", pyxel.COLOR_WHITE)

        # Combo top-right
        combo_color = COLOR_VALS[self.dart_color_idx] if self.combo > 0 else pyxel.COLOR_GRAY
        pyxel.text(SCREEN_W - 60, 2, f"COMBO:{self.combo}", combo_color)

        # Timer top-center
        secs = self.timer // FPS
        timer_color = pyxel.COLOR_WHITE if secs > 10 else pyxel.COLOR_RED
        pyxel.text(SCREEN_W // 2 - 12, 2, f"T:{secs:02d}", timer_color)

        # Darts remaining
        pyxel.text(SCREEN_W - 45, SCREEN_H - 8, f"D:{self.darts_remaining}", pyxel.COLOR_WHITE)

        # Super mode indicator
        if self.super_active:
            super_secs = self.super_timer // FPS
            pyxel.text(4, SCREEN_H - 8, f"SUPER:{super_secs}s", pyxel.COLOR_YELLOW)

        # Dart color indicator (bottom-left)
        pyxel.text(4, SCREEN_H - 18, f"NEXT:{COLOR_NAMES[self.dart_color_idx]}", COLOR_VALS[self.dart_color_idx])

        # Instructions (bottom center)
        if self.phase == Phase.AIMING:
            pyxel.text(SCREEN_W // 2 - 40, SCREEN_H - 18, "DRAG TO AIM", pyxel.COLOR_GRAY)

    def _draw_game_over(self) -> None:
        # Darken background
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, pyxel.COLOR_BLACK)

        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 - 30, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(SCREEN_W // 2 - 45, SCREEN_H // 2 - 10, f"SCORE: {self.score}", pyxel.COLOR_WHITE)
        pyxel.text(SCREEN_W // 2 - 55, SCREEN_H // 2 + 5, f"MAX COMBO: {self.max_combo}", pyxel.COLOR_YELLOW)
        pyxel.text(SCREEN_W // 2 - 50, SCREEN_H // 2 + 20, "PRESS R TO RETRY", pyxel.COLOR_GRAY)
