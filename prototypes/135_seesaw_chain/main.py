"""SEESAW CHAIN — Balance puzzle game.

Core mechanic: place colored weights on a pivoting beam.
Same-color consecutive placements build COMBO → SUPER BALANCE (rainbow, auto-balance, 3x score).
A "future hand" mechanic shows the next weight's color — commit to it for bonus, or break commitment for HEAT penalty.
Game over when the seesaw tips too far (>30°), HEAT reaches max (100), or 90-second timer expires.

Most fun moment: building a COMBO chain of same-color weights while the seesaw gets increasingly unstable,
then hitting COMBO>=4 to trigger SUPER BALANCE which auto-stabilizes everything and gives a 3x score burst.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
import math
import random

import pyxel


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCREEN_W = 320
SCREEN_H = 240
PIVOT_X = SCREEN_W // 2       # 160
PIVOT_Y = SCREEN_H // 2 + 30  # 150
BEAM_LENGTH = 240
MAX_ANGLE = 30
MAX_HEAT = 100
GAME_TIME = 90 * 30           # 90 seconds at 30 FPS
SUPER_DURATION = 5 * 30       # 5 seconds at 30 FPS
WEIGHT_SPAWN_INTERVAL = 45    # frames between auto-spawns
TORQUE_SCALE = 8.0
NUM_COLORS = 4
COLOR_NAMES = ["RED", "GREEN", "BLUE", "YELLOW"]
COLOR_VALS = [8, 3, 6, 10]    # RED, GREEN, LIGHT_BLUE, YELLOW in pyxel
HEAT_WRONG_COLOR = 15
HEAT_MISS_COMMIT = 10
HEAT_COMBO_MATCH = -5
HEAT_DECAY = 0.05
COMBO_SUPER_THRESHOLD = 4
SUPER_TORQUE_REDUCTION = 0.5
COMMIT_MULTIPLIER = 1.5
SUPER_SCORE_MULTIPLIER = 3.0
MIN_WEIGHT_MASS = 1.0
MAX_WEIGHT_MASS = 5.0
WEIGHT_PLACEMENT_SCORE = 10


class Side(Enum):
    LEFT = auto()
    RIGHT = auto()


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Weight:
    color: int
    mass: float
    side: Side
    dist: float
    x: float = 0.0
    y: float = 0.0
    landed: bool = False
    landing_frame: int = 0


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
    life: int
    color: int
    vy: float = -1.0


# ---------------------------------------------------------------------------
# Game class
# ---------------------------------------------------------------------------

class Game:
    """Main game class for SEESAW CHAIN."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="SEESAW CHAIN", display_scale=2)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    # ---- State reset ----

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.beam_angle: float = 0.0
        self.weights: list[Weight] = []
        self.last_color: int | None = None
        self.next_color: int = self._rng.randint(0, NUM_COLORS - 1)
        self.committed: bool = False
        self.super_timer: int = 0
        self.super_active: bool = False
        self.game_timer: int = GAME_TIME
        self.active_color: int = 0
        self.spawn_timer: int = WEIGHT_SPAWN_INTERVAL
        self.current_mass: float = self._rng.uniform(MIN_WEIGHT_MASS, MAX_WEIGHT_MASS)
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._rng = random.Random()

    # ---- Update dispatch ----

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()
        self._update_particles()
        self._update_floating_texts()

    # ---- Draw dispatch ----

    def draw(self) -> None:
        pyxel.cls(1)  # NAVY background
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    # ---- Title screen ----

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._start_game()

    def _start_game(self) -> None:
        self.reset()
        self.phase = Phase.PLAYING

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 42, 60, "SEESAW CHAIN", 7)
        pyxel.text(SCREEN_W // 2 - 55, 82, "Balance the Beam!", 7)
        pyxel.text(SCREEN_W // 2 - 55, 108, "Click LEFT/RIGHT to place", 13)
        pyxel.text(SCREEN_W // 2 - 55, 120, "Wheel: Change Color", 13)
        pyxel.text(SCREEN_W // 2 - 55, 132, "RightClick: Commit to Next", 13)
        pyxel.text(SCREEN_W // 2 - 55, 144, "Buttons: Select Color", 13)
        pyxel.text(SCREEN_W // 2 - 55, 170, "SPACE or Click to Start", 7)

    # ---- Playing phase ----

    def _update_playing(self) -> None:
        # 1. Decrement game_timer
        self.game_timer -= 1
        if self.game_timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        # 2. Heat decay
        self.heat = max(0.0, self.heat - HEAT_DECAY)

        # 3. Check heat game over
        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER
            return

        # 4. Handle input
        self._handle_input()

        # 5. Spawn timer (auto-cycle current weight if idle)
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.active_color = self._rng.randint(0, NUM_COLORS - 1)
            self.current_mass = self._rng.uniform(MIN_WEIGHT_MASS, MAX_WEIGHT_MASS)
            self.spawn_timer = WEIGHT_SPAWN_INTERVAL
            self.heat = min(float(MAX_HEAT), self.heat + 2.0)

        # 6. Update particles handled in update()

        # 7. Update floating texts handled in update()

        # 8. SUPER timer
        if self.super_active:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_active = False
                self.combo = 0

        # 9. Compute beam angle
        total_torque = self._compute_torque()
        if self.super_active:
            total_torque *= SUPER_TORQUE_REDUCTION
        self.beam_angle = self._compute_beam_angle(total_torque)

        # 10. Check angle game over
        if abs(self.beam_angle) >= MAX_ANGLE:
            self._spawn_particles(PIVOT_X, PIVOT_Y, 8, 50)
            self._spawn_floating_text(PIVOT_X, PIVOT_Y - 30, "TIPPED!", 8)
            self.phase = Phase.GAME_OVER
            return

    def _handle_input(self) -> None:
        """Handle mouse input: color selection, weight placement, commitment toggle."""
        mx = pyxel.mouse_x
        my = pyxel.mouse_y

        # Color selection via mouse wheel
        if pyxel.mouse_wheel != 0:
            direction = 1 if pyxel.mouse_wheel > 0 else -1
            self.active_color = (self.active_color + direction) % NUM_COLORS

        # Right click to toggle commitment
        if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            self.committed = not self.committed

        # Color selection buttons at bottom (y=195-227)
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            # Check bottom color buttons
            for i in range(NUM_COLORS):
                bx = 40 + i * 50
                if mx >= bx and mx < bx + 32 and my >= 195 and my < 227:
                    self.active_color = i
                    return

            # Check placement zones (y > PIVOT_Y)
            if my > PIVOT_Y - 20 and my < SCREEN_H - 40:
                side = Side.LEFT if mx < PIVOT_X else Side.RIGHT
                self._place_weight(self.active_color, side)

    # ---- Game over screen ----

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._start_game()

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 32, 60, "GAME OVER", 7)
        pyxel.text(SCREEN_W // 2 - 40, 82, f"Score: {self.score}", 7)
        pyxel.text(SCREEN_W // 2 - 42, 97, f"Max Combo: {self.max_combo}", 10)
        if self.heat >= MAX_HEAT:
            pyxel.text(SCREEN_W // 2 - 38, 117, "Overheated!", 8)
        elif self.game_timer <= 0:
            pyxel.text(SCREEN_W // 2 - 38, 117, "Time's up!", 12)
        else:
            pyxel.text(SCREEN_W // 2 - 38, 117, "Seesaw Tipped!", 8)
        pyxel.text(SCREEN_W // 2 - 48, 150, "Press R to Restart", 7)

    # ---- Core logic (testable, no pyxel input) ----

    def _compute_torque(self) -> float:
        """Return total torque from all placed weights."""
        total = 0.0
        for w in self.weights:
            sign = 1.0 if w.side == Side.RIGHT else -1.0
            total += w.mass * w.dist * sign
        return total

    def _compute_beam_angle(self, torque: float) -> float:
        """Convert total torque to beam angle, clamped to MAX_ANGLE."""
        angle = torque / TORQUE_SCALE
        return max(-MAX_ANGLE, min(MAX_ANGLE, angle))

    def _place_weight(self, color: int, side: Side) -> int:
        """Place a weight on the beam. Returns score gained from this placement."""
        # Determine color (if committed and next_color matches, could override)
        # Actually committed is handled below for bonus/malus

        # Compute distance: find position on the selected side
        same_side_count = sum(1 for w in self.weights if w.side == side)
        dist = BEAM_LENGTH / 2 * 0.3 + same_side_count * 12.0
        dist = min(dist, BEAM_LENGTH / 2 - 10.0)

        weight = Weight(
            color=color,
            mass=self.current_mass,
            side=side,
            dist=dist,
            x=0.0,
            y=0.0,
            landed=False,
            landing_frame=3,
        )
        self.weights.append(weight)

        # Color match / COMBO logic
        if self.super_active:
            self.combo += 1
        elif self.last_color is not None and color == self.last_color:
            self.combo += 1
            self.heat = max(0.0, self.heat + HEAT_COMBO_MATCH)
        else:
            self.combo = 0
            if self.last_color is not None:
                self.heat = min(float(MAX_HEAT), self.heat + HEAT_WRONG_COLOR)

        if self.combo > self.max_combo:
            self.max_combo = self.combo

        # Commitment handling
        commit_mul = 1.0
        if self.committed:
            if color == self.next_color:
                commit_mul = COMMIT_MULTIPLIER
            else:
                self.heat = min(float(MAX_HEAT), self.heat + HEAT_MISS_COMMIT)
            self.committed = False

        # SUPER BALANCE activation
        if self.combo >= COMBO_SUPER_THRESHOLD and not self.super_active:
            self._activate_super()

        # Score calculation
        super_mul = SUPER_SCORE_MULTIPLIER if self.super_active else 1.0
        combo_mul = max(1, self.combo)
        score_gain = int(self.current_mass * WEIGHT_PLACEMENT_SCORE * combo_mul * super_mul * commit_mul)
        self.score += score_gain

        # Update state
        self.last_color = color if not self.super_active else self.last_color

        # Generate next color preview
        next_c = self._rng.randint(0, NUM_COLORS - 1)
        while next_c == color and NUM_COLORS > 1:
            next_c = self._rng.randint(0, NUM_COLORS - 1)
        self.next_color = next_c

        # Generate next weight mass
        self.current_mass = self._rng.uniform(MIN_WEIGHT_MASS, MAX_WEIGHT_MASS)

        # Reset spawn timer
        self.spawn_timer = WEIGHT_SPAWN_INTERVAL

        # Visual effects
        angle_rad = math.radians(self.beam_angle)
        sign = 1.0 if side == Side.RIGHT else -1.0
        drop_x = PIVOT_X + math.cos(angle_rad) * dist * sign
        drop_y = PIVOT_Y + math.sin(angle_rad) * dist * sign
        self._spawn_particles(drop_x, drop_y, COLOR_VALS[color], 10)
        if score_gain > 0:
            self._spawn_floating_text(drop_x, drop_y - 8, f"+{score_gain}", 14)
        if self.combo >= 2:
            self._spawn_floating_text(drop_x, drop_y - 20, f"COMBO x{self.combo}!", 10)

        return score_gain

    def _activate_super(self) -> None:
        """Activate SUPER BALANCE mode."""
        self.super_active = True
        self.super_timer = SUPER_DURATION
        self._spawn_particles(PIVOT_X, PIVOT_Y, 10, 30)
        for i in range(NUM_COLORS):
            self._spawn_floating_text(
                PIVOT_X - 20 + i * 15, PIVOT_Y - 40,
                "SUPER", COLOR_VALS[i],
            )
        self._spawn_floating_text(PIVOT_X, PIVOT_Y - 20, "BALANCE!", 14)

    def _check_game_over(self) -> bool:
        """Return True if game over conditions are met (no pyxel input needed)."""
        return self.heat >= MAX_HEAT or self.game_timer <= 0 or abs(self.beam_angle) >= MAX_ANGLE

    # ---- Weight position update ----

    def _update_weight_positions(self) -> None:
        """Update x,y for all weights based on current beam_angle."""
        angle_rad = math.radians(self.beam_angle)
        for w in self.weights:
            sign = 1.0 if w.side == Side.RIGHT else -1.0
            w.x = PIVOT_X + math.cos(angle_rad) * w.dist * sign
            w.y = PIVOT_Y + math.sin(angle_rad) * w.dist * sign

    # ---- Particle and floating text methods ----

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-2.5, 2.5)
            vy = self._rng.uniform(-2.5, 2.5)
            life = self._rng.randint(15, 30)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=30, color=color)
        )

    def _update_particles(self) -> None:
        surviving: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                surviving.append(p)
        self.particles = surviving

    def _update_floating_texts(self) -> None:
        surviving: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life > 0:
                surviving.append(ft)
        self.floating_texts = surviving

    # ---- Drawing methods ----

    def _draw_playing(self) -> None:
        self._draw_hud()
        self._draw_seesaw()
        self._draw_particles_vis()
        self._draw_floating_texts_vis()
        self._draw_bottom_bar()
        self._draw_mouse_indicator()

    def _draw_hud(self) -> None:
        # Top bar background
        pyxel.rect(0, 0, SCREEN_W, 28, 0)
        pyxel.line(0, 28, SCREEN_W, 28, 7)

        # Timer
        secs = max(0, self.game_timer // 30)
        if secs > 10:
            timer_color = 7
        elif secs > 5:
            timer_color = 10
        else:
            timer_color = 8 if (pyxel.frame_count // 15) % 2 == 0 else 10
        pyxel.text(4, 4, f"TIME {secs:2d}", timer_color)

        # Score
        pyxel.text(SCREEN_W // 2 - 25, 4, f"SCORE {self.score}", 7)

        # Combo
        combo_color = 7
        if self.combo >= COMBO_SUPER_THRESHOLD:
            combo_color = COLOR_VALS[(pyxel.frame_count // 4) % 4]
        elif self.combo >= 3:
            combo_color = 10
        pyxel.text(SCREEN_W - 60, 4, f"COMBO x{self.combo}", combo_color)

        # Heat bar
        pyxel.text(4, 16, "HEAT", 9)
        pyxel.rect(48, 16, MAX_HEAT, 6, 0)
        heat_w = int(self.heat)
        heat_bar_color = 3 if self.heat < 50 else 10 if self.heat < 80 else 8
        pyxel.rect(48, 16, heat_w, 6, heat_bar_color)

        # SUPER indicator
        if self.super_active:
            secs = self.super_timer // 30 + 1
            color = COLOR_VALS[(pyxel.frame_count // 3) % 4]
            pyxel.text(SCREEN_W - 67, 16, f"SUPER {secs}s", color)

    def _draw_seesaw(self) -> None:
        self._update_weight_positions()

        angle_rad = math.radians(self.beam_angle)
        half_len = BEAM_LENGTH / 2
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        # Left endpoint
        lx = PIVOT_X - half_len * cos_a
        ly = PIVOT_Y - half_len * sin_a
        # Right endpoint
        rx = PIVOT_X + half_len * cos_a
        ry = PIVOT_Y + half_len * sin_a

        # Ground support
        pyxel.rect(PIVOT_X - 40, PIVOT_Y + 10, 80, 40, 5)
        pyxel.rect(PIVOT_X - 20, PIVOT_Y - 5, 40, 20, 13)
        pyxel.tri(PIVOT_X, PIVOT_Y - 10, PIVOT_X - 8, PIVOT_Y + 5, PIVOT_X + 8, PIVOT_Y + 5, 13)

        # Beam
        beam_color = 7
        if self.super_active:
            beam_color = COLOR_VALS[(pyxel.frame_count // 4) % 4]
        elif abs(self.beam_angle) > MAX_ANGLE * 0.7:
            beam_color = 8 if (pyxel.frame_count // 8) % 2 == 0 else 10
        pyxel.line(int(lx), int(ly), int(rx), int(ry), beam_color)

        # Draw angle indicator lines
        danger_threshold = MAX_ANGLE * 0.7
        if abs(self.beam_angle) > danger_threshold:
            # Danger zone markers
            pyxel.text(PIVOT_X - 60, PIVOT_Y + 15, "!", 8 if (pyxel.frame_count // 15) % 2 == 0 else 10)
            pyxel.text(PIVOT_X + 56, PIVOT_Y + 15, "!", 8 if (pyxel.frame_count // 15) % 2 == 0 else 10)

        # Draw weights
        for w in self.weights:
            base_size = 6.0 + w.mass * 2.0
            hw = int(base_size)  # half-width

            if w.landing_frame > 0:
                w.landing_frame -= 1
                offset_y = -20 + w.landing_frame * 7
                draw_x = int(w.x - hw)
                draw_y = int(w.y - hw + offset_y)
                alpha = (3 - w.landing_frame) / 3
                if alpha < 0.3:
                    alpha = 0.3
                pyxel.rect(draw_x, draw_y, hw * 2, hw * 2, COLOR_VALS[0])
            else:
                w.landed = True
                w_color = COLOR_VALS[w.color]
                if self.super_active:
                    w_color = COLOR_VALS[(pyxel.frame_count // 4) % 4]
                draw_x = int(w.x - hw)
                draw_y = int(w.y - hw)
                pyxel.rect(draw_x, draw_y, hw * 2, hw * 2, w_color)
                pyxel.rectb(draw_x, draw_y, hw * 2, hw * 2, 7)

    def _draw_particles_vis(self) -> None:
        for p in self.particles:
            alpha_scale = p.life / 30.0
            r = max(0.5, 1.5 * alpha_scale)
            pyxel.circ(int(p.x), int(p.y), int(r), p.color)

    def _draw_floating_texts_vis(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 30.0
            if alpha < 0.2:
                continue
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_bottom_bar(self) -> None:
        # Bottom bar background
        pyxel.rect(0, 190, SCREEN_W, 50, 0)
        pyxel.line(0, 190, SCREEN_W, 190, 7)

        # Color selection buttons
        for i in range(NUM_COLORS):
            bx = 40 + i * 50
            by = 195
            # Draw button
            btn_color = COLOR_VALS[i]
            pyxel.rect(bx, by, 32, 32, btn_color)
            # Highlight active color
            if i == self.active_color:
                border_color = 7 if (pyxel.frame_count // 15) % 2 == 0 else 0
            else:
                border_color = 0
            pyxel.rectb(bx, by, 32, 32, border_color)
            # Label
            pyxel.text(bx + 1, by + 10, COLOR_NAMES[i][:3], 7 if btn_color < 7 else 0)

        # Next weight preview
        nx = 270
        ny = 205
        pyxel.text(nx - 15, ny - 10, "NEXT", 7)
        pyxel.rect(nx - 6, ny - 6, 12, 12, COLOR_VALS[self.next_color])
        pyxel.rectb(nx - 6, ny - 6, 12, 12, 7)

        # Commitment indicator
        if self.committed:
            pyxel.text(nx - 4, ny + 10, "C!", 10)
        else:
            pyxel.text(nx - 4, ny + 10, "?", 13)

        # Mass indicator
        pyxel.text(nx - 20, ny + 22, f"M:{self.current_mass:.1f}", 7)

    def _draw_mouse_indicator(self) -> None:
        """Draw the current weight color attached to mouse cursor."""
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        if my < 190 and my > 30:
            c_color = COLOR_VALS[self.active_color]
            if self.super_active:
                c_color = COLOR_VALS[(pyxel.frame_count // 4) % 4]
            pyxel.circ(mx, my, 5, c_color)
            pyxel.circb(mx, my, 5, 7)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    Game()


if __name__ == "__main__":
    main()
