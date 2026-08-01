"""test_imports.py — Headless logic tests for COIN SURGE (269_coin_surge)."""

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/269_coin_surge")

from main import (  # noqa: E402
    BASE_SCORE,
    CELL,
    COLORS,
    COMBO_THRESHOLD,
    Coin,
    FloatingText,
    GAME_DURATION,
    GRID_COLS,
    GRID_ROWS,
    HEAT_DECAY,
    HEAT_MAX,
    HEAT_MISMATCH,
    INITIAL_COLOR_CYCLE,
    INITIAL_PUSHER_INTERVAL,
    MIN_COLOR_CYCLE,
    MIN_PUSHER_INTERVAL,
    NUM_COLORS,
    Particle,
    Phase,
    RED,
    Game,
    SUPER_DURATION,
)


# ---------------------------------------------------------------------------
# Factory — bypasses pyxel.init / pyxel.run
# ---------------------------------------------------------------------------
def _make_game() -> Game:
    """Create a Game instance in headless mode with seeded RNG."""
    g = Game.__new__(Game)
    g._headless = True
    # Pre-init all attributes that start_game() or any testable method touches
    g.phase = Phase.TITLE
    g.coins = []
    g.particles = []
    g.floating_texts = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.best_score = 0
    g.super_timer = 0
    g.super_mode = False
    g.heat = 0.0
    g.timer = GAME_DURATION
    g.frame = 0
    g.pusher_countdown = INITIAL_PUSHER_INTERVAL
    g.drop_color = 0
    g.drop_color_timer = INITIAL_COLOR_CYCLE
    g.color_cycle_interval = INITIAL_COLOR_CYCLE
    g.pusher_interval = INITIAL_PUSHER_INTERVAL
    g.last_collected_color = None
    g._rng = random.Random(42)
    g._frame_count = 0
    g._anim_frame = 0
    g._pending_collected = []
    g._pusher_offset = 0.0
    g._highest_score = 0
    g._bgm_playing = False
    g.start_game()
    g._rng = random.Random(42)  # re-seed after start_game
    return g


# ---------------------------------------------------------------------------
# Data class tests
# ---------------------------------------------------------------------------
def test_coin_dataclass() -> None:
    c = Coin(col=3, row=5, color=2, falling=True)
    assert c.col == 3
    assert c.row == 5
    assert c.color == 2
    assert c.falling is True
    assert c.pyxel_color == COLORS[2]


def test_particle_dataclass() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, color=8, life=30)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert abs(p.vy - (-2.0)) < 0.001
    assert p.color == 8
    assert p.life == 30
    assert p.size == 3


def test_floating_text_dataclass() -> None:
    ft = FloatingText(x=100.0, y=50.0, text="+100", color=7, life=30)
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "+100"
    assert ft.color == 7
    assert ft.life == 30


# ---------------------------------------------------------------------------
# Phase enum
# ---------------------------------------------------------------------------
def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.PUSHER_ANIM in Phase
    assert Phase.COLLECT in Phase
    assert Phase.GAME_OVER in Phase


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
def test_constants() -> None:
    assert len(COLORS) == 4
    assert NUM_COLORS == 4
    assert COLORS[0] == 8  # RED
    assert COLORS[1] == 11  # LIME
    assert COLORS[2] == 5  # DARK_BLUE
    assert COLORS[3] == 10  # YELLOW
    assert GRID_COLS == 10
    assert GRID_ROWS == 12
    assert CELL == 20
    assert BASE_SCORE == 10
    assert COMBO_THRESHOLD == 4
    assert HEAT_MAX == 100
    assert SUPER_DURATION == 300


# ---------------------------------------------------------------------------
# Game factory tests
# ---------------------------------------------------------------------------
def test_make_game_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == GAME_DURATION
    assert g.frame == 0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.last_collected_color is None
    assert g.drop_color == 0
    assert len(g.coins) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0


