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

GATE_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
SCREEN_W = 320
SCREEN_H = 240
FPS = 60
PLAYER_MIN_X = 20
PLAYER_MAX_X = 300
PLAYER_MOVE_SPEED = 3.0
BASE_SCROLL_SPEED = 1.5
SCROLL_SPEED_INCREMENT = 0.3
SCROLL_SPEED_INTERVAL = 600
MAX_SCROLL_SPEED = 4.0
GATE_SPAWN_MIN = 60
GATE_SPAWN_MAX = 100
GATE_MIN_X = 60
GATE_MAX_X = 260
GATE_MIN_WIDTH = 40
GATE_MAX_WIDTH = 70
MAX_GATES = 6
OBSTACLE_SPAWN_MIN = 120
OBSTACLE_SPAWN_MAX = 200
MAX_OBSTACLES = 4
OBSTACLE_W = 16
OBSTACLE_H = 24
HEAT_MAX = 5.0
HEAT_PER_MISS = 1.2
HEAT_DECAY = 0.01
HEAT_PER_OBSTACLE = 2.0
SUPER_COMBO_THRESHOLD = 5
SUPER_DURATION = 300
SUPER_SCORE_MULTIPLIER = 3
GATE_BASE_SCORE = 10
POLE_W = 6
POLE_H = 40
BOTTOM_BAR_H = 4
GATE_SPAWN_Y = 250
GATE_OFFSCREEN_Y = -50
PLAYER_Y = 160
PLAYER_W = 12
PLAYER_H = 16
MAX_GHOST_POINTS = 200
GHOST_RECORD_INTERVAL = 3


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Gate:
    x: float
    y: float
    color: int
    width: float
    passed: bool = False
    pole_w: int = 6


@dataclass
class Obstacle:
    x: float
    y: float
    w: float
    h: float
    color: int


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


