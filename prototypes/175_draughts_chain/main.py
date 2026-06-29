"""
Draughts Chain — Checkers with color-match COMBO chains.
Same-color consecutive captures build a COMBO chain.
COMBO >= 4 activates SUPER KING: 300 frames rainbow mode, 3x score.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto

import pyxel

# ============================================================
# Constants
# ============================================================
SCREEN_W = 320
SCREEN_H = 240
CELL = 28
OX = 48
OY = 8

# Colors (raw ints)
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

PLAYER_COLORS: list[int] = [RED, GREEN, DARK_BLUE, YELLOW]
PLAYER_COLORS_PER_TYPE = 3
AI_COLOR = GRAY

PIECE_RADIUS = 11
DOT_RADIUS = 3
KING_CROWN_H = 3

BASE_CAPTURE_SCORE = 100
COMBO_MULT_BASE = 1.0
COMBO_MULT_STEP = 0.5
SUPER_KING_THRESHOLD = 4
SUPER_KING_DURATION = 300
SUPER_KING_SCORE_MULT = 3
HEAT_MAX = 100.0
HEAT_WRONG_CAPTURE = 15.0
HEAT_DECAY = 0.02
ECHO_STONE_BONUS = 50
ECHO_SPREAD_INTERVAL = 30
AI_THINK_DELAY = 15
MESSAGE_DURATION = 60

HEAT_BAR_W = 200
HEAT_BAR_H = 6
HEAT_BAR_X = (SCREEN_W - HEAT_BAR_W) // 2
HEAT_BAR_Y = 232


# ============================================================
# Enums & Data Classes
# ============================================================
class Phase(Enum):
    TITLE = auto()
    PLAYING = auto()
    GAME_OVER = auto()


class PieceType(Enum):
    MAN = auto()
    KING = auto()


@dataclass
class Piece:
    color: int
    ptype: PieceType
    row: int
    col: int


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


# Move result type: (dest_col, dest_row, [(cap_col, cap_row), ...], is_capture)
MoveResult = tuple[int, int, list[tuple[int, int]], bool]


# ============================================================
# Game Class
# ============================================================
class Game:
    def __init__(self) -> None:
        pyxel.init(SCREEN_W, SCREEN_H, title="Draughts Chain", display_scale=2)
        self._rng: random.Random = random.Random()
        self.reset()
        pyxel.run(self.update, self.draw)

    # ---- State initialization ----

    def reset(self) -> None:
        self.phase = Phase.TITLE
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.heat: float = 0.0
        self.super_king_timer = 0
        self.echo_stones: set[tuple[int, int]] = set()
        self.selected_piece: Piece | None = None
        self.valid_moves: list[MoveResult] = []
        self.player_turn = True
        self.particles: list[Particle] = []
        self.floating_texts: list[FloatingText] = []
        self.message = ""
        self.message_timer = 0
        self.game_over_message = ""
        self._won = False
        self._game_timer = 0
        self._ai_think_timer = 0
        self._chain_color = -1
        self._pending_chain: list[tuple[int, int]] = []

        self.player_pieces: list[Piece] = []
        self.ai_pieces: list[Piece] = []
        self._init_pieces()

    def _init_pieces(self) -> None:
        self.player_pieces.clear()
        self.ai_pieces.clear()

        # Player pieces: rows 0-2, dark squares
        player_positions: list[tuple[int, int]] = []
        for row in range(3):
            for col in range(8):
                if (row + col) % 2 == 1:
                    player_positions.append((col, row))

        # 12 pieces, 3 of each color
        colors: list[int] = []
        for c in PLAYER_COLORS:
            colors.extend([c] * PLAYER_COLORS_PER_TYPE)
        self._rng.shuffle(colors)

        for (col, row), color in zip(player_positions, colors):
            self.player_pieces.append(Piece(color=color, ptype=PieceType.MAN, row=row, col=col))

        # AI pieces: rows 5-7, dark squares
        ai_positions: list[tuple[int, int]] = []
        for row in range(5, 8):
            for col in range(8):
                if (row + col) % 2 == 1:
                    ai_positions.append((col, row))

        # AI pieces get colors from PLAYER_COLORS for combo mechanic
        ai_colors: list[int] = []
        for c in PLAYER_COLORS:
            ai_colors.extend([c] * PLAYER_COLORS_PER_TYPE)
        self._rng.shuffle(ai_colors)

        for (col, row), color in zip(ai_positions, ai_colors):
            self.ai_pieces.append(Piece(color=color, ptype=PieceType.MAN, row=row, col=col))

    # ---- Phase machine ----

    def update(self) -> None:
        self._game_timer += 1
        self._update_particles()
        self._update_floating_texts()

        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()

        if self.phase == Phase.TITLE:
            self._update_title()
        elif self.phase == Phase.PLAYING:
            self._update_playing()
        elif self.phase == Phase.GAME_OVER:
            self._update_game_over()

    def draw(self) -> None:
        pyxel.cls(BLACK)
        if self.phase == Phase.TITLE:
            self._draw_title()
        elif self.phase in (Phase.PLAYING, Phase.GAME_OVER):
            self._draw_board()
            self._draw_echo_stones()
            self._draw_valid_moves()
            self._draw_pieces()
            self._draw_particles()
            self._draw_heat_bar()
            self._draw_ui()
            if self.phase == Phase.GAME_OVER:
                self._draw_game_over_overlay()

    # ---- Title ----

    def _update_title(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.PLAYING

    def _draw_title(self) -> None:
        title = "DRAUGHTS CHAIN"
        tw = len(title) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 60, title, WHITE)

        lines = [
            "Click to Start",
            "",
            "Match captured piece colors",
            "for COMBO chains!",
            "",
            "COMBO 4+ = SUPER KING",
            "Wrong color = HEAT",
            "HEAT 100 = OVERHEAT",
        ]
        for i, line in enumerate(lines):
            pyxel.text(SCREEN_W // 2 - len(line) * 2, 100 + i * 10, line, GRAY)

        # Color legend
        legend_y = 200
        pyxel.text(SCREEN_W // 2 - 30, legend_y, "Colors:", GRAY)
        for i, c in enumerate(PLAYER_COLORS):
            px = SCREEN_W // 2 - 24 + i * 22
            pyxel.circ(px + 3, legend_y + 12, 4, c)
            pyxel.circb(px + 3, legend_y + 12, 4, WHITE)

    # ---- Playing ----

    def _update_playing(self) -> None:
        # Message timer
        if self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer == 0:
                self.message = ""

        # Heat decay
        self.heat = max(0.0, self.heat - HEAT_DECAY)

        # SUPER KING timer
        if self.super_king_timer > 0:
            self.super_king_timer -= 1
            if self.super_king_timer == 0:
                self.combo = 0
                self._chain_color = -1

        # Echo stone spread
        if self._game_timer % ECHO_SPREAD_INTERVAL == 0:
            self._spread_echo_stones()

        # Check game over
        if self._check_game_over():
            self.phase = Phase.GAME_OVER
            return

        if self.player_turn:
            self._handle_player_input()
        else:
            self._ai_turn()

    def _handle_player_input(self) -> None:
        if not pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            return

        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        col = (mx - OX) // CELL
        row = (my - OY) // CELL

        if not self._is_valid_square(col, row):
            return

        clicked_piece = self._get_piece_at(col, row)
        clicked_empty = not clicked_piece

        # If continuing a chain capture, only allow selecting the active piece's destinations
        if self._pending_chain:
            active_piece = self._pending_chain_piece()
            if active_piece is None:
                self._pending_chain.clear()
                return
            # Check if clicked a valid move for the active piece
            moves = self._get_valid_moves_captures_only(active_piece)
            for dest_col, dest_row, caps, _ in moves:
                if col == dest_col and row == dest_row:
                    self._execute_and_switch(active_piece, dest_col, dest_row, caps)
                    # Check for further captures after this jump
                    if self._get_single_captures(
                        active_piece.col, active_piece.row,
                        active_piece.ptype,
                        self._is_player_piece(active_piece),
                        frozenset(),
                    ):
                        self._pending_chain = []  # more captures possible, compute new valid moves next frame
                        self.selected_piece = active_piece
                        self.valid_moves = self._get_valid_moves_captures_only(active_piece)
                    else:
                        self._pending_chain.clear()
                        self.selected_piece = None
                        self.valid_moves.clear()
                        self.player_turn = False
                        self._ai_think_timer = AI_THINK_DELAY
                    return
            return

        # Normal selection
        if clicked_piece and clicked_piece in self.player_pieces:
            if self.selected_piece is clicked_piece:
                # Deselect
                self.selected_piece = None
                self.valid_moves.clear()
            else:
                self.selected_piece = clicked_piece
                self.valid_moves = self._get_valid_moves(clicked_piece)
        elif clicked_empty and self.selected_piece is not None:
            # Try to move to clicked destination
            for dest_col, dest_row, caps, is_capture in self.valid_moves:
                if col == dest_col and row == dest_row:
                    self._execute_and_switch(self.selected_piece, dest_col, dest_row, caps)
                    if is_capture:
                        # Check if further captures available
                        if self._get_single_captures(
                            self.selected_piece.col, self.selected_piece.row,
                            self.selected_piece.ptype,
                            True,
                            frozenset(),
                        ):
                            self._pending_chain = caps
                            self.valid_moves = self._get_valid_moves_captures_only(
                                self.selected_piece
                            )
                        else:
                            self.selected_piece = None
                            self.valid_moves.clear()
                            self.player_turn = False
                            self._ai_think_timer = AI_THINK_DELAY
                    else:
                        self.selected_piece = None
                        self.valid_moves.clear()
                        self.player_turn = False
                        self._ai_think_timer = AI_THINK_DELAY
                    return
            # Clicked empty but not a valid destination
            self.selected_piece = None
            self.valid_moves.clear()
        else:
            self.selected_piece = None
            self.valid_moves.clear()

    def _pending_chain_piece(self) -> Piece | None:
        if self.selected_piece is not None and self.selected_piece in self.player_pieces:
            return self.selected_piece
        return None

    def _execute_and_switch(
        self, piece: Piece, dest_col: int, dest_row: int, captures: list[tuple[int, int]]
    ) -> None:
        """Execute a move/capture and handle effects. Does NOT switch turn (caller decides)."""
        is_capture = len(captures) > 0
        self._execute_move(piece, dest_col, dest_row, captures, is_capture)

    # ---- Game Over ----

    def _update_game_over(self) -> None:
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.reset()
            self.phase = Phase.TITLE

    def _draw_game_over_overlay(self) -> None:
        # Semi-transparent overlay
        for y in range(0, SCREEN_H, 2):
            for x in range(0, SCREEN_W, 2):
                if (x // 2 + y // 2) % 2 == 0:
                    pyxel.pset(x, y, BLACK)

        msg = self.game_over_message
        tw = len(msg) * 4
        pyxel.text(SCREEN_W // 2 - tw // 2, 80, msg, PINK if self._won else ORANGE)

        score_text = f"SCORE: {self.score}"
        stw = len(score_text) * 4
        pyxel.text(SCREEN_W // 2 - stw // 2, 100, score_text, WHITE)

        combo_text = f"MAX COMBO: {self.max_combo}"
        ctw = len(combo_text) * 4
        pyxel.text(SCREEN_W // 2 - ctw // 2, 115, combo_text, YELLOW)

        restart = "Click to Restart"
        rtw = len(restart) * 4
        pyxel.text(SCREEN_W // 2 - rtw // 2, 150, restart, GRAY)

    # ---- Board rendering ----

    def _draw_board(self) -> None:
        # Board background
        for row in range(8):
            for col in range(8):
                x = OX + col * CELL
                y = OY + row * CELL
                is_dark = (row + col) % 2 == 1
                color = BLACK if is_dark else WHITE
                pyxel.rect(x, y, CELL, CELL, color)

        # Board border
        pyxel.rectb(OX - 1, OY - 1, CELL * 8 + 2, CELL * 8 + 2, NAVY)

    def _draw_pieces(self) -> None:
        # Player pieces
        for p in self.player_pieces:
            self._draw_piece(p, p is self.selected_piece)
        # AI pieces
        for p in self.ai_pieces:
            self._draw_piece(p, False)

    def _draw_piece(self, piece: Piece, selected: bool) -> None:
        cx = OX + piece.col * CELL + CELL // 2
        cy = OY + piece.row * CELL + CELL // 2

        color = piece.color
        if self.super_king_timer > 0 and piece in self.player_pieces:
            # Rainbow cycling for SUPER KING piece
            idx = (pyxel.frame_count // 4) % len(PLAYER_COLORS)
            color = PLAYER_COLORS[idx]

        # Piece body
        pyxel.circ(cx, cy, PIECE_RADIUS, color)
        pyxel.circb(cx, cy, PIECE_RADIUS, WHITE)

        # SUPER KING glow
        if self.super_king_timer > 0 and piece in self.player_pieces:
            glow_radius = PIECE_RADIUS + 3 + (pyxel.frame_count % 8) // 4
            pyxel.circb(cx, cy, glow_radius, PINK)

        # King crown
        if piece.ptype == PieceType.KING:
            pyxel.tri(cx - 4, cy - PIECE_RADIUS + 2, cx, cy - PIECE_RADIUS - KING_CROWN_H, cx + 4, cy - PIECE_RADIUS + 2, YELLOW)

        # Selection highlight
        if selected:
            pyxel.circb(cx, cy, PIECE_RADIUS + 2, CYAN)

    def _draw_echo_stones(self) -> None:
        pulse = pyxel.frame_count % 30
        alpha_phase = pulse < 15
        for col, row in self.echo_stones:
            cx = OX + col * CELL + CELL // 2
            cy = OY + row * CELL + CELL // 2
            if alpha_phase or pulse % 5 < 3:
                pyxel.circ(cx, cy, DOT_RADIUS, PURPLE)

    def _draw_valid_moves(self) -> None:
        for dest_col, dest_row, _caps, is_capture in self.valid_moves:
            cx = OX + dest_col * CELL + CELL // 2
            cy = OY + dest_row * CELL + CELL // 2
            if is_capture:
                pyxel.circ(cx, cy, DOT_RADIUS + 2, CYAN)
                pyxel.circb(cx, cy, DOT_RADIUS + 2, WHITE)
            else:
                pyxel.circ(cx, cy, DOT_RADIUS, CYAN)

    def _draw_particles(self) -> None:
        for p in self.particles:
            pyxel.pset(int(p.x), int(p.y), p.color)

    def _draw_heat_bar(self) -> None:
        # Label
        pyxel.text(HEAT_BAR_X - 20, HEAT_BAR_Y, "HEAT", ORANGE)

        # Background
        pyxel.rect(HEAT_BAR_X, HEAT_BAR_Y, HEAT_BAR_W, HEAT_BAR_H, GRAY)

        # Fill
        fill_w = int(HEAT_BAR_W * self.heat / HEAT_MAX)
        bar_color = PINK if self.heat > 80 else ORANGE
        if fill_w > 0:
            pyxel.rect(HEAT_BAR_X, HEAT_BAR_Y, fill_w, HEAT_BAR_H, bar_color)

        # Border
        pyxel.rectb(HEAT_BAR_X, HEAT_BAR_Y, HEAT_BAR_W, HEAT_BAR_H, WHITE)

    def _draw_ui(self) -> None:
        # Score (top-left)
        score_text = f"SCORE:{self.score:05d}"
        pyxel.text(2, 2, score_text, WHITE)

        # Combo (top-right, in board area)
        if self.combo > 0:
            combo_text = f"COMBO:x{self.combo}"
            cx = OX + CELL * 8 + 4
            pyxel.text(cx, OY, combo_text, YELLOW if self.combo < SUPER_KING_THRESHOLD else PINK)

        # SUPER KING timer
        if self.super_king_timer > 0:
            sk_text = f"SUPER:{self.super_king_timer // 60 + 1}s"
            pyxel.text(OX + CELL * 8 + 4, OY + 12, sk_text, PINK)

        # Message
        if self.message and self.message_timer > 0:
            mw = len(self.message) * 4
            pyxel.text(SCREEN_W // 2 - mw // 2, SCREEN_H - 16, self.message, WHITE)

        # Floating texts
        for ft in self.floating_texts:
            pyxel.text(int(ft.x), int(ft.y) - (40 - ft.life) // 3, ft.text, ft.color)

        # Turn indicator
        if self.phase == Phase.PLAYING:
            turn_text = "YOUR TURN" if self.player_turn else "AI THINKING..."
            tw = len(turn_text) * 4
            pyxel.text(SCREEN_W // 2 - tw // 2, OY - 2 if OY >= 10 else 2, turn_text, WHITE if self.player_turn else GRAY)

    # ---- Core geometry helpers ----

    @staticmethod
    def _is_valid_square(col: int, row: int) -> bool:
        return 0 <= col < 8 and 0 <= row < 8

    def _get_piece_at(self, col: int, row: int) -> Piece | None:
        for p in self.player_pieces:
            if p.col == col and p.row == row:
                return p
        for p in self.ai_pieces:
            if p.col == col and p.row == row:
                return p
        return None

    def _is_player_piece(self, piece: Piece) -> bool:
        return piece in self.player_pieces

    # ---- Move computation ----

    def _get_simple_moves(
        self, col: int, row: int, ptype: PieceType, is_player: bool
    ) -> list[tuple[int, int]]:
        moves: list[tuple[int, int]] = []
        forward = 1 if is_player else -1

        if ptype == PieceType.MAN:
            dy_dirs = [forward]
        else:
            dy_dirs = [-1, 1]

        for dx in (-1, 1):
            for dy in dy_dirs:
                nc, nr = col + dx, row + dy
                if self._is_valid_square(nc, nr) and self._get_piece_at(nc, nr) is None:
                    moves.append((nc, nr))
        return moves

    def _get_single_captures(
        self,
        col: int,
        row: int,
        ptype: PieceType,
        is_player: bool,
        removed: frozenset[tuple[int, int]],
    ) -> list[tuple[int, int, int, int]]:
        """Returns list of (cap_col, cap_row, dest_col, dest_row)."""
        captures: list[tuple[int, int, int, int]] = []
        forward = 1 if is_player else -1
        if ptype == PieceType.MAN:
            dy_dirs = [forward]
        else:
            dy_dirs = [-1, 1]

        for dx in (-1, 1):
            for dy in dy_dirs:
                cap_col = col + dx
                cap_row = row + dy
                dest_col = col + dx * 2
                dest_row = row + dy * 2

                if not self._is_valid_square(dest_col, dest_row):
                    continue
                if (cap_col, cap_row) in removed:
                    continue
                if self._get_piece_at(dest_col, dest_row) is not None:
                    continue

                cap_piece = self._get_piece_at(cap_col, cap_row)
                if cap_piece is None:
                    continue
                if (cap_piece.col, cap_piece.row) in removed:
                    continue
                # Must be enemy piece
                if self._is_player_piece(cap_piece) == is_player:
                    continue

                captures.append((cap_col, cap_row, dest_col, dest_row))
        return captures

    def _get_capture_chains(
        self,
        col: int,
        row: int,
        ptype: PieceType,
        is_player: bool,
        removed: frozenset[tuple[int, int]] = frozenset(),
    ) -> list[tuple[int, int, list[tuple[int, int]]]]:
        """Returns list of (final_col, final_row, [(cap_col, cap_row), ...])."""
        chains: list[tuple[int, int, list[tuple[int, int]]]] = []
        singles = self._get_single_captures(col, row, ptype, is_player, removed)

        for cap_col, cap_row, dest_col, dest_row in singles:
            new_removed = removed | {(cap_col, cap_row)}
            new_ptype = ptype
            if ptype == PieceType.MAN:
                if is_player and dest_row == 7:
                    new_ptype = PieceType.KING
                elif not is_player and dest_row == 0:
                    new_ptype = PieceType.KING

            sub_chains = self._get_capture_chains(
                dest_col, dest_row, new_ptype, is_player, new_removed
            )
            if sub_chains:
                for sub_dest_col, sub_dest_row, sub_caps in sub_chains:
                    chains.append(
                        (sub_dest_col, sub_dest_row, [(cap_col, cap_row)] + sub_caps)
                    )
            else:
                chains.append((dest_col, dest_row, [(cap_col, cap_row)]))
        return chains

    def _get_valid_moves(self, piece: Piece) -> list[MoveResult]:
        result: list[MoveResult] = []
        is_player = self._is_player_piece(piece)
        chains = self._get_capture_chains(
            piece.col, piece.row, piece.ptype, is_player
        )

        for dest_col, dest_row, caps in chains:
            result.append((dest_col, dest_row, caps, True))

        # If no captures for this piece, and no global captures required, show moves
        if not chains:
            global_captures = self._has_any_captures_for_side(is_player)
            if not global_captures:
                moves = self._get_simple_moves(
                    piece.col, piece.row, piece.ptype, is_player
                )
                for dest_col, dest_row in moves:
                    result.append((dest_col, dest_row, [], False))
        return result

    def _get_valid_moves_captures_only(self, piece: Piece) -> list[MoveResult]:
        """Get only capture moves (for chain continuation)."""
        result: list[MoveResult] = []
        is_player = self._is_player_piece(piece)
        chains = self._get_capture_chains(
            piece.col, piece.row, piece.ptype, is_player
        )
        for dest_col, dest_row, caps in chains:
            result.append((dest_col, dest_row, caps, True))
        return result

    def _has_any_captures(self) -> bool:
        return self._has_any_captures_for_side(True)

    def _has_any_captures_for_side(self, is_player: bool) -> bool:
        pieces = self.player_pieces if is_player else self.ai_pieces
        for p in pieces:
            if self._get_single_captures(
                p.col, p.row, p.ptype, is_player, frozenset()
            ):
                return True
        return False

    # ---- Move execution ----

    def _execute_move(
        self,
        piece: Piece,
        dest_col: int,
        dest_row: int,
        captures: list[tuple[int, int]],
        is_capture: bool,
    ) -> int:
        score_earned = 0
        is_player = self._is_player_piece(piece)

        # Collect PRE-EXISTING echo stones BEFORE adding new ones
        for cap_col, cap_row in captures:
            if (cap_col, cap_row) in self.echo_stones:
                self.echo_stones.discard((cap_col, cap_row))
                bonus = ECHO_STONE_BONUS
                if is_player and self.super_king_timer > 0:
                    bonus *= SUPER_KING_SCORE_MULT
                score_earned += bonus
                cx = OX + cap_col * CELL + CELL // 2
                cy = OY + cap_row * CELL + CELL // 2
                self._add_floating_text(cx, cy, f"+{bonus}", PURPLE, 30)

        if (dest_col, dest_row) in self.echo_stones:
            self.echo_stones.discard((dest_col, dest_row))
            bonus = ECHO_STONE_BONUS
            if is_player and self.super_king_timer > 0:
                bonus *= SUPER_KING_SCORE_MULT
            score_earned += bonus
            cx = OX + dest_col * CELL + CELL // 2
            cy = OY + dest_row * CELL + CELL // 2
            self._add_floating_text(cx, cy, f"+{bonus}", PURPLE, 30)

        # Remove captured pieces and add echo stones
        captured_colors: list[int] = []
        for cap_col, cap_row in captures:
            cap_piece = self._get_piece_at(cap_col, cap_row)
            if cap_piece:
                captured_colors.append(cap_piece.color)
                if cap_piece in self.player_pieces:
                    self.player_pieces.remove(cap_piece)
                else:
                    self.ai_pieces.remove(cap_piece)
                self.echo_stones.add((cap_col, cap_row))
                cx = OX + cap_col * CELL + CELL // 2
                cy = OY + cap_row * CELL + CELL // 2
                self._spawn_particles(cx, cy, 10, cap_piece.color, (-2.0, 2.0))
            else:
                captured_colors.append(-1)

        # Move the piece
        piece.col = dest_col
        piece.row = dest_row

        # King promotion
        if piece.ptype == PieceType.MAN:
            if is_player and piece.row == 7:
                piece.ptype = PieceType.KING
                cx = OX + piece.col * CELL + CELL // 2
                cy = OY + piece.row * CELL + CELL // 2
                self._spawn_particles(cx, cy, 15, YELLOW, (-3.0, 3.0))
                self._add_floating_text(cx, cy - 10, "KING!", YELLOW, 40)
            elif not is_player and piece.row == 0:
                piece.ptype = PieceType.KING

        # Combo and scoring for player captures
        if is_player and is_capture:
            for color in captured_colors:
                if color == -1:
                    continue

                # Wrong color check (only when not in SUPER KING mode)
                if self.combo > 0 and self.super_king_timer == 0 and color != self._chain_color:
                    self.combo = 0
                    self._chain_color = -1
                    self.heat = min(HEAT_MAX, self.heat + HEAT_WRONG_CAPTURE)
                    self._set_message("WRONG COLOR! +HEAT")
                    cx = OX + piece.col * CELL + CELL // 2
                    cy = OY + piece.row * CELL + CELL // 2
                    self._add_floating_text(cx, cy - 20, "+15 HEAT", ORANGE, 40)
                    # Still earn base score for capturing (no combo multiplier)
                    base_score = BASE_CAPTURE_SCORE
                    if self.super_king_timer > 0:
                        base_score *= SUPER_KING_SCORE_MULT
                    score_earned += base_score
                    continue

                # Combo growth
                if self.combo == 0:
                    self._chain_color = color
                self.combo += 1
                if self.combo > self.max_combo:
                    self.max_combo = self.combo

                # Score with combo multiplier
                multiplier = COMBO_MULT_BASE + COMBO_MULT_STEP * (self.combo - 1)
                if self.super_king_timer > 0:
                    multiplier *= SUPER_KING_SCORE_MULT
                capture_score = int(BASE_CAPTURE_SCORE * multiplier)
                score_earned += capture_score

                # Floating text
                cx = OX + piece.col * CELL + CELL // 2
                cy = OY + piece.row * CELL + CELL // 2
                combo_label = f"+{capture_score}"
                if self.combo >= 2:
                    combo_label += f" x{self.combo}"
                self._add_floating_text(cx, cy - 15, combo_label, YELLOW, 30)

                # SUPER KING activation
                if self.combo >= SUPER_KING_THRESHOLD and self.super_king_timer == 0:
                    self.super_king_timer = SUPER_KING_DURATION
                    self._set_message("SUPER KING!")
                    cx = OX + piece.col * CELL + CELL // 2
                    cy = OY + piece.row * CELL + CELL // 2
                    self._spawn_particles(cx, cy, 30, PINK, (-4.0, 4.0))
                    self._add_floating_text(cx, cy - 25, "SUPER KING!", PINK, 50)

        self.score += score_earned
        return score_earned

    # ---- Echo stones ----

    def _spread_echo_stones(self) -> None:
        new_stones: set[tuple[int, int]] = set()
        for col, row in self.echo_stones:
            # Up to 2 random diagonal empty neighbors
            neighbors: list[tuple[int, int]] = []
            for dx in (-1, 1):
                for dy in (-1, 1):
                    nc, nr = col + dx, row + dy
                    if not self._is_valid_square(nc, nr):
                        continue
                    if (nc, nr) in self.echo_stones:
                        continue
                    if self._get_piece_at(nc, nr) is not None:
                        continue
                    neighbors.append((nc, nr))

            if neighbors:
                count = min(2, len(neighbors))
                chosen = self._rng.sample(neighbors, count)
                new_stones.update(chosen)

        self.echo_stones.update(new_stones)

    # ---- AI ----

    def _ai_turn(self) -> None:
        if self._ai_think_timer > 0:
            self._ai_think_timer -= 1
            return

        # Find best AI move
        best_capture_chain: list[tuple[int, int]] = []
        best_capture_len = 0
        best_piece: Piece | None = None
        best_dest: tuple[int, int] = (0, 0)

        for piece in self.ai_pieces:
            chains = self._get_capture_chains(
                piece.col, piece.row, piece.ptype, False
            )
            for dest_col, dest_row, caps in chains:
                if len(caps) > best_capture_len:
                    best_capture_len = len(caps)
                    best_capture_chain = caps
                    best_piece = piece
                    best_dest = (dest_col, dest_row)

        if best_piece is not None and best_capture_chain:
            self._execute_move(
                best_piece, best_dest[0], best_dest[1], best_capture_chain, True
            )

            # Check for further captures
            if self._get_single_captures(
                best_piece.col, best_piece.row, best_piece.ptype, False, frozenset()
            ):
                self._ai_think_timer = AI_THINK_DELAY // 2
                return
        else:
            # No captures, pick a random valid move
            all_moves: list[tuple[Piece, int, int]] = []
            for piece in self.ai_pieces:
                moves = self._get_simple_moves(
                    piece.col, piece.row, piece.ptype, False
                )
                for dest_col, dest_row in moves:
                    all_moves.append((piece, dest_col, dest_row))

            if all_moves:
                piece, dest_col, dest_row = self._rng.choice(all_moves)
                self._execute_move(piece, dest_col, dest_row, [], False)

        # Check game over after AI move
        if self._check_game_over():
            self.phase = Phase.GAME_OVER
            return

        self.player_turn = True

    # ---- Game over conditions ----

    def _check_game_over(self) -> bool:
        # HEAT >= 100
        if self.heat >= HEAT_MAX:
            self.game_over_message = "OVERHEAT!"
            self._won = False
            return True

        # All AI pieces captured → WIN
        if not self.ai_pieces:
            self.game_over_message = "YOU WIN!"
            self._won = True
            return True

        # All player pieces captured → LOSE
        if not self.player_pieces:
            self.game_over_message = "DEFEATED"
            self._won = False
            return True

        # No valid moves for current side
        if self.player_turn:
            has_move = self._has_any_captures_for_side(True) or any(
                self._get_simple_moves(p.col, p.row, p.ptype, True)
                for p in self.player_pieces
            )
            if not has_move:
                self.game_over_message = "NO MOVES — DEFEATED"
                self._won = False
                return True
        else:
            has_move = self._has_any_captures_for_side(False) or any(
                self._get_simple_moves(p.col, p.row, p.ptype, False)
                for p in self.ai_pieces
            )
            if not has_move:
                self.game_over_message = "AI HAS NO MOVES — YOU WIN!"
                self._won = True
                return True

        return False

    # ---- Particle effects ----

    def _spawn_particles(
        self,
        x: float,
        y: float,
        count: int,
        color: int,
        vrange: tuple[float, float],
    ) -> None:
        for _ in range(count):
            vx = self._rng.uniform(*vrange)
            vy = self._rng.uniform(*vrange)
            life = self._rng.randint(15, 25)
            self.particles.append(Particle(x, y, vx, vy, life, color))

    def _update_particles(self) -> None:
        for p in self.particles:
            p.life -= 1
            p.x += p.vx
            p.y += p.vy
        self.particles = [p for p in self.particles if p.life > 0]

    # ---- Floating text ----

    def _add_floating_text(
        self, x: float, y: float, text: str, color: int, life: int = 40
    ) -> None:
        self.floating_texts.append(FloatingText(x, y, text, life, color))

    def _update_floating_texts(self) -> None:
        for ft in self.floating_texts:
            ft.life -= 1
        self.floating_texts = [ft for ft in self.floating_texts if ft.life > 0]

    # ---- Helpers ----

    def _set_message(self, msg: str) -> None:
        self.message = msg
        self.message_timer = MESSAGE_DURATION


# ============================================================
# Entry Point
# ============================================================
if __name__ == "__main__":
    Game()
