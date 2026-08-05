"""DODGE CHAIN -- Color-Match Dodgeball Prototype.

Most fun moment: Catching an incoming ball at the last second, throwing it
right back, and hitting same-color opponents consecutively to build a COMBO
chain that explodes into a SUPER THROW wiping out the entire enemy team.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
import math
import random

import pyxel


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCREEN_W = 320
SCREEN_H = 240
FPS = 30

GAME_DURATION = 60 * FPS  # 1800 frames (60 seconds)
SUPER_THRESHOLD = 4
SUPER_DURATION = 300  # 10 seconds
HEAT_HIT = 15.0
HEAT_WRONG_COLOR = 5.0
HEAT_COOL_HIT = -5.0
HEAT_COOL_CATCH = -10.0
HEAT_DECAY = 0.02
HEAT_MAX = 100.0
HEAT_WARN = 70.0
HEAT_DANGER = 85.0
PLAYER_SPEED = 2.5
BALL_SPEED = 6.0
OPPONENT_COUNT = 3
AI_THROW_MIN = 60
AI_THROW_MAX = 120
OPPONENT_RESPAWN = 90
PLAYER_RADIUS = 10
OPPONENT_RADIUS = 9
BALL_RADIUS = 4
CATCH_RADIUS = 18
THROW_COOLDOWN = 20

COLOR_VALS = (8, 11, 5, 10)  # RED, LIME, DARK_BLUE, YELLOW


# ---------------------------------------------------------------------------
# Phase enum
# ---------------------------------------------------------------------------

class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    color: int  # 0-3
    from_player: bool = True
    active: bool = True


@dataclass
class Opponent:
    x: float
    y: float
    color: int
    hit: bool = False
    respawn_timer: int = 0
    throw_timer: int = 0


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
    text: str
    x: float
    y: float
    life: int
    color: int


# ---------------------------------------------------------------------------
# Game class
# ---------------------------------------------------------------------------

class Game:
    """Main game class for DODGE CHAIN."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="DODGE CHAIN", fps=FPS, display_scale=2)
        self._rng = random.Random()
        self.best_score: int = 0
        self.reset()
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.game_timer: int = 0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.player_x: float = 160.0
        self.player_y: float = 200.0
        self.player_color: int = self._rng.randint(0, 3)
        self.balls: list[Ball] = []
        self.opponents: list[Opponent] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shake_frames: int = 0
        self._throw_cooldown: int = 0
        self._difficulty_timer: int = 0
        self._spawn_opponents()

    def _spawn_opponents(self) -> None:
        self.opponents = []
        positions = [(80.0, 45.0), (160.0, 45.0), (240.0, 45.0)]
        for px, py in positions:
            color = self._rng.randint(0, 3)
            throw_timer = self._rng.randint(AI_THROW_MIN, AI_THROW_MAX)
            self.opponents.append(Opponent(x=px, y=py, color=color, throw_timer=throw_timer))

    # ------------------------------------------------------------------
    # Update / Draw dispatch
    # ------------------------------------------------------------------

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.PLAYING
                self._throw_ball(160.0, 120.0)
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.PLAYING
                self._throw_ball(160.0, 120.0)
            return

        if self.phase == Phase.PLAYING:
            self._tick_timers()
            if self.phase != Phase.PLAYING:
                return
            self._update_player_input(
                pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A),
                pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D),
                pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W),
                pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S),
            )
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self._handle_click(float(pyxel.mouse_x), float(pyxel.mouse_y))
            self._update_balls()
            self._update_opponents()
            self._update_particles()
            self._update_floating_texts()
            if self.shake_frames > 0:
                self.shake_frames -= 1

    def draw(self) -> None:
        pyxel.cls(1)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    # ------------------------------------------------------------------
    # Title screen
    # ------------------------------------------------------------------

    def _draw_title(self) -> None:
        color_idx = (pyxel.frame_count // 15) % 4
        title_color = [8, 11, 5, 10][color_idx]
        title = "DODGE CHAIN"
        pyxel.text(SCREEN_W // 2 - len(title) * 4 // 2, 60, title, title_color)
        pyxel.text(60, 110, "Arrow Keys: Move", 7)
        pyxel.text(60, 125, "Click: Throw Ball", 7)
        pyxel.text(35, 145, "Click near incoming ball to CATCH!", 10)
        pyxel.text(45, 165, "Same-color hits = COMBO chain", 7)
        pyxel.text(45, 180, "COMBO >= 4 = SUPER THROW!", 9)
        if pyxel.frame_count % 40 < 20:
            pyxel.text(100, 215, "Press SPACE to Start", 7)
        if self.best_score > 0:
            pyxel.text(10, 5, f"Best: {self.best_score}", 7)

    # ------------------------------------------------------------------
    # Game over screen
    # ------------------------------------------------------------------

    def _draw_game_over(self) -> None:
        title = "GAME OVER"
        pyxel.text(SCREEN_W // 2 - len(title) * 4 // 2, 70, title, 8)
        pyxel.text(100, 110, f"Score: {self.score}", 7)
        pyxel.text(100, 130, f"Max Combo: {self.max_combo}", 7)
        pyxel.text(100, 150, f"Best: {self.best_score}", 7)
        if self.score >= self.best_score and self.score > 0 and pyxel.frame_count % 20 < 10:
            pyxel.text(105, 170, "NEW BEST!", 10)
        if pyxel.frame_count % 40 < 20:
            pyxel.text(95, 200, "Press SPACE to Retry", 7)

    # ------------------------------------------------------------------
    # Playing screen drawing
    # ------------------------------------------------------------------

    def _draw_playing(self) -> None:
        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0:
            shake_x = int(math.sin(pyxel.frame_count * 0.5) * self.shake_frames * 0.3)
            shake_y = int(math.cos(pyxel.frame_count * 0.7) * self.shake_frames * 0.3)

        # Court boundary
        pyxel.rectb(18 + shake_x, 18 + shake_y, 284, 204, 7)
        pyxel.line(18 + shake_x, 120 + shake_y, 302 + shake_x, 120 + shake_y, 13)

        # Opponents
        for opp in self.opponents:
            opp_col = COLOR_VALS[opp.color]
            if opp.hit:
                opp_col = 13
            pyxel.circ(int(opp.x + shake_x), int(opp.y + shake_y), OPPONENT_RADIUS, opp_col)

        # Player
        player_col = COLOR_VALS[self.player_color]
        if self.super_mode:
            colors = [8, 11, 5, 10]
            player_col = colors[(pyxel.frame_count // 4) % 4]
        pyxel.circ(int(self.player_x + shake_x), int(self.player_y + shake_y), PLAYER_RADIUS, player_col)
        pyxel.circ(int(self.player_x + shake_x), int(self.player_y + shake_y), PLAYER_RADIUS - 3, 0)

        # Balls
        for ball in self.balls:
            if not ball.active:
                continue
            col = COLOR_VALS[ball.color]
            pyxel.circ(int(ball.x + shake_x), int(ball.y + shake_y), BALL_RADIUS, col)
            if not ball.from_player:
                pyxel.circb(int(ball.x + shake_x), int(ball.y + shake_y), BALL_RADIUS + 1, 7)

        # Particles
        for p in self.particles:
            alpha_col = p.color if p.life > 5 else 13
            pyxel.rect(int(p.x + shake_x), int(p.y + shake_y), 2, 2, alpha_col)

        # Floating texts
        for ft in self.floating_texts:
            pyxel.text(int(ft.x + shake_x), int(ft.y + shake_y), ft.text, ft.color)

        # HEAT bar
        bar_h = int((self.heat / HEAT_MAX) * 200)
        bar_color = 3
        if self.heat >= HEAT_DANGER:
            bar_color = 8
        elif self.heat >= HEAT_WARN:
            bar_color = 9
        pyxel.rect(4, 230 - bar_h, 10, bar_h, bar_color)
        pyxel.rectb(3, 29, 12, 202, 7)
        pyxel.text(2, 8, "HEAT", 7)

        # UI
        pyxel.text(220, 5, f"SCORE:{self.score}", 7)
        time_left = max(0, (GAME_DURATION - self.game_timer) // FPS)
        pyxel.text(235, 15, f"TIME:{time_left}", 7)

        if self.combo > 0:
            combo_text = f"COMBO x{self.combo}"
            combo_col = 7
            if self.combo >= 2:
                combo_col = 9
            if self.combo >= 4:
                combo_col = 8
            pyxel.text(
                SCREEN_W // 2 - len(combo_text) * 4 // 2 + shake_x,
                130 + shake_y,
                combo_text,
                combo_col,
            )

        # SUPER MODE border
        if self.super_mode:
            border_colors = [8, 11, 5, 10]
            border_c = border_colors[(pyxel.frame_count // 5) % 4]
            pyxel.rectb(1, 1, SCREEN_W - 2, SCREEN_H - 2, border_c)
            sec_left = self.super_timer // FPS
            pyxel.text(90, 5, f"SUPER! {sec_left}s", 10)

    # ------------------------------------------------------------------
    # Input (headless-testable)
    # ------------------------------------------------------------------

    def _handle_click(self, target_x: float, target_y: float) -> None:
        for ball in self.balls:
            if not ball.from_player and ball.active:
                dist = math.hypot(ball.x - self.player_x, ball.y - self.player_y)
                if dist < CATCH_RADIUS:
                    self._catch_ball(ball)
                    return
        if self._throw_cooldown <= 0:
            self._throw_ball(target_x, target_y)

    def _update_player_input(self, dt_left: bool, dt_right: bool, dt_up: bool, dt_down: bool) -> None:
        if dt_left:
            self.player_x -= PLAYER_SPEED
        if dt_right:
            self.player_x += PLAYER_SPEED
        if dt_up:
            self.player_y -= PLAYER_SPEED
        if dt_down:
            self.player_y += PLAYER_SPEED
        self.player_x = max(20.0, min(300.0, self.player_x))
        self.player_y = max(165.0, min(220.0, self.player_y))

    # ------------------------------------------------------------------
    # Core game logic (headless-testable)
    # ------------------------------------------------------------------

    def _tick_timers(self) -> None:
        self.game_timer += 1
        if self._throw_cooldown > 0:
            self._throw_cooldown -= 1
        self.heat = max(0.0, self.heat - HEAT_DECAY)
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.combo = 0
        self._update_difficulty()
        if self.game_timer >= GAME_DURATION:
            self.phase = Phase.GAME_OVER
            self._finalize_game()

    def _update_difficulty(self) -> None:
        self._difficulty_timer += 1

    def _throw_ball(self, target_x: float, target_y: float) -> None:
        dx = target_x - self.player_x
        dy = target_y - self.player_y
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            dist = 1.0
        vx = dx / dist * BALL_SPEED
        vy = dy / dist * BALL_SPEED
        color = self.player_color
        ball = Ball(x=self.player_x, y=self.player_y, vx=vx, vy=vy, color=color, from_player=True)
        self.balls.append(ball)
        self.player_color = (self.player_color + 1) % 4
        self._throw_cooldown = THROW_COOLDOWN

    def _catch_ball(self, ball: Ball) -> None:
        self.score += 50
        self.heat = max(0.0, self.heat + HEAT_COOL_CATCH)
        ball.active = False
        self.floating_texts.append(FloatingText("+50", ball.x, ball.y, 30, 10))
        self._spawn_particles(ball.x, ball.y, ball.color, 6)

    def _update_balls(self) -> None:
        for ball in list(self.balls):
            if not ball.active:
                self.balls.remove(ball)
                continue
            ball.x += ball.vx
            ball.y += ball.vy

            if ball.x < -10.0 or ball.x > 330.0 or ball.y < -10.0 or ball.y > 250.0:
                self.balls.remove(ball)
                continue

            if not ball.from_player:
                dist = math.hypot(ball.x - self.player_x, ball.y - self.player_y)
                if dist < PLAYER_RADIUS + BALL_RADIUS:
                    self._player_hit()
                    self.balls.remove(ball)
                    continue

            if ball.from_player:
                for opp in self.opponents:
                    if opp.hit:
                        continue
                    dist = math.hypot(ball.x - opp.x, ball.y - opp.y)
                    if dist < OPPONENT_RADIUS + BALL_RADIUS:
                        self._opponent_hit(opp, ball)
                        self.balls.remove(ball)
                        break

    def _player_hit(self) -> None:
        self.heat += HEAT_HIT
        self.combo = 0
        self.shake_frames = 12
        self._spawn_particles(self.player_x, self.player_y, 8, 4)
        self.floating_texts.append(FloatingText("OUCH!", self.player_x, self.player_y - 10, 30, 8))
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            self._finalize_game()

    def _opponent_hit(self, opp: Opponent, ball: Ball) -> None:
        color_matched = ball.color == opp.color

        if self.super_mode:
            base_score = 30
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            scored = base_score * 3 * self.combo
            self.heat = max(0.0, self.heat + HEAT_COOL_HIT * 2)
        elif color_matched:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            base_score = 10
            scored = base_score * self.combo
            self.heat = max(0.0, self.heat + HEAT_COOL_HIT)
            if self.combo >= SUPER_THRESHOLD:
                self.super_mode = True
                self.super_timer = SUPER_DURATION
                self.shake_frames = 15
                self._spawn_particles(opp.x, opp.y, 10, 20)
                self.floating_texts.append(FloatingText("SUPER!", opp.x, opp.y - 15, 45, 10))
        else:
            scored = 5
            self.combo = 0
            self.heat += HEAT_WRONG_COLOR

        self.score += scored
        opp.hit = True
        opp.respawn_timer = OPPONENT_RESPAWN
        self._spawn_particles(opp.x, opp.y, ball.color, 8)
        self.floating_texts.append(FloatingText(
            f"+{scored}", opp.x, opp.y - 8, 25,
            10 if color_matched or self.super_mode else 8,
        ))

        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            self._finalize_game()

    def _update_opponents(self) -> None:
        diff_scale = self._get_diff_scale()
        for opp in self.opponents:
            if opp.hit:
                opp.respawn_timer -= 1
                if opp.respawn_timer <= 0:
                    opp.hit = False
                    opp.color = self._rng.randint(0, 3)
            else:
                opp.throw_timer -= 1
                if opp.throw_timer <= 0:
                    self._ai_throw(opp, diff_scale)
                    min_t = max(20, int(AI_THROW_MIN * diff_scale))
                    max_t = max(40, int(AI_THROW_MAX * diff_scale))
                    opp.throw_timer = self._rng.randint(min_t, max_t)

    def _get_diff_scale(self) -> float:
        elapsed_sec = self.game_timer / FPS
        if elapsed_sec < 10:
            return 1.0
        return 1.0 - min(0.6, (elapsed_sec - 10) * 0.012)

    def _ai_throw(self, opp: Opponent, diff_scale: float = 1.0) -> None:
        spread = 30.0 * diff_scale + 10.0
        dx = self.player_x - opp.x + self._rng.uniform(-spread, spread)
        dy = self.player_y - opp.y + self._rng.uniform(-10.0, 10.0)
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            dist = 1.0
        vx = dx / dist * BALL_SPEED * 0.85
        vy = dy / dist * BALL_SPEED * 0.85
        color = self._rng.randint(0, 3)
        ball = Ball(x=opp.x, y=opp.y, vx=vx, vy=vy, color=color, from_player=False)
        self.balls.append(ball)

    def _update_particles(self) -> None:
        for p in list(self.particles):
            p.vx *= 0.9
            p.vy *= 0.9
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in list(self.floating_texts):
            ft.y -= 0.5
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0.0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.5)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = self._rng.randint(8, 18)
            self.particles.append(Particle(x, y, vx, vy, color, life))

    def _finalize_game(self) -> None:
        if self.score > self.best_score:
            self.best_score = self.score


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    Game()


if __name__ == "__main__":
    main()
