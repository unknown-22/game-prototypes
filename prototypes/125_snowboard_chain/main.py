"""125_snowboard_chain — Snowboard down a slope hitting same-color gates for COMBO.
Core fun moment: Split zones fork the slope into two lanes — player picks one,
ghost rides the other. When both hit matching gates, a massive SURGE bonus fires.
Risk/reward: chasing combos builds HEAT; wrong-color resets combo and adds HEAT.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import pyxel

# ── Phase Enum ──────────────────────────────────────────────────────────

class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    SPLIT = auto()
    CONVERGE = auto()
    GAME_OVER = auto()

# ── Constants ───────────────────────────────────────────────────────────

SCREEN_W = 320
SCREEN_H = 240

# Player
PLAYER_X = 160
PLAYER_Y = 200
PLAYER_SPEED = 4
PLAYER_W = 20
PLAYER_H = 28

# Gates
GATE_COLORS: tuple[int, int, int, int] = (8, 3, 5, 10)  # RED, GREEN, DARK_BLUE, YELLOW
GATE_NAMES: tuple[str, str, str, str] = ("RED", "GREEN", "BLUE", "YELLOW")
GATE_W = 40
GATE_H = 28
GATE_SPEED = 2.0
GATE_SPAWN_INTERVAL = 45

# Combo
SUPER_THRESHOLD = 5
SUPER_DURATION = 150
SUPER_MULTIPLIER = 3

# Split Zone
SPLIT_INTERVAL = 300
SPLIT_DURATION = 90
SPLIT_LANE_OFFSET = 50
SPLIT_Y = 120

# Resources
MAX_HP = 3
MAX_HEAT = 100
HEAT_WRONG_GATE = 15
HEAT_DECAY = 0.05
SURGE_HEAT_REDUCTION = 30

# Scoring
BASE_SCORE = 10
SURGE_BONUS = 200

# Invulnerability
INVULN_DURATION = 60

# Obstacles
OBSTACLE_SPAWN_CHANCE = 0.3
OBSTACLE_W = 24
OBSTACLE_H = 24

# Speeds
SPEED_RAMP = 0.001

# Converge
CONVERGE_DURATION = 30

# ── Data Classes ────────────────────────────────────────────────────────

@dataclass
class Gate:
    x: float
    y: float
    w: int = GATE_W
    h: int = GATE_H
    color: int = 0
    hit: bool = False
    lane: int = 0  # 0=main, 1=left, 2=right

@dataclass
class Obstacle:
    x: float
    y: float
    w: int = OBSTACLE_W
    h: int = OBSTACLE_H
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

@dataclass
class EchoGate:
    x: float
    y: float
    color: int
    life: int
    collected: bool = False

# ── Game Class ──────────────────────────────────────────────────────────

class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Snowboard Chain", display_scale=2, fps=30)
        bdf_path = Path(__file__).with_name("k8x12.bdf")
        if bdf_path.exists():
            pyxel.load(str(bdf_path), exclude_images=False, exclude_tilemaps=False,
                       exclude_sounds=False, exclude_musics=False)
        self._rng: random.Random
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.player_x: float = PLAYER_X
        self.hp: int = MAX_HP
        self.heat: float = 0.0
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.gates: list[Gate] = []
        self.obstacles: list[Obstacle] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.echo_gates: list[EchoGate] = []
        self.super_timer: int = 0
        self.super_mode: bool = False
        self.gate_spawn_timer: int = 0
        self.split_timer: int = 0
        self.split_active: bool = False
        self.split_elapsed: int = 0
        self.split_ghost_hit: bool = False
        self.split_player_lane: int = 0  # 0=unchosen, 1=left, 2=right
        self.player_color_idx: int = -1  # -1 means no gate hit yet
        self.scroll_speed: float = GATE_SPEED
        self.distance: int = 0
        self.frame: int = 0
        self.invuln_timer: int = 0
        self.converge_timer: int = 0
        self._rng = random.Random()

    # ── Update ───────────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.PLAYING
        elif self.phase == Phase.PLAYING:
            self._handle_input()
            self._update_gates()
            self._update_obstacles()
            self._update_collisions()
            self._update_heat()
            self._update_super()
            self._update_invuln()
            self._update_particles()
            self._update_floating_texts()
            self._update_echo_gates()
            self._update_split_timer()
            self._update_scroll_speed()
            self.frame += 1
            self.distance += int(self.scroll_speed)
        elif self.phase == Phase.SPLIT:
            self._handle_split_input()
            self._update_gates()
            self._update_split_collisions()
            self._update_split_timer()
            self._update_particles()
            self._update_floating_texts()
            self._update_echo_gates()
            self._update_scroll_speed()
            self.frame += 1
        elif self.phase == Phase.CONVERGE:
            self._update_converge()
            self._update_particles()
            self._update_floating_texts()
            self.frame += 1
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.PLAYING

    def _handle_input(self) -> None:
        dx = 0.0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx -= PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx += PLAYER_SPEED
        if dx != 0:
            self.player_x = max(PLAYER_W / 2, min(SCREEN_W - PLAYER_W / 2, self.player_x + dx))

    def _handle_split_input(self) -> None:
        if self.split_player_lane == 0:
            if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A):
                self.split_player_lane = 1
                self.player_x = SCREEN_W / 2 - SPLIT_LANE_OFFSET
            elif pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D):
                self.split_player_lane = 2
                self.player_x = SCREEN_W / 2 + SPLIT_LANE_OFFSET

    def _update_invuln(self) -> None:
        if self.invuln_timer > 0:
            self.invuln_timer -= 1

    def _update_scroll_speed(self) -> None:
        self.scroll_speed += SPEED_RAMP

    # ── Gate Spawning & Updates ──────────────────────────────────────────

    def _update_gates(self) -> None:
        for gate in self.gates:
            gate.y += self.scroll_speed
        # Check gates that passed player without being hit (missed gates)
        for gate in self.gates:
            if not gate.hit and gate.lane == 0 and gate.y > PLAYER_Y + PLAYER_H:
                gate.hit = True  # prevent double reset
                self.combo = 0
        # Remove off-screen gates
        self.gates = [g for g in self.gates if g.y < SCREEN_H + GATE_H]
        # Spawn new gates during PLAYING
        if self.phase == Phase.PLAYING:
            if self.gate_spawn_timer <= 0:
                self._spawn_gate()
                self.gate_spawn_timer = GATE_SPAWN_INTERVAL
            else:
                self.gate_spawn_timer -= 1
        # Spawn obstacles occasionally
        if (self.phase == Phase.PLAYING and self.frame % 90 == 30
                and self._rng.random() < OBSTACLE_SPAWN_CHANCE):
            self._spawn_obstacle()

    def _spawn_gate(self) -> None:
        color_idx = self._rng.randint(0, 3)
        x_margin = GATE_W
        x = self._rng.uniform(x_margin, SCREEN_W - x_margin)
        self.gates.append(Gate(x=x, y=-GATE_H, color=color_idx))

    def _spawn_obstacle(self) -> None:
        x_margin = OBSTACLE_W
        x = self._rng.uniform(x_margin, SCREEN_W - x_margin)
        self.obstacles.append(Obstacle(x=x, y=-OBSTACLE_H))

    def _update_obstacles(self) -> None:
        for obs in self.obstacles:
            obs.y += self.scroll_speed
        self.obstacles = [o for o in self.obstacles
                          if o.y < SCREEN_H + OBSTACLE_H and o.alive]

    # ── Collisions ───────────────────────────────────────────────────────

    def _update_collisions(self) -> None:
        if self.invuln_timer > 0:
            return
        px = self.player_x - PLAYER_W / 2
        py = PLAYER_Y - PLAYER_H / 2
        for gate in self.gates:
            if gate.hit or gate.lane != 0:
                continue
            if self._check_gate_hit(gate, px, py):
                self._on_gate_hit(gate)
        for obs in self.obstacles:
            if not obs.alive:
                continue
            ox = obs.x - OBSTACLE_W / 2
            oy = obs.y - OBSTACLE_H / 2
            if (px < ox + OBSTACLE_W and px + PLAYER_W > ox
                    and py < oy + OBSTACLE_H and py + PLAYER_H > oy):
                self._on_obstacle_hit(obs)

    def _check_gate_hit(self, gate: Gate, px: float, py: float) -> bool:
        gx = gate.x - GATE_W / 2
        gy = gate.y
        return (px < gx + GATE_W and px + PLAYER_W > gx
                and py < gy + GATE_H and py + PLAYER_H > gy)

    def _on_gate_hit(self, gate: Gate) -> None:
        gate.hit = True
        is_same_color = (gate.color == self.player_color_idx)
        is_first = (self.player_color_idx == -1)
        if is_first or is_same_color:
            self.combo += 1
            multiplier = SUPER_MULTIPLIER if self.super_mode else 1
            points = BASE_SCORE * self.combo * multiplier
            self.score += points
            self._spawn_particles(gate.x, gate.y, GATE_COLORS[gate.color], 10)
            self._spawn_floating_text(gate.x, gate.y, f"+{points}", GATE_COLORS[gate.color])
            if self.combo >= SUPER_THRESHOLD and not self.super_mode:
                self.super_mode = True
                self.super_timer = SUPER_DURATION
                self._spawn_floating_text(SCREEN_W / 2, 80, "SUPER!!", 9)
        else:
            self.combo = 0
            self.heat = min(float(MAX_HEAT), self.heat + HEAT_WRONG_GATE)
            self._spawn_floating_text(gate.x, gate.y, "WRONG!", 8)
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        self.player_color_idx = gate.color

    def _on_obstacle_hit(self, obs: Obstacle) -> None:
        obs.alive = False
        self.hp -= 1
        self.invuln_timer = INVULN_DURATION
        self._spawn_particles(obs.x, obs.y, 8, 5)
        self._spawn_floating_text(obs.x, obs.y, "-1 HP", 8)
        if self.hp <= 0:
            self.phase = Phase.GAME_OVER

    def _update_split_collisions(self) -> None:
        """Check gate collisions during SPLIT phase for the player's chosen lane."""
        if self.split_player_lane == 0:
            return
        px = self.player_x - PLAYER_W / 2
        py = PLAYER_Y - PLAYER_H / 2
        for gate in self.gates:
            if gate.hit or gate.lane != self.split_player_lane:
                continue
            if self._check_gate_hit(gate, px, py):
                gate.hit = True
                self._spawn_particles(gate.x, gate.y, GATE_COLORS[gate.color], 8)

    # ── Split Zone ───────────────────────────────────────────────────────

    def _update_split_timer(self) -> None:
        if self.phase == Phase.PLAYING:
            self.split_timer += 1
            if self.split_timer >= SPLIT_INTERVAL:
                self._start_split_zone()
        elif self.phase == Phase.SPLIT:
            self.split_elapsed += 1
            if self.split_elapsed >= SPLIT_DURATION:
                self._end_split_zone()

    def _start_split_zone(self) -> None:
        self.phase = Phase.SPLIT
        self.split_active = True
        self.split_elapsed = 0
        self.split_timer = 0
        self.split_player_lane = 0
        self.split_ghost_hit = False
        # Remove normal (non-lane) gates to avoid clutter during split
        self.gates = [g for g in self.gates if g.lane != 0]
        # Spawn two gates at split lanes
        color = self._rng.randint(0, 3)
        self.gates.append(Gate(
            x=SCREEN_W / 2 - SPLIT_LANE_OFFSET, y=-GATE_H, color=color, lane=1,
        ))
        self.gates.append(Gate(
            x=SCREEN_W / 2 + SPLIT_LANE_OFFSET, y=-GATE_H, color=color, lane=2,
        ))

    def _end_split_zone(self) -> None:
        self.phase = Phase.CONVERGE
        self.converge_timer = CONVERGE_DURATION
        self.split_active = False
        # Determine ghost outcome
        self.split_ghost_hit = self._rng.random() < 0.8
        # Did player hit their gate?
        split_gates = [g for g in self.gates if g.lane in (1, 2)]
        player_hit = any(g.hit and g.lane == self.split_player_lane for g in split_gates)
        # Apply results
        if player_hit and self.split_ghost_hit:
            self.score += SURGE_BONUS
            self.combo += 2
            self.heat = max(0.0, self.heat - SURGE_HEAT_REDUCTION)
            self._spawn_particles(SCREEN_W / 2, PLAYER_Y, 7, 30)
            self._spawn_floating_text(SCREEN_W / 2, PLAYER_Y - 20,
                                     f"+{SURGE_BONUS} SURGE!", 9)
            # Spawn echo gates from the surge
            self._add_echo_gate(SCREEN_W / 2 - 40, PLAYER_Y - 30, 0)
            self._add_echo_gate(SCREEN_W / 2 + 40, PLAYER_Y - 30, 1)
        elif player_hit:
            multiplier = SUPER_MULTIPLIER if self.super_mode else 1
            points = BASE_SCORE * self.combo * multiplier
            self.score += points
            self.combo += 1
            self._spawn_floating_text(SCREEN_W / 2, PLAYER_Y - 20,
                                     f"+{points}", 9)
        else:
            self.combo = 0
            self.heat = min(float(MAX_HEAT), self.heat + HEAT_WRONG_GATE)
            self._spawn_floating_text(SCREEN_W / 2, PLAYER_Y - 20, "MISS!", 8)
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        if self.combo >= SUPER_THRESHOLD and not self.super_mode:
            self.super_mode = True
            self.super_timer = SUPER_DURATION
        # Reset player position and clear split gates
        self.player_x = PLAYER_X
        self.gates = [g for g in self.gates if g.lane == 0]

    def _update_converge(self) -> None:
        self.converge_timer -= 1
        if self.converge_timer <= 0:
            self.phase = Phase.PLAYING

    # ── Heat ─────────────────────────────────────────────────────────────

    def _update_heat(self) -> None:
        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    # ── Super ────────────────────────────────────────────────────────────

    def _update_super(self) -> None:
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False

    # ── Particles ────────────────────────────────────────────────────────

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-3.0, 3.0)
            vy = self._rng.uniform(-4.0, -0.5)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=25, color=color))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.3
            p.vx *= 0.98
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ── Floating Text ────────────────────────────────────────────────────

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=45, color=color))

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.8
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ── Echo Gates ───────────────────────────────────────────────────────

    def _add_echo_gate(self, x: float, y: float, color: int) -> None:
        self.echo_gates.append(EchoGate(x=x, y=y, color=color, life=120))

    def _update_echo_gates(self) -> None:
        for eg in self.echo_gates:
            eg.life -= 1
        self.echo_gates = [eg for eg in self.echo_gates if eg.life > 0]
        for eg in self.echo_gates:
            if eg.collected:
                continue
            if abs(self.player_x - eg.x) < 20 and abs(PLAYER_Y - eg.y) < 22:
                eg.collected = True
                self.score += 50
                self._spawn_floating_text(eg.x, eg.y, "+50 ECHO", 12)

    # ── Draw ─────────────────────────────────────────────────────────────

    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.PLAYING, Phase.SPLIT, Phase.CONVERGE):
            self._draw_playfield()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.cls(1)
        pyxel.text(80, 50, "SNOWBOARD CHAIN", 7)
        pyxel.text(110, 110, "PRESS SPACE", 7)
        pyxel.text(80, 140, "LEFT/RIGHT: Move", 6)
        pyxel.text(55, 155, "Hit same-color gates for COMBO!", 6)
        pyxel.text(40, 170, "Split zones: choose lane, get SURGE!", 6)
        # Draw a preview snowboarder
        self._draw_player(160, 85, False, False)

    def _draw_playfield(self) -> None:
        # Sky background with gradient-like stripes
        pyxel.cls(6)
        for i in range(20):
            band_y = (i * 12 + self.frame * 2) % SCREEN_H
            shade = 6 if i % 3 != 0 else 12
            pyxel.rect(0, band_y, SCREEN_W, 2, shade)

        # Snow ground
        pyxel.rect(0, 210, SCREEN_W, 30, 7)
        # Snow surface detail
        for i in range(16):
            sx = (i * 20 + self.frame * 3) % SCREEN_W
            pyxel.rect(sx, 208, 3, 3, 13)

        # Draw split zone indicators
        if self.phase == Phase.SPLIT:
            self._draw_split_indicators()
        elif self.phase == Phase.CONVERGE:
            self._draw_converge_effect()

        # Draw obstacles
        for obs in self.obstacles:
            if obs.alive:
                self._draw_obstacle(obs)

        # Draw gates
        for gate in self.gates:
            self._draw_gate(gate)

        # Draw echo gates
        for eg in self.echo_gates:
            if not eg.collected and (eg.life // 6) % 2 == 0:
                c = GATE_COLORS[eg.color % len(GATE_COLORS)]
                pyxel.rect(int(eg.x) - 8, int(eg.y) - 8, 16, 16, c)
                pyxel.rectb(int(eg.x) - 8, int(eg.y) - 8, 16, 16, 7)

        # Draw player (with blink during invulnerability)
        blink = self.invuln_timer > 0 and (self.invuln_timer // 4) % 2 == 0
        if not blink:
            self._draw_player(self.player_x, PLAYER_Y, self.super_mode,
                             self.phase == Phase.SPLIT)

        # Draw particles
        for p in self.particles:
            alpha = max(p.life, 6)
            if alpha > 0:
                pyxel.pset(int(p.x), int(p.y), p.color)

        # Draw floating texts
        for ft in self.floating_texts:
            color = ft.color if ft.life > 10 else 13
            pyxel.text(int(ft.x - len(ft.text) * 2), int(ft.y), ft.text, color)

        # Draw HUD
        self._draw_hud()

    def _draw_split_indicators(self) -> None:
        # Vertical divider
        pyxel.rect(SCREEN_W // 2 - 1, 0, 2, SCREEN_H, 1)

        # Labels
        pyxel.text(SCREEN_W // 2 - 75, 70, "<- LEFT", 7)
        pyxel.text(SCREEN_W // 2 + 35, 70, "RIGHT ->", 7)

        # Highlight chosen lane
        if self.split_player_lane == 1:
            pyxel.rect(SCREEN_W // 2 - 65, 90, 55, 12, 10)
            pyxel.text(SCREEN_W // 2 - 55, 92, "GO!", 0)
        elif self.split_player_lane == 2:
            pyxel.rect(SCREEN_W // 2 + 10, 90, 55, 12, 10)
            pyxel.text(SCREEN_W // 2 + 20, 92, "GO!", 0)

    def _draw_converge_effect(self) -> None:
        progress = 1.0 - (self.converge_timer / CONVERGE_DURATION)
        # Flash at start
        if self.converge_timer > CONVERGE_DURATION - 10:
            color = 10 if self.split_ghost_hit else 8
            a = (self.converge_timer - (CONVERGE_DURATION - 10))
            if a % 3 == 0:
                pyxel.rect(0, 0, SCREEN_W, SCREEN_H, color)
        # Converging lines
        offset = int(progress * SPLIT_LANE_OFFSET)
        pyxel.line(SCREEN_W // 2 - offset, 0, SCREEN_W // 2, SCREEN_H, 7)
        pyxel.line(SCREEN_W // 2 + offset, 0, SCREEN_W // 2, SCREEN_H, 7)

    def _draw_player(self, x: float, y: float, super_mode: bool, _split_mode: bool) -> None:
        ix = int(x)
        iy = int(y)
        # Board
        pyxel.rect(ix - 12, iy + 12, 24, 3, 4)
        # Body
        if super_mode:
            body_color = [8, 3, 5, 10][(self.frame // 4) % 4]
        else:
            body_color = 7
        pyxel.rect(ix - 7, iy - 4, 14, 16, body_color)
        # Head
        pyxel.rect(ix - 4, iy - 10, 8, 6, 7)
        # Goggles
        pyxel.rect(ix - 2, iy - 9, 4, 2, 1)

    def _draw_gate(self, gate: Gate) -> None:
        gx = int(gate.x - GATE_W / 2)
        gy = int(gate.y)
        color = GATE_COLORS[gate.color]
        if gate.hit:
            color = 13  # GRAY when already hit
        # Gate arch: two pillars + top bar
        pillar_w = 4
        # Top bar
        pyxel.rect(gx, gy, GATE_W, 5, color)
        # Left pillar
        pyxel.rect(gx, gy + 5, pillar_w, GATE_H - 5, color)
        # Right pillar
        pyxel.rect(gx + GATE_W - pillar_w, gy + 5, pillar_w, GATE_H - 5, color)
        # Lane indicator
        if gate.lane == 1:
            pyxel.text(gx - 10, gy + 8, "L", 7)
        elif gate.lane == 2:
            pyxel.text(gx + GATE_W + 4, gy + 8, "R", 7)

    def _draw_obstacle(self, obs: Obstacle) -> None:
        ox = int(obs.x - OBSTACLE_W / 2)
        oy = int(obs.y - OBSTACLE_H / 2)
        # Rock shape
        pyxel.rect(ox + 4, oy, OBSTACLE_W - 8, OBSTACLE_H - 4, 4)
        pyxel.rect(ox, oy + 6, OBSTACLE_W, OBSTACLE_H - 6, 4)
        pyxel.rect(ox + 4, oy + 2, OBSTACLE_W - 8, OBSTACLE_H - 2, 5)

    def _draw_hud(self) -> None:
        # Score
        pyxel.text(4, 4, f"SCORE: {self.score}", 7)
        # Combo
        combo_color = 10 if self.combo >= SUPER_THRESHOLD else 7
        pyxel.text(4, 14, f"COMBO: x{self.combo}", combo_color)
        # Max combo
        pyxel.text(4, 24, f"MAX: x{self.max_combo}", 5)

        # HP hearts
        for i in range(MAX_HP):
            hx = SCREEN_W - 80 + i * 16
            if i < self.hp:
                pyxel.text(hx, 4, "O", 8)
            else:
                pyxel.text(hx, 4, "X", 5)

        # HEAT bar
        pyxel.text(SCREEN_W - 80, 14, "HEAT", 7)
        bar_w = 70
        bar_h = 6
        bar_x = SCREEN_W - 80
        bar_y = 20
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, 5)
        heat_w = int(bar_w * self.heat / MAX_HEAT)
        if self.heat > 70:
            heat_color = 8
        elif self.heat > 40:
            heat_color = 10
        else:
            heat_color = 3
        if heat_w > 0:
            pyxel.rect(bar_x, bar_y, heat_w, bar_h, heat_color)

        # SUPER indicator
        if self.super_mode:
            timer_sec = self.super_timer // 30
            pyxel.text(SCREEN_W // 2 - 30, 4, f"SUPER! {timer_sec}s", 9)

        # Split zone approaching warning
        if self.phase == Phase.PLAYING:
            remaining = SPLIT_INTERVAL - self.split_timer
            if remaining < 60:
                pyxel.text(SCREEN_W // 2 - 35, SCREEN_H - 20, f"SPLIT IN {remaining}", 9)

    def _draw_game_over(self) -> None:
        pyxel.cls(1)
        pyxel.text(115, 50, "GAME OVER", 8)
        pyxel.text(100, 90, f"SCORE: {self.score}", 7)
        pyxel.text(85, 105, f"MAX COMBO: x{self.max_combo}", 10)
        pyxel.text(90, 150, "PRESS SPACE TO RETRY", 7)


# ── Factory for headless testing ───────────────────────────────────────

def _make_game(seed: int = 42) -> Game:
    """Create a Game instance bypassing pyxel.init/run for tests."""
    g = Game.__new__(Game)
    g.reset()
    g._rng = random.Random(seed)
    return g


# ── Entry Point ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    Game()
