"""SPLASH CHAIN — Top-down water-gun fight with CA propagation and COMBO chains.

Core fun moment: water droplets spread via CA, drenching same-color buckets
in rapid succession for explosive COMBO chains, culminating in SUPER SOAKER mode.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ──────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
FPS = 60
GAME_DURATION = 60  # seconds
TOTAL_FRAMES = FPS * GAME_DURATION

# Grid
GRID_COLS = 10
GRID_ROWS = 10
CELL_SIZE = 20
GRID_X = 60
GRID_Y = 10
GRID_W = GRID_COLS * CELL_SIZE
GRID_H = GRID_ROWS * CELL_SIZE

# Spray
SPRAY_CONE_ANGLE = 30  # degrees, total cone width
DROPLETS_PER_FRAME = 4
DROPLET_SPEED_MIN = 3.0
DROPLET_SPEED_MAX = 5.0
WATER_PER_FRAME = 0.5
WATER_RECHARGE = 0.3
MAX_WATER = 100.0
NOZZLE_CYCLE_FRAMES = 180  # 3 seconds per color

# Heat
HEAT_BUILD_PER_FRAME = 0.4
HEAT_DECAY_PER_FRAME = 0.2
MAX_HEAT = 100.0
OVERHEAT_COOLDOWN = 90  # 1.5 sec
OVERHEAT_HEAT_RESET = 30.0
WRONG_COLOR_HEAT = 15.0
OVERHEAT_SCORE_PENALTY = 50

# CA Spread
CA_INTERVAL = 8
CA_MATURE_AGE = 16  # frames a cell must be wet before it can spread
CA_SPREAD_CHANCE = 0.5

# Buckets
BUCKET_SPAWN_INTERVAL = 120  # 2 sec
MAX_BUCKETS = 8
BUCKET_HP_MIN = 1
BUCKET_HP_MAX = 2

# SUPER SOAKER
SUPER_COMBO_THRESHOLD = 5
SUPER_DURATION = 300  # 5 sec
SUPER_SCORE_MULTIPLIER = 3

# Scoring
BASE_DRENCH_SCORE = 10
COMBO_BONUS_PER_LEVEL = 2

# Player
PLAYER_W = 20
PLAYER_H = 28
PLAYER_X = SCREEN_W // 2 - PLAYER_W // 2
PLAYER_Y = SCREEN_H - PLAYER_H - 8
PLAYER_COLOR = 13  # GRAY
PLAYER_HP = 5

# Bar positions
BAR_X_LEFT = 8
BAR_X_RIGHT = SCREEN_W - 20
BAR_Y = 10
BAR_W = 12
BAR_H = GRID_H

# Colors
COLOR_BLACK = 0
COLOR_WHITE = 7
COLOR_RED = 8
COLOR_GREEN = 3
COLOR_DARK_BLUE = 5
COLOR_YELLOW = 10
COLOR_LIGHT_BLUE = 6
COLOR_ORANGE = 9
COLOR_GRAY = 13
COLOR_PINK = 14
COLOR_CYAN = 12

NOZZLE_COLORS = [COLOR_RED, COLOR_GREEN, COLOR_DARK_BLUE, COLOR_YELLOW]

# ── Enums ──────────────────────────────────────────────────────────────


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class CellState(Enum):
    DRY = 0
    WET_RED = 1
    WET_GREEN = 2
    WET_BLUE = 3
    WET_YELLOW = 4
    BUCKET_RED = 5
    BUCKET_GREEN = 6
    BUCKET_BLUE = 7
    BUCKET_YELLOW = 8


WET_STATES = {
    CellState.WET_RED: COLOR_RED,
    CellState.WET_GREEN: COLOR_GREEN,
    CellState.WET_BLUE: COLOR_DARK_BLUE,
    CellState.WET_YELLOW: COLOR_YELLOW,
}

BUCKET_STATES = {
    CellState.BUCKET_RED: CellState.WET_RED,
    CellState.BUCKET_GREEN: CellState.WET_GREEN,
    CellState.BUCKET_BLUE: CellState.WET_BLUE,
    CellState.BUCKET_YELLOW: CellState.WET_YELLOW,
}

BUCKET_COLORS_MAP = {
    CellState.BUCKET_RED: COLOR_RED,
    CellState.BUCKET_GREEN: COLOR_GREEN,
    CellState.BUCKET_BLUE: COLOR_DARK_BLUE,
    CellState.BUCKET_YELLOW: COLOR_YELLOW,
}

WET_TO_BUCKET = {v: k for k, v in BUCKET_STATES.items()}


def wet_state_for_color(color_idx: int) -> CellState:
    return CellState(color_idx + 1)


def bucket_state_for_color(color_idx: int) -> CellState:
    return CellState(color_idx + 5)


def nozzle_color_idx(timer: int) -> int:
    return (timer // NOZZLE_CYCLE_FRAMES) % 4


# ── Data Classes ───────────────────────────────────────────────────────


@dataclass
class Bucket:
    col: int
    row: int
    color: int  # CellState index for WET (1-4)
    hp: int
    drenched: bool = False

    @property
    def bucket_state(self) -> int:
        return self.color + 4  # BUCKET_RED = 5, etc.


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


@dataclass
class Droplet:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    active: bool = True


# ── Game ───────────────────────────────────────────────────────────────


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Splash Chain", fps=FPS)
        pyxel.mouse(True)
        self._rng: random.Random
        self.phase: Phase
        self.score: int
        self.high_score: int
        self.combo: int
        self.max_combo: int
        self.hp: int
        self.water: float
        self.heat: float
        self.super_mode: bool
        self.super_timer: int
        self.game_timer: int
        self.cooldown_timer: int
        self.grid: list[list[int]]
        self.grid_age: list[list[int]]  # frames since cell became wet
        self.buckets: list[Bucket]
        self.particles: list[Particle]
        self.floating_texts: list[FloatingText]
        self.droplets: list[Droplet]
        self.mouse_held: bool
        self.spray_angle: float
        self.bucket_spawn_timer: int
        self.nozzle_color_idx: int
        self.nozzle_timer: int
        self.ca_timer: int
        self._post_reset: bool = False
        self.reset()
        pyxel.run(self._update, self._draw)

    def _init_state(self) -> None:
        self._rng = random.Random()
        self.phase = Phase.TITLE
        self.score = 0
        self.high_score = 0
        self.combo = 0
        self.max_combo = 0
        self.hp = PLAYER_HP
        self.water = MAX_WATER
        self.heat = 0.0
        self.super_mode = False
        self.super_timer = 0
        self.game_timer = TOTAL_FRAMES
        self.cooldown_timer = 0
        self.grid = [[CellState.DRY.value for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        self.grid_age = [[0 for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        self.buckets = []
        self.particles = []
        self.floating_texts = []
        self.droplets = []
        self.mouse_held = False
        self.spray_angle = 0.0
        self.bucket_spawn_timer = BUCKET_SPAWN_INTERVAL
        self.nozzle_color_idx = 0
        self.nozzle_timer = 0
        self.ca_timer = 0

    def reset(self) -> None:
        self._init_state()

    # ── Update ─────────────────────────────────────────────────────────

    def _update(self) -> None:
        self._handle_input()

        if self.phase == Phase.PLAYING:
            self._update_game()

    def _handle_input(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self._start_game()
        elif self.phase == Phase.PLAYING:
            self.mouse_held = pyxel.btn(pyxel.MOUSE_BUTTON_LEFT)
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_R):
                self._start_game()

    def _start_game(self) -> None:
        self._init_state()
        self.phase = Phase.PLAYING

    def _update_game(self) -> None:
        self._update_spray()
        self._update_droplets()
        self._update_ca()
        self._update_timers()
        self._update_heat()
        self._update_water()
        self._update_buckets()
        self._update_particles()
        self._update_floating_texts()
        self._check_game_over()

    def _update_spray(self) -> None:
        if not self.mouse_held:
            return
        if self.cooldown_timer > 0:
            return
        if self.water <= 0:
            return

        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        gun_tip_x = PLAYER_X + PLAYER_W // 2
        gun_tip_y = PLAYER_Y - 4
        dx = mx - gun_tip_x
        dy = my - gun_tip_y
        self.spray_angle = math.atan2(dy, dx)

        nozzle_color = NOZZLE_COLORS[self.nozzle_color_idx]
        half_cone = math.radians(SPRAY_CONE_ANGLE / 2)

        for _ in range(DROPLETS_PER_FRAME):
            angle = self.spray_angle + self._rng.uniform(-half_cone, half_cone)
            speed = self._rng.uniform(DROPLET_SPEED_MIN, DROPLET_SPEED_MAX)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self.droplets.append(Droplet(float(gun_tip_x), float(gun_tip_y), vx, vy, nozzle_color))

    def _update_droplets(self) -> None:
        for d in self.droplets:
            if not d.active:
                continue
            d.x += d.vx
            d.y += d.vy
            d.vy += 0.05  # slight gravity

            col = int((d.x - GRID_X) // CELL_SIZE)
            row = int((d.y - GRID_Y) // CELL_SIZE)

            if 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS:
                self._hit_cell(col, row, d.color)
                self._spawn_spray_particles(d.x, d.y, d.color)
                d.active = False
                continue

            # Bounce off screen edges
            if d.x < 0 or d.x > SCREEN_W or d.y < 0 or d.y > SCREEN_H:
                d.active = False

        self.droplets = [d for d in self.droplets if d.active]

    def _hit_cell(self, col: int, row: int, color: int) -> None:
        cell = self.grid[row][col]
        wet_state = self._color_to_wet_state(color)

        # Check for bucket hit
        bucket = self._bucket_at(col, row)
        if bucket is not None and not bucket.drenched:
            if self.super_mode or bucket.color == wet_state.value:
                self._hit_bucket(bucket, col, row, color)
            else:
                self._wrong_color_penalty(bucket, col, row)
            return

        if cell == CellState.DRY.value:
            self.grid[row][col] = wet_state.value
            self.grid_age[row][col] = 0
        else:
            self.grid[row][col] = wet_state.value
            self.grid_age[row][col] = 0

    def _color_to_wet_state(self, color: int) -> CellState:
        for wet, c in WET_STATES.items():
            if c == color:
                return wet
        return CellState.WET_RED

    def _bucket_at(self, col: int, row: int) -> Bucket | None:
        for b in self.buckets:
            if b.col == col and b.row == row and not b.drenched:
                return b
        return None

    def _hit_bucket(self, bucket: Bucket, col: int, row: int, color: int) -> None:
        bucket.hp -= 1
        if bucket.hp <= 0:
            bucket.drenched = True
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            multiplier = 1
            if self.super_mode:
                multiplier = SUPER_SCORE_MULTIPLIER
            points = (BASE_DRENCH_SCORE + self.combo * COMBO_BONUS_PER_LEVEL) * multiplier
            self.score += points

            self._spawn_drench_particles(col, row, color)
            self.floating_texts.append(
                FloatingText(
                    float(GRID_X + col * CELL_SIZE + CELL_SIZE // 2),
                    float(GRID_Y + row * CELL_SIZE),
                    f"+{points}",
                    30,
                    COLOR_CYAN,
                )
            )
            self.floating_texts.append(
                FloatingText(
                    float(GRID_X + col * CELL_SIZE + CELL_SIZE // 2),
                    float(GRID_Y + row * CELL_SIZE + 10),
                    f"COMBO x{self.combo}",
                    30,
                    COLOR_WHITE,
                )
            )

            wet_state = CellState(bucket.color)
            self.grid[row][col] = wet_state.value
            self.grid_age[row][col] = 0

            if self.combo >= SUPER_COMBO_THRESHOLD and not self.super_mode:
                self._activate_super()
        else:
            # Partial hit, still do some feedback but no score
            pass

    def _wrong_color_penalty(self, bucket: Bucket, col: int, row: int) -> None:
        self.combo = 0
        self.heat = min(MAX_HEAT, self.heat + WRONG_COLOR_HEAT)
        self.floating_texts.append(
            FloatingText(
                float(GRID_X + col * CELL_SIZE + CELL_SIZE // 2),
                float(GRID_Y + row * CELL_SIZE),
                "MISS",
                30,
                COLOR_ORANGE,
            )
        )

    def _update_ca(self) -> None:
        self.ca_timer += 1
        if self.ca_timer < CA_INTERVAL:
            return
        self.ca_timer = 0
        self._ca_spread()

    def _ca_spread(self) -> None:
        changes: list[tuple[int, int, int]] = []  # (r, c, new_value)

        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                cell = self.grid[r][c]
                if cell == CellState.DRY.value:
                    continue
                if self.grid_age[r][c] < CA_MATURE_AGE:
                    continue

                bucket = self._bucket_at(c, r)
                if bucket is not None:
                    continue

                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < GRID_ROWS and 0 <= nc < GRID_COLS:
                        if self._rng.random() >= CA_SPREAD_CHANCE:
                            continue
                        target = self.grid[nr][nc]
                        if target == CellState.DRY.value:
                            changes.append((nr, nc, cell))
                        elif CellState.DRY.value < target <= CellState.WET_YELLOW.value:
                            t_bucket = self._bucket_at(nc, nr)
                            if t_bucket is not None and not t_bucket.drenched:
                                if self.super_mode or t_bucket.color == cell:
                                    self._hit_bucket(t_bucket, nc, nr, self._wet_state_to_color(cell))

        for r, c, val in changes:
            self.grid[r][c] = val
            self.grid_age[r][c] = 0

    def _wet_state_to_color(self, wet_value: int) -> int:
        for wet_state, color_val in WET_STATES.items():
            if wet_state.value == wet_value:
                return color_val
        return COLOR_RED

    def _update_timers(self) -> None:
        self.game_timer -= 1
        self.nozzle_timer += 1
        self.nozzle_color_idx = nozzle_color_idx(self.nozzle_timer)

        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False

        if self.cooldown_timer > 0:
            self.cooldown_timer -= 1

        # Age grid cells
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.grid[r][c] != CellState.DRY.value:
                    self.grid_age[r][c] += 1

    def _update_heat(self) -> None:
        if self.mouse_held and self.cooldown_timer <= 0:
            self.heat = min(MAX_HEAT, self.heat + HEAT_BUILD_PER_FRAME)
            if self.heat >= MAX_HEAT:
                self._overheat()
        else:
            self.heat = max(0.0, self.heat - HEAT_DECAY_PER_FRAME)

    def _overheat(self) -> None:
        self.hp -= 1
        self.cooldown_timer = OVERHEAT_COOLDOWN
        self.heat = OVERHEAT_HEAT_RESET
        self.super_mode = False
        self.super_timer = 0
        self.score = max(0, self.score - OVERHEAT_SCORE_PENALTY)
        self.floating_texts.append(
            FloatingText(float(SCREEN_W // 2), float(SCREEN_H // 2), "OVERHEAT!", 60, COLOR_ORANGE)
        )

    def _update_water(self) -> None:
        if self.cooldown_timer > 0:
            self.water = min(MAX_WATER, self.water + WATER_RECHARGE)
        elif self.mouse_held:
            if self.super_mode:
                return  # unlimited water
            self.water = max(0.0, self.water - WATER_PER_FRAME)
        else:
            self.water = min(MAX_WATER, self.water + WATER_RECHARGE)

    def _update_buckets(self) -> None:
        self.bucket_spawn_timer -= 1
        if self.bucket_spawn_timer <= 0:
            self.bucket_spawn_timer = BUCKET_SPAWN_INTERVAL
            self._spawn_bucket()

    def _spawn_bucket(self) -> None:
        active_buckets = [b for b in self.buckets if not b.drenched]
        if len(active_buckets) >= MAX_BUCKETS:
            return

        for _ in range(50):
            col = self._rng.randint(0, GRID_COLS - 1)
            row = self._rng.randint(0, GRID_ROWS - 1)
            if self._bucket_at(col, row) is not None:
                continue
            # Don't spawn on wet cells (to give visual clarity)
            # Allow spawning anywhere for simplicity
            color_idx = self._rng.randint(1, 4)  # WET_RED (1) through WET_YELLOW (4)
            hp = self._rng.randint(BUCKET_HP_MIN, BUCKET_HP_MAX)
            self.buckets.append(Bucket(col, row, color_idx, hp))
            break

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self._spawn_super_particles()
        self.floating_texts.append(
            FloatingText(float(SCREEN_W // 2), float(SCREEN_H // 2 - 30), "SUPER SOAKER!", 90, COLOR_PINK)
        )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1  # gravity
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _spawn_spray_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(self._rng.randint(5, 10)):
            vx = self._rng.uniform(-1.5, 1.5)
            vy = self._rng.uniform(-2.5, -0.5)
            life = self._rng.randint(15, 25)
            self.particles.append(Particle(x, y, vx, vy, life, color))

    def _spawn_drench_particles(self, col: int, row: int, color: int) -> None:
        cx = GRID_X + col * CELL_SIZE + CELL_SIZE // 2
        cy = GRID_Y + row * CELL_SIZE + CELL_SIZE // 2
        for _ in range(self._rng.randint(15, 20)):
            vx = self._rng.uniform(-2.0, 2.0)
            vy = self._rng.uniform(-3.0, -1.0)
            life = self._rng.randint(15, 25)
            self.particles.append(Particle(cx, cy, vx, vy, life, color))

    def _spawn_super_particles(self) -> None:
        cx = PLAYER_X + PLAYER_W // 2
        cy = PLAYER_Y + PLAYER_H // 2
        for _ in range(30):
            vx = self._rng.uniform(-3.0, 3.0)
            vy = self._rng.uniform(-4.0, -0.5)
            life = self._rng.randint(20, 35)
            color = self._rng.choice(NOZZLE_COLORS)
            self.particles.append(Particle(cx, cy, vx, vy, life, color))

    def _check_game_over(self) -> None:
        if self.hp <= 0 or self.game_timer <= 0:
            self.phase = Phase.GAME_OVER
            if self.score > self.high_score:
                self.high_score = self.score

    # ── Draw ───────────────────────────────────────────────────────────

    def _draw(self) -> None:
        pyxel.cls(COLOR_BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = "SPLASH CHAIN"
        title_w = len(title) * 4  # approximate with pyxel.text width
        pyxel.text(SCREEN_W // 2 - title_w // 2, 60, title, COLOR_WHITE)

        subtitle = "Click to Start"
        sub_w = len(subtitle) * 4
        pyxel.text(SCREEN_W // 2 - sub_w // 2, 90, subtitle, COLOR_CYAN)

        controls = [
            "Hold LMB to spray water",
            "Aim at the grid to wet cells",
            "Match bucket colors for COMBO",
            "COMBO >= 5 = SUPER SOAKER!",
            "Watch your heat gauge!",
        ]
        for i, line in enumerate(controls):
            lw = len(line) * 4
            pyxel.text(SCREEN_W // 2 - lw // 2, 120 + i * 12, line, COLOR_GRAY)

    def _draw_game(self) -> None:
        self._draw_grid()
        self._draw_droplets()
        self._draw_player()
        self._draw_bars()
        self._draw_hud()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_super_indicator()

    def _draw_grid(self) -> None:
        # Draw cells
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                x = GRID_X + c * CELL_SIZE
                y = GRID_Y + r * CELL_SIZE
                cell = self.grid[r][c]

                if cell == CellState.DRY.value:
                    pyxel.rectb(x, y, CELL_SIZE, CELL_SIZE, 5)  # dark outline only
                else:
                    color = WET_STATES.get(CellState(cell), COLOR_WHITE)
                    pyxel.rect(x, y, CELL_SIZE, CELL_SIZE, color)

        # Draw buckets
        for b in self.buckets:
            if b.drenched:
                continue
            x = GRID_X + b.col * CELL_SIZE
            y = GRID_Y + b.row * CELL_SIZE
            bucket_color = BUCKET_COLORS_MAP.get(CellState(b.bucket_state), COLOR_WHITE)
            # Thick border for bucket
            pyxel.rectb(x, y, CELL_SIZE, CELL_SIZE, bucket_color)
            pyxel.rectb(x + 1, y + 1, CELL_SIZE - 2, CELL_SIZE - 2, bucket_color)
            pyxel.rectb(x + 2, y + 2, CELL_SIZE - 4, CELL_SIZE - 4, bucket_color)
            # HP indicator (dots)
            for i in range(b.hp):
                pyxel.circ(x + 4 + i * 6, y + 4, 2, bucket_color)

    def _draw_droplets(self) -> None:
        for d in self.droplets:
            if d.active:
                pyxel.pset(int(d.x), int(d.y), d.color)

    def _draw_player(self) -> None:
        color = COLOR_GRAY
        if self.super_mode:
            color = COLOR_PINK

        # Body
        pyxel.rect(PLAYER_X, PLAYER_Y, PLAYER_W, PLAYER_H, color)
        # Head
        pyxel.rect(PLAYER_X + 3, PLAYER_Y - 6, PLAYER_W - 6, 8, color)
        # Eyes
        pyxel.pset(PLAYER_X + 5, PLAYER_Y - 3, COLOR_BLACK)
        pyxel.pset(PLAYER_X + PLAYER_W - 7, PLAYER_Y - 3, COLOR_BLACK)

        # Water gun
        gun_color = NOZZLE_COLORS[self.nozzle_color_idx]
        gun_center_x = PLAYER_X + PLAYER_W // 2
        gun_top_y = PLAYER_Y - 6
        gun_length = 12
        end_x = gun_center_x + math.cos(self.spray_angle) * gun_length
        end_y = gun_top_y + math.sin(self.spray_angle) * gun_length
        pyxel.tri(gun_center_x - 2, gun_top_y, gun_center_x + 2, gun_top_y, int(end_x), int(end_y), gun_color)

        if self.mouse_held and self.cooldown_timer <= 0:
            self._draw_spray_cone()

        # SUPER SOAKER glow
        if self.super_mode:
            pyxel.rectb(PLAYER_X - 2, PLAYER_Y - 8, PLAYER_W + 4, PLAYER_H + 10, COLOR_PINK)
            if pyxel.frame_count % 10 < 5:
                pyxel.rectb(PLAYER_X - 3, PLAYER_Y - 9, PLAYER_W + 6, PLAYER_H + 12, COLOR_PINK)

    def _draw_spray_cone(self) -> None:
        gun_center_x = float(PLAYER_X + PLAYER_W // 2)
        gun_top_y = float(PLAYER_Y - 6)
        cone_length = 80.0
        half_cone = math.radians(SPRAY_CONE_ANGLE / 2)

        left_x = int(gun_center_x + math.cos(self.spray_angle - half_cone) * cone_length)
        left_y = int(gun_top_y + math.sin(self.spray_angle - half_cone) * cone_length)
        right_x = int(gun_center_x + math.cos(self.spray_angle + half_cone) * cone_length)
        right_y = int(gun_top_y + math.sin(self.spray_angle + half_cone) * cone_length)

        gun_color = NOZZLE_COLORS[self.nozzle_color_idx]
        pyxel.tri(
            int(gun_center_x), int(gun_top_y),
            left_x, left_y,
            right_x, right_y,
            gun_color,
        )

    def _draw_bars(self) -> None:
        # Heat bar (left side)
        heat_h = int((self.heat / MAX_HEAT) * BAR_H)
        heat_color = COLOR_RED if self.heat >= MAX_HEAT * 0.8 else COLOR_ORANGE
        pyxel.rectb(BAR_X_LEFT, BAR_Y, BAR_W, BAR_H, heat_color)
        pyxel.rect(BAR_X_LEFT, BAR_Y + BAR_H - heat_h, BAR_W, heat_h, heat_color)

        # Water bar (right side)
        water_h = int((self.water / MAX_WATER) * BAR_H)
        pyxel.rectb(BAR_X_RIGHT, BAR_Y, BAR_W, BAR_H, COLOR_LIGHT_BLUE)
        pyxel.rect(BAR_X_RIGHT, BAR_Y + BAR_H - water_h, BAR_W, water_h, COLOR_LIGHT_BLUE)

        # Labels
        pyxel.text(BAR_X_LEFT, BAR_Y + BAR_H + 2, "H", COLOR_ORANGE)
        pyxel.text(BAR_X_RIGHT, BAR_Y + BAR_H + 2, "W", COLOR_LIGHT_BLUE)

    def _draw_hud(self) -> None:
        # Score
        pyxel.text(2, 2, f"SCORE: {self.score}", COLOR_WHITE)
        # Combo
        combo_color = COLOR_CYAN
        if self.combo >= SUPER_COMBO_THRESHOLD:
            combo_color = COLOR_PINK
        pyxel.text(2, 10, f"COMBO: x{self.combo}", combo_color)
        # HP
        hp_text = f"HP: {self.hp}"
        pyxel.text(SCREEN_W - len(hp_text) * 4 - 2, 2, hp_text, COLOR_RED if self.hp <= 2 else COLOR_GREEN)
        # Timer
        seconds = max(0, self.game_timer // FPS)
        timer_text = f"TIME: {seconds}s"
        pyxel.text(SCREEN_W - len(timer_text) * 4 - 2, 10, timer_text, COLOR_WHITE if seconds > 10 else COLOR_RED)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 30
            if alpha > 0.3:
                pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life > 0:
                color = ft.color
                if ft.life < 10:
                    color = COLOR_BLACK if ft.life % 2 == 0 else ft.color
                pyxel.text(int(ft.x - len(ft.text) * 2), int(ft.y), ft.text, color)

    def _draw_super_indicator(self) -> None:
        if self.super_mode:
            sec = self.super_timer // FPS
            tenths = (self.super_timer % FPS) // 6
            text = f"SUPER {sec}.{tenths}s"
            tw = len(text) * 4
            pyxel.text(SCREEN_W // 2 - tw // 2, GRID_Y + GRID_H + 4, text, COLOR_PINK)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 20, 60, "GAME OVER", COLOR_RED)
        score_text = f"Score: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_text) * 2, 80, score_text, COLOR_WHITE)
        combo_text = f"Max Combo: x{self.max_combo}"
        pyxel.text(SCREEN_W // 2 - len(combo_text) * 2, 92, combo_text, COLOR_CYAN)
        high_text = f"High Score: {self.high_score}"
        pyxel.text(SCREEN_W // 2 - len(high_text) * 2, 104, high_text, COLOR_YELLOW)
        retry_text = "Click or press R to Retry"
        pyxel.text(SCREEN_W // 2 - len(retry_text) * 2, 130, retry_text, COLOR_GRAY)


# ── Entry ──────────────────────────────────────────────────────────────

def main() -> None:
    Game()


if __name__ == "__main__":
    main()
