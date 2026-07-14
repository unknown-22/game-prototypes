"""HORSESHOE CHAIN -- Color-match horseshoe tossing game prototype."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto

import pyxel

# --- Constants ---
WIDTH = 320
HEIGHT = 240
FPS = 60

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

COLORS = (RED, LIME, DARK_BLUE, YELLOW)
RAINBOW_COLORS = (RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK)

STAKE_Y = 190
STAKE_X_POSITIONS = (50, 110, 170, 230)
PLAYER_X = 160
PLAYER_Y = 220
STAKE_RADIUS = 10
RINGER_DEPTH = 15

MAX_POWER = 12.0
GRAVITY = 0.3
GROUND_Y = 230

GAME_DURATION = 60 * FPS
SUPER_DURATION = 300
COMBO_THRESHOLD = 4
MAX_HEAT = 100.0
HEAT_MISS = 10.0
HEAT_MISMATCH = 15.0
HEAT_DECAY = 0.02

SHUFFLE_INTERVAL = 15 * FPS
DESPERATION_THRESHOLD = 10 * FPS

SCORING_DURATION = 30

MAX_GHOST_POINTS = 60


class Phase(Enum):
    TITLE = auto()
    AIMING = auto()
    FLYING = auto()
    SCORING = auto()
    GAME_OVER = auto()


@dataclass
class Stake:
    x: float
    y: float
    color: int
    radius: int = STAKE_RADIUS


@dataclass
class Horseshoe:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    color: int = WHITE
    active: bool = True
    scored: bool = False
    trail: list[tuple[float, float]] = field(default_factory=list)


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


class Game:
    phase: Phase
    score: int
    combo: int
    max_combo: int
    best_combo: int
    heat: float
    timer: int
    super_timer: int
    scoring_timer: int
    stake_shuffle_timer: int
    aim_start_x: float
    aim_start_y: float
    dragging: bool
    shake_frames: int
    shake_intensity: int
    horseshoe: Horseshoe | None
    stakes: list[Stake]
    particles: list[Particle]
    floating_texts: list[FloatingText]
    ghost_trail: list[tuple[float, float]]
    best_score: int
    rng: random.Random

    def __init__(self) -> None:
        self.rng = random.Random()
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.best_combo = 0
        self.heat = 0.0
        self.timer = GAME_DURATION
        self.super_timer = 0
        self.scoring_timer = 0
        self.stake_shuffle_timer = 0
        self.aim_start_x = 0.0
        self.aim_start_y = 0.0
        self.dragging = False
        self.shake_frames = 0
        self.shake_intensity = 0
        self.horseshoe = None
        self.stakes = []
        self.particles = []
        self.floating_texts = []
        self.ghost_trail = []
        self.best_score = 0

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.best_combo = 0
        self.heat = 0.0
        self.timer = GAME_DURATION
        self.super_timer = 0
        self.scoring_timer = 0
        self.stake_shuffle_timer = 0
        self.aim_start_x = 0.0
        self.aim_start_y = 0.0
        self.dragging = False
        self.shake_frames = 0
        self.shake_intensity = 0
        self.horseshoe = None
        self.stakes = []
        self.particles = []
        self.floating_texts = []
        self.ghost_trail = []
        self.best_score = 0

    def _start_game(self) -> None:
        self.phase = Phase.AIMING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = GAME_DURATION
        self.super_timer = 0
        self.scoring_timer = 0
        self.stake_shuffle_timer = 0
        self.aim_start_x = 0.0
        self.aim_start_y = 0.0
        self.dragging = False
        self.shake_frames = 0
        self.shake_intensity = 0
        self.horseshoe = None
        self.stakes = []
        self.particles = []
        self.floating_texts = []
        self.ghost_trail = []
        self._spawn_stakes()

    def _spawn_stakes(self) -> None:
        self.stakes = []
        color_pool = list(COLORS)
        self.rng.shuffle(color_pool)
        for i, xpos in enumerate(STAKE_X_POSITIONS):
            self.stakes.append(Stake(x=float(xpos), y=STAKE_Y, color=color_pool[i]))

    def _shuffle_stakes(self) -> None:
        colors = [s.color for s in self.stakes]
        self.rng.shuffle(colors)
        for s, c in zip(self.stakes, colors):
            s.color = c

    # --- Throw ---

    def _throw(self, power_x: float, power_y: float) -> None:
        dist = math.hypot(power_x, power_y)
        if dist < 1.0:
            return
        speed = min(dist / 8.0, MAX_POWER)
        if speed < 0.5:
            return
        nx = power_x / dist
        ny = power_y / dist
        self.horseshoe = Horseshoe(
            x=PLAYER_X,
            y=PLAYER_Y,
            vx=nx * speed,
            vy=ny * speed,
            color=COLORS[self.rng.randint(0, 3)],
        )
        self.phase = Phase.FLYING

    # --- Physics ---

    def _update_flying(self) -> None:
        if self.horseshoe is None or not self.horseshoe.active:
            return
        shoe = self.horseshoe
        shoe.trail.append((shoe.x, shoe.y))
        shoe.x += shoe.vx
        shoe.y += shoe.vy
        shoe.vy += GRAVITY

        # Ground bounce
        if shoe.y >= GROUND_Y:
            if abs(shoe.vy) > 2:
                shoe.y = GROUND_Y
                shoe.vy *= -0.4
            else:
                shoe.y = GROUND_Y
                shoe.vy = 0.0
                shoe.vx = 0.0

        # Off-screen
        if shoe.y > HEIGHT or shoe.x < -20 or shoe.x > WIDTH + 20:
            shoe.active = False
            self._on_miss()

        # Out of bounds after bounce stop
        if shoe.y >= GROUND_Y and abs(shoe.vy) < 0.01 and abs(shoe.vx) < 0.01:
            shoe.active = False
            self._on_miss()

    def _check_ringer(self) -> Stake | None:
        if self.horseshoe is None or not self.horseshoe.active:
            return None
        shoe = self.horseshoe
        if shoe.scored:
            return None
        for s in self.stakes:
            dist = math.hypot(shoe.x - s.x, shoe.y - s.y)
            if dist <= s.radius and abs(shoe.y - s.y) <= RINGER_DEPTH:
                return s
        return None

    def _handle_ringer(self, stake: Stake) -> None:
        if self.horseshoe is None:
            return
        shoe = self.horseshoe
        shoe.scored = True
        shoe.active = False

        is_super = self.super_timer > 0
        is_match = shoe.color == stake.color or is_super

        if is_match:
            self.combo += 1
            mult = 3.0 if is_super else 1.0
            gained = int(10 * self.combo * mult)
            self.score += gained
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            if self.combo >= COMBO_THRESHOLD and self.super_timer <= 0:
                self._activate_super()

            pcolor = (
                RAINBOW_COLORS[self.combo % len(RAINBOW_COLORS)]
                if is_super
                else stake.color
            )
            pcount = 20 if is_super else 8
            self._spawn_particles(stake.x, stake.y, pcolor, pcount)
            self.floating_texts.append(
                FloatingText(stake.x, stake.y - 5, f"+{gained}", pcolor, 30)
            )
            if self.combo > 1:
                self.floating_texts.append(
                    FloatingText(
                        stake.x,
                        stake.y - 15,
                        f"COMBO x{self.combo}",
                        YELLOW,
                        30,
                    )
                )
            # Save ghost trail for best throw
            if self.combo > 0 and self.horseshoe and self.horseshoe.trail:
                self._save_ghost_trail()
        else:
            self.combo = 0
            self.heat = min(MAX_HEAT, self.heat + HEAT_MISMATCH)
            self._spawn_particles(stake.x, stake.y, GRAY, 5)
            self.floating_texts.append(
                FloatingText(stake.x, stake.y - 5, "WRONG", ORANGE, 30)
            )

        self.scoring_timer = SCORING_DURATION
        self.phase = Phase.SCORING

    def _on_miss(self) -> None:
        shoe = self.horseshoe
        if shoe is not None and shoe.trail:
            mx = shoe.x
            my = shoe.y
        else:
            mx = PLAYER_X
            my = GROUND_Y
        self.combo = 0
        self.heat = min(MAX_HEAT, self.heat + HEAT_MISS)
        self.floating_texts.append(FloatingText(mx, my, "MISS", GRAY, 30))
        self._spawn_particles(mx, my, GRAY, 3)
        self.scoring_timer = SCORING_DURATION
        self.phase = Phase.SCORING

    # --- Super ---

    def _activate_super(self) -> None:
        self.super_timer = SUPER_DURATION
        self.shake_frames = 10
        self.shake_intensity = 4
        self._spawn_particles(PLAYER_X, PLAYER_Y, YELLOW, 20)
        self.floating_texts.append(
            FloatingText(PLAYER_X, PLAYER_Y - 20, "SUPER!", YELLOW, 60)
        )

    def _deactivate_super(self) -> None:
        self.super_timer = 0
        self.combo = 0

    # --- Ghost trail ---

    def _save_ghost_trail(self) -> None:
        if self.horseshoe is None or not self.horseshoe.trail:
            return
        trail = list(self.horseshoe.trail)
        if len(trail) > MAX_GHOST_POINTS:
            step = len(trail) / MAX_GHOST_POINTS
            trail = [trail[int(i * step)] for i in range(MAX_GHOST_POINTS)]
        self.ghost_trail = trail

    # --- Particles ---

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.pi * 2)
            speed = self.rng.uniform(0.5, 2.0)
            life = self.rng.randint(10, 25)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    color=color,
                    life=life,
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles[:] = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.8
            ft.life -= 1
        self.floating_texts[:] = [ft for ft in self.floating_texts if ft.life > 0]

    # --- Timer ---

    def _update_timer(self) -> None:
        if self.timer > 0:
            self.timer -= 1
        if self.timer <= 0:
            if self.super_timer > 0:
                self.super_timer = 1  # will end naturally
            else:
                self._end_game()

        self.stake_shuffle_timer += 1
        if self.stake_shuffle_timer >= SHUFFLE_INTERVAL:
            self.stake_shuffle_timer = 0
            if self.horseshoe is None or not self.horseshoe.active:
                self._shuffle_stakes()

    def _end_game(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.combo > self.best_combo:
            self.best_combo = self.combo
        if self.score > self.best_score:
            self.best_score = self.score

    # --- Main loop ---

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE):
                self._start_game()

        elif self.phase == Phase.AIMING:
            self._update_timer()
            self._update_particles()
            self._update_floating_texts()

            if self.super_timer > 0:
                self.super_timer -= 1
                if self.super_timer <= 0:
                    self._deactivate_super()

            desperation = self.timer < DESPERATION_THRESHOLD
            if not desperation:
                self.heat = max(0.0, self.heat - HEAT_DECAY)

            if self.heat >= MAX_HEAT:
                self._end_game()
                return

            if self.shake_frames > 0:
                self.shake_frames -= 1
                if self.shake_frames == 0:
                    self.shake_intensity = 0

            mx = pyxel.mouse_x
            my = pyxel.mouse_y

            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.dragging = True
                self.aim_start_x = float(mx)
                self.aim_start_y = float(my)

            if self.dragging:
                if pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT):
                    self.dragging = False
                    dx = mx - self.aim_start_x
                    dy = my - self.aim_start_y
                    self._throw(dx, dy)

        elif self.phase == Phase.FLYING:
            self._update_timer()
            self._update_flying()
            self._update_particles()
            self._update_floating_texts()

            if self.super_timer > 0:
                self.super_timer -= 1
                if self.super_timer <= 0:
                    self._deactivate_super()

            stake = self._check_ringer()
            if stake is not None:
                self._handle_ringer(stake)

        elif self.phase == Phase.SCORING:
            self._update_timer()
            self._update_particles()
            self._update_floating_texts()

            if self.super_timer > 0:
                self.super_timer -= 1
                if self.super_timer <= 0:
                    self._deactivate_super()

            self.scoring_timer -= 1
            if self.scoring_timer <= 0:
                self.horseshoe = None
                self.phase = Phase.AIMING

        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE):
                self._start_game()

    def draw(self) -> None:
        pyxel.cls(NAVY)
        self._draw_background()

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.AIMING, Phase.FLYING, Phase.SCORING):
            self._draw_stakes()
            self._draw_horseshoe()
            self._draw_particles()
            self._draw_floating_texts()
            self._draw_aim_indicator()
            self._draw_hud()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

        # Screen shake via camera
        if self.shake_frames > 0:
            sx = self.rng.randint(-self.shake_intensity, self.shake_intensity)
            sy = self.rng.randint(-self.shake_intensity, self.shake_intensity)
            pyxel.camera(sx, sy)
        else:
            pyxel.camera(0, 0)

        # Super rainbow border
        if self.super_timer > 0:
            border_color = RAINBOW_COLORS[
                (pyxel.frame_count // 3) % len(RAINBOW_COLORS)
            ]
            pyxel.rectb(0, 0, WIDTH, HEIGHT, border_color)

    def _draw_background(self) -> None:
        pyxel.rect(0, 100, WIDTH, HEIGHT - 100, GREEN)

        # Ground line
        for x in range(0, WIDTH, 6):
            pyxel.pset(x, GROUND_Y, BROWN)

    def _draw_title(self) -> None:
        pyxel.text(70, 60, "HORSESHOE CHAIN", WHITE)
        pyxel.text(108, 85, "Click to Start", WHITE)
        pyxel.text(55, 115, "Click & drag to aim / throw", WHITE)
        pyxel.text(48, 130, "Same-color ringer = COMBO chain", WHITE)
        pyxel.text(78, 148, "Combo x4 = SUPER TOSS! (3x)", YELLOW)
        pyxel.text(85, 166, "Heat >= 100 = Game Over", ORANGE)

        # Draw example stakes
        for i in range(4):
            color = COLORS[i]
            x = 50 + i * 60
            self._draw_stake_at(float(x), 210.0, color)

    def _draw_stake_at(self, x: float, y: float, color: int) -> None:
        post_w = 3
        post_h = 12
        pyxel.rect(int(x - post_w), int(y - post_h), post_w * 2, post_h, BROWN)
        pyxel.circ(int(x), int(y - post_h), 4, color)
        pyxel.circb(int(x), int(y - post_h), 4, color)

    def _draw_stakes(self) -> None:
        for s in self.stakes:
            if self.super_timer > 0:
                scolor = RAINBOW_COLORS[
                    (pyxel.frame_count // 4) % len(RAINBOW_COLORS)
                ]
            else:
                scolor = s.color
                # Flash in desperation
                if self.timer < DESPERATION_THRESHOLD and (pyxel.frame_count // 15) % 2 == 0:
                    scolor = WHITE
            self._draw_stake_at(s.x, s.y, scolor)

    def _draw_horseshoe(self) -> None:
        shoe = self.horseshoe
        if shoe is None or not shoe.active:
            return

        scolor = shoe.color
        if self.super_timer > 0:
            scolor = RAINBOW_COLORS[
                (pyxel.frame_count // 3) % len(RAINBOW_COLORS)
            ]

        # Draw as U-shape (horseshoe)
        r = 5
        pyxel.circb(int(shoe.x), int(shoe.y - r), r, scolor)
        pyxel.circ(int(shoe.x - r), int(shoe.y), r, scolor)
        pyxel.circ(int(shoe.x + r), int(shoe.y), r, scolor)
        pyxel.rect(int(shoe.x - r), int(shoe.y - r), r * 2, r, BLACK)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pcolor = p.color if p.life > 5 else GRAY
            pyxel.pset(int(p.x), int(p.y), pcolor)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 30.0
            if alpha > 1.0:
                alpha = 1.0
            tcolor = ft.color if alpha > 0.5 else GRAY
            pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, tcolor)

    def _draw_aim_indicator(self) -> None:
        # Ghost trail
        for gx, gy in self.ghost_trail:
            pyxel.pset(int(gx), int(gy), GRAY)

        # Player position
        pcolor = WHITE
        if self.super_timer > 0:
            pcolor = RAINBOW_COLORS[
                (pyxel.frame_count // 3) % len(RAINBOW_COLORS)
            ]
        pyxel.circ(PLAYER_X, PLAYER_Y, 5, pcolor)
        pyxel.circb(PLAYER_X, PLAYER_Y, 5, pcolor)

        if self.phase == Phase.AIMING and self.dragging:
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            dx = mx - PLAYER_X
            dy = my - PLAYER_Y

            # Dotted aim line from player to cursor
            dist = math.hypot(dx, dy)
            if dist > 2:
                steps = min(20, int(dist / 4))
                for i in range(steps):
                    t = (i + 1) / steps
                    px = PLAYER_X + dx * t
                    py = PLAYER_Y + dy * t
                    if i % 2 == 0:
                        pyxel.pset(int(px), int(py), WHITE)

            # Power indicator ring
            power = math.hypot(mx - self.aim_start_x, my - self.aim_start_y)
            power_radius = min(15, int(power / 5))
            pyxel.circb(PLAYER_X, PLAYER_Y, power_radius, YELLOW)

    def _draw_hud(self) -> None:
        # Heat bar (left side)
        bar_w = 6
        bar_h = 80
        bar_x = 4
        bar_y = 4
        fill = int(bar_h * self.heat / MAX_HEAT)
        bar_color = GREEN if self.heat < 40 else (ORANGE if self.heat < 70 else RED)
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        pyxel.rect(bar_x, bar_y + bar_h - fill, bar_w, fill, bar_color)
        pyxel.text(bar_x, bar_y + bar_h + 2, "HEAT", WHITE)

        # Timer (top-center)
        sec = (self.timer + FPS - 1) // FPS
        tcolor = WHITE if sec > 10 else RED
        tstr = f"TIME:{sec:02d}"
        pyxel.text(WIDTH // 2 - len(tstr) * 2, 3, tstr, tcolor)

        # Score (top-right)
        pyxel.text(WIDTH - 85, 3, f"SCORE:{self.score}", WHITE)

        # Combo
        ccolor = YELLOW
        if self.combo >= COMBO_THRESHOLD or self.super_timer > 0:
            ccolor = RAINBOW_COLORS[
                (pyxel.frame_count // 3) % len(RAINBOW_COLORS)
            ]
        pyxel.text(WIDTH - 85, 13, f"COMBO:{self.combo}", ccolor)

        # Super timer
        if self.super_timer > 0:
            stext = f"SUPER! {self.super_timer // FPS}s"
            pyxel.text(WIDTH // 2 - len(stext) * 2, 16, stext, YELLOW)

    def _draw_game_over(self) -> None:
        pyxel.text(112, 60, "GAME OVER", RED)
        pyxel.text(110, 85, f"Score: {self.score}", WHITE)
        pyxel.text(100, 100, f"Max Combo: {self.max_combo}", YELLOW)
        pyxel.text(95, 115, f"Best Combo: {self.best_combo}", WHITE)
        pyxel.text(95, 130, f"Best Score: {self.best_score}", WHITE)
        pyxel.text(100, 155, "Click to Retry", WHITE)


def main() -> None:
    pyxel.init(WIDTH, HEIGHT, title="HORSESHOE CHAIN")
    game = Game()
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
