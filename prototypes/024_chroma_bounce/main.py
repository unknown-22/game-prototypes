"""
CHROMA BOUNCE — Color-Match Pinball
====================================
Reinterpreted from game idea #1 (score 31.65): dice/bag roguelite + space mining.
Hooks: "synthesis compression" + "one-color-per-turn" → color-match pinball.

Core mechanic: Bounce the ball off same-color bumpers to build COMBO.
COMBO >= 4 triggers SYNTHESIS super-mode (all bumpers rainbow, 3x score).
Wrong-color hits reset combo. Ball drains cost lives.

Engine: Pyxel 2.x, 220x320, display_scale=2
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

import pyxel

if TYPE_CHECKING:
    pass

# ── Config ──
SCREEN_W = 220
SCREEN_H = 320
PLAYFIELD_LEFT = 6
PLAYFIELD_RIGHT = SCREEN_W - 6
PLAYFIELD_TOP = 6
DRAIN_Y = SCREEN_H - 6
BALL_RADIUS = 4
BALL_MAX_SPEED = 8.0
BALL_MIN_SPEED = 1.5
GRAVITY = 0.13
LAUNCH_SPEED = -5.0

# Flippers
FLIPPER_PIVOT_L = (45, 272)
FLIPPER_PIVOT_R = (SCREEN_W - 45, 272)
FLIPPER_LEN = 32
FLIPPER_W = 5
FLIPPER_REST_ANGLE_L = 0.35      # rad, pointing right + slightly down
FLIPPER_ACTIVE_ANGLE_L = -1.05   # rad, pointing right + up
FLIPPER_REST_ANGLE_R = math.pi - 0.35    # pointing left + slightly down
FLIPPER_ACTIVE_ANGLE_R = math.pi + 1.05  # pointing left + up
FLIPPER_KICK = 3.5  # impulse strength when flipper activates

# Bumpers
BUMPER_RADIUS = 10
BUMPER_COUNT = 12
BUMPER_BOUNCE = 0.85  # bounce velocity multiplier

# Combo / Synthesis
COMBO_THRESHOLD = 4
SYNTHESIS_DURATION = 300  # frames (5 sec)
COMBO_SCORE_BASE = 10

# Game state
MAX_LIVES = 3

# Particles
PARTICLE_MAX = 60
PARTICLE_LIFE = 20

# Colors (Pyxel palette)
COLOR_FIRE = 0
COLOR_WATER = 1
COLOR_EARTH = 2
COLOR_AIR = 3
COLOR_COUNT = 4

PYXEL_COLORS: dict[int, int] = {
    COLOR_FIRE: pyxel.COLOR_RED,
    COLOR_WATER: pyxel.COLOR_CYAN,
    COLOR_EARTH: pyxel.COLOR_LIME,
    COLOR_AIR: pyxel.COLOR_YELLOW,
}

PYXEL_LIGHT: dict[int, int] = {
    COLOR_FIRE: pyxel.COLOR_ORANGE,
    COLOR_WATER: pyxel.COLOR_LIGHT_BLUE,
    COLOR_EARTH: pyxel.COLOR_GREEN,
    COLOR_AIR: pyxel.COLOR_PEACH,
}

COLOR_NAMES: list[str] = ["FIRE", "WATER", "EARTH", "AIR"]


# ── Data Classes ──

@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    color: int  # 0-3
    locked: bool = True  # True = in launcher

@dataclass
class Bumper:
    x: float
    y: float
    radius: int
    color: int  # 0-3
    flash_timer: int = 0  # hit flash countdown

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


# ── Phase Enum ──

class Phase(Enum):
    LAUNCH = auto()     # ball in launcher
    PLAYING = auto()    # ball in play
    DRAIN = auto()      # ball draining
    GAME_OVER = auto()  # no lives left


# ── Game ──

class ChromaBounce:
    """Color-match pinball game."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CHROMA BOUNCE", display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        """Reset game to initial state."""
        self.phase = Phase.LAUNCH
        self.score: int = 0
        self.high_score: int = 0
        self.lives: int = MAX_LIVES
        self.combo: int = 0
        self.max_combo: int = 0
        self.synthesis_timer: int = 0
        self.synthesis_active: bool = False

        # Flipper state
        self.flipper_left_active: bool = False
        self.flipper_right_active: bool = False
        self.flipper_left_was_active: bool = False
        self.flipper_right_was_active: bool = False
        self.flipper_left_angle: float = FLIPPER_REST_ANGLE_L
        self.flipper_right_angle: float = FLIPPER_REST_ANGLE_R

        # Ball
        self.ball = self._new_ball()

        # Bumpers
        self.bumpers: list[Bumper] = []
        self._spawn_bumpers()

        # Particles
        self.particles: list[Particle] = []

    def _new_ball(self) -> Ball:
        """Create a new ball in the launcher position."""
        return Ball(
            x=SCREEN_W / 2,
            y=DRAIN_Y - 20,
            vx=0.0,
            vy=0.0,
            color=random.randint(0, COLOR_COUNT - 1),
            locked=True,
        )

    def _spawn_bumpers(self) -> None:
        """Create colored bumpers in the playfield."""
        self.bumpers.clear()
        # Row 1
        for i in range(4):
            self.bumpers.append(Bumper(32 + i * 50, 55, BUMPER_RADIUS, i % COLOR_COUNT))
        # Row 2
        for i in range(4):
            self.bumpers.append(Bumper(47 + i * 50, 120, BUMPER_RADIUS, (i + 2) % COLOR_COUNT))
        # Row 3
        for i in range(4):
            self.bumpers.append(Bumper(32 + i * 50, 185, BUMPER_RADIUS, (i + 1) % COLOR_COUNT))
        # Row 4 (bottom bumpers, smaller)
        for i in range(4):
            self.bumpers.append(Bumper(47 + i * 50, 240, 8, i % COLOR_COUNT))

    # ── Update ──

    def update(self) -> None:
        """Main update loop."""
        # Always allow restart
        if pyxel.btnp(pyxel.KEY_R) and self.phase == Phase.GAME_OVER:
            self.reset()
            return

        if self.phase == Phase.LAUNCH:
            self._update_launch()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.DRAIN:
            self._update_drain()

        # Particle updates (always)
        self._update_particles()

    def _update_launch(self) -> None:
        """Handle ball launch phase."""
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.ball.locked = False
            self.ball.vy = LAUNCH_SPEED
            self.ball.vx = random.uniform(-0.5, 0.5)
            self.ball.color = random.randint(0, COLOR_COUNT - 1)
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        """Main gameplay update."""
        # Input
        self.flipper_left_was_active = self.flipper_left_active
        self.flipper_right_was_active = self.flipper_right_active
        self.flipper_left_active = pyxel.btn(pyxel.KEY_Z) or pyxel.btn(pyxel.KEY_LEFT)
        self.flipper_right_active = pyxel.btn(pyxel.KEY_M) or pyxel.btn(pyxel.KEY_RIGHT)

        # Flipper angles
        self.flipper_left_angle = (
            FLIPPER_ACTIVE_ANGLE_L if self.flipper_left_active else FLIPPER_REST_ANGLE_L
        )
        self.flipper_right_angle = (
            FLIPPER_ACTIVE_ANGLE_R if self.flipper_right_active else FLIPPER_REST_ANGLE_R
        )

        # Synthesis timer
        if self.synthesis_active:
            self.synthesis_timer -= 1
            if self.synthesis_timer <= 0:
                self.synthesis_active = False
                self.combo = 0

        # Physics
        self._update_physics()

        # Check drain
        if self.ball.y > DRAIN_Y + 20:
            self.phase = Phase.DRAIN
            self.synthesis_active = False

    def _update_physics(self) -> None:
        """Apply gravity, movement, wall/bumper/flipper collisions."""
        b = self.ball

        # Gravity
        b.vy += GRAVITY

        # Speed clamping
        speed = math.sqrt(b.vx * b.vx + b.vy * b.vy)
        if speed > BALL_MAX_SPEED:
            scale = BALL_MAX_SPEED / speed
            b.vx *= scale
            b.vy *= scale

        # Move
        b.x += b.vx
        b.y += b.vy

        # Wall collisions
        if b.x - BALL_RADIUS < PLAYFIELD_LEFT:
            b.x = PLAYFIELD_LEFT + BALL_RADIUS
            b.vx = abs(b.vx) * 0.8
            self._spawn_wall_particles(b.x, b.y, -1, 0)

        if b.x + BALL_RADIUS > PLAYFIELD_RIGHT:
            b.x = PLAYFIELD_RIGHT - BALL_RADIUS
            b.vx = -abs(b.vx) * 0.8
            self._spawn_wall_particles(b.x, b.y, 1, 0)

        if b.y - BALL_RADIUS < PLAYFIELD_TOP:
            b.y = PLAYFIELD_TOP + BALL_RADIUS
            b.vy = abs(b.vy) * 0.8
            self._spawn_wall_particles(b.x, b.y, 0, -1)

        # Flipper collisions
        self._check_flipper_collision(
            FLIPPER_PIVOT_L[0], FLIPPER_PIVOT_L[1],
            self.flipper_left_angle, FLIPPER_LEN,
            self.flipper_left_active and not self.flipper_left_was_active,
        )
        self._check_flipper_collision(
            FLIPPER_PIVOT_R[0], FLIPPER_PIVOT_R[1],
            self.flipper_right_angle, FLIPPER_LEN,
            self.flipper_right_active and not self.flipper_right_was_active,
        )

        # Bumper collisions
        self._check_bumper_collisions()

        # Ensure minimum speed to prevent getting stuck
        if speed < BALL_MIN_SPEED and speed > 0:
            scale = BALL_MIN_SPEED / speed
            b.vx *= scale
            b.vy *= scale

    def _flipper_tip(self, px: float, py: float, angle: float, length: float) -> tuple[float, float]:
        """Get flipper tip position from pivot and angle."""
        return (px + math.cos(angle) * length, py + math.sin(angle) * length)

    def _closest_point_on_segment(
        self, px: float, py: float, ax: float, ay: float, bx: float, by: float
    ) -> tuple[float, float]:
        """Find closest point on segment AB to point P."""
        abx = bx - ax
        aby = by - ay
        ab_len_sq = abx * abx + aby * aby
        if ab_len_sq < 0.001:
            return ax, ay
        t = ((px - ax) * abx + (py - ay) * aby) / ab_len_sq
        t = max(0.0, min(1.0, t))
        return ax + t * abx, ay + t * aby

    def _check_flipper_collision(
        self, px: float, py: float, angle: float, length: float, just_activated: bool
    ) -> None:
        """Check and handle ball-flipper collision."""
        b = self.ball
        tx, ty = self._flipper_tip(px, py, angle, length)
        cx, cy = self._closest_point_on_segment(b.x, b.y, px, py, tx, ty)

        dx = b.x - cx
        dy = b.y - cy
        dist = math.sqrt(dx * dx + dy * dy)

        if dist >= BALL_RADIUS + FLIPPER_W:
            return

        # Push ball out
        if dist < 0.01:
            dx = b.vx if abs(b.vx) > 0.01 else 0.1
            dy = b.vy if abs(b.vy) > 0.01 else -0.1
            dist = math.sqrt(dx * dx + dy * dy)

        overlap = BALL_RADIUS + FLIPPER_W - dist
        nx = dx / dist
        ny = dy / dist
        b.x += nx * overlap
        b.y += ny * overlap

        # Reflect velocity across segment normal
        dot = b.vx * nx + b.vy * ny
        if dot < 0:  # ball moving toward flipper
            b.vx -= 2 * dot * nx
            b.vy -= 2 * dot * ny
            b.vx *= 0.75  # energy loss
            b.vy *= 0.75

        # Kick impulse if flipper just activated
        if just_activated:
            kick_dir_x = -math.sin(angle)  # perpendicular to flipper
            kick_dir_y = math.cos(angle)
            # Ensure kick goes upward
            if kick_dir_y > 0:
                kick_dir_y = -kick_dir_y
                kick_dir_x = -kick_dir_x
            b.vx += kick_dir_x * FLIPPER_KICK
            b.vy += kick_dir_y * FLIPPER_KICK

    def _check_bumper_collisions(self) -> None:
        """Check ball-bumper collisions."""
        b = self.ball
        for bumper in self.bumpers:
            dx = b.x - bumper.x
            dy = b.y - bumper.y
            dist_sq = dx * dx + dy * dy
            min_dist = BALL_RADIUS + bumper.radius
            if dist_sq < min_dist * min_dist:
                dist = math.sqrt(dist_sq)
                if dist < 0.01:
                    dx = b.vx if abs(b.vx) > 0.01 else 0.1
                    dy = b.vy if abs(b.vy) > 0.01 else -0.1
                    dist = math.sqrt(dx * dx + dy * dy)

                # Push out
                overlap = min_dist - dist
                nx = dx / dist
                ny = dy / dist
                b.x += nx * overlap
                b.y += ny * overlap

                # Reflect
                dot = b.vx * nx + b.vy * ny
                if dot < 0:
                    b.vx -= 2 * dot * nx
                    b.vy -= 2 * dot * ny

                b.vx *= BUMPER_BOUNCE
                b.vy *= BUMPER_BOUNCE

                # Flash effect
                bumper.flash_timer = 8

                # Scoring
                self._on_bumper_hit(bumper)

    def _on_bumper_hit(self, bumper: Bumper) -> None:
        """Handle score and combo on bumper hit."""
        is_same_color = (bumper.color == self.ball.color) or self.synthesis_active

        if is_same_color:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            multiplier = 3 if self.synthesis_active else 1
            points = COMBO_SCORE_BASE * self.combo * multiplier
            self.score += points

            # Check synthesis trigger
            if not self.synthesis_active and self.combo >= COMBO_THRESHOLD:
                self._activate_synthesis()

            # Spawn hit particles
            self._spawn_hit_particles(bumper.x, bumper.y, bumper.color, points)
        else:
            self.combo = 0
            self.score += 5
            self._spawn_hit_particles(bumper.x, bumper.y, -1, 5)

        # Ball takes bumper's color
        if not self.synthesis_active:
            self.ball.color = bumper.color

    def _activate_synthesis(self) -> None:
        """Activate synthesis super-mode."""
        self.synthesis_active = True
        self.synthesis_timer = SYNTHESIS_DURATION
        # Spawn burst particles
        for _ in range(20):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1, 4)
            self.particles.append(Particle(
                self.ball.x, self.ball.y,
                math.cos(angle) * speed, math.sin(angle) * speed,
                PARTICLE_LIFE, -1,
            ))

    def _update_drain(self) -> None:
        """Handle ball draining."""
        self.ball.vy += 0.3
        self.ball.y += self.ball.vy
        if self.ball.y > SCREEN_H + 20:
            self.lives -= 1
            self.combo = 0
            self.synthesis_active = False
            if self.lives <= 0:
                if self.score > self.high_score:
                    self.high_score = self.score
                self.phase = Phase.GAME_OVER
            else:
                self.ball = self._new_ball()
                self.phase = Phase.LAUNCH

    def _update_particles(self) -> None:
        """Update particle lifetimes."""
        alive: list[Particle] = []
        for p in self.particles:
            p.life -= 1
            if p.life > 0:
                p.x += p.vx
                p.y += p.vy
                p.vy += 0.05
                alive.append(p)
        self.particles = alive

    def _spawn_wall_particles(self, x: float, y: float, dx: float, dy: float) -> None:
        """Spawn small particles on wall hit."""
        for _ in range(2):
            self.particles.append(Particle(
                x, y,
                dx * random.uniform(0.5, 1.5) + random.uniform(-0.3, 0.3),
                dy * random.uniform(0.5, 1.5) + random.uniform(-0.3, 0.3),
                8, pyxel.COLOR_WHITE,
            ))

    def _spawn_hit_particles(self, x: float, y: float, color: int, points: int) -> None:
        """Spawn particles on bumper hit."""
        pcol = PYXEL_COLORS.get(color, pyxel.COLOR_WHITE)
        count = 6 if color >= 0 else 3
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(0.5, 2.5)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * speed, math.sin(angle) * speed - 1.0,
                PARTICLE_LIFE // 2, pcol,
            ))

    # ── Draw ──

    def draw(self) -> None:
        """Main draw loop."""
        pyxel.cls(pyxel.COLOR_BLACK)

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
            return

        self._draw_playfield()
        self._draw_bumpers()
        self._draw_flippers()
        self._draw_ball()
        self._draw_particles()
        self._draw_ui()

    def _draw_playfield(self) -> None:
        """Draw walls and boundaries."""
        # Side walls
        pyxel.rect(0, 0, PLAYFIELD_LEFT, SCREEN_H, pyxel.COLOR_GRAY)
        pyxel.rect(PLAYFIELD_RIGHT, 0, SCREEN_W - PLAYFIELD_RIGHT, SCREEN_H, pyxel.COLOR_GRAY)
        # Top wall
        pyxel.rect(0, 0, SCREEN_W, PLAYFIELD_TOP, pyxel.COLOR_GRAY)
        # Inner glow lines
        pyxel.line(PLAYFIELD_LEFT, PLAYFIELD_TOP, PLAYFIELD_LEFT, SCREEN_H, pyxel.COLOR_DARK_BLUE)
        pyxel.line(PLAYFIELD_RIGHT, PLAYFIELD_TOP, PLAYFIELD_RIGHT, SCREEN_H, pyxel.COLOR_DARK_BLUE)
        # Drain zone
        pyxel.rect(PLAYFIELD_LEFT, DRAIN_Y, PLAYFIELD_RIGHT - PLAYFIELD_LEFT, SCREEN_H - DRAIN_Y, pyxel.COLOR_NAVY)

    def _draw_bumpers(self) -> None:
        """Draw all bumpers."""
        for bumper in self.bumpers:
            if self.synthesis_active:
                col = pyxel.COLOR_WHITE
                if (pyxel.frame_count // 4) % 2 == 0:
                    col = pyxel.COLOR_PINK
            elif bumper.flash_timer > 0:
                col = pyxel.COLOR_WHITE
                bumper.flash_timer -= 1
            else:
                col = PYXEL_COLORS[bumper.color]

            # Draw filled circle
            pyxel.circ(bumper.x, bumper.y, bumper.radius, col)
            # Inner circle
            inner_col = pyxel.COLOR_BLACK if bumper.flash_timer <= 0 or (pyxel.frame_count // 2) % 2 == 0 else col
            pyxel.circ(bumper.x, bumper.y, bumper.radius - 3, inner_col)
            # Color dot in center
            if not self.synthesis_active:
                pyxel.circ(bumper.x, bumper.y, 2, PYXEL_LIGHT[bumper.color])

    def _draw_flippers(self) -> None:
        """Draw flippers."""
        # Left flipper
        l_tx, l_ty = self._flipper_tip(
            FLIPPER_PIVOT_L[0], FLIPPER_PIVOT_L[1],
            self.flipper_left_angle, FLIPPER_LEN,
        )
        pyxel.line(
            FLIPPER_PIVOT_L[0], FLIPPER_PIVOT_L[1],
            l_tx, l_ty,
            pyxel.COLOR_ORANGE if self.synthesis_active else pyxel.COLOR_WHITE,
        )
        # Draw flipper body (thick line)
        perp_x = -math.sin(self.flipper_left_angle)
        perp_y = math.cos(self.flipper_left_angle)
        for i in range(-FLIPPER_W, FLIPPER_W + 1):
            pcol = pyxel.COLOR_WHITE if (i >= -1 and i <= 1) else pyxel.COLOR_GRAY
            if self.synthesis_active:
                pcol = pyxel.COLOR_ORANGE if (i >= -1 and i <= 1) else pyxel.COLOR_PEACH
            pyxel.line(
                int(FLIPPER_PIVOT_L[0] + perp_x * i),
                int(FLIPPER_PIVOT_L[1] + perp_y * i),
                int(l_tx + perp_x * i),
                int(l_ty + perp_y * i),
                pcol,
            )

        # Right flipper
        r_tx, r_ty = self._flipper_tip(
            FLIPPER_PIVOT_R[0], FLIPPER_PIVOT_R[1],
            self.flipper_right_angle, FLIPPER_LEN,
        )
        pyxel.line(
            FLIPPER_PIVOT_R[0], FLIPPER_PIVOT_R[1],
            r_tx, r_ty,
            pyxel.COLOR_ORANGE if self.synthesis_active else pyxel.COLOR_WHITE,
        )
        perp_x_r = -math.sin(self.flipper_right_angle)
        perp_y_r = math.cos(self.flipper_right_angle)
        for i in range(-FLIPPER_W, FLIPPER_W + 1):
            pcol = pyxel.COLOR_WHITE if (i >= -1 and i <= 1) else pyxel.COLOR_GRAY
            if self.synthesis_active:
                pcol = pyxel.COLOR_ORANGE if (i >= -1 and i <= 1) else pyxel.COLOR_PEACH
            pyxel.line(
                int(FLIPPER_PIVOT_R[0] + perp_x_r * i),
                int(FLIPPER_PIVOT_R[1] + perp_y_r * i),
                int(r_tx + perp_x_r * i),
                int(r_ty + perp_y_r * i),
                pcol,
            )

    def _draw_ball(self) -> None:
        """Draw the ball."""
        b = self.ball
        if self.phase == Phase.DRAIN:
            # Fading ball
            alpha_tick = (pyxel.frame_count // 3) % 3
            if alpha_tick == 0:
                return

        ball_col = PYXEL_COLORS.get(b.color, pyxel.COLOR_WHITE)
        if self.synthesis_active:
            ball_col = pyxel.COLOR_WHITE

        # Glow effect
        pyxel.circ(b.x, b.y, BALL_RADIUS + 2, pyxel.COLOR_BLACK)
        pyxel.circ(b.x, b.y, BALL_RADIUS + 1, PYXEL_LIGHT.get(b.color, pyxel.COLOR_GRAY))
        pyxel.circ(b.x, b.y, BALL_RADIUS, ball_col)
        # Inner highlight
        pyxel.circ(b.x - 1, b.y - 1, BALL_RADIUS - 2, pyxel.COLOR_WHITE)
        pyxel.circ(b.x - 1, b.y - 1, BALL_RADIUS - 3, ball_col)

        # Launcher guide line
        if b.locked:
            pyxel.line(b.x, b.y, b.x, b.y + 15, pyxel.COLOR_GRAY)

    def _draw_particles(self) -> None:
        """Draw active particles."""
        for p in self.particles:
            alpha = p.life / PARTICLE_LIFE
            size = max(1, int(2 * alpha))
            pyxel.pset(p.x, p.y, p.color)
            if size > 1:
                pyxel.pset(p.x + 1, p.y, p.color)
                pyxel.pset(p.x, p.y + 1, p.color)

    def _draw_ui(self) -> None:
        """Draw score, combo, lives HUD."""
        # Score (top-left)
        pyxel.text(10, 2, f"SCORE:{self.score:06d}", pyxel.COLOR_WHITE)

        # High score (top-right)
        hs_text = f"HI:{self.high_score:06d}"
        pyxel.text(SCREEN_W - len(hs_text) * 4 - 8, 2, hs_text, pyxel.COLOR_GRAY)

        # Combo (centered, under playfield)
        if self.combo > 0:
            combo_text = f"COMBO x{self.combo}"
            if self.synthesis_active:
                combo_text = f"SYNTHESIS x{self.combo}"
            cx = SCREEN_W // 2 - len(combo_text) * 2
            combo_col = pyxel.COLOR_ORANGE if self.synthesis_active else pyxel.COLOR_YELLOW
            if self.combo >= COMBO_THRESHOLD - 1:
                # Pulsing when close to synthesis
                if (pyxel.frame_count // 8) % 2 == 0:
                    combo_col = pyxel.COLOR_RED
            pyxel.text(cx, DRAIN_Y - 12, combo_text, combo_col)

        # Synthesis timer bar
        if self.synthesis_active:
            bar_w = 100
            bar_h = 4
            bar_x = SCREEN_W // 2 - bar_w // 2
            bar_y = DRAIN_Y - 6
            fill = int(bar_w * self.synthesis_timer / SYNTHESIS_DURATION)
            pyxel.rect(bar_x, bar_y, bar_w, bar_h, pyxel.COLOR_GRAY)
            pyxel.rect(bar_x, bar_y, fill, bar_h, pyxel.COLOR_ORANGE)
            # Flashing if low
            if self.synthesis_timer < 60 and (pyxel.frame_count // 4) % 2 == 0:
                pyxel.rect(bar_x, bar_y, fill, bar_h, pyxel.COLOR_RED)

        # Lives (bottom)
        lives_text = f"BALLS:{'O' * self.lives}{'-' * (MAX_LIVES - self.lives)}"
        pyxel.text(8, SCREEN_H - 8, lives_text, pyxel.COLOR_WHITE)

        # Controls hint (launch phase)
        if self.phase == Phase.LAUNCH:
            hint = "PRESS SPACE TO LAUNCH"
            hx = SCREEN_W // 2 - len(hint) * 2
            pyxel.text(hx, DRAIN_Y - 18, hint, pyxel.COLOR_YELLOW)

        # Ball color indicator
        if self.phase in (Phase.PLAYING, Phase.LAUNCH) and not self.synthesis_active:
            color_name = COLOR_NAMES[self.ball.color]
            pyxel.text(SCREEN_W - 42, SCREEN_H - 8, color_name, PYXEL_COLORS[self.ball.color])

    def _draw_game_over(self) -> None:
        """Draw game over screen."""
        pyxel.cls(pyxel.COLOR_NAVY)

        # Title
        title = "GAME OVER"
        tx = SCREEN_W // 2 - len(title) * 2
        pyxel.text(tx, 80, title, pyxel.COLOR_RED)

        # Score
        score_text = f"SCORE: {self.score:06d}"
        sx = SCREEN_W // 2 - len(score_text) * 2
        pyxel.text(sx, 120, score_text, pyxel.COLOR_WHITE)

        # High score
        hs_text = f"BEST:  {self.high_score:06d}"
        if self.score >= self.high_score and self.score > 0:
            hs_text = f"NEW BEST: {self.high_score:06d}"
        hx = SCREEN_W // 2 - len(hs_text) * 2
        pyxel.text(hx, 140, hs_text, pyxel.COLOR_YELLOW)

        # Max combo
        combo_text = f"MAX COMBO: x{self.max_combo}"
        cx = SCREEN_W // 2 - len(combo_text) * 2
        pyxel.text(cx, 165, combo_text, pyxel.COLOR_ORANGE)

        # Restart hint
        restart = "PRESS R TO RETRY"
        rx = SCREEN_W // 2 - len(restart) * 2
        pyxel.text(rx, 210, restart, pyxel.COLOR_GREEN)


# ── Entry Point ──

def main() -> None:
    ChromaBounce()


if __name__ == "__main__":
    main()
