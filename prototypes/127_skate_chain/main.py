"""SKATE CHAIN — Color-match skateboarding on a vert ramp.

Core fun moment: building a COMBO of same-color tricks until SUPER COMBO
activates — rainbow explosions, auto-success, and 3x score multiplier.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import pyxel

SCREEN_W = 320
SCREEN_H = 240
DISPLAY_SCALE = 2
FPS = 60
FONT_PATH = Path(__file__).with_name("k8x12.bdf")

BLACK = 0
NAVY = 1
GREEN = 3
DARK_BLUE = 5
WHITE = 7
RED = 8
YELLOW = 10
LIME = 11
CYAN = 12
GRAY = 13
PINK = 14
PEACH = 15

TRICK_COLORS: tuple[int, int, int, int] = (RED, GREEN, DARK_BLUE, YELLOW)
TRICK_NAMES: tuple[str, str, str, str] = ("RED", "GREEN", "BLUE", "YELLOW")
TRICK_KEY_LABELS: tuple[str, str, str, str] = ("Z", "X", "C", "V")
COLOR_TO_IDX: dict[int, int] = {RED: 0, GREEN: 1, DARK_BLUE: 2, YELLOW: 3}

GAME_DURATION = 3600  # 60s * 60fps
SUPER_DURATION = 300  # 5s * 60fps
MAX_HEAT = 100.0
HEAT_DECAY = 0.05
COMBO_THRESHOLD = 5
RAMP_CENTER_X = 160.0
RAMP_BOTTOM_Y = 180.0
RAMP_TOP_Y = 60.0
RAMP_HALF_WIDTH = 130.0
RAMP_LEFT_EDGE_X = 30.0
RAMP_RIGHT_EDGE_X = 290.0
RAMP_FLAT_LEFT = 60.0
RAMP_FLAT_RIGHT = 260.0
OSC_SPEED_BASE = 0.03
TRICK_ZONE_THRESHOLD = 20.0  # y below RAMP_BOTTOM_Y means "on ramp above flat"
APEX_THRESHOLD = 0.85  # abs(sin(angle)) threshold for apex


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
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
class Skater:
    x: float = RAMP_CENTER_X
    y: float = RAMP_BOTTOM_Y
    vx: float = 0.0
    vy: float = 0.0
    angle: float = 0.0
    direction: int = 1
    on_ramp: bool = True
    in_trick_zone: bool = False

    @property
    def which_side(self) -> int:
        return 0 if self.x < RAMP_CENTER_X else 1

    @property
    def at_apex(self) -> bool:
        return abs(math.sin(self.angle)) > APEX_THRESHOLD


def ramp_y(x: float) -> float:
    """Compute y position on the halfpipe curve from x. Pure function for testability."""
    if RAMP_FLAT_LEFT <= x <= RAMP_FLAT_RIGHT:
        return RAMP_BOTTOM_Y
    if x < RAMP_FLAT_LEFT:
        d = max(0.0, x - RAMP_LEFT_EDGE_X)
        w = RAMP_FLAT_LEFT - RAMP_LEFT_EDGE_X
        t = max(0.0, min(1.0, d / w)) if w > 0 else 0.0
        st = t * t * (3.0 - 2.0 * t)
        return RAMP_BOTTOM_Y - (RAMP_BOTTOM_Y - RAMP_TOP_Y) * (1.0 - st)
    else:
        d = min(0.0, x - RAMP_RIGHT_EDGE_X)
        w = RAMP_RIGHT_EDGE_X - RAMP_FLAT_RIGHT
        t = max(0.0, min(1.0, abs(d) / w)) if w > 0 else 0.0
        st = t * t * (3.0 - 2.0 * t)
        return RAMP_BOTTOM_Y - (RAMP_BOTTOM_Y - RAMP_TOP_Y) * (1.0 - st)


def oscillation_angle(frame_count: int, combo: int, base_speed: float = OSC_SPEED_BASE) -> float:
    """Compute oscillation angle from frame count and combo. Pure function."""
    speed = base_speed * (1.0 + combo * 0.1)
    return frame_count * speed


def oscillation_x(angle: float) -> float:
    """Compute x position from oscillation angle."""
    return RAMP_CENTER_X + RAMP_HALF_WIDTH * math.sin(angle)


def clamp_x(x: float) -> float:
    return max(RAMP_LEFT_EDGE_X, min(RAMP_RIGHT_EDGE_X, x))


class Game:
    SCREEN_W = SCREEN_W
    SCREEN_H = SCREEN_H

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="SKATE CHAIN", fps=FPS, display_scale=DISPLAY_SCALE)
        _ = pyxel.Font(str(FONT_PATH))
        self._rng = random.Random()
        self._frame_count: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._shake_frames: int = 0
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.skater = Skater()
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.super_timer: int = 0
        self.super_mode: bool = False
        self.trick_color_idx: int = self._rng.randrange(0, 4)
        self.next_trick_idx: int = (self.trick_color_idx + 1) % 4
        self.game_timer: int = GAME_DURATION
        self.last_trick_color: int = -1
        self.pre_commit_color: int = -1
        self.pre_commit_bonus: bool = False
        self.trick_resolved_this_apex: bool = False
        self._osc_frame: int = 0
        self.particles.clear()
        self.floating_texts.clear()
        self._shake_frames = 0

    # ── Pure Logic Methods ────────────────────────────────────────────

    def _advance_trick_color(self) -> None:
        self.trick_color_idx = self.next_trick_idx
        self.next_trick_idx = (self.trick_color_idx + 1) % 4

    def _commit_trick(self, color: int) -> int:
        """Return 0=miss, 1=hit, 2=pre-commit-hit."""
        if self.super_mode:
            return 1
        correct_color = TRICK_COLORS[self.trick_color_idx]
        if self.pre_commit_color == color:
            self.pre_commit_bonus = (color == correct_color)
            self.pre_commit_color = -1
            if self.pre_commit_bonus:
                return 2
            return 0
        if color == correct_color:
            return 1
        return 0

    def _resolve_trick(self, success: int) -> None:
        if success == 0:
            self.combo = 0
            extra_heat = 30.0 if self.pre_commit_bonus is not None and not self.pre_commit_bonus else 20.0
            self.heat = min(MAX_HEAT, self.heat + extra_heat)
            self._spawn_particles(self.skater.x, self.skater.y, 5, GRAY)
            self._spawn_floating_text(self.skater.x, self.skater.y - 10, "MISS", GRAY)
        elif success == 1:
            bonus = 2 if self.pre_commit_bonus else 1
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            pts = 100 * self.combo * bonus
            if self.super_mode:
                pts *= 3
            self.score += pts
            self.heat = max(0.0, self.heat - 5.0)
            trick_color = TRICK_COLORS[self.trick_color_idx]
            self.last_trick_color = trick_color
            label = f"+{pts}"
            if bonus > 1:
                label = f"+{pts} x2"
            self._spawn_floating_text(self.skater.x, self.skater.y - 10, label, trick_color)
            self._spawn_particles(self.skater.x, self.skater.y, 12, trick_color)
            if self.combo >= COMBO_THRESHOLD and not self.super_mode:
                self._activate_super()
        elif success == 2:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            pts = 100 * self.combo * 2
            if self.super_mode:
                pts *= 3
            self.score += pts
            self.heat = max(0.0, self.heat - 5.0)
            trick_color = TRICK_COLORS[self.trick_color_idx]
            self.last_trick_color = trick_color
            self._spawn_floating_text(self.skater.x, self.skater.y - 10, f"+{pts} x2 BONUS", YELLOW)
            self._spawn_particles(self.skater.x, self.skater.y, 16, trick_color)
            if self.combo >= COMBO_THRESHOLD and not self.super_mode:
                self._activate_super()
        self.pre_commit_bonus = False
        self.pre_commit_color = -1
        self.trick_resolved_this_apex = True

    def _activate_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self._spawn_floating_text(self.skater.x, self.skater.y - 25, "SUPER!", LIME)
        self._spawn_particles(self.skater.x, self.skater.y, 20, LIME)
        self._spawn_particles(self.skater.x, self.skater.y, 20, YELLOW)
        self._shake_frames = 8

    def _update_super(self) -> None:
        if not self.super_mode:
            return
        self.super_timer -= 1
        if self.super_timer <= 0:
            self.super_mode = False
            self.super_timer = 0

    def _update_heat(self) -> None:
        if self.heat >= MAX_HEAT and self.phase == Phase.PLAYING and not self.super_mode:
            self.phase = Phase.GAME_OVER
            self._spawn_particles(self.skater.x, self.skater.y, 40, RED)
            self._spawn_particles(self.skater.x, self.skater.y, 20, YELLOW)
            self._shake_frames = 4
            return
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_timer(self) -> None:
        self.game_timer -= 1
        if self.game_timer <= 0:
            self.game_timer = 0
            self.phase = Phase.GAME_OVER

    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-2.0, 2.0)
            vy = self._rng.uniform(-3.0, 0.5)
            life = self._rng.randint(15, 30)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=30, color=color))

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y -= 1.0
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    # ── Update ─────────────────────────────────────────────────────────

    def update(self) -> None:
        if self._shake_frames > 0:
            self._shake_frames -= 1

        match self.phase:
            case Phase.TITLE:
                self._update_title()
            case Phase.PLAYING:
                self._update_playing()
            case Phase.GAME_OVER:
                self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.phase = Phase.PLAYING
            self._osc_frame = 0
            self.game_timer = GAME_DURATION

    def _update_playing(self) -> None:
        self._osc_frame += 1
        self._update_physics()
        self._update_super()
        self._update_heat()
        self._update_timer()
        self._update_particles()
        self._update_floating_texts()

        if self.phase != Phase.PLAYING:
            return

        was_in_trick_zone = self.skater.in_trick_zone
        self.skater.in_trick_zone = self.skater.y < RAMP_BOTTOM_Y - TRICK_ZONE_THRESHOLD

        if self.skater.in_trick_zone and not was_in_trick_zone:
            self._advance_trick_color()
            self.trick_resolved_this_apex = False

        if self.skater.at_apex and not self.trick_resolved_this_apex:
            if self.super_mode:
                self._resolve_trick(1)
            else:
                self.heat = min(MAX_HEAT, self.heat + 10.0)
                self.combo = 0
                self._spawn_floating_text(self.skater.x, self.skater.y - 10, "MISS", GRAY)
                self._spawn_particles(self.skater.x, self.skater.y, 5, GRAY)
                self.trick_resolved_this_apex = True

        if not self.super_mode and not self.skater.at_apex:
            for i, key in enumerate((pyxel.KEY_Z, pyxel.KEY_X, pyxel.KEY_C, pyxel.KEY_V)):
                if pyxel.btnp(key):
                    expected_color = TRICK_COLORS[self.trick_color_idx]
                    pressed_color = TRICK_COLORS[i]
                    self.pre_commit_color = pressed_color
                    self.pre_commit_bonus = (pressed_color == expected_color)
                    if not self.skater.in_trick_zone:
                        pass

        if not self.super_mode and self.skater.in_trick_zone and self.skater.at_apex and not self.trick_resolved_this_apex:
            for i, key in enumerate((pyxel.KEY_Z, pyxel.KEY_X, pyxel.KEY_C, pyxel.KEY_V)):
                if pyxel.btnp(key):
                    result = self._commit_trick(TRICK_COLORS[i])
                    self._resolve_trick(result)
                    break
            else:
                if self.pre_commit_color == TRICK_COLORS[self.trick_color_idx]:
                    result = 2
                    self._resolve_trick(result)

        if self.skater.at_apex and self.trick_resolved_this_apex and self.pre_commit_color != -1:
            self.pre_commit_color = -1

    def _update_physics(self) -> None:
        angle = oscillation_angle(self._osc_frame, self.combo)
        self.skater.angle = angle
        self.skater.x = oscillation_x(angle)
        self.skater.y = ramp_y(self.skater.x)
        self.skater.direction = 1 if math.cos(angle) > 0 else -1

    def _update_game_over(self) -> None:
        self._update_particles()
        self._update_floating_texts()
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.phase = Phase.TITLE

    # ── Draw ───────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self._shake_frames > 0:
            ox = self._rng.randint(-3, 3)
            oy = self._rng.randint(-3, 3)
            pyxel.camera(ox, oy)
        else:
            pyxel.camera(0, 0)

        match self.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.PLAYING:
                self._draw_game()
            case Phase.GAME_OVER:
                self._draw_game()
                self._draw_game_over()

    def _draw_title(self) -> None:
        sky_colors = (BLACK, NAVY, NAVY, DARK_BLUE)
        for i, c in enumerate(sky_colors):
            pyxel.rect(0, i * 8, SCREEN_W, 8, c)

        self._text_center(SCREEN_W // 2, 40, "SKATE CHAIN", WHITE)
        self._text_center(SCREEN_W // 2, 56, "COLOR-MATCH VERT RAMP", GRAY)

        ramp_y_top = RAMP_BOTTOM_Y + 10
        pyxel.line(RAMP_LEFT_EDGE_X, ramp_y_top, RAMP_FLAT_LEFT, RAMP_BOTTOM_Y + 10, CYAN)
        pyxel.line(RAMP_FLAT_LEFT, RAMP_BOTTOM_Y + 10, RAMP_FLAT_RIGHT, RAMP_BOTTOM_Y + 10, CYAN)
        pyxel.line(RAMP_FLAT_RIGHT, RAMP_BOTTOM_Y + 10, RAMP_RIGHT_EDGE_X, ramp_y_top, CYAN)
        pyxel.tri(
            RAMP_LEFT_EDGE_X + 15, ramp_y_top - 20,
            RAMP_LEFT_EDGE_X + 15, ramp_y_top + 5,
            RAMP_LEFT_EDGE_X + 35, ramp_y_top - 7,
            WHITE,
        )

        self._text_center(SCREEN_W // 2, 130, "HOW TO PLAY", WHITE)
        y = 148
        for i in range(4):
            c = TRICK_COLORS[i]
            label = TRICK_KEY_LABELS[i]
            name = TRICK_NAMES[i]
            text = f"[{label}] {name} TRICK"
            self._text_center(SCREEN_W // 2, y, text, c)
            y += 14

        self._text_center(SCREEN_W // 2, 210, "MATCH COLOR BEFORE APEX", GRAY)
        if (pyxel.frame_count // 30) % 2 == 0:
            self._text_center(SCREEN_W // 2, 226, "PRESS SPACE TO START", WHITE)

    def _draw_game(self) -> None:
        self._draw_sky()
        self._draw_halfpipe()
        self._draw_trick_indicator()
        self._draw_skater()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_sky(self) -> None:
        sky_colors = (BLACK, NAVY, NAVY, DARK_BLUE, DARK_BLUE, BLACK, BLACK)
        for i, c in enumerate(sky_colors):
            pyxel.rect(0, i * 12, SCREEN_W, 12, c)

    def _draw_halfpipe(self) -> None:
        prev_y = ramp_y(0)
        for px in range(1, SCREEN_W):
            cy = ramp_y(float(px))
            pyxel.line(px - 1, prev_y, px, cy, CYAN)
            pyxel.line(px - 1, prev_y + 1, px, cy + 1, GRAY)
            prev_y = cy
        pyxel.line(0, RAMP_BOTTOM_Y + 2, SCREEN_W, RAMP_BOTTOM_Y + 2, GRAY)
        pyxel.rect(0, int(RAMP_BOTTOM_Y) + 3, SCREEN_W, SCREEN_H - int(RAMP_BOTTOM_Y) - 3, GRAY)

    def _draw_trick_indicator(self) -> None:
        if self.skater.at_apex and self.skater.in_trick_zone:
            trick_color = TRICK_COLORS[self.trick_color_idx]
            ramp_edge_x = RAMP_LEFT_EDGE_X + 10 if self.skater.which_side == 0 else RAMP_RIGHT_EDGE_X - 10
            indicator_y = int(RAMP_TOP_Y) - 10
            pyxel.circ(ramp_edge_x, indicator_y, 8, trick_color)
            pyxel.circb(ramp_edge_x, indicator_y, 8, WHITE)
            label = TRICK_KEY_LABELS[self.trick_color_idx]
            pyxel.text(ramp_edge_x - 3, indicator_y - 5, label, WHITE)

    def _draw_skater(self) -> None:
        sx = int(self.skater.x)
        sy = int(self.skater.y)
        body_color = PEACH
        board_color = WHITE

        if self.super_mode:
            rainbow = (RED, YELLOW, LIME, CYAN, DARK_BLUE)
            body_color = rainbow[(pyxel.frame_count // 4) % len(rainbow)]

        dir_x = 1 if self.skater.direction > 0 else -1

        pyxel.line(sx, sy - 18, sx, sy - 6, body_color)
        pyxel.tri(
            sx - 4, sy - 18,
            sx + 4, sy - 18,
            sx, sy - 24,
            body_color,
        )
        pyxel.line(sx - 6, sy - 10, sx + 6 * dir_x, sy - 14, body_color)
        pyxel.line(sx - 6, sy - 8, sx + 6 * dir_x, sy - 12, body_color)
        pyxel.line(sx - 10, sy - 6, sx + 10, sy - 6, board_color)
        pyxel.line(sx - 10, sy - 5, sx + 10, sy - 5, board_color)
        pyxel.rect(sx - 4, sy - 5, 8, 3, GRAY)
        pyxel.rect(sx - 4, sy - 3, 8, 3, GRAY)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 30.0
            if alpha > 0.3:
                pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 30.0
            if alpha > 0.3:
                pyxel.text(int(ft.x) - len(ft.text) * 4 // 2, int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        timer_sec = max(0, self.game_timer // FPS)
        pyxel.text(4, 4, f"TIME: {timer_sec}", WHITE)
        pyxel.text(4, 14, f"SCORE: {self.score}", WHITE)
        combo_color = LIME if self.combo >= COMBO_THRESHOLD else YELLOW if self.combo >= 3 else WHITE
        pyxel.text(4, 24, f"COMBO: x{self.combo}", combo_color)

        bar_x = 200
        bar_w = 100
        bar_y = 4
        bar_h = 8
        heat_pct = self.heat / MAX_HEAT
        bar_color = RED if heat_pct > 0.7 else YELLOW if heat_pct > 0.4 else GREEN
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        pyxel.rect(bar_x, bar_y, int(bar_w * heat_pct), bar_h, bar_color)
        pyxel.text(bar_x + 2, bar_y + 10, "HEAT", GRAY)

        if self.super_mode:
            super_left = max(0, self.super_timer * bar_w // SUPER_DURATION)
            pyxel.rect(bar_x, bar_y + 14, super_left, 4, LIME)
            rainbow_label = ("S", "U", "P", "E", "R")
            for i, ch in enumerate(rainbow_label):
                c = (RED, YELLOW, LIME, CYAN, DARK_BLUE)[i]
                pyxel.text(SCREEN_W // 2 - 12 + i * 6, 4, ch, c)

        if self.pre_commit_color >= 0:
            pyxel.text(4, 34, "PRE-COMMIT LOCKED", YELLOW)
            pyxel.rect(4, 44, 20, 8, self.pre_commit_color)
            pyxel.rectb(4, 44, 20, 8, WHITE)

    def _draw_game_over(self) -> None:
        overlay_y = SCREEN_H // 2 - 60
        pyxel.rect(0, overlay_y, SCREEN_W, 120, BLACK)
        pyxel.rectb(0, overlay_y, SCREEN_W, 120, WHITE)
        self._text_center(SCREEN_W // 2, SCREEN_H // 2 - 48, "WIPEOUT!", RED)
        self._text_center(SCREEN_W // 2, SCREEN_H // 2 - 28, f"SCORE: {self.score}", WHITE)
        self._text_center(SCREEN_W // 2, SCREEN_H // 2 - 10, f"MAX COMBO: x{self.max_combo}", YELLOW)
        if (pyxel.frame_count // 30) % 2 == 0:
            self._text_center(SCREEN_W // 2, SCREEN_H // 2 + 20, "PRESS SPACE TO RETRY", WHITE)

    @staticmethod
    def _text_center(x: int, y: int, text: str, color: int) -> None:
        px = x - len(text) * 4 // 2
        pyxel.text(px, y, text, color)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
