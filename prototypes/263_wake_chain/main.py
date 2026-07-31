"""WAKE CHAIN — Jet Ski Color-Match COMBO Racer"""
from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ──
SCREEN_W = 320
SCREEN_H = 240
FPS = 30
GAME_DURATION = 1800

# Colors (raw ints)
C_BLACK = 0
C_NAVY = 1
C_PURPLE = 2
C_GREEN = 3
C_BROWN = 4
C_DARK_BLUE = 5
C_LIGHT_BLUE = 6
C_WHITE = 7
C_RED = 8
C_ORANGE = 9
C_YELLOW = 10
C_LIME = 11
C_CYAN = 12
C_GRAY = 13
C_PINK = 14
C_PEACH = 15

BUOY_COLORS = (C_RED, C_LIME, C_DARK_BLUE, C_YELLOW)
COLOR_NAMES = {C_RED: "RED", C_LIME: "LIME", C_DARK_BLUE: "D.BLUE", C_YELLOW: "YEL"}

PLAYER_Y = 160
PLAYER_SPEED = 3.0
PLAYER_RADIUS = 8
BUOY_RADIUS = 8
COLLECT_RADIUS = PLAYER_RADIUS + BUOY_RADIUS

SUPER_THRESHOLD = 4
SUPER_DURATION = 300

HEAT_MISMATCH = 15
HEAT_MISS = 5
HEAT_DECAY = 0.02
HEAT_CAP = 100


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Buoy:
    x: float
    y: float
    color: int
    alive: bool = True


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


@dataclass
class WakePoint:
    x: float
    y: float
    frame: int


