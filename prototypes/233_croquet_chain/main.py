"""CROQUET CHAIN -- Top-down croquet game prototype."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# --- Constants ---
WIDTH = 320
HEIGHT = 240
FPS = 60

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

BALL_COLORS = (RED, LIME, DARK_BLUE, YELLOW)
RAINBOW_COLORS = (RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK)

FIELD_LEFT = 20
FIELD_TOP = 20
FIELD_RIGHT = 300
FIELD_BOTTOM = 220

FRICTION = 0.98
STOP_SPEED = 0.1
SUPER_DURATION = 300
SUPER_COMBO_THRESHOLD = 4
GAME_DURATION = 60 * FPS
HEAT_WRONG_WICKET = 15.0
HEAT_BOUNDARY = 5.0
HEAT_DECAY = 0.02
MAX_GHOST_POINTS = 60


class Phase(Enum):
    TITLE = auto()
    AIMING = auto()
    SHOOTING = auto()
    GAME_OVER = auto()


@dataclass
class Ball:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    radius: int = 6
    color: int = WHITE
    active: bool = True


@dataclass
class Wicket:
    x: float
    y: float
    color: int
    scored: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


class Game:
    phase: Phase
    score: int
    combo: int
    max_combo: int
    best_combo: int
    heat: float
    timer: int
    super_timer: int
    aim_start_x: float
    aim_start_y: float
    cue_ball: Ball
    balls: list[Ball]
    wickets: list[Wicket]
    particles: list[Particle]
    ghost_trail: list[tuple[float, float]]
    shot_trail: list[tuple[float, float]]
    rng: random.Random
    spawn_timer: int
    wicket_move_timer: int
    dragging: bool

    def __init__(self) -> None:
        self.rng = random.Random()
        self.reset()

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.best_combo = 0
        self.heat = 0.0
        self.timer = GAME_DURATION
        self.super_timer = 0
        self.aim_start_x = 0.0
        self.aim_start_y = 0.0
        self.cue_ball = Ball(160.0, 210.0, radius=6, color=WHITE)
        self.balls = []
        self.wickets = []
        self.particles = []
        self.ghost_trail = []
        self.shot_trail = []
        self.spawn_timer = 0
        self.wicket_move_timer = 0
        self.dragging = False

    def _start_game(self) -> None:
        self.phase = Phase.AIMING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = GAME_DURATION
        self.super_timer = 0
        self.cue_ball = Ball(160.0, 210.0, radius=6, color=WHITE)
        self.balls = []
        self.wickets = []
        self.particles = []
        self.ghost_trail = []
        self.shot_trail = []
        self.spawn_timer = 0
        self.wicket_move_timer = 0
        self.dragging = False
        self._spawn_balls()
        self._spawn_wickets()

    # --- Spawning ---

    def _spawn_balls(self) -> None:
        self.balls.clear()
        for color in BALL_COLORS:
            for _attempt in range(100):
                x = self.rng.uniform(FIELD_LEFT + 12, FIELD_RIGHT - 12)
                y = self.rng.uniform(FIELD_TOP + 80, FIELD_BOTTOM - 12)
                if math.hypot(x - self.cue_ball.x, y - self.cue_ball.y) < 30:
                    continue
                ok = True
                for b in self.balls:
                    if math.hypot(x - b.x, y - b.y) < 20:
                        ok = False
                        break
                if ok:
                    break
            self.balls.append(Ball(x=x, y=y, radius=6, color=color))

    def _spawn_wickets(self) -> None:
        self.wickets.clear()
        for color in BALL_COLORS:
            for _attempt in range(100):
                x = self.rng.uniform(FIELD_LEFT + 30, FIELD_RIGHT - 30)
                y = self.rng.uniform(FIELD_TOP + 10, FIELD_TOP + 90)
                ok = True
                for w in self.wickets:
                    if math.hypot(x - w.x, y - w.y) < 48:
                        ok = False
                        break
                if ok:
                    break
            self.wickets.append(Wicket(x=x, y=y, color=color))

    # --- Shooting ---

    def _shoot_cue_ball(self, dx: float, dy: float, power: float) -> None:
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            return
        speed = min(power / 10.0, 8.0)
        if speed < 0.3:
            return
        self.cue_ball.vx = (dx / dist) * speed
        self.cue_ball.vy = (dy / dist) * speed

    def _launch_toward_nearest(self) -> None:
        nearest: Ball | None = None
        nearest_dist = float("inf")
        for b in self.balls:
            if not b.active:
                continue
            d = math.hypot(b.x - self.cue_ball.x, b.y - self.cue_ball.y)
            if d < nearest_dist:
                nearest_dist = d
                nearest = b
        if nearest is not None and nearest_dist > 0:
            dx = nearest.x - self.cue_ball.x
            dy = nearest.y - self.cue_ball.y
            self._shoot_cue_ball(dx, dy, nearest_dist)

    # --- Physics ---

    def _update_physics(self) -> None:
        all_balls = [self.cue_ball] + self.balls
        for b in all_balls:
            if not b.active:
                continue
            b.x += b.vx
            b.y += b.vy
            b.vx *= FRICTION
            b.vy *= FRICTION
            # Boundary bounce
            hit_wall = False
            if b.x - b.radius < FIELD_LEFT:
                b.x = FIELD_LEFT + b.radius
                b.vx = abs(b.vx) * 0.7
                hit_wall = True
            elif b.x + b.radius > FIELD_RIGHT:
                b.x = FIELD_RIGHT - b.radius
                b.vx = -abs(b.vx) * 0.7
                hit_wall = True
            if b.y - b.radius < FIELD_TOP:
                b.y = FIELD_TOP + b.radius
                b.vy = abs(b.vy) * 0.7
                hit_wall = True
            elif b.y + b.radius > FIELD_BOTTOM:
                b.y = FIELD_BOTTOM - b.radius
                b.vy = -abs(b.vy) * 0.7
                hit_wall = True
            if hit_wall and b is not self.cue_ball:
                self.heat = min(100.0, self.heat + HEAT_BOUNDARY)
                self._spawn_particles(b.x, b.y, WHITE, 3)
                b.x = self.rng.uniform(FIELD_LEFT + 12, FIELD_RIGHT - 12)
                b.y = self.rng.uniform(FIELD_TOP + 80, FIELD_BOTTOM - 12)
                b.vx = 0.0
                b.vy = 0.0

    @staticmethod
    def _ball_stopping(b: Ball) -> bool:
        return abs(b.vx) < STOP_SPEED and abs(b.vy) < STOP_SPEED

    def _all_stopped(self) -> bool:
        if self.cue_ball.active and not self._ball_stopping(self.cue_ball):
            return False
        for b in self.balls:
            if b.active and not self._ball_stopping(b):
                return False
        return True

    def _check_collisions(self) -> None:
        all_balls = [self.cue_ball] + self.balls
        n = len(all_balls)
        for i in range(n):
            a = all_balls[i]
            if not a.active:
                continue
            for j in range(i + 1, n):
                b = all_balls[j]
                if not b.active:
                    continue
                dx = b.x - a.x
                dy = b.y - a.y
                dist = math.hypot(dx, dy)
                min_dist = a.radius + b.radius
                if dist > min_dist or dist < 0.001:
                    continue
                nx = dx / dist
                ny = dy / dist
                overlap = min_dist - dist
                a.x -= nx * overlap * 0.5
                a.y -= ny * overlap * 0.5
                b.x += nx * overlap * 0.5
                b.y += ny * overlap * 0.5
                dvx = a.vx - b.vx
                dvy = a.vy - b.vy
                dvn = dvx * nx + dvy * ny
                if dvn > 0:
                    a.vx -= dvn * nx
                    a.vy -= dvn * ny
                    b.vx += dvn * nx
                    b.vy += dvn * ny

    # --- Wickets ---

    def _check_wicket_pass(self, ball: Ball, wicket: Wicket) -> bool:
        if wicket.scored:
            return False
        post_half = 12
        h_inside = abs(ball.x - wicket.x) < post_half - ball.radius * 0.5
        v_near = abs(ball.y - wicket.y) < 10.0
        return h_inside and v_near

    def _handle_wicket_score(self, ball: Ball, wicket: Wicket) -> None:
        is_super = self.super_timer > 0
        is_match = ball.color == wicket.color or is_super

        if is_match:
            self.combo += 1
            mult = 3.0 if is_super else 1.0
            self.score += int(10 * self.combo * mult)
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            if self.combo >= SUPER_COMBO_THRESHOLD and self.super_timer == 0:
                self.super_timer = SUPER_DURATION
            pcolor = (
                RAINBOW_COLORS[self.combo % len(RAINBOW_COLORS)]
                if is_super
                else ball.color
            )
            pcount = 20 if is_super else 8
        else:
            self.combo = 0
            self.heat = min(100.0, self.heat + HEAT_WRONG_WICKET)
            pcolor = GRAY
            pcount = 5

        self._spawn_particles(ball.x, ball.y, pcolor, pcount)
        wicket.scored = True

    # --- Particles ---

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles[:] = [p for p in self.particles if p.life > 0]

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.pi * 2)
            speed = self.rng.uniform(0.5, 1.5)
            life = self.rng.randint(15, 25)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=life, color=color,
            ))

    # --- Resolution ---

    def _resolve_shot(self) -> None:
        if self.combo > 0 and self.shot_trail:
            trail = list(self.shot_trail)
            if len(trail) > MAX_GHOST_POINTS:
                step = len(trail) / MAX_GHOST_POINTS
                trail = [trail[int(i * step)] for i in range(MAX_GHOST_POINTS)]
            self.ghost_trail = trail
        self.shot_trail.clear()

        if all(w.scored for w in self.wickets):
            self._spawn_wickets()

        self.cue_ball.x = 160.0
        self.cue_ball.y = 210.0
        self.cue_ball.vx = 0.0
        self.cue_ball.vy = 0.0

        for b in self.balls:
            if not b.active:
                b.active = True
                b.x = self.rng.uniform(FIELD_LEFT + 12, FIELD_RIGHT - 12)
                b.y = self.rng.uniform(FIELD_TOP + 80, FIELD_BOTTOM - 12)
                b.vx = 0.0
                b.vy = 0.0

        self.phase = Phase.AIMING

    # --- Timer / Difficulty ---

    def _update_timer(self) -> None:
        if self.timer > 0:
            self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER
            if self.combo > self.best_combo:
                self.best_combo = self.combo

    def _update_difficulty(self) -> None:
        self.wicket_move_timer += 1
        if self.wicket_move_timer >= 900:
            self.wicket_move_timer = 0
            for w in self.wickets:
                w.x += self.rng.uniform(-15, 15)
                w.y += self.rng.uniform(-10, 10)
                w.x = max(FIELD_LEFT + 24, min(FIELD_RIGHT - 24, w.x))
                w.y = max(FIELD_TOP + 8, min(FIELD_TOP + 100, w.y))

    # --- Main loop ---

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE):
                self._start_game()

        elif self.phase == Phase.AIMING:
            self._update_timer()
            self._update_difficulty()

            if self.heat >= 100.0:
                self.phase = Phase.GAME_OVER
                if self.combo > self.best_combo:
                    self.best_combo = self.combo
                return

            self.heat = max(0.0, self.heat - HEAT_DECAY)

            if self.super_timer > 0:
                self.super_timer -= 1

            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                if math.hypot(mx - self.cue_ball.x, my - self.cue_ball.y) < 35:
                    self.dragging = True
                    self.aim_start_x = float(mx)
                    self.aim_start_y = float(my)

            if self.dragging:
                if pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT):
                    self.dragging = False
                    dx = mx - self.cue_ball.x
                    dy = my - self.cue_ball.y
                    power = math.hypot(
                        mx - self.aim_start_x, my - self.aim_start_y
                    )
                    self._shoot_cue_ball(dx, dy, power)
                    if abs(self.cue_ball.vx) > 0.001 or abs(self.cue_ball.vy) > 0.001:
                        self.phase = Phase.SHOOTING
                        self.shot_trail.clear()

        elif self.phase == Phase.SHOOTING:
            self._update_timer()
            self._update_physics()
            self._check_collisions()

            if self.cue_ball.active:
                self.shot_trail.append((self.cue_ball.x, self.cue_ball.y))

            if self.super_timer > 0:
                self.super_timer -= 1

            for b in self.balls:
                if not b.active:
                    continue
                for w in self.wickets:
                    if self._check_wicket_pass(b, w):
                        self._handle_wicket_score(b, w)

            self._update_particles()

            if self.super_timer > 0 and self._all_stopped():
                self._launch_toward_nearest()

            if self.super_timer <= 0 and self._all_stopped():
                self._resolve_shot()

        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE):
                self._start_game()

    def draw(self) -> None:
        pyxel.cls(NAVY)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.AIMING, Phase.SHOOTING):
            self._draw_field()
            self._draw_hud()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(105, 70, "CROQUET CHAIN", WHITE)
        pyxel.text(108, 95, "Click to Start", WHITE)
        pyxel.text(60, 125, "Drag cue ball to aim & shoot", WHITE)
        pyxel.text(55, 140, "Match ball color to wicket color", WHITE)
        pyxel.text(78, 158, "Combo x4 = SUPER SHOT!", YELLOW)
        pyxel.text(85, 178, "Heat >= 100 = Game Over", ORANGE)

    def _draw_field(self) -> None:
        fw = FIELD_RIGHT - FIELD_LEFT
        fh = FIELD_BOTTOM - FIELD_TOP
        pyxel.rect(FIELD_LEFT, FIELD_TOP, fw, fh, GREEN)
        pyxel.rectb(FIELD_LEFT, FIELD_TOP, fw, fh, WHITE)

        for gx, gy in self.ghost_trail:
            pyxel.pset(int(gx), int(gy), GRAY)

        post_half = 12
        post_h = 16
        for w in self.wickets:
            if self.super_timer > 0:
                wcolor = RAINBOW_COLORS[
                    (pyxel.frame_count // 4) % len(RAINBOW_COLORS)
                ]
            else:
                wcolor = w.color
            if w.scored:
                wcolor = GRAY
            pyxel.line(
                int(w.x - post_half), int(w.y),
                int(w.x - post_half), int(w.y + post_h), wcolor,
            )
            pyxel.line(
                int(w.x + post_half), int(w.y),
                int(w.x + post_half), int(w.y + post_h), wcolor,
            )
            pyxel.line(
                int(w.x - post_half), int(w.y),
                int(w.x + post_half), int(w.y), wcolor,
            )

        if self.cue_ball.active:
            ccolor = WHITE
            if self.super_timer > 0:
                ccolor = RAINBOW_COLORS[
                    (pyxel.frame_count // 3) % len(RAINBOW_COLORS)
                ]
            pyxel.circ(
                int(self.cue_ball.x), int(self.cue_ball.y),
                self.cue_ball.radius, ccolor,
            )

        for b in self.balls:
            if not b.active:
                continue
            bcolor = b.color
            if self.super_timer > 0:
                bcolor = RAINBOW_COLORS[
                    (pyxel.frame_count // 3) % len(RAINBOW_COLORS)
                ]
            pyxel.circ(int(b.x), int(b.y), b.radius, bcolor)

        if self.phase == Phase.AIMING and self.dragging:
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            dx = mx - self.cue_ball.x
            dy = my - self.cue_ball.y
            dist = math.hypot(dx, dy)
            if dist > 2:
                steps = min(16, int(dist / 3))
                for i in range(steps):
                    t = (i + 1) / steps
                    px = self.cue_ball.x + dx * t
                    py = self.cue_ball.y + dy * t
                    if i % 2 == 0:
                        pyxel.pset(int(px), int(py), YELLOW)

        for p in self.particles:
            pcolor = p.color if p.life > 5 else GRAY
            pyxel.pset(int(p.x), int(p.y), pcolor)

    def _draw_hud(self) -> None:
        bar_w = 50
        bar_h = 5
        bar_x = 6
        bar_y = 3
        fill = int(bar_w * self.heat / 100)
        bar_color = (
            GREEN if self.heat < 40 else (ORANGE if self.heat < 70 else RED)
        )
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        pyxel.rect(bar_x, bar_y, fill, bar_h, bar_color)
        pyxel.text(bar_x, bar_y + 7, "HEAT", WHITE)

        sec = (self.timer + FPS - 1) // FPS
        tcolor = WHITE if sec > 10 else RED
        tstr = f"TIME:{sec:02d}"
        pyxel.text(WIDTH // 2 - len(tstr) * 2, 3, tstr, tcolor)

        pyxel.text(WIDTH - 85, 3, f"SCORE:{self.score}", WHITE)
        ccolor = YELLOW
        if self.combo >= SUPER_COMBO_THRESHOLD:
            ccolor = RAINBOW_COLORS[
                (pyxel.frame_count // 3) % len(RAINBOW_COLORS)
            ]
        pyxel.text(WIDTH - 85, 13, f"COMBO:{self.combo}", ccolor)

        if self.super_timer > 0:
            stext = f"SUPER! {self.super_timer // FPS}s"
            pyxel.text(WIDTH // 2 - len(stext) * 2, 16, stext, YELLOW)

    def _draw_game_over(self) -> None:
        pyxel.text(112, 60, "GAME OVER", RED)
        pyxel.text(110, 85, f"Score: {self.score}", WHITE)
        pyxel.text(100, 100, f"Max Combo: {self.max_combo}", YELLOW)
        pyxel.text(85, 120, f"Best Combo: {self.best_combo}", WHITE)
        pyxel.text(100, 145, "Click to Retry", WHITE)


def main() -> None:
    pyxel.init(WIDTH, HEIGHT, title="CROQUET CHAIN")
    game = Game()
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
