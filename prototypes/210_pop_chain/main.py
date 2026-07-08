"""POP CHAIN — Bubble wrap popping game with CA inflation and COMBO chains."""
from __future__ import annotations

import enum
import math
import random
from dataclasses import dataclass

import pyxel


SCREEN_W = 320
SCREEN_H = 240
COLS = 10
ROWS = 8
CELL = 24
GRID_OX = (SCREEN_W - COLS * CELL) // 2
GRID_OY = (SCREEN_H - ROWS * CELL) // 2
COLORS = (8, 3, 5, 10)
INFLATE_INTERVAL = 120
COLOR_CYCLE_TIME = 90
SUPER_DURATION = 300
GAME_TIME = 60 * 60
BUBBLE_MAX = 32
HEAT_MAX = 100
HEAT_WRONG = 15
HEAT_DECAY = 0.05
COMBO_SUPER = 4
INITIAL_BUBBLES = 8


class Phase(enum.Enum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


@dataclass
class Bubble:
    col: int
    row: int
    color: int
    life: int = 0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class FloatText:
    x: float
    y: float
    text: str
    life: int
    color: int


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="POP CHAIN", display_scale=2)
        pyxel.mouse(True)
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatText] = []
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = GAME_TIME
        self.super_timer = 0
        self.color_index = 0
        self.color_timer = COLOR_CYCLE_TIME
        self.frame = 0
        self.grid: list[list[Bubble | None]] = (
            [[None for _ in range(COLS)] for _ in range(ROWS)]
        )
        self.particles.clear()
        self.floating_texts.clear()

    # ── Core logic (headless-testable) ─────────────────────────

    def _screen_to_grid(self, mx: int, my: int) -> tuple[int, int] | None:
        col = (mx - GRID_OX) // CELL
        row = (my - GRID_OY) // CELL
        if 0 <= col < COLS and 0 <= row < ROWS:
            return (col, row)
        return None

    def _random_bubble_color(self) -> int:
        return random.choice(COLORS)

    def _count_alive_bubbles(self) -> int:
        count = 0
        for row in range(ROWS):
            for col in range(COLS):
                bubble = self.grid[row][col]
                if bubble is not None and bubble.life == 0:
                    count += 1
        return count

    def _spawn_initial_bubbles(self) -> None:
        for _ in range(INITIAL_BUBBLES):
            while True:
                col = random.randrange(COLS)
                row = random.randrange(ROWS)
                if self.grid[row][col] is None:
                    self.grid[row][col] = Bubble(
                        col, row, self._random_bubble_color(), life=0
                    )
                    break

    def _inflate_bubbles(self) -> None:
        if self._count_alive_bubbles() >= BUBBLE_MAX:
            return

        sources: list[tuple[int, int, Bubble]] = []
        for row in range(ROWS):
            for col in range(COLS):
                bubble = self.grid[row][col]
                if bubble is not None and bubble.life == 0:
                    sources.append((col, row, bubble))

        for col, row, bubble in sources:
            if self._count_alive_bubbles() >= BUBBLE_MAX:
                return
            if random.random() < 0.4:
                neighbors: list[tuple[int, int]] = []
                for dc, dr in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    nc = col + dc
                    nr = row + dr
                    if 0 <= nc < COLS and 0 <= nr < ROWS and (
                        self.grid[nr][nc] is None
                    ):
                        neighbors.append((nc, nr))
                if neighbors:
                    nc, nr = random.choice(neighbors)
                    self.grid[nr][nc] = Bubble(nc, nr, bubble.color, life=0)

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION

        alive: list[tuple[int, int, Bubble]] = []
        for row in range(ROWS):
            for col in range(COLS):
                bubble = self.grid[row][col]
                if bubble is not None and bubble.life == 0:
                    alive.append((col, row, bubble))

        for col, row, bubble in alive:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            pts = int(10 * (1 + self.combo * 0.5))
            self.score += pts
            bubble.life = 60
            x = float(col * CELL + GRID_OX + CELL // 2)
            y = float(row * CELL + GRID_OY + CELL // 2)
            self._spawn_particles(x, y, bubble.color, random.randint(4, 8))
            self._spawn_floating_text(x, y, f"+{pts}", bubble.color)

    def _pop_bubble(self, col: int, row: int) -> int:
        bubble = self.grid[row][col]
        if bubble is None or bubble.life > 0:
            return 0

        active_color = COLORS[self.color_index]
        is_match = self.super_timer > 0 or bubble.color == active_color

        if is_match:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            multiplier = 3 if self.super_timer > 0 else 1
            pts = int(10 * (1 + self.combo * 0.5)) * multiplier
            self.score += pts
            bubble.life = 60
            x = float(col * CELL + GRID_OX + CELL // 2)
            y = float(row * CELL + GRID_OY + CELL // 2)
            self._spawn_particles(x, y, bubble.color, random.randint(4, 8))
            self._spawn_floating_text(x, y, f"+{pts}", bubble.color)

            if self.combo >= COMBO_SUPER:
                if self.super_timer == 0:
                    self._activate_super()
                else:
                    self.super_timer = SUPER_DURATION

            return pts
        else:
            self.combo = 0
            self.heat = min(float(HEAT_MAX), self.heat + HEAT_WRONG)
            if self.heat >= HEAT_MAX:
                self.phase = Phase.GAME_OVER
            bubble.life = 60
            x = float(col * CELL + GRID_OX + CELL // 2)
            y = float(row * CELL + GRID_OY + CELL // 2)
            self._spawn_particles(x, y, 8, random.randint(2, 4))
            self._spawn_floating_text(x, y, "MISS!", 8)
            return 0

    def _update_heat(self) -> None:
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_bubble_animations(self) -> None:
        for row in range(ROWS):
            for col in range(COLS):
                bubble = self.grid[row][col]
                if bubble is not None and bubble.life > 0:
                    bubble.life -= 1
                    if bubble.life <= 0:
                        self.grid[row][col] = None

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def _update_floating_texts(self) -> None:
        alive: list[FloatText] = []
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life > 0:
                alive.append(ft)
        self.floating_texts = alive

    def _update_timer(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER

    def _spawn_particles(
        self, x: float, y: float, color: int, count: int
    ) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(0.5, 2.5)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = random.randint(15, 25)
            self.particles.append(Particle(x, y, vx, vy, life, color))

    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        self.floating_texts.append(FloatText(x, y, text, 20, color))

    # ── Update ─────────────────────────────────────────────────

    def _start_game(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = GAME_TIME
        self.super_timer = 0
        self.color_index = 0
        self.color_timer = COLOR_CYCLE_TIME
        self.frame = 0
        self.grid = [[None for _ in range(COLS)] for _ in range(ROWS)]
        self.particles.clear()
        self.floating_texts.clear()
        self._spawn_initial_bubbles()
        self.phase = Phase.PLAYING

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_RETURN):
            self._start_game()

    def _update_playing(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            cell = self._screen_to_grid(pyxel.mouse_x, pyxel.mouse_y)
            if cell is not None:
                self._pop_bubble(cell[0], cell[1])

        if self.phase == Phase.GAME_OVER:
            return

        self.frame += 1

        if self.frame % INFLATE_INTERVAL == 0:
            self._inflate_bubbles()

        self.color_timer -= 1
        if self.color_timer <= 0:
            self.color_timer = COLOR_CYCLE_TIME
            self.color_index = (self.color_index + 1) % 4

        if self.super_timer > 0:
            self.super_timer -= 1

        self._update_heat()
        self._update_bubble_animations()
        self._update_particles()
        self._update_floating_texts()
        self._update_timer()

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    # ── Draw ───────────────────────────────────────────────────

    def _draw_grid(self) -> None:
        for row in range(ROWS + 1):
            y = row * CELL + GRID_OY
            pyxel.line(GRID_OX, y, GRID_OX + COLS * CELL, y, 1)
        for col in range(COLS + 1):
            x = col * CELL + GRID_OX
            pyxel.line(x, GRID_OY, x, GRID_OY + ROWS * CELL, 1)

    def _draw_bubbles(self) -> None:
        for row in range(ROWS):
            for col in range(COLS):
                bubble = self.grid[row][col]
                if bubble is None:
                    continue
                cx = col * CELL + GRID_OX + CELL // 2
                cy = row * CELL + GRID_OY + CELL // 2

                if bubble.life > 0:
                    ratio = bubble.life / 60.0
                    r = max(1, int((CELL // 2 - 2) * ratio))
                    color = 7
                else:
                    r = CELL // 2 - 2
                    color = bubble.color

                pyxel.circ(cx, cy, r, color)
                pyxel.circb(cx, cy, r, 7)
                hl_r = max(1, r // 3)
                pyxel.circ(cx - hl_r, cy - hl_r, hl_r, 7)

    def _draw_hud(self) -> None:
        time_s = max(0, self.timer // 60)
        pyxel.text(4, 4, f"TIME: {time_s}", 7)
        pyxel.text(SCREEN_W // 2 - 20, 4, f"{self.score}", 7)

        if self.combo >= 2:
            combo_text = f"COMBO x{self.combo}"
            x = SCREEN_W - len(combo_text) * 4 - 4
            combo_color = 9 if self.combo >= COMBO_SUPER else 7
            if self.super_timer > 0:
                combo_color = 9
            pyxel.text(x, 4, combo_text, combo_color)

    def _draw_active_color(self) -> None:
        cx = 30
        cy = SCREEN_H - 16
        if self.super_timer > 0:
            rainbow_idx = (self.frame // 8) % 4
            active_color = COLORS[rainbow_idx]
        else:
            active_color = COLORS[self.color_index]
        pyxel.circ(cx, cy, 8, active_color)
        pyxel.circb(cx, cy, 8, 7)
        pyxel.text(cx + 12, cy - 4, "POP", 7)

    def _draw_heat_bar(self) -> None:
        bar_x = 70
        bar_y = SCREEN_H - 20
        bar_w = 200
        bar_h = 6
        fill = int(bar_w * (self.heat / HEAT_MAX))

        if fill > 0:
            ratio = self.heat / HEAT_MAX
            if ratio < 0.5:
                heat_color = 8
            elif ratio < 0.8:
                heat_color = 9
            else:
                heat_color = 10
            pyxel.rect(bar_x, bar_y, fill, bar_h, heat_color)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, 7)
        pyxel.text(bar_x - 36, bar_y - 1, "HEAT", 7)

    def _draw_super_effects(self) -> None:
        if self.super_timer > 0:
            rainbow = (8, 9, 10, 11, 12, 6)
            ci = (self.frame // 8) % len(rainbow)
            pyxel.rectb(
                GRID_OX - 2,
                GRID_OY - 2,
                COLS * CELL + 4,
                ROWS * CELL + 4,
                rainbow[ci],
            )

            super_text = "SUPER!"
            x = SCREEN_W // 2 - len(super_text) * 2
            pyxel.text(
                x,
                GRID_OY - 12,
                super_text,
                rainbow[(ci + 2) % len(rainbow)],
            )

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            pyxel.text(
                int(ft.x - len(ft.text) * 2), int(ft.y), ft.text, ft.color
            )

    def _draw_mouse_cursor(self) -> None:
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        cell = self._screen_to_grid(mx, my)
        if cell is not None:
            col, row = cell
            cx = col * CELL + GRID_OX + CELL // 2
            cy = row * CELL + GRID_OY + CELL // 2
            pyxel.circb(cx, cy, CELL // 2 - 1, 7)

    def _draw_title(self) -> None:
        pyxel.cls(0)

        title = "POP CHAIN"
        x = SCREEN_W // 2 - len(title) * 4
        pyxel.text(x, 50, title, 7)

        instructions = [
            "Click matching bubbles!",
            "CA inflation + COMBO chain = SUPER POP",
        ]
        y = 80
        for line in instructions:
            lx = SCREEN_W // 2 - len(line) * 2
            pyxel.text(lx, y, line, 13)
            y += 12

        y += 8
        for i, c in enumerate(COLORS):
            cx = SCREEN_W // 2 - 30 + i * 20
            pyxel.circ(cx, y + 6, 6, c)
            pyxel.circb(cx, y + 6, 6, 7)

        y += 24
        start_text = "Click or ENTER to start"
        lx = SCREEN_W // 2 - len(start_text) * 2
        blink_color = 9 if (pyxel.frame_count // 30) % 2 == 0 else 13
        pyxel.text(lx, y, start_text, blink_color)

    def _draw_game_over(self) -> None:
        pyxel.cls(0)

        title = "GAME OVER"
        x = SCREEN_W // 2 - len(title) * 4
        pyxel.text(x, 70, title, 8)

        score_text = f"SCORE: {self.score}"
        x = SCREEN_W // 2 - len(score_text) * 2
        pyxel.text(x, 100, score_text, 7)

        combo_text = f"MAX COMBO: {self.max_combo}"
        x = SCREEN_W // 2 - len(combo_text) * 2
        pyxel.text(x, 116, combo_text, 9)

        retry_text = "Click or ENTER to retry"
        x = SCREEN_W // 2 - len(retry_text) * 2
        pyxel.text(x, 150, retry_text, 13)

    def _draw_playing(self) -> None:
        pyxel.cls(0)
        self._draw_grid()
        self._draw_bubbles()
        self._draw_super_effects()
        self._draw_hud()
        self._draw_active_color()
        self._draw_heat_bar()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_mouse_cursor()

    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()


if __name__ == "__main__":
    Game()
