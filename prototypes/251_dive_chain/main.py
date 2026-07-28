from __future__ import annotations

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


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Ring:
    x: float
    y: float
    vx: float
    vy: float
    color: int  # RED=8, LIME=11, DARK_BLUE=5, YELLOW=10
    radius: int = 12


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class GhostPoint:
    x: float
    y: float


class Game:
    SPRINGBOARD_X = 20
    SPRINGBOARD_Y = 200
    SPRINGBOARD_W = 60
    SPRINGBOARD_H = 6
    DIVER_W = 10
    DIVER_H = 16
    AIR_LEFT = 60
    AIR_RIGHT = 300
    AIR_TOP = 30
    AIR_BOTTOM = 200
    COLORS: tuple[int, ...] = (8, 11, 5, 10)
    COLOR_NAMES: tuple[str, ...] = ("RED", "LIME", "DARK_BLUE", "YELLOW")
    RING_RADIUS = 12
    COLLISION_RADIUS = 16
    MAX_HEAT = 100.0
    HEAT_DECAY = 0.02
    MAX_RINGS = 8
    SUPER_DURATION = 300
    SUPER_COMBO_THRESHOLD = 4
    GAME_DURATION = 1800
    POWER_MAX = 100.0
    POWER_RATE = 100.0 / 30.0
    LAUNCH_VY_SCALE = 0.12
    LAUNCH_VX_SCALE = 0.03
    GRAVITY = 0.35
    COLOR_CYCLE_COOLDOWN = 8

    phase: Phase
    score: int
    combo: int
    max_combo: int
    heat: float
    timer: int
    diver_x: float
    diver_y: float
    diver_vx: float
    diver_vy: float
    diver_color: int
    diver_color_idx: int
    diver_color_cooldown: int
    diver_airborne: bool
    power: float
    charging: bool
    stun_timer: int
    landing_cooldown: int
    super_timer: int
    rings: list[Ring]
    particles: list[Particle]
    floating_texts: list[tuple[float, float, str, int, int]]
    ghost_points: list[GhostPoint]
    best_ghost: list[GhostPoint]
    best_score: int
    ring_spawn_timer: int
    _rng: random.Random
    _shake_frames: int
    _bounce_anim: float

    def __init__(self) -> None:
        self._rng = random.Random()
        self.reset()

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = self.GAME_DURATION
        self.diver_x = float(self.SPRINGBOARD_X + self.SPRINGBOARD_W // 2)
        self.diver_y = float(self.SPRINGBOARD_Y - self.DIVER_H)
        self.diver_vx = 0.0
        self.diver_vy = 0.0
        self.diver_color = RED
        self.diver_color_idx = 0
        self.diver_color_cooldown = 0
        self.diver_airborne = False
        self.power = 0.0
        self.charging = False
        self.stun_timer = 0
        self.landing_cooldown = 0
        self.super_timer = 0
        self.rings = []
        self.particles = []
        self.floating_texts = []
        self.ghost_points = []
        self.best_ghost = []
        self.best_score = 0
        self.ring_spawn_timer = 60
        self._shake_frames = 0
        self._bounce_anim = 0.0

    def _spawn_ring(self) -> Ring:
        x = float(self._rng.randint(self.AIR_RIGHT, self.AIR_RIGHT + 20))
        y = float(self._rng.randint(self.AIR_TOP + 20, self.AIR_BOTTOM - 20))
        color = self._rng.choice(self.COLORS)
        speed = 0.5 + (1.0 - self.timer / self.GAME_DURATION) * 1.0
        vx = -speed
        vy = self._rng.uniform(-0.3, 0.3)
        return Ring(x=x, y=y, vx=vx, vy=vy, color=color, radius=self.RING_RADIUS)

    def _check_ring_collision(self, diver_x: float, diver_y: float, ring: Ring) -> bool:
        dx = diver_x - ring.x
        dy = diver_y - ring.y
        dist_sq = dx * dx + dy * dy
        collision_dist = self.COLLISION_RADIUS + ring.radius
        return dist_sq <= collision_dist * collision_dist

    def _collect_ring(self, ring: Ring) -> None:
        match = self.super_timer > 0 or ring.color == self.diver_color

        if match:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            multiplier = 3 if self.super_timer > 0 else 1
            gained = 10 * self.combo * multiplier
            self.score += gained

            if self.super_timer > 0:
                self._spawn_particles(ring.x, ring.y, 15, 25, color=-1)
                self._add_floating_text(ring.x, ring.y - 10, f"+{gained}", YELLOW)
            else:
                self._spawn_particles(ring.x, ring.y, 8, 20, color=ring.color)
                self._add_floating_text(ring.x, ring.y - 10, f"+{gained}", WHITE)

            if self.combo >= 2:
                self._add_floating_text(
                    self.diver_x, self.diver_y - 16,
                    f"COMBO x{self.combo}", YELLOW,
                )

            if self.combo >= self.SUPER_COMBO_THRESHOLD and self.super_timer == 0:
                self._activate_super()

        else:
            self.combo = 0
            self.heat = min(float(self.MAX_HEAT), self.heat + 15.0)
            self.stun_timer = 15
            self._spawn_particles(ring.x, ring.y, 4, 10, color=GRAY)
            self._add_floating_text(ring.x, ring.y - 10, "WRONG!", RED)
            self._shake_frames = 8

        if ring in self.rings:
            self.rings.remove(ring)

    def _activate_super(self) -> None:
        self.super_timer = self.SUPER_DURATION
        self._add_floating_text(
            self.diver_x, self.diver_y - 24,
            "SUPER DIVE!", YELLOW,
        )

    def _launch_diver(self) -> None:
        if self.power <= 0.0:
            return
        self.diver_vy = -self.power * self.LAUNCH_VY_SCALE
        self.diver_vx = self.power * self.LAUNCH_VX_SCALE
        self.diver_airborne = True
        self.combo = 0
        self.ghost_points = []
        self.power = 0.0
        self.charging = False
        self._spawn_particles(
            self.SPRINGBOARD_X + self.SPRINGBOARD_W // 2,
            self.SPRINGBOARD_Y,
            5, 10, color=WHITE,
        )

    def _update_diver_physics(self) -> None:
        if not self.diver_airborne:
            return

        self.diver_vy += self.GRAVITY
        self.diver_x += self.diver_vx
        self.diver_y += self.diver_vy

        if self.diver_y >= self.SPRINGBOARD_Y - self.DIVER_H and self.diver_vy > 0:
            self.diver_y = float(self.SPRINGBOARD_Y - self.DIVER_H)
            self.diver_vx = 0.0
            self.diver_vy = 0.0
            self.diver_airborne = False
            self.landing_cooldown = 30
            self._spawn_particles(
                self.diver_x + self.DIVER_W // 2,
                self.SPRINGBOARD_Y,
                5, 10, color=LIGHT_BLUE,
            )
            self._shake_frames = 4

            self._add_floating_text(
                self.diver_x, self.SPRINGBOARD_Y - 30,
                f"Score this dive: {self.score}", CYAN,
            )

            if self.diver_x > self.AIR_RIGHT or self.diver_x < self.AIR_LEFT:
                self.heat = min(float(self.MAX_HEAT), self.heat + 25.0)
                self._add_floating_text(
                    self.diver_x, self.diver_y - 10,
                    "SPLASH OUT!", RED,
                )

        if (self.diver_y < -20
                or self.diver_x > 340
                or self.diver_x < -20
                or self.diver_y > 260):
            self.heat = min(float(self.MAX_HEAT), self.heat + 25.0)
            self.diver_x = float(self.SPRINGBOARD_X + self.SPRINGBOARD_W // 2)
            self.diver_y = float(self.SPRINGBOARD_Y - self.DIVER_H)
            self.diver_vx = 0.0
            self.diver_vy = 0.0
            self.diver_airborne = False
            self.landing_cooldown = 30
            self._add_floating_text(
                self.diver_x, self.diver_y - 10,
                "SPLASH OUT!", RED,
            )

    def _update_rings(self) -> None:
        for ring in list(self.rings):
            ring.x += ring.vx
            ring.y += ring.vy
            if ring.x < self.AIR_LEFT - 20 or ring.y < self.AIR_TOP - 20 or ring.y > self.AIR_BOTTOM + 20:
                self.rings.remove(ring)

        while len(self.rings) > self.MAX_RINGS:
            self.rings.pop(0)

        self.ring_spawn_timer -= 1
        if self.ring_spawn_timer <= 0 and len(self.rings) < self.MAX_RINGS:
            progress = 1.0 - self.timer / self.GAME_DURATION
            interval = max(25, 60 - int(progress * 35))
            self.ring_spawn_timer = self._rng.randint(interval, interval + 15)
            self.rings.append(self._spawn_ring())

        if self.ring_spawn_timer <= 0:
            self.ring_spawn_timer = 5

    def _update_particles(self) -> None:
        for p in list(self.particles):
            p.vy += 0.05
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        new_list: list[tuple[float, float, str, int, int]] = []
        for x, y, text, color, life in self.floating_texts:
            new_life = life - 1
            if new_life > 0:
                new_list.append((x, y - 1.0, text, color, new_life))
        self.floating_texts = new_list

    def _update_heat(self) -> None:
        if self.heat >= self.MAX_HEAT:
            self.heat = float(self.MAX_HEAT)
            if self.phase == Phase.PLAYING:
                self._on_game_over()
            return
        if self.heat > 0 and self.super_timer == 0:
            self.heat = max(0.0, self.heat - self.HEAT_DECAY)

    def _on_game_over(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score
            self.best_ghost = list(self.ghost_points)

    def _spawn_particles(
        self,
        x: float,
        y: float,
        min_count: int,
        max_count: int,
        color: int | None = None,
    ) -> None:
        count = self._rng.randint(min_count, max_count)
        for _ in range(count):
            if color is not None and color == -1:
                c = self._rng.choice(self.COLORS)
            elif color is not None:
                c = color
            else:
                c = WHITE
            vx = self._rng.uniform(-2.0, 2.0)
            vy = self._rng.uniform(-3.0, 1.0)
            life = self._rng.randint(10, 25)
            self.particles.append(Particle(x, y, vx, vy, life, c))

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append((x, y, text, color, 30))

    def _cycle_diver_color(self, direction: int) -> None:
        if self.super_timer > 0:
            return
        if self.diver_color_cooldown > 0:
            return
        if self.stun_timer > 0:
            return
        idx = self.COLORS.index(self.diver_color)
        idx = (idx + direction) % len(self.COLORS)
        self.diver_color = self.COLORS[idx]
        self.diver_color_idx = idx
        self.diver_color_cooldown = self.COLOR_CYCLE_COOLDOWN

    def update(self) -> None:
        if self.phase != Phase.PLAYING:
            return

        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self._on_game_over()
            return

        if self.landing_cooldown > 0:
            self.landing_cooldown -= 1
        if self.diver_color_cooldown > 0:
            self.diver_color_cooldown -= 1
        if self.stun_timer > 0:
            self.stun_timer -= 1
        if self.super_timer > 0:
            self.super_timer -= 1
        if self._shake_frames > 0:
            self._shake_frames -= 1

        if self.charging and not self.diver_airborne and self.landing_cooldown <= 0:
            self.power = min(self.POWER_MAX, self.power + self.POWER_RATE)
            if self.power >= self.POWER_MAX:
                self._launch_diver()

        self._update_diver_physics()
        self._update_rings()

        if self.diver_airborne and self.stun_timer == 0:
            for ring in list(self.rings):
                if self._check_ring_collision(self.diver_x, self.diver_y, ring):
                    self._collect_ring(ring)

        if self.diver_airborne and pyxel.frame_count % 5 == 0:
            self.ghost_points.append(
                GhostPoint(x=self.diver_x, y=self.diver_y)
            )

        self._update_heat()
        self._update_particles()
        self._update_floating_texts()

    def draw(self) -> None:
        pyxel.cls(DARK_BLUE)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(105, 40, "DIVE CHAIN", CYAN)
        pyxel.text(50, 65, "SPACE: Charge & Release to Jump", WHITE)
        pyxel.text(50, 75, "UP/DOWN: Change Dive Color", WHITE)
        pyxel.text(50, 85, "Match color to pass through rings", WHITE)
        pyxel.text(50, 95, "COMBO x4 = SUPER DIVE!", YELLOW)
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(105, 125, "PRESS SPACE", YELLOW)

        if self.best_score > 0:
            pyxel.text(50, 155, f"Best Score: {self.best_score}", CYAN)
            pyxel.text(50, 165, f"Max Combo: {self.max_combo}", YELLOW)

        pyxel.text(70, 195, "DIVE CHAIN RULES", WHITE)
        pyxel.text(50, 207, "Same color rings = COMBO UP", LIME)
        pyxel.text(50, 217, "Wrong color = HEAT UP + Stun", RED)
        pyxel.text(50, 227, "COMBO x4 triggers SUPER DIVE!", YELLOW)

    def _draw_playing(self) -> None:
        if self._shake_frames > 0:
            sx = self._rng.randint(-2, 2)
            sy = self._rng.randint(-2, 2)
            pyxel.camera(sx, sy)

        self._draw_background()
        self._draw_best_ghost()
        self._draw_rings()
        self._draw_diver()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_springboard()
        self._draw_power_bar()
        self._draw_hud()
        self._draw_super_border()

        if self._shake_frames > 0:
            pyxel.camera(0, 0)

    def _draw_background(self) -> None:
        pyxel.rect(0, self.SPRINGBOARD_Y + self.SPRINGBOARD_H,
                   320, 240 - self.SPRINGBOARD_Y - self.SPRINGBOARD_H, LIGHT_BLUE)

        wave_offset = pyxel.frame_count % 60
        for i in range(0, 320, 12):
            h = 2 + pyxel.sin(wave_offset * 30 + i * 30) * 1
            pyxel.line(i, int(self.SPRINGBOARD_Y + self.SPRINGBOARD_H + 1),
                       i, int(self.SPRINGBOARD_Y + self.SPRINGBOARD_H + 1 + h), NAVY)

    def _draw_best_ghost(self) -> None:
        for gp in self.ghost_points:
            pyxel.circ(int(gp.x), int(gp.y), 2, CYAN)

    def _draw_rings(self) -> None:
        for ring in self.rings:
            pyxel.circb(int(ring.x), int(ring.y), ring.radius, ring.color)
            pyxel.circb(int(ring.x), int(ring.y), ring.radius - 1, ring.color)

    def _draw_diver(self) -> None:
        x = int(self.diver_x)
        y = int(self.diver_y)

        if self.super_timer > 0:
            c = self.COLORS[(pyxel.frame_count // 8) % len(self.COLORS)]
        elif self.stun_timer > 0 and (pyxel.frame_count // 4) % 2 == 0:
            c = GRAY
        else:
            c = self.diver_color

        pyxel.rect(x, y, self.DIVER_W, self.DIVER_H, c)
        pyxel.rect(x + 2, y + 2, 3, 2, WHITE)
        pyxel.rect(x + 6, y + 2, 3, 2, WHITE)

        if self.super_timer > 0:
            sig_color = self.COLORS[(pyxel.frame_count // 6) % len(self.COLORS)]
            pyxel.circb(x + self.DIVER_W // 2, y + self.DIVER_H // 2,
                        self.DIVER_W, sig_color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 25.0
            if alpha > 1.0:
                alpha = 1.0
            col = p.color
            if alpha < 0.3:
                col = DARK_BLUE
            size = 1
            if p.life > 15:
                size = 2
            pyxel.circ(int(p.x), int(p.y), size, col)

    def _draw_floating_texts(self) -> None:
        for x, y, text, color, life in self.floating_texts:
            alpha = life / 30.0
            if alpha < 0.3:
                continue
            pyxel.text(int(x) - len(text) * 2, int(y), text, color)

    def _draw_springboard(self) -> None:
        board_x = self.SPRINGBOARD_X
        board_y = self.SPRINGBOARD_Y
        board_w = self.SPRINGBOARD_W
        board_h = self.SPRINGBOARD_H

        if self.charging:
            self._bounce_anim = self.power / self.POWER_MAX * 4
        else:
            self._bounce_anim *= 0.8

        compression = min(self._bounce_anim, 4)
        pyxel.rect(board_x, int(board_y + compression),
                   board_w, int(board_h - compression), WHITE)
        pyxel.rect(board_x, int(board_y + board_h - 2 - compression),
                   board_w, 4, BROWN)

    def _draw_power_bar(self) -> None:
        bar_x = self.SPRINGBOARD_X
        bar_y = self.SPRINGBOARD_Y + 12
        bar_w = 8
        bar_h = 40

        pyxel.rectb(bar_x, bar_y, bar_w, bar_h + 2, WHITE)
        fill_h = int(bar_h * self.power / self.POWER_MAX)
        if self.power < 30:
            color = LIME
        elif self.power < 70:
            color = YELLOW
        else:
            color = RED
        pyxel.rect(bar_x + 1, bar_y + bar_h - fill_h + 1, bar_w - 2, fill_h, color)

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, 320, 20, DARK_BLUE)
        pyxel.line(0, 20, 320, 20, LIGHT_BLUE)

        pyxel.text(4, 4, f"SCORE:{self.score}", WHITE)
        pyxel.text(75, 4, f"COMBO:{self.combo}", YELLOW)

        color_name = self.COLOR_NAMES[self.diver_color_idx]
        if self.super_timer > 0:
            color_display = "RAINBOW"
        else:
            color_display = color_name
        pyxel.text(145, 4, f"COLOR:{color_display}", WHITE)

        seconds = self.timer // 30
        pyxel.text(235, 4, f"TIME:{seconds:02d}", WHITE)

        if self.super_timer > 0:
            super_sec = self.super_timer // 30
            pyxel.text(285, 4, f"S:{super_sec:02d}", YELLOW)

        bar_x = 5
        bar_y = 230
        bar_w = 310
        bar_h = 6
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        fill_w = int(bar_w * self.heat / self.MAX_HEAT)
        if self.heat < 33:
            hc = GREEN
        elif self.heat < 66:
            hc = YELLOW
        else:
            hc = RED
        pyxel.rect(bar_x, bar_y, fill_w, bar_h, hc)
        pyxel.text(bar_x + bar_w // 2 - 8, bar_y + 1, "HEAT", WHITE)

    def _draw_super_border(self) -> None:
        if self.super_timer <= 0:
            return
        c = self.COLORS[(pyxel.frame_count // 10) % len(self.COLORS)]
        pyxel.rectb(0, 0, 320, 240, c)
        pyxel.rectb(1, 1, 318, 238, c)

    def _draw_game_over(self) -> None:
        pyxel.text(90, 60, "GAME OVER", RED)
        pyxel.text(90, 85, f"Score: {self.score}", WHITE)
        pyxel.text(90, 95, f"Max Combo: {self.max_combo}", YELLOW)
        pyxel.text(90, 105, f"Best Score: {self.best_score}", CYAN)

        if self.score >= self.best_score and self.score > 0:
            pyxel.text(95, 125, "NEW BEST!", YELLOW)

        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(90, 150, "PRESS SPACE TO RETRY", WHITE)


class App:
    def __init__(self) -> None:
        pyxel.init(320, 240, title="DIVE CHAIN", fps=30)
        self.game = Game()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        game = self.game

        if game.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                game.reset()
                game.phase = Phase.PLAYING
                game.timer = Game.GAME_DURATION
            return

        if game.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                game.reset()
                game.phase = Phase.TITLE
            return

        if game.phase == Phase.PLAYING:
            if not game.diver_airborne and game.landing_cooldown <= 0:
                if pyxel.btn(pyxel.KEY_SPACE):
                    game.charging = True
                else:
                    if game.charging:
                        game._launch_diver()
                    game.charging = False

            if game.diver_airborne:
                if pyxel.btnp(pyxel.KEY_UP):
                    game._cycle_diver_color(1)
                elif pyxel.btnp(pyxel.KEY_DOWN):
                    game._cycle_diver_color(-1)

            game.update()

    def draw(self) -> None:
        self.game.draw()


def main() -> None:
    App()


if __name__ == "__main__":
    main()
