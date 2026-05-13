"""
THRUST CHAIN — Lunar Lander with Color-Matched Combo Chains
=============================================================
Reinterpreted from game idea #1 (Score 32.15):
  "Deckbuilder roguelite — delivery/logistics"
Hooks mapped:
  - "circuit/pipe flow visible" → colored landing pad chain
  - "split values converge and explode" → COMBO multiplier jackpots
  - "log/replay as assets" → ghost trail (previous best path)

Core mechanic: Land on color-matched pads to build COMBO chains.
The most fun moment: aiming for the next same-color pad with
barely enough fuel, landing precisely to keep the combo alive.

Controls:
  LEFT/RIGHT  — Rotate ship
  UP          — Thrust
  Z           — Cycle ship color
  R           — Restart (on game over)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ═══════════════════════════════════════════════════════════════
#  Config
# ═══════════════════════════════════════════════════════════════

WIDTH: int = 256
HEIGHT: int = 256
DISPLAY_SCALE: int = 2
FPS: int = 60

GRAVITY: float = 0.06
THRUST_POWER: float = 0.14
ROTATION_SPEED: float = 3.0
ROTATION_FRICTION: float = 0.95
LINEAR_DAMPING: float = 0.998

MAX_FUEL: float = 100.0
MAX_HP: int = 100
THRUST_FUEL_COST: float = 0.4
LANDING_REFUEL: float = 35.0

SAFE_LANDING_SPEED: float = 1.8
SAFE_LANDING_ANGLE: float = 35.0  # degrees from upright

WALL_DAMAGE: int = 15
WRONG_COLOR_DAMAGE: int = 20
CRASH_DAMAGE: int = 30  # landing too fast

PAD_WIDTH: int = 32
PAD_HEIGHT: int = 6
PAD_Y: int = HEIGHT - 20
PAD_COUNT: int = 4
PAD_MIN_GAP: int = 6

SHIP_SIZE: int = 10  # half-height of triangle

COLORS: list[int] = [
    pyxel.COLOR_RED,
    pyxel.COLOR_CYAN,
    pyxel.COLOR_GREEN,
    pyxel.COLOR_YELLOW,
]
COLOR_NAMES: list[str] = ["RED", "BLUE", "GREEN", "YELLOW"]

GHOST_TRAIL_MAX: int = 300


# ═══════════════════════════════════════════════════════════════
#  Data classes
# ═══════════════════════════════════════════════════════════════


@dataclass
class LandingPad:
    x: float
    y: float = PAD_Y
    width: float = PAD_WIDTH
    color_idx: int = 0
    value: int = 10
    active: bool = True

    @property
    def color(self) -> int:
        return COLORS[self.color_idx]

    @property
    def left(self) -> float:
        return self.x - self.width / 2

    @property
    def right(self) -> float:
        return self.x + self.width / 2


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    max_life: int = 20


@dataclass
class GhostPoint:
    x: float
    y: float
    angle: float


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int
    vy: float = -0.8


# ═══════════════════════════════════════════════════════════════
#  Phase enum
# ═══════════════════════════════════════════════════════════════


class Phase(Enum):
    PLAYING = auto()
    LAND_PAUSE = auto()  # brief celebration after landing
    GAME_OVER = auto()


# ═══════════════════════════════════════════════════════════════
#  Ship
# ═══════════════════════════════════════════════════════════════


@dataclass
class Ship:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    angle: float = 0.0  # degrees, 0 = pointing up
    color_idx: int = 0
    fuel: float = MAX_FUEL
    hp: int = MAX_HP
    thrusting: bool = False

    @property
    def color(self) -> int:
        return COLORS[self.color_idx]

    def reset(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.angle = 0.0
        self.color_idx = 0
        self.fuel = MAX_FUEL
        self.hp = MAX_HP
        self.thrusting = False

    def nose_x(self) -> float:
        rad = math.radians(self.angle - 90)
        return self.x + SHIP_SIZE * math.cos(rad)

    def nose_y(self) -> float:
        rad = math.radians(self.angle - 90)
        return self.y + SHIP_SIZE * math.sin(rad)

    def base_left(self) -> tuple[float, float]:
        """Bottom-left corner of the triangular ship."""
        rad_back = math.radians(self.angle + 90)
        rad_perp = math.radians(self.angle)
        bx = self.x + SHIP_SIZE * 0.5 * math.cos(rad_back)
        by = self.y + SHIP_SIZE * 0.5 * math.sin(rad_back)
        return (
            bx - SHIP_SIZE * 0.55 * math.cos(rad_perp),
            by - SHIP_SIZE * 0.55 * math.sin(rad_perp),
        )

    def base_right(self) -> tuple[float, float]:
        """Bottom-right corner of the triangular ship."""
        rad_back = math.radians(self.angle + 90)
        rad_perp = math.radians(self.angle)
        bx = self.x + SHIP_SIZE * 0.5 * math.cos(rad_back)
        by = self.y + SHIP_SIZE * 0.5 * math.sin(rad_back)
        return (
            bx + SHIP_SIZE * 0.55 * math.cos(rad_perp),
            by + SHIP_SIZE * 0.55 * math.sin(rad_perp),
        )


# ═══════════════════════════════════════════════════════════════
#  Game
# ═══════════════════════════════════════════════════════════════


class Game:
    """Thrust Chain — lunar lander with color-matched combo chains."""

    def __init__(self) -> None:
        pyxel.init(WIDTH, HEIGHT, title="THRUST CHAIN", display_scale=DISPLAY_SCALE, fps=FPS)
        self.ship: Ship = Ship(x=WIDTH / 2, y=60)
        self.pads: list[LandingPad] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.ghost_trail: list[GhostPoint] = []
        self.player_trail: list[GhostPoint] = []

        self.phase: Phase = Phase.PLAYING
        self.land_timer: int = 0
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.best_score: int = 0
        self.screen_shake: int = 0

        self.reset_game()
        pyxel.run(self.update, self.draw)

    # ── Reset ──

    def reset_game(self) -> None:
        """Reset game state for a new run."""
        self.ship.reset(WIDTH / 2, 50)
        self.pads.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.player_trail.clear()
        self.phase = Phase.PLAYING
        self.land_timer = 0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.screen_shake = 0
        self._spawn_pads(count=PAD_COUNT)

    # ── Pad spawning ──

    def _spawn_pads(self, count: int) -> None:
        """Spawn landing pads, ensuring minimum gap between them."""
        attempts = 0
        while len(self.pads) < count and attempts < 200:
            attempts += 1
            x = random.uniform(PAD_WIDTH, WIDTH - PAD_WIDTH)
            # Check minimum gap
            ok = True
            for pad in self.pads:
                if abs(x - pad.x) < PAD_WIDTH + PAD_MIN_GAP:
                    ok = False
                    break
            if ok:
                color_idx = random.randrange(len(COLORS))
                value = 10 + random.randint(0, 3) * 5
                self.pads.append(LandingPad(x=x, color_idx=color_idx, value=value))

    def _refill_pads(self) -> None:
        """Remove inactive pads and spawn new ones."""
        self.pads = [p for p in self.pads if p.active]
        self._spawn_pads(count=PAD_COUNT)

    # ── Update ──

    def update(self) -> None:
        """Main update loop."""
        if pyxel.btnp(pyxel.KEY_R) and self.phase == Phase.GAME_OVER:
            self.reset_game()
            return

        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()

        if self.phase == Phase.PLAYING:
            self._update_input()
            self._update_physics()
            self._update_collision()
            self._update_particles()
            self._update_floating_texts()
            self._update_trail()
        elif self.phase == Phase.LAND_PAUSE:
            self._update_land_pause()
            self._update_particles()
            self._update_floating_texts()

        if self.screen_shake > 0:
            self.screen_shake -= 1

    def _update_input(self) -> None:
        """Handle player input for ship control."""
        ship = self.ship

        # Rotation
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            ship.angle -= ROTATION_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            ship.angle += ROTATION_SPEED

        # Keep angle in [0, 360)
        ship.angle %= 360.0

        # Color cycling
        if pyxel.btnp(pyxel.KEY_Z) or pyxel.btnp(pyxel.KEY_X):
            ship.color_idx = (ship.color_idx + 1) % len(COLORS)

        # Thrust
        ship.thrusting = (
            (pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W))
            and ship.fuel > 0
        )

    def _update_physics(self) -> None:
        """Apply gravity, thrust, and update position."""
        ship = self.ship

        # Gravity
        ship.vy += GRAVITY

        # Thrust
        if ship.thrusting:
            rad = math.radians(ship.angle - 90)
            ship.vx += THRUST_POWER * math.cos(rad)
            ship.vy += THRUST_POWER * math.sin(rad)
            ship.fuel = max(0, ship.fuel - THRUST_FUEL_COST)

            # Thrust particles
            bx, by = ship.base_left()
            bx2, by2 = ship.base_right()
            mid_x = (bx + bx2) / 2
            mid_y = (by + by2) / 2
            rad_back = math.radians(ship.angle + 90)
            for _ in range(2):
                self.particles.append(
                    Particle(
                        x=mid_x + random.uniform(-2, 2),
                        y=mid_y + random.uniform(-2, 2),
                        vx=1.5 * math.cos(rad_back) + random.uniform(-0.5, 0.5),
                        vy=1.5 * math.sin(rad_back) + random.uniform(-0.5, 0.5),
                        life=random.randint(8, 16),
                        color=ship.color,
                        max_life=16,
                    )
                )

        # Damping
        ship.vx *= LINEAR_DAMPING
        ship.vy *= LINEAR_DAMPING

        # Update position
        ship.x += ship.vx
        ship.y += ship.vy

    def _update_collision(self) -> None:
        """Check collisions with walls and landing pads."""
        ship = self.ship

        # Wall collisions
        margin = 5.0
        hit_wall = False
        if ship.x < margin:
            ship.x = margin
            ship.vx = abs(ship.vx) * 0.5
            hit_wall = True
        elif ship.x > WIDTH - margin:
            ship.x = WIDTH - margin
            ship.vx = -abs(ship.vx) * 0.5
            hit_wall = True
        if ship.y < margin:
            ship.y = margin
            ship.vy = abs(ship.vy) * 0.5
            hit_wall = True
        elif ship.y > HEIGHT - margin:
            ship.y = HEIGHT - margin
            ship.vy = -abs(ship.vy) * 0.5
            hit_wall = True

        if hit_wall and ship.hp > 0:
            ship.hp = max(0, ship.hp - WALL_DAMAGE)
            self._add_floating_text(ship.x, ship.y, f"-{WALL_DAMAGE}", pyxel.COLOR_RED)
            self._spawn_crash_particles(ship.x, ship.y, pyxel.COLOR_ORANGE)
            self.screen_shake = 8
            if ship.hp <= 0:
                self._on_game_over()

        # Landing pad collisions — check when ship base is near pad level
        speed = math.sqrt(ship.vx**2 + ship.vy**2)
        is_upright = abs(ship.angle % 360 - 0) < SAFE_LANDING_ANGLE or abs(ship.angle % 360 - 360) < SAFE_LANDING_ANGLE

        for pad in self.pads:
            if not pad.active:
                continue
            # Ship base y must be near pad y
            _, ship_bottom = ship.base_left()
            ship_bottom = max(ship_bottom, ship.base_right()[1])
            if pad.y - 4 <= ship_bottom <= pad.y + 10:
                if pad.left <= ship.x <= pad.right:
                    # Landed on this pad
                    pad.active = False
                    if ship.vy > 0 and speed <= SAFE_LANDING_SPEED and is_upright:
                        self._on_safe_landing(pad)
                    else:
                        self._on_crash_landing(pad)
                    break

    def _on_safe_landing(self, pad: LandingPad) -> None:
        """Handle a safe landing on a pad."""
        ship = self.ship
        ship.vy = 0
        ship.vx = 0

        if pad.color_idx == ship.color_idx:
            # Color match — COMBO!
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            multiplier = self.combo
            earned = pad.value * multiplier
            self.score += earned
            self._add_floating_text(
                ship.x, ship.y - 8,
                f"+{earned} x{multiplier}",
                ship.color,
            )
            # Spawn celebration particles
            for _ in range(12):
                self._spawn_burst_particle(ship.x, pad.y, ship.color)
            self.screen_shake = 3
        else:
            # Wrong color — combo reset, damage
            self.combo = 0
            ship.hp = max(0, ship.hp - WRONG_COLOR_DAMAGE)
            self._add_floating_text(
                ship.x, ship.y - 8,
                f"WRONG! -{WRONG_COLOR_DAMAGE}",
                pyxel.COLOR_RED,
            )
            self._spawn_crash_particles(ship.x, pad.y, pyxel.COLOR_RED)
            self.screen_shake = 6
            if ship.hp <= 0:
                self._on_game_over()
                return

        # Refuel
        ship.fuel = min(MAX_FUEL, ship.fuel + LANDING_REFUEL)

        # Auto-launch upward
        ship.vy = -3.0
        ship.vx = random.uniform(-0.5, 0.5)

        # Spawn new pads
        self._refill_pads()

    def _on_crash_landing(self, pad: LandingPad) -> None:
        """Handle a crash landing (too fast or not upright)."""
        ship = self.ship
        self.combo = 0
        ship.hp = max(0, ship.hp - CRASH_DAMAGE)
        self._add_floating_text(
            ship.x, ship.y - 8,
            f"CRASH! -{CRASH_DAMAGE}",
            pyxel.COLOR_ORANGE,
        )
        self._spawn_crash_particles(ship.x, pad.y, pyxel.COLOR_ORANGE)
        self.screen_shake = 10

        # Bounce
        ship.vy = -abs(ship.vy) * 0.4
        ship.vx *= 0.5

        if ship.hp <= 0:
            self._on_game_over()
            return

        ship.fuel = min(MAX_FUEL, ship.fuel + LANDING_REFUEL * 0.5)
        self._refill_pads()

    def _on_game_over(self) -> None:
        """Transition to game over state."""
        self.phase = Phase.GAME_OVER
        self.screen_shake = 12
        if self.score > self.best_score:
            self.best_score = self.score
        # Save ghost trail of this run if it was the best
        if self.score >= self.best_score:
            self.ghost_trail = list(self.player_trail)

    def _update_land_pause(self) -> None:
        """Handle brief pause after landing."""
        self.land_timer -= 1
        if self.land_timer <= 0:
            self.phase = Phase.PLAYING

    def _update_particles(self) -> None:
        """Update particle positions and lifetimes."""
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.03  # particle gravity
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        """Update floating text positions."""
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _update_trail(self) -> None:
        """Record ship position for ghost trail."""
        if len(self.player_trail) < GHOST_TRAIL_MAX:
            self.player_trail.append(
                GhostPoint(x=self.ship.x, y=self.ship.y, angle=self.ship.angle)
            )

    # ── Particle helpers ──

    def _spawn_burst_particle(self, x: float, y: float, color: int) -> None:
        """Spawn a single burst particle in random direction."""
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(1.0, 3.0)
        self.particles.append(
            Particle(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 1.0,
                life=random.randint(12, 24),
                color=color,
                max_life=24,
            )
        )

    def _spawn_crash_particles(self, x: float, y: float, color: int) -> None:
        """Spawn crash particles."""
        for _ in range(10):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.5, 2.5)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed - 1.5,
                    life=random.randint(8, 18),
                    color=color,
                    max_life=18,
                )
            )

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        """Add floating score/damage text."""
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=40, color=color)
        )

    # ── Draw ──

    def draw(self) -> None:
        """Main draw loop."""
        shake_x = 0
        shake_y = 0
        if self.screen_shake > 0:
            shake_x = random.randint(-2, 2)
            shake_y = random.randint(-2, 2)

        pyxel.cls(pyxel.COLOR_BLACK)

        # Apply screen shake via camera offset
        try:
            pyxel.camera(shake_x, shake_y)
        except BaseException:
            pass

        self._draw_stars()
        self._draw_ghost_trail()
        self._draw_cavern()
        self._draw_pads()
        self._draw_ship()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()

        # Reset camera
        try:
            pyxel.camera(0, 0)
        except BaseException:
            pass

    def _draw_stars(self) -> None:
        """Draw background stars (deterministic from seed)."""
        for i in range(30):
            sx = (i * 73 + 17) % WIDTH
            sy = (i * 47 + 31) % HEIGHT
            brightness = 5 + (i % 4)
            pyxel.pset(sx, sy, brightness)

    def _draw_ghost_trail(self) -> None:
        """Draw ghost trail from previous best run."""
        step = max(1, len(self.ghost_trail) // 100)
        for i in range(0, len(self.ghost_trail), step):
            gp = self.ghost_trail[i]
            alpha = i / max(1, len(self.ghost_trail))
            c = pyxel.COLOR_GRAY if alpha < 0.66 else pyxel.COLOR_WHITE
            pyxel.pset(int(gp.x), int(gp.y), c)

    def _draw_cavern(self) -> None:
        """Draw cavern walls and floor."""
        # Ceiling
        pyxel.rect(0, 0, WIDTH, 4, pyxel.COLOR_NAVY)
        # Floor
        pyxel.rect(0, HEIGHT - 4, WIDTH, 4, pyxel.COLOR_BROWN)
        # Left wall
        pyxel.rect(0, 0, 2, HEIGHT, pyxel.COLOR_NAVY)
        # Right wall
        pyxel.rect(WIDTH - 2, 0, 2, HEIGHT, pyxel.COLOR_NAVY)
        # Floor surface line
        pyxel.line(2, PAD_Y + PAD_HEIGHT + 2, WIDTH - 2, PAD_Y + PAD_HEIGHT + 2, pyxel.COLOR_BROWN)

    def _draw_pads(self) -> None:
        """Draw landing pads."""
        for pad in self.pads:
            if not pad.active:
                continue
            # Pad body
            pyxel.rect(
                int(pad.left), int(pad.y),
                int(pad.width), PAD_HEIGHT,
                pad.color,
            )
            # Pad highlight (top edge)
            pyxel.line(
                int(pad.left), int(pad.y),
                int(pad.right) - 1, int(pad.y),
                pyxel.COLOR_WHITE,
            )
            # Pad label (value)
            label = f"{pad.value}"
            lx = int(pad.x) - len(label) * 2
            pyxel.text(lx, int(pad.y) - 7, label, pad.color)

    def _draw_ship(self) -> None:
        """Draw the player's ship."""
        ship = self.ship
        if ship.hp <= 0 and self.phase == Phase.GAME_OVER:
            return

        # Blink when damaged recently
        if self.screen_shake > 0 and self.screen_shake % 2 == 0:
            return

        nose = (ship.nose_x(), ship.nose_y())
        bl = ship.base_left()
        br = ship.base_right()

        # Ship body
        pyxel.tri(
            nose[0], nose[1],
            bl[0], bl[1],
            br[0], br[1],
            ship.color,
        )

        # Ship outline
        pyxel.tri(
            nose[0], nose[1],
            bl[0], bl[1],
            br[0], br[1],
            pyxel.COLOR_WHITE if ship.color_idx != 0 else pyxel.COLOR_BLACK,
        )

        # Color indicator dot at center
        pyxel.circ(int(ship.x), int(ship.y), 2, pyxel.COLOR_WHITE)
        pyxel.circ(int(ship.x), int(ship.y), 1, ship.color)

    def _draw_particles(self) -> None:
        """Draw particle effects."""
        for p in self.particles:
            alpha_ratio = p.life / max(1, p.max_life)
            c = p.color if alpha_ratio > 0.5 else pyxel.COLOR_GRAY
            pyxel.pset(int(p.x), int(p.y), c)

    def _draw_floating_texts(self) -> None:
        """Draw floating score/damage texts."""
        for ft in self.floating_texts:
            alpha = ft.life / 40
            c = ft.color if alpha > 0.3 else pyxel.COLOR_GRAY
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, c)

    def _draw_hud(self) -> None:
        """Draw HUD: fuel, HP, score, combo, ship color."""
        ship = self.ship

        # Top bar background
        pyxel.rect(0, 0, WIDTH, 14, pyxel.COLOR_BLACK)

        # Fuel bar
        fuel_pct = ship.fuel / MAX_FUEL
        fuel_color = pyxel.COLOR_GREEN if fuel_pct > 0.3 else pyxel.COLOR_RED
        pyxel.text(4, 3, "FUEL", pyxel.COLOR_GRAY)
        pyxel.rect(30, 4, 40, 6, pyxel.COLOR_NAVY)
        pyxel.rect(30, 4, int(40 * fuel_pct), 6, fuel_color)

        # HP bar
        hp_pct = ship.hp / MAX_HP
        hp_color = pyxel.COLOR_GREEN if hp_pct > 0.3 else pyxel.COLOR_RED
        pyxel.text(76, 3, "HP", pyxel.COLOR_GRAY)
        pyxel.rect(92, 4, 40, 6, pyxel.COLOR_NAVY)
        pyxel.rect(92, 4, int(40 * hp_pct), 6, hp_color)

        # Score
        pyxel.text(140, 3, f"SC:{self.score}", pyxel.COLOR_WHITE)

        # Combo
        if self.combo > 1:
            combo_color = pyxel.COLOR_YELLOW if self.combo >= 5 else pyxel.COLOR_GREEN
            pyxel.text(140, 3, f"SC:{self.score}", pyxel.COLOR_WHITE)
            pyxel.text(200, 3, f"x{self.combo}", combo_color)
        else:
            pyxel.text(200, 3, f"x{self.combo}", pyxel.COLOR_GRAY)

        # Ship color indicator
        pyxel.text(4, HEIGHT - 10, "COLOR:", pyxel.COLOR_GRAY)
        pyxel.rect(36, HEIGHT - 10, 10, 8, ship.color)
        pyxel.text(50, HEIGHT - 10, COLOR_NAMES[ship.color_idx], ship.color)

        # Controls hint
        pyxel.text(90, HEIGHT - 10, "Z:CHG COLOR  ARROWS:MOVE", pyxel.COLOR_GRAY)

    def _draw_game_over(self) -> None:
        """Draw game over screen overlay."""
        # Dim background
        for y in range(80, 160):
            for x in range(40, WIDTH - 40, 4):
                if (x + y) % 8 < 4:
                    pyxel.pset(x, y, pyxel.COLOR_NAVY)

        pyxel.text(WIDTH // 2 - 24, 100, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(WIDTH // 2 - 40, 115, f"SCORE: {self.score}", pyxel.COLOR_WHITE)
        pyxel.text(WIDTH // 2 - 40, 125, f"MAX COMBO: x{self.max_combo}", pyxel.COLOR_YELLOW)
        pyxel.text(WIDTH // 2 - 40, 135, f"BEST: {self.best_score}", pyxel.COLOR_GREEN)
        pyxel.text(WIDTH // 2 - 40, 150, "PRESS R TO RETRY", pyxel.COLOR_GRAY)


# ═══════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    Game()
