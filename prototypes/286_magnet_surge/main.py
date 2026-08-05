"""MAGNET SURGE -- Color-match magnet physics game.

Core fun moment: 同じ色の金属片を連続で磁石に引き寄せてCOMBOを繋ぎ、
SUPER MAGNETで一気に回収するのが面白い
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import pyxel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCREEN_W = 320
SCREEN_H = 240
FPS = 60
GAME_TIME = 3600  # frames = 60 seconds
FONT_PATH = Path(__file__).with_name("k8x12.bdf")
FONT_W = 8
FONT_H = 12

# Scrap colors: RED=8, LIME=11, DARK_BLUE=5, YELLOW=10
SCRAP_COLORS: tuple[int, int, int, int] = (8, 11, 5, 10)

# Magnet physics
ATTRACT_RADIUS = 80.0
REPEL_RADIUS = 100.0
COLLECT_RADIUS = 12.0
ATTRACT_FORCE = 200.0
DAMPING = 0.98
BOUNCE_COEFFICIENT = 0.8
SUPER_RADIUS = 120.0
SUPER_DURATION = 300  # frames

# Scrap spawning
SCRAP_SIZE = 6
MAX_SCRAPS_START = 8
MAX_SCRAPS_END = 12
SPAWN_INTERVAL_START = 60
SPAWN_INTERVAL_END = 25
DRIFT_SPEED_START = 0.5
DRIFT_SPEED_END = 2.0
SCRAP_LIFE_START = 300
SCRAP_LIFE_END = 180

# Difficulty
DIFFICULTY_DURATION = GAME_TIME

# Heat
HEAT_MISMATCH = 15.0
HEAT_DECAY = 0.02
HEAT_MAX = 100.0

# Super
COMBO_FOR_SUPER = 4

# Score
BASE_SCORE = 10

# Particles
PARTICLE_COUNT = 8
PARTICLE_SPEED = 3.0
PARTICLE_LIFE = 20

# Floating text
FLOAT_TEXT_LIFE = 60
FLOAT_TEXT_SPEED = 1.0


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------
@dataclass
class Scrap:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int
    size: int = SCRAP_SIZE


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


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    def __init__(self) -> None:
        self.rng = random.Random()
        self.font: Path | None = None
        self._init_state()

    def _init_state(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_timer = 0
        self.timer = GAME_TIME
        self.best_score = 0
        self.polarity = True  # True=N/attract, False=S/repel
        self.last_color: int = -1
        self.scraps: list[Scrap] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.spawn_timer = 0
        self.mouse_x = 0
        self.mouse_y = 0
        self.rainbow_tick = 0
        self._elapsed_frames = 0

    def reset(self) -> None:
        best = self.best_score
        self._init_state()
        self.best_score = best
        self.rng = random.Random()
        self.phase = Phase.PLAYING

    # ── Helpers ──────────────────────────────────────────────────────────
    @property
    def is_super(self) -> bool:
        return self.super_timer > 0

    def _progress(self) -> float:
        elapsed = GAME_TIME - self.timer
        return min(elapsed / DIFFICULTY_DURATION, 1.0)

    def _lerp(self, a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    # ── Spawning ─────────────────────────────────────────────────────────
    def _spawn_scrap(self) -> None:
        max_scraps = int(self._lerp(MAX_SCRAPS_START, MAX_SCRAPS_END, self._progress()))
        if len(self.scraps) >= max_scraps:
            return

        color = self.rng.choice(SCRAP_COLORS)
        edge = self.rng.randint(0, 3)
        if edge == 0:  # top
            x = self.rng.uniform(0, SCREEN_W)
            y = -SCRAP_SIZE
        elif edge == 1:  # right
            x = SCREEN_W + SCRAP_SIZE
            y = self.rng.uniform(0, SCREEN_H)
        elif edge == 2:  # bottom
            x = self.rng.uniform(0, SCREEN_W)
            y = SCREEN_H + SCRAP_SIZE
        else:  # left
            x = -SCRAP_SIZE
            y = self.rng.uniform(0, SCREEN_H)

        drift_speed = self._lerp(DRIFT_SPEED_START, DRIFT_SPEED_END, self._progress())
        angle = self.rng.uniform(0, math.tau)
        vx = math.cos(angle) * drift_speed
        vy = math.sin(angle) * drift_speed

        scrap_life = int(self._lerp(SCRAP_LIFE_START, SCRAP_LIFE_END, self._progress()))
        self.scraps.append(Scrap(x=x, y=y, vx=vx, vy=vy, color=color, life=scrap_life))

    # ── Physics ──────────────────────────────────────────────────────────
    def _apply_magnet_force(self, scrap: Scrap) -> None:
        mx = float(self.mouse_x)
        my = float(self.mouse_y)
        dx = scrap.x - mx
        dy = scrap.y - my
        dist_sq = dx * dx + dy * dy

        if self.is_super:
            effective_radius = SUPER_RADIUS
            is_attract = True  # SUPER always attracts
        elif self.polarity:  # N pole = attract
            effective_radius = ATTRACT_RADIUS
            is_attract = True
        else:  # S pole = repel
            effective_radius = REPEL_RADIUS
            is_attract = False

        radius_sq = effective_radius * effective_radius
        if dist_sq < 0.01 or dist_sq > radius_sq:
            return

        dist = math.sqrt(dist_sq)
        force = ATTRACT_FORCE / dist_sq
        nx = dx / dist
        ny = dy / dist

        if is_attract:
            scrap.vx -= nx * force
            scrap.vy -= ny * force
        else:
            scrap.vx += nx * force
            scrap.vy += ny * force

    def _update_scraps(self) -> None:
        for scrap in self.scraps:
            self._apply_magnet_force(scrap)
            scrap.vx *= DAMPING
            scrap.vy *= DAMPING
            scrap.x += scrap.vx
            scrap.y += scrap.vy
            scrap.life -= 1

            if scrap.x < 0:
                scrap.x = 0
                scrap.vx = -scrap.vx * BOUNCE_COEFFICIENT
            elif scrap.x > SCREEN_W:
                scrap.x = SCREEN_W
                scrap.vx = -scrap.vx * BOUNCE_COEFFICIENT
            if scrap.y < 0:
                scrap.y = 0
                scrap.vy = -scrap.vy * BOUNCE_COEFFICIENT
            elif scrap.y > SCREEN_H:
                scrap.y = SCREEN_H
                scrap.vy = -scrap.vy * BOUNCE_COEFFICIENT

    def _check_collection(self) -> None:
        mx = float(self.mouse_x)
        my = float(self.mouse_y)
        collected: list[Scrap] = []

        for scrap in self.scraps:
            dx = scrap.x - mx
            dy = scrap.y - my
            dist_sq = dx * dx + dy * dy
            if dist_sq < COLLECT_RADIUS * COLLECT_RADIUS:
                collected.append(scrap)

        for scrap in collected:
            if self.is_super:
                multiplier = 3
                self.combo += 1
                self.score += BASE_SCORE * self.combo * multiplier
                self.max_combo = max(self.max_combo, self.combo)
                self._spawn_particles(scrap.x, scrap.y, scrap.color)
                self._spawn_floating_text(
                    scrap.x, scrap.y - 10,
                    f"+{BASE_SCORE * self.combo * multiplier}",
                    pyxel.COLOR_YELLOW,
                )
            elif self.last_color == -1 or scrap.color == self.last_color:
                self.combo += 1
                self.score += BASE_SCORE * self.combo
                self.max_combo = max(self.max_combo, self.combo)
                self._spawn_particles(scrap.x, scrap.y, scrap.color)
                self._spawn_floating_text(
                    scrap.x, scrap.y - 10,
                    f"+{BASE_SCORE * self.combo}",
                    self.last_color if self.last_color > 0 else scrap.color,
                )
            else:
                self.combo = 0
                self.heat += HEAT_MISMATCH
                self._spawn_floating_text(
                    scrap.x, scrap.y - 10, "WRONG!", pyxel.COLOR_RED,
                )

            self.last_color = scrap.color if scrap.color == self.last_color or self.last_color == -1 else -1
            if self.is_super:
                self.last_color = scrap.color
            self.scraps.remove(scrap)

        if self.combo >= COMBO_FOR_SUPER and self.super_timer <= 0:
            self._activate_super()

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self._spawn_floating_text(
            SCREEN_W // 2, SCREEN_H // 2 - 20,
            "SUPER MAGNET!",
            pyxel.COLOR_YELLOW,
        )

    # ── Heat ─────────────────────────────────────────────────────────────
    def _update_heat(self) -> None:
        self.heat = max(0.0, min(HEAT_MAX, self.heat - HEAT_DECAY))

    # ── Particles ────────────────────────────────────────────────────────
    def _spawn_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(PARTICLE_COUNT):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(1.0, PARTICLE_SPEED)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                color=color, life=PARTICLE_LIFE,
            ))

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    # ── Floating Text ────────────────────────────────────────────────────
    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, color=color, life=FLOAT_TEXT_LIFE))

    def _update_floating_texts(self) -> None:
        alive: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= FLOAT_TEXT_SPEED
            ft.life -= 1
            if ft.life > 0:
                alive.append(ft)
        self.floating_texts = alive

    # ── Difficulty ───────────────────────────────────────────────────────
    def _spawn_interval(self) -> int:
        return int(self._lerp(SPAWN_INTERVAL_START, SPAWN_INTERVAL_END, self._progress()))

    # ── Update ───────────────────────────────────────────────────────────
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            return
        if self.phase == Phase.GAME_OVER:
            return

        self._elapsed_frames += 1

        # Timer
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self._end_game()

        # Spawn
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_timer = self._spawn_interval()
            self._spawn_scrap()

        # Scrap update
        self._update_scraps()

        # Remove expired scraps (no penalty)
        self.scraps = [s for s in self.scraps if s.life > 0]

        # Collection
        self._check_collection()

        # Heat
        self._update_heat()
        if self.heat >= HEAT_MAX:
            self._end_game(overheat=True)

        # Super timer
        if self.super_timer > 0:
            self.super_timer -= 1
            self.rainbow_tick = (self.rainbow_tick + 1) % 5

        # Particles
        self._update_particles()

        # Floating texts
        self._update_floating_texts()

    def _end_game(self, overheat: bool = False) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score

    # ── Draw ─────────────────────────────────────────────────────────────
    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = "MAGNET SURGE"
        pyxel.text(SCREEN_W // 2 - len(title) * FONT_W // 2, 70, title, pyxel.COLOR_WHITE)

        lines = [
            "Move: Mouse    SPACE: Toggle Polarity",
            "Attract same-color scraps to build COMBO",
            "COMBO x4 = SUPER MAGNET (3x score!)",
            "Wrong color = HEAT (100 = GAME OVER)",
            "",
            "PRESS SPACE TO START",
        ]
        for i, line in enumerate(lines):
            y = 110 + i * (FONT_H + 2)
            pyxel.text(SCREEN_W // 2 - len(line) * FONT_W // 2, y, line, pyxel.COLOR_GRAY)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - len("GAME OVER") * FONT_W // 2, 60, "GAME OVER", pyxel.COLOR_RED)
        score_text = f"SCORE: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_text) * FONT_W // 2, 90, score_text, pyxel.COLOR_WHITE)
        combo_text = f"MAX COMBO: x{self.max_combo}"
        pyxel.text(SCREEN_W // 2 - len(combo_text) * FONT_W // 2, 108, combo_text, pyxel.COLOR_YELLOW)
        best_text = f"BEST: {self.best_score}"
        pyxel.text(SCREEN_W // 2 - len(best_text) * FONT_W // 2, 126, best_text, pyxel.COLOR_GRAY)

        if self.heat >= HEAT_MAX:
            reason = "OVERHEAT!"
        else:
            reason = "Time is up!"
        pyxel.text(SCREEN_W // 2 - len(reason) * FONT_W // 2, 150, reason, pyxel.COLOR_RED)

        retry = "PRESS R TO RETRY"
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(SCREEN_W // 2 - len(retry) * FONT_W // 2, 180, retry, pyxel.COLOR_YELLOW)

    def _draw_playing(self) -> None:
        self._draw_hud()
        self._draw_magnet_field()
        self._draw_scraps()
        self._draw_magnet()
        self._draw_particles()
        self._draw_floating_texts()

    def _draw_hud(self) -> None:
        # Timer
        seconds = self.timer // FPS
        time_text = f"TIME: {seconds}"
        pyxel.text(SCREEN_W // 2 - len(time_text) * FONT_W // 2, 4, time_text, pyxel.COLOR_WHITE)

        # Score
        score_text = f"{self.score}"
        pyxel.text(SCREEN_W - len(score_text) * FONT_W - 8, 4, score_text, pyxel.COLOR_WHITE)

        # Combo
        if self.combo > 1:
            combo_text = f"COMBO x{self.combo}"
            combo_color = pyxel.COLOR_YELLOW if self.combo >= COMBO_FOR_SUPER else pyxel.COLOR_GRAY
            pyxel.text(SCREEN_W - len(combo_text) * FONT_W - 8, FONT_H + 6, combo_text, combo_color)

        # Super timer
        if self.is_super:
            super_text = f"SUPER {self.super_timer // FPS + 1}s"
            pyxel.text(8, FONT_H + 6, super_text, pyxel.COLOR_YELLOW)

        # Heat bar
        bar_w = 80
        bar_h = 6
        bar_x = 8
        bar_y = 4
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, pyxel.COLOR_DARK_BLUE)
        fill_w = int(bar_w * (self.heat / HEAT_MAX))
        heat_color = pyxel.COLOR_GREEN
        if self.heat > 33:
            heat_color = pyxel.COLOR_YELLOW
        if self.heat > 66:
            heat_color = pyxel.COLOR_RED
        pyxel.rect(bar_x, bar_y, fill_w, bar_h, heat_color)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, pyxel.COLOR_WHITE)
        pyxel.text(bar_x + bar_w + 4, bar_y - 2, "HEAT", pyxel.COLOR_GRAY)

        # Polarity indicator
        pol_text = "N ATTRACT" if self.polarity else "S REPEL"
        pol_color = pyxel.COLOR_LIGHT_BLUE if self.polarity else pyxel.COLOR_RED
        pyxel.text(8, SCREEN_H - FONT_H - 4, pol_text, pol_color)

    def _draw_magnet(self) -> None:
        mx = self.mouse_x
        my = self.mouse_y

        if self.is_super:
            color = SCRAP_COLORS[self.rainbow_tick % 4]
            radius = int(SUPER_RADIUS)
        elif self.combo > 0 and self.last_color > 0:
            color = self.last_color
            radius = int(ATTRACT_RADIUS)
        else:
            color = pyxel.COLOR_WHITE
            radius = 0

        if radius > 0:
            pyxel.circb(mx, my, radius, color)
        if self.is_super:
            pyxel.circb(mx, my, int(SUPER_RADIUS) + 2, pyxel.COLOR_YELLOW)

        r = 10
        pyxel.circ(mx, my, r, color)
        if self.polarity:
            pyxel.text(mx - FONT_W // 2, my - FONT_H // 2, "N", pyxel.COLOR_LIGHT_BLUE)
        else:
            pyxel.text(mx - FONT_W // 2, my - FONT_H // 2, "S", pyxel.COLOR_RED)

    def _draw_magnet_field(self) -> None:
        if self.is_super:
            return
        mx = self.mouse_x
        my = self.mouse_y
        if self.polarity:
            pyxel.circb(mx, my, int(ATTRACT_RADIUS), pyxel.COLOR_LIGHT_BLUE)
        else:
            pyxel.circb(mx, my, int(REPEL_RADIUS), pyxel.COLOR_RED)

    def _draw_scraps(self) -> None:
        for scrap in self.scraps:
            x = int(scrap.x)
            y = int(scrap.y)
            s = scrap.size
            pyxel.rect(x - s // 2, y - s // 2, s, s, scrap.color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            color = p.color if p.color > 0 else pyxel.COLOR_WHITE
            alpha = p.life / PARTICLE_LIFE
            actual_color = color if alpha > 0.5 else pyxel.COLOR_GRAY
            pyxel.pset(int(p.x), int(p.y), actual_color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / FLOAT_TEXT_LIFE
            if alpha < 0.2:
                continue
            color = ft.color if alpha > 0.5 else pyxel.COLOR_GRAY
            pyxel.text(
                int(ft.x) - len(ft.text) * FONT_W // 2,
                int(ft.y),
                ft.text,
                color,
            )


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
class App:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="MAGNET SURGE", display_scale=2)
        if FONT_PATH.exists():
            pyxel.load(str(FONT_PATH))
        self.game = Game()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        g = self.game
        g.mouse_x = pyxel.mouse_x
        g.mouse_y = pyxel.mouse_y

        if g.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE):
                g.reset()
        elif g.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.KEY_RETURN):
                g.reset()
        elif g.phase == Phase.PLAYING:
            if pyxel.btnp(pyxel.KEY_SPACE):
                g.polarity = not g.polarity
            g.update()

    def draw(self) -> None:
        self.game.draw()


def main() -> None:
    App()


if __name__ == "__main__":
    main()
