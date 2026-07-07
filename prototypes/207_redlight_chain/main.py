from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, IntEnum

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


class Phase(Enum):
    TITLE = 1
    PLAYING = 2
    GAME_OVER = 3


class LightColor(IntEnum):
    RED = 0
    GREEN = 1
    YELLOW = 2
    BLUE = 3


LIGHT_COLORS: list[int] = [LightColor.RED, LightColor.GREEN, LightColor.YELLOW, LightColor.BLUE]

LIGHT_PYXEL_COLORS: dict[int, int] = {
    LightColor.RED: RED,
    LightColor.GREEN: GREEN,
    LightColor.YELLOW: YELLOW,
    LightColor.BLUE: LIGHT_BLUE,
}

LIGHT_DIM_COLORS: dict[int, int] = {
    LightColor.RED: BROWN,
    LightColor.GREEN: DARK_BLUE,
    LightColor.YELLOW: ORANGE,
    LightColor.BLUE: NAVY,
}

WIDTH = 320
HEIGHT = 240
LANE_Y = 180
PLAYER_Y = 170
TRAFFIC_LIGHT_X = 20
TRAFFIC_TOP_Y = 30
TRAFFIC_BOTTOM_Y = 110
PLAYER_MIN_X = 40
PLAYER_MAX_X = 300
GEM_SPAWN_X = 330
GEM_DESPAWN_X = -20
GEM_SPEED = 2.0
PLAYER_SPEED = 2.0
GEM_RADIUS = 16
MAX_GEMS = 8
GAME_DURATION = 3600
SUPER_DURATION = 180
MAX_HEAT = 100
HEAT_PER_MISS = 15
HEAT_DECAY = 0.1
COMBO_SUPER_THRESHOLD = 4
SCORE_BASE = 10
SCORE_COMBO_MULT = 5
SUPER_SCORE_MULT = 3
GEM_SPAWN_INTERVAL_MIN = 30
GEM_SPAWN_INTERVAL_MAX = 60
MATCH_BIAS = 0.4
PARTICLE_BURST = 8
FLOATING_TEXT_LIFE = 30
INITIAL_LIGHT_INTERVAL = 120
MIN_LIGHT_INTERVAL = 40
LIGHT_SPEEDUP_DIVISOR = 600
LIGHT_SPEEDUP_STEP = 10
FINISH_TARGET_GEMS = 30


