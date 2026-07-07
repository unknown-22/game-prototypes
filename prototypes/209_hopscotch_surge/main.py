"""HOPSCOTCH SURGE — Color-Match COMBO Chain Hopscotch.

Core fun moment: chaining same-color square landings to build explosive COMBO,
then blazing through the court in rainbow SUPER HOP mode.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import IntEnum

import pyxel

SCREEN_W = 320
SCREEN_H = 240
FPS = 60

NUM_COLORS = 4
COMBO_SUPER = 4
SUPER_DURATION = 300
HEAT_MAX = 100
HEAT_MISMATCH = 15
HEAT_TIMEOUT = 5
HEAT_DECAY = 0.05
GAME_DURATION = 60 * FPS
HOP_INTERVAL_INITIAL = 75
HOP_INTERVAL_MIN = 18

SQUARE_W = 48
SQUARE_H = 30
SQUARE_CURRENT_X = 120
SQUARE_NEXT_X = 200
SQUARE_Y = 160
PLAYER_X = 96
PLAYER_Y = 145

COLOR_BLACK = 0
COLOR_NAVY = 1
COLOR_GREEN = 3
COLOR_DARK_BLUE = 5
COLOR_WHITE = 7
COLOR_RED = 8
COLOR_ORANGE = 9
COLOR_YELLOW = 10
COLOR_LIME = 11
COLOR_GRAY = 13
COLOR_PINK = 14

COLOR_VALS = (COLOR_RED, COLOR_GREEN, COLOR_DARK_BLUE, COLOR_YELLOW)
COLOR_LABELS = ("R", "G", "B", "Y")


class Phase(IntEnum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


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


class Game:
    """Hopscotch Surge — color-match combo hopscotch."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="HOPSCOTCH SURGE", fps=FPS)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self._rng = random.Random()
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.timer: int = GAME_DURATION
        self.hop_timer: int = HOP_INTERVAL_INITIAL
        self.player_color: int = self._rng.randint(0, NUM_COLORS - 1)
        self.current_color: int = self.player_color
        self.next_color: int = self._generate_next_square()
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._reset_animation: int = 0

    # ── Core logic (headless-testable) ──────────────────────────────

    def _generate_next_square(self) -> int:
        """Generate next square color with 40% bias toward player_color."""
        if self._rng.random() < 0.4:
            return self.player_color
        return self._rng.randint(0, NUM_COLORS - 1)

    def _hop_interval(self) -> int:
        """Get current hop interval based on remaining time."""
        elapsed = GAME_DURATION - self.timer
        frac = min(elapsed / GAME_DURATION, 1.0)
        hop_range = HOP_INTERVAL_INITIAL - HOP_INTERVAL_MIN
        return max(HOP_INTERVAL_MIN, int(HOP_INTERVAL_INITIAL - frac * hop_range))

    def _do_hop(self, mismatch: bool = False) -> None:
        """Process a hop (either player-triggered or auto-hop timeout).

        Args:
            mismatch: True if this is an auto-hop timeout (forced miss).
        """
        if self.phase != Phase.PLAYING:
            return

        if mismatch:
            self.heat = min(HEAT_MAX, self.heat + HEAT_TIMEOUT)
            self.combo = 0
        elif self.super_mode or self.next_color == self.player_color:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            base_score = 10
            multiplier = 1 + self.combo * 0.5
            if self.super_mode:
                multiplier *= 3
            self.score += int(base_score * multiplier)
            self._spawn_floating_text(f"+{int(base_score * multiplier)}", COLOR_WHITE)

            if not self.super_mode and self.combo >= COMBO_SUPER:
                self.super_mode = True
                self.super_timer = SUPER_DURATION
                self._spawn_floating_text("SUPER!", COLOR_PINK)
                self._spawn_particles(PLAYER_X + SQUARE_W // 2, PLAYER_Y, COLOR_VALS[self.player_color], 20)
        else:
            self.heat = min(HEAT_MAX, self.heat + HEAT_MISMATCH)
            self.combo = 0
            self._spawn_floating_text(f"+{HEAT_MISMATCH} HEAT!", COLOR_RED)

        self.player_color = self.next_color
        self.current_color = self.next_color
        self.next_color = self._generate_next_square()
        self.hop_timer = self._hop_interval()

        if not mismatch:
            self._spawn_particles(PLAYER_X + SQUARE_W // 2, PLAYER_Y, COLOR_VALS[self.current_color], 6)

    def _update_super(self) -> None:
        """Decrement super_timer and deactivate when expired."""
        if not self.super_mode:
            return
        self.super_timer -= 1
        if self.super_timer <= 0:
            self.super_mode = False
            self.super_timer = 0

    def _update_timers(self) -> None:
        """Update hop_timer, timer, heat decay. Auto-hop on timeout."""
        if self.phase != Phase.PLAYING:
            return

        self.hop_timer -= 1
        self.timer -= 1

        if self.hop_timer <= 0:
            self._do_hop(mismatch=True)

        if self.heat >= HEAT_MAX or self.timer <= 0:
            self._end_game()
        else:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _end_game(self) -> None:
        """Transition to game-over phase."""
        self.phase = Phase.GAME_OVER
        self.timer = max(0, self.timer)

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y -= 0.8
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 3.0)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed - 2,
                    life=15 + self._rng.randint(0, 10),
                    color=color,
                )
            )

    def _spawn_floating_text(self, text: str, color: int) -> None:
        self.floating_texts.append(
            FloatingText(
                x=float(SQUARE_CURRENT_X + SQUARE_W // 2 - len(text) * 2),
                y=float(SQUARE_Y - 10),
                text=text,
                life=45,
                color=color,
            )
        )

    # ── Input helpers ───────────────────────────────────────────────

    @staticmethod
    def _btn_hop() -> bool:
        return pyxel.btnp(pyxel.KEY_SPACE)

    @staticmethod
    def _btn_restart() -> bool:
        return pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_R)

    # ── Update ──────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if self._btn_hop():
                self.reset()
                self.phase = Phase.PLAYING
                self.player_color = self._rng.randint(0, NUM_COLORS - 1)
                self.current_color = self.player_color
                self.next_color = self._generate_next_square()
            return

        if self.phase == Phase.GAME_OVER:
            if self._btn_restart():
                self.reset()
                self.phase = Phase.PLAYING
                self.player_color = self._rng.randint(0, NUM_COLORS - 1)
                self.current_color = self.player_color
                self.next_color = self._generate_next_square()
            return

        # PLAYING
        if self._btn_hop():
            self._do_hop()
        self._update_timers()
        self._update_super()
        self._update_particles()
        self._update_floating_texts()

    # ── Draw ────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(COLOR_BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        # Super mode rainbow border
        if self.super_mode:
            self._draw_super_border()

        self._draw_hud()
        self._draw_court()
        self._draw_player()
        self._draw_floating_texts()
        self._draw_particles()

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        cx = SCREEN_W // 2
        y = 40

        pyxel.text(cx - 55, y, "HOPSCOTCH SURGE", COLOR_YELLOW)
        y += 24
        pyxel.text(cx - 70, y, "Color-Match COMBO Hopscotch", COLOR_GRAY)
        y += 36
        pyxel.text(cx - 50, y, "SPACE: Hop to next square", COLOR_WHITE)
        y += 12
        pyxel.text(cx - 50, y, "Match color = COMBO + Score", COLOR_GREEN)
        y += 12
        pyxel.text(cx - 50, y, "Mismatch = HEAT!", COLOR_RED)
        y += 12
        pyxel.text(cx - 50, y, "COMBO x4 = SUPER HOP!", COLOR_PINK)
        y += 36
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(cx - 45, y, "PRESS SPACE", COLOR_YELLOW)

    def _draw_super_border(self) -> None:
        """Rainbow border around screen edge in super mode."""
        t = pyxel.frame_count
        colors = (COLOR_RED, COLOR_ORANGE, COLOR_YELLOW, COLOR_GREEN, COLOR_DARK_BLUE, COLOR_PINK)
        for i in range(SCREEN_W):
            ci = (i + t // 2) % len(colors)
            pyxel.pset(i, 0, colors[ci])
            pyxel.pset(i, SCREEN_H - 1, colors[ci])
        for i in range(SCREEN_H):
            ci = (i + t // 2) % len(colors)
            pyxel.pset(0, i, colors[ci])
            pyxel.pset(SCREEN_W - 1, i, colors[ci])

    def _draw_hud(self) -> None:
        pyxel.text(8, 6, f"SCORE: {self.score}", COLOR_WHITE)
        combo_col = COLOR_PINK if self.combo >= COMBO_SUPER else COLOR_YELLOW
        pyxel.text(120, 6, f"COMBO x{self.combo}", combo_col)
        if self.max_combo > 0:
            pyxel.text(218, 6, f"MAX: {self.max_combo}", COLOR_GRAY)

        bar_x = 8
        bar_y = 18
        bar_w = 100
        bar_h = 6
        heat_ratio = self.heat / HEAT_MAX
        bar_color = COLOR_GREEN if heat_ratio <= 0.4 else (COLOR_ORANGE if heat_ratio <= 0.7 else COLOR_RED)
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, COLOR_NAVY)
        pyxel.rect(bar_x, bar_y, int(bar_w * heat_ratio), bar_h, bar_color)
        pyxel.text(bar_x, bar_y + 8, f"TIME: {max(0, self.timer // FPS)}", COLOR_WHITE)

        if self.super_mode:
            pyxel.text(250, 6, f"SUPER: {self.super_timer // 60 + 1}s", COLOR_PINK)

    def _draw_court(self) -> None:
        """Draw current and next hopscotch squares."""
        # Floor line
        pyxel.line(40, SQUARE_Y + SQUARE_H, 280, SQUARE_Y + SQUARE_H, COLOR_WHITE)

        # Current square
        cx = SQUARE_CURRENT_X - SQUARE_W // 2
        cy = SQUARE_Y
        current_color = COLOR_VALS[self.current_color]
        pyxel.rect(cx, cy, SQUARE_W, SQUARE_H, current_color)
        pyxel.rectb(cx, cy, SQUARE_W, SQUARE_H, COLOR_WHITE if not self.super_mode else COLOR_YELLOW)
        # Color label
        label = COLOR_LABELS[self.current_color]
        pyxel.text(cx + SQUARE_W // 2 - 2, cy + SQUARE_H // 2 - 4, label, COLOR_WHITE)

        # Next square
        nx = SQUARE_NEXT_X - SQUARE_W // 2
        ny = SQUARE_Y
        next_color = COLOR_VALS[self.next_color]
        pyxel.rect(nx, ny, SQUARE_W, SQUARE_H, next_color)
        pyxel.rectb(nx, ny, SQUARE_W, SQUARE_H, COLOR_WHITE if not self.super_mode else COLOR_YELLOW)
        label = COLOR_LABELS[self.next_color]
        pyxel.text(nx + SQUARE_W // 2 - 2, ny + SQUARE_H // 2 - 4, label, COLOR_WHITE)

        # Arrow from current to next
        arrow_y = SQUARE_Y + SQUARE_H // 2
        pyxel.line(SQUARE_CURRENT_X + SQUARE_W // 2, arrow_y,
                    SQUARE_NEXT_X - SQUARE_W // 2, arrow_y, COLOR_GRAY)

        # Player color indicator
        px = cx - 14
        py_label = cy + SQUARE_H // 2 - 4
        pyxel.text(px, py_label, "YOU:", COLOR_GRAY)
        pyxel.rect(px + 16, py_label, 8, 8, COLOR_VALS[self.player_color])

    def _draw_player(self) -> None:
        """Draw player figure above current square."""
        px = PLAYER_X
        py = PLAYER_Y

        # Simple hop animation based on hop_timer
        hop_progress = 1.0 - (self.hop_timer / max(1, self._hop_interval()))
        bounce_y = int(abs(math.sin(hop_progress * math.pi)) * 10) if self.phase == Phase.PLAYING else 0
        draw_x = px + int(hop_progress * (SQUARE_NEXT_X - SQUARE_CURRENT_X))
        draw_y = py - bounce_y

        player_color = COLOR_WHITE
        if self.super_mode:
            t = pyxel.frame_count
            rainbow = (COLOR_RED, COLOR_ORANGE, COLOR_YELLOW, COLOR_GREEN, COLOR_LIME,
                       COLOR_DARK_BLUE, COLOR_PINK)
            player_color = rainbow[(t // 4) % len(rainbow)]

        # Head
        pyxel.circ(draw_x + 16, draw_y + 2, 4, player_color)
        # Body
        pyxel.rect(draw_x + 13, draw_y + 6, 6, 8, player_color)
        # Arms
        pyxel.line(draw_x + 13, draw_y + 8, draw_x + 8, draw_y + 12, player_color)
        pyxel.line(draw_x + 19, draw_y + 8, draw_x + 24, draw_y + 12, player_color)
        # Legs
        pyxel.line(draw_x + 14, draw_y + 14, draw_x + 11, draw_y + 20, player_color)
        pyxel.line(draw_x + 18, draw_y + 14, draw_x + 21, draw_y + 20, player_color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 45
            c = ft.color if alpha > 0.5 else COLOR_GRAY
            pyxel.text(int(ft.x), int(ft.y), ft.text, c)

    def _draw_particles(self) -> None:
        for p in self.particles:
            px_val = int(p.x)
            py_val = int(p.y)
            if 0 <= px_val < SCREEN_W and 0 <= py_val < SCREEN_H:
                pyxel.pset(px_val, py_val, p.color)

    def _draw_game_over(self) -> None:
        cx = SCREEN_W // 2
        cy = SCREEN_H // 2

        pyxel.rect(cx - 90, cy - 55, 180, 110, COLOR_BLACK)
        pyxel.rectb(cx - 90, cy - 55, 180, 110, COLOR_WHITE)

        pyxel.text(cx - 30, cy - 44, "GAME OVER", COLOR_RED)
        pyxel.text(cx - 45, cy - 26, f"SCORE: {self.score}", COLOR_WHITE)
        pyxel.text(cx - 45, cy - 14, f"MAX COMBO: {self.max_combo}", COLOR_YELLOW)
        pyxel.text(cx - 45, cy - 2, f"HEAT: {int(self.heat)}", COLOR_RED)
        pyxel.text(cx - 45, cy + 18, "PRESS SPACE / R", COLOR_WHITE)
        pyxel.text(cx - 45, cy + 32, "TO RESTART", COLOR_WHITE)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = GAME_DURATION
    g.hop_timer = HOP_INTERVAL_INITIAL
    g.player_color = 0
    g.current_color = 0
    g.next_color = 0
    g.super_mode = False
    g.super_timer = 0
    g.particles = []
    g.floating_texts = []
    g._rng = random.Random()
    return g


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
