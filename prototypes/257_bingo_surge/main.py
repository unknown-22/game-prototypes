from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class CardCell:
    row: int
    col: int
    number: int
    color: int
    daubed: bool = False


@dataclass
class DriftingNumber:
    x: float
    y: float
    number: int
    color: int
    speed: float
    active: bool = True


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

CELL_SIZE = 28
CARD_LEFT = 24
CARD_TOP = 40
CARD_COLS = 5
CARD_ROWS = 5
BINGO_LETTERS = ["B", "I", "N", "G", "O"]
COLUMN_RANGES = [(1, 15), (16, 30), (31, 45), (46, 60), (61, 75)]
PLAY_COLORS = [RED, LIME, DARK_BLUE, YELLOW]
COLOR_NAMES = ["RED", "LIME", "BLUE", "YELLOW"]
COMBO_THRESHOLD = 4
SUPER_DURATION = 300
GAME_DURATION = 1800
HEAT_MAX = 100
HEAT_DECAY = 0.02
HEAT_MISMATCH = 15
HEAT_MISS = 10
HEAT_SUPER = 0
SPAWN_INTERVAL_INITIAL = 60
SPAWN_INTERVAL_MIN = 20
NUMBER_SPEED_MIN = 1.0
NUMBER_SPEED_MAX = 2.5
BINGO_BONUS = 500
PARTICLE_BURST_COUNT = 12
CARD_WIDTH = CARD_COLS * CELL_SIZE
CARD_HEIGHT = CARD_ROWS * CELL_SIZE
HIT_RADIUS = 14


