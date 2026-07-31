"""SUMO SURGE — Top-Down Sumo Wrestling Color-Match Arena

The most fun moment:
    同色のパワーゾーンを追いかけてCOMBOを4以上まで積み上げ、
    SUPER SUMOを発動させて相手を土俵の外に吹き飛ばす瞬間が面白い。

Core loop: Move wrestler, collect matching-color power zones to build COMBO.
COMBO>=4 triggers SUPER SUMO (rainbow mode, 3x force, auto-match all colors).
Push the AI out of the ring to score ring-outs. First to 3 wins.
HEAT punishes mismatches — at HEAT>=100 the AI gets a free super-push.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto


import pyxel

# ── Constants ──
SCREEN_W = 320
SCREEN_H = 240
FPS = 30
GAME_TIMER = 1800  # 60 seconds at 30 FPS
WIN_THRESHOLD = 3

RING_CX = 160
RING_CY = 130
RING_RADIUS = 90

WRESTLER_RADIUS = 14
ZONE_RADIUS = 7
MAX_ZONES = 6

# Colors (raw ints)
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

PLAYER_COLORS: list[int] = [RED, LIME, DARK_BLUE, YELLOW]
COLOR_NAMES: list[str] = ["RED", "LIME", "DARK_BLUE", "YELLOW"]
RAINBOW: list[int] = [RED, ORANGE, YELLOW, LIME, CYAN, PINK]

PLAYER_SPEED = 2.0
AI_SPEED = 1.5
SUPER_THRESHOLD = 4
SUPER_DURATION = 300  # 10 seconds at 30 FPS
SUPER_FORCE_MULT = 3.0

ZONE_SPAWN_INTERVAL_START = 35
ZONE_SPAWN_INTERVAL_MIN = 20
ZONE_SPAWN_INTERVAL_DECREASE = 1  # every 120f
ZONE_SPAWN_INTERVAL_PERIOD = 120
ZONE_LIFE = 300  # 10 seconds

COLOR_CYCLE_FRAMES = 20  # player color cycle every 20 frames
AI_COLOR_CYCLE_FRAMES = 25

HEAT_MISMATCH = 15
HEAT_PUSHED_OUT = 10
HEAT_DECAY = 0.02
HEAT_CAP = 100
OVERHEAT_DURATION = 120
OVERHEAT_FORCE_BONUS = 0.5

ROUND_END_DURATION = 60  # 2 seconds

# ── Data Classes ──


@dataclass
class Wrestler:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    radius: int = WRESTLER_RADIUS
    color_idx: int = 0
    push_force: float = 1.0
    stunned: int = 0


@dataclass
class PowerZone:
    x: float
    y: float
    color_idx: int
    life: int = ZONE_LIFE
    radius: int = ZONE_RADIUS


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


# ── Phase Enum ──


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    ROUND_END = auto()
    GAME_OVER = auto()


# ── Game ──


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="SUMO SURGE", fps=FPS)
        self._rng: random.Random = random.Random()
        self._init_state()
        pyxel.run(self._update, self._draw)

    def _init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.player: Wrestler = Wrestler(x=RING_CX, y=RING_CY + 30)
        self.ai: Wrestler = Wrestler(x=RING_CX, y=RING_CY - 30)
        self.zones: list[PowerZone] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.player_ringouts: int = 0
        self.ai_ringouts: int = 0
        self.heat: float = 0.0
        self.overheat_timer: int = 0  # frames remaining for AI power bonus
        self.super_timer: int = 0
        self.color_timer: int = COLOR_CYCLE_FRAMES
        self.ai_color_timer: int = AI_COLOR_CYCLE_FRAMES
        self.timer: int = GAME_TIMER
        self.zone_spawn_timer: int = ZONE_SPAWN_INTERVAL_START
        self.zone_spawn_interval: int = ZONE_SPAWN_INTERVAL_START
        self.zone_spawn_speedup_counter: int = 0
        self.shake_frames: int = 0
        self.best_score: int = 0
        self.round_end_timer: int = 0

    # ── Public API for reset ──

    def reset(self) -> None:
        best = self.best_score
        self._init_state()
        self.best_score = best

    # ══════════════════════════════════════════════════
    #  Testable Logic (no Pyxel input calls)
    # ══════════════════════════════════════════════════

    def _cycle_color(self) -> None:
        """Advance player color_idx every COLOR_CYCLE_FRAMES."""
        self.color_timer -= 1
        if self.color_timer <= 0:
            self.color_timer = COLOR_CYCLE_FRAMES
            self.player.color_idx = (self.player.color_idx + 1) % 4

    def _cycle_ai_color(self) -> None:
        """Advance AI color_idx independently."""
        self.ai_color_timer -= 1
        if self.ai_color_timer <= 0:
            self.ai_color_timer = AI_COLOR_CYCLE_FRAMES
            self.ai.color_idx = (self.ai.color_idx + 1) % 4

    def _spawn_zone(self) -> None:
        """Spawn a random-colored zone at a random position inside the ring."""
        if len(self.zones) >= MAX_ZONES:
            return
        for _ in range(20):
            angle = self._rng.uniform(0, math.pi * 2)
            dist = self._rng.uniform(0, RING_RADIUS - ZONE_RADIUS - 5)
            cx = RING_CX + math.cos(angle) * dist
            cy = RING_CY + math.sin(angle) * dist
            # ensure not too close to wrestlers
            if (math.hypot(cx - self.player.x, cy - self.player.y) < WRESTLER_RADIUS + ZONE_RADIUS + 4
                    or math.hypot(cx - self.ai.x, cy - self.ai.y) < WRESTLER_RADIUS + ZONE_RADIUS + 4):
                continue
            color_idx = self._rng.randint(0, 3)
            self.zones.append(PowerZone(x=cx, y=cy, color_idx=color_idx))
            return

    def _update_zones(self) -> None:
        """Decrement zone life, remove expired."""
        for z in self.zones[:]:
            z.life -= 1
            if z.life <= 0:
                self.zones.remove(z)

    def _check_zone_collisions(self) -> None:
        """Check player overlap with zones; match/mismatch logic."""
        for z in self.zones[:]:
            dist = math.hypot(self.player.x - z.x, self.player.y - z.y)
            if dist > WRESTLER_RADIUS + z.radius:
                continue

            if self.super_timer > 0:
                # SUPER mode: auto-match always
                self.combo += 1
                self.max_combo = max(self.max_combo, self.combo)
                self._spawn_particles_zone(z.x, z.y, 16, RAINBOW)
                self.floating_texts.append(
                    FloatingText(z.x, z.y - 6, f"COMBO x{self.combo}", 40, CYAN)
                )
                self.zones.remove(z)
            elif z.color_idx == self.player.color_idx:
                self.combo += 1
                self.max_combo = max(self.max_combo, self.combo)
                self._spawn_particles_zone(z.x, z.y, 8, PLAYER_COLORS[z.color_idx])
                self.floating_texts.append(
                    FloatingText(z.x, z.y - 6, f"COMBO x{self.combo}", 40, YELLOW)
                )
                self.zones.remove(z)
                self._check_super_activation()
            else:
                self.combo = 0
                self.heat = min(HEAT_CAP, self.heat + HEAT_MISMATCH)
                self._spawn_particles_zone(z.x, z.y, 3, RED)
                self.floating_texts.append(
                    FloatingText(z.x, z.y - 6, "WRONG!", 30, RED)
                )
                self.zones.remove(z)

    def _update_push_force(self) -> None:
        """Recalculate push_force based on COMBO and super mode."""
        if self.super_timer > 0:
            self.player.push_force = (1.0 + self.combo * 0.3) * SUPER_FORCE_MULT
        else:
            self.player.push_force = 1.0 + self.combo * 0.3

    def _check_push(self) -> None:
        """Check player-AI distance; if overlapping, apply push forces."""
        dx = self.ai.x - self.player.x
        dy = self.ai.y - self.player.y
        dist = math.hypot(dx, dy)
        min_dist = WRESTLER_RADIUS + WRESTLER_RADIUS

        if dist < min_dist and dist > 0:
            nx = dx / dist
            ny = dy / dist
            overlap = (min_dist - dist) * 0.5 + 0.5

            ai_force = self.ai.push_force
            if self.overheat_timer > 0:
                ai_force *= 1.0 + OVERHEAT_FORCE_BONUS

            player_power = self.player.push_force * overlap
            ai_power = ai_force * overlap

            # Apply forces
            self.player.x -= nx * ai_power
            self.player.y -= ny * ai_power
            self.ai.x += nx * player_power
            self.ai.y += ny * player_power

            if player_power > ai_power:
                self._spawn_particles_push(self.ai.x, self.ai.y, 4, WHITE)
            elif ai_power > player_power:
                self._spawn_particles_push(self.player.x, self.player.y, 4, ORANGE)

    def _check_ring_boundary(self, w: Wrestler) -> bool:
        """Return True if the wrestler is outside the ring."""
        return math.hypot(w.x - RING_CX, w.y - RING_CY) > RING_RADIUS

    def _check_ring_out(self) -> None:
        """Check if either wrestler is outside the ring; handle ring-outs."""
        player_out = self._check_ring_boundary(self.player)
        ai_out = self._check_ring_boundary(self.ai)

        if player_out and ai_out:
            # Both pushed out simultaneously: respawn at center
            self.player.x = RING_CX
            self.player.y = RING_CY + 5
            self.player.vx = 0.0
            self.player.vy = 0.0
            self.ai.x = RING_CX
            self.ai.y = RING_CY - 5
            self.ai.vx = 0.0
            self.ai.vy = 0.0
            self.shake_frames = 5
            return

        if ai_out:
            self.player_ringouts += 1
            self.score += 100 + self.combo * 10
            self.best_score = max(self.best_score, self.score)
            self.shake_frames = 12
            self._spawn_particles_ring_out(self.ai.x, self.ai.y)
            self.floating_texts.append(
                FloatingText(self.ai.x, self.ai.y - 10, "RING OUT!", 50, YELLOW)
            )
            self._check_round_end()

        if player_out:
            self.ai_ringouts += 1
            self.heat = min(HEAT_CAP, self.heat + HEAT_PUSHED_OUT)
            self.combo = 0
            self.shake_frames = 8
            self._spawn_particles_ring_out(self.player.x, self.player.y)
            self.floating_texts.append(
                FloatingText(self.player.x, self.player.y - 10, "OUT!", 40, RED)
            )
            self._check_round_end()

    def _check_round_end(self) -> None:
        """Check if win threshold reached or timer expired."""
        if self.player_ringouts >= WIN_THRESHOLD or self.ai_ringouts >= WIN_THRESHOLD or self.timer <= 0:
            self.best_score = max(self.best_score, self.compute_score())
            self.phase = Phase.GAME_OVER
            self.shake_frames = 20
            self._spawn_particles_ring_out(RING_CX, RING_CY)
        else:
            self.phase = Phase.ROUND_END
            self.round_end_timer = ROUND_END_DURATION

    def _reset_round(self) -> None:
        """Reset wrestler positions for a new round."""
        self.player.x = RING_CX
        self.player.y = RING_CY + 30
        self.player.vx = 0.0
        self.player.vy = 0.0
        self.player.stunned = 0
        self.ai.x = RING_CX
        self.ai.y = RING_CY - 30
        self.ai.vx = 0.0
        self.ai.vy = 0.0
        self.ai.stunned = 0
        self.combo = 0
        self.zones.clear()
        self.zone_spawn_interval = ZONE_SPAWN_INTERVAL_START
        self.zone_spawn_timer = ZONE_SPAWN_INTERVAL_START
        self.zone_spawn_speedup_counter = 0
        self.phase = Phase.PLAYING

    def _update_ai(self) -> None:
        """AI movement logic: target zone or push toward player."""
        if self.ai.stunned > 0:
            self.ai.stunned -= 1
            return

        # AI near edge: prioritize moving toward center
        ai_dist_from_center = math.hypot(self.ai.x - RING_CX, self.ai.y - RING_CY)
        edge_danger = ai_dist_from_center > RING_RADIUS - 25

        dist_to_player = math.hypot(self.player.x - self.ai.x, self.player.y - self.ai.y)

        target_x: float
        target_y: float

        if edge_danger:
            # Move toward center
            target_x = RING_CX
            target_y = RING_CY
        elif dist_to_player < 40:
            # Move toward player to push
            target_x = self.player.x
            target_y = self.player.y
        else:
            # Find nearest matching zone
            zone = self._find_nearest_zone(self.ai.x, self.ai.y, self.ai.color_idx)
            if zone:
                target_x = zone.x
                target_y = zone.y
            else:
                target_x = RING_CX
                target_y = RING_CY

        dx = target_x - self.ai.x
        dy = target_y - self.ai.y
        target_dist = math.hypot(dx, dy)
        if target_dist > 0:
            speed = AI_SPEED
            if self.overheat_timer > 0:
                speed *= 1.3
            self.ai.vx = (dx / target_dist) * speed
            self.ai.vy = (dy / target_dist) * speed
        else:
            self.ai.vx = 0.0
            self.ai.vy = 0.0

        self.ai.x += self.ai.vx
        self.ai.y += self.ai.vy

    def _find_nearest_zone(self, wx: float, wy: float, color_idx: int) -> PowerZone | None:
        """Find the nearest zone of a given color."""
        best: PowerZone | None = None
        best_dist: float = float("inf")
        for z in self.zones:
            if z.color_idx == color_idx:
                d = math.hypot(wx - z.x, wy - z.y)
                if d < best_dist:
                    best_dist = d
                    best = z
        return best

    def _update_heat(self) -> None:
        """HEAT decay, overheat activation."""
        if self.heat >= HEAT_CAP and self.overheat_timer <= 0:
            self.overheat_timer = OVERHEAT_DURATION
            self.heat = HEAT_CAP  # clamp
            self.floating_texts.append(
                FloatingText(RING_CX, RING_CY - 40, "OVERHEAT!", 40, RED)
            )

        if self.overheat_timer > 0:
            self.overheat_timer -= 1
            if self.overheat_timer <= 0:
                self.heat = 50.0  # cooldown after overheat
        else:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _check_super_activation(self) -> None:
        """If COMBO >= threshold and not in super mode, activate SUPER SUMO."""
        if self.combo >= SUPER_THRESHOLD and self.super_timer <= 0:
            self.super_timer = SUPER_DURATION
            self._spawn_particles_zone(RING_CX, RING_CY - 20, 30, RAINBOW)
            self.floating_texts.append(
                FloatingText(RING_CX, RING_CY - 30, "SUPER SUMO!", 60, CYAN)
            )

    def compute_score(self) -> int:
        """Compute total score: ringouts * 100 + max_combo * 10 + timer_bonus."""
        return self.player_ringouts * 100 + self.max_combo * 10 + (self.timer // 30)

    # ── Particles ──

    def _spawn_particles_zone(self, x: float, y: float, count: int, colors: list[int] | int) -> None:
        """Particle burst from zone collection."""
        if isinstance(colors, int):
            colors = [colors]
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.5)
            c = colors[self._rng.randint(0, len(colors) - 1)]
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 0.5,
                life=self._rng.randint(15, 30),
                color=c,
                size=self._rng.randint(1, 3),
            ))

    def _spawn_particles_push(self, x: float, y: float, count: int, color: int) -> None:
        """Particle burst from push event."""
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.0)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 0.3,
                life=self._rng.randint(10, 15),
                color=color,
                size=self._rng.randint(1, 2),
            ))

    def _spawn_particles_ring_out(self, x: float, y: float) -> None:
        """Large particle burst for ring-out."""
        for _ in range(20):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 5.0)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=self._rng.randint(20, 40),
                color=RAINBOW[self._rng.randint(0, len(RAINBOW) - 1)],
                size=self._rng.randint(1, 3),
            ))

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y -= 0.8
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    # ══════════════════════════════════════════════════
    #  Update (Pyxel input calls separated here)
    # ══════════════════════════════════════════════════

    def _update(self) -> None:
        if self.shake_frames > 0:
            self.shake_frames -= 1
            shx = self._rng.randint(-3, 3) if self.shake_frames > 0 else 0
            shy = self._rng.randint(-2, 2) if self.shake_frames > 0 else 0
            pyxel.camera(shx, shy)
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.phase = Phase.PLAYING
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.ROUND_END:
            self.round_end_timer -= 1
            if self.round_end_timer <= 0:
                self._reset_round()
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self._check_round_end()
            return

        # Super timer
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.combo = 0

        # Color cycles
        self._cycle_color()
        self._cycle_ai_color()

        # Zone spawning
        self.zone_spawn_timer -= 1
        if self.zone_spawn_timer <= 0:
            self._spawn_zone()
            self.zone_spawn_speedup_counter += 1
            if self.zone_spawn_speedup_counter >= ZONE_SPAWN_INTERVAL_PERIOD:
                self.zone_spawn_speedup_counter = 0
                self.zone_spawn_interval = max(
                    ZONE_SPAWN_INTERVAL_MIN,
                    self.zone_spawn_interval - ZONE_SPAWN_INTERVAL_DECREASE,
                )
            self.zone_spawn_timer = self.zone_spawn_interval

        # Player movement
        self._update_player_movement()

        # Zone updates
        self._update_zones()
        self._check_zone_collisions()

        # Push force
        self._update_push_force()

        # AI
        self._update_ai()

        # Push physics
        self._check_push()

        # Ring boundaries and ring-out
        self._check_ring_out()

        # HEAT
        self._update_heat()

        # Particles and texts
        self._update_particles()
        self._update_floating_texts()

        # Stun countdown
        if self.player.stunned > 0:
            self.player.stunned -= 1

    def _update_player_movement(self) -> None:
        if self.player.stunned > 0:
            self.player.vx = 0.0
            self.player.vy = 0.0
            return

        dx: float = 0.0
        dy: float = 0.0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx = -PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx = PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy = -PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy = PLAYER_SPEED

        if dx != 0 and dy != 0:
            dx *= 0.707
            dy *= 0.707

        self.player.vx = dx
        self.player.vy = dy
        self.player.x += self.player.vx
        self.player.y += self.player.vy

        # Clamp player to ring
        self._clamp_to_ring(self.player)

    def _clamp_to_ring(self, w: Wrestler) -> None:
        """Clamp a wrestler inside the ring boundary."""
        dist = math.hypot(w.x - RING_CX, w.y - RING_CY)
        if dist > RING_RADIUS - w.radius:
            angle = math.atan2(w.y - RING_CY, w.x - RING_CX)
            w.x = RING_CX + math.cos(angle) * (RING_RADIUS - w.radius)
            w.y = RING_CY + math.sin(angle) * (RING_RADIUS - w.radius)

    # ══════════════════════════════════════════════════
    #  Draw
    # ══════════════════════════════════════════════════

    def _draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_game()
            self._draw_hud()
        elif self.phase == Phase.ROUND_END:
            self._draw_game()
            self._draw_hud()
            self._draw_round_end_overlay()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_dohyo(self) -> None:
        """Draw the sumo ring (dohyo)."""
        # Base fill
        pyxel.circ(RING_CX, RING_CY, RING_RADIUS, GRAY)
        # Border
        pyxel.circb(RING_CX, RING_CY, RING_RADIUS, WHITE)
        # Outer ring
        pyxel.circb(RING_CX, RING_CY, RING_RADIUS + 3, BROWN)
        pyxel.circb(RING_CX, RING_CY, RING_RADIUS + 5, BROWN)
        # Inner center mark
        pyxel.circb(RING_CX, RING_CY, 8, LIGHT_BLUE)

        # SUPER mode: rainbow border
        if self.super_timer > 0:
            num_seg = len(RAINBOW)
            for i in range(num_seg):
                a_start = (pyxel.frame_count * 3 + i * (360 // num_seg)) % 360
                a_end = a_start + 360 // num_seg
                c = RAINBOW[i]
                for a in range(a_start, a_end, 3):
                    rad = math.radians(a)
                    px = int(RING_CX + math.cos(rad) * (RING_RADIUS + 2))
                    py = int(RING_CY + math.sin(rad) * (RING_RADIUS + 2))
                    pyxel.pset(px, py, c)

    def _draw_wrestler(self, w: Wrestler, is_player: bool) -> None:
        cx = int(w.x)
        cy = int(w.y)
        r = w.radius

        # Stun flash
        stunned_visible = w.stunned > 0 and (pyxel.frame_count // 4) % 2 == 0

        body_color = PLAYER_COLORS[w.color_idx]
        if self.super_timer > 0 and is_player:
            # Rainbow body for SUPER SUMO
            idx = (pyxel.frame_count // 6) % len(RAINBOW)
            body_color = RAINBOW[idx]

        # Glow ring in SUPER mode
        if self.super_timer > 0 and is_player:
            pyxel.circb(cx, cy, r + 3, CYAN)

        # Body
        pyxel.circ(cx, cy, r, body_color)
        if stunned_visible:
            pyxel.circb(cx, cy, r + 1, WHITE)

        # Belt / mawashi
        pyxel.tri(cx - 5, cy + r - 3, cx + 5, cy + r - 3, cx, cy + r, WHITE)

        # Face: simple eyes
        eye_y = cy - 3
        pyxel.pset(cx - 3, eye_y, WHITE)
        pyxel.pset(cx + 3, eye_y, WHITE)
        # Mouth
        pyxel.pset(cx, eye_y + 3, WHITE)

    def _draw_zones(self) -> None:
        """Draw power zones with pulsing effect."""
        pulse = int(math.sin(pyxel.frame_count * 0.2) * 1.5)
        for z in self.zones:
            r = z.radius + pulse
            alpha = z.life / ZONE_LIFE
            # Fade when about to expire
            if alpha < 0.2 and (pyxel.frame_count // 6) % 2 == 0:
                continue
            color = PLAYER_COLORS[z.color_idx]
            if z.life < 60:
                pyxel.circb(int(z.x), int(z.y), r, color)
            pyxel.circ(int(z.x), int(z.y), max(2, r), color)

    def _draw_particles_vis(self) -> None:
        for p in self.particles:
            alpha = p.life / 40.0
            c = p.color if alpha > 0.3 else GRAY
            pyxel.rect(int(p.x), int(p.y), p.size, p.size, c)

    def _draw_floating_texts_vis(self) -> None:
        for ft in self.floating_texts:
            alpha = min(1.0, ft.life / 40.0)
            c = ft.color if alpha > 0.4 else GRAY
            tw = len(ft.text) * 4
            pyxel.text(int(ft.x) - tw // 2, int(ft.y), ft.text, c)

    def _draw_hud(self) -> None:
        # Top-left: score, COMBO, max_combo
        pyxel.text(4, 2, f"SCORE:{self.score}", WHITE)
        combo_c = YELLOW if self.combo >= SUPER_THRESHOLD else (ORANGE if self.combo >= 2 else WHITE)
        pyxel.text(4, 10, f"COMBO:{self.combo}", combo_c)
        pyxel.text(4, 18, f"MAX:{self.max_combo}", GRAY)

        # Timer (top-center)
        secs = max(0, self.timer // FPS)
        t_text = f"TIME:{secs:02d}"
        tw = len(t_text) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 2, t_text, WHITE if secs > 10 else RED)

        # Round score (top-right)
        ring_text = f"P{self.player_ringouts}-{self.ai_ringouts}AI"
        rw = len(ring_text) * 4
        pyxel.text(SCREEN_W - rw - 4, 2, ring_text, WHITE)

        # SUPER timer
        if self.super_timer > 0:
            s_text = f"SUPER {self.super_timer // FPS + 1}s"
            sw = len(s_text) * 4
            pyxel.text(SCREEN_W // 2 - sw // 2, 12, s_text, LIME)

        # Color indicator (bottom-left)
        pyxel.text(4, SCREEN_H - 18, "COLOR:", WHITE)
        pyxel.rect(42, SCREEN_H - 17, 10, 10, PLAYER_COLORS[self.player.color_idx])
        pyxel.rectb(42, SCREEN_H - 17, 10, 10, WHITE)

        # HEAT bar (bottom)
        bar_w = 80
        bar_h = 6
        bar_x = SCREEN_W - bar_w - 4
        bar_y = SCREEN_H - 12
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, DARK_BLUE)
        fill = int(bar_w * (self.heat / HEAT_CAP))
        hc = RED if self.heat > 70 else (ORANGE if self.heat > 40 else YELLOW)
        pyxel.rect(bar_x, bar_y, fill, bar_h, hc)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        pyxel.text(bar_x - 26, bar_y - 1, "HEAT", RED)

        # OVERHEAT indicator
        if self.overheat_timer > 0:
            o_text = f"OVERHEAT {self.overheat_timer // FPS + 1}s"
            ow = len(o_text) * 4
            pyxel.text(SCREEN_W // 2 - ow // 2, SCREEN_H - 10, o_text, RED)

    def _draw_game(self) -> None:
        self._draw_dohyo()
        self._draw_zones()
        self._draw_wrestler(self.ai, is_player=False)
        self._draw_wrestler(self.player, is_player=True)
        self._draw_particles_vis()
        self._draw_floating_texts_vis()

    def _draw_round_end_overlay(self) -> None:
        secs = self.round_end_timer // FPS + 1
        txt = f"ROUND OVER! {secs}"
        tw = len(txt) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, SCREEN_H // 2 - 4, txt, YELLOW)

    def _draw_title(self) -> None:
        pyxel.cls(BLACK)

        title = "SUMO SURGE"
        tw = len(title) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 24, title, YELLOW)

        subtitle = "Color-Match Sumo Arena"
        sw = len(subtitle) * 4
        pyxel.text(SCREEN_W // 2 - sw // 2, 38, subtitle, GRAY)

        # Color legend
        for i, (col, name) in enumerate(zip(PLAYER_COLORS, COLOR_NAMES)):
            bx = 40 + i * 65
            pyxel.rect(bx, 50, 12, 12, col)
            pyxel.rectb(bx, 50, 12, 12, WHITE)
            nw = len(name) * 4
            pyxel.text(bx + 6 - nw // 2, 64, name, WHITE)

        lines = [
            "ARROW/WASD: Move",
            "",
            "Your color cycles every 0.67s",
            "Collect matching-color zones to",
            "  build COMBO and PUSH FORCE!",
            "Mismatch = COMBO reset + HEAT",
            "",
            f"COMBO >= {SUPER_THRESHOLD} = SUPER SUMO!",
            "  Rainbow mode, 3x force!",
            "",
            "Push opponent out of the ring!",
            f"First to {WIN_THRESHOLD} ring-outs wins!",
            "",
            "HEAT >= 100 = AI OVERHEAT BONUS",
            "",
            "SPACE to START",
        ]
        for i, ln in enumerate(lines):
            pyxel.text(50, 76 + i * 10, ln, GRAY if i < len(lines) - 2 else WHITE)

    def _draw_game_over(self) -> None:
        pyxel.cls(BLACK)

        # Determine result
        if self.player_ringouts >= WIN_THRESHOLD:
            result = "YOU WIN!"
            rc = LIME
        elif self.ai_ringouts >= WIN_THRESHOLD:
            result = "AI WINS!"
            rc = RED
        else:
            result = "TIME UP!"
            rc = YELLOW

        rw = len(result) * 4
        pyxel.text(SCREEN_W // 2 - rw // 2, 30, result, rc)

        def _ctr(y: int, text: str, color: int) -> None:
            pyxel.text(SCREEN_W // 2 - len(text) * 2, y, text, color)

        _ctr(55, f"SCORE: {self.compute_score()}", WHITE)
        _ctr(72, f"BEST: {self.best_score}", YELLOW)
        _ctr(89, f"RING-OUTS: P{self.player_ringouts}-{self.ai_ringouts}AI", ORANGE)
        _ctr(106, f"MAX COMBO: {self.max_combo}", CYAN)
        super_yes = "YES" if self.max_combo >= SUPER_THRESHOLD else "NO"
        _ctr(123, f"SUPER REACHED: {super_yes}", LIME)
        _ctr(140, f"HEAT: {int(self.heat)}", RED)
        secs = max(0, self.timer // FPS)
        _ctr(157, f"TIME LEFT: {secs}s", GRAY)

        _ctr(200, "SPACE to RETRY", WHITE)


# ── Entry Point ──


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
