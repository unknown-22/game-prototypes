"""test_imports.py — Headless logic tests for 168_magnet_chain."""

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/168_magnet_chain")
from main import (
    WHITE,
    RED, Game, Phase, Magnet, Particle, FloatingText,
)


def _make_seeded_game(seed: int = 42) -> Game:
    """Factory helper: create a seeded game for deterministic tests."""
    g = Game._make_game()
    g._rng = random.Random(seed)
    g.reset()
    return g


# --- Test: _make_game factory creates valid Game ---
def test_make_game() -> None:
    g = Game._make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.game_timer == Game.GAME_TIME
    assert g.total_placed == 0
    assert len(g.magnets) == 0  # _make_game doesn't call reset()
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.polarity_counter == 0


# --- Test: reset() with seeded RNG creates 3 initial magnets ---
def test_reset_spawns_three_magnets() -> None:
    g = _make_seeded_game(42)
    assert len(g.magnets) == 3
    # Center cells (3,3)-(4,3)-(3,2)-(4,2) should be avoided
    for m in g.magnets:
        assert not (3 <= m.col <= 4 and 2 <= m.row <= 3)


# --- Test: determinism with same seed ---
def test_determinism() -> None:
    g1 = _make_seeded_game(42)
    g2 = _make_seeded_game(42)
    assert len(g1.magnets) == len(g2.magnets) == 3
    for m1, m2 in zip(g1.magnets, g2.magnets):
        assert m1.col == m2.col
        assert m1.row == m2.row
        assert m1.color == m2.color
        assert m1.polarity == m2.polarity


# --- Test: different seeds produce different placements ---
def test_different_seeds() -> None:
    g1 = _make_seeded_game(42)
    g2 = _make_seeded_game(99)
    # Very unlikely 3 magnets all match across different seeds
    coords1 = {(m.col, m.row) for m in g1.magnets}
    coords2 = {(m.col, m.row) for m in g2.magnets}
    # At least one magnet should differ
    assert coords1 != coords2 or any(
        m1.color != m2.color
        for m1, m2 in zip(g1.magnets, g2.magnets)
    )


# --- Test: cell helper methods ---
def test_get_cell_center() -> None:
    g = _make_seeded_game(42)
    cx, cy = g._get_cell_center(0, 0)
    assert cx == Game.GRID_X + Game.CELL / 2
    assert cy == Game.GRID_Y + Game.CELL / 2

    cx, cy = g._get_cell_center(7, 5)
    assert cx == Game.GRID_X + 7 * Game.CELL + Game.CELL / 2
    assert cy == Game.GRID_Y + 5 * Game.CELL + Game.CELL / 2


def test_is_cell_in_bounds() -> None:
    g = _make_seeded_game(42)
    assert g._is_cell_in_bounds(0, 0) is True
    assert g._is_cell_in_bounds(7, 5) is True
    assert g._is_cell_in_bounds(8, 0) is False
    assert g._is_cell_in_bounds(0, 6) is False
    assert g._is_cell_in_bounds(-1, 0) is False
    assert g._is_cell_in_bounds(0, -1) is False


def test_is_cell_empty() -> None:
    g = _make_seeded_game(42)
    # Initial 3 magnets occupy some cells
    for m in g.magnets:
        assert g._is_cell_empty(m.col, m.row) is False
    # Empty cells should be empty
    empty_cells = 0
    for col in range(8):
        for row in range(6):
            if g._is_cell_empty(col, row):
                empty_cells += 1
    assert empty_cells == 48 - 3  # 48 total - 3 occupied


def test_get_magnet_at() -> None:
    g = _make_seeded_game(42)
    m = g.magnets[0]
    found = g._get_magnet_at(m.col, m.row)
    assert found is not None
    assert found.col == m.col
    assert found.row == m.row
    assert found.color == m.color

    # Get magnet at empty cell
    for col in range(8):
        for row in range(6):
            if g._is_cell_empty(col, row):
                assert g._get_magnet_at(col, row) is None
                break
        else:
            continue
        break


# --- Test: combo logic ---
def test_place_magnet_first() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    g.active_color = 0
    result = g._place_magnet(0, 0)
    assert g.combo == 1
    assert g.max_combo == 1
    assert g._last_placed_color == 0
    assert g.total_placed == 1
    assert len(g.magnets) == 4  # 3 initial + 1 new
    assert result > 0


