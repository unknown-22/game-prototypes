"""269_coin_surge — Grid Coin Pusher arcade game.

Split coins across columns, converge them with the periodic pusher toward the
right edge, and explode with same-color COMBO chains + SUPER DROP super mode.

Core fun moment: timing your drops across columns so same-color coins get
pushed off together, building a COMBO chain and activating SUPER DROP.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ---------------------------------------------------------------------------
# Screen & grid constants
# ---------------------------------------------------------------------------
SCREEN_W = 320
SCREEN_H = 240
CELL = 20
GRID_COLS = 10
GRID_ROWS = 12
GRID_X = 60
GRID_Y = 0

# ---------------------------------------------------------------------------
# Game constants
# ---------------------------------------------------------------------------
GAME_DURATION = 1800
INITIAL_PUSHER_INTERVAL = 180
MIN_PUSHER_INTERVAL = 60
PUSHER_ANIM_FRAMES = 15
GRAVITY_INTERVAL = 12
INITIAL_COLOR_CYCLE = 90
MIN_COLOR_CYCLE = 30
SUPER_DURATION = 300
COMBO_THRESHOLD = 4
HEAT_MISMATCH = 15
HEAT_DECAY = 0.02
HEAT_MAX = 100
BASE_SCORE = 10

# ---------------------------------------------------------------------------
# Color constants (raw ints — never use pyxel.COLOR_* in logic)
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

COLORS: tuple[int, ...] = (RED, LIME, DARK_BLUE, YELLOW)
COLOR_NAMES: tuple[str, ...] = ("RED", "LIME", "DARK_BLUE", "YELLOW")
NUM_COLORS = len(COLORS)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    PUSHER_ANIM = auto()
    COLLECT = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class Coin:
    col: int
    row: int
    color: int
    falling: bool = True

    @property
    def pyxel_color(self) -> int:
        return COLORS[self.color]


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: int
    size: int = 3


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
    """COIN SURGE — Grid Coin Pusher arcade game."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="COIN SURGE", fps=30, display_scale=2)
        self._load_assets()
        self.phase: Phase = Phase.TITLE
        self.coins: list[Coin] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.best_score: int = 0
        self.super_timer: int = 0
        self.super_mode: bool = False
        self.heat: float = 0.0
        self.timer: int = GAME_DURATION
        self.frame: int = 0
        self.pusher_countdown: int = INITIAL_PUSHER_INTERVAL
        self.drop_color: int = 0
        self.drop_color_timer: int = INITIAL_COLOR_CYCLE
        self.color_cycle_interval: int = INITIAL_COLOR_CYCLE
        self.pusher_interval: int = INITIAL_PUSHER_INTERVAL
        self.last_collected_color: int | None = None
        self._rng: random.Random = random.Random()
        self._frame_count: int = 0
        self._headless: bool = False
        self._anim_frame: int = 0
        self._pending_collected: list[Coin] = []
        self._pusher_offset: float = 0.0
        self._highest_score: int = 0
        self._bgm_playing: bool = False
        self.reset()
        pyxel.run(self.update, self.draw)

    def _load_assets(self) -> None:
        pass

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.coins.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.super_timer = 0
        self.super_mode = False
        self.heat = 0.0
        self.timer = GAME_DURATION
        self.frame = 0
        self.pusher_countdown = INITIAL_PUSHER_INTERVAL
        self.drop_color = 0
        self.drop_color_timer = INITIAL_COLOR_CYCLE
        self.color_cycle_interval = INITIAL_COLOR_CYCLE
        self.pusher_interval = INITIAL_PUSHER_INTERVAL
        self.last_collected_color = None
        self._rng = random.Random()
        self._frame_count = 0
        self._anim_frame = 0
        self._pending_collected.clear()
        self._pusher_offset = 0.0

    def start_game(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.super_timer = 0
        self.super_mode = False
        self.heat = 0.0
        self.timer = GAME_DURATION
        self.frame = 0
        self.pusher_countdown = INITIAL_PUSHER_INTERVAL
        self.drop_color = 0
        self.drop_color_timer = INITIAL_COLOR_CYCLE
        self.color_cycle_interval = INITIAL_COLOR_CYCLE
        self.pusher_interval = INITIAL_PUSHER_INTERVAL
        self.last_collected_color = None
        self._frame_count = 0
        self._anim_frame = 0
        self._pending_collected.clear()
        self._pusher_offset = 0.0
        self.coins.clear()
        self.particles.clear()
        self.floating_texts.clear()

    # -----------------------------------------------------------------------
    # Update (called by pyxel)
    # -----------------------------------------------------------------------
    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.PUSHER_ANIM:
            self._update_pusher_anim()
        elif self.phase == Phase.COLLECT:
            self._update_collect()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.start_game()
        self._update_particles()
        self._update_floating_texts()

    def _update_playing(self) -> None:
        self._frame_count += 1
        self.frame += 1

        if self.frame % GRAVITY_INTERVAL == 0:
            self._apply_gravity()

        self.pusher_countdown -= 1
        if self.pusher_countdown <= 0:
            self.phase = Phase.PUSHER_ANIM
            self._anim_frame = 0
            self._pending_collected = self._activate_pusher()
            self.pusher_countdown = self.pusher_interval
            self._pusher_offset = CELL

        self._update_timer()
        self._update_color_cycle()
        self._update_difficulty()
        self._update_heat()
        self._update_super()
        self._update_particles()
        self._update_floating_texts()

        if self.timer <= 0:
            self._end_game()

        self._handle_input()

    def _handle_input(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            col = self._mouse_to_col()
            if col is not None:
                self._drop_coin(col)
        for k in range(10):
            if pyxel.btnp(getattr(pyxel, f"KEY_{k}")):
                self._drop_coin(k)
                return

    def _mouse_to_col(self) -> int | None:
        mx = pyxel.mouse_x
        if GRID_X <= mx < GRID_X + GRID_COLS * CELL:
            col = (mx - GRID_X) // CELL
            return col
        return None

    def _update_pusher_anim(self) -> None:
        self._anim_frame += 1
        progress = self._anim_frame / PUSHER_ANIM_FRAMES
        self._pusher_offset = CELL * (1.0 - progress)

        self._update_particles()
        self._update_floating_texts()

        if self._anim_frame >= PUSHER_ANIM_FRAMES:
            self._pusher_offset = 0.0
            self.phase = Phase.COLLECT

    def _update_collect(self) -> None:
        self._evaluate_collection(self._pending_collected)
        self._pending_collected.clear()
        self.phase = Phase.PLAYING

        if self.heat >= HEAT_MAX:
            self._end_game()
        if self.timer <= 0:
            self._end_game()

    def _update_game_over(self) -> None:
        self._update_particles()
        self._update_floating_texts()
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()

    def _end_game(self) -> None:
        self.phase = Phase.GAME_OVER
        self.best_score = max(self.best_score, self.score)
        self._highest_score = self.best_score

    # -----------------------------------------------------------------------
    # Core logic (testable, no pyxel input)
    # -----------------------------------------------------------------------
    def _drop_coin(self, col: int) -> None:
        if col < 0 or col >= GRID_COLS:
            return
        if any(c.col == col and c.row == 0 and not c.falling for c in self.coins):
            return
        coin = Coin(col=col, row=0, color=self.drop_color, falling=True)
        self.coins.append(coin)

    def _apply_gravity(self) -> None:
        sorted_coins = sorted(
            [c for c in self.coins if c.falling],
            key=lambda c: c.row, reverse=True,
        )
        for c in sorted_coins:
            if c.row == GRID_ROWS - 1:
                c.falling = False
            elif self._is_cell_occupied(c.col, c.row + 1):
                c.falling = False
            else:
                c.row += 1

    def _activate_pusher(self) -> list[Coin]:
        collected: list[Coin] = []

        for col in range(GRID_COLS - 2, -1, -1):
            for c in list(self.coins):
                if c.col == col and not c.falling:
                    if not self._is_cell_occupied(col + 1, c.row):
                        c.col = col + 1

        for c in list(self.coins):
            if c.col == GRID_COLS - 1 and not c.falling:
                collected.append(c)
                self.coins.remove(c)

        return collected

    def _evaluate_collection(self, collected: list[Coin]) -> None:
        if not collected:
            return

        for coin in collected:
            matching: bool
            if self.super_mode:
                matching = True
            elif self.last_collected_color is None:
                matching = True
            else:
                matching = coin.color == self.last_collected_color

            if matching:
                self.combo += 1
                self.max_combo = max(self.max_combo, self.combo)
                mult = 3 if self.super_mode else 1
                points = BASE_SCORE * self.combo * mult
                self.score += points

                if self.combo >= COMBO_THRESHOLD and not self.super_mode:
                    self.super_mode = True
                    self.super_timer = SUPER_DURATION

                gx = GRID_X + (GRID_COLS - 1) * CELL + CELL
                gy = coin.row * CELL + CELL // 2
                self._spawn_particles(gx, gy, coin.pyxel_color, 4)
                self._spawn_floating_text(gx, gy - 4, f"+{points}", WHITE)

                if self.combo % COMBO_THRESHOLD == 0 and self.combo > 0:
                    self._spawn_floating_text(
                        GRID_X + GRID_COLS * CELL // 2, 60,
                        f"COMBO x{self.combo}", YELLOW,
                    )
                if self.super_mode:
                    self._spawn_floating_text(
                        GRID_X + GRID_COLS * CELL // 2, 40,
                        "SUPER DROP!", YELLOW,
                    )
            else:
                self.combo = 1
                self.heat += HEAT_MISMATCH
                gx = GRID_X + (GRID_COLS - 1) * CELL + CELL
                gy = coin.row * CELL + CELL // 2
                self._spawn_floating_text(gx, gy - 4, "MISS", RED)

            self.last_collected_color = coin.color

    def _update_heat(self) -> None:
        if self.heat >= HEAT_MAX:
            return
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _update_super(self) -> None:
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0

    def _update_timer(self) -> None:
        self.timer -= 1

    def _update_color_cycle(self) -> None:
        self.drop_color_timer -= 1
        if self.drop_color_timer <= 0:
            self.drop_color = (self.drop_color + 1) % NUM_COLORS
            self.drop_color_timer = self.color_cycle_interval
        if self.frame % 300 == 0 and self.color_cycle_interval > MIN_COLOR_CYCLE:
            self.color_cycle_interval -= 2

    def _update_difficulty(self) -> None:
        if self.frame > 0 and self.frame % 300 == 0 and self.pusher_interval > MIN_PUSHER_INTERVAL:
            self.pusher_interval -= 4

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        for _ in range(count):
            angle = self._rng.random() * 2 * math.pi
            speed = 0.5 + self._rng.random() * 2.0
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 1.0,
                color=color, life=20 + self._rng.randint(0, 10),
            ))

    def _spawn_floating_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, color=color, life=30))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    def _is_cell_occupied(self, col: int, row: int) -> bool:
        return any(
            c.col == col and c.row == row and not c.falling
            for c in self.coins
        )

    def _get_coin_at(self, col: int, row: int) -> Coin | None:
        for c in self.coins:
            if c.col == col and c.row == row and not c.falling:
                return c
        return None

    # -----------------------------------------------------------------------
    # Drawing
    # -----------------------------------------------------------------------
    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.PUSHER_ANIM:
            self._draw_playing()
        elif self.phase == Phase.COLLECT:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_playing()
            self._draw_game_over()

    def _draw_title(self) -> None:
        self._draw_grid()

        msg1 = "COIN SURGE"
        w1 = len(msg1) * 4
        pyxel.text(SCREEN_W // 2 - w1 // 2, 70, msg1, YELLOW)

        msg2 = "Press SPACE or Click to start"
        w2 = len(msg2) * 4
        pyxel.text(SCREEN_W // 2 - w2 // 2, 100, msg2, WHITE)

        hints = [
            "Click column / 0-9 key = Drop coin",
            "Pusher shifts coins right periodically",
            "Same-color off the edge = COMBO",
            "COMBO 4+ = SUPER DROP (3x, any color)",
            "Color mismatch = HEAT UP",
            "HEAT 100 = GAME OVER",
        ]
        for i, hint in enumerate(hints):
            hw = len(hint) * 4
            pyxel.text(SCREEN_W // 2 - hw // 2, 130 + i * 12, hint, GRAY)

        if self.best_score > 0:
            bs = f"BEST SCORE: {self.best_score}"
            bw = len(bs) * 4
            pyxel.text(SCREEN_W // 2 - bw // 2, 210, bs, WHITE)

        self._draw_particles()
        self._draw_floating_texts()

    def _draw_playing(self) -> None:
        self._draw_grid()
        self._draw_coins()
        self._draw_drop_preview()
        self._draw_pusher_indicator()
        self._draw_hud()
        self._draw_super_effect()
        self._draw_particles()
        self._draw_floating_texts()

    def _draw_grid(self) -> None:
        pyxel.rect(GRID_X, GRID_Y, GRID_COLS * CELL, GRID_ROWS * CELL, DARK_BLUE)

        for col in range(GRID_COLS + 1):
            px = GRID_X + col * CELL
            pyxel.line(px, 0, px, SCREEN_H, NAVY)

        for row in range(GRID_ROWS + 1):
            py = row * CELL
            pyxel.line(GRID_X, py, GRID_X + GRID_COLS * CELL, py, NAVY)

        pyxel.rectb(GRID_X - 1, GRID_Y, GRID_COLS * CELL + 2, GRID_ROWS * CELL, WHITE)

        # Right edge danger zone
        edge_x = GRID_X + (GRID_COLS - 1) * CELL
        pyxel.rect(edge_x, GRID_Y, CELL, GRID_ROWS * CELL, PURPLE)

    def _draw_coins(self) -> None:
        radius = CELL // 2 - 2
        offset_x = 0.0
        if self.phase == Phase.PUSHER_ANIM:
            offset_x = self._pusher_offset

        for c in self.coins:
            cx = GRID_X + c.col * CELL + CELL // 2 - int(offset_x)
            cy = c.row * CELL + CELL // 2

            col = c.pyxel_color
            if self.super_mode:
                idx = (pyxel.frame_count // 4 + c.color) % NUM_COLORS
                col = COLORS[idx]

            pyxel.circ(int(cx), int(cy), radius + 1, WHITE)
            pyxel.circ(int(cx), int(cy), radius, col)
            pyxel.circ(int(cx) - 2, int(cy) - 2, 1, WHITE)

    def _draw_drop_preview(self) -> None:
        if self.phase != Phase.PLAYING:
            return
        mx = pyxel.mouse_x
        if GRID_X <= mx < GRID_X + GRID_COLS * CELL:
            col = (mx - GRID_X) // CELL
            if not any(c.col == col and c.row == 0 and not c.falling for c in self.coins):
                px = GRID_X + col * CELL + CELL // 2
                py = CELL // 2
                col_val = COLORS[self.drop_color]
                pyxel.circb(px, py, CELL // 2 - 2, col_val)

    def _draw_pusher_indicator(self) -> None:
        bar_x = GRID_X - 8
        bar_y = 10
        bar_w = 4
        bar_h = GRID_ROWS * CELL - 20
        progress = self.pusher_countdown / self.pusher_interval
        fill_h = int(bar_h * (1.0 - progress))

        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, GRAY)
        if fill_h > 0:
            col = LIME
            if progress < 0.3:
                col = RED
            elif progress < 0.6:
                col = YELLOW
            pyxel.rect(bar_x + 1, bar_y + bar_h - fill_h, bar_w - 2, fill_h, col)

        lbl = "PUSH"
        for i, ch in enumerate(lbl):
            pyxel.text(bar_x - 1, bar_y + bar_h + 4 + i * 6, ch, GRAY)

    def _draw_hud(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, 14, BLACK)
        pyxel.line(0, 14, SCREEN_W, 14, GRAY)

        pyxel.text(3, 3, f"SCORE:{self.score}", WHITE)

        combo_s = f"COMBO:{self.combo}"
        cw = len(combo_s) * 4
        combo_col = YELLOW if self.combo >= COMBO_THRESHOLD else WHITE
        pyxel.text(SCREEN_W // 2 - cw // 2, 3, combo_s, combo_col)

        if self.max_combo > 0:
            mx_s = f"MAX:{self.max_combo}"
            mw = len(mx_s) * 4
            pyxel.text(SCREEN_W // 2 - mw // 2, 14, mx_s, GRAY)

        secs = self.timer // 30
        ts = f"TIME:{secs}"
        tc = WHITE if secs > 10 else RED
        pyxel.text(SCREEN_W - 55, 3, ts, tc)

        heat_bar_x = SCREEN_W - 58
        heat_bar_w = 54
        heat_bar_y = 12
        heat_bar_h = 4
        pyxel.rectb(heat_bar_x, heat_bar_y, heat_bar_w, heat_bar_h, GRAY)
        hf = int(self.heat / HEAT_MAX * (heat_bar_w - 1))
        hc = RED if self.heat >= 80 else ORANGE if self.heat >= 50 else YELLOW
        if hf > 0:
            pyxel.rect(heat_bar_x + 1, heat_bar_y, hf, heat_bar_h - 1, hc)
        pyxel.text(heat_bar_x - 22, heat_bar_y - 2, "HEAT", GRAY)

        if self.super_mode:
            ss = f"SUPER:{self.super_timer // 30 + 1}s"
            pyxel.text(3, 22, ss, YELLOW)

        curr_col = COLORS[self.drop_color]
        pyxel.rect(3, 24, 8, 8, curr_col)
        pyxel.rectb(2, 23, 10, 10, WHITE)

    def _draw_super_effect(self) -> None:
        if not self.super_mode:
            return
        pulse = abs(math.sin(pyxel.frame_count * 0.1)) * 8
        col_idx = (pyxel.frame_count // 4) % NUM_COLORS
        border_col = COLORS[col_idx]
        pyxel.rectb(
            GRID_X - 2, GRID_Y - 2,
            GRID_COLS * CELL + 4, GRID_ROWS * CELL + 4,
            border_col,
        )
        if pulse > 0:
            pyxel.rectb(
                int(GRID_X - 2 - pulse), int(GRID_Y - 2 - pulse),
                int(GRID_COLS * CELL + 4 + pulse * 2),
                int(GRID_ROWS * CELL + 4 + pulse * 2),
                border_col,
            )

    def _draw_particles(self) -> None:
        for p in self.particles:
            px = int(p.x)
            py = int(p.y)
            if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
                alpha = p.life / 30
                if alpha > 0.5:
                    pyxel.pset(px, py, p.color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            tx = int(ft.x)
            ty = int(ft.y)
            tw = len(ft.text) * 4
            col = ft.color
            if ft.life < 10:
                col = GRAY
            pyxel.text(tx - tw // 2, ty, ft.text, col)

    def _draw_game_over(self) -> None:
        pyxel.rect(0, 0, SCREEN_W, SCREEN_H, BLACK)

        go = "GAME OVER"
        gw = len(go) * 4
        pyxel.text(SCREEN_W // 2 - gw // 2, 70, go, RED)

        ss = f"SCORE: {self.score}"
        sw = len(ss) * 4
        pyxel.text(SCREEN_W // 2 - sw // 2, 95, ss, WHITE)

        mc = f"MAX COMBO: {self.max_combo}"
        mw = len(mc) * 4
        pyxel.text(SCREEN_W // 2 - mw // 2, 110, mc, YELLOW)

        bs = f"BEST SCORE: {self.best_score}"
        bw = len(bs) * 4
        pyxel.text(SCREEN_W // 2 - bw // 2, 125, bs, WHITE)

        cause = "TIME UP" if self.timer <= 0 else "OVERHEAT"
        cw = len(cause) * 4
        pyxel.text(SCREEN_W // 2 - cw // 2, 145, cause, GRAY)

        retry = "Press SPACE or Click to retry"
        rw = len(retry) * 4
        pyxel.text(SCREEN_W // 2 - rw // 2, 170, retry, GRAY)

        self._draw_particles()
        self._draw_floating_texts()


if __name__ == "__main__":
    Game()
