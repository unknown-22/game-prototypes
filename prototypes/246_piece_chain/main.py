"""Piece Chain — Color-Match Jigsaw Puzzle

Same-color consecutive placements build a COMBO chain.
COMBO >= 4 triggers SUPER SOLVE — a rainbow cascade of auto-placements.
Wrong placements raise HEAT. Place all 12 pieces before timer or HEAT runs out.
"""

from __future__ import annotations

import enum
import random
from dataclasses import dataclass

import pyxel

SCREEN_W = 320
SCREEN_H = 240
CELL = 40
GAP = 2
GRID_LEFT = 40
GRID_TOP = 30
GRID_COLS = 4
GRID_ROWS = 3
TOTAL_PIECES = GRID_COLS * GRID_ROWS

TRAY_LEFT = 210
TRAY_TOP = 20
TRAY_WIDTH = 100
TRAY_ITEM_SIZE = 36
TRAY_ITEM_GAP = 4

FPS = 60
PLAY_TIME = 60 * FPS
SUPER_DURATION = 300
SUPER_AUTO_INTERVAL = 60

COLOR_RED = 8
COLOR_LIME = 11
COLOR_DARK_BLUE = 5
COLOR_YELLOW = 10
PLAYER_COLORS = (COLOR_RED, COLOR_LIME, COLOR_DARK_BLUE, COLOR_YELLOW)

HEAT_WRONG = 15.0
HEAT_DECAY = 0.02
HEAT_MAX = 100.0

PACKAGE_DIR = __file__


class Phase(enum.Enum):
    TITLE = enum.auto()
    PLAYING = enum.auto()
    GAME_OVER = enum.auto()
    VICTORY = enum.auto()


@dataclass
class Piece:
    color: int
    target_col: int
    target_row: int
    x: float = 0.0
    y: float = 0.0
    placed: bool = False
    tray_index: int = 0


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
    color: int = 7


