from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import pyxel

SCREEN_W = 320
SCREEN_H = 240
BELT_COUNT = 3
BELT_Y_START = 40
BELT_SPACING = 60
BELT_HEIGHT = 30
BELT_SPEED_BASE = 1.0
ITEM_SIZE = 16

COLOR_COUNT = 4
COLOR_NAMES = ["RED", "GREEN", "YELLOW", "CYAN"]
COLOR_VALS = [8, 3, 10, 12]

BIN_COUNT = 4
BIN_Y = SCREEN_H - 40
BIN_WIDTH = 60
BIN_X_START = (SCREEN_W - BIN_COUNT * BIN_WIDTH) // 2
BIN_HEIGHT = 40

COMBO_THRESHOLD = 5
SUPER_DURATION = 300
SUPER_MULTIPLIER = 3

MAX_HEAT = 100
HEAT_PER_WRONG = 15
HEAT_PER_MISS = 8
HEAT_DECAY = 0.05

SPAWN_INTERVAL = 45
SPAWN_INTERVAL_MIN = 20
DIFFICULTY_RAMP = 0.002


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Item:
    x: float
    y: float
    color: int
    belt: int
    alive: bool = True


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
        font_path = Path(__file__).with_name("k8x12.bdf")
        if font_path.exists():
            pyxel.load(str(font_path))
        pyxel.init(SCREEN_W, SCREEN_H, title="Belt Surge", display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_timer = 0
        self.spawn_timer = 0
        self.spawn_interval = float(SPAWN_INTERVAL)
        self.frame = 0
        self.items: list[Item] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._rng = random.Random()
        self._shake_frames = 0
        self._sort_anim_timer = 0
        self._last_sorted_color: int = -1

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE):
            self._start_game()
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            pyxel.quit()

    def _start_game(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_timer = 0
        self.spawn_timer = 0
        self.spawn_interval = float(SPAWN_INTERVAL)
        self.frame = 0
        self.items.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self._shake_frames = 0
        self._sort_anim_timer = 0
        self._last_sorted_color = -1

    def _update_playing(self) -> None:
        self.frame += 1

        if pyxel.btnp(pyxel.KEY_ESCAPE):
            pyxel.quit()

        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.combo = 0

        self.spawn_interval = max(
            float(SPAWN_INTERVAL_MIN),
            SPAWN_INTERVAL - DIFFICULTY_RAMP * self.frame,
        )
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self._spawn_item()
            self.spawn_timer = self.spawn_interval

        self._update_items()

        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER

        self.heat = max(0.0, self.heat - HEAT_DECAY)

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._handle_click(pyxel.mouse_x, pyxel.mouse_y)

        self._update_particles()
        self._update_floating_texts()

        if self._shake_frames > 0:
            self._shake_frames -= 1

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self._start_game()
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            pyxel.quit()

    def _belt_y(self, belt_idx: int) -> int:
        return BELT_Y_START + belt_idx * BELT_SPACING

    def _spawn_item(self) -> None:
        belt = self._rng.randrange(BELT_COUNT)
        color = self._rng.randrange(COLOR_COUNT)
        y = self._belt_y(belt)
        item = Item(x=-ITEM_SIZE, y=float(y), color=color, belt=belt)
        self.items.append(item)

    def _belt_speed(self) -> float:
        bonus = 0.0
        if self.frame > 3600:
            bonus += 0.6
        elif self.frame > 1800:
            bonus += 0.3
        return BELT_SPEED_BASE + bonus

    def _update_items(self) -> None:
        speed = self._belt_speed()
        for item in self.items:
            if not item.alive:
                continue
            item.x += speed
            if item.x > SCREEN_W + ITEM_SIZE:
                item.alive = False
                self.heat += HEAT_PER_MISS
                self._spawn_particles(item.x, item.y, 7, 8)
                self.floating_texts.append(
                    FloatingText(
                        x=item.x - 10,
                        y=item.y,
                        text="MISS!",
                        life=40,
                        color=8,
                    )
                )
        self.items = [it for it in self.items if it.alive]

    def _handle_click(self, mx: int, my: int) -> None:
        best_item: Item | None = None
        best_dist = float("inf")

        for item in self.items:
            if not item.alive:
                continue
            hw = ITEM_SIZE // 2
            if abs(mx - item.x) <= hw and abs(my - item.y) <= hw:
                dist = (mx - item.x) ** 2 + (my - item.y) ** 2
                if dist < best_dist:
                    best_dist = dist
                    best_item = item

        if best_item is not None:
            self._sort_item(best_item, best_item.color)

    def _sort_item(self, item: Item, bin_idx: int) -> None:
        is_super = self.super_timer > 0

        if item.color == bin_idx:
            item.alive = False
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            points = 10 + self.combo * 5
            if is_super:
                points *= SUPER_MULTIPLIER
            self.score += points

            label = f"+{points}"
            if self.combo >= COMBO_THRESHOLD and not is_super:
                self.super_timer = SUPER_DURATION
                self.floating_texts.append(
                    FloatingText(
                        x=item.x,
                        y=item.y - 16,
                        text="SUPER!",
                        life=60,
                        color=10,
                    )
                )
            if self.combo > 1:
                label = f"+{points} x{self.combo}"

            self.floating_texts.append(
                FloatingText(
                    x=item.x + 8,
                    y=item.y - 8,
                    text=label,
                    life=30,
                    color=10 if self.combo >= 3 else 7,
                )
            )
            self._spawn_particles(item.x, item.y, COLOR_VALS[item.color], 12)
            self._last_sorted_color = item.color
        else:
            if not is_super:
                item.alive = False
                self.combo = 0
                self.heat += HEAT_PER_WRONG
                self.floating_texts.append(
                    FloatingText(
                        x=item.x,
                        y=item.y - 8,
                        text="WRONG!",
                        life=40,
                        color=8,
                    )
                )
                self._spawn_particles(item.x, item.y, COLOR_VALS[item.color], 6)
                self._shake_frames = 8
            else:
                item.alive = False
                points = (10 + self.combo * 5) * SUPER_MULTIPLIER
                self.score += points
                self.combo += 1
                self.max_combo = max(self.max_combo, self.combo)
                self.floating_texts.append(
                    FloatingText(
                        x=item.x + 8,
                        y=item.y - 8,
                        text=f"+{points}",
                        life=30,
                        color=12,
                    )
                )
                self._spawn_particles(item.x, item.y, COLOR_VALS[item.color], 12)

            self._last_sorted_color = item.color

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed_val = self._rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed_val,
                    vy=math.sin(angle) * speed_val,
                    life=self._rng.randint(10, 25),
                    color=color,
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 1
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.cls(1)
        pyxel.text(SCREEN_W // 2 - 40, 80, "BELT SURGE", 7)
        pyxel.text(SCREEN_W // 2 - 80, 130, "Click items to sort by color!", 7)
        pyxel.text(SCREEN_W // 2 - 80, 148, "Same color = COMBO -> SUPER SORT!", 7)
        pyxel.text(SCREEN_W // 2 - 80, 166, "Wrong color = HEAT -> GAME OVER", 7)
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(SCREEN_W // 2 - 50, 200, "Press SPACE to start", 10)

    def _draw_playing(self) -> None:
        shake_x = 0
        shake_y = 0
        if self._shake_frames > 0:
            shake_x = self._rng.randint(-2, 2)
            shake_y = self._rng.randint(-2, 2)

        pyxel.cls(0)

        is_super = self.super_timer > 0
        if is_super:
            hue = (pyxel.frame_count // 4) % 16
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, hue)

        for i in range(BELT_COUNT):
            self._draw_belt(i, shake_x, shake_y)

        for item in self.items:
            if item.alive:
                self._draw_item(item, shake_x, shake_y)

        self._draw_bins(shake_x, shake_y)

        self._draw_particles(shake_x, shake_y)
        self._draw_floating_texts(shake_x, shake_y)

        self._draw_hud()

    def _draw_game_over(self) -> None:
        pyxel.cls(1)
        pyxel.text(SCREEN_W // 2 - 30, 60, "GAME OVER", 8)
        pyxel.text(SCREEN_W // 2 - 50, 100, f"Score: {self.score}", 7)
        pyxel.text(SCREEN_W // 2 - 50, 120, f"Max Combo: {self.max_combo}", 7)
        pyxel.text(SCREEN_W // 2 - 60, 160, "Press R to restart", 10)

    def _draw_belt(self, belt_idx: int, shake_x: int, shake_y: int) -> None:
        y = self._belt_y(belt_idx)
        bx = shake_x
        by = y + shake_y
        pyxel.rect(bx, by - BELT_HEIGHT // 2, SCREEN_W, BELT_HEIGHT, 5)

        scroll = (self.frame + belt_idx * 20) % 16
        for sx in range(-scroll, SCREEN_W, 16):
            pyxel.line(bx + sx, by - BELT_HEIGHT // 2 + 4, bx + sx + 8, by - BELT_HEIGHT // 2 + 4, 13)
            pyxel.line(bx + sx, by + BELT_HEIGHT // 2 - 4, bx + sx + 8, by + BELT_HEIGHT // 2 - 4, 13)

    def _draw_item(self, item: Item, shake_x: int, shake_y: int) -> None:
        x = int(item.x) + shake_x
        y = int(item.y) + shake_y
        hw = ITEM_SIZE // 2
        color = COLOR_VALS[item.color]

        is_super = self.super_timer > 0
        if is_super:
            glow = (pyxel.frame_count // 4) % 2
            if glow:
                pyxel.rectb(x - hw - 1, y - hw - 1, ITEM_SIZE + 2, ITEM_SIZE + 2, 7)

        pyxel.rect(x - hw, y - hw, ITEM_SIZE, ITEM_SIZE, color)
        pyxel.rectb(x - hw, y - hw, ITEM_SIZE, ITEM_SIZE, 7)

    def _draw_bins(self, shake_x: int, shake_y: int) -> None:
        for i in range(BIN_COUNT):
            bx = BIN_X_START + i * BIN_WIDTH + shake_x
            by = BIN_Y + shake_y
            pyxel.rectb(bx, by, BIN_WIDTH, BIN_HEIGHT, COLOR_VALS[i])
            pyxel.rect(bx + 1, by + 1, BIN_WIDTH - 2, BIN_HEIGHT - 2, 5)
            label = COLOR_NAMES[i]
            lx = bx + (BIN_WIDTH - len(label) * 4) // 2
            pyxel.text(lx, by + BIN_HEIGHT // 2 - 3, label, COLOR_VALS[i])

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, 22, 5)
        pyxel.text(4, 4, f"Score: {self.score}", 7)
        combo_col = 10 if self.combo >= COMBO_THRESHOLD else 7
        pyxel.text(SCREEN_W // 2 - 30, 4, f"Combo: {self.combo}", combo_col)

        bar_x = SCREEN_W - 106
        bar_y = 4
        bar_w = 100
        bar_h = 8
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, 7)
        fill = int(self.heat / MAX_HEAT * bar_w)
        if self.heat > 60:
            bar_color = 8
        elif self.heat > 30:
            bar_color = 10
        else:
            bar_color = 3
        pyxel.rect(bar_x + 1, bar_y + 1, fill, bar_h - 2, bar_color)
        pyxel.text(bar_x, bar_y + 6, "HEAT", 7)

        if self.super_timer > 0:
            sec = self.super_timer // 60
            pyxel.text(SCREEN_W // 2 - 20, 14, f"SUPER {sec}s", 10)

    def _draw_particles(self, shake_x: int, shake_y: int) -> None:
        for p in self.particles:
            alpha = p.life / 25
            if alpha > 0.5:
                pyxel.rect(
                    int(p.x) + shake_x - 1,
                    int(p.y) + shake_y - 1,
                    3,
                    3,
                    p.color,
                )
            else:
                pyxel.pset(
                    int(p.x) + shake_x,
                    int(p.y) + shake_y,
                    p.color,
                )

    def _draw_floating_texts(self, shake_x: int, shake_y: int) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 60
            if alpha <= 0:
                continue
            col = ft.color
            if alpha < 0.3:
                col = 5
            pyxel.text(
                int(ft.x) + shake_x - len(ft.text) * 2,
                int(ft.y) + shake_y,
                ft.text,
                col,
            )


if __name__ == "__main__":
    Game()
