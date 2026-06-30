"""FOOSBALL SURGE — Top-down table football with color-match COMBO chains."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto

import pyxel

# === Color Constants (raw ints) ===
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

ROD_COLORS: tuple[int, ...] = (RED, GREEN, DARK_BLUE, YELLOW)
SUPER_RAINBOW: tuple[int, ...] = (RED, ORANGE, YELLOW, GREEN, LIGHT_BLUE, PURPLE)

PLAYER_DEF_X = 64
PLAYER_FWD_X = 144
AI_FWD_X = 176
AI_DEF_X = 256

ROD_SPEED = 3.0
AI_SPEED = 2.5
BALL_INITIAL_SPEED = 2.0
GOAL_SCORED_PAUSE = 60
SUPER_DURATION = 180
COMBO_THRESHOLD = 4
GOALS_TO_WIN = 5
HEAT_MAX = 100
HEAT_INCREMENT = 15


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Figure:
    x: float
    y: float
    radius: int = 8
    color: int = WHITE


@dataclass
class Rod:
    x: float
    y: float
    color: int
    figures: list[Figure] = field(default_factory=list)


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    color: int = WHITE
    radius: int = 5


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


class Game:
    score: int
    combo: int
    max_combo: int
    goals_player: int
    goals_ai: int
    heat: float
    super_timer: int
    shake_frames: int
    goal_scored_timer: int
    ball: Ball
    rods: list[Rod]
    particles: list[Particle]
    floating_texts: list[FloatingText]
    phase: Phase
    _rng: random.Random
    player_up: bool
    player_down: bool
    player_fwd_up: bool
    player_fwd_down: bool

    def __init__(self) -> None:
        pyxel.init(320, 240, "FOOSBALL SURGE", display_scale=2, fps=60)
        self._rng = random.Random()
        self.particles = []
        self.floating_texts = []
        self.player_up = False
        self.player_down = False
        self.player_fwd_up = False
        self.player_fwd_down = False
        self.reset()
        self.phase = Phase.TITLE
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.goals_player = 0
        self.goals_ai = 0
        self.heat = 0.0
        self.super_timer = 0
        self.shake_frames = 0
        self.goal_scored_timer = 0
        self.particles.clear()
        self.floating_texts.clear()

        colors = list(ROD_COLORS)
        self._rng.shuffle(colors)
        self.rods = [
            Rod(x=PLAYER_DEF_X, y=120, color=colors[0]),
            Rod(x=PLAYER_FWD_X, y=120, color=colors[1]),
            Rod(x=AI_FWD_X, y=120, color=colors[2]),
            Rod(x=AI_DEF_X, y=120, color=colors[3]),
        ]
        for rod in self.rods:
            self._sync_figures(rod)

        angle = self._rng.uniform(0, 2 * math.pi)
        self.ball = Ball(
            x=160, y=120,
            vx=math.cos(angle) * BALL_INITIAL_SPEED,
            vy=math.sin(angle) * BALL_INITIAL_SPEED,
            color=WHITE,
        )

    # ------------------------------------------------------------------ helpers
    def _sync_figures(self, rod: Rod) -> None:
        rod.figures = [
            Figure(x=rod.x, y=rod.y - 22, color=rod.color),
            Figure(x=rod.x, y=rod.y, color=rod.color),
            Figure(x=rod.x, y=rod.y + 22, color=rod.color),
        ]

    def _read_input(self) -> None:
        self.player_up = pyxel.btn(pyxel.KEY_W)
        self.player_down = pyxel.btn(pyxel.KEY_S)
        self.player_fwd_up = pyxel.btn(pyxel.KEY_UP)
        self.player_fwd_down = pyxel.btn(pyxel.KEY_DOWN)

    @staticmethod
    def _clamp_rod_y(y: float) -> float:
        return max(22.0, min(218.0, y))

    # ----------------------------------------------------------- game logic ---

    def _update_rods(self) -> None:
        # Player defense rod (index 0)
        rod = self.rods[0]
        if self.player_up:
            rod.y -= ROD_SPEED
        if self.player_down:
            rod.y += ROD_SPEED
        rod.y = self._clamp_rod_y(rod.y)
        self._sync_figures(rod)

        # Player forward rod (index 1)
        rod = self.rods[1]
        if self.player_fwd_up:
            rod.y -= ROD_SPEED
        if self.player_fwd_down:
            rod.y += ROD_SPEED
        rod.y = self._clamp_rod_y(rod.y)
        self._sync_figures(rod)

        # AI rods (indices 2, 3)
        ai_jitter = math.sin(pyxel.frame_count * 0.08) * 12
        for i in (2, 3):
            rod = self.rods[i]
            target_y = self.ball.y + ai_jitter + (i - 2) * 8
            if rod.y < target_y:
                rod.y = min(rod.y + AI_SPEED, target_y)
            elif rod.y > target_y:
                rod.y = max(rod.y - AI_SPEED, target_y)
            rod.y = self._clamp_rod_y(rod.y)
            self._sync_figures(rod)

    def _update_physics(self) -> None:
        ball = self.ball
        ball.x += ball.vx
        ball.y += ball.vy

        # Top / bottom walls
        if ball.y - ball.radius < 0:
            ball.y = float(ball.radius)
            ball.vy = abs(ball.vy)
        elif ball.y + ball.radius > 240:
            ball.y = 240.0 - ball.radius
            ball.vy = -abs(ball.vy)

        # Goal zones
        if ball.x < 16:
            self._handle_goal("ai")
        elif ball.x > 304:
            self._handle_goal("player")

    def _check_figure_collisions(self) -> None:
        ball = self.ball
        closest_dist = float("inf")
        closest_fig: Figure | None = None

        for rod in self.rods:
            for fig in rod.figures:
                dx = ball.x - fig.x
                dy = ball.y - fig.y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < ball.radius + fig.radius and dist < closest_dist:
                    closest_dist = dist
                    closest_fig = fig

        if closest_fig is None:
            # Un-stick ball if speed is too low
            speed = math.sqrt(ball.vx * ball.vx + ball.vy * ball.vy)
            if speed < 0.5:
                angle = self._rng.uniform(0, 2 * math.pi)
                ball.vx = math.cos(angle) * BALL_INITIAL_SPEED
                ball.vy = math.sin(angle) * BALL_INITIAL_SPEED
            return

        old_color = ball.color
        ball.color = closest_fig.color

        # --- COMBO / HEAT ---
        if old_color != WHITE:
            if closest_fig.color == old_color:
                self.combo += 1
                if self.combo > self.max_combo:
                    self.max_combo = self.combo
                if self.combo >= COMBO_THRESHOLD and self.super_timer <= 0:
                    self._activate_super()
                self.floating_texts.append(
                    FloatingText(ball.x, ball.y, f"+{self.combo} COMBO", 40, closest_fig.color)
                )
            else:
                self.combo = 0
                self.heat = min(HEAT_MAX + 1.0, self.heat + HEAT_INCREMENT)
                self.floating_texts.append(
                    FloatingText(ball.x, ball.y, f"HEAT+{HEAT_INCREMENT}", 40, ORANGE)
                )
        else:
            self.floating_texts.append(
                FloatingText(ball.x, ball.y, "HIT", 30, closest_fig.color)
            )

        # --- Reflection ---
        if closest_dist < 0.001:
            closest_dist = 0.001
        nx = (ball.x - closest_fig.x) / closest_dist
        ny = (ball.y - closest_fig.y) / closest_dist
        dot = ball.vx * nx + ball.vy * ny
        ball.vx -= 2 * dot * nx
        ball.vy -= 2 * dot * ny

        # Enforce minimum speed after bounce
        speed = math.sqrt(ball.vx * ball.vx + ball.vy * ball.vy)
        min_spd = BALL_INITIAL_SPEED
        if speed < min_spd:
            scale = min_spd / speed
            ball.vx *= scale
            ball.vy *= scale

        # Push ball out of figure to prevent re-collision
        overlap = ball.radius + closest_fig.radius - closest_dist + 1
        ball.x += nx * overlap
        ball.y += ny * overlap

        self._spawn_hit_particles(closest_fig.x, closest_fig.y, closest_fig.color)
        self._play_sound(0)

    # ------------------------------------------------------------ SUPER SHOT

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self.ball.vx *= 2.0
        self.ball.vy *= 2.0
        self.floating_texts.append(
            FloatingText(self.ball.x, self.ball.y, "SUPER SHOT!", 50, YELLOW)
        )
        self.shake_frames = 8

    def _update_super_timer(self) -> None:
        if self.super_timer <= 0:
            return
        # Don't expire while a goal is being resolved
        if self.goal_scored_timer > 0:
            # Still spawn particles during pause
            if pyxel.frame_count % 2 == 0:
                self._spawn_super_particle()
            return

        self.super_timer -= 1
        if self.super_timer == 0:
            self.ball.vx /= 2.0
            self.ball.vy /= 2.0
        elif pyxel.frame_count % 2 == 0:
            self._spawn_super_particle()

    def _spawn_super_particle(self) -> None:
        idx = pyxel.frame_count % len(SUPER_RAINBOW)
        self.particles.append(Particle(
            self.ball.x + self._rng.uniform(-6, 6),
            self.ball.y + self._rng.uniform(-6, 6),
            self._rng.uniform(-1.5, 1.5),
            self._rng.uniform(-1.5, 1.5),
            18,
            SUPER_RAINBOW[idx],
        ))

    # ---------------------------------------------------------------- GOAL ---

    def _handle_goal(self, scorer: str) -> None:
        if self.goal_scored_timer > 0:
            return

        is_super = self.super_timer > 0
        points = 300 if is_super else 100
        self.score += points

        if scorer == "player":
            self.goals_player += 1
            goal_x = 304
        else:
            self.goals_ai += 1
            goal_x = 16

        label = f"+{points}" if not is_super else f"+{points} SUPER!"
        self.floating_texts.append(
            FloatingText(float(goal_x), 120, label, 50, YELLOW if is_super else WHITE)
        )
        self._spawn_goal_particles(float(goal_x), 120, 25)
        self.goal_scored_timer = GOAL_SCORED_PAUSE
        self.shake_frames = 12
        self._play_sound(1)
        self._cycle_rod_colors()

    def _cycle_rod_colors(self) -> None:
        colors = [rod.color for rod in self.rods]
        colors = colors[1:] + colors[:1]
        for rod, c in zip(self.rods, colors):
            rod.color = c
            self._sync_figures(rod)

    def _reset_after_goal(self) -> None:
        ball = self.ball
        ball.x = 160
        ball.y = 120
        ball.color = WHITE
        self.combo = 0
        self.super_timer = 0
        angle = self._rng.uniform(0, 2 * math.pi)
        ball.vx = math.cos(angle) * BALL_INITIAL_SPEED
        ball.vy = math.sin(angle) * BALL_INITIAL_SPEED

    # --------------------------------------------------------- particles / fx

    def _spawn_hit_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(6):
            self.particles.append(Particle(
                x, y,
                self._rng.uniform(-2, 2),
                self._rng.uniform(-2, 2),
                20,
                color,
            ))

    def _spawn_goal_particles(self, x: float, y: float, count: int) -> None:
        for _ in range(count):
            self.particles.append(Particle(
                x, y,
                self._rng.uniform(-3, 3),
                self._rng.uniform(-3, 3),
                30,
                WHITE,
            ))

    def _update_particles(self) -> None:
        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts[:]:
            ft.y -= 1.0
            ft.life -= 1
            if ft.life <= 0:
                self.floating_texts.remove(ft)

    def _play_sound(self, idx: int) -> None:
        try:
            pyxel.play(0, idx)
        except BaseException:
            pass

    # ================================================================= update

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.phase = Phase.PLAYING

        elif self.phase == Phase.PLAYING:
            self._read_input()

            if self.goal_scored_timer > 0:
                self.goal_scored_timer -= 1
                self._update_particles()
                self._update_floating_texts()
                self._update_super_timer()
                if self.shake_frames > 0:
                    self.shake_frames -= 1
                if self.goal_scored_timer == 0:
                    self._reset_after_goal()
                    if self.goals_player >= GOALS_TO_WIN or self.goals_ai >= GOALS_TO_WIN:
                        self.phase = Phase.GAME_OVER
            else:
                self._update_rods()
                self._update_physics()
                self._check_figure_collisions()
                self._update_particles()
                self._update_floating_texts()
                self._update_super_timer()
                if self.shake_frames > 0:
                    self.shake_frames -= 1
                if self.heat >= HEAT_MAX:
                    self.phase = Phase.GAME_OVER

        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.phase = Phase.TITLE

    # =================================================================== draw

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.shake_frames > 0:
            ox = self._rng.randint(-3, 3)
            oy = self._rng.randint(-3, 3)
            pyxel.camera(ox, oy)
        else:
            pyxel.camera(0, 0)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    # --------------------------------------------------------- draw screens

    def _draw_title(self) -> None:
        # Animated ball decoration
        bx = 160 + math.sin(pyxel.frame_count * 0.05) * 40
        by = 55 + math.sin(pyxel.frame_count * 0.07) * 10
        pyxel.circ(int(bx), int(by), 6, YELLOW)
        pyxel.circ(int(bx), int(by), 3, WHITE)

        pyxel.text(110, 80, "FOOSBALL SURGE", WHITE)
        pyxel.text(85, 92, "Top-down Table Football", GRAY)

        pyxel.line(70, 108, 250, 108, GRAY)

        pyxel.text(50, 118, "W / S        :  Move Defense Rod", WHITE)
        pyxel.text(50, 130, "UP / DOWN    :  Move Forward Rod", WHITE)
        pyxel.text(50, 148, "Hit same-color figures to build COMBO", YELLOW)
        pyxel.text(50, 160, f"COMBO >= {COMBO_THRESHOLD}  triggers SUPER SHOT (3x score!)", GREEN)

        # Blinking ENTER prompt
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(105, 190, "Press ENTER to Start", WHITE)

        pyxel.text(80, 215, f"First to {GOALS_TO_WIN} goals wins!", GRAY)

    def _draw_playing(self) -> None:
        # Table
        pyxel.rect(16, 0, 288, 240, GRAY)
        pyxel.rect(0, 0, 16, 240, LIGHT_BLUE)
        pyxel.rect(304, 0, 16, 240, LIGHT_BLUE)

        # Centre line
        for yy in range(0, 240, 12):
            pyxel.line(160, yy, 160, yy + 6, WHITE)

        # Rods
        for rod in self.rods:
            pyxel.line(int(rod.x), 20, int(rod.x), 220, WHITE)
            for fig in rod.figures:
                pyxel.circ(int(fig.x), int(fig.y), fig.radius, fig.color)

        # Ball (only if not hidden during goal pause)
        if self.goal_scored_timer <= 0:
            ball = self.ball
            ball_color = ball.color
            if self.super_timer > 0:
                ball_color = SUPER_RAINBOW[pyxel.frame_count % len(SUPER_RAINBOW)]
                # Trail
                pyxel.circ(
                    int(ball.x - ball.vx * 0.4),
                    int(ball.y - ball.vy * 0.4),
                    ball.radius - 1,
                    SUPER_RAINBOW[(pyxel.frame_count + 2) % len(SUPER_RAINBOW)],
                )
            pyxel.circ(int(ball.x), int(ball.y), ball.radius, ball_color)

        # Particles
        for p in self.particles:
            c = p.color
            if p.life < 5:
                c = GRAY
            pyxel.pset(int(p.x), int(p.y), c)

        # Floating texts
        for ft in self.floating_texts:
            if ft.life > 5:
                text_x = int(ft.x) - len(ft.text) * 2
                pyxel.text(text_x, int(ft.y), ft.text, ft.color)

        # ---- HUD ----
        # Score bar
        pyxel.text(8, 2, f"SCORE: {self.score}", WHITE)
        pyxel.text(130, 2, f"P:{self.goals_player}  AI:{self.goals_ai}", WHITE)

        # COMBO
        combo_color = WHITE
        if self.combo >= 2:
            combo_color = YELLOW
        if self.combo >= COMBO_THRESHOLD:
            combo_color = ORANGE
        pyxel.text(8, 11, f"COMBO: {self.combo}  (max {self.max_combo})", combo_color)

        # HEAT bar
        heat_ratio = min(1.0, self.heat / HEAT_MAX)
        heat_color = YELLOW
        if heat_ratio > 0.5:
            heat_color = ORANGE
        if heat_ratio > 0.75:
            heat_color = RED
        bar_w = int(80 * heat_ratio)
        pyxel.rect(232, 2, 80, 6, DARK_BLUE)
        pyxel.rect(232, 2, bar_w, 6, heat_color)
        pyxel.text(232, 10, f"HEAT {int(self.heat)}", heat_color)

        # SUPER indicator
        if self.super_timer > 0:
            sc = SUPER_RAINBOW[pyxel.frame_count % len(SUPER_RAINBOW)]
            sec = max(1, self.super_timer // 60 + 1)
            pyxel.text(135, 20, f"!! SUPER !!  {sec}s", sc)

    def _draw_game_over(self) -> None:
        if self.goals_player >= GOALS_TO_WIN:
            pyxel.text(115, 70, "YOU WIN!", GREEN)
            subtitle = f"You scored {self.goals_player} goals"
        elif self.goals_ai >= GOALS_TO_WIN:
            pyxel.text(105, 70, "YOU LOSE...", RED)
            subtitle = f"AI scored {self.goals_ai} goals"
        else:
            pyxel.text(100, 70, "OVERHEATED!", RED)
            subtitle = "Heat reached maximum"

        pyxel.text(70, 85, subtitle, GRAY)

        pyxel.line(60, 102, 260, 102, GRAY)

        pyxel.text(80, 112, f"Final Score :  {self.score}", WHITE)
        pyxel.text(80, 124, f"Max COMBO   :  {self.max_combo}", YELLOW)
        pyxel.text(80, 136, f"Goals       :  P:{self.goals_player}  AI:{self.goals_ai}", WHITE)

        if self.goals_player >= GOALS_TO_WIN:
            pyxel.text(80, 154, "SUPER shots really paid off!", GREEN)
        elif self.heat >= HEAT_MAX:
            pyxel.text(80, 154, "Watch your HEAT!  Stick to same colors.", ORANGE)

        # Blinking ENTER
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(100, 185, "Press ENTER to Retry", WHITE)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
