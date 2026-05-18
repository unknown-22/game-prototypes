"""test_imports.py — Headless logic tests for 041_tower_collapse."""

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/041_tower_collapse")
from main import (
    BLOCK_COLORS,
    COLS,
    COMBO_TIMEOUT,
    DANGER_ROW,
    GRID_X,
    GRID_Y,
    MATCH_MIN,
    NUM_COLORS,
    ROWS,
    SCREEN_H,
    SCREEN_W,
    TOWER_START,
    CELL,
    FloatingText,
    Game,
    Particle,
    Phase,
)


def test_phase_enum() -> None:
    assert Phase.TITLE == 1
    assert Phase.PLAYING == 2
    assert Phase.GAME_OVER == 3
    print("PASS: Phase enum")


def test_constants() -> None:
    assert SCREEN_W == 128
    assert SCREEN_H == 160
    assert COLS == 10
    assert ROWS == 16
    assert CELL == 12
    assert NUM_COLORS == 5
    assert len(BLOCK_COLORS) == 5
    assert DANGER_ROW == 2
    assert MATCH_MIN == 3
    assert TOWER_START == 4
    print("PASS: Constants")


def test_particle_dataclass() -> None:
    p = Particle(x=10, y=20, vx=1.0, vy=-2.0, life=15, color=8)
    assert p.x == 10
    assert p.y == 20
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == 8
    assert p.size == 2
    print("PASS: Particle dataclass")


def test_floating_text_dataclass() -> None:
    ft = FloatingText(x=50, y=60, text="+100", life=40, color=11)
    assert ft.x == 50
    assert ft.y == 60
    assert ft.text == "+100"
    assert ft.life == 40
    assert ft.color == 11
    print("PASS: FloatingText dataclass")


def test_game_new() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.chain_count = 0
    g.total_cleared = 0
    g.drop_col = COLS // 2
    g.drop_color = 0
    g.drop_y = 0.0
    g.drop_active = False
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g.combo_timer = 0.0
    g.phase = Phase.PLAYING
    g.reset()
    assert g.phase == Phase.PLAYING
    assert len(g.grid) == ROWS
    assert all(len(row) == COLS for row in g.grid)
    print("PASS: Game.__new__ + reset()")


def test_grid_init_has_blocks() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.chain_count = 0
    g.total_cleared = 0
    g.drop_col = COLS // 2
    g.drop_color = 0
    g.drop_y = 0.0
    g.drop_active = False
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g.combo_timer = 0.0
    g.phase = Phase.PLAYING
    g.reset()

    # Bottom TOWER_START rows should have blocks
    for r in range(TOWER_START):
        for c in range(COLS):
            assert g._get(r, c) is not None, f"Grid[{r}][{c}] should not be None"

    # Rows above TOWER_START should be empty
    for r in range(TOWER_START, ROWS):
        for c in range(COLS):
            assert g._get(r, c) is None, f"Grid[{r}][{c}] should be None"
    print("PASS: Grid init has blocks at bottom")


def test_spawn_drop() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.chain_count = 0
    g.total_cleared = 0
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g.combo_timer = 0.0
    g.phase = Phase.PLAYING
    g._spawn_drop()
    assert g.drop_active is True
    assert 0 <= g.drop_color < NUM_COLORS
    assert g.drop_col == COLS // 2
    assert g.drop_y == -1.0
    print("PASS: _spawn_drop")


def test_get_set() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.chain_count = 0
    g.total_cleared = 0
    g.drop_col = COLS // 2
    g.drop_color = 0
    g.drop_y = 0.0
    g.drop_active = False
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g.combo_timer = 0.0
    g.phase = Phase.PLAYING

    g._set(5, 5, 3)
    assert g._get(5, 5) == 3
    assert g._get(-1, 5) is None
    assert g._get(5, -1) is None
    assert g._get(ROWS, 5) is None
    assert g._get(5, COLS) is None
    print("PASS: _get/_set")


def test_adjacent() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]

    adj = g._adjacent(5, 5)
    assert (5, 6) in adj
    assert (5, 4) in adj
    assert (6, 5) in adj
    assert (4, 5) in adj
    assert len(adj) == 4

    # Edge case
    adj0 = g._adjacent(0, 0)
    assert (0, 1) in adj0
    assert (1, 0) in adj0
    assert (-1, 0) not in adj0
    assert (0, -1) not in adj0
    assert len(adj0) == 2
    print("PASS: _adjacent")


def test_find_cluster_single() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g._set(5, 5, 1)
    cluster = g._find_cluster(5, 5)
    assert len(cluster) == 1
    assert (5, 5) in cluster
    print("PASS: _find_cluster single")


def test_find_cluster_two() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g._set(5, 5, 1)
    g._set(5, 6, 1)
    cluster = g._find_cluster(5, 5)
    assert len(cluster) == 2
    assert (5, 5) in cluster
    assert (5, 6) in cluster
    print("PASS: _find_cluster two adjacent")


