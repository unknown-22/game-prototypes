from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# --- Raw int color constants ---
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

COLOR_VALS = [RED, GREEN, LIGHT_BLUE, YELLOW]  # 8, 3, 6, 10


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    SYNTHESIS_ANIM = auto()
    GAME_OVER = auto()
    LOCK_CLEAR = auto()


class PinState(Enum):
    LOCKED = auto()
    SET = auto()
    JAMMED = auto()


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


@dataclass
class SynthesisStep:
    col: int
    row: int
    color: int


class Game:
    SCREEN_W = 320
    SCREEN_H = 240
    GRID_COLS = 4
    GRID_ROWS = 5
    CELL_SIZE = 40
    GRID_X = 60
    GRID_Y = 20
    CELL_GAP = 2
    NUM_COLORS = 4
    SYNTHESIS_THRESHOLD = 4
    TENSION_PER_CLICK = 12
    MAX_TENSION = 100
    SECURITY_THRESHOLD = 70
    SECURITY_INTERVAL = 30
    MAX_JAMMED = 8

    def __init__(self) -> None:
        pyxel.init(self.SCREEN_W, self.SCREEN_H, title="Lockpick Surge")
        self._rng: random.Random = random.Random()
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.tension: int = 0
        self.locks_cleared: int = 0
        self.security_timer: int = 0
        self.prev_color: int | None = None
        self.grid: list[list[int]] = []
        self.state: list[list[PinState]] = []
        self.jammed_count: int = 0
        self.synth_steps: list[SynthesisStep] = []
        self.synth_step_idx: int = 0
        self.synth_bonus: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._shake_frames: int = 0
        self.game_timer: int = 90 * 30
        self.high_score: int = 0
        self.final_score_breakdown: list[str] = []
        self.synth_anim_timer: int = 0
        self.synth_anim_duration: int = 20
        self._prev_mouse_pressed: bool = False
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.tension = 0
        self.locks_cleared = 0
        self.security_timer = 0
        self.prev_color = None
        self.grid = []
        self.state = []
        self.jammed_count = 0
        self.synth_steps = []
        self.synth_step_idx = 0
        self.synth_bonus = 0
        self.particles = []
        self.floating_texts = []
        self._shake_frames = 0
        self.game_timer = 90 * 30
        self.final_score_breakdown = []
        self.synth_anim_timer = 0
        self._generate_lock()

    def _generate_lock(self) -> None:
        self.grid = [[0] * self.GRID_COLS for _ in range(self.GRID_ROWS)]
        self.state = [[PinState.LOCKED] * self.GRID_COLS for _ in range(self.GRID_ROWS)]
        for r in range(self.GRID_ROWS):
            for c in range(self.GRID_COLS):
                self.grid[r][c] = self._rng.randint(0, self.NUM_COLORS - 1)
        for color in range(self.NUM_COLORS):
            r = self._rng.randint(0, self.GRID_ROWS - 1)
            c = self._rng.randint(0, self.GRID_COLS - 1)
            self.grid[r][c] = color
        self.jammed_count = 0
        self.security_timer = 0

    def _handle_click(self, col: int, row: int) -> bool:
        if col < 0 or col >= self.GRID_COLS or row < 0 or row >= self.GRID_ROWS:
            return False
        if self.state[row][col] != PinState.LOCKED:
            return False
        self.state[row][col] = PinState.SET
        tumbler_color = self.grid[row][col]
        if self.prev_color is not None and tumbler_color == self.prev_color:
            self.combo += 1
        else:
            self.combo = 1
        self.prev_color = tumbler_color
        self.max_combo = max(self.max_combo, self.combo)
        self.tension = min(self.MAX_TENSION, self.tension + self.TENSION_PER_CLICK)

        if self.combo >= 4:
            multiplier = 3.0
        elif self.combo >= 3:
            multiplier = 2.0
        elif self.combo >= 2:
            multiplier = 1.5
        else:
            multiplier = 1.0
        add = int(100 * multiplier)
        self.score += add

        cx = self.GRID_X + col * (self.CELL_SIZE + self.CELL_GAP) + self.CELL_SIZE // 2
        cy = self.GRID_Y + row * (self.CELL_SIZE + self.CELL_GAP) + self.CELL_SIZE // 2
        self._spawn_particles(cx, cy, COLOR_VALS[tumbler_color], 6)
        self._spawn_floating_text(cx, cy, f"+{add}", YELLOW)

        if self.tension >= self.MAX_TENSION:
            self.phase = Phase.GAME_OVER
            self._spawn_particles(cx, cy, RED, 10)
            if self.score > self.high_score:
                self.high_score = self.score
            return True

        if self.combo >= self.SYNTHESIS_THRESHOLD:
            steps = self._bfs_synthesis(col, row)
            if steps:
                self.synth_steps = steps
                self.synth_step_idx = 0
                self.synth_bonus = 0
                self.synth_anim_timer = 0
                self.phase = Phase.SYNTHESIS_ANIM
                return True

        if self._all_set():
            self.phase = Phase.LOCK_CLEAR
            clear_bonus = self.tension * 10
            self.score += clear_bonus
            self.locks_cleared += 1
            self.final_score_breakdown = [
                f"CLEAR BONUS: +{clear_bonus}",
                f"COMBO MAX: x{self.max_combo}",
                f"TENSION LEFT: {self.tension}%",
            ]
            self._spawn_particles(self.SCREEN_W // 2, self.SCREEN_H // 2, WHITE, 20)
            if self.score > self.high_score:
                self.high_score = self.score

        return True

    def _bfs_synthesis(self, start_col: int, start_row: int) -> list[SynthesisStep]:
        target_color = self.grid[start_row][start_col]
        visited: set[tuple[int, int]] = {(start_col, start_row)}
        queue: deque[tuple[int, int]] = deque()
        result: list[SynthesisStep] = []

        dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        for dc, dr in dirs:
            nc, nr = start_col + dc, start_row + dr
            if 0 <= nc < self.GRID_COLS and 0 <= nr < self.GRID_ROWS:
                if (nc, nr) not in visited:
                    visited.add((nc, nr))
                    if self.grid[nr][nc] == target_color and self.state[nr][nc] == PinState.LOCKED:
                        queue.append((nc, nr))

        while queue:
            col, row = queue.popleft()
            result.append(SynthesisStep(col=col, row=row, color=target_color))
            self.state[row][col] = PinState.SET
            self.synth_bonus += 200
            self.score += 200

            for dc, dr in dirs:
                nc, nr = col + dc, row + dr
                if 0 <= nc < self.GRID_COLS and 0 <= nr < self.GRID_ROWS:
                    if (nc, nr) not in visited:
                        visited.add((nc, nr))
                        if self.grid[nr][nc] == target_color and self.state[nr][nc] == PinState.LOCKED:
                            queue.append((nc, nr))

        return result

    def _release_tension(self) -> None:
        self.tension = 0
        self.combo = 0
        self.prev_color = None
        self.security_timer = 0

    def _update_security(self) -> None:
        self.security_timer += 1
        if self.security_timer >= self.SECURITY_INTERVAL:
            self.security_timer = 0
            locked_cells: list[tuple[int, int]] = []
            for r in range(self.GRID_ROWS):
                for c in range(self.GRID_COLS):
                    if self.state[r][c] == PinState.LOCKED:
                        locked_cells.append((c, r))
            if locked_cells:
                col, row = self._rng.choice(locked_cells)
                self.state[row][col] = PinState.JAMMED
                self.jammed_count += 1
                cx = self.GRID_X + col * (self.CELL_SIZE + self.CELL_GAP) + self.CELL_SIZE // 2
                cy = self.GRID_Y + row * (self.CELL_SIZE + self.CELL_GAP) + self.CELL_SIZE // 2
                self._spawn_particles(cx, cy, GRAY, 4)

            dirs_8 = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
            new_jammed: list[tuple[int, int]] = []
            for r in range(self.GRID_ROWS):
                for c in range(self.GRID_COLS):
                    if self.state[r][c] == PinState.JAMMED:
                        for dc, dr in dirs_8:
                            nc, nr = c + dc, r + dr
                            if 0 <= nc < self.GRID_COLS and 0 <= nr < self.GRID_ROWS:
                                if self.state[nr][nc] == PinState.LOCKED:
                                    if self._rng.random() < 0.5:
                                        new_jammed.append((nc, nr))
            for nc, nr in new_jammed:
                self.state[nr][nc] = PinState.JAMMED
                self.jammed_count += 1

            if self.jammed_count >= self.MAX_JAMMED:
                self.phase = Phase.GAME_OVER
                if self.score > self.high_score:
                    self.high_score = self.score

    def _check_game_over(self) -> bool:
        return self.tension >= self.MAX_TENSION or self.jammed_count >= self.MAX_JAMMED or self.game_timer <= 0

    def _all_set(self) -> bool:
        for r in range(self.GRID_ROWS):
            for c in range(self.GRID_COLS):
                if self.state[r][c] != PinState.SET:
                    return False
        return True

    def _count_set(self) -> int:
        count = 0
        for r in range(self.GRID_ROWS):
            for c in range(self.GRID_COLS):
                if self.state[r][c] == PinState.SET:
                    count += 1
        return count

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-1.5, 1.5)
            vy = self._rng.uniform(-1.5, 1.5)
            life = self._rng.randint(15, 25)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        life = self._rng.randint(20, 30)
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=life, color=color))

    def _grid_to_screen(self, col: int, row: int) -> tuple[int, int]:
        sx = self.GRID_X + col * (self.CELL_SIZE + self.CELL_GAP)
        sy = self.GRID_Y + row * (self.CELL_SIZE + self.CELL_GAP)
        return sx, sy

    def _cell_at_mouse(self) -> tuple[int, int] | None:
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        for r in range(self.GRID_ROWS):
            for c in range(self.GRID_COLS):
                sx, sy = self._grid_to_screen(c, r)
                if sx <= mx < sx + self.CELL_SIZE and sy <= my < sy + self.CELL_SIZE:
                    return c, r
        return None

    def update(self) -> None:
        mouse_pressed = pyxel.btn(pyxel.MOUSE_BUTTON_LEFT)
        mouse_clicked = mouse_pressed and not self._prev_mouse_pressed
        self._prev_mouse_pressed = mouse_pressed

        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()
            return

        if self.phase == Phase.TITLE:
            if mouse_clicked or pyxel.btnp(pyxel.KEY_SPACE):
                self.phase = Phase.PLAYING
                self._generate_lock()
                self.score = 0
                self.combo = 0
                self.max_combo = 0
                self.tension = 0
                self.locks_cleared = 0
                self.security_timer = 0
                self.prev_color = None
                self.jammed_count = 0
                self.synth_steps = []
                self.synth_step_idx = 0
                self.synth_bonus = 0
                self.particles = []
                self.floating_texts = []
                self._shake_frames = 0
                self.game_timer = 90 * 30
                self.final_score_breakdown = []
                self.synth_anim_timer = 0
            return

        if self.phase == Phase.LOCK_CLEAR:
            if mouse_clicked or pyxel.btnp(pyxel.KEY_SPACE):
                self.phase = Phase.PLAYING
                self._generate_lock()
                self.combo = 0
                self.max_combo = 0
                self.tension = 0
                self.security_timer = 0
                self.prev_color = None
                self.jammed_count = 0
                self.synth_steps = []
                self.synth_step_idx = 0
                self.synth_bonus = 0
                self.particles = []
                self.floating_texts = []
                self._shake_frames = 0
                self.game_timer = 90 * 30
                self.final_score_breakdown = []
                self.synth_anim_timer = 0
            return

        if self.phase == Phase.GAME_OVER:
            if mouse_clicked or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
            return

        if self.phase == Phase.SYNTHESIS_ANIM:
            self.synth_anim_timer += 1
            if self.synth_step_idx < len(self.synth_steps):
                step = self.synth_steps[self.synth_step_idx]
                self.state[step.row][step.col] = PinState.SET
                cx = self.GRID_X + step.col * (self.CELL_SIZE + self.CELL_GAP) + self.CELL_SIZE // 2
                cy = self.GRID_Y + step.row * (self.CELL_SIZE + self.CELL_GAP) + self.CELL_SIZE // 2
                self._spawn_particles(cx, cy, COLOR_VALS[step.color], 3)
                self._spawn_floating_text(cx, cy, "+200", YELLOW)
                self.synth_step_idx += 1
            if self.synth_step_idx >= len(self.synth_steps) or self.synth_anim_timer >= self.synth_anim_duration:
                self.phase = Phase.PLAYING
                if self._all_set():
                    self.phase = Phase.LOCK_CLEAR
                    clear_bonus = self.tension * 10
                    self.score += clear_bonus
                    self.locks_cleared += 1
                    self.final_score_breakdown = [
                        f"CLEAR BONUS: +{clear_bonus}",
                        f"COMBO MAX: x{self.max_combo}",
                        f"TENSION LEFT: {self.tension}%",
                    ]
                    self._spawn_particles(self.SCREEN_W // 2, self.SCREEN_H // 2, WHITE, 20)
                    if self.score > self.high_score:
                        self.high_score = self.score
            return

        if self.phase == Phase.PLAYING:
            self.game_timer -= 1
            if self.game_timer <= 0:
                self.phase = Phase.GAME_OVER
                if self.score > self.high_score:
                    self.high_score = self.score
                return

            if pyxel.btnp(pyxel.KEY_SPACE):
                self._release_tension()

            if mouse_clicked:
                cell = self._cell_at_mouse()
                if cell is not None:
                    col, row = cell
                    self._handle_click(col, row)
                    if self.phase != Phase.PLAYING:
                        return

            if self.tension >= self.SECURITY_THRESHOLD:
                self._update_security()
                if self.phase != Phase.PLAYING:
                    return

            if self._check_game_over():
                self.phase = Phase.GAME_OVER
                if self.score > self.high_score:
                    self.high_score = self.score

        self._update_particles()
        self._update_floating_texts()

    def _update_particles(self) -> None:
        for p in self.particles:
            p.vy += 0.05
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.8
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def draw(self) -> None:
        pyxel.cls(NAVY)

        if self._shake_frames > 0:
            ox = self._rng.randint(-2, 2)
            oy = self._rng.randint(-2, 2)
            pyxel.camera(ox, oy)
            self._shake_frames -= 1
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_grid()
            self._draw_hud()
            self._draw_particles()
            self._draw_floating_texts()
        elif self.phase == Phase.SYNTHESIS_ANIM:
            self._draw_grid()
            self._draw_hud()
            self._draw_particles()
            self._draw_floating_texts()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        elif self.phase == Phase.LOCK_CLEAR:
            self._draw_lock_clear()
            self._draw_particles()

    def _draw_title(self) -> None:
        pyxel.text(self.SCREEN_W // 2 - 44, 20, "LOCKPICK SURGE", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 38, 32, "==============", CYAN)

        pyxel.text(self.SCREEN_W // 2 - 55, 60, "Click tumblers to set them", LIME)
        pyxel.text(self.SCREEN_W // 2 - 58, 70, "Same color = COMBO chain", LIME)
        pyxel.text(self.SCREEN_W // 2 - 57, 80, "COMBO x4 = SYNTHESIS!", YELLOW)
        pyxel.text(self.SCREEN_W // 2 - 58, 90, "SPACE = Release Tension", LIME)

        pyxel.text(self.SCREEN_W // 2 - 50, 110, "- Rules -", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 60, 120, "Set all 20 tumblers to clear", GREEN)
        pyxel.text(self.SCREEN_W // 2 - 60, 130, "Tension 70%+ -> Jamming spreads", ORANGE)
        pyxel.text(self.SCREEN_W // 2 - 60, 140, "8 jammed pins -> GAME OVER", RED)

        if self.high_score > 0:
            pyxel.text(self.SCREEN_W // 2 - 38, 170, f"HIGH SCORE: {self.high_score}", YELLOW)

        pyxel.text(self.SCREEN_W // 2 - 48, 210, "Click or SPACE to start", WHITE)

    def _draw_grid(self) -> None:
        for r in range(self.GRID_ROWS):
            for c in range(self.GRID_COLS):
                sx, sy = self._grid_to_screen(c, r)
                state = self.state[r][c]
                color_idx = self.grid[r][c]
                cell_color = COLOR_VALS[color_idx]

                if state == PinState.JAMMED:
                    pyxel.rect(sx, sy, self.CELL_SIZE, self.CELL_SIZE, GRAY)
                    pyxel.rectb(sx, sy, self.CELL_SIZE, self.CELL_SIZE, DARK_BLUE)
                    pyxel.line(sx, sy, sx + self.CELL_SIZE - 1, sy + self.CELL_SIZE - 1, RED)
                    pyxel.line(sx + self.CELL_SIZE - 1, sy, sx, sy + self.CELL_SIZE - 1, RED)
                elif state == PinState.SET:
                    pyxel.rect(sx, sy - 2, self.CELL_SIZE, self.CELL_SIZE - 2, WHITE)
                    pyxel.rectb(sx, sy - 2, self.CELL_SIZE, self.CELL_SIZE - 2, CYAN)
                elif state == PinState.LOCKED:
                    pyxel.rect(sx, sy, self.CELL_SIZE, self.CELL_SIZE, cell_color)
                    pyxel.rectb(sx, sy, self.CELL_SIZE, self.CELL_SIZE, DARK_BLUE)
                    pyxel.rect(sx + 2, sy + 2, self.CELL_SIZE - 4, self.CELL_SIZE - 4, cell_color)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)
        pyxel.text(4, 12, f"LOCKS: {self.locks_cleared}", WHITE)

        time_left = max(0, self.game_timer) // 30
        time_color = GREEN if time_left > 30 else (YELLOW if time_left > 10 else RED)
        pyxel.text(self.SCREEN_W - 70, 4, f"TIME: {time_left}", time_color)

        if self.combo >= 2:
            if self.combo >= 4:
                combo_color = RED
            elif self.combo >= 3:
                combo_color = ORANGE
            else:
                combo_color = YELLOW
            combo_text = f"COMBO x{self.combo}"
            pyxel.text(self.SCREEN_W // 2 - 28, self.GRID_Y + self.GRID_ROWS * (self.CELL_SIZE + self.CELL_GAP) + 6, combo_text, combo_color)

        pyxel.text(4, 20, f"MAX COMBO: x{self.max_combo}", CYAN)

        bar_x = 280
        bar_y = 20
        bar_w = 20
        bar_h = 200
        pyxel.rectb(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2, WHITE)
        fill_h = int(bar_h * self.tension / self.MAX_TENSION)
        if self.tension >= self.SECURITY_THRESHOLD:
            bar_color = RED
        elif self.tension >= 50:
            bar_color = YELLOW
        else:
            bar_color = GREEN
        pyxel.rect(bar_x, bar_y + bar_h - fill_h, bar_w, fill_h, bar_color)
        pyxel.text(bar_x - 14, bar_y + bar_h + 6, "TENSION", WHITE)
        pyxel.text(bar_x + 4, bar_y + bar_h // 2 - 4, f"{self.tension}%", WHITE)

        progress = self._count_set()
        pyxel.text(self.GRID_X, self.GRID_Y - 10, f"SET: {progress}/20", WHITE)

        if self.tension >= self.SECURITY_THRESHOLD:
            warn_x = self.GRID_X + self.GRID_COLS * (self.CELL_SIZE + self.CELL_GAP) + 30
            warn_y = self.GRID_Y + self.GRID_ROWS * (self.CELL_SIZE + self.CELL_GAP) - 10
            pyxel.text(warn_x - 20, warn_y, "! JAMMING !", RED)

    def _draw_game_over(self) -> None:
        pyxel.text(self.SCREEN_W // 2 - 40, 50, "LOCK JAMMED!", RED)
        pyxel.text(self.SCREEN_W // 2 - 48, 64, "============", RED)

        pyxel.text(self.SCREEN_W // 2 - 35, 90, f"SCORE: {self.score}", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 45, 100, f"MAX COMBO: x{self.max_combo}", CYAN)
        pyxel.text(self.SCREEN_W // 2 - 48, 110, f"LOCKS CLEARED: {self.locks_cleared}", LIME)
        pyxel.text(self.SCREEN_W // 2 - 38, 120, f"TENSION: {self.tension}%", RED)

        if self.score == self.high_score and self.score > 0:
            pyxel.text(self.SCREEN_W // 2 - 42, 140, "** NEW HIGH SCORE! **", YELLOW)

        if self.jammed_count >= self.MAX_JAMMED:
            pyxel.text(self.SCREEN_W // 2 - 55, 155, "Too many pins jammed!", GRAY)
        elif self.tension >= self.MAX_TENSION:
            pyxel.text(self.SCREEN_W // 2 - 48, 155, "Tension overload!", GRAY)
        elif self.game_timer <= 0:
            pyxel.text(self.SCREEN_W // 2 - 38, 155, "Time ran out!", GRAY)

        pyxel.text(self.SCREEN_W // 2 - 52, 210, "Click or SPACE to retry", WHITE)

    def _draw_lock_clear(self) -> None:
        pyxel.text(self.SCREEN_W // 2 - 42, 50, "LOCK CLEARED!", LIME)
        pyxel.text(self.SCREEN_W // 2 - 50, 62, "=============", LIME)

        pyxel.text(self.SCREEN_W // 2 - 35, 90, f"SCORE: {self.score}", WHITE)

        y_off = 100
        for line in self.final_score_breakdown:
            pyxel.text(self.SCREEN_W // 2 - 40, y_off, line, CYAN)
            y_off += 10

        pyxel.text(self.SCREEN_W // 2 - 43, y_off + 10, f"LOCKS CLEARED: {self.locks_cleared}", LIME)

        if self.score == self.high_score and self.score > 0:
            pyxel.text(self.SCREEN_W // 2 - 42, y_off + 30, "** NEW HIGH SCORE! **", YELLOW)

        pyxel.text(self.SCREEN_W // 2 - 60, 210, "Click or SPACE for next lock", WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            px = int(p.x)
            py = int(p.y)
            if 0 <= px < self.SCREEN_W and 0 <= py < self.SCREEN_H:
                pyxel.pset(px, py, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = min(255, max(0, ft.life * 10))
            if alpha > 200:
                pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)
            elif alpha > 100:
                pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, GRAY)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