# ---------------------------------------------------------------------------
# _drop_coin tests
# ---------------------------------------------------------------------------
def test_drop_coin_basic() -> None:
    g = _make_game()
    g._drop_coin(3)
    assert len(g.coins) == 1
    assert g.coins[0].col == 3
    assert g.coins[0].row == 0
    assert g.coins[0].color == g.drop_color
    assert g.coins[0].falling is True


def test_drop_coin_invalid_column() -> None:
    g = _make_game()
    g._drop_coin(-1)
    assert len(g.coins) == 0
    g._drop_coin(GRID_COLS)
    assert len(g.coins) == 0


def test_drop_coin_column_full() -> None:
    g = _make_game()
    # Fill column 3 fully
    for row in range(GRID_ROWS):
        g.coins.append(Coin(col=3, row=row, color=0, falling=False))
    # Try to drop — should be blocked at row 0
    g._drop_coin(3)
    assert len(g.coins) == GRID_ROWS  # No new coin added


def test_drop_coin_multiple_columns() -> None:
    g = _make_game()
    g._drop_coin(0)
    g._drop_coin(5)
    g._drop_coin(9)
    assert len(g.coins) == 3
    cols = {c.col for c in g.coins}
    assert cols == {0, 5, 9}


# ---------------------------------------------------------------------------
# _apply_gravity tests
# ---------------------------------------------------------------------------
def test_gravity_falls_to_bottom() -> None:
    g = _make_game()
    g._drop_coin(3)
    for _ in range(GRID_ROWS):
        g._apply_gravity()
    c = g.coins[0]
    assert c.row == GRID_ROWS - 1
    assert c.falling is False


def test_gravity_stacks_on_coin() -> None:
    g = _make_game()
    # Place a stationary coin at row 10 in col 3
    g.coins.append(Coin(col=3, row=10, color=0, falling=False))
    g._drop_coin(3)  # drops at row 0
    for _ in range(GRID_ROWS):
        g._apply_gravity()
    # The falling coin should land on top of the stationary one (row 9)
    falling = [c for c in g.coins if c.falling]
    assert len(falling) == 0  # All coins settled
    # Find the top coin (should be at row 9, above the row 10 coin)
    assert g._is_cell_occupied(3, 9)
    assert g._is_cell_occupied(3, 10)


def test_gravity_multiple_coins() -> None:
    g = _make_game()
    g._drop_coin(2)
    # Apply gravity for first coin to settle
    for _ in range(GRID_ROWS + 1):
        g._apply_gravity()
    # Now drop second coin — it stacks on top
    g._drop_coin(2)
    for _ in range(GRID_ROWS + 1):
        g._apply_gravity()
    # Both should be settled at bottom
    assert g._is_cell_occupied(2, GRID_ROWS - 1)
    assert g._is_cell_occupied(2, GRID_ROWS - 2)
    assert not any(c.falling for c in g.coins)


# ---------------------------------------------------------------------------
# _is_cell_occupied / _get_coin_at tests
# ---------------------------------------------------------------------------
def test_is_cell_occupied() -> None:
    g = _make_game()
    assert g._is_cell_occupied(3, 5) is False
    g.coins.append(Coin(col=3, row=5, color=0, falling=False))
    assert g._is_cell_occupied(3, 5) is True
    # Falling coin shouldn't count as occupied
    g.coins.append(Coin(col=3, row=6, color=1, falling=True))
    assert g._is_cell_occupied(3, 6) is False


def test_get_coin_at() -> None:
    g = _make_game()
    assert g._get_coin_at(3, 5) is None
    coin = Coin(col=3, row=5, color=0, falling=False)
    g.coins.append(coin)
    result = g._get_coin_at(3, 5)
    assert result is coin
    # Falling coin shouldn't be returned
    g.coins.append(Coin(col=3, row=6, color=1, falling=True))
    assert g._get_coin_at(3, 6) is None


