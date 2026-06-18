"""
SIGNAL SURGE - Fast-paced signal decoding game
==============================================
Colored signals scroll from right to left across 4 horizontal lanes.
Press Z/X/C/V to decode matching-color signals.
Consecutive same-color decodes build COMBO chain.
COMBO >= 5 triggers SUPER DECODE (5s auto-decode, 3x score).
Wrong key or missed signal builds HEAT. HEAT >= 100 = game over.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel

# Color constants (raw ints, Pyxel 16-color palette)
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

# Signal colors
SIGNAL_COLORS: list[int] = [RED, GREEN, LIGHT_BLUE, YELLOW]
COLOR_NAMES: list[str] = ["RED", "GREEN", "BLUE", "YELLOW"]

# Screen
SCREEN_W = 320
SCREEN_H = 240
FPS = 30

# Lane configuration
LANE_COUNT = 4
LANE_TOP = 40
LANE_H = 40
LANE_CENTER_Y: list[int] = [LANE_TOP + i * LANE_H + LANE_H // 2 for i in range(LANE_COUNT)]

# Key mapping: Z=RED(0), X=GREEN(1), C=LIGHT_BLUE(2), V=YELLOW(3)
KEY_TO_COLOR_IDX: dict[int, int] = {
    pyxel.KEY_Z: 0,
    pyxel.KEY_X: 1,
    pyxel.KEY_C: 2,
    pyxel.KEY_V: 3,
}

# Game constants
MAX_HEAT = 100
SUPER_DURATION = 5 * FPS  # 5 seconds at 30 fps
COMBO_THRESHOLD = 5
BASE_SCORE = 10
WRONG_HEAT = 15
MISS_HEAT = 5
INITIAL_SPAWN_INTERVAL = 45  # frames
MIN_SPAWN_INTERVAL = 15
SIGNAL_W = 30
SIGNAL_H = 20
BASE_SPEED = 1.5


@dataclass
class Signal:
    x: float
    y: float
    color: int
    speed: float
    color_idx: int = 0
    active: bool = True
    flash_timer: int = 0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    max_life: int
    color: int
    size: int = 2


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class Game:
    # Class constants
    SCREEN_W: ClassVar[int] = SCREEN_W
    SCREEN_H: ClassVar[int] = SCREEN_H
    MAX_HEAT: ClassVar[int] = MAX_HEAT
    SUPER_DURATION: ClassVar[int] = SUPER_DURATION
    COMBO_THRESHOLD: ClassVar[int] = COMBO_THRESHOLD
    BASE_SCORE: ClassVar[int] = BASE_SCORE
    WRONG_HEAT: ClassVar[int] = WRONG_HEAT
    MISS_HEAT: ClassVar[int] = MISS_HEAT
    INITIAL_SPAWN_INTERVAL: ClassVar[int] = INITIAL_SPAWN_INTERVAL
    MIN_SPAWN_INTERVAL: ClassVar[int] = MIN_SPAWN_INTERVAL
    SIGNAL_W: ClassVar[int] = SIGNAL_W
    SIGNAL_H: ClassVar[int] = SIGNAL_H
    BASE_SPEED: ClassVar[float] = BASE_SPEED

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="SIGNAL SURGE", fps=FPS, display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    # ══════════════════════════════════════════════════
    # State initialization (testable)
    # ══════════════════════════════════════════════════
    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.super_timer: int = 0
        self.signals: list[Signal] = []
        self.particles: list[Particle] = []
        self.spawn_timer: int = 0
        self.game_timer: int = 0
        self.spawn_interval: int = self.INITIAL_SPAWN_INTERVAL
        self.decoded_count: int = 0
        self._rng: random.Random = random.Random()

        # Visual state
        self._super_flash: int = 0
        self._shake_timer: int = 0
        self._popup_texts: list[tuple[str, float, float, int, int]] = []

    # ══════════════════════════════════════════════════
    # Core game logic (testable, no pyxel calls)
    # ══════════════════════════════════════════════════
    def _spawn_signal(self, rng: random.Random | None = None) -> Signal | None:
        """Create one signal at right edge, random lane and color."""
        if rng is None:
            rng = self._rng
        lane = rng.randint(0, LANE_COUNT - 1)
        color_idx = rng.randint(0, len(SIGNAL_COLORS) - 1)
        color = SIGNAL_COLORS[color_idx]
        return Signal(
            x=float(self.SCREEN_W + self.SIGNAL_W),
            y=float(LANE_CENTER_Y[lane]),
            color=color,
            speed=self._current_speed(),
            color_idx=color_idx,
        )

    def _current_speed(self) -> float:
        return self.BASE_SPEED + self.decoded_count * 0.03

    def _update_signals(self) -> None:
        """Move all signals left, remove off-screen left, add heat for missed."""
        to_remove: list[Signal] = []
        for s in self.signals:
            if not s.active:
                to_remove.append(s)
                continue
            s.x -= s.speed
            if s.flash_timer > 0:
                s.flash_timer -= 1
            if s.x < -self.SIGNAL_W:
                self.heat += self.MISS_HEAT
                to_remove.append(s)
        for s in to_remove:
            if s in self.signals:
                self.signals.remove(s)

    def _find_decode_target(self, color_idx: int) -> Signal | None:
        """Find rightmost active signal of given color_idx across all lanes."""
        best: Signal | None = None
        for s in self.signals:
            if not s.active:
                continue
            if s.color_idx != color_idx:
                continue
            if best is None or s.x > best.x:
                best = s
        return best

    def _decode_signal(self, color_idx: int) -> tuple[int, bool]:
        """Attempt to decode rightmost signal of given color.
        Returns (score_earned, was_successful).
        Updates heat/combo/super_timer/signals/particles_spawn_data.
        Does NOT spawn particles directly (returns info for rendering layer).
        """
        if self.super_timer > 0:
            # During super, auto-decode ALL active signals
            return self._super_decode_all()

        target = self._find_decode_target(color_idx)
        if target is None:
            return (0, False)

        # Color match
        self.decoded_count += 1
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo

        multiplier = self._get_score_multiplier()
        earned = int(self.BASE_SCORE * multiplier)

        if self.combo >= self.COMBO_THRESHOLD and self.super_timer == 0:
            self.super_timer = self.SUPER_DURATION
            self._super_flash = 15

        # Deactivate the signal (will be removed next update)
        target.active = False
        target.flash_timer = 0

        return (earned, True)

    def _decode_wrong(self, color_idx: int) -> tuple[int, bool]:
        """Handle wrong key press. Returns (score, was_successful)."""
        # Check if there are ANY active signals
        has_signals = any(s.active for s in self.signals)
        if not has_signals:
            return (0, False)

        target = self._find_decode_target(color_idx)
        if target is not None:
            # There IS a signal of this color, so it would have been handled by _decode_signal
            return (0, False)

        # Pressed a color key but no signal of that color is on screen
        # This is a wrong decode attempt
        self.heat += self.WRONG_HEAT
        self.combo = 0
        return (0, False)

    def _process_decode_key(self, color_idx: int) -> tuple[int, bool, int, float, float]:
        """Process a decode key press. Returns (score, was_match, particle_color, px, py)."""
        if self.super_timer > 0:
            earned, _ = self._super_decode_all()
            return (earned, True, WHITE, 0.0, 0.0)

        target = self._find_decode_target(color_idx)
        if target is not None:
            earned, _ = self._decode_signal(color_idx)
            px, py = target.x, target.y
            pcol = target.color
            return (earned, True, pcol, px, py)

        # No matching signal - wrong key
        any_signals = any(s.active for s in self.signals)
        if any_signals:
            self.heat += self.WRONG_HEAT
            self.combo = 0
        return (0, False, GRAY, 0.0, 0.0)

    def _super_decode_all(self) -> tuple[int, bool]:
        """During SUPER DECODE: auto-decode all active signals. Returns (total_score, True)."""
        total = 0
        for s in self.signals:
            if not s.active:
                continue
            self.decoded_count += 1
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            multiplier = self._get_score_multiplier()
            total += int(self.BASE_SCORE * multiplier * 3)  # 3x during super
            s.active = False
            s.flash_timer = 5
        return (total, True)

    def _update_super(self) -> None:
        """Tick super_timer down."""
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer == 0:
                self.combo = 0
        if self._super_flash > 0:
            self._super_flash -= 1

    def _update_particles(self) -> None:
        """Move particles, decrement life, remove dead."""
        dead: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                dead.append(p)
        for p in dead:
            self.particles.remove(p)

    def _spawn_particles(
        self, x: float, y: float, color: int, count: int = 8
    ) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.tau)
            speed = self._rng.uniform(0.5, 2.5)
            life = self._rng.randint(15, 25)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed - 0.5,
                    life=life,
                    max_life=life,
                    color=color,
                    size=self._rng.randint(1, 3),
                )
            )

    def _spawn_super_particles(self) -> None:
        for _ in range(30):
            color = SIGNAL_COLORS[self._rng.randint(0, 3)]
            angle = self._rng.uniform(0, math.tau)
            speed = self._rng.uniform(1.0, 4.0)
            life = self._rng.randint(20, 40)
            self.particles.append(
                Particle(
                    x=float(self.SCREEN_W // 2),
                    y=float(self.SCREEN_H // 2),
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=life,
                    max_life=life,
                    color=color,
                    size=self._rng.randint(2, 4),
                )
            )

    def _update_difficulty(self) -> None:
        """Decrease spawn_interval based on decoded_count."""
        reduction = self.decoded_count // 5
        self.spawn_interval = max(
            self.MIN_SPAWN_INTERVAL,
            self.INITIAL_SPAWN_INTERVAL - reduction * 2,
        )

    def _check_game_over(self) -> bool:
        """Check if heat >= MAX_HEAT. Returns True if game over."""
        if self.heat >= self.MAX_HEAT:
            self.phase = Phase.GAME_OVER
            self._shake_timer = 20
            return True
        return False

    def _get_score_multiplier(self) -> float:
        """1.0 + (combo - 1) * 0.5, capped at 5.0."""
        if self.combo <= 1:
            return 1.0
        return min(5.0, 1.0 + (self.combo - 1) * 0.5)

    def _update_popups(self) -> None:
        self._popup_texts = [
            (text, x, y - 1.5, color, life - 1)
            for text, x, y, color, life in self._popup_texts
            if life > 0
        ]

    # ══════════════════════════════════════════════════
    # Update (pyxel-bound)
    # ══════════════════════════════════════════════════
    def update(self) -> None:
        if self._shake_timer > 0:
            self._shake_timer -= 1

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN):
            self._start_game()
            return
        for key in KEY_TO_COLOR_IDX:
            if pyxel.btnp(key):
                self._start_game()
                return

    def _start_game(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_timer = 0
        self.signals.clear()
        self.particles.clear()
        self.spawn_timer = 0
        self.game_timer = 0
        self.spawn_interval = self.INITIAL_SPAWN_INTERVAL
        self.decoded_count = 0
        self._rng = random.Random()
        self._super_flash = 0
        self._shake_timer = 0
        self._popup_texts.clear()

    def _update_playing(self) -> None:
        self.game_timer += 1

        # Input handling
        for key, color_idx in KEY_TO_COLOR_IDX.items():
            if pyxel.btnp(key):
                earned, was_match, pcol, px, py = self._process_decode_key(color_idx)
                if was_match and earned > 0:
                    self.score += earned
                    if self.combo >= self.COMBO_THRESHOLD and self.super_timer > 0:
                        self._spawn_super_particles()
                        self._popup_texts.append(
                            ("SUPER DECODE!", float(self.SCREEN_W // 2), float(self.SCREEN_H // 2), YELLOW, 45)
                        )
                    else:
                        self._spawn_particles(px, py, pcol, 8)
                        self._popup_texts.append(
                            (f"+{earned}", px, py, pcol, 20)
                        )
                        if self.combo >= 2:
                            combo_y = py - 15
                            self._popup_texts.append(
                                (f"COMBO x{self.combo}", px, combo_y, WHITE, 25)
                            )
                elif px > 0:
                    self._spawn_particles(px, py, GRAY, 6)

        # Spawn signals
        if self.spawn_timer <= 0:
            signal = self._spawn_signal()
            if signal is not None:
                self.signals.append(signal)
            self._update_difficulty()
            self.spawn_timer = self.spawn_interval
        else:
            self.spawn_timer -= 1

        # Update signals
        self._update_signals()

        # Update super
        self._update_super()

        # Update particles
        self._update_particles()

        # Update popups
        self._update_popups()

        # Check game over
        if self._check_game_over():
            return

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()

    # ══════════════════════════════════════════════════
    # Draw
    # ══════════════════════════════════════════════════
    def draw(self) -> None:
        shake_x = 0
        shake_y = 0
        if self._shake_timer > 0:
            shake_x = self._rng.randint(-3, 3)
            shake_y = self._rng.randint(-2, 2)

        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing(shake_x, shake_y)
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over(shake_x, shake_y)

    def _draw_title(self) -> None:
        # Title
        title = "SIGNAL SURGE"
        tx = self.SCREEN_W // 2 - len(title) * 4 // 2
        pyxel.text(tx, 40, title, WHITE)

        # Subtitle
        subtitle = "Decode the signals before they escape!"
        sx = self.SCREEN_W // 2 - len(subtitle) * 4 // 2
        pyxel.text(sx, 58, subtitle, GRAY)

        # Lane preview on right side
        for i in range(LANE_COUNT):
            ly = LANE_CENTER_Y[i] - self.SIGNAL_H // 2
            pyxel.rectb(self.SCREEN_W - 40, ly, self.SIGNAL_W, self.SIGNAL_H, SIGNAL_COLORS[i])
            pyxel.rect(self.SCREEN_W - 39, ly + 1, self.SIGNAL_W - 2, self.SIGNAL_H - 2, SIGNAL_COLORS[i])

        # Key hints
        key_labels = ["Z", "X", "C", "V"]
        color_label_texts = ["RED", "GREEN", "BLUE", "YELLOW"]
        hint_x = 50
        hint_y = 100
        for i in range(LANE_COUNT):
            label = key_labels[i]
            pyxel.text(hint_x, hint_y + i * 20, f"[{label}] = ", WHITE)
            pyxel.text(hint_x + 24, hint_y + i * 20, color_label_texts[i], SIGNAL_COLORS[i])

        # Start prompt
        prompt = "Press any key to start"
        px = self.SCREEN_W // 2 - len(prompt) * 4 // 2
        pyxel.text(px, 210, prompt, WHITE)

    def _draw_playing(self, shake_x: int, shake_y: int) -> None:
        # Lane backgrounds
        for i in range(LANE_COUNT):
            ly = LANE_TOP + i * LANE_H
            pyxel.rect(0 + shake_x, ly + shake_y, self.SCREEN_W, LANE_H, NAVY if i % 2 == 0 else BLACK)
            # Lane divider
            pyxel.line(0 + shake_x, ly + shake_y, self.SCREEN_W + shake_x, ly + shake_y, DARK_BLUE)
        # Bottom divider
        pyxel.line(
            0 + shake_x, LANE_TOP + LANE_COUNT * LANE_H + shake_y,
            self.SCREEN_W + shake_x, LANE_TOP + LANE_COUNT * LANE_H + shake_y,
            DARK_BLUE,
        )

        # Left edge danger zone indicator
        danger_x = 5
        pyxel.rect(danger_x + shake_x, LANE_TOP + shake_y, 2, LANE_COUNT * LANE_H, RED)

        # Signals
        for s in self.signals:
            if not s.active:
                continue
            sx = int(s.x) + shake_x - self.SIGNAL_W // 2
            sy = int(s.y) + shake_y - self.SIGNAL_H // 2

            col = s.color
            if self.super_timer > 0:
                # Rainbow effect during super
                rainbow_colors = [RED, ORANGE, YELLOW, GREEN, LIGHT_BLUE, CYAN]
                col = rainbow_colors[(pyxel.frame_count // 4 + s.color_idx) % len(rainbow_colors)]

            if s.flash_timer > 0:
                col = WHITE

            # Signal body
            pyxel.rect(sx, sy, self.SIGNAL_W, self.SIGNAL_H, col)
            # Border (lighter)
            border_col = WHITE if s.flash_timer > 0 else self._lighter(col)
            pyxel.rectb(sx, sy, self.SIGNAL_W, self.SIGNAL_H, border_col)

            # Inner highlight
            pyxel.rect(sx + 2, sy + 2, self.SIGNAL_W - 4, 3, border_col)

        # Particles
        for p in self.particles:
            alpha = max(0.0, p.life / p.max_life)
            size = max(1, int(p.size * alpha))
            col = p.color if p.life > p.max_life // 2 else GRAY
            px = int(p.x) + shake_x
            py_pos = int(p.y) + shake_y
            pyxel.rect(px, py_pos, size, size, col)

        # Popup texts
        for text, x, y, color, _life in self._popup_texts:
            tx = int(x) + shake_x - len(text) * 2
            ty = int(y) + shake_y
            pyxel.text(tx, ty, text, color)

        # HUD
        self._draw_hud(shake_x, shake_y)

        # Super mode border
        if self.super_timer > 0:
            border_col = self._rainbow_color(pyxel.frame_count // 3)
            pyxel.rectb(0 + shake_x, 0 + shake_y, self.SCREEN_W, self.SCREEN_H, border_col)
            pyxel.rectb(1 + shake_x, 1 + shake_y, self.SCREEN_W - 2, self.SCREEN_H - 2, border_col)

            # "SUPER DECODE" text
            remain = self.super_timer // FPS + 1
            super_display = f"SUPER DECODE {remain}s"
            sdx = self.SCREEN_W // 2 - len(super_display) * 4 // 2 + shake_x
            pyxel.text(sdx, 4 + shake_y, super_display, YELLOW)

    def _draw_hud(self, shake_x: int, shake_y: int) -> None:
        # Score
        pyxel.text(4 + shake_x, 4 + shake_y, f"SCORE: {self.score}", WHITE)

        # Combo (large, center-right)
        if self.combo >= 2:
            combo_text = f"COMBO x{self.combo}"
            cx = self.SCREEN_W - len(combo_text) * 4 - 10 + shake_x
            combo_col = WHITE
            if self.combo >= self.COMBO_THRESHOLD:
                combo_col = YELLOW
            elif self.combo >= 3:
                combo_col = ORANGE
            pyxel.text(cx, 4 + shake_y, combo_text, combo_col)

        # Heat bar (top of screen)
        bar_x = 4 + shake_x
        bar_y = 14 + shake_y
        bar_w = self.SCREEN_W - 8
        bar_h = 6

        # Background
        pyxel.rect(bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2, BLACK)
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, DARK_BLUE)

        # Fill
        heat_pct = min(1.0, self.heat / self.MAX_HEAT)
        fill_w = int(bar_w * heat_pct)
        if fill_w > 0:
            if heat_pct < 0.5:
                heat_col = GREEN
            elif heat_pct < 0.8:
                heat_col = ORANGE
            else:
                heat_col = RED
            pyxel.rect(bar_x, bar_y, fill_w, bar_h, heat_col)

        # Heat label
        pyxel.text(bar_x, bar_y + bar_h + 2, f"HEAT {int(self.heat)}/{self.MAX_HEAT}", GRAY)

        # Max combo
        pyxel.text(4 + shake_x, bar_y + bar_h + 12 + shake_y, f"MAX COMBO: {self.max_combo}", GRAY)

        # Speed indicator
        speed_text = f"SPD: {self._current_speed():.1f}"
        pyxel.text(self.SCREEN_W - 50 + shake_x, bar_y + bar_h + 12 + shake_y, speed_text, GRAY)

    def _draw_game_over(self, shake_x: int, shake_y: int) -> None:
        # Title
        title = "SIGNAL OVERLOAD"
        tx = self.SCREEN_W // 2 - len(title) * 4 // 2 + shake_x
        pyxel.text(tx, 50 + shake_y, title, RED)

        # Stats
        score_text = f"FINAL SCORE: {self.score}"
        sx = self.SCREEN_W // 2 - len(score_text) * 4 // 2 + shake_x
        pyxel.text(sx, 80 + shake_y, score_text, WHITE)

        combo_text = f"MAX COMBO: {self.max_combo}"
        cx = self.SCREEN_W // 2 - len(combo_text) * 4 // 2 + shake_x
        pyxel.text(cx, 100 + shake_y, combo_text, WHITE)

        decoded_text = f"SIGNALS DECODED: {self.decoded_count}"
        dx = self.SCREEN_W // 2 - len(decoded_text) * 4 // 2 + shake_x
        pyxel.text(dx, 120 + shake_y, decoded_text, GRAY)

        # Super triggered?
        if self.max_combo >= self.COMBO_THRESHOLD:
            super_msg = "SUPER DECODE ACTIVATED!"
            smx = self.SCREEN_W // 2 - len(super_msg) * 4 // 2 + shake_x
            pyxel.text(smx, 140 + shake_y, super_msg, YELLOW)

        # Retry prompt
        retry = "Press ENTER to retry"
        rx = self.SCREEN_W // 2 - len(retry) * 4 // 2 + shake_x
        pyxel.text(rx, 190 + shake_y, retry, WHITE)

    # ══════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════
    @staticmethod
    def _lighter(color: int) -> int:
        """Return a lighter variant of a color."""
        if color == RED:
            return ORANGE
        if color == GREEN:
            return LIME
        if color == LIGHT_BLUE:
            return CYAN
        if color == YELLOW:
            return PEACH
        if color == ORANGE:
            return YELLOW
        return WHITE

    @staticmethod
    def _rainbow_color(offset: int) -> int:
        colors = [RED, ORANGE, YELLOW, GREEN, LIGHT_BLUE, PURPLE, PINK]
        return colors[offset % len(colors)]


if __name__ == "__main__":
    Game()
