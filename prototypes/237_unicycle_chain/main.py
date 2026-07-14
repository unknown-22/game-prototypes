"""Unicycle Chain — 237

Side-view unicycle balancing game. Pedal through colored rings while maintaining balance.
Build combos with matching colors, activate SUPER BALANCE at 4+ combo.
Manage HEAT (mismatch/fall penalty) and STAMINA (aggressive pedaling cost).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Ring:
    x: float
    y: float
    color: int
    passed: bool = False
    radius: int = 16


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class FloatText:
    x: float
    y: float
    text: str
    life: int
    color: int


@dataclass
class GhostPoint:
    tilt: float
    x: float
    y: float


class Game:
    _RING_COLORS: tuple[int, int, int, int] = (8, 11, 5, 10)
    GROUND_Y: int = 200
    UNI_X: float = 80.0
    RING_RADIUS: int = 16
    UNI_RADIUS: int = 12
    MAX_HEAT: float = 100.0
    MAX_STAMINA: float = 100.0
    GAME_DURATION: int = 60 * 60
    SUPER_DURATION: int = 300
    COMBO_THRESHOLD: int = 4

    TILT_GRAVITY: float = 0.0003
    TILT_INPUT: float = 0.008
    TILT_MAX: float = 0.6
    TILT_FALL_THRESHOLD: float = 0.55
    TILT_FALL_FRAMES: int = 30

    HEAT_MISMATCH: float = 15.0
    HEAT_FALL: float = 25.0
    HEAT_DECAY: float = 0.02

    STAMINA_DRAIN: float = 0.3
    STAMINA_RECHARGE: float = 0.08
    STAMINA_LOW_THRESHOLD: float = 20.0
    STAMINA_LOW_MULT: float = 0.5

    SPEED_MULT_PEDAL: float = 1.3

    _rng: random.Random
    _fall_frames: int
    _best_run_trail: list[GhostPoint]
    _best_run_score: int
    scroll_speed: float
    _frame: int

    phase: Phase
    score: int
    combo: int
    max_combo: int
    timer: int
    uni_x: float
    uni_y: float
    tilt: float
    tilt_vel: float
    rings: list[Ring]
    ring_color: int
    ring_color_timer: int
    ring_color_interval: int
    spawn_timer: int
    spawn_interval: int
    super_timer: int
    super_active: bool
    heat: float
    stamina: float
    ghost_trail: list[GhostPoint]
    best_score: int
    particles: list[Particle]
    floating_texts: list[FloatText]
    shake_frames: int
    stun_timer: int
    super_mult: int
    speed_mult: float

    def __new__(cls, *args: object, **kwargs: object) -> Game:
        instance = super().__new__(cls)
        instance.phase: Phase = Phase.TITLE
        instance.score: int = 0
        instance.combo: int = 0
        instance.max_combo: int = 0
        instance.timer: int = 0
        instance.uni_x: float = cls.UNI_X
        instance.uni_y: float = float(cls.GROUND_Y - 10)
        instance.tilt: float = 0.0
        instance.tilt_vel: float = 0.0
        instance.rings: list[Ring] = []
        instance.ring_color: int = cls._RING_COLORS[0]
        instance.ring_color_timer: int = 90
        instance.ring_color_interval: int = 90
        instance.spawn_timer: int = 0
        instance.spawn_interval: int = 70
        instance.super_timer: int = 0
        instance.super_active: bool = False
        instance.heat: float = 0.0
        instance.stamina: float = cls.MAX_STAMINA
        instance.ghost_trail: list[GhostPoint] = []
        instance.best_score: int = 0
        instance.particles: list[Particle] = []
        instance.floating_texts: list[FloatText] = []
        instance.shake_frames: int = 0
        instance.stun_timer: int = 0
        instance.super_mult: int = 1
        instance.speed_mult: float = 1.0
        instance._rng: random.Random = random.Random(42)
        instance._fall_frames: int = 0
        instance._best_run_trail: list[GhostPoint] = []
        instance._best_run_score: int = 0
        instance.scroll_speed: float = 1.5
        instance._frame: int = 0
        return instance

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.timer = 0
        self.uni_x = self.UNI_X
        self.uni_y = float(self.GROUND_Y - 10)
        self.tilt = 0.0
        self.tilt_vel = 0.0
        self.rings = []
        self.ring_color = self._RING_COLORS[0]
        self.ring_color_timer = 90
        self.ring_color_interval = 90
        self.spawn_timer = 0
        self.spawn_interval = 70
        self.super_timer = 0
        self.super_active = False
        self.heat = 0.0
        self.stamina = self.MAX_STAMINA
        self.ghost_trail = []
        self.particles = []
        self.floating_texts = []
        self.shake_frames = 0
        self.stun_timer = 0
        self.super_mult = 1
        self.speed_mult = 1.0
        self._fall_frames = 0
        self.scroll_speed = 1.5
        self._frame = 0

    def _start_playing(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.timer = self.GAME_DURATION
        self.uni_x = self.UNI_X
        self.uni_y = float(self.GROUND_Y - 10)
        self.tilt = 0.0
        self.tilt_vel = 0.0
        self.rings = []
        self.ring_color = self._RING_COLORS[0]
        self.ring_color_timer = 90
        self.ring_color_interval = 90
        self.spawn_timer = 0
        self.spawn_interval = 70
        self.super_timer = 0
        self.super_active = False
        self.heat = 0.0
        self.stamina = self.MAX_STAMINA
        self.ghost_trail = []
        self.particles = []
        self.floating_texts = []
        self.shake_frames = 0
        self.stun_timer = 0
        self.super_mult = 1
        self.speed_mult = 1.0
        self._fall_frames = 0
        self.scroll_speed = 1.5
        self._frame = 0

    def _update_unicycle(self, delta_balance: float, pedaling: bool) -> None:
        input_effectiveness = 1.0
        if self.stamina < self.STAMINA_LOW_THRESHOLD:
            input_effectiveness = self.STAMINA_LOW_MULT

        self.tilt_vel += delta_balance * self.TILT_INPUT * input_effectiveness

        gravity_dir = 1.0 if self.tilt > 0 else -1.0
        self.tilt_vel += gravity_dir * self.TILT_GRAVITY

        self.tilt += self.tilt_vel

        if self.tilt > self.TILT_MAX:
            self.tilt = self.TILT_MAX
        elif self.tilt < -self.TILT_MAX:
            self.tilt = -self.TILT_MAX

        if abs(self.tilt) >= self.TILT_FALL_THRESHOLD:
            self._fall_frames += 1
        else:
            self._fall_frames = 0

        if self._fall_frames >= self.TILT_FALL_FRAMES:
            self.heat += self.HEAT_FALL
            self._fall_frames = 0
            self.tilt = 0.0
            self.tilt_vel = 0.0
            self.stun_timer = 15
            self.shake_frames = 10
            self._add_particles(self.uni_x, self.uni_y, 10, 4)

        self.uni_y = self.GROUND_Y - 10 + self.tilt * 30

    def _spawn_ring(self) -> None:
        y = self._rng.uniform(80, 180)
        color = self._rng.choice(self._RING_COLORS)
        self.rings.append(Ring(x=330.0, y=y, color=color))

    def _update_rings(self) -> None:
        for ring in self.rings:
            ring.x -= self.scroll_speed * self.speed_mult
        self.rings = [r for r in self.rings if r.x > -30]

    def _check_ring_pass(self) -> tuple[int, bool]:
        if not self.rings:
            return 0, False

        matched = 0
        mismatch = False
        for ring in self.rings:
            if ring.passed:
                continue
            dx = abs(self.uni_x - ring.x)
            dy = abs(self.uni_y - ring.y)
            threshold = float(self.UNI_RADIUS + ring.radius)
            if dx < threshold and dy < threshold:
                ring.passed = True
                if self.super_active or ring.color == self.ring_color:
                    matched += 1
                else:
                    mismatch = True
                break
        return matched, mismatch

    def _update_color_cycle(self) -> None:
        self.ring_color_timer -= 1
        if self.ring_color_timer <= 0:
            colors = self._RING_COLORS
            current_idx = colors.index(self.ring_color)
            next_idx = (current_idx + 1) % len(colors)
            self.ring_color = colors[next_idx]
            self.ring_color_timer = self.ring_color_interval

    def _activate_super(self) -> None:
        self.super_active = True
        self.super_timer = self.SUPER_DURATION
        self.super_mult = 3
        self.combo = 0
        self._add_particles(self.uni_x, self.uni_y, 20, 8)
        self._add_floating_text(160, 120, "SUPER!", 14)
        self.shake_frames = 5

    def _deactivate_super(self) -> None:
        self.super_active = False
        self.super_timer = 0
        self.super_mult = 1

    def _update_heat(self) -> None:
        if self.heat >= self.MAX_HEAT:
            self.heat = self.MAX_HEAT
            self._end_game()
            return
        self.heat = max(0.0, self.heat - self.HEAT_DECAY)

    def _update_stamina(self, pedaling: bool) -> None:
        if pedaling:
            self.stamina = max(0.0, self.stamina - self.STAMINA_DRAIN)
            self.speed_mult = self.SPEED_MULT_PEDAL
        else:
            self.stamina = min(
                self.MAX_STAMINA, self.stamina + self.STAMINA_RECHARGE
            )
            self.speed_mult = 1.0

    def _end_game(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self._best_run_score:
            self._best_run_score = self.score
            self._best_run_trail = list(self.ghost_trail)
        if self.score > self.best_score:
            self.best_score = self.score

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.8
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _add_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-2.5, 2.5)
            vy = self._rng.uniform(-2.5, 2.5)
            life = self._rng.randint(10, 25)
            self.particles.append(
                Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color)
            )

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(
            FloatText(x=x, y=y, text=text, life=35, color=color)
        )

    def _update_ghost_trail(self) -> None:
        if self._frame % 3 == 0:
            self.ghost_trail.append(
                GhostPoint(tilt=self.tilt, x=self.uni_x, y=self.uni_y)
            )

    def _update_difficulty(self) -> None:
        elapsed = self.GAME_DURATION - self.timer
        seconds = elapsed / 60.0
        self.scroll_speed = 1.5 + seconds * 0.02
        self.spawn_interval = max(30, int(70 - seconds * (40.0 / 60.0)))
        self.ring_color_interval = max(40, int(90 - seconds))

    def _update_playing(self) -> None:
        if self.phase != Phase.PLAYING:
            return
        self._frame += 1

        if self.stun_timer > 0:
            self.stun_timer -= 1
            self._update_particles()
            self._update_floating_texts()
            if self.shake_frames > 0:
                self.shake_frames -= 1
            self._update_heat()
            if self.timer > 0:
                self.timer -= 1
            if self.timer <= 0:
                self._end_game()
            return

        delta_balance = 0.0
        if pyxel.btn(pyxel.KEY_LEFT):
            delta_balance -= 1.0
        if pyxel.btn(pyxel.KEY_RIGHT):
            delta_balance += 1.0
        pedaling = pyxel.btn(pyxel.KEY_UP)

        self._update_unicycle(delta_balance, pedaling)
        self._update_stamina(pedaling)
        self._update_heat()

        if self.phase != Phase.PLAYING:
            return

        self._update_rings()
        self._update_color_cycle()
        self._update_difficulty()
        self._update_particles()
        self._update_floating_texts()

        matched, mismatch = self._check_ring_pass()

        if not self.super_active:
            self.combo += matched
            if mismatch:
                self.heat += self.HEAT_MISMATCH
                if self.combo > 0:
                    self.combo = 0
                self.stun_timer = 15
                self._add_particles(self.uni_x, self.uni_y, 5, 13)
                self._add_floating_text(self.uni_x - 10, self.uni_y - 20, "MISS!", 8)

            if matched > 0:
                points = 10 * self.combo * self.super_mult
                self.score += int(points)
                if self.combo > self.max_combo:
                    self.max_combo = self.combo
                self._add_particles(self.uni_x, self.uni_y, 8, self.ring_color)
                self._add_floating_text(
                    self.uni_x - 10, self.uni_y - 30, f"+{int(points)}", 7
                )
                if self.combo >= 2:
                    self._add_floating_text(
                        self.uni_x + 20, self.uni_y - 40,
                        f"COMBO x{self.combo}", 14
                    )
                if self.combo >= self.COMBO_THRESHOLD:
                    self._activate_super()
        else:
            if matched > 0:
                points = 10 * self.super_mult
                self.score += int(points)
                self._add_particles(self.uni_x, self.uni_y, 8, self.ring_color)
                self._add_floating_text(
                    self.uni_x - 10, self.uni_y - 30, f"+{int(points)}", 7
                )
            self.super_timer -= 1
            if self.super_timer <= 0:
                self._deactivate_super()

        if self.timer > 0:
            self.timer -= 1
        if self.timer <= 0:
            self._end_game()

        self._update_ghost_trail()

        if self.spawn_timer <= 0 and self.phase == Phase.PLAYING:
            self._spawn_ring()
            self.spawn_timer = max(
                20,
                self._rng.randint(
                    self.spawn_interval - 10, self.spawn_interval + 10
                ),
            )
        elif self.phase == Phase.PLAYING:
            self.spawn_timer -= 1

        if self.shake_frames > 0:
            self.shake_frames -= 1
            ox = self._rng.randint(-2, 2)
            oy = self._rng.randint(-2, 2)
            pyxel.camera(ox, oy)
        else:
            pyxel.camera(0, 0)

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self._start_playing()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()

    def _draw_title(self) -> None:
        pyxel.cls(0)
        pyxel.text(95, 50, "UNICYCLE CHAIN", 7)
        pyxel.text(100, 66, "Balance & Combo!", 11)
        pyxel.text(70, 100, "LEFT / RIGHT : Balance", 7)
        pyxel.text(70, 112, "UP           : Pedal (-STA)", 7)
        pyxel.text(70, 124, "Match ring color = COMBO", 7)
        pyxel.text(70, 136, "4+ COMBO = SUPER BALANCE", 14)
        pyxel.text(82, 160, "Survive 60 seconds!", 7)
        if self.best_score > 0:
            pyxel.text(140, 180, f"BEST: {self.best_score}", 10)
        pyxel.text(108, 210, "PRESS SPACE", 7)

    def _draw_playing(self) -> None:
        pyxel.cls(0)

        if self.super_active and (pyxel.frame_count // 8) % 2 == 0:
            pyxel.rectb(0, 0, 320, 240, 14)

        if self._best_run_trail:
            for i, gp in enumerate(self._best_run_trail):
                if i % 6 != 0:
                    continue
                px = int(gp.x)
                py = int(gp.y)
                if 0 <= px < 320 and 0 <= py < 240:
                    pyxel.pset(px, py, 12)

        for ring in self.rings:
            rx = int(ring.x)
            ry = int(ring.y)
            pyxel.circb(rx, ry, ring.radius, ring.color)
            if not ring.passed:
                pyxel.circb(rx, ry, ring.radius - 2, ring.color)

        pyxel.line(0, self.GROUND_Y, 320, self.GROUND_Y, 4)

        ux = int(self.uni_x)
        uy = int(self.uni_y)

        wheel_frame = pyxel.frame_count * 0.15
        for spoke_i in range(8):
            angle = wheel_frame + spoke_i * math.pi / 4
            inner_r = 3.0
            outer_r = 9.0
            x1 = ux + inner_r * math.cos(angle)
            y1 = uy + inner_r * math.sin(angle)
            x2 = ux + outer_r * math.cos(angle)
            y2 = uy + outer_r * math.sin(angle)
            pyxel.line(int(x1), int(y1), int(x2), int(y2), 13)
        pyxel.circb(ux, uy, 10, 13)

        frame_angle = self.tilt
        frame_top_x = ux + 16 * math.sin(frame_angle)
        frame_top_y = uy - 16 * math.cos(frame_angle)
        pyxel.line(ux, uy, int(frame_top_x), int(frame_top_y), 13)

        seat_w = 6.0
        sx1 = frame_top_x - seat_w * math.cos(frame_angle)
        sy1 = frame_top_y - seat_w * math.sin(frame_angle)
        sx2 = frame_top_x + seat_w * math.cos(frame_angle)
        sy2 = frame_top_y + seat_w * math.sin(frame_angle)
        pyxel.line(int(sx1), int(sy1), int(sx2), int(sy2), 15)

        rider_cx = frame_top_x - 7 * math.cos(frame_angle)
        rider_cy = frame_top_y - 7 * math.sin(frame_angle)
        pyxel.circ(int(rider_cx), int(rider_cy), 5, 15)
        body_bottom_x = rider_cx
        body_bottom_y = rider_cy + 12
        pyxel.line(
            int(rider_cx), int(rider_cy) + 5,
            int(body_bottom_x), int(body_bottom_y), 15
        )

        for p in self.particles:
            if p.life > 5:
                pyxel.pset(int(p.x), int(p.y), p.color)

        for ft in self.floating_texts:
            if ft.life > 5:
                pyxel.text(int(ft.x), int(ft.y), ft.text, ft.color)

        pyxel.text(4, 2, f"SCORE: {self.score}", 7)
        pyxel.text(4, 12, f"COMBO: {self.combo}", 11)
        sec = max(0, self.timer // 60)
        pyxel.text(4, 22, f"TIME: {sec}", 7)

        color_names = {8: "RED", 11: "LIME", 5: "BLUE", 10: "YELLOW"}
        label = color_names.get(self.ring_color, "???")
        pyxel.text(245, 2, f"RING: {label}", self.ring_color)

        bar_x = 4
        bar_y = 34
        bar_w = 80
        bar_h = 6

        heat_w = int(bar_w * (self.heat / self.MAX_HEAT))
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, 0)
        pyxel.rect(bar_x, bar_y, heat_w, bar_h, 2)
        heat_label = "HEAT" if self.heat < 70 else "HEAT!"
        hc = 7 if self.heat < 70 else 8
        pyxel.text(bar_x + 2, bar_y + 1, heat_label, hc)

        stam_w = int(bar_w * (self.stamina / self.MAX_STAMINA))
        pyxel.rect(bar_x, bar_y + bar_h + 2, bar_w, bar_h, 0)
        pyxel.rect(bar_x, bar_y + bar_h + 2, stam_w, bar_h, 9)
        stam_label = "STAM" if self.stamina >= 20 else "STAM!"
        sc = 7 if self.stamina >= 20 else 8
        pyxel.text(bar_x + 2, bar_y + bar_h + 3, stam_label, sc)

        if self.super_active:
            rem = max(0, self.super_timer // 60)
            pyxel.text(120, 2, f"SUPER! {rem}s", 14)

        if self.stun_timer > 0:
            pyxel.text(
                int(self.uni_x) - 10, int(self.uni_y) - 30, "STUN", 8
            )

    def _draw_game_over(self) -> None:
        pyxel.cls(0)
        pyxel.text(120, 70, "GAME OVER", 8)
        pyxel.text(105, 95, f"SCORE: {self.score}", 7)
        pyxel.text(105, 107, f"MAX COMBO: {self.max_combo}", 11)
        best = max(self.best_score, self.score)
        pyxel.text(105, 119, f"BEST: {best}", 10)
        cause = "TIME UP" if self.timer <= 0 else "OVERHEAT"
        pyxel.text(112, 135, cause, 8 if cause == "OVERHEAT" else 7)
        pyxel.text(85, 160, "PRESS SPACE TO RETRY", 7)

    def draw(self) -> None:
        pyxel.camera(0, 0)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()


def main() -> None:
    pyxel.init(320, 240, title="Unicycle Chain", display_scale=2)
    game = Game()
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
