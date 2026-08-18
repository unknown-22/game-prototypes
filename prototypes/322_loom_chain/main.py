import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

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

WEAVE_COLORS = (RED, LIME, DARK_BLUE, YELLOW)
FLAW = GRAY

SCREEN_W = 320
SCREEN_H = 240
FPS = 60

COLS = 6
CELL = 40
BOARD_X = (SCREEN_W - COLS * CELL) // 2
BOARD_Y = 150

GAME_DURATION = 3600
HEAT_MAX = 100
COMBO_SUPER = 4
SUPER_DURATION = 300
CYCLE_START = 20
CYCLE_MIN = 12
HEAT_DECAY = 0.02


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class FloatText:
    x: int
    y: int
    text: str
    color: int
    life: int


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="LOOM CHAIN", display_scale=2)
        pyxel.mouse(True)
        self.reset()
        pyxel.run(self.update, self.draw)

    @property
    def super_active(self) -> bool:
        return self.super_timer > 0

    def reset(self) -> None:
        self.best_score = getattr(self, "best_score", 0)
        self.rng = getattr(self, "rng", random.Random())
        self.phase = Phase.TITLE
        self.frame = 0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_timer = 0
        self.consecutive_perfect = 0
        self.warp_colors = [self.rng.choice(WEAVE_COLORS) for _ in range(COLS)]
        self.cells = [-1] * COLS
        self.cursor_col = 0
        self.weft_color = WEAVE_COLORS[0]
        self.cycle_timer = 0
        self.fabric_log: list[list[int]] = []
        self.floats: list[FloatText] = []
        self.shake = 0

    def cycle_interval(self) -> int:
        return max(CYCLE_MIN, CYCLE_START - self.frame // 150)

    def _advance_weft(self) -> None:
        if self.super_timer > 0:
            return
        self.cycle_timer += 1
        if self.cycle_timer >= self.cycle_interval():
            self.cycle_timer = 0
            idx = WEAVE_COLORS.index(self.weft_color)
            self.weft_color = WEAVE_COLORS[(idx + 1) % len(WEAVE_COLORS)]

    def _weave(self, col: int) -> None:
        if not (0 <= col < COLS) or self.cells[col] != -1:
            return
        was_super = self.super_timer > 0
        cx = BOARD_X + col * CELL + CELL // 2
        cy = BOARD_Y - 8
        if self.weft_color == self.warp_colors[col] or was_super:
            self.cells[col] = self.weft_color
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            mult = 3 if was_super else 1
            gain = 10 * self.combo * mult
            self.score += gain
            self.floats.append(FloatText(cx, cy, f"+{gain}", WHITE, 30))
            if self.combo >= COMBO_SUPER and self.super_timer == 0:
                self.super_timer = SUPER_DURATION
                self.shake = 6
                self.floats.append(FloatText(160, 60, "SUPER SHUTTLE!", YELLOW, 50))
        else:
            self.cells[col] = FLAW
            self.heat = min(HEAT_MAX, self.heat + 15)
            self.combo = 0
            self.shake = 4
            self.floats.append(FloatText(cx, cy, "FLAW", GRAY, 30))
        if all(c != -1 for c in self.cells):
            self._complete_row()

    def _complete_row(self) -> None:
        perfect = sum(1 for c in self.cells if c != FLAW)
        if perfect == 0:
            self.heat = min(HEAT_MAX, self.heat + 15)
        if perfect == COLS:
            self.consecutive_perfect += 1
            self.score += 100 * self.consecutive_perfect
            self.floats.append(
                FloatText(160, BOARD_Y - 24, f"PERFECT ROW x{self.consecutive_perfect}", YELLOW, 50)
            )
        else:
            self.consecutive_perfect = 0
        self.score += perfect * 20 * (1 + self.consecutive_perfect)
        self.fabric_log.append(list(self.cells))
        self.cells = [-1] * COLS

    def _update_heat(self) -> None:
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            return
        if self.super_timer == 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1

    def _update_floats(self) -> None:
        for f in self.floats:
            f.life -= 1
        self.floats = [f for f in self.floats if f.life > 0]

    def _update_shake(self) -> None:
        if self.shake > 0:
            self.shake -= 1

    def _mouse_col(self) -> int | None:
        x = pyxel.mouse_x
        if BOARD_X <= x < BOARD_X + COLS * CELL:
            return (x - BOARD_X) // CELL
        return None

    def _update_playing(self) -> None:
        self.frame += 1
        if self.frame >= GAME_DURATION:
            self.phase = Phase.GAME_OVER
            return
        self._advance_weft()
        self._update_super()
        self._update_heat()
        if self.phase == Phase.GAME_OVER:
            return
        if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A):
            self.cursor_col = max(0, self.cursor_col - 1)
        if pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D):
            self.cursor_col = min(COLS - 1, self.cursor_col + 1)
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            col = self._mouse_col()
            if col is None:
                col = self.cursor_col
            self._weave(col)
        self._update_floats()
        self._update_shake()

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
                self.phase = Phase.PLAYING
        elif self.phase == Phase.PLAYING:
            self._update_playing()
            self.best_score = max(self.best_score, self.score)
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_R):
                self.reset()
                self.phase = Phase.PLAYING

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        else:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(115, 60, "LOOM CHAIN", WHITE)
        pyxel.text(52, 78, "WEAVE A PERFECT RAINBOW CLOTH", GRAY)
        pyxel.text(60, 108, "MOVE: LEFT/RIGHT or A/D", WHITE)
        pyxel.text(60, 120, "WEAVE: SPACE or CLICK", WHITE)
        pyxel.text(60, 132, "MATCH WEFT COLOR TO WARP COLOR", WHITE)
        pyxel.text(60, 144, "COMBO>=4 = SUPER SHUTTLE", WHITE)
        pyxel.text(60, 156, "PERFECT ROWS SNOWBALL BONUS", WHITE)
        pyxel.text(60, 168, "FLAWS COST HEAT", WHITE)
        pyxel.text(96, 198, "PRESS ENTER TO START", YELLOW)
        pyxel.text(80, 218, f"BEST {self.best_score}", WHITE)

    def _draw_playing(self) -> None:
        ox = self.rng.randint(-2, 2) if self.shake > 0 else 0
        oy = self.rng.randint(-2, 2) if self.shake > 0 else 0

        for col in range(COLS):
            cx = BOARD_X + col * CELL + CELL // 2
            pyxel.line(cx, 40, cx, SCREEN_H, self.warp_colors[col])
            pyxel.rect(BOARD_X + col * CELL + 2, 42, CELL - 4, 6, self.warp_colors[col])

        for col in range(COLS):
            x = BOARD_X + col * CELL + ox
            y = BOARD_Y + oy
            c = self.cells[col]
            if c == -1:
                pyxel.rectb(x, y, CELL, CELL, DARK_BLUE)
            elif c == FLAW:
                pyxel.rect(x, y, CELL, CELL, GRAY)
                pyxel.rectb(x, y, CELL, CELL, WHITE)
            else:
                pyxel.rect(x, y, CELL, CELL, c)
                pyxel.rectb(x, y, CELL, CELL, WHITE)

        hc = WEAVE_COLORS[self.frame // 4 % 4] if self.super_active else YELLOW
        cx = BOARD_X + self.cursor_col * CELL + ox
        pyxel.rectb(cx - 1, BOARD_Y - 1 + oy, CELL + 2, CELL + 2, hc)

        self._draw_shuttle(ox, oy)
        self._draw_fabric_log()

        for f in self.floats:
            pyxel.text(f.x + ox, f.y + oy, f.text, f.color)

        self._draw_hud()

        if self.super_active:
            border = WEAVE_COLORS[self.frame // 6 % 4]
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, border)

    def _draw_shuttle(self, ox: int, oy: int) -> None:
        sx = BOARD_X + self.cursor_col * CELL + CELL // 2 + ox
        sy = BOARD_Y - 16 + oy
        body = YELLOW if self.super_active else WHITE
        pyxel.tri(sx - 10, sy, sx + 10, sy, sx, sy + 6, body)
        pyxel.rect(sx - 9, sy, 18, 4, body)
        pyxel.rect(sx - 4, sy + 4, 8, 2, self.weft_color)

    def _draw_fabric_log(self) -> None:
        start_y = BOARD_Y + CELL + 6
        for i, row in enumerate(self.fabric_log):
            y = start_y + i * 4
            if y >= SCREEN_H - 2:
                break
            perfect = all(c != FLAW for c in row)
            for col, c in enumerate(row):
                x = BOARD_X + col * CELL
                if perfect:
                    pyxel.rect(x, y, CELL - 1, 3, YELLOW)
                else:
                    pyxel.rect(x, y, CELL - 1, 3, c if c != FLAW else GRAY)

    def _draw_hud(self) -> None:
        remaining = max(0, GAME_DURATION - self.frame)
        timer_w = int(remaining / GAME_DURATION * 200)
        pyxel.rect(8, 6, timer_w, 4, LIME)

        pyxel.text(8, 16, f"SCORE {self.score}", WHITE)
        pyxel.text(8, 28, f"COMBO x{self.combo}", WHITE)
        if self.consecutive_perfect > 0:
            pyxel.text(8, 40, f"PERFECT x{self.consecutive_perfect}", YELLOW)

        pyxel.text(124, 12, "WEFT", GRAY)
        wc = WEAVE_COLORS[self.frame // 4 % 4] if self.super_active else self.weft_color
        pyxel.rect(156, 10, 16, 16, wc)
        pyxel.rectb(156, 10, 16, 16, WHITE)

        heat_h = int(self.heat / HEAT_MAX * 180)
        if self.heat < 50:
            heat_color = GREEN
        elif self.heat < 80:
            heat_color = YELLOW
        else:
            heat_color = RED
        pyxel.rect(304, 20, 8, 180, DARK_BLUE)
        pyxel.rect(304, 200 - heat_h, 8, heat_h, heat_color)
        pyxel.text(296, 204, "HEAT", GRAY)

    def _draw_game_over(self) -> None:
        reason = "LOOM TANGLED" if self.heat >= HEAT_MAX else "TIME UP"
        pyxel.text(112, 80, "GAME OVER", RED)
        pyxel.text(132, 96, reason, WHITE)
        pyxel.text(112, 118, f"SCORE {self.score}", WHITE)
        pyxel.text(112, 130, f"BEST {self.best_score}", WHITE)
        pyxel.text(88, 158, "PRESS ENTER TO RETRY", YELLOW)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