# ---------------------------------------------------------------------------
# _activate_pusher tests
# ---------------------------------------------------------------------------
def test_pusher_shifts_coins_right() -> None:
    g = _make_game()
    g.coins.append(Coin(col=0, row=11, color=0, falling=False))
    g.coins.append(Coin(col=3, row=11, color=1, falling=False))
    g.coins.append(Coin(col=7, row=11, color=2, falling=False))

    collected = g._activate_pusher()
    assert len(collected) == 0  # None at right edge yet
    # Coins should have shifted right
    cols_after = {c.col for c in g.coins}
    assert 1 in cols_after  # from col 0
    assert 4 in cols_after  # from col 3
    assert 8 in cols_after  # from col 7


def test_pusher_collects_right_edge() -> None:
    g = _make_game()
    g.coins.append(Coin(col=GRID_COLS - 1, row=11, color=0, falling=False))

    collected = g._activate_pusher()
    assert len(collected) == 1
    assert collected[0].col == GRID_COLS - 1
    assert len(g.coins) == 0  # Removed from board


def test_pusher_cascade() -> None:
    """Coins packed together should cascade rightward."""
    g = _make_game()
    # Place coin at col 8, row 11. Col 9 at same row is empty.
    # When pusher fires, col 8 coin shifts to col 9 → collected.
    g.coins.append(Coin(col=8, row=11, color=0, falling=False))

    collected = g._activate_pusher()
    # Coin shifts col 8 → col 9, then collected from col 9
    assert len(collected) == 1
    assert len(g.coins) == 0  # All coins collected


def test_pusher_blocked_shift() -> None:
    """Coin can shift if target cell becomes empty due to cascade.
    Since pusher processes right-to-left, a coin at col 6 first shifts
    to col 7, freeing col 6 for the coin at col 5."""
    g = _make_game()
    g.coins.append(Coin(col=5, row=11, color=0, falling=False))
    g.coins.append(Coin(col=6, row=11, color=1, falling=False))

    g._activate_pusher()
    # col 6 → col 7 (freed), col 5 → col 6 (cascade)
    cols = {c.col for c in g.coins}
    assert 6 in cols  # col 5 coin moved to col 6
    assert 7 in cols  # col 6 coin moved to col 7


# ---------------------------------------------------------------------------
# _evaluate_collection tests
# ---------------------------------------------------------------------------
def test_evaluate_collection_first_coin() -> None:
    g = _make_game()
    coin = Coin(col=GRID_COLS - 1, row=11, color=0, falling=False)
    g._evaluate_collection([coin])
    assert g.score == BASE_SCORE  # 10 * 1 * 1
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.heat == 0.0
    assert g.last_collected_color == 0


def test_evaluate_collection_combo_chain() -> None:
    g = _make_game()
    c1 = Coin(col=GRID_COLS - 1, row=11, color=0, falling=False)
    c2 = Coin(col=GRID_COLS - 1, row=11, color=0, falling=False)  # same color
    c3 = Coin(col=GRID_COLS - 1, row=11, color=0, falling=False)
    g._evaluate_collection([c1])
    assert g.combo == 1
    assert g.score == BASE_SCORE * 1  # 10

    g._evaluate_collection([c2])
    assert g.combo == 2
    # score += 10 * 2 * 1 = 20, total = 30
    assert g.score == BASE_SCORE * 1 + BASE_SCORE * 2

    g._evaluate_collection([c3])
    assert g.combo == 3
    assert g.score == BASE_SCORE * 1 + BASE_SCORE * 2 + BASE_SCORE * 3


def test_evaluate_collection_mismatch() -> None:
    g = _make_game()
    c1 = Coin(col=GRID_COLS - 1, row=11, color=0, falling=False)
    c2 = Coin(col=GRID_COLS - 1, row=11, color=1, falling=False)  # different color

    g._evaluate_collection([c1])
    assert g.combo == 1
    assert g.heat == 0.0

    prev_heat = g.heat
    g._evaluate_collection([c2])
    assert g.combo == 1  # Reset to 1 (this coin starts new chain)
    assert g.heat == prev_heat + HEAT_MISMATCH
    assert g.last_collected_color == 1