class Game:
    def __init__(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.timer: int = PLAY_TIME
        self.heat: float = 0.0
        self.pieces: list[Piece] = []
        self.slots: list[list[int | None]] = []
        self.selected_piece: Piece | None = None
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.last_placed_color: int | None = None
        self.placed_count: int = 0
        self._rng = random.Random(42)
        self._tray_scroll: int = 0
        self._screen_shake: int = 0

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.timer = PLAY_TIME
        self.heat = 0.0
        self.selected_piece = None
        self.super_mode = False
        self.super_timer = 0
        self.particles.clear()
        self.floating_texts.clear()
        self.last_placed_color = None
        self.placed_count = 0
        self._tray_scroll = 0
        self._screen_shake = 0

        self.pieces = []
        r = self._rng
        colors_pool: list[int] = []
        for c in PLAYER_COLORS:
            colors_pool.extend([c] * 3)
        r.shuffle(colors_pool)

        slots_list = []
        for col in range(GRID_COLS):
            for row in range(GRID_ROWS):
                slots_list.append((col, row))
        r.shuffle(slots_list)

        for i in range(TOTAL_PIECES):
            col, row = slots_list[i]
            piece = Piece(
                color=colors_pool[i],
                target_col=col,
                target_row=row,
                tray_index=i,
            )
            self.pieces.append(piece)

        self.slots = [[None for _ in range(GRID_ROWS)] for _ in range(GRID_COLS)]

    def _get_slot_rect(self, col: int, row: int) -> tuple[int, int, int, int]:
        x = GRID_LEFT + col * (CELL + GAP)
        y = GRID_TOP + row * (CELL + GAP)
        return (x, y, CELL, CELL)

    def _check_click_slot(self, mx: int, my: int) -> tuple[int, int] | None:
        for col in range(GRID_COLS):
            for row in range(GRID_ROWS):
                x, y, w, h = self._get_slot_rect(col, row)
                if x <= mx < x + w and y <= my < y + h:
                    return (col, row)
        return None

    def _check_click_tray(self, mx: int, my: int) -> Piece | None:
        if mx < TRAY_LEFT or mx > TRAY_LEFT + TRAY_WIDTH:
            return None
        unplaced = [p for p in self.pieces if not p.placed]
        for i, piece in enumerate(unplaced):
            py = TRAY_TOP + i * (TRAY_ITEM_SIZE + TRAY_ITEM_GAP) - self._tray_scroll
            if py <= my < py + TRAY_ITEM_SIZE:
                return piece
        return None

    def _try_place(self, col: int, row: int) -> bool:
        piece = self.selected_piece
        if piece is None:
            return False

        if self.slots[col][row] is not None:
            return False

        expected_color = [
            p for p in self.pieces if p.target_col == col and p.target_row == row
        ][0].color

        # In super mode, any piece matches any slot
        is_match = self.super_mode or (piece.color == expected_color)

        if is_match:
            if piece.color == self.last_placed_color or self.super_mode:
                self.combo += 1
            else:
                self.combo = 1

            if self.combo > self.max_combo:
                self.max_combo = self.combo

            multiplier = 3 if self.super_mode else 1
            points = 10 * self.combo * multiplier
            self.score += points

            self.slots[col][row] = piece.color
            piece.placed = True
            self.placed_count += 1
            self.last_placed_color = piece.color

            slot_x, slot_y, _, _ = self._get_slot_rect(col, row)
            cx = slot_x + CELL // 2
            cy = slot_y + CELL // 2

            self._spawn_particles(cx, cy, piece.color, 10)
            self._spawn_floating_text(cx, cy - 5, f"+{points}", 7, 30)

            if self.combo >= 2:
                self._spawn_floating_text(
                    cx, cy + 10, f"COMBO x{self.combo}!", COLOR_YELLOW, 25
                )

            if self.combo >= 3 and not self.super_mode:
                self.super_mode = True
                self.super_timer = SUPER_DURATION
                grid_cx = GRID_LEFT + GRID_COLS * (CELL + GAP) // 2 - GAP
                grid_cy = GRID_TOP + GRID_ROWS * (CELL + GAP) // 2 - GAP
                self._spawn_floating_text(
                    grid_cx,
                    grid_cy,
                    "SUPER SOLVE!",
                    COLOR_YELLOW,
                    40,
                )

            if self.placed_count >= TOTAL_PIECES:
                self.phase = Phase.VICTORY

            return True
        else:
            self.heat = min(HEAT_MAX, self.heat + HEAT_WRONG)
            self.combo = 0
            self.last_placed_color = None
            self._screen_shake = 8

            slot_x, slot_y, _, _ = self._get_slot_rect(col, row)
            cx = slot_x + CELL // 2
            cy = slot_y + CELL // 2
            self._spawn_floating_text(cx, cy, "WRONG!", COLOR_RED, 20)

            return False

    def _spawn_particles(self, x: float, y: float, color: int, count: int) -> None:
        r = self._rng
        for _ in range(count):
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=r.uniform(-1.5, 1.5),
                    vy=r.uniform(-1.5, 1.5),
                    life=r.randint(15, 25),
                    color=color,
                )
            )

    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int, life: int
    ) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=life, color=color)
        )

    def _update_particles(self) -> None:
        remaining: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                remaining.append(p)
        self.particles = remaining

    def _update_floating_texts(self) -> None:
        remaining: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
            if ft.life > 0:
                remaining.append(ft)
        self.floating_texts = remaining

    def _update_heat(self) -> None:
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _draw_heat_bar(self) -> None:
        bar_x = 160
        bar_y = 4
        bar_w = 80
        bar_h = 6

        pyxel.rect(bar_x, bar_y, bar_w, bar_h, 13)
        fill_w = int(self.heat / HEAT_MAX * bar_w)
        if fill_w > 0:
            if self.heat < 40:
                bar_color = COLOR_LIME
            elif self.heat < 70:
                bar_color = COLOR_YELLOW
            else:
                bar_color = COLOR_RED
            pyxel.rect(bar_x, bar_y, fill_w, bar_h, bar_color)

    def _draw_grid(self) -> None:
        for col in range(GRID_COLS):
            for row in range(GRID_ROWS):
                x, y, w, h = self._get_slot_rect(col, row)
                expected = [
                    p
                    for p in self.pieces
                    if p.target_col == col and p.target_row == row
                ][0]
                slot_color = self.slots[col][row]
                if slot_color is not None:
                    pyxel.rect(x, y, w, h, slot_color)
                    pyxel.rectb(x, y, w, h, 7)
                else:
                    pyxel.rectb(x, y, w, h, expected.color)
                    pyxel.rectb(x + 1, y + 1, w - 2, h - 2, 13)

        if self.super_mode:
            border_color = (pyxel.frame_count % 16) + 1
            if border_color > 15:
                border_color = border_color % 16
            grid_right = GRID_LEFT + GRID_COLS * (CELL + GAP) - GAP
            grid_bottom = GRID_TOP + GRID_ROWS * (CELL + GAP) - GAP
            pyxel.rectb(
                GRID_LEFT - 3,
                GRID_TOP - 3,
                grid_right - GRID_LEFT + 6,
                grid_bottom - GRID_TOP + 6,
                border_color,
            )

    def _draw_tray(self) -> None:
        unplaced = [p for p in self.pieces if not p.placed]
        for i, piece in enumerate(unplaced):
            py = TRAY_TOP + i * (TRAY_ITEM_SIZE + TRAY_ITEM_GAP) - self._tray_scroll
            if py + TRAY_ITEM_SIZE < TRAY_TOP or py > SCREEN_H:
                continue
            px = TRAY_LEFT + 2
            pyxel.rect(px, py, TRAY_ITEM_SIZE, TRAY_ITEM_SIZE, piece.color)
            if piece is self.selected_piece:
                pyxel.rectb(px - 1, py - 1, TRAY_ITEM_SIZE + 2, TRAY_ITEM_SIZE + 2, 7)

    def _draw_particles(self) -> None:
        for p in self.particles:
            if p.life >= 5:
                shade = p.color if p.life > 12 else 13
                pyxel.rect(int(p.x), int(p.y), 2, 2, shade)

    def _draw_floating_texts(self) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 30.0
            if alpha > 0.2:
                pyxel.text(
                    int(ft.x - len(ft.text) * 2),
                    int(ft.y),
                    ft.text,
                    ft.color,
                )

    def _draw_hud(self) -> None:
        pyxel.text(4, 4, f"SCORE:{self.score}", 7)
        pyxel.text(4, 14, f"COMBO:{self.combo}", 7)
        seconds = max(0, self.timer // 60)
        pyxel.text(4, 24, f"TIME:{seconds}", 7)
        self._draw_heat_bar()
        pyxel.text(242, 3, "HEAT", 7)
        placed_text = f"PIECES:{self.placed_count}/{TOTAL_PIECES}"
        pyxel.text(210, 220, placed_text, 7)

    def _draw_title(self) -> None:
        pyxel.cls(0)
        pyxel.text(110, 60, "PIECE CHAIN", 7)
        pyxel.text(100, 90, "Color-Match Puzzle", 13)
        pyxel.text(75, 130, "Place same-color pieces", 7)
        pyxel.text(65, 140, "consecutively to build COMBO!", 7)
        pyxel.text(60, 155, "COMBO x3 = SUPER SOLVE!", COLOR_YELLOW)
        pyxel.text(100, 190, "Click a piece in tray,", 7)
        pyxel.text(85, 200, "then click matching slot", 7)
        pyxel.text(95, 220, "Press ENTER to Start", COLOR_LIME)

    def _draw_game_over(self) -> None:
        pyxel.cls(0)
        reason = "TIME UP!" if self.timer <= 0 else "OVERHEAT!"
        pyxel.text(120, 60, "GAME OVER", COLOR_RED)
        pyxel.text(125, 80, reason, 7)
        pyxel.text(100, 110, f"SCORE: {self.score}", 7)
        pyxel.text(90, 125, f"MAX COMBO: {self.max_combo}", COLOR_YELLOW)
        pyxel.text(90, 150, f"PIECES: {self.placed_count}/{TOTAL_PIECES}", 7)
        pyxel.text(80, 200, "Press R to Restart", COLOR_LIME)

    def _draw_victory(self) -> None:
        pyxel.cls(1)
        pyxel.text(85, 70, "PUZZLE COMPLETE!", COLOR_YELLOW)
        pyxel.text(100, 105, f"SCORE: {self.score}", 7)
        pyxel.text(90, 120, f"MAX COMBO: {self.max_combo}", COLOR_YELLOW)
        pyxel.text(80, 200, "Press R to Restart", COLOR_LIME)

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.reset()

    def _update_playing(self) -> None:
        if self._screen_shake > 0:
            self._screen_shake -= 1

        self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER
            return

        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            return

        self._update_heat()

        self._update_particles()
        self._update_floating_texts()

        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
            elif self.super_timer % SUPER_AUTO_INTERVAL == 0:
                unplaced = [p for p in self.pieces if not p.placed]
                if unplaced:
                    auto_piece = self._rng.choice(unplaced)
                    self.selected_piece = auto_piece
                    self._try_place(auto_piece.target_col, auto_piece.target_row)

        wheel = pyxel.mouse_wheel
        if wheel != 0:
            self._tray_scroll = max(
                0, self._tray_scroll - wheel * (TRAY_ITEM_SIZE // 2)
            )

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx = pyxel.mouse_x
            my = pyxel.mouse_y

            if mx >= TRAY_LEFT:
                clicked = self._check_click_tray(mx, my)
                if clicked is not None:
                    self.selected_piece = clicked
                    return

            slot = self._check_click_slot(mx, my)
            if slot is not None:
                self._try_place(slot[0], slot[1])

        if self.placed_count >= TOTAL_PIECES:
            self.phase = Phase.VICTORY

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_R):
            self.reset()

    def _draw_playing(self) -> None:
        shake_x = 0
        shake_y = 0
        if self._screen_shake > 0:
            shake_x = self._rng.randint(-2, 2)
            shake_y = self._rng.randint(-2, 2)

        pyxel.cls(1)
        self._draw_grid()
        self._draw_tray()
        self._draw_particles()
        self._draw_floating_texts()
        self._draw_hud()

        if self.selected_piece is not None and not self.selected_piece.placed:
            mx = pyxel.mouse_x + shake_x
            my = pyxel.mouse_y + shake_y
            pyxel.rect(mx - 18, my - 18, 36, 36, self.selected_piece.color)
            pyxel.rectb(mx - 19, my - 19, 38, 38, 7)

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()
        elif self.phase == Phase.VICTORY:
            if pyxel.btnp(pyxel.KEY_R):
                self.reset()

    def draw(self) -> None:
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()
        elif self.phase == Phase.VICTORY:
            self._draw_victory()


def main() -> None:
    pyxel.init(SCREEN_W, SCREEN_H, title="Piece Chain")
    game = Game()
    pyxel.run(game.update, game.draw)


if __name__ == "__main__":
    main()
