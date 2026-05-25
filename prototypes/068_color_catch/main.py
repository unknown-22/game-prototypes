"""COLOR CATCH — Color-match catcher game.

Core fun moment: building COMBO by catching same-color objects
consecutively, then triggering SUPER CATCH mode with a 2x-wide catcher
and 3x scoring for massive score bursts.
Risk/reward: chase same-color for combo multiplier vs. safe catch
any color to avoid MISS penalty (5 misses = GAME OVER).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ──────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
DISPLAY_SCALE = 2
FPS = 30

CATCHER_Y = 220
CATCHER_W = 40
CATCHER_H = 8
CATCHER_W_SUPER = 80
CATCHER_SPEED = 200.0
CATCHER_COLOR = pyxel.COLOR_WHITE

OBJECT_SIZE = 12
OBJECT_SPEED_INITIAL = 60.0
OBJECT_SPEED_INCREASE = 5.0
SPAWN_INTERVAL_INITIAL = 0.8
SPAWN_INTERVAL_DECREASE = 0.05
SPAWN_INTERVAL_MIN = 0.3

OBJECT_COLORS: tuple[int, int, int, int] = (
    pyxel.COLOR_RED,       # 8
    pyxel.COLOR_GREEN,     # 3
    pyxel.COLOR_DARK_BLUE, # 5
    pyxel.COLOR_YELLOW,    # 10
)

MAX_MISSES = 5
SUPER_COMBO_THRESHOLD = 5
SUPER_DURATION = 5.0

BASE_CATCH_SCORE = 10

# ── Data Classes ───────────────────────────────────────────────────────

@dataclass
class FallingObject:
    x: float
    y: float
    color: int
    speed: float


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


# ── Phase Enum ─────────────────────────────────────────────────────────

class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ── Game Class ─────────────────────────────────────────────────────────

class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="COLOR CATCH", display_scale=DISPLAY_SCALE, fps=FPS)
        pyxel.mouse(False)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.misses: int = 0
        self.catcher_x: float = SCREEN_W / 2
        self.objects: list[FallingObject] = []
        self.particles: list[Particle] = []
        self._elapsed_time: float = 0.0
        self._spawn_timer: float = 0.0
        self._prev_catch_color: int | None = None
        self._super_timer: float = 0.0
        self._frame: int = 0

    # ── Pure Logic (Testable) ──────────────────────────────────────

    def _spawn_object(self) -> FallingObject:
        """Create a new falling object at random x with random color."""
        color = self._rng.choice(OBJECT_COLORS)
        x = self._rng.uniform(OBJECT_SIZE, SCREEN_W - OBJECT_SIZE)
        speed = self._get_current_object_speed(self._elapsed_time)
        return FallingObject(x=float(x), y=float(-OBJECT_SIZE), color=color, speed=speed)

    @staticmethod
    def _get_current_object_speed(elapsed: float) -> float:
        """Return object fall speed based on elapsed time."""
        level = int(elapsed // 10.0)
        return min(OBJECT_SPEED_INITIAL + level * OBJECT_SPEED_INCREASE, 200.0)

    @staticmethod
    def _get_spawn_interval(elapsed: float) -> float:
        """Return spawn interval based on elapsed time."""
        level = int(elapsed // 10.0)
        return max(SPAWN_INTERVAL_INITIAL - level * SPAWN_INTERVAL_DECREASE, SPAWN_INTERVAL_MIN)

    def _update_objects(self, dt: float) -> list[FallingObject]:
        """Move all objects down. Remove and return those that went off-screen."""
        missed: list[FallingObject] = []
        for obj in self.objects:
            obj.y += obj.speed * dt
        for obj in self.objects[:]:
            if obj.y > SCREEN_H + OBJECT_SIZE:
                self.objects.remove(obj)
                missed.append(obj)
        return missed

    def _check_catch(self, obj: FallingObject) -> bool:
        """Check if an object overlaps the catcher."""
        hw = self._catcher_width() / 2
        left = self.catcher_x - hw
        right = self.catcher_x + hw
        if not (obj.y + OBJECT_SIZE >= CATCHER_Y and obj.y <= CATCHER_Y + CATCHER_H):
            return False
        return left <= obj.x + OBJECT_SIZE / 2 <= right

    def _catcher_width(self) -> float:
        """Return current catcher width (normal or super)."""
        return float(CATCHER_W_SUPER) if self._super_timer > 0.0 else float(CATCHER_W)

    def _handle_catch(self, obj: FallingObject) -> int:
        """Handle catching an object. Returns points earned.
        Updates score, combo, super mode, and spawns particles."""
        super_mode = self._super_timer > 0.0

        if super_mode:
            self.combo += 1
        else:
            if self._prev_catch_color == obj.color:
                self.combo += 1
            else:
                self.combo = 1
            self._prev_catch_color = obj.color

        if self.combo > self.max_combo:
            self.max_combo = self.combo

        combo_mult = 1.0 + self.combo * 0.5
        points = int(BASE_CATCH_SCORE * combo_mult * (3 if super_mode else 1))
        self.score += points

        if not super_mode and self.combo >= SUPER_COMBO_THRESHOLD:
            self._super_timer = SUPER_DURATION

        count = 12 if super_mode else 6
        self._spawn_particles(obj.x, obj.y, obj.color, count)

        return points

    def _update_super_timer(self, dt: float) -> bool:
        """Decrement super timer. Returns True if super just ended."""
        if self._super_timer > 0.0:
            self._super_timer -= dt
            if self._super_timer <= 0.0:
                self._super_timer = 0.0
                self.combo = 0
                self._prev_catch_color = None
                return True
        return False

    def _update_particles(self) -> None:
        """Update particle positions and life."""
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        """Spawn burst particles at a position."""
        for _ in range(count):
            self.particles.append(Particle(
                x=float(x),
                y=float(y),
                vx=(self._rng.random() * 2 - 1) * 2.5,
                vy=(self._rng.random() * -1.5) * 2.0,
                color=color,
                life=12 + self._rng.randint(0, 8),
            ))

    def _handle_miss(self, obj: FallingObject) -> int:
        """Handle a missed object. Returns 1 if missed, updates state."""
        self.misses += 1
        self.combo = 0
        self._prev_catch_color = None
        self._spawn_particles(obj.x, SCREEN_H - 4, pyxel.COLOR_GRAY, 3)
        if self.misses >= MAX_MISSES:
            self.phase = Phase.GAME_OVER
        return 1

    # ── Update Helpers ─────────────────────────────────────────────

    def _start_game(self) -> None:
        """Initialize state and transition from TITLE to PLAYING."""
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.misses = 0
        self.catcher_x = SCREEN_W / 2
        self.objects.clear()
        self.particles.clear()
        self._elapsed_time = 0.0
        self._spawn_timer = 0.0
        self._prev_catch_color = None
        self._super_timer = 0.0
        self._frame = 0
        self.phase = Phase.PLAYING

    # ── Update ─────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self._start_game()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
            return

        # PLAYING phase
        self._frame += 1
        dt = 1.0 / FPS
        self._elapsed_time += dt

        # Input
        move_left = pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A)
        move_right = pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D)

        # Move catcher
        if move_left:
            self.catcher_x -= CATCHER_SPEED * dt
        if move_right:
            self.catcher_x += CATCHER_SPEED * dt
        hw = self._catcher_width() / 2
        self.catcher_x = max(hw, min(SCREEN_W - hw, self.catcher_x))

        # Spawn new objects
        interval = self._get_spawn_interval(self._elapsed_time)
        self._spawn_timer += dt
        while self._spawn_timer >= interval:
            self._spawn_timer -= interval
            self.objects.append(self._spawn_object())

        # Update object positions and detect misses
        missed = self._update_objects(dt)
        for obj in missed:
            self._handle_miss(obj)

        # Check catches
        for obj in self.objects[:]:
            if self._check_catch(obj):
                self._handle_catch(obj)
                self.objects.remove(obj)

        # Game over check (from misses in _handle_miss)
        if self.phase == Phase.GAME_OVER:
            return

        # Update super timer
        self._update_super_timer(dt)

        # Update particles
        self._update_particles()

    # ── Draw ────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_NAVY)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
            return

        # Objects
        for obj in self.objects:
            ox = int(obj.x - OBJECT_SIZE / 2)
            oy = int(obj.y - OBJECT_SIZE / 2)
            pyxel.rect(ox, oy, OBJECT_SIZE, OBJECT_SIZE, obj.color)
            pyxel.rectb(ox, oy, OBJECT_SIZE, OBJECT_SIZE, pyxel.COLOR_WHITE)

        # Catcher
        cw = int(self._catcher_width())
        cl = int(self.catcher_x - cw / 2)
        c_color = pyxel.COLOR_YELLOW if self._super_timer > 0.0 else CATCHER_COLOR
        pyxel.rect(cl, CATCHER_Y, cw, CATCHER_H, c_color)
        pyxel.rectb(cl, CATCHER_Y, cw, CATCHER_H, pyxel.COLOR_WHITE)

        # Particles
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

        # HUD
        self._draw_hud()

        # Super flash border
        if self._super_timer > 0.0 and (self._frame // 5) % 2 == 0:
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, pyxel.COLOR_YELLOW)
            pyxel.rectb(1, 1, SCREEN_W - 2, SCREEN_H - 2, pyxel.COLOR_YELLOW)

    def _draw_title(self) -> None:
        """Draw title screen."""
        title = "COLOR CATCH"
        pyxel.text(SCREEN_W // 2 - len(title) * 4 // 2, 50, title, pyxel.COLOR_WHITE)

        colors_label = "CATCH COLORS:"
        pyxel.text(SCREEN_W // 2 - len(colors_label) * 4 // 2, 75, colors_label, pyxel.COLOR_GRAY)
        # Draw example color blocks
        for i, color in enumerate(OBJECT_COLORS):
            bx = SCREEN_W // 2 - 30 + i * 16
            pyxel.rect(bx, 88, 12, 12, color)
            pyxel.rectb(bx, 88, 12, 12, pyxel.COLOR_WHITE)

        instructions = [
            "ARROWS or A/D: Move catcher",
            "Catch same-color for COMBO!",
            "COMBO x5 = SUPER CATCH!",
            "5 MISSES = GAME OVER",
            "",
            "SPACE to Start",
        ]
        for i, line in enumerate(instructions):
            if line:
                pyxel.text(SCREEN_W // 2 - len(line) * 4 // 2, 115 + i * 12, line, pyxel.COLOR_GRAY)

    def _draw_game_over(self) -> None:
        """Draw game over screen."""
        pyxel.text(SCREEN_W // 2 - len("GAME OVER") * 4 // 2, 60, "GAME OVER", pyxel.COLOR_RED)

        pyxel.text(
            SCREEN_W // 2 - len(f"SCORE: {self.score}") * 4 // 2,
            90,
            f"SCORE: {self.score}",
            pyxel.COLOR_WHITE,
        )
        pyxel.text(
            SCREEN_W // 2 - len(f"MAX COMBO: {self.max_combo}") * 4 // 2,
            110,
            f"MAX COMBO: {self.max_combo}",
            pyxel.COLOR_ORANGE,
        )
        pyxel.text(
            SCREEN_W // 2 - len(f"MISSES: {self.misses}/{MAX_MISSES}") * 4 // 2,
            130,
            f"MISSES: {self.misses}/{MAX_MISSES}",
            pyxel.COLOR_GRAY,
        )

        pyxel.text(
            SCREEN_W // 2 - len("SPACE to Retry") * 4 // 2,
            200,
            "SPACE to Retry",
            pyxel.COLOR_WHITE,
        )

    def _draw_hud(self) -> None:
        """Draw HUD: score, combo, misses, super timer bar."""
        # Background
        pyxel.rect(0, 0, SCREEN_W, 24, pyxel.COLOR_NAVY)

        # Score (left)
        pyxel.text(4, 4, f"SCORE: {self.score}", pyxel.COLOR_WHITE)

        # Combo (center-left)
        combo_color = pyxel.COLOR_WHITE
        if self.combo >= 3:
            combo_color = pyxel.COLOR_ORANGE
        if self.combo >= SUPER_COMBO_THRESHOLD:
            combo_color = pyxel.COLOR_YELLOW
        combo_text = f"COMBO: {self.combo}"
        if self._super_timer > 0.0:
            combo_text = f"SUPER! {self.combo}"
        pyxel.text(SCREEN_W // 2 - len(combo_text) * 4 // 2, 4, combo_text, combo_color)

        # Misses (right)
        miss_color = pyxel.COLOR_WHITE
        if self.misses >= 3:
            miss_color = pyxel.COLOR_ORANGE
        if self.misses >= 4:
            miss_color = pyxel.COLOR_RED
        pyxel.text(SCREEN_W - 80, 4, f"MISS: {self.misses}/{MAX_MISSES}", miss_color)

        # Previous catch color indicator
        if self._prev_catch_color is not None and self._super_timer <= 0.0:
            pyxel.rect(4, 16, 8, 4, self._prev_catch_color)

        # Super timer bar
        if self._super_timer > 0.0:
            bar_w = 120
            bar_x = SCREEN_W // 2 - bar_w // 2
            bar_fill = int(bar_w * (self._super_timer / SUPER_DURATION))
            pyxel.rect(bar_x, 16, bar_w, 4, pyxel.COLOR_DARK_BLUE)
            pyxel.rect(bar_x, 16, bar_fill, 4, pyxel.COLOR_YELLOW)


# ── Entry Point ────────────────────────────────────────────────────────

def main() -> None:
    Game()


if __name__ == "__main__":
    main()
