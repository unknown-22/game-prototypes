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

GRID_COLS = 4
GRID_ROWS = 3
CELL_W = 64
CELL_H = 56
GRID_X = 32
GRID_Y = 40
NUM_COLORS = 4
INGREDIENT_COLORS: list[int] = [RED, LIME, ORANGE, LIGHT_BLUE]
COLOR_NAMES: dict[int, str] = {
    RED: "RED",
    LIME: "GRN",
    ORANGE: "ORG",
    LIGHT_BLUE: "BLU",
}

INGREDIENT_TIMER_MAX = 180
SPAWN_INTERVAL = 60
SUPER_COMBO_THRESHOLD = 5
SUPER_DURATION = 300
MAX_HP = 5
BASE_SCORE = 100


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Ingredient:
    color: int
    x: int
    y: int
    timer: int
    opacity: float = 1.0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int
    size: int = 2


# ---------------------------------------------------------------------------
# Game — core logic (testable without Pyxel)
# ---------------------------------------------------------------------------


class Game:
    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.reset()

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.grid: list[list[Ingredient | None]] = [
            [None] * GRID_COLS for _ in range(GRID_ROWS)
        ]
        self.flame_color: int = self.rng.choice(INGREDIENT_COLORS)
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.hp: int = MAX_HP
        self.super_timer: int = 0
        self.spawn_timer: int = 0
        self.particles: list[Particle] = []
        self.super_active: bool = False

    # --- Grid helpers ---

    def _cell_center_x(self, col: int) -> int:
        return GRID_X + col * CELL_W + CELL_W // 2

    def _cell_center_y(self, row: int) -> int:
        return GRID_Y + row * CELL_H + CELL_H // 2

    def _cell_rect(self, col: int, row: int) -> tuple[int, int, int, int]:
        x = GRID_X + col * CELL_W
        y = GRID_Y + row * CELL_H
        return x, y, CELL_W, CELL_H

    def _grid_click_to_cell(self, mx: int, my: int) -> tuple[int, int] | None:
        col = (mx - GRID_X) // CELL_W
        row = (my - GRID_Y) // CELL_H
        if 0 <= col < GRID_COLS and 0 <= row < GRID_ROWS:
            return col, row
        return None

    # --- Cooking ---

    def _cook(self, col: int, row: int) -> bool:
        """Returns True if a successful cook occurred."""
        ingredient = self.grid[row][col]
        if ingredient is None:
            return False

        can_cook = self.super_active or ingredient.color == self.flame_color

        if not can_cook:
            # Wrong color: reset combo, lose HP
            self.combo = 0
            self.hp -= 1
            self._spawn_particles(
                self._cell_center_x(col),
                self._cell_center_y(row),
                ingredient.color,
                8,
            )
            self.grid[row][col] = None
            return False

        # Successful cook
        cooked_color = ingredient.color
        is_same_color = self.super_active or cooked_color == self.flame_color

        if is_same_color and self.combo > 0:
            self.combo += 1
        else:
            self.combo = 1

        if self.combo > self.max_combo:
            self.max_combo = self.combo

        # Update flame color to cooked ingredient's color
        self.flame_color = cooked_color

        # Score
        points = self._score_for_cook()
        self.score += points

        # Particles
        self._spawn_particles(
            self._cell_center_x(col),
            self._cell_center_y(row),
            cooked_color,
            10,
        )

        # Remove ingredient
        self.grid[row][col] = None

        # Check SUPER DISH activation
        if not self.super_active and self.combo >= SUPER_COMBO_THRESHOLD:
            self._activate_super()

        return True

    def _score_for_cook(self, base: int = BASE_SCORE) -> int:
        mult = 3 if self.super_active else 1
        return base * self.combo * mult

    # --- SUPER DISH ---

    def _activate_super(self) -> None:
        self.super_active = True
        self.super_timer = SUPER_DURATION

    # --- Spawning ---

    def _spawn_ingredient(self) -> bool:
        """Returns True if an ingredient was spawned."""
        empty_slots: list[tuple[int, int]] = []
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                if self.grid[row][col] is None:
                    empty_slots.append((col, row))

        if not empty_slots:
            return False

        col, row = self.rng.choice(empty_slots)
        color = self.rng.choice(INGREDIENT_COLORS)
        timer = INGREDIENT_TIMER_MAX + self.rng.randint(-30, 30)
        self.grid[row][col] = Ingredient(color=color, x=col, y=row, timer=timer)
        return True

    # --- Timers ---

    def _update_timers(self) -> None:
        expired: list[tuple[int, int]] = []
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                ing = self.grid[row][col]
                if ing is not None:
                    ing.timer -= 1
                    if ing.timer <= 0:
                        expired.append((col, row))

        for col, row in expired:
            ing = self.grid[row][col]
            if ing is not None:
                self.hp -= 1
                self._spawn_particles(
                    self._cell_center_x(col),
                    self._cell_center_y(row),
                    ing.color,
                    6,
                )
                self.grid[row][col] = None

    # --- Particles ---

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(1.0, 3.5)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = self.rng.randint(8, 20)
            size = self.rng.randint(1, 3)
            self.particles.append(
                Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color, size=size)
            )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.life -= 1
            p.x += p.vx
            p.y += p.vy
        self.particles = [p for p in self.particles if p.life > 0]

    # --- Update (game tick) ---

    def update(self) -> None:
        if self.phase != Phase.PLAYING:
            return

        # Super timer
        if self.super_active:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_active = False
                self.combo = 0

        # Spawn ingredients
        self.spawn_timer += 1
        if self.spawn_timer >= SPAWN_INTERVAL:
            self.spawn_timer = 0
            self._spawn_ingredient()

        # Update timers (expiration check)
        self._update_timers()

        # Update particles
        self._update_particles()

        # Game over check
        if self.hp <= 0:
            self.phase = Phase.GAME_OVER

    # --- Mouse click handling ---

    def handle_click(self, mx: int, my: int) -> None:
        if self.phase != Phase.PLAYING:
            return

        cell = self._grid_click_to_cell(mx, my)
        if cell is None:
            return

        col, row = cell
        self._cook(col, row)


