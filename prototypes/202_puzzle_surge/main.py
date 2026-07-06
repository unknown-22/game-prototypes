from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import pyxel


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    VICTORY = auto()
    GAME_OVER = auto()


@dataclass
class SlotDef:
    col: int
    row: int
    color: int
    shape_id: int
    target_piece_id: int
    filled: bool = False
    filled_color: int = 0


@dataclass
class TrayPiece:
    piece_id: int
    color: int
    shape_id: int


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


class Game:
    SCREEN_W = 320
    SCREEN_H = 240
    CELL = 24
    GRID_COLS = 8
    GRID_ROWS = 6
    GRID_X = 56
    GRID_Y = 32
    TRAY_Y = 180
    PIECE_SIZE = 20
    NUM_COLORS = 4
    COLORS = (8, 3, 5, 10)
    SURGE_COMBO_THRESHOLD = 4
    SURGE_DURATION = 300
    MAX_HEAT = 100
    GAME_TIME = 90 * 60
    TRAY_VISIBLE = 5
    TRAY_START_X = 30
    TRAY_SPACING = 60

    def __init__(self) -> None:
        font_path = Path(__file__).with_name("k8x12.bdf")
        if font_path.exists():
            pyxel.load(str(font_path))
        pyxel.init(self.SCREEN_W, self.SCREEN_H, title="PUZZLE SURGE", display_scale=2)
        self._rng = random.Random(42)
        self.reset()
        pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = self.GAME_TIME
        self.surge_mode = False
        self.surge_timer = 0
        self.selected_piece: int | None = None
        self.tray_pieces: list[TrayPiece] = []
        self.slots: list[list[SlotDef]] = []
        self.pieces_total = 0
        self.pieces_placed = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self._shake_frames = 0
        self._tray_scroll = 0
        self._color_filter: int | None = None
        self._timer_bonus = 0
        self._rng = random.Random(42)
        self._generate_puzzle()

    def _generate_puzzle(self) -> None:
        self.slots = []
        for row in range(self.GRID_ROWS):
            row_slots: list[SlotDef] = []
            for col in range(self.GRID_COLS):
                piece_id = row * self.GRID_COLS + col
                color = self.COLORS[piece_id // 12]
                shape_id = piece_id % 3
                row_slots.append(
                    SlotDef(
                        col=col,
                        row=row,
                        color=color,
                        shape_id=shape_id,
                        target_piece_id=piece_id,
                    )
                )
            self.slots.append(row_slots)

        piece_ids = list(range(self.GRID_COLS * self.GRID_ROWS))
        self._rng.shuffle(piece_ids)
        self.tray_pieces = []
        for pid in piece_ids:
            color = self.COLORS[pid // 12]
            shape_id = pid % 3
            self.tray_pieces.append(
                TrayPiece(piece_id=pid, color=color, shape_id=shape_id)
            )

        self.pieces_total = self.GRID_COLS * self.GRID_ROWS
        self.pieces_placed = 0

    def update(self) -> None:
        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase in (Phase.VICTORY, Phase.GAME_OVER):
            self._update_end_screen()

        self._update_particles()
        self._update_floating_texts()
        self._update_shake()

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self._start_game()

    def _update_playing(self) -> None:
        self.timer -= 1
        if self.timer <= 0:
            self._timer_bonus = 0
            self.phase = Phase.GAME_OVER
            return
        if self.heat >= self.MAX_HEAT:
            self._timer_bonus = 0
            self.phase = Phase.GAME_OVER
            return

        self.heat = max(0.0, self.heat - 0.02)

        if self.surge_mode:
            self.surge_timer -= 1
            if self.surge_timer <= 0:
                self.surge_mode = False

        self._handle_input()

        self._clamp_scroll()

        if self.pieces_placed >= self.pieces_total:
            remaining_seconds = self.timer / 60
            self._timer_bonus = int(
                remaining_seconds * 10 * (1 + self.max_combo * 0.2)
            )
            self.score += self._timer_bonus
            self.phase = Phase.VICTORY

    def _update_end_screen(self) -> None:
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.PLAYING

    def _start_game(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat = 0.0
        self.timer = self.GAME_TIME
        self.surge_mode = False
        self.surge_timer = 0
        self.selected_piece = None
        self.pieces_placed = 0
        self.particles.clear()
        self.floating_texts.clear()
        self._shake_frames = 0
        self._tray_scroll = 0
        self._color_filter = None
        self._timer_bonus = 0
        self._rng = random.Random(42)
        self._generate_puzzle()

    def _handle_input(self) -> None:
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.handle_click(pyxel.mouse_x, pyxel.mouse_y)

        for i, key in enumerate(
            [pyxel.KEY_1, pyxel.KEY_2, pyxel.KEY_3, pyxel.KEY_4]
        ):
            if pyxel.btnp(key):
                if self._color_filter == i:
                    self._color_filter = None
                else:
                    self._color_filter = i
                self.selected_piece = None
                self._tray_scroll = 0

        if self.surge_mode and pyxel.btnp(pyxel.KEY_SPACE):
            remaining = self.surge_timer
            bonus = remaining // 30
            self.score += bonus
            self._add_floating_text(
                float(self.SCREEN_W // 2),
                float(self.SCREEN_H // 2),
                f"BONUS +{bonus}",
                10,
            )
            self.surge_mode = False
            self.surge_timer = 0

        wheel = pyxel.mouse_wheel
        if wheel != 0:
            filtered = self._get_filtered_tray_pieces()
            max_scroll = max(0, len(filtered) - self.TRAY_VISIBLE)
            self._tray_scroll = max(
                0, min(self._tray_scroll - wheel, max_scroll)
            )

    def _clamp_scroll(self) -> None:
        filtered = self._get_filtered_tray_pieces()
        max_scroll = max(0, len(filtered) - self.TRAY_VISIBLE)
        self._tray_scroll = max(0, min(self._tray_scroll, max_scroll))

    def handle_click(self, mx: int, my: int) -> None:
        tray_y = self.TRAY_Y + 10
        if tray_y <= my <= tray_y + self.PIECE_SIZE:
            visible = self._get_visible_pieces()
            for i, tp in enumerate(visible):
                px = self.TRAY_START_X + i * self.TRAY_SPACING
                if px <= mx <= px + self.PIECE_SIZE:
                    if self.selected_piece == tp.piece_id:
                        self.selected_piece = None
                    else:
                        self.selected_piece = tp.piece_id
                    return
            self.selected_piece = None
            return

        if (
            self.GRID_Y <= my < self.GRID_Y + self.GRID_ROWS * self.CELL
            and self.GRID_X <= mx < self.GRID_X + self.GRID_COLS * self.CELL
        ):
            col = (mx - self.GRID_X) // self.CELL
            row = (my - self.GRID_Y) // self.CELL
            if self.selected_piece is not None:
                tray_idx = self._find_tray_idx(self.selected_piece)
                if tray_idx is not None:
                    self.place_piece(tray_idx, col, row)
                self.selected_piece = None
            return

        self.selected_piece = None

    def place_piece(self, tray_idx: int, grid_col: int, grid_row: int) -> str:
        if tray_idx < 0 or tray_idx >= len(self.tray_pieces):
            return "invalid"
        if (
            grid_col < 0
            or grid_col >= self.GRID_COLS
            or grid_row < 0
            or grid_row >= self.GRID_ROWS
        ):
            return "invalid"

        slot = self.slots[grid_row][grid_col]
        if slot.filled:
            return "invalid"

        piece = self.tray_pieces[tray_idx]
        is_surge = self.surge_mode

        cx = float(self.GRID_X + grid_col * self.CELL + self.CELL // 2)
        cy = float(self.GRID_Y + grid_row * self.CELL + self.CELL // 2)

        if is_surge or piece.piece_id == slot.target_piece_id:
            slot.filled = True
            slot.filled_color = piece.color
            self.pieces_placed += 1
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)

            multiplier = 3 if is_surge else 1
            points = int(10 * (1 + self.combo * 0.5) * multiplier)
            self.score += points

            self._add_floating_text(cx, cy - self.CELL // 2, f"+{points}", 10)
            if self.combo >= 2:
                self._add_floating_text(
                    cx, cy - self.CELL,
                    f"COMBO x{self.combo}", 10 if self.combo >= self.SURGE_COMBO_THRESHOLD else 7,
                )

            self._spawn_particles(cx, cy, piece.color, 15 if is_surge else 10)

            self.tray_pieces.pop(tray_idx)

            if self.combo >= self.SURGE_COMBO_THRESHOLD and not self.surge_mode:
                self._activate_surge()

            return "correct"
        elif piece.color == slot.color:
            self.combo += 1
            self.heat += 5
            self.score += 5
            self._add_floating_text(cx - 4, cy, "+5", 7)
            return "partial"
        else:
            self.combo = 0
            self.heat += 15
            self._add_floating_text(cx - 8, cy, "MISS!", 8)
            self._spawn_particles(cx, cy, 13, 5)
            self._shake_frames = 8
            return "wrong"

    def _activate_surge(self) -> None:
        self.surge_mode = True
        self.surge_timer = self.SURGE_DURATION
        cx = float(self.GRID_X + self.CELL * self.GRID_COLS // 2)
        cy = float(self.GRID_Y + self.CELL * self.GRID_ROWS // 2)
        self._add_floating_text(cx, cy, "SURGE!", 10)
        self._spawn_surge_particles(cx, cy)
        self._auto_solve_adjacent()
        self._auto_solve_adjacent()

    def _auto_solve_adjacent(self) -> None:
        candidates: list[tuple[int, int]] = []
        for row in range(self.GRID_ROWS):
            for col in range(self.GRID_COLS):
                slot = self.slots[row][col]
                if slot.filled:
                    continue
                adjacent_to_solved = False
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = row + dr, col + dc
                    if 0 <= nr < self.GRID_ROWS and 0 <= nc < self.GRID_COLS:
                        if self.slots[nr][nc].filled:
                            adjacent_to_solved = True
                            break
                if adjacent_to_solved:
                    candidates.append((row, col))
        if not candidates:
            return

        row, col = self._rng.choice(candidates)
        slot = self.slots[row][col]
        for i, tp in enumerate(self.tray_pieces):
            if tp.piece_id == slot.target_piece_id:
                slot.filled = True
                slot.filled_color = tp.color
                self.pieces_placed += 1
                self.score += 20
                ax = float(self.GRID_X + col * self.CELL + self.CELL // 2)
                ay = float(self.GRID_Y + row * self.CELL + self.CELL // 2)
                self._spawn_particles(ax, ay, 10, 18)
                self._add_floating_text(ax, ay - 10, "+20", 10)
                self.tray_pieces.pop(i)
                break

    def _get_filtered_tray_pieces(self) -> list[TrayPiece]:
        if self._color_filter is None:
            return self.tray_pieces
        target_color = self.COLORS[self._color_filter]
        return [tp for tp in self.tray_pieces if tp.color == target_color]

    def _get_visible_pieces(self) -> list[TrayPiece]:
        filtered = self._get_filtered_tray_pieces()
        start = self._tray_scroll
        return filtered[start : start + self.TRAY_VISIBLE]

    def _find_tray_idx(self, piece_id: int) -> int | None:
        for i, tp in enumerate(self.tray_pieces):
            if tp.piece_id == piece_id:
                return i
        return None

    def _spawn_particles(
        self, x: float, y: float, color: int, count: int
    ) -> None:
        for _ in range(count):
            angle = self._rng.uniform(0, 6.283185307179586)
            speed = self._rng.uniform(1.0, 3.5)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=pyxel.cos(angle) * speed,
                    vy=pyxel.sin(angle) * speed,
                    life=self._rng.randint(12, 30),
                    color=color,
                )
            )

    def _spawn_surge_particles(self, x: float, y: float) -> None:
        for _ in range(35):
            angle = self._rng.uniform(0, 6.283185307179586)
            speed = self._rng.uniform(2.0, 5.0)
            color = self.COLORS[self._rng.randrange(self.NUM_COLORS)]
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=pyxel.cos(angle) * speed,
                    vy=pyxel.sin(angle) * speed,
                    life=self._rng.randint(20, 45),
                    color=color,
                )
            )

    def _add_floating_text(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, life=45, color=color)
        )

    def _update_particles(self) -> None:
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [
            ft for ft in self.floating_texts if ft.life > 0
        ]

    def _update_shake(self) -> None:
        if self._shake_frames > 0:
            self._shake_frames -= 1

    def draw(self) -> None:
        shake_x = 0
        shake_y = 0
        if self._shake_frames > 0:
            shake_x = self._rng.randint(-2, 2)
            shake_y = self._rng.randint(-2, 2)

        if self.phase == Phase.TITLE:
            self._draw_title(shake_x, shake_y)
        elif self.phase == Phase.PLAYING:
            self._draw_playing(shake_x, shake_y)
        elif self.phase == Phase.VICTORY:
            self._draw_victory(shake_x, shake_y)
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over(shake_x, shake_y)

    def _draw_title(self, shake_x: int, shake_y: int) -> None:
        pyxel.cls(1)
        cx = self.SCREEN_W // 2 + shake_x
        pyxel.text(cx - 48, 40, "PUZZLE SURGE", 7)

        instructions = [
            ("Assemble the jigsaw!", 7),
            ("Click piece in tray", 7),
            ("then click grid slot", 7),
            ("Match color = COMBO +", 10),
            ("COMBO x4 = SURGE MODE", 10),
            ("1-4: Filter by color", 7),
            ("Wrong color = HEAT!", 8),
        ]
        for i, (text, col) in enumerate(instructions):
            pyxel.text(cx - len(text) * 2, 80 + i * 14, text, col)

        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(cx - 50, 210, "Press SPACE to start", 10)

    def _draw_playing(self, shake_x: int, shake_y: int) -> None:
        pyxel.cls(0)

        for row in range(self.GRID_ROWS):
            for col in range(self.GRID_COLS):
                self._draw_slot(col, row, shake_x, shake_y)

        self._draw_tray(shake_x, shake_y)
        self._draw_hud(shake_x, shake_y)
        self._draw_particles(shake_x, shake_y)
        self._draw_floating_texts(shake_x, shake_y)

        if self.surge_mode:
            hue = (pyxel.frame_count // 4) % 16
            pyxel.rectb(
                shake_x, shake_y, self.SCREEN_W, self.SCREEN_H, hue
            )
            sec = self.surge_timer // 60
            pyxel.text(
                self.SCREEN_W // 2 - 24 + shake_x,
                20 + shake_y,
                f"SURGE {sec}s",
                10,
            )

    def _draw_slot(
        self, col: int, row: int, shake_x: int, shake_y: int
    ) -> None:
        slot = self.slots[row][col]
        x = self.GRID_X + col * self.CELL + shake_x
        y = self.GRID_Y + row * self.CELL + shake_y

        if slot.filled:
            pyxel.rect(
                x + 1, y + 1, self.CELL - 2, self.CELL - 2, slot.filled_color
            )
            self._draw_shape(
                x + self.CELL // 2,
                y + self.CELL // 2,
                slot.filled_color,
                slot.shape_id,
                6,
            )
        else:
            pyxel.rectb(x + 1, y + 1, self.CELL - 2, self.CELL - 2, 6)
            dim_color = max(slot.color - 7, 1) if slot.color >= 8 else slot.color
            pyxel.rect(x + 3, y + 3, self.CELL - 6, self.CELL - 6, 1)
            pyxel.rectb(x + 3, y + 3, self.CELL - 6, self.CELL - 6, dim_color)

    def _draw_shape(
        self, cx: int, cy: int, color: int, shape_id: int, outline_color: int
    ) -> None:
        color_idx = 0
        for i, c in enumerate(self.COLORS):
            if c == color:
                color_idx = i
                break

        s = 4
        if color_idx == 0:
            pyxel.tri(
                cx, cy - s, cx - s, cy + s, cx + s, cy + s, outline_color
            )
        elif color_idx == 1:
            pyxel.circb(cx, cy, 3, outline_color)
        elif color_idx == 2:
            pyxel.line(cx, cy - s + 1, cx - s + 1, cy, outline_color)
            pyxel.line(cx - s + 1, cy, cx, cy + s - 1, outline_color)
            pyxel.line(cx, cy + s - 1, cx + s - 1, cy, outline_color)
            pyxel.line(cx + s - 1, cy, cx, cy - s + 1, outline_color)
        elif color_idx == 3:
            pyxel.rectb(cx - 3, cy - 3, 6, 6, outline_color)

        if shape_id >= 1:
            pyxel.pset(cx + 5, cy - 5, outline_color)
        if shape_id >= 2:
            pyxel.pset(cx - 5, cy - 5, outline_color)

    def _draw_tray(self, shake_x: int, shake_y: int) -> None:
        tray_y = self.TRAY_Y + shake_y
        pyxel.rect(0, self.TRAY_Y, self.SCREEN_W, self.SCREEN_H - self.TRAY_Y, 1)
        pyxel.line(
            shake_x, tray_y,
            self.SCREEN_W + shake_x, tray_y,
            7,
        )

        for i in range(self.NUM_COLORS):
            button_x = self.SCREEN_W - 60 + i * 14 + shake_x
            button_y = tray_y + 4
            pyxel.rect(button_x, button_y, 10, 10, self.COLORS[i])
            if self._color_filter == i:
                pyxel.rectb(button_x - 1, button_y - 1, 12, 12, 7)

        visible = self._get_visible_pieces()
        for i, tp in enumerate(visible):
            px = self.TRAY_START_X + i * self.TRAY_SPACING + shake_x
            py = tray_y + 10
            pyxel.rect(px, py, self.PIECE_SIZE, self.PIECE_SIZE, tp.color)
            self._draw_shape(
                px + self.PIECE_SIZE // 2,
                py + self.PIECE_SIZE // 2,
                tp.color,
                tp.shape_id,
                7,
            )
            if tp.piece_id == self.selected_piece:
                pyxel.rectb(
                    px - 2,
                    py - 2,
                    self.PIECE_SIZE + 4,
                    self.PIECE_SIZE + 4,
                    7,
                )

        filtered = self._get_filtered_tray_pieces()
        if len(filtered) > self.TRAY_VISIBLE:
            page_count = len(filtered) - self.TRAY_VISIBLE + 1
            for i in range(page_count):
                dot_x = 4 + i * 5 + shake_x
                dot_y = tray_y + 42
                color = 7 if i == self._tray_scroll else 5
                pyxel.rect(dot_x, dot_y, 3, 3, color)

        remaining = len(self.tray_pieces)
        label = f"Pieces: {remaining}"
        pyxel.text(
            shake_x + 4,
            tray_y + 2,
            label,
            7,
        )

    def _draw_hud(self, shake_x: int, shake_y: int) -> None:
        seconds = self.timer // 60
        sec_str = f"{seconds:02d}"
        pyxel.text(4 + shake_x, 4 + shake_y, f"TIME {sec_str}", 7)

        pyxel.text(
            self.SCREEN_W // 2 - 28 + shake_x,
            4 + shake_y,
            f"SCORE {self.score}",
            7,
        )

        combo_color = (
            10 if self.combo >= self.SURGE_COMBO_THRESHOLD else 7
        )
        pyxel.text(
            self.SCREEN_W - 72 + shake_x,
            4 + shake_y,
            f"COMBO {self.combo}",
            combo_color,
        )

        bar_x = 4 + shake_x
        bar_y = 16 + shake_y
        bar_w = 100
        bar_h = 6
        pyxel.rectb(bar_x, bar_y, bar_w, bar_h, 7)
        fill = min(int(self.heat / self.MAX_HEAT * (bar_w - 2)), bar_w - 2)
        if self.heat > 60:
            bar_color = 8
        elif self.heat > 30:
            bar_color = 10
        else:
            bar_color = 3
        pyxel.rect(bar_x + 1, bar_y + 1, fill, bar_h - 2, bar_color)
        pyxel.text(bar_x, bar_y + 8, f"HEAT {int(self.heat)}", 7)

    def _draw_victory(self, shake_x: int, shake_y: int) -> None:
        pyxel.cls(3)
        cx = self.SCREEN_W // 2 + shake_x
        pyxel.text(cx - 40, 40, "COMPLETE!", 7)
        pyxel.text(cx - 50, 80, f"Score: {self.score}", 7)
        pyxel.text(cx - 50, 100, f"Max Combo: {self.max_combo}", 7)
        pyxel.text(
            cx - 50, 120, f"Timer Bonus: +{self._timer_bonus}", 10
        )
        pyxel.text(cx - 50, 160, f"Pieces: {self.pieces_placed}/{self.pieces_total}", 7)
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(cx - 50, 200, "Press SPACE to retry", 10)

    def _draw_game_over(self, shake_x: int, shake_y: int) -> None:
        pyxel.cls(8)
        cx = self.SCREEN_W // 2 + shake_x
        pyxel.text(cx - 32, 40, "GAME OVER", 7)
        pyxel.text(cx - 50, 80, f"Score: {self.score}", 7)
        pyxel.text(cx - 50, 100, f"Max Combo: {self.max_combo}", 7)
        pyxel.text(
            cx - 50,
            120,
            f"Pieces: {self.pieces_placed}/{self.pieces_total}",
            7,
        )
        if self.heat >= self.MAX_HEAT:
            pyxel.text(cx - 40, 140, "OVERHEAT!", 8)
        else:
            pyxel.text(cx - 40, 140, "TIME UP!", 10)
        if (pyxel.frame_count // 30) % 2 == 0:
            pyxel.text(cx - 50, 200, "Press SPACE to retry", 10)

    def _draw_particles(self, shake_x: int, shake_y: int) -> None:
        for p in self.particles:
            alpha = p.life / 30
            if alpha > 0.4:
                pyxel.rect(
                    int(p.x) + shake_x - 1,
                    int(p.y) + shake_y - 1,
                    3,
                    3,
                    p.color,
                )
            else:
                pyxel.pset(
                    int(p.x) + shake_x,
                    int(p.y) + shake_y,
                    p.color,
                )

    def _draw_floating_texts(self, shake_x: int, shake_y: int) -> None:
        for ft in self.floating_texts:
            alpha = ft.life / 45
            if alpha <= 0:
                continue
            col = ft.color
            if alpha < 0.25:
                col = 5
            pyxel.text(
                int(ft.x) + shake_x - len(ft.text) * 2,
                int(ft.y) + shake_y,
                ft.text,
                col,
            )


if __name__ == "__main__":
    Game()
