from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import ClassVar

import pyxel

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

COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
COLOR_NAMES: list[str] = ["RED", "GREEN", "BLUE", "YELLOW"]

SCREEN_W = 320
SCREEN_H = 240
GROUND_Y = 200
CATAPULT_X = 50

WALL_X = 140
WALL_Y = 40
CELL = 24
WALL_COLS = 8
WALL_ROWS = 6

GRAVITY = 0.3
MIN_POWER = 20.0
MAX_POWER = 150.0

BASE_SCORE = 10
COMBO_SCORE_MULT = 0.5

COMBO_FOR_SUPER = 4
SUPER_DURATION = 300
SUPER_SCORE_MULT = 3

HEAT_PER_MISMATCH = 15.0
HEAT_DECAY = 0.03
HEAT_MAX = 100.0

GAME_DURATION = 3600
IMPACT_PAUSE = 15

MAX_PARTICLES = 100
MAX_FLOATING_TEXTS = 20

TRAJECTORY_STORE_MAX = 200


class Phase(Enum):
    TITLE = auto()
    AIMING = auto()
    FLYING = auto()
    IMPACT = auto()
    GAME_OVER = auto()


@dataclass
class Block:
    col: int
    row: int
    color: int
    hp: int = 1
    cracked: bool = False
    crack_timer: int = 0


@dataclass
class Boulder:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    alive: bool = True


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
    life: int
    color: int


@dataclass
class TrajectoryPoint:
    x: float
    y: float