@dataclass
class Gem:
    x: float
    y: float
    color: int
    collected: bool = False


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
        self.phase: Phase = Phase.TITLE
        self.player_x: float = 160.0
        self.light_color: int = LightColor.RED
        self.light_timer: int = INITIAL_LIGHT_INTERVAL
        self.light_index: int = 0
        self.gems: list[Gem] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.super_active: bool = False
        self.super_timer: int = 0
        self.game_timer: int = GAME_DURATION
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._rng: random.Random = random.Random()
        self._spawn_timer: int = 0
        self._shake_frames: int = 0
        self._idle_frames: int = 0

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.player_x = 160.0
        self.light_color = LightColor.RED
        self.light_timer = INITIAL_LIGHT_INTERVAL
        self.light_index = 0
        self.gems.clear()
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_active = False
        self.super_timer = 0
        self.game_timer = GAME_DURATION
        self.particles.clear()
        self.floating_texts.clear()
        self._spawn_timer = 0
        self._shake_frames = 0
        self._idle_frames = 0

    def _current_light_interval(self) -> int:
        elapsed = GAME_DURATION - self.game_timer
        step = elapsed // LIGHT_SPEEDUP_DIVISOR
        return max(MIN_LIGHT_INTERVAL, INITIAL_LIGHT_INTERVAL - step * LIGHT_SPEEDUP_STEP)

    def _spawn_gem(self) -> None:
        if len(self.gems) >= MAX_GEMS:
            return
        if self._rng.random() < MATCH_BIAS:
            color = self.light_color
        else:
            color = self._rng.randint(0, 3)
        y_jitter = self._rng.randint(-5, 6)
        self.gems.append(Gem(x=float(GEM_SPAWN_X), y=float(LANE_Y + y_jitter), color=color))

    def _burst_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(PARTICLE_BURST):
            angle = self._rng.uniform(0, 2 * math.pi)
            speed = self._rng.uniform(2, 5)
            p = Particle(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=self._rng.randint(15, 26),
                color=color,
            )
            self.particles.append(p)

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=FLOATING_TEXT_LIFE, color=color))

    def _collect_gem(self, gem: Gem) -> None:
        gem.collected = True
        match_color = (gem.color == self.light_color) or self.super_active

        if match_color:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            points = (SCORE_BASE + self.combo * SCORE_COMBO_MULT)
            if self.super_active:
                points *= SUPER_SCORE_MULT
            self.score += points
            self._burst_particles(gem.x, gem.y, LIGHT_PYXEL_COLORS.get(gem.color, WHITE))
            fg_color = YELLOW
            if self.super_active:
                fg_color = self._rainbow_color()
            self._add_floating_text(gem.x, gem.y - 8, f"+{points}", fg_color)
            if self.combo >= COMBO_SUPER_THRESHOLD and not self.super_active:
                self.super_active = True
                self.super_timer = SUPER_DURATION
                self._add_floating_text(gem.x, gem.y - 16, "SUPER!", LIME)
            self._idle_frames = 0
        else:
            self.combo = 0
            self.heat = min(MAX_HEAT, self.heat + HEAT_PER_MISS)
            self._add_floating_text(gem.x, gem.y - 8, "MISS", RED)
            self._shake_frames = 3

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
            return

        if self.phase == Phase.PLAYING:
            self._update_playing()

    def _update_playing(self) -> None:
        self.game_timer -= 1

        if pyxel.btn(pyxel.KEY_RIGHT):
            self.player_x += PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_LEFT):
            self.player_x -= PLAYER_SPEED
        if self.player_x < PLAYER_MIN_X:
            self.player_x = PLAYER_MIN_X
        if self.player_x > PLAYER_MAX_X:
            self.player_x = PLAYER_MAX_X

        self.light_timer -= 1
        if self.light_timer <= 0:
            self.light_index = (self.light_index + 1) % 4
            self.light_color = LIGHT_COLORS[self.light_index]
            self.light_timer = self._current_light_interval()

        if self.super_active:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_active = False

        self._spawn_timer -= 1
        if self._spawn_timer <= 0:
            self._spawn_gem()
            self._spawn_timer = self._rng.randint(GEM_SPAWN_INTERVAL_MIN, GEM_SPAWN_INTERVAL_MAX + 1)

        for gem in self.gems:
            if gem.collected:
                continue
            gem.x -= GEM_SPEED

        player_cx = self.player_x
        player_cy = PLAYER_Y
        any_collected = False
        for gem in self.gems:
            if gem.collected:
                continue
            dist = math.hypot(gem.x - player_cx, gem.y - player_cy)
            if dist < GEM_RADIUS:
                self._collect_gem(gem)
                any_collected = True

        if not any_collected:
            self._idle_frames += 1
            if self._idle_frames >= 60:
                self.heat = max(0.0, self.heat - HEAT_DECAY)
        else:
            self._idle_frames = 0

        self.gems = [g for g in self.gems if not g.collected and g.x > GEM_DESPAWN_X]

        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

        for ft in self.floating_texts:
            ft.y -= 1
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

        if self._shake_frames > 0:
            self._shake_frames -= 1

        if self.game_timer <= 0 or self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER

    def _rainbow_color(self) -> int:
        t = pyxel.frame_count // 4
        rainbow = [RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK]
        return rainbow[t % len(rainbow)]

    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.cls(NAVY)
        pyxel.text(WIDTH // 2 - 50, 60, "REDLIGHT CHAIN", WHITE)
        pyxel.text(WIDTH // 2 - 55, 80, "Traffic Light Action", LIME)
        pyxel.text(WIDTH // 2 - 40, 120, "[SPACE] or [ENTER]", GRAY)
        pyxel.text(WIDTH // 2 - 30, 140, "to start", GRAY)
        pyxel.text(WIDTH // 2 - 60, 180, "Collect matching gems", LIGHT_BLUE)
        pyxel.text(WIDTH // 2 - 60, 190, "Avoid wrong colors!", RED)
        pyxel.text(WIDTH // 2 - 55, 210, "Combo x4 = SUPER MODE", YELLOW)

    def _draw_game_over(self) -> None:
        pyxel.cls(NAVY)
        pyxel.text(WIDTH // 2 - 30, 50, "GAME OVER", RED)
        pyxel.text(WIDTH // 2 - 25, 80, f"Score: {self.score}", WHITE)
        pyxel.text(WIDTH // 2 - 45, 100, f"Best Combo: {self.max_combo}", YELLOW)
        pyxel.text(WIDTH // 2 - 35, 140, "[SPACE] to retry", GRAY)

    def _draw_playing(self) -> None:
        offset_x = 0
        offset_y = 0
        if self._shake_frames > 0:
            offset_x = self._rng.randint(-2, 3)
            offset_y = self._rng.randint(-2, 3)

        pyxel.cls(NAVY)
        color_bands = [NAVY, DARK_BLUE, PURPLE, LIGHT_BLUE, CYAN]
        for i in range(60):
            col = color_bands[min(i * len(color_bands) // 60, len(color_bands) - 1)]
            pyxel.rect(0, i * 3, WIDTH, 3, col)

        pyxel.rect(0, 180, WIDTH, 60, GREEN)

        pyxel.rect(0, 175 + offset_y, WIDTH, 10, GRAY)

        pyxel.rect(16 + offset_x, 30 + offset_y, 6, 180, GRAY)

        top_y = 30 + offset_y
        box_h = 88
        pyxel.rect(8 + offset_x, top_y, 22, box_h, DARK_BLUE)

        circle_x = 19 + offset_x
        for idx, lc in enumerate(LIGHT_COLORS):
            cy = top_y + 10 + idx * 20
            if lc == self.light_color:
                pyxel.circ(circle_x, cy, 8, LIGHT_PYXEL_COLORS[lc])
                pyxel.circb(circle_x, cy, 10, WHITE)
            else:
                pyxel.circ(circle_x, cy, 6, LIGHT_DIM_COLORS[lc])

        for gem in self.gems:
            if gem.collected:
                continue
            gx = int(gem.x) + offset_x
            gy = int(gem.y) + offset_y
            c = LIGHT_PYXEL_COLORS.get(gem.color, WHITE)
            pyxel.tri(gx, gy - 4, gx + 4, gy, gx, gy + 4, c)
            pyxel.tri(gx, gy - 4, gx - 4, gy, gx, gy + 4, c)

        player_cx = int(self.player_x) + offset_x
        player_cy = PLAYER_Y + offset_y
        if self.super_active:
            player_color = self._rainbow_color()
            pyxel.circb(player_cx, player_cy, 10, LIME)
        else:
            player_color = WHITE
        pyxel.rect(player_cx - 6, player_cy - 6, 12, 12, player_color)
        pyxel.rectb(player_cx - 7, player_cy - 7, 14, 14, BLACK)

        for p in self.particles:
            if p.life > 0:
                px = int(p.x) + offset_x
                py = int(p.y) + offset_y
                alpha = min(p.life, 15)
                c = p.color if alpha > 8 else DARK_BLUE
                pyxel.rect(px, py, 2, 2, c)

        for ft in self.floating_texts:
            if ft.life > 0:
                fx = int(ft.x) + offset_x
                fy = int(ft.y) + offset_y
                c = ft.color
                if ft.life < 10:
                    c = GRAY
                pyxel.text(fx - len(ft.text) * 2, fy, ft.text, c)

        if self.super_active:
            rainbow = self._rainbow_color()
            pyxel.rectb(0, 0, WIDTH, HEIGHT, rainbow)

        pyxel.text(WIDTH - 60, 4, f"SCORE: {self.score}", WHITE)
        pyxel.text(WIDTH - 60, 14, f"COMBO: {self.combo}", YELLOW)
        mm = self.game_timer // 3600
        ss = (self.game_timer // 60) % 60
        pyxel.text(WIDTH // 2 - 15, 4, f"{mm:02d}:{ss:02d}", WHITE)
        heat_bar_width = 80
        heat_x = 4
        heat_y = HEIGHT - 14
        pyxel.rect(heat_x, heat_y, heat_bar_width, 6, DARK_BLUE)
        heat_fill = int(heat_bar_width * self.heat / MAX_HEAT)
        if heat_fill > 0:
            heat_color = RED
            if self.heat > 75:
                heat_color = ORANGE
            pyxel.rect(heat_x, heat_y, heat_fill, 6, heat_color)
        pyxel.rectb(heat_x - 1, heat_y - 1, heat_bar_width + 2, 8, GRAY)
        pyxel.text(heat_x + heat_bar_width + 6, heat_y - 1, "HEAT", RED)

        if self.super_active:
            super_sec = self.super_timer // 60 + 1
            pyxel.text(WIDTH // 2 - 20, 20, f"SUPER {super_sec}s", LIME)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.player_x = 160.0
    g.light_color = LightColor.RED
    g.light_timer = INITIAL_LIGHT_INTERVAL
    g.light_index = 0
    g.gems = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.super_active = False
    g.super_timer = 0
    g.game_timer = GAME_DURATION
    g.particles = []
    g.floating_texts = []
    g._rng = random.Random()
    g._spawn_timer = 0
    g._shake_frames = 0
    g._idle_frames = 0
    return g


def main() -> None:
    pyxel.init(WIDTH, HEIGHT, title="Redlight Chain")
    game = Game()
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
