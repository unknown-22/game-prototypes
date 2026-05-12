"""ORE SERPENT — Snake-like mining roguelite prototype.

Core mechanic: Navigate a growing drill-serpent through mineral caverns.
Collect same-color ores consecutively to build a COMBO multiplier.
Your body (the drill's trail) blocks movement — longer body = more risk.

Reinterpreted from game_idea_factory idea #1 (score 32.2):
  Original: Vampire Survivors-like auto-shooter / Space mining
  Hook: "log/replay as assets (past actions become next cards)"
  Reinterpretation: Snake body = log of past positions constraining future movement
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel

# ── Config ──
SCREEN_W = 320
SCREEN_H = 240
GRID = 16
COLS = SCREEN_W // GRID  # 20
ROWS = SCREEN_H // GRID  # 15

TICK_BASE = 0.16  # seconds per tick at start
TICK_FAST = 0.07  # fastest tick (at high score)
GAME_TIME = 60.0  # seconds
TARGET_SCORE = 500
MAX_ORES = 6
ORE_SPAWN_INTERVAL = 3.0  # seconds
INITIAL_LENGTH = 3
SCORE_PER_ORE = 10


# ── Enums ──
class Direction(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()

    @property
    def dx(self) -> int:
        _map: dict[Direction, int] = {
            Direction.UP: 0, Direction.DOWN: 0,
            Direction.LEFT: -1, Direction.RIGHT: 1,
        }
        return _map[self]

    @property
    def dy(self) -> int:
        _map: dict[Direction, int] = {
            Direction.UP: -1, Direction.DOWN: 1,
            Direction.LEFT: 0, Direction.RIGHT: 0,
        }
        return _map[self]

    def opposite(self) -> Direction:
        _map: dict[Direction, Direction] = {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT,
        }
        return _map[self]


class OreType(Enum):
    RUBY = auto()      # red
    SAPPHIRE = auto()  # blue
    GOLD = auto()      # yellow
    EMERALD = auto()   # green

    @property
    def color(self) -> int:
        _map: dict[OreType, int] = {
            OreType.RUBY: pyxel.COLOR_RED,
            OreType.SAPPHIRE: pyxel.COLOR_CYAN,
            OreType.GOLD: pyxel.COLOR_YELLOW,
            OreType.EMERALD: pyxel.COLOR_LIME,
        }
        return _map[self]

    @property
    def name(self) -> str:
        _map: dict[OreType, str] = {
            OreType.RUBY: "RUBY",
            OreType.SAPPHIRE: "SAPH",
            OreType.GOLD: "GOLD",
            OreType.EMERALD: "EMRD",
        }
        return _map[self]

    @property
    def abbr(self) -> str:
        _map: dict[OreType, str] = {
            OreType.RUBY: "R",
            OreType.SAPPHIRE: "S",
            OreType.GOLD: "G",
            OreType.EMERALD: "E",
        }
        return _map[self]


class Phase(Enum):
    PLAYING = auto()
    VICTORY = auto()
    DEFEAT = auto()


# ── Data classes ──
@dataclass
class Ore:
    x: int
    y: int
    ore_type: OreType
    spawn_timer: float = 0.0  # for fade-in animation


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    color: int
    size: float = 1.0


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: float
    color: int
    vy: float = -0.5


# ── Game ──
class OreSerpent:
    """Snake-like mining game. Grid-based movement, combo system."""

    GRID: ClassVar[int] = GRID
    COLS: ClassVar[int] = COLS
    ROWS: ClassVar[int] = ROWS

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="ORE SERPENT", fps=60, display_scale=2)
        self.reset()
        pyxel.run(self._update, self._draw)

    def reset(self) -> None:
        """Initialize or reset all game state."""
        # Snake state
        start_x = COLS // 2
        start_y = ROWS // 2
        self.snake: list[tuple[int, int]] = []
        for i in range(INITIAL_LENGTH):
            self.snake.append((start_x - i, start_y))
        self.direction = Direction.RIGHT
        self.next_direction = Direction.RIGHT
        self.growing = 0  # segments to add

        # Ore state
        self.ores: list[Ore] = []
        self.ore_spawn_cooldown = ORE_SPAWN_INTERVAL
        self._spawn_initial_ores()

        # Score / combo
        self.score = 0
        self.combo = 0  # consecutive same-color count
        self.last_ore_type: OreType | None = None
        self.max_combo = 0

        # Timer
        self.tick_timer = 0.0
        self.tick_interval = TICK_BASE
        self.game_timer = GAME_TIME

        # Phase
        self.phase = Phase.PLAYING
        self.phase_timer = 0.0  # for end-screen delay

        # Effects
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shake_timer = 0.0
        self.shake_intensity = 0.0

        # Input lock (prevent double-move in one tick)
        self._moved_this_tick = False

    def _spawn_initial_ores(self) -> None:
        """Spawn initial set of ores on empty cells."""
        for _ in range(3):
            self._spawn_ore()

    def _spawn_ore(self) -> OreType | None:
        """Spawn one random ore on an empty cell. Returns ore type or None."""
        if len(self.ores) >= MAX_ORES:
            return None

        snake_set = set(self.snake)
        ore_set = {(o.x, o.y) for o in self.ores}
        occupied = snake_set | ore_set

        # Try to find empty cell (not on snake, not on existing ore)
        attempts = 0
        while attempts < 50:
            x = random.randint(1, COLS - 2)  # avoid walls
            y = random.randint(1, ROWS - 2)
            if (x, y) not in occupied:
                ore_type = random.choice(list(OreType))
                self.ores.append(Ore(x=x, y=y, ore_type=ore_type))
                return ore_type
            attempts += 1
        return None

    # ── Update ──

    def _update(self) -> None:
        """Main update loop (called every frame)."""
        if self.phase == Phase.PLAYING:
            self._update_input()
            self._update_tick()
            self._update_ore_spawn()
        elif self.phase in (Phase.VICTORY, Phase.DEFEAT):
            self._update_end_screen()

        self._update_particles()
        self._update_floating_texts()

    def _update_end_screen(self) -> None:
        """Handle end screen: wait then allow restart."""
        self.phase_timer += 1.0 / 60.0
        if self.phase_timer > 1.0:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()

    def _update_input(self) -> None:
        """Buffer directional input for next tick."""
        if pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.KEY_W):
            if self.direction != Direction.DOWN:
                self.next_direction = Direction.UP
        elif pyxel.btnp(pyxel.KEY_DOWN) or pyxel.btnp(pyxel.KEY_S):
            if self.direction != Direction.UP:
                self.next_direction = Direction.DOWN
        elif pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A):
            if self.direction != Direction.RIGHT:
                self.next_direction = Direction.LEFT
        elif pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D):
            if self.direction != Direction.LEFT:
                self.next_direction = Direction.RIGHT

    def _update_tick(self) -> None:
        """Accumulate time and trigger snake movement on tick."""
        dt = 1.0 / 60.0
        self.game_timer -= dt
        if self.game_timer <= 0:
            self.game_timer = 0
            self.phase = Phase.DEFEAT
            self.phase_timer = 0.0
            return

        self.tick_timer += dt
        tick_needed = self.tick_interval
        if self.tick_timer >= tick_needed:
            self.tick_timer -= tick_needed
            self._moved_this_tick = False
            self._move_snake()
            # Update tick speed based on score
            progress = min(self.score / TARGET_SCORE, 1.0)
            self.tick_interval = TICK_BASE - (TICK_BASE - TICK_FAST) * progress

    def _move_snake(self) -> None:
        """Execute one grid movement tick."""
        if self._moved_this_tick:
            return
        self._moved_this_tick = True

        self.direction = self.next_direction
        head_x, head_y = self.snake[0]
        new_head = (head_x + self.direction.dx, head_y + self.direction.dy)
        nhx, nhy = new_head

        # Collision: walls
        if nhx < 0 or nhx >= COLS or nhy < 0 or nhy >= ROWS:
            self._on_death()
            return

        # Collision: self (skip tail if not growing — tail will move away)
        tail_check = self.snake[:-1] if self.growing == 0 else self.snake
        if new_head in tail_check:
            self._on_death()
            return

        # Move: insert new head
        self.snake.insert(0, new_head)

        # Check ore collection
        ore_eaten = self._check_ore_collection(nhx, nhy)
        if ore_eaten:
            self.growing += 1

        # Remove tail or grow
        if self.growing > 0:
            self.growing -= 1
        else:
            self.snake.pop()

        # Check victory
        if self.score >= TARGET_SCORE:
            self.phase = Phase.VICTORY
            self.phase_timer = 0.0

    def _check_ore_collection(self, x: int, y: int) -> bool:
        """Check if snake head is on an ore. If so, collect it. Returns True if ore eaten."""
        for i, ore in enumerate(self.ores):
            if ore.x == x and ore.y == y:
                ore_type = ore.ore_type

                # Combo logic
                if self.last_ore_type == ore_type:
                    self.combo += 1
                else:
                    self.combo = 1
                self.last_ore_type = ore_type

                if self.combo > self.max_combo:
                    self.max_combo = self.combo

                # Score calculation
                multiplier = min(self.combo, 8)  # cap at x8
                gained = SCORE_PER_ORE * multiplier
                self.score += gained

                # Effects
                self._spawn_collect_particles(x, y, ore_type)
                self._spawn_floating_text(x, y, f"+{gained}", ore_type.color)
                if self.combo >= 3:
                    self._spawn_floating_text(
                        x, y - 0.5, f"x{multiplier}!", pyxel.COLOR_ORANGE
                    )
                    self.shake_timer = 0.15
                    self.shake_intensity = min(2 + self.combo, 6)

                # Remove ore
                self.ores.pop(i)
                return True
        return False

    def _on_death(self) -> None:
        """Handle death: screen shake, particles, defeat phase."""
        self.phase = Phase.DEFEAT
        self.phase_timer = 0.0
        self.shake_timer = 0.3
        self.shake_intensity = 5.0
        head_x, head_y = self.snake[0]
        self._spawn_death_particles(head_x, head_y)

    def _update_ore_spawn(self) -> None:
        """Periodically spawn new ores."""
        self.ore_spawn_cooldown -= 1.0 / 60.0
        if self.ore_spawn_cooldown <= 0:
            self.ore_spawn_cooldown = ORE_SPAWN_INTERVAL
            self._spawn_ore()

    # ── Particle systems ──

    def _spawn_collect_particles(self, gx: int, gy: int, ore_type: OreType) -> None:
        """Spawn particles when ore is collected."""
        px = gx * GRID + GRID // 2
        py = gy * GRID + GRID // 2
        color = ore_type.color
        for _ in range(6):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(0.5, 2.0)
            self.particles.append(Particle(
                x=float(px), y=float(py),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=0.5, color=color, size=2.0,
            ))

    def _spawn_death_particles(self, gx: int, gy: int) -> None:
        """Spawn explosion particles on death."""
        px = gx * GRID + GRID // 2
        py = gy * GRID + GRID // 2
        for _ in range(20):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.0, 4.0)
            color = random.choice([
                pyxel.COLOR_RED, pyxel.COLOR_ORANGE, pyxel.COLOR_YELLOW, pyxel.COLOR_WHITE,
            ])
            self.particles.append(Particle(
                x=float(px), y=float(py),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=random.uniform(0.3, 0.8),
                color=color,
                size=random.uniform(1.5, 3.0),
            ))

    def _spawn_floating_text(self, gx: int, gy: float, text: str, color: int) -> None:
        """Spawn floating score text."""
        px = gx * GRID + GRID // 2
        py = gy * GRID + GRID // 2
        self.floating_texts.append(FloatingText(
            x=float(px), y=float(py),
            text=text, life=0.8, color=color,
        ))

    def _update_particles(self) -> None:
        """Update particle positions and lifetimes."""
        dt = 1.0 / 60.0
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= dt
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def _update_floating_texts(self) -> None:
        """Update floating text positions and lifetimes."""
        dt = 1.0 / 60.0
        alive: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= dt
            if ft.life > 0:
                alive.append(ft)
        self.floating_texts = alive

    # ── Draw ──

    def _draw(self) -> None:
        """Main draw loop."""
        pyxel.cls(pyxel.COLOR_BLACK)

        # Screen shake
        shake_x = 0.0
        shake_y = 0.0
        if self.shake_timer > 0:
            self.shake_timer -= 1.0 / 60.0
            shake_x = random.uniform(-self.shake_intensity, self.shake_intensity)
            shake_y = random.uniform(-self.shake_intensity, self.shake_intensity)
            if self.shake_timer <= 0:
                self.shake_intensity = 0.0

        pyxel.camera(int(shake_x), int(shake_y))

        self._draw_grid()
        self._draw_ores()
        self._draw_snake()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_ui()

        pyxel.camera(0, 0)  # Reset camera for UI overlay

        if self.phase == Phase.VICTORY:
            self._draw_overlay("VICTORY!", pyxel.COLOR_LIME, f"Score: {self.score}")
        elif self.phase == Phase.DEFEAT:
            self._draw_overlay("DEFEAT", pyxel.COLOR_RED, f"Score: {self.score}")

    def _draw_grid(self) -> None:
        """Draw subtle grid lines."""
        for x in range(0, SCREEN_W, GRID):
            pyxel.line(x, 0, x, SCREEN_H, pyxel.COLOR_NAVY)
        for y in range(0, SCREEN_H, GRID):
            pyxel.line(0, y, SCREEN_W, y, pyxel.COLOR_NAVY)

    def _draw_snake(self) -> None:
        """Draw snake body segments."""
        if not self.snake:
            return

        for i, (sx, sy) in enumerate(self.snake):
            px = sx * GRID + 1
            py = sy * GRID + 1
            sz = GRID - 2

            if i == 0:
                # Head: bright white with direction indicator
                pyxel.rect(px, py, sz, sz, pyxel.COLOR_WHITE)
                # Eyes / direction indicator
                eye_color = pyxel.COLOR_BLACK
                cx = px + sz // 2
                cy = py + sz // 2
                ex = self.direction.dx * 3
                ey = self.direction.dy * 3
                pyxel.rect(cx + ex - 1, cy + ey - 1, 3, 3, eye_color)
            elif i < len(self.snake) - 1:
                # Body: gradient from light gray to dark
                ratio = i / max(len(self.snake), 1)
                if ratio < 0.33:
                    color = pyxel.COLOR_GRAY
                elif ratio < 0.66:
                    color = pyxel.COLOR_LIGHT_BLUE
                else:
                    color = pyxel.COLOR_NAVY
                pyxel.rect(px, py, sz, sz, color)
            else:
                # Tail: darkest, slightly smaller
                pyxel.rect(px + 1, py + 1, sz - 2, sz - 2, pyxel.COLOR_NAVY)

    def _draw_ores(self) -> None:
        """Draw ore deposits with pulsing animation."""
        for ore in self.ores:
            px = ore.x * GRID + GRID // 2
            py = ore.y * GRID + GRID // 2
            color = ore.ore_type.color

            # Pulsing glow
            pulse = (math.sin(pyxel.frame_count * 0.1) + 1) * 0.5
            glow_radius = int(3 + pulse * 2)
            for r in range(glow_radius, 0, -1):
                alpha_color = pyxel.COLOR_BROWN if r > 2 else color
                pyxel.circ(px, py, r, alpha_color)

            # Core
            pyxel.circ(px, py, 3, pyxel.COLOR_WHITE)
            pyxel.circ(px, py, 2, color)

    def _draw_particles(self) -> None:
        """Draw particle effects."""
        for p in self.particles:
            alpha = p.life / 0.8
            # Use size for fade
            r = int(p.size * alpha)
            if r > 0:
                pyxel.circ(int(p.x), int(p.y), r, p.color)

    def _draw_floating_texts(self) -> None:
        """Draw floating score/damage text."""
        for ft in self.floating_texts:
            alpha = ft.life / 0.8
            if alpha > 0:
                # Fade out by drawing with darker shade
                col = ft.color if alpha > 0.5 else pyxel.COLOR_GRAY
                tx = int(ft.x) - len(ft.text) * 2
                ty = int(ft.y)
                pyxel.text(tx, ty, ft.text, col)

    def _draw_ui(self) -> None:
        """Draw HUD: score, combo, timer, target."""
        # Top bar background
        pyxel.rect(0, 0, SCREEN_W, 16, pyxel.COLOR_NAVY)

        # Score
        pyxel.text(2, 4, f"SCORE:{self.score}", pyxel.COLOR_WHITE)

        # Combo
        if self.combo >= 2:
            combo_text = f"COMBO x{min(self.combo, 8)}"
            combo_color = pyxel.COLOR_ORANGE if self.combo >= 5 else pyxel.COLOR_YELLOW
            pyxel.text(100, 4, combo_text, combo_color)

        # Target
        pyxel.text(200, 4, f"TGT:{TARGET_SCORE}", pyxel.COLOR_GRAY)

        # Timer bar
        bar_x = 2
        bar_y = SCREEN_H - 6
        bar_w = SCREEN_W - 4
        bar_h = 4
        ratio = self.game_timer / GAME_TIME
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, pyxel.COLOR_NAVY)
        fill_w = int(bar_w * ratio)
        if ratio > 0.5:
            bar_color = pyxel.COLOR_LIME
        elif ratio > 0.25:
            bar_color = pyxel.COLOR_YELLOW
        else:
            bar_color = pyxel.COLOR_RED
        pyxel.rect(bar_x, bar_y, fill_w, bar_h, bar_color)

        # Max combo indicator
        if self.max_combo >= 5:
            pyxel.text(SCREEN_W - 70, 4, f"BEST:x{min(self.max_combo, 8)}", pyxel.COLOR_PINK)

    def _draw_overlay(self, title: str, color: int, subtitle: str) -> None:
        """Draw victory/defeat overlay."""
        # Dim background
        for y in range(0, SCREEN_H, 2):
            pyxel.line(0, y, SCREEN_W, y, pyxel.COLOR_BLACK)

        # Title
        tx = SCREEN_W // 2 - len(title) * 2
        ty = SCREEN_H // 2 - 20
        pyxel.text(tx, ty, title, color)

        # Subtitle
        stx = SCREEN_W // 2 - len(subtitle) * 2
        sty = SCREEN_H // 2
        pyxel.text(stx, sty, subtitle, pyxel.COLOR_WHITE)

        # Max combo
        combo_text = f"Max Combo: x{min(self.max_combo, 8)}"
        ctx = SCREEN_W // 2 - len(combo_text) * 2
        cty = SCREEN_H // 2 + 12
        pyxel.text(ctx, cty, combo_text, pyxel.COLOR_YELLOW)

        # Restart hint
        hint = "SPACE to retry"
        hx = SCREEN_W // 2 - len(hint) * 2
        hy = SCREEN_H // 2 + 30
        alpha = int((math.sin(pyxel.frame_count * 0.05) + 1) * 0.5 * 7)
        pyxel.text(hx, hy, hint, alpha)


# ── Entry point ──
if __name__ == "__main__":
    OreSerpent()
