"""138_coin_surge — COIN SURGE: Top-down coin pusher arcade game.

Drop colored coins onto a table, trigger COMBO chains with same-color adjacency,
and build toward SUPER DROP (rainbow, 3x score) while managing HEAT risk.

Core fun moment: dropping a coin into a gap that chains same-color coin pushes
for a cascade + SUPER DROP activation.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


# ---------------------------------------------------------------------------
# Color constants
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

COIN_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
NUM_COLORS = len(COIN_COLORS)
SUPER_COLOR_CYCLE: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCREEN_W = 320
SCREEN_H = 240
FPS = 30

# Table
TABLE_LEFT = 20
TABLE_RIGHT = 300
TABLE_TOP = 20
TABLE_BOTTOM = 200
TABLE_W = TABLE_RIGHT - TABLE_LEFT
TABLE_H = TABLE_BOTTOM - TABLE_TOP

# Coin
COIN_RADIUS = 8
COIN_DIAMETER = COIN_RADIUS * 2
GRAVITY = 0.3
MAX_SPEED = 5.0
DAMPING = 0.7
SETTLE_FRAMES = 60
DROP_COOLDOWN = 15

# Game
GAME_DURATION_SEC = 90
HEAT_MAX = 100.0
HEAT_PER_DIFF = 15.0
HEAT_DECAY = 0.02
HEAT_DECAY_ON_COMBO = 5.0
COMBO_SUPER_THRESHOLD = 4
SUPER_DURATION = 5 * FPS  # 5 seconds
OVERHEAT_DURATION = 5 * FPS
OVERHEAT_JITTER = 20
SCORE_PER_COIN = 10


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
class Coin:
    x: float
    y: float
    color: int  # 0-3 index
    vx: float = 0.0
    vy: float = 0.0
    settled: bool = False
    settle_counter: int = 0

    @property
    def pyxel_color(self) -> int:
        return COIN_COLORS[self.color]


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


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    """COIN SURGE — coin pusher arcade game."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="COIN SURGE", fps=FPS, display_scale=2)
        self._rng: random.Random = random.Random()
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.coins: list[Coin] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.current_color_idx: int = 0
        self.drop_x: float = TABLE_LEFT + TABLE_W / 2
        self.super_timer: int = 0
        self.overheat_timer: int = 0
        self.game_timer: int = GAME_DURATION_SEC * FPS
        self.drop_cooldown: int = 0
        self.shake_frames: int = 0
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self._rng = random.Random()
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.coins.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.current_color_idx = 0
        self.drop_x = TABLE_LEFT + TABLE_W / 2
        self.super_timer = 0
        self.overheat_timer = 0
        self.game_timer = GAME_DURATION_SEC * FPS
        self.drop_cooldown = 0
        self.shake_frames = 0

    # -----------------------------------------------------------------------
    # Phase helpers
    # -----------------------------------------------------------------------
    def start_playing(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.coins.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.current_color_idx = 0
        self.drop_x = TABLE_LEFT + TABLE_W / 2
        self.super_timer = 0
        self.overheat_timer = 0
        self.game_timer = GAME_DURATION_SEC * FPS
        self.drop_cooldown = 0
        self.shake_frames = 0
        # Seed some initial coins so the table isn't empty
        self._seed_initial_coins()

    def _seed_initial_coins(self) -> None:
        """Place a few starting coins to give the table life."""
        rng = self._rng
        for _ in range(10):
            x = rng.uniform(TABLE_LEFT + COIN_RADIUS, TABLE_RIGHT - COIN_RADIUS)
            y = rng.uniform(TABLE_BOTTOM - 60, TABLE_BOTTOM - COIN_RADIUS)
            col = rng.randint(0, NUM_COLORS - 1)
            c = Coin(x=x, y=y, color=col)
            # Settle them
            self._settle_single_coin(c)
            self.coins.append(c)

    def _settle_single_coin(self, c: Coin) -> None:
        """Run physics on a single coin until it settles against existing coins."""
        for _ in range(200):
            all_others = [o for o in self.coins if o is not c]
            c.vy += GRAVITY
            c.vy = min(c.vy, MAX_SPEED)
            c.y += c.vy
            # Clamp bottom
            if c.y + COIN_RADIUS >= TABLE_BOTTOM:
                c.y = TABLE_BOTTOM - COIN_RADIUS
                c.vy = 0.0
            # Resolve against existing coins
            for other in all_others:
                self._resolve_coin_collision(c, other)
            # Wall clamping
            c.x = max(TABLE_LEFT + COIN_RADIUS, min(TABLE_RIGHT - COIN_RADIUS, c.x))
            c.vy *= DAMPING
            if abs(c.vy) < 0.05:
                break

    # -----------------------------------------------------------------------
    # Update (called by pyxel)
    # -----------------------------------------------------------------------
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_RETURN):
            self.start_playing()

    def _update_playing(self) -> None:
        # Timer
        self.game_timer -= 1

        # Drop cooldown
        if self.drop_cooldown > 0:
            self.drop_cooldown -= 1

        # Mouse drop position
        jitter = 0
        if self.overheat_timer > 0:
            jitter = self._rng.randint(-OVERHEAT_JITTER, OVERHEAT_JITTER)
        self.drop_x = pyxel.mouse_x + jitter
        self.drop_x = max(TABLE_LEFT + COIN_RADIUS, min(TABLE_RIGHT - COIN_RADIUS, self.drop_x))

        # Drop coin on click
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and self.drop_cooldown <= 0:
            self._drop_coin(self.drop_x, self.current_color_idx)
            self.drop_cooldown = DROP_COOLDOWN
            self._advance_next_color()

        # Physics
        self._update_physics()

        # Edge check (coins pushed off bottom)
        scored = self._check_edge_coins()
        if scored:
            self._handle_scored_coins(scored)

        # Super timer
        self._update_super_timer()

        # Overheat timer
        self._update_overheat_timer()

        # Heat
        self._update_heat()

        # Particles
        self._update_particles()

        # Floating texts
        self._update_floating_texts()

        # Shake
        if self.shake_frames > 0:
            self.shake_frames -= 1

        # Game over conditions
        if self.game_timer <= 0:
            self.game_timer = 0
            self.phase = Phase.GAME_OVER

    def _update_game_over(self) -> None:
        self._update_particles()
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_RETURN):
            self.start_playing()

    # -----------------------------------------------------------------------
    # Core logic (testable, no pyxel input)
    # -----------------------------------------------------------------------
    def _drop_coin(self, x: float, color_idx: int) -> None:
        c = Coin(x=x, y=TABLE_TOP + COIN_RADIUS, color=color_idx)
        self.coins.append(c)
        self._spawn_drop_particles(c.x, c.y, c.pyxel_color)
        self._check_adjacent_combo(c)

    def _is_position_blocked(self, x: float, y: float) -> bool:
        for other in self.coins:
            dx = x - other.x
            dy = y - other.y
            dist = math.hypot(dx, dy)
            if dist < COIN_DIAMETER * 0.9:
                return True
        return False

    def _find_drop_y(self, x: float) -> float:
        """Find the highest y where a coin can be placed at x."""
        best_y = TABLE_TOP + COIN_RADIUS
        for other in self.coins:
            if abs(x - other.x) < COIN_DIAMETER:
                candidate = other.y - COIN_DIAMETER
                if candidate > best_y:
                    best_y = candidate
        return max(best_y, TABLE_TOP + COIN_RADIUS)

    def _update_physics(self) -> None:
        # Gravity
        for c in self.coins:
            if not c.settled:
                c.vy += GRAVITY
                c.vy = min(c.vy, MAX_SPEED)
                c.x += c.vx
                c.y += c.vy

        # Coin-coin collision resolution (multiple passes)
        for _ in range(3):
            for i in range(len(self.coins)):
                for j in range(i + 1, len(self.coins)):
                    self._resolve_coin_collision(self.coins[i], self.coins[j])

        # Wall clamping & bottom stop
        for c in self.coins:
            c.x = max(TABLE_LEFT + COIN_RADIUS, min(TABLE_RIGHT - COIN_RADIUS, c.x))
            if c.y + COIN_RADIUS >= TABLE_BOTTOM:
                c.y = TABLE_BOTTOM - COIN_RADIUS
                c.vy = 0.0
                if c.y + COIN_RADIUS > TABLE_BOTTOM:
                    # Prevent passing through bottom
                    pass
            if c.y - COIN_RADIUS < TABLE_TOP:
                c.y = TABLE_TOP + COIN_RADIUS
                c.vy = abs(c.vy) * 0.5

        # Settle check
        for c in self.coins:
            if abs(c.vx) < 0.1 and abs(c.vy) < 0.1:
                c.settle_counter += 1
            else:
                c.settle_counter = 0
            if c.settle_counter >= SETTLE_FRAMES and c.y + COIN_RADIUS >= TABLE_BOTTOM - 2:
                c.settled = True
                c.vx = 0.0
                c.vy = 0.0
            elif c.settle_counter >= SETTLE_FRAMES * 2:
                # Long-settle coins that aren't at bottom
                c.settled = True
                c.vx = 0.0
                c.vy = 0.0

        # Velocity damping
        for c in self.coins:
            if not c.settled:
                c.vx *= DAMPING
                c.vy *= DAMPING

    def _resolve_coin_collision(self, c1: Coin, c2: Coin) -> None:
        dx = c2.x - c1.x
        dy = c2.y - c1.y
        dist = math.hypot(dx, dy)
        min_dist = COIN_DIAMETER

        if dist >= min_dist or dist == 0:
            return

        # Push apart
        overlap = min_dist - dist
        if dist < 0.001:
            nx = 1.0
            ny = 0.0
        else:
            nx = dx / dist
            ny = dy / dist

        push = overlap * 0.5
        c1.x -= nx * push
        c1.y -= ny * push
        c2.x += nx * push
        c2.y += ny * push

        # Velocity exchange (simplified elastic)
        rel_vx = c2.vx - c1.vx
        rel_vy = c2.vy - c1.vy
        rel_vn = rel_vx * nx + rel_vy * ny

        if rel_vn < 0:
            impulse = rel_vn * 0.5
            c1.vx += nx * impulse
            c1.vy += ny * impulse
            c2.vx -= nx * impulse
            c2.vy -= ny * impulse

        # Wake settled coins
        if c1.settled and overlap > 1.0:
            c1.settled = False
            c1.settle_counter = 0
        if c2.settled and overlap > 1.0:
            c2.settled = False
            c2.settle_counter = 0

    def _check_edge_coins(self) -> list[Coin]:
        """Find coins pushed past bottom edge. Returns list of removed coins."""
        scored: list[Coin] = []
        survivors: list[Coin] = []
        for c in self.coins:
            if c.y + COIN_RADIUS >= TABLE_BOTTOM and c.vy > 0.5:
                # Coin is actively being pushed through bottom
                scored.append(c)
            elif c.y - COIN_RADIUS > TABLE_BOTTOM + COIN_RADIUS:
                # Fully off screen
                scored.append(c)
            else:
                survivors.append(c)
        self.coins = survivors
        return scored

    def _handle_scored_coins(self, coins: list[Coin]) -> None:
        """Award score for pushed-off coins."""
        for c in coins:
            mult = 3 if self.super_timer > 0 else 1
            combo_bonus = int(self.combo * 0.5)
            points = (SCORE_PER_COIN + combo_bonus) * mult
            self.score += points
            self._spawn_score_particles(c.x, TABLE_BOTTOM, c.pyxel_color)
            self.floating_texts.append(FloatingText(
                x=c.x, y=TABLE_BOTTOM - 10,
                text=f"+{points}",
                life=30,
                color=WHITE,
            ))
            # Combo scoring also reduces heat
            if self.combo > 0:
                self.heat = max(0.0, self.heat - HEAT_DECAY_ON_COMBO)

    def _check_adjacent_combo(self, dropped: Coin) -> None:
        """Check adjacent coins for same/diff color, update combo/heat."""
        same_count = 0
        diff_count = 0

        for other in self.coins:
            if other is dropped:
                continue
            dx = dropped.x - other.x
            dy = dropped.y - other.y
            dist = math.hypot(dx, dy)
            if dist < COIN_DIAMETER * 1.5:
                if other.color == dropped.color:
                    same_count += 1
                else:
                    diff_count += 1

        if same_count > 0:
            old_combo = self.combo
            self.combo += same_count
            self.max_combo = max(self.max_combo, self.combo)
            self.heat = max(0.0, self.heat - HEAT_DECAY_ON_COMBO * same_count)
            # Combo particles
            self._spawn_combo_particles(dropped.x, dropped.y, dropped.pyxel_color, same_count)
            self.floating_texts.append(FloatingText(
                x=dropped.x, y=dropped.y - 12,
                text=f"COMBO x{self.combo}",
                life=40,
                color=YELLOW,
            ))
            # Check SUPER DROP trigger
            if old_combo < COMBO_SUPER_THRESHOLD and self.combo >= COMBO_SUPER_THRESHOLD:
                self._activate_super()

        if diff_count > 0:
            self.combo = 0
            self.heat += HEAT_PER_DIFF * diff_count
            self._spawn_heat_particles(dropped.x, dropped.y)
            self.floating_texts.append(FloatingText(
                x=dropped.x, y=dropped.y - 12,
                text="BROKEN",
                life=30,
                color=GRAY,
            ))

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self.shake_frames = 20
        self._spawn_super_particles()
        self.floating_texts.append(FloatingText(
            x=TABLE_LEFT + TABLE_W / 2, y=TABLE_TOP + 30,
            text="SUPER DROP!",
            life=60,
            color=YELLOW,
        ))

    def _update_super_timer(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1

    def _update_overheat_timer(self) -> None:
        if self.overheat_timer > 0:
            self.overheat_timer -= 1

    def _update_heat(self) -> None:
        # Clamp
        self.heat = min(self.heat, HEAT_MAX)
        self.heat = max(self.heat, 0.0)

        # Check OVERHEAT threshold (before decay, to catch exact threshold)
        if self.heat >= HEAT_MAX:
            self.overheat_timer = OVERHEAT_DURATION
            self.shake_frames = 15
            self.floating_texts.append(FloatingText(
                x=TABLE_LEFT + TABLE_W / 2, y=TABLE_TOP + 30,
                text="OVERHEAT!",
                life=40,
                color=ORANGE,
            ))
            self.particles.extend([
                Particle(
                    x=self._rng.uniform(TABLE_LEFT, TABLE_RIGHT),
                    y=self._rng.uniform(TABLE_TOP, TABLE_BOTTOM),
                    vx=self._rng.uniform(-2, 2),
                    vy=self._rng.uniform(-2, 2),
                    life=15,
                    color=ORANGE,
                )
                for _ in range(15)
            ])

        # Decay heat over time
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    # -----------------------------------------------------------------------
    # Next color
    # -----------------------------------------------------------------------
    def _advance_next_color(self) -> None:
        # 25% chance same color, otherwise cycle
        if self._rng.random() < 0.25:
            return  # stay on same color
        self.current_color_idx = (self.current_color_idx + 1) % NUM_COLORS

    # -----------------------------------------------------------------------
    # Particle spawners
    # -----------------------------------------------------------------------
    def _spawn_drop_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(4):
            self.particles.append(Particle(
                x=x, y=y,
                vx=self._rng.uniform(-1.0, 1.0),
                vy=self._rng.uniform(-0.5, 0.5),
                life=self._rng.randint(8, 15),
                color=color,
            ))

    def _spawn_score_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(6):
            self.particles.append(Particle(
                x=x, y=y,
                vx=self._rng.uniform(-2.0, 2.0),
                vy=self._rng.uniform(-2.5, -0.5),
                life=self._rng.randint(10, 20),
                color=color,
            ))

    def _spawn_combo_particles(self, x: float, y: float, color: int, count: int) -> None:
        n = min(count * 2, 8)
        for _ in range(n):
            self.particles.append(Particle(
                x=x, y=y,
                vx=self._rng.uniform(-1.5, 1.5),
                vy=self._rng.uniform(-1.5, 1.5),
                life=self._rng.randint(8, 12),
                color=color,
            ))

    def _spawn_heat_particles(self, x: float, y: float) -> None:
        for _ in range(3):
            self.particles.append(Particle(
                x=x, y=y,
                vx=self._rng.uniform(-1.0, 1.0),
                vy=self._rng.uniform(-1.0, 1.0),
                life=self._rng.randint(6, 10),
                color=ORANGE,
            ))

    def _spawn_super_particles(self) -> None:
        cx = TABLE_LEFT + TABLE_W / 2
        cy = TABLE_TOP + TABLE_H / 2
        for _ in range(20):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 4.0)
            col = SUPER_COLOR_CYCLE[self._rng.randint(0, 3)]
            self.particles.append(Particle(
                x=cx, y=cy,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=self._rng.randint(15, 25),
                color=col,
            ))

    # -----------------------------------------------------------------------
    # Particle update
    # -----------------------------------------------------------------------
    def _update_particles(self) -> None:
        survivors: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1  # particle gravity
            p.life -= 1
            if p.life > 0:
                survivors.append(p)
        self.particles = survivors

    # -----------------------------------------------------------------------
    # Floating text update
    # -----------------------------------------------------------------------
    def _update_floating_texts(self) -> None:
        survivors: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= 0.5  # float upward
            ft.life -= 1
            if ft.life > 0:
                survivors.append(ft)
        self.floating_texts = survivors

    # -----------------------------------------------------------------------
    # Drawing
    # -----------------------------------------------------------------------
    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_playing()  # show table state behind overlay
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = "COIN SURGE"
        tw = len(title) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 80, title, YELLOW)

        sub = "CLICK TO START"
        sw = len(sub) * 4
        pyxel.text(SCREEN_W // 2 - sw // 2, 120, sub, WHITE)

        hint1 = "Mouse: aim drop position"
        hw1 = len(hint1) * 4
        pyxel.text(SCREEN_W // 2 - hw1 // 2, 150, hint1, GRAY)

        hint2 = "Click: drop coin"
        hw2 = len(hint2) * 4
        pyxel.text(SCREEN_W // 2 - hw2 // 2, 160, hint2, GRAY)

        hint3 = "Same color adjacent = COMBO"
        hw3 = len(hint3) * 4
        pyxel.text(SCREEN_W // 2 - hw3 // 2, 178, hint3, GRAY)

        hint4 = "COMBO 4 = SUPER DROP (3x)"
        hw4 = len(hint4) * 4
        pyxel.text(SCREEN_W // 2 - hw4 // 2, 188, hint4, GRAY)

    def _draw_playing(self) -> None:
        # Camera shake
        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0:
            shake_x = self._rng.randint(-2, 2)
            shake_y = self._rng.randint(-2, 2)
        pyxel.camera(shake_x, shake_y)

        # Table background
        pyxel.rect(TABLE_LEFT, TABLE_TOP, TABLE_W, TABLE_H, NAVY)

        # Bottom push-off zone highlight
        push_zone_y = TABLE_BOTTOM - 4
        if self.super_timer > 0:
            # Rainbow bottom during super
            rainbow_col = SUPER_COLOR_CYCLE[(pyxel.frame_count // 4) % 4]
            pyxel.rect(TABLE_LEFT, push_zone_y, TABLE_W, 6, rainbow_col)
        else:
            pyxel.rect(TABLE_LEFT, push_zone_y, TABLE_W, 4, DARK_BLUE)

        # Table border
        pyxel.rectb(TABLE_LEFT - 1, TABLE_TOP - 1, TABLE_W + 2, TABLE_H + 2, GRAY)

        # Draw coins
        super_frame = pyxel.frame_count
        for c in self.coins:
            col = c.pyxel_color
            # Super mode: rainbow flash
            if self.super_timer > 0:
                col = SUPER_COLOR_CYCLE[(super_frame // 4 + c.color) % 4]
            px = int(c.x)
            py = int(c.y)
            # Outline
            pyxel.circb(px, py, COIN_RADIUS, WHITE if col != WHITE else BLACK)
            # Fill
            pyxel.circ(px, py, COIN_RADIUS - 1, col)
            # Small highlight dot
            pyxel.circ(px - 2, py - 2, 2, WHITE)

        # Drop preview line
        if self.drop_cooldown <= 0:
            preview_color = COIN_COLORS[self.current_color_idx]
            preview_y = self._find_drop_y(self.drop_x) if self.coins else TABLE_TOP + COIN_RADIUS
            # Vertical guide line
            pyxel.line(int(self.drop_x), TABLE_TOP, int(self.drop_x), int(preview_y), preview_color)
            # Ghost coin at drop position
            ghost_x = int(self.drop_x)
            ghost_y = int(preview_y)
            pyxel.circb(ghost_x, ghost_y, COIN_RADIUS, preview_color)

        # Overheat indicator
        if self.overheat_timer > 0:
            # Red border pulse
            pulse = int(abs(math.sin(pyxel.frame_count * 0.3)) * 3)
            pyxel.rectb(
                TABLE_LEFT - 2 - pulse, TABLE_TOP - 2 - pulse,
                TABLE_W + 4 + pulse * 2, TABLE_H + 4 + pulse * 2, RED,
            )

        # Draw particles (camera shake already applied via pyxel.camera)
        for p in self.particles:
            px = int(p.x)
            py = int(p.y)
            if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
                if p.life > 5:
                    pyxel.pset(px, py, p.color)
                else:
                    pyxel.pset(px, py, GRAY)

        # Draw floating texts
        for ft in self.floating_texts:
            tx = int(ft.x) - len(ft.text) * 2
            if ft.life > 20:
                pyxel.text(tx, int(ft.y), ft.text, ft.color)
            elif ft.life > 0:
                pyxel.text(tx, int(ft.y), ft.text, GRAY)

        # Reset camera
        pyxel.camera(0, 0)

        # HUD
        self._draw_hud()

    def _draw_hud(self) -> None:
        # Top bar background
        pyxel.rect(0, 0, SCREEN_W, 19, BLACK)
        pyxel.line(0, 19, SCREEN_W, 19, GRAY)

        # Score (top-left)
        pyxel.text(3, 3, f"SCORE:{self.score}", WHITE)

        # Combo (top-center)
        combo_col = YELLOW if self.combo >= COMBO_SUPER_THRESHOLD else WHITE
        combo_text = f"COMBO:{self.combo}"
        ctw = len(combo_text) * 4
        pyxel.text(SCREEN_W // 2 - ctw // 2, 3, combo_text, combo_col)

        if self.max_combo > 0:
            mx_text = f"MAX:{self.max_combo}"
            mtw = len(mx_text) * 4
            pyxel.text(SCREEN_W // 2 - mtw // 2, 11, mx_text, GRAY)

        # Timer (top-right area)
        seconds = self.game_timer // FPS
        timer_text = f"TIME:{seconds}"
        pyxel.text(SCREEN_W - 60, 3, timer_text, WHITE if seconds > 10 else RED)

        # HEAT bar (below timer)
        heat_bar_x = SCREEN_W - 62
        heat_bar_w = 56
        heat_bar_y = 12
        heat_bar_h = 5
        pyxel.rectb(heat_bar_x, heat_bar_y, heat_bar_w, heat_bar_h, GRAY)
        heat_fill = int(self.heat / HEAT_MAX * (heat_bar_w - 1))
        heat_col = RED if self.heat >= 80 else ORANGE if self.heat >= 50 else YELLOW
        if heat_fill > 0:
            pyxel.rect(heat_bar_x + 1, heat_bar_y + 1, heat_fill, heat_bar_h - 2, heat_col)

        # HEAT label
        pyxel.text(heat_bar_x - 20, heat_bar_y - 1, "HEAT", GRAY)

        # Super timer indicator
        if self.super_timer > 0:
            s_text = f"SUPER:{self.super_timer // FPS + 1}s"
            pyxel.text(3, 11, s_text, YELLOW)

        # Current coin color indicator (next to drop preview area)
        curr_col = COIN_COLORS[self.current_color_idx]
        pyxel.rect(TABLE_LEFT + 2, 3, 10, 10, curr_col)
        pyxel.rectb(TABLE_LEFT + 1, 2, 12, 12, WHITE)
        pyxel.text(TABLE_LEFT + 15, 4, "NEXT", GRAY)

    def _draw_game_over(self) -> None:
        # Semi-transparent overlay
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, BLACK)

        go_text = "GAME OVER"
        gtw = len(go_text) * 4
        pyxel.text(SCREEN_W // 2 - gtw // 2, 80, go_text, RED)

        score_text = f"SCORE: {self.score}"
        stw = len(score_text) * 4
        pyxel.text(SCREEN_W // 2 - stw // 2, 105, score_text, WHITE)

        combo_text = f"MAX COMBO: {self.max_combo}"
        ctw = len(combo_text) * 4
        pyxel.text(SCREEN_W // 2 - ctw // 2, 120, combo_text, YELLOW)

        retry_text = "CLICK TO RETRY"
        rtw = len(retry_text) * 4
        pyxel.text(SCREEN_W // 2 - rtw // 2, 150, retry_text, GRAY)


if __name__ == "__main__":
    Game()
