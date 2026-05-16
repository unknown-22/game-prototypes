"""034_hook_chain — Color-match fishing combo game.

Reinterpreted from game_idea_factory idea #1 (score 32.0):
  "Synthesis compression" → same-color catches build COMBO → SUPER CATCH
  "Chain visualization" → combo meter grows, particles fly on each catch

Core mechanic: Time your strike to catch same-colored fish consecutively.
Combo 3+ unlocks SUPER mode (rainbow hook, auto-catch all nearby fish).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ────────────────────────────────────────────────────────────
SCREEN_W = 256
SCREEN_H = 240
FPS = 60
GAME_DURATION = 90  # seconds
HOOK_X = 200  # hook horizontal position
HOOK_RADIUS = 12
CATCH_RANGE = 50  # max distance to catch a fish
SUPER_COMBO_THRESHOLD = 3  # combo needed for SUPER mode
SUPER_DURATION = 300  # frames (5 seconds)
MEGA_COMBO_THRESHOLD = 6
HEAT_PER_CAST = 14
HEAT_MAX = 100
HEAT_COOLDOWN_FRAMES = 120  # 2 seconds
HEAT_REGEN_RATE = 0.3  # per frame
FISH_MAX = 12
SPAWN_INTERVAL_BASE = 60  # frames between spawns
HOOK_SPEED = 2.5

# Colors
COLOR_NAMES = ["RED", "BLUE", "GREEN", "YELLOW"]
COLOR_VALS = [pyxel.COLOR_RED, pyxel.COLOR_DARK_BLUE, pyxel.COLOR_GREEN, pyxel.COLOR_YELLOW]
NUM_COLORS = len(COLOR_NAMES)

# ── Enums ────────────────────────────────────────────────────────────────
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()

# ── Data Classes ─────────────────────────────────────────────────────────
@dataclass
class Fish:
    x: float
    y: float
    color: int  # 0-3 index
    vx: float
    vy: float = 0.0
    alive: bool = True
    size: int = 6
    golden: bool = False

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
class FloatText:
    x: float
    y: float
    text: str
    life: int
    color: int
    vy: float = -1.5

# ── Game ─────────────────────────────────────────────────────────────────
class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="HOOK CHAIN", fps=FPS, display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.hook_color = 0  # current target color
        self.hook_y = SCREEN_H // 2
        self.heat = 0.0
        self.heat_cooldown = 0
        self.super_mode = 0  # frames remaining in super mode
        self.game_timer = GAME_DURATION * FPS
        self.spawn_timer = 0
        self.spawn_interval = SPAWN_INTERVAL_BASE
        self.highest_combo = 0
        self.fish: list[Fish] = []
        self.particles: list[Particle] = []
        self.floats: list[FloatText] = []
        self.frame = 0
        self.catches = 0
        self.misses = 0
        self.water_offset = 0.0  # water shimmer
        self.title_blink = 0

    # ── Update ──────────────────────────────────────────────────────────
    def update(self) -> None:
        self.frame += 1
        self.water_offset += 0.03

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        self.title_blink += 1
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._start_game()

    def _start_game(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.hook_color = random.randrange(NUM_COLORS)
        self.hook_y = SCREEN_H // 2
        self.heat = 0.0
        self.heat_cooldown = 0
        self.super_mode = 0
        self.game_timer = GAME_DURATION * FPS
        self.spawn_timer = 0
        self.spawn_interval = SPAWN_INTERVAL_BASE
        self.highest_combo = 0
        self.fish.clear()
        self.particles.clear()
        self.floats.clear()
        self.catches = 0
        self.misses = 0
        # Spawn initial fish
        for _ in range(6):
            self._spawn_fish()

    def _update_playing(self) -> None:
        self.game_timer -= 1
        if self.game_timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        # Super mode countdown
        if self.super_mode > 0:
            self.super_mode -= 1

        # Heat regeneration
        if self.heat_cooldown > 0:
            self.heat_cooldown -= 1
        else:
            self.heat = max(0.0, self.heat - HEAT_REGEN_RATE)

        # Hook movement
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            self.hook_y = max(40, self.hook_y - HOOK_SPEED)
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            self.hook_y = min(215, self.hook_y + HOOK_SPEED)

        # Color selection
        if pyxel.btnp(pyxel.KEY_1):
            self.hook_color = 0
        if pyxel.btnp(pyxel.KEY_2):
            self.hook_color = 1
        if pyxel.btnp(pyxel.KEY_3):
            self.hook_color = 2
        if pyxel.btnp(pyxel.KEY_4):
            self.hook_color = 3
        # Scroll wheel to cycle colors
        mw = pyxel.mouse_wheel
        if mw != 0:
            self.hook_color = (self.hook_color + (1 if mw > 0 else -1)) % NUM_COLORS

        # Catch attempt
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_Z):
            self._attempt_catch()

        # Update fish
        self._update_fish()

        # Spawn new fish
        self._update_spawn()

        # Difficulty scaling
        elapsed = GAME_DURATION * FPS - self.game_timer
        self.spawn_interval = max(20, SPAWN_INTERVAL_BASE - elapsed // 300)

        # Update particles
        self._update_particles()

        # Update floating text
        self._update_floats()

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_R) or pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._start_game()

    def _attempt_catch(self) -> None:
        """Try to catch the nearest fish within range."""
        if self.heat_cooldown > 0:
            return  # overheated, can't cast

        self.heat += HEAT_PER_CAST
        if self.heat >= HEAT_MAX:
            self.heat = HEAT_MAX
            self.heat_cooldown = HEAT_COOLDOWN_FRAMES
            self._spawn_particles(HOOK_X, self.hook_y, pyxel.COLOR_ORANGE, 8)
            self._add_float(HOOK_X, self.hook_y - 10, "OVERHEAT!", pyxel.COLOR_ORANGE)
            return

        # Find nearest fish within range
        nearest: Fish | None = None
        nearest_dist = CATCH_RANGE
        for f in self.fish:
            if not f.alive:
                continue
            dx = f.x - HOOK_X
            dy = f.y - self.hook_y
            dist = math.hypot(dx, dy)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = f

        if nearest is None:
            self.misses += 1
            self.combo = 0
            self.super_mode = 0
            self._add_float(HOOK_X, self.hook_y - 10, "MISS", pyxel.COLOR_GRAY)
            self._spawn_particles(HOOK_X, self.hook_y, pyxel.COLOR_WHITE, 3)
            return

        # Catch the fish
        nearest.alive = False
        self.catches += 1

        if self.super_mode > 0:
            # Super mode: catch is always successful, counts for combo
            self.combo += 1
            earned = 200 * min(self.combo, 5)
            self.score += earned
            self._add_float(nearest.x, nearest.y, f"+{earned}", pyxel.COLOR_YELLOW)
            self._spawn_particles(nearest.x, nearest.y, COLOR_VALS[nearest.color], 6)
            # Auto-catch all fish of the same color
            self._auto_catch_color(nearest.color)
        elif nearest.color == self.hook_color:
            # Matching color → combo!
            self.combo += 1
            multiplier = 1 + (self.combo - 1) * 0.5
            earned = int(100 * multiplier)
            if nearest.golden:
                earned *= 2
            self.score += earned
            self._add_float(nearest.x, nearest.y, f"+{earned}", COLOR_VALS[nearest.color])
            self._spawn_particles(nearest.x, nearest.y, COLOR_VALS[nearest.color], 5)
            self.highest_combo = max(self.highest_combo, self.combo)

            # Check super threshold
            if self.combo >= MEGA_COMBO_THRESHOLD:
                self.super_mode = SUPER_DURATION * 2
                self._add_float(HOOK_X, 20, "MEGA SUPER!!", pyxel.COLOR_YELLOW)
                self._spawn_particles(HOOK_X, 30, pyxel.COLOR_YELLOW, 15)
            elif self.combo >= SUPER_COMBO_THRESHOLD and self.super_mode == 0:
                self.super_mode = SUPER_DURATION
                self._add_float(HOOK_X, 20, "SUPER!!", pyxel.COLOR_PINK)
                self._spawn_particles(HOOK_X, 30, pyxel.COLOR_PINK, 12)
        else:
            # Wrong color → caught but combo resets
            self.combo = 1
            self.hook_color = nearest.color
            self.super_mode = 0
            earned = 50
            if nearest.golden:
                earned *= 2
            self.score += earned
            self._add_float(nearest.x, nearest.y, f"+{earned}", pyxel.COLOR_WHITE)
            self._spawn_particles(nearest.x, nearest.y, COLOR_VALS[nearest.color], 4)
            self.highest_combo = max(self.highest_combo, self.combo)

    def _auto_catch_color(self, color: int) -> None:
        """Super mode: auto-catch all living fish of the given color."""
        for f in self.fish:
            if f.alive and f.color == color and f is not None:
                f.alive = False
                earned = 100
                self.score += earned
                self._add_float(f.x, f.y, f"+{earned}", COLOR_VALS[color])
                self._spawn_particles(f.x, f.y, COLOR_VALS[color], 4)
                self.catches += 1

    def _update_fish(self) -> None:
        for f in self.fish:
            if not f.alive:
                continue
            f.x += f.vx
            # Remove off-screen fish
            if f.x < -20 or f.x > SCREEN_W + 20:
                f.alive = False
                # Escaped fish don't penalize — they're just removed

        # Clean up dead fish
        self.fish = [f for f in self.fish if f.alive]

    def _update_spawn(self) -> None:
        self.spawn_timer -= 1
        if self.spawn_timer <= 0 and len(self.fish) < FISH_MAX:
            self.spawn_timer = self.spawn_interval + random.randrange(-10, 20)
            self._spawn_fish()

    def _spawn_fish(self) -> None:
        """Spawn a new fish."""
        from_right = random.random() < 0.25
        color = random.randrange(NUM_COLORS)
        depth_base = 50 + random.randrange(0, 150)

        if from_right:
            x = SCREEN_W + random.uniform(5, 30)
            vx = random.uniform(-2.0, -0.6)
        else:
            x = random.uniform(-30, -5)
            vx = random.uniform(0.6, 2.0)

        # Y position: base depth ± random offset
        y = depth_base + random.uniform(-10, 10)

        # Golden fish (rare, 8% chance)
        golden = random.random() < 0.08

        size = 7 if golden else 6
        speed_mult = 1.3 if golden else 1.0
        vx *= speed_mult

        self.fish.append(Fish(x=x, y=y, color=color, vx=vx, size=size, golden=golden))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.15  # gravity
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floats(self) -> None:
        for ft in self.floats:
            ft.y += ft.vy
            ft.life -= 1
        self.floats = [ft for ft in self.floats if ft.life > 0]

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(0.5, 3.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 1.0
            life = random.randint(8, 20)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def _add_float(self, x: float, y: float, text: str, color: int) -> None:
        self.floats.append(FloatText(x=x - len(text) * 2, y=y, text=text, life=40, color=color))

    # ── Draw ────────────────────────────────────────────────────────────
    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game()
            self._draw_game_over_overlay()

    def _draw_title(self) -> None:
        pyxel.cls(pyxel.COLOR_NAVY)
        # Water background
        for y in range(30, SCREEN_H):
            shimmer = int(math.sin(y * 0.1 + self.water_offset) * 2)
            col = pyxel.COLOR_DARK_BLUE if (y // 4 + shimmer) % 2 == 0 else pyxel.COLOR_LIGHT_BLUE
            pyxel.line(0, y, SCREEN_W, y, col)

        # Title
        title = "HOOK CHAIN"
        pyxel.text(SCREEN_W // 2 - len(title) * 2, 60, title, pyxel.COLOR_YELLOW)

        # Subtitle
        sub = "Color-Match Fishing"
        pyxel.text(SCREEN_W // 2 - len(sub) * 2, 75, sub, pyxel.COLOR_WHITE)

        # Hook icon
        hook_x = SCREEN_W // 2
        pyxel.line(hook_x, 100, hook_x, 130, pyxel.COLOR_WHITE)
        pyxel.circ(hook_x, 130, HOOK_RADIUS, pyxel.COLOR_RED)

        # Instructions
        lines = [
            "UP/DOWN : Move hook",
            "SPACE/Z : Cast line",
            "1-4     : Select target color",
            "WHEEL   : Cycle color",
            "",
            "Catch same-color fish to COMBO!",
            f"COMBO {SUPER_COMBO_THRESHOLD}+ = SUPER MODE",
        ]
        for i, line in enumerate(lines):
            pyxel.text(20, 150 + i * 9, line, pyxel.COLOR_WHITE if i < 4 or i == 5 else pyxel.COLOR_LIME)

        # Blink prompt
        if (self.title_blink // 30) % 2 == 0:
            prompt = "PRESS SPACE TO START"
            pyxel.text(SCREEN_W // 2 - len(prompt) * 2, 225, prompt, pyxel.COLOR_YELLOW)

    def _draw_game(self) -> None:
        # Background — water
        for y in range(0, SCREEN_H):
            wave = int(math.sin(y * 0.08 + self.water_offset) * 1.5)
            if y < 30:
                col = pyxel.COLOR_NAVY
            else:
                base = pyxel.COLOR_DARK_BLUE if (y // 6 + wave) % 3 == 0 else pyxel.COLOR_LIGHT_BLUE
                col = base if (y // 6 + wave) % 3 != 2 else pyxel.COLOR_NAVY
            pyxel.line(0, y, SCREEN_W, y, col)

        # Surface line
        pyxel.line(0, 30, SCREEN_W, 30, pyxel.COLOR_CYAN)

        # Fish
        for f in self.fish:
            if not f.alive:
                continue
            self._draw_fish(f)

        # Hook line
        line_col = pyxel.COLOR_WHITE if self.heat_cooldown == 0 else pyxel.COLOR_ORANGE
        pyxel.line(HOOK_X, 30, HOOK_X, self.hook_y, line_col)

        # Hook
        hook_color = COLOR_VALS[self.hook_color]
        if self.super_mode > 0:
            # Rainbow pulsing in super mode
            rainbow_idx = (self.frame // 5) % NUM_COLORS
            hook_color = COLOR_VALS[rainbow_idx]

        # Hook glow effect in super mode
        if self.super_mode > 0:
            glow_radius = HOOK_RADIUS + 3 + int(math.sin(self.frame * 0.3) * 2)
            pyxel.circb(HOOK_X, self.hook_y, glow_radius, pyxel.COLOR_YELLOW)

        pyxel.circ(HOOK_X, self.hook_y, HOOK_RADIUS, hook_color)
        pyxel.circ(HOOK_X, self.hook_y, HOOK_RADIUS - 3, pyxel.COLOR_WHITE)

        # Catch range indicator (subtle)
        if self.super_mode > 0:
            pyxel.circb(HOOK_X, self.hook_y, CATCH_RANGE, pyxel.COLOR_YELLOW)

        # Particles
        for p in self.particles:
            alpha_col = p.color if p.life > 5 else pyxel.COLOR_GRAY
            pyxel.pset(int(p.x), int(p.y), alpha_col)

        # Floating text
        for ft in self.floats:
            text_col = ft.color if ft.life > 10 else pyxel.COLOR_GRAY
            pyxel.text(int(ft.x), int(ft.y), ft.text, text_col)

        # ── HUD ──
        self._draw_hud()

    def _draw_fish(self, f: Fish) -> None:
        """Draw a fish at its position."""
        col = pyxel.COLOR_YELLOW if f.golden else COLOR_VALS[f.color]
        x, y = int(f.x), int(f.y)
        s = f.size

        if f.vx > 0:  # swimming right
            # Body
            pyxel.elli(x - s, y - s // 2, s * 2, s, col)
            # Tail
            pyxel.tri(x - s - 2, y, x - s - 5, y - 4, x - s - 5, y + 4, col)
            # Eye
            eye_col = pyxel.COLOR_WHITE if not f.golden else pyxel.COLOR_RED
            pyxel.pset(x + s - 2, y - 1, eye_col)
        else:  # swimming left
            pyxel.elli(x - s, y - s // 2, s * 2, s, col)
            pyxel.tri(x + s + 2, y, x + s + 5, y - 4, x + s + 5, y + 4, col)
            eye_col = pyxel.COLOR_WHITE if not f.golden else pyxel.COLOR_RED
            pyxel.pset(x - s + 2, y - 1, eye_col)

    def _draw_hud(self) -> None:
        """Draw score, combo, timer, heat bar."""
        # Top bar background
        pyxel.rect(0, 0, SCREEN_W, 30, pyxel.COLOR_BLACK)

        # Timer
        secs = max(0, self.game_timer // FPS)
        timer_text = f"TIME {secs:02d}"
        timer_col = pyxel.COLOR_RED if secs <= 10 else pyxel.COLOR_WHITE
        pyxel.text(4, 3, timer_text, timer_col)

        # Score
        score_text = f"SCORE {self.score:06d}"
        pyxel.text(4, 14, score_text, pyxel.COLOR_YELLOW)

        # Combo
        combo_col = pyxel.COLOR_LIME
        if self.combo >= MEGA_COMBO_THRESHOLD:
            combo_col = pyxel.COLOR_YELLOW
        elif self.combo >= SUPER_COMBO_THRESHOLD:
            combo_col = pyxel.COLOR_PINK
        pyxel.text(110, 3, f"COMBO x{self.combo}", combo_col)

        # Current target color
        pyxel.text(110, 14, "TARGET:", pyxel.COLOR_WHITE)
        target_col = COLOR_VALS[self.hook_color]
        if self.super_mode > 0:
            target_col = pyxel.COLOR_YELLOW
        pyxel.rect(155, 13, 12, 12, target_col)

        # Super mode indicator
        if self.super_mode > 0:
            super_secs = self.super_mode // FPS + 1
            pyxel.text(180, 3, f"SUPER {super_secs}s", pyxel.COLOR_YELLOW)

        # Heat bar
        heat_x = 180
        heat_w = 70
        pyxel.rect(heat_x, 22, heat_w, 6, pyxel.COLOR_GRAY)
        heat_fill = int(heat_w * self.heat / HEAT_MAX)
        heat_bar_col = pyxel.COLOR_ORANGE if self.heat_cooldown > 0 else pyxel.COLOR_RED
        pyxel.rect(heat_x, 22, heat_fill, 6, heat_bar_col)
        pyxel.text(heat_x - 28, 22, "HEAT", pyxel.COLOR_ORANGE)

    def _draw_game_over_overlay(self) -> None:
        """Semi-transparent overlay with final stats."""
        # Darken
        for y in range(0, SCREEN_H):
            if y % 3 == 0:
                pyxel.line(0, y, SCREEN_W, y, pyxel.COLOR_BLACK)

        # Panel
        panel_x, panel_y, panel_w, panel_h = 28, 40, 200, 160
        pyxel.rect(panel_x, panel_y, panel_w, panel_h, pyxel.COLOR_NAVY)
        pyxel.rectb(panel_x, panel_y, panel_w, panel_h, pyxel.COLOR_WHITE)

        pyxel.text(panel_x + 55, panel_y + 12, "GAME OVER", pyxel.COLOR_RED)

        stats = [
            f"SCORE: {self.score:06d}",
            f"HIGHEST COMBO: x{self.highest_combo}",
            f"CATCHES: {self.catches}",
            f"MISSES: {self.misses}",
            "",
            "PRESS R TO RETRY",
        ]
        for i, s in enumerate(stats):
            col = pyxel.COLOR_YELLOW if i == 0 else pyxel.COLOR_WHITE
            if i == len(stats) - 1:
                col = pyxel.COLOR_LIME
            pyxel.text(panel_x + 16, panel_y + 40 + i * 14, s, col)

        # Color legend
        leg_x = panel_x + 12
        leg_y = panel_y + 130
        pyxel.text(leg_x, leg_y, "COLORS:", pyxel.COLOR_WHITE)
        for ci in range(NUM_COLORS):
            px = leg_x + 46 + ci * 32
            pyxel.rect(px, leg_y, 8, 8, COLOR_VALS[ci])
            pyxel.text(px + 12, leg_y, f"[{ci + 1}]", pyxel.COLOR_WHITE)

# ── Entry Point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    Game()
