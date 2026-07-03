"""
DODGE SURGE — A Color-Match Dodgeball Game

Top-down dodgeball court. Player dodges and catches/throwing color-matched balls.
Same-color consecutive catches build COMBO chain. COMBO>=4 triggers SUPER THROW.
Ghost ball trails and CA danger zones on court.
"""

from __future__ import annotations

import dataclasses
import enum
import math
import random
from typing import ClassVar

import pyxel


# ---------------------------------------------------------------------------
# Color Constants (Pyxel palette integers — NOT pyxel.COLOR_XXX)
# ---------------------------------------------------------------------------
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

COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
COLOR_NAMES: list[str] = ["RED", "GREEN", "BLUE", "YELLOW"]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Phase(enum.Enum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------
@dataclasses.dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    is_player_ball: bool
    life: int  # ticks remaining (for ghost trail display)


@dataclasses.dataclass
class Opponent:
    x: float
    y: float
    color: int
    hp: int
    throw_timer: int
    flash_timer: int  # hit feedback


@dataclasses.dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


@dataclasses.dataclass
class DangerCell:
    x: int  # col
    y: int  # row
    life: int  # CA spread timer
    intensity: int  # 1-3 for colour brightness


@dataclasses.dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int
    vy: float


# ---------------------------------------------------------------------------
# Game Class
# ---------------------------------------------------------------------------
class Game:
    SCREEN_W: ClassVar[int] = 320
    SCREEN_H: ClassVar[int] = 240
    COURT_TOP: ClassVar[int] = 40
    COURT_BOT: ClassVar[int] = 220
    COURT_MID: ClassVar[int] = 130
    PLAYER_ZONE_TOP: ClassVar[int] = 140
    MAX_HEAT: ClassVar[float] = 100.0
    HEAT_DECAY: ClassVar[float] = 0.05
    HEAT_ON_HIT: ClassVar[float] = 15.0
    COMBO_FOR_SUPER: ClassVar[int] = 4
    SUPER_DURATION: ClassVar[int] = 300
    GAME_TIME: ClassVar[int] = 60 * 60
    THROW_SPEED: ClassVar[float] = 4.0
    BALL_RADIUS: ClassVar[int] = 6
    PLAYER_SPEED: ClassVar[float] = 3.0
    PLAYER_RADIUS: ClassVar[int] = 10
    OPPONENT_RADIUS: ClassVar[int] = 10
    OPPONENT_COUNT: ClassVar[int] = 3
    MAX_BALLS_ON_FIELD: ClassVar[int] = 6
    GHOST_TRAIL_LENGTH: ClassVar[int] = 10
    CA_GRID_COLS: ClassVar[int] = 32
    CA_GRID_ROWS: ClassVar[int] = 18
    CA_CELL_SIZE: ClassVar[int] = 10
    OPPONENT_HP_BASE: ClassVar[int] = 3
    OPPONENT_THROW_MIN: ClassVar[int] = 40
    OPPONENT_THROW_MAX: ClassVar[int] = 90
    BALL_SPAWN_MIN: ClassVar[int] = 60
    BALL_SPAWN_MAX: ClassVar[int] = 90

    def __init__(self) -> None:
        pyxel.init(
            self.SCREEN_W,
            self.SCREEN_H,
            title="DODGE SURGE",
            display_scale=2,
            fps=60,
        )
        self._rng = random.Random()
        self._play_sound = pyxel.play
        self._init_state()
        pyxel.run(self.update, self.draw)

    def _init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.player_x: float = float(self.SCREEN_W // 2)
        self.player_y: float = float(self.SCREEN_H - 50)
        self.player_color: int = 0
        self.held_ball_color: int = -1
        self.last_caught_color: int = -1
        self.opponents: list[Opponent] = []
        self.balls: list[Ball] = []
        self.particles: list[Particle] = []
        self.danger_grid: list[list[int]] = [
            [0 for _ in range(self.CA_GRID_COLS)] for _ in range(self.CA_GRID_ROWS)
        ]
        self.ghost_trail: list[tuple[float, float, int]] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.heat: float = 0.0
        self.game_timer: int = self.GAME_TIME
        self.frame: int = 0
        self.shake_frames: int = 0
        self.floating_texts: list[FloatingText] = []
        self._difficulty_level: int = 0
        self._ball_spawn_timer: int = self._rng.randint(
            self.BALL_SPAWN_MIN, self.BALL_SPAWN_MAX
        )
        self._super_auto_throw_timer: int = 0

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.player_x = float(self.SCREEN_W // 2)
        self.player_y = float(self.SCREEN_H - 50)
        self.player_color = 0
        self.held_ball_color = -1
        self.last_caught_color = -1
        self.opponents.clear()
        self.balls.clear()
        self.particles.clear()
        for row in range(self.CA_GRID_ROWS):
            for col in range(self.CA_GRID_COLS):
                self.danger_grid[row][col] = 0
        self.ghost_trail.clear()
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.super_mode = False
        self.super_timer = 0
        self.heat = 0.0
        self.game_timer = self.GAME_TIME
        self.frame = 0
        self.shake_frames = 0
        self.floating_texts.clear()
        self._difficulty_level = 0
        self._ball_spawn_timer = self._rng.randint(
            self.BALL_SPAWN_MIN, self.BALL_SPAWN_MAX
        )
        self._super_auto_throw_timer = 0

    # ---- helpers ---------------------------------------------------------

    def _spawn_opponents(self) -> None:
        self.opponents.clear()
        cols = COLORS[: self.OPPONENT_COUNT]
        margin = 40
        spacing = (self.SCREEN_W - margin * 2) // (self.OPPONENT_COUNT - 1) if self.OPPONENT_COUNT > 1 else 0
        for i in range(self.OPPONENT_COUNT):
            x = float(margin + spacing * i) if self.OPPONENT_COUNT > 1 else float(self.SCREEN_W // 2)
            y = float(self.COURT_TOP + 30)
            hp = self.OPPONENT_HP_BASE + self._difficulty_level
            opp = Opponent(
                x=x,
                y=y,
                color=cols[i],
                hp=hp,
                throw_timer=self._get_opponent_throw_interval(),
                flash_timer=0,
            )
            self.opponents.append(opp)

    def _get_opponent_throw_interval(self) -> int:
        base_min = max(20, self.OPPONENT_THROW_MIN - self._difficulty_level * 10)
        base_max = max(30, self.OPPONENT_THROW_MAX - self._difficulty_level * 10)
        return self._rng.randint(base_min, base_max)

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = self.SUPER_DURATION
        self._super_auto_throw_timer = 15
        self._add_floating_text(
            self.player_x, self.player_y - 20, "SUPER!", YELLOW, 60
        )
        for _ in range(20):
            p = Particle(
                x=self.player_x,
                y=self.player_y,
                vx=self._rng.uniform(-2.0, 2.0),
                vy=self._rng.uniform(-2.0, 2.0),
                color=self._rng.choice(COLORS),
                life=20 + self._rng.randint(0, 20),
            )
            self.particles.append(p)

    def _add_floating_text(
        self, x: float, y: float, text: str, color: int, life: int = 30
    ) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, color=color, life=life, vy=-1.0)
        )

    def _spawn_ball_at(self, x: float, y: float, color: int, is_player_ball: bool, vx: float = 0, vy: float = 0) -> None:
        if vx == 0 and vy == 0:
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self.THROW_SPEED * self._rng.uniform(0.7, 1.3)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
        ball = Ball(
            x=x,
            y=y,
            vx=vx,
            vy=vy,
            color=color,
            is_player_ball=is_player_ball,
            life=self.GHOST_TRAIL_LENGTH,
        )
        self.balls.append(ball)

    def _spawn_neutral_ball(self) -> None:
        x = float(self._rng.randint(40, self.SCREEN_W - 40))
        color = self._rng.randint(0, 3)
        self._spawn_ball_at(x, float(self.COURT_MID), color, is_player_ball=False)

    def _spawn_opponent_throw(self, opp: Opponent) -> None:
        dx = self.player_x - opp.x
        dy = self.player_y - opp.y
        dist = max(0.1, math.hypot(dx, dy))
        speed = self.THROW_SPEED * 1.2
        vx = dx / dist * speed
        vy = dy / dist * speed
        self._spawn_ball_at(opp.x, opp.y, opp.color, is_player_ball=False, vx=vx, vy=vy)

    def _player_throw(self) -> None:
        if self.held_ball_color < 0:
            return
        living = [o for o in self.opponents if o.hp > 0]
        if not living:
            # No target — throw forward
            self._spawn_ball_at(
                self.player_x,
                self.player_y - 15,
                self.held_ball_color,
                is_player_ball=True,
                vx=0,
                vy=-self.THROW_SPEED,
            )
        else:
            target = min(living, key=lambda o: math.hypot(o.x - self.player_x, o.y - self.player_y))
            dx = target.x - self.player_x
            dy = target.y - self.player_y
            dist = max(0.1, math.hypot(dx, dy))
            speed = self.THROW_SPEED * 1.8
            vx = dx / dist * speed
            vy = dy / dist * speed
            self._spawn_ball_at(
                self.player_x,
                self.player_y - 8,
                self.held_ball_color,
                is_player_ball=True,
                vx=vx,
                vy=vy,
            )
        self.held_ball_color = -1

    def _mark_danger(self, x: float, y: float) -> None:
        col = int(x) // self.CA_CELL_SIZE
        row = (int(y) - self.COURT_TOP) // self.CA_CELL_SIZE
        if 0 <= col < self.CA_GRID_COLS and 0 <= row < self.CA_GRID_ROWS:
            self.danger_grid[row][col] = 3

    def _update_ca_grid(self) -> None:
        new_grid = [row[:] for row in self.danger_grid]
        for row in range(self.CA_GRID_ROWS):
            for col in range(self.CA_GRID_COLS):
                val = self.danger_grid[row][col]
                if val > 0:
                    # Spread to neighbours
                    spread_val = val - 1
                    if spread_val > 0:
                        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                            nr, nc = row + dr, col + dc
                            if 0 <= nr < self.CA_GRID_ROWS and 0 <= nc < self.CA_GRID_COLS:
                                if new_grid[nr][nc] < spread_val:
                                    new_grid[nr][nc] = spread_val
                    # Decay original
                    new_grid[row][col] = max(0, val - 1)
        self.danger_grid = new_grid

    def _is_in_danger(self, x: float, y: float) -> bool:
        col = int(x) // self.CA_CELL_SIZE
        row = (int(y) - self.COURT_TOP) // self.CA_CELL_SIZE
        if 0 <= col < self.CA_GRID_COLS and 0 <= row < self.CA_GRID_ROWS:
            return self.danger_grid[row][col] > 0
        return False

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            p = Particle(
                x=x,
                y=y,
                vx=self._rng.uniform(-1.5, 1.5),
                vy=self._rng.uniform(-1.5, 1.5),
                color=color,
                life=10 + self._rng.randint(0, 10),
            )
            self.particles.append(p)

    def _eliminate_opponent(self, opp: Opponent, ball_color: int) -> None:
        opp.hp = 0
        self._spawn_particles(opp.x, opp.y, opp.color, 12)
        multiplier = 3.0 if self.super_mode else 1.0
        bonus = 1 + self.combo * 0.5
        elim_score = int(100 * bonus * multiplier)
        self.score += elim_score
        self._add_floating_text(
            opp.x, opp.y - 10, f"+{elim_score}", YELLOW, 30
        )
        # Schedule respawn
        opp.hp = self.OPPONENT_HP_BASE + self._difficulty_level
        opp.x = float(self._rng.randint(40, self.SCREEN_W - 40))
        opp.y = float(self.COURT_TOP + 20 + self._rng.randint(0, 30))
        opp.throw_timer = self._get_opponent_throw_interval()

    def _on_catch(self, ball: Ball) -> None:
        color = ball.color
        if self.last_caught_color == color:
            self.combo += 1
        else:
            self.combo = 1
        self.last_caught_color = color
        self.held_ball_color = color
        self.player_color = color
        self.max_combo = max(self.max_combo, self.combo)
        multiplier = 3.0 if self.super_mode else 1.0
        bonus = 1 + self.combo * 0.5
        catch_score = int(10 * bonus * multiplier)
        self.score += catch_score
        self._add_floating_text(
            self.player_x, self.player_y - 15, f"+{catch_score}", COLORS[color], 20
        )
        self._spawn_particles(self.player_x, self.player_y, color, 8)
        self._mark_danger(self.player_x, self.player_y)
        if self.combo >= self.COMBO_FOR_SUPER and not self.super_mode:
            self._activate_super()

    # ---- update ----------------------------------------------------------

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self._spawn_opponents()
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self._spawn_opponents()
        elif self.phase == Phase.PLAYING:
            self._update_playing()

    def _update_playing(self) -> None:
        self.frame += 1
        self.game_timer -= 1

        # Difficulty scaling
        elapsed_seconds = (self.GAME_TIME - self.game_timer) // 60
        new_diff = elapsed_seconds // 15
        if new_diff > self._difficulty_level:
            self._difficulty_level = new_diff
            for opp in self.opponents:
                opp.hp = max(1, opp.hp + 1)

        # Game over checks — BEFORE decay (decaying 100 -> 99.7 would miss the check)
        if self.game_timer <= 0 or self.heat >= self.MAX_HEAT:
            self.phase = Phase.GAME_OVER
            return

        # Heat decay
        if self.heat > 0:
            self.heat = max(0.0, self.heat - self.HEAT_DECAY)

        # Player movement
        speed = self.PLAYER_SPEED
        if self._is_in_danger(self.player_x, self.player_y):
            speed *= 0.7
        dx = dy = 0.0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx -= 1
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx += 1
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy -= 1
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy += 1
        if dx != 0 or dy != 0:
            mag = math.hypot(dx, dy)
            dx = dx / mag * speed
            dy = dy / mag * speed
        self.player_x += dx
        self.player_y += dy
        self.player_x = max(float(self.PLAYER_RADIUS), min(float(self.SCREEN_W - self.PLAYER_RADIUS), self.player_x))
        self.player_y = max(float(self.PLAYER_ZONE_TOP + self.PLAYER_RADIUS), min(float(self.COURT_BOT - self.PLAYER_RADIUS), self.player_y))

        # Throw
        if pyxel.btnp(pyxel.KEY_SPACE) and self.held_ball_color >= 0:
            self._player_throw()

        # SUPER mode
        if self.super_mode:
            self.super_timer -= 1
            self._super_auto_throw_timer -= 1
            if self._super_auto_throw_timer <= 0:
                self._super_auto_throw_timer = 15
                if self.held_ball_color >= 0:
                    self._player_throw()
            if self.super_timer <= 0:
                self.super_mode = False
            # Super particles
            if self.frame % 8 == 0:
                p = Particle(
                    x=self.player_x + self._rng.uniform(-8, 8),
                    y=self.player_y + self._rng.uniform(-8, 8),
                    vx=self._rng.uniform(-1, 1),
                    vy=self._rng.uniform(-1, 1),
                    color=self._rng.choice(COLORS),
                    life=15,
                )
                self.particles.append(p)

        # Ball spawning (neutral balls)
        self._ball_spawn_timer -= 1
        if self._ball_spawn_timer <= 0:
            if len(self.balls) < self.MAX_BALLS_ON_FIELD:
                self._spawn_neutral_ball()
            self._ball_spawn_timer = self._rng.randint(
                self.BALL_SPAWN_MIN, self.BALL_SPAWN_MAX
            )

        # Opponent AI
        for opp in self.opponents:
            if opp.flash_timer > 0:
                opp.flash_timer -= 1
            opp.throw_timer -= 1
            if opp.throw_timer <= 0 and opp.hp > 0:
                self._spawn_opponent_throw(opp)
                opp.throw_timer = self._get_opponent_throw_interval()

        # Shake decay
        if self.shake_frames > 0:
            self.shake_frames -= 1

        # Ball update & player catch / hit
        new_balls: list[Ball] = []
        for ball in self.balls:
            ball.x += ball.vx
            ball.y += ball.vy

            # Bounce off court walls
            if ball.x - self.BALL_RADIUS < 0:
                ball.x = float(self.BALL_RADIUS)
                ball.vx = abs(ball.vx)
                self._mark_danger(ball.x, ball.y)
            elif ball.x + self.BALL_RADIUS > self.SCREEN_W:
                ball.x = float(self.SCREEN_W - self.BALL_RADIUS)
                ball.vx = -abs(ball.vx)
                self._mark_danger(ball.x, ball.y)
            if ball.y - self.BALL_RADIUS < self.COURT_TOP:
                ball.y = float(self.COURT_TOP + self.BALL_RADIUS)
                ball.vy = abs(ball.vy)
                self._mark_danger(ball.x, ball.y)
            elif ball.y + self.BALL_RADIUS > self.COURT_BOT:
                ball.y = float(self.COURT_BOT - self.BALL_RADIUS)
                ball.vy = -abs(ball.vy)
                self._mark_danger(ball.x, ball.y)

            # Remove out of bounds
            if ball.y < self.COURT_TOP - 20 or ball.y > self.COURT_BOT + 20:
                continue

            # Player catch (catch wins over hit)
            dist_to_player = math.hypot(ball.x - self.player_x, ball.y - self.player_y)
            if dist_to_player < self.PLAYER_RADIUS + self.BALL_RADIUS:
                if not ball.is_player_ball:
                    self._on_catch(ball)
                    continue
                # Own ball hit on player — always bad
                self.heat += self.HEAT_ON_HIT
                self.shake_frames = 5
                self.combo = 0
                self._add_floating_text(ball.x, ball.y, "HIT! +15", RED, 30)
                self._spawn_particles(ball.x, ball.y, RED, 16)
                self._mark_danger(ball.x, ball.y)
                continue

            # Opponent ball hits player
            if not ball.is_player_ball:
                dist = math.hypot(ball.x - self.player_x, ball.y - self.player_y)
                if dist < self.PLAYER_RADIUS + self.BALL_RADIUS:
                    self.heat += self.HEAT_ON_HIT
                    self.shake_frames = 5
                    self.combo = 0
                    self._add_floating_text(ball.x, ball.y, "HIT! +15", RED, 30)
                    self._spawn_particles(ball.x, ball.y, RED, 16)
                    self._mark_danger(ball.x, ball.y)
                    continue

            # Player ball hits opponent
            if ball.is_player_ball:
                for opp in self.opponents:
                    if opp.hp <= 0:
                        continue
                    dist = math.hypot(ball.x - opp.x, ball.y - opp.y)
                    if dist < self.OPPONENT_RADIUS + self.BALL_RADIUS:
                        opp.hp -= 1
                        opp.flash_timer = 10
                        self._spawn_particles(ball.x, ball.y, ball.color, 8)
                        self._mark_danger(ball.x, ball.y)
                        if opp.hp <= 0:
                            self._eliminate_opponent(opp, ball.color)
                        continue  # ball consumed

            new_balls.append(ball)
        self.balls = new_balls

        # Ghost trail
        for ball in self.balls:
            if ball.life > 0:
                ball.life -= 1

        # CA danger grid
        if self.frame % 30 == 0:
            self._update_ca_grid()

        # Particles
        alive_particles: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
            if p.life > 0:
                alive_particles.append(p)
        self.particles = alive_particles

        # Floating texts
        alive_texts: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life > 0:
                alive_texts.append(ft)
        self.floating_texts = alive_texts

    # ---- draw ------------------------------------------------------------

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.shake_frames > 0:
            ox = self._rng.randint(-2, 2)
            oy = self._rng.randint(-2, 2)
            pyxel.camera(ox, oy)
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()

    def _draw_title(self) -> None:
        pyxel.text(self.SCREEN_W // 2 - 48, 60, "DODGE SURGE", RED)
        pyxel.text(self.SCREEN_W // 2 - 56, 72, "A Color-Match Dodgeball Game", WHITE)
        pyxel.text(
            self.SCREEN_W // 2 - 52, 110, "ARROWS/WASD: Move", GRAY
        )
        pyxel.text(
            self.SCREEN_W // 2 - 52, 122, "SPACE: Throw held ball", GRAY
        )
        pyxel.text(
            self.SCREEN_W // 2 - 64, 140, "Catch same colors to COMBO!", YELLOW
        )
        pyxel.text(
            self.SCREEN_W // 2 - 52, 160, "COMBO>=4 = SUPER THROW", ORANGE
        )
        pyxel.text(
            self.SCREEN_W // 2 - 56, 200, "PRESS ENTER TO START", WHITE
        )

    def _draw_game_over(self) -> None:
        pyxel.text(self.SCREEN_W // 2 - 28, 70, "GAME OVER", RED)
        pyxel.text(
            self.SCREEN_W // 2 - 48 + 20, 100,
            f"SCORE: {self.score}", WHITE,
        )
        pyxel.text(
            self.SCREEN_W // 2 - 48 + 20, 112,
            f"MAX COMBO: {self.max_combo}", YELLOW,
        )
        if self.game_timer <= 0:
            pyxel.text(
                self.SCREEN_W // 2 - 30, 130, "TIME UP!", GREEN,
            )
        pyxel.text(
            self.SCREEN_W // 2 - 64, 200, "PRESS ENTER TO RESTART", WHITE,
        )

    def _draw_playing(self) -> None:
        # Court background
        pyxel.rect(
            0, self.COURT_TOP, self.SCREEN_W,
            self.COURT_BOT - self.COURT_TOP, NAVY,
        )
        # Player zone tint
        pyxel.rect(
            0, self.PLAYER_ZONE_TOP, self.SCREEN_W,
            self.COURT_BOT - self.PLAYER_ZONE_TOP, DARK_BLUE,
        )
        # Center line
        for x in range(0, self.SCREEN_W, 10):
            pyxel.rect(x, self.COURT_MID, 5, 1, WHITE)

        # CA danger grid
        for row in range(self.CA_GRID_ROWS):
            for col in range(self.CA_GRID_COLS):
                val = self.danger_grid[row][col]
                if val > 0:
                    px = col * self.CA_CELL_SIZE
                    py = self.COURT_TOP + row * self.CA_CELL_SIZE
                    if val == 3:
                        clr = RED
                    elif val == 2:
                        clr = ORANGE
                    else:
                        clr = YELLOW
                    pyxel.rect(px, py, self.CA_CELL_SIZE, self.CA_CELL_SIZE, clr)

        # Ghost trail (render behind balls)
        for ball in self.balls:
            if ball.life > 0:
                alpha_colors = [GRAY, GRAY, GRAY, GRAY, DARK_BLUE]
                for i in range(min(ball.life, len(alpha_colors))):
                    r = self.BALL_RADIUS - i
                    if r > 0:
                        clr = alpha_colors[min(i, len(alpha_colors) - 1)]
                        pyxel.circ(int(ball.x), int(ball.y), r, clr)

        # Balls
        for ball in self.balls:
            pyxel.circ(int(ball.x), int(ball.y), self.BALL_RADIUS, COLORS[ball.color])
            pyxel.circb(int(ball.x), int(ball.y), self.BALL_RADIUS, WHITE)

        # Opponents
        for opp in self.opponents:
            if opp.hp <= 0:
                continue
            clr = COLORS[opp.color]
            if opp.flash_timer > 0:
                clr = WHITE
            pyxel.circ(int(opp.x), int(opp.y), self.OPPONENT_RADIUS, clr)
            pyxel.circb(int(opp.x), int(opp.y), self.OPPONENT_RADIUS, WHITE)
            # HP bar
            bar_w = 20
            bar_h = 3
            bar_x = int(opp.x) - bar_w // 2
            bar_y = int(opp.y) - self.OPPONENT_RADIUS - 6
            max_hp = self.OPPONENT_HP_BASE + self._difficulty_level
            hp_fraction = opp.hp / max(max_hp, 1)
            pyxel.rect(bar_x, bar_y, bar_w, bar_h, BLACK)
            pyxel.rect(bar_x, bar_y, int(bar_w * hp_fraction), bar_h, RED if hp_fraction < 0.5 else GREEN)

        # Player
        player_clr = COLORS[self.player_color]
        if self.super_mode and self.frame % 6 < 3:
            player_clr = COLORS[self._rng.randint(0, 3)]
        pyxel.circ(int(self.player_x), int(self.player_y), self.PLAYER_RADIUS, player_clr)
        pyxel.circb(int(self.player_x), int(self.player_y), self.PLAYER_RADIUS, WHITE)

        # Held ball indicator
        if self.held_ball_color >= 0:
            bx = int(self.player_x)
            by = int(self.player_y) - self.PLAYER_RADIUS - 5
            pyxel.circ(bx, by, 4, COLORS[self.held_ball_color])
            pyxel.circb(bx, by, 4, WHITE)

        # Particles
        for p in self.particles:
            alpha = p.life / 20.0
            clr = p.color if alpha > 0.5 else GRAY
            pyxel.circ(int(p.x), int(p.y), 2, clr)

        # Floating texts
        for ft in self.floating_texts:
            alpha = ft.life / 30.0
            clr = ft.color if alpha > 0.5 else GRAY
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, clr)

        # HUD
        # Score
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)
        # Combo
        combo_clr = WHITE
        if self.combo >= self.COMBO_FOR_SUPER:
            combo_clr = YELLOW
        pyxel.text(4, 14, f"COMBO: {self.combo}", combo_clr)
        if self.max_combo > 0:
            pyxel.text(4, 24, f"MAX: {self.max_combo}", GRAY)
        # SUPER indicator
        if self.super_mode:
            pyxel.text(
                self.SCREEN_W // 2 - 30, 4,
                f"SUPER! {self.super_timer // 60 + 1}s",
                ORANGE,
            )
        # Timer
        secs = self.game_timer // 60
        timer_clr = WHITE if secs > 10 else (RED if self.frame % 30 < 15 else WHITE)
        pyxel.text(self.SCREEN_W - 52, 4, f"TIME: {secs}s", timer_clr)
        # HEAT bar
        heat_x = self.SCREEN_W - 70
        heat_y = 14
        heat_w = 66
        heat_h = 4
        heat_fraction = self.heat / self.MAX_HEAT
        heat_clr = GREEN if heat_fraction < 0.5 else (YELLOW if heat_fraction < 0.8 else RED)
        pyxel.rectb(heat_x, heat_y, heat_w, heat_h, WHITE)
        pyxel.rect(heat_x, heat_y, int(heat_w * heat_fraction), heat_h, heat_clr)
        pyxel.text(heat_x - 28, heat_y - 1, "HEAT", WHITE)

        # Player zone label
        pyxel.text(self.SCREEN_W // 2 - 12, self.PLAYER_ZONE_TOP + 4, "YOU", GRAY)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    Game()
