"""WRECK CHAIN -- Wrecking ball demolition COMBO chain game.

一番面白い瞬間: 振り子のタイミングを完璧に合わせて同色のビルを連続破壊し、
COMBOを繋いでSUPER WRECKを発動させ、一気にスコアを爆発させる瞬間
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import pyxel

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCREEN_W = 320
SCREEN_H = 240
FPS = 60
GAME_DURATION = 3600
FONT_PATH = Path(__file__).with_name("k8x12.bdf")
FONT_W = 8
FONT_H = 12

PIVOT_X = SCREEN_W // 2
PIVOT_Y = 20
ROPE_LENGTH = 80
BALL_RADIUS = 8

BUILDING_W = 40
BUILDING_H_MIN = 30
BUILDING_H_MAX = 70
BUILDING_Y = SCREEN_H - 10  # ground floor, buildings extend upward
BUILDING_GAP = 10
SLOT_COUNT = 5

COLOR_RED = 8
COLOR_LIME = 11
COLOR_DARK_BLUE = 5
COLOR_YELLOW = 10
COLORS = (COLOR_RED, COLOR_LIME, COLOR_DARK_BLUE, COLOR_YELLOW)

HEAT_MISMATCH = 15.0
HEAT_MISS = 5.0
HEAT_DECAY = 0.02
HEAT_MAX = 100.0

COMBO_SUPER_THRESHOLD = 4
SUPER_DURATION = 300

INITIAL_SPAWN_INTERVAL = 90
FINAL_SPAWN_INTERVAL = 30
INITIAL_COLOR_CYCLE = 45
FINAL_COLOR_CYCLE = 25
SPAWN_ANIM_FRAMES = 20

IMPACT_FRAMES = 8
RETRACT_FRAMES = 30

GRAVITY = 0.3
PENDULUM_ACCEL = 0.0035
PENDULUM_DAMPING = 0.999
TENSION_RATE = 0.0016
MAX_ANGULAR_VELOCITY = 0.08
MAX_SWING_ANGLE = math.pi / 2.2

PARTICLE_COUNT = 10
PARTICLE_LIFE = 25
PARTICLE_SPEED = 4.0
FLOAT_TEXT_LIFE = 60
FLOAT_TEXT_SPEED = 1.0

BASE_SCORE = 100


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class PlayPhase(Enum):
    SWINGING = auto()
    FLYING = auto()
    IMPACT = auto()
    RETRACT = auto()


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------
@dataclass
class Building:
    x: int  # left edge
    h: int  # height from ground up
    color: int
    spawn_anim: int = 0  # remaining frames for spawn rise animation

    @property
    def y(self) -> int:
        return BUILDING_Y - self.h

    @property
    def w(self) -> int:
        return BUILDING_W


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    """Pure game logic — no pyxel calls for testable methods."""

    def __init__(self) -> None:
        self.rng = random.Random()
        self.font: Path | None = None
        self._init_state()

    def _init_state(self) -> None:
        self.phase = Phase.TITLE
        self.play_phase = PlayPhase.SWINGING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_timer = 0
        self.timer = GAME_DURATION
        self.best_score = 0
        self.buildings: list[Building] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []

        # Pendulum
        self.angle = 0.0
        self.angular_velocity = 0.01
        self.holding = False

        # Ball
        self.ball_color_idx = 0
        self.ball_color = COLORS[0]
        self.ball_x: float = PIVOT_X
        self.ball_y: float = PIVOT_Y + ROPE_LENGTH
        self.ball_vx: float = 0.0
        self.ball_vy: float = 0.0

        # Timers
        self.spawn_timer = 0
        self.color_timer = 0
        self.impact_timer = 0
        self.retract_timer = 0
        self.spawn_interval = INITIAL_SPAWN_INTERVAL
        self.color_cycle_speed = INITIAL_COLOR_CYCLE

        # Effects
        self.shake_frames = 0
        self.rainbow_tick = 0

    def reset(self) -> None:
        best = self.best_score
        self._init_state()
        self.rng = random.Random()
        self.best_score = best
        self.phase = Phase.PLAYING
        self.play_phase = PlayPhase.SWINGING
        self._populate_buildings(3)
        self.spawn_timer = self.spawn_interval

    # ── Helpers ──────────────────────────────────────────────────────────
    @property
    def is_super(self) -> bool:
        return self.super_timer > 0

    def _progress(self) -> float:
        elapsed = GAME_DURATION - self.timer
        return min(elapsed / GAME_DURATION, 1.0)

    def _lerp(self, a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    def _slot_x(self, idx: int) -> int:
        total_w = SLOT_COUNT * BUILDING_W + (SLOT_COUNT - 1) * BUILDING_GAP
        start_x = (SCREEN_W - total_w) // 2
        return start_x + idx * (BUILDING_W + BUILDING_GAP)

    def _empty_slots(self) -> list[int]:
        occupied_x = {b.x for b in self.buildings if b.spawn_anim <= 0}
        return [self._slot_x(i) for i in range(SLOT_COUNT) if self._slot_x(i) not in occupied_x]

    def _populate_buildings(self, count: int) -> None:
        slots = self._empty_slots()
        self.rng.shuffle(slots)
        for x in slots[:count]:
            h = self.rng.randint(BUILDING_H_MIN, BUILDING_H_MAX)
            color = self.rng.choice(COLORS)
            self.buildings.append(
                Building(x=x, h=h, color=color, spawn_anim=SPAWN_ANIM_FRAMES)
            )

    # ── Building Spawning ────────────────────────────────────────────────
    def _spawn_building(self) -> None:
        slots = self._empty_slots()
        if not slots:
            return
        x = self.rng.choice(slots)
        h = self.rng.randint(BUILDING_H_MIN, BUILDING_H_MAX)
        color = self.rng.choice(COLORS)
        self.buildings.append(
            Building(x=x, h=h, color=color, spawn_anim=SPAWN_ANIM_FRAMES)
        )

    def _update_building_anims(self) -> None:
        for b in self.buildings:
            if b.spawn_anim > 0:
                b.spawn_anim -= 1

    # ── Pendulum & Ball Physics ──────────────────────────────────────────
    def _update_pendulum(self, holding: bool) -> None:
        angular_accel = -PENDULUM_ACCEL * math.sin(self.angle)
        self.angular_velocity += angular_accel
        self.angular_velocity *= PENDULUM_DAMPING

        if holding:
            direction = 1.0 if self.angular_velocity >= 0 else -1.0
            self.angular_velocity += TENSION_RATE * direction

        self.angular_velocity = max(-MAX_ANGULAR_VELOCITY, min(MAX_ANGULAR_VELOCITY, self.angular_velocity))

        if abs(self.angle) > MAX_SWING_ANGLE:
            self.angle = math.copysign(MAX_SWING_ANGLE, self.angle)
            self.angular_velocity *= -0.5

        self.angle += self.angular_velocity

        self.ball_x = PIVOT_X + ROPE_LENGTH * math.sin(self.angle)
        self.ball_y = PIVOT_Y + ROPE_LENGTH * math.cos(self.angle)

    def _launch_ball(self) -> None:
        self.ball_vx = self.angular_velocity * ROPE_LENGTH * math.cos(self.angle)
        self.ball_vy = -self.angular_velocity * ROPE_LENGTH * math.sin(self.angle)
        self.play_phase = PlayPhase.FLYING

    def _update_flying(self) -> None:
        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy
        self.ball_vy += GRAVITY

    def _is_ball_off_screen(self) -> bool:
        return (
            self.ball_y > SCREEN_H + BALL_RADIUS * 3
            or self.ball_x < -BALL_RADIUS * 3
            or self.ball_x > SCREEN_W + BALL_RADIUS * 3
        )

    # ── Hit Detection ────────────────────────────────────────────────────
    def _check_building_hit(self) -> Building | None:
        for b in self.buildings:
            closest_x = max(b.x, min(self.ball_x, b.x + b.w))
            closest_y = max(b.y, min(self.ball_y, b.y + b.h))
            dx = self.ball_x - closest_x
            dy = self.ball_y - closest_y
            if dx * dx + dy * dy < BALL_RADIUS * BALL_RADIUS:
                return b
        return None

    # ── Hit Processing ───────────────────────────────────────────────────
    def _process_hit(self, building: Building) -> None:
        match = self.is_super or building.color == self.ball_color

        if match:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            combo_mult = 1.0 + 0.25 * (self.combo - 1)
            score_gain = int(BASE_SCORE * self.combo * combo_mult)
            if self.is_super:
                score_gain *= 3
            self.score += score_gain

            mid_x = building.x + building.w / 2
            mid_y = building.y + building.h / 2
            self._spawn_particles(mid_x, mid_y, building.color)
            text_color = pyxel.COLOR_YELLOW if self.is_super else pyxel.COLOR_WHITE
            self._spawn_floating_text(mid_x, building.y - 5, f"+{score_gain}", text_color)

            if self.combo > 1:
                combo_color = pyxel.COLOR_RED if self.combo >= COMBO_SUPER_THRESHOLD else pyxel.COLOR_YELLOW
                self._spawn_floating_text(SCREEN_W // 2, 60, f"COMBO x{self.combo}!", combo_color)

            if self.combo >= COMBO_SUPER_THRESHOLD and not self.is_super:
                self._activate_super()
        else:
            self.combo = 0
            self.heat += HEAT_MISMATCH
            mid_x = building.x + building.w / 2
            mid_y = building.y + building.h / 2
            self._spawn_particles(mid_x, mid_y, pyxel.COLOR_GRAY)
            self._spawn_floating_text(mid_x, building.y - 5, "WRONG!", pyxel.COLOR_RED)

        self.buildings.remove(building)
        self.play_phase = PlayPhase.IMPACT
        self.impact_timer = IMPACT_FRAMES

    def _handle_miss(self) -> None:
        self.combo = 0
        self.heat += HEAT_MISS
        self._spawn_floating_text(SCREEN_W // 2, SCREEN_H // 2 - 20, "MISS!", pyxel.COLOR_GRAY)

        self.ball_x = max(0.0, min(float(SCREEN_W), self.ball_x))
        self.ball_y = min(float(SCREEN_H + BALL_RADIUS), self.ball_y)
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.play_phase = PlayPhase.RETRACT
        self.retract_timer = RETRACT_FRAMES

    # ── SUPER WRECK ──────────────────────────────────────────────────────
    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self._spawn_floating_text(SCREEN_W // 2, 80, "SUPER WRECK!", pyxel.COLOR_YELLOW)

    # ── Heat ─────────────────────────────────────────────────────────────
    def _update_heat(self) -> None:
        self.heat = max(0.0, min(HEAT_MAX, self.heat - HEAT_DECAY))

    # ── Particles ────────────────────────────────────────────────────────
    def _spawn_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(PARTICLE_COUNT):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(1.0, PARTICLE_SPEED)
            self.particles.append(
                Particle(x=x, y=y, vx=math.cos(angle) * speed, vy=math.sin(angle) * speed, color=color, life=PARTICLE_LIFE)
            )

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.3
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    # ── Floating Text ────────────────────────────────────────────────────
    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, color=color, life=FLOAT_TEXT_LIFE))

    def _update_floating_texts(self) -> None:
        alive: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= FLOAT_TEXT_SPEED
            ft.life -= 1
            if ft.life > 0:
                alive.append(ft)
        self.floating_texts = alive

    # ── Difficulty ───────────────────────────────────────────────────────
    def _update_difficulty(self) -> None:
        t = self._progress()
        self.spawn_interval = int(self._lerp(INITIAL_SPAWN_INTERVAL, FINAL_SPAWN_INTERVAL, t))
        self.color_cycle_speed = int(self._lerp(INITIAL_COLOR_CYCLE, FINAL_COLOR_CYCLE, t))

    # ── Color Cycle ──────────────────────────────────────────────────────
    def _update_color_cycle(self) -> None:
        if self.is_super:
            return
        self.color_timer -= 1
        if self.color_timer <= 0:
            self.color_timer = self.color_cycle_speed
            self.ball_color_idx = (self.ball_color_idx + 1) % len(COLORS)
            self.ball_color = COLORS[self.ball_color_idx]

    # ── Ball Reset ───────────────────────────────────────────────────────
    def _reset_ball_to_pivot(self) -> None:
        self.angle = 0.0
        self.angular_velocity = 0.02 if self.rng.random() > 0.5 else -0.02
        self.ball_x = float(PIVOT_X)
        self.ball_y = float(PIVOT_Y + ROPE_LENGTH)
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.play_phase = PlayPhase.SWINGING
        self.holding = False

    # ── Update ───────────────────────────────────────────────────────────
    def update(self) -> None:
        if self.phase != Phase.PLAYING:
            return

        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self._end_game()
            return

        if self.heat >= HEAT_MAX:
            self._end_game()
            return
        self._update_heat()

        if self.super_timer > 0:
            self.super_timer -= 1
            self.rainbow_tick += 1

        self._update_difficulty()

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_timer = self.spawn_interval
            self._spawn_building()

        self._update_building_anims()
        self._update_color_cycle()

        if self.play_phase == PlayPhase.SWINGING:
            self._update_pendulum(self.holding)
        elif self.play_phase == PlayPhase.FLYING:
            self._update_flying()
            hit = self._check_building_hit()
            if hit is not None:
                self._process_hit(hit)
            elif self._is_ball_off_screen():
                self._handle_miss()
        elif self.play_phase == PlayPhase.IMPACT:
            self.impact_timer -= 1
            if self.impact_timer <= 0:
                self._start_retract()
        elif self.play_phase == PlayPhase.RETRACT:
            self._update_retract()

        if self.shake_frames > 0:
            self.shake_frames -= 1

        self._update_particles()
        self._update_floating_texts()

    def _start_retract(self) -> None:
        self.play_phase = PlayPhase.RETRACT
        self.retract_timer = RETRACT_FRAMES

    def _update_retract(self) -> None:
        self.retract_timer -= 1
        target_x = float(PIVOT_X)
        target_y = float(PIVOT_Y + ROPE_LENGTH)
        self.ball_x = self._lerp(self.ball_x, target_x, 0.1)
        self.ball_y = self._lerp(self.ball_y, target_y, 0.1)

        if self.retract_timer <= 0:
            self._reset_ball_to_pivot()
            if len(self.buildings) < 2:
                self._populate_buildings(2 - len(self.buildings))

    def _end_game(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score

    # ── Draw ─────────────────────────────────────────────────────────────
    def draw(self) -> None:
        pyxel.cls(pyxel.COLOR_BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = "WRECK CHAIN"
        pyxel.text(SCREEN_W // 2 - len(title) * FONT_W // 2, 60, title, pyxel.COLOR_WHITE)

        lines = [
            "Hold SPACE to swing, release to wreck!",
            "Hit same-color buildings to build COMBO",
            "COMBO x4 = SUPER WRECK (3x score!)",
            "Wrong color = HEAT up (100 = GAME OVER)",
            "",
            "TIMER: 60 seconds",
            "",
            "PRESS SPACE TO START",
        ]
        for i, line in enumerate(lines):
            y = 100 + i * (FONT_H + 2)
            pyxel.text(SCREEN_W // 2 - len(line) * FONT_W // 2, y, line, pyxel.COLOR_GRAY)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - len("GAME OVER") * FONT_W // 2, 50, "GAME OVER", pyxel.COLOR_RED)
        score_text = f"SCORE: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_text) * FONT_W // 2, 80, score_text, pyxel.COLOR_WHITE)
        combo_text = f"MAX COMBO: x{self.max_combo}"
        pyxel.text(SCREEN_W // 2 - len(combo_text) * FONT_W // 2, 98, combo_text, pyxel.COLOR_YELLOW)
        best_text = f"BEST: {self.best_score}"
        pyxel.text(SCREEN_W // 2 - len(best_text) * FONT_W // 2, 116, best_text, pyxel.COLOR_GRAY)

        if self.heat >= HEAT_MAX:
            reason = "OVERHEAT!"
        else:
            reason = "TIME'S UP!"
        pyxel.text(SCREEN_W // 2 - len(reason) * FONT_W // 2, 140, reason, pyxel.COLOR_RED)

        retry = "R: RETRY   SPACE: TITLE"
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(SCREEN_W // 2 - len(retry) * FONT_W // 2, 170, retry, pyxel.COLOR_YELLOW)

    def _draw_playing(self) -> None:
        if self.heat >= 70 and self.shake_frames == 0:
            self.shake_frames = 10

        if self.shake_frames > 0:
            sx = self.rng.randint(-2, 2)
            sy = self.rng.randint(-2, 2)
            pyxel.camera(sx, sy)

        self._draw_ground()
        self._draw_buildings()
        self._draw_rope_and_ball()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()
        self._draw_pivot()

        pyxel.camera(0, 0)

    def _draw_hud(self) -> None:
        score_text = f"SCORE:{self.score}"
        pyxel.text(4, 4, score_text, pyxel.COLOR_WHITE)

        if self.combo > 1:
            combo_text = f"COMBO x{self.combo}"
            combo_color = pyxel.COLOR_RED if self.combo >= COMBO_SUPER_THRESHOLD else pyxel.COLOR_YELLOW
            pyxel.text(4, FONT_H + 4, combo_text, combo_color)

        seconds = self.timer // FPS
        time_text = f"TIME:{seconds}"
        pyxel.text(SCREEN_W // 2 - len(time_text) * FONT_W // 2, 4, time_text, pyxel.COLOR_WHITE)

        if self.is_super:
            super_text = f"SUPER WRECK! {self.super_timer // FPS + 1}s"
            pyxel.text(SCREEN_W // 2 - len(super_text) * FONT_W // 2, FONT_H + 4, super_text, pyxel.COLOR_YELLOW)

        bar_w = 80
        bar_h = 6
        bar_x = SCREEN_W - bar_w - 8
        bar_y = 4
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, pyxel.COLOR_DARK_BLUE)
        fill_w = int(bar_w * (self.heat / HEAT_MAX))
        if self.heat < 33:
            heat_c = pyxel.COLOR_GREEN
        elif self.heat < 66:
            heat_c = pyxel.COLOR_YELLOW
        else:
            heat_c = pyxel.COLOR_RED
        pyxel.rect(bar_x, bar_y, fill_w, bar_h, heat_c)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, pyxel.COLOR_WHITE)
        pyxel.text(bar_x - FONT_W * 5 + 1, bar_y - 2, "HEAT", pyxel.COLOR_GRAY)

    def _draw_ground(self) -> None:
        pyxel.line(0, BUILDING_Y, SCREEN_W, BUILDING_Y, pyxel.COLOR_BROWN)
        pyxel.rect(0, BUILDING_Y + 1, SCREEN_W, SCREEN_H - BUILDING_Y - 1, pyxel.COLOR_BROWN)

    def _draw_pivot(self) -> None:
        pyxel.circ(PIVOT_X, PIVOT_Y, 3, pyxel.COLOR_GRAY)

    def _draw_rope_and_ball(self) -> None:
        if self.play_phase in (PlayPhase.SWINGING,):
            pyxel.line(PIVOT_X, PIVOT_Y, int(self.ball_x), int(self.ball_y), pyxel.COLOR_GRAY)
        elif self.play_phase == PlayPhase.RETRACT:
            pyxel.line(PIVOT_X, PIVOT_Y, int(self.ball_x), int(self.ball_y), pyxel.COLOR_GRAY)

        if self.is_super:
            ball_c = COLORS[self.rainbow_tick % 4]
        elif self.heat >= 90 and (pyxel.frame_count // 15) % 2 == 0:
            ball_c = pyxel.COLOR_RED
        else:
            ball_c = self.ball_color

        pyxel.circ(int(self.ball_x), int(self.ball_y), BALL_RADIUS, ball_c)
        pyxel.circb(int(self.ball_x), int(self.ball_y), BALL_RADIUS, pyxel.COLOR_WHITE)

    def _draw_buildings(self) -> None:
        for b in self.buildings:
            display_h = b.h
            if b.spawn_anim > 0:
                display_h = max(1, int(b.h * (1.0 - b.spawn_anim / SPAWN_ANIM_FRAMES)))

            by = BUILDING_Y - display_h
            pyxel.rect(b.x, by, b.w, display_h, b.color)
            pyxel.rectb(b.x, by, b.w, display_h, pyxel.COLOR_WHITE)

            if display_h > 10:
                window_color = pyxel.COLOR_WHITE
                for wy in range(by + 6, BUILDING_Y - 6, 14):
                    for wx in (b.x + 6, b.x + b.w - 10):
                        pyxel.rect(wx, wy, 4, 6, window_color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / PARTICLE_LIFE
            color = p.color if alpha > 0.4 else pyxel.COLOR_GRAY
            pyxel.pset(int(p.x), int(p.y), color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / FLOAT_TEXT_LIFE
            if alpha < 0.2:
                continue
            color = ft.color if alpha > 0.4 else pyxel.COLOR_GRAY
            pyxel.text(int(ft.x) - len(ft.text) * FONT_W // 2, int(ft.y), ft.text, color)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
class App:
    """Pyxel entry point — wires input to Game."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="WRECK CHAIN", display_scale=2)
        if FONT_PATH.exists():
            pyxel.load(str(FONT_PATH))
        self.game = Game()
        self._space_was_held = False
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        g = self.game

        if g.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                g.reset()
        elif g.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_R):
                g.reset()
            elif pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                g._init_state()
                g.phase = Phase.TITLE
        elif g.phase == Phase.PLAYING:
            if g.play_phase == PlayPhase.SWINGING:
                space_held = pyxel.btn(pyxel.KEY_SPACE)
                g.holding = space_held
                if self._space_was_held and not space_held:
                    g._launch_ball()
                self._space_was_held = space_held
            g.update()

    def draw(self) -> None:
        self.game.draw()


def main() -> None:
    App()


if __name__ == "__main__":
    main()
