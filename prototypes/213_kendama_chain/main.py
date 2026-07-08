import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

SCREEN_W = 320
SCREEN_H = 240

HANDLE_X = SCREEN_W // 2
HANDLE_Y = SCREEN_H - 40
PIVOT_X = HANDLE_X
PIVOT_Y = HANDLE_Y - 20

BALL_REST_X = PIVOT_X
BALL_REST_Y = PIVOT_Y + 50
REST_STRING_LEN = 50
MAX_STRING_LEN = 80
BALL_RADIUS = 5
MIN_LAUNCH_POWER = 3.0
MAX_LAUNCH_POWER = 12.0

CUP_COLORS = [8, 3, 10, 6]
COLOR_NAMES = ["RED", "GREEN", "YELLOW", "BLUE"]

GRAVITY = 0.15
STRING_DAMPING = 0.92
AIR_FRICTION = 0.995

GAME_TIME = 60 * 30
MAX_HEAT = 10
COMBO_THRESHOLD = 4
SUPER_DURATION = 5 * 30
SUPER_MULTIPLIER = 3
BASE_SCORE = 100

HEAT_WRONG_CUP = 1
HEAT_MISS = 2

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

COLOR_HANDLE = GRAY
COLOR_STRING = DARK_BLUE
COLOR_BALL_DEFAULT = WHITE
COLOR_HEAT_BAR = RED
COLOR_SUPER = ORANGE

CUP_DEFS = [
    (135, 170, 12, 0, 0, "BIG"),
    (185, 170, 12, 1, 0, "SMALL"),
    (140, 145, 10, 2, 1, "HIGH"),
    (160, 125, 8, 3, 2, "SPIKE"),
]


@dataclass
class Cup:
    x: float
    y: float
    r: float
    color_idx: int
    tier: int
    label: str


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    string_length: float
    is_launched: bool
    pivot_x: float
    pivot_y: float


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
    vy: float = -1.5


