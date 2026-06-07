from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# --- Color constants ---
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

GAME_COLORS: list[int] = [RED, GREEN, LIGHT_BLUE, YELLOW]
COLOR_LABELS: list[str] = ["R", "G", "B", "Y"]
SEGMENT_COLORS: list[int] = [RED, GREEN, LIGHT_BLUE, YELLOW, RED, GREEN, LIGHT_BLUE, YELLOW]

WHEEL_CX = 160
WHEEL_CY = 110
WHEEL_R = 70
NUM_SEGMENTS = 8

FPS = 60
GAME_DURATION_SEC = 60
RESULT_PAUSE = 48
HEAT_MAX = 100
HEAT_PER_MISS = 15
SUPER_TURNS = 5
SUPER_MULTIPLIER = 3.0
COMBO_THRESHOLD = 5
FORESIGHT_MAX = 3
BASE_SCORE = 100
COMBO_MULT_STEP = 0.5
DECAY = 0.985
SPIN_THRESHOLD = 0.002


class Phase(Enum):
    TITLE = auto()
    BET = auto()
    SPINNING = auto()
    RESULT = auto()
    GAME_OVER = auto()


@dataclass
class WheelSegment:
    color: int
    start_angle: float
    end_angle: float


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


class Game:
    SCREEN_W = 320
    SCREEN_H = 240

    def __init__(self) -> None:
        pyxel.init(self.SCREEN_W, self.SCREEN_H, title="Roulette Surge", fps=FPS, display_scale=2)
        self._rng: random.Random = random.Random()
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: int = 0
        self.wheel_angle: float = 0.0
        self.spin_speed: float = 0.0
        self.bet_color: int = -1
        self.winning_color: int = -1
        self.result_timer: int = 0
        self.super_mode: bool = False
        self.super_turns: int = 0
        self.foresight_tokens: int = FORESIGHT_MAX
        self.foresight_queue: list[int] = []
        self.game_timer: int = GAME_DURATION_SEC * FPS
        self.segments: list[WheelSegment] = []
        self.particles: list[Particle] = []
        self._spin_frames: int = 0
        self._was_match: bool = False
        self._last_score_gain: int = 0
        self.high_score: int = 0
        self._blink: int = 0
        self._prev_mouse_pressed: bool = False
        self._target_angle_mod: float = 0.0
        self._build_segments()
        self._refill_foresight()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0
        self.wheel_angle = 0.0
        self.spin_speed = 0.0
        self.bet_color = -1
        self.winning_color = -1
        self.result_timer = 0
        self.super_mode = False
        self.super_turns = 0
        self.foresight_tokens = FORESIGHT_MAX
        self.game_timer = GAME_DURATION_SEC * FPS
        self.particles.clear()
        self._spin_frames = 0
        self._was_match = False
        self._last_score_gain = 0
        self._target_angle_mod = 0.0
        self._build_segments()
        self._refill_foresight()

    def _build_segments(self) -> None:
        self.segments = []
        seg_angle = 2 * math.pi / NUM_SEGMENTS
        for i in range(NUM_SEGMENTS):
            start = i * seg_angle
            end = start + seg_angle
            self.segments.append(WheelSegment(SEGMENT_COLORS[i], start, end))

    def _refill_foresight(self) -> None:
        while len(self.foresight_queue) < 2:
            self.foresight_queue.append(self._rng.choice(GAME_COLORS))

    def _find_segment_for_color(self, color: int) -> int:
        indices = [i for i, seg in enumerate(self.segments) if seg.color == color]
        return self._rng.choice(indices)

    def _start_spin(self) -> None:
        if self.phase != Phase.BET:
            return
        target_color = self.foresight_queue[0]
        target_idx = self._find_segment_for_color(target_color)
        target_mod = (2 * math.pi) - (target_idx * math.pi / 4 + math.pi / 8)
        target_mod %= 2 * math.pi
        self._target_angle_mod = target_mod

        current_mod = self.wheel_angle % (2 * math.pi)
        delta = target_mod - current_mod
        if delta <= 0:
            delta += 2 * math.pi

        extra_rots = self._rng.randint(3, 5) * 2 * math.pi
        total_rotation = delta + extra_rots
        self.spin_speed = total_rotation * (1.0 - DECAY)
        self.spin_speed = max(0.3, min(0.5, self.spin_speed))
        self.phase = Phase.SPINNING
        self._spin_frames = 0

    def _update_spinning(self) -> None:
        self.wheel_angle += self.spin_speed
        self.wheel_angle %= 2 * math.pi
        self.spin_speed *= DECAY
        self._spin_frames += 1
        if self.spin_speed < SPIN_THRESHOLD:
            self.wheel_angle = self._target_angle_mod
            self._evaluate_result()

    def _evaluate_result(self) -> None:
        winner_idx = int(((2 * math.pi - self.wheel_angle) % (2 * math.pi)) / (math.pi / 4)) % NUM_SEGMENTS
        self.winning_color = self.segments[winner_idx].color
        if self.foresight_queue:
            self.foresight_queue.pop(0)
        self._refill_foresight()

        was_super = self.super_mode
        is_match = self.winning_color == self.bet_color or was_super
        self._was_match = is_match

        if is_match:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            if was_super:
                multiplier = SUPER_MULTIPLIER
            else:
                multiplier = 1.0 + self.combo * COMBO_MULT_STEP
            gain = int(BASE_SCORE * multiplier)
            self.score += gain
            self._last_score_gain = gain
            self._spawn_particles(WHEEL_CX, WHEEL_CY - WHEEL_R, self.winning_color, 12)
            if self.combo >= COMBO_THRESHOLD and not self.super_mode:
                self.super_mode = True
                self.super_turns = SUPER_TURNS
                self._spawn_particles(WHEEL_CX, WHEEL_CY, WHITE, 30)
        else:
            self.combo = 0
            self.heat = min(HEAT_MAX, self.heat + HEAT_PER_MISS)
            self._last_score_gain = 0
            self._spawn_particles(WHEEL_CX, WHEEL_CY - WHEEL_R, RED, 6)

        if was_super:
            self.super_turns -= 1
            if self.super_turns <= 0:
                self.super_mode = False

        if self.heat >= HEAT_MAX:
            if self.score > self.high_score:
                self.high_score = self.score
            self.phase = Phase.GAME_OVER
            return

        self.phase = Phase.RESULT
        self.result_timer = RESULT_PAUSE

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-2.0, 2.0)
            vy = self._rng.uniform(-3.5, -0.5)
            life = self._rng.randint(15, 25)
            self.particles.append(Particle(x, y, vx, vy, life, color))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_timer(self) -> None:
        if self.phase not in (Phase.BET, Phase.SPINNING, Phase.RESULT):
            return
        self.game_timer -= 1
        if self.game_timer <= 0:
            self.game_timer = 0
            if self.score > self.high_score:
                self.high_score = self.score
            self.phase = Phase.GAME_OVER

    def place_bet(self, color_idx: int) -> None:
        if self.phase != Phase.BET:
            return
        if color_idx < 0 or color_idx >= len(GAME_COLORS):
            return
        self.bet_color = GAME_COLORS[color_idx]
        self._start_spin()

    def use_foresight(self) -> None:
        if self.phase != Phase.BET:
            return
        if self.foresight_tokens <= 0:
            return
        self.foresight_tokens -= 1

    def update(self) -> None:
        self._blink += 1
        self._update_particles()

        mouse_pressed = pyxel.btn(pyxel.MOUSE_BUTTON_LEFT)
        mouse_clicked = mouse_pressed and not self._prev_mouse_pressed
        self._prev_mouse_pressed = mouse_pressed

        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()
            return

        match self.phase:
            case Phase.TITLE:
                if mouse_clicked or pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                    self.phase = Phase.BET
                    self.game_timer = GAME_DURATION_SEC * FPS
            case Phase.BET:
                self._update_timer()
                if self.phase != Phase.BET:
                    return
                for i in range(4):
                    if pyxel.btnp(pyxel.KEY_1 + i):
                        self.place_bet(i)
                        return
                if pyxel.btnp(pyxel.KEY_SPACE):
                    self.use_foresight()
                if mouse_clicked:
                    self._handle_mouse_bet()
            case Phase.SPINNING:
                self._update_timer()
                self._update_spinning()
            case Phase.RESULT:
                self._update_timer()
                if self.phase != Phase.RESULT:
                    return
                self.result_timer -= 1
                if self.result_timer <= 0:
                    if self.phase == Phase.RESULT:
                        self.phase = Phase.BET
                        self.bet_color = -1
            case Phase.GAME_OVER:
                if mouse_clicked or pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                    self.phase = Phase.BET
                    self.score = 0
                    self.combo = 0
                    self.max_combo = 0
                    self.heat = 0
                    self.wheel_angle = 0.0
                    self.spin_speed = 0.0
                    self.bet_color = -1
                    self.winning_color = -1
                    self.result_timer = 0
                    self.super_mode = False
                    self.super_turns = 0
                    self.foresight_tokens = FORESIGHT_MAX
                    self.game_timer = GAME_DURATION_SEC * FPS
                    self.particles.clear()
                    self._spin_frames = 0
                    self._was_match = False
                    self._last_score_gain = 0
                    self._target_angle_mod = 0.0
                    self._build_segments()
                    self._refill_foresight()

    def _handle_mouse_bet(self) -> None:
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        bw, bh = 60, 20
        gap = 6
        total_w = 4 * bw + 3 * gap
        start_x = (self.SCREEN_W - total_w) // 2
        btn_y = 200
        for i in range(4):
            bx = start_x + i * (bw + gap)
            if bx <= mx <= bx + bw and btn_y <= my <= btn_y + bh:
                self.place_bet(i)
                return

    def draw(self) -> None:
        pyxel.cls(NAVY)
        match self.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.BET | Phase.SPINNING | Phase.RESULT:
                self._draw_game()
            case Phase.GAME_OVER:
                self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(self.SCREEN_W // 2 - 60, 30, "ROULETTE SURGE", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 55, 42, "===============", CYAN)

        pyxel.text(self.SCREEN_W // 2 - 70, 65, "Bet on colors, build COMBO chains!", LIME)
        pyxel.text(self.SCREEN_W // 2 - 70, 77, "1-4 keys or Click to bet", GREEN)
        pyxel.text(self.SCREEN_W // 2 - 70, 89, "SPACE = Foresight (reveal future)", GREEN)
        pyxel.text(self.SCREEN_W // 2 - 70, 101, "COMBO x5 = SUPER MODE (all win, 3x!)", YELLOW)
        pyxel.text(self.SCREEN_W // 2 - 70, 113, "Miss = +15 HEAT (100 = GAME OVER)", ORANGE)
        pyxel.text(self.SCREEN_W // 2 - 70, 125, "Survive 60 sec, maximize SCORE!", WHITE)

        if self.high_score > 0:
            pyxel.text(self.SCREEN_W // 2 - 38, 155, f"HIGH SCORE: {self.high_score}", YELLOW)

        pyxel.text(self.SCREEN_W // 2 - 38, 185, "Click / SPACE / ENTER", WHITE)

    def _draw_game(self) -> None:
        self._draw_wheel()
        self._draw_pointer()
        self._draw_hud()
        self._draw_bet_buttons()
        self._draw_foresight()
        self._draw_super_mode()
        self._draw_particles()
        if self.phase == Phase.RESULT:
            self._draw_result_overlay()

    def _draw_wheel(self) -> None:
        cx = WHEEL_CX
        cy = WHEEL_CY
        r = WHEEL_R
        angle = self.wheel_angle
        draw_steps = 8

        for i, seg in enumerate(self.segments):
            a1 = seg.start_angle + angle - math.pi / 2
            a2 = seg.end_angle + angle - math.pi / 2
            color = seg.color
            for j in range(draw_steps):
                t1 = a1 + (a2 - a1) * j / draw_steps
                t2 = a1 + (a2 - a1) * (j + 1) / draw_steps
                x1 = cx + math.cos(t1) * r
                y1 = cy + math.sin(t1) * r
                x2 = cx + math.cos(t2) * r
                y2 = cy + math.sin(t2) * r
                if self.super_mode:
                    pulse = (pyxel.frame_count // 6) % 2
                    col = WHITE if pulse else color
                else:
                    col = color
                pyxel.tri(cx, cy, x1, y1, x2, y2, col)

        pyxel.circb(cx, cy, r, WHITE)
        pyxel.circ(cx, cy, 6, WHITE)
        pyxel.circ(cx, cy, 3, BLACK)

    def _draw_pointer(self) -> None:
        px = WHEEL_CX
        py = WHEEL_CY - WHEEL_R
        pyxel.tri(px, py - 14, px - 8, py, px + 8, py, WHITE)

    def _draw_hud(self) -> None:
        secs = self.game_timer // FPS
        tcolor = RED if secs < 10 else WHITE

        pyxel.text(4, 4, f"SCORE: {self.score}", WHITE)
        pyxel.text(120, 4, f"TIME: {secs:02d}", tcolor)
        combo_color = YELLOW if self.combo >= COMBO_THRESHOLD else WHITE
        pyxel.text(250, 4, f"C:{self.combo}", combo_color)

        pyxel.text(4, 218, "HEAT", WHITE)
        bar_w = 80
        bar_h = 6
        bar_x = 36
        bar_y = 219
        heat_ratio = self.heat / HEAT_MAX
        if heat_ratio > 0.7:
            heat_color = RED
        elif heat_ratio > 0.3:
            heat_color = ORANGE
        else:
            heat_color = GREEN
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, DARK_BLUE)
        if self.heat > 0:
            pyxel.rect(bar_x, bar_y, int(bar_w * heat_ratio), bar_h, heat_color)

    def _draw_bet_buttons(self) -> None:
        bw, bh = 60, 20
        gap = 6
        total_w = 4 * bw + 3 * gap
        start_x = (self.SCREEN_W - total_w) // 2
        btn_y = 200

        for i in range(4):
            bx = start_x + i * (bw + gap)
            color = GAME_COLORS[i]
            if self.bet_color == color and self.phase == Phase.BET:
                pyxel.rectb(bx - 2, btn_y - 2, bw + 4, bh + 4, WHITE)
            pyxel.rect(bx, btn_y, bw, bh, color)
            label_col = BLACK if color == YELLOW else WHITE
            pyxel.text(bx + bw // 2 - 3, btn_y + 7, COLOR_LABELS[i], label_col)

    def _draw_foresight(self) -> None:
        pyxel.text(250, 218, f"F: {self.foresight_tokens}", WHITE if self.foresight_tokens > 0 else GRAY)
        if self.phase == Phase.BET and self.foresight_tokens < FORESIGHT_MAX and self.foresight_queue:
            pyxel.text(250, 200, "NEXT:", GRAY)
            for i, c in enumerate(self.foresight_queue[:2]):
                pyxel.circ(284 + i * 16, 204, 5, c)
                pyxel.circb(284 + i * 16, 204, 5, WHITE)

    def _draw_super_mode(self) -> None:
        if self.super_mode:
            pulse = (pyxel.frame_count // 8) % 3
            if pulse == 0:
                col = YELLOW
            elif pulse == 1:
                col = ORANGE
            else:
                col = RED
            pyxel.text(self.SCREEN_W // 2 - 36, 20, f"SUPER x3  T:{self.super_turns}", col)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 25
            if alpha > 0.6:
                col = p.color
            elif alpha > 0.3:
                col = WHITE
            else:
                col = GRAY
            px = int(p.x)
            py = int(p.y)
            if 0 <= px < self.SCREEN_W and 0 <= py < self.SCREEN_H:
                pyxel.pset(px, py, col)

    def _draw_result_overlay(self) -> None:
        if self._was_match:
            color = YELLOW if self.super_mode else LIME
            if self.combo >= COMBO_THRESHOLD and self.super_mode:
                text = f"SUPER! +{self._last_score_gain}"
            else:
                text = f"+{self._last_score_gain} COMBO x{self.combo}"
            pyxel.text(WHEEL_CX - len(text) * 2, WHEEL_CY + WHEEL_R + 10, text, color)
        else:
            text = f"MISS  +{HEAT_PER_MISS} HEAT"
            pyxel.text(WHEEL_CX - len(text) * 2, WHEEL_CY + WHEEL_R + 10, text, RED)

    def _draw_game_over(self) -> None:
        pyxel.text(self.SCREEN_W // 2 - 40, 50, "GAME OVER", RED)
        pyxel.text(self.SCREEN_W // 2 - 44, 62, "==========", RED)

        pyxel.text(self.SCREEN_W // 2 - 40, 85, f"SCORE: {self.score}", WHITE)
        pyxel.text(self.SCREEN_W // 2 - 40, 97, f"MAX COMBO: {self.max_combo}", YELLOW)

        if self.heat >= HEAT_MAX:
            pyxel.text(self.SCREEN_W // 2 - 40, 109, "OVERHEATED!", RED)
        else:
            pyxel.text(self.SCREEN_W // 2 - 40, 109, "TIME UP!", GRAY)

        if self.score == self.high_score and self.score > 0:
            pyxel.text(self.SCREEN_W // 2 - 48, 130, "** NEW HIGH SCORE! **", YELLOW)

        pyxel.text(self.SCREEN_W // 2 - 55, 200, "Click / SPACE / ENTER to retry", WHITE)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
