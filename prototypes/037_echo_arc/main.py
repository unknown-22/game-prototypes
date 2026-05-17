"""ECHO ARC — Color-match trajectory launcher.

Reinterpreted from game_idea_factory idea #1 (score 31.85):
  "log/replay as asset" → echo rings from past successful hits
  "one color per turn" → only one color active; match for COMBO

Core mechanic: Aim and launch colored projectiles with mouse slingshot.
Same-color consecutive hits build COMBO. Each hit leaves an ECHO RING
that amplifies subsequent shots passing through. COMBO≥4 → SUPER SHOT.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import IntEnum

import pyxel

# ── Config ──
SCREEN_W = 256
SCREEN_H = 256
DISPLAY_SCALE = 2

FPS = 60
GAME_DURATION = 60  # seconds
COLOR_COUNT = 4
COMBO_THRESHOLD = 4  # combo needed for SUPER SHOT
ECHO_MAX = 8
ECHO_RADIUS = 20
ECHO_GROW_RATE = 15  # pixels per second when triggered
ECHO_FADE_TIME = 3.0  # seconds before echo fades

TARGET_COUNT = 3
TARGET_RADIUS = 12
TARGET_SPAWN_INTERVAL = 2.0  # seconds between spawn checks
MAX_TARGETS = 6

LAUNCHER_X = SCREEN_W // 2
LAUNCHER_Y = SCREEN_H - 40
MAX_POWER = 180.0
MIN_POWER = 30.0
POWER_CHARGE_RATE = 200.0  # per second while holding

GRAVITY = 220.0  # pixels/sec^2
PROJECTILE_SPEED_FACTOR = 1.8
PROJECTILE_RADIUS = 4

# ── Colors (Pyxel palette hex) ──
COLORS: list[int] = [
    pyxel.COLOR_RED,     # 0: fire
    pyxel.COLOR_CYAN,    # 1: ice
    pyxel.COLOR_YELLOW,  # 2: lightning
    pyxel.COLOR_LIME,    # 3: nature
]
COLOR_NAMES: list[str] = ["FIRE", "ICE", "LIGHT", "NATR"]


class Phase(IntEnum):
    AIMING = 0
    FLYING = 1
    RESOLVING = 2
    GAME_OVER = 3


@dataclass
class Target:
    x: float
    y: float
    color: int
    radius: int = TARGET_RADIUS
    alive: bool = True
    spawn_time: float = 0.0


@dataclass
class EchoRing:
    x: float
    y: float
    color: int
    radius: float = 0.0
    life: float = ECHO_FADE_TIME
    max_radius: float = ECHO_RADIUS


@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    alive: bool = True


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: float
    size: float = 2.0


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: float = 1.0
    vy: float = -40.0


class Game:
    """ECHO ARC — Slingshot trajectory launcher."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="ECHO ARC", fps=FPS,
                    display_scale=DISPLAY_SCALE)
        self.reset()
        pyxel.run(self._update, self._draw)

    def reset(self) -> None:
        self.phase = Phase.AIMING
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.active_color: int = 0
        self.color_timer: float = 5.0  # auto-cycle every 5s
        self.game_timer: float = float(GAME_DURATION)

        # Launcher state
        self.aim_angle: float = -math.pi / 4  # 45° up-left initially
        self.power: float = 0.0
        self.dragging: bool = False
        self.drag_start_x: float = 0.0
        self.drag_start_y: float = 0.0

        # Entities
        self.projectiles: list[Projectile] = []
        self.targets: list[Target] = []
        self.echo_rings: list[EchoRing] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []

        # Seed RNG for deterministic tests
        self._rng = random.Random()

        # Timers
        self.spawn_timer: float = 0.0
        self.super_timer: float = 0.0  # remaining super mode time
        self.super_mode: bool = False

        # Spawn initial targets
        for _ in range(TARGET_COUNT):
            self._spawn_target()

    # ── Targeting ──

    def _spawn_target(self) -> None:
        if len(self.targets) >= MAX_TARGETS:
            return
        color = self._rng.randint(0, COLOR_COUNT - 1)
        margin = TARGET_RADIUS + 10
        x = float(self._rng.randint(margin, SCREEN_W - margin))
        y = float(self._rng.randint(30, SCREEN_H // 2))
        t = Target(x=x, y=y, color=color, spawn_time=self.game_timer)
        self.targets.append(t)

    def _cycle_active_color(self) -> None:
        self.active_color = (self.active_color + 1) % COLOR_COUNT
        self.color_timer = 5.0

    # ── Launch ──

    def _launch(self, angle: float, power: float) -> None:
        speed = power * PROJECTILE_SPEED_FACTOR
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        p = Projectile(
            x=float(LAUNCHER_X), y=float(LAUNCHER_Y),
            vx=vx, vy=vy, color=self.active_color,
        )
        self.projectiles.append(p)
        self.phase = Phase.FLYING
        self.power = 0.0
        self.dragging = False

    # ── Collision ──

    def _check_hit(self, proj: Projectile, target: Target) -> bool:
        dx = proj.x - target.x
        dy = proj.y - target.y
        dist = math.hypot(dx, dy)
        return dist < PROJECTILE_RADIUS + target.radius

    # ── Echo ──

    def _create_echo(self, x: float, y: float, color: int) -> None:
        if len(self.echo_rings) >= ECHO_MAX:
            # Remove oldest
            self.echo_rings.pop(0)
        self.echo_rings.append(EchoRing(x=x, y=y, color=color))

    def _check_echo_bonus(self, proj: Projectile) -> bool:
        for echo in self.echo_rings:
            if echo.radius <= 0:
                continue
            dx = proj.x - echo.x
            dy = proj.y - echo.y
            dist = math.hypot(dx, dy)
            if dist < echo.radius and proj.color == echo.color:
                echo.life = ECHO_FADE_TIME  # refresh
                echo.radius = min(echo.radius + ECHO_GROW_RATE * 0.1,
                                  ECHO_RADIUS * 2.0)
                return True
        return False

    # ── Particles ──

    def _spawn_particles(self, x: float, y: float, color: int, count: int = 8) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(20, 80)
            life = self._rng.uniform(0.3, 0.8)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                color=color, life=life,
            ))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(
            x=x, y=y, text=text, color=color,
        ))

    # ── Update ──

    def _update(self) -> None:
        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
            return

        self._update_timers()
        self._update_targets()
        self._update_input()
        self._update_projectiles()
        self._update_echoes()
        self._update_particles()
        self._update_floating_texts()

    def _update_timers(self) -> None:
        dt = 1.0 / FPS
        if self.phase != Phase.GAME_OVER:
            self.game_timer -= dt
            if self.game_timer <= 0:
                self.game_timer = 0
                self.phase = Phase.GAME_OVER
                return

        # Color auto-cycle
        if self.phase == Phase.AIMING:
            self.color_timer -= dt
            if self.color_timer <= 0:
                self._cycle_active_color()

        # Super mode timer
        if self.super_mode:
            self.super_timer -= dt
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0.0

    def _update_targets(self) -> None:
        # Remove dead targets
        self.targets = [t for t in self.targets if t.alive]

        # Spawn timer
        self.spawn_timer -= 1.0 / FPS
        if self.spawn_timer <= 0:
            self.spawn_timer = TARGET_SPAWN_INTERVAL
            if len(self.targets) < MAX_TARGETS:
                self._spawn_target()

    def _update_input(self) -> None:
        if self.phase != Phase.AIMING:
            return

        # Color switch on SPACE press
        if pyxel.btnp(pyxel.KEY_SPACE):
            self._cycle_active_color()

        # Mouse drag to aim
        mx = pyxel.mouse_x
        my = pyxel.mouse_y

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.dragging = True
            self.drag_start_x = float(mx)
            self.drag_start_y = float(my)
            self.power = 0.0

        if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT) and self.dragging:
            # Power increases while holding
            self.power = min(self.power + POWER_CHARGE_RATE / FPS, MAX_POWER)
            # Angle from launcher to mouse
            dx = mx - LAUNCHER_X
            dy = my - LAUNCHER_Y
            if abs(dx) > 1 or abs(dy) > 1:
                self.aim_angle = math.atan2(dy, dx)

        if pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT) and self.dragging:
            if self.power >= MIN_POWER:
                # Clamp angle: must go upward (-90 to -10 degrees in radians)
                clamped = max(-math.pi * 0.85, min(-math.pi * 0.15, self.aim_angle))
                self._launch(clamped, self.power)
            else:
                self.power = 0.0
                self.dragging = False

    def _update_projectiles(self) -> None:
        dt = 1.0 / FPS
        for proj in self.projectiles:
            if not proj.alive:
                continue
            proj.vy += GRAVITY * dt
            proj.x += proj.vx * dt
            proj.y += proj.vy * dt

            # Check echo ring bonus
            self._check_echo_bonus(proj)

            # Check target hits
            for target in self.targets:
                if not target.alive:
                    continue
                if self._check_hit(proj, target):
                    self._resolve_hit(proj, target)
                    proj.alive = False
                    break

            # Off-screen → auto-resolve as miss
            if proj.alive and (proj.y > SCREEN_H + 20 or proj.x < -20
                               or proj.x > SCREEN_W + 20):
                proj.alive = False
                self._resolve_miss()

        # Clean dead projectiles
        self.projectiles = [p for p in self.projectiles if p.alive]
        if not self.projectiles and self.phase == Phase.FLYING:
            self.phase = Phase.AIMING

    def _resolve_hit(self, proj: Projectile, target: Target) -> None:
        is_match = (proj.color == target.color) or self.super_mode
        if is_match:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            base = 10
            combo_mult = 1.0 + self.combo * 0.5
            dist_mult = 1.0 + (target.y / SCREEN_H) * 0.5
            points = int(base * combo_mult * dist_mult)
            self.score += points

            # Create echo ring
            self._create_echo(target.x, target.y, target.color)
            self._spawn_particles(target.x, target.y, target.color, 12)
            self._spawn_floating_text(
                target.x, target.y - 10,
                f"+{points}", COLORS[target.color],
            )

            # COMBO→SUPER
            if self.combo >= COMBO_THRESHOLD:
                self.super_mode = True
                self.super_timer = 3.0
                self._spawn_floating_text(
                    target.x, target.y - 20,
                    "SUPER!", pyxel.COLOR_WHITE,
                )
        else:
            # Wrong color — reset combo
            self.combo = 0
            self._spawn_particles(target.x, target.y, pyxel.COLOR_GRAY, 4)
            self._spawn_floating_text(
                target.x, target.y - 10,
                "MISS", pyxel.COLOR_GRAY,
            )

        target.alive = False

    def _resolve_miss(self) -> None:
        self.combo = 0
        # Small particle burst at edge
        last = self.projectiles[-1] if self.projectiles else None
        if last:
            self._spawn_particles(last.x, last.y, pyxel.COLOR_BROWN, 3)

    def _update_echoes(self) -> None:
        dt = 1.0 / FPS
        for echo in self.echo_rings:
            echo.life -= dt
            if echo.radius < ECHO_RADIUS:
                echo.radius += ECHO_RADIUS * 2.0 * dt
            if echo.radius > ECHO_RADIUS:
                echo.radius = ECHO_RADIUS
        self.echo_rings = [e for e in self.echo_rings if e.life > 0]

    def _update_particles(self) -> None:
        dt = 1.0 / FPS
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.life -= dt
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        dt = 1.0 / FPS
        for ft in self.floating_texts:
            ft.y += ft.vy * dt
            ft.life -= dt
        self.floating_texts = [ft for ft in self.floating_texts
                                if ft.life > 0]

    # ── Draw ──

    def _draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)
        self._draw_bg()
        self._draw_echos()
        self._draw_targets()
        self._draw_projectiles()
        self._draw_launcher()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_ui()

    def _draw_bg(self) -> None:
        # Ground line
        pyxel.line(0, LAUNCHER_Y + 15, SCREEN_W, LAUNCHER_Y + 15,
                    pyxel.COLOR_NAVY)
        # Simple stars/dots
        for i in range(20):
            sx = (i * 37 + 13) % SCREEN_W
            sy = (i * 19 + 7) % (SCREEN_H // 3)
            pyxel.pset(sx, sy, pyxel.COLOR_DARK_BLUE)

    def _draw_echos(self) -> None:
        for echo in self.echo_rings:
            color = echo.color
            # Draw ring
            r = int(echo.radius)
            if r > 1:
                pyxel.circb(int(echo.x), int(echo.y), r, color)
                if echo.life < 0.5:
                    pyxel.circb(int(echo.x), int(echo.y), r - 1, color)
            # Center dot
            pyxel.pset(int(echo.x), int(echo.y), color)

    def _draw_targets(self) -> None:
        for target in self.targets:
            if not target.alive:
                continue
            color = COLORS[target.color]
            # Outer ring
            pyxel.circb(int(target.x), int(target.y),
                         target.radius, color)
            # Inner filled
            pyxel.circ(int(target.x), int(target.y),
                        target.radius - 3, color)
            # Highlight if matches active color
            if target.color == self.active_color or self.super_mode:
                pyxel.circb(int(target.x), int(target.y),
                             target.radius + 2, pyxel.COLOR_WHITE)

    def _draw_projectiles(self) -> None:
        for proj in self.projectiles:
            if not proj.alive:
                continue
            color = COLORS[proj.color]
            # Trail
            for i in range(3):
                tx = proj.x - proj.vx * i * 0.02
                ty = proj.y - proj.vy * i * 0.02
                pyxel.circ(int(tx), int(ty), PROJECTILE_RADIUS - i, color)
            # Main projectile
            pyxel.circ(int(proj.x), int(proj.y), PROJECTILE_RADIUS, color)
            # Glow if super
            if self.super_mode:
                pyxel.circb(int(proj.x), int(proj.y),
                             PROJECTILE_RADIUS + 3, pyxel.COLOR_WHITE)

    def _draw_launcher(self) -> None:
        # Draw launcher base
        pyxel.rect(LAUNCHER_X - 8, LAUNCHER_Y - 2,
                    LAUNCHER_X + 8, LAUNCHER_Y + 6, pyxel.COLOR_GRAY)
        pyxel.rect(LAUNCHER_X - 6, LAUNCHER_Y,
                    LAUNCHER_X + 6, LAUNCHER_Y + 4, pyxel.COLOR_LIGHT_BLUE)

        # Draw aiming line when dragging
        if self.dragging and self.phase == Phase.AIMING:
            # Power bar behind
            r = int(LAUNCHER_X - self.power * 0.1 - 2)
            pyxel.rect(r, LAUNCHER_Y + 12,
                        LAUNCHER_X + int(self.power * 0.1) + 2, LAUNCHER_Y + 16,
                        pyxel.COLOR_NAVY)
            power_width = int(self.power * 0.2)
            if power_width > 0:
                pyxel.rect(LAUNCHER_X - power_width, LAUNCHER_Y + 12,
                            LAUNCHER_X + power_width, LAUNCHER_Y + 16,
                            COLORS[self.active_color])

            # Aim line
            line_len = min(self.power * 0.8, 80)
            end_x = LAUNCHER_X + math.cos(self.aim_angle) * line_len
            end_y = LAUNCHER_Y + math.sin(self.aim_angle) * line_len
            pyxel.line(LAUNCHER_X, LAUNCHER_Y, int(end_x), int(end_y),
                       COLORS[self.active_color])
            # Dot at end
            pyxel.circ(int(end_x), int(end_y), 3, COLORS[self.active_color])

        # Color indicator on launcher
        pyxel.circ(LAUNCHER_X, LAUNCHER_Y - 8, 5, COLORS[self.active_color])
        if self.super_mode:
            # Rainbow glow
            pyxel.circb(LAUNCHER_X, LAUNCHER_Y - 8, 8, pyxel.COLOR_WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            s = int(p.size * p.life)
            if s > 0:
                pyxel.circ(int(p.x), int(p.y), s, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = int(ft.life * 15)
            color = ft.color if alpha > 5 else pyxel.COLOR_GRAY
            pyxel.text(int(ft.x) - len(ft.text) * 2,
                        int(ft.y), ft.text, color)

    def _draw_ui(self) -> None:
        # Score
        pyxel.text(4, 2, f"SCORE:{self.score}", pyxel.COLOR_WHITE)
        # Combo
        if self.combo > 0:
            combo_text = f"COMBO x{self.combo}"
            pyxel.text(SCREEN_W - len(combo_text) * 4 - 2, 2,
                        combo_text, COLORS[self.active_color])
        # Max combo
        pyxel.text(4, 10, f"MAX:{self.max_combo}", pyxel.COLOR_GRAY)
        # Active color
        pyxel.text(4, 18,
                    f"COLOR:{COLOR_NAMES[self.active_color]}",
                    COLORS[self.active_color])
        # Timer
        t = max(0, int(self.game_timer))
        timer_text = f"TIME:{t:02d}"
        c = pyxel.COLOR_RED if t <= 10 else pyxel.COLOR_WHITE
        pyxel.text(SCREEN_W // 2 - len(timer_text) * 2, 2, timer_text, c)

        # Super mode indicator
        if self.super_mode:
            st = int(self.super_timer * 10) / 10
            super_text = f"SUPER {st:.1f}s"
            pyxel.text(SCREEN_W // 2 - len(super_text) * 2, 12,
                        super_text, pyxel.COLOR_YELLOW)

        # Game over screen
        if self.phase == Phase.GAME_OVER:
            pyxel.rect(SCREEN_W // 2 - 70, SCREEN_H // 2 - 30,
                        SCREEN_W // 2 + 70, SCREEN_H // 2 + 30,
                        pyxel.COLOR_BLACK)
            pyxel.rectb(SCREEN_W // 2 - 70, SCREEN_H // 2 - 30,
                         SCREEN_W // 2 + 70, SCREEN_H // 2 + 30,
                         pyxel.COLOR_WHITE)
            pyxel.text(SCREEN_W // 2 - 20, SCREEN_H // 2 - 20,
                        "GAME OVER", pyxel.COLOR_RED)
            score_text = f"SCORE: {self.score}"
            pyxel.text(SCREEN_W // 2 - len(score_text) * 2,
                        SCREEN_H // 2 - 5, score_text, pyxel.COLOR_WHITE)
            combo_text = f"MAX COMBO: {self.max_combo}"
            pyxel.text(SCREEN_W // 2 - len(combo_text) * 2,
                        SCREEN_H // 2 + 5, combo_text, pyxel.COLOR_YELLOW)
            pyxel.text(SCREEN_W // 2 - 25, SCREEN_H // 2 + 18,
                        "PRESS [R] TO RETRY", pyxel.COLOR_GRAY)

        # Instructions
        if self.phase == Phase.AIMING and not self.dragging:
            pyxel.text(4, SCREEN_H - 24,
                        "CLICK+DRAG: AIM & POWER",
                        pyxel.COLOR_GRAY)
            pyxel.text(4, SCREEN_H - 16,
                        "SPACE: SWITCH COLOR",
                        pyxel.COLOR_GRAY)
            if self.super_mode:
                pyxel.text(4, SCREEN_H - 8,
                            "SUPER: RAINBOW HITS!",
                            pyxel.COLOR_YELLOW)


if __name__ == "__main__":
    Game()
