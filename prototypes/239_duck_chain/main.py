"""Duck Chain — Top-down Duck Duck Goose circle game with color-match COMBO chain mechanics."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar, Self

import pyxel


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    CHASE = auto()
    GAME_OVER = auto()


@dataclass
class Duck:
    idx: int
    color: int
    angle: float
    x: float = 0.0
    y: float = 0.0
    active: bool = True


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


class Game:
    SCREEN_W: ClassVar[int] = 320
    SCREEN_H: ClassVar[int] = 240
    CIRCLE_CX: ClassVar[int] = 160
    CIRCLE_CY: ClassVar[int] = 120
    CIRCLE_R: ClassVar[int] = 80
    PLAYER_TRACK_R: ClassVar[int] = 100
    DUCK_COUNT: ClassVar[int] = 12
    DUCK_RADIUS: ClassVar[int] = 8
    PLAYER_RADIUS: ClassVar[int] = 6
    CHASE_CATCH_DIST: ClassVar[int] = 8
    PLAYER_SPEED: ClassVar[float] = 1.5
    CHASE_PLAYER_SPEED: ClassVar[float] = 2.0
    CHASE_DUCK_SPEED: ClassVar[float] = 1.5
    DUCK_COLORS: ClassVar[tuple[int, ...]] = (8, 11, 5, 10)
    COLOR_CYCLE_INTERVAL: ClassVar[int] = 90
    COMBO_THRESHOLD: ClassVar[int] = 4
    SUPER_DURATION: ClassVar[int] = 300
    SUPER_MULT: ClassVar[int] = 3
    HEAT_MAX: ClassVar[int] = 100
    HEAT_MISMATCH: ClassVar[int] = 15
    HEAT_CAUGHT: ClassVar[int] = 25
    HEAT_DECAY: ClassVar[float] = 0.02
    GAME_DURATION: ClassVar[int] = 60 * 60
    SHUFFLE_INTERVAL: ClassVar[int] = 10 * 60
    TAG_COOLDOWN: ClassVar[int] = 15
    PARTICLE_GRAVITY: ClassVar[float] = 0.1

    phase: Phase
    score: int
    combo: int
    max_combo: int
    heat: float
    timer: int
    player_angle: float
    player_color_idx: int
    color_timer: int
    ducks: list[Duck]
    chase_duck_idx: int
    chase_duck_x: float
    chase_duck_y: float
    chase_target_x: float
    chase_target_y: float
    player_x: float
    player_y: float
    super_timer: int
    tag_cooldown: int
    shuffle_timer: int
    particles: list[Particle]
    _rng: random.Random
    _elapsed_frames: int
    _shake_x: float
    _shake_y: float
    _shake_duration: int
    _chase_flash_timer: int
    _last_goose_duck_idx: int

    def __new__(cls) -> Self:
        instance = object.__new__(cls)
        instance.phase = Phase.TITLE
        instance.score = 0
        instance.combo = 0
        instance.max_combo = 0
        instance.heat = 0.0
        instance.timer = 0
        instance.player_angle = 0.0
        instance.player_color_idx = 0
        instance.color_timer = 0
        instance.ducks = []
        instance.chase_duck_idx = -1
        instance.chase_duck_x = 0.0
        instance.chase_duck_y = 0.0
        instance.chase_target_x = 0.0
        instance.chase_target_y = 0.0
        instance.player_x = 0.0
        instance.player_y = 0.0
        instance.super_timer = 0
        instance.tag_cooldown = 0
        instance.shuffle_timer = 0
        instance.particles: list[Particle] = []
        instance._rng = random.Random()
        instance._elapsed_frames = 0
        instance._shake_x = 0.0
        instance._shake_y = 0.0
        instance._shake_duration = 0
        instance._chase_flash_timer = 0
        instance._last_goose_duck_idx = -1
        return instance

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = self.GAME_DURATION
        self.player_angle = 0.0
        self.player_color_idx = 0
        self.color_timer = self.COLOR_CYCLE_INTERVAL
        self.super_timer = 0
        self.tag_cooldown = 0
        self.shuffle_timer = self.SHUFFLE_INTERVAL
        self.particles.clear()
        self.chase_duck_idx = -1
        self._elapsed_frames = 0
        self._shake_x = 0.0
        self._shake_y = 0.0
        self._shake_duration = 0
        self._chase_flash_timer = 0
        self._last_goose_duck_idx = -1

        self.ducks = []
        for i in range(self.DUCK_COUNT):
            angle = (2 * math.pi * i / self.DUCK_COUNT) - (math.pi / 2)
            color = self._rng.choice(self.DUCK_COLORS)
            duck = Duck(idx=i, color=color, angle=angle)
            self.ducks.append(duck)
        self._update_positions()

    def _update_positions(self) -> None:
        for duck in self.ducks:
            if duck.active or self.chase_duck_idx != duck.idx:
                duck.x = self.CIRCLE_CX + self.CIRCLE_R * math.cos(duck.angle)
                duck.y = self.CIRCLE_CY + self.CIRCLE_R * math.sin(duck.angle)

        if self.phase in (Phase.PLAYING, Phase.TITLE):
            self.player_x = self.CIRCLE_CX + self.PLAYER_TRACK_R * math.cos(self.player_angle)
            self.player_y = self.CIRCLE_CY + self.PLAYER_TRACK_R * math.sin(self.player_angle)

    def _get_player_duck_idx(self) -> int:
        best_idx = 0
        best_dist = float("inf")
        px = self.CIRCLE_CX + self.PLAYER_TRACK_R * math.cos(self.player_angle)
        py = self.CIRCLE_CY + self.PLAYER_TRACK_R * math.sin(self.player_angle)
        for duck in self.ducks:
            if not duck.active:
                continue
            dx = duck.x - px
            dy = duck.y - py
            dist = dx * dx + dy * dy
            if dist < best_dist:
                best_dist = dist
                best_idx = duck.idx
        return best_idx

    def _tag_duck(self, idx: int) -> tuple[bool, int]:
        if self.tag_cooldown > 0:
            return False, 0
        if idx < 0 or idx >= self.DUCK_COUNT:
            return False, 0

        duck = self.ducks[idx]
        if not duck.active:
            return False, 0

        player_color = self.DUCK_COLORS[self.player_color_idx]
        matched = duck.color == player_color or self.super_timer > 0

        if matched:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            mult = self.SUPER_MULT if self.super_timer > 0 else 1
            score_earned = 10 * self.combo * mult
            self.score += score_earned
            self.tag_cooldown = self.TAG_COOLDOWN
            self._spawn_particles(duck.x, duck.y, duck.color, 8, (10, 20), (-1.0, 1.0), (-1.0, 1.0))
            return True, score_earned
        else:
            self.combo = 0
            self.heat = min(self.HEAT_MAX, self.heat + self.HEAT_MISMATCH)
            self.tag_cooldown = self.TAG_COOLDOWN
            self._spawn_particles(duck.x, duck.y, 14, 4, (5, 10), (-0.5, 0.5), (-0.5, 0.5))
            self._trigger_shake(2.0, 6)
            return False, 0

    def _try_trigger_chase(self) -> bool:
        if self.combo < self.COMBO_THRESHOLD:
            return False
        if self.phase != Phase.PLAYING:
            return False

        idx = self._get_player_duck_idx()
        duck = self.ducks[idx]
        if not duck.active:
            return False

        self.chase_duck_idx = idx
        self._last_goose_duck_idx = idx
        duck.active = False
        self.chase_duck_x = duck.x
        self.chase_duck_y = duck.y
        self.chase_target_x = duck.x
        self.chase_target_y = duck.y

        self.player_x = self.CIRCLE_CX + self.PLAYER_TRACK_R * math.cos(self.player_angle)
        self.player_y = self.CIRCLE_CY + self.PLAYER_TRACK_R * math.sin(self.player_angle)

        self.phase = Phase.CHASE
        self._chase_flash_timer = 60
        return True

    def _update_chase(self) -> str:
        dx = self.chase_target_x - self.player_x
        dy = self.chase_target_y - self.player_y
        dist_to_target = math.hypot(dx, dy)

        e_dx = self.player_x - self.chase_duck_x
        e_dy = self.player_y - self.chase_duck_y
        dist_to_duck = math.hypot(e_dx, e_dy)

        if dist_to_target < 8.0:
            return "reached"

        if dist_to_duck < self.CHASE_CATCH_DIST:
            return "caught"

        if dx != 0 or dy != 0:
            move_x = (dx / dist_to_target) * self.CHASE_PLAYER_SPEED
            move_y = (dy / dist_to_target) * self.CHASE_PLAYER_SPEED
            self.player_x += move_x
            self.player_y += move_y

        if e_dx != 0 or e_dy != 0:
            chase_move_x = (e_dx / dist_to_duck) * self.CHASE_DUCK_SPEED
            chase_move_y = (e_dy / dist_to_duck) * self.CHASE_DUCK_SPEED
            self.chase_duck_x += chase_move_x
            self.chase_duck_y += chase_move_y

        if dist_to_duck < 16.0:
            self._trigger_shake(1.0, 4)

        return "chasing"

    def _resolve_chase(self, result: str) -> None:
        if result == "reached":
            self.super_timer = self.SUPER_DURATION
            self.combo = 0
            self._spawn_particles(
                self.player_x, self.player_y, 0, 20, (15, 30), (-2.0, 2.0), (-2.0, 2.0)
            )
            self._trigger_shake(6.0, 15)
            self.phase = Phase.PLAYING
        elif result == "caught":
            self.heat = min(self.HEAT_MAX, self.heat + self.HEAT_CAUGHT)
            self.combo = 0
            self._spawn_particles(
                self.player_x, self.player_y, 8, 10, (10, 20), (-1.5, 1.5), (-1.5, 1.5)
            )
            self._trigger_shake(4.0, 10)
            self.phase = Phase.PLAYING
        else:
            self.phase = Phase.PLAYING

        duck = self.ducks[self.chase_duck_idx]
        duck.active = True
        self.chase_duck_idx = -1
        self.player_angle = math.atan2(
            self.player_y - self.CIRCLE_CY, self.player_x - self.CIRCLE_CX
        )
        self._update_positions()

    def _update_heat(self) -> None:
        if self.heat >= self.HEAT_MAX:
            self.phase = Phase.GAME_OVER
            return
        self.heat = max(0.0, self.heat - self.HEAT_DECAY)

    def _shuffle_ducks(self) -> None:
        new_colors = [self._rng.choice(self.DUCK_COLORS) for _ in range(self.DUCK_COUNT)]
        all_same = True
        for c in new_colors:
            if c != new_colors[0]:
                all_same = False
                break
        if all_same and len(self.DUCK_COLORS) > 1:
            diff_idx = self._rng.randrange(self.DUCK_COUNT)
            available = [c for c in self.DUCK_COLORS if c != new_colors[0]]
            new_colors[diff_idx] = self._rng.choice(available)

        for i, duck in enumerate(self.ducks):
            duck.color = new_colors[i]

    def _spawn_particles(
        self,
        x: float,
        y: float,
        color: int | tuple[int, ...],
        count: int,
        life_range: tuple[int, int],
        vx_range: tuple[float, float],
        vy_range: tuple[float, float],
    ) -> None:
        for _ in range(count):
            vx = self._rng.uniform(*vx_range)
            vy = self._rng.uniform(*vy_range)
            life = self._rng.randint(*life_range)
            c = color if isinstance(color, int) else self._rng.choice(color)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=c))

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.life -= 1
            if p.life <= 0:
                continue
            p.vy += self.PARTICLE_GRAVITY
            p.x += p.vx
            p.y += p.vy
            alive.append(p)
        self.particles = alive

    def _update_timers(self) -> None:
        if self.timer > 0:
            self.timer -= 1
            if self.timer <= 0:
                self.timer = 0
                self.phase = Phase.GAME_OVER

        if self.super_timer > 0:
            self.super_timer -= 1

        if self.tag_cooldown > 0:
            self.tag_cooldown -= 1

    def _trigger_shake(self, intensity: float, duration: int) -> None:
        self._shake_x = intensity
        self._shake_y = intensity
        self._shake_duration = duration

    def _update_shake(self) -> None:
        if self._shake_duration > 0:
            self._shake_duration -= 1
            if self._shake_duration <= 0:
                self._shake_x = 0.0
                self._shake_y = 0.0
            else:
                self._shake_x = self._rng.uniform(-2, 2)
                self._shake_y = self._rng.uniform(-2, 2)

    def get_color_cycle_interval(self) -> int:
        elapsed_s = self._elapsed_frames / 60.0
        return max(50, int(90 - elapsed_s * 0.5))

    def get_shuffle_interval(self) -> int:
        elapsed_s = self._elapsed_frames / 60.0
        return max(300, int(600 - elapsed_s * 3))

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            return

        if self.phase == Phase.GAME_OVER:
            return

        self._elapsed_frames += 1
        self._update_timers()
        self._update_heat()
        self._update_shake()
        self._update_particles()

        if self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.CHASE:
            self._update_chase_phase()

        if self._chase_flash_timer > 0:
            self._chase_flash_timer -= 1

    def _update_playing(self) -> None:
        if self.color_timer > 0:
            self.color_timer -= 1
        else:
            self.color_timer = self.get_color_cycle_interval()
            self.player_color_idx = (self.player_color_idx + 1) % len(self.DUCK_COLORS)

        if self.shuffle_timer > 0:
            self.shuffle_timer -= 1
        else:
            self.shuffle_timer = self.get_shuffle_interval()
            self._shuffle_ducks()

        if self.chase_duck_idx == -1:
            self._update_positions()

    def _update_chase_phase(self) -> None:
        result = self._update_chase()
        if result != "chasing":
            self._resolve_chase(result)

    def handle_input(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.phase = Phase.TITLE
            return

        if self.phase == Phase.PLAYING:
            self._handle_playing_input()
        elif self.phase == Phase.CHASE:
            self._handle_chase_input()

    def _handle_playing_input(self) -> None:
        if pyxel.btn(pyxel.KEY_LEFT):
            self.player_angle -= self.PLAYER_SPEED * (math.pi / 180)
        if pyxel.btn(pyxel.KEY_RIGHT):
            self.player_angle += self.PLAYER_SPEED * (math.pi / 180)

        self._update_positions()

        if pyxel.btnp(pyxel.KEY_SPACE):
            idx = self._get_player_duck_idx()
            matched, _ = self._tag_duck(idx)
            if matched and self.combo >= self.COMBO_THRESHOLD:
                self._try_trigger_chase()

    def _handle_chase_input(self) -> None:
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            self.player_x -= self.CHASE_PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            self.player_x += self.CHASE_PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            self.player_y -= self.CHASE_PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            self.player_y += self.CHASE_PLAYER_SPEED

    def draw(self) -> None:
        ox = int(self._shake_x) if self._shake_duration > 0 else 0
        oy = int(self._shake_y) if self._shake_duration > 0 else 0
        pyxel.camera(ox, oy)

        pyxel.cls(0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.PLAYING, Phase.CHASE):
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

        pyxel.camera(0, 0)

    def _draw_title(self) -> None:
        pyxel.text(110, 80, "DUCK CHAIN", 7)
        pyxel.text(85, 100, "Press SPACE to Start", 7)
        pyxel.text(40, 130, "LEFT/RIGHT: Walk  SPACE: Tag", 7)
        pyxel.text(50, 140, "Match colors for COMBO!", 7)
        pyxel.text(55, 155, "COMBO 4+ = GOOSE CHASE!", 12)

    def _draw_game(self) -> None:
        pyxel.circb(self.CIRCLE_CX, self.CIRCLE_CY, self.CIRCLE_R, 13)

        for i in range(24):
            angle = i * (math.pi / 12)
            x = self.CIRCLE_CX + self.PLAYER_TRACK_R * math.cos(angle)
            y = self.CIRCLE_CY + self.PLAYER_TRACK_R * math.sin(angle)
            if i % 2 == 0:
                pyxel.pset(int(x), int(y), 13)

        for duck in self.ducks:
            if duck.idx == self.chase_duck_idx and self.phase == Phase.CHASE:
                continue
            self._draw_duck(duck.x, duck.y, duck.color, duck.angle)

        if self.phase == Phase.CHASE and self.chase_duck_idx >= 0:
            chase_duck = self.ducks[self.chase_duck_idx]
            self._draw_goose_spot(self.chase_target_x, self.chase_target_y)
            self._draw_chase_duck(self.chase_duck_x, self.chase_duck_y, chase_duck.color)

        player_color = self.DUCK_COLORS[self.player_color_idx]
        if self.super_timer > 0:
            player_color = self._get_rainbow_color()

        if self.phase == Phase.PLAYING:
            px = int(self.CIRCLE_CX + self.PLAYER_TRACK_R * math.cos(self.player_angle))
            py = int(self.CIRCLE_CY + self.PLAYER_TRACK_R * math.sin(self.player_angle))
            pyxel.circ(px, py, self.PLAYER_RADIUS - 1, 7)
            pyxel.circb(px, py, self.PLAYER_RADIUS + 1, player_color)
            beak_angle = self.player_angle + (math.pi / 2)
            bx = int(px + (self.PLAYER_RADIUS + 2) * math.cos(beak_angle))
            by = int(py + (self.PLAYER_RADIUS + 2) * math.sin(beak_angle))
            pyxel.pset(bx, by, player_color)
        elif self.phase == Phase.CHASE:
            px = int(self.player_x)
            py = int(self.player_y)
            pyxel.circ(px, py, self.PLAYER_RADIUS - 1, 7)
            pyxel.circb(px, py, self.PLAYER_RADIUS + 1, player_color)

        for p in self.particles:
            alpha = p.life / 30.0
            c = p.color if alpha > 0.3 else 13
            pyxel.rect(int(p.x), int(p.y), 2, 2, c)

        self._draw_hud()

        if self.phase == Phase.CHASE:
            pyxel.text(100, 50, "GOOSE CHASE!", 12 if self._chase_flash_timer % 8 < 4 else 7)

        if self.super_timer > 0:
            pyxel.text(105, 65, "SUPER GOOSE!", self._get_rainbow_color())

    def _draw_duck(self, x: float, y: float, color: int, angle: float) -> None:
        ix = int(x)
        iy = int(y)
        pyxel.circ(ix, iy, self.DUCK_RADIUS - 1, color)
        pyxel.circb(ix, iy, self.DUCK_RADIUS, 0)
        beak_angle = angle + (math.pi / 2)
        bx = int(ix + (self.DUCK_RADIUS + 2) * math.cos(beak_angle))
        by = int(iy + (self.DUCK_RADIUS + 2) * math.sin(beak_angle))
        pyxel.pset(bx, by, color)

    def _draw_goose_spot(self, x: float, y: float) -> None:
        blink_on = pyxel.frame_count % 30 < 15
        color = 12 if blink_on else 7
        pyxel.circb(int(x), int(y), self.DUCK_RADIUS, color)
        pyxel.circ(int(x), int(y), 2, color)

    def _draw_chase_duck(self, x: float, y: float, color: int) -> None:
        ix = int(x)
        iy = int(y)
        pyxel.circ(ix, iy, self.DUCK_RADIUS + 2, 8)
        pyxel.circ(ix, iy, self.DUCK_RADIUS, color)
        pyxel.circb(ix, iy, self.DUCK_RADIUS + 2, 8)

    def _get_rainbow_color(self) -> int:
        colors = self.DUCK_COLORS
        idx = (pyxel.frame_count // 4) % len(colors)
        return colors[idx]

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", 7)
        pyxel.text(4, 14, f"COMBO: {self.combo}", 7)
        pyxel.text(4, 24, f"MAX COMBO: {self.max_combo}", 7)

        sec = self.timer // 60
        frame = self.timer % 60
        pyxel.text(230, 4, "TIME", 7)
        pyxel.text(230, 14, f"{sec:02d}:{frame:02d}", 7)

        player_color_label = self.DUCK_COLORS[self.player_color_idx]
        pyxel.text(4, 34, "COLOR:", 7)
        pyxel.rect(48, 34, 8, 8, player_color_label)

        pyxel.text(4, 48, "HEAT", 7)
        pyxel.rectb(4, 56, 60, 8, 13)
        hw = int(60 * (self.heat / self.HEAT_MAX))
        heat_color = 8 if self.heat < 80 else (8 if pyxel.frame_count % 10 < 5 else 9)
        pyxel.rect(4, 56, hw, 8, heat_color)

    def _draw_game_over(self) -> None:
        pyxel.text(120, 80, "GAME OVER", 7)
        pyxel.text(90, 100, f"SCORE: {self.score}", 7)
        pyxel.text(75, 110, f"MAX COMBO: {self.max_combo}", 7)
        pyxel.text(80, 130, "Press SPACE to Retry", 7)


class App:
    def __init__(self) -> None:
        pyxel.init(Game.SCREEN_W, Game.SCREEN_H, title="Duck Chain", fps=60)
        self.game = Game.__new__(Game)
        self.game.phase = Phase.TITLE
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        self.game.handle_input()
        self.game.update()

    def draw(self) -> None:
        self.game.draw()


if __name__ == "__main__":
    App()
