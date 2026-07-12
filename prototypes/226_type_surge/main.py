from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

SCREEN_W = 320
SCREEN_H = 240
COLS = 10
ROWS = 8
CELL = 24
GRID_X = 40
GRID_Y = 24
GAME_DURATION = 60 * 60
SUPER_DURATION = 300
MAX_HEAT = 100
WRONG_KEY_HEAT = 15
COMBO_THRESHOLD = 4
SPREAD_BASE_INTERVAL = 90
SPREAD_MIN_INTERVAL = 30
SPAWN_INTERVAL = 120
SPREAD_CHANCE = 0.5
HEAT_DECAY = 0.02
GRID_PRESSURE_THRESHOLD = 0.6

LETTER_CHARS: tuple[str, str, str, str] = ("A", "S", "D", "F")
GRID_COLORS: tuple[int, int, int, int] = (8, 3, 5, 10)

RAINBOW_COLORS: tuple[int, ...] = (8, 9, 10, 11, 12, 6, 2, 14)


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


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


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="TYPE SURGE", display_scale=2)
        self._rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.grid: list[list[int]] = [
            [-1 for _ in range(COLS)] for _ in range(ROWS)
        ]
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.heat: float = 0.0
        self.game_timer: int = GAME_DURATION
        self.last_cleared: int = -1
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.spread_timer: int = SPREAD_BASE_INTERVAL
        self.spawn_timer: int = SPAWN_INTERVAL
        self.total_cleared: int = 0
        self._rng = random.Random()

    # ---- Phase helpers ----

    def _current_spread_interval(self) -> int:
        progress = 1.0 - (self.game_timer / GAME_DURATION)
        return int(
            SPREAD_BASE_INTERVAL
            - (SPREAD_BASE_INTERVAL - SPREAD_MIN_INTERVAL) * progress
        )

    # ---- Keypress handling ----

    def _handle_keypress(self, char: str) -> int:
        letter_idx = LETTER_CHARS.index(char)
        cells_cleared = self._clear_letter(letter_idx)

        if cells_cleared > 0:
            if self.super_mode:
                self.combo += 1
            elif self.last_cleared == letter_idx:
                self.combo += 1
            else:
                self.combo = 1

            self.last_cleared = letter_idx
            multiplier = 3 if self.super_mode else 1
            gained = int(cells_cleared * (1 + self.combo * 0.5) * multiplier)
            self.score += gained
            self.max_combo = max(self.max_combo, self.combo)
            self.total_cleared += cells_cleared

            if not self.super_mode and self.combo >= COMBO_THRESHOLD:
                self._activate_super_mode()

        else:
            self.heat = min(self.heat + WRONG_KEY_HEAT, MAX_HEAT)
            self.combo = 0
            self.last_cleared = -1

        return cells_cleared

    def _clear_letter(self, letter_idx: int) -> int:
        count = 0
        for y in range(ROWS):
            for x in range(COLS):
                if self.grid[y][x] == -1:
                    continue
                if self.super_mode or self.grid[y][x] == letter_idx:
                    self._spawn_particles(
                        GRID_X + x * CELL + CELL // 2,
                        GRID_Y + y * CELL + CELL // 2,
                        GRID_COLORS[self.grid[y][x]],
                        4,
                    )
                    self.grid[y][x] = -1
                    count += 1
        return count

    def _activate_super_mode(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self.floating_texts.append(
            FloatingText(
                SCREEN_W // 2 - 30,
                SCREEN_H // 2 - 10,
                "SUPER MODE!",
                50,
                10,
            )
        )

    def _deactivate_super_mode(self) -> None:
        self.super_mode = False
        self.combo = 0
        self.last_cleared = -1

    # ---- Grid spread (CA) ----

    def _spread_letters(self) -> None:
        new_cells: list[tuple[int, int, int]] = []
        for y in range(ROWS):
            for x in range(COLS):
                if self.grid[y][x] == -1:
                    continue
                if self._rng.random() >= SPREAD_CHANCE:
                    continue
                letter = self.grid[y][x]
                adj = self._adjacent_empty(x, y)
                if adj:
                    nx, ny = self._rng.choice(adj)
                    new_cells.append((nx, ny, letter))
        for nx, ny, letter in new_cells:
            if self.grid[ny][nx] == -1:
                self.grid[ny][nx] = letter

    def _adjacent_empty(self, x: int, y: int) -> list[tuple[int, int]]:
        result: list[tuple[int, int]] = []
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < COLS and 0 <= ny < ROWS and self.grid[ny][nx] == -1:
                result.append((nx, ny))
        return result

    def _spawn_letter(self) -> None:
        edge_cells = self._edge_empty_cells()
        if not edge_cells:
            self.heat = min(self.heat + 5, MAX_HEAT)
            return
        x, y = self._rng.choice(edge_cells)
        letter = self._rng.randint(0, 3)
        self.grid[y][x] = letter

    def _edge_empty_cells(self) -> list[tuple[int, int]]:
        result: list[tuple[int, int]] = []
        for x in range(COLS):
            if self.grid[0][x] == -1:
                result.append((x, 0))
            if self.grid[ROWS - 1][x] == -1:
                result.append((x, ROWS - 1))
        for y in range(1, ROWS - 1):
            if self.grid[y][0] == -1:
                result.append((0, y))
            if self.grid[y][COLS - 1] == -1:
                result.append((COLS - 1, y))
        return result

    # ---- HEAT ----

    def _update_heat(self) -> None:
        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER
            return

        self.heat = max(0.0, self.heat - HEAT_DECAY)

        occ = self._grid_occupancy()
        if occ > GRID_PRESSURE_THRESHOLD:
            self.heat = min(self.heat + 1, MAX_HEAT)

        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER

    def _grid_occupancy(self) -> float:
        filled = sum(1 for row in self.grid for c in row if c != -1)
        return filled / (COLS * ROWS)

    # ---- Timers ----

    def _update_timers(self) -> None:
        self.game_timer -= 1
        if self.game_timer <= 0:
            self.game_timer = 0
            self.phase = Phase.GAME_OVER
            return

        self.spread_timer -= 1
        if self.spread_timer <= 0:
            self.spread_timer = self._current_spread_interval()
            self._spread_letters()

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_timer = SPAWN_INTERVAL
            self._spawn_letter()

        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self._deactivate_super_mode()

        self._update_heat()

    # ---- Particles ----

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-1.5, 1.5)
            vy = self._rng.uniform(-2.5, -0.5)
            life = self._rng.randint(20, 30)
            self.particles.append(
                Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color)
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=35, color=color)
        )

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.8
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ---- Update ----

    def update(self) -> None:
        self._update_particles()
        self._update_floating_texts()

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.PLAYING

        elif self.phase == Phase.PLAYING:
            self._update_timers()
            if self.phase == Phase.GAME_OVER:
                return

            if pyxel.btnp(pyxel.KEY_A):
                self._handle_keypress("A")
            elif pyxel.btnp(pyxel.KEY_S):
                self._handle_keypress("S")
            elif pyxel.btnp(pyxel.KEY_D):
                self._handle_keypress("D")
            elif pyxel.btnp(pyxel.KEY_F):
                self._handle_keypress("F")

        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.PLAYING

    # ---- Draw ----

    def draw(self) -> None:
        pyxel.cls(0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_playing()
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = "TYPE SURGE"
        tw = len(title) * 8
        pyxel.text(SCREEN_W // 2 - tw // 2, 50, title, 7)

        instructions = [
            "Match letters on the grid: A S D F",
            "Same-letter chains build COMBO!",
            "COMBO x4 = SUPER MODE (5s, 3x score!)",
            "SUPER MODE clears all letters!",
            "Wrong key = HEAT +15",
            "Grid overflow raises HEAT",
            "HEAT>=100 or 60s = Game Over",
            "",
            "Press SPACE to Start",
        ]
        for i, line in enumerate(instructions):
            lw = len(line) * 4
            pyxel.text(SCREEN_W // 2 - lw // 2, 80 + i * 14, line, 13)

    def _draw_playing(self) -> None:
        if self.super_mode:
            border_c = RAINBOW_COLORS[(pyxel.frame_count // 4) % len(RAINBOW_COLORS)]
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, border_c)

        self._draw_grid()
        self._draw_hud()
        self._draw_particles()
        self._draw_floating_texts()

    def _draw_grid(self) -> None:
        bg_color = 1 if not self.super_mode else \
            RAINBOW_COLORS[(pyxel.frame_count // 8) % len(RAINBOW_COLORS)]
        pyxel.rect(GRID_X - 2, GRID_Y - 2, COLS * CELL + 4, ROWS * CELL + 4, bg_color)
        pyxel.rect(GRID_X - 1, GRID_Y - 1, COLS * CELL + 2, ROWS * CELL + 2, 0)

        for y in range(ROWS):
            for x in range(COLS):
                px = GRID_X + x * CELL
                py = GRID_Y + y * CELL
                letter_idx = self.grid[y][x]
                if letter_idx != -1:
                    color = GRID_COLORS[letter_idx]
                    pyxel.rect(px + 1, py + 1, CELL - 2, CELL - 2, color)
                    pyxel.rectb(px, py, CELL, CELL, 5)
                    char = LETTER_CHARS[letter_idx]
                    cx = px + (CELL - 4) // 2
                    cy = py + (CELL - 6) // 2
                    pyxel.text(cx, cy, char, 0)
                else:
                    pyxel.rect(px + 1, py + 1, CELL - 2, CELL - 2, 1)
                    pyxel.rectb(px, py, CELL, CELL, 5)

    def _draw_hud(self) -> None:
        timer_sec = max(0, self.game_timer) // 60
        pyxel.text(4, 2, f"TIME: {timer_sec}s", 7)
        pyxel.text(SCREEN_W - 80, 2, f"SCORE: {self.score}", 7)

        if self.combo > 0:
            combo_color = 10 if self.combo >= COMBO_THRESHOLD else 7
            if self.combo >= COMBO_THRESHOLD and pyxel.frame_count % 10 < 5:
                combo_color = 8
            pyxel.text(4, 12, f"COMBO: x{self.combo}", combo_color)

        if self.super_mode:
            rc = RAINBOW_COLORS[(pyxel.frame_count // 4) % len(RAINBOW_COLORS)]
            super_text = f"SUPER {self.super_timer // 60 + 1}s"
            pyxel.text(SCREEN_W // 2 - 20, 2, super_text, rc)

        self._draw_heat_bar()

    def _draw_heat_bar(self) -> None:
        bar_w = 120
        bar_x = SCREEN_W - bar_w - 4
        bar_y = SCREEN_H - 12
        pyxel.rect(bar_x, bar_y, bar_w, 8, 5)
        fill_w = min(bar_w, int(bar_w * self.heat / MAX_HEAT))
        if self.heat >= 70:
            hc = 8
        elif self.heat >= 40:
            hc = 9
        else:
            hc = 3
        if fill_w > 0:
            pyxel.rect(bar_x, bar_y, fill_w, 8, hc)
        pyxel.rectb(bar_x, bar_y, bar_w, 8, 7)
        pyxel.text(bar_x - 30, bar_y, "HEAT", 7)

    def _draw_particles(self) -> None:
        for p in self.particles:
            if p.life > 4 or pyxel.frame_count % 2 == 0:
                sz = max(1, p.life // 6)
                pyxel.rect(int(p.x), int(p.y), sz, sz, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life > 0:
                pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

    def _draw_game_over(self) -> None:
        pyxel.rect(40, 50, SCREEN_W - 80, SCREEN_H - 100, 0)
        pyxel.rectb(40, 50, SCREEN_W - 80, SCREEN_H - 100, 7)

        go_text = "GAME OVER"
        pyxel.text(SCREEN_W // 2 - len(go_text) * 4, 70, go_text, 8)

        score_text = f"SCORE: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_text) * 4, 95, score_text, 7)

        combo_text = f"MAX COMBO: {self.max_combo}"
        pyxel.text(SCREEN_W // 2 - len(combo_text) * 4, 115, combo_text, 7)

        cleared_text = f"TOTAL CLEARED: {self.total_cleared}"
        pyxel.text(SCREEN_W // 2 - len(cleared_text) * 4, 135, cleared_text, 7)

        reason = "TIME UP!" if self.heat < MAX_HEAT else "HEAT OVERLOAD!"
        pyxel.text(SCREEN_W // 2 - len(reason) * 4, 155, reason, 13)

        retry = "Press SPACE to Retry"
        pyxel.text(SCREEN_W // 2 - len(retry) * 4, 185, retry, 7)


if __name__ == "__main__":
    Game()
