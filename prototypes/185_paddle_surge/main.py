from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


SCREEN_W = 320
SCREEN_H = 240
RIVER_LEFT = 40
RIVER_RIGHT = 280
RIVER_WIDTH = RIVER_RIGHT - RIVER_LEFT
KAYAK_SPEED = 2.0
MAX_HEAT = 100.0
SUPER_DURATION = 300
COMBO_THRESHOLD = 4
SCROLL_SPEED_BASE = 1.0
GATE_SPAWN_INTERVAL = 180
STUN_DURATION = 15

COLOR_RED = 8
COLOR_GREEN = 3
COLOR_DARK_BLUE = 5
COLOR_YELLOW = 10
COLOR_WHITE = 7
COLOR_BLACK = 0
COLOR_GRAY = 13
COLOR_NAVY = 1
COLOR_PURPLE = 2
COLOR_CYAN = 12
COLOR_ORANGE = 9

GATE_COLOR_VALS: tuple[int, int, int, int] = (COLOR_RED, COLOR_GREEN, COLOR_DARK_BLUE, COLOR_YELLOW)


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class GateColor(Enum):
    RED = 0
    GREEN = 1
    DARK_BLUE = 2
    YELLOW = 3


@dataclass
class Gate:
    x: float
    y: float
    color: GateColor
    width: float = 48.0
    pole_w: float = 8.0
    pole_h: float = 20.0
    passed: bool = False


@dataclass
class Rock:
    x: float
    y: float
    radius: float = 10.0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int
    vy: float = -1.0


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.kayak_x = SCREEN_W / 2.0
    g.kayak_y = SCREEN_H - 60.0
    g.kayak_color: GateColor = GateColor.RED
    g.combo = 0
    g.max_combo = 0
    g.score = 0
    g.heat = 0.0
    g.scroll_speed = SCROLL_SPEED_BASE
    g.super_timer = 0
    g.distance = 0.0
    g.gates: list[Gate] = []
    g.rocks: list[Rock] = []
    g.particles: list[Particle] = []
    g.floating_texts: list[FloatingText] = []
    g._gate_timer = 0
    g._rng = random.Random(42)
    g._stun_timer = 0
    g._game_over_timer = 0
    g.phase = Phase.TITLE
    return g


