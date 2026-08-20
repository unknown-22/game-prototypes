"""Rune Break - a Mastermind-style rune-lock deduction game."""

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

SCREEN_W = 320
SCREEN_H = 240
CODE_LEN = 4
MAX_GUESSES = 8
START_LIVES = 3
SOLVE_FRAMES = 60

PALETTE: tuple[int, ...] = (8, 11, 5, 10, 2, 12)
COLOR_NAMES: tuple[str, ...] = ("RED", "LIME", "BLUE", "YELLOW", "PURPLE", "CYAN")
KEY_NUMBERS: tuple[int, ...] = (
    pyxel.KEY_1,
    pyxel.KEY_2,
    pyxel.KEY_3,
    pyxel.KEY_4,
    pyxel.KEY_5,
    pyxel.KEY_6,
)

HUD_H = 18
BOARD_X = 20
BOARD_Y = 24
RUNE_SIZE = 16
RUNE_GAP = 4
ROW_H = 20
PEG_X = 108
SWATCH_X = 20
SWATCH_Y = 202
SWATCH_SIZE = 20
SWATCH_GAP = 6
SUBMIT_RECT = (180, 202, 60, 20)
HINT_RECT = (248, 202, 52, 20)
CURRENT_Y = BOARD_Y + MAX_GUESSES * ROW_H


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    SOLVED = auto()
    GAME_OVER = auto()


@dataclass
class GuessRow:
    slots: list[int]
    exact: int
    misplaced: int


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class FloatText:
    x: float
    y: float
    text: str
    life: int
    color: int


def compute_feedback(guess: list[int], code: list[int]) -> tuple[int, int]:
    exact = sum(1 for g, c in zip(guess, code) if g >= 0 and g == c)
    total = 0
    for c in set(code):
        if c < 0:
            continue
        total += min(guess.count(c), code.count(c))
    return exact, total - exact


