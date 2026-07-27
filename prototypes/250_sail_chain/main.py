from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
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


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class BuoyColor(Enum):
    RED = 0
    LIME = 1
    DARK_BLUE = 2
    YELLOW = 3


BUOY_COLOR_VALS: tuple[int, ...] = (8, 11, 5, 10)


@dataclass
class Buoy:
    x: float
    y: float
    color: BuoyColor
    vx: float = 0.0
    vy: float = 0.0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: float = 2.0


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int
    vy: float = -1.0


class Game:
    SCREEN_W = 320
    SCREEN_H = 240
    BOAT_SIZE = 10
    BUOY_RADIUS = 8
    COLLECT_RADIUS = 16
    BOAT_THRUST = 0.3
    BOAT_FRICTION = 0.95
    MAX_SPEED = 3.0
    MAX_HEAT = 100
    HEAT_DECAY = 0.02
    SUPER_DURATION = 300
    SUPER_SCORE_MULT = 3
    GAME_TIME = 60 * 30
    BASE_SCORE = 10
    MAX_BUOYS = 12
    MISMATCH_HEAT = 15
    MISS_HEAT = 5

    phase: Phase
    score: int
    combo: int
    max_combo: int
    timer: int
    heat: float
    boat_x: float
    boat_y: float
    boat_vx: float
    boat_vy: float
    boat_angle: float
    sail_color: BuoyColor
    wind_dir: float
    wind_strength: float
    wind_timer: int
    super_timer: int
    super_mode: bool
    buoys: list[Buoy]
    particles: list[Particle]
    floating_texts: list[FloatingText]
    ghost_path: list[tuple[float, float]]
    current_path: list[tuple[float, float]]
    best_score: int
    spawn_timer: int
    spawn_interval: int
    color_cycle_cooldown: int
    color_cycle_timer: int
    color_cycle_interval: int
    _rng: random.Random
    _path_record_timer: int
    _screen_shake: int
    _rainbow_frame: int

    def __init__(self) -> None:
        self._rng = random.Random()
        self.reset()

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.timer = self.GAME_TIME
        self.heat = 0.0
        self.boat_x = self.SCREEN_W / 2
        self.boat_y = self.SCREEN_H / 2
        self.boat_vx = 0.0
        self.boat_vy = 0.0
        self.boat_angle = -math.pi / 2
        self.sail_color = BuoyColor.RED
        self.wind_dir = self._rng.uniform(0, math.pi * 2)
        self.wind_strength = 0.5
        self.wind_timer = self._rng.randint(300, 600)
        self.super_timer = 0
        self.super_mode = False
        self.buoys = []
        self.particles = []
        self.floating_texts = []
        self.ghost_path = []
        self.current_path = []
        self.best_score = 0
        self.spawn_timer = 0
        self.spawn_interval = 90
        self.color_cycle_cooldown = 0
        self.color_cycle_timer = 0
        self.color_cycle_interval = 90
        self._path_record_timer = 0
        self._screen_shake = 0
        self._rainbow_frame = 0

        for _ in range(5):
            self._spawn_buoy()

    def _move_boat(self, dx: float, dy: float) -> None:
        if self.super_mode:
            dx *= 1.3
            dy *= 1.3
        self.boat_vx += dx * self.BOAT_THRUST
        self.boat_vy += dy * self.BOAT_THRUST

    def _cycle_color(self, direction: int) -> None:
        if self.super_mode:
            return
        if self.color_cycle_cooldown > 0:
            return
        colors = list(BuoyColor)
        idx = colors.index(self.sail_color)
        self.sail_color = colors[(idx + direction) % len(colors)]
        self.color_cycle_cooldown = 8

    def _update_physics(self) -> None:
        self.boat_vx *= self.BOAT_FRICTION
        self.boat_vy *= self.BOAT_FRICTION

        if not self.super_mode:
            self.boat_vx += math.cos(self.wind_dir) * self.wind_strength * 0.1
            self.boat_vy += math.sin(self.wind_dir) * self.wind_strength * 0.1

        speed = math.hypot(self.boat_vx, self.boat_vy)
        if speed > self.MAX_SPEED:
            ratio = self.MAX_SPEED / speed
            self.boat_vx *= ratio
            self.boat_vy *= ratio

        self.boat_x += self.boat_vx
        self.boat_y += self.boat_vy

        self.boat_x = max(0.0, min(float(self.SCREEN_W), self.boat_x))
        self.boat_y = max(0.0, min(float(self.SCREEN_H), self.boat_y))

        if speed > 0.1:
            self.boat_angle = math.atan2(self.boat_vy, self.boat_vx)

    def _check_collections(self) -> None:
        for buoy in list(self.buoys):
            dist = math.hypot(self.boat_x - buoy.x, self.boat_y - buoy.y)
            if dist <= self.COLLECT_RADIUS:
                self._collect_buoy(buoy)

    def _collect_buoy(self, buoy: Buoy) -> None:
        match = self.super_mode or buoy.color == self.sail_color

        if match:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            multiplier = self.SUPER_SCORE_MULT if self.super_mode else 1
            gained = self.BASE_SCORE * self.combo * multiplier
            self.score += gained

            if self.super_mode:
                self._spawn_particles(buoy.x, buoy.y, 15, 20, 3.0, random_color=True)
                self.floating_texts.append(
                    FloatingText(self.boat_x, self.boat_y - 10, f"+{gained}", 30, YELLOW)
                )
            else:
                col_val = BUOY_COLOR_VALS[buoy.color.value]
                self._spawn_particles(buoy.x, buoy.y, 8, 12, 2.0, color=col_val)
                self.floating_texts.append(
                    FloatingText(buoy.x, buoy.y - 8, f"+{gained}", 30, WHITE)
                )

            if self.combo >= 2:
                self.floating_texts.append(
                    FloatingText(self.boat_x, self.boat_y - 16, f"COMBO x{self.combo}", 45, YELLOW)
                )

            if self.combo >= 4 and not self.super_mode:
                self._activate_super()

        else:
            self.combo = 0
            self.heat = min(float(self.MAX_HEAT), self.heat + self.MISMATCH_HEAT)
            self._spawn_particles(buoy.x, buoy.y, 4, 6, 2.0, color=GRAY)
            self.floating_texts.append(
                FloatingText(self.boat_x, self.boat_y - 10, "WRONG!", 30, RED)
            )
            self._screen_shake = 8

        if buoy in self.buoys:
            self.buoys.remove(buoy)

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = self.SUPER_DURATION
        self.floating_texts.append(
            FloatingText(self.boat_x, self.boat_y - 24, "SUPER SAIL!", 60, YELLOW)
        )

    def _spawn_buoy(self) -> None:
        edge = self._rng.randint(0, 3)
        if edge == 0:
            x = float(self._rng.randint(0, self.SCREEN_W))
            y = -10.0
        elif edge == 1:
            x = float(self.SCREEN_W + 10)
            y = float(self._rng.randint(0, self.SCREEN_H))
        elif edge == 2:
            x = float(self._rng.randint(0, self.SCREEN_W))
            y = float(self.SCREEN_H + 10)
        else:
            x = -10.0
            y = float(self._rng.randint(0, self.SCREEN_H))

        color = BuoyColor(self._rng.randint(0, 3))
        vx = self._rng.uniform(-0.3, 0.3)
        vy = self._rng.uniform(-0.3, 0.3)
        self.buoys.append(Buoy(x, y, color, vx, vy))

    def _update_buoys(self) -> None:
        for buoy in list(self.buoys):
            buoy.x += buoy.vx
            buoy.y += buoy.vy
            margin = 30.0
            if (
                buoy.x < -margin
                or buoy.x > self.SCREEN_W + margin
                or buoy.y < -margin
                or buoy.y > self.SCREEN_H + margin
            ):
                self.heat = min(float(self.MAX_HEAT), self.heat + self.MISS_HEAT)
                self._spawn_particles(buoy.x, buoy.y, 2, 3, 2.0, color=GRAY)
                self.buoys.remove(buoy)

        while len(self.buoys) < self.MAX_BUOYS:
            self._spawn_buoy()

    def _update_wind(self) -> None:
        self.wind_timer -= 1
        if self.wind_timer <= 0:
            self.wind_dir = self._rng.uniform(0, math.pi * 2)
            t = min(1.0, (self.GAME_TIME - self.timer) / self.GAME_TIME)
            self.wind_strength = 0.5 + t * 1.5
            self.wind_timer = self._rng.randint(300, 600)

    def _update_timers(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self._on_game_over()
            return

        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self._spawn_buoy()
            t = min(1.0, (self.GAME_TIME - self.timer) / self.GAME_TIME)
            self.spawn_interval = max(30, 90 - int(t * 60))
            self.spawn_timer = self._rng.randint(
                max(20, self.spawn_interval - 15),
                self.spawn_interval + 15,
            )

        self.color_cycle_timer -= 1
        if self.color_cycle_timer <= 0 and not self.super_mode:
            self._cycle_color(1)
            t = min(1.0, (self.GAME_TIME - self.timer) / self.GAME_TIME)
            self.color_cycle_interval = max(40, 90 - int(t * 50))
            self.color_cycle_timer = self.color_cycle_interval

        if self.color_cycle_cooldown > 0:
            self.color_cycle_cooldown -= 1

        if self._screen_shake > 0:
            self._screen_shake -= 1

        self._rainbow_frame += 1

    def _update_heat(self) -> None:
        if self.heat >= self.MAX_HEAT:
            self.heat = float(self.MAX_HEAT)
            if self.phase == Phase.PLAYING:
                self._on_game_over()
            return
        if self.heat > 0 and not self.super_mode:
            self.heat = max(0.0, self.heat - self.HEAT_DECAY)

    def _on_game_over(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score
            self.ghost_path = list(self.current_path)

    def _update_particles(self) -> None:
        for p in list(self.particles):
            p.vy += 0.05
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in list(self.floating_texts):
            ft.y += ft.vy
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    def _record_path(self) -> None:
        self._path_record_timer -= 1
        if self._path_record_timer <= 0:
            self._path_record_timer = 15
            self.current_path.append((self.boat_x, self.boat_y))

    def _spawn_particles(
        self,
        x: float,
        y: float,
        min_count: int,
        max_count: int,
        size: float,
        color: int | None = None,
        random_color: bool = False,
    ) -> None:
        count = self._rng.randint(min_count, max_count)
        for _ in range(count):
            vx = self._rng.uniform(-2.0, 2.0)
            vy = self._rng.uniform(-2.0, 2.0)
            if random_color:
                c = self._rng.choice(BUOY_COLOR_VALS)
            elif color is not None:
                c = color
            else:
                c = WHITE
            self.particles.append(Particle(x, y, vx, vy, self._rng.randint(10, 25), c, size))

    def update(self) -> None:
        if self.phase != Phase.PLAYING:
            return

        self._update_timers()
        if self.phase != Phase.PLAYING:
            return

        self._update_wind()
        self._update_physics()
        self._update_buoys()
        self._check_collections()
        self._update_heat()
        self._update_particles()
        self._update_floating_texts()
        self._record_path()

    def draw(self) -> None:
        pyxel.cls(DARK_BLUE)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(self.SCREEN_W // 2 - 40, 40, "SAIL CHAIN", CYAN)
        pyxel.text(self.SCREEN_W // 2 - 70, 70, "Arrow keys: sail", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 70, 80, "UP/DOWN: change color", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 70, 90, "Match sail color to buoys", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 70, 100, "COMBO x4 = SUPER SAIL!", WHITE)
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(self.SCREEN_W // 2 - 40, 130, "PRESS SPACE", YELLOW)

        pyxel.text(self.SCREEN_W // 2 - 60, 180, "Best Score: " + str(self.best_score), CYAN)

    def _draw_playing(self) -> None:
        self._draw_wind_lines()

        if self._screen_shake > 0:
            shake_x = self._rng.randint(-2, 2)
            shake_y = self._rng.randint(-2, 2)
            pyxel.camera(shake_x, shake_y)

        self._draw_ghost_path()
        self._draw_buoys()
        self._draw_boat()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()
        self._draw_super_border()

        if self._screen_shake > 0:
            pyxel.camera(0, 0)

    def _draw_wind_lines(self) -> None:
        spacing = 60
        length = self.wind_strength * 15
        for sx in range(0, self.SCREEN_W + spacing, spacing):
            for sy in range(0, self.SCREEN_H + spacing, spacing):
                ex = sx + math.cos(self.wind_dir) * length
                ey = sy + math.sin(self.wind_dir) * length
                pyxel.line(sx, sy, ex, ey, LIGHT_BLUE)

    def _draw_ghost_path(self) -> None:
        for px, py in self.ghost_path:
            pyxel.circ(int(px), int(py), 2, CYAN)

    def _draw_buoys(self) -> None:
        for buoy in self.buoys:
            col = BUOY_COLOR_VALS[buoy.color.value]
            pyxel.circ(int(buoy.x), int(buoy.y), self.BUOY_RADIUS, col)
            pyxel.circb(int(buoy.x), int(buoy.y), self.BUOY_RADIUS, WHITE)

    def _draw_boat(self) -> None:
        angle = self.boat_angle
        bx = self.boat_x
        by = self.boat_y
        size = self.BOAT_SIZE

        tip_x = bx + math.cos(angle) * size
        tip_y = by + math.sin(angle) * size
        left_x = bx + math.cos(angle + 2.5) * size * 0.7
        left_y = by + math.sin(angle + 2.5) * size * 0.7
        right_x = bx + math.cos(angle - 2.5) * size * 0.7
        right_y = by + math.sin(angle - 2.5) * size * 0.7

        if self.super_mode:
            rainbow_idx = (self._rainbow_frame // 10) % len(BUOY_COLOR_VALS)
            boat_color = BUOY_COLOR_VALS[rainbow_idx]
        else:
            boat_color = BUOY_COLOR_VALS[self.sail_color.value]

        pyxel.tri(tip_x, tip_y, left_x, left_y, right_x, right_y, boat_color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 25.0
            if alpha > 1.0:
                alpha = 1.0
            col = p.color
            if alpha < 0.3:
                col = DARK_BLUE
            pyxel.circ(int(p.x), int(p.y), int(p.size), col)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 60.0
            if alpha > 1.0:
                alpha = 1.0
            col = ft.color
            if alpha < 0.3:
                col = DARK_BLUE
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, col)

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, self.SCREEN_W, 18, DARK_BLUE)
        pyxel.line(0, 18, self.SCREEN_W, 18, LIGHT_BLUE)

        pyxel.text(4, 4, f"SCORE:{self.score}", WHITE)
        pyxel.text(70, 4, f"COMBO:{self.combo}", WHITE)
        color_name = self.sail_color.name if not self.super_mode else "RAINBOW"
        pyxel.text(120, 4, f"SAIL:{color_name}", WHITE)

        seconds = self.timer // 30
        pyxel.text(175, 4, f"TIME:{seconds:02d}s", WHITE)

        if self.super_mode:
            super_sec = self.super_timer // 30
            pyxel.text(230, 4, f"SUPER:{super_sec:02d}", YELLOW)

        bar_x = 5
        bar_y = 20
        bar_w = 100
        bar_h = 6
        pyxel.rect(bar_x, bar_y, bar_w + 2, bar_h + 2, WHITE)
        fill_w = int(bar_w * self.heat / self.MAX_HEAT)
        if self.heat < 33:
            bar_col = GREEN
        elif self.heat < 66:
            bar_col = YELLOW
        else:
            bar_col = RED
        pyxel.rect(bar_x + 1, bar_y + 1, fill_w, bar_h, bar_col)
        pyxel.text(bar_x, bar_y + 7, "HEAT", WHITE)

    def _draw_super_border(self) -> None:
        if not self.super_mode:
            return
        rainbow_idx = (self._rainbow_frame // 10) % len(BUOY_COLOR_VALS)
        col = BUOY_COLOR_VALS[rainbow_idx]
        pyxel.rectb(0, 0, self.SCREEN_W, self.SCREEN_H, col)
        pyxel.rectb(1, 1, self.SCREEN_W - 2, self.SCREEN_H - 2, col)

    def _draw_game_over(self) -> None:
        pyxel.text(self.SCREEN_W // 2 - 30, 60, "GAME OVER", RED)
        pyxel.text(self.SCREEN_W // 2 - 40, 80, f"Score: {self.score}", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 40, 90, f"Best: {self.best_score}", CYAN)
        pyxel.text(self.SCREEN_W // 2 - 40, 100, f"Max Combo: {self.max_combo}", YELLOW)

        if self.score >= self.best_score and self.score > 0:
            pyxel.text(self.SCREEN_W // 2 - 30, 120, "NEW BEST!", YELLOW)

        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(self.SCREEN_W // 2 - 40, 150, "PRESS SPACE", WHITE)


class App:
    def __init__(self) -> None:
        pyxel.init(Game.SCREEN_W, Game.SCREEN_H, title="SAIL CHAIN")
        self.game = Game()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        game = self.game

        if game.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                game.reset()
                game.phase = Phase.PLAYING
                game.timer = Game.GAME_TIME
            return

        if game.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                game.reset()
                game.phase = Phase.TITLE
            return

        if game.phase == Phase.PLAYING:
            if pyxel.btn(pyxel.KEY_LEFT):
                game.boat_angle -= 0.05
            if pyxel.btn(pyxel.KEY_RIGHT):
                game.boat_angle += 0.05
            if pyxel.btn(pyxel.KEY_UP):
                game._move_boat(math.cos(game.boat_angle), math.sin(game.boat_angle))

            if pyxel.btnp(pyxel.KEY_DOWN):
                game._cycle_color(1)
            elif pyxel.btnp(pyxel.KEY_Z):
                game._cycle_color(-1)

            game.update()

    def draw(self) -> None:
        self.game.draw()


def main() -> None:
    App()


if __name__ == "__main__":
    main()