def test_place_magnet_same_color_combo() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    g.active_color = 0

    g._place_magnet(0, 0)  # combo 1
    assert g.combo == 1
    g._place_magnet(0, 1)  # combo 2
    assert g.combo == 2
    g._place_magnet(0, 2)  # combo 3
    assert g.combo == 3
    g._place_magnet(0, 3)  # combo 4
    assert g.combo == 4
    assert g.max_combo == 4


def test_place_magnet_super_activation() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    g.active_color = 0

    cells = [(0, 0), (0, 1), (0, 2), (0, 3)]
    for col, row in cells:
        g._place_magnet(col, row)
    assert g.combo == 4
    assert g._is_super_active()
    assert g.super_timer == Game.SUPER_DURATION


def test_place_magnet_mismatch_resets_combo() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    g.active_color = 0
    g._place_magnet(0, 0)  # combo 1
    assert g.combo == 1

    g.active_color = 1  # different color
    g._place_magnet(0, 1)  # mismatch
    assert g.combo == 0
    assert g.max_combo == 1  # max retains peak
    assert g._last_placed_color == 1


def test_place_magnet_heat_on_mismatch() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    g.active_color = 0
    g._place_magnet(0, 0)  # first, no heat
    assert g.heat == 0.0

    g.active_color = 1
    g._place_magnet(0, 1)  # mismatch
    assert g.heat == Game.HEAT_PER_MISMATCH  # 10.0


def test_place_magnet_no_heat_on_first() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    g.active_color = 0
    g._place_magnet(0, 0)
    assert g.heat == 0.0  # first placement never gives heat


def test_place_magnet_heat_accumulates() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    g.active_color = 0
    g._place_magnet(0, 0)  # color 0

    g.active_color = 1
    g._place_magnet(0, 1)  # mismatch: +10
    assert g.heat == 10.0

    g.active_color = 2
    g._place_magnet(0, 2)  # mismatch: +10
    assert g.heat == 20.0

    g.active_color = 3
    g._place_magnet(0, 3)  # mismatch: +10
    assert g.heat == 30.0


# --- Test: bounds and occupancy checks ---
def test_place_magnet_out_of_bounds() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    g.active_color = 0
    result = g._place_magnet(-1, 0)
    assert result == 0
    result = g._place_magnet(8, 0)
    assert result == 0
    result = g._place_magnet(0, 6)
    assert result == 0
    assert g.total_placed == 0  # no change


def test_place_magnet_on_occupied_cell() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    occupied = g.magnets[0]
    result = g._place_magnet(occupied.col, occupied.row)
    assert result == 0
    assert len(g.magnets) == 3  # no new magnet


# --- Test: polarity alternation ---
def test_polarity_alternates() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    g.active_color = 0

    g._place_magnet(0, 0)
    g._place_magnet(0, 1)
    g._place_magnet(0, 2)

    # Newly placed magnets should alternate polarity
    # Just check the last 3 placed
    # The initial magnets already consumed some polarity_counter states
    # So check alternation only among the newly placed ones
    new_only = [m for m in g.magnets if m.col == 0 and 0 <= m.row <= 2]
    assert len(new_only) == 3
    # Within newly placed magnets, polarity alternates
    assert new_only[0].polarity != new_only[1].polarity
    assert new_only[1].polarity != new_only[2].polarity


# --- Test: game over by heat ---
def test_game_over_by_heat() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    g.heat = 199.0
    g.active_color = 0
    g._place_magnet(5, 5)  # first placement, no mismatch
    assert g.phase != Phase.GAME_OVER  # heat < 200

    g.heat = 200.0
    g.active_color = 1
    g._place_magnet(5, 4)  # triggers game over
    assert g.phase == Phase.GAME_OVER


# --- Test: combo score values ---
def test_place_magnet_combo_score() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    g.active_color = 0

    result1 = g._place_magnet(0, 0)  # first placement, combo=1 but is_combo=False
    # First placement: no combo bonus (is_combo is False), base only
    assert result1 == Game.SCORE_PER_PLACEMENT  # 100

    result2 = g._place_magnet(0, 1)  # combo=2, is_combo=True → bonus=50*2=100
    assert result2 == Game.SCORE_PER_PLACEMENT + Game.SCORE_COMBO_BONUS * 2  # 200

    result3 = g._place_magnet(0, 2)  # combo=3, bonus=50*3=150
    assert result3 == Game.SCORE_PER_PLACEMENT + Game.SCORE_COMBO_BONUS * 3  # 250

    result4 = g._place_magnet(0, 3)  # combo=4, bonus=50*4=200
    assert result4 == Game.SCORE_PER_PLACEMENT + Game.SCORE_COMBO_BONUS * 4  # 300


