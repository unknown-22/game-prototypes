"""
SEED SURGE — Mancala-style color-match COMBO chain game.
Prototype #183.

Core fun: Chain-capturing same-color pits across the board feels like a cascade explosion.
Risk/reward: Matching colors builds COMBO for huge scores; mismatching builds HEAT toward game over.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any

import pyxel


# ── Constants ───────────────────────────────────────────────────────────────

SCREEN_W = 320
SCREEN_H = 240
FONT_PATH = Path(__file__).with_name("k8x12.bdf")

# Colors (Pyxel 16-color palette)
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

SEED_COLORS = [RED, GREEN, LIGHT_BLUE, YELLOW]
SEED_COLOR_NAMES = ["RED", "GREEN", "BLUE", "YELLOW"]

PITS_PER_ROW = 6
NUM_ROWS = 2
PIT_SIZE = 30
PIT_GAP = 10
BOARD_LEFT = 28
BOARD_TOP_AI = 32
BOARD_TOP_PLAYER = 138
STORE_W = 36
STORE_H = 80

INITIAL_SEEDS_PER_PIT = 4
HEAT_MAX = 100.0
HEAT_DECAY = 0.5
HEAT_WRONG_CAPTURE = 15.0
SUPER_SOW_THRESHOLD = 4
SUPER_SOW_DURATION = 60
FLOAT_TEXT_LIFE = 30


# ── Data Classes ────────────────────────────────────────────────────────────


@dataclass
class Pit:
    seeds: int
    color: int  # 0-3 index into SEED_COLORS


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: int
    color: int


@dataclass
class FloatText:
    x: float
    y: float
    text: str
    life: int
    color: int


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


# ── Game Class ──────────────────────────────────────────────────────────────


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="SEED SURGE", display_scale=2)
        self._rng = random.Random()
        self.board: list[list[Pit]] = []
        self.stores: list[int] = [0, 0]
        self.player_turn: bool = True
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: float = 0.0
        self.score: int = 0
        self.turn_count: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatText] = []
        self.last_capture_color: int = -1
        self.super_sow_timer: int = 0
        self.phase: Phase = Phase.TITLE
        self.game_over_reason: str = ""
        self._sow_anim: list[dict[str, Any]] = []
        self._sow_anim_start_color: int = -1
        self._anim_timer: int = 0
        self._hovered_col: int = -1

        self._font: pyxel.Font | None = None
        if FONT_PATH.exists():
            self._font = pyxel.Font(str(FONT_PATH))

        self.reset()
        pyxel.run(self.update, self.draw)

    # ── Reset ───────────────────────────────────────────────────────────

    def reset(self) -> None:
        self.board = [
            [Pit(seeds=INITIAL_SEEDS_PER_PIT, color=self._rng.randint(0, 3)) for _ in range(PITS_PER_ROW)]
            for _ in range(NUM_ROWS)
        ]
        self.stores = [0, 0]
        self.player_turn = True
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.score = 0
        self.turn_count = 0
        self.last_capture_color = -1
        self.super_sow_timer = 0
        self.particles.clear()
        self.floating_texts.clear()
        self._sow_anim.clear()
        self._sow_anim_start_color = -1
        self._anim_timer = 0
        self._hovered_col = -1

    # ── Update ──────────────────────────────────────────────────────────

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.phase = Phase.PLAYING
            self.reset()

    def _update_playing(self) -> None:
        self._update_particles()
        self._update_floating_texts()

        if self.super_sow_timer > 0:
            self.super_sow_timer -= 1
            if self.super_sow_timer == 0:
                self._finish_turn()

        if self._anim_timer > 0:
            self._anim_timer -= 1
            if self._anim_timer == 0:
                self._process_sow_result()
            return

        if self.player_turn:
            self._hovered_col = self._find_hovered_pit()
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and self._hovered_col >= 0:
                self._handle_player_click(self._hovered_col)
        else:
            self._ai_turn()

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.phase = Phase.PLAYING
            self.reset()

    # ── Pit geometry ────────────────────────────────────────────────────

    def _get_pit_center(self, row: int, col: int) -> tuple[float, float]:
        x = BOARD_LEFT + 10 + col * (PIT_SIZE + PIT_GAP) + PIT_SIZE // 2
        y = (BOARD_TOP_AI if row == 0 else BOARD_TOP_PLAYER) + PIT_SIZE // 2
        return float(x), float(y)

    def _get_store_center(self, row: int) -> tuple[float, float]:
        x = BOARD_LEFT + PITS_PER_ROW * (PIT_SIZE + PIT_GAP) + 25
        y = (BOARD_TOP_AI if row == 0 else BOARD_TOP_PLAYER) + PIT_SIZE // 2
        return float(x), float(y)

    def _pit_at_pos(self, mx: int, my: int) -> int | None:
        """Return col index of player pit under mouse, or None."""
        for col in range(PITS_PER_ROW):
            cx, cy = self._get_pit_center(1, col)
            if math.hypot(mx - cx, my - cy) <= PIT_SIZE // 2:
                return col
        return None

    def _find_hovered_pit(self) -> int:
        col = self._pit_at_pos(pyxel.mouse_x, pyxel.mouse_y)
        if col is not None and self.board[1][col].seeds > 0:
            return col
        return -1

    # ── Player action ───────────────────────────────────────────────────

    def _handle_player_click(self, col: int) -> None:
        if self.board[1][col].seeds == 0:
            return
        start_color = self.board[1][col].color
        self._start_sow(1, col, start_color)

    def _start_sow(self, row: int, col: int, start_color: int) -> None:
        seeds = self.board[row][col].seeds
        self.board[row][col].seeds = 0
        path = self._build_sow_path(row, col, seeds)
        self._sow_anim = [
            {"row": p[0], "col": p[1], "is_store": p[2]} for p in path
        ]
        self._sow_anim_start_color = start_color
        self._anim_timer = min(seeds * 4, 40)

    def _build_sow_path(self, row: int, col: int, seeds: int) -> list[tuple[int, int, bool]]:
        """Build full path of positions for sowing, repeating if needed."""
        single_path: list[tuple[int, int, bool]] = []
        if row == 1:  # Player: go right, store, top row right-to-left, store, loop
            for c in range(col + 1, PITS_PER_ROW):
                single_path.append((1, c, False))
            single_path.append((1, -1, True))  # Player store
            for c in range(PITS_PER_ROW - 1, -1, -1):
                single_path.append((0, c, False))
            single_path.append((0, -1, True))  # AI store
            for c in range(0, col):
                single_path.append((1, c, False))
        else:  # AI: go left, store, bottom row left-to-right, store, loop
            for c in range(col - 1, -1, -1):
                single_path.append((0, c, False))
            single_path.append((0, -1, True))  # AI store
            for c in range(0, PITS_PER_ROW):
                single_path.append((1, c, False))
            single_path.append((1, -1, True))  # Player store
            for c in range(PITS_PER_ROW - 1, col, -1):
                single_path.append((0, c, False))

        result: list[tuple[int, int, bool]] = []
        for i in range(seeds):
            idx = i % len(single_path)
            result.append(single_path[idx])
        return result

    def _process_sow_result(self) -> None:
        """After sowing animation, determine capture result."""
        last = self._sow_anim[-1] if self._sow_anim else None

        # Add seeds to pits (skip stores)
        for step in self._sow_anim:
            if not step["is_store"]:
                self.board[step["row"]][step["col"]].seeds += 1

        if last is None or last["is_store"]:
            self._finish_turn()
            return

        landing_row = last["row"]
        landing_col = last["col"]
        landing_color = self.board[landing_row][landing_col].color
        start_color = self._sow_anim_start_color
        is_player = self.player_turn
        player_row = 1 if is_player else 0

        if landing_color == start_color:
            captured = self._capture(landing_row, landing_col, player_row)
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            self.last_capture_color = start_color
            bonus = captured * self.combo * 10
            self.score += bonus

            cx, cy = self._get_pit_center(landing_row, landing_col)
            self._spawn_particles(cx, cy, 10, SEED_COLORS[start_color])
            self._spawn_float_text(cx, cy - 8, f"+{bonus}", LIME)
            if self.combo > 1:
                self._spawn_float_text(cx, cy - 20, f"COMBO x{self.combo}!", YELLOW)

            if self.combo >= SUPER_SOW_THRESHOLD:
                self._trigger_super_sow(landing_row, landing_col, player_row)
            else:
                self._finish_turn()
        else:
            self.combo = 0
            self.heat = min(self.heat + HEAT_WRONG_CAPTURE, HEAT_MAX)
            self.last_capture_color = -1
            cx, cy = self._get_pit_center(landing_row, landing_col)
            self._spawn_float_text(cx, cy - 8, "MISS!", RED)
            self._finish_turn()

    def _capture(self, row: int, col: int, capturing_player_row: int) -> int:
        """Capture seeds from landing pit and opposite pit. Returns total captured."""
        total = self.board[row][col].seeds
        self.board[row][col].seeds = 0

        opp_row = 1 - row
        total += self.board[opp_row][col].seeds
        self.board[opp_row][col].seeds = 0

        self.stores[capturing_player_row] += total
        return total

    def _trigger_super_sow(self, row: int, col: int, capturing_player_row: int) -> None:
        """Find adjacent same-color pits and auto-capture them."""
        color_idx = self.board[row][col].color  # 0-3 index
        neighbors = self._find_adjacent_same_color(row, col, color_idx)
        self.super_sow_timer = SUPER_SOW_DURATION

        for nr, nc in neighbors:
            if self.board[nr][nc].seeds > 0:
                captured = self._capture(nr, nc, capturing_player_row)
                self.score += captured * self.combo * 5
                cx, cy = self._get_pit_center(nr, nc)
                self._spawn_particles(cx, cy, 6, SEED_COLORS[color_idx])

        cx, cy = self._get_pit_center(row, col)
        self._spawn_float_text(cx, cy - 32, "SUPER!", ORANGE)
        self._spawn_particles(cx, cy, 25, SEED_COLORS[color_idx])

    def _find_adjacent_same_color(self, row: int, col: int, color_idx: int) -> list[tuple[int, int]]:
        """Find pits adjacent (up/down/left/right in grid) with same color."""
        result: list[tuple[int, int]] = []
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        for dr, dc in directions:
            nr, nc = row + dr, col + dc
            if 0 <= nr < NUM_ROWS and 0 <= nc < PITS_PER_ROW:
                if self.board[nr][nc].color == color_idx and self.board[nr][nc].seeds > 0:
                    result.append((nr, nc))
        return result

    # ── AI ───────────────────────────────────────────────────────────────

    def _ai_turn(self) -> None:
        move = self._ai_pick_pit()
        if move is None:
            self._finish_turn()
            return

        ai_row, ai_col = move
        start_color = self.board[ai_row][ai_col].color
        self._start_sow(ai_row, ai_col, start_color)

    def _ai_pick_pit(self) -> tuple[int, int] | None:
        """Pick best AI pit. Prefer same-color counter-pick, else most seeds."""
        ai_row = 0
        valid = [(ai_row, c) for c in range(PITS_PER_ROW) if self.board[ai_row][c].seeds > 0]
        if not valid:
            return None

        # Prefer pits matching player's last capture color
        if self.last_capture_color >= 0:
            matching = [
                (r, c) for r, c in valid
                if self.board[r][c].color == self.last_capture_color
            ]
            if matching:
                return matching[self._rng.randint(0, len(matching) - 1)]

        # Otherwise pick pit with most seeds
        max_seeds = max(self.board[r][c].seeds for r, c in valid)
        best = [(r, c) for r, c in valid if self.board[r][c].seeds == max_seeds]
        return best[self._rng.randint(0, len(best) - 1)]

    def _finish_turn(self) -> None:
        """End current turn and check game over / switch turns."""
        if self._check_game_over():
            return

        if self.player_turn:
            self.player_turn = False
        else:
            self.player_turn = True
            self.heat = max(0.0, self.heat - HEAT_DECAY)
            self.turn_count += 1

        self._sow_anim.clear()
        self._anim_timer = 0

    def _check_game_over(self) -> bool:
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            self.game_over_reason = "Overheated!"
            return True

        player_empty = all(p.seeds == 0 for p in self.board[1])
        ai_empty = all(p.seeds == 0 for p in self.board[0])
        if player_empty or ai_empty:
            self.phase = Phase.GAME_OVER
            self.game_over_reason = "Board Empty!"
            # Award remaining seeds to the player with seeds
            if not player_empty:
                self.stores[1] += sum(p.seeds for p in self.board[1])
            elif not ai_empty:
                self.stores[0] += sum(p.seeds for p in self.board[0])
            self.score += self.stores[1] * 5
            return True

        return False

    # ── Particles ───────────────────────────────────────────────────────

    def _spawn_particles(self, x: float, y: float, count: int, color: int) -> None:
        for _ in range(count):
            vx = self._rng.uniform(-2.5, 2.5)
            vy = self._rng.uniform(-4.0, -1.0)
            life = self._rng.randint(12, 28)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.12
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    # ── Floating texts ──────────────────────────────────────────────────

    def _spawn_float_text(self, x: float, y: float, text: str, color: int) -> None:
        self.floating_texts.append(FloatText(x=x, y=y, text=text, life=FLOAT_TEXT_LIFE, color=color))

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.8
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ── Text helpers ────────────────────────────────────────────────────

    def _draw_text(self, x: float, y: float, s: str, col: int) -> None:
        if self._font is not None:
            pyxel.text(int(x) + 1, int(y) + 1, s, BLACK, self._font)
            pyxel.text(int(x), int(y), s, col, self._font)
        else:
            pyxel.text(int(x), int(y), s, col)

    def _text_width(self, s: str) -> int:
        if self._font is not None:
            return self._font.text_width(s)
        return len(s) * 4

    # ── Draw ────────────────────────────────────────────────────────────

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_game()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        title = "SEED SURGE"
        self._draw_text(SCREEN_W // 2 - self._text_width(title) // 2, 60, title, YELLOW)

        subtitle = "Mancala Color-Combo Chain"
        self._draw_text(SCREEN_W // 2 - self._text_width(subtitle) // 2, 78, subtitle, GRAY)

        if (pyxel.frame_count // 30) % 2 == 0:
            cts = "Click to Start"
            self._draw_text(SCREEN_W // 2 - self._text_width(cts) // 2, 120, cts, WHITE)

        controls = [
            "Click your pit to sow seeds",
            "Match colors for COMBO chain!",
            "COMBO x4 = SUPER SOW!",
            "Mismatch builds HEAT -> Game Over",
        ]
        for i, line in enumerate(controls):
            self._draw_text(SCREEN_W // 2 - self._text_width(line) // 2, 150 + i * 12, line, GRAY)

    def _draw_game(self) -> None:
        self._draw_board()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

    def _draw_game_over(self) -> None:
        go_text = "GAME OVER"
        self._draw_text(SCREEN_W // 2 - self._text_width(go_text) // 2, 60, go_text, RED)
        self._draw_text(SCREEN_W // 2 - self._text_width(self.game_over_reason) // 2, 80, self.game_over_reason, ORANGE)

        score_text = f"Score: {self.score}"
        self._draw_text(SCREEN_W // 2 - self._text_width(score_text) // 2, 100, score_text, WHITE)

        combo_text = f"Max Combo: x{self.max_combo}"
        self._draw_text(SCREEN_W // 2 - self._text_width(combo_text) // 2, 114, combo_text, YELLOW)

        store_text = f"Seeds Captured: {self.stores[1]}"
        self._draw_text(SCREEN_W // 2 - self._text_width(store_text) // 2, 128, store_text, GRAY)

        if (pyxel.frame_count // 30) % 2 == 0:
            ctr = "Click to Restart"
            self._draw_text(SCREEN_W // 2 - self._text_width(ctr) // 2, 170, ctr, WHITE)

    def _draw_board(self) -> None:
        # Background
        pyxel.rectb(10, 10, SCREEN_W - 20, SCREEN_H - 40, BROWN)

        # Draw AI pits (row 0)
        for col in range(PITS_PER_ROW):
            self._draw_pit(0, col)

        # Draw Player pits (row 1)
        for col in range(PITS_PER_ROW):
            self._draw_pit(1, col)

        # Draw stores
        self._draw_store(0)
        self._draw_store(1)

        # Draw labels
        self._draw_text(12, 12, "AI", GRAY)
        self._draw_text(12, BOARD_TOP_PLAYER - 10, "YOU", WHITE)

    def _draw_pit(self, row: int, col: int) -> None:
        cx, cy = self._get_pit_center(row, col)
        pit = self.board[row][col]
        color_val = SEED_COLORS[pit.color]

        # Highlight hovered pit
        is_hovered = self.player_turn and row == 1 and col == self._hovered_col
        if is_hovered:
            pyxel.circb(int(cx), int(cy), PIT_SIZE // 2 + 2, WHITE)

        # Pit circle
        pyxel.circb(int(cx), int(cy), PIT_SIZE // 2, DARK_BLUE if not is_hovered else NAVY)
        pyxel.circ(int(cx), int(cy), PIT_SIZE // 2, color_val)

        # Seed count
        count_text = str(pit.seeds)
        text_x = int(cx) - self._text_width(count_text) // 2
        text_y = int(cy) - 4
        self._draw_text(text_x, text_y, count_text, WHITE)

        # Color dot
        pyxel.circb(int(cx) + 8, int(cy) - 8, 3, color_val)

    def _draw_store(self, row: int) -> None:
        sx, sy = self._get_store_center(row)
        x = int(sx) - STORE_W // 2
        y = int(sy) - STORE_H // 2
        store_color = SEED_COLORS[(self.stores[row] // 5) % 4] if self.stores[row] > 0 else GRAY

        pyxel.rectb(x, y, STORE_W, STORE_H, WHITE)
        pyxel.rect(x + 1, y + 1, STORE_W - 2, STORE_H - 2, DARK_BLUE)

        count_text = str(self.stores[row])
        self._draw_text(int(sx) - self._text_width(count_text) // 2, int(sy) - 4, count_text, store_color)

    def _draw_hud(self) -> None:
        # Combo display
        if self.combo > 0:
            combo_text = f"COMBO x{self.combo}"
            color = YELLOW if self.combo < SUPER_SOW_THRESHOLD else ORANGE
            self._draw_text(SCREEN_W - self._text_width(combo_text) - 8, 8, combo_text, color)

        # Super sow indicator
        if self.super_sow_timer > 0:
            if (pyxel.frame_count // 4) % 2 == 0:
                ss_text = "SUPER SOW!"
                self._draw_text(SCREEN_W // 2 - self._text_width(ss_text) // 2, 8, ss_text, ORANGE)

        # Score
        score_text = f"SCORE: {self.score}"
        self._draw_text(SCREEN_W - self._text_width(score_text) - 8, 22, score_text, WHITE)

        # Turn indicator
        if self.player_turn:
            turn_text = "YOUR TURN"
            self._draw_text(SCREEN_W // 2 - self._text_width(turn_text) // 2, SCREEN_H - 16, turn_text, LIME)
        else:
            turn_text = "AI TURN..."
            self._draw_text(SCREEN_W // 2 - self._text_width(turn_text) // 2, SCREEN_H - 16, turn_text, GRAY)

        # Heat bar
        self._draw_heat_bar()

    def _draw_heat_bar(self) -> None:
        bar_x = 10
        bar_y = SCREEN_H - 26
        bar_w = 140
        bar_h = 8

        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, GRAY)

        heat_ratio = self.heat / HEAT_MAX
        fill_w = int(bar_w * heat_ratio)
        heat_color = GREEN if heat_ratio < 0.4 else YELLOW if heat_ratio < 0.7 else RED
        if fill_w > 0:
            pyxel.rect(bar_x + 1, bar_y + 1, fill_w - 1, bar_h - 2, heat_color)

        self._draw_text(bar_x + bar_w + 4, bar_y - 1, "HEAT", GRAY)

    def _draw_particles(self) -> None:
        for p in self.particles:
            alpha = p.life / 28.0
            col = p.color if alpha > 0.5 else GRAY
            pyxel.pset(int(p.x), int(p.y), col)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / FLOAT_TEXT_LIFE
            col = ft.color if alpha > 0.3 else GRAY
            self._draw_text(int(ft.x) - self._text_width(ft.text) // 2, int(ft.y), ft.text, col)


if __name__ == "__main__":
    Game()
