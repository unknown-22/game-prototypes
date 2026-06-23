"""153_row_surge - ROW SURGE

Side-scrolling rowing game with color-match stroke COMBO system.
Same-color consecutive strokes build COMBO. COMBO >= 4 triggers SUPER STROKE
(rainbow glow, 3x score, 1.5x speed, 5s). Wake trail amplifies stroke power (ECHO).
Water hazards spread via CA and drift toward the boat. 60-second time limit.
HEAT >= 100 = GAME OVER.

面白い瞬間: 同じ色のストロークをリズムよく連続で決め、COMBOが4に達して
SUPER STROKEが発動、虹色に輝きながら川を一気に駆け抜け、ウェイクトレイルが
増幅して高スコアが爆発する瞬間
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import pyxel

# ── Constants ────────────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
DISPLAY_SCALE = 2
FPS = 60

WATER_Y = 40
WATER_H = 160
BOAT_Y = 120

COLORS = 4
COLOR_MAP: list[int] = [8, 3, 6, 10]  # RED, GREEN, LIGHT_BLUE, YELLOW
COLOR_NAMES: list[str] = ["RED", "GRN", "BLU", "YEL"]

COMBO_THRESHOLD = 4
SUPER_DURATION = 300  # frames (5s at 60fps)
MAX_HEAT = 100.0
HEAT_DECAY = 0.3
HEAT_PER_WRONG = 8
HEAT_PER_HAZARD = 10
STROKE_COOLDOWN = 15
COMBO_WINDOW = 60  # frames (1s)
COLOR_CYCLE_FRAMES = 20
GAME_TIME = 3600  # frames (60s)

BASE_SPEED = 1.0
SUPER_SPEED_MULT = 1.5
STROKE_BURST = 3.0
BURST_DECAY = 0.1

BASE_SCORE = 10
COMBO_BONUS_PER_LEVEL = 5
SUPER_SCORE_MULT = 3
ECHO_BONUS_MULT = 0.5

HAZARD_MAX = 15
HAZARD_SPAWN_GAP_MIN = 80
HAZARD_SPAWN_GAP_MAX = 160
HAZARD_DRIFT = 0.5
CA_SPREAD_INTERVAL = 60
CA_SPREAD_CHANCE = 0.15
CA_SPREAD_RADIUS = 30

WAKE_PARTICLES_PER_STROKE_MIN = 3
WAKE_PARTICLES_PER_STROKE_MAX = 5
WAKE_LIFE = 180
WAKE_DRIFT = 1.1  # slightly faster than base speed to drift forward
ECHO_THRESHOLD = 14

PARTICLE_LIFE_MIN = 10
PARTICLE_LIFE_MAX = 20
PARTICLE_GRAVITY = 0.05

SCREEN_BOAT_X = 60

# ── Color Constants ──────────────────────────────────────────────────────────
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

FONT_PATH = Path(__file__).with_name("k8x12.bdf")


# ── Enums ────────────────────────────────────────────────────────────────────


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class Stroke:
    color: int  # 0=RED, 1=GREEN, 2=BLUE, 3=YELLOW
    x: float  # world space position


@dataclass
class WakeParticle:
    x: float
    y: float
    color: int
    life: float  # 0-1 fades out


@dataclass
class Hazard:
    x: float
    y: float
    color: int
    radius: float


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int  # frames remaining


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


# ── Game Class ───────────────────────────────────────────────────────────────


class Game:
    def __init__(self) -> None:
        pyxel.init(
            SCREEN_W, SCREEN_H,
            title="ROW SURGE",
            display_scale=DISPLAY_SCALE,
            fps=FPS,
        )
        pyxel.mouse(False)
        self._font: pyxel.Font | None = None
        if FONT_PATH.exists():
            self._font = pyxel.Font(str(FONT_PATH))
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── State initialization ─────────────────────────────────────────────

    def reset(self) -> None:
        self._rng = random.Random()
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.high_score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.boat_x: float = 0.0
        self.boat_y: float = float(BOAT_Y)
        self.stroke_color: int = 0  # current stroke color index 0-3
        self.prev_stroke_color: int = -1
        self.stroke_cooldown: int = 0
        self.stroke_timer: int = 0  # frames since last stroke
        self.super_timer: int = 0
        self.super_mode: bool = False
        self.camera_x: float = 0.0
        self.distance: float = 0.0
        self.game_timer: int = GAME_TIME
        self.speed_burst: float = 0.0
        self.echo_active: bool = False
        self.color_cycle_timer: int = 0
        self.ca_spread_timer: int = 0
        self.strokes: list[Stroke] = []
        self.wake_particles: list[WakeParticle] = []
        self.hazards: list[Hazard] = []
        self.floating_texts: list[FloatingText] = []
        self.particles: list[Particle] = []
        self.frame: int = 0
        self.shake_frames: int = 0
        self.shake_intensity: int = 0
        self.path: list[tuple[float, float]] = []

    def _start_game(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.boat_x = 0.0
        self.boat_y = float(BOAT_Y)
        self.stroke_color = 0
        self.prev_stroke_color = -1
        self.stroke_cooldown = 0
        self.stroke_timer = 0
        self.super_timer = 0
        self.super_mode = False
        self.camera_x = 0.0
        self.distance = 0.0
        self.game_timer = GAME_TIME
        self.speed_burst = 0.0
        self.echo_active = False
        self.color_cycle_timer = 0
        self.ca_spread_timer = 0
        self.strokes.clear()
        self.wake_particles.clear()
        self.hazards.clear()
        self.floating_texts.clear()
        self.particles.clear()
        self.frame = 0
        self.shake_frames = 0
        self.shake_intensity = 0
        self.path.clear()
        # Spawn initial hazards
        for _ in range(4):
            self._spawn_hazard(initial=True)
        self.phase = Phase.PLAYING

    # ── Pure Logic (Testable) ────────────────────────────────────────────

    @staticmethod
    def _compute_stroke_score(combo: int, is_super: bool, echo: bool) -> int:
        base = BASE_SCORE + combo * COMBO_BONUS_PER_LEVEL
        mult = 1.0
        if is_super:
            mult *= SUPER_SCORE_MULT
        if echo:
            mult *= (1.0 + ECHO_BONUS_MULT)
        return int(base * mult)

    def _handle_stroke(self) -> None:
        """Called when SPACE is pressed to row."""
        if self.stroke_cooldown > 0:
            return
        if self.super_mode:
            # SUPER STROKE: always counts as match
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            points = self._compute_stroke_score(self.combo, True, self.echo_active)
            self._add_score(points)
            self._add_floating_text(self.boat_x, self.boat_y - 15, f"+{points}", self._rainbow_color())
            self._spawn_stroke_particles(self.boat_x, self.boat_y, self._rainbow_color(), 12)
            self._spawn_wake(self.boat_x, self.boat_y, self.stroke_color)
            self._apply_stroke_effects()
            self.echo_active = False
            return

        # Normal stroke
        if self.stroke_color == self.prev_stroke_color and self.stroke_timer <= COMBO_WINDOW and self.prev_stroke_color >= 0:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            points = self._compute_stroke_score(self.combo, False, self.echo_active)
            self._add_score(points)
            txt = f"+{points}"
            if self.combo >= 3:
                txt = f"x{self.combo} +{points}"
            self._add_floating_text(self.boat_x, self.boat_y - 15, txt, COLOR_MAP[self.stroke_color])
            self._spawn_stroke_particles(self.boat_x, self.boat_y, COLOR_MAP[self.stroke_color], 8)
            # Check SUPER
            if self.combo >= COMBO_THRESHOLD and not self.super_mode:
                self._activate_super()
        else:
            if self.prev_stroke_color >= 0:
                self.combo = 0
                self.heat += HEAT_PER_WRONG
                self._add_floating_text(self.boat_x, self.boat_y - 15, "+10 WRONG", GRAY)
                self._spawn_stroke_particles(self.boat_x, self.boat_y, GRAY, 5)
                self.shake_frames = 8
                self.shake_intensity = 3
            else:
                # First stroke, no wrong penalty
                self.combo = 1
                if self.combo > self.max_combo:
                    self.max_combo = self.combo
                points = self._compute_stroke_score(self.combo, False, False)
                self._add_score(points)
                self._add_floating_text(self.boat_x, self.boat_y - 15, f"+{points}", COLOR_MAP[self.stroke_color])

        self.prev_stroke_color = self.stroke_color
        self._spawn_wake(self.boat_x, self.boat_y, self.stroke_color)
        self._apply_stroke_effects()
        self.echo_active = False

    def _apply_stroke_effects(self) -> None:
        """Apply cooldown, burst, and record stroke."""
        self.stroke_cooldown = STROKE_COOLDOWN
        self.stroke_timer = 0
        self.speed_burst = STROKE_BURST
        self.strokes.append(Stroke(color=self.stroke_color, x=self.boat_x))
        # Keep last 20 strokes
        if len(self.strokes) > 20:
            self.strokes.pop(0)

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self._add_floating_text(self.boat_x, self.boat_y - 30, "SUPER STROKE!", YELLOW)
        self._spawn_super_particles(self.boat_x, self.boat_y)
        self.shake_frames = 15
        self.shake_intensity = 5

    def _update_boat(self) -> None:
        """Update boat position and speed."""
        if self.speed_burst > 0:
            self.speed_burst = max(0.0, self.speed_burst - BURST_DECAY)
        multiplier = SUPER_SPEED_MULT if self.super_mode else 1.0
        speed = BASE_SPEED * multiplier + self.speed_burst
        self.boat_x += speed
        self.distance += speed
        self.camera_x = self.boat_x - SCREEN_BOAT_X

    def _update_wake(self) -> None:
        """Update wake particles lifecycle and check echo."""
        for wp in self.wake_particles[:]:
            wp.x += WAKE_DRIFT
            wp.life -= 1.0 / WAKE_LIFE
            if wp.life <= 0:
                self.wake_particles.remove(wp)

    def _check_wake_echo(self) -> None:
        """Check if boat overlaps same-color wake particle for ECHO."""
        if self.echo_active:
            return
        for wp in self.wake_particles:
            if wp.color != self.stroke_color:
                continue
            dx = abs(self.boat_x - wp.x)
            dy = abs(self.boat_y - wp.y)
            if dx < ECHO_THRESHOLD and dy < 10:
                self.echo_active = True
                self._add_floating_text(self.boat_x, self.boat_y - 8, "ECHO!", CYAN)
                wp.life = 0.05  # flash and fade fast
                break

    def _update_hazards(self) -> None:
        """Move hazards, remove off-screen ones, spawn new ones."""
        # Move hazards
        for h in self.hazards[:]:
            h.x -= HAZARD_DRIFT
            if h.x < self.camera_x - 40:
                self.hazards.remove(h)

        # Spawn new hazards
        right_edge = self.camera_x + SCREEN_W + 100
        if self.hazards:
            last_hazard_x = max(h.x for h in self.hazards)
        else:
            last_hazard_x = self.camera_x + SCREEN_W * 0.5

        while last_hazard_x < right_edge and len(self.hazards) < HAZARD_MAX:
            self._spawn_hazard(initial=False)
            if self.hazards:
                last_hazard_x = max(h.x for h in self.hazards)
            else:
                last_hazard_x += HAZARD_SPAWN_GAP_MIN

        # CA spread
        self.ca_spread_timer += 1
        if self.ca_spread_timer >= CA_SPREAD_INTERVAL:
            self.ca_spread_timer = 0
            self._ca_spread()

    def _spawn_hazard(self, initial: bool = False) -> None:
        """Spawn a new hazard at right edge."""
        if len(self.hazards) >= HAZARD_MAX:
            return
        color = self._rng.randrange(COLORS)
        if initial:
            x = self.camera_x + SCREEN_W + self._rng.uniform(20, SCREEN_W * 2)
        else:
            if self.hazards:
                rightmost = max(h.x for h in self.hazards)
            else:
                rightmost = self.camera_x + SCREEN_W
            x = rightmost + self._rng.uniform(HAZARD_SPAWN_GAP_MIN, HAZARD_SPAWN_GAP_MAX)
        y = self._rng.uniform(WATER_Y + 30, WATER_Y + WATER_H - 30)
        radius = self._rng.uniform(8.0, 16.0)
        self.hazards.append(Hazard(x=x, y=y, color=color, radius=radius))

    def _ca_spread(self) -> None:
        """CA spread: each hazard has chance to spawn adjacent same-color hazard."""
        new_hazards: list[Hazard] = []
        for h in self.hazards:
            if self._rng.random() < CA_SPREAD_CHANCE:
                dist = self._rng.uniform(10, CA_SPREAD_RADIUS)
                nx = h.x + dist
                ny = h.y + (self._rng.uniform(-1, 1) * dist)
                ny = max(WATER_Y + 10, min(WATER_Y + WATER_H - 10, ny))
                if len(self.hazards) + len(new_hazards) < HAZARD_MAX:
                    new_hazards.append(Hazard(x=nx, y=ny, color=h.color, radius=h.radius * 0.8))
        self.hazards.extend(new_hazards)

    def _check_hazard_collision(self) -> None:
        """Check boat collision with hazards."""
        boat_radius = 8.0
        for h in self.hazards[:]:
            dx = self.boat_x - h.x
            dy = self.boat_y - h.y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < h.radius + boat_radius:
                self.heat += HEAT_PER_HAZARD
                self.combo = 0
                self._spawn_hit_particles(h.x, h.y)
                self._add_floating_text(self.boat_x, self.boat_y - 15, "+10 HEAT!", ORANGE)
                self.shake_frames = 10
                self.shake_intensity = 4
                self.hazards.remove(h)
                break  # one collision per frame

    def _update_heat(self) -> None:
        """Decay heat over time."""
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_super(self) -> None:
        """Update SUPER STROKE timer."""
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer == 0:
                self.super_mode = False
                self._add_floating_text(self.boat_x, self.boat_y - 18, "END", GRAY)

    def _add_score(self, points: int) -> None:
        self.score += points

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, color=color, life=30)
        )

    def _spawn_wake(self, x: float, y: float, color: int) -> None:
        count = self._rng.randint(WAKE_PARTICLES_PER_STROKE_MIN, WAKE_PARTICLES_PER_STROKE_MAX)
        for _ in range(count):
            wx = x + self._rng.uniform(-8, 8)
            wy = y + self._rng.uniform(-6, 6)
            self.wake_particles.append(WakeParticle(x=wx, y=wy, color=color, life=1.0))

    def _spawn_stroke_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-2.0, 0.5),
                    vy=self._rng.uniform(-3.0, 3.0),
                    life=self._rng.randint(PARTICLE_LIFE_MIN, PARTICLE_LIFE_MAX),
                    color=color,
                )
            )

    def _spawn_super_particles(self, x: float, y: float) -> None:
        for _ in range(30):
            color = COLOR_MAP[self._rng.randrange(COLORS)]
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-5.0, 2.0),
                    vy=self._rng.uniform(-5.0, 5.0),
                    life=self._rng.randint(15, 30),
                    color=color,
                )
            )

    def _spawn_hit_particles(self, x: float, y: float) -> None:
        for _ in range(10):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-2.0, 2.0),
                    vy=self._rng.uniform(-2.0, 2.0),
                    life=self._rng.randint(10, 20),
                    color=ORANGE,
                )
            )

    def _rainbow_color(self) -> int:
        cycle = (self.frame // 6) % COLORS
        return COLOR_MAP[cycle]

    # ── Update ───────────────────────────────────────────────────────────

    def update(self) -> None:
        self.frame += 1

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self._start_game()
            return

        if self.phase == Phase.GAME_OVER:
            self._update_particles()
            self._update_floating_texts()
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.phase = Phase.TITLE
                self.reset()
            return

        # PLAYING ──────────────────────────────────────────────────────────
        self.game_timer -= 1

        # Color cycle
        self.color_cycle_timer += 1
        if self.color_cycle_timer >= COLOR_CYCLE_FRAMES:
            self.color_cycle_timer = 0
            self.stroke_color = (self.stroke_color + 1) % COLORS

        # Cooldown countdown
        if self.stroke_cooldown > 0:
            self.stroke_cooldown -= 1

        # Stroke timer
        self.stroke_timer += 1

        # Input
        if pyxel.btnp(pyxel.KEY_SPACE):
            self._handle_stroke()

        # Check wake echo before boat moves
        self._check_wake_echo()

        # Update game systems
        self._update_boat()
        self._update_wake()
        self._update_hazards()
        self._check_hazard_collision()

        # Check game over BEFORE heat decay
        if self.heat >= MAX_HEAT or self.game_timer <= 0:
            self._on_game_over()
            return

        self._update_heat()
        self._update_super()
        self._update_particles()
        self._update_floating_texts()

        if self.shake_frames > 0:
            self.shake_frames -= 1

        self.path.append((self.boat_x, self.boat_y))
        if len(self.path) > 120:
            self.path.pop(0)

    def _on_game_over(self) -> None:
        if self.score > self.high_score:
            self.high_score = self.score
        self.phase = Phase.GAME_OVER
        # Death particles
        for _ in range(25):
            color = RED if self.heat >= MAX_HEAT else GRAY
            self.particles.append(
                Particle(
                    x=self.boat_x,
                    y=self.boat_y,
                    vx=self._rng.uniform(-4.0, 4.0),
                    vy=self._rng.uniform(-5.0, 1.0),
                    life=self._rng.randint(15, 30),
                    color=color,
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += PARTICLE_GRAVITY
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    def _world_to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        return (wx - self.camera_x, wy)

    # ── Draw ─────────────────────────────────────────────────────────────

    def draw(self) -> None:
        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0:
            shake_x = self._rng.randint(-self.shake_intensity, self.shake_intensity)
            shake_y = self._rng.randint(-self.shake_intensity, self.shake_intensity)

        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        if self.phase == Phase.GAME_OVER:
            self._draw_playing(shake_x, shake_y)
            self._draw_game_over_overlay()
            return

        self._draw_playing(shake_x, shake_y)

    def _draw_playing(self, shake_x: int, shake_y: int) -> None:
        # Set camera for scrolling
        try:
            pyxel.camera(0, 0)
        except BaseException:
            pass

        # Sky
        pyxel.rect(0, 0, SCREEN_W, WATER_Y, NAVY)

        # Water background
        self._draw_water(shake_x, shake_y)

        # Wake particles
        self._draw_wake(shake_x, shake_y)

        # Hazards
        self._draw_hazards(shake_x, shake_y)

        # Boat
        self._draw_boat(shake_x, shake_y)

        # Particles
        self._draw_particles(shake_x, shake_y)

        # Floating texts
        self._draw_floating_texts(shake_x, shake_y)

        # HUD
        self._draw_hud()

        # Reset camera
        try:
            pyxel.camera(0, 0)
        except BaseException:
            pass

    def _draw_title(self) -> None:
        self._draw_static_water_bg()

        title = "ROW SURGE"
        self._text_center(title, 35, CYAN)

        lines = [
            "SPACE : Stroke (row the boat)",
            "Wait to cycle stroke color",
            "",
            "Same color = COMBO UP!",
            "Wrong color = COMBO RESET + HEAT",
            "COMBO x4 = SUPER STROKE!",
            "  (Rainbow, 3x score, 5 sec)",
            "Cross your wake = ECHO +50%",
            "Avoid hazards or take HEAT",
            "HEAT >= 100 = GAME OVER",
            "Survive 60 seconds!",
            "",
            "SPACE or ENTER to Start",
        ]

        y_off = 55
        for line in lines:
            self._text_center(line, y_off, GRAY if line else WHITE)
            y_off += 9 if line else 5

        # Color legend
        y_off += 2
        labels = ["RED", "GRN", "BLU", "YEL"]
        for i in range(COLORS):
            bx = SCREEN_W // 2 - 50 + i * 26
            by = y_off
            pyxel.rect(bx, by, 18, 8, COLOR_MAP[i])
            pyxel.rectb(bx, by, 18, 8, WHITE)
            self._text(labels[i], bx + 9 - len(labels[i]) * 4 // 2, by + 10, WHITE)

        if self.high_score > 0:
            self._text_center(f"HIGH SCORE: {self.high_score}", SCREEN_H - 20, ORANGE)

    def _draw_game_over_overlay(self) -> None:
        # Semi-transparent overlay
        for y in range(0, SCREEN_H, 4):
            for x in range((y // 4) % 2, SCREEN_W, 4):
                pyxel.pset(x, y, BLACK)

        go_text = "GAME OVER"
        self._text_center(go_text, 40, RED)

        reason = "HEAT OVERLOAD!" if self.heat >= MAX_HEAT else "TIME OUT!"
        self._text_center(reason, 58, ORANGE)

        lines = [
            f"SCORE: {self.score}",
            f"HIGH SCORE: {self.high_score}",
            f"MAX COMBO: x{self.max_combo}",
            f"DISTANCE: {int(self.distance)}",
            f"HEAT: {int(self.heat)}",
            "",
            "SPACE or ENTER to Retry",
        ]
        y_off = 80
        for line in lines:
            if "HIGH" in line:
                col = YELLOW
            elif "COMBO" in line:
                col = CYAN
            elif "HEAT" in line and self.heat >= MAX_HEAT:
                col = RED
            else:
                col = WHITE
            self._text_center(line, y_off, col)
            y_off += 14

        if self.score >= self.high_score and self.score > 0:
            self._text_center("NEW BEST!", y_off + 4, ORANGE)

        # Blinking retry
        if self.frame % 60 < 40:
            self._text_center("PRESS SPACE TO RETRY", SCREEN_H - 24, WHITE)

    # ── Drawing Helpers ──────────────────────────────────────────────────

    def _draw_static_water_bg(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, WATER_Y, NAVY)
        self._draw_water(0, 0)

    def _draw_water(self, shake_x: int, shake_y: int) -> None:
        """
        Draw wavy horizontal water lines.
        Offset by camera for parallax effect (simplified: slight wave offset).
        """
        for row in range(WATER_Y, WATER_Y + WATER_H, 12):
            y = row + shake_y
            if y < WATER_Y - 12 or y > WATER_Y + WATER_H:
                continue
            col = CYAN if (row // 12) % 2 == 0 else NAVY
            # Draw wavy line using short segments
            for x in range(0, SCREEN_W, 4):
                wave_offset = int(1.5 * ((x + self.frame + row * 3) % 60) / 60)
                pyxel.pset(x + shake_x, y + wave_offset, col)
                pyxel.pset(x + shake_x, y + wave_offset - 1, col)

    def _draw_wake(self, shake_x: int, shake_y: int) -> None:
        for wp in self.wake_particles:
            sx, sy = self._world_to_screen(wp.x, wp.y)
            sx += shake_x
            sy += shake_y
            if sx < -4 or sx > SCREEN_W + 4 or sy < WATER_Y or sy > WATER_Y + WATER_H:
                continue
            alpha = wp.life
            radius = max(1, int(3 * alpha))
            col = COLOR_MAP[wp.color]
            if wp.life < 0.1:
                col = WHITE
            elif alpha < 0.3:
                col = GRAY
            pyxel.circ(int(sx), int(sy), radius, col)

    def _draw_hazards(self, shake_x: int, shake_y: int) -> None:
        for h in self.hazards:
            sx, sy = self._world_to_screen(h.x, h.y)
            sx += shake_x
            sy += shake_y
            if sx < -20 or sx > SCREEN_W + 20:
                continue
            # Dark outline
            pyxel.circb(int(sx), int(sy), int(h.radius), BLACK)
            pyxel.circb(int(sx), int(sy), int(h.radius) + 1, BLACK)
            # Fill
            col = COLOR_MAP[h.color]
            pyxel.circ(int(sx), int(sy), int(h.radius) - 1, col)
            # Inner detail
            pyxel.circ(int(sx), int(sy), 2, BLACK)

    def _draw_boat(self, shake_x: int, shake_y: int) -> None:
        # Boat is rendered at fixed screen position
        sx = SCREEN_BOAT_X + shake_x
        sy = int(self.boat_y) + shake_y

        color = self._rainbow_color() if self.super_mode else COLOR_MAP[self.stroke_color]

        # Boat hull (triangle)
        if self.super_mode and self.frame % 4 < 2:
            color = WHITE

        # Main hull
        pyxel.tri(sx - 10, sy + 6, sx + 10, sy + 6, sx, sy - 6, color)
        # Bow (forward point)
        pyxel.tri(sx + 6, sy + 2, sx + 14, sy, sx + 6, sy - 2, color)

        # Outline
        pyxel.trib(sx - 10, sy + 6, sx + 10, sy + 6, sx, sy - 6, WHITE)

        # SUPER STROKE glow
        if self.super_mode:
            glow_color = self._rainbow_color()
            pyxel.circb(sx, sy, 16, glow_color)
            if self.frame % 10 < 5:
                pyxel.circb(sx, sy, 18, YELLOW)

        # Speed lines if bursting
        if self.speed_burst > 0.5:
            for i in range(2):
                lx = sx - 10 - int(self.speed_burst * 2) + i * 6
                pyxel.line(lx, sy - 2 + i * 4, lx - 5, sy - 2 + i * 4, CYAN)

    def _draw_particles(self, shake_x: int, shake_y: int) -> None:
        for p in self.particles:
            sx, sy = self._world_to_screen(p.x, p.y)
            sx += shake_x
            sy += shake_y
            if sx < -4 or sx > SCREEN_W + 4 or sy < -4 or sy > SCREEN_H + 4:
                continue
            alpha = p.life / max(PARTICLE_LIFE_MIN, PARTICLE_LIFE_MAX)
            col = p.color if self.frame % 2 == 0 else WHITE
            if alpha < 0.3:
                col = GRAY
            pyxel.pset(int(sx), int(sy), col)

    def _draw_floating_texts(self, shake_x: int, shake_y: int) -> None:
        for ft in self.floating_texts:
            sx, sy = self._world_to_screen(ft.x, ft.y)
            sx += shake_x
            sy += shake_y
            if sx < -20 or sx > SCREEN_W + 20 or sy < -10 or sy > SCREEN_H + 10:
                continue
            alpha = ft.life / 30
            col = ft.color if alpha > 0.3 else GRAY
            self._text(ft.text, int(sx) - len(ft.text) * 4 // 2, int(sy), col)

    def _draw_hud(self) -> None:
        # Background strip
        pyxel.rect(0, 0, SCREEN_W, 14, BLACK)

        # Score
        self._text(f"SCORE: {self.score}", 2, 2, WHITE)

        # Combo
        if self.combo > 0:
            combo_text = f"COMBO x{self.combo}"
            col = WHITE
            if self.combo >= COMBO_THRESHOLD:
                col = ORANGE
            if self.super_mode:
                col = YELLOW
            self._text(combo_text, 95, 2, col)

        # Timer
        sec = max(0, self.game_timer // FPS)
        timer_col = WHITE if sec > 10 else (ORANGE if sec > 5 else RED)
        self._text(f"TIME: {sec}s", SCREEN_W - 80, 2, timer_col)

        # Bottom HUD
        pyxel.rect(0, SCREEN_H - 16, SCREEN_W, 16, BLACK)

        # HEAT bar
        bar_w = 80
        bar_x = 4
        bar_y = SCREEN_H - 13
        self._text("HEAT", bar_x, bar_y - 1, GRAY)
        bar_x += 25
        pyxel.rect(bar_x, bar_y, bar_w, 6, DARK_BLUE)
        fill_w = int(bar_w * min(1.0, self.heat / MAX_HEAT))
        heat_col = GREEN if self.heat < 40 else (YELLOW if self.heat < 70 else (ORANGE if self.heat < 90 else RED))
        if fill_w > 0:
            pyxel.rect(bar_x, bar_y, fill_w, 6, heat_col)
        pyxel.rectb(bar_x, bar_y, bar_w, 6, WHITE)

        # SUPER indicator
        if self.super_mode:
            super_remaining = self.super_timer / SUPER_DURATION
            super_bar_w = 60
            super_bar_x = SCREEN_W - super_bar_w - 4
            fill = int(super_bar_w * super_remaining)
            self._text("SUPER", super_bar_x - 32, bar_y - 1, YELLOW)
            pyxel.rect(super_bar_x, bar_y, super_bar_w, 6, DARK_BLUE)
            pyxel.rect(super_bar_x, bar_y, fill, 6, YELLOW)
            pyxel.rectb(super_bar_x, bar_y, super_bar_w, 6, WHITE)

        # Current stroke color indicator
        color = COLOR_MAP[self.stroke_color]
        pyxel.rect(SCREEN_W - 18, 2, 10, 10, color)
        pyxel.rectb(SCREEN_W - 18, 2, 10, 10, WHITE)

        # Echo indicator
        if self.echo_active:
            self._text("ECHO", SCREEN_W - 58, 2, CYAN)

        # Combo warning (blinking when close to SUPER)
        if self.super_mode:
            return
        if self.combo >= 3 and not self.super_mode:
            if self.frame % 30 < 15:
                self._text("READY!", SCREEN_W // 2, 2, YELLOW)

    # ── Text Helpers ─────────────────────────────────────────────────────

    def _text_center(self, s: str, y: int, col: int) -> None:
        if self._font is not None:
            w = self._font.text_width(s)
            x = (SCREEN_W - w) // 2
            pyxel.text(x + 1, y + 1, s, BLACK, self._font)
            pyxel.text(x, y, s, col, self._font)
        else:
            pyxel.text((SCREEN_W - len(s) * 4) // 2, y, s, col)

    def _text(self, s: str, x: int, y: int, col: int) -> None:
        if self._font is not None:
            pyxel.text(x + 1, y + 1, s, BLACK, self._font)
            pyxel.text(x, y, s, col, self._font)
        else:
            pyxel.text(x, y, s, col)


# ── Entry Point ───────────────────────────────────────────────────────────────


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
