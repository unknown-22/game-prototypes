"""test_imports.py — Headless logic tests for TYPE SURGE."""
import sys
import random
import unittest.mock as mock

mock_display = mock.MagicMock()
mock_display.return_value = None
sys.modules["pyxel"] = mock.MagicMock()
sys.modules["pyxel"].COLOR_BLACK = 0
sys.modules["pyxel"].COLOR_NAVY = 1
sys.modules["pyxel"].COLOR_PURPLE = 2
sys.modules["pyxel"].COLOR_GREEN = 3
sys.modules["pyxel"].COLOR_BROWN = 4
sys.modules["pyxel"].COLOR_DARK_BLUE = 5
sys.modules["pyxel"].COLOR_LIGHT_BLUE = 6
sys.modules["pyxel"].COLOR_WHITE = 7
sys.modules["pyxel"].COLOR_RED = 8
sys.modules["pyxel"].COLOR_ORANGE = 9
sys.modules["pyxel"].COLOR_YELLOW = 10
sys.modules["pyxel"].COLOR_LIME = 11
sys.modules["pyxel"].COLOR_CYAN = 12
sys.modules["pyxel"].COLOR_GRAY = 13
sys.modules["pyxel"].COLOR_PINK = 14
sys.modules["pyxel"].COLOR_PEACH = 15
sys.modules["pyxel"].MOUSE_BUTTON_LEFT = 0
sys.modules["pyxel"].MOUSE_BUTTON_RIGHT = 1
sys.modules["pyxel"].MOUSE_BUTTON_MIDDLE = 2
sys.modules["pyxel"].KEY_A = 1
sys.modules["pyxel"].KEY_S = 2
sys.modules["pyxel"].KEY_D = 3
sys.modules["pyxel"].KEY_F = 4
sys.modules["pyxel"].KEY_SPACE = 8
sys.modules["pyxel"].KEY_RETURN = 9
sys.modules["pyxel"].btnp = mock.MagicMock(return_value=False)
sys.modules["pyxel"].btn = mock.MagicMock(return_value=False)
sys.modules["pyxel"].frame_count = 0

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/226_type_surge")