class Game:
    def __init__(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.kayak_x: float = SCREEN_W / 2
        self.kayak_y: float = SCREEN_H - 60
        self.kayak_color: GateColor = GateColor.RED
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.heat: float = 0.0
        self.scroll_speed: float = SCROLL_SPEED_BASE
        self.super_timer: int = 0
        self.distance: float = 0.0
        self.gates: list[Gate] = []
        self.rocks: list[Rock] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._gate_timer: int = 0
        self._rng: random.Random = random.Random()
        self._stun_timer: int = 0
        self._game_over_timer: int = 0

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.kayak_x = SCREEN_W / 2
        self.kayak_y = SCREEN_H - 60
        self.kayak_color = GateColor.RED
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.heat = 0.0
        self.scroll_speed = SCROLL_SPEED_BASE
        self.super_timer = 0
        self.distance = 0.0
        self.gates.clear()
        self.rocks.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self._gate_timer = 0
        self._rng = random.Random()
        self._stun_timer = 0
        self._game_over_timer = 0

    # ---------- pyxel entry points ----------

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
        elif self.phase == Phase.PLAYING:
            self._update_super()
            if self._stun_timer > 0:
                self._stun_timer -= 1
            else:
                self._handle_input()
            self._scroll_river()
            self._spawn_entities()
            self._update_heat()
            self._check_bank_collision()
            self._update_particles()
            self._update_floating_texts()

            gate = self._check_gate_pass()
            if gate is not None:
                earned = self._resolve_gate(gate)
                self.score += earned

            self._check_rock_collision()
        elif self.phase == Phase.GAME_OVER:
            self._update_particles()
            self._update_floating_texts()
            if self._game_over_timer > 0:
                self._game_over_timer -= 1
            elif pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()

    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_playing()
            self._draw_game_over()

    # ---------- input ----------

    def _handle_input(self) -> None:
        dx = dy = 0.0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx = -1.0
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx = 1.0
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy = -1.0
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy = 1.0

        if dx != 0.0 and dy != 0.0:
            dx *= 0.707
            dy *= 0.707

        self.kayak_x += dx * KAYAK_SPEED
        self.kayak_y += dy * KAYAK_SPEED

        self.kayak_x = max(RIVER_LEFT + 8.0, min(RIVER_RIGHT - 8.0, self.kayak_x))
        self.kayak_y = max(20.0, min(SCREEN_H - 20.0, self.kayak_y))

    # ---------- gate logic ----------

    def _spawn_gate(self) -> Gate:
        color = self._rng.choice(list(GateColor))
        margin = 30.0
        x = self._rng.uniform(RIVER_LEFT + margin, RIVER_RIGHT - margin)
        gate = Gate(x=x, y=-20.0, color=color)
        self.gates.append(gate)
        return gate

    def _check_gate_pass(self) -> Gate | None:
        kayak_r = 6.0
        for gate in self.gates:
            if gate.passed:
                continue
            if gate.y <= self.kayak_y <= gate.y + gate.pole_h:
                left_pole_right = gate.x - gate.width / 2.0
                right_pole_left = gate.x + gate.width / 2.0
                if left_pole_right + kayak_r <= self.kayak_x <= right_pole_left - kayak_r:
                    gate.passed = True
                    return gate
        return None

    def _resolve_gate(self, gate: Gate) -> int:
        is_match = self.kayak_color == gate.color
        is_super = self.super_timer > 0
        color_val = GATE_COLOR_VALS[gate.color.value]

        if is_super or is_match:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            multiplier = min(self.combo, 10)
            base_score = 10
            if is_super:
                base_score *= 3
            earned = base_score * multiplier

            if self.combo >= COMBO_THRESHOLD and self.super_timer == 0:
                self.super_timer = SUPER_DURATION
                earned += 50
                self._spawn_floating_text("SUPER!", SCREEN_W / 2.0, SCREEN_H / 2.0, COLOR_YELLOW)

            self.kayak_color = gate.color
            self._spawn_particles(gate.x, gate.y, color_val, 8)
            self._spawn_floating_text(f"+{earned}", gate.x, gate.y, COLOR_YELLOW)
            return earned
        else:
            self.combo = 0
            self.heat = min(MAX_HEAT, self.heat + 15.0)
            self.kayak_color = gate.color
            self._spawn_particles(gate.x, gate.y, COLOR_RED, 4)
            self._spawn_floating_text("MISS!", gate.x, gate.y, COLOR_RED)
            return 0

    # ---------- rock collision ----------

    def _check_rock_collision(self) -> bool:
        kayak_r = 6.0
        for rock in self.rocks:
            dist = math.hypot(self.kayak_x - rock.x, self.kayak_y - rock.y)
            if dist < kayak_r + rock.radius:
                self.heat = min(MAX_HEAT, self.heat + 20.0)
                self._stun_timer = STUN_DURATION
                self._spawn_particles(rock.x, rock.y, COLOR_GRAY, 6)
                self._spawn_floating_text("OUCH!", rock.x, rock.y, COLOR_RED)
                return True
        return False

    # ---------- heat ----------

    def _update_heat(self) -> None:
        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER
            self._game_over_timer = 60
            return
        self.heat = max(0.0, self.heat - 0.05)

    def _check_bank_collision(self) -> None:
        margin = 6.0
        if self.kayak_x <= RIVER_LEFT + margin or self.kayak_x >= RIVER_RIGHT - margin:
            self.heat = min(MAX_HEAT, self.heat + 5.0)
            self.kayak_x = max(RIVER_LEFT + margin, min(RIVER_RIGHT - margin, self.kayak_x))

    # ---------- super ----------

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1

    # ---------- particles ----------

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0.0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.5)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=20 + self._rng.randint(0, 10),
                color=color,
                size=2,
            ))

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _spawn_floating_text(self, text: str, x: float, y: float, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=30, color=color, vy=-1.0))

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    # ---------- scrolling & spawning ----------

    def _scroll_river(self) -> None:
        for gate in self.gates[:]:
            gate.y += self.scroll_speed
            if gate.y > SCREEN_H + 40:
                self.gates.remove(gate)

        for rock in self.rocks[:]:
            rock.y += self.scroll_speed
            if rock.y > SCREEN_H + 40:
                self.rocks.remove(rock)

        self.distance += self.scroll_speed
        self.scroll_speed = SCROLL_SPEED_BASE + self.distance / 5000.0

    def _spawn_entities(self) -> None:
        self._gate_timer += 1
        interval = max(60.0, GATE_SPAWN_INTERVAL - self.distance / 50.0)
        if self._gate_timer >= int(interval):
            self._gate_timer = 0
            self._spawn_gate()
            if self._rng.random() < 0.4:
                rx = self._rng.uniform(RIVER_LEFT + 15.0, RIVER_RIGHT - 15.0)
                self.rocks.append(Rock(x=rx, y=-15.0, radius=8.0 + self._rng.randint(0, 4)))

    # ---------- drawing ----------

    def _draw_title(self) -> None:
        pyxel.cls(COLOR_NAVY)
        pyxel.text(90, 60, "PADDLE SURGE", COLOR_WHITE)
        pyxel.text(85, 80, "Kayak Slalom", 6)
        pyxel.text(70, 120, "Arrow Keys: Move", COLOR_WHITE)
        pyxel.text(50, 135, "Match kayak color to gates", COLOR_WHITE)
        pyxel.text(50, 150, "for COMBO chains!", COLOR_WHITE)
        pyxel.text(60, 180, "COMBO x4 = SUPER SURGE!", COLOR_YELLOW)
        pyxel.text(85, 210, "Press SPACE to start", COLOR_CYAN)

    def _draw_playing(self) -> None:
        pyxel.cls(COLOR_NAVY)

        pyxel.rect(0, 0, RIVER_LEFT, SCREEN_H, COLOR_DARK_BLUE)
        pyxel.rect(RIVER_RIGHT, 0, SCREEN_W - RIVER_RIGHT, SCREEN_H, COLOR_DARK_BLUE)
        pyxel.rect(RIVER_LEFT, 0, RIVER_WIDTH, SCREEN_H, COLOR_PURPLE)

        for rock in self.rocks:
            pyxel.circ(int(rock.x), int(rock.y), int(rock.radius), COLOR_GRAY)
            pyxel.circb(int(rock.x), int(rock.y), int(rock.radius), COLOR_DARK_BLUE)

        for gate in self.gates:
            color_val = GATE_COLOR_VALS[gate.color.value]
            left_x = gate.x - gate.width / 2.0 - gate.pole_w / 2.0
            pyxel.rect(int(left_x), int(gate.y), int(gate.pole_w), int(gate.pole_h), color_val)
            right_x = gate.x + gate.width / 2.0 - gate.pole_w / 2.0
            pyxel.rect(int(right_x), int(gate.y), int(gate.pole_w), int(gate.pole_h), color_val)
            pyxel.rect(int(left_x), int(gate.y), int(gate.width + gate.pole_w), 3, color_val)

        kayak_color_val: int
        if self.super_timer > 0 and (pyxel.frame_count // 4) % 2 == 0:
            kayak_color_val = COLOR_WHITE
        else:
            kayak_color_val = GATE_COLOR_VALS[self.kayak_color.value]

        kx = int(self.kayak_x)
        ky = int(self.kayak_y)
        pyxel.tri(kx, ky - 8, kx - 6, ky + 4, kx + 6, ky + 4, kayak_color_val)
        pyxel.trib(kx, ky - 8, kx - 6, ky + 4, kx + 6, ky + 4, COLOR_WHITE)

        if self.super_timer > 0:
            aura_r = 10 + (pyxel.frame_count % 8)
            pyxel.circb(kx, ky, aura_r, COLOR_YELLOW)
            pyxel.circb(kx, ky, aura_r + 2, COLOR_RED)

        for p in self.particles:
            alpha = p.life / 30.0
            col = p.color if alpha > 0.5 else COLOR_GRAY
            pyxel.rect(int(p.x), int(p.y), p.size, p.size, col)

        for ft in self.floating_texts:
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

        pyxel.rect(0, 0, SCREEN_W, 16, COLOR_BLACK)
        pyxel.text(4, 4, f"SCORE:{self.score:06d}", COLOR_WHITE)
        combo_col = COLOR_YELLOW if self.combo > 0 else COLOR_WHITE
        pyxel.text(110, 4, f"COMBO:x{self.combo}", combo_col)
        pyxel.text(210, 4, f"DIST:{int(self.distance):04d}", 6)

        bar_x, bar_y = 4, SCREEN_H - 12
        bar_w = 100
        pyxel.rect(bar_x, bar_y, bar_w, 6, COLOR_DARK_BLUE)
        heat_w = int(bar_w * self.heat / MAX_HEAT)
        if self.heat < 50:
            heat_col = COLOR_GREEN
        elif self.heat < 80:
            heat_col = COLOR_ORANGE
        else:
            heat_col = COLOR_RED
        pyxel.rect(bar_x, bar_y, heat_w, 6, heat_col)
        pyxel.text(bar_x, bar_y - 7, "HEAT", COLOR_WHITE)

        if self.super_timer > 0:
            remain_sec = self.super_timer / 60.0
            pyxel.text(120, SCREEN_H - 20, f"SUPER! {remain_sec:.1f}s", COLOR_YELLOW)

    def _draw_game_over(self) -> None:
        pyxel.cls(COLOR_NAVY)
        pyxel.text(110, 60, "GAME OVER", COLOR_RED)
        pyxel.text(60, 90, f"SCORE: {self.score:06d}", COLOR_WHITE)
        pyxel.text(60, 110, f"MAX COMBO: x{self.max_combo}", COLOR_YELLOW)
        pyxel.text(60, 130, f"DISTANCE: {int(self.distance)}", 6)
        pyxel.text(70, 180, "Press SPACE to retry", COLOR_CYAN)


def main() -> None:
    pyxel.init(SCREEN_W, SCREEN_H, title="PADDLE SURGE", display_scale=2)
    game = Game()
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
