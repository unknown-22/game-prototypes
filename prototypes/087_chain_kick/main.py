from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

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

BALL_COLORS: list[int] = [RED, GREEN, LIGHT_BLUE, YELLOW]
BALL_COLOR_NAMES: dict[int, str] = {
    RED: "RED",
    GREEN: "GREEN",
    LIGHT_BLUE: "BLUE",
    YELLOW: "YELLOW",
}

GOAL_LEFT = 60
GOAL_RIGHT = 260
GOAL_TOP = 40
GOAL_BOTTOM = 200
GOAL_WIDTH = GOAL_RIGHT - GOAL_LEFT
GOAL_HEIGHT = GOAL_BOTTOM - GOAL_TOP
GOAL_CENTER_X = 160
GOAL_CENTER_Y = 120

PENALTY_X = 160
PENALTY_Y = 200

GK_Y = 100
GK_WIDTH = 16
GK_HEIGHT = 36

POST_THICKNESS = 4
BAR_THICKNESS = 4

ROUNDS_TOTAL = 10
MAX_HEAT = 10
SUPER_COMBO_THRESHOLD = 3
SUPER_BONUS = 50
SPEED_BONUS = 20
SPEED_BONUS_FRAMES = 60  # 2 seconds at 30fps
BASE_SCORE = 10
COMBO_SCORE_MULT = 5

HEAT_SAVE = 2
HEAT_MISS = 1
HEAT_GOAL_DEC = 1

SHOT_SPEED = 6.0
RESULT_DELAY = 45
SHAKE_FRAMES = 8

COLOR_CYCLE: list[int] = [RED, GREEN, LIGHT_BLUE, YELLOW]


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    SHOT_ANIM = auto()
    RESULT = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Ball:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    color: int = 0
    target_x: float = 160.0
    target_y: float = 140.0
    active: bool = False
    shot_frame: int = 0


@dataclass
class Goalkeeper:
    x: float = 160.0
    y: float = 100.0
    dive_x: float = 0.0
    dive_y: float = 0.0
    direction: int = -1
    diving: bool = False
    dive_timer: int = 0
    guess_color: int = -1
    dive_target_x: float = 160.0
    dive_target_y: float = 100.0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: int
    life: int


# ---------------------------------------------------------------------------
# Pure game logic (pyxel-independent, testable)
# ---------------------------------------------------------------------------


def choose_ball_color(rng: random.Random) -> int:
    return rng.choice(BALL_COLORS)


def gk_choose_direction(
    heat: int,
    rng: random.Random,
    last_shot_x: float | None = None,
    last_shot_y: float | None = None,
    prev_ball_colors: list[int] | None = None,
) -> tuple[int, float, float, int]:
    """Return (direction, target_x, target_y, guess_color).

    direction: -1=center, 0=left, 1=right
    """
    heat_bias = 0.35 + heat * 0.05
    heat_bias = min(heat_bias, 0.9)

    if last_shot_x is not None and rng.random() < heat_bias:
        target_x = last_shot_x
        if target_x < 120:
            direction = 0
        elif target_x > 200:
            direction = 1
        else:
            direction = -1
    else:
        direction = rng.choices([-1, 0, 1], weights=[30, 20, 50])[0]
        if direction == 0:
            target_x = rng.uniform(70, 120)
        elif direction == 1:
            target_x = rng.uniform(200, 250)
        else:
            target_x = rng.uniform(140, 180)

    target_y = rng.uniform(80, 150)

    if prev_ball_colors:
        guess_color = rng.choice(prev_ball_colors[-3:]) if rng.random() < 0.7 else rng.choice(BALL_COLORS)
    else:
        guess_color = rng.choice(BALL_COLORS)

    return direction, target_x, target_y, guess_color


def resolve_shot(
    target_x: float,
    target_y: float,
    ball_color: int,
    gk_direction: int,
    gk_guess_color: int,
    gk_dive_x: float,
    gk_dive_y: float,
    is_super: bool,
) -> str:
    """Return "GOAL", "SAVE", "MISS", or "SUPER"."""
    if is_super:
        return "SUPER"

    if target_x <= GOAL_LEFT + POST_THICKNESS:
        return "MISS"
    if target_x >= GOAL_RIGHT - POST_THICKNESS:
        return "MISS"
    if target_y <= GOAL_TOP + BAR_THICKNESS:
        return "MISS"
    if target_y >= GOAL_BOTTOM:
        return "MISS"

    if gk_direction == -1:
        return "GOAL"

    dx = abs(target_x - gk_dive_x)
    dy = abs(target_y - gk_dive_y)
    if dx < 40 and dy < 40:
        if gk_guess_color == ball_color:
            return "SAVE"
        return "GOAL"

    return "GOAL"


