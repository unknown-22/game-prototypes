from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
import random
import pyxel

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

PLATE_COLORS: list[int] = [RED, LIME, DARK_BLUE, YELLOW]
PLATE_COLOR_NAMES: list[str] = ["RED", "LIME", "BLUE", "YEL"]

LIFT_LINE_Y = 75
PLATFORM_Y = 190
PLATFORM_X = 160
PLATFORM_W = 280
LIFTER_X = 160
LIFTER_FEET_Y = 186

VELOCITY_FACTOR = 0.10
GRAVITY = 0.25
POWER_BUILD_RATE = 2.0
POWER_MAX = 100.0
HEAT_MAX = 100.0
HEAT_DECAY = 0.02
HEAT_MISMATCH = 10.0
HEAT_MISS = 15.0

BARBELL_BAR_LENGTH = 80
PLATE_RADIUS = 12
PLATE_INNER_OFFSET = 20
PLATE_OUTER_OFFSET = 36

COMBO_THRESHOLD = 4
SUPER_DURATION = 300
SUPER_AUTO_LIFT_INTERVAL = 40
SUPER_SCORE_MULT = 3

RESULT_DISPLAY_FRAMES = 30
TIMER_START = 3600

COLOR_CYCLE_INTERVAL_START = 90
COLOR_CYCLE_INTERVAL_MIN = 40
DIFFICULTY_SCALE_RATE = 1.0

POWER_BAR_X = 240
POWER_BAR_Y = 30
POWER_BAR_W = 20
POWER_BAR_H = 150


class Phase(Enum):
    TITLE = auto()
    POWERING = auto()
    LIFTING = auto()
    RESULT = auto()
    GAME_OVER = auto()


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    color: int


