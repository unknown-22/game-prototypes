from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

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

SUBJECT_COLORS = (RED, LIME, CYAN, YELLOW)

COLS = 8
ROWS = 6
CELL = 32
GRID_X = 32
GRID_Y = 24
GRID_W = COLS * CELL
GRID_H = ROWS * CELL

WIDTH = 320
HEIGHT = 240
FPS = 30
GAME_DURATION = 60 * FPS  # 1800 frames
SUPER_DURATION = 300
FLASH_ANIM_DURATION = 15
HEAT_MAX = 100.0
HEAT_MISMATCH = 15.0
HEAT_DECAY = 0.2  # per frame
COMBO_SUPER_THRESHOLD = 4
SUBJECT_MIN = 4
SUBJECT_MAX = 8

INITIAL_FOG_INTERVAL = 90
FINAL_FOG_INTERVAL = 30
INITIAL_SPAWN_INTERVAL = 120
FINAL_SPAWN_INTERVAL = 60
INITIAL_SUBJECT_LIFE = 300
FINAL_SUBJECT_LIFE = 150

FOG_SPREAD_CHANCE = 0.20


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    FLASH_ANIM = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Subject:
    col: int
    row: int
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


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------


class Game:
    def __init__(self) -> None:
        pyxel.init(WIDTH, HEIGHT, title="FLASH CHAIN", display_scale=2, fps=FPS)
        self.rng = random.Random()

        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.best_score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.timer: int = GAME_DURATION
        self.fog: list[list[bool]] = []
        self.subjects: list[Subject] = []
        self.last_color: int | None = None
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.flash_alpha: int = 0
        self.particles: list[Particle] = []
        self.frame: int = 0
        self.fog_interval: int = INITIAL_FOG_INTERVAL
        self.spawn_interval: int = INITIAL_SPAWN_INTERVAL
        self.spawn_timer: int = 0
        self.fog_timer: int = 0

        self._mouse_just_pressed: bool = False

        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = GAME_DURATION
        self.fog = self._make_initial_fog()
        self.subjects.clear()
        self.last_color = None
        self.super_mode = False
        self.super_timer = 0
        self.flash_alpha = 0
        self.particles.clear()
        self.frame = 0
        self.fog_interval = INITIAL_FOG_INTERVAL
        self.spawn_interval = INITIAL_SPAWN_INTERVAL
        self.spawn_timer = 0
        self.fog_timer = 0

    def _make_initial_fog(self) -> list[list[bool]]:
        return [[False] * COLS for _ in range(ROWS)]

    # ------------------------------------------------------------------
    # Difficulty helpers
    # ------------------------------------------------------------------

    def _elapsed_ratio(self) -> float:
        elapsed = GAME_DURATION - self.timer
        return min(elapsed / GAME_DURATION, 1.0)

    def _get_fog_interval(self) -> int:
        t = self._elapsed_ratio()
        return round(INITIAL_FOG_INTERVAL + (FINAL_FOG_INTERVAL - INITIAL_FOG_INTERVAL) * t)

    def _get_spawn_interval(self) -> int:
        t = self._elapsed_ratio()
        return round(INITIAL_SPAWN_INTERVAL + (FINAL_SPAWN_INTERVAL - INITIAL_SPAWN_INTERVAL) * t)

    def _get_subject_life(self) -> int:
        t = self._elapsed_ratio()
        return round(INITIAL_SUBJECT_LIFE + (FINAL_SUBJECT_LIFE - INITIAL_SUBJECT_LIFE) * t)

    # ------------------------------------------------------------------
    # Fog CA spread
    # ------------------------------------------------------------------

    def _spread_fog(self) -> None:
        new_fogged: list[tuple[int, int]] = []
        dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]

        for r in range(ROWS):
            for c in range(COLS):
                if not self.fog[r][c]:
                    continue
                for dc, dr in dirs:
                    nc, nr = c + dc, r + dr
                    if 0 <= nc < COLS and 0 <= nr < ROWS and not self.fog[nr][nc]:
                        if self.rng.random() < FOG_SPREAD_CHANCE:
                            new_fogged.append((nc, nr))

        for c, r in new_fogged:
            self.fog[r][c] = True

    # ------------------------------------------------------------------
    # Subject management
    # ------------------------------------------------------------------

    def _spawn_subjects(self) -> None:
        current_count = len(self.subjects)
        if current_count >= SUBJECT_MAX:
            return

        unfogged: list[tuple[int, int]] = []
        for r in range(ROWS):
            for c in range(COLS):
                if not self.fog[r][c]:
                    occupied = any(s.col == c and s.row == r for s in self.subjects)
                    if not occupied:
                        unfogged.append((c, r))

        needed = SUBJECT_MIN - current_count
        if needed <= 0 and current_count >= SUBJECT_MIN:
            return

        if current_count < SUBJECT_MIN:
            needed = max(needed, SUBJECT_MIN - current_count)

        spawn_count = min(needed, len(unfogged), SUBJECT_MAX - current_count)
        if spawn_count <= 0:
            return

        chosen = self.rng.sample(unfogged, spawn_count)
        life = self._get_subject_life()
        for c, r in chosen:
            color = self.rng.choice(SUBJECT_COLORS)
            self.subjects.append(Subject(col=c, row=r, color=color, life=life))

    def _update_subjects(self) -> None:
        for s in self.subjects:
            s.life -= 1
        self.subjects = [s for s in self.subjects if s.life > 0]

    # ------------------------------------------------------------------
    # Heat
    # ------------------------------------------------------------------

    def _update_heat(self, amount: float) -> None:
        self.heat = max(0.0, min(HEAT_MAX, self.heat + amount))
        if self.heat >= HEAT_MAX:
            self._game_over()

    # ------------------------------------------------------------------
    # SUPER FLASH
    # ------------------------------------------------------------------

    def _activate_super_flash(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self.flash_alpha = 220
        self.phase = Phase.FLASH_ANIM

        cx = GRID_X + GRID_W / 2
        cy = GRID_Y + GRID_H / 2
        for _ in range(20):
            angle = self.rng.uniform(0, math.pi * 2)
            speed = self.rng.uniform(1.0, 3.0)
            color = self.rng.choice([WHITE] + list(SUBJECT_COLORS))
            self.particles.append(
                Particle(
                    x=cx,
                    y=cy,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=self.rng.randint(25, 40),
                    color=color,
                )
            )

    def _update_super(self) -> None:
        if not self.super_mode:
            return
        self.super_timer -= 1
        if self.super_timer <= 0:
            self.super_mode = False
            self.super_timer = 0

    def _update_flash_anim(self) -> None:
        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - 15)
        if self.flash_alpha == 0 and self.phase == Phase.FLASH_ANIM:
            self.phase = Phase.PLAYING

    # ------------------------------------------------------------------
    # Particles
    # ------------------------------------------------------------------

    def _spawn_photo_particles(self, col: int, row: int, color: int) -> None:
        cx = GRID_X + col * CELL + CELL / 2
        cy = GRID_Y + row * CELL + CELL / 2
        for _ in range(8):
            angle = self.rng.uniform(0, math.pi * 2)
            speed = self.rng.uniform(0.5, 1.5)
            self.particles.append(
                Particle(
                    x=cx,
                    y=cy,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=self.rng.randint(20, 30),
                    color=color,
                )
            )

    def _spawn_mismatch_particles(self, col: int, row: int) -> None:
        cx = GRID_X + col * CELL + CELL / 2
        cy = GRID_Y + row * CELL + CELL / 2
        for _ in range(4):
            angle = self.rng.uniform(0, math.pi * 2)
            speed = self.rng.uniform(0.3, 1.0)
            self.particles.append(
                Particle(
                    x=cx,
                    y=cy,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=self.rng.randint(15, 25),
                    color=GRAY,
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ------------------------------------------------------------------
    # Click handling
    # ------------------------------------------------------------------

    def grid_coord(self, screen_x: int, screen_y: int) -> tuple[int, int] | None:
        if screen_x < GRID_X or screen_y < GRID_Y:
            return None
        gx = screen_x - GRID_X
        gy = screen_y - GRID_Y
        col = gx // CELL
        row = gy // CELL
        if 0 <= col < COLS and 0 <= row < ROWS:
            return (col, row)
        return None

    def _handle_click(self, col: int, row: int) -> None:
        if self.fog[row][col]:
            return

        subject: Subject | None = None
        for s in reversed(self.subjects):
            if s.col == col and s.row == row:
                subject = s
                break

        if subject is None:
            return

        if self.super_mode:
            self._process_match(subject)
        elif self.last_color is None or subject.color == self.last_color:
            self._process_match(subject)
        else:
            self._process_mismatch(subject)

    def _process_match(self, subject: Subject) -> None:
        self.combo += 1
        if self.combo > self.max_combo:
            self.max_combo = self.combo

        multiplier = 3 if self.super_mode else 1
        points = 10 * self.combo * multiplier
        self.score += points

        self.subjects.remove(subject)

        self.last_color = subject.color if not self.super_mode else self.last_color

        self._spawn_photo_particles(subject.col, subject.row, subject.color)

        if not self.super_mode and self.combo >= COMBO_SUPER_THRESHOLD:
            self._activate_super_flash()
        elif self.super_mode:
            self._activate_super_flash()

    def _process_mismatch(self, subject: Subject) -> None:
        self._update_heat(HEAT_MISMATCH)
        self.combo = 0
        self.last_color = None
        self._spawn_mismatch_particles(subject.col, subject.row)

    # ------------------------------------------------------------------
    # Game over
    # ------------------------------------------------------------------

    def _game_over(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self) -> None:
        self._mouse_just_pressed = pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)

        match self.phase:
            case Phase.TITLE:
                self._update_title()
            case Phase.PLAYING:
                self._update_playing()
            case Phase.FLASH_ANIM:
                self._update_playing()
                self._update_flash_anim()
            case Phase.GAME_OVER:
                self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()

    def _update_playing(self) -> None:
        if pyxel.btnp(pyxel.KEY_Q) or pyxel.btnp(pyxel.KEY_ESCAPE):
            pyxel.quit()
            return

        self.frame += 1
        self.timer -= 1
        if self.timer <= 0:
            self._game_over()
            return

        self.heat = max(0.0, self.heat - HEAT_DECAY)
        if self.heat >= HEAT_MAX:
            self._game_over()
            return

        self.fog_interval = self._get_fog_interval()
        self.spawn_interval = self._get_spawn_interval()

        self.fog_timer += 1
        if self.fog_timer >= self.fog_interval:
            self.fog_timer = 0
            self._spread_fog()

        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0
            self._spawn_subjects()

        self._update_subjects()
        self._update_super()
        self._update_particles()

        if self._mouse_just_pressed:
            coord = self.grid_coord(pyxel.mouse_x, pyxel.mouse_y)
            if coord is not None:
                self._handle_click(*coord)

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self) -> None:
        match self.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.PLAYING | Phase.FLASH_ANIM:
                self._draw_game()
                if self.phase == Phase.FLASH_ANIM and self.flash_alpha > 0:
                    self._draw_flash_overlay()
            case Phase.GAME_OVER:
                self._draw_game_over()

    # ------------------------------------------------------------------
    # Title screen
    # ------------------------------------------------------------------

    def _draw_title(self) -> None:
        pyxel.cls(NAVY)
        title = "FLASH CHAIN"
        tw = len(title) * 4
        pyxel.text((WIDTH - tw) // 2, 60, title, WHITE)

        subtitle = "Photograph same-color subjects"
        sw = len(subtitle) * 4
        pyxel.text((WIDTH - sw) // 2, 90, subtitle, LIME)

        lines = [
            "CLICK  to shoot",
            "COMBO>=4 = SUPER FLASH",
            "SUPER FLASH: any-color match x3",
            "",
            "Press SPACE to start",
        ]
        for i, line in enumerate(lines):
            lw = len(line) * 4
            pyxel.text((WIDTH - lw) // 2, 130 + i * 12, line, GRAY)

        if self.best_score > 0:
            best = f"Best: {self.best_score}"
            bw = len(best) * 4
            pyxel.text((WIDTH - bw) // 2, 200, best, YELLOW)

    # ------------------------------------------------------------------
    # Game screen
    # ------------------------------------------------------------------

    def _draw_game(self) -> None:
        pyxel.cls(NAVY)
        self._draw_grid()
        self._draw_subjects()
        self._draw_fog()
        self._draw_particles()
        self._draw_hud()
        self._draw_viewfinder_frame()

    def _draw_grid(self) -> None:
        for r in range(ROWS + 1):
            y = GRID_Y + r * CELL
            pyxel.line(GRID_X, y, GRID_X + GRID_W, y, DARK_BLUE)
        for c in range(COLS + 1):
            x = GRID_X + c * CELL
            pyxel.line(x, GRID_Y, x, GRID_Y + GRID_H, DARK_BLUE)

    def _draw_subjects(self) -> None:
        for s in self.subjects:
            if self.fog[s.row][s.col]:
                continue
            cx = GRID_X + s.col * CELL + CELL // 2
            cy = GRID_Y + s.row * CELL + CELL // 2

            pyxel.circ(cx, cy, 10, s.color)
            pyxel.circ(cx, cy, 7, BLACK)

            r = 3
            pyxel.line(cx - r, cy, cx + r, cy, s.color)
            pyxel.line(cx, cy - r, cx, cy + r, s.color)

            alpha = s.life / INITIAL_SUBJECT_LIFE
            if alpha < 0.5:
                blink = (pyxel.frame_count // 10) % 2 == 0
                if blink:
                    pyxel.circb(cx, cy, 11, YELLOW)

    def _draw_fog(self) -> None:
        for r in range(ROWS):
            for c in range(COLS):
                if self.fog[r][c]:
                    x = GRID_X + c * CELL
                    y = GRID_Y + r * CELL
                    for ry in range(CELL):
                        for rx in range(CELL):
                            if (rx + ry) % 2 == 0:
                                pyxel.pset(x + rx, y + ry, GRAY)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 40
            alpha = max(0.1, alpha)
            col = p.color
            if alpha < 0.4:
                col = GRAY
            pyxel.pset(int(p.x), int(p.y), col)

    def _draw_viewfinder_frame(self) -> None:
        pyxel.rectb(GRID_X - 1, GRID_Y - 1, GRID_W + 2, GRID_H + 2, WHITE)
        pyxel.line(0, 0, 0, HEIGHT, WHITE)
        pyxel.line(WIDTH - 1, 0, WIDTH - 1, HEIGHT, WHITE)

    def _draw_hud(self) -> None:
        score_text = f"SCORE:{self.score}"
        pyxel.text(2, 2, score_text, WHITE)

        elapsed = max(0, self.timer // FPS)
        time_text = f"TIME:{elapsed:02d}"
        pyxel.text(2, 12, time_text, YELLOW if elapsed <= 10 else WHITE)

        combo_color = ORANGE if self.combo >= 3 else YELLOW
        combo_text = f"COMBO:x{self.combo}"
        pyxel.text((WIDTH - len(combo_text) * 4) // 2, 2, combo_text, combo_color)

        bar_x = WIDTH - 108
        bar_y = 2
        bar_w = 100
        bar_h = 6
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        heat_w = int(bar_w * (self.heat / HEAT_MAX))
        heat_col = ORANGE if self.heat > 70 else RED
        if heat_w > 0:
            pyxel.rect(bar_x, bar_y, heat_w, bar_h, heat_col)

        heat_label = "HEAT"
        pyxel.text(bar_x - 24, bar_y - 1, heat_label, RED)

        if self.super_mode:
            super_text = "SUPER FLASH!"
            super_w = len(super_text) * 4
            t = self.super_timer // FPS
            sub_text = f"{t}s"
            sx = (WIDTH - super_w) // 2
            pyxel.text(sx, GRID_Y - 10, super_text, WHITE)
            pyxel.text(sx + super_w + 6, GRID_Y - 10, sub_text, YELLOW)

        max_combo_text = f"MAX:x{self.max_combo}"
        pyxel.text(2, GRID_Y + GRID_H + 4, max_combo_text, CYAN)

    def _draw_flash_overlay(self) -> None:
        alpha = self.flash_alpha / 220
        color = WHITE if alpha > 0.5 else ORANGE
        for y in range(0, HEIGHT, 2):
            for x in range(0, WIDTH, 2):
                if (x // 2 + y // 2) % 2 == 0:
                    pyxel.pset(x, y, color)

    # ------------------------------------------------------------------
    # Game Over screen
    # ------------------------------------------------------------------

    def _draw_game_over(self) -> None:
        pyxel.cls(NAVY)
        go = "GAME OVER"
        gw = len(go) * 4
        pyxel.text((WIDTH - gw) // 2, 60, go, RED)

        score_line = f"Score: {self.score}"
        sw_ = len(score_line) * 4
        pyxel.text((WIDTH - sw_) // 2, 90, score_line, WHITE)

        best_line = f"Best:  {self.best_score}"
        bw = len(best_line) * 4
        color = YELLOW if self.score >= self.best_score and self.score > 0 else WHITE
        pyxel.text((WIDTH - bw) // 2, 105, best_line, color)

        maxc_line = f"Max Combo: x{self.max_combo}"
        mw = len(maxc_line) * 4
        pyxel.text((WIDTH - mw) // 2, 125, maxc_line, CYAN)

        reason: str
        if self.heat >= HEAT_MAX:
            reason = "Overexposed!"
        elif self.timer <= 0:
            reason = "Time's up!"
        else:
            reason = ""
        if reason:
            rw = len(reason) * 4
            pyxel.text((WIDTH - rw) // 2, 145, reason, ORANGE)

        prompt = "Press SPACE to retry"
        pw = len(prompt) * 4
        pyxel.text((WIDTH - pw) // 2, 175, prompt, GRAY)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
