"""
Reversi Surge - Color-Match Reversi with COMBO chain flipping.

Concept: Place colored discs on an 8x8 board, sandwiching AI discs to flip them.
Same-color consecutive flips build COMBO chain. COMBO >= 4 triggers SUPER FLIP
(rainbow mode: all flips count as color-match, 3x score, 5 seconds).
Risk: wrong-color placements reset COMBO and add HEAT. HEAT >= 100 = game over.
Board fills up -> highest score wins.

Most Fun Moment: Landing 4 consecutive same-color flips to activate SUPER FLIP,
then watching the entire board chain-flip in rainbow mode for 3x score.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import pyxel

# -- Constants --
SCREEN_W = 320
SCREEN_H = 240
CELL = 28
BOARD_SIZE = 8
BOARD_X = (SCREEN_W - BOARD_SIZE * CELL) // 2  # 48
BOARD_Y = 8
BOARD_RIGHT = BOARD_X + BOARD_SIZE * CELL
BOARD_BOTTOM = BOARD_Y + BOARD_SIZE * CELL
DISC_R = 11
SUPER_DURATION = 300  # frames (5 seconds at 60fps)
HEAT_MAX = 100
AI_MOVE_DELAY = 30  # frames before AI responds

# Disc grid values
EMPTY = 0
COLOR_RED = 1
COLOR_GREEN = 2
COLOR_DARK_BLUE = 3
COLOR_YELLOW = 4
COLOR_AI = 5

# Display colors (raw pyxel ints)
DISC_COLORS: dict[int, int] = {
    COLOR_RED: 8,
    COLOR_GREEN: 3,
    COLOR_DARK_BLUE: 5,
    COLOR_YELLOW: 10,
    COLOR_AI: 13,
}
PLAYER_COLORS = [COLOR_RED, COLOR_GREEN, COLOR_DARK_BLUE, COLOR_YELLOW]
PLAYER_COLOR_NAMES = ["RED", "GRN", "BLU", "YEL"]

# Directions for sandwich check (8 directions)
DIRS: list[tuple[int, int]] = [
    (-1, 0), (-1, 1), (0, 1), (1, 1),
    (1, 0), (1, -1), (0, -1), (-1, -1),
]

# Pyxel raw color ints (for reference in drawing)
C_BLACK = 0
C_NAVY = 1
C_DARK_BLUE = 5
C_WHITE = 7
C_RED = 8
C_ORANGE = 9
C_YELLOW = 10
C_LIME = 11
C_CYAN = 12
C_GRAY = 13
C_PEACH = 15


class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class Turn(Enum):
    PLAYER = auto()
    AI = auto()


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
    color: int
    life: int
    vy: float  # floats upward


class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="REVERSI SURGE", display_scale=2)
        pyxel.mouse(True)
        self._pre_init_state()
        self.reset()
        pyxel.run(self.update, self.draw)

    def _pre_init_state(self) -> None:
        """Set all instance attributes before reset() for headless compatibility."""
        self.grid: list[list[int]] = []
        self.phase: Phase = Phase.TITLE
        self.turn: Turn = Turn.PLAYER
        self.player_color: int = COLOR_RED
        self.combo: int = 0
        self.max_combo: int = 0
        self.score: int = 0
        self.ai_score: int = 0
        self.heat: float = 0.0
        self.super_mode: bool = False
        self.super_timer: int = 0
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.hover_cell: Optional[tuple[int, int]] = None
        self.valid_moves: list[tuple[int, int]] = []
        self.game_over_reason: str = ""
        self.rng: random.Random = random.Random()
        self.shake_frames: int = 0
        self._ai_move_delay: int = 0
        self._last_placed_color: int = COLOR_RED

    def reset(self) -> None:
        """Initialize/reinitialize all game state."""
        self.grid = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.grid[3][3] = COLOR_RED
        self.grid[3][4] = COLOR_AI
        self.grid[4][3] = COLOR_AI
        self.grid[4][4] = COLOR_GREEN
        self.phase = Phase.TITLE
        self.turn = Turn.PLAYER
        self.player_color = COLOR_RED
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.ai_score = 0
        self.heat = 0.0
        self.super_mode = False
        self.super_timer = 0
        self.particles = []
        self.floating_texts = []
        self.hover_cell = None
        self.valid_moves = []
        self.game_over_reason = ""
        self.shake_frames = 0
        self._ai_move_delay = 0
        self._last_placed_color = COLOR_RED

    # -- Core Logic: Move Validation (testable, no pyxel calls) --

    @staticmethod
    def _is_opponent(cell_val: int, player_val: int) -> bool:
        """Check if a cell value belongs to the opponent of the given player."""
        if player_val == COLOR_AI:
            return cell_val in PLAYER_COLORS
        return cell_val == COLOR_AI

    @staticmethod
    def _in_bounds(col: int, row: int) -> bool:
        return 0 <= col < BOARD_SIZE and 0 <= row < BOARD_SIZE

    def _get_flippable(
        self, col: int, row: int, player_val: int
    ) -> list[tuple[int, int]]:
        """Return list of (col, row) tuples that would be flipped by placing at (col, row)."""
        result: list[tuple[int, int]] = []
        for dc, dr in DIRS:
            c, r = col + dc, row + dr
            path: list[tuple[int, int]] = []
            while self._in_bounds(c, r) and self._is_opponent(self.grid[r][c], player_val):
                path.append((c, r))
                c += dc
                r += dr
            if path and self._in_bounds(c, r) and self.grid[r][c] == player_val:
                result.extend(path)
        return result

    def _is_valid_move(self, col: int, row: int, player_val: int) -> bool:
        """Check if placing a disc at (col, row) is a valid Reversi move."""
        if not self._in_bounds(col, row):
            return False
        if self.grid[row][col] != EMPTY:
            return False
        return len(self._get_flippable(col, row, player_val)) > 0

    def _get_valid_moves_for(self, player_val: int) -> list[tuple[int, int]]:
        """Get all valid moves for a given player value."""
        moves: list[tuple[int, int]] = []
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if self._is_valid_move(col, row, player_val):
                    moves.append((col, row))
        return moves

    # -- Core Logic: Place Disc (testable) --

    def _place_disc(self, col: int, row: int, color: int) -> int:
        """Place disc, flip all sandwiched AI discs to color. Returns count of flipped discs."""
        flippable = self._get_flippable(col, row, color)
        self.grid[row][col] = color
        for fc, fr in flippable:
            self.grid[fr][fc] = color
        return len(flippable)

    def _count_color_matches(
        self, flippable: list[tuple[int, int]], target_color: int
    ) -> int:
        """Count how many flipped positions match the target color (were AI before flip)."""
        count = 0
        for fc, fr in flippable:
            # All flippable cells are COLOR_AI before flip,
            # we check if the placed color matches player_color
            if target_color == self.player_color:
                count += 1
        return count

    def _check_board_full(self) -> bool:
        """True if all 64 cells are non-empty."""
        for row in self.grid:
            for cell in row:
                if cell == EMPTY:
                    return False
        return True

    def _count_discs(self, color: int) -> int:
        """Count discs of a specific color on the board."""
        count = 0
        for row in self.grid:
            for cell in row:
                if cell == color:
                    count += 1
        return count

    # -- Heat System (testable) --

    def _update_heat(self) -> None:
        """Update heat: apply decay (0.02/frame) toward 0. Never goes below 0."""
        if self.heat > 0:
            self.heat = max(0.0, self.heat - 0.02)
        if self.heat < 0:
            self.heat = 0.0

    # -- SUPER Mode (testable) --

    def _activate_super(self) -> None:
        """Activate SUPER MODE: all flips count as color-match, 3x score multiplier."""
        self.super_mode = True
        self.super_timer = SUPER_DURATION

    def _update_super(self) -> None:
        """Decrement super timer, deactivate when 0."""
        if self.super_mode:
            self.super_timer -= 1
            if self.super_timer <= 0:
                self.super_mode = False
                self.super_timer = 0

    # -- Particles (testable with mock) --

    def _spawn_particles_burst(
        self, x: float, y: float, color: int, count: int
    ) -> None:
        """Spawn a particle burst at position."""
        for _ in range(count):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(0.5, 2.5)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=self.rng.randint(15, 30),
                    color=color,
                )
            )

    def _spawn_super_burst(self, x: float, y: float) -> None:
        """Spawn a rainbow particle burst for SUPER activation."""
        rainbow = [C_RED, C_ORANGE, C_YELLOW, C_LIME, C_CYAN, 12, 14, 15]
        for _ in range(50):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(0.5, 3.0)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=self.rng.randint(20, 40),
                    color=self.rng.choice(rainbow),
                )
            )

    def _spawn_floating_text(
        self, x: float, y: float, text: str, color: int
    ) -> None:
        """Spawn floating text at position."""
        self.floating_texts.append(
            FloatingText(x=x, y=y, text=text, color=color, life=30, vy=-0.5)
        )

    def _update_particles(self) -> None:
        """Update particle positions, decrement life, remove dead."""
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def _update_floating_texts(self) -> None:
        """Update floating text positions, decrement life, remove dead."""
        alive: list[FloatingText] = []
        for ft in self.floating_texts:
            ft.y += ft.vy
            ft.life -= 1
            if ft.life > 0:
                alive.append(ft)
        self.floating_texts = alive

    # -- AI Logic (testable) --

    def _ai_find_best_move(self) -> Optional[tuple[int, int]]:
        """Evaluate all valid AI moves, return the one that flips most player discs."""
        valid_moves = self._get_valid_moves_for(COLOR_AI)
        if not valid_moves:
            return None

        best_move: Optional[tuple[int, int]] = None
        best_count = -1
        for col, row in valid_moves:
            count = len(self._get_flippable(col, row, COLOR_AI))
            if count > best_count:
                best_count = count
                best_move = (col, row)
        return best_move

    def _ai_do_move(self) -> None:
        """Execute AI's best move."""
        best = self._ai_find_best_move()
        if best is None:
            # AI has no valid moves, generate heat penalty for player but skip
            self.heat = min(HEAT_MAX, self.heat + 5.0)
            self._spawn_floating_text(
                BOARD_X + BOARD_SIZE * CELL / 2,
                BOARD_Y + BOARD_SIZE * CELL / 2,
                "AI SKIPS",
                C_GRAY,
            )
            return
        col, row = best
        flipped_count = self._place_disc(col, row, COLOR_AI)
        self.ai_score += flipped_count * 5
        center_x = BOARD_X + col * CELL + CELL // 2
        center_y = BOARD_Y + row * CELL + CELL // 2
        self._spawn_particles_burst(center_x, center_y, DISC_COLORS[COLOR_AI], 10)

    # -- Player Action Handling (testable) --

    def _handle_color_select(self, color: int) -> None:
        """Set player_color to new color."""
        self.player_color = color

    def _handle_click(self, col: int, row: int) -> None:
        """Handle a click at grid position. Updates combo/score/heat.
        Does NOT call pyxel functions (spawning particles via internal methods is OK for tests with mock)."""
        if not self._is_valid_move(col, row, self.player_color):
            return

        # Get flippable cells before placing
        flippable = self._get_flippable(col, row, self.player_color)
        flipped_count = len(flippable)
        if flipped_count == 0:
            return

        # Place disc and flip
        self._place_disc(col, row, self.player_color)

        # Update combo: same-color consecutive or SUPER → increment; otherwise reset
        if self.super_mode or self.player_color == self._last_placed_color:
            self.combo += 1
            if self.combo > self.max_combo:
                self.max_combo = self.combo
            # Score: flipped_count * 10 * (1 + 0.5 * (combo - 1))
            multiplier = 1.0 + 0.5 * (self.combo - 1)
            if self.super_mode:
                multiplier *= 3.0
            points = int(flipped_count * 10 * multiplier)
            self.score += points
        else:
            # Color mismatch → reset combo, add heat
            self.combo = 0
            self.heat = min(HEAT_MAX, self.heat + 15.0)
            points = flipped_count * 10  # Base score only
            self.score += points
            self._spawn_floating_text(
                BOARD_X + col * CELL + CELL // 2,
                BOARD_Y + row * CELL + CELL // 2 - 10,
                "MISS!",
                C_ORANGE,
            )
        self._last_placed_color = self.player_color

        # Check COMBO >= 4 -> SUPER MODE
        if self.combo >= 4 and not self.super_mode:
            self._activate_super()
            cx = BOARD_X + col * CELL + CELL // 2
            cy = BOARD_Y + row * CELL + CELL // 2
            self.shake_frames = 15
            self._spawn_super_burst(cx, cy)
            self._spawn_floating_text(cx, cy - 10, "SUPER!", C_YELLOW)

        # Spawn particles for flipped discs
        for fc, fr in flippable:
            px = BOARD_X + fc * CELL + CELL // 2
            py = BOARD_Y + fr * CELL + CELL // 2
            disc_color = DISC_COLORS[self.player_color]
            if self.super_mode:
                disc_color = self.rng.choice([C_RED, C_ORANGE, C_YELLOW, C_LIME, C_CYAN])
            self._spawn_particles_burst(px, py, disc_color, 5)

        # Spawn floating score text
        self._spawn_floating_text(
            BOARD_X + col * CELL + CELL // 2,
            BOARD_Y + row * CELL + CELL // 2 - 20,
            f"+{points}",
            C_WHITE,
        )

        # Check board full
        if self._check_board_full():
            self.phase = Phase.GAME_OVER
            self.game_over_reason = "board_full"
            return

        # Switch to AI turn
        self.turn = Turn.AI
        self._ai_move_delay = AI_MOVE_DELAY

    # -- Update Methods (called each frame) --

    def _update_title_input(self) -> None:
        """Handle input on TITLE screen."""
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.phase = Phase.PLAYING
            self.grid = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
            self.grid[3][3] = COLOR_RED
            self.grid[3][4] = COLOR_AI
            self.grid[4][3] = COLOR_AI
            self.grid[4][4] = COLOR_GREEN
            self.turn = Turn.PLAYER
            self.player_color = COLOR_RED
            self.combo = 0
            self.max_combo = 0
            self.score = 0
            self.ai_score = 0
            self.heat = 0.0
            self.super_mode = False
            self.super_timer = 0
            self.particles = []
            self.floating_texts = []
            self.hover_cell = None
            self.valid_moves = []
            self.game_over_reason = ""
            self.shake_frames = 0
            self._ai_move_delay = 0
            self._last_placed_color = COLOR_RED

    def _update_playing_input(self) -> None:
        """Handle input on PLAYING screen."""
        mx = pyxel.mouse_x
        my = pyxel.mouse_y

        # Track hover cell
        self.hover_cell = None
        self.valid_moves = self._get_valid_moves_for(self.player_color)

        if (
            BOARD_X <= mx < BOARD_RIGHT
            and BOARD_Y <= my < BOARD_BOTTOM
            and self.turn == Turn.PLAYER
        ):
            col = (mx - BOARD_X) // CELL
            row = (my - BOARD_Y) // CELL
            if self._in_bounds(col, row):
                self.hover_cell = (col, row)

        # Mouse click on board
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and self.turn == Turn.PLAYER:
            # Check color palette clicks
            for i, color_val in enumerate(PLAYER_COLORS):
                px = BOARD_X + i * 52 + 8
                py = 220
                if px <= mx <= px + 48 and py <= my <= py + 20:
                    self._handle_color_select(color_val)
                    return

            # Check board click
            if self.hover_cell is not None:
                col, row = self.hover_cell
                if (col, row) in self.valid_moves:
                    self._handle_click(col, row)

    def _update_playing(self) -> None:
        """Update game logic during PLAYING phase."""
        # Update heat decay
        self._update_heat()

        # Check heat game over
        if self.heat >= HEAT_MAX:
            self.phase = Phase.GAME_OVER
            self.game_over_reason = "overheat"
            return

        # Update SUPER mode
        self._update_super()

        # Update screen shake
        if self.shake_frames > 0:
            self.shake_frames -= 1
            if self.shake_frames % 2 == 0:
                pyxel.camera(
                    self.rng.randint(-3, 3),
                    self.rng.randint(-3, 3),
                )
            else:
                pyxel.camera(0, 0)
        else:
            pyxel.camera(0, 0)

        # AI turn delay
        if self.turn == Turn.AI:
            if self._ai_move_delay > 0:
                self._ai_move_delay -= 1
            else:
                ai_valid = self._get_valid_moves_for(COLOR_AI)
                if not ai_valid:
                    # AI skips
                    self.turn = Turn.PLAYER
                    player_valid = self._get_valid_moves_for(self.player_color)
                    if not player_valid:
                        # Neither can move -> game over
                        self.phase = Phase.GAME_OVER
                        self.game_over_reason = "board_full"
                else:
                    self._ai_do_move()
                    if self._check_board_full():
                        self.phase = Phase.GAME_OVER
                        self.game_over_reason = "board_full"
                    else:
                        self.turn = Turn.PLAYER
                        # Check if player can move
                        if not self._get_valid_moves_for(self.player_color):
                            # Player skips, slight heat penalty
                            self.heat = min(HEAT_MAX, self.heat + 5.0)
                            self.turn = Turn.AI
                            self._ai_move_delay = AI_MOVE_DELAY

        # Update particles and floating texts
        self._update_particles()
        self._update_floating_texts()

    def _update_game_over_input(self) -> None:
        """Handle input on GAME_OVER screen."""
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()

    # -- Main Update/Draw --

    def update(self) -> None:
        """Main update loop."""
        if self.phase == Phase.TITLE:
            self._update_title_input()
        elif self.phase == Phase.PLAYING:
            self._update_playing_input()
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over_input()

    def draw(self) -> None:
        """Main draw loop."""
        pyxel.cls(C_BLACK)

        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase == Phase.PLAYING:
            self._draw_board()
            self._draw_discs()
            self._draw_valid_hints()
            self._draw_hover()
            self._draw_hud()
            self._draw_color_palette()
            self._draw_particles()
            self._draw_floating_texts()
        elif self.phase == Phase.GAME_OVER:
            self._draw_game_over()

    # -- Drawing Methods --

    def _draw_title(self) -> None:
        """Draw TITLE screen."""
        title = "REVERSI SURGE"
        pyxel.text(SCREEN_W // 2 - len(title) * 2 - 4, 60, title, C_WHITE)
        subtitle = "Color-Match Board Battle"
        pyxel.text(SCREEN_W // 2 - len(subtitle) * 2 + 2, 80, subtitle, C_LIME)

        # Rules
        rules = [
            "Match 4+ same-color flips for SUPER MODE",
            "SUPER: 3x score, all flips count",
            "Wrong color? COMBO resets + HEAT!",
            "HEAT 100 = GAME OVER",
            "",
            "Place discs to flip AI discs",
            "Select color from palette below",
            "",
            "Click or ENTER to start",
        ]
        for i, line in enumerate(rules):
            color = C_WHITE
            if "SUPER" in line:
                color = C_YELLOW
            elif "HEAT" in line and "GAME OVER" in line:
                color = C_RED
            elif "Click" in line:
                color = C_LIME
            pyxel.text(SCREEN_W // 2 - len(line) * 2, 110 + i * 10, line, color)

    def _draw_board(self) -> None:
        """Draw the 8x8 board grid."""
        # SUPER mode: rainbow border
        if self.super_mode:
            rainbow = [C_RED, C_ORANGE, C_YELLOW, C_LIME, C_CYAN, 12, 14]
            pulse = pyxel.frame_count // 4
            border_color = rainbow[pulse % len(rainbow)]
        else:
            border_color = C_WHITE

        # Grid lines
        for i in range(BOARD_SIZE + 1):
            x = BOARD_X + i * CELL
            y = BOARD_Y + i * CELL
            # Vertical lines
            pyxel.line(x, BOARD_Y, x, BOARD_BOTTOM, C_WHITE if not self.super_mode else border_color)
            # Horizontal lines
            pyxel.line(BOARD_X, y, BOARD_RIGHT, y, C_WHITE if not self.super_mode else border_color)

        # Board border
        pyxel.rectb(BOARD_X - 1, BOARD_Y - 1, BOARD_SIZE * CELL + 2, BOARD_SIZE * CELL + 2, border_color)

    def _draw_discs(self) -> None:
        """Draw all discs on the board."""
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                cell_val = self.grid[row][col]
                if cell_val == EMPTY:
                    continue

                cx = BOARD_X + col * CELL + CELL // 2
                cy = BOARD_Y + row * CELL + CELL // 2
                disc_color = DISC_COLORS.get(cell_val, C_GRAY)

                # SUPER mode: player discs pulse with rainbow
                if self.super_mode and cell_val in PLAYER_COLORS:
                    rainbow = [C_RED, C_ORANGE, C_YELLOW, C_LIME, C_CYAN, 12, 14]
                    pulse = (pyxel.frame_count // 6 + col + row) % len(rainbow)
                    disc_color = rainbow[pulse]

                pyxel.circ(cx, cy, DISC_R, disc_color)
                # Subtle highlight
                if cell_val != COLOR_AI:
                    pyxel.circb(cx, cy, DISC_R, C_WHITE)
                else:
                    pyxel.circb(cx, cy, DISC_R, C_DARK_BLUE)

    def _draw_valid_hints(self) -> None:
        """Draw dim circles on valid move cells."""
        if self.turn != Turn.PLAYER:
            return
        for col, row in self.valid_moves:
            cx = BOARD_X + col * CELL + CELL // 2
            cy = BOARD_Y + row * CELL + CELL // 2
            # Dim hint circle
            pyxel.circb(cx, cy, 6, DISC_COLORS[self.player_color])

    def _draw_hover(self) -> None:
        """Draw hover highlight on the cell under mouse."""
        if self.hover_cell is None or self.turn != Turn.PLAYER:
            return
        col, row = self.hover_cell
        x = BOARD_X + col * CELL
        y = BOARD_Y + row * CELL
        is_valid = (col, row) in self.valid_moves
        if is_valid:
            pyxel.rectb(x, y, CELL, CELL, C_WHITE)
        else:
            pyxel.rectb(x, y, CELL, CELL, C_GRAY)

    def _draw_hud(self) -> None:
        """Draw HUD: score, combo, heat bar, super timer, turn indicator."""
        # Left panel
        x = 2
        y = 8

        # Title/logo
        pyxel.text(x, y, "REVERSI SURGE", C_WHITE)
        y += 12

        # Score
        pyxel.text(x, y, f"Score: {self.score}", C_WHITE)
        y += 10

        # AI Score
        pyxel.text(x, y, f"AI: {self.ai_score}", C_GRAY)
        y += 10

        # Combo
        combo_color = C_WHITE
        if self.combo >= 3:
            combo_color = C_ORANGE
        if self.combo >= 4:
            combo_color = C_YELLOW
        pyxel.text(x, y, f"COMBO: {self.combo}", combo_color)
        y += 10

        # Max combo
        pyxel.text(x, y, f"MAX: {self.max_combo}", C_LIME)
        y += 12

        # Turn indicator
        turn_text = "YOUR TURN" if self.turn == Turn.PLAYER else "AI TURN.."
        turn_color = C_LIME if self.turn == Turn.PLAYER else C_GRAY
        pyxel.text(x, y, turn_text, turn_color)
        y += 12

        # Selected color
        pyxel.text(x, y, "Color:", C_WHITE)
        pyxel.rect(x + 30, y, 10, 10, DISC_COLORS[self.player_color])
        y += 14

        # SUPER mode indicator
        if self.super_mode:
            rainbow = [C_RED, C_ORANGE, C_YELLOW, C_LIME, C_CYAN, 12, 14]
            pulse = pyxel.frame_count // 4
            super_color = rainbow[pulse % len(rainbow)]
            pyxel.text(x, y, "SUPER!", super_color)
            pyxel.text(x, y + 10, f"{self.super_timer // 60 + 1}s", super_color)
            y += 20

        # Heat bar (vertical, right side of HUD)
        heat_x = BOARD_X - 10
        heat_y = BOARD_Y
        heat_w = 6
        heat_h = BOARD_SIZE * CELL
        pyxel.rect(heat_x, heat_y, heat_w, heat_h, C_NAVY)
        heat_pixels = int((self.heat / HEAT_MAX) * heat_h)
        # Heat color goes from green to red
        if self.heat < 30:
            heat_bar_color = C_LIME
        elif self.heat < 60:
            heat_bar_color = C_YELLOW
        elif self.heat < 80:
            heat_bar_color = C_ORANGE
        else:
            heat_bar_color = C_RED
        pyxel.rect(
            heat_x,
            heat_y + heat_h - heat_pixels,
            heat_w,
            heat_pixels,
            heat_bar_color,
        )
        pyxel.rectb(heat_x, heat_y, heat_w, heat_h, C_WHITE)
        # Label
        pyxel.text(heat_x - 6, heat_y + heat_h + 4, "H", C_RED)
        pyxel.text(heat_x - 6, heat_y + heat_h + 12, "E", C_RED)
        pyxel.text(heat_x - 6, heat_y + heat_h + 20, "A", C_RED)
        pyxel.text(heat_x - 6, heat_y + heat_h + 28, "T", C_RED)

        # Score in big text top-right
        pyxel.text(BOARD_RIGHT + 2, BOARD_Y, f"{self.score:04d}", C_WHITE)

    def _draw_color_palette(self) -> None:
        """Draw the 4-color selection palette at bottom."""
        pyxel.text(BOARD_X, 208, "Select Color:", C_WHITE)
        for i, color_val in enumerate(PLAYER_COLORS):
            px = BOARD_X + i * 52 + 8
            py = 220
            # Background
            pyxel.rect(px, py, 48, 20, DISC_COLORS[color_val])
            # Border (highlight selected)
            if color_val == self.player_color and self.turn == Turn.PLAYER:
                pyxel.rectb(px - 1, py - 1, 50, 22, C_WHITE)
            else:
                pyxel.rectb(px, py, 48, 20, C_DARK_BLUE)
            # Color name
            name = PLAYER_COLOR_NAMES[i]
            pyxel.text(px + 12, py + 6, name, C_WHITE)

    def _draw_particles(self) -> None:
        """Draw all active particles."""
        for p in self.particles:
            alpha = min(1.0, p.life / 15.0)
            if alpha > 0.3:
                size = max(1, int(2 * alpha))
                pyxel.rect(int(p.x), int(p.y), size, size, p.color)

    def _draw_floating_texts(self) -> None:
        """Draw all active floating texts."""
        for ft in self.floating_texts:
            alpha = min(1.0, ft.life / 30.0)
            if alpha > 0.2:
                pyxel.text(int(ft.x) - len(ft.text) * 2, int(ft.y), ft.text, ft.color)

    def _draw_game_over(self) -> None:
        """Draw GAME OVER screen."""
        # Title
        pyxel.text(SCREEN_W // 2 - 24, 50, "GAME OVER", C_RED)

        # Reason
        if self.game_over_reason == "overheat":
            reason = "REACTOR OVERHEAT!"
            pyxel.text(SCREEN_W // 2 - len(reason) * 2, 70, reason, C_ORANGE)
        else:
            reason = "BOARD FULL"
            pyxel.text(SCREEN_W // 2 - len(reason) * 2, 70, reason, C_LIME)

        # Score
        score_text = f"Score: {self.score}"
        pyxel.text(SCREEN_W // 2 - len(score_text) * 2, 90, score_text, C_WHITE)

        # AI score
        ai_text = f"AI Score: {self.ai_score}"
        pyxel.text(SCREEN_W // 2 - len(ai_text) * 2, 105, ai_text, C_GRAY)

        # Result
        if self.score > self.ai_score:
            result = "YOU WIN!"
            result_color = C_YELLOW
        elif self.score < self.ai_score:
            result = "AI WINS..."
            result_color = C_GRAY
        else:
            result = "DRAW"
            result_color = C_WHITE
        pyxel.text(SCREEN_W // 2 - len(result) * 2, 125, result, result_color)

        # Max combo
        combo_text = f"Max COMBO: {self.max_combo}"
        pyxel.text(SCREEN_W // 2 - len(combo_text) * 2, 145, combo_text, C_ORANGE)

        # Heat
        heat_text = f"Final Heat: {int(self.heat)}"
        pyxel.text(SCREEN_W // 2 - len(heat_text) * 2, 160, heat_text, C_RED)

        # Restart hint
        hint = "Click or ENTER to Retry"
        pyxel.text(SCREEN_W // 2 - len(hint) * 2, 190, hint, C_LIME)


class GameHeadless(Game):
    """Headless Game for testing - skips pyxel.init/run."""

    def __init__(self) -> None:
        self._pre_init_state()
        self.reset()


if __name__ == "__main__":
    Game()