def update_combo(result: str, ball_color: int, prev_color: int, current_combo: int) -> int:
    """Return new combo value."""
    if result == "SAVE" or result == "MISS":
        return 0
    if result == "GOAL" or result == "SUPER":
        if ball_color == prev_color:
            return current_combo + 1
        return 1
    return current_combo


def compute_score(result: str, combo: int, is_super: bool, shot_frames: int) -> tuple[int, str]:
    """Return (score_delta, label)."""
    if result == "SAVE" or result == "MISS":
        return 0, ""

    base = BASE_SCORE + combo * COMBO_SCORE_MULT
    bonus = 0
    labels: list[str] = []

    if is_super:
        bonus += SUPER_BONUS
        labels.append("SUPER!!")

    if shot_frames <= SPEED_BONUS_FRAMES:
        bonus += SPEED_BONUS
        labels.append("FAST!")

    if combo >= 2:
        labels.append(f"COMBO x{combo}")

    total = base + bonus
    label = "  ".join(labels) if labels else ""
    return total, label


def update_heat(result: str, current_heat: int) -> int:
    """Return new heat value."""
    if result == "SAVE":
        return min(MAX_HEAT, current_heat + HEAT_SAVE)
    if result == "MISS":
        return min(MAX_HEAT, current_heat + HEAT_MISS)
    if result == "GOAL":
        return max(0, current_heat - HEAT_GOAL_DEC)
    return current_heat


def is_in_goal_area(x: float, y: float) -> bool:
    """Check if coords are within valid goal target area."""
    return GOAL_LEFT + POST_THICKNESS < x < GOAL_RIGHT - POST_THICKNESS and GOAL_TOP + BAR_THICKNESS < y < GOAL_BOTTOM


def compute_ball_trajectory(
    start_x: float, start_y: float, target_x: float, target_y: float, speed: float
) -> tuple[float, float]:
    """Return (vx, vy) for ball launch."""
    dx = target_x - start_x
    dy = target_y - start_y
    dist = (dx * dx + dy * dy) ** 0.5
    if dist < 1:
        return 0.0, -speed
    return dx / dist * speed, dy / dist * speed


# ---------------------------------------------------------------------------
# Game class
# ---------------------------------------------------------------------------


