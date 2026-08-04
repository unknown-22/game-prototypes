"""Sumo Chain — Top-down sumo wrestling with color-match COMBO mechanics."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pyxel


@dataclass
class Wrestler:
    x: float
    y: float
    radius: float
    facing_angle: float
    active_color: int


@dataclass
class PushZone:
    x: float
    y: float
    radius: float
    color: int
    life: int


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int


@dataclass
class FloatText:
    x: float
    y: float
    text: str
    color: int
    life: int


class Game:
    SCR_W = 320
    SCR_H = 240
    RING_CX = 160
    RING_CY = 120
    RING_RADIUS = 90
    WRESTLER_RADIUS = 8
    ZONE_RADIUS = 20
    ZONE_COUNT_MIN = 3
    ZONE_COUNT_MAX = 5
    ZONE_LIFE = 300
    ZONE_OVERLAP_MIN = 20
    BASE_PUSH_POWER = 3.0
    SUPER_PUSH_POWER = 7.5
    SUPER_DURATION = 300
    COMBO_THRESHOLD = 4
    MAX_HEAT = 100
    HEAT_MISMATCH = 15
    HEAT_AI_HIT = 10
    HEAT_DECAY = 0.02
    GAME_TIME = 1800
    FPS = 30
    PLAYER_SPEED = 1.5
    AI_PUSH_POWER = 2.5
    AI_PUSH_INTERVAL_MIN = 60
    AI_PUSH_INTERVAL_MAX = 120
    ZONE_SPAWN_INTERVAL = 90

    COLORS = [8, 11, 5, 10]
    RAINBOW_COLORS = [8, 9, 10, 11, 12, 14]

    def __init__(self) -> None:
        pyxel.init(self.SCR_W, self.SCR_H, title="Sumo Chain")
        self._rng = random.Random()
        self.best_score = 0
        self._reset()
        pyxel.run(self.update, self.draw)

    def _reset(self) -> None:
        self.phase = "TITLE"
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = self.GAME_TIME
        self.super_timer = 0
        self.rounds_won = 0
        self.last_color: int | None = None
        self.zones: list[PushZone] = []
        self.particles: list[Particle] = []
        self.float_texts: list[FloatText] = []
        self.zone_spawn_timer = self.ZONE_SPAWN_INTERVAL

        self.player = Wrestler(
            x=self.RING_CX - 30.0,
            y=self.RING_CY,
            radius=self.WRESTLER_RADIUS,
            facing_angle=0.0,
            active_color=self.COLORS[0],
        )
        self.ai = Wrestler(
            x=self.RING_CX + 30.0,
            y=self.RING_CY,
            radius=self.WRESTLER_RADIUS,
            facing_angle=math.pi,
            active_color=self.COLORS[1],
        )
        self.ai_push_timer = self._rng.randint(self.AI_PUSH_INTERVAL_MIN, self.AI_PUSH_INTERVAL_MAX)
        self.thrusting = False
        self.thrust_timer = 0
        self.thrust_duration = 8

        self._spawn_zones()

    # ------------------------------------------------------------------ Zone

    def _spawn_zones(self) -> None:
        self.zones.clear()
        target_count = self._rng.randint(self.ZONE_COUNT_MIN, self.ZONE_COUNT_MAX)
        attempts = 0
        max_zone_dist = self.RING_RADIUS - self.ZONE_RADIUS - 10
        while len(self.zones) < target_count and attempts < 200:
            attempts += 1
            angle = self._rng.random() * 2 * math.pi
            dist = self._rng.random() * max_zone_dist
            x = self.RING_CX + math.cos(angle) * dist
            y = self.RING_CY + math.sin(angle) * dist
            if dist > max_zone_dist - 1:
                continue
            if not self._zone_overlaps_existing(x, y):
                color = self._rng.choice(self.COLORS)
                life = self.ZONE_LIFE
                self.zones.append(PushZone(x=x, y=y, radius=self.ZONE_RADIUS, color=color, life=life))

    def _zone_overlaps_existing(self, x: float, y: float) -> bool:
        for z in self.zones:
            dx = x - z.x
            dy = y - z.y
            if dx * dx + dy * dy < self.ZONE_OVERLAP_MIN * self.ZONE_OVERLAP_MIN:
                return True
        return False

    def _update_zones(self) -> None:
        for z in self.zones:
            z.life -= 1
        self.zones = [z for z in self.zones if z.life > 0]

        self.zone_spawn_timer -= 1
        if self.zone_spawn_timer <= 0:
            self.zone_spawn_timer = self.ZONE_SPAWN_INTERVAL
            self._try_spawn_additional_zone()

    def _try_spawn_additional_zone(self) -> None:
        if len(self.zones) >= self.ZONE_COUNT_MAX:
            return
        max_zone_dist = self.RING_RADIUS - self.ZONE_RADIUS - 10
        for _ in range(30):
            angle = self._rng.random() * 2 * math.pi
            dist = self._rng.random() * max_zone_dist
            x = self.RING_CX + math.cos(angle) * dist
            y = self.RING_CY + math.sin(angle) * dist
            if dist > max_zone_dist + 1:
                continue
            if not self._zone_overlaps_existing(x, y):
                color = self._rng.choice(self.COLORS)
                self.zones.append(PushZone(x=x, y=y, radius=self.ZONE_RADIUS, color=color, life=self.ZONE_LIFE))
                break

    def _match_zone(self, wx: float, wy: float) -> int | None:
        threshold = self.WRESTLER_RADIUS + self.ZONE_RADIUS - 4
        for z in self.zones:
            dx = wx - z.x
            dy = wy - z.y
            if dx * dx + dy * dy < threshold * threshold:
                return z.color
        return None

    # --------------------------------------------------------------- Push

    def compute_push_power(self, combo: int, super_active: bool) -> float:
        if super_active:
            return self.SUPER_PUSH_POWER
        return self.BASE_PUSH_POWER * (1.0 + 0.2 * combo)

    def _do_push(
        self,
        pusher: Wrestler,
        target: Wrestler,
        matched_color: int | None,
    ) -> None:
        super_active = self.super_timer > 0

        if matched_color is not None:
            if super_active or self.last_color is None or matched_color == self.last_color:
                self.combo += 1
                self.max_combo = max(self.max_combo, self.combo)
                multiplier = 3 if super_active else 1
                gained = 10 * self.combo * multiplier
                self.score += gained
                self.last_color = matched_color
                self._spawn_score_text(target.x, target.y, gained)
                if self.combo >= 3:
                    self._spawn_combo_text(self.combo)
                if self.combo >= self.COMBO_THRESHOLD and self.super_timer <= 0:
                    self._activate_super()
            else:
                self.combo = 0
                self.last_color = matched_color
                self.heat += self.HEAT_MISMATCH
                gained = 10
                self.score += gained
                self._spawn_score_text(target.x, target.y, gained)
                self._spawn_wrong_text(target.x, target.y)
        else:
            self.combo = 0
            self.last_color = None

        power = self.compute_push_power(self.combo, super_active)
        dx = target.x - pusher.x
        dy = target.y - pusher.y
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            dx = math.cos(pusher.facing_angle)
            dy = math.sin(pusher.facing_angle)
            dist = 1.0
        nx = dx / dist
        ny = dy / dist

        target.x += nx * power
        target.y += ny * power

        if super_active:
            self._spawn_particles(target.x, target.y, random.choice(self.RAINBOW_COLORS), 16, 25)
        else:
            matched_clr = matched_color if matched_color is not None else 7
            self._spawn_particles(target.x, target.y, matched_clr, 10, 20)

    def _activate_super(self) -> None:
        self.super_timer = self.SUPER_DURATION
        self.float_texts.append(FloatText(
            self.SCR_W // 2, self.RING_CY - 40,
            "SUPER PUSH!", random.choice(self.RAINBOW_COLORS), 60,
        ))

    def _check_ring_out(self, x: float, y: float) -> bool:
        dx = x - self.RING_CX
        dy = y - self.RING_CY
        return dx * dx + dy * dy >= self.RING_RADIUS * self.RING_RADIUS

    def _clamp_to_ring(self, w: Wrestler) -> None:
        dx = w.x - self.RING_CX
        dy = w.y - self.RING_CY
        dist = math.hypot(dx, dy)
        max_dist = self.RING_RADIUS - w.radius
        if dist > max_dist:
            nx = dx / dist
            ny = dy / dist
            w.x = self.RING_CX + nx * max_dist
            w.y = self.RING_CY + ny * max_dist

    # --------------------------------------------------------------- AI

    def _update_ai(self) -> None:
        if self._check_ring_out(self.ai.x, self.ai.y):
            return

        dx_center = self.RING_CX - self.ai.x
        dy_center = self.RING_CY - self.ai.y
        dist_center = math.hypot(dx_center, dy_center)
        if dist_center > 30:
            nx = dx_center / dist_center
            ny = dy_center / dist_center
            self.ai.x += nx * 0.8
            self.ai.y += ny * 0.8
            self.ai.facing_angle = math.atan2(ny, nx)

        self.ai_push_timer -= 1
        if self.ai_push_timer <= 0:
            self.ai_push_timer = self._rng.randint(self.AI_PUSH_INTERVAL_MIN, self.AI_PUSH_INTERVAL_MAX)
            self._ai_push()

    def _ai_push(self) -> None:
        dx = self.player.x - self.ai.x
        dy = self.player.y - self.ai.y
        dist = math.hypot(dx, dy)

        if dist < self.WRESTLER_RADIUS * 2 + self.AI_PUSH_POWER + 10:
            nx = dx / dist if dist > 0 else 1.0
            ny = dy / dist if dist > 0 else 0.0
            self.player.x += nx * self.AI_PUSH_POWER
            self.player.y += ny * self.AI_PUSH_POWER
            self.heat += self.HEAT_AI_HIT
            self._spawn_particles(self.player.x, self.player.y, 13, 6, 15)
            self.float_texts.append(FloatText(
                self.player.x, self.player.y - 10, "PUSHED!", 8, 25,
            ))

    # ------------------------------------------------------------ Particles

    def _spawn_particles(self, x: float, y: float, color: int, count: int, base_life: int) -> None:
        for _ in range(count):
            angle = self._rng.random() * 2 * math.pi
            speed = self._rng.random() * 3 + 1
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=base_life + int(self._rng.random() * 20),
                color=color,
                size=2 + int(self._rng.random() * 3),
            ))

    def _spawn_score_text(self, x: float, y: float, gained: int) -> None:
        self.float_texts.append(FloatText(x, y - 8, f"+{gained}", 7, 30))

    def _spawn_combo_text(self, combo: int) -> None:
        color = self.RAINBOW_COLORS[combo % len(self.RAINBOW_COLORS)]
        self.float_texts.append(FloatText(
            self.SCR_W // 2, self.RING_CY - 60,
            f"COMBO x{combo}!", color, 45,
        ))

    def _spawn_wrong_text(self, x: float, y: float) -> None:
        self.float_texts.append(FloatText(x, y - 8, "WRONG!", 8, 30))

    def _spawn_ring_out_particles(self, x: float, y: float) -> None:
        for _ in range(30):
            angle = self._rng.random() * 2 * math.pi
            speed = self._rng.random() * 4 + 2
            clr = random.choice(self.RAINBOW_COLORS)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=30 + int(self._rng.random() * 30),
                color=clr,
                size=2 + int(self._rng.random() * 4),
            ))

    # ------------------------------------------------------------ Updates

    def _update_heat(self) -> None:
        if self.heat >= self.MAX_HEAT:
            self._end_game("HEAT OVERLOAD!")
            return
        self.heat = max(0.0, self.heat - self.HEAT_DECAY)

    def _update_particles(self) -> None:
        for p in self.particles:
            p.vy += 0.1
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_float_texts(self) -> None:
        for ft in self.float_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.float_texts = [ft for ft in self.float_texts if ft.life > 0]

    # --------------------------------------------------------- Game Loop

    def update(self) -> None:
        match self.phase:
            case "TITLE":
                self._update_title()
            case "PLAYING":
                self._update_playing()
            case "ROUND_WIN":
                self._update_round_win()
            case "GAME_OVER":
                self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._reset()
            self.phase = "PLAYING"

    def _update_playing(self) -> None:
        self._update_heat()
        if self.phase != "PLAYING":
            return

        self.timer -= 1
        if self.timer <= 0:
            self._end_game("TIME UP!")
            return

        if self.super_timer > 0:
            self.super_timer -= 1

        self._update_player_input()
        self._update_thrust()
        self._update_ai()
        self._update_zones()
        self._update_particles()
        self._update_float_texts()

        self._clamp_to_ring(self.player)
        self._clamp_to_ring(self.ai)

        if self._check_ring_out(self.ai.x, self.ai.y):
            self._on_ai_ring_out()
        elif self._check_ring_out(self.player.x, self.player.y):
            self._on_player_ring_out()

    def _update_player_input(self) -> None:
        if self.thrusting:
            return

        if pyxel.btn(pyxel.KEY_LEFT):
            self.player.facing_angle -= 0.07
        if pyxel.btn(pyxel.KEY_RIGHT):
            self.player.facing_angle += 0.07

        if pyxel.btn(pyxel.KEY_UP):
            self.player.x += math.cos(self.player.facing_angle) * self.PLAYER_SPEED
            self.player.y += math.sin(self.player.facing_angle) * self.PLAYER_SPEED
        if pyxel.btn(pyxel.KEY_DOWN):
            self.player.x -= math.cos(self.player.facing_angle) * self.PLAYER_SPEED
            self.player.y -= math.sin(self.player.facing_angle) * self.PLAYER_SPEED

        if pyxel.btnp(pyxel.KEY_SPACE):
            self.thrusting = True
            self.thrust_timer = self.thrust_duration
            self.player.x += math.cos(self.player.facing_angle) * self.PLAYER_SPEED * 2
            self.player.y += math.sin(self.player.facing_angle) * self.PLAYER_SPEED * 2
            self._resolve_push_collision()

    def _update_thrust(self) -> None:
        if not self.thrusting:
            return
        self.thrust_timer -= 1
        self.player.x += math.cos(self.player.facing_angle) * 2.0
        self.player.y += math.sin(self.player.facing_angle) * 2.0
        if self.thrust_timer <= 0:
            self.thrusting = False

    def _resolve_push_collision(self) -> None:
        dx = self.ai.x - self.player.x
        dy = self.ai.y - self.player.y
        dist = math.hypot(dx, dy)
        contact_dist = self.WRESTLER_RADIUS * 2 + 6

        if dist < contact_dist:
            matched_color = self._match_zone(self.player.x, self.player.y)
            self._do_push(self.player, self.ai, matched_color)

    def _on_ai_ring_out(self) -> None:
        self.rounds_won += 1
        self.score += 500
        self._spawn_ring_out_particles(self.ai.x, self.ai.y)
        self.float_texts.append(FloatText(
            self.SCR_W // 2, self.RING_CY - 30,
            "ROUND WIN!", 10, 60,
        ))
        self.phase = "ROUND_WIN"
        self.win_timer = 60

    def _on_player_ring_out(self) -> None:
        self._spawn_ring_out_particles(self.player.x, self.player.y)
        self._end_game("RING OUT!")

    def _update_round_win(self) -> None:
        self._update_particles()
        self._update_float_texts()
        self.win_timer -= 1  # type: ignore[attr-defined]
        if self.win_timer <= 0:  # type: ignore[attr-defined]
            self._reset_round()

    def _reset_round(self) -> None:
        self.phase = "PLAYING"
        self.player.x = self.RING_CX - 30.0
        self.player.y = self.RING_CY
        self.player.facing_angle = 0.0
        self.ai.x = self.RING_CX + 30.0
        self.ai.y = self.RING_CY
        self.ai.facing_angle = math.pi
        self.combo = 0
        self.last_color = None
        self.super_timer = 0
        self.thrusting = False
        self.thrust_timer = 0
        self.ai_push_timer = self._rng.randint(self.AI_PUSH_INTERVAL_MIN, self.AI_PUSH_INTERVAL_MAX)
        self._spawn_zones()

    def _end_game(self, reason: str) -> None:
        self.phase = "GAME_OVER"
        if self.score > self.best_score:
            self.best_score = self.score
        self.float_texts.append(FloatText(
            self.SCR_W // 2, self.RING_CY - 10,
            reason, 8, 90,
        ))

    def _update_game_over(self) -> None:
        self._update_particles()
        self._update_float_texts()
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._reset()
            self.phase = "TITLE"

    # --------------------------------------------------------------- Draw

    def draw(self) -> None:
        pyxel.cls(0)
        match self.phase:
            case "TITLE":
                self._draw_title()
            case "PLAYING":
                self._draw_playing()
            case "ROUND_WIN":
                self._draw_playing()
                self._draw_round_win_overlay()
            case "GAME_OVER":
                self._draw_playing()
                self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(self.SCR_W // 2 - 38, 40, "SUMO CHAIN", 7)
        pyxel.text(self.SCR_W // 2 - 55, 62, "Color-Match COMBO!", 11)
        pyxel.text(self.SCR_W // 2 - 75, 100, "LEFT/RIGHT: Turn", 7)
        pyxel.text(self.SCR_W // 2 - 75, 112, "UP/DOWN: Move", 7)
        pyxel.text(self.SCR_W // 2 - 75, 124, "SPACE: Push!", 7)
        pyxel.text(self.SCR_W // 2 - 80, 150, "Match 4 colors -> SUPER PUSH!", 10)
        pyxel.text(self.SCR_W // 2 - 70, 175, "Watch your HEAT meter!", 8)
        pyxel.text(self.SCR_W // 2 - 50, 210, "Press SPACE to start", 7)
        blink = (pyxel.frame_count // 30) % 2
        if blink:
            pyxel.text(self.SCR_W // 2 - 50, 210, "Press SPACE to start", 10)

    def _draw_ring(self) -> None:
        pyxel.circ(self.RING_CX, self.RING_CY, self.RING_RADIUS, 1)
        pyxel.circb(self.RING_CX, self.RING_CY, self.RING_RADIUS, 7)
        pyxel.circb(self.RING_CX, self.RING_CY, self.RING_RADIUS + 1, 5)

    def _draw_zones(self) -> None:
        for z in self.zones:
            alpha = z.life / self.ZONE_LIFE
            if alpha > 0.2:
                pyxel.circ(int(z.x), int(z.y), int(z.radius), z.color)
                pyxel.circb(int(z.x), int(z.y), int(z.radius), 7)

    def _draw_wrestler(self, w: Wrestler, is_player: bool) -> None:
        if is_player and self.super_timer > 0:
            clr_idx = (pyxel.frame_count // 4) % len(self.RAINBOW_COLORS)
            clr = self.RAINBOW_COLORS[clr_idx]
        elif is_player:
            clr = w.active_color
        else:
            clr = 13

        pyxel.circ(int(w.x), int(w.y), int(w.radius), clr)
        pyxel.circb(int(w.x), int(w.y), int(w.radius), 7)

        fx = w.x + math.cos(w.facing_angle) * (w.radius + 4)
        fy = w.y + math.sin(w.facing_angle) * (w.radius + 4)
        pyxel.line(int(w.x), int(w.y), int(fx), int(fy), 7)

        if is_player and self.thrusting:
            ex_x = w.x + math.cos(w.facing_angle) * (w.radius + 8)
            ex_y = w.y + math.sin(w.facing_angle) * (w.radius + 8)
            pyxel.rect(int(ex_x) - 2, int(ex_y) - 2, 4, 4, 10)

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, self.SCR_W, 14, 1)
        pyxel.text(2, 3, f"SCORE:{self.score}", 7)

        combo_text = f"COMBO:{self.combo}"
        pyxel.text(82, 3, combo_text, 7)

        heat_bar_x = 152
        heat_fill = int(50 * (self.heat / self.MAX_HEAT))
        pyxel.text(heat_bar_x, 3, "HEAT", 8)
        pyxel.rect(heat_bar_x + 26, 2, 50, 9, 5)
        pyxel.rect(heat_bar_x + 26, 2, heat_fill, 9, 8)

        if self.super_timer > 0:
            super_secs = self.super_timer // self.FPS
            clr_idx = (pyxel.frame_count // 4) % len(self.RAINBOW_COLORS)
            pyxel.text(236, 3, f"SUPER {super_secs}s", self.RAINBOW_COLORS[clr_idx])
        else:
            secs = max(0, self.timer // self.FPS)
            pyxel.text(290, 3, f"{secs:2d}s", 7)

        pyxel.text(2, 228, f"Rounds:{self.rounds_won}", 7)

    def _draw_playing(self) -> None:
        self._draw_ring()
        self._draw_zones()
        self._draw_wrestler(self.player, True)
        self._draw_wrestler(self.ai, False)
        self._draw_particles()
        self._draw_float_texts()
        self._draw_hud()

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 30
            if alpha > 0.3:
                pyxel.rect(int(p.x), int(p.y), p.size, p.size, p.color)

    def _draw_float_texts(self) -> None:
        for ft in self.float_texts:
            alpha = ft.life / 60
            if alpha > 0.2:
                pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_round_win_overlay(self) -> None:
        pyxel.text(self.SCR_W // 2 - 35, self.RING_CY - 40, "ROUND WIN!", 10)

    def _draw_game_over(self) -> None:
        pyxel.rect(self.SCR_W // 2 - 75, 45, 150, 100, 1)
        pyxel.rectb(self.SCR_W // 2 - 75, 45, 150, 100, 7)
        pyxel.text(self.SCR_W // 2 - 30, 52, "GAME OVER", 8)
        pyxel.text(self.SCR_W // 2 - 45, 72, f"SCORE: {self.score}", 7)
        pyxel.text(self.SCR_W // 2 - 48, 84, f"MAX COMBO: {self.max_combo}", 7)
        pyxel.text(self.SCR_W // 2 - 42, 96, f"ROUNDS: {self.rounds_won}", 7)
        pyxel.text(self.SCR_W // 2 - 50, 108, f"BEST: {self.best_score}", 10)
        pyxel.text(self.SCR_W // 2 - 50, 128, "Press SPACE to restart", 7)


if __name__ == "__main__":
    Game()
