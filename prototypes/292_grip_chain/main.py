"""GRIP CHAIN -- Vertical rock climbing COMBO chain game.

一番面白い瞬間: 同じ色のホールドを連続で掴んでCOMBOを伸ばし、
壁面を自分の色で塗り替えていくのが面白い
"""
from __future__ import annotations

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
FPS = 30
FONT_PATH = Path(__file__).with_name("k8x12.bdf")
FONT_W = 8
FONT_H = 12

COLS = 8
ROWS = 10
CELL = 24
GRID_X = 40
GRID_Y = 12

GAME_DURATION = 1800
SUPER_DURATION = 300

COLORS = (8, 11, 5, 10)  # RED, LIME, DARK_BLUE, YELLOW
COLOR_CYCLE_INITIAL = 45
COLOR_CYCLE_MIN = 20

MIN_HOLDS = 8
MAX_HOLDS = 12
RESPAWN_DELAY_INITIAL = 60
RESPAWN_DELAY_MIN = 30

HEAT_MISMATCH = 15.0
HEAT_DECAY = 0.02
HEAT_MAX = 100.0

COMBO_SUPER_THRESHOLD = 4

PARTICLE_COUNT_MATCH = 8
PARTICLE_COUNT_SUPER = 16
PARTICLE_COUNT_MISMATCH = 4
FLOAT_TEXT_LIFE = 45
BLINK_VISIBLE = 20
BLINK_HIDDEN = 5

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

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------
@dataclass
class Hold:
    col: int
    row: int
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


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    """Pure game logic -- no pyxel calls for testable methods."""

    def __init__(self) -> None:
        self.rng = random.Random()
        self.best_score = 0
        self._init_state()

    def _init_state(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = GAME_DURATION
        self.holds: list[Hold] = []
        self.player_col = 0
        self.player_row = 0
        self.player_color_idx = 0
        self.color_cycle_timer = COLOR_CYCLE_INITIAL
        self.super_timer = 0
        self.super_mode = False
        self.respawn_timer = 0
        self.last_grabbed_color = -1
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._shake_frames = 0
        self._elapsed_frames = 0

    def reset(self) -> None:
        best = self.best_score
        self.rng = random.Random()
        self._init_state()
        self.best_score = best
        self.phase = Phase.PLAYING
        self.holds.clear()
        self._generate_holds(MIN_HOLDS)
        self._place_player()
        self.respawn_timer = self._get_respawn_delay()
        self.color_cycle_timer = COLOR_CYCLE_INITIAL

    # ── Hold Management ───────────────────────────────────────────────────
    def _generate_holds(self, n: int) -> None:
        occupied = {(h.col, h.row) for h in self.holds}
        available = [
            (c, r)
            for c in range(COLS)
            for r in range(ROWS)
            if (c, r) not in occupied
        ]
        self.rng.shuffle(available)
        for col, row in available[:n]:
            color = self.rng.choice(COLORS)
            self.holds.append(Hold(col=col, row=row, color=color))

    def _find_hold(self, col: int, row: int) -> Hold | None:
        for h in self.holds:
            if h.col == col and h.row == row:
                return h
        return None

    def _place_player(self) -> None:
        """Place player on a random hold."""
        if not self.holds:
            return
        hold = self.rng.choice(self.holds)
        self.player_col = hold.col
        self.player_row = hold.row

    # ── Movement ──────────────────────────────────────────────────────────
    def _try_move(self, dcol: int, drow: int) -> bool:
        new_col = self.player_col + dcol
        new_row = self.player_row + drow
        if not (0 <= new_col < COLS and 0 <= new_row < ROWS):
            return False
        hold = self._find_hold(new_col, new_row)
        if hold is None:
            return False
        self.player_col = new_col
        self.player_row = new_row
        self._process_grab(hold)
        return True

    # ── Grab Processing ───────────────────────────────────────────────────
    def _process_grab(self, hold: Hold) -> None:
        player_color = COLORS[self.player_color_idx]
        is_match = self.super_mode or hold.color == player_color

        gx, gy = self._hold_center(hold.col, hold.row)

        if is_match:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            base_score = 10 * self.combo
            score_gain = base_score * 3 if self.super_mode else base_score
            self.score += score_gain
            self.last_grabbed_color = hold.color
            hold.color = player_color

            if self.super_mode:
                self._spawn_particles(gx, gy, WHITE, PARTICLE_COUNT_SUPER, 0.05)
            else:
                self._spawn_particles(gx, gy, hold.color, PARTICLE_COUNT_MATCH, 0.1)
            self._add_floating_text(f"+{score_gain}", gx, gy - 6, WHITE)

            if self.combo > 1:
                combo_color = RED if self.combo >= COMBO_SUPER_THRESHOLD else YELLOW
                self._add_floating_text(f"COMBO x{self.combo}!", SCREEN_W // 2, 30, combo_color)

            if self.combo >= COMBO_SUPER_THRESHOLD and not self.super_mode:
                self._start_super()
        else:
            self.combo = 0
            self.last_grabbed_color = -1
            self.heat += HEAT_MISMATCH
            self._shake_frames = 8
            self._spawn_particles(gx, gy, GRAY, PARTICLE_COUNT_MISMATCH, 0.2)
            self._add_floating_text("WRONG!", gx, gy - 6, RED)

        self._remove_and_respawn_hold(hold)

    def _remove_and_respawn_hold(self, hold: Hold) -> None:
        self.holds.remove(hold)

    def _hold_center(self, col: int, row: int) -> tuple[float, float]:
        return (
            GRID_X + col * CELL + CELL // 2,
            GRID_Y + row * CELL + CELL // 2,
        )

    # ── SUPER GRIP ────────────────────────────────────────────────────────
    def _start_super(self) -> None:
        self.super_mode = True
        self.super_timer = SUPER_DURATION
        self._add_floating_text("SUPER GRIP!", SCREEN_W // 2, 14, YELLOW)

    def _end_super(self) -> None:
        self.super_mode = False
        self.super_timer = 0

    # ── Heat ──────────────────────────────────────────────────────────────
    def _update_heat(self) -> None:
        self.heat = max(0.0, self.heat - HEAT_DECAY)
        if self.heat >= HEAT_MAX:
            self.heat = HEAT_MAX

    # ── Color Cycle ───────────────────────────────────────────────────────
    def _update_color_cycle(self) -> None:
        if self.super_mode:
            return
        self.color_cycle_timer -= 1
        if self.color_cycle_timer <= 0:
            self.player_color_idx = (self.player_color_idx + 1) % len(COLORS)
            self.color_cycle_timer = self._get_color_cycle_interval()

    # ── Timer ─────────────────────────────────────────────────────────────
    def _update_timer(self) -> None:
        self.timer -= 1

    # ── Respawns ──────────────────────────────────────────────────────────
    def _update_respawns(self) -> None:
        self.respawn_timer -= 1
        if self.respawn_timer <= 0:
            current = len(self.holds)
            needed = self._get_min_holds() - current
            if needed > 0:
                self._generate_holds(min(needed, MAX_HOLDS - current))
            self.respawn_timer = self._get_respawn_delay()

    # ── Difficulty ────────────────────────────────────────────────────────
    def _get_progress(self) -> float:
        return min(self._elapsed_frames / GAME_DURATION, 1.0)

    def _get_color_cycle_interval(self) -> int:
        t = self._get_progress()
        return int(COLOR_CYCLE_INITIAL + (COLOR_CYCLE_MIN - COLOR_CYCLE_INITIAL) * t)

    def _get_respawn_delay(self) -> int:
        t = self._get_progress()
        return int(RESPAWN_DELAY_INITIAL + (RESPAWN_DELAY_MIN - RESPAWN_DELAY_INITIAL) * t)

    def _get_min_holds(self) -> int:
        t = self._get_progress()
        return int(MIN_HOLDS + (MAX_HOLDS - MIN_HOLDS) * t)

    # ── Particles ─────────────────────────────────────────────────────────
    def _spawn_particles(self, x: float, y: float, color: int, count: int, gravity: float) -> None:
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=x + self.rng.uniform(-4, 4),
                    y=y + self.rng.uniform(-4, 4),
                    vx=self.rng.uniform(-2, 2),
                    vy=self.rng.uniform(-4, -2),
                    life=self.rng.randint(15, 25),
                    color=color,
                )
            )

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    # ── Floating Text ─────────────────────────────────────────────────────
    def _add_floating_text(self, text: str, x: float, y: float, color: int) -> None:
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=FLOAT_TEXT_LIFE, color=color))

    def _update_floating_texts(self) -> None:
        alive: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= 0.7
            ft.life -= 1
            if ft.life > 0:
                alive.append(ft)
        self.floating_texts = alive

    # ── Update ────────────────────────────────────────────────────────────
    def update(self) -> None:
        if self.phase != Phase.PLAYING:
            return

        self._elapsed_frames += 1
        self._update_timer()

        if self.timer <= 0:
            self.timer = 0
            self._end_game()
            return

        if self.heat >= HEAT_MAX:
            self._end_game()
            return
        self._update_heat()

        self._update_color_cycle()
        self._update_respawns()

        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self._end_super()

        if self._shake_frames > 0:
            self._shake_frames -= 1

        self._update_particles()
        self._update_floating_texts()

    def _end_game(self) -> None:
        self.phase = Phase.GAME_OVER
        if self.score > self.best_score:
            self.best_score = self.score

    # ── Draw ──────────────────────────────────────────────────────────────
    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = "GRIP CHAIN"
        tw = len(title) * FONT_W
        pyxel.text(SCREEN_W // 2 - tw // 2, 40, title, WHITE)

        subtitle = "ROCK CLIMBING"
        sw = len(subtitle) * FONT_W
        pyxel.text(SCREEN_W // 2 - sw // 2, 56, subtitle, YELLOW)

        lines = [
            "Arrow Keys: Move cursor",
            "Grab same-color holds to build COMBO",
            "Wrong color = HEAT up (100 = GAME OVER)",
            "COMBO x4 = SUPER GRIP (3x score!)",
            "",
            "TIMER: 60 seconds",
            "",
            "PRESS ENTER TO START",
        ]
        for i, line in enumerate(lines):
            y = 80 + i * (FONT_H + 2)
            lw = len(line) * FONT_W
            pyxel.text(SCREEN_W // 2 - lw // 2, y, line, GRAY)

        if self.best_score > 0:
            best_text = f"BEST SCORE: {self.best_score}"
            bw = len(best_text) * FONT_W
            pyxel.text(SCREEN_W // 2 - bw // 2, 210, best_text, CYAN)

    def _draw_game_over(self) -> None:
        go_text = "GAME OVER"
        tw = len(go_text) * FONT_W
        pyxel.text(SCREEN_W // 2 - tw // 2, 50, go_text, RED)

        score_text = f"SCORE: {self.score}"
        sw = len(score_text) * FONT_W
        pyxel.text(SCREEN_W // 2 - sw // 2, 80, score_text, WHITE)

        if self.score >= self.best_score and self.best_score > 0:
            new_best = "NEW BEST!"
            nbw = len(new_best) * FONT_W
            pyxel.text(SCREEN_W // 2 - nbw // 2, 96, new_best, YELLOW)

        best_text = f"BEST: {self.best_score}"
        bw = len(best_text) * FONT_W
        pyxel.text(SCREEN_W // 2 - bw // 2, 112, best_text, GRAY)

        combo_text = f"MAX COMBO: x{self.max_combo}"
        cw = len(combo_text) * FONT_W
        pyxel.text(SCREEN_W // 2 - cw // 2, 130, combo_text, YELLOW)

        if self.heat >= HEAT_MAX:
            reason = "OVERHEAT!"
        else:
            reason = "TIME'S UP!"
        rw = len(reason) * FONT_W
        pyxel.text(SCREEN_W // 2 - rw // 2, 158, reason, RED)

        if (pyxel.frame_count // 30) % 2 == 0:
            retry = "PRESS ENTER TO RETRY"
            rtw = len(retry) * FONT_W
            pyxel.text(SCREEN_W // 2 - rtw // 2, 190, retry, YELLOW)

    def _draw_playing(self) -> None:
        self._draw_grid()
        self._draw_holds()
        self._draw_player()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_grid(self) -> None:
        for c in range(COLS + 1):
            x = GRID_X + c * CELL
            pyxel.line(x, GRID_Y, x, GRID_Y + ROWS * CELL, NAVY)
        for r in range(ROWS + 1):
            y = GRID_Y + r * CELL
            pyxel.line(GRID_X, y, GRID_X + COLS * CELL, y, NAVY)

    def _draw_holds(self) -> None:
        hold_size = CELL - 4
        offset = 2
        for h in self.holds:
            x = GRID_X + h.col * CELL + offset
            y = GRID_Y + h.row * CELL + offset
            pyxel.rect(x, y, hold_size, hold_size, h.color)
            pyxel.rectb(x, y, hold_size, hold_size, WHITE)

    def _draw_player(self) -> None:
        visible = (pyxel.frame_count % (BLINK_VISIBLE + BLINK_HIDDEN)) < BLINK_VISIBLE
        if not visible:
            return

        px = GRID_X + self.player_col * CELL + 1
        py = GRID_Y + self.player_row * CELL + 1
        size = CELL - 2

        if self.super_mode:
            color = COLORS[(pyxel.frame_count // 10) % len(COLORS)]
        else:
            color = COLORS[self.player_color_idx]

        pyxel.rectb(px, py, size, size, color)
        pyxel.rectb(px + 1, py + 1, size - 2, size - 2, color)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 25.0
            color = p.color if alpha > 0.3 else GRAY
            pyxel.pset(int(p.x), int(p.y), color)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / FLOAT_TEXT_LIFE
            if alpha < 0.15:
                continue
            color = ft.color if alpha > 0.3 else GRAY
            tw = len(ft.text) * FONT_W
            pyxel.text(int(ft.x) - tw // 2, int(ft.y), ft.text, color)

    def _draw_hud(self) -> None:
        score_text = f"SCORE:{self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_text) * FONT_W // 2, 2, score_text, WHITE)

        if self.combo > 1:
            combo_text = f"COMBO x{self.combo}"
            combo_color = RED if self.combo >= COMBO_SUPER_THRESHOLD else YELLOW
            pyxel.text(SCREEN_W // 2 - len(combo_text) * FONT_W // 2, FONT_H + 2, combo_text, combo_color)

        if self.super_mode:
            super_text = f"SUPER GRIP! {self.super_timer // FPS + 1}s"
            super_color = COLORS[(pyxel.frame_count // 10) % len(COLORS)]
            pyxel.text(SCREEN_W // 2 - len(super_text) * FONT_W // 2, FONT_H * 2 + 4, super_text, super_color)

        self._draw_heat_bar()
        self._draw_timer_bar()

        player_color_text = "COLOR:"
        pyxel.text(4, SCREEN_H - FONT_H - 2, player_color_text, GRAY)
        pc = COLORS[self.player_color_idx]
        pyxel.rect(4 + len(player_color_text) * FONT_W + 2, SCREEN_H - FONT_H, 10, 10, pc)

    def _draw_heat_bar(self) -> None:
        bar_w = 160
        bar_h = 8
        bar_x = 8
        bar_y = FONT_H + 2

        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        fill_w = int(bar_w * (self.heat / HEAT_MAX))
        if self.heat < 33:
            heat_c = GREEN
        elif self.heat < 66:
            heat_c = YELLOW
        else:
            heat_c = RED
        if fill_w > 0:
            pyxel.rect(bar_x, bar_y, fill_w, bar_h, heat_c)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)

        heat_label = "HEAT"
        pyxel.text(bar_x + bar_w + 4, bar_y - 1, heat_label, GRAY)

    def _draw_timer_bar(self) -> None:
        bar_w = 120
        bar_h = 6
        bar_x = SCREEN_W - bar_w - 8
        bar_y = FONT_H + 3

        pyxel.rect(bar_x, bar_y, bar_w, bar_h, GRAY)
        fill_w = int(bar_w * (self.timer / GAME_DURATION))
        if fill_w > 0:
            pyxel.rect(bar_x, bar_y, fill_w, bar_h, CYAN)
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, WHITE)

        time_label = f"{self.timer // FPS}s"
        pyxel.text(bar_x - len(time_label) * FONT_W - 4, bar_y - 2, time_label, WHITE)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
class App:
    """Pyxel entry point -- wires input to Game."""

    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="GRIP CHAIN", display_scale=2, fps=FPS)
        if FONT_PATH.exists():
            pyxel.load(str(FONT_PATH))
        self.game = Game()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        g = self.game

        if g.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_RETURN):
                g.reset()
        elif g.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN):
                g.reset()
        elif g.phase == Phase.PLAYING:
            if pyxel.btnp(pyxel.KEY_UP):
                g._try_move(0, -1)
            elif pyxel.btnp(pyxel.KEY_DOWN):
                g._try_move(0, 1)
            elif pyxel.btnp(pyxel.KEY_LEFT):
                g._try_move(-1, 0)
            elif pyxel.btnp(pyxel.KEY_RIGHT):
                g._try_move(1, 0)

            g.update()

    def draw(self) -> None:
        g = self.game

        if g._shake_frames > 0 and g.phase == Phase.PLAYING:
            sx = g.rng.randint(-2, 2)
            sy = g.rng.randint(-2, 2)
        else:
            sx = 0
            sy = 0

        if sx != 0 or sy != 0:
            pyxel.camera(sx, sy)
            g.draw()
            pyxel.camera(0, 0)
        else:
            g.draw()


def main() -> None:
    App()


if __name__ == "__main__":
    main()
