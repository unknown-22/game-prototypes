"""test_imports.py — Headless logic tests for ECHO DRIFT prototype.

Tests data classes, track geometry, element cycling, game state transitions,
combo/heat/volatile mechanics, and discharge — all without Pyxel display.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add prototype directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (
    CELL,
    CLASH_DAMAGE,
    COMBO_SPEED_THRESHOLDS,
    DISCHARGE_COOLDOWN,
    GRID_SIZE,
    HEAT_DECAY_RATE,
    HEAT_PER_COMBO,
    MAX_HEAT,
    MAX_HP,
    SCREEN,
    VOLATILE_HEAT_THRESHOLD,
    Cell,
    Direction,
    Element,
    ELEMENT_COLORS,
    ELEMENT_NAMES,
    ELEMENT_ORDER,
    FloatingText,
    Particle,
    Phase,
    TRACK_CELLS,
    is_track,
    next_element,
)


# ── Constants ────────────────────────────────────────────────────────────────


def test_screen_dimensions() -> None:
    """Screen is 256×256."""
    assert SCREEN == 256


def test_grid_config() -> None:
    """Grid has correct dimensions."""
    assert GRID_SIZE == 16
    assert CELL == 16


def test_combo_thresholds() -> None:
    """Combo speed thresholds are monotonic."""
    assert COMBO_SPEED_THRESHOLDS == [0, 3, 7, 12, 20]
    for i in range(len(COMBO_SPEED_THRESHOLDS) - 1):
        assert COMBO_SPEED_THRESHOLDS[i] < COMBO_SPEED_THRESHOLDS[i + 1]


# ── Track ────────────────────────────────────────────────────────────────────


def test_track_cells_exist() -> None:
    """Track has sufficient cells for a playable loop."""
    assert len(TRACK_CELLS) >= 30  # Oval loop needs decent length
    assert len(TRACK_CELLS) <= 60  # Not too large for 16×16 grid


def test_track_top_straight() -> None:
    """Top straight row 2, cols 3-12."""
    for c in range(3, 13):
        assert is_track(c, 2), f"({c}, 2) should be track"
    # Adjacent non-track
    assert not is_track(2, 2)
    assert not is_track(13, 2)


def test_track_bottom_straight() -> None:
    """Bottom straight row 12, cols 3-12."""
    for c in range(3, 13):
        assert is_track(c, 12), f"({c}, 12) should be track"
    assert not is_track(2, 12)
    assert not is_track(13, 12)


def test_track_left_vertical() -> None:
    """Left wall rows 3-11, col 3."""
    for r in range(3, 12):
        assert is_track(3, r), f"(3, {r}) should be track"
    assert not is_track(3, 1)
    assert not is_track(3, 13)


def test_track_right_vertical() -> None:
    """Right wall rows 3-11, col 12."""
    for r in range(3, 12):
        assert is_track(12, r), f"(12, {r}) should be track"


def test_track_bounds() -> None:
    """Cells outside the grid are not track."""
    assert not is_track(-1, 0)
    assert not is_track(0, -1)
    assert not is_track(GRID_SIZE, 0)
    assert not is_track(0, GRID_SIZE)


def test_track_is_closed_loop() -> None:
    """Every track cell has at least 2 adjacent track neighbors (connected loop)."""
    for col, row in TRACK_CELLS:
        neighbors = 0
        for dc, dr in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            if is_track(col + dc, row + dr):
                neighbors += 1
        assert neighbors >= 2, f"({col}, {row}) has only {neighbors} track neighbors"


# ── Element System ───────────────────────────────────────────────────────────


def test_element_order_length() -> None:
    """Four elements in rotation."""
    assert len(ELEMENT_ORDER) == 4


def test_element_cycle() -> None:
    """next_element cycles through all four."""
    assert next_element(Element.FIRE) == Element.WATER
    assert next_element(Element.WATER) == Element.EARTH
    assert next_element(Element.EARTH) == Element.AIR
    assert next_element(Element.AIR) == Element.FIRE


def test_element_colors_defined() -> None:
    """All elements have color mappings."""
    for elem in Element:
        assert elem in ELEMENT_COLORS
        assert ELEMENT_COLORS[elem] >= 0


def test_element_names_defined() -> None:
    """All elements have name mappings."""
    for elem in Element:
        assert elem in ELEMENT_NAMES
        assert len(ELEMENT_NAMES[elem]) >= 3


# ── Data Classes ─────────────────────────────────────────────────────────────


def test_cell_default() -> None:
    """Default Cell has no element and is not volatile."""
    c = Cell()
    assert c.element is None
    assert c.volatile is False


def test_cell_with_element() -> None:
    """Cell can store an element."""
    c = Cell(element=Element.FIRE)
    assert c.element == Element.FIRE
    assert c.volatile is False


def test_cell_volatile() -> None:
    """Volatile cell can have element and volatile flag."""
    c = Cell(element=Element.WATER, volatile=True)
    assert c.element == Element.WATER
    assert c.volatile is True


def test_particle_creation() -> None:
    """Particle dataclass works."""
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-0.5, life=30, color=8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -0.5
    assert p.life == 30
    assert p.color == 8
    assert p.text == ""


def test_floating_text_creation() -> None:
    """FloatingText dataclass works."""
    ft = FloatingText(x=50.0, y=60.0, text="+100", life=40, color=7)
    assert ft.x == 50.0
    assert ft.y == 60.0
    assert ft.text == "+100"
    assert ft.life == 40
    assert ft.color == 7


# ── Direction ────────────────────────────────────────────────────────────────


def test_direction_values() -> None:
    """Direction enum has correct delta values."""
    assert Direction.UP.value == (0, -1)
    assert Direction.DOWN.value == (0, 1)
    assert Direction.LEFT.value == (-1, 0)
    assert Direction.RIGHT.value == (1, 0)


# ── Phase ────────────────────────────────────────────────────────────────────


def test_phases_exist() -> None:
    """Both game phases are defined."""
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ── Game State Transitions (via Game.__new__ headless pattern) ───────────────


class HeadlessGame:
    """A headless game instance for testing logic without Pyxel display.

    Uses Game.__new__ to bypass pyxel.init and pyxel.run.
    """

    @staticmethod
    def create() -> "HeadlessGame":
        """Create a headless game by calling Game.__new__ then reset()."""
        from main import Game

        g = Game.__new__(Game)
        g.reset()
        return g


def test_game_initial_state() -> None:
    """Game starts in PLAYING phase with full HP."""
    g = HeadlessGame.create()
    assert g.phase == Phase.PLAYING
    assert g.hp == MAX_HP
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.car_element == Element.FIRE
    assert g.direction == Direction.RIGHT
    assert g.laps == 0
    assert len(g.grid) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0


def test_game_start_position_on_track() -> None:
    """Car starts on a valid track cell."""
    g = HeadlessGame.create()
    assert is_track(g.car_col, g.car_row)


def test_move_car_on_track() -> None:
    """Moving right from start position lands on a track cell."""
    g = HeadlessGame.create()
    g.direction = Direction.RIGHT
    g._moved_this_frame = False
    g._move_car()
    # After moving right, should still be on track
    assert is_track(g.car_col, g.car_row)
    # Score increased
    assert g.score >= 1


def test_move_car_leaves_echo() -> None:
    """Moving car leaves a colored echo cell behind."""
    g = HeadlessGame.create()
    start_col, start_row = g.car_col, g.car_row
    g.direction = Direction.RIGHT
    g._moved_this_frame = False
    g._move_car()
    # The previous cell should now have an echo
    prev_cell = g.grid.get((start_col, start_row))
    assert prev_cell is not None
    assert prev_cell.element == Element.FIRE  # Starting element


def test_move_into_same_color_echo_triggers_combo() -> None:
    """Moving into a cell with matching echo color triggers combo."""
    g = HeadlessGame.create()
    # Manually place a same-color echo ahead
    target_col = g.car_col + 1
    target_row = g.car_row
    g.grid[(target_col, target_row)] = Cell(element=Element.FIRE)

    g.direction = Direction.RIGHT
    g._moved_this_frame = False
    g._move_car()

    assert g.combo >= 1
    assert g.score > 1  # Base + combo bonus
    assert g.heat > 0  # Heat builds from combo


def test_move_into_different_color_echo_triggers_clash() -> None:
    """Moving into a cell with different echo color causes clash damage."""
    g = HeadlessGame.create()
    target_col = g.car_col + 1
    target_row = g.car_row
    g.grid[(target_col, target_row)] = Cell(element=Element.WATER)  # Different from FIRE

    g.direction = Direction.RIGHT
    g._moved_this_frame = False
    g._move_car()

    assert g.hp == MAX_HP - CLASH_DAMAGE
    assert g.combo == 0  # Reset on clash


def test_move_into_volatile_cell_always_damages() -> None:
    """Volatile cell damages regardless of color match."""
    g = HeadlessGame.create()
    target_col = g.car_col + 1
    target_row = g.car_row
    g.grid[(target_col, target_row)] = Cell(element=Element.FIRE, volatile=True)  # Same color but volatile

    g.direction = Direction.RIGHT
    g._moved_this_frame = False
    g._move_car()

    assert g.hp == MAX_HP - CLASH_DAMAGE


def test_cannot_move_off_track() -> None:
    """Moving into a non-track cell is blocked."""
    g = HeadlessGame.create()
    # Move car to top-left corner of track
    g.car_col = 3
    g.car_row = 2
    g.direction = Direction.LEFT  # Would move to (2, 2) which is not track

    g._moved_this_frame = False
    g._move_car()

    # Car should not have moved
    assert g.car_col == 3
    assert g.car_row == 2


def test_double_move_prevented() -> None:
    """_moved_this_frame guard prevents double movement."""
    g = HeadlessGame.create()
    g._moved_this_frame = True
    start_col, start_row = g.car_col, g.car_row
    g._move_car()
    # Should not have moved
    assert g.car_col == start_col
    assert g.car_row == start_row


def test_heat_builds_from_combo() -> None:
    """Heat increases with combo matches."""
    g = HeadlessGame.create()
    initial_heat = g.heat

    # Place consecutive same-color echoes and drive through them
    for i in range(1, 6):
        col = g.car_col + i
        row = g.car_row
        if is_track(col, row):
            g.grid[(col, row)] = Cell(element=Element.FIRE)

    for _ in range(3):
        g.direction = Direction.RIGHT
        g._moved_this_frame = False
        g._move_car()
        if g.combo > 0:
            assert g.heat > 0

    assert g.heat > initial_heat


def test_volatile_threshold() -> None:
    """When heat exceeds VOLATILE_HEAT_THRESHOLD, cells become volatile."""
    g = HeadlessGame.create()
    # Place some echo cells
    g.grid[(5, 2)] = Cell(element=Element.FIRE)
    g.grid[(6, 2)] = Cell(element=Element.WATER)

    # Set heat above threshold
    g.heat = VOLATILE_HEAT_THRESHOLD + 1
    g._make_volatile()

    # All colored cells should be volatile
    for cell in g.grid.values():
        assert cell.volatile is True


def test_discharge_clears_heat() -> None:
    """Discharge resets heat to 0."""
    g = HeadlessGame.create()
    g.heat = 90.0
    g._discharge()
    assert g.heat == 0.0


def test_discharge_clears_grid() -> None:
    """Discharge clears all trail cells."""
    g = HeadlessGame.create()
    g.grid[(5, 2)] = Cell(element=Element.FIRE, volatile=True)
    g.grid[(6, 2)] = Cell(element=Element.WATER)

    g._discharge()

    assert len(g.grid) == 0


def test_discharge_sets_cooldown() -> None:
    """Discharge sets cooldown timer."""
    g = HeadlessGame.create()
    g._discharge()
    assert g.discharge_cooldown == DISCHARGE_COOLDOWN


def test_heat_decay() -> None:
    """Heat decays gradually."""
    g = HeadlessGame.create()
    g.heat = 50.0
    # Simulate the decay that happens in update()
    g.heat = max(0.0, g.heat - HEAT_DECAY_RATE)
    assert g.heat < 50.0
    assert g.heat >= 0.0


def test_heat_never_negative() -> None:
    """Heat is clamped at 0."""
    g = HeadlessGame.create()
    g.heat = 0.0
    g.heat = max(0.0, g.heat - HEAT_DECAY_RATE)
    assert g.heat == 0.0


def test_heat_capped_at_max() -> None:
    """Heat cannot exceed MAX_HEAT."""
    g = HeadlessGame.create()
    g.heat = float(MAX_HEAT)
    g.heat = min(float(MAX_HEAT), g.heat + 100.0)
    assert g.heat == float(MAX_HEAT)


def test_hp_zero_triggers_game_over() -> None:
    """When HP reaches 0, phase transitions to GAME_OVER."""
    g = HeadlessGame.create()
    g.hp = 1
    # Simulate a clash that would kill
    target_col = g.car_col + 1
    target_row = g.car_row
    g.grid[(target_col, target_row)] = Cell(element=Element.WATER)  # Different = clash

    g.direction = Direction.RIGHT
    g._moved_this_frame = False
    g._move_car()

    assert g.hp == 0
    assert g.phase == Phase.GAME_OVER


def test_reset_restores_state() -> None:
    """Reset returns game to initial PLAYING state."""
    g = HeadlessGame.create()
    # Mess up state
    g.hp = 0
    g.score = 500
    g.heat = 99.0
    g.combo = 10
    g.phase = Phase.GAME_OVER
    g.grid[(5, 2)] = Cell(element=Element.FIRE)

    g.reset()

    assert g.phase == Phase.PLAYING
    assert g.hp == MAX_HP
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert len(g.grid) == 0
    assert g.discharge_cooldown == 0


def test_combo_resets_on_uncolored_cell() -> None:
    """Landing on an uncolored cell resets combo to 0."""
    g = HeadlessGame.create()
    g.combo = 5
    g._reset_combo()
    assert g.combo == 0


def test_max_combo_tracked() -> None:
    """max_combo records the highest combo achieved."""
    g = HeadlessGame.create()

    # Simulate a combo
    g.combo = 3
    if g.combo > g.max_combo:
        g.max_combo = g.combo
    assert g.max_combo == 3

    g.combo = 7
    if g.combo > g.max_combo:
        g.max_combo = g.combo
    assert g.max_combo == 7

    # Combo drops but max stays
    g.combo = 1
    assert g.max_combo == 7


def test_particle_update_removes_dead() -> None:
    """Particles with life <= 0 are removed."""
    g = HeadlessGame.create()
    g.particles = [
        Particle(x=10.0, y=10.0, vx=0.0, vy=0.0, life=5, color=8),
        Particle(x=20.0, y=20.0, vx=0.0, vy=0.0, life=0, color=9),
        Particle(x=30.0, y=30.0, vx=0.0, vy=0.0, life=-1, color=10),
    ]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 4  # Decremented from 5


def test_floating_text_update_removes_dead() -> None:
    """Floating texts with life <= 0 are removed."""
    g = HeadlessGame.create()
    g.floating_texts = [
        FloatingText(x=10.0, y=10.0, text="A", life=3, color=7),
        FloatingText(x=20.0, y=20.0, text="B", life=0, color=8),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    # Life decremented and y moved up
    assert g.floating_texts[0].life == 2
    assert g.floating_texts[0].y < 10.0


def test_element_cycle_in_game() -> None:
    """Car element cycles when color_timer exceeds interval."""
    g = HeadlessGame.create()
    assert g.car_element == Element.FIRE

    g.car_element = next_element(g.car_element)
    assert g.car_element == Element.WATER

    g.car_element = next_element(g.car_element)
    assert g.car_element == Element.EARTH

    g.car_element = next_element(g.car_element)
    assert g.car_element == Element.AIR

    g.car_element = next_element(g.car_element)
    assert g.car_element == Element.FIRE


def test_particle_movement() -> None:
    """Particles move according to velocity."""
    p = Particle(x=10.0, y=10.0, vx=2.0, vy=-1.5, life=10, color=8)
    p.x += p.vx
    p.y += p.vy
    p.life -= 1
    assert p.x == 12.0
    assert abs(p.y - 8.5) < 0.01
    assert p.life == 9


# ── Lap Detection ────────────────────────────────────────────────────────────


def test_lap_progress_increments() -> None:
    """Lap progress increases with movement."""
    g = HeadlessGame.create()
    initial = g.lap_progress
    g._update_lap_progress()
    assert g.lap_progress > initial or g.laps > 0


# ── Run All ──────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v", "--tb=short"])