class Game:
    def __init__(self) -> None:
        self.phase: Phase = Phase.TITLE
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.best_score: int = 0
        self.timer: int = GAME_DURATION
        self.heat: float = 0.0
        self.player_color_idx: int = 0
        self.color_cycle_timer: int = 90
        self.card: list[list[CardCell]] = []
        self.drifting_numbers: list[DriftingNumber] = []
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.super_timer: int = 0
        self.spawn_timer: int = 0
        self.frame: int = 0
        self._rng: random.Random = random.Random()
        self._cycle_colors: list[int] = [RED, LIME, DARK_BLUE, YELLOW, RED, LIME, DARK_BLUE, YELLOW]
        self._cycle_idx: int = 0
        self._title_color_timer: int = 0

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.timer = GAME_DURATION
        self.heat = 0.0
        self.player_color_idx = 0
        self.color_cycle_timer = 90
        self.super_timer = 0
        self.spawn_timer = 0
        self.frame = 0
        self.drifting_numbers.clear()
        self.particles.clear()
        self.floating_texts.clear()
        self._cycle_idx = 0
        self._title_color_timer = 0
        self._init_card()

    def _init_card(self) -> None:
        self.card = []
        for row in range(CARD_ROWS):
            row_cells: list[CardCell] = []
            for col in range(CARD_COLS):
                lo, hi = COLUMN_RANGES[col]
                number = self._rng.randint(lo, hi)
                color_idx = self._rng.randrange(len(PLAY_COLORS))
                row_cells.append(CardCell(row=row, col=col, number=number, color=color_idx))
            self.card.append(row_cells)

    def _color_cycle_interval(self) -> int:
        return max(40, 90 - (GAME_DURATION - self.timer) // 30)

    def _get_undaubed_cell_numbers(self) -> list[tuple[int, int, int, int]]:
        results: list[tuple[int, int, int, int]] = []
        for row in range(CARD_ROWS):
            for col in range(CARD_COLS):
                cell = self.card[row][col]
                if not cell.daubed:
                    results.append((cell.number, row, col, cell.color))
        return results

    def _random_undaubed_or_any(self) -> tuple[int, int, int, int]:
        undaubed = self._get_undaubed_cell_numbers()
        if undaubed:
            return self._rng.choice(undaubed)
        row = self._rng.randrange(CARD_ROWS)
        col = self._rng.randrange(CARD_COLS)
        cell = self.card[row][col]
        return (cell.number, row, col, cell.color)

    def _spawn_number(self) -> None:
        number, row, col, _color = self._random_undaubed_or_any()
        color = self._rng.choice(PLAY_COLORS)
        spawn_x: float = float(310 + self._rng.randint(0, 30))
        target_y: float = float(CARD_TOP + row * CELL_SIZE + CELL_SIZE // 2)
        speed: float = NUMBER_SPEED_MIN + self._rng.random() * (NUMBER_SPEED_MAX - NUMBER_SPEED_MIN)
        self.drifting_numbers.append(
            DriftingNumber(x=spawn_x, y=target_y, number=number, color=color, speed=speed)
        )

    def _update_drifting(self) -> None:
        for dn in self.drifting_numbers[:]:
            dn.x -= dn.speed
            if dn.x < CARD_LEFT - 20:
                dn.active = False
                self.heat = min(HEAT_MAX, self.heat + HEAT_MISS)
                self.combo = 0
        self.drifting_numbers = [dn for dn in self.drifting_numbers if dn.active]

    def _update_heat(self) -> None:
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            return
        self.heat = max(0.0, self.heat - HEAT_DECAY)

    def _check_bingo(self) -> int:
        bingo_count = 0
        cells_to_reset: set[tuple[int, int]] = set()

        for row in range(CARD_ROWS):
            if all(self.card[row][col].daubed for col in range(CARD_COLS)):
                bingo_count += 1
                for col in range(CARD_COLS):
                    cells_to_reset.add((row, col))

        for col in range(CARD_COLS):
            if all(self.card[row][col].daubed for row in range(CARD_ROWS)):
                bingo_count += 1
                for row in range(CARD_ROWS):
                    cells_to_reset.add((row, col))

        if all(self.card[i][i].daubed for i in range(CARD_ROWS)):
            bingo_count += 1
            for i in range(CARD_ROWS):
                cells_to_reset.add((i, i))

        if all(self.card[i][CARD_COLS - 1 - i].daubed for i in range(CARD_ROWS)):
            bingo_count += 1
            for i in range(CARD_ROWS):
                cells_to_reset.add((i, CARD_COLS - 1 - i))

        if bingo_count > 0:
            self.score += BINGO_BONUS * bingo_count
            for row, col in cells_to_reset:
                lo, hi = COLUMN_RANGES[col]
                new_number = self._rng.randint(lo, hi)
                new_color = self._rng.randrange(len(PLAY_COLORS))
                self.card[row][col] = CardCell(row=row, col=col, number=new_number, color=new_color, daubed=False)

            cx = CARD_LEFT + CARD_WIDTH // 2
            cy = CARD_TOP + CARD_HEIGHT // 2
            self.floating_texts.append(FloatingText(float(cx), float(cy), f"BINGO! x{bingo_count}", 120, YELLOW))
            self._spawn_particles(float(cx), float(cy), 20, 25)

        return bingo_count

    def _spawn_particles(self, x: float, y: float, count: int, life: int) -> None:
        for _ in range(count):
            angle = self._rng.random() * math.pi * 2
            speed = 1.0 + self._rng.random() * 3.0
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            color = self._rng.choice(PLAY_COLORS)
            self.particles.append(Particle(x=x, y=y, vx=vx, vy=vy, life=life, color=color))

    def _check_click(self, mx: int, my: int) -> bool:
        for i, dn in enumerate(self.drifting_numbers):
            dist = math.hypot(mx - dn.x, my - dn.y)
            if dist < HIT_RADIUS:
                cell = self._find_card_cell(dn.number)
                if cell is None or cell.daubed:
                    self.drifting_numbers.pop(i)
                    return True

                is_super = self.super_timer > 0
                is_match = (dn.color == PLAY_COLORS[self.player_color_idx]) or is_super

                if is_match:
                    cell.daubed = True
                    self.combo += 1
                    self.max_combo = max(self.max_combo, self.combo)
                    if self.combo >= COMBO_THRESHOLD:
                        self.super_timer = SUPER_DURATION
                        cx = float(CARD_LEFT + CARD_WIDTH // 2)
                        cy = float(CARD_TOP + CARD_HEIGHT // 2)
                        self._spawn_particles(cx, cy, 15, 20)
                        self.floating_texts.append(FloatingText(cx, cy, "SUPER DAUB!", 90, YELLOW))
                    multiplier = 3 if is_super else 1
                    gain = 10 * self.combo * multiplier
                    self.score += gain
                    self._spawn_particles(dn.x, dn.y, 6, 15)
                    self.floating_texts.append(
                        FloatingText(dn.x, dn.y - 10, f"+{gain}", 45, PLAY_COLORS[self.player_color_idx])
                    )
                    if self.combo >= 2:
                        self.floating_texts.append(
                            FloatingText(dn.x, dn.y - 20, f"COMBO x{self.combo}", 45, ORANGE)
                        )
                    self.drifting_numbers.pop(i)
                    self._check_bingo()
                else:
                    self.combo = 0
                    self.heat = min(HEAT_MAX, self.heat + HEAT_MISMATCH)
                    self.floating_texts.append(
                        FloatingText(dn.x, dn.y - 10, "WRONG!", 60, RED)
                    )
                    self.drifting_numbers.pop(i)
                return True
        return False

    def _find_card_cell(self, number: int) -> CardCell | None:
        for row in range(CARD_ROWS):
            for col in range(CARD_COLS):
                if self.card[row][col].number == number:
                    return self.card[row][col]
        return None

    def update(self) -> None:
        if self.phase != Phase.PLAYING:
            return

        self.frame += 1
        self.timer -= 1
        if self.timer <= 0:
            self.phase = Phase.GAME_OVER
            self.best_score = max(self.best_score, self.score)
            return

        self.color_cycle_timer -= 1
        if self.color_cycle_timer <= 0:
            self.player_color_idx = (self.player_color_idx + 1) % len(PLAY_COLORS)
            self.color_cycle_timer = self._color_cycle_interval()

        if pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.KEY_DOWN):
            self.player_color_idx = (self.player_color_idx + 1) % len(PLAY_COLORS)
            self.color_cycle_timer = self._color_cycle_interval()

        self._update_drifting()

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self._spawn_number()
            progress = (GAME_DURATION - self.timer) / GAME_DURATION
            self.spawn_timer = int(SPAWN_INTERVAL_INITIAL - (SPAWN_INTERVAL_INITIAL - SPAWN_INTERVAL_MIN) * progress)

        for p in self.particles[:]:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
        self.particles = [p for p in self.particles if p.life > 0]

        for ft in self.floating_texts[:]:
            ft.y -= 0.5
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

        if self.super_timer > 0:
            self.super_timer -= 1
            self._cycle_idx = (self._cycle_idx + 1) % len(self._cycle_colors)

        self._update_heat()
        if self.phase == Phase.GAME_OVER:
            self.best_score = max(self.best_score, self.score)

    def draw(self) -> None:
        pyxel.cls(BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_playing()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    def _draw_title(self) -> None:
        self._title_color_timer = (self._title_color_timer + 1) % (len(PLAY_COLORS) * 30)
        color_idx = (self._title_color_timer // 30) % len(PLAY_COLORS)
        title_color = PLAY_COLORS[color_idx]
        draw_text_centered("BINGO SURGE", 80, title_color)
        if self.frame % 60 < 30:
            draw_text_centered("Click to Start", 140, WHITE)
        draw_text_centered("Match colors to daub numbers", 160, GRAY)
        draw_text_centered("COMBO x4 = SUPER DAUB!", 180, ORANGE)
        draw_text_centered("BINGO lines = BIG BONUS", 200, LIME)

    def _draw_playing(self) -> None:
        pyxel.rect(CARD_LEFT, CARD_TOP, CARD_WIDTH, CARD_HEIGHT, DARK_BLUE)

        for i in range(CARD_COLS + 1):
            x = CARD_LEFT + i * CELL_SIZE
            pyxel.line(x, CARD_TOP, x, CARD_TOP + CARD_HEIGHT, GRAY)
        for i in range(CARD_ROWS + 1):
            y = CARD_TOP + i * CELL_SIZE
            pyxel.line(CARD_LEFT, y, CARD_LEFT + CARD_WIDTH, y, GRAY)

        for col in range(CARD_COLS):
            letter = BINGO_LETTERS[col]
            lx = CARD_LEFT + col * CELL_SIZE + CELL_SIZE // 2 - 2
            pyxel.text(lx, CARD_TOP - 14, letter, WHITE)

        for row in range(CARD_ROWS):
            for col in range(CARD_COLS):
                cell = self.card[row][col]
                cx = CARD_LEFT + col * CELL_SIZE
                cy = CARD_TOP + row * CELL_SIZE
                if cell.daubed:
                    pyxel.rect(cx + 1, cy + 1, CELL_SIZE - 2, CELL_SIZE - 2, WHITE)
                    draw_number_centered(cell.number, cx + CELL_SIZE // 2, cy + CELL_SIZE // 2 + 2, BLACK)
                else:
                    clr = PLAY_COLORS[cell.color]
                    pyxel.rect(cx + 1, cy + 1, CELL_SIZE - 2, CELL_SIZE - 2, clr)
                    draw_number_centered(cell.number, cx + CELL_SIZE // 2, cy + CELL_SIZE // 2 + 2, WHITE)

        for dn in self.drifting_numbers:
            r = 10
            pyxel.circb(int(dn.x), int(dn.y), r, WHITE)
            pyxel.circ(int(dn.x), int(dn.y), r - 1, dn.color)
            draw_number_centered(dn.number, int(dn.x), int(dn.y) + 2, WHITE)

        for p in self.particles:
            pyxel.rect(int(p.x), int(p.y), 2, 2, p.color)

        for ft in self.floating_texts:
            tw = len(ft.text) * 4
            pyxel.text(int(ft.x - tw // 2), int(ft.y), ft.text, ft.color)

        if self.super_timer > 0:
            border_color = self._cycle_colors[self._cycle_idx]
            for offset in range(3):
                pyxel.rectb(
                    CARD_LEFT - offset,
                    CARD_TOP - offset,
                    CARD_WIDTH + offset * 2,
                    CARD_HEIGHT + offset * 2,
                    border_color,
                )
            secs = self.super_timer // 30
            draw_text_centered(f"SUPER DAUB! {secs}s", 220, YELLOW)

        pyxel.text(8, 4, f"SCORE: {self.score}", WHITE)
        pyxel.text(100, 4, f"COMBO: x{self.combo}", ORANGE)
        pyxel.text(200, 4, f"BEST: {self.best_score}", GRAY)

        bar_w = 304
        pyxel.rectb(8, 16, bar_w, 6, WHITE)
        timer_ratio = self.timer / GAME_DURATION
        fill_w = int(bar_w * timer_ratio)
        if timer_ratio > 0.5:
            tcolor = GREEN
        elif timer_ratio > 0.25:
            tcolor = YELLOW
        else:
            tcolor = RED
        pyxel.rect(8, 16, fill_w, 6, tcolor)

        pyxel.rectb(8, 24, bar_w, 4, RED)
        heat_fill = int(bar_w * (self.heat / HEAT_MAX))
        pyxel.rect(8, 24, heat_fill, 4, RED)

        color_name = COLOR_NAMES[self.player_color_idx]
        color_clr = PLAY_COLORS[self.player_color_idx]
        label = f"COLOR: {color_name}"
        pyxel.text(160 - len(label) * 2, 228, label, color_clr)
        pyxel.rect(160 + len(label) * 2 + 2, 228, 8, 8, color_clr)

    def _draw_game_over(self) -> None:
        draw_text_centered("GAME OVER", 80, RED)
        draw_text_centered(f"Score: {self.score}", 120, WHITE)
        draw_text_centered(f"Best: {self.best_score}", 140, WHITE)
        draw_text_centered(f"Max Combo: x{self.max_combo}", 160, ORANGE)
        if self.frame % 60 < 30:
            draw_text_centered("Click to Retry", 200, WHITE)

    def handle_input(self) -> None:
        if self.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()
        elif self.phase == Phase.PLAYING:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self._check_click(pyxel.mouse_x, pyxel.mouse_y)
        elif self.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.reset()


def draw_text_centered(text: str, y: int, color: int) -> None:
    pyxel.text(160 - len(text) * 2, y, text, color)


def draw_number_centered(num: int, cx: int, cy: int, color: int) -> None:
    s = str(num)
    x = cx - len(s) * 2
    y = cy - 3
    pyxel.text(x, y, s, color)


class App:
    def __init__(self) -> None:
        self.game = Game()
        pyxel.init(320, 240, title="BINGO SURGE")
        self.game.frame = 0
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        if self.game.phase == Phase.TITLE:
            self.game.frame += 1
        self.game.handle_input()
        self.game.update()

    def draw(self) -> None:
        self.game.draw()


def main() -> None:
    App()


if __name__ == "__main__":
    main()
