from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import pyxel

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
BAT_X = 60
BAT_Y = 160
STUMP_X = 35
HIT_ZONE_X = 72

BALL_COLORS: tuple[int, int, int, int] = (RED, LIME, DARK_BLUE, YELLOW)
COLOR_NAMES: tuple[str, str, str, str] = ("RED", "LIME", "BLUE", "YEL")
RAINBOW_COLORS: tuple[int, ...] = (RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK)

COMBO_SUPER = 4
SUPER_DURATION = 300
GAME_TIME = 60 * 60  # 60 seconds at 60fps
MAX_HEAT = 100
HEAT_MISMATCH = 15
HEAT_PASS = 10
HEAT_DECAY = 0.02
BALL_SPAWN_START = 90
BALL_SPAWN_MIN = 30
BALL_SPEED_START = 2.0
BALL_SPEED_MAX = 4.0
BAT_REACH_Y = 24
BOUNDARY_Y = 30


class Phase(IntEnum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    active: bool = True
    resolved: bool = False
    flying_to_boundary: bool = False
    fly_vx: float = 0.0
    fly_vy: float = 0.0


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


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="WICKET CHAIN", display_scale=2)
        font_path = str(Path(__file__).with_name("k8x12.bdf"))
        try:
            pyxel.load(font_path, exclude_images=True, exclude_tilemaps=True, exclude_sounds=True, exclude_musics=True)
        except Exception:
            pass
        self._rng: random.Random = random.Random()
        self._pre_init_state()
        pyxel.run(self._update, self._draw)

    def _pre_init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.bat_color_idx: int = 0
        self.bat_color: int = BALL_COLORS[0]
        self.balls: list[Ball] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.score: int = 0
        self.high_score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.game_timer: int = GAME_TIME
        self.super_timer: int = 0
        self.ball_spawn_timer: int = 0
        self._shake_frames: int = 0
        self._reset()

    def _reset(self) -> None:
        self.phase = Phase.PLAYING
        self.bat_color_idx = 0
        self.bat_color = BALL_COLORS[0]
        self.balls.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.game_timer = GAME_TIME
        self.super_timer = 0
        self.ball_spawn_timer = 60
        self._shake_frames = 0

    def _get_spawn_interval(self) -> int:
        elapsed = GAME_TIME - self.game_timer
        t = elapsed / GAME_TIME
        return int(BALL_SPAWN_START - (BALL_SPAWN_START - BALL_SPAWN_MIN) * t)

    def _get_ball_speed(self) -> float:
        elapsed = GAME_TIME - self.game_timer
        t = elapsed / GAME_TIME
        return BALL_SPEED_START + (BALL_SPEED_MAX - BALL_SPEED_START) * t

    def _spawn_ball(self) -> Ball:
        color = self._rng.choice(BALL_COLORS)
        speed = self._get_ball_speed()
        y_offs = self._rng.uniform(-10, 10)
        return Ball(
            x=float(SCREEN_W + 10),
            y=float(BAT_Y + y_offs),
            vx=-speed,
            vy=0.0,
            color=color,
        )

    def _resolve_hit(self, ball: Ball) -> str:
        if abs(ball.y - BAT_Y) <= BAT_REACH_Y:
            if ball.color == self.bat_color or self.super_timer > 0:
                return "hit"
            return "miss"
        return "none"

    def _check_game_over(self) -> bool:
        return self.heat >= MAX_HEAT or self.game_timer <= 0

    def _spawn_hit_particles(self, x: float, y: float, color: int) -> None:
        count = 20 if self.super_timer > 0 else 10
        for _ in range(count):
            vx = self._rng.uniform(-3.0, 5.0)
            vy = self._rng.uniform(-4.0, 0.0)
            pcolor = self._rng.choice(RAINBOW_COLORS) if self.super_timer > 0 else color
            self.particles.append(Particle(x, y, vx, vy, 15 + self._rng.randrange(15), pcolor))
        boundary_x = self._rng.uniform(100, SCREEN_W - 40)
        for _ in range(6):
            vx = self._rng.uniform(-1.0, 1.0)
            vy = self._rng.uniform(-2.0, -0.5)
            self.particles.append(
                Particle(boundary_x, float(BOUNDARY_Y), vx, vy, 20 + self._rng.randrange(20), YELLOW)
            )

    def _spawn_miss_particles(self, x: float, y: float) -> None:
        for _ in range(6):
            vx = self._rng.uniform(-1.0, 1.0)
            vy = self._rng.uniform(-2.0, 2.0)
            self.particles.append(Particle(x, y, vx, vy, 12 + self._rng.randrange(10), RED))

    def _update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

        self._update_particles()
        self._update_floating_texts()
        if self._shake_frames > 0:
            self._shake_frames -= 1

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._reset()

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._reset()

    def _update_playing(self) -> None:
        self.game_timer -= 1

        if pyxel.btnp(pyxel.KEY_LEFT):
            self.bat_color_idx = (self.bat_color_idx - 1) % 4
            self.bat_color = BALL_COLORS[self.bat_color_idx]
        if pyxel.btnp(pyxel.KEY_RIGHT):
            self.bat_color_idx = (self.bat_color_idx + 1) % 4
            self.bat_color = BALL_COLORS[self.bat_color_idx]

        if self.super_timer > 0:
            self.super_timer -= 1

        self._update_heat()
        self._update_balls()

        if self.heat >= MAX_HEAT or self.game_timer <= 0:
            self.phase = Phase.GAME_OVER
            if self.score > self.high_score:
                self.high_score = self.score
            return

        self.ball_spawn_timer -= 1
        if self.ball_spawn_timer <= 0:
            self.balls.append(self._spawn_ball())
            self.ball_spawn_timer = self._get_spawn_interval()

    def _update_heat(self) -> None:
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_balls(self) -> None:
        for ball in self.balls:
            if not ball.active:
                continue

            if ball.flying_to_boundary:
                ball.x += ball.fly_vx
                ball.y += ball.fly_vy
                ball.fly_vy += 0.15
                if ball.y <= BOUNDARY_Y or ball.x > SCREEN_W:
                    ball.active = False
                continue

            ball.x += ball.vx

            if not ball.resolved and ball.x <= HIT_ZONE_X:
                result = self._resolve_hit(ball)
                if result == "hit":
                    ball.resolved = True
                    ball.flying_to_boundary = True
                    target_x = self._rng.uniform(120, SCREEN_W - 40)
                    target_y = float(BOUNDARY_Y)
                    dx = target_x - ball.x
                    dy = target_y - ball.y
                    dist = math.sqrt(dx * dx + dy * dy)
                    speed = 6.0
                    ball.fly_vx = (dx / dist) * speed
                    ball.fly_vy = (dy / dist) * speed
                    self._on_hit(ball)
                elif result == "miss":
                    ball.resolved = True
                    self._on_mismatch(ball)
                    ball.vx *= 0.5

            if ball.x < STUMP_X - 10:
                if not ball.resolved:
                    self.combo = 0
                    self.heat = min(self.heat + HEAT_PASS, MAX_HEAT)
                    self._shake_frames = 8
                    self.floating_texts.append(
                        FloatingText(STUMP_X, BAT_Y - 20, "WICKET!", 35, RED)
                    )
                ball.active = False

            if ball.x < -20:
                ball.active = False

        self.balls = [b for b in self.balls if b.active]

    def _on_hit(self, ball: Ball) -> None:
        multiplier = 3 if self.super_timer > 0 else 1
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        gained = 10 * self.combo * multiplier
        self.score += gained
        self._spawn_hit_particles(ball.x, ball.y, ball.color)

        if self.combo >= COMBO_SUPER and self.super_timer <= 0:
            self.super_timer = SUPER_DURATION
            self.floating_texts.append(
                FloatingText(SCREEN_W // 2 - 20, SCREEN_H // 2 - 20, "SUPER INNINGS!", 60, YELLOW)
            )

        self.floating_texts.append(
            FloatingText(ball.x + 15, ball.y - 10, f"+{gained}", 30, YELLOW)
        )
        if self.combo >= 2:
            self.floating_texts.append(
                FloatingText(ball.x + 15, ball.y - 22, f"COMBO x{self.combo}", 35, LIME)
            )

    def _on_mismatch(self, ball: Ball) -> None:
        self.combo = 0
        self.heat = min(self.heat + HEAT_MISMATCH, MAX_HEAT)
        self._shake_frames = 4
        self._spawn_miss_particles(ball.x, ball.y)
        self.floating_texts.append(
            FloatingText(ball.x, ball.y - 12, "WRONG!", 30, RED)
        )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vx *= 0.95
            p.vy *= 0.95
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        else:
            self._draw_gameplay()
            if self.phase == Phase.GAME_OVER:
                self._draw_game_over_overlay()

    def _draw_title(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, DARK_BLUE)
        title = "WICKET CHAIN"
        tw = len(title) * 8
        pyxel.text(SCREEN_W // 2 - tw // 2, 50, title, WHITE)

        instructions = [
            "LEFT/RIGHT arrows to change shot color",
            "Match ball color to HIT for a SIX!",
            "Same-color COMBO chain builds score",
            "COMBO x4 = SUPER INNINGS (auto-match!)",
            "Wrong color = HEAT. HEAT=100 = Game Over",
            "Survive 60 seconds!",
            "",
            "Press SPACE to Start",
        ]
        for i, line in enumerate(instructions):
            lw = len(line) * 4
            pyxel.text(SCREEN_W // 2 - lw // 2, 85 + i * 14, line, GRAY)

        if self.high_score > 0:
            hs_text = f"High Score: {self.high_score}"
            pyxel.text(SCREEN_W // 2 - len(hs_text) * 4, 200, hs_text, YELLOW)

        self._draw_demo_batter()

    def _draw_demo_batter(self) -> None:
        x = BAT_X
        y = BAT_Y
        pyxel.line(x, y - 16, x, y + 4, WHITE)
        pyxel.circ(x, y - 22, 5, WHITE)
        pyxel.line(x - 4, y - 10, x + 16, y - 6, BALL_COLORS[0])
        pyxel.rect(x - 4, y - 10, 6, 2, BALL_COLORS[0])

    def _draw_gameplay(self) -> None:
        shake_x = self._rng.randint(-2, 2) if self._shake_frames > 0 else 0
        shake_y = self._rng.randint(-2, 2) if self._shake_frames > 0 else 0

        self._draw_pitch(shake_x, shake_y)
        self._draw_stumps(shake_x, shake_y)
        self._draw_boundary(shake_x, shake_y)
        self._draw_fielders(shake_x, shake_y)
        self._draw_batter(shake_x, shake_y)
        self._draw_balls(shake_x, shake_y)
        self._draw_particles(shake_x, shake_y)
        self._draw_floating_texts(shake_x, shake_y)
        self._draw_hud()

    def _draw_pitch(self, sx: int, sy: int) -> None:
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, DARK_BLUE)
        pyxel.rect(0, SCREEN_H - 80, SCREEN_W, 80, GREEN)
        pyxel.rect(20, SCREEN_H - 74, SCREEN_W - 40, 68, BROWN)
        center_strip_y = SCREEN_H - 40
        pyxel.rect(20, center_strip_y - 3, SCREEN_W - 40, 6, GREEN)

    def _draw_stumps(self, sx: int, sy: int) -> None:
        x = STUMP_X + sx
        py = SCREEN_H - 80 + sy
        for i in range(3):
            stump_x = x + i * 6
            pyxel.rect(stump_x, py - 24, 3, 26, BROWN)
        pyxel.rect(x - 1, py - 24, 16, 3, BROWN)

    def _draw_boundary(self, sx: int, sy: int) -> None:
        y = BOUNDARY_Y + sy
        pyxel.line(30, y, SCREEN_W - 30, y, WHITE)
        pyxel.text(SCREEN_W // 2 - 24, y - 10, "BOUNDARY", WHITE)

    def _draw_fielders(self, sx: int, sy: int) -> None:
        fielder_positions = [
            (180, 80), (230, 100), (150, 70), (260, 120),
            (200, 60), (280, 80), (170, 110), (240, 60),
        ]
        for fx, fy in fielder_positions:
            px = fx + sx
            py = fy + sy
            c = self._rng.randint(0, 3)
            color = BALL_COLORS[c]
            f_alpha = (pyxel.frame_count // 15 + fx + fy) % 2
            if f_alpha == 0:
                pyxel.circ(px, py, 4, color)
                pyxel.circb(px, py, 4, WHITE)

    def _draw_batter(self, sx: int, sy: int) -> None:
        x = BAT_X + sx
        y = BAT_Y + sy
        leg_y = y + 4
        pyxel.line(x, y - 16, x, leg_y, WHITE)
        pyxel.circ(x, y - 22, 5, WHITE)
        pyxel.line(x + 4, leg_y, x + 6, leg_y + 8, WHITE)
        pyxel.line(x - 4, leg_y, x - 6, leg_y + 8, WHITE)
        pyxel.line(x, y - 12, x + 6, y - 8, WHITE)
        pyxel.line(x, y - 12, x - 6, y - 8, WHITE)

        if self.super_timer > 0:
            bat_color = RAINBOW_COLORS[(pyxel.frame_count // 4) % len(RAINBOW_COLORS)]
        else:
            bat_color = self.bat_color

        bat_len = 20
        bat_w = 4
        bat_x = x + 4
        bat_y = y - 10
        pyxel.rect(bat_x, bat_y - bat_w // 2, bat_len, bat_w, bat_color)
        pyxel.rect(bat_x + bat_len - 2, bat_y - bat_w // 2 - 2, 6, bat_w + 4, BROWN)

    def _draw_balls(self, sx: int, sy: int) -> None:
        for ball in self.balls:
            if not ball.active:
                continue
            bx = int(ball.x) + sx
            by = int(ball.y) + sy
            if ball.flying_to_boundary and self.super_timer > 0:
                trail_idx = (pyxel.frame_count // 3) % len(RAINBOW_COLORS)
                for t in range(3):
                    tx = bx - int(ball.fly_vx * t * 2)
                    ty = by - int(ball.fly_vy * t * 2)
                    tc = RAINBOW_COLORS[(trail_idx + t) % len(RAINBOW_COLORS)]
                    pyxel.circ(tx, ty, 3 - t, tc)
            pyxel.circ(bx, by, 4, ball.color)
            pyxel.circb(bx, by, 4, WHITE)

    def _draw_particles(self, sx: int, sy: int) -> None:
        for p in self.particles:
            if p.life <= 0:
                continue
            px = int(p.x) + sx
            py = int(p.y) + sy
            if p.life > 7:
                pyxel.rect(px, py, p.size, p.size, p.color)
            else:
                pyxel.rect(px, py, max(1, p.size - 1), max(1, p.size - 1), GRAY)

    def _draw_floating_texts(self, sx: int, sy: int) -> None:
        for ft in self.floating_texts:
            if ft.life <= 0:
                continue
            alpha = ft.life / 40.0
            if alpha > 0.15:
                pyxel.text(int(ft.x) + sx, int(ft.y) + sy, ft.text, ft.color)

    def _draw_hud(self) -> None:
        heat_bar_w = 80
        heat_bar_h = 8
        heat_bar_x = 8
        heat_bar_y = 8
        pyxel.rect(heat_bar_x, heat_bar_y, heat_bar_w, heat_bar_h, GRAY)
        heat_frac = self.heat / MAX_HEAT
        heat_fill = int(heat_bar_w * heat_frac)
        heat_color = GREEN if heat_frac < 0.5 else (ORANGE if heat_frac < 0.75 else RED)
        pyxel.rect(heat_bar_x, heat_bar_y, heat_fill, heat_bar_h, heat_color)
        pyxel.rectb(heat_bar_x, heat_bar_y, heat_bar_w, heat_bar_h, WHITE)
        pyxel.text(heat_bar_x + heat_bar_w + 4, heat_bar_y, f"HEAT {int(self.heat)}", WHITE)

        seconds_remaining = max(0, self.game_timer // 60)
        timer_str = f"{seconds_remaining:02d}"
        tw = len(timer_str) * 8
        timer_color = WHITE if seconds_remaining > 10 else RED
        if (seconds_remaining <= 10 and (pyxel.frame_count // 15) % 2 == 0):
            timer_color = RED
        pyxel.text(SCREEN_W - tw - 10, 8, timer_str, timer_color)

        score_str = f"SCORE: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_str) * 4, 8, score_str, WHITE)

        combo_str = f"COMBO: x{self.combo}"
        combo_color = WHITE
        if self.combo >= COMBO_SUPER:
            combo_color = RAINBOW_COLORS[(pyxel.frame_count // 4) % len(RAINBOW_COLORS)]
        elif self.combo >= 2:
            combo_color = LIME
        pyxel.text(SCREEN_W // 2 - len(combo_str) * 4, 20, combo_str, combo_color)

        bat_label = COLOR_NAMES[self.bat_color_idx]
        pyxel.text(BAT_X - 12, BAT_Y - 40, bat_label, self.bat_color)
        pyxel.rect(BAT_X - 14, BAT_Y - 38, 8, 2, self.bat_color)

        if self.super_timer > 0:
            border_c = RAINBOW_COLORS[(pyxel.frame_count // 4) % len(RAINBOW_COLORS)]
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, border_c)
            super_sec = self.super_timer / 60.0
            super_str = f"SUPER {super_sec:.1f}s"
            pyxel.text(SCREEN_W // 2 - len(super_str) * 4, 34, super_str, YELLOW)

    def _draw_game_over_overlay(self) -> None:
        pyxel.rect(50, 50, SCREEN_W - 100, SCREEN_H - 100, BLACK)
        pyxel.rectb(50, 50, SCREEN_W - 100, SCREEN_H - 100, RED)
        go_text = "GAME OVER"
        pyxel.text(SCREEN_W // 2 - len(go_text) * 4, 70, go_text, RED)
        score_text = f"SCORE: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_text) * 4, 95, score_text, WHITE)
        combo_text = f"MAX COMBO: {self.max_combo}"
        pyxel.text(SCREEN_W // 2 - len(combo_text) * 4, 115, combo_text, YELLOW)
        reason = "HEAT OVERLOAD!" if self.heat >= MAX_HEAT else "TIME UP!"
        pyxel.text(SCREEN_W // 2 - len(reason) * 4, 135, reason, GRAY)
        hs_text = f"BEST: {self.high_score}"
        pyxel.text(SCREEN_W // 2 - len(hs_text) * 4, 155, hs_text, YELLOW)
        retry_text = "Press SPACE to Retry"
        pyxel.text(SCREEN_W // 2 - len(retry_text) * 4, 180, retry_text, WHITE)


if __name__ == "__main__":
    Game()
