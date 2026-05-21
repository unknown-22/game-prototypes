"""SPLIT SURGE — Zuma-style marble chain shooter.

Reinterpreted from game_idea_factory #1 (Score 32.0):
  - "split→converge" hook → matching 3+ splits the chain; same-color
    segment ends that touch reconverge for COMBO chain reactions.
  - "synthesis compression" hook → consecutive same-color matches
    build COMBO; COMBO >= 3 unlocks SUPER SHOT (rainbow marble).

Core loop: aim cannon → shoot colored marble → match 3+ to pop →
chain splits. If split ends reconverge with same color → COMBO SURGE.
Clear all marbles to advance to faster, longer waves.

Controls:
  Mouse aim + click to shoot
  Keys 1-4 or scroll wheel to change active color
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ══════════════════════════════════════════════════════════════════════════════
# Config
# ══════════════════════════════════════════════════════════════════════════════
WIDTH = 256
HEIGHT = 256
CENTER_X = 128
CENTER_Y = 128

# Path
OUTER_R = 108
INNER_R = 20
TURNS = 4
START_ANGLE = -math.pi / 2
PATH_POINTS = 600  # discrete path steps

# Marbles
MARBLE_RADIUS = 6
CHAIN_SPEED = 0.25  # path_idx units per frame (base)
SPEED_PER_WAVE = 0.03  # extra speed per wave
SPAWN_INTERVAL = 100  # frames between new marble spawns (base)
SPAWN_DECREASE = 5  # fewer frames between spawns per wave
NUM_COLORS = 4  # red, green, blue, yellow

# Color palette (pyxel color indices)
COLOR_VALS: tuple[int, ...] = (8, 11, 5, 10)  # RED, GREEN, DARK_BLUE, YELLOW
COLOR_NAMES: tuple[str, ...] = ("RED", "GRN", "BLU", "YLW")
COLOR_DARK: tuple[int, ...] = (4, 3, 1, 9)  # darker shades for outline

# Match
MATCH_MIN = 3
COMBO_SUPER_THRESHOLD = 3  # consecutive matches for SUPER SHOT

# Shot
SHOT_SPEED = 5.0
SHOT_RADIUS = 4
CANNON_LENGTH = 14

# Score
BASE_SCORE = 10
COMBO_MULTIPLIER = 1.5  # score *= COMBO * this
RECONVERGE_BONUS = 50

# UI
UI_COLOR = 7  # WHITE/LIGHT_BLUE


# ══════════════════════════════════════════════════════════════════════════════
# Phase enum
# ══════════════════════════════════════════════════════════════════════════════
class Phase(Enum):
    PLAYING = auto()
    STAGE_CLEAR = auto()
    GAME_OVER = auto()


# ══════════════════════════════════════════════════════════════════════════════
# Data classes
# ══════════════════════════════════════════════════════════════════════════════
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


@dataclass
class ShotMarble:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    alive: bool = True


# ══════════════════════════════════════════════════════════════════════════════
# Game
# ══════════════════════════════════════════════════════════════════════════════
class Game:
    def __init__(self) -> None:
        pyxel.init(WIDTH, HEIGHT, title="SPLIT SURGE", display_scale=2)
        self._build_path()
        self.reset()
        pyxel.run(self.update, self.draw)

    def _build_path(self) -> None:
        """Precompute spiral path points."""
        self.path: list[tuple[float, float]] = []
        for i in range(PATH_POINTS + 1):
            t = i / PATH_POINTS
            r = OUTER_R - (OUTER_R - INNER_R) * t
            angle = START_ANGLE + t * TURNS * 2 * math.pi
            self.path.append((
                CENTER_X + r * math.cos(angle),
                CENTER_Y + r * math.sin(angle),
            ))

    def _path_pos(self, idx: float) -> tuple[float, float]:
        """Interpolate position along discrete path."""
        idx = max(0.0, min(float(PATH_POINTS), idx))
        i0 = int(idx)
        i1 = min(i0 + 1, PATH_POINTS)
        frac = idx - i0
        p0 = self.path[i0]
        p1 = self.path[i1]
        return (
            p0[0] + (p1[0] - p0[0]) * frac,
            p0[1] + (p1[1] - p0[1]) * frac,
        )

    def reset(self) -> None:
        """Initialize / reset game state."""
        self._rng = random.Random()
        self.phase: Phase = Phase.PLAYING
        self.wave: int = 1
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.active_color: int = 0  # index into COLOR_VALS
        self.shot: ShotMarble | None = None
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._spawn_timer: int = 0
        self._flash_timer: int = 0
        self._stage_clear_timer: int = 0

        # Marble chain: (path_idx, color_index)
        self.marbles: list[tuple[float, int]] = []

        # Seed the chain with initial marbles
        self._init_chain()

    def _init_chain(self) -> None:
        """Fill chain with initial marbles."""
        count = 15 + self.wave * 3
        for i in range(count):
            col = self._rng.randint(0, NUM_COLORS - 1)
            # Place marbles with spacing, starting from outside
            idx = -float(i) * 15.0
            self.marbles.append((idx, col))
        # Sort by position (closest to 0 first)
        self.marbles.sort(key=lambda m: m[0])

    @property
    def _speed(self) -> float:
        return CHAIN_SPEED + SPEED_PER_WAVE * (self.wave - 1)

    @property
    def _spawn_interval(self) -> int:
        return max(40, SPAWN_INTERVAL - SPAWN_DECREASE * (self.wave - 1))

    # ══════════════════════════════════════════════════════════════════════════
    # Update
    # ══════════════════════════════════════════════════════════════════════════
    def update(self) -> None:
        if self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.STAGE_CLEAR:
            self._update_stage_clear()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

        self._update_particles_and_texts()

    def _update_playing(self) -> None:
        # Color selection
        self._update_color_input()

        # Cannon + shooting
        self._update_cannon()

        # Shot marble movement
        self._update_shot()

        # Chain movement
        self._update_chain()

        # Spawn new marbles
        self._spawn_marbles()

        # Check game over
        if self.marbles and self.marbles[-1][0] >= PATH_POINTS:
            self.phase = Phase.GAME_OVER

        # Check stage clear
        if not self.marbles:
            self._flash_timer = 15
            self.phase = Phase.STAGE_CLEAR
            self._stage_clear_timer = 60

    def _update_color_input(self) -> None:
        """Handle color selection via keys or scroll."""
        for i in range(NUM_COLORS):
            if pyxel.btnp(getattr(pyxel, f"KEY_{i + 1}")):
                self.active_color = i
        # Scroll wheel
        mw = pyxel.mouse_wheel
        if mw > 0:
            self.active_color = (self.active_color - 1) % NUM_COLORS
        elif mw < 0:
            self.active_color = (self.active_color + 1) % NUM_COLORS

    def _update_cannon(self) -> None:
        """Handle shooting input."""
        if self.shot is not None:
            return  # shot already in flight

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            dx = pyxel.mouse_x - CENTER_X
            dy = pyxel.mouse_y - CENTER_Y
            dist = math.hypot(dx, dy)
            if dist < 1:
                dx, dy = 1.0, 0.0
                dist = 1.0
            vx = dx / dist * SHOT_SPEED
            vy = dy / dist * SHOT_SPEED
            # Spawn shot from just outside cannon
            sx = CENTER_X + vx / SHOT_SPEED * CANNON_LENGTH
            sy = CENTER_Y + vy / SHOT_SPEED * CANNON_LENGTH
            color = COLOR_VALS[self.active_color]
            self.shot = ShotMarble(sx, sy, vx, vy, color)

    def _update_shot(self) -> None:
        """Move shot marble and check collision with chain."""
        if self.shot is None or not self.shot.alive:
            self.shot = None
            return

        s = self.shot
        s.x += s.vx
        s.y += s.vy

        # Out of bounds → expire
        if s.x < -20 or s.x > WIDTH + 20 or s.y < -20 or s.y > HEIGHT + 20:
            s.alive = False
            self.shot = None
            return

        # Check collision with any marble in the chain
        hit_idx = -1
        for i, (m_idx, _) in enumerate(self.marbles):
            mx, my = self._path_pos(m_idx)
            if math.hypot(s.x - mx, s.y - my) < MARBLE_RADIUS + SHOT_RADIUS:
                hit_idx = i
                break

        if hit_idx >= 0:
            # Insert this color at the collision point
            self._insert_marble(hit_idx, self.active_color)
            s.alive = False
            self.shot = None

    def _update_chain(self) -> None:
        """Move all marbles along the path."""
        speed = self._speed
        for i in range(len(self.marbles)):
            idx, col = self.marbles[i]
            self.marbles[i] = (idx + speed, col)

    def _spawn_marbles(self) -> None:
        """Periodically add new marbles at the back of the chain."""
        self._spawn_timer += 1
        if self._spawn_timer >= self._spawn_interval:
            self._spawn_timer = 0
            col = self._rng.randint(0, NUM_COLORS - 1)
            # Place at the beginning of the chain
            if self.marbles:
                first_idx = self.marbles[0][0]
                new_idx = max(-50.0, first_idx - 18.0)
            else:
                new_idx = -50.0
            self.marbles.insert(0, (new_idx, col))

    def _insert_marble(self, pos: int, color_idx: int) -> None:
        """Insert a marble at the given position in the chain and check matches."""
        if not self.marbles:
            return

        # Determine insertion index
        m_idx, _ = self.marbles[pos]
        new_m_idx = m_idx
        insert_at = pos

        # Place the new marble
        self.marbles.insert(insert_at, (new_m_idx, color_idx))

        # Check for matches and reconverge
        self._check_matches()

    def _check_matches(self) -> None:
        """Find and pop matching groups, handling reconverge chains."""
        while True:
            # Find the first group of MATCH_MIN+ same-color consecutive marbles
            match_start = -1
            match_end = -1

            current_color: int | None = None
            run_start = 0
            for i, (_, col) in enumerate(self.marbles):
                if col != current_color:
                    # End of previous run
                    if current_color is not None and i - run_start >= MATCH_MIN:
                        match_start = run_start
                        match_end = i
                        break
                    current_color = col
                    run_start = i

            # Check final run
            if match_start < 0 and current_color is not None:
                run_len = len(self.marbles) - run_start
                if run_len >= MATCH_MIN:
                    match_start = run_start
                    match_end = len(self.marbles)

            if match_start < 0:
                # No more matches → check reconverge
                if self._check_reconverge():
                    continue  # reconverge triggered, re-scan for matches
                break  # done

            # Pop the matched group
            popped = self.marbles[match_start:match_end]
            popped_count = len(popped)
            popped_color = popped[0][1]
            self.marbles = self.marbles[:match_start] + self.marbles[match_end:]

            # Score
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            points = int(BASE_SCORE * popped_count * (1 + self.combo * COMBO_MULTIPLIER))
            self.score += points

            # Particles at popped positions
            for _, (m_idx, _) in enumerate(popped):
                px, py = self._path_pos(m_idx)
                for _ in range(4):
                    angle = random.random() * 2 * math.pi
                    speed = random.random() * 3 + 1
                    self.particles.append(Particle(
                        px, py,
                        math.cos(angle) * speed,
                        math.sin(angle) * speed,
                        15 + random.randint(0, 10),
                        COLOR_VALS[popped_color],
                    ))

            # Floating text
            if popped:
                px, py = self._path_pos(popped[0][0])
                txt = f"{popped_count}x{points:+}"
                self.floating_texts.append(FloatingText(px, py - 8, txt, 40, UI_COLOR))

            if not self.marbles:
                return  # stage clear

            # After popping, continue loop to check if new matches appeared

    def _check_reconverge(self) -> bool:
        """Check if adjacent marbles on either side of a gap share the same color.

        Returns True if reconverge triggered (chain re-scanned for matches).
        """
        if len(self.marbles) < 2:
            return False

        # Check every adjacent pair for same-color reconverge
        to_pop: set[int] = set()
        i = 0
        while i < len(self.marbles) - 1:
            _, c1 = self.marbles[i]
            _, c2 = self.marbles[i + 1]
            if c1 == c2:
                # Found reconverge pair — expand to include all adjacent
                # same-color marbles on both sides
                left = i
                while left > 0 and self.marbles[left - 1][1] == c1:
                    left -= 1
                right = i + 1
                while right < len(self.marbles) - 1 and self.marbles[right + 1][1] == c1:
                    right += 1
                # Only trigger if at least one side is a multi-marble group
                # (to avoid trivial 1+1 merges that would fire constantly)
                span = right - left + 1
                if span >= MATCH_MIN:
                    for j in range(left, right + 1):
                        to_pop.add(j)
                i = right + 1
            else:
                i += 1

        if to_pop:
            # Pop reconverged marbles
            sorted_indices = sorted(to_pop, reverse=True)
            popped: list[tuple[float, int]] = []
            for idx in sorted_indices:
                popped.append(self.marbles.pop(idx))

            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            bonus = RECONVERGE_BONUS * self.combo
            self.score += bonus

            # Particles
            for m_idx, col in popped:
                px, py = self._path_pos(m_idx)
                for _ in range(6):
                    angle = random.random() * 2 * math.pi
                    speed = random.random() * 4 + 1
                    self.particles.append(Particle(
                        px, py,
                        math.cos(angle) * speed,
                        math.sin(angle) * speed,
                        20 + random.randint(0, 10),
                        COLOR_VALS[col],
                    ))

            # Floating text
            if popped:
                px, py = self._path_pos(popped[0][0])
                self.floating_texts.append(FloatingText(
                    px, py - 8, f"SURGE! +{bonus}", 40, pyxel.COLOR_YELLOW,
                ))

            return True

        # No reconverge found → reset combo
        self.combo = 0
        return False

    def _update_stage_clear(self) -> None:
        self._stage_clear_timer -= 1
        if self._stage_clear_timer <= 0:
            self.wave += 1
            self.combo = 0
            self.marbles.clear()
            self.particles.clear()
            self.floating_texts.clear()
            self.shot = None
            self._spawn_timer = 0
            self.phase = Phase.PLAYING
            self._init_chain()

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_1):
            self.reset()

    def _update_particles_and_texts(self) -> None:
        # Particles
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vx *= 0.95
            p.vy *= 0.95
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

        # Floating texts
        for ft in self.floating_texts[:]:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    # ══════════════════════════════════════════════════════════════════════════
    # Draw
    # ══════════════════════════════════════════════════════════════════════════
    def draw(self) -> None:
        pyxel.cls(0)

        # Flash background on stage clear
        if self._flash_timer > 0:
            flash_col = pyxel.COLOR_WHITE if self._flash_timer % 4 < 2 else 0
            if flash_col != 0:
                pyxel.cls(flash_col)
            self._flash_timer -= 1

        # Draw path trace (subtle)
        self._draw_path()

        # Draw marbles
        self._draw_marbles()

        # Draw shot marble
        self._draw_shot()

        # Draw cannon
        self._draw_cannon()

        # Draw particles
        self._draw_particles()

        # Draw floating texts
        self._draw_floating_texts()

        # Draw UI
        self._draw_ui()

        # Draw overlays
        if self.phase == Phase.STAGE_CLEAR:
            self._draw_stage_clear_overlay()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over_overlay()

    def _draw_path(self) -> None:
        """Draw subtle path indicators."""
        for i in range(0, PATH_POINTS, 40):
            x, y = self.path[i]
            pyxel.circb(int(x), int(y), 3, 5)  # dark blue dots

    def _draw_marbles(self) -> None:
        # Draw from back to front (drawn later = on top)
        for m_idx, col_idx in self.marbles:
            x, y = self._path_pos(m_idx)
            ix, iy = int(x), int(y)
            color = COLOR_VALS[col_idx % NUM_COLORS]
            dark = COLOR_DARK[col_idx % NUM_COLORS]
            # Shadow
            pyxel.circ(ix + 1, iy + 1, MARBLE_RADIUS, dark)
            # Body
            pyxel.circ(ix, iy, MARBLE_RADIUS, color)
            # Highlight
            pyxel.circ(ix - 1, iy - 1, MARBLE_RADIUS - 3, pyxel.COLOR_WHITE)
            # Outline
            pyxel.circb(ix, iy, MARBLE_RADIUS, dark)

    def _draw_shot(self) -> None:
        if self.shot is None or not self.shot.alive:
            return
        s = self.shot
        ix, iy = int(s.x), int(s.y)
        pyxel.circ(ix, iy, SHOT_RADIUS, s.color)
        pyxel.circb(ix, iy, SHOT_RADIUS, 0)

    def _draw_cannon(self) -> None:
        """Draw cannon at center, pointing toward mouse."""
        # Compute aim direction
        dx = pyxel.mouse_x - CENTER_X
        dy = pyxel.mouse_y - CENTER_Y
        dist = math.hypot(dx, dy)
        if dist < 1:
            dx, dy = 0.0, -1.0
            dist = 1.0
        ndx = dx / dist
        ndy = dy / dist

        # Cannon barrel
        bx = CENTER_X + ndx * CANNON_LENGTH
        by = CENTER_Y + ndy * CANNON_LENGTH
        pyxel.line(CENTER_X, CENTER_Y, int(bx), int(by), pyxel.COLOR_GRAY)

        # Cannon base
        pyxel.circ(CENTER_X, CENTER_Y, 8, pyxel.COLOR_GRAY)
        pyxel.circb(CENTER_X, CENTER_Y, 8, pyxel.COLOR_WHITE)

        # Active color indicator
        active_col = COLOR_VALS[self.active_color]
        pyxel.circ(CENTER_X, CENTER_Y, 4, active_col)
        pyxel.circb(CENTER_X, CENTER_Y, 4, pyxel.COLOR_WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = max(0, min(255, p.life * 15))
            if alpha > 100:
                pyxel.circ(int(p.x), int(p.y), 2, p.color)
            else:
                pyxel.circ(int(p.x), int(p.y), 1, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_ui(self) -> None:
        # Score (top-left)
        pyxel.text(4, 4, f"SCORE:{self.score:06d}", UI_COLOR)
        # Wave (top-right)
        wave_text = f"WAVE:{self.wave}"
        pyxel.text(WIDTH - len(wave_text) * 4 - 4, 4, wave_text, UI_COLOR)
        # Combo (top-center)
        if self.combo > 0:
            combo_text = f"COMBO x{self.combo}"
            pyxel.text(CENTER_X - len(combo_text) * 2, 4, combo_text, pyxel.COLOR_YELLOW)
        # Max combo
        maxc_text = f"MAX:{self.max_combo}"
        pyxel.text(4, 12, maxc_text, pyxel.COLOR_GRAY)
        # Active color hint (bottom-center)
        hint_text = f"[{COLOR_NAMES[self.active_color]}] 1-4/WHEEL"
        pyxel.text(CENTER_X - len(hint_text) * 2, HEIGHT - 10, hint_text, UI_COLOR)

    def _draw_stage_clear_overlay(self) -> None:
        msg = f"STAGE {self.wave} CLEAR!"
        pyxel.text(CENTER_X - len(msg) * 2, CENTER_Y - 8, msg, pyxel.COLOR_YELLOW)
        nxt = f"NEXT WAVE IN {self._stage_clear_timer // 30 + 1}"
        pyxel.text(CENTER_X - len(nxt) * 2, CENTER_Y + 8, nxt, UI_COLOR)

    def _draw_game_over_overlay(self) -> None:
        # Dim background
        pyxel.rect(0, 0, WIDTH, HEIGHT, 0)
        # Draw path + marbles underneath
        self._draw_path()
        self._draw_marbles()
        self._draw_cannon()
        self._draw_particles()
        self._draw_floating_texts()
        # Overlay
        pyxel.rect(0, CENTER_Y - 30, WIDTH, 60, 0)
        pyxel.rectb(0, CENTER_Y - 30, WIDTH, 60, UI_COLOR)
        msg = "GAME OVER"
        pyxel.text(CENTER_X - len(msg) * 2, CENTER_Y - 20, msg, pyxel.COLOR_RED)
        sc_msg = f"SCORE: {self.score:06d}"
        pyxel.text(CENTER_X - len(sc_msg) * 2, CENTER_Y - 8, sc_msg, UI_COLOR)
        wv_msg = f"WAVE: {self.wave}  MAX COMBO: {self.max_combo}"
        pyxel.text(CENTER_X - len(wv_msg) * 2, CENTER_Y + 4, wv_msg, pyxel.COLOR_GRAY)
        restart_msg = "CLICK or 1 to restart"
        pyxel.text(CENTER_X - len(restart_msg) * 2, CENTER_Y + 16, restart_msg, UI_COLOR)


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    Game()
