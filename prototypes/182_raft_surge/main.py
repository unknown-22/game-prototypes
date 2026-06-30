"""
RAFT SURGE — White water rafting color-match COMBO chain game.

Top-down river scrolling downward. Steer the raft through rapids,
pass through same-color buoys to build COMBO. COMBO>=4 triggers
SUPER PADDLE rainbow mode. Hit rocks → HEAT. HEAT>=100 → game over.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import pyxel

# ── Constants ──
SCREEN_W = 320
SCREEN_H = 240
RAFT_W = 24
RAFT_H = 12
RAFT_Y = 180
BUOY_RADIUS = 6
ROCK_RADIUS = 8
INITIAL_TIMER = 3600  # 60 seconds at 60fps
SUPER_DURATION = 180  # 3 seconds at 60fps
HEAT_MAX = 100.0
HEAT_DECAY = 0.03
STUN_DURATION = 10

# Colors (Pyxel palette)
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

BUOY_COLORS = [RED, GREEN, DARK_BLUE, YELLOW]

INITIAL_BUOY_MIN = 90
INITIAL_BUOY_MAX = 150
INITIAL_ROCK_MIN = 120
INITIAL_ROCK_MAX = 200


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Buoy:
    x: float
    y: float
    color: int  # 8=RED, 3=GREEN, 5=DARK_BLUE, 10=YELLOW
    collected: bool = False


@dataclass
class Rock:
    x: float
    y: float
    size: int = 16


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
    frame: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


# ── Headless testing helper ──


def _make_game() -> "Game":
    g = Game.__new__(Game)
    g.reset()
    return g


# ── Game ──


class Game:
    """Raft Surge main game class. Uses pyxel for I/O and rendering."""

    # Pre-init for headless __new__ pattern
    phase: Phase = Phase.TITLE
    score: int = 0
    combo: int = 0
    max_combo: int = 0
    heat: float = 0.0
    timer: int = INITIAL_TIMER
    raft_x: float = 160.0
    raft_y: float = float(RAFT_Y)
    scroll_speed: float = 1.0
    super_timer: int = 0
    super_mode: bool = False
    stun_timer: int = 0
    buoys: list[Buoy] = []
    rocks: list[Rock] = []
    particles: list[Particle] = []
    floating_texts: list[FloatingText] = []
    ghost_trail: list[GhostPoint] = []
    best_ghost: list[GhostPoint] = []
    best_score: int = 0
    spawn_timer_buoy: int = 0
    spawn_timer_rock: int = 0
    difficulty_timer: int = 0
    current_color: Optional[int] = None
    _rng: random.Random = random.Random(0)
    _frame: int = 0

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="RAFT SURGE", display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = INITIAL_TIMER
        self.raft_x = 160.0
        self.raft_y = float(RAFT_Y)
        self.scroll_speed = 1.0
        self.super_timer = 0
        self.super_mode = False
        self.stun_timer = 0
        self.buoys = []
        self.rocks = []
        self.particles = []
        self.floating_texts = []
        self.ghost_trail = []
        self._rng = random.Random()
        self.spawn_timer_buoy = self._rng.randint(INITIAL_BUOY_MIN, INITIAL_BUOY_MAX)
        self.spawn_timer_rock = self._rng.randint(INITIAL_ROCK_MIN, INITIAL_ROCK_MAX)
        self.difficulty_timer = 0
        self.current_color = None
        self._frame = 0

    # ── Update ──

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._start_game()

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._start_game()

    def _start_game(self) -> None:
        saved_best_score = self.best_score
        saved_best_ghost = self.best_ghost
        self.reset()
        self.best_score = saved_best_score
        self.best_ghost = saved_best_ghost
        self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self._frame += 1
        self.timer -= 1
        if self.timer <= 0:
            self._end_game()
            return

        self._handle_input()

        if self.stun_timer > 0:
            self.stun_timer -= 1
            self._update_particles()
            self._update_floating_texts()
            self._update_ghost_trail()
            return

        self._update_difficulty()
        self._spawn_objects()
        self._update_entities()
        self._check_collisions()
        self._update_heat()
        self._update_super()
        self._update_particles()
        self._update_floating_texts()
        self._update_ghost_trail()
        self._spawn_water_trail()

    def _handle_input(self) -> None:
        if self.stun_timer > 0:
            return
        speed = 2.5
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            self.raft_x -= speed
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            self.raft_x += speed
        if self.raft_x < 20:
            self.raft_x = 20
        if self.raft_x > 300:
            self.raft_x = 300

    def _end_game(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score
            self.best_ghost = self.ghost_trail.copy()
        self.ghost_trail.clear()

    # ── Spawning ──

    def _spawn_objects(self) -> None:
        self.spawn_timer_buoy -= 1
        if self.spawn_timer_buoy <= 0:
            self._spawn_buoy()
            diff_level = self.difficulty_timer // 600
            lo = max(40, INITIAL_BUOY_MIN - diff_level * 10)
            hi = max(80, INITIAL_BUOY_MAX - diff_level * 15)
            self.spawn_timer_buoy = self._rng.randint(lo, hi)

        self.spawn_timer_rock -= 1
        if self.spawn_timer_rock <= 0:
            self._spawn_rock()
            diff_level = self.difficulty_timer // 600
            lo = max(60, INITIAL_ROCK_MIN - diff_level * 10)
            hi = max(100, INITIAL_ROCK_MAX - diff_level * 15)
            self.spawn_timer_rock = self._rng.randint(lo, hi)

    def _spawn_buoy(self) -> None:
        x = self._rng.uniform(40, 280)
        color = self._rng.choice(BUOY_COLORS)
        self.buoys.append(Buoy(x=x, y=-10.0, color=color))

    def _spawn_rock(self) -> None:
        x = self._rng.uniform(40, 280)
        self.rocks.append(Rock(x=x, y=-10.0))

    def _spawn_water_trail(self) -> None:
        if self._frame % 3 != 0:
            return
        vx = self._rng.uniform(-0.3, 0.3)
        vy = 1.0
        life = self._rng.randint(8, 12)
        self.particles.append(
            Particle(self.raft_x, self.raft_y + RAFT_H / 2, vx, vy, life, LIGHT_BLUE)
        )

    # ── Entity updates ──

    def _update_entities(self) -> None:
        for b in self.buoys:
            b.y += self.scroll_speed
        for r in self.rocks:
            r.y += self.scroll_speed
        self.buoys = [b for b in self.buoys if b.y < SCREEN_H + 20 and not b.collected]
        self.rocks = [r for r in self.rocks if r.y < SCREEN_H + 20]

    def _update_difficulty(self) -> None:
        self.difficulty_timer += 1
        if self.difficulty_timer % 600 == 0:
            self.scroll_speed += 0.1

    # ── Collisions ──

    def _check_collisions(self) -> None:
        raft_left = self.raft_x - RAFT_W / 2
        raft_right = self.raft_x + RAFT_W / 2
        raft_top = self.raft_y - RAFT_H / 2
        raft_bottom = self.raft_y + RAFT_H / 2

        # Rock collisions (auto-avoid in super mode)
        if not self.super_mode:
            for r in self.rocks:
                closest_x = max(raft_left, min(r.x, raft_right))
                closest_y = max(raft_top, min(r.y, raft_bottom))
                if math.hypot(r.x - closest_x, r.y - closest_y) < ROCK_RADIUS:
                    self._hit_rock()
                    break

        # Buoy collection: collect closest one per frame
        closest_buoy: Optional[Buoy] = None
        closest_dist = float("inf")
        for b in self.buoys:
            if b.collected:
                continue
            if abs(b.x - self.raft_x) < (RAFT_W / 2 + BUOY_RADIUS) and abs(
                b.y - self.raft_y
            ) < (RAFT_H / 2 + BUOY_RADIUS):
                dist = math.hypot(b.x - self.raft_x, b.y - self.raft_y)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_buoy = b

        if closest_buoy is not None:
            self._collect_buoy(closest_buoy)

    def _collect_buoy(self, buoy: Buoy) -> None:
        buoy.collected = True

        if self.super_mode:
            self.combo += 1
            points = (10 + self.combo * 5) * 3
            self._add_score(points)
            self._spawn_particles(buoy.x, buoy.y, 8, buoy.color, vel_range=1.5, life_min=15, life_max=25)
            self._spawn_floating_text(buoy.x, buoy.y - 8, f"+{points}", YELLOW)
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            return

        if self.current_color == buoy.color:
            self.combo += 1
            points = 10 + self.combo * 5
            self._add_score(points)
            self._spawn_particles(buoy.x, buoy.y, 8, buoy.color, vel_range=1.5, life_min=15, life_max=25)
            self._spawn_floating_text(buoy.x, buoy.y - 8, f"+{points}", YELLOW)
            if self.combo >= 2:
                self._spawn_floating_text(
                    buoy.x, buoy.y - 16, f"COMBO x{self.combo}!", ORANGE
                )
        else:
            self.combo = 0
            self.heat += 10
            self._spawn_particles(buoy.x, buoy.y, 4, RED, vel_range=1.0, life_min=8, life_max=15)
            self._spawn_floating_text(buoy.x, buoy.y - 8, "MISS", RED)

        self.current_color = buoy.color

        if self.combo > self.max_combo:
            self.max_combo = self.combo

        if self.combo >= 4 and not self.super_mode:
            self._activate_super()

    def _hit_rock(self) -> None:
        self.heat += 20
        self.stun_timer = STUN_DURATION
        self._spawn_particles(
            self.raft_x, self.raft_y, 16, ORANGE, vel_range=3.0, life_min=20, life_max=30
        )
        for _ in range(8):
            self._spawn_particles(
                self.raft_x, self.raft_y, 1, BROWN, vel_range=3.0, life_min=20, life_max=30
            )
        self._spawn_floating_text(self.raft_x, self.raft_y - 12, "CRASH!", RED)

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self._spawn_floating_text(
            self.raft_x, self.raft_y - 24, "SUPER PADDLE!", ORANGE
        )

    # ── State updates ──

    def _update_heat(self) -> None:
        if self.heat >= HEAT_MAX:
            self._end_game()
            return
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_super(self) -> None:
        if not self.super_mode:
            return
        self.super_timer -= 1
        if self.super_timer <= 0:
            self.super_mode = False
            self.combo = 0
            self.current_color = None
        else:
            if self._frame % 2 == 0:
                color = self._rng.choice(BUOY_COLORS)
                ox = self._rng.uniform(-14, 14)
                oy = self._rng.uniform(-8, 8)
                self.particles.append(
                    Particle(
                        self.raft_x + ox,
                        self.raft_y + oy,
                        self._rng.uniform(-0.5, 0.5),
                        self._rng.uniform(-0.5, 0.5),
                        self._rng.randint(10, 15),
                        color,
                    )
                )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.7
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _update_ghost_trail(self) -> None:
        if self._frame % 3 == 0:
            self.ghost_trail.append(
                GhostPoint(self.raft_x, self.raft_y, self._frame)
            )

    # ── Helpers ──

    def _add_score(self, points: int) -> None:
        self.score += points

    def _spawn_particles(
        self,
        x: float,
        y: float,
        count: int,
        color: int,
        vel_range: float = 2.0,
        life_min: int = 10,
        life_max: int = 25,
    ) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x,
                    y,
                    self._rng.uniform(-vel_range, vel_range),
                    self._rng.uniform(-vel_range, vel_range),
                    self._rng.randint(life_min, life_max),
                    color,
                )
            )

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x, y, text, life=36, color=color))

    # ── Draw ──

    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.cls(DARK_BLUE)
        # Decorative waves
        t = pyxel.frame_count * 0.05
        for y in range(0, SCREEN_H, 4):
            off = int(math.sin(y * 0.05 + t) * 3)
            pyxel.pset(off, y, LIGHT_BLUE)
            pyxel.pset(SCREEN_W - 1 - off, y, LIGHT_BLUE)

        pyxel.text(SCREEN_W // 2 - 30, 50, "RAFT SURGE", WHITE)
        pyxel.text(SCREEN_W // 2 - 58, 85, "STEER: LEFT / RIGHT", LIGHT_BLUE)
        pyxel.text(SCREEN_W // 2 - 50, 97, "AVOID ROCKS", LIGHT_BLUE)
        pyxel.text(SCREEN_W // 2 - 68, 109, "MATCH BUOY COLORS", LIGHT_BLUE)
        pyxel.text(SCREEN_W // 2 - 60, 121, "4x COMBO = SUPER PADDLE", YELLOW)

        if self.best_score > 0:
            best_text = f"BEST SCORE: {self.best_score}"
            pyxel.text(
                SCREEN_W // 2 - len(best_text) * 2, 150, best_text, YELLOW
            )

        pyxel.text(SCREEN_W // 2 - 48, 190, "PRESS SPACE TO START", WHITE)

    def _draw_playing(self) -> None:
        self._draw_river()
        self._draw_ghost_trail()
        self._draw_rocks()
        self._draw_buoys()
        self._draw_particles()
        self._draw_raft()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_river(self) -> None:
        pyxel.cls(DARK_BLUE)
        t = self._frame * 0.05
        for y in range(0, SCREEN_H, 4):
            off = int(math.sin(y * 0.05 + t) * 3)
            pyxel.pset(off, y, LIGHT_BLUE)
            pyxel.pset(SCREEN_W - 1 - off, y, LIGHT_BLUE)

    def _draw_ghost_trail(self) -> None:
        if not self.best_ghost:
            return
        for i, gp in enumerate(self.best_ghost):
            if i % 3 != 0:
                continue
            if 0 <= gp.y < SCREEN_H:
                pyxel.pset(int(gp.x), int(gp.y), PINK)

    def _draw_rocks(self) -> None:
        for r in self.rocks:
            rx = int(r.x)
            ry = int(r.y)
            pyxel.circ(rx, ry, ROCK_RADIUS, BROWN)
            pyxel.circb(rx, ry, ROCK_RADIUS, WHITE)
            # Detail lines
            pyxel.circ(rx - 2, ry - 2, 2, WHITE)

    def _draw_buoys(self) -> None:
        for b in self.buoys:
            if b.collected:
                continue
            bx = int(b.x)
            by = int(b.y)
            pyxel.circ(bx, by, BUOY_RADIUS, b.color)
            pyxel.circb(bx, by, BUOY_RADIUS, WHITE)
            # Inner ring
            pyxel.circb(bx, by, 3, WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_raft(self) -> None:
        rx = int(self.raft_x)
        ry = int(self.raft_y)
        hw = RAFT_W // 2
        hh = RAFT_H // 2

        if self.super_mode:
            ci = (self._frame // 4) % 4
            body_color = BUOY_COLORS[ci]
            pyxel.rect(rx - hw, ry - hh, RAFT_W, RAFT_H, body_color)
            pyxel.rectb(rx - hw, ry - hh, RAFT_W, RAFT_H, WHITE)
            pyxel.rectb(rx - hw - 1, ry - hh - 1, RAFT_W + 2, RAFT_H + 2, ORANGE)
        else:
            pyxel.rect(rx - hw, ry - hh, RAFT_W, RAFT_H, CYAN)
            pyxel.rectb(rx - hw, ry - hh, RAFT_W, RAFT_H, WHITE)

        # Prow triangle
        pyxel.tri(rx, ry - hh - 4, rx - 5, ry - hh, rx + 5, ry - hh, WHITE)

        # Stun indicator
        if self.stun_timer > 0:
            pyxel.text(rx - 8, ry + hh + 4, "STUN", RED)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life <= 0:
                continue
            c = ft.color if ft.life > 10 else GRAY
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, c)

    def _draw_hud(self) -> None:
        # Score — top left
        pyxel.text(4, 2, f"SCORE:{self.score}", WHITE)

        # Combo — top center
        if self.combo > 1:
            combo_text = f"COMBO x{self.combo}"
            pyxel.text(
                SCREEN_W // 2 - len(combo_text) * 2, 2, combo_text, YELLOW
            )

        # HEAT bar — top right
        bar_x = 254
        bar_w = 56
        bar_h = 6
        bar_y = 3
        ratio = self.heat / HEAT_MAX
        pyxel.text(bar_x - 16, 2, "HEAT", WHITE)
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        if ratio > 0.7:
            bar_col = RED
        elif ratio > 0.4:
            bar_col = ORANGE
        elif ratio > 0.2:
            bar_col = YELLOW
        else:
            bar_col = GREEN
        pyxel.rect(bar_x, bar_y, int(bar_w * ratio), bar_h, bar_col)

        # Timer — bottom right
        seconds = max(0, self.timer // 60)
        timer_text = f"TIME:{seconds:02d}"
        pyxel.text(SCREEN_W - len(timer_text) * 4 - 4, SCREEN_H - 10, timer_text, WHITE)

        # SUPER counter
        if self.super_mode:
            sup_sec = self.super_timer / 60
            sup_text = f"SUPER {sup_sec:.1f}s"
            pyxel.text(
                SCREEN_W // 2 - len(sup_text) * 2, 12, sup_text, ORANGE
            )

    def _draw_game_over(self) -> None:
        pyxel.cls(DARK_BLUE)
        t = pyxel.frame_count * 0.05
        for y in range(0, SCREEN_H, 4):
            off = int(math.sin(y * 0.05 + t) * 3)
            pyxel.pset(off, y, LIGHT_BLUE)
            pyxel.pset(SCREEN_W - 1 - off, y, LIGHT_BLUE)

        pyxel.text(SCREEN_W // 2 - 24, 50, "GAME OVER", RED)

        score_text = f"SCORE: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_text) * 2, 80, score_text, WHITE)

        combo_text = f"MAX COMBO: {self.max_combo}"
        pyxel.text(SCREEN_W // 2 - len(combo_text) * 2, 95, combo_text, YELLOW)

        if self.score >= self.best_score and self.best_score > 0:
            pyxel.text(SCREEN_W // 2 - 24, 115, "NEW BEST!", ORANGE)
        elif self.best_score > 0:
            best_text = f"BEST: {self.best_score}"
            pyxel.text(SCREEN_W // 2 - len(best_text) * 2, 115, best_text, WHITE)

        pyxel.text(SCREEN_W // 2 - 48, 180, "PRESS SPACE TO RETRY", WHITE)


if __name__ == "__main__":
    Game()
