import random
import math
from enum import Enum
from dataclasses import dataclass

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

COLOR_NAMES = ["RED", "LIME", "DARK_BLUE", "YELLOW"]
COLOR_VALS = [RED, LIME, DARK_BLUE, YELLOW]
COLOR_COUNT = 4


class Phase(Enum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


@dataclass
class Target:
    x: int
    y: int
    color: int
    life: int = 300


@dataclass
class Knight:
    x: int
    y: int
    color: int


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
    CELL = 28
    BOARD_X = 48
    BOARD_Y = 8
    BOARD_W = 8
    BOARD_H = 8
    MAX_HEAT = 100
    GAME_TIME = 60 * 30
    SUPER_DURATION = 300
    TARGET_LIFETIME = 300
    TARGET_COUNT_MAX = 5
    SPAWN_INTERVAL_INIT = 60
    SPAWN_INTERVAL_MIN = 20
    KNIGHT_COLOR_CYCLE = 90
    KNIGHT_COLOR_CYCLE_MIN = 40

    RAINBOW_COLORS = [RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK]

    def __init__(self):
        pyxel.init(320, 240, title="KNIGHT CHAIN", fps=30, display_scale=2)
        self.best_score = 0
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self):
        self.phase = Phase.TITLE
        self.knight = Knight(x=3, y=4, color=0)
        self.targets: list[Target] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = self.GAME_TIME
        self.super_timer = 0
        self.super_mode = False
        self.spawn_timer = self.SPAWN_INTERVAL_INIT
        self.color_cycle_timer = self.KNIGHT_COLOR_CYCLE
        self._rng = random.Random()

    # ---------- logic (no pyxel calls) ----------

    @staticmethod
    def _get_knight_moves(kx: int, ky: int) -> list[tuple[int, int]]:
        offsets = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
        moves: list[tuple[int, int]] = []
        for dx, dy in offsets:
            nx, ny = kx + dx, ky + dy
            if 0 <= nx < Game.BOARD_W and 0 <= ny < Game.BOARD_H:
                moves.append((nx, ny))
        return moves

    def _speed_for_time(self) -> float:
        elapsed = self.GAME_TIME - self.timer
        return elapsed / self.GAME_TIME

    def _spawn_interval(self) -> int:
        t = self._speed_for_time()
        return int(self.SPAWN_INTERVAL_INIT + t * (self.SPAWN_INTERVAL_MIN - self.SPAWN_INTERVAL_INIT))

    def _cycle_interval(self) -> int:
        t = self._speed_for_time()
        return int(self.KNIGHT_COLOR_CYCLE + t * (self.KNIGHT_COLOR_CYCLE_MIN - self.KNIGHT_COLOR_CYCLE))

    def _target_lifetime(self) -> int:
        t = self._speed_for_time()
        return int(self.TARGET_LIFETIME - t * 100)

    def _spawn_target(self):
        if len(self.targets) >= self.TARGET_COUNT_MAX:
            return
        occupied = {(t.x, t.y) for t in self.targets}
        occupied.add((self.knight.x, self.knight.y))
        available = [(x, y) for x in range(self.BOARD_W) for y in range(self.BOARD_H) if (x, y) not in occupied]
        if not available:
            return
        x, y = self._rng.choice(available)
        color = self._rng.randrange(COLOR_COUNT)
        life = self._target_lifetime()
        self.targets.append(Target(x=x, y=y, color=color, life=life))

    def _handle_move(self, tx: int, ty: int):
        if not self.super_mode and (tx, ty) == (self.knight.x, self.knight.y):
            return

        self.knight.x = tx
        self.knight.y = ty

        target = None
        for t in self.targets:
            if t.x == tx and t.y == ty:
                target = t
                break

        if target is not None:
            self.targets.remove(target)
            color_val = COLOR_VALS[target.color]

            if self.super_mode:
                self.combo += 1
                pts = 10 * self.combo * 3
                self.score += pts
                self._add_floating_text(tx, ty, f"+{pts}", color_val)
                self._spawn_particles(tx, ty, color_val, 20)
            elif target.color == self.knight.color:
                self.combo += 1
                pts = 10 * self.combo
                self.score += pts
                self._add_floating_text(tx, ty, f"+{pts}", color_val)
                self._spawn_particles(tx, ty, color_val, 8)
                if self.combo >= 4 and not self.super_mode:
                    self.super_mode = True
                    self.super_timer = self.SUPER_DURATION
                    self._add_floating_text(tx, ty, "SUPER KNIGHT!", YELLOW)
            else:
                self._add_floating_text(tx, ty, "WRONG!", RED)
                self._spawn_particles(tx, ty, RED, 4)
                self.heat += 15.0
                self.combo = 0

        if self.combo > self.max_combo:
            self.max_combo = self.combo

    def _update_timers(self):
        self.timer -= 1
        if self.timer < 0:
            self.timer = 0

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_timer = self._spawn_interval()
            self._spawn_target()

        self.color_cycle_timer -= 1
        if self.color_cycle_timer <= 0:
            self.color_cycle_timer = self._cycle_interval()
            self.knight.color = (self.knight.color + 1) % COLOR_COUNT

        for t in self.targets:
            t.life -= 1
        self.targets = [t for t in self.targets if t.life > 0]

        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0
                self.combo = 0

    def _update_particles(self):
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self):
        for ft in self.floating_texts:
            ft.y -= 0.8
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _spawn_particles(self, col: int, row: int, color: int, count: int):
        cx = self.BOARD_X + col * self.CELL + self.CELL // 2
        cy = self.BOARD_Y + row * self.CELL + self.CELL // 2
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 3.0)
            life = self._rng.randint(10, 25)
            self.particles.append(
                Particle(
                    x=float(cx),
                    y=float(cy),
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed - 1.0,
                    life=life,
                    color=color,
                )
            )

    def _add_floating_text(self, col: int, row: int, text: str, color: int):
        cx = self.BOARD_X + col * self.CELL + self.CELL // 2
        cy = self.BOARD_Y + row * self.CELL + self.CELL // 2
        self.floating_texts.append(
            FloatingText(x=float(cx), y=float(cy), text=text, life=30, color=color)
        )

    def _screen_to_board(self, screen_x: int, screen_y: int) -> tuple[int, int] | None:
        col = (screen_x - self.BOARD_X) // self.CELL
        row = (screen_y - self.BOARD_Y) // self.CELL
        if 0 <= col < self.BOARD_W and 0 <= row < self.BOARD_H:
            return col, row
        return None

    # ---------- update / draw ----------

    def update(self):
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
                self.phase = Phase.PLAYING
        elif self.phase == Phase.PLAYING:
            self._update_timers()
            self._update_particles()
            self._update_floating_texts()

            if self.timer <= 0 or self.heat >= self.MAX_HEAT:
                self.phase = Phase.GAME_OVER
                if self.score > self.best_score:
                    self.best_score = self.score
                return

            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                pos = self._screen_to_board(pyxel.mouse_x, pyxel.mouse_y)
                if pos is not None:
                    tx, ty = pos
                    if self.super_mode:
                        self._handle_move(tx, ty)
                    else:
                        valid = self._get_knight_moves(self.knight.x, self.knight.y)
                        if (tx, ty) in valid:
                            self._handle_move(tx, ty)
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
                self.phase = Phase.PLAYING

    def draw(self):
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_board()
            self._draw_highlights()
            self._draw_targets()
            self._draw_knight()
            self._draw_particles()
            self._draw_floating_texts()
            self._draw_ui_bar()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    # ---------- draw helpers ----------

    def _draw_title(self):
        pyxel.text(100, 60, "KNIGHT CHAIN", WHITE)
        pyxel.text(60, 90, "Click valid squares to move knight", GRAY)
        pyxel.text(60, 102, "Match knight color with targets", GRAY)
        pyxel.text(60, 120, "COMBO >= 4 = SUPER KNIGHT", YELLOW)
        pyxel.text(85, 150, "R or SPACE to start", LIME)
        if self.best_score > 0:
            pyxel.text(100, 170, f"BEST SCORE: {self.best_score}", ORANGE)

    def _draw_board(self):
        for row in range(self.BOARD_H):
            for col in range(self.BOARD_W):
                x = self.BOARD_X + col * self.CELL
                y = self.BOARD_Y + row * self.CELL
                sq_color = WHITE if (row + col) % 2 == 0 else DARK_BLUE
                pyxel.rect(x, y, self.CELL, self.CELL, sq_color)

    def _draw_highlights(self):
        if self.super_mode:
            for row in range(self.BOARD_H):
                for col in range(self.BOARD_W):
                    if col == self.knight.x and row == self.knight.y:
                        continue
                    x = self.BOARD_X + col * self.CELL
                    y = self.BOARD_Y + row * self.CELL
                    idx = (pyxel.frame_count // 4 + col + row) % len(self.RAINBOW_COLORS)
                    rainbow = self.RAINBOW_COLORS[idx]
                    pyxel.rectb(x, y, self.CELL, self.CELL, rainbow)
        else:
            valid = self._get_knight_moves(self.knight.x, self.knight.y)
            for nx, ny in valid:
                x = self.BOARD_X + nx * self.CELL
                y = self.BOARD_Y + ny * self.CELL
                target_color = None
                for t in self.targets:
                    if t.x == nx and t.y == ny:
                        target_color = COLOR_VALS[t.color]
                        break
                border_color = target_color if target_color is not None else GRAY
                pyxel.rectb(x, y, self.CELL, self.CELL, border_color)

    def _draw_targets(self):
        for t in self.targets:
            cx = self.BOARD_X + t.x * self.CELL + self.CELL // 2
            cy = self.BOARD_Y + t.y * self.CELL + self.CELL // 2
            color = COLOR_VALS[t.color]
            r = self.CELL // 2 - 4
            pyxel.circ(cx, cy, r, color)
            if t.life < 60 and (pyxel.frame_count // 15) % 2 == 0:
                pyxel.circb(cx, cy, r + 1, WHITE)

    def _draw_knight(self):
        cx = self.BOARD_X + self.knight.x * self.CELL + self.CELL // 2
        cy = self.BOARD_Y + self.knight.y * self.CELL + self.CELL // 2

        if self.super_mode:
            knight_color = self.RAINBOW_COLORS[(pyxel.frame_count // 3) % len(self.RAINBOW_COLORS)]
        else:
            knight_color = COLOR_VALS[self.knight.color]

        s = 7
        top = (cx, cy - s)
        right = (cx + s, cy)
        bottom = (cx, cy + s)
        left = (cx - s, cy)
        pyxel.tri(*top, *right, *left, knight_color)
        pyxel.tri(*bottom, *right, *left, knight_color)
        pyxel.rectb(cx - s, cy - s, s * 2, s * 2, WHITE)

    def _draw_particles(self):
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self):
        for ft in self.floating_texts:
            x = int(ft.x) - len(ft.text) * 2
            y = int(ft.y)
            pyxel.text(x, y, ft.text, ft.color)

    def _draw_ui_bar(self):
        secs = max(0, self.timer // 30)
        info = f"T:{secs}S  SC:{self.score}  x{self.combo}"
        heat_w = int((self.heat / self.MAX_HEAT) * 320)
        heat_c = RED if self.heat > 60 else YELLOW if self.heat > 30 else LIME
        pyxel.rect(0, 232, heat_w, 4, heat_c)
        pyxel.text(2, 236, info, WHITE)
        if self.super_mode:
            s_secs = self.super_timer // 30
            super_text = f"SUPER:{s_secs}S"
            pyxel.text(320 - len(super_text) * 4 - 2, 236, super_text, YELLOW)

    def _draw_game_over(self):
        pyxel.text(110, 60, "GAME OVER", RED)
        pyxel.text(100, 90, f"SCORE: {self.score}", WHITE)
        pyxel.text(95, 105, f"MAX COMBO: {self.max_combo}", YELLOW)
        pyxel.text(100, 125, f"BEST: {self.best_score}", ORANGE)
        if self.heat >= self.MAX_HEAT:
            pyxel.text(95, 145, "OVERHEAT!", RED)
        else:
            pyxel.text(100, 145, "TIME UP!", GRAY)
        pyxel.text(80, 175, "R or SPACE to retry", LIME)

if __name__ == "__main__":
    Game()
