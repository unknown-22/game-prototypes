"""test_imports.py — Headless logic tests for Chop Chain (101_chop_chain)."""

import random
import sys

# Import from parent game module
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/101_chop_chain")
from main import (
    Board,
    FloatingText,
    Game,
    Particle,
    Phase,
    BOARD_COLORS,
    BOARD_SCORE,
    HEAT_EMPTY_CHOP,
    HEAT_WRONG_COLOR,
    MAX_HEAT,
    MAX_BOARDS_PER_COLUMN,
    NUM_COLUMNS,
    SUPER_DURATION,
    SUPER_SCORE_MULTIPLIER,
    HEAT_DECAY_INTERVAL,
    INITIAL_SPAWN_INTERVAL,
    MIN_SPAWN_INTERVAL,
    SPAWN_DECREASE_AMOUNT,
    SPAWN_DECREASE_INTERVAL,
    PARTICLE_GRAVITY,
)


def _make_game() -> Game:
    """Factory for headless Game instances with deterministic RNG."""
    g = Game.__new__(Game)
    g._init_state()
    g._rng = random.Random(42)  # seed AFTER _init_state (which resets _rng)
    g.reset()
    return g


# ── Data Class Tests ──────────────────────────────────────────────────


def test_board_creation() -> None:
    b = Board(color=8)
    assert b.color == 8
    assert b.hp == 1


def test_particle_defaults() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=20, color=3)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 20
    assert p.color == 3


def test_floating_text() -> None:
    ft = FloatingText(x=50.0, y=60.0, text="+10", life=30, color=8)
    assert ft.text == "+10"
    assert ft.life == 30


# ── Enum Tests ────────────────────────────────────────────────────────


def test_phase_values() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ── Reset / Init Tests ────────────────────────────────────────────────


def test_reset_clears_all_state() -> None:
    g = _make_game()
    # Dirty the state
    g.columns[0].append(Board(color=8))
    g.score = 100
    g.combo = 3
    g.heat = 5
    g.super_mode = True
    g.particles.append(Particle(0, 0, 0, 0, 10, 8))
    g.floating_texts.append(FloatingText(0, 0, "x", 10, 8))

    g.reset()

    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.last_broken_color == -1
    assert g.particles == []
    assert g.floating_texts == []
    assert all(len(col) == 0 for col in g.columns)
    assert g.cursor_col == 0
    assert g.phase == Phase.TITLE  # reset doesn't change phase, stays as-is (TITLE from _init_state)
    assert g.game_timer == 0


def test_init_state_sets_title_phase() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE


# ── _chop Tests ───────────────────────────────────────────────────────


def test_chop_empty_column_adds_heat() -> None:
    g = _make_game()
    initial_heat = g.heat
    score = g._chop(0)
    assert score == 0
    assert g.heat == initial_heat + HEAT_EMPTY_CHOP
    assert g.combo == 0
    assert g.last_broken_color == -1


def test_chop_empty_column_spawns_gray_particles() -> None:
    g = _make_game()
    g._chop(0)
    assert len(g.particles) > 0
    assert all(p.color == 13 for p in g.particles)  # GRAY = 13


def test_chop_first_board_always_matches() -> None:
    g = _make_game()
    g.columns[0].append(Board(color=8))  # RED
    g.combo = 0
    g.last_broken_color = -1

    score = g._chop(0)
    assert score > 0
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.heat == 0
    assert g.last_broken_color == 8


def test_chop_same_color_increments_combo() -> None:
    g = _make_game()
    g.columns[0].append(Board(color=8))  # RED
    g.last_broken_color = 8
    g.combo = 3

    g._chop(0)
    assert g.combo == 4
    assert g.max_combo == 4
    assert g.heat == 0


def test_chop_wrong_color_adds_heat_and_resets_combo() -> None:
    g = _make_game()
    g.columns[0].append(Board(color=3))  # GREEN
    g.last_broken_color = 8  # RED
    g.combo = 4
    g.max_combo = 4  # max_combo only updates on is_match, set externally

    g._chop(0)
    assert g.combo == 0
    assert g.max_combo == 4  # max_combo preserved
    assert g.heat == HEAT_WRONG_COLOR
    assert g.last_broken_color == 3


def test_chop_wrong_color_gives_base_score() -> None:
    g = _make_game()
    g.columns[0].append(Board(color=3))
    g.last_broken_color = 8
    g.combo = 4

    score = g._chop(0)
    # effective_combo = 1 (since is_match=False)
    assert score == BOARD_SCORE * 1