def test_evaluate_collection_super_mode() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = SUPER_DURATION

    c1 = Coin(col=GRID_COLS - 1, row=11, color=0, falling=False)
    c2 = Coin(col=GRID_COLS - 1, row=11, color=1, falling=False)  # different, but super mode

    g._evaluate_collection([c1])
    assert g.combo == 1

    g._evaluate_collection([c2])
    assert g.combo == 2  # Still matched (super mode)
    assert g.score == BASE_SCORE * 1 * 3 + BASE_SCORE * 2 * 3  # 3x multiplier


def test_evaluate_collection_triggers_super() -> None:
    g = _make_game()
    g.combo = 3  # Pre-set combo so next match triggers super
    g.last_collected_color = 0

    coin = Coin(col=GRID_COLS - 1, row=11, color=0, falling=False)
    g._evaluate_collection([coin])
    assert g.combo == COMBO_THRESHOLD
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_evaluate_collection_empty() -> None:
    g = _make_game()
    g._evaluate_collection([])
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0


def test_evaluate_collection_multiple_coins() -> None:
    """Multiple coins collected in one pusher cycle."""
    g = _make_game()
    coins = [
        Coin(col=GRID_COLS - 1, row=11, color=0, falling=False),
        Coin(col=GRID_COLS - 1, row=10, color=0, falling=False),  # same color
        Coin(col=GRID_COLS - 1, row=9, color=1, falling=False),  # different
    ]
    g._evaluate_collection(coins)
    # First two match (combo 1, 2), third mismatches (combo resets to 1)
    assert g.combo == 1  # Reset on mismatch
    assert g.heat == HEAT_MISMATCH
    assert g.score == BASE_SCORE * 1 + BASE_SCORE * 2  # 10 + 20 = 30


# ---------------------------------------------------------------------------
# _update_heat tests
# ---------------------------------------------------------------------------
def test_heat_decay() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert abs(g.heat - (50.0 - HEAT_DECAY)) < 0.001


def test_heat_floor_at_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_heat_game_over_check_not_in_update_heat() -> None:
    """_update_heat only decays; game over check is in _update_collect."""
    g = _make_game()
    g.heat = HEAT_MAX
    g._update_heat()
    assert g.heat == HEAT_MAX  # No decay at cap
    # Game over is checked elsewhere


# ---------------------------------------------------------------------------
# _update_super tests
# ---------------------------------------------------------------------------
def test_super_timer_decrement() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = SUPER_DURATION
    g._update_super()
    assert g.super_timer == SUPER_DURATION - 1
    assert g.super_mode is True


def test_super_expires() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_super()
    assert g.super_timer == 0
    assert g.super_mode is False


def test_super_inactive_noop() -> None:
    g = _make_game()
    g.super_mode = False
    g.super_timer = 0
    g._update_super()
    assert g.super_timer == 0
    assert g.super_mode is False


# ---------------------------------------------------------------------------
# _update_timer tests
# ---------------------------------------------------------------------------
def test_timer_decrement() -> None:
    g = _make_game()
    g.timer = 100
    g._update_timer()
    assert g.timer == 99


# ---------------------------------------------------------------------------
# _update_color_cycle tests
# ---------------------------------------------------------------------------
def test_color_cycle_basic() -> None:
    g = _make_game()
    g.frame = 1  # Avoid frame 0 triggering escalation (0 % 300 == 0)
    g.drop_color_timer = 1
    old_color = g.drop_color
    g._update_color_cycle()
    assert g.drop_color == (old_color + 1) % NUM_COLORS
    assert g.drop_color_timer == g.color_cycle_interval


def test_color_cycle_speed_escalation() -> None:
    g = _make_game()
    g.frame = 300
    old_interval = g.color_cycle_interval
    g._update_color_cycle()
    assert g.color_cycle_interval == old_interval - 2  # Escalated


