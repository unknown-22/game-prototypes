"""
COMBO BURST — Color-match target shooting gallery with chain explosions.

Reinterpreted from game_idea_factory #1 (score 31.8):
  "space-mining deckbuilder with floor rule changes + chain collapse"
  → reaction shooter where same-color combo unlocks chain bursts.

Core hook: maintain same-color streak → COMBO ≥ 3 triggers CHAIN BURST
that cascades through nearby matching targets for massive score.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel

# ── Config ──────────────────────────────────────────────────────────────────
SCREEN_W = 256
SCREEN_H = 256
FPS = 60
GAME_DURATION = 60  # seconds
TARGET_SPAWN_INTERVAL = 40  # frames between spawns
COMBO_THRESHOLD = 3  # combos needed for chain burst
CHAIN_RADIUS = 55  # chain explosion radius in px
MAX_TARGETS = 24
CROSSHAIR_SIZE = 7
TARGET_RADIUS = 10
PLAYER_HP = 5
TARGET_LIFETIME = 180  # frames (~3s) before target escapes
HEAT_MAX = 100
HEAT_PER_SHOT = 4
HEAT_PER_BURST_TARGET = 8
HEAT_DECAY = 0.3  # per frame
HEAT_THRESHOLD = 70  # above this: screen shake + 2x score

# ── Color palette ───────────────────────────────────────────────────────────
COLOR_RED = pyxel.COLOR_RED
COLOR_GREEN = pyxel.COLOR_GREEN
COLOR_BLUE = pyxel.COLOR_DARK_BLUE
COLOR_YELLOW = pyxel.COLOR_YELLOW
TARGET_COLORS: list[int] = [COLOR_RED, COLOR_GREEN, COLOR_BLUE, COLOR_YELLOW]
COLOR_NAMES: dict[int, str] = {
    COLOR_RED: "RED",
    COLOR_GREEN: "GRN",
    COLOR_BLUE: "BLU",
    COLOR_YELLOW: "YEL",
}

# ── Data classes ────────────────────────────────────────────────────────────


@dataclass
class Target:
    """A colored target the player must shoot."""

    x: float
    y: float
    radius: int
    color: int
    vx: float = 0.0
    vy: float = 0.0
    alive: bool = True
    spawn_frame: int = 0


@dataclass
class Particle:
    """Visual particle for explosions and effects."""

    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int
    max_life: int


@dataclass
class FloatingText:
    """Floating score/feedback text."""

    x: float
    y: float
    text: str
    color: int
    life: int
    max_life: int


# ── Phase ───────────────────────────────────────────────────────────────────


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ── Game ────────────────────────────────────────────────────────────────────


class ComboBurst:
    """Color-match target shooting gallery with chain explosions."""

    # Hit-check margin (pixels inside target radius that count as hit)
    HIT_MARGIN: ClassVar[int] = 2

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="COMBO BURST", fps=FPS, display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        """Reset all game state for a new session."""
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.hits: int = 0
        self.misses: int = 0
        self.hp: int = PLAYER_HP
        self.heat: float = 0.0
        self.targets: list[Target] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.frame: int = 0
        self.spawn_timer: int = 0
        self.active_color: int | None = None  # current combo color
        self.crosshair_x: float = float(SCREEN_W // 2)
        self.crosshair_y: float = float(SCREEN_H // 2)
        self.game_timer: int = GAME_DURATION * FPS
        self.shake_frames: int = 0
        self.shake_intensity: int = 0
        self.chain_count: int = 0  # targets destroyed in current chain
        self.best_chain: int = 0

    # ── Update ──────────────────────────────────────────────────────────────

    def update(self) -> None:
        """Main update loop called by Pyxel each frame."""
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        """Handle title screen input."""
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE):
            self.phase = Phase.PLAYING
            self.frame = 0
            self.game_timer = GAME_DURATION * FPS

    def _update_game_over(self) -> None:
        """Handle game over screen input."""
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.phase = Phase.PLAYING
            self.frame = 0
            self.game_timer = GAME_DURATION * FPS

    def _update_playing(self) -> None:
        """Update game logic during active play."""
        self.frame += 1
        self.game_timer -= 1

        # Heat decay
        self.heat = max(0.0, self.heat - HEAT_DECAY)

        # Screen shake decay
        if self.shake_frames > 0:
            self.shake_frames -= 1

        # Spawn targets
        self._update_spawning()

        # Move targets
        self._update_targets()

        # Escape check: targets that live too long
        self._update_escapes()

        # Mouse tracking
        self.crosshair_x = float(pyxel.mouse_x)
        self.crosshair_y = float(pyxel.mouse_y)

        # Shoot on click
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._shoot()

        # Update particles
        self._update_particles()

        # Update floating texts
        self._update_floating_texts()

        # Game over conditions
        if self.hp <= 0 or self.game_timer <= 0:
            self.phase = Phase.GAME_OVER

    def _update_spawning(self) -> None:
        """Spawn new targets at intervals, escalating over time."""
        self.spawn_timer += 1
        # Faster spawns as time decreases
        elapsed_pct = 1.0 - (self.game_timer / (GAME_DURATION * FPS))
        interval = max(15, int(TARGET_SPAWN_INTERVAL * (1.0 - elapsed_pct * 0.5)))
        # High heat = even faster spawns
        if self.heat >= HEAT_THRESHOLD:
            interval = max(10, interval - 10)

        if self.spawn_timer >= interval and len(self.targets) < MAX_TARGETS:
            self.spawn_timer = 0
            self._spawn_target()

    def _spawn_target(self) -> None:
        """Spawn one target at a random edge position."""
        color = random.choice(TARGET_COLORS)
        radius = TARGET_RADIUS

        # Spawn from edges
        edge = random.randint(0, 3)
        margin = radius + 4
        if edge == 0:  # top
            x = float(random.uniform(margin, SCREEN_W - margin))
            y = float(margin)
            vx = random.uniform(-0.5, 0.5)
            vy = random.uniform(0.3, 0.8)
        elif edge == 1:  # right
            x = float(SCREEN_W - margin)
            y = float(random.uniform(margin, SCREEN_H - margin))
            vx = random.uniform(-0.8, -0.3)
            vy = random.uniform(-0.5, 0.5)
        elif edge == 2:  # bottom
            x = float(random.uniform(margin, SCREEN_W - margin))
            y = float(SCREEN_H - margin)
            vx = random.uniform(-0.5, 0.5)
            vy = random.uniform(-0.8, -0.3)
        else:  # left
            x = float(margin)
            y = float(random.uniform(margin, SCREEN_H - margin))
            vx = random.uniform(0.3, 0.8)
            vy = random.uniform(-0.5, 0.5)

        # High heat = faster targets
        if self.heat >= HEAT_THRESHOLD:
            vx *= 1.8
            vy *= 1.8

        target = Target(
            x=x, y=y, radius=radius, color=color, vx=vx, vy=vy, spawn_frame=self.frame
        )
        self.targets.append(target)

    def _update_targets(self) -> None:
        """Move targets and bounce off walls."""
        for t in self.targets:
            if not t.alive:
                continue
            t.x += t.vx
            t.y += t.vy
            # Bounce off walls
            if t.x - t.radius < 0:
                t.x = float(t.radius)
                t.vx = abs(t.vx)
            elif t.x + t.radius > SCREEN_W:
                t.x = float(SCREEN_W - t.radius)
                t.vx = -abs(t.vx)
            if t.y - t.radius < 0:
                t.y = float(t.radius)
                t.vy = abs(t.vy)
            elif t.y + t.radius > SCREEN_H:
                t.y = float(SCREEN_H - t.radius)
                t.vy = -abs(t.vy)

    def _update_escapes(self) -> None:
        """Check for targets that have lived past their lifetime."""
        for t in self.targets:
            if not t.alive:
                continue
            if self.frame - t.spawn_frame >= TARGET_LIFETIME:
                t.alive = False
                self.hp -= 1
                self._spawn_floating_text(t.x, t.y, "MISS", pyxel.COLOR_GRAY)

        # Remove dead targets
        self.targets = [t for t in self.targets if t.alive]

    def _shoot(self) -> None:
        """Handle mouse click: check if any target was hit."""
        mx = self.crosshair_x
        my = self.crosshair_y

        # Build heat
        self.heat = min(float(HEAT_MAX), self.heat + HEAT_PER_SHOT)

        # Find closest hit target
        hit_target: Target | None = None
        best_dist = float("inf")
        for t in self.targets:
            if not t.alive:
                continue
            dx = mx - t.x
            dy = my - t.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist <= t.radius + self.HIT_MARGIN and dist < best_dist:
                hit_target = t
                best_dist = dist

        if hit_target is not None:
            self._hit_target(hit_target)
        else:
            # Clicked empty space: miss penalty
            self.misses += 1
            self._spawn_floating_text(mx, my, "MISS", pyxel.COLOR_GRAY)
            # Miss breaks combo
            self.combo = 0
            self.active_color = None

    def _hit_target(self, target: Target) -> None:
        """Process a successful hit on a target."""
        color = target.color

        # Combo logic
        if self.active_color == color:
            self.combo += 1
        else:
            self.combo = 1
            self.active_color = color

        self.max_combo = max(self.max_combo, self.combo)
        self.hits += 1
        target.alive = False

        # Score calculation
        base_score = 10
        combo_mult = self.combo
        heat_mult = 2 if self.heat >= HEAT_THRESHOLD else 1
        points = base_score * combo_mult * heat_mult
        self.score += points

        # Spawn hit particles
        self._spawn_hit_particles(target.x, target.y, color)

        # Floating score text
        label = f"+{points}"
        if self.combo >= COMBO_THRESHOLD:
            label = f"COMBO x{self.combo}!"
        self._spawn_floating_text(target.x, target.y - 10, label, color)

        # Chain burst: if combo >= threshold, explode nearby same-color targets
        if self.combo >= COMBO_THRESHOLD:
            self.chain_count = 1
            self._chain_burst(target.x, target.y, color)
            if self.chain_count > self.best_chain:
                self.best_chain = self.chain_count

    def _chain_burst(self, cx: float, cy: float, color: int) -> None:
        """Recursively chain-explode nearby same-color targets."""
        for t in self.targets:
            if not t.alive or t.color != color:
                continue
            dx = cx - t.x
            dy = cy - t.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist <= CHAIN_RADIUS:
                t.alive = False
                self.chain_count += 1
                self.heat = min(float(HEAT_MAX), self.heat + HEAT_PER_BURST_TARGET)
                # Score for chain targets
                base_score = 15
                combo_mult = self.combo + self.chain_count
                heat_mult = 2 if self.heat >= HEAT_THRESHOLD else 1
                points = base_score * combo_mult * heat_mult
                self.score += points
                self._spawn_hit_particles(t.x, t.y, color)
                self._spawn_floating_text(
                    t.x, t.y - 5, f"+{points}", pyxel.COLOR_WHITE
                )
                # Recurse from this target's position
                self._chain_burst(t.x, t.y, color)

        # Remove dead targets
        self.targets = [t for t in self.targets if t.alive]

        # Screen shake on big chains
        if self.chain_count >= 5:
            self.shake_frames = 8
            self.shake_intensity = min(3, self.chain_count // 2)
        elif self.chain_count >= 3:
            self.shake_frames = 4
            self.shake_intensity = 2

    def _spawn_hit_particles(self, x: float, y: float, color: int) -> None:
        """Spawn explosion particles at (x, y)."""
        for _ in range(8):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1.0, 3.0)
            p = Particle(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                color=color,
                life=15,
                max_life=15,
            )
            self.particles.append(p)
        # White flash particles
        for _ in range(3):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2.0, 4.0)
            p = Particle(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                color=pyxel.COLOR_WHITE,
                life=8,
                max_life=8,
            )
            self.particles.append(p)

    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        """Create floating score/feedback text."""
        ft = FloatingText(
            x=x,
            y=y,
            text=text,
            color=color,
            life=30,
            max_life=30,
        )
        self.floating_texts.append(ft)

    def _update_particles(self) -> None:
        """Update particle positions and lifetimes."""
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        """Update floating text positions and lifetimes."""
        for ft in self.floating_texts:
            ft.y -= 0.8
            ft.life -= 1
        self.floating_texts = [
            ft for ft in self.floating_texts if ft.life > 0
        ]

    # ── Draw ────────────────────────────────────────────────────────────────

    def draw(self) -> None:
        """Main draw loop called by Pyxel each frame."""
        pyxel.cls(pyxel.COLOR_BLACK)

        # Apply screen shake offset
        shake_ox = 0
        shake_oy = 0
        if self.shake_frames > 0:
            shake_ox = random.randint(-self.shake_intensity, self.shake_intensity)
            shake_oy = random.randint(-self.shake_intensity, self.shake_intensity)

        if self.phase == Phase.TITLE:
            self._draw_title(shake_ox, shake_oy)
        elif self.phase == Phase.PLAYING:
            self._draw_playing(shake_ox, shake_oy)
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over(shake_ox, shake_oy)

    def _draw_title(self, ox: int, oy: int) -> None:
        """Draw title screen."""
        cx = SCREEN_W // 2 + ox
        pyxel.text(cx - 40, 80, "COMBO BURST", pyxel.COLOR_WHITE)
        pyxel.text(cx - 44, 95, "Click to Start", pyxel.COLOR_YELLOW)
        pyxel.text(cx - 40, 120, "Same color = COMBO", pyxel.COLOR_GREEN)
        pyxel.text(cx - 44, 133, "COMBOx3 = CHAIN BURST!", pyxel.COLOR_RED)
        pyxel.text(cx - 38, 155, "Survive 60 seconds", pyxel.COLOR_CYAN)

    def _draw_game_over(self, ox: int, oy: int) -> None:
        """Draw game over screen."""
        cx = SCREEN_W // 2 + ox
        cy = SCREEN_H // 2 + oy

        if self.hp <= 0:
            reason = "NO HP LEFT"
        else:
            reason = "TIME'S UP"

        pyxel.text(cx - 24, cy - 40, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(cx - len(reason) * 2, cy - 20, reason, pyxel.COLOR_WHITE)
        pyxel.text(
            cx - 30, cy, f"SCORE: {self.score}", pyxel.COLOR_YELLOW
        )
        pyxel.text(
            cx - 28, cy + 15, f"HITS: {self.hits}", pyxel.COLOR_GREEN
        )
        pyxel.text(
            cx - 38, cy + 28, f"MAX COMBO: {self.max_combo}", pyxel.COLOR_CYAN
        )
        pyxel.text(
            cx - 38, cy + 41, f"BEST CHAIN: {self.best_chain}", pyxel.COLOR_RED
        )
        pyxel.text(cx - 42, cy + 65, "Click to Retry", pyxel.COLOR_WHITE)

    def _draw_playing(self, ox: int, oy: int) -> None:
        """Draw the main gameplay view."""
        # Draw background grid
        for gx in range(0, SCREEN_W, 32):
            for gy in range(0, SCREEN_H, 32):
                pyxel.pset(gx + ox, gy + oy, pyxel.COLOR_NAVY)

        # Draw targets
        for t in self.targets:
            if not t.alive:
                continue
            self._draw_target(t, ox, oy)

        # Draw particles
        for p in self.particles:
            alpha = p.life / p.max_life
            col = p.color if alpha > 0.3 else pyxel.COLOR_GRAY
            px = int(p.x) + ox
            py = int(p.y) + oy
            pyxel.pset(px, py, col)
            if alpha > 0.5:
                pyxel.pset(px + 1, py, col)
                pyxel.pset(px - 1, py, col)
                pyxel.pset(px, py + 1, col)
                pyxel.pset(px, py - 1, col)

        # Draw floating texts
        for ft in self.floating_texts:
            alpha = ft.life / ft.max_life
            col = ft.color if alpha > 0.3 else pyxel.COLOR_GRAY
            tx = int(ft.x) + ox - len(ft.text) * 2
            ty = int(ft.y) + oy
            pyxel.text(tx, ty, ft.text, col)

        # Draw crosshair
        self._draw_crosshair(ox, oy)

        # Draw HUD
        self._draw_hud()

    def _draw_target(self, t: Target, ox: int, oy: int) -> None:
        """Draw a single target circle."""
        tx = int(t.x) + ox
        ty = int(t.y) + oy
        r = t.radius

        # Outer ring (white flash if near death)
        time_left = TARGET_LIFETIME - (self.frame - t.spawn_frame)
        outer_color = t.color
        if time_left < 30 and (self.frame % 8 < 4):
            outer_color = pyxel.COLOR_WHITE
        pyxel.circb(tx, ty, r, outer_color)

        # Inner fill
        pyxel.circ(tx, ty, r - 2, t.color)

        # Color indicator dot in center
        pyxel.circ(tx, ty, 2, pyxel.COLOR_WHITE)

        # Highlight if this target would continue the combo
        if self.active_color is not None and t.color == self.active_color:
            pyxel.circb(tx, ty, r + 2, pyxel.COLOR_WHITE)

    def _draw_crosshair(self, ox: int, oy: int) -> None:
        """Draw the mouse crosshair."""
        cx = int(self.crosshair_x) + ox
        cy = int(self.crosshair_y) + oy
        s = CROSSHAIR_SIZE

        # Color based on heat level
        ch_color = pyxel.COLOR_WHITE
        if self.heat >= HEAT_THRESHOLD:
            ch_color = pyxel.COLOR_RED
        elif self.heat >= HEAT_THRESHOLD * 0.5:
            ch_color = pyxel.COLOR_ORANGE

        pyxel.line(cx - s, cy, cx - 3, cy, ch_color)
        pyxel.line(cx + 3, cy, cx + s, cy, ch_color)
        pyxel.line(cx, cy - s, cx, cy - 3, ch_color)
        pyxel.line(cx, cy + 3, cx, cy + s, ch_color)
        pyxel.pset(cx, cy, ch_color)

    def _draw_hud(self) -> None:
        """Draw heads-up display: score, combo, HP, timer, heat."""
        # Timer bar (top)
        time_pct = self.game_timer / (GAME_DURATION * FPS)
        bar_w = int(SCREEN_W * time_pct)
        bar_color = pyxel.COLOR_GREEN if time_pct > 0.3 else pyxel.COLOR_RED
        if time_pct > 0.6:
            bar_color = pyxel.COLOR_CYAN
        pyxel.rect(0, 0, bar_w, 4, bar_color)
        pyxel.rect(bar_w, 0, SCREEN_W - bar_w, 4, pyxel.COLOR_NAVY)

        # Heat bar (below timer)
        heat_pct = self.heat / HEAT_MAX
        heat_bar_w = int(SCREEN_W * heat_pct)
        heat_col = pyxel.COLOR_ORANGE if heat_pct < 0.7 else pyxel.COLOR_RED
        pyxel.rect(0, 5, heat_bar_w, 3, heat_col)
        pyxel.rect(heat_bar_w, 5, SCREEN_W - heat_bar_w, 3, pyxel.COLOR_NAVY)
        if self.heat >= HEAT_THRESHOLD:
            pyxel.text(SCREEN_W // 2 - 12, 5, "OVERHEAT x2", pyxel.COLOR_RED)

        # Score (top-left)
        pyxel.text(2, 12, f"SCORE: {self.score}", pyxel.COLOR_WHITE)

        # Combo (top-right)
        combo_text = f"COMBO: x{self.combo}"
        combo_color = pyxel.COLOR_WHITE
        if self.combo >= COMBO_THRESHOLD:
            combo_color = pyxel.COLOR_YELLOW
        if self.combo >= 8:
            combo_color = pyxel.COLOR_RED
        pyxel.text(SCREEN_W - len(combo_text) * 4 - 2, 12, combo_text, combo_color)

        # HP (bottom-left)
        hp_text = f"HP: {self.hp}"
        hp_color = pyxel.COLOR_GREEN if self.hp > 2 else pyxel.COLOR_RED
        pyxel.text(2, SCREEN_H - 10, hp_text, hp_color)

        # Timer text (bottom-right)
        time_s = max(0, self.game_timer // FPS)
        time_text = f"TIME: {time_s}s"
        pyxel.text(
            SCREEN_W - len(time_text) * 4 - 2, SCREEN_H - 10, time_text, pyxel.COLOR_WHITE
        )

        # Active color indicator (bottom-center)
        if self.active_color is not None:
            name = COLOR_NAMES.get(self.active_color, "???")
            label = f"LOCK: {name}"
            px = SCREEN_W // 2 - len(label) * 2
            pyxel.text(px, SCREEN_H - 10, label, self.active_color)


# ── Entry point ─────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point for the COMBO BURST prototype."""
    ComboBurst()


if __name__ == "__main__":
    main()