class Game:
    _initialized: ClassVar[bool] = False

    def __init__(self) -> None:
        if Game._initialized:
            return
        Game._initialized = True

        pyxel.init(SCREEN_W, SCREEN_H, title="Siege Chain", display_scale=2)
        self._rng = random.Random()
        self._pre_init_state()
        try:
            pyxel.load(str(Path(__file__).with_name("k8x12.bdf")))
        except Exception:
            pass
        pyxel.run(self._update, self._draw)

    def _pre_init_state(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.high_score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.super_timer: int = 0
        self.super_mode: bool = False
        self.super_flash: int = 0
        self.game_timer: int = GAME_DURATION
        self.blocks: list[Block] = []
        self.boulder: Boulder | None = None
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.aim_start_x: int = 0
        self.aim_start_y: int = 0
        self.aiming: bool = False
        self.impact_pause: int = 0
        self.prev_trajectory: list[TrajectoryPoint] = []
        self.color_index: int = 0
        self.frame: int = 0
        self._phase_playing_start: bool = False

    def reset(self) -> None:
        self.phase = Phase.AIMING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.super_timer = 0
        self.super_mode = False
        self.super_flash = 0
        self.game_timer = GAME_DURATION
        self.boulder = None
        self.particles.clear()
        self.floating_texts.clear()
        self.aiming = False
        self.impact_pause = 0
        self.prev_trajectory.clear()
        self.color_index = 0
        self._phase_playing_start = True
        self._init_wall()

    def _init_wall(self) -> None:
        self.blocks.clear()
        for row in range(WALL_ROWS):
            for col in range(WALL_COLS):
                color = self._rng.choice(COLORS)
                self.blocks.append(Block(col=col, row=row, color=color, hp=1))

    def _get_next_color(self) -> int:
        c = COLORS[self.color_index % len(COLORS)]
        self.color_index += 1
        return c

    # --- Update ---

    def _update(self) -> None:
        self.frame = self.frame + 1

        if self.phase in (Phase.AIMING, Phase.FLYING, Phase.IMPACT):
            if pyxel.btnp(pyxel.KEY_R):
                self._force_game_over()
                return

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()
        elif self.phase == Phase.AIMING:
            self._update_aiming()
        elif self.phase == Phase.FLYING:
            self._update_flying()
        elif self.phase == Phase.IMPACT:
            self._update_impact()
        else:
            self._update_playing_common()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.phase = Phase.TITLE

    def _update_playing_common(self) -> None:
        self.game_timer -= 1
        if self.game_timer <= 0:
            if len(self.blocks) == 0:
                self.score = int(self.score * 1.5)
            self.phase = Phase.GAME_OVER
            if self.score > self.high_score:
                self.high_score = self.score
            return

        self._update_super_mode()
        self._update_heat()
        self._update_particles()
        self._update_floating_texts()
        self._update_crack_timers()

    def _update_aiming(self) -> None:
        self._update_playing_common()
        if self.phase != Phase.AIMING:
            return

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.aim_start_x = pyxel.mouse_x
            self.aim_start_y = pyxel.mouse_y
            self.aiming = True
        elif pyxel.btn(pyxel.MOUSE_BUTTON_LEFT) and self.aiming:
            mx = pyxel.mouse_x
            my = pyxel.mouse_y
            dx = mx - CATAPULT_X
            dy = GROUND_Y - my
            power = math.sqrt(dx * dx + dy * dy)
            power = max(MIN_POWER, min(MAX_POWER, power))
            angle = math.atan2(float(dy), float(dx))
            boulder_color = self._get_next_color()
            vx = power * math.cos(angle)
            vy = -(power * math.sin(angle))
            self.boulder = Boulder(x=float(CATAPULT_X), y=float(GROUND_Y), vx=vx, vy=vy, color=boulder_color)
            self.phase = Phase.FLYING
            self.aiming = False
        elif not pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
            self.aiming = False

    def _update_flying(self) -> None:
        self._update_playing_common()
        if self.phase != Phase.FLYING:
            return
        if self.boulder is None or not self.boulder.alive:
            self._miss_shot()
            return

        b = self.boulder
        prev_x = b.x
        prev_y = b.y
        b.x += b.vx
        b.y += b.vy
        b.vy += GRAVITY

        if len(self.prev_trajectory) < TRAJECTORY_STORE_MAX:
            self.prev_trajectory.append(TrajectoryPoint(x=prev_x, y=prev_y))

        # Check wall collision
        hit_block = self._check_wall_collision(b.x, b.y)
        if hit_block is not None:
            self._handle_impact(hit_block)
            self.phase = Phase.IMPACT
            self.impact_pause = IMPACT_PAUSE
            self.boulder = None
            return

        # Miss check
        if b.y > SCREEN_H + 20 or b.x > SCREEN_W + 20 or b.x < -20:
            self._miss_shot()

    def _update_impact(self) -> None:
        self._update_playing_common()
        if self.phase != Phase.IMPACT:
            return
        self.impact_pause -= 1
        if self.impact_pause <= 0:
            self._propagate_cracks()
            self._remove_cracked_blocks()
            self.impact_pause = 0
            if len(self.blocks) == 0:
                self.score = int(self.score * 1.5)
                self.phase = Phase.GAME_OVER
                if self.score > self.high_score:
                    self.high_score = self.score
            else:
                self.phase = Phase.AIMING

    # --- Super & Heat ---

    def _update_super_mode(self) -> None:
        if self.super_timer > 0:
            self.super_timer -= 1
            self.super_flash = (self.super_flash + 1) % (4 * 8)
            if self.super_timer == 0:
                self.super_mode = False
                self.super_flash = 0

    def _update_heat(self) -> None:
        if self.heat > 0:
            self.heat -= HEAT_DECAY
            if self.heat < 0:
                self.heat = 0.0

    # --- Wall Collision ---

    def _check_wall_collision(self, bx: float, by: float) -> Block | None:
        for block in self.blocks:
            if block.hp <= 0:
                continue
            block_x = WALL_X + block.col * CELL
            block_y = WALL_Y + block.row * CELL
            if block_x <= bx <= block_x + CELL and block_y <= by <= block_y + CELL:
                return block
        return None

    def _handle_impact(self, block: Block) -> None:
        bx = WALL_X + block.col * CELL + CELL // 2
        by = WALL_Y + block.row * CELL + CELL // 2

        if self.boulder is None:
            return

        boulder_color = self.boulder.color

        if self.super_mode:
            self.combo += 1
            score_gain = int(BASE_SCORE * SUPER_SCORE_MULT * (1 + self.combo * COMBO_SCORE_MULT))
            self.score += score_gain
            self._spawn_super_particles(bx, by)
            self._add_floating_text(bx, by, f"+{score_gain}", YELLOW)
            if self.combo > 1:
                self._add_floating_text(bx, by - 8, f"COMBO x{self.combo}!", GREEN)
        elif boulder_color == block.color:
            self.combo += 1
            score_gain = int(BASE_SCORE * (1 + self.combo * COMBO_SCORE_MULT))
            self.score += score_gain
            self._spawn_match_particles(bx, by, block.color)
            self._add_floating_text(bx, by, f"+{score_gain}", block.color)
            if self.combo > 1:
                self._add_floating_text(bx, by - 8, f"COMBO x{self.combo}!", GREEN)
        else:
            self.combo = 0
            self.heat += HEAT_PER_MISMATCH
            if self.heat > HEAT_MAX:
                self.heat = HEAT_MAX
            self.score += 5
            self._spawn_mismatch_particles(bx, by)
            self._add_floating_text(bx, by, "+5", ORANGE)
            self._add_floating_text(bx, by - 8, "HEAT +15", RED)

        if self.combo > self.max_combo:
            self.max_combo = self.combo

        if self.combo >= COMBO_FOR_SUPER and not self.super_mode:
            self.super_mode = True
            self.super_timer = SUPER_DURATION
            self.super_flash = 0
            self._add_floating_text(SCREEN_W // 2, SCREEN_H // 2 - 20, "SUPER!", YELLOW)

        # Mark block as cracked and propagate
        block.hp = 0
        block.cracked = True
        block.crack_timer = 8

        # CA propagation: find same-color neighbors and crack them
        self._crack_neighbors(block)

    def _crack_neighbors(self, block: Block) -> None:
        """CA propagation: crack adjacent same-color blocks."""
        for nb in self.blocks:
            if nb.hp <= 0 or nb.cracked:
                continue
            is_adjacent = (
                (abs(nb.col - block.col) == 1 and nb.row == block.row)
                or (abs(nb.row - block.row) == 1 and nb.col == block.col)
            )
            if not is_adjacent:
                continue
            if self.super_mode or nb.color == block.color:
                nb.hp = 0
                nb.cracked = True
                nb.crack_timer = 8

    def _propagate_cracks(self) -> None:
        """One step of CA propagation: cracked blocks spread to neighbors."""
        newly_cracked: list[Block] = []
        for block in self.blocks:
            if not block.cracked:
                continue
            for nb in self.blocks:
                if nb.hp <= 0 or nb.cracked:
                    continue
                is_adjacent = (
                    (abs(nb.col - block.col) == 1 and nb.row == block.row)
                    or (abs(nb.row - block.row) == 1 and nb.col == block.col)
                )
                if not is_adjacent:
                    continue
                if self.super_mode or nb.color == block.color:
                    nb.hp = 0
                    nb.cracked = True
                    nb.crack_timer = 8
                    newly_cracked.append(nb)

        for nb in newly_cracked:
            bx = WALL_X + nb.col * CELL + CELL // 2
            by = WALL_Y + nb.row * CELL + CELL // 2
            self._spawn_match_particles(bx, by, nb.color)
            self.score += 5

    def _remove_cracked_blocks(self) -> None:
        self.blocks = [b for b in self.blocks if b.hp > 0]

    def _update_crack_timers(self) -> None:
        for block in self.blocks:
            if block.cracked and block.crack_timer > 0:
                block.crack_timer -= 1

    def _force_game_over(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.high_score:
            self.high_score = self.score

    def _miss_shot(self) -> None:
        self.combo = 0
        self.boulder = None
        self.phase = Phase.AIMING

    # --- Particles ---

    def _spawn_match_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(7):
            if len(self.particles) >= MAX_PARTICLES:
                break
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-2.5, 2.5),
                    vy=self._rng.uniform(-2.5, 2.5),
                    life=self._rng.randint(15, 25),
                    color=color,
                    size=2,
                )
            )

    def _spawn_super_particles(self, x: float, y: float) -> None:
        for _ in range(14):
            if len(self.particles) >= MAX_PARTICLES:
                break
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-3.5, 3.5),
                    vy=self._rng.uniform(-3.5, 3.5),
                    life=self._rng.randint(20, 30),
                    color=self._rng.choice(COLORS),
                    size=4,
                )
            )

    def _spawn_mismatch_particles(self, x: float, y: float) -> None:
        for _ in range(5):
            if len(self.particles) >= MAX_PARTICLES:
                break
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=self._rng.uniform(-1.5, 1.5),
                    vy=self._rng.uniform(-1.5, 1.5),
                    life=self._rng.randint(10, 18),
                    color=RED,
                    size=2,
                )
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # --- Floating Text ---

    def _add_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=40, color=color))
        while len(self.floating_texts) > MAX_FLOATING_TEXTS:
            self.floating_texts.pop(0)

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.6
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # --- Drawing ---

    def _draw(self) -> None:
        pyxel.cls(DARK_BLUE)
        self._draw_sky_gradient()

        if self.phase == Phase.TITLE:
            self._draw_title()
            return

        self._draw_ground()
        self._draw_ghost_trajectory()
        self._draw_wall()
        self._draw_boulder()
        self._draw_catapult()

        if self.phase == Phase.AIMING:
            self._draw_aim_line()
        elif self.phase == Phase.IMPACT:
            pass

        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

        if self.phase == Phase.GAME_OVER:
            self._draw_game_over_overlay()
        elif self.phase == Phase.TITLE:
            self._draw_title_overlay()

    def _draw_sky_gradient(self) -> None:
        for y in range(0, SCREEN_H, 2):
            if y < GROUND_Y - 40:
                c = LIGHT_BLUE
            elif y < GROUND_Y:
                c = DARK_BLUE
            else:
                c = BROWN
            pyxel.rect(0, y, SCREEN_W, 2, c)

    def _draw_ground(self) -> None:
        pyxel.rect(0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y, BROWN)
        pyxel.line(0, GROUND_Y, SCREEN_W, GROUND_Y, GREEN)

    def _draw_catapult(self) -> None:
        cx = CATAPULT_X
        cy = GROUND_Y
        pyxel.rect(cx - 10, cy - 6, 20, 8, BROWN)
        pyxel.tri(cx - 10, cy - 6, cx + 10, cy - 6, cx, cy - 18, GRAY)
        pyxel.circ(cx - 8, cy - 12, 3, GRAY)
        pyxel.circ(cx + 8, cy - 12, 3, GRAY)
        pyxel.rect(cx - 15, cy, 30, 4, BROWN)

    def _draw_aim_line(self) -> None:
        if not self.aiming:
            return
        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        pyxel.line(CATAPULT_X, GROUND_Y, mx, my, WHITE)
        dx = mx - CATAPULT_X
        dy = GROUND_Y - my
        power = math.sqrt(dx * dx + dy * dy)
        power = max(MIN_POWER, min(MAX_POWER, power))
        # Draw power indicator dot
        dot_x = int(CATAPULT_X + (mx - CATAPULT_X) * 0.3)
        dot_y = int(GROUND_Y - (GROUND_Y - my) * 0.3)
        pyxel.circ(dot_x, dot_y, 2, WHITE)

    def _draw_wall(self) -> None:
        for block in self.blocks:
            if block.hp <= 0:
                continue
            x = WALL_X + block.col * CELL
            y = WALL_Y + block.row * CELL
            color = block.color
            pyxel.rect(x, y, CELL, CELL, color)
            pyxel.rectb(x, y, CELL, CELL, BLACK)
            if block.cracked:
                pyxel.line(x, y, x + CELL, y + CELL, WHITE)
                pyxel.line(x + CELL, y, x, y + CELL, WHITE)
                pyxel.rectb(x, y, CELL, CELL, WHITE)

    def _draw_boulder(self) -> None:
        if self.boulder is not None and self.boulder.alive:
            color = self.boulder.color
            if self.super_mode:
                colors = COLORS
                idx = (self.super_flash // 8) % len(colors)
                color = colors[idx]
            pyxel.circ(int(self.boulder.x), int(self.boulder.y), 4, color)
            pyxel.circb(int(self.boulder.x), int(self.boulder.y), 4, BLACK)

    def _draw_ghost_trajectory(self) -> None:
        if not self.prev_trajectory:
            return
        for pt in self.prev_trajectory:
            ix = int(pt.x)
            iy = int(pt.y)
            if 0 <= ix < SCREEN_W and 0 <= iy < SCREEN_H:
                if self.frame % 3 == 0:
                    pyxel.pset(ix, iy, GRAY)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 30.0
            if alpha > 0.2:
                pyxel.rect(int(p.x), int(p.y), p.size, p.size, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 40.0
            if alpha > 0.2:
                pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_hud(self) -> None:
        score_str = f"SCORE: {self.score}"
        pyxel.text(4, 4, score_str, WHITE)

        combo_str = f"COMBO: {self.combo}x"
        combo_color = WHITE
        if self.combo >= COMBO_FOR_SUPER:
            combo_color = YELLOW
        elif self.combo >= 3:
            combo_color = GREEN
        pyxel.text(4, 14, combo_str, combo_color)

        timer_str = f"TIME: {max(0, self.game_timer // 60)}"
        pyxel.text(SCREEN_W // 2 - len(timer_str) * 2, 4, timer_str, WHITE)

        # HEAT bar
        bar_x = SCREEN_W - 70
        bar_y = 6
        bar_w = 64
        bar_h = 6
        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        fill_w = int(bar_w * (self.heat / HEAT_MAX))
        fill_color = GREEN
        if self.heat > 60:
            fill_color = ORANGE
        if self.heat > 80:
            fill_color = RED
        pyxel.rect(bar_x, bar_y, fill_w, bar_h, fill_color)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)
        heat_str = f"HEAT: {int(self.heat)}"
        pyxel.text(bar_x, bar_y + 8, heat_str, fill_color)

        # Next boulder color indicator
        next_color = COLORS[self.color_index % len(COLORS)]
        pyxel.rect(4, SCREEN_H - 16, 12, 12, next_color)
        pyxel.rectb(4, SCREEN_H - 16, 12, 12, WHITE)
        pyxel.text(18, SCREEN_H - 14, "NEXT", WHITE)

        if self.super_mode:
            super_sec = self.super_timer / 60.0
            super_str = f"SUPER! {super_sec:.1f}s"
            pyxel.text(SCREEN_W // 2 - len(super_str) * 2, 16, super_str, YELLOW)

    def _draw_title(self) -> None:
        pyxel.text(SCREEN_W // 2 - 32, 60, "SIEGE CHAIN", WHITE)

        pyxel.text(SCREEN_W // 2 - 64, 90, "Click & Drag to aim catapult", WHITE)
        pyxel.text(SCREEN_W // 2 - 76, 100, "Match boulder color to wall blocks!", WHITE)
        pyxel.text(SCREEN_W // 2 - 52, 112, "Same color = COMBO chain", GREEN)
        pyxel.text(SCREEN_W // 2 - 52, 124, "COMBO x4 = SUPER BOULDER", YELLOW)
        pyxel.text(SCREEN_W // 2 - 68, 136, "Wrong color = HEAT (+15)", RED)

        pyxel.text(SCREEN_W // 2 - 40, 160, "60 second timer!", WHITE)
        pyxel.text(SCREEN_W // 2 - 56, 180, "PRESS ENTER to start", YELLOW)
        pyxel.text(SCREEN_W // 2 - 32, 210, "R to restart", GRAY)

        # Draw small demo catapult
        self._draw_demo_catapult()

    def _draw_demo_catapult(self) -> None:
        cx = SCREEN_W // 2
        cy = 200
        pyxel.rect(cx - 8, cy - 5, 16, 7, BROWN)
        pyxel.tri(cx - 8, cy - 5, cx + 8, cy - 5, cx, cy - 15, GRAY)
        pyxel.circ(cx - 7, cy - 10, 2, GRAY)
        pyxel.circ(cx + 7, cy - 10, 2, GRAY)

    def _draw_title_overlay(self) -> None:
        pass

    def _draw_game_over_overlay(self) -> None:
        pyxel.rect(SCREEN_W // 2 - 80, SCREEN_H // 2 - 50, 160, 100, BLACK)
        pyxel.rectb(SCREEN_W // 2 - 80, SCREEN_H // 2 - 50, 160, 100, RED)
        pyxel.text(SCREEN_W // 2 - 22, SCREEN_H // 2 - 40, "GAME OVER", RED)

        score_str = f"Score: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_str) * 2, SCREEN_H // 2 - 20, score_str, WHITE)
        hi_str = f"Best: {self.high_score}"
        pyxel.text(SCREEN_W // 2 - len(hi_str) * 2, SCREEN_H // 2 - 10, hi_str, YELLOW)
        combo_str = f"Max Combo: {self.max_combo}"
        pyxel.text(SCREEN_W // 2 - len(combo_str) * 2, SCREEN_H // 2, combo_str, GREEN)
        pyxel.text(SCREEN_W // 2 - 44, SCREEN_H // 2 + 20, "ENTER to retry", YELLOW)

    def _draw_boulder_trail(self) -> None:
        pass


def main() -> None:
    Game()


if __name__ == "__main__":
    main()
