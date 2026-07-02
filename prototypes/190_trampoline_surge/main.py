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

ZONE_COLORS: tuple[int, ...] = (RED, GREEN, DARK_BLUE, YELLOW)
ZONE_X_POSITIONS: tuple[int, ...] = (40, 100, 160, 220)
ZONE_WIDTH: int = 60
TRAMPOLINE_Y: int = 220
PLAYER_RADIUS: int = 6
GRAVITY: float = 0.3
BOUNCE_VEL: float = -8.0
AIR_FRICTION: float = 0.98
MAX_VX: float = 4.0
HEAT_DECAY: float = 0.05
HEAT_MAX: int = 100
HEAT_MISMATCH: int = 15
SUPER_DURATION: int = 300
GAME_DURATION: int = 3600
COMBO_THRESHOLD: int = 4
SUPER_COLORS: tuple[int, ...] = (RED, ORANGE, YELLOW, LIME, GREEN, CYAN, DARK_BLUE, PURPLE, PINK)


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Player:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    on_ground: bool


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
        pyxel.init(320, 240, "Trampoline Surge", display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.player: Player = Player(
            x=160.0, y=float(TRAMPOLINE_Y - PLAYER_RADIUS),
            vx=0.0, vy=0.0, color=RED, on_ground=True,
        )
        self.zones: list[int] = list(ZONE_COLORS)
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.super_timer: int = 0
        self.timer: int = GAME_DURATION
        self.last_zone_color: int = RED
        self.particles: list[Particle] = []
        self.float_texts: list[FloatText] = []
        self._rng: random.Random = random.Random()
        self._peak_y: float = float(TRAMPOLINE_Y)
        self._game_over_reason: str = ""

    def _apply_physics(self) -> None:
        p = self.player
        p.vy += GRAVITY
        p.x += p.vx
        p.y += p.vy
        if not p.on_ground:
            p.vx *= AIR_FRICTION
            if p.vx > MAX_VX:
                p.vx = MAX_VX
            elif p.vx < -MAX_VX:
                p.vx = -MAX_VX
        else:
            p.vx = 0.0
        if p.x < PLAYER_RADIUS:
            p.x = PLAYER_RADIUS
            if p.vx < 0:
                p.vx = 0.0
        elif p.x > 320 - PLAYER_RADIUS:
            p.x = 320 - PLAYER_RADIUS
            if p.vx > 0:
                p.vx = 0.0
        if p.y + PLAYER_RADIUS > TRAMPOLINE_Y:
            p.y = float(TRAMPOLINE_Y - PLAYER_RADIUS)
            p.vy = 0.0
            p.on_ground = True
        if p.y < self._peak_y:
            self._peak_y = p.y

    def _check_landing(self) -> tuple[bool, int]:
        p = self.player
        if p.y + PLAYER_RADIUS >= TRAMPOLINE_Y and p.vy > 0 and not p.on_ground:
            zone_idx = -1
            for i, zx in enumerate(ZONE_X_POSITIONS):
                if zx <= p.x < zx + ZONE_WIDTH:
                    zone_idx = i
                    break
            return True, zone_idx
        return False, -1

    def _shuffle_zones(self) -> None:
        self._rng.shuffle(self.zones)

    def _resolve_landing(self, zone_idx: int) -> int:
        matched = False
        if self.super_timer > 0:
            matched = True
        elif zone_idx >= 0:
            matched = self.zones[zone_idx] == self.last_zone_color

        if matched:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            was_super = self.super_timer > 0
            if self.combo >= COMBO_THRESHOLD and self.super_timer == 0:
                self.super_timer = SUPER_DURATION
                self._spawn_super_particles(self.player.x, self.player.y)
                self._spawn_float_text(self.player.x, self.player.y - 16, "SUPER!", WHITE, 60)

            bounce_height = int(TRAMPOLINE_Y - self._peak_y)
            base = max(0.0, bounce_height)
            multiplier = 1.0 + 0.5 * self.combo
            if was_super:
                multiplier *= 3.0
            scored = int(base * multiplier)
            self.score += scored

            zone_color = self.zones[zone_idx] if zone_idx >= 0 else RED
            self._spawn_bounce_particles(self.player.x, zone_color)
            self._spawn_float_text(self.player.x, self.player.y - 8, f"+{scored}", WHITE, 30)
            if self.combo >= 2:
                self._spawn_float_text(
                    self.player.x, self.player.y - 20,
                    f"COMBO x{self.combo}", zone_color, 45,
                )
            return scored
        else:
            self.combo = 0
            self.heat = min(float(HEAT_MAX), self.heat + float(HEAT_MISMATCH))
            bounce_height = int(TRAMPOLINE_Y - self._peak_y)
            base = max(0.0, bounce_height)
            scored = int(base)
            self.score += scored
            self._spawn_bounce_particles(self.player.x, GRAY)
            self._spawn_float_text(self.player.x, self.player.y - 8, "+0", GRAY, 30)
            self._spawn_float_text(self.player.x, self.player.y - 20, "HEAT!", ORANGE, 30)
            return scored

    def _spawn_bounce_particles(self, x: float, color: int) -> None:
        n = 8
        for _ in range(n):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.0)
            self.particles.append(Particle(
                x=x, y=float(TRAMPOLINE_Y),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 1.0,
                life=self._rng.randint(15, 25),
                color=color,
            ))

    def _spawn_super_particles(self, x: float, y: float) -> None:
        for _ in range(20):
            self.particles.append(Particle(
                x=x, y=y,
                vx=self._rng.uniform(-3.0, 3.0),
                vy=self._rng.uniform(-4.0, -1.0),
                life=self._rng.randint(20, 35),
                color=self._rng.choice(SUPER_COLORS),
            ))

    def _spawn_float_text(self, x: float, y: float, text: str, color: int, life: int) -> None:
        self.float_texts.append(FloatText(x=x, y=y, text=text, life=life, color=color))

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def _update_float_texts(self) -> None:
        alive: list[FloatText] = []
        for ft in self.float_texts:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life > 0:
                alive.append(ft)
        self.float_texts = alive

    def _update_heat(self) -> None:
        if self.heat >= HEAT_MAX:
            self._game_over_reason = "OVERHEAT!"
            self.phase = Phase.GAME_OVER
            return
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_timer(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self._game_over_reason = "TIME UP!"
            self.phase = Phase.GAME_OVER

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1

    def _steer_air(self) -> None:
        if self.player.on_ground:
            return
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            self.player.vx -= 0.5
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            self.player.vx += 0.5

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self._steer_air()
        self._apply_physics()
        did_land, zone_idx = self._check_landing()
        if did_land:
            self._resolve_landing(zone_idx)
            if zone_idx >= 0:
                self.last_zone_color = self.zones[zone_idx]
            self.player.vy = BOUNCE_VEL
            self.player.y = float(TRAMPOLINE_Y - PLAYER_RADIUS)
            self.player.on_ground = False
            self._peak_y = float(TRAMPOLINE_Y)
            self._shuffle_zones()
        self._update_heat()
        if self.phase != Phase.PLAYING:
            return
        self._update_timer()
        if self.phase != Phase.PLAYING:
            return
        self._update_super()
        self._update_particles()
        self._update_float_texts()

    def _update_game_over(self) -> None:
        self._update_particles()
        self._update_float_texts()
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.phase = Phase.TITLE

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(72, 70, "TRAMPOLINE SURGE", WHITE)
        pyxel.text(50, 100, "Same-color bounce = COMBO!", LIGHT_BLUE)
        pyxel.text(55, 115, "COMBO x4 = SUPER BOUNCE!", YELLOW)
        pyxel.text(55, 135, "Wrong color = HEAT + COMBO reset", ORANGE)
        pyxel.text(50, 165, "LEFT/RIGHT or A/D to steer in air", GRAY)
        pyxel.text(85, 200, "Press ENTER to start", CYAN)

    def _draw_playing(self) -> None:
        pyxel.line(0, TRAMPOLINE_Y, 320, TRAMPOLINE_Y, GRAY)
        pyxel.line(0, TRAMPOLINE_Y + 1, 320, TRAMPOLINE_Y + 1, GRAY)
        pyxel.line(0, TRAMPOLINE_Y + 2, 320, TRAMPOLINE_Y + 2, GRAY)
        for i in range(4):
            zx = ZONE_X_POSITIONS[i]
            color = self.zones[i]
            if self.super_timer > 0:
                pulse = (pyxel.frame_count // 6) % len(SUPER_COLORS)
                color = SUPER_COLORS[pulse]
            pyxel.rect(zx, TRAMPOLINE_Y - 8, ZONE_WIDTH, 8, color)

        if self.super_timer > 0:
            rainbow_idx = (pyxel.frame_count // 4) % len(SUPER_COLORS)
            player_color = SUPER_COLORS[rainbow_idx]
        else:
            player_color = WHITE
        px = int(self.player.x)
        py = int(self.player.y)
        pyxel.circ(px, py, PLAYER_RADIUS, player_color)

        for p in self.particles:
            alpha = p.life / 35
            if alpha > 0.3:
                pyxel.pset(int(p.x), int(p.y), p.color)

        for ft in self.float_texts:
            if ft.life > 0:
                col = ft.color
                if ft.life < 8 and ft.life % 2 == 0:
                    continue
                tx = int(ft.x) - len(ft.text) * 2
                pyxel.text(tx, int(ft.y), ft.text, col)

        self._draw_hud()

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"Score: {self.score}", WHITE)
        pyxel.text(4, 14, f"Combo: x{self.combo}", WHITE)
        secs = self.timer // 60
        pyxel.text(260, 4, f"{secs}s", WHITE)

        bar_x = 310
        bar_y = 20
        bar_h = 200
        bar_w = 6
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        fill_h = int(bar_h * (self.heat / HEAT_MAX))
        if self.heat < 30:
            heat_color = GREEN
        elif self.heat < 60:
            heat_color = YELLOW
        elif self.heat < 85:
            heat_color = ORANGE
        else:
            heat_color = RED
        pyxel.rect(bar_x, bar_y + bar_h - fill_h, bar_w, fill_h, heat_color)

        if self.super_timer > 0:
            pulse_color = SUPER_COLORS[(pyxel.frame_count // 8) % len(SUPER_COLORS)]
            pyxel.text(125, 20, "SUPER!", pulse_color)
            super_bar_w = 60
            pyxel.rect(185, 22, super_bar_w, 4, GRAY)
            fill = int(super_bar_w * (self.super_timer / SUPER_DURATION))
            pyxel.rect(185, 22, fill, 4, pulse_color)

    def _draw_game_over(self) -> None:
        pyxel.text(120, 70, "GAME OVER", WHITE)
        pyxel.text(100, 95, self._game_over_reason, RED)
        pyxel.text(95, 115, f"Final Score: {self.score}", WHITE)
        pyxel.text(80, 130, f"Max Combo: x{self.max_combo}", LIME)
        pyxel.text(90, 170, "Press ENTER to retry", CYAN)

        for p in self.particles:
            if p.life > 0:
                pyxel.pset(int(p.x), int(p.y), p.color)
        for ft in self.float_texts:
            if ft.life > 0:
                tx = int(ft.x) - len(ft.text) * 2
                pyxel.text(tx, int(ft.y), ft.text, ft.color)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