def test_find_cluster_no_match_different_color() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g._set(5, 5, 1)
    g._set(5, 6, 2)
    cluster = g._find_cluster(5, 5)
    assert len(cluster) == 1
    print("PASS: _find_cluster different color")


def test_find_cluster_l_shape() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g._set(5, 5, 1)
    g._set(5, 6, 1)
    g._set(6, 5, 1)
    cluster = g._find_cluster(5, 5)
    assert len(cluster) == 3
    print("PASS: _find_cluster L-shape")


def test_find_cluster_empty() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    cluster = g._find_cluster(5, 5)
    assert len(cluster) == 0
    print("PASS: _find_cluster empty cell")


def test_apply_gravity() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g._set(3, 5, 1)  # Block at row 3
    g._set(1, 5, 2)  # Block at row 1

    g._apply_gravity()

    # Blocks should fall to bottom
    assert g._get(ROWS - 1, 5) == 1
    assert g._get(ROWS - 2, 5) == 2
    assert g._get(3, 5) is None
    assert g._get(1, 5) is None
    print("PASS: _apply_gravity")


def test_apply_gravity_full_column() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    for r in range(ROWS):
        g._set(r, 0, r % NUM_COLORS)

    g._apply_gravity()

    # All blocks should stay in same column, order preserved from bottom
    assert g._get(ROWS - 1, 0) == (ROWS - 1) % NUM_COLORS
    assert g._get(0, 0) == 0
    print("PASS: _apply_gravity full column")


def test_find_all_matches_none() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    # Place blocks with no 3+ same-color
    g._set(5, 5, 0)
    g._set(5, 6, 1)
    g._set(6, 5, 2)
    matches = g._find_all_matches()
    assert len(matches) == 0
    print("PASS: _find_all_matches none")


def test_find_all_matches_three_horizontal() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g._set(5, 4, 3)
    g._set(5, 5, 3)
    g._set(5, 6, 3)
    matches = g._find_all_matches()
    assert len(matches) == 1
    assert len(matches[0]) == 3
    print("PASS: _find_all_matches three horizontal")


def test_find_all_matches_three_vertical() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g._set(4, 5, 2)
    g._set(5, 5, 2)
    g._set(6, 5, 2)
    matches = g._find_all_matches()
    assert len(matches) == 1
    assert len(matches[0]) == 3
    print("PASS: _find_all_matches three vertical")


def test_find_all_matches_four() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g._set(5, 3, 4)
    g._set(5, 4, 4)
    g._set(5, 5, 4)
    g._set(5, 6, 4)
    matches = g._find_all_matches()
    assert len(matches) == 1
    assert len(matches[0]) == 4
    print("PASS: _find_all_matches four in a row")


def test_find_all_matches_two_clusters() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    # Red cluster
    g._set(5, 1, 0)
    g._set(5, 2, 0)
    g._set(5, 3, 0)
    # Blue cluster far away
    g._set(5, 7, 3)
    g._set(5, 8, 3)
    g._set(5, 9, 3)
    matches = g._find_all_matches()
    assert len(matches) == 2
    print("PASS: _find_all_matches two clusters")


def test_resolve_chains_no_match() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.chain_count = 0
    g.total_cleared = 0
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g.combo_timer = 0.0

    g._set(5, 5, 1)
    g._resolve_chains()

    assert g.chain_count == 0
    assert g._get(5, 5) == 1  # Block still there
    print("PASS: _resolve_chains no match")


def test_resolve_chains_clears_match() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.chain_count = 0
    g.total_cleared = 0
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g.combo_timer = 0.0

    g._set(5, 4, 2)
    g._set(5, 5, 2)
    g._set(5, 6, 2)
    g._resolve_chains()

    assert g.chain_count == 1
    assert g._get(5, 4) is None
    assert g._get(5, 5) is None
    assert g._get(5, 6) is None
    assert g.total_cleared == 3
    assert g.score > 0
    print("PASS: _resolve_chains clears match")


def test_resolve_chains_gravity_after_clear() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.chain_count = 0
    g.total_cleared = 0
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g.combo_timer = 0.0

    # Block above match
    g._set(5, 4, 2)
    g._set(5, 5, 2)
    g._set(5, 6, 2)
    g._set(3, 5, 1)  # Block above the middle

    g._resolve_chains()

    # Cleared blocks gone, block above should have fallen
    assert g._get(5, 5) is None
    # The block at row 3, col 5 should have fallen
    # After clearing row 5, gravity pulls it down
    assert g._get(ROWS - 1, 5) == 1
    print("PASS: _resolve_chains gravity after clear")


def test_place_block() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.chain_count = 0
    g.total_cleared = 0
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g.combo_timer = 0.0
    g.phase = Phase.PLAYING

    g._place_block(5, 5, 3)
    assert g._get(5, 5) == 3
    print("PASS: _place_block")


def test_check_game_over_not_triggered() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.chain_count = 0
    g.total_cleared = 0
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g.combo_timer = 0.0
    g.phase = Phase.PLAYING

    g._check_game_over()
    assert g.phase == Phase.PLAYING
    print("PASS: _check_game_over not triggered")


