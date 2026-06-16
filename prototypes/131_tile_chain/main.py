from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


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


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


class Game:
    COLS: int = 8
    ROWS: int = 6
    CELL: int = 40
    TILE_SIZE: int = 36
    TOTAL_TILES: int = 48
    COLORS: list[int] = [8, 5, 3, 10]  # RED, DARK_BLUE, GREEN, YELLOW
    TILES_PER_COLOR: int = 12
    GAME_TIME: int = 90 * 60  # 5400 frames
    SUPER_DURATION: int = 5 * 60  # 300 frames
    MAX_HEAT: int = 100
    HEAT_DECAY: float = 0.05
    WRONG_MATCH_HEAT: int = 15
    RESHUFFLE_HEAT: int = 10
    SUPER_COMBO_THRESHOLD: int = 4
    SUPER_SCORE_MULT: int = 3
    BASE_SCORE: int = 100

    BG_COLOR: int = 0
    TEXT_COLOR: int = 7

    TILE_MARGIN: int = 2  # (CELL - TILE_SIZE) // 2

    def __init__(self) -> None:
        pyxel.init(320, 240, title="TILE CHAIN", display_scale=2)
        self.reset()
        pyxel.run(self._update, self._draw)

    # ------------------------------------------------------------------ reset

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.grid: list[list[int | None]] = self._init_grid()
        self.selected: tuple[int, int] | None = None
        self.hovered: tuple[int, int] | None = None
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.heat: float = 0.0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.game_timer: int = self.GAME_TIME
        self.tiles_remaining: int = self.TOTAL_TILES
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shake_frames: int = 0
        self._rng: random.Random = random.Random()
        self._won: bool = False

    # ------------------------------------------------------------------ grid

    def _init_grid(self) -> list[list[int | None]]:
        tiles: list[int] = []
        for color in self.COLORS:
            tiles.extend([color] * self.TILES_PER_COLOR)
        self._rng.shuffle(tiles)
        grid: list[list[int | None]] = []
        idx = 0
        for row in range(self.ROWS):
            grid_row: list[int | None] = []
            for _ in range(self.COLS):
                grid_row.append(tiles[idx])
                idx += 1
            grid.append(grid_row)
        return grid

    def _find_matches(
        self, grid: list[list[int | None]]
    ) -> list[tuple[tuple[int, int], tuple[int, int]]]:
        positions: list[tuple[int, int]] = []
        for row in range(self.ROWS):
            for col in range(self.COLS):
                if grid[row][col] is not None:
                    positions.append((col, row))
        pairs: list[tuple[tuple[int, int], tuple[int, int]]] = []
        n = len(positions)
        for i in range(n):
            c1, r1 = positions[i]
            for j in range(i + 1, n):
                c2, r2 = positions[j]
                if grid[r1][c1] == grid[r2][c2]:
                    pairs.append((positions[i], positions[j]))
        return pairs

    def _has_valid_moves(self) -> bool:
        if self.tiles_remaining < 2:
            return False
        if self.super_mode:
            return True
        return len(self._find_matches(self.grid)) > 0

    def _reshuffle_grid(self) -> None:
        remaining: list[int] = []
        for row in range(self.ROWS):
            for col in range(self.COLS):
                color = self.grid[row][col]
                if color is not None:
                    remaining.append(color)
        self._rng.shuffle(remaining)
        idx = 0
        for row in range(self.ROWS):
            for col in range(self.COLS):
                if self.grid[row][col] is not None:
                    self.grid[row][col] = remaining[idx]
                    idx += 1
        self.heat = min(self.heat + self.RESHUFFLE_HEAT, self.MAX_HEAT)

    # ------------------------------------------------------------------ selection

    def _can_match(self, pos1: tuple[int, int], pos2: tuple[int, int]) -> bool:
        c1, r1 = pos1
        c2, r2 = pos2
        tile1 = self.grid[r1][c1]
        tile2 = self.grid[r2][c2]
        if tile1 is None or tile2 is None:
            return False
        if self.super_mode:
            return True
        return tile1 == tile2

    def _select_tile(self, col: int, row: int) -> str | None:
        if self.grid[row][col] is None:
            return None
        prev = self.selected
        if prev is None:
            self.selected = (col, row)
            return "select"
        if prev == (col, row):
            self.selected = None
            return None
        if self._can_match(prev, (col, row)):
            return "match"
        self.selected = None
        return "wrong"

    def _remove_tiles(
        self, pos1: tuple[int, int], pos2: tuple[int, int]
    ) -> int:
        c1, r1 = pos1
        c2, r2 = pos2
        self.grid[r1][c1] = None
        self.grid[r2][c2] = None
        return self.BASE_SCORE

    def _check_win(self) -> bool:
        return self.tiles_remaining <= 0

    def _check_game_over(self) -> bool:
        return self.heat >= self.MAX_HEAT or self.game_timer <= 0

    # ------------------------------------------------------------------ effects

    def _cell_center(self, col: int, row: int) -> tuple[float, float]:
        return (
            col * self.CELL + self.CELL / 2,
            row * self.CELL + self.CELL / 2,
        )

    def _spawn_match_particles(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: int,
        count: int = 8,
    ) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-2.0, 2.0)
            vy = self._rng.uniform(-3.0, -1.0)
            life = self._rng.randint(15, 25)
            self.particles.append(Particle(x1, y1, vx, vy, life, color))
        for _ in range(count):
            vx = self._rng.uniform(-2.0, 2.0)
            vy = self._rng.uniform(-3.0, -1.0)
            life = self._rng.randint(15, 25)
            self.particles.append(Particle(x2, y2, vx, vy, life, color))

    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int, life: int = 30
    ) -> None:
        self.floating_texts.append(FloatingText(x, y, text, life, color))

    # ------------------------------------------------------------------ handle match

    def _handle_match(self, pos1: tuple[int, int], pos2: tuple[int, int]) -> None:
        c1, r1 = pos1
        c2, r2 = pos2
        color = self.grid[r1][c1]
        if color is None:
            return

        base_score = self._remove_tiles(pos1, pos2)
        mult = self.SUPER_SCORE_MULT if self.super_mode else 1
        combo_bonus = 1 + self.combo * 0.5
        total = int(base_score * combo_bonus * mult)
        self.score += total
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        self.selected = None
        self.tiles_remaining -= 2

        cx1, cy1 = self._cell_center(c1, r1)
        cx2, cy2 = self._cell_center(c2, r2)
        mid_x = (cx1 + cx2) / 2
        mid_y = (cy1 + cy2) / 2

        self._spawn_match_particles(cx1, cy1, cx2, cy2, color)
        self._spawn_floating_text(mid_x, mid_y, f"+{total}", self.TEXT_COLOR)

        if self.combo >= 2:
            self._spawn_floating_text(
                mid_x, mid_y - 10, f"COMBO x{self.combo}", 10
            )

        if self.combo >= self.SUPER_COMBO_THRESHOLD and not self.super_mode:
            self.super_mode = True
            self.super_timer = self.SUPER_DURATION
            self._spawn_floating_text(160, 120, "SUPER MATCH!", 10, 45)
            self.shake_frames = 15

        if self.combo >= 6:
            self.shake_frames = max(self.shake_frames, 6)

        if self._check_win():
            self._won = True
            time_bonus = self.game_timer * 10
            self.score += 5000 + time_bonus
            self.phase = Phase.GAME_OVER

    def _handle_wrong(self) -> None:
        self.combo = 0
        self.heat = min(self.heat + self.WRONG_MATCH_HEAT, self.MAX_HEAT)
        self.shake_frames = max(self.shake_frames, 3)

    # ------------------------------------------------------------------ update

    def _update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self._start_game()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.TITLE
            return

        # --- PLAYING ---
        self._update_playing()

    def _start_game(self) -> None:
        self.phase = Phase.PLAYING
        self.grid = self._init_grid()
        self.selected = None
        self.hovered = None
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.heat = 0.0
        self.super_mode = False
        self.super_timer = 0
        self.game_timer = self.GAME_TIME
        self.tiles_remaining = self.TOTAL_TILES
        self.particles = []
        self.floating_texts = []
        self.shake_frames = 0
        self._rng = random.Random()
        self._won = False

    def _update_playing(self) -> None:
        # timer
        self.game_timer -= 1

        # heat decay
        self.heat = max(0.0, self.heat - self.HEAT_DECAY)

        # super mode timer
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0

        # shake
        if self.shake_frames > 0:
            self.shake_frames -= 1

        # particles
        for p in self.particles[:]:
            p.life -= 1
            p.vy += 0.1
            p.x += p.vx
            p.y += p.vy
            if p.life <= 0:
                self.particles.remove(p)

        # floating texts
        for ft in self.floating_texts[:]:
            ft.life -= 1
            ft.y -= 0.8
            if ft.life <= 0:
                self.floating_texts.remove(ft)

        # check game over
        if self._check_game_over():
            if self.heat >= self.MAX_HEAT:
                self._won = False
            self.phase = Phase.GAME_OVER
            return

        # input
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        col = mx // self.CELL
        row = my // self.CELL

        if 0 <= col < self.COLS and 0 <= row < self.ROWS:
            self.hovered = (col, row)
        else:
            self.hovered = None

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if self.hovered is not None:
                result = self._select_tile(col, row)
                if result == "match":
                    prev = self.selected
                    if prev is not None:
                        self._handle_match(prev, self.hovered)
                elif result == "wrong":
                    self._handle_wrong()
                # "select" or None: nothing else needed
            else:
                self.selected = None

        if pyxel.btnp(pyxel.KEY_R):
            if not self._has_valid_moves():
                self._reshuffle_grid()

    # ------------------------------------------------------------------ draw

    def _draw(self) -> None:
        pyxel.cls(self.BG_COLOR)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(120, 30, "TILE CHAIN", self.TEXT_COLOR)
        pyxel.text(115, 50, "Click matching tiles!", 5)
        pyxel.text(85, 70, "Match same colors to build combo", self.TEXT_COLOR)
        pyxel.text(95, 85, "COMBO x4 = SUPER MATCH!", 10)

        # color legend
        pyxel.text(130, 115, "Colors:", self.TEXT_COLOR)
        color_names = ["RED", "BLUE", "GREEN", "YELLOW"]
        for i, (c, name) in enumerate(zip(self.COLORS, color_names)):
            py = 130 + i * 12
            pyxel.rect(100, py, 8, 8, c)
            pyxel.text(112, py, name, c)

        pyxel.text(68, 190, "Press SPACE to start", self.TEXT_COLOR)
        pyxel.text(80, 210, "R = Reshuffle (+10 HEAT)", 13)

    def _draw_playing(self) -> None:
        # camera shake
        if self.shake_frames > 0:
            ox = self._rng.randint(-2, 2)
            oy = self._rng.randint(-2, 2)
            pyxel.camera(ox, oy)
        else:
            pyxel.camera(0, 0)

        # draw tiles
        for row in range(self.ROWS):
            for col in range(self.COLS):
                color = self.grid[row][col]
                tx = col * self.CELL + self.TILE_MARGIN
                ty = row * self.CELL + self.TILE_MARGIN

                if color is not None:
                    # super mode rainbow cycling
                    draw_color = color
                    if self.super_mode:
                        cycle_idx = (pyxel.frame_count // 10) % len(self.COLORS)
                        draw_color = self.COLORS[cycle_idx]

                    # tile body with 3D bevel
                    pyxel.rect(tx, ty, self.TILE_SIZE, self.TILE_SIZE, draw_color)
                    # highlight (top-left edges)
                    pyxel.rect(tx, ty, self.TILE_SIZE, 1, 7)
                    pyxel.rect(tx, ty, 1, self.TILE_SIZE, 7)
                    # shadow (bottom-right edges)
                    pyxel.rect(
                        tx, ty + self.TILE_SIZE - 1, self.TILE_SIZE, 1, 0
                    )
                    pyxel.rect(
                        tx + self.TILE_SIZE - 1, ty, 1, self.TILE_SIZE, 0
                    )
                else:
                    # empty cell background
                    pyxel.rect(tx, ty, self.TILE_SIZE, self.TILE_SIZE, 5)

        # hover highlight
        if self.hovered is not None:
            hc, hr = self.hovered
            if self.grid[hr][hc] is not None:
                hx = hc * self.CELL + self.TILE_MARGIN
                hy = hr * self.CELL + self.TILE_MARGIN
                pyxel.rectb(hx - 1, hy - 1, self.TILE_SIZE + 2, self.TILE_SIZE + 2, 7)

        # selected highlight (pulsing)
        if self.selected is not None:
            sc, sr = self.selected
            if self.grid[sr][sc] is not None:
                sx = sc * self.CELL + self.TILE_MARGIN
                sy = sr * self.CELL + self.TILE_MARGIN
                pulse = (pyxel.frame_count // 15) % 2
                border_color = 7 if pulse else 10
                pyxel.rectb(
                    sx - 2, sy - 2, self.TILE_SIZE + 4, self.TILE_SIZE + 4, border_color
                )

        # super mode indicator
        if self.super_mode:
            remaining = self.super_timer // 60
            pyxel.text(130, 2, f"SUPER {remaining}s", 10)

        # draw particles
        for p in self.particles:
            if p.life > 0:
                pyxel.circ(int(p.x), int(p.y), 2, p.color)

        # draw floating texts
        for ft in self.floating_texts:
            if ft.life > 0:
                pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

        # UI overlay background
        bar_y = 228
        pyxel.rect(0, bar_y - 2, 320, 14, 0)

        # heat bar
        heat_width = int(self.heat)
        if self.heat < 30:
            heat_color = 3
        elif self.heat < 60:
            heat_color = 10
        elif self.heat < 85:
            heat_color = 9
        else:
            heat_color = 8
        pyxel.rect(4, bar_y, heat_width, 6, heat_color)
        pyxel.rectb(4, bar_y, 100, 6, 7)
        pyxel.text(4, bar_y - 6, f"HEAT {int(self.heat)}", 7)

        # score
        score_text = f"SCORE {self.score}"
        pyxel.text(160 - len(score_text) * 2, bar_y - 2, score_text, 7)

        # combo
        if self.combo >= 2:
            combo_color = 10 if (pyxel.frame_count // 20) % 2 == 0 else 7
            combo_text = f"COMBO x{self.combo}"
            pyxel.text(
                160 - len(combo_text) * 2,
                bar_y - 14,
                combo_text,
                combo_color,
            )

        # timer
        secs = self.game_timer // 60
        timer_text = f"{secs}s"
        timer_color = 7 if secs > 10 else 8
        pyxel.text(310 - len(timer_text) * 4, bar_y - 2, timer_text, timer_color)

        # no valid moves hint
        if not self.super_mode and self.tiles_remaining >= 2 and not self._has_valid_moves():
            hint = "Press R to reshuffle"
            pyxel.text(
                160 - len(hint) * 2, bar_y - 26, hint, 10
            )

        # reset camera
        pyxel.camera(0, 0)

    def _draw_game_over(self) -> None:
        if self._won:
            pyxel.text(125, 60, "ALL CLEAR!", 10)
        else:
            pyxel.text(122, 60, "GAME OVER", 8)

        pyxel.text(115, 90, f"Score: {self.score}", self.TEXT_COLOR)
        pyxel.text(105, 105, f"Max Combo: {self.max_combo}", self.TEXT_COLOR)

        if self._won:
            pyxel.text(110, 125, "You cleared all tiles!", 3)

        pyxel.text(68, 160, "Press SPACE to retry", self.TEXT_COLOR)


# ------------------------------------------------------------------ factory for testing


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.selected = None
    g.hovered = None
    g.combo = 0
    g.max_combo = 0
    g.score = 0
    g.heat = 0.0
    g.super_mode = False
    g.super_timer = 0
    g.game_timer = Game.GAME_TIME
    g.tiles_remaining = Game.TOTAL_TILES
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g._rng = random.Random(seed)
    g._won = False
    g.grid = g._init_grid()
    return g


# ------------------------------------------------------------------ main

if __name__ == "__main__":
    Game()
