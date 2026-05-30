from __future__ import annotations

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

SCREEN_W = 320
SCREEN_H = 240

NET_X = 160
NET_TOP_Y = 110

PLAYER_X_MIN = 40
PLAYER_X_MAX = 150
AI_X_MIN = 170
AI_X_MAX = 280

PLAYER_Y = 200
GROUND_Y = 210
CEILING_Y = 30

TOUCH_RANGE_H = 60
TOUCH_RANGE_V = 70

_TOUCH_COLOR_CYCLE: list[int] = [RED, GREEN, LIME, YELLOW]

MAX_POINTS = 5
GRAVITY = 0.3
BOUNCE_FACTOR = 0.7
MAX_SPEED = 10
TOUCHES_PER_SIDE = 3

_COOLDOWN_FRAMES = 10


class Phase(Enum):
    TITLE = auto()
    SERVING = auto()
    PLAYING = auto()
    POINT_SCORED = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float


@dataclass
class Player:
    x: float
    y: float
    touches_left: int
    last_color: int
    combo: int
    max_combo: int


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
    color: int
    life: int


# ---------------------------------------------------------------------------
# Game logic (pyxel-independent)
# ---------------------------------------------------------------------------


def cycle_color(c: int) -> int:
    """Return next color in the cycle: RED->GREEN->LIME->YELLOW->RED."""
    idx = _TOUCH_COLOR_CYCLE.index(c)
    return _TOUCH_COLOR_CYCLE[(idx + 1) % len(_TOUCH_COLOR_CYCLE)]


def compute_touch_combo(last_color: int, current_color: int, current_combo: int) -> int:
    """Return new combo value after a touch."""
    if last_color == current_color:
        return current_combo + 1
    return 1


def is_super_spike(combo: int, touches_left_after: int) -> bool:
    """Super spike triggers when combo >= 3 and it's the spike touch (#3)."""
    return combo >= 3 and touches_left_after == 0


def compute_touch_velocity(touch_index: int, is_super: bool, rng: random.Random) -> tuple[float, float]:
    """Return (vx, vy) for a player touch."""
    if touch_index == 1:  # Bump
        vy = -rng.uniform(4, 5)
        vx = rng.uniform(1, 3)
    elif touch_index == 2:  # Set
        vy = -rng.uniform(5, 6)
        vx = rng.uniform(1, 3)
    else:  # Spike
        vy = -3.0
        vx = rng.uniform(5, 8)
        if is_super:
            vx *= 2
            vy *= 2
    return vx, vy


def compute_ai_touch_velocity(touch_index: int, rng: random.Random) -> tuple[float, float]:
    """Return (vx, vy) for an AI touch."""
    if touch_index == 1:
        vy = -rng.uniform(3, 5)
        vx = -rng.uniform(1, 3)
    elif touch_index == 2:
        vy = -rng.uniform(4, 6)
        vx = -rng.uniform(1, 3)
    else:
        vy = -rng.uniform(2, 4)
        vx = -rng.uniform(3, 7)
    return vx, vy


def update_ball_physics(ball: Ball) -> None:
    """Apply gravity, bounces, speed clamp. Mutates ball in place."""
    ball.vy += GRAVITY

    # Ground bounce
    if ball.y >= GROUND_Y:
        ball.y = GROUND_Y
        ball.vy = -abs(ball.vy) * BOUNCE_FACTOR
        if abs(ball.vy) < 1:
            ball.vy = 0

    # Ceiling bounce
    if ball.y <= CEILING_Y:
        ball.y = CEILING_Y
        ball.vy = abs(ball.vy) * BOUNCE_FACTOR

    # Clamp speed
    ball.vx = max(-MAX_SPEED, min(MAX_SPEED, ball.vx))
    ball.vy = max(-MAX_SPEED, min(MAX_SPEED, ball.vy))

    ball.x += ball.vx
    ball.y += ball.vy


def check_point(ball: Ball) -> int:
    """Return -1=no point, 0=AI scores, 1=player scores."""
    if ball.y >= GROUND_Y and abs(ball.vy) < 0.5:
        if ball.x < NET_X:
            return 0
        return 1
    if ball.x < -20:
        return 1
    if ball.x > SCREEN_W + 20:
        return 0
    return -1


def ball_in_range(ball: Ball, px: float, py: float) -> bool:
    """Check if ball is within touch range of a player at (px, py)."""
    dx = abs(ball.x - px)
    dy = abs(ball.y - py)
    return dx <= TOUCH_RANGE_H and dy <= TOUCH_RANGE_V


