from __future__ import annotations

import math
import random as random_module
from dataclasses import dataclass
from enum import Enum, auto


import pyxel

# ── Enums ──────────────────────────────────────────────


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ── Data Classes ───────────────────────────────────────


@dataclass
class Prize:
    x: float
    y: float
    color: int
    tier: int  # 0=normal, 1=rare
    alive: bool = True
    spawn_timer: int = 0


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


# ── Constants ──────────────────────────────────────────

GRID_COLS: int = 5
GRID_ROWS: int = 4
CELL: int = 48
OFFSET_X: int = 40
OFFSET_Y: int = 60

PRIZE_COLORS: list[int] = [8, 3, 5, 10]  # RED, GREEN, DARK_BLUE, YELLOW
COLOR_NAMES: dict[int, str] = {8: "RED", 3: "GREEN", 5: "DARK_BLUE", 10: "YELLOW"}

RARE_CHANCE: float = 0.2
RESPAWN_DELAY: int = 90
SUPER_DURATION: int = 300
GAME_DURATION: int = 1800  # 60s * 30fps
HEAT_DECAY: float = 0.05
HEAT_GAIN: float = 15.0
HEAT_MAX: float = 100.0
MOVE_SPEED: int = 5
CLAW_SIZE: int = 24
GRAB_ANIM_FRAMES: int = 15

COMBO_MULTIPLIER_TABLE: list[float] = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]

NORMAL_SCORE: int = 10
RARE_SCORE: int = 30


def _color_name(color: int) -> str:
    return COLOR_NAMES.get(color, "UNKNOWN")


def _combo_multiplier(combo: int) -> float:
    if combo <= 0:
        return 1.0
    idx = min(combo - 1, len(COMBO_MULTIPLIER_TABLE) - 1)
    return COMBO_MULTIPLIER_TABLE[idx]


# ── Game ───────────────────────────────────────────────


