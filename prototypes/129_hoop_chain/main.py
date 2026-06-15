"""HOOP CHAIN — Top-down color-match basketball shooting prototype."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

import pyxel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCREEN_W = 320
SCREEN_H = 240
HOOP_X = 160
HOOP_Y = 40
HOOP_WIDTH = 40
HOOP_RIM = 3
SHOOTER_X = 160
SHOOTER_Y = 210
GRAVITY = 0.3
MAX_POWER = 12.0
BALL_RADIUS = 6

NUM_COLORS = 4
COLOR_VALS: tuple[int, ...] = (8, 3, 5, 10)  # RED, GREEN, DARK_BLUE, YELLOW
COLOR_NAMES: tuple[str, ...] = ("RED", "GREEN", "DARK_BLUE", "YELLOW")

SUPER_THRESHOLD = 4
SUPER_DURATION = 150  # 5 seconds at 30fps
SUPER_SCORE_MULT = 3

HEAT_MAX = 100.0
HEAT_MISS = 15.0
HEAT_BASKET = -5.0
HEAT_DECAY = 0.02  # per frame

MAX_DEFENDERS = 6
DEFENDER_SPAWN_INTERVAL = 300  # every 10 seconds
DEFENDER_RADIUS = 16
DEFENDER_HP = 2

GAME_DURATION = 1800  # 60s * 30fps

# Pyxel color constants
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


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    color: int  # 0-3 index into COLOR_VALS
    active: bool = True
    trail: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class Defender:
    x: float
    y: float
    radius: float
    hp: int
    color: int


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int
    vy: float = -1.0


# ---------------------------------------------------------------------------
# Phase enum
# ---------------------------------------------------------------------------


class Phase(Enum):
    TITLE = 0
    AIMING = 1
    FLYING = 2
    SCORING = 3
    MISSING = 4
    GAME_OVER = 5


# ---------------------------------------------------------------------------
# Game class
# ---------------------------------------------------------------------------


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="HOOP CHAIN")
        pyxel.mouse(True)
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_mode = False
        self.super_timer = 0
        self.game_timer = GAME_DURATION
        self.balls_shot = 0
        self.ball = None
        self.defenders: list[Defender] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._shake_frames = 0
        self._shake_intensity = 0
        self._last_scored_color = -1
        self._next_ball_color = 0
        self._defender_spawn_timer = DEFENDER_SPAWN_INTERVAL
        self._power_charge = 0.0
        self._charging = False
        self.phase = Phase.AIMING

    # ------------------------------------------------------------------
    # Spawning helpers (testable)
    # ------------------------------------------------------------------

    def _spawn_ball(self) -> Ball:
        color = self._next_ball_color
        self._next_ball_color = (color + 1) % NUM_COLORS
        return Ball(SHOOTER_X, SHOOTER_Y, 0.0, 0.0, color=color)

    def _spawn_particles(
        self, x: float, y: float, count: int, color: int
    ) -> None:
        for _ in range(count):
            speed = self._rng.uniform(1.0, 4.0)
            life = self._rng.randint(10, 25)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=speed * 0.7 * (1 if self._rng.random() > 0.5 else -1),
                    vy=speed * 0.7 * (1 if self._rng.random() > 0.5 else -1),
                    life=life,
                    color=color,
                    size=self._rng.randint(1, 3),
                )
            )

    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=40, color=color)
        )

    # ------------------------------------------------------------------
    # Ball physics (testable)
    # ------------------------------------------------------------------

    def _update_ball(self) -> None:
        ball = self.ball
        if ball is None or not ball.active:
            return
        ball.vy += GRAVITY
        ball.x += ball.vx
        ball.y += ball.vy
        ball.trail.append((ball.x, ball.y))
        if len(ball.trail) > 8:
            ball.trail = ball.trail[-8:]

        # Ball misses if below screen margin
        if ball.y > SCREEN_H + 20:
            ball.active = False
            return

        # Bounce off left/right/top edges (not bottom — falling below is a miss)
        restitution = 0.7
        if ball.x - BALL_RADIUS < 0:
            ball.x = BALL_RADIUS
            ball.vx = abs(ball.vx) * restitution
        if ball.x + BALL_RADIUS > SCREEN_W:
            ball.x = SCREEN_W - BALL_RADIUS
            ball.vx = -abs(ball.vx) * restitution
        if ball.y - BALL_RADIUS < 0:
            ball.y = BALL_RADIUS
            ball.vy = abs(ball.vy) * restitution

    def _check_hoop_score(self) -> bool:
        ball = self.ball
        if ball is None or not ball.active:
            return False
        in_hoop_x = (
            HOOP_X - HOOP_WIDTH // 2 < ball.x < HOOP_X + HOOP_WIDTH // 2
        )
        in_hoop_y = ball.y < HOOP_Y + 5 and ball.vy < 0
        return in_hoop_x and in_hoop_y

    def _check_defender_collision(self) -> bool:
        ball = self.ball
        if ball is None or not ball.active:
            return False
        for defender in self.defenders:
            dx = ball.x - defender.x
            dy = ball.y - defender.y
            dist = (dx * dx + dy * dy) ** 0.5
            min_dist = BALL_RADIUS + defender.radius
            if dist < min_dist:
                # Push ball out
                if dist > 0:
                    nx = dx / dist
                    ny = dy / dist
                    overlap = min_dist - dist
                    ball.x += nx * overlap
                    ball.y += ny * overlap
                # Reflect ball
                ball.vx = (ball.vx * 0.7) * -1 if abs(ball.vx) > 0 else 0
                ball.vy = abs(ball.vy * 0.7) + 1.0
                return True
        return False

    # ------------------------------------------------------------------
    # Score / Miss handling (testable)
    # ------------------------------------------------------------------

    def _handle_score(self) -> None:
        ball = self.ball
        if ball is None:
            return
        color = ball.color
        last = self._last_scored_color

        if self.super_mode or (last == color):
            self.combo += 1
            self.heat = max(0.0, self.heat + HEAT_BASKET)
        else:
            self.combo = 1
            self.heat = max(0.0, self.heat + HEAT_BASKET)

        mult = SUPER_SCORE_MULT if self.super_mode else 1
        base = 10 * self.combo * mult
        self.score += base
        self._last_scored_color = color
        self.max_combo = max(self.max_combo, self.combo)

        # Check super mode activation
        if self.combo >= SUPER_THRESHOLD and not self.super_mode:
            self.super_mode = True
            self.super_timer = SUPER_DURATION

        # Particles and text
        col = COLOR_VALS[color]
        self._spawn_particles(HOOP_X, HOOP_Y - 5, 10, col)
        txt = f"+{base}"
        if self.combo > 1:
            txt += f" x{self.combo}"
        self._spawn_floating_text(HOOP_X, HOOP_Y - 15, txt, col)
        if self.combo >= SUPER_THRESHOLD and self.super_timer == SUPER_DURATION:
            self._spawn_floating_text(
                HOOP_X, HOOP_Y - 30, "SUPER!", YELLOW
            )
            self._spawn_particles(HOOP_X, HOOP_Y - 5, 20, YELLOW)

    def _handle_miss(self) -> None:
        self.combo = 0
        self.heat = min(HEAT_MAX, self.heat + HEAT_MISS)
        self._last_scored_color = -1

        ball = self.ball
        if ball is not None:
            self._spawn_particles(ball.x, ball.y, 4, GRAY)
            self._spawn_floating_text(ball.x, ball.y, "MISS", GRAY)

    # ------------------------------------------------------------------
    # Defender management (testable)
    # ------------------------------------------------------------------

    def _update_defenders(self) -> None:
        # Spawn new defenders
        if not self.super_mode:
            self._defender_spawn_timer -= 1
            if self._defender_spawn_timer <= 0 and len(self.defenders) < MAX_DEFENDERS:
                self._defender_spawn_timer = DEFENDER_SPAWN_INTERVAL
                color = self._rng.randint(0, NUM_COLORS - 1)
                x = self._rng.uniform(HOOP_X - HOOP_WIDTH * 2, HOOP_X + HOOP_WIDTH * 2)
                self.defenders.append(
                    Defender(
                        x=x,
                        y=HOOP_Y + 30 + self._rng.uniform(0, 40),
                        radius=DEFENDER_RADIUS,
                        hp=DEFENDER_HP,
                        color=color,
                    )
                )

        # Move defenders downward slowly
        for d in self.defenders:
            d.y += 0.15

        # Remove defenders that go off-screen
        self.defenders = [d for d in self.defenders if d.y < SCREEN_H + 30]

    def _handle_defender_hit(self, defender: Defender) -> None:
        if self.super_mode:
            defender.hp = 0
        else:
            defender.hp -= 1
        if defender.hp <= 0:
            col = COLOR_VALS[defender.color]
            self._spawn_particles(defender.x, defender.y, 12, col)
            self._spawn_floating_text(defender.x, defender.y, "+50", col)
            self.score += 50

        # Remove dead defenders
        self.defenders = [d for d in self.defenders if d.hp > 0]

    # ------------------------------------------------------------------
    # Super mode / heat (testable)
    # ------------------------------------------------------------------

    def _update_super_mode(self) -> None:
        if not self.super_mode:
            return
        self.super_timer -= 1
        if self.super_timer <= 0:
            self.super_mode = False
            self.super_timer = 0
            self.combo = 0
            self._last_scored_color = -1

    def _update_heat(self) -> None:
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _check_game_over(self) -> bool:
        return self.heat >= HEAT_MAX or self.game_timer <= 0

    # ------------------------------------------------------------------
    # Update / Draw
    # ------------------------------------------------------------------

    def update(self) -> None:
        # Screen shake countdown
        if self._shake_frames > 0:
            self._shake_frames -= 1
            return  # skip update during shake

        match self.phase:
            case Phase.TITLE:
                if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                    self.reset()
                    self.phase = Phase.AIMING

            case Phase.AIMING:
                self._update_defenders()
                self._update_super_mode()
                self._update_heat()
                if self.game_timer > 0:
                    self.game_timer -= 1

                if self._check_game_over():
                    self.phase = Phase.GAME_OVER
                    self._shake_frames = 15
                    self._shake_intensity = 8
                    self.ball = None
                    return

                mx = pyxel.mouse_x
                my = pyxel.mouse_y

                if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
                    if not self._charging:
                        self._charging = True
                        self._power_charge = 0.0
                    self._power_charge = min(MAX_POWER, self._power_charge + 0.4)

                if pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT) and self._charging:
                    # Shoot
                    dx = mx - SHOOTER_X
                    dy = my - SHOOTER_Y
                    dist = max(1.0, (dx * dx + dy * dy) ** 0.5)
                    power = self._power_charge
                    self.ball = self._spawn_ball()
                    self.ball.vx = (dx / dist) * power * 0.8
                    self.ball.vy = (dy / dist) * power * 0.8
                    self.balls_shot += 1
                    self._power_charge = 0.0
                    self._charging = False
                    self.phase = Phase.FLYING

            case Phase.FLYING:
                self._update_ball()
                self._update_defenders()
                self._update_super_mode()
                self._update_heat()
                if self.game_timer > 0:
                    self.game_timer -= 1

                ball = self.ball
                if ball is None or not ball.active:
                    self._handle_miss()
                    self.phase = Phase.MISSING
                    self._shake_frames = 6
                    self._shake_intensity = 3
                    self.ball = None
                    return

                # Check defender collision
                if self._check_defender_collision():
                    # Find which defender was hit
                    for d in self.defenders[:]:
                        dx = ball.x - d.x
                        dy = ball.y - d.y
                        if (dx * dx + dy * dy) ** 0.5 < BALL_RADIUS + d.radius + 5:
                            self._handle_defender_hit(d)

                # Check hoop scoring
                if self._check_hoop_score():
                    self._handle_score()
                    self.phase = Phase.SCORING
                    self.ball = None

                if self._check_game_over():
                    self.phase = Phase.GAME_OVER
                    self._shake_frames = 15
                    self._shake_intensity = 8
                    self.ball = None

            case Phase.SCORING:
                # Quick transition phase: show fx then go to AIMING
                self._update_particles_and_texts()
                if not self.particles and not self.floating_texts:
                    if self._check_game_over():
                        self.phase = Phase.GAME_OVER
                        self._shake_frames = 15
                        self._shake_intensity = 8
                    else:
                        self.phase = Phase.AIMING

            case Phase.MISSING:
                self._update_particles_and_texts()
                if not self.particles and not self.floating_texts:
                    if self._check_game_over():
                        self.phase = Phase.GAME_OVER
                        self._shake_frames = 15
                        self._shake_intensity = 8
                    else:
                        self.phase = Phase.AIMING

            case Phase.GAME_OVER:
                if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                    self.reset()
                    self.phase = Phase.TITLE

        # Always update particles/texts (except during shake)
        if self._shake_frames == 0:
            self._update_particles_and_texts()

    def _update_particles_and_texts(self) -> None:
        for p in self.particles:
            p.vy += 0.1
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def draw(self) -> None:
        # Apply screen shake
        shake_x = shake_y = 0
        if self._shake_frames > 0:
            shake_x = self._rng.randint(-self._shake_intensity, self._shake_intensity)
            shake_y = self._rng.randint(-self._shake_intensity, self._shake_intensity)
            try:
                pyxel.camera(shake_x, shake_y)
            except BaseException:
                pass
        else:
            try:
                pyxel.camera(0, 0)
            except BaseException:
                pass

        pyxel.cls(NAVY)

        match self.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.AIMING | Phase.FLYING | Phase.SCORING | Phase.MISSING:
                self._draw_court()
                self._draw_hoop()
                self._draw_shooter()
                self._draw_defenders()
                self._draw_hud()
                self._draw_power_bar()
                self._draw_heat_bar()
                self._draw_super_mode_indicator()
                self._draw_particles_and_texts()

                ball = self.ball
                if ball is not None and ball.active:
                    self._draw_ball(ball)
            case Phase.GAME_OVER:
                self._draw_game_over()

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _draw_title(self) -> None:
        pyxel.text(85, 70, "HOOP CHAIN", WHITE)
        pyxel.text(110, 100, "Color-Match", LIGHT_BLUE)
        pyxel.text(95, 110, "Basketball Shooting", LIGHT_BLUE)
        pyxel.text(90, 150, "Click to Start", YELLOW)
        pyxel.text(70, 180, "Mouse: Aim + Shoot", GRAY)
        pyxel.text(65, 190, "Same-color baskets build COMBO", GRAY)
        pyxel.text(60, 200, "COMBO x4 triggers SUPER SHOT!", ORANGE)

    def _draw_court(self) -> None:
        # Court outline
        pyxel.rectb(20, 20, SCREEN_W - 40, SCREEN_H - 40, WHITE)
        # Three-point arc suggestion
        pyxel.line(40, 140, 160, 200, GRAY)
        pyxel.line(280, 140, 160, 200, GRAY)

    def _draw_hoop(self) -> None:
        left_x = HOOP_X - HOOP_WIDTH // 2
        right_x = HOOP_X + HOOP_WIDTH // 2
        # Rim
        pyxel.line(left_x, HOOP_Y, right_x, HOOP_Y, WHITE)
        # Left post
        pyxel.line(left_x, HOOP_Y, left_x, HOOP_Y + 15, WHITE)
        # Right post
        pyxel.line(right_x, HOOP_Y, right_x, HOOP_Y + 15, WHITE)
        # Rims
        pyxel.rect(left_x - 2, HOOP_Y - 3, 5, 3, WHITE)
        pyxel.rect(right_x - 2, HOOP_Y - 3, 5, 3, WHITE)
        # Net hint
        for i in range(3):
            ny = HOOP_Y + 5 + i * 4
            pyxel.line(left_x + 4, ny + 1, HOOP_X, ny + 2, GRAY)
            pyxel.line(right_x - 4, ny + 1, HOOP_X, ny + 2, GRAY)

    def _draw_shooter(self) -> None:
        pyxel.circ(SHOOTER_X, SHOOTER_Y, 8, WHITE)
        pyxel.circ(SHOOTER_X, SHOOTER_Y, 6, PEACH)

    def _draw_ball(self, ball: Ball) -> None:
        col = COLOR_VALS[ball.color]
        # Trail
        for i, (tx, ty) in enumerate(ball.trail):
            alpha = int((i + 1) / len(ball.trail) * 3)
            pyxel.circ(int(tx), int(ty), BALL_RADIUS - alpha, col)
        # Super mode rainbow cycling
        if self.super_mode:
            col = COLOR_VALS[(pyxel.frame_count // 3) % NUM_COLORS]
        pyxel.circ(int(ball.x), int(ball.y), BALL_RADIUS, col)
        pyxel.circ(int(ball.x), int(ball.y), BALL_RADIUS - 1, WHITE)

    def _draw_defenders(self) -> None:
        for d in self.defenders:
            col = COLOR_VALS[d.color]
            pyxel.circb(int(d.x), int(d.y), int(d.radius), col)
            pyxel.circb(int(d.x), int(d.y), int(d.radius) - 4, col)
            # HP indicator
            if d.hp > 1:
                pyxel.circ(int(d.x), int(d.y), 3, col)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"Score:{self.score:06d}", WHITE)
        sec = self.game_timer // 30
        pyxel.text(SCREEN_W - 60, 4, f"Time:{sec:02d}", WHITE)
        if self.combo > 1:
            combo_txt = f"COMBO x{self.combo}"
            pyxel.text(HOOP_X - 20 if self.combo < 10 else HOOP_X - 25, HOOP_Y + 25, combo_txt, ORANGE)

    def _draw_power_bar(self) -> None:
        if not self._charging:
            return
        bar_x = SHOOTER_X - 20
        bar_y = SHOOTER_Y + 15
        bar_w = 40
        bar_h = 6
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        fill_w = int(bar_w * (self._power_charge / MAX_POWER))
        bar_col = GREEN if self._power_charge < MAX_POWER * 0.5 else YELLOW if self._power_charge < MAX_POWER * 0.8 else RED
        pyxel.rect(bar_x + 1, bar_y + 1, fill_w - 1, bar_h - 1, bar_col)

    def _draw_heat_bar(self) -> None:
        bar_x = 60
        bar_y = SCREEN_H - 12
        bar_w = 200
        bar_h = 6
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        fill_w = int(bar_w * (self.heat / HEAT_MAX))
        if self.heat < 30:
            col = GREEN
        elif self.heat < 60:
            col = YELLOW
        elif self.heat < 85:
            col = ORANGE
        else:
            col = RED
        pyxel.rect(bar_x + 1, bar_y + 1, fill_w - 1, bar_h - 1, col)
        pyxel.text(bar_x - 30, bar_y - 1, "HEAT", GRAY)

    def _draw_super_mode_indicator(self) -> None:
        if not self.super_mode:
            return
        frames_left = self.super_timer / SUPER_DURATION
        # Border flash
        if pyxel.frame_count % 4 < 2:
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, YELLOW)
        pyxel.text(SCREEN_W - 90, 12, "SUPER MODE!", YELLOW)
        # Timer bar
        bar_w = 80
        bar_h = 4
        bar_x = SCREEN_W - 90
        bar_y = 20
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        pyxel.rect(bar_x + 1, bar_y + 1, int(bar_w * frames_left) - 1, bar_h - 1, YELLOW)

    def _draw_particles_and_texts(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)
        for ft in self.floating_texts:
            ft_color = ft.color if ft.life > 20 else GRAY
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft_color)

    def _draw_game_over(self) -> None:
        pyxel.text(100, 70, "GAME OVER", RED)
        pyxel.text(90, 95, f"Score: {self.score}", WHITE)
        pyxel.text(90, 110, f"Max Combo: {self.max_combo}", ORANGE)
        pyxel.text(90, 125, f"Balls Shot: {self.balls_shot}", LIGHT_BLUE)
        if self.heat >= HEAT_MAX:
            pyxel.text(70, 145, "Overheated!", RED)
        else:
            pyxel.text(70, 145, "Time's Up!", RED)
        pyxel.text(85, 175, "Click to Retry", YELLOW)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
