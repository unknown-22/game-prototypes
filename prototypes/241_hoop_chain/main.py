"""Hoop Chain - Color-match basketball shooting COMBO game."""
import enum
import math
import random
from dataclasses import dataclass
from collections import deque

import pyxel


class Phase(enum.Enum):
    TITLE = enum.auto()
    PLAYING = enum.auto()
    GAME_OVER = enum.auto()


@dataclass
class Ball:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    color: int = 0
    active: bool = True
    scored: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int


class Game:
    SCREEN_W = 320
    SCREEN_H = 240

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

    BALL_COLORS = (8, 11, 5, 10)  # RED, LIME, DARK_BLUE, YELLOW
    BALL_COLOR_NAMES = ("RED", "LIME", "DARK_BLUE", "YELLOW")

    HOOP_X = 160
    HOOP_Y = 60
    HOOP_RADIUS = 16
    PLAYER_X = 160
    PLAYER_Y = 180
    MAX_POWER = 150.0
    GRAVITY = 0.15
    FRICTION = 0.995
    POWER_FACTOR = 0.03
    SPRING_CONSTANT = 0.3

    MAX_BALLS = 5
    SUPER_DURATION = 300
    SUPER_CHAIN_RADIUS = 80.0
    SUPER_MULTIPLIER = 3
    HEAT_MAX = 100.0
    HEAT_DECAY = 0.02
    HEAT_MISMATCH = 15
    HEAT_MISS = 10
    HEAT_OUT_OF_BOUNDS = 10
    GAME_DURATION = 3600
    COLOR_INTERVAL = 90
    MIN_COLOR_INTERVAL = 40
    DIFFICULTY_STEP = 1
    DIFFICULTY_EVERY = 180
    SCORE_PER_COMBO = 100
    SHAKE_SUPER = 8
    SHAKE_GAMEOVER = 5
    BALL_MIN_X = 8
    BALL_MAX_X = 312
    BALL_MIN_Y = 8
    BALL_MAX_Y = 235
    HOOP_CLEAR_RADIUS = 60.0
    SPAWN_MARGIN = 20
    AIM_LINE_DASH = 6
    AIM_LINE_GAP = 4
    POWER_BAR_X = 10
    POWER_BAR_Y = 215
    POWER_BAR_W = 50
    POWER_BAR_H = 6
    PLAYER_RADIUS = 10
    BALL_RADIUS = 6

    def __init__(self) -> None:
        self._rng = random.Random()
        self.reset()

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.balls: list[Ball] = []
        self.hand_color = 0
        self.color_timer = self.COLOR_INTERVAL
        self.aiming = False
        self.aim_start_x = 0.0
        self.aim_start_y = 0.0
        self.aim_end_x = 0.0
        self.aim_end_y = 0.0
        self.heat = 0.0
        self.super_mode = False
        self.super_timer = 0
        self.game_timer = self.GAME_DURATION
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shot_count = 0
        self.shake_frames = 0
        self.frame = 0

    def start_game(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.balls = []
        self.hand_color = 0
        self.color_timer = self.COLOR_INTERVAL
        self.aiming = False
        self.aim_start_x = 0.0
        self.aim_start_y = 0.0
        self.aim_end_x = 0.0
        self.aim_end_y = 0.0
        self.heat = 0.0
        self.super_mode = False
        self.super_timer = 0
        self.game_timer = self.GAME_DURATION
        self.particles = []
        self.floating_texts = []
        self.shot_count = 0
        self.shake_frames = 0
        self.frame = 0
        self._spawn_balls()

    def _spawn_balls(self) -> None:
        for _ in range(self.MAX_BALLS):
            self._spawn_one_ball()

    def _spawn_one_ball(self) -> None:
        for _ in range(100):
            x = self._rng.uniform(self.BALL_MIN_X, self.BALL_MAX_X)
            y = self._rng.uniform(self.BALL_MIN_Y, self.BALL_MAX_Y)
            if self._in_hoop_clear(x, y):
                continue
            color = self._rng.randint(0, 3)
            angle = self._rng.random() * math.pi * 2
            speed = self._rng.uniform(0.3, 1.0)
            ball = Ball(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                color=color,
            )
            self.balls.append(ball)
            return
        x = self._rng.uniform(self.SPAWN_MARGIN, self.SCREEN_W - self.SPAWN_MARGIN)
        y = self._rng.uniform(self.SPAWN_MARGIN, self.SCREEN_H * 0.5)
        color = self._rng.randint(0, 3)
        self.balls.append(Ball(x=x, y=y, color=color))

    def _in_hoop_clear(self, x: float, y: float) -> bool:
        dx = x - self.HOOP_X
        dy = y - self.HOOP_Y
        return (dx * dx + dy * dy) < self.HOOP_CLEAR_RADIUS * self.HOOP_CLEAR_RADIUS

    def _shoot(self) -> None:
        dx = self.aim_start_x - self.aim_end_x
        dy = self.aim_start_y - self.aim_end_y
        dist = math.hypot(dx, dy)
        if dist < 5.0:
            return
        power = min(dist, self.MAX_POWER)
        angle = math.atan2(-dy, -dx)
        vx = math.cos(angle) * power * self.POWER_FACTOR
        vy = math.sin(angle) * power * self.POWER_FACTOR
        ball = Ball(
            x=self.PLAYER_X,
            y=self.PLAYER_Y,
            vx=vx,
            vy=vy,
            color=self.hand_color,
        )
        self.balls.append(ball)
        self.shot_count += 1
        px = self.PLAYER_X
        py = self.PLAYER_Y
        self._spawn_particles(px, py, self.WHITE, 3, 8)

    def _update_balls(self) -> None:
        for ball in self.balls[:]:
            if not ball.active or ball.scored:
                continue
            ball.vy += self.GRAVITY
            ball.x += ball.vx
            ball.y += ball.vy
            ball.vx *= self.FRICTION
            ball.vy *= self.FRICTION

            if ball.x < self.BALL_MIN_X:
                ball.x = self.BALL_MIN_X
                ball.vx = abs(ball.vx) * self.SPRING_CONSTANT
            elif ball.x > self.BALL_MAX_X:
                ball.x = self.BALL_MAX_X
                ball.vx = -abs(ball.vx) * self.SPRING_CONSTANT

            if ball.y < self.BALL_MIN_Y:
                ball.y = self.BALL_MIN_Y
                ball.vy = abs(ball.vy) * self.SPRING_CONSTANT
            elif ball.y > self.BALL_MAX_Y:
                ball.y = self.BALL_MAX_Y
                ball.vy = -abs(ball.vy) * self.SPRING_CONSTANT
                if not self.super_mode:
                    self.heat = min(self.HEAT_MAX, self.heat + self.HEAT_OUT_OF_BOUNDS)
                ball.active = False

            self._check_hoop(ball)

        self.balls[:] = [b for b in self.balls if b.active]
        self._maintain_ball_count()

    def _check_hoop(self, ball: Ball) -> None:
        if ball.scored:
            return
        dx = ball.x - self.HOOP_X
        dy = ball.y - self.HOOP_Y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < self.HOOP_RADIUS and ball.y > self.HOOP_Y - 5:
            self._handle_score(ball)

    def _handle_score(self, ball: Ball) -> None:
        is_match = self.BALL_COLORS[ball.color] == self.BALL_COLORS[self.hand_color] or self.super_mode
        if is_match:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            multiplier = self.SUPER_MULTIPLIER if self.super_mode else 1
            gained = self.SCORE_PER_COMBO * self.combo * multiplier
            self.score += gained
            ball.scored = True
            ball.active = False

            p_count = 25 if self.super_mode else 15
            self._spawn_particles(ball.x, ball.y, self.BALL_COLORS[ball.color], p_count, 12)
            if self.super_mode:
                self._spawn_floating_text(ball.x, ball.y, f"+{gained}", self.BALL_COLORS[(self.frame // 4) % 4])
            elif self.combo >= 3:
                self._spawn_floating_text(ball.x, ball.y, f"COMBO x{self.combo}", self.BALL_COLORS[ball.color])
            else:
                self._spawn_floating_text(ball.x, ball.y, f"+{gained}", self.WHITE)

            if self.combo >= 4 and not self.super_mode:
                self._activate_super(ball.x, ball.y)

            if self.super_mode:
                self.super_timer = self.SUPER_DURATION
        else:
            if not self.super_mode:
                self.combo = 0
                self.heat = min(self.HEAT_MAX, self.heat + self.HEAT_MISMATCH)
            ball.scored = True
            ball.active = False
            self._spawn_particles(ball.x, ball.y, self.GRAY, 8, 8)
            self._spawn_floating_text(ball.x, ball.y, "MISS!", self.GRAY)

    def _activate_super(self, x: float, y: float) -> None:
        self.super_mode = True
        self.super_timer = self.SUPER_DURATION
        self.shake_frames = self.SHAKE_SUPER
        self._spawn_floating_text(x, y, "SUPER SHOT!", self.BALL_COLORS[(self.frame // 4) % 4])

        visited: set[int] = set()
        queue: deque[int] = deque()
        for i, b in enumerate(self.balls):
            if b.active and not b.scored:
                d = math.hypot(b.x - self.HOOP_X, b.y - self.HOOP_Y)
                if d < self.SUPER_CHAIN_RADIUS:
                    queue.append(i)
                    visited.add(i)

        while queue:
            idx = queue.popleft()
            b = self.balls[idx]
            if b.scored or not b.active:
                continue
            b.scored = True
            b.active = False
            gained = self.SCORE_PER_COMBO * self.combo * self.SUPER_MULTIPLIER
            self.score += gained
            self._spawn_particles(b.x, b.y, self.BALL_COLORS[b.color], 25, 12)
            self._spawn_floating_text(b.x, b.y, f"+{gained}", self.BALL_COLORS[(self.frame // 4) % 4])

            for i2, b2 in enumerate(self.balls):
                if i2 in visited:
                    continue
                if b2.active and not b2.scored:
                    d = math.hypot(b2.x - b.x, b2.y - b.y)
                    if d < self.SUPER_CHAIN_RADIUS:
                        queue.append(i2)
                        visited.add(i2)

    def _maintain_ball_count(self) -> None:
        active = [b for b in self.balls if b.active]
        need = self.MAX_BALLS - len(active)
        for _ in range(need):
            self._spawn_one_ball()

    def _update_players_aim(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.aiming = True
            self.aim_start_x = float(pyxel.mouse_x)
            self.aim_start_y = float(pyxel.mouse_y)

        if self.aiming:
            self.aim_end_x = float(pyxel.mouse_x)
            self.aim_end_y = float(pyxel.mouse_y)
            if pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT):
                self._shoot()
                self.aiming = False

    def _update_heat(self) -> None:
        if self.heat >= self.HEAT_MAX:
            self.phase = Phase.GAME_OVER
            self.shake_frames = self.SHAKE_GAMEOVER
            return
        self.heat = max(0.0, self.heat - self.HEAT_DECAY)

    def _difficulty_cycle_interval(self) -> int:
        elapsed = self.GAME_DURATION - self.game_timer
        steps = elapsed // self.DIFFICULTY_EVERY
        return max(self.MIN_COLOR_INTERVAL, self.COLOR_INTERVAL - steps * self.DIFFICULTY_STEP)

    def _spawn_particles(self, x: float, y: float, color: int, count: int, life: int) -> None:
        for _ in range(count):
            angle = self._rng.random() * math.pi * 2
            speed = self._rng.random() * 3.0 + 1.0
            p_life = life + self._rng.randint(-5, 5)
            self.particles.append(
                Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed, max(1, p_life), color)
            )

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x, y, text, color, 40))

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.life -= 1
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.life -= 1
            ft.y -= 1.0
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.start_game()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.start_game()
            return

        self.frame += 1
        self.game_timer -= 1
        if self.game_timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        self.color_timer -= 1
        if self.color_timer <= 0:
            self.hand_color = (self.hand_color + 1) % 4
            self.color_timer = self._difficulty_cycle_interval()

        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False

        self._update_players_aim()
        self._update_balls()
        self._update_heat()
        if self.phase == Phase.GAME_OVER:
            return
        self._update_particles()
        self._update_floating_texts()
        if self.shake_frames > 0:
            self.shake_frames -= 1

    def draw(self) -> None:
        pyxel.cls(0)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = "HOOP CHAIN"
        pyxel.text(self.SCREEN_W // 2 - len(title) * 4 // 2, 50, title, 7)
        lines = [
            "Click + Drag + Release to Shoot",
            "",
            "Match ball color to hoop color",
            "for COMBO chain!",
            "COMBO>=4 -> SUPER SHOT!",
            "",
            "Mismatch = HEAT  /  HEAT>=100 = GAME OVER",
            "",
            "Click or SPACE to Start",
        ]
        y = 80
        for line in lines:
            color = 7
            if "SUPER SHOT" in line:
                color = 10
            elif "HEAT" in line:
                color = 8
            pyxel.text(self.SCREEN_W // 2 - len(line) * 4 // 2, y, line, color)
            y += 12

    def _draw_game_over(self) -> None:
        pyxel.text(self.SCREEN_W // 2 - 20, 60, "GAME OVER", 8)
        score_text = f"SCORE: {self.score}"
        pyxel.text(self.SCREEN_W // 2 - len(score_text) * 4 // 2, 90, score_text, 7)
        combo_text = f"MAX COMBO: {self.max_combo}"
        pyxel.text(self.SCREEN_W // 2 - len(combo_text) * 4 // 2, 110, combo_text, 7)
        shots_text = f"SHOTS: {self.shot_count}"
        pyxel.text(self.SCREEN_W // 2 - len(shots_text) * 4 // 2, 130, shots_text, 7)
        retry_text = "Click or SPACE to Retry"
        pyxel.text(self.SCREEN_W // 2 - len(retry_text) * 4 // 2, 160, retry_text, 7)

    def _draw_playing(self) -> None:
        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0:
            shake_x = self._rng.randint(-2, 2)
            shake_y = self._rng.randint(-2, 2)
        pyxel.camera(shake_x, shake_y)

        pyxel.cls(self.DARK_BLUE)

        self._draw_court_lines()
        self._draw_hoop()
        self._draw_balls()
        self._draw_player()
        self._draw_aim_line()
        self._draw_particles()
        self._draw_floating_texts()

        pyxel.camera(0, 0)
        self._draw_hud()

    def _draw_court_lines(self) -> None:
        pyxel.line(0, self.SCREEN_H // 2, self.SCREEN_W, self.SCREEN_H // 2, self.LIGHT_BLUE)
        pyxel.rectb(50, 20, self.SCREEN_W - 100, self.HOOP_Y + self.HOOP_RADIUS - 10, self.LIGHT_BLUE)

    def _draw_hoop(self) -> None:
        hx = self.HOOP_X
        hy = self.HOOP_Y
        pyxel.line(hx - 20, hy, hx - 15, hy + 10, self.BROWN)
        pyxel.line(hx + 20, hy, hx + 15, hy + 10, self.BROWN)
        pyxel.line(hx - 15, hy + 10, hx + 15, hy + 10, self.BROWN)
        rim_color = self.BALL_COLORS[self.hand_color]
        if self.super_mode:
            rim_color = self.BALL_COLORS[(self.frame // 4) % 4]
        pyxel.circb(hx, hy, self.HOOP_RADIUS, rim_color)
        pyxel.circb(hx, hy, self.HOOP_RADIUS + 1, rim_color)

    def _draw_balls(self) -> None:
        for ball in self.balls:
            if not ball.active or ball.scored:
                continue
            bx = int(ball.x)
            by = int(ball.y)
            color = self.BALL_COLORS[ball.color]
            pyxel.circ(bx, by, self.BALL_RADIUS, color)
            pyxel.circb(bx, by, self.BALL_RADIUS, self.WHITE)
            label = self.BALL_COLOR_NAMES[ball.color][0]
            pyxel.text(bx - 2, by - 2, label, self.BLACK)

    def _draw_player(self) -> None:
        px = self.PLAYER_X
        py = self.PLAYER_Y
        pyxel.circ(px, py, self.PLAYER_RADIUS, self.WHITE)
        pyxel.circb(px, py, self.PLAYER_RADIUS, self.GRAY)
        hand_color = self.BALL_COLORS[self.hand_color]
        if self.super_mode:
            hand_color = self.BALL_COLORS[(self.frame // 4) % 4]
        pyxel.circ(px, py, 5, hand_color)

    def _draw_aim_line(self) -> None:
        if not self.aiming:
            return
        sx = int(self.aim_start_x)
        sy = int(self.aim_start_y)
        ex = int(self.aim_end_x)
        ey = int(self.aim_end_y)
        dx = ex - sx
        dy = ey - sy
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            return
        steps = int(dist / (self.AIM_LINE_DASH + self.AIM_LINE_GAP))
        for i in range(steps + 1):
            t = i / max(steps, 1)
            x = sx + dx * t
            y = sy + dy * t
            if i % 2 == 0:
                pyxel.circ(int(x), int(y), 1, self.WHITE)
        power = min(dist, self.MAX_POWER) / self.MAX_POWER
        bar_w = int(self.POWER_BAR_W * power)
        pyxel.rect(self.POWER_BAR_X, self.POWER_BAR_Y, self.POWER_BAR_W, self.POWER_BAR_H, self.GRAY)
        hc = self.GREEN if power < 0.5 else self.YELLOW if power < 0.8 else self.RED
        pyxel.rect(self.POWER_BAR_X, self.POWER_BAR_Y, bar_w, self.POWER_BAR_H, hc)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.rect(int(p.x), int(p.y), 2, 2, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            tx = int(ft.x) - len(ft.text) * 2
            ty = int(ft.y)
            pyxel.text(tx, ty, ft.text, ft.color)

    def _draw_hud(self) -> None:
        if self.super_mode:
            border_color = self.BALL_COLORS[(self.frame // 4) % 4]
            pyxel.rectb(0, 0, self.SCREEN_W, self.SCREEN_H, border_color)
            pyxel.rectb(1, 1, self.SCREEN_W - 2, self.SCREEN_H - 2, border_color)

        score_text = f"SCORE: {self.score}"
        pyxel.text(2, 2, score_text, 7)

        combo_color = 7
        if self.combo >= 4:
            combo_color = 10
        elif self.combo >= 2:
            combo_color = 11
        combo_text = f"COMBO: {self.combo}"
        pyxel.text(self.SCREEN_W // 2 - len(combo_text) * 2, 2, combo_text, combo_color)

        seconds = max(0, self.game_timer) // 60
        timer_text = f"TIME: {seconds}"
        timer_color = 8 if seconds <= 10 and self.frame % 30 < 15 else 7
        pyxel.text(self.SCREEN_W - len(timer_text) * 4 - 2, 2, timer_text, timer_color)

        bw = self.SCREEN_W - 4
        bh = 4
        bx = 2
        by = self.SCREEN_H - 10
        pyxel.rect(bx, by, bw, bh, self.DARK_BLUE)
        hw = int(bw * self.heat / self.HEAT_MAX)
        hc = self.GREEN
        if self.heat > 75:
            hc = self.RED
        elif self.heat > 50:
            hc = self.ORANGE
        elif self.heat > 25:
            hc = self.YELLOW
        if hw > 0:
            pyxel.rect(bx, by, hw, bh, hc)
        pyxel.rectb(bx, by, bw, bh, self.WHITE)
        pyxel.text(bx, by + 5, "HEAT", self.WHITE)

        cix = self.SCREEN_W // 2 - 80
        hand_color = self.BALL_COLORS[self.hand_color]
        if self.super_mode:
            hand_color = self.BALL_COLORS[(self.frame // 4) % 4]
        pyxel.rect(cix, self.SCREEN_H - 20, 8, 8, hand_color)
        label = f"HAND: {self.BALL_COLOR_NAMES[self.hand_color]}"
        pyxel.text(cix + 10, self.SCREEN_H - 18, label, 7)

        if self.super_mode:
            st = f"SUPER SHOT! {self.super_timer // 60}s"
            sc = self.BALL_COLORS[(self.frame // 4) % 4]
            pyxel.text(self.SCREEN_W // 2 - len(st) * 2, self.SCREEN_H - 30, st, sc)


class App:
    def __init__(self) -> None:
        self.game = Game()
        pyxel.init(Game.SCREEN_W, Game.SCREEN_H, title="Hoop Chain")
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        self.game.update()

    def draw(self) -> None:
        self.game.draw()


if __name__ == "__main__":
    App()
