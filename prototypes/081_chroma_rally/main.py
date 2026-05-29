"""081_chroma_rally — CHROMA RALLY
Color-Match Tennis Rally.

Side-view tennis rally game. Player (left) rallies against AI opponent (right)
across a net. The ball and racket both have colors. Hitting the ball when
colors MATCH builds COMBO. COMBO >= 4 triggers SUPER SHOT — an ultra-fast
unreturnable winner. Wrong-color hit returns the ball normally but resets COMBO.
Miss the ball = opponent scores.

Core fun: "Chaining same-color returns to hit COMBO 4, unleashing a SUPER SHOT
that blazes past the opponent — they can't even react."
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import pyxel

# ── Constants ──────────────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
FPS = 60

COLORS: tuple[int, ...] = (8, 3, 10, 12)  # RED, GREEN, YELLOW, CYAN
COLOR_NAMES: tuple[str, ...] = ("RED", "GREEN", "YELLOW", "CYAN")
MATCH_POINTS = 7
NET_X = SCREEN_W // 2
NET_HEIGHT = 200
PLAYER_X = 40
OPPONENT_X = SCREEN_W - 40
RACKET_W = 6
RACKET_H = 32
BALL_RADIUS = 5
BALL_SPEED = 3.0
SUPER_SPEED = 8.0
COMBO_FOR_SUPER = 4
GRAVITY = 0.15
COURT_TOP = 30
COURT_BOTTOM = SCREEN_H - 10
PLAYER_SPEED = 3.0
AI_SPEED_FACTOR = 0.85
AI_RANDOM_OFFSET = 8.0
SERVE_FRAMES = 60
TRAIL_LENGTH = 6
SUPER_TRAIL_LENGTH = 12


class Phase(IntEnum):
    TITLE = 0
    PLAYING = 1
    POINT_SCORED = 2
    GAME_OVER = 3


# ── Data Classes ──────────────────────────────────────────────────────────────


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    color: int  # 0-3
    active: bool = True
    is_super: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int
    max_life: int = 15


# ── Game ──────────────────────────────────────────────────────────────────────


class Game:
    """CHROMA RALLY — Color-Match Tennis Rally."""

    def __init__(self) -> None:
        pyxel.init(
            SCREEN_W, SCREEN_H,
            title="CHROMA RALLY",
            fps=FPS,
            display_scale=2,
        )
        font_path = str(Path(__file__).with_name("k8x12.bdf"))
        if Path(font_path).exists():
            pyxel.load(font_path, True, True)

        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── State Management ──────────────────────────────────────────────────

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.player_y: float = SCREEN_H // 2
        self.opponent_y: float = SCREEN_H // 2
        self.racket_color: int = 0
        self.ball: Ball = Ball(
            x=NET_X, y=SCREEN_H // 2, vx=0.0, vy=0.0, color=0,
        )
        self.combo: int = 0
        self.max_combo: int = 0
        self.score_player: int = 0
        self.score_opponent: int = 0
        self.super_ready: bool = False
        self.particles: list[Particle] = []
        self.serve_timer: int = 0
        self.last_hitter: str = "none"
        self._rng = random.Random()
        self._ball_trail: list[tuple[float, float, int, bool]] = []
        self._player_hit_count: int = 0
        self._opponent_hit_count: int = 0
        self._shake_frames: int = 0
        self._point_text_timer: int = 0
        self._point_scorer: str = ""
        self.total_score: int = 0
        self._title_blink_timer: int = 0
        self._title_demo_ball: Ball = Ball(
            x=NET_X, y=SCREEN_H // 2, vx=2.0, vy=1.0, color=0,
        )
        self._title_demo_paddle_y: float = SCREEN_H // 2
        self._title_demo_opponent_y: float = SCREEN_H // 2

    # ── Update ────────────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.POINT_SCORED:
            self._update_point_scored()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        self._title_blink_timer += 1
        # Animate demo ball
        b = self._title_demo_ball
        b.x += b.vx
        b.y += b.vy
        if b.y - BALL_RADIUS <= COURT_TOP:
            b.y = COURT_TOP + BALL_RADIUS
            b.vy = abs(b.vy)
        elif b.y + BALL_RADIUS >= COURT_BOTTOM:
            b.y = COURT_BOTTOM - BALL_RADIUS
            b.vy = -abs(b.vy)
        # Paddle tracking
        self._title_demo_paddle_y += (b.y - self._title_demo_paddle_y) * 0.15
        self._title_demo_opponent_y += (b.y - self._title_demo_opponent_y) * 0.12
        if b.x - BALL_RADIUS <= PLAYER_X + RACKET_W + 2:
            b.x = PLAYER_X + RACKET_W + 2 + BALL_RADIUS
            b.vx = abs(b.vx)
            b.color = (b.color + 1) % 4
        elif b.x + BALL_RADIUS >= OPPONENT_X - RACKET_W - 2:
            b.x = OPPONENT_X - RACKET_W - 2 - BALL_RADIUS
            b.vx = -abs(b.vx)
            b.color = (b.color + 1) % 4

        if pyxel.btnp(pyxel.KEY_RETURN):
            self._rng = random.Random()
            self.phase = Phase.PLAYING
            self.total_score = 0
            self.score_player = 0
            self.score_opponent = 0
            self.max_combo = 0
            self.combo = 0
            self._player_hit_count = 0
            self._opponent_hit_count = 0
            self.racket_color = 0
            self.player_y = SCREEN_H // 2
            self.opponent_y = SCREEN_H // 2
            self.particles.clear()
            self._ball_trail.clear()
            self._serve_ball()

    def _update_playing(self) -> None:
        # Input
        if pyxel.btn(pyxel.KEY_UP):
            self.player_y -= PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_DOWN):
            self.player_y += PLAYER_SPEED
        self.player_y = max(
            COURT_TOP + RACKET_H // 2,
            min(COURT_BOTTOM - RACKET_H // 2, self.player_y),
        )

        # AI
        self._ai_move()

        # Ball physics
        self._update_ball()

        # Check scoring (ball passed a player)
        b = self.ball
        if not b.active:
            return

        if b.x + BALL_RADIUS < PLAYER_X - RACKET_W - 10:
            self._score_point("opponent")
            return
        if b.x - BALL_RADIUS > OPPONENT_X + RACKET_W + 10:
            self._score_point("player")
            return

        # Check paddle collisions
        self._check_player_hit()
        self._check_opponent_hit()

        # Update particles and trail
        self._update_particles()
        self._update_trail()

    def _update_point_scored(self) -> None:
        self.serve_timer -= 1
        self._update_particles()
        self._update_trail()
        if self._point_text_timer > 0:
            self._point_text_timer -= 1
        if self._shake_frames > 0:
            self._shake_frames -= 1
        if self.serve_timer <= 0:
            if self.score_player >= MATCH_POINTS or self.score_opponent >= MATCH_POINTS:
                self.phase = Phase.GAME_OVER
            else:
                self.phase = Phase.PLAYING
                self._serve_ball()

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self._rng = random.Random()
            self.phase = Phase.PLAYING
            self.total_score = 0
            self.score_player = 0
            self.score_opponent = 0
            self.max_combo = 0
            self.combo = 0
            self._player_hit_count = 0
            self._opponent_hit_count = 0
            self.racket_color = 0
            self.player_y = SCREEN_H // 2
            self.opponent_y = SCREEN_H // 2
            self.particles.clear()
            self._ball_trail.clear()
            self._serve_ball()

    # ── Serving ───────────────────────────────────────────────────────────

    def _serve_ball(self) -> None:
        direction = 1 if self._rng.random() < 0.5 else -1
        color = self._rng.randint(0, 3)
        angle = self._rng.uniform(-0.5, 0.5)
        vx = BALL_SPEED * direction
        vy = BALL_SPEED * angle
        self.ball = Ball(
            x=NET_X, y=SCREEN_H // 2,
            vx=vx, vy=vy,
            color=color,
            active=True,
            is_super=False,
        )
        self.ball.vx *= BALL_SPEED / max(abs(self.ball.vx), abs(self.ball.vy))
        self.ball.vy *= BALL_SPEED / max(abs(self.ball.vx), abs(self.ball.vy))
        self.combo = 0
        self.super_ready = False
        self.last_hitter = "none"
        self._ball_trail.clear()

    # ── Ball Physics ──────────────────────────────────────────────────────

    def _update_ball(self) -> None:
        b = self.ball
        if not b.active:
            return
        b.x += b.vx
        b.y += b.vy
        b.vy += GRAVITY

        # Bounce off top/bottom
        if b.y - BALL_RADIUS <= COURT_TOP:
            b.y = COURT_TOP + BALL_RADIUS
            b.vy = abs(b.vy)
        elif b.y + BALL_RADIUS >= COURT_BOTTOM:
            b.y = COURT_BOTTOM - BALL_RADIUS
            b.vy = -abs(b.vy)

    def _update_trail(self) -> None:
        b = self.ball
        max_len = SUPER_TRAIL_LENGTH if b.is_super else TRAIL_LENGTH
        self._ball_trail.append((b.x, b.y, b.color, b.is_super))
        if len(self._ball_trail) > max_len:
            self._ball_trail = self._ball_trail[-max_len:]

    # ── AI ────────────────────────────────────────────────────────────────

    def _ai_move(self) -> None:
        b = self.ball
        ai_speed = PLAYER_SPEED * AI_SPEED_FACTOR

        if b.is_super and b.vx > 0:
            return  # AI freezes on SUPER SHOT

        target_y = b.y
        if b.vx < 0:
            target_y = SCREEN_H // 2  # Ball moving away, return to center

        if self.opponent_y < target_y:
            self.opponent_y += ai_speed
        elif self.opponent_y > target_y:
            self.opponent_y -= ai_speed

        # Add imperfection
        self.opponent_y += self._rng.uniform(-AI_RANDOM_OFFSET * 0.3, AI_RANDOM_OFFSET * 0.3)

        self.opponent_y = max(
            COURT_TOP + RACKET_H // 2,
            min(COURT_BOTTOM - RACKET_H // 2, self.opponent_y),
        )

    # ── Collision Detection ───────────────────────────────────────────────

    def _check_player_hit(self) -> None:
        b = self.ball
        if not b.active or b.vx > 0:
            return  # Ball moving away from player

        px = PLAYER_X
        py = self.player_y
        hw = RACKET_W
        hh = RACKET_H // 2

        if (
            b.x - BALL_RADIUS <= px + hw
            and b.x + BALL_RADIUS >= px - hw
            and b.y + BALL_RADIUS >= py - hh
            and b.y - BALL_RADIUS <= py + hh
        ):
            # Hit!
            b.x = px + hw + BALL_RADIUS
            b.vx = abs(b.vx)

            # Vertical influence
            hit_offset = (b.y - py) / (hh if hh > 0 else 1)
            b.vy += hit_offset * 3.0

            self._resolve_hit("player")

    def _check_opponent_hit(self) -> None:
        b = self.ball
        if not b.active or b.vx < 0:
            return  # Ball moving away from opponent

        ox = OPPONENT_X
        oy = self.opponent_y
        hw = RACKET_W
        hh = RACKET_H // 2

        if (
            b.x + BALL_RADIUS >= ox - hw
            and b.x - BALL_RADIUS <= ox + hw
            and b.y + BALL_RADIUS >= oy - hh
            and b.y - BALL_RADIUS <= oy + hh
        ):
            # Hit!
            b.x = ox - hw - BALL_RADIUS
            b.vx = -abs(b.vx)

            # Vertical influence
            hit_offset = (b.y - oy) / (hh if hh > 0 else 1)
            b.vy += hit_offset * 1.5

            self._resolve_hit("opponent")

    def _resolve_hit(self, hitter: str) -> None:
        b = self.ball

        if hitter == "player":
            # Check match BEFORE cycling racket color
            color_matched = (b.color == self.racket_color)
            self._player_hit_count += 1
            self.racket_color = self._player_hit_count % 4

            if color_matched:
                # Same-color match
                self.combo += 1
                self.max_combo = max(self.max_combo, self.combo)

                if self.combo >= COMBO_FOR_SUPER:
                    # SUPER SHOT!
                    b.is_super = True
                    self.super_ready = True
                    speed = SUPER_SPEED
                    self._spawn_super_particles()
                    self._shake_frames = 15
                    self._point_text_timer = 30
                else:
                    speed = BALL_SPEED + self.combo * 0.5

                # Ball color cycles to next
                b.color = (b.color + 1) % 4
            else:
                # Mismatch — reset combo
                speed = BALL_SPEED
                self.combo = 0
                self.super_ready = False

            # Normalize velocity to speed
            current = (b.vx * b.vx + b.vy * b.vy) ** 0.5
            if current > 0:
                scale = speed / current
                b.vx *= scale
                b.vy *= scale

            self._spawn_hit_particles(b.x, b.y, b.color)
            self.last_hitter = "player"

        else:
            # Opponent hit — just returns, doesn't affect player combo
            self._opponent_hit_count += 1

            # Opponent doesn't color-match — just returns at normal speed
            speed = BALL_SPEED

            # Ball color changes on opponent hit too (adds variety)
            b.color = self._rng.randint(0, 3)

            current = (b.vx * b.vx + b.vy * b.vy) ** 0.5
            if current > 0:
                scale = speed / current
                b.vx *= scale
                b.vy *= scale

            self._spawn_hit_particles(b.x, b.y, b.color)
            self.last_hitter = "opponent"

    # ── Scoring ───────────────────────────────────────────────────────────

    def _score_point(self, scorer: str) -> None:
        b = self.ball
        b.active = False

        if scorer == "player":
            self.score_player += 1
            bonus = 100
            bonus += self.combo * 50
            if b.is_super:
                bonus += 500
            self.total_score += bonus
            self._spawn_point_particles(OPPONENT_X, b.y)
        else:
            self.score_opponent += 1
            self._spawn_point_particles(PLAYER_X, b.y)

        self.combo = 0
        self.super_ready = False
        self.phase = Phase.POINT_SCORED
        self.serve_timer = SERVE_FRAMES
        self._point_text_timer = 40
        self._point_scorer = scorer

    # ── Particles ─────────────────────────────────────────────────────────

    def _spawn_hit_particles(self, x: float, y: float, color: int) -> None:
        count = 8
        for _ in range(count):
            self.particles.append(Particle(
                x=x, y=y,
                vx=self._rng.uniform(-2, 2),
                vy=self._rng.uniform(-2, 2),
                color=color,
                life=15,
                max_life=15,
            ))

    def _spawn_super_particles(self) -> None:
        colors = [0, 1, 2, 3]
        for _ in range(20):
            self.particles.append(Particle(
                x=self.ball.x, y=self.ball.y,
                vx=self._rng.uniform(-4, 4),
                vy=self._rng.uniform(-4, 4),
                color=colors[_ % 4],
                life=20,
                max_life=20,
            ))

    def _spawn_point_particles(self, x: float, y: float) -> None:
        for _ in range(12):
            self.particles.append(Particle(
                x=x, y=y,
                vx=self._rng.uniform(-3, 3),
                vy=self._rng.uniform(-3, 3),
                color=self._rng.randint(0, 3),
                life=20,
                max_life=20,
            ))

    def _update_particles(self) -> None:
        survivors: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1  # gravity
            p.life -= 1
            if p.life > 0:
                survivors.append(p)
        self.particles = survivors

    # ── Draw ──────────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(1)  # Navy background

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.POINT_SCORED:
            self._draw_playing()
            self._draw_point_overlay()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_playing(self) -> None:
        shake_x = shake_y = 0
        if self._shake_frames > 0:
            shake_x = self._rng.randint(-2, 2)
            shake_y = self._rng.randint(-2, 2)

        self._draw_court(shake_x, shake_y)
        self._draw_trail(shake_x, shake_y)
        self._draw_ball(shake_x, shake_y)
        self._draw_racket_player(shake_x, shake_y)
        self._draw_racket_opponent(shake_x, shake_y)
        self._draw_particles(shake_x, shake_y)
        self._draw_hud()
        self._draw_super_indicator()

    def _draw_court(self, shake_x: int, shake_y: int) -> None:
        # Green court surface
        pyxel.rect(
            0, COURT_TOP,
            SCREEN_W, COURT_BOTTOM - COURT_TOP + 10,
            3,  # GREEN
        )
        # White boundary lines
        pyxel.line(0, COURT_TOP, SCREEN_W, COURT_TOP, 7)  # top
        pyxel.line(0, COURT_BOTTOM, SCREEN_W, COURT_BOTTOM, 7)  # bottom
        # Net
        for i in range(COURT_TOP, COURT_BOTTOM, 12):
            pyxel.line(
                NET_X + shake_x, i,
                NET_X + shake_x, min(i + 6, COURT_BOTTOM),
                13,  # GRAY
            )
        # Net post
        pyxel.rect(NET_X - 1 + shake_x, COURT_TOP - 5, 3, 10, 7)

    def _draw_racket_player(self, shake_x: int, shake_y: int) -> None:
        px = PLAYER_X + shake_x
        py = int(self.player_y) + shake_y
        hw = RACKET_W
        hh = RACKET_H // 2
        color = COLORS[self.racket_color]

        # Racket body
        pyxel.rect(px - hw, py - hh, RACKET_W * 2, RACKET_H, color)
        pyxel.rectb(px - hw, py - hh, RACKET_W * 2, RACKET_H, 7)
        # Handle
        pyxel.rect(px + hw, py - 3, 5, 6, 13)

    def _draw_racket_opponent(self, shake_x: int, shake_y: int) -> None:
        ox = OPPONENT_X + shake_x
        oy = int(self.opponent_y) + shake_y
        hw = RACKET_W
        hh = RACKET_H // 2

        # Opponent racket always white
        pyxel.rect(ox - hw, oy - hh, RACKET_W * 2, RACKET_H, 7)
        pyxel.rectb(ox - hw, oy - hh, RACKET_W * 2, RACKET_H, 7)
        # Handle
        pyxel.rect(ox - hw - 5, oy - 3, 5, 6, 13)

    def _draw_ball(self, shake_x: int, shake_y: int) -> None:
        b = self.ball
        if not b.active and self.phase == Phase.PLAYING:
            return
        bx = int(b.x) + shake_x
        by = int(b.y) + shake_y
        color = COLORS[b.color]

        # Glow for super shot
        if b.is_super:
            glow_r = BALL_RADIUS + 3 + int(abs(pyxel.sin(pyxel.frame_count * 0.3)) * 3)
            pyxel.circb(bx, by, glow_r, 7)

        pyxel.circ(bx, by, BALL_RADIUS, color)
        pyxel.circb(bx, by, BALL_RADIUS, 7)

    def _draw_trail(self, shake_x: int, shake_y: int) -> None:
        trail = list(self._ball_trail)
        total = len(trail)
        for i, (tx, ty, tc, ts) in enumerate(trail):
            t = (i + 1) / max(1, total)
            r = BALL_RADIUS * t * 0.8
            if r < 0.5:
                continue
            col = COLORS[tc]
            if ts:
                col = 7 if t < 0.5 else col
            bx = int(tx) + shake_x
            by = int(ty) + shake_y
            pyxel.circb(bx, by, int(r), col)

    def _draw_particles(self, shake_x: int, shake_y: int) -> None:
        for p in self.particles:
            px = int(p.x) + shake_x
            py = int(p.y) + shake_y
            alpha = p.life / max(p.max_life, 1)
            if alpha > 0.5:
                col = COLORS[p.color]
            elif alpha > 0.25:
                col = 13  # GRAY
            else:
                col = 1  # NAVY
            if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
                pyxel.pset(px, py, col)

    def _draw_hud(self) -> None:
        # Score
        score_text = f"YOU {self.score_player} - {self.score_opponent} CPU"
        tw = len(score_text) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 4, score_text, 7)

        # Score total
        total_text = f"SCORE: {self.total_score}"
        pyxel.text(4, 4, total_text, 7)

        # COMBO
        if self.combo > 0:
            combo_color = COLORS[self.racket_color]
            combo_text = f"COMBO x{self.combo}"
            pyxel.text(4, 16, combo_text, combo_color)

        # Markers for MATCH_POINTS
        for i in range(MATCH_POINTS):
            px = 110 + i * 10
            py = 18
            if i < self.score_player:
                col = 7  # white filled
                pyxel.circ(px, py, 3, col)
            elif i < self.score_opponent:
                col = 13  # gray filled
                pyxel.circ(px + 80, py, 3, col)
            else:
                col = 5  # dark blue empty
                pyxel.circb(px, py, 3, col)

        # Color indicator for player racket
        pyxel.rect(4, SCREEN_H - 16, 12, 12, COLORS[self.racket_color])
        pyxel.rectb(4, SCREEN_H - 16, 12, 12, 7)

    def _draw_super_indicator(self) -> None:
        if not self.super_ready:
            return
        pulse = int(abs(pyxel.sin(pyxel.frame_count * 0.2)) * 3)
        text = "SUPER READY!"
        tw = len(text) * 4
        pyxel.text(
            SCREEN_W // 2 - tw // 2, SCREEN_H - 20,
            text, 7 if pulse > 1 else 10,
        )

    def _draw_point_overlay(self) -> None:
        if self._point_text_timer <= 0:
            return
        scorer = self._point_scorer
        if scorer == "player":
            text = "POINT! +" + str(100 + self.max_combo * 50 + (500 if self.ball.is_super else 0))
            col = 10  # YELLOW
        elif scorer == "opponent":
            text = "CPU SCORES!"
            col = 8  # RED
        else:
            return
        tw = len(text) * 4
        ty = SCREEN_H // 2 - 20
        self._draw_text_shadow(text, SCREEN_W // 2 - tw // 2, ty, col)

    def _draw_title(self) -> None:
        # Animated background demo
        self._draw_court(0, 0)
        # Demo paddles
        px = PLAYER_X
        py = int(self._title_demo_paddle_y)
        pyxel.rect(px - RACKET_W, py - RACKET_H // 2, RACKET_W * 2, RACKET_H, COLORS[0])
        pyxel.rectb(px - RACKET_W, py - RACKET_H // 2, RACKET_W * 2, RACKET_H, 7)
        pyxel.rect(px + RACKET_W, py - 3, 5, 6, 13)

        ox = OPPONENT_X
        oy = int(self._title_demo_opponent_y)
        pyxel.rect(ox - RACKET_W, oy - RACKET_H // 2, RACKET_W * 2, RACKET_H, 7)
        pyxel.rectb(ox - RACKET_W, oy - RACKET_H // 2, RACKET_W * 2, RACKET_H, 7)
        pyxel.rect(ox - RACKET_W - 5, oy - 3, 5, 6, 13)

        # Demo ball
        b = self._title_demo_ball
        pyxel.circ(int(b.x), int(b.y), BALL_RADIUS, COLORS[b.color])
        pyxel.circb(int(b.x), int(b.y), BALL_RADIUS, 7)

        # Title background band
        pyxel.rect(0, 30, SCREEN_W, 130, 1)
        pyxel.line(0, 30, SCREEN_W, 30, 5)
        pyxel.line(0, 160, SCREEN_W, 160, 5)

        # Title
        title = "CHROMA RALLY"
        tw = len(title) * 4
        self._draw_text_shadow(title, SCREEN_W // 2 - tw // 2, 50, 8)

        subtitle = "Color-Match Tennis"
        sw = len(subtitle) * 4
        self._draw_text_shadow(subtitle, SCREEN_W // 2 - sw // 2, 68, 10)

        # Instructions
        inst1 = "UP/DOWN: Move Racket"
        iw1 = len(inst1) * 4
        pyxel.text(SCREEN_W // 2 - iw1 // 2, 100, inst1, 7)

        inst2 = "Match colors for COMBO!"
        iw2 = len(inst2) * 4
        pyxel.text(SCREEN_W // 2 - iw2 // 2, 112, inst2, 7)

        inst3 = "COMBO x4 = SUPER SHOT!"
        iw3 = len(inst3) * 4
        pyxel.text(SCREEN_W // 2 - iw3 // 2, 124, inst3, 7)

        inst4 = "First to 7 wins!"
        iw4 = len(inst4) * 4
        pyxel.text(SCREEN_W // 2 - iw4 // 2, 136, inst4, 7)

        # Blinking "Press ENTER"
        if (self._title_blink_timer // 30) % 2 == 0:
            start_text = "Press ENTER to start"
            sw2 = len(start_text) * 4
            pyxel.text(SCREEN_W // 2 - sw2 // 2, 170, start_text, 7)

        # Color legend
        for i, (name, col) in enumerate(zip(COLOR_NAMES, COLORS)):
            x = 60 + i * 60
            pyxel.rect(x, 190, 14, 14, col)
            pyxel.text(x + 18, 193, name, col)

    def _draw_text_shadow(self, text: str, x: int, y: int, color: int) -> None:
        pyxel.text(x + 1, y + 1, text, 5)
        pyxel.text(x, y, text, color)

    def _draw_game_over(self) -> None:
        # Keep the court visible in background
        self._draw_court(0, 0)
        self._draw_racket_player(0, 0)
        self._draw_racket_opponent(0, 0)

        # Dark overlay
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, 1)

        # Result
        if self.score_player >= MATCH_POINTS:
            result = "YOU WIN!"
            col = 10  # YELLOW
        else:
            result = "CPU WINS!"
            col = 8  # RED

        tw = len(result) * 4
        self._draw_text_shadow(result, SCREEN_W // 2 - tw // 2, 60, col)

        # Stats
        lines = [
            f"FINAL SCORE: {self.total_score}",
            f"MAX COMBO: {self.max_combo}",
            f"YOU {self.score_player} - {self.score_opponent} CPU",
            "",
            "Press ENTER to restart",
        ]
        y = 100
        for line in lines:
            lw = len(line) * 4
            col2 = 10 if line.startswith("MAX COMBO:") else 7
            pyxel.text(SCREEN_W // 2 - lw // 2, y, line, col2)
            y += 16


if __name__ == "__main__":
    Game()
