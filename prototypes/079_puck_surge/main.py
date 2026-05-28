"""079_puck_surge - Puck Surge

Top-down air hockey arena where the player deflects pucks to build COMBO.
COMBO >= 4 triggers SURGE mode (rainbow pucks, score 3x, 3 seconds).
面白い瞬間 is when same-color pucks are deflected consecutively, COMBO hits 4,
SURGE erupts, and all pucks turn rainbow as they cascade into the AI goal.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import pyxel

# ── Constants ──────────────────────────────────────────────────────────────────
SCREEN_W = 320
SCREEN_H = 240
FPS = 30
DISPLAY_SCALE = 2

# Arena geometry
ARENA_X = 10
ARENA_Y = 10
ARENA_W = 300
ARENA_H = 220
GOAL_W = 80
GOAL_LEFT = ARENA_X + (ARENA_W - GOAL_W) // 2
GOAL_RIGHT = GOAL_LEFT + GOAL_W

# Paddle
PLAYER_W = 40
PLAYER_H = 8
PLAYER_Y = ARENA_Y + ARENA_H - PLAYER_H - 4
AI_W = 40
AI_H = 8
AI_Y = ARENA_Y + 4

# Puck
PUCK_RADIUS = 6
PUCK_SPEED_MIN = 1.5
PUCK_SPEED_MAX = 2.5
PUCK_FRICTION = 0.998
PUCK_COLORS: tuple[int, ...] = (8, 3, 6, 9)  # RED, GREEN, LIGHT_BLUE, ORANGE
SURGE_RAINBOW: tuple[int, ...] = (8, 9, 10, 3, 12, 2)  # RED, ORANGE, YELLOW, GREEN, CYAN, PURPLE

# Game balance
MAX_HP = 5
GAME_DURATION = 60 * FPS  # 60 seconds
SPAWN_INTERVAL_INITIAL = 60
SPAWN_INTERVAL_DECREASE = 2  # every 15 seconds
SPAWN_INTERVAL_MIN = 20
DIFFICULTY_STEP = 15 * FPS  # 15 seconds
COMBO_SURGE_THRESHOLD = 4
SURGE_DURATION = 90  # frames (3 seconds)
SURGE_COOLDOWN = 150  # frames (5 seconds)
AI_UPDATE_INTERVAL = 3
BASE_SCORE = 100

# Particles
PARTICLE_LIFE_MIN = 10
PARTICLE_LIFE_MAX = 20
FLOAT_LIFE = 30
FLOAT_RISE_SPEED = 0.5

# Colors
COL_BLACK = 0
COL_NAVY = 1
COL_PURPLE = 2
COL_GREEN = 3
COL_BROWN = 4
COL_DARK_BLUE = 5
COL_LIGHT_BLUE = 6
COL_WHITE = 7
COL_RED = 8
COL_ORANGE = 9
COL_YELLOW = 10
COL_LIME = 11
COL_CYAN = 12
COL_GRAY = 13
COL_PINK = 14
COL_PEACH = 15

FONT_PATH = Path(__file__).with_name("k8x12.bdf")


# ── Enums ──────────────────────────────────────────────────────────────────────
class Phase(IntEnum):
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2


# ── Data Classes ───────────────────────────────────────────────────────────────
@dataclass
class Puck:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    radius: int = PUCK_RADIUS


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


# ── Game ───────────────────────────────────────────────────────────────────────
class Game:
    def __init__(self) -> None:
        pyxel.init(
            SCREEN_W, SCREEN_H,
            title="Puck Surge",
            display_scale=DISPLAY_SCALE,
            fps=FPS,
        )
        self.font = pyxel.Font(str(FONT_PATH))
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── Init / Reset ───────────────────────────────────────────────────────
    def reset(self) -> None:
        self._rng = random.Random()
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.best_score: int = 0
        self.hp: int = MAX_HP
        self.timer: int = GAME_DURATION
        self.combo: int = 0
        self.max_combo: int = 0
        self.surge_timer: int = 0
        self.surge_cooldown: int = 0
        self.player_x: float = SCREEN_W / 2
        self.player_y: float = PLAYER_Y
        self.player_w: int = PLAYER_W
        self.player_h: int = PLAYER_H
        self.ai_x: float = SCREEN_W / 2
        self.ai_y: float = AI_Y
        self.ai_w: int = AI_W
        self.ai_h: int = AI_H
        self.ai_speed: float = 2.0
        self.last_hit_color: int = -1
        self.pucks: list[Puck] = []
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self.spawn_timer: int = 0
        self.spawn_interval: int = SPAWN_INTERVAL_INITIAL
        self._frame_count: int = 0
        self._shake_frames: int = 0
        self._ai_cooldown: int = 0

    # ── Properties ─────────────────────────────────────────────────────────
    @property
    def time_left(self) -> int:
        return max(0, self.timer // FPS)

    @property
    def is_surge(self) -> bool:
        return self.surge_timer > 0

    @property
    def can_surge(self) -> bool:
        return self.surge_cooldown == 0 and not self.is_surge

    # ── Input Helpers ──────────────────────────────────────────────────────
    @staticmethod
    def _read_confirm() -> bool:
        return pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN)

    @staticmethod
    def _read_mouse_x() -> float:
        return float(pyxel.mouse_x)

    # ── Spawn / Update Logic ───────────────────────────────────────────────
    def _spawn_puck(self) -> None:
        angle = self._rng.uniform(0, 2 * math.pi)
        speed = self._rng.uniform(PUCK_SPEED_MIN, PUCK_SPEED_MAX)
        color = self._rng.choice(PUCK_COLORS)
        self.pucks.append(Puck(
            x=ARENA_X + ARENA_W / 2,
            y=ARENA_Y + ARENA_H / 2,
            vx=math.cos(angle) * speed,
            vy=math.sin(angle) * speed,
            color=color,
        ))

    def _update_pucks(self) -> None:
        for puck in self.pucks:
            puck.x += puck.vx
            puck.y += puck.vy
            puck.vx *= PUCK_FRICTION
            puck.vy *= PUCK_FRICTION

            # Bounce off side walls
            if puck.x - puck.radius < ARENA_X:
                puck.x = ARENA_X + puck.radius
                puck.vx = abs(puck.vx)
            elif puck.x + puck.radius > ARENA_X + ARENA_W:
                puck.x = ARENA_X + ARENA_W - puck.radius
                puck.vx = -abs(puck.vx)

            # Bounce off top wall (except goal area)
            if puck.y - puck.radius < ARENA_Y:
                if puck.x < GOAL_LEFT or puck.x > GOAL_RIGHT:
                    puck.y = ARENA_Y + puck.radius
                    puck.vy = abs(puck.vy)

            # Bounce off bottom wall (except goal area)
            if puck.y + puck.radius > ARENA_Y + ARENA_H:
                if puck.x < GOAL_LEFT or puck.x > GOAL_RIGHT:
                    puck.y = ARENA_Y + ARENA_H - puck.radius
                    puck.vy = -abs(puck.vy)

    def _check_paddle_collision(
        self, paddle_x: float, paddle_y: float,
        paddle_w: float, paddle_h: float,
        is_player: bool,
    ) -> int:
        collisions = 0
        for puck in self.pucks:
            closest_x = max(paddle_x - paddle_w / 2, min(puck.x, paddle_x + paddle_w / 2))
            closest_y = max(paddle_y - paddle_h / 2, min(puck.y, paddle_y + paddle_h / 2))
            dist = math.hypot(puck.x - closest_x, puck.y - closest_y)
            if dist >= puck.radius:
                continue

            overlap = puck.radius - dist
            if overlap <= 0:
                continue
            dx = puck.x - closest_x
            dy = puck.y - closest_y
            if dx == 0 and dy == 0:
                dy = -1.0
            length = math.hypot(dx, dy)
            nx = dx / length
            ny = dy / length
            puck.x += nx * overlap
            puck.y += ny * overlap
            dot = puck.vx * nx + puck.vy * ny
            puck.vx -= 2 * dot * nx
            puck.vy -= 2 * dot * ny
            speed = math.hypot(puck.vx, puck.vy)
            min_speed = PUCK_SPEED_MIN + self.combo * 0.1
            if speed < min_speed:
                scale = min_speed / speed
                puck.vx *= scale
                puck.vy *= scale

            collisions += 1
            self._spawn_particles(puck.x, puck.y, puck.color, count=4)

            if is_player:
                if self.last_hit_color == puck.color:
                    self.combo += 1
                    self.max_combo = max(self.max_combo, self.combo)
                    self._spawn_float(puck.x, puck.y, f"COMBO x{self.combo}", COL_CYAN)
                    if self.combo >= COMBO_SURGE_THRESHOLD and self.can_surge:
                        self._enter_surge()
                else:
                    if self.combo > 0:
                        self._spawn_float(puck.x, puck.y, "MISS!", COL_RED)
                    self.combo = 0
                self.last_hit_color = puck.color
        return collisions

    def _check_goals(self) -> tuple[int, int]:
        player_scored = 0
        ai_scored = 0
        new_pucks: list[Puck] = []
        for puck in self.pucks:
            if puck.y < ARENA_Y and GOAL_LEFT <= puck.x <= GOAL_RIGHT:
                # Player scored (puck entered AI goal - top)
                multiplier = 3 if self.is_surge else 1
                gained = BASE_SCORE * (1 + self.combo) * multiplier
                player_scored += gained
                self._spawn_float(puck.x, puck.y, f"+{gained}", COL_YELLOW)
                self._spawn_particles(puck.x, puck.y, COL_YELLOW, count=12)
                self._shake_frames = 2
            elif puck.y > ARENA_Y + ARENA_H and GOAL_LEFT <= puck.x <= GOAL_RIGHT:
                # AI scored (puck entered player goal - bottom)
                ai_scored += 1
                self._spawn_float(puck.x, puck.y, "LOST!", COL_RED)
                self._spawn_particles(puck.x, puck.y, COL_RED, count=12)
                self._shake_frames = 2
            else:
                new_pucks.append(puck)
        self.pucks = new_pucks
        return player_scored, ai_scored

    def _update_ai(self) -> None:
        self._ai_cooldown += 1
        if self._ai_cooldown % AI_UPDATE_INTERVAL != 0:
            return

        active_w = self.ai_w
        if self.is_surge:
            active_w = self.ai_w // 2

        # Track nearest puck heading toward AI goal
        target_x = ARENA_X + ARENA_W / 2
        best_dist = float("inf")
        for puck in self.pucks:
            if puck.vy < 0:
                dist = abs(puck.x - self.ai_x) + abs(puck.y - self.ai_y)
                if dist < best_dist:
                    best_dist = dist
                    target_x = puck.x

        if target_x < self.ai_x - active_w / 2:
            self.ai_x -= self.ai_speed
        elif target_x > self.ai_x + active_w / 2:
            self.ai_x += self.ai_speed

        # Clamp to arena
        self.ai_x = max(ARENA_X + active_w / 2, min(ARENA_X + ARENA_W - active_w / 2, self.ai_x))

    def _enter_surge(self) -> None:
        self.surge_timer = SURGE_DURATION
        self.surge_cooldown = SURGE_DURATION + SURGE_COOLDOWN
        self.combo = 0
        self._spawn_particles(SCREEN_W / 2, SCREEN_H / 2, COL_YELLOW, count=20)
        self._spawn_float(SCREEN_W / 2, SCREEN_H / 2 - 20, "SURGE!", COL_YELLOW)

    def _update_surge_timers(self) -> None:
        if self.surge_timer > 0:
            self.surge_timer -= 1
        if self.surge_cooldown > 0:
            self.surge_cooldown -= 1

    def _get_puck_draw_color(self, puck: Puck) -> int:
        if not self.is_surge:
            return puck.color
        idx = (self._frame_count // 4) % len(SURGE_RAINBOW)
        return SURGE_RAINBOW[idx]

    def _update_timer(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 0
            self.phase = Phase.GAME_OVER
            if self.score > self.best_score:
                self.best_score = self.score

    def _update_difficulty(self) -> None:
        elapsed = GAME_DURATION - self.timer
        steps = elapsed // DIFFICULTY_STEP
        self.spawn_interval = max(SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_INITIAL - steps * SPAWN_INTERVAL_DECREASE)

    # ── Effects ────────────────────────────────────────────────────────────
    def _spawn_particles(self, x: float, y: float, color: int, count: int = 8) -> None:
        for _ in range(count):
            self.particles.append(Particle(
                x=x,
                y=y,
                vx=self._rng.uniform(-2.0, 2.0),
                vy=self._rng.uniform(-2.0, 2.0),
                life=self._rng.randint(PARTICLE_LIFE_MIN, PARTICLE_LIFE_MAX),
                color=color,
            ))

    def _update_particles(self) -> None:
        survived: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                survived.append(p)
        self.particles = survived

    def _spawn_float(self, x: float, y: float, text: str, color: int) -> None:
        self.floats.append(FloatingText(x=x, y=y, text=text, life=FLOAT_LIFE, color=color))

    def _update_floats(self) -> None:
        survived: list[FloatingText] = []
        for f in self.floats:
            f.y -= FLOAT_RISE_SPEED
            f.life -= 1
            if f.life > 0:
                survived.append(f)
        self.floats = survived

    # ── Text Helpers ───────────────────────────────────────────────────────
    def _text_center(self, s: str, y: int, col: int) -> None:
        w = self.font.text_width(s)
        x = (SCREEN_W - w) // 2
        pyxel.text(x + 1, y + 1, s, COL_BLACK, self.font)
        pyxel.text(x, y, s, col, self.font)

    def _text(self, s: str, x: int, y: int, col: int) -> None:
        pyxel.text(x + 1, y + 1, s, COL_BLACK, self.font)
        pyxel.text(x, y, s, col, self.font)

    # ── Update ─────────────────────────────────────────────────────────────
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if self._read_confirm():
                self.reset()
                self.phase = Phase.PLAYING
            return

        if self.phase == Phase.GAME_OVER:
            if self._read_confirm():
                self.reset()
                self.phase = Phase.PLAYING
            return

        # ── PLAYING ──
        self._frame_count += 1

        self.player_x = self._read_mouse_x()
        self.player_x = max(
            ARENA_X + PLAYER_W / 2,
            min(ARENA_X + ARENA_W - PLAYER_W / 2, self.player_x),
        )

        self._update_timer()
        if self.phase == Phase.GAME_OVER:
            return

        self._update_difficulty()

        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0
            self._spawn_puck()

        self._update_pucks()
        self._check_paddle_collision(self.player_x, PLAYER_Y, PLAYER_W, PLAYER_H, is_player=True)
        self._check_paddle_collision(self.ai_x, AI_Y, AI_W, AI_H, is_player=False)
        player_scored, ai_scored = self._check_goals()

        if player_scored > 0:
            self.score += player_scored
        if ai_scored > 0:
            self.hp -= ai_scored
            if self.hp <= 0:
                self.hp = 0
                if self.score > self.best_score:
                    self.best_score = self.score
                self.phase = Phase.GAME_OVER
                return

        self._update_ai()
        self._update_surge_timers()
        self._update_particles()
        self._update_floats()

        # Screen shake
        if self._shake_frames > 0:
            self._shake_frames -= 1

    # ── Draw ───────────────────────────────────────────────────────────────
    def draw(self) -> None:
        pyxel.cls(COL_BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        # Screen shake
        shake_x = shake_y = 0
        if self._shake_frames > 0:
            shake_x = self._rng.randint(-2, 2)
            shake_y = self._rng.randint(-2, 2)
        pyxel.camera(shake_x, shake_y)

        self._draw_arena()
        self._draw_goals()
        self._draw_pucks()
        self._draw_paddles()
        self._draw_particles()
        self._draw_floats()
        self._draw_hud()

        pyxel.camera(0, 0)

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        self._text_center("PUCK SURGE", 40, COL_CYAN)
        self._text_center("Click or SPACE to Start", 100, COL_WHITE)
        self._text_center("Mouse: Move Paddle", 140, COL_GRAY)
        self._text_center(f"Best Score: {self.best_score}", 200, COL_YELLOW)

    def _draw_arena(self) -> None:
        if self.is_surge:
            border_col = SURGE_RAINBOW[(self._frame_count // 4) % len(SURGE_RAINBOW)]
        else:
            border_col = COL_GRAY
        pyxel.rectb(ARENA_X - 1, ARENA_Y - 1, ARENA_W + 2, ARENA_H + 2, border_col)

    def _draw_goals(self) -> None:
        # AI goal (top)
        pyxel.line(GOAL_LEFT, ARENA_Y, GOAL_RIGHT, ARENA_Y, COL_YELLOW)
        # Player goal (bottom)
        pyxel.line(GOAL_LEFT, ARENA_Y + ARENA_H, GOAL_RIGHT, ARENA_Y + ARENA_H, COL_YELLOW)

    def _draw_paddles(self) -> None:
        # Player paddle
        p_col = COL_CYAN if self.is_surge else COL_WHITE
        p_l = int(self.player_x - PLAYER_W / 2)
        p_t = int(PLAYER_Y - PLAYER_H / 2)
        pyxel.rect(p_l, p_t, PLAYER_W, PLAYER_H, p_col)
        pyxel.rect(p_l + 1, p_t + 1, PLAYER_W - 2, PLAYER_H - 2, COL_BLACK)

        # AI paddle
        ai_w = (AI_W // 2) if self.is_surge else AI_W
        ai_l = int(self.ai_x - ai_w / 2)
        ai_t = int(AI_Y - AI_H / 2)
        ai_col = COL_GRAY
        pyxel.rect(ai_l, ai_t, ai_w, AI_H, ai_col)

    def _draw_pucks(self) -> None:
        for puck in self.pucks:
            draw_col = self._get_puck_draw_color(puck)
            pyxel.circ(int(puck.x), int(puck.y), puck.radius, draw_col)
            if not self.is_surge:
                pyxel.circb(int(puck.x), int(puck.y), puck.radius, COL_WHITE)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / PARTICLE_LIFE_MAX
            radius = max(1, int(3 * alpha))
            col = p.color if pyxel.frame_count % 2 == 0 else COL_WHITE
            pyxel.circ(int(p.x), int(p.y), radius, col)

    def _draw_floats(self) -> None:
        for f in self.floats:
            alpha = f.life / FLOAT_LIFE
            col = f.color if alpha > 0.5 else COL_GRAY
            pyxel.text(int(f.x) - len(f.text) * 2, int(f.y), f.text, col, self.font)

    def _draw_hud(self) -> None:
        # Score
        self._text(f"SCORE: {self.score}", 4, 3, COL_WHITE)

        # Timer
        secs = self.time_left
        timer_col = COL_RED if secs <= 10 else COL_WHITE
        self._text(f"TIME: {secs}s", 4, 15, timer_col)

        # HP hearts
        hearts = ""
        for i in range(MAX_HP):
            hearts += "O" if i < self.hp else "X"
        self._text(f"HP: {hearts}", 4, 27, COL_RED if self.hp <= 1 else COL_GREEN)

        # COMBO
        if self.combo > 0:
            self._text(f"COMBO: x{self.combo}", SCREEN_W // 2 - 30, 3, COL_CYAN)

        # SURGE gauge
        if self.is_surge:
            gauge_text = f"SURGE: {self.surge_timer // FPS + 1}s"
            self._text(gauge_text, SCREEN_W // 2 - 30, 15, COL_YELLOW)
        elif self.surge_cooldown > 0:
            progress = 1.0 - (self.surge_cooldown / (SURGE_DURATION + SURGE_COOLDOWN))
            bar_w = 60
            bar_h = 4
            bar_x = SCREEN_W // 2 - bar_w // 2
            bar_y = 18
            pyxel.rectb(bar_x, bar_y, bar_w, bar_h, COL_GRAY)
            fill_w = int(bar_w * progress)
            pyxel.rect(bar_x, bar_y, fill_w, bar_h, COL_YELLOW)
        elif self.can_surge:
            self._text("SURGE READY", SCREEN_W // 2 - 35, 15, COL_YELLOW)

        # Max combo
        if self.max_combo > 0:
            self._text(f"BEST COMBO: x{self.max_combo}", SCREEN_W - 90, 3, COL_GRAY)

    def _draw_game_over(self) -> None:
        # Dark overlay
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, COL_BLACK)
        is_new_best = self.score >= self.best_score and self.score > 0
        col = COL_YELLOW if is_new_best else COL_RED
        self._text_center("GAME OVER", 60, col)
        self._text_center(f"Score: {self.score}", 110, COL_WHITE)
        self._text_center(f"Best: {self.best_score}", 130, COL_YELLOW)
        self._text_center(f"Max Combo: x{self.max_combo}", 150, COL_CYAN)
        if is_new_best:
            self._text_center("NEW BEST!", 180, COL_YELLOW)
        self._text_center("Click or SPACE to Retry", 210, COL_GRAY)


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
