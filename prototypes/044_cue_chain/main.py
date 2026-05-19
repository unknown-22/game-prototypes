"""CUE CHAIN — Color-Match Billiards prototype.

Reinterpreted from game_idea_factory #1 (score 31.8, deckbuilder roguelite):
  "same card consecutively use mutates" → same-color ball pocketed consecutively = COMBO
  "chain collapse UI" → COMBO ≥ 3 triggers CHAIN BREAK super-mode

Core mechanic: Aim-and-shoot billiards with color-match combo system.
Most fun moment: Sinking 3+ same-color balls in a chain, triggering CHAIN BREAK,
and watching the rainbow cue ball ricochet for massive 3x score.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if not TYPE_CHECKING:
    import pyxel

# ── Config ────────────────────────────────────────────────────────────────────
SCREEN_W = 256
SCREEN_H = 256
DISPLAY_SCALE = 2

TABLE_LEFT = 20
TABLE_TOP = 20
TABLE_RIGHT = 236
TABLE_BOTTOM = 236
TABLE_W = TABLE_RIGHT - TABLE_LEFT
TABLE_H = TABLE_BOTTOM - TABLE_TOP

POCKET_RADIUS = 7
BALL_RADIUS = 5
BALL_COUNT = 6
MAX_POWER = 8.0
FRICTION = 0.985
STOP_THRESHOLD = 0.3
COMBO_FOR_CHAIN_BREAK = 3
CHAIN_BREAK_MULT = 3
GAME_TIME_SECS = 60  # seconds

# Pyxel palette indices for ball colors (Red, DarkBlue, Yellow, Green)
# Using raw int values to avoid TYPE_CHECKING guard issues at module level.
COLOR_IDS: tuple[int, ...] = (8, 6, 10, 3)
COLOR_NAMES: tuple[str, ...] = ("RED", "BLUE", "YELLOW", "GREEN")

POCKET_POSITIONS: tuple[tuple[int, int], ...] = (
    (TABLE_LEFT, TABLE_TOP),                     # top-left
    (TABLE_RIGHT, TABLE_TOP),                    # top-right
    (TABLE_LEFT, TABLE_BOTTOM),                  # bottom-left
    (TABLE_RIGHT, TABLE_BOTTOM),                 # bottom-right
    (TABLE_LEFT, TABLE_TOP + TABLE_H // 2),      # mid-left
    (TABLE_RIGHT, TABLE_TOP + TABLE_H // 2),     # mid-right
)


# ── Data Classes ──────────────────────────────────────────────────────────────
@dataclass
class Ball:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    color: int = -1  # -1 = cue ball, 0-3 = colored
    active: bool = True


class Phase(Enum):
    AIMING = auto()
    MOVING = auto()
    GAME_OVER = auto()


# ── Game ──────────────────────────────────────────────────────────────────────
class Game:
    """CUE CHAIN billiards game."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CUE CHAIN", display_scale=DISPLAY_SCALE)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self._rng = random.Random()
        self.phase = Phase.AIMING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.chain_break = False
        self.game_timer = GAME_TIME_SECS * 30  # frames (pyxel runs at 30fps default)
        self.cue_ball = Ball(
            TABLE_LEFT + TABLE_W // 2, TABLE_TOP + TABLE_H // 2
        )
        self.balls: list[Ball] = []
        self._aim_start_x: float = 0.0
        self._aim_start_y: float = 0.0
        self._aiming: bool = False
        self._last_pocketed_color: int = -1
        self._spawn_balls()

    # ── Spawning ──────────────────────────────────────────────────────────

    def _spawn_balls(self) -> None:
        self.balls.clear()
        for _ in range(BALL_COUNT):
            self._spawn_one_ball()

    def _spawn_one_ball(self) -> None:
        color = self._rng.randint(0, 3)
        for _ in range(80):
            x = self._rng.uniform(
                TABLE_LEFT + BALL_RADIUS + 8, TABLE_RIGHT - BALL_RADIUS - 8
            )
            y = self._rng.uniform(
                TABLE_TOP + BALL_RADIUS + 8, TABLE_BOTTOM - BALL_RADIUS - 8
            )
            if not self._ball_overlaps(x, y):
                self.balls.append(Ball(x=x, y=y, color=color))
                return
        # Fallback: place far from cue ball
        self.balls.append(
            Ball(x=TABLE_LEFT + 60, y=TABLE_TOP + 60, color=color)
        )

    def _ball_overlaps(self, x: float, y: float) -> bool:
        min_dist = BALL_RADIUS * 2 + 4
        if math.hypot(x - self.cue_ball.x, y - self.cue_ball.y) < min_dist:
            return True
        for b in self.balls:
            if b.active and math.hypot(x - b.x, y - b.y) < min_dist:
                return True
        return False

    # ── State Checks ──────────────────────────────────────────────────────

    def _all_stopped(self) -> bool:
        if (
            self.cue_ball.active
            and (abs(self.cue_ball.vx) > STOP_THRESHOLD or abs(self.cue_ball.vy) > STOP_THRESHOLD)
        ):
            return False
        for b in self.balls:
            if b.active and (
                abs(b.vx) > STOP_THRESHOLD or abs(b.vy) > STOP_THRESHOLD
            ):
                return False
        return True

    # ── Update ────────────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.GAME_OVER:
            if (
                pyxel.btnp(pyxel.KEY_R)
                or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            ):
                self.reset()
            return

        self.game_timer -= 1
        if self.game_timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        if self.phase == Phase.AIMING:
            self._update_aiming()
        elif self.phase == Phase.MOVING:
            self._update_physics()
            if self._all_stopped():
                self._finalize_motion()

    def _update_aiming(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx, my = pyxel.mouse_x, pyxel.mouse_y
            if math.hypot(mx - self.cue_ball.x, my - self.cue_ball.y) < BALL_RADIUS + 12:
                self._aim_start_x = float(mx)
                self._aim_start_y = float(my)
                self._aiming = True

        if self._aiming and pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT):
            mx, my = pyxel.mouse_x, pyxel.mouse_y
            dx = self._aim_start_x - mx
            dy = self._aim_start_y - my
            dist = math.hypot(dx, dy)
            if dist > 2.0:
                power = min(dist / 8.0, MAX_POWER)
                # Velocity direction: from release point toward click-start
                # (ball shoots opposite of drag direction)
                angle = math.atan2(dy, dx)
                self.cue_ball.vx = math.cos(angle) * power
                self.cue_ball.vy = math.sin(angle) * power
                self.combo = 0
                self.chain_break = False
                self.phase = Phase.MOVING
            self._aiming = False

    def _update_physics(self) -> None:
        # Friction
        self.cue_ball.vx *= FRICTION
        self.cue_ball.vy *= FRICTION
        for b in self.balls:
            if b.active:
                b.vx *= FRICTION
                b.vy *= FRICTION

        # Move
        if self.cue_ball.active:
            self.cue_ball.x += self.cue_ball.vx
            self.cue_ball.y += self.cue_ball.vy
        for b in self.balls:
            if b.active:
                b.x += b.vx
                b.y += b.vy

        # Ball-ball collisions
        if self.cue_ball.active:
            for b in self.balls:
                if b.active:
                    self._resolve_collision(self.cue_ball, b)
        for i in range(len(self.balls)):
            if not self.balls[i].active:
                continue
            for j in range(i + 1, len(self.balls)):
                if not self.balls[j].active:
                    continue
                self._resolve_collision(self.balls[i], self.balls[j])

        # Wall collisions
        if self.cue_ball.active:
            self._clamp_to_table(self.cue_ball)
        for b in self.balls:
            if b.active:
                self._clamp_to_table(b)

        # Pocket check
        if self.cue_ball.active:
            self._check_pocket(self.cue_ball, is_cue=True)
        for b in self.balls:
            if b.active:
                self._check_pocket(b, is_cue=False)

    def _resolve_collision(self, a: Ball, b: Ball) -> None:
        dx = b.x - a.x
        dy = b.y - a.y
        dist = math.hypot(dx, dy)
        if dist >= BALL_RADIUS * 2 or dist < 0.0001:
            return

        # Separate overlapping balls
        overlap = BALL_RADIUS * 2 - dist
        if dist > 0.0001:
            nx = dx / dist
            ny = dy / dist
        else:
            nx, ny = 1.0, 0.0
        a.x -= nx * overlap / 2
        a.y -= ny * overlap / 2
        b.x += nx * overlap / 2
        b.y += ny * overlap / 2

        # Elastic collision (equal-mass balls)
        dvx = a.vx - b.vx
        dvy = a.vy - b.vy
        dot = dvx * nx + dvy * ny
        if dot > 0:
            a.vx -= dot * nx
            a.vy -= dot * ny
            b.vx += dot * nx
            b.vy += dot * ny

    def _clamp_to_table(self, b: Ball) -> None:
        r = BALL_RADIUS
        if b.x - r < TABLE_LEFT:
            b.x = TABLE_LEFT + r
            b.vx = abs(b.vx) * 0.8
        elif b.x + r > TABLE_RIGHT:
            b.x = TABLE_RIGHT - r
            b.vx = -abs(b.vx) * 0.8
        if b.y - r < TABLE_TOP:
            b.y = TABLE_TOP + r
            b.vy = abs(b.vy) * 0.8
        elif b.y + r > TABLE_BOTTOM:
            b.y = TABLE_BOTTOM - r
            b.vy = -abs(b.vy) * 0.8

    def _check_pocket(self, b: Ball, *, is_cue: bool = False) -> None:
        for px, py in POCKET_POSITIONS:
            if math.hypot(b.x - px, b.y - py) < POCKET_RADIUS + BALL_RADIUS:
                if is_cue:
                    b.active = False
                    b.vx = 0.0
                    b.vy = 0.0
                else:
                    self._pocket_ball(b)
                break

    def _pocket_ball(self, b: Ball) -> None:
        b.active = False
        b.vx = 0.0
        b.vy = 0.0
        color = b.color

        # Combo: same color consecutively (or chain_break ignores color)
        if self.combo == 0 or self._last_pocketed_color == color or self.chain_break:
            self.combo += 1
        else:
            self.combo = 1  # wrong color breaks combo

        self._last_pocketed_color = color
        self.max_combo = max(self.max_combo, self.combo)

        # Score
        base_score = 100
        mult = CHAIN_BREAK_MULT * self.combo if self.chain_break else self.combo
        self.score += base_score * mult

        # Chain break: COMBO >= 3 activates one-shot super-mode
        if self.combo >= COMBO_FOR_CHAIN_BREAK and not self.chain_break:
            self.chain_break = True

        # Replace pocketed ball
        self._spawn_one_ball()

    def _finalize_motion(self) -> None:
        """Called when all balls stop — transition back to AIMING."""
        self.cue_ball.vx = 0.0
        self.cue_ball.vy = 0.0
        for b in self.balls:
            b.vx = 0.0
            b.vy = 0.0

        # Respawn cue ball if pocketed
        if not self.cue_ball.active:
            self.cue_ball = Ball(
                TABLE_LEFT + TABLE_W // 2, TABLE_TOP + TABLE_H // 2
            )

        # Keep cue ball on table
        self.cue_ball.x = max(
            TABLE_LEFT + BALL_RADIUS,
            min(TABLE_RIGHT - BALL_RADIUS, self.cue_ball.x),
        )
        self.cue_ball.y = max(
            TABLE_TOP + BALL_RADIUS,
            min(TABLE_BOTTOM - BALL_RADIUS, self.cue_ball.y),
        )

        # Push cue ball away from overlapping colored balls
        self._separate_cue_ball()

        # Chain break expires after one shot (already used)
        self.chain_break = False
        self.phase = Phase.AIMING

    def _separate_cue_ball(self) -> None:
        for _ in range(5):  # iterate to handle multiple overlaps
            for b in self.balls:
                if not b.active:
                    continue
                dx = self.cue_ball.x - b.x
                dy = self.cue_ball.y - b.y
                dist = math.hypot(dx, dy)
                if dist < BALL_RADIUS * 2 + 3 and dist > 0.001:
                    nx = dx / dist
                    ny = dy / dist
                    self.cue_ball.x = b.x + nx * (BALL_RADIUS * 2 + 3)
                    self.cue_ball.y = b.y + ny * (BALL_RADIUS * 2 + 3)
            # Re-clamp
            self.cue_ball.x = max(
                TABLE_LEFT + BALL_RADIUS,
                min(TABLE_RIGHT - BALL_RADIUS, self.cue_ball.x),
            )
            self.cue_ball.y = max(
                TABLE_TOP + BALL_RADIUS,
                min(TABLE_BOTTOM - BALL_RADIUS, self.cue_ball.y),
            )

    # ── Draw ──────────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_NAVY)

        # Table frame
        pyxel.rect(
            TABLE_LEFT - 6, TABLE_TOP - 6, TABLE_W + 12, TABLE_H + 12,
            pyxel.COLOR_BROWN,
        )
        # Felt
        pyxel.rect(TABLE_LEFT, TABLE_TOP, TABLE_W, TABLE_H, pyxel.COLOR_GREEN)
        # Inner cushion line
        pyxel.rectb(
            TABLE_LEFT - 1, TABLE_TOP - 1, TABLE_W + 2, TABLE_H + 2,
            pyxel.COLOR_BROWN,
        )

        # Pockets
        for px, py in POCKET_POSITIONS:
            pyxel.circ(px, py, POCKET_RADIUS, pyxel.COLOR_BLACK)

        # Colored balls
        for b in self.balls:
            if b.active:
                pyxel.circ(int(b.x), int(b.y), BALL_RADIUS, COLOR_IDS[b.color])
                pyxel.circb(int(b.x), int(b.y), BALL_RADIUS, pyxel.COLOR_WHITE)

        # Cue ball
        if self.cue_ball.active:
            cue_color: int = pyxel.COLOR_PEACH if self.chain_break else pyxel.COLOR_WHITE
            pyxel.circ(int(self.cue_ball.x), int(self.cue_ball.y), BALL_RADIUS, cue_color)
            pyxel.circb(
                int(self.cue_ball.x), int(self.cue_ball.y),
                BALL_RADIUS, pyxel.COLOR_BLACK,
            )

        # Aim line (while dragging)
        if self.phase == Phase.AIMING and self._aiming:
            mx, my = pyxel.mouse_x, pyxel.mouse_y
            dx = self._aim_start_x - mx
            dy = self._aim_start_y - my
            # Dashed aim line
            end_x = int(self.cue_ball.x + dx * 2)
            end_y = int(self.cue_ball.y + dy * 2)
            pyxel.line(
                int(self.cue_ball.x), int(self.cue_ball.y),
                end_x, end_y, pyxel.COLOR_GRAY,
            )
            # Power indicator circle at mouse
            power = min(math.hypot(dx, dy) / 8.0, MAX_POWER) / MAX_POWER
            pcol = pyxel.COLOR_RED if power > 0.7 else pyxel.COLOR_YELLOW if power > 0.3 else pyxel.COLOR_GREEN
            pyxel.circb(mx, my, 8, pcol)

        # ── HUD ──
        timer_sec = max(0, self.game_timer // 30)
        pyxel.text(5, 2, f"TIME:{timer_sec:02d}", pyxel.COLOR_WHITE)
        pyxel.text(5, 10, f"SCORE:{self.score}", pyxel.COLOR_YELLOW)

        # Combo display
        if self.chain_break:
            combo_color = pyxel.COLOR_PEACH
            combo_text = f"COMBO:{self.combo}*{CHAIN_BREAK_MULT}"
        elif self.combo >= COMBO_FOR_CHAIN_BREAK - 1:
            combo_color = pyxel.COLOR_YELLOW
            combo_text = f"COMBO:{self.combo}"
        else:
            combo_color = pyxel.COLOR_WHITE
            combo_text = f"COMBO:{self.combo}"
        pyxel.text(5, 18, combo_text, combo_color)

        if self.chain_break:
            pyxel.text(100, 2, "CHAIN BREAK!", pyxel.COLOR_PEACH)

        # ── Game Over Overlay ──
        if self.phase == Phase.GAME_OVER:
            pyxel.rect(48, 88, 160, 80, pyxel.COLOR_BLACK)
            pyxel.rectb(48, 88, 160, 80, pyxel.COLOR_WHITE)
            pyxel.text(72, 100, "GAME OVER", pyxel.COLOR_RED)
            pyxel.text(60, 116, f"SCORE: {self.score}", pyxel.COLOR_WHITE)
            pyxel.text(60, 132, f"MAX COMBO: {self.max_combo}", pyxel.COLOR_YELLOW)
            pyxel.text(56, 150, "CLICK TO RETRY", pyxel.COLOR_GRAY)


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    Game()
