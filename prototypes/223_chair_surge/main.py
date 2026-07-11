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
CIRCLE_CX = 160
CIRCLE_CY = 115
CIRCLE_R = 75
NUM_CHAIRS = 8
NUM_COLORS = 4
COLOR_VALS: tuple[int, int, int, int] = (RED, LIME, DARK_BLUE, YELLOW)
COLOR_NAMES: tuple[str, str, str, str] = ("RED", "LIME", "BLUE", "YEL")
CHAIR_TIME_START = 90
CHAIR_TIME_MIN = 30
HEAT_MAX = 100
HEAT_MISMATCH = 15
COMBO_SUPER = 4
SUPER_DURATION = 150
GAME_DURATION = 60 * 30
SIT_ANIM_FRAMES = 15
PLAYER_SPEED = 0.08

RAINBOW_COLORS: tuple[int, ...] = (RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK)


class Phase(IntEnum):
    TITLE = 0
    PLAYING = 1
    SIT_ANIM = 2
    COMPRESS = 3
    SUPER = 4
    GAME_OVER = 5


@dataclass
class Chair:
    angle: float
    target_angle: float
    color: int
    active: bool = True
    spawn_appear: int = 0


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


class Game:
    def __init__(self) -> None:
        font_path = str(Path(__file__).with_name("k8x12.bdf"))
        pyxel.init(SCREEN_W, SCREEN_H, title="CHAIR SURGE", display_scale=2)
        pyxel.load(font_path, exclude_images=True, exclude_tilemaps=True, exclude_sounds=True, exclude_musics=True)
        self._rng: random.Random = random.Random()
        self.phase: Phase = Phase.TITLE
        self.chairs: list[Chair] = []
        self.player_angle: float = 0.0
        self.timer: int = CHAIR_TIME_START
        self.overall_timer: int = GAME_DURATION
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.heat: float = 0.0
        self.last_color: int | None = None
        self.super_timer: int = 0
        self.sit_flash: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._reset()
        pyxel.run(self._update, self._draw)

    def _reset(self) -> None:
        self.phase = Phase.PLAYING
        self.chairs = []
        for i in range(NUM_CHAIRS):
            angle = 2.0 * math.pi * i / NUM_CHAIRS
            color = self._rng.choice(COLOR_VALS)
            self.chairs.append(Chair(angle=angle, target_angle=angle, color=color))
        self.player_angle = 0.0
        self.timer = CHAIR_TIME_START
        self.overall_timer = GAME_DURATION
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.heat = 0.0
        self.last_color = None
        self.super_timer = 0
        self.sit_flash = 0
        self.particles.clear()
        self.floating_texts.clear()

    def _update(self) -> None:
        self._update_particles()
        self._update_floating_texts()

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self._reset()

        elif self.phase == Phase.PLAYING:
            self.overall_timer -= 1
            if pyxel.btn(pyxel.KEY_LEFT):
                self.player_angle -= PLAYER_SPEED
            if pyxel.btn(pyxel.KEY_RIGHT):
                self.player_angle += PLAYER_SPEED
            self.player_angle %= 2.0 * math.pi

            if self.super_timer > 0:
                self.super_timer -= 1

            chairs_alive = sum(1 for c in self.chairs if c.active)
            if chairs_alive > 0:
                self.timer -= 1
                if self.timer <= 0:
                    self.phase = Phase.SIT_ANIM
                    self.sit_flash = SIT_ANIM_FRAMES
            else:
                self._respawn_all_chairs()
                self.timer = max(CHAIR_TIME_MIN, CHAIR_TIME_START - self.score // 50)

            if self.overall_timer <= 0:
                self.phase = Phase.GAME_OVER

        elif self.phase == Phase.SIT_ANIM:
            self.sit_flash -= 1
            if self.sit_flash <= 0:
                self._resolve_sit()

        elif self.phase == Phase.COMPRESS:
            all_done = True
            for chair in self.chairs:
                if not chair.active:
                    continue
                diff = chair.target_angle - chair.angle
                if abs(diff) < 0.01:
                    chair.angle = chair.target_angle
                else:
                    chair.angle += diff * 0.15
                    all_done = False
            if all_done:
                self._spawn_chair()
                if self.combo >= COMBO_SUPER and self.super_timer <= 0:
                    self.super_timer = SUPER_DURATION
                self.timer = max(CHAIR_TIME_MIN, CHAIR_TIME_START - self.score // 50)
                self.phase = Phase.PLAYING

        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.phase = Phase.TITLE
                self._reset()

    def _resolve_sit(self) -> None:
        active_chairs = [c for c in self.chairs if c.active]
        if not active_chairs:
            self._respawn_all_chairs()
            self.phase = Phase.PLAYING
            self.timer = max(CHAIR_TIME_MIN, CHAIR_TIME_START - self.score // 50)
            return

        nearest = min(
            active_chairs,
            key=lambda c: min(
                abs(c.angle - self.player_angle),
                2.0 * math.pi - abs(c.angle - self.player_angle),
            ),
        )
        cx = CIRCLE_CX + math.cos(nearest.angle) * CIRCLE_R
        cy = CIRCLE_CY + math.sin(nearest.angle) * CIRCLE_R

        is_match = (self.super_timer > 0) or (self.last_color is None) or (nearest.color == self.last_color)

        if is_match:
            if self.last_color is None:
                self.combo = 1
            else:
                self.combo += 1
            multiplier = 3 if self.super_timer > 0 else 1
            gained = 10 * self.combo * multiplier
            self.score += gained
            self.max_combo = max(self.max_combo, self.combo)
            self._spawn_particles(cx, cy, nearest.color)
            if self.combo >= 2:
                self.floating_texts.append(
                    FloatingText(cx, cy - 10, f"x{self.combo}", 40, WHITE)
                )
            self.floating_texts.append(
                FloatingText(cx + 8, cy, f"+{gained}", 30, YELLOW)
            )
            self.last_color = nearest.color
        else:
            self.combo = 0
            self.heat = min(self.heat + HEAT_MISMATCH, HEAT_MAX)
            self.last_color = nearest.color
            self.floating_texts.append(
                FloatingText(cx, cy - 10, "WRONG!", 40, RED)
            )
            self._spawn_particles(cx, cy, nearest.color)

        nearest.active = False

        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            return
        if self.overall_timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        active = [c for c in self.chairs if c.active]
        if active:
            for i, chair in enumerate(active):
                chair.target_angle = 2.0 * math.pi * i / len(active)
        self.phase = Phase.COMPRESS

    def _respawn_all_chairs(self) -> None:
        self.chairs.clear()
        for i in range(NUM_CHAIRS):
            angle = 2.0 * math.pi * i / NUM_CHAIRS
            color = self._rng.choice(COLOR_VALS)
            self.chairs.append(Chair(angle=angle, target_angle=angle, color=color))

    def _spawn_chair(self) -> None:
        occupied = [c.target_angle for c in self.chairs if c.active]
        all_slots = [2.0 * math.pi * i / NUM_CHAIRS for i in range(NUM_CHAIRS)]
        free_slots = [
            s
            for s in all_slots
            if not any(abs(s - o) < 0.01 for o in occupied)
        ]
        if free_slots:
            angle = self._rng.choice(free_slots)
            color = self._rng.choice(COLOR_VALS)
            self.chairs.append(Chair(angle=angle, target_angle=angle, color=color))

    def _spawn_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(8):
            vx = self._rng.uniform(-2.0, 2.0)
            vy = self._rng.uniform(-2.0, 2.0)
            self.particles.append(Particle(x, y, vx, vy, 15 + self._rng.randrange(10), color))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
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
        elif self.phase == Phase.GAME_OVER:
            self._draw_gameplay()
            self._draw_game_over_overlay()
        else:
            self._draw_gameplay()

    def _draw_title(self) -> None:
        title = "CHAIR SURGE"
        tw = len(title) * 8
        pyxel.text(SCREEN_W // 2 - tw // 2, 70, title, WHITE)

        instructions = [
            "Arrow keys to move around the circle",
            "Match same-color chairs for COMBO!",
            "Wrong color = HEAT, HEAT=100 = KO",
            "COMBO x4 = SUPER SIT (3x score!)",
            "",
            "Press SPACE to Start",
        ]
        for i, line in enumerate(instructions):
            lw = len(line) * 4
            pyxel.text(SCREEN_W // 2 - lw // 2, 110 + i * 14, line, GRAY)

    def _draw_gameplay(self) -> None:
        self._draw_circle()

        for i, chair in enumerate(self.chairs):
            if not chair.active:
                continue
            cx = CIRCLE_CX + math.cos(chair.angle) * CIRCLE_R
            cy = CIRCLE_CY + math.sin(chair.angle) * CIRCLE_R
            w = 12
            h = 12
            pyxel.rect(int(cx) - w // 2, int(cy) - h // 2, w, h, chair.color)
            pyxel.rectb(int(cx) - w // 2, int(cy) - h // 2, w, h, WHITE)

        px = CIRCLE_CX + math.cos(self.player_angle) * CIRCLE_R
        py = CIRCLE_CY + math.sin(self.player_angle) * CIRCLE_R

        if self.phase == Phase.SIT_ANIM and (self.sit_flash // 4) % 2 == 0:
            pyxel.circ(int(px), int(py), 8, YELLOW)
            pyxel.circb(int(px), int(py), 10, WHITE)
        else:
            tri_angle = self.player_angle
            x1 = px + math.cos(tri_angle) * 7
            y1 = py + math.sin(tri_angle) * 7
            x2 = px + math.cos(tri_angle + 2.5) * 5
            y2 = py + math.sin(tri_angle + 2.5) * 5
            x3 = px + math.cos(tri_angle - 2.5) * 5
            y3 = py + math.sin(tri_angle - 2.5) * 5
            pyxel.tri(int(x1), int(y1), int(x2), int(y2), int(x3), int(y3), WHITE)

        chair_time = max(CHAIR_TIME_MIN, CHAIR_TIME_START - self.score // 50)
        bar_w = 100
        bar_x = 10
        bar_y = 8
        frac = self.timer / chair_time
        bar_fill = int(bar_w * frac)
        color = GREEN if frac > 0.5 else (YELLOW if frac > 0.25 else RED)
        pyxel.rect(bar_x, bar_y, bar_w, 6, GRAY)
        pyxel.rect(bar_x, bar_y, bar_fill, 6, color)
        pyxel.text(bar_x + bar_w + 4, bar_y, "TIME", GRAY)

        overall_frac = self.overall_timer / GAME_DURATION
        overall_fill = int(bar_w * overall_frac)
        overall_y = bar_y + 8
        overall_color = GREEN if overall_frac > 0.5 else (YELLOW if overall_frac > 0.25 else RED)
        pyxel.rect(bar_x, overall_y, bar_w, 6, GRAY)
        pyxel.rect(bar_x, overall_y, overall_fill, 6, overall_color)
        pyxel.text(bar_x + bar_w + 4, overall_y, "TOTAL", GRAY)

        heat_bar_h = 80
        heat_bar_x = SCREEN_W - 16
        heat_bar_y = 40
        heat_frac = self.heat / HEAT_MAX
        heat_fill = int(heat_bar_h * heat_frac)
        pyxel.rect(heat_bar_x, heat_bar_y, 8, heat_bar_h, GRAY)
        heat_color = PINK if heat_frac < 0.5 else (ORANGE if heat_frac < 0.75 else RED)
        pyxel.rect(
            heat_bar_x, heat_bar_y + heat_bar_h - heat_fill, 8, heat_fill, heat_color
        )
        pyxel.text(SCREEN_W - 20, heat_bar_y + heat_bar_h + 4, "HEAT", GRAY)

        pyxel.text(10, SCREEN_H - 28, f"SCORE:{self.score}", WHITE)
        pyxel.text(10, SCREEN_H - 18, f"COMBO:{self.combo}", YELLOW)

        if self.super_timer > 0:
            rainbow_idx = (pyxel.frame_count // 4) % len(RAINBOW_COLORS)
            rc = RAINBOW_COLORS[rainbow_idx]
            pyxel.text(SCREEN_W // 2 - 20, SCREEN_H - 20, "SUPER!", rc)
            border_c = RAINBOW_COLORS[rainbow_idx]
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, border_c)

        for p in self.particles:
            if p.life > 0:
                alpha_color = p.color if p.life > 7 else GRAY
                sx = int(p.x)
                sy = int(p.y)
                sz = max(2, p.life // 3)
                pyxel.rect(sx, sy, sz, sz, alpha_color)

        for ft in self.floating_texts:
            if ft.life > 0:
                pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

    def _draw_circle(self) -> None:
        pyxel.circb(CIRCLE_CX, CIRCLE_CY, CIRCLE_R, WHITE)
        for i in range(NUM_CHAIRS):
            a = 2.0 * math.pi * i / NUM_CHAIRS
            mx = CIRCLE_CX + math.cos(a) * (CIRCLE_R + 6)
            my = CIRCLE_CY + math.sin(a) * (CIRCLE_R + 6)
            pyxel.pset(int(mx), int(my), GRAY)

    def _draw_game_over_overlay(self) -> None:
        pyxel.rect(50, 70, SCREEN_W - 100, SCREEN_H - 140, BLACK)
        pyxel.rectb(50, 70, SCREEN_W - 100, SCREEN_H - 140, WHITE)
        go_text = "GAME OVER"
        pyxel.text(SCREEN_W // 2 - len(go_text) * 4, 90, go_text, RED)
        score_text = f"SCORE: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_text) * 4, 110, score_text, WHITE)
        combo_text = f"MAX COMBO: {self.max_combo}"
        pyxel.text(SCREEN_W // 2 - len(combo_text) * 4, 130, combo_text, YELLOW)
        heat_text = "HEAT OVERLOAD!" if self.heat >= HEAT_MAX else "TIME UP!"
        pyxel.text(SCREEN_W // 2 - len(heat_text) * 4, 150, heat_text, GRAY)
        retry_text = "Press SPACE to Retry"
        pyxel.text(SCREEN_W // 2 - len(retry_text) * 4, 180, retry_text, WHITE)


if __name__ == "__main__":
    Game()