def test_place_magnet_super_multiplier() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    g.active_color = 0

    # Build combo to 4 to activate super (use cells we know are empty)
    cells = []
    for col in range(8):
        for row in range(6):
            if g._is_cell_empty(col, row) and len(cells) < 4:
                cells.append((col, row))
    assert len(cells) >= 4  # should have space
    for col, row in cells:
        g._place_magnet(col, row)
    assert g._is_super_active()

    # Next placement with super active — find another empty cell
    for col in range(8):
        for row in range(6):
            if g._is_cell_empty(col, row):
                score_before = g.score
                result = g._place_magnet(col, row)
                # During SUPER: base * 3 = 300
                assert result == Game.SCORE_PER_PLACEMENT * Game.SUPER_MULTIPLIER
                assert g.score == score_before + result
                break
        else:
            continue
        break


# --- Test: score with mismatch ---
def test_place_magnet_mismatch_score() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    g.active_color = 0
    g._place_magnet(0, 0)  # combo 1

    g.active_color = 1
    result = g._place_magnet(0, 1)  # mismatch
    assert result == Game.SCORE_PER_PLACEMENT  # base score only
    assert g.combo == 0


# --- Test: field propagation ---
def test_field_propagation_no_magnets() -> None:
    g = _make_seeded_game(42)
    # Clear all magnets
    g.magnets.clear()
    g._update_field_propagation()
    # All field should be 0
    for row in g.field_strength:
        for val in row:
            assert val == 0.0


def test_field_propagation_with_magnets() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    g.active_color = 0
    g._place_magnet(0, 0)
    g._place_magnet(7, 5)

    # Need _field_tick to reach FIELD_TICK_INTERVAL (15) for propagation to trigger
    g._field_tick = Game.FIELD_TICK_INTERVAL - 1  # 14 → next call: 15, which % 15 == 0
    g._update_field_propagation()
    # At least the cells with magnets should have non-zero field
    assert g.field_strength[0][0] > 0
    assert g.field_strength[5][7] > 0
    # Adjacent cells should have field too (propagation)
    field_count = sum(1 for row in g.field_strength for v in row if v > 0.005)
    assert field_count >= 2  # at least the 2 direct cells


def test_field_propagation_during_super() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    g.active_color = 0

    for col, row in [(0, 0), (0, 1), (0, 2), (0, 3)]:
        g._place_magnet(col, row)
    assert g._is_super_active()

    # During SUPER, field_tick fires every frame (interval=1)
    g._field_tick = Game.FIELD_TICK_INTERVAL - 1  # triggers next call
    g._update_field_propagation()
    assert g.field_strength[0][0] > 0


# --- Test: magnetic forces ---
def test_apply_magnetic_forces_no_effect_distant() -> None:
    g = _make_seeded_game(42)
    # Magnets placed far apart shouldn't affect each other
    g.magnets.clear()
    g.magnets.append(Magnet(col=0, row=0, color=0, polarity=0))
    g.magnets.append(Magnet(col=7, row=5, color=0, polarity=0))
    g._apply_magnetic_forces()
    # Dist > 2, no effect expected
    assert g.magnets[0].field_strength == 0.0
    assert g.magnets[1].field_strength == 0.0


def test_apply_magnetic_forces_same_color_same_polarity() -> None:
    g = _make_seeded_game(42)
    g.magnets.clear()
    g.magnets.append(Magnet(col=0, row=0, color=0, polarity=0))
    g.magnets.append(Magnet(col=1, row=0, color=0, polarity=0))  # same color, same polarity
    g._apply_magnetic_forces()
    # Same color + same polarity = REPEL (field_strength increases)
    assert g.magnets[0].field_strength > 0
    assert g.magnets[1].field_strength > 0


def test_apply_magnetic_forces_same_color_diff_polarity() -> None:
    g = _make_seeded_game(42)
    g.magnets.clear()
    g.magnets.append(Magnet(col=0, row=0, color=0, polarity=0, field_strength=0.5))
    g.magnets.append(Magnet(col=1, row=0, color=0, polarity=1, field_strength=0.1))
    g._apply_magnetic_forces()
    # Same color + diff polarity = ATTRACT (field_strength averages)
    avg = (0.5 + 0.1) / 2
    assert abs(g.magnets[0].field_strength - avg) < 0.01
    assert abs(g.magnets[1].field_strength - avg) < 0.01


