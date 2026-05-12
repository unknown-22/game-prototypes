"""ELEMENT DROP — Pachinko synthesis prototype.

Reinterpreted from game_idea_factory idea #1 (Score 31.65):
  "Effects synthesize into one compressed card" → same-element peg chains
    double the combo multiplier (x1→x2→x4→x8→x16).
  "Cost is future hand, not HP" → future ball preview limits
    how many drops you can plan ahead (3 visible).

Core loop: aim drop → watch ball bounce through pegs → combo multiplier
escalates → tally score → next ball. Clear all TARGET pegs to win.

The most fun moment: Dropping a ball through a tight corridor of
same-element pegs and watching the multiplier explode as the ball
carves a path of destruction.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import IntEnum

import pyxel

# ── Config ────────────────────────────────────────────────────────────────────

SCREEN_W = 256
SCREEN_H = 256
DISPLAY_SCALE = 2

GRAVITY = 0.17
BOUNCE_DAMP = 0.62
BALL_START_VY = 2.2
BALL_R = 3
PEG_R = 4
BALLS_PER_GAME = 10
FUTURE_SHOWN = 3
TARGET_FRACTION = 0.10

# pyxel color palette (indices)
C_BLACK = 0
C_PURPLE = 2
C_GREEN = 3
C_BROWN = 4
C_NAVY = 5
C_LIGHT_BLUE = 6
C_WHITE = 7
C_RED = 8
C_ORANGE = 9
C_YELLOW = 10
C_CYAN = 11
C_LIME = 12  # NOTE: pyxel type stubs call this COLOR_LIME, index 12
C_GRAY = 13
C_PINK = 14
C_PEACH = 15

# 5 elements + target
ELEMENT_COLORS: list[int] = [C_RED, C_CYAN, C_BROWN, C_LIME, C_PURPLE]
ELEMENT_NAMES: list[str] = ["FIRE", "WATER", "EARTH", "AIR", "AETHER"]
ELEMENT_LABELS: list[str] = ["Fr", "Wa", "Ea", "Ai", "Ae"]
TARGET_COLOR = C_YELLOW


class Phase(IntEnum):
    AIM = 0
    DROP = 1
    RESULT = 2
    GAMEOVER = 3


@dataclass
class Peg:
    x: float
    y: float
    element: int  # 0-4 for normal elements, 5 for target
    alive: bool = True
    radius: float = PEG_R


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    element: int  # current ball element (determines match)
    alive: bool = True
    hits: int = 0  # consecutive same-element hits in this drop


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 1


@dataclass
class FloatText:
    x: float
    y: float
    text: str
    life: int
    color: int
    vy: float = -1.0


# ── Game ──────────────────────────────────────────────────────────────────────


class Game:
    """Pachinko-style ball-drop game with element synthesis combos."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Element Drop", display_scale=DISPLAY_SCALE)
        pyxel.mouse(True)
        self._reset()
        pyxel.run(self._update, self._draw)

    # ── State ──────────────────────────────────────────────────────────────

    def _reset(self) -> None:
        self.phase: Phase = Phase.AIM
        self.pegs: list[Peg] = []
        self.ball: Ball | None = None
        self.balls_left: int = BALLS_PER_GAME
        self.score: int = 0
        self.high_score: int = 0
        self.particles: list[Particle] = []
        self.float_texts: list[FloatText] = []
        self.combo_depth: int = 0
        self.last_element: int | None = None
        self.future_balls: list[int] = [
            random.randint(0, 4) for _ in range(FUTURE_SHOWN)
        ]
        self.targets_total: int = 0
        self.targets_cleared: int = 0
        self.result_timer: int = 0
        self._generate_board()

    def _generate_board(self) -> None:
        """Generate a fresh peg board with random elements."""
        self.pegs.clear()
        self.targets_total = 0
        self.targets_cleared = 0
        rows = 8
        cols = 12
        spacing_x = 20
        spacing_y = 20
        start_y = 32

        for row in range(rows):
            num_pegs = cols if row % 2 == 0 else cols - 1
            ox = (SCREEN_W - (num_pegs - 1) * spacing_x) / 2
            if row % 2 == 1:
                ox += spacing_x / 2
            for col in range(num_pegs):
                x = ox + col * spacing_x
                y = start_y + row * spacing_y
                # skip some random slots for variety
                if random.random() < 0.18:
                    continue
                if random.random() < TARGET_FRACTION:
                    elem = 5  # target
                    self.targets_total += 1
                else:
                    elem = random.randint(0, 4)
                self.pegs.append(Peg(x, y, elem))

        # guarantee at least 6 target pegs
        while self.targets_total < 6:
            alive_pegs = [p for p in self.pegs if p.element != 5 and p.alive]
            if not alive_pegs:
                break
            chosen = random.choice(alive_pegs)
            chosen.element = 5
            self.targets_total += 1

    def _next_ball_element(self) -> int:
        """Pop the next ball element from the future queue."""
        elem = self.future_balls.pop(0)
        self.future_balls.append(random.randint(0, 4))
        return elem

    # ── Update ─────────────────────────────────────────────────────────────

    def _update(self) -> None:
        if self.phase == Phase.AIM:
            self._update_aim()
        elif self.phase == Phase.DROP:
            self._update_drop()
        elif self.phase == Phase.RESULT:
            self._update_result()
        elif self.phase == Phase.GAMEOVER:
            self._update_gameover()

        # particles always update
        self._update_particles()
        self._update_float_texts()

    def _update_aim(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and self.balls_left > 0:
            mouse_x = pyxel.mouse_x
            mouse_x = max(20, min(SCREEN_W - 20, mouse_x))
            element = self._next_ball_element()
            self.ball = Ball(
                x=mouse_x, y=16, vx=0.0, vy=BALL_START_VY, element=element
            )
            self.balls_left -= 1
            self.combo_depth = 0
            self.last_element = None
            self.phase = Phase.DROP

    def _update_drop(self) -> None:
        if self.ball is None:
            self.phase = Phase.AIM
            return

        b = self.ball
        if not b.alive:
            return

        # apply gravity
        b.vy += GRAVITY

        # move
        b.x += b.vx
        b.y += b.vy

        # wall bounces (left/right)
        if b.x < BALL_R:
            b.x = BALL_R
            b.vx = abs(b.vx) * BOUNCE_DAMP
        elif b.x > SCREEN_W - BALL_R:
            b.x = SCREEN_W - BALL_R
            b.vx = -abs(b.vx) * BOUNCE_DAMP

        # ceiling bounce
        if b.y < BALL_R:
            b.y = BALL_R
            b.vy = abs(b.vy) * BOUNCE_DAMP

        # check if ball fell out bottom
        if b.y > SCREEN_H + 10:
            b.alive = False
            self.ball = None
            self.phase = Phase.RESULT
            self.result_timer = 60
            # check game state
            if self.targets_cleared >= self.targets_total and self.targets_total > 0:
                self.score += 500  # board clear bonus
                self._spawn_float_text(SCREEN_W / 2, SCREEN_H / 2, "CLEAR!", 90, C_YELLOW)
                self._spawn_burst(SCREEN_W / 2, SCREEN_H / 2, C_YELLOW, 20)
            elif self.balls_left <= 0:
                if self.score > self.high_score:
                    self.high_score = self.score
            return

        # check peg collisions
        for peg in self.pegs:
            if not peg.alive:
                continue
            dx = b.x - peg.x
            dy = b.y - peg.y
            dist = math.hypot(dx, dy)
            min_dist = BALL_R + peg.radius
            if dist < min_dist and dist > 0.001:
                # collision!
                peg.alive = False
                b.hits += 1

                # combo logic: ball element determines synthesis chain
                # same-element peg = synthesis, different = reset, target = bonus
                is_match = peg.element == b.element
                if peg.element == 5:
                    # target peg: always counts
                    self.targets_cleared += 1
                    mult = max(1, 2**self.combo_depth)
                    pts = 30 * mult
                    self.last_element = None  # target resets combo tracking
                    self.combo_depth = 0
                elif is_match:
                    # same element as ball = synthesis chain
                    if self.last_element == b.element:
                        self.combo_depth += 1
                    else:
                        self.combo_depth = 0
                    self.last_element = b.element
                    mult = max(1, 2**self.combo_depth)
                    pts = 10 * mult
                else:
                    # different element = reset
                    self.combo_depth = 0
                    self.last_element = peg.element
                    mult = 1
                    pts = 5

                self.score += pts

                # visual feedback
                if self.combo_depth >= 1:
                    color = ELEMENT_COLORS[b.element]
                    self._spawn_float_text(
                        b.x, b.y, f"x{mult}", 40, color
                    )
                self._spawn_burst(peg.x, peg.y, ELEMENT_COLORS[peg.element % 5], 4)

                # bounce physics: reflect velocity across normal
                nx = dx / dist
                ny = dy / dist
                dot = b.vx * nx + b.vy * ny
                # only reflect if moving toward peg
                if dot < 0:
                    b.vx -= 2 * dot * nx
                    b.vy -= 2 * dot * ny
                    b.vx *= BOUNCE_DAMP
                    b.vy *= BOUNCE_DAMP

                # push ball out of peg
                overlap = min_dist - dist
                b.x += nx * overlap
                b.y += ny * overlap

                # add tiny random nudge for variety
                b.vx += random.uniform(-0.25, 0.25)
                b.vy += random.uniform(-0.15, 0.15)

                break  # one peg per frame

        # check if ball is stuck (very slow + in play area)
        speed = math.hypot(b.vx, b.vy)
        if speed < 0.3 and b.y > 20 and b.y < SCREEN_H - 10:
            b.alive = False
            self.ball = None
            self.phase = Phase.RESULT
            self.result_timer = 60
            if self.balls_left <= 0 and self.score > self.high_score:
                self.high_score = self.score

    def _update_result(self) -> None:
        self.result_timer -= 1
        if self.result_timer <= 0:
            if self.balls_left <= 0 or (
                self.targets_cleared >= self.targets_total and self.targets_total > 0
            ):
                self.phase = Phase.GAMEOVER
            else:
                self.phase = Phase.AIM

    def _update_gameover(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            if self.score > self.high_score:
                self.high_score = self.score
            self._reset()
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if self.score > self.high_score:
                self.high_score = self.score
            self._reset()

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05  # particle gravity
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_float_texts(self) -> None:
        for ft in self.float_texts[:]:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life <= 0:
                self.float_texts.remove(ft)

    # ── Draw ───────────────────────────────────────────────────────────────

    def _draw(self) -> None:
        pyxel.cls(C_BLACK)

        # draw pegs
        for peg in self.pegs:
            if not peg.alive:
                continue
            if peg.element == 5:
                color = TARGET_COLOR
            else:
                color = ELEMENT_COLORS[peg.element]
            pyxel.circ(peg.x, peg.y, peg.radius, color)

        # draw ball
        if self.ball is not None and self.ball.alive:
            b = self.ball
            color = ELEMENT_COLORS[b.element]
            pyxel.circ(b.x, b.y, BALL_R, color)
            # glow for high combo
            if self.combo_depth >= 2:
                glow_r = BALL_R + min(self.combo_depth, 5)
                pyxel.circb(b.x, b.y, glow_r, C_WHITE)

        # draw aim line
        if self.phase == Phase.AIM:
            mx = pyxel.mouse_x
            mx = max(20, min(SCREEN_W - 20, mx))
            pyxel.line(mx, 16, mx, SCREEN_H, C_GRAY)
            # drop preview ball
            if self.future_balls:
                color = ELEMENT_COLORS[self.future_balls[0]]
                pyxel.circ(mx, 12, BALL_R, color)

        # draw particles
        for p in self.particles:
            alpha = max(0, min(15, p.life * 2))
            if alpha > 0:
                pyxel.pset(p.x, p.y, p.color)

        # draw float texts
        for ft in self.float_texts:
            alpha = max(0, min(15, ft.life))
            if alpha > 0:
                pyxel.text(ft.x, ft.y, ft.text, ft.color)

        # ── UI ──
        # top bar
        pyxel.rect(0, 0, SCREEN_W, 10, C_NAVY)
        pyxel.text(2, 2, f"BALLS:{self.balls_left}", C_WHITE)
        pyxel.text(80, 2, f"SCORE:{self.score}", C_YELLOW)
        pyxel.text(170, 2, f"TGT:{self.targets_cleared}/{self.targets_total}", C_ORANGE)

        # future balls preview
        fx = SCREEN_W - 50
        for i, elem in enumerate(self.future_balls):
            if elem < 5:
                pyxel.circ(fx + i * 14, 5, 3, ELEMENT_COLORS[elem])

        # bottom bar — current element + combo
        pyxel.rect(0, SCREEN_H - 12, SCREEN_W, 12, C_NAVY)
        if self.ball is not None and self.ball.alive:
            elem = self.ball.element
            pyxel.text(2, SCREEN_H - 10, f"NOW:{ELEMENT_NAMES[elem]}", ELEMENT_COLORS[elem])
            if self.combo_depth > 0:
                mult = 2**self.combo_depth
                pyxel.text(
                    100, SCREEN_H - 10, f"SYNTH x{mult}", C_WHITE
                )
        elif self.phase == Phase.AIM and self.future_balls:
            elem = self.future_balls[0]
            pyxel.text(
                2, SCREEN_H - 10, f"NEXT:{ELEMENT_NAMES[elem]}", ELEMENT_COLORS[elem]
            )

        # game over screen
        if self.phase == Phase.GAMEOVER:
            pyxel.rect(40, 80, 176, 90, C_NAVY)
            pyxel.rectb(40, 80, 176, 90, C_WHITE)
            won = self.targets_cleared >= self.targets_total and self.targets_total > 0
            msg = "CLEAR!" if won else "GAME OVER"
            col = C_YELLOW if won else C_RED
            pyxel.text(SCREEN_W // 2 - 18, 90, msg, col)
            pyxel.text(SCREEN_W // 2 - 30, 108, f"SCORE: {self.score}", C_WHITE)
            pyxel.text(SCREEN_W // 2 - 35, 124, f"BEST: {self.high_score}", C_YELLOW)
            pyxel.text(SCREEN_W // 2 - 45, 150, "CLICK or R to retry", C_GRAY)

        # result popup (brief)
        if self.phase == Phase.RESULT:
            pyxel.text(SCREEN_W // 2 - 15, SCREEN_H // 2 - 4, "DROP END", C_WHITE)

    # ── Effects ───────────────────────────────────────────────────────────

    def _spawn_burst(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(0.5, 2.5)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=random.randint(8, 20),
                    color=color,
                )
            )

    def _spawn_float_text(
        self, x: float, y: float, text: str, life: int, color: int
    ) -> None:
        self.float_texts.append(
            FloatText(x=x - len(text) * 2, y=y, text=text, life=life, color=color)
        )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    Game()
