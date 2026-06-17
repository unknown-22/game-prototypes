"""PAPER PLANE TOSS — Side-view paper airplane throwing game.

Core mechanic: Click & drag to aim (angle + power), release to throw a paper airplane
that flies through colored rings. Same-color consecutive ring passes build COMBO -> SUPER FLIGHT.
Wrong-color passes break combo and accumulate HEAT. Score as high as possible in 90 seconds.

Most fun moment: lining up a throw that passes through 3+ same-color rings in a single flight,
triggering the COMBO chain with escalating score multiplier.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCREEN_W = 320
SCREEN_H = 240
GRAVITY = 0.15
DRAG = 0.995
LAUNCH_X = 50
LAUNCH_Y = 180
GROUND_Y = SCREEN_H - 20
RING_COLORS: tuple[int, ...] = (8, 3, 5, 10)  # RED, GREEN, DARK_BLUE, YELLOW
RING_RADIUS = 10
MAX_HEAT = 100
GAME_TIME = 90 * 30  # 90 seconds at 30fps
SUPER_DURATION = 5 * 30  # 5 seconds at 30fps
SUPER_COMBO_THRESHOLD = 5
BASE_SCORE = 100
HEAT_PER_WRONG = 15
HEAT_PER_FRAME = 1.0 / 30.0  # 1 heat per second
SUPER_SCORE_MULTIPLIER = 3.0
RESULT_DURATION = 45  # 1.5 seconds at 30fps
MIN_RINGS = 6
MAX_RINGS = 10
RING_MIN_X = 60
RING_MAX_X = 300
RING_MIN_Y = 30
RING_MAX_Y = 180
COMBO_MULTIPLIER_STEP = 0.5  # combo multiplier per combo: 1 + combo * 0.5


class Phase(Enum):
    TITLE = auto()
    AIMING = auto()
    FLIGHT = auto()
    RESULT = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Ring:
    x: float
    y: float
    color: int
    collected: bool = False
    radius: int = RING_RADIUS


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
    vy: float = -0.8


@dataclass
class Plane:
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    active: bool = False
    angle: float = 0.0


# ---------------------------------------------------------------------------
# Game class
# ---------------------------------------------------------------------------


class Game:
    """Main game class for PAPER PLANE TOSS."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="PAPER PLANE", display_scale=2)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.timer: int = GAME_TIME
        self.super_timer: int = 0
        self.super_active: bool = False
        self.plane: Plane = Plane()
        self.rings: list[Ring] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.aim_start_x: float = LAUNCH_X
        self.aim_start_y: float = LAUNCH_Y
        self.aim_end_x: float = LAUNCH_X
        self.aim_end_y: float = LAUNCH_Y
        self.aim_dragging: bool = False
        self.result_timer: int = 0
        self._prev_ring_color: int | None = None
        self._rng = random.Random()
        self._spawn_rings()

    # ---- Update dispatch ----

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.AIMING:
            self._update_aiming()
        elif self.phase == Phase.FLIGHT:
            self._update_flight()
        elif self.phase == Phase.RESULT:
            self._update_result()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

        self._update_particles()
        self._update_floating_texts()

    # ---- Draw dispatch ----

    def draw(self) -> None:
        pyxel.cls(6)  # LIGHT_BLUE sky
        pyxel.rect(0, GROUND_Y, SCREEN_W, 20, 3)  # GREEN ground
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.AIMING, Phase.FLIGHT, Phase.RESULT):
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game()
            self._draw_game_over_overlay()

    # ---- Title screen ----

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._start_game()

    def _start_game(self) -> None:
        self.reset()
        self.phase = Phase.AIMING
        self._prev_ring_color = None
        self.combo = 0

    def _draw_title(self) -> None:
        cx = SCREEN_W // 2
        pyxel.text(cx - 42, 50, "PAPER PLANE", 7)
        pyxel.text(cx - 52, 80, "Click & Drag to Aim", 7)
        pyxel.text(cx - 48, 95, "Release to Throw!", 7)
        pyxel.text(cx - 52, 120, "Fly through rings!", 7)
        pyxel.text(cx - 42, 135, "Same color = COMBO", 11)
        pyxel.text(cx - 42, 150, "Wrong color = HEAT", 8)
        pyxel.text(cx - 48, 175, "COMBO x5 = SUPER FLIGHT!", 10)
        pyxel.text(cx - 40, 200, "CLICK to START", 7)

    # ---- Aiming phase ----

    def _update_aiming(self) -> None:
        # Timer counts down during aiming too
        self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        # Heat decay
        self.heat = max(0.0, self.heat - HEAT_PER_FRAME * 0.5)

        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER
            return

        # Super timer countdown
        self._update_super_timer()

        mx = pyxel.mouse_x
        my = pyxel.mouse_y

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.aim_dragging = True
            self.aim_start_x = LAUNCH_X
            self.aim_start_y = LAUNCH_Y
            self.aim_end_x = mx
            self.aim_end_y = my

        if self.aim_dragging and pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
            self.aim_end_x = mx
            self.aim_end_y = my

        if self.aim_dragging and pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT):
            self.aim_dragging = False
            self._launch_plane()

    def _launch_plane(self) -> None:
        dx = self.aim_end_x - self.aim_start_x
        dy = self.aim_end_y - self.aim_start_y

        # Clamp power (minimum velocity)
        power = math.sqrt(dx * dx + dy * dy)
        if power < 5:
            power = 5
            dx = 5
            dy = 0

        # Scale velocity
        scale = power / 30.0  # scale factor
        scale = min(scale, 4.0)  # max launch speed

        vx = dx / power * scale * 3
        vy = dy / power * scale * 3

        # Ensure there are rings to fly through
        if not self.rings:
            self._spawn_rings()

        self.plane.x = LAUNCH_X
        self.plane.y = LAUNCH_Y
        self.plane.vx = vx
        self.plane.vy = vy
        self.plane.active = True
        self.plane.angle = math.atan2(vy, vx)
        self._prev_ring_color = None
        self.phase = Phase.FLIGHT

    # ---- Flight phase ----

    def _update_flight(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        self._update_super_timer()

        # Physics
        self._apply_flight_physics()

        plane = self.plane
        plane.angle = math.atan2(plane.vy, plane.vx)

        # Check ring collisions (only collect one ring per frame)
        hit_ring = self._check_ring_collisions()
        if hit_ring is not None:
            self._collect_ring(hit_ring)

        # Heat accumulation during flight
        self.heat += HEAT_PER_FRAME
        if self.heat >= MAX_HEAT:
            self.heat = MAX_HEAT
            self.phase = Phase.GAME_OVER
            return

        # End flight conditions
        if plane.y >= GROUND_Y:
            self._end_flight()
        elif plane.x < -30 or plane.x > SCREEN_W + 30 or plane.y < -30:
            self._end_flight()

    def _apply_flight_physics(self) -> None:
        """Apply gravity and drag to the plane. (Testable)"""
        self.plane.vy += GRAVITY
        self.plane.vx *= DRAG
        self.plane.x += self.plane.vx
        self.plane.y += self.plane.vy

    def _end_flight(self) -> None:
        self.plane.active = False
        self.rings.clear()
        self._spawn_rings()
        self.result_timer = RESULT_DURATION
        self.phase = Phase.RESULT

    def _check_ring_collisions(self) -> Ring | None:
        """Return the first uncollected ring the plane passes through, or None."""
        px = self.plane.x
        py = self.plane.y
        for ring in self.rings:
            if ring.collected:
                continue
            # Check if center of ring and some points around the plane body are within radius
            if self._plane_passes_ring(px, py, ring):
                return ring
        return None

    @staticmethod
    def _plane_passes_ring(px: float, py: float, ring: Ring) -> bool:
        """Check if a point (plane center) is within the ring's radius."""
        dx = px - ring.x
        dy = py - ring.y
        return (dx * dx + dy * dy) <= ring.radius * ring.radius

    def _collect_ring(self, ring: Ring) -> None:
        """Handle ring collection, combo logic, super activation, scoring."""
        ring.collected = True
        ring_color = ring.color

        if self.super_active:
            # In super, all colors count as match
            is_match = True
        elif self._prev_ring_color is None:
            is_match = True
        else:
            is_match = ring_color == self._prev_ring_color

        if is_match:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            # Combo multiplier: 1 + (combo - 1) * 0.5
            combo_mul = 1.0 + (self.combo - 1) * COMBO_MULTIPLIER_STEP
            super_mul = SUPER_SCORE_MULTIPLIER if self.super_active else 1.0
            points = int(BASE_SCORE * combo_mul * super_mul)
            self.score += points

            # Floating text
            self._spawn_floating_text(ring.x, ring.y - 5, f"+{points}", 7)
            if self.combo >= 3:
                self._spawn_floating_text(ring.x, ring.y - 20, f"COMBO x{self.combo}!", 11)

            # Particles
            self._spawn_particles(ring.x, ring.y, ring_color, 8)

            # Check SUPER FLIGHT activation
            if self.combo >= SUPER_COMBO_THRESHOLD and not self.super_active:
                self._activate_super()

        else:
            # Wrong color: combo reset, heat up
            self.combo = 0
            self.heat = min(float(MAX_HEAT), self.heat + HEAT_PER_WRONG)
            self._spawn_particles(ring.x, ring.y, 8, 5)  # RED particles
            self._spawn_floating_text(ring.x, ring.y - 5, "+0", 8)

        self._prev_ring_color = ring_color

    def _compute_ring_score(self, ring_color: int) -> int:
        """Compute score for collecting a ring. (Testable)"""
        if self.super_active:
            is_match = True
        elif self._prev_ring_color is None:
            is_match = True
        else:
            is_match = ring_color == self._prev_ring_color

        if not is_match:
            return 0
        combo_mul = 1.0 + (self.combo) * COMBO_MULTIPLIER_STEP
        super_mul = SUPER_SCORE_MULTIPLIER if self.super_active else 1.0
        return int(BASE_SCORE * combo_mul * super_mul)

    def _activate_super(self) -> None:
        """Activate SUPER FLIGHT mode."""
        self.super_active = True
        self.super_timer = SUPER_DURATION
        self._spawn_particles(self.plane.x, self.plane.y, 10, 20)
        self._spawn_floating_text(
            SCREEN_W // 2 - 30, SCREEN_H // 2 - 20, "SUPER FLIGHT!", 10
        )
        for i, c in enumerate(RING_COLORS):
            self._spawn_floating_text(
                SCREEN_W // 2 - 25 + i * 14, SCREEN_H // 2,
                "*", c,
            )

    def _update_super_timer(self) -> None:
        """Update super timer; deactivate when expired."""
        if self.super_active:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_active = False
                self.super_timer = 0
                self.combo = 0

    # ---- Result phase ----

    def _update_result(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        self._update_super_timer()

        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER
            return

        self.result_timer -= 1
        if self.result_timer <= 0:
            self.phase = Phase.AIMING

    # ---- Game over screen ----

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._start_game()

    # ---- Ring spawning ----

    def _spawn_rings(self) -> None:
        """Spawn 6-10 rings at random positions, avoiding too much overlap."""
        count = self._rng.randint(MIN_RINGS, MAX_RINGS)
        for _ in range(count):
            self.rings.append(self._make_ring())

    def _make_ring(self) -> Ring:
        color = self._rng.choice(RING_COLORS)
        # Try to avoid extreme overlap
        for _ in range(20):
            x = self._rng.uniform(RING_MIN_X, RING_MAX_X)
            y = self._rng.uniform(RING_MIN_Y, RING_MAX_Y)
            collision = False
            for r in self.rings:
                dx = x - r.x
                dy = y - r.y
                if dx * dx + dy * dy < (RING_RADIUS * 3) ** 2:
                    collision = True
                    break
            if not collision:
                return Ring(x=x, y=y, color=color)
        # Fallback: just place it
        x = self._rng.uniform(RING_MIN_X, RING_MAX_X)
        y = self._rng.uniform(RING_MIN_Y, RING_MAX_Y)
        return Ring(x=x, y=y, color=color)

    # ---- Particle and floating text methods ----

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-2.0, 2.0),
                    vy=self._rng.uniform(-2.0, 2.0),
                    life=self._rng.randint(10, 25),
                    color=color,
                )
            )

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=30, color=color)
        )

    def _update_particles(self) -> None:
        surviving: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05  # slight gravity on particles
            p.life -= 1
            if p.life > 0:
                surviving.append(p)
        self.particles = surviving

    def _update_floating_texts(self) -> None:
        surviving: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life > 0:
                surviving.append(ft)
        self.floating_texts = surviving

    # ---- Drawing methods ----

    def _draw_game(self) -> None:
        self._draw_rings()
        self._draw_airplane()
        self._draw_trajectory()
        self._draw_particles_vis()
        self._draw_floating_texts_vis()
        self._draw_hud()

    def _draw_hud(self) -> None:
        # Top bar background
        pyxel.rect(0, 0, SCREEN_W, 24, 0)
        pyxel.line(0, 24, SCREEN_W, 24, 7)

        # Score (top-left)
        pyxel.text(4, 4, f"SCORE:{self.score}", 7)

        # Combo (top-center)
        combo_color = 7
        if self.combo >= SUPER_COMBO_THRESHOLD:
            combo_color = RING_COLORS[(pyxel.frame_count // 4) % 4]
        elif self.combo >= 3:
            combo_color = 10
        pyxel.text(SCREEN_W // 2 - 20, 4, f"COMBO x{self.combo}", combo_color)

        # Timer (top-right)
        secs = max(0, self.timer // 30)
        timer_color = 7
        if secs <= 10:
            timer_color = 8 if (pyxel.frame_count // 15) % 2 == 0 else 10
        elif secs <= 30:
            timer_color = 10
        pyxel.text(SCREEN_W - 48, 4, f"TIME {secs}s", timer_color)

        # SUPER indicator
        if self.super_active:
            sec = self.super_timer // 30 + 1
            c = RING_COLORS[(pyxel.frame_count // 3) % 4]
            pyxel.text(SCREEN_W // 2 - 25, 16, f"SUPER {sec}s", c)

        # HEAT bar (bottom)
        pyxel.rect(0, SCREEN_H - 10, SCREEN_W, 10, 0)
        bar_w = int(SCREEN_W * (self.heat / MAX_HEAT))
        heat_col = 3 if self.heat < 40 else 10 if self.heat < 70 else 8
        pyxel.rect(0, SCREEN_H - 10, bar_w, 10, heat_col)
        pyxel.rectb(0, SCREEN_H - 10, SCREEN_W, 10, 7)
        if self.heat > 0:
            pyxel.text(SCREEN_W // 2 - 10, SCREEN_H - 9, "HEAT", 0)

    def _draw_rings(self) -> None:
        for ring in self.rings:
            if ring.collected:
                continue
            pyxel.circb(int(ring.x), int(ring.y), ring.radius, ring.color)
            # Inner highlight dot
            pyxel.pset(int(ring.x), int(ring.y), ring.color)

    def _draw_airplane(self) -> None:
        if not self.plane.active and self.phase != Phase.AIMING:
            return

        if self.phase == Phase.AIMING:
            # Draw plane at launch point
            self._draw_plane_tri(LAUNCH_X, LAUNCH_Y, 0.0, 7)
            return

        px = int(self.plane.x)
        py = int(self.plane.y)
        angle = self.plane.angle

        color = 7
        if self.super_active:
            color = RING_COLORS[(pyxel.frame_count // 3) % 4]
        elif abs(self.plane.angle) > 1.0:
            color = 7 if (pyxel.frame_count // 10) % 2 == 0 else 13

        self._draw_plane_tri(px, py, angle, color)

    @staticmethod
    def _draw_plane_tri(x: float, y: float, angle: float, color: int) -> None:
        """Draw a paper airplane as a triangle oriented by angle."""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        ix = int(x)
        iy = int(y)

        # Nose at front (direction of angle)
        nose_x = ix + cos_a * 10
        nose_y = iy + sin_a * 10

        # Wings at back (perpendicular to angle)
        wing_x1 = ix - cos_a * 6 + sin_a * 6
        wing_y1 = iy - sin_a * 6 - cos_a * 6
        wing_x2 = ix - cos_a * 6 - sin_a * 6
        wing_y2 = iy - sin_a * 6 + cos_a * 6

        pyxel.tri(
            nose_x, nose_y,
            wing_x1, wing_y1,
            wing_x2, wing_y2,
            color,
        )

    def _draw_trajectory(self) -> None:
        """Draw aim line and trajectory preview during AIMING phase."""
        if self.phase != Phase.AIMING:
            return

        # Draw aim line from launch point to mouse
        mx = self.aim_end_x
        my = self.aim_end_y

        # Dashed aim line
        lx, ly = LAUNCH_X, LAUNCH_Y
        dist = math.sqrt((mx - lx) ** 2 + (my - ly) ** 2)
        if dist < 1:
            return
        steps = int(dist / 6)
        for i in range(0, steps, 2):
            t = i / max(steps, 1)
            x1 = int(lx + (mx - lx) * t)
            y1 = int(ly + (my - ly) * t)
            t2 = (i + 1) / max(steps, 1)
            x2 = int(lx + (mx - lx) * t2)
            y2 = int(ly + (my - ly) * t2)
            pyxel.line(x1, y1, x2, y2, 7)

        # Trajectory preview (simulated dots)
        dx = mx - lx
        dy = my - ly
        power = math.sqrt(dx * dx + dy * dy)
        if power < 5:
            return
        scale = power / 30.0
        scale = min(scale, 4.0)
        vx = dx / power * scale * 3
        vy = dy / power * scale * 3
        px, py = float(lx), float(ly)
        for i in range(30):
            vy += GRAVITY
            vx *= DRAG
            px += vx
            py += vy
            if py >= GROUND_Y or px < 0 or px > SCREEN_W:
                break
            if i % 2 == 0:
                pyxel.pset(int(px), int(py), 13)

    def _draw_particles_vis(self) -> None:
        for p in self.particles:
            alpha = p.life / 25.0
            if alpha < 0.1:
                continue
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts_vis(self) -> None:
        for ft in self.floating_texts:
            if ft.life < 5:
                continue
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_game_over_overlay(self) -> None:
        # Semi-transparent overlay
        for y in range(0, SCREEN_H, 2):
            for x in range(0, SCREEN_W, 2):
                if (x // 2 + y // 2) % 2 == 0:
                    pyxel.pset(x, y, 0)

        cx = SCREEN_W // 2
        pyxel.text(cx - 28, 60, "GAME OVER", 8)
        pyxel.text(cx - 40, 85, f"SCORE: {self.score}", 7)
        pyxel.text(cx - 45, 102, f"MAX COMBO: {self.max_combo}", 10)
        if self.heat >= MAX_HEAT:
            pyxel.text(cx - 30, 124, "OVERHEATED!", 8)
        elif self.timer <= 0:
            pyxel.text(cx - 27, 124, "TIME'S UP!", 12)
        pyxel.text(cx - 40, 155, "CLICK to RETRY", 7)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
