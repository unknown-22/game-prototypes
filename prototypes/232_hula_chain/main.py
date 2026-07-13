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

HOOP_COLORS = (RED, LIME, DARK_BLUE, YELLOW)
SCREEN_W = 320
SCREEN_H = 240
PLAYER_X = 160
PLAYER_Y = 140
HOOP_RADIUS = 60
PLAYER_RADIUS = 12
GEM_RADIUS = 4
MAX_HEAT = 100
GAME_TIME = 3600  # 60s at 60fps
SUPER_DURATION = 300


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Gem:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    active: bool = True


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
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="HULA CHAIN", fps=60)
        self._seed_rng = random.Random(42)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.best_score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat: float = 0.0
        self.super_mode = False
        self.super_timer = 0
        self.timer = GAME_TIME
        self.frame = 0
        self.hoop_angle: float = 0.0
        self.ghost_angle: float = 0.0
        self.shake_frames = 0
        self.gems: list[Gem] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._spawn_cooldown = 0

    def _get_spawn_interval(self) -> int:
        t = 1.0 - (self.timer / GAME_TIME)
        return int(60 - t * 40)

    def _get_gem_speed(self) -> float:
        t = 1.0 - (self.timer / GAME_TIME)
        return 1.5 + t * 1.5

    def _get_max_gems(self) -> int:
        t = 1.0 - (self.timer / GAME_TIME)
        return int(8 + t * 4)

    def _get_hoop_auto_speed(self) -> float:
        t = 1.0 - (self.timer / GAME_TIME)
        return 0.02 + t * 0.02

    def _get_quadrant_color(self, world_angle: float) -> int:
        normalized = world_angle % (2 * math.pi)
        quadrant = int(normalized / (math.pi / 2))
        return HOOP_COLORS[quadrant % 4]

    def _spawn_gem(self) -> None:
        if len(self.gems) >= self._get_max_gems():
            return
        rng = self._seed_rng
        color = rng.randint(0, 3)
        edge = rng.randint(0, 3)
        if edge == 0:  # top
            x = rng.uniform(0, SCREEN_W)
            y = -10.0
        elif edge == 1:  # bottom
            x = rng.uniform(0, SCREEN_W)
            y = SCREEN_H + 10.0
        elif edge == 2:  # left
            x = -10.0
            y = rng.uniform(0, SCREEN_H)
        else:  # right
            x = SCREEN_W + 10.0
            y = rng.uniform(0, SCREEN_H)

        dx = PLAYER_X - x
        dy = PLAYER_Y - y
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            dist = 1.0
        speed = self._get_gem_speed()
        vx = dx / dist * speed
        vy = dy / dist * speed

        self.gems.append(Gem(x=x, y=y, vx=vx, vy=vy, color=HOOP_COLORS[color]))

    def _update_gems(self) -> None:
        for gem in self.gems:
            if not gem.active:
                continue
            gem.x += gem.vx
            gem.y += gem.vy
        self.gems = [g for g in self.gems if g.active]

    def _check_collection(self) -> None:
        center_x = PLAYER_X
        center_y = PLAYER_Y
        for gem in self.gems:
            if not gem.active:
                continue
            dist = math.hypot(gem.x - center_x, gem.y - center_y)
            if dist <= HOOP_RADIUS + GEM_RADIUS:
                angle_to_gem = math.atan2(gem.y - center_y, gem.x - center_x)
                quadrant_color = self._get_quadrant_color(angle_to_gem - self.hoop_angle)
                if self.super_mode or gem.color == quadrant_color:
                    self._collect_gem(gem)
                else:
                    self._mismatch_gem(gem)

    def _collect_gem(self, gem: Gem) -> None:
        gem.active = False
        points = int(10 * (1 + self.combo * 0.5) * (3 if self.super_mode else 1))
        self.score += points
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo
            self.ghost_angle = self.hoop_angle

        self._spawn_particles(gem.x, gem.y, gem.color, 6)
        self.floating_texts.append(
            FloatingText(x=gem.x, y=gem.y, text=f"+{points}", life=30, color=gem.color)
        )

        if self.combo % 4 == 0 and not self.super_mode:
            self._activate_super()
        elif self.super_mode:
            self.super_timer = SUPER_DURATION

        if not self.super_mode and self.combo >= 2:
            self.floating_texts.append(
                FloatingText(
                    x=PLAYER_X,
                    y=PLAYER_Y - 30,
                    text=f"COMBO x{self.combo}!",
                    life=45,
                    color=YELLOW,
                )
            )

        try:
            if self.combo >= 4:
                pyxel.play(0, 1)
            else:
                pyxel.play(0, 0)
        except BaseException:
            pass

    def _mismatch_gem(self, gem: Gem) -> None:
        gem.active = False
        self.heat += 15.0
        self.combo = 0
        self._spawn_particles(gem.x, gem.y, GRAY, 3)
        self.shake_frames = 5
        try:
            pyxel.play(0, 3)
        except BaseException:
            pass

    def _miss_gem(self, gem: Gem) -> None:
        gem.active = False
        self.heat += 10.0

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self.floating_texts.append(
            FloatingText(
                x=PLAYER_X, y=PLAYER_Y - 20, text="SUPER HOOP!", life=60, color=YELLOW
            )
        )
        for i in range(20):
            angle = i * 2 * math.pi / 20
            p_color = HOOP_COLORS[i % 4]
            self.particles.append(
                Particle(
                    x=PLAYER_X, y=PLAYER_Y, vx=math.cos(angle) * 2.5, vy=math.sin(angle) * 2.5, life=25, color=p_color
                )
            )
        try:
            pyxel.play(0, 2)
        except BaseException:
            pass

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        rng = self._seed_rng
        for _ in range(count):
            angle = rng.uniform(0, 2 * math.pi)
            speed = rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=rng.randint(15, 20),
                    color=color,
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for t in self.floating_texts:
            t.y -= 0.5
            t.life -= 1
        self.floating_texts = [t for t in self.floating_texts if t.life > 0]

    def _update_heat(self) -> None:
        self.heat -= 0.02
        if self.heat < 0.0:
            self.heat = 0.0

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.phase = Phase.PLAYING
                self.reset()
                self.phase = Phase.PLAYING
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                if self.score > self.best_score:
                    self.best_score = self.score
                self.reset()
            return

        self.frame += 1
        self.timer -= 1

        if self.shake_frames > 0:
            self.shake_frames -= 1

        self._update_heat()
        if self.heat >= MAX_HEAT or self.timer <= 0:
            self.phase = Phase.GAME_OVER
            if self.score > self.best_score:
                self.best_score = self.score
            try:
                pyxel.play(0, 4)
            except BaseException:
                pass
            return

        auto_speed = self._get_hoop_auto_speed()
        self.hoop_angle += auto_speed
        if pyxel.btn(pyxel.KEY_LEFT):
            self.hoop_angle -= 0.01
        if pyxel.btn(pyxel.KEY_RIGHT):
            self.hoop_angle += 0.01

        if self._spawn_cooldown <= 0:
            self._spawn_gem()
            self._spawn_cooldown = self._get_spawn_interval()
        self._spawn_cooldown -= 1

        self._update_gems()

        center_x = PLAYER_X
        center_y = PLAYER_Y
        for gem in self.gems:
            if not gem.active:
                continue
            dist = math.hypot(gem.x - center_x, gem.y - center_y)
            if dist <= HOOP_RADIUS + GEM_RADIUS:
                self._check_collection()
                break
            elif dist <= PLAYER_RADIUS + GEM_RADIUS:
                self._miss_gem(gem)

        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False

        self._update_particles()
        self._update_floating_texts()

    def _draw_hoop(self) -> None:
        cx = PLAYER_X
        cy = PLAYER_Y
        r = HOOP_RADIUS
        num_points = 128
        for i in range(num_points):
            angle = i * 2 * math.pi / num_points
            world_angle = self.hoop_angle + angle
            color = HOOP_COLORS[0] if self.super_mode else self._get_quadrant_color(world_angle)
            if self.super_mode:
                color = HOOP_COLORS[(i // 16) % 4]
            x = cx + math.cos(world_angle) * r
            y = cy + math.sin(world_angle) * r
            pyxel.pset(int(x), int(y), color)

    def _draw_ghost_hoop(self) -> None:
        if self.max_combo < 2:
            return
        cx = PLAYER_X
        cy = PLAYER_Y
        r = HOOP_RADIUS
        for i in range(0, 64, 2):
            angle = i * 2 * math.pi / 64
            world_angle = self.ghost_angle + angle
            x = cx + math.cos(world_angle) * r
            y = cy + math.sin(world_angle) * r
            pyxel.pset(int(x), int(y), WHITE)

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return
        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
            return

        if self.shake_frames > 0:
            ox = self._seed_rng.randint(-2, 2)
            oy = self._seed_rng.randint(-2, 2)
            pyxel.camera(ox, oy)
        else:
            pyxel.camera()

        self._draw_ghost_hoop()
        self._draw_hoop()

        pyxel.circ(PLAYER_X, PLAYER_Y, PLAYER_RADIUS, DARK_BLUE)

        for gem in self.gems:
            if gem.active:
                pyxel.circ(int(gem.x), int(gem.y), GEM_RADIUS, gem.color)

        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

        for t in self.floating_texts:
            pyxel.text(int(t.x) - len(t.text) * 2, int(t.y), t.text, t.color)

        self._draw_hud()

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE:{self.score}", WHITE)

        time_left = max(0, self.timer) // 60
        time_str = f"TIME:{time_left:02d}"
        pyxel.text(SCREEN_W - len(time_str) * 4 - 4, 4, time_str, WHITE)

        heat_width = int(self.heat / MAX_HEAT * 100)
        heat_color = RED if self.heat > 70 else ORANGE
        pyxel.rect(4, 14, 100, 6, NAVY)
        pyxel.rect(4, 14, heat_width, 6, heat_color)

        if self.combo >= 2:
            combo_str = f"COMBO x{self.combo}!"
            combo_color = LIME if self.combo >= 4 else YELLOW
            x = SCREEN_W // 2 - len(combo_str) * 2
            pyxel.text(x, 22, combo_str, combo_color)

        if self.super_mode:
            sf = (self.frame // 4) % 4
            color = HOOP_COLORS[sf]
            pyxel.text(SCREEN_W // 2 - 20, 34, "SUPER!", color)

    def _draw_title(self) -> None:
        title = "HULA CHAIN"
        x = SCREEN_W // 2 - len(title) * 4 // 2
        pyxel.text(x, 60, title, YELLOW)

        subtitle = "Match hoop colors!"
        x = SCREEN_W // 2 - len(subtitle) * 4 // 2
        pyxel.text(x, 85, subtitle, WHITE)

        inst1 = "LEFT/RIGHT: spin hoop"
        x = SCREEN_W // 2 - len(inst1) * 4 // 2
        pyxel.text(x, 110, inst1, LIGHT_BLUE)

        inst2 = "SPACE/RET: start"
        x = SCREEN_W // 2 - len(inst2) * 4 // 2
        pyxel.text(x, 125, inst2, LIGHT_BLUE)

        if self.best_score > 0:
            best_str = f"BEST SCORE: {self.best_score}"
            x = SCREEN_W // 2 - len(best_str) * 4 // 2
            pyxel.text(x, 155, best_str, YELLOW)

    def _draw_game_over(self) -> None:
        title = "GAME OVER"
        x = SCREEN_W // 2 - len(title) * 4 // 2
        pyxel.text(x, 70, title, RED)

        score_str = f"SCORE: {self.score}"
        x = SCREEN_W // 2 - len(score_str) * 4 // 2
        pyxel.text(x, 95, score_str, WHITE)

        combo_str = f"MAX COMBO: {self.max_combo}"
        x = SCREEN_W // 2 - len(combo_str) * 4 // 2
        pyxel.text(x, 110, combo_str, YELLOW)

        best_str = f"BEST: {self.best_score}"
        x = SCREEN_W // 2 - len(best_str) * 4 // 2
        pyxel.text(x, 125, best_str, WHITE)

        inst = "SPACE/RET: retry"
        x = SCREEN_W // 2 - len(inst) * 4 // 2
        pyxel.text(x, 155, inst, LIGHT_BLUE)


if __name__ == "__main__":
    Game()