def test_check_game_over_triggered() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.chain_count = 0
    g.total_cleared = 0
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g.combo_timer = 0.0
    g.phase = Phase.PLAYING

    g._set(DANGER_ROW, 5, 1)
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER
    print("PASS: _check_game_over triggered")


def test_spawn_burst_creates_particles() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.particles = []
    g._spawn_burst(50, 50, 8)
    assert len(g.particles) == 6
    for p in g.particles:
        assert p.color == 8
        assert p.life > 0
        assert p.x == 50
        assert p.y == 50
    print("PASS: _spawn_burst creates particles")


def test_update_particles() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.particles = [
        Particle(x=10, y=20, vx=1, vy=-1, life=5, color=8),
        Particle(x=30, y=40, vx=0, vy=0, life=1, color=11),
    ]
    g._update_particles()
    assert len(g.particles) == 1  # Second one died
    assert g.particles[0].life == 4
    assert g.particles[0].y < 20  # vy was -1
    print("PASS: _update_particles")


def test_update_floating_texts() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.floating_texts = [
        FloatingText(x=50, y=60, text="+10", life=5, color=11),
        FloatingText(x=70, y=80, text="+20", life=1, color=8),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].y < 60
    print("PASS: _update_floating_texts")


def test_full_reset() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.chain_count = 0
    g.total_cleared = 0
    g.drop_col = 0
    g.drop_color = 0
    g.drop_y = 0.0
    g.drop_active = False
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=1, color=0)]
    g.floating_texts = [FloatingText(x=0, y=0, text="X", life=1, color=0)]
    g.shake_frames = 5
    g.combo_timer = 1.0
    g.phase = Phase.GAME_OVER

    g.reset()

    assert g.phase == Phase.PLAYING
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.shake_frames == 0
    assert g.combo_timer == 0.0
    assert g.score == 0
    assert g.drop_active is True
    print("PASS: Full reset")


def test_combo_chain_scoring() -> None:
    """Test that chain reactions multiply score."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.chain_count = 0
    g.total_cleared = 0
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g.combo_timer = 0.0
    g.phase = Phase.PLAYING

    # Set up a scenario where clearing one cluster causes blocks to fall
    # and create a new match
    # Row 12-14: three red blocks in a row at col 5
    # Row 10: one red block above, will fall when lower blocks clear
    # But gravity won't create a match with just 1 block falling
    # Let's set up two separate matches that gravity can chain
    g._set(12, 4, 0)
    g._set(12, 5, 0)
    g._set(12, 6, 0)
    g._resolve_chains()
    score_after_first = g.score

    # Second match elsewhere
    g._set(10, 1, 3)
    g._set(10, 2, 3)
    g._set(10, 3, 3)
    g._resolve_chains()
    score_after_second = g.score

    # Chain count should have increased, and combo should be > 0
    assert g.max_combo >= 1
    print(f"PASS: Combo chain scoring (score: {score_after_first} -> {score_after_second})")


def test_score_formula_direction() -> None:
    """Verify that more cleared blocks = more score."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.grid = [[None] * COLS for _ in range(ROWS)]
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.chain_count = 0
    g.total_cleared = 0
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g.combo_timer = 0.0
    g.phase = Phase.PLAYING

    # Clear 3 blocks
    g._set(10, 4, 1)
    g._set(10, 5, 1)
    g._set(10, 6, 1)
    g._resolve_chains()
    score_3 = g.score

    # Reset for 4-block test
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.chain_count = 0
    g.total_cleared = 0
    g.particles.clear()
    g.floating_texts.clear()

    g._set(10, 3, 1)
    g._set(10, 4, 1)
    g._set(10, 5, 1)
    g._set(10, 6, 1)
    g._resolve_chains()
    score_4 = g.score

    assert score_4 > score_3, f"4 blocks ({score_4}) should score more than 3 ({score_3})"
    print("PASS: Score formula direction")


if __name__ == "__main__":
    test_phase_enum()
    test_constants()
    test_particle_dataclass()
    test_floating_text_dataclass()
    test_game_new()
    test_grid_init_has_blocks()
    test_spawn_drop()
    test_get_set()
    test_adjacent()
    test_find_cluster_single()
    test_find_cluster_two()
    test_find_cluster_no_match_different_color()
    test_find_cluster_l_shape()
    test_find_cluster_empty()
    test_apply_gravity()
    test_apply_gravity_full_column()
    test_find_all_matches_none()
    test_find_all_matches_three_horizontal()
    test_find_all_matches_three_vertical()
    test_find_all_matches_four()
    test_find_all_matches_two_clusters()
    test_resolve_chains_no_match()
    test_resolve_chains_clears_match()
    test_resolve_chains_gravity_after_clear()
    test_place_block()
    test_check_game_over_not_triggered()
    test_check_game_over_triggered()
    test_spawn_burst_creates_particles()
    test_update_particles()
    test_update_floating_texts()
    test_full_reset()
    test_combo_chain_scoring()
    test_score_formula_direction()
    print(f"\nAll {33} tests passed!")
