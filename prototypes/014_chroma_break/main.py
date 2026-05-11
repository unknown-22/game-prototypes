"""CHROMA BREAK — Color-match breakout.

Reinterpreted from game_idea_factory idea #1 (Score 31.65):
  "synthesis/compress into one card" → combo chain → SUPER BALL
  "one color per turn" → paddle cycles through 4 colors,
    ball only damages matching-color bricks.

Core loop: aim ball → watch combo build → SUPER BALL → next wave.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import IntEnum

import pyxel

# ── Config ────────────────────────────────────────────────────────────────────

SCREEN_W = 256
SCREEN_H = 256
DISPLAY_SCALE = 3

PADDLE_W = 48
PADDLE_H = 8
PADDLE_Y = 232

BALL_R = 3
BALL_SPEED = 3.5

BRICK_W = 32
BRICK_H = 12
BRICK_ROWS_START = 4
BRICK_COLS = 8
BRICK_Y_START = 32
BRICK_GAP = 2

COMBO_THRESHOLD = 6  # combos needed for SUPER BALL

# pyxel color palette indices
C_BLACK = 0
C_RED = 8
C_GREEN = 3
C_BLUE = 12
C_YELLOW = 10
C_WHITE = 7
C_GRAY = 13
C_ORANGE = 9
C_PURPLE = 2
C_CYAN = 11
C_PINK = 14

# 4 element colors the paddle cycles through
ELEMENT_COLORS: list[int] = [C_RED, C_BLUE, C_GREEN, C_YELLOW]
ELEMENT_NAMES: list[str] = ["FIRE", "WATER", "EARTH", "LIGHT"]
ELEMENT_LABELS: list[str] = ["R", "B", "G", "Y"]


class Phase(IntEnum):
    AIM = 0        # ball on paddle, player aims
    PLAY = 1       # ball in flight
    BALL_LOST = 2  # ball fell, brief pause
    SUPER = 3      # super ball animation
    WAVE_CLEAR = 4 # all bricks destroyed
    GAME_OVER = 5


@dataclass
class Brick:
    x: float
    y: float
    w: float
    h: float
    color_idx: int  # index into ELEMENT_COLORS
    hp: int = 1
    flashing: int = 0  # frames of white flash remaining


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    color_idx: int  # current color of the ball (matches paddle)
    super_mode: bool = False  # super ball pierces all colors


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class PowerUp:
    x: float
    y: float
    kind: str  # "WIDE", "SLOW", "LIFE", "MULTI"
    vy: float = 1.2
    life: int = 600  # falls for 10 sec max


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int
    vy: float = -1.5


# ── Wave definitions ──────────────────────────────────────────────────────────

# Each wave: rows, speed_mult, bricks_with_hp2_count
WAVE_DEFS: list[dict[str, int]] = [
    {"rows": 4, "speed_mult": 100, "hp2_count": 0},
    {"rows": 5, "speed_mult": 110, "hp2_count": 4},
    {"rows": 5, "speed_mult": 120, "hp2_count": 8},
    {"rows": 6, "speed_mult": 130, "hp2_count": 12},
    {"rows": 6, "speed_mult": 140, "hp2_count": 16},
    {"rows": 7, "speed_mult": 150, "hp2_count": 20},
]


# ── Game ──────────────────────────────────────────────────────────────────────

class Game:
    """Main game class. Handles update/draw for Pyxel."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CHROMA BREAK", display_scale=DISPLAY_SCALE)
        self.reset()
        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.AIM
        self.score: int = 0
        self.lives: int = 3
        self.wave: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.paddle_color: int = 0  # index into ELEMENT_COLORS
        self.paddle_w: float = float(PADDLE_W)
        self.paddle_x: float = SCREEN_W / 2 - PADDLE_W / 2
        self.paddle_timer: int = 0  # frames remaining for WIDE power-up

        self.balls: list[Ball] = []
        self.bricks: list[Brick] = []
        self.particles: list[Particle] = []
        self.power_ups: list[PowerUp] = []
        self.float_texts: list[FloatingText] = []
        self.screen_shake: int = 0

        self._ball_lost_timer: int = 0
        self._wave_clear_timer: int = 0
        self._ball_speed_base: float = BALL_SPEED

        self._spawn_wave()

    # ── Wave spawning ─────────────────────────────────────────────────────

    def _spawn_wave(self) -> None:
        """Create bricks for the current wave."""
        self.bricks.clear()
        self.balls.clear()
        self.power_ups.clear()

        wdef = WAVE_DEFS[min(self.wave, len(WAVE_DEFS) - 1)]
        rows = wdef["rows"]
        hp2_count = wdef["hp2_count"]
        self._ball_speed_base = BALL_SPEED * (wdef["speed_mult"] / 100.0)

        # Build brick grid
        cols = BRICK_COLS
        for row in range(rows):
            for col in range(cols):
                bx = col * (BRICK_W + BRICK_GAP) + BRICK_GAP
                by = BRICK_Y_START + row * (BRICK_H + BRICK_GAP)
                color_idx = (row + col) % 4
                self.bricks.append(Brick(bx, by, BRICK_W, BRICK_H, color_idx))

        # Assign 2 HP to random bricks
        hp2_indices = random.sample(range(len(self.bricks)), min(hp2_count, len(self.bricks)))
        for i in hp2_indices:
            self.bricks[i].hp = 2

        # Reset paddle
        self.paddle_x = SCREEN_W / 2 - self.paddle_w / 2
        self.paddle_color = 0
        self.combo = 0

        # Create ball on paddle
        self._reset_ball()

    def _reset_ball(self) -> None:
        """Place ball on paddle, ready to aim."""
        self.balls = [Ball(
            x=self.paddle_x + self.paddle_w / 2,
            y=PADDLE_Y - BALL_R - 1,
            vx=0.0,
            vy=0.0,
            color_idx=self.paddle_color,
        )]
        self.phase = Phase.AIM

    # ── Update ────────────────────────────────────────────────────────────

    def update(self) -> None:
        """Main update called by pyxel each frame."""
        # Screen shake decay
        if self.screen_shake > 0:
            self.screen_shake -= 1

        # Always allow restart
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()
            return

        if self.phase == Phase.AIM:
            self._update_aim()
        elif self.phase == Phase.PLAY:
            self._update_play()
        elif self.phase == Phase.BALL_LOST:
            self._update_ball_lost()
        elif self.phase == Phase.SUPER:
            self._update_super()
        elif self.phase == Phase.WAVE_CLEAR:
            self._update_wave_clear()
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.wave = 0
                self.score = 0
                self.lives = 3
                self.max_combo = 0
                self._spawn_wave()

        # Always update particles and floating text
        self._update_particles()
        self._update_float_texts()

    def _update_aim(self) -> None:
        """Aim phase: ball sits on paddle, player positions and chooses color."""
        self._update_paddle()
        self._update_color_switch()

        # Ball follows paddle
        ball = self.balls[0]
        ball.x = self.paddle_x + self.paddle_w / 2
        ball.y = PADDLE_Y - BALL_R - 1
        ball.color_idx = self.paddle_color

        # Launch
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            # Calculate launch angle from mouse position
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            dx = mx - ball.x
            dy = my - ball.y
            if dy >= 0:
                dy = -1  # force upward if mouse is below ball
            dist = math.hypot(dx, dy)
            if dist < 1:
                dx, dy = 0.0, -1.0
                dist = 1.0
            ball.vx = (dx / dist) * self._ball_speed_base
            ball.vy = (dy / dist) * self._ball_speed_base
            self.phase = Phase.PLAY

    def _update_play(self) -> None:
        """Main play phase: balls bouncing, bricks breaking."""
        self._update_paddle()
        self._update_color_switch()

        # Update each ball
        balls_to_remove: list[int] = []
        for i, ball in enumerate(self.balls):
            if not self._update_ball_physics(ball):
                balls_to_remove.append(i)

        # Remove dead balls in reverse order
        for i in reversed(balls_to_remove):
            del self.balls[i]

        # Update power-ups
        self._update_power_ups()

        # Check wave clear
        if len(self.bricks) == 0 and self.phase == Phase.PLAY:
            self.phase = Phase.WAVE_CLEAR
            self._wave_clear_timer = 60
            self.score += 500 * (self.wave + 1)

    def _update_ball_physics(self, ball: Ball) -> bool:
        """Move ball, handle collisions. Returns True if ball still alive."""
        ball.x += ball.vx
        ball.y += ball.vy

        # Wall bounces
        if ball.x - BALL_R <= 0:
            ball.x = float(BALL_R)
            ball.vx = abs(ball.vx)
        elif ball.x + BALL_R >= SCREEN_W:
            ball.x = SCREEN_W - BALL_R
            ball.vx = -abs(ball.vx)

        if ball.y - BALL_R <= 0:
            ball.y = float(BALL_R)
            ball.vy = abs(ball.vy)

        # Bottom — ball lost
        if ball.y - BALL_R > SCREEN_H:
            return False

        # Paddle bounce
        if self._check_paddle_collision(ball):
            return True

        # Brick collisions
        self._check_brick_collisions(ball)

        return True

    def _check_paddle_collision(self, ball: Ball) -> bool:
        """Check and handle ball-paddle collision. Returns True if collision happened."""
        if ball.vy <= 0:
            return False  # ball moving up, skip

        px = self.paddle_x
        py = float(PADDLE_Y)
        pw = self.paddle_w

        if (ball.x + BALL_R >= px and ball.x - BALL_R <= px + pw and
                ball.y + BALL_R >= py and ball.y - BALL_R <= py + PADDLE_H):
            # Bounce off paddle
            ball.y = py - BALL_R
            hit_pos = (ball.x - px) / pw  # 0.0 to 1.0
            angle = (hit_pos - 0.5) * 120  # -60 to +60 degrees
            speed = self._ball_speed_base
            ball.vx = speed * math.sin(math.radians(angle))
            ball.vy = -speed * math.cos(math.radians(angle))

            # Ball color updates to match paddle
            ball.color_idx = self.paddle_color
            ball.super_mode = self.combo >= COMBO_THRESHOLD

            if ball.super_mode:
                self.phase = Phase.SUPER
                self.screen_shake = 8

            # Spawn paddle hit particles
            for _ in range(3):
                self.particles.append(Particle(
                    x=ball.x, y=ball.y,
                    vx=random.uniform(-1, 1),
                    vy=random.uniform(-2, -1),
                    life=10, color=ELEMENT_COLORS[self.paddle_color],
                ))

            return True
        return False

    def _check_brick_collisions(self, ball: Ball) -> None:
        """Check ball against all bricks, handle first collision."""
        for brick in self.bricks:
            if self._ball_rect_collision(ball, brick):
                if ball.super_mode or brick.color_idx == ball.color_idx:
                    self._break_brick(brick, ball)
                else:
                    # Wrong color — bounce off, reset combo
                    self._deflect_ball(ball, brick)
                    if self.combo > 0:
                        self._add_float_text(
                            ball.x, ball.y, "MISS", C_GRAY,
                        )
                    self.combo = 0
                return  # only process one brick per frame per ball

    def _ball_rect_collision(self, ball: Ball, brick: Brick) -> bool:
        """Circle-rect collision test."""
        cx = ball.x
        cy = ball.y
        rx = brick.x
        ry = brick.y
        rw = brick.w
        rh = brick.h

        # Find closest point on rect to circle center
        closest_x = max(rx, min(cx, rx + rw))
        closest_y = max(ry, min(cy, ry + rh))

        dist_x = cx - closest_x
        dist_y = cy - closest_y
        return (dist_x * dist_x + dist_y * dist_y) < (BALL_R * BALL_R)

    def _deflect_ball(self, ball: Ball, brick: Brick) -> None:
        """Bounce ball off a brick of wrong color (no damage)."""
        # Determine which side was hit
        cx = ball.x
        cy = ball.y
        rx = brick.x
        ry = brick.y
        rw = brick.w
        rh = brick.h

        # Overlap amounts on each side
        overlap_left = (cx + BALL_R) - rx
        overlap_right = (rx + rw) - (cx - BALL_R)
        overlap_top = (cy + BALL_R) - ry
        overlap_bottom = (ry + rh) - (cy - BALL_R)

        min_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)

        if min_overlap == overlap_left:
            ball.x = rx - BALL_R
            ball.vx = -abs(ball.vx)
        elif min_overlap == overlap_right:
            ball.x = rx + rw + BALL_R
            ball.vx = abs(ball.vx)
        elif min_overlap == overlap_top:
            ball.y = ry - BALL_R
            ball.vy = -abs(ball.vy)
        else:
            ball.y = ry + rh + BALL_R
            ball.vy = abs(ball.vy)

    def _break_brick(self, brick: Brick, ball: Ball) -> None:
        """Damage or destroy a brick."""
        brick.hp -= 1
        brick.flashing = 4

        if brick.hp <= 0:
            # Remove brick
            self.bricks.remove(brick)

            # Score
            base_points = 10 if ball.super_mode else 10 + self.combo * 5
            self.score += base_points

            # Combo
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo

            # Particles
            pcolor = ELEMENT_COLORS[brick.color_idx]
            for _ in range(6):
                self.particles.append(Particle(
                    x=brick.x + brick.w / 2, y=brick.y + brick.h / 2,
                    vx=random.uniform(-2, 2),
                    vy=random.uniform(-2, 2),
                    life=15, color=pcolor,
                ))

            # Floating score
            if self.combo >= 3:
                self._add_float_text(
                    brick.x + brick.w / 2, brick.y,
                    f"x{self.combo}", C_ORANGE,
                )

            # Power-up drop chance
            if random.random() < 0.15:
                kind = random.choice(["WIDE", "SLOW", "LIFE", "MULTI"])
                self.power_ups.append(PowerUp(
                    x=brick.x + brick.w / 2,
                    y=brick.y + brick.h,
                    kind=kind,
                ))
        else:
            # Brick damaged but not destroyed
            for _ in range(3):
                self.particles.append(Particle(
                    x=ball.x, y=ball.y,
                    vx=random.uniform(-1, 1),
                    vy=random.uniform(-1, 1),
                    life=8, color=C_WHITE,
                ))

        # Super ball doesn't reset combo or bounce — it pierces through
        if not ball.super_mode:
            self._deflect_ball(ball, brick)

    def _update_paddle(self) -> None:
        """Move paddle with mouse or keyboard."""
        # Mouse control
        if pyxel.mouse_x > 0 or pyxel.mouse_y > 0:
            self.paddle_x = pyxel.mouse_x - self.paddle_w / 2
        else:
            # Keyboard fallback
            speed = 4.0
            if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
                self.paddle_x -= speed
            if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
                self.paddle_x += speed

        # Clamp paddle
        self.paddle_x = max(0.0, min(float(SCREEN_W) - self.paddle_w, self.paddle_x))

        # WIDE timer
        if self.paddle_timer > 0:
            self.paddle_timer -= 1
            if self.paddle_timer == 0:
                self.paddle_w = float(PADDLE_W)
                self.paddle_x = max(0.0, min(float(SCREEN_W) - self.paddle_w, self.paddle_x))

    def _update_color_switch(self) -> None:
        """Handle color switching input."""
        changed = False

        if pyxel.btnp(pyxel.KEY_Q):
            self.paddle_color = (self.paddle_color - 1) % 4
            changed = True
        elif pyxel.btnp(pyxel.KEY_E):
            self.paddle_color = (self.paddle_color + 1) % 4
            changed = True
        elif pyxel.btnp(pyxel.KEY_1):
            self.paddle_color = 0
            changed = True
        elif pyxel.btnp(pyxel.KEY_2):
            self.paddle_color = 1
            changed = True
        elif pyxel.btnp(pyxel.KEY_3):
            self.paddle_color = 2
            changed = True
        elif pyxel.btnp(pyxel.KEY_4):
            self.paddle_color = 3
            changed = True

        # Scroll wheel
        mw = pyxel.mouse_wheel
        if mw > 0:
            self.paddle_color = (self.paddle_color + 1) % 4
            changed = True
        elif mw < 0:
            self.paddle_color = (self.paddle_color - 1) % 4
            changed = True

        if changed and self.combo > 0:
            self._add_float_text(
                self.paddle_x + self.paddle_w / 2, PADDLE_Y - 10,
                "SWITCH", C_GRAY,
            )
            self.combo = 0

    def _update_power_ups(self) -> None:
        """Move power-ups and check paddle collection."""
        for pu in self.power_ups[:]:
            pu.y += pu.vy
            pu.life -= 1

            # Check paddle collection
            if (pu.y + 4 >= PADDLE_Y and pu.y - 4 <= PADDLE_Y + PADDLE_H and
                    pu.x + 4 >= self.paddle_x and pu.x - 4 <= self.paddle_x + self.paddle_w):
                self._apply_power_up(pu)
                self.power_ups.remove(pu)
            elif pu.y > SCREEN_H or pu.life <= 0:
                self.power_ups.remove(pu)

    def _apply_power_up(self, pu: PowerUp) -> None:
        """Apply a collected power-up effect."""
        if pu.kind == "WIDE":
            self.paddle_w = float(PADDLE_W) * 1.6
            self.paddle_timer = 600  # 10 seconds
            self._add_float_text(pu.x, pu.y, "WIDE", C_CYAN)
        elif pu.kind == "SLOW":
            self._ball_speed_base *= 0.7
            # Apply to all balls
            for ball in self.balls:
                speed = math.hypot(ball.vx, ball.vy)
                if speed > 0:
                    ratio = self._ball_speed_base / speed
                    ball.vx *= ratio
                    ball.vy *= ratio
            self._add_float_text(pu.x, pu.y, "SLOW", C_BLUE)
        elif pu.kind == "LIFE":
            self.lives += 1
            self._add_float_text(pu.x, pu.y, "+1 LIFE", C_GREEN)
        elif pu.kind == "MULTI":
            # Spawn 2 extra balls from current ball positions
            new_balls: list[Ball] = []
            for ball in self.balls:
                angle1 = random.uniform(0, math.pi * 2)
                angle2 = random.uniform(0, math.pi * 2)
                speed = self._ball_speed_base
                new_balls.append(Ball(
                    x=ball.x, y=ball.y,
                    vx=speed * math.cos(angle1),
                    vy=speed * math.sin(angle1),
                    color_idx=ball.color_idx,
                ))
                new_balls.append(Ball(
                    x=ball.x, y=ball.y,
                    vx=speed * math.cos(angle2),
                    vy=speed * math.sin(angle2),
                    color_idx=ball.color_idx,
                ))
            self.balls.extend(new_balls)
            self._add_float_text(pu.x, pu.y, "MULTI!", C_ORANGE)

        # Particles for collection
        for _ in range(8):
            self.particles.append(Particle(
                x=pu.x, y=pu.y,
                vx=random.uniform(-2, 2),
                vy=random.uniform(-2, 2),
                life=12, color=C_WHITE,
            ))

    def _update_ball_lost(self) -> None:
        """Brief pause after losing a ball."""
        self._ball_lost_timer -= 1
        if self._ball_lost_timer <= 0:
            if self.lives <= 0:
                self.phase = Phase.GAME_OVER
            else:
                self._reset_ball()

    def _update_super(self) -> None:
        """Super ball in flight — continues physics but with piercing."""
        balls_to_remove: list[int] = []
        for i, ball in enumerate(self.balls):
            if not self._update_ball_physics(ball):
                balls_to_remove.append(i)

        for i in reversed(balls_to_remove):
            del self.balls[i]

        # End super mode when ball hits paddle again (handled in _check_paddle_collision)
        # or when all super balls are gone
        if not any(b.super_mode for b in self.balls):
            self.combo = 0
            if self.balls:
                self.phase = Phase.PLAY
            elif self.lives > 0:
                self._reset_ball()
            else:
                self.phase = Phase.GAME_OVER

    def _on_ball_lost(self) -> None:
        """Called when a ball falls off screen."""
        self.lives -= 1
        self.combo = 0
        self._ball_lost_timer = 45
        self.phase = Phase.BALL_LOST
        self.screen_shake = 6
        self._add_float_text(SCREEN_W / 2, SCREEN_H / 2, "MISS!", C_RED)

    def _update_wave_clear(self) -> None:
        """Brief celebration between waves."""
        self._wave_clear_timer -= 1
        if self._wave_clear_timer <= 0:
            self.wave += 1
            if self.wave >= len(WAVE_DEFS):
                # Victory! Loop with harder waves
                self.wave = len(WAVE_DEFS) - 1
                self._spawn_wave()
                self._add_float_text(SCREEN_W / 2, SCREEN_H / 2, "MAX WAVE!", C_YELLOW)
            else:
                self._spawn_wave()
                self._add_float_text(SCREEN_W / 2, SCREEN_H / 2, f"WAVE {self.wave + 1}", C_WHITE)

    # ── Particles & float text ────────────────────────────────────────────

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.15  # gravity
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_float_texts(self) -> None:
        for ft in self.float_texts[:]:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life <= 0:
                self.float_texts.remove(ft)

    def _add_float_text(self, x: float, y: float, text: str, color: int) -> None:
        self.float_texts.append(FloatingText(x=x, y=y, text=text, life=30, color=color))

    # ── Draw ──────────────────────────────────────────────────────────────

    def draw(self) -> None:
        """Main draw called by pyxel each frame."""
        pyxel.cls(C_BLACK)

        # Screen shake offset
        shake_x = 0
        shake_y = 0
        if self.screen_shake > 0:
            shake_x = random.randint(-2, 2)
            shake_y = random.randint(-2, 2)

        # Background grid
        for gx in range(0, SCREEN_W, 32):
            for gy in range(0, SCREEN_H, 32):
                pyxel.pset(gx + shake_x, gy + shake_y, 1)

        # Bricks
        for brick in self.bricks:
            bx = int(brick.x) + shake_x
            by = int(brick.y) + shake_y
            bw = int(brick.w)
            bh = int(brick.h)
            color = C_WHITE if brick.flashing > 0 else ELEMENT_COLORS[brick.color_idx]
            pyxel.rect(bx, by, bw, bh, color)

            # 2 HP bricks have a dot
            if brick.hp == 2:
                pyxel.rect(bx + bw // 2 - 2, by + bh // 2 - 2, 4, 4, C_BLACK)

            if brick.flashing > 0:
                brick.flashing -= 1

        # Power-ups
        for pu in self.power_ups:
            px = int(pu.x) + shake_x
            py = int(pu.y) + shake_y
            if pu.kind == "WIDE":
                pyxel.rect(px - 3, py - 3, 6, 6, C_CYAN)
            elif pu.kind == "SLOW":
                pyxel.circ(px, py, 3, C_BLUE)
            elif pu.kind == "LIFE":
                pyxel.rect(px - 2, py - 3, 4, 6, C_GREEN)
            elif pu.kind == "MULTI":
                pyxel.circb(px, py, 3, C_ORANGE)
                pyxel.circb(px, py, 1, C_ORANGE)

        # Paddle
        px = int(self.paddle_x) + shake_x
        py = PADDLE_Y + shake_y
        pw = int(self.paddle_w)
        pyxel.rect(px, py, pw, PADDLE_H, ELEMENT_COLORS[self.paddle_color])
        # Paddle highlight
        pyxel.rect(px + 2, py + 1, pw - 4, 2, C_WHITE)

        # Balls
        for ball in self.balls:
            bx = int(ball.x) + shake_x
            by = int(ball.y) + shake_y
            bcolor = C_WHITE if ball.super_mode else ELEMENT_COLORS[ball.color_idx]
            if ball.super_mode:
                # Glow effect for super ball
                pyxel.circ(bx, by, BALL_R + 2, C_YELLOW)
                pyxel.circ(bx, by, BALL_R, C_WHITE)
            else:
                pyxel.circ(bx, by, BALL_R, bcolor)
                pyxel.circ(bx, by, BALL_R - 1, C_WHITE)

        # Particles
        for p in self.particles:
            alpha = p.life / 15.0
            c = p.color if alpha > 0.5 else C_GRAY
            pyxel.pset(int(p.x) + shake_x, int(p.y) + shake_y, c)

        # Floating text
        for ft in self.float_texts:
            alpha = ft.life / 30.0
            c = ft.color if alpha > 0.5 else C_GRAY
            tw = len(ft.text) * 4
            pyxel.text(
                int(ft.x) - tw // 2 + shake_x,
                int(ft.y) + shake_y,
                ft.text, c,
            )

        # ── HUD ──
        # Color indicators at top
        for i in range(4):
            ix = 4 + i * 28
            iy = 2
            pyxel.rect(ix, iy, 22, 10, ELEMENT_COLORS[i])
            if i == self.paddle_color:
                pyxel.rectb(ix - 1, iy - 1, 24, 12, C_WHITE)
            pyxel.text(ix + 5, iy + 2, ELEMENT_LABELS[i], C_BLACK if i != 2 else C_WHITE)

        # Score
        pyxel.text(SCREEN_W - 52, 3, f"SC:{self.score:05d}", C_WHITE)

        # Lives
        for i in range(self.lives):
            lx = SCREEN_W - 12 - i * 10
            pyxel.rect(lx, SCREEN_H - 10, 6, 6, C_RED)

        # Combo meter
        combo_pct = min(self.combo / COMBO_THRESHOLD, 1.0)
        combo_bar_w = 80
        combo_x = SCREEN_W // 2 - combo_bar_w // 2
        combo_y = SCREEN_H - 14
        pyxel.rectb(combo_x - 1, combo_y - 1, combo_bar_w + 2, 8, C_GRAY)
        if combo_pct > 0:
            bar_color = C_ORANGE if combo_pct >= 1.0 else ELEMENT_COLORS[self.paddle_color]
            bar_w = int(combo_bar_w * combo_pct)
            pyxel.rect(combo_x, combo_y, bar_w, 6, bar_color)
        pyxel.text(combo_x + combo_bar_w // 2 - 24, combo_y - 1, f"COMBO:{self.combo}", C_WHITE)

        # Wave info
        wave_text = f"WAVE {self.wave + 1}"
        pyxel.text(SCREEN_W // 2 - len(wave_text) * 2, SCREEN_H - 26, wave_text, C_GRAY)

        # Phase-specific overlays
        if self.phase == Phase.AIM:
            aim_text = "AIM & CLICK"
            pyxel.text(SCREEN_W // 2 - len(aim_text) * 2, PADDLE_Y - 20, aim_text, C_WHITE)
            # Draw aim line
            ball = self.balls[0]
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            if my < ball.y:
                dx = mx - ball.x
                dy = my - ball.y
                dist = math.hypot(dx, dy)
                if dist > 0:
                    for t in range(0, min(int(dist), 100), 4):
                        lx = ball.x + dx / dist * t
                        ly = ball.y + dy / dist * t
                        pyxel.pset(int(lx), int(ly), C_GRAY)

        elif self.phase == Phase.BALL_LOST:
            pyxel.text(SCREEN_W // 2 - 20, SCREEN_H // 2 - 10, "MISS!", C_RED)
            pyxel.text(SCREEN_W // 2 - 32, SCREEN_H // 2 + 2, f"LIVES: {self.lives}", C_WHITE)

        elif self.phase == Phase.WAVE_CLEAR:
            pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 - 10, "WAVE CLEAR!", C_GREEN)
            pyxel.text(SCREEN_W // 2 - 40, SCREEN_H // 2 + 2, f"+{500 * (self.wave + 1)} BONUS", C_YELLOW)

        elif self.phase == Phase.GAME_OVER:
            pyxel.rect(SCREEN_W // 2 - 70, SCREEN_H // 2 - 30, 140, 60, C_BLACK)
            pyxel.rectb(SCREEN_W // 2 - 70, SCREEN_H // 2 - 30, 140, 60, C_RED)
            pyxel.text(SCREEN_W // 2 - 24, SCREEN_H // 2 - 22, "GAME OVER", C_RED)
            pyxel.text(SCREEN_W // 2 - 44, SCREEN_H // 2 - 8, f"SCORE: {self.score:05d}", C_WHITE)
            pyxel.text(SCREEN_W // 2 - 48, SCREEN_H // 2 + 6, f"MAX COMBO: {self.max_combo}", C_ORANGE)
            pyxel.text(SCREEN_W // 2 - 52, SCREEN_H // 2 + 20, "CLICK TO RETRY", C_GRAY)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    Game()
