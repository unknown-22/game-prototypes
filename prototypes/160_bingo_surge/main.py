"""BINGO SURGE — Color-match BINGO game."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Phase Enum ──


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ── Data Classes ──


@dataclass
class BingoCell:
    number: int  # 1-25
    color: int  # 0-3
    marked: bool = False


@dataclass
class CallBall:
    number: int  # 1-25
    color: int  # 0-3
    x: float
    y: float
    timer: float
    alive: bool = True


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


# ── Constants ──

SCREEN_W = 320
SCREEN_H = 240
GRID_SIZE = 5
CELL_SIZE = 32
CELL_GAP = 2
STEP = CELL_SIZE + CELL_GAP
GRID_LEFT = 16
GRID_TOP = 30
CALL_X = 256
CALL_Y = 80
BALL_RADIUS = 22
BALL_LIFETIME = 180  # 3 seconds at 60fps
SUPER_DURATION = 300  # 5 seconds at 60fps
GAME_DURATION = 5400  # 90 seconds at 60fps
HEAT_MAX = 100.0
HEAT_DECAY = 0.03
COMBO_THRESHOLD = 5
SPAWN_INTERVAL = 10  # frames between spawn attempts

COLORS = [8, 3, 10, 6]  # RED, GREEN, YELLOW, LIGHT_BLUE
COLOR_NAMES = ["RED", "GREEN", "YELLOW", "BLUE"]

# Pyxel palette (aliases for readability)
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

RAINBOW = [RED, ORANGE, YELLOW, GREEN, LIGHT_BLUE, PURPLE]

# ── Game Class ──


class Game:
    def __init__(self) -> None:
        self.grid: list[list[BingoCell]] = []
        self.current_ball: CallBall | None = None
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.heat: float = 0.0
        self.super_timer: int = 0
        self.game_timer: int = GAME_DURATION
        self.phase: Phase = Phase.TITLE
        self.particles: list[Particle] = []
        self.last_marked_color: int | None = None
        self.bingo_lines_cleared: int = 0
        self.rng: random.Random = random.Random()
        self._spawn_cooldown: int = 0
        self._title_blink: int = 0
        self._go_blink: int = 0

    def reset(self) -> None:
        self.grid = self._generate_grid()
        self.current_ball = None
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.heat = 0.0
        self.super_timer = 0
        self.game_timer = GAME_DURATION
        self.phase = Phase.PLAYING
        self.particles = []
        self.last_marked_color = None
        self.bingo_lines_cleared = 0
        self._spawn_cooldown = 0

    def _generate_grid(self) -> list[list[BingoCell]]:
        numbers = self.rng.sample(range(1, 26), 25)
        grid: list[list[BingoCell]] = []
        for row in range(GRID_SIZE):
            cell_row: list[BingoCell] = []
            for col in range(GRID_SIZE):
                idx = row * GRID_SIZE + col
                color = self.rng.randint(0, 3)
                cell_row.append(BingoCell(number=numbers[idx], color=color))
            grid.append(cell_row)
        return grid

    # ── Per-frame update ──

    def update(self) -> None:
        self._title_blink = (self._title_blink + 1) % 60
        self._go_blink = (self._go_blink + 1) % 60

        if self.phase != Phase.PLAYING:
            return

        self.game_timer -= 1
        if self.game_timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        if self.super_timer > 0:
            self.super_timer -= 1

        if self.current_ball is None:
            self._spawn_cooldown -= 1
            if self._spawn_cooldown <= 0:
                self._spawn_ball()
                self._spawn_cooldown = SPAWN_INTERVAL
        else:
            self.current_ball.timer -= 1
            if self.current_ball.timer <= 0:
                self._on_ball_expired()
            elif self.super_timer > 0:
                self._auto_mark_current_ball()

        self._update_heat()
        self._update_particles()

    # ── Ball spawning ──

    def _spawn_ball(self) -> None:
        number = self.rng.randint(1, 25)
        color = self.rng.randint(0, 3)
        self.current_ball = CallBall(
            number=number,
            color=color,
            x=float(CALL_X),
            y=float(CALL_Y),
            timer=float(BALL_LIFETIME),
        )

    def _on_ball_expired(self) -> None:
        self.heat = min(self.heat + 20, HEAT_MAX)
        self.combo = 0
        self.last_marked_color = None
        self._spawn_particles(
            float(CALL_X), float(CALL_Y), RED, 4, 8, spread=2.0, vy_min=-2.0, vy_max=-0.5
        )
        self.current_ball = None
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER

    def _auto_mark_current_ball(self) -> None:
        if self.current_ball is None or not self.current_ball.alive:
            return
        ball = self.current_ball
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                cell = self.grid[row][col]
                if not cell.marked and cell.number == ball.number:
                    self._mark_cell(col, row, is_match=True, multiplier=3)
                    self.current_ball = None
                    return

    # ── Click handling ──

    def _handle_click(self, col: int, row: int) -> str:
        if self.phase != Phase.PLAYING:
            return "no_play"
        if self.current_ball is None:
            return "no_ball"

        cell = self.grid[row][col]
        if cell.marked:
            return "already_marked"

        ball = self.current_ball
        is_match = (cell.number == ball.number and cell.color == ball.color)
        multiplier = 3 if self.super_timer > 0 else 1

        self._mark_cell(col, row, is_match=is_match, multiplier=multiplier)
        return "match" if is_match else "mismatch"

    def _mark_cell(self, col: int, row: int, *, is_match: bool, multiplier: int) -> None:
        cell = self.grid[row][col]
        cell.marked = True
        cx = float(GRID_LEFT + col * STEP + CELL_SIZE // 2)
        cy = float(GRID_TOP + row * STEP + CELL_SIZE // 2)

        if is_match:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            base = 10 + self.combo * 5
            gained = base * multiplier
            self.score += gained
            self.last_marked_color = cell.color
            self._spawn_particles(cx, cy, COLORS[cell.color], 4, 8, spread=3.0, vy_min=-3.0, vy_max=-1.0)
            if self.combo >= COMBO_THRESHOLD and self.super_timer == 0:
                self._activate_super()
            if self.super_timer > 0:
                self._ca_spread(col, row)
        else:
            self.heat = min(self.heat + 15, HEAT_MAX)
            self.combo = 0
            self.last_marked_color = None
            gained = 5 * multiplier
            self.score += gained
            self._spawn_particles(cx, cy, RED, 3, 8, spread=1.5, vy_min=-2.0, vy_max=-0.5)
            if self.heat >= HEAT_MAX:
                self.phase = Phase.GAME_OVER

        self.current_ball = None
        self._check_and_clear_bingo()

    # ── BINGO check ──

    def _check_bingo(self) -> list[list[tuple[int, int]]]:
        lines: list[list[tuple[int, int]]] = []
        for r in range(GRID_SIZE):
            if all(self.grid[r][c].marked for c in range(GRID_SIZE)):
                lines.append([(r, c) for c in range(GRID_SIZE)])
        for c in range(GRID_SIZE):
            if all(self.grid[r][c].marked for r in range(GRID_SIZE)):
                lines.append([(r, c) for r in range(GRID_SIZE)])
        if all(self.grid[i][i].marked for i in range(GRID_SIZE)):
            lines.append([(i, i) for i in range(GRID_SIZE)])
        if all(self.grid[i][GRID_SIZE - 1 - i].marked for i in range(GRID_SIZE)):
            lines.append([(i, GRID_SIZE - 1 - i) for i in range(GRID_SIZE)])
        return lines

    def _check_and_clear_bingo(self) -> None:
        lines = self._check_bingo()
        for cells in lines:
            self.bingo_lines_cleared += 1
            bonus = 100 * (1 + self.bingo_lines_cleared) * (3 if self.super_timer > 0 else 1)
            self.score += bonus
            self._clear_bingo_line(cells)
            self._spawn_bingo_burst()

    def _clear_bingo_line(self, cells: list[tuple[int, int]]) -> None:
        used_numbers: set[int] = set()
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if not self.grid[r][c].marked:
                    used_numbers.add(self.grid[r][c].number)

        for r, c in cells:
            self.grid[r][c].marked = False

        refill_numbers: list[int] = []
        for _ in cells:
            available = [n for n in range(1, 26) if n not in used_numbers and n not in refill_numbers]
            if not available:
                available = [n for n in range(1, 26) if n not in used_numbers]
            chosen = self.rng.choice(available)
            refill_numbers.append(chosen)

        for i, (r, c) in enumerate(cells):
            self.grid[r][c].number = refill_numbers[i]
            self.grid[r][c].color = self.rng.randint(0, 3)

    # ── SUPER BINGO ──

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        gx = float(GRID_LEFT + GRID_SIZE * STEP // 2)
        gy = float(GRID_TOP + GRID_SIZE * STEP // 2)
        for _ in range(20):
            self.particles.append(
                Particle(
                    x=gx + self.rng.uniform(-40, 40),
                    y=gy + self.rng.uniform(-40, 40),
                    vx=self.rng.uniform(-3, 3),
                    vy=self.rng.uniform(-3, 3),
                    color=self.rng.choice(RAINBOW),
                    life=self.rng.randint(15, 30),
                )
            )

    def _ca_spread(self, col: int, row: int) -> None:
        target_number = self.grid[row][col].number
        visited: set[tuple[int, int]] = set()
        stack = [(col, row)]
        while stack:
            c, r = stack.pop()
            if (c, r) in visited:
                continue
            if not (0 <= c < GRID_SIZE and 0 <= r < GRID_SIZE):
                continue
            if self.grid[r][c].number != target_number:
                continue
            visited.add((c, r))
            if not self.grid[r][c].marked:
                self.grid[r][c].marked = True
                cx = float(GRID_LEFT + c * STEP + CELL_SIZE // 2)
                cy = float(GRID_TOP + r * STEP + CELL_SIZE // 2)
                self.score += 50 * 3
                self._spawn_particles(cx, cy, COLORS[self.grid[r][c].color], 3, 6, spread=2.0, vy_min=-2.0, vy_max=-0.5)
            for dc, dr in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
                nc, nr = c + dc, r + dr
                if (nc, nr) not in visited:
                    stack.append((nc, nr))

        if visited:
            self._check_and_clear_bingo()

    # ── HEAT ──

    def _update_heat(self) -> None:
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER

    # ── Particles ──

    def _spawn_particles(
        self,
        x: float,
        y: float,
        color: int,
        count: int,
        life: int,
        *,
        spread: float = 2.0,
        vy_min: float = -3.0,
        vy_max: float = -1.0,
    ) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=x + self.rng.uniform(-4, 4),
                    y=y + self.rng.uniform(-4, 4),
                    vx=self.rng.uniform(-spread, spread),
                    vy=self.rng.uniform(vy_min, vy_max),
                    color=color,
                    life=self.rng.randint(max(4, life - 2), life + 2),
                )
            )

    def _spawn_bingo_burst(self) -> None:
        gx = float(GRID_LEFT + GRID_SIZE * STEP // 2)
        gy = float(GRID_TOP + GRID_SIZE * STEP // 2)
        for _ in range(12):
            self.particles.append(
                Particle(
                    x=gx + self.rng.uniform(-60, 60),
                    y=gy + self.rng.uniform(-60, 60),
                    vx=self.rng.uniform(-4, 4),
                    vy=self.rng.uniform(-4, 4),
                    color=YELLOW,
                    life=self.rng.randint(15, 25),
                )
            )

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    # ── Drawing ──

    def draw(self) -> None:
        pyxel.cls(NAVY)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game()
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(112, 60, "BINGO SURGE", WHITE)
        pyxel.text(116, 76, "Color-Match Bingo", LIGHT_BLUE)
        pyxel.text(90, 102, "Click matching numbers!", GRAY)
        pyxel.text(70, 117, "Same color = COMBO chain", GRAY)
        pyxel.text(70, 132, f"COMBO {COMBO_THRESHOLD}+ = SUPER BINGO!", YELLOW)
        pyxel.text(70, 147, "Wrong color builds HEAT", ORANGE)
        pyxel.text(70, 162, "Clear lines for BONUS", GREEN)
        if self._title_blink < 30:
            pyxel.text(100, 200, "Press SPACE to start", WHITE)

    def _draw_game(self) -> None:
        rainbow_idx = (pyxel.frame_count // 4) % len(RAINBOW)

        if self.super_timer > 0:
            border_color = RAINBOW[rainbow_idx]
            for t in range(3):
                pyxel.rectb(
                    GRID_LEFT - 3 - t,
                    GRID_TOP - 3 - t,
                    GRID_SIZE * STEP + 6 + t * 2,
                    GRID_SIZE * STEP + 6 + t * 2,
                    border_color,
                )

        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                cell = self.grid[row][col]
                cx = GRID_LEFT + col * STEP
                cy = GRID_TOP + row * STEP
                bg = COLORS[cell.color]
                if cell.marked:
                    pyxel.rect(cx, cy, CELL_SIZE, CELL_SIZE, bg + 1 if bg < 15 else bg - 1)
                else:
                    pyxel.rect(cx, cy, CELL_SIZE, CELL_SIZE, bg)
                if cell.marked:
                    pyxel.rectb(cx, cy, CELL_SIZE, CELL_SIZE, WHITE)
                num_str = str(cell.number)
                tx = cx + (CELL_SIZE - len(num_str) * 4) // 2
                pyxel.text(tx, cy + 12, num_str, WHITE)
                if self.super_timer > 0 and cell.marked:
                    pyxel.rectb(cx + 1, cy + 1, CELL_SIZE - 2, CELL_SIZE - 2, RAINBOW[rainbow_idx])

        self._draw_call_area()
        self._draw_hud()
        self._draw_particles()

    def _draw_call_area(self) -> None:
        pyxel.rectb(196, 0, 124, 240, GRAY)
        pyxel.text(210, 8, "CALL", WHITE)

        if self.current_ball is not None:
            ball = self.current_ball
            bx = int(ball.x)
            by = int(ball.y)
            ball_color = COLORS[ball.color]
            pyxel.circ(bx, by, BALL_RADIUS, ball_color)
            pyxel.circb(bx, by, BALL_RADIUS, WHITE)
            num_str = str(ball.number)
            tx = bx - len(num_str) * 2
            pyxel.text(tx, by - 4, num_str, WHITE)

            timer_ratio = ball.timer / BALL_LIFETIME
            if timer_ratio > 0.66:
                ring_color = GREEN
            elif timer_ratio > 0.33:
                ring_color = YELLOW
            else:
                ring_color = RED
            ring_r = int(BALL_RADIUS + 4)
            segments = 16
            visible_segments = int(segments * timer_ratio)
            for i in range(visible_segments):
                angle = (i / segments) * 2 * 3.14159 - 3.14159 / 2
                sx = bx + math.cos(angle) * ring_r
                sy = by + math.sin(angle) * ring_r
                ex = bx + math.cos(angle + 2 * 3.14159 / segments) * ring_r
                ey = by + math.sin(angle + 2 * 3.14159 / segments) * ring_r
                pyxel.line(int(sx), int(sy), int(ex), int(ey), ring_color)

        if self.super_timer > 0:
            sc = RAINBOW[(pyxel.frame_count // 4) % len(RAINBOW)]
            pyxel.text(210, 140, "SUPER!", sc)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)
        pyxel.text(4, 14, f"COMBO: x{self.combo}", YELLOW)
        pyxel.text(4, 24, f"TIME: {self.game_timer // 60}s", WHITE)

        heat_w = 100
        bar_x = 200
        bar_y = 180
        pyxel.rect(bar_x, bar_y, heat_w, 8, GRAY)
        hw = int(heat_w * self.heat / HEAT_MAX)
        if self.heat < 30:
            hc = GREEN
        elif self.heat < 60:
            hc = YELLOW
        elif self.heat < 85:
            hc = ORANGE
        else:
            hc = RED
        pyxel.rect(bar_x, bar_y, hw, 8, hc)
        pyxel.rectb(bar_x, bar_y, heat_w, 8, WHITE)
        pyxel.text(bar_x, bar_y + 10, f"HEAT {int(self.heat)}", WHITE)

        if self.super_timer > 0:
            sr = self.super_timer / SUPER_DURATION
            sdw = int(100 * sr)
            pyxel.rect(bar_x, bar_y + 22, 100, 4, GRAY)
            sc = RAINBOW[(pyxel.frame_count // 4) % len(RAINBOW)]
            pyxel.rect(bar_x, bar_y + 22, sdw, 4, sc)

        pyxel.text(200, 210, f"BINGOs: {self.bingo_lines_cleared}", WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_game_over(self) -> None:
        pyxel.rect(45, 45, 230, 160, BLACK)
        pyxel.rectb(45, 45, 230, 160, WHITE)
        pyxel.text(112, 55, "BINGO OVER", YELLOW)
        pyxel.text(65, 80, f"SCORE:        {self.score}", WHITE)
        pyxel.text(65, 96, f"MAX COMBO:    x{self.max_combo}", YELLOW)
        pyxel.text(65, 112, f"BINGOs:       {self.bingo_lines_cleared}", WHITE)
        pyxel.text(65, 128, f"TIME LEFT:    {max(0, self.game_timer // 60)}s", GRAY)
        cause = "HEAT OVERLOAD" if self.heat >= HEAT_MAX else "TIME UP"
        pyxel.text(65, 144, f"CAUSE:        {cause}", RED if self.heat >= HEAT_MAX else GRAY)
        if self._go_blink < 30:
            pyxel.text(75, 180, "Press SPACE to retry", WHITE)


# ── Pyxel App ──


class App:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="BINGO SURGE", display_scale=2)
        pyxel.mouse(True)
        self.game = Game()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        g = self.game

        if g.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                g.reset()
        elif g.phase == Phase.PLAYING:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                mx = pyxel.mouse_x
                my = pyxel.mouse_y
                col = (mx - GRID_LEFT) // STEP
                row = (my - GRID_TOP) // STEP
                lx = (mx - GRID_LEFT) % STEP
                ly = (my - GRID_TOP) % STEP
                if 0 <= col < GRID_SIZE and 0 <= row < GRID_SIZE and lx < CELL_SIZE and ly < CELL_SIZE:
                    g._handle_click(col, row)
        elif g.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                g.reset()

        g.update()

    def draw(self) -> None:
        self.game.draw()


def main() -> None:
    App()


if __name__ == "__main__":
    main()
