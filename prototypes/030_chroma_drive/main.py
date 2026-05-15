"""CHROMA DRIVE — Top-down color-match putting game.

Reinterpreted from game_idea_factory idea #1 (score 31.85):
  "log/replay as assets" + "one color per turn" hooks
  → the color you just sank determines your next ball's color,
    creating a constraint-driven risk/reward putting loop.

Core mechanic: putt colored ball into holes; match the ball's color
to the hole for COMBO multiplier; sink a different color to reset.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Config ──
SCREEN_W = 256
SCREEN_H = 256
DISPLAY_SCALE = 3
NUM_HOLES = 6
NUM_PUTTS = 9
HOLE_RADIUS = 7
BALL_RADIUS = 3
MAX_POWER = 9.0
FRICTION = 0.94
MIN_SPEED = 0.15
WALL_DAMP = 0.6
TEE_X = SCREEN_W // 2
TEE_Y = SCREEN_H - 28
MARGIN = 22  # min distance from edges for holes

# Pyxel color indices
COLOR_NAMES: list[str] = ["RED", "BLUE", "GREEN", "YELLOW"]
COLORS: list[int] = [pyxel.COLOR_RED, pyxel.COLOR_DARK_BLUE, pyxel.COLOR_GREEN, pyxel.COLOR_YELLOW]
COLOR_COUNT = len(COLORS)

# ── Data Classes ──


@dataclass
class Hole:
    """A putting hole on the green."""

    x: float
    y: float
    color: int  # Pyxel color index


@dataclass
class Ball:
    """The putted ball."""

    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    color: int = pyxel.COLOR_WHITE
    active: bool = True


@dataclass
class Particle:
    """Lightweight visual particle."""

    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


# ── Phase Enum ──


class Phase(Enum):
    AIM = auto()
    PUTT = auto()
    SCORE_POP = auto()
    GAME_OVER = auto()


# ── Game Class ──


class Game:
    """CHROMA DRIVE main game class."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CHROMA DRIVE", display_scale=DISPLAY_SCALE)
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── State Init ──

    def reset(self) -> None:
        """Reset all game state for a new round."""
        self.phase: Phase = Phase.AIM
        self.score: int = 0
        self.combo: int = 0
        self.putts_left: int = NUM_PUTTS
        self.ball_color: int = random.choice(COLORS)
        self.ball: Ball = Ball(x=TEE_X, y=TEE_Y, color=self.ball_color)
        self.holes: list[Hole] = self._spawn_holes()
        self.particles: list[Particle] = []
        self.score_pop: int = 0
        self.score_pop_timer: int = 0
        self.best_combo: int = 0

    def _spawn_holes(self) -> list[Hole]:
        """Generate non-overlapping holes in the upper play area."""
        holes: list[Hole] = []
        attempts = 0
        while len(holes) < NUM_HOLES and attempts < 200:
            x = random.uniform(MARGIN, SCREEN_W - MARGIN)
            y = random.uniform(16, SCREEN_H - 60)
            # Keep holes away from tee
            if abs(x - TEE_X) < 30 and abs(y - TEE_Y) < 50:
                attempts += 1
                continue
            # Check overlap
            too_close = False
            for h in holes:
                if math.hypot(x - h.x, y - h.y) < HOLE_RADIUS * 3:
                    too_close = True
                    break
            if not too_close:
                color = random.choice(COLORS)
                holes.append(Hole(x, y, color))
            attempts += 1
        return holes

    def _reset_ball(self) -> None:
        """Return ball to tee with new color."""
        self.ball.x = TEE_X
        self.ball.y = TEE_Y
        self.ball.vx = 0.0
        self.ball.vy = 0.0
        self.ball.color = self.ball_color
        self.ball.active = True

    # ── Update ──

    def update(self) -> None:
        """Main update loop — delegate to phase handlers."""
        self._update_particles()

        if self.phase == Phase.AIM:
            self._update_aim()
        elif self.phase == Phase.PUTT:
            self._update_putt()
        elif self.phase == Phase.SCORE_POP:
            self._update_score_pop()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_aim(self) -> None:
        """Handle aiming input."""
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            dx = mx - self.ball.x
            dy = my - self.ball.y
            dist = math.hypot(dx, dy)
            if dist < 3:
                return  # too close to click
            # Scale power: longer drag = more power, capped at MAX_POWER
            power = min(dist / 25.0, 1.0) * MAX_POWER
            nx = dx / dist
            ny = dy / dist
            self.ball.vx = nx * power
            self.ball.vy = ny * power
            self.phase = Phase.PUTT

    def _update_putt(self) -> None:
        """Simulate ball physics during putt."""
        b = self.ball
        # Friction
        b.vx *= FRICTION
        b.vy *= FRICTION
        # Move
        b.x += b.vx
        b.y += b.vy
        # Wall bounce
        if b.x < BALL_RADIUS:
            b.x = BALL_RADIUS
            b.vx = abs(b.vx) * WALL_DAMP
        elif b.x > SCREEN_W - BALL_RADIUS:
            b.x = SCREEN_W - BALL_RADIUS
            b.vx = -abs(b.vx) * WALL_DAMP
        if b.y < BALL_RADIUS:
            b.y = BALL_RADIUS
            b.vy = abs(b.vy) * WALL_DAMP
        elif b.y > SCREEN_H - BALL_RADIUS:
            b.y = SCREEN_H - BALL_RADIUS
            b.vy = -abs(b.vy) * WALL_DAMP

        # Trail particles
        speed = math.hypot(b.vx, b.vy)
        if speed > 0.8 and pyxel.frame_count % 2 == 0:
            self.particles.append(
                Particle(b.x, b.y, random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3), 6, b.color)
            )

        # Check hole entry
        holed = self._check_hole_entry()
        if holed is not None:
            b.vx = 0.0
            b.vy = 0.0
            self._on_hole_sunk(holed)
            return

        # Ball stopped
        if speed < MIN_SPEED:
            b.vx = 0.0
            b.vy = 0.0
            self._on_putt_missed()

    def _check_hole_entry(self) -> Hole | None:
        """Return the Hole the ball is within radius of, or None."""
        for h in self.holes:
            if math.hypot(self.ball.x - h.x, self.ball.y - h.y) <= HOLE_RADIUS:
                return h
        return None

    def _on_hole_sunk(self, hole: Hole) -> None:
        """Handle ball sinking into a hole."""
        points: int
        if hole.color == self.ball.color:
            self.combo += 1
            points = 100 * self.combo
            if self.combo > self.best_combo:
                self.best_combo = self.combo
            # Spawn celebration particles
            self._burst_particles(hole.x, hole.y, hole.color, 12)
            # Screen shake for big combos
            if self.combo >= 3:
                self._try_screen_shake(3.0)
        else:
            points = 50
            self.combo = 0
            self._burst_particles(hole.x, hole.y, pyxel.COLOR_WHITE, 4)

        self.score += points
        self.putts_left -= 1
        self.ball_color = hole.color  # "replay as asset" — sunk color becomes next ball
        self.score_pop = points
        self.score_pop_timer = 30
        self.phase = Phase.SCORE_POP

        # Replace sunk hole with new one
        self.holes.remove(hole)
        self._add_new_hole()

    def _on_putt_missed(self) -> None:
        """Handle ball stopping outside any hole."""
        self.putts_left -= 1
        self.combo = 0
        if self.putts_left <= 0:
            self.phase = Phase.GAME_OVER
        else:
            self._reset_ball()
            self.phase = Phase.AIM

    def _add_new_hole(self) -> None:
        """Spawn a replacement hole."""
        attempts = 0
        while attempts < 100:
            x = random.uniform(MARGIN, SCREEN_W - MARGIN)
            y = random.uniform(16, SCREEN_H - 60)
            if abs(x - TEE_X) < 30 and abs(y - TEE_Y) < 50:
                attempts += 1
                continue
            too_close = False
            for h in self.holes:
                if math.hypot(x - h.x, y - h.y) < HOLE_RADIUS * 3:
                    too_close = True
                    break
            if not too_close:
                self.holes.append(Hole(x, y, random.choice(COLORS)))
                return
            attempts += 1

    def _update_score_pop(self) -> None:
        """Brief score display between putts."""
        self.score_pop_timer -= 1
        if self.score_pop_timer <= 0:
            if self.putts_left <= 0:
                self.phase = Phase.GAME_OVER
            else:
                self._reset_ball()
                self.phase = Phase.AIM

    def _update_game_over(self) -> None:
        """Wait for retry input."""
        if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()

    # ── Particles ──

    def _update_particles(self) -> None:
        """Update particle positions and lifetimes."""
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def _burst_particles(self, x: float, y: float, color: int, count: int) -> None:
        """Spawn a burst of celebration particles."""
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(0.8, 2.5)
            self.particles.append(
                Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed, 15, color)
            )

    def _try_screen_shake(self, amount: float) -> None:
        """Attempt screen shake; safe no-op in headless tests."""
        try:
            pyxel.camera(0, 0)
            pyxel.camera(random.uniform(-amount, amount), random.uniform(-amount, amount))
        except BaseException:
            pass

    # ── Draw ──

    def draw(self) -> None:
        """Main draw loop."""
        # Reset camera in case of prior shake
        try:
            pyxel.camera(0, 0)
        except BaseException:
            pass

        pyxel.cls(pyxel.COLOR_DARK_BLUE)

        # Green background
        pyxel.rect(4, 4, SCREEN_W - 8, SCREEN_H - 8, pyxel.COLOR_GREEN)

        # Draw holes
        for hole in self.holes:
            # Outer ring
            pyxel.circb(int(hole.x), int(hole.y), HOLE_RADIUS, pyxel.COLOR_BLACK)
            pyxel.circb(int(hole.x), int(hole.y), HOLE_RADIUS - 1, hole.color)
            # Inner dot
            pyxel.circ(int(hole.x), int(hole.y), 3, pyxel.COLOR_BLACK)
            pyxel.circ(int(hole.x), int(hole.y), 2, hole.color)

        # Draw ball
        if self.ball.active:
            # Shadow
            pyxel.circ(int(self.ball.x + 1), int(self.ball.y + 1), BALL_RADIUS, pyxel.COLOR_BLACK)
            # Ball body
            pyxel.circ(int(self.ball.x), int(self.ball.y), BALL_RADIUS, pyxel.COLOR_WHITE)
            pyxel.circ(int(self.ball.x), int(self.ball.y), BALL_RADIUS - 1, self.ball.color)
            # Shine
            pyxel.pset(int(self.ball.x - 1), int(self.ball.y - 1), pyxel.COLOR_WHITE)

        # Draw particles
        for p in self.particles:
            if p.life > 0:
                pyxel.pset(int(p.x), int(p.y), p.color if p.life > 4 else pyxel.COLOR_GRAY)

        # Draw aim line
        if self.phase == Phase.AIM:
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            dx = mx - self.ball.x
            dy = my - self.ball.y
            dist = math.hypot(dx, dy)
            if dist > 3:
                power_ratio = min(dist / 25.0, 1.0)
                line_len = power_ratio * 45
                nx = dx / dist
                ny = dy / dist
                ex = self.ball.x + nx * line_len
                ey = self.ball.y + ny * line_len
                # Draw dotted aim line
                steps = int(line_len / 4)
                for i in range(steps):
                    t = i / steps
                    lx = self.ball.x + nx * line_len * t
                    ly = self.ball.y + ny * line_len * t
                    if i % 2 == 0:
                        pyxel.pset(int(lx), int(ly), pyxel.COLOR_WHITE)
                # Power bar
                bar_w = int(power_ratio * 40)
                pyxel.rect(int(ex) - 20, int(ey) + 2, 40, 4, pyxel.COLOR_BLACK)
                bar_color = pyxel.COLOR_RED if power_ratio > 0.7 else pyxel.COLOR_YELLOW if power_ratio > 0.4 else pyxel.COLOR_GREEN
                pyxel.rect(int(ex) - 20, int(ey) + 2, bar_w, 4, bar_color)

        # UI overlay
        pyxel.rect(0, 0, SCREEN_W, 12, pyxel.COLOR_BLACK)
        pyxel.text(3, 2, f"SCORE:{self.score:05d}", pyxel.COLOR_WHITE)
        combo_text = f"COMBO:x{max(1, self.combo)}"
        pyxel.text(SCREEN_W // 2 - 16, 2, combo_text, pyxel.COLOR_YELLOW if self.combo >= 3 else pyxel.COLOR_WHITE)
        pyxel.text(SCREEN_W - 60, 2, f"PUTTS:{self.putts_left}", pyxel.COLOR_WHITE)

        # Ball color indicator (bottom-left)
        pyxel.text(2, SCREEN_H - 10, "BALL:", pyxel.COLOR_WHITE)
        pyxel.rect(28, SCREEN_H - 10, 8, 8, self.ball_color)

        # Hole color hint (show matching holes)
        match_count = sum(1 for h in self.holes if h.color == self.ball_color)
        hint = f"MATCH:{match_count}"
        pyxel.text(SCREEN_W - 50, SCREEN_H - 10, hint, pyxel.COLOR_YELLOW if match_count > 1 else pyxel.COLOR_WHITE)

        # Score popup
        if self.phase == Phase.SCORE_POP and self.score_pop_timer > 20:
            pop_color = pyxel.COLOR_YELLOW if self.combo >= 3 else pyxel.COLOR_WHITE
            pyxel.text(SCREEN_W // 2 - 20, SCREEN_H // 2 - 10, f"+{self.score_pop}", pop_color)

        # Game over screen
        if self.phase == Phase.GAME_OVER:
            # Dim overlay
            for yy in range(0, SCREEN_H, 2):
                for xx in range(0, SCREEN_W, 2):
                    if (xx + yy) % 4 == 0:
                        c = pyxel.pget(xx, yy)
                        dark_c = 0 if c == 0 else (c if c < 4 else pyxel.COLOR_NAVY)
                        pyxel.pset(xx, yy, dark_c)

            pyxel.text(SCREEN_W // 2 - 35, SCREEN_H // 2 - 22, "GAME OVER", pyxel.COLOR_WHITE)
            pyxel.text(SCREEN_W // 2 - 40, SCREEN_H // 2 - 6, f"FINAL SCORE: {self.score:05d}", pyxel.COLOR_YELLOW)
            pyxel.text(SCREEN_W // 2 - 38, SCREEN_H // 2 + 6, f"BEST COMBO: x{self.best_combo}", pyxel.COLOR_ORANGE)
            pyxel.text(SCREEN_W // 2 - 48, SCREEN_H // 2 + 22, "CLICK or [R] TO RETRY", pyxel.COLOR_GRAY)


# ── Entry Point ──

def main() -> None:
    """Launch the game."""
    Game()


if __name__ == "__main__":
    main()
