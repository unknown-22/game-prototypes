"""188_skip_surge -- Color-Match Jump Rope Prototype

The most fun moment:
  縄跳びで同じ色の縄を連続でリズムよく跳び、COMBOが4以上に達して
  SUPER JUMPが発動し、自動で跳び続けてスコアが3倍で加速する瞬間が面白い
  (Rhythmically jumping same-color rope segments, building COMBO >= 4,
  triggering SUPER JUMP, and auto-jumping for 3x accelerating score.)

Core loop: Rope with 4 colored segments rotates around player.
Press SPACE to jump. Same-color consecutive jumps build COMBO.
COMBO >= 4 triggers SUPER JUMP (5s rainbow, auto-jump, 3x score).
Missed jumps add HEAT; HEAT >= 100 = GAME OVER.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import pyxel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
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

# Rope colors: RED=8, GREEN=3, DARK_BLUE=5, YELLOW=10
ROPE_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
COLOR_SCORES: dict[int, int] = {RED: 8, GREEN: 3, DARK_BLUE: 5, YELLOW: 10}
SUPER_COMBO = 4

GROUND_Y = 200
ROPE_RADIUS = 40
PLAYER_X = SCREEN_W // 2
ROPE_ANCHOR_Y = GROUND_Y

JUMP_VELOCITY = -5.5
GRAVITY = 0.35
INITIAL_ROPE_SPEED = 0.03
MAX_ROPE_SPEED = 0.10
SPEED_INCREMENT = 0.002
SPEED_INTERVAL = 100  # frames between speed increases

SUPER_DURATION = 300  # 5 seconds at 60fps
HEAT_MISS = 10.0
HEAT_DECAY = 0.025
MAX_HEAT = 100.0

SEGMENT_COUNT = 4
SEGMENT_ANGLE = 2 * math.pi / SEGMENT_COUNT  # pi/2

JUMP_WINDOW_RADIANS = 0.45  # ~26 degrees

FONT_PATH = Path(__file__).with_name("k8x12.bdf")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Phase(Enum):
    TITLE = "title"
    PLAYING = "playing"
    GAME_OVER = "game_over"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    """Core game logic. Headless-testable by using Game.__new__ bypass."""

    # Class-level constants
    SEGMENT_COUNT: int = 4
    GROUND_Y: int = 200
    ROPE_RADIUS: int = 40
    JUMP_VELOCITY: float = -5.5
    GRAVITY: float = 0.35
    INITIAL_ROPE_SPEED: float = 0.03
    MAX_ROPE_SPEED: float = 0.10
    SUPER_DURATION: int = 300
    HEAT_MISS: float = 10.0
    HEAT_DECAY: float = 0.025
    MAX_HEAT: float = 100.0
    COMBO_FOR_SUPER: int = 4

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="188 Skip Surge", display_scale=2)
        self._rng: random.Random = random.Random()
        # Pre-init ALL instance attributes
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.rope_angle: float = 0.0
        self.rope_speed: float = INITIAL_ROPE_SPEED
        self.player_y: float = float(GROUND_Y)
        self.player_vy: float = 0.0
        self.is_jumping: bool = False
        self.on_ground: bool = True
        self.active_color: int = ROPE_COLORS[0]
        self.prev_segment_index: int = 0
        self.prev_jump_color: int = 0  # 0 = no previous jump
        self.super_timer: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.frame: int = 0
        self.shake_frames: int = 0
        self.rope_colors: list[int] = list(ROPE_COLORS)
        self._rng = random.Random()
        self.reset()

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset all game state for a new play."""
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.rope_angle = 0.0
        self.rope_speed = INITIAL_ROPE_SPEED
        self.player_y = float(GROUND_Y)
        self.player_vy = 0.0
        self.is_jumping = False
        self.on_ground = True
        self.active_color = ROPE_COLORS[0]
        self.prev_segment_index = 0
        self.prev_jump_color = 0
        self.super_timer = 0
        self.particles.clear()
        self.floating_texts.clear()
        self.frame = 0
        self.shake_frames = 0
        self._shuffle_rope_colors()

    def _shuffle_rope_colors(self) -> None:
        """Randomly shuffle the 4 segment colors."""
        self.rope_colors = list(ROPE_COLORS)
        self._rng.shuffle(self.rope_colors)

    # ------------------------------------------------------------------
    # Testable game logic (no pyxel dependency)
    # ------------------------------------------------------------------

    def _get_segment_index_at_bottom(self) -> int:
        """Returns the index (0-3) of the segment currently at the 6-o'clock position."""
        bottom_angle = math.pi / 2  # 6 o'clock position in screen coords (down = +y)
        normalized = (bottom_angle - self.rope_angle) % (2 * math.pi)
        return int(normalized / SEGMENT_ANGLE) % SEGMENT_COUNT

    def _get_active_color(self) -> int:
        """Returns the color of the segment currently at the 6-o'clock position."""
        idx = self._get_segment_index_at_bottom()
        return self.rope_colors[idx]

    def _is_segment_in_jump_window(self) -> bool:
        """Check if the active segment is within the jump window (near 6 o'clock)."""
        bottom = math.pi / 2
        seg_idx = self._get_segment_index_at_bottom()
        seg_center = (seg_idx * SEGMENT_ANGLE + SEGMENT_ANGLE / 2 + self.rope_angle) % (2 * math.pi)
        diff = abs((seg_center - bottom + math.pi) % (2 * math.pi) - math.pi)
        return diff < JUMP_WINDOW_RADIANS

    def _update_rope(self) -> None:
        """Advance rope angle, update active color, increase speed over time."""
        self.rope_angle = (self.rope_angle + self.rope_speed) % (2 * math.pi)
        self.active_color = self._get_active_color()

        if self.frame > 0 and self.frame % SPEED_INTERVAL == 0:
            self.rope_speed = min(self.rope_speed + SPEED_INCREMENT, MAX_ROPE_SPEED)

    def _jump(self) -> None:
        """Initiate a jump if the player is on the ground."""
        if self.on_ground:
            self.player_vy = JUMP_VELOCITY
            self.is_jumping = True
            self.on_ground = False

    def _update_player(self) -> None:
        """Apply gravity and check ground collision."""
        self.player_vy += GRAVITY
        self.player_y += self.player_vy

        if self.player_y >= GROUND_Y:
            self.player_y = float(GROUND_Y)
            self.player_vy = 0.0
            self.is_jumping = False
            self.on_ground = True

    def _check_jump_timing(self) -> tuple[bool, bool]:
        """Returns (timing_ok, color_match).
        timing_ok = player is in air (above ground).
        color_match = active_color matches prev_jump_color.
        """
        timing_ok = not self.on_ground and self.player_y < GROUND_Y - 5
        color_match = self.active_color == self.prev_jump_color if self.prev_jump_color != 0 else True
        return timing_ok, color_match

    def _resolve_jump(self, timing_ok: bool, color_match: bool) -> None:
        """Update score, combo, heat, and super mode based on jump result."""
        if timing_ok:
            base_score = COLOR_SCORES.get(self.active_color, 5)
            multiplier = 3 if self.super_timer > 0 else 1
            earned = base_score * multiplier
            self.score += earned

            if color_match and self.prev_jump_color != 0:
                self.combo += 1
            else:
                self.combo = 1
            self.prev_jump_color = self.active_color

            if self.combo > self.max_combo:
                self.max_combo = self.combo

            if self.combo >= SUPER_COMBO and self.super_timer == 0:
                self._activate_super()

            self._spawn_jump_particles(PLAYER_X, self.player_y - 8, self.active_color)
            text = f"+{earned}"
            if self.combo > 1:
                text += f" x{self.combo}"
            self._spawn_floating_text(PLAYER_X, self.player_y - 20, text, YELLOW)
        else:
            self.heat += HEAT_MISS
            self.combo = 0
            self.prev_jump_color = 0
            self._spawn_miss_particles(PLAYER_X, GROUND_Y - 2)
            self._spawn_floating_text(PLAYER_X, self.player_y - 20, "MISS!", RED)
            self.shake_frames = 8

    def _update_heat(self) -> None:
        """Decay heat over time and check for game over."""
        self.heat = max(0.0, self.heat - HEAT_DECAY)
        if self.heat >= MAX_HEAT:
            self.heat = MAX_HEAT
            self.phase = Phase.GAME_OVER

    def _activate_super(self) -> None:
        """Activate SUPER JUMP mode."""
        self.super_timer = SUPER_DURATION
        self._spawn_super_particles(PLAYER_X, self.player_y - 15)

    def _update_super(self) -> None:
        """Decrement super_timer and handle super mode effects."""
        if self.super_timer > 0:
            self.super_timer -= 1

    def _update_particles(self) -> None:
        """Move particles, apply gravity, kill expired ones."""
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles[:] = [p for p in self.particles if p.life > 0]
        if len(self.particles) > 100:
            self.particles = self.particles[-100:]

    def _update_floating_texts(self) -> None:
        """Move floating texts upward, kill expired ones."""
        for ft in self.floating_texts:
            ft.y -= 1.2
            ft.life -= 1
        self.floating_texts[:] = [ft for ft in self.floating_texts if ft.life > 0]

    def _spawn_jump_particles(self, x: float, y: float, color: int) -> None:
        """Spawn particles for a successful jump."""
        count = 5
        if self.combo > 0 and self.combo % 5 == 0:
            count = 10
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=x + self._rng.uniform(-4, 4),
                    y=y + self._rng.uniform(-4, 4),
                    vx=self._rng.uniform(-2.0, 2.0),
                    vy=self._rng.uniform(-2.5, -0.5),
                    life=self._rng.randint(12, 22),
                    color=color,
                )
            )

    def _spawn_miss_particles(self, x: float, y: float) -> None:
        """Spawn particles for a missed jump."""
        for _ in range(8):
            self.particles.append(
                Particle(
                    x=x + self._rng.uniform(-6, 6),
                    y=y + self._rng.uniform(-2, 6),
                    vx=self._rng.uniform(-3.0, 3.0),
                    vy=self._rng.uniform(-3.0, -1.0),
                    life=self._rng.randint(10, 18),
                    color=RED,
                )
            )

    def _spawn_super_particles(self, x: float, y: float) -> None:
        """Spawn particles for SUPER mode activation."""
        rainbow = [RED, ORANGE, YELLOW, GREEN, LIME, CYAN, DARK_BLUE, PURPLE, PINK]
        for _ in range(20):
            self.particles.append(
                Particle(
                    x=x + self._rng.uniform(-10, 10),
                    y=y + self._rng.uniform(-10, 10),
                    vx=self._rng.uniform(-4.0, 4.0),
                    vy=self._rng.uniform(-4.0, 0.0),
                    life=self._rng.randint(18, 30),
                    color=self._rng.choice(rainbow),
                )
            )

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        """Spawn a floating text indicator."""
        self.floating_texts.append(
            FloatingText(
                x=x - len(text) * 2,
                y=y,
                text=text,
                life=30,
                color=color,
            )
        )

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def _update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.TITLE

    def _update_playing(self) -> None:
        self.frame += 1

        # Input
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._jump()

        # Auto-jump in super mode
        if self.super_timer > 0 and self._is_segment_in_jump_window():
            self._jump()

        # Update subsystems
        self._update_player()
        self._update_rope()
        self._update_super()
        self._update_heat()

        # Check rope segment crossing (new segment at bottom)
        current_seg_idx = self._get_segment_index_at_bottom()
        if current_seg_idx != self.prev_segment_index:
            self.prev_segment_index = current_seg_idx
            timing_ok, color_match = self._check_jump_timing()
            self._resolve_jump(timing_ok, color_match)

        self._update_particles()
        self._update_floating_texts()

        if self.shake_frames > 0:
            self.shake_frames -= 1

        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def _draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_background(self) -> None:
        """Draw the sky and ground."""
        # Sky
        pyxel.rect(0, 0, SCREEN_W, GROUND_Y - 30, LIGHT_BLUE)
        # Ground gradient
        pyxel.rect(0, GROUND_Y - 30, SCREEN_W, 30, GREEN)
        pyxel.rect(0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y, BROWN)

    def _draw_player(self) -> None:
        """Draw stick figure player."""
        px = PLAYER_X
        py = int(self.player_y)

        # Head
        pyxel.circ(px, py - 22, 5, WHITE)

        # Body
        pyxel.line(px, py - 17, px, py - 5, WHITE)

        # Arms (swing slightly)
        arm_offset = int(math.sin(self.frame * 0.3) * 3)
        pyxel.line(px, py - 14, px - 6 + arm_offset, py - 8, WHITE)
        pyxel.line(px, py - 14, px + 6 - arm_offset, py - 8, WHITE)

        # Legs (split when jumping, together on ground)
        if self.on_ground:
            pyxel.line(px, py - 5, px - 4, py, WHITE)
            pyxel.line(px, py - 5, px + 4, py, WHITE)
        else:
            leg_spread = int(abs(self.player_vy) * 2)
            pyxel.line(px, py - 5, px - 2 - leg_spread, py + 2, WHITE)
            pyxel.line(px, py - 5, px + 2 + leg_spread, py + 2, WHITE)

    def _draw_rope(self) -> None:
        """Draw the 4 colored rope segments as arcs around the anchor."""
        anchor_x = PLAYER_X
        anchor_y = ROPE_ANCHOR_Y
        radius = ROPE_RADIUS

        for i in range(SEGMENT_COUNT):
            start_angle = i * SEGMENT_ANGLE + self.rope_angle
            end_angle = start_angle + SEGMENT_ANGLE
            color = self.rope_colors[i]

            steps = 10
            for step in range(steps):
                a1 = start_angle + (end_angle - start_angle) * step / steps
                a2 = start_angle + (end_angle - start_angle) * (step + 1) / steps
                x1 = anchor_x + math.cos(a1) * radius
                y1 = anchor_y + math.sin(a1) * radius
                x2 = anchor_x + math.cos(a2) * radius
                y2 = anchor_y + math.sin(a2) * radius

                # Fade color for top half (above anchor, not dangerous)
                is_top = math.sin(a1) < 0 and math.sin(a2) < 0
                draw_color = GRAY if is_top else color
                pyxel.line(int(x1), int(y1), int(x2), int(y2), draw_color)

        # Highlight the active segment at bottom
        active_idx = self._get_segment_index_at_bottom()
        active_start = active_idx * SEGMENT_ANGLE + self.rope_angle

        # Brighten active segment
        if self._is_segment_in_jump_window():
            active_color = self.rope_colors[active_idx]
            for step in range(steps):
                a1 = active_start + SEGMENT_ANGLE * step / steps
                a2 = active_start + SEGMENT_ANGLE * (step + 1) / steps
                ax1 = anchor_x + math.cos(a1) * (radius + 1)
                ay1 = anchor_y + math.sin(a1) * (radius + 1)
                ax2 = anchor_x + math.cos(a2) * (radius + 1)
                ay2 = anchor_y + math.sin(a2) * (radius + 1)
                pyxel.line(int(ax1), int(ay1), int(ax2), int(ay2), active_color)

    def _draw_rope_anchor(self) -> None:
        """Draw the rope anchor point on the ground."""
        pyxel.circ(PLAYER_X, ROPE_ANCHOR_Y, 3, GRAY)

    def _draw_hud(self) -> None:
        """Draw the HUD: score, combo, heat bar, super indicator."""
        # Score
        score_text = f"SCORE:{self.score}"
        pyxel.text(4, 4, score_text, WHITE)

        # Combo
        if self.combo >= SUPER_COMBO:
            combo_color = YELLOW
        elif self.combo >= 2:
            combo_color = ORANGE
        else:
            combo_color = GRAY
        combo_text = f"COMBO:{self.combo}"
        cw = len(combo_text) * 4
        pyxel.text(SCREEN_W // 2 - cw // 2, 4, combo_text, combo_color)

        # Max combo (small, top-right)
        max_text = f"MAX:{self.max_combo}"
        pyxel.text(SCREEN_W - len(max_text) * 4 - 4, 4, max_text, WHITE)

        # SUPER indicator
        if self.super_timer > 0:
            super_text = f"SUPER! {self.super_timer // 60 + 1}s"
            sw = len(super_text) * 4
            flash = (pyxel.frame_count // 4) % 2 == 0
            super_color = YELLOW if flash else LIME
            pyxel.text(SCREEN_W // 2 - sw // 2, 16, super_text, super_color)

        # Heat bar (bottom)
        bar_w = 200
        bar_h = 8
        bar_x = (SCREEN_W - bar_w) // 2
        bar_y = SCREEN_H - 16
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, DARK_BLUE)
        heat_fill = int(bar_w * (self.heat / MAX_HEAT))
        if self.heat < 30:
            heat_color = GREEN
        elif self.heat < 60:
            heat_color = ORANGE
        else:
            heat_color = RED
        pyxel.rect(bar_x, bar_y, heat_fill, bar_h, heat_color)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        heat_label = "HEAT"
        pyxel.text(bar_x - 20, bar_y, heat_label, GRAY)

        # Frame (optional, for debugging)
        # pyxel.text(4, SCREEN_H - 10, f"SPD:{self.rope_speed:.3f}", GRAY)

    def _draw_particles(self) -> None:
        """Draw all active particles."""
        for p in self.particles:
            alpha = p.life / 25.0
            if alpha > 0.3:
                pyxel.rect(int(p.x), int(p.y), 2, 2, p.color)
            else:
                pyxel.rect(int(p.x), int(p.y), 2, 2, GRAY)

    def _draw_floating_texts(self) -> None:
        """Draw all floating text indicators."""
        for ft in self.floating_texts:
            pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

    def _draw_super_border(self) -> None:
        """Draw a rainbow pulsing border during SUPER mode."""
        if self.super_timer <= 0:
            return
        rainbow = [RED, ORANGE, YELLOW, GREEN, LIME, CYAN, DARK_BLUE, PURPLE, PINK]
        offset = (self.frame // 3) % len(rainbow)
        thickness = 3
        for t in range(thickness):
            c = rainbow[(offset + t) % len(rainbow)]
            pyxel.rectb(t, t, SCREEN_W - t * 2, SCREEN_H - t * 2, c)

    def _draw_playing(self) -> None:
        """Draw the playing game screen."""
        self._draw_background()
        self._draw_rope()
        self._draw_rope_anchor()
        self._draw_player()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_super_border()
        self._draw_hud()

    def _draw_title(self) -> None:
        """Draw the title screen."""
        self._draw_background()
        # Simulate idle rope rotation
        idle_angle = (pyxel.frame_count * 0.02) % (2 * math.pi)
        self.rope_angle = idle_angle
        self._draw_rope()
        self._draw_rope_anchor()

        # Title
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, BLACK)

        title = "SKIP SURGE"
        tw = len(title) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 30, title, WHITE)

        sub = "Color-Match Jump Rope"
        sw = len(sub) * 4
        pyxel.text(SCREEN_W // 2 - sw // 2, 50, sub, LIME)

        # Color legend
        color_names = ["RED(8)", "GREEN(3)", "BERRY(5)", "GOLD(10)"]
        color_values = [RED, GREEN, DARK_BLUE, YELLOW]
        for i, (col, name) in enumerate(zip(color_values, color_names)):
            bx = 16 + i * 72
            pyxel.rect(bx - 6, 70, 12, 12, col)
            pyxel.rectb(bx - 6, 70, 12, 12, WHITE)
            nw = len(name) * 4
            pyxel.text(bx - nw // 2, 86, name, WHITE)

        # Instructions
        lines = [
            "Jump over rope segments with SPACE.",
            "",
            "Match same color -> COMBO UP!",
            f"COMBO>={SUPER_COMBO} -> SUPER JUMP!",
            "  (5s rainbow, 3x score, auto-jump)",
            "",
            "Miss timing -> HEAT (rope hits feet)",
            "HEAT >= 100 -> GAME OVER",
            "",
            "[SPACE] / [ENTER] to START",
        ]
        for i, ln in enumerate(lines):
            color = GRAY if ln else GRAY
            pyxel.text(25, 105 + i * 11, ln, color)

    def _draw_game_over(self) -> None:
        """Draw the game over screen."""
        self._draw_background()
        self._draw_rope()
        self._draw_rope_anchor()
        self._draw_player()

        # Dim overlay
        pyxel.rect(0, 70, SCREEN_W, 100, BLACK)

        go_text = "GAME OVER"
        gw = len(go_text) * 4
        pyxel.text(SCREEN_W // 2 - gw // 2, 82, go_text, RED)

        def _ctr(y: int, text: str, color: int) -> None:
            pyxel.text(SCREEN_W // 2 - len(text) * 2, y, text, color)

        _ctr(105, f"SCORE: {self.score}", WHITE)
        _ctr(118, f"MAX COMBO: {self.max_combo}", ORANGE)
        _ctr(131, f"SPEED: {self.rope_speed:.3f}", GRAY)
        super_yes = "YES" if self.max_combo >= SUPER_COMBO else "NO"
        _ctr(144, f"SUPER REACHED: {super_yes}", YELLOW)

        _ctr(170, "[SPACE] to RESTART", GRAY)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    Game()


if __name__ == "__main__":
    main()