class Game:
    def __init__(self) -> None:
        self._headless = False
        self.rng = random.Random()
        self.best_score = 0
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_active = False
        self.super_timer = 0
        self.super_mult = 1
        self.player_x = float(SCREEN_W // 2)
        self.player_color = BUOY_COLORS[0]
        self._color_timer = 0
        self._frame_count = 0
        self._spawn_timer = 0
        self._spawn_interval = 60
        self._buoy_speed = 1.0
        self._shake_frames = 0
        self._shake_x = 0
        self._shake_y = 0
        self.buoys: list[Buoy] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._wake_trail: deque[WakePoint] = deque(maxlen=360)
        self._wake_timer = 0
        self._game_over_reason = ""
        pyxel.init(SCREEN_W, SCREEN_H, title="WAKE CHAIN", fps=FPS, display_scale=2)
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_active = False
        self.super_timer = 0
        self.super_mult = 1
        self.player_x = float(SCREEN_W // 2)
        self.player_color = BUOY_COLORS[0]
        self._color_timer = 0
        self._frame_count = 0
        self._spawn_timer = 0
        self._spawn_interval = 60
        self._buoy_speed = 1.0
        self._shake_frames = 0
        self._shake_x = 0
        self._shake_y = 0
        self.buoys.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self._wake_trail.clear()
        self._wake_timer = 0
        self._game_over_reason = ""

    # ── Update ──

    def update(self) -> None:
        if self._headless:
            return

        match self.phase:
            case Phase.TITLE:
                self._update_title()
            case Phase.PLAYING:
                self._update_playing()
            case Phase.GAME_OVER:
                self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()

    def _update_playing(self) -> None:
        if self._shake_frames > 0:
            self._shake_frames -= 1
            self._shake_x = self.rng.randint(-3, 3)
            self._shake_y = self.rng.randint(-3, 3)
        else:
            self._shake_x = 0
            self._shake_y = 0

        self._handle_input()
        self._update_player_color()
        self._update_difficulty()
        self._update_timer()
        self._update_super()
        self._update_heat()
        self._spawn_buoys()
        self._update_buoys()
        self._update_particles()
        self._update_floating_texts()
        self._update_wake_trail()
        self._frame_count += 1

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()

    # ── Draw ──

    def draw(self) -> None:
        if self._headless:
            return

        match self.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.PLAYING:
                self._draw_playing()
            case Phase.GAME_OVER:
                self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.cls(C_DARK_BLUE)
        pyxel.text(SCREEN_W // 2 - 50, 40, "WAKE CHAIN", C_CYAN)
        pyxel.text(SCREEN_W // 2 - 65, 55, "Jet Ski Color-Match Racer", C_WHITE)
        pyxel.text(SCREEN_W // 2 - 68, 80, "Collect same-color buoys", C_LIGHT_BLUE)
        pyxel.text(SCREEN_W // 2 - 58, 90, "Build combos for points", C_LIGHT_BLUE)
        pyxel.text(SCREEN_W // 2 - 68, 100, "Combo x4 = SUPER WAKE!", C_YELLOW)
        pyxel.text(SCREEN_W // 2 - 75, 120, "LEFT/RIGHT arrow or A/D", C_WHITE)
        pyxel.text(SCREEN_W // 2 - 78, 130, "Avoid mismatches or HEAT!", C_RED)
        pyxel.text(SCREEN_W // 2 - 80, 160, "Click or press SPACE to start", C_CYAN)

        t = pyxel.frame_count
        for i in range(4):
            c = BUOY_COLORS[i]
            bx = SCREEN_W // 2 - 30 + i * 20
            by = 185 + math.sin(t * 0.05 + i) * 5
            pyxel.circ(int(bx), int(by), BUOY_RADIUS, c)

    def _draw_playing(self) -> None:
        sx = self._shake_x
        sy = self._shake_y
        pyxel.camera(sx, sy)

        pyxel.cls(C_DARK_BLUE)
        self._draw_water_current()
        self._draw_wake_trail()
        self._draw_buoys()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_player()
        self._draw_super_border()
        self._draw_hud()

        pyxel.camera(0, 0)

    def _draw_game_over(self) -> None:
        pyxel.cls(C_DARK_BLUE)
        pyxel.text(SCREEN_W // 2 - 43, 60, "GAME OVER", C_RED)
        pyxel.text(SCREEN_W // 2 - 50, 80, f"Score: {self.score}", C_WHITE)
        pyxel.text(SCREEN_W // 2 - 50, 95, f"Max Combo: {self.max_combo}", C_YELLOW)
        if self._game_over_reason:
            pyxel.text(SCREEN_W // 2 - len(self._game_over_reason) * 2, 115, self._game_over_reason, C_ORANGE)
        pyxel.text(SCREEN_W // 2 - 78, 150, "Click or press SPACE to restart", C_CYAN)

        if self.score > self.best_score:
            self.best_score = self.score
        pyxel.text(SCREEN_W // 2 - 55, 130, f"Best: {self.best_score}", C_LIME)

    # ── Input ──

    def _handle_input(self) -> None:
        if self._headless:
            return
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            self.player_x = max(20.0, self.player_x - PLAYER_SPEED)
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            self.player_x = min(300.0, self.player_x + PLAYER_SPEED)

    # ── Player color cycling ──

    def _update_player_color(self) -> None:
        self._color_timer += 1
        if self._color_timer >= 20:
            self._color_timer = 0
        idx = (self._color_timer // 5) % 4
        self.player_color = BUOY_COLORS[idx]

    # ── Difficulty ──

    def _escalate(self, start: float, end: float) -> float:
        t = min(1.0, self._frame_count / GAME_DURATION)
        return start + (end - start) * t

    def _update_difficulty(self) -> None:
        self._spawn_interval = self._escalate(60, 25)
        self._buoy_speed = self._escalate(1.0, 3.0)

    # ── Timer ──

    def _update_timer(self) -> None:
        if self._frame_count >= GAME_DURATION:
            self.phase = Phase.GAME_OVER
            self._game_over_reason = "Time Up!"

    # ── SUPER WAKE ──

    def _update_super(self) -> None:
        if self.super_active:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_active = False
                self.super_timer = 0
                self.super_mult = 1
                self._add_floating_text(
                    SCREEN_W // 2, SCREEN_H // 2 - 20, "WAKE END", C_CYAN, 45
                )

    # ── HEAT ──

    def _update_heat(self) -> None:
        if self.heat >= HEAT_CAP:
            self.phase = Phase.GAME_OVER
            self._game_over_reason = "OVERHEAT!"
            self._add_floating_text(SCREEN_W // 2, SCREEN_H // 2, "OVERHEAT!", C_RED, 60)
            self._shake_frames = 15
            for _ in range(30):
                p = Particle(
                    x=SCREEN_W // 2 + self.rng.uniform(-40, 40),
                    y=SCREEN_H // 2 + self.rng.uniform(-30, 30),
                    vx=self.rng.uniform(-3, 3),
                    vy=self.rng.uniform(-4, 1),
                    color=C_RED if self.rng.random() < 0.5 else C_ORANGE,
                    life=40,
                )
                self.particles.append(p)
            return
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    # ── Buoy spawning ──

    def _spawn_buoys(self) -> None:
        self._spawn_timer += 1
        active_buoys = sum(1 for b in self.buoys if b.alive)
        if self._spawn_timer >= self._spawn_interval and active_buoys < 8:
            self._spawn_timer = 0
            buoy = self._spawn_buoy()
            self.buoys.append(buoy)

    def _spawn_buoy(self) -> Buoy:
        return Buoy(
            x=self.rng.uniform(30, 290),
            y=-10.0,
            color=self.rng.choice(BUOY_COLORS),
        )

    # ── Buoy update ──

    def _update_buoys(self) -> None:
        px = self.player_x
        py_val = PLAYER_Y
        for buoy in self.buoys:
            if not buoy.alive:
                continue
            buoy.y += self._buoy_speed

            if buoy.y > 250:
                buoy.alive = False
                self.combo = 0
                if not self.super_active:
                    self.heat = min(HEAT_CAP, self.heat + HEAT_MISS)

            elif self._check_collection(buoy, px, py_val):
                self._collect_buoy(buoy)

        self.buoys = [b for b in self.buoys if b.alive]

    def _check_collection(self, buoy: Buoy, px: float, py_val: float) -> bool:
        dx = buoy.x - px
        dy = buoy.y - py_val
        dist = math.sqrt(dx * dx + dy * dy)
        return dist < COLLECT_RADIUS

    def _collect_buoy(self, buoy: Buoy) -> None:
        matched = buoy.color == self.player_color or self.super_active
        if matched:
            self.combo = min(99, self.combo + 1)
            self.max_combo = max(self.max_combo, self.combo)
            pts = int(10 * self.combo * self.super_mult)
            self.score += pts
            self._add_particles(buoy.x, buoy.y, self.player_color, 8, 20)
            self._add_floating_text(buoy.x, buoy.y - 5, f"+{pts}", self.player_color, 30)
            if self.combo >= SUPER_THRESHOLD and not self.super_active:
                self.super_active = True
                self.super_timer = SUPER_DURATION
                self.super_mult = 3
                self._add_floating_text(SCREEN_W // 2, SCREEN_H // 2 - 20, "SUPER WAKE!", C_YELLOW, 60)
                self._add_particles(SCREEN_W // 2, SCREEN_H // 2, C_YELLOW, 20, 30)
        else:
            self.combo = 0
            if not self.super_active:
                self.heat = min(HEAT_CAP, self.heat + HEAT_MISMATCH)
            self._add_particles(buoy.x, buoy.y, C_RED, 4, 15)
            self._add_floating_text(buoy.x, buoy.y - 5, "WRONG!", C_RED, 30)
        buoy.alive = False

    # ── Particles ──

    def _add_particles(self, x: float, y: float, color: int, count: int, life: int) -> None:
        for _ in range(count):
            p = Particle(
                x=x,
                y=y,
                vx=self.rng.uniform(-2, 2),
                vy=self.rng.uniform(-3, 1),
                color=color,
                life=life,
            )
            self.particles.append(p)

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ── Floating text ──

    def _add_floating_text(self, x: float, y: float, text: str, color: int, life: int) -> None:
        ft = FloatingText(x=x, y=y, text=text, color=color, life=life)
        self.floating_texts.append(ft)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ── Wake trail ──

    def _update_wake_trail(self) -> None:
        self._wake_timer += 1
        if self._wake_timer >= 5:
            self._wake_timer = 0
            wp = WakePoint(x=self.player_x, y=float(PLAYER_Y), frame=0)
            self._wake_trail.append(wp)
        for wp in self._wake_trail:
            wp.frame += 1
        while self._wake_trail and self._wake_trail[0].frame > 60:
            self._wake_trail.popleft()

    # ── Drawing helpers ──

    def _draw_water_current(self) -> None:
        t = pyxel.frame_count
        for i in range(8):
            base_y = (i * 30 + t * 1.5) % SCREEN_H
            for sx in range(0, SCREEN_W, 40):
                x1 = sx
                x2 = sx + 30
                y1 = base_y + math.sin(sx * 0.05 + t * 0.02) * 3
                y2 = base_y + math.sin((sx + 30) * 0.05 + t * 0.02) * 3
                pyxel.line(int(x1), int(y1), int(x2), int(y2), C_LIGHT_BLUE)

    def _draw_wake_trail(self) -> None:
        for wp in self._wake_trail:
            alpha = max(1, 4 - wp.frame // 15)
            if alpha > 0:
                pyxel.circ(int(wp.x), int(wp.y), alpha, C_CYAN)

    def _draw_buoys(self) -> None:
        for buoy in self.buoys:
            if buoy.alive:
                pyxel.circ(int(buoy.x), int(buoy.y), BUOY_RADIUS, buoy.color)
                pyxel.circb(int(buoy.x), int(buoy.y), BUOY_RADIUS, C_WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = min(15, max(1, p.life))
            pyxel.circ(int(p.x), int(p.y), 1 + p.life // 5, p.color if p.life > 5 else alpha)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life
            if alpha > 0:
                x = int(ft.x - len(ft.text) * 2)
                y = int(ft.y)
                pyxel.text(x, y, ft.text, ft.color)

    def _draw_player(self) -> None:
        t = pyxel.frame_count
        px = int(self.player_x)
        py_val = PLAYER_Y
        color = self.player_color

        if self.super_active:
            rc = BUOY_COLORS[(t // 5) % 4]
            glow_size = 12
            pyxel.tri(
                px, py_val - glow_size - 2,
                px - glow_size, py_val + glow_size - 2,
                px + glow_size, py_val + glow_size - 2,
                rc,
            )

        pyxel.tri(
            px, py_val - 12,
            px - 8, py_val + 8,
            px + 8, py_val + 8,
            color,
        )
        pyxel.trib(
            px, py_val - 12,
            px - 8, py_val + 8,
            px + 8, py_val + 8,
            C_WHITE,
        )

    def _draw_super_border(self) -> None:
        if not self.super_active:
            return
        t = pyxel.frame_count
        c = BUOY_COLORS[(t // 10) % 4]
        pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, c)
        pyxel.rectb(1, 1, SCREEN_W - 2, SCREEN_H - 2, c)

    def _draw_hud(self) -> None:
        pyxel.text(4, 2, f"SCORE: {self.score}", C_WHITE)
        combo_x = SCREEN_W // 2 - 20
        if self.combo > 1:
            pyxel.text(combo_x, 2, f"COMBO x{self.combo}", C_YELLOW)
        else:
            pyxel.text(combo_x, 2, f"COMBO x{self.combo}", C_GRAY)

        time_left = max(0, GAME_DURATION - self._frame_count)
        sec = time_left // FPS
        pyxel.text(SCREEN_W - 60, 2, f"TIME: {sec}", C_WHITE)

        if self.super_active:
            sup_sec = self.super_timer // FPS
            pyxel.text(SCREEN_W // 2 - 25, 12, f"SUPER WAKE {sup_sec}", C_YELLOW)

        bar_w = 100
        bar_h = 6
        bar_x = 10
        bar_y = SCREEN_H - 12
        fill_w = int(self.heat / HEAT_CAP * bar_w)
        if self.heat >= 75:
            bar_color = C_RED
        elif self.heat >= 40:
            bar_color = C_ORANGE
        else:
            bar_color = C_YELLOW

        pyxel.rectb(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2, C_WHITE)
        pyxel.rect(bar_x, bar_y, fill_w, bar_h, bar_color)
        pyxel.text(bar_x + bar_w + 6, bar_y - 1, "HEAT", C_WHITE)


# ── Headless test factory ──

def _make_game() -> Game:
    g = Game.__new__(Game)
    g._headless = True
    g.rng = random.Random(42)
    g.best_score = 0
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.super_active = False
    g.super_timer = 0
    g.super_mult = 1
    g.player_x = float(SCREEN_W // 2)
    g.player_color = BUOY_COLORS[0]
    g._color_timer = 0
    g._frame_count = 0
    g._spawn_timer = 0
    g._spawn_interval = 60
    g._buoy_speed = 1.0
    g._shake_frames = 0
    g._shake_x = 0
    g._shake_y = 0
    g.buoys = []
    g.particles = []
    g.floating_texts = []
    g._wake_trail = deque(maxlen=360)
    g._wake_timer = 0
    g._game_over_reason = ""
    g.reset()
    return g


if __name__ == "__main__":
    Game()