# ---------------------------------------------------------------------------
# App — Pyxel rendering wrapper
# ---------------------------------------------------------------------------


class App:
    def __init__(self) -> None:
        bdf_path = Path(__file__).with_name("k8x12.bdf")
        if bdf_path.exists():
            pyxel.load(str(bdf_path))
        pyxel.init(SCREEN_W, SCREEN_H, title="Flame Chain", display_scale=2)
        self.game = Game()
        pyxel.run(self.update, self.draw)

    # --- Update ---

    def update(self) -> None:
        game = self.game

        if game.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                game.reset()
                game.phase = Phase.PLAYING
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                game.reset()
                game.phase = Phase.PLAYING
            return

        if game.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                game.reset()
                game.phase = Phase.PLAYING
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                game.reset()
                game.phase = Phase.PLAYING
            return

        if game.phase == Phase.PLAYING:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                game.handle_click(pyxel.mouse_x, pyxel.mouse_y)
            game.update()

    # --- Draw ---

    def draw(self) -> None:
        pyxel.cls(BLACK)
        game = self.game

        if game.phase == Phase.TITLE:
            self._draw_background()
            self._draw_title()
        elif game.phase == Phase.PLAYING:
            self._draw_background()
            self._draw_grid()
            self._draw_ingredients()
            self._draw_flame()
            self._draw_hud()
            self._draw_particles()
        elif game.phase == Phase.GAME_OVER:
            self._draw_background()
            self._draw_grid()
            self._draw_ingredients()
            self._draw_flame()
            self._draw_hud()
            self._draw_particles()
            self._draw_game_over()

    # --- Drawing helpers ---

    def _draw_background(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, NAVY)

    def _draw_grid(self) -> None:
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                x = GRID_X + col * CELL_W
                y = GRID_Y + row * CELL_H
                pyxel.rect(x, y, CELL_W, CELL_H, GRAY)
                pyxel.rectb(x, y, CELL_W, CELL_H, WHITE)

    def _draw_ingredients(self) -> None:
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                ing = self.game.grid[row][col]
                if ing is None:
                    continue

                x = GRID_X + col * CELL_W + 4
                y = GRID_Y + row * CELL_H + 4
                w = CELL_W - 8
                h = CELL_H - 8

                # Ingredient body
                pyxel.rect(x, y, w, h, ing.color)
                pyxel.rectb(x, y, w, h, WHITE)

                # Timer bar
                timer_ratio = max(0.0, min(1.0, ing.timer / INGREDIENT_TIMER_MAX))
                bar_w = int((w - 2) * timer_ratio)
                if timer_ratio > 0.5:
                    bar_color = GREEN
                elif timer_ratio > 0.25:
                    bar_color = YELLOW
                else:
                    bar_color = RED
                pyxel.rect(x + 1, y + h - 4, bar_w, 2, bar_color)

                # Color label
                label = COLOR_NAMES.get(ing.color, "???")
                pyxel.text(x + 2, y + 2, label, BLACK)

    def _draw_flame(self) -> None:
        game = self.game

        # Flame indicator (right side of screen)
        cx = SCREEN_W - 48
        cy = 60
        r = 20

        if game.super_active:
            # Rainbow cycling
            idx = (pyxel.frame_count // 4) % len(INGREDIENT_COLORS)
            color = INGREDIENT_COLORS[idx]
        else:
            color = game.flame_color

        pyxel.circ(cx, cy, r, color)
        pyxel.circb(cx, cy, r, WHITE)
        pyxel.circ(cx, cy, r - 6, BLACK)

        # Flame glow
        if game.super_active:
            glow_r = r + 2 + (pyxel.frame_count % 8)
            pyxel.circb(cx, cy, glow_r, CYAN)

        pyxel.text(cx - 14, cy + r + 4, "FLAME", WHITE)

        if game.super_active:
            super_str = "SUPER DISH!"
            pyxel.text(cx - 24, cy + r + 14, super_str, CYAN)

    def _draw_hud(self) -> None:
        game = self.game

        # Score
        pyxel.text(4, 4, f"SCORE: {game.score}", WHITE)

        # Combo
        if game.combo > 0:
            combo_str = f"COMBO x{game.combo}"
            combo_color = game.flame_color
            pyxel.text(4, 14, combo_str, combo_color)

        # HP bar
        hp_x = 4
        hp_y = SCREEN_H - 16
        pyxel.text(hp_x, hp_y - 8, "HP:", WHITE)
        for i in range(MAX_HP):
            hx = hp_x + 16 + i * 14
            if i < game.hp:
                pyxel.rect(hx, hp_y, 10, 6, RED if game.hp > 2 else BROWN)
            else:
                pyxel.rect(hx, hp_y, 10, 6, BLACK)
            pyxel.rectb(hx, hp_y, 10, 6, WHITE)

        # Super timer bar
        if game.super_active:
            bar_w = int(80 * (game.super_timer / SUPER_DURATION))
            pyxel.rect(SCREEN_W // 2 - 40, SCREEN_H - 8, 80, 4, BLACK)
            pyxel.rect(SCREEN_W // 2 - 40, SCREEN_H - 8, bar_w, 4, CYAN)
            pyxel.rectb(SCREEN_W // 2 - 40, SCREEN_H - 8, 80, 4, WHITE)

    def _draw_particles(self) -> None:
        for p in self.game.particles:
            px = int(p.x)
            py = int(p.y)
            if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
                pyxel.rect(px, py, p.size, p.size, p.color)

    def _draw_title(self) -> None:
        # Title
        pyxel.text(SCREEN_W // 2 - 44, 60, "FLAME CHAIN", YELLOW)
        pyxel.text(SCREEN_W // 2 - 64, 80, "Color-Match Cooking", WHITE)
        pyxel.text(SCREEN_W // 2 - 56, 100, "Click ingredients that", WHITE)
        pyxel.text(SCREEN_W // 2 - 56, 110, "match the FLAME color!", WHITE)
        pyxel.text(SCREEN_W // 2 - 56, 130, "Same-color chain = COMBO", YELLOW)
        pyxel.text(SCREEN_W // 2 - 56, 140, "COMBO x5 = SUPER DISH!", CYAN)
        pyxel.text(SCREEN_W // 2 - 56, 160, "Burn (wrong color) = -1HP", RED)
        pyxel.text(SCREEN_W // 2 - 56, 170, "Expire = -1HP", RED)
        pyxel.text(SCREEN_W // 2 - 56, 200, "CLICK or SPACE to start", WHITE)

        # Flame preview animation
        anim_cx = SCREEN_W - 48
        anim_cy = 60
        anim_color = self.game.flame_color
        pyxel.circ(anim_cx, anim_cy, 20, anim_color)
        pyxel.circb(anim_cx, anim_cy, 20, WHITE)
        pyxel.circ(anim_cx, anim_cy, 14, BLACK)
        pyxel.text(anim_cx - 14, anim_cy + 24, "FLAME", WHITE)

    def _draw_game_over(self) -> None:
        pyxel.rect(SCREEN_W // 2 - 90, SCREEN_H // 2 - 45, 180, 90, BLACK)
        pyxel.rectb(SCREEN_W // 2 - 90, SCREEN_H // 2 - 45, 180, 90, WHITE)
        pyxel.text(SCREEN_W // 2 - 30, SCREEN_H // 2 - 35, "GAME OVER", RED)
        pyxel.text(
            SCREEN_W // 2 - 50,
            SCREEN_H // 2 - 18,
            f"SCORE: {self.game.score}",
            WHITE,
        )
        pyxel.text(
            SCREEN_W // 2 - 50,
            SCREEN_H // 2 - 6,
            f"MAX COMBO: {self.game.max_combo}",
            YELLOW,
        )
        pyxel.text(
            SCREEN_W // 2 - 50,
            SCREEN_H // 2 + 12,
            "CLICK or SPACE to retry",
            LIGHT_BLUE,
        )


def main() -> None:
    App()


if __name__ == "__main__":
    main()
