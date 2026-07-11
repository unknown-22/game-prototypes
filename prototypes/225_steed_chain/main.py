from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel

SCREEN_W = 320
SCREEN_H = 240
GROUND_Y = 200
HORSE_X = 80
HORSE_W = 32
HORSE_H = 24
HURDLE_SPAWN_INTERVAL_INITIAL = 120
HURDLE_SPAWN_INTERVAL_MIN = 40
COLOR_NAMES: list[str] = ["RED", "GREEN", "DARK_BLUE", "YELLOW"]
COLOR_VALS: list[int] = [8, 3, 5, 10]
SUPER_DURATION = 300
MAX_HEAT = 100
GAME_DURATION = 60 * 60
JUMP_VELOCITY = -8.0
GRAVITY = 0.5
STUMBLE_COOLDOWN = 30
MIN_SCROLL_SPEED = 2.0
MAX_SCROLL_SPEED = 5.0
COLOR_CYCLE_INTERVAL = 90


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Hurdle:
    x: float
    y: float
    color: int
    height: int = 30
    width: int = 20
    cleared: bool = False


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
    _best_run: ClassVar[list[tuple[float, float]]] = []
    _best_score: ClassVar[int] = 0
    _best_max_combo: ClassVar[int] = 0

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Steed Chain")
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.scroll_speed: float = MIN_SCROLL_SPEED
        self.hurdles: list[Hurdle] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.horse_color: int = 0
        self.horse_y: float = float(GROUND_Y)
        self.horse_vy: float = 0.0
        self.is_jumping: bool = False
        self.jump_frame: int = 0
        self.stumble_frame: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.total_hurdles_cleared: int = 0
        self.heat: int = 0
        self.super_timer: int = 0
        self.timer: int = GAME_DURATION
        self.spawn_countdown: int = HURDLE_SPAWN_INTERVAL_INITIAL
        self.color_timer: int = 0
        self._run_positions: list[tuple[float, float]] = []

    def _is_super(self) -> bool:
        return self.super_timer > 0

    def _elapsed(self) -> int:
        return GAME_DURATION - self.timer

    def _progress_ratio(self) -> float:
        return min(1.0, self._elapsed() / GAME_DURATION)

    def _current_spawn_interval(self) -> int:
        return int(
            HURDLE_SPAWN_INTERVAL_INITIAL
            - (HURDLE_SPAWN_INTERVAL_INITIAL - HURDLE_SPAWN_INTERVAL_MIN)
            * self._progress_ratio()
        )

    # ---- update ----

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        if self.timer > 0:
            self.timer -= 1
        if self.timer <= 0:
            self._end_game()
            return
        if self.heat >= MAX_HEAT:
            self._end_game()
            return

        progress = self._progress_ratio()
        self.scroll_speed = MIN_SCROLL_SPEED + (MAX_SCROLL_SPEED - MIN_SCROLL_SPEED) * progress

        if self.stumble_frame > 0:
            self.stumble_frame -= 1

        if self.super_timer > 0:
            self.super_timer -= 1

        self.color_timer += 1
        if self.color_timer >= COLOR_CYCLE_INTERVAL:
            self.color_timer = 0
            self.horse_color = (self.horse_color + 1) % 4

        self._handle_input()
        self._update_horse()
        self._update_hurdles()
        self._spawn_hurdles()
        self._check_collisions()
        self._update_particles()
        self._update_floating_texts()

        if self._is_super() and pyxel.frame_count % 2 == 0:
            self._spawn_particles(
                HORSE_X + HORSE_W // 2,
                self.horse_y - HORSE_H // 2,
                self._rng.choice(COLOR_VALS),
                count=1,
            )

        self._run_positions.append((self.horse_y, 1.0 if self._is_super() else 0.0))

    def _end_game(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > Game._best_score:
            Game._best_score = self.score
            Game._best_max_combo = self.max_combo
            Game._best_run = list(self._run_positions)

    def _handle_input(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if not self.is_jumping and self.stumble_frame == 0:
                self.is_jumping = True
                self.jump_frame = 0
                self.horse_vy = JUMP_VELOCITY

    def _update_horse(self) -> None:
        if not self.is_jumping:
            return
        self.horse_vy += GRAVITY
        self.horse_y += self.horse_vy
        self.jump_frame += 1
        if self.horse_y >= GROUND_Y:
            self.horse_y = float(GROUND_Y)
            self.is_jumping = False
            self.horse_vy = 0.0

    def _spawn_hurdles(self) -> None:
        self.spawn_countdown -= 1
        if self.spawn_countdown <= 0:
            self.spawn_countdown = self._current_spawn_interval()
            self._spawn_hurdle()

    def _spawn_hurdle(self) -> None:
        color_idx = self._rng.randint(0, 3)
        height = self._rng.randint(20, 50)
        self.hurdles.append(
            Hurdle(
                x=float(SCREEN_W + 20),
                y=float(GROUND_Y),
                color=color_idx,
                height=height,
            )
        )

    def _update_hurdles(self) -> None:
        for h in self.hurdles:
            h.x -= self.scroll_speed
        self.hurdles = [h for h in self.hurdles if h.x > -30]

    def _check_collisions(self) -> None:
        for hurdle in self.hurdles:
            if hurdle.cleared:
                continue
            if not self._hurdle_overlaps_horse(hurdle):
                continue

            hurdle_top_y = GROUND_Y - hurdle.height

            if self._is_super():
                self._resolve_hurdle(hurdle, matched=True)
            elif self.is_jumping and self.horse_y < hurdle_top_y:
                matched = self.horse_color == hurdle.color
                self._resolve_hurdle(hurdle, matched=matched)
            else:
                self._crash(hurdle)

    def _hurdle_overlaps_horse(self, hurdle: Hurdle) -> bool:
        return hurdle.x + hurdle.width > HORSE_X and hurdle.x < HORSE_X + HORSE_W

    def _resolve_hurdle(self, hurdle: Hurdle, *, matched: bool) -> None:
        hurdle.cleared = True
        self.total_hurdles_cleared += 1
        hurdle_top_y = GROUND_Y - hurdle.height

        if self._is_super():
            self.combo += 1
            bonus = 10 * self.combo * 3
            self.score += bonus
            self.max_combo = max(self.max_combo, self.combo)
            self._spawn_particles(hurdle.x + hurdle.width // 2, hurdle_top_y, 10, count=8)
            c = 10 if pyxel.frame_count % 4 < 2 else 8
            self._spawn_floating_text(hurdle.x, hurdle_top_y, f"+{bonus}", c)
        elif matched:
            self.combo += 1
            bonus = 10 * self.combo
            self.score += bonus
            self.max_combo = max(self.max_combo, self.combo)
            self._spawn_particles(
                hurdle.x + hurdle.width // 2, hurdle_top_y, hurdle.color, count=10
            )
            self._spawn_floating_text(hurdle.x, hurdle_top_y, f"+{bonus}", COLOR_VALS[hurdle.color])
            if self.combo >= 4 and not self._is_super() and self.super_timer == 0:
                self.super_timer = SUPER_DURATION
                self._spawn_floating_text(
                    SCREEN_W // 2 - 40, SCREEN_H // 2 - 10, "SUPER GALLOP!", 10, life=60
                )
        else:
            prev_combo = self.combo
            self.combo = 0
            self.heat = min(MAX_HEAT, self.heat + 15)
            self.stumble_frame = STUMBLE_COOLDOWN
            self._spawn_particles(hurdle.x + hurdle.width // 2, hurdle_top_y, 4, count=10)
            if prev_combo > 1:
                self._spawn_floating_text(
                    HORSE_X, self.horse_y - 30, f"COMBO x{prev_combo}!", 10, life=40
                )

    def _crash(self, hurdle: Hurdle) -> None:
        hurdle.cleared = True
        prev_combo = self.combo
        self.combo = 0
        self.heat = min(MAX_HEAT, self.heat + 25)
        self.stumble_frame = STUMBLE_COOLDOWN
        self._spawn_particles(HORSE_X + HORSE_W // 2, GROUND_Y, 4, count=10)
        if prev_combo > 1:
            self._spawn_floating_text(
                HORSE_X, self.horse_y - 30, f"COMBO x{prev_combo}!", 10, life=40
            )
        if self.is_jumping:
            self.is_jumping = False
            self.horse_y = float(GROUND_Y)
            self.horse_vy = 0.0

    # ---- particles / floating text ----

    def _spawn_particles(
        self, x: float, y: float, color_hint: int, *, count: int = 10
    ) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-2, 2)
            vy = self._rng.uniform(-4, -0.5)
            life = self._rng.randint(12, 22)
            self.particles.append(
                Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color_hint)
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.15
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int, *, life: int = 25
    ) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=life, color=color)
        )

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.8
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ---- draw ----

    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.cls(1)
        t = pyxel.frame_count
        pyxel.text(SCREEN_W // 2 - 55, 50, "STEED CHAIN", 7)
        pyxel.text(SCREEN_W // 2 - 50, 80, "Press SPACE to Start", 7 if t % 60 < 40 else 5)
        pyxel.text(SCREEN_W // 2 - 75, 110, "SPACE / Click : Jump over hurdles", 7)
        pyxel.text(SCREEN_W // 2 - 75, 125, "Match horse color to build COMBO", 7)
        pyxel.text(SCREEN_W // 2 - 75, 140, "Combo x4 = SUPER GALLOP", 10)
        pyxel.text(SCREEN_W // 2 - 75, 155, "Wrong color = HEAT + stumble", 8)
        pyxel.text(SCREEN_W // 2 - 75, 170, "Survive 60s / Keep HEAT under 100", 7)
        pyxel.text(SCREEN_W // 2 - 65, 200, "Click or SPACE to start", 13)

    def _draw_playing(self) -> None:
        pyxel.cls(6)
        pyxel.rect(0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y, 4)

        self._draw_ghost()
        self._draw_hurdles()
        self._draw_horse()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_ghost(self) -> None:
        if not Game._best_run:
            return
        idx = len(self._run_positions) - 1
        if idx < 0 or idx >= len(Game._best_run):
            return
        gy, _was_super = Game._best_run[idx]
        gx = HORSE_X - 2
        pyxel.rectb(gx, int(gy) - HORSE_H, HORSE_W, HORSE_H, 13)

    def _draw_hurdles(self) -> None:
        for h in self.hurdles:
            top_y = int(GROUND_Y - h.height)
            pyxel.rect(int(h.x), top_y, h.width, h.height, COLOR_VALS[h.color])
            pyxel.rectb(int(h.x), top_y, h.width, h.height, 7)

    def _draw_horse(self) -> None:
        hx = HORSE_X
        hy = int(self.horse_y)

        if self._is_super():
            body_color = COLOR_VALS[(pyxel.frame_count // 8) % 4]
            glow_color = COLOR_VALS[(pyxel.frame_count // 8 + 2) % 4]
        else:
            body_color = COLOR_VALS[self.horse_color]
            glow_color = body_color

        if self.stumble_frame > 0 and pyxel.frame_count % 4 < 2:
            hy += 3

        pyxel.rect(hx, hy - HORSE_H, HORSE_W, HORSE_H, body_color)

        pyxel.rect(hx + HORSE_W - 2, hy - HORSE_H - 6, 8, 8, body_color)
        pyxel.circ(hx + HORSE_W + 2, hy - HORSE_H - 6, 2, 0)

        pyxel.tri(
            hx + HORSE_W + 4,
            hy - HORSE_H - 4,
            hx + HORSE_W + 14,
            hy - HORSE_H + 2,
            hx + HORSE_W + 4,
            hy - HORSE_H + 4,
            body_color,
        )

        pyxel.line(
            hx - 2,
            hy - HORSE_H + 4,
            hx - 10,
            hy - HORSE_H + 2,
            body_color,
        )
        pyxel.line(
            hx - 2,
            hy - 4,
            hx - 10,
            hy - 6,
            body_color,
        )

        if self.stumble_frame > 0:
            pyxel.circ(hx + HORSE_W // 3, hy - HORSE_H + 6, 3, 7)
            pyxel.circ(hx + 2 * HORSE_W // 3, hy - HORSE_H + 6, 3, 7)

        if self._is_super():
            pyxel.rectb(hx - 2, hy - HORSE_H - 2, HORSE_W + 4, HORSE_H + 4, glow_color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            if p.life > 4 or pyxel.frame_count % 2 == 0:
                pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"Score: {self.score}", 7)
        pyxel.text(4, 14, f"Combo: x{self.combo}", 10 if self.combo >= 4 else 7)

        color_text = f"Color: {COLOR_NAMES[self.horse_color]}"
        pyxel.text(4, 26, color_text, COLOR_VALS[self.horse_color])

        pyxel.text(SCREEN_W - 72, 4, f"Time: {max(0, self.timer) // 60}s", 7)
        if self._is_super():
            pyxel.text(SCREEN_W - 80, 16, f"SUPER: {self.super_timer // 60 + 1}s", 10)

        pyxel.text(4, SCREEN_H - 30, "HEAT", 7)
        bar_w = 100
        pyxel.rect(4, SCREEN_H - 20, bar_w, 8, 5)
        fill_w = min(bar_w, int(bar_w * self.heat / MAX_HEAT))
        if self.heat >= 70:
            hc = 8
        elif self.heat >= 40:
            hc = 9
        else:
            hc = 3
        if fill_w > 0:
            pyxel.rect(4, SCREEN_H - 20, fill_w, 8, hc)
        pyxel.rectb(4, SCREEN_H - 20, bar_w, 8, 7)

        pyxel.text(4, SCREEN_H - 10, f"Best: {Game._best_score}", 13)

    def _draw_game_over(self) -> None:
        pyxel.cls(1)
        t = pyxel.frame_count
        pyxel.text(SCREEN_W // 2 - 40, 30, "GAME OVER", 8)
        pyxel.text(SCREEN_W // 2 - 55, 55, f"Score: {self.score}", 7)
        pyxel.text(SCREEN_W // 2 - 55, 70, f"Max Combo: {self.max_combo}", 7)
        pyxel.text(SCREEN_W // 2 - 55, 85, f"Hurdles Cleared: {self.total_hurdles_cleared}", 7)
        pyxel.text(SCREEN_W // 2 - 55, 110, f"Best Score: {Game._best_score}", 10)
        pyxel.text(SCREEN_W // 2 - 55, 125, f"Best Max Combo: {Game._best_max_combo}", 10)
        msg = "SPACE or Click to Retry"
        pyxel.text(SCREEN_W // 2 - len(msg) * 2, 170, msg, 7 if t % 60 < 40 else 5)

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.PLAYING


if __name__ == "__main__":
    Game()
