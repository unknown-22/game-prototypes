"""BATTER CHAIN — Baseball Batting Game Prototype

Face a pitcher throwing colored balls. Time your swing with mouse click.
Same color = COMBO. 3 combo = SUPER HOME RUN!
Different color = FOUL (combo reset). Miss = STRIKE.
3 strikes or 10 pitches = GAME OVER.

"Most Fun Moment":
  「ピッチャーの投げる色を見極め、ギリギリまで引きつけて
    同色COMBOを決め、SUPER HITでホームランをかっ飛ばす瞬間」

Risk/Reward:
  - Wait for same-color pitch → COMBO multiplier (high score) but risk strikes
  - Swing at any pitch → safe from strikes but lower score
  - Close to plate timing → higher score bonus
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto

import pyxel

# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

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

SCREEN_W = 320
SCREEN_H = 240

COMBO_COLORS: list[int] = [RED, GREEN, NAVY, YELLOW]
COMBO_COLOR_NAMES: list[str] = ["RED", "GREEN", "BLUE", "YELLOW"]

TOTAL_PITCHES = 10
MAX_STRIKES = 3
SUPER_HIT_THRESHOLD = 3

# Strike zone rectangle
SZ_LEFT = 200
SZ_TOP = 100
SZ_W = 60
SZ_H = 60
SZ_RIGHT = SZ_LEFT + SZ_W
SZ_BOTTOM = SZ_TOP + SZ_H
SZ_CX = SZ_LEFT + SZ_W / 2
SZ_CY = SZ_TOP + SZ_H / 2

# Positions
PITCHER_X = 40
PITCHER_Y = 110
BATTER_X = 240
BATTER_Y = 180

# Timing (frames)
WINDUP_FRAMES = 60
RESULT_FRAMES = 30
SWING_FRAMES = 6
HIT_FLASH_FRAMES = 3
SUPER_SHAKE_FRAMES = 10

# Speeds
BASE_PITCH_SPEED = 3.0
SPEED_INCREMENT = 0.15
TRAIL_INTERVAL = 3
TRAIL_MAX = 8

# Hit zone — ball is hittable when near the strike zone
HIT_ZONE_X_MIN = SZ_LEFT - 10
HIT_ZONE_X_MAX = SZ_RIGHT + 10
HIT_ZONE_Y_MIN = SZ_TOP - 10
HIT_ZONE_Y_MAX = SZ_BOTTOM + 10


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

class Phase(Enum):
    TITLE = auto()
    WINDUP = auto()
    PITCH = auto()
    RESULT = auto()
    GAME_OVER = auto()


# ═══════════════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Pitch:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    active: bool = True
    trail: list[tuple[float, float]] = field(default_factory=list)


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


# ═══════════════════════════════════════════════════════════════════════════════
# Game Class
# ═══════════════════════════════════════════════════════════════════════════════

class Game:
    # ── State attributes (all pre-init for headless tests via __new__) ─────

    phase: Phase
    score: int
    high_score: int
    combo: int
    max_combo: int
    combo_color: int
    strikes: int
    pitch_count: int
    total_pitches: int
    pitch_speed: float
    pitch_timer: int
    current_pitch: Pitch | None
    particles: list[Particle]
    floating_texts: list[FloatingText]
    hit_flash: int
    shake_frames: int
    swing_anim: int
    result_timer: int
    last_result: str
    last_score: int
    rng: random.Random
    pitch_speeds: list[float]
    windup_timer: int

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="BATTER CHAIN")
        self._init_sounds()
        self.high_score = 0
        self.rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def _init_sounds(self) -> None:
        try:
            pyxel.sounds[0].set("c3e3g3", "s", "7", "n", 15)
            pyxel.sounds[1].set("c2", "s", "7", "n", 15)
            pyxel.sounds[2].set("c4e4g4c5", "s", "7", "n", 20)
            pyxel.sounds[3].set("d2", "s", "7", "n", 10)
            pyxel.sounds[4].set("g2e2c2", "s", "7", "n", 30)
        except BaseException:
            pass

    # ── Reset ──────────────────────────────────────────────────────────────

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.combo_color = -1
        self.strikes = 0
        self.pitch_count = 0
        self.total_pitches = TOTAL_PITCHES
        self.pitch_speed = BASE_PITCH_SPEED
        self.pitch_timer = 0
        self.current_pitch = None
        self.particles = []
        self.floating_texts = []
        self.hit_flash = 0
        self.shake_frames = 0
        self.swing_anim = 0
        self.result_timer = 0
        self.last_result = ""
        self.last_score = 0
        self.windup_timer = 0
        self.pitch_speeds = [
            BASE_PITCH_SPEED + SPEED_INCREMENT * i
            for i in range(TOTAL_PITCHES)
        ]

    # ═══════════════════════════════════════════════════════════════════════════
    # Update
    # ═══════════════════════════════════════════════════════════════════════════

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.WINDUP:
            self._update_windup()
        elif self.phase == Phase.PITCH:
            self._update_pitch_phase()
        elif self.phase == Phase.RESULT:
            self._update_result()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

        self._update_particles()
        self._update_floating_texts()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_RETURN):
            self.phase = Phase.WINDUP
            self.windup_timer = WINDUP_FRAMES

    def _update_windup(self) -> None:
        self.windup_timer -= 1
        if self.windup_timer <= 0:
            self._throw_pitch()
            self.phase = Phase.PITCH

    def _update_pitch_phase(self) -> None:
        # Handle swing input
        swing_pressed = (
            pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and self.swing_anim == 0
        )
        if swing_pressed and self.current_pitch is not None:
            if self._try_swing():
                self._resolve_hit()
            else:
                self._resolve_miss()
            self.phase = Phase.RESULT
            self.result_timer = RESULT_FRAMES
            return

        # Move pitch
        if self.current_pitch is not None and self.current_pitch.active:
            self._update_pitch()

    def _update_result(self) -> None:
        self.result_timer -= 1
        if self.swing_anim > 0:
            self.swing_anim -= 1
        if self.hit_flash > 0:
            self.hit_flash -= 1
        if self.shake_frames > 0:
            self.shake_frames -= 1

        if self.result_timer <= 0:
            if self._check_game_over():
                self.phase = Phase.GAME_OVER
                if self.score > self.high_score:
                    self.high_score = self.score
                try:
                    pyxel.play(3, 4)
                except BaseException:
                    pass
            else:
                self.current_pitch = None
                self.swing_anim = 0
                self.hit_flash = 0
                self.shake_frames = 0
                self.phase = Phase.WINDUP
                self.windup_timer = WINDUP_FRAMES

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.WINDUP
            self.windup_timer = WINDUP_FRAMES

    # ═══════════════════════════════════════════════════════════════════════════
    # Core Logic (testable — no pyxel input calls)
    # ═══════════════════════════════════════════════════════════════════════════

    def _throw_pitch(self) -> None:
        color_idx = self.rng.randint(0, len(COMBO_COLORS) - 1)
        color = COMBO_COLORS[color_idx]

        target_y = SZ_CY + self.rng.uniform(-20, 20)
        target_y = max(SZ_TOP + 5, min(SZ_BOTTOM - 5, target_y))

        idx = min(self.pitch_count, TOTAL_PITCHES - 1)
        speed = self.pitch_speeds[idx]

        dx = SZ_CX - PITCHER_X
        dy = target_y - PITCHER_Y
        dist = (dx * dx + dy * dy) ** 0.5
        if dist > 0:
            vx = speed * dx / dist
            vy = speed * dy / dist
        else:
            vx = speed
            vy = 0.0

        self.current_pitch = Pitch(
            x=float(PITCHER_X),
            y=float(PITCHER_Y),
            vx=vx,
            vy=vy,
            color=color,
        )

    def _update_pitch(self) -> None:
        p = self.current_pitch
        if p is None:
            return

        # Trail
        if pyxel.frame_count % TRAIL_INTERVAL == 0:
            p.trail.append((p.x, p.y))
            if len(p.trail) > TRAIL_MAX:
                p.trail.pop(0)

        # Move ball
        p.x += p.vx
        p.y += p.vy

        # Ball passed plate?
        if p.x > SZ_RIGHT + 20:
            p.active = False
            self._on_pitch_passed()

    def _try_swing(self) -> bool:
        p = self.current_pitch
        if p is None:
            return False
        return (
            HIT_ZONE_X_MIN <= p.x <= HIT_ZONE_X_MAX
            and HIT_ZONE_Y_MIN <= p.y <= HIT_ZONE_Y_MAX
        )

    def _resolve_hit(self) -> None:
        p = self.current_pitch
        if p is None:
            return

        pitch_color = p.color
        self.pitch_count += 1
        self.swing_anim = SWING_FRAMES

        # Timing bonus: closer to strike zone center = better
        dx = p.x - SZ_CX
        dy = p.y - SZ_CY
        dist = (dx * dx + dy * dy) ** 0.5
        max_dist = ((SZ_W / 2) ** 2 + (SZ_H / 2) ** 2) ** 0.5
        timing_bonus = max(0.0, 1.0 - dist / max_dist)

        is_combo = self.combo_color == pitch_color and self.combo > 0

        if is_combo:
            # Same color — COMBO!
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo

            base_score = 100 * self.combo
            self.last_score = int(base_score * (1.0 + timing_bonus * 0.5))
            self.score += self.last_score

            self._spawn_hit_particles(p.x, p.y, pitch_color)
            self._spawn_floating_text(
                f"+{self.last_score}", p.x, p.y - 10, CYAN
            )
            self.hit_flash = HIT_FLASH_FRAMES
            self.last_result = "COMBO"
            try:
                pyxel.play(0, 0)
            except BaseException:
                pass

            if self.combo >= SUPER_HIT_THRESHOLD:
                # SUPER HIT! Extra score burst
                super_bonus = int(500 * self.combo * (1.0 + timing_bonus))
                self.score += super_bonus
                self.last_score += super_bonus
                self._spawn_super_particles(p.x, p.y)
                self._spawn_floating_text("SUPER!!", p.x, p.y - 25, LIME)
                self.shake_frames = SUPER_SHAKE_FRAMES
                self.last_result = "SUPER"
                try:
                    pyxel.play(0, 2)
                except BaseException:
                    pass
                # Reset combo after SUPER, but keep its color as the new active
                self.combo = 1
                self.combo_color = pitch_color
            # If combo but not super, combo stays active with same color
        else:
            # Different color or first hit — FOUL / new color start
            if self.combo > 0:
                self.last_result = "FOUL"
                if self.combo > self.max_combo:
                    self.max_combo = self.combo
            else:
                self.last_result = "HIT"

            self.combo = 1
            self.combo_color = pitch_color
            base_score = 50
            self.last_score = int(base_score * (1.0 + timing_bonus * 0.3))
            self.score += self.last_score

            self._spawn_hit_particles(p.x, p.y, pitch_color)
            self._spawn_floating_text(
                f"+{self.last_score}", p.x, p.y - 10, WHITE
            )
            self.hit_flash = HIT_FLASH_FRAMES
            try:
                pyxel.play(0, 3)
            except BaseException:
                pass

        p.active = False
        self.current_pitch = None

    def _resolve_miss(self) -> None:
        p = self.current_pitch
        if p is None:
            return

        self.strikes += 1
        self.pitch_count += 1
        self.last_result = "STRIKE"
        self.last_score = 0
        self.swing_anim = SWING_FRAMES

        self._spawn_strike_particles(p.x, p.y)
        self._spawn_floating_text("MISS", p.x, p.y - 10, RED)
        try:
            pyxel.play(0, 1)
        except BaseException:
            pass

        p.active = False
        self.current_pitch = None

    def _on_pitch_passed(self) -> None:
        """Ball passed the plate without a swing — automatic strike."""
        self.strikes += 1
        self.pitch_count += 1
        self.last_result = "STRIKE"
        self.last_score = 0

        self._spawn_strike_particles(SZ_CX, SZ_CY)
        self._spawn_floating_text("STRIKE", SZ_CX, SZ_TOP - 10, RED)
        try:
            pyxel.play(0, 1)
        except BaseException:
            pass

        if self.current_pitch is not None:
            self.current_pitch.active = False
            self.current_pitch = None

        self.phase = Phase.RESULT
        self.result_timer = RESULT_FRAMES

    def _check_game_over(self) -> bool:
        return (
            self.strikes >= MAX_STRIKES
            or self.pitch_count >= self.total_pitches
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # Particles & Floating Text
    # ═══════════════════════════════════════════════════════════════════════════

    def _spawn_hit_particles(
        self, x: float, y: float, color: int
    ) -> None:
        for _ in range(12):
            speed = self.rng.uniform(1.5, 4.0)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=speed * (1.0 if self.rng.random() < 0.5 else -1.0),
                    vy=speed * (1.0 if self.rng.random() < 0.5 else -1.0),
                    life=self.rng.randint(15, 30),
                    color=color,
                    size=self.rng.randint(2, 4),
                )
            )

    def _spawn_super_particles(self, x: float, y: float) -> None:
        super_colors = [LIME, PINK, YELLOW, ORANGE, WHITE]
        for _ in range(40):
            speed = self.rng.uniform(3.0, 8.0)
            c = super_colors[self.rng.randint(0, len(super_colors) - 1)]
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=speed * (1.0 if self.rng.random() < 0.5 else -1.0),
                    vy=speed * (1.0 if self.rng.random() < 0.5 else -1.0),
                    life=self.rng.randint(20, 40),
                    color=c,
                    size=self.rng.randint(2, 5),
                )
            )

    def _spawn_strike_particles(self, x: float, y: float) -> None:
        for _ in range(4):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self.rng.uniform(-1.0, 1.0),
                    vy=self.rng.uniform(-1.5, 0.5),
                    life=self.rng.randint(8, 15),
                    color=RED,
                    size=2,
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _spawn_floating_text(
        self, text: str, x: float, y: float, color: int
    ) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=40, color=color)
        )

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ═══════════════════════════════════════════════════════════════════════════
    # Drawing
    # ═══════════════════════════════════════════════════════════════════════════

    def draw(self) -> None:
        pyxel.cls(BLACK)

        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0:
            shake_x = self.rng.randint(-3, 3)
            shake_y = self.rng.randint(-3, 3)
        pyxel.camera(shake_x, shake_y)

        if self.phase == Phase.TITLE:
            self._draw_title()
        else:
            self._draw_field()
            self._draw_pitcher()
            self._draw_batter()
            self._draw_strike_zone()
            self._draw_ui()
            self._draw_pitch_ball()
            self._draw_particles()
            self._draw_floating_texts()
            self._draw_hit_flash()
            if self.phase == Phase.GAME_OVER:
                self._draw_game_over_overlay()

        pyxel.camera(0, 0)

    # ── Title Screen ───────────────────────────────────────────────────────

    def _draw_title(self) -> None:
        title = "BATTER CHAIN"
        pyxel.text(
            SCREEN_W // 2 - len(title) * 4 // 2, 50, title, YELLOW
        )

        subtitle = "Timing & Color Combo Batting"
        pyxel.text(
            SCREEN_W // 2 - len(subtitle) * 4 // 2, 68, subtitle, WHITE
        )

        lines = [
            ("CLICK to swing when ball crosses the plate", CYAN),
            ("Same color = COMBO!  3 Combo = SUPER HOME RUN!", LIME),
            ("Different color = FOUL (resets combo)", GRAY),
            ("Miss or let ball pass = STRIKE", GRAY),
            ("3 Strikes / 10 Pitches = GAME OVER", GRAY),
        ]
        for i, (text, color) in enumerate(lines):
            pyxel.text(
                SCREEN_W // 2 - len(text) * 4 // 2,
                100 + i * 13,
                text,
                color,
            )

        start = "CLICK or ENTER to START"
        pyxel.text(
            SCREEN_W // 2 - len(start) * 4 // 2, 190, start, WHITE
        )

        if self.high_score > 0:
            hs = f"HIGH SCORE: {self.high_score}"
            pyxel.text(
                SCREEN_W // 2 - len(hs) * 4 // 2, 215, hs, YELLOW
            )

    # ── Field ──────────────────────────────────────────────────────────────

    def _draw_field(self) -> None:
        # Sky
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H // 2 + 10, NAVY)

        # Grass
        pyxel.rect(0, SCREEN_H // 2 + 20, SCREEN_W, SCREEN_H // 2 - 20, GREEN)

        # Dirt around plate
        pyxel.rect(SZ_LEFT - 30, SZ_TOP - 10, SZ_W + 60, SZ_H + 40, BROWN)
        # Plate area
        pyxel.rect(SZ_LEFT - 5, SZ_TOP - 5, SZ_W + 10, SZ_H + 10, GRAY)

        # Pitcher mound dirt
        pyxel.circ(PITCHER_X, PITCHER_Y + 25, 20, BROWN)

        # Foul lines
        pyxel.line(PITCHER_X, PITCHER_Y + 25, SZ_LEFT, SZ_TOP, WHITE)
        pyxel.line(PITCHER_X, PITCHER_Y + 25, SZ_LEFT, SZ_BOTTOM, WHITE)

    # ── Pitcher ────────────────────────────────────────────────────────────

    def _draw_pitcher(self) -> None:
        px, py = PITCHER_X, PITCHER_Y

        windup_offset = 0
        if self.phase == Phase.WINDUP and self.windup_timer > 0:
            progress = 1.0 - (self.windup_timer / WINDUP_FRAMES)
            windup_offset = int(progress * 12)

        # Legs
        pyxel.rect(px - 5, py + 18, 5, 10, WHITE)
        pyxel.rect(px + 2, py + 18, 5, 10, WHITE)

        # Body
        pyxel.rect(px - 6, py, 12, 20, WHITE)

        # Head
        pyxel.circ(px, py - 6, 6, WHITE)

        # Cap
        pyxel.rect(px - 7, py - 14, 14, 4, NAVY)
        pyxel.rect(px - 9, py - 10, 18, 2, NAVY)

        # Throwing arm — animates during windup
        arm_x = px - 8 - windup_offset
        arm_y = py + 5 + windup_offset
        pyxel.line(px - 6, py + 3, arm_x, arm_y, WHITE)

        # Glove arm
        pyxel.line(px + 6, py + 3, px + 12, py + 8, BROWN)

    # ── Batter ─────────────────────────────────────────────────────────────

    def _draw_batter(self) -> None:
        bx, by = BATTER_X, BATTER_Y

        swing_t = 0.0
        if self.swing_anim > 0:
            swing_t = 1.0 - (self.swing_anim / SWING_FRAMES)

        # Legs
        pyxel.rect(bx - 4, by + 6, 4, 8, WHITE)
        pyxel.rect(bx + 2, by + 6, 4, 8, WHITE)

        # Body
        pyxel.rect(bx - 6, by - 12, 12, 20, WHITE)

        # Head
        pyxel.circ(bx, by - 20, 6, WHITE)

        # Helmet
        pyxel.rect(bx - 7, by - 26, 14, 6, NAVY)

        # Bat — swings from right to left across the plate
        bat_origin_x = bx + 6
        bat_origin_y = by - 8

        if swing_t < 0.01:
            # Ready position: bat held back
            bat_tip_x = bat_origin_x + 18
            bat_tip_y = bat_origin_y - 10
        else:
            # Swing arc
            t = swing_t
            bat_tip_x = bat_origin_x - int(15 * (1 - t)) + int(t * 8)
            bat_tip_y = bat_origin_y - 12 + int(t * 20)

        pyxel.line(bat_origin_x, bat_origin_y, bat_tip_x, bat_tip_y, BROWN)
        pyxel.circ(bat_tip_x, bat_tip_y, 3, BROWN)

    # ── Strike Zone ────────────────────────────────────────────────────────

    def _draw_strike_zone(self) -> None:
        color = WHITE
        if (
            self.phase == Phase.PITCH
            and self.current_pitch is not None
        ):
            p = self.current_pitch
            if (
                HIT_ZONE_X_MIN <= p.x <= HIT_ZONE_X_MAX
                and HIT_ZONE_Y_MIN <= p.y <= HIT_ZONE_Y_MAX
            ):
                color = LIME

        self._draw_dashed_rect(
            SZ_LEFT, SZ_TOP, SZ_W, SZ_H, 6, 4, color
        )

    def _draw_dashed_rect(
        self,
        x: int, y: int, w: int, h: int,
        dash: int, gap: int, color: int,
    ) -> None:
        # Top
        self._draw_dashed_line(x, y, x + w, y, dash, gap, color)
        # Bottom
        self._draw_dashed_line(x, y + h, x + w, y + h, dash, gap, color)
        # Left
        self._draw_dashed_line(x, y, x, y + h, dash, gap, color)
        # Right
        self._draw_dashed_line(x + w, y, x + w, y + h, dash, gap, color)

    @staticmethod
    def _draw_dashed_line(
        x1: int, y1: int, x2: int, y2: int,
        dash: int, gap: int, color: int,
    ) -> None:
        dx = x2 - x1
        dy = y2 - y1
        length = (dx * dx + dy * dy) ** 0.5
        if length == 0:
            return
        ux = dx / length
        uy = dy / length
        pos = 0.0
        cycle = dash + gap
        while pos < length:
            end = min(pos + dash, length)
            pyxel.line(
                int(x1 + ux * pos),
                int(y1 + uy * pos),
                int(x1 + ux * end),
                int(y1 + uy * end),
                color,
            )
            pos += cycle

    # ── UI ─────────────────────────────────────────────────────────────────

    def _draw_ui(self) -> None:
        # Top bar background
        pyxel.rect(0, 0, SCREEN_W, 12, BLACK)
        pyxel.line(0, 12, SCREEN_W, 12, GRAY)

        # Score
        pyxel.text(4, 2, f"SCORE:{self.score}", WHITE)

        # Combo
        if self.combo > 0:
            combo_str = f"COMBO:x{self.combo}"
            combo_color = CYAN if self.combo >= SUPER_HIT_THRESHOLD else WHITE
        else:
            combo_str = "COMBO:--"
            combo_color = GRAY
        pyxel.text(80, 2, combo_str, combo_color)

        # Active combo color swatch
        if self.combo_color >= 0:
            pyxel.rect(148, 2, 10, 8, self.combo_color)

        # Strikes
        pyxel.text(168, 2, "STRIKES:", WHITE)
        for i in range(MAX_STRIKES):
            sx = 216 + i * 10
            if i < self.strikes:
                pyxel.circ(sx, 6, 3, RED)
            else:
                pyxel.circb(sx, 6, 3, GRAY)

        # Pitch count
        pitch_str = f"P:{self.pitch_count}/{self.total_pitches}"
        pyxel.text(260, 2, pitch_str, GRAY)

    # ── Pitch Ball ─────────────────────────────────────────────────────────

    def _draw_pitch_ball(self) -> None:
        p = self.current_pitch
        if p is None or not p.active:
            return

        # Trail (fading circles behind ball)
        for i, (tx, ty) in enumerate(p.trail):
            alpha = (i + 1) / len(p.trail)
            radius = max(1, int(4 * alpha * 0.65))
            tc = p.color if alpha > 0.3 else GRAY
            pyxel.circ(int(tx), int(ty), radius, tc)

        # Ball with highlight
        ball_color = p.color
        pyxel.circ(int(p.x), int(p.y), 4, ball_color)
        pyxel.circ(int(p.x) - 1, int(p.y) - 1, 1, WHITE)

    # ── Particles ──────────────────────────────────────────────────────────

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = min(1.0, p.life / 20.0)
            color = p.color if alpha > 0.25 else GRAY
            pyxel.circ(int(p.x), int(p.y), p.size, color)

    # ── Floating Texts ─────────────────────────────────────────────────────

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = min(1.0, ft.life / 30.0)
            if ft.life < 8:
                alpha = ft.life / 8.0
            color = ft.color if alpha > 0.3 else GRAY
            pyxel.text(
                int(ft.x) - len(ft.text) * 4 // 2,
                int(ft.y),
                ft.text,
                color,
            )

    # ── Hit Flash ──────────────────────────────────────────────────────────

    def _draw_hit_flash(self) -> None:
        if self.hit_flash <= 0:
            return
        if self.last_result == "SUPER":
            flash_color = LIME if self.hit_flash % 2 == 0 else PINK
        elif self.combo_color >= 0:
            flash_color = self.combo_color
        else:
            flash_color = WHITE

        for y in range(0, SCREEN_H, 6):
            if (y // 6 + self.hit_flash) % 3 == 0:
                pyxel.rect(0, y, SCREEN_W, 2, flash_color)

    # ── Game Over Overlay ──────────────────────────────────────────────────

    def _draw_game_over_overlay(self) -> None:
        # Dark transparent overlay
        for y in range(0, SCREEN_H, 3):
            pyxel.rect(0, y, SCREEN_W, 1, BLACK)

        pyxel.text(
            SCREEN_W // 2 - len("GAME OVER") * 4 // 2,
            60,
            "GAME OVER",
            RED,
        )

        lines = [
            (f"FINAL SCORE: {self.score}", YELLOW),
            (f"MAX COMBO: x{self.max_combo}", CYAN),
            (f"STRIKES: {self.strikes}/{MAX_STRIKES}", RED),
            (f"PITCHES FACED: {self.pitch_count}/{self.total_pitches}", GRAY),
        ]
        for i, (text, color) in enumerate(lines):
            pyxel.text(
                SCREEN_W // 2 - len(text) * 4 // 2,
                85 + i * 14,
                text,
                color,
            )

        if self.high_score > 0:
            hs = f"HIGH SCORE: {self.high_score}"
            pyxel.text(
                SCREEN_W // 2 - len(hs) * 4 // 2,
                150,
                hs,
                YELLOW,
            )

        retry = "CLICK or ENTER to RETRY"
        pyxel.text(
            SCREEN_W // 2 - len(retry) * 4 // 2,
            200,
            retry,
            WHITE,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    Game()


if __name__ == "__main__":
    main()
