from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum

import pyxel


# ---------------------------------------------------------------------------
# Colors (raw ints — pyxel 16-color palette)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class Ship:
    x: float
    y: float
    heading: float  # degrees, 0 = right, clockwise positive
    speed: float  # px/frame
    fuel: float  # frames remaining
    color: int
    trail: list[tuple[float, float]] = field(default_factory=list)
    id: int = 0


@dataclass
class Bay:
    x: int
    y: int
    radius: int


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


class Phase(Enum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


# ---------------------------------------------------------------------------
# Module-level pure functions
# ---------------------------------------------------------------------------
def ship_velocity(heading: float, speed: float) -> tuple[float, float]:
    """Return (vx, vy) for a heading in degrees and speed in px/frame."""
    rad = math.radians(heading)
    return math.cos(rad) * speed, math.sin(rad) * speed


def spawn_interval(frame: int) -> int:
    """Frames between spawns, ramping from 200 to 50."""
    return max(50, 200 - frame // 24)


def spawn_speed(frame: int) -> float:
    """Entry speed, ramping from 0.8 to 2.2."""
    return min(2.2, 0.8 + frame / 1800)


def dock_score(fuel_left: float, speed: float) -> int:
    """Score for docking with more fuel left and slower speed."""
    return 100 + int(fuel_left) // 60


class Game:
    # ------------------------------------------------------------------
    # Class-level constants
    # ------------------------------------------------------------------
    SCREEN_W = 320
    SCREEN_H = 240
    BAYS = [(40, 60), (160, 40), (280, 60)]
    BAY_RADIUS = 16
    SHIP_RADIUS = 4
    COLLIDE_DIST = 8
    DOCK_RADIUS = 16
    DOCK_SPEED_MAX = 0.9
    FUEL_START = 1800  # 30s of fuel
    FUEL_LOW = 300
    FUEL_CRIT = 120
    LIVES_START = 3
    GAME_DURATION = 3600  # 60s
    TURN_RATE = 3.0
    THROTTLE_ACCEL = 0.03
    SPEED_MIN = 0.0
    SPEED_MAX = 2.5
    NEAR_MISS = 14
    MAX_SHIPS = 6

    def __init__(self) -> None:
        pyxel.init(self.SCREEN_W, self.SCREEN_H, title="SPACE DOCK", fps=60)
        self.reset()
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------
    # State reset
    # ------------------------------------------------------------------
    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.ships: list[Ship] = []
        self.bays: list[Bay] = [
            Bay(x, y, self.BAY_RADIUS) for x, y in self.BAYS
        ]
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.score = 0
        self.lives = self.LIVES_START
        self.docked = 0
        self.lost = 0
        self.near_misses = 0
        self.frame = 0
        self.spawn_timer = 0
        self.next_ship_id = 0
        self.selected_index = -1
        self.best_score = getattr(self, "best_score", 0)
        self.shake = 0
        self.flash = 0
        self.rng = random.Random()
        self.game_over_reason = ""

    # ------------------------------------------------------------------
    # Pure gameplay methods (headless-testable)
    # ------------------------------------------------------------------
    def _spawn_ship(self) -> None:
        if len(self.ships) >= self.MAX_SHIPS:
            return
        edge = self.rng.randint(0, 3)
        if edge == 0:  # left
            x = 0.0
            y = float(self.rng.uniform(0, self.SCREEN_H))
        elif edge == 1:  # right
            x = float(self.SCREEN_W)
            y = float(self.rng.uniform(0, self.SCREEN_H))
        elif edge == 2:  # top
            x = float(self.rng.uniform(0, self.SCREEN_W))
            y = 0.0
        else:  # bottom
            x = float(self.rng.uniform(0, self.SCREEN_W))
            y = float(self.SCREEN_H)

        cx, cy = self.SCREEN_W / 2, self.SCREEN_H / 2
        heading = math.degrees(
            math.atan2(cy - y, cx - x)
        ) + self.rng.uniform(-20, 20)
        heading %= 360.0

        ship = Ship(
            x=x,
            y=y,
            heading=heading,
            speed=spawn_speed(self.frame),
            fuel=float(self.FUEL_START),
            color=WHITE,
            id=self.next_ship_id,
        )
        self.next_ship_id += 1
        self.ships.append(ship)

    def _update_ships(self, dt_frames: int = 1) -> None:
        for ship in self.ships:
            vx, vy = ship_velocity(ship.heading, ship.speed)
            ship.x += vx * dt_frames
            ship.y += vy * dt_frames
            ship.x %= self.SCREEN_W
            ship.y %= self.SCREEN_H
            ship.fuel -= dt_frames
            ship.trail.append((ship.x, ship.y))
            if len(ship.trail) > 24:
                ship.trail.pop(0)

    def _check_collisions(self) -> int:
        to_remove: set[int] = set()
        pairs: set[tuple[int, int]] = set()
        for i in range(len(self.ships)):
            for j in range(i + 1, len(self.ships)):
                a = self.ships[i]
                b = self.ships[j]
                dx = a.x - b.x
                dy = a.y - b.y
                dist = math.hypot(dx, dy)
                if dist < self.COLLIDE_DIST:
                    to_remove.add(i)
                    to_remove.add(j)
                    pairs.add((min(a.id, b.id), max(a.id, b.id)))
                    self._explode((a.x + b.x) / 2, (a.y + b.y) / 2, RED)
                    self._floating_text(
                        (a.x + b.x) / 2, (a.y + b.y) / 2, "CRASH", RED
                    )
                    self.shake = 6
                    self.flash = 4

        collisions = len(pairs)
        if to_remove:
            removed = 0
            new_ships = []
            for idx, ship in enumerate(self.ships):
                if idx in to_remove:
                    removed += 1
                else:
                    new_ships.append(ship)
            self.ships = new_ships
            self.lives -= 1
            self.lost += removed
        return collisions

    def _check_fuel(self) -> int:
        stranded: list[Ship] = []
        for ship in self.ships:
            if ship.fuel <= 0:
                stranded.append(ship)
        for ship in stranded:
            self.ships.remove(ship)
            self.lives -= 1
            self.lost += 1
            self._floating_text(ship.x, ship.y, "STRANDED", ORANGE)
        return len(stranded)

    def _check_docking(self) -> int:
        docked = 0
        remaining: list[Ship] = []
        for ship in self.ships:
            docked_this = False
            if ship.speed <= self.DOCK_SPEED_MAX:
                for bay in self.bays:
                    dx = ship.x - bay.x
                    dy = ship.y - bay.y
                    if math.hypot(dx, dy) <= self.DOCK_RADIUS:
                        self.score += dock_score(ship.fuel, ship.speed)
                        self.docked += 1
                        docked += 1
                        self._explode(ship.x, ship.y, LIME)
                        self._floating_text(ship.x, ship.y, "DOCKED", LIME)
                        docked_this = True
                        break
            if not docked_this:
                remaining.append(ship)
        self.ships = remaining
        return docked

    def _steer_selected(
        self,
        turn_left: bool,
        turn_right: bool,
        accel: bool,
        decel: bool,
    ) -> None:
        if self.selected_index < 0 or self.selected_index >= len(self.ships):
            self.selected_index = -1
            self._recolor_ships()
            return
        ship = self.ships[self.selected_index]
        if turn_left:
            ship.heading = (ship.heading - self.TURN_RATE) % 360.0
        if turn_right:
            ship.heading = (ship.heading + self.TURN_RATE) % 360.0
        if accel:
            ship.speed = min(ship.speed + self.THROTTLE_ACCEL, self.SPEED_MAX)
        if decel:
            ship.speed = max(ship.speed - self.THROTTLE_ACCEL, self.SPEED_MIN)
        self._recolor_ships()

    def _recolor_ships(self) -> None:
        for i, ship in enumerate(self.ships):
            ship.color = YELLOW if i == self.selected_index else WHITE

    def _select_at(self, mx: int, my: int) -> None:
        best_index = -1
        best_dist = float("inf")
        threshold = self.SHIP_RADIUS + 6
        for i, ship in enumerate(self.ships):
            dist = math.hypot(ship.x - mx, ship.y - my)
            if dist <= threshold and dist < best_dist:
                best_dist = dist
                best_index = i
        self.selected_index = best_index
        self._recolor_ships()

    def _check_game_over(self) -> None:
        if self.lives <= 0:
            self.phase = Phase.GAME_OVER
            self.game_over_reason = "ALL SHIPS LOST"
        elif self.frame >= self.GAME_DURATION:
            self.phase = Phase.GAME_OVER
            self.game_over_reason = "TIME UP"
        if self.phase == Phase.GAME_OVER:
            self.best_score = max(self.best_score, self.score)

    def _count_near_misses(self) -> None:
        counted: set[tuple[int, int]] = set()
        for i in range(len(self.ships)):
            for j in range(i + 1, len(self.ships)):
                a = self.ships[i]
                b = self.ships[j]
                if math.hypot(a.x - b.x, a.y - b.y) < self.NEAR_MISS:
                    counted.add((min(a.id, b.id), max(a.id, b.id)))
        for _ in counted:
            self.near_misses += 1
            self.score += 20

    # ------------------------------------------------------------------
    # Helpers for effects
    # ------------------------------------------------------------------
    def _explode(self, x: float, y: float, color: int) -> None:
        for _ in range(12):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(0.5, 2.5)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=self.rng.randint(15, 30),
                    color=color,
                )
            )

    def _floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=45, color=color)
        )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for t in self.floating_texts:
            t.y -= 0.4
            t.life -= 1
        self.floating_texts = [t for t in self.floating_texts if t.life > 0]

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.PLAYING
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.PLAYING
            return

        # PLAYING
        self.frame += 1

        if pyxel.btnp(pyxel.KEY_ESCAPE):
            self.phase = Phase.GAME_OVER
            self.game_over_reason = "TIME UP"
            self.best_score = max(self.best_score, self.score)
            return

        # Input
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._select_at(pyxel.mouse_x, pyxel.mouse_y)

        turn_left = pyxel.btn(pyxel.KEY_LEFT)
        turn_right = pyxel.btn(pyxel.KEY_RIGHT)
        accel = pyxel.btn(pyxel.KEY_UP)
        decel = pyxel.btn(pyxel.KEY_DOWN)
        self._steer_selected(turn_left, turn_right, accel, decel)

        # Spawning
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self._spawn_ship()
            self.spawn_timer = spawn_interval(self.frame)

        # Simulation
        self._update_ships()
        self._check_collisions()
        self._count_near_misses()
        self._check_fuel()
        self._check_docking()
        self._update_particles()
        self._update_floating_texts()

        if self.shake > 0:
            self.shake -= 1
        if self.flash > 0:
            self.flash -= 1

        self._check_game_over()

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------
    def draw(self) -> None:
        pyxel.cls(NAVY)

        if self.shake > 0:
            ox = self.rng.randint(-2, 2)
            oy = self.rng.randint(-2, 2)
            try:
                pyxel.camera(ox, oy)
            except BaseException:
                pass
        else:
            try:
                pyxel.camera(0, 0)
            except BaseException:
                pass

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

        # Flash overlay
        if self.flash > 0:
            pyxel.rect(0, 0, self.SCREEN_W, self.SCREEN_H, RED)

    def _draw_background(self) -> None:
        cx, cy = self.SCREEN_W / 2, self.SCREEN_H / 2
        for r in (40, 80, 120, 160):
            pyxel.circb(int(cx), int(cy), r, DARK_BLUE)
        pyxel.line(int(cx) - 160, int(cy), int(cx) + 160, int(cy), GRAY)
        pyxel.line(int(cx), int(cy) - 120, int(cx), int(cy) + 120, GRAY)

    def _draw_bays(self) -> None:
        for bay in self.bays:
            ring = GREEN
            if self.selected_index >= 0 and self.selected_index < len(self.ships):
                ship = self.ships[self.selected_index]
                if math.hypot(ship.x - bay.x, ship.y - bay.y) <= self.DOCK_RADIUS:
                    ring = YELLOW
            pyxel.circ(bay.x, bay.y, bay.radius, LIME)
            pyxel.circb(bay.x, bay.y, bay.radius, ring)

    def _draw_ships(self) -> None:
        for ship in self.ships:
            # trail
            for i, (tx, ty) in enumerate(ship.trail):
                c = LIGHT_BLUE
                if i % 3 == 0:
                    pyxel.pset(int(tx), int(ty), c)
            color = ship.color
            if ship.fuel <= self.FUEL_CRIT:
                if pyxel.frame_count % 8 < 4:
                    color = RED
                else:
                    color = WHITE
            elif ship.fuel <= self.FUEL_LOW:
                color = ORANGE

            # triangle rotated by heading
            rad = math.radians(ship.heading)
            tip_x = ship.x + math.cos(rad) * (self.SHIP_RADIUS + 2)
            tip_y = ship.y + math.sin(rad) * (self.SHIP_RADIUS + 2)
            left_angle = rad + math.radians(140)
            right_angle = rad - math.radians(140)
            lx = ship.x + math.cos(left_angle) * self.SHIP_RADIUS
            ly = ship.y + math.sin(left_angle) * self.SHIP_RADIUS
            rx = ship.x + math.cos(right_angle) * self.SHIP_RADIUS
            ry = ship.y + math.sin(right_angle) * self.SHIP_RADIUS
            pyxel.tri(
                int(tip_x), int(tip_y),
                int(lx), int(ly),
                int(rx), int(ry),
                color,
            )

        if self.selected_index >= 0 and self.selected_index < len(self.ships):
            ship = self.ships[self.selected_index]
            pyxel.circb(
                int(ship.x), int(ship.y), self.SHIP_RADIUS + 6, LIGHT_BLUE
            )

    def _draw_hud(self) -> None:
        # Score
        pyxel.text(4, 2, f"SCORE {self.score}", WHITE)
        pyxel.text(4, 10, f"DOCK {self.docked}", WHITE)
        pyxel.text(4, 18, f"LOST {self.lost}", WHITE)
        # Lives as hearts
        for i in range(self.lives):
            pyxel.text(4 + i * 8, 26, "O", RED)
        # Near misses
        pyxel.text(self.SCREEN_W - 76, 2, f"NEAR {self.near_misses}", YELLOW)

        # Timer bar
        frac = 1.0 - self.frame / self.GAME_DURATION
        bar_w = 100
        x = self.SCREEN_W // 2 - bar_w // 2
        color = LIME
        if frac < 0.3:
            color = RED
        elif frac < 0.6:
            color = YELLOW
        pyxel.rectb(x - 1, 3, bar_w + 2, 7, GRAY)
        pyxel.rect(x, 4, int(bar_w * frac), 5, color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for t in self.floating_texts:
            pyxel.text(int(t.x) - len(t.text) * 2, int(t.y), t.text, t.color)

    def _draw_playing(self) -> None:
        self._draw_background()
        self._draw_bays()
        self._draw_ships()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_title(self) -> None:
        pyxel.text(110, 60, "SPACE DOCK", WHITE)
        pyxel.text(96, 84, "CLICK SHIP TO SELECT", LIGHT_BLUE)
        pyxel.text(100, 96, "LEFT/RIGHT = TURN", WHITE)
        pyxel.text(102, 108, "UP/DOWN = THROTTLE", WHITE)
        pyxel.text(94, 120, "DOCK SLOWLY IN A BAY", LIME)
        pyxel.text(84, 140, "PRESS ENTER TO START", YELLOW)

    def _draw_game_over(self) -> None:
        pyxel.text(120, 60, "GAME OVER", RED)
        pyxel.text(96, 84, f"SCORE {self.score}", WHITE)
        pyxel.text(96, 96, f"DOCKED {self.docked}", WHITE)
        pyxel.text(96, 108, self.game_over_reason, ORANGE)
        pyxel.text(92, 120, f"BEST {self.best_score}", YELLOW)
        pyxel.text(80, 140, "PRESS ENTER TO RETRY", LIME)


if __name__ == "__main__":
    Game()
