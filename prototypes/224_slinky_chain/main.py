"""Slinky Chain - A timing-based color-match slinky descent game."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Step:
    x: float
    y: float
    width: int
    height: int
    color: int


@dataclass
class Slinky:
    x: float
    y: float
    color: int
    on_step_index: int
    flipping: bool
    flip_timer: int
    vy: float


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


SCREEN_W = 320
SCREEN_H = 240
STEP_W = 80
STEP_H = 20
STEP_GAP_X = 60
STEP_GAP_Y = 30
NUM_STEPS = 8
STAIRS_START_X = 30
STAIRS_START_Y = 40
SLINKY_W = 20
SLINKY_H = 24
COMBO_THRESHOLD = 4
SUPER_DURATION = 300
GAME_DURATION = 3600
HEAT_MAX = 100
HEAT_WRONG = 15
HEAT_DECAY = 0.05
COLOR_CYCLE = 90
FLIP_DURATION = 20
IDLE_WOBBLE = 180
IDLE_FALL = 240
SCROLL_THRESHOLD = 3
AUTO_FLIP_INTERVAL = 30

COLORS = [8, 3, 5, 10]
COLOR_NAMES = ["RED", "GREEN", "BLUE", "YELLOW"]

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


class Game:
    def __init__(self) -> None:
        self.phase: Phase = Phase.TITLE
        pyxel.init(SCREEN_W, SCREEN_H, title="Slinky Chain")
        self._setup_sounds()
        self.phase = Phase.TITLE
        self.screen_shake: int = 0
        self._reset_state()
        pyxel.run(self.update, self.draw)

    def _setup_sounds(self) -> None:
        pyxel.sounds[0].set("c3e3g3c4", "p", "6", "n", 15)
        pyxel.sounds[1].set("b1", "n", "6", "n", 20)
        pyxel.sounds[2].set("c4e4g4c5e5", "t", "7", "vffn", 30)
        pyxel.sounds[3].set("c4b3a3g3f3", "t", "7", "n", 40)

    def _reset_state(self) -> None:
        self.steps: list[Step] = []
        self.slinky: Slinky = Slinky(0, 0, 0, 0, False, 0, 0.0)
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.score: int = 0
        self.best_score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.timer: int = GAME_DURATION
        self.super_active: bool = False
        self.super_timer: int = 0
        self.multiplier: float = 1.0
        self.idle_timer: int = 0
        self.wobble_phase: float = 0.0
        self.scroll_x: float = 0.0
        self.steps_descended: int = 0
        self.best_path: list[tuple[float, float]] = []
        self.current_path: list[tuple[float, float]] = []
        self.color_timer: int = 0
        self.super_flip_timer: int = AUTO_FLIP_INTERVAL
        self.game_over_reason: str = ""
        self.screen_shake: int = 0
        self._generate_steps(for_reset=True)
        step = self.steps[0]
        self.slinky.x = step.x + step.width / 2
        self.slinky.y = step.y - SLINKY_H / 2
        self.slinky.on_step_index = 0
        self.slinky.color = random.randint(0, 3)
        self.color_timer = 0

    def _generate_steps(self, for_reset: bool = False) -> None:
        if for_reset:
            self.steps.clear()
            for i in range(NUM_STEPS):
                x = float(STAIRS_START_X + i * STEP_GAP_X)
                y = float(STAIRS_START_Y + i * STEP_GAP_Y)
                color = random.randint(0, 3)
                self.steps.append(Step(x, y, STEP_W, STEP_H, color))
        else:
            while len(self.steps) <= self.slinky.on_step_index + 5:
                last = self.steps[-1]
                x = last.x + STEP_GAP_X
                y = last.y + STEP_GAP_Y
                color = random.randint(0, 3)
                self.steps.append(Step(x, y, STEP_W, STEP_H, color))

    def _flip_slinky(self) -> bool:
        if self.slinky.flipping:
            return False
        if self.slinky.on_step_index < 0:
            return False
        if self.slinky.on_step_index >= len(self.steps) - 1:
            self._generate_steps()
        self.slinky.flipping = True
        self.slinky.flip_timer = FLIP_DURATION
        self.idle_timer = 0
        return True

    def _check_match(self) -> bool:
        if self.slinky.on_step_index < 0 or self.slinky.on_step_index >= len(self.steps):
            return False
        step = self.steps[self.slinky.on_step_index]
        return self.slinky.color == step.color

    def _update_heat(self, delta: float) -> None:
        self.heat = max(0.0, min(float(HEAT_MAX), self.heat + delta))

    def _check_game_over(self) -> str:
        if self.heat >= HEAT_MAX:
            return "OVERHEAT"
        if self.timer <= 0:
            return "TIME"
        if self.slinky.on_step_index < 0:
            return "FALL"
        return ""

    def _update_timer(self) -> None:
        if self.timer > 0:
            self.timer -= 1

    def _activate_super(self) -> None:
        self.super_active = True
        self.super_timer = SUPER_DURATION
        self.multiplier = 3.0
        self.super_flip_timer = AUTO_FLIP_INTERVAL

    def _update_super(self) -> None:
        if not self.super_active:
            return
        self.super_timer -= 1
        if self.super_timer <= 0:
            self.super_active = False
            self.multiplier = 1.0

    def _complete_flip(self) -> None:
        self.slinky.on_step_index += 1
        self.slinky.flipping = False
        self.slinky.flip_timer = 0
        step = self.steps[self.slinky.on_step_index]
        self.slinky.x = step.x + step.width / 2
        self.slinky.y = step.y - SLINKY_H / 2
        self.steps_descended += 1

        if self.super_active:
            points = int(10 * self.combo * self.multiplier)
            self.score += points
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            self._spawn_match_particles()
            self._spawn_floating_text(
                self.slinky.x, self.slinky.y - 10, f"+{points}", YELLOW
            )
        elif self._check_match():
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            points = int(10 * self.combo * self.multiplier)
            self.score += points
            self._spawn_match_particles()
            self._spawn_floating_text(
                self.slinky.x, self.slinky.y - 10, f"+{points}", COLORS[step.color]
            )
            if self.combo >= COMBO_THRESHOLD and not self.super_active:
                self._activate_super()
                self._spawn_super_particles()
                self._spawn_floating_text(
                    self.slinky.x, self.slinky.y - 20, "SUPER!", YELLOW
                )
        else:
            self.combo = 0
            self._update_heat(HEAT_WRONG)
            self._spawn_mismatch_particles()
            self._spawn_floating_text(
                self.slinky.x, self.slinky.y - 10, "MISS", GRAY
            )
            self.screen_shake = 8

        self.idle_timer = 0

    def _spawn_match_particles(self) -> None:
        step = self.steps[self.slinky.on_step_index]
        px = self.slinky.x
        py = step.y
        pc = COLORS[step.color]
        for _ in range(random.randint(5, 8)):
            angle = random.uniform(-math.pi, -math.pi * 0.3)
            speed = random.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x=px + random.uniform(-5, 5),
                    y=py,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=random.randint(15, 30),
                    color=pc,
                )
            )

    def _spawn_mismatch_particles(self) -> None:
        px = self.slinky.x
        py = self.steps[self.slinky.on_step_index].y
        for _ in range(random.randint(3, 5)):
            angle = random.uniform(-math.pi * 0.5, -math.pi * 0.1)
            speed = random.uniform(0.5, 2.0)
            self.particles.append(
                Particle(
                    x=px + random.uniform(-5, 5),
                    y=py,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=random.randint(10, 20),
                    color=GRAY,
                )
            )

    def _spawn_super_particles(self) -> None:
        px = self.slinky.x
        py = self.slinky.y
        for _ in range(random.randint(20, 30)):
            angle = random.uniform(-math.pi, 0)
            speed = random.uniform(1.0, 4.0)
            self.particles.append(
                Particle(
                    x=px + random.uniform(-10, 10),
                    y=py,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=random.randint(20, 40),
                    color=COLORS[random.randint(0, 3)],
                )
            )

    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=40, color=color)
        )

    def _start_fall(self) -> None:
        self.slinky.on_step_index = -1
        self.slinky.vy = -2.0
        self.game_over_reason = "FALL"

    def _on_game_over(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score
            self.best_path = list(self.current_path)

    def update(self) -> None:
        if self.screen_shake > 0:
            self.screen_shake -= 1

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()
        else:
            self._update_playing()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.phase = Phase.PLAYING
            self._reset_state()

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self.phase = Phase.PLAYING
            self._reset_state()

    def _update_playing(self) -> None:
        self._update_timer()

        if self.slinky.on_step_index < 0:
            self.slinky.vy += 0.5
            self.slinky.y += self.slinky.vy
            if self.slinky.y > SCREEN_H + 50:
                self._on_game_over()
            return

        reason = self._check_game_over()
        if reason:
            if reason == "TIME":
                self.game_over_reason = "TIME"
                self._on_game_over()
            elif reason == "OVERHEAT":
                self.game_over_reason = "OVERHEAT"
                self._on_game_over()
            return

        self._update_heat(-HEAT_DECAY)

        if not self.slinky.flipping:
            self.idle_timer += 1
            if self.idle_timer >= IDLE_FALL:
                self._start_fall()
                self._on_game_over()
                return

        self.color_timer += 1
        if self.color_timer >= COLOR_CYCLE:
            self.color_timer = 0
            if not self.super_active:
                self.slinky.color = (self.slinky.color + 1) % 4

        self._update_super()

        if self.super_active:
            self.super_flip_timer -= 1
            if self.super_flip_timer <= 0 and not self.slinky.flipping:
                self._flip_slinky()
                self.super_flip_timer = AUTO_FLIP_INTERVAL

        if (
            pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN)
        ) and not self.super_active:
            if self.slinky.on_step_index >= 0 and not self.slinky.flipping:
                self._flip_slinky()

        if self.slinky.flipping:
            self.slinky.flip_timer -= 1
            if self.slinky.flip_timer <= 0:
                self._complete_flip()
            else:
                t = 1.0 - self.slinky.flip_timer / FLIP_DURATION
                start_step = self.steps[self.slinky.on_step_index]
                end_step = self.steps[self.slinky.on_step_index + 1]
                start_x = start_step.x + start_step.width / 2
                start_y = start_step.y - SLINKY_H / 2
                end_x = end_step.x + end_step.width / 2
                end_y = end_step.y - SLINKY_H / 2
                self.slinky.x = start_x + (end_x - start_x) * t
                arc = -STEP_GAP_Y * 1.5 * math.sin(t * math.pi)
                self.slinky.y = start_y + (end_y - start_y) * t + arc

        if self.slinky.on_step_index >= SCROLL_THRESHOLD:
            target_scroll = (
                self.slinky.on_step_index - SCROLL_THRESHOLD
            ) * STEP_GAP_X
            self.scroll_x += (target_scroll - self.scroll_x) * 0.1

        if self.slinky.on_step_index >= len(self.steps) - 3:
            self._generate_steps()

        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

        for ft in self.floating_texts[:]:
            ft.y -= 0.8
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

        if pyxel.frame_count % 4 == 0 and self.slinky.on_step_index >= 0:
            self.current_path.append((self.slinky.x, self.slinky.y))
            if len(self.current_path) > 900:
                self.current_path = self.current_path[-900:]

    def draw(self) -> None:
        pyxel.cls(NAVY)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.GAME_OVER:
            self._draw_world()
            self._draw_game_over()
        else:
            self._draw_world()
            self._draw_hud()

    def _draw_title(self) -> None:
        T = pyxel.frame_count
        pyxel.text(SCREEN_W // 2 - 38, 60, "SLINKY CHAIN", WHITE)
        y = 90
        for i, name in enumerate(COLOR_NAMES):
            tx = SCREEN_W // 2 - 35 + i * 20
            bounce = int(math.sin(T * 0.05 + i * 1.2) * 4)
            pyxel.rect(tx, y + bounce - 2, 14, 10, COLORS[i])
        pyxel.text(SCREEN_W // 2 - 55, 120, "Press SPACE to Start", LIME)
        pyxel.text(SCREEN_W // 2 - 70, 140, "Match colors to build COMBO!", LIGHT_BLUE)
        pyxel.text(SCREEN_W // 2 - 65, 152, "COMBO x4 = SUPER SLINKY!", YELLOW)
        pyxel.text(SCREEN_W // 2 - 40, 172, "Space: Flip  R: Restart", GRAY)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 30, 40, "GAME OVER", RED)
        reason_texts = {
            "FALL": "Slinky fell off the stairs!",
            "OVERHEAT": "Slinky overheated!",
            "TIME": "Time's up! You survived!",
        }
        reason = reason_texts.get(self.game_over_reason, "")
        pyxel.text(SCREEN_W // 2 - len(reason) * 2, 60, reason, GRAY)
        pyxel.text(
            SCREEN_W // 2 - 35, 80, f"Score: {self.score}", WHITE
        )
        pyxel.text(
            SCREEN_W // 2 - 35, 92, f"Best: {self.best_score}", YELLOW
        )
        pyxel.text(
            SCREEN_W // 2 - 35, 104, f"Max Combo: {self.max_combo}", LIGHT_BLUE
        )
        pyxel.text(
            SCREEN_W // 2 - 35, 116, f"Steps: {self.steps_descended}", GRAY
        )
        pyxel.text(
            SCREEN_W // 2 - 55, 150, "Press SPACE to Restart", LIME
        )

    def _draw_world(self) -> None:
        pyxel.camera(int(self.scroll_x), 0)
        shake_x = 0
        shake_y = 0
        if self.screen_shake > 0:
            shake_x = random.randint(-2, 2)
            shake_y = random.randint(-2, 2)

        visible_steps = [
            s
            for s in self.steps
            if s.x - self.scroll_x + STEP_W > 0
            and s.x - self.scroll_x < SCREEN_W
        ]
        for step in visible_steps:
            sx = step.x + shake_x
            sy = step.y + shake_y
            pyxel.rect(sx, sy, step.width, step.height, COLORS[step.color])
            pyxel.rectb(sx, sy, step.width, step.height, WHITE)

        for i, (px, py) in enumerate(self.best_path):
            alpha = 10
            if i % 3 == 0:
                px_screen = px + shake_x
                py_screen = py + shake_y
                if 0 <= px_screen - self.scroll_x <= SCREEN_W and 0 <= py_screen <= SCREEN_H:
                    pyxel.pset(px_screen, py_screen, alpha)

        self._draw_slinky(shake_x, shake_y)
        self._draw_particles(shake_x, shake_y)
        self._draw_floating_texts(shake_x, shake_y)

        pyxel.camera(0, 0)

    def _draw_slinky(self, shake_x: int, shake_y: int) -> None:
        if self.slinky.on_step_index < 0:
            x = self.slinky.x + shake_x
            y = self.slinky.y + shake_y
            color = COLORS[self.slinky.color]
            pyxel.rectb(x - SLINKY_W / 2, y - SLINKY_H / 2, SLINKY_W, SLINKY_H, color)
            pyxel.line(
                x - SLINKY_W / 2, y, x + SLINKY_W / 2, y, color
            )
            return

        x = self.slinky.x + shake_x
        y = self.slinky.y + shake_y

        wobble_x = 0.0
        if self.idle_timer >= IDLE_WOBBLE and not self.slinky.flipping:
            wobble_x = math.sin(pyxel.frame_count * 0.5) * 2.0
        x += wobble_x

        if self.super_active:
            color = COLORS[(pyxel.frame_count // 4) % 4]
        else:
            color = COLORS[self.slinky.color]

        half_w = SLINKY_W / 2
        half_h = SLINKY_H / 2
        segments = 4
        seg_h = SLINKY_H / segments
        for i in range(segments):
            y1 = y - half_h + i * seg_h
            y2 = y - half_h + (i + 1) * seg_h
            if i % 2 == 0:
                pyxel.line(x - half_w, y1, x + half_w, y2, color)
            else:
                pyxel.line(x + half_w, y1, x - half_w, y2, color)

        if self.super_active:
            glow_color = COLORS[(pyxel.frame_count // 2) % 4]
            pyxel.rectb(
                x - half_w - 2, y - half_h - 2, SLINKY_W + 4, SLINKY_H + 4, glow_color
            )

        if self.slinky.flipping:
            trail_count = 3
            for ti in range(1, trail_count + 1):
                trail_x = x - wobble_x
                trail_y = y
                trail_color = COLORS[self.slinky.color]
                pyxel.pset(
                    trail_x - ti * 2,
                    trail_y,
                    trail_color if ti % 2 == 0 else WHITE,
                )

    def _draw_particles(self, shake_x: int, shake_y: int) -> None:
        for p in self.particles:
            px = p.x + shake_x
            py = p.y + shake_y
            if p.life > 10:
                pyxel.pset(px, py, p.color)
            else:
                alpha_color = p.color if p.life % 2 == 0 else BLACK
                pyxel.pset(px, py, alpha_color)

    def _draw_floating_texts(self, shake_x: int, shake_y: int) -> None:
        for ft in self.floating_texts:
            x = ft.x + shake_x
            y = ft.y + shake_y
            if ft.life > 10:
                pyxel.text(x - len(ft.text) * 2, y, ft.text, ft.color)

    def _draw_hud(self) -> None:
        pyxel.text(8, 8, f"SCORE: {self.score}", WHITE)
        combo_color = YELLOW if self.combo >= COMBO_THRESHOLD else LIGHT_BLUE
        pyxel.text(8, 18, f"COMBO: x{self.combo}", combo_color)

        bar_x = SCREEN_W - 100
        bar_y = 8
        bar_w = 80
        bar_h = 8
        heat_ratio = self.heat / HEAT_MAX
        bar_color = RED if self.heat > 60 else ORANGE if self.heat > 30 else LIME
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        pyxel.rect(bar_x, bar_y, int(bar_w * heat_ratio), bar_h, bar_color)
        pyxel.text(bar_x - 32, bar_y, "HEAT", WHITE)

        seconds = max(0, self.timer // 60)
        timer_color = WHITE if seconds > 10 else RED if seconds % 2 == 0 else YELLOW
        pyxel.text(SCREEN_W - 50, 20, f"TIME: {seconds:02d}", timer_color)

        if self.super_active:
            super_bar_x = SCREEN_W - 100
            super_bar_y = 30
            super_bar_w = 80
            super_bar_h = 6
            super_ratio = self.super_timer / SUPER_DURATION
            pyxel.rect(super_bar_x, super_bar_y, super_bar_w, super_bar_h, GRAY)
            pyxel.rect(
                super_bar_x,
                super_bar_y,
                int(super_bar_w * super_ratio),
                super_bar_h,
                YELLOW,
            )
            rainbow_color = COLORS[(pyxel.frame_count // 3) % 4]
            pyxel.text(super_bar_x - 32, super_bar_y - 2, "SUPER!", rainbow_color)

        pyxel.text(8, 30, f"STEPS: {self.steps_descended}", GRAY)

        warn_x = SCREEN_W // 2 - 40
        warn_y = SCREEN_H - 20
        if self.idle_timer >= IDLE_WOBBLE and self.slinky.on_step_index >= 0:
            warn_text = "FLIP NOW!" if self.idle_timer < IDLE_FALL - 30 else "!!!"
            warn_color = YELLOW if pyxel.frame_count % 30 < 15 else RED
            pyxel.text(warn_x, warn_y, warn_text, warn_color)


if __name__ == "__main__":
    Game()
