from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel

# ── Constants ────────────────────────────────────────────────────────────────
WIDTH: int = 320
HEIGHT: int = 240
GRAVITY: float = 0.3
TERMINAL_VELOCITY: float = 6.0
PLAYER_RADIUS: int = 8
ZONE_W: float = 40.0
ZONE_H: float = 12.0
PLATFORM_W: int = 60
HEAT_MAX: float = 100.0
HEAT_DECAY: float = 0.02
HEAT_WRONG: float = 15.0
HEAT_MISS: float = 25.0
SUPER_DURATION: int = 300
GAME_TIME: int = 3600
COLOR_CYCLE_INTERVAL: int = 180
PLATFORM_RISE_AMOUNT: int = 8
MAX_PLATFORM_RISES: int = 5
BOUNCE_FACTOR: float = 20.0
CENTER_X: float = 160.0
SCORE_CENTER_BONUS_MAX: int = 50
PLAYER_SPEED: float = 1.5
PARTICLE_GRAVITY: float = 0.1
TRAIL_MAX_AGE: int = 120

# Color palette (raw ints)
BLACK: int = 0
NAVY: int = 1
PURPLE: int = 2
GREEN: int = 3
BROWN: int = 4
DARK_BLUE: int = 5
LIGHT_BLUE: int = 6
WHITE: int = 7
RED: int = 8
ORANGE: int = 9
YELLOW: int = 10
LIME: int = 11
CYAN: int = 12
GRAY: int = 13
PINK: int = 14
PEACH: int = 15

ZONE_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
SUPER_RAINBOW: list[int] = [RED, YELLOW, LIME, GREEN, CYAN, DARK_BLUE]

# ── Enums & Data Classes ─────────────────────────────────────────────────────


class Phase(Enum):
    TITLE = auto()
    FALLING = auto()
    RISING = auto()
    GAME_OVER = auto()


@dataclass
class LandingZone:
    x: float
    y: float
    w: float = ZONE_W
    h: float = ZONE_H
    color: int = RED
    active: bool = True


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


# ── Game Class ───────────────────────────────────────────────────────────────


