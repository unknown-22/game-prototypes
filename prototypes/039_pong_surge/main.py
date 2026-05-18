"""PONG SURGE — Color-match Pong rally prototype.
Reinterpreted from deckbuilder idea #1 (score 32.6):
  - "log/replay as asset" → rally history builds COMBO
  - "chain collapse/expansion/compression" → SURGE mode with visual effects

Core fun moment: rallying same-color hits to build COMBO, then triggering
SURGE mode for double points and screen-shaking chain effects.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

if not TYPE_CHECKING:
    import pyxel


# ── Config ──
SCREEN_W = 256
SCREEN_H = 192
DISPLAY_SCALE = 3
FPS = 60

PADDLE_W = 6
PADDLE_H = 40
PADDLE_X_PLAYER = 16
PADDLE_X_AI = SCREEN_W - 16
PADDLE_SPEED = 3.0
AI_SPEED = 2.0

BALL_RADIUS = 3
BALL_SPEED_INIT = 2.5
BALL_SPEED_MAX = 6.0
BALL_SPEED_INCREMENT = 0.2

COMBO_SURGE_THRESHOLD = 5
SURGE_DURATION = 180  # frames
SURGE_SCORE_MULT = 3

NUM_COLORS = 4
# (name, pyxel color index)
COLOR_DEFS: tuple[tuple[str, int], ...] = (
    ("RED", 8),       # pyxel.COLOR_RED
    ("GREEN", 11),    # pyxel.COLOR_GREEN
    ("YELLOW", 10),   # pyxel.COLOR_YELLOW
    ("CYAN", 13),     # pyxel.COLOR_CYAN
)

# Scoring: passing the AI nets bonus points
SCORE_PASS_AI = 10
SCORE_HIT_BASE = 1


# ── Data Classes ──
@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    color: int  # 0..NUM_COLORS-1
    speed: float = BALL_SPEED_INIT

    def color_val(self) -> int:
        return COLOR_DEFS[self.color][1]


@dataclass
class Paddle:
    x: float
    y: float
    w: int = PADDLE_W
    h: int = PADDLE_H
    color: int = 0

    def color_val(self) -> int:
        return COLOR_DEFS[self.color][1]

    @property
    def left(self) -> float:
        return self.x - self.w / 2

    @property
    def right(self) -> float:
        return self.x + self.w / 2

    @property
    def top(self) -> float:
        return self.y - self.h / 2

    @property
    def bottom(self) -> float:
        return self.y + self.h / 2


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int
    max_life: int = 20


# ── Game ──
class Game:
    """PONG SURGE — Color-match Pong rally."""

    def __init__(self) -> None:
        pyxel.init(
            SCREEN_W, SCREEN_H,
            title="PONG SURGE",
            fps=FPS,
            display_scale=DISPLAY_SCALE,
        )
        self._rng: random.Random = random.Random()
        self.player: Paddle = Paddle(x=PADDLE_X_PLAYER, y=SCREEN_H / 2)
        self.ai: Paddle = Paddle(x=PADDLE_X_AI, y=SCREEN_H / 2)
        self.ball: Ball = Ball(x=0, y=0, vx=0, vy=0, color=0)
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.rally_count: int = 0
        self.surge_timer: int = 0
        self.particles: list[Particle] = []
        self._ai_color_timer: int = 0
        self._shake_frames: int = 0
        self.game_over: bool = False
        self.reset()

    def reset(self) -> None:
        self._rng = random.Random()
        self.player = Paddle(x=PADDLE_X_PLAYER, y=SCREEN_H / 2, color=0)
        self.ai = Paddle(x=PADDLE_X_AI, y=SCREEN_H / 2, color=1)
        self._reset_ball(serve_direction=1)
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.rally_count = 0
        self.surge_timer = 0
        self.particles.clear()
        self._ai_color_timer = 0
        self._shake_frames = 0
        self.game_over = False

    def _reset_ball(self, serve_direction: int = 1) -> None:
        """Reset ball to center, serving toward *serve_direction* (+1=right, -1=left)."""
        color = self._rng.randint(0, NUM_COLORS - 1)
        angle = self._rng.uniform(-0.6, 0.6)
        vx = math.cos(angle) * BALL_SPEED_INIT * serve_direction
        vy = math.sin(angle) * BALL_SPEED_INIT
        self.ball = Ball(
            x=SCREEN_W / 2, y=SCREEN_H / 2,
            vx=vx, vy=vy,
            color=color,
            speed=BALL_SPEED_INIT,
        )

    # ── Update ──
    def update(self) -> None:
        if self.game_over:
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
            return

        self._update_input()
        self._update_ai()
        self._update_ball()
        self._update_particles()
        self._update_surge()

    def _update_input(self) -> None:
        p = self.player
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            p.y -= PADDLE_SPEED
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            p.y += PADDLE_SPEED
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_E):
            p.color = (p.color + 1) % NUM_COLORS

        # Clamp to screen
        half_h = PADDLE_H / 2
        p.y = max(half_h, min(SCREEN_H - half_h, p.y))

    def _update_ai(self) -> None:
        a = self.ai
        b = self.ball

        # Move toward ball's y-position (with some lag)
        target_y = b.y
        if b.vx < 0:
            # Ball moving away from AI — return to center slowly
            target_y = SCREEN_H / 2
        if a.y < target_y:
            a.y += AI_SPEED
        elif a.y > target_y:
            a.y -= AI_SPEED

        half_h = PADDLE_H / 2
        a.y = max(half_h, min(SCREEN_H - half_h, a.y))

        # Cycle color periodically, biased toward matching ball
        self._ai_color_timer += 1
        if self._ai_color_timer >= 75:
            self._ai_color_timer = 0
            # 60% chance to match ball color, 40% random
            if self._rng.random() < 0.6:
                a.color = b.color
            else:
                a.color = self._rng.randint(0, NUM_COLORS - 1)

    def _update_ball(self) -> None:
        b = self.ball
        b.x += b.vx
        b.y += b.vy

        # Wall bounces (top/bottom)
        if b.y - BALL_RADIUS <= 0:
            b.y = BALL_RADIUS
            b.vy = abs(b.vy)
        elif b.y + BALL_RADIUS >= SCREEN_H:
            b.y = SCREEN_H - BALL_RADIUS
            b.vy = -abs(b.vy)

        # Right wall: AI miss → player scores
        if b.x + BALL_RADIUS >= SCREEN_W:
            self.score += SCORE_PASS_AI
            self._spawn_score_particles()
            self._reset_ball(serve_direction=-1)
            return

        # Left wall: player miss → game over
        if b.x - BALL_RADIUS <= 0:
            self.game_over = True
            return

        # Paddle collisions
        self._check_paddle_collision(self.ai, is_ai=True)
        self._check_paddle_collision(self.player, is_ai=False)

    def _check_paddle_collision(self, paddle: Paddle, *, is_ai: bool) -> None:
        b = self.ball

        # Ball must be moving toward paddle
        if is_ai and b.vx < 0:
            return  # ball moving left, away from AI
        if not is_ai and b.vx > 0:
            return  # ball moving right, away from player

        # AABB intersection
        if not (
            b.x + BALL_RADIUS >= paddle.left
            and b.x - BALL_RADIUS <= paddle.right
            and b.y + BALL_RADIUS >= paddle.top
            and b.y - BALL_RADIUS <= paddle.bottom
        ):
            return

        # Reposition ball at paddle edge
        if is_ai:
            b.x = paddle.left - BALL_RADIUS
            b.vx = -abs(b.vx)
        else:
            b.x = paddle.right + BALL_RADIUS
            b.vx = abs(b.vx)

        # Vertical influence from paddle position
        hit_offset = (b.y - paddle.y) / (paddle.h / 2)  # -1..1
        b.vy += hit_offset * 2.0

        # Color match
        if b.color == paddle.color:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            b.speed = min(BALL_SPEED_MAX, b.speed + BALL_SPEED_INCREMENT)
            self._spawn_hit_particles(paddle)
        else:
            self.combo = 0
            b.speed = BALL_SPEED_INIT

        # Normalize velocity to current speed
        current_speed = math.hypot(b.vx, b.vy)
        if current_speed > 0:
            scale = b.speed / current_speed
            b.vx *= scale
            b.vy *= scale

        self.rally_count += 1
        combo_mult = SURGE_SCORE_MULT if self.surge_timer > 0 else 1
        self.score += SCORE_HIT_BASE + self.combo * combo_mult

        # Ball changes color on AI hit (adds unpredictability)
        if is_ai:
            b.color = self._rng.randint(0, NUM_COLORS - 1)

        # SURGE activation
        if self.combo >= COMBO_SURGE_THRESHOLD and self.surge_timer == 0:
            self.surge_timer = SURGE_DURATION
            self._shake_frames = 15
            self._spawn_surge_particles()

    def _update_particles(self) -> None:
        survivors: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                survivors.append(p)
        self.particles = survivors

    def _update_surge(self) -> None:
        if self.surge_timer > 0:
            self.surge_timer -= 1
        if self._shake_frames > 0:
            self._shake_frames -= 1

    # ── Particle Spawners ──
    def _spawn_hit_particles(self, paddle: Paddle) -> None:
        for _ in range(5):
            self.particles.append(Particle(
                x=self.ball.x, y=self.ball.y,
                vx=self._rng.uniform(-1.5, 1.5),
                vy=self._rng.uniform(-1.5, 1.5),
                color=self.ball.color,
                life=12,
                max_life=12,
            ))

    def _spawn_surge_particles(self) -> None:
        for _ in range(25):
            angle = self._rng.uniform(0, math.pi * 2)
            spd = self._rng.uniform(1.5, 5)
            self.particles.append(Particle(
                x=self.ball.x, y=self.ball.y,
                vx=math.cos(angle) * spd,
                vy=math.sin(angle) * spd,
                color=self._rng.randint(0, NUM_COLORS - 1),
                life=20,
                max_life=20,
            ))

    def _spawn_score_particles(self) -> None:
        for _ in range(12):
            self.particles.append(Particle(
                x=SCREEN_W - 4, y=self._rng.uniform(20, SCREEN_H - 20),
                vx=self._rng.uniform(-2, -0.5),
                vy=self._rng.uniform(-1, 1),
                color=self.ball.color,
                life=18,
                max_life=18,
            ))

    # ── Draw ──
    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        shake_x = shake_y = 0
        if self._shake_frames > 0:
            shake_x = self._rng.randint(-3, 3)
            shake_y = self._rng.randint(-3, 3)

        # SURGE background pulse
        if self.surge_timer > 0:
            pyxel.rect(0, 0, SCREEN_W, SCREEN_H, pyxel.COLOR_NAVY)

        # Center line
        for i in range(0, SCREEN_H, 12):
            pyxel.rect(
                SCREEN_W // 2 - 1 + shake_x, i + shake_y, 2, 6, pyxel.COLOR_GRAY
            )

        # Draw paddles
        self._draw_paddle(self.player, shake_x, shake_y)
        self._draw_paddle(self.ai, shake_x, shake_y)

        # Draw ball
        b = self.ball
        bx = int(b.x) + shake_x
        by = int(b.y) + shake_y
        # Glow during SURGE
        if self.surge_timer > 0:
            glow_r = BALL_RADIUS + 3 + int(abs(math.sin(self.surge_timer * 0.3)) * 3)
            pyxel.circb(bx, by, glow_r, pyxel.COLOR_WHITE)
        pyxel.circ(bx, by, BALL_RADIUS + 1, pyxel.COLOR_WHITE)
        pyxel.circ(bx, by, BALL_RADIUS, b.color_val())

        # Draw particles
        for p in self.particles:
            alpha = p.life / max(p.max_life, 1)
            col = COLOR_DEFS[p.color][1] if alpha > 0.45 else pyxel.COLOR_GRAY
            px = int(p.x) + shake_x
            py = int(p.y) + shake_y
            if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
                pyxel.pset(px, py, col)

        # HUD
        pyxel.text(2, 2, f"SCORE:{self.score}", pyxel.COLOR_WHITE)
        combo_col = pyxel.COLOR_YELLOW if self.combo >= COMBO_SURGE_THRESHOLD else pyxel.COLOR_WHITE
        pyxel.text(2, 10, f"COMBO:{self.combo}", combo_col)
        pyxel.text(2, 18, f"MAX:{self.max_combo}", pyxel.COLOR_GRAY)
        pyxel.text(2, 26, f"HITS:{self.rally_count}", pyxel.COLOR_GRAY)

        # Speed indicator
        spd_pct = int((b.speed - BALL_SPEED_INIT) / (BALL_SPEED_MAX - BALL_SPEED_INIT) * 100)
        pyxel.text(SCREEN_W - 56, 2, f"SPD:{spd_pct}%", pyxel.COLOR_GRAY)

        # SURGE indicator
        if self.surge_timer > 0:
            secs = self.surge_timer // 60 + 1
            txt = f"SURGE {secs}s"
            tw = len(txt) * 4
            pyxel.text(
                SCREEN_W // 2 - tw // 2, SCREEN_H - 10,
                txt, pyxel.COLOR_YELLOW,
            )

        # Color indicators
        self._draw_color_hud()

        if self.game_over:
            self._draw_game_over()

    def _draw_paddle(self, p: Paddle, shake_x: int, shake_y: int) -> None:
        px = int(p.x) + shake_x
        py = int(p.y) + shake_y
        hw = PADDLE_W // 2
        hh = PADDLE_H // 2
        pyxel.rect(px - hw, py - hh, PADDLE_W, PADDLE_H, p.color_val())
        pyxel.rectb(px - hw, py - hh, PADDLE_W, PADDLE_H, pyxel.COLOR_WHITE)
        # Center color dot
        pyxel.circ(px, py, 2, pyxel.COLOR_WHITE)

    def _draw_color_hud(self) -> None:
        """Show available colors and highlight current."""
        for i, (name, col_idx) in enumerate(COLOR_DEFS):
            x = 4 + i * 24
            y = SCREEN_H - 12
            pyxel.rect(x, y, 18, 8, col_idx)
            if i == self.player.color:
                pyxel.rectb(x - 1, y - 1, 20, 10, pyxel.COLOR_WHITE)
            if i == self.ball.color:
                pyxel.rect(x + 6, y - 2, 6, 3, pyxel.COLOR_WHITE)

    def _draw_game_over(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, pyxel.COLOR_BLACK)
        texts = [
            ("GAME OVER", pyxel.COLOR_RED, -28),
            (f"SCORE: {self.score}", pyxel.COLOR_WHITE, -6),
            (f"MAX COMBO: {self.max_combo}", pyxel.COLOR_YELLOW, 10),
            (f"HITS: {self.rally_count}", pyxel.COLOR_GRAY, 26),
            ("PRESS R TO RESTART", pyxel.COLOR_GRAY, 50),
        ]
        for txt, col, y_off in texts:
            tw = len(txt) * 4
            pyxel.text(SCREEN_W // 2 - tw // 2, SCREEN_H // 2 + y_off, txt, col)


if __name__ == "__main__":
    Game()