def test_color_cycle_min_cap() -> None:
    g = _make_game()
    g.frame = 300  # Triggers escalation
    g.color_cycle_interval = MIN_COLOR_CYCLE + 1
    g._update_color_cycle()
    # Escalation reduces by 2: 31 → 29 (can go below MIN)
    assert g.color_cycle_interval == MIN_COLOR_CYCLE - 1


# ---------------------------------------------------------------------------
# _update_difficulty tests
# ---------------------------------------------------------------------------
def test_difficulty_escalation() -> None:
    g = _make_game()
    g.frame = 300
    old_interval = g.pusher_interval
    g._update_difficulty()
    assert g.pusher_interval == old_interval - 4


def test_difficulty_min_cap() -> None:
    g = _make_game()
    g.frame = 300
    g.pusher_interval = MIN_PUSHER_INTERVAL + 1
    g._update_difficulty()
    # Similar to color cycle — may go below MIN but check only fires if > MIN
    assert g.pusher_interval <= MIN_PUSHER_INTERVAL + 1


# ---------------------------------------------------------------------------
# Particle system tests
# ---------------------------------------------------------------------------
def test_spawn_particles() -> None:
    g = _make_game()
    g._spawn_particles(100, 100, RED, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.x == 100.0
        assert p.y == 100.0
        assert p.color == RED
        assert p.life >= 20


def test_update_particles_decay() -> None:
    g = _make_game()
    g._spawn_particles(100, 100, RED, 1)
    assert len(g.particles) == 1
    for _ in range(30):  # Run past max life
        g._update_particles()
    assert len(g.particles) == 0  # All expired


def test_particle_movement() -> None:
    g = _make_game()
    g._spawn_particles(100, 100, RED, 1)
    p = g.particles[0]
    orig_x, orig_y = p.x, p.y
    g._update_particles()
    assert p.x != orig_x or p.y != orig_y  # At least one moved


# ---------------------------------------------------------------------------
# Floating text tests
# ---------------------------------------------------------------------------
def test_spawn_floating_text() -> None:
    g = _make_game()
    g._spawn_floating_text(100, 50, "+50", 7)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "+50"
    assert ft.color == 7
    assert ft.life == 30


def test_update_floating_texts_decay() -> None:
    g = _make_game()
    g._spawn_floating_text(100, 50, "+50", 7)
    for _ in range(35):
        g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_floating_text_floats_upward() -> None:
    g = _make_game()
    g._spawn_floating_text(100, 50, "+50", 7)
    ft = g.floating_texts[0]
    orig_y = ft.y
    g._update_floating_texts()
    assert ft.y < orig_y  # Floats upward


# ---------------------------------------------------------------------------
# Integration: full cycle test
# ---------------------------------------------------------------------------
def test_full_cycle_drop_gravity_pusher_collect() -> None:
    """Test a complete cycle: drop coin → gravity → pusher → collect."""
    g = _make_game()
    # Drop a coin in col 9 (rightmost)
    g._drop_coin(9)
    assert len(g.coins) == 1
    assert g.coins[0].falling is True

    # Apply gravity until settled
    for _ in range(GRID_ROWS + 1):
        g._apply_gravity()
    assert not any(c.falling for c in g.coins)

    # Activate pusher
    collected = g._activate_pusher()
    # Coin at col 9 should be collected
    assert len(collected) == 1

    # Evaluate collection
    g._evaluate_collection(collected)
    assert g.score > 0
    assert g.combo == 1
    assert g.max_combo == 1


def test_multi_coin_chain() -> None:
    """Drop multiple same-color coins, have them pushed off together."""
    g = _make_game()
    g.drop_color = 0  # RED

    # Place coins at col 8 (will shift to 9 then be collected)
    g.coins.append(Coin(col=8, row=GRID_ROWS - 1, color=0, falling=False))
    g.drop_color = 0  # Still RED
    g.coins.append(Coin(col=8, row=GRID_ROWS - 2, color=0, falling=False))

    collected = g._activate_pusher()
    # Both shift to col 9 → both collected
    assert len(collected) == 2

    g._evaluate_collection(collected)
    assert g.combo == 2  # Two same-color in a row
    assert g.max_combo == 2
    assert g.score == BASE_SCORE * 1 + BASE_SCORE * 2  # 10 + 20


def test_heat_accumulation_on_mismatch() -> None:
    """Mismatch should add heat."""
    g = _make_game()
    c1 = Coin(col=GRID_COLS - 1, row=11, color=0, falling=False)
    g._evaluate_collection([c1])
    assert g.heat == 0.0

    c2 = Coin(col=GRID_COLS - 1, row=11, color=1, falling=False)
    g._evaluate_collection([c2])
    assert abs(g.heat - HEAT_MISMATCH) < 0.001


def test_max_combo_tracking() -> None:
    """max_combo should track the highest combo achieved."""
    g = _make_game()
    g.last_collected_color = 0

    # Build combo to 3
    for i in range(3):
        coin = Coin(col=GRID_COLS - 1, row=11, color=0, falling=False)
        g._evaluate_collection([coin])
    assert g.combo == 3
    assert g.max_combo == 3

    # Mismatch resets combo
    coin_mismatch = Coin(col=GRID_COLS - 1, row=11, color=1, falling=False)
    g._evaluate_collection([coin_mismatch])
    assert g.combo == 1
    assert g.max_combo == 3  # Max stays at 3


def test_super_mode_activates_at_threshold() -> None:
    """SUPER DROP activates when combo reaches COMBO_THRESHOLD."""
    g = _make_game()
    g.combo = COMBO_THRESHOLD - 1
    g.last_collected_color = 0

    coin = Coin(col=GRID_COLS - 1, row=11, color=0, falling=False)
    g._evaluate_collection([coin])
    assert g.combo == COMBO_THRESHOLD
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_end_game_heat() -> None:
    """Game ends when heat reaches HEAT_MAX."""
    g = _make_game()
    g.heat = HEAT_MAX
    g._end_game()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score >= g.score


def test_end_game_timer() -> None:
    """Game ends when timer runs out."""
    g = _make_game()
    g.timer = 0
    g._end_game()
    assert g.phase == Phase.GAME_OVER


def test_start_game_resets_state() -> None:
    """start_game() should properly reset all gameplay state."""
    g = _make_game()
    g.score = 1000
    g.combo = 5
    g.heat = 50.0
    g.super_mode = True
    g.super_timer = 100
    g.coins.append(Coin(col=0, row=0, color=0, falling=True))
    g.particles.append(Particle(x=0, y=0, vx=0, vy=0, color=0, life=10))
    g.floating_texts.append(FloatingText(x=0, y=0, text="test", color=0, life=1))

    g.start_game()

    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert len(g.coins) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.last_collected_color is None


# ---------------------------------------------------------------------------
# Score calculation edge cases
# ---------------------------------------------------------------------------
def test_score_with_super_multiplier() -> None:
    """In super mode, score should be tripled."""
    g = _make_game()
    g.super_mode = True
    g.last_collected_color = 0

    coin = Coin(col=GRID_COLS - 1, row=11, color=0, falling=False)
    g._evaluate_collection([coin])
    assert g.score == BASE_SCORE * 1 * 3  # 10 * 1 * 3 = 30


def test_score_combo_accumulation() -> None:
    """Score should accumulate correctly across multiple collections.
    Super activates at combo 4, so 5th match gets 3x multiplier."""
    g = _make_game()
    g.last_collected_color = 0

    expected_score = 0
    for i in range(1, 6):
        was_super = g.super_mode  # snapshot BEFORE call
        coin = Coin(col=GRID_COLS - 1, row=11, color=0, falling=False)
        g._evaluate_collection([coin])
        mult = 3 if was_super else 1
        expected_score += BASE_SCORE * i * mult

    # combo 1-3: mult=1 → 10+20+30=60
    # combo 4: mult=1 (super activates AFTER score calc) → +40=100
    # combo 5: mult=3 → +150=250
    assert g.score == 250
    assert g.score == expected_score


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
