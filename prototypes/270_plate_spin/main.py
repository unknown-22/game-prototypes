from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

WIDE = 320
HIGH = 240
TARGET_FPS = 30
PLATE_XS: list[int] = [60, 120, 200, 260]
PLATE_Y = 120
PLATE_RADIUS = 22
STICK_Y = 150
STICK_BOTTOM = 220
STICK_WIDTH = 4

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

PLATE_COLORS: tuple[int, int, int, int] = (RED, LIME, DARK_BLUE, YELLOW)

WOBBLE_DECAY = 0.04
WOBBLE_RECOVERY = 100.0
WOBBLE_DANGER = 20.0
CA_DECAY_MULTIPLIER = 1.5
SUPER_DURATION = 300
SUPER_AUTO_INTERVAL = 30
RESPAWN_FRAMES = 60
FLOAT_TEXT_LIFE = 30
FLOAT_TEXT_SPEED = 0.5
PARTICLE_GRAVITY = 0.1

TIMER_MAX = 1800
HEAT_MAX = 100.0


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Plate:
    x: int
    color: int
    wobble: float = WOBBLE_RECOVERY
    fallen: bool = False
    respawn_timer: int = 0


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
    def __new__(cls) -> Game:
        instance = super().__new__(cls)
        instance.phase = Phase.TITLE
        instance.score = 0
        instance.best_score = 0
        instance.combo = 0
        instance.max_combo = 0
        instance.heat = 0.0
        instance.timer = TIMER_MAX
        instance.super_timer = 0
        instance.last_color = -1
        instance._rng = random.Random()
        instance.plates: list[Plate] = []
        instance.particles: list[Particle] = []
        instance.floating_texts: list[FloatingText] = []
        instance._auto_spin_counter = 0
        return instance

    def __init__(self) -> None:
        pyxel.init(WIDE, HIGH, title="PLATE SURGE", fps=TARGET_FPS, display_scale=2)
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = TIMER_MAX
        self.super_timer = 0
        self.last_color = -1
        self._rng = random.Random()
        self.plates = [self._spawn_plate(i) for i in range(4)]
        self.particles = []
        self.floating_texts = []
        self._auto_spin_counter = 0

    def _spawn_plate(self, index: int) -> Plate:
        color = self._rng.choice(PLATE_COLORS)
        return Plate(x=PLATE_XS[index], color=color)

    def _spin_plate(self, index: int) -> tuple[int, bool]:
        if index < 0 or index >= len(self.plates):
            return 0, False
        plate = self.plates[index]
        if plate.fallen:
            return 0, False

        in_super = self.super_timer > 0
        was_match: bool
        if in_super:
            was_match = True
        else:
            if self.last_color == -1:
                was_match = True
            else:
                was_match = plate.color == self.last_color

        if was_match:
            self.combo += 1
            multiplier = 3 if in_super else 1
            score_gained = 10 * self.combo * multiplier
        else:
            score_gained = 0
            self.heat = min(self.heat + 15, HEAT_MAX)
            self._add_floating_text(plate.x, PLATE_Y - 30, "WRONG!", ORANGE)

        self.last_color = plate.color if was_match else -1
        plate.wobble = WOBBLE_RECOVERY

        if self.combo > self.max_combo:
            self.max_combo = self.combo

        return score_gained, was_match

    def _update_wobble(self) -> None:
        for i, plate in enumerate(self.plates):
            if plate.fallen:
                continue
            decay = WOBBLE_DECAY
            if i > 0:
                left = self.plates[i - 1]
                if not left.fallen and left.wobble < WOBBLE_DANGER:
                    decay *= CA_DECAY_MULTIPLIER
            if i < len(self.plates) - 1:
                right = self.plates[i + 1]
                if not right.fallen and right.wobble < WOBBLE_DANGER:
                    decay *= CA_DECAY_MULTIPLIER
            plate.wobble = max(plate.wobble - decay, 0)

    def _check_fallen(self) -> list[int]:
        fallen_indices: list[int] = []
        for i, plate in enumerate(self.plates):
            if plate.wobble <= 0 and not plate.fallen:
                plate.fallen = True
                plate.respawn_timer = RESPAWN_FRAMES
                self.heat = min(self.heat + 25, HEAT_MAX)
                self.combo = 0
                self.last_color = -1
                fallen_indices.append(i)
        return fallen_indices

    def _respawn_fallen(self) -> None:
        for i, plate in enumerate(self.plates):
            if plate.fallen:
                plate.respawn_timer -= 1
                if plate.respawn_timer <= 0:
                    plate.fallen = False
                    plate.wobble = WOBBLE_RECOVERY
                    plate.color = self._rng.choice(PLATE_COLORS)

    def _update_super(self) -> None:
        if self.super_timer <= 0:
            return
        self.super_timer -= 1
        self._auto_spin_counter += 1
        if self._auto_spin_counter >= SUPER_AUTO_INTERVAL:
            self._auto_spin_counter = 0
            for i, plate in enumerate(self.plates):
                if not plate.fallen:
                    plate.wobble = WOBBLE_RECOVERY
                    self._add_spin_particles(i, True)

    def _update_heat(self) -> None:
        self.heat = max(self.heat - 0.02, 0)

    def _update_timer(self) -> None:
        self.timer = max(self.timer - 1, 0)

    def _add_spin_particles(self, index: int, was_match: bool) -> None:
        plate = self.plates[index]
        px = float(plate.x)
        py = float(PLATE_Y)
        if was_match:
            count = 12 if self.super_timer > 0 else 6
            color = plate.color
        else:
            count = 3
            color = GRAY
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1, 3)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 1.5
            life = self._rng.randint(15, 25)
            self.particles.append(Particle(px, py, vx, vy, life, color))

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x, y, text, FLOAT_TEXT_LIFE, color))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += PARTICLE_GRAVITY
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= FLOAT_TEXT_SPEED
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if _btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE):
                self.phase = Phase.PLAYING
                self.reset()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            if _btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE):
                self.phase = Phase.TITLE

    def _update_playing(self) -> None:
        self._update_timer()
        # Check game-over conditions BEFORE mutating updates (decay etc.)
        all_fallen = all(p.fallen for p in self.plates)
        if self.timer <= 0 or self.heat >= HEAT_MAX or all_fallen:
            self.best_score = max(self.best_score, self.score)
            self.phase = Phase.GAME_OVER
            return
        self._update_heat()
        self._update_super()
        self._update_wobble()
        self._check_fallen()
        self._respawn_fallen()
        self._update_particles()
        self._update_floating_texts()

        if _btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            for i, plate in enumerate(self.plates):
                if plate.fallen:
                    continue
                dx = mx - plate.x
                dy = my - PLATE_Y
                if dx * dx + dy * dy < PLATE_RADIUS * PLATE_RADIUS:
                    score_gained, was_match = self._spin_plate(i)
                    self.score += score_gained
                    self._add_spin_particles(i, was_match)
                    if was_match and self.combo >= 2:
                        self._add_floating_text(
                            plate.x, PLATE_Y - 20, f"+{score_gained}", plate.color
                        )
                        if self.combo >= 4:
                            self._add_floating_text(
                                plate.x, PLATE_Y - 50, f"COMBO x{self.combo}!", LIME
                            )
                    if self.combo >= 4 and self.super_timer <= 0:
                        self.super_timer = SUPER_DURATION
                        self._auto_spin_counter = 0
                        self._add_floating_text(WIDE // 2, HIGH // 2, "SUPER SPIN!", PINK)
                        for j in range(len(self.plates)):
                            self._add_spin_particles(j, True)
                    break

        all_fallen = all(p.fallen for p in self.plates)
        if self.timer <= 0 or self.heat >= HEAT_MAX or all_fallen:
            self.best_score = max(self.best_score, self.score)
            self.phase = Phase.GAME_OVER

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(WIDE // 2 - 45, 50, "PLATE SURGE", WHITE)
        pyxel.text(WIDE // 2 - 60, 80, "Keep the plates spinning!", WHITE)
        pyxel.text(WIDE // 2 - 55, 100, "Click same-color plates", WHITE)
        pyxel.text(WIDE // 2 - 50, 115, "for COMBO chains!", WHITE)
        pyxel.text(WIDE // 2 - 50, 135, "SUPER SPIN at COMBO>=4", PINK)
        pyxel.text(WIDE // 2 - 60, 170, f"BEST SCORE: {self.best_score}", YELLOW)
        pyxel.text(WIDE // 2 - 55, 210, "CLICK or SPACE to start", LIME)

    def _draw_playing(self) -> None:
        frame = pyxel.frame_count

        for i, plate in enumerate(self.plates):
            sx = plate.x
            pyxel.rect(
                sx - STICK_WIDTH // 2,
                STICK_Y,
                STICK_WIDTH,
                STICK_BOTTOM - STICK_Y,
                GRAY,
            )

        for i, plate in enumerate(self.plates):
            sx = plate.x
            if plate.fallen:
                pyxel.circb(sx, STICK_BOTTOM + 10, PLATE_RADIUS, GRAY)
                pyxel.circ(sx, STICK_BOTTOM + 10, PLATE_RADIUS - 2, GRAY)
            else:
                wobble_offset = math.sin(frame * 0.3) * (100 - plate.wobble) * 0.02
                py_val = PLATE_Y + wobble_offset

                border_color = plate.color
                fill_color = plate.color
                if self.super_timer > 0:
                    rainbow_index = (frame // 10 + i) % len(PLATE_COLORS)
                    border_color = PLATE_COLORS[rainbow_index]
                    fill_color = PLATE_COLORS[rainbow_index]

                pyxel.circb(sx, py_val, PLATE_RADIUS, border_color)
                pyxel.circ(sx, py_val, PLATE_RADIUS - 2, fill_color)

                wobble_percent = plate.wobble / WOBBLE_RECOVERY
                if wobble_percent < 0.25:
                    blink = int(frame // 4) % 2 == 0
                    if blink:
                        pyxel.circb(sx, py_val, PLATE_RADIUS + 2, PINK)

        for p in self.particles:
            alpha = p.life / 25.0
            if alpha > 0:
                pyxel.pset(int(p.x), int(p.y), p.color)

        for ft in self.floating_texts:
            alpha = ft.life / FLOAT_TEXT_LIFE
            if alpha > 0:
                pyxel.text(int(ft.x - len(ft.text) * 2), int(ft.y), ft.text, ft.color)

        self._draw_hud()

    def _draw_hud(self) -> None:
        pyxel.text(4, 2, f"SCORE:{self.score}", WHITE)

        combo_color = WHITE
        if self.combo >= 4:
            combo_color = PINK if pyxel.frame_count // 8 % 2 == 0 else YELLOW
        pyxel.text(WIDE // 2 - 20, 2, f"COMBO:{self.combo}", combo_color)

        seconds = self.timer // TARGET_FPS
        timer_color = WHITE if seconds > 10 else (PINK if pyxel.frame_count // 15 % 2 == 0 else WHITE)
        pyxel.text(WIDE - 70, 2, f"TIME:{seconds}", timer_color)

        bar_x = 4
        bar_y = 12
        bar_w = 80
        bar_h = 6
        heat_pct = self.heat / HEAT_MAX
        fill_w = int(bar_w * heat_pct)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        if fill_w > 0:
            if heat_pct < 0.5:
                bar_color = LIME
            elif heat_pct < 0.75:
                bar_color = YELLOW
            else:
                bar_color = RED
            pyxel.rect(bar_x + 1, bar_y + 1, fill_w - 2, bar_h - 2, bar_color)

        if self.super_timer > 0:
            super_seconds = self.super_timer // TARGET_FPS
            pyxel.text(WIDE - 60, 20, f"SUPER:{super_seconds}", LIME)

    def _draw_game_over(self) -> None:
        pyxel.text(WIDE // 2 - 30, 80, "GAME OVER", RED)
        pyxel.text(WIDE // 2 - 60, 120, f"SCORE: {self.score}", WHITE)
        pyxel.text(WIDE // 2 - 60, 140, f"BEST: {self.best_score}", YELLOW)
        pyxel.text(WIDE // 2 - 60, 160, f"MAX COMBO: {self.max_combo}", LIME)
        pyxel.text(WIDE // 2 - 55, 210, "CLICK or SPACE to retry", LIME)


def _btnp(key: int) -> bool:
    x = pyxel.mouse_x
    y = pyxel.mouse_y
    return pyxel.btnp(key) and 0 <= x < WIDE and 0 <= y < HIGH


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
