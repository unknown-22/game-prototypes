"""
HANG CHAIN — Color-Match Hangman Prototype
===========================================
Guess hidden words by typing letters. Each letter position has a color.
Consecutive same-color correct guesses build COMBO chain.
COMBO >= 4 triggers SUPER SOLVE (auto-reveal, 3x score, rainbow mode).
Wrong guesses add HEAT. HEAT = 100 = game over. 60s timer.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

W, H = 320, 240
FPS = 30

BLACK = 0
NAVY = 1
PURPLE_COL = 2
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

COLOR_NAMES: tuple[str, str, str, str] = ("RED", "LIME", "DARK_BLUE", "YELLOW")
COLOR_VALS: tuple[int, int, int, int] = (RED, LIME, DARK_BLUE, YELLOW)
COLOR_COUNT = len(COLOR_VALS)

RAINBOW_COLORS = (RED, ORANGE, YELLOW, LIME, CYAN, PURPLE_COL, PINK)


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    WORD_COMPLETE = auto()
    GAME_OVER = auto()


WORD_POOL: list[str] = [
    "cat", "dog", "sun", "moon", "star", "tree", "bird", "fish",
    "home", "road", "lake", "wind", "dark", "gold", "blue", "fire",
    "water", "stone", "cloud", "light", "night", "dream", "music",
    "apple", "brain", "candy", "dance", "earth", "flame", "grape",
    "heart", "ivory", "joker", "knife", "lemon", "magic", "noble",
    "ocean", "piano", "queen", "river", "snake", "tiger", "union",
    "vivid", "whale", "xenon", "youth", "zebra", "ghost", "angel",
    "computer", "diamond", "forever", "guitar", "horizon",
]


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
    vy: float = -1.0


class Game:
    def __init__(self) -> None:
        pyxel.init(W, H, title="HANG CHAIN", fps=FPS)
        self._rng = random.Random()
        self._init_state()
        pyxel.run(self.update, self.draw)

    def _init_state(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat: float = 0.0
        self.timer = 1800
        self.phase = Phase.TITLE
        self.wrong_guesses = 0
        self.current_word = ""
        self._revealed: list[bool] = []
        self._letter_colors: list[int] = []
        self._guessed_letters: set[str] = set()
        self.last_correct_color = -1
        self.super_mode = False
        self.super_timer = 0
        self.multiplier = 1
        self.best_score = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._word_complete_timer = 0
        self._used_words: list[str] = []
        self._flash_timer = 0
        self._word_started = False

    def reset(self) -> None:
        best = max(self.score, self.best_score)
        self._init_state()
        self.best_score = best

    def _generate_word(self) -> str:
        elapsed = 1800 - self.timer
        min_len = 4 if elapsed < 600 else 5 if elapsed < 1200 else 6

        pool = [w for w in WORD_POOL if len(w) >= min_len and len(w) <= 7]
        if not pool:
            pool = WORD_POOL

        available = [w for w in pool if w not in self._used_words]
        if not available:
            self._used_words.clear()
            available = pool

        word = self._rng.choice(available)
        self._used_words.append(word)

        self._revealed = [False] * len(word)
        self._letter_colors = [
            self._rng.randrange(COLOR_COUNT) for _ in range(len(word))
        ]
        return word

    def _handle_guess(self, letter: str) -> bool:
        if letter in self._guessed_letters:
            return False
        self._guessed_letters.add(letter)

        if letter in self.current_word:
            positions = [
                i for i, ch in enumerate(self.current_word) if ch == letter
            ]
            first_pos = positions[0]
            letter_color = self._letter_colors[first_pos]

            is_color_match = letter_color == self.last_correct_color
            if is_color_match:
                self.combo += 1
            else:
                self.combo = 1

            self.last_correct_color = letter_color
            if self.combo > self.max_combo:
                self.max_combo = self.combo

            for pos in positions:
                if not self._revealed[pos]:
                    self._revealed[pos] = True
                    gained = 10 * self.combo * self.multiplier
                    self.score += gained
                    self._spawn_particles_at_letter(pos, letter_color)
                    self._spawn_floating_text_at_letter(pos, f"+{gained}", WHITE, 30)

            if self.combo >= 2:
                cx = W // 2
                cy = 170
                self.floating_texts.append(
                    FloatingText(cx, cy, f"COMBO x{self.combo}!",
                              life=45, color=COLOR_VALS[letter_color])
                )

            if self.combo >= 4 and not self.super_mode:
                self._activate_super_mode()

            if self._all_revealed():
                self.phase = Phase.WORD_COMPLETE
                self._word_complete_timer = 60
                self.floating_texts.append(
                    FloatingText(W // 2, 170, "WORD CLEAR!", life=60, color=LIME)
                )
            return True
        else:
            self.heat = min(100.0, self.heat + 15.0)
            self.combo = 0
            self.last_correct_color = -1
            self.wrong_guesses += 1
            self.floating_texts.append(
                FloatingText(W // 2, 170, "WRONG!", life=45, color=RED)
            )
            for _ in range(4):
                self.particles.append(
                    Particle(W // 2, 100, self._rng.uniform(-1.5, 1.5),
                              self._rng.uniform(-1.5, 1.5), 10, RED)
                )
            if self.heat >= 100.0:
                self.phase = Phase.GAME_OVER
            return True

    def _spawn_particles_at_letter(self, pos: int, color_idx: int) -> None:
        lx = self._letter_x(pos)
        ly = self._letter_y()
        cval = COLOR_VALS[color_idx]
        for _ in range(8):
            self.particles.append(
                Particle(lx, ly,
                         self._rng.uniform(-2.0, 2.0),
                         self._rng.uniform(-2.5, -0.5),
                         15, cval)
            )

    def _spawn_floating_text_at_letter(self, pos: int, text: str, color: int,
                                        life: int) -> None:
        lx = self._letter_x(pos)
        ly = self._letter_y() - 5
        self.floating_texts.append(FloatingText(lx, ly, text, life, color))

    def _letter_x(self, pos: int) -> int:
        word = self.current_word
        spacing = 20
        total_w = len(word) * spacing
        start_x = W // 2 - total_w // 2 + spacing // 2
        return start_x + pos * spacing

    def _letter_y(self) -> int:
        return 60

    def _activate_super_mode(self) -> None:
        self.super_mode = True
        self.super_timer = 300
        self.multiplier = 3
        self.floating_texts.append(
            FloatingText(W // 2, 180, "SUPER SOLVE!", life=60, color=LIME)
        )
        for _ in range(20):
            self.particles.append(
                Particle(W // 2, 60, self._rng.uniform(-3.0, 3.0),
                         self._rng.uniform(-3.0, 3.0), 30,
                         self._rng.choice(RAINBOW_COLORS))
            )

    def _deactivate_super_mode(self) -> None:
        self.super_mode = False
        self.super_timer = 0
        self.multiplier = 1

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.life -= 1
            if p.life <= 0:
                continue
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            alive.append(p)
        self.particles = alive

    def _update_floating_texts(self) -> None:
        alive: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.life -= 1
            if ft.life <= 0:
                continue
            ft.y += ft.vy
            alive.append(ft)
        self.floating_texts = alive

    def _update_heat(self) -> bool:
        self.heat = max(0.0, self.heat - 0.02)
        return False

    def _update_super_mode(self) -> None:
        if not self.super_mode:
            return
        self.super_timer -= 1
        if self.super_timer % 60 == 0:
            unrevealed = [i for i, r in enumerate(self._revealed) if not r]
            if unrevealed:
                pos = self._rng.choice(unrevealed)
                self._revealed[pos] = True
                gained = 10 * self.combo * self.multiplier
                self.score += gained
                self._spawn_particles_at_letter(pos, self._letter_colors[pos])
                self._spawn_floating_text_at_letter(pos, f"+{gained}", WHITE, 30)
                if self._all_revealed():
                    self.phase = Phase.WORD_COMPLETE
                    self._word_complete_timer = 60
                    self.floating_texts.append(
                        FloatingText(W // 2, 170, "WORD CLEAR!", life=60, color=LIME)
                    )
        if self.super_timer <= 0:
            self._deactivate_super_mode()

    def _all_revealed(self) -> bool:
        return all(self._revealed)

    def _start_game(self) -> None:
        self._init_state()
        old_best = self.best_score
        self.best_score = old_best
        self.phase = Phase.PLAYING
        self.current_word = self._generate_word()

    def _start_title(self) -> None:
        self._init_state()
        self.phase = Phase.TITLE

    def _next_word(self) -> None:
        self.current_word = self._generate_word()
        self._guessed_letters.clear()
        self.last_correct_color = -1
        self.phase = Phase.PLAYING

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self._start_game()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self._start_game()
            return

        if self.phase == Phase.WORD_COMPLETE:
            self._word_complete_timer -= 1
            self._update_particles()
            self._update_floating_texts()
            if self._word_complete_timer <= 0:
                if self.timer <= 0:
                    self.phase = Phase.GAME_OVER
                else:
                    self._next_word()
            return

        if self.phase == Phase.PLAYING:
            self._update_timer()
            self._flash_timer += 1
            self._update_heat()
            self._update_super_mode()
            self._update_particles()
            self._update_floating_texts()

            for key in range(pyxel.KEY_A, pyxel.KEY_Z + 1):
                if pyxel.btnp(key):
                    letter = chr(key - pyxel.KEY_A + ord("A")).lower()
                    self._handle_guess(letter)

    def _update_timer(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER

    def _heat_bar_color(self) -> int:
        if self.heat < 50:
            return GREEN
        elif self.heat < 80:
            return ORANGE
        else:
            return RED

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.WORD_COMPLETE:
            self._draw_playing()
            self._draw_word_complete_overlay()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = "HANG CHAIN"
        pyxel.text(W // 2 - len(title) * 4 // 2, 60, title, LIME)
        pyxel.text(W // 2 - len("Press ENTER to start") * 4 // 2, 100,
                    "Press ENTER to start", WHITE)

        instructions = [
            "Type A-Z to guess letters",
            "Same color = COMBO!",
            "COMBO x4 = SUPER SOLVE!",
            "Wrong guesses add HEAT",
            "60 seconds to score BIG!",
        ]
        for i, line in enumerate(instructions):
            pyxel.text(W // 2 - len(line) * 4 // 2, 130 + i * 14, line, GRAY)

    def _draw_playing(self) -> None:
        self._draw_top_bar()
        self._draw_word()
        self._draw_color_bar()
        self._draw_guessed_letters()
        self._draw_hangman()
        self._draw_particles()
        self._draw_floating_texts()
        if self.super_mode:
            self._draw_super_mode_effects()

    def _draw_top_bar(self) -> None:
        pyxel.rect(0, 0, W, 20, DARK_BLUE)

        timer_sec = max(0, self.timer // FPS)
        time_str = f"TIME: {timer_sec}"
        time_col = RED if timer_sec <= 10 else WHITE
        pyxel.text(4, 6, time_str, time_col)

        score_str = f"SCORE: {self.score}"
        pyxel.text(W - len(score_str) * 4 - 4, 3, score_str, YELLOW)

        combo_str = f"COMBO: x{self.combo}"
        pyxel.text(W - len(combo_str) * 4 - 4, 12, combo_str,
                    WHITE if self.combo < 4 else LIME)

        bar_x = 70
        bar_w = 80
        bar_h = 6
        bar_y = 7
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        fill_w = int(bar_w * self.heat / 100.0)
        pyxel.rect(bar_x, bar_y, fill_w, bar_h, self._heat_bar_color())

    def _draw_word(self) -> None:
        if not self.current_word:
            return

        spacing = 20
        word = self.current_word
        total_w = len(word) * spacing
        start_x = W // 2 - total_w // 2 + spacing // 2

        for i, ch in enumerate(word):
            x = start_x + i * spacing
            y = 60

            if self._revealed[i]:
                cval = COLOR_VALS[self._letter_colors[i]]
                if self.super_mode:
                    cidx = (self._flash_timer // 4 + i) % len(RAINBOW_COLORS)
                    cval = RAINBOW_COLORS[cidx]
                pyxel.text(x - 3, y - 2, ch.upper(), cval)
            else:
                pyxel.text(x - 3, y - 2, "_", GRAY)

    def _draw_color_bar(self) -> None:
        if not self.current_word:
            return
        spacing = 20
        word = self.current_word
        total_w = len(word) * spacing
        start_x = W // 2 - total_w // 2 + spacing // 2

        for i in range(len(word)):
            x = start_x + i * spacing - 4
            y = 80
            cval = COLOR_VALS[self._letter_colors[i]]
            if self._revealed[i]:
                pyxel.rect(x, y, 8, 8, cval)
            else:
                pyxel.rectb(x, y, 8, 8, cval)

    def _draw_guessed_letters(self) -> None:
        if not self._guessed_letters:
            return

        letters = sorted(self._guessed_letters)
        cols_per_row = 13
        for i, letter in enumerate(letters):
            row = i // cols_per_row
            col = i % cols_per_row
            x = 10 + col * 12
            y = 120 + row * 14
            in_word = letter in self.current_word
            col_val = WHITE if in_word else GRAY
            pyxel.text(x, y, letter.upper(), col_val)

    def _draw_hangman(self) -> None:
        bx = 240
        by = 30

        parts_order = [
            ("rope", None),
            ("head", None),
            ("body", None),
            ("left_arm", None),
            ("right_arm", None),
            ("left_leg", None),
            ("right_leg", None),
        ]

        parts_to_draw = min(self.wrong_guesses, len(parts_order))

        if parts_to_draw >= 1:
            pyxel.line(bx, by, bx, by + 15, WHITE)  # rope

        if parts_to_draw >= 2:
            pyxel.circb(bx, by + 20, 8, WHITE)  # head

        if parts_to_draw >= 3:
            pyxel.line(bx, by + 28, bx, by + 55, WHITE)  # body

        if parts_to_draw >= 4:
            pyxel.line(bx, by + 40, bx - 12, by + 30, WHITE)  # left arm

        if parts_to_draw >= 5:
            pyxel.line(bx, by + 40, bx + 12, by + 30, WHITE)  # right arm

        if parts_to_draw >= 6:
            pyxel.line(bx, by + 55, bx - 10, by + 70, WHITE)  # left leg

        if parts_to_draw >= 7:
            pyxel.line(bx, by + 55, bx + 10, by + 70, WHITE)  # right leg

        pyxel.line(bx - 15, by, bx + 15, by, WHITE)  # beam top
        pyxel.line(bx + 15, by, bx + 15, by + 5, WHITE)  # beam vertical

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life % 8 > 3
            if not alpha:
                continue
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_super_mode_effects(self) -> None:
        border_colors = RAINBOW_COLORS
        step = (self._flash_timer // 2) % len(border_colors)
        for i in range(4):
            c = border_colors[(step + i) % len(border_colors)]
            pyxel.rectb(i, i, W - i * 2, H - i * 2, c)

        remaining = self.super_timer // FPS
        s = f"SUPER SOLVE {remaining}s"
        pyxel.text(W // 2 - len(s) * 4 // 2, 190, s, LIME)

    def _draw_word_complete_overlay(self) -> None:
        msg = "WORD COMPLETE!"
        pyxel.text(W // 2 - len(msg) * 4 // 2, 170, msg, LIME)

    def _draw_game_over(self) -> None:
        pyxel.cls(BLACK)
        msg = "GAME OVER"
        pyxel.text(W // 2 - len(msg) * 4 // 2, 70, msg, RED)

        score_msg = f"SCORE: {self.score}"
        pyxel.text(W // 2 - len(score_msg) * 4 // 2, 100, score_msg, WHITE)

        best_msg = f"BEST: {self.best_score}"
        pyxel.text(W // 2 - len(best_msg) * 4 // 2, 114, best_msg, YELLOW)

        combo_msg = f"MAX COMBO: x{self.max_combo}"
        pyxel.text(W // 2 - len(combo_msg) * 4 // 2, 128, combo_msg, LIME)

        restart_msg = "Press ENTER to retry"
        pyxel.text(W // 2 - len(restart_msg) * 4 // 2, 160, restart_msg, WHITE)


if __name__ == "__main__":
    Game()