def test_chop_combo5_activates_super_mode() -> None:
    g = _make_game()
    g.columns[0].append(Board(color=8))
    g.last_broken_color = 8
    g.combo = 4  # next match → 5 → SUPER

    g._chop(0)
    assert g.combo == 5
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_chop_super_mode_wrong_color_no_heat() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.columns[0].append(Board(color=3))  # GREEN
    g.last_broken_color = 8  # RED — normally wrong color
    g.combo = 5

    g._chop(0)
    assert g.combo == 6  # still increments (super mode matches everything)
    assert g.heat == 0  # no HEAT penalty
    assert g.last_broken_color == 3


def test_chop_super_mode_3x_score() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.columns[0].append(Board(color=8))
    g.last_broken_color = 8
    g.combo = 5

    score = g._chop(0)
    # combo=6, BOARD_SCORE*6*3
    assert score == BOARD_SCORE * 6 * SUPER_SCORE_MULTIPLIER


def test_chop_super_mode_does_not_reactivate() -> None:
    """SUPER mode is already active — combo shouldn't trigger it again."""
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.columns[0].append(Board(color=8))
    g.last_broken_color = 8
    g.combo = 5  # >= threshold, but already super

    g._chop(0)
    assert g.super_mode is True
    assert g.super_timer == 100  # unchanged (not reset)


def test_chop_spawns_particles_with_board_color() -> None:
    g = _make_game()
    g.columns[0].append(Board(color=10))  # YELLOW
    g.last_broken_color = 10
    g.combo = 0

    g._chop(0)
    assert len(g.particles) >= 6
    assert all(p.color == 10 for p in g.particles)


def test_chop_spawns_floating_score() -> None:
    g = _make_game()
    g.columns[0].append(Board(color=8))
    g.last_broken_color = 8

    g._chop(0)
    assert len(g.floating_texts) >= 1
    assert g.floating_texts[0].text.startswith("+")


def test_chop_combo_3_spawns_combo_text() -> None:
    g = _make_game()
    g.columns[0].append(Board(color=8))
    g.last_broken_color = 8
    g.combo = 2  # after chop → 3 → COMBO text

    g._chop(0)
    texts = [ft.text for ft in g.floating_texts]
    combo_texts = [t for t in texts if "COMBO" in t]
    assert len(combo_texts) >= 1


def test_chop_removes_board_from_column() -> None:
    g = _make_game()
    g.columns[0] = [Board(color=1), Board(color=8), Board(color=8)]
    assert len(g.columns[0]) == 3

    g._chop(0)
    assert len(g.columns[0]) == 2


def test_chop_sets_shake_and_flash() -> None:
    g = _make_game()
    g.columns[0].append(Board(color=8))
    g.last_broken_color = 8

    g._chop(0)
    assert g.shake_timer > 0
    assert g.flash_timer > 0


def test_chop_invalid_col_idx_returns_zero() -> None:
    g = _make_game()
    assert g._chop(-1) == 0
    assert g._chop(99) == 0


# ── _score_for_break Tests ────────────────────────────────────────────


def test_score_for_break_normal() -> None:
    g = _make_game()
    g.super_mode = False
    s = g._score_for_break(Board(color=8), combo=3)
    assert s == BOARD_SCORE * 3


def test_score_for_break_super_mode() -> None:
    g = _make_game()
    g.super_mode = True
    s = g._score_for_break(Board(color=8), combo=3)
    assert s == BOARD_SCORE * 3 * SUPER_SCORE_MULTIPLIER


def test_score_for_break_combo1() -> None:
    g = _make_game()
    g.super_mode = False
    s = g._score_for_break(Board(color=8), combo=1)
    assert s == BOARD_SCORE


# ── _check_game_over Tests ────────────────────────────────────────────


def test_check_game_over_heat_max() -> None:
    g = _make_game()
    g.heat = MAX_HEAT
    assert g._check_game_over() is True


def test_check_game_over_heat_under_max() -> None:
    g = _make_game()
    g.heat = MAX_HEAT - 1
    assert g._check_game_over() is False


def test_check_game_over_column_overflow() -> None:
    g = _make_game()
    g.columns[0] = [Board(color=8)] * (MAX_BOARDS_PER_COLUMN + 1)
    assert g._check_game_over() is True


def test_check_game_over_column_at_limit() -> None:
    g = _make_game()
    g.columns[0] = [Board(color=8)] * MAX_BOARDS_PER_COLUMN
    assert g._check_game_over() is False


def test_check_game_over_initial_state() -> None:
    g = _make_game()
    assert g._check_game_over() is False


# ── _update_spawn Tests ───────────────────────────────────────────────


def test_update_spawn_adds_board() -> None:
    g = _make_game()
    # Force timer to expire
    g.spawn_timer = 1
    g._update_spawn(1)
    assert any(len(col) > 0 for col in g.columns)


