"""Sky Surge — Skydiving Color-Match COMBO Chain"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# --- Constants ---
SCREEN_W = 320
SCREEN_H = 240
FPS = 30
GAME_DURATION = 60 * FPS  # 1800 frames
DIVE_DURATION = 15 * FPS  # 450 frames
CHUTE_DURATION = 3 * FPS  # 90 frames
LANDED_PAUSE = 1 * FPS  # 30 frames

PLAYER_SPEED = 3.0
PLAYER_RADIUS = 8
RING_RADIUS = 16
MAX_RINGS = 8

SUPER_DIVE_DURATION = 300  # frames
COMBO_THRESHOLD = 4
SUPER_MULTIPLIER = 3.0

HEAT_MAX = 100
HEAT_WRONG = 15
HEAT_PASS = 5
HEAT_COMBO_COOL = -5
HEAT_PASSIVE = 0.03
HEAT_DECAY = 0.02
HEAT_SHAKE = 70
HEAT_BLINK = 90

RING_COLORS = [pyxel.COLOR_RED, pyxel.COLOR_LIME, pyxel.COLOR_DARK_BLUE, pyxel.COLOR_YELLOW]


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class DivePhase(Enum):
    FALLING = auto()
    CHUTE = auto()
    LANDED = auto()


@dataclass
class Ring:
    x: float
    y: float
    color: int
    radius: int = RING_RADIUS
    passed: bool = False


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
    vy: float = -1.5


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Sky Surge", fps=FPS, display_scale=2)
        self.rng = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self._init_game_state()

    def _init_game_state(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.game_timer = GAME_DURATION
        self.best_score = getattr(self, "best_score", 0)

        self.player_x: float = SCREEN_W / 2
        self.player_y: float = SCREEN_H - 40
        self.player_color_idx = 0
        self.player_color_timer = 0
        self.player_color_interval = 30

        self.fall_speed = 2.0
        self.ring_spawn_timer = 0
        self.ring_spawn_interval = 40
        self.verticl_gap = 50

        self.dive_phase = DivePhase.FALLING
        self.dive_timer = DIVE_DURATION
        self.chute_timer = 0
        self.landed_timer = 0
        self.dive_count = 0
        self.dive_score = 0

        self.super_dive = False
        self.super_dive_timer = 0
        self.super_rainbow_offset = 0

        self.rings: list[Ring] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.player_trail: list[tuple[float, float, int]] = []

        self.shake_x = 0
        self.shake_y = 0
        self.shake_timer = 0

        self.chute_warning_flash = 0

    # --- Update ---
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self.phase = Phase.PLAYING
            self._init_game_state()

    def _update_playing(self) -> None:
        self.game_timer -= 1
        if self.game_timer <= 0:
            self._game_over()
            return

        self._update_escalation()
        self._read_player_input()
        self._update_player_color()
        self._update_player_y()
        self._update_rings()
        self._update_collisions()
        self._update_heat()
        self._update_super_dive()
        self._update_dive_timers()
        self._update_particles()
        self._update_floating_texts()
        self._update_shake()

    def _update_escalation(self) -> None:
        t = 1.0 - (self.game_timer / GAME_DURATION)
        self.fall_speed = 2.0 + t * 4.0
        self.ring_spawn_interval = max(20, int(40 - t * 20))
        self.player_color_interval = max(15, int(30 - t * 15))
        self.verticl_gap = max(30, int(50 - t * 20))

    def _read_player_input(self) -> None:
        if pyxel.btn(pyxel.KEY_LEFT):
            self._move_player(-PLAYER_SPEED)
        if pyxel.btn(pyxel.KEY_RIGHT):
            self._move_player(PLAYER_SPEED)
        if pyxel.btnp(pyxel.KEY_SPACE) and self.dive_phase == DivePhase.FALLING:
            if self.dive_timer <= DIVE_DURATION - 30:
                self._deploy_chute()

    def _move_player(self, dx: float) -> None:
        self.player_x += dx
        self.player_x = max(16.0, min(float(SCREEN_W - 16), self.player_x))

    def _update_player_color(self) -> None:
        self.player_color_timer += 1
        if self.player_color_timer >= self.player_color_interval:
            self.player_color_timer = 0
            self.player_color_idx = (self.player_color_idx + 1) % 4

    def _update_player_y(self) -> None:
        if self.dive_phase == DivePhase.FALLING:
            self.player_y += self.fall_speed
        elif self.dive_phase == DivePhase.CHUTE:
            self.player_y += 0.5

    def _update_rings(self) -> None:
        if self.dive_phase != DivePhase.FALLING:
            return

        self.ring_spawn_timer += 1
        if self.ring_spawn_timer >= self.ring_spawn_interval and len(self.rings) < MAX_RINGS:
            self.ring_spawn_timer = 0
            self._spawn_ring()

        for ring in self.rings:
            ring.y += self.fall_speed

        self.rings = [r for r in self.rings if r.y < SCREEN_H + RING_RADIUS]

    def _spawn_ring(self) -> None:
        color = self.rng.choice(RING_COLORS)
        x = self.rng.uniform(RING_RADIUS + 8, SCREEN_W - RING_RADIUS - 8)
        self.rings.append(Ring(x=x, y=-RING_RADIUS, color=color))

    def _update_collisions(self) -> None:
        if self.dive_phase != DivePhase.FALLING:
            return

        player_color = RING_COLORS[self.player_color_idx]
        for ring in self.rings:
            if ring.passed:
                continue
            dx = self.player_x - ring.x
            dy = self.player_y - ring.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < ring.radius + PLAYER_RADIUS:
                ring.passed = True
                if self.super_dive or ring.color == player_color:
                    self._on_match(ring)
                else:
                    self._on_mismatch(ring)

    def _on_match(self, ring: Ring) -> None:
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        multiplier = SUPER_MULTIPLIER if self.super_dive else 1.0
        points = int(10 * self.combo * multiplier)
        self.score += points
        self.dive_score += points
        self.heat = max(0, self.heat + HEAT_COMBO_COOL)

        self._spawn_particles(ring.x, ring.y, ring.color, 8)
        self._spawn_floating_text(ring.x, ring.y - 10, f"+{points}",
                                  ring.color if not self.super_dive else pyxel.COLOR_WHITE)
        if self.combo >= 2:
            self._spawn_floating_text(self.player_x, self.player_y - 20,
                                      f"COMBO x{self.combo}", pyxel.COLOR_WHITE)
        self._try_play_sound(0)

    def _on_mismatch(self, ring: Ring) -> None:
        self.heat = min(HEAT_MAX, self.heat + HEAT_WRONG)
        self.combo = 0
        self._spawn_floating_text(ring.x, ring.y - 10, "WRONG!", pyxel.COLOR_RED)
        self._spawn_particles(ring.x, ring.y, pyxel.COLOR_RED, 4)
        self._try_play_sound(2)

    def _update_heat(self) -> None:
        if not self.super_dive:
            self.heat += HEAT_PASSIVE
            self.heat -= HEAT_DECAY
        self.heat = max(0, min(HEAT_MAX, self.heat))
        if self.heat >= HEAT_MAX:
            self._game_over()

    def _update_super_dive(self) -> None:
        if self.combo >= COMBO_THRESHOLD and not self.super_dive:
            self._activate_super_dive()
        if self.super_dive:
            self.super_dive_timer -= 1
            self.super_rainbow_offset = (self.super_rainbow_offset + 1) % 4
            if self.super_dive_timer % 4 == 0:
                px = self.player_x + self.rng.uniform(-10, 10)
                py = self.player_y + self.rng.uniform(-10, 10)
                c = RING_COLORS[self.rng.randint(0, 3)]
                self.particles.append(Particle(x=px, y=py, vx=0, vy=0, life=12, color=c, max_life=12))
            if self.super_dive_timer <= 0:
                self._deactivate_super_dive()

    def _activate_super_dive(self) -> None:
        self.super_dive = True
        self.super_dive_timer = SUPER_DIVE_DURATION
        self._spawn_floating_text(self.player_x, self.player_y - 30, "SUPER DIVE!", pyxel.COLOR_WHITE)
        for _ in range(20):
            px = self.player_x + self.rng.uniform(-20, 20)
            py = self.player_y + self.rng.uniform(-20, 20)
            c = RING_COLORS[self.rng.randint(0, 3)]
            vx = self.rng.uniform(-2, 2)
            vy = self.rng.uniform(-2, 2)
            self.particles.append(Particle(x=px, y=py, vx=vx, vy=vy, life=20, color=c, max_life=20))
        for i in range(3):
            self._try_play_sound(i * 2)

    def _deactivate_super_dive(self) -> None:
        self.super_dive = False
        self.combo = 0
        self._spawn_floating_text(self.player_x, self.player_y - 30, "DIVE END", pyxel.COLOR_GRAY)
        for _ in range(10):
            px = self.player_x + self.rng.uniform(-10, 10)
            py = self.player_y + self.rng.uniform(-10, 10)
            self.particles.append(Particle(x=px, y=py, vx=0, vy=0, life=10, color=pyxel.COLOR_GRAY, max_life=10))

    def _update_dive_timers(self) -> None:
        if self.dive_phase == DivePhase.FALLING:
            self.dive_timer -= 1
            if self.dive_timer <= 0 and not self._chute_deployed():
                self._deploy_chute()
            else:
                chute_warn = 1 * FPS
                if self.dive_timer <= chute_warn:
                    self.chute_warning_flash = (self.chute_warning_flash + 1) % 30
        elif self.dive_phase == DivePhase.CHUTE:
            self.chute_timer -= 1
            if self.chute_timer <= 0:
                self.dive_phase = DivePhase.LANDED
                self.landed_timer = LANDED_PAUSE
        elif self.dive_phase == DivePhase.LANDED:
            self.landed_timer -= 1
            if self.landed_timer <= 0:
                self._start_new_dive()

    def _chute_deployed(self) -> bool:
        return self.dive_phase in (DivePhase.CHUTE, DivePhase.LANDED)

    def _deploy_chute(self) -> None:
        landing_bonus = self.dive_timer * 2
        self.score += landing_bonus
        self.dive_score += landing_bonus
        self.dive_phase = DivePhase.CHUTE
        self.chute_timer = CHUTE_DURATION
        self.rings.clear()
        self._spawn_floating_text(self.player_x, self.player_y - 20,
                                  f"LANDING! +{landing_bonus}", pyxel.COLOR_LIME)
        self._try_play_sound(3)

    def _start_new_dive(self) -> None:
        self.dive_count += 1
        self.dive_phase = DivePhase.FALLING
        self.dive_timer = DIVE_DURATION
        self.dive_score = 0
        self.combo = 0
        self.super_dive = False
        self.super_dive_timer = 0
        self.player_y = 0
        self.rings.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.player_trail.clear()
        self._spawn_floating_text(self.player_x, self.player_y + 20,
                                  f"DIVE {self.dive_count + 1}", pyxel.COLOR_WHITE)

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _update_shake(self) -> None:
        if self.heat >= HEAT_SHAKE:
            self.shake_timer = max(self.shake_timer, 10)
        if self.shake_timer > 0:
            self.shake_timer -= 1
            self.shake_x = self.rng.uniform(-2, 2)
            self.shake_y = self.rng.uniform(-2, 2)
        else:
            self.shake_x = 0
            self.shake_y = 0

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.pi * 2)
            speed = self.rng.uniform(1, 3)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=15, color=color, max_life=15))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=40, color=color))

    def _try_play_sound(self, note: int) -> None:
        try:
            pyxel.play(0, note)
        except BaseException:
            pass

    def _game_over(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score
        self.rings.clear()
        self.particles.clear()
        self.floating_texts.clear()

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self.phase = Phase.PLAYING
            self._init_game_state()

    # --- Draw ---
    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        self._draw_sky_bg()
        pyxel.text(SCREEN_W // 2 - 40, 60, "SKY SURGE", pyxel.COLOR_WHITE)
        pyxel.text(SCREEN_W // 2 - 70, 80, "Skydiving Color-Match", pyxel.COLOR_LIME)
        pyxel.text(SCREEN_W // 2 - 55, 95, "COMBO Chain Challenge", pyxel.COLOR_LIME)
        pyxel.text(SCREEN_W // 2 - 50, 140, "LEFT/RIGHT : Move", pyxel.COLOR_GRAY)
        pyxel.text(SCREEN_W // 2 - 50, 152, "SPACE      : Deploy Chute", pyxel.COLOR_GRAY)
        pyxel.text(SCREEN_W // 2 - 50, 164, "Match ring colors!", pyxel.COLOR_GRAY)
        pyxel.text(SCREEN_W // 2 - 50, 176, "COMBO x4 = SUPER DIVE!", pyxel.COLOR_YELLOW)
        blink = pyxel.frame_count % 60 < 40
        if blink:
            pyxel.text(SCREEN_W // 2 - 40, 210, "PRESS ENTER", pyxel.COLOR_WHITE)

    def _draw_playing(self) -> None:
        self._draw_sky_bg()
        self._draw_rings()
        self._draw_player_trail()
        self._draw_player()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_game_over(self) -> None:
        self._draw_sky_bg()
        pyxel.text(SCREEN_W // 2 - 40, 60, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(SCREEN_W // 2 - 30, 90, f"SCORE: {self.score}", pyxel.COLOR_WHITE)
        pyxel.text(SCREEN_W // 2 - 30, 105, f"BEST:  {self.best_score}", pyxel.COLOR_YELLOW)
        if self.score >= self.best_score:
            pyxel.text(SCREEN_W // 2 - 30, 120, "NEW RECORD!", pyxel.COLOR_LIME)
        pyxel.text(SCREEN_W // 2 - 30, 150, f"DIVES: {self.dive_count}", pyxel.COLOR_GRAY)
        pyxel.text(SCREEN_W // 2 - 30, 162, f"MAX COMBO: {self.max_combo}", pyxel.COLOR_GRAY)
        reason = "BURNED UP!" if self.heat >= HEAT_MAX else "TIME'S UP!"
        pyxel.text(SCREEN_W // 2 - 40, 180, reason, pyxel.COLOR_RED)
        blink = pyxel.frame_count % 40 < 30
        if blink:
            pyxel.text(SCREEN_W // 2 - 45, 210, "PRESS R TO RETRY", pyxel.COLOR_WHITE)

    def _draw_sky_bg(self) -> None:
        for i in range(SCREEN_H):
            t = i / SCREEN_H
            if t > 0.8:
                color = pyxel.COLOR_GREEN
            else:
                color = pyxel.COLOR_NAVY + int(t * 5)
                color = max(pyxel.COLOR_NAVY, min(pyxel.COLOR_LIGHT_BLUE, color))
            pyxel.rect(0, i, SCREEN_W, 1, color)

    def _draw_rings(self) -> None:
        for ring in self.rings:
            color = pyxel.COLOR_GRAY if ring.passed else ring.color
            pyxel.circb(int(ring.x), int(ring.y), ring.radius, color)

    def _draw_player_trail(self) -> None:
        trail_len = 10 if self.super_dive else 5
        self.player_trail.append((self.player_x, self.player_y, 8))
        if len(self.player_trail) > trail_len:
            self.player_trail = self.player_trail[-trail_len:]
        for i, (tx, ty, _) in enumerate(self.player_trail[:-1]):
            c = RING_COLORS[i % 4] if self.super_dive else RING_COLORS[self.player_color_idx]
            pyxel.circ(int(tx), int(ty), 2 + i, c)

    def _draw_player(self) -> None:
        px = int(self.player_x) + int(self.shake_x)
        py = int(self.player_y) + int(self.shake_y)
        if self.super_dive:
            c = RING_COLORS[self.super_rainbow_offset]
            pyxel.circ(px, py, PLAYER_RADIUS + 3, c)
            pyxel.circ(px, py, PLAYER_RADIUS + 2, RING_COLORS[(self.super_rainbow_offset + 1) % 4])
            pyxel.circ(px, py, PLAYER_RADIUS, RING_COLORS[(self.super_rainbow_offset + 2) % 4])
            pyxel.circ(px, py, PLAYER_RADIUS - 3, pyxel.COLOR_WHITE)
        else:
            pyxel.circ(px, py, PLAYER_RADIUS, RING_COLORS[self.player_color_idx])
            pyxel.circ(px, py, PLAYER_RADIUS - 3, pyxel.COLOR_WHITE)

        if self.dive_phase == DivePhase.CHUTE:
            pyxel.circb(px, py - PLAYER_RADIUS - 6, PLAYER_RADIUS + 4, pyxel.COLOR_WHITE)
            pyxel.circb(px, py - PLAYER_RADIUS - 6, PLAYER_RADIUS + 2, pyxel.COLOR_LIGHT_BLUE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha_ratio = p.life / max(p.max_life, 1)
            size = max(1, int(3 * alpha_ratio))
            pyxel.circ(int(p.x) + int(self.shake_x), int(p.y) + int(self.shake_y), size, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 40
            c = ft.color if alpha > 0.5 else pyxel.COLOR_GRAY
            pyxel.text(int(ft.x) - len(ft.text) * 2 + int(self.shake_x),
                       int(ft.y) + int(self.shake_y), ft.text, c)

    def _draw_hud(self) -> None:
        margin = 4
        pyxel.rect(0, 0, SCREEN_W, 16, pyxel.COLOR_BLACK)
        pyxel.text(margin, 4, f"SCORE:{self.score}", pyxel.COLOR_WHITE)
        pyxel.text(120, 4, f"COMBO:{self.combo}", pyxel.COLOR_YELLOW)

        time_left = max(0, self.game_timer / FPS)
        pyxel.text(220, 4, f"TIME:{time_left:.0f}", pyxel.COLOR_WHITE)

        heat_bar_x = 120
        heat_bar_w = 80
        pyxel.rect(heat_bar_x, 2, heat_bar_w, 4, pyxel.COLOR_GRAY)
        heat_fill = int(heat_bar_w * self.heat / HEAT_MAX)
        if self.heat >= HEAT_BLINK:
            heat_color = pyxel.COLOR_RED if pyxel.frame_count % 20 < 10 else pyxel.COLOR_ORANGE
        elif self.heat >= HEAT_SHAKE:
            heat_color = pyxel.COLOR_RED
        elif self.heat >= 40:
            heat_color = pyxel.COLOR_YELLOW
        else:
            heat_color = pyxel.COLOR_GREEN
        pyxel.rect(heat_bar_x, 2, heat_fill, 4, heat_color)

        if self.super_dive:
            sd_left = max(0, self.super_dive_timer / FPS)
            pyxel.text(margin, 224, f"SUPER:{sd_left:.1f}s", pyxel.COLOR_WHITE)

        if self.dive_phase == DivePhase.FALLING and self.dive_timer <= FPS:
            if self.chute_warning_flash < 15:
                msg = "PULL CHUTE! (SPACE)"
                pyxel.text(SCREEN_W // 2 - len(msg) * 2, SCREEN_H - 30, msg, pyxel.COLOR_YELLOW)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
