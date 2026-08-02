"""SNOW CHAIN — Snowboard Color-Match COMBO Chain Prototype.

Core fun moment: riding through same-color gates in rapid succession, COMBO
building to 4+, then SUPER CARVE activates — all gates auto-match, score
explodes at 3x, and you blast ahead of the avalanche.
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

WIDTH = 320
HEIGHT = 240
FPS = 30
GAME_DURATION = 1800  # 60s * 30fps
SUPER_DURATION = 300  # 10s * 30fps

GROUND_Y = 200
PLAYER_BASE_Y = 160

HEAT_MAX = 100.0
SUPER_COMBO_THRESHOLD = 4

MAX_GATES = 6
MAX_ROCKS = 3

AVALANCHE_MARGIN = 20

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

GATE_COLORS = (RED, LIME, DARK_BLUE, YELLOW)
NUM_COLORS = len(GATE_COLORS)
RAINBOW = (RED, ORANGE, YELLOW, LIME, CYAN, PINK)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Gate:
    x: float
    y: float
    color: int
    passed: bool = False


@dataclass
class Rock:
    x: float
    y: float
    radius: int = 8


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


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------


class Game:
    phase: Phase
    score: int
    best_score: int
    combo: int
    max_combo: int
    heat: float
    timer: int
    super_timer: int
    frame: int
    player_x: float
    player_y: float
    player_vy: float
    player_color_idx: int
    player_on_ground: bool
    scroll_speed: float
    color_cycle_timer: int
    color_cycle_interval: int
    gate_spawn_timer: int
    gate_spawn_interval: int
    rock_spawn_timer: int
    rock_spawn_interval: int
    avalanche_edge: float
    avalanche_timer: int
    avalanche_interval: int
    stun_timer: int
    shake_frames: int
    gates: list[Gate]
    rocks: list[Rock]
    particles: list[Particle]
    floating_texts: list[FloatingText]
    ghost_trail: list[tuple[float, float]]
    snow_particles: list[tuple[float, float, float, float]]  # (x, y, vy, wx)
    _rng: random.Random

    def __new__(cls) -> Game:  # type: ignore[misc]
        obj = object.__new__(cls)
        obj.phase = Phase.TITLE
        obj.score = 0
        obj.best_score = 0
        obj.combo = 0
        obj.max_combo = 0
        obj.heat = 0.0
        obj.timer = GAME_DURATION
        obj.super_timer = 0
        obj.frame = 0
        obj.player_x = 160.0
        obj.player_y = float(PLAYER_BASE_Y)
        obj.player_vy = 0.0
        obj.player_color_idx = 0
        obj.player_on_ground = True
        obj.scroll_speed = 2.0
        obj.color_cycle_timer = 20
        obj.color_cycle_interval = 20
        obj.gate_spawn_timer = 90
        obj.gate_spawn_interval = 90
        obj.rock_spawn_timer = 180
        obj.rock_spawn_interval = 180
        obj.avalanche_edge = -20.0
        obj.avalanche_timer = 60
        obj.avalanche_interval = 60
        obj.stun_timer = 0
        obj.shake_frames = 0
        obj.gates = []
        obj.rocks = []
        obj.particles = []
        obj.floating_texts = []
        obj.ghost_trail = []
        obj.snow_particles = []
        obj._rng = random.Random()
        return obj

    def __init__(self) -> None:
        pyxel.init(WIDTH, HEIGHT, title="SNOW CHAIN", fps=FPS, display_scale=2)
        pyxel.mouse(False)
        self._init_snow(40)
        self.reset()
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = GAME_DURATION
        self.super_timer = 0
        self.frame = 0
        self.player_x = 160.0
        self.player_y = float(PLAYER_BASE_Y)
        self.player_vy = 0.0
        self.player_color_idx = 0
        self.player_on_ground = True
        self.scroll_speed = 2.0
        self.color_cycle_timer = 20
        self.color_cycle_interval = 20
        self.gate_spawn_timer = 90
        self.gate_spawn_interval = 90
        self.rock_spawn_timer = 180
        self.rock_spawn_interval = 180
        self.avalanche_edge = -20.0
        self.avalanche_timer = 60
        self.avalanche_interval = 60
        self.stun_timer = 0
        self.shake_frames = 0
        self.gates.clear()
        self.rocks.clear()
        self.particles.clear()
        self.floating_texts.clear()

    def _init_snow(self, count: int) -> None:
        self.snow_particles.clear()
        for _ in range(count):
            sx = self._rng.uniform(0, WIDTH)
            sy = self._rng.uniform(0, HEIGHT)
            svy = self._rng.uniform(0.3, 0.8)
            sw = self._rng.uniform(-0.5, 0.5)
            self.snow_particles.append((sx, sy, svy, sw))

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self) -> None:
        if self.phase is Phase.TITLE:
            self._update_title()
        elif self.phase is Phase.PLAYING:
            self._update_playing()
        elif self.phase is Phase.GAME_OVER:
            self._update_game_over()

    def _update_playing(self) -> None:
        self.frame += 1

        if self.shake_frames > 0:
            self.shake_frames -= 1

        # Timer
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self._end_game()
            return

        # Heat check (before decay)
        if self.heat >= HEAT_MAX:
            self._end_game()
            return

        # Heat decay
        self.heat = max(0.0, self.heat - 0.02)

        # Update escalation
        self._update_escalation()

        # SUPER timer
        if self.super_timer > 0:
            self.super_timer -= 1

        # Stun timer
        if self.stun_timer > 0:
            self.stun_timer -= 1

        # Input
        if pyxel.btnp(pyxel.KEY_SPACE) and self.stun_timer == 0:
            if self.player_on_ground:
                self.player_vy = -7.0
                self.player_on_ground = False

        # Player physics
        if not self.player_on_ground:
            self.player_vy += 0.45
            self.player_y += self.player_vy
            if self.player_y >= PLAYER_BASE_Y:
                self.player_y = float(PLAYER_BASE_Y)
                self.player_vy = 0.0
                self.player_on_ground = True

        # Color cycle
        self.color_cycle_timer -= 1
        if self.color_cycle_timer <= 0:
            self.color_cycle_timer = self.color_cycle_interval
            if self.super_timer == 0:
                self.player_color_idx = (self.player_color_idx + 1) % NUM_COLORS
            else:
                self.player_color_idx = (self.player_color_idx + 1) % len(RAINBOW)

        # Spawn gates
        self.gate_spawn_timer -= 1
        if self.gate_spawn_timer <= 0 and len(self.gates) < MAX_GATES:
            self.gate_spawn_timer = self.gate_spawn_interval
            self.gates.append(self._spawn_gate())

        # Spawn rocks
        self.rock_spawn_timer -= 1
        if self.rock_spawn_timer <= 0 and len(self.rocks) < MAX_ROCKS:
            self.rock_spawn_timer = self.rock_spawn_interval
            self.rocks.append(self._spawn_rock())

        # Scroll gates and rocks
        for gate in self.gates:
            gate.x -= self.scroll_speed
        for rock in self.rocks:
            rock.x -= self.scroll_speed

        # Process gates
        super_triggered = False
        for gate in self.gates:
            if not gate.passed and gate.x < self.player_x:
                combo_delta, score_gain, heat_gain, triggered = self._process_gate(gate)
                gate.passed = True
                if combo_delta > 0:
                    self.combo += combo_delta
                    self.max_combo = max(self.max_combo, self.combo)
                    self.score += score_gain
                    if triggered:
                        super_triggered = True
                    self._spawn_gate_particles(gate)
                    self._spawn_floating_text(
                        gate.x, gate.y - 10,
                        f"+{score_gain}", YELLOW,
                    )
                    if self.combo >= 2:
                        self._spawn_floating_text(
                            gate.x, gate.y - 24,
                            f"COMBO x{self.combo}", ORANGE,
                        )
                elif heat_gain > 0:
                    self.combo = 0
                    self.heat += heat_gain
                    self.stun_timer = 15
                    self.shake_frames = 4
                    self._spawn_floating_text(
                        gate.x, gate.y - 10,
                        "WRONG!", RED,
                    )

        if super_triggered:
            self._trigger_super()

        # SUPER CARVE trigger check (if combo just hit threshold)
        if (
            self.super_timer == 0
            and self.combo >= SUPER_COMBO_THRESHOLD
            and self.combo % SUPER_COMBO_THRESHOLD == 0
        ):
            self._trigger_super()

        # Process rock collisions
        for rock in self.rocks:
            heat_gain, combo_reset = self._process_rock_collision(rock)
            if heat_gain > 0:
                self.heat += heat_gain
                self.shake_frames = 6
                self._spawn_floating_text(
                    rock.x, rock.y - 16,
                    "OUCH!", RED,
                )
                self._spawn_rock_particles(rock)
                if combo_reset:
                    self.combo = 0

        # Update avalanche
        caught = self._update_avalanche()
        if caught:
            self.heat += 30
            self.combo = 0
            self.shake_frames = 10
            self.stun_timer = max(self.stun_timer, 30)
            self._spawn_floating_text(
                self.player_x - 20, self.player_y - 30,
                "AVALANCHE!", RED,
            )

        # Ghost trail recording (every 5 frames)
        if self.frame % 5 == 0:
            self.ghost_trail.append((self.player_x, self.player_y))

        # Remove off-screen elements
        self.gates = [g for g in self.gates if g.x > -50]
        self.rocks = [r for r in self.rocks if r.x > -20]

        # Update particles
        self._update_particles()

        # Update floating texts
        self._update_floating_texts()

        # Update snow
        self._update_snow()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.PLAYING
            self._init_snow(40)

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()
            self.phase = Phase.TITLE

    def _end_game(self) -> None:
        self.phase = Phase.GAME_OVER
        self.shake_frames = 16
        if self.score > self.best_score:
            self.best_score = self.score
            self.ghost_trail.clear()

    # ------------------------------------------------------------------
    # Playable logic (testable)
    # ------------------------------------------------------------------

    def _process_gate(self, gate: Gate) -> tuple[int, int, float, bool]:
        """Returns (combo_delta, score_gain, heat_gain, super_triggered)."""
        if gate.passed:
            return 0, 0, 0.0, False

        player_color = self._player_color()
        matched = gate.color == player_color
        is_super = self.super_timer > 0

        if matched or is_super:
            combo_delta = 1
            super_mult = 3.0 if is_super else 1.0
            score_gain = int(10 * self.combo * super_mult) if self.combo > 0 else int(10 * super_mult)
            triggered = False
            if not is_super and self.combo + 1 >= SUPER_COMBO_THRESHOLD and (self.combo + 1) % SUPER_COMBO_THRESHOLD == 0:
                triggered = True
            return combo_delta, score_gain, 0.0, triggered
        else:
            return 0, 0, 15.0, False

    def _process_rock_collision(self, rock: Rock) -> tuple[float, bool]:
        """Returns (heat_gain, combo_reset)."""
        if self.player_on_ground:
            dx = self.player_x - rock.x
            dy = self.player_y - rock.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < rock.radius + 8:
                self.stun_timer = 20
                return 25.0, True
        return 0.0, False

    def _update_avalanche(self) -> bool:
        """Advances avalanche edge, returns True if caught."""
        self.avalanche_timer -= 1
        if self.avalanche_timer <= 0:
            self.avalanche_timer = self.avalanche_interval
            elapsed = GAME_DURATION - self.timer
            advance = 2.0 + elapsed / (10 * FPS) * 0.5
            self.avalanche_edge += advance

        return self.player_x < self.avalanche_edge + AVALANCHE_MARGIN

    def _update_escalation(self) -> None:
        elapsed = GAME_DURATION - self.timer
        t = elapsed / GAME_DURATION

        self.scroll_speed = 2.0 + t * 3.0
        self.gate_spawn_interval = int(90 - t * 60)
        self.rock_spawn_interval = int(180 - t * 90)
        self.color_cycle_interval = int(20 - t * 8)
        self.avalanche_interval = int(60 - t * 30)

    def _spawn_gate(self) -> Gate:
        y = self._rng.uniform(130, 170)
        color = self._rng.choice(GATE_COLORS)
        return Gate(x=330.0, y=y, color=color)

    def _spawn_rock(self) -> Rock:
        y = 188.0
        return Rock(x=330.0, y=y, radius=8)

    def _check_gate_pass(self, player_x: float, gate: Gate) -> tuple[bool, bool]:
        """Returns (passed, matched)."""
        if gate.passed:
            return False, False
        if player_x > gate.x:
            return True, gate.color == self._player_color()
        return False, False

    def _player_color(self) -> int:
        if self.super_timer > 0:
            return RAINBOW[self.player_color_idx % len(RAINBOW)]
        return GATE_COLORS[self.player_color_idx % NUM_COLORS]

    def _trigger_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self.shake_frames = 6
        self._spawn_floating_text(
            self.player_x - 20, self.player_y - 40,
            "SUPER CARVE!", PINK,
        )
        for _ in range(20):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.5, 4.0)
            self.particles.append(Particle(
                x=self.player_x, y=self.player_y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=20, color=YELLOW,
            ))

    # ------------------------------------------------------------------
    # Particles
    # ------------------------------------------------------------------

    def _spawn_gate_particles(self, gate: Gate) -> None:
        p_color = gate.color
        for _ in range(8):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(Particle(
                x=gate.x, y=gate.y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=15, color=p_color,
            ))

    def _spawn_rock_particles(self, rock: Rock) -> None:
        for _ in range(6):
            angle = self._rng.uniform(-math.pi / 2, 0)
            speed = self._rng.uniform(1.0, 2.5)
            self.particles.append(Particle(
                x=rock.x, y=rock.y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=12, color=GRAY,
            ))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.2
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ------------------------------------------------------------------
    # Floating texts
    # ------------------------------------------------------------------

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=30, color=color))

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 1.0
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ------------------------------------------------------------------
    # Snow
    # ------------------------------------------------------------------

    def _update_snow(self) -> None:
        new_snow: list[tuple[float, float, float, float]] = []
        for sx, sy, svy, sw in self.snow_particles:
            sx += sw
            sy += svy
            if sy >= HEIGHT:
                sy = 0.0
                sx = self._rng.uniform(0, WIDTH)
            new_snow.append((sx, sy, svy, sw))
        self.snow_particles = new_snow

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self) -> None:
        pyxel.cls(BLACK)

        sx = 0
        sy = 0
        if self.shake_frames > 0:
            intensity = max(1, self.shake_frames // 3)
            sx = self._rng.randint(-intensity, intensity)
            sy = self._rng.randint(-intensity, intensity)

        if self.phase is Phase.TITLE:
            self._draw_scene_background(sx, sy)
            self._draw_title(sx, sy)
        elif self.phase is Phase.PLAYING:
            self._draw_scene_background(sx, sy)
            self._draw_playing(sx, sy)
        elif self.phase is Phase.GAME_OVER:
            self._draw_scene_background(sx, sy)
            self._draw_game_over(sx, sy)

    # ------------------------------------------------------------------
    # Scene background
    # ------------------------------------------------------------------

    def _draw_scene_background(self, sx: int, sy: int) -> None:
        # Sky gradient
        for y in range(0, int(GROUND_Y * 0.7)):
            t = y / (GROUND_Y * 0.7)
            col = NAVY if t < 0.33 else (LIGHT_BLUE if t < 0.66 else CYAN)
            pyxel.line(0, y + sy, WIDTH, y + sy, col)

        # Mountains (parallax - slower)
        mountain_shift = int(self.player_x * 0.15) % 300 if self.phase is Phase.PLAYING else 0
        if self.phase is Phase.GAME_OVER:
            mountain_shift = 0

        pyxel.tri(
            -100 - mountain_shift, 180 + sy,
            0 - mountain_shift, 100 + sy,
            100 - mountain_shift, 180 + sy,
            DARK_BLUE,
        )
        pyxel.tri(
            50 - mountain_shift, 180 + sy,
            150 - mountain_shift, 110 + sy,
            250 - mountain_shift, 180 + sy,
            DARK_BLUE,
        )
        pyxel.tri(
            120 - mountain_shift, 180 + sy,
            220 - mountain_shift, 95 + sy,
            320 - mountain_shift, 180 + sy,
            DARK_BLUE,
        )
        pyxel.tri(
            280 - mountain_shift, 180 + sy,
            380 - mountain_shift, 120 + sy,
            480 - mountain_shift, 180 + sy,
            DARK_BLUE,
        )

        # Ground
        pyxel.rect(0, GROUND_Y + sy, WIDTH, HEIGHT - GROUND_Y - sy, WHITE)
        pyxel.line(0, GROUND_Y + sy, WIDTH, GROUND_Y + sy, BROWN)
        pyxel.line(0, GROUND_Y + 1 + sy, WIDTH, GROUND_Y + 1 + sy, BROWN)

        # Snow mounds
        for i in range(8):
            mx = (i * 45 + int(self.player_x * 0.3) % 45) % (WIDTH + 40) - 20
            pyxel.circ(mx + sx, GROUND_Y + 8 + sy, 14, WHITE)
            pyxel.circb(mx + sx, GROUND_Y + 8 + sy, 14, GRAY)

    # ------------------------------------------------------------------
    # Title screen
    # ------------------------------------------------------------------

    def _draw_title(self, sx: int, sy: int) -> None:
        cx = WIDTH // 2
        pyxel.text(cx - 36 + sx, 20 + sy, "SNOW CHAIN", YELLOW)

        # Draw a snowboarder illustration
        bx = cx + sx
        by = 60 + sy
        pyxel.rect(bx + 8, by - 10, 18, 3, CYAN)
        pyxel.rect(bx + 8, by - 26, 18, 16, GRAY)
        pyxel.circ(bx + 17, by - 30, 5, GRAY)
        pyxel.rect(bx + 14, by - 33, 6, 3, WHITE)

        pyxel.text(cx - 58 + sx, 90 + sy, "Match gate colors", LIME)
        pyxel.text(cx - 60 + sx, 102 + sy, "to build COMBO chain!", CYAN)
        pyxel.text(cx - 52 + sx, 116 + sy, "COMBO x4 = SUPER CARVE", YELLOW)
        pyxel.text(cx - 54 + sx, 128 + sy, "(rainbow!), 3x score!", PINK)
        pyxel.text(cx - 54 + sx, 142 + sy, "Mismatch = HEAT + reset", RED)
        pyxel.text(cx - 44 + sx, 154 + sy, "AVOID rocks!", BROWN)
        pyxel.text(cx - 52 + sx, 166 + sy, "OUTRUN avalanche!", ORANGE)

        pyxel.text(cx - 60 + sx, 184 + sy, "SPACE: jump", WHITE)
        pyxel.text(cx - 46 + sx, 196 + sy, "Color auto-cycles", GRAY)

        if self.best_score > 0:
            pyxel.text(cx - 40 + sx, 212 + sy, f"BEST: {self.best_score}", PINK)

        pyxel.text(cx - 48 + sx, 228 + sy, "ENTER to START", WHITE)

    # ------------------------------------------------------------------
    # Playing screen
    # ------------------------------------------------------------------

    def _draw_playing(self, sx: int, sy: int) -> None:
        # Avalanche zone
        self._draw_avalanche(sx, sy)

        # Ghost trail
        self._draw_ghost_trail(sx, sy)

        # Gates
        for gate in self.gates:
            self._draw_gate(gate, sx, sy)

        # Rocks
        for rock in self.rocks:
            self._draw_rock(rock, sx, sy)

        # Player
        self._draw_player(sx, sy)

        # Particles
        for p in self.particles:
            pyxel.pset(int(p.x) + sx, int(p.y) + sy, p.color)

        # Floating texts
        for ft in self.floating_texts:
            tw = len(ft.text) * 4
            pyxel.text(int(ft.x - tw // 2) + sx, int(ft.y) + sy, ft.text, ft.color)

        # Snow
        for ssx, ssy, _, _ in self.snow_particles:
            pyxel.pset(int(ssx) + sx, int(ssy) + sy, WHITE)

        # Rainbow border during SUPER
        if self.super_timer > 0:
            rc = RAINBOW[self.frame // 4 % len(RAINBOW)]
            pyxel.rectb(sx, sy, WIDTH, HEIGHT, rc)
            pyxel.rectb(sx + 1, sy + 1, WIDTH - 2, HEIGHT - 2, rc)

        # Avalanche warning flash
        if self.avalanche_edge + 60 > self.player_x:
            if self.frame % 10 < 5:
                pyxel.rectb(sx, sy, WIDTH, HEIGHT, RED)

        # HUD
        self._draw_hud()

    def _draw_avalanche(self, sx: int, sy: int) -> None:
        edge = int(self.avalanche_edge) + sx
        if edge > WIDTH + sy:
            return
        left = max(sx, sx - 20 if self.phase is Phase.PLAYING else sx)
        for x in range(left, min(edge, WIDTH)):
            dither = (x // 2) % 2 == 0
            col = RED if dither else ORANGE
            pyxel.line(x, sy, x, HEIGHT + sy, col)

    def _draw_ghost_trail(self, sx: int, sy: int) -> None:
        if not self.ghost_trail:
            return
        for i, (gx, gy) in enumerate(self.ghost_trail):
            alpha = 0.3 + 0.7 * (i / len(self.ghost_trail))
            if alpha > 0.5:
                pyxel.pset(int(gx) + sx, int(gy) + sy, CYAN)

    def _draw_gate(self, gate: Gate, sx: int, sy: int) -> None:
        gx = int(gate.x) + sx
        gy = int(gate.y) + sy
        # Two vertical poles
        pyxel.rect(int(gx - 20), int(gy - 6), 2, 12, WHITE)
        pyxel.rect(int(gx + 18), int(gy - 6), 2, 12, WHITE)
        # Top bar (colored)
        bright_color = gate.color
        pyxel.rect(int(gx - 22), int(gy - 8), 44, 3, bright_color)

    def _draw_rock(self, rock: Rock, sx: int, sy: int) -> None:
        rx = int(rock.x) + sx
        ry = int(rock.y) + sy
        pyxel.circ(rx, ry, rock.radius, GRAY)
        pyxel.circb(rx, ry, rock.radius, DARK_BLUE)
        pyxel.circ(rx - 3, ry - 3, 3, LIGHT_BLUE)

    def _draw_player(self, sx: int, sy: int) -> None:
        px = int(self.player_x) + sx
        py = int(self.player_y) + sy

        color = self._player_color()
        is_super = self.super_timer > 0
        is_stunned = self.stun_timer > 0 and self.stun_timer % 4 < 2

        if is_stunned:
            color = RED

        # Snowboard
        pyxel.rect(px - 10, py + 4, 20, 3, color)

        # Body
        pyxel.rect(px - 3, py - 12, 6, 16, GRAY if is_super else WHITE)

        # Head
        head_color = color if is_super else GRAY
        pyxel.circ(px, py - 16, 5, head_color)

        # Goggles / visor
        pyxel.rect(px - 4, py - 20, 8, 3, YELLOW)

        # Arms (angled like snowboarding)
        lean = 3 if self.player_vy < 0 else -1
        pyxel.line(px - 3, py - 8, px - 5 - lean, py - 2, GRAY if is_super else WHITE)
        pyxel.line(px + 3 + lean, py - 6, px + 6 + lean, py, GRAY if is_super else WHITE)

        # SUPER glow
        if is_super:
            glow_r = 8 if self.frame % 12 < 6 else 6
            pyxel.circb(px, py - 14, glow_r, YELLOW)

    def _draw_hud(self) -> None:
        # HUD background
        pyxel.rect(0, 0, WIDTH, 24, BLACK)
        pyxel.line(0, 24, WIDTH, 24, DARK_BLUE)

        secs = max(0, self.timer // FPS)
        tc = RED if secs <= 10 else WHITE
        pyxel.text(4, 2, f"TIME:{secs}", tc)
        pyxel.text(72, 2, f"SCORE:{self.score}", WHITE)

        combo_color = RED if self.combo >= SUPER_COMBO_THRESHOLD else (YELLOW if self.combo >= 2 else GRAY)
        pyxel.text(170, 2, f"CMB:x{self.combo}", combo_color)

        if self.super_timer > 0:
            ss = self.super_timer // FPS
            pyxel.text(240, 2, f"SUPER:{ss}", PINK)

        # Heat bar
        hx = 170
        hy = 16
        hw = 147
        hh = 6
        pyxel.rectb(hx - 1, hy - 1, hw + 2, hh + 2, WHITE)
        pyxel.rect(hx, hy, hw, hh, NAVY)
        heat_fill = int(hw * self.heat / HEAT_MAX)
        heat_color = RED if self.heat > 60 else (ORANGE if self.heat > 30 else YELLOW)
        if heat_fill > 0:
            pyxel.rect(hx, hy, heat_fill, hh, heat_color)
        pyxel.text(4, 16, f"HEAT:{int(self.heat)}", WHITE)

        # Player color indicator
        pcol = self._player_color()
        pyxel.rect(75, 16, 12, 6, pcol)

    # ------------------------------------------------------------------
    # Game over screen
    # ------------------------------------------------------------------

    def _draw_game_over(self, sx: int, sy: int) -> None:
        # Overlay
        pyxel.rect(20, 40, WIDTH - 40, 160, BLACK)
        pyxel.rectb(20, 40, WIDTH - 40, 160, WHITE)

        cx = WIDTH // 2
        pyxel.text(cx - 36, 50, "GAME OVER", RED)

        if self.heat >= HEAT_MAX:
            pyxel.text(cx - 52, 70, "OVERHEATED!", ORANGE)
        elif self.timer <= 0:
            pyxel.text(cx - 36, 70, "TIME'S UP!", YELLOW)

        pyxel.text(cx - 48, 90, f"SCORE: {self.score}", WHITE)
        pyxel.text(cx - 50, 106, f"MAX COMBO: x{self.max_combo}", PINK)
        pyxel.text(cx - 40, 122, f"HEAT: {int(self.heat)}%", ORANGE)

        if self.score >= self.best_score:
            pyxel.text(cx - 30, 142, "NEW BEST!", YELLOW)
        pyxel.text(cx - 44, 158, f"BEST: {self.best_score}", WHITE)

        pyxel.text(cx - 40, 180, "R to RETRY", WHITE)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    Game()
