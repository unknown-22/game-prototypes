"""WRECK CHAIN — Side-view wrecking ball demolition game.

Pendulum swings from top-center. Hold mouse to charge power, release to swing.
Chain same-color block destruction for COMBO multiplier. COMBO >= 4 triggers SUPER BALL.
Wrong-color hits reset COMBO and add HEAT. HEAT >= 100 = game over.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import IntEnum

import pyxel

# ── Config ────────────────────────────────────────────────────────────────────

SCREEN_W = 320
SCREEN_H = 240
CELL = 20
COLS = 10
ROWS = 8
GRID_X = 40
GRID_Y = 60
GROUND_Y = 220

PIVOT_X = 160.0
PIVOT_Y = 20.0
ROPE_MIN = 80.0
ROPE_MAX = 160.0
ROPE_BASE = 120.0
GRAVITY = 9.8
BALL_RADIUS = 8
SUPER_BALL_RADIUS = 14
SUPER_DURATION = 300
COMBO_THRESHOLD = 4
HEAT_MAX = 100.0
HEAT_DECAY = 0.03
HEAT_HIT_WRONG = 15
TIMER_MAX = 3600  # 60s * 60fps
PENDULUM_DAMPING = 0.999

BLOCK_COLORS: list[int] = [8, 3, 5, 10]  # RED, GREEN, DARK_BLUE, YELLOW

# pyxel color palette
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


class Phase(IntEnum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


@dataclass
class Block:
    col: int
    row: int
    color: int
    destroyed: bool = False


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
    vy: float = -1.5


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Wreck Chain", display_scale=2)
        self.reset()
        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.timer: int = TIMER_MAX
        self.super_timer: int = 0
        self._is_super: bool = False
        self.pendulum_angle: float = 0.0
        self.pendulum_angular_vel: float = 0.0
        self.charge: float = 0.0
        self.charging: bool = False
        self._swing_power: float = 0.0
        self._swinging: bool = False
        self._ball_x: float = PIVOT_X
        self._ball_y: float = PIVOT_Y + ROPE_BASE
        self._rope_len: float = ROPE_BASE
        self.last_hit_color: int = -1
        self._super_color_cycle: int = 0
        self.blocks: list[Block] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shake_frames: int = 0
        self._rng = random.Random()
        self._init_grid()

    # ── Grid ───────────────────────────────────────────────────────────────

    def _init_grid(self) -> None:
        self.blocks.clear()
        for row in range(ROWS):
            for col in range(COLS):
                color = self._rng.choice(BLOCK_COLORS)
                self.blocks.append(Block(col=col, row=row, color=color))

    def _any_blocks_alive(self) -> bool:
        return any(not b.destroyed for b in self.blocks)

    # ── Pendulum Physics ───────────────────────────────────────────────────

    def _update_pendulum(self) -> None:
        self.pendulum_angular_vel += GRAVITY * math.sin(self.pendulum_angle) * 0.005
        self.pendulum_angular_vel *= PENDULUM_DAMPING
        self.pendulum_angle += self.pendulum_angular_vel

    def _update_ball_position(self) -> None:
        self._ball_x = PIVOT_X + self._rope_len * math.sin(self.pendulum_angle)
        self._ball_y = PIVOT_Y + self._rope_len * math.cos(self.pendulum_angle)

    def _get_rope_len(self) -> float:
        if self.charging:
            return ROPE_BASE - (self.charge / 100.0) * (ROPE_BASE - ROPE_MIN)
        return ROPE_BASE

    # ── Block Collision ────────────────────────────────────────────────────

    def _block_rect(self, block: Block) -> tuple[float, float, float, float]:
        x = GRID_X + block.col * CELL
        y = GRID_Y + block.row * CELL
        return (x, y, x + CELL, y + CELL)

    def _check_block_collisions(self) -> list[tuple[int, int]]:
        r = self._get_ball_radius()
        bx = self._ball_x
        by = self._ball_y
        hits: list[tuple[int, int]] = []
        for block in self.blocks:
            if block.destroyed:
                continue
            rx1, ry1, rx2, ry2 = self._block_rect(block)
            closest_x = max(rx1, min(bx, rx2))
            closest_y = max(ry1, min(by, ry2))
            dist_x = bx - closest_x
            dist_y = by - closest_y
            if (dist_x * dist_x + dist_y * dist_y) < (r * r):
                hits.append((block.col, block.row))
        return hits

    def _destroy_block(self, col: int, row: int) -> bool:
        for block in self.blocks:
            if block.col == col and block.row == row and not block.destroyed:
                block.destroyed = True
                block_color = block.color
                if self._is_super:
                    self._on_same_color_hit(block_color)
                    return True
                if self.last_hit_color == -1 or block_color == self.last_hit_color:
                    self.last_hit_color = block_color
                    self._on_same_color_hit(block_color)
                    return True
                else:
                    self._on_wrong_color_hit()
                    self.last_hit_color = -1
                    return False
        return False

    def _on_same_color_hit(self, block_color: int) -> None:
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        multiplier = 1.0 + self.combo * 0.5
        if self._is_super:
            multiplier *= 3
        points = int(10 * multiplier)
        self.score += points

        self._spawn_particles(self._ball_x, self._ball_y, block_color, 8)
        self._spawn_floating_text(self._ball_x, self._ball_y - 8, f"+{points}", block_color)

        if self.combo >= COMBO_THRESHOLD and not self._is_super:
            self._activate_super()

    def _on_wrong_color_hit(self) -> None:
        self.heat = min(HEAT_MAX, self.heat + HEAT_HIT_WRONG)
        self.combo = 0
        self._spawn_floating_text(self._ball_x, self._ball_y - 8, "HEAT+15", ORANGE)

    # ── Super Ball ─────────────────────────────────────────────────────────

    def _activate_super(self) -> None:
        self._is_super = True
        self.super_timer = SUPER_DURATION
        self.shake_frames = 10
        self._spawn_particles(self._ball_x, self._ball_y, YELLOW, 20)
        self._spawn_floating_text(self._ball_x, self._ball_y - 12, "SUPER!", LIME)

    def _deactivate_super(self) -> None:
        self._is_super = False
        self.super_timer = 0

    def _get_ball_radius(self) -> int:
        return SUPER_BALL_RADIUS if self._is_super else BALL_RADIUS

    def _get_ball_color(self) -> int:
        if self._is_super:
            idx = (pyxel.frame_count // 5) % len(BLOCK_COLORS)
            return BLOCK_COLORS[idx]
        if self.last_hit_color >= 0:
            return self.last_hit_color
        return WHITE

    # ── Particles ──────────────────────────────────────────────────────────

    def _spawn_particles(self, x: float, y: float, color: int, count: int = 8) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.tau)
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 1.5,
                life=self._rng.randint(15, 30),
                color=color,
            ))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(
            x=x, y=y, text=text, color=color, life=30,
        ))

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.15
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    # ── Timer & Heat ───────────────────────────────────────────────────────

    def _update_timer(self) -> None:
        if self.timer > 0:
            self.timer -= 1

    def _update_heat(self) -> None:
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    # ── Main Update ────────────────────────────────────────────────────────

    def update(self) -> None:
        if self.shake_frames > 0:
            self.shake_frames -= 1

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

        self._update_particles()
        self._update_floating_texts()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        if self.timer <= 0 or self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            return

        self._update_timer()
        self._update_heat()

        if self._is_super:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self._deactivate_super()

        mouse_pressed = pyxel.btn(pyxel.MOUSE_BUTTON_LEFT)

        if mouse_pressed and not self._swinging:
            self.charging = True
            self.charge = min(100.0, self.charge + 1.5)
        elif self.charging and not mouse_pressed:
            self.charging = False
            self._swing_power = self.charge
            self.charge = 0.0
            self._swinging = True
            boost = (self._swing_power / 100.0) * 0.15
            direction = 1.0 if self.pendulum_angular_vel >= 0 else -1.0
            self.pendulum_angular_vel += direction * boost
        else:
            self.charging = False

        self._rope_len = self._get_rope_len()
        self._update_pendulum()
        self._update_ball_position()

        hits = self._check_block_collisions()
        for col, row in hits:
            self._destroy_block(col, row)

        if not self._any_blocks_alive():
            self.score += 500
            self._spawn_floating_text(PIVOT_X, SCREEN_H // 2, "CLEAR +500", YELLOW)
            self._init_grid()
            self.last_hit_color = -1

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.PLAYING

    # ── Draw ───────────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(NAVY)

        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0:
            shake_x = self._rng.randint(-3, 3)
            shake_y = self._rng.randint(-3, 3)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing(shake_x, shake_y)
        elif self.phase == Phase.GAME_OVER:
            self._draw_playing(shake_x, shake_y)
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = "WRECK CHAIN"
        tw = len(title) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, SCREEN_H // 2 - 40, title, YELLOW)
        subtitle = "Click to swing | Destroy blocks!"
        tw2 = len(subtitle) * 4
        pyxel.text(SCREEN_W // 2 - tw2 // 2, SCREEN_H // 2, subtitle, WHITE)
        cta = "SPACE or CLICK to start"
        tw3 = len(cta) * 4
        blink = (pyxel.frame_count // 30) % 2 == 0
        if blink:
            pyxel.text(SCREEN_W // 2 - tw3 // 2, SCREEN_H // 2 + 30, cta, GRAY)

    def _draw_playing(self, shake_x: int, shake_y: int) -> None:
        # Ground
        pyxel.rect(0, GROUND_Y + shake_y, SCREEN_W, SCREEN_H - GROUND_Y, BROWN)

        # Blocks
        for block in self.blocks:
            if block.destroyed:
                continue
            bx = GRID_X + block.col * CELL + shake_x
            by = GRID_Y + block.row * CELL + shake_y
            pyxel.rect(bx + 1, by + 1, CELL - 2, CELL - 2, block.color)
            pyxel.rectb(bx, by, CELL, CELL, WHITE)

        # Rope
        pyxel.line(
            int(PIVOT_X + shake_x), int(PIVOT_Y + shake_y),
            int(self._ball_x + shake_x), int(self._ball_y + shake_y),
            GRAY,
        )

        # Pivot
        pyxel.circ(int(PIVOT_X + shake_x), int(PIVOT_Y + shake_y), 3, WHITE)

        # Ball
        bx = int(self._ball_x + shake_x)
        by = int(self._ball_y + shake_y)
        br = self._get_ball_radius()
        bcolor = self._get_ball_color()
        if self._is_super:
            pyxel.circ(bx, by, br + 2, YELLOW)
            pyxel.circ(bx, by, br, bcolor)
            pyxel.circ(bx, by, br - 3, WHITE)
        else:
            pyxel.circ(bx, by, br, bcolor)
            pyxel.circb(bx, by, br, WHITE)

        # Particles
        for p in self.particles:
            alpha = p.life / 30.0
            c = p.color if alpha > 0.5 else GRAY
            pyxel.pset(int(p.x + shake_x), int(p.y + shake_y), c)

        # Floating texts
        for ft in self.floating_texts:
            alpha = ft.life / 30.0
            c = ft.color if alpha > 0.3 else GRAY
            tw = len(ft.text) * 4
            pyxel.text(
                int(ft.x) - tw // 2 + shake_x,
                int(ft.y) + shake_y,
                ft.text, c,
            )

        self._draw_hud()
        self._draw_charge_bar(shake_x, shake_y)

    def _draw_hud(self) -> None:
        # Score
        pyxel.text(4, 2, f"SCORE:{self.score:06d}", WHITE)
        # Combo
        combo_str = f"COMBO:{self.combo}"
        pyxel.text(4, 10, combo_str, YELLOW if self.combo >= COMBO_THRESHOLD else WHITE)
        # Timer
        seconds = max(0, (self.timer + 59) // 60)
        timer_str = f"TIME:{seconds:02d}"
        pyxel.text(SCREEN_W - 52, 2, timer_str, WHITE if seconds > 10 else RED)
        # Heat bar
        bar_x = SCREEN_W - 56
        bar_y = 10
        bar_w = 48
        bar_h = 5
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, GRAY)
        heat_w = int(bar_w * (self.heat / HEAT_MAX))
        heat_color = RED if self.heat >= HEAT_MAX else (ORANGE if self.heat >= 60 else YELLOW)
        pyxel.rect(bar_x, bar_y, heat_w, bar_h, heat_color)
        pyxel.text(SCREEN_W - 56, 16, "HEAT", GRAY)

        # Super timer
        if self._is_super:
            super_left = (self.super_timer + 59) // 60
            pyxel.text(SCREEN_W // 2 - 20, 2, f"SUPER:{super_left}s", LIME)

    def _draw_charge_bar(self, shake_x: int, shake_y: int) -> None:
        bar_x = 4
        bar_y = SCREEN_H - 10
        bar_w = SCREEN_W - 8
        bar_h = 6
        if self.charging:
            fill_w = int(bar_w * (self.charge / 100.0))
            pyxel.rectb(bar_x, bar_y, bar_w, bar_h, GRAY)
            c = RED if self.charge >= 100 else YELLOW
            pyxel.rect(bar_x, bar_y, fill_w, bar_h, c)

    def _draw_game_over(self) -> None:
        pyxel.rect(SCREEN_W // 2 - 70, SCREEN_H // 2 - 35, 140, 70, NAVY)
        pyxel.rectb(SCREEN_W // 2 - 70, SCREEN_H // 2 - 35, 140, 70, RED)
        go_text = "GAME OVER"
        tw = len(go_text) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, SCREEN_H // 2 - 28, go_text, RED)
        score_str = f"SCORE: {self.score:06d}"
        tw2 = len(score_str) * 4
        pyxel.text(SCREEN_W // 2 - tw2 // 2, SCREEN_H // 2 - 8, score_str, WHITE)
        combo_str = f"MAX COMBO: {self.max_combo}"
        tw3 = len(combo_str) * 4
        pyxel.text(SCREEN_W // 2 - tw3 // 2, SCREEN_H // 2 + 4, combo_str, YELLOW)
        retry = "SPACE or CLICK to retry"
        tw4 = len(retry) * 4
        pyxel.text(SCREEN_W // 2 - tw4 // 2, SCREEN_H // 2 + 20, retry, GRAY)


if __name__ == "__main__":
    Game()
