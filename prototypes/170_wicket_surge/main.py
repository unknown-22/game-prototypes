from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# --- Color Constants ---
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

BAT_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
COLOR_NAMES: list[str] = ["RED", "GREEN", "BLUE", "YELLOW"]

SCREEN_W = 320
SCREEN_H = 240
STRIKE_ZONE_X = 110
STRIKE_ZONE_Y = 180
STRIKE_ZONE_W = 100
STRIKE_ZONE_H = 30
BAT_Y = 195
BAT_W = 80
BAT_H = 8
BALL_RADIUS = 6
COLOR_CYCLE_FRAMES = 90
SUPER_DURATION = 300
HEAT_DECAY = 0.05
HEAT_WRONG_HIT = 20.0
MAX_HEAT = 100.0
MAX_WICKETS = 3
SHAKE_FRAMES = 10
BASE_BALL_SPEED = 1.5
MAX_BALL_SPEED = 4.0
BASE_SPAWN_INTERVAL = 120
MIN_SPAWN_INTERVAL = 60


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Ball:
    x: float
    y: float
    color: int
    active: bool = True


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    gravity: float = 0.0


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, "WICKET SURGE", display_scale=2)
        self.rng = random.Random()
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.wickets = 0
        self.bat_color = 0
        self.color_timer = COLOR_CYCLE_FRAMES
        self.super_mode = False
        self.super_timer = 0
        self.balls: list[Ball] = []
        self.particles: list[Particle] = []
        self.spawn_timer = BASE_SPAWN_INTERVAL
        self.shake_frames = 0
        self.game_timer = 0
        self.high_score = 0
        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.wickets = 0
        self.bat_color = 0
        self.color_timer = COLOR_CYCLE_FRAMES
        self.super_mode = False
        self.super_timer = 0
        self.balls.clear()
        self.particles.clear()
        self.spawn_timer = BASE_SPAWN_INTERVAL
        self.shake_frames = 0
        self.game_timer = 0

    # --- Ball Logic ---

    def _spawn_ball(self) -> Ball:
        x = self.rng.uniform(40, SCREEN_W - 40)
        color = self.rng.randint(0, 3)
        return Ball(x=x, y=self.rng.uniform(0, 30), color=color, active=True)

    def _ball_speed(self) -> float:
        return min(MAX_BALL_SPEED, BASE_BALL_SPEED + self.score / 500.0)

    def _spawn_interval(self) -> int:
        return max(MIN_SPAWN_INTERVAL, BASE_SPAWN_INTERVAL - self.score // 20)

    def _strike_zone_contains(self, ball: Ball) -> bool:
        left = STRIKE_ZONE_X
        right = STRIKE_ZONE_X + STRIKE_ZONE_W
        top = STRIKE_ZONE_Y
        bottom = STRIKE_ZONE_Y + STRIKE_ZONE_H
        return (ball.x + BALL_RADIUS > left and ball.x - BALL_RADIUS < right
                and ball.y + BALL_RADIUS > top and ball.y - BALL_RADIUS < bottom)

    def _update_balls(self) -> None:
        speed = self._ball_speed()
        for ball in self.balls:
            if ball.active:
                ball.y += speed

        if self.phase == Phase.PLAYING:
            if self.super_mode:
                for ball in self.balls:
                    if ball.active and self._strike_zone_contains(ball):
                        self._handle_hit(ball)

            self.balls = [b for b in self.balls if b.active and b.y - BALL_RADIUS < SCREEN_H + 20]
            active_balls = [b for b in self.balls if b.active]
            for ball in active_balls:
                if ball.y > STRIKE_ZONE_Y + STRIKE_ZONE_H + BALL_RADIUS and self._strike_zone_contains(ball):
                    pass
                if ball.y > STRIKE_ZONE_Y + STRIKE_ZONE_H + 10 and ball.active:
                    self._handle_miss(ball)

    def _check_swing(self, click_x: int, click_y: int) -> int:
        del click_y
        bat_left = SCREEN_W // 2 - BAT_W // 2
        bat_right = SCREEN_W // 2 + BAT_W // 2
        if click_x < bat_left or click_x > bat_right:
            return -1

        zone_balls = [b for b in self.balls if b.active and self._strike_zone_contains(b)]
        if not zone_balls:
            return -1

        matching = [b for b in zone_balls if b.color == self.bat_color or self.super_mode]
        if matching:
            self._handle_hit(matching[0])
            return 0
        else:
            self._handle_wrong_hit()
            return 1

    # --- Hit Handling ---

    def _handle_hit(self, ball: Ball) -> None:
        ball.active = False
        multiplier = 1.0 + self.combo * 0.5
        base_score = 10
        if self.super_mode:
            base_score *= 3
        self.score += int(base_score * multiplier)
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        self._spawn_hit_particles(ball.x, ball.y, BAT_COLORS[ball.color])

        if self.combo >= 4 and not self.super_mode:
            self._activate_super()

    def _handle_wrong_hit(self) -> None:
        self.combo = 0
        self.wickets += 1
        self.heat += HEAT_WRONG_HIT
        self.shake_frames = SHAKE_FRAMES
        zone_center_x = STRIKE_ZONE_X + STRIKE_ZONE_W // 2
        zone_center_y = STRIKE_ZONE_Y + STRIKE_ZONE_H // 2
        self._spawn_wicket_particles(zone_center_x, zone_center_y)
        self._update_heat()

    def _handle_miss(self, ball: Ball) -> None:
        ball.active = False
        self.combo = 0
        self.wickets += 1
        self.shake_frames = SHAKE_FRAMES
        self._spawn_wicket_particles(ball.x, ball.y)
        if self.super_mode:
            self._deactivate_super()
        self._check_game_over()

    # --- Heat System ---

    def _update_heat(self) -> None:
        self.heat = max(0.0, self.heat - HEAT_DECAY)
        self._check_game_over()

    def _check_game_over(self) -> None:
        if self.wickets >= MAX_WICKETS or self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER
            if self.score > self.high_score:
                self.high_score = self.score

    # --- Bat Color Cycling ---

    def _cycle_bat_color(self) -> None:
        if self.super_mode:
            return
        self.color_timer -= 1
        if self.color_timer <= 0:
            self.color_timer = COLOR_CYCLE_FRAMES
            self.bat_color = (self.bat_color + 1) % 4

    # --- Super Mode ---

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        for ball in self.balls:
            if ball.active:
                self._spawn_hit_particles(ball.x, ball.y, self.rng.choice(BAT_COLORS))

    def _deactivate_super(self) -> None:
        self.super_mode = False
        self.super_timer = 0

    def _update_super(self) -> None:
        if not self.super_mode:
            return
        self.super_timer -= 1
        if self.super_timer <= 0:
            self._deactivate_super()

    # --- Particle System ---

    def _spawn_hit_particles(self, x: float, y: float, color: int) -> None:
        count = self.rng.randint(15, 25) if self.super_mode else self.rng.randint(5, 10)
        for _ in range(count):
            px = x + self.rng.uniform(-4, 4)
            py = y + self.rng.uniform(-4, 4)
            pcolor = self.rng.choice(BAT_COLORS) if self.super_mode else color
            life = self.rng.randint(20, 30) if self.super_mode else self.rng.randint(15, 25)
            vx = self.rng.uniform(-2, 2) if not self.super_mode else self.rng.uniform(-3, 3)
            vy = self.rng.uniform(-3, -1) if not self.super_mode else self.rng.uniform(-4, -1)
            self.particles.append(Particle(x=px, y=py, vx=vx, vy=vy, life=life, color=pcolor, gravity=0.0))

    def _spawn_wicket_particles(self, x: float, y: float) -> None:
        count = self.rng.randint(20, 30)
        for _ in range(count):
            px = x + self.rng.uniform(-6, 6)
            py = y + self.rng.uniform(-4, 4)
            vx = self.rng.uniform(-4, 4)
            vy = self.rng.uniform(-5, -1)
            life = self.rng.randint(30, 40)
            self.particles.append(Particle(x=px, y=py, vx=vx, vy=vy, life=life, color=RED, gravity=0.05))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += p.gravity
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # --- Update Loop ---

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
            return

        self.game_timer += 1

        self._cycle_bat_color()
        self._update_super()

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_timer = self._spawn_interval()
            self.balls.append(self._spawn_ball())

        self._update_balls()

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._check_swing(pyxel.mouse_x, pyxel.mouse_y)

        self._update_heat()
        self._update_particles()

        if self.shake_frames > 0:
            self.shake_frames -= 1

    # --- Draw Loop ---

    def draw(self) -> None:
        if self.shake_frames > 0 and self.phase == Phase.PLAYING:
            intensity = max(1, self.shake_frames // 2)
            ox = self.rng.randint(-intensity, intensity)
            oy = self.rng.randint(-intensity, intensity)
            pyxel.camera(ox, oy)
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.cls(GREEN)
        pyxel.text(SCREEN_W // 2 - len("WICKET SURGE") * 2, 60, "WICKET SURGE", WHITE)
        pyxel.rect(SCREEN_W // 2 - 40, 78, 80, 1, LIME)

        pyxel.text(SCREEN_W // 2 - 45, 100, "Click to swing bat", LIME)
        pyxel.text(SCREEN_W // 2 - 55, 112, "Match ball color to hit!", LIME)
        pyxel.text(SCREEN_W // 2 - 52, 124, "4x combo = SUPER SHOT", LIME)

        if self.high_score > 0:
            pyxel.text(SCREEN_W // 2 - 30, 150, f"HIGH SCORE: {self.high_score}", YELLOW)

        blink = (pyxel.frame_count // 30) % 2 == 0
        if blink:
            pyxel.text(SCREEN_W // 2 - 40, 200, "CLICK TO START", WHITE)

    def _draw_playing(self) -> None:
        pyxel.cls(GREEN)
        for i in range(0, SCREEN_W, 40):
            pyxel.line(i, STRIKE_ZONE_Y, i + 20, STRIKE_ZONE_Y, LIME)
        pyxel.line(0, STRIKE_ZONE_Y + STRIKE_ZONE_H, SCREEN_W, STRIKE_ZONE_Y + STRIKE_ZONE_H, LIME)

        pyxel.rectb(STRIKE_ZONE_X, STRIKE_ZONE_Y, STRIKE_ZONE_W, STRIKE_ZONE_H, WHITE)

        bat_left = SCREEN_W // 2 - BAT_W // 2
        if self.super_mode:
            rainbow_frame = (pyxel.frame_count // 5) % 4
            for offset in range(-1, 2):
                c = BAT_COLORS[(rainbow_frame + offset) % 4]
                pyxel.rect(bat_left - 1, BAT_Y - 1, BAT_W + 2, BAT_H + 2, c)
            pyxel.rect(bat_left, BAT_Y, BAT_W, BAT_H, WHITE)
        else:
            pyxel.rect(bat_left, BAT_Y, BAT_W, BAT_H, BAT_COLORS[self.bat_color])
            pyxel.rectb(bat_left, BAT_Y, BAT_W, BAT_H, WHITE)

        for ball in self.balls:
            if ball.active:
                c = BAT_COLORS[ball.color]
                pyxel.circ(int(ball.x), int(ball.y), BALL_RADIUS, c)
                pyxel.circ(int(ball.x) - 2, int(ball.y) - 2, 2, WHITE)
            else:
                pyxel.circ(int(ball.x), int(ball.y), BALL_RADIUS, ORANGE)

        for p in self.particles:
            alpha_factor = p.life / 40.0
            if alpha_factor > 0.5:
                pyxel.pset(int(p.x), int(p.y), p.color)
            elif alpha_factor > 0.25:
                if (p.life // 2) % 2 == 0:
                    pyxel.pset(int(p.x), int(p.y), p.color)

        self._draw_hud()

        if self.super_mode:
            tint = (pyxel.frame_count // 10) % 2
            if tint:
                for x in range(0, SCREEN_W, 3):
                    for y in range(0, SCREEN_H, 3):
                        pyxel.pset(x, y, self.rng.choice(BAT_COLORS))

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, 20, NAVY)
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)

        combo_text = f"COMBO: {self.combo}"
        combo_color = WHITE
        if self.combo >= 3:
            combo_color = YELLOW
        if self.combo >= 4:
            combo_color = ORANGE
        pyxel.text(SCREEN_W // 2 - len(combo_text) * 2, 4, combo_text, combo_color)

        heat_bar_x = SCREEN_W // 2 - 30
        heat_bar_y = 14
        pyxel.rectb(heat_bar_x - 1, heat_bar_y - 1, 62, 5, WHITE)
        heat_width = int((self.heat / MAX_HEAT) * 60)
        if self.heat < 40:
            heat_color = GREEN
        elif self.heat < 70:
            heat_color = YELLOW
        else:
            heat_color = RED
        pyxel.rect(heat_bar_x, heat_bar_y, heat_width, 3, heat_color)

        wicket_start_x = SCREEN_W - 30
        for i in range(MAX_WICKETS):
            cx = wicket_start_x + i * 10
            pyxel.circb(cx, 10, 4, WHITE)
            if i < self.wickets:
                pyxel.circ(cx, 10, 3, RED)

        if self.super_mode:
            super_text = "SUPER!"
            super_x = SCREEN_W - 85
            rave = pyxel.frame_count // 3
            pyxel.text(super_x, 4, super_text, BAT_COLORS[rave % 4])

    def _draw_game_over(self) -> None:
        pyxel.cls(BLACK)
        pyxel.text(SCREEN_W // 2 - len("GAME OVER") * 2, 50, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - len(f"SCORE: {self.score}") * 2, 80, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - len(f"MAX COMBO: {self.max_combo}") * 2, 100, f"MAX COMBO: {self.max_combo}", WHITE)

        if self.score >= self.high_score and self.score > 0:
            pyxel.text(SCREEN_W // 2 - 30, 120, "NEW HIGH SCORE!", YELLOW)

        cause = "HEAT OVERLOAD" if self.heat >= MAX_HEAT else "ALL OUT"
        pyxel.text(SCREEN_W // 2 - len(cause) * 2, 150, cause, ORANGE)

        blink = (pyxel.frame_count // 30) % 2 == 0
        if blink:
            pyxel.text(SCREEN_W // 2 - 40, 200, "CLICK TO RETRY", WHITE)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
