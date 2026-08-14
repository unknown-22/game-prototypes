import math
import random
from dataclasses import dataclass
from enum import Enum

import pyxel

# Raw 16-color palette (pyxel)
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


class Phase(Enum):
    TITLE = 0
    PLAYING = 1
    CRANE_COMPLETE = 2
    GAME_OVER = 3


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    gravity: float = 0.12


@dataclass
class FloatingText:
    x: int
    y: int
    text: str
    life: int
    color: int


class Game:
    SCREEN_W = 320
    SCREEN_H = 240
    CELL = 22
    PAPER_X = 72
    PAPER_Y = 36
    MAX_HEAT = 100
    SUPER_DURATION = 300
    TIME_START = 3600
    # index = color id (0..4) -> RED, LIME, DARK_BLUE, YELLOW, ORANGE
    COLOR_VALS: tuple[int, ...] = (8, 11, 5, 10, 9)

    def __init__(self) -> None:
        pyxel.init(self.SCREEN_W, self.SCREEN_H, title="ORIGAMI CHAIN", fps=60, display_scale=2)
        self._init_state()

    def _init_state(self) -> None:
        self.best_score = 0
        self.rng = random.Random()
        self.phase = Phase.TITLE
        self.reset()
        self.phase = Phase.TITLE

    def reset(self) -> None:
        self.rows = 8
        self.cols = 8
        self.num_colors = 3
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.heat = 0.0
        self.super_mode = False
        self.super_timer = 0
        self.time_left = self.TIME_START
        self.phase = Phase.PLAYING
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shake_frames = 0
        self.crane_frames = 0
        self._new_sheet()

    # ------------------------------------------------------------------ #
    # Pure logic (no pyxel input/init; safe for headless tests)
    # ------------------------------------------------------------------ #

    def _new_sheet(self) -> None:
        self.rows = 8
        self.cols = 8
        self.paper = [[self.rng.randrange(self.num_colors) for _ in range(8)] for _ in range(8)]

    def _resolve_pair(self, v1: int, v2: int) -> tuple[int, bool, bool]:
        if v1 == -1 or v2 == -1:
            return (-1, False, False)
        if self.super_mode:
            return (v1, True, False)
        if v1 == v2:
            return (v1, True, False)
        return (-1, False, True)

    def _register_fusion(self, cx: int, cy: int, color_id: int) -> int:
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        mult = 3 if self.super_mode else 1
        gained = 10 * self.combo * mult
        self.score += gained
        self._spawn_burst(cx, cy, self.COLOR_VALS[color_id], 8)
        self._spawn_text(cx, cy - 6, f"+{gained}", self.COLOR_VALS[color_id])
        if self.combo >= 4 and not self.super_mode:
            self.super_mode = True
            self.super_timer = self.SUPER_DURATION
            self._spawn_text(self.PAPER_X + 88, self.PAPER_Y - 10, "SUPER FOLD!", WHITE)
        return gained

    def _register_mismatch(self, cx: int, cy: int) -> None:
        self._add_heat(10.0)
        self._spawn_text(cx, cy - 6, "WRONG!", GRAY)
        self.shake_frames = 6

    def _fold_vertical(self) -> int:
        if self.cols < 2:
            return 0
        old_cols = self.cols
        new_cols = (old_cols + 1) // 2
        score_gained = 0
        any_mismatch = False
        for r in range(self.rows):
            row = self.paper[r]
            new_row: list[int] = []
            for c in range(new_cols):
                mirror = old_cols - 1 - c
                if mirror == c:
                    new_row.append(row[c])
                    continue
                v1 = row[c]
                v2 = row[mirror]
                result, fused, mismatch = self._resolve_pair(v1, v2)
                new_row.append(result)
                cx, cy = self._cell_center(r, c)
                if fused:
                    score_gained += self._register_fusion(cx, cy, v1)
                elif mismatch:
                    any_mismatch = True
                    self._register_mismatch(cx, cy)
            self.paper[r] = new_row
        if any_mismatch:
            self.combo = 0
        self.cols = new_cols
        if self._check_crane_complete():
            self._complete_crane()
        return score_gained

    def _fold_horizontal(self) -> int:
        if self.rows < 2:
            return 0
        old_rows = self.rows
        new_rows = (old_rows + 1) // 2
        score_gained = 0
        any_mismatch = False
        for r in range(new_rows):
            mirror = old_rows - 1 - r
            if mirror == r:
                continue
            for c in range(self.cols):
                v1 = self.paper[r][c]
                v2 = self.paper[mirror][c]
                result, fused, mismatch = self._resolve_pair(v1, v2)
                self.paper[r][c] = result
                cx, cy = self._cell_center(r, c)
                if fused:
                    score_gained += self._register_fusion(cx, cy, v1)
                elif mismatch:
                    any_mismatch = True
                    self._register_mismatch(cx, cy)
        if any_mismatch:
            self.combo = 0
        self.rows = new_rows
        self.paper = self.paper[:new_rows]
        if self._check_crane_complete():
            self._complete_crane()
        return score_gained

    def _check_crane_complete(self) -> bool:
        return self.rows == 1 and self.cols == 1

    def _complete_crane(self) -> None:
        final = self.paper[0][0]
        bonus = 500 if final >= 0 else 100
        self.score += bonus
        self.phase = Phase.CRANE_COMPLETE
        self.crane_frames = 40
        self._new_sheet()
        cx, cy = self.PAPER_X + 4 * self.CELL, self.PAPER_Y + 4 * self.CELL
        self._spawn_text(cx - 20, cy - 20, "CRANE!", WHITE)
        self._spawn_burst(cx, cy, WHITE, 30)
        self.shake_frames = 12

    def _update_difficulty(self) -> None:
        if self.time_left <= 1200:
            self.num_colors = 5
        elif self.time_left <= 2400:
            self.num_colors = 4
        else:
            self.num_colors = 3

    def _update_super(self) -> None:
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0

    def _update_heat(self) -> None:
        if self.heat >= self.MAX_HEAT:
            self._game_over()
            return
        if not self.super_mode:
            self.heat = max(0.0, self.heat - 0.02)

    def _add_heat(self, amount: float) -> None:
        if self.heat >= self.MAX_HEAT:
            self._game_over()
            return
        self.heat += amount
        if self.heat >= self.MAX_HEAT:
            self.heat = float(self.MAX_HEAT)
            self._game_over()

    def _update_timer(self) -> None:
        self.time_left -= 1
        if self.time_left <= 0:
            self.time_left = 0
            self._game_over()

    def _game_over(self) -> None:
        if self.phase != Phase.PLAYING:
            return
        self.phase = Phase.GAME_OVER
        self.best_score = max(self.best_score, self.score)

    # ------------------------------------------------------------------ #
    # Particles / floating text
    # ------------------------------------------------------------------ #

    def _cell_center(self, r: int, c: int) -> tuple[int, int]:
        return (
            self.PAPER_X + c * self.CELL + self.CELL // 2,
            self.PAPER_Y + r * self.CELL + self.CELL // 2,
        )

    def _spawn_burst(self, x: float, y: float, color: int, n: int) -> None:
        for _ in range(n):
            angle = self.rng.uniform(0.0, 2.0 * math.pi)
            speed = self.rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=20 + self.rng.randrange(10),
                    color=color,
                )
            )

    def _spawn_text(self, x: int, y: int, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=45, color=color))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.life -= 1
            p.vy += p.gravity
            p.x += p.vx
            p.y += p.vy
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for t in self.floating_texts:
            t.life -= 1
            t.y -= 1
        self.floating_texts = [t for t in self.floating_texts if t.life > 0]

    def _tick_effects(self) -> None:
        self._update_particles()
        self._update_floating_texts()
        if self.shake_frames > 0:
            self.shake_frames -= 1

    def _inside_paper(self, x: int, y: int) -> bool:
        return (
            self.PAPER_X <= x < self.PAPER_X + self.cols * self.CELL
            and self.PAPER_Y <= y < self.PAPER_Y + self.rows * self.CELL
        )

    # ------------------------------------------------------------------ #
    # Pyxel update / draw
    # ------------------------------------------------------------------ #

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return
        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return
        if self.phase == Phase.CRANE_COMPLETE:
            self.crane_frames -= 1
            if self.crane_frames <= 0:
                self.phase = Phase.PLAYING
            self._tick_effects()
            return
        # PLAYING
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and self._inside_paper(pyxel.mouse_x, pyxel.mouse_y):
            self._fold_vertical()
        if self.phase == Phase.PLAYING and (pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN)):
            self._fold_horizontal()
        if self.phase != Phase.PLAYING:
            return
        self._update_difficulty()
        self._update_super()
        self._update_heat()
        self._update_timer()
        self._tick_effects()

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        else:
            ox = oy = 0
            if self.shake_frames > 0:
                ox = self.rng.randrange(-2, 3)
                oy = self.rng.randrange(-2, 3)
            self._draw_playing(ox, oy)

    def _draw_title(self) -> None:
        pyxel.text((self.SCREEN_W - 13 * 4) // 2, 40, "ORIGAMI CHAIN", WHITE)
        pyxel.text(48, 66, "Fuse same colors by folding.", GRAY)
        pyxel.text(48, 84, "CLICK  = FOLD VERTICAL", LIME)
        pyxel.text(48, 98, "SPACE  = FOLD HORIZONTAL", YELLOW)
        pyxel.text(48, 112, "4 COMBO = SUPER FOLD", RED)
        pyxel.text((self.SCREEN_W - 15 * 4) // 2, 150, "SPACE TO START", WHITE)

    def _draw_game_over(self) -> None:
        pyxel.text((self.SCREEN_W - 9 * 4) // 2, 80, "GAME OVER", RED)
        pyxel.text(96, 110, f"SCORE {self.score}", WHITE)
        pyxel.text(96, 124, f"BEST  {self.best_score}", YELLOW)
        pyxel.text((self.SCREEN_W - 16 * 4) // 2, 160, "SPACE TO RESTART", GRAY)

    def _draw_playing(self, ox: int, oy: int) -> None:
        self._draw_paper(ox, oy)
        if self.super_mode:
            self._draw_super_border(ox, oy)
        for p in self.particles:
            pyxel.circ(int(p.x + ox), int(p.y + oy), 1, p.color)
        for t in self.floating_texts:
            pyxel.text(t.x + ox, t.y + oy, t.text, t.color)
        self._draw_hud(ox, oy)
        if self.phase == Phase.CRANE_COMPLETE:
            pyxel.text(128 + ox, 110 + oy, "CRANE!", WHITE)

    def _draw_paper(self, ox: int, oy: int) -> None:
        for r in range(self.rows):
            for c in range(self.cols):
                x = self.PAPER_X + c * self.CELL + ox
                y = self.PAPER_Y + r * self.CELL + oy
                v = self.paper[r][c]
                if v < 0:
                    pyxel.rect(x, y, self.CELL, self.CELL, GRAY)
                    pyxel.line(x, y, x + self.CELL - 1, y + self.CELL - 1, NAVY)
                else:
                    pyxel.rect(x, y, self.CELL, self.CELL, self.COLOR_VALS[v])
                    pyxel.rectb(x, y, self.CELL, self.CELL, BLACK)
        if self.cols > 1:
            fx = self.PAPER_X + self.cols * self.CELL // 2 + ox
            for yy in range(self.PAPER_Y + oy, self.PAPER_Y + self.rows * self.CELL + oy, 6):
                pyxel.pset(fx, yy, DARK_BLUE)
        if self.rows > 1:
            fy = self.PAPER_Y + self.rows * self.CELL // 2 + oy
            for xx in range(self.PAPER_X + ox, self.PAPER_X + self.cols * self.CELL + ox, 6):
                pyxel.pset(xx, fy, DARK_BLUE)

    def _draw_super_border(self, ox: int, oy: int) -> None:
        colors = (RED, ORANGE, YELLOW, LIME, CYAN, WHITE, PINK, PEACH)
        w = self.cols * self.CELL
        h = self.rows * self.CELL
        for i in range(4):
            col = colors[(pyxel.frame_count // 4 + i) % len(colors)]
            pyxel.rectb(
                self.PAPER_X - 3 - i + ox,
                self.PAPER_Y - 3 - i + oy,
                w + 6 + i * 2,
                h + 6 + i * 2,
                col,
            )

    def _heat_color(self) -> int:
        if self.heat < 40:
            return GREEN
        if self.heat < 70:
            return YELLOW
        if self.heat < 90:
            return ORANGE
        return RED

    def _draw_hud(self, ox: int, oy: int) -> None:
        pyxel.text(8 + ox, 6 + oy, f"SCORE {self.score}", WHITE)
        pyxel.text(8 + ox, 16 + oy, f"COMBO {self.combo}", YELLOW)
        pyxel.text(8 + ox, 26 + oy, f"MAX {self.max_combo}", GRAY)
        pyxel.text(200 + ox, 6 + oy, "HEAT", RED)
        pyxel.rect(240 + ox, 6 + oy, 60, 6, NAVY)
        hw = int(60 * self.heat / self.MAX_HEAT)
        if hw > 0:
            pyxel.rect(240 + ox, 6 + oy, hw, 6, self._heat_color())
        pyxel.rectb(240 + ox, 6 + oy, 60, 6, WHITE)
        pyxel.text(200 + ox, 16 + oy, "TIME", CYAN)
        pyxel.rect(240 + ox, 16 + oy, 60, 6, NAVY)
        tw = int(60 * self.time_left / self.TIME_START)
        if tw > 0:
            pyxel.rect(240 + ox, 16 + oy, tw, 6, CYAN)
        pyxel.rectb(240 + ox, 16 + oy, 60, 6, WHITE)
        if self.super_mode and (pyxel.frame_count // 10) % 2 == 0:
            pyxel.text(200 + ox, 26 + oy, "SUPER FOLD!", PINK)


def main() -> None:
    game = Game()
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
