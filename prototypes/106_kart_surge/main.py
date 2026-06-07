import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# --- Constants ---
SCREEN_W = 320
SCREEN_H = 240

# Pad colors (pyxel color ints)
COLOR_RED = 8
COLOR_GREEN = 3
COLOR_DARK_BLUE = 5
COLOR_YELLOW = 10
PAD_COLORS = (COLOR_RED, COLOR_GREEN, COLOR_DARK_BLUE, COLOR_YELLOW)

KART_RADIUS = 6
PAD_RADIUS = 5
MAX_SPEED = 3.0
ACCEL = 0.15
BRAKE = 0.1
FRICTION = 0.98
TURN_SPEED = 0.08
LAP_COUNT = 3
SURGE_DURATION = 300
COMBO_FOR_SURGE = 5
PAD_RESPAWN_TIME = 90
PAD_COUNT = 16
PARTICLE_COUNT_ON_COLLECT = 5
PARTICLE_COUNT_ON_SURGE = 12
PARTICLE_LIFE = 20

# Track bounds
TRACK_LEFT = 40
TRACK_TOP = 40
TRACK_RIGHT = 280
TRACK_BOTTOM = 200
INFIELD_LEFT = 85
INFIELD_TOP = 85
INFIELD_RIGHT = 235
INFIELD_BOTTOM = 155


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class BoostPad:
    x: float
    y: float
    color: int
    active: bool = True
    respawn_timer: int = 0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class GhostPoint:
    x: float
    y: float


