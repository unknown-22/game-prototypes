from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum

import pyxel

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

COLOR_VALS: tuple[int, ...] = (RED, LIME, DARK_BLUE, YELLOW)
RAINBOW: tuple[int, ...] = (RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK)


class Phase(Enum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


@dataclass
class Head:
    color: int
    tier: int


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
    MAX_HEADS = 6
    HEADS_START = 5
    MAX_TIER = 3
    COMBO_SUPER = 4
    SUPER_DURATION = 300
    GAME_LENGTH = 3600
    HEAT_MAX = 100

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="HYDRA CHAIN", display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------ setup

    def reset(self) -> None:
        self._rng = random.Random(42)
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.frame = 0
        self.timer = self.GAME_LENGTH
        self.heads = [
            Head(color=self._rng.randrange(4), tier=1) for _ in range(self.HEADS_START)
        ]
        self.blade_color = 0
        self.blade_timer = 0
        self.super_timer = 0
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self.respawn_queue: list[int] = []
        self.shake = 0
        self.flash = 0
        if not hasattr(self, "best_score"):
            self.best_score = 0
        self.game_over_reason = ""

    # ------------------------------------------------------- testable logic

    def _cycle_interval(self) -> int:
        return max(12, 20 - self.frame // 120)

    def _respawn_delay(self) -> int:
        return max(25, 60 - (35 * self.frame) // 3600)

    def _heat_decay(self) -> float:
        return -0.02

    def _head_pos(self, i: int) -> tuple[int, int]:
        return (36 + i * 54, 70 + 12 * (i - 2) ** 2)

    def _head_radius(self, tier: int) -> int:
        return 8 + (tier - 1) * 3

    def _head_at(self, x: float, y: float) -> int | None:
        for i, head in enumerate(self.heads):
            hx, hy = self._head_pos(i)
            r = self._head_radius(head.tier)
            if (x - hx) ** 2 + (y - hy) ** 2 <= r * r:
                return i
        return None

    def _chain_run(self, i: int, color: int) -> list[int]:
        run: list[int] = []
        j = i
        while j >= 0 and self.heads[j].color == color:
            run.append(j)
            j -= 1
        run.reverse()
        j = i + 1
        while j < len(self.heads) and self.heads[j].color == color:
            run.append(j)
            j += 1
        return run

    def _do_cut_score(self, i: int) -> int:
        head = self.heads[i]
        mult = 3 if self.super_timer > 0 else 1
        return 10 * self.combo * head.tier * mult

    def _cut_head(self, i: int) -> None:
        head = self.heads[i]
        matched = self.super_timer > 0 or head.color == self.blade_color
        if not matched:
            hx, hy = self._head_pos(i)
            self._update_heat(15)
            self.combo = 0
            self._spawn_mismatch_particles(hx, hy)
            self.floats.append(FloatingText(hx, hy - 8, "WRONG!", 30, GRAY))
            self.shake = 6
            return
        run = self._chain_run(i, head.color)
        for idx in run:
            hx, hy = self._head_pos(idx)
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            gain = self._do_cut_score(idx)
            self.score += gain
            self.floats.append(FloatingText(hx, hy - 8, f"+{gain}", 30, WHITE))
            if self.super_timer > 0:
                self._spawn_super_cut_particles(hx, hy)
            else:
                count = 8 if idx == i else 6
                self._spawn_cut_particles(hx, hy, COLOR_VALS[self.blade_color], count)
        for idx in sorted(run, reverse=True):
            del self.heads[idx]
            self.respawn_queue.append(self._respawn_delay())
        if self.combo >= self.COMBO_SUPER and self.super_timer == 0:
            self.super_timer = self.SUPER_DURATION
            self.floats.append(FloatingText(SCREEN_W / 2, SCREEN_H / 2, "SUPER BLADE!", 60, WHITE))

    def _strike_head(self, i: int) -> None:
        head = self.heads[i]
        hx, hy = self._head_pos(i)
        if head.tier < self.MAX_TIER:
            head.tier += 1
            self._spawn_strike_particles(hx, hy, COLOR_VALS[head.color])
            self.floats.append(
                FloatingText(hx, hy - 8, f"TIER {head.tier}", 30, COLOR_VALS[head.color])
            )
            return
        head.tier = 1
        self._update_heat(20)
        self._spawn_head()
        self._spawn_enrage_particles(hx, hy)
        self.shake = 8
        self.flash = 10
        self.floats.append(FloatingText(hx, hy - 8, "ENRAGE!", 40, ORANGE))

    def _spawn_head(self) -> None:
        if len(self.heads) < self.MAX_HEADS:
            self.heads.append(Head(color=self._rng.randrange(4), tier=1))

    def _update_heat(self, delta: float) -> None:
        self.heat = max(0.0, min(float(self.HEAT_MAX), self.heat + delta))
        if self.heat >= self.HEAT_MAX:
            self._trigger_game_over("HYDRA RAMPAGE")

    def _update_timer(self) -> None:
        self.frame += 1
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self._trigger_game_over("TIME UP")

    def _update_blade(self) -> None:
        self.blade_timer += 1
        if self.blade_timer >= self._cycle_interval():
            self.blade_timer = 0
            self.blade_color = (self.blade_color + 1) % 4

    def _update_heads(self) -> None:
        remaining: list[int] = []
        for delay in self.respawn_queue:
            delay -= 1
            if delay <= 0:
                self._spawn_head()
            else:
                remaining.append(delay)
        self.respawn_queue = remaining

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floats(self) -> None:
        for f in self.floats:
            f.life -= 1
            f.y -= 0.5
        self.floats = [f for f in self.floats if f.life > 0]

    def _trigger_game_over(self, reason: str) -> None:
        self.phase = Phase.GAME_OVER
        self.game_over_reason = reason
        self.best_score = max(self.best_score, self.score)

    # ------------------------------------------------------------ particles

    def _spawn_cut_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x,
                    y,
                    self._rng.uniform(-2.0, 2.0),
                    self._rng.uniform(-3.0, -1.0),
                    self._rng.randint(20, 35),
                    color,
                )
            )

    def _spawn_super_cut_particles(self, x: float, y: float) -> None:
        for k in range(20):
            color = RAINBOW[k % len(RAINBOW)]
            ang = self._rng.uniform(0.0, math.tau)
            spd = self._rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x,
                    y,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    self._rng.randint(30, 60),
                    color,
                )
            )

    def _spawn_mismatch_particles(self, x: float, y: float) -> None:
        for _ in range(4):
            self.particles.append(
                Particle(
                    x,
                    y,
                    self._rng.uniform(-1.0, 1.0),
                    self._rng.uniform(-1.0, 1.0),
                    self._rng.randint(10, 20),
                    GRAY,
                )
            )

    def _spawn_enrage_particles(self, x: float, y: float) -> None:
        for _ in range(12):
            ang = self._rng.uniform(0.0, math.tau)
            spd = self._rng.uniform(1.0, 4.0)
            self.particles.append(
                Particle(
                    x,
                    y,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    self._rng.randint(20, 40),
                    ORANGE,
                )
            )

    def _spawn_strike_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(4):
            self.particles.append(
                Particle(
                    x,
                    y,
                    self._rng.uniform(-1.0, 1.0),
                    self._rng.uniform(-2.0, -0.5),
                    self._rng.randint(10, 20),
                    color,
                )
            )

    # ------------------------------------------------------------- update

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        else:
            self._update_gameover()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_gameover(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()

    def _update_playing(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            idx = self._head_at(pyxel.mouse_x, pyxel.mouse_y)
            if idx is not None:
                self._cut_head(idx)
        if pyxel.btnp(pyxel.KEY_SPACE):
            idx = self._head_at(pyxel.mouse_x, pyxel.mouse_y)
            if idx is not None:
                self._strike_head(idx)
        for k in (pyxel.KEY_1, pyxel.KEY_2, pyxel.KEY_3, pyxel.KEY_4):
            if pyxel.btnp(k):
                self.blade_color = k - pyxel.KEY_1
        self._update_timer()
        self._update_blade()
        self._update_super()
        if self.super_timer == 0:
            self._update_heat(self._heat_decay())
        self._update_heads()
        self._update_particles()
        self._update_floats()
        if self.shake > 0:
            self.shake -= 1
        if self.flash > 0:
            self.flash -= 1
        self.best_score = max(self.best_score, self.score)

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
        pyxel.text(108, 40, "HYDRA CHAIN", WHITE)
        pyxel.text(120, 52, "many heads, one blade", YELLOW)
        pyxel.text(56, 80, "CLICK  = CUT matching head", WHITE)
        pyxel.text(56, 92, "SPACE  = STRIKE (grow head)", WHITE)
        pyxel.text(56, 104, "COMBO x4 = SUPER BLADE", LIME)
        pyxel.text(56, 116, "overfeed = ENRAGE = +HEAT", ORANGE)
        pyxel.text(56, 128, "HEAT 100 = HYDRA RAMPAGE", RED)
        pyxel.text(76, 152, "1-4 = set blade color", CYAN)
        for i, c in enumerate(COLOR_VALS):
            pyxel.circ(92 + i * 36, 184, 8, c)
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(104, 208, "PRESS ENTER", WHITE)

    def _draw_playing(self) -> None:
        ox = oy = 0
        if self.shake > 0:
            ox = self._rng.randint(-3, 3)
            oy = self._rng.randint(-3, 3)
        pyxel.cls(NAVY)
        self._draw_heads(ox, oy)
        self._draw_blade(ox, oy)
        self._draw_hud(ox, oy)
        self._draw_heat_bar(ox, oy)
        self._draw_timer_bar(ox, oy)
        for p in self.particles:
            pyxel.rect(int(p.x + ox), int(p.y + oy), 2, 2, p.color)
        for f in self.floats:
            pyxel.text(int(f.x + ox), int(f.y + oy), f.text, f.color)
        if self.super_timer > 0:
            c = RAINBOW[(pyxel.frame_count // 4) % len(RAINBOW)]
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, c)

    def _draw_heads(self, ox: int, oy: int) -> None:
        for i, head in enumerate(self.heads):
            x, y = self._head_pos(i)
            r = self._head_radius(head.tier)
            pyxel.circ(x + ox, y + oy, r, COLOR_VALS[head.color])
            pyxel.circb(x + ox, y + oy, r, WHITE)
            if self.flash > 0:
                pyxel.circb(x + ox, y + oy, r + 3, WHITE)
            for t in range(head.tier):
                px = x + ox + (t - (head.tier - 1) / 2) * 6
                pyxel.rect(int(px) - 1, y + oy - r - 7, 3, 3, WHITE)

    def _draw_blade(self, ox: int, oy: int) -> None:
        if self.super_timer > 0:
            color = RAINBOW[(self.frame // 4) % len(RAINBOW)]
        else:
            color = COLOR_VALS[self.blade_color]
        pyxel.rect(8 + ox, 214 + oy, 72, 18, color)
        pyxel.rectb(8 + ox, 214 + oy, 72, 18, WHITE)
        pyxel.text(16 + ox, 220 + oy, "CUT", WHITE)

    def _draw_hud(self, ox: int, oy: int) -> None:
        pyxel.text(8 + ox, 8 + oy, f"SCORE {self.score}", WHITE)
        pyxel.text(8 + ox, 20 + oy, f"COMBO x{self.combo}", YELLOW)
        if self.super_timer > 0:
            pyxel.text(8 + ox, 32 + oy, "SUPER!", LIME)

    def _draw_heat_bar(self, ox: int, oy: int) -> None:
        bx = 308 + ox
        by = 8 + oy
        bh = 120
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
        tw = int(200 * max(0, self.timer) / self.GAME_LENGTH)
        pyxel.rectb(60 + ox, 8 + oy, 202, 6, WHITE)
        pyxel.rect(61 + ox, 9 + oy, tw, 4, CYAN)

    def _draw_game_over(self) -> None:
        pyxel.cls(NAVY)
        pyxel.text(120, 60, "GAME OVER", RED)
        pyxel.text(96, 80, self.game_over_reason, WHITE)
        pyxel.text(120, 100, f"SCORE {self.score}", WHITE)
        pyxel.text(120, 112, f"BEST {self.best_score}", YELLOW)
        pyxel.text(104, 140, "PRESS ENTER to retry", CYAN)


if __name__ == "__main__":
    Game()
