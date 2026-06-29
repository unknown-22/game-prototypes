from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel

# ── Color constants ──────────────────────────────────────────────
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

PEG_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
SUPER_RAINBOW_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]

# ── Board constants ──────────────────────────────────────────────
CELL = 30
BOARD_OFFSET_X = 55
BOARD_OFFSET_Y = 30
PEG_RADIUS = 12

# ── Game balance ─────────────────────────────────────────────────
SUPER_DURATION = 150  # frames (5s at 30fps)
HEAT_DECAY = 0.05
HEAT_WRONG_COLOR = 15.0
HEAT_MAX = 100.0
COMBO_SUPER_THRESHOLD = 4
SUPER_SCORE_MULTIPLIER = 3.0
BASE_SCORE = 10
COMBO_SCORE_FACTOR = 0.5
PARTICLE_LIFE_MIN = 15
PARTICLE_LIFE_MAX = 30
FLOAT_TEXT_LIFE_MIN = 30
FLOAT_TEXT_LIFE_MAX = 45
SHAKE_FRAMES = 8
SHAKE_AMPLITUDE = 3
CAPTURE_PARTICLE_COUNT = 8
SUPER_BURST_PARTICLE_COUNT = 30


# ── Valid board cells (English peg solitaire cross) ──────────────
def _build_valid_cells() -> set[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    for r in range(7):
        for c in range(7):
            if r <= 1 or r >= 5:
                if 2 <= c <= 4:
                    cells.add((c, r))
            else:
                cells.add((c, r))
    return cells


VALID_CELLS: set[tuple[int, int]] = _build_valid_cells()


# ── Enums / Data ─────────────────────────────────────────────────
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Peg:
    col: int
    row: int
    color: int


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


# ── Game ─────────────────────────────────────────────────────────
class Game:
    W: ClassVar[int] = 320
    H: ClassVar[int] = 240

    def __init__(self) -> None:
        pyxel.init(self.W, self.H, title="PEG SURGE", display_scale=2)
        self._pegs: dict[tuple[int, int], Peg] = {}
        self._phase: Phase = Phase.TITLE
        self._score: int = 0
        self._combo: int = 0
        self._max_combo: int = 0
        self._heat: float = 0.0
        self._super_timer: int = 0
        self._selected_col: int | None = None
        self._selected_row: int | None = None
        self._last_captured_color: int | None = None
        self._particles: list[Particle] = []
        self._floating_texts: list[FloatingText] = []
        self._shake_frames: int = 0
        self._hover_col: int | None = None
        self._hover_row: int | None = None
        self._rng: random.Random = random.Random()
        self._rainbow_cycle: int = 0
        pyxel.run(self.update, self.draw)

    # ── Static helpers (testable, no pyxel) ──────────────────────
    @staticmethod
    def _is_valid_cell(col: int, row: int) -> bool:
        return (col, row) in VALID_CELLS

    @staticmethod
    def _is_adjacent(fc: int, fr: int, tc: int, tr: int) -> bool:
        dx = abs(tc - fc)
        dy = abs(tr - fr)
        return (dx == 2 and dy == 0) or (dx == 0 and dy == 2)

    @staticmethod
    def _middle_cell(fc: int, fr: int, tc: int, tr: int) -> tuple[int, int]:
        return ((fc + tc) // 2, (fr + tr) // 2)

    def _can_jump(self, fc: int, fr: int, tc: int, tr: int) -> bool:
        if not self._is_valid_cell(tc, tr):
            return False
        if (tc, tr) in self._pegs:
            return False
        if not self._is_adjacent(fc, fr, tc, tr):
            return False
        mid_c, mid_r = self._middle_cell(fc, fr, tc, tr)
        return (mid_c, mid_r) in self._pegs

    def _get_valid_moves(self, col: int, row: int) -> list[tuple[int, int]]:
        candidates = [
            (col - 2, row),
            (col + 2, row),
            (col, row - 2),
            (col, row + 2),
        ]
        return [(c, r) for c, r in candidates if self._can_jump(col, row, c, r)]

    def _all_valid_moves(self) -> list[tuple[int, int, int, int]]:
        results: list[tuple[int, int, int, int]] = []
        for (pc, pr) in self._pegs:
            for dc, dr in self._get_valid_moves(pc, pr):
                results.append((pc, pr, dc, dr))
        return results

    def _has_valid_moves(self) -> bool:
        return len(self._all_valid_moves()) > 0

    def _execute_jump(self, fc: int, fr: int, tc: int, tr: int) -> int:
        mid_c, mid_r = self._middle_cell(fc, fr, tc, tr)
        captured_peg = self._pegs.pop((mid_c, mid_r))
        capt_color = captured_peg.color
        moving_peg = self._pegs.pop((fc, fr))
        moving_peg.col = tc
        moving_peg.row = tr
        self._pegs[(tc, tr)] = moving_peg

        is_super = self._super_timer > 0
        if self._last_captured_color is not None:
            if is_super or capt_color == self._last_captured_color:
                self._combo += 1
                if self._combo > self._max_combo:
                    self._max_combo = self._combo
            else:
                self._combo = 0
                self._heat = min(self._heat + HEAT_WRONG_COLOR, HEAT_MAX + 10)

        self._last_captured_color = capt_color

        # Score
        multiplier = SUPER_SCORE_MULTIPLIER if is_super else 1.0
        combo_bonus = 1.0 + COMBO_SCORE_FACTOR * self._combo
        gained = int(BASE_SCORE * combo_bonus * multiplier)
        self._score += gained

        # SUPER trigger
        if self._combo >= COMBO_SUPER_THRESHOLD and self._super_timer == 0:
            self._activate_super()

        # Particles / floating text
        self._spawn_capture_particles(
            mid_c * CELL + BOARD_OFFSET_X + CELL // 2,
            mid_r * CELL + BOARD_OFFSET_Y + CELL // 2,
            capt_color,
            CAPTURE_PARTICLE_COUNT,
        )
        if is_super:
            self._spawn_super_particles(
                mid_c * CELL + BOARD_OFFSET_X + CELL // 2,
                mid_r * CELL + BOARD_OFFSET_Y + CELL // 2,
            )
        self._floating_texts.append(
            FloatingText(
                x=tc * CELL + BOARD_OFFSET_X + CELL // 2,
                y=tr * CELL + BOARD_OFFSET_Y + 10,
                text=f"+{gained}",
                life=self._rng.randint(FLOAT_TEXT_LIFE_MIN, FLOAT_TEXT_LIFE_MAX),
                color=YELLOW if is_super else WHITE,
            )
        )
        return gained

    def _activate_super(self) -> None:
        self._super_timer = SUPER_DURATION
        self._shake_frames = SHAKE_FRAMES
        self._rainbow_cycle = 0
        if self._selected_col is not None and self._selected_row is not None:
            cx = self._selected_col * CELL + BOARD_OFFSET_X + CELL // 2
            cy = self._selected_row * CELL + BOARD_OFFSET_Y + CELL // 2
            self._spawn_super_burst(cx, cy)

    def _deactivate_super(self) -> None:
        self._super_timer = 0

    def _spawn_capture_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            self._particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-1.5, 1.5),
                    vy=self._rng.uniform(-1.5, 1.5),
                    life=self._rng.randint(PARTICLE_LIFE_MIN, PARTICLE_LIFE_MAX),
                    color=color,
                )
            )

    def _spawn_super_particles(self, x: float, y: float) -> None:
        for _ in range(4):
            c = self._rng.choice(SUPER_RAINBOW_COLORS)
            self._particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-1.5, 1.5),
                    vy=self._rng.uniform(-1.5, 1.5),
                    life=self._rng.randint(PARTICLE_LIFE_MIN, PARTICLE_LIFE_MAX),
                    color=c,
                )
            )

    def _spawn_super_burst(self, x: float, y: float) -> None:
        for _ in range(SUPER_BURST_PARTICLE_COUNT):
            self._particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-3.0, 3.0),
                    vy=self._rng.uniform(-3.0, 3.0),
                    life=self._rng.randint(20, 40),
                    color=self._rng.choice(SUPER_RAINBOW_COLORS),
                )
            )

    def _update_particles(self) -> None:
        surviving: list[Particle] = []
        for p in self._particles:
            p.life -= 1
            if p.life <= 0:
                continue
            p.vy += 0.05  # gravity
            p.x += p.vx
            p.y += p.vy
            surviving.append(p)
        self._particles = surviving

    def _update_floating_texts(self) -> None:
        surviving: list[FloatingText] = []
        for ft in self._floating_texts:
            ft.life -= 1
            if ft.life <= 0:
                continue
            ft.y -= 0.6
            surviving.append(ft)
        self._floating_texts = surviving

    def _find_hovered_cell(self, mx: int, my: int) -> tuple[int, int] | None:
        for c in range(7):
            for r in range(7):
                if not self._is_valid_cell(c, r):
                    continue
                cx = c * CELL + BOARD_OFFSET_X + CELL // 2
                cy = r * CELL + BOARD_OFFSET_Y + CELL // 2
                dx = mx - cx
                dy = my - cy
                if dx * dx + dy * dy < PEG_RADIUS * PEG_RADIUS:
                    return (c, r)
        return None

    # ── State reset ──────────────────────────────────────────────
    def reset(self) -> None:
        self._score = 0
        self._combo = 0
        self._max_combo = 0
        self._heat = 0.0
        self._super_timer = 0
        self._selected_col = None
        self._selected_row = None
        self._last_captured_color = None
        self._particles.clear()
        self._floating_texts.clear()
        self._shake_frames = 0
        self._hover_col = None
        self._hover_row = None
        self._rainbow_cycle = 0
        self._pegs.clear()

        # Place 32 pegs, center (3,3) empty
        peg_positions: list[tuple[int, int]] = [
            (c, r) for (c, r) in VALID_CELLS if (c, r) != (3, 3)
        ]
        self._rng.shuffle(peg_positions)

        # Equal-ish distribution: 8 of each color across 32 pegs
        colors_pool = PEG_COLORS * 8  # 8 each = 32
        self._rng.shuffle(colors_pool)
        for (c, r), col in zip(peg_positions, colors_pool):
            self._pegs[(c, r)] = Peg(col=c, row=r, color=col)

    # ── Update dispatch ──────────────────────────────────────────
    def update(self) -> None:
        if self._phase == Phase.TITLE:
            self._update_title()
        elif self._phase == Phase.PLAYING:
            self._update_playing()
        elif self._phase == Phase.GAME_OVER:
            self._update_game_over()

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self._phase == Phase.TITLE:
            self._draw_title()
        elif self._phase == Phase.PLAYING:
            self._draw_playing()
        elif self._phase == Phase.GAME_OVER:
            self._draw_game_over()

    # ── Title ────────────────────────────────────────────────────
    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self._phase = Phase.PLAYING

    def _draw_title(self) -> None:
        pyxel.text(113, 50, "PEG SURGE", WHITE)
        pyxel.text(60, 80, "Click peg then empty hole to jump", GRAY)
        pyxel.text(38, 100, "Same color = COMBO!  COMBO>=4 = SUPER", GRAY)
        pyxel.text(30, 120, "Wrong color = HEAT!  HEAT>=100 = OVER", GRAY)
        pyxel.text(72, 160, "Press ENTER or click to start", WHITE)
        pyxel.text(60, 200, "Click peg, then click hole 2 away", GRAY)

    # ── Playing ──────────────────────────────────────────────────
    def _update_playing(self) -> None:
        self._update_particles()
        self._update_floating_texts()

        # Heat decay
        if self._heat > 0:
            self._heat = max(0.0, self._heat - HEAT_DECAY)

        # Shake countdown
        if self._shake_frames > 0:
            self._shake_frames -= 1

        # SUPER timer
        if self._super_timer > 0:
            self._super_timer -= 1
            self._rainbow_cycle = (self._rainbow_cycle + 1) % (len(SUPER_RAINBOW_COLORS) * 5)
            if self._super_timer == 0:
                self._deactivate_super()

        # Hover
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        cell = self._find_hovered_cell(mx, my)
        if cell is None:
            self._hover_col = None
            self._hover_row = None
        else:
            self._hover_col, self._hover_row = cell

        # Click handling
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._handle_click(mx, my)

        # Keyboard shortcuts
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            pyxel.quit()

        # Check game-over conditions
        if self._heat >= HEAT_MAX:
            self._phase = Phase.GAME_OVER
        elif not self._has_valid_moves():
            self._phase = Phase.GAME_OVER
        elif len(self._pegs) == 0:
            self._score += 500  # perfect bonus
            self._phase = Phase.GAME_OVER

    def _handle_click(self, mx: int, my: int) -> None:
        cell = self._find_hovered_cell(mx, my)
        if cell is None:
            self._selected_col = None
            self._selected_row = None
            return

        cc, cr = cell
        # Already have a peg selected
        if self._selected_col is not None and self._selected_row is not None:
            sc, sr = self._selected_col, self._selected_row
            if (cc, cr) == (sc, sr):
                # Deselect
                self._selected_col = None
                self._selected_row = None
                return
            if self._can_jump(sc, sr, cc, cr):
                self._execute_jump(sc, sr, cc, cr)
                # After jump, keep same peg selected for multi-jump
                self._selected_col = cc
                self._selected_row = cr
                return
            else:
                # Clicked a different peg -> select that one
                if (cc, cr) in self._pegs:
                    self._selected_col = cc
                    self._selected_row = cr
                else:
                    self._selected_col = None
                    self._selected_row = None
                return

        # No peg selected yet
        if (cc, cr) in self._pegs:
            self._selected_col = cc
            self._selected_row = cr
        else:
            self._selected_col = None
            self._selected_row = None

    def _draw_playing(self) -> None:
        # Camera shake
        shake_x = 0
        shake_y = 0
        if self._shake_frames > 0:
            shake_x = self._rng.randint(-SHAKE_AMPLITUDE, SHAKE_AMPLITUDE)
            shake_y = self._rng.randint(-SHAKE_AMPLITUDE, SHAKE_AMPLITUDE)

        pyxel.camera(shake_x, shake_y)

        # HUD bar background
        pyxel.rect(0, 0, self.W, 22, NAVY)

        # Score
        pyxel.text(5, 4, f"SCORE: {self._score:04d}", WHITE)
        # Combo
        combo_color = YELLOW if self._combo >= 3 else WHITE
        pyxel.text(130, 4, f"COMBO: {self._combo}", combo_color)
        # SUPER indicator
        if self._super_timer > 0:
            super_sec = self._super_timer // 30
            idx = (self._rainbow_cycle // 5) % len(SUPER_RAINBOW_COLORS)
            rainbow_color = SUPER_RAINBOW_COLORS[idx]
            pyxel.text(220, 4, f"SUPER {super_sec}s", rainbow_color)

        # HEAT bar
        heat_x = 5
        heat_y = 25
        heat_w = 100
        heat_h = 6
        pyxel.rect(heat_x, heat_y, heat_w, heat_h, DARK_BLUE)
        fill_w = int((self._heat / HEAT_MAX) * heat_w)
        if fill_w > 0:
            heat_bar_color = RED
            if self._heat >= 70:
                blink_on = (pyxel.frame_count // 15) % 2 == 0
                heat_bar_color = RED if blink_on else ORANGE
            pyxel.rect(heat_x, heat_y, fill_w, heat_h, heat_bar_color)

        # Board grid lines (subtle)
        for c in range(7):
            for r in range(7):
                if not self._is_valid_cell(c, r):
                    continue
                cx = c * CELL + BOARD_OFFSET_X
                cy = r * CELL + BOARD_OFFSET_Y
                pyxel.rectb(cx, cy, CELL, CELL, NAVY)

                peg_center_x = cx + CELL // 2
                peg_center_y = cy + CELL // 2

                if (c, r) in self._pegs:
                    peg = self._pegs[(c, r)]
                    peg_color = peg.color

                    # SUPER rainbow for selected peg
                    if (
                        self._super_timer > 0
                        and self._selected_col is not None
                        and self._selected_row is not None
                        and (c, r) == (self._selected_col, self._selected_row)
                    ):
                        idx = (self._rainbow_cycle // 5) % len(SUPER_RAINBOW_COLORS)
                        peg_color = SUPER_RAINBOW_COLORS[idx]

                    # Hover highlight
                    if (c, r) == (self._hover_col, self._hover_row):
                        peg_color = LIGHT_BLUE if peg_color == DARK_BLUE else peg_color + 0

                    # Draw peg
                    pyxel.circ(peg_center_x, peg_center_y, PEG_RADIUS, peg_color)
                    pyxel.circb(peg_center_x, peg_center_y, PEG_RADIUS, BLACK)
                else:
                    # Empty hole
                    pyxel.circb(peg_center_x, peg_center_y, PEG_RADIUS - 2, GRAY)
                    pyxel.circb(peg_center_x, peg_center_y, PEG_RADIUS - 1, GRAY)

        # Selection highlight
        if self._selected_col is not None and self._selected_row is not None:
            sc, sr = self._selected_col, self._selected_row
            sx = sc * CELL + BOARD_OFFSET_X + CELL // 2
            sy = sr * CELL + BOARD_OFFSET_Y + CELL // 2
            pyxel.circb(sx, sy, PEG_RADIUS + 2, WHITE)
            pyxel.circb(sx, sy, PEG_RADIUS + 3, WHITE)

            # Valid move destinations highlight
            if (sc, sr) in self._pegs:
                for dc, dr in self._get_valid_moves(sc, sr):
                    dx = dc * CELL + BOARD_OFFSET_X + CELL // 2
                    dy = dr * CELL + BOARD_OFFSET_Y + CELL // 2
                    pyxel.circb(dx, dy, PEG_RADIUS, WHITE)

        # Particles
        for p in self._particles:
            alpha_scale = p.life / max(PARTICLE_LIFE_MAX, 1)
            px = int(p.x)
            py_ = int(p.y)
            size = max(1, int(2 * alpha_scale))
            pyxel.rect(px, py_, size, size, p.color)

        # Floating texts
        for ft in self._floating_texts:
            alpha_scale = ft.life / max(FLOAT_TEXT_LIFE_MAX, 1)
            ft_color = ft.color
            if alpha_scale < 0.3:
                ft_color = GRAY
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft_color)

        pyxel.camera(0, 0)

    # ── Game Over ─────────────────────────────────────────────────
    def _update_game_over(self) -> None:
        self._update_particles()
        self._update_floating_texts()
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._phase = Phase.TITLE
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            pyxel.quit()

    def _draw_game_over(self) -> None:
        pyxel.text(100, 60, "GAME OVER", RED)
        pyxel.text(85, 90, f"SCORE: {self._score:04d}", WHITE)
        pyxel.text(85, 110, f"MAX COMBO: {self._max_combo}", YELLOW)
        pyxel.text(85, 130, f"PEGS LEFT: {len(self._pegs)}", GRAY)
        pyxel.text(55, 170, "Press ENTER or click to retry", WHITE)

        # Particles (leftover)
        for p in self._particles:
            alpha_scale = p.life / max(PARTICLE_LIFE_MAX, 1)
            px = int(p.x)
            py_ = int(p.y)
            size = max(1, int(2 * alpha_scale))
            pyxel.rect(px, py_, size, size, p.color)


# ── Entry point ──────────────────────────────────────────────────
if __name__ == "__main__":
    Game()
