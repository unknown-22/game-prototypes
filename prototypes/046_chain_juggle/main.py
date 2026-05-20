"""CHAIN JUGGLE — Color-match keep-up juggling game.

Reinterpreted from game_idea_factory #1 (Score 31.25, alchemy deckbuilder):
  - "Synthesis compression" -> same-color COMBO compresses all same-color balls into SUPER BALL
  - "Damage strengthens enemies"  -> each same-color hit speeds up the ball (risk/reward)
  - Missed balls grow a rising hazard zone from below

Core fun: Chaining same-color juggles to compress into a super ball, while managing
increasingly fast balls and a rising hazard floor.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import ClassVar

import pyxel

# ── Constants ──
SCREEN_W = 240
SCREEN_H = 300
DISPLAY_SCALE = 2
FPS = 30
GRAVITY: float = 0.25
PLAYER_Y: int = 268
PLAYER_W: int = 40
PLAYER_H: int = 6
PLAYER_SPEED: float = 3.0
BALL_RADIUS: int = 7
SUPER_RADIUS: int = 12
BALL_SPAWN_INTERVAL: int = 150  # frames (~5s at 30fps)
MAX_BALLS: int = 5
HAZARD_START_Y: float = float(SCREEN_H + 40)  # off-screen
HAZARD_RISE: float = 10.0  # px per miss
COMBO_THRESHOLD: int = 4  # hits to trigger compression
SUPER_DURATION: int = 90  # frames (3 seconds)
SPEED_INCREASE: float = 0.12  # per same-color hit
SPEED_CLAMP: float = 3.5
PARTICLE_LIFE: int = 15

COLOR_NAMES: tuple[str, ...] = ("RED", "LIME", "CYAN", "YELW")
# pyxel color index -> actual pyxel color constant
COLORS: tuple[int, ...] = (
    pyxel.COLOR_RED,    # 0: red
    pyxel.COLOR_LIME,   # 1: lime (green)
    pyxel.COLOR_CYAN,   # 2: cyan (blue)
    pyxel.COLOR_YELLOW, # 3: yellow
)
N_COLORS: int = len(COLORS)


# ── Data Classes ──

@dataclass
class Ball:
    """A juggling ball with physics and color state."""
    x: float
    y: float
    vx: float
    vy: float
    color: int          # index into COLORS (0-3)
    speed_mult: float = 1.0
    is_super: bool = False
    super_timer: int = 0

    def radius(self) -> int:
        return SUPER_RADIUS if self.is_super else BALL_RADIUS


@dataclass
class Particle:
    """Visual particle for hit/miss effects."""
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


# ── Game Class ──

class ChainJuggle:
    """Color-match juggling game.

    Public API::
        g = ChainJuggle()
        g.reset()   # reset all state
        g.update()  # one frame tick (calls internal step methods)
        g.draw()    # render frame

    For headless testing, bypass pyxel.init via Game.__new__ pattern.
    """

    # Class-level defaults for test pre-init
    _PLAYER_SPEED: ClassVar[float] = PLAYER_SPEED
    _GRAVITY: ClassVar[float] = GRAVITY
    _HAZARD_RISE: ClassVar[float] = HAZARD_RISE
    _SPEED_INCREASE: ClassVar[float] = SPEED_INCREASE
    _COMBO_THRESHOLD: ClassVar[int] = COMBO_THRESHOLD
    _MAX_BALLS: ClassVar[int] = MAX_BALLS

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CHAIN JUGGLE",
                   fps=FPS, display_scale=DISPLAY_SCALE)
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        """Reset all game state for a new round."""
        self.player_x: float = SCREEN_W / 2.0
        self.balls: list[Ball] = []
        self.particles: list[Particle] = []
        self.combo: int = 0
        self.active_color: int = -1  # -1 = no active combo
        self.score: int = 0
        self.max_combo: int = 0
        self.hazard_y: float = HAZARD_START_Y
        self.game_over: bool = False
        self._spawn_timer: int = 0
        self._shake_frames: int = 0
        self.balls_juggled: int = 0
        self._frame: int = 0
        # Spawn initial balls
        self._spawn_ball()
        self._spawn_ball()

    # ── Spawning ──

    def _spawn_ball(self) -> None:
        """Spawn a new ball with random color and slight horizontal velocity."""
        if len(self.balls) >= MAX_BALLS:
            return
        color = self._rng.randint(0, N_COLORS - 1)
        x = self._rng.uniform(BALL_RADIUS + 15, SCREEN_W - BALL_RADIUS - 15)
        ball = Ball(
            x=x, y=float(self._rng.randint(20, 50)),
            vx=self._rng.uniform(-0.8, 0.8),
            vy=0.0,
            color=color,
        )
        self.balls.append(ball)

    def _spawn_particles(self, x: float, y: float, color: int,
                         count: int = 6) -> None:
        """Burst particles at a position."""
        for _ in range(count):
            angle = self._rng.uniform(0.0, math.pi * 2.0)
            speed = self._rng.uniform(1.0, 3.5)
            p = Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=PARTICLE_LIFE,
                color=color,
            )
            self.particles.append(p)

    # ── Compression ──

    def _compress(self, color: int) -> int:
        """Compress all same-color non-super balls into one super ball.

        Returns the number of balls compressed (0 if none).
        """
        same_color = [b for b in self.balls
                      if b.color == color and not b.is_super]
        if not same_color:
            return 0

        count = len(same_color)
        avg_x = sum(b.x for b in same_color) / count
        avg_y = sum(b.y for b in same_color) / count

        # Remove regular same-color balls
        self.balls = [b for b in self.balls
                      if b.color != color or b.is_super]

        # Create super ball with upward kick
        super_ball = Ball(
            x=avg_x, y=avg_y,
            vx=self._rng.uniform(-0.5, 0.5),
            vy=-4.0,
            color=color,
            is_super=True,
            super_timer=SUPER_DURATION,
        )
        self.balls.append(super_ball)
        self._shake_frames = 10
        return count

    # ── Physics ──

    def _apply_physics(self, ball: Ball) -> None:
        """Apply gravity and speed multiplier to a ball."""
        ball.vy += GRAVITY
        spd = ball.speed_mult
        ball.x += ball.vx * spd
        ball.y += ball.vy * spd

    def _clamp_speed(self, ball: Ball) -> None:
        """Clamp ball velocity magnitudes."""
        spd = ball.speed_mult
        vx = ball.vx * spd
        vy = ball.vy * spd
        if abs(vx) > SPEED_CLAMP:
            ball.vx = SPEED_CLAMP * (1.0 if vx > 0 else -1.0) / spd
        if abs(vy) > SPEED_CLAMP:
            ball.vy = SPEED_CLAMP * (1.0 if vy > 0 else -1.0) / spd

    def _check_walls(self, ball: Ball) -> None:
        """Bounce ball off screen walls and ceiling."""
        r = ball.radius()
        if ball.x - r < 0:
            ball.x = float(r)
            ball.vx = abs(ball.vx)
        elif ball.x + r > SCREEN_W:
            ball.x = float(SCREEN_W - r)
            ball.vx = -abs(ball.vx)
        if ball.y - r < 0:
            ball.y = float(r)
            ball.vy = abs(ball.vy)

    def _check_paddle(self, ball: Ball) -> bool:
        """Check paddle collision. Returns True if a hit occurred."""
        r = ball.radius()
        half_w = PLAYER_W / 2.0
        paddle_top = float(PLAYER_Y - PLAYER_H)

        if not (ball.y + r >= paddle_top and ball.y - r <= float(PLAYER_Y)):
            return False
        if not (ball.x + r >= self.player_x - half_w and
                ball.x - r <= self.player_x + half_w):
            return False

        # Hit! Bounce upward.
        ball.y = paddle_top - float(r)
        ball.vy = -abs(ball.vy)

        # Horizontal deflection based on hit position
        hit_offset = (ball.x - self.player_x) / half_w
        ball.vx += hit_offset * 1.8

        self._clamp_speed(ball)

        # ── Combo logic ──
        if self.active_color == ball.color:
            # Same color: continue combo
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            # Speed up (risk!)
            ball.speed_mult += SPEED_INCREASE
            # Score
            points = 10 * self.combo
            if ball.is_super:
                points *= 3
            self.score += points
            # Check compression
            if self.combo >= COMBO_THRESHOLD and not ball.is_super:
                self._compress(ball.color)
        else:
            # Different color: start new combo
            self.active_color = ball.color
            self.combo = 1
            points = 10
            if ball.is_super:
                points = 30
            self.score += points

        self.balls_juggled += 1
        return True

    # ── Update ──

    def update(self) -> None:
        """Frame update: input, physics, spawning, game-over check."""
        if self.game_over:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        self._frame += 1

        # ── Input ──
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            self.player_x -= PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            self.player_x += PLAYER_SPEED
        half_w = PLAYER_W / 2.0
        self.player_x = max(half_w, min(float(SCREEN_W) - half_w, self.player_x))

        # ── Spawning ──
        self._spawn_timer += 1
        if self._spawn_timer >= BALL_SPAWN_INTERVAL:
            self._spawn_timer = 0
            if len(self.balls) < MAX_BALLS:
                self._spawn_ball()

        # ── Physics ──
        for b in self.balls:
            self._apply_physics(b)
        for b in self.balls:
            self._check_walls(b)
        for b in self.balls:
            if self._check_paddle(b):
                self._spawn_particles(b.x, b.y, COLORS[b.color], 4)

        # ── Super timer decay ──
        for b in self.balls:
            if b.is_super:
                b.super_timer -= 1
                if b.super_timer <= 0:
                    b.is_super = False

        # ── Missed balls ──
        missed = [b for b in self.balls
                  if b.y - b.radius() > float(SCREEN_H)]
        for b in missed:
            self.balls.remove(b)
            self.hazard_y -= HAZARD_RISE
            self.combo = 0
            self.active_color = -1
            self._spawn_particles(b.x, float(SCREEN_H), pyxel.COLOR_RED, 6)

        # ── Particles ──
        self._update_particles()

        # ── Shake decay ──
        if self._shake_frames > 0:
            self._shake_frames -= 1

        # ── Game over ──
        if self.hazard_y <= float(PLAYER_Y + PLAYER_H):
            self.game_over = True
        if len(self.balls) > MAX_BALLS:
            self.game_over = True

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.08
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    # ── Draw ──

    def draw(self) -> None:
        """Render the current frame."""
        pyxel.cls(pyxel.COLOR_BLACK)

        # Screen shake offset
        sx = self._rng.randint(-3, 3) if self._shake_frames > 0 else 0
        sy = self._rng.randint(-2, 2) if self._shake_frames > 0 else 0

        # ── Hazard zone (rising lava) ──
        ht = int(self.hazard_y)
        for y in range(max(0, ht), SCREEN_H):
            t = (y - ht) / max(1.0, float(SCREEN_H - ht))
            if t < 0.25:
                col = pyxel.COLOR_BROWN
            elif t < 0.5:
                col = pyxel.COLOR_RED
            elif t < 0.75:
                col = pyxel.COLOR_ORANGE
            else:
                col = pyxel.COLOR_YELLOW
            pyxel.line(0, y + sy, SCREEN_W, y + sy, col)

        # Hazard rim glow
        if ht < SCREEN_H and ht >= 0:
            pyxel.line(0, ht + sy, SCREEN_W, ht + sy, pyxel.COLOR_WHITE)

        # ── Player paddle ──
        px = int(self.player_x + sx)
        py = PLAYER_Y + PLAYER_H + sy
        half_w = PLAYER_W // 2
        pad_col = COLORS[self.active_color] if self.active_color >= 0 else pyxel.COLOR_WHITE
        pyxel.rect(px - half_w, py - PLAYER_H, PLAYER_W, PLAYER_H, pad_col)
        # Paddle highlight
        pyxel.rect(px - half_w + 3, py - PLAYER_H + 1, PLAYER_W - 6, 2,
                   pyxel.COLOR_WHITE)

        # ── Balls ──
        for b in self.balls:
            bx = int(b.x + sx)
            by = int(b.y + sy)
            r = b.radius()
            col = COLORS[b.color]

            if b.is_super:
                pulse = math.sin(self._frame * 0.3) * 2.0
                pr = r + int(pulse)
                pyxel.circb(bx, by, pr + 1, pyxel.COLOR_WHITE)
                pyxel.circ(bx, by, pr, col)
                pyxel.circ(bx - 2, by - 2, max(1, pr // 3), pyxel.COLOR_WHITE)
            else:
                pyxel.circb(bx, by, r, pyxel.COLOR_WHITE)
                pyxel.circ(bx, by, r - 1, col)
                pyxel.circ(bx - 2, by - 2, 2, pyxel.COLOR_WHITE)

        # ── Particles ──
        for p in self.particles:
            alpha = p.life / float(PARTICLE_LIFE)
            sz = max(1, int(3.0 * alpha))
            pyxel.circ(int(p.x + sx), int(p.y + sy), sz, p.color)

        # ── HUD ──
        pyxel.text(4, 3, f"CMB:{self.combo}", pyxel.COLOR_WHITE)
        if self.active_color >= 0:
            pyxel.text(4, 12, COLOR_NAMES[self.active_color],
                       COLORS[self.active_color])

        pyxel.text(SCREEN_W - 56, 3, f"SC:{self.score}",
                   pyxel.COLOR_YELLOW)
        ball_warn = pyxel.COLOR_RED if len(self.balls) >= 4 else pyxel.COLOR_WHITE
        pyxel.text(SCREEN_W - 40, 12, f"x{len(self.balls)}", ball_warn)
        pyxel.text(4, SCREEN_H - 10, f"MAX:{self.max_combo}", pyxel.COLOR_GRAY)

        # ── Game over overlay ──
        if self.game_over:
            self._draw_game_over(sx, sy)

    def _draw_game_over(self, sx: int, sy: int) -> None:
        """Draw game-over screen overlay."""
        # Dim background
        for y in range(0, SCREEN_H, 3):
            pyxel.rect(0 + sx, y + sy, SCREEN_W, 2, pyxel.COLOR_BLACK)

        cx = SCREEN_W // 2
        cy = SCREEN_H // 2

        pyxel.text(cx - 28, cy - 24, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(cx - 28, cy - 4, f"SCORE: {self.score}",
                   pyxel.COLOR_WHITE)
        pyxel.text(cx - 28, cy + 10, f"MAX COMBO: {self.max_combo}",
                   pyxel.COLOR_YELLOW)
        pyxel.text(cx - 28, cy + 24, f"JUGGLES: {self.balls_juggled}",
                   pyxel.COLOR_GRAY)
        pyxel.text(cx - 52, cy + 42, "SPACE / ENTER TO RETRY",
                   pyxel.COLOR_WHITE)


if __name__ == "__main__":
    ChainJuggle()
