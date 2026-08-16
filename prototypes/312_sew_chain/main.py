from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

SCREEN_W = 320
SCREEN_H = 240

NUM_PATCHES = 8
PATCH_SIZE = 24
PATCH_Y = 110
PATCH_X0 = 16
PATCH_STEP = 36

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

FABRIC_COLORS: tuple[int, ...] = (RED, LIME, DARK_BLUE, YELLOW)
RAINBOW: tuple[int, ...] = (RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK)


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    RETHREADING = auto()
    GAME_OVER = auto()


@dataclass
class Patch:
    color: int
    x: int
    y: int
    respawn_timer: int


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
    x: int
    y: int
    text: str
    life: int
    color: int


class Game:
    SCREEN_W = SCREEN_W
    SCREEN_H = SCREEN_H
    HEAT_MAX = 100
    THREAD_MAX = 12
    SUPER_DURATION = 300
    RETHREAD_DURATION = 120
    GAME_TIME = 3600
    MATCH_PARTICLES = 8
    SUPER_PARTICLES = 20
    MISMATCH_PARTICLES = 4
    RETHREAD_PARTICLES = 12

    def __init__(self) -> None:
        pyxel.init(self.SCREEN_W, self.SCREEN_H, title="SEW CHAIN")
        self.reset()

    def run(self) -> None:
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------ setup

    def reset(self) -> None:
        self._rng = random.Random(42)
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.thread = self.THREAD_MAX
        self.needle_color = 0
        self.needle_timer = 0
        self.timer = self.GAME_TIME
        self.elapsed = 0
        self.super_timer = 0
        self.rethread_timer = 0
        self.patches = [
            Patch(
                color=self._rng.randrange(4),
                x=PATCH_X0 + i * PATCH_STEP,
                y=PATCH_Y,
                respawn_timer=0,
            )
            for i in range(NUM_PATCHES)
        ]
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self.shake = 0
        self.best_score = 0
        self.frame = 0
        self.phase = Phase.TITLE

    # ------------------------------------------------------- testable logic

    def _cycle_interval(self) -> int:
        return max(12, 20 - self.elapsed // 120)

    def _respawn_delay(self) -> int:
        return max(25, 60 - self.elapsed // 100)

    def _heat_decay(self) -> float:
        return -0.02

    def _sew(self, index: int) -> tuple[bool, str]:
        if self.thread <= 0:
            return (False, "NO THREAD")
        patch = self.patches[index]
        if patch.respawn_timer > 0:
            return (False, "")
        matched = (patch.color == self.needle_color) or (self.super_timer > 0)
        cx = patch.x + PATCH_SIZE // 2
        cy = patch.y + PATCH_SIZE // 2
        if matched:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            mult = 3 if self.super_timer > 0 else 1
            gain = 10 * self.combo * mult
            self.score += gain
            if self.super_timer == 0:
                self.thread -= 1
            patch.respawn_timer = self._respawn_delay()
            self._spawn_match_particles(cx, cy, FABRIC_COLORS[patch.color])
            self.floats.append(FloatingText(cx, cy, f"+{gain}", 30, WHITE))
            if self.combo >= 4 and self.super_timer == 0:
                self.super_timer = self.SUPER_DURATION
                self._spawn_super_particles()
                self.floats.append(
                    FloatingText(self.SCREEN_W // 2, self.SCREEN_H // 2 - 10, "SUPER STITCH!", 60, WHITE)
                )
            return (True, f"+{gain}")
        self.heat += 15
        self.combo = 0
        self.thread -= 1
        self._spawn_mismatch_particles(cx, cy)
        self.floats.append(FloatingText(cx, cy, "WRONG!", 30, RED))
        self.shake = 8
        return (False, "WRONG!")

    def _rethread(self) -> bool:
        if self.phase == Phase.PLAYING and self.thread < self.THREAD_MAX:
            self.phase = Phase.RETHREADING
            self.rethread_timer = self.RETHREAD_DURATION
            return True
        return False

    def _finish_rethread(self) -> None:
        self.thread = self.THREAD_MAX
        self.combo = 0
        self.heat += 5
        self.phase = Phase.PLAYING
        self._spawn_rethread_particles()
        self.floats.append(
            FloatingText(self.SCREEN_W // 2, PATCH_Y - 20, "RETHREADED", 40, CYAN)
        )

    def _update_heat(self) -> None:
        if self.heat >= self.HEAT_MAX:
            self.phase = Phase.GAME_OVER
            self.best_score = max(self.best_score, self.score)
            return
        if self.super_timer == 0 and self.phase != Phase.RETHREADING:
            self.heat = max(0.0, self.heat + self._heat_decay())

    def _update_needle(self) -> None:
        if self.phase == Phase.RETHREADING:
            return
        self.needle_timer += 1
        if self.needle_timer >= self._cycle_interval():
            self.needle_timer = 0
            self.needle_color = (self.needle_color + 1) % 4

    def _update_patches(self) -> None:
        for patch in self.patches:
            if patch.respawn_timer > 0:
                patch.respawn_timer -= 1
                if patch.respawn_timer <= 0:
                    patch.respawn_timer = 0
                    patch.color = self._rng.randrange(4)

    def _update_floats(self) -> None:
        for f in self.floats:
            f.life -= 1
        self.floats = [f for f in self.floats if f.life > 0]

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ------------------------------------------------------------ particles

    def _spawn_match_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(self.MATCH_PARTICLES):
            ang = self._rng.uniform(0.0, math.tau)
            spd = self._rng.uniform(0.5, 1.5)
            self.particles.append(
                Particle(x, y, math.cos(ang) * spd, math.sin(ang) * spd, self._rng.randint(15, 30), color)
            )

    def _spawn_mismatch_particles(self, x: float, y: float) -> None:
        for _ in range(self.MISMATCH_PARTICLES):
            ang = self._rng.uniform(0.0, math.tau)
            spd = self._rng.uniform(0.5, 1.5)
            self.particles.append(
                Particle(x, y, math.cos(ang) * spd, math.sin(ang) * spd, self._rng.randint(15, 30), RED)
            )

    def _spawn_super_particles(self) -> None:
        for i in range(self.SUPER_PARTICLES):
            color = RAINBOW[i % len(RAINBOW)]
            ang = self._rng.uniform(0.0, math.tau)
            spd = self._rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    self.SCREEN_W / 2,
                    self.SCREEN_H / 2,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    self._rng.randint(30, 60),
                    color,
                )
            )

    def _spawn_rethread_particles(self) -> None:
        for _ in range(self.RETHREAD_PARTICLES):
            ang = self._rng.uniform(0.0, math.tau)
            spd = self._rng.uniform(0.5, 1.5)
            self.particles.append(
                Particle(
                    self.SCREEN_W / 2,
                    PATCH_Y - 20,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    self._rng.randint(20, 40),
                    CYAN,
                )
            )

    # ------------------------------------------------------------- update

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.RETHREADING:
            self._update_rethreading()
        else:
            self._update_gameover()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_gameover(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self.frame += 1
        self.elapsed += 1
        self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            for i, patch in enumerate(self.patches):
                if patch.respawn_timer > 0:
                    continue
                if (
                    patch.x <= pyxel.mouse_x <= patch.x + PATCH_SIZE
                    and patch.y <= pyxel.mouse_y <= patch.y + PATCH_SIZE
                ):
                    self._sew(i)
                    break
        if pyxel.btnp(pyxel.KEY_R):
            self._rethread()
        if self.super_timer > 0:
            self.super_timer -= 1
        self._update_heat()
        self._update_needle()
        self._update_patches()
        self._update_floats()
        self._update_particles()
        if self.shake > 0:
            self.shake -= 1
        self.best_score = max(self.best_score, self.score)

    def _update_rethreading(self) -> None:
        self.rethread_timer -= 1
        if self.rethread_timer <= 0:
            self._finish_rethread()

    # --------------------------------------------------------------- draw

    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        else:
            self._draw_playing()

    def _draw_title(self) -> None:
        pyxel.cls(NAVY)
        pyxel.text(112, 50, "SEW CHAIN", WHITE)
        pyxel.text(132, 66, "Tailor", YELLOW)
        pyxel.text(64, 100, "CLICK matching patch to sew", WHITE)
        pyxel.text(88, 112, "R = RETHREAD (when low)", CYAN)
        pyxel.text(64, 124, "COMBO>=4 = SUPER STITCH", LIME)
        pyxel.text(104, 150, "SPACE to start", PINK)
        for i, c in enumerate(FABRIC_COLORS):
            pyxel.circ(80 + i * 40, 180, 8, c)

    def _draw_playing(self) -> None:
        ox = oy = 0
        if self.shake > 0:
            ox = self._rng.randint(-3, 3)
            oy = self._rng.randint(-3, 3)
        pyxel.cls(NAVY)
        self._draw_needle(ox, oy)
        for patch in self.patches:
            if patch.respawn_timer > 0:
                continue
            pyxel.rect(patch.x + ox, patch.y + oy, PATCH_SIZE, PATCH_SIZE, FABRIC_COLORS[patch.color])
            pyxel.rectb(patch.x + ox, patch.y + oy, PATCH_SIZE, PATCH_SIZE, WHITE)
        self._draw_thread_bar(ox, oy)
        self._draw_heat_bar(ox, oy)
        self._draw_timer_bar(ox, oy)
        self._draw_hud(ox, oy)
        for p in self.particles:
            pyxel.rect(int(p.x + ox), int(p.y + oy), 2, 2, p.color)
        for f in self.floats:
            pyxel.text(f.x + ox, f.y + oy, f.text, f.color)
        if self.super_timer > 0:
            self._draw_super_border()
        if self.phase == Phase.RETHREADING:
            self._draw_rethread_overlay()

    def _draw_needle(self, ox: int, oy: int) -> None:
        x = 160 + ox
        pyxel.line(x, 8 + oy, x, 52 + oy, WHITE)
        pyxel.rect(x - 1, 52 + oy, 2, 8, GRAY)
        if self.super_timer > 0:
            color = RAINBOW[(self.frame // 4) % len(RAINBOW)]
        else:
            color = FABRIC_COLORS[self.needle_color]
        pyxel.circ(x, 60 + oy, 6, color)

    def _draw_thread_bar(self, ox: int, oy: int) -> None:
        pyxel.text(8 + ox, 202 + oy, "THREAD", WHITE)
        for i in range(self.THREAD_MAX):
            x = 8 + i * 10 + ox
            color = WHITE if i < self.thread else GRAY
            pyxel.rect(x, 216 + oy, 8, 8, color)

    def _draw_heat_bar(self, ox: int, oy: int) -> None:
        bx = 312 + ox
        by = 64 + oy
        bh = 150
        pyxel.rectb(bx, by, 6, bh, WHITE)
        h = int(bh * min(1.0, self.heat / self.HEAT_MAX))
        if self.heat < 33:
            color = GREEN
        elif self.heat < 66:
            color = YELLOW
        else:
            color = RED
        pyxel.rect(bx + 1, by + bh - h, 4, h, color)

    def _draw_timer_bar(self, ox: int, oy: int) -> None:
        tw = int(100 * max(0, self.timer) / self.GAME_TIME)
        pyxel.rectb(8 + ox, 20 + oy, 102, 6, WHITE)
        pyxel.rect(9 + ox, 21 + oy, tw, 4, CYAN)

    def _draw_hud(self, ox: int, oy: int) -> None:
        pyxel.text(8 + ox, 8 + oy, f"SCORE {self.score}", WHITE)
        pyxel.text(8 + ox, 230 + oy, f"COMBO x{self.combo}", YELLOW)
        if self.super_timer > 0:
            pyxel.text(140 + ox, 230 + oy, "SUPER", LIME)

    def _draw_super_border(self) -> None:
        c = RAINBOW[(pyxel.frame_count // 4) % len(RAINBOW)]
        pyxel.rectb(0, 0, self.SCREEN_W, self.SCREEN_H, c)

    def _draw_rethread_overlay(self) -> None:
        pyxel.rect(60, 96, 200, 40, BLACK)
        pyxel.rectb(60, 96, 200, 40, WHITE)
        pyxel.text(120, 108, "RETHREADING...", WHITE)
        pw = int(180 * (1.0 - self.rethread_timer / self.RETHREAD_DURATION))
        pyxel.rect(70, 124, pw, 6, CYAN)

    def _draw_game_over(self) -> None:
        pyxel.cls(NAVY)
        pyxel.text(120, 70, "GAME OVER", RED)
        reason = "NEEDLE SNAPPED" if self.heat >= self.HEAT_MAX else "TIME UP"
        pyxel.text((self.SCREEN_W - len(reason) * 4) // 2, 90, reason, WHITE)
        pyxel.text(120, 110, f"SCORE {self.score}", WHITE)
        pyxel.text(116, 122, f"BEST {self.best_score}", YELLOW)
        pyxel.text(112, 150, "SPACE to retry", CYAN)


if __name__ == "__main__":
    Game().run()