class Game:
    def __init__(self) -> None:
        self._rng: random.Random = random.Random()
        self._font_path = Path(__file__).with_name("k8x12.bdf")
        self._init_state()

    def _init_state(self) -> None:
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: int = 0
        self.round: int = 0
        self.rounds_total: int = ROUNDS_TOTAL
        self.phase: Phase = Phase.TITLE

        self.ball_color: int = RED
        self.prev_ball_colors: list[int] = []
        self.ball: Ball = Ball(x=PENALTY_X, y=PENALTY_Y, color=RED)
        self.goalkeeper: Goalkeeper = Goalkeeper(x=GOAL_CENTER_X, y=GK_Y)
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []

        self.aim_x: int = GOAL_CENTER_X
        self.aim_y: int = GOAL_CENTER_Y
        self.result_timer: int = 0
        self.last_result: str = ""
        self.last_shot_label: str = ""
        self.last_score_delta: int = 0
        self.shake_frames: int = 0
        self.is_super: bool = False
        self.title_flash: int = 0
        self.shot_frame_count: int = 0

    def reset(self) -> None:
        self._init_state()

    # ------------------------------------------------------------------
    # Phase: TITLE
    # ------------------------------------------------------------------

    def _update_title(self) -> None:
        self.title_flash += 1
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
            self._start_game()

    def _start_game(self) -> None:
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0
        self.round = 1
        self.prev_ball_colors.clear()
        self._setup_round()
        self.phase = Phase.PLAYING

    # ------------------------------------------------------------------
    # Phase: PLAYING
    # ------------------------------------------------------------------

    def _setup_round(self) -> None:
        self.ball_color = self._rng.choice(BALL_COLORS)
        self.ball = Ball(x=PENALTY_X, y=PENALTY_Y, color=self.ball_color)
        self.goalkeeper = Goalkeeper(x=GOAL_CENTER_X, y=GK_Y)
        self.aim_x = GOAL_CENTER_X
        self.aim_y = GOAL_CENTER_Y
        self.last_result = ""
        self.last_shot_label = ""
        self.last_score_delta = 0
        self.is_super = False

    def _update_playing(self) -> None:
        self.aim_x = pyxel.mouse_x
        self.aim_y = pyxel.mouse_y

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._shoot()

    def _shoot(self) -> None:
        target_x = float(self.aim_x)
        target_y = float(self.aim_y)

        target_x = max(GOAL_LEFT, min(GOAL_RIGHT, target_x))
        target_y = max(GOAL_TOP, min(GOAL_BOTTOM, target_y))

        self.ball.target_x = target_x
        self.ball.target_y = target_y
        self.ball.active = True
        self.ball.shot_frame = 0

        self.is_super = self.combo >= SUPER_COMBO_THRESHOLD

        if self.is_super:
            self.ball.color = WHITE

        vx, vy = compute_ball_trajectory(PENALTY_X, PENALTY_Y, target_x, target_y, SHOT_SPEED)
        self.ball.vx = vx
        self.ball.vy = vy

        direction, dive_tx, dive_ty, guess_color = gk_choose_direction(
            self.heat,
            self._rng,
            last_shot_x=self.ball.target_x if self.round > 1 else None,
            last_shot_y=self.ball.target_y if self.round > 1 else None,
            prev_ball_colors=self.prev_ball_colors,
        )

        self.goalkeeper.direction = direction
        self.goalkeeper.guess_color = guess_color
        self.goalkeeper.dive_x = 0.0
        self.goalkeeper.dive_y = 0.0
        self.goalkeeper.dive_target_x = dive_tx
        self.goalkeeper.dive_target_y = dive_ty
        self.goalkeeper.diving = True
        self.goalkeeper.dive_timer = 0

        self.shot_frame_count = 0
        self.phase = Phase.SHOT_ANIM

    # ------------------------------------------------------------------
    # Phase: SHOT_ANIM
    # ------------------------------------------------------------------

    def _update_shot_anim(self) -> None:
        self.shot_frame_count += 1
        self.ball.shot_frame += 1

        self.ball.x += self.ball.vx
        self.ball.y += self.ball.vy

        self._update_gk_dive()

        dist_to_target = (
            (self.ball.x - self.ball.target_x) ** 2 + (self.ball.y - self.ball.target_y) ** 2
        ) ** 0.5

        if dist_to_target < 8 or self.ball.shot_frame > 60:
            self.ball.x = self.ball.target_x
            self.ball.y = self.ball.target_y
            self._resolve_result()

    def _update_gk_dive(self) -> None:
        gk = self.goalkeeper
        if not gk.diving:
            return
        gk.dive_timer += 1
        gk.dive_x += (gk.dive_target_x - gk.x - gk.dive_x) * 0.3
        gk.dive_y += (gk.dive_target_y - gk.y - gk.dive_y) * 0.3

    def _resolve_result(self) -> None:
        result = resolve_shot(
            self.ball.target_x,
            self.ball.target_y,
            self.ball_color,
            self.goalkeeper.direction,
            self.goalkeeper.guess_color,
            self.goalkeeper.x + self.goalkeeper.dive_x,
            self.goalkeeper.y + self.goalkeeper.dive_y,
            self.is_super,
        )

        self.last_result = result

        prev_color = self.prev_ball_colors[-1] if self.prev_ball_colors else -1
        self.combo = update_combo(result, self.ball_color, prev_color, self.combo)
        if self.combo > self.max_combo:
            self.max_combo = self.combo

        score_delta, label = compute_score(result, self.combo, self.is_super, self.shot_frame_count)
        self.score += score_delta
        self.last_score_delta = score_delta
        self.last_shot_label = label

        self.heat = update_heat(result, self.heat)

        self.prev_ball_colors.append(self.ball_color)
        if len(self.prev_ball_colors) > 5:
            self.prev_ball_colors.pop(0)

        # Visual effects
        if result == "SUPER" or result == "GOAL":
            particle_color = YELLOW if result == "SUPER" else self.ball_color
            count = 30 if result == "SUPER" else 15
            self._spawn_particles(self.ball.target_x, self.ball.target_y, particle_color, count)

            if result == "SUPER":
                self._spawn_particles(self.ball.target_x, self.ball.target_y, WHITE, 15)
                self.shake_frames = SHAKE_FRAMES

            if score_delta > 0:
                self._spawn_floating_text(
                    self.ball.target_x, self.ball.target_y - 10,
                    f"+{score_delta}", YELLOW, 40,
                )
            if label:
                self._spawn_floating_text(
                    self.ball.target_x, self.ball.target_y - 22,
                    label, CYAN, 40,
                )
        elif result == "SAVE":
            self._spawn_particles(self.ball.target_x, self.ball.target_y, RED, 10)
            self._spawn_floating_text(
                self.ball.target_x, self.ball.target_y - 10,
                "SAVED!", RED, 40,
            )
        elif result == "MISS":
            self._spawn_particles(self.ball.target_x, self.ball.target_y, GRAY, 8)
            self._spawn_floating_text(
                self.ball.target_x, self.ball.target_y - 10,
                "MISS!", GRAY, 40,
            )

        self.result_timer = RESULT_DELAY
        self.phase = Phase.RESULT

    # ------------------------------------------------------------------
    # Phase: RESULT
    # ------------------------------------------------------------------

    def _update_result(self) -> None:
        self.result_timer -= 1
        self._update_particles()
        self._update_floating_texts()

        if self.shake_frames > 0:
            self.shake_frames -= 1
            if self.shake_frames > 0:
                pyxel.camera(self._rng.randint(-3, 3), self._rng.randint(-3, 3))
            else:
                pyxel.camera(0, 0)

        if self.result_timer <= 0:
            if self.heat >= MAX_HEAT or self.round >= self.rounds_total:
                self.phase = Phase.GAME_OVER
            else:
                self.round += 1
                self._setup_round()
                self.phase = Phase.PLAYING

    # ------------------------------------------------------------------
    # Phase: GAME_OVER
    # ------------------------------------------------------------------

    def _update_game_over(self) -> None:
        self._update_particles()
        self._update_floating_texts()

        if (
            pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT)
            or pyxel.btnp(pyxel.KEY_SPACE)
            or pyxel.btnp(pyxel.KEY_RETURN)
            or pyxel.btnp(pyxel.KEY_R)
        ):
            self.reset()
            self._start_game()

    # ------------------------------------------------------------------
    # Particle system
    # ------------------------------------------------------------------

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            self.particles.append(Particle(
                x=x, y=y,
                vx=self._rng.uniform(-2.5, 2.5),
                vy=self._rng.uniform(-4, 1),
                life=self._rng.randint(8, 20),
                color=color,
                size=self._rng.randint(1, 3),
            ))

    def _update_particles(self) -> None:
        new_particles: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.3
            p.life -= 1
            if p.life > 0:
                new_particles.append(p)
        self.particles = new_particles

    # ------------------------------------------------------------------
    # Floating text
    # ------------------------------------------------------------------

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int, life: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, color=color, life=life))

    def _update_floating_texts(self) -> None:
        new_floats: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life > 0:
                new_floats.append(ft)
        self.floating_texts = new_floats

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------

    def update(self) -> None:
        match self.phase:
            case Phase.TITLE:
                self._update_title()
            case Phase.PLAYING:
                self._update_playing()
            case Phase.SHOT_ANIM:
                self._update_shot_anim()
            case Phase.RESULT:
                self._update_result()
            case Phase.GAME_OVER:
                self._update_game_over()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self) -> None:
        match self.phase:
            case Phase.TITLE:
                self._draw_title()
            case Phase.PLAYING | Phase.SHOT_ANIM:
                self._draw_playing()
            case Phase.RESULT:
                self._draw_result()
            case Phase.GAME_OVER:
                self._draw_game_over()

    def _draw_field(self) -> None:
        pyxel.cls(DARK_BLUE)

        # Field (green pitch behind goal)
        pyxel.rect(0, GOAL_BOTTOM + 20, SCREEN_W, SCREEN_H - GOAL_BOTTOM - 20, 3)

        # Goal frame: posts
        pyxel.rect(GOAL_LEFT, GOAL_TOP, POST_THICKNESS, GOAL_BOTTOM - GOAL_TOP, WHITE)
        pyxel.rect(GOAL_RIGHT - POST_THICKNESS, GOAL_TOP, POST_THICKNESS, GOAL_BOTTOM - GOAL_TOP, WHITE)

        # Crossbar
        pyxel.rect(GOAL_LEFT, GOAL_TOP, GOAL_WIDTH, BAR_THICKNESS, WHITE)

        # Net (dashed)
        for yy in range(GOAL_TOP + BAR_THICKNESS, GOAL_BOTTOM, 8):
            for xx in range(GOAL_LEFT + POST_THICKNESS, GOAL_RIGHT - POST_THICKNESS, 8):
                if (xx // 4 + yy // 4) % 3 == 0:
                    pyxel.pset(xx, yy, GRAY)

        # Penalty spot
        pyxel.circb(PENALTY_X, PENALTY_Y, 3, WHITE)

    def _draw_goalkeeper(self) -> None:
        gk = self.goalkeeper
        gk_x = int(gk.x + gk.dive_x)
        gk_y = int(gk.y + gk.dive_y)

        # Body
        pyxel.rect(gk_x - 8, gk_y - 8, GK_WIDTH, GK_HEIGHT, ORANGE)

        # Head
        pyxel.circ(gk_x, gk_y - 14, 8, ORANGE)

        # Eyes
        eye_offset = 3 if gk.direction == 0 else (-3 if gk.direction == 1 else 0)
        pyxel.pset(gk_x - 3 + eye_offset, gk_y - 16, BLACK)
        pyxel.pset(gk_x + 3 + eye_offset, gk_y - 16, BLACK)

        # Gloves
        glove_color = YELLOW if gk.diving else ORANGE
        pyxel.rect(gk_x - 12, gk_y - 2, 6, 4, glove_color)
        pyxel.rect(gk_x + 6, gk_y - 2, 6, 4, glove_color)

        # Glow on diving
        if gk.diving:
            dive_progress = min(1.0, gk.dive_timer / 12.0)
            if dive_progress < 1.0:
                gx = int(gk.x + gk.dive_x * dive_progress)
                gy = int(gk.y + gk.dive_y * dive_progress)
                pyxel.circb(gx, gy, 14, GRAY)

        if self.phase in (Phase.SHOT_ANIM, Phase.RESULT):
            pass

    def _draw_ball(self) -> None:
        b = self.ball
        if not b.active:
            bx = PENALTY_X
            by = PENALTY_Y
        else:
            bx = int(b.x)
            by = int(b.y)

        color = b.color

        if self.is_super and b.active and (pyxel.frame_count % 6 < 3):
            color = BALL_COLORS[(pyxel.frame_count // 3) % len(BALL_COLORS)]

        # Shadow
        if b.active:
            pyxel.circ(bx, by + 2, 5, BLACK)

        pyxel.circ(bx, by, 6, color)
        pyxel.circb(bx, by, 6, WHITE)

        # Color dot
        if not self.is_super or not b.active:
            pyxel.circ(bx, by, 2, BLACK)

    def _draw_aim_reticle(self) -> None:
        if self.phase != Phase.PLAYING:
            return
        ax = self.aim_x
        ay = self.aim_y
        ax = max(GOAL_LEFT, min(GOAL_RIGHT, ax))
        ay = max(GOAL_TOP, min(GOAL_BOTTOM, ay))

        reticle_in_goal = is_in_goal_area(float(ax), float(ay))
        color = WHITE if reticle_in_goal else RED

        size = 8
        pyxel.line(ax - size, ay, ax - 4, ay, color)
        pyxel.line(ax + size, ay, ax + 4, ay, color)
        pyxel.line(ax, ay - size, ax, ay - 4, color)
        pyxel.line(ax, ay + size, ax, ay + 4, color)
        pyxel.circb(ax, ay, 3, color)

        pyxel.tri(PENALTY_X, PENALTY_Y + 10, ax, ay, PENALTY_X + 5, PENALTY_Y + 5, color)

    def _draw_hud(self) -> None:
        # Top bar background
        pyxel.rect(0, 0, SCREEN_W, 30, BLACK)

        # Score
        score_text = f"SCORE: {self.score}"
        pyxel.text(6, 6, score_text, WHITE)

        # Combo
        if self.combo >= 2:
            combo_text = f"COMBO x{self.combo}"
            combo_color = YELLOW if self.combo >= SUPER_COMBO_THRESHOLD else CYAN
            pyxel.text(106, 6, combo_text, combo_color)

        # Round
        round_text = f"R{self.round}/{self.rounds_total}"
        pyxel.text(206, 6, round_text, WHITE)

        # Color indicator
        color_name = BALL_COLOR_NAMES.get(self.ball_color, "???")
        pyxel.text(6, 18, f"BALL: {color_name}", self.ball_color)

        if self.is_super and self.phase in (Phase.SHOT_ANIM, Phase.RESULT):
            pass

        # HEAT bar
        heat_label = "HEAT"
        heat_bar_x = 266
        heat_bar_w = 48
        pyxel.text(heat_bar_x, 18, heat_label, RED)
        pyxel.rect(heat_bar_x, 26, heat_bar_w, 3, GRAY)
        fill_w = int(heat_bar_w * self.heat / MAX_HEAT)
        heat_fill_color = YELLOW if self.heat >= 8 else ORANGE if self.heat >= 5 else RED
        pyxel.rect(heat_bar_x, 26, fill_w, 3, heat_fill_color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 20.0
            c = p.color if alpha > 0.2 else GRAY
            s = p.size
            pyxel.rect(int(p.x) - s // 2, int(p.y) - s // 2, s, s, c)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 40.0
            c = ft.color if alpha > 0.3 else GRAY
            tx = int(ft.x)
            ty = int(ft.y)
            strlen = len(ft.text)
            pyxel.text(tx - strlen * 2, ty, ft.text, c)

    # ------------------------------------------------------------------
    # Screen draws
    # ------------------------------------------------------------------

    def _draw_title(self) -> None:
        pyxel.cls(DARK_BLUE)

        pyxel.text(100, 30, "CHAIN KICK", YELLOW)
        pyxel.text(85, 48, "Soccer Penalty COMBO", WHITE)

        # Ball color legend
        pyxel.text(60, 72, "Ball Colors:", GRAY)
        for i, (color, name) in enumerate(BALL_COLOR_NAMES.items()):
            x = 70 + i * 52
            pyxel.circ(x, 88, 5, color)
            pyxel.text(x - 10, 96, name, color)

        lines = [
            "Same-color goals build COMBO!",
            "COMBO x3+ = SUPER KICK (unstoppable!)",
            "",
            "Mouse: Aim  |  Click: Shoot",
            "R / SPACE: Restart",
        ]
        for i, line in enumerate(lines):
            if line:
                x = (SCREEN_W - len(line) * 4) // 2
                col = CYAN if i <= 1 else GRAY
                pyxel.text(max(0, x), 110 + i * 14, line, col)

        pyxel.text(50, 190, f"{self.rounds_total} rounds  |  Watch HEAT gauge!", ORANGE)

        if (self.title_flash // 20) % 2 == 0:
            pyxel.text(95, 215, "Click / SPACE to Start", WHITE)

    def _draw_playing(self) -> None:
        self._draw_field()
        self._draw_goalkeeper()
        self._draw_ball()
        self._draw_aim_reticle()
        self._draw_hud()
        self._draw_particles()
        self._draw_floating_texts()

    def _draw_result(self) -> None:
        self._draw_field()
        self._draw_goalkeeper()
        self._draw_ball()
        self._draw_hud()
        self._draw_particles()
        self._draw_floating_texts()

        if self.last_result == "SUPER":
            res_text = "SUPER KICK!!"
            res_color = YELLOW
        elif self.last_result == "GOAL":
            res_text = "GOAL!"
            res_color = GREEN
        elif self.last_result == "SAVE":
            res_text = "SAVED!"
            res_color = RED
        else:
            res_text = "MISS!"
            res_color = GRAY

        tx = GOAL_CENTER_X - len(res_text) * 2
        pyxel.text(tx, 10, res_text, res_color)

    def _draw_game_over(self) -> None:
        pyxel.cls(DARK_BLUE)

        pyxel.text(110, 30, "GAME OVER", RED)

        cause = "HEAT maxed out!" if self.heat >= MAX_HEAT else "All rounds played!"
        pyxel.text((SCREEN_W - len(cause) * 4) // 2, 52, cause, GRAY)

        score_text = f"Final Score: {self.score}"
        pyxel.text((SCREEN_W - len(score_text) * 4) // 2, 75, score_text, YELLOW)

        combo_text = f"Max COMBO: x{self.max_combo}"
        pyxel.text((SCREEN_W - len(combo_text) * 4) // 2, 95, combo_text, CYAN)

        heat_text = f"Final HEAT: {self.heat}/{MAX_HEAT}"
        pyxel.text((SCREEN_W - len(heat_text) * 4) // 2, 115, heat_text, ORANGE)

        pyxel.text((SCREEN_W - len("Click / SPACE / R to Retry") * 4) // 2, 155, "Click / SPACE / R to Retry", WHITE)

        self._draw_particles()
        self._draw_floating_texts()


# ---------------------------------------------------------------------------
# App wrapper
# ---------------------------------------------------------------------------


class App:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="CHAIN KICK", display_scale=2)
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
