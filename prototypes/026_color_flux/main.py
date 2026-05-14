"""COLOR FLUX — One-button color-matching flyer.

Reinterpreted from game idea #1 (score 31.65): dice/bag roguelite with
"synthesis compression" + "one color per turn" hooks, reimagined as a
one-button flyer where matching same-color gates builds COMBO for
SYNTHESIS super-mode.

Core mechanic: flap through colored gates. Consecutive same-color gates
build COMBO. COMBO >= SYNTHESIS_THRESHOLD triggers super-mode (all gates
auto-match, 3x score). Heat builds from wrong colors and misses.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Config ────────────────────────────────────────────────────────────────

SCREEN_W = 256
SCREEN_H = 256
DISPLAY_SCALE = 3
FPS = 60

# Bird
BIRD_X = 64
BIRD_SIZE = 14
GRAVITY = 0.45
FLAP_VELOCITY = -4.8
MAX_FALL_SPEED = 7.0
CEILING_Y = 4
FLOOR_Y = SCREEN_H - 4

# Gates
GATE_WIDTH = 22
GATE_SPEED = 1.8
GATE_SPAWN_INTERVAL = 72  # frames between gates
GATE_MIN_GAP = 50
GATE_MAX_GAP = 70
GATE_MIN_Y = 30
GATE_MAX_Y = SCREEN_H - 30

# Colors (Pyxel built-in constants that exist in stubs)
COLORS: list[int] = [
    pyxel.COLOR_RED,
    pyxel.COLOR_GREEN,
    pyxel.COLOR_YELLOW,
    pyxel.COLOR_CYAN,
]
COLOR_NAMES: list[str] = ["RED", "GREEN", "YELLOW", "CYAN"]
N_COLORS = len(COLORS)

# COMBO / SYNTHESIS
SYNTHESIS_THRESHOLD = 5  # COMBO needed to trigger SYNTHESIS
SYNTHESIS_DURATION = 120  # frames (2 seconds)

# Heat
MAX_HEAT = 10
WRONG_COLOR_HEAT = 2
MISS_GATE_HEAT = 1

# Scoring
BASE_SCORE = 10
COMBO_BONUS = 5  # extra per combo level
SYNTHESIS_MULTIPLIER = 3


# ── Data Classes ───────────────────────────────────────────────────────────


class Phase(Enum):
    PLAYING = auto()
    SYNTHESIS = auto()
    GAME_OVER = auto()


@dataclass
class Gate:
    """A colored gate obstacle with a gap for the bird to pass through."""

    x: float
    gap_y: int  # center of the gap
    gap_h: int  # height of the gap
    color: int  # Pyxel color constant
    scored: bool = False  # has the player passed through this gate?

    @property
    def top_h(self) -> int:
        """Height of the top pillar."""
        return self.gap_y - self.gap_h // 2

    @property
    def bottom_y(self) -> int:
        """Y position where the bottom pillar starts."""
        return self.gap_y + self.gap_h // 2

    @property
    def right(self) -> float:
        return self.x + GATE_WIDTH

    @property
    def left(self) -> float:
        return self.x


@dataclass
class Particle:
    """Floating score/effect particle."""

    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    text: str = ""


# ── Game Class ─────────────────────────────────────────────────────────────


class ColorFlux:
    """One-button color-matching flyer game."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="COLOR FLUX", fps=FPS,
                    display_scale=DISPLAY_SCALE)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        """Initialize or reset all game state."""
        # Bird
        self.bird_y: float = SCREEN_H / 2
        self.bird_vy: float = 0.0
        self.bird_color: int = random.choice(COLORS)

        # Gates
        self.gates: list[Gate] = []
        self._gate_timer: int = 0

        # Phase
        self.phase: Phase = Phase.PLAYING
        self._synth_timer: int = 0

        # Scoring
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: int = 0
        self.gates_passed: int = 0
        self.synthesis_count: int = 0

        # Particles
        self.particles: list[Particle] = []

        # Spawn the first gate quickly
        self._gate_timer = GATE_SPAWN_INTERVAL - 30

    # ── Update ─────────────────────────────────────────────────────────

    def update(self) -> None:
        """Main update loop."""
        if self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.SYNTHESIS:
            self._update_synthesis()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

        self._update_particles()

    def _update_playing(self) -> None:
        """Update during normal play."""
        # Bird physics
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.bird_vy = FLAP_VELOCITY
            self._spawn_flap_particle()

        self.bird_vy = min(self.bird_vy + GRAVITY, MAX_FALL_SPEED)
        self.bird_y += self.bird_vy

        # Boundary check
        if self.bird_y <= CEILING_Y or self.bird_y >= FLOOR_Y:
            self._die()
            return

        # Spawn gates
        self._gate_timer -= 1
        if self._gate_timer <= 0:
            self._spawn_gate()
            self._gate_timer = GATE_SPAWN_INTERVAL

        # Move gates & check collisions
        for gate in self.gates:
            gate.x -= GATE_SPEED

            # Check if bird is inside gate x-range
            if not gate.scored and gate.left <= BIRD_X <= gate.right:
                bird_half = BIRD_SIZE / 2
                bird_top = self.bird_y - bird_half
                bird_bottom = self.bird_y + bird_half

                # Collision with pillars
                if bird_top < gate.top_h or bird_bottom > gate.bottom_y:
                    self._die()
                    return

                # Passed through gap — check color match
                if self.bird_color == gate.color:
                    self._on_match(gate)
                else:
                    self._on_mismatch(gate)
                gate.scored = True

        # Remove off-screen gates (left side)
        missed = [g for g in self.gates if g.right < 0 and not g.scored]
        for _ in missed:
            self._on_miss()

        self.gates = [g for g in self.gates if g.right > -20]

        # Randomly change bird color periodically
        if pyxel.frame_count % 180 == 0 and self.gates:
            self._shift_bird_color()

    def _update_synthesis(self) -> None:
        """Update during SYNTHESIS super-mode."""
        # Bird physics (same as playing)
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.bird_vy = FLAP_VELOCITY
            self._spawn_flap_particle()

        self.bird_vy = min(self.bird_vy + GRAVITY, MAX_FALL_SPEED)
        self.bird_y += self.bird_vy

        if self.bird_y <= CEILING_Y or self.bird_y >= FLOOR_Y:
            self._die()
            return

        # Spawn gates (faster during synthesis)
        self._gate_timer -= 1
        if self._gate_timer <= 0:
            self._spawn_gate()
            self._gate_timer = max(40, GATE_SPAWN_INTERVAL - 20)

        # Move gates — all gates auto-match during synthesis
        for gate in self.gates:
            gate.x -= GATE_SPEED

            if not gate.scored and gate.left <= BIRD_X <= gate.right:
                bird_half = BIRD_SIZE / 2
                bird_top = self.bird_y - bird_half
                bird_bottom = self.bird_y + bird_half

                if bird_top < gate.top_h or bird_bottom > gate.bottom_y:
                    self._die()
                    return

                # Synthesis mode: every gate matches
                self._on_synthesis_match(gate)
                gate.scored = True

        # Remove off-screen gates
        missed = [g for g in self.gates if g.right < 0 and not g.scored]
        for _ in missed:
            self._on_miss()
        self.gates = [g for g in self.gates if g.right > -20]

        # Synthesis timer
        self._synth_timer -= 1
        if self._synth_timer <= 0:
            self.phase = Phase.PLAYING
            self.combo = 0  # reset combo after synthesis ends

    def _update_game_over(self) -> None:
        """Update during game over screen."""
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_R):
            self.reset()

    def _update_particles(self) -> None:
        """Update floating particles."""
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ── Gate Logic ─────────────────────────────────────────────────────

    def _spawn_gate(self) -> None:
        """Create a new gate at the right edge."""
        gap_h = random.randint(GATE_MIN_GAP, GATE_MAX_GAP)
        margin = gap_h // 2 + 8
        gap_y = random.randint(margin, SCREEN_H - margin)
        color = random.choice(COLORS)
        self.gates.append(Gate(x=SCREEN_W, gap_y=gap_y, gap_h=gap_h,
                                color=color))

    def _shift_bird_color(self) -> None:
        """Change the bird's active color to a different one."""
        current = self.bird_color
        others = [c for c in COLORS if c != current]
        if others:
            self.bird_color = random.choice(others)

    # ── Match/Mismatch/Miss ────────────────────────────────────────────

    def _on_match(self, gate: Gate) -> None:
        """Handle passing through a matching-color gate."""
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        points = BASE_SCORE + self.combo * COMBO_BONUS
        self.score += points
        self.gates_passed += 1
        self._spawn_score_particle(gate, points, gate.color)

        if self.combo >= SYNTHESIS_THRESHOLD:
            self._trigger_synthesis()

    def _on_mismatch(self, gate: Gate) -> None:
        """Handle passing through a non-matching gate."""
        self.combo = 0
        self.heat = min(MAX_HEAT, self.heat + WRONG_COLOR_HEAT)
        points = BASE_SCORE
        self.score += points
        self.gates_passed += 1
        self._spawn_score_particle(gate, points, pyxel.COLOR_GRAY)

        if self.heat >= MAX_HEAT:
            self._die()

    def _on_miss(self) -> None:
        """Handle completely missing a gate."""
        self.heat = min(MAX_HEAT, self.heat + MISS_GATE_HEAT)
        if self.heat >= MAX_HEAT:
            self._die()

    def _on_synthesis_match(self, gate: Gate) -> None:
        """Handle passing through a gate during SYNTHESIS mode."""
        points = (BASE_SCORE + self.combo * COMBO_BONUS) * SYNTHESIS_MULTIPLIER
        self.score += points
        self.gates_passed += 1
        self._spawn_score_particle(gate, points, pyxel.COLOR_YELLOW)

    def _trigger_synthesis(self) -> None:
        """Enter SYNTHESIS super-mode."""
        self.phase = Phase.SYNTHESIS
        self._synth_timer = SYNTHESIS_DURATION
        self.synthesis_count += 1
        # Spawn burst particles
        for _ in range(12):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.0, 3.0)
            self.particles.append(Particle(
                x=BIRD_X, y=self.bird_y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=20, color=pyxel.COLOR_YELLOW,
            ))

    def _die(self) -> None:
        """Handle game over."""
        self.phase = Phase.GAME_OVER
        # Death particles
        for _ in range(16):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.0, 4.0)
            self.particles.append(Particle(
                x=BIRD_X, y=self.bird_y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=30, color=pyxel.COLOR_RED,
            ))

    # ── Particles ──────────────────────────────────────────────────────

    def _spawn_flap_particle(self) -> None:
        """Spawn particles when the bird flaps."""
        for _ in range(3):
            self.particles.append(Particle(
                x=BIRD_X - 4, y=self.bird_y + BIRD_SIZE // 2,
                vx=random.uniform(-1.5, -0.5),
                vy=random.uniform(0.5, 2.0),
                life=8, color=pyxel.COLOR_WHITE,
            ))

    def _spawn_score_particle(self, gate: Gate, points: int, color: int) -> None:
        """Spawn a floating score number."""
        self.particles.append(Particle(
            x=gate.x + GATE_WIDTH // 2,
            y=gate.gap_y,
            vx=-0.5,
            vy=-1.5,
            life=25,
            color=color,
            text=f"+{points}",
        ))

    # ── Draw ───────────────────────────────────────────────────────────

    def draw(self) -> None:
        """Main draw loop."""
        pyxel.cls(pyxel.COLOR_BLACK)

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
            self._draw_particles()
            return

        # Background stars
        self._draw_background()

        # Gates
        for gate in self.gates:
            self._draw_gate(gate)

        # Bird
        self._draw_bird()

        # Particles
        self._draw_particles()

        # HUD
        self._draw_hud()

        # Synthesis overlay
        if self.phase == Phase.SYNTHESIS:
            self._draw_synthesis_overlay()

    def _draw_background(self) -> None:
        """Draw subtle background elements."""
        # Speed lines / grid
        for y in range(0, SCREEN_H, 32):
            offset = (pyxel.frame_count * 2 + y) % 64
            pyxel.pset(offset, y, pyxel.COLOR_NAVY)
            pyxel.pset(offset + 32, y, pyxel.COLOR_NAVY)

    def _draw_gate(self, gate: Gate) -> None:
        """Draw a single gate (top pillar + bottom pillar)."""
        x = int(gate.x)
        color = gate.color
        if self.phase == Phase.SYNTHESIS:
            # Rainbow cycling during synthesis
            idx = (pyxel.frame_count // 4 + x) % N_COLORS
            color = COLORS[idx]

        # Top pillar
        top_h = gate.top_h
        if top_h > 0:
            pyxel.rect(x, 0, GATE_WIDTH, top_h, color)
            # Edge highlight
            pyxel.rect(x + GATE_WIDTH - 2, 0, 2, top_h, pyxel.COLOR_WHITE)

        # Bottom pillar
        bottom_y = gate.bottom_y
        if bottom_y < SCREEN_H:
            pyxel.rect(x, bottom_y, GATE_WIDTH, SCREEN_H - bottom_y, color)
            pyxel.rect(x + GATE_WIDTH - 2, bottom_y, 2,
                        SCREEN_H - bottom_y, pyxel.COLOR_WHITE)

        # Gap indicator lines
        pyxel.line(x, gate.top_h, x + GATE_WIDTH, gate.top_h, pyxel.COLOR_BLACK)
        pyxel.line(x, bottom_y, x + GATE_WIDTH, bottom_y, pyxel.COLOR_BLACK)

    def _draw_bird(self) -> None:
        """Draw the player bird."""
        x = BIRD_X
        y = int(self.bird_y)
        half = BIRD_SIZE // 2

        # Choose color based on phase
        if self.phase == Phase.SYNTHESIS:
            # Rainbow cycling
            idx = (pyxel.frame_count // 6) % N_COLORS
            color = COLORS[idx]
        else:
            color = self.bird_color

        # Body
        pyxel.rect(x - half, y - half, BIRD_SIZE, BIRD_SIZE, color)

        # Eye
        eye_color = pyxel.COLOR_WHITE if color != pyxel.COLOR_WHITE else pyxel.COLOR_BLACK
        pyxel.pset(x + half - 4, y - 3, eye_color)
        pyxel.pset(x + half - 3, y - 4, eye_color)

        # Trail effect
        pyxel.rect(x - half - 2, y - half + 2, 3, BIRD_SIZE - 4, pyxel.COLOR_NAVY)

    def _draw_hud(self) -> None:
        """Draw score, combo, heat, etc."""
        # Score
        pyxel.text(4, 4, f"SCORE:{self.score:06d}", pyxel.COLOR_WHITE)

        # COMBO
        combo_color = pyxel.COLOR_YELLOW if self.combo >= SYNTHESIS_THRESHOLD - 1 else pyxel.COLOR_WHITE
        pyxel.text(4, 12, f"COMBO:{self.combo}", combo_color)

        # Heat bar
        pyxel.text(4, 22, "HEAT", pyxel.COLOR_WHITE)
        bar_x = 36
        bar_w = 60
        bar_h = 5
        pyxel.rectb(bar_x, 22, bar_w, bar_h, pyxel.COLOR_WHITE)
        fill_w = int(bar_w * self.heat / MAX_HEAT)
        if fill_w > 0:
            heat_color = pyxel.COLOR_GREEN
            if self.heat > MAX_HEAT * 0.6:
                heat_color = pyxel.COLOR_YELLOW
            if self.heat > MAX_HEAT * 0.8:
                heat_color = pyxel.COLOR_RED
            pyxel.rect(bar_x + 1, 23, fill_w, bar_h - 1, heat_color)

        # Bird color indicator
        pyxel.text(4, 32, "COLOR:", pyxel.COLOR_WHITE)
        pyxel.rect(42, 32, 8, 6, self.bird_color)

        # Phase indicator
        if self.phase == Phase.SYNTHESIS:
            remaining = self._synth_timer / SYNTHESIS_DURATION
            bar_w2 = 80
            pyxel.rect(4, 42, int(bar_w2 * remaining), 3, pyxel.COLOR_YELLOW)

    def _draw_synthesis_overlay(self) -> None:
        """Draw the SYNTHESIS mode visual effects."""
        # Pulsing border
        alpha = (math.sin(pyxel.frame_count * 0.2) + 1) / 2
        if alpha > 0.5:
            border_color = pyxel.COLOR_YELLOW if pyxel.frame_count % 8 < 4 else pyxel.COLOR_WHITE
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, border_color)

        # "SYNTHESIS!" text
        flash = pyxel.frame_count % 30 < 15
        if flash:
            txt = "SYNTHESIS!"
            tw = len(txt) * 4
            pyxel.text(SCREEN_W // 2 - tw // 2, SCREEN_H - 16, txt, pyxel.COLOR_YELLOW)

    def _draw_game_over(self) -> None:
        """Draw the game over screen."""
        # Dim overlay
        for y in range(0, SCREEN_H, 2):
            pyxel.rect(0, y, SCREEN_W, 1, pyxel.COLOR_BLACK)

        # Title
        title = "GAME OVER"
        tw = len(title) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 60, title, pyxel.COLOR_RED)

        # Stats
        lines = [
            f"SCORE: {self.score}",
            f"MAX COMBO: {self.max_combo}",
            f"SYNTHESIS: {self.synthesis_count}",
            f"GATES: {self.gates_passed}",
        ]
        for i, line in enumerate(lines):
            tw = len(line) * 4
            pyxel.text(SCREEN_W // 2 - tw // 2, 90 + i * 12, line,
                        pyxel.COLOR_WHITE)

        # Restart prompt
        prompt = "PRESS SPACE TO RETRY"
        pw = len(prompt) * 4
        if pyxel.frame_count % 60 < 40:
            pyxel.text(SCREEN_W // 2 - pw // 2, 165, prompt, pyxel.COLOR_GREEN)

    def _draw_particles(self) -> None:
        """Draw all active particles."""
        for p in self.particles:
            alpha = p.life / 30
            col = p.color
            if alpha < 0.3:
                col = pyxel.COLOR_NAVY
            if p.text:
                pyxel.text(int(p.x), int(p.y), p.text, col)
            else:
                pyxel.pset(int(p.x), int(p.y), col)
                pyxel.pset(int(p.x) + 1, int(p.y), col)


# ── Entry Point ────────────────────────────────────────────────────────────


def main() -> None:
    ColorFlux()


if __name__ == "__main__":
    main()
