from __future__ import annotations

import random as random_module
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Prize:
    x: int
    y: int
    color: int
    value: int


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


SCREEN_W: int = 320
SCREEN_H: int = 240
COLS: int = 8
ROWS: int = 6
CELL: int = 32
GRID_X: int = (320 - 8 * 32) // 2
GRID_Y: int = 24
COLORS: tuple[int, int, int, int] = (8, 11, 5, 10)
COLOR_NAMES: tuple[str, str, str, str] = ("RED", "LIME", "DARK_BLUE", "YELLOW")
SUPER_DURATION: int = 300
GAME_TIME: int = 60 * 30
MAX_HEAT: float = 100.0
HEAT_DECAY: float = 0.02
HEAT_MISMATCH: float = 15.0
HEAT_EMPTY: float = 5.0
BASE_VALUE: int = 10
MOVE_COOLDOWN: int = 5
SPAWN_INTERVAL_START: int = 60
SPAWN_INTERVAL_END: int = 30
COLOR_CYCLE_FRAMES: int = 90


class Game:
    def __init__(self) -> None:
        self._rng = random_module.Random()
        self._pre_init()
        pyxel.init(SCREEN_W, SCREEN_H, title="CLAW SURGE", display_scale=2)
        pyxel.run(self._update, self._draw)

    def _pre_init(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.timer: int = GAME_TIME
        self.claw_col: int = 0
        self.claw_row: int = 0
        self.claw_color: int = COLORS[0]
        self.super_timer: int = 0
        self.prizes: list[Prize] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.best_score: int = 0
        self._move_cooldown: int = 0
        self._color_idx: int = 0
        self._color_timer: int = COLOR_CYCLE_FRAMES
        self._spawn_timer: int = SPAWN_INTERVAL_START

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = GAME_TIME
        self.claw_col = COLS // 2
        self.claw_row = ROWS // 2
        self.claw_color = COLORS[0]
        self.super_timer = 0
        self.prizes = []
        self.particles = []
        self.floating_texts = []
        self._move_cooldown = 0
        self._color_idx = 0
        self._color_timer = COLOR_CYCLE_FRAMES
        self._spawn_timer = SPAWN_INTERVAL_START
        self._initial_spawn()

    def _initial_spawn(self) -> None:
        for row in range(ROWS):
            for col in range(COLS):
                if self._rng.random() < 0.6:
                    color = self._rng.choice(COLORS)
                    self.prizes.append(Prize(x=col, y=row, color=color, value=BASE_VALUE))

    def _get_prize_at(self, col: int, row: int) -> Prize | None:
        for p in self.prizes:
            if p.x == col and p.y == row:
                return p
        return None

    def _remove_prize_at(self, col: int, row: int) -> None:
        self.prizes = [p for p in self.prizes if not (p.x == col and p.y == row)]

    def _empty_slots(self) -> list[tuple[int, int]]:
        occupied = {(p.x, p.y) for p in self.prizes}
        return [(c, r) for r in range(ROWS) for c in range(COLS) if (c, r) not in occupied]

    def _claw_px(self) -> tuple[float, float]:
        return (
            GRID_X + self.claw_col * CELL + CELL // 2,
            GRID_Y + self.claw_row * CELL + CELL // 2,
        )

    def _grab_prize(self) -> None:
        prize = self._get_prize_at(self.claw_col, self.claw_row)
        cx, cy = self._claw_px()
        if prize is None:
            self.combo = 0
            self.heat = min(MAX_HEAT, self.heat + HEAT_EMPTY)
            self._spawn_miss_particles(cx, cy)
            self._spawn_floating_text(cx, cy - 8, "MISS!", 13, 20)
            return

        is_super = self.super_timer > 0
        is_match = is_super or (prize.color == self.claw_color)

        if is_match:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            multiplier = self.combo
            super_mult = 3.0 if is_super else 1.0
            points = int(prize.value * multiplier * super_mult)
            self.score += points
            particle_color = prize.color if not is_super else self._rng.choice(COLORS)
            count = 15 if is_super else self._rng.randint(6, 10)
            self._spawn_grab_particles(cx, cy, count, particle_color, is_super)
            self._spawn_floating_text(cx, cy - 16, f"+{points}", 7, 30)
            if self.combo >= 2:
                self._spawn_floating_text(cx, cy - 28, f"COMBO x{self.combo}", 10, 40)
            if self.combo >= 4 and not is_super:
                self._activate_super()
        else:
            self.combo = 0
            self.heat = min(MAX_HEAT, self.heat + HEAT_MISMATCH)
            self._spawn_mismatch_particles(cx, cy)
            self._spawn_floating_text(cx, cy - 8, "MISS", 13, 20)

        self._remove_prize_at(prize.x, prize.y)

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        cx, cy = self._claw_px()
        self._spawn_super_particles(cx, cy)
        self._spawn_floating_text(cx, cy - 40, "SUPER!", 10, 60)

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1

    def _update_color_cycle(self) -> None:
        if self.super_timer > 0:
            return
        self._color_timer -= 1
        if self._color_timer <= 0:
            self._color_timer = COLOR_CYCLE_FRAMES
            self._color_idx = (self._color_idx + 1) % 4
            self.claw_color = COLORS[self._color_idx]

    def _spawn_prizes(self) -> None:
        self._spawn_timer -= 1
        elapsed_ratio = 1.0 - (self.timer / GAME_TIME)
        interval = SPAWN_INTERVAL_START - (SPAWN_INTERVAL_START - SPAWN_INTERVAL_END) * elapsed_ratio
        if self._spawn_timer <= 0:
            self._spawn_timer = max(1, int(interval))
            slots = self._empty_slots()
            if slots:
                col, row = self._rng.choice(slots)
                color = self._rng.choice(COLORS)
                self.prizes.append(Prize(x=col, y=row, color=color, value=BASE_VALUE))

    def _update_heat(self) -> None:
        self.heat = max(0.0, self.heat - HEAT_DECAY)
        if self.heat >= MAX_HEAT:
            self._end_game()

    def _update_timer(self) -> None:
        if self.timer > 0:
            self.timer -= 1
        if self.timer <= 0:
            self._end_game()

    def _update_particles(self) -> None:
        for pt in self.particles:
            pt.x += pt.vx
            pt.y += pt.vy
            pt.vy += 0.05
            pt.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [f for f in self.floating_texts if f.life > 0]

    def _end_game(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score

    def _spawn_grab_particles(self, x: float, y: float, count: int, base_color: int, is_super: bool) -> None:
        for _ in range(count):
            c = self._rng.choice(COLORS) if is_super else base_color
            self.particles.append(
                Particle(
                    x=x, y=y,
                    vx=self._rng.uniform(-2.0, 2.0),
                    vy=self._rng.uniform(-2.0, 2.0),
                    life=self._rng.randint(15, 25),
                    color=c,
                )
            )

    def _spawn_mismatch_particles(self, x: float, y: float) -> None:
        for _ in range(self._rng.randint(3, 5)):
            self.particles.append(
                Particle(
                    x=x, y=y,
                    vx=self._rng.uniform(-1.0, 1.0),
                    vy=self._rng.uniform(-1.0, 1.0),
                    life=self._rng.randint(10, 15),
                    color=13,
                )
            )

    def _spawn_miss_particles(self, x: float, y: float) -> None:
        for _ in range(self._rng.randint(3, 5)):
            self.particles.append(
                Particle(
                    x=x, y=y,
                    vx=self._rng.uniform(-1.0, 1.0),
                    vy=self._rng.uniform(-1.0, 1.0),
                    life=self._rng.randint(10, 15),
                    color=13,
                )
            )

    def _spawn_super_particles(self, x: float, y: float) -> None:
        for _ in range(self._rng.randint(15, 20)):
            self.particles.append(
                Particle(
                    x=x, y=y,
                    vx=self._rng.uniform(-3.0, 3.0),
                    vy=self._rng.uniform(-3.0, 3.0),
                    life=self._rng.randint(20, 40),
                    color=self._rng.choice(COLORS),
                )
            )

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int, life: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=life, color=color))

    def _update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.phase = Phase.TITLE

    def _update_playing(self) -> None:
        if self._move_cooldown > 0:
            self._move_cooldown -= 1

        if self._move_cooldown == 0:
            dx, dy = 0, 0
            if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
                dx = -1
            if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
                dx = 1
            if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
                dy = -1
            if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
                dy = 1
            if dx != 0 or dy != 0:
                self.claw_col = max(0, min(COLS - 1, self.claw_col + dx))
                self.claw_row = max(0, min(ROWS - 1, self.claw_row + dy))
                self._move_cooldown = MOVE_COOLDOWN

        if pyxel.btnp(pyxel.KEY_SPACE) and self.super_timer == 0:
            self._grab_prize()

        if self.super_timer > 0:
            prize = self._get_prize_at(self.claw_col, self.claw_row)
            if prize is not None:
                self._grab_prize()

        self._update_super()
        self._update_color_cycle()
        self._spawn_prizes()
        self._update_heat()
        self._update_timer()
        self._update_particles()
        self._update_floating_texts()

    def _draw(self) -> None:
        pyxel.cls(1)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(105, 60, "CLAW SURGE", 7)
        pyxel.text(95, 80, "Arcade Crane Game", 13)
        pyxel.text(70, 120, "ARROWS/WASD: Move Claw", 6)
        pyxel.text(85, 134, "SPACE: Grab Prize", 6)
        pyxel.text(105, 148, "R: Restart", 6)
        pyxel.text(88, 180, "Press SPACE to start", 7)
        if self.best_score > 0:
            pyxel.text(105, 200, f"Best: {self.best_score}", 10)

    def _draw_game_over(self) -> None:
        pyxel.text(115, 70, "GAME OVER", 8)
        pyxel.text(110, 100, f"Score: {self.score}", 7)
        pyxel.text(100, 115, f"Max Combo: {self.max_combo}", 10)
        if self.best_score > 0:
            pyxel.text(105, 135, f"Best: {self.best_score}", 9)
        pyxel.text(95, 170, "Press R to retry", 13)

    def _draw_playing(self) -> None:
        self._draw_grid()
        self._draw_prizes()
        self._draw_claw()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_super_border()
        self._draw_hud()

    def _draw_grid(self) -> None:
        for row in range(ROWS + 1):
            py = GRID_Y + row * CELL
            pyxel.line(GRID_X, py, GRID_X + COLS * CELL, py, 13)
        for col in range(COLS + 1):
            px = GRID_X + col * CELL
            pyxel.line(px, GRID_Y, px, GRID_Y + ROWS * CELL, 13)

    def _draw_prizes(self) -> None:
        for p in self.prizes:
            px = GRID_X + p.x * CELL + 4
            py = GRID_Y + p.y * CELL + 4
            sz = CELL - 8
            pyxel.rect(px, py, sz, sz, p.color)
            pyxel.rectb(px, py, sz, sz, 7)

    def _draw_claw(self) -> None:
        cx, cy = self._claw_px()
        cx = int(cx)
        cy = int(cy)
        half = CELL // 2 - 2

        if self.super_timer > 0:
            rainbow_idx = (pyxel.frame_count // 4) % 4
            color = COLORS[rainbow_idx]
        else:
            color = self.claw_color

        pyxel.line(cx - half, cy, cx - half + 4, cy, color)
        pyxel.line(cx + half - 4, cy, cx + half, cy, color)
        pyxel.line(cx, cy - half, cx, cy - half + 4, color)
        pyxel.line(cx, cy + half - 4, cx, cy + half, color)

    def _draw_super_border(self) -> None:
        if self.super_timer > 0:
            rainbow_idx = (pyxel.frame_count // 4) % 4
            color = COLORS[rainbow_idx]
            pyxel.rectb(GRID_X - 2, GRID_Y - 2, COLS * CELL + 4, ROWS * CELL + 4, color)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", 7)
        pyxel.text(120, 4, f"COLOR: {COLOR_NAMES[COLORS.index(self.claw_color)]}", self.claw_color)

        combo_color = 7
        if self.combo >= 4:
            combo_color = 8
        elif self.combo >= 2:
            combo_color = 10
        pyxel.text(244, 4, f"COMBO: {self.combo}", combo_color)

        if self.super_timer > 0:
            seconds = self.super_timer // 30
            pyxel.text(130, 16, f"SUPER! {seconds}s", 10)

        seconds = max(0, self.timer // 30)
        timer_color = 8 if seconds <= 10 else 7
        pyxel.text(136, 228, f"TIME: {seconds}", timer_color)

        bar_x = 4
        bar_y = 16
        bar_w = 150
        bar_h = 6
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, 7)
        fill_w = int(self.heat / MAX_HEAT * (bar_w - 2))
        heat_col = 3
        if self.heat > 30:
            heat_col = 11
        if self.heat > 60:
            heat_col = 10
        if self.heat > 80:
            heat_col = 8
        pyxel.rect(bar_x + 1, bar_y + 1, fill_w, bar_h - 2, heat_col)
        pyxel.text(bar_x + bar_w + 4, bar_y - 1, "HEAT", 13)

    def _draw_particles(self) -> None:
        for pt in self.particles:
            alpha = pt.life / 25
            if alpha > 0.2:
                pyxel.pset(int(pt.x), int(pt.y), pt.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life > 3:
                pyxel.text(int(ft.x - len(ft.text) * 2), int(ft.y), ft.text, ft.color)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
