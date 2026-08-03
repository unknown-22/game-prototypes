"""CHRONO CHAIN — Time-Loop Crystal Collection Puzzle.

Your time echo replays your past movements, collecting crystals independently.
Same-color consecutive collections build COMBO chains. Reach COMBO 4 for
SUPER CHRONO: rainbow burst auto-collects everything at 3x score.

Core fun moment: your echo sweeps through a crystal cluster you lured it
toward, triggering SUPER CHRONO — the echo worked FOR you.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WIDTH = 320
HEIGHT = 240
FPS = 30
GAME_TIME = 1800  # 60s * 30fps

COLS = 10
ROWS = 8
CELL = 24
PLAYFIELD_X = (WIDTH - COLS * CELL) // 2  # 40
PLAYFIELD_Y = (HEIGHT - ROWS * CELL) // 2  # 24

PLAYER_SPEED = 2.0
PLAYER_R = 10
ECHO_SPEED = 1.2
CRYSTAL_R = 8

MAX_HEAT = 100.0
HEAT_MISMATCH = 15.0
HEAT_DECAY = 0.02
HEAT_PER_FRAME = 0.03
SUPER_DURATION = 300
COMBO_FOR_SUPER = 4
RECORD_INTERVAL = 120
MAX_CRYSTALS = 12

COLOR_RED = 8
COLOR_ORANGE = 9
COLOR_YELLOW = 10
COLOR_LIME = 11
COLOR_CYAN = 12
COLOR_DARK_BLUE = 5
COLOR_WHITE = 7
COLOR_GRAY = 13
COLOR_PINK = 14
COLOR_BLACK = 0
COLOR_NAVY = 1

CRYSTAL_COLORS = (COLOR_RED, COLOR_LIME, COLOR_DARK_BLUE, COLOR_YELLOW)
NUM_CRYSTAL_COLORS = len(CRYSTAL_COLORS)
RAINBOW = (COLOR_RED, COLOR_ORANGE, COLOR_YELLOW, COLOR_LIME, COLOR_CYAN, COLOR_PINK)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Crystal:
    x: float
    y: float
    color: int
    alive: bool = True
    spawn_frame: int = 0


@dataclass
class PathPoint:
    x: float
    y: float
    frame: int


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
    phase: Phase
    score: int
    best_score: int
    combo: int
    max_combo: int
    heat: float
    timer: int
    super_timer: int
    frame: int
    player_x: float
    player_y: float
    last_color: int | None
    crystals: list[Crystal]
    path: list[PathPoint]
    echo_path: list[PathPoint]
    echo_idx: int
    echo_active: bool
    echo_x: float
    echo_y: float
    record_timer: int
    shake_frames: int
    particles: list[Particle]
    floating_texts: list[FloatingText]
    spawn_timer: int
    spawn_interval: int
    crystal_lifetime: int
    _rng: random.Random

    def __new__(cls) -> Game:  # type: ignore[misc]
        obj = object.__new__(cls)
        obj.phase = Phase.TITLE
        obj.score = 0
        obj.best_score = 0
        obj.combo = 0
        obj.max_combo = 0
        obj.heat = 0.0
        obj.timer = GAME_TIME
        obj.super_timer = 0
        obj.frame = 0
        obj.player_x = PLAYFIELD_X + COLS * CELL / 2.0
        obj.player_y = PLAYFIELD_Y + ROWS * CELL / 2.0
        obj.last_color = None
        obj.crystals = []
        obj.path = []
        obj.echo_path = []
        obj.echo_idx = 0
        obj.echo_active = False
        obj.echo_x = 0.0
        obj.echo_y = 0.0
        obj.record_timer = RECORD_INTERVAL
        obj.shake_frames = 0
        obj.particles = []
        obj.floating_texts = []
        obj.spawn_timer = 0
        obj.spawn_interval = 60
        obj.crystal_lifetime = 240
        obj._rng = random.Random()
        return obj

    def __init__(self) -> None:
        pyxel.init(WIDTH, HEIGHT, title="CHRONO CHAIN", fps=FPS, display_scale=2)
        pyxel.mouse(False)
        self.reset()
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = GAME_TIME
        self.super_timer = 0
        self.frame = 0
        self.player_x = PLAYFIELD_X + COLS * CELL / 2.0
        self.player_y = PLAYFIELD_Y + ROWS * CELL / 2.0
        self.last_color = None
        self.crystals.clear()
        self.path.clear()
        self.echo_path.clear()
        self.echo_idx = 0
        self.echo_active = False
        self.echo_x = 0.0
        self.echo_y = 0.0
        self.record_timer = RECORD_INTERVAL
        self.shake_frames = 0
        self.particles.clear()
        self.floating_texts.clear()
        self.spawn_timer = 0
        self.spawn_interval = 60
        self.crystal_lifetime = 240

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self) -> None:
        if self.phase is Phase.TITLE:
            self._update_title()
        elif self.phase is Phase.PLAYING:
            self._update_playing()
        elif self.phase is Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.phase = Phase.PLAYING
            self.timer = GAME_TIME
            self.frame = 0

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()
            self.phase = Phase.TITLE

    def _update_playing(self) -> None:
        self.frame += 1

        if self.shake_frames > 0:
            self.shake_frames -= 1

        # Timer
        self._update_timer()
        if self.timer <= 0:
            self._end_game()
            return

        # Input — movement
        dx = 0
        dy = 0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx = -1
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx = 1
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy = -1
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy = 1

        if dx != 0 or dy != 0:
            self._move_player(float(dx), float(dy))

        # Record path
        self._record_path()

        # Update echo
        self._update_echo()

        # Heat decay + passive heat
        self._update_heat()

        # SUPER timer
        if self.super_timer > 0:
            self.super_timer -= 1

        # Spawn crystals
        self._spawn_crystals()

        # Escalation
        self._update_escalation()

        # Crystal lifetime decay
        elapsed = GAME_TIME - self.timer
        t = min(1.0, elapsed / (45.0 * FPS))
        self.crystal_lifetime = int(240 - t * 120)  # 8s → 4s

        # Remove expired crystals
        for c in self.crystals:
            if c.alive and self.frame - c.spawn_frame > self.crystal_lifetime:
                c.alive = False

        # Player collects crystals
        for c in self.crystals:
            if not c.alive:
                continue
            dx_p = self.player_x - c.x
            dy_p = self.player_y - c.y
            if math.sqrt(dx_p * dx_p + dy_p * dy_p) < CRYSTAL_R + PLAYER_R:
                self._collect_crystal(c, is_echo=False)

        # Update particles
        self._update_particles()

        # Update floating texts
        self._update_floating_texts()

        # Heat game over
        if self.heat >= MAX_HEAT:
            self._end_game()

    def _end_game(self) -> None:
        self.phase = Phase.GAME_OVER
        self.shake_frames = 16
        if self.score > self.best_score:
            self.best_score = self.score

    # ------------------------------------------------------------------
    # Testable logic methods
    # ------------------------------------------------------------------

    def _move_player(self, dx: float, dy: float) -> None:
        if dx != 0 and dy != 0:
            dx *= 0.707
            dy *= 0.707
        nx = self.player_x + dx * PLAYER_SPEED
        ny = self.player_y + dy * PLAYER_SPEED
        margin = PLAYER_R
        self.player_x = max(
            PLAYFIELD_X + margin, min(PLAYFIELD_X + COLS * CELL - margin, nx)
        )
        self.player_y = max(
            PLAYFIELD_Y + margin, min(PLAYFIELD_Y + ROWS * CELL - margin, ny)
        )

    def _record_path(self) -> None:
        self.record_timer -= 1
        self.path.append(PathPoint(x=self.player_x, y=self.player_y, frame=self.frame))
        if self.record_timer <= 0:
            self.record_timer = RECORD_INTERVAL
            if len(self.path) > 10:
                self.echo_path = list(self.path)
                self.echo_idx = 0
                if self.echo_path:
                    self.echo_x = self.echo_path[0].x
                    self.echo_y = self.echo_path[0].y
                    self.echo_active = True
            self.path.clear()

        elapsed = GAME_TIME - self.timer
        t = min(1.0, elapsed / (45.0 * FPS))
        interval = int(120 - t * 60)  # 120f → 60f
        if self.record_timer <= 0:
            self.record_timer = max(30, interval)

    def _update_echo(self) -> None:
        if not self.echo_active:
            return

        if not self.echo_path or self.echo_idx >= len(self.echo_path):
            self.echo_active = False
            return

        target = self.echo_path[self.echo_idx]
        dx = target.x - self.echo_x
        dy = target.y - self.echo_y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < ECHO_SPEED * 0.5:
            self.echo_idx += 1
        elif dist > 0:
            self.echo_x += (dx / dist) * ECHO_SPEED
            self.echo_y += (dy / dist) * ECHO_SPEED

        if self.echo_idx >= len(self.echo_path):
            self.echo_active = False

        # Echo collects crystals (check even when reaching end of path)
        for c in self.crystals:
            if not c.alive:
                continue
            dx_e = self.echo_x - c.x
            dy_e = self.echo_y - c.y
            if math.sqrt(dx_e * dx_e + dy_e * dy_e) < CRYSTAL_R + PLAYER_R:
                self._collect_crystal(c, is_echo=True)

    def _spawn_crystals(self) -> None:
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            elapsed = GAME_TIME - self.timer
            t = min(1.0, elapsed / (45.0 * FPS))
            interval = int(60 - t * 24)  # 2s → 0.8s (~0.5/s → ~1.25/s)
            self.spawn_timer = max(20, interval)

            alive = sum(1 for c in self.crystals if c.alive)
            to_spawn = min(2, MAX_CRYSTALS - alive)
            for _ in range(to_spawn):
                if alive + len([c for c in self.crystals if c.alive]) >= MAX_CRYSTALS:
                    break
                cx = self._rng.uniform(
                    PLAYFIELD_X + CRYSTAL_R + 2,
                    PLAYFIELD_X + COLS * CELL - CRYSTAL_R - 2,
                )
                cy = self._rng.uniform(
                    PLAYFIELD_Y + CRYSTAL_R + 2,
                    PLAYFIELD_Y + ROWS * CELL - CRYSTAL_R - 2,
                )
                color = self._rng.choice(CRYSTAL_COLORS)
                self.crystals.append(
                    Crystal(x=cx, y=cy, color=color, spawn_frame=self.frame)
                )
                alive += 1

        # Clean up dead crystals
        self.crystals = [c for c in self.crystals if c.alive]

    def _collect_crystal(self, crystal: Crystal, *, is_echo: bool = False) -> None:
        if not crystal.alive:
            return
        crystal.alive = False

        is_super = self.super_timer > 0
        color = crystal.color

        if is_super:
            # SUPER mode: any color matches
            self.combo += 1
            points = int(10 * self.combo * 3)
            self.score += max(points, 10)
            self.max_combo = max(self.max_combo, self.combo)
            self._spawn_float(crystal.x, crystal.y, f"+{points}", RAINBOW[self.frame % len(RAINBOW)])
            self._spawn_collect_particles(crystal.x, crystal.y, color, big=True)
            if self.combo >= 2 and self.combo % 2 == 0:
                self._spawn_float(crystal.x, crystal.y - 12, f"COMBO x{self.combo}", COLOR_YELLOW)
        elif self.last_color is None or crystal.color == self.last_color:
            # Combo
            self.combo += 1
            points = max(int(10 * self.combo), 10)
            self.score += points
            self.last_color = crystal.color
            self.max_combo = max(self.max_combo, self.combo)
            self._spawn_float(crystal.x, crystal.y, f"+{points}", color)
            self._spawn_collect_particles(crystal.x, crystal.y, color, big=False)
            if self.combo >= 2:
                self._spawn_float(crystal.x, crystal.y - 12, f"COMBO x{self.combo}", COLOR_YELLOW)
            # SUPER trigger
            if self.combo >= COMBO_FOR_SUPER and self.super_timer == 0:
                self._activate_super()
        else:
            # Mismatch
            self.combo = 0
            self.last_color = crystal.color
            self.heat += HEAT_MISMATCH
            self.shake_frames = 8
            self._spawn_float(crystal.x, crystal.y, "WRONG!", COLOR_RED)
            self._spawn_collect_particles(crystal.x, crystal.y, COLOR_RED, big=False)

    def _update_heat(self) -> None:
        self.heat = max(0.0, self.heat - HEAT_DECAY)
        self.heat = min(MAX_HEAT, self.heat + HEAT_PER_FRAME)

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self.shake_frames = 6
        self._spawn_float(
            self.player_x, self.player_y - 20,
            "SUPER CHRONO!", RAINBOW[0],
        )
        for _ in range(20):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.5, 4.0)
            self.particles.append(
                Particle(
                    x=self.player_x, y=self.player_y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    color=COLOR_YELLOW,
                    life=25,
                )
            )

    def _update_timer(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0

    def _update_escalation(self) -> None:
        pass  # Escalation handled inline in spawn/record/heat

    # ------------------------------------------------------------------
    # Particles
    # ------------------------------------------------------------------

    def _spawn_collect_particles(
        self, x: float, y: float, color: int, *, big: bool = False
    ) -> None:
        count = 16 if big else 8
        life_min = 25 if big else 15
        life_max = 40 if big else 25
        spd_min = 1.0 if big else 0.5
        spd_max = 3.0 if big else 2.0
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(spd_min, spd_max)
            self.particles.append(
                Particle(
                    x=x, y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    color=color,
                    life=self._rng.randint(life_min, life_max),
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ------------------------------------------------------------------
    # Floating texts
    # ------------------------------------------------------------------

    def _spawn_float(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, color=color, life=30)
        )

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self) -> None:
        pyxel.cls(COLOR_BLACK)

        sx = 0
        sy = 0
        if self.shake_frames > 0:
            intensity = max(1, self.shake_frames // 3)
            sx = self._rng.randint(-intensity, intensity)
            sy = self._rng.randint(-intensity, intensity)

        if self.phase is Phase.TITLE:
            self._draw_title(sx, sy)
        elif self.phase is Phase.PLAYING:
            self._draw_playfield(sx, sy)
            self._draw_crystals(sx, sy)
            self._draw_echo(sx, sy)
            self._draw_player(sx, sy)
            self._draw_particles(sx, sy)
            self._draw_floating_texts(sx, sy)
            self._draw_ui()
            self._draw_super_border(sx, sy)
        elif self.phase is Phase.GAME_OVER:
            self._draw_playfield(sx, sy)
            self._draw_crystals(sx, sy)
            self._draw_echo(sx, sy)
            self._draw_player(sx, sy)
            self._draw_particles(sx, sy)
            self._draw_floating_texts(sx, sy)
            self._draw_game_over(sx, sy)
            self._draw_ui()

    # ------------------------------------------------------------------
    # Playfield
    # ------------------------------------------------------------------

    def _draw_playfield(self, sx: int, sy: int) -> None:
        # Border
        pyxel.rectb(
            PLAYFIELD_X - 2 + sx, PLAYFIELD_Y - 2 + sy,
            COLS * CELL + 4, ROWS * CELL + 4,
            COLOR_DARK_BLUE,
        )
        # Grid
        for col in range(COLS + 1):
            x = PLAYFIELD_X + col * CELL + sx
            pyxel.line(
                x, PLAYFIELD_Y + sy,
                x, PLAYFIELD_Y + ROWS * CELL + sy,
                COLOR_NAVY,
            )
        for row in range(ROWS + 1):
            y = PLAYFIELD_Y + row * CELL + sy
            pyxel.line(
                PLAYFIELD_X + sx, y,
                PLAYFIELD_X + COLS * CELL + sx, y,
                COLOR_NAVY,
            )
        # Fill inside
        pyxel.rect(
            PLAYFIELD_X + sx, PLAYFIELD_Y + sy,
            COLS * CELL, ROWS * CELL,
            COLOR_BLACK,
        )

    # ------------------------------------------------------------------
    # Crystals
    # ------------------------------------------------------------------

    def _draw_crystals(self, sx: int, sy: int) -> None:
        for c in self.crystals:
            if not c.alive:
                continue
            cx = int(c.x) + sx
            cy = int(c.y) + sy
            # Glow
            pyxel.circb(cx, cy, CRYSTAL_R, c.color)
            pyxel.circb(cx, cy, CRYSTAL_R - 1, c.color)
            # Fill
            pyxel.circ(cx, cy, CRYSTAL_R - 2, c.color)
            # Highlight
            hl_color = COLOR_WHITE if c.color != COLOR_WHITE else COLOR_GRAY
            pyxel.circ(cx - 2, cy - 2, 2, hl_color)

    # ------------------------------------------------------------------
    # Player
    # ------------------------------------------------------------------

    def _draw_player(self, sx: int, sy: int) -> None:
        px = int(self.player_x) + sx
        py = int(self.player_y) + sy

        is_super = self.super_timer > 0

        # Glow ring (last_color indicator)
        if self.last_color is not None:
            ring_color = self.last_color
        else:
            ring_color = COLOR_WHITE

        if is_super:
            rc = RAINBOW[self.frame // 4 % len(RAINBOW)]
            pyxel.circb(px, py, PLAYER_R + 2, rc)
            pyxel.circb(px, py, PLAYER_R + 1, rc)
            # SUPER glow
            glow_r = PLAYER_R + 4 if self.frame % 12 < 6 else PLAYER_R + 2
            pyxel.circb(px, py, glow_r, COLOR_YELLOW)
        else:
            pyxel.circb(px, py, PLAYER_R + 2, ring_color)

        # Body
        body_color = COLOR_WHITE
        pyxel.circ(px, py, PLAYER_R, body_color)
        pyxel.circb(px, py, PLAYER_R, COLOR_GRAY)

        # Eyes / direction indicator (small dots based on position)
        ex1 = px - 3
        ex2 = px + 3
        ey = py - 2
        pyxel.pset(ex1, ey, COLOR_BLACK)
        pyxel.pset(ex2, ey, COLOR_BLACK)

    # ------------------------------------------------------------------
    # Echo
    # ------------------------------------------------------------------

    def _draw_echo(self, sx: int, sy: int) -> None:
        if not self.echo_active:
            return

        ex = int(self.echo_x) + sx
        ey = int(self.echo_y) + sy

        is_super = self.super_timer > 0
        color = (
            RAINBOW[self.frame // 4 % len(RAINBOW)]
            if is_super
            else COLOR_CYAN
        )

        # Dotted outline ghost
        for angle_deg in range(0, 360, 30):
            rad = math.radians(angle_deg)
            dx = math.cos(rad) * PLAYER_R
            dy = math.sin(rad) * PLAYER_R
            px_val = int(ex + dx)
            py_val = int(ey + dy)
            pyxel.pset(px_val, py_val, color)

        # Comet trail (echo direction indicator)
        trail_color = COLOR_CYAN if not is_super else RAINBOW[(self.frame // 4 + 1) % len(RAINBOW)]
        for i in range(3):
            bx = int(ex - (i + 1) * 4)
            by = int(ey)
            pyxel.pset(bx, by, trail_color)

    # ------------------------------------------------------------------
    # Particles / texts
    # ------------------------------------------------------------------

    def _draw_particles(self, sx: int, sy: int) -> None:
        for p in self.particles:
            alpha = p.life / 40.0
            if alpha > 0.3 or self.frame % 2 == 0:
                pyxel.pset(int(p.x) + sx, int(p.y) + sy, p.color)

    def _draw_floating_texts(self, sx: int, sy: int) -> None:
        for ft in self.floating_texts:
            tw = len(ft.text) * 4
            alpha = ft.life / 30.0
            if alpha > 0.2:
                pyxel.text(
                    int(ft.x - tw // 2) + sx,
                    int(ft.y) + sy,
                    ft.text,
                    ft.color,
                )

    # ------------------------------------------------------------------
    # SUPER border
    # ------------------------------------------------------------------

    def _draw_super_border(self, sx: int, sy: int) -> None:
        if self.super_timer > 0:
            rc = RAINBOW[self.frame // 4 % len(RAINBOW)]
            pyxel.rectb(sx, sy, WIDTH, HEIGHT, rc)
            pyxel.rectb(sx + 1, sy + 1, WIDTH - 2, HEIGHT - 2, rc)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _draw_ui(self) -> None:
        # HUD background
        pyxel.rect(0, 0, WIDTH, 12, COLOR_BLACK)

        secs = max(0, self.timer // FPS)
        tc = COLOR_RED if secs <= 10 else COLOR_WHITE
        pyxel.text(4, 2, f"TIME:{secs}", tc)

        pyxel.text(72, 2, f"SCORE:{self.score}", COLOR_WHITE)

        combo_color = (
            COLOR_PINK if self.combo >= COMBO_FOR_SUPER
            else COLOR_YELLOW if self.combo >= 2
            else COLOR_GRAY
        )
        pyxel.text(170, 2, f"CMB:x{self.combo}", combo_color)

        if self.super_timer > 0:
            ss = self.super_timer // FPS
            pyxel.text(240, 2, f"SUPER:{ss}", COLOR_PINK)

        # Heat bar (bottom)
        bar_y = HEIGHT - 10
        hw = WIDTH - 60
        hx = 55
        pyxel.rectb(hx - 1, bar_y - 1, hw + 2, 8, COLOR_WHITE)
        pyxel.rect(hx, bar_y, hw, 6, COLOR_NAVY)
        heat_fill = int(hw * self.heat / MAX_HEAT)
        if heat_fill > 0:
            heat_color = (
                COLOR_RED if self.heat > 60
                else COLOR_ORANGE if self.heat > 30
                else COLOR_YELLOW
            )
            pyxel.rect(hx, bar_y, heat_fill, 6, heat_color)
        pyxel.text(4, bar_y - 1, f"H:{int(self.heat)}", COLOR_WHITE)

    # ------------------------------------------------------------------
    # Title screen
    # ------------------------------------------------------------------

    def _draw_title(self, sx: int, sy: int) -> None:
        cx = WIDTH // 2

        pyxel.text(cx - 38 + sx, 30 + sy, "CHRONO CHAIN", COLOR_YELLOW)
        pyxel.text(cx - 52 + sx, 42 + sy, "TIME-LOOP CRYSTAL PUZZLE", COLOR_CYAN)

        # Decorative clock-like visualization
        cex = cx + sx
        cey = 80 + sy
        clock_r = 20
        pyxel.circb(cex, cey, clock_r, COLOR_WHITE)
        pyxel.circb(cex, cey, clock_r + 1, COLOR_GRAY)
        # Clock hands
        angle = self.frame * 0.05
        nx = cex + math.cos(angle) * (clock_r - 4)
        ny = cey + math.sin(angle) * (clock_r - 4)
        pyxel.line(cex, cey, int(nx), int(ny), COLOR_RED)
        # Second hand
        angle2 = self.frame * 0.3
        nx2 = cex + math.cos(angle2) * (clock_r - 8)
        ny2 = cey + math.sin(angle2) * (clock_r - 8)
        pyxel.line(cex, cey, int(nx2), int(ny2), COLOR_LIME)

        # Circle of colored dots around clock
        for i, col in enumerate(CRYSTAL_COLORS):
            da = self.frame * 0.02 + i * math.pi / 2
            dx_val = math.cos(da) * (clock_r + 8)
            dy_val = math.sin(da) * (clock_r + 8)
            pyxel.pset(int(cex + dx_val), int(cey + dy_val), col)

        pyxel.text(cx - 52 + sx, 112 + sy, "Same color = COMBO chain!", COLOR_LIME)
        pyxel.text(cx - 48 + sx, 124 + sy, "COMBO x4 = SUPER CHRONO", COLOR_YELLOW)
        pyxel.text(cx - 52 + sx, 136 + sy, "(rainbow burst, 3x score)", COLOR_PINK)
        pyxel.text(cx - 46 + sx, 148 + sy, "Wrong color = HEAT + reset", COLOR_RED)
        pyxel.text(cx - 52 + sx, 160 + sy, "Your TIME ECHO replays past", COLOR_CYAN)
        pyxel.text(cx - 44 + sx, 172 + sy, "path + collects crystals!", COLOR_CYAN)

        pyxel.text(cx - 56 + sx, 190 + sy, "ARROWS / WASD: move", COLOR_WHITE)
        pyxel.text(cx - 60 + sx, 202 + sy, "Survive 60s, don't overheat!", COLOR_WHITE)

        if self.best_score > 0:
            pyxel.text(cx - 40 + sx, 216 + sy, f"BEST: {self.best_score}", COLOR_PINK)

        pyxel.text(cx - 48 + sx, 230 + sy, "ENTER to START", COLOR_WHITE)

    # ------------------------------------------------------------------
    # Game over screen
    # ------------------------------------------------------------------

    def _draw_game_over(self, sx: int, sy: int) -> None:
        pyxel.rect(20, 40, WIDTH - 40, 160, COLOR_BLACK)
        pyxel.rectb(20, 40, WIDTH - 40, 160, COLOR_WHITE)

        cx = WIDTH // 2

        if self.heat >= MAX_HEAT:
            pyxel.text(cx - 36 + sx, 54 + sy, "HEAT OVERLOAD", COLOR_RED)
        elif self.timer <= 0:
            pyxel.text(cx - 44 + sx, 54 + sy, "TIME COLLAPSED", COLOR_YELLOW)
        else:
            pyxel.text(cx - 28 + sx, 54 + sy, "GAME OVER", COLOR_RED)

        pyxel.text(cx - 40 + sx, 74 + sy, f"SCORE: {self.score}", COLOR_WHITE)
        pyxel.text(cx - 48 + sx, 90 + sy, f"MAX COMBO: x{self.max_combo}", COLOR_PINK)
        pyxel.text(cx - 36 + sx, 106 + sy, f"HEAT: {int(self.heat)}%", COLOR_ORANGE)

        if self.score >= self.best_score:
            pyxel.text(cx - 30 + sx, 126 + sy, "NEW BEST!", COLOR_YELLOW)
        pyxel.text(cx - 36 + sx, 142 + sy, f"BEST: {self.best_score}", COLOR_WHITE)

        pyxel.text(cx - 46 + sx, 170 + sy, "R to RETRY", COLOR_WHITE)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    Game()
