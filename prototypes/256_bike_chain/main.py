from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel

SCREEN_W = 320
SCREEN_H = 240
GROUND_Y = 200
BIKE_X = 80
JUMP_VY = -8.0
GRAVITY = 0.45
COLOR_VALS: tuple[int, int, int, int] = (8, 11, 5, 10)
COLOR_NAMES: tuple[str, str, str, str] = ("RED", "LIME", "BLUE", "YELLOW")
COLOR_CYCLE_FRAMES = 20
SUPER_DURATION = 300
MAX_HEAT = 100.0
HEAT_DECAY = 0.02
HEAT_MISMATCH = 15.0
HEAT_IGNORE = 5.0
STAMINA_MAX = 100.0
STAMINA_JUMP_COST = 20.0
STAMINA_RECHARGE = 0.05
GAME_DURATION = 1800
GATE_GAP_WIDTH = 40
GATE_POLE_WIDTH = 4
FPS = 30

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


@dataclass
class Gate:
    x: float
    y: float
    color: int
    width: int = 20
    passed: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int


class Game:
    COLORS: ClassVar[tuple[int, ...]] = COLOR_VALS

    def __new__(cls, headless: bool = False) -> Game:
        obj = object.__new__(cls)
        obj._set_defaults()
        obj._headless = headless
        return obj

    def _set_defaults(self) -> None:
        self._headless: bool = False
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.best_score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.stamina: float = STAMINA_MAX
        self.timer: int = GAME_DURATION
        self.bike_color: int = 0
        self.bike_color_timer: int = COLOR_CYCLE_FRAMES
        self.bike_y: float = float(GROUND_Y)
        self.bike_vy: float = 0.0
        self.is_jumping: bool = False
        self.super_timer: int = 0
        self.gates: list[Gate] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.scroll_speed: float = 2.0
        self.scroll_x: float = 0.0
        self.gate_spawn_timer: int = 0
        self.gate_spawn_interval: int = 90
        self.shake_frames: int = 0
        self.stun_frames: int = 0
        self.frame: int = 0
        self.ghost_trail: list[tuple[int, int]] = []
        self.best_trail: list[tuple[int, int]] = []
        self.current_trail: list[tuple[int, int]] = []
        self._rng: random.Random = random.Random()

    def __init__(self, headless: bool = False) -> None:
        if not headless:
            pyxel.init(SCREEN_W, SCREEN_H, title="BIKE CHAIN", fps=FPS)
            self.reset()
            pyxel.run(self._update, self._draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.stamina = STAMINA_MAX
        self.timer = GAME_DURATION
        self.bike_color = 0
        self.bike_color_timer = COLOR_CYCLE_FRAMES
        self.bike_y = float(GROUND_Y)
        self.bike_vy = 0.0
        self.is_jumping = False
        self.super_timer = 0
        self.gates.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.scroll_speed = 2.0
        self.scroll_x = 0.0
        self.gate_spawn_timer = 30
        self.gate_spawn_interval = 90
        self.shake_frames = 0
        self.stun_frames = 0
        self.frame = 0
        self.ghost_trail.clear()
        self.best_trail.clear()
        self.current_trail.clear()

    def _get_input(self) -> dict:
        if self._headless:
            return {"space": False, "space_p": False}
        return {
            "space": pyxel.btn(pyxel.KEY_SPACE),
            "space_p": pyxel.btnp(pyxel.KEY_SPACE),
        }

    def _update(self) -> None:
        inp = self._get_input()

        if self.phase == Phase.TITLE:
            self._update_title(inp)
        elif self.phase == Phase.PLAYING:
            self._update_playing(inp)
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over(inp)

    def _update_title(self, inp: dict) -> None:
        if inp["space_p"]:
            self.phase = Phase.PLAYING
            self.score = 0
            self.combo = 0
            self.max_combo = 0
            self.heat = 0.0
            self.stamina = STAMINA_MAX
            self.timer = GAME_DURATION
            self.bike_color = 0
            self.bike_color_timer = COLOR_CYCLE_FRAMES
            self.bike_y = float(GROUND_Y)
            self.bike_vy = 0.0
            self.is_jumping = False
            self.super_timer = 0
            self.gates.clear()
            self.particles.clear()
            self.floating_texts.clear()
            self.scroll_speed = 2.0
            self.scroll_x = 0.0
            self.gate_spawn_timer = 30
            self.gate_spawn_interval = 90
            self.shake_frames = 0
            self.stun_frames = 0
            self.frame = 0
            self.ghost_trail.clear()
            self.current_trail.clear()

    def _update_playing(self, inp: dict) -> None:
        self.frame += 1
        elapsed = GAME_DURATION - self.timer

        self._update_bike_color()
        self._update_bike_jump(inp)
        self._update_bike_physics()

        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer == 0:
                self.combo = 0

        if self.stun_frames > 0:
            self.stun_frames -= 1

        if self.shake_frames > 0:
            self.shake_frames -= 1

        self.scroll_speed = 2.0 + 3.0 * (elapsed / GAME_DURATION)
        self.scroll_x += self.scroll_speed

        self.gate_spawn_interval = int(90 - 60 * (elapsed / GAME_DURATION))
        self.gate_spawn_timer -= 1
        if self.gate_spawn_timer <= 0:
            self._spawn_gate()
            self.gate_spawn_timer = max(30, self.gate_spawn_interval)

        self._update_gates()
        self._update_heat()
        self._update_stamina()
        self._update_particles()
        self._update_floating_texts()

        self.timer -= 1
        if self.timer <= 0 or self.heat >= MAX_HEAT:
            if self.score > self.best_score:
                self.best_score = self.score
            if self.score >= self.best_score and len(self.current_trail) > 0:
                self.best_trail = self.current_trail.copy()
            self.phase = Phase.GAME_OVER

        if self.frame % 5 == 0:
            self.current_trail.append((int(self.scroll_x), int(self.bike_y)))

    def _update_bike_color(self) -> None:
        self.bike_color_timer -= 1
        if self.bike_color_timer <= 0:
            self.bike_color = (self.bike_color + 1) % 4
            self.bike_color_timer = COLOR_CYCLE_FRAMES

    def _update_bike_jump(self, inp: dict) -> None:
        if self._is_super():
            return
        if inp["space_p"] and self.bike_y >= float(GROUND_Y) and self.stun_frames == 0:
            if self.stamina >= STAMINA_JUMP_COST:
                self.bike_vy = JUMP_VY
                self.stamina -= STAMINA_JUMP_COST
                self.is_jumping = True
            elif self.stamina >= 10.0:
                self.bike_vy = JUMP_VY * 0.5
                self.stamina -= self.stamina
                self.is_jumping = True

    def _update_bike_physics(self) -> None:
        if self.bike_y < float(GROUND_Y):
            self.bike_vy += GRAVITY
            self.bike_y += self.bike_vy
            if self.bike_y >= float(GROUND_Y):
                self.bike_y = float(GROUND_Y)
                self.bike_vy = 0.0
                self.is_jumping = False

    def _is_super(self) -> bool:
        return self.super_timer > 0

    def _spawn_gate(self) -> None:
        color = self._rng.choice(COLOR_VALS)
        self.gates.append(Gate(x=float(SCREEN_W + GATE_GAP_WIDTH), y=float(GROUND_Y), color=color, width=GATE_GAP_WIDTH))

    def _process_gate(self, gate: Gate) -> bool:
        if self._is_super():
            return True
        return COLOR_VALS[self.bike_color] == gate.color

    def _update_gates(self) -> None:
        for gate in self.gates:
            gate.x -= self.scroll_speed

        for gate in self.gates:
            if gate.passed:
                continue
            if gate.x <= BIKE_X:
                on_ground = self.bike_y >= float(GROUND_Y)
                if on_ground:
                    matched = self._process_gate(gate)
                    if matched:
                        self.combo += 1
                        if self.combo > self.max_combo:
                            self.max_combo = self.combo
                        multiplier = 3.0 if self._is_super() else 1.0
                        points = int(10 * self.combo * multiplier)
                        self.score += points
                        self._spawn_particles(BIKE_X, GROUND_Y, 6, gate.color)
                        self._spawn_floating_text(BIKE_X, GROUND_Y - 20, f"+{points}", LIME, 30)
                        if self.combo >= 4 and self.super_timer == 0:
                            self.super_timer = SUPER_DURATION
                            self._spawn_particles(BIKE_X, GROUND_Y, 12, -1)
                            self._spawn_floating_text(BIKE_X, GROUND_Y - 32, "SUPER RIDE!", YELLOW, 40)
                    else:
                        self.combo = 0
                        self.heat = min(MAX_HEAT, self.heat + HEAT_MISMATCH)
                        self.stun_frames = 15
                        self.shake_frames = 10
                        self._spawn_particles(BIKE_X, GROUND_Y, 4, RED)
                        self._spawn_floating_text(BIKE_X, GROUND_Y - 20, "WRONG!", RED, 25)
                else:
                    self.heat = min(MAX_HEAT, self.heat + HEAT_IGNORE)
                    self._spawn_floating_text(BIKE_X, GROUND_Y - 20, "SKIP!", GRAY, 25)
                gate.passed = True

        self.gates = [g for g in self.gates if g.x > -GATE_GAP_WIDTH * 2]
        for gate in self.gates:
            if not gate.passed and gate.x + GATE_GAP_WIDTH / 2 < 0:
                gate.passed = True

    def _update_heat(self) -> None:
        if self.heat >= MAX_HEAT:
            if self.score > self.best_score:
                self.best_score = self.score
            if self.score >= self.best_score and len(self.current_trail) > 0:
                self.best_trail = self.current_trail.copy()
            self.phase = Phase.GAME_OVER
            return
        if not self._is_super():
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_stamina(self) -> None:
        self.stamina = min(STAMINA_MAX, self.stamina + STAMINA_RECHARGE)

    def _update_particles(self) -> None:
        for p in self.particles:
            p.vy += 0.05
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            pcolor = color if color != -1 else self._rng.choice(COLOR_VALS)
            vx = self._rng.uniform(-1.5, 1.5)
            vy = self._rng.uniform(-2.5, -0.5)
            life = self._rng.randint(15, 25) if color == -1 else self._rng.randint(12, 20)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, color=pcolor, life=life))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int, life: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, color=color, life=life))

    def _update_game_over(self, inp: dict) -> None:
        if inp["space_p"]:
            self.reset()
            self.phase = Phase.TITLE

    def _draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.PLAYING, Phase.GAME_OVER):
            self._draw_sky()
            self._draw_ground()
            self._draw_best_trail()
            self._draw_gates()
            self._draw_bike()
            self._draw_particles()
            self._draw_floating_texts()
            self._draw_hud()
            if self._is_super():
                self._draw_super_border()
            if self.phase == Phase.GAME_OVER:
                self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, BLACK)
        pyxel.text(SCREEN_W // 2 - 36, 50, "BIKE CHAIN", WHITE)
        pyxel.text(SCREEN_W // 2 - 58, 72, "Color-match BMX Combo!", LIME)
        pyxel.text(SCREEN_W // 2 - 58, 96, "SPACE: Jump (costs stamina)", WHITE)
        pyxel.text(SCREEN_W // 2 - 58, 108, "Stay grounded: ride through gates", WHITE)
        pyxel.text(SCREEN_W // 2 - 58, 120, "Same color: COMBO chain", LIME)
        pyxel.text(SCREEN_W // 2 - 58, 132, "Wrong color: COMBO reset + HEAT", RED)
        pyxel.text(SCREEN_W // 2 - 58, 144, "Jump over gates you want to skip", GRAY)
        pyxel.text(SCREEN_W // 2 - 58, 156, "Bike color cycles automatically", WHITE)
        pyxel.text(SCREEN_W // 2 - 58, 168, "COMBO x4 = SUPER RIDE!", YELLOW)
        pyxel.text(SCREEN_W // 2 - 58, 180, "HEAT 100 = GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 58, 198, "60s to score as high as you can!", WHITE)
        pyxel.text(SCREEN_W // 2 - 45, 220, "SPACE to start", CYAN)
        if self.best_score > 0:
            pyxel.text(SCREEN_W // 2 - 30, 235, f"BEST: {self.best_score}", YELLOW)

    def _draw_sky(self) -> None:
        for i in range(GROUND_Y):
            t = i / GROUND_Y
            if t < 0.5:
                col = NAVY
            elif t < 0.75:
                col = DARK_BLUE
            else:
                col = CYAN
            pyxel.line(0, i, SCREEN_W, i, col)

    def _draw_ground(self) -> None:
        pyxel.rect(0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y, BROWN)
        pyxel.line(0, GROUND_Y, SCREEN_W, GROUND_Y, GREEN)
        for i in range(0, SCREEN_W, 8):
            pyxel.line(i, GROUND_Y - 2, i + 3, GROUND_Y, GREEN)

    def _draw_gates(self) -> None:
        for gate in self.gates:
            x = int(gate.x)
            half_gap = gate.width // 2
            pole_h = 50
            pole_y = GROUND_Y - pole_h

            gate_color = gate.color if not gate.passed else GRAY
            if self._is_super() and not gate.passed:
                rainbow = [RED, ORANGE, YELLOW, LIME, CYAN, PURPLE]
                gate_color = rainbow[(pyxel.frame_count // 3) % len(rainbow)]

            pyxel.rect(x - half_gap - GATE_POLE_WIDTH, pole_y, GATE_POLE_WIDTH, pole_h, gate_color)
            pyxel.rect(x + half_gap, pole_y, GATE_POLE_WIDTH, pole_h, gate_color)

    def _draw_bike(self) -> None:
        bx = BIKE_X
        by = int(self.bike_y)

        if self.stun_frames > 0 and self.frame % 4 < 2:
            draw_color = WHITE
        else:
            draw_color = LIGHT_BLUE

        if self._is_super():
            rainbow = [RED, ORANGE, YELLOW, LIME, CYAN, PURPLE]
            idx = (pyxel.frame_count // 4) % len(rainbow)
            draw_color = rainbow[idx]

        wheel_radius = 8
        rear_wx = bx - 16
        front_wx = bx + 16
        wheel_y = by - wheel_radius

        pyxel.circb(rear_wx, wheel_y, wheel_radius, draw_color)
        pyxel.circb(front_wx, wheel_y, wheel_radius, draw_color)
        pyxel.circ(rear_wx, wheel_y, 2, draw_color)
        pyxel.circ(front_wx, wheel_y, 2, draw_color)

        pyxel.line(rear_wx, wheel_y, front_wx, wheel_y, draw_color)
        pyxel.line(rear_wx, wheel_y, bx - 4, wheel_y - 12, draw_color)
        pyxel.line(front_wx, wheel_y, bx + 4, wheel_y - 12, draw_color)
        pyxel.line(bx - 4, wheel_y - 12, bx + 4, wheel_y - 12, draw_color)
        pyxel.line(bx + 4, wheel_y - 12, bx - 2, wheel_y - 20, draw_color)
        pyxel.line(bx - 4, wheel_y - 12, bx + 2, wheel_y - 18, draw_color)
        pyxel.line(bx, wheel_y - 12, bx, wheel_y - 24, draw_color)

        head_y = wheel_y - 26
        pyxel.circ(bx, head_y, 3, PEACH)
        pyxel.line(bx, head_y + 3, bx, wheel_y - 12, PEACH)
        pyxel.line(bx, head_y + 8, bx - 4, wheel_y - 16, PEACH)
        pyxel.line(bx, head_y + 8, bx + 4, wheel_y - 16, PEACH)
        pyxel.line(bx, wheel_y - 12, bx - 4, wheel_y - 6, PEACH)
        pyxel.line(bx, wheel_y - 12, bx + 4, wheel_y - 6, PEACH)

    def _draw_particles(self) -> None:
        for p in self.particles:
            if p.life > 8:
                pyxel.rect(int(p.x), int(p.y), 2, 2, p.color)
            else:
                pyxel.circ(int(p.x), int(p.y), 1, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life > 0:
                pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        pyxel.text(4, 2, f"SCORE: {self.score}", WHITE)
        pyxel.text(4, 12, f"COMBO: {self.combo}", YELLOW if self.combo >= 3 else WHITE)
        pyxel.text(4, 22, f"MAX: {self.max_combo}", LIME)

        secs = max(0, self.timer // FPS)
        timer_color = WHITE
        if secs <= 10:
            timer_color = RED
        elif secs <= 20:
            timer_color = ORANGE
        pyxel.text(SCREEN_W // 2 - 20, 2, f"TIME: {secs}s", timer_color)

        bike_col = COLOR_VALS[self.bike_color]
        name = COLOR_NAMES[self.bike_color]
        pyxel.text(SCREEN_W - 58, 2, "COLOR:", WHITE)
        pyxel.circ(SCREEN_W - 10, 7, 4, bike_col)
        pyxel.text(SCREEN_W - 58, 12, name, bike_col)

        pyxel.text(4, GROUND_Y + 4, "HEAT", WHITE)
        heat_w = 80
        heat_h = 6
        pyxel.rectb(4, GROUND_Y + 12, heat_w, heat_h, WHITE)
        heat_fill = int(heat_w * self.heat / MAX_HEAT)
        heat_color = LIME if self.heat <= 60 else ORANGE if self.heat <= 80 else RED
        pyxel.rect(4, GROUND_Y + 12, heat_fill, heat_h, heat_color)

        pyxel.text(4, GROUND_Y + 20, "STM", WHITE)
        stam_w = 80
        stam_h = 6
        pyxel.rectb(4, GROUND_Y + 28, stam_w, stam_h, WHITE)
        stam_fill = int(stam_w * self.stamina / STAMINA_MAX)
        stam_color = LIME if self.stamina >= 50 else ORANGE if self.stamina >= 25 else RED
        pyxel.rect(4, GROUND_Y + 28, stam_fill, stam_h, stam_color)

        if self._is_super():
            super_secs = self.super_timer // FPS
            rainbow = [RED, ORANGE, YELLOW, LIME, CYAN, PURPLE]
            col = rainbow[(pyxel.frame_count // 3) % len(rainbow)]
            pyxel.text(SCREEN_W // 2 - 30, 18, f"SUPER! {super_secs}s", col)

    def _draw_super_border(self) -> None:
        rainbow = [RED, ORANGE, YELLOW, LIME, CYAN, PURPLE]
        idx = (pyxel.frame_count // 4) % len(rainbow)
        col = rainbow[idx]
        pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, col)
        idx2 = (idx + 3) % len(rainbow)
        col2 = rainbow[idx2]
        if pyxel.frame_count % 8 < 4:
            pyxel.rectb(1, 1, SCREEN_W - 2, SCREEN_H - 2, col2)

    def _draw_best_trail(self) -> None:
        for tx, ty in self.best_trail:
            rel_x = BIKE_X + (tx - int(self.scroll_x))
            if 0 <= rel_x <= SCREEN_W:
                pyxel.circ(rel_x, ty, 1, CYAN)

    def _draw_game_over(self) -> None:
        pyxel.rect(SCREEN_W // 2 - 70, SCREEN_H // 2 - 35, 140, 60, BLACK)
        pyxel.rectb(SCREEN_W // 2 - 70, SCREEN_H // 2 - 35, 140, 60, RED)
        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 - 25, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 35, SCREEN_H // 2 - 10, f"SCORE: {self.score}", WHITE)
        if self.score >= self.best_score and self.score > 0:
            pyxel.text(SCREEN_W // 2 - 25, SCREEN_H // 2, "NEW BEST!", YELLOW)
        pyxel.text(SCREEN_W // 2 - 45, SCREEN_H // 2 + 12, "SPACE to retry", CYAN)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
