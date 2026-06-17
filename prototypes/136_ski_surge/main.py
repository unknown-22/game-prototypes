import pyxel
import random
from dataclasses import dataclass
from enum import Enum, auto


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Gate:
    x: float
    y: float
    color: int
    width: int = 30
    passed: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


SCREEN_W = 320
SCREEN_H = 240
GATE_COLORS_COUNT = 4
GATE_WIDTH = 30
GATE_SPACING_X = 120
GATE_SPAWN_X = 340
SKIER_X = 80
SKIER_W = 16
SKIER_H = 24
SKIER_SPEED = 3
SCROLL_SPEED = 2
COMBO_THRESHOLD = 5
SUPER_DURATION = 300
HEAT_MAX = 100.0
HEAT_PER_WRONG = 15.0
HEAT_PER_FRAME = 0.05
HEAT_DECAY = 0.1
SCORE_BASE = 10

GATE_COLORS = [8, 11, 6, 10]  # RED, LIME, LIGHT_BLUE, YELLOW


class Game:
    def __init__(self):
        pyxel.init(SCREEN_W, SCREEN_H, title="SKI SURGE", display_scale=2)
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self):
        self.phase = Phase.TITLE
        self.skier_y: float = SCREEN_H // 2
        self.skier_color: int = 0
        self.gates: list[Gate] = []
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.heat: float = 0.0
        self.super_timer: int = 0
        self.super_mode: bool = False
        self.scroll_x: float = 0.0
        self.scroll_speed: float = SCROLL_SPEED
        self.particles: list[Particle] = []
        self._spawn_gates_initial()

    def _spawn_gates_initial(self):
        for i in range(4):
            x = SCREEN_W + 20 + i * GATE_SPACING_X
            gate = self._make_gate(x)
            self.gates.append(gate)

    def _make_gate(self, x: float) -> Gate:
        color = self._rng.randint(0, GATE_COLORS_COUNT - 1)
        y = self._rng.uniform(40, SCREEN_H - 40)
        return Gate(x=x, y=y, color=color, width=GATE_WIDTH)

    def _spawn_gate(self):
        last_x = self.gates[-1].x if self.gates else SCREEN_W
        spawn_x = max(last_x + GATE_SPACING_X, SCREEN_W + 20)
        self.gates.append(self._make_gate(spawn_x))

    def update(self):
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_input()
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self):
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.PLAYING
            self._spawn_gates_initial()

    def _update_game_over(self):
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.PLAYING
            self._spawn_gates_initial()

    def _update_input(self):
        if pyxel.btn(pyxel.KEY_UP):
            self.skier_y -= SKIER_SPEED
        if pyxel.btn(pyxel.KEY_DOWN):
            self.skier_y += SKIER_SPEED
        half_h = SKIER_H / 2
        self.skier_y = max(half_h, min(SCREEN_H - half_h, self.skier_y))

    def _update_playing(self):
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0

        self.scroll_x += self.scroll_speed

        for gate in self.gates:
            gate.x -= self.scroll_speed

        for gate in self.gates:
            if not gate.passed:
                if self._check_gate_pass(gate):
                    gate.passed = True
                    self._handle_gate_pass(gate)

        self.gates = [g for g in self.gates if g.x > -50]

        if len(self.gates) < 5:
            next_check = self.gates[-1].x if self.gates else SCREEN_W
            if next_check < GATE_SPAWN_X - GATE_SPACING_X:
                self._spawn_gate()

        self._update_heat()
        self._update_particles()

    def _check_gate_pass(self, gate: Gate) -> bool:
        half_w = SKIER_W / 2
        skier_right = SKIER_X + half_w
        skier_left = SKIER_X - half_w
        gate_left = gate.x - gate.width
        gate_right = gate.x + gate.width
        if skier_right < gate_left or skier_left > gate_right:
            return False
        half_h = SKIER_H / 2
        skier_top = self.skier_y - half_h
        skier_bottom = self.skier_y + half_h
        gate_top = gate.y - gate.width
        gate_bottom = gate.y + gate.width
        if skier_bottom < gate_top or skier_top > gate_bottom:
            return False
        return True

    def _handle_gate_pass(self, gate: Gate):
        if self.super_mode:
            pts = int(SCORE_BASE * (1 + self.combo * 0.5) * 3)
            self.score += pts
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            self._add_particles(gate.x, gate.y, gate.color, 12)
            return

        if gate.color == self.skier_color:
            pts = int(SCORE_BASE * (1 + self.combo * 0.5))
            self.score += pts
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            self.heat = max(0.0, self.heat - HEAT_DECAY)
            if self.combo >= COMBO_THRESHOLD and not self.super_mode:
                self.super_mode = True
                self.super_timer = SUPER_DURATION
                self._add_particles(SKIER_X, self.skier_y, GATE_COLORS[self._rng.randint(0, 3)], 20)
            else:
                self._add_particles(gate.x, gate.y, gate.color, 8)
        else:
            self.combo = 0
            self.skier_color = gate.color
            self.heat += HEAT_PER_WRONG
            self._add_particles(gate.x, gate.y, gate.color, 4)

    def _update_heat(self):
        self.heat += HEAT_PER_FRAME
        if self.heat >= HEAT_MAX:
            self.heat = HEAT_MAX
            self.phase = Phase.GAME_OVER

    def _update_particles(self):
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def _add_particles(self, x: float, y: float, color: int, count: int):
        for _ in range(count):
            self.particles.append(Particle(
                x=x, y=y,
                vx=self._rng.uniform(-2, 2),
                vy=self._rng.uniform(-2, 2),
                life=self._rng.randint(10, 25),
                color=color,
            ))

    def draw(self):
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self):
        pyxel.cls(0)
        x = SCREEN_W // 2
        pyxel.text(x - len("SKI SURGE") * 2, 70, "SKI SURGE", 7)
        pyxel.text(x - len("PRESS ENTER") * 2, 130, "PRESS ENTER", 7)
        pyxel.text(x - len("UP/DOWN: steer") * 2, 160, "UP/DOWN: steer", 5)
        pyxel.text(x - len("Match gate colors") * 2, 180, "Match gate colors", 5)
        pyxel.text(x - len("Build combo for SURGE!") * 2, 195, "Build combo for SURGE!", 5)

    def _draw_playing(self):
        pyxel.cls(0)
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, 1)
        pyxel.rect(0, SCREEN_H - 20, SCREEN_W, 20, 5)

        for gate in self.gates:
            self._draw_gate(gate)

        self._draw_skier()

        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

        if self.super_mode:
            sec = self.super_timer // 60
            pyxel.text(SCREEN_W // 2 - 20, 40, f"SUPER {sec}s", 10)

        pyxel.text(4, 4, f"SCORE:{self.score}", 7)
        pyxel.text(SCREEN_W // 2 - 20, 4, f"COMBO:{self.combo}", 7)
        pyxel.rect(4, 18, 60, 6, 0)
        bar_w = int(60 * (self.heat / HEAT_MAX))
        heat_col = 8 if self.heat > 70 else 10 if self.heat > 40 else 11
        pyxel.rect(4, 18, bar_w, 6, heat_col)

    def _draw_skier(self):
        x = int(SKIER_X)
        y = int(self.skier_y)
        color = GATE_COLORS[self.skier_color] if not self.super_mode else (pyxel.frame_count // 4 % len(GATE_COLORS))
        if isinstance(color, int):
            c = color
        else:
            c = GATE_COLORS[color]
        pyxel.tri(x, y - SKIER_H // 2, x - SKIER_W // 2, y + SKIER_H // 2, x + SKIER_W // 2, y + SKIER_H // 2, c)
        pyxel.rect(x - 2, y - SKIER_H // 2 - 4, 4, 6, 7)

    def _draw_game_over(self):
        pyxel.cls(0)
        x = SCREEN_W // 2
        pyxel.text(x - len("GAME OVER") * 2, 60, "GAME OVER", 8)
        pyxel.text(x - len(f"SCORE: {self.score}") * 2, 100, f"SCORE: {self.score}", 7)
        pyxel.text(x - len(f"MAX COMBO: {self.max_combo}") * 2, 120, f"MAX COMBO: {self.max_combo}", 7)
        pyxel.text(x - len("PRESS ENTER") * 2, 160, "PRESS ENTER", 7)
        pyxel.text(x - len("TO RETRY") * 2, 175, "TO RETRY", 5)

    def _draw_gate(self, gate: Gate):
        gx = int(gate.x)
        gy = int(gate.y)
        half = gate.width
        color = GATE_COLORS[gate.color]
        pyxel.rect(gx - half - 4, gy - half, 4, half * 2, color)
        pyxel.rect(gx + half, gy - half, 4, half * 2, color)
        pyxel.rect(gx - half + 4, gy - 2, half * 2 - 8, 4, color)


if __name__ == "__main__":
    Game()
