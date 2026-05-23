"""MOLE CHAIN — Color-match whack-a-mole with COMBO chains.

Reinterpreted from game_idea_factory #1 (Score 31.45):
  "log/replay as asset" → echo ghosts of previous whacks guide next hits
  "one-color-per-turn" → only same-color consecutive whacks build COMBO

Core fun moment: rhythmically whacking same-colored moles as the COMBO
multiplier accelerates x2, x3, x4 — score explodes.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ── Constants ──────────────────────────────────────────────────────────
SCREEN_W = 256
SCREEN_H = 256
DISPLAY_SCALE = 2
GAME_TIME = 60  # seconds
FPS = 30

# Grid
COLS = 4
ROWS = 3
CELL_W = 52
CELL_H = 56
GRID_X = (SCREEN_W - COLS * CELL_W) // 2
GRID_Y = 60
HOLE_R = 18  # hole radius

# Colors (Pyxel palette)
COLOR_IDS: tuple[int, int, int, int] = (
    pyxel.COLOR_RED,     # 0
    pyxel.COLOR_GREEN,   # 1
    pyxel.COLOR_YELLOW,  # 2
    pyxel.COLOR_CYAN,    # 3
)
COLOR_NAMES: tuple[str, str, str, str] = ("RED", "GREEN", "YELLOW", "CYAN")
NUM_COLORS = 4

# Mole animation
RISE_FRAMES = 10
FALL_FRAMES = 8
MIN_VISIBLE_FRAMES = 30  # at start
MAX_VISIBLE_FRAMES = 8   # at end (fast)

# Scoring
BASE_SCORE = 100
SUPER_SCORE = 200
SUPER_COMBO_THRESHOLD = 4

# ── Data Classes ───────────────────────────────────────────────────────


class MoleState(Enum):
    HIDDEN = auto()
    RISING = auto()
    VISIBLE = auto()
    FALLING = auto()
    WHACKED = auto()  # brief hit animation


@dataclass
class Mole:
    col: int
    row: int
    color: int = 0
    state: MoleState = MoleState.HIDDEN
    timer: int = 0       # frames remaining in current state
    anim_frame: int = 0  # 0..RISE_FRAMES or 0..FALL_FRAMES

    @property
    def cx(self) -> int:
        """Center X in pixels."""
        return GRID_X + self.col * CELL_W + CELL_W // 2

    @property
    def cy(self) -> int:
        """Center Y in pixels."""
        return GRID_Y + self.row * CELL_H + CELL_H // 2

    @property
    def hit_radius(self) -> int:
        """Click detection radius."""
        return HOLE_R + 6

    def hit_test(self, mx: int, my: int) -> bool:
        return (mx - self.cx) ** 2 + (my - self.cy) ** 2 <= self.hit_radius ** 2


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
class EchoGhost:
    """Log/replay as asset: ghost trail of previous whacks."""
    x: float
    y: float
    life: int
    color: int


# ── Phase Enum ─────────────────────────────────────────────────────────


class Phase(Enum):
    PLAYING = auto()
    GAME_OVER = auto()


# ── Game Class ─────────────────────────────────────────────────────────


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="MOLE CHAIN", display_scale=DISPLAY_SCALE, fps=FPS)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase: Phase = Phase.PLAYING
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.hits: int = 0
        self.misses: int = 0
        self.frame: int = 0
        self.time_left: float = float(GAME_TIME)
        self.super_mode: bool = False
        self.super_timer: int = 0
        self._active_color: int | None = None  # current combo color
        self._spawn_cooldown: int = 0
        self._max_active: int = 3  # moles visible at once (increases)
        self._difficulty: float = 1.0

        # Grid of moles
        self.moles: list[list[Mole]] = [
            [Mole(col=c, row=r) for r in range(ROWS)] for c in range(COLS)
        ]

        # VFX
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.echoes: list[EchoGhost] = []
        self._shake_frames: int = 0

    # ── Update ─────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
            return

        self.frame += 1

        # Timer
        self.time_left -= 1.0 / FPS
        if self.time_left <= 0:
            self.time_left = 0
            self.phase = Phase.GAME_OVER
            return

        # Difficulty scaling
        elapsed = GAME_TIME - self.time_left
        self._difficulty = 1.0 + elapsed / 15.0  # ramps over 60s
        self._max_active = min(3 + int(elapsed // 15), 8)  # 3→7 max
        # Shorter spawn intervals
        spawn_interval = max(15, int(60 - elapsed * 0.7))

        # SUPER timer
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False

        # Spawn moles
        self._spawn_cooldown -= 1
        if self._spawn_cooldown <= 0:
            self._try_spawn_mole()
            self._spawn_cooldown = spawn_interval

        # Update moles
        for c in range(COLS):
            for r in range(ROWS):
                self._update_mole(self.moles[c][r])

        # Update particles
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.3  # gravity
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

        # Update floating texts
        for ft in self.floating_texts[:]:
            ft.y -= 1.0
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

        # Update echoes
        for e in self.echoes[:]:
            e.life -= 1
            if e.life <= 0:
                self.echoes.remove(e)

        # Screen shake decay
        if self._shake_frames > 0:
            self._shake_frames -= 1

        # Mouse click
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._handle_click(pyxel.mouse_x, pyxel.mouse_y)

    def _try_spawn_mole(self) -> None:
        """Spawn a new mole at a random empty hole."""
        active_count = sum(
            1 for c in range(COLS) for r in range(ROWS)
            if self.moles[c][r].state != MoleState.HIDDEN
        )
        if active_count >= self._max_active:
            return

        # Find empty holes
        empty: list[tuple[int, int]] = [
            (c, r) for c in range(COLS) for r in range(ROWS)
            if self.moles[c][r].state == MoleState.HIDDEN
        ]
        if not empty:
            return

        c, r = self._rng.choice(empty)
        color = self._rng.randrange(NUM_COLORS)
        mole = self.moles[c][r]
        mole.color = color
        mole.state = MoleState.RISING
        mole.timer = RISE_FRAMES
        mole.anim_frame = 0

    def _update_mole(self, mole: Mole) -> None:
        if mole.state == MoleState.HIDDEN:
            return
        mole.timer -= 1
        if mole.state == MoleState.RISING:
            mole.anim_frame = RISE_FRAMES - mole.timer
            if mole.timer <= 0:
                visible_frames = int(
                    MIN_VISIBLE_FRAMES
                    - (MIN_VISIBLE_FRAMES - MAX_VISIBLE_FRAMES)
                    * min((GAME_TIME - self.time_left) / GAME_TIME, 1.0)
                )
                mole.state = MoleState.VISIBLE
                mole.timer = max(visible_frames, MAX_VISIBLE_FRAMES)
        elif mole.state == MoleState.VISIBLE:
            if mole.timer <= 0:
                mole.state = MoleState.FALLING
                mole.timer = FALL_FRAMES
                mole.anim_frame = 0
        elif mole.state == MoleState.FALLING:
            mole.anim_frame = FALL_FRAMES - mole.timer
            if mole.timer <= 0:
                mole.state = MoleState.HIDDEN
        elif mole.state == MoleState.WHACKED:
            if mole.timer <= 0:
                mole.state = MoleState.HIDDEN

    def _handle_click(self, mx: int, my: int) -> None:
        """Process a mouse click on the grid."""
        # Check each visible mole for hit
        hit_mole: Mole | None = None
        for c in range(COLS):
            for r in range(ROWS):
                mole = self.moles[c][r]
                if mole.state in (MoleState.RISING, MoleState.VISIBLE):
                    if mole.hit_test(mx, my):
                        hit_mole = mole
                        break
            if hit_mole:
                break

        if hit_mole is None:
            # Clicked empty space — reset combo
            if self.combo > 0:
                self._break_combo()
            return

        self._whack_mole(hit_mole)

    def _whack_mole(self, mole: Mole) -> None:
        """Whack a mole: handle combo logic and scoring."""
        color = mole.color

        # Check color match
        if self._active_color is not None and color != self._active_color:
            # Wrong color — break combo
            self._break_combo()
            # Still whack it, but no combo
            self._do_whack(mole, combo_mult=1.0)
            return

        # Same color (or first whack) — build combo
        self._active_color = color
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        combo_mult = 1.0 + (self.combo - 1) * 0.5  # 1.0, 1.5, 2.0, 2.5, ...

        self._do_whack(mole, combo_mult=combo_mult)

        # Add echo ghost (log/replay as asset)
        self.echoes.append(EchoGhost(
            x=float(mole.cx), y=float(mole.cy),
            life=30, color=color,
        ))

        # SUPER trigger
        if self.combo >= SUPER_COMBO_THRESHOLD:
            self._trigger_super()

    def _do_whack(self, mole: Mole, combo_mult: float) -> None:
        """Execute the whack: score, particles, animation."""
        mole.state = MoleState.WHACKED
        mole.timer = 12
        self.hits += 1

        base = SUPER_SCORE if self.super_mode else BASE_SCORE
        points = int(base * combo_mult)
        self.score += points

        # Floating text
        txt = f"+{points}"
        txt_color = pyxel.COLOR_YELLOW if combo_mult >= 2.5 else pyxel.COLOR_WHITE
        if self.super_mode:
            txt += "!"
            txt_color = pyxel.COLOR_RED
        self.floating_texts.append(FloatingText(
            x=float(mole.cx), y=float(mole.cy) - 10,
            text=txt, life=25, color=txt_color,
        ))

        # Particles
        for _ in range(6):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.0, 3.0)
            self.particles.append(Particle(
                x=float(mole.cx), y=float(mole.cy),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=15, color=COLOR_IDS[mole.color],
            ))

        # COMBO display
        if self.combo >= 2:
            self.floating_texts.append(FloatingText(
                x=float(mole.cx), y=float(mole.cy) - 22,
                text=f"COMBO x{self.combo}",
                life=30, color=pyxel.COLOR_ORANGE,
            ))

    def _trigger_super(self) -> None:
        """Activate SUPER mode: auto-whack all visible moles for bonus."""
        self.super_mode = True
        self.super_timer = 1  # lasts for this frame only (auto-whack once)

        # Find all visible moles of the active color (or all if combo is high)
        target_color = self._active_color if self._active_color is not None else 0
        targets: list[Mole] = []
        for c in range(COLS):
            for r in range(ROWS):
                mole = self.moles[c][r]
                if mole.state in (MoleState.RISING, MoleState.VISIBLE):
                    if self.combo >= 6 or mole.color == target_color:
                        targets.append(mole)

        # Auto-whack all targets
        for mole in targets:
            self._do_whack(mole, combo_mult=1.0 + (self.combo - 1) * 0.5)

        # Screen shake
        self._shake_frames = 8

        # Particles burst at center
        for _ in range(20):
            angle = self._rng.uniform(0, math.pi * 2)
            speed = self._rng.uniform(1.5, 4.0)
            self.particles.append(Particle(
                x=SCREEN_W / 2, y=SCREEN_H / 2,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=20, color=pyxel.COLOR_YELLOW,
            ))

        # SUPER text
        self.floating_texts.append(FloatingText(
            x=SCREEN_W / 2 - 30, y=SCREEN_H / 2,
            text="SUPER!!",
            life=40, color=pyxel.COLOR_RED,
        ))

    def _break_combo(self) -> None:
        """Break the current combo."""
        if self.combo > 0:
            self.combo = 0
            self._active_color = None
            self.misses += 1

    # ── Draw ───────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)

        # Screen shake offset
        shake_x = 0
        shake_y = 0
        if self._shake_frames > 0:
            shake_x = self._rng.randint(-3, 3)
            shake_y = self._rng.randint(-3, 3)

        # Draw ground
        ground_y = GRID_Y + ROWS * CELL_H
        pyxel.rect(0, ground_y, SCREEN_W, SCREEN_H - ground_y, pyxel.COLOR_BROWN)

        # Draw grid background
        pyxel.rect(GRID_X - 10 + shake_x, GRID_Y - 10 + shake_y,
                    COLS * CELL_W + 20, ROWS * CELL_H + 20, pyxel.COLOR_NAVY)

        # Draw holes
        for c in range(COLS):
            for r in range(ROWS):
                mole = self.moles[c][r]
                cx = mole.cx + shake_x
                cy = mole.cy + shake_y
                # Hole
                pyxel.circ(cx, cy, HOLE_R, pyxel.COLOR_BLACK)
                pyxel.circb(cx, cy, HOLE_R, pyxel.COLOR_GRAY)

        # Draw moles
        mole_draw_order = sorted(
            [(c, r) for c in range(COLS) for r in range(ROWS)],
            key=lambda cr: self.moles[cr[0]][cr[1]].cy,  # sort by y for depth
        )
        for c, r in mole_draw_order:
            self._draw_mole(self.moles[c][r], shake_x, shake_y)

        # Draw echoes (under particles)
        for e in self.echoes:
            alpha = e.life / 30.0
            r = int(6 + 10 * alpha)
            col = e.color if alpha > 0.5 else pyxel.COLOR_GRAY
            pyxel.circb(int(e.x) + shake_x, int(e.y) + shake_y, r, col)

        # Draw particles
        for p in self.particles:
            pyxel.pset(int(p.x) + shake_x, int(p.y) + shake_y, p.color)

        # Draw floating texts
        for ft in self.floating_texts:
            pyxel.text(int(ft.x) + shake_x, int(ft.y) + shake_y, ft.text, ft.color)

        # Draw HUD
        self._draw_hud()

        # Game over screen
        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_mole(self, mole: Mole, shake_x: int, shake_y: int) -> None:
        if mole.state == MoleState.HIDDEN:
            return

        cx = mole.cx + shake_x
        cy = mole.cy + shake_y
        color = COLOR_IDS[mole.color]

        if mole.state == MoleState.RISING:
            # Rising from hole: only top part visible
            progress = mole.anim_frame / RISE_FRAMES  # 0→1
            offset_y = int((1.0 - progress) * 24)
            # Body
            body_y = cy + offset_y - 10
            body_h = min(20, int(progress * 24))
            if body_h > 0:
                pyxel.ellib(cx - 10, body_y, 20, body_h, color)
                # Eyes
                eye_y = body_y + 6
                pyxel.circ(cx - 4, eye_y, 3, pyxel.COLOR_WHITE)
                pyxel.circ(cx + 4, eye_y, 3, pyxel.COLOR_WHITE)
                pyxel.circ(cx - 4, eye_y, 1, pyxel.COLOR_BLACK)
                pyxel.circ(cx + 4, eye_y, 1, pyxel.COLOR_BLACK)
            # Nose
            nose_y = body_y + 10
            if nose_y < cy + HOLE_R:
                pyxel.circ(cx, nose_y, 3, pyxel.COLOR_RED)
        elif mole.state in (MoleState.VISIBLE, MoleState.WHACKED):
            # Fully visible mole
            body_y = cy - 12
            # Body
            pyxel.elli(cx - 12, body_y, 24, 24, color)
            # Eyes
            eye_y = body_y + 8
            if mole.state == MoleState.WHACKED:
                # X eyes
                pyxel.line(cx - 6, eye_y - 3, cx - 2, eye_y + 3, pyxel.COLOR_BLACK)
                pyxel.line(cx - 6, eye_y + 3, cx - 2, eye_y - 3, pyxel.COLOR_BLACK)
                pyxel.line(cx + 2, eye_y - 3, cx + 6, eye_y + 3, pyxel.COLOR_BLACK)
                pyxel.line(cx + 2, eye_y + 3, cx + 6, eye_y - 3, pyxel.COLOR_BLACK)
            else:
                pyxel.circ(cx - 4, eye_y, 3, pyxel.COLOR_WHITE)
                pyxel.circ(cx + 4, eye_y, 3, pyxel.COLOR_WHITE)
                pyxel.circ(cx - 4, eye_y, 1, pyxel.COLOR_BLACK)
                pyxel.circ(cx + 4, eye_y, 1, pyxel.COLOR_BLACK)
            # Nose
            nose_y = body_y + 12
            pyxel.circ(cx, nose_y, 3, pyxel.COLOR_RED)
            # Mouth (open if whacked)
            if mole.state == MoleState.WHACKED:
                pyxel.elli(cx - 5, nose_y + 2, 10, 6, pyxel.COLOR_BLACK)
        elif mole.state == MoleState.FALLING:
            # Falling back into hole
            progress = mole.anim_frame / FALL_FRAMES  # 0→1
            offset_y = int(progress * 24)
            body_y = cy - 12 + offset_y
            body_h = max(2, 24 - offset_y)
            if body_h > 0:
                pyxel.ellib(cx - 12, body_y, 24, body_h, color)
                # Eyes (visible while still above hole)
                if offset_y < 16:
                    eye_y = body_y + 6
                    pyxel.circ(cx - 4, eye_y, 2, pyxel.COLOR_WHITE)
                    pyxel.circ(cx + 4, eye_y, 2, pyxel.COLOR_WHITE)
                    pyxel.circ(cx - 4, eye_y, 1, pyxel.COLOR_BLACK)
                    pyxel.circ(cx + 4, eye_y, 1, pyxel.COLOR_BLACK)

    def _draw_hud(self) -> None:
        """Draw score, timer, combo at top."""
        # Background bar
        pyxel.rect(0, 0, SCREEN_W, 36, pyxel.COLOR_DARK_BLUE)

        # Score
        pyxel.text(6, 4, f"SCORE:{self.score:>7d}", pyxel.COLOR_WHITE)

        # Timer
        secs = int(self.time_left)
        timer_color = pyxel.COLOR_RED if secs <= 10 else pyxel.COLOR_WHITE
        pyxel.text(6, 16, f"TIME: {secs:>2d}s", timer_color)

        # COMBO (right side)
        combo_color = pyxel.COLOR_YELLOW
        if self.combo >= SUPER_COMBO_THRESHOLD:
            combo_color = pyxel.COLOR_RED
        elif self.combo >= 2:
            combo_color = pyxel.COLOR_ORANGE
        pyxel.text(SCREEN_W - 80, 4, f"COMBO: x{self.combo}", combo_color)

        # Hits / Misses
        pyxel.text(SCREEN_W - 80, 16, f"HIT:{self.hits} MIS:{self.misses}", pyxel.COLOR_GRAY)

        # Active color indicator
        if self._active_color is not None:
            ac = COLOR_IDS[self._active_color]
            pyxel.rect(SCREEN_W - 80, 28, 22, 6, ac)
            pyxel.text(SCREEN_W - 56, 28, COLOR_NAMES[self._active_color], ac)

        # SUPER indicator
        if self.super_mode:
            pyxel.text(SCREEN_W // 2 - 20, 16, "SUPER!", pyxel.COLOR_RED)

    def _draw_game_over(self) -> None:
        """Draw game over overlay."""
        # Semi-transparent overlay
        pyxel.rect(0, SCREEN_H // 2 - 50, SCREEN_W, 100, pyxel.COLOR_BLACK)
        pyxel.rectb(0, SCREEN_H // 2 - 50, SCREEN_W, 100, pyxel.COLOR_WHITE)

        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 - 40, "GAME OVER", pyxel.COLOR_RED)
        pyxel.text(
            SCREEN_W // 2 - 50, SCREEN_H // 2 - 20,
            f"SCORE: {self.score}", pyxel.COLOR_WHITE,
        )
        pyxel.text(
            SCREEN_W // 2 - 50, SCREEN_H // 2 - 6,
            f"MAX COMBO: x{self.max_combo}", pyxel.COLOR_YELLOW,
        )
        pyxel.text(
            SCREEN_W // 2 - 50, SCREEN_H // 2 + 8,
            f"HITS: {self.hits}  MISS: {self.misses}", pyxel.COLOR_GRAY,
        )
        pyxel.text(
            SCREEN_W // 2 - 52, SCREEN_H // 2 + 24,
            "CLICK or ENTER to retry", pyxel.COLOR_WHITE,
        )


# ── Entry Point ────────────────────────────────────────────────────────


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
