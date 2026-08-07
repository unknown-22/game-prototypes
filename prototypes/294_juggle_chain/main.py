from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

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

SCREEN_W = 320
SCREEN_H = 240
FPS = 60

CATCH_Y = 210
CATCH_ZONE_HALF_W = 30
CATCH_H = 30
PLAYER_X = SCREEN_W // 2  # fixed catch zone center X
BALL_RADIUS = 6
BALL_VX_MAX = 1.5
BALL_VY_LAUNCH = -8.0
GRAVITY = 0.25

HEAT_MAX = 100.0
HEAT_MISMATCH = 15.0
HEAT_DROP = 10.0
HEAT_DECAY = 0.02

SUPER_DURATION = 300
SUPER_SCORE_MULT = 3
COMBO_SUPER_THRESHOLD = 4

GAME_TIME = 60 * FPS  # 3600 frames

INITIAL_BALLS = 3
MAX_BALLS_START = 3
MAX_BALLS_END = 5
MIN_SPAWN_INTERVAL = 30
MAX_SPAWN_INTERVAL = 60
INITIAL_CYCLE_SPEED = 20
MIN_CYCLE_SPEED = 12

COLORS = (RED, LIME, DARK_BLUE, YELLOW)
COLOR_NAMES: dict[int, str] = {RED: "RED", LIME: "LIME", DARK_BLUE: "BLUE", YELLOW: "YELW"}


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
    color: int
    active: bool = True


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_int(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="JUGGLE CHAIN", display_scale=2, fps=FPS)
        self.rng = random.Random()

        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.best_score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.timer: int = GAME_TIME
        self.hand_color: int = COLORS[0]
        self.color_idx: int = 0
        self.cycle_timer: int = INITIAL_CYCLE_SPEED
        self.spawn_timer: int = MAX_SPAWN_INTERVAL
        self.elapsed_frames: int = 0
        self.super_timer: int = 0
        self.balls: list[Ball] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []

        self._mouse_just_pressed: bool = False

        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = GAME_TIME
        self.hand_color = COLORS[0]
        self.color_idx = 0
        self.cycle_timer = INITIAL_CYCLE_SPEED
        self.spawn_timer = MAX_SPAWN_INTERVAL
        self.elapsed_frames = 0
        self.super_timer = 0
        self.balls.clear()
        self.particles.clear()
        self.floating_texts.clear()

        for _ in range(INITIAL_BALLS):
            self._spawn_ball()

    # ------------------------------------------------------------------
    # Difficulty helpers
    # ------------------------------------------------------------------

    def _elapsed_ratio(self) -> float:
        return min(self.elapsed_frames / GAME_TIME, 1.0)

    def _get_spawn_interval(self) -> int:
        return _lerp_int(MAX_SPAWN_INTERVAL, MIN_SPAWN_INTERVAL, self._elapsed_ratio())

    def _get_cycle_speed(self) -> int:
        return _lerp_int(INITIAL_CYCLE_SPEED, MIN_CYCLE_SPEED, self._elapsed_ratio())

    def _get_max_balls(self) -> int:
        return _lerp_int(MAX_BALLS_START, MAX_BALLS_END, self._elapsed_ratio())

    # ------------------------------------------------------------------
    # Ball management
    # ------------------------------------------------------------------

    def _active_balls(self) -> list[Ball]:
        return [b for b in self.balls if b.active]

    def _spawn_ball(self) -> None:
        if len(self._active_balls()) >= self._get_max_balls():
            return
        x = self.rng.uniform(20, SCREEN_W - 20)
        vx = self.rng.uniform(-BALL_VX_MAX, BALL_VX_MAX)
        vy = self.rng.uniform(-9.0, -7.0)
        color = self.rng.choice(COLORS)
        self.balls.append(Ball(x=x, y=CATCH_Y, vx=vx, vy=vy, color=color, active=True))

    def _update_balls(self) -> None:
        for ball in self.balls:
            if not ball.active:
                continue
            ball.vy += GRAVITY
            ball.x += ball.vx
            ball.y += ball.vy

            if ball.x < BALL_RADIUS:
                ball.x = BALL_RADIUS
                ball.vx = abs(ball.vx)
            elif ball.x > SCREEN_W - BALL_RADIUS:
                ball.x = SCREEN_W - BALL_RADIUS
                ball.vx = -abs(ball.vx)

            if ball.y < BALL_RADIUS:
                ball.y = BALL_RADIUS
                ball.vy = abs(ball.vy)

            if ball.y > SCREEN_H + BALL_RADIUS:
                ball.active = False
                self.heat = min(HEAT_MAX, self.heat + HEAT_DROP)
                self.combo = 0
                for _ in range(4):
                    self._spawn_particle(
                        ball.x,
                        SCREEN_H,
                        self.rng.uniform(-1.5, 1.5),
                        self.rng.uniform(-2.0, 0.0),
                        GRAY,
                        self.rng.randint(6, 12),
                    )

    # ------------------------------------------------------------------
    # Catch resolution
    # ------------------------------------------------------------------

    def _is_in_catch_zone(self, ball: Ball) -> bool:
        return (
            ball.active
            and abs(ball.x - PLAYER_X) <= CATCH_ZONE_HALF_W + BALL_RADIUS
            and CATCH_Y <= ball.y <= CATCH_Y + CATCH_H + BALL_RADIUS
        )

    def _resolve_catch(self, ball: Ball) -> None:
        ball.active = False

        if self.super_timer > 0:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            points = 10 * self.combo * SUPER_SCORE_MULT
            self.score += points
            self._spawn_match_particles(ball.x, ball.y, ball.color)
            self._spawn_floating_text(ball.x, ball.y, f"+{points}", WHITE, 30)
        elif ball.color == self.hand_color:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            points = 10 * self.combo
            self.score += points
            self._spawn_match_particles(ball.x, ball.y, ball.color)
            self._spawn_floating_text(ball.x, ball.y, f"+{points}", WHITE, 30)
            if self.combo >= COMBO_SUPER_THRESHOLD and self.super_timer == 0:
                self.super_timer = SUPER_DURATION
                for _ in range(20):
                    self._spawn_particle(
                        ball.x,
                        ball.y,
                        self.rng.uniform(-3.0, 3.0),
                        self.rng.uniform(-4.0, 1.0),
                        self.rng.choice(COLORS),
                        self.rng.randint(20, 35),
                    )
                self._spawn_floating_text(ball.x, ball.y - 10, "SUPER JUGGLE!", YELLOW, 60)
        else:
            self.heat = min(HEAT_MAX, self.heat + HEAT_MISMATCH)
            self.combo = 0
            for _ in range(4):
                self._spawn_particle(
                    ball.x,
                    ball.y,
                    self.rng.uniform(-1.5, 1.5),
                    self.rng.uniform(-2.0, 1.0),
                    GRAY,
                    self.rng.randint(8, 15),
                )
            self._spawn_floating_text(ball.x, ball.y, "WRONG!", RED, 20)

    # ------------------------------------------------------------------
    # Heat
    # ------------------------------------------------------------------

    def _update_heat(self) -> None:
        if self.heat >= HEAT_MAX:
            self._game_over()
            return
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    # ------------------------------------------------------------------
    # Game over
    # ------------------------------------------------------------------

    def _game_over(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score

    # ------------------------------------------------------------------
    # Timers
    # ------------------------------------------------------------------

    def _update_timers(self) -> None:
        self.elapsed_frames += 1
        self.timer -= 1

        self.cycle_timer -= 1
        if self.cycle_timer <= 0:
            self.color_idx = (self.color_idx + 1) % len(COLORS)
            self.hand_color = COLORS[self.color_idx]
            self.cycle_timer = self._get_cycle_speed()

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self._spawn_ball()
            self.spawn_timer = self._get_spawn_interval()

    # ------------------------------------------------------------------
    # SUPER timer
    # ------------------------------------------------------------------

    def _update_super_timer(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1

    # ------------------------------------------------------------------
    # Particles
    # ------------------------------------------------------------------

    def _spawn_particle(self, x: float, y: float, vx: float, vy: float, color: int, life: int) -> None:
        self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, color=color, life=life))

    def _spawn_match_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(8):
            self._spawn_particle(
                x,
                y,
                self.rng.uniform(-2.0, 2.0),
                self.rng.uniform(-3.0, 0.0),
                color,
                self.rng.randint(10, 18),
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.vy += 0.1
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ------------------------------------------------------------------
    # Floating texts
    # ------------------------------------------------------------------

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int, life: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, color=color, life=life))

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def _handle_input(self) -> None:
        if not self._mouse_just_pressed and not pyxel.btnp(pyxel.KEY_SPACE):
            return

        for ball in self.balls:
            if not ball.active:
                continue
            if self._is_in_catch_zone(ball):
                self._resolve_catch(ball)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self) -> None:
        self._mouse_just_pressed = pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)

        match self.phase:
            case Phase.TITLE:
                self._update_title()
            case Phase.PLAYING:
                self._update_playing()
            case Phase.GAME_OVER:
                self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()

    def _update_playing(self) -> None:
        if pyxel.btnp(pyxel.KEY_Q) or pyxel.btnp(pyxel.KEY_ESCAPE):
            pyxel.quit()
            return

        self._update_timers()
        self._update_balls()
        self._update_heat()
        if self.phase == Phase.GAME_OVER:
            return

        self._handle_input()
        self._update_particles()
        self._update_floating_texts()
        self._update_super_timer()

        if self.timer <= 0:
            self._game_over()

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self) -> None:
        match self.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.PLAYING:
                self._draw_game()
            case Phase.GAME_OVER:
                self._draw_game_over()

    # ------------------------------------------------------------------
    # Title screen
    # ------------------------------------------------------------------

    def _draw_title(self) -> None:
        pyxel.cls(NAVY)

        title = "JUGGLE CHAIN"
        tw = len(title) * 4
        pyxel.text((SCREEN_W - tw) // 2, 50, title, YELLOW)

        lines = [
            "SPACE/CLICK = Catch",
            "Match ball color to hand color!",
            "Chain same-color catches for SUPER JUGGLE!",
            "",
            "COMBO>=4 triggers SUPER (rainbow, any-color match, 3x score)",
            "",
            "HEAT fills on wrong catch / drop",
            "HEAT>=100 = Game Over",
            "",
            "Press SPACE or CLICK to start",
        ]
        for i, line in enumerate(lines):
            lw = len(line) * 4
            pyxel.text((SCREEN_W - lw) // 2, 90 + i * 12, line, GRAY)

        if self.best_score > 0:
            best = f"Best: {self.best_score}"
            bw = len(best) * 4
            pyxel.text((SCREEN_W - bw) // 2, 215, best, YELLOW)

    # ------------------------------------------------------------------
    # Game screen
    # ------------------------------------------------------------------

    def _draw_game(self) -> None:
        pyxel.cls(BLACK)

        # Sky zone
        pyxel.rect(0, 0, SCREEN_W, CATCH_Y - 10, DARK_BLUE)

        self._draw_balls()
        self._draw_catch_zone()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

        if self.super_timer > 0:
            self._draw_super_border()

    def _draw_balls(self) -> None:
        for ball in self.balls:
            if not ball.active:
                continue
            if ball.y > CATCH_Y + CATCH_H + BALL_RADIUS:
                continue
            ix = int(ball.x)
            iy = int(ball.y)
            pyxel.circ(ix, iy, BALL_RADIUS, ball.color)
            pyxel.pset(ix - 1, iy - 2, WHITE)

    def _draw_catch_zone(self) -> None:
        x0 = PLAYER_X - CATCH_ZONE_HALF_W
        color = self.hand_color
        if self.super_timer > 0:
            color = COLORS[(pyxel.frame_count // 4) % len(COLORS)]

        pyxel.rect(x0, CATCH_Y, CATCH_ZONE_HALF_W * 2, CATCH_H, color)
        pyxel.rectb(x0, CATCH_Y, CATCH_ZONE_HALF_W * 2, CATCH_H, WHITE)

        # Hand color indicator
        indicator_cx = SCREEN_W // 2
        indicator_cy = CATCH_Y - 4
        pyxel.rect(indicator_cx - 4, indicator_cy - 4, 8, 8, color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            col = p.color
            if p.life < 4:
                col = GRAY
            pyxel.pset(int(p.x), int(p.y), col)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            tw = len(ft.text) * 4
            x = int(ft.x - tw / 2)
            y = int(ft.y)
            col = ft.color
            if ft.life < 8:
                col = GRAY
            pyxel.text(x, y, ft.text, col)

    def _draw_hud(self) -> None:
        score_text = f"Score: {self.score}"
        pyxel.text(4, 2, score_text, WHITE)

        combo_color = ORANGE if self.combo >= 3 else YELLOW
        combo_text = f"Combo x{self.combo}"
        cw = len(combo_text) * 4
        pyxel.text((SCREEN_W - cw) // 2, 2, combo_text, combo_color)

        elapsed = max(0, self.timer // FPS)
        time_color = RED if elapsed <= 10 else WHITE
        time_text = f"Time: {elapsed:02d}"
        pyxel.text(SCREEN_W - 70, 2, time_text, time_color)

        # HEAT bar (vertical, left side)
        bar_x = 2
        bar_y = 20
        bar_w = 8
        bar_h = 100
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, GRAY)
        heat_h = int(bar_h * (self.heat / HEAT_MAX))
        if heat_h > 0:
            heat_color: int
            if self.heat > 70:
                heat_color = RED
            elif self.heat > 40:
                heat_color = ORANGE
            else:
                heat_color = LIME
            pyxel.rect(bar_x, bar_y + bar_h - heat_h, bar_w, heat_h, heat_color)
        pyxel.text(bar_x + 12, bar_y + 40, "H", RED)
        pyxel.text(bar_x + 12, bar_y + 50, "E", RED)
        pyxel.text(bar_x + 12, bar_y + 60, "A", RED)
        pyxel.text(bar_x + 12, bar_y + 70, "T", RED)

        if self.super_timer > 0:
            super_text = "SUPER JUGGLE!"
            sw = len(super_text) * 4
            sc = COLORS[(pyxel.frame_count // 3) % len(COLORS)]
            pyxel.text((SCREEN_W - sw) // 2, 14, super_text, sc)

        best_text = f"Best: {self.best_score}"
        pyxel.text(SCREEN_W - 70, 14, best_text, YELLOW if self.best_score > 0 else GRAY)

    def _draw_super_border(self) -> None:
        c = COLORS[(pyxel.frame_count // 4) % len(COLORS)]
        pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, c)
        pyxel.rectb(1, 1, SCREEN_W - 2, SCREEN_H - 2, c)

    # ------------------------------------------------------------------
    # Game Over screen
    # ------------------------------------------------------------------

    def _draw_game_over(self) -> None:
        pyxel.cls(NAVY)

        go = "GAME OVER"
        gw = len(go) * 4
        pyxel.text((SCREEN_W - gw) // 2, 50, go, RED)

        score_line = f"Score: {self.score}"
        sw = len(score_line) * 4
        pyxel.text((SCREEN_W - sw) // 2, 80, score_line, WHITE)

        best_line = f"Best:  {self.best_score}"
        bw = len(best_line) * 4
        color = YELLOW if self.score >= self.best_score and self.score > 0 else WHITE
        pyxel.text((SCREEN_W - bw) // 2, 95, best_line, color)

        maxc_line = f"Max Combo: x{self.max_combo}"
        mw = len(maxc_line) * 4
        pyxel.text((SCREEN_W - mw) // 2, 115, maxc_line, CYAN)

        reason: str
        if self.heat >= HEAT_MAX:
            reason = "Overheated!"
        elif self.timer <= 0:
            reason = "Time's up!"
        else:
            reason = ""
        if reason:
            rw = len(reason) * 4
            pyxel.text((SCREEN_W - rw) // 2, 135, reason, ORANGE)

        prompt = "Press SPACE or CLICK to retry"
        pw = len(prompt) * 4
        pyxel.text((SCREEN_W - pw) // 2, 170, prompt, GRAY)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