@dataclass
class EchoGhost:
    points: list[tuple[float, float]]
    life: int
    color: int


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class Game:
    def __init__(self) -> None:
        self._make_state()
        self.phase = Phase.TITLE

    def _make_state(self) -> None:
        self.ball = Ball(
            x=float(BALL_REST_X), y=float(BALL_REST_Y),
            vx=0.0, vy=0.0,
            string_length=float(REST_STRING_LEN),
            is_launched=False,
            pivot_x=float(PIVOT_X), pivot_y=float(PIVOT_Y),
        )
        self.cups = [
            Cup(x=float(c[0]), y=float(c[1]), r=float(c[2]),
                color_idx=c[3], tier=c[4], label=c[5])
            for c in CUP_DEFS
        ]
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0
        self.target_color = 0
        self.phase_timer = GAME_TIME
        self.super_mode = False
        self.super_timer = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.echo_ghost: EchoGhost | None = None
        self.rng: random.Random = random.Random()
        self._mouse_held = False
        self._caught_this_launch = False
        self._trajectory: list[tuple[float, float]] = []
        self.frame = 0

    def reset(self) -> None:
        self._make_state()
        self.phase = Phase.PLAYING
        self.rng = random.Random()

    def _update_ball_physics(self) -> None:
        b = self.ball
        if not b.is_launched:
            return
        b.vy += GRAVITY
        b.vx *= AIR_FRICTION
        b.vy *= AIR_FRICTION
        b.x += b.vx
        b.y += b.vy
        self._trajectory.append((b.x, b.y))
        if len(self._trajectory) > 120:
            self._trajectory = self._trajectory[-120:]
        dist = math.hypot(b.x - b.pivot_x, b.y - b.pivot_y)
        if dist > MAX_STRING_LEN:
            angle = math.atan2(b.y - b.pivot_y, b.x - b.pivot_x)
            b.x = b.pivot_x + MAX_STRING_LEN * math.cos(angle)
            b.y = b.pivot_y + MAX_STRING_LEN * math.sin(angle)
        rest_y = b.pivot_y + REST_STRING_LEN
        speed = math.hypot(b.vx, b.vy)
        if b.y >= rest_y and speed < 1.5 and b.vy >= 0:
            self._return_to_rest()

    def _return_to_rest(self) -> None:
        b = self.ball
        if not self._caught_this_launch:
            self.combo = 0
            self.heat += HEAT_MISS
            self._spawn_floating_text(b.x, b.y, "MISS!", RED)
        b.x = float(BALL_REST_X)
        b.y = float(BALL_REST_Y)
        b.vx = 0.0
        b.vy = 0.0
        b.string_length = float(REST_STRING_LEN)
        b.is_launched = False
        self._caught_this_launch = False
        self._trajectory.clear()
        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER

    def _compute_launch_velocity(self, pull_x: float, pull_y: float) -> tuple[float, float]:
        b = self.ball
        dx = b.pivot_x - b.x
        dy = b.pivot_y - b.y
        dist = math.hypot(dx, dy)
        if dist < 0.001:
            return (0.0, 0.0)
        stretch = b.string_length - REST_STRING_LEN
        stretch_range = MAX_STRING_LEN - REST_STRING_LEN
        if stretch_range <= 0:
            return (0.0, 0.0)
        t = stretch / stretch_range
        power = MIN_LAUNCH_POWER + t * (MAX_LAUNCH_POWER - MIN_LAUNCH_POWER)
        nx = dx / dist
        ny = dy / dist
        return (nx * power, ny * power)

    def _constrain_ball_to_string(self, bx: float, by: float, slen: float) -> tuple[float, float]:
        px = self.ball.pivot_x
        py = self.ball.pivot_y
        dx = bx - px
        dy = by - py
        dist = math.hypot(dx, dy)
        if dist < 0.001:
            return (px, py + slen)
        ratio = slen / dist
        return (px + dx * ratio, py + dy * ratio)

    def _check_cup_collisions(self, bx: float, by: float) -> Cup | None:
        for cup in self.cups:
            dist = math.hypot(bx - cup.x, by - cup.y)
            if dist <= cup.r + BALL_RADIUS:
                return cup
        return None

    def _resolve_catch(self, cup: Cup) -> None:
        self._caught_this_launch = True
        cup_color_idx = cup.color_idx
        ball_color_idx = self.target_color
        is_match = self.super_mode or (cup_color_idx == ball_color_idx)

        if is_match:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            tier_bonus = cup.tier + 1
            mult = SUPER_MULTIPLIER if self.super_mode else 1
            points = int(BASE_SCORE * self.combo * tier_bonus * mult)
            self.score += points
            color = CUP_COLORS[cup_color_idx]
            self._spawn_catch_particles(cup.x, cup.y, color, 12)
            self._spawn_floating_text(cup.x, cup.y - 8, f"+{points}", CYAN)
            if self.combo >= 3:
                self._spawn_floating_text(cup.x, cup.y - 20, f"COMBO x{self.combo}!", YELLOW)
            self._record_echo_ghost()
            self._advance_target_color()
            self._check_super_threshold()
        else:
            self.combo = 0
            self.heat += HEAT_WRONG_CUP
            self._spawn_catch_particles(cup.x, cup.y, GRAY, 4)
            self._spawn_floating_text(cup.x, cup.y - 8, "WRONG!", RED)
            if self.heat >= MAX_HEAT:
                self.phase = Phase.GAME_OVER

        self.ball.x = float(BALL_REST_X)
        self.ball.y = float(BALL_REST_Y)
        self.ball.vx = 0.0
        self.ball.vy = 0.0
        self.ball.string_length = float(REST_STRING_LEN)
        self.ball.is_launched = False
        self._caught_this_launch = False
        self._trajectory.clear()

    def _record_echo_ghost(self) -> None:
        if not self._trajectory:
            return
        traj = self._trajectory
        n = len(traj)
        if n < 5:
            pts = list(traj)
        else:
            pts = [traj[min(i * (n - 1) // 4, n - 1)] for i in range(5)]
        self.echo_ghost = EchoGhost(
            points=list(pts),
            life=90,
            color=CUP_COLORS[self.target_color],
        )

    def _advance_target_color(self) -> None:
        self.target_color = (self.target_color + 1) % 4

    def _check_super_threshold(self) -> None:
        if self.combo >= COMBO_THRESHOLD and not self.super_mode:
            self.super_mode = True
            self.super_timer = SUPER_DURATION
            self._spawn_catch_particles(
                self.ball.pivot_x, self.ball.pivot_y, ORANGE, 30,
            )
            self._spawn_floating_text(
                self.ball.pivot_x, self.ball.pivot_y - 30, "SUPER!", YELLOW,
            )

    def _update_super_timer(self) -> None:
        if not self.super_mode:
            return
        self.super_timer -= 1
        if self.super_timer <= 0:
            self.super_mode = False
            self.super_timer = 0
            self.combo = 0

    def _update_timers(self) -> None:
        self.phase_timer -= 1
        self._update_super_timer()
        if self.phase_timer <= 0:
            self.phase = Phase.GAME_OVER

    def _check_game_over(self) -> bool:
        return self.heat >= MAX_HEAT or self.phase_timer <= 0

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.08
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _update_echo_ghost(self) -> None:
        if self.echo_ghost is None:
            return
        self.echo_ghost.life -= 1
        if self.echo_ghost.life <= 0:
            self.echo_ghost = None

    def _spawn_catch_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.pi * 2)
            speed = self.rng.uniform(1.0, 3.0)
            life = self.rng.randint(20, 40)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=life, color=color,
            ))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(
            x=x - len(text) * 2, y=y,
            text=text, life=30, color=color,
            vy=-1.5,
        ))

    def _handle_input_playing(self) -> None:
        b = self.ball
        mouse_x = float(max(0, min(SCREEN_W, pyxel.mouse_x)))
        mouse_y = float(max(0, min(SCREEN_H, pyxel.mouse_y)))

        if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
            if not self._mouse_held and not b.is_launched:
                self._mouse_held = True
            if self._mouse_held and b.is_launched:
                pass
            elif self._mouse_held:
                dist = math.hypot(mouse_x - b.pivot_x, mouse_y - b.pivot_y)
                slen = max(float(REST_STRING_LEN), min(float(MAX_STRING_LEN), dist))
                b.string_length = slen
                new_x, new_y = self._constrain_ball_to_string(mouse_x, mouse_y, slen)
                b.x = new_x
                b.y = new_y
                b.vx = 0.0
                b.vy = 0.0
                self._trajectory.clear()
        else:
            if self._mouse_held and not b.is_launched:
                vx, vy = self._compute_launch_velocity(b.x, b.y)
                speed = math.hypot(vx, vy)
                if speed < MIN_LAUNCH_POWER * 0.5:
                    b.x = float(BALL_REST_X)
                    b.y = float(BALL_REST_Y)
                    b.string_length = float(REST_STRING_LEN)
                    b.vx = 0.0
                    b.vy = 0.0
                else:
                    b.vx = vx
                    b.vy = vy
                    b.is_launched = True
                    self._caught_this_launch = False
                    self._trajectory = [(b.x, b.y)]
            self._mouse_held = False

    def update(self) -> None:
        self.frame += 1

    def draw(self) -> None:
        pyxel.cls(BLACK)

    def _draw_title(self) -> None:
        pyxel.cls(BLACK)
        title = "KENDAMA CHAIN"
        pyxel.text(SCREEN_W // 2 - len(title) * 2, 40, title, WHITE)

        kx = HANDLE_X
        ky = HANDLE_Y
        pyxel.line(kx, ky - 30, kx, ky + 10, COLOR_HANDLE)
        pyxel.line(kx - 12, ky - 24, kx + 12, ky - 24, COLOR_HANDLE)
        pyxel.line(kx - 6, ky - 28, kx - 6, ky - 20, COLOR_HANDLE)
        pyxel.line(kx + 6, ky - 28, kx + 6, ky - 20, COLOR_HANDLE)

        bx = BALL_REST_X
        by = BALL_REST_Y
        pyxel.line(PIVOT_X, PIVOT_Y, bx, by, COLOR_STRING)
        pyxel.circ(int(bx), int(by), BALL_RADIUS, CUP_COLORS[0])

        lines = [
            "CLICK & DRAG down to pull",
            "RELEASE to launch the ball",
            "Catch ball in matching cup!",
            "Same color = COMBO",
            "Wrong color = HEAT +1",
            "Miss = HEAT +2",
            "COMBO x4 = SUPER MODE!",
            "60 sec time limit",
            "",
            "CLICK OR PRESS ENTER",
        ]
        for i, line in enumerate(lines):
            cy = 92 + i * 13
            if line and i == len(lines) - 1:
                if (self.frame // 30) % 2 == 0:
                    pyxel.text(SCREEN_W // 2 - len(line) * 2, cy, line, YELLOW)
            elif line:
                pyxel.text(SCREEN_W // 2 - len(line) * 2, cy, line, WHITE)

        for ci in range(4):
            cx = 120 + ci * 24
            cy = 215
            pyxel.rect(cx, cy, 6, 6, CUP_COLORS[ci])
            pyxel.rect(cx, cy, 6, 6, WHITE)

    def _draw_playing(self) -> None:
        pyxel.cls(BLACK)
        self._draw_echo_ghost()
        self._draw_string()
        self._draw_kendama()
        self._draw_cups()
        self._draw_ball()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_kendama(self) -> None:
        kx = HANDLE_X
        ky = HANDLE_Y
        pyxel.line(kx, ky - 30, kx, ky + 10, COLOR_HANDLE)
        pyxel.line(kx - 12, ky - 24, kx + 12, ky - 24, COLOR_HANDLE)
        pyxel.line(kx - 6, ky - 28, kx - 6, ky - 20, COLOR_HANDLE)
        pyxel.line(kx + 6, ky - 28, kx + 6, ky - 20, COLOR_HANDLE)

    def _draw_cups(self) -> None:
        for cup in self.cups:
            c = CUP_COLORS[cup.color_idx]
            if self.super_mode:
                c = [RED, YELLOW, GREEN, LIGHT_BLUE][(self.frame // 4) % 4]
            pyxel.circ(int(cup.x), int(cup.y), int(cup.r), c)
            pyxel.circb(int(cup.x), int(cup.y), int(cup.r), WHITE)
            arc_y = int(cup.y - cup.r * 0.5)
            arc_r = int(cup.r * 0.7)
            pyxel.circb(int(cup.x), arc_y, arc_r, c)

    def _draw_string(self) -> None:
        b = self.ball
        if b.is_launched and len(self._trajectory) >= 2:
            for i in range(len(self._trajectory) - 1):
                p0 = self._trajectory[i]
                p1 = self._trajectory[i + 1]
                alpha = i / len(self._trajectory)
                col = DARK_BLUE if alpha < 0.5 else NAVY
                pyxel.line(int(p0[0]), int(p0[1]), int(p1[0]), int(p1[1]), col)
        else:
            pyxel.line(int(b.pivot_x), int(b.pivot_y), int(b.x), int(b.y), COLOR_STRING)

    def _draw_ball(self) -> None:
        b = self.ball
        if self.super_mode:
            c = [RED, YELLOW, GREEN, LIGHT_BLUE][(self.frame // 4) % 4]
        else:
            c = CUP_COLORS[self.target_color]
        cx = int(b.x)
        cy = int(b.y)
        pyxel.circ(cx, cy, BALL_RADIUS, c)
        pyxel.circb(cx, cy, BALL_RADIUS, WHITE)
        highlight_x = int(b.x - 1)
        highlight_y = int(b.y - 1)
        pyxel.circ(highlight_x, highlight_y, 1, WHITE)

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, 32, BLACK)
        pyxel.line(0, 32, SCREEN_W, 32, DARK_BLUE)

        pyxel.text(4, 4, f"SCORE {self.score}", WHITE)

        combo_color = WHITE
        if self.combo >= 3:
            combo_color = YELLOW
        if self.combo >= COMBO_THRESHOLD and self.super_mode:
            combo_color = ORANGE
        pyxel.text(4, 14, f"COMBO x{self.combo}", combo_color)

        secs = max(0, self.phase_timer) // 30 + 1
        pyxel.text(SCREEN_W - 60, 4, f"TIME {secs}s", WHITE)

        pyxel.text(SCREEN_W - 60, 14, f"HEAT {self.heat}/{MAX_HEAT}", RED)

        tx = SCREEN_W - 74
        ty = 4
        pyxel.rect(tx, ty, 6, 6, CUP_COLORS[self.target_color])
        pyxel.rectb(tx, ty, 6, 6, WHITE)

        if self.super_mode:
            secs_left = self.super_timer // 30 + 1
            suptext = f"SUPER {secs_left}s"
            pyxel.text(SCREEN_W // 2 - len(suptext) * 2, 4, suptext, ORANGE)

        bar_x = 4
        bar_w = (SCREEN_W - 8) * self.phase_timer // GAME_TIME
        pyxel.rect(bar_x, SCREEN_H - 8, SCREEN_W - 8, 4, NAVY)
        pyxel.rect(bar_x, SCREEN_H - 8, max(0, bar_w), 4, WHITE)

        heat_w = (SCREEN_W - 8) * self.heat // MAX_HEAT
        heat_color = RED if self.heat < MAX_HEAT - 3 else ORANGE
        pyxel.rect(bar_x, SCREEN_H - 14, SCREEN_W - 8, 4, DARK_BLUE)
        pyxel.rect(bar_x, SCREEN_H - 14, max(0, heat_w), 4, heat_color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            if p.life > 0:
                sz = max(1, p.life // 10)
                pyxel.rect(int(p.x), int(p.y), sz, sz, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life > 0:
                pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

    def _draw_echo_ghost(self) -> None:
        if self.echo_ghost is None:
            return
        ghost = self.echo_ghost
        alpha = ghost.life / 90
        for i, pt in enumerate(ghost.points):
            if i > 0:
                prev = ghost.points[i - 1]
                pyxel.line(
                    int(prev[0]), int(prev[1]),
                    int(pt[0]), int(pt[1]),
                    ghost.color,
                )
            if alpha > 0.3:
                pyxel.circ(int(pt[0]), int(pt[1]), 2, ghost.color)

    def _draw_game_over(self) -> None:
        pyxel.cls(BLACK)

        go_text = "GAME OVER"
        pyxel.text(SCREEN_W // 2 - len(go_text) * 2, 30, go_text, RED)

        out = [
            f"SCORE: {self.score}",
            f"MAX COMBO: x{self.max_combo}",
        ]
        y = 70
        for t in out:
            pyxel.text(SCREEN_W // 2 - len(t) * 2, y, t, WHITE)
            y += 20

        if self.heat >= MAX_HEAT:
            reason = "OVERHEATED!"
        elif self.phase_timer <= 0:
            reason = "TIME UP!"
        else:
            reason = "MISS!"
        pyxel.text(SCREEN_W // 2 - len(reason) * 2, y + 10, reason, ORANGE)

        retry = "CLICK OR PRESS ENTER"
        if (self.frame // 30) % 2 == 0:
            pyxel.text(SCREEN_W // 2 - len(retry) * 2, 170, retry, WHITE)


class App:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="KENDAMA CHAIN", display_scale=2)
        self.game = Game()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        g = self.game
        g.update()
        if g.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_RETURN):
                g.reset()
        elif g.phase == Phase.PLAYING:
            g._handle_input_playing()
            g._update_ball_physics()
            if g.ball.is_launched:
                hit_cup = g._check_cup_collisions(g.ball.x, g.ball.y)
                if hit_cup and not g._caught_this_launch:
                    g._resolve_catch(hit_cup)
            g._update_timers()
            g._update_particles()
            g._update_floating_texts()
            g._update_echo_ghost()
        elif g.phase == Phase.GAME_OVER:
            g._update_particles()
            g._update_floating_texts()
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_RETURN):
                g.reset()

    def draw(self) -> None:
        g = self.game
        if g.phase == Phase.TITLE:
            g._draw_title()
        elif g.phase == Phase.PLAYING:
            g._draw_playing()
        elif g.phase == Phase.GAME_OVER:
            g._draw_game_over()


def main() -> None:
    App()


if __name__ == "__main__":
    main()
