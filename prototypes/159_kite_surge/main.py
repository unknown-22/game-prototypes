from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel


# --- Data Classes ---


@dataclass
class WindGust:
    x: float
    y: float
    vx: float
    color: int
    radius: int
    alive: bool = True


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    radius: float = 2.0


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int
    vy: float = -1.5


@dataclass
class EchoPoint:
    x: float
    y: float
    color: int
    alpha: float = 0.5


@dataclass
class TailSegment:
    x: float
    y: float
    color: int


# --- Phase Enum ---


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# --- Color Constants ---
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


class Game:
    SCREEN_W: ClassVar[int] = 320
    SCREEN_H: ClassVar[int] = 240
    KITE_X: ClassVar[float] = 80.0
    COLOR_CYCLE: ClassVar[list[int]] = [RED, GREEN, DARK_BLUE, YELLOW]
    COLOR_CYCLE_DURATION: ClassVar[int] = 180
    HEAT_MAX: ClassVar[float] = 100.0
    HEAT_PER_MISS: ClassVar[float] = 20.0
    HEAT_DECAY: ClassVar[float] = 0.02
    SUPER_DURATION: ClassVar[int] = 300
    GAME_DURATION: ClassVar[float] = 90.0
    KITE_SPEED: ClassVar[float] = 2.0
    KITE_Y_MIN: ClassVar[float] = 40.0
    KITE_Y_MAX: ClassVar[float] = 220.0
    BASE_SCORE: ClassVar[int] = 10
    MAX_GUSTS: ClassVar[int] = 12
    TAIL_COUNT: ClassVar[int] = 8
    RAINBOW_COLORS: ClassVar[list[int]] = [RED, ORANGE, YELLOW, GREEN, CYAN, PINK, PURPLE]

    def __init__(self) -> None:
        pyxel.init(self.SCREEN_W, self.SCREEN_H, title="KITE SURGE", display_scale=2)
        self.rng = random.Random()
        self.gusts: list[WindGust] = []
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self.echo_trail: list[EchoPoint] = []
        self.current_trail: list[EchoPoint] = []
        self.tail_segments: list[TailSegment] = []
        self.best_score: int = 0
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.kite_y: float = (self.KITE_Y_MIN + self.KITE_Y_MAX) / 2
        self.kite_color_idx: int = 0
        self.color_timer: int = self.COLOR_CYCLE_DURATION
        self.timer: float = self.GAME_DURATION
        self.gusts.clear()
        self.particles.clear()
        self.floats.clear()
        self.current_trail.clear()
        self.tail_segments.clear()
        for i in range(self.TAIL_COUNT):
            seg = TailSegment(x=self.KITE_X, y=self.kite_y, color=self.COLOR_CYCLE[0])
            self.tail_segments.append(seg)
        self.spawn_cooldown: int = 0
        self.heat_triggered: bool = False
        # Initialize sky decorations
        self._init_sky_decor()

    def _init_sky_decor(self) -> None:
        self.sky_stars: list[tuple[float, float]] = []
        for _ in range(30):
            sx = self.rng.uniform(0, self.SCREEN_W)
            sy = self.rng.uniform(0, self.SCREEN_H * 0.7)
            self.sky_stars.append((sx, sy))
        self.sky_bands: list[tuple[float, float, float]] = []
        for _ in range(4):
            by = self.rng.uniform(80, self.SCREEN_H - 20)
            bx = self.rng.uniform(0, self.SCREEN_W)
            bw = self.rng.uniform(40, 120)
            self.sky_bands.append((bx, by, bw))

    # ---- Phase Dispatch ----

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def draw(self) -> None:
        pyxel.cls(NAVY)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    # ---- Title Screen ----

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.phase = Phase.PLAYING
            self.reset_play_state()

    def reset_play_state(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_mode = False
        self.super_timer = 0
        self.kite_y = (self.KITE_Y_MIN + self.KITE_Y_MAX) / 2
        self.kite_color_idx = 0
        self.color_timer = self.COLOR_CYCLE_DURATION
        self.timer = self.GAME_DURATION
        self.gusts.clear()
        self.particles.clear()
        self.floats.clear()
        self.current_trail.clear()
        self.tail_segments.clear()
        for i in range(self.TAIL_COUNT):
            seg = TailSegment(x=self.KITE_X, y=self.kite_y, color=self.COLOR_CYCLE[0])
            self.tail_segments.append(seg)
        self.spawn_cooldown = 0
        self.heat_triggered = False

    def _draw_title(self) -> None:
        # Decorative floating gusts in background
        t = pyxel.frame_count * 0.02
        for i in range(8):
            gx = (self.SCREEN_W + 40 * i + pyxel.frame_count) % (self.SCREEN_W + 60) - 30
            gy = 60 + math.sin(t + i * 1.3) * 40
            col = self.COLOR_CYCLE[i % 4]
            pyxel.circb(int(gx), int(gy), 6, col)

        pyxel.text(160 - 40, 70, "KITE SURGE", WHITE)
        pyxel.text(160 - 72, 110, "Fly through matching winds!", GRAY)
        pyxel.text(160 - 56, 130, "UP/DOWN: steer kite", GRAY)
        pyxel.text(160 - 60, 145, "Match kite color -> COMBO!", GRAY)
        pyxel.text(160 - 52, 160, "Wrong color -> HEAT!", GRAY)
        pyxel.text(160 - 56, 175, "COMBO x4 -> SUPER KITE!", ORANGE)

        # Blinking PRESS SPACE
        if pyxel.frame_count % 60 < 30:
            pyxel.text(160 - 40, 200, "PRESS SPACE", YELLOW)

        # Best score display
        if self.best_score > 0:
            pyxel.text(160 - 30, 220, f"BEST: {self.best_score}", WHITE)

    # ---- Playing State ----

    def _update_playing(self) -> None:
        # Input
        y_input = 0
        if pyxel.btn(pyxel.KEY_UP):
            y_input = -1
        if pyxel.btn(pyxel.KEY_DOWN):
            y_input += 1

        self._update_kite(y_input)
        self._cycle_color()
        self._update_super_timer()
        self._spawn_gust()
        self._update_gusts()
        self._check_all_collisions()
        self._update_tail()
        self._update_particles()
        self._update_floats()
        self._update_heat()
        self._update_timer()
        self._record_trail()

    def _update_kite(self, y_input: int) -> None:
        self.kite_y += y_input * self.KITE_SPEED
        if self.kite_y < self.KITE_Y_MIN:
            self.kite_y = self.KITE_Y_MIN
        if self.kite_y > self.KITE_Y_MAX:
            self.kite_y = self.KITE_Y_MAX

    def _cycle_color(self) -> None:
        self.color_timer -= 1
        if self.color_timer <= 0:
            self.color_timer = self.COLOR_CYCLE_DURATION
            self.kite_color_idx = (self.kite_color_idx + 1) % len(self.COLOR_CYCLE)

    @property
    def kite_color(self) -> int:
        return self.COLOR_CYCLE[self.kite_color_idx]

    def _spawn_gust(self) -> None:
        if self.spawn_cooldown > 0:
            self.spawn_cooldown -= 1
            return
        if len([g for g in self.gusts if g.alive]) >= self.MAX_GUSTS:
            return
        y = self.rng.uniform(30, self.SCREEN_H - 20)
        # Higher altitude = faster gusts
        altitude_ratio = 1.0 - (y / self.SCREEN_H)
        speed = self.rng.uniform(0.8 + altitude_ratio * 1.0, 1.2 + altitude_ratio * 0.8)
        color = self.rng.choice(self.COLOR_CYCLE)
        radius = self.rng.randint(8, 12)
        gust = WindGust(x=float(self.SCREEN_W + radius), y=y, vx=-speed, color=color, radius=radius)
        self.gusts.append(gust)
        self.spawn_cooldown = self.rng.randint(30, 60)

    def _update_gusts(self) -> None:
        for g in self.gusts:
            g.x += g.vx
        self.gusts = [g for g in self.gusts if g.x > -20]

    def _check_collision(self, gust: WindGust) -> bool:
        if not gust.alive:
            return False
        dx = self.KITE_X - gust.x
        dy = self.kite_y - gust.y
        dist_sq = dx * dx + dy * dy
        collision_dist = 6.0 + gust.radius
        return dist_sq < collision_dist * collision_dist

    def _check_all_collisions(self) -> None:
        for gust in self.gusts:
            if not gust.alive:
                continue
            if self._check_collision(gust):
                self._resolve_gust(gust)

    def _resolve_gust(self, gust: WindGust) -> None:
        gust.alive = False

        if self.super_mode:
            self._handle_match(gust)
        elif gust.color == self.kite_color:
            self._handle_match(gust)
        else:
            self._handle_mismatch(gust)

    def _handle_match(self, gust: WindGust) -> None:
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo

        multiplier = 3.0 if self.super_mode else 1.0
        score_gain = int(self.BASE_SCORE * (1 + self.combo * 0.5) * multiplier)
        self.score += score_gain

        if not self.super_mode and self.combo >= 4:
            self._activate_super_mode()

        burst_color = gust.color
        if self.super_mode:
            burst_color = self.RAINBOW_COLORS[pyxel.frame_count % len(self.RAINBOW_COLORS)]

        self._spawn_particles(gust.x, gust.y, burst_color, 12 if self.super_mode else 8)
        self._add_float(gust.x, gust.y, f"+{score_gain}", burst_color)

    def _handle_mismatch(self, gust: WindGust) -> None:
        self.heat = min(self.HEAT_MAX, self.heat + self.HEAT_PER_MISS)
        self.combo = 0
        self._spawn_particles(gust.x, gust.y, GRAY, 5)
        self._add_float(gust.x, gust.y, "HEAT+20", RED)

    def _activate_super_mode(self) -> None:
        self.super_mode = True
        self.super_timer = self.SUPER_DURATION
        self._add_float(self.KITE_X, self.kite_y - 10, "SUPER!", ORANGE)

    def _update_super_timer(self) -> None:
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0

    def _update_heat(self) -> None:
        if self.heat >= self.HEAT_MAX:
            self.heat_triggered = True
            self._trigger_game_over()
            return
        self.heat = max(0.0, self.heat - self.HEAT_DECAY)

    def _update_timer(self) -> None:
        self.timer -= 1.0 / 60.0
        if self.timer <= 0:
            self.timer = 0
            self._trigger_game_over()

    def _trigger_game_over(self) -> None:
        if self.score > self.best_score:
            self.best_score = self.score
            self.echo_trail = list(self.current_trail)
        self.phase = Phase.GAME_OVER

    def _update_tail(self) -> None:
        active_color = self.kite_color
        if self.super_mode:
            active_color = self.RAINBOW_COLORS[(pyxel.frame_count // 4) % len(self.RAINBOW_COLORS)]

        # First segment follows kite
        if len(self.tail_segments) > 0:
            seg = self.tail_segments[0]
            seg.x += (self.KITE_X - seg.x) * 0.4
            seg.y += (self.kite_y - seg.y) * 0.4
            seg.color = active_color

        # Subsequent segments follow previous
        for i in range(1, len(self.tail_segments)):
            prev = self.tail_segments[i - 1]
            curr = self.tail_segments[i]
            curr.x += (prev.x - curr.x) * 0.3
            curr.y += (prev.y - curr.y) * 0.3
            curr.color = prev.color

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.pi * 2)
            speed = self.rng.uniform(0.5, 2.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 0.5
            life = self.rng.randint(10, 20)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color, radius=2))

    def _add_float(self, x: float, y: float, text: str, color: int) -> None:
        self.floats.append(FloatingText(x=x, y=y, text=text, life=30, color=color))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05  # gravity
            p.life -= 1
            if p.radius > 0:
                p.radius = max(0, p.radius - 0.1)
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floats(self) -> None:
        for f in self.floats:
            f.y += f.vy
            f.life -= 1
        self.floats = [f for f in self.floats if f.life > 0]

    def _record_trail(self) -> None:
        if pyxel.frame_count % 4 == 0:
            color = self.kite_color
            if self.super_mode:
                color = self.RAINBOW_COLORS[(pyxel.frame_count // 4) % len(self.RAINBOW_COLORS)]
            self.current_trail.append(EchoPoint(x=self.KITE_X, y=self.kite_y, color=color))

    # ---- Drawing ----

    def _draw_playing(self) -> None:
        self._draw_sky()
        self._draw_echo_trail()
        self._draw_current_trail()
        self._draw_gusts()
        self._draw_tail()
        self._draw_kite()
        self._draw_particles()
        self._draw_floats()
        self._draw_hud()
        self._draw_heat_bar()
        self._draw_color_indicator()

    def _draw_sky(self) -> None:
        # Lighter horizon band
        pyxel.rect(0, self.SCREEN_H - 60, self.SCREEN_W, 60, DARK_BLUE)
        pyxel.rect(0, self.SCREEN_H - 40, self.SCREEN_W, 40, PURPLE)

        # Stars / clouds
        for sx, sy in self.sky_stars:
            brightness = 7 if (sx * 7 + sy * 3 + pyxel.frame_count) % 120 < 80 else 13
            pyxel.pset(int(sx), int(sy), brightness)

        # Wind bands
        for bx, by, bw in self.sky_bands:
            wx = (bx - pyxel.frame_count * 0.3) % (self.SCREEN_W + bw) - bw
            pyxel.line(int(wx), int(by), int(wx + bw), int(by), LIGHT_BLUE)

    def _draw_echo_trail(self) -> None:
        if not self.echo_trail:
            return
        prev_x, prev_y = self.echo_trail[0].x, self.echo_trail[0].y
        for ep in self.echo_trail[1:]:
            # Use small dots connected by dim lines
            dx = ep.x - prev_x
            dy = ep.y - prev_y
            if abs(dx) + abs(dy) < 30:  # avoid teleport connecting lines
                pyxel.line(int(prev_x), int(prev_y), int(ep.x), int(ep.y), GRAY)
            prev_x, prev_y = ep.x, ep.y
        for ep in self.echo_trail:
            if ep.alpha > 0:
                pyxel.pset(int(ep.x), int(ep.y), GRAY)

    def _draw_current_trail(self) -> None:
        for ep in self.current_trail:
            if ep.alpha > 0:
                col = GRAY if not self.super_mode else ep.color
                pyxel.pset(int(ep.x), int(ep.y), col)

    def _draw_gusts(self) -> None:
        for gust in self.gusts:
            if not gust.alive:
                continue
            pyxel.circb(int(gust.x), int(gust.y), gust.radius, gust.color)
            pyxel.circ(int(gust.x), int(gust.y), gust.radius - 1, gust.color)

    def _draw_kite(self) -> None:
        color = self.kite_color
        if self.super_mode:
            color = self.RAINBOW_COLORS[(pyxel.frame_count // 4) % len(self.RAINBOW_COLORS)]
        # Kite triangle (upward pointing)
        pyxel.tri(int(self.KITE_X), int(self.kite_y - 10),
                  int(self.KITE_X - 8), int(self.kite_y + 5),
                  int(self.KITE_X + 8), int(self.kite_y + 5),
                  color)
        # Kite string
        pyxel.line(int(self.KITE_X), int(self.kite_y + 5),
                   int(self.KITE_X), self.SCREEN_H, GRAY)

    def _draw_tail(self) -> None:
        for i, seg in enumerate(self.tail_segments):
            r = max(1, 3 - i * 0.25)
            pyxel.circ(int(seg.x), int(seg.y), int(r), seg.color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            r = max(1, int(p.radius))
            alpha_intensity = (p.life / 20)
            if alpha_intensity > 0.3:
                pyxel.circ(int(p.x), int(p.y), r, p.color)

    def _draw_floats(self) -> None:
        for f in self.floats:
            alpha_intensity = f.life / 30.0
            if alpha_intensity > 0.2:
                pyxel.text(int(f.x) - len(f.text) * 2, int(f.y), f.text, f.color)

    def _draw_hud(self) -> None:
        # Score (top-left)
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)
        # Combo (top-center)
        combo_text = f"COMBO x{self.combo}"
        if self.super_mode and pyxel.frame_count % 30 < 15:
            combo_text = f"SUPER! x{self.combo}"
        pyxel.text(160 - len(combo_text) * 2, 4, combo_text, ORANGE if self.super_mode else WHITE)
        # Timer (top-right)
        timer_text = f"TIME: {self.timer:.0f}"
        pyxel.text(self.SCREEN_W - len(timer_text) * 4 - 4, 4, timer_text, WHITE)

    def _draw_heat_bar(self) -> None:
        bar_x = 60
        bar_y = self.SCREEN_H - 12
        bar_w = 200
        bar_h = 8
        # Background
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, DARK_BLUE)
        # Fill
        fill_w = int(bar_w * self.heat / self.HEAT_MAX)
        fill_color = RED
        if self.heat > 70:
            fill_color = ORANGE if pyxel.frame_count % 20 < 10 else RED
        if fill_w > 0:
            pyxel.rect(bar_x, bar_y, fill_w, bar_h, fill_color)
        # Label
        pyxel.text(bar_x - 30, bar_y, "HEAT", WHITE)
        # Danger indicator
        if self.heat > 70:
            danger_text = "WARNING!"
            pyxel.text(bar_x + bar_w + 4, bar_y, danger_text, RED)

    def _draw_color_indicator(self) -> None:
        color = self.kite_color
        if self.super_mode:
            color = self.RAINBOW_COLORS[(pyxel.frame_count // 4) % len(self.RAINBOW_COLORS)]
        pyxel.rect(int(self.KITE_X) + 12, int(self.kite_y) - 6, 6, 6, color)
        pyxel.text(int(self.KITE_X) + 20, int(self.kite_y) - 8, "YOU", WHITE)

    # ---- Game Over Screen ----

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.phase = Phase.PLAYING
            self.reset_play_state()

    def _draw_game_over(self) -> None:
        # Decorative elements
        for sx, sy in self.sky_stars:
            pyxel.pset(int(sx), int(sy), GRAY)

        pyxel.text(160 - 36, 60, "GAME OVER", RED)
        pyxel.text(160 - 30, 90, f"SCORE: {self.score}", WHITE)
        pyxel.text(160 - 28, 105, f"BEST: {self.best_score}", YELLOW)
        pyxel.text(160 - 44, 120, f"MAX COMBO: x{self.max_combo}", ORANGE)

        if self.heat_triggered:
            pyxel.text(160 - 44, 140, "LINE SNAPPED!", RED)
        else:
            pyxel.text(160 - 28, 140, "TIME UP!", GRAY)

        # Echo trail replay hint
        if self.echo_trail:
            pyxel.text(160 - 52, 160, "Best path shown as echo", GRAY)

        if pyxel.frame_count % 60 < 30:
            pyxel.text(160 - 52, 195, "PRESS SPACE TO RETRY", YELLOW)

        # Show echo trail of best run in background
        if self.echo_trail:
            prev_x, prev_y = self.echo_trail[0].x, self.echo_trail[0].y
            for ep in self.echo_trail[1:]:
                dx = ep.x - prev_x
                dy = ep.y - prev_y
                if abs(dx) + abs(dy) < 30:
                    pyxel.line(int(prev_x), int(prev_y), int(ep.x), int(ep.y), GRAY)
                prev_x, prev_y = ep.x, ep.y


# --- Entry Point ---


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