def test_update_spawn_resets_timer() -> None:
    g = _make_game()
    g.spawn_interval = 90
    g.spawn_timer = 1
    g._update_spawn(1)
    assert g.spawn_timer >= 89  # 90 - (1 used) = 89, set to 89+


def test_update_spawn_no_spawn_when_timer_not_expired() -> None:
    g = _make_game()
    g.spawn_timer = 50
    initial_boards = sum(len(col) for col in g.columns)
    g._update_spawn(1)
    assert sum(len(col) for col in g.columns) == initial_boards


# ── _update_heat_decay Tests ──────────────────────────────────────────


def test_heat_decay_reduces_heat() -> None:
    g = _make_game()
    g.heat = 3
    g.heat_decay_timer = 1
    g._update_heat_decay(HEAT_DECAY_INTERVAL)  # big enough to trigger
    assert g.heat == 2


def test_heat_decay_stops_at_zero() -> None:
    g = _make_game()
    g.heat = 1
    g.heat_decay_timer = 1
    g._update_heat_decay(HEAT_DECAY_INTERVAL * 2)
    assert g.heat == 0


def test_heat_decay_no_decay_when_heat_is_zero() -> None:
    g = _make_game()
    g.heat = 0
    g.heat_decay_timer = 1
    g._update_heat_decay(HEAT_DECAY_INTERVAL * 10)
    assert g.heat == 0


# ── _update_super_timer Tests ─────────────────────────────────────────


def test_super_timer_decrements() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g._update_super_timer(1)
    assert g.super_timer == 99
    assert g.super_mode is True


def test_super_timer_expires() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_super_timer(1)
    assert g.super_timer == 0
    assert g.super_mode is False


def test_super_timer_no_op_when_inactive() -> None:
    g = _make_game()
    g.super_mode = False
    g.super_timer = 0
    g._update_super_timer(100)
    assert g.super_timer == 0
    assert g.super_mode is False


# ── _spawn_board Tests ────────────────────────────────────────────────


def test_spawn_board_adds_to_one_column() -> None:
    g = _make_game()
    initial = sum(len(col) for col in g.columns)
    g._spawn_board()
    assert sum(len(col) for col in g.columns) == initial + 1


def test_spawn_board_uses_valid_color() -> None:
    g = _make_game()
    g._spawn_board()
    # Find the board
    for col in g.columns:
        if col:
            assert col[-1].color in BOARD_COLORS
            return
    assert False, "No board spawned"


# ── _update_particles Tests ───────────────────────────────────────────


def test_update_particles_moves_positions() -> None:
    g = _make_game()
    p = Particle(x=50.0, y=100.0, vx=2.0, vy=-3.0, life=10, color=8)
    g.particles = [p]
    g._update_particles()
    assert p.x == 52.0
    # vy updated AFTER position: y = 100.0 + (-3.0) = 97.0, then vy = -3.0 + 0.1 = -2.9
    assert abs(p.y - 97.0) < 0.01


def test_update_particles_applies_gravity() -> None:
    g = _make_game()
    p = Particle(x=50.0, y=100.0, vx=0.0, vy=0.0, life=10, color=8)
    g.particles = [p]
    g._update_particles()
    assert abs(p.vy - PARTICLE_GRAVITY) < 0.001


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    p = Particle(x=50.0, y=100.0, vx=0.0, vy=0.0, life=1, color=8)
    g.particles = [p]
    g._update_particles()
    assert len(g.particles) == 0


def test_update_particles_keeps_alive() -> None:
    g = _make_game()
    p = Particle(x=50.0, y=100.0, vx=0.0, vy=0.0, life=2, color=8)
    g.particles = [p]
    g._update_particles()
    assert len(g.particles) == 1
    assert p.life == 1


# ── _update_floating_texts Tests ──────────────────────────────────────


def test_update_floating_texts_moves_up() -> None:
    g = _make_game()
    ft = FloatingText(x=50.0, y=100.0, text="+10", life=20, color=8)
    g.floating_texts = [ft]
    g._update_floating_texts()
    assert ft.y < 100.0  # moved up


def test_update_floating_texts_removes_dead() -> None:
    g = _make_game()
    ft = FloatingText(x=50.0, y=100.0, text="+10", life=1, color=8)
    g.floating_texts = [ft]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_update_floating_texts_keeps_alive() -> None:
    g = _make_game()
    ft = FloatingText(x=50.0, y=100.0, text="+10", life=2, color=8)
    g.floating_texts = [ft]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert ft.life == 1


# ── _update_difficulty Tests ──────────────────────────────────────────


