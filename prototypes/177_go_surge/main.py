"""177_go_surge - Liberty Chain

Go-like territory capture puzzle. Place colored stones on a 7×7 grid.
Same-color consecutive placements build COMBO chain.
COMBO≥3 triggers BFS liberty-based capture of surrounded enemy groups.
COMBO≥5 unlocks SUPER STONE rainbow mode with auto-capture.

面白い瞬間 (core fun moment):
Building a chain of same-color placements, then watching BFS flood-fill
surround and capture a huge enemy group in one sweep with score explosion.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import ClassVar

import pyxel

# ── Constants ──────────────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
FPS = 30
DISPLAY_SCALE = 2

GRID_SIZE = 7
CELL = 28
OX = 62
OY = 20

STONE_RADIUS = 10
DOT_RADIUS = 3

STONE_COLORS: tuple[int, ...] = (8, 3, 5, 10)  # RED, GREEN, DARK_BLUE, YELLOW
COLOR_NAMES: tuple[str, ...] = ("RED", "GREEN", "BLUE", "YELLOW")

COMBO_THRESHOLD = 3
SUPER_THRESHOLD = 5
SUPER_DURATION = 150
HEAT_MAX = 100.0
HEAT_PER_MISMATCH = 20.0
HEAT_DECAY = 0.05
MAX_STONES = 30
INITIAL_STONES = 10
SPAWN_INTERVAL = 180

# Pyxel palette
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

RAINBOW = (RED, ORANGE, YELLOW, GREEN, CYAN, PINK)

FONT_PATH = Path(__file__).with_name("k8x12.bdf")


# ── Enums ──────────────────────────────────────────────────────────────────────
class Phase(IntEnum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


# ── Data Classes ───────────────────────────────────────────────────────────────
@dataclass
class Stone:
    color: int
    col: int
    row: int


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
    vy: float = -0.6


# ── Game ───────────────────────────────────────────────────────────────────────
class Game:
    _DIRS: ClassVar[list[tuple[int, int]]] = [(0, -1), (0, 1), (-1, 0), (1, 0)]

    def __init__(self) -> None:
        pyxel.init(
            SCREEN_W, SCREEN_H,
            title="Liberty Chain",
            display_scale=DISPLAY_SCALE,
            fps=FPS,
        )
        self._font: pyxel.Font | None = None
        if FONT_PATH.exists():
            self._font = pyxel.Font(str(FONT_PATH))
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── Reset ──────────────────────────────────────────────────────────────
    def reset(self) -> None:
        self._rng = random.Random()
        self.phase = Phase.TITLE
        self._init_game_state()

    def _init_game_state(self) -> None:
        self.phase = Phase.PLAYING
        self.grid: list[list[Stone | None]] = [[None] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.active_color: int = 0
        self.last_color: int = -1
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.heat: float = 0.0
        self.stones_placed: int = 0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.capture_pending: bool = False
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._spawn_timer: int = SPAWN_INTERVAL

        # Place initial neutral stones
        self._place_initial_stones()

    def _place_initial_stones(self) -> None:
        positions = [(c, r) for r in range(GRID_SIZE) for c in range(GRID_SIZE)]
        self._rng.shuffle(positions)
        for i in range(min(INITIAL_STONES, len(positions))):
            col, row = positions[i]
            color = self._rng.randint(0, 3)
            self.grid[row][col] = Stone(color, col, row)
            self.stones_placed += 1

    # ── Input Helpers ──────────────────────────────────────────────────────
    @staticmethod
    def _confirm_pressed() -> bool:
        return pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE)

    @staticmethod
    def _click_pressed() -> bool:
        return pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)

    # ── Text Helpers ───────────────────────────────────────────────────────
    def _text(self, s: str, x: int, y: int, col: int) -> None:
        if self._font is not None:
            pyxel.text(x + 1, y + 1, s, BLACK, self._font)
            pyxel.text(x, y, s, col, self._font)
        else:
            pyxel.text(x, y, s, col)

    def _text_center(self, s: str, y: int, col: int, scale: float = 1.0) -> None:
        if self._font is not None:
            w = self._font.text_width(s)
            x = (SCREEN_W - w) // 2
            pyxel.text(x + 1, y + 1, s, BLACK, self._font)
            pyxel.text(x, y, s, col, self._font)
        else:
            pyxel.text((SCREEN_W - len(s) * 4) // 2, y, s, col)

    # ── Coordinate Helpers ──────────────────────────────────────────────────
    @staticmethod
    def _screen_to_grid(sx: float, sy: float) -> tuple[int, int] | None:
        col = round((sx - OX) / CELL)
        row = round((sy - OY) / CELL)
        if 0 <= col < GRID_SIZE and 0 <= row < GRID_SIZE:
            return col, row
        return None

    @staticmethod
    def _grid_to_screen(col: int, row: int) -> tuple[int, int]:
        return OX + col * CELL, OY + row * CELL

    # ── Core Logic: Placement ───────────────────────────────────────────────
    def _place_stone(self, col: int, row: int) -> bool:
        """Place a stone of active_color at (col, row). Returns True if successful."""
        if self.grid[row][col] is not None:
            return False

        color = self.active_color
        self.grid[row][col] = Stone(color, col, row)
        self.stones_placed += 1

        # Combo tracking
        if self.last_color == color:
            self.combo += 1
        else:
            if self.last_color >= 0:
                self.heat = min(HEAT_MAX, self.heat + HEAT_PER_MISMATCH)
            self.combo = 1
        self.last_color = color
        self.max_combo = max(self.max_combo, self.combo)

        # SUPER activation
        if self.combo >= SUPER_THRESHOLD and not self.super_mode:
            self.super_mode = True
            self.super_timer = SUPER_DURATION
            sx, sy = self._grid_to_screen(col, row)
            self._spawn_floating_text(sx, sy - 16, "SUPER!", PINK, 50)

        # Capture trigger
        if self.combo >= COMBO_THRESHOLD:
            self.capture_pending = True

        return True

    # ── Core Logic: Capture ─────────────────────────────────────────────────
    def _process_capture(self) -> int:
        """BFS liberty-based capture. Returns number of stones captured."""
        captured = 0
        color = self.active_color

        if self.super_mode:
            # SUPER mode: capture all enemy groups adjacent to new stone
            captured = self._process_super_capture(color)
        else:
            captured = self._process_normal_capture(color)

        self.capture_pending = False
        return captured

    def _process_normal_capture(self, active_color: int) -> int:
        visited: set[tuple[int, int]] = set()
        total_captured = 0

        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                stone = self.grid[row][col]
                if stone is None or stone.color == active_color:
                    continue
                if (col, row) in visited:
                    continue
                group = self._bfs_group(col, row, stone.color)
                visited.update(group)
                liberties = self._count_liberties(group)
                if liberties == 0:
                    for gc, gr in group:
                        self.grid[gr][gc] = None
                        self.stones_placed -= 1
                    total_captured += len(group)
                    self._spawn_capture_effects(group, stone.color)

        if total_captured > 0:
            score_delta = total_captured * self.combo
            self.score += score_delta
            self._add_capture_score_text(total_captured, score_delta)
        return total_captured

    def _process_super_capture(self, active_color: int) -> int:
        """SUPER mode: capture ALL enemy groups (ignore liberties)."""
        visited: set[tuple[int, int]] = set()
        total_captured = 0

        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                stone = self.grid[row][col]
                if stone is None or stone.color == active_color:
                    continue
                if (col, row) in visited:
                    continue
                group = self._bfs_group(col, row, stone.color)
                visited.update(group)
                for gc, gr in group:
                    self.grid[gr][gc] = None
                    self.stones_placed -= 1
                total_captured += len(group)
                self._spawn_capture_effects(group, stone.color)

        if total_captured > 0:
            score_delta = total_captured * self.combo * 3
            self.score += score_delta
            self._add_capture_score_text(total_captured, score_delta)
        return total_captured

    def _bfs_group(self, start_col: int, start_row: int, target_color: int) -> set[tuple[int, int]]:
        """BFS: collect all connected stones of target_color."""
        group: set[tuple[int, int]] = set()
        queue: list[tuple[int, int]] = [(start_col, start_row)]
        group.add((start_col, start_row))

        while queue:
            col, row = queue.pop(0)
            for dc, dr in self._DIRS:
                nc, nr = col + dc, row + dr
                if not (0 <= nc < GRID_SIZE and 0 <= nr < GRID_SIZE):
                    continue
                if (nc, nr) in group:
                    continue
                stone = self.grid[nr][nc]
                if stone is not None and stone.color == target_color:
                    group.add((nc, nr))
                    queue.append((nc, nr))
        return group

    def _count_liberties(self, group: set[tuple[int, int]]) -> int:
        """Count unique empty adjacent intersections for a group."""
        liberties: set[tuple[int, int]] = set()
        for col, row in group:
            for dc, dr in self._DIRS:
                nc, nr = col + dc, row + dr
                if not (0 <= nc < GRID_SIZE and 0 <= nr < GRID_SIZE):
                    continue
                if self.grid[nr][nc] is None:
                    liberties.add((nc, nr))
        return len(liberties)

    # ── Core Logic: State Updates ───────────────────────────────────────────
    def _update_heat(self) -> bool:
        """Decay heat. Returns True if game over from heat."""
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            return True
        self.heat = max(0.0, self.heat - HEAT_DECAY)
        return False

    def _update_super(self) -> None:
        if not self.super_mode:
            return
        self.super_timer -= 1
        if self.super_timer <= 0:
            self.super_mode = False
            self.super_timer = 0

    def _spawn_neutral_stone(self) -> None:
        if self.stones_placed >= MAX_STONES:
            return
        empties = [
            (c, r) for r in range(GRID_SIZE) for c in range(GRID_SIZE)
            if self.grid[r][c] is None
        ]
        if not empties:
            return
        col, row = self._rng.choice(empties)
        color = self._rng.randint(0, 3)
        self.grid[row][col] = Stone(color, col, row)
        self.stones_placed += 1

    def _check_board_full(self) -> bool:
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                if self.grid[row][col] is None:
                    return False
        return True

    # ── Particles & Floating Text ───────────────────────────────────────────
    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=self._rng.randint(10, 25),
                color=color,
            ))

    def _spawn_super_particles(self, x: float, y: float) -> None:
        for _ in range(30):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(2.0, 5.0)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=self._rng.randint(15, 35),
                color=self._rng.choice(RAINBOW),
            ))

    def _spawn_capture_effects(self, group: set[tuple[int, int]], color: int) -> None:
        for col, row in group:
            cx, cy = self._grid_to_screen(col, row)
            self._spawn_particles(cx, cy, 6, color)

    def _add_capture_score_text(self, count: int, score_delta: int) -> None:
        # Use center of the grid area as default position
        cx = OX + 3 * CELL
        cy = OY + 3 * CELL
        self._spawn_floating_text(cx, cy - 20, f"+{score_delta}", YELLOW, 40)
        if count >= 3:
            self._spawn_floating_text(cx, cy - 34, f"x{count} CAPTURED!", CYAN, 45)

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int, life: int = 30) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, color=color, life=life))

    def _update_particles(self) -> None:
        survived: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                survived.append(p)
        self.particles = survived

    def _update_floating_texts(self) -> None:
        survived: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.life -= 1
            ft.y += ft.vy
            if ft.life > 0:
                survived.append(ft)
        self.floating_texts = survived

    # ── Update ──────────────────────────────────────────────────────────────
    def update(self) -> None:
        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()

        if self.phase == Phase.TITLE:
            self._update_title()
            return

        if self.phase == Phase.GAME_OVER:
            self._update_particles()
            self._update_floating_texts()
            self._update_game_over()
            return

        # ── PLAYING ──
        self._update_playing()

    def _update_title(self) -> None:
        if self._confirm_pressed() or self._click_pressed():
            self._init_game_state()

    def _update_playing(self) -> None:
        # Keyboard color select
        if pyxel.btnp(pyxel.KEY_1):
            self.active_color = 0
        elif pyxel.btnp(pyxel.KEY_2):
            self.active_color = 1
        elif pyxel.btnp(pyxel.KEY_3):
            self.active_color = 2
        elif pyxel.btnp(pyxel.KEY_4):
            self.active_color = 3
        elif pyxel.btnp(pyxel.KEY_R):
            self._init_game_state()
            return

        # Heat decay / game over
        if self._update_heat():
            return

        # SUPER timer
        self._update_super()

        # Mouse click to place stone
        if self._click_pressed():
            self._handle_click()

        # Capture processing
        if self.capture_pending:
            self._process_capture()

        # Neutral stone spawn
        self._spawn_timer -= 1
        if self._spawn_timer <= 0:
            self._spawn_timer = SPAWN_INTERVAL
            self._spawn_neutral_stone()

        # Board full check
        if self._check_board_full():
            self.phase = Phase.GAME_OVER

        self._update_particles()
        self._update_floating_texts()

    def _handle_click(self) -> None:
        gpos = self._screen_to_grid(pyxel.mouse_x, pyxel.mouse_y)
        if gpos is None:
            # Check color palette clicks
            self._check_palette_click(pyxel.mouse_x, pyxel.mouse_y)
            return
        col, row = gpos
        if self._place_stone(col, row):
            sx, sy = self._grid_to_screen(col, row)
            pcolor = STONE_COLORS[self.active_color]
            if self.super_mode:
                self._spawn_super_particles(sx, sy)
            else:
                self._spawn_particles(sx, sy, 8, pcolor)
            if self.combo >= 2:
                combo_text = f"x{self.combo}" if self.combo < SUPER_THRESHOLD else f"x{self.combo}!"
                self._spawn_floating_text(sx, sy - 14, combo_text, YELLOW, 25)

    def _check_palette_click(self, mx: int, my: int) -> None:
        # Color palette at bottom
        palette_y = OY + 6 * CELL + 20
        btn_size = 24
        gap = 8
        total_w = 4 * btn_size + 3 * gap
        start_x = (SCREEN_W - total_w) // 2

        for i in range(4):
            bx = start_x + i * (btn_size + gap)
            if bx <= mx <= bx + btn_size and palette_y <= my <= palette_y + btn_size:
                self.active_color = i
                break

    def _update_game_over(self) -> None:
        if self._confirm_pressed() or self._click_pressed():
            self._init_game_state()

    # ── Draw ────────────────────────────────────────────────────────────────
    def draw(self) -> None:
        pyxel.cls(NAVY)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        self._draw_grid()
        self._draw_stones()
        self._draw_hover()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_ui()

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over_overlay()

    def _draw_title(self) -> None:
        self._text_center("LIBERTY CHAIN", 30, CYAN)
        self._text_center("Go-like Territory Capture", 58, WHITE)
        self._text_center("Place same-color stones", 80, GRAY)
        self._text_center("to build COMBO chains.", 93, GRAY)
        self._text_center("COMBO >=3: BFS Liberty Capture", 115, YELLOW)
        self._text_center("COMBO >=5: SUPER STONE Mode!", 128, PINK)
        self._text_center("Wrong color: +HEAT", 150, ORANGE)
        self._text_center("HEAT 100 = Game Over", 163, RED)
        self._text_center("Keys 1/2/3/4: Select Color", 188, GRAY)
        self._text_center("Click grid: Place Stone", 201, GRAY)
        self._text_center("R: Restart", 214, GRAY)
        self._text_center("ENTER or Click to Start", 232, LIME)

    def _draw_grid(self) -> None:
        # Grid lines
        for i in range(GRID_SIZE):
            # Horizontal
            y = OY + i * CELL
            pyxel.line(OX, y, OX + (GRID_SIZE - 1) * CELL, y, GRAY)

            # Vertical
            x = OX + i * CELL
            pyxel.line(x, OY, x, OY + (GRID_SIZE - 1) * CELL, GRAY)

        # Intersection dots
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                cx, cy = self._grid_to_screen(col, row)
                pyxel.pset(cx, cy, WHITE)

        # Border
        pyxel.rectb(
            OX - 2, OY - 2,
            (GRID_SIZE - 1) * CELL + 4,
            (GRID_SIZE - 1) * CELL + 4,
            WHITE,
        )

    def _draw_stones(self) -> None:
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                stone = self.grid[row][col]
                if stone is None:
                    continue
                cx, cy = self._grid_to_screen(col, row)

                # SUPER mode rainbow cycling for stones of active color
                if self.super_mode and stone.color == self.active_color:
                    idx = (pyxel.frame_count // 4) % len(RAINBOW)
                    color_idx = RAINBOW[idx]
                    # Draw glow
                    glow_r = STONE_RADIUS + 2 + (pyxel.frame_count % 8) // 4
                    pyxel.circb(cx, cy, glow_r, PINK)
                    pyxel.circ(cx, cy, STONE_RADIUS, color_idx)
                    pyxel.circb(cx, cy, STONE_RADIUS, WHITE)
                else:
                    pyxel.circ(cx, cy, STONE_RADIUS, STONE_COLORS[stone.color])
                    pyxel.circb(cx, cy, STONE_RADIUS, WHITE)

    def _draw_hover(self) -> None:
        if self.phase != Phase.PLAYING:
            return
        gpos = self._screen_to_grid(pyxel.mouse_x, pyxel.mouse_y)
        if gpos is None:
            return
        col, row = gpos
        if self.grid[row][col] is not None:
            return
        cx, cy = self._grid_to_screen(col, row)
        if self.super_mode:
            idx = (pyxel.frame_count // 4) % len(RAINBOW)
            hcolor = RAINBOW[idx]
        else:
            hcolor = STONE_COLORS[self.active_color]
        # Pulsing dot
        pulse = (pyxel.frame_count % 20) / 10.0
        radius = int(3 + pulse * 3)
        pyxel.circb(cx, cy, radius, hcolor)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 25
            if alpha < 0.1:
                continue
            col = p.color if alpha > 0.3 else GRAY
            pyxel.pset(int(p.x), int(p.y), col)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 40
            col = ft.color if alpha > 0.2 else GRAY
            if self._font is not None:
                pyxel.text(int(ft.x) + 1, int(ft.y) + 1, ft.text, BLACK, self._font)
                pyxel.text(int(ft.x), int(ft.y), ft.text, col, self._font)
            else:
                pyxel.text(int(ft.x), int(ft.y), ft.text, col)

    def _draw_ui(self) -> None:
        # Top info bar
        self._text(f"SCORE: {self.score}", 4, 2, WHITE)

        # Combo
        if self.super_mode:
            idx = (pyxel.frame_count // 4) % len(RAINBOW)
            combo_col = RAINBOW[idx]
        elif self.combo >= COMBO_THRESHOLD:
            combo_col = YELLOW
        elif self.combo > 0:
            combo_col = GRAY
        else:
            combo_col = GRAY
        self._text(f"COMBO: x{self.combo}", 4, 10, combo_col)

        # Heat bar (top-right)
        bar_w = 100
        bar_h = 5
        bar_x = SCREEN_W - bar_w - 4
        bar_y = 4
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        ratio = min(1.0, self.heat / HEAT_MAX)
        fill_w = int(bar_w * ratio)
        heat_col = PINK if ratio > 0.8 else (ORANGE if ratio > 0.5 else YELLOW)
        if fill_w > 0:
            pyxel.rect(bar_x, bar_y, fill_w, bar_h, heat_col)

        self._text("HEAT", bar_x - 24, bar_y - 1, ORANGE)
        self._text(f"{self.heat:.0f}", bar_x + bar_w + 4, bar_y - 1, heat_col)

        # SUPER mode timer
        if self.super_mode:
            sec = self.super_timer / FPS
            idx = (pyxel.frame_count // 4) % len(RAINBOW)
            self._text(f"SUPER: {sec:.1f}s", 4, 22, RAINBOW[idx])

        # Max combo
        self._text(f"MAX COMBO: x{self.max_combo}", 4, 228, GRAY)

        # Color palette buttons at bottom
        self._draw_color_palette()

        # Active color indicator
        palette_y = OY + 6 * CELL + 20
        btn_size = 24
        gap = 8
        total_w = 4 * btn_size + 3 * gap
        start_x = (SCREEN_W - total_w) // 2
        y = palette_y - 16
        pyxel.text(start_x - 6, y, ">", WHITE)
        self._text(COLOR_NAMES[self.active_color], start_x + 4, y, STONE_COLORS[self.active_color])

    def _draw_color_palette(self) -> None:
        palette_y = OY + 6 * CELL + 20
        btn_size = 24
        gap = 8
        total_w = 4 * btn_size + 3 * gap
        start_x = (SCREEN_W - total_w) // 2

        for i in range(4):
            bx = start_x + i * (btn_size + gap)
            by = palette_y
            # Button body
            pyxel.rect(bx, by, btn_size, btn_size, STONE_COLORS[i])
            if i == self.active_color:
                pyxel.rectb(bx - 2, by - 2, btn_size + 4, btn_size + 4, WHITE)
            else:
                pyxel.rectb(bx, by, btn_size, btn_size, WHITE)

            # Number label
            label = str(i + 1)
            if self._font is not None:
                lw = self._font.text_width(label)
                pyxel.text(bx + (btn_size - lw) // 2 + 1, by + 2, label, BLACK, self._font)
                pyxel.text(bx + (btn_size - lw) // 2, by + 1, label, WHITE, self._font)
            else:
                pyxel.text(bx + btn_size // 2 - 1, by + 2, label, WHITE)

    def _draw_game_over_overlay(self) -> None:
        # Dim
        for y in range(0, SCREEN_H, 2):
            for x in range(0, SCREEN_W, 2):
                if (x // 2 + y // 2) % 2 == 0:
                    pyxel.pset(x, y, BLACK)

        # Panel
        px, py, pw, ph = 60, 70, 200, 90
        pyxel.rect(px, py, pw, ph, BLACK)
        pyxel.rectb(px, py, pw, ph, WHITE)

        self._text_center("GAME OVER", py + 10, RED)
        self._text_center(f"SCORE: {self.score}", py + 30, WHITE)
        self._text_center(f"MAX COMBO: x{self.max_combo}", py + 45, YELLOW)
        self._text_center("ENTER or Click to Retry", py + 65, LIME)


# ── Test Helper ────────────────────────────────────────────────────────────────
def _make_game(rng: random.Random | None = None) -> Game:
    """Create a minimal Game instance for testing (no pyxel.init/run)."""
    g = Game.__new__(Game)
    g._font = None
    g.reset()
    g._rng = rng if rng is not None else random.Random(42)
    return g


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