from main import (  # noqa: E402
    Game, Phase,
    COLS, ROWS, GAME_DURATION, SUPER_DURATION, MAX_HEAT,
    WRONG_KEY_HEAT, COMBO_THRESHOLD, HEAT_DECAY,
    SPREAD_BASE_INTERVAL, SPREAD_MIN_INTERVAL,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.grid = [[-1 for _ in range(COLS)] for _ in range(ROWS)]
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.super_mode = False
    g.super_timer = 0
    g.heat = 0.0
    g.game_timer = GAME_DURATION
    g.last_cleared = -1
    g.particles = []
    g.floating_texts = []
    g.spread_timer = SPREAD_BASE_INTERVAL
    g.spawn_timer = 120
    g.total_cleared = 0
    g._rng = random.Random(42)
    return g


# ---- Test reset ----

def test_reset_clears_all_state() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.grid[0][0] = 0
    g.score = 100
    g.combo = 5
    g.heat = 80
    g.game_timer = 100
    g.last_cleared = 2
    g.super_mode = True
    g.super_timer = 50

    g.reset()
    g.phase = Phase.PLAYING

    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.game_timer == GAME_DURATION
    assert g.last_cleared == -1
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.total_cleared == 0
    for row in g.grid:
        for cell in row:
            assert cell == -1


# ---- Test _handle_keypress ----

def test_handle_keypress_clears_matching() -> None:
    g = _make_game()
    g.grid[0][0] = 0  # A at (0,0)
    g.grid[0][1] = 0  # A at (1,0)
    g.grid[1][0] = 1  # S at (0,1)

    cleared = g._handle_keypress("A")
    assert cleared == 2
    assert g.grid[0][0] == -1
    assert g.grid[0][1] == -1
    assert g.grid[1][0] == 1  # S still there


def test_handle_keypress_increases_heat_on_miss() -> None:
    g = _make_game()
    g.grid[0][0] = 0  # only A

    g._handle_keypress("S")
    assert g.heat == WRONG_KEY_HEAT
    assert g.combo == 0
    assert g.last_cleared == -1


def test_handle_keypress_heat_on_empty_grid() -> None:
    g = _make_game()

    g._handle_keypress("A")
    assert g.heat == WRONG_KEY_HEAT


def test_combo_increments_on_same_letter() -> None:
    g = _make_game()
    g.grid[0][0] = 0  # A
    g.grid[0][1] = 0  # A

    g._handle_keypress("A")
    assert g.combo == 1

    g.grid[0][0] = 0  # more A
    g._handle_keypress("A")
    assert g.combo == 2


def test_combo_resets_on_different_letter() -> None:
    g = _make_game()
    g.grid[0][0] = 0  # A
    g._handle_keypress("A")
    assert g.combo == 1

    g.grid[0][0] = 1  # S
    g._handle_keypress("S")
    assert g.combo == 1  # reset to 1


def test_combo_activates_super_mode() -> None:
    g = _make_game()
    for _ in range(COMBO_THRESHOLD):
        g.grid[0][0] = 0  # A
        g._handle_keypress("A")

    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_super_mode_clears_all_letters() -> None:
    g = _make_game()
    g.grid[0][0] = 0  # A
    g.grid[1][1] = 1  # S
    g.grid[2][2] = 2  # D
    g.grid[3][3] = 3  # F

    g.super_mode = True
    cleared = g._handle_keypress("A")
    assert cleared == 4
    for row in g.grid:
        for cell in row:
            assert cell == -1


def test_super_mode_3x_score() -> None:
    g = _make_game()
    for y in range(2):
        g.grid[y][0] = 0  # A x2

    g.super_mode = True
    initial_score = g.score
    g._handle_keypress("A")
    gained = g.score - initial_score
    # 2 cells * (1 + combo*0.5) * 3
    assert gained == int(2 * (1 + 1 * 0.5) * 3)


def test_score_calculation_with_combo() -> None:
    g = _make_game()
    g.grid[0][0] = 0  # A
    g.grid[0][1] = 0  # A
    g.grid[0][2] = 0  # A

    g._handle_keypress("A")
    gained = g.score
    assert gained == int(3 * (1 + 1 * 0.5) * 1)


def test_super_mode_expires() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 3

    g._update_timers()
    assert g.super_timer == 2
    assert g.super_mode is True

    g._update_timers()
    g._update_timers()
    assert g.super_timer == 0
    assert g.super_mode is False


# ---- Test grid spread ----

def test_spread_letters_fills_adjacent() -> None:
    g = _make_game()
    g.grid[4][5] = 0  # A at center
    g._rng = random.Random(1)

    g._spread_letters()

    neighbor_filled = False
    for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
        nx, ny = 5 + dx, 4 + dy
        if 0 <= nx < COLS and 0 <= ny < ROWS and g.grid[ny][nx] == 0:
            neighbor_filled = True
            break
    assert neighbor_filled


def test_spread_respects_bounds() -> None:
    g = _make_game()
    g.grid[0][0] = 0
    g._rng = random.Random(0)

    for _ in range(10):
        g._spread_letters()

    for y in range(ROWS):
        for x in range(COLS):
            assert 0 <= g.grid[y][x] <= 3 or g.grid[y][x] == -1


# ---- Test _spawn_letter ----

def test_spawn_letter_at_edge() -> None:
    g = _make_game()
    g._spawn_letter()

    edge_has_letter = False
    for x in range(COLS):
        if g.grid[0][x] != -1 or g.grid[ROWS - 1][x] != -1:
            edge_has_letter = True
            break
    for y in range(1, ROWS - 1):
        if g.grid[y][0] != -1 or g.grid[y][COLS - 1] != -1:
            edge_has_letter = True
            break
    assert edge_has_letter


def test_spawn_letter_full_grid_adds_heat() -> None:
    g = _make_game()
    for y in range(ROWS):
        for x in range(COLS):
            g.grid[y][x] = 0

    initial_heat = g.heat
    g._spawn_letter()
    assert g.heat > initial_heat


# ---- Test _grid_occupancy ----

def test_grid_occupancy_empty() -> None:
    g = _make_game()
    assert g._grid_occupancy() == 0.0


def test_grid_occupancy_full() -> None:
    g = _make_game()
    for y in range(ROWS):
        for x in range(COLS):
            g.grid[y][x] = 0
    assert g._grid_occupancy() == 1.0


def test_grid_occupancy_half() -> None:
    g = _make_game()
    for y in range(ROWS // 2):
        for x in range(COLS):
            g.grid[y][x] = 0
    assert g._grid_occupancy() == 0.5


# ---- Test HEAT ----

def test_heat_decays() -> None:
    g = _make_game()
    g.heat = 10.0
    g._update_heat()
    assert g.heat == 10.0 - HEAT_DECAY


def test_heat_pressure_above_threshold() -> None:
    g = _make_game()
    for y in range(ROWS):
        for x in range(COLS):
            g.grid[y][x] = 0
    g.heat = 0.0
    g._update_heat()
    assert g.heat > 0.0


def test_heat_at_max_triggers_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = MAX_HEAT
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


# ---- Test timer ----

def test_game_timer_triggers_game_over() -> None:
    g = _make_game()
    g.game_timer = 1
    g._update_timers()
    assert g.game_timer == 0
    assert g.phase == Phase.GAME_OVER


def test_spread_timer_triggers_spread() -> None:
    g = _make_game()
    g.grid[2][2] = 0
    g.spread_timer = 1
    g._rng = random.Random(1)

    g._update_timers()

    spread_happened = False
    for y in range(ROWS):
        for x in range(COLS):
            if (x, y) != (2, 2) and g.grid[y][x] != -1:
                spread_happened = True
                break
    assert spread_happened


def test_spawn_timer_triggers_spawn() -> None:
    g = _make_game()
    g.spawn_timer = 1
    g._update_timers()

    has_letter = any(c != -1 for row in g.grid for c in row)
    assert has_letter


# ---- Test particles ----

def test_particles_spawn_and_update() -> None:
    g = _make_game()
    g._spawn_particles(100, 100, 8, 5)
    assert len(g.particles) == 5

    for _ in range(50):
        g._update_particles()

    assert len(g.particles) == 0


def test_floating_text_spawn_and_update() -> None:
    g = _make_game()
    g._spawn_floating_text(100, 100, "+10", 7)
    assert len(g.floating_texts) == 1

    for _ in range(50):
        g._update_floating_texts()

    assert len(g.floating_texts) == 0


# ---- Test _adjacent_empty ----

def test_adjacent_empty_center() -> None:
    g = _make_game()
    adj = g._adjacent_empty(5, 4)
    assert len(adj) == 4


def test_adjacent_empty_corner() -> None:
    g = _make_game()
    adj = g._adjacent_empty(0, 0)
    assert len(adj) == 2


def test_adjacent_empty_edges() -> None:
    g = _make_game()
    adj = g._adjacent_empty(0, 4)
    assert len(adj) == 3


# ---- Test current spread interval ----

def test_spread_interval_decreases() -> None:
    g = _make_game()
    g.game_timer = GAME_DURATION // 2
    interval = g._current_spread_interval()
    assert SPREAD_MIN_INTERVAL <= interval <= SPREAD_BASE_INTERVAL
    assert interval < SPREAD_BASE_INTERVAL


# ---- Run all tests ----
if __name__ == "__main__":
    import traceback

    tests = [
        ("test_reset_clears_all_state", test_reset_clears_all_state),
        ("test_handle_keypress_clears_matching", test_handle_keypress_clears_matching),
        ("test_handle_keypress_increases_heat_on_miss", test_handle_keypress_increases_heat_on_miss),
        ("test_handle_keypress_heat_on_empty_grid", test_handle_keypress_heat_on_empty_grid),
        ("test_combo_increments_on_same_letter", test_combo_increments_on_same_letter),
        ("test_combo_resets_on_different_letter", test_combo_resets_on_different_letter),
        ("test_combo_activates_super_mode", test_combo_activates_super_mode),
        ("test_super_mode_clears_all_letters", test_super_mode_clears_all_letters),
        ("test_super_mode_3x_score", test_super_mode_3x_score),
        ("test_score_calculation_with_combo", test_score_calculation_with_combo),
        ("test_super_mode_expires", test_super_mode_expires),
        ("test_spread_letters_fills_adjacent", test_spread_letters_fills_adjacent),
        ("test_spread_respects_bounds", test_spread_respects_bounds),
        ("test_spawn_letter_at_edge", test_spawn_letter_at_edge),
        ("test_spawn_letter_full_grid_adds_heat", test_spawn_letter_full_grid_adds_heat),
        ("test_grid_occupancy_empty", test_grid_occupancy_empty),
        ("test_grid_occupancy_full", test_grid_occupancy_full),
        ("test_grid_occupancy_half", test_grid_occupancy_half),
        ("test_heat_decays", test_heat_decays),
        ("test_heat_pressure_above_threshold", test_heat_pressure_above_threshold),
        ("test_heat_at_max_triggers_game_over", test_heat_at_max_triggers_game_over),
        ("test_game_timer_triggers_game_over", test_game_timer_triggers_game_over),
        ("test_spread_timer_triggers_spread", test_spread_timer_triggers_spread),
        ("test_spawn_timer_triggers_spawn", test_spawn_timer_triggers_spawn),
        ("test_particles_spawn_and_update", test_particles_spawn_and_update),
        ("test_floating_text_spawn_and_update", test_floating_text_spawn_and_update),
        ("test_adjacent_empty_center", test_adjacent_empty_center),
        ("test_adjacent_empty_corner", test_adjacent_empty_corner),
        ("test_adjacent_empty_edges", test_adjacent_empty_edges),
        ("test_spread_interval_decreases", test_spread_interval_decreases),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS {name}")
            passed += 1
        except Exception:
            print(f"  FAIL {name}")
            traceback.print_exc()
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