class Game:
    def __init__(self) -> None:
        self.rng = random.Random()
        self.best_score = 0
        self.reset()

    def reset(self) -> None:
        self.rng = getattr(self, "rng", random.Random())
        self.best_score = getattr(self, "best_score", 0)
        self.score = 0
        self.lives = START_LIVES
        self.codes_broken = 0
        self.streak = 0
        self.max_streak = 0
        self.guesses_used = 0
        self.current_guess = [-1] * CODE_LEN
        self.history: list[GuessRow] = []
        self.revealed: set[int] = set()
        self.cursor = 0
        self.phase = Phase.TITLE
        self.frame = 0
        self.particles: list[Particle] = []
        self.floats: list[FloatText] = []
        self.shake_frames = 0
        self.solve_frame = 0
        self.code: list[int] = []
        self._new_code()

    def _new_code(self) -> None:
        n = self._num_colors()
        self.code = self.rng.sample(list(PALETTE[:n]), CODE_LEN)
        self.guesses_used = 0
        self.current_guess = [-1] * CODE_LEN
        self.history = []
        self.revealed = set()

    def _num_colors(self) -> int:
        if self.codes_broken >= 2:
            return 6
        if self.codes_broken == 1:
            return 5
        return 4

    def _place_color(self, slot: int, color: int) -> None:
        if slot not in self.revealed:
            self.current_guess[slot] = color

    def _clear_slot(self, slot: int) -> None:
        if slot not in self.revealed:
            self.current_guess[slot] = -1

    def _select_slot(self, slot: int) -> None:
        self.cursor = max(0, min(CODE_LEN - 1, slot))

    def _submit_guess(self) -> bool:
        if any(s == -1 for s in self.current_guess):
            return False
        exact, misplaced = compute_feedback(self.current_guess, self.code)
        self.history.append(GuessRow(list(self.current_guess), exact, misplaced))
        self.guesses_used += 1
        if exact == CODE_LEN:
            self._on_solve()
            return True
        if self.guesses_used >= MAX_GUESSES:
            self._on_fail()
        return False

    def _on_solve(self) -> int:
        self.streak += 1
        self.max_streak = max(self.max_streak, self.streak)
        self.codes_broken += 1
        bonus = (MAX_GUESSES - self.guesses_used + 1) * 150 + self.streak * 100
        self.score += bonus
        self.phase = Phase.SOLVED
        self.solve_frame = self.frame
        self.shake_frames = 10
        self._spawn_solve_effects(bonus)
        return bonus

    def _spawn_solve_effects(self, bonus: int) -> None:
        cx = SCREEN_W / 2.0
        cy = SCREEN_H / 2.0
        colors = list(PALETTE[: self._num_colors()])
        for _ in range(48):
            angle = self.rng.uniform(0.0, math.tau)
            speed = self.rng.uniform(1.0, 4.5)
            self.particles.append(
                Particle(
                    cx,
                    cy,
                    math.cos(angle) * speed,
                    math.sin(angle) * speed,
                    self.rng.randint(20, 45),
                    self.rng.choice(colors),
                )
            )
        self.floats.append(FloatText(cx, cy - 24, "CRACKED!", 50, 7))
        self.floats.append(FloatText(cx, cy - 6, f"+{bonus}", 50, 10))

    def _on_fail(self) -> None:
        self.lives -= 1
        self.streak = 0
        if self.lives <= 0:
            self.phase = Phase.GAME_OVER
            self.shake_frames = 12
            if self.score > self.best_score:
                self.best_score = self.score
        else:
            self._new_code()

    def _hint_reveal(self) -> bool:
        if self.cursor in self.revealed:
            return False
        if self.guesses_used >= MAX_GUESSES:
            return False
        self.guesses_used += 1
        self.revealed.add(self.cursor)
        self.current_guess[self.cursor] = self.code[self.cursor]
        return True

    def _update_effects(self) -> None:
        for p in self.particles:
            p.life -= 1
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.15
        self.particles = [p for p in self.particles if p.life > 0]
        for f in self.floats:
            f.life -= 1
            f.y -= 0.5
        self.floats = [f for f in self.floats if f.life > 0]

    def _update_playing(self) -> None:
        if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A):
            self._select_slot(self.cursor - 1)
        if pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D):
            self._select_slot(self.cursor + 1)
        for i, key in enumerate(KEY_NUMBERS):
            if pyxel.btnp(key) and i < self._num_colors():
                self._place_color(self.cursor, PALETTE[i])
        if pyxel.btnp(pyxel.KEY_BACKSPACE) or pyxel.btnp(pyxel.KEY_X):
            self._clear_slot(self.cursor)
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._submit_guess()
            if self.phase is not Phase.PLAYING:
                return
        if pyxel.btnp(pyxel.KEY_H):
            self._hint_reveal()
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._handle_mouse()

    def _handle_mouse(self) -> None:
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        for i in range(CODE_LEN):
            x = BOARD_X + i * (RUNE_SIZE + RUNE_GAP)
            if x <= mx < x + RUNE_SIZE and CURRENT_Y <= my < CURRENT_Y + RUNE_SIZE:
                self._select_slot(i)
                return
        for i in range(self._num_colors()):
            x = SWATCH_X + i * (SWATCH_SIZE + SWATCH_GAP)
            if x <= mx < x + SWATCH_SIZE and SWATCH_Y <= my < SWATCH_Y + SWATCH_SIZE:
                self._place_color(self.cursor, PALETTE[i])
                return
        if self._in_rect(mx, my, SUBMIT_RECT):
            self._submit_guess()
        elif self._in_rect(mx, my, HINT_RECT):
            self._hint_reveal()

    @staticmethod
    def _in_rect(mx: int, my: int, rect: tuple[int, int, int, int]) -> bool:
        x, y, w, h = rect
        return x <= mx < x + w and y <= my < y + h

    def update(self) -> None:
        self.frame += 1
        if self.shake_frames > 0:
            self.shake_frames -= 1
        self._update_effects()
        if self.phase is Phase.TITLE:
            if (
                pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            ):
                self.phase = Phase.PLAYING
        elif self.phase is Phase.PLAYING:
            self._update_playing()
        elif self.phase is Phase.SOLVED:
            if self.frame - self.solve_frame >= SOLVE_FRAMES:
                self._new_code()
                self.phase = Phase.PLAYING
        elif self.phase is Phase.GAME_OVER:
            if (
                pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.KEY_RETURN)
                or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            ):
                self.reset()

    def draw(self) -> None:
        pyxel.cls(0)
        ox = 0
        oy = 0
        if self.shake_frames > 0:
            ox = self.rng.randint(-2, 2)
            oy = self.rng.randint(-2, 2)
        pyxel.camera(ox, oy)
        if self.phase is Phase.TITLE:
            self._draw_title()
        elif self.phase is Phase.GAME_OVER:
            self._draw_game_over()
        else:
            self._draw_board()
        pyxel.camera(0, 0)

    def _draw_board(self) -> None:
        self._draw_hud()
        self._draw_history()
        self._draw_current_guess()
        self._draw_palette()
        self._draw_effects()

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, HUD_H, 1)
        pyxel.text(4, 5, f"SCORE {self.score}", 7)
        pyxel.text(92, 5, f"LIVES {self.lives}", 10)
        pyxel.text(168, 5, f"CODE {self.codes_broken + 1}", 12)
        pyxel.text(240, 5, f"STREAK {self.streak}", 11)

    def _draw_history(self) -> None:
        for k, row in enumerate(self.history):
            y = BOARD_Y + k * ROW_H
            for i, c in enumerate(row.slots):
                x = BOARD_X + i * (RUNE_SIZE + RUNE_GAP)
                pyxel.rect(x, y, RUNE_SIZE, RUNE_SIZE, c)
            self._draw_pegs(row, PEG_X, y + 3)

    def _draw_pegs(self, row: GuessRow, x: int, y: int) -> None:
        idx = 0
        for _ in range(row.exact):
            px = x + (idx % 2) * 8
            py = y + (idx // 2) * 8
            pyxel.rect(px, py, 6, 6, 7)
            idx += 1
        for _ in range(row.misplaced):
            px = x + (idx % 2) * 8
            py = y + (idx // 2) * 8
            pyxel.circ(px + 3, py + 3, 3, 13)
            idx += 1

    def _draw_current_guess(self) -> None:
        y = CURRENT_Y
        for i in range(CODE_LEN):
            x = BOARD_X + i * (RUNE_SIZE + RUNE_GAP)
            c = self.current_guess[i]
            if i in self.revealed:
                pyxel.rect(x, y, RUNE_SIZE, RUNE_SIZE, c)
                pyxel.rectb(x - 2, y - 2, RUNE_SIZE + 4, RUNE_SIZE + 4, 7)
            else:
                fill = c if c != -1 else 1
                pyxel.rect(x, y, RUNE_SIZE, RUNE_SIZE, fill)
                pyxel.rectb(x, y, RUNE_SIZE, RUNE_SIZE, 5)
            if i == self.cursor:
                pyxel.rectb(x - 1, y - 1, RUNE_SIZE + 2, RUNE_SIZE + 2, 10)

    def _draw_palette(self) -> None:
        for i in range(self._num_colors()):
            x = SWATCH_X + i * (SWATCH_SIZE + SWATCH_GAP)
            pyxel.rect(x, SWATCH_Y, SWATCH_SIZE, SWATCH_SIZE, PALETTE[i])
            pyxel.rectb(x, SWATCH_Y, SWATCH_SIZE, SWATCH_SIZE, 7)
            pyxel.text(x + 7, SWATCH_Y + 6, str(i + 1), 0)
        self._draw_button(SUBMIT_RECT, "SUBMIT", 3)
        self._draw_button(HINT_RECT, "HINT", 2)

    def _draw_button(self, rect: tuple[int, int, int, int], label: str, color: int) -> None:
        x, y, w, h = rect
        pyxel.rect(x, y, w, h, color)
        pyxel.rectb(x, y, w, h, 7)
        pyxel.text(x + (w - len(label) * 4) // 2, y + (h - 6) // 2 + 1, label, 0)

    def _draw_effects(self) -> None:
        for p in self.particles:
            pyxel.rect(int(p.x), int(p.y), 2, 2, p.color)
        for f in self.floats:
            pyxel.text(int(f.x - len(f.text) * 2), int(f.y), f.text, f.color)

    def _draw_title(self) -> None:
        self._center_text("RUNE BREAK", 66, 7)
        self._center_text("BREAK THE HIDDEN 4-RUNE CODE", 96, 11)
        self._center_text("1-6 PLACE COLOR    LEFT/RIGHT MOVE", 122, 10)
        self._center_text("SPACE SUBMIT    H HINT    X CLEAR", 134, 12)
        self._center_text("HINT COSTS 1 GUESS AND REVEALS A RUNE", 148, 2)
        self._center_text("8 GUESSES PER LOCK    3 LIVES", 162, 13)
        self._center_text("PRESS SPACE TO START", 188, 7)

    def _draw_game_over(self) -> None:
        self._center_text("GAME OVER", 64, 8)
        self._center_text(f"SCORE {self.score}", 98, 7)
        self._center_text(f"CODES BROKEN {self.codes_broken}", 114, 12)
        self._center_text(f"BEST STREAK {self.max_streak}", 130, 11)
        self._center_text(f"BEST {self.best_score}", 146, 10)
        self._center_text("PRESS SPACE TO RESTART", 176, 7)

    def _center_text(self, text: str, y: int, color: int) -> None:
        pyxel.text((SCREEN_W - len(text) * 4) // 2, y, text, color)


if __name__ == "__main__":
    pyxel.init(SCREEN_W, SCREEN_H, title="Rune Break")
    game = Game()
    pyxel.run(game.update, game.draw)
