from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import pyxel


# ── Constants ──────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
PLAYER_RADIUS = 6
FALL_SPEED_FREEFALL = 1.5
FALL_SPEED_CHUTE = 0.8
VX_MAX_FREEFALL = 2.5
VX_MAX_CHUTE = 4.0
RING_MIN_RADIUS = 8
RING_MAX_RADIUS = 12
MAX_RINGS = 12
HEAT_MAX = 100.0
HEAT_WRONG = 15.0
HEAT_MISS = 5.0
HEAT_DECAY = 0.5 / 60.0
SUPER_DURATION = 300
SUPER_MULTIPLIER = 3
SUPER_RING_RADIUS_MULT = 2.0
COMBO_THRESHOLD = 4
TIMER_MAX = 3600
ALTITUDE_START = 5000.0
ALTITUDE_PER_FRAME = ALTITUDE_START / TIMER_MAX
GROUND_Y = 210
LANDING_SCORE = 500

COLOR_NAMES: list[str] = ["RED", "GREEN", "BLUE", "GOLD"]
COLOR_VALS: tuple[int, int, int, int] = (8, 3, 5, 10)


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Ring:
    x: float
    y: float
    color: int
    radius: float
    vy: float = 1.0
    collected: bool = False


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    max_life: int = 20


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


@dataclass
class WindLine:
    x: float
    y: float
    length: float
    speed: float
    life: int
    alpha: int = 7


