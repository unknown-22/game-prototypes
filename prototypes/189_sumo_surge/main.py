from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum

import pyxel

# Color constants
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

# Game constants
WRESTLER_RADIUS = 14
RING_CX = 160
RING_CY = 120
RING_RADIUS = 100
COLORS = [RED, GREEN, DARK_BLUE, YELLOW]
SUPER_COLORS = [RED, GREEN, DARK_BLUE, YELLOW, ORANGE, CYAN, PINK, LIME]
CHARGE_FORCE_BASE = 4.0
HEAT_MISMATCH = 15.0
HEAT_MAX = 100.0
HEAT_DECAY = 0.05
SUPER_DURATION = 300
CHARGE_COOLDOWN = 15
GAME_TIME = 60 * 60
COLOR_CYCLE_SPEED = 45
OPP_CHARGE_INTERVAL_BASE = 90
MOVE_SPEED = 2.0
DIAGONAL_SPEED = 2.0 / math.sqrt(2)


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    gravity: float = 0.0


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


class Phase(Enum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


class Game:
    def __init__(self) -> None:
        pyxel.init(320, 240, "Sumo Surge", display_scale=2)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.TITLE

        # Player state
        self.px: float = RING_CX
        self.py: float = RING_CY + 60
        self.p_color_idx: int = 0
        self.charge_cooldown: int = 0
        self.charging: bool = False
        self.charge_dir_x: float = 0.0
        self.charge_dir_y: float = 0.0
        self.invuln_frames: int = 0

        # Opponent state
        self.ox: float = RING_CX
        self.oy: float = RING_CY - 50
        self.o_color_idx: int = 2
        self.o_vx: float = 0.0
        self.o_vy: float = 0.0
        self.o_hp: float = 10.0

        # Game state
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.ko_count: int = 0
        self.round_num: int = 1
        self.game_timer: int = GAME_TIME
        self.game_over_reason: str = ""

        # SUPER MODE
        self.super_mode: bool = False
        self.super_timer: int = 0

        # Animation
        self.anim_timer: int = 0
        self.anim_type: str = ""

        # Effects
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shake_frames: int = 0
        self.shake_intensity: int = 0

        # Color cycling
        self.color_timer: int = 0

        # Difficulty
        self.opponent_speed: float = 0.6
        self.opponent_aggression: float = 0.3
        self.opp_charge_timer: int = 0

    # --- Core utility methods ---

    @staticmethod
    def _distance(x1: float, y1: float, x2: float, y2: float) -> float:
        return math.hypot(x1 - x2, y1 - y2)

    @staticmethod
    def _is_in_ring(x: float, y: float) -> bool:
        return (x - RING_CX) ** 2 + (y - RING_CY) ** 2 <= RING_RADIUS**2

    @staticmethod
    def _clamp_to_ring(x: float, y: float) -> tuple[float, float]:
        dx = x - RING_CX
        dy = y - RING_CY
        dist = math.hypot(dx, dy)
        if dist > RING_RADIUS - WRESTLER_RADIUS and dist > 0:
            scale = (RING_RADIUS - WRESTLER_RADIUS) / dist
            return RING_CX + dx * scale, RING_CY + dy * scale
        return x, y

    def _charge_direction(self) -> tuple[float, float]:
        dx = self.ox - self.px
        dy = self.oy - self.py
        dist = math.hypot(dx, dy)
        if dist < 0.01:
            return 0.0, -1.0
        return dx / dist, dy / dist

    def _apply_push(self, force_x: float, force_y: float, target_x: float, target_y: float) -> tuple[float, float]:
        return target_x + force_x, target_y + force_y

    def _check_ko(self, x: float, y: float) -> bool:
        return not self._is_in_ring(x, y)

    # --- Color cycling ---

    def _cycle_colors(self) -> None:
        self.color_timer += 1
        if self.color_timer >= COLOR_CYCLE_SPEED:
            self.color_timer = 0
            self.p_color_idx = (self.p_color_idx + 1) % len(COLORS)
            self.o_color_idx = (self.o_color_idx + 1) % len(COLORS)

    # --- Charge resolution ---

    def _resolve_charge(self) -> None:
        if self.super_mode:
            matched = True
            match_color = COLORS[self.p_color_idx]
        else:
            matched = self.p_color_idx == self.o_color_idx
            match_color = COLORS[self.p_color_idx]

        dir_x, dir_y = self._charge_direction()

        if matched:
            force_mult = 1.0 + 0.25 * self.combo
            if self.super_mode:
                force_mult = 3.0
            force_x = dir_x * CHARGE_FORCE_BASE * force_mult
            force_y = dir_y * CHARGE_FORCE_BASE * force_mult
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            points = int(100 * (1.0 + 0.5 * self.combo) * (3.0 if self.super_mode else 1.0))
            self.score += points
            self.ox, self.oy = self._apply_push(force_x, force_y, self.ox, self.oy)
            # Don't clamp yet — allow KO to be detected first
            self._spawn_push_particles(
                (self.px + self.ox) / 2, (self.py + self.oy) / 2, match_color, 8
            )
            self._spawn_floating_text(
                (self.px + self.ox) / 2, (self.py + self.oy) / 2 - 8,
                f"+{self.combo} COMBO!", match_color
            )
            self._spawn_floating_text(
                (self.px + self.ox) / 2, (self.py + self.oy) / 2 - 20,
                f"+{points}", YELLOW
            )
            if not self.super_mode and self.combo >= 4:
                self._activate_super()
            self.shake_frames = 4
            self.shake_intensity = 2
        else:
            self.heat = min(HEAT_MAX, self.heat + HEAT_MISMATCH)
            self.combo = 0
            self._spawn_push_particles(
                (self.px + self.ox) / 2, (self.py + self.oy) / 2, RED, 5
            )
            self._spawn_floating_text(
                (self.px + self.ox) / 2, (self.py + self.oy) / 2 - 8,
                "HEAT!", RED
            )
            if self.heat >= 70:
                self._spawn_floating_text(self.px, self.py - 20, "HEAT!", RED)

        # Check KO BEFORE clamping — clamp keeps opponent inside ring
        if self._check_ko(self.ox, self.oy):
            self._on_ko()
        else:
            self.ox, self.oy = self._clamp_to_ring(self.ox, self.oy)

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self._spawn_floating_text(self.px, self.py - 24, "SUPER!", WHITE)
        for _ in range(12):
            self.particles.append(Particle(
                x=self.px, y=self.py,
                vx=random.uniform(-2.0, 2.0),
                vy=random.uniform(-2.0, 2.0),
                life=random.randint(20, 30),
                color=random.choice(SUPER_COLORS),
                gravity=0.0,
            ))

    def _on_ko(self) -> None:
        self.ko_count += 1
        self.score += 500
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        self._spawn_ko_particles(self.ox, self.oy)
        self._spawn_floating_text(self.ox, self.oy - 10, "KO!", WHITE)
        self._spawn_floating_text(self.ox, self.oy - 25, "+500", YELLOW)
        self.shake_frames = 8
        self.shake_intensity = 4
        self.anim_timer = 30
        self.anim_type = "ko"
        self.combo = 0
        self.round_num += 1
        self._spawn_opponent(self.round_num)

    # --- Heat ---

    def _update_heat(self) -> None:
        # Check threshold BEFORE decay (tightrope-surge pitfall)
        if self.heat >= HEAT_MAX:
            self.game_over_reason = "OVERHEAT!"
            self.phase = Phase.GAME_OVER
            return
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)

    # --- SUPER MODE ---

    def _update_super_mode(self) -> None:
        if not self.super_mode:
            return
        self.super_timer -= 1
        if self.super_timer <= 0:
            self.super_mode = False
            self.super_timer = 0

    # --- Opponent AI ---

    def _spawn_opponent(self, round_num: int) -> None:
        angle = random.uniform(0, math.pi * 2)
        dist = random.uniform(30, RING_RADIUS - 60)
        self.ox = RING_CX + math.cos(angle) * dist
        self.oy = RING_CY + math.sin(angle) * dist
        self.o_color_idx = random.randint(0, len(COLORS) - 1)
        self.o_hp = 10.0 + (round_num - 1) * 3.0
        self.o_vx = 0.0
        self.o_vy = 0.0
        self.opponent_speed = 0.6 + (round_num - 1) * 0.15
        self.opponent_aggression = min(0.3 + (round_num - 1) * 0.1, 0.8)
        self.opp_charge_timer = max(30, OPP_CHARGE_INTERVAL_BASE - (round_num - 1) * 15)

    def _update_opponent_ai(self) -> None:
        dist = self._distance(self.px, self.oy, self.ox, self.oy)

        dir_x = 0.0
        dir_y = 0.0
        if dist > WRESTLER_RADIUS * 3:
            if dist > 0.01:
                dir_x = (self.px - self.ox) / dist
                dir_y = (self.py - self.oy) / dist
            self.ox += dir_x * self.opponent_speed
            self.oy += dir_y * self.opponent_speed

        self.ox, self.oy = self._clamp_to_ring(self.ox, self.oy)

        self.opp_charge_timer -= 1
        if self.opp_charge_timer <= 0:
            if dist < WRESTLER_RADIUS * 6 and random.random() < self.opponent_aggression:
                dx = self.px - self.ox
                dy = self.py - self.oy
                if dist > 0.01:
                    dx /= dist
                    dy /= dist
                push_strength = CHARGE_FORCE_BASE * 0.4
                self.px += dx * push_strength * 0.3
                self.py += dy * push_strength * 0.3
                self.px, self.py = self._clamp_to_ring(self.px, self.py)
            self.opp_charge_timer = max(30, OPP_CHARGE_INTERVAL_BASE - (self.round_num - 1) * 15)

    # --- Particles ---

    def _spawn_push_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.0, 3.0)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=random.randint(15, 25),
                color=color,
                gravity=0.0,
            ))

    def _spawn_ko_particles(self, x: float, y: float) -> None:
        for _ in range(20):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.5, 4.0)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=random.randint(20, 35),
                color=random.choice(SUPER_COLORS),
                gravity=0.05,
            ))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(
            x=x, y=y,
            text=text,
            life=30,
            color=color,
        ))

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += p.gravity
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def _update_floating_texts(self) -> None:
        alive: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life > 0:
                alive.append(ft)
        self.floating_texts = alive

    # --- Update ---

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.PLAYING

    def _update_playing(self) -> None:
        if self.anim_timer > 0:
            self.anim_timer -= 1
            if self.anim_timer <= 0:
                self.anim_type = ""
            self._update_particles()
            self._update_floating_texts()
            if self.shake_frames > 0:
                self.shake_frames -= 1
            return

        self.game_timer -= 1
        if self.game_timer <= 0:
            self.game_over_reason = "TIME UP!"
            self.phase = Phase.GAME_OVER
            return

        self._cycle_colors()
        self._update_super_mode()

        dx = 0.0
        dy = 0.0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx -= 1.0
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx += 1.0
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy -= 1.0
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy += 1.0

        if dx != 0.0 and dy != 0.0:
            dx *= DIAGONAL_SPEED
            dy *= DIAGONAL_SPEED
        else:
            dx *= MOVE_SPEED
            dy *= MOVE_SPEED

        self.px += dx
        self.py += dy
        self.px, self.py = self._clamp_to_ring(self.px, self.py)

        if self.invuln_frames > 0:
            self.invuln_frames -= 1

        if self.charge_cooldown > 0:
            self.charge_cooldown -= 1

        if pyxel.btnp(pyxel.KEY_SPACE) and self.charge_cooldown <= 0:
            self.charging = True
            self.charge_dir_x, self.charge_dir_y = self._charge_direction()
            self._resolve_charge()
            self.charge_cooldown = CHARGE_COOLDOWN
        else:
            self.charging = False

        self._update_opponent_ai()
        self._update_heat()
        self._update_particles()
        self._update_floating_texts()

        if self.shake_frames > 0:
            self.shake_frames -= 1

    def _update_game_over(self) -> None:
        self._update_particles()
        self._update_floating_texts()
        if self.shake_frames > 0:
            self.shake_frames -= 1
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()
            self.phase = Phase.TITLE

    # --- Draw ---

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.shake_frames > 0:
            sx = random.randint(-self.shake_intensity, self.shake_intensity)
            sy = random.randint(-self.shake_intensity, self.shake_intensity)
            pyxel.camera(sx, sy)
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(RING_CX - 35, 60, "SUMO SURGE", WHITE)
        pyxel.text(RING_CX - 75, 110, "Push foes out of the ring!", WHITE)
        pyxel.text(RING_CX - 70, 130, "Match colors for COMBO!", WHITE)
        pyxel.text(RING_CX - 70, 150, "COMBO x4 = SUPER CHARGE", WHITE)
        pyxel.text(RING_CX - 80, 180, "Arrow keys: Move  SPACE: Charge", GRAY)
        pyxel.text(RING_CX - 55, 210, "Press ENTER to start", YELLOW)

    def _draw_playing(self) -> None:
        self._draw_ring()

        if self.anim_type != "ko" or self.anim_timer % 4 < 2:
            self._draw_wrestler(self.ox, self.oy, COLORS[self.o_color_idx], is_player=False)

        self._draw_wrestler(self.px, self.py, self._player_draw_color(), is_player=True)

        for p in self.particles:
            alpha = p.life / 35
            col = p.color if alpha > 0.5 else (p.color if random.random() < alpha * 2 else BLACK)
            pyxel.pset(int(p.x), int(p.y), col)

        for ft in self.floating_texts:
            if ft.life > 0:
                col = ft.color
                if ft.life < 8:
                    if ft.life % 2 == 0:
                        continue
                pyxel.text(int(ft.x - len(ft.text) * 2), int(ft.y), ft.text, col)

        self._draw_hud()

    def _draw_ring(self) -> None:
        pyxel.circ(RING_CX, RING_CY, RING_RADIUS, BROWN)
        pyxel.circb(RING_CX, RING_CY, RING_RADIUS, WHITE)
        pyxel.circb(RING_CX, RING_CY, RING_RADIUS + 2, WHITE)

    def _draw_wrestler(self, x: float, y: float, body_color: int, *, is_player: bool) -> None:
        pyxel.circ(int(x), int(y), WRESTLER_RADIUS, GRAY)
        pyxel.circ(int(x), int(y), WRESTLER_RADIUS - 2, body_color)
        belt_y = -4 if is_player else 1
        pyxel.rect(int(x) - 8, int(y) + belt_y, 16, 3, WHITE)
        arm_y = -11 if is_player else 8
        pyxel.line(int(x) - 10, int(y) + arm_y, int(x) - 6, int(y) + arm_y + 3, WHITE)
        pyxel.line(int(x) + 10, int(y) + arm_y, int(x) + 6, int(y) + arm_y + 3, WHITE)

    def _player_draw_color(self) -> int:
        if self.super_mode:
            idx = (pyxel.frame_count // 6) % len(SUPER_COLORS)
            return SUPER_COLORS[idx]
        return COLORS[self.p_color_idx]

    def _draw_hud(self) -> None:
        pyxel.text(4, 2, f"Score: {self.score}", WHITE)
        pyxel.text(4, 11, f"Combo: {self.combo}", WHITE)
        pyxel.text(4, 20, f"KOs: {self.ko_count}", WHITE)

        secs = max(0, self.game_timer // 60)
        pyxel.text(RING_CX + RING_RADIUS - 30, 2, f"TIME: {secs}s", WHITE)

        bar_x = 60
        bar_y = 225
        bar_w = 200
        bar_h = 8
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        fill = int(bar_w * self.heat / HEAT_MAX)
        heat_color = RED if self.heat < 70 else (ORANGE if self.heat < 90 else RED)
        pyxel.rect(bar_x, bar_y, fill, bar_h, heat_color)
        pyxel.text(bar_x + bar_w + 4, bar_y - 1, "HEAT", GRAY)

        if self.super_mode:
            super_color = SUPER_COLORS[(pyxel.frame_count // 8) % len(SUPER_COLORS)]
            pyxel.text(RING_CX - 14, 30, "SUPER!", super_color)

    def _draw_game_over(self) -> None:
        pyxel.text(RING_CX - 45, 60, "GAME OVER", WHITE)
        pyxel.text(RING_CX - len(self.game_over_reason) * 2, 90, self.game_over_reason, RED)
        pyxel.text(RING_CX - 40, 120, f"Final Score: {self.score}", WHITE)
        pyxel.text(RING_CX - 55, 140, f"KOs: {self.ko_count}  Max Combo: {self.max_combo}", WHITE)
        pyxel.text(RING_CX - 55, 190, "Press ENTER to retry", YELLOW)

        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)
        for ft in self.floating_texts:
            if ft.life > 0:
                pyxel.text(int(ft.x - len(ft.text) * 2), int(ft.y), ft.text, ft.color)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
