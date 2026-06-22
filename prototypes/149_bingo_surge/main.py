import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel


# ---------------------------------------------------------------------------
# Enums & Data
# ---------------------------------------------------------------------------

class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class CallInfo:
    number: int
    color: int  # 0-3
    active: bool = False


@dataclass
class Cell:
    number: int
    color: int  # 0-3
    marked: bool = False


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
    vy: float = -1.0


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CELL_SIZE: int = 32
CELL_GAP: int = 2
STEP: int = CELL_SIZE + CELL_GAP  # 34
GRID_X: int = 48
GRID_Y: int = 48
GRID_W: int = 5 * CELL_SIZE + 4 * CELL_GAP  # 168
GRID_H: int = 5 * CELL_SIZE + 4 * CELL_GAP  # 168
CALL_DELAY: int = 90
MAX_HEAT: int = 100
SHAKE_FRAMES: int = 120
SUPER_DAUB_DURATION: int = 300
COMBO_THRESHOLD: int = 4
TOTAL_CALLS: int = 50
NUM_COLORS: int = 4

# Pyxel palette indices
BLACK: int = 0
NAVY: int = 1
PURPLE: int = 2
GREEN: int = 3
BROWN: int = 4
DARK_BLUE: int = 5
LIGHT_BLUE: int = 6
WHITE: int = 7
RED: int = 8
ORANGE: int = 9
YELLOW: int = 10
LIME: int = 11
CYAN: int = 12
GRAY: int = 13
PINK: int = 14
PEACH: int = 15

RAINBOW_COLORS: list[int] = [RED, ORANGE, YELLOW, GREEN, LIGHT_BLUE, PURPLE]

# (unmarked, marked) colour per logical colour index 0-3
COLOR_MAP: list[tuple[int, int]] = [
    (BROWN, RED),           # 0 – RED family
    (NAVY, GREEN),          # 1 – GREEN family
    (DARK_BLUE, LIGHT_BLUE),  # 2 – BLUE family
    (GRAY, YELLOW),         # 3 – YELLOW family
]

COLOR_NAMES: list[str] = ["RED", "GREEN", "BLUE", "YELLOW"]


# ---------------------------------------------------------------------------
# Game logic (testable — no pyxel I/O)
# ---------------------------------------------------------------------------