class Game:
    """Chute Chain — Parachute Skydiving Color-Match COMBO Game."""

    best_score: ClassVar[int] = 0

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CHUTE CHAIN", display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.player_x: float = 160.0
        self.player_y: float = 30.0
        self.player_vx: float = 0.0
        self.player_vy: float = 1.5
        self.parachute_deployed: bool = False
        self.rings: list[Ring] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.wind_lines: list[WindLine] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.super_timer: int = 0
        self.timer: int = TIMER_MAX
        self.altitude: float = ALTITUDE_START
        self.bg_offset: float = 0.0
        self.rng = random.Random()
        self.ring_timer: int = 0
        self.landing_x: float = 160.0
        self.shake_frames: int = 0
        self.wind_dir: float = 0.0
        self.wind_timer: int = 0
        self.last_color: int | None = None
        self.heat_warning_timer: int = 0
        self._spawn_ring_cooldown: int = 60

    # ── Input ─────────────────────────────────────────────

    def _handle_input(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self._start_game()
            return

        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self._start_game()
            return

        # Playing input
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            self.player_vx -= 0.6
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            self.player_vx += 0.6

        if pyxel.btnp(pyxel.KEY_SPACE):
            self.parachute_deployed = not self.parachute_deployed
            if self.parachute_deployed:
                self.player_vy = FALL_SPEED_CHUTE
            else:
                self.player_vy = FALL_SPEED_FREEFALL

    # ── Phase transitions ─────────────────────────────────

    def _start_game(self) -> None:
        self.phase = Phase.PLAYING
        self.player_x = 160.0
        self.player_y = 30.0
        self.player_vx = 0.0
        self.player_vy = FALL_SPEED_FREEFALL
        self.parachute_deployed = False
        self.rings.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.wind_lines.clear()
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_timer = 0
        self.timer = TIMER_MAX
        self.altitude = ALTITUDE_START
        self.bg_offset = 0.0
        self.rng = random.Random()
        self.ring_timer = 0
        self.landing_x = 160.0
        self.shake_frames = 0
        self.wind_dir = 0.0
        self.wind_timer = 300 + self.rng.randint(0, 180)
        self.last_color = None
        self.heat_warning_timer = 0
        self._spawn_ring_cooldown = 60

    def _game_over(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.heat >= HEAT_MAX:
            self.shake_frames = 30
        if self.score > Game.best_score:
            Game.best_score = self.score

    # ── Update ────────────────────────────────────────────

    def update(self) -> None:
        # Always handle input
        self._handle_input()

        if self.phase != Phase.PLAYING:
            return

        self._update_player()
        self._update_rings()
        self._check_collisions()
        self._update_particles()
        self._update_floating_texts()
        self._update_heat()
        self._update_super()
        self._update_wind()
        self._update_difficulty()
        if self.shake_frames > 0:
            self.shake_frames -= 1

        self.timer -= 1
        self.altitude -= ALTITUDE_PER_FRAME

        # Check failure conditions
        if self.heat >= HEAT_MAX:
            self._game_over()
            return
        if self.timer <= 0 or self.altitude <= 0:
            if self.parachute_deployed:
                # Successful landing
                if abs(self.player_x - self.landing_x) < 40:
                    self.score += LANDING_SCORE
                    self._spawn_text(self.player_x, self.player_y,
                                     f"+{LANDING_SCORE}", 10)
                self._game_over()
            else:
                self._game_over()
            return

    def _update_player(self) -> None:
        max_vx = VX_MAX_CHUTE if self.parachute_deployed else VX_MAX_FREEFALL
        self.player_vx *= 0.90
        if abs(self.player_vx) > max_vx:
            self.player_vx = max_vx if self.player_vx > 0 else -max_vx

        self.player_x += self.player_vx
        self.player_y += self.player_vy

        # Wind drift on player
        self.player_x += self.wind_dir * 0.3

        # Clamp
        self.player_x = max(5.0, min(float(SCREEN_W - 5), self.player_x))
        self.player_y = max(5.0, min(float(SCREEN_H - 5), self.player_y))

    def _update_rings(self) -> None:
        # Move existing rings upward
        for ring in self.rings:
            ring.y -= ring.vy
            ring.x += self.wind_dir * 0.2

        # Remove off-screen (passed player above screen or too far off sides)
        new_rings: list[Ring] = []
        for ring in self.rings:
            if ring.y > -20 and ring.x > -30 and ring.x < SCREEN_W + 30:
                new_rings.append(ring)
            elif not ring.collected:
                # Missed ring -> add heat
                self.heat += HEAT_MISS
                self._spawn_text(ring.x, max(ring.y, 10.0), "MISS", 8)
        self.rings = new_rings

        # Spawn new rings
        self.ring_timer += 1
        if self.ring_timer >= self._spawn_ring_cooldown and len(self.rings) < MAX_RINGS:
            self.ring_timer = 0
            count = self.rng.randint(2, 4)
            for _ in range(count):
                if len(self.rings) < MAX_RINGS:
                    self._spawn_ring()

    def _spawn_ring(self) -> None:
        x = float(self.rng.randint(20, SCREEN_W - 20))
        y = float(SCREEN_H + self.rng.randint(10, 40))
        color = self.rng.randint(0, 3)
        radius = float(self.rng.randint(RING_MIN_RADIUS, RING_MAX_RADIUS))
        vy = 1.0 + self.rng.random() * 1.0
        self.rings.append(Ring(x=x, y=y, color=color, radius=radius, vy=vy))

    def _check_collisions(self) -> None:
        is_super = self.super_timer > 0
        for ring in self.rings:
            if ring.collected:
                continue
            effective_radius = ring.radius
            if is_super:
                effective_radius *= SUPER_RING_RADIUS_MULT
            dist = math.hypot(self.player_x - ring.x, self.player_y - ring.y)
            if dist < PLAYER_RADIUS + effective_radius:
                self._collect_ring(ring)

    def _collect_ring(self, ring: Ring) -> None:
        ring.collected = True
        is_super = self.super_timer > 0

        if is_super or self.last_color is None or ring.color == self.last_color:
            # Same color or super mode
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo

            base_score = 100
            mult = self.combo
            if is_super:
                base_score *= SUPER_MULTIPLIER
            points = base_score * (1 + mult)
            self.score += points

            txt = f"+{points}"
            if self.combo >= 2:
                txt = f"+{points} x{self.combo}"
            self._spawn_text(ring.x, ring.y, txt, 3)

            # Trigger SUPER CHUTE
            if self.combo >= COMBO_THRESHOLD and not is_super:
                self.super_timer = SUPER_DURATION
                self._play_sound_super()

            self._play_sound_combo() if self.combo > 1 else self._play_sound_collect()
        else:
            # Wrong color
            self.combo = 0
            self.heat += HEAT_WRONG
            self._spawn_text(ring.x, ring.y, "WRONG!", 8)
            self._play_sound_collect()

        self.last_color = ring.color

        # Particle burst
        num = 16 if is_super else 10
        for i in range(num):
            angle = (math.pi * 2 / num) * i + self.rng.random() * 0.3
            speed = 2.0 + self.rng.random() * 3.0
            p_color = ring.color
            if is_super:
                p_color = self.rng.randint(0, 3)
            self.particles.append(Particle(
                x=ring.x, y=ring.y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=15 + self.rng.randint(0, 15),
                color=COLOR_VALS[p_color],
                max_life=30,
            ))

    def _update_particles(self) -> None:
        new_parts: list[Particle] = []
        for p in self.particles:
            p.life -= 1
            if p.life > 0:
                p.x += p.vx
                p.y += p.vy
                p.vy += 0.05
                new_parts.append(p)
        self.particles = new_parts

    def _update_floating_texts(self) -> None:
        new_texts: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.life -= 1
            if ft.life > 0:
                ft.y -= 0.8
                new_texts.append(ft)
        self.floating_texts = new_texts

    def _spawn_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(
            x=x, y=y, text=text, life=25, color=color,
        ))

    def _update_heat(self) -> None:
        if self.heat > 0:
            self.heat -= HEAT_DECAY
            if self.heat < 0:
                self.heat = 0.0
        if self.heat > 70:
            self.heat_warning_timer += 1
        else:
            self.heat_warning_timer = 0

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_timer = 0
                self.combo = 0
                self.last_color = None

    def _update_wind(self) -> None:
        self.wind_timer -= 1
        if self.wind_timer <= 0:
            self.wind_dir = self.rng.uniform(-1.5, 1.5)
            self.wind_timer = 300 + self.rng.randint(0, 180)

        # Spawn wind lines
        if self.rng.random() < 0.3:
            y = float(self.rng.randint(0, SCREEN_H))
            length = 40.0 + self.rng.random() * 80.0
            speed = self.wind_dir * (1.5 + self.rng.random())
            self.wind_lines.append(WindLine(
                x=0.0 if self.wind_dir > 0 else float(SCREEN_W),
                y=y, length=length, speed=speed, life=30 + self.rng.randint(0, 20),
            ))

        # Move wind lines
        new_lines: list[WindLine] = []
        for wl in self.wind_lines:
            wl.life -= 1
            if wl.life > 0:
                wl.x += wl.speed * 0.3
                new_lines.append(wl)
        self.wind_lines = new_lines

    def _update_difficulty(self) -> None:
        # Faster spawns as score increases
        reduction = (self.score // 2000) * 2
        self._spawn_ring_cooldown = max(30, 60 - reduction)

    # ── Sound ─────────────────────────────────────────────

    def _play_sound_collect(self) -> None:
        pyxel.play(0, 0, loop=False)

    def _play_sound_combo(self) -> None:
        pyxel.play(0, 1, loop=False)

    def _play_sound_super(self) -> None:
        pyxel.play(1, 2, loop=False)

    # ── Draw ──────────────────────────────────────────────

    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.cls(1)
        pyxel.text(SCREEN_W // 2 - 42, 40, "CHUTE CHAIN", 7)
        pyxel.text(SCREEN_W // 2 - 58, 55, "Parachute skydiving color-match", 13)
        pyxel.text(SCREEN_W // 2 - 48, 85, "ARROWS: Move", 7)
        pyxel.text(SCREEN_W // 2 - 48, 95, "SPACE: Toggle Chute", 7)
        pyxel.text(SCREEN_W // 2 - 60, 115, "Match colors -> COMBO -> SUPER CHUTE!", 10)
        pyxel.text(SCREEN_W // 2 - 35, 140, "Avoid HEAT from wrong colors!", 8)
        pyxel.text(SCREEN_W // 2 - 50, 170, "Deploy chute before hitting ground!", 7)
        pyxel.text(SCREEN_W // 2 - 48, 200, "Press ENTER to start", 13)

    def _draw_playing(self) -> None:
        # Sky background
        bg_color = 1 if self.super_timer <= 0 else 1
        pyxel.cls(bg_color)

        # Sky gradient bands
        for i in range(0, SCREEN_H, 8):
            shade = 1 if i % 16 == 0 else 13
            pyxel.rect(0, int((i + self.bg_offset * 2) % SCREEN_H), SCREEN_W, 4, shade)

        self.bg_offset = (self.bg_offset + 0.3) % (SCREEN_H)

        # Wind lines
        for wl in self.wind_lines:
            alpha = max(1, wl.life)
            for dx in range(int(wl.length)):
                px = int(wl.x + dx * (1 if wl.speed > 0 else -1))
                if 0 <= px < SCREEN_W:
                    pyxel.pset(px, int(wl.y) + (dx % 3), wl.alpha)

        # Rings
        is_super = self.super_timer > 0
        for ring in self.rings:
            if ring.collected:
                continue
            col = COLOR_VALS[ring.color]
            r = int(ring.radius)
            if is_super:
                col = self._rainbow_color(ring.color)
            pyxel.circb(int(ring.x), int(ring.y), r, col)

        # SUPER mode border glow
        if is_super:
            hue = (pyxel.frame_count // 5) % 8 + 8
            pyxel.rectb(0, 0, SCREEN_W, SCREEN_H, hue)

        # Ground
        pyxel.rect(0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y, 4)
        pyxel.rect(0, GROUND_Y, SCREEN_W, 2, 9)

        # Player
        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0:
            shake_x = self.rng.randint(-3, 3)
            shake_y = self.rng.randint(-3, 3)

        px = int(self.player_x + shake_x)
        py = int(self.player_y + shake_y)

        # Parachute canopy (above player if deployed)
        if self.parachute_deployed:
            chute_col = 7
            if is_super:
                chute_col = self._rainbow_color(0)
            # Canopy arc
            for dx in range(-14, 15):
                dy = -12 - int(abs(dx) * 0.5)
                if px + dx >= 0 and px + dx < SCREEN_W and py + dy >= 0:
                    pyxel.pset(px + dx, py + dy, chute_col)
            # Lines from canopy to player
            pyxel.line(px - 8, py - 8, px, py, 7)
            pyxel.line(px + 8, py - 8, px, py, 7)

        # Player body
        player_col = 7
        if is_super:
            player_col = self._rainbow_color(0)
        # Triangle pointing down (skydiver)
        pyxel.tri(px, py - 8, px - 5, py, px + 5, py, player_col)
        # Head circle
        pyxel.circ(px, py - 9, 3, player_col)

        # Parachute ripple lines below if deployed
        if self.parachute_deployed:
            for dx in range(-3, 4):
                if dx % 2 == 0:
                    pyxel.pset(px + dx, py + 6, 7)
            pyxel.line(px - 5, py + 4, px + 5, py + 4, 7)

        # Particles
        for p in self.particles:
            alpha_ratio = p.life / p.max_life
            col = p.color
            if alpha_ratio < 0.3:
                continue
            pyxel.pset(int(p.x), int(p.y), col)

        # Floating texts
        for ft in self.floating_texts:
            alpha = ft.life / 25
            if alpha < 0.1:
                continue
            col = ft.color if alpha > 0.5 else 13
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, col)

        # HUD
        pyxel.text(4, 2, f"SCORE: {self.score}", 7)
        combo_text = f"COMBO: x{self.combo}"
        pyxel.text(SCREEN_W // 2 - len(combo_text) * 2, 2, combo_text, 10 if self.combo >= COMBO_THRESHOLD else 7)
        alt_str = f"ALT: {int(self.altitude)}ft"
        pyxel.text(SCREEN_W - len(alt_str) * 4 - 4, 2, alt_str, 7)

        # Timer
        secs = self.timer // 60
        time_str = f"TIME: {secs}"
        timer_col = 7 if secs > 15 else (8 if secs % 2 == 0 else 7)
        pyxel.text(SCREEN_W - len(time_str) * 4 - 4, 10, time_str, timer_col)

        # HEAT bar
        heat_bar_w = 100
        heat_pct = min(1.0, self.heat / HEAT_MAX)
        heat_col = 8 if self.heat > 70 else (10 if self.heat > 40 else 3)
        pyxel.rect(4, SCREEN_H - 12, heat_bar_w, 8, 1)
        pyxel.rect(4, SCREEN_H - 12, int(heat_bar_w * heat_pct), 8, heat_col)
        heat_text = f"HEAT: {int(self.heat)}"
        pyxel.text(4, SCREEN_H - 20, heat_text, heat_col)

        # SUPER timer gauge
        if is_super:
            super_pct = self.super_timer / SUPER_DURATION
            gauge_w = 80
            pyxel.rect(SCREEN_W // 2 - gauge_w // 2, SCREEN_H - 12, gauge_w, 8, 1)
            pyxel.rect(SCREEN_W // 2 - gauge_w // 2, SCREEN_H - 12,
                       int(gauge_w * super_pct), 8, 10)
            pyxel.text(SCREEN_W // 2 - 22, SCREEN_H - 20, "SUPER CHUTE!", 10)

        # Parachute status indicator
        status = "CHUTE: ON" if self.parachute_deployed else "CHUTE: OFF"
        status_col = 3 if self.parachute_deployed else 8
        pyxel.text(4, 10, status, status_col)

    def _draw_game_over(self) -> None:
        pyxel.cls(1)
        pyxel.text(SCREEN_W // 2 - 30, 40, "GAME OVER", 8)
        pyxel.text(SCREEN_W // 2 - 50, 70, f"SCORE: {self.score}", 7)
        pyxel.text(SCREEN_W // 2 - 50, 85, f"MAX COMBO: x{self.max_combo}", 10)
        pyxel.text(SCREEN_W // 2 - 50, 100, f"BEST SCORE: {Game.best_score}", 7)
        if self.heat >= HEAT_MAX:
            pyxel.text(SCREEN_W // 2 - 70, 130, "Parachute malfunction! (overheat)", 8)
        elif not self.parachute_deployed and (self.timer <= 0 or self.altitude <= 0):
            pyxel.text(SCREEN_W // 2 - 60, 130, "No parachute deployed! SPLAT!", 8)
        else:
            pyxel.text(SCREEN_W // 2 - 40, 130, "You landed safely!", 3)
        pyxel.text(SCREEN_W // 2 - 48, 170, "Press ENTER to retry", 13)

    def _rainbow_color(self, offset: int = 0) -> int:
        i = (pyxel.frame_count // 6 + offset) % 4
        return COLOR_VALS[i]


# ── Entry point ───────────────────────────────────────────

if __name__ == "__main__":
    Game()
