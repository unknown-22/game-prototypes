"""
LIFT CHAIN - Color-match Olympic weightlifting

Hold SPACE to build power, release at the right timing to complete a lift.
Same-color consecutive successful lifts build a COMBO chain.
COMBO >= 4 triggers SUPER LIFT (rainbow plates, auto-perfect timing, 3x score).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# --- Constants ---
SCREEN_W = 320
SCREEN_H = 240

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

MAX_HEAT = 100.0
PLATE_COLORS: list[int] = [RED, GREEN, YELLOW, CYAN]
NUM_COLORS = 4
COMBO_FOR_SUPER = 4
SUPER_DURATION = 150
RESULT_DURATION = 30
LOCKOUT_DURATION = 30
POWER_RATE = 0.02
INITIAL_WEIGHT = 100
WEIGHT_INCREMENT = 25
INITIAL_TARGET_WIDTH = 0.30
MIN_TARGET_WIDTH = 0.08
HEAT_MISS = 15.0
HEAT_WRONG_COLOR = 5.0
HEAT_DECAY = 0.05

COLOR_NAMES = ["RED", "GREEN", "YELLOW", "CYAN"]


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class PlaySubPhase(Enum):
    AWAIT_LIFT = auto()
    POWERING = auto()
    LOCKOUT = auto()
    RESULT = auto()


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


class Game:
    _rng: random.Random

    def __new__(cls) -> Game:
        obj = super().__new__(cls)
        obj.phase: Phase = Phase.TITLE
        obj.sub_phase: PlaySubPhase = PlaySubPhase.AWAIT_LIFT
        obj.score: int = 0
        obj.combo: int = 0
        obj.max_combo: int = 0
        obj.heat: float = 0.0
        obj.plate_color: int = 0
        obj.prev_plate_color: int = 0
        obj.weight: int = INITIAL_WEIGHT
        obj.power: float = 0.0
        obj.power_rate: float = POWER_RATE
        obj.target_center: float = 0.5
        obj.target_width: float = INITIAL_TARGET_WIDTH
        obj.super_timer: int = 0
        obj.result_timer: int = 0
        obj.lockout_timer: int = 0
        obj.last_result: str = ""
        obj.last_score_gain: int = 0
        obj.particles: list[Particle] = []
        obj.frames: int = 0
        obj.high_score: int = 0
        obj.blink_timer: int = 0
        obj._rng = random.Random()
        return obj

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, "LIFT CHAIN", display_scale=2, fps=30)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.sub_phase = PlaySubPhase.AWAIT_LIFT
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.plate_color = 0
        self.prev_plate_color = 0
        self.weight = INITIAL_WEIGHT
        self.power = 0.0
        self.power_rate = POWER_RATE
        self.target_center = self._random_target_center()
        self.target_width = INITIAL_TARGET_WIDTH
        self.super_timer = 0
        self.result_timer = 0
        self.lockout_timer = 0
        self.last_result = ""
        self.last_score_gain = 0
        self.particles: list[Particle] = []
        self.frames = 0
        self.blink_timer = 0

    # --- Testable Logic Methods ---

    def _random_target_center(self) -> float:
        return self._rng.uniform(0.3, 0.7)

    def _start_lift(self) -> None:
        self.prev_plate_color = self.plate_color
        if self.super_timer > 0:
            self.plate_color = self.prev_plate_color
        else:
            if self.combo >= 2 and self._rng.random() < 0.4:
                self.plate_color = self.prev_plate_color
            else:
                self.plate_color = self._rng.randint(0, NUM_COLORS - 1)
        self.weight = self._weight_for_combo()
        self.target_center = self._random_target_center()
        self.target_width = self._target_width_for_weight(self.weight)

    def _weight_for_combo(self) -> int:
        return INITIAL_WEIGHT + (self.combo - 1) * WEIGHT_INCREMENT

    def _target_width_for_weight(self, w: int) -> float:
        extra = (w - INITIAL_WEIGHT) // WEIGHT_INCREMENT
        width = INITIAL_TARGET_WIDTH - extra * 0.02
        return max(MIN_TARGET_WIDTH, width)

    def _update_powering(self, held: bool) -> None:
        if held:
            self.power = min(1.0, self.power + self.power_rate)

    def _check_lift(self) -> tuple[str, float]:
        if self.super_timer > 0:
            return ("perfect", 1.0)
        half_width = self.target_width / 2
        if half_width <= 0:
            return ("miss", 0.0)
        acc = 1.0 - abs(self.power - self.target_center) / half_width
        if acc >= 0.9:
            return ("perfect", acc)
        elif acc >= 0.5:
            return ("ok", acc)
        else:
            return ("miss", 0.0)

    def _resolve_lift(self, result: str, accuracy: float) -> int:
        if result == "miss":
            self.heat = min(MAX_HEAT, self.heat + HEAT_MISS)
            self.combo = 0
            self.last_result = "miss"
            self.last_score_gain = 0
            return 0

        color_match = self.plate_color == self.prev_plate_color
        if not color_match:
            self.heat = min(MAX_HEAT, self.heat + HEAT_WRONG_COLOR)
            if self.super_timer == 0:
                self.combo = 1

        if self.super_timer == 0 and color_match:
            self.combo += 1
        elif self.super_timer > 0:
            self.combo += 1

        self.max_combo = max(self.max_combo, self.combo)

        if self.combo >= COMBO_FOR_SUPER:
            self.super_timer = SUPER_DURATION

        timing_multiplier = 1.5 if result == "perfect" else 1.0
        combo_multiplier = 1.0 + (self.combo - 1) * 0.25
        if self.super_timer > 0:
            combo_multiplier *= 3.0
        score_gain = int(self.weight * timing_multiplier * combo_multiplier)
        self.score += score_gain
        self.high_score = max(self.high_score, self.score)

        self.last_result = result
        self.last_score_gain = score_gain

        if self.super_timer == 0:
            self.weight = self._weight_for_combo()

        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER

        return score_gain

    def _update_heat(self) -> None:
        if self.heat >= MAX_HEAT:
            self.phase = Phase.GAME_OVER
            return
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            self.particles.append(Particle(
                x=x,
                y=y,
                vx=self._rng.uniform(-1.5, 1.5),
                vy=self._rng.uniform(-2.0, -0.5),
                life=self._rng.randint(15, 30),
                color=color,
            ))

    def _spawn_super_particles(self, x: float, y: float, count: int) -> None:
        for _ in range(count):
            color = PLATE_COLORS[self._rng.randint(0, NUM_COLORS - 1)]
            self.particles.append(Particle(
                x=x + self._rng.uniform(-20, 20),
                y=y + self._rng.uniform(-10, 10),
                vx=self._rng.uniform(-3.0, 3.0),
                vy=self._rng.uniform(-3.0, 0.0),
                life=self._rng.randint(20, 40),
                color=color,
            ))

    def _spawn_miss_particles(self, x: float, y: float, count: int) -> None:
        for _ in range(count):
            self.particles.append(Particle(
                x=x,
                y=y,
                vx=self._rng.uniform(-1.0, 1.0),
                vy=self._rng.uniform(-1.5, 0.0),
                life=self._rng.randint(10, 20),
                color=RED,
            ))

    def _update_particles(self) -> None:
        gravity = 0.03 if self.super_timer > 0 else 0.05
        for p in self.particles:
            p.vy += gravity
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # --- Update ---

    def update(self) -> None:
        self.frames += 1
        self._update_particles()

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        self.blink_timer = (self.blink_timer + 1) % 60
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.phase = Phase.PLAYING
            self.sub_phase = PlaySubPhase.AWAIT_LIFT
            self._start_lift()

    def _update_playing(self) -> None:
        self._update_heat()
        if self.phase == Phase.GAME_OVER:
            return

        if self.super_timer > 0:
            self.super_timer -= 1

        if self.sub_phase == PlaySubPhase.AWAIT_LIFT:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.power = 0.0
                self.sub_phase = PlaySubPhase.POWERING

        elif self.sub_phase == PlaySubPhase.POWERING:
            if pyxel.btn(pyxel.KEY_SPACE):
                self._update_powering(True)
            else:
                result, accuracy = self._check_lift()
                self._resolve_lift(result, accuracy)
                self.sub_phase = PlaySubPhase.LOCKOUT
                self.lockout_timer = 0
                if result == "perfect":
                    self._spawn_particles(200, 170, 10, self.plate_color)
                elif result == "ok":
                    self._spawn_particles(200, 170, 5, self.plate_color)
                else:
                    self._spawn_miss_particles(200, 170, 5)
                if self.super_timer > 0:
                    self._spawn_super_particles(200, 170, 20)

        elif self.sub_phase == PlaySubPhase.LOCKOUT:
            self.lockout_timer += 1
            if self.lockout_timer >= LOCKOUT_DURATION:
                self.sub_phase = PlaySubPhase.RESULT
                self.result_timer = 0

        elif self.sub_phase == PlaySubPhase.RESULT:
            self.result_timer += 1
            if self.result_timer >= RESULT_DURATION:
                self.sub_phase = PlaySubPhase.AWAIT_LIFT
                self.power = 0.0
                self._start_lift()

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()

    # --- Draw ---

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 40, 50, "LIFT CHAIN", WHITE)
        pyxel.text(SCREEN_W // 2 - 58, 62, "Color-Match Weightlifting", LIGHT_BLUE)

        pyxel.text(SCREEN_W // 2 - 50, 90, "PLATE COLORS:", WHITE)
        for i, color in enumerate(PLATE_COLORS):
            pyxel.rect(SCREEN_W // 2 - 45 + i * 32, 100, 10, 10, color)
        pyxel.text(SCREEN_W // 2 - 55, 114, "Same color = COMBO chain", GRAY)

        pyxel.text(SCREEN_W // 2 - 55, 138, "HOW TO PLAY:", WHITE)
        pyxel.text(SCREEN_W // 2 - 55, 150, "HOLD SPACE to build power", GRAY)
        pyxel.text(SCREEN_W // 2 - 55, 162, "Release in GREEN zone", GRAY)
        pyxel.text(SCREEN_W // 2 - 55, 174, "MATCH colors for COMBO", GRAY)
        pyxel.text(SCREEN_W // 2 - 55, 186, "COMBO x4 = SUPER LIFT!", GRAY)

        pyxel.text(SCREEN_W // 2 - 45, 206, f"HIGH SCORE: {self.high_score}", YELLOW)

        if self.blink_timer < 30:
            pyxel.text(SCREEN_W // 2 - 55, SCREEN_H - 20, "PRESS SPACE TO START", WHITE)

    def _draw_game(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, 130, LIGHT_BLUE)
        pyxel.rect(0, 130, SCREEN_W, 110, DARK_BLUE)

        self._draw_lifter()
        self._draw_barbell()
        self._draw_power_meter()
        self._draw_hud()
        self._draw_particles()
        self._draw_super_indicator()

        if self.sub_phase == PlaySubPhase.RESULT:
            self._draw_result_feedback()

        if self.sub_phase == PlaySubPhase.AWAIT_LIFT and self.combo >= 2:
            if self.plate_color == self.prev_plate_color:
                pyxel.text(SCREEN_W // 2 - 55, 50, "SAME COLOR! +COMBO", YELLOW)

    def _draw_lifter(self) -> None:
        pyxel.tri(150, 140, 170, 140, 160, 95, GRAY)
        pyxel.circ(160, 83, 8, GRAY)
        pyxel.line(138, 130, 115, 158, GRAY)
        pyxel.line(182, 130, 205, 158, GRAY)
        pyxel.line(157, 140, 148, 210, GRAY)
        pyxel.line(163, 140, 172, 210, GRAY)

    def _draw_barbell(self) -> None:
        bar_y_base = 170
        bar_y = bar_y_base

        if self.sub_phase == PlaySubPhase.LOCKOUT:
            lift_progress = self.lockout_timer / LOCKOUT_DURATION
            bar_y = bar_y_base - int(15 * lift_progress)

        bar_x_start = 60
        bar_x_end = 260
        bar_length = bar_x_end - bar_x_start

        if self.super_timer > 0:
            plate_color = PLATE_COLORS[(self.frames // 5) % NUM_COLORS]
            glow_color = PINK if self.frames % 10 < 5 else plate_color
            pyxel.rect(bar_x_start - 3, bar_y - 2, bar_length + 6, 5, glow_color)
        else:
            plate_color = PLATE_COLORS[self.plate_color]

        pyxel.rect(bar_x_start, bar_y, bar_length, 2, WHITE)

        plate_w = 12
        plate_h = 20
        pyxel.rect(bar_x_start - 8, bar_y - plate_h // 2 + 1, plate_w, plate_h, plate_color)
        pyxel.rect(bar_x_start - 8, bar_y - plate_h // 2 + 1, plate_w, plate_h, plate_color)
        pyxel.rect(bar_x_start + 20, bar_y - plate_h // 2 + 1, 8, plate_h, GRAY)

        pyxel.rect(bar_x_end - 4, bar_y - plate_h // 2 + 1, plate_w, plate_h, plate_color)
        pyxel.rect(bar_x_end - 4, bar_y - plate_h // 2 + 1, plate_w, plate_h, plate_color)
        pyxel.rect(bar_x_end - 28, bar_y - plate_h // 2 + 1, 8, plate_h, GRAY)

        pyxel.rect(bar_x_start + 10, bar_y - 5, 6, 12, GRAY)
        pyxel.rect(bar_x_end - 16, bar_y - 5, 6, 12, GRAY)

        weight_text = f"WEIGHT: {self.weight}kg"
        pyxel.text(SCREEN_W // 2 - 30, bar_y_base + 30, weight_text, WHITE)

    def _draw_power_meter(self) -> None:
        meter_x = 20
        meter_y = 35
        meter_w = 18
        meter_h = 145

        pyxel.rect(meter_x - 1, meter_y - 1, meter_w + 2, meter_h + 2, WHITE)
        pyxel.rect(meter_x, meter_y, meter_w, meter_h, GRAY)

        if self.sub_phase in (PlaySubPhase.AWAIT_LIFT, PlaySubPhase.POWERING):
            zone_center_y = meter_y + int(meter_h * self.target_center)
            zone_half = int(meter_h * self.target_width / 2)
            zone_top = max(meter_y, zone_center_y - zone_half)
            zone_bottom = min(meter_y + meter_h, zone_center_y + zone_half)

            perfect_half = zone_half // 3
            perfect_top = min(zone_bottom - perfect_half, zone_center_y - perfect_half)
            pyxel.rect(meter_x, perfect_top, meter_w, perfect_half * 2, GREEN)
            pyxel.rect(meter_x, zone_top, meter_w, perfect_top - zone_top, YELLOW)
            pyxel.rect(meter_x, perfect_top + perfect_half * 2, meter_w,
                       zone_bottom - (perfect_top + perfect_half * 2), YELLOW)

        if self.sub_phase in (PlaySubPhase.POWERING, PlaySubPhase.LOCKOUT, PlaySubPhase.RESULT):
            fill_height = int(meter_h * self.power)
            fill_y = meter_y + meter_h - fill_height
            if self.super_timer > 0 and self.sub_phase == PlaySubPhase.RESULT:
                fill_color = PINK
            elif self.sub_phase == PlaySubPhase.POWERING:
                zone_center_y = meter_y + int(meter_h * self.target_center)
                zone_half = int(meter_h * self.target_width / 2)
                power_mid = fill_y + fill_height // 2
                if abs(power_mid - zone_center_y) < zone_half // 3:
                    fill_color = GREEN
                elif abs(power_mid - zone_center_y) < zone_half:
                    fill_color = YELLOW
                else:
                    fill_color = RED
            elif self.last_result == "perfect":
                fill_color = GREEN
            elif self.last_result == "ok":
                fill_color = YELLOW
            else:
                fill_color = RED

            pyxel.rect(meter_x, fill_y, meter_w, fill_height, fill_color)

        pyxel.text(meter_x - 2, meter_y - 10, "PWR", WHITE)

    def _draw_hud(self) -> None:
        heat_bar_x = 55
        heat_bar_y = 10
        heat_bar_w = 70
        heat_bar_h = 6

        pyxel.text(heat_bar_x - 43, heat_bar_y, "HEAT", RED)
        pyxel.rect(heat_bar_x - 1, heat_bar_y - 1, heat_bar_w + 2, heat_bar_h + 2, WHITE)
        pyxel.rect(heat_bar_x, heat_bar_y, heat_bar_w, heat_bar_h, GRAY)
        heat_fill = int(heat_bar_w * (self.heat / MAX_HEAT))
        heat_color = PINK if self.heat > 70 else RED
        if heat_fill > 0:
            pyxel.rect(heat_bar_x, heat_bar_y, heat_fill, heat_bar_h, heat_color)

        score_text = f"SCORE: {self.score}"
        pyxel.text(SCREEN_W // 2 - 25, 8, score_text, WHITE)

        combo_color = WHITE
        if self.combo >= COMBO_FOR_SUPER:
            combo_color = PINK if self.frames % 8 < 4 else YELLOW
        elif self.combo >= 3:
            combo_color = YELLOW
        combo_text = f"COMBO x{self.combo}"
        pyxel.text(SCREEN_W - 74, 8, combo_text, combo_color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 40.0
            color = p.color if alpha > 0.3 else GRAY
            radius = 2 if p.life > 15 else 1
            pyxel.circ(int(p.x), int(p.y), radius, color)

    def _draw_result_feedback(self) -> None:
        if self.last_result == "perfect":
            pyxel.text(SCREEN_W // 2 - 28, 45, "PERFECT!", GREEN)
            pyxel.text(SCREEN_W // 2 - 30, 58, f"+{self.last_score_gain}", YELLOW)
        elif self.last_result == "ok":
            pyxel.text(SCREEN_W // 2 - 14, 45, "OK", YELLOW)
            pyxel.text(SCREEN_W // 2 - 30, 58, f"+{self.last_score_gain}", YELLOW)
        elif self.last_result == "miss":
            pyxel.text(SCREEN_W // 2 - 20, 45, "MISS!", RED)
            pyxel.text(SCREEN_W // 2 - 28, 58, "No lift!", GRAY)

    def _draw_super_indicator(self) -> None:
        if self.super_timer <= 0:
            return
        remaining_sec = self.super_timer // 30 + 1
        text = f"SUPER LIFT! {remaining_sec}s"
        color = PINK if self.frames % 6 < 3 else YELLOW
        pyxel.text(SCREEN_W // 2 - 55, 35, text, color)
        if self.frames % 3 == 0:
            self._spawn_super_particles(160, 170, 1)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 35, 60, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 52, 90, f"FINAL SCORE: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 55, 108, f"MAX COMBO: x{self.max_combo}", YELLOW)
        if self.score >= self.high_score and self.score > 0:
            pyxel.text(SCREEN_W // 2 - 45, 128, "NEW HIGH SCORE!", GREEN)
        else:
            pyxel.text(SCREEN_W // 2 - 50, 128, f"HIGH SCORE: {self.high_score}", GRAY)
        pyxel.text(SCREEN_W // 2 - 55, 170, "PRESS R TO RETRY", WHITE)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
