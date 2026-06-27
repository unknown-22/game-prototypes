"""168_magnet_chain — Color-match magnet grid puzzle with combo chain and CA field propagation."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


# === Color Constants (raw ints for pyxel compatibility) ===
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

GRID_COLORS = (RED, GREEN, LIGHT_BLUE, YELLOW)


# === Enums ===
class Phase(Enum):
    TITLE = auto()
    PLACING = auto()
    ANIM = auto()
    FIELD_PROPAGATE = auto()
    GAME_OVER = auto()


# === Data Classes ===
@dataclass
class Magnet:
    col: int
    row: int
    color: int
    polarity: int  # 0=N, 1=S
    field_strength: float = 0.0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


# === Main Game Class ===
class Game:
    GRID_COLS = 8
    GRID_ROWS = 6
    CELL = 30
    GRID_X = 40
    GRID_Y = 30
    NUM_COLORS = 4
    SUPER_DURATION = 300
    HEAT_MAX = 200
    HEAT_UNSTABLE = 100
    GAME_TIME = 60 * 60
    COMBO_THRESHOLD = 4
    FIELD_TICK_INTERVAL = 15
    BASE_REPEL = 120.0
    BASE_ATTRACT = 80.0
    ATTRACT_THRESHOLD = 0.3
    HEAT_PER_MISMATCH = 10.0
    HEAT_DECAY = 0.02
    SCORE_PER_PLACEMENT = 100
    SCORE_COMBO_BONUS = 50
    SCORE_MISMATCH = -10
    SUPER_MULTIPLIER = 3

    def __init__(self) -> None:
        pyxel.init(320, 240, title="MAGNET CHAIN", display_scale=2)
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.active_color: int = 0
        self.heat: float = 0.0
        self.super_timer: int = 0
        self.game_timer: int = self.GAME_TIME
        self.polarity_counter: int = 0
        self.total_placed: int = 0
        self.magnets: list[Magnet] = []
        self.field_strength: list[list[float]] = [
            [0.0] * self.GRID_COLS for _ in range(self.GRID_ROWS)
        ]
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._shake_frames: int = 0
        self._field_tick: int = 0
        self._last_placed_color: int | None = None
        self._spawn_initial_magnets()

    @staticmethod
    def _make_game() -> Game:
        """Factory for headless tests. Caller must call reset() after seeding _rng."""
        g = Game.__new__(Game)
        g._rng = random.Random()
        g.phase = Phase.TITLE
        g.score = 0
        g.combo = 0
        g.max_combo = 0
        g.active_color = 0
        g.heat = 0.0
        g.super_timer = 0
        g.game_timer = Game.GAME_TIME
        g.polarity_counter = 0
        g.total_placed = 0
        g.magnets = []
        g.field_strength = [[0.0] * Game.GRID_COLS for _ in range(Game.GRID_ROWS)]
        g.particles = []
        g.floating_texts = []
        g._shake_frames = 0
        g._field_tick = 0
        g._last_placed_color = None
        return g

    # --- Cell helpers ---
    def _get_cell_center(self, col: int, row: int) -> tuple[float, float]:
        return (
            self.GRID_X + col * self.CELL + self.CELL / 2,
            self.GRID_Y + row * self.CELL + self.CELL / 2,
        )

    def _is_cell_empty(self, col: int, row: int) -> bool:
        return self._get_magnet_at(col, row) is None

    def _is_cell_in_bounds(self, col: int, row: int) -> bool:
        return 0 <= col < self.GRID_COLS and 0 <= row < self.GRID_ROWS

    def _get_magnet_at(self, col: int, row: int) -> Magnet | None:
        for m in self.magnets:
            if m.col == col and m.row == row:
                return m
        return None

    # --- Initial placement ---
    def _spawn_initial_magnets(self) -> None:
        center_cols = {self.GRID_COLS // 2 - 1, self.GRID_COLS // 2}
        center_rows = {self.GRID_ROWS // 2 - 1, self.GRID_ROWS // 2}
        placed = 0
        attempts = 0
        while placed < 3 and attempts < 200:
            attempts += 1
            col = self._rng.randint(0, self.GRID_COLS - 1)
            row = self._rng.randint(0, self.GRID_ROWS - 1)
            if col in center_cols and row in center_rows:
                continue
            if not self._is_cell_empty(col, row):
                continue
            color = self._rng.randint(0, self.NUM_COLORS - 1)
            polarity = self.polarity_counter % 2
            self.polarity_counter += 1
            m = Magnet(col=col, row=row, color=color, polarity=polarity)
            self.magnets.append(m)
            placed += 1

    # --- Combo ---
    def _check_combo(self, color: int) -> bool:
        if self._last_placed_color is None:
            return False
        return color == self._last_placed_color

    def _is_super_active(self) -> bool:
        return self.super_timer > 0

    # --- Placement ---
    def _place_magnet(self, col: int, row: int) -> int:
        """Place a magnet at the given cell. Returns score gained."""
        if not self._is_cell_in_bounds(col, row):
            return 0
        if not self._is_cell_empty(col, row):
            return 0

        color = self.active_color

        # Combo check
        is_combo = self._check_combo(color)
        if self._last_placed_color is None:
            self.combo = 1
        elif is_combo:
            self.combo += 1
        else:
            self.combo = 0

        self._last_placed_color = color
        self.total_placed += 1
        self.max_combo = max(self.max_combo, self.combo)

        # Heat
        prev_color_existed = self.total_placed > 1
        if prev_color_existed and not is_combo:
            self.heat = min(self.heat + self.HEAT_PER_MISMATCH, float(self.HEAT_MAX))

        # Polarity
        polarity = self.polarity_counter % 2
        self.polarity_counter += 1

        # Create magnet
        m = Magnet(col=col, row=row, color=color, polarity=polarity)
        self.magnets.append(m)

        # Score and effects
        cx, cy = self._get_cell_center(col, row)

        if self._is_super_active():
            base_score = self.SCORE_PER_PLACEMENT * self.SUPER_MULTIPLIER
            self.score += base_score
            self._add_particles(cx, cy, 20, color)
            self._add_floating_text(cx, cy - 10, f"+{base_score}", YELLOW)
            if self.combo >= 2:
                self._add_floating_text(cx, cy - 22, f"COMBO x{self.combo}!", CYAN)
            return base_score

        if is_combo:
            score_gain = self.SCORE_PER_PLACEMENT + self.SCORE_COMBO_BONUS * self.combo
            self.score += score_gain
            self._add_particles(cx, cy, 6, color)
            self._add_floating_text(cx, cy - 10, f"+{score_gain}", WHITE)
            if self.combo >= 2:
                self._add_floating_text(cx, cy - 22, f"COMBO x{self.combo}!", CYAN)

            # Check SUPER FIELD activation
            if self.combo >= self.COMBO_THRESHOLD:
                self._activate_super(cx, cy)
        else:
            self.score += self.SCORE_PER_PLACEMENT
            if self.total_placed > 1:
                self._add_particles(cx, cy, 4, BROWN)
                self._add_floating_text(cx, cy - 10, "MISMATCH!", RED)
            self._add_particles(cx, cy, 4, color)

        # Check game over by heat
        if self.heat >= self.HEAT_MAX:
            self.phase = Phase.GAME_OVER
            return self.SCORE_PER_PLACEMENT

        return self.SCORE_PER_PLACEMENT + (
            self.SCORE_COMBO_BONUS * self.combo if is_combo else 0
        )

    # --- Super Field ---
    def _activate_super(self, x: float, y: float) -> None:
        self.super_timer = self.SUPER_DURATION
        self._add_particles(x, y, 25, -1)  # -1 = rainbow
        self._add_floating_text(x, y - 34, "SUPER FIELD!", YELLOW)
        self._shake_frames = 10

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer == 0:
                for m in self.magnets:
                    cx, cy = self._get_cell_center(m.col, m.row)
                    self._add_particles(cx, cy, 6, m.color)

    # --- Field propagation (CA) ---
    def _update_field_propagation(self) -> None:
        self._field_tick += 1
        tick_interval = 1 if self._is_super_active() else self.FIELD_TICK_INTERVAL
        if self._field_tick % tick_interval != 0:
            return

        new_field = [[0.0] * self.GRID_COLS for _ in range(self.GRID_ROWS)]

        for m in self.magnets:
            new_field[m.row][m.col] = max(new_field[m.row][m.col], 1.0)

        # Spread to neighbors (4-directional)
        spreads = 2 if self._is_super_active() else 1
        for _ in range(spreads):
            prev = [row[:] for row in new_field]
            for row in range(self.GRID_ROWS):
                for col in range(self.GRID_COLS):
                    if prev[row][col] > 0.01:
                        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                            nr, nc = row + dr, col + dc
                            if 0 <= nr < self.GRID_ROWS and 0 <= nc < self.GRID_COLS:
                                new_field[nr][nc] = max(
                                    new_field[nr][nc], prev[row][col] * 0.5
                                )

        self.field_strength = new_field

    # --- Magnetic forces ---
    def _apply_magnetic_forces(self) -> None:
        """Apply attraction/repulsion based on color and polarity."""
        unstable = self.heat >= self.HEAT_UNSTABLE and not self._is_super_active()
        for i, m1 in enumerate(self.magnets):
            for j, m2 in enumerate(self.magnets):
                if i >= j:
                    continue
                dc = abs(m1.col - m2.col)
                dr = abs(m1.row - m2.row)
                dist = max(dc, dr)
                if dist > 2 or dist == 0:
                    continue

                # Random polarity flip when unstable
                if unstable and self._rng.random() < 0.02 * self.heat / self.HEAT_MAX:
                    m1.polarity = 1 - m1.polarity

                same_color = m1.color == m2.color
                same_polarity = m1.polarity == m2.polarity
                force_scale = 1.0 / (dist * dist)

                if same_color:
                    if same_polarity:
                        m1.field_strength += force_scale * 0.1
                        m2.field_strength += force_scale * 0.1
                    else:
                        avg_strength = (m1.field_strength + m2.field_strength) / 2
                        m1.field_strength = avg_strength
                        m2.field_strength = avg_strength

    # --- Particles ---
    def _add_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            angle = self._rng.random() * 2 * math.pi
            speed = self._rng.uniform(1.0, 3.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            if color == -1:
                pc = self._rng.choice(list(GRID_COLORS))
            else:
                pc = color
            life = self._rng.randint(15, 30)
            self.particles.append(
                Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=pc)
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # --- Floating text ---
    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=40, color=color)
        )

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # --- Update ---
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLACING:
            self._update_placing()
        elif self.phase == Phase.ANIM:
            self._update_anim()
        elif self.phase == Phase.FIELD_PROPAGATE:
            self._update_field_phase()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

        self._update_particles()
        self._update_floating_texts()
        if self._shake_frames > 0:
            self._shake_frames -= 1

    def _update_title(self) -> None:
        if (
            pyxel.btnp(pyxel.KEY_RETURN)
            or pyxel.btnp(pyxel.KEY_Z)
            or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
        ):
            self.reset()
            self.phase = Phase.PLACING

    def _update_placing(self) -> None:
        self.game_timer -= 1
        if self.game_timer <= 0:
            self.game_timer = 0
            self.phase = Phase.GAME_OVER
            return

        self.heat = max(0.0, self.heat - self.HEAT_DECAY)
        if self.heat >= self.HEAT_MAX:
            self.phase = Phase.GAME_OVER
            return

        self._update_super()
        self._update_field_propagation()
        self._apply_magnetic_forces()

        if pyxel.btnp(pyxel.KEY_SPACE):
            self.active_color = (self.active_color + 1) % self.NUM_COLORS

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx, my = pyxel.mouse_x, pyxel.mouse_y

            # Check palette click
            if mx >= 280 and mx <= 310 and 30 <= my <= 190:
                idx = (my - 30) // 40
                if 0 <= idx < self.NUM_COLORS:
                    self.active_color = idx
                    return

            # Check grid click
            col = int((mx - self.GRID_X) / self.CELL)
            row = int((my - self.GRID_Y) / self.CELL)
            if self._is_cell_in_bounds(col, row) and self._is_cell_empty(col, row):
                self._place_magnet(col, row)

    def _update_anim(self) -> None:
        self.phase = Phase.PLACING

    def _update_field_phase(self) -> None:
        self.phase = Phase.PLACING

    def _update_game_over(self) -> None:
        if (
            pyxel.btnp(pyxel.KEY_RETURN)
            or pyxel.btnp(pyxel.KEY_Z)
            or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
        ):
            self.reset()
            self.phase = Phase.PLACING

    # --- Draw ---
    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self._shake_frames > 0:
            ox = self._rng.randint(-2, 2)
            oy = self._rng.randint(-2, 2)
            try:
                pyxel.camera(ox, oy)
            except Exception:
                pass
        else:
            try:
                pyxel.camera(0, 0)
            except Exception:
                pass

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.PLACING, Phase.ANIM, Phase.FIELD_PROPAGATE):
            self._draw_grid()
            self._draw_field()
            self._draw_particles()
            self._draw_floating_texts()
            self._draw_ui()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = "MAGNET CHAIN"
        pyxel.text(160 - len(title) * 4 // 2, 50, title, YELLOW)

        lines = [
            "Place same-color magnets to build COMBO!",
            "",
            "COMBO>=4 triggers SUPER FIELD!",
            "",
            "Controls:",
            "  Click grid to place magnet",
            "  Click palette or SPACE to change color",
            "",
            "Press Z or click to start",
        ]
        y = 80
        for line in lines:
            if line:
                col = (
                    WHITE
                    if "Controls" not in line and "Press" not in line
                    else GRAY
                )
                pyxel.text(30, y, line, col)
            y += 12

    def _draw_grid(self) -> None:
        gx, gy = self.GRID_X, self.GRID_Y

        for row in range(self.GRID_ROWS):
            for col in range(self.GRID_COLS):
                x = gx + col * self.CELL
                y = gy + row * self.CELL

                # Cell border
                pyxel.rectb(x, y, self.CELL, self.CELL, DARK_BLUE)

                # Field strength glow
                fs = self.field_strength[row][col]
                if fs > 0.05:
                    glow = min(int(fs * 3 + 1), 5)
                    pyxel.rectb(x, y, self.CELL, self.CELL, glow)

                # Draw magnet
                magnet = self._get_magnet_at(col, row)
                if magnet:
                    cx, cy = self._get_cell_center(col, row)
                    r = 11

                    if self._is_super_active():
                        pulse_idx = (pyxel.frame_count // 6 + col + row) % 4
                        pulse_col = GRID_COLORS[pulse_idx]
                        pyxel.circb(cx, cy, r + 2, pulse_col)
                        pyxel.circ(cx, cy, r, magnet.color)
                    else:
                        pyxel.circ(cx, cy, r, magnet.color)

                    # Polarity label
                    polarity_char = "N" if magnet.polarity == 0 else "S"
                    pol_color = WHITE if magnet.polarity == 0 else BLACK
                    pyxel.text(cx - 3, cy - 5, polarity_char, pol_color)

        # Field lines between adjacent same-color magnets
        if self._is_super_active():
            for i, m1 in enumerate(self.magnets):
                for m2 in self.magnets[i + 1 :]:
                    if m1.color == m2.color:
                        dc = abs(m1.col - m2.col)
                        dr = abs(m1.row - m2.row)
                        if dc + dr == 1:
                            x1, y1 = self._get_cell_center(m1.col, m1.row)
                            x2, y2 = self._get_cell_center(m2.col, m2.row)
                            pyxel.line(int(x1), int(y1), int(x2), int(y2), YELLOW)

    def _draw_field(self) -> None:
        gx, gy = self.GRID_X, self.GRID_Y
        for row in range(self.GRID_ROWS):
            for col in range(self.GRID_COLS):
                fs = self.field_strength[row][col]
                if fs > 0.1 and self._is_cell_empty(col, row):
                    alpha = min(int(fs * 8), 5)
                    x = gx + col * self.CELL + self.CELL // 2
                    y = gy + row * self.CELL + self.CELL // 2
                    pyxel.rect(x - 2, y - 2, 4, 4, alpha)

    def _draw_particles(self) -> None:
        for pt in self.particles:
            alpha = min(pt.life / 15, 3)
            if alpha <= 0:
                continue
            sz = max(1, int(pt.size * pt.life / 30))
            pyxel.rect(int(pt.x) - sz, int(pt.y) - sz, sz * 2, sz * 2, int(alpha) + 1)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life > 0:
                pyxel.text(
                    int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color
                )

    def _draw_ui(self) -> None:
        # Right panel background
        pyxel.rect(280, 0, 40, 240, NAVY)

        # Title on side panel
        pyxel.text(283, 5, "MAGNET", YELLOW)
        pyxel.text(283, 13, "CHAIN", YELLOW)

        # Score
        pyxel.text(283, 30, "SCORE", GRAY)
        pyxel.text(283, 38, f"{self.score}", WHITE)

        # Combo
        pyxel.text(283, 50, "COMBO", GRAY)
        combo_col = YELLOW if self._is_super_active() else WHITE
        pyxel.text(283, 58, f"{self.combo}", combo_col)

        # Max combo
        pyxel.text(283, 70, "MAX", GRAY)
        pyxel.text(283, 78, f"{self.max_combo}", WHITE)

        # Timer
        pyxel.text(283, 90, "TIME", GRAY)
        secs = self.game_timer // 60
        timer_col = RED if secs <= 10 else WHITE
        pyxel.text(283, 98, f"{secs}s", timer_col)

        # Super indicator
        if self._is_super_active():
            pyxel.text(280, 110, "SUPER!", YELLOW)
            pyxel.text(280, 118, f"{self.super_timer // 60}", CYAN)

        # Color palette
        pyxel.text(283, 135, "COLOR", GRAY)
        for i, color in enumerate(GRID_COLORS):
            py = 150 + i * 15
            pyxel.rect(285, py, 10, 10, color)
            if i == self.active_color:
                pyxel.rectb(284, py - 1, 12, 12, WHITE)

        # Magnet count
        pyxel.text(283, 215, "MGNTS", GRAY)
        pyxel.text(288, 223, f"{len(self.magnets)}", WHITE)

        # Heat bar at bottom
        bar_x, bar_y, bar_w, bar_h = 10, 225, 260, 8
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        heat_fill = int(self.heat / self.HEAT_MAX * bar_w)
        heat_color = (
            GREEN if self.heat < 50 else (YELLOW if self.heat < 100 else RED)
        )
        pyxel.rect(bar_x, bar_y, heat_fill, bar_h, heat_color)
        pyxel.text(bar_x + 2, bar_y - 6, "HEAT", GRAY)

        # Top status bar
        pyxel.text(10, 5, "MAGNET CHAIN", YELLOW)

    def _draw_game_over(self) -> None:
        pyxel.text(120, 40, "GAME OVER", RED)

        death_reason = (
            "Time Up!" if self.game_timer <= 0 else "Magnetic Overload!"
        )
        pyxel.text(120, 60, death_reason, WHITE)

        pyxel.text(80, 90, f"FINAL SCORE: {self.score}", YELLOW)
        pyxel.text(80, 110, f"MAX COMBO: {self.max_combo}", CYAN)
        pyxel.text(80, 130, f"MAGNETS PLACED: {self.total_placed}", WHITE)

        pyxel.text(70, 170, "Press Z or click to restart", GRAY)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
