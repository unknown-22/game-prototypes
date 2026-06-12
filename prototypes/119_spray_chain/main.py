"""SPRAY CHAIN - Graffiti spray paint game prototype.

Chain same-color sprays to build COMBO. COMBO >= 4 activates SUPER SPRAY
(rainbow color, 5x5 pattern, 3x score). Wrong-color sprays reset COMBO
and increase HEAT. 60-second time limit with CA drip propagation.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ────────────────────────────────────────────────────────────────

SCREEN_W = 320
SCREEN_H = 240
GRID_COLS = 20
GRID_ROWS = 15
CELL_SIZE = 16

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

PAINT_COLORS: tuple[int, ...] = (RED, GREEN, DARK_BLUE, YELLOW)
PAINT_NAMES: tuple[str, ...] = ("RED", "GREEN", "BLUE", "YELLOW")
NUM_COLORS = len(PAINT_COLORS)

FPS = 60
GAME_DURATION = 3600
SPRAY_COOLDOWN = 3
SUPER_DURATION = 300
DRIP_INTERVAL = 30
HEAT_DECAY_INTERVAL = 12
HEAT_DECAY_AMOUNT = 1
MAX_HEAT = 100
HEAT_MISMATCH = 15
SUPER_COMBO_THRESHOLD = 4
SHAKE_FRAMES = 8
SHAKE_AMPLITUDE = 4

BASE_SCORE_PER_CELL = 10

SEED = 42
random.seed(SEED)

# ── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class DripParticle:
    x: float
    y: float
    vy: float
    life: int
    color: int


# ── Phase Enum ───────────────────────────────────────────────────────────────


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ── Game Class ───────────────────────────────────────────────────────────────


class Game:
    """Core game state and logic. Pyxel-free for headless testing."""

    def _init_all_attrs(self) -> None:
        """Pre-initialize all instance attributes for headless testing."""
        self.phase: Phase = Phase.TITLE
        self.grid: list[list[int]] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.game_timer: int = GAME_DURATION
        self.current_color: int = 0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.spray_cooldown: int = 0
        self.drip_timer: int = DRIP_INTERVAL
        self.heat_decay_timer: int = 0
        self.cells_painted: int = 0
        self.total_sprays: int = 0
        self.particles: list[Particle] = []
        self.drip_particles: list[DripParticle] = []
        self.shake_frames: int = 0
        self._last_wheel: int = 0

    def reset(self) -> None:
        """Initialize or reset all game state for a new round."""
        self.phase = Phase.PLAYING
        self.grid = [[-1 for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.game_timer = GAME_DURATION
        self.current_color = 0
        self.super_mode = False
        self.super_timer = 0
        self.spray_cooldown = 0
        self.drip_timer = DRIP_INTERVAL
        self.heat_decay_timer = 0
        self.cells_painted = 0
        self.total_sprays = 0
        self.particles = []
        self.drip_particles = []
        self.shake_frames = 0
        self._last_wheel = 0

    # ── Core Mechanics (testable) ────────────────────────────────────────

    def _spray_at(self, gx: int, gy: int) -> tuple[int, bool, bool]:
        """Apply spray at grid position.

        Returns:
            (cells_painted_this_spray, color_matched, was_super)
        """
        cells_painted = 0
        color_matched = True
        was_super = self.super_mode

        size = 5 if self.super_mode else 3
        half = size // 2

        for dy in range(-half, half + 1):
            for dx in range(-half, half + 1):
                cx = gx + dx
                cy = gy + dy
                if 0 <= cx < GRID_COLS and 0 <= cy < GRID_ROWS:
                    cell_val = self.grid[cy][cx]
                    if cell_val == -1:
                        paint_color = (
                            random.randint(0, NUM_COLORS - 1)
                            if self.super_mode
                            else self.current_color
                        )
                        self.grid[cy][cx] = paint_color
                        cells_painted += 1
                        self.cells_painted += 1
                    elif cell_val != self.current_color and not self.super_mode:
                        color_matched = False

        return cells_painted, color_matched, was_super

    def _activate_super(self) -> None:
        """Enter SUPER SPRAY mode."""
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self.shake_frames = SHAKE_FRAMES

    def _deactivate_super(self) -> None:
        """Exit SUPER SPRAY mode."""
        self.super_mode = False
        self.super_timer = 0

    def _ca_drip(self) -> None:
        """CA propagation: painted cells have a chance to drip downward.

        Scans top-to-bottom so cascading drips can occur in one pass.
        """
        for gy in range(GRID_ROWS):
            for gx in range(GRID_COLS):
                cell_val = self.grid[gy][gx]
                if cell_val == -1:
                    continue
                if random.random() < 0.1:
                    px = gx * CELL_SIZE + CELL_SIZE // 2
                    py = gy * CELL_SIZE + CELL_SIZE
                    self._spawn_drip_particle(float(px), float(py), PAINT_COLORS[cell_val])

                    if gy + 1 < GRID_ROWS and self.grid[gy + 1][gx] == -1:
                        self.grid[gy + 1][gx] = cell_val
                        self.cells_painted += 1
                        for _ in range(random.randint(2, 4)):
                            self.particles.append(
                                Particle(
                                    x=float(gx * CELL_SIZE + random.randint(2, 14)),
                                    y=float((gy + 1) * CELL_SIZE + 2),
                                    vx=random.uniform(-0.5, 0.5),
                                    vy=random.uniform(-1.5, -0.5),
                                    life=random.randint(5, 10),
                                    color=PAINT_COLORS[cell_val],
                                )
                            )

    def _update_heat(self) -> None:
        """Decay heat over time."""
        self.heat_decay_timer += 1
        if self.heat_decay_timer >= HEAT_DECAY_INTERVAL:
            self.heat_decay_timer = 0
            if self.heat > 0:
                self.heat = max(0.0, self.heat - HEAT_DECAY_AMOUNT)

    def _update_timer(self) -> bool:
        """Decrement game timer. Returns True if time is up."""
        if self.game_timer > 0:
            self.game_timer -= 1
        return self.game_timer <= 0

    def _update_particles(self) -> None:
        """Move particles, apply gravity, remove dead ones."""
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.3
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_drip_particles(self) -> None:
        """Move drip particles downward, remove off-screen or dead ones."""
        for dp in self.drip_particles:
            dp.y += dp.vy
            dp.life -= 1
        self.drip_particles = [
            dp for dp in self.drip_particles if dp.life > 0 and dp.y < SCREEN_H + 10
        ]

    def _spawn_spray_particles(
        self, gx: int, gy: int, color: int, count: int
    ) -> None:
        """Spawn particle burst at spray location."""
        cx = gx * CELL_SIZE + CELL_SIZE // 2
        cy = gy * CELL_SIZE + CELL_SIZE // 2
        is_super = self.super_mode
        vel_max = 3.0 if is_super else 2.0
        vel_min = 1.0 if is_super else 0.5
        life_min, life_max = (15, 25) if is_super else (10, 20)

        for _ in range(count):
            particle_color = (
                PAINT_COLORS[random.randint(0, NUM_COLORS - 1)]
                if is_super
                else color
            )
            self.particles.append(
                Particle(
                    x=float(cx + random.uniform(-4, 4)),
                    y=float(cy + random.uniform(-4, 4)),
                    vx=random.uniform(-vel_max, vel_max),
                    vy=random.uniform(-vel_max, -vel_min),
                    life=random.randint(life_min, life_max),
                    color=particle_color,
                )
            )

    def _spawn_drip_particle(self, x: float, y: float, color: int) -> None:
        """Spawn a single drip particle."""
        self.drip_particles.append(
            DripParticle(
                x=x,
                y=y,
                vy=random.uniform(1.0, 2.0),
                life=random.randint(20, 40),
                color=color,
            )
        )

    def _cell_color(self, gx: int, gy: int) -> int:
        """Get pyxel color for a grid cell value. Unpainted returns BROWN."""
        cell_val = self.grid[gy][gx]
        if cell_val == -1:
            return BROWN
        return PAINT_COLORS[cell_val]


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_game() -> Game:
    """Factory for headless testing. Bypasses __init__ to avoid pyxel."""
    g = Game.__new__(Game)
    g._init_all_attrs()
    g.reset()
    return g


# ── App Class (Pyxel Integration) ───────────────────────────────────────────


class App:
    """Pyxel application wrapper for SPRAY CHAIN."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="SPRAY CHAIN", display_scale=2, fps=FPS)
        self.game = Game.__new__(Game)
        self.game._init_all_attrs()
        self.game.reset()
        self.game.phase = Phase.TITLE
        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    # ── Update ────────────────────────────────────────────────────────────

    def update(self) -> None:
        g = self.game

        if g.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_RETURN):
                g.reset()
            return

        if g.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_RETURN):
                g.reset()
            return

        # ── PLAYING ──

        # Color switching via keyboard
        if pyxel.btnp(pyxel.KEY_1):
            g.current_color = 0
        elif pyxel.btnp(pyxel.KEY_2):
            g.current_color = 1
        elif pyxel.btnp(pyxel.KEY_3):
            g.current_color = 2
        elif pyxel.btnp(pyxel.KEY_4):
            g.current_color = 3

        # Color cycling via mouse wheel
        wheel = pyxel.mouse_wheel
        if wheel != g._last_wheel:
            delta = wheel - g._last_wheel
            g.current_color = (g.current_color + (1 if delta > 0 else -1)) % NUM_COLORS
            g._last_wheel = wheel

        # Spray cooldown
        if g.spray_cooldown > 0:
            g.spray_cooldown -= 1

        # SUPER timer (decrement before spray per spec edge case)
        if g.super_mode:
            g.super_timer -= 1
            if g.super_timer <= 0:
                g._deactivate_super()

        # Handle spray input
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        if (
            pyxel.btn(pyxel.MOUSE_BUTTON_LEFT)
            and g.spray_cooldown <= 0
            and 0 <= mx < SCREEN_W
            and 0 <= my < SCREEN_H
        ):
            gx = mx // CELL_SIZE
            gy = my // CELL_SIZE

            # Activate SUPER before spray if combo threshold reached
            if g.combo >= SUPER_COMBO_THRESHOLD and not g.super_mode:
                g._activate_super()

            cells_painted, color_matched, was_super = g._spray_at(gx, gy)

            if was_super:
                g.combo += 1
            elif color_matched:
                g.combo += 1
            else:
                g.combo = 0
                g.heat = min(float(MAX_HEAT), g.heat + HEAT_MISMATCH)

            if g.combo > g.max_combo:
                g.max_combo = g.combo

            # Score
            combo_mult = 1.0 + g.combo * 0.1
            score_add = int(
                cells_painted * BASE_SCORE_PER_CELL * combo_mult * (3 if was_super else 1)
            )
            g.score += score_add

            g.total_sprays += 1
            g.spray_cooldown = SPRAY_COOLDOWN

            particle_color = PAINT_COLORS[g.current_color]
            particle_count = (
                random.randint(20, 30) if was_super else random.randint(8, 12)
            )
            g._spawn_spray_particles(gx, gy, particle_color, particle_count)

        # CA drip
        g.drip_timer -= 1
        if g.drip_timer <= 0:
            g.drip_timer = DRIP_INTERVAL
            g._ca_drip()

        # Particles
        g._update_particles()
        g._update_drip_particles()

        # Heat decay
        g._update_heat()

        # Timer
        time_up = g._update_timer()

        # Shake
        if g.shake_frames > 0:
            g.shake_frames -= 1

        # Game over checks
        if time_up or g.heat >= MAX_HEAT:
            g.phase = Phase.GAME_OVER

    # ── Draw ──────────────────────────────────────────────────────────────

    def draw(self) -> None:
        g = self.game

        shake_x = 0
        shake_y = 0
        if g.shake_frames > 0:
            shake_x = random.randint(-SHAKE_AMPLITUDE, SHAKE_AMPLITUDE)
            shake_y = random.randint(-SHAKE_AMPLITUDE, SHAKE_AMPLITUDE)
        pyxel.camera(shake_x, shake_y)

        pyxel.cls(BLACK)

        if g.phase == Phase.TITLE:
            self._draw_title()
        elif g.phase == Phase.PLAYING:
            self._draw_game()
        elif g.phase == Phase.GAME_OVER:
            self._draw_game_over()

        pyxel.camera(0, 0)

    # ── Title Screen ──────────────────────────────────────────────────────

    def _draw_title(self) -> None:
        title = "SPRAY CHAIN"
        pyxel.text(SCREEN_W // 2 - len(title) * 2, 30, title, WHITE)

        pyxel.text(SCREEN_W // 2 - 50, 55, "CLICK TO START", YELLOW)

        pyxel.text(SCREEN_W // 2 - 50, 75, "PAINT COLORS:", GRAY)
        for i, (name, color) in enumerate(zip(PAINT_NAMES, PAINT_COLORS)):
            y = 90 + i * 15
            pyxel.rect(SCREEN_W // 2 - 50, y, 12, 12, color)
            pyxel.text(SCREEN_W // 2 - 34, y + 2, name, color)

        lines = [
            "1-4 : Switch Color",
            "Wheel : Cycle Color",
            "Mouse : Hold to Spray",
            "Same color = COMBO UP",
            "COMBO >= 4 = SUPER SPRAY!",
            "Wrong color = COMBO LOST + HEAT",
            "HEAT 100 = Canvas Ruined",
            "60 sec to get HIGH SCORE!",
        ]
        for i, line in enumerate(lines):
            pyxel.text(SCREEN_W // 2 - len(line) * 2, 160 + i * 10, line, GRAY)

    # ── Game Screen ───────────────────────────────────────────────────────

    def _draw_game(self) -> None:
        g = self.game

        # Draw grid cells
        for gy in range(GRID_ROWS):
            for gx in range(GRID_COLS):
                px = gx * CELL_SIZE
                py = gy * CELL_SIZE
                cell_val = g.grid[gy][gx]
                if cell_val == -1:
                    pyxel.rect(px, py, CELL_SIZE, CELL_SIZE, BROWN)
                else:
                    pyxel.rect(px, py, CELL_SIZE, CELL_SIZE, PAINT_COLORS[cell_val])
                pyxel.rectb(px, py, CELL_SIZE, CELL_SIZE, BLACK)

        # Drip particles (thin vertical lines)
        for dp in g.drip_particles:
            line_len = min(dp.life // 2, 6)
            pyxel.line(
                int(dp.x), int(dp.y),
                int(dp.x), int(dp.y + line_len),
                dp.color,
            )

        # Spray particles
        for p in g.particles:
            size = max(1, p.life // 6 + 1)
            pyxel.rect(int(p.x), int(p.y), size, size, p.color)

        # Spray area indicator around cursor
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        if 0 <= mx < SCREEN_W and 0 <= my < SCREEN_H:
            gx = mx // CELL_SIZE
            gy = my // CELL_SIZE
            size = 5 if g.super_mode else 3
            half = size // 2

            indicator_color = PAINT_COLORS[g.current_color]
            if g.super_mode:
                indicator_color = PAINT_COLORS[(pyxel.frame_count // 4) % NUM_COLORS]

            left = max(0, (gx - half) * CELL_SIZE)
            top = max(0, (gy - half) * CELL_SIZE)
            right = min(SCREEN_W - 1, (gx + half + 1) * CELL_SIZE - 1)
            bottom = min(SCREEN_H - 1, (gy + half + 1) * CELL_SIZE - 1)

            dash = 5
            for x in range(left, right, dash * 2):
                end_x = min(x + dash, right)
                pyxel.line(x, top, end_x, top, indicator_color)
                pyxel.line(x, bottom, end_x, bottom, indicator_color)
            for y in range(top, bottom, dash * 2):
                end_y = min(y + dash, bottom)
                pyxel.line(left, y, left, end_y, indicator_color)
                pyxel.line(right, y, right, end_y, indicator_color)

            # Center crosshair
            cx = gx * CELL_SIZE + CELL_SIZE // 2
            cy = gy * CELL_SIZE + CELL_SIZE // 2
            pyxel.pset(cx, cy, indicator_color)

        # ── UI Overlay ──

        # HEAT bar (top-left)
        bar_w = 80
        bar_h = 6
        bar_x = 4
        bar_y = 4
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, DARK_BLUE)
        fill_w = int(g.heat / MAX_HEAT * bar_w)
        heat_color = GREEN if g.heat < 50 else (YELLOW if g.heat < 80 else RED)
        if fill_w > 0:
            pyxel.rect(bar_x, bar_y, fill_w, bar_h, heat_color)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        pyxel.text(bar_x + bar_w + 4, bar_y - 1, "HEAT", GRAY)

        # Current color (below HEAT bar)
        ci_y = bar_y + bar_h + 4
        pyxel.rect(4, ci_y, 10, 10, PAINT_COLORS[g.current_color])
        pyxel.text(16, ci_y + 1, PAINT_NAMES[g.current_color], PAINT_COLORS[g.current_color])

        # COMBO (top-center)
        combo_text = f"COMBO: {min(g.combo, 99)}"
        combo_color = (
            PINK if g.super_mode
            else (PEACH if g.combo >= SUPER_COMBO_THRESHOLD else WHITE)
        )
        pyxel.text(SCREEN_W // 2 - len(combo_text) * 2, 4, combo_text, combo_color)

        # SUPER indicator
        if g.super_mode:
            super_text = f"SUPER! {g.super_timer // 60 + 1}s"
            pyxel.text(
                SCREEN_W // 2 - len(super_text) * 2, 14, super_text, PINK
            )

        # Score (top-right)
        score_text = f"SCORE: {g.score}"
        pyxel.text(SCREEN_W - len(score_text) * 4 - 4, 4, score_text, WHITE)

        # Timer (bottom-center)
        sec = g.game_timer // 60
        timer_text = f"TIME: {sec}s"
        timer_color = RED if sec < 10 else WHITE
        pyxel.text(
            SCREEN_W // 2 - len(timer_text) * 2, SCREEN_H - 14, timer_text, timer_color
        )

        # Max combo (bottom-right)
        best_text = f"BEST: {min(g.max_combo, 99)}x"
        pyxel.text(
            SCREEN_W - len(best_text) * 4 - 4, SCREEN_H - 14, best_text, GRAY
        )

    # ── Game Over Screen ──────────────────────────────────────────────────

    def _draw_game_over(self) -> None:
        g = self.game

        # Dim background by drawing grid in dark tones
        for gy in range(GRID_ROWS):
            for gx in range(GRID_COLS):
                px = gx * CELL_SIZE
                py = gy * CELL_SIZE
                if g.grid[gy][gx] != -1:
                    pyxel.rect(px, py, CELL_SIZE, CELL_SIZE, NAVY)
                pyxel.rectb(px, py, CELL_SIZE, CELL_SIZE, BLACK)

        # Panel
        px = 40
        py = 20
        pw = SCREEN_W - 80
        ph = SCREEN_H - 40
        pyxel.rect(px, py, pw, ph, BLACK)
        pyxel.rectb(px, py, pw, ph, WHITE)

        # Title
        if g.heat >= MAX_HEAT:
            title = "CANVAS RUINED"
        else:
            title = "TIME'S UP!"
        pyxel.text(SCREEN_W // 2 - len(title) * 2, py + 10, title, RED)

        # Stats
        y = py + 32
        stats = [
            f"SCORE: {g.score}",
            f"CELLS PAINTED: {g.cells_painted}",
            f"MAX COMBO: {g.max_combo}",
            f"TOTAL SPRAYS: {g.total_sprays}",
        ]
        for stat in stats:
            pyxel.text(SCREEN_W // 2 - len(stat) * 2, y, stat, WHITE)
            y += 16

        # Tier
        y += 6
        if g.score >= 5000:
            tier = "MASTERPIECE!"
            tcol = PINK
        elif g.score >= 2000:
            tier = "GREAT WORK!"
            tcol = PEACH
        elif g.score >= 800:
            tier = "NOT BAD!"
            tcol = YELLOW
        else:
            tier = "KEEP TRYING!"
            tcol = GRAY
        pyxel.text(SCREEN_W // 2 - len(tier) * 2, y, tier, tcol)

        # Restart
        pyxel.text(
            SCREEN_W // 2 - 55, py + ph - 14, "CLICK TO RESTART", YELLOW
        )


# ── Entry Point ──────────────────────────────────────────────────────────────


def main() -> None:
    App()


if __name__ == "__main__":
    main()
