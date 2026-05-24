import pyxel
import random
import math
from dataclasses import dataclass

SCREEN_W = 320
SCREEN_H = 240
COLS = 7
ROWS = 6
CELL_SIZE = 32
GRID_X = 48
GRID_Y = 24
DISC_RADIUS = 14
SUPER_DISC_RADIUS = 16

NAVY = 1
GREEN = 3
DARK_BLUE = 5
WHITE = 7
RED = 8
YELLOW = 10
CYAN = 12
GRAY = 13
BLACK = 0

DISC_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
SUPER_DISC_COLOR_CYCLE: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
NUM_COLORS = len(DISC_COLORS)
SUPER_DISC_VALUE = NUM_COLORS

PHASE_TITLE = 0
PHASE_PLAYING = 1
PHASE_ANIM_DROP = 2
PHASE_ANIM_CLEAR = 3
PHASE_ANIM_GRAVITY = 4
PHASE_GRID_PRESSURE = 5
PHASE_GAME_OVER = 6


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int


class Game:
    def __init__(self) -> None:
        self._rng = random.Random()
        self._init_state()
        pyxel.init(SCREEN_W, SCREEN_H, title="CHAIN DROP", display_scale=2)
        pyxel.run(self.update, self.draw)

    def _init_state(self) -> None:
        self.grid: list[list[int | None]] = [[None] * COLS for _ in range(ROWS)]
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.turn_count = 0
        self.pressure_timer = 5
        self.last_color: int | None = None
        self.super_disc_ready = False
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._shake_frames = 0
        self._shake_offset_x = 0
        self._shake_offset_y = 0
        self.selected_col = 3
        self.phase = PHASE_TITLE
        self._anim_timer = 0
        self._drop_col = -1
        self._drop_color = -1
        self._drop_target_row = -1
        self._drop_y = 0.0
        self._match_flash_timer = 0
        self._matches_to_clear: list[set[tuple[int, int]]] = []
        self._discs_cleared = 0
        self._chain_count = 0
        self._was_super_disc = False
        self._super_disc_anim_timer = 0
        self._decrement_pressure_on_settle = False

    def update(self) -> None:
        if self.phase == PHASE_TITLE:
            self._update_title()
        elif self.phase == PHASE_PLAYING:
            self._update_playing()
        elif self.phase == PHASE_ANIM_DROP:
            self._update_anim_drop()
        elif self.phase == PHASE_ANIM_CLEAR:
            self._update_anim_clear()
        elif self.phase == PHASE_ANIM_GRAVITY:
            self._update_anim_gravity()
        elif self.phase == PHASE_GRID_PRESSURE:
            self._update_grid_pressure()
        elif self.phase == PHASE_GAME_OVER:
            self._update_game_over()

        self._update_particles()
        self._update_floating_texts()

        if self._shake_frames > 0:
            self._shake_frames -= 1
            self._shake_offset_x = self._rng.randint(-2, 2)
            self._shake_offset_y = self._rng.randint(-2, 2)
        else:
            self._shake_offset_x = 0
            self._shake_offset_y = 0

        self._super_disc_anim_timer += 1

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y -= 1.0
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    # -- Title --

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._init_state()
            self.phase = PHASE_PLAYING

    # -- Playing --

    def _update_playing(self) -> None:
        if pyxel.btnp(pyxel.KEY_LEFT):
            self.selected_col = (self.selected_col - 1) % COLS
        if pyxel.btnp(pyxel.KEY_RIGHT):
            self.selected_col = (self.selected_col + 1) % COLS

        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            if self.grid[0][self.selected_col] is not None:
                return
            color = self._next_disc_color()
            target_row = self._find_drop_target_row(self.selected_col)
            self._drop_col = self.selected_col
            self._drop_color = color
            self._drop_target_row = target_row
            self._drop_y = float(GRID_Y - 16)
            self._decrement_pressure_on_settle = True
            self.phase = PHASE_ANIM_DROP

    def _next_disc_color(self) -> int:
        if self.super_disc_ready:
            self._was_super_disc = True
            self.super_disc_ready = False
            self.combo = 0
            self.last_color = None
            return SUPER_DISC_VALUE
        self._was_super_disc = False
        return self._rng.randint(0, NUM_COLORS - 1)

    def _find_drop_target_row(self, col: int) -> int:
        for row in range(ROWS - 1, -1, -1):
            if self.grid[row][col] is None:
                return row
        return -1

    # -- Anim Drop --

    def _update_anim_drop(self) -> None:
        target_y = float(GRID_Y + self._drop_target_row * CELL_SIZE + CELL_SIZE // 2)
        remaining = target_y - self._drop_y
        self._drop_y += max(remaining * 0.3, 3.0)
        if self._drop_y >= target_y:
            self._drop_y = target_y
            self.grid[self._drop_target_row][self._drop_col] = self._drop_color
            self._on_disc_placed()

    def _on_disc_placed(self) -> None:
        if self._drop_color != SUPER_DISC_VALUE:
            if self.last_color is not None and self._drop_color == self.last_color:
                self.combo += 1
            else:
                self.combo = 0
            self.last_color = self._drop_color
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            if self.combo >= 4:
                self.super_disc_ready = True

        self.turn_count += 1
        matches = self._find_all_matches()
        if matches:
            self._matches_to_clear = matches
            self._match_flash_timer = 15
            self._chain_count = 0
            self.phase = PHASE_ANIM_CLEAR
        else:
            self._finish_turn()

    # -- Match Detection --

    def _find_all_matches(self) -> list[set[tuple[int, int]]]:
        matched: set[tuple[int, int]] = set()

        for r in range(ROWS):
            for c in range(COLS - 3):
                seg = [(r, c + i) for i in range(4)]
                if self._is_match(seg):
                    matched.update(seg)

        for r in range(ROWS - 3):
            for c in range(COLS):
                seg = [(r + i, c) for i in range(4)]
                if self._is_match(seg):
                    matched.update(seg)

        for r in range(ROWS - 3):
            for c in range(COLS - 3):
                seg = [(r + i, c + i) for i in range(4)]
                if self._is_match(seg):
                    matched.update(seg)

        for r in range(ROWS - 3):
            for c in range(3, COLS):
                seg = [(r + i, c - i) for i in range(4)]
                if self._is_match(seg):
                    matched.update(seg)

        if not matched:
            return []
        return self._group_connected(matched)

    def _is_match(self, cells: list[tuple[int, int]]) -> bool:
        vals = [self.grid[r][c] for r, c in cells]
        if any(v is None for v in vals):
            return False
        non_super = {v for v in vals if v != SUPER_DISC_VALUE}
        return len(non_super) <= 1

    def _group_connected(
        self, matched: set[tuple[int, int]]
    ) -> list[set[tuple[int, int]]]:
        remaining = set(matched)
        groups: list[set[tuple[int, int]]] = []
        while remaining:
            start = remaining.pop()
            group: set[tuple[int, int]] = {start}
            stack = [start]
            while stack:
                r, c = stack.pop()
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if (nr, nc) in remaining:
                        remaining.remove((nr, nc))
                        group.add((nr, nc))
                        stack.append((nr, nc))
            groups.append(group)
        return groups

    # -- Anim Clear --

    def _update_anim_clear(self) -> None:
        self._match_flash_timer -= 1
        if self._match_flash_timer <= 0:
            self._execute_clear()
            self.phase = PHASE_ANIM_GRAVITY

    def _execute_clear(self) -> None:
        self._discs_cleared = 0
        for group in self._matches_to_clear:
            for r, c in group:
                self.grid[r][c] = None
                self._discs_cleared += 1
                cx = float(GRID_X + c * CELL_SIZE + CELL_SIZE // 2)
                cy = float(GRID_Y + r * CELL_SIZE + CELL_SIZE // 2)
                for _ in range(self._rng.randint(4, 8)):
                    angle = self._rng.uniform(0, math.pi * 2)
                    speed = self._rng.uniform(1.5, 3.5)
                    self.particles.append(
                        Particle(
                            x=cx,
                            y=cy,
                            vx=math.cos(angle) * speed,
                            vy=math.sin(angle) * speed,
                            color=self._rng.choice(DISC_COLORS),
                            life=self._rng.randint(15, 30),
                        )
                    )

        num_groups = len(self._matches_to_clear)
        base = self._discs_cleared * 10
        multiplier = max(1, num_groups)
        combo_bonus = self.combo * 50
        score_gain = base * multiplier + combo_bonus
        if self._was_super_disc:
            score_gain = int(score_gain * 3)
            self._was_super_disc = False

        self._chain_count += 1
        if self._chain_count > 1:
            score_gain = int(score_gain * (1.0 + 0.5 * (self._chain_count - 1)))

        self.score += score_gain

        cx = float(GRID_X + COLS * CELL_SIZE // 2)
        cy = float(GRID_Y + ROWS * CELL_SIZE // 2)
        self.floating_texts.append(
            FloatingText(x=cx, y=cy, text=f"+{score_gain}", color=WHITE, life=30)
        )

        if num_groups >= 3:
            self._shake_frames = 8

    # -- Anim Gravity --

    def _update_anim_gravity(self) -> None:
        moved = self._apply_gravity()
        if not moved:
            matches = self._find_all_matches()
            if matches:
                self._matches_to_clear = matches
                self._match_flash_timer = 10
                self.phase = PHASE_ANIM_CLEAR
            else:
                self._finish_turn()

    def _apply_gravity(self) -> bool:
        moved = False
        for col in range(COLS):
            col_vals = [self.grid[row][col] for row in range(ROWS)]
            non_empty = [v for v in col_vals if v is not None]
            new_col: list[int | None] = [None] * (ROWS - len(non_empty)) + non_empty
            for row in range(ROWS):
                if self.grid[row][col] != new_col[row]:
                    moved = True
                self.grid[row][col] = new_col[row]
        return moved

    # -- Turn Finish --

    def _finish_turn(self) -> None:
        if self._decrement_pressure_on_settle:
            self._decrement_pressure_on_settle = False
            self.pressure_timer -= 1
            if self.pressure_timer <= 0:
                spawned, has_matches = self._spawn_pressure_disc()
                if not spawned:
                    self.phase = PHASE_GAME_OVER
                    return
                self.pressure_timer = 5
                if has_matches:
                    self.phase = PHASE_ANIM_CLEAR
                else:
                    self.phase = PHASE_GRID_PRESSURE
                return
        self.phase = PHASE_PLAYING

    # -- Grid Pressure --

    def _spawn_pressure_disc(self) -> tuple[bool, bool]:
        cols = list(range(COLS))
        self._rng.shuffle(cols)
        for col in cols:
            for row in range(ROWS - 1, -1, -1):
                if self.grid[row][col] is None:
                    self.grid[row][col] = self._rng.randint(0, NUM_COLORS - 1)
                    matches = self._find_all_matches()
                    if matches:
                        self._matches_to_clear = matches
                        self._match_flash_timer = 15
                        self._chain_count = 0
                        return True, True
                    return True, False
        return False, False

    def _update_grid_pressure(self) -> None:
        self._anim_timer += 1
        if self._anim_timer > 20:
            self._anim_timer = 0
            self.phase = PHASE_PLAYING

    # -- Game Over --

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self._init_state()
            self.phase = PHASE_PLAYING

    # -- Drawing --

    def draw(self) -> None:
        pyxel.cls(NAVY)
        if self.phase == PHASE_TITLE:
            self._draw_title()
            return

        ox = self._shake_offset_x
        oy = self._shake_offset_y
        self._draw_grid(ox, oy)
        self._draw_ui()
        self._draw_particles(ox, oy)
        self._draw_floating_texts(ox, oy)

        if self.phase == PHASE_PLAYING:
            self._draw_column_selector()
        elif self.phase == PHASE_ANIM_DROP:
            self._draw_dropping_disc()
        elif self.phase == PHASE_ANIM_CLEAR:
            self._draw_match_flash(ox, oy)

        if self.phase == PHASE_GAME_OVER:
            self._draw_game_over_overlay()

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 40, 55, "CHAIN DROP", WHITE)
        pyxel.text(SCREEN_W // 2 - 70, 85, "Drop discs, match 4+!", GRAY)
        pyxel.text(SCREEN_W // 2 - 70, 100, "Same color consecutively", GRAY)
        pyxel.text(SCREEN_W // 2 - 60, 115, "builds COMBO for SUPER!", GRAY)
        pyxel.text(SCREEN_W // 2 - 75, 145, "LEFT / RIGHT  : move column", GRAY)
        pyxel.text(SCREEN_W // 2 - 75, 160, "SPACE / RETURN: drop disc", GRAY)
        pyxel.text(SCREEN_W // 2 - 60, 195, "Press SPACE to start", CYAN)

    def _draw_grid(self, ox: int, oy: int) -> None:
        x0 = GRID_X + ox
        y0 = GRID_Y + oy
        gw = COLS * CELL_SIZE
        gh = ROWS * CELL_SIZE

        pyxel.rect(x0, y0, gw, gh, BLACK)
        for i in range(COLS + 1):
            pyxel.line(x0 + i * CELL_SIZE, y0, x0 + i * CELL_SIZE, y0 + gh, GRAY)
        for i in range(ROWS + 1):
            pyxel.line(x0, y0 + i * CELL_SIZE, x0 + gw, y0 + i * CELL_SIZE, GRAY)

        if self.pressure_timer <= 2:
            if (pyxel.frame_count // 8) % 2 == 0:
                pyxel.rectb(x0, y0 + gh - 4, gw, 8, RED)

        for r in range(ROWS):
            for c in range(COLS):
                v = self.grid[r][c]
                if v is None:
                    continue
                cx = x0 + c * CELL_SIZE + CELL_SIZE // 2
                cy = y0 + r * CELL_SIZE + CELL_SIZE // 2
                if v == SUPER_DISC_VALUE:
                    self._draw_super_disc(cx, cy)
                else:
                    pyxel.circ(cx, cy, DISC_RADIUS, DISC_COLORS[v])
                    pyxel.circ(cx - 2, cy - 3, DISC_RADIUS // 3, WHITE)

    def _draw_super_disc(self, cx: int, cy: int) -> None:
        ci = (self._super_disc_anim_timer // 4) % 4
        color = SUPER_DISC_COLOR_CYCLE[ci]
        radius = int(SUPER_DISC_RADIUS + math.sin(self._super_disc_anim_timer * 0.2) * 2)
        pyxel.circ(cx, cy, radius, color)
        pyxel.circ(cx - 3, cy - 4, 5, WHITE)

    def _draw_column_selector(self) -> None:
        cx = GRID_X + self.selected_col * CELL_SIZE + CELL_SIZE // 2
        ty = GRID_Y - 12
        pyxel.tri(cx - 8, ty - 4, cx + 8, ty - 4, cx, ty + 8, CYAN)
        if pyxel.frame_count // 12 % 2 == 0:
            pyxel.tri(cx - 4, ty - 2, cx + 4, ty - 2, cx, ty + 4, WHITE)

    def _draw_dropping_disc(self) -> None:
        cx = GRID_X + self._drop_col * CELL_SIZE + CELL_SIZE // 2
        dy = int(self._drop_y)
        if self._drop_color == SUPER_DISC_VALUE:
            self._draw_super_disc(cx, dy)
        else:
            pyxel.circ(cx, dy, DISC_RADIUS, DISC_COLORS[self._drop_color])
            pyxel.circ(cx - 2, dy - 3, DISC_RADIUS // 3, WHITE)

    def _draw_match_flash(self, ox: int, oy: int) -> None:
        if self._match_flash_timer % 4 < 2:
            x0 = GRID_X + ox
            y0 = GRID_Y + oy
            for group in self._matches_to_clear:
                for r, c in group:
                    cx = x0 + c * CELL_SIZE + CELL_SIZE // 2
                    cy = y0 + r * CELL_SIZE + CELL_SIZE // 2
                    pyxel.circ(cx, cy, DISC_RADIUS, WHITE)

    def _draw_ui(self) -> None:
        pyxel.text(4, 2, f"SCORE:{self.score}", WHITE)
        combo_str = f"COMBO:{self.combo}"
        if self.super_disc_ready:
            combo_str += " SUPER!"
        pyxel.text(4, 12, combo_str, CYAN if self.super_disc_ready else WHITE)
        pyxel.text(SCREEN_W - 55, 2, f"MAX:{self.max_combo}", GRAY)
        pc = RED if self.pressure_timer <= 2 else GRAY
        pyxel.text(SCREEN_W - 35, 12, f"P:{self.pressure_timer}", pc)

    def _draw_game_over_overlay(self) -> None:
        pyxel.rect(0, SCREEN_H // 2 - 45, SCREEN_W, 95, NAVY)
        pyxel.rectb(0, SCREEN_H // 2 - 45, SCREEN_W, 95, RED)
        pyxel.text(SCREEN_W // 2 - 35, SCREEN_H // 2 - 35, "GAME OVER", WHITE)
        pyxel.text(
            SCREEN_W // 2 - 55, SCREEN_H // 2 - 15, f"SCORE: {self.score}", WHITE
        )
        pyxel.text(
            SCREEN_W // 2 - 55, SCREEN_H // 2, f"MAX COMBO: {self.max_combo}", CYAN
        )
        pyxel.text(SCREEN_W // 2 - 50, SCREEN_H // 2 + 20, "R: RESTART", GRAY)

    def _draw_particles(self, ox: int, oy: int) -> None:
        for p in self.particles:
            alpha = p.life / 30.0
            px = int(p.x + ox)
            py = int(p.y + oy)
            if alpha > 0.6:
                pyxel.circ(px, py, 2, p.color)
            elif alpha > 0.3:
                pyxel.pset(px, py, p.color)

    def _draw_floating_texts(self, ox: int, oy: int) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 30.0
            if alpha <= 0:
                continue
            color = ft.color if alpha > 0.5 else GRAY
            pyxel.text(int(ft.x + ox), int(ft.y + oy), ft.text, color)


if __name__ == "__main__":
    Game()
