"""PING PONG SURGE - Top-down table tennis with color-matching mechanics.

The most fun moment: hitting a 5+ COMBO chain to enter SUPER RALLY mode where
all returns auto-match for 5 seconds with 3x score and rainbow particles.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel


# ============================================================
# Enums and Data Classes
# ============================================================


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class BallColor(Enum):
    RED = 0
    GREEN = 1
    BLUE = 2
    YELLOW = 3


BALL_COLORS: tuple[int, int, int, int] = (8, 3, 5, 10)  # RED, GREEN, DARK_BLUE, YELLOW
RAINBOW: tuple[int, ...] = (8, 9, 10, 11, 12, 14, 15)


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    color: int  # BallColor index 0-3
    speed: float


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


# ============================================================
# Game Logic (pure, testable — no pyxel input calls)
# ============================================================


class Game:
    SCREEN_W: ClassVar[int] = 320
    SCREEN_H: ClassVar[int] = 240
    PADDLE_Y: ClassVar[int] = 210
    AI_PADDLE_Y: ClassVar[int] = 30
    PADDLE_W: ClassVar[int] = 40
    PADDLE_H: ClassVar[int] = 8
    BALL_RADIUS: ClassVar[int] = 6
    NET_Y: ClassVar[int] = 120
    MAX_HEAT: ClassVar[int] = 100
    COMBO_FOR_SUPER: ClassVar[int] = 5
    SUPER_DURATION: ClassVar[int] = 300
    OVERHEAT_DURATION: ClassVar[int] = 300
    GAME_TIME: ClassVar[int] = 3600
    INITIAL_SPEED: ClassVar[float] = 3.0
    MAX_SPEED: ClassVar[float] = 10.0

    def __init__(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.high_score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.ball: Ball | None = None
        self.paddle_x: float = 0.0
        self.paddle_color: int = 0
        self.ai_paddle_x: float = 0.0
        self.ai_paddle_color: int = 0
        self.heat: float = 0.0
        self.overheat_timer: int = 0
        self.super_timer: int = 0
        self.particles: list[Particle] = []
        self.shake_offset_x: int = 0
        self.shake_offset_y: int = 0
        self.rally_count: int = 0
        self.serve_ready: bool = True
        self.game_timer: int = 0
        self._frame: int = 0
        self._ai_color_timer: int = 0
        self._overheat_color_timer: int = 0

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.ball = None
        self.paddle_x = self.SCREEN_W / 2 - self.PADDLE_W / 2
        self.paddle_color = 0
        self.ai_paddle_x = self.SCREEN_W / 2 - self.PADDLE_W / 2
        self.ai_paddle_color = 2
        self.heat = 0.0
        self.overheat_timer = 0
        self.super_timer = 0
        self.particles.clear()
        self.shake_offset_x = 0
        self.shake_offset_y = 0
        self.rally_count = 0
        self.serve_ready = True
        self.game_timer = self.GAME_TIME
        self._frame = 0
        self._ai_color_timer = 0
        self._overheat_color_timer = 0

    # --- Paddle Movement ---

    def _move_paddle(self, target_x: float) -> None:
        self.paddle_x = target_x - self.PADDLE_W / 2
        self.paddle_x = max(0.0, min(float(self.SCREEN_W - self.PADDLE_W), self.paddle_x))

    def _move_ai_paddle(self) -> None:
        if self.ball is not None:
            target = self.ball.x - self.PADDLE_W / 2
        else:
            target = self.SCREEN_W / 2 - self.PADDLE_W / 2

        diff = target - self.ai_paddle_x
        max_step: float = 2.5
        if abs(diff) < max_step:
            self.ai_paddle_x = target
        else:
            self.ai_paddle_x += max_step if diff > 0 else -max_step
        self.ai_paddle_x = max(0.0, min(float(self.SCREEN_W - self.PADDLE_W), self.ai_paddle_x))

        self._ai_color_timer += 1
        if self._ai_color_timer >= 90:
            self._ai_color_timer = 0
            self.ai_paddle_color = random.randint(0, 3)

    def _cycle_paddle_color(self, direction: int) -> None:
        self.paddle_color = (self.paddle_color + direction) % 4

    # --- Ball ---

    def _serve_ball(self) -> None:
        angle = random.uniform(-0.4, 0.4)
        speed = self.INITIAL_SPEED + self.rally_count * 0.08
        self.ball = Ball(
            x=self.SCREEN_W / 2,
            y=self.NET_Y,
            vx=math.sin(angle) * speed * 0.5,
            vy=speed * 0.7,
            color=random.randint(0, 3),
            speed=speed,
        )
        self.serve_ready = False

    def _update_ball(self) -> None:
        if self.ball is None:
            return

        ball = self.ball
        ball.x += ball.vx
        ball.y += ball.vy

        # Bounce off left/right walls
        if ball.x - self.BALL_RADIUS < 0:
            ball.x = self.BALL_RADIUS
            ball.vx = abs(ball.vx)
        elif ball.x + self.BALL_RADIUS > self.SCREEN_W:
            ball.x = self.SCREEN_W - self.BALL_RADIUS
            ball.vx = -abs(ball.vx)

        # Bounce off top wall (AI side boundary)
        if ball.y - self.BALL_RADIUS < 0:
            ball.y = self.BALL_RADIUS
            ball.vy = abs(ball.vy)

        # Check paddle collisions based on direction
        if ball.vy > 0:
            self._check_paddle_hit()
        elif ball.vy < 0:
            self._check_ai_hit()

        # Miss: ball exits player side
        if ball.y - self.BALL_RADIUS > self.SCREEN_H:
            self._on_miss()

    def _check_paddle_hit(self) -> None:
        if self.ball is None:
            return
        ball = self.ball
        if ball.vy <= 0:
            return

        pad_l = self.paddle_x - self.BALL_RADIUS
        pad_r = self.paddle_x + self.PADDLE_W + self.BALL_RADIUS
        pad_t = self.PADDLE_Y - self.PADDLE_H // 2 - self.BALL_RADIUS
        pad_b = self.PADDLE_Y + self.PADDLE_H // 2 + self.BALL_RADIUS

        if pad_l <= ball.x <= pad_r and pad_t <= ball.y <= pad_b:
            self._process_hit(is_player=True)

    def _check_ai_hit(self) -> None:
        if self.ball is None:
            return
        ball = self.ball
        if ball.vy >= 0:
            return

        pad_l = self.ai_paddle_x - self.BALL_RADIUS
        pad_r = self.ai_paddle_x + self.PADDLE_W + self.BALL_RADIUS
        pad_t = self.AI_PADDLE_Y - self.PADDLE_H // 2 - self.BALL_RADIUS
        pad_b = self.AI_PADDLE_Y + self.PADDLE_H // 2 + self.BALL_RADIUS

        if pad_l <= ball.x <= pad_r and pad_t <= ball.y <= pad_b:
            self._process_hit(is_player=False)

    def _process_hit(self, is_player: bool) -> None:
        if self.ball is None:
            return

        ball = self.ball

        pad_x = self.paddle_x if is_player else self.ai_paddle_x
        pad_color = self.paddle_color if is_player else self.ai_paddle_color
        pad_y = self.PADDLE_Y if is_player else self.AI_PADDLE_Y

        color_match = (
            pad_color == ball.color
            or (is_player and self.super_timer > 0)
        )
        dist_from_center = abs(ball.x - (pad_x + self.PADDLE_W / 2))
        is_smash = dist_from_center < self.PADDLE_W / 4 and ball.speed > 3.5

        if is_player:
            if color_match:
                self.combo += 1
                if self.combo > self.max_combo:
                    self.max_combo = self.combo

                multiplier = 1.0 + max(0, self.combo - 1) * 0.5
                if self.super_timer > 0:
                    multiplier *= 3.0
                base_score = 15 if is_smash else 10
                self.score += int(base_score * multiplier)

                if self.super_timer == 0:
                    self.heat += 20.0 if is_smash else 5.0

                if self.combo >= self.COMBO_FOR_SUPER and self.super_timer == 0:
                    self.super_timer = self.SUPER_DURATION

                p_count = 30 if self.super_timer > 0 else 20
                if self.super_timer > 0:
                    p_color = random.choice(RAINBOW)
                else:
                    p_color = BALL_COLORS[ball.color]
                self._spawn_particles(ball.x, ball.y, p_color, p_count)
            else:
                self.combo = 0
                self._spawn_particles(ball.x, ball.y, 8, 8)
                ball.speed = max(self.INITIAL_SPEED - 1.0, ball.speed - 0.5)

            self.rally_count += 1
        else:
            if color_match:
                self._spawn_particles(ball.x, ball.y, BALL_COLORS[self.ai_paddle_color], 10)
            elif random.random() < 0.3:
                self._spawn_particles(ball.x, ball.y, 8, 4)

        # Ramp ball speed
        ball.speed = min(self.MAX_SPEED, self.INITIAL_SPEED + self.rally_count * 0.08)

        # Reflect ball based on hit position
        angle_ratio = (ball.x - pad_x - self.PADDLE_W / 2) / (self.PADDLE_W / 2)
        angle = angle_ratio * 0.7
        ball.vx = math.sin(angle) * ball.speed
        if is_player:
            ball.vy = -abs(ball.speed * 0.75)
            ball.y = pad_y - self.PADDLE_H // 2 - self.BALL_RADIUS - 1
        else:
            ball.vy = abs(ball.speed * 0.75)
            ball.y = pad_y + self.PADDLE_H // 2 + self.BALL_RADIUS + 1

        # Cycle ball color on every hit
        ball.color = random.randint(0, 3)

    def _on_miss(self) -> None:
        if self.score > self.high_score:
            self.high_score = self.score
        self.phase = Phase.GAME_OVER

    # --- Heat ---

    def _update_heat(self) -> None:
        if self.overheat_timer > 0:
            self.overheat_timer -= 1
            if self.overheat_timer == 0:
                self.heat = 0.0
            return

        if self.heat >= self.MAX_HEAT:
            self.overheat_timer = self.OVERHEAT_DURATION
            self.heat = float(self.MAX_HEAT)
        self.heat = max(0.0, self.heat - 0.2)

    def _update_shake(self) -> None:
        if self.overheat_timer > 0:
            self.shake_offset_x = random.randint(-3, 3)
            self.shake_offset_y = random.randint(-3, 3)
            self._overheat_color_timer += 1
            if self._overheat_color_timer >= 30:
                self._overheat_color_timer = 0
                self.paddle_color = random.randint(0, 3)
        else:
            self.shake_offset_x = 0
            self.shake_offset_y = 0
            self._overheat_color_timer = 0

    # --- Super ---

    def _update_super_timer(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1

    # --- Particles ---

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=random.uniform(-2.0, 2.0),
                    vy=random.uniform(-2.0, 2.0),
                    life=random.randint(15, 30),
                    color=color,
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # --- Main Update ---

    def update(self) -> None:
        if self.phase != Phase.PLAYING:
            return

        self._frame += 1
        self._move_ai_paddle()
        self._update_particles()

        if self.serve_ready:
            return

        if self.game_timer > 0:
            self.game_timer -= 1
        if self.game_timer == 0:
            self._on_miss()
            return

        self._update_ball()
        self._update_heat()
        self._update_shake()
        self._update_super_timer()


# ============================================================
# Pyxel App (handles drawing and input)
# ============================================================


class App:
    def __init__(self) -> None:
        pyxel.init(Game.SCREEN_W, Game.SCREEN_H, title="PING PONG SURGE")
        self.game = Game()
        self._wheel_acc: int = 0
        pyxel.run(self._update, self._draw)

    # --- Update ---

    def _update(self) -> None:
        game = self.game

        if game.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE):
                game.reset()
            return

        if game.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE):
                game.phase = Phase.TITLE
            return

        # === PLAYING ===

        if game.serve_ready:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE):
                game._serve_ball()
        else:
            game._move_paddle(float(pyxel.mouse_x))

            wheel = pyxel.mouse_wheel
            self._wheel_acc += wheel
            while self._wheel_acc <= -1:
                game._cycle_paddle_color(-1)
                self._wheel_acc += 1
            while self._wheel_acc >= 1:
                game._cycle_paddle_color(1)
                self._wheel_acc -= 1

            if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A):
                game._cycle_paddle_color(-1)
            if pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D):
                game._cycle_paddle_color(1)

        game.update()

    # --- Draw ---

    def _draw(self) -> None:
        pyxel.cls(0)

        game = self.game
        if game.phase == Phase.TITLE:
            self._draw_title()
        elif game.phase == Phase.GAME_OVER:
            self._draw_game_over()
        else:
            self._draw_play()

        # Draw particles on top of everything
        if game.phase == Phase.PLAYING:
            self._draw_particles()

    def _draw_title(self) -> None:
        game = self.game

        # Table background
        pyxel.rect(0, 0, Game.SCREEN_W, Game.SCREEN_H, 5)

        title = "PING PONG SURGE"
        title_w = len(title) * 4
        pyxel.text(Game.SCREEN_W // 2 - title_w // 2, 50, title, 7)

        # Subtitle
        sub = "Color-Match Table Tennis"
        sub_w = len(sub) * 4
        pyxel.text(Game.SCREEN_W // 2 - sub_w // 2, 66, sub, 10)

        # High score
        if game.high_score > 0:
            hs_text = f"HIGH SCORE: {game.high_score}"
            hs_w = len(hs_text) * 4
            pyxel.text(Game.SCREEN_W // 2 - hs_w // 2, 86, hs_text, 9)

        # Controls
        controls = [
            "MOUSE MOVE   - Control Paddle",
            "MOUSE WHEEL  - Cycle Color",
            "LEFT/RIGHT   - Cycle Color",
            "CLICK/SPACE  - Serve / Start",
            "",
            "MATCH paddle color to ball color",
            "Build 5+ COMBO for SUPER RALLY!",
            "Smash shots score more but build HEAT",
            "OVERHEAT = Loss of control",
        ]
        y = 110
        for line in controls:
            pyxel.text(24, y, line, 7)
            y += 10

        # Blink prompt
        if pyxel.frame_count % 60 < 40:
            prompt = "CLICK OR PRESS SPACE TO START"
            p_w = len(prompt) * 4
            pyxel.text(Game.SCREEN_W // 2 - p_w // 2, 222, prompt, 10)

    def _draw_game_over(self) -> None:
        game = self.game

        # Table background
        pyxel.rect(0, 0, Game.SCREEN_W, Game.SCREEN_H, 5)

        go_text = "GAME OVER"
        go_w = len(go_text) * 4
        pyxel.text(Game.SCREEN_W // 2 - go_w // 2, 60, go_text, 8)

        # Stats
        score_text = f"SCORE: {game.score}"
        sw = len(score_text) * 4
        pyxel.text(Game.SCREEN_W // 2 - sw // 2, 90, score_text, 7)

        combo_text = f"MAX COMBO: {game.max_combo}"
        cw = len(combo_text) * 4
        pyxel.text(Game.SCREEN_W // 2 - cw // 2, 104, combo_text, 10)

        rally_text = f"RALLIES: {game.rally_count}"
        rw = len(rally_text) * 4
        pyxel.text(Game.SCREEN_W // 2 - rw // 2, 118, rally_text, 7)

        # High score
        if game.score >= game.high_score and game.score > 0:
            hs = "NEW HIGH SCORE!"
            hw = len(hs) * 4
            pyxel.text(Game.SCREEN_W // 2 - hw // 2, 140, hs, 9)
        elif game.high_score > 0:
            hs = f"HIGH SCORE: {game.high_score}"
            hw = len(hs) * 4
            pyxel.text(Game.SCREEN_W // 2 - hw // 2, 140, hs, 7)

        # Blink prompt
        if pyxel.frame_count % 60 < 40:
            prompt = "CLICK OR PRESS SPACE TO RETRY"
            pw = len(prompt) * 4
            pyxel.text(Game.SCREEN_W // 2 - pw // 2, 222, prompt, 10)

    def _draw_play(self) -> None:
        game = self.game

        # Apply shake via camera
        pyxel.camera(game.shake_offset_x, game.shake_offset_y)

        # Table
        pyxel.rect(0, 0, Game.SCREEN_W, Game.SCREEN_H, 5)

        # Net (dashed line)
        dash_len = 6
        for x in range(0, Game.SCREEN_W, dash_len * 2):
            pyxel.rect(x, Game.NET_Y, dash_len, 1, 7)

        # Super rally border flash
        if game.super_timer > 0:
            flash_color = RAINBOW[(pyxel.frame_count // 4) % len(RAINBOW)]
            pyxel.rectb(0, 0, Game.SCREEN_W, Game.SCREEN_H, flash_color)

        # AI paddle
        pyxel.rect(
            int(game.ai_paddle_x),
            Game.AI_PADDLE_Y - Game.PADDLE_H // 2,
            Game.PADDLE_W,
            Game.PADDLE_H,
            BALL_COLORS[game.ai_paddle_color],
        )

        # Player paddle (with overheat tint)
        p_color = BALL_COLORS[game.paddle_color]
        if game.overheat_timer > 0 and pyxel.frame_count % 6 < 3:
            p_color = 8  # flash red
        pyxel.rect(
            int(game.paddle_x),
            Game.PADDLE_Y - Game.PADDLE_H // 2,
            Game.PADDLE_W,
            Game.PADDLE_H,
            p_color,
        )

        # Ball
        if game.ball is not None:
            ball = game.ball
            b_color = BALL_COLORS[ball.color]
            if game.super_timer > 0:
                # Rainbow trail
                pyxel.circ(
                    int(ball.x - ball.vx * 2),
                    int(ball.y - ball.vy * 2),
                    Game.BALL_RADIUS - 2,
                    RAINBOW[(pyxel.frame_count // 3) % len(RAINBOW)],
                )
            pyxel.circ(int(ball.x), int(ball.y), Game.BALL_RADIUS, b_color)
            # Ball outline for visibility
            pyxel.circb(int(ball.x), int(ball.y), Game.BALL_RADIUS, 7)

        # Serve prompt
        if game.serve_ready:
            if pyxel.frame_count % 60 < 40:
                prompt = "CLICK TO SERVE"
                pw = len(prompt) * 4
                pyxel.text(Game.SCREEN_W // 2 - pw // 2, Game.NET_Y - 8, prompt, 10)

        # Reset camera
        pyxel.camera(0, 0)

        # --- HUD (no shake) ---

        # Score (top-left)
        pyxel.text(4, 4, f"SCORE: {game.score}", 7)

        # Combo (top-right)
        if game.combo > 0:
            combo_text = f"COMBO x{game.combo}"
            cw = len(combo_text) * 4
            c_color = 9 if game.combo < game.COMBO_FOR_SUPER else 8
            pyxel.text(Game.SCREEN_W - cw - 4, 4, combo_text, c_color)

        # Max combo (below combo)
        if game.max_combo > 0:
            mc_text = f"MAX: {game.max_combo}"
            mcw = len(mc_text) * 4
            pyxel.text(Game.SCREEN_W - mcw - 4, 14, mc_text, 12)

        # Heat bar (bottom-left)
        bar_x = 4
        bar_y = Game.SCREEN_H - 14
        bar_w = 60
        bar_h = 6
        pyxel.rectb(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2, 7)
        heat_fill = int(bar_w * game.heat / Game.MAX_HEAT)
        heat_color = 8 if game.overheat_timer > 0 else (
            9 if game.heat > 60 else 10
        )
        if heat_fill > 0:
            pyxel.rect(bar_x, bar_y, heat_fill, bar_h, heat_color)
        pyxel.text(4, bar_y - 8, "HEAT", 7)

        # Super timer (bottom)
        if game.super_timer > 0:
            sec_left = game.super_timer // 60 + 1
            super_text = f"SUPER RALLY {sec_left}s"
            sw = len(super_text) * 4
            pyxel.text(Game.SCREEN_W // 2 - sw // 2, Game.SCREEN_H - 10, super_text, 9)

        # Overheat (bottom-center-right)
        if game.overheat_timer > 0:
            oh_text = "OVERHEAT!"
            ow = len(oh_text) * 4
            pyxel.text(Game.SCREEN_W - ow - 4, Game.SCREEN_H - 10, oh_text, 8)

        # Game timer (top-center)
        sec = game.game_timer // 60
        timer_text = f"{sec // 60}:{sec % 60:02d}"
        tw = len(timer_text) * 4
        t_color = 7 if sec > 10 else 8
        pyxel.text(Game.SCREEN_W // 2 - tw // 2, 4, timer_text, t_color)

    def _draw_particles(self) -> None:
        for p in self.game.particles:
            alpha = p.life / 30
            size = max(1, int(3 * alpha))
            # Simulate fade by choosing darker color for older particles
            pyxel.circ(int(p.x), int(p.y), size, p.color)


if __name__ == "__main__":
    App()
