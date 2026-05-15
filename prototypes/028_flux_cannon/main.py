"""
FLUX CANNON — artillery chain-combo prototype (028_flux_cannon)

Reinterpreted from deckbuilder idea #1 (score 32.05):
  "Synthesis compression" + "cost is future hand, not HP"
  → Color-match chain COMBO → SUPER SHOT (AOE burst)
  → FOCUS: using high power costs accuracy for future shots

Controls:
  Mouse: aim cannon angle
  Scroll wheel: adjust power
  Left click: fire
  R: restart after game over

Dev status:
  ✅ Core artillery aiming + firing
  ✅ Color-match combo system
  ✅ SUPER shot at combo >= 3 (AOE burst)
  ✅ Focus accuracy mechanic (wobble when low)
  ✅ Heat overheat mechanic with cooldown
  ✅ 60-second timed run
  ✅ Floating score popups
  ✅ Particle effects + screen shake
  ✅ Target drift for dynamic aiming
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ────────────────────────────────────────────────────────────────
W, H = 400, 300
FPS = 60
GAME_TIME = 60.0

N_COLORS = 5
COLOR_LIST: list[int] = [
    pyxel.COLOR_RED,
    pyxel.COLOR_DARK_BLUE,
    pyxel.COLOR_GREEN,
    pyxel.COLOR_YELLOW,
    pyxel.COLOR_PURPLE,
]
COLOR_SHORT: list[str] = ["R", "B", "G", "Y", "P"]

# Cannon
CANNON_X = 50.0
CANNON_Y = float(H - 30)
CANNON_LEN = 22.0
POWER_MIN = 40
POWER_MAX = 130
GRAVITY = 200.0

# Targets
TARGET_RADIUS: float = 11.0
TARGET_COUNT: int = 6
TARGET_Y_MIN: float = 40.0
TARGET_Y_MAX: float = 200.0
TARGET_DRIFT_SPEED: float = 15.0

# Combo
SUPER_COMBO_THRESHOLD: int = 3
SUPER_AOE_RADIUS: float = 90.0

# Focus
FOCUS_MAX: float = 100.0
FOCUS_DRAIN_BASE: float = 10.0
FOCUS_REGEN: float = 10.0
FOCUS_HIT_BONUS: float = 15.0
FOCUS_LOW_THRESHOLD: float = 25.0

# Heat
HEAT_MAX: float = 100.0
HEAT_PER_SHOT: float = 14.0
HEAT_COOLDOWN_FRAMES: int = 75

# Scoring
BASE_SCORE: int = 100
COMBO_MULT_STEP: float = 0.5
SUPER_MULT: float = 2.0


class Color(Enum):
    RED = 0
    BLUE = 1
    GREEN = 2
    YELLOW = 3
    PURPLE = 4


class Phase(Enum):
    AIMING = auto()
    FLYING = auto()
    GAME_OVER = auto()


@dataclass
class Target:
    x: float
    y: float
    color: Color
    drift_vx: float = 0.0
    alive: bool = True


@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    color: Color
    is_super: bool = False
    alive: bool = True


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


class Game:
    """Main game class — single-file Pyxel artillery prototype."""

    def __init__(self) -> None:
        pyxel.init(W, H, title="FLUX CANNON", fps=FPS, display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.AIMING
        self.score: int = 0
        self.combo: int = 0
        self.combo_color: Color | None = None
        self.is_super_next: bool = False
        self.power: int = 80
        self.aim_angle: float = -math.pi / 4
        self.focus: float = FOCUS_MAX
        self.heat: float = 0.0
        self.heat_cooldown: int = 0
        self.time_remaining: float = GAME_TIME
        self.shots_fired: int = 0
        self.hits_landed: int = 0
        self.targets: list[Target] = []
        self.projectile: Projectile | None = None
        self.particles: list[Particle] = []
        self.float_texts: list[FloatingText] = []
        self.screen_shake: int = 0
        self._spawn_initial_targets()

    # ── Spawning ────────────────────────────────────────────────────────

    def _spawn_initial_targets(self) -> None:
        for _ in range(TARGET_COUNT):
            t = self._make_target()
            self.targets.append(t)

    def _make_target(self) -> Target:
        color = random.choice(list(Color))
        for _attempt in range(100):
            x = random.uniform(TARGET_RADIUS + 40, W - TARGET_RADIUS - 10)
            y = random.uniform(TARGET_Y_MIN, TARGET_Y_MAX)
            if not self._overlaps_existing(x, y):
                drift = random.uniform(-TARGET_DRIFT_SPEED, TARGET_DRIFT_SPEED)
                return Target(x=x, y=y, color=color, drift_vx=drift)
        return Target(
            x=random.uniform(60, W - 20),
            y=random.uniform(TARGET_Y_MIN, TARGET_Y_MAX),
            color=color,
            drift_vx=0.0,
        )

    def _replace_dead_targets(self) -> None:
        for i, t in enumerate(self.targets):
            if not t.alive:
                self.targets[i] = self._make_target()

    def _overlaps_existing(self, x: float, y: float) -> bool:
        min_dist = TARGET_RADIUS * 3.0
        for t in self.targets:
            if not t.alive:
                continue
            dx = t.x - x
            dy = t.y - y
            if dx * dx + dy * dy < min_dist * min_dist:
                return True
        return False

    # ── Update ──────────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
            return

        dt = 1.0 / FPS

        self.time_remaining -= dt
        if self.time_remaining <= 0.0:
            self.time_remaining = 0.0
            self.phase = Phase.GAME_OVER
            return

        self.focus = min(FOCUS_MAX, self.focus + FOCUS_REGEN * dt)

        if self.heat_cooldown > 0:
            self.heat_cooldown -= 1
            if self.heat_cooldown <= 0:
                self.heat = 0.0

        if self.screen_shake > 0:
            self.screen_shake -= 1

        self._update_target_drift(dt)
        self._update_particles(dt)
        self._update_float_texts(dt)

        if self.phase == Phase.AIMING:
            self._update_aiming()
        elif self.phase == Phase.FLYING:
            self._update_flying(dt)

    def _update_target_drift(self, dt: float) -> None:
        for t in self.targets:
            if not t.alive:
                continue
            t.x += t.drift_vx * dt
            if t.x < TARGET_RADIUS + 5:
                t.x = TARGET_RADIUS + 5
                t.drift_vx = abs(t.drift_vx)
            elif t.x > W - TARGET_RADIUS - 5:
                t.x = W - TARGET_RADIUS - 5
                t.drift_vx = -abs(t.drift_vx)

    def _update_aiming(self) -> None:
        dx = pyxel.mouse_x - CANNON_X
        dy = pyxel.mouse_y - CANNON_Y
        if dx == 0 and dy == 0:
            dx = 1
        self.aim_angle = math.atan2(-dy, dx)
        if self.aim_angle > 0.0:
            self.aim_angle = 0.0
        if self.aim_angle < -math.pi * 0.85:
            self.aim_angle = -math.pi * 0.85

        mw = pyxel.mouse_wheel
        if mw != 0:
            self.power = max(POWER_MIN, min(POWER_MAX, self.power + mw * 6))

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and self.heat_cooldown == 0:
            self._fire()

    def _fire(self) -> None:
        if self.combo_color is not None:
            color = self.combo_color
        else:
            color = random.choice(list(Color))

        if self.focus < FOCUS_LOW_THRESHOLD:
            wobble = (1.0 - self.focus / FOCUS_LOW_THRESHOLD) * 0.15
            angle = self.aim_angle + random.uniform(-wobble, wobble)
        else:
            angle = self.aim_angle

        vx = math.cos(angle) * self.power
        vy = math.sin(angle) * self.power

        self.projectile = Projectile(
            x=CANNON_X, y=CANNON_Y,
            vx=vx, vy=vy,
            color=color,
            is_super=self.is_super_next,
        )

        power_ratio = (self.power - POWER_MIN) / (POWER_MAX - POWER_MIN)
        focus_drain = FOCUS_DRAIN_BASE + power_ratio * 15.0
        self.focus = max(0.0, self.focus - focus_drain)

        self.heat += HEAT_PER_SHOT
        if self.heat >= HEAT_MAX:
            self.heat = HEAT_MAX
            self.heat_cooldown = HEAT_COOLDOWN_FRAMES
            self.combo = 0
            self.combo_color = None
            self.is_super_next = False

        self.shots_fired += 1
        self.is_super_next = False
        self.phase = Phase.FLYING

    def _update_flying(self, dt: float) -> None:
        if self.projectile is None:
            self._on_miss()
            return

        p = self.projectile
        p.x += p.vx * dt
        p.y += p.vy * dt
        p.vy += GRAVITY * dt

        if p.y > H + 30 or p.y < -30 or p.x < -30 or p.x > W + 30:
            self._on_miss()
            return

        for t in self.targets:
            if not t.alive:
                continue
            dx = p.x - t.x
            dy = p.y - t.y
            if dx * dx + dy * dy < (TARGET_RADIUS + 6) * (TARGET_RADIUS + 6):
                self._on_hit(t)
                return

    def _on_hit(self, target: Target) -> None:
        target.alive = False

        if self.combo_color == target.color:
            self.combo += 1
        else:
            self.combo = 1
            self.combo_color = target.color

        combo_mult = 1.0 + (self.combo - 1) * COMBO_MULT_STEP
        super_mult = SUPER_MULT if (self.projectile and self.projectile.is_super) else 1.0
        points = int(BASE_SCORE * combo_mult * super_mult)
        self.score += points

        self.focus = min(FOCUS_MAX, self.focus + FOCUS_HIT_BONUS)

        if self.combo >= SUPER_COMBO_THRESHOLD:
            self.is_super_next = True

        col = COLOR_LIST[target.color.value]
        self._spawn_hit_particles(target.x, target.y, col, 14)
        text_col = pyxel.COLOR_ORANGE if (self.projectile and self.projectile.is_super) else pyxel.COLOR_WHITE
        self._spawn_float_text(target.x, target.y - 10, str(points), text_col)

        if self.projectile and self.projectile.is_super:
            self._super_aoe(target)
            self.screen_shake = 8

        self.hits_landed += 1
        self._replace_dead_targets()
        self.projectile = None
        self.phase = Phase.AIMING

    def _super_aoe(self, origin: Target) -> None:
        for t in self.targets:
            if not t.alive:
                continue
            if t.color != origin.color:
                continue
            dx = t.x - origin.x
            dy = t.y - origin.y
            if dx * dx + dy * dy < SUPER_AOE_RADIUS * SUPER_AOE_RADIUS:
                t.alive = False
                col = COLOR_LIST[t.color.value]
                self._spawn_hit_particles(t.x, t.y, col, 8)
                combo_mult2 = 1.0 + self.combo * COMBO_MULT_STEP
                bonus = int(BASE_SCORE * combo_mult2 * SUPER_MULT)
                self.score += bonus
                self._spawn_float_text(t.x, t.y - 10, str(bonus), pyxel.COLOR_ORANGE)
                self.hits_landed += 1

    def _on_miss(self) -> None:
        self.combo = 0
        self.combo_color = None
        self.is_super_next = False
        self.projectile = None
        self.phase = Phase.AIMING

    # ── Particles & Effects ─────────────────────────────────────────────

    def _spawn_hit_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(20, 90)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=random.randint(10, 30),
                color=color,
            ))

    def _spawn_float_text(self, x: float, y: float, text: str, color: int) -> None:
        self.float_texts.append(FloatingText(
            x=x, y=y, text=text, life=40, color=color,
        ))

    def _update_particles(self, dt: float) -> None:
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += GRAVITY * 0.3 * dt
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_float_texts(self, dt: float) -> None:
        for ft in self.float_texts:
            ft.y -= 1.0
            ft.life -= 1
        self.float_texts = [ft for ft in self.float_texts if ft.life > 0]

    # ── Draw ────────────────────────────────────────────────────────────

    def draw(self) -> None:
        shake_x = 0
        shake_y = 0
        if self.screen_shake > 0:
            shake_x = random.randint(-3, 3)
            shake_y = random.randint(-3, 3)
            pyxel.camera(shake_x, shake_y)

        pyxel.cls(pyxel.COLOR_BLACK)

        for gx in range(0, W, 30):
            for gy in range(0, H, 30):
                if (gx // 30 + gy // 30) % 2 == 0:
                    pyxel.pset(gx, gy, pyxel.COLOR_NAVY)

        pyxel.line(0, H - 18, W, H - 18, pyxel.COLOR_GRAY)

        self._draw_targets()
        self._draw_cannon()
        self._draw_projectile()
        self._draw_trajectory()
        self._draw_particles()
        self._draw_float_texts()
        self._draw_ui()

        pyxel.camera(0, 0)

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_targets(self) -> None:
        for t in self.targets:
            if not t.alive:
                continue
            color = COLOR_LIST[t.color.value]
            pyxel.circb(t.x, t.y, TARGET_RADIUS, color)
            pyxel.circ(t.x, t.y, TARGET_RADIUS - 3, color)
            pyxel.circ(t.x, t.y, 2, pyxel.COLOR_WHITE)

    def _draw_cannon(self) -> None:
        if self.phase == Phase.GAME_OVER:
            return
        ex = CANNON_X + math.cos(self.aim_angle) * CANNON_LEN
        ey = CANNON_Y + math.sin(self.aim_angle) * CANNON_LEN
        pyxel.line(CANNON_X, CANNON_Y, ex, ey, pyxel.COLOR_WHITE)
        pyxel.line(CANNON_X - 1, CANNON_Y + 1, ex - 1, ey + 1, pyxel.COLOR_GRAY)
        pyxel.line(CANNON_X + 1, CANNON_Y - 1, ex + 1, ey - 1, pyxel.COLOR_GRAY)
        pyxel.rect(CANNON_X - 10, CANNON_Y - 4, 20, 12, pyxel.COLOR_BROWN)

    def _draw_projectile(self) -> None:
        if self.projectile is None:
            return
        p = self.projectile
        col = COLOR_LIST[p.color.value]
        if p.is_super:
            r = 5.0 + abs(math.sin(pyxel.frame_count * 0.25)) * 3.0
            pyxel.circ(p.x, p.y, r, col)
            pyxel.circ(p.x, p.y, r - 2, pyxel.COLOR_WHITE)
        else:
            pyxel.circ(p.x, p.y, 4, col)
            pyxel.circ(p.x, p.y, 2, pyxel.COLOR_WHITE)

    def _draw_trajectory(self) -> None:
        if self.phase != Phase.AIMING:
            return
        px: float = CANNON_X
        py: float = CANNON_Y
        vx = math.cos(self.aim_angle) * self.power
        vy = math.sin(self.aim_angle) * self.power
        dt = 0.04
        for i in range(80):
            px += vx * dt
            py += vy * dt
            vy += GRAVITY * dt
            if py > H or px < 0 or px > W:
                break
            if i % 2 == 0:
                dot_col = pyxel.COLOR_GRAY if self.focus >= FOCUS_LOW_THRESHOLD else pyxel.COLOR_BROWN
                pyxel.pset(px, py, dot_col)

    def _draw_particles(self) -> None:
        for p in self.particles:
            if p.life > 0 and p.life % 2 == 0:
                pyxel.pset(p.x, p.y, p.color)

    def _draw_float_texts(self) -> None:
        for ft in self.float_texts:
            alpha = ft.life / 40.0
            if alpha > 0.3:
                pyxel.text(ft.x - len(ft.text) * 2, ft.y, ft.text, ft.color)

    def _draw_ui(self) -> None:
        pyxel.rect(0, 0, W, 30, pyxel.COLOR_BLACK)

        pyxel.text(5, 4, f"SCORE {self.score:06d}", pyxel.COLOR_WHITE)
        t_left = max(0, int(self.time_remaining))
        tc = pyxel.COLOR_WHITE if t_left > 10 else pyxel.COLOR_RED
        pyxel.text(5, 13, f"TIME  {t_left:02d}s", tc)

        if self.combo > 1:
            pyxel.text(5, 22, f"COMBO x{self.combo}", pyxel.COLOR_YELLOW)

        if self.is_super_next:
            pyxel.text(W - 75, 4, ">> SUPER <<", pyxel.COLOR_ORANGE)

        bar_x = W - 65
        bar_w = 58
        bar_h = 5

        fy = H - 22
        pyxel.rect(bar_x - 1, fy - 1, bar_w + 2, bar_h + 2, pyxel.COLOR_GRAY)
        fw = int(bar_w * self.focus / FOCUS_MAX)
        fc = pyxel.COLOR_GREEN if self.focus >= FOCUS_LOW_THRESHOLD else pyxel.COLOR_RED
        pyxel.rect(bar_x, fy, fw, bar_h, fc)
        pyxel.text(bar_x, fy - 8, "FOCUS", pyxel.COLOR_GRAY)

        hy = H - 13
        pyxel.rect(bar_x - 1, hy - 1, bar_w + 2, bar_h + 2, pyxel.COLOR_GRAY)
        hw = int(bar_w * self.heat / HEAT_MAX)
        hc = pyxel.COLOR_ORANGE if self.heat < HEAT_MAX else pyxel.COLOR_RED
        pyxel.rect(bar_x, hy, hw, bar_h, hc)
        pyxel.text(bar_x, hy - 8, "HEAT", pyxel.COLOR_GRAY)
        if self.heat_cooldown > 0:
            pyxel.text(bar_x + 5, hy, "COOL...", pyxel.COLOR_RED)

        pyxel.text(CANNON_X + 18, CANNON_Y - 15, f"PWR:{self.power:03d}", pyxel.COLOR_WHITE)

        # Color legend in bottom-left
        for i in range(N_COLORS):
            lx = 5 + i * 22
            ly = H - 30
            pyxel.rect(lx, ly, 16, 10, COLOR_LIST[i])
            pyxel.text(lx + 5, ly + 2, COLOR_SHORT[i], pyxel.COLOR_BLACK if i != 3 else pyxel.COLOR_BLACK)

    def _draw_game_over(self) -> None:
        pyxel.rect(W // 2 - 65, H // 2 - 35, 130, 80, pyxel.COLOR_BLACK)
        pyxel.rectb(W // 2 - 65, H // 2 - 35, 130, 80, pyxel.COLOR_WHITE)
        pyxel.text(W // 2 - 28, H // 2 - 25, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(W // 2 - 40, H // 2 - 6, f"SCORE: {self.score}", pyxel.COLOR_WHITE)
        hits_pct = int(self.hits_landed / max(1, self.shots_fired) * 100)
        pyxel.text(W // 2 - 46, H // 2 + 6, f"HITS: {hits_pct}%", pyxel.COLOR_GRAY)
        pyxel.text(W // 2 - 50, H // 2 + 22, "PRESS R TO RETRY", pyxel.COLOR_YELLOW)


if __name__ == "__main__":
    Game()