@dataclass
class GhostPoint:
    x: float
    y: float


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Slope Surge", fps=FPS, display_scale=2)
        self._rng: random.Random = random.Random()
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.scroll_speed: float = BASE_SCROLL_SPEED
        self.player_x: float = 160.0
        self.player_y: float = float(PLAYER_Y)
        self.player_w: int = PLAYER_W
        self.player_h: int = PLAYER_H
        self.last_gate_color: int | None = None
        self.gates: list[Gate] = []
        self.obstacles: list[Obstacle] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.ghost_trail: list[GhostPoint] = []
        self.best_ghost: list[GhostPoint] = []
        self.best_score: int = 0
        self.game_timer: int = 0
        self._gate_spawn_timer: int = 0
        self._obstacle_spawn_timer: int = 0
        self._ghost_record_timer: int = 0
        self._rainbow_idx: int = 0
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_mode = False
        self.super_timer = 0
        self.scroll_speed = BASE_SCROLL_SPEED
        self.player_x = 160.0
        self.last_gate_color = None
        self.gates.clear()
        self.obstacles.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.ghost_trail.clear()
        self.game_timer = 0
        self._gate_spawn_timer = 0
        self._obstacle_spawn_timer = 0
        self._ghost_record_timer = 0
        self._rainbow_idx = 0

    def _spawn_gate(self) -> None:
        if len(self.gates) >= MAX_GATES:
            return
        color = self._rng.choice(GATE_COLORS)
        x = self._rng.uniform(GATE_MIN_X, GATE_MAX_X)
        width = self._rng.uniform(GATE_MIN_WIDTH, GATE_MAX_WIDTH)
        self.gates.append(Gate(x=x, y=float(GATE_SPAWN_Y), color=color, width=width))

    def _spawn_obstacle(self) -> None:
        if len(self.obstacles) >= MAX_OBSTACLES:
            return
        x = self._rng.uniform(40.0, 280.0)
        color = self._rng.choice([BROWN, GRAY])
        self.obstacles.append(Obstacle(x=x, y=float(GATE_SPAWN_Y), w=float(OBSTACLE_W), h=float(OBSTACLE_H), color=color))

    def _check_gate_pass(self, gate: Gate) -> bool:
        if gate.passed:
            return False
        player_top = PLAYER_Y - PLAYER_H / 2
        player_bottom = PLAYER_Y + PLAYER_H / 2
        gate_y = gate.y
        prev_player_bottom = player_bottom
        crossed = prev_player_bottom >= gate_y and player_top < gate_y
        if not crossed:
            return False
        return abs(self.player_x - gate.x) < gate.width / 2

    def _handle_gate_pass(self, gate: Gate) -> None:
        gate.passed = True
        same_color = self.last_gate_color is not None and gate.color == self.last_gate_color
        if same_color:
            self.combo += 1
            score_gain = GATE_BASE_SCORE * (self.combo + 1)
            if self.super_mode:
                score_gain *= SUPER_SCORE_MULTIPLIER
            self.score += int(score_gain)
        else:
            self.combo = 1
            score_gain = GATE_BASE_SCORE
            if self.super_mode:
                score_gain *= SUPER_SCORE_MULTIPLIER
            self.score += int(score_gain)
        self.max_combo = max(self.max_combo, self.combo)
        self.last_gate_color = gate.color
        self._spawn_gate_particles(gate.color)
        self.floating_texts.append(
            FloatingText(x=self.player_x, y=self.player_y - 10, text=f"+{int(score_gain)}", life=30, color=gate.color)
        )
        if self.combo >= 3:
            self.floating_texts.append(
                FloatingText(x=self.player_x, y=self.player_y - 20, text=f"x{self.combo}", life=25, color=gate.color)
            )
        if self.combo >= SUPER_COMBO_THRESHOLD and not self.super_mode:
            self._activate_super()

    def _handle_gate_miss(self, gate: Gate) -> None:
        gate.passed = True
        self.heat = min(HEAT_MAX, self.heat + HEAT_PER_MISS)
        self.combo = 0
        self.last_gate_color = None
        if self.super_mode:
            self._deactivate_super()
        self.floating_texts.append(
            FloatingText(x=self.player_x, y=self.player_y - 10, text="MISS!", life=30, color=RED)
        )

    def _check_obstacle_collision(self, obs: Obstacle) -> bool:
        return (
            self.player_x - PLAYER_W / 2 < obs.x + obs.w
            and self.player_x + PLAYER_W / 2 > obs.x
            and PLAYER_Y - PLAYER_H / 2 < obs.y + obs.h
            and PLAYER_Y + PLAYER_H / 2 > obs.y
        )

    def _handle_obstacle_collision(self, obs: Obstacle) -> None:
        if self.super_mode:
            return
        self.heat = min(HEAT_MAX, self.heat + HEAT_PER_OBSTACLE)
        self.combo = 0
        self.last_gate_color = None
        knock_dir = 1 if self.player_x <= obs.x + obs.w / 2 else -1
        self.player_x += knock_dir * 10
        self.player_x = max(PLAYER_MIN_X, min(PLAYER_MAX_X, self.player_x))
        self._spawn_obstacle_particles()
        self.floating_texts.append(
            FloatingText(x=self.player_x, y=self.player_y - 10, text="OUCH!", life=25, color=BROWN)
        )

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self.floating_texts.append(
            FloatingText(x=self.player_x, y=self.player_y - 30, text="SUPER!!", life=60, color=YELLOW)
        )
        for _ in range(20):
            angle = self._rng.uniform(0, 6.2832)
            speed = self._rng.uniform(1.0, 3.0)
            color = self._rng.choice(GATE_COLORS)
            self.particles.append(
                Particle(
                    x=self.player_x,
                    y=self.player_y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=self._rng.randint(15, 25),
                    color=color,
                )
            )

    def _deactivate_super(self) -> None:
        self.super_mode = False
        self.super_timer = 0
        self.combo = 0
        self.last_gate_color = None

    def _spawn_gate_particles(self, color: int) -> None:
        count = 12 if self.super_mode else 8
        for _ in range(count):
            angle = self._rng.uniform(0, 6.2832)
            speed = self._rng.uniform(0.5, 2.5)
            self.particles.append(
                Particle(
                    x=self.player_x,
                    y=self.player_y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=self._rng.randint(15, 25),
                    color=color,
                )
            )

    def _spawn_obstacle_particles(self) -> None:
        for _ in range(5):
            angle = self._rng.uniform(0, 6.2832)
            speed = self._rng.uniform(0.5, 1.5)
            self.particles.append(
                Particle(
                    x=self.player_x,
                    y=self.player_y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=self._rng.randint(10, 20),
                    color=BROWN,
                )
            )

    def _update_gates(self) -> None:
        for gate in self.gates:
            gate.y -= self.scroll_speed
        gates_to_process = [g for g in self.gates if not g.passed]
        for gate in gates_to_process:
            if not self.super_mode:
                passed = self._check_gate_pass(gate)
                if passed:
                    self._handle_gate_pass(gate)
            else:
                player_top = PLAYER_Y - PLAYER_H / 2
                player_bottom = PLAYER_Y + PLAYER_H / 2
                gate_y = gate.y
                prev_player_bottom = player_bottom
                crossed = prev_player_bottom >= gate_y and player_top < gate_y
                if crossed:
                    self._handle_gate_pass(gate)
        still_on_screen = [g for g in self.gates if not g.passed]
        for gate in still_on_screen:
            player_top = PLAYER_Y - PLAYER_H / 2
            player_bottom = PLAYER_Y + PLAYER_H / 2
            gate_y = gate.y
            prev_player_bottom = player_bottom
            crossed = prev_player_bottom >= gate_y and player_top < gate_y
            if crossed:
                self._handle_gate_miss(gate)
        self.gates = [g for g in self.gates if g.y > GATE_OFFSCREEN_Y]

    def _update_obstacles(self) -> None:
        for obs in self.obstacles:
            obs.y -= self.scroll_speed
        if not self.super_mode:
            for obs in self.obstacles:
                if self._check_obstacle_collision(obs):
                    self._handle_obstacle_collision(obs)
                    obs.y = -100
        self.obstacles = [o for o in self.obstacles if o.y > GATE_OFFSCREEN_Y]

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 1
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _update_heat(self) -> None:
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            if self.score > self.best_score:
                self.best_score = self.score
                self.best_ghost = list(self.ghost_trail)
            return
        if not self.super_mode:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _record_ghost_point(self) -> None:
        if len(self.ghost_trail) >= MAX_GHOST_POINTS:
            return
        self.ghost_trail.append(GhostPoint(x=self.player_x, y=self.player_y))

    def _update_scroll_speed(self) -> None:
        new_speed = BASE_SCROLL_SPEED + (self.game_timer // SCROLL_SPEED_INTERVAL) * SCROLL_SPEED_INCREMENT
        self.scroll_speed = min(MAX_SCROLL_SPEED, new_speed)

    def _update_spawning(self) -> None:
        self._gate_spawn_timer -= 1
        if self._gate_spawn_timer <= 0:
            self._spawn_gate()
            self._gate_spawn_timer = self._rng.randint(GATE_SPAWN_MIN, GATE_SPAWN_MAX)
        self._obstacle_spawn_timer -= 1
        if self._obstacle_spawn_timer <= 0:
            self._spawn_obstacle()
            self._obstacle_spawn_timer = self._rng.randint(OBSTACLE_SPAWN_MIN, OBSTACLE_SPAWN_MAX)

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        if self.phase == Phase.PLAYING:
            if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
                self.player_x -= PLAYER_MOVE_SPEED
            if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
                self.player_x += PLAYER_MOVE_SPEED
            self.player_x = max(PLAYER_MIN_X, min(PLAYER_MAX_X, self.player_x))

            self._update_scroll_speed()
            self._update_spawning()
            self._update_gates()
            self._update_obstacles()
            self._update_particles()
            self._update_floating_texts()
            self._update_heat()

            if self.super_mode:
                self.super_timer -= 1
                if self.super_timer <= 0:
                    self._deactivate_super()

            self._ghost_record_timer -= 1
            if self._ghost_record_timer <= 0:
                self._record_ghost_point()
                self._ghost_record_timer = GHOST_RECORD_INTERVAL

            self.game_timer += 1
            self._rainbow_idx = (self._rainbow_idx + 1) % len(GATE_COLORS)

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 40, 60, "SLOPE SURGE", WHITE)
        pyxel.text(SCREEN_W // 2 - 65, 120, "Arrow Keys: Move", GRAY)
        pyxel.text(SCREEN_W // 2 - 80, 130, "Same Color Gates = COMBO", GRAY)
        pyxel.text(SCREEN_W // 2 - 70, 150, "COMBO x5 => SUPER MODE!", GRAY)
        pyxel.text(SCREEN_W // 2 - 60, 170, "Avoid obstacles!", GRAY)
        pyxel.text(SCREEN_W // 2 - 65, 200, "Press SPACE to Start", WHITE)
        if self.best_score > 0:
            pyxel.text(SCREEN_W // 2 - 40, 220, f"BEST: {self.best_score}", YELLOW)

    def _draw_game(self) -> None:
        pyxel.cls(BLACK)
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, WHITE)
        for i in range(0, SCREEN_W, 4):
            pyxel.pset((i + pyxel.frame_count // 2 % 4) % SCREEN_W, 200, GRAY)
            pyxel.pset((i + pyxel.frame_count // 2 % 4 + 16) % SCREEN_W, 215, GRAY)

        self._draw_ghost()
        self._draw_obstacles()
        self._draw_gates()
        self._draw_player()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()
        if self.super_mode:
            self._draw_super_border()

    def _draw_gates(self) -> None:
        for gate in self.gates:
            left_x = gate.x - gate.width / 2 - gate.pole_w
            right_x = gate.x + gate.width / 2
            pyxel.rect(left_x, gate.y, gate.pole_w, POLE_H, gate.color)
            pyxel.rect(right_x, gate.y, gate.pole_w, POLE_H, gate.color)
            bar_y = gate.y + POLE_H
            pyxel.rect(left_x, bar_y, gate.width + gate.pole_w * 2, BOTTOM_BAR_H, gate.color)

    def _draw_player(self) -> None:
        px = int(self.player_x)
        py = int(self.player_y)
        if self.super_mode:
            player_color = GATE_COLORS[self._rainbow_idx]
        else:
            player_color = LIME
        pyxel.tri(px, py - 8, px - 6, py + 4, px + 6, py + 4, WHITE)
        pyxel.tri(px, py - 2, px - 4, py + 4, px + 4, py + 4, player_color)

    def _draw_obstacles(self) -> None:
        for obs in self.obstacles:
            ox = int(obs.x)
            oy = int(obs.y)
            ow = int(obs.w)
            oh = int(obs.h)
            pyxel.rect(ox - ow // 2, oy - oh, ow, oh, obs.color)
            pyxel.tri(ox - ow // 2 - 3, oy, ox, oy - 8, ox + ow // 2 + 3, oy, obs.color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.circ(int(p.x), int(p.y), p.size, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_ghost(self) -> None:
        if not self.best_ghost:
            return
        for i, gp in enumerate(self.best_ghost):
            if i % 2 == 0:
                pyxel.pset(int(gp.x), int(gp.y), GRAY)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", BLACK)
        if self.combo >= 2:
            pyxel.text(4, 14, f"COMBO: x{self.combo}", RED)
        heat_width = int((self.heat / HEAT_MAX) * 100)
        bar_x = 4
        bar_y = 22
        bar_w = 100
        bar_h = 6
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        if self.heat < HEAT_MAX / 3:
            heat_color = GREEN
        elif self.heat < HEAT_MAX * 2 / 3:
            heat_color = YELLOW
        else:
            heat_color = RED
        pyxel.rect(bar_x, bar_y, min(heat_width, bar_w), bar_h, heat_color)
        pyxel.text(SCREEN_W - 60, 4, f"TIME: {self.game_timer // FPS}s", BLACK)

    def _draw_super_border(self) -> None:
        border_color = GATE_COLORS[self._rainbow_idx]
        for i in range(4):
            if i % 2 == 0:
                pyxel.rect(0, 0 + i, SCREEN_W, 1, border_color)
                pyxel.rect(0, SCREEN_H - 1 - i, SCREEN_W, 1, border_color)
        pyxel.text(SCREEN_W // 2 - 20, 35, "SUPER!", YELLOW)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 25, 60, "GAME OVER", WHITE)
        pyxel.text(SCREEN_W // 2 - 30, 100, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 30, 120, f"BEST: {self.best_score}", YELLOW)
        pyxel.text(SCREEN_W // 2 - 40, 140, f"MAX COMBO: x{self.max_combo}", WHITE)
        if self.heat >= HEAT_MAX:
            pyxel.text(SCREEN_W // 2 - 35, 160, "HEAT OVERLOAD!", RED)
        pyxel.text(SCREEN_W // 2 - 55, 200, "Press SPACE to Retry", GRAY)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
