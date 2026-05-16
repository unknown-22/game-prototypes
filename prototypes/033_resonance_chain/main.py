"""033_resonance_chain — Rhythm-action with colored note chain reactions.

Core mechanic: Hit falling colored notes at the timing zone. Consecutive
same-color hits build a RESONANCE chain that multiplies score and triggers
chain-clear effects at threshold.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import IntEnum

import pyxel

# ── Config ──
SCREEN_W = 256
SCREEN_H = 240
LANE_COUNT = 4
LANE_W = SCREEN_W // LANE_COUNT
HIT_ZONE_Y = SCREEN_H - 40
NOTE_SPEED = 2.0
NOTE_W = 20
NOTE_H = 14
SPAWN_INTERVAL = 40
PERFECT_WINDOW = 10
GOOD_WINDOW = 25
CHAIN_THRESHOLD = 5

LANE_COLORS = [11, 7, 10, 9]  # RED, LIGHT_BLUE, LIME, YELLOW
LANE_KEYS = [pyxel.KEY_Z, pyxel.KEY_X, pyxel.KEY_C, pyxel.KEY_V]
LANE_LABELS = ["Z", "X", "C", "V"]


# ── Data classes ──
@dataclass
class Note:
    lane: int
    y: float
    hit: bool = False
    missed: bool = False


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


class Phase(IntEnum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


# ── Game ──
class Game:
    """Rhythm game with resonance chain mechanic."""

    def __init__(self) -> None:
        self.reset()

    def init_and_run(self) -> None:
        """Initialize pyxel and start the game loop."""
        import pyxel

        pyxel.init(SCREEN_W, SCREEN_H, title="Resonance Chain")
        pyxel.run(self._update, self._draw)

    def reset(self) -> None:
        """Reset all game state to initial values."""
        self.phase: Phase = Phase.TITLE
        self.notes: list[Note] = []
        self.particles: list[Particle] = []
        self.texts: list[FloatingText] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.health: int = 5
        self.resonance_color: int | None = None
        self.resonance_count: int = 0
        self.spawn_timer: int = 0
        self.frame: int = 0
        self.difficulty: float = 1.0
        self.chain_clear_count: int = 0

    # ── Update ──
    def _update(self) -> None:
        import pyxel

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
                self.phase = Phase.PLAYING
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
                self.phase = Phase.TITLE

    def _update_playing(self) -> None:
        import pyxel

        self.frame += 1
        self.difficulty = 1.0 + self.frame / 3600.0  # scales over ~60 seconds

        # Spawn notes
        self.spawn_timer += 1
        interval = max(15, SPAWN_INTERVAL - int(self.difficulty * 5))
        if self.spawn_timer >= interval:
            self.spawn_timer = 0
            self._spawn_note()

        # Update notes
        for note in self.notes:
            if not note.hit and not note.missed:
                note.y += NOTE_SPEED * self.difficulty
                if note.y > HIT_ZONE_Y + GOOD_WINDOW:
                    note.missed = True
                    self._on_miss(note)

        # Clean up notes
        self.notes = [
            n for n in self.notes
            if n.y < SCREEN_H + 20 and not n.hit and not n.missed
        ]

        # Handle input
        for i, key in enumerate(LANE_KEYS):
            if pyxel.btnp(key):
                self._try_hit(i)

        # Update particles
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

        # Update floating texts
        for t in self.texts:
            t.y -= 0.5
            t.life -= 1
        self.texts = [t for t in self.texts if t.life > 0]

        # Game over check
        if self.health <= 0:
            self.phase = Phase.GAME_OVER

    def _spawn_note(self) -> None:
        lane = random.randint(0, LANE_COUNT - 1)
        self.notes.append(Note(lane=lane, y=-float(NOTE_H)))

    def _try_hit(self, lane: int) -> None:
        """Attempt to hit the closest note in the given lane."""
        best_note: Note | None = None
        best_dist = float("inf")
        for note in self.notes:
            if note.lane == lane and not note.hit and not note.missed:
                dist = abs(note.y - HIT_ZONE_Y)
                if dist < best_dist:
                    best_dist = dist
                    best_note = note

        if best_note is None:
            return

        if best_dist <= PERFECT_WINDOW:
            self._on_hit(best_note, "PERFECT", 2)
        elif best_dist <= GOOD_WINDOW:
            self._on_hit(best_note, "GOOD", 1)

    def _on_hit(self, note: Note, rating: str, points: int) -> None:
        """Process a successful hit with combo/resonance tracking."""
        note.hit = True

        # Combo
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo

        # Resonance chain
        note_color = note.lane
        if self.resonance_color == note_color:
            self.resonance_count += 1
        else:
            self.resonance_color = note_color
            self.resonance_count = 1

        # Score
        base = points * 10
        multiplier = 1 + self.combo // 10
        if self.resonance_count >= CHAIN_THRESHOLD:
            multiplier *= 3
        elif self.resonance_count >= 3:
            multiplier *= 2
        self.score += base * multiplier

        # Chain clear
        if self.resonance_count >= CHAIN_THRESHOLD and self.resonance_count % CHAIN_THRESHOLD == 0:
            self._chain_clear(note_color)

        # Visual feedback
        x = float(note.lane * LANE_W + LANE_W // 2)
        self._spawn_particles(x, float(HIT_ZONE_Y), LANE_COLORS[note.lane])
        color = 5 if rating == "PERFECT" else 10  # WHITE or YELLOW
        self.texts.append(FloatingText(x, float(HIT_ZONE_Y - 10), rating, 30, color))

    def _on_miss(self, note: Note) -> None:
        """Process a missed note."""
        self.health -= 1
        self.combo = 0
        self.resonance_count = 0
        self.resonance_color = None
        x = float(note.lane * LANE_W + LANE_W // 2)
        self.texts.append(FloatingText(x, float(HIT_ZONE_Y), "MISS", 30, 8))  # RED

    def _chain_clear(self, color: int) -> None:
        """Clear all active notes of the given color for bonus."""
        cleared = 0
        for note in self.notes:
            if note.lane == color and not note.hit and not note.missed:
                note.hit = True
                cleared += 1
                x = float(note.lane * LANE_W + LANE_W // 2)
                self._spawn_particles(x, note.y, LANE_COLORS[color])
        if cleared > 0:
            self.score += cleared * 50
            self.chain_clear_count += cleared
            self.texts.append(FloatingText(
                float(SCREEN_W // 2), float(SCREEN_H // 2),
                f"CHAIN x{cleared}!", 45, 12,  # PINK
            ))

    def _spawn_particles(self, x: float, y: float, color: int) -> None:
        """Spawn a burst of particles at the given position."""
        for _ in range(8):
            angle = random.random() * math.pi * 2
            speed = random.uniform(1.0, 3.0)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 1.0,
                life=20,
                color=color,
            ))

    # ── Draw ──
    def _draw(self) -> None:
        import pyxel

        pyxel.cls(0)  # BLACK
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_playing()
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 40, 80, "RESONANCE", 13)  # CYAN
        pyxel.text(SCREEN_W // 2 - 20, 96, "CHAIN", 12)  # PINK
        pyxel.text(SCREEN_W // 2 - 50, 130, "PRESS SPACE", 5)  # WHITE
        pyxel.text(SCREEN_W // 2 - 60, 150, "Z/X/C/V to play", 7)  # GRAY

    def _draw_playing(self) -> None:
        import pyxel

        # Lane dividers
        for i in range(1, LANE_COUNT):
            x = i * LANE_W
            pyxel.line(x, 0, x, SCREEN_H, 6)  # DARK_BLUE

        # Hit zone line
        pyxel.rect(0, HIT_ZONE_Y - 2, SCREEN_W, 4, 5)  # WHITE

        # Hit zone markers
        for i in range(LANE_COUNT):
            x = i * LANE_W + LANE_W // 2
            pyxel.circ(x, HIT_ZONE_Y, 8, LANE_COLORS[i])

        # Notes
        for note in self.notes:
            if note.hit or note.missed:
                continue
            x = note.lane * LANE_W + (LANE_W - NOTE_W) // 2
            pyxel.rect(x, int(note.y) - NOTE_H // 2, NOTE_W, NOTE_H, LANE_COLORS[note.lane])

        # Particles
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

        # Floating texts
        for t in self.texts:
            pyxel.text(int(t.x) - len(t.text) * 2, int(t.y), t.text, t.color)

        # HUD
        pyxel.text(4, 4, f"SCORE {self.score}", 5)  # WHITE
        pyxel.text(4, 14, f"COMBO {self.combo}", 10)  # YELLOW
        if self.resonance_count >= 3:
            pyxel.text(4, 24, f"RESONANCE x{self.resonance_count}", 12)  # PINK

        # Health
        for i in range(self.health):
            pyxel.circ(SCREEN_W - 12 - i * 14, 10, 5, 8)  # RED

        # Lane labels
        for i in range(LANE_COUNT):
            x = i * LANE_W + LANE_W // 2 - 2
            pyxel.text(x, SCREEN_H - 12, LANE_LABELS[i], LANE_COLORS[i])

    def _draw_game_over(self) -> None:
        import pyxel

        pyxel.rect(0, SCREEN_H // 2 - 30, SCREEN_W, 60, 6)  # NAVY
        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 - 15, "GAME OVER", 8)  # RED
        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2, f"SCORE: {self.score}", 5)  # WHITE
        pyxel.text(
            SCREEN_W // 2 - 50, SCREEN_H // 2 + 15,
            f"MAX COMBO: {self.max_combo}", 10,  # YELLOW
        )
        pyxel.text(SCREEN_W // 2 - 40, SCREEN_H // 2 + 28, "PRESS SPACE", 10)


if __name__ == "__main__":
    game = Game()
    game.init_and_run()
