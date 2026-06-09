from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    VICTORY = auto()
    DEFEAT = auto()


@dataclass
class Rikishi:
    x: float
    y: float
    color: int
    vx: float = 0.0
    vy: float = 0.0
    stunned: bool = False
    stun_timer: float = 0.0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


SCREEN_W = 320
SCREEN_H = 240
RING_CENTER_X = 160
RING_CENTER_Y = 120
INNER_RADIUS = 90
OUTER_RADIUS = 110
RIKISHI_RADIUS = 12
BASE_PUSH_POWER = 1.5
SUPER_PUSH_POWER = 4.5
SUPER_DURATION = 300
COMBO_THRESHOLD = 4
STUN_DURATION = 90
HEAT_PER_MISS = 25
HEAT_DECAY = 0.3
MAX_HEAT = 100
GAME_TIME = 5400
COLORS = [8, 3, 5, 10]  # RED, GREEN, DARK_BLUE, YELLOW
PLAYER_SPEED = 2.0
AI_SPEED = 1.6
CONTACT_COOLDOWN = 10
AI_COLOR_CYCLE_INTERVAL = 120
COLOR_NAMES = {8: "RED", 3: "GREEN", 5: "BLUE", 10: "YELLOW"}


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="SUMO SURGE", fps=60)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.player = Rikishi(160.0, 160.0, 8)  # RED
        self.ai = Rikishi(160.0, 80.0, 3)  # GREEN
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.heat: float = 0.0
        self.phase = Phase.TITLE
        self.timer: int = GAME_TIME
        self.particles: list[Particle] = []
        self._contact_cooldown: int = 0
        self._ai_color_timer: int = 0
        self._stun_flash_counter: int = 0
        self._rainbow_offset: int = 0

    def update(self) -> None:
        self._stun_flash_counter += 1
        self._rainbow_offset = (self._rainbow_offset + 1) % len(COLORS)
        match self.phase:
            case Phase.TITLE:
                self._update_title()
            case Phase.PLAYING:
                self._update_playing()
            case Phase.VICTORY:
                self._update_victory()
            case Phase.DEFEAT:
                self._update_defeat()

    def draw(self) -> None:
        match self.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.PLAYING:
                self._draw_playing()
            case Phase.VICTORY:
                self._draw_victory()
            case Phase.DEFEAT:
                self._draw_defeat()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.PLAYING

    def _draw_title(self) -> None:
        pyxel.cls(1)
        pyxel.text(110, 40, "SUMO SURGE", 7)
        pyxel.text(75, 80, "Color-Match Sumo Wrestling", 6)
        pyxel.text(60, 130, "Arrow Keys: Move & Push", 7)
        pyxel.text(60, 145, "Match colors for COMBO!", 7)
        pyxel.text(60, 160, "COMBOx4 = SUPER SUMO", 10)
        pyxel.text(60, 175, "Wrong color = HEAT risk", 8)
        pyxel.text(70, 210, "Press SPACE to Start", pyxel.frame_count % 30 < 15 and 7 or 0)

    def _update_playing(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.DEFEAT
            return

        self._update_heat()
        self._update_super_mode()
        self._update_ai()
        self._update_particles()

        if self._contact_cooldown > 0:
            self._contact_cooldown -= 1

        if self.player.stunned:
            self.player.stun_timer -= 1
            if self.player.stun_timer <= 0:
                self.player.stunned = False
        else:
            self._move_player()

        if self._contact_cooldown <= 0:
            self._check_push()

        self._clamp_rikishi(self.player)
        self._clamp_rikishi(self.ai)

    def _draw_playing(self) -> None:
        pyxel.cls(1)
        self._draw_dohyo()
        self._draw_particles()
        self._draw_rikishi(self.player, True)
        self._draw_rikishi(self.ai, False)
        self._draw_hud()

    def _update_victory(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.TITLE

    def _draw_victory(self) -> None:
        pyxel.cls(1)
        pyxel.text(125, 50, "VICTORY!", 10)
        pyxel.text(110, 80, f"Score: {self.score}", 7)
        pyxel.text(100, 100, f"Max Combo: {self.max_combo}", 7)
        pyxel.text(80, 130, f"Time Left: {self.timer // 60}s", 7)
        time_bonus = self.timer
        pyxel.text(85, 145, f"Time Bonus: +{time_bonus}", 10)
        pyxel.text(75, 210, "Press SPACE to Continue", pyxel.frame_count % 30 < 15 and 7 or 0)

    def _update_defeat(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.TITLE

    def _draw_defeat(self) -> None:
        pyxel.cls(1)
        reason = "Ring Out" if self.timer > 0 else "Time Up"
        pyxel.text(130, 50, "DEFEAT", 8)
        pyxel.text(120, 75, f"({reason})", 6)
        pyxel.text(110, 100, f"Score: {self.score}", 7)
        pyxel.text(100, 120, f"Max Combo: {self.max_combo}", 7)
        pyxel.text(75, 210, "Press SPACE to Continue", pyxel.frame_count % 30 < 15 and 7 or 0)

    def _move_player(self) -> None:
        dx = 0.0
        dy = 0.0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx = -PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx = PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy = -PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy = PLAYER_SPEED

        if dx != 0.0 and dy != 0.0:
            inv_sqrt2 = 1.0 / math.sqrt(2.0)
            dx *= inv_sqrt2
            dy *= inv_sqrt2

        self.player.x += dx
        self.player.y += dy
        self.player.vx = dx
        self.player.vy = dy

    def _update_ai(self) -> None:
        r = self.ai
        if r.stunned:
            r.stun_timer -= 1
            if r.stun_timer <= 0:
                r.stunned = False
            return

        self._ai_color_timer += 1
        if self._ai_color_timer >= AI_COLOR_CYCLE_INTERVAL:
            self._ai_color_timer = 0
            r.color = self._cycle_color(r.color)

        dx = self.player.x - r.x
        dy = self.player.y - r.y
        dist = math.hypot(dx, dy)

        target_dist = RIKISHI_RADIUS * 2 + 10

        if dist > target_dist + 30:
            speed = AI_SPEED
        elif dist < target_dist - 10:
            speed = -AI_SPEED * 0.6
        else:
            speed = 0.3 * (1 if random.random() > 0.5 else -1)

        if dist > 0.001:
            ndx = dx / dist
            ndy = dy / dist
            jitter_x = random.uniform(-0.3, 0.3)
            jitter_y = random.uniform(-0.3, 0.3)
            r.x += ndx * speed + jitter_x
            r.y += ndy * speed + jitter_y
        else:
            r.x += random.uniform(-0.5, 0.5)
            r.y += random.uniform(-0.5, 0.5)

        r.vx = self.ai.vx if hasattr(self.ai, 'vx') else 0.0

    def _check_push(self) -> None:
        p = self.player
        a = self.ai
        dx = p.x - a.x
        dy = p.y - a.y
        dist = math.hypot(dx, dy)

        if dist < RIKISHI_RADIUS * 2 and dist > 0.001:
            self._resolve_push(dx / dist, dy / dist)

    def _resolve_push(self, ndx: float, ndy: float) -> None:
        is_match = self.super_mode or self.player.color == self.ai.color

        if is_match:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            self.heat = max(0.0, self.heat - 10.0)
        else:
            self.combo = 0
            self.heat = min(float(MAX_HEAT), self.heat + HEAT_PER_MISS)

        if self.combo >= COMBO_THRESHOLD and not self.super_mode:
            self.super_mode = True
            self.super_timer = SUPER_DURATION

        push_power = SUPER_PUSH_POWER if self.super_mode else BASE_PUSH_POWER

        if self.player.stunned:
            self.ai.x -= ndx * push_power
            self.ai.y -= ndy * push_power
        elif self.ai.stunned:
            self.ai.x += ndx * push_power
            self.ai.y += ndy * push_power
        else:
            self.ai.x += ndx * push_power
            self.ai.y += ndy * push_power

        px = (self.player.x + self.ai.x) / 2.0
        py = (self.player.y + self.ai.y) / 2.0
        count = 10 if self.super_mode else 5
        if self.super_mode:
            for i in range(count):
                color = COLORS[i % len(COLORS)]
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(1, 3)
                life = 30
                self.particles.append(Particle(px, py, math.cos(angle) * speed, math.sin(angle) * speed, life, color))
        else:
            p_color = 7
            for _ in range(count):
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(1, 3)
                life = 20
                self.particles.append(Particle(px, py, math.cos(angle) * speed, math.sin(angle) * speed, life, p_color))

        self.player.color = self._cycle_color(self.player.color)

        self._contact_cooldown = CONTACT_COOLDOWN

        self._check_ring_out()

    def _check_ring_out(self) -> None:
        p_dist = math.hypot(self.player.x - RING_CENTER_X, self.player.y - RING_CENTER_Y)
        a_dist = math.hypot(self.ai.x - RING_CENTER_X, self.ai.y - RING_CENTER_Y)

        if p_dist > OUTER_RADIUS:
            self.phase = Phase.DEFEAT
        elif a_dist > OUTER_RADIUS:
            self.score += self.combo * 100 + self.timer
            self.phase = Phase.VICTORY

    def _update_heat(self) -> None:
        if self.heat >= MAX_HEAT:
            self.player.stunned = True
            self.player.stun_timer = STUN_DURATION
            self.heat = 0.0
            return
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_super_mode(self) -> None:
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0

    def _update_particles(self) -> None:
        for pt in self.particles:
            pt.x += pt.vx
            pt.y += pt.vy
            pt.life -= 1
        self.particles = [pt for pt in self.particles if pt.life > 0]

    def _cycle_color(self, current: int) -> int:
        try:
            idx = COLORS.index(current)
            return COLORS[(idx + 1) % len(COLORS)]
        except ValueError:
            return COLORS[0]

    def _clamp_rikishi(self, r: Rikishi) -> None:
        pass

    def _draw_dohyo(self) -> None:
        pyxel.circb(RING_CENTER_X, RING_CENTER_Y, OUTER_RADIUS, 15)
        pyxel.circb(RING_CENTER_X, RING_CENTER_Y, OUTER_RADIUS - 1, 15)
        pyxel.circb(RING_CENTER_X, RING_CENTER_Y, INNER_RADIUS, 15)
        pyxel.circ(RING_CENTER_X, RING_CENTER_Y, INNER_RADIUS - 1, 4)
        pyxel.circ(RING_CENTER_X, RING_CENTER_Y, INNER_RADIUS - 3, 4)

    def _draw_rikishi(self, r: Rikishi, is_player: bool) -> None:
        if r.stunned and (self._stun_flash_counter // 8) % 2 == 0:
            return

        border_color = 7 if is_player else 13

        if is_player and self.super_mode:
            rainbow_color = COLORS[self._rainbow_offset]
            pyxel.circb(int(r.x), int(r.y), RIKISHI_RADIUS + 2, rainbow_color)
            pyxel.circb(int(r.x), int(r.y), RIKISHI_RADIUS + 1, COLORS[(self._rainbow_offset + 1) % len(COLORS)])

        pyxel.circ(int(r.x), int(r.y), RIKISHI_RADIUS, r.color)
        pyxel.circb(int(r.x), int(r.y), RIKISHI_RADIUS, border_color)

        if is_player and self.super_mode:
            pyxel.text(int(r.x) - RIKISHI_RADIUS - 2, int(r.y) - RIKISHI_RADIUS - 10, "SUPER!", COLORS[self._rainbow_offset])

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, 18, 0)

        pyxel.text(4, 2, f"SCORE:{self.score}", 7)
        combo_text = f"COMBO:{self.combo}"
        combo_color = 10 if self.combo >= COMBO_THRESHOLD else 7
        pyxel.text(100, 2, combo_text, combo_color)

        heat_width = 40
        heat_fill = int(self.heat * heat_width / MAX_HEAT)
        pyxel.text(180, 2, "HEAT", 7)
        pyxel.rectb(215, 1, heat_width + 2, 10, 7)
        if heat_fill > 0:
            heat_color = 2 if self.heat >= 70 else 9
            pyxel.rect(216, 2, heat_fill, 8, heat_color)

        secs = self.timer // 60
        pyxel.text(270, 2, f"T:{secs}", 7)

        if self.super_mode:
            super_secs = self.super_timer // 60
            pyxel.text(110, 14, f"SUPER {super_secs}s", COLORS[self._rainbow_offset])

    def _draw_particles(self) -> None:
        for pt in self.particles:
            alpha = max(1, pt.life)
            if alpha > 10:
                pyxel.pset(int(pt.x), int(pt.y), pt.color)
            elif alpha > 0:
                if (self._stun_flash_counter // 4) % 2 == 0:
                    pyxel.pset(int(pt.x), int(pt.y), pt.color)


if __name__ == "__main__":
    Game()
