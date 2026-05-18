"""CHAIN CROSS — Color-match traffic intersection manager.

Reinterpreted from game_idea_factory #1 (score 32.35):
  Dice/bag-building roguelite / Space mining
  Hooks: synthesis compression + CA grid spread/control

Genre: Traffic control / intersection management (novel — none of 39
existing prototypes cover this).

Core mechanic: Match the signal color to approaching car colors so they
pass safely. Same-color consecutive safe passages build COMBO, unlocking
SUPER CLEAR. Non-matching cars crash, causing congestion (CA spread).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Config ───────────────────────────────────────────────────────────────
SCREEN_W = 240
SCREEN_H = 240
FPS = 60

# Intersection geometry (roads form a + shape)
ROAD_HALF = 18  # half-width of each road
CENTER_X = SCREEN_W // 2
CENTER_Y = SCREEN_H // 2
ROAD_LEFT = CENTER_X - ROAD_HALF
ROAD_RIGHT = CENTER_X + ROAD_HALF
ROAD_TOP = CENTER_Y - ROAD_HALF
ROAD_BOTTOM = CENTER_Y + ROAD_HALF

# Colors (pyxel int constants)
# pyxel color ints: 8=RED, 6=DARK_BLUE, 3=GREEN, 10=YELLOW, 2=PURPLE
COLOR_NAMES: tuple[str, ...] = ("RED", "BLUE", "GREEN", "YELLOW", "PURPLE")
COLOR_VALS: tuple[int, ...] = (8, 6, 3, 10, 2)
NUM_COLORS: int = len(COLOR_VALS)

# Car
CAR_SPEED = 1.0
CAR_W = 14  # horizontal car width
CAR_H = 8   # horizontal car height (vertical car uses CAR_H x CAR_W)

# Signal
SIGNAL_RADIUS = 12

# COMBO
COMBO_THRESHOLD = 3  # combo needed for SUPER CLEAR
SUPER_DURATION = 120  # frames (2 seconds at 60fps)
SUPER_SCORE_MULT = 3

# Heat / Congestion
HEAT_PER_CRASH = 15
HEAT_DECAY_PER_PASS = 2
HEAT_MAX = 100
HEAT_SPAWN_FAST = 70  # threshold for faster spawns
HEAT_SPAWN_FASTER = 90
SPAWN_INTERVAL_BASE = 50  # frames between spawns
SPAWN_INTERVAL_FAST = 30
SPAWN_INTERVAL_FASTER = 18

# Player HP
MAX_HP = 5

# Particles
MAX_PARTICLES = 60


# ── Data Classes ──────────────────────────────────────────────────────────

class Direction(Enum):
    """Which direction a car is coming from / going to."""
    DOWN = auto()   # spawned at top, moves down
    UP = auto()     # spawned at bottom, moves up
    RIGHT = auto()  # spawned at left, moves right
    LEFT = auto()   # spawned at right, moves left


@dataclass
class Car:
    """A car traveling through the intersection."""
    x: float
    y: float
    direction: Direction
    color_idx: int  # 0..NUM_COLORS-1

    @property
    def color_val(self) -> int:
        return COLOR_VALS[self.color_idx]

    @property
    def color_name(self) -> str:
        return COLOR_NAMES[self.color_idx]

    @property
    def is_vertical(self) -> bool:
        return self.direction in (Direction.DOWN, Direction.UP)

    @property
    def w(self) -> int:
        return CAR_H if self.is_vertical else CAR_W

    @property
    def h(self) -> int:
        return CAR_W if self.is_vertical else CAR_H

    @property
    def is_in_intersection(self) -> bool:
        """Check if car center has entered the intersection zone."""
        return (ROAD_LEFT <= self.x <= ROAD_RIGHT and
                ROAD_TOP <= self.y <= ROAD_BOTTOM)


@dataclass
class Particle:
    """Visual particle for crash / super effects."""
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class FloatingText:
    """Floating score/combo text."""
    x: float
    y: float
    text: str
    life: int
    color: int


# ── Phase Enum ────────────────────────────────────────────────────────────

class Phase(Enum):
    PLAYING = auto()
    GAME_OVER = auto()


# ── Game Class ────────────────────────────────────────────────────────────

class Game:
    """CHAIN CROSS — Color-match traffic intersection manager."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CHAIN CROSS", fps=FPS,
                   display_scale=2, capture_scale=2)
        self._rng = random.Random()
        self._signal_idx: int = 0
        self._cars: list[Car] = []
        self._particles: list[Particle] = []
        self._floating_texts: list[FloatingText] = []
        self._spawn_timer: int = 0
        self._super_timer: int = 0
        self._shake_frames: int = 0
        self._shake_intensity: int = 0
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.hp: int = MAX_HP
        self.heat: int = 0  # congestion heat 0-100
        self.phase: Phase = Phase.PLAYING
        self._frame: int = 0
        pyxel.run(self.update, self.draw)

    # ── State ─────────────────────────────────────────────────────────

    def reset(self) -> None:
        self._signal_idx = 0
        self._cars.clear()
        self._particles.clear()
        self._floating_texts.clear()
        self._spawn_timer = 0
        self._super_timer = 0
        self._shake_frames = 0
        self._shake_intensity = 0
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.hp = MAX_HP
        self.heat = 0
        self.phase = Phase.PLAYING
        self._frame = 0

    @property
    def is_super(self) -> bool:
        return self._super_timer > 0

    @property
    def signal_color(self) -> int:
        return COLOR_VALS[self._signal_idx]

    @property
    def signal_color_name(self) -> str:
        return COLOR_NAMES[self._signal_idx]

    # ── Spawning ──────────────────────────────────────────────────────

    def _spawn_interval(self) -> int:
        if self.heat >= HEAT_SPAWN_FASTER:
            return SPAWN_INTERVAL_FASTER
        if self.heat >= HEAT_SPAWN_FAST:
            return SPAWN_INTERVAL_FAST
        return SPAWN_INTERVAL_BASE

    def _spawn_car(self, direction: Direction) -> None:
        color_idx = self._rng.randint(0, NUM_COLORS - 1)
        if direction == Direction.DOWN:
            x = float(self._rng.randint(ROAD_LEFT + 4, ROAD_RIGHT - 4))
            y = float(-CAR_W)
        elif direction == Direction.UP:
            x = float(self._rng.randint(ROAD_LEFT + 4, ROAD_RIGHT - 4))
            y = float(SCREEN_H + CAR_W)
        elif direction == Direction.RIGHT:
            x = float(-CAR_W)
            y = float(self._rng.randint(ROAD_TOP + 4, ROAD_BOTTOM - 4))
        else:  # LEFT
            x = float(SCREEN_W + CAR_W)
            y = float(self._rng.randint(ROAD_TOP + 4, ROAD_BOTTOM - 4))
        self._cars.append(Car(x=x, y=y, direction=direction, color_idx=color_idx))

    # ── Car Logic ─────────────────────────────────────────────────────

    def _update_cars(self) -> None:
        """Move cars and check intersection passage."""
        for car in self._cars[:]:
            # Move car
            dx: float = 0.0
            dy: float = 0.0
            if car.direction == Direction.DOWN:
                dy = CAR_SPEED
            elif car.direction == Direction.UP:
                dy = -CAR_SPEED
            elif car.direction == Direction.RIGHT:
                dx = CAR_SPEED
            else:  # LEFT
                dx = -CAR_SPEED
            car.x += dx
            car.y += dy

            # Check if car has entered intersection center zone
            if car.is_in_intersection:
                self._resolve_car(car)
                self._cars.remove(car)
                continue

            # Remove off-screen cars (shouldn't normally happen)
            if (car.x < -20 or car.x > SCREEN_W + 20 or
                    car.y < -20 or car.y > SCREEN_H + 20):
                self._cars.remove(car)

    def _resolve_car(self, car: Car) -> None:
        """Handle car arrival at intersection."""
        if car.color_idx == self._signal_idx:
            # Match! Safe passage
            self._on_match(car)
        else:
            # Crash!
            self._on_crash(car)

    def _on_match(self, car: Car) -> None:
        """Car matches signal — safe passage, combo build."""
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo

        mult = SUPER_SCORE_MULT if self.is_super else 1
        points = 10 * self.combo * mult
        self.score += points

        # Reduce heat
        self.heat = max(0, self.heat - HEAT_DECAY_PER_PASS)

        # Spawn pass particles
        for _ in range(3):
            self._particles.append(Particle(
                x=car.x, y=car.y,
                vx=self._rng.uniform(-1, 1),
                vy=self._rng.uniform(-1, 1),
                life=10, color=car.color_val,
            ))

        # Floating score text
        txt = f"+{points}"
        if self.combo >= COMBO_THRESHOLD:
            txt = f"COMBO x{self.combo}!"
        elif self.is_super:
            txt = f"SUPER +{points}"
        self._floating_texts.append(FloatingText(
            x=car.x, y=car.y, text=txt, life=30,
            color=car.color_val,
        ))

        # Check SUPER CLEAR activation
        if self.combo >= COMBO_THRESHOLD and not self.is_super:
            self._activate_super()

    def _on_crash(self, car: Car) -> None:
        """Car doesn't match signal — collision, HP loss."""
        self.hp -= 1
        self.combo = 0
        self._super_timer = 0

        # Increase congestion heat (CA spread)
        self.heat = min(HEAT_MAX, self.heat + HEAT_PER_CRASH)

        # Crash particles (big burst)
        for _ in range(8):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1, 3)
            self._particles.append(Particle(
                x=car.x, y=car.y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=15, color=car.color_val,
            ))

        # Screen shake
        self._shake_frames = 8
        self._shake_intensity = 3

        # Floating text
        self._floating_texts.append(FloatingText(
            x=car.x, y=car.y, text="-1 HP", life=30,
            color=8,  # red
        ))

        if self.hp <= 0:
            self.phase = Phase.GAME_OVER

    def _activate_super(self) -> None:
        """Activate SUPER CLEAR mode."""
        self._super_timer = SUPER_DURATION
        # Burst particles from center
        for i in range(12):
            angle = i * math.pi * 2 / 12
            self._particles.append(Particle(
                x=CENTER_X, y=CENTER_Y,
                vx=math.cos(angle) * 2,
                vy=math.sin(angle) * 2,
                life=20, color=self.signal_color,
            ))
        self._floating_texts.append(FloatingText(
            x=CENTER_X, y=CENTER_Y - 10, text="SUPER CLEAR!",
            life=40, color=10,  # yellow
        ))

    # ── Particles ─────────────────────────────────────────────────────

    def _update_particles(self) -> None:
        for p in self._particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self._particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self._floating_texts[:]:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life <= 0:
                self._floating_texts.remove(ft)

    # ── Input ─────────────────────────────────────────────────────────

    def _handle_input(self) -> None:
        """Handle keyboard input for signal color changes."""
        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
            return

        # Number keys 1-5 or QWERT to set signal color
        for i in range(NUM_COLORS):
            key_num = getattr(pyxel, f'KEY_{i + 1}', None)
            key_letter: int | None = None
            letter_map = (pyxel.KEY_Q, pyxel.KEY_W, pyxel.KEY_E,
                         pyxel.KEY_R, pyxel.KEY_T)
            if i < len(letter_map):
                key_letter = letter_map[i]

            if (key_num is not None and pyxel.btnp(key_num)) or \
               (key_letter is not None and pyxel.btnp(key_letter)):
                self._signal_idx = i
                break

    # ── Update ────────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.GAME_OVER:
            self._handle_input()
            self._update_particles()
            self._update_floating_texts()
            return

        self._frame += 1
        self._handle_input()

        # SUPER timer
        if self._super_timer > 0:
            self._super_timer -= 1

        # Spawn new cars
        self._spawn_timer -= 1
        if self._spawn_timer <= 0:
            direction = self._rng.choice(list(Direction))
            self._spawn_car(direction)
            self._spawn_timer = self._spawn_interval()

            # On faster spawn rates, occasionally spawn from extra direction
            if self.heat >= HEAT_SPAWN_FAST and self._rng.random() < 0.3:
                d2 = self._rng.choice(list(Direction))
                self._spawn_car(d2)
            if self.heat >= HEAT_SPAWN_FASTER and self._rng.random() < 0.4:
                d3 = self._rng.choice(list(Direction))
                self._spawn_car(d3)

        # Natural heat decay (slow)
        if self._frame % 30 == 0:
            self.heat = max(0, self.heat - 1)

        self._update_cars()
        self._update_particles()
        self._update_floating_texts()

        # Screen shake decay
        if self._shake_frames > 0:
            self._shake_frames -= 1

    # ── Draw ──────────────────────────────────────────────────────────

    def _draw_roads(self) -> None:
        """Draw the intersection roads."""
        # Road surface (dark gray)
        road_color = 5  # gray
        # Vertical road
        pyxel.rect(ROAD_LEFT, 0, ROAD_RIGHT - ROAD_LEFT, SCREEN_H, road_color)
        # Horizontal road
        pyxel.rect(0, ROAD_TOP, SCREEN_W, ROAD_BOTTOM - ROAD_TOP, road_color)

        # Road edge lines
        edge_color = 13  # light gray
        # Vertical road edges
        pyxel.line(ROAD_LEFT, 0, ROAD_LEFT, SCREEN_H, edge_color)
        pyxel.line(ROAD_RIGHT, 0, ROAD_RIGHT, SCREEN_H, edge_color)
        # Horizontal road edges
        pyxel.line(0, ROAD_TOP, SCREEN_W, ROAD_TOP, edge_color)
        pyxel.line(0, ROAD_BOTTOM, SCREEN_W, ROAD_BOTTOM, edge_color)

        # Lane divider dashes
        dash_color = 10  # yellow
        for y in range(0, SCREEN_H, 8):
            pyxel.rect(CENTER_X - 1, y, 2, 4, dash_color)
        for x in range(0, SCREEN_W, 8):
            pyxel.rect(x, CENTER_Y - 1, 4, 2, dash_color)

    def _draw_cars(self) -> None:
        """Draw all cars."""
        for car in self._cars:
            px = int(car.x)
            py = int(car.y)
            c = car.color_val
            if car.is_vertical:
                pyxel.rect(px - CAR_H // 2, py - CAR_W // 2, CAR_H, CAR_W, c)
                # Windshield
                pyxel.rect(px - 2, py - CAR_W // 2 + 1, 4, CAR_W - 2, 7)
            else:
                pyxel.rect(px - CAR_W // 2, py - CAR_H // 2, CAR_W, CAR_H, c)
                # Windshield
                pyxel.rect(px - CAR_W // 2 + 1, py - 2, CAR_W - 2, 4, 7)

    def _draw_signal(self) -> None:
        """Draw the traffic signal at the intersection center."""
        cx = CENTER_X
        cy = CENTER_Y

        # Outer ring (dark)
        pyxel.circb(cx, cy, SIGNAL_RADIUS + 2, 1)
        # Signal light (current color)
        sig_color = self.signal_color
        if self.is_super:
            # Rainbow pulse in super mode
            pulse = (self._frame // 4) % NUM_COLORS
            sig_color = COLOR_VALS[pulse]
        pyxel.circ(cx, cy, SIGNAL_RADIUS, sig_color)
        # Inner highlight
        pyxel.circ(cx - 3, cy - 3, SIGNAL_RADIUS // 3, 7)

    def _draw_particles(self) -> None:
        """Draw particles."""
        for p in self._particles:
            size = max(1, p.life // 4)
            if size == 1:
                pyxel.pset(int(p.x), int(p.y), p.color)
            else:
                pyxel.rect(int(p.x) - size // 2, int(p.y) - size // 2,
                          size, size, p.color)

    def _draw_floating_texts(self) -> None:
        """Draw floating texts."""
        for ft in self._floating_texts:
            alpha = max(1, ft.life // 4 + 1)
            c = ft.color if alpha > 4 else 13  # fade to gray
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y),
                      ft.text, c)

    def _draw_hud(self) -> None:
        """Draw HUD: score, combo, HP, heat."""
        # Background bar at top
        pyxel.rect(0, 0, SCREEN_W, 10, 1)

        # Score
        pyxel.text(2, 2, f"SCORE:{self.score}", 7)
        # Combo
        combo_str = f"C:{self.combo}"
        pyxel.text(70, 2, combo_str, 10 if self.combo >= COMBO_THRESHOLD else 7)
        # Max combo
        pyxel.text(100, 2, f"MX:{self.max_combo}", 13)
        # HP
        hp_str = "HP:" + "|" * self.hp
        pyxel.text(150, 2, hp_str, 8)
        # Heat bar
        heat_w = 40
        pyxel.rect(SCREEN_W - heat_w - 2, 2, heat_w, 3, 5)
        heat_fill = int(heat_w * self.heat / HEAT_MAX)
        heat_c = 8 if self.heat >= HEAT_SPAWN_FAST else 10
        if heat_fill > 0:
            pyxel.rect(SCREEN_W - heat_w - 2, 2, heat_fill, 3, heat_c)

        # SUPER CLEAR indicator
        if self.is_super:
            remaining = self._super_timer // 10
            sup_text = f"SUPER {remaining // 6 + 1}s"
            pyxel.text(CENTER_X - len(sup_text) * 2, 12, sup_text, 10)

        # Signal color name at bottom
        pyxel.text(2, SCREEN_H - 8,
                  f"SIGNAL: {self.signal_color_name} (press 1-5)",
                  self.signal_color)

    def _draw_game_over(self) -> None:
        """Draw game over screen."""
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, 1)
        pyxel.text(CENTER_X - 20, CENTER_Y - 15, "GAME OVER", 8)
        pyxel.text(CENTER_X - 28, CENTER_Y, f"SCORE: {self.score}", 7)
        pyxel.text(CENTER_X - 28, CENTER_Y + 10,
                  f"MAX COMBO: {self.max_combo}", 10)
        pyxel.text(CENTER_X - 25, CENTER_Y + 25,
                  "PRESS R TO RETRY", 13)

    def _apply_shake(self) -> tuple[int, int]:
        """Return camera offset for screen shake."""
        if self._shake_frames > 0:
            ox = self._rng.randint(-self._shake_intensity,
                                   self._shake_intensity)
            oy = self._rng.randint(-self._shake_intensity,
                                   self._shake_intensity)
            return ox, oy
        return 0, 0

    def draw(self) -> None:
        pyxel.cls(0)  # black background

        ox, oy = self._apply_shake()
        if ox != 0 or oy != 0:
            try:
                pyxel.camera(ox, oy)
            except BaseException:
                pass

        self._draw_roads()
        self._draw_cars()
        self._draw_signal()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()

        # Reset camera
        if ox != 0 or oy != 0:
            try:
                pyxel.camera(0, 0)
            except BaseException:
                pass


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> None:
    Game()


if __name__ == "__main__":
    main()