def test_update_difficulty_decreases_spawn_interval() -> None:
    g = _make_game()
    initial = g.spawn_interval
    g._update_difficulty(SPAWN_DECREASE_INTERVAL)
    assert g.spawn_interval == initial - SPAWN_DECREASE_AMOUNT


def test_update_difficulty_respects_minimum() -> None:
    g = _make_game()
    g.spawn_interval = MIN_SPAWN_INTERVAL + 1
    g._update_difficulty(SPAWN_DECREASE_INTERVAL * 10)
    assert g.spawn_interval >= MIN_SPAWN_INTERVAL


def test_update_difficulty_no_decrease_below_threshold() -> None:
    g = _make_game()
    g.spawn_interval = INITIAL_SPAWN_INTERVAL
    g._update_difficulty(SPAWN_DECREASE_INTERVAL - 1)
    assert g.spawn_interval == INITIAL_SPAWN_INTERVAL


# ── update() Tests ────────────────────────────────────────────────────


def test_update_increments_game_timer() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.update(1)
    assert g.game_timer == 1


def test_update_skips_when_not_playing() -> None:
    g = _make_game()
    g.phase = Phase.TITLE
    g.update(1)
    assert g.game_timer == 0


def test_update_triggers_game_over_on_heat() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = MAX_HEAT
    g.update(1)
    assert g.phase == Phase.GAME_OVER


def test_update_triggers_game_over_on_overflow() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.columns[0] = [Board(color=8)] * (MAX_BOARDS_PER_COLUMN + 1)
    g.update(1)
    assert g.phase == Phase.GAME_OVER


def test_update_caps_heat() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = MAX_HEAT + 5
    g.update(1)
    assert g.heat == MAX_HEAT


# ── max_combo Tracking Tests ─────────────────────────────────────────


def test_max_combo_updated_on_new_record() -> None:
    g = _make_game()
    g.columns[0].append(Board(color=8))
    g.last_broken_color = -1
    g._chop(0)
    assert g.max_combo == 1

    g.columns[0].append(Board(color=8))
    g._chop(0)
    assert g.max_combo == 2


def test_max_combo_preserved_after_reset() -> None:
    g = _make_game()
    g.columns[0].append(Board(color=8))
    g.last_broken_color = -1
    g._chop(0)  # combo=1

    g.columns[0].append(Board(color=3))  # wrong color
    g._chop(0)  # combo=0
    assert g.max_combo == 1  # preserved


# ── Edge Case Tests ───────────────────────────────────────────────────


def test_multiple_boards_in_column_chop_order() -> None:
    """Top board (last in list) is broken first."""
    g = _make_game()
    g.columns[0] = [
        Board(color=8),   # bottom
        Board(color=3),   # middle
        Board(color=10),  # top (last) — this one breaks
    ]
    g.last_broken_color = 10

    g._chop(0)
    assert len(g.columns[0]) == 2
    # The remaining boards should be the bottom two
    assert g.columns[0][-1].color == 3  # now top


def test_rapid_chops_on_same_column() -> None:
    g = _make_game()
    g.columns[0] = [Board(color=8), Board(color=8), Board(color=8)]
    g.last_broken_color = -1

    s1 = g._chop(0)
    s2 = g._chop(0)
    s3 = g._chop(0)

    assert s1 > 0
    assert s2 > 0
    assert s3 > 0
    assert len(g.columns[0]) == 0
    assert g.combo == 3


def test_heat_decay_recovery_during_gameplay() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 5
    g.heat_decay_timer = HEAT_DECAY_INTERVAL

    # Simulate 2 decay cycles
    g.update(HEAT_DECAY_INTERVAL * 2)
    assert g.heat == 3  # 5 - 2


def test_super_mode_expires_during_update() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_mode = True
    g.super_timer = 1
    g.update(1)
    assert g.super_mode is False


# ── Chip Away at Super from High Combo ────────────────────────────────


def test_full_combo_to_super_flow() -> None:
    """Simulate building combo 1→2→3→4→5, triggering SUPER."""
    g = _make_game()
    g.phase = Phase.PLAYING

    # 5 same-color chops to reach SUPER
    for i in range(5):
        g.columns[0].append(Board(color=8))
        g._chop(0)

    assert g.combo == 5
    assert g.super_mode is True
    assert g.max_combo == 5


# ── Module Constants Tests ───────────────────────────────────────────


def test_num_columns() -> None:
    assert NUM_COLUMNS == 4


def test_board_colors_length() -> None:
    assert len(BOARD_COLORS) == 4


def test_max_boards_per_column_calculated() -> None:
    assert MAX_BOARDS_PER_COLUMN > 0
    assert MAX_BOARDS_PER_COLUMN < 20
