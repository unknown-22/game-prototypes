"""162_hammer_surge — Hammer throw color-match COMBO chain prototype."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

import pyxel


# ── Phase Enum ──


class Phase(Enum):
    TITLE = auto()
    POWERING = auto()
    FLYING = auto()
    RESULT = auto()
    GAME_OVER = auto()


# ── Data Classes ──


@dataclass
class ThrowRecord:
    angle: float
    power: float
    color: int
    matched: bool
    landing_y: float = 0.0


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
    vy: float = -1.0


# ── Constants ──

SCREEN_W = 320
SCREEN_H = 240
THROWER_X = 160
THROWER_Y = 120
ZONE_X = 240
ZONE_W = 60
ZONE_H = 50
ZONE_Y = [20, 70, 120, 170]
MAX_THROWS = 15
MAX_HEAT = 100.0
HEAT_PER_MISS = 15.0
HEAT_DECAY = 0.02
COMBO_SUPER_THRESHOLD = 4
SUPER_DURATION = 300  # 5 seconds at 60fps
RESULT_DURATION = 60  # 1 second
SHAKE_FRAMES = 10
POWER_BUILD_RATE = 0.02
SPIN_SPEED_BASE = 0.05
SPIN_SPEED_POWERED = 0.15
HAMMER_SPEED_MIN = 5.0
HAMMER_SPEED_MAX = 9.0
HAMMER_RADIUS = 6
THROWER_RADIUS = 10
GHOST_TRAIL_COUNT = 3

# Pyxel palette
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

ZONE_COLORS = [RED, GREEN, DARK_BLUE, YELLOW]
COLOR_NAMES = ["RED", "GREEN", "BLUE", "YELLOW"]
GHOST_TRAIL_COLORS = [ORANGE, LIME, LIGHT_BLUE, PEACH]
RAINBOW_COLORS = [RED, ORANGE, YELLOW, GREEN, LIME, CYAN, PINK]
POWER_BAR_COLORS = [GREEN, YELLOW, RED]


# ── Game Logic (testable — no pyxel input calls) ──


@dataclass
class Game:
    """Core game logic. All attributes pre-initialized for headless testing."""

    phase: Phase = Phase.TITLE
    score: int = 0
    combo: int = 0
    max_combo: int = 0
    heat: float = 0.0
    throw_count: int = MAX_THROWS
    max_throws: int = MAX_THROWS
    super_mode: bool = False
    super_timer: int = 0
    spin_angle: float = 0.0
    spin_power: float = 0.0
    hammer_active: bool = False
    hammer_x: float = float(THROWER_X)
    hammer_y: float = float(THROWER_Y)
    hammer_vx: float = 0.0
    hammer_vy: float = 0.0
    hammer_color: int = 0
    current_zone_index: int = -1
    ghost_trails: list[ThrowRecord] = field(default_factory=list)
    particles: list[Particle] = field(default_factory=list)
    floating_texts: list[FloatingText] = field(default_factory=list)
    shake_frames: int = 0
    shake_x: int = 0
    shake_y: int = 0
    frame: int = 0
    result_timer: int = 0
    title_blink: int = 0
    go_blink: int = 0
    rng: random.Random = field(default_factory=random.Random)

    # ── Reset ──

    def reset(self) -> None:
        """Reset all state for a new game."""
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.throw_count = MAX_THROWS
        self.super_mode = False
        self.super_timer = 0
        self.spin_angle = 0.0
        self.spin_power = 0.0
        self.hammer_active = False
        self.hammer_x = float(THROWER_X)
        self.hammer_y = float(THROWER_Y)
        self.hammer_vx = 0.0
        self.hammer_vy = 0.0
        self.hammer_color = 0
        self.current_zone_index = -1
        self.ghost_trails.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.shake_frames = 0
        self.shake_x = 0
        self.shake_y = 0
        self.frame = 0
        self.result_timer = 0
        self.title_blink = 0
        self.go_blink = 0

    def start_game(self) -> None:
        """Start game from TITLE or restart from GAME_OVER."""
        self.reset()
        self.phase = Phase.POWERING

    # ── Power Building ──

    def _build_power(self) -> float:
        """Increment spin_power while SPACE held. Returns current power."""
        self.spin_power = min(1.0, self.spin_power + POWER_BUILD_RATE)
        return self.spin_power

    def _reset_power(self) -> None:
        """Reset power to 0 after throw."""
        self.spin_power = 0.0

    # ── Throw Mechanics ──

    def _throw_hammer(self, angle: float, power: float) -> None:
        """Launch hammer from thrower position at given angle and power."""
        clamped = max(0.0, min(1.0, power))
        speed = HAMMER_SPEED_MIN + clamped * (HAMMER_SPEED_MAX - HAMMER_SPEED_MIN)
        self.hammer_vx = math.cos(angle) * speed
        self.hammer_vy = math.sin(angle) * speed
        self.hammer_x = float(THROWER_X)
        self.hammer_y = float(THROWER_Y)
        self.hammer_active = True
        self._reset_power()

    def _update_hammer(self) -> bool:
        """Move hammer by vx/vy. Returns True if still flying."""
        if not self.hammer_active:
            return False
        self.hammer_x += self.hammer_vx
        self.hammer_y += self.hammer_vy
        if self.hammer_x >= ZONE_X:
            return False
        return True

    # ── Landing Check ──

    def _check_landing(self, hx: float, hy: float) -> tuple[int, bool]:
        """Return (zone_index, matched) for landing position."""
        zi = self._compute_zone_index(hy)
        self.current_zone_index = zi
        # In super mode, auto-match regardless of zone
        if self.super_mode:
            return zi, True
        matched = zi == self.hammer_color
        return zi, matched

    def _compute_zone_index(self, y: float) -> int:
        """Map y coordinate to zone index 0-3."""
        for i, zy in enumerate(ZONE_Y):
            if zy <= y < zy + ZONE_H:
                return i
        if y < ZONE_Y[0]:
            return 0
        if y >= ZONE_Y[3] + ZONE_H:
            return 3
        return 3  # fallback

    def _compute_landing_y(self, angle: float) -> float:
        """Compute the y position where hammer path intersects ZONE_X."""
        dx = ZONE_X - THROWER_X
        return THROWER_Y + dx * math.tan(angle)

    # ── Result Application ──

    def _apply_result(self, matched: bool) -> None:
        """Apply match/miss results: score, combo, heat, super check."""
        if matched:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            mult = self._get_score_multiplier()
            base = 100
            gained = int(base * mult)
            self.score += gained
            self._spawn_particles(self.hammer_x, self.hammer_y, ZONE_COLORS[self.hammer_color], 12)
            self._spawn_floating_text(
                float(THROWER_X), float(THROWER_Y - 20),
                f"+{gained} COMBO x{self.combo}", YELLOW, 40
            )
            self._check_super_activation()
        else:
            self.combo = 0
            if self.super_mode:
                self.super_mode = False
                self.super_timer = 0
            self.heat = min(self.heat + HEAT_PER_MISS, MAX_HEAT)
            self._spawn_particles(self.hammer_x, self.hammer_y, GRAY, 8)
            self._spawn_floating_text(
                self.hammer_x, self.hammer_y - 10,
                "MISS! +15 HEAT", ORANGE, 35
            )
        # Advance hammer color for next throw
        self.hammer_color = (self.hammer_color + 1) % 4

    # ── Heat ──

    def _update_heat(self) -> bool:
        """Check heat game over, then decay. Return True if game over."""
        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER
            return True
        self.heat = max(0.0, self.heat - HEAT_DECAY)
        return False

    # ── Super Mode ──

    def _check_super_activation(self) -> None:
        """Activate super mode if combo threshold reached."""
        if self.combo >= COMBO_SUPER_THRESHOLD and not self.super_mode:
            self.super_mode = True
            self.super_timer = SUPER_DURATION
            self.shake_frames = SHAKE_FRAMES
            self._spawn_super_particles()
            self._spawn_floating_text(
                float(SCREEN_W // 2), float(SCREEN_H // 2),
                "SUPER THROW!", YELLOW, 60
            )

    def _update_super(self) -> None:
        """Decrement super timer each frame."""
        if self.super_mode:
            self.super_timer = max(0, self.super_timer - 1)
            if self.super_timer <= 0:
                self.super_mode = False

    # ── Score ──

    def _get_score_multiplier(self) -> float:
        """Return current score multiplier."""
        if self.super_mode:
            return 3.0
        return 1.0 + self.combo * 0.25

    def _compute_score(self, base: int, matched: bool) -> int:
        """Compute score for a throw."""
        if not matched:
            return 0
        return int(base * self._get_score_multiplier())

    # ── Phase Flow ──

    def _advance_from_result(self) -> None:
        """Transition from RESULT phase to next phase."""
        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER
            return
        self.throw_count -= 1
        if self.throw_count <= 0:
            self.phase = Phase.GAME_OVER
            return
        self.phase = Phase.POWERING

    # ── Particles ──

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        """Spawn particle burst at position."""
        for _ in range(count):
            angle = self.rng.uniform(0, 2 * math.pi)
            speed = self.rng.uniform(1.0, 3.0)
            self.particles.append(
                Particle(
                    x=x + self.rng.uniform(-4, 4),
                    y=y + self.rng.uniform(-4, 4),
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed - 1.0,
                    life=self.rng.randint(15, 35),
                    color=color,
                )
            )

    def _spawn_super_particles(self) -> None:
        """Spawn rainbow particle burst for super mode activation."""
        for _ in range(30):
            angle = self.rng.uniform(0, 2 * math.pi)
            speed = self.rng.uniform(2.0, 5.0)
            self.particles.append(
                Particle(
                    x=float(THROWER_X) + self.rng.uniform(-20, 20),
                    y=float(THROWER_Y) + self.rng.uniform(-20, 20),
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed - 1.0,
                    life=self.rng.randint(20, 45),
                    color=self.rng.choice(RAINBOW_COLORS),
                )
            )

    def _update_particles(self) -> None:
        """Update all particles: move, apply gravity, remove dead."""
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1  # gravity
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    # ── Floating Texts ──

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int, life: int) -> None:
        """Spawn floating text."""
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=life, color=color)
        )

    def _update_floating_texts(self) -> None:
        """Update floating texts: move upward, remove expired."""
        alive: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= 0.8
            ft.life -= 1
            if ft.life > 0:
                alive.append(ft)
        self.floating_texts = alive

    # ── Ghost Trails ──

    def _record_throw(self, angle: float, power: float, matched: bool) -> None:
        """Record a throw result for ghost trail display."""
        landing_y = self._compute_landing_y(angle)
        self.ghost_trails.append(
            ThrowRecord(
                angle=angle,
                power=power,
                color=self.hammer_color,
                matched=matched,
                landing_y=landing_y,
            )
        )
        while len(self.ghost_trails) > GHOST_TRAIL_COUNT:
            self.ghost_trails.pop(0)

    # ── Per-Frame Update ──

    def update(self) -> None:
        """Per-frame update. Called by App."""
        self.frame += 1
        self.title_blink = (self.title_blink + 1) % 60
        self.go_blink = (self.go_blink + 1) % 60

        if self.shake_frames > 0:
            self.shake_frames -= 1
            self.shake_x = self.rng.randint(-4, 4)
            self.shake_y = self.rng.randint(-4, 4)
        else:
            self.shake_x = 0
            self.shake_y = 0

        self._update_super()
        self._update_particles()
        self._update_floating_texts()

        if self.phase == Phase.POWERING:
            self._update_heat()

        elif self.phase == Phase.RESULT:
            self.result_timer -= 1
            self._update_heat()
            if self.result_timer <= 0:
                self._advance_from_result()

    # ── Drawing Methods ──

    def draw(self) -> None:
        """Draw current game state."""
        pyxel.camera()
        pyxel.cls(BLACK)

        self._draw_landing_zones()
        self._draw_ghost_trails()
        self._draw_thrower()
        self._draw_hammer()
        self._draw_power_bar()
        self._draw_hud()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_super_indicator()

        if self.phase == Phase.TITLE:
            self._draw_title_overlay()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over_overlay()

    def _draw_landing_zones(self) -> None:
        """Draw 4 colored landing zones on the right side."""
        for i, zy in enumerate(ZONE_Y):
            x = ZONE_X + self.shake_x
            y = zy + self.shake_y
            pyxel.rect(x, y, ZONE_W, ZONE_H, ZONE_COLORS[i])
            pyxel.rectb(x, y, ZONE_W, ZONE_H, WHITE)
            # Zone label
            label = COLOR_NAMES[i]
            tx = x + (ZONE_W - len(label) * 4) // 2
            pyxel.text(tx, y + ZONE_H // 2 - 4, label, WHITE)

    def _draw_ghost_trails(self) -> None:
        """Draw ghost echo trails of previous throws."""
        for rec in self.ghost_trails:
            gcolor = GHOST_TRAIL_COLORS[rec.color]
            end_x = ZONE_X + self.shake_x
            end_y = int(rec.landing_y) + self.shake_y
            pyxel.line(
                THROWER_X + self.shake_x,
                THROWER_Y + self.shake_y,
                end_x, end_y,
                gcolor,
            )

    def _draw_thrower(self) -> None:
        """Draw thrower circle and aiming arm at center."""
        cx = THROWER_X + self.shake_x
        cy = THROWER_Y + self.shake_y
        # Body circle
        pyxel.circ(cx, cy, THROWER_RADIUS, WHITE)
        # Super mode rainbow border
        if self.super_mode:
            sc = RAINBOW_COLORS[(self.frame // 4) % len(RAINBOW_COLORS)]
            pyxel.circb(cx, cy, THROWER_RADIUS + 2, sc)
            pyxel.circb(cx, cy, THROWER_RADIUS + 3, sc)
        # Spin indicator (small dot on circumference)
        sx = cx + int(THROWER_RADIUS * math.cos(self.spin_angle))
        sy = cy + int(THROWER_RADIUS * math.sin(self.spin_angle))
        pyxel.circ(sx, sy, 2, GREEN)
        # Aiming arm line
        arm_len = 20
        ax = cx + int(arm_len * math.cos(self.spin_angle))
        ay = cy + int(arm_len * math.sin(self.spin_angle))
        pyxel.line(cx, cy, ax, ay, WHITE)

    def _draw_hammer(self) -> None:
        """Draw the hammer if active or at thrower."""
        if self.hammer_active:
            hx = int(self.hammer_x) + self.shake_x
            hy = int(self.hammer_y) + self.shake_y
        else:
            hx = THROWER_X + self.shake_x + int(20 * math.cos(self.spin_angle))
            hy = THROWER_Y + self.shake_y + int(20 * math.sin(self.spin_angle))

        hammer_clr = ZONE_COLORS[self.hammer_color]
        if self.super_mode:
            hammer_clr = RAINBOW_COLORS[(self.frame // 4) % len(RAINBOW_COLORS)]
        pyxel.circ(hx, hy, HAMMER_RADIUS, hammer_clr)
        pyxel.circb(hx, hy, HAMMER_RADIUS, WHITE)

    def _draw_power_bar(self) -> None:
        """Draw power bar at bottom-left."""
        bar_x = 8
        bar_y = SCREEN_H - 16
        bar_w = 100
        bar_h = 8
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        if self.spin_power > 0:
            fw = int(bar_w * self.spin_power)
            if self.spin_power < 0.5:
                pc = GREEN
            elif self.spin_power < 0.8:
                pc = YELLOW
            else:
                pc = RED
            pyxel.rect(bar_x, bar_y, fw, bar_h, pc)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        pyxel.text(bar_x + bar_w + 4, bar_y - 1, "PWR", WHITE)

    def _draw_hud(self) -> None:
        """Draw score, combo, throws, heat bar."""
        # Score (top-left)
        pyxel.text(4, 2, f"SCORE: {self.score}", WHITE)
        # Combo (top-center)
        combo_text = f"COMBO: x{self.combo}"
        combo_color = YELLOW if self.combo >= 3 else WHITE
        pyxel.text(SCREEN_W // 2 - len(combo_text) * 2, 2, combo_text, combo_color)
        # Throws remaining (below score)
        thr_color = WHITE
        if self.throw_count <= 3:
            thr_color = RED if (pyxel.frame_count % 20) < 10 else WHITE
        pyxel.text(4, 12, f"THROWS: {self.throw_count}", thr_color)
        # Heat bar (top-right)
        hbar_x = SCREEN_W - 88
        hbar_y = 2
        hbar_w = 80
        hbar_h = 6
        pyxel.rect(hbar_x, hbar_y, hbar_w, hbar_h, GRAY)
        hw = int(hbar_w * self.heat / MAX_HEAT)
        heat_clr = GREEN
        if self.heat >= 80:
            heat_clr = RED if (pyxel.frame_count % 15) < 8 else ORANGE
        elif self.heat >= 50:
            heat_clr = ORANGE
        elif self.heat >= 30:
            heat_clr = YELLOW
        pyxel.rect(hbar_x, hbar_y, hw, hbar_h, heat_clr)
        pyxel.rectb(hbar_x, hbar_y, hbar_w, hbar_h, WHITE)
        pyxel.text(hbar_x - 2, hbar_y + 6, f"HEAT {int(self.heat)}", WHITE)

    def _draw_super_indicator(self) -> None:
        """Draw SUPER MODE indicator bar if active."""
        if self.super_mode:
            sr = self.super_timer / SUPER_DURATION
            bar_x = 4
            bar_y = SCREEN_H - 28
            bar_w = 310
            bar_h = 6
            pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
            sdw = int(bar_w * sr)
            sc = RAINBOW_COLORS[(self.frame // 4) % len(RAINBOW_COLORS)]
            pyxel.rect(bar_x, bar_y, sdw, bar_h, sc)
            pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
            pyxel.text(bar_x + 2, bar_y - 8, "SUPER THROW!", sc)

    def _draw_particles(self) -> None:
        """Draw all particles."""
        for p in self.particles:
            if p.life < 4 and p.life % 2 == 0:
                continue  # blink out
            px = int(p.x) + self.shake_x
            py = int(p.y) + self.shake_y
            pyxel.pset(px, py, p.color)

    def _draw_floating_texts(self) -> None:
        """Draw all floating texts."""
        for ft in self.floating_texts:
            tx = int(ft.x) - len(ft.text) * 2
            ty = int(ft.y) + self.shake_y
            pyxel.text(tx, ty, ft.text, ft.color)

    def _draw_title_overlay(self) -> None:
        """Draw title screen overlay."""
        pyxel.rect(25, 20, 270, 200, BLACK)
        pyxel.rectb(25, 20, 270, 200, WHITE)
        pyxel.text(90, 32, "HAMMER SURGE", YELLOW)
        pyxel.text(100, 46, "Color-Match COMBO Throw", LIGHT_BLUE)
        pyxel.text(52, 68, "LEFT/RIGHT: Aim hammer angle", GRAY)
        pyxel.text(62, 82, "HOLD SPACE: Build throw power", GRAY)
        pyxel.text(62, 96, "RELEASE SPACE: Throw hammer", GRAY)
        pyxel.text(70, 114, "Land in matching color zone", GRAY)
        pyxel.text(70, 126, "to build COMBO chain!", GRAY)
        pyxel.text(70, 142, "COMBO 4+ = SUPER THROW!", YELLOW)
        pyxel.text(70, 158, "Wrong color = +15 HEAT", ORANGE)
        pyxel.text(70, 174, "HEAT 100 = FOUL (Game Over)", RED)
        pyxel.text(82, 190, "15 throws to max your score!", GREEN)
        if self.title_blink < 30:
            pyxel.text(80, 210, "Press SPACE to start", WHITE)

    def _draw_game_over_overlay(self) -> None:
        """Draw game over overlay."""
        pyxel.rect(35, 35, 250, 170, BLACK)
        pyxel.rectb(35, 35, 250, 170, WHITE)

        if self.heat >= MAX_HEAT:
            title = "FOUL! HEAT OVERLOAD"
            title_clr = RED
        elif self.throw_count <= 0:
            title = "ALL THROWS USED!"
            title_clr = GRAY
        else:
            title = "GAME OVER"
            title_clr = YELLOW
        pyxel.text(SCREEN_W // 2 - len(title) * 2, 44, title, title_clr)

        pyxel.text(55, 70, f"SCORE:         {self.score}", WHITE)
        pyxel.text(55, 86, f"MAX COMBO:     x{self.max_combo}", YELLOW)
        pyxel.text(55, 102, f"SUPER ACTIVE:  {'YES' if self.max_combo >= 4 else 'NO'}", GRAY)
        pyxel.text(55, 118, f"THROWS USED:   {MAX_THROWS - self.throw_count}", GRAY)
        pyxel.text(55, 134, f"HEAT:          {int(self.heat)}", GRAY)
        if self.go_blink < 30:
            pyxel.text(65, 190, "Press SPACE to retry", WHITE)


# ── Pyxel App Layer (input handling only) ──


class App:
    """Pyxel application wrapper. Handles input, delegates logic to Game."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="HAMMER SURGE", display_scale=2)
        pyxel.mouse(True)
        font_path = Path(__file__).with_name("k8x12.bdf")
        try:
            pyxel.load(str(font_path))
        except Exception:
            pass
        self.game = Game()
        self.game.reset()
        self._space_held = False
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        g = self.game

        if g.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                g.start_game()
            g.update()
            return

        if g.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                g.start_game()
            g.update()
            return

        if g.phase == Phase.POWERING:
            # Adjust aim angle
            if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_UP):
                g.spin_angle -= 0.05
            if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_DOWN):
                g.spin_angle += 0.05

            # Build power
            if pyxel.btn(pyxel.KEY_SPACE):
                g._build_power()
                self._space_held = True
            elif self._space_held:
                # Released SPACE → throw
                self._space_held = False
                if g.spin_power > 0:
                    g._throw_hammer(g.spin_angle, g.spin_power)
                    g.phase = Phase.FLYING

        elif g.phase == Phase.FLYING:
            still_flying = g._update_hammer()
            if not still_flying:
                zi, matched = g._check_landing(g.hammer_x, g.hammer_y)
                g._record_throw(g.spin_angle, g.spin_power, matched)
                g._apply_result(matched)
                g.hammer_active = False
                g.hammer_x = float(THROWER_X)
                g.hammer_y = float(THROWER_Y)
                g.result_timer = RESULT_DURATION
                g.phase = Phase.RESULT

        g.update()

    def draw(self) -> None:
        self.game.draw()


def main() -> None:
    App()


if __name__ == "__main__":
    main()