class Game:
    _patched: ClassVar[bool] = False

    # Class-level type annotations (for type checker; values set in __new__)
    phase: Phase
    player_x: float
    player_y: float
    player_vy: float
    player_color: int
    anchor_x: float
    anchor_y: float
    platform_y: float
    zones: list[LandingZone]
    score: int
    combo: int
    max_combo: int
    best_combo: int
    heat: float
    super_timer: int
    game_timer: int
    color_idx: int
    color_cycle_timer: int
    landed_zone_idx: int
    particles: list[Particle]
    floating_texts: list[FloatingText]
    shake_frames: int
    ghost_trail: list[tuple[float, float, int]]
    rng: random.Random
    start_platform_y: float
    platform_rise_count: int
    fall_start_y: float
    rainbow_idx: int
    rainbow_timer: int
    cause: str

    def __new__(cls: type[Game]) -> Game:
        if not Game._patched:

            def _noop_init(  # noqa: F811
                w: int = 0,
                h: int = 0,
                title: str = "",
                fps: int = 60,
                display_scale: int = 1,
                capture_scale: int = 1,
                capture_sec: int = 0,
                quit_key: int = 0,
            ) -> None:
                pass

            setattr(pyxel, "init", _noop_init)  # type: ignore[arg-type]
            Game._patched = True

        obj = super().__new__(cls)
        # Pre-init all instance attributes for headless testing
        obj.phase = Phase.TITLE
        obj.player_x = CENTER_X
        obj.player_y = 60.0
        obj.player_vy = 0.0
        obj.player_color = WHITE
        obj.anchor_x = CENTER_X
        obj.anchor_y = 40.0
        obj.platform_y = 40.0
        obj.zones = []
        obj.score = 0
        obj.combo = 0
        obj.max_combo = 0
        obj.best_combo = 0
        obj.heat = 0.0
        obj.super_timer = 0
        obj.game_timer = GAME_TIME
        obj.color_idx = 0
        obj.color_cycle_timer = COLOR_CYCLE_INTERVAL
        obj.landed_zone_idx = -1
        obj.particles = []
        obj.floating_texts = []
        obj.shake_frames = 0
        obj.ghost_trail = []
        obj.rng = random.Random()
        obj.start_platform_y = 40.0
        obj.platform_rise_count = 0
        obj.fall_start_y = 60.0
        obj.rainbow_idx = 0
        obj.rainbow_timer = 0
        obj.cause = ""
        return obj

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def __init__(self) -> None:
        pyxel.init(WIDTH, HEIGHT, title="BUNGEE SURGE", display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.player_x = CENTER_X
        self.player_y = self.start_platform_y + 20
        self.player_vy = 0.0
        self.player_color = WHITE
        self.anchor_x = CENTER_X
        self.anchor_y = self.start_platform_y
        self.platform_y = self.start_platform_y
        self.platform_rise_count = 0
        self.zones = []
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.best_combo = 0
        self.heat = 0.0
        self.super_timer = 0
        self.game_timer = GAME_TIME
        self.color_idx = 0
        self.color_cycle_timer = COLOR_CYCLE_INTERVAL
        self.landed_zone_idx = -1
        self.particles = []
        self.floating_texts = []
        self.shake_frames = 0
        self.ghost_trail = []
        self.fall_start_y = 60.0
        self.rainbow_idx = 0
        self.rainbow_timer = 0
        self.cause = ""
        self._spawn_zones()

    # ── Update ─────────────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self._start_game()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
                self._start_game()
            return

        # Decrement game timer
        if self.game_timer > 0:
            self.game_timer -= 1
        if self.game_timer <= 0:
            self.phase = Phase.GAME_OVER
            self.cause = "TIME'S UP!"
            return

        # Update heat decay
        self.heat = max(0.0, self.heat - HEAT_DECAY)

        # Update super timer
        self._update_super_timer()

        # Update color cycle
        self._update_color_cycle()

        # Update ghost trail
        self._update_ghost_trail()

        # Update shake
        if self.shake_frames > 0:
            self.shake_frames -= 1

        # Update particles and floating texts
        self._update_particles()
        self._update_floating_texts()

        # Handle input and physics based on phase
        if self.phase == Phase.FALLING:
            if pyxel.btn(pyxel.KEY_LEFT):
                self._move_player(-PLAYER_SPEED)
            if pyxel.btn(pyxel.KEY_RIGHT):
                self._move_player(PLAYER_SPEED)

            self._apply_physics()
            zone_idx = self._check_landing()
            if zone_idx >= 0:
                self._resolve_landing(zone_idx)
            elif self.player_y >= HEIGHT - PLAYER_RADIUS:
                self._resolve_miss()

        elif self.phase == Phase.RISING:
            self._apply_physics()
            # Apex reached: velocity was negative, now >= 0 (player starts falling)
            if self.player_vy >= 0.0:
                self.fall_start_y = self.player_y
                self.phase = Phase.FALLING
                self._spawn_zones()

        # Check game over conditions
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            self.cause = "CORD SNAP!"
            self.shake_frames = 10
            self._spawn_cord_snap_particles()

    def _start_game(self) -> None:
        self.phase = Phase.FALLING
        self.player_y = self.platform_y + 20
        self.player_vy = 0.0
        self.fall_start_y = self.player_y
        self.game_timer = GAME_TIME
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_timer = 0
        self.particles.clear()
        self.floating_texts.clear()
        self.ghost_trail.clear()
        self._spawn_zones()

    # ── Physics ────────────────────────────────────────────────────────────

    def _apply_physics(self) -> None:
        self.player_vy += GRAVITY
        if self.player_vy > TERMINAL_VELOCITY:
            self.player_vy = TERMINAL_VELOCITY
        self.player_y += self.player_vy

    def _move_player(self, dx: float) -> None:
        self.player_x += dx
        self.player_x = max(PLAYER_RADIUS, min(WIDTH - PLAYER_RADIUS, self.player_x))

    # ── Landing Detection ──────────────────────────────────────────────────

    def _check_landing(self) -> int:
        for i, zone in enumerate(self.zones):
            if not zone.active:
                continue
            if (
                self.player_x + PLAYER_RADIUS >= zone.x
                and self.player_x - PLAYER_RADIUS <= zone.x + zone.w
                and self.player_y + PLAYER_RADIUS >= zone.y
                and self.player_y - PLAYER_RADIUS <= zone.y + zone.h
            ):
                return i
        return -1

    def _resolve_landing(self, zone_idx: int) -> None:
        zone = self.zones[zone_idx]
        zone.active = False
        self.landed_zone_idx = zone_idx

        is_match = zone.color == self.player_color
        is_super = self.super_timer > 0

        if is_super or is_match:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            if self.combo > self.best_combo:
                self.best_combo = self.combo

            # Calculate score
            distance_from_center = abs(zone.x + zone.w / 2 - CENTER_X)
            center_bonus = max(
                0, int(SCORE_CENTER_BONUS_MAX * (1 - distance_from_center / (WIDTH / 2)))
            )
            base_score = 100 + center_bonus
            combo_mult = 1.0 + 0.5 * min(self.combo, 4)
            if combo_mult > 3.0:
                combo_mult = 3.0
            landing_score = int(base_score * combo_mult)
            if is_super:
                landing_score *= 3

            self.score += landing_score

            # Floating score text
            self.floating_texts.append(
                FloatingText(zone.x + zone.w / 2, zone.y - 4, f"+{landing_score}", 40, WHITE)
            )
            if self.combo >= 2:
                self.floating_texts.append(
                    FloatingText(
                        zone.x + zone.w / 2, zone.y - 16, f"COMBO x{self.combo}", 40, YELLOW
                    )
                )

            # SUPER activation
            if self.combo >= 4 and self.super_timer == 0:
                self.super_timer = SUPER_DURATION
                self._spawn_super_particles()
                self.floating_texts.append(
                    FloatingText(CENTER_X, HEIGHT // 2, "SUPER BUNGEE!", 60, LIME)
                )

            # Landing particles
            particle_color = zone.color if is_match else YELLOW
            self._spawn_landing_particles(zone.x + zone.w / 2, zone.y, particle_color)

            # Platform rises
            if self.platform_rise_count < MAX_PLATFORM_RISES:
                self.platform_y -= PLATFORM_RISE_AMOUNT
                self.anchor_y = self.platform_y
                self.platform_rise_count += 1
        else:
            self.combo = 0
            self.heat += HEAT_WRONG
            self.floating_texts.append(
                FloatingText(zone.x + zone.w / 2, zone.y - 4, "WRONG!", 30, RED)
            )
            self._spawn_wrong_particles(zone.x + zone.w / 2, zone.y)

        self._bounce()
        self.phase = Phase.RISING

    def _resolve_miss(self) -> None:
        self.combo = 0
        self.heat += HEAT_MISS
        self.floating_texts.append(
            FloatingText(self.player_x, self.player_y - 8, "MISS!", 30, RED)
        )
        self._bounce()
        self.phase = Phase.RISING

    def _bounce(self) -> None:
        fall_distance = self.player_y - self.fall_start_y
        bounce_speed = GRAVITY * (fall_distance / BOUNCE_FACTOR)
        self.player_vy = -bounce_speed

    # ── Color Cycling ──────────────────────────────────────────────────────

    def _update_color_cycle(self) -> None:
        self.color_cycle_timer -= 1
        if self.color_cycle_timer <= 0:
            self.color_cycle_timer = COLOR_CYCLE_INTERVAL
            self._cycle_color()

        if self.super_timer > 0:
            self.rainbow_timer -= 1
            if self.rainbow_timer <= 0:
                self.rainbow_timer = 4
                self.rainbow_idx = (self.rainbow_idx + 1) % len(SUPER_RAINBOW)

    def _cycle_color(self) -> None:
        self.color_idx = (self.color_idx + 1) % len(ZONE_COLORS)
        self.player_color = ZONE_COLORS[self.color_idx]

    # ── Zones ──────────────────────────────────────────────────────────────

    def _spawn_zones(self) -> None:
        self.zones = []
        colors = list(ZONE_COLORS)
        self.rng.shuffle(colors)
        spacing = (WIDTH - 40) / 4
        for i in range(4):
            x = 20 + spacing * i + self.rng.uniform(-8, 8)
            x = max(10.0, min(WIDTH - ZONE_W - 10, x))
            self.zones.append(
                LandingZone(x=x, y=HEIGHT - ZONE_H - 10, color=colors[i])
            )

    # ── Super Timer ────────────────────────────────────────────────────────

    def _update_super_timer(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer == 0:
                self.combo = 0

    # ── Ghost Trail ────────────────────────────────────────────────────────

    def _update_ghost_trail(self) -> None:
        self.ghost_trail.append((self.player_x, self.player_y, 0))
        aged: list[tuple[float, float, int]] = []
        for x, y, age in self.ghost_trail:
            aged.append((x, y, age + 1))
        self.ghost_trail = [(x, y, a) for x, y, a in aged if a < TRAIL_MAX_AGE]

    # ── Particles ──────────────────────────────────────────────────────────

    def _spawn_landing_particles(self, x: float, y: float, color: int) -> None:
        count = self.rng.randint(8, 12)
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self.rng.uniform(-1.0, 1.0),
                    vy=self.rng.uniform(-2.0, 0.0),
                    life=self.rng.randint(15, 25),
                    color=color,
                )
            )

    def _spawn_wrong_particles(self, x: float, y: float) -> None:
        count = self.rng.randint(4, 6)
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self.rng.uniform(-1.5, 1.5),
                    vy=self.rng.uniform(-1.0, 1.0),
                    life=self.rng.randint(10, 15),
                    color=RED,
                )
            )

    def _spawn_super_particles(self) -> None:
        count = self.rng.randint(20, 30)
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=self.player_x,
                    y=self.player_y,
                    vx=self.rng.uniform(-3.0, 3.0),
                    vy=self.rng.uniform(-3.0, 1.0),
                    life=self.rng.randint(20, 30),
                    color=self.rng.choice(SUPER_RAINBOW),
                )
            )

    def _spawn_cord_snap_particles(self) -> None:
        count = self.rng.randint(30, 50)
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=self.player_x,
                    y=self.player_y,
                    vx=self.rng.uniform(-4.0, 4.0),
                    vy=self.rng.uniform(-4.0, 2.0),
                    life=self.rng.randint(15, 30),
                    color=self.rng.choice([RED, ORANGE]),
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.vy += PARTICLE_GRAVITY
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ── Floating Text ──────────────────────────────────────────────────────

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ── Drawing ────────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(NAVY)

        if self.shake_frames > 0:
            shake_x = self.rng.randint(-3, 3)
            shake_y = self.rng.randint(-3, 3)
            pyxel.camera(shake_x, shake_y)
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.FALLING, Phase.RISING):
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        else:
            self._draw_title()

    # ── Title Screen ───────────────────────────────────────────────────────

    def _draw_title(self) -> None:
        title = "BUNGEE SURGE"
        title_w = len(title) * 4
        pyxel.text(WIDTH // 2 - title_w // 2, 40, title, WHITE)

        instructions = [
            "Land same-color zones to build COMBO!",
            "COMBO x4 = SUPER BUNGEE",
            "(rainbow mode, 3x score!)",
            "",
            "LEFT / RIGHT : Steer during fall",
            "SPACE : Start / Retry",
        ]
        for i, line in enumerate(instructions):
            line_w = len(line) * 4
            pyxel.text(WIDTH // 2 - line_w // 2, 80 + i * 12, line, GRAY)

        pyxel.text(WIDTH // 2 - 40, 170, "Press SPACE to jump", WHITE)

        # Draw colored example zones
        for i, color in enumerate(ZONE_COLORS):
            zx = 40 + i * 70
            zy = 200
            pyxel.rect(zx, zy, ZONE_W, ZONE_H, color)
            pyxel.rectb(zx, zy, ZONE_W, ZONE_H, WHITE)

    # ── Game Screen ────────────────────────────────────────────────────────

    def _draw_game(self) -> None:
        # Platform
        px1 = self.anchor_x - PLATFORM_W // 2
        px2 = self.anchor_x + PLATFORM_W // 2
        pyxel.line(px1, self.platform_y, px2, self.platform_y, WHITE)

        # Bungee cord
        cord_color = GRAY
        if self.heat > 80:
            cord_color = RED
        elif self.heat > 50:
            cord_color = PURPLE
        pyxel.line(
            int(self.anchor_x),
            int(self.platform_y),
            int(self.player_x),
            int(self.player_y),
            cord_color,
        )

        # Ghost trail
        for x, y, age in self.ghost_trail:
            if age % 4 == 0:
                pyxel.circ(int(x), int(y), 2, GRAY)

        # Landing zones
        for zone in self.zones:
            if not zone.active:
                continue
            pyxel.rect(zone.x, zone.y, zone.w, zone.h, zone.color)
            pyxel.rectb(zone.x, zone.y, zone.w, zone.h, WHITE)

        # Player
        player_col = self.player_color
        if self.super_timer > 0:
            player_col = SUPER_RAINBOW[self.rainbow_idx]
        if self.super_timer > 0:
            pyxel.circ(int(self.player_x), int(self.player_y), PLAYER_RADIUS + 2, player_col)
            pyxel.circ(int(self.player_x), int(self.player_y), PLAYER_RADIUS, WHITE)
        else:
            pyxel.circ(int(self.player_x), int(self.player_y), PLAYER_RADIUS, player_col)

        # Particles
        for p in self.particles:
            pyxel.circ(int(p.x), int(p.y), 1, p.color)

        # Floating texts
        for ft in self.floating_texts:
            tx = int(ft.x - len(ft.text) * 2)
            ty = int(ft.y)
            pyxel.text(tx, ty, ft.text, ft.color)

        # HUD
        self._draw_hud()

    # ── HUD ────────────────────────────────────────────────────────────────

    def _draw_hud(self) -> None:
        # Score (top-left)
        pyxel.text(4, 2, f"SCORE:{self.score}", WHITE)

        # Timer (top-center)
        seconds = self.game_timer // 60
        timer_text = f"TIME:{seconds:02d}"
        pyxel.text(WIDTH // 2 - len(timer_text) * 2, 2, timer_text, WHITE)

        # Combo
        combo_text = f"COMBO:x{self.combo}"
        pyxel.text(WIDTH // 2 - len(combo_text) * 2, 12, combo_text, YELLOW)

        # Heat bar (top-right)
        bar_x = WIDTH - 64
        bar_y = 2
        bar_w = 60
        bar_h = 6
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        heat_fill = int(bar_w * self.heat / HEAT_MAX)
        if heat_fill > 0:
            heat_color = ORANGE if self.heat < 80 else RED
            pyxel.rect(bar_x, bar_y, heat_fill, bar_h, heat_color)
        pyxel.text(bar_x, bar_y + 8, "HEAT", GRAY)

        # Super timer indicator
        if self.super_timer > 0:
            super_sec = self.super_timer // 60
            super_text = f"SUPER:{super_sec}s"
            pyxel.text(WIDTH // 2 - len(super_text) * 2, 22, super_text, LIME)

    # ── Game Over Screen ───────────────────────────────────────────────────

    def _draw_game_over(self) -> None:
        msg = self.cause
        msg_w = len(msg) * 4
        pyxel.text(WIDTH // 2 - msg_w // 2, 60, msg, RED if "SNAP" in msg else ORANGE)

        score_text = f"FINAL SCORE: {self.score}"
        score_w = len(score_text) * 4
        pyxel.text(WIDTH // 2 - score_w // 2, 90, score_text, WHITE)

        combo_text = f"BEST COMBO: x{self.max_combo}"
        combo_w = len(combo_text) * 4
        pyxel.text(WIDTH // 2 - combo_w // 2, 106, combo_text, YELLOW)

        restart_text = "Press SPACE to retry"
        restart_w = len(restart_text) * 4
        pyxel.text(WIDTH // 2 - restart_w // 2, 150, restart_text, WHITE)


# ── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    Game()