class Game:
    def __init__(self) -> None:
        self.reset()
        self.phase = Phase.TITLE

    # -- reset ---------------------------------------------------------------

    def reset(self) -> None:
        self.phase = Phase.PLAYING
        self.cells = self._generate_card()
        self.call_queue = self._generate_calls()
        self.current_call_index: int = 0
        self.call_timer: int = CALL_DELAY
        self.score: int = 0
        self.combo: int = 0
        self.max_combo: int = 0
        self.heat: int = 0
        self.bingo_count: int = 0
        self.bingo_lines: set[str] = set()
        self.super_daub_timer: int = 0
        self.shake_timer: int = 0
        self.flash_timer: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.title_blink: int = 0
        self.game_over_blink: int = 0
        self.hits: int = 0
        self.missed: int = 0
        self.wrong_color: int = 0
        self.total_marks: int = 0
        self._call_handled: bool = False
        # Activate the first call
        if self.call_queue:
            self.call_queue[0].active = True

    # -- card / call generation ----------------------------------------------

    def _generate_card(self) -> list[list[Cell]]:
        numbers: list[int] = random.sample(range(1, 76), 25)
        cells: list[list[Cell]] = []
        for row in range(5):
            cell_row: list[Cell] = []
            for col in range(5):
                idx = row * 5 + col
                color = random.randint(0, NUM_COLORS - 1)
                marked = (row == 2 and col == 2)  # FREE space
                cell_row.append(Cell(number=numbers[idx], color=color, marked=marked))
            cells.append(cell_row)
        return cells

    def _generate_calls(self) -> list[CallInfo]:
        calls: list[CallInfo] = []
        for _ in range(TOTAL_CALLS):
            calls.append(
                CallInfo(
                    number=random.randint(1, 75),
                    color=random.randint(0, NUM_COLORS - 1),
                )
            )
        return calls

    # -- call advancement ----------------------------------------------------

    def _advance_call(self) -> str:
        if self.current_call_index < TOTAL_CALLS:
            self.call_queue[self.current_call_index].active = False

        self.current_call_index += 1

        if self.current_call_index >= TOTAL_CALLS:
            self.phase = Phase.GAME_OVER
            return "game_over"

        self.call_queue[self.current_call_index].active = True
        self.call_timer = CALL_DELAY
        self._call_handled = False

        # Super-daub auto-mark on new call
        if self.super_daub_timer > 0:
            self._auto_daub(self.call_queue[self.current_call_index].color)

        return "next"

    # -- click handling ------------------------------------------------------

    def _handle_click(self, cell_x: int, cell_y: int) -> str:
        if self.phase != Phase.PLAYING:
            return "no_play"
        if self.shake_timer > 0:
            return "shake"
        if self.current_call_index >= TOTAL_CALLS:
            return "no_call"

        cell: Cell = self.cells[cell_y][cell_x]

        if cell.marked:
            return "already_marked"

        # Wrong number -------------------------------------------------------
        if not self._is_correct_cell(cell_x, cell_y):
            self._update_heat(40)
            self._update_combo(False)
            self._spawn_wrong_particles(cell_x, cell_y)
            self._add_floating(cell_x, cell_y, "WRONG", RED, 20)
            return "wrong_number"

        # Correct number -----------------------------------------------------
        if not self._call_handled:
            self._call_handled = True

        cell.marked = True
        self.total_marks += 1

        if self._cell_matches_called_color(cell_x, cell_y):
            # Perfect match
            self._update_combo(True)
            self.hits += 1
            multiplier = max(1, self.combo)
            if self.super_daub_timer > 0:
                multiplier *= 3
            bonus = 100 * multiplier
            self.score += bonus
            self._spawn_mark_particles(cell_x, cell_y)
            self._add_floating(cell_x, cell_y, f"+{bonus}", YELLOW, 25)

            if self.combo >= COMBO_THRESHOLD and self.super_daub_timer == 0:
                self._activate_super_daub()

            result = "correct_color"
        else:
            # Wrong colour
            self._update_combo(False)
            self._update_heat(25)
            self.wrong_color += 1
            self.score += 100
            self._spawn_mark_particles(cell_x, cell_y)
            self._add_floating(cell_x, cell_y, "WRONG CLR", ORANGE, 25)
            result = "wrong_color"

        # BINGO check after any mark -----------------------------------------
        bingos = self._check_bingo()
        for _ in bingos:
            self.bingo_count += 1
            self.score += 500 * self.bingo_count
            self._spawn_bingo_particles()
            self.flash_timer = 3
            self._add_floating(2, 2, "BINGO!", YELLOW, 40, vy=-1.5, center=True)

        return result

    # -- query helpers -------------------------------------------------------

    def _is_correct_cell(self, col: int, row: int) -> bool:
        if self.current_call_index >= TOTAL_CALLS:
            return False
        return self.cells[row][col].number == self.call_queue[self.current_call_index].number

    def _cell_matches_called_color(self, col: int, row: int) -> bool:
        if self.current_call_index >= TOTAL_CALLS:
            return False
        return self.cells[row][col].color == self.call_queue[self.current_call_index].color

    # -- combo ---------------------------------------------------------------

    def _update_combo(self, is_match: bool) -> None:
        if self.super_daub_timer > 0:
            return  # frozen during super-daub
        if is_match:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
        else:
            self.combo = 0

    # -- heat ----------------------------------------------------------------

    def _update_heat(self, amount: int) -> None:
        self.heat = min(self.heat + amount, MAX_HEAT)
        if self.heat >= MAX_HEAT and self.shake_timer == 0:
            self.shake_timer = SHAKE_FRAMES
            self.heat = 0
            # spawn shake particles
            for _ in range(10):
                self.particles.append(
                    Particle(
                        x=280 + random.uniform(-5, 5),
                        y=222 + random.uniform(-3, 3),
                        vx=random.uniform(-2, 2),
                        vy=random.uniform(-2, 2),
                        life=random.randint(10, 20),
                        color=RED,
                    )
                )

    # -- bingo check ---------------------------------------------------------

    def _check_bingo(self) -> list[str]:
        new_lines: list[str] = []
        # rows
        for r in range(5):
            if all(self.cells[r][c].marked for c in range(5)):
                lid = f"R{r}"
                if lid not in self.bingo_lines:
                    self.bingo_lines.add(lid)
                    new_lines.append(lid)
        # columns
        for c in range(5):
            if all(self.cells[r][c].marked for r in range(5)):
                lid = f"C{c}"
                if lid not in self.bingo_lines:
                    self.bingo_lines.add(lid)
                    new_lines.append(lid)
        # diagonals
        if all(self.cells[i][i].marked for i in range(5)):
            if "D0" not in self.bingo_lines:
                self.bingo_lines.add("D0")
                new_lines.append("D0")
        if all(self.cells[i][4 - i].marked for i in range(5)):
            if "D1" not in self.bingo_lines:
                self.bingo_lines.add("D1")
                new_lines.append("D1")
        return new_lines

    # -- super-daub ----------------------------------------------------------

    def _activate_super_daub(self) -> None:
        self.super_daub_timer = SUPER_DAUB_DURATION
        for _ in range(20):
            self.particles.append(
                Particle(
                    x=GRID_X + GRID_W // 2 + random.uniform(-30, 30),
                    y=GRID_Y + GRID_H // 2 + random.uniform(-30, 30),
                    vx=random.uniform(-3, 3),
                    vy=random.uniform(-3, 3),
                    life=random.randint(20, 35),
                    color=random.choice(RAINBOW_COLORS),
                )
            )
        self._add_floating(2, 2, "SUPER DAUB!", YELLOW, 50, vy=-1.0, center=True, at_y=GRID_Y - 12)

    def _update_super_daub(self) -> None:
        if self.super_daub_timer > 0:
            self.super_daub_timer -= 1

    def _auto_daub(self, color: int) -> int:
        count = 0
        for row in range(5):
            for col in range(5):
                cell = self.cells[row][col]
                if not cell.marked and cell.color == color:
                    cell.marked = True
                    count += 1
                    self.score += 300  # 100 base * 3x
                    self.total_marks += 1
                    self._spawn_mark_particles(col, row)

        # BINGO check after auto-daub
        bingos = self._check_bingo()
        for _ in bingos:
            self.bingo_count += 1
            self.score += 500 * self.bingo_count
            self._spawn_bingo_particles()
            self.flash_timer = 3
            self._add_floating(2, 2, "BINGO!", YELLOW, 40, vy=-1.5, center=True)

        return count

    # -- particles & floating texts ------------------------------------------

    def _spawn_mark_particles(self, col: int, row: int) -> None:
        cx = GRID_X + col * STEP + CELL_SIZE // 2
        cy = GRID_Y + row * STEP + CELL_SIZE // 2
        cell_color = COLOR_MAP[self.cells[row][col].color][1]
        for _ in range(8):
            self.particles.append(
                Particle(
                    x=cx + random.uniform(-4, 4),
                    y=cy + random.uniform(-4, 4),
                    vx=random.uniform(-2, 2),
                    vy=random.uniform(-3, -1),
                    life=random.randint(15, 25),
                    color=cell_color,
                )
            )

    def _spawn_wrong_particles(self, col: int, row: int) -> None:
        cx = GRID_X + col * STEP + CELL_SIZE // 2
        cy = GRID_Y + row * STEP + CELL_SIZE // 2
        for _ in range(4):
            self.particles.append(
                Particle(
                    x=cx + random.uniform(-4, 4),
                    y=cy + random.uniform(-4, 4),
                    vx=random.uniform(-1, 1),
                    vy=random.uniform(-2, -0.5),
                    life=random.randint(10, 20),
                    color=GRAY,
                )
            )

    def _spawn_bingo_particles(self) -> None:
        cx = GRID_X + GRID_W // 2
        cy = GRID_Y + GRID_H // 2
        for _ in range(30):
            self.particles.append(
                Particle(
                    x=cx + random.uniform(-30, 30),
                    y=cy + random.uniform(-30, 30),
                    vx=random.uniform(-4, 4),
                    vy=random.uniform(-4, 4),
                    life=random.randint(15, 40),
                    color=random.choice(RAINBOW_COLORS),
                    size=3,
                )
            )

    def _add_floating(
        self,
        col: int,
        row: int,
        text: str,
        color: int,
        life: int,
        *,
        vy: float = -1.0,
        center: bool = False,
        at_y: float | None = None,
    ) -> None:
        if center:
            x = 160.0
            y = 130.0 if at_y is None else float(at_y)
        else:
            x = float(GRID_X + col * STEP + CELL_SIZE // 2)
            y = float(GRID_Y + row * STEP)
        self.floating_texts.append(FloatingText(x=x, y=y, text=text, life=life, color=color, vy=vy))

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def _update_floating_texts(self) -> None:
        alive: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life > 0:
                alive.append(ft)
        self.floating_texts = alive

    # -- per-frame update ----------------------------------------------------

    def update(self) -> None:
        self.title_blink = (self.title_blink + 1) % 60
        self.game_over_blink = (self.game_over_blink + 1) % 60

        if self.phase != Phase.PLAYING:
            return

        if self.flash_timer > 0:
            self.flash_timer -= 1

        self._update_super_daub()

        if self.shake_timer > 0:
            self.shake_timer -= 1

        self.call_timer -= 1
        if self.call_timer <= 0:
            if self.current_call_index < TOTAL_CALLS and not self._call_handled:
                self.missed += 1
            self._advance_call()

        self._update_particles()
        self._update_floating_texts()

    # -- drawing -------------------------------------------------------------

    def draw(self) -> None:
        pyxel.cls(NAVY)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.PLAYING, Phase.GAME_OVER):
            self._draw_game_board()

        # BINGO flash on top of everything
        if self.flash_timer > 0:
            pyxel.rect(0, 0, 320, 240, WHITE)

    # --- title screen -------------------------------------------------------

    def _draw_title(self) -> None:
        pyxel.text(112, 80, "BINGO SURGE", WHITE)
        pyxel.text(116, 96, "Color-Match Bingo", LIGHT_BLUE)
        pyxel.text(100, 122, "Click matching numbers", GRAY)
        pyxel.text(90, 137, "Same colour = COMBO chain!", GRAY)
        pyxel.text(90, 152, "COMBO 4+ = SUPER DAUB", YELLOW)
        pyxel.text(90, 167, "Wrong clicks build HEAT", ORANGE)
        pyxel.text(90, 182, "Complete lines for BINGO!", GREEN)
        if self.title_blink < 30:
            pyxel.text(100, 205, "Press SPACE to start", WHITE)

    # --- game / game-over screen --------------------------------------------

    def _draw_game_board(self) -> None:
        playing = self.phase == Phase.PLAYING

        # ---- caller / timer bar ----
        if self.current_call_index < TOTAL_CALLS:
            call = self.call_queue[self.current_call_index]
            call_color = COLOR_MAP[call.color][1]
            pyxel.text(70, 8, f"CALL: {call.number}", WHITE)
            pyxel.rect(156, 10, 16, 16, call_color)

            # colour label
            pyxel.text(176, 8, COLOR_NAMES[call.color], call_color)

            # timer bar
            ratio = max(0.0, self.call_timer / CALL_DELAY)
            bw = int(320 * ratio)
            if ratio > 0.66:
                bc = GREEN
            elif ratio > 0.33:
                bc = YELLOW
            else:
                bc = RED
            pyxel.rect(0, 30, bw, 4, bc)
            pyxel.rect(bw, 30, 320 - bw, 4, NAVY)

        if self.super_daub_timer > 0:
            frame_color = RAINBOW_COLORS[(pyxel.frame_count // 4) % len(RAINBOW_COLORS)]
            pyxel.text(208, 8, "SUPER!", frame_color)

        # ---- card ----
        ox, oy = 0, 0
        if self.shake_timer > 0:
            ox = random.randint(-3, 3)
            oy = random.randint(-3, 3)

        # rainbow border during super-daub
        if self.super_daub_timer > 0:
            fc = RAINBOW_COLORS[(pyxel.frame_count // 4) % len(RAINBOW_COLORS)]
            for t in range(2):
                pyxel.rectb(
                    GRID_X + ox - 3 - t,
                    GRID_Y + oy - 3 - t,
                    GRID_W + 6 + t * 2,
                    GRID_H + 6 + t * 2,
                    fc,
                )

        for row in range(5):
            for col in range(5):
                cell = self.cells[row][col]
                cx = GRID_X + col * STEP + ox
                cy = GRID_Y + row * STEP + oy

                bg_color = COLOR_MAP[cell.color][1 if cell.marked else 0]
                pyxel.rect(cx, cy, CELL_SIZE, CELL_SIZE, bg_color)
                if cell.marked:
                    pyxel.rectb(cx, cy, CELL_SIZE, CELL_SIZE, WHITE)

                if row == 2 and col == 2 and cell.marked:
                    pyxel.text(cx + 8, cy + 12, "FREE", WHITE)
                else:
                    num_str = str(cell.number)
                    tx = cx + (CELL_SIZE - len(num_str) * 4) // 2
                    pyxel.text(tx, cy + 12, num_str, WHITE)

        # ---- HUD ----
        if playing:
            pyxel.text(6, 218, f"SCORE: {self.score}", WHITE)
            pyxel.text(140, 218, f"COMBO: x{self.combo}", YELLOW)

            # heat bar
            pyxel.rect(236, 218, 78, 10, GRAY)
            hw = int(78 * self.heat / MAX_HEAT)
            pyxel.rect(236, 218, hw, 10, RED)
            pyxel.text(236, 230, f"HEAT {self.heat}%", WHITE)

            # super-daub remaining bar
            if self.super_daub_timer > 0:
                sr = self.super_daub_timer / SUPER_DAUB_DURATION
                sdw = int(314 * sr)
                pyxel.rect(3, 234, 314, 4, GRAY)
                sd_clr = RAINBOW_COLORS[(pyxel.frame_count // 4) % len(RAINBOW_COLORS)]
                pyxel.rect(3, 234, sdw, 4, sd_clr)

        # ---- particles ----
        for p in self.particles:
            pyxel.circ(int(p.x), int(p.y), p.size, p.color)

        # ---- floating texts ----
        for ft in self.floating_texts:
            if ft.life > 0:
                tx = int(ft.x) - len(ft.text) * 2
                pyxel.text(tx, int(ft.y), ft.text, ft.color)

        # ---- game-over overlay ----
        if not playing:
            pyxel.rect(45, 35, 230, 180, BLACK)
            pyxel.rectb(45, 35, 230, 180, WHITE)
            pyxel.text(112, 46, "GAME OVER", YELLOW)
            pyxel.text(60, 70, f"SCORE:      {self.score}", WHITE)
            pyxel.text(60, 86, f"BINGOs:     {self.bingo_count}", WHITE)
            pyxel.text(60, 102, f"MAX COMBO:  x{self.max_combo}", YELLOW)
            pyxel.text(60, 118, f"HITS:       {self.hits}/{TOTAL_CALLS}", WHITE)
            pyxel.text(60, 134, f"MISSED:     {self.missed}", GRAY)
            pyxel.text(60, 150, f"WRONG CLR:  {self.wrong_color}", GRAY)
            pyxel.text(60, 166, f"MARKS:      {self.total_marks}", GRAY)
            if self.game_over_blink < 30:
                pyxel.text(65, 190, "Press SPACE to retry", WHITE)


# ---------------------------------------------------------------------------
# Pyxel App
# ---------------------------------------------------------------------------

class App:
    def __init__(self) -> None:
        pyxel.init(320, 240, title="BINGO SURGE", display_scale=2)
        self.game = Game()
        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        g = self.game

        if g.phase == Phase.TITLE:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                g.reset()
        elif g.phase == Phase.PLAYING:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and g.shake_timer == 0:
                mx, my = pyxel.mouse_x, pyxel.mouse_y
                if GRID_X <= mx < GRID_X + GRID_W and GRID_Y <= my < GRID_Y + GRID_H:
                    col = (mx - GRID_X) // STEP
                    row = (my - GRID_Y) // STEP
                    lx = (mx - GRID_X) % STEP
                    ly = (my - GRID_Y) % STEP
                    if 0 <= col < 5 and 0 <= row < 5 and lx < CELL_SIZE and ly < CELL_SIZE:
                        g._handle_click(col, row)
        elif g.phase == Phase.GAME_OVER:
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                g.phase = Phase.TITLE

        g.update()

    def draw(self) -> None:
        self.game.draw()


def main() -> None:
    App()


if __name__ == "__main__":
    main()
