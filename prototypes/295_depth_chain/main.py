"""DEPTH CHAIN -- Submarine Deep-Sea Color-Match Explorer."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ──
SCREEN_W = 320
SCREEN_H = 240
FPS = 60
GAME_DURATION = 3600
PLAYER_SPEED = 2.0
COLLECT_RADIUS = 20
SUPER_COLLECT_RADIUS = 40
SUPER_DURATION = 300
HEAT_MAX = 100
HEAT_MISMATCH = 15
HEAT_DECAY = 0.02
HEAT_DEPTH_THRESHOLD = 50
HEAT_DEPTH_RATE = 0.02

RED = 8
LIME = 11
DARK_BLUE = 5
YELLOW = 10
WHITE = 7
GREEN = 3
ORANGE = 9
CYAN = 12
BLACK = 0
NAVY = 1

CREATURE_COLORS: list[int] = [RED, LIME, DARK_BLUE, YELLOW]
SPAWN_INTERVAL_START = 90
SPAWN_INTERVAL_END = 30
MAX_CREATURES_START = 6
MAX_CREATURES_END = 14
DRIFT_SPEED_START = 0.3
DRIFT_SPEED_END = 1.0
LIFESPAN_START = 600
LIFESPAN_END = 300


# ── Data Classes ──
@dataclass
class Creature:
    x: float
    y: float
    color: int
    size: int
    vx: float
    vy: float
    life: int
    seed: float


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int
    size: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int
    vy: float


# ── Phase ──
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ── Game Class ──
class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="DEPTH CHAIN", fps=FPS)
        self._rng = random.Random()
        self.best_score = 0
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.player_x = 160.0
        self.player_y = 40.0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.last_color: int | None = None
        self.super_sonar_timer = 0
        self.timer = GAME_DURATION
        self.creatures: list[Creature] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._elapsed = 0
        self._spawn_timer = 0
        self._depth_reached = 0.0
        self._shake_offset_x = 0.0
        self._shake_offset_y = 0.0
        self._sonar_pulse_timer = 0
        self._spawn_interval = SPAWN_INTERVAL_START
        self._max_creatures = MAX_CREATURES_START
        self._drift_speed = DRIFT_SPEED_START
        self._lifespan = LIFESPAN_START

    # ── Update ──
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._start_game()

    def _start_game(self) -> None:
        self.phase = Phase.PLAYING
        self.player_x = 160.0
        self.player_y = 40.0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.last_color = None
        self.super_sonar_timer = 0
        self.timer = GAME_DURATION
        self.creatures.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self._elapsed = 0
        self._spawn_timer = 0
        self._depth_reached = 0.0
        self._shake_offset_x = 0.0
        self._shake_offset_y = 0.0
        self._sonar_pulse_timer = 0
        self._spawn_interval = SPAWN_INTERVAL_START
        self._max_creatures = MAX_CREATURES_START
        self._drift_speed = DRIFT_SPEED_START
        self._lifespan = LIFESPAN_START

    def _update_playing(self) -> None:
        self._handle_input()
        self._update_timer()
        self._update_depth()
        self._update_heat()
        self._update_difficulty()
        self._update_creatures()
        creature = self._check_collection()
        if creature is not None:
            self._handle_collection(creature)
        self._update_super_sonar()
        self._update_particles()
        self._update_floating_texts()
        self._update_shake()
        self._elapsed += 1

    def _handle_input(self) -> None:
        dx, dy = 0.0, 0.0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx -= PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx += PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy -= PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy += PLAYER_SPEED
        if dx != 0 and dy != 0:
            inv_sqrt2 = 1.0 / math.sqrt(2)
            dx *= inv_sqrt2
            dy *= inv_sqrt2
        self.player_x = max(8.0, min(SCREEN_W - 8.0, self.player_x + dx))
        self.player_y = max(8.0, min(SCREEN_H - 8.0, self.player_y + dy))

    def _update_depth(self) -> float:
        depth_pct = self.player_y / SCREEN_H
        depth_m = depth_pct * 100.0
        if depth_m > self._depth_reached:
            self._depth_reached = depth_m
        return 1.0 + depth_pct * 2.0

    def _update_heat(self) -> None:
        if self.heat >= HEAT_MAX:
            self._on_game_over()
            return
        depth_pct = self.player_y / SCREEN_H
        depth_val = depth_pct * 100.0
        if self.super_sonar_timer <= 0 and depth_val > HEAT_DEPTH_THRESHOLD:
            self.heat += HEAT_DEPTH_RATE * (depth_val / 100.0)
        if self.super_sonar_timer <= 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)
        if self.heat >= HEAT_MAX:
            self._on_game_over()

    def _update_timer(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self._on_game_over()

    def _update_difficulty(self) -> None:
        t = min(1.0, self._elapsed / GAME_DURATION)
        self._spawn_interval = int(SPAWN_INTERVAL_START + (SPAWN_INTERVAL_END - SPAWN_INTERVAL_START) * t)
        self._max_creatures = int(MAX_CREATURES_START + (MAX_CREATURES_END - MAX_CREATURES_START) * t)
        self._drift_speed = DRIFT_SPEED_START + (DRIFT_SPEED_END - DRIFT_SPEED_START) * t
        self._lifespan = int(LIFESPAN_START + (LIFESPAN_END - LIFESPAN_START) * t)

    def _spawn_creature(self) -> Creature:
        y: float
        if self._rng.random() < 0.8:
            y = self._rng.uniform(SCREEN_H * 0.5, SCREEN_H - 20)
        else:
            y = self._rng.uniform(20, SCREEN_H * 0.5)
        x = self._rng.uniform(20, SCREEN_W - 20)
        color = self._rng.choice(CREATURE_COLORS)
        size = self._rng.randint(8, 14)
        vx = self._rng.uniform(-self._drift_speed, self._drift_speed)
        vy = self._rng.uniform(-self._drift_speed * 0.5, self._drift_speed * 0.5)
        life = self._lifespan
        seed = self._rng.uniform(0, math.pi * 2)
        return Creature(x=x, y=y, color=color, size=size, vx=vx, vy=vy, life=life, seed=seed)

    def _update_creatures(self) -> None:
        self._spawn_timer -= 1
        if self._spawn_timer <= 0 and len(self.creatures) < self._max_creatures:
            self.creatures.append(self._spawn_creature())
            self._spawn_timer = self._spawn_interval
        for c in self.creatures[:]:
            c.life -= 1
            if c.life <= 0:
                self.creatures.remove(c)
                continue
            drift_x = math.sin(c.seed + self._elapsed * 0.02) * c.vx
            drift_y = math.cos(c.seed + self._elapsed * 0.03) * c.vy
            c.x += drift_x
            c.y += drift_y
            c.x = max(8.0, min(SCREEN_W - 8.0, c.x))
            c.y = max(8.0, min(SCREEN_H - 8.0, c.y))

    def _check_collection(self, player_x: float | None = None, player_y: float | None = None) -> Creature | None:
        px = player_x if player_x is not None else self.player_x
        py = player_y if player_y is not None else self.player_y
        radius = SUPER_COLLECT_RADIUS if self.super_sonar_timer > 0 else COLLECT_RADIUS
        for c in self.creatures[:]:
            dist = math.hypot(c.x - px, c.y - py)
            if dist <= radius:
                self.creatures.remove(c)
                return c
        return None

    def _handle_collection(self, creature: Creature) -> None:
        depth_mult = self._update_depth()
        is_super = self.super_sonar_timer > 0
        is_first = self.last_color is None
        color_matched = is_first or creature.color == self.last_color
        if is_super:
            color_matched = True

        if color_matched:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            score_mult = 3.0 if is_super else 1.0
            base_score = 10 * self.combo
            self.score += int(base_score * depth_mult * score_mult)
            self._spawn_particles(creature.x, creature.y, creature.color, 8)
            if is_super:
                self._spawn_particles(creature.x, creature.y, WHITE, 12)
            self._add_floating_text(
                creature.x, creature.y - 8,
                f"+{base_score}", creature.color,
            )
            if self.combo >= 4 and not is_super:
                self.super_sonar_timer = SUPER_DURATION
                self._sonar_pulse_timer = 0
                self._add_floating_text(
                    self.player_x, self.player_y - 16,
                    "SUPER SONAR!", YELLOW,
                )
            self.last_color = creature.color
        else:
            self.combo = 0
            self.heat += HEAT_MISMATCH
            self.score += int(5 * depth_mult)
            self._spawn_particles(creature.x, creature.y, WHITE, 4)
            self._add_floating_text(creature.x, creature.y - 8, "WRONG!", RED)
            self.last_color = None

    def _update_super_sonar(self) -> None:
        if self.super_sonar_timer > 0:
            self.super_sonar_timer -= 1
            self._sonar_pulse_timer -= 1
            if self._sonar_pulse_timer <= 0:
                self._sonar_pulse_timer = 30
            if self.super_sonar_timer <= 0:
                self.combo = 0
                self.last_color = None

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = self._rng.randint(15, 30)
            size = self._rng.randint(1, 3)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, color=color, life=life, size=size))

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        ft = FloatingText(x=float(int(x)), y=y, text=text, color=color, life=45, vy=-1.0)
        self.floating_texts.append(ft)

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    def _update_shake(self) -> None:
        if self.heat >= 70:
            intensity = (self.heat - 70) / 30.0 * 2.0
            self._shake_offset_x = self._rng.uniform(-intensity, intensity)
            self._shake_offset_y = self._rng.uniform(-intensity, intensity)
        else:
            self._shake_offset_x = 0.0
            self._shake_offset_y = 0.0

    def _on_game_over(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._start_game()

    # ── Draw ──
    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.cls(BLACK)
        pyxel.text(SCREEN_W // 2 - 42, 50, "DEPTH CHAIN", WHITE)
        pyxel.text(SCREEN_W // 2 - 64, 78, "Submarine Color-Match Explorer", CYAN)
        pyxel.text(SCREEN_W // 2 - 88, 110, "ARROW KEYS: Move submarine", GREEN)
        pyxel.text(SCREEN_W // 2 - 100, 126, "Collect same-color creatures for COMBO", GREEN)
        pyxel.text(SCREEN_W // 2 - 94, 142, "COMBO x4 = SUPER SONAR (rainbow mode)", GREEN)
        pyxel.text(SCREEN_W // 2 - 108, 158, "Deep = high score, Surface = safe HEAT", GREEN)
        pyxel.text(SCREEN_W // 2 - 74, 190, "Press SPACE or CLICK to start", YELLOW)

        pyxel.rect(SCREEN_W // 2 - 6, 210, 12, 8, RED)
        pyxel.tri(SCREEN_W // 2 - 6, 218, SCREEN_W // 2, 222, SCREEN_W // 2 + 6, 218, RED)

        for i, (cx, cy, col) in enumerate([
            (80, 50, LIME), (240, 70, YELLOW), (60, 80, DARK_BLUE), (260, 55, RED),
        ]):
            ox = math.sin(self._elapsed * 0.03 + i * 1.5) * 3
            oy = math.cos(self._elapsed * 0.04 + i * 1.5) * 3
            self._draw_creature_shape(cx + ox, cy + oy, col, 10)

    def _draw_playing(self) -> None:
        pyxel.cls(BLACK)
        shx = self._shake_offset_x
        shy = self._shake_offset_y
        self._draw_background()
        self._draw_depth_zones()
        self._draw_creatures()
        self._draw_particles(shx, shy)
        self._draw_player_submarine()
        self._draw_floating_texts(shx, shy)
        self._draw_super_sonar_effects()
        self._draw_hud()

    def _draw_background(self) -> None:
        for y in range(0, SCREEN_H, 4):
            t = y / SCREEN_H
            color = NAVY
            if t > 0.5:
                color = DARK_BLUE
            if t > 0.8:
                color = BLACK
            pyxel.rect(0, y, SCREEN_W, 4, color)

    def _draw_depth_zones(self) -> None:
        pyxel.text(2, 2, "SURFACE", CYAN)
        pyxel.text(2, SCREEN_H // 2 - 6, "TWILIGHT", DARK_BLUE)
        pyxel.text(2, SCREEN_H - 14, "ABYSS", RED)
        pyxel.line(0, int(SCREEN_H * 0.5), SCREEN_W, int(SCREEN_H * 0.5), 1)
        pyxel.line(0, int(SCREEN_H * 0.8), SCREEN_W, int(SCREEN_H * 0.8), 1)

    def _draw_creatures(self) -> None:
        for c in self.creatures:
            self._draw_creature_shape(c.x, c.y, c.color, c.size)

    def _draw_creature_shape(self, x: float, y: float, color: int, size: int) -> None:
        ix, iy = int(x), int(y)
        half = size // 2
        if color == RED:
            pyxel.ellib(ix - half, iy - half, ix + half, iy + half, color)
            pyxel.rect(ix - 2, iy + half, 2, 3, color)
        elif color == LIME:
            pyxel.tri(ix, iy - half, ix - half, iy + half, ix + half, iy + half, color)
            pyxel.rect(ix, iy - half - 2, 3, 2, color)
        elif color == DARK_BLUE:
            pyxel.ellib(ix - half, iy - half // 2, ix + half, iy + half // 2, color)
            pyxel.tri(ix - half, iy, ix - half - 4, iy - 3, ix - half - 4, iy + 3, color)
            pyxel.tri(ix + half, iy, ix + half + 4, iy - 3, ix + half + 4, iy + 3, color)
        elif color == YELLOW:
            for a in range(0, 360, 72):
                rad = math.radians(a)
                px = ix + int(math.cos(rad) * half * 0.9)
                py = iy + int(math.sin(rad) * half * 0.9)
                pyxel.line(ix, iy, px, py, color)

    def _draw_player_submarine(self) -> None:
        px, py = int(self.player_x), int(self.player_y)
        color = WHITE
        if self.heat >= 90 and self._elapsed % 10 < 5:
            color = RED
        if self.super_sonar_timer > 0:
            hue = (self._elapsed // 3) % 12
            rainbow_colors = [RED, ORANGE, YELLOW, LIME, GREEN, CYAN, DARK_BLUE, 2, 6, 12, 10, 8]
            color = rainbow_colors[hue]
        pyxel.tri(px - 8, py + 6, px, py + 10, px + 8, py + 6, color)
        propeller_angle = self._elapsed % 20
        if propeller_angle < 10:
            pyxel.rect(px - 1, py + 10, 2, 3, color)
        else:
            pyxel.rect(px - 1, py + 10, 2, 1, color)
        pyxel.ellib(px - 6, py - 4, px + 6, py + 6, color)
        pyxel.rect(px - 2, py - 8, 4, 5, color)
        pyxel.pset(px - 4, py - 2, BLACK)
        pyxel.pset(px + 4, py - 2, BLACK)

    def _draw_particles(self, shx: float, shy: float) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x + shx), int(p.y + shy), p.color)

    def _draw_floating_texts(self, shx: float, shy: float) -> None:
        for ft in self.floating_texts[:]:
            alpha = ft.life / 45.0
            col = ft.color if alpha > 0.3 else WHITE
            pyxel.text(int(ft.x + shx) - len(ft.text) * 2, int(ft.y + shy), ft.text, col)

    def _draw_super_sonar_effects(self) -> None:
        if self.super_sonar_timer > 0:
            hue = (self._elapsed // 3) % 12
            rainbow_colors = [RED, ORANGE, YELLOW, LIME, GREEN, CYAN, DARK_BLUE, 2, 6, 12, 10, 8]
            border_color = rainbow_colors[hue]
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, border_color)
            if self._sonar_pulse_timer == 30 or self._sonar_pulse_timer == 15:
                pulse_r = int((30 - self._sonar_pulse_timer) * 5 + 10)
                pyxel.circb(int(self.player_x), int(self.player_y), pulse_r, border_color)
                pyxel.circb(int(self.player_x), int(self.player_y), pulse_r + 2, rainbow_colors[(hue + 2) % 12])

    def _draw_hud(self) -> None:
        pyxel.text(4, 12, f"SCORE: {self.score}", WHITE)
        pyxel.text(4, 22, f"COMBO: x{self.combo}", YELLOW)

        depth_val = (self.player_y / SCREEN_H) * 100.0
        pyxel.text(SCREEN_W - 56, 12, f"DEPTH: {depth_val:.0f}m", CYAN)

        bar_w = SCREEN_W - 80
        timer_pct = self.timer / GAME_DURATION
        if timer_pct > 0.6:
            timer_col = GREEN
        elif timer_pct > 0.3:
            timer_col = YELLOW
        else:
            timer_col = RED
        pyxel.rect(40, 2, bar_w, 6, BLACK)
        pyxel.rect(40, 2, int(bar_w * timer_pct), 6, timer_col)
        pyxel.rectb(40, 2, bar_w, 6, WHITE)

        heat_bar_x = 8
        heat_bar_top = 40
        heat_bar_h = 160
        heat_pct = self.heat / HEAT_MAX
        if heat_pct <= 0.3:
            heat_col = GREEN
        elif heat_pct <= 0.6:
            heat_col = YELLOW
        elif heat_pct <= 0.8:
            heat_col = ORANGE
        else:
            heat_col = RED
        pyxel.rect(heat_bar_x, heat_bar_top, 8, heat_bar_h, BLACK)
        pyxel.rect(heat_bar_x, heat_bar_top + int(heat_bar_h * (1.0 - heat_pct)),
                   8, int(heat_bar_h * heat_pct), heat_col)
        pyxel.rectb(heat_bar_x, heat_bar_top, 8, heat_bar_h, WHITE)
        pyxel.text(2, heat_bar_top + heat_bar_h + 4, "HEAT", RED)

    def _draw_game_over(self) -> None:
        pyxel.cls(BLACK)
        pyxel.text(SCREEN_W // 2 - 30, 50, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 32, 85, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 44, 100, f"BEST: {self.best_score}", YELLOW)
        pyxel.text(SCREEN_W // 2 - 40, 123, f"MAX COMBO: x{self.max_combo}", LIME)
        pyxel.text(SCREEN_W // 2 - 52, 143, f"DEPTH REACHED: {self._depth_reached:.0f}m", CYAN)
        pyxel.text(SCREEN_W // 2 - 78, 180, "Press SPACE or CLICK to restart", GREEN)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
