from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

import pyxel

# Color constants
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

# Game constants
SCREEN_W = 320
SCREEN_H = 240
BUCK_COLORS = [RED, GREEN, DARK_BLUE, YELLOW]
SUPER_COLORS = [RED, GREEN, DARK_BLUE, YELLOW, ORANGE, CYAN, PINK, LIME]
BUCK_INTERVAL_INITIAL = 90
BUCK_INTERVAL_MIN = 30
REACTION_WINDOW = 45
SUPER_DURATION = 300
SUPER_BUCK_INTERVAL = 30
GAME_DURATION = 60 * 60
HEAT_WRONG = 15.0
HEAT_TIMEOUT = 15.0
HEAT_DECAY = 0.02
HEAT_MAX = 100.0
SCORE_BASE = 10


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
    vy: float = -1.5


class Phase(Enum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, "BULL SURGE", display_scale=2, fps=60)
        self.rng = random.Random(42)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.best_score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.buck_color: int = 0
        self.buck_timer: int = BUCK_INTERVAL_INITIAL
        self.reaction_timer: int = 0
        self.game_timer: int = GAME_DURATION
        self.buck_interval: int = BUCK_INTERVAL_INITIAL
        self.super_timer: int = 0
        self.shake_frames: int = 0
        self.shake_intensity: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.game_over_reason: str = ""
        self.prev_combo: int = 0

    # --- Core logic methods (testable, no pyxel input calls) ---

    def _handle_match(self, color_idx: int) -> bool:
        """Process a color match attempt. Returns True if matched."""
        if self.reaction_timer <= 0:
            return False
        if color_idx == self.buck_color:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            multiplier = self._get_score_multiplier()
            points = int(SCORE_BASE * (1.0 + self.combo * 0.5) * multiplier)
            self.score += points
            self._spawn_match_particles()
            self._spawn_floating_text(f"+{points}", self.buck_color)
            if self.combo >= 2:
                self._spawn_floating_text(f"COMBO x{self.combo}!", YELLOW)
            if self.combo >= 4:
                self._activate_super()
            self._spawn_buck()
            return True
        else:
            self.combo = 0
            self.heat = min(HEAT_MAX, self.heat + HEAT_WRONG)
            self._spawn_miss_particles()
            self._spawn_floating_text("MISS!", RED)
            self._spawn_buck()
            return False

    def _handle_timeout(self) -> None:
        self.combo = 0
        self.heat = min(HEAT_MAX, self.heat + HEAT_TIMEOUT)
        self._spawn_miss_particles()
        self._spawn_floating_text("TOO SLOW!", RED)
        self._spawn_buck()

    def _update_playing(self) -> None:
        self.game_timer -= 1
        if self.game_timer <= 0:
            self.game_timer = 0
            self.game_over_reason = "TIME'S UP!"
            self.phase = Phase.GAME_OVER
            if self.score > self.best_score:
                self.best_score = self.score
            return

        if self.heat >= HEAT_MAX:
            self.game_over_reason = "THROWN OFF!"
            self.phase = Phase.GAME_OVER
            if self.score > self.best_score:
                self.best_score = self.score
            return

        self._update_heat()
        self._update_super_mode()
        self._update_difficulty()
        self._update_buck_timers()
        self._update_particles()
        self._update_floating_texts()

        if self.shake_frames > 0:
            self.shake_frames -= 1

    def _update_buck_timers(self) -> None:
        if self.reaction_timer > 0:
            self.reaction_timer -= 1
            if self.reaction_timer <= 0:
                self._handle_timeout()
            return

        if self.super_timer > 0:
            self.buck_timer -= 1
            if self.buck_timer <= 0:
                self._auto_match()
        else:
            self.buck_timer -= 1
            if self.buck_timer <= 0:
                self._spawn_buck()

    def _auto_match(self) -> None:
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        multiplier = self._get_score_multiplier()
        points = int(SCORE_BASE * (1.0 + self.combo * 0.5) * multiplier)
        self.score += points
        self._spawn_match_particles()
        self._spawn_floating_text(f"+{points}", self.buck_color)
        self.buck_color = self.rng.randint(0, 3)
        self.buck_timer = SUPER_BUCK_INTERVAL
        self.reaction_timer = 0

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self.shake_frames = 15
        self.shake_intensity = 4
        self._spawn_floating_text("SUPER RIDE!", WHITE)
        for _ in range(20):
            color = self.rng.choice(SUPER_COLORS)
            self.particles.append(Particle(
                x=160, y=150,
                vx=self.rng.uniform(-3.0, 3.0),
                vy=self.rng.uniform(-5.0, -1.0),
                life=self.rng.randint(15, 30),
                color=color,
            ))

    def _update_heat(self) -> None:
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_super_mode(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_timer = 0
                self.combo = 0

    def _update_difficulty(self) -> None:
        elapsed_sec = (GAME_DURATION - self.game_timer) / 60
        new_interval = BUCK_INTERVAL_INITIAL - int(elapsed_sec * 2)
        self.buck_interval = max(BUCK_INTERVAL_MIN, new_interval)

    def _spawn_buck(self) -> None:
        if self.super_timer > 0:
            self.buck_color = self.rng.randint(0, 3)
            self.buck_timer = SUPER_BUCK_INTERVAL
            self.reaction_timer = 0
        else:
            self.buck_color = self.rng.randint(0, 3)
            self.buck_timer = self.buck_interval
            self.reaction_timer = REACTION_WINDOW

    def _get_score_multiplier(self) -> float:
        return 3.0 if self.super_timer > 0 else 1.0

    def _spawn_match_particles(self) -> None:
        for _ in range(10):
            self.particles.append(Particle(
                x=80, y=120,
                vx=self.rng.uniform(-3.0, 3.0),
                vy=self.rng.uniform(-5.0, -1.0),
                life=self.rng.randint(15, 30),
                color=BUCK_COLORS[self.buck_color],
            ))

    def _spawn_miss_particles(self) -> None:
        for _ in range(5):
            self.particles.append(Particle(
                x=80, y=120,
                vx=self.rng.uniform(-2.0, 2.0),
                vy=self.rng.uniform(-3.0, -1.0),
                life=self.rng.randint(10, 20),
                color=RED,
            ))

    def _spawn_floating_text(self, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(
            x=160, y=60,
            text=text,
            life=30,
            color=color,
        ))

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def _update_floating_texts(self) -> None:
        alive: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life > 0:
                alive.append(ft)
        self.floating_texts = alive

    # --- Input handling ---

    def _check_color_input(self) -> None:
        """Check for color key presses and attempt matches."""
        if pyxel.btnp(pyxel.KEY_1) or pyxel.btnp(pyxel.KEY_Q) or pyxel.btnp(pyxel.KEY_Z):
            self._handle_match(0)
        elif pyxel.btnp(pyxel.KEY_2) or pyxel.btnp(pyxel.KEY_W) or pyxel.btnp(pyxel.KEY_X):
            self._handle_match(1)
        elif pyxel.btnp(pyxel.KEY_3) or pyxel.btnp(pyxel.KEY_E) or pyxel.btnp(pyxel.KEY_C):
            self._handle_match(2)
        elif pyxel.btnp(pyxel.KEY_4) or pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.KEY_V):
            self._handle_match(3)

    # --- Update ---

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._check_color_input()
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN):
            self._start_game()

    def _start_game(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.buck_color = 0
        self.buck_timer = BUCK_INTERVAL_INITIAL
        self.reaction_timer = 0
        self.game_timer = GAME_DURATION
        self.buck_interval = BUCK_INTERVAL_INITIAL
        self.super_timer = 0
        self.shake_frames = 0
        self.shake_intensity = 0
        self.particles = []
        self.floating_texts = []
        self.game_over_reason = ""
        self.phase = Phase.PLAYING

    def _update_game_over(self) -> None:
        self._update_particles()
        self._update_floating_texts()
        if self.shake_frames > 0:
            self.shake_frames -= 1
        if pyxel.btnp(pyxel.KEY_RETURN):
            self._start_game()

    # --- Draw ---

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.shake_frames > 0:
            sx = self.rng.randint(-self.shake_intensity, self.shake_intensity)
            sy = self.rng.randint(-self.shake_intensity, self.shake_intensity)
            pyxel.camera(sx, sy)
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(110, 50, "BULL SURGE", WHITE)
        pyxel.text(70, 80, "Match colors to stay on!", WHITE)
        pyxel.text(40, 100, "1/RED  2/GREEN  3/BLUE  4/YELLOW", GRAY)
        pyxel.text(60, 120, "Same color = COMBO x4 = SUPER!", YELLOW)
        pyxel.text(60, 140, "Wrong = HEAT! HEAT 100 = thrown!", RED)
        pyxel.text(70, 170, "Survive 60 seconds!", WHITE)
        pyxel.text(90, 210, "Press ENTER to ride!", YELLOW)

    def _draw_playing(self) -> None:
        self._draw_arena()
        self._draw_bull()
        self._draw_rider()
        self._draw_hud()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_super_effects()
        self._draw_key_hints()

    def _draw_arena(self) -> None:
        pyxel.rect(0, SCREEN_H - 30, SCREEN_W, 30, BROWN)
        pyxel.line(0, SCREEN_H - 30, SCREEN_W, SCREEN_H - 30, GRAY)
        for i in range(0, SCREEN_W, 40):
            pyxel.line(i, SCREEN_H - 30, i - 10, SCREEN_H - 15, GRAY)

    def _draw_bull(self) -> None:
        color = DARK_BLUE if self.reaction_timer <= 0 else BROWN

        buck_sy = 0
        if self.reaction_timer > 0 and self.reaction_timer > REACTION_WINDOW - 10:
            buck_sy = -3 if self.reaction_timer % 6 < 3 else 3

        bx = 60
        by = SCREEN_H - 80 + buck_sy

        pyxel.elli(bx + 40, by + 10, 100, 60, color)
        pyxel.elli(bx + 40, by + 5, 60, 50, color)
        pyxel.ellib(bx + 40, by + 10, 100, 60, GRAY)

        pyxel.circ(bx, by + 30, 22, BROWN)
        pyxel.circ(bx, by + 30, 18, PEACH)
        pyxel.circ(bx + 5, by + 25, 4, BLACK)
        pyxel.line(bx - 15, by + 15, bx - 5, by + 5, WHITE)
        pyxel.line(bx - 20, by + 20, bx - 8, by + 10, WHITE)
        pyxel.line(bx - 15, by + 45, bx + 10, by + 45, WHITE)
        pyxel.line(bx - 15, by + 50, bx + 10, by + 50, WHITE)

        for i in range(0, 100, 15):
            px = bx + 5 + i
            py = by + 12
            pyxel.line(px, py, px - 5, py - 8, GRAY)

        ring_y = by + 5
        ring_color = BUCK_COLORS[self.buck_color]
        for i in range(5):
            pyxel.circb(bx + 40, ring_y, 25 + i * 6, ring_color)
        pyxel.ellib(bx + 40, ring_y, 52, 14, ring_color)

    def _draw_rider(self) -> None:
        bx = 60
        by = SCREEN_H - 80

        buck_sy = 0
        if self.reaction_timer > 0 and self.reaction_timer > REACTION_WINDOW - 10:
            buck_sy = -3 if self.reaction_timer % 6 < 3 else 3

        rx = bx + 60
        ry = by - 35 + buck_sy

        pyxel.circ(int(rx), int(ry), 8, PEACH)
        if self.super_timer > 0:
            eye_color = SUPER_COLORS[(pyxel.frame_count // 6) % len(SUPER_COLORS)]
        else:
            eye_color = BUCK_COLORS[self.buck_color]
        pyxel.pset(int(rx) - 2, int(ry) - 1, eye_color)
        pyxel.pset(int(rx) + 2, int(ry) - 1, eye_color)

        pyxel.line(int(rx), int(ry + 8), int(rx), int(ry + 25), WHITE)
        pyxel.line(int(rx), int(ry + 15), int(rx) + 8, int(ry + 8), WHITE)
        pyxel.line(int(rx), int(ry + 15), int(rx) - 5, int(ry + 20), WHITE)

        pyxel.line(int(rx), int(ry + 25), int(rx) - 5, int(ry + 35), WHITE)
        pyxel.line(int(rx), int(ry + 25), int(rx) + 5, int(ry + 35), WHITE)

        lx = int(rx) - 15
        ly = int(ry + 15)
        pyxel.line(lx, ly, bx + 40, by + 5, ORANGE)

    def _draw_hud(self) -> None:
        pyxel.text(4, 2, f"SCORE: {self.score}", WHITE)
        pyxel.text(4, 12, f"COMBO: {self.combo}", YELLOW if self.combo >= 3 else WHITE)

        secs = max(0, self.game_timer / 60)
        time_text = f"TIME: {secs:.1f}s"
        pyxel.text(SCREEN_W - 70, 2, time_text, WHITE)

        bar_x = SCREEN_W - 20
        bar_y = 30
        bar_w = 12
        bar_h = 120
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        fill_h = int(bar_h * self.heat / HEAT_MAX)
        if self.heat < 40:
            heat_color = GREEN
        elif self.heat < 70:
            heat_color = YELLOW
        else:
            heat_color = RED
        pyxel.rect(bar_x, bar_y + bar_h - fill_h, bar_w, fill_h, heat_color)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        pyxel.text(bar_x - 16, bar_y - 8, "HEAT", GRAY)

    def _draw_particles(self) -> None:
        for p in self.particles:
            if p.life > 0:
                size = max(1, p.size * p.life // 30)
                pyxel.rect(int(p.x), int(p.y), size, size, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            if ft.life > 0:
                col = ft.color
                if ft.life < 8 and ft.life % 2 == 0:
                    continue
                tw = len(ft.text) * 4
                pyxel.text(int(ft.x - tw // 2), int(ft.y), ft.text, col)

    def _draw_super_effects(self) -> None:
        if self.super_timer > 0:
            super_color = SUPER_COLORS[(pyxel.frame_count // 6) % len(SUPER_COLORS)]
            pyxel.rectb(1, 1, SCREEN_W - 2, SCREEN_H - 2, super_color)
            pyxel.rectb(3, 3, SCREEN_W - 6, SCREEN_H - 6, super_color)
            pyxel.text(SCREEN_W // 2 - 24, 24, "SUPER RIDE!", super_color)

    def _draw_key_hints(self) -> None:
        hint_y = SCREEN_H - 14
        for i, col in enumerate(BUCK_COLORS):
            x = 40 + i * 70
            key_str = str(i + 1)
            hint_col = col
            if self.reaction_timer > 0 and i == self.buck_color:
                hint_col = WHITE
            px = x
            pyxel.text(px, hint_y, key_str, hint_col)
            pyxel.rect(px + 8, hint_y - 2, 6, 6, col)
            pyxel.rectb(px + 8, hint_y - 2, 6, 6, WHITE)
            label = ["R/Q", "G/W", "B/E", "Y/R"][i]
            pyxel.text(px + 16, hint_y, label, hint_col)

    def _draw_game_over(self) -> None:
        pyxel.text(90, 50, self.game_over_reason, RED)
        pyxel.text(100, 80, f"SCORE: {self.score}", WHITE)
        pyxel.text(90, 100, f"BEST: {self.best_score}", YELLOW)
        pyxel.text(100, 120, f"MAX COMBO: {self.max_combo}", WHITE)
        pyxel.text(80, 160, "Press ENTER to retry", YELLOW)

        for p in self.particles:
            if p.life > 0:
                pyxel.pset(int(p.x), int(p.y), p.color)
        for ft in self.floating_texts:
            if ft.life > 0:
                tw = len(ft.text) * 4
                pyxel.text(int(ft.x - tw // 2), int(ft.y), ft.text, ft.color)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