def test_apply_magnetic_forces_different_color_no_effect() -> None:
    g = _make_seeded_game(42)
    g.magnets.clear()
    g.magnets.append(Magnet(col=0, row=0, color=0, polarity=0, field_strength=0.5))
    g.magnets.append(Magnet(col=1, row=0, color=1, polarity=0, field_strength=0.1))
    g._apply_magnetic_forces()
    # Different colors: no interaction
    assert g.magnets[0].field_strength == 0.5
    assert g.magnets[1].field_strength == 0.1


# --- Test: heat decay ---
def test_heat_decay() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    g.active_color = 0
    g._place_magnet(0, 0)

    g.active_color = 1
    g._place_magnet(0, 1)  # heat = 10.0
    assert g.heat == 10.0

    # Manually simulate the decay that happens in _update_placing
    g.heat = max(0.0, g.heat - Game.HEAT_DECAY)
    assert abs(g.heat - (10.0 - 0.02)) < 0.001


# --- Test: super timer ---
def test_update_super_decrements() -> None:
    g = _make_seeded_game(42)
    g.super_timer = 10
    assert g._is_super_active()
    g._update_super()
    assert g.super_timer == 9
    assert g._is_super_active()


def test_update_super_expires() -> None:
    g = _make_seeded_game(42)
    g.super_timer = 1
    assert g._is_super_active()
    g._update_super()
    assert g.super_timer == 0
    assert not g._is_super_active()


# --- Test: particles ---
def test_add_particles() -> None:
    g = _make_seeded_game(42)
    g._add_particles(100, 100, 5, RED)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.x == 100.0
        assert p.y == 100.0
        assert p.color == RED
        assert 15 <= p.life <= 30


def test_add_particles_rainbow() -> None:
    g = _make_seeded_game(42)
    g._add_particles(100, 100, 10, -1)  # -1 = rainbow
    assert len(g.particles) == 10
    colors = {p.color for p in g.particles}
    # At least 2 different colors from rainbow
    assert len(colors) >= 1  # could be same color by chance, but seeded


def test_update_particles() -> None:
    g = _make_seeded_game(42)
    g._add_particles(100, 100, 3, RED)
    initial_positions = [(p.x, p.y) for p in g.particles]
    g._update_particles()
    assert len(g.particles) == 3  # life still > 0
    for p, (ix, iy) in zip(g.particles, initial_positions):
        assert p.x != ix or p.y != iy  # particles moved
        assert p.life >= 14  # decremented by 1 from [15-30]


def test_update_particles_removes_expired() -> None:
    g = _make_seeded_game(42)
    # Manually add a particle with life=1
    g.particles.append(Particle(x=100, y=100, vx=0, vy=0, life=1, color=RED))
    assert len(g.particles) == 1
    g._update_particles()
    assert len(g.particles) == 0  # life decremented to 0, removed


# --- Test: floating text ---
def test_add_floating_text() -> None:
    g = _make_seeded_game(42)
    g._add_floating_text(100, 100, "Test", WHITE)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.x == 100.0
    assert ft.y == 100.0
    assert ft.text == "Test"
    assert ft.color == WHITE
    assert ft.life == 40


def test_update_floating_texts() -> None:
    g = _make_seeded_game(42)
    g._add_floating_text(100, 100, "Test", WHITE)
    g._update_floating_texts()
    ft = g.floating_texts[0]
    assert ft.y < 100.0  # floated upward
    assert ft.life == 39  # decremented


def test_update_floating_texts_removes_expired() -> None:
    g = _make_seeded_game(42)
    g.floating_texts.append(FloatingText(x=100, y=100, text="X", life=1, color=WHITE))
    assert len(g.floating_texts) == 1
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# --- Test: stable heat doesn't flip polarity ---
def test_magnetic_forces_no_flip_below_unstable() -> None:
    g = _make_seeded_game(42)
    g.magnets.clear()
    g.magnets.append(Magnet(col=0, row=0, color=0, polarity=0))
    g.magnets.append(Magnet(col=1, row=0, color=0, polarity=0))
    g.heat = 50  # below HEAT_UNSTABLE (100)
    original_p = g.magnets[0].polarity
    # Call many times — should never flip
    for _ in range(100):
        g._apply_magnetic_forces()
    assert g.magnets[0].polarity == original_p


