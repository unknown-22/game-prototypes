"""Limbo Chain — Color-match limbo dance game."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum

import pyxel

SCREEN_W = 320
SCREEN_H = 240

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

COLORS = (RED, LIME, DARK_BLUE, YELLOW)
COLOR_NAMES = ("RED", "LIME", "DARK_BLUE", "YELLOW")
RAINBOW_COLORS = (RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK)

BAR_INITIAL_Y = 180.0
BAR_MIN_Y = 40.0
BAR_DESCENT = 0.6
BAR_RAISE_ON_SUPER = 15.0
BAR_X = 160
BAR_WIDTH = 120
BAR_HEIGHT = 8

PLAYER_X = 60
PLAYER_Y = 200
PLAYER_DUCK_Y = 210
PLAYER_DUCK_DURATION = 15
PLAYER_COOLDOWN = 8

GAME_DURATION = 60 * 60
COLOR_CYCLE_INTERVAL = 90
SUPER_DURATION = 300
COMBO_THRESHOLD = 4
ATTEMPT_INTERVAL_INITIAL = 120
ATTEMPT_INTERVAL_MIN = 45

BASE_SCORE = 10

HEAT_MISMATCH = 15.0
HEAT_BAR_HIT = 25.0
HEAT_MAX = 100.0
HEAT_DECAY = 0.02


class Phase(Enum):
    TITLE = "title"
    PLAYING = "playing"
    GAME_OVER = "game_over"


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 3


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Limbo Chain")
        self._init_state()
        pyxel.run(self.update, self.draw)

    def _init_state(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = GAME_DURATION
        self.bar_y = BAR_INITIAL_Y
        self.bar_color = COLORS[0]
        self.color_cycle_timer = COLOR_CYCLE_INTERVAL
        self.player_ducking = False
        self.player_duck_timer = 0
        self.player_cooldown = 0
        self.super_mode = False
        self.super_timer = 0
        self.last_duck_color: int | None = None
        self.attempt_timer = ATTEMPT_INTERVAL_INITIAL
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.rng = random.Random()
        self._shake_frames = 0
        self._rainbow_frame = 0
        if not hasattr(self, "best_score"):
            self.best_score = 0

    # -- Update ----------------------------------------------------------

    def update(self) -> None:
        self._rainbow_frame += 1

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self._init_state()
                self.phase = Phase.PLAYING
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.best_score = max(self.best_score, self.score)
                self._init_state()
                self.phase = Phase.PLAYING
            return

        self._update_playing()

    def _update_playing(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self._end_game()
            return

        self.heat = max(0.0, self.heat - HEAT_DECAY)

        elapsed_ratio = 1.0 - (self.timer / GAME_DURATION)

        # Color cycle escalation: 90 -> 40
        self.color_cycle_timer -= 1
        if self.color_cycle_timer <= 0:
            cycle_min = int(90 - 50 * elapsed_ratio)
            self.color_cycle_timer = max(40, cycle_min)
            current_idx = COLORS.index(self.bar_color)
            self.bar_color = COLORS[(current_idx + 1) % len(COLORS)]

        # SUPER mode timer
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                if self.heat >= HEAT_MAX:
                    self._end_game()
                    return

        # Player cooldown
        self.player_cooldown = max(0, self.player_cooldown - 1)

        # Duck state timer
        if self.player_duck_timer > 0:
            self.player_duck_timer -= 1
            if self.player_duck_timer <= 0:
                self.player_ducking = False

        # Screen shake
        if self._shake_frames > 0:
            self._shake_frames -= 1

        # Attempt timer — when it expires, either auto-duck (SUPER) or bar hit
        self.attempt_timer -= 1
        if self.attempt_timer <= 0:
            if self.super_mode:
                self._auto_duck()
            else:
                self._on_bar_hit()
            self._reset_attempt(elapsed_ratio)

        # Input: SPACE to duck
        if (
            pyxel.btnp(pyxel.KEY_SPACE)
            and self.player_cooldown == 0
            and not self.player_ducking
        ):
            self.player_ducking = True
            self.player_duck_timer = PLAYER_DUCK_DURATION
            self.player_cooldown = PLAYER_COOLDOWN
            self._process_duck()
            self._reset_attempt(elapsed_ratio)

        self._update_particles()
        self._update_floating_texts()

    def _reset_attempt(self, elapsed_ratio: float) -> None:
        interval = int(
            ATTEMPT_INTERVAL_INITIAL
            - (ATTEMPT_INTERVAL_INITIAL - ATTEMPT_INTERVAL_MIN) * elapsed_ratio
        )
        self.attempt_timer = max(ATTEMPT_INTERVAL_MIN, interval)

    # -- Duck processing (TESTABLE — no pyxel calls) ---------------------

    def _process_duck(self) -> tuple[int, bool, bool]:
        """Returns (combo, matched, is_super)."""
        matched = False
        triggered_super = False

        if self.last_duck_color is None:
            # First duck always succeeds
            self.last_duck_color = self.bar_color
            self.score += BASE_SCORE
        elif self.super_mode or self.last_duck_color == self.bar_color:
            matched = True
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            mult = 3 if self.super_mode else 1
            self.score += BASE_SCORE * self.combo * mult
            self.last_duck_color = self.bar_color

            if self.combo >= COMBO_THRESHOLD and not self.super_mode:
                self.super_mode = True
                self.super_timer = SUPER_DURATION
                self.bar_y = min(BAR_INITIAL_Y, self.bar_y + BAR_RAISE_ON_SUPER)
                triggered_super = True
                self._spawn_super_particles()
                self._shake_frames = 10
                self._spawn_floating_text("SUPER LIMBO!", SCREEN_W // 2, SCREEN_H // 2, YELLOW)
            else:
                self._spawn_combo_particles(self.bar_color, 5 + self.combo * 2)
                self._spawn_floating_text(
                    f"COMBO x{self.combo}", PLAYER_X, PLAYER_Y - 20, LIME
                )
        else:
            # Mismatch
            self.combo = 0
            self.heat += HEAT_MISMATCH
            self.score += BASE_SCORE
            self.last_duck_color = self.bar_color
            self._spawn_heat_particles()
            self._spawn_floating_text("WRONG!", PLAYER_X, PLAYER_Y - 20, RED)

        self.bar_y = max(BAR_MIN_Y, self.bar_y - BAR_DESCENT)

        if self.heat >= HEAT_MAX and not self.super_mode:
            self._end_game()

        return (self.combo, matched, triggered_super)

    def _auto_duck(self) -> None:
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        self.score += BASE_SCORE * self.combo * 3
        self.last_duck_color = self.bar_color
        self.bar_y = max(BAR_MIN_Y, self.bar_y - BAR_DESCENT)
        self._spawn_combo_particles(self.bar_color, 5 + self.combo * 2)
        self._spawn_floating_text(
            f"AUTO x{self.combo}", PLAYER_X, PLAYER_Y - 20, CYAN
        )

    def _on_bar_hit(self) -> None:
        self.combo = 0
        self.heat += HEAT_BAR_HIT
        self._spawn_heat_particles()
        self._shake_frames = 8
        self._spawn_floating_text("MISS!", PLAYER_X, PLAYER_Y - 20, ORANGE)

        if self.heat >= HEAT_MAX and not self.super_mode:
            self._end_game()

    def _end_game(self) -> None:
        self.phase = Phase.GAME_OVER
        self.best_score = max(self.best_score, self.score)

    # -- Particle / text helpers -----------------------------------------

    def _spawn_combo_particles(self, color: int, count: int) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=PLAYER_X,
                    y=PLAYER_Y - 10,
                    vx=self.rng.uniform(-3, 3),
                    vy=self.rng.uniform(-5, -1),
                    life=self.rng.randint(15, 30),
                    color=color,
                    size=self.rng.randint(2, 5),
                )
            )

    def _spawn_super_particles(self) -> None:
        for _ in range(30):
            angle = self.rng.uniform(0, math.pi * 2)
            speed = self.rng.uniform(2, 6)
            color = RAINBOW_COLORS[self.rng.randint(0, len(RAINBOW_COLORS) - 1)]
            self.particles.append(
                Particle(
                    x=PLAYER_X,
                    y=PLAYER_Y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=self.rng.randint(25, 45),
                    color=color,
                    size=self.rng.randint(2, 6),
                )
            )

    def _spawn_heat_particles(self) -> None:
        for _ in range(3):
            self.particles.append(
                Particle(
                    x=PLAYER_X + self.rng.uniform(-10, 10),
                    y=PLAYER_Y,
                    vx=self.rng.uniform(-1, 1),
                    vy=self.rng.uniform(-3, -1),
                    life=self.rng.randint(10, 20),
                    color=RED,
                    size=2,
                )
            )

    def _spawn_floating_text(self, text: str, x: float, y: float, color: int) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=30, color=color)
        )

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.2
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for t in self.floating_texts[:]:
            t.y -= 1
            t.life -= 1
            if t.life <= 0:
                self.floating_texts.remove(t)

    # -- Drawing ---------------------------------------------------------

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = "LIMBO CHAIN"
        subtitle = "Color-Match Limbo!"
        pyxel.text(SCREEN_W // 2 - len(title) * 2, 50, title, WHITE)
        pyxel.text(SCREEN_W // 2 - len(subtitle) * 2, 65, subtitle, GRAY)

        lines = [
            ("How to Play", YELLOW),
            ("Press SPACE to duck under the bar", WHITE),
            ("Match consecutive colors = COMBO chain!", LIME),
            ("COMBO x4 = SUPER LIMBO! (5s rainbow)", CYAN),
            ("Wrong color adds HEAT", RED),
            ("Miss the window = even more HEAT!", ORANGE),
        ]
        y = 95
        for text, color in lines:
            pyxel.text(SCREEN_W // 2 - len(text) * 2, y, text, color)
            y += 14

        pyxel.text(
            SCREEN_W // 2 - 55, y + 10, "HEAT = 100 or Time Up = Game Over", GRAY
        )

        if (self._rainbow_frame // 30) % 2 == 0:
            msg = "Press SPACE to start!"
            pyxel.text(SCREEN_W // 2 - len(msg) * 2, SCREEN_H - 30, msg, WHITE)

    def _draw_playing(self) -> None:
        px = 0
        py = 0
        if self._shake_frames > 0:
            px = self.rng.randint(-3, 3)
            py = self.rng.randint(-3, 3)

        # SUPER border
        if self.super_mode:
            ri = (self._rainbow_frame // 4) % len(RAINBOW_COLORS)
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, RAINBOW_COLORS[ri])
            if (self._rainbow_frame // 6) % 2 == 0:
                pyxel.rectb(
                    1, 1, SCREEN_W - 2, SCREEN_H - 2,
                    RAINBOW_COLORS[(ri + 1) % len(RAINBOW_COLORS)],
                )

        # Ground
        ground_y = 208
        pyxel.line(0 + px, ground_y + py, SCREEN_W + px, ground_y + py, GRAY)

        # Player
        self._draw_player(PLAYER_X + px, PLAYER_Y + py)

        # Bar
        self._draw_bar(px, py)

        # Particles
        for p in self.particles:
            pyxel.rect(int(p.x + px), int(p.y + py), p.size, p.size, p.color)

        # Floating texts
        for t in self.floating_texts:
            alpha = t.life / 30.0
            color = t.color if alpha > 0.4 else GRAY
            pyxel.text(int(t.x + px) - len(t.text) * 2, int(t.y + py), t.text, color)

        # HUD
        self._draw_hud()

    def _draw_player(self, x: int, y: int) -> None:
        if self.player_ducking:
            # Compressed stance
            pyxel.circ(x, y - 12, 4, WHITE)
            pyxel.line(x, y - 8, x, y - 2, WHITE)
            pyxel.line(x, y - 5, x + 7, y - 2, WHITE)
            pyxel.line(x, y - 5, x - 7, y - 2, WHITE)
            pyxel.line(x, y - 2, x + 5, y + 3, WHITE)
            pyxel.line(x, y - 2, x - 5, y + 3, WHITE)
        else:
            pyxel.circ(x, y - 20, 5, WHITE)
            pyxel.line(x, y - 15, x, y - 5, WHITE)
            pyxel.line(x, y - 12, x + 8, y - 15, WHITE)
            pyxel.line(x, y - 12, x - 8, y - 15, WHITE)
            pyxel.line(x, y - 5, x + 5, y + 5, WHITE)
            pyxel.line(x, y - 5, x - 5, y + 5, WHITE)

    def _draw_bar(self, px: int = 0, py: int = 0) -> None:
        left = BAR_X - BAR_WIDTH // 2
        right = BAR_X + BAR_WIDTH // 2
        by = int(self.bar_y)

        # Poles
        pole_top = by - 30
        pyxel.rect(left + px - 2, pole_top + py, 4, 30, GRAY)
        pyxel.rect(right + px - 2, pole_top + py, 4, 30, GRAY)

        # Bar body
        pyxel.rect(left + px, by + py, BAR_WIDTH, BAR_HEIGHT, self.bar_color)

        # Color indicator above bar
        ind_w, ind_h = 30, 10
        pyxel.rect(
            BAR_X - ind_w // 2 + px, by - 20 + py, ind_w, ind_h, self.bar_color
        )
        pyxel.rectb(
            BAR_X - ind_w // 2 + px, by - 20 + py, ind_w, ind_h, WHITE
        )

    def _draw_hud(self) -> None:
        # Timer
        seconds = self.timer // 60
        timer_color = RED if seconds <= 10 else WHITE
        pyxel.text(5, 5, f"TIME: {seconds:02d}", timer_color)

        # Score
        score_text = f"SCORE: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_text) * 2, 5, score_text, WHITE)

        # Combo
        if self.combo > 0:
            c_color = (
                RAINBOW_COLORS[self._rainbow_frame % len(RAINBOW_COLORS)]
                if self.super_mode
                else LIME
            )
            combo_text = f"COMBO x{self.combo}"
            pyxel.text(
                SCREEN_W - len(combo_text) * 4 - 5, 5, combo_text, c_color
            )

        # SUPER remaining
        if self.super_mode:
            remain = self.super_timer // 60 + 1
            s_text = f"SUPER {remain}s"
            ri = (self._rainbow_frame // 4) % len(RAINBOW_COLORS)
            pyxel.text(
                SCREEN_W // 2 - len(s_text) * 2,
                16,
                s_text,
                RAINBOW_COLORS[ri],
            )

        # HEAT bar (bottom)
        hbx, hby = 10, SCREEN_H - 16
        hbw, hbh = SCREEN_W - 20, 8
        pyxel.rect(hbx, hby, hbw, hbh, GRAY)
        fill = int(hbw * min(1.0, self.heat / HEAT_MAX))
        h_color = ORANGE if self.heat >= 70 else RED
        pyxel.rect(hbx, hby, fill, hbh, h_color)
        pyxel.rectb(hbx, hby, hbw, hbh, WHITE)
        pyxel.text(hbx + 2, hby - 7, "HEAT", GRAY)

        # Bar height indicator (right edge)
        ratio = (self.bar_y - BAR_MIN_Y) / (BAR_INITIAL_Y - BAR_MIN_Y)
        ind_x, ind_top, ind_bot = SCREEN_W - 10, 40, 140
        ind_h = int((ind_bot - ind_top) * ratio)
        pyxel.rect(ind_x, ind_top, 5, ind_bot - ind_top, GRAY)
        pyxel.rect(ind_x, ind_bot - ind_h, 5, ind_h, self.bar_color)

    def _draw_game_over(self) -> None:
        title = "GAME OVER"
        pyxel.text(SCREEN_W // 2 - len(title) * 2, 40, title, RED)

        y = 80
        pyxel.text(SCREEN_W // 2 - 30, y, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 30, y + 20, f"MAX COMBO: {self.max_combo}", LIME)
        pyxel.text(
            SCREEN_W // 2 - 30, y + 40, f"BEST SCORE: {self.best_score}", YELLOW
        )

        if self.timer <= 0:
            pyxel.text(SCREEN_W // 2 - 20, y + 65, "Time Up!", GRAY)
        else:
            pyxel.text(SCREEN_W // 2 - 25, y + 65, "Overheated!", RED)

        if (self._rainbow_frame // 30) % 2 == 0:
            msg = "Press SPACE to retry!"
            pyxel.text(SCREEN_W // 2 - len(msg) * 2, SCREEN_H - 30, msg, WHITE)


# -- Testable factory ----------------------------------------------------


def _make_game() -> Game:
    g = Game.__new__(Game)
    g._init_state()
    return g


# -- Entry point ---------------------------------------------------------


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
