"""SHELL CHAIN - a shell game (three-cup monte) with color tracking.

The core loop: cups lift to reveal colored balls, then shuffle. The player
must remember which color sits under which cup, click a cup, and type the
correct color key. A correct guess chains into adjacent same-color cups, and
a x4 combo triggers SUPER VISION (rainbow, 3x score, frozen heat/time, and
auto-matching guesses). Wrong guesses build HEAT; hitting 100 ends the run.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

WIDTH = 320
HEIGHT = 240

CUP_W = 36
CUP_H = 48
CUP_Y = 108
CUP_DOME_R = 18
BALL_R = 6
LIFT = 22

TIMER_FRAMES = 3600
SUPER_VISION_FRAMES = 300
HEAT_MAX = 100
HEAT_PER_MISS = 15
START_CUPS = 3
MAX_CUPS = 10

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

BALL_COLORS = (RED, LIME, DARK_BLUE, YELLOW)
RAINBOW = (RED, ORANGE, YELLOW, LIME, GREEN, CYAN, LIGHT_BLUE, DARK_BLUE, PURPLE, PINK)


class Phase(Enum):
    TITLE = auto()
    SHOW = auto()
    SHUFFLE = auto()
    GUESS = auto()
    RESOLVE = auto()
    GAME_OVER = auto()


@dataclass
class Cup:
    x: float
    y: float
    target_x: float
    revealed: bool
    ball_color: int
    wobble: float
    index: int


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
    color: int
    life: int


class Game:
    def __init__(self) -> None:
        pyxel.init(WIDTH, HEIGHT, title="SHELL CHAIN", display_scale=2)
        self._setup_sounds()
        self.reset()
        self.phase = Phase.TITLE
        pyxel.run(self.update, self.draw)

    def _setup_sounds(self) -> None:
        pyxel.sounds[0].set("c3e3g3c4", "s", "5", "n", 15)
        pyxel.sounds[1].set("g2e2c2", "s", "5", "n", 15)

    def reset(self) -> None:
        if not hasattr(self, "rng"):
            self.rng = random.Random()
        self.phase = Phase.SHOW
        self.score = 0
        self.combo = 0
        self.best_combo = 0
        self.heat = 0
        self.timer = TIMER_FRAMES
        self.round_count = 0
        self.cup_count = START_CUPS
        self.super_vision = 0
        self.selected_cup: int | None = None
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.cups: list[Cup] = []
        self.show_timer_frames = 0
        self.shuffle_frames = 0
        self.resolve_frames = 0
        self._start_show()

    def _layout(self) -> list[float]:
        n = self.cup_count
        avail = WIDTH - 2 * 12 - CUP_W
        pitch = avail / (n - 1) if n > 1 else 0.0
        if pitch > 64.0:
            pitch = 64.0
        start = (WIDTH - ((n - 1) * pitch + CUP_W)) / 2
        return [start + i * pitch for i in range(n)]

    def _random_color(self) -> int:
        return self.rng.choice(BALL_COLORS)

    def _make_cups(self) -> None:
        layout = self._layout()
        self.cups = [
            Cup(
                x=layout[i],
                y=CUP_Y,
                target_x=layout[i],
                revealed=False,
                ball_color=self._random_color(),
                wobble=0.0,
                index=i,
            )
            for i in range(self.cup_count)
        ]

    def _start_show(self) -> None:
        self.phase = Phase.SHOW
        self._make_cups()
        for cup in self.cups:
            cup.revealed = True
        self.show_timer_frames = self._show_timer()
        self.selected_cup = None

    def _start_shuffle(self) -> None:
        self.phase = Phase.SHUFFLE
        for cup in self.cups:
            cup.revealed = False
        slots = self._layout()
        self.rng.shuffle(slots)
        for cup, slot in zip(self.cups, slots):
            cup.target_x = slot
        self.shuffle_frames = self._shuffle_duration()

    def _start_guess(self) -> None:
        self.phase = Phase.GUESS
        self.selected_cup = None

    def _handle_guess(self, cup_index: int, guessed_color: int) -> None:
        if not (0 <= cup_index < len(self.cups)):
            return
        cup = self.cups[cup_index]
        if cup.revealed:
            return
        if self.super_vision > 0 or cup.ball_color == guessed_color:
            self._resolve_match(cup_index)
        else:
            self._resolve_mismatch(cup_index)

    def _resolve_match(self, cup_index: int) -> None:
        self.combo += 1
        self.best_combo = max(self.best_combo, self.combo)
        multiplier = 3 if self.super_vision > 0 else 1
        gained = 10 * self.combo * multiplier
        self.score += gained
        cup = self.cups[cup_index]
        cup.revealed = True
        self._spawn_burst(cup.x + CUP_W / 2, CUP_Y + 24, cup.ball_color)
        self.floating_texts.append(
            FloatingText(cup.x + CUP_W / 2, CUP_Y - 6, f"+{gained}", YELLOW, 40)
        )
        self._chain_burst(cup_index)
        if self.combo >= 4 and self.super_vision <= 0:
            self.super_vision = SUPER_VISION_FRAMES
            self.floating_texts.append(
                FloatingText(WIDTH / 2, HEIGHT / 2 - 20, "SUPER VISION!", PINK, 60)
            )
        if self._all_revealed():
            self._round_complete()

    def _chain_burst(self, cup_index: int) -> None:
        color = self.cups[cup_index].ball_color
        stack = [cup_index]
        visited: set[int] = set()
        while stack:
            i = stack.pop()
            if i in visited or not (0 <= i < len(self.cups)):
                continue
            visited.add(i)
            cup = self.cups[i]
            if cup.ball_color == color:
                if not cup.revealed:
                    cup.revealed = True
                    self._spawn_burst(cup.x + CUP_W / 2, CUP_Y + 24, cup.ball_color)
                    self.floating_texts.append(
                        FloatingText(cup.x + CUP_W / 2, CUP_Y - 6, "CHAIN", CYAN, 30)
                    )
                stack.append(i - 1)
                stack.append(i + 1)

    def _resolve_mismatch(self, cup_index: int) -> None:
        self._update_heat(HEAT_PER_MISS)
        self.combo = 0
        cup = self.cups[cup_index]
        cup.revealed = False
        cup.ball_color = self._random_color()
        self.floating_texts.append(
            FloatingText(cup.x + CUP_W / 2, CUP_Y - 6, "MISS", RED, 40)
        )

    def _update_heat(self, amount: int) -> None:
        if self.super_vision > 0:
            return
        self.heat = min(HEAT_MAX, self.heat + amount)

    def _all_revealed(self) -> bool:
        return all(cup.revealed for cup in self.cups)

    def _round_complete(self) -> None:
        bonus = 100 * self.combo
        self.score += bonus
        self.round_count += 1
        self.floating_texts.append(
            FloatingText(WIDTH / 2, HEIGHT / 2, f"ROUND BONUS +{bonus}", YELLOW, 60)
        )
        if self.cup_count < MAX_CUPS:
            self.cup_count += 1
        self.phase = Phase.RESOLVE
        self.resolve_frames = 50

    def _check_game_over(self) -> bool:
        if self.heat >= HEAT_MAX or self.timer <= 0:
            self.phase = Phase.GAME_OVER
            return True
        return False

    def _show_timer(self) -> int:
        span = MAX_CUPS - START_CUPS
        return int(round(120 - (self.cup_count - START_CUPS) * (60 / span)))

    def _shuffle_duration(self) -> int:
        span = MAX_CUPS - START_CUPS
        return int(round(40 - (self.cup_count - START_CUPS) * (20 / span)))

    def _spawn_burst(self, x: float, y: float, color: int) -> None:
        for _ in range(8):
            angle = self.rng.uniform(0.0, math.tau)
            speed = self.rng.uniform(0.5, 2.0)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed - 1.0,
                    life=self.rng.randint(10, 25),
                    color=color,
                )
            )

    def _update_particles(self) -> None:
        for particle in self.particles:
            particle.x += particle.vx
            particle.y += particle.vy
            particle.vy += 0.3
            particle.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for text in self.floating_texts:
            text.y -= 0.6
            text.life -= 1
        self.floating_texts = [t for t in self.floating_texts if t.life > 0]

    def _update_guess_input(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            for i, cup in enumerate(self.cups):
                if cup.revealed:
                    continue
                if cup.x <= mx <= cup.x + CUP_W and CUP_Y - 4 <= my <= CUP_Y + CUP_H + 4:
                    self.selected_cup = i
                    break
        wheel = pyxel.mouse_wheel
        if wheel != 0:
            if self.selected_cup is None:
                self.selected_cup = 0
            else:
                self.selected_cup = (self.selected_cup + (1 if wheel > 0 else -1)) % self.cup_count
        color_keys = {
            pyxel.KEY_1: RED,
            pyxel.KEY_2: LIME,
            pyxel.KEY_3: DARK_BLUE,
            pyxel.KEY_4: YELLOW,
        }
        for key, color in color_keys.items():
            if pyxel.btnp(key):
                if self.selected_cup is not None:
                    before_combo = self.combo
                    before_heat = self.heat
                    self._handle_guess(self.selected_cup, color)
                    if self.combo > before_combo:
                        pyxel.play(0, 0)
                    elif self.heat > before_heat:
                        pyxel.play(0, 1)
                break

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
            return

        for cup in self.cups:
            target_wobble = 1.0 if cup.revealed else 0.0
            cup.wobble += (target_wobble - cup.wobble) * 0.25
            cup.x += (cup.target_x - cup.x) * 0.18

        self._update_particles()
        self._update_floating_texts()

        if self.super_vision > 0:
            self.super_vision -= 1
        else:
            self.timer -= 1

        if self.phase == Phase.SHOW:
            self.show_timer_frames -= 1
            if self.show_timer_frames <= 0:
                self._start_shuffle()
        elif self.phase == Phase.SHUFFLE:
            self.shuffle_frames -= 1
            if self.shuffle_frames <= 0:
                self._start_guess()
        elif self.phase == Phase.GUESS:
            self._update_guess_input()
        elif self.phase == Phase.RESOLVE:
            self.resolve_frames -= 1
            if self.resolve_frames <= 0:
                self._start_show()

        self._check_game_over()

    def _center_text(self, y: int, text: str, color: int) -> None:
        pyxel.text(WIDTH // 2 - len(text) * 2, y, text, color)

    def _draw_cup(self, cup: Cup) -> None:
        lift = cup.wobble * LIFT
        wiggle = math.sin(pyxel.frame_count * 0.4 + cup.index) * cup.wobble * 1.5
        cx = cup.x + CUP_W / 2
        if cup.wobble > 0.05:
            pyxel.circ(int(cx), int(CUP_Y + 28), BALL_R, cup.ball_color)
        x = int(cup.x + wiggle)
        y = int(CUP_Y - lift)
        pyxel.rect(x, y, CUP_W, CUP_H, GRAY)
        pyxel.circ(x + CUP_W // 2, y, CUP_DOME_R, GRAY)
        pyxel.rectb(x, y, CUP_W, CUP_H, WHITE)
        pyxel.circb(x + CUP_W // 2, y, CUP_DOME_R, DARK_BLUE)
        if self.super_vision > 0:
            rainbow_color = RAINBOW[(pyxel.frame_count // 4) % len(RAINBOW)]
            pyxel.rectb(x, y, CUP_W, CUP_H, rainbow_color)

    def _draw_playfield(self) -> None:
        for cup in self.cups:
            self._draw_cup(cup)
        if self.phase == Phase.GUESS and self.selected_cup is not None:
            cup = self.cups[self.selected_cup]
            if not cup.revealed:
                cx = int(cup.x + CUP_W / 2)
                pyxel.tri(cx, CUP_Y - 28, cx - 5, CUP_Y - 36, cx + 5, CUP_Y - 36, WHITE)
        if self.super_vision > 0:
            rainbow_color = RAINBOW[(pyxel.frame_count // 4) % len(RAINBOW)]
            pyxel.rectb(0, 0, WIDTH, HEIGHT, rainbow_color)
            self._center_text(4, "SUPER", rainbow_color)

    def _draw_hud(self) -> None:
        pyxel.text(6, 4, f"SCORE {self.score}", WHITE)
        self._center_text(4, f"COMBO {self.combo}", WHITE if self.combo < 4 else PINK)

        bar_x = WIDTH - 24
        bar_y = 8
        bar_h = 120
        pyxel.rectb(bar_x, bar_y, 12, bar_h, WHITE)
        fill = int(bar_h * self.heat / HEAT_MAX)
        heat_color = GREEN if self.heat < 40 else (YELLOW if self.heat < 75 else RED)
        pyxel.rect(bar_x + 1, bar_y + bar_h - fill, 10, fill, heat_color)
        pyxel.text(bar_x - 2, bar_y + bar_h + 2, "HEAT", WHITE)
        if self.heat >= 75:
            pyxel.tri(bar_x + 6, bar_y - 8, bar_x, bar_y - 2, bar_x + 12, bar_y - 2, RED)

        bar_w = WIDTH - 24
        pyxel.rectb(12, HEIGHT - 14, bar_w, 8, WHITE)
        timer_w = int(bar_w * max(0, self.timer) / TIMER_FRAMES)
        pyxel.rect(13, HEIGHT - 13, timer_w, 6, CYAN)

        if self.phase == Phase.SHOW:
            self._center_text(HEIGHT - 40, "MEMORIZE!", YELLOW)
        elif self.phase == Phase.GUESS:
            self._center_text(HEIGHT - 40, "CLICK CUP + 1..4", WHITE)
        elif self.phase == Phase.SHUFFLE:
            self._center_text(HEIGHT - 40, "WATCH!", LIGHT_BLUE)

    def _draw_title(self) -> None:
        self._center_text(70, "SHELL CHAIN", WHITE)
        self._center_text(92, "The Shell Game", GRAY)
        pyxel.text(WIDTH // 2 - 56, 112, "1=RED  2=LIME", RED)
        pyxel.text(WIDTH // 2 - 56, 122, "3=BLUE 4=YELLOW", LIGHT_BLUE)
        self._center_text(142, "Lift. Shuffle. Remember.", WHITE)
        self._center_text(162, "Combo x4 = SUPER VISION", PINK)
        self._center_text(200, "PRESS ENTER", YELLOW)

    def _draw_game_over(self) -> None:
        self._center_text(80, "GAME OVER", RED)
        self._center_text(104, f"SCORE {self.score}", WHITE)
        self._center_text(116, f"BEST COMBO {self.best_combo}", WHITE)
        reason = "OVERHEAT!" if self.heat >= HEAT_MAX else "TIME UP!"
        self._center_text(136, reason, YELLOW)
        self._center_text(160, "PRESS ENTER", WHITE)

    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            pyxel.cls(NAVY)
            self._draw_title()
            return
        if self.phase == Phase.GAME_OVER:
            pyxel.cls(BLACK)
            self._draw_game_over()
            return
        pyxel.cls(NAVY)
        self._draw_playfield()
        for particle in self.particles:
            pyxel.pset(int(particle.x), int(particle.y), particle.color)
        self._draw_hud()
        for text in self.floating_texts:
            pyxel.text(int(text.x - len(text.text) * 2), int(text.y), text.text, text.color)


if __name__ == "__main__":
    Game()
