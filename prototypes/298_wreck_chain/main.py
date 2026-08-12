"""WRECK CHAIN -- Wrecking ball demolition with COMBO chains.

一番面白い瞬間: 振り子の勢いで同色区画を連続破壊し COMBO を繋ぎ、
SUPER WRECK で虹色ボールが全てを粉砕する瞬間。
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# -- Constants --
SCREEN_W = 320
SCREEN_H = 240
FPS = 30
GAME_DURATION = 60  # seconds

# Colors (Pyxel palette ints)
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

BUILDING_COLORS: tuple[int, ...] = (RED, LIME, DARK_BLUE, YELLOW)

# Crane
CRANE_Y = 14
CABLE_LENGTH = 60
BALL_RADIUS = 6
CRANE_SPEED = 2.0

# Physics
GRAVITY = 0.4
DAMPING = 0.995
BASE_DAMAGE = 1.0

# Scoring
BASE_SCORE = 10
DEBRIS_BONUS = 5
SUPER_COMBO_THRESHOLD = 4
SUPER_DURATION = 300  # frames (10 sec at 30fps)
SUPER_MULTIPLIER = 3

# HEAT
HEAT_MAX = 100.0
HEAT_MISS = 10.0
HEAT_DECAY = 0.02  # per frame

# Screen zones
PLAY_LEFT = 0
PLAY_RIGHT = 320
PLAY_TOP = 30
PLAY_BOTTOM = 210
GROUND_Y = 210

# Building
SEGMENT_W = 16
SEGMENT_H = 16
SEGMENT_HP = 1.0
BUILDING_GAP = 8

# Spawning
SPAWN_INTERVAL_START = 180  # frames
SPAWN_INTERVAL_END = 60
MAX_SEGMENTS = 18

# Particles
PARTICLE_HIT_COUNT = 6
PARTICLE_DESTROY_COUNT = 12
PARTICLE_DEBRIS_COUNT = 8

# Screen shake
SHAKE_DURATION = 6
SHAKE_AMPLITUDE = 2


# -- Enums --
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# -- Dataclasses --
@dataclass
class BuildingSegment:
    x: float
    y: float
    w: int
    h: int
    color: int
    hp: float
    weakened: bool


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int
    max_life: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int


# -- Pure functions (testable without pyxel) --
def compute_score(
    combo: int, weakened: bool, super_mode: bool, base: int = BASE_SCORE
) -> int:
    """Pure score computation."""
    multiplier = combo
    if weakened:
        multiplier *= 2
    if super_mode:
        multiplier *= 3
    return base * multiplier


def check_collision(
    ball_x: float, ball_y: float, ball_r: int,
    seg_x: float, seg_y: float, seg_w: int, seg_h: int,
) -> bool:
    """Circle vs AABB collision."""
    nearest_x = max(seg_x - seg_w / 2, min(ball_x, seg_x + seg_w / 2))
    nearest_y = max(seg_y - seg_h / 2, min(ball_y, seg_y + seg_h / 2))
    dx = ball_x - nearest_x
    dy = ball_y - nearest_y
    return dx * dx + dy * dy <= ball_r * ball_r


def compute_heat_game_over(heat: float) -> bool:
    """Check if heat exceeds max."""
    return heat >= HEAT_MAX


def compute_timer_game_over(timer: int) -> bool:
    """Check if timer has expired."""
    return timer <= 0


# -- Game Class --
class Game:
    """Pure game logic — pyxel calls only in update/draw/__init__."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="WRECK CHAIN", fps=FPS, display_scale=2)
        self.rng = random.Random()
        self.best_score = 0
        self._init_state()
        pyxel.run(self.update, self.draw)

    def _init_state(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = GAME_DURATION * FPS
        self.crane_x = float(SCREEN_W // 2)
        self.ball_x = self.crane_x
        self.ball_y = CRANE_Y + CABLE_LENGTH
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.ball_released = False
        self.last_hit_color: int | None = None
        self.super_mode = False
        self.super_timer = 0
        self.spawn_timer = SPAWN_INTERVAL_START
        self.shake_timer = 0
        self.segments: list[BuildingSegment] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._spawn_building()

    def reset(self) -> None:
        best = self.best_score
        self.rng = random.Random()
        self._init_state()
        self.best_score = best

    # -- Physics --
    def _update_physics(self) -> None:
        """Update ball pendulum physics."""
        if not self.ball_released:
            self.ball_x = self.crane_x
            self.ball_y = CRANE_Y + CABLE_LENGTH
            self.ball_vx = 0.0
            self.ball_vy = 0.0
            return

        self.ball_vy += GRAVITY
        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy

        # Constrain to cable length
        dx = self.ball_x - self.crane_x
        dy = self.ball_y - CRANE_Y
        dist = math.hypot(dx, dy)
        if dist > 0 and dist > CABLE_LENGTH:
            self.ball_x = self.crane_x + dx / dist * CABLE_LENGTH
            self.ball_y = CRANE_Y + dy / dist * CABLE_LENGTH
            # Project velocity onto tangent
            nx = dx / dist
            ny = dy / dist
            dot = self.ball_vx * nx + self.ball_vy * ny
            if dot < 0:
                self.ball_vx -= dot * nx
                self.ball_vy -= dot * ny

        self.ball_vx *= DAMPING
        self.ball_vy *= DAMPING

    def _update_crane(self, dx: float) -> None:
        """Move crane left/right. dx from input."""
        self.crane_x += dx * CRANE_SPEED
        self.crane_x = max(20.0, min(float(SCREEN_W - 20), self.crane_x))
        if not self.ball_released:
            self.ball_x = self.crane_x

    # -- Collisions --
    def _check_ball_collisions(self) -> None:
        """Check ball vs building segments. Apply damage."""
        hit_any = False
        for seg in self.segments:
            if seg.hp <= 0:
                continue
            if check_collision(
                self.ball_x, self.ball_y, BALL_RADIUS,
                seg.x, seg.y, seg.w, seg.h,
            ):
                self._damage_segment(seg)
                hit_any = True

        if not hit_any and self.ball_released:
            # Check if ball swung without hitting (moved significantly)
            ball_dist = math.hypot(self.ball_x - self.crane_x, self.ball_y - CRANE_Y)
            if ball_dist > CABLE_LENGTH * 0.4:
                self.heat += HEAT_MISS

    def _damage_segment(self, seg: BuildingSegment) -> None:
        """Apply damage to a segment. Update combo on every hit, score on destroy."""
        dmg = BASE_DAMAGE
        if seg.weakened:
            dmg *= 2.0
        seg.hp -= dmg

        color_matched = (
            self.last_hit_color is None
            or self.super_mode
            or self.last_hit_color == seg.color
        )

        if color_matched:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            self.last_hit_color = seg.color
        else:
            self.combo = 1
            self.last_hit_color = seg.color

        if seg.hp <= 0:
            self._on_segment_destroyed(seg)
        else:
            self._spawn_hit_particles(seg)

    def _on_segment_destroyed(self, seg: BuildingSegment) -> None:
        """Handle segment destruction: score, particles, weakening."""
        pts = compute_score(self.combo, seg.weakened, self.super_mode)
        self.score += pts

        if self.combo >= SUPER_COMBO_THRESHOLD and not self.super_mode:
            self.super_mode = True
            self.super_timer = SUPER_DURATION

        # Spawn particles
        self._spawn_destroy_particles(seg)
        self._spawn_floating_text(seg.x, seg.y - 8, f"+{pts}", YELLOW, 20)

        # Debris bonus
        if self.rng.random() < 0.5:
            self.score += DEBRIS_BONUS
            self._spawn_floating_text(
                seg.x + self.rng.randint(-10, 10), seg.y - 2, f"+{DEBRIS_BONUS}", CYAN, 15
            )

        # Weaken adjacent same-color segments
        self._weaken_adjacent(seg)
        self._shake()

    def _weaken_adjacent(self, destroyed: BuildingSegment) -> None:
        """Weaken adjacent segments of the same color."""
        for seg in self.segments:
            if seg is destroyed or seg.hp <= 0:
                continue
            if seg.color != destroyed.color:
                continue
            dist = math.hypot(seg.x - destroyed.x, seg.y - destroyed.y)
            if dist < SEGMENT_W * 2.0:
                seg.weakened = True

    # -- Combo / Super --
    def _update_super_mode(self) -> None:
        """Decrement super timer. Deactivate when expired."""
        if not self.super_mode:
            return
        self.super_timer -= 1
        if self.super_timer <= 0:
            self.super_mode = False
            self.super_timer = 0

    # -- Building Spawning --
    def _spawn_building(self) -> None:
        """Spawn a new building (stack of segments) from the bottom."""
        if len(self.segments) >= MAX_SEGMENTS:
            return

        # Pick a column for this building
        num_cols = (SCREEN_W - 40) // (SEGMENT_W + BUILDING_GAP)
        col = self.rng.randint(0, num_cols - 1)
        x = 20 + col * (SEGMENT_W + BUILDING_GAP) + SEGMENT_W // 2

        # Check if there's already a building here
        for seg in self.segments:
            if seg.hp > 0 and abs(seg.x - x) < SEGMENT_W:
                return

        num_segments = self.rng.randint(2, 5)
        # Rarer buildings have more segments over time
        progress = 1.0 - (self.timer / (GAME_DURATION * FPS))
        if progress > 0.5:
            num_segments = self.rng.randint(3, 6)

        color = BUILDING_COLORS[self.rng.randint(0, len(BUILDING_COLORS) - 1)]
        for i in range(num_segments):
            seg_x = float(x)
            seg_y = float(GROUND_Y - SEGMENT_H // 2 - i * SEGMENT_H)
            self.segments.append(
                BuildingSegment(
                    x=seg_x, y=seg_y, w=SEGMENT_W, h=SEGMENT_H,
                    color=color, hp=SEGMENT_HP, weakened=False,
                )
            )

    # -- Segment Management --
    def _update_segments(self) -> None:
        """Remove destroyed segments."""
        self.segments = [s for s in self.segments if s.hp > 0]

    # -- Particle Management --
    def _spawn_hit_particles(self, seg: BuildingSegment) -> None:
        self._spawn_particles_at(seg.x, seg.y, seg.color, PARTICLE_HIT_COUNT)

    def _spawn_destroy_particles(self, seg: BuildingSegment) -> None:
        self._spawn_particles_at(seg.x, seg.y, seg.color, PARTICLE_DESTROY_COUNT)

    def _spawn_particles_at(
        self, cx: float, cy: float, color: int, count: int
    ) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.pi * 2)
            speed = self.rng.uniform(1.0, 3.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - self.rng.uniform(0.5, 2.0)
            life = self.rng.randint(8, 20)
            self.particles.append(Particle(cx, cy, vx, vy, color, life, life))

    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int, life: int = 30
    ) -> None:
        self.floating_texts.append(FloatingText(float(x), float(y), text, color, life))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1  # slight gravity on particles
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.8
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # -- HEAT --
    def _update_heat(self) -> None:
        """Decay heat and check game over."""
        if compute_heat_game_over(self.heat):
            self._game_over("OVERHEAT!")
            return
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    # -- Timer --
    def _update_timer(self) -> None:
        """Decrement timer, check game over."""
        self.timer -= 1
        if compute_timer_game_over(self.timer):
            self._game_over("TIME'S UP!")

    def _game_over(self, reason: str) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score
        self.floating_texts.append(
            FloatingText(float(SCREEN_W // 2), float(SCREEN_H // 2), reason, RED, 90)
        )

    # -- Screen Shake --
    def _shake(self) -> None:
        self.shake_timer = SHAKE_DURATION

    # -- Update --
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.phase = Phase.PLAYING
                self.timer = GAME_DURATION * FPS
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
                self.phase = Phase.PLAYING
            return

        if self.phase != Phase.PLAYING:
            return

        # Input
        dx = 0.0
        if pyxel.btn(pyxel.KEY_LEFT):
            dx -= 1.0
        if pyxel.btn(pyxel.KEY_RIGHT):
            dx += 1.0
        self._update_crane(dx)

        if pyxel.btnp(pyxel.KEY_SPACE):
            self.ball_released = not self.ball_released

        # Physics
        self._update_physics()

        # Collisions
        self._check_ball_collisions()

        # Super mode
        self._update_super_mode()

        # Timer & Heat
        self._update_timer()
        self._update_heat()

        # Segment cleanup
        self._update_segments()

        # Spawn buildings
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            progress = 1.0 - (self.timer / (GAME_DURATION * FPS))
            self._spawn_building()
            self.spawn_timer = int(
                SPAWN_INTERVAL_START
                + (SPAWN_INTERVAL_END - SPAWN_INTERVAL_START) * progress
            )
            self.spawn_timer = max(1, self.spawn_timer)

        # Particles & texts
        self._update_particles()
        self._update_floating_texts()

        # Shake
        if self.shake_timer > 0:
            self.shake_timer -= 1

    # -- Draw --
    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        if self.phase == Phase.GAME_OVER:
            self._draw_game()
            self._draw_game_over_overlay()
            return

        # Screen shake offset
        cam_x = 0
        cam_y = 0
        if self.shake_timer > 0:
            cam_x = self.rng.randint(-SHAKE_AMPLITUDE, SHAKE_AMPLITUDE)
            cam_y = self.rng.randint(-SHAKE_AMPLITUDE, SHAKE_AMPLITUDE)
        pyxel.camera(cam_x, cam_y)

        self._draw_game()
        pyxel.camera(0, 0)

    def _draw_title(self) -> None:
        title = "WRECK CHAIN"
        pyxel.text(SCREEN_W // 2 - 28, 70, title, YELLOW)

        instructions = [
            "LEFT/RIGHT: Move Crane",
            "SPACE: Release / Lock Ball",
            "",
            "Same-color hits = COMBO!",
            "Combo x4 = SUPER WRECK!",
            "Swing without hitting = HEAT up",
            "",
            "Press SPACE to Start",
        ]
        for i, line in enumerate(instructions):
            if line:
                tw = len(line) * pyxel.FONT_WIDTH  # type: ignore[attr-defined]
                pyxel.text(SCREEN_W // 2 - tw // 2, 105 + i * 12, line, WHITE)

    def _draw_game_over_overlay(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, BLACK)
        pyxel.text(SCREEN_W // 2 - 36, 60, "GAME OVER", RED)

        lines = [
            f"Score: {self.score}",
            f"Best: {self.best_score}",
            f"Max Combo: {self.max_combo}",
        ]
        for i, line in enumerate(lines):
            tw = len(line) * pyxel.FONT_WIDTH  # type: ignore[attr-defined]
            pyxel.text(SCREEN_W // 2 - tw // 2, 90 + i * 16, line, WHITE)

        pyxel.text(SCREEN_W // 2 - 52, 160, "Press SPACE to Retry", YELLOW)

    def _draw_game(self) -> None:
        # Sky gradient
        for row in range(PLAY_TOP, GROUND_Y):
            t = (row - PLAY_TOP) / (GROUND_Y - PLAY_TOP)
            sky_col = NAVY if t < 0.5 else PURPLE
            pyxel.line(0, row, SCREEN_W, row, sky_col)

        # Ground
        pyxel.rect(0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y, BROWN)
        pyxel.line(0, GROUND_Y, SCREEN_W, GROUND_Y, WHITE)

        # HUD background
        pyxel.rect(0, 0, SCREEN_W, PLAY_TOP, BLACK)

        # Score
        pyxel.text(4, 2, f"SCORE: {self.score}", WHITE)

        # Combo
        if self.combo > 1:
            combo_str = f"COMBO x{self.combo}"
            pyxel.text(SCREEN_W // 2 - 20, 2, combo_str, YELLOW)

        # SUPER indicator
        if self.super_mode:
            super_str = f"SUPER WRECK! {self.super_timer // FPS}s"
            rainbow_colors = [RED, ORANGE, YELLOW, LIME, CYAN, WHITE]
            hue = (pyxel.frame_count // 10) % len(rainbow_colors)
            pyxel.text(
                SCREEN_W // 2 - 40, 14, super_str, rainbow_colors[hue]
            )

        # Timer
        secs = max(0, self.timer // FPS)
        timer_str = f"{secs}s"
        timer_col = WHITE if secs > 10 else ORANGE if secs > 5 else RED
        pyxel.text(SCREEN_W - 30, 2, timer_str, timer_col)

        # HEAT bar
        heat_bar_x = SCREEN_W - 20
        heat_bar_y = 2
        heat_bar_w = 16
        heat_bar_h = 22
        heat_ratio = self.heat / HEAT_MAX
        heat_fill = int(heat_bar_h * heat_ratio)

        heat_col = GREEN if heat_ratio < 0.5 else (
            ORANGE if heat_ratio < 0.75 else RED
        )
        heat_fill_y = heat_bar_y + heat_bar_h - heat_fill
        if heat_fill > 0:
            pyxel.rect(heat_bar_x, heat_fill_y, heat_bar_w, heat_fill, heat_col)
        pyxel.rectb(heat_bar_x, heat_bar_y, heat_bar_w, heat_bar_h, WHITE)
        pyxel.text(SCREEN_W - 18, heat_bar_y - 1, "H", GRAY)

        # Crane (trolley at top)
        crane_w = 16
        crane_h = 8
        pyxel.rect(
            int(self.crane_x - crane_w // 2), CRANE_Y - crane_h // 2,
            crane_w, crane_h, GRAY,
        )
        pyxel.rectb(
            int(self.crane_x - crane_w // 2), CRANE_Y - crane_h // 2,
            crane_w, crane_h, WHITE,
        )

        # Cable
        ball_color = WHITE if not self.super_mode else self._rainbow_color()
        pyxel.line(
            int(self.crane_x), CRANE_Y,
            int(self.ball_x), int(self.ball_y),
            GRAY,
        )

        # Ball
        ball_r = BALL_RADIUS
        if self.super_mode:
            ball_r += int(math.sin(pyxel.frame_count * 0.3) * 2) + 1
            # Rainbow ring
            self._draw_rainbow_ball(self.ball_x, self.ball_y, ball_r)
        else:
            pyxel.circ(int(self.ball_x), int(self.ball_y), ball_r, ball_color)

        # Building segments
        for seg in self.segments:
            if seg.hp <= 0:
                continue
            sx = int(seg.x - seg.w // 2)
            sy = int(seg.y - seg.h // 2)
            color = seg.color
            if seg.weakened:
                pyxel.rectb(sx, sy, seg.w, seg.h, WHITE)
            pyxel.rect(sx, sy, seg.w, seg.h, color)

        # Particles
        for p in self.particles:
            alpha = p.life / p.max_life
            col = p.color if alpha > 0.3 else GRAY
            pyxel.pset(int(p.x), int(p.y), col)

        # Floating texts
        for ft in self.floating_texts:
            if ft.life > 0:
                tw = len(ft.text) * pyxel.FONT_WIDTH  # type: ignore[attr-defined]
                pyxel.text(int(ft.x - tw // 2), int(ft.y), ft.text, ft.color)

        # Ball state indicator
        if not self.ball_released:
            lock_str = "LOCKED"
            lw = len(lock_str) * pyxel.FONT_WIDTH  # type: ignore[attr-defined]
            pyxel.text(
                int(self.crane_x - lw // 2), CRANE_Y + 10, lock_str, GRAY
            )

    def _draw_rainbow_ball(self, cx: float, cy: float, r: int) -> None:
        """Draw ball with rainbow ring effect."""
        colors = [RED, ORANGE, YELLOW, LIME, CYAN]
        for i in range(3):
            rr = r - i
            if rr > 0:
                offset = (pyxel.frame_count // 5 + i) % len(colors)
                pyxel.circb(int(cx), int(cy), rr, colors[offset])
        pyxel.circ(int(cx), int(cy), r - 3, WHITE)

    def _rainbow_color(self) -> int:
        colors = [RED, ORANGE, YELLOW, LIME, CYAN, WHITE]
        return colors[(pyxel.frame_count // 10) % len(colors)]


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
