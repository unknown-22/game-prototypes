"""CHROMA DASH — Side-scrolling endless runner with color-match COMBO system.

Reinterpreted from game idea #1 (score 32.0): deckbuilder roguelite with
"synthesis compression" + "chain collapse UI effects" hooks, reinterpreted
into an endless runner where same-color consecutive gem collection builds
COMBO, and COMBO >= 5 triggers FLUX super-mode.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel

# ── Config ────────────────────────────────────────────────────────────────────

SCREEN_W = 240
SCREEN_H = 160
GROUND_Y = 130
PLAYER_X = 40
PLAYER_W = 14
PLAYER_H = 18
PLAYER_W_DUCK = 14
PLAYER_H_DUCK = 10
GRAVITY = 0.6
JUMP_VEL = -7.5
SPEED_BASE = 1.8
SPEED_MAX = 5.5
SPEED_INC = 0.00015  # per frame
GEM_SIZE = 8
GEM_HEIGHTS: tuple[int, int, int] = (118, 90, 60)
NUM_COLORS = 4
FLUX_THRESHOLD = 5
FLUX_DURATION = 300  # frames (5 seconds at 60fps)
FLUX_SCORE_MULT = 3
OBSTACLE_TYPES: tuple[str, str, str] = ("spike", "bar", "pit")
SPAWN_MIN_GAP = 80  # minimum pixels between spawns
COMBO_MAX_DISPLAY = 99

# Pyxel color constants — only these 16 exist in stubs:
# COLOR_BLACK=0, COLOR_NAVY=1, COLOR_PURPLE=2, COLOR_GREEN=3,
# COLOR_BROWN=4, COLOR_DARK_BLUE=5, COLOR_LIGHT_BLUE=6, COLOR_WHITE=7,
# COLOR_RED=8, COLOR_ORANGE=9, COLOR_YELLOW=10, COLOR_LIME=11,
# COLOR_CYAN=12, COLOR_GRAY=13, COLOR_PINK=14, COLOR_PEACH=15

COLOR_MAP: dict[int, int] = {
    0: pyxel.COLOR_RED,         # FIRE
    1: pyxel.COLOR_LIGHT_BLUE,  # WATER
    2: pyxel.COLOR_LIME,        # NATURE
    3: pyxel.COLOR_YELLOW,      # GOLD
}

COLOR_NAMES: dict[int, str] = {
    0: "FIRE",
    1: "WATER",
    2: "LEAF",
    3: "GOLD",
}


# ── Data Classes ──────────────────────────────────────────────────────────────


@dataclass
class Gem:
    """A collectible gem on the field."""

    x: float
    y: float
    color: int  # 0-3
    collected: bool = False
    size: int = GEM_SIZE


@dataclass
class Obstacle:
    """A hazard the player must avoid."""

    x: float
    y: float
    w: int
    h: int
    kind: str  # "spike", "bar", "pit"
    active: bool = True


@dataclass
class Particle:
    """Lightweight visual particle."""

    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


@dataclass
class FloatingText:
    """Floating score/combo text that rises and fades."""

    x: float
    y: float
    text: str
    color: int
    life: int


# ── Phase ─────────────────────────────────────────────────────────────────────


class Phase(Enum):
    PLAYING = auto()
    GAME_OVER = auto()


# ── Player ────────────────────────────────────────────────────────────────────


@dataclass
class Player:
    """Player state."""

    y: float = GROUND_Y - PLAYER_H
    vy: float = 0.0
    is_jumping: bool = False
    is_ducking: bool = False
    duck_timer: int = 0  # frames remaining in duck
    invuln_timer: int = 0  # brief invulnerability after flux ends

    @property
    def h(self) -> int:
        return PLAYER_H_DUCK if self.is_ducking else PLAYER_H

    @property
    def w(self) -> int:
        return PLAYER_W


# ── Game ──────────────────────────────────────────────────────────────────────


class Game:
    """CHROMA DASH — endless runner."""

    # Scoring constants
    SCORE_DIST_PER_FRAME: ClassVar[int] = 1
    SCORE_GEM_BASE: ClassVar[int] = 10

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CHROMA DASH", display_scale=3)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.player = Player()
        self.gems: list[Gem] = []
        self.obstacles: list[Obstacle] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.speed = SPEED_BASE
        self.scroll_x = 0.0
        self.score = 0
        self.distance = 0
        self.combo = 0
        self.last_color: int | None = None
        self.flux_timer = 0
        self.is_flux = False
        self.best_score = 0
        self.spawn_timer = 0.0
        self.ground_offset = 0.0
        self._next_spawn_x = SCREEN_W + 30.0

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_playing(self) -> None:
        # Speed ramp
        self.speed = min(SPEED_BASE + SPEED_INC * self.distance, SPEED_MAX)

        # Input
        self._update_input()

        # Player physics
        self._update_player_physics()

        # Scrolling
        self.scroll_x += self.speed
        self.distance += 1
        self.score += Game.SCORE_DIST_PER_FRAME
        self.ground_offset = (self.ground_offset + self.speed) % 16

        # Spawning
        self._update_spawning()

        # Move and cull entities
        self._update_entities()

        # Collision detection
        self._update_collisions()

        # Flux timer
        self._update_flux()

        # Player invulnerability
        if self.player.invuln_timer > 0:
            self.player.invuln_timer -= 1

        # Particles
        self._update_particles()

        # Floating texts
        self._update_floating_texts()

    def _update_input(self) -> None:
        # Duck
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            self.player.is_ducking = True
            self.player.duck_timer = 6  # brief hold
        elif self.player.duck_timer > 0:
            self.player.duck_timer -= 1
        else:
            self.player.is_ducking = False

        # Jump
        on_ground = self.player.y >= GROUND_Y - PLAYER_H
        if (pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.KEY_W)) and on_ground:
            self.player.vy = JUMP_VEL
            self.player.is_jumping = True

    def _update_player_physics(self) -> None:
        if not self.player.is_ducking:
            self.player.vy += GRAVITY
        else:
            # No gravity while ducking (stays low)
            self.player.vy = 0.0

        self.player.y += self.player.vy

        # Ground clamp
        if self.player.y >= GROUND_Y - PLAYER_H:
            self.player.y = GROUND_Y - PLAYER_H
            self.player.vy = 0.0
            self.player.is_jumping = False

        # Ceiling clamp
        if self.player.y < 0:
            self.player.y = 0
            self.player.vy = 0.0

    def _update_spawning(self) -> None:
        """Spawn gems and obstacles ahead of the player."""
        right_edge = SCREEN_W + self.scroll_x + 50
        while self._next_spawn_x < right_edge:
            self._next_spawn_x += SPAWN_MIN_GAP + random.uniform(0, 40)
            spawn_type = random.random()

            if spawn_type < 0.55:
                # Spawn gem
                height_idx = random.randint(0, 2)
                gy = GEM_HEIGHTS[height_idx]
                color = random.randint(0, NUM_COLORS - 1)
                self.gems.append(Gem(x=self._next_spawn_x, y=gy, color=color))
            elif spawn_type < 0.85:
                # Spawn obstacle
                kind = random.choice(["spike", "bar"])
                if kind == "spike":
                    self.obstacles.append(
                        Obstacle(
                            x=self._next_spawn_x,
                            y=GROUND_Y - 10,
                            w=16,
                            h=10,
                            kind="spike",
                        )
                    )
                else:  # bar
                    bar_y = GROUND_Y - 35 - random.randint(0, 15)
                    self.obstacles.append(
                        Obstacle(
                            x=self._next_spawn_x,
                            y=bar_y,
                            w=20,
                            h=12,
                            kind="bar",
                        )
                    )
            else:
                # Spawn pit
                self.obstacles.append(
                    Obstacle(
                        x=self._next_spawn_x,
                        y=GROUND_Y,
                        w=24,
                        h=30,
                        kind="pit",
                    )
                )

    def _update_entities(self) -> None:
        """Move entities left relative to scroll, cull off-screen."""
        # Gems
        self.gems = [
            g
            for g in self.gems
            if not g.collected and g.x > self.scroll_x - 20
        ]

        # Obstacles
        self.obstacles = [
            o
            for o in self.obstacles
            if o.active and o.x > self.scroll_x - 30
        ]

    def _get_player_bounds(self) -> tuple[float, float, float, float]:
        """Return player hitbox: (left, top, right, bottom)."""
        px = PLAYER_X
        py = self.player.y
        if self.player.is_ducking:
            py = GROUND_Y - PLAYER_H_DUCK
            return (px, py, px + PLAYER_W_DUCK, py + PLAYER_H_DUCK)
        return (px, py, px + PLAYER_W, py + PLAYER_H)

    def _update_collisions(self) -> None:
        """Check gem collection and obstacle collisions."""
        pl, pt, pr, pb = self._get_player_bounds()

        # Gem collection
        for gem in self.gems:
            if gem.collected:
                continue
            gx = gem.x - self.scroll_x
            # Simple distance-based collection
            gcx = gx + gem.size / 2
            gcy = gem.y + gem.size / 2
            pcx = (pl + pr) / 2
            pcy = (pt + pb) / 2
            dist = math.sqrt((gcx - pcx) ** 2 + (gcy - pcy) ** 2)
            if dist < PLAYER_W + gem.size:
                gem.collected = True
                self._on_gem_collected(gem)

        # Obstacle collisions
        for obs in self.obstacles:
            if not obs.active:
                continue
            ox = obs.x - self.scroll_x
            oy = obs.y

            if obs.kind == "pit":
                # Pit: only kill if player is on ground and over pit
                if self.player.y >= GROUND_Y - PLAYER_H and not self.player.is_jumping:
                    if pl < ox + obs.w and pr > ox:
                        if not self.player.is_ducking:
                            self._on_death()
                            return
            else:
                # Spike/bar: AABB collision
                if pl < ox + obs.w and pr > ox and pt < oy + obs.h and pb > oy:
                    self._on_death()
                    return

    def _on_gem_collected(self, gem: Gem) -> None:
        """Handle gem pickup: combo logic, score, particles."""
        # Combo logic
        if self.last_color == gem.color:
            self.combo += 1
        else:
            self.combo = 1
            self.last_color = gem.color

        # Score
        combo_mult = min(self.combo, 10)
        base = Game.SCORE_GEM_BASE
        if self.is_flux:
            base *= FLUX_SCORE_MULT
        points = base * combo_mult
        self.score += points

        # Floating text
        text = f"+{points}"
        if self.combo >= 3:
            text = f"COMBO x{combo_mult} +{points}"
        self.floating_texts.append(
            FloatingText(
                x=PLAYER_X,
                y=self.player.y - 6,
                text=text,
                color=COLOR_MAP[gem.color],
                life=30,
            )
        )

        # Particles
        for _ in range(5):
            self.particles.append(
                Particle(
                    x=gem.x - self.scroll_x,
                    y=gem.y,
                    vx=random.uniform(-1.5, 1.5),
                    vy=random.uniform(-2.0, -0.5),
                    color=COLOR_MAP[gem.color],
                    life=15,
                )
            )

        # Flux trigger
        if self.combo >= FLUX_THRESHOLD and not self.is_flux:
            self._activate_flux()

    def _activate_flux(self) -> None:
        """Activate FLUX super-mode."""
        self.is_flux = True
        self.flux_timer = FLUX_DURATION
        # Burst of particles
        for _ in range(20):
            angle = random.uniform(0, math.pi * 2)
            speed_p = random.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x=PLAYER_X + PLAYER_W // 2,
                    y=self.player.y + PLAYER_H // 2,
                    vx=math.cos(angle) * speed_p,
                    vy=math.sin(angle) * speed_p,
                    color=pyxel.COLOR_YELLOW,
                    life=20,
                )
            )
        self.floating_texts.append(
            FloatingText(
                x=PLAYER_X,
                y=self.player.y - 18,
                text="FLUX!",
                color=pyxel.COLOR_YELLOW,
                life=45,
            )
        )

    def _update_flux(self) -> None:
        """Update flux timer."""
        if self.is_flux:
            self.flux_timer -= 1
            if self.flux_timer <= 0:
                self.is_flux = False
                self.combo = 0
                self.last_color = None
                self.player.invuln_timer = 15  # brief invuln after flux ends
                self.floating_texts.append(
                    FloatingText(
                        x=PLAYER_X,
                        y=self.player.y - 18,
                        text="FLUX END",
                        color=pyxel.COLOR_GRAY,
                        life=30,
                    )
                )

    def _update_particles(self) -> None:
        """Update and cull particles."""
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1  # gravity
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        """Update and cull floating texts."""
        for ft in self.floating_texts:
            ft.y -= 0.8  # rise
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _on_death(self) -> None:
        """Handle player death."""
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score
        # Death particles
        for _ in range(15):
            self.particles.append(
                Particle(
                    x=PLAYER_X + PLAYER_W // 2,
                    y=self.player.y + PLAYER_H // 2,
                    vx=random.uniform(-3.0, 3.0),
                    vy=random.uniform(-4.0, -1.0),
                    color=pyxel.COLOR_RED,
                    life=25,
                )
            )

    def _update_game_over(self) -> None:
        """Handle game over input."""
        # Update particles even in game over
        self._update_particles()
        self._update_floating_texts()

        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_R):
            self.reset()

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        if self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_playing()
            self._draw_game_over_overlay()

    def _draw_playing(self) -> None:
        # Background stars (parallax)
        self._draw_background()

        # Ground
        self._draw_ground()

        # Gems
        self._draw_gems()

        # Obstacles
        self._draw_obstacles()

        # Player
        self._draw_player()

        # Particles
        self._draw_particles()

        # Floating texts
        self._draw_floating_texts()

        # HUD
        self._draw_hud()

    def _draw_background(self) -> None:
        """Draw parallax starfield background."""
        for i in range(20):
            # Deterministic star positions based on index
            sx = (i * 47 + 13) % SCREEN_W
            sy = (i * 31 + 7) % (GROUND_Y - 10)
            # Scroll with parallax (slower than foreground)
            px = (sx - (self.scroll_x * 0.2) % SCREEN_W) % SCREEN_W
            bright = (i % 3 == 0)
            col = pyxel.COLOR_WHITE if bright else pyxel.COLOR_GRAY
            pyxel.pset(int(px), sy, col)

    def _draw_ground(self) -> None:
        """Draw scrolling ground with pattern."""
        # Ground fill
        pyxel.rect(0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y, pyxel.COLOR_BROWN)
        # Top edge line
        pyxel.line(0, GROUND_Y, SCREEN_W, GROUND_Y, pyxel.COLOR_WHITE)

        # Scrolling hash marks on ground
        mark_spacing = 24
        start_offset = int(self.ground_offset) % mark_spacing
        for x in range(-start_offset, SCREEN_W, mark_spacing):
            pyxel.line(x, GROUND_Y + 4, x + 4, GROUND_Y + 4, pyxel.COLOR_ORANGE)
            pyxel.line(x + 8, GROUND_Y + 8, x + 14, GROUND_Y + 8, pyxel.COLOR_ORANGE)

    def _draw_gems(self) -> None:
        """Draw all uncollected gems."""
        for gem in self.gems:
            if gem.collected:
                continue
            gx = int(gem.x - self.scroll_x)
            if gx < -GEM_SIZE or gx > SCREEN_W + GEM_SIZE:
                continue
            gy = int(gem.y)

            # Glow effect in flux mode
            if self.is_flux and pyxel.frame_count % 4 < 2:
                pyxel.circb(gx + gem.size // 2, gy + gem.size // 2, gem.size + 3, pyxel.COLOR_YELLOW)

            # Gem body
            col = COLOR_MAP[gem.color]
            pyxel.rect(gx, gy, gem.size, gem.size, col)
            # Highlight
            pyxel.rect(gx + 1, gy + 1, gem.size - 3, gem.size - 3, pyxel.COLOR_WHITE)
            # Center dot
            pyxel.pset(gx + gem.size // 2, gy + gem.size // 2, col)

    def _draw_obstacles(self) -> None:
        """Draw all obstacles."""
        for obs in self.obstacles:
            if not obs.active:
                continue
            ox = int(obs.x - self.scroll_x)
            if ox < -obs.w or ox > SCREEN_W + obs.w:
                continue
            oy = int(obs.y)

            if obs.kind == "spike":
                # Triangle spike on ground
                pyxel.tri(
                    ox, oy + obs.h,
                    ox + obs.w // 2, oy,
                    ox + obs.w, oy + obs.h,
                    pyxel.COLOR_RED,
                )
                # Outline
                pyxel.trib(
                    ox, oy + obs.h,
                    ox + obs.w // 2, oy,
                    ox + obs.w, oy + obs.h,
                    pyxel.COLOR_WHITE,
                )
            elif obs.kind == "bar":
                # Floating horizontal bar
                pyxel.rect(ox, oy, obs.w, obs.h, pyxel.COLOR_PURPLE)
                pyxel.rectb(ox, oy, obs.w, obs.h, pyxel.COLOR_WHITE)
            elif obs.kind == "pit":
                # Gap in ground
                pyxel.rect(ox, oy, obs.w, obs.h, pyxel.COLOR_BLACK)
                # Warning edges
                pyxel.line(ox, oy, ox + obs.w, oy, pyxel.COLOR_RED)
                pyxel.line(ox, oy + obs.h, ox + obs.w, oy + obs.h, pyxel.COLOR_RED)

    def _draw_player(self) -> None:
        """Draw the player character."""
        px = PLAYER_X
        py = int(self.player.y)

        # Invulnerability blink
        if self.player.invuln_timer > 0 and pyxel.frame_count % 4 < 2:
            return

        if self.player.is_ducking:
            py = GROUND_Y - PLAYER_H_DUCK
            w = PLAYER_W_DUCK
            h = PLAYER_H_DUCK
        else:
            w = PLAYER_W
            h = PLAYER_H

        # Body color based on flux state
        body_col = pyxel.COLOR_WHITE
        if self.is_flux:
            # Rainbow cycling
            flux_cycle = (pyxel.frame_count // 4) % NUM_COLORS
            body_col = COLOR_MAP[flux_cycle]
        elif self.last_color is not None:
            body_col = COLOR_MAP[self.last_color]

        # Body
        pyxel.rect(px, py, w, h, body_col)
        # Outline
        pyxel.rectb(px, py, w, h, pyxel.COLOR_BLACK)

        # Eye
        eye_x = px + w - 5
        eye_y = py + 3
        if self.player.is_ducking:
            eye_x = px + w - 4
            eye_y = py + 1
        pyxel.pset(eye_x, eye_y, pyxel.COLOR_BLACK)

        # Flux aura
        if self.is_flux and pyxel.frame_count % 3 == 0:
            pyxel.circb(px + w // 2, py + h // 2, max(w, h) + 2, pyxel.COLOR_YELLOW)

    def _draw_particles(self) -> None:
        """Draw all particles."""
        for p in self.particles:
            alpha = p.life / 25
            col = p.color if alpha > 0.5 else pyxel.COLOR_GRAY
            pyxel.pset(int(p.x), int(p.y), col)

    def _draw_floating_texts(self) -> None:
        """Draw all floating texts."""
        for ft in self.floating_texts:
            alpha = ft.life / 45
            col = ft.color if alpha > 0.4 else pyxel.COLOR_GRAY
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, col)

    def _draw_hud(self) -> None:
        """Draw heads-up display."""
        # Score
        pyxel.text(4, 2, f"SCORE:{self.score:06d}", pyxel.COLOR_WHITE)
        pyxel.text(4, 9, f"BEST:{self.best_score:06d}", pyxel.COLOR_GRAY)

        # Combo
        combo_text = f"COMBO x{min(self.combo, COMBO_MAX_DISPLAY)}"
        combo_col = pyxel.COLOR_WHITE
        if self.combo >= 5:
            combo_col = pyxel.COLOR_ORANGE
        if self.combo >= 10:
            combo_col = pyxel.COLOR_RED
        pyxel.text(SCREEN_W - len(combo_text) * 4 - 4, 2, combo_text, combo_col)

        # Flux gauge
        if self.is_flux:
            bar_w = 50
            bar_x = SCREEN_W - bar_w - 4
            bar_y = 10
            fill = int(bar_w * self.flux_timer / FLUX_DURATION)
            pyxel.rect(bar_x, bar_y, bar_w, 4, pyxel.COLOR_GRAY)
            pyxel.rect(bar_x, bar_y, fill, 4, pyxel.COLOR_YELLOW)
            pyxel.text(bar_x - 18, bar_y, "FLUX", pyxel.COLOR_YELLOW)

        # Last color indicator
        if self.last_color is not None:
            indicator_x = SCREEN_W - 14
            indicator_y = 18
            pyxel.rect(indicator_x, indicator_y, 8, 8, COLOR_MAP[self.last_color])
            pyxel.rectb(indicator_x, indicator_y, 8, 8, pyxel.COLOR_WHITE)
            pyxel.text(indicator_x - 16, indicator_y, "COL:", pyxel.COLOR_GRAY)

        # Speed indicator
        speed_pct = int((self.speed - SPEED_BASE) / (SPEED_MAX - SPEED_BASE) * 100)
        pyxel.text(4, SCREEN_H - 10, f"SPD:{speed_pct:03d}%", pyxel.COLOR_GRAY)

    def _draw_game_over_overlay(self) -> None:
        """Draw game over screen."""
        # Semi-transparent overlay (checkerboard pattern)
        for y in range(0, SCREEN_H, 4):
            for x in range((y // 4) % 2, SCREEN_W, 4):
                pyxel.pset(x, y, pyxel.COLOR_BLACK)

        # Game over text
        go_text = "GAME OVER"
        tx = (SCREEN_W - len(go_text) * 4) // 2
        pyxel.text(tx, 55, go_text, pyxel.COLOR_RED)

        # Score display
        score_text = f"SCORE: {self.score}"
        tx = (SCREEN_W - len(score_text) * 4) // 2
        pyxel.text(tx, 70, score_text, pyxel.COLOR_WHITE)

        best_text = f"BEST:  {self.best_score}"
        tx = (SCREEN_W - len(best_text) * 4) // 2
        pyxel.text(tx, 80, best_text, pyxel.COLOR_YELLOW)

        # New best indicator
        if self.score >= self.best_score and self.score > 0:
            nb_text = "NEW BEST!"
            tx = (SCREEN_W - len(nb_text) * 4) // 2
            pyxel.text(tx, 90, nb_text, pyxel.COLOR_ORANGE)

        # Restart prompt
        restart_text = "PRESS SPACE TO RETRY"
        tx = (SCREEN_W - len(restart_text) * 4) // 2
        if pyxel.frame_count % 60 < 40:
            pyxel.text(tx, 110, restart_text, pyxel.COLOR_WHITE)


# ── Launcher ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    Game()