@dataclass
class GhostLift:
    y: float
    color: int
    frame: int


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="LIFT CHAIN")
        self._rng: random.Random = random.Random()
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.ghost_recording: list[GhostLift] = []
        self._init_state()
        pyxel.run(self.update, self.draw)

    def _init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.timer: int = TIMER_START
        self.power: float = 0.0
        self.barbell_y: float = PLATFORM_Y
        self.barbell_vy: float = 0.0
        self.barbell_color: int = 0
        self.attempt_color: int = 0
        self.super_timer: int = 0
        self.super_mode: bool = False
        self.super_auto_frame: int = 0
        self.result_timer: int = 0
        self.lift_success: bool = False
        self.last_score: int = 0
        self.color_cycle_timer: int = 0
        self.color_cycle_interval: int = COLOR_CYCLE_INTERVAL_START
        self.powering: bool = False
        self.difficulty_level: float = 0.0
        self.best_lift_y: float = PLATFORM_Y
        self.screen_shake: int = 0
        self.particles.clear()
        self.floating_texts.clear()
        self.ghost_recording.clear()
        self.barbell_y = PLATFORM_Y
        self.barbell_vy = 0.0
        self.barbell_color = self._rng.randint(0, 3)
        self.attempt_color = self._rng.randint(0, 3)
        self.color_cycle_timer = self.color_cycle_interval

    def reset(self) -> None:
        self._init_state()

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.POWERING:
            self._update_powering()
        elif self.phase == Phase.LIFTING:
            self._update_lifting()
        elif self.phase == Phase.RESULT:
            self._update_result()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

        self._update_particles()
        self._update_floating_texts()

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.screen_shake > 0:
            ox = self._rng.randint(-3, 3)
            oy = self._rng.randint(-3, 3)
            pyxel.camera(ox, oy)
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.POWERING, Phase.LIFTING, Phase.RESULT):
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

        pyxel.camera(0, 0)

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.phase = Phase.POWERING

    def _update_powering(self) -> None:
        # Check game-over BEFORE decay (decay-before-threshold pitfall)
        if self.timer <= 0 or self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            return

        self._update_timer()
        self._update_heat()
        self._update_difficulty()
        self._cycle_attempt_color()

        if pyxel.btn(pyxel.KEY_SPACE):
            self._build_power()
        elif self.powering:
            self._release_lift()
            return

        if pyxel.btnr(pyxel.KEY_SPACE):
            self.powering = False

        if pyxel.btnp(pyxel.KEY_SPACE):
            self.powering = True
            self.power = 0.0

    def _update_lifting(self) -> None:
        self._update_lift()

        if self.super_mode:
            self._update_super()

        if self.barbell_vy >= 0 and self.barbell_y >= PLATFORM_Y:
            self.barbell_y = PLATFORM_Y
            self.barbell_vy = 0.0
            if self.super_mode and self.super_timer <= 0:
                self.super_mode = False
            self._resolve_lift(self.lift_success)
            self._start_result()
            return

        if self.barbell_y <= LIFT_LINE_Y:
            self.lift_success = True

    def _update_result(self) -> None:
        # Check game-over BEFORE decay (decay-before-threshold pitfall)
        if self.timer <= 0 or self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            return

        self._update_timer()
        self._update_heat()

        if self.screen_shake > 0:
            self.screen_shake -= 1

        self.result_timer -= 1
        if self.result_timer <= 0:
            if self.timer <= 0 or self.heat >= HEAT_MAX:
                self.phase = Phase.GAME_OVER
            else:
                self._start_powering()

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_R):
            self.reset()
            self.phase = Phase.TITLE

    def _start_powering(self) -> None:
        self.phase = Phase.POWERING
        self.power = 0.0
        self.powering = False
        self.barbell_color = self._rng.randint(0, 3)
        self.barbell_y = PLATFORM_Y
        self.barbell_vy = 0.0
        self.lift_success = False

    def _build_power(self) -> None:
        self.power += POWER_BUILD_RATE
        if self.power > POWER_MAX:
            self.power = POWER_MAX

    def _release_lift(self) -> None:
        self.barbell_vy = -self.power * VELOCITY_FACTOR
        self.powering = False
        self.phase = Phase.LIFTING
        self.lift_success = False

    def _update_lift(self) -> None:
        self.barbell_vy += GRAVITY
        self.barbell_y += self.barbell_vy

        lift_y = self.barbell_y
        if lift_y < self.best_lift_y:
            self.best_lift_y = lift_y

        if self.super_mode:
            self.ghost_recording.append(
                GhostLift(y=self.barbell_y, color=self.barbell_color, frame=pyxel.frame_count)
            )

    def _resolve_lift(self, reached_line: bool) -> None:
        if not reached_line:
            self.lift_success = False
            self.heat += HEAT_MISS
            self.combo = 0
            self.last_score = 0
            self._spawn_particles(LIFTER_X, PLATFORM_Y, 5, GRAY)
            self._spawn_floating_text(LIFTER_X, PLATFORM_Y - 20, "MISS", GRAY)
            self.screen_shake = 10
            return

        match = self.barbell_color == self.attempt_color or self.super_mode

        if match:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            mult = SUPER_SCORE_MULT if self.super_mode else 1
            self.last_score = 10 * self.combo * mult
            self.score += self.last_score

            if self.super_mode:
                self._spawn_particles(self.barbell_x(), self.barbell_y, 25, self.barbell_color)
                for _ in range(5):
                    rc = PLATE_COLORS[self._rng.randint(0, 3)]
                    self._spawn_particles(self.barbell_x(), self.barbell_y, 5, rc)
                self._spawn_floating_text(
                    LIFTER_X, LIFT_LINE_Y - 10, f"+{self.last_score} x{SUPER_SCORE_MULT}", PEACH
                )
            else:
                self._spawn_particles(self.barbell_x(), self.barbell_y, 12, self.barbell_color)
                self._spawn_floating_text(LIFTER_X, LIFT_LINE_Y - 10, f"+{self.last_score}", self.barbell_color)

            if self.combo >= COMBO_THRESHOLD and not self.super_mode:
                self._activate_super()
        else:
            self.heat += HEAT_MISMATCH
            self.combo = 0
            self.last_score = 0
            self._spawn_particles(LIFTER_X, PLATFORM_Y, 8, ORANGE)
            self._spawn_floating_text(LIFTER_X, PLATFORM_Y - 20, "MISMATCH", ORANGE)

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self.super_auto_frame = SUPER_AUTO_LIFT_INTERVAL
        self.screen_shake = 15
        for _ in range(30):
            rc = PLATE_COLORS[self._rng.randint(0, 3)]
            self._spawn_particles(self.barbell_x(), self.barbell_y, 3, rc)

    def _update_super(self) -> None:
        self.super_timer -= 1
        if self.super_timer <= 0:
            self.super_mode = False
            return

        self.super_auto_frame -= 1
        if self.super_auto_frame <= 0:
            self.super_auto_frame = SUPER_AUTO_LIFT_INTERVAL
            self._execute_auto_lift()

    def _execute_auto_lift(self) -> None:
        self.power = POWER_MAX
        self.barbell_vy = -POWER_MAX * VELOCITY_FACTOR
        self.barbell_color = self._rng.randint(0, 3)
        self.lift_success = False

    def _update_heat(self) -> None:
        self.heat -= HEAT_DECAY
        if self.heat < 0:
            self.heat = 0.0

    def _update_difficulty(self) -> None:
        elapsed = (TIMER_START - self.timer) / 300.0
        self.difficulty_level = elapsed * DIFFICULTY_SCALE_RATE
        self.color_cycle_interval = max(
            COLOR_CYCLE_INTERVAL_MIN,
            int(COLOR_CYCLE_INTERVAL_START - self.difficulty_level),
        )

    def _update_timer(self) -> None:
        if self.super_mode:
            return
        self.timer -= 1
        if self.timer < 0:
            self.timer = 0

    def _cycle_attempt_color(self) -> None:
        self.color_cycle_timer -= 1
        if self.color_cycle_timer <= 0:
            self.color_cycle_timer = self.color_cycle_interval
            self.attempt_color = (self.attempt_color + 1) % 4

    def _start_result(self) -> None:
        self.phase = Phase.RESULT
        self.result_timer = RESULT_DISPLAY_FRAMES

    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-3.0, 3.0)
            vy = self._rng.uniform(-5.0, -1.0)
            life = self._rng.randint(10, 25)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=40, color=color))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.life -= 1
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
        self.particles = [p for p in self.particles if p.life > 0]
        if len(self.particles) > 200:
            self.particles = self.particles[-200:]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.life -= 1
            ft.y -= 0.5
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def barbell_x(self) -> float:
        return LIFTER_X

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 40, 60, "LIFT CHAIN", WHITE)
        pyxel.text(SCREEN_W // 2 - 55, 90, "Press SPACE to start", CYAN)

        pyxel.text(SCREEN_W // 2 - 60, 120, "Hold SPACE: build power", GRAY)
        pyxel.text(SCREEN_W // 2 - 60, 132, "Release SPACE: execute lift", GRAY)
        pyxel.text(SCREEN_W // 2 - 60, 144, "Match colors for COMBO", GRAY)
        pyxel.text(SCREEN_W // 2 - 60, 156, "COMBO 4+ = SUPER LIFT!", PEACH)
        pyxel.text(SCREEN_W // 2 - 60, 168, "60 second challenge", GRAY)

        if self.score > 0:
            pyxel.text(SCREEN_W // 2 - 50, 200, f"Previous Score: {self.score}", WHITE)
            pyxel.text(SCREEN_W // 2 - 50, 212, f"Best Combo: {self.max_combo}", WHITE)

    def _draw_game(self) -> None:
        self._draw_lift_line()
        self._draw_platform()
        self._draw_lifter()
        self._draw_barbell()
        self._draw_power_bar()
        self._draw_hud()
        self._draw_particles()
        self._draw_floating_texts()

        if self.super_mode:
            self._draw_super_border()

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 40, 60, "GAME OVER", RED)

        reason = "Heat overload!" if self.heat >= HEAT_MAX else "Time's up!"
        pyxel.text(SCREEN_W // 2 - 25, 80, reason, WHITE)

        pyxel.text(SCREEN_W // 2 - 50, 110, f"Score: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 50, 125, f"Max Combo: {self.max_combo}", WHITE)
        best_y_display = abs(int(self.best_lift_y - PLATFORM_Y)) if self.best_lift_y < PLATFORM_Y else 0
        pyxel.text(SCREEN_W // 2 - 50, 140, f"Best Lift: {best_y_display}", WHITE)

        pyxel.text(SCREEN_W // 2 - 55, 180, "Press SPACE to retry", CYAN)

    def _draw_lift_line(self) -> None:
        for x in range(0, SCREEN_W, 8):
            pyxel.line(x, LIFT_LINE_Y, x + 4, LIFT_LINE_Y, GREEN)
        pyxel.text(2, LIFT_LINE_Y - 10, "LIFT LINE", GREEN)

    def _draw_platform(self) -> None:
        x0 = PLATFORM_X - PLATFORM_W // 2
        pyxel.rect(x0, PLATFORM_Y, PLATFORM_W, 4, WHITE)

    def _draw_lifter(self) -> None:
        head_y = 130
        body_bottom_y = LIFTER_FEET_Y

        if self.phase == Phase.POWERING and self.powering:
            head_y = 120
            body_bottom_y = LIFTER_FEET_Y - 10

        if self.phase == Phase.LIFTING:
            lift_ratio = (PLATFORM_Y - self.barbell_y) / (PLATFORM_Y - LIFT_LINE_Y)
            lift_ratio = max(0.0, min(1.0, lift_ratio))
            head_y = 130 - int(lift_ratio * 10)
            body_bottom_y = LIFTER_FEET_Y - int(lift_ratio * 5)

        pyxel.circ(LIFTER_X, head_y, 6, WHITE)
        pyxel.line(LIFTER_X, head_y + 6, LIFTER_X, body_bottom_y, WHITE)

        arm_target_y = int(self.barbell_y) if self.phase in (Phase.LIFTING, Phase.RESULT) else head_y + 20
        arm_target_y = max(head_y + 10, min(arm_target_y, body_bottom_y - 10))
        pyxel.line(LIFTER_X - 5, head_y + 10, LIFTER_X - 25, arm_target_y, WHITE)
        pyxel.line(LIFTER_X + 5, head_y + 10, LIFTER_X + 25, arm_target_y, WHITE)

        pyxel.line(LIFTER_X - 5, body_bottom_y, LIFTER_X - 15, LIFTER_FEET_Y + 4, WHITE)
        pyxel.line(LIFTER_X + 5, body_bottom_y, LIFTER_X + 15, LIFTER_FEET_Y + 4, WHITE)

    def _draw_barbell(self) -> None:
        bx = self.barbell_x()
        by = int(self.barbell_y)
        bar_x0 = bx - BARBELL_BAR_LENGTH // 2
        bar_x1 = bx + BARBELL_BAR_LENGTH // 2

        if self.super_mode:
            rainbow_offset = pyxel.frame_count // 3
            bar_color = PLATE_COLORS[(rainbow_offset) % 4]
        else:
            bar_color = GRAY

        pyxel.line(bar_x0, by, bar_x1, by, bar_color)

        plate_color = self._get_barbell_display_color()
        for offset in [-PLATE_OUTER_OFFSET, -PLATE_INNER_OFFSET, PLATE_INNER_OFFSET, PLATE_OUTER_OFFSET]:
            px = bx + offset
            pyxel.circ(px, by, PLATE_RADIUS, GRAY)
            pyxel.circ(px, by, PLATE_RADIUS - 2, plate_color)
            pyxel.circ(px, by, 4, GRAY)

    def _get_barbell_display_color(self) -> int:
        if self.super_mode:
            return PLATE_COLORS[(pyxel.frame_count // 3) % 4]
        return PLATE_COLORS[self.barbell_color]

    def _draw_power_bar(self) -> None:
        bx = POWER_BAR_X
        by = POWER_BAR_Y

        pyxel.rectb(bx, by, POWER_BAR_W, POWER_BAR_H, WHITE)

        if self.powering and self.phase == Phase.POWERING:
            fill_h = int(POWER_BAR_H * self.power / POWER_MAX)
            fy = by + POWER_BAR_H - fill_h

            if self.power < 40:
                pc = GREEN
            elif self.power < 76:
                pc = YELLOW
            else:
                pc = RED

            pyxel.rect(bx + 1, fy, POWER_BAR_W - 2, fill_h, pc)

        pyxel.text(bx + POWER_BAR_W + 4, by, "PWR", GRAY)

        if self.powering and self.phase == Phase.POWERING:
            pyxel.text(bx + POWER_BAR_W + 4, by + 10, f"{int(self.power)}", WHITE)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)

        combo_text = f"COMBO: {self.combo}"
        combo_color = PEACH if self.combo >= COMBO_THRESHOLD else WHITE
        pyxel.text(SCREEN_W // 2 - 25, 4, combo_text, combo_color)

        secs = max(0, self.timer) // 60
        timer_color = RED if secs <= 10 else WHITE
        pyxel.text(SCREEN_W - 60, 4, f"TIME: {secs}", timer_color)

        hw = 100
        hy = 8
        hx = 2
        pyxel.rectb(hx, hy, hw, 6, ORANGE)
        heat_fill = int(hw * self.heat / HEAT_MAX)
        if heat_fill > 0:
            heat_color = RED if self.heat > 70 else ORANGE
            pyxel.rect(hx + 1, hy + 1, heat_fill, 4, heat_color)
        pyxel.text(hx, hy + 8, "HEAT", ORANGE)

        if self.super_mode:
            sup_text = f"SUPER LIFT! {self.super_timer // 60}s"
            pyxel.text(SCREEN_W // 2 - 35, 20, sup_text, CYAN)

        attempt_color = PLATE_COLORS[self.attempt_color]
        pyxel.text(4, LIFT_LINE_Y + LIFT_LINE_Y // 2, "AIM:", GRAY)
        pyxel.rect(24, LIFT_LINE_Y + LIFT_LINE_Y // 2 - 3, 10, 10, attempt_color)

    def _draw_super_border(self) -> None:
        t = pyxel.frame_count
        colors = PLATE_COLORS
        for i in range(4):
            c = colors[(t // 3 + i) % 4]
            pyxel.rectb(i * 2, i * 2, SCREEN_W - i * 4, SCREEN_H - i * 4, c)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = 16 - max(0, min(15, 16 - p.life))
            f = alpha / 16.0
            sx = int(p.x)
            sy = int(p.y)
            if f > 0.5:
                pyxel.circ(sx, sy, 1, p.color)
            else:
                pyxel.pset(sx, sy, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = max(0, ft.life / 40.0)
            if alpha > 0.3:
                pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
