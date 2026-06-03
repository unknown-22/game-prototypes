"""102_ring_surge -- Color-Match Sumo Wrestling Prototype

The most fun moment:
    相手を狙った色のゾーンに連続で押し込み、コンボが光って
    SUPER PUSHで一気に土俵外に吹き飛ばす瞬間

Core loop: Top-down sumo wrestling in a circular ring. Push opponent into
matching color zones to build COMBO. COMBO >= 4 triggers SUPER PUSH (3x force).
HEAT builds with pushing — overheat causes stagger.
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
SCREEN_W = 320
SCREEN_H = 240
RING_CX = 160.0
RING_CY = 120.0
RING_RADIUS = 100
RING_BORDER = 4

PLAYER_RADIUS = 10
PLAYER_SPEED = 1.8
PLAYER_COLOR = 6  # LIGHT_BLUE
PLAYER_OUTLINE = 7  # WHITE

OPPONENT_RADIUS = 12
OPPONENT_SPEED_BASE = 1.2
OPPONENT_SPEED_PER_ROUND = 0.15
OPPONENT_COLOR = 8  # RED
OPPONENT_OUTLINE = 7  # WHITE

ZONE_ANGLE = 80
ZONE_OFFSET = 5
ZONE_THICKNESS = 8

SUPER_COMBO = 4
SUPER_DURATION = 5 * 30  # 5 seconds at 30fps
SUPER_FORCE_MULT = 3.0

PUSH_FORCE = 2.5
HEAT_PER_PUSH = 2.0
HEAT_PER_MISMATCH = 8.0
HEAT_DECAY = 0.05  # per frame when not pushing
MAX_HEAT = 100.0
OVERHEAT_DURATION = 45  # 1.5 seconds at 30fps
OVERHEAT_BURST = 10  # particles on overheat

RING_OUT_SCORE = 100
COMBO_BONUS_MULT = 25

SHAKE_FRAMES = 5
RING_OUT_TIMER = 45  # 1.5 seconds celebration

# pyxel palette ints
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

ZONE_COLORS = (RED, GREEN, DARK_BLUE, YELLOW)
RAINBOW_COLORS = (RED, GREEN, DARK_BLUE, YELLOW)
COMBO_COLORS = (WHITE, ORANGE, YELLOW, YELLOW)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    RING_OUT = auto()
    GAME_OVER = auto()


class ZoneColor(Enum):
    RED = 0
    GREEN = 1
    DARK_BLUE = 2
    YELLOW = 3


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class Wrestler:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    radius: int = PLAYER_RADIUS
    color: int = PLAYER_COLOR


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    max_life: int
    color: int


@dataclass
class ColorZone:
    angle_start: int  # degrees
    angle_end: int    # degrees
    color: int        # pyxel color int


# ---------------------------------------------------------------------------
# Game class
# ---------------------------------------------------------------------------
class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Ring Surge")
        self._rng = random.Random()
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.max_combo: int = 0
        self.combo: int = 0
        self.round_num: int = 1
        self.prev_zone_color: int | None = None
        self.super_push_timer: int = 0
        self.heat: float = 0.0
        self.overheat_timer: int = 0
        self.player: Wrestler = Wrestler(x=RING_CX, y=RING_CY - 60, radius=PLAYER_RADIUS, color=PLAYER_COLOR)
        self.opponent: Wrestler = Wrestler(x=RING_CX, y=RING_CY + 60, radius=OPPONENT_RADIUS, color=OPPONENT_COLOR)
        self.particles: list[Particle] = []
        self.ring_out_timer: int = 0
        self.shake_frames: int = 0
        self.player_pushing: bool = False
        self.color_zones: list[ColorZone] = []
        self._init_zones()
        self.reset()
        pyxel.run(self._update, self._draw)

    def _init_zones(self) -> None:
        self.color_zones = []
        colors = [RED, GREEN, DARK_BLUE, YELLOW]
        for i in range(4):
            start = ZONE_OFFSET + i * 90
            end = start + ZONE_ANGLE
            self.color_zones.append(ColorZone(angle_start=start, angle_end=end, color=colors[i]))

    # -------------------------------------------------------------------
    # Testable logic methods (no Pyxel input)
    # -------------------------------------------------------------------

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.max_combo = 0
        self.combo = 0
        self.round_num = 1
        self.prev_zone_color = None
        self.super_push_timer = 0
        self.heat = 0.0
        self.overheat_timer = 0
        self.ring_out_timer = 0
        self.shake_frames = 0
        self.player_pushing = False
        self.particles.clear()
        self._place_wrestlers()

    def _place_wrestlers(self) -> None:
        self.player.x = RING_CX
        self.player.y = RING_CY - 60
        self.player.vx = 0.0
        self.player.vy = 0.0
        self.opponent.x = RING_CX
        self.opponent.y = RING_CY + 60
        self.opponent.vx = 0.0
        self.opponent.vy = 0.0

    def _angle_from_center(self, x: float, y: float) -> float:
        dx = x - RING_CX
        dy = y - RING_CY
        angle = math.degrees(math.atan2(-dy, dx))  # negate y for screen coords
        return angle % 360.0

    def _dist_from_center(self, x: float, y: float) -> float:
        return math.hypot(x - RING_CX, y - RING_CY)

    def _is_at_edge(self, x: float, y: float, radius: int) -> bool:
        dist = self._dist_from_center(x, y)
        return dist + radius >= RING_RADIUS

    def _is_outside(self, x: float, y: float, radius: int) -> bool:
        dist = self._dist_from_center(x, y)
        return dist + radius > RING_RADIUS + 10  # clear margin

    def _color_zone_at_angle(self, angle_deg: float) -> int | None:
        for zone in self.color_zones:
            if zone.angle_start <= angle_deg <= zone.angle_end:
                return zone.color
        # Check wrap-around for the last zone
        last = self.color_zones[3]
        if last.angle_start > last.angle_end:
            if angle_deg >= last.angle_start or angle_deg <= last.angle_end:
                return last.color
        return None

    def _clamp_to_ring(self, w: Wrestler) -> None:
        dist = self._dist_from_center(w.x, w.y)
        max_dist = RING_RADIUS - w.radius
        if dist > max_dist and dist > 0:
            factor = max_dist / dist
            w.x = RING_CX + (w.x - RING_CX) * factor
            w.y = RING_CY + (w.y - RING_CY) * factor

    def _move_wrestler(self, w: Wrestler, dx: float, dy: float) -> None:
        if dx == 0 and dy == 0:
            return
        # Normalize and scale by speed
        length = math.hypot(dx, dy)
        norm_dx = dx / length
        norm_dy = dy / length
        speed = PLAYER_SPEED if w is self.player else self._opponent_speed()
        w.x += norm_dx * speed
        w.y += norm_dy * speed
        w.vx = norm_dx * speed
        w.vy = norm_dy * speed
        self._clamp_to_ring(w)

    def _opponent_speed(self) -> float:
        return OPPONENT_SPEED_BASE + (self.round_num - 1) * OPPONENT_SPEED_PER_ROUND

    def _push_opponent(self, player_dx: float, player_dy: float) -> None:
        if self.overheat_timer > 0:
            return
        if player_dx == 0 and player_dy == 0:
            self.player_pushing = False
            return

        length = math.hypot(player_dx, player_dy)
        norm_dx = player_dx / length
        norm_dy = player_dy / length

        # Check collision: distance between centers <= sum of radii
        dist = math.hypot(self.opponent.x - self.player.x, self.opponent.y - self.player.y)
        min_dist = self.player.radius + self.opponent.radius
        if dist <= min_dist:
            self.player_pushing = True
            force = PUSH_FORCE
            if self._is_super():
                force *= SUPER_FORCE_MULT
            self.opponent.x += norm_dx * force
            self.opponent.y += norm_dy * force
            self._clamp_to_ring(self.opponent)
        else:
            self.player_pushing = False

    def _is_super(self) -> bool:
        return self.super_push_timer > 0

    def _check_strike(self) -> None:
        # Check both wrestlers at ring edge
        for w, is_player in [(self.opponent, False), (self.player, True)]:
            if self._is_at_edge(w.x, w.y, w.radius):
                angle = self._angle_from_center(w.x, w.y)
                zone_color = self._color_zone_at_angle(angle)
                if zone_color is not None:
                    if is_player:
                        # Player touching edge — opponent wins, game over
                        self._ring_out_player()
                        return
                    else:
                        self._handle_opponent_strike(zone_color)

    def _handle_opponent_strike(self, zone_color: int) -> None:
        if self.prev_zone_color is not None and zone_color == self.prev_zone_color:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            self._spawn_particles(self.opponent.x, self.opponent.y, zone_color, 5 * self.combo)
            if self.combo >= SUPER_COMBO:
                self.super_push_timer = SUPER_DURATION
        else:
            self.combo = 0
            self.heat += HEAT_PER_MISMATCH
            if self.heat > MAX_HEAT:
                self.heat = MAX_HEAT
        self.prev_zone_color = zone_color
        self.heat = min(self.heat + HEAT_PER_PUSH, MAX_HEAT)
        if self.heat >= MAX_HEAT and self.overheat_timer == 0:
            self.overheat_timer = OVERHEAT_DURATION
            self._spawn_particles(self.player.x, self.player.y, ORANGE, OVERHEAT_BURST)

    def _update_opponent_ai(self) -> None:
        # Move opponent toward player
        dx = self.player.x - self.opponent.x
        dy = self.player.y - self.opponent.y
        dist = math.hypot(dx, dy)
        if dist < 1:
            return
        speed = self._opponent_speed()
        # AI: try to push player toward a different-color zone
        # Add randomness based on round
        jitter = (self.round_num - 1) * 0.3
        rx = (self._rng.random() - 0.5) * jitter * 2
        ry = (self._rng.random() - 0.5) * jitter * 2
        norm_dx = (dx + rx) / (dist + 0.001)
        norm_dy = (dy + ry) / (dist + 0.001)
        self.opponent.x += norm_dx * speed
        self.opponent.y += norm_dy * speed
        self.opponent.vx = norm_dx * speed
        self.opponent.vy = norm_dy * speed
        self._clamp_to_ring(self.opponent)

        # Opponent pushing player
        pdist = math.hypot(self.player.x - self.opponent.x, self.player.y - self.opponent.y)
        min_dist = self.player.radius + self.opponent.radius
        if pdist <= min_dist:
            push_force = PUSH_FORCE * 0.8
            px = self.player.x - self.opponent.x
            py = self.player.y - self.opponent.y
            plen = math.hypot(px, py) + 0.001
            self.player.x += (px / plen) * push_force
            self.player.y += (py / plen) * push_force
            self._clamp_to_ring(self.player)

    def _update_particles(self) -> None:
        new_particles: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05  # gravity
            p.life -= 1
            if p.life > 0:
                new_particles.append(p)
        self.particles = new_particles

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-2.0, 2.0)
            vy = self._rng.uniform(-2.0, 2.0)
            life = self._rng.randint(20, 40)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, max_life=life, color=color))

    def _update_super_push(self) -> None:
        if self.super_push_timer > 0:
            self.super_push_timer -= 1
            # Spawn rainbow particles during super
            if self.super_push_timer % 5 == 0:
                rc = RAINBOW_COLORS[self.super_push_timer % len(RAINBOW_COLORS)]
                self._spawn_particles(self.player.x, self.player.y, rc, 2)

    def _update_overheat(self) -> None:
        if self.overheat_timer > 0:
            self.overheat_timer -= 1
            if self.overheat_timer == 0:
                self.heat = 0.0
        elif not self.player_pushing:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _ring_out_opponent(self) -> None:
        angle = self._angle_from_center(self.opponent.x, self.opponent.y)
        zone_color = self._color_zone_at_angle(angle)
        particle_color = zone_color if zone_color is not None else WHITE
        self._spawn_particles(self.opponent.x, self.opponent.y, particle_color, 20)
        combo_bonus = self.combo * COMBO_BONUS_MULT
        self.score += RING_OUT_SCORE + combo_bonus
        self.combo = 0
        self.prev_zone_color = None
        self.heat = 0.0
        self.super_push_timer = 0
        self.overheat_timer = 0
        self.round_num += 1
        self.ring_out_timer = RING_OUT_TIMER
        self.shake_frames = SHAKE_FRAMES
        self.phase = Phase.RING_OUT

    def _ring_out_player(self) -> None:
        self._spawn_particles(self.player.x, self.player.y, PLAYER_COLOR, 20)
        self.shake_frames = SHAKE_FRAMES
        self.phase = Phase.GAME_OVER

    def _advance_round(self) -> None:
        self.ring_out_timer -= 1
        if self.ring_out_timer <= 0:
            self._place_wrestlers()
            self.phase = Phase.PLAYING

    # -------------------------------------------------------------------
    # Update (with Pyxel input)
    # -------------------------------------------------------------------

    def _update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.PLAYING
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.TITLE
            return

        if self.phase == Phase.RING_OUT:
            if self.shake_frames > 0:
                self.shake_frames -= 1
            self._update_particles()
            self._advance_round()
            return

        # PLAYING
        if self.shake_frames > 0:
            self.shake_frames -= 1

        # Input
        dx = 0.0
        dy = 0.0
        if self.overheat_timer == 0:
            if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
                dx -= 1
            if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
                dx += 1
            if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
                dy -= 1
            if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
                dy += 1

        # Move player
        if dx != 0 or dy != 0:
            self._move_wrestler(self.player, dx, dy)

        # Push opponent
        self._push_opponent(dx, dy)

        # Check outside
        if self._is_outside(self.opponent.x, self.opponent.y, self.opponent.radius):
            self._ring_out_opponent()
            return
        if self._is_outside(self.player.x, self.player.y, self.player.radius):
            self._ring_out_player()
            return

        # Check strike (ring edge contact)
        self._check_strike()

        # Update opponent AI
        self._update_opponent_ai()

        # Check outside again after AI movement
        if self._is_outside(self.opponent.x, self.opponent.y, self.opponent.radius):
            self._ring_out_opponent()
            return
        if self._is_outside(self.player.x, self.player.y, self.player.radius):
            self._ring_out_player()
            return

        # Update systems
        self._update_super_push()
        self._update_overheat()
        self._update_particles()

    # -------------------------------------------------------------------
    # Draw
    # -------------------------------------------------------------------

    def _draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()
            return

        self._draw_game()

    def _draw_title(self) -> None:
        title = "RING SURGE"
        tw = len(title) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 40, title, YELLOW)

        subtitle = "Color-Match Sumo Wrestling"
        sw = len(subtitle) * 4
        pyxel.text(SCREEN_W // 2 - sw // 2, 55, subtitle, WHITE)

        lines = [
            "ARROW KEYS / WASD: Move & Push",
            "Push opponent into same-color zone",
            "to build COMBO chain!",
            "COMBO x4 = SUPER PUSH (3x force!)",
            "Different color = COMBO reset + HEAT",
            "HEAT 100% = OVERHEAT (stagger)",
            "",
            "Press SPACE or ENTER to start",
        ]
        for i, line in enumerate(lines):
            lw = len(line) * 4
            pyxel.text(SCREEN_W // 2 - lw // 2, 90 + i * 14, line, GRAY)

    def _draw_game(self) -> None:
        # Screen shake offset
        sx = 0
        sy = 0
        if self.shake_frames > 0:
            sx = self._rng.randint(-3, 3)
            sy = self._rng.randint(-3, 3)

        # Ring
        pyxel.clip()
        for i in range(RING_BORDER):
            pyxel.circb(int(RING_CX + sx), int(RING_CY + sy), RING_RADIUS + i, WHITE)

        # Color zones on ring circumference
        for zone in self.color_zones:
            a1 = math.radians(zone.angle_start)
            a2 = math.radians(zone.angle_end)
            steps = max(int((a2 - a1) / 0.05), 2)
            for i in range(steps + 1):
                frac = i / max(steps, 1)
                angle = a1 + frac * (a2 - a1)
                for t in range(ZONE_THICKNESS):
                    r = RING_RADIUS - t
                    px = RING_CX + sx + math.cos(angle) * r
                    py_ = RING_CY + sy - math.sin(angle) * r
                    pyxel.pset(int(px), int(py_), zone.color)

        # Draw line from center to current combo zone indicator
        if self.prev_zone_color is not None and self.combo > 0:
            match_zone = None
            for zone in self.color_zones:
                if zone.color == self.prev_zone_color:
                    match_zone = zone
                    break
            if match_zone is not None:
                ma = math.radians((match_zone.angle_start + match_zone.angle_end) / 2)
                mx = RING_CX + sx + math.cos(ma) * (RING_RADIUS - ZONE_THICKNESS)
                my = RING_CY + sy - math.sin(ma) * (RING_RADIUS - ZONE_THICKNESS)
                pyxel.line(int(RING_CX + sx), int(RING_CY + sy), int(mx), int(my), match_zone.color)

        # Opponent
        if self.phase != Phase.RING_OUT:
            ocx = int(self.opponent.x + sx)
            ocy = int(self.opponent.y + sy)
            pyxel.circ(ocx + 1, ocy + 1, self.opponent.radius, BLACK)
            pyxel.circ(ocx, ocy, self.opponent.radius, self.opponent.color)
            pyxel.circb(ocx, ocy, self.opponent.radius, OPPONENT_OUTLINE)

        # Player
        pcx = int(self.player.x + sx)
        pcy = int(self.player.y + sy)
        if self._is_super():
            flash_idx = (pyxel.frame_count // 8) % len(RAINBOW_COLORS)
            pcol = RAINBOW_COLORS[flash_idx]
        elif self.overheat_timer > 0:
            pcol = ORANGE
        else:
            pcol = self.player.color
        pyxel.circ(pcx + 1, pcy + 1, self.player.radius, BLACK)
        pyxel.circ(pcx, pcy, self.player.radius, pcol)
        pyxel.circb(pcx, pcy, self.player.radius, PLAYER_OUTLINE)

        # Overheat stagger animation
        if self.overheat_timer > 0 and self.overheat_timer % 6 < 3:
            pyxel.circb(pcx, pcy, self.player.radius + 4, ORANGE)

        # Particles
        for p in self.particles:
            alpha = p.life / max(p.max_life, 1)
            c = p.color if alpha > 0.3 else GRAY
            pyxel.pset(int(p.x + sx), int(p.y + sy), c)

        # --- UI ---
        # Score top-left
        pyxel.text(4, 2, f"SCORE:{self.score}", WHITE)

        # Round top-right
        rtext = f"ROUND:{self.round_num}"
        rw = len(rtext) * 4
        pyxel.text(SCREEN_W - rw - 4, 2, rtext, WHITE)

        # COMBO top-center
        if self.combo > 0:
            ctext = f"COMBO x{self.combo}"
            cw = len(ctext) * 4
            cc = COMBO_COLORS[min(self.combo, len(COMBO_COLORS) - 1)]
            if self._is_super():
                cc = YELLOW
            pyxel.text(SCREEN_W // 2 - cw // 2, 2, ctext, cc)

        # SUPER PUSH indicator
        if self._is_super():
            stext = "SUPER!"
            sw_super = len(stext) * 4
            sc = RAINBOW_COLORS[(pyxel.frame_count // 8) % len(RAINBOW_COLORS)]
            pyxel.text(int(self.player.x + sx) - sw_super // 2, int(self.player.y + sy) - self.player.radius - 10, stext, sc)

        # HEAT bar bottom-left
        bar_x = 4
        bar_y = SCREEN_H - 10
        bar_w = 80
        bar_h = 6
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, DARK_BLUE)
        fill_w = int(bar_w * self.heat / MAX_HEAT)
        if self.heat >= MAX_HEAT:
            hc = RED
        elif self.heat >= 60:
            hc = ORANGE
        elif self.heat >= 30:
            hc = YELLOW
        else:
            hc = GREEN
        pyxel.rect(bar_x, bar_y, fill_w, bar_h, hc)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        pyxel.text(bar_x + bar_w + 4, bar_y - 1, "HEAT", GRAY)

        # Max combo display
        mtext = f"BEST:{self.max_combo}"
        pyxel.text(SCREEN_W - len(mtext) * 4 - 4, SCREEN_H - 10, mtext, GRAY)

        # Ring-out celebration overlay
        if self.phase == Phase.RING_OUT:
            rtext2 = "RING OUT!"
            rw2 = len(rtext2) * 4
            pyxel.text(SCREEN_W // 2 - rw2 // 2, SCREEN_H // 2 - 4, rtext2, YELLOW)
            btext = f"+{RING_OUT_SCORE + self.max_combo * COMBO_BONUS_MULT}"
            bw = len(btext) * 4
            pyxel.text(SCREEN_W // 2 - bw // 2, SCREEN_H // 2 + 10, btext, GREEN)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 20, 50, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 30, 85, f"SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 45, 100, f"MAX COMBO: {self.max_combo}", ORANGE)
        pyxel.text(SCREEN_W // 2 - 45, 115, f"REACHED: ROUND {self.round_num}", GRAY)
        super_str = "YES" if self.max_combo >= SUPER_COMBO else "NO"
        pyxel.text(SCREEN_W // 2 - 45, 130, f"SUPER PUSH: {super_str}", YELLOW)
        pyxel.text(SCREEN_W // 2 - 55, 170, "SPACE or ENTER: Retry", GRAY)


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
def main() -> None:
    Game()


if __name__ == "__main__":
    main()
