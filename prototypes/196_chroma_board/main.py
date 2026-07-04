"""CHROMA BOARD — Side-scrolling downhill snowboarding game.
Auto-scroll mountain with slalom gates in 4 colors, obstacles to avoid,
and a color-match COMBO chain system. Race down the mountain for 60 seconds!

Most Fun Moment: Racing downhill at high speed, threading through same-color
gates building a massive COMBO chain, then triggering SUPER BOARD mode for a
rainbow explosion of points while smashing through everything.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

SCREEN_W = 320
SCREEN_H = 240

SCROLL_SPEED = 2.0
GRAVITY = 0.5
JUMP_VEL = -7.0
PLAYER_X = 80
GROUND_Y = 190

GATE_W = 40
GATE_GAP = 50
GATE_H = 60
GATE_SPAWN_INTERVAL = 90

COMBO_THRESHOLD = 4
SUPER_DURATION = 240

HEAT_MAX = 100.0
HEAT_DECAY = 0.05
HEAT_PER_SECOND = 0.3
HEAT_PER_OBSTACLE = 15.0

GAME_TIME = 3600

OBSTACLE_SPAWN_INTERVAL = 60
MAX_PARTICLES = 80

RED = 0
GREEN = 1
BLUE = 2
YELLOW = 3

COLOR_NAMES = {RED: "RED", GREEN: "GREEN", BLUE: "BLUE", YELLOW: "YELLOW"}
PYXEL_COLORS = {RED: 8, GREEN: 3, BLUE: 6, YELLOW: 10}

C_SKY = 5
C_SNOW_TOP = 7
C_SNOW_SHADOW = 13
C_PLAYER_BODY = 7
C_PLAYER_BOARD = 5
C_PLAYER_OUTLINE = 0
C_HUD_BG = 0
C_TEXT = 7
C_BLUE = 6
C_YELLOW = 10
C_HEAT_LOW = 3
C_HEAT_MID = 10
C_HEAT_HIGH = 8
C_OBSTACLE = 4
C_TREE = 3
C_BROWN = 4
C_WHITE = 7
C_BLACK = 0
C_LIME = 11
C_GRAY = 13


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Gate:
    x: float
    y: float
    color: int
    scored: bool = False


@dataclass
class Obstacle:
    x: float
    y: float
    w: int
    h: int
    obs_type: str


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


@dataclass
class FloatText:
    x: float
    y: float
    text: str
    color: int
    life: int


@dataclass
class Player:
    x: float = float(PLAYER_X)
    y: float = float(GROUND_Y)
    vy: float = 0.0
    on_ground: bool = True
    color: int = -1
    combo: int = 0
    max_combo: int = 0
    super_timer: int = 0
    heat: float = 0.0


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CHROMA BOARD", display_scale=2)
        self._pre_init_attrs()
        self.reset()

        self.frame: int = 0
        self.best_score: int = 0
        self.best_max_combo: int = 0
        self.ghost_gates: list[tuple[float, float, int]] = []

        pyxel.run(self._update, self._draw)

    def _pre_init_attrs(self) -> None:
        self.random: random.Random = random.Random()
        self.phase: Phase = Phase.TITLE
        self.player: Player = Player()
        self.gates: list[Gate] = []
        self.obstacles: list[Obstacle] = []
        self.particles: list[Particle] = []
        self.float_texts: list[FloatText] = []
        self.timer: int = GAME_TIME
        self.score: int = 0
        self.gate_spawn_timer: int = 0
        self.obstacle_spawn_timer: int = 0
        self.scroll_speed: float = SCROLL_SPEED

    def reset(self) -> None:
        self.player = Player()
        self.gates.clear()
        self.obstacles.clear()
        self.particles.clear()
        self.float_texts.clear()
        self.timer = GAME_TIME
        self.score = 0
        self.gate_spawn_timer = 0
        self.obstacle_spawn_timer = 0
        self.scroll_speed = SCROLL_SPEED

    def _update(self) -> None:
        self.frame += 1
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self._update_player_input()
        self._update_player_physics()
        self._update_speed()
        self._update_spawning()
        self._update_positions()
        self._check_all_collisions()
        self._update_heat()
        self._update_super()
        self._update_particles()
        self._update_floating_texts()
        self._update_timer()

    def _update_player_input(self) -> None:
        p = self.player
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            p.x -= 3.0
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            p.x += 3.0
        if p.on_ground and (
            pyxel.btnp(pyxel.KEY_SPACE)
            or pyxel.btnp(pyxel.KEY_UP)
            or pyxel.btnp(pyxel.KEY_W)
        ):
            p.vy = JUMP_VEL
            p.on_ground = False
        p.x = max(10.0, min(float(SCREEN_W - 10), p.x))

    def _update_player_physics(self) -> None:
        p = self.player
        if not p.on_ground:
            p.vy += GRAVITY
            p.y += p.vy
            if p.y >= GROUND_Y:
                p.y = float(GROUND_Y)
                p.vy = 0.0
                p.on_ground = True

    def _update_speed(self) -> None:
        elapsed = (GAME_TIME - self.timer) / 60.0
        self.scroll_speed = SCROLL_SPEED + (elapsed / 20.0) * 2.0

    def _update_spawning(self) -> None:
        self.gate_spawn_timer -= 1
        if self.gate_spawn_timer <= 0:
            self._spawn_gate()
            self.gate_spawn_timer = GATE_SPAWN_INTERVAL

        self.obstacle_spawn_timer -= 1
        if self.obstacle_spawn_timer <= 0:
            self._spawn_obstacle()
            self.obstacle_spawn_timer = OBSTACLE_SPAWN_INTERVAL

    def _spawn_gate(self) -> None:
        color = self.random.randint(0, 3)
        y = GROUND_Y - GATE_GAP // 2 + self.random.randint(-20, 20)
        y = max(float(GATE_GAP // 2 + 10), min(float(SCREEN_H - 40), y))
        gate = Gate(x=float(SCREEN_W + GATE_W), y=y, color=color)
        self.gates.append(gate)

    def _spawn_obstacle(self) -> None:
        obs_type = self.random.choice(["rock", "tree"])
        if obs_type == "rock":
            w = self.random.randint(12, 20)
            h = self.random.randint(10, 16)
        else:
            w = self.random.randint(14, 22)
            h = self.random.randint(20, 30)
        x = float(SCREEN_W + w)
        y = float(GROUND_Y - h)
        obs = Obstacle(x=x, y=y, w=w, h=h, obs_type=obs_type)
        self.obstacles.append(obs)

    def _update_positions(self) -> None:
        speed = self.scroll_speed
        for gate in self.gates:
            gate.x -= speed
        for obs in self.obstacles:
            obs.x -= speed

        self.gates = [g for g in self.gates if g.x > -GATE_W * 2]
        self.obstacles = [o for o in self.obstacles if o.x > -60]

    def _check_all_collisions(self) -> None:
        p = self.player
        for gate in self.gates:
            if gate.scored:
                continue
            if self._check_gate_collision(p, gate):
                gate.scored = True
                self._process_gate_pass(gate)

        for obs in self.obstacles:
            if self._check_obstacle_collision(p, obs):
                self._process_obstacle_hit(obs)

    def _check_gate_collision(self, p: Player, gate: Gate) -> bool:
        left_edge = gate.x - GATE_W
        right_edge = gate.x
        gap_top = gate.y - GATE_GAP // 2
        gap_bottom = gate.y + GATE_GAP // 2

        player_left = p.x - 6
        player_right = p.x + 6
        player_top = p.y - 10
        player_bottom = p.y + 2

        if player_right > left_edge and player_left < right_edge:
            if player_top < gap_bottom and player_bottom > gap_top:
                if p.y - 4 > gap_top and p.y - 4 < gap_bottom:
                    return True
        return False

    def _check_obstacle_collision(self, p: Player, obs: Obstacle) -> bool:
        if self.player.super_timer > 0:
            return False
        player_left = p.x - 6
        player_right = p.x + 6
        player_top = p.y - 10
        player_bottom = p.y + 2

        return (
            player_right > obs.x - obs.w // 2
            and player_left < obs.x + obs.w // 2
            and player_bottom > obs.y
            and player_top < obs.y + obs.h
        )

    def _process_gate_pass(self, gate: Gate) -> None:
        p = self.player
        is_super = p.super_timer > 0

        if is_super or p.color < 0:
            p.combo += 1
        elif gate.color == p.color:
            p.combo += 1
        else:
            p.combo = 0

        p.color = gate.color
        p.max_combo = max(p.max_combo, p.combo)

        multiplier = 3 if is_super else 1
        points = 100 * p.combo * multiplier
        self.score += points

        text_color = PYXEL_COLORS.get(gate.color, C_WHITE)
        if is_super:
            text = f"+{points} SUPER!"
        elif p.combo >= 2:
            text = f"+{points} x{p.combo}"
        else:
            text = f"+{points}"
        self._spawn_float_text(gate.x, gate.y - 10, text, text_color)

        self._spawn_particles(gate.x, gate.y, PYXEL_COLORS.get(gate.color, C_WHITE), 8)

        if p.combo >= COMBO_THRESHOLD and p.super_timer <= 0:
            p.super_timer = SUPER_DURATION
            self._spawn_particles(p.x, p.y, C_WHITE, 20)

    def _process_obstacle_hit(self, obs: Obstacle) -> None:
        p = self.player
        if p.super_timer > 0:
            self._spawn_particles(obs.x, obs.y + obs.h // 2, C_LIME, 10)
            self.obstacles.remove(obs)
            self.score += 50
            self._spawn_float_text(obs.x, obs.y, "+50 SMASH!", C_LIME)
            return

        p.heat += HEAT_PER_OBSTACLE

        color = C_BROWN if obs.obs_type == "rock" else C_TREE
        self._spawn_particles(obs.x, obs.y + obs.h // 2, color, 10)
        self._spawn_float_text(obs.x, obs.y, "+15 HEAT!", C_HEAT_HIGH)

        p.vy = JUMP_VEL * 0.5
        p.on_ground = False

    def _update_heat(self) -> None:
        p = self.player
        p.heat += HEAT_PER_SECOND
        p.heat -= HEAT_DECAY
        if p.heat < 0:
            p.heat = 0
        if p.heat >= HEAT_MAX:
            p.heat = HEAT_MAX
            self._end_game()

    def _update_super(self) -> None:
        p = self.player
        if p.super_timer > 0:
            p.super_timer -= 1
            if p.super_timer <= 0:
                p.super_timer = 0
                p.combo = 0

    def _update_timer(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self._end_game()

    def _end_game(self) -> None:
        p = self.player
        if self.score > self.best_score:
            self.best_score = self.score
            self.best_max_combo = p.max_combo
            self.ghost_gates = [(g.x, g.y, g.color) for g in self.gates]
        self.phase = Phase.GAME_OVER

    def _update_particles(self) -> None:
        for pt in self.particles:
            pt.x += pt.vx
            pt.y += pt.vy
            pt.vy += 0.2
            pt.life -= 1
        self.particles = [pt for pt in self.particles if pt.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.float_texts:
            ft.y -= 1.0
            ft.life -= 1
        self.float_texts = [ft for ft in self.float_texts if ft.life > 0]

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        max_new = MAX_PARTICLES - len(self.particles)
        if max_new <= 0:
            return
        count = min(count, max_new)
        for _ in range(count):
            angle = self.random.uniform(0, 2 * math.pi)
            speed = self.random.uniform(0.5, 3.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 1.0
            life = self.random.randint(10, 25)
            self.particles.append(
                Particle(x=x, y=y, vx=vx, vy=vy, color=color, life=life)
            )

    def _spawn_float_text(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        self.float_texts.append(
            FloatText(x=x, y=y, text=text, color=color, life=40)
        )

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.TITLE

    def _draw(self) -> None:
        pyxel.cls(C_SKY)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        self._draw_bg_mountain()
        self._draw_centered_text("CHROMA BOARD", 60, C_WHITE)
        self._draw_centered_text("Snowboard through same-color gates!", 90, C_TEXT)
        self._draw_centered_text("COMBO x4 = SUPER BOARD!", 105, C_YELLOW)
        self._draw_centered_text("A/D or Arrows: Move", 135, C_TEXT)
        self._draw_centered_text("SPACE/UP/W: Jump", 150, C_TEXT)
        self._draw_centered_text("Press SPACE to start", 190, C_LIME)

    def _draw_playing(self) -> None:
        self._draw_bg_mountain()
        self._draw_gates()
        self._draw_obstacles()
        self._draw_ghost_gates()
        self._draw_player()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_game_over(self) -> None:
        pyxel.cls(C_BLACK)
        self._draw_centered_text("GAME OVER", 60, C_HEAT_HIGH)
        self._draw_centered_text(f"Score: {self.score}", 100, C_WHITE)
        self._draw_centered_text(f"Max Combo: {self.player.max_combo}", 115, C_WHITE)
        self._draw_centered_text(f"Best Score: {self.best_score}", 140, C_LIME)
        self._draw_centered_text(
            f"Best Max Combo: {self.best_max_combo}", 155, C_LIME
        )
        self._draw_centered_text("Press SPACE to restart", 190, C_WHITE)

    def _draw_centered_text(self, text: str, y: int, col: int) -> None:
        x = (SCREEN_W - len(text) * 4) // 2
        pyxel.text(x, y, text, col)

    def _draw_bg_mountain(self) -> None:
        for i in range(16):
            peak_x = 20 + i * 20 + math.sin(self.frame * 0.02 + i * 0.5) * 10
            peak_y = 30 + math.sin(i * 1.3) * 10
            pyxel.tri(
                float(peak_x),
                float(peak_y),
                float(peak_x) - 30.0,
                130.0,
                float(peak_x) + 30.0,
                130.0,
                C_SNOW_SHADOW,
            )

        for i in range(0, SCREEN_W + 20, 20):
            offset = i + (self.frame * self.scroll_speed * 0.3) % 20
            pyxel.tri(
                float(offset),
                float(GROUND_Y),
                float(offset - 20),
                float(SCREEN_H),
                float(offset + 20),
                float(SCREEN_H),
                C_SNOW_SHADOW,
            )

        pyxel.rect(0, GROUND_Y - 5, SCREEN_W, 5, C_SNOW_TOP)

        for i in range(0, SCREEN_W + 40, 40):
            offset = i + (self.frame * -self.scroll_speed * 0.5) % 40
            pyxel.rect(float(offset), float(GROUND_Y - 8), 15.0, 3.0, C_SNOW_TOP)

    def _draw_gates(self) -> None:
        for gate in self.gates:
            color = PYXEL_COLORS.get(gate.color, C_WHITE)
            left = gate.x - GATE_W

            top_rect_h = gate.y - GATE_GAP // 2
            if top_rect_h > 0:
                pyxel.rect(left, 0, GATE_W, top_rect_h, color)
            bottom_rect_y = gate.y + GATE_GAP // 2
            bottom_rect_h = SCREEN_H - bottom_rect_y
            if bottom_rect_h > 0:
                pyxel.rect(left, bottom_rect_y, GATE_W, bottom_rect_h, color)

            pyxel.rectb(left - 1, gate.y - GATE_GAP // 2 - 1, GATE_W + 2, 2, C_WHITE)
            pyxel.rectb(
                left - 1,
                gate.y + GATE_GAP // 2 - 1,
                GATE_W + 2,
                2,
                C_WHITE,
            )

    def _draw_obstacles(self) -> None:
        for obs in self.obstacles:
            if obs.obs_type == "rock":
                pyxel.rect(
                    obs.x - obs.w // 2,
                    obs.y,
                    obs.w,
                    obs.h,
                    C_BROWN,
                )
                pyxel.rectb(
                    obs.x - obs.w // 2,
                    obs.y,
                    obs.w,
                    obs.h,
                    C_BLACK,
                )
            else:
                x = obs.x
                base_y = obs.y + obs.h
                pyxel.tri(
                    x,
                    obs.y,
                    x - obs.w // 2,
                    base_y,
                    x + obs.w // 2,
                    base_y,
                    C_TREE,
                )
                pyxel.rect(
                    x - 2,
                    base_y - obs.h // 3,
                    4,
                    obs.h // 3,
                    C_BROWN,
                )

    def _draw_ghost_gates(self) -> None:
        for gx, gy, gc in self.ghost_gates:
            color = PYXEL_COLORS.get(gc, C_GRAY)
            left = gx - GATE_W
            pyxel.rectb(left - 1, gy - GATE_GAP // 2 - 1, GATE_W + 2, 2, color)
            pyxel.rectb(left - 1, gy + GATE_GAP // 2 - 1, GATE_W + 2, 2, color)

    def _draw_player(self) -> None:
        p = self.player
        x = p.x
        y = p.y

        if p.super_timer > 0:
            rainbow_colors = [C_HEAT_HIGH, C_LIME, C_BLUE, C_YELLOW]
            main_color = rainbow_colors[(self.frame // 4) % len(rainbow_colors)]
            for i in range(3):
                px = x + self.random.uniform(-2, 2)
                py = y + self.random.uniform(-2, 2)
                pc = rainbow_colors[self.random.randint(0, 3)]
                pyxel.circ(px, py, 1, pc)
        else:
            main_color = C_SNOW_TOP

        pyxel.tri(x, y - 12, x - 5, y, x + 5, y, main_color)
        pyxel.tri(x, y - 12, x - 5, y, x + 5, y, C_PLAYER_OUTLINE)
        pyxel.rect(x - 4, y - 6, 8, 4, C_PLAYER_BODY)

        pyxel.rect(x - 7, y, 14, 2, C_PLAYER_BOARD)
        pyxel.rect(x - 7, y - 2, 2, 2, C_PLAYER_BOARD)
        pyxel.rect(x + 5, y - 2, 2, 2, C_PLAYER_BOARD)

    def _draw_particles(self) -> None:
        for pt in self.particles:
            if pt.life > 0:
                pyxel.pset(pt.x, pt.y, pt.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.float_texts:
            if ft.life > 0:
                pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, 20, C_HUD_BG)

        score_text = f"SCORE: {self.score}"
        pyxel.text(4, 6, score_text, C_TEXT)

        combo_text = f"COMBO: x{self.player.combo}"
        pyxel.text(80, 6, combo_text, PYXEL_COLORS.get(self.player.color, C_TEXT))

        p = self.player
        heat_bar_x = 155
        heat_bar_w = 60
        pyxel.rectb(heat_bar_x, 4, heat_bar_w, 10, C_TEXT)
        heat_fill = int((p.heat / HEAT_MAX) * (heat_bar_w - 2))
        if p.heat > 70:
            heat_color = C_HEAT_HIGH
        elif p.heat > 40:
            heat_color = C_HEAT_MID
        else:
            heat_color = C_HEAT_LOW
        pyxel.rect(heat_bar_x + 1, 5, heat_fill, 8, heat_color)

        heat_label = f"H:{int(p.heat)}"
        pyxel.text(heat_bar_x + heat_bar_w + 3, 6, heat_label, C_TEXT)

        seconds = self.timer // 60
        timer_text = f"T:{seconds:02d}"
        timer_color = C_HEAT_HIGH if seconds <= 10 else C_TEXT
        pyxel.text(SCREEN_W - 35, 6, timer_text, timer_color)

        if p.super_timer > 0:
            super_left = p.super_timer // 60
            pyxel.text(4, 16, f"SUPER BOARD! {super_left}s", C_LIME)


if __name__ == "__main__":
    Game()
