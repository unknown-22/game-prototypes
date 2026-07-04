"""
STEADY CHAIN — Operation-style steady hand maze
Navigate narrow paths, chain same-color checkpoints for COMBO,
trigger SUPER STEADY for massive score.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


# ---------------------------------------------------------------------------
# Enums & constants
# ---------------------------------------------------------------------------

class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# Colors (raw ints per pyxel palette)
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

CHECKPOINT_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
COLOR_NAMES: list[str] = ["RED", "GREEN", "BLUE", "YELLOW"]
SUPER_RAINBOW: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]

SCREEN_W = 320
SCREEN_H = 240
PATH_WIDTH = 24
CURSOR_RADIUS = 4
CHECKPOINT_RADIUS = 10
CURSOR_SPEED = 2.0
SUPER_DURATION = 300
SUPER_AUTO_SPEED = 1.5
HEAT_MAX = 100
GAME_TIME = 60 * 60
NUM_CHECKPOINTS = 8
CHECKPOINT_RESPAWN_DELAY = 60
SUPER_COOLDOWN = 60
WALL_HEAT = 5
WRONG_COLOR_HEAT = 15
HEAT_DECAY = 0.03
MAX_PARTICLES = 50
MAX_FLOATS = 10
FLOAT_LIFE = 30
SHAKE_FRAMES_WALL = 3
SHAKE_AMPLITUDE_WALL = 3
SHAKE_FRAMES_SUPER = 8
SHAKE_AMPLITUDE_SUPER = 5


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

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
class Checkpoint:
    x: int
    y: int
    color: int
    collected: bool = False
    respawn_timer: int = 0


@dataclass
class PathSegment:
    x1: int
    y1: int
    x2: int
    y2: int
    width: int = PATH_WIDTH


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------

class Game:
    SCREEN_W = SCREEN_W
    SCREEN_H = SCREEN_H
    PATH_WIDTH = PATH_WIDTH
    CURSOR_RADIUS = CURSOR_RADIUS
    CHECKPOINT_RADIUS = CHECKPOINT_RADIUS
    CURSOR_SPEED = CURSOR_SPEED
    SUPER_DURATION = SUPER_DURATION
    HEAT_MAX = HEAT_MAX
    GAME_TIME = GAME_TIME
    NUM_CHECKPOINTS = NUM_CHECKPOINTS
    COLORS = CHECKPOINT_COLORS
    COLOR_NAMES = COLOR_NAMES

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="STEADY CHAIN")
        self.reset()
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------
    # State initialisation
    # ------------------------------------------------------------------

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.cursor_x: float = 50.0
        self.cursor_y: float = 30.0
        self.combo: int = 0
        self.max_combo: int = 0
        self.last_color: int | None = None
        self.score: int = 0
        self.heat: float = 0.0
        self.timer: int = GAME_TIME
        self.super_timer: int = 0
        self.super_cooldown: int = 0
        self.checkpoints: list[Checkpoint] = []
        self.path_segments: list[PathSegment] = []
        self.particles: list[Particle] = []
        self.floats: list[FloatText] = []
        self.shake_x: int = 0
        self.shake_y: int = 0
        self.shake_frames: int = 0
        self._rng: random.Random = random.Random()

        self._build_path()
        self._spawn_checkpoints()

        self.combo = 0
        self.max_combo = 0
        self.last_color = None
        self.score = 0
        self.heat = 0.0
        self.timer = GAME_TIME
        self.super_timer = 0
        self.super_cooldown = 0
        self.shake_x = 0
        self.shake_y = 0
        self.shake_frames = 0
        self.particles.clear()
        self.floats.clear()

    def _build_path(self) -> None:
        w = PATH_WIDTH
        self.path_segments = [
            PathSegment(30, 30, 200, 30, w),
            PathSegment(200, 30, 200, 80, w),
            PathSegment(200, 80, 50, 80, w),
            PathSegment(50, 80, 50, 130, w),
            PathSegment(50, 130, 270, 130, w),
            PathSegment(270, 130, 270, 200, w),
            PathSegment(270, 200, 40, 200, w),
            PathSegment(40, 200, 40, 70, w),
            PathSegment(40, 70, 180, 70, w),
            PathSegment(180, 70, 180, 110, w),
            PathSegment(180, 110, 60, 110, w),
            PathSegment(60, 110, 60, 170, w),
            PathSegment(60, 170, 250, 170, w),
            PathSegment(250, 170, 250, 100, w),
            PathSegment(250, 100, 80, 100, w),
            PathSegment(80, 100, 80, 150, w),
            PathSegment(80, 150, 220, 150, w),
            PathSegment(220, 150, 220, 120, w),
            PathSegment(220, 120, 100, 120, w),
            PathSegment(100, 120, 100, 140, w),
        ]
        self.cursor_x = 52.0
        self.cursor_y = 30.0

    def _get_path_points(self) -> list[tuple[int, int]]:
        """Return all pixel positions along the path centre-lines (sampled)."""
        points: list[tuple[int, int]] = []
        for seg in self.path_segments:
            if seg.y1 == seg.y2:
                step = 1 if seg.x2 >= seg.x1 else -1
                for x in range(seg.x1, seg.x2 + step, step):
                    points.append((x, seg.y1))
            else:
                step = 1 if seg.y2 >= seg.y1 else -1
                for y in range(seg.y1, seg.y2 + step, step):
                    points.append((seg.x1, y))
        return points

    def _spawn_checkpoints(self) -> None:
        path_points = self._get_path_points()
        if not path_points:
            return

        self.checkpoints.clear()
        used_set: set[tuple[int, int]] = set()
        color_index = 0
        attempts = 0
        while len(self.checkpoints) < NUM_CHECKPOINTS and attempts < 2000:
            attempts += 1
            px, py = self._rng.choice(path_points)
            key = (px, py)
            if key in used_set:
                continue
            too_close = False
            for existing in self.checkpoints:
                if abs(px - existing.x) < 24 and abs(py - existing.y) < 24:
                    too_close = True
                    break
            if too_close:
                continue
            used_set.add(key)
            color = CHECKPOINT_COLORS[color_index % len(CHECKPOINT_COLORS)]
            color_index += 1
            self.checkpoints.append(Checkpoint(x=px, y=py, color=color))

    def _respawn_checkpoint(self, cp: Checkpoint) -> None:
        path_points = self._get_path_points()
        if not path_points:
            return

        occupied: set[tuple[int, int]] = set()
        for c in self.checkpoints:
            if c is not cp and not c.collected:
                occupied.add((c.x, c.y))

        for _ in range(200):
            px, py = self._rng.choice(path_points)
            key = (px, py)
            if key in occupied:
                continue
            too_close = False
            for c in self.checkpoints:
                if c is cp:
                    continue
                if abs(px - c.x) < 20 and abs(py - c.y) < 20:
                    too_close = True
                    break
            if too_close:
                continue
            cp.x = px
            cp.y = py
            cp.color = self._rng.choice(CHECKPOINT_COLORS)
            cp.collected = False
            cp.respawn_timer = 0
            return

        cp.collected = False
        cp.respawn_timer = 0

    # ------------------------------------------------------------------
    # Pure-logic helpers (testable)
    # ------------------------------------------------------------------

    def _is_on_path(self, x: float, y: float) -> bool:
        hw = PATH_WIDTH / 2
        for seg in self.path_segments:
            if seg.y1 == seg.y2:
                x1, x2 = (seg.x1, seg.x2) if seg.x2 >= seg.x1 else (seg.x2, seg.x1)
                if x1 - hw <= x <= x2 + hw and abs(y - seg.y1) <= hw:
                    return True
            else:
                y1, y2 = (seg.y1, seg.y2) if seg.y2 >= seg.y1 else (seg.y2, seg.y1)
                if y1 - hw <= y <= y2 + hw and abs(x - seg.x1) <= hw:
                    return True
        return False

    def _check_checkpoint_collision(self, cx: float, cy: float) -> Checkpoint | None:
        for cp in self.checkpoints:
            if cp.collected:
                continue
            dx = cx - cp.x
            dy = cy - cp.y
            if dx * dx + dy * dy <= CHECKPOINT_RADIUS * CHECKPOINT_RADIUS:
                return cp
        return None

    def _process_checkpoint(self, cp: Checkpoint) -> tuple[int, int]:
        """Returns (score_added, heat_added). Modifies self.combo / self.last_color."""
        is_super = self.super_timer > 0
        if is_super or cp.color == self.last_color:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            score_add = self._compute_score(10, self.combo, is_super)
            heat_add = 0
        else:
            self.combo = 0
            score_add = self._compute_score(10, 0, is_super)
            heat_add = WRONG_COLOR_HEAT
        self.last_color = cp.color
        return (score_add, heat_add)

    def _update_heat(self, amount: float) -> bool:
        """Apply heat change. Returns True if game-over (HEAT >= MAX)."""
        self.heat += amount
        if self.heat < 0:
            self.heat = 0
        if self.heat > HEAT_MAX:
            self.heat = HEAT_MAX
        return self.heat >= HEAT_MAX

    def _compute_score(self, base: int, combo: int, super_active: bool) -> int:
        mult = 3 if super_active else 1
        return int(base * (1 + combo * 0.5) * mult)

    def _can_activate_super(self) -> bool:
        return self.combo >= 4 and self.super_cooldown <= 0

    # ------------------------------------------------------------------
    # Particles & floating text
    # ------------------------------------------------------------------

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            if len(self.particles) >= MAX_PARTICLES:
                break
            angle = self._rng.uniform(0, math.tau)
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    color=color,
                    life=15 + self._rng.randint(0, 15),
                )
            )

    def _spawn_float_text(self, x: float, y: float, text: str, color: int) -> None:
        if len(self.floats) >= MAX_FLOATS:
            return
        self.floats.append(FloatText(x=x, y=y, text=text, color=color, life=FLOAT_LIFE))

    def _update_particles_and_floats(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

        for ft in self.floats:
            ft.y -= 0.6
            ft.life -= 1
        self.floats = [ft for ft in self.floats if ft.life > 0]

    # ------------------------------------------------------------------
    # Shake
    # ------------------------------------------------------------------

    def _start_shake(self, frames: int, amplitude: int) -> None:
        self.shake_frames = max(self.shake_frames, frames)
        self.shake_amplitude = max(
            getattr(self, "shake_amplitude", 0), amplitude
        )

    def _update_shake(self) -> None:
        if self.shake_frames > 0:
            self.shake_x = self._rng.randint(-self.shake_amplitude, self.shake_amplitude)
            self.shake_y = self._rng.randint(-self.shake_amplitude, self.shake_amplitude)
            self.shake_frames -= 1
        else:
            self.shake_x = 0
            self.shake_y = 0

    # ------------------------------------------------------------------
    # Super activation
    # ------------------------------------------------------------------

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self._start_shake(SHAKE_FRAMES_SUPER, SHAKE_AMPLITUDE_SUPER)
        self._spawn_particles(self.cursor_x, self.cursor_y, YELLOW, 20)
        self._spawn_float_text(self.cursor_x, self.cursor_y - 14, "SUPER!", YELLOW)
        for c in self.checkpoints:
            if not c.collected:
                self._spawn_particles(c.x, c.y, c.color, 3)

    # ------------------------------------------------------------------
    # Super auto-navigate: gentle pull toward nearest checkpoint
    # ------------------------------------------------------------------

    def _super_auto_pull(self) -> tuple[float, float]:
        """Return (dx, dy) velocity toward nearest uncollected checkpoint."""
        best_dx = 0.0
        best_dy = 0.0
        best_dist = float("inf")
        for cp in self.checkpoints:
            if cp.collected:
                continue
            dx = cp.x - self.cursor_x
            dy = cp.y - self.cursor_y
            dist_sq = dx * dx + dy * dy
            if dist_sq < best_dist:
                best_dist = dist_sq
                if dist_sq > 0:
                    inv = SUPER_AUTO_SPEED / math.sqrt(dist_sq)
                    best_dx = dx * inv
                    best_dy = dy * inv
                else:
                    best_dx = 0.0
                    best_dy = 0.0
        return best_dx, best_dy

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.phase = Phase.PLAYING
                self.reset()
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.phase = Phase.PLAYING
                self.reset()
        elif self.phase == Phase.PLAYING:
            self._update_playing()

    def _update_playing(self) -> None:
        self._update_shake()

        # Input
        dx = 0.0
        dy = 0.0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx -= CURSOR_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx += CURSOR_SPEED
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy -= CURSOR_SPEED
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy += CURSOR_SPEED

        # Super auto-pull
        if self.super_timer > 0:
            sx, sy = self._super_auto_pull()
            dx += sx
            dy += sy

        # Move and clamp to path
        new_x = self.cursor_x + dx
        new_y = self.cursor_y + dy

        new_x = max(0, min(SCREEN_W - 1, new_x))
        new_y = max(0, min(SCREEN_H - 1, new_y))

        if self._is_on_path(new_x, new_y):
            self.cursor_x = new_x
            self.cursor_y = new_y
        else:
            # Wall collision
            wall_touch = False
            if self._is_on_path(new_x, self.cursor_y):
                self.cursor_x = new_x
            else:
                wall_touch = True
            if self._is_on_path(self.cursor_x, new_y):
                self.cursor_y = new_y
            else:
                wall_touch = True

            if wall_touch:
                game_over = self._update_heat(WALL_HEAT)
                self.combo = 0
                self._start_shake(SHAKE_FRAMES_WALL, SHAKE_AMPLITUDE_WALL)
                self._spawn_particles(self.cursor_x, self.cursor_y, RED, 3)
                if game_over:
                    self.phase = Phase.GAME_OVER
                    return

        # Checkpoint collision
        cp = self._check_checkpoint_collision(self.cursor_x, self.cursor_y)
        if cp is not None:
            score_add, heat_add = self._process_checkpoint(cp)
            cp.collected = True
            cp.respawn_timer = CHECKPOINT_RESPAWN_DELAY

            self.score += score_add
            game_over = self._update_heat(heat_add)

            color = cp.color
            self._spawn_particles(cp.x, cp.y, color, 6)
            self._spawn_float_text(cp.x, cp.y - 8, f"+{score_add}", color)

            if self.combo >= 2:
                self._spawn_float_text(
                    cp.x + 6, cp.y - 16, f"COMBO x{self.combo}", WHITE
                )

            if self._can_activate_super():
                self._activate_super()

            if game_over:
                self.phase = Phase.GAME_OVER
                return

        # Update checkpoint respawn timers
        for cp in self.checkpoints:
            if cp.collected:
                cp.respawn_timer -= 1
                if cp.respawn_timer <= 0:
                    self._respawn_checkpoint(cp)

        # Timer
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self.phase = Phase.GAME_OVER
            return

        # HEAT decay
        self._update_heat(-HEAT_DECAY)

        # Super timer / cooldown
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_timer = 0
                self.combo = 0
                self.super_cooldown = SUPER_COOLDOWN
        if self.super_cooldown > 0:
            self.super_cooldown -= 1

        # Particles & floats
        self._update_particles_and_floats()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_hud()
            self._draw_path()
            self._draw_checkpoints()
            self._draw_cursor()
            self._draw_particles()
            self._draw_float_texts()
        elif self.phase == Phase.GAME_OVER:
            self._draw_hud()
            self._draw_path()
            self._draw_checkpoints()
            self._draw_cursor()
            self._draw_particles()
            self._draw_float_texts()
            self._draw_game_over_overlay()

    def _draw_title(self) -> None:
        pyxel.text(70, 70, "STEADY CHAIN", WHITE)
        pyxel.text(55, 100, "Navigate the narrow path", GRAY)
        pyxel.text(32, 112, "Collect same-color gems to build COMBO", GRAY)
        pyxel.text(48, 124, "COMBO x4 = SUPER STEADY!", YELLOW)
        pyxel.text(60, 150, "Arrow keys / WASD : Move", GRAY)
        pyxel.text(60, 162, "Avoid walls!  Watch your HEAT!", GRAY)
        pyxel.text(100, 190, "Press ENTER to start", WHITE)

    def _draw_hud(self) -> None:
        # HEAT bar background
        pyxel.rect(4, 4, 104, 10, DARK_BLUE)
        heat_width = int(self.heat / HEAT_MAX * 100)
        if heat_width > 0:
            heat_color = GREEN if self.heat < 50 else (
                RED if self.heat >= 80 else YELLOW
            )
            if self.heat < 50:
                heat_color = GREEN
            elif self.heat < 80:
                heat_color = YELLOW
            else:
                heat_color = RED
            pyxel.rect(6, 6, heat_width, 6, heat_color)
        pyxel.text(4, 16, f"HEAT {int(self.heat)}", GRAY)

        # Timer
        seconds = self.timer // 60
        pyxel.text(SCREEN_W // 2 - 16, 4, f"TIME {seconds}", WHITE)

        # Score
        pyxel.text(SCREEN_W - 70, 4, f"SCORE {self.score}", YELLOW)

        # COMBO
        if self.combo > 0:
            pyxel.text(SCREEN_W - 70, 14, f"COMBO x{self.combo}", WHITE)

        # SUPER bar
        if self.super_timer > 0:
            bar_y = 22
            pyxel.rect(4, bar_y, 104, 6, DARK_BLUE)
            super_pct = self.super_timer / SUPER_DURATION
            super_width = int(super_pct * 100)
            if super_width > 0:
                idx = (pyxel.frame_count // 4) % len(SUPER_RAINBOW)
                pyxel.rect(6, bar_y + 1, super_width, 4, SUPER_RAINBOW[idx])
            pyxel.text(4, bar_y + 8, "SUPER!", YELLOW)

    def _draw_path(self) -> None:
        ox = self.shake_x
        oy = self.shake_y
        hw = PATH_WIDTH / 2
        for seg in self.path_segments:
            if seg.y1 == seg.y2:
                x1 = min(seg.x1, seg.x2)
                x2 = max(seg.x1, seg.x2)
                rect_x = int(x1 - hw) + ox
                rect_y = int(seg.y1 - hw) + oy
                rect_w = int(x2 - x1 + PATH_WIDTH)
                rect_h = PATH_WIDTH
                pyxel.rectb(rect_x, rect_y, rect_w, rect_h, GRAY)
            else:
                y1 = min(seg.y1, seg.y2)
                y2 = max(seg.y1, seg.y2)
                rect_x = int(seg.x1 - hw) + ox
                rect_y = int(y1 - hw) + oy
                rect_w = PATH_WIDTH
                rect_h = int(y2 - y1 + PATH_WIDTH)
                pyxel.rectb(rect_x, rect_y, rect_w, rect_h, GRAY)

    def _draw_checkpoints(self) -> None:
        ox = self.shake_x
        oy = self.shake_y
        for cp in self.checkpoints:
            if cp.collected:
                continue
            if self.super_timer > 0:
                idx = (pyxel.frame_count // 4) % len(SUPER_RAINBOW)
                color = SUPER_RAINBOW[idx]
            else:
                color = cp.color
            px = cp.x + ox
            py = cp.y + oy
            pyxel.circb(px, py, CHECKPOINT_RADIUS, color)
            pyxel.circ(px, py, CHECKPOINT_RADIUS - 4, color)

    def _draw_cursor(self) -> None:
        ox = self.shake_x
        oy = self.shake_y
        px = int(self.cursor_x) + ox
        py = int(self.cursor_y) + oy

        if self.super_timer > 0:
            idx = (pyxel.frame_count // 4) % len(SUPER_RAINBOW)
            color = SUPER_RAINBOW[idx]
            pyxel.circ(px, py, CURSOR_RADIUS + 2, color)
            pyxel.circb(px, py, CURSOR_RADIUS + 4, color)
        else:
            pyxel.circ(px, py, CURSOR_RADIUS, WHITE)
            pyxel.circb(px, py, CURSOR_RADIUS + 1, GRAY)

    def _draw_particles(self) -> None:
        ox = self.shake_x
        oy = self.shake_y
        for p in self.particles:
            px = int(p.x) + ox
            py = int(p.y) + oy
            if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
                pyxel.pset(px, py, p.color)

    def _draw_float_texts(self) -> None:
        ox = self.shake_x
        oy = self.shake_y
        for ft in self.floats:
            px = int(ft.x) + ox
            py = int(ft.y) + oy
            # Fade out near end of life
            if ft.life < 8 and ft.life % 2 == 0:
                continue
            pyxel.text(px, py, ft.text, ft.color)

    def _draw_game_over_overlay(self) -> None:
        pyxel.rect(0, SCREEN_H // 2 - 30, SCREEN_W, 60, BLACK)
        pyxel.rectb(1, SCREEN_H // 2 - 29, SCREEN_W - 2, 58, GRAY)

        if self.heat >= HEAT_MAX:
            pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 - 18, "BUZZ!", RED)
        else:
            pyxel.text(SCREEN_W // 2 - 50, SCREEN_H // 2 - 18, "TIME'S UP", WHITE)

        pyxel.text(
            SCREEN_W // 2 - 40, SCREEN_H // 2 - 4,
            f"SCORE: {self.score}", YELLOW,
        )
        pyxel.text(
            SCREEN_W // 2 - 50, SCREEN_H // 2 + 8,
            f"MAX COMBO: {self.max_combo}", WHITE,
        )
        pyxel.text(
            SCREEN_W // 2 - 50, SCREEN_H // 2 + 20,
            "Press ENTER to retry", GRAY,
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    Game()