class Game:
    def __init__(self) -> None:
        self._rng = random_module.Random()
        self._pre_init()
        pyxel.init(320, 240, title="CLAW SURGE", display_scale=2)
        pyxel.run(self._update, self._draw)

    # ── Pre-init (for Game.__new__ bypass in tests) ─

    def _pre_init(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.timer: int = GAME_DURATION
        self.claw_x: float = OFFSET_X + CELL * 2
        self.claw_y: float = OFFSET_Y + CELL * 2
        self.claw_color: int = 8
        self.super_timer: int = 0
        self.ghost_path: list[tuple[float, float]] = []
        self.best_path: list[tuple[float, float]] = []
        self.best_score: int = 0
        self.prizes: list[Prize] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.shake_frames: int = 0
        self._claw_anim: int = 0
        self._grab_target: Prize | None = None
        self._ghost_frame_counter: int = 0

    # ── Reset ──────────────────────────────────────

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = GAME_DURATION
        self.claw_x = OFFSET_X + CELL * 2
        self.claw_y = OFFSET_Y + CELL * 2
        self.claw_color = 8
        self.super_timer = 0
        self.ghost_path = []
        self.prizes = []
        self.particles = []
        self.floating_texts = []
        self.shake_frames = 0
        self._claw_anim = 0
        self._grab_target = None
        self._ghost_frame_counter = 0
        self._spawn_prizes()

    # ── Prize Spawning ─────────────────────────────

    def _spawn_prizes(self) -> None:
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                color = self._rng.choice(PRIZE_COLORS)
                tier = 1 if self._rng.random() < RARE_CHANCE else 0
                x = OFFSET_X + col * CELL + CELL // 2
                y = OFFSET_Y + row * CELL + CELL // 2
                self.prizes.append(Prize(x=x, y=y, color=color, tier=tier, alive=True, spawn_timer=0))

    # ── Claw Movement ─────────────────────────────

    def _move_claw(self, dx: float, dy: float) -> None:
        min_x = OFFSET_X
        max_x = OFFSET_X + GRID_COLS * CELL - CELL // 2
        min_y = OFFSET_Y
        max_y = OFFSET_Y + GRID_ROWS * CELL - CELL // 2
        self.claw_x = max(min_x, min(max_x, self.claw_x + dx))
        self.claw_y = max(min_y, min(max_y, self.claw_y + dy))

    # ── Grab Logic ────────────────────────────────

    def _find_prize_at_claw(self) -> Prize | None:
        closest: Prize | None = None
        closest_dist: float = 20.0
        for p in self.prizes:
            if not p.alive:
                continue
            dist = math.hypot(p.x - self.claw_x, p.y - self.claw_y)
            if dist < closest_dist:
                closest_dist = dist
                closest = p
        return closest

    def _grab_prize(self, prize: Prize) -> int:
        is_super = self.super_timer > 0
        is_match = is_super or (prize.color == self.claw_color)
        self._compute_combo(is_match)
        base = RARE_SCORE if prize.tier == 1 else NORMAL_SCORE
        mult = _combo_multiplier(self.combo)
        super_mult = 3.0 if is_super else 1.0
        points = int(base * mult * super_mult)

        if is_match:
            self.score += points
            self._spawn_grab_particles(prize)
            self._spawn_floating_text(prize.x, prize.y, f"+{points}", 7, 30)
            if self.combo >= 2:
                self._spawn_floating_text(prize.x, prize.y - 10, f"COMBO x{self.combo}", 10, 40)
            if self.combo >= 4 and self.super_timer == 0:
                self._activate_super()
        else:
            self._spawn_mismatch_particles(prize)
            self._spawn_floating_text(prize.x, prize.y, "MISS", 13, 20)

        prize.alive = False
        prize.spawn_timer = RESPAWN_DELAY
        self._claw_anim = GRAB_ANIM_FRAMES
        self._grab_target = prize
        return points

    def _compute_combo(self, is_match: bool) -> None:
        if is_match:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            self.claw_color = PRIZE_COLORS[((self.combo - 1) // 2) % 4]
        else:
            self.combo = 0
            self.heat = min(HEAT_MAX, self.heat + HEAT_GAIN)
            self.claw_color = PRIZE_COLORS[0]

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self._spawn_super_particles()
        self._spawn_floating_text(self.claw_x, self.claw_y - 20, "SUPER!", 10, 60)
        self.shake_frames = 10

    # ── Updates ────────────────────────────────────

    def _update_particles(self) -> None:
        for pt in self.particles:
            pt.x += pt.vx
            pt.y += pt.vy
            pt.vy += 0.1
            pt.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [f for f in self.floating_texts if f.life > 0]

    def _update_prizes(self) -> None:
        for p in self.prizes:
            if not p.alive:
                if p.spawn_timer > 0:
                    p.spawn_timer -= 1
                if p.spawn_timer <= 0:
                    p.alive = True
                    p.color = self._rng.choice(PRIZE_COLORS)
                    p.tier = 1 if self._rng.random() < RARE_CHANCE else 0

    def _update_heat(self) -> None:
        self.heat = max(0.0, self.heat - HEAT_DECAY)
        if self.heat >= HEAT_MAX:
            self._end_game()

    def _update_timer(self) -> None:
        if self.timer > 0:
            self.timer -= 1
        if self.timer <= 0:
            self._end_game()

    def _update_super(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1

    def _update_ghost(self) -> None:
        self._ghost_frame_counter += 1
        if self._ghost_frame_counter % 10 == 0:
            self.ghost_path.append((self.claw_x, self.claw_y))

    # ── Game Over ──────────────────────────────────

    def _end_game(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score
            self.best_path = list(self.ghost_path)

    # ── Particle Spawning ──────────────────────────

    def _spawn_grab_particles(self, prize: Prize) -> None:
        count = self._rng.randint(6, 10)
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=prize.x,
                    y=prize.y,
                    vx=self._rng.uniform(-2, 2),
                    vy=self._rng.uniform(-2, 2),
                    life=self._rng.randint(15, 25),
                    color=prize.color,
                )
            )

    def _spawn_mismatch_particles(self, prize: Prize) -> None:
        count = self._rng.randint(3, 5)
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=prize.x,
                    y=prize.y,
                    vx=self._rng.uniform(-1, 1),
                    vy=self._rng.uniform(-1, 1),
                    life=self._rng.randint(10, 15),
                    color=13,
                )
            )

    def _spawn_super_particles(self) -> None:
        count = self._rng.randint(20, 30)
        for _ in range(count):
            c = self._rng.choice(PRIZE_COLORS)
            self.particles.append(
                Particle(
                    x=self.claw_x,
                    y=self.claw_y,
                    vx=self._rng.uniform(-3, 3),
                    vy=self._rng.uniform(-3, 3),
                    life=self._rng.randint(20, 40),
                    color=c,
                )
            )

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int, life: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=life, color=color))

    # ── Update & Draw ──────────────────────────────

    def _update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.phase = Phase.TITLE

    def _update_playing(self) -> None:
        dx, dy = 0.0, 0.0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx = -MOVE_SPEED
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx = MOVE_SPEED
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy = -MOVE_SPEED
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy = MOVE_SPEED

        if self._claw_anim == 0:
            self._move_claw(dx, dy)

        if self._claw_anim > 0:
            self._claw_anim -= 1

        if self._claw_anim == 0 and (
            pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
        ):
            prize = self._find_prize_at_claw()
            if prize is not None:
                self._grab_prize(prize)

        self._update_super()
        self._update_heat()
        self._update_timer()
        self._update_prizes()
        self._update_particles()
        self._update_floating_texts()
        self._update_ghost()

        if self.shake_frames > 0:
            self.shake_frames -= 1

    def _draw(self) -> None:
        pyxel.cls(0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        pyxel.text(100, 70, "CLAW SURGE", 7)
        pyxel.text(85, 100, "Click or Press SPACE", 13)
        pyxel.text(97, 112, "to Start", 13)
        pyxel.text(80, 140, "Arrow/WASD: Move", 6)
        pyxel.text(90, 152, "SPACE: Grab", 6)
        if self.best_score > 0:
            pyxel.text(105, 175, f"Best: {self.best_score}", 10)

    def _draw_game_over(self) -> None:
        pyxel.text(120, 70, "GAME OVER", 8)
        pyxel.text(95, 100, f"Score: {self.score}", 7)
        pyxel.text(85, 115, f"Best: {self.best_score}", 10)
        pyxel.text(85, 130, f"Max Combo: {self.max_combo}", 9)
        pyxel.text(78, 160, "Press SPACE to Retry", 13)

    def _draw_playing(self) -> None:
        if self.shake_frames > 0:
            sx = self._rng.randint(-3, 3)
            sy = self._rng.randint(-3, 3)
            pyxel.camera(sx, sy)
        else:
            pyxel.camera(0, 0)

        self._draw_ghost_trail()
        self._draw_prizes()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_claw()
        self._draw_hud()

    def _draw_ghost_trail(self) -> None:
        for gx, gy in self.best_path:
            pyxel.circ(gx, gy, 2, 5)

    def _draw_prizes(self) -> None:
        for p in self.prizes:
            if not p.alive:
                continue
            px = int(p.x - 16)
            py_ = int(p.y - 16)
            if p.tier == 1:
                blink = (pyxel.frame_count // 15) % 2
                if blink:
                    pyxel.rectb(px - 2, py_ - 2, 36, 36, 7)
                pyxel.rect(px, py_, 32, 32, p.color)
                pyxel.rectb(px, py_, 32, 32, 7)
            else:
                pyxel.rect(px, py_, 32, 32, p.color)
                pyxel.rectb(px, py_, 32, 32, 0)

    def _draw_particles(self) -> None:
        for pt in self.particles:
            alpha = pt.life / 25
            if alpha > 0.3:
                pyxel.pset(int(pt.x), int(pt.y), pt.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life
            if alpha > 5:
                pyxel.text(int(ft.x - len(ft.text) * 2), int(ft.y), ft.text, ft.color)

    def _draw_claw(self) -> None:
        cx = int(self.claw_x)
        cy = int(self.claw_y)
        half = CLAW_SIZE // 2
        side = CLAW_SIZE // 4

        color = self.claw_color
        if self.super_timer > 0:
            rainbow_idx = (pyxel.frame_count // 4) % 4
            color = PRIZE_COLORS[rainbow_idx]

        anim_scale = 1.0
        if self._claw_anim > 0:
            progress = self._claw_anim / GRAB_ANIM_FRAMES
            anim_scale = 1.0 - 0.3 * (1.0 - abs(progress - 0.5) * 2.0)

        if self.super_timer > 0:
            pyxel.rectb(cx - half - 2, cy - half - 2, CLAW_SIZE + 4, CLAW_SIZE + 4, 7)

        pyxel.rectb(cx - half, cy - half, CLAW_SIZE, CLAW_SIZE, color)
        pyxel.line(cx - half - 4, cy, cx - half, cy, color)
        pyxel.line(cx + half, cy, cx + half + 4, cy, color)
        pyxel.line(cx, cy - half - 4, cx, cy - half, color)
        pyxel.line(cx, cy + half, cx, cy + half + 4, color)

        pyxel.circ(cx - side * anim_scale, cy - side * anim_scale, 2, color)
        pyxel.circ(cx + side * anim_scale, cy - side * anim_scale, 2, color)
        pyxel.circ(cx - side * anim_scale, cy + side * anim_scale, 2, color)
        pyxel.circ(cx + side * anim_scale, cy + side * anim_scale, 2, color)

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE: {self.score}", 7)
        pyxel.text(132, 4, f"COMBO: {self.combo}", 10 if self.combo < 4 else 8)
        if self.super_timer > 0:
            pyxel.text(260, 4, f"SUPER:{self.super_timer // 30}", 8)

        seconds = max(0, self.timer // 30)
        timer_color = 8 if seconds <= 10 else 7
        pyxel.text(136, 228, f"TIME: {seconds}", timer_color)

        bar_y = 4
        pyxel.rectb(60, bar_y, 204, 10, 7)
        bar_width = int(self.heat / HEAT_MAX * 202)
        heat_color = 3
        if self.heat > 30:
            heat_color = 10
        if self.heat > 60:
            heat_color = 9
        if self.heat > 80:
            heat_color = 8
        pyxel.rect(61, bar_y + 1, bar_width, 8, heat_color)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