class Game:
    def __init__(self) -> None:
        self._rng: random.Random
        self.phase: Phase
        self.player_x: float
        self.player_y: float
        self.player_angle: float
        self.player_speed: float
        self.combo: int
        self.max_combo: int
        self.score: int
        self.surge_timer: int
        self.lap: int
        self.lap_start_frame: int
        self.best_lap_time: int
        self.frame: int
        self.finish_crossed: bool
        self.pads: list[BoostPad]
        self.particles: list[Particle]
        self.ghost: list[GhostPoint]
        self.recording: list[GhostPoint]
        self.last_pad_color: int | None
        self.reset()
        pyxel.init(SCREEN_W, SCREEN_H, title="KART SURGE", display_scale=2)
        pyxel.run(self.update, self.draw)

    # ---- Reset & Spawn ----

    def reset(self) -> None:
        self._rng = random.Random()
        self.phase = Phase.TITLE
        self.player_x = 160.0
        self.player_y = 120.0
        self.player_angle = 0.0
        self.player_speed = 0.0
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.surge_timer = 0
        self.lap = 1
        self.lap_start_frame = 0
        self.best_lap_time = 99999
        self.frame = 0
        self.finish_crossed = False
        self.pads = []
        self.particles = []
        self.ghost = []
        self.recording = []
        self.last_pad_color = None
        self._spawn_pads()

    def _spawn_pads(self) -> None:
        self.pads.clear()
        colors = list(PAD_COLORS) * (PAD_COUNT // len(PAD_COLORS))
        self._rng.shuffle(colors)
        placed = []
        for color in colors:
            for _ in range(200):
                x = self._rng.uniform(TRACK_LEFT + 10, TRACK_RIGHT - 10)
                y = self._rng.uniform(TRACK_TOP + 10, TRACK_BOTTOM - 10)
                if INFIELD_LEFT <= x <= INFIELD_RIGHT and INFIELD_TOP <= y <= INFIELD_BOTTOM:
                    continue
                too_close = any(
                    math.hypot(x - px, y - py) < 30 for px, py in placed
                )
                if not too_close:
                    placed.append((x, y))
                    self.pads.append(BoostPad(x=x, y=y, color=color))
                    break

    # ---- Update ----

    def update(self) -> None:
        self.frame += 1
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self.phase = Phase.PLAYING
                self.lap_start_frame = self.frame
            return
        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
            return

        self._update_input()
        self._update_physics()
        self._check_pad_collisions()
        self._update_surge()
        self._update_particles()
        self._update_pad_respawns()
        self._record_ghost()
        self._check_lap()

    def _update_input(self) -> None:
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            self.player_speed += ACCEL
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            self.player_speed -= BRAKE
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            self.player_angle -= TURN_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            self.player_angle += TURN_SPEED

        surge_mult = 1.5 if self.surge_timer > 0 else 1.0
        max_spd = MAX_SPEED * surge_mult
        if self.player_speed > max_spd:
            self.player_speed = max_spd
        if self.player_speed < -max_spd * 0.5:
            self.player_speed = -max_spd * 0.5

    def _update_physics(self) -> None:
        self.player_x += math.cos(self.player_angle) * self.player_speed
        self.player_y += math.sin(self.player_angle) * self.player_speed
        self.player_speed *= FRICTION

        # Outer boundary clamp
        margin = TRACK_LEFT + KART_RADIUS
        self.player_x = max(margin, min(TRACK_RIGHT - KART_RADIUS, self.player_x))
        self.player_y = max(TRACK_TOP + KART_RADIUS, min(TRACK_BOTTOM - KART_RADIUS, self.player_y))

        # Infield collision (AABB)
        if self.player_x - KART_RADIUS < INFIELD_RIGHT and self.player_x + KART_RADIUS > INFIELD_LEFT and \
           self.player_y - KART_RADIUS < INFIELD_BOTTOM and self.player_y + KART_RADIUS > INFIELD_TOP:
            # Push to nearest edge
            cx = self.player_x
            cy = self.player_y
            r = KART_RADIUS

            # Distances to each edge of infield
            d_left = cx + r - INFIELD_LEFT
            d_right = INFIELD_RIGHT - (cx - r)
            d_top = cy + r - INFIELD_TOP
            d_bottom = INFIELD_BOTTOM - (cy - r)

            min_d = min(d_left, d_right, d_top, d_bottom)
            if min_d == d_left:
                self.player_x = INFIELD_LEFT - r
            elif min_d == d_right:
                self.player_x = INFIELD_RIGHT + r
            elif min_d == d_top:
                self.player_y = INFIELD_TOP - r
            else:
                self.player_y = INFIELD_BOTTOM + r

    def _check_pad_collisions(self) -> None:
        for pad in self.pads:
            if not pad.active:
                continue
            dist = math.hypot(self.player_x - pad.x, self.player_y - pad.y)
            if dist < KART_RADIUS + PAD_RADIUS:
                self._collect_pad(pad)

    def _collect_pad(self, pad: BoostPad) -> None:
        # Combo logic
        if self.last_pad_color is not None and pad.color == self.last_pad_color:
            self.combo += 1
        else:
            self.combo = 1
        self.last_pad_color = pad.color
        if self.combo > self.max_combo:
            self.max_combo = self.combo

        # Surge activation
        if self.combo >= COMBO_FOR_SURGE and self.surge_timer == 0:
            self.surge_timer = SURGE_DURATION
            self._spawn_particles(self.player_x, self.player_y, pad.color,
                                  PARTICLE_COUNT_ON_SURGE, surge=True)
        if self.surge_timer > 0:
            self.surge_timer = SURGE_DURATION  # refresh during surge

        # Scoring
        points = 10 * self.combo
        if self.surge_timer > 0:
            points *= 3
        self.score += points

        # Deactivate pad
        pad.active = False
        pad.respawn_timer = PAD_RESPAWN_TIME

        # Spawn collection particles
        self._spawn_particles(pad.x, pad.y, pad.color, PARTICLE_COUNT_ON_COLLECT)

    def _spawn_particles(self, x: float, y: float, color: int, count: int, surge: bool = False) -> None:
        for i in range(count):
            if surge:
                c = PAD_COLORS[i % len(PAD_COLORS)]
            else:
                c = color
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(0.5, 2.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=PARTICLE_LIFE, color=c))

    def _update_surge(self) -> None:
        if self.surge_timer > 0:
            self.surge_timer -= 1

    def _update_particles(self) -> None:
        alive = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def _update_pad_respawns(self) -> None:
        for pad in self.pads:
            if not pad.active:
                pad.respawn_timer -= 1
                if pad.respawn_timer <= 0:
                    pad.active = True
                    pad.respawn_timer = 0

    def _record_ghost(self) -> None:
        if self.frame % 3 == 0:
            self.recording.append(GhostPoint(x=self.player_x, y=self.player_y))

    def _check_lap(self) -> None:
        # Finish line: y=155, x between 100 and 220
        FINISH_Y = 155
        FINISH_X1 = 100
        FINISH_X2 = 220
        # Check if kart crosses finish line going right (angle near 0)
        on_line = (FINISH_Y - 4 <= self.player_y <= FINISH_Y + 4 and
                   FINISH_X1 <= self.player_x <= FINISH_X2)

        if on_line and not self.finish_crossed:
            self.finish_crossed = True
            lap_time = self.frame - self.lap_start_frame
            if lap_time < self.best_lap_time:
                self.best_lap_time = lap_time
                self.ghost = list(self.recording)
                self.score += self._best_lap_bonus()
            else:
                self.score += self._best_lap_bonus()

            self.lap += 1
            if self.lap > LAP_COUNT:
                self.phase = Phase.GAME_OVER
                return

            self.lap_start_frame = self.frame
            self.recording.clear()
            self._spawn_pads()
            self.last_pad_color = None
            self.combo = 0
            self.surge_timer = 0

        if not on_line:
            self.finish_crossed = False

    def _best_lap_bonus(self) -> int:
        if self.best_lap_time <= 0:
            return 100
        return max(50, int(600 / max(1, self.best_lap_time) * 100))

    # ---- Draw ----

    def draw(self) -> None:
        pyxel.cls(0)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_track()
            self._draw_ghost()
            self._draw_pads()
            self._draw_kart()
            self._draw_particles()
            self._draw_hud()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.cls(5)
        pyxel.text(SCREEN_W // 2 - 40, SCREEN_H // 2 - 30, "KART SURGE", 7)
        pyxel.text(SCREEN_W // 2 - 55, SCREEN_H // 2 - 8, "Press ENTER to start", 7)
        # Draw a small kart illustration
        cx = SCREEN_W // 2
        cy = SCREEN_H // 2 + 30
        pyxel.circ(cx, cy, KART_RADIUS, 7)
        pyxel.line(cx, cy, cx + 15, cy, 7)

    def _draw_track(self) -> None:
        pyxel.cls(3)  # Green background
        pyxel.rect(TRACK_LEFT, TRACK_TOP, TRACK_RIGHT - TRACK_LEFT, TRACK_BOTTOM - TRACK_TOP, 13)  # Road
        pyxel.rect(INFIELD_LEFT, INFIELD_TOP, INFIELD_RIGHT - INFIELD_LEFT, INFIELD_BOTTOM - INFIELD_TOP, 3)  # Infield
        # Track border
        pyxel.rectb(TRACK_LEFT, TRACK_TOP, TRACK_RIGHT - TRACK_LEFT, TRACK_BOTTOM - TRACK_TOP, 7)
        pyxel.rectb(INFIELD_LEFT, INFIELD_TOP, INFIELD_RIGHT - INFIELD_LEFT, INFIELD_BOTTOM - INFIELD_TOP, 7)
        # Finish line
        pyxel.line(100, 155, 220, 155, 7)

    def _draw_ghost(self) -> None:
        if not self.ghost:
            return
        lap_elapsed = self.frame - self.lap_start_frame
        idx = lap_elapsed // 3
        if idx < len(self.ghost):
            gp = self.ghost[idx]
            pyxel.circ(int(gp.x), int(gp.y), 3, 6)

    def _draw_pads(self) -> None:
        for pad in self.pads:
            if pad.active:
                c = pad.color
            else:
                c = pad.color + 8 if pad.color + 8 <= 15 else 0
            pyxel.circ(int(pad.x), int(pad.y), PAD_RADIUS, c)

    def _draw_kart(self) -> None:
        px = int(self.player_x)
        py = int(self.player_y)

        if self.surge_timer > 0:
            # Rainbow outline
            for i, c in enumerate(PAD_COLORS):
                angle = self.frame * 0.1 + i * (math.pi / 2)
                ox = int(math.cos(angle) * 2)
                oy = int(math.sin(angle) * 2)
                pyxel.circ(px + ox, py + oy, KART_RADIUS, c)
            body_color = 7
        else:
            body_color = self.last_pad_color if self.last_pad_color is not None else 7

        pyxel.circ(px, py, KART_RADIUS, body_color)
        # Direction indicator
        dx = int(math.cos(self.player_angle) * (KART_RADIUS + 4))
        dy = int(math.sin(self.player_angle) * (KART_RADIUS + 4))
        pyxel.line(px, py, px + dx, py + dy, 0)

    def _draw_particles(self) -> None:
        for p in self.particles:
            r = max(1, p.life // 4)
            pyxel.circ(int(p.x), int(p.y), r, p.color)

    def _draw_hud(self) -> None:
        # Score top-left
        pyxel.text(4, 2, f"SCORE: {self.score}", 7)

        # Combo top-center
        if self.combo > 0:
            combo_color = self.last_pad_color if self.last_pad_color is not None else 7
            pyxel.text(SCREEN_W // 2 - 25, 2, f"COMBO x{self.combo}", combo_color)

        # Lap top-right
        pyxel.text(SCREEN_W - 55, 2, f"LAP {min(self.lap, LAP_COUNT)}/{LAP_COUNT}", 7)

        # Surge bar
        if self.surge_timer > 0:
            bar_w = 60
            bar_h = 4
            bx = SCREEN_W // 2 - bar_w // 2
            by = 12
            fill = int(bar_w * self.surge_timer / SURGE_DURATION)
            pyxel.rect(bx, by, bar_w, bar_h, 0)
            for i in range(fill):
                c = PAD_COLORS[(i * len(PAD_COLORS)) // bar_w % len(PAD_COLORS)]
                pyxel.line(bx + i, by, bx + i, by + bar_h - 1, c)

        # Speed bottom-left
        speed_pct = int(abs(self.player_speed) / MAX_SPEED * 100)
        pyxel.text(4, SCREEN_H - 10, f"SPD: {speed_pct}%", 7)

    def _draw_game_over(self) -> None:
        pyxel.cls(5)
        pyxel.text(SCREEN_W // 2 - 48, SCREEN_H // 2 - 40, "RACE COMPLETE!", 7)
        pyxel.text(SCREEN_W // 2 - 50, SCREEN_H // 2 - 16, f"Final Score: {self.score}", 7)
        pyxel.text(SCREEN_W // 2 - 50, SCREEN_H // 2 + 0, f"Best Lap: {self.best_lap_time} frames", 7)
        pyxel.text(SCREEN_W // 2 - 50, SCREEN_H // 2 + 16, f"Max Combo: {self.max_combo}", 7)
        pyxel.text(SCREEN_W // 2 - 50, SCREEN_H // 2 + 36, "Press R to restart", 7)


if __name__ == "__main__":
    Game()
