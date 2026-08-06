from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pyxel


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
    life: int
    color: int


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

COLORS = (RED, LIME, DARK_BLUE, YELLOW)
COLOR_NAMES = ("RED", "LIME", "DARK_BLUE", "YELLOW")


class Game:
    SCREEN_W = 320
    SCREEN_H = 240
    LAUNCH_Y_MIN = 30
    LAUNCH_Y_MAX = 200
    TUBE_X = 160
    TUBE_Y = 220
    TUBE_W = 20
    TUBE_H = 16
    FIREWORK_SPEED = 6.0
    SUPER_DURATION = 300
    GAME_DURATION = 1800
    HEAT_MAX = 100
    HEAT_DECAY = 0.02
    HEAT_MISMATCH = 15
    AUTO_CYCLE_INIT = 300
    AUTO_CYCLE_MIN = 90
    COLORS = (RED, LIME, DARK_BLUE, YELLOW)
    COLOR_NAMES = ("RED", "LIME", "DARK_BLUE", "YELLOW")
    RAINBOW = (RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PINK, PEACH)

    def __init__(self) -> None:
        pyxel.init(self.SCREEN_W, self.SCREEN_H, title="Blast Chain", fps=30)
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = "TITLE"
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = self.GAME_DURATION
        self.last_fired_color = 0
        self.next_color_index = 1
        self.super_mode = False
        self.super_timer = 0
        self.firework_active = False
        self.firework_x = 0.0
        self.firework_y = 0.0
        self.firework_target_x = 0.0
        self.firework_target_y = 0.0
        self.firework_color = 0
        self.color_index = 0
        self.auto_cycle_timer = self.AUTO_CYCLE_INIT
        self.auto_cycle_interval = self.AUTO_CYCLE_INIT
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.best_score = getattr(self, "best_score", 0)
        self.tube_glow = 0
        self.stars: list[tuple[int, int, int]] = [
            (self._rng.randint(0, self.SCREEN_W - 1), self._rng.randint(0, 180), self._rng.randint(0, 1))
            for _ in range(40)
        ]
        self._auto_cycle_elapsed = 0

    @property
    def next_color(self) -> int:
        return self.COLORS[self.color_index % len(self.COLORS)]

    def _cycle_to_next_color(self) -> None:
        self.color_index = (self.color_index + 1) % len(self.COLORS)

    # ---- Update ----

    def update(self) -> None:
        if self.phase == "TITLE":
            self._update_title()
        elif self.phase == "PLAYING":
            self._update_playing()
        elif self.phase == "GAME_OVER":
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = "PLAYING"

    def _update_playing(self) -> None:
        self._update_timer()
        self._update_heat()
        self._update_auto_cycle()
        self._update_firework()
        self._update_particles()
        self._update_floating_texts()
        self._check_game_over()

        if not self.firework_active and pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            tx = float(pyxel.mouse_x)
            ty = float(pyxel.mouse_y)
            if ty > self.LAUNCH_Y_MAX:
                ty = self.LAUNCH_Y_MAX
            if ty < self.LAUNCH_Y_MIN:
                ty = self.LAUNCH_Y_MIN
            self._start_launch(tx, ty)

        if self.tube_glow > 0:
            self.tube_glow -= 1

        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.combo = 0

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = "PLAYING"

    def _start_launch(self, target_x: float, target_y: float) -> None:
        self.firework_active = True
        self.firework_x = float(self.TUBE_X)
        self.firework_y = float(self.TUBE_Y)
        self.firework_target_x = target_x
        self.firework_target_y = target_y
        self.firework_color = self.next_color
        self.tube_glow = 30

    def _update_firework(self) -> None:
        if not self.firework_active:
            return

        dx = self.firework_target_x - self.firework_x
        dy = self.firework_target_y - self.firework_y
        dist = math.hypot(dx, dy)

        if dist <= self.FIREWORK_SPEED:
            self.firework_x = self.firework_target_x
            self.firework_y = self.firework_target_y
            self._burst_firework()
        else:
            self.firework_x += dx / dist * self.FIREWORK_SPEED
            self.firework_y += dy / dist * self.FIREWORK_SPEED

    def _burst_firework(self) -> None:
        launched_color = self.firework_color
        last_color = self.last_fired_color
        self.last_fired_color = launched_color
        self.firework_active = False
        self._cycle_to_next_color()

        multiplier = 3.0 if self.super_mode else 1.0

        if self.super_mode or launched_color == last_color:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo

            points = int(10 * self.combo * multiplier)
            self.score += points
            self._spawn_particles(
                int(self.firework_x), int(self.firework_y),
                launched_color, 25
            )
            self.floating_texts.append(FloatingText(
                self.firework_x, self.firework_y - 5,
                f"+{points}", 40, WHITE
            ))
            self.floating_texts.append(FloatingText(
                self.firework_x, self.firework_y + 6,
                f"COMBO x{self.combo}", 40, ORANGE
            ))

            if self.combo >= 4 and not self.super_mode:
                self.super_mode = True
                self.super_timer = self.SUPER_DURATION
                self._spawn_particles(
                    int(self.firework_x), int(self.firework_y),
                    launched_color, 55
                )
                self.floating_texts.append(FloatingText(
                    self.firework_x, self.firework_y - 15,
                    "SUPER FINALE!", 60, YELLOW
                ))
        else:
            self.heat += self.HEAT_MISMATCH
            if self.heat > self.HEAT_MAX:
                self.heat = self.HEAT_MAX
            self.combo = 0
            self.super_mode = False
            self.super_timer = 0

            points = int(1 * multiplier)
            self.score += points
            self._spawn_particles(
                int(self.firework_x), int(self.firework_y),
                GRAY, 4
            )
            self.floating_texts.append(FloatingText(
                self.firework_x, self.firework_y - 5,
                f"+{points} (MISS)", 30, GRAY
            ))

    def _spawn_particles(self, cx: int, cy: int, base_color: int, count: int) -> None:
        is_super = self.super_mode and count >= 50
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 5.0) if not is_super else self._rng.uniform(2.0, 7.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 0.5
            life = self._rng.randint(20, 60) if not is_super else self._rng.randint(40, 80)
            if is_super:
                color = self._rng.choice(self.RAINBOW)
            else:
                color = base_color
            self.particles.append(Particle(float(cx), float(cy), vx, vy, life, color))

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.life -= 1
            if p.life <= 0:
                continue
            p.vy += 0.1
            p.x += p.vx
            p.y += p.vy
            alive.append(p)
        self.particles = alive

    def _update_floating_texts(self) -> None:
        alive: list[FloatingText] = []
        for t in self.floating_texts:
            t.life -= 1
            if t.life <= 0:
                continue
            t.y -= 0.5
            alive.append(t)
        self.floating_texts = alive

    def _update_heat(self) -> None:
        self.heat -= self.HEAT_DECAY
        if self.heat < 0:
            self.heat = 0

    def _update_timer(self) -> None:
        self.timer -= 1
        if self.timer < 0:
            self.timer = 0

    def _update_auto_cycle(self) -> None:
        self._auto_cycle_elapsed += 1
        if self._auto_cycle_elapsed >= 60:
            self._auto_cycle_elapsed -= 60
            self.auto_cycle_interval = max(self.AUTO_CYCLE_MIN, self.auto_cycle_interval - 3)

        self.auto_cycle_timer -= 1
        if self.auto_cycle_timer <= 0:
            self._cycle_to_next_color()
            self.auto_cycle_timer = self.auto_cycle_interval

    def _check_game_over(self) -> None:
        if self.timer <= 0 or self.heat >= self.HEAT_MAX:
            self.phase = "GAME_OVER"
            if self.score > self.best_score:
                self.best_score = self.score

    # ---- Draw ----

    def draw(self) -> None:
        pyxel.cls(NAVY)
        self._draw_stars()

        if self.phase == "TITLE":
            self._draw_title()
        elif self.phase == "PLAYING":
            self._draw_playing()
        elif self.phase == "GAME_OVER":
            self._draw_playing()
            self._draw_game_over()

    def _draw_stars(self) -> None:
        for sx, sy, c in self.stars:
            pyxel.pset(sx, sy, WHITE if c == 0 else LIGHT_BLUE)

    def _draw_title(self) -> None:
        pyxel.text(self.SCREEN_W // 2 - 38, 60, "BLAST CHAIN", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 55, 80, "Fireworks Display", LIGHT_BLUE)
        pyxel.text(self.SCREEN_W // 2 - 64, 110, "Click the night sky to launch", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 68, 122, "Match colors to build COMBO chain!", CYAN)
        pyxel.text(self.SCREEN_W // 2 - 64, 134, "COMBO x4 triggers SUPER FINALE!", YELLOW)
        pyxel.text(self.SCREEN_W // 2 - 40, 154, "Avoid overheating!", RED)
        pyxel.text(self.SCREEN_W // 2 - 50, 190, "Press SPACE or CLICK", WHITE)
        self._draw_tube()

    def _draw_playing(self) -> None:
        pyxel.rect(0, self.LAUNCH_Y_MAX, self.SCREEN_W, self.SCREEN_H - self.LAUNCH_Y_MAX, BROWN)
        self._draw_hud()
        self._draw_tube()
        self._draw_firework()
        self._draw_particles()
        self._draw_floating_texts()

    def _draw_game_over(self) -> None:
        pyxel.rect(self.SCREEN_W // 2 - 70, self.SCREEN_H // 2 - 40, 140, 80, BLACK)
        pyxel.rectb(self.SCREEN_W // 2 - 70, self.SCREEN_H // 2 - 40, 140, 80, WHITE)
        pyxel.text(self.SCREEN_W // 2 - 30, self.SCREEN_H // 2 - 30, "GAME OVER", RED)
        pyxel.text(self.SCREEN_W // 2 - 55, self.SCREEN_H // 2 - 15, f"SCORE: {self.score}", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 55, self.SCREEN_H // 2, f"BEST:  {self.best_score}", YELLOW)
        pyxel.text(self.SCREEN_W // 2 - 55, self.SCREEN_H // 2 + 20, "PRESS SPACE TO RETRY", CYAN)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 20, 4, f"COMBO x{self.combo}", ORANGE if self.combo >= 3 else WHITE)
        seconds = max(0, self.timer // 30)
        time_color = RED if seconds <= 10 else WHITE
        pyxel.text(self.SCREEN_W - 56, 4, f"TIME: {seconds}", time_color)

        bar_x = self.SCREEN_W // 2 - 25
        bar_y = 14
        bar_w = 50
        pyxel.text(bar_x - 22, bar_y, "HEAT", RED)
        pyxel.rectb(bar_x, bar_y, bar_w, 6, RED)
        fill_w = int(bar_w * (self.heat / self.HEAT_MAX))
        heat_fill_color = ORANGE if self.heat > 70 else RED
        pyxel.rect(bar_x, bar_y, fill_w, 6, heat_fill_color)

        if self.super_mode:
            sec = max(1, self.super_timer // 30)
            pyxel.text(self.SCREEN_W // 2 - 35, self.SCREEN_H - 16, f"SUPER: {sec}s", YELLOW)

    def _draw_tube(self) -> None:
        tx = self.TUBE_X
        ty = self.TUBE_Y
        pyxel.rect(tx - self.TUBE_W // 2, ty - self.TUBE_H // 2, self.TUBE_W, self.TUBE_H, GRAY)
        pyxel.rect(tx - 6, ty - self.TUBE_H // 2 - 4, 12, 4, DARK_BLUE)

        if self.phase == "PLAYING":
            ring_color = self.last_fired_color if self.last_fired_color != 0 else self.next_color
            if self.super_mode:
                ring_color_idx = (pyxel.frame_count // 4) % len(self.RAINBOW)
                ring_color = self.RAINBOW[ring_color_idx]

            if self.tube_glow > 0:
                glow_alpha = self.tube_glow / 30
                gw = int(self.TUBE_W + 4 + glow_alpha * 4)
                gh = int(self.TUBE_H + 4 + glow_alpha * 4)
                pyxel.rectb(tx - gw // 2, ty - gh // 2, gw, gh, ring_color)
            else:
                pyxel.rectb(tx - self.TUBE_W // 2 - 2, ty - self.TUBE_H // 2 - 2,
                            self.TUBE_W + 4, self.TUBE_H + 4, ring_color)

    def _draw_firework(self) -> None:
        if not self.firework_active:
            return
        fx = int(self.firework_x)
        fy = int(self.firework_y)
        pyxel.pset(fx, fy, self.firework_color)
        pyxel.pset(fx, fy + 1, self.firework_color)
        pyxel.pset(fx + 1, fy, self.firework_color)
        pyxel.pset(fx - 1, fy, self.firework_color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            color = p.color
            if p.life < 10:
                color = max(NAVY, color - 1)
            pyxel.pset(int(p.x), int(p.y), color)

    def _draw_floating_texts(self) -> None:
        for t in self.floating_texts:
            alpha = t.life / 40
            color = t.color if alpha > 0.5 else GRAY
            pyxel.text(int(t.x) - len(t.text) * 2, int(t.y), t.text, color)


if __name__ == "__main__":
    Game()
