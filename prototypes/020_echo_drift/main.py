"""
ECHO DRIFT — Grid-based top-down racer prototype.
Reinterpreted from game idea #1 (score 32.15):
  auto-shooter / power plant overload → grid racer with echo trail mechanics.

The most fun moment: threading the needle at high combo, color-matching your
own echo trail for chain multipliers, then discharging just before the
volatile track consumes you.

Core mechanic: Your car leaves a colored "echo" trail on track cells.
Re-entering a cell of the SAME color triggers a COMBO (speed + score boost).
DIFFERENT color = CLASH (HP loss). Combos build HEAT; at max heat, trail
cells become VOLATILE (always damaging). DISCHARGE clears heat and trail.

Built with Pyxel 2.x — single-file, type-hinted, English-only text.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


# ── Constants ────────────────────────────────────────────────────────────────

SCREEN = 256
GRID_SIZE = 16  # cells per side
CELL = SCREEN // GRID_SIZE  # 16px per cell
FPS = 30
DISPLAY_SCALE = 3

# Element colors (Pyxel palette indices)
COLOR_FIRE = pyxel.COLOR_RED
COLOR_WATER = pyxel.COLOR_CYAN
COLOR_EARTH = pyxel.COLOR_GREEN
COLOR_AIR = pyxel.COLOR_YELLOW
COLOR_VOLATILE = pyxel.COLOR_PURPLE
COLOR_TRACK = pyxel.COLOR_DARK_BLUE
COLOR_WALL_BG = pyxel.COLOR_NAVY
COLOR_CAR = pyxel.COLOR_WHITE
COLOR_UI_BG = pyxel.COLOR_BLACK
COLOR_UI_TEXT = pyxel.COLOR_WHITE
COLOR_HEART = pyxel.COLOR_PINK
COLOR_HEAT_BAR = pyxel.COLOR_ORANGE

# Gameplay
MAX_HP = 5
MAX_HEAT = 100
COMBO_SPEED_THRESHOLDS: list[int] = [0, 3, 7, 12, 20]
HEAT_PER_COMBO = 8
HEAT_DECAY_RATE = 0.3  # per frame
VOLATILE_HEAT_THRESHOLD = 80
CLASH_DAMAGE = 1
DISCHARGE_COOLDOWN = 30  # frames


# ── Enums ────────────────────────────────────────────────────────────────────


class Direction(Enum):
    """Grid movement directions."""

    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)


class Element(Enum):
    """Four elemental affinities for car color and echo trail."""

    FIRE = auto()
    WATER = auto()
    EARTH = auto()
    AIR = auto()


class Phase(Enum):
    """Game phase state machine."""

    PLAYING = auto()
    GAME_OVER = auto()


# ── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class Cell:
    """A single grid cell on the track."""

    element: Element | None = None  # Colored echo trail (None = uncolored)
    volatile: bool = False  # True when heat overload makes it dangerous


@dataclass
class Particle:
    """Floating visual particle for combo/clash feedback."""

    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    text: str = ""


@dataclass
class FloatingText:
    """Temporary floating score/combo text."""

    x: float
    y: float
    text: str
    life: int
    color: int


# ── Track Definition ─────────────────────────────────────────────────────────


def _build_track() -> set[tuple[int, int]]:
    """Build the oval track as a set of (col, row) grid coordinates.

    Track layout (16×16 grid):
        Row  2: cols 3..12 (top straight)
        Rows 3..11: col 3 (left wall), col 12 (right wall)
        Row 12: cols 3..12 (bottom straight)

    Returns a set of (col, row) tuples.
    """
    cells: set[tuple[int, int]] = set()
    # Top straight
    for c in range(3, 13):
        cells.add((c, 2))
    # Bottom straight
    for c in range(3, 13):
        cells.add((c, 12))
    # Left vertical
    for r in range(3, 12):
        cells.add((3, r))
    # Right vertical
    for r in range(3, 12):
        cells.add((12, r))
    return cells


TRACK_CELLS: set[tuple[int, int]] = _build_track()


def is_track(col: int, row: int) -> bool:
    """Check if a grid coordinate is on the track."""
    return (col, row) in TRACK_CELLS


# ── Element Helpers ──────────────────────────────────────────────────────────


ELEMENT_ORDER: list[Element] = [Element.FIRE, Element.WATER, Element.EARTH, Element.AIR]

ELEMENT_COLORS: dict[Element, int] = {
    Element.FIRE: COLOR_FIRE,
    Element.WATER: COLOR_WATER,
    Element.EARTH: COLOR_EARTH,
    Element.AIR: COLOR_AIR,
}

ELEMENT_NAMES: dict[Element, str] = {
    Element.FIRE: "FIRE",
    Element.WATER: "WATER",
    Element.EARTH: "EARTH",
    Element.AIR: "AIR",
}


def next_element(current: Element) -> Element:
    """Cycle to the next element in rotation."""
    idx = ELEMENT_ORDER.index(current)
    return ELEMENT_ORDER[(idx + 1) % len(ELEMENT_ORDER)]


# ── Game Class ───────────────────────────────────────────────────────────────


class Game:
    """ECHO DRIFT — Grid-based racing prototype."""

    def __init__(self) -> None:
        pyxel.init(SCREEN, SCREEN, title="ECHO DRIFT", fps=FPS, display_scale=DISPLAY_SCALE)
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── State ────────────────────────────────────────────────────────────

    def reset(self) -> None:
        """Initialize / reset all game state."""
        self.phase: Phase = Phase.PLAYING
        self.hp: int = MAX_HP
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.car_element: Element = Element.FIRE
        self.car_col: int = 8  # Start near middle-top of track
        self.car_row: int = 2
        self.direction: Direction = Direction.RIGHT
        self.laps: int = 0
        self.lap_progress: float = 0.0
        self.discharge_cooldown: int = 0

        # Grid state: dict of (col, row) → Cell for colored cells only
        self.grid: dict[tuple[int, int], Cell] = {}

        # Visual effects
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []

        # Auto color cycle
        self.color_timer: int = 0
        self.color_interval: int = 90  # frames (3 seconds at 30fps)

        # Input tracking (prevent repeated movement in one frame)
        self._moved_this_frame: bool = False

        # Screen shake
        self.shake_frames: int = 0
        self.shake_intensity: int = 0

    # ── Update ───────────────────────────────────────────────────────────

    def update(self) -> None:
        """Main update loop."""
        self._moved_this_frame = False

        # Quit
        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()

        if self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

        # Always update particles and floating texts
        self._update_particles()
        self._update_floating_texts()
        self._update_shake()

        # Decay heat
        if self.phase == Phase.PLAYING and self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY_RATE)

        # Decay discharge cooldown
        if self.discharge_cooldown > 0:
            self.discharge_cooldown -= 1

    def _update_playing(self) -> None:
        """Update during PLAYING phase."""
        # Auto color cycling
        self.color_timer += 1
        if self.color_timer >= self.color_interval:
            self.color_timer = 0
            self.car_element = next_element(self.car_element)
            self._spawn_particles(
                self.car_col * CELL + CELL // 2,
                self.car_row * CELL + CELL // 2,
                ELEMENT_COLORS[self.car_element],
                6,
            )

        # Input: direction change + move (one press = set direction and move one cell)
        moved = False
        if pyxel.btnp(pyxel.KEY_UP):
            self.direction = Direction.UP
            moved = True
        elif pyxel.btnp(pyxel.KEY_DOWN):
            self.direction = Direction.DOWN
            moved = True
        elif pyxel.btnp(pyxel.KEY_LEFT):
            self.direction = Direction.LEFT
            moved = True
        elif pyxel.btnp(pyxel.KEY_RIGHT):
            self.direction = Direction.RIGHT
            moved = True

        if moved:
            self._move_car()

        # Discharge
        if pyxel.btnp(pyxel.KEY_D) and self.discharge_cooldown == 0:
            self._discharge()

    def _move_car(self) -> None:
        """Move the car one cell in the current direction if possible."""
        if self._moved_this_frame:
            return

        dx, dy = self.direction.value
        new_col = self.car_col + dx
        new_row = self.car_row + dy

        if not is_track(new_col, new_row):
            return  # Can't move off track

        self._moved_this_frame = True

        # Leave echo on current cell before moving
        old_pos = (self.car_col, self.car_row)
        if old_pos not in self.grid:
            self.grid[old_pos] = Cell(element=self.car_element)
        else:
            # Update existing cell's element (overwrite with current)
            self.grid[old_pos].element = self.car_element

        # Move
        self.car_col = new_col
        self.car_row = new_row
        new_pos = (new_col, new_row)
        self.score += 1

        # Check what we landed on
        cell = self.grid.get(new_pos)
        if cell is not None and cell.element is not None:
            if cell.volatile:
                # Volatile cell always damages
                self._handle_clash(new_pos)
            elif cell.element == self.car_element:
                # Same color → COMBO!
                self._handle_combo(new_pos)
            else:
                # Different color → CLASH
                self._handle_clash(new_pos)
        else:
            # Uncolored cell — reset combo (no penalty but no reward)
            self._reset_combo()

        # Update track progress
        self._update_lap_progress()

    def _handle_combo(self, pos: tuple[int, int]) -> None:
        """Handle landing on a same-color echo cell."""
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo

        bonus = self.combo * 10
        self.score += bonus

        px = pos[0] * CELL + CELL // 2
        py_pos = pos[1] * CELL + CELL // 2
        self._spawn_particles(px, py_pos, ELEMENT_COLORS[self.car_element], 12)
        self._add_floating_text(px, py_pos - 8, f"+{bonus}", ELEMENT_COLORS[self.car_element])
        self._add_floating_text(px, py_pos, f"x{self.combo}", pyxel.COLOR_WHITE)

        # Build heat
        self.heat = min(float(MAX_HEAT), self.heat + HEAT_PER_COMBO + self.combo * 0.5)

        # Make cells volatile if heat is high
        if self.heat >= VOLATILE_HEAT_THRESHOLD:
            self._make_volatile()

    def _handle_clash(self, pos: tuple[int, int]) -> None:
        """Handle landing on a different-color or volatile echo cell."""
        self.hp -= CLASH_DAMAGE
        self.combo = 0

        px = pos[0] * CELL + CELL // 2
        py_pos = pos[1] * CELL + CELL // 2
        self._spawn_particles(px, py_pos, pyxel.COLOR_RED, 8)
        self._add_floating_text(px, py_pos - 8, "CLASH!", pyxel.COLOR_RED)
        self._add_shake(6, 3)

        if self.hp <= 0:
            self.hp = 0
            self.phase = Phase.GAME_OVER

    def _reset_combo(self) -> None:
        """Reset combo when landing on uncolored cell."""
        self.combo = 0

    def _discharge(self) -> None:
        """Clear all heat and volatile trail cells."""
        if self.discharge_cooldown > 0:
            return

        self.heat = 0.0
        self.discharge_cooldown = DISCHARGE_COOLDOWN

        # Clear all volatile flags and remove all echo cells
        cleared = 0
        for cell in self.grid.values():
            if cell.volatile:
                cleared += 1
            cell.volatile = False
            cell.element = None

        # Actually clear all colored cells (full board reset)
        self.grid.clear()

        # Visual feedback
        px = self.car_col * CELL + CELL // 2
        py_pos = self.car_row * CELL + CELL // 2
        for _ in range(20):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x=px,
                    y=py_pos,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=random.randint(15, 30),
                    color=pyxel.COLOR_CYAN,
                )
            )
        self._add_floating_text(px, py_pos - 8, "CLEAR!", pyxel.COLOR_CYAN)
        self._add_shake(4, 2)

    def _make_volatile(self) -> None:
        """Convert all colored trail cells to volatile (damaging)."""
        for cell in self.grid.values():
            if cell.element is not None:
                cell.volatile = True

    def _update_lap_progress(self) -> None:
        """Track approximate lap completion."""
        # Simple heuristic: track car's row/col position relative to start area
        # Start area is top straight (row 2)
        # A "lap" is when we go from row > 2 → row 2 while moving right
        if self.car_row == 2 and self.car_col > 8 and self.lap_progress > 0.5:
            self.laps += 1
            self.lap_progress = 0.0
            self.score += 100  # Lap bonus
            self._add_floating_text(
                self.car_col * CELL + CELL // 2,
                self.car_row * CELL - 10,
                f"LAP {self.laps}!",
                pyxel.COLOR_WHITE,
            )
        else:
            # Track progress through the loop
            self.lap_progress = min(1.0, self.lap_progress + 0.03)

    # ── Update Helpers ───────────────────────────────────────────────────

    def _update_game_over(self) -> None:
        """Update during GAME_OVER phase — wait for restart."""
        if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()

    def _update_particles(self) -> None:
        """Update all particles: move, decay life, remove dead."""
        survivors: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                survivors.append(p)
        self.particles = survivors

    def _update_floating_texts(self) -> None:
        """Update floating texts: rise, decay, remove dead."""
        survivors: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life > 0:
                survivors.append(ft)
        self.floating_texts = survivors

    def _update_shake(self) -> None:
        """Update screen shake countdown."""
        if self.shake_frames > 0:
            self.shake_frames -= 1
            if self.shake_frames == 0:
                pyxel.camera(0, 0)

    # ── Draw ─────────────────────────────────────────────────────────────

    def draw(self) -> None:
        """Main draw loop."""
        pyxel.cls(COLOR_UI_BG)

        # Draw grid background
        self._draw_track()

        # Draw echo trail
        self._draw_echoes()

        # Draw car
        self._draw_car()

        # Draw particles
        self._draw_particles()

        # Draw floating texts
        self._draw_floating_texts()

        # Draw UI
        self._draw_ui()

        # Draw game over overlay
        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_track(self) -> None:
        """Draw the track and wall grid."""
        for col in range(GRID_SIZE):
            for row in range(GRID_SIZE):
                x = col * CELL
                y = row * CELL
                if is_track(col, row):
                    pyxel.rect(x, y, CELL, CELL, COLOR_TRACK)
                else:
                    pyxel.rect(x, y, CELL, CELL, COLOR_WALL_BG)

    def _draw_echoes(self) -> None:
        """Draw colored and volatile trail cells."""
        for (col, row), cell in self.grid.items():
            x = col * CELL
            y = row * CELL
            if cell.volatile:
                # Pulsing volatile effect
                pulse = (pyxel.frame_count % 20) < 10
                color = COLOR_VOLATILE if pulse else pyxel.COLOR_RED
                pyxel.rect(x + 1, y + 1, CELL - 2, CELL - 2, color)
            elif cell.element is not None:
                color = ELEMENT_COLORS[cell.element]
                pyxel.rect(x + 2, y + 2, CELL - 4, CELL - 4, color)

    def _draw_car(self) -> None:
        """Draw the player car."""
        x = self.car_col * CELL
        y = self.car_row * CELL

        # Car body
        pyxel.rect(x + 2, y + 2, CELL - 4, CELL - 4, COLOR_CAR)

        # Element color border
        border = ELEMENT_COLORS[self.car_element]
        pyxel.rectb(x + 1, y + 1, CELL - 2, CELL - 2, border)

        # Combo glow (pulsing border when combo is active)
        if self.combo >= 3:
            pulse_phase = (pyxel.frame_count // 4) % 2
            if pulse_phase == 0:
                pyxel.rectb(x, y, CELL, CELL, border)

    def _draw_particles(self) -> None:
        """Draw visual particles."""
        for p in self.particles:
            alpha = p.life / 20.0
            if alpha > 1.0:
                alpha = 1.0
            if alpha > 0.3:
                pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        """Draw floating score/combo text."""
        for ft in self.floating_texts:
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_ui(self) -> None:
        """Draw HUD: HP, combo, heat, score."""
        # HP hearts
        heart_x = 4
        heart_y = SCREEN - 12
        for i in range(self.hp):
            pyxel.text(heart_x + i * 14, heart_y, "O", COLOR_HEART)

        # Score
        pyxel.text(4, 4, f"SCORE:{self.score:06d}", COLOR_UI_TEXT)

        # Combo
        if self.combo > 0:
            combo_text = f"COMBO x{self.combo}"
            pyxel.text(SCREEN - len(combo_text) * 4 - 4, 4, combo_text, COLOR_AIR)

        # Max combo
        if self.max_combo > 0:
            max_text = f"MAX:{self.max_combo}"
            pyxel.text(SCREEN - len(max_text) * 4 - 4, 12, max_text, pyxel.COLOR_GRAY)

        # Heat bar
        bar_x = 4
        bar_y = 16
        bar_w = 60
        bar_h = 6
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, COLOR_UI_TEXT)
        heat_w = int(bar_w * self.heat / MAX_HEAT)
        heat_color = COLOR_HEAT_BAR if self.heat < VOLATILE_HEAT_THRESHOLD else pyxel.COLOR_RED
        pyxel.rect(bar_x + 1, bar_y + 1, heat_w - 2, bar_h - 2, heat_color)
        pyxel.text(bar_x + bar_w + 4, bar_y - 1, "HEAT", COLOR_UI_TEXT)

        # Volatile warning
        if self.heat >= VOLATILE_HEAT_THRESHOLD:
            warn_text = "VOLATILE!"
            if (pyxel.frame_count // 15) % 2 == 0:
                pyxel.text(bar_x, bar_y + 8, warn_text, pyxel.COLOR_RED)

        # Discharge status
        disc_y = 26
        if self.discharge_cooldown > 0:
            disc_text = f"D:{self.discharge_cooldown // 10}"
            pyxel.text(4, disc_y, disc_text, pyxel.COLOR_GRAY)
        else:
            pyxel.text(4, disc_y, "D:READY", pyxel.COLOR_CYAN)

        # Current element
        elem_text = f"[{ELEMENT_NAMES[self.car_element]}]"
        pyxel.text(
            SCREEN - len(elem_text) * 4 - 4,
            disc_y,
            elem_text,
            ELEMENT_COLORS[self.car_element],
        )

        # Laps
        lap_text = f"LAP:{self.laps}"
        pyxel.text(4, 36, lap_text, pyxel.COLOR_WHITE)

    def _draw_game_over(self) -> None:
        """Draw game over overlay."""
        # Dim background
        pyxel.rect(0, 0, SCREEN, SCREEN, pyxel.COLOR_BLACK)

        # Title
        title = "GAME OVER"
        tx = SCREEN // 2 - len(title) * 2
        pyxel.text(tx, 80, title, pyxel.COLOR_RED)

        # Score
        score_text = f"SCORE: {self.score}"
        sx = SCREEN // 2 - len(score_text) * 2
        pyxel.text(sx, 100, score_text, pyxel.COLOR_WHITE)

        # Max combo
        combo_text = f"MAX COMBO: x{self.max_combo}"
        cx = SCREEN // 2 - len(combo_text) * 2
        pyxel.text(cx, 112, combo_text, COLOR_AIR)

        # Laps
        lap_text = f"LAPS: {self.laps}"
        lx = SCREEN // 2 - len(lap_text) * 2
        pyxel.text(lx, 124, lap_text, pyxel.COLOR_WHITE)

        # Restart prompt
        restart = "PRESS [R] TO RETRY"
        rx = SCREEN // 2 - len(restart) * 2
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(rx, 160, restart, pyxel.COLOR_WHITE)

    # ── Effect Helpers ───────────────────────────────────────────────────

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        """Spawn burst particles at a position."""
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(0.5, 2.5)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=random.randint(8, 20),
                    color=color,
                )
            )

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        """Add a floating text effect."""
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=40, color=color))

    def _add_shake(self, frames: int, intensity: int) -> None:
        """Add screen shake (headless-safe)."""
        self.shake_frames = max(self.shake_frames, frames)
        self.shake_intensity = max(self.shake_intensity, intensity)
        if self.shake_frames > 0:
            off_x = random.randint(-self.shake_intensity, self.shake_intensity)
            off_y = random.randint(-self.shake_intensity, self.shake_intensity)
            try:
                pyxel.camera(off_x, off_y)
            except BaseException:
                pass  # Headless mode — Pyxel not initialized (panic is BaseException)


# ── Entry Point ──────────────────────────────────────────────────────────────


def main() -> None:
    """Launch the game."""
    Game()


if __name__ == "__main__":
    main()
