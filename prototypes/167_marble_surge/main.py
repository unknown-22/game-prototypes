"""Marble Surge - Plinko meets color-matching marble drop game."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

SCREEN_W = 320
SCREEN_H = 240

PEG_FIELD_LEFT = 40
PEG_FIELD_RIGHT = 280
PEG_FIELD_TOP = 60
PEG_FIELD_BOTTOM = 220
PEG_COLS = 8
PEG_ROWS = 5
PEG_RADIUS = 4
MARBLE_RADIUS = 5

GRAVITY = 0.15
MAX_FALL_SPEED = 4.0
BOUNCE_RESTITUTION = 0.6
BOUNCE_JITTER = 0.3

MAX_ROUNDS = 10
SUPER_DURATION = 300
ROUND_END_DELAY = 60
HEAT_PER_MISS = 15.0
HEAT_MAX = 100.0
BASE_SCORE_PER_HIT = 10

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

PEG_COLORS = [RED, GREEN, LIGHT_BLUE, YELLOW]
SUPER_RAINBOW_COLORS = [RED, GREEN, LIGHT_BLUE, YELLOW]
COLOR_NAMES = {RED: "RED", GREEN: "GREEN", LIGHT_BLUE: "BLUE", YELLOW: "YEL"}

COMBO_COLORS = [WHITE, CYAN, LIME, YELLOW, RED]
HEAT_BAR_X = 230
HEAT_BAR_Y = 4
HEAT_BAR_W = 80
HEAT_BAR_H = 6


class Phase(Enum):
    TITLE = auto()
    AIMING = auto()
    FALLING = auto()
    ROUND_END = auto()
    GAME_OVER = auto()


@dataclass
class Peg:
    x: float
    y: float
    color: int
    hit: bool = False
    glow_timer: int = 0


@dataclass
class Marble:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    active: bool = True


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    max_life: int
    color: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    life: int
    max_life: int
    color: int


class Game:
    def __init__(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.round_num: int = 0
        self.max_rounds: int = MAX_ROUNDS
        self.super_timer: int = 0
        self.drop_x: float = float(SCREEN_W // 2)
        self.marble: Marble | None = None
        self.pegs: list[Peg] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.best_score: int = 0
        self.ghost_path: list[tuple[float, float]] = []
        self.shake_frames: int = 0
        self._rng: random.Random = random.Random()
        self.round_end_timer: int = 0
        self.best_round_score: int = 0
        self.round_score_start: int = 0
        self._current_path: list[tuple[float, float]] = []
        self._path_sample_counter: int = 0
        self.reset()

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.round_num = 0
        self.super_timer = 0
        self.drop_x = float(SCREEN_W // 2)
        self.marble = None
        self.pegs.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.shake_frames = 0
        self.round_end_timer = 0
        self.best_score = 0
        self.best_round_score = 0
        self.round_score_start = 0
        self.ghost_path.clear()
        self._current_path.clear()
        self._path_sample_counter = 0
        self._spawn_pegs()

    def start_game(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.round_num = 1
        self.super_timer = 0
        self.drop_x = float(SCREEN_W // 2)
        self.marble = None
        self.particles.clear()
        self.floating_texts.clear()
        self.shake_frames = 0
        self.round_end_timer = 0
        self.best_round_score = 0
        self.round_score_start = 0
        self._current_path.clear()
        self._path_sample_counter = 0
        self._spawn_pegs()
        self.phase = Phase.AIMING

    def _spawn_pegs(self) -> None:
        self.pegs.clear()
        x_spacing = (PEG_FIELD_RIGHT - PEG_FIELD_LEFT) / (PEG_COLS - 1)
        y_spacing = (PEG_FIELD_BOTTOM - PEG_FIELD_TOP) / (PEG_ROWS - 1)
        for row in range(PEG_ROWS):
            if row % 2 == 0:
                cols = PEG_COLS
                x_offset = float(PEG_FIELD_LEFT)
            else:
                cols = PEG_COLS - 1
                x_offset = PEG_FIELD_LEFT + x_spacing / 2.0
            for col in range(cols):
                x = x_offset + col * x_spacing
                y = float(PEG_FIELD_TOP + row * y_spacing)
                color = self._rng.choice(PEG_COLORS)
                self.pegs.append(Peg(x=x, y=y, color=color))

    def _drop_marble(self, x: float) -> None:
        color = self._rng.choice(PEG_COLORS)
        self.marble = Marble(
            x=x,
            y=10.0,
            vx=0.0,
            vy=0.0,
            color=color,
            active=True,
        )
        self.combo = 0
        self._current_path.clear()
        self._path_sample_counter = 0
        self.round_score_start = self.score

    def _update_falling(self) -> None:
        if self.marble is None:
            return
        m = self.marble

        if self.super_timer > 0:
            self.super_timer -= 1

        m.vy += GRAVITY
        if m.vy > MAX_FALL_SPEED:
            m.vy = MAX_FALL_SPEED
        if m.vy < -MAX_FALL_SPEED:
            m.vy = -MAX_FALL_SPEED

        m.x += m.vx
        m.y += m.vy

        if m.x < MARBLE_RADIUS:
            m.x = float(MARBLE_RADIUS)
            m.vx = abs(m.vx) * BOUNCE_RESTITUTION
        elif m.x > SCREEN_W - MARBLE_RADIUS:
            m.x = float(SCREEN_W - MARBLE_RADIUS)
            m.vx = -abs(m.vx) * BOUNCE_RESTITUTION

        self._path_sample_counter += 1
        if self._path_sample_counter >= 3:
            self._path_sample_counter = 0
            self._current_path.append((m.x, m.y))

        collisions: list[Peg] = []
        for peg in self.pegs:
            if peg.hit:
                continue
            if self._check_peg_collision(m, peg):
                collisions.append(peg)

        if collisions:
            for i, peg in enumerate(collisions):
                self._resolve_collision_physics(m, peg)
                peg.hit = True
                peg.glow_timer = 10
                is_super = self.super_timer > 0

                if i == 0:
                    self._resolve_peg_hit(peg, m, is_super)

            self._spawn_hit_particles(collisions[0].x, collisions[0].y, collisions[0].color, self.super_timer > 0)

        if m.y > SCREEN_H + MARBLE_RADIUS:
            self._advance_round()

    @staticmethod
    def _check_peg_collision(marble: Marble, peg: Peg) -> bool:
        dx = marble.x - peg.x
        dy = marble.y - peg.y
        dist_sq = dx * dx + dy * dy
        threshold = MARBLE_RADIUS + PEG_RADIUS
        return dist_sq < threshold * threshold

    @staticmethod
    def _resolve_collision_physics(marble: Marble, peg: Peg) -> None:
        dx = marble.x - peg.x
        dy = marble.y - peg.y
        dist = math.hypot(dx, dy)
        if dist < 0.001:
            overlap = float(MARBLE_RADIUS + PEG_RADIUS)
            nx = 0.0
            ny = 1.0
        else:
            overlap = (MARBLE_RADIUS + PEG_RADIUS) - dist
            nx = dx / dist
            ny = dy / dist

        if overlap > 0:
            marble.x += nx * overlap
            marble.y += ny * overlap

        vn = marble.vx * nx + marble.vy * ny
        if vn < 0:
            marble.vx -= (1.0 + BOUNCE_RESTITUTION) * vn * nx
            marble.vy -= (1.0 + BOUNCE_RESTITUTION) * vn * ny

        jitter_x = (random.random() - 0.5) * BOUNCE_JITTER * 2
        jitter_y = (random.random() - 0.5) * BOUNCE_JITTER * 2
        marble.vx += jitter_x
        marble.vy += jitter_y

    def _resolve_peg_hit(self, peg: Peg, marble: Marble, is_super: bool) -> None:
        if is_super:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            points = self._get_score_for_hit()
            self.score += points
            text = f"+{points}"
            text_color = YELLOW
            if self.combo >= 4:
                text = f"+{points} x3!"
            self._spawn_floating_text(peg.x, peg.y, text, text_color)
            return

        if marble.color == peg.color:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            points = self._get_score_for_hit()
            self.score += points
            text = f"+{points}"
            text_color = COMBO_COLORS[min(self.combo, len(COMBO_COLORS) - 1)]
            if self.combo >= 4:
                self._activate_super()
                self._spawn_floating_text(peg.x, peg.y, "SUPER!", YELLOW)
                self.shake_frames = 15
            else:
                self._spawn_floating_text(peg.x, peg.y, text, text_color)
        else:
            self.combo = 0
            self.heat += HEAT_PER_MISS
            if self.heat > HEAT_MAX:
                self.heat = HEAT_MAX
            self._spawn_floating_text(peg.x, peg.y, "MISS", ORANGE)
            if self.heat >= HEAT_MAX:
                self._advance_round()

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION

    def _get_combo_multiplier(self) -> float:
        return 1.0 + self.combo * 0.5

    def _get_score_for_hit(self) -> int:
        base = BASE_SCORE_PER_HIT * self._get_combo_multiplier()
        if self.super_timer > 0:
            base *= 3.0
        return max(1, int(base))

    def _advance_round(self) -> None:
        round_score = self.score - self.round_score_start
        if round_score > self.best_round_score:
            self.best_round_score = round_score
            self.ghost_path = list(self._current_path)

        self.marble = None
        self.super_timer = 0

        if self.heat >= HEAT_MAX:
            self._end_game()
            return

        self.round_num += 1
        if self.round_num > self.max_rounds:
            self._end_game()
            return

        self.combo = 0
        for peg in self.pegs:
            peg.hit = False
            peg.glow_timer = 0
        self._spawn_pegs()
        self.drop_x = float(SCREEN_W // 2)
        self.phase = Phase.ROUND_END
        self.round_end_timer = ROUND_END_DELAY

    def _end_game(self) -> None:
        if self.score > self.best_score:
            self.best_score = self.score
        self.phase = Phase.GAME_OVER

    def _update_round_end(self) -> None:
        self.round_end_timer -= 1
        self._update_particles()
        self._update_floating_texts()
        if self.round_end_timer <= 0:
            self.phase = Phase.AIMING

    def _update_particles(self) -> None:
        surviving: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                surviving.append(p)
        self.particles = surviving

    def _update_floating_texts(self) -> None:
        surviving: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life > 0:
                surviving.append(ft)
        self.particles = self.particles  # dummy to avoid unused var warning
        self.floating_texts = surviving

    def _spawn_hit_particles(self, x: float, y: float, color: int, is_super: bool) -> None:
        count = self._rng.randint(20, 30) if is_super else self._rng.randint(8, 12)
        max_life_range = (20, 40) if is_super else (15, 30)
        for _ in range(count):
            angle = self._rng.uniform(0, math.tau)
            speed = self._rng.uniform(0.5, 2.0)
            life = self._rng.randint(*max_life_range)
            p_color = color
            if self._rng.random() < 0.3:
                p_color = self._rng.choice(PEG_COLORS)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=life,
                    max_life=life,
                    color=p_color,
                )
            )

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=20, max_life=20, color=color)
        )

    def update(self) -> None:
        if self.shake_frames > 0:
            self.shake_frames -= 1

        if self.phase == Phase.FALLING:
            self._update_falling()
            self._update_particles()
            self._update_floating_texts()
        elif self.phase == Phase.ROUND_END:
            self._update_round_end()
        elif self.phase == Phase.GAME_OVER:
            self._update_particles()
            self._update_floating_texts()
            self.shake_frames = 0

        for peg in self.pegs:
            if peg.glow_timer > 0:
                peg.glow_timer -= 1


class App:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Marble Surge", display_scale=2)
        self.game = Game()
        pyxel.mouse(True)
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        g = self.game

        if g.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                g.start_game()

        elif g.phase == Phase.AIMING:
            g.drop_x = float(
                max(PEG_FIELD_LEFT - MARBLE_RADIUS, min(PEG_FIELD_RIGHT + MARBLE_RADIUS, pyxel.mouse_x))
            )
            g.update()
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                g._drop_marble(g.drop_x)
                g.phase = Phase.FALLING

        elif g.phase == Phase.FALLING:
            g.update()

        elif g.phase == Phase.ROUND_END:
            if pyxel.btnp(pyxel.KEY_SPACE):
                g.round_end_timer = 0
                g.phase = Phase.AIMING
            g.update()

        elif g.phase == Phase.GAME_OVER:
            g.update()
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                g.best_score = max(g.best_score, g.score)
                prev_best = g.best_score
                prev_ghost = list(g.ghost_path)
                g.reset()
                g.best_score = prev_best
                g.ghost_path = prev_ghost

    def draw(self) -> None:
        g = self.game
        pyxel.cls(BLACK)

        if g.shake_frames > 0:
            sx = (random.random() - 0.5) * 4
            sy = (random.random() - 0.5) * 4
            pyxel.camera(int(sx), int(sy))
        else:
            pyxel.camera()

        self._draw_background()
        self._draw_pegs()
        self._draw_ghost_path()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

        if g.phase == Phase.TITLE:
            self._draw_title()
        elif g.phase == Phase.AIMING:
            self._draw_aiming_preview()
        elif g.phase == Phase.FALLING:
            self._draw_marble()
        elif g.phase == Phase.ROUND_END:
            self._draw_round_end()
        elif g.phase == Phase.GAME_OVER:
            self._draw_game_over()

        pyxel.camera()

    def _draw_background(self) -> None:
        for x in range(PEG_FIELD_LEFT, PEG_FIELD_RIGHT + 1, 20):
            for y in range(0, SCREEN_H, 20):
                pyxel.pset(x, y, NAVY)

    def _draw_pegs(self) -> None:
        g = self.game
        for peg in g.pegs:
            if peg.hit:
                c = GRAY
            elif peg.glow_timer > 0:
                c = WHITE if peg.glow_timer % 4 < 2 else peg.color
            else:
                c = peg.color
            pyxel.circ(int(peg.x), int(peg.y), PEG_RADIUS, c)
            pyxel.circb(int(peg.x), int(peg.y), PEG_RADIUS, DARK_BLUE)

    def _draw_ghost_path(self) -> None:
        if not self.game.ghost_path:
            return
        for i, (px, py) in enumerate(self.game.ghost_path):
            alpha = 1.0 - (i / len(self.game.ghost_path)) * 0.7
            if int(alpha * 10) % 3 == 0:
                pyxel.circ(int(px), int(py), 2, DARK_BLUE)

    def _draw_marble(self) -> None:
        g = self.game
        if g.marble is None:
            return
        m = g.marble

        if g.super_timer > 0:
            color_idx = (pyxel.frame_count // 4) % len(SUPER_RAINBOW_COLORS)
            marble_color = SUPER_RAINBOW_COLORS[color_idx]
            rim_color = WHITE
        else:
            marble_color = m.color
            rim_color = WHITE

        if g.super_timer > 0 and g.super_timer < 60 and g.super_timer % 8 < 4:
            marble_color = m.color

        pyxel.circ(int(m.x), int(m.y), MARBLE_RADIUS, marble_color)
        pyxel.circb(int(m.x), int(m.y), MARBLE_RADIUS, rim_color)

        if g.super_timer > 0:
            for i in range(3):
                offset = pyxel.frame_count + i * 20
                tx = m.x + math.cos(offset * 0.1) * 6
                ty = m.y - i * 5 - (offset % 20) * 0.3
                tc = SUPER_RAINBOW_COLORS[(pyxel.frame_count // 4 + i) % len(SUPER_RAINBOW_COLORS)]
                pyxel.circ(int(tx), int(ty), 2, tc)

    def _draw_particles(self) -> None:
        for p in self.game.particles:
            alpha_frac = p.life / p.max_life
            if alpha_frac < 0.1:
                continue
            size = 1 if alpha_frac < 0.4 else 2
            c = p.color if alpha_frac > 0.5 else GRAY
            pyxel.pset(int(p.x), int(p.y), c)
            if size == 2:
                pyxel.pset(int(p.x) + 1, int(p.y), c)
                pyxel.pset(int(p.x), int(p.y) + 1, c)
                pyxel.pset(int(p.x) + 1, int(p.y) + 1, c)

    def _draw_floating_texts(self) -> None:
        for ft in self.game.floating_texts:
            alpha_frac = ft.life / ft.max_life
            if alpha_frac < 0.1:
                continue
            c = ft.color if alpha_frac > 0.3 else GRAY
            tx = int(ft.x - len(ft.text) * 2)
            ty = int(ft.y)
            pyxel.text(tx, ty, ft.text, c)

    def _draw_hud(self) -> None:
        g = self.game
        pyxel.rect(0, 0, SCREEN_W, 20, BLACK)

        score_text = f"SCORE: {g.score}"
        pyxel.text(4, 4, score_text, WHITE)

        round_text = f"R {g.round_num}/{g.max_rounds}"
        pyxel.text(SCREEN_W // 2 - len(round_text) * 2, 4, round_text, WHITE)

        combo_text = f"COMBO: x{g.combo}"
        combo_color = COMBO_COLORS[min(g.combo, len(COMBO_COLORS) - 1)] if g.combo > 0 else GRAY
        pyxel.text(SCREEN_W // 2 + 40, 4, combo_text, combo_color)

        if g.super_timer > 0:
            super_sec = g.super_timer / 60.0
            super_text = f"SUPER {super_sec:.1f}s"
            pyxel.text(4, 14, super_text, YELLOW)

        heat_ratio = g.heat / HEAT_MAX
        heat_color = GREEN if heat_ratio < 0.4 else (YELLOW if heat_ratio < 0.7 else RED)
        pyxel.rect(HEAT_BAR_X, HEAT_BAR_Y, HEAT_BAR_W, HEAT_BAR_H, DARK_BLUE)
        pyxel.rect(HEAT_BAR_X, HEAT_BAR_Y, int(HEAT_BAR_W * heat_ratio), HEAT_BAR_H, heat_color)
        pyxel.rectb(HEAT_BAR_X, HEAT_BAR_Y, HEAT_BAR_W, HEAT_BAR_H, WHITE)
        pyxel.text(HEAT_BAR_X - 36, HEAT_BAR_Y, "HEAT", RED if heat_ratio > 0.6 else WHITE)

        if g.phase == Phase.AIMING:
            pyxel.text(4, SCREEN_H - 10, "Aim with mouse, Click to drop", GRAY)

    def _draw_title(self) -> None:
        title = "MARBLE SURGE"
        tx = SCREEN_W // 2 - len(title) * 2
        ty = SCREEN_H // 2 - 30
        pyxel.text(tx, ty, title, WHITE)

        sub = "Click or Press SPACE to Start"
        sx = SCREEN_W // 2 - len(sub) * 2
        pyxel.text(sx, ty + 20, sub, GRAY)

        hint = "Aim & drop marbles. Match colors to combo!"
        hx = SCREEN_W // 2 - len(hint) * 2
        pyxel.text(hx, ty + 32, hint, GRAY)

        hint2 = "COMBO x4 = SUPER MARBLE (3x score!)"
        hx2 = SCREEN_W // 2 - len(hint2) * 2
        pyxel.text(hx2, ty + 42, hint2, YELLOW)

    def _draw_aiming_preview(self) -> None:
        g = self.game
        x = int(g.drop_x)
        pyxel.circb(x, 10, MARBLE_RADIUS, WHITE)
        for dy in range(12, SCREEN_H, 6):
            pyxel.pset(x, dy, GRAY)

    def _draw_round_end(self) -> None:
        g = self.game
        round_score = g.score - g.round_score_start
        msg = f"Round {g.round_num - 1} Done! +{round_score} pts"
        mx = SCREEN_W // 2 - len(msg) * 2
        pyxel.rect(0, SCREEN_H // 2 - 10, SCREEN_W, 20, BLACK)
        pyxel.text(mx, SCREEN_H // 2 - 4, msg, WHITE)

        if g.round_num > g.max_rounds:
            pyxel.text(mx, SCREEN_H // 2 + 10, "Last round complete!", YELLOW)

    def _draw_game_over(self) -> None:
        g = self.game
        pyxel.rect(0, SCREEN_H // 2 - 30, SCREEN_W, 60, BLACK)

        go_text = "GAME OVER"
        go_x = SCREEN_W // 2 - len(go_text) * 2
        pyxel.text(go_x, SCREEN_H // 2 - 20, go_text, RED)

        score_text = f"Score: {g.score}  Best: {g.best_score}"
        sx = SCREEN_W // 2 - len(score_text) * 2
        pyxel.text(sx, SCREEN_H // 2 - 6, score_text, WHITE)

        retry_text = "Press SPACE to Retry"
        rx = SCREEN_W // 2 - len(retry_text) * 2
        pyxel.text(rx, SCREEN_H // 2 + 10, retry_text, GRAY)


def main() -> None:
    App()


if __name__ == "__main__":
    main()
