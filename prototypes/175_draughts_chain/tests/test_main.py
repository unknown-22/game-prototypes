"""Tests for Draughts Chain."""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import (  # type: ignore[import-untyped]
    AI_THINK_DELAY,
    BASE_CAPTURE_SCORE,
    CELL,
    COMBO_MULT_BASE,
    COMBO_MULT_STEP,
    ECHO_STONE_BONUS,
    GREEN,
    HEAT_MAX,
    HEAT_WRONG_CAPTURE,
    OX,
    OY,
    PIECE_RADIUS,
    PLAYER_COLORS,
    RED,
    SUPER_KING_DURATION,
    SUPER_KING_SCORE_MULT,
    SUPER_KING_THRESHOLD,
    WHITE,
    YELLOW,
    FloatingText,
    Game,
    Particle,
    Phase,
    Piece,
    PieceType,
)


def _make_game() -> Game:
    """Factory for headless Game instances."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.reset()
    return g


# ---- Initialization ----

def test_init_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_king_timer == 0
    assert g.echo_stones == set()
    assert g.selected_piece is None
    assert g.valid_moves == []
    assert g.player_turn
    assert g.particles == []
    assert g.floating_texts == []
    assert g._won is False
    assert g._game_timer == 0


def test_pieces_initialized() -> None:
    g = _make_game()
    # After reset we're in TITLE, but pieces have been initialized
    assert len(g.player_pieces) == 12
    assert len(g.ai_pieces) == 12

    # Player pieces should be on dark squares, rows 0-2
    for p in g.player_pieces:
        assert 0 <= p.row <= 2
        assert 0 <= p.col <= 7
        assert (p.row + p.col) % 2 == 1  # dark square
        assert p.ptype == PieceType.MAN

    # AI pieces should be on dark squares, rows 5-7
    for p in g.ai_pieces:
        assert 5 <= p.row <= 7
        assert 0 <= p.col <= 7
        assert (p.row + p.col) % 2 == 1
        assert p.ptype == PieceType.MAN

    # Player pieces have colors from PLAYER_COLORS (3 each)
    color_counts: dict[int, int] = {}
    for p in g.player_pieces:
        color_counts[p.color] = color_counts.get(p.color, 0) + 1
    for c in PLAYER_COLORS:
        assert color_counts.get(c, 0) == 3, f"Expected 3 pieces of color {c}, got {color_counts.get(c, 0)}"

    # AI pieces have colors from PLAYER_COLORS (for combo mechanic)
    ai_color_counts: dict[int, int] = {}
    for p in g.ai_pieces:
        ai_color_counts[p.color] = ai_color_counts.get(p.color, 0) + 1
    for c in PLAYER_COLORS:
        assert ai_color_counts.get(c, 0) == 3, f"Expected 3 AI pieces of color {c}, got {ai_color_counts.get(c, 0)}"


def test_piece_repr() -> None:
    p = Piece(color=8, ptype=PieceType.MAN, row=0, col=1)
    assert p.color == 8
    assert p.ptype == PieceType.MAN
    assert p.row == 0
    assert p.col == 1


# ---- Geometry helpers ----

def test_is_valid_square() -> None:
    g = _make_game()
    assert g._is_valid_square(0, 0) is True
    assert g._is_valid_square(7, 7) is True
    assert g._is_valid_square(3, 4) is True
    assert g._is_valid_square(-1, 0) is False
    assert g._is_valid_square(0, 8) is False
    assert g._is_valid_square(8, 0) is False


def test_get_piece_at() -> None:
    g = _make_game()
    # Find a position where a player piece exists
    p = g.player_pieces[0]
    found = g._get_piece_at(p.col, p.row)
    assert found is p

    # Empty square (light square)
    assert g._get_piece_at(0, 0) is None


def test_is_player_piece() -> None:
    g = _make_game()
    assert g._is_player_piece(g.player_pieces[0]) is True
    assert g._is_player_piece(g.ai_pieces[0]) is False


# ---- Move computation ----

def test_get_simple_moves_player_man() -> None:
    g = _make_game()
    # Find a player piece that can move
    for p in g.player_pieces:
        moves = g._get_simple_moves(p.col, p.row, p.ptype, True)
        # Most pieces should be blocked initially (pieces in front)
        # but some on the front row might have moves
        if moves:
            for dc, dr in moves:
                assert g._is_valid_square(dc, dr)
                assert g._get_piece_at(dc, dr) is None
                assert dr == p.row + 1  # forward
            return
    # If no piece can move (all blocked), test passes anyway


def test_get_simple_moves_king() -> None:
    g = _make_game()
    # Create a king manually
    king = Piece(color=RED, ptype=PieceType.KING, row=3, col=3)
    # Make sure position is empty
    assert g._get_piece_at(3, 3) is None
    moves = g._get_simple_moves(king.col, king.row, king.ptype, True)
    # King at center can move to 4 diagonal squares (if empty)
    assert all(g._is_valid_square(c, r) for c, r in moves)
    assert all(g._get_piece_at(c, r) is None for c, r in moves)


def test_get_single_captures() -> None:
    g = _make_game()
    # Clear the board and set up a simple capture scenario
    g.player_pieces.clear()
    g.ai_pieces.clear()

    # Player piece at (2,2), AI at (3,3) - player can capture
    player = Piece(color=RED, ptype=PieceType.MAN, row=2, col=2)
    enemy = Piece(color=GREEN, ptype=PieceType.MAN, row=3, col=3)
    g.player_pieces.append(player)
    g.ai_pieces.append(enemy)

    caps = g._get_single_captures(player.col, player.row, player.ptype, True, frozenset())
    assert len(caps) == 1
    assert caps[0] == (3, 3, 4, 4)

    # Verify can't capture own piece
    g.ai_pieces.clear()
    g.player_pieces.append(Piece(color=RED, ptype=PieceType.MAN, row=3, col=3))
    caps = g._get_single_captures(player.col, player.row, player.ptype, True, frozenset())
    assert len(caps) == 0


def test_get_capture_chains_single() -> None:
    g = _make_game()
    g.player_pieces.clear()
    g.ai_pieces.clear()

    player = Piece(color=RED, ptype=PieceType.MAN, row=1, col=1)
    enemy = Piece(color=GREEN, ptype=PieceType.MAN, row=2, col=2)
    g.player_pieces.append(player)
    g.ai_pieces.append(enemy)

    chains = g._get_capture_chains(player.col, player.row, player.ptype, True)
    assert len(chains) == 1
    dest_col, dest_row, caps = chains[0]
    assert (dest_col, dest_row) == (3, 3)
    assert caps == [(2, 2)]


def test_get_capture_chains_double() -> None:
    g = _make_game()
    g.player_pieces.clear()
    g.ai_pieces.clear()

    # Set up: player at (1,1), AI at (2,2) and (4,4)
    player = Piece(color=RED, ptype=PieceType.MAN, row=1, col=1)
    g.player_pieces.append(player)
    g.ai_pieces.append(Piece(color=GREEN, ptype=PieceType.MAN, row=2, col=2))
    g.ai_pieces.append(Piece(color=RED, ptype=PieceType.MAN, row=4, col=4))

    chains = g._get_capture_chains(player.col, player.row, player.ptype, True)
    # Should find one double capture chain
    assert len(chains) == 1
    dest_col, dest_row, caps = chains[0]
    assert (dest_col, dest_row) == (5, 5)
    assert caps == [(2, 2), (4, 4)]


def test_get_valid_moves_no_captures() -> None:
    g = _make_game()
    # Find a piece that has non-capture moves (front row)
    for p in g.player_pieces:
        chains = g._get_capture_chains(p.col, p.row, p.ptype, True)
        if not chains:
            moves = g._get_valid_moves(p)
            # All moves should be non-capture
            for _, _, caps, is_cap in moves:
                assert caps == []
                assert not is_cap
            return
    # If all pieces have captures (unlikely in initial board), skip


def test_has_any_captures() -> None:
    g = _make_game()
    # Initial board: no immediate captures (pieces are 2 rows apart)
    result = g._has_any_captures()
    assert result is False

    # Set up a capture scenario
    g.player_pieces.clear()
    g.ai_pieces.clear()
    g.player_pieces.append(Piece(color=RED, ptype=PieceType.MAN, row=4, col=0))
    g.ai_pieces.append(Piece(color=GREEN, ptype=PieceType.MAN, row=5, col=1))
    assert g._has_any_captures() is True


# ---- Move execution ----

def test_execute_move_simple() -> None:
    g = _make_game()
    g.player_pieces.clear()
    g.ai_pieces.clear()

    p = Piece(color=RED, ptype=PieceType.MAN, row=5, col=0)
    g.player_pieces.append(p)
    g.phase = Phase.PLAYING

    score = g._execute_move(p, 1, 6, [], False)
    assert score == 0
    assert p.col == 1
    assert p.row == 6
    assert p.ptype == PieceType.MAN  # not yet king


def test_execute_move_capture() -> None:
    g = _make_game()
    g.player_pieces.clear()
    g.ai_pieces.clear()

    player = Piece(color=RED, ptype=PieceType.MAN, row=4, col=0)
    enemy = Piece(color=GREEN, ptype=PieceType.MAN, row=5, col=1)
    g.player_pieces.append(player)
    g.ai_pieces.append(enemy)
    g.phase = Phase.PLAYING

    score = g._execute_move(player, 2, 6, [(1, 5)], True)
    assert score > 0
    assert player.col == 2
    assert player.row == 6
    assert enemy not in g.ai_pieces
    # Echo stone should be at captured position
    assert (1, 5) in g.echo_stones


def test_execute_move_king_promotion() -> None:
    g = _make_game()
    g.player_pieces.clear()
    g.ai_pieces.clear()

    # Player piece one step from promotion
    player = Piece(color=RED, ptype=PieceType.MAN, row=6, col=0)
    g.player_pieces.append(player)
    g.phase = Phase.PLAYING

    g._execute_move(player, 1, 7, [], False)
    assert player.row == 7
    assert player.ptype == PieceType.KING


def test_execute_move_echo_stone_collect() -> None:
    g = _make_game()
    g.player_pieces.clear()
    g.ai_pieces.clear()

    # Place echo stone and move onto it
    g.echo_stones.add((1, 5))
    player = Piece(color=RED, ptype=PieceType.MAN, row=4, col=0)
    g.player_pieces.append(player)
    g.phase = Phase.PLAYING

    score = g._execute_move(player, 1, 5, [], False)
    assert score == ECHO_STONE_BONUS
    assert (1, 5) not in g.echo_stones


# ---- Combo system ----

def test_combo_grows_on_same_color_capture() -> None:
    g = _make_game()
    g.player_pieces.clear()
    g.ai_pieces.clear()

    player = Piece(color=RED, ptype=PieceType.MAN, row=4, col=0)
    g.player_pieces.append(player)
    g.phase = Phase.PLAYING

    # First capture: RED AI piece
    g.ai_pieces.append(Piece(color=RED, ptype=PieceType.MAN, row=5, col=1))
    g._execute_move(player, 2, 6, [(1, 5)], True)
    assert g.combo == 1
    assert g._chain_color == RED
    assert g.score > 0

    # Second same-color capture
    player.col = 4
    player.row = 4
    g.echo_stones.clear()  # Remove echo stones from previous capture
    g.ai_pieces.append(Piece(color=RED, ptype=PieceType.MAN, row=5, col=1))
    score_before = g.score
    g._execute_move(player, 2, 6, [(1, 5)], True)
    assert g.combo == 2
    multiplier = COMBO_MULT_BASE + COMBO_MULT_STEP * (2 - 1)  # 1.5
    expected = int(BASE_CAPTURE_SCORE * multiplier)
    assert g.score - score_before == expected


def test_combo_resets_on_wrong_color_capture() -> None:
    g = _make_game()
    g.player_pieces.clear()
    g.ai_pieces.clear()

    player = Piece(color=RED, ptype=PieceType.MAN, row=4, col=0)
    g.player_pieces.append(player)
    g.phase = Phase.PLAYING

    # First capture: RED AI piece → sets chain to RED
    g.ai_pieces.append(Piece(color=RED, ptype=PieceType.MAN, row=5, col=1))
    g._execute_move(player, 2, 6, [(1, 5)], True)
    assert g.combo == 1
    assert g._chain_color == RED

    # Move player back
    player.col = 4
    player.row = 4
    player.ptype = PieceType.MAN
    g.heat = 0.0

    # Second capture: GREEN AI piece → wrong color, combo reset
    g.ai_pieces.append(Piece(color=GREEN, ptype=PieceType.MAN, row=5, col=1))
    g._execute_move(player, 2, 6, [(1, 5)], True)
    assert g.combo == 0
    assert g.heat == HEAT_WRONG_CAPTURE


def test_super_king_activates_at_combo_4() -> None:
    g = _make_game()
    g.player_pieces.clear()
    g.ai_pieces.clear()

    player = Piece(color=RED, ptype=PieceType.MAN, row=4, col=0)
    g.player_pieces.append(player)
    g.phase = Phase.PLAYING

    # 4 same-color captures in a row
    for i in range(SUPER_KING_THRESHOLD):
        g.ai_pieces.append(Piece(color=RED, ptype=PieceType.MAN, row=5, col=1))
        g._execute_move(player, 2, 6, [(1, 5)], True)
        # Reset player for next capture
        player.col = 4
        player.row = 4
        player.ptype = PieceType.MAN

    assert g.combo == SUPER_KING_THRESHOLD
    assert g.super_king_timer == SUPER_KING_DURATION


def test_super_king_ignores_color() -> None:
    g = _make_game()
    g.player_pieces.clear()
    g.ai_pieces.clear()

    player = Piece(color=RED, ptype=PieceType.MAN, row=4, col=0)
    g.player_pieces.append(player)
    g.phase = Phase.PLAYING

    # Activate SUPER KING
    for _ in range(SUPER_KING_THRESHOLD):
        g.ai_pieces.append(Piece(color=RED, ptype=PieceType.MAN, row=5, col=1))
        g._execute_move(player, 2, 6, [(1, 5)], True)
        player.col = 4
        player.row = 4
        player.ptype = PieceType.MAN

    combo_before = g.combo
    assert g.super_king_timer > 0

    # Capture a different color during SUPER KING - should NOT reset combo
    g.ai_pieces.append(Piece(color=GREEN, ptype=PieceType.MAN, row=5, col=1))
    g._execute_move(player, 2, 6, [(1, 5)], True)
    assert g.combo == combo_before + 1  # combo grew, not reset


def test_super_king_triple_score() -> None:
    g = _make_game()
    g.player_pieces.clear()
    g.ai_pieces.clear()

    player = Piece(color=RED, ptype=PieceType.MAN, row=4, col=0)
    g.player_pieces.append(player)
    g.phase = Phase.PLAYING

    # Activate SUPER KING
    for _ in range(SUPER_KING_THRESHOLD):
        g.ai_pieces.append(Piece(color=RED, ptype=PieceType.MAN, row=5, col=1))
        g._execute_move(player, 2, 6, [(1, 5)], True)
        player.col = 4
        player.row = 4
        player.ptype = PieceType.MAN

    assert g.super_king_timer > 0

    # Capture during SUPER KING: should have 3x multiplier
    g.echo_stones.clear()  # Remove echo stones from build-up captures
    g.ai_pieces.append(Piece(color=RED, ptype=PieceType.MAN, row=5, col=1))
    score_before = g.score
    g._execute_move(player, 2, 6, [(1, 5)], True)
    score_gained = g.score - score_before

    multiplier = COMBO_MULT_BASE + COMBO_MULT_STEP * (g.combo - 1)
    multiplier *= SUPER_KING_SCORE_MULT
    expected = int(BASE_CAPTURE_SCORE * multiplier)
    assert score_gained == expected


# ---- Echo stones ----

def test_echo_stone_created_on_capture() -> None:
    g = _make_game()
    g.player_pieces.clear()
    g.ai_pieces.clear()

    player = Piece(color=RED, ptype=PieceType.MAN, row=4, col=0)
    enemy = Piece(color=GREEN, ptype=PieceType.MAN, row=5, col=1)
    g.player_pieces.append(player)
    g.ai_pieces.append(enemy)
    g.phase = Phase.PLAYING

    assert (1, 5) not in g.echo_stones
    g._execute_move(player, 2, 6, [(1, 5)], True)
    assert (1, 5) in g.echo_stones


def test_echo_stone_spread() -> None:
    g = _make_game()
    g.player_pieces.clear()
    g.ai_pieces.clear()

    # Place isolated echo stone
    g.echo_stones.add((4, 4))
    initial_count = len(g.echo_stones)
    g._spread_echo_stones()
    # Should have spread to 1 or 2 neighbors (or more if chain)
    assert len(g.echo_stones) >= initial_count + 1


# ---- Heat system ----

def test_heat_increases_on_wrong_color() -> None:
    g = _make_game()
    g.player_pieces.clear()
    g.ai_pieces.clear()

    player = Piece(color=RED, ptype=PieceType.MAN, row=4, col=0)
    g.player_pieces.append(player)
    g.phase = Phase.PLAYING

    # Set up combo on RED
    g.ai_pieces.append(Piece(color=RED, ptype=PieceType.MAN, row=5, col=1))
    g._execute_move(player, 2, 6, [(1, 5)], True)

    player.col = 4
    player.row = 4
    player.ptype = PieceType.MAN

    # Capture wrong color
    g.heat = 0.0
    g.ai_pieces.append(Piece(color=GREEN, ptype=PieceType.MAN, row=5, col=1))
    g._execute_move(player, 2, 6, [(1, 5)], True)
    assert g.heat == HEAT_WRONG_CAPTURE


def test_heat_max_100() -> None:
    g = _make_game()
    g.player_pieces.clear()
    g.ai_pieces.clear()

    player = Piece(color=RED, ptype=PieceType.MAN, row=4, col=0)
    g.player_pieces.append(player)
    g.phase = Phase.PLAYING

    # Set combo on RED
    g.ai_pieces.append(Piece(color=RED, ptype=PieceType.MAN, row=5, col=1))
    g._execute_move(player, 2, 6, [(1, 5)], True)

    # Add lots of wrong-color captures
    for _ in range(10):
        player.col = 4
        player.row = 4
        player.ptype = PieceType.MAN
        g.ai_pieces.append(Piece(color=GREEN, ptype=PieceType.MAN, row=5, col=1))
        g._execute_move(player, 2, 6, [(1, 5)], True)

    assert g.heat <= HEAT_MAX


# ---- Game over conditions ----

def test_game_over_overheat() -> None:
    g = _make_game()
    g.heat = HEAT_MAX
    g.phase = Phase.PLAYING
    g.player_turn = True
    assert g._check_game_over() is True
    assert g.game_over_message == "OVERHEAT!"
    assert g._won is False


def test_game_over_win() -> None:
    g = _make_game()
    g.ai_pieces.clear()
    g.phase = Phase.PLAYING
    g.player_turn = True
    assert g._check_game_over() is True
    assert g.game_over_message == "YOU WIN!"
    assert g._won is True


def test_game_over_lose() -> None:
    g = _make_game()
    g.player_pieces.clear()
    g.phase = Phase.PLAYING
    g.player_turn = True
    assert g._check_game_over() is True
    assert g.game_over_message == "DEFEATED"
    assert g._won is False


def test_game_over_no_moves_player() -> None:
    g = _make_game()
    g.player_pieces.clear()
    g.ai_pieces.clear()

    # Place one player piece completely surrounded
    g.player_pieces.append(Piece(color=RED, ptype=PieceType.MAN, row=7, col=0))
    g.phase = Phase.PLAYING
    g.player_turn = True
    assert g._check_game_over() is True


# ---- Reset ----

def test_reset_clears_state() -> None:
    g = _make_game()
    g.score = 500
    g.combo = 5
    g.heat = 80.0
    g.echo_stones.add((3, 3))
    g.super_king_timer = 100
    g.particles.append(Particle(0, 0, 1, 1, 10, RED))
    g.floating_texts.append(FloatingText(0, 0, "test", 10, WHITE))

    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.echo_stones == set()
    assert g.super_king_timer == 0
    assert g.particles == []
    assert g.floating_texts == []
    assert g.phase == Phase.TITLE


# ---- AI ----

def test_ai_has_12_pieces() -> None:
    g = _make_game()
    assert len(g.ai_pieces) == 12


def test_ai_can_find_moves() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.player_pieces.clear()
    g.ai_pieces.clear()

    # Simple AI piece
    ai = Piece(color=GREEN, ptype=PieceType.MAN, row=5, col=0)
    g.ai_pieces.append(ai)

    moves = g._get_simple_moves(ai.col, ai.row, ai.ptype, False)
    assert len(moves) > 0


# ---- Particle system ----

def test_spawn_and_update_particles() -> None:
    g = _make_game()
    g._spawn_particles(100.0, 100.0, 5, RED, (-2.0, 2.0))
    assert len(g.particles) == 5
    g._update_particles()
    assert all(p.life >= 0 for p in g.particles)


def test_particles_expire() -> None:
    g = _make_game()
    g._spawn_particles(100.0, 100.0, 3, RED, (0.0, 0.0))
    for p in g.particles:
        p.life = 0  # force expire
    g._update_particles()
    assert len(g.particles) == 0


# ---- Floating text ----

def test_floating_text_lifecycle() -> None:
    g = _make_game()
    g._add_floating_text(100.0, 100.0, "+100", YELLOW, 40)
    assert len(g.floating_texts) == 1
    for ft in g.floating_texts:
        ft.life = 0
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ---- Score tracking ----

def test_max_combo_tracked() -> None:
    g = _make_game()
    g.player_pieces.clear()
    g.ai_pieces.clear()
    g.phase = Phase.PLAYING

    player = Piece(color=RED, ptype=PieceType.MAN, row=4, col=0)
    g.player_pieces.append(player)

    # Build combo to 3
    for _ in range(3):
        g.ai_pieces.append(Piece(color=RED, ptype=PieceType.MAN, row=5, col=1))
        g._execute_move(player, 2, 6, [(1, 5)], True)
        player.col = 4
        player.row = 4
        player.ptype = PieceType.MAN

    assert g.max_combo == 3
    assert g.combo == 3


# ---- Constants ----

def test_constants_reasonable() -> None:
    assert CELL == 28
    assert OX == 48
    assert OY == 8
    assert PIECE_RADIUS == 11
    assert BASE_CAPTURE_SCORE == 100
    assert SUPER_KING_DURATION == 300
    assert AI_THINK_DELAY == 15
    assert HEAT_MAX == 100.0
    assert HEAT_WRONG_CAPTURE == 15.0