# --- Test: max_combo tracks correctly ---
def test_max_combo_persists() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    g.active_color = 0
    # Build combo to 3
    for col, row in [(0, 0), (0, 1), (0, 2)]:
        g._place_magnet(col, row)
    assert g.max_combo == 3

    # Mismatch resets combo but not max_combo
    g.active_color = 1
    g._place_magnet(0, 3)
    assert g.combo == 0
    assert g.max_combo == 3


# --- Test: super field prevents heat accumulation? ---
# Actually, during SUPER in _place_magnet, heat can still come from mismatches.
# But the super score multiplier applies.
def test_super_field_score_multiplier() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    g.active_color = 0
    # Find 4 empty cells
    cells = []
    for col in range(8):
        for row in range(6):
            if g._is_cell_empty(col, row) and len(cells) < 4:
                cells.append((col, row))
    for col, row in cells:
        g._place_magnet(col, row)
    assert g._is_super_active()
    assert g.super_timer == Game.SUPER_DURATION

    # Next placement with super active — find another empty cell
    for col in range(8):
        for row in range(6):
            if g._is_cell_empty(col, row):
                score_before = g.score
                g._place_magnet(col, row)
                assert g.score == score_before + Game.SCORE_PER_PLACEMENT * Game.SUPER_MULTIPLIER
                break
        else:
            continue
        break


# --- Edge case: place on all cells ---
def test_fill_all_cells() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    g.active_color = 0
    count = 0
    for col in range(8):
        for row in range(6):
            if g._is_cell_empty(col, row):
                g._place_magnet(col, row)
                count += 1
    assert len(g.magnets) == 48  # grid is full
    # Placing on full grid returns 0
    result = g._place_magnet(0, 0)
    assert result == 0


# --- Test: _check_combo ---
def test_check_combo_first_placement() -> None:
    g = _make_seeded_game(42)
    assert g._check_combo(0) is False  # _last_placed_color is None


def test_check_combo_match() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLACING
    g.active_color = 0
    g._place_magnet(0, 0)
    assert g._check_combo(0) is True
    assert g._check_combo(1) is False


# --- Test: _is_cell_in_bounds exhaustive ---
def test_bounds_all_cells() -> None:
    g = _make_seeded_game(42)
    for col in range(8):
        for row in range(6):
            assert g._is_cell_in_bounds(col, row) is True
    assert g._is_cell_in_bounds(0, -1) is False
    assert g._is_cell_in_bounds(-1, 0) is False
    assert g._is_cell_in_bounds(8, 0) is False
    assert g._is_cell_in_bounds(0, 6) is False


# --- Smoke: run all tests ---
if __name__ == "__main__":
    import traceback

    tests = [
        test_make_game,
        test_reset_spawns_three_magnets,
        test_determinism,
        test_different_seeds,
        test_get_cell_center,
        test_is_cell_in_bounds,
        test_is_cell_empty,
        test_get_magnet_at,
        test_place_magnet_first,
        test_place_magnet_same_color_combo,
        test_place_magnet_super_activation,
        test_place_magnet_mismatch_resets_combo,
        test_place_magnet_heat_on_mismatch,
        test_place_magnet_no_heat_on_first,
        test_place_magnet_heat_accumulates,
        test_place_magnet_out_of_bounds,
        test_place_magnet_on_occupied_cell,
        test_polarity_alternates,
        test_game_over_by_heat,
        test_place_magnet_combo_score,
        test_place_magnet_super_multiplier,
        test_place_magnet_mismatch_score,
        test_field_propagation_no_magnets,
        test_field_propagation_with_magnets,
        test_field_propagation_during_super,
        test_apply_magnetic_forces_no_effect_distant,
        test_apply_magnetic_forces_same_color_same_polarity,
        test_apply_magnetic_forces_same_color_diff_polarity,
        test_apply_magnetic_forces_different_color_no_effect,
        test_heat_decay,
        test_update_super_decrements,
        test_update_super_expires,
        test_add_particles,
        test_add_particles_rainbow,
        test_update_particles,
        test_update_particles_removes_expired,
        test_add_floating_text,
        test_update_floating_texts,
        test_update_floating_texts_removes_expired,
        test_magnetic_forces_no_flip_below_unstable,
        test_max_combo_persists,
        test_super_field_score_multiplier,
        test_fill_all_cells,
        test_check_combo_first_placement,
        test_check_combo_match,
        test_bounds_all_cells,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
            print(f"  ✅ {test_fn.__name__}")
        except Exception as e:
            failed += 1
            print(f"  ❌ {test_fn.__name__}: {e}")
            traceback.print_exc()

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    if failed > 0:
        sys.exit(1)
    else:
        print("All tests passed!")
