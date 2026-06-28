"""Word Surge - Word-building puzzle with COMBO chain scoring."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# --- Constants ---
SCREEN_W = 320
SCREEN_H = 240
GRID_SIZE = 6
CELL = 30
GRID_X = 70
GRID_Y = 20
MIN_WORD_LEN = 3
SUPER_THRESHOLD = 4
SUPER_DURATION = 150
TIMER_MAX = 1800
HEAT_LOW_SCORE = 10.0
HEAT_HIGH_SCORE = -5.0
HEAT_MAX = 100.0

# --- Color Constants ---
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

TILE_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Tile:
    letter: str
    color: int
    row: int
    col: int


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


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, "WORD SURGE", display_scale=2)
        self.rng = random.Random()
        self.phase = Phase.TITLE
        self.grid: list[list[Tile | None]] = []
        self.selected: list[tuple[int, int]] = []
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.super_timer = 0
        self.words_found = 0
        self.heat = 0.0
        self.timer = TIMER_MAX
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.high_score = 0
        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    # --- State Initialization ---

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.super_timer = 0
        self.words_found = 0
        self.heat = 0.0
        self.timer = TIMER_MAX
        self.selected.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self._init_grid()

    def _init_grid(self) -> None:
        self.grid = []
        for row in range(GRID_SIZE):
            row_tiles: list[Tile | None] = []
            for col in range(GRID_SIZE):
                row_tiles.append(self._spawn_tile(row, col))
            self.grid.append(row_tiles)

    def _spawn_tile(self, row: int, col: int) -> Tile:
        letter = chr(ord("A") + self.rng.randint(0, 25))
        color = TILE_COLORS[ord(letter) % 4]
        return Tile(letter=letter, color=color, row=row, col=col)

    # --- Selection Logic ---

    def _is_adjacent(self, r1: int, c1: int, r2: int, c2: int) -> bool:
        return abs(r1 - r2) + abs(c1 - c2) == 1

    def _find_in_selected(self, row: int, col: int) -> int:
        for i, (r, c) in enumerate(self.selected):
            if r == row and c == col:
                return i
        return -1

    def _try_select(self, row: int, col: int) -> bool:
        if not (0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE):
            return False
        if self.grid[row][col] is None:
            return False

        idx = self._find_in_selected(row, col)
        if idx >= 0:
            # Deselect from this tile onward
            while len(self.selected) > idx:
                self.selected.pop()
            self._recalc_combo()
            return True

        if not self.selected:
            self.selected.append((row, col))
            self.combo = 1
            self.max_combo = max(self.max_combo, self.combo)
            self._check_super_activation()
            return True

        last_r, last_c = self.selected[-1]
        if self._is_adjacent(last_r, last_c, row, col):
            self.selected.append((row, col))
            self._recalc_combo()
            self._check_super_activation()
            return True

        return False

    def _recalc_combo(self) -> None:
        if not self.selected:
            self.combo = 0
            return
        current_streak = 0
        max_run = 0
        prev_color = -1
        super_active = self.super_timer > 0
        for r, c in self.selected:
            tile = self.grid[r][c]
            if tile is None:
                continue
            if not super_active and tile.color != prev_color:
                current_streak = 1
            else:
                current_streak += 1
            prev_color = tile.color
            if current_streak > max_run:
                max_run = current_streak
        self.combo = current_streak
        self.max_combo = max(self.max_combo, max_run)

    def _check_super_activation(self) -> None:
        if self.combo >= SUPER_THRESHOLD and self.super_timer <= 0:
            self.super_timer = SUPER_DURATION

    def _cancel_selection(self) -> None:
        self.selected.clear()
        self._recalc_combo()

    # --- Word Submission ---

    def _compute_score(self) -> tuple[int, float]:
        word_len = len(self.selected)
        base = word_len * 50

        c = self.combo
        multiplier = 1.0 + 0.5 * min(c, 8)

        if self.super_timer > 0:
            multiplier *= 3.0

        return int(base * multiplier), multiplier

    def _submit_word(self) -> int:
        if len(self.selected) < MIN_WORD_LEN:
            return 0

        score_earned, multiplier = self._compute_score()

        self.score += score_earned
        self.words_found += 1

        if self.score > self.high_score:
            self.high_score = self.score

        self._update_heat(score_earned, multiplier)

        # Spawn particles at cleared tile positions
        for r, c in self.selected:
            tile = self.grid[r][c]
            if tile is not None:
                px = GRID_X + c * CELL + CELL // 2
                py = GRID_Y + r * CELL + CELL // 2
                self._spawn_burst_particles(float(px), float(py), tile.color)

        # Floating text for score
        cx = GRID_X + GRID_SIZE * CELL // 2
        cy = GRID_Y + GRID_SIZE * CELL // 2
        self.floating_texts.append(
            FloatingText(
                x=float(cx),
                y=float(cy),
                text=f"+{score_earned}",
                life=45,
                color=YELLOW,
            )
        )

        self._clear_used_tiles()
        self._apply_gravity()
        self._spawn_new_tiles()
        self.selected.clear()
        self._recalc_combo()

        return score_earned

    def _update_heat(self, score_earned: int, multiplier: float) -> None:
        del score_earned
        if multiplier < 2.0:
            self.heat += HEAT_LOW_SCORE
        elif multiplier >= 3.0:
            self.heat += HEAT_HIGH_SCORE
        self.heat = max(0.0, min(self.heat, HEAT_MAX))

    # --- Grid Manipulation ---

    def _clear_used_tiles(self) -> None:
        for r, c in self.selected:
            if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
                self.grid[r][c] = None

    def _apply_gravity(self) -> None:
        for col in range(GRID_SIZE):
            write_row = GRID_SIZE - 1
            for row in range(GRID_SIZE - 1, -1, -1):
                tile = self.grid[row][col]
                if tile is not None:
                    if write_row != row:
                        self.grid[write_row][col] = tile
                        self.grid[row][col] = None
                        tile.row = write_row
                    write_row -= 1

    def _spawn_new_tiles(self) -> None:
        for col in range(GRID_SIZE):
            for row in range(GRID_SIZE):
                if self.grid[row][col] is None:
                    self.grid[row][col] = self._spawn_tile(row, col)

    # --- Update Methods ---

    def _update_timer(self) -> None:
        if self.timer > 0:
            self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER
            if self.score > self.high_score:
                self.high_score = self.score

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self._recalc_combo()

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 1.0
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # --- Particle / Effect Spawning ---

    def _spawn_burst_particles(self, x: float, y: float, color: int) -> None:
        count = self.rng.randint(4, 8)
        for _ in range(count):
            vx = self.rng.uniform(-1.5, 1.5)
            vy = self.rng.uniform(-2.0, 0.5)
            life = self.rng.randint(15, 30)
            self.particles.append(
                Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color)
            )

    def _spawn_super_particles(self) -> None:
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                tile = self.grid[r][c]
                if tile is not None and self.rng.random() < 0.2:
                    px = GRID_X + c * CELL + CELL // 2
                    py = GRID_Y + r * CELL + CELL // 2
                    rc = self.rng.choice(TILE_COLORS)
                    self.particles.append(
                        Particle(
                            x=float(px),
                            y=float(py),
                            vx=0.0,
                            vy=self.rng.uniform(-2.0, -1.0),
                            life=self.rng.randint(20, 40),
                            color=rc,
                        )
                    )

    # --- Main Update Loop ---

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        self._update_timer()
        self._update_super()

        if self.super_timer > 0 and self.rng.random() < 0.3:
            self._spawn_super_particles()

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            col = (mx - GRID_X) // CELL
            row = (my - GRID_Y) // CELL
            self._try_select(row, col)

        if pyxel.btnp(pyxel.KEY_RETURN):
            if len(self.selected) >= MIN_WORD_LEN:
                self._submit_word()

        if pyxel.btnp(pyxel.KEY_ESCAPE):
            self._cancel_selection()

        self._update_particles()
        self._update_floating_texts()

    # --- Drawing ---

    def draw(self) -> None:
        pyxel.cls(NAVY)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 32, 60, "WORD SURGE", WHITE)
        pyxel.rect(SCREEN_W // 2 - 40, 76, 80, 1, LIME)

        instructions = [
            "Click adjacent letter tiles",
            "to build words (3+ tiles)",
            "",
            "Same-color = COMBO chain",
            "COMBO x4 = SUPER WORD (3x)",
            "",
            "ENTER: Submit word",
            "ESC: Cancel selection",
            "",
            "PRESS SPACE OR ENTER",
        ]
        y = 95
        for line in instructions:
            if line:
                pyxel.text(SCREEN_W // 2 - len(line) * 2, y, line, LIME)
            y += 12

        if self.high_score > 0:
            pyxel.text(
                SCREEN_W // 2 - 30,
                215,
                f"HIGH SCORE: {self.high_score}",
                YELLOW,
            )

    def _draw_playing(self) -> None:
        # Timer bar
        timer_ratio = self.timer / TIMER_MAX
        timer_w = int(300 * timer_ratio)
        timer_color = GREEN if timer_ratio > 0.3 else (YELLOW if timer_ratio > 0.15 else RED)
        pyxel.rectb(9, 4, 302, 10, WHITE)
        pyxel.rect(10, 5, timer_w, 8, timer_color)

        # Grid background
        grid_w = GRID_SIZE * CELL
        grid_h = GRID_SIZE * CELL
        pyxel.rect(GRID_X - 2, GRID_Y - 2, grid_w + 4, grid_h + 4, WHITE)

        # SUPER WORD border
        if self.super_timer > 0:
            border_colors = [RED, ORANGE, YELLOW, LIME, GREEN, CYAN, DARK_BLUE, PURPLE]
            idx = (pyxel.frame_count // 4) % len(border_colors)
            pyxel.rectb(GRID_X - 3, GRID_Y - 3, grid_w + 6, grid_h + 6, border_colors[idx])
            pyxel.rectb(GRID_X - 4, GRID_Y - 4, grid_w + 8, grid_h + 8, border_colors[(idx + 2) % len(border_colors)])

        # Draw tiles
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                tile = self.grid[row][col]
                if tile is None:
                    continue
                x = GRID_X + col * CELL
                y = GRID_Y + row * CELL

                # Determine tile color
                draw_color = tile.color
                if self.super_timer > 0:
                    rainbow = [RED, ORANGE, YELLOW, LIME, GREEN, CYAN, DARK_BLUE, PURPLE]
                    draw_color = rainbow[(row * GRID_SIZE + col + pyxel.frame_count // 6) % len(rainbow)]

                is_selected = any(sr == row and sc == col for sr, sc in self.selected)
                is_last = bool(self.selected and self.selected[-1] == (row, col))

                if is_selected:
                    pyxel.rect(x, y, CELL, CELL, draw_color)
                    if is_last and (pyxel.frame_count // 15) % 2 == 0:
                        pyxel.rectb(x, y, CELL, CELL, WHITE)
                    else:
                        pyxel.rectb(x, y, CELL, CELL, WHITE)
                else:
                    pyxel.rect(x, y, CELL, CELL, draw_color)
                    pyxel.rectb(x, y, CELL, CELL, GRAY)

                # Letter
                letter_x = x + CELL // 2 - 2
                letter_y = y + CELL // 2 - 4
                pyxel.text(letter_x, letter_y, tile.letter, WHITE)

        # Connection lines between selected tiles
        if len(self.selected) >= 2:
            super_active = self.super_timer > 0
            for i in range(len(self.selected) - 1):
                r1, c1 = self.selected[i]
                r2, c2 = self.selected[i + 1]
                x1 = GRID_X + c1 * CELL + CELL // 2
                y1 = GRID_Y + r1 * CELL + CELL // 2
                x2 = GRID_X + c2 * CELL + CELL // 2
                y2 = GRID_Y + r2 * CELL + CELL // 2

                t1 = self.grid[r1][c1]
                t2 = self.grid[r2][c2]
                if super_active or (t1 and t2 and t1.color == t2.color):
                    line_color = WHITE
                else:
                    line_color = GRAY
                pyxel.line(x1, y1, x2, y2, line_color)

        # Particles
        for p in self.particles:
            alpha = p.life / 30.0
            if alpha > 0.3 or (p.life // 2) % 2 == 0:
                pyxel.pset(int(p.x), int(p.y), p.color)

        # Floating texts
        for ft in self.floating_texts:
            alpha = ft.life / 45.0
            if alpha > 0.2 or (ft.life // 3) % 2 == 0:
                pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

        # HUD
        self._draw_hud()

    def _draw_hud(self) -> None:
        # Score
        pyxel.text(GRID_X + GRID_SIZE * CELL + 12, GRID_Y + 5, "SCORE", WHITE)
        pyxel.text(GRID_X + GRID_SIZE * CELL + 12, GRID_Y + 15, f"{self.score}", YELLOW)

        # Words found
        pyxel.text(GRID_X + GRID_SIZE * CELL + 12, GRID_Y + 35, "WORDS", WHITE)
        pyxel.text(GRID_X + GRID_SIZE * CELL + 12, GRID_Y + 45, f"{self.words_found}", LIME)

        # COMBO
        combo_y = GRID_Y + GRID_SIZE * CELL + 5
        pyxel.text(GRID_X, combo_y, f"COMBO x{self.combo}", WHITE)
        if self.combo >= SUPER_THRESHOLD:
            pyxel.text(GRID_X + 80, combo_y, "!!!", ORANGE)

        # SUPER WORD indicator
        if self.super_timer > 0:
            super_sec = self.super_timer / 30.0
            super_text = f"SUPER WORD {super_sec:.1f}s"
            rave = (pyxel.frame_count // 6) % len(TILE_COLORS)
            pyxel.text(GRID_X, combo_y + 10, super_text, TILE_COLORS[rave])

        # HEAT bar
        heat_bar_x = GRID_X
        heat_bar_y = GRID_Y + GRID_SIZE * CELL + 30
        pyxel.text(heat_bar_x, heat_bar_y - 8, "HEAT", WHITE)
        pyxel.rectb(heat_bar_x - 1, heat_bar_y - 1, GRID_SIZE * CELL + 2, 8, WHITE)
        heat_w = int((self.heat / HEAT_MAX) * GRID_SIZE * CELL)
        if self.heat < 40:
            hc = GREEN
        elif self.heat < 70:
            hc = YELLOW
        else:
            hc = RED
        pyxel.rect(heat_bar_x, heat_bar_y, heat_w, 6, hc)

        # Timer text
        sec = self.timer / 30.0
        timer_text = f"TIME {sec:.1f}s"
        tx = GRID_X + GRID_SIZE * CELL + 12
        pyxel.text(tx, GRID_Y + 65, timer_text, WHITE if sec > 10 else RED)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 30, 40, "GAME OVER", RED)
        pyxel.rect(SCREEN_W // 2 - 40, 55, 80, 1, WHITE)

        pyxel.text(SCREEN_W // 2 - 40, 75, f"SCORE: {self.score}", YELLOW)
        pyxel.text(SCREEN_W // 2 - 40, 95, f"WORDS: {self.words_found}", LIME)
        pyxel.text(SCREEN_W // 2 - 40, 115, f"MAX COMBO: {self.max_combo}", WHITE)

        cause = "TIME UP" if self.timer <= 0 else "HEAT OVERLOAD"
        pyxel.text(SCREEN_W // 2 - 30, 140, cause, ORANGE)

        if self.score >= self.high_score and self.score > 0:
            pyxel.text(SCREEN_W // 2 - 40, 170, "NEW HIGH SCORE!", YELLOW)

        blink = (pyxel.frame_count // 30) % 2 == 0
        if blink:
            pyxel.text(SCREEN_W // 2 - 50, 210, "PRESS SPACE TO RETRY", WHITE)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
