"""ZIP SURGE — Side-view zipline action game with color-match COMBO system.

Core fun moment: building COMBO >= 4 triggers SUPER ZIP (rainbow ziplines,
3x score, auto-connect for 5 seconds) where score explodes.
Risk/reward: chase same-color ziplines for COMBO multiplier vs safe any-color
landing; wrong-color jumps reset COMBO and add HEAT (game over at HEAT >= 100).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ────────────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
DISPLAY_SCALE = 2
FPS = 60

PLAYER_RADIUS = 6
PLAYER_SCREEN_X = 80

JUMP_VELOCITY = -3.5
GRAVITY = 0.3
STEER_SPEED = 1.5
MAX_FALL_SPEED = 8.0

INITIAL_GAME_SPEED = 1.0
SPEED_INC_PER_FRAME = 0.001
MAX_GAME_SPEED = 2.5

SUPER_DURATION = 300  # 5 seconds at 60fps
COMBO_THRESHOLD = 4

BASE_SCORE_PER_LAND = 10
SAME_COLOR_SCORE = 5  # multiplied by combo
SUPER_LAND_SCORE = 50
SUPER_SCORE_MULT = 3

HEAT_PER_WRONG = 15.0
HEAT_DECAY = 0.5
HEAT_MAX = 100.0

ZIpline_MIN_LENGTH = 120
ZIpline_MAX_LENGTH = 240
ZIpline_Y_MIN = 30
ZIpline_Y_MAX = SCREEN_H - 40

SPAWN_INTERVAL_MIN = 40
SPAWN_INTERVAL_MAX = 60

PARTICLE_LAND_COUNT = 8
PARTICLE_SUPER_COUNT = 30
PARTICLE_WRONG_COUNT = 5
PARTICLE_LIFE_MIN = 10
PARTICLE_LIFE_MAX = 20
PARTICLE_GRAVITY = 0.05

# ── Color Constants ──────────────────────────────────────────────────────────
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

ZIP_COLORS: list[int] = [RED, GREEN, LIGHT_BLUE, YELLOW]
ZIP_COLOR_NAMES: dict[int, str] = {
    RED: "RED",
    GREEN: "GRN",
    LIGHT_BLUE: "BLU",
    YELLOW: "YEL",
}


# ── Enums ────────────────────────────────────────────────────────────────────


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class Zipline:
    x1: float
    y: float
    x2: float
    color: int
    alive: bool = True

    @property
    def length(self) -> float:
        return self.x2 - self.x1


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


# ── Game Class ───────────────────────────────────────────────────────────────


class Game:
    def __init__(self) -> None:
        pyxel.init(
            SCREEN_W, SCREEN_H, title="ZIP SURGE", display_scale=DISPLAY_SCALE, fps=FPS
        )
        pyxel.mouse(False)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── State initialization ─────────────────────────────────────────────

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.high_score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.player_x: float = float(PLAYER_SCREEN_X)
        self.player_y: float = float(SCREEN_H // 2)
        self.player_vx: float = 0.0
        self.player_vy: float = 0.0
        self.player_on_line: Zipline | None = None
        self.player_color: int = RED
        self.player_airborne: bool = True
        self.lines: list[Zipline] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.super_timer: int = 0
        self.super_mode: bool = False
        self.game_speed: float = INITIAL_GAME_SPEED
        self.frame: int = 0
        self.spawn_timer: int = 0
        self.scroll_x: float = 0.0
        self.best_path: list[tuple[float, float]] = []
        self.recording: list[tuple[float, float]] = []
        self.shake_frames: int = 0
        self.shake_intensity: int = 0

    def _start_game(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.player_x = float(PLAYER_SCREEN_X)
        self.player_y = float(SCREEN_H // 2)
        self.player_vx = 0.0
        self.player_vy = 0.0
        self.player_on_line = None
        self.player_color = RED
        self.player_airborne = True
        self.lines.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.super_timer = 0
        self.super_mode = False
        self.game_speed = INITIAL_GAME_SPEED
        self.frame = 0
        self.spawn_timer = 0
        self.scroll_x = 0.0
        self.recording.clear()
        self.shake_frames = 0
        self.shake_intensity = 0
        self._init_lines()
        self.phase = Phase.PLAYING

    def _init_lines(self) -> None:
        first_y = float(SCREEN_H // 2 - 20)
        first_line = Zipline(
            x1=0.0, y=first_y, x2=float(SCREEN_W * 2), color=self._rng.choice(ZIP_COLORS)
        )
        self.lines.append(first_line)
        self.player_on_line = first_line
        self.player_y = first_y
        self.player_airborne = False
        self.player_color = first_line.color
        self.player_x = float(PLAYER_SCREEN_X)

        last_x = first_line.x2 + 40.0
        for _ in range(5):
            color = self._rng.choice(ZIP_COLORS)
            length = self._rng.uniform(ZIpline_MIN_LENGTH, ZIpline_MAX_LENGTH)
            y = self._rng.uniform(ZIpline_Y_MIN, ZIpline_Y_MAX)
            x1 = last_x
            x2 = x1 + length
            self.lines.append(Zipline(x1=x1, y=y, x2=x2, color=color))
            last_x = x2 + self._rng.uniform(SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX)

    # ── Pure Logic (Testable) ────────────────────────────────────────────

    @staticmethod
    def _compute_land_score(combo: int, is_super: bool) -> int:
        base = BASE_SCORE_PER_LAND + combo * SAME_COLOR_SCORE
        return int(base * (SUPER_SCORE_MULT if is_super else 1))

    def _update_speed(self) -> None:
        self.game_speed = min(
            INITIAL_GAME_SPEED + self.frame * SPEED_INC_PER_FRAME, MAX_GAME_SPEED
        )

    def _scrolled_x(self, world_x: float) -> float:
        return world_x - self.scroll_x

    def _player_screen_x(self) -> float:
        return self._scrolled_x(self.player_x)

    def _player_screen_y(self) -> float:
        return self.player_y

    def _apply_gravity(self) -> None:
        self.player_vy += GRAVITY
        if self.player_vy > MAX_FALL_SPEED:
            self.player_vy = MAX_FALL_SPEED
        self.player_y += self.player_vy

    def _update_player_physics(self) -> None:
        scroll_speed = 2.0 * self.game_speed

        if self.player_on_line is not None:
            self.player_x += scroll_speed
            self.player_y = self.player_on_line.y
            self.player_vy = 0.0
            self.player_airborne = False
            if self.player_x >= self.player_on_line.x2:
                self.player_on_line = None
                self.player_airborne = True
        else:
            self.player_x += scroll_speed + self.player_vx * STEER_SPEED
            self._apply_gravity()
            self.player_airborne = True

    def _check_line_landing(self) -> bool:
        if not self.player_airborne:
            return False
        if self.player_vy < 0:
            return False

        px = self.player_x
        py = self.player_y
        best_dist = float("inf")
        best_line: Zipline | None = None

        for line in self.lines:
            if not line.alive:
                continue
            if line is self.player_on_line:
                continue
            if px < line.x1 - 10 or px > line.x2 + 10:
                continue
            dist = abs(py - line.y)
            if dist < 12 and dist < best_dist:
                best_dist = dist
                best_line = line

        if best_line is not None and best_dist <= PLAYER_RADIUS + 3:
            self.player_on_line = best_line
            self.player_airborne = False
            self.player_y = best_line.y
            self.player_vy = 0.0
            self._handle_landing(best_line)
            return True
        return False

    def _handle_landing(self, line: Zipline) -> None:
        prev_color = self.player_color
        self.player_color = line.color

        if self.super_mode:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            points = self._compute_land_score(self.combo, True) + SUPER_LAND_SCORE
            self.score += points
            self._spawn_land_particles(self.player_x, self.player_y, line.color)
            self._add_floating_text(
                self.player_x, self.player_y - 12, f"+{points}", line.color
            )
            return

        if line.color == prev_color:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            points = self._compute_land_score(self.combo, False)
            self.score += points
            self._spawn_land_particles(self.player_x, self.player_y, line.color)
            txt = f"+{points}"
            if self.combo >= 3:
                txt = f"COMBO x{self.combo} +{points}"
            self._add_floating_text(self.player_x, self.player_y - 12, txt, line.color)
            if self.combo >= COMBO_THRESHOLD and not self.super_mode:
                self._activate_super()
        else:
            self._wrong_color_land(line)

    def _wrong_color_land(self, line: Zipline) -> None:
        self.combo = 0
        self.heat += HEAT_PER_WRONG
        self.score += BASE_SCORE_PER_LAND
        self._spawn_wrong_particles(self.player_x, self.player_y)
        self._add_floating_text(
            self.player_x, self.player_y - 12, f"+{BASE_SCORE_PER_LAND} WRONG", GRAY
        )
        self.shake_frames = 10
        self.shake_intensity = 3

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self._spawn_super_particles(self.player_x, self.player_y)
        self._add_floating_text(
            self.player_x, self.player_y - 24, "SUPER ZIP!", YELLOW
        )
        self.shake_frames = 15
        self.shake_intensity = 5

    def _update_super_timer(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer == 0:
                self.super_mode = False
                self.combo = 0
                self.player_color = RED
                self._add_floating_text(
                    self.player_x, self.player_y - 18, "END", GRAY
                )

    def _auto_jump_to_nearest(self) -> None:
        if not self.super_mode:
            return
        if self.player_on_line is None:
            return
        if self.player_x < self.player_on_line.x2 - 20:
            return

        best_line: Zipline | None = None
        best_dist = float("inf")
        for line in self.lines:
            if line is self.player_on_line:
                continue
            if not line.alive:
                continue
            dist = abs(self.player_y - line.y)
            if dist < 60 and line.x1 - 10 < self.player_x < line.x2 + 10:
                if dist < best_dist:
                    best_dist = dist
                    best_line = line

        if best_line is not None:
            self.player_on_line = best_line
            self.player_airborne = False
            self.player_y = best_line.y
            self.player_vy = 0.0
            self.player_color = best_line.color
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            points = self._compute_land_score(self.combo, True) + SUPER_LAND_SCORE
            self.score += points
            self._spawn_land_particles(self.player_x, self.player_y, best_line.color)

    def _update_game_over_check(self) -> bool:
        if self.heat >= HEAT_MAX:
            self._on_game_over()
            return True
        if self.player_y > SCREEN_H + 30:
            self._on_game_over()
            return True
        return False

    def _on_game_over(self) -> None:
        if self.score > self.high_score:
            self.high_score = self.score
            self.best_path = list(self.recording)
        self.phase = Phase.GAME_OVER
        for _ in range(20):
            self.particles.append(
                Particle(
                    x=self.player_x,
                    y=min(self.player_y, float(SCREEN_H)),
                    vx=self._rng.uniform(-3.0, 3.0),
                    vy=self._rng.uniform(-4.0, -1.0),
                    life=self._rng.randint(15, 30),
                    color=RED,
                )
            )

    def _update_lines(self) -> None:
        scroll_speed = 2.0 * self.game_speed
        self.scroll_x += scroll_speed

        right_edge = self.scroll_x + SCREEN_W + 100
        self.lines = [ln for ln in self.lines if ln.alive and ln.x2 > self.scroll_x - 50]

        if not self.lines:
            return

        last_x = max(ln.x2 for ln in self.lines)
        while last_x < right_edge:
            color = self._rng.choice(ZIP_COLORS)
            length = self._rng.uniform(ZIpline_MIN_LENGTH, ZIpline_MAX_LENGTH)
            y = self._rng.uniform(ZIpline_Y_MIN, ZIpline_Y_MAX)
            gap = self._rng.uniform(SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX)
            x1 = last_x + gap
            x2 = x1 + length
            self.lines.append(Zipline(x1=x1, y=y, x2=x2, color=color))
            last_x = x2

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += PARTICLE_GRAVITY
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y -= 0.8
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    def _spawn_land_particles(self, x: float, y: float, color: int) -> None:
        count = PARTICLE_SUPER_COUNT if self.super_mode else PARTICLE_LAND_COUNT
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-1.5, 1.5),
                    vy=self._rng.uniform(-2.0, 0),
                    life=self._rng.randint(PARTICLE_LIFE_MIN, PARTICLE_LIFE_MAX),
                    color=color,
                )
            )

    def _spawn_super_particles(self, x: float, y: float) -> None:
        for _ in range(PARTICLE_SUPER_COUNT):
            color = self._rng.choice(ZIP_COLORS)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-4.0, 4.0),
                    vy=self._rng.uniform(-4.0, 0),
                    life=self._rng.randint(15, 25),
                    color=color,
                )
            )

    def _spawn_wrong_particles(self, x: float, y: float) -> None:
        for _ in range(PARTICLE_WRONG_COUNT):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-0.5, 0.5),
                    vy=self._rng.uniform(-1.0, 0),
                    life=self._rng.randint(10, 15),
                    color=GRAY,
                )
            )

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(
            FloatingText(x=self._scrolled_x(x), y=y, text=text, life=25, color=color)
        )

    def _decay_heat(self) -> None:
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    # ── Update ───────────────────────────────────────────────────────────

    def update(self) -> None:
        self.frame += 1

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self._start_game()
            return

        if self.phase == Phase.GAME_OVER:
            self._update_particles()
            self._update_floating_texts()
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.phase = Phase.TITLE
                self.reset()
            return

        # PLAYING ──────────────────────────────────────────────────────────
        self._update_speed()
        self._update_lines()

        # Input
        if self.player_on_line is not None:
            if (
                pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.KEY_UP)
                or pyxel.btnp(pyxel.KEY_Z)
            ):
                self.player_vy = JUMP_VELOCITY
                self.player_on_line = None
                self.player_airborne = True
                self.player_vx = 0.0
        else:
            steer = 0.0
            if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
                steer = -1.0
            if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
                steer = 1.0
            self.player_vx = steer

        self._update_player_physics()
        self._check_line_landing()
        self._auto_jump_to_nearest()
        self._update_super_timer()

        # Check game over BEFORE heat decay (spec: heat >= 100 check before decay)
        if self._update_game_over_check():
            return

        self._decay_heat()
        self._update_particles()
        self._update_floating_texts()

        if self.shake_frames > 0:
            self.shake_frames -= 1

        self.recording.append((self.player_x, self.player_y))
        if len(self.recording) > 600:
            self.recording.pop(0)

    # ── Draw ─────────────────────────────────────────────────────────────

    def draw(self) -> None:
        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0:
            shake_x = self._rng.randint(-self.shake_intensity, self.shake_intensity)
            shake_y = self._rng.randint(-self.shake_intensity, self.shake_intensity)

        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
            return
        if self.phase == Phase.GAME_OVER:
            self._draw_playing(shake_x, shake_y)
            self._draw_game_over_overlay()
            return

        self._draw_playing(shake_x, shake_y)

    def _draw_playing(self, shake_x: int, shake_y: int) -> None:
        # Background: sky, mountains, ground
        self._draw_background(shake_x, shake_y)

        # Ghost trail
        self._draw_ghost_trail(shake_x, shake_y)

        # Trees at zipline endpoints
        self._draw_trees(shake_x, shake_y)

        # Ziplines
        self._draw_ziplines(shake_x, shake_y)

        # Player
        self._draw_player(shake_x, shake_y)

        # Particles
        for p in self.particles:
            sx = int(self._scrolled_x(p.x) + shake_x)
            sy = int(p.y + shake_y)
            if 0 <= sx < SCREEN_W and 0 <= sy < SCREEN_H:
                pyxel.pset(sx, sy, p.color)

        # Floating texts
        for ft in self.floating_texts:
            alpha = ft.life / 25
            col = ft.color if alpha > 0.3 else GRAY
            tx = int(ft.x + shake_x)
            ty = int(ft.y + shake_y)
            if 0 <= tx < SCREEN_W and 0 <= ty < SCREEN_H:
                pyxel.text(tx, ty, ft.text, col)

        # HUD
        self._draw_hud()

    def _draw_background(self, shake_x: int, shake_y: int) -> None:
        # Sky gradient (navy/dark blue)
        for i in range(SCREEN_H):
            col = NAVY if i < SCREEN_H // 2 else DARK_BLUE
            pyxel.line(0, i + shake_y, SCREEN_W, i + shake_y, col)

        # Mountains
        mountain_color = DARK_BLUE
        for i in range(5):
            mx = (i * 80 + 20 + int(self.scroll_x * 0.1) % 80) % (SCREEN_W + 100) - 50
            my = 120 + i * 15
            mw = 60 + i * 20
            mh = 40 + i * 15
            sx = mx + shake_x
            sy = my + shake_y
            if -80 < sx < SCREEN_W + 80:
                pyxel.tri(
                    int(sx),
                    int(sy + mh),
                    int(sx + mw // 2),
                    int(sy),
                    int(sx + mw),
                    int(sy + mh),
                    mountain_color,
                )

        # Ground
        pyxel.rect(
            0, int(SCREEN_H - 8 + shake_y), SCREEN_W, 16, BROWN
        )

    def _draw_trees(self, shake_x: int, shake_y: int) -> None:
        drawn: set[tuple[float, float]] = set()
        for line in self.lines:
            if not line.alive:
                continue
            for endpoint_x in (line.x1, line.x2):
                key = (round(endpoint_x, 1), round(line.y, 1))
                if key in drawn:
                    continue
                drawn.add(key)
                sx = int(self._scrolled_x(endpoint_x)) + shake_x
                sy = int(line.y) + shake_y
                if sx < -10 or sx > SCREEN_W + 10:
                    continue
                # Trunk
                pyxel.rect(sx - 3, sy - 20, 6, 20, BROWN)
                # Canopy (triangle top)
                pyxel.tri(sx - 8, sy - 20, sx, sy - 35, sx + 8, sy - 20, GREEN)

    def _draw_ziplines(self, shake_x: int, shake_y: int) -> None:
        for line in self.lines:
            if not line.alive:
                continue
            x1 = int(self._scrolled_x(line.x1)) + shake_x
            x2 = int(self._scrolled_x(line.x2)) + shake_x
            yy = int(line.y) + shake_y
            if x2 < -10 or x1 > SCREEN_W + 10:
                continue

            color = line.color
            if self.super_mode:
                color = self._rainbow_color()
            pyxel.line(x1, yy, x2, yy, color)
            pyxel.line(x1, yy + 1, x2, yy + 1, color)

    def _rainbow_color(self) -> int:
        cycle = (self.frame // 6) % 4
        return ZIP_COLORS[cycle]

    def _draw_player(self, shake_x: int, shake_y: int) -> None:
        sx = int(self._scrolled_x(self.player_x)) + shake_x
        sy = int(self.player_y) + shake_y

        if sx < -10 or sx > SCREEN_W + 10:
            return

        if self.player_airborne:
            pyxel.circb(sx, sy, PLAYER_RADIUS, WHITE)
            inner_color = self._rainbow_color() if self.super_mode else self.player_color
            pyxel.circ(sx, sy, PLAYER_RADIUS - 1, inner_color)
        else:
            color = self._rainbow_color() if self.super_mode else self.player_color
            pyxel.circ(sx, sy, PLAYER_RADIUS, color)
            pyxel.circb(sx, sy, PLAYER_RADIUS, WHITE)

        # Super mode glow
        if self.super_mode and self.frame % 4 < 2:
            pyxel.circb(sx, sy, PLAYER_RADIUS + 4, YELLOW)

    def _draw_ghost_trail(self, shake_x: int, shake_y: int) -> None:
        if not self.best_path:
            return
        for i, (wx, wy) in enumerate(self.best_path):
            if i % 3 != 0:
                continue
            sx = int(self._scrolled_x(wx))
            sy = int(wy)
            alpha_col = WHITE if i % 6 == 0 else DARK_BLUE
            screen_sx = sx + shake_x
            screen_sy = sy + shake_y
            if 0 <= screen_sx < SCREEN_W and 0 <= screen_sy < SCREEN_H:
                pyxel.pset(screen_sx, screen_sy, alpha_col)

    def _draw_hud(self) -> None:
        # Background strip
        pyxel.rect(0, 0, SCREEN_W, 16, BLACK)

        # Score
        pyxel.text(4, 2, f"SCORE: {self.score}", WHITE)
        pyxel.text(4, 9, f"BEST: {self.high_score}", GRAY)

        # Combo
        if self.combo > 0:
            combo_text = f"COMBO x{self.combo}"
            combo_color = WHITE
            if self.combo >= COMBO_THRESHOLD:
                combo_color = ORANGE
            if self.super_mode:
                combo_color = YELLOW
            pyxel.text(130, 2, combo_text, combo_color)

        # Heat bar
        heat_bar_w = 60
        heat_bar_x = SCREEN_W - heat_bar_w - 40
        heat_fill = int(heat_bar_w * self.heat / HEAT_MAX)
        pyxel.text(heat_bar_x - 30, 2, "HEAT", GRAY)
        pyxel.rect(heat_bar_x, 2, heat_bar_w, 6, DARK_BLUE)
        pyxel.rect(heat_bar_x, 2, heat_fill, 6, RED)
        pyxel.rectb(heat_bar_x, 2, heat_bar_w, 6, WHITE)

        # Super timer bar
        if self.super_mode:
            bar_w = 80
            bar_x = SCREEN_W - bar_w - 4
            fill = int(bar_w * self.super_timer / SUPER_DURATION)
            pyxel.text(bar_x - 40, 9, "SUPER", YELLOW)
            pyxel.rect(bar_x, 9, bar_w, 4, DARK_BLUE)
            pyxel.rect(bar_x, 9, fill, 4, YELLOW)

        # Color indicator
        if not self.super_mode:
            color = self.player_color
        else:
            color = self._rainbow_color()
        pyxel.rect(SCREEN_W - 16, 2, 10, 10, color)
        pyxel.rectb(SCREEN_W - 16, 2, 10, 10, WHITE)

        # Speed
        pyxel.text(240, 2, f"SPD: {self.game_speed:.1f}x", GRAY)

    # ── Title Screen ─────────────────────────────────────────────────────

    def _draw_title(self) -> None:
        # Background
        self._draw_background(0, 0)

        # Ghost trail in background if available
        if self.best_path:
            self._draw_ghost_trail(0, 0)

        title = "ZIP SURGE"
        tw = len(title) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 40, title, WHITE)

        instructions = [
            "SPACE / UP / Z :  Jump to next zipline",
            "LEFT / RIGHT / A / D :  Steer while airborne",
            "",
            "Ride SAME color = COMBO UP!",
            "COMBO x4 = SUPER ZIP!",
            "  (Rainbow lines, 3x score, 5 sec)",
            "Wrong color = COMBO RESET + HEAT!",
            "HEAT >= 100 = GAME OVER",
            "Fall off screen = GAME OVER",
            "",
            "SPACE or ENTER to Start",
        ]
        y_off = 65
        for line in instructions:
            lw = len(line) * 4
            pyxel.text(SCREEN_W // 2 - lw // 2, y_off, line, GRAY)
            y_off += 10

        # Color legend
        color_labels = ["RED", "GRN", "BLU", "YEL"]
        for i in range(4):
            bx = SCREEN_W // 2 - 50 + i * 26
            by = y_off + 4
            pyxel.rect(bx, by, 18, 8, ZIP_COLORS[i])
            pyxel.rectb(bx, by, 18, 8, WHITE)
            lw = len(color_labels[i]) * 4
            pyxel.text(bx + 9 - lw // 2, by + 10, color_labels[i], WHITE)

    # ── Game Over Screen ─────────────────────────────────────────────────

    def _draw_game_over_overlay(self) -> None:
        # Semi-transparent overlay
        for y in range(0, SCREEN_H, 4):
            for x in range((y // 4) % 2, SCREEN_W, 4):
                pyxel.pset(x, y, BLACK)

        go_text = "GAME OVER"
        tw = len(go_text) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 50, go_text, RED)

        lines = [
            f"SCORE: {self.score}",
            f"HIGH SCORE: {self.high_score}",
            f"MAX COMBO: {self.max_combo}",
            "",
            "SPACE or ENTER to Retry",
        ]
        y_off = 80
        for line in lines:
            lw = len(line) * 4
            col = YELLOW if "HIGH" in line else ORANGE if "COMBO" in line else WHITE
            pyxel.text(SCREEN_W // 2 - lw // 2, y_off, line, col)
            y_off += 14

        # New best
        if self.score >= self.high_score and self.score > 0:
            nb_text = "NEW BEST!"
            nw = len(nb_text) * 4
            pyxel.text(SCREEN_W // 2 - nw // 2, y_off + 4, nb_text, ORANGE)

        # Blinking restart
        if self.frame % 60 < 40:
            rt_text = "PRESS SPACE TO RETRY"
            rw = len(rt_text) * 4
            pyxel.text(SCREEN_W // 2 - rw // 2, SCREEN_H - 30, rt_text, WHITE)


# ── Entry Point ───────────────────────────────────────────────────────────────


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
