"""PULSE REACTOR — Rhythm/Timing game.

Core fun moment: hitting same-colored beats in rhythm to build a COMBO
chain, then discharging the OVERLOAD for a huge score bomb.

Colored beats travel from 4 screen edges toward the center reactor.
Press the corresponding arrow key when a beat enters the strike zone.
Same-color consecutive hits build COMBO → SYNTHESIS multiplier.
COMBO >= 8 triggers OVERLOAD → HP drain → press SPACE to DISCHARGE.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import pyxel

# ── Constants ──────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
DISPLAY_SCALE = 2
FPS = 60

CENTER_X = SCREEN_W // 2
CENTER_Y = SCREEN_H // 2

# Strike zone radii from reactor center
STRIKE_RADIUS = 42      # outer ring — beat must be inside this to hit
PERFECT_RADIUS = 20     # inner zone — “perfect” hit timing
MISS_RADIUS = 6         # beat passed this far → missed

# Gameplay
OVERLOAD_THRESHOLD = 8
MAX_HP = 10
GAME_TIME_SEC = 60
GAME_TIME_FRAMES = GAME_TIME_SEC * FPS  # 3600
OVERLOAD_DRAIN_INTERVAL = 60  # frames between overload HP drains

# Beat colours — indexes into BEAT_COLORS
NUM_BEAT_COLORS = 4
BEAT_COLORS: tuple[int, int, int, int] = (
    pyxel.COLOR_RED,     # 0
    pyxel.COLOR_GREEN,   # 1
    pyxel.COLOR_YELLOW,  # 2
    pyxel.COLOR_CYAN,    # 3
)
BEAT_COLOR_NAMES: tuple[str, str, str, str] = (
    "RED", "GREEN", "YELLOW", "CYAN",
)

# Difficulty
SPEED_INITIAL = 1.2
SPEED_STEP = 0.35          # + per 10 seconds
SPEED_INTERVAL_SEC = 10
SPAWN_RATE_INITIAL = 55    # frames between spawns
SPAWN_RATE_STEP = 10       # - per 15 seconds
SPAWN_RATE_INTERVAL_SEC = 15
SPAWN_RATE_MIN = 15

# Colours available unlocked over time
# 0s: 2 colours → 15s: 3 colours → 30s: 4 colours
COLOR_UNLOCK_SCHEDULE: tuple[tuple[int, int], ...] = (
    (0, 2),   # 0 s  → 2 colours
    (15, 3),  # 15s  → 3 colours
    (30, 4),  # 30s  → 4 colours
)

# Font
FONT_PATH = Path(__file__).with_name("k8x12.bdf")
FONT_W = 8
FONT_H = 12


# ── Phase Enum ─────────────────────────────────────────────────────────

class Phase(IntEnum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


# ── Data Classes ───────────────────────────────────────────────────────

@dataclass
class Beat:
    """A coloured beat travelling from a screen edge toward the reactor centre."""
    x: float
    y: float
    direction: int  # 0=up(↑), 1=down(↓), 2=left(←), 3=right(→)
    color: int      # index into BEAT_COLORS
    speed: float    # px/frame
    alive: bool = True

    @property
    def color_val(self) -> int:
        return BEAT_COLORS[self.color]

    @property
    def color_name(self) -> str:
        return BEAT_COLOR_NAMES[self.color]

    def dist_to_center(self) -> float:
        return math.hypot(self.x - CENTER_X, self.y - CENTER_Y)


@dataclass
class Particle:
    """Visual particle for hit / discharge effects."""
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class FloatingText:
    """Floating score / feedback text."""
    x: float
    y: float
    text: str
    life: int
    color: int


# ── Game Class ─────────────────────────────────────────────────────────

class Game:
    """PULSE REACTOR — rhythm/timing reactor-control game."""

    def __init__(self) -> None:
        pyxel.init(
            SCREEN_W, SCREEN_H,
            title="PULSE REACTOR",
            display_scale=DISPLAY_SCALE,
            fps=FPS,
        )
        self.font = pyxel.Font(str(FONT_PATH))
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── State initialisation ────────────────────────────────────────

    def reset(self) -> None:
        """Reset / initialise all game state.

        Callable headless via ``Game.__new__(Game).reset()``.
        """
        self._rng = random.Random()
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.current_color: int | None = None  # colour of current combo
        self.hp: int = MAX_HP
        self.timer: int = GAME_TIME_FRAMES
        self.synthesis_multiplier: float = 1.0
        self.overload: bool = False  # overload state active
        self._overload_drain_timer: int = OVERLOAD_DRAIN_INTERVAL
        self.beats: list[Beat] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._shake_frames: int = 0
        self._spawn_cooldown: int = SPAWN_RATE_INITIAL
        self._frame: int = 0

    # ── Derived properties ──────────────────────────────────────────

    @property
    def time_left_sec(self) -> float:
        return self.timer / FPS

    @property
    def elapsed_sec(self) -> float:
        return GAME_TIME_SEC - self.time_left_sec

    @property
    def available_colors(self) -> int:
        """How many beat colours are currently unlocked."""
        n = 2
        for threshold, count in COLOR_UNLOCK_SCHEDULE:
            if self.elapsed_sec >= threshold:
                n = count
        return n

    @property
    def beat_speed(self) -> float:
        """Current beat speed (increases every 10 seconds)."""
        boost = int(self.elapsed_sec // SPEED_INTERVAL_SEC)
        return SPEED_INITIAL + boost * SPEED_STEP

    @property
    def spawn_interval(self) -> int:
        """Frames between beat spawns (decreases every 15 seconds)."""
        reduction = int(self.elapsed_sec // SPAWN_RATE_INTERVAL_SEC)
        return max(SPAWN_RATE_MIN, SPAWN_RATE_INITIAL - reduction * SPAWN_RATE_STEP)

    # ── Input helpers (pyxel-dependent — keep in these methods only) ──

    @staticmethod
    def _read_arrow() -> int | None:
        """Read a single arrow-key press. Returns direction 0–3 or None."""
        if pyxel.btnp(pyxel.KEY_UP):
            return 0
        if pyxel.btnp(pyxel.KEY_DOWN):
            return 1
        if pyxel.btnp(pyxel.KEY_LEFT):
            return 2
        if pyxel.btnp(pyxel.KEY_RIGHT):
            return 3
        return None

    @staticmethod
    def _read_discharge() -> bool:
        return pyxel.btnp(pyxel.KEY_SPACE)

    @staticmethod
    def _read_confirm() -> bool:
        return pyxel.btnp(pyxel.KEY_RETURN)

    # ── Update ──────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if self._read_confirm():
                self.reset()
                self.phase = Phase.PLAYING
            return

        if self.phase == Phase.GAME_OVER:
            if self._read_confirm():
                self.reset()
                self.phase = Phase.PLAYING
            return

        # ────── PLAYING ──────
        self._frame += 1

        # Timer countdown
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self.phase = Phase.GAME_OVER
            return

        # Collect input (pyxel-dependent — only here)
        arrow = self._read_arrow()
        space = self._read_discharge()

        # Dispatch to pure-logic methods
        self._spawn_beat()
        self._update_beats()
        self._check_misses()
        if arrow is not None:
            self._check_hit(arrow)
        if space:
            self._discharge()
        self._update_overload()
        self._update_particles()
        self._update_floating_texts()

        # Screen-shake decay
        if self._shake_frames > 0:
            self._shake_frames -= 1

    # ── Pure-logic methods (testable, no pyxel.* calls) ─────────────

    def _spawn_beat(self) -> None:
        """Try to spawn a new beat on cooldown (seeded RNG)."""
        self._spawn_cooldown -= 1
        if self._spawn_cooldown > 0:
            return

        direction = self._rng.randint(0, 3)
        color_idx = self._rng.randint(0, self.available_colors - 1)
        speed = self.beat_speed

        # Spawn at the edge that matches the direction.
        # Direction = arrow key to stop it → beat comes from opposite side.
        if direction == 0:       # ↑ — beat comes from bottom
            x = float(self._rng.randint(40, SCREEN_W - 40))
            y = float(SCREEN_H + 8)
        elif direction == 1:     # ↓ — beat comes from top
            x = float(self._rng.randint(40, SCREEN_W - 40))
            y = -8.0
        elif direction == 2:     # ← — beat comes from right
            x = float(SCREEN_W + 8)
            y = float(self._rng.randint(40, SCREEN_H - 40))
        else:                    # → — beat comes from left
            x = -8.0
            y = float(self._rng.randint(40, SCREEN_H - 40))

        self.beats.append(
            Beat(x=x, y=y, direction=direction, color=color_idx, speed=speed)
        )

        # Set next cooldown with jitter
        base = self.spawn_interval
        self._spawn_cooldown = self._rng.randint(max(8, base - 12), base + 12)

    def _update_beats(self) -> None:
        """Move all beats toward the reactor centre. Remove dead / far-off beats."""
        for beat in self.beats[:]:
            if not beat.alive:
                self.beats.remove(beat)
                continue

            dx = CENTER_X - beat.x
            dy = CENTER_Y - beat.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                beat.x += (dx / dist) * beat.speed
                beat.y += (dy / dist) * beat.speed

            # Cull if far off-screen (safety net)
            if (
                beat.x < -60
                or beat.x > SCREEN_W + 60
                or beat.y < -60
                or beat.y > SCREEN_H + 60
            ):
                beat.alive = False

    def _check_misses(self) -> None:
        """Mark beats that passed the reactor as missed (HP-1, combo reset)."""
        for beat in self.beats:
            if not beat.alive:
                continue
            if beat.dist_to_center() <= MISS_RADIUS:
                beat.alive = False
                self.combo = 0
                self.current_color = None
                self.overload = False
                self._overload_drain_timer = OVERLOAD_DRAIN_INTERVAL
                self.hp -= 1
                self._spawn_particles(
                    beat.x, beat.y, pyxel.COLOR_RED, count=6
                )
                self._spawn_floating_text(
                    beat.x, beat.y, "MISS", pyxel.COLOR_RED
                )
                if self.hp <= 0:
                    self.hp = 0
                    self.phase = Phase.GAME_OVER
                    self._spawn_particles(
                        CENTER_X, CENTER_Y, pyxel.COLOR_ORANGE, 30
                    )

    def _check_hit(self, direction: int) -> None:
        """Check if a beat in the strike zone matches *direction*.

        On hit: score, combo update, particles, floating text.
        Wrong colour: HP-1, combo break.
        """
        # Find closest alive beat with matching direction inside strike zone
        best: tuple[float, Beat] | None = None
        for beat in self.beats:
            if not beat.alive or beat.direction != direction:
                continue
            d = beat.dist_to_center()
            if d <= STRIKE_RADIUS:
                if best is None or d < best[0]:
                    best = (d, beat)

        if best is None:
            return  # no valid beat to hit

        dist, beat = best
        beat.alive = False
        color_idx = beat.color

        # ── Colour mismatch → penalty ──
        if self.current_color is not None and color_idx != self.current_color:
            self.combo = 0
            self.current_color = None
            self.overload = False
            self._overload_drain_timer = OVERLOAD_DRAIN_INTERVAL
            self.hp -= 1
            self._spawn_particles(beat.x, beat.y, pyxel.COLOR_RED, 8)
            self._spawn_floating_text(beat.x, beat.y, "WRONG", pyxel.COLOR_RED)
            if self.hp <= 0:
                self.hp = 0
                self.phase = Phase.GAME_OVER
                self._spawn_particles(
                    CENTER_X, CENTER_Y, pyxel.COLOR_ORANGE, 30
                )
            return

        # ── Colour match → combo & score ──
        self.current_color = color_idx
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        self.synthesis_multiplier = 1.0 + self.combo * 0.25

        is_perfect = dist <= PERFECT_RADIUS
        base = 100 if is_perfect else 50
        points = int(base * self.synthesis_multiplier)
        self.score += points

        # Feedback
        label = "PERFECT!" if is_perfect else "HIT"
        label_col = pyxel.COLOR_YELLOW if is_perfect else pyxel.COLOR_WHITE
        self._spawn_particles(beat.x, beat.y, beat.color_val, 6)
        self._spawn_floating_text(
            beat.x, beat.y, f"{label} +{points}", label_col
        )

        # Overload gate
        self.overload = self.combo >= OVERLOAD_THRESHOLD

    def _update_combo(self) -> None:
        """Public hook for combo-state introspection (no mutation needed)."""
        pass

    def _update_overload(self) -> None:
        """Drain HP periodically while overload is active."""
        if not self.overload:
            self._overload_drain_timer = OVERLOAD_DRAIN_INTERVAL
            return

        self._overload_drain_timer -= 1
        if self._overload_drain_timer <= 0:
            self._overload_drain_timer = OVERLOAD_DRAIN_INTERVAL
            self.hp -= 1
            self._spawn_floating_text(
                CENTER_X, CENTER_Y - 16, "OVERLOAD", pyxel.COLOR_RED
            )
            self._spawn_particles(CENTER_X, CENTER_Y, pyxel.COLOR_RED, 4)
            if self.hp <= 0:
                self.hp = 0
                self.phase = Phase.GAME_OVER
                self._spawn_particles(
                    CENTER_X, CENTER_Y, pyxel.COLOR_ORANGE, 30
                )

    def _discharge(self) -> None:
        """Discharge overload: score bonus, screen shake, reset overload."""
        if not self.overload:
            return

        bonus = self.combo * 200
        self.score += bonus
        self._spawn_particles(CENTER_X, CENTER_Y, pyxel.COLOR_YELLOW, 22)
        self._spawn_floating_text(
            CENTER_X, CENTER_Y - 16,
            f"DISCHARGE! +{bonus}",
            pyxel.COLOR_YELLOW,
        )
        self._shake_frames = 16

        # Reset overload state
        self.overload = False
        self._overload_drain_timer = OVERLOAD_DRAIN_INTERVAL

    # ── Effects ─────────────────────────────────────────────────────

    def _spawn_particles(
        self, x: float, y: float, color: int, count: int
    ) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            spd = self._rng.uniform(0.6, 3.0)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * spd,
                    vy=math.sin(angle) * spd,
                    life=18 + self._rng.randint(0, 12),
                    color=color,
                )
            )

    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=35, color=color)
        )

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y -= 0.6
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    # ── Text helpers ────────────────────────────────────────────────

    def _text(self, x: int, y: int, s: str, col: int) -> None:
        """Draw text using the shared BDF font."""
        pyxel.text(x, y, s, col, self.font)

    def _text_center(self, cx: int, y: int, s: str, col: int) -> None:
        self._text(cx - self._text_width(s) // 2, y, s, col)

    @staticmethod
    def _text_width(s: str) -> int:
        return len(s) * FONT_W

    # ── Draw ────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        # Screen-shake offset
        sx = 0
        sy = 0
        if self._shake_frames > 0:
            sx = self._rng.randint(-4, 4)
            sy = self._rng.randint(-4, 4)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        # Background
        self._draw_background(sx, sy)

        # Strike zone ring
        self._draw_strike_zone(sx, sy)

        # Beats
        self._draw_beats(sx, sy)

        # Reactor core
        self._draw_reactor(sx, sy)

        # Particles
        self._draw_particles(sx, sy)

        # Floating texts
        self._draw_floating_texts(sx, sy)

        # HUD
        self._draw_hud()

        # Game-over overlay
        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    # ── Screen drawing ──────────────────────────────────────────────

    def _draw_title(self) -> None:
        """Title screen."""
        cx = SCREEN_W // 2
        self._text_center(cx, 50, "PULSE REACTOR", pyxel.COLOR_YELLOW)

        y = 90
        self._text_center(cx, y,     "ARR KEYS: Hit beats", pyxel.COLOR_GRAY)
        y += 16
        self._text_center(cx, y,     "SPACE: Discharge Overload", pyxel.COLOR_GRAY)
        y += 16
        self._text_center(cx, y,     "Same color hits = COMBO", pyxel.COLOR_GREEN)
        y += 16
        self._text_center(cx, y,     "Wrong color = HP-1", pyxel.COLOR_RED)
        y += 16
        self._text_center(cx, y,     "8+ COMBO = OVERLOAD (HP drain)", pyxel.COLOR_RED)
        y += 16
        self._text_center(cx, y,     "Discharge for bonus!", pyxel.COLOR_YELLOW)

        y += 28
        if (pyxel.frame_count // 30) % 2 == 0:
            self._text_center(cx, y, "PRESS ENTER", pyxel.COLOR_WHITE)

    def _draw_background(self, sx: int, sy: int) -> None:
        """Dark control-room background with subtle grid."""
        # Control-room panels
        for i in range(4):
            bx = 6 + i * 80 + sx
            by = 6 + sy
            pyxel.rectb(bx, by, 74, 20, pyxel.COLOR_NAVY)
        for i in range(4):
            bx = 6 + i * 80 + sx
            by = SCREEN_H - 26 + sy
            pyxel.rectb(bx, by, 74, 20, pyxel.COLOR_NAVY)

        # Grid lines on floor
        for x in range(0, SCREEN_W, 32):
            pyxel.line(x + sx, 0 + sy, x + sx, SCREEN_H + sy, pyxel.COLOR_NAVY)
        for y in range(0, SCREEN_H, 32):
            pyxel.line(0 + sx, y + sy, SCREEN_W + sx, y + sy, pyxel.COLOR_NAVY)

        # Reactor platform
        pyxel.circ(CENTER_X + sx, CENTER_Y + sy, 58, pyxel.COLOR_NAVY)
        pyxel.circb(CENTER_X + sx, CENTER_Y + sy, 58, pyxel.COLOR_DARK_BLUE)

    def _draw_strike_zone(self, sx: int, sy: int) -> None:
        """Draw the strike-zone ring around the reactor."""
        cx = CENTER_X + sx
        cy = CENTER_Y + sy

        # Outer ring (strike zone boundary)
        ring_col = pyxel.COLOR_RED if self.overload else pyxel.COLOR_GRAY
        pyxel.circb(cx, cy, STRIKE_RADIUS, ring_col)

        # Perfect zone ring (dashed — every other pixel)
        for angle in range(0, 360, 12):
            rad = math.radians(angle)
            px = int(cx + PERFECT_RADIUS * math.cos(rad))
            py = int(cy + PERFECT_RADIUS * math.sin(rad))
            if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
                pyxel.pset(px, py, pyxel.COLOR_GRAY)

    def _draw_beats(self, sx: int, sy: int) -> None:
        """Draw all alive beats."""
        for beat in self.beats:
            if not beat.alive:
                continue
            bx = int(beat.x) + sx
            by = int(beat.y) + sy
            # Beat body: small diamond/triangle pointing toward center
            color = beat.color_val

            # Direction arrow shape
            if beat.direction == 0:   # ↑ — triangle pointing up
                pyxel.tri(bx, by - 5, bx - 4, by + 3, bx + 4, by + 3, color)
            elif beat.direction == 1: # ↓ — triangle pointing down
                pyxel.tri(bx, by + 5, bx - 4, by - 3, bx + 4, by - 3, color)
            elif beat.direction == 2: # ← — triangle pointing left
                pyxel.tri(bx - 5, by, bx + 3, by - 4, bx + 3, by + 4, color)
            else:                     # → — triangle pointing right
                pyxel.tri(bx + 5, by, bx - 3, by - 4, bx - 3, by + 4, color)

    def _draw_reactor(self, sx: int, sy: int) -> None:
        """Draw the centre reactor core."""
        cx = CENTER_X + sx
        cy = CENTER_Y + sy

        # Core pulsation based on combo
        pulse = 1
        if self.combo > 0:
            pulse = int(3 + self.combo * 0.4)

        # Outer glow
        if self.combo > 0:
            glow_col = (
                pyxel.COLOR_RED
                if self.overload
                else BEAT_COLORS[self.current_color % NUM_BEAT_COLORS]
                if self.current_color is not None
                else pyxel.COLOR_WHITE
            )
            pyxel.circ(cx, cy, 12 + pulse, glow_col)

        # Core body
        core_col = pyxel.COLOR_RED if self.overload else pyxel.COLOR_ORANGE
        pyxel.circ(cx, cy, 8, core_col)

        # Inner highlight
        if self.overload:
            # Flash
            flash = (pyxel.frame_count // 8) % 2
            inner = pyxel.COLOR_WHITE if flash else pyxel.COLOR_YELLOW
        else:
            inner = pyxel.COLOR_YELLOW
        pyxel.circ(cx, cy, 4, inner)

        # Combo ring
        if self.combo >= 2:
            pyxel.circb(cx, cy, 16 + pulse, pyxel.COLOR_YELLOW)

    def _draw_particles(self, sx: int, sy: int) -> None:
        for p in self.particles:
            px = int(p.x) + sx
            py = int(p.y) + sy
            if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
                pyxel.pset(px, py, p.color)

    def _draw_floating_texts(self, sx: int, sy: int) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 35.0
            if alpha > 0.15:
                self._text(
                    int(ft.x) + sx - self._text_width(ft.text) // 2,
                    int(ft.y) + sy,
                    ft.text,
                    ft.color,
                )

    def _draw_hud(self) -> None:
        """Score (top-left), combo (top-centre), HP (top-right), timer (bottom)."""
        # Top bar background
        pyxel.rect(0, 0, SCREEN_W, FONT_H + 2, pyxel.COLOR_NAVY)

        # Score — left
        self._text(4, 2, f"SCORE:{self.score:>7d}", pyxel.COLOR_WHITE)

        # Combo — centre
        combo_str = f"COMBO:x{self.combo}"
        combo_col = pyxel.COLOR_YELLOW
        if self.combo >= OVERLOAD_THRESHOLD:
            combo_col = pyxel.COLOR_RED
        elif self.combo >= 4:
            combo_col = pyxel.COLOR_ORANGE
        self._text_center(SCREEN_W // 2, 2, combo_str, combo_col)

        # Multiplier
        if self.combo > 0:
            mult_str = f" (x{self.synthesis_multiplier:.1f})"
            self._text(
                SCREEN_W // 2 + self._text_width(combo_str) // 2 + 4,
                2,
                mult_str,
                pyxel.COLOR_LIME,
            )

        # HP — top-right
        hp_label = "HP:"
        label_w = self._text_width(hp_label)
        self._text(SCREEN_W - label_w - self._text_width("10") - 4, 2, hp_label, pyxel.COLOR_WHITE)
        for i in range(MAX_HP):
            hx = SCREEN_W - (MAX_HP - i) * 7 - 2
            if i < self.hp:
                pyxel.rect(hx, 3, 5, 7, pyxel.COLOR_RED)
            else:
                pyxel.rectb(hx, 3, 5, 7, pyxel.COLOR_GRAY)

        # Overload indicator
        if self.overload:
            flash = (pyxel.frame_count // 16) % 2
            if flash:
                self._text_center(
                    SCREEN_W // 2, FONT_H + 5,
                    "OVERLOAD! PRESS SPACE TO DISCHARGE",
                    pyxel.COLOR_RED,
                )

        # Bottom bar
        pyxel.rect(0, SCREEN_H - FONT_H - 4, SCREEN_W, FONT_H + 4, pyxel.COLOR_NAVY)

        # Timer — bottom centre
        secs = max(0, int(self.time_left_sec))
        t_color = pyxel.COLOR_RED if secs <= 10 else pyxel.COLOR_WHITE
        timer_str = f"TIME: {secs:>2d}s"
        self._text_center(SCREEN_W // 2, SCREEN_H - FONT_H - 2, timer_str, t_color)

        # Current combo colour — bottom-left
        if self.current_color is not None:
            cc = BEAT_COLORS[self.current_color]
            pyxel.rect(4, SCREEN_H - FONT_H - 2, 14, FONT_H, cc)
            self._text(22, SCREEN_H - FONT_H - 2, BEAT_COLOR_NAMES[self.current_color], cc)

    def _draw_game_over(self) -> None:
        """Game-over overlay."""
        # Dim overlay
        pyxel.rect(SCREEN_W // 2 - 90, SCREEN_H // 2 - 55, 180, 110, pyxel.COLOR_BLACK)
        pyxel.rectb(SCREEN_W // 2 - 90, SCREEN_H // 2 - 55, 180, 110, pyxel.COLOR_WHITE)

        cx = SCREEN_W // 2
        cy = SCREEN_H // 2
        self._text_center(cx, cy - 46, "GAME OVER", pyxel.COLOR_RED)
        self._text_center(cx, cy - 22, f"SCORE: {self.score}", pyxel.COLOR_WHITE)
        self._text_center(
            cx, cy - 6, f"MAX COMBO: {self.max_combo}", pyxel.COLOR_YELLOW
        )
        self._text_center(cx, cy + 18, "PRESS ENTER TO RETRY", pyxel.COLOR_WHITE)


# ── Entry point ────────────────────────────────────────────────────────

def main() -> None:
    Game()


if __name__ == "__main__":
    main()
