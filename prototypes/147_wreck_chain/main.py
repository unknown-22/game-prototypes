"""WRECK CHAIN - Side-view demolition with wrecking ball pendulum physics."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# --- Screen ---
SCREEN_W = 320
SCREEN_H = 240
GROUND_Y = 180

# --- Building Grid ---
COLS = 8
ROWS = 7
BLOCK_W = 36
BLOCK_H = 20
BUILDING_X = 180
BUILDING_Y = 40

# --- Crane / Ball ---
ANCHOR_Y = 20
CHAIN_LENGTH = 120
BALL_RADIUS = 6
ANCHOR_MIN_X = 60
ANCHOR_MAX_X = 280
RELEASE_SPEED = 8.0

# --- Physics ---
PEND_GRAVITY = 0.4
PEND_DAMPING = 0.995
MAX_ANGULAR_VEL = 15.0
DEBRIS_GRAVITY = 0.2

# --- Timer / Game State ---
TIMER_MAX = 3600
SUPER_DURATION = 300
HEAT_MAX = 100.0
HEAT_DECAY = 0.05
HEAT_PENALTY = 20.0

# --- Scoring ---
BASE_SCORE = 100
CHAIN_BONUS = 50
WRONG_COLOR_SCORE = 10
SUPER_MULTIPLIER = 3.0
VICTORY_BONUS = 500

# --- Effects ---
SHAKE_DURATION = 10
TRAIL_LENGTH = 5

# --- Colors (pyxel palette) ---
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

BLOCK_COLORS = {0: RED, 1: GREEN, 2: LIGHT_BLUE, 3: YELLOW}
NUM_COLORS = 4
RAINBOW_COLORS = [RED, ORANGE, YELLOW, LIME, CYAN, LIGHT_BLUE, PURPLE, PINK]


@dataclass
class Block:
    col: int
    row: int
    color: int  # 0-3


@dataclass
class Debris:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


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


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    SWINGING = auto()
    GAME_OVER = auto()
    VICTORY = auto()


def _combo_multiplier(combo: int) -> float:
    if combo <= 1:
        return 1.0
    elif combo == 2:
        return 1.5
    elif combo == 3:
        return 2.0
    else:
        return 3.0


class Game:
    def __init__(self) -> None:
        self._init_state()

    def _init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.anchor_x: float = 160.0
        self.ball_x: float = 160.0
        self.ball_y: float = ANCHOR_Y + CHAIN_LENGTH
        self.ball_vx: float = 0.0
        self.ball_vy: float = 0.0
        self.ball_angle: float = 0.0
        self.ball_angular_vel: float = 0.0
        self.swing_active: bool = False
        self._trail: list[tuple[float, float]] = []
        self.grid: list[list[Block | None]] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.last_color: int | None = None
        self.heat: float = 0.0
        self.timer: int = TIMER_MAX
        self.super_timer: int = 0
        self.shake_frames: int = 0
        self.debris: list[Debris] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.mouse_pressed: bool = False
        self.rng: random.Random = random.Random()
        self._hit_this_swing: set[tuple[int, int]] = set()
        self._frame: int = 0

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.anchor_x = 160.0
        self.ball_angle = 0.0
        self.ball_angular_vel = 0.0
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.swing_active = False
        self._update_ball_position()
        self._trail = [(self.ball_x, self.ball_y)] * TRAIL_LENGTH
        self.grid = self._init_grid()
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.last_color = None
        self.heat = 0.0
        self.timer = TIMER_MAX
        self.super_timer = 0
        self.shake_frames = 0
        self.debris = []
        self.particles = []
        self.floating_texts = []
        self.mouse_pressed = False
        self._hit_this_swing = set()
        self._frame = 0

    def _init_grid(self) -> list[list[Block | None]]:
        grid: list[list[Block | None]] = []
        for col in range(COLS):
            column: list[Block | None] = []
            for row in range(ROWS):
                column.append(Block(col, row, self.rng.randint(0, NUM_COLORS - 1)))
            grid.append(column)
        return grid

    def _update_ball_position(self) -> None:
        self.ball_x = self.anchor_x + CHAIN_LENGTH * math.sin(self.ball_angle)
        self.ball_y = ANCHOR_Y + CHAIN_LENGTH * math.cos(self.ball_angle)

    def _update_ball_physics(self) -> None:
        self.ball_angular_vel += PEND_GRAVITY * math.sin(self.ball_angle)
        self.ball_angular_vel *= PEND_DAMPING
        if self.ball_angular_vel > MAX_ANGULAR_VEL:
            self.ball_angular_vel = MAX_ANGULAR_VEL
        elif self.ball_angular_vel < -MAX_ANGULAR_VEL:
            self.ball_angular_vel = -MAX_ANGULAR_VEL
        self.ball_angle += self.ball_angular_vel
        self._update_ball_position()

    def _release_ball(self) -> None:
        if self.ball_angle < 0:
            self.ball_angular_vel = RELEASE_SPEED
        else:
            self.ball_angular_vel = -RELEASE_SPEED
        self.swing_active = True
        self.phase = Phase.SWINGING
        self._hit_this_swing = set()

    def _check_block_collision(self) -> list[tuple[int, int]]:
        collisions: list[tuple[int, int]] = []
        for col in range(COLS):
            for row in range(ROWS):
                if self.grid[col][row] is None:
                    continue
                if (col, row) in self._hit_this_swing:
                    continue
                bx = BUILDING_X + col * BLOCK_W
                by = BUILDING_Y + row * BLOCK_H
                nearest_x = max(bx, min(self.ball_x, bx + BLOCK_W))
                nearest_y = max(by, min(self.ball_y, by + BLOCK_H))
                dx = self.ball_x - nearest_x
                dy = self.ball_y - nearest_y
                if dx * dx + dy * dy < BALL_RADIUS * BALL_RADIUS:
                    collisions.append((col, row))
        return collisions

    def _destroy_block(self, col: int, row: int) -> int:
        block = self.grid[col][row]
        if block is None:
            return 0
        color = block.color
        self.grid[col][row] = None
        cx = BUILDING_X + col * BLOCK_W + BLOCK_W // 2
        cy = BUILDING_Y + row * BLOCK_H + BLOCK_H // 2
        self._spawn_debris(cx, cy, BLOCK_COLORS.get(color, WHITE), 8)
        return BASE_SCORE

    def _resolve_collisions(self, collisions: list[tuple[int, int]]) -> int:
        total_points = 0
        for col, row in collisions:
            block = self.grid[col][row]
            if block is None:
                continue
            color = block.color
            points = self._destroy_block(col, row)
            self._hit_this_swing.add((col, row))
            bx = BUILDING_X + col * BLOCK_W + BLOCK_W // 2
            by = BUILDING_Y + row * BLOCK_H

            if self.last_color is None:
                self.combo = 1
                mult = _combo_multiplier(self.combo)
                if self.super_timer > 0:
                    mult *= SUPER_MULTIPLIER
                total_points += int(points * mult)
                self.last_color = color
            elif self.super_timer > 0:
                self.combo += 1
                mult = _combo_multiplier(self.combo) * SUPER_MULTIPLIER
                total_points += int(points * mult)
                self.last_color = color
            elif color == self.last_color:
                self.combo += 1
                mult = _combo_multiplier(self.combo)
                total_points += int(points * mult)
            else:
                self.combo = 0
                self.heat += HEAT_PENALTY
                self.last_color = color
                total_points += WRONG_COLOR_SCORE
                if self.shake_frames < 3:
                    self.shake_frames = 3

            if self.combo > self.max_combo:
                self.max_combo = self.combo

            if self.combo >= 2:
                self._add_floating_text(bx, by, f"x{_combo_multiplier(self.combo)}", YELLOW)
            if self.combo >= 3:
                self._spawn_particles(bx, by, BLOCK_COLORS.get(color, WHITE), 6)

            if self.combo >= 4 and self.super_timer <= 0:
                self.super_timer = SUPER_DURATION
                self.shake_frames = SHAKE_DURATION
                self._add_floating_text(SCREEN_W // 2, SCREEN_H // 2 - 20, "SUPER BALL!", RAINBOW_COLORS[0])

        return total_points

    def _apply_gravity(self) -> list[tuple[int, int]]:
        moved: list[tuple[int, int]] = []
        for col in range(COLS):
            for row in range(ROWS - 2, -1, -1):
                block = self.grid[col][row]
                if block is None:
                    continue
                fall_row = row
                while fall_row + 1 < ROWS and self.grid[col][fall_row + 1] is None:
                    fall_row += 1
                if fall_row != row:
                    block.row = fall_row
                    self.grid[col][fall_row] = block
                    self.grid[col][row] = None
                    moved.append((col, fall_row))
        return moved

    def _update_heat(self) -> bool:
        if self.heat >= HEAT_MAX:
            return True
        if self.heat > 0:
            self.heat = max(0.0, self.heat - HEAT_DECAY)
        return False

    def _check_victory(self) -> bool:
        for col in range(COLS):
            for row in range(ROWS):
                if self.grid[col][row] is not None:
                    return False
        return True

    def _spawn_debris(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, 2 * math.pi)
            speed = self.rng.uniform(30, 80) / 60.0
            vx = math.cos(angle) * speed * 60.0
            vy = math.sin(angle) * speed * 60.0 - 1.5
            life = self.rng.randint(30, 45)
            self.debris.append(Debris(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, 2 * math.pi)
            speed = self.rng.uniform(50, 120) / 60.0
            vx = math.cos(angle) * speed * 60.0
            vy = math.sin(angle) * speed * 60.0 - 2.0
            life = self.rng.randint(15, 25)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=30, color=color))

    def _update_debris(self) -> None:
        surviving: list[Debris] = []
        for d in self.debris:
            d.x += d.vx
            d.y += d.vy
            d.vy += DEBRIS_GRAVITY
            d.life -= 1
            if d.life > 0:
                surviving.append(d)
        self.debris = surviving

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
        self.floating_texts = surviving

    def update(self) -> None:
        self._frame += 1

        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.phase = Phase.PLAYING
                self.timer = TIMER_MAX
                self.grid = self._init_grid()
                self.score = 0
                self.combo = 0
                self.max_combo = 0
                self.last_color = None
                self.heat = 0.0
                self.super_timer = 0
                self.swing_active = False
                self._trail = [(self.ball_x, self.ball_y)] * TRAIL_LENGTH
                self.debris = []
                self.particles = []
                self.floating_texts = []
                self.shake_frames = 0
                self._hit_this_swing = set()
                self.ball_angle = 0.0
                self.ball_angular_vel = 0.0
                self._update_ball_position()
            return

        if self.phase in (Phase.GAME_OVER, Phase.VICTORY):
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()
            return

        # Decay state
        if self.shake_frames > 0:
            self.shake_frames -= 1

        if self.phase == Phase.PLAYING:
            # Idle pendulum swing
            idle_angle = 0.03 * math.sin(self._frame * 0.04)
            self.ball_angle = idle_angle
            self._update_ball_position()
            self.ball_angular_vel = 0.0
            self._trail = [(self.ball_x, self.ball_y)] * TRAIL_LENGTH

            # Timer
            if self.timer > 0:
                self.timer -= 1
            if self.timer <= 0:
                self.phase = Phase.GAME_OVER
                return

            # Heat decay
            if self._update_heat():
                self.phase = Phase.GAME_OVER
                return

            # Super timer
            if self.super_timer > 0:
                self.super_timer -= 1

            # Update anchor from mouse
            self.anchor_x = float(max(ANCHOR_MIN_X, min(ANCHOR_MAX_X, pyxel.mouse_x)))

            # Mouse click → release
            if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
                self.mouse_pressed = True
            else:
                if self.mouse_pressed:
                    self.mouse_pressed = False
                    self._release_ball()

        elif self.phase == Phase.SWINGING:
            # Timer
            if self.timer > 0:
                self.timer -= 1
            if self.timer <= 0:
                self.phase = Phase.GAME_OVER
                return

            # Heat decay
            if self._update_heat():
                self.phase = Phase.GAME_OVER
                return

            # Super timer
            if self.super_timer > 0:
                self.super_timer -= 1

            # Update anchor from mouse (player can still reposition during swing)
            self.anchor_x = float(max(ANCHOR_MIN_X, min(ANCHOR_MAX_X, pyxel.mouse_x)))

            # Physics step (4 sub-steps for better collision detection)
            for _ in range(4):
                self._update_ball_physics()

                collisions = self._check_block_collision()
                if collisions:
                    total = self._resolve_collisions(collisions)
                    self.score += total

                    moved = self._apply_gravity()
                    chain_bonus_total = len(moved) * CHAIN_BONUS
                    if chain_bonus_total > 0:
                        self.score += chain_bonus_total
                        if len(moved) >= 3:
                            cx = BUILDING_X + moved[0][0] * BLOCK_W + BLOCK_W // 2
                            cy = BUILDING_Y + moved[0][1] * BLOCK_H
                            self._add_floating_text(cx, cy, f"CHAIN +{chain_bonus_total}", ORANGE)

                    if self._check_victory():
                        self.score += VICTORY_BONUS
                        self.phase = Phase.VICTORY
                        self.shake_frames = SHAKE_DURATION
                        break

                # Check settled
                if (
                    abs(self.ball_angular_vel) < 0.1
                    and abs(self.ball_angle) < 0.05
                    and self._frame > 1
                ):
                    self.ball_angle = 0.0
                    self.ball_angular_vel = 0.0
                    self._update_ball_position()
                    self.swing_active = False
                    self._trail = [(self.ball_x, self.ball_y)] * TRAIL_LENGTH
                    self.phase = Phase.PLAYING
                    self._hit_this_swing = set()
                    break

            # Trail
            self._trail.append((self.ball_x, self.ball_y))
            if len(self._trail) > TRAIL_LENGTH:
                self._trail.pop(0)

        # Update effects
        self._update_debris()
        self._update_particles()
        self._update_floating_texts()

    def draw(self) -> None:
        if self.shake_frames > 0:
            pyxel.camera(self.rng.randint(-3, 3), self.rng.randint(-3, 3))
        else:
            pyxel.camera(0, 0)

        pyxel.cls(DARK_BLUE)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.PLAYING, Phase.SWINGING):
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        elif self.phase == Phase.VICTORY:
            self._draw_victory()

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 - 20, "WRECK CHAIN", WHITE)
        pyxel.text(SCREEN_W // 2 - 35, SCREEN_H // 2 + 5, "SPACE to start", GRAY)
        pyxel.text(SCREEN_W // 2 - 55, SCREEN_H // 2 + 25, "Mouse: aim  Click: swing", GRAY)

    def _draw_game_over(self) -> None:
        pyxel.text(SCREEN_W // 2 - 20, SCREEN_H // 2 - 25, "GAME OVER", RED)
        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2, f"Score: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 35, SCREEN_H // 2 + 12, f"Max Combo: {self.max_combo}", YELLOW)
        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 + 28, "R to restart", GRAY)

    def _draw_victory(self) -> None:
        pyxel.text(SCREEN_W // 2 - 45, SCREEN_H // 2 - 25, "BUILDING DEMOLISHED!", LIME)
        pyxel.text(SCREEN_W // 2 - 35, SCREEN_H // 2, f"Score: {self.score}", WHITE)
        pyxel.text(SCREEN_W // 2 - 35, SCREEN_H // 2 + 12, f"Max Combo: {self.max_combo}", YELLOW)
        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 + 28, "R to restart", GRAY)

    def _draw_game(self) -> None:
        # Ground
        pyxel.rect(0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y, GRAY)
        pyxel.line(0, GROUND_Y, SCREEN_W, GROUND_Y, BLACK)

        # Building
        self._draw_building()

        # Debris
        for d in self.debris:
            c = d.color if d.life >= 10 else GRAY
            pyxel.rect(int(d.x), int(d.y), 4, 4, c)

        # Particles
        for p in self.particles:
            pyxel.rect(int(p.x), int(p.y), 2, 2, p.color)

        # Ball trail
        for i, (tx, ty) in enumerate(self._trail):
            if i >= TRAIL_LENGTH - 1:
                continue
            alpha_colors = [NAVY, PURPLE, DARK_BLUE, NAVY]
            c = alpha_colors[i % len(alpha_colors)]
            pyxel.circ(int(tx), int(ty), BALL_RADIUS - 1, c)

        # Chain
        pyxel.line(
            int(self.anchor_x), ANCHOR_Y,
            int(self.ball_x), int(self.ball_y),
            WHITE,
        )

        # Anchor
        pyxel.circ(int(self.anchor_x), ANCHOR_Y, 3, GRAY)

        # Ball
        if self.super_timer > 0:
            ball_color = RAINBOW_COLORS[(pyxel.frame_count // 4) % len(RAINBOW_COLORS)]
        else:
            ball_color = GRAY
        pyxel.circ(int(self.ball_x), int(self.ball_y), BALL_RADIUS, ball_color)

        # Floating texts
        for ft in self.floating_texts:
            c = ft.color if ft.life >= 10 else GRAY
            pyxel.text(int(ft.x), int(ft.y), ft.text, c)

        # HUD
        self._draw_hud()

    def _draw_building(self) -> None:
        for col in range(COLS):
            for row in range(ROWS):
                block = self.grid[col][row]
                if block is None:
                    continue
                x = BUILDING_X + col * BLOCK_W
                y = BUILDING_Y + row * BLOCK_H
                color = BLOCK_COLORS.get(block.color, WHITE)
                pyxel.rect(x, y, BLOCK_W, BLOCK_H, color)
                pyxel.rectb(x, y, BLOCK_W, BLOCK_H, BLACK)
                # Highlight edges
                pyxel.line(x, y, x + BLOCK_W - 1, y, WHITE)
                pyxel.line(x, y, x, y + BLOCK_H - 1, WHITE)

    def _draw_hud(self) -> None:
        # Score
        pyxel.text(4, 2, f"Score: {self.score}", WHITE)

        # Combo
        if self.combo > 1:
            cm = YELLOW if self.combo % 2 != 0 else ORANGE
            pyxel.text(4, 10, f"Combo: x{_combo_multiplier(self.combo)}", cm)

        # HEAT bar
        bar_x = 110
        bar_y = 4
        bar_w = 80
        bar_h = 6
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        fill = int(self.heat / HEAT_MAX * bar_w)
        if fill > 0:
            if self.heat < 40:
                hc = GREEN
            elif self.heat < 70:
                hc = YELLOW
            else:
                hc = RED
            pyxel.rect(bar_x, bar_y, fill, bar_h, hc)
        pyxel.text(bar_x + 2, bar_y + bar_h + 2, "HEAT", GRAY)

        # Timer
        seconds = max(0, self.timer // 60)
        tcolor = RED if seconds <= 10 else WHITE
        pyxel.text(SCREEN_W - 40, 2, f"Time: {seconds}", tcolor)

        # SUPER indicator
        if self.super_timer > 0:
            remain = self.super_timer // 60 + 1
            color = RAINBOW_COLORS[(pyxel.frame_count // 6) % len(RAINBOW_COLORS)]
            pyxel.text(SCREEN_W // 2 - 25, 16, f"SUPER {remain}s", color)


def main() -> None:
    pyxel.init(SCREEN_W, SCREEN_H, title="WRECK CHAIN", display_scale=2)
    game = Game()
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