def ball_crossed_net(prev_x: float, curr_x: float) -> bool:
    """Detect if ball crossed the net line this frame."""
    return (prev_x < NET_X <= curr_x) or (curr_x < NET_X <= prev_x)


# ---------------------------------------------------------------------------
# Game class
# ---------------------------------------------------------------------------


class Game:
    def __init__(self) -> None:
        self._rng: random.Random = random.Random()
        self._init_state()

    def _init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.ball: Ball = Ball(x=0, y=0, vx=0, vy=0)
        self.player: Player = Player(
            x=100, y=PLAYER_Y, touches_left=TOUCHES_PER_SIDE,
            last_color=-1, combo=0, max_combo=0,
        )
        self.ai: Player = Player(
            x=240, y=PLAYER_Y, touches_left=TOUCHES_PER_SIDE,
            last_color=-1, combo=0, max_combo=0,
        )
        self.particles: list[Particle] = []
        self.floats: list[FloatingText] = []
        self.score_player: int = 0
        self.score_ai: int = 0
        self.player_color: int = RED
        self.ai_color: int = RED
        self._touch_cooldown: int = 0
        self._serve_timer: int = 0
        self._point_timer: int = 0
        self._shake_frames: int = 0
        self._ai_timer: int = 0
        self._serving_side: int = 0  # 0=AI, 1=player
        self._ball_prev_x: float = 0
        self._touch_label: str = ""
        self._touch_label_timer: int = 0
        self._super_spike: bool = False
        self._title_flash: int = 0

    def reset(self) -> None:
        self._init_state()

    # ------------------------------------------------------------------
    # Serve
    # ------------------------------------------------------------------

    def _serve_ball(self) -> None:
        if self._serving_side == 0:
            self.ball.x = AI_X_MIN + 20
            self.ball.y = GROUND_Y - 40
            self.ball.vx = -self._rng.uniform(2, 4)
            self.ball.vy = -self._rng.uniform(3, 5)
        else:
            self.ball.x = PLAYER_X_MAX - 20
            self.ball.y = GROUND_Y - 40
            self.ball.vx = self._rng.uniform(2, 4)
            self.ball.vy = -self._rng.uniform(3, 5)

        self._ball_prev_x = self.ball.x

        self.player.touches_left = TOUCHES_PER_SIDE
        self.ai.touches_left = TOUCHES_PER_SIDE
        self.player.combo = 0
        self.ai.combo = 0
        self.player.last_color = -1
        self.ai.last_color = -1
        self._super_spike = False

    # ------------------------------------------------------------------
    # Player touch
    # ------------------------------------------------------------------

    def _ball_in_player_court(self) -> bool:
        return PLAYER_X_MIN <= self.ball.x <= PLAYER_X_MAX

    def _execute_player_touch(self) -> None:
        if self.player.touches_left <= 0:
            return

        touch_index = TOUCHES_PER_SIDE - self.player.touches_left + 1
        current_color = self.player_color

        # Combo
        self.player.combo = compute_touch_combo(
            self.player.last_color, current_color, self.player.combo,
        )
        self.player.last_color = current_color
        if self.player.combo > self.player.max_combo:
            self.player.max_combo = self.player.combo

        self.player.touches_left -= 1

        super_spike = is_super_spike(self.player.combo, self.player.touches_left)
        self._super_spike = super_spike

        vx, vy = compute_touch_velocity(touch_index, super_spike, self._rng)
        self.ball.vx = vx
        self.ball.vy = vy

        # After 3 touches, ball must go toward AI side
        if self.player.touches_left == 0 and self.ball.vx <= 0:
            self.ball.vx = abs(self.ball.vx)

        self._touch_cooldown = _COOLDOWN_FRAMES

        # Label
        if super_spike:
            self._touch_label = "SUPER SPIKE!"
        elif touch_index == 1:
            self._touch_label = "Bump"
        elif touch_index == 2:
            self._touch_label = "Set"
        else:
            self._touch_label = "Spike"
        self._touch_label_timer = 30

        # Particles
        self._spawn_particles(self.ball.x, self.ball.y, current_color, 20 if super_spike else 8)

        # Screen shake
        if super_spike:
            self._shake_frames = 8
            self._spawn_floating_text(self.ball.x, self.ball.y - 10, "SUPER SPIKE!", YELLOW, 40)

        # Combo text
        if self.player.combo >= 2:
            self._spawn_floating_text(
                self.ball.x, self.ball.y - 20,
                f"+COMBO x{self.player.combo}",
                YELLOW, 30,
            )

        self.player_color = cycle_color(current_color)

    # ------------------------------------------------------------------
    # AI touch
    # ------------------------------------------------------------------

    def _ball_in_ai_court(self) -> bool:
        return AI_X_MIN <= self.ball.x <= AI_X_MAX

    def _execute_ai_touch(self) -> None:
        if self.ai.touches_left <= 0:
            return
        if self._super_spike:
            return

        touch_index = TOUCHES_PER_SIDE - self.ai.touches_left + 1
        current_color = self.ai_color

        self.ai.combo = compute_touch_combo(
            self.ai.last_color, current_color, self.ai.combo,
        )
        self.ai.last_color = current_color
        if self.ai.combo > self.ai.max_combo:
            self.ai.max_combo = self.ai.combo

        self.ai.touches_left -= 1

        vx, vy = compute_ai_touch_velocity(touch_index, self._rng)
        self.ball.vx = vx
        self.ball.vy = vy

        if self.ai.touches_left == 0 and self.ball.vx >= 0:
            self.ball.vx = -abs(self.ball.vx)

        self._ai_timer = self._rng.randint(15, 30)

        self._spawn_particles(self.ball.x, self.ball.y, current_color, 5)
        self.ai_color = cycle_color(current_color)

    # ------------------------------------------------------------------
    # AI movement
    # ------------------------------------------------------------------

    def _update_ai(self) -> None:
        target_x = self.ball.x
        target_x = max(AI_X_MIN, min(AI_X_MAX, target_x))
        dx = target_x - self.ai.x
        self.ai.x += dx * 0.05
        self.ai.x = max(AI_X_MIN, min(AI_X_MAX, self.ai.x))

        if self._ai_timer > 0:
            self._ai_timer -= 1
            return

        if self._ball_in_ai_court() and ball_in_range(self.ball, self.ai.x, self.ai.y):
            self._execute_ai_touch()

    # ------------------------------------------------------------------
    # Particle system
    # ------------------------------------------------------------------

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            self.particles.append(Particle(
                x=x, y=y,
                vx=self._rng.uniform(-2, 2),
                vy=self._rng.uniform(-3, 1),
                life=self._rng.randint(6, 16),
                color=color,
            ))

    def _update_particles(self) -> None:
        new_particles: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05
            p.life -= 1
            if p.life > 0:
                new_particles.append(p)
        self.particles = new_particles

    # ------------------------------------------------------------------
    # Floating text
    # ------------------------------------------------------------------

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int, life: int) -> None:
        self.floats.append(FloatingText(x=x, y=y, text=text, color=color, life=life))

    def _update_floating_texts(self) -> None:
        new_floats: list[FloatingText] = []
        for ft in self.floats:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life > 0:
                new_floats.append(ft)
        self.floats = new_floats

    # ------------------------------------------------------------------
    # Update phases
    # ------------------------------------------------------------------

    def update(self) -> None:
        match self.phase:
            case Phase.TITLE:
                self._update_title()
            case Phase.SERVING:
                self._update_serving()
            case Phase.PLAYING:
                self._update_playing()
            case Phase.POINT_SCORED:
                self._update_point_scored()
            case Phase.GAME_OVER:
                self._update_game_over()

    def _update_title(self) -> None:
        self._title_flash += 1
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.phase = Phase.SERVING
            self._serving_side = 0
            self._serve_timer = 30
            self.score_player = 0
            self.score_ai = 0
            self.player.max_combo = 0
            self.ai.max_combo = 0

    def _update_serving(self) -> None:
        self._serve_timer -= 1
        if self._serve_timer <= 0:
            self._serve_ball()
            self.phase = Phase.PLAYING
            self._ai_timer = self._rng.randint(10, 25)

    def _update_playing(self) -> None:
        # Cooldown
        if self._touch_cooldown > 0:
            self._touch_cooldown -= 1

        # Screen shake
        if self._shake_frames > 0:
            self._shake_frames -= 1
            if self._shake_frames > 0:
                pyxel.camera(self._rng.randint(-3, 3), self._rng.randint(-3, 3))
            else:
                pyxel.camera(0, 0)

        # Touch label timer
        if self._touch_label_timer > 0:
            self._touch_label_timer -= 1
        else:
            self._touch_label = ""

        # Track ball position for net crossing detection
        self._ball_prev_x = self.ball.x
        update_ball_physics(self.ball)

        # Net crossing -> reset touches for both sides
        if ball_crossed_net(self._ball_prev_x, self.ball.x):
            self.player.touches_left = TOUCHES_PER_SIDE
            self.ai.touches_left = TOUCHES_PER_SIDE
            self.player.combo = 0
            self.ai.combo = 0
            self.player.last_color = -1
            self.ai.last_color = -1
            self._super_spike = False

        # Player movement (mouse)
        target_x = float(pyxel.mouse_x)
        target_x = max(PLAYER_X_MIN, min(PLAYER_X_MAX, target_x))
        self.player.x += (target_x - self.player.x) * 0.15

        # Player touch input
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and self._touch_cooldown <= 0:
            if self._ball_in_player_court() and ball_in_range(self.ball, self.player.x, self.player.y):
                self._execute_player_touch()

        # AI
        self._update_ai()

        # Point check
        result = check_point(self.ball)
        if result != -1:
            if result == 1:
                self.score_player += 1
                self._spawn_floating_text(NET_X, SCREEN_H // 2, "POINT!", YELLOW, 50)
                self._spawn_particles(self.ball.x, self.ball.y, YELLOW, 12)
            else:
                self.score_ai += 1
                self._spawn_floating_text(NET_X, SCREEN_H // 2, "LOST...", RED, 50)
                self._spawn_particles(self.ball.x, self.ball.y, RED, 12)
            self._point_timer = 60
            self._super_spike = False
            self.phase = Phase.POINT_SCORED

        # Particles & floating texts
        self._update_particles()
        self._update_floating_texts()

        # R restart
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()

    def _update_point_scored(self) -> None:
        self._point_timer -= 1
        self._update_particles()
        self._update_floating_texts()

        if pyxel.btnp(pyxel.KEY_R):
            self.reset()
            return

        if self._point_timer <= 0:
            if self.score_player >= MAX_POINTS or self.score_ai >= MAX_POINTS:
                self.phase = Phase.GAME_OVER
            else:
                self._serving_side = 1 - self._serving_side
                self.phase = Phase.SERVING
                self._serve_timer = 30

    def _update_game_over(self) -> None:
        self._update_particles()
        self._update_floating_texts()

        if (
            pyxel.btnp(pyxel.KEY_SPACE)
            or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            or pyxel.btnp(pyxel.KEY_R)
        ):
            self.reset()

    # ------------------------------------------------------------------
    # Draw phases
    # ------------------------------------------------------------------

    def draw(self) -> None:
        match self.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.SERVING:
                self._draw_serving()
            case Phase.PLAYING:
                self._draw_playing()
            case Phase.POINT_SCORED:
                self._draw_point_scored()
            case Phase.GAME_OVER:
                self._draw_game_over()

    def _draw_court(self) -> None:
        pyxel.cls(LIGHT_BLUE)

        # Ground
        pyxel.rect(0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y, YELLOW)

        # Court zone markers
        pyxel.rect(PLAYER_X_MIN, GROUND_Y - 1, PLAYER_X_MAX - PLAYER_X_MIN, 2, ORANGE)
        pyxel.rect(AI_X_MIN, GROUND_Y - 1, AI_X_MAX - AI_X_MIN, 2, ORANGE)

        # Net: vertical dashed line
        for yy in range(NET_TOP_Y, GROUND_Y, 6):
            pyxel.rect(NET_X, yy, 2, 3, WHITE)

        # Net top
        pyxel.rect(NET_X - 4, NET_TOP_Y, 10, 2, WHITE)

        # Net pole
        pyxel.rect(NET_X - 1, NET_TOP_Y - 20, 2, 20, GRAY)

    def _draw_player(self, is_ai: bool = False) -> None:
        p = self.ai if is_ai else self.player
        color = RED if is_ai else GREEN
        px = int(p.x)
        py = int(p.y)

        # Legs
        pyxel.rect(px - 4, py + 16, 2, 8, color)
        pyxel.rect(px + 2, py + 16, 2, 8, color)

        # Body + head
        pyxel.rect(px - 2, py - 8, 4, 24, color)
        pyxel.rect(px - 3, py - 12, 6, 6, color)

        # Arm toward ball
        if self.phase in (Phase.PLAYING, Phase.POINT_SCORED):
            bx = int(self.ball.x)
            by = int(self.ball.y)
            ax = px
            ay = py - 2
            dx = bx - ax
            dy = by - ay
            dist = max(1, (dx * dx + dy * dy) ** 0.5)
            arm_len = 10
            ex = ax + int(dx / dist * arm_len)
            ey = ay + int(dy / dist * arm_len)
            pyxel.line(ax, ay, ex, ey, color)

    def _draw_ball(self) -> None:
        bx = int(self.ball.x)
        by = int(self.ball.y)

        if self._super_spike and pyxel.frame_count % 4 < 2:
            color = WHITE
        else:
            if self.ball.x < NET_X:
                color = self.player.last_color if self.player.last_color >= 0 else RED
            else:
                color = self.ai.last_color if self.ai.last_color >= 0 else RED

        pyxel.circ(bx, by, 5, color)
        pyxel.circb(bx, by, 5, WHITE)

    def _draw_hud(self) -> None:
        # Score centered at top
        score_text = f"{self.score_player}  -  {self.score_ai}"
        x = NET_X - len(score_text) * 2
        pyxel.text(x + 1, 4, score_text, BLACK)
        pyxel.text(x, 3, score_text, WHITE)

        # Player combo
        if self.player.combo >= 2:
            combo_text = f"COMBO x{self.player.combo}"
            pyxel.text(10, 4, combo_text, YELLOW)

        # Touch label above player
        if self._touch_label:
            tx = int(self.player.x) - len(self._touch_label) * 2
            ty = int(self.player.y) - 30
            color = YELLOW if "SUPER" in self._touch_label else WHITE
            pyxel.text(tx, ty, self._touch_label, color)

        # Touches remaining
        if self.phase == Phase.PLAYING:
            touches_text = f"Touches: {self.player.touches_left}"
            pyxel.text(10, 16, touches_text, GRAY)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 16.0
            c = p.color if alpha > 0.3 else GRAY
            pyxel.pset(int(p.x), int(p.y), c)

    def _draw_floating_texts(self) -> None:
        for ft in self.floats:
            alpha = ft.life / 50.0
            c = ft.color if alpha > 0.4 else GRAY
            x = int(ft.x) - len(ft.text) * 2
            pyxel.text(x, int(ft.y), ft.text, c)

    def _draw_title(self) -> None:
        pyxel.cls(BLACK)
        pyxel.text(110, 40, "SPIKE CHAIN", RED)
        pyxel.text(85, 58, "Volleyball Color-Match", WHITE)

        lines = [
            "Same-color touches build COMBO!",
            "COMBO x3+ = SUPER SPIKE!",
            "",
            "Mouse: Move  |  Click: Touch",
            "R: Restart",
        ]
        for i, line in enumerate(lines):
            if line:
                x = (SCREEN_W - len(line) * 4) // 2
                pyxel.text(x, 80 + i * 14, line, GRAY)

        # Serve indicator
        pyxel.text(80, 155, "First to 5 points wins!", CYAN)

        if (self._title_flash // 20) % 2 == 0:
            pyxel.text(100, 200, "SPACE / Click to Start", WHITE)

    def _draw_serving(self) -> None:
        self._draw_court()
        self._draw_player()
        self._draw_player(is_ai=True)
        self._draw_hud()
        self._draw_particles()
        self._draw_floating_texts()

        serve_text = "AI Serves..." if self._serving_side == 0 else "Your Serve!"
        x = NET_X - len(serve_text) * 2
        pyxel.text(x, SCREEN_H // 2 - 6, serve_text, WHITE)

    def _draw_playing(self) -> None:
        self._draw_court()
        self._draw_player()
        self._draw_player(is_ai=True)
        self._draw_ball()
        self._draw_hud()
        self._draw_particles()
        self._draw_floating_texts()

    def _draw_point_scored(self) -> None:
        self._draw_court()
        self._draw_player()
        self._draw_player(is_ai=True)
        self._draw_ball()
        self._draw_hud()
        self._draw_particles()
        self._draw_floating_texts()

    def _draw_game_over(self) -> None:
        pyxel.cls(BLACK)

        if self.score_player >= MAX_POINTS:
            title = "VICTORY!"
            color = YELLOW
        else:
            title = "DEFEAT..."
            color = RED

        pyxel.text(110, 30, title, color)
        pyxel.text(70, 55, f"Final Score:  {self.score_player} - {self.score_ai}", WHITE)
        pyxel.text(70, 80, f"Max COMBO: x{self.player.max_combo}", CYAN)

        if (pyxel.frame_count // 20) % 2 == 0:
            pyxel.text(85, 150, "SPACE / Click / R to Retry", YELLOW)

        self._draw_particles()
        self._draw_floating_texts()


# ---------------------------------------------------------------------------
# App (pyxel wrapper)
# ---------------------------------------------------------------------------


class App:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="SPIKE CHAIN", display_scale=2)
        self.game = Game()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        self.game.update()

    def draw(self) -> None:
        self.game.draw()


def main() -> None:
    App()


if __name__ == "__main__":
    main()
