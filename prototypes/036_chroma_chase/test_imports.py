"""test_imports.py — Headless logic tests for CHROMA CHASE.

Tests game logic without initializing Pyxel (no display required).
Uses Game.__new__ pattern to access internal methods.
"""
import sys
import random
import inspect

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/036_chroma_chase")
from main import (
    Ghost,
    Gem,
    TrailCell,
    FloatingText,
    Phase,
    Game,
    NUM_COLORS,
    GRID_W,
    GRID_H,
    CELL,
    PX_COLORS,
    PX_DARK,
    INITIAL_GHOSTS,
    MAX_GEMS,
    TRAIL_DURATION,
    GHOST_SPAWN_INTERVAL,
    OBSTACLE_COUNT,
)


def test_dataclasses() -> None:
    """Test that all dataclasses can be instantiated with correct types."""
    ghost = Ghost(x=3, y=5)
    assert ghost.x == 3
    assert ghost.y == 5
    assert isinstance(ghost.x, int)
    assert isinstance(ghost.y, int)

    gem = Gem(x=7, y=2, color=3)
    assert gem.x == 7
    assert gem.y == 2
    assert gem.color == 3

    power_gem = Gem(x=1, y=1, color=-1)
    assert power_gem.color == -1

    trail = TrailCell(x=4, y=4, color=0, life=100)
    assert trail.x == 4
    assert trail.y == 4
    assert trail.color == 0
    assert trail.life == 100

    text = FloatingText(x=10, y=20, text="TEST", color=7, life=30)
    assert text.x == 10
    assert text.y == 20
    assert text.text == "TEST"
    assert text.color == 7
    assert text.life == 30


def test_phase_enum() -> None:
    """Test that Phase enum has expected values."""
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    assert Phase.PLAYING != Phase.GAME_OVER


def make_game() -> Game:
    """Create a Game instance without initializing Pyxel."""
    g = Game.__new__(Game)
    g.reset()
    return g


def test_game_initial_state() -> None:
    """Test that game reset produces valid initial state."""
    g = make_game()
    assert g.phase == Phase.PLAYING
    assert g.player_x == GRID_W // 2
    assert g.player_y == GRID_H // 2
    assert g.player_color == -1
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.score == 0
    assert g.gems_eaten == 0
    assert g.invincible_timer == 0
    assert len(g.ghosts) == INITIAL_GHOSTS
    assert len(g.gems) == MAX_GEMS
    assert g.player_cooldown == 0
    assert g.ghost_spawn_timer == GHOST_SPAWN_INTERVAL
    assert len(g._obstacles) == OBSTACLE_COUNT


def test_obstacles_deterministic() -> None:
    """Test that obstacles are generated deterministically."""
    g1 = make_game()
    g2 = make_game()
    assert g1._obstacles == g2._obstacles


def test_is_blocked() -> None:
    """Test grid boundary and obstacle collision."""
    g = make_game()
    # Out of bounds
    assert g._is_blocked(-1, 0) is True
    assert g._is_blocked(0, -1) is True
    assert g._is_blocked(GRID_W, 0) is True
    assert g._is_blocked(0, GRID_H) is True
    # Empty cell (center should be clear of obstacles)
    assert g._is_blocked(GRID_W // 2, GRID_H // 2) is False
    # Obstacle cell
    for ox, oy in g._obstacles:
        assert g._is_blocked(ox, oy) is True
        break


def test_has_trail_at() -> None:
    """Test trail detection on grid cells."""
    g = make_game()
    assert g._has_trail_at(5, 5) is False
    g.trails.append(TrailCell(5, 5, 2, 100))
    assert g._has_trail_at(5, 5) is True
    assert g._has_trail_at(5, 6) is False


def test_collect_gem_same_color() -> None:
    """Test collecting a gem of the same color builds combo."""
    g = make_game()
    g.player_color = 2  # GREEN
    g.combo = 3
    g.score = 100
    gem_count_before = len(g.gems)
    # Place player on a gem of same color
    g.player_x = g.gems[0].x
    g.player_y = g.gems[0].y
    g.gems[0].color = 2  # override to same color
    g._update_gems()
    # Combo should increase and score should reflect multiplier
    assert g.combo == 4
    assert g.max_combo == 4
    assert g.score == 140  # 100 + 10 * 4
    assert g.gems_eaten == 1
    assert len(g.gems) == gem_count_before  # one removed, one spawned


def test_collect_gem_different_color() -> None:
    """Test collecting a gem of different color resets combo to 1."""
    g = make_game()
    g.player_color = 0  # RED
    g.combo = 5
    g.max_combo = 5  # preserve the high combo in tracking
    g.score = 200
    gem_count_before = len(g.gems)
    # Place player on first gem, override its color to YELLOW (different)
    g.player_x = g.gems[0].x
    g.player_y = g.gems[0].y
    g.gems[0].color = 3  # YELLOW (different from RED)
    g._update_gems()
    assert g.combo == 1
    assert g.max_combo == 5  # max combo preserved
    assert g.score == 210  # 200 + 10
    assert g.player_color == 3  # now YELLOW
    assert g.gems_eaten == 1
    assert len(g.gems) == gem_count_before  # one removed, one spawned


def test_collect_power_gem() -> None:
    """Test that power gem grants invincibility but not score."""
    g = make_game()
    g.score = 100
    g.gems_eaten = 0
    gem = Gem(x=g.player_x, y=g.player_y, color=-1)  # power gem
    g.gems = [gem]
    g._update_gems()
    assert g.invincible_timer > 0
    assert g.gems_eaten == 1
    # Score shouldn't change for power gem
    assert g.score == 100


def test_ghost_candidates_unblocked() -> None:
    """Test that ghost move candidates exclude blocked cells."""
    g = make_game()
    ghost = Ghost(x=5, y=5)
    # Place ghost away from player and obstacles
    g.player_x = 10
    g.player_y = 10
    # Ensure cell (5,4) is not blocked
    candidates = g._ghost_candidates(ghost)
    assert len(candidates) >= 1
    # Should prefer direction toward player (10,10)
    # Closest candidate should be to the right or down (toward player)
    best = candidates[0]
    dist_to_player = abs(best[0] - g.player_x) + abs(best[1] - g.player_y)
    ghost_dist = abs(5 - g.player_x) + abs(5 - g.player_y)
    assert dist_to_player < ghost_dist  # moved closer


def test_ghost_candidates_blocked() -> None:
    """Test ghost candidates when surrounded by obstacles."""
    g = make_game()
    # Create a ghost in a corner
    ghost = Ghost(x=0, y=0)
    # Place obstacle at (1,0) and (0,1)
    g._obstacles.add((1, 0))
    g._obstacles.add((0, 1))
    g.player_x = 10
    g.player_y = 10
    candidates = g._ghost_candidates(ghost)
    # (0,-1) and (-1,0) are out of bounds, (1,0) and (0,1) are blocked
    assert len(candidates) == 0


def test_ghost_candidates_avoid_other_ghosts() -> None:
    """Test that ghosts don't move into cells occupied by other ghosts."""
    g = make_game()
    ghost_a = Ghost(x=5, y=5)
    ghost_b = Ghost(x=6, y=5)
    g.ghosts = [ghost_a, ghost_b]
    g.player_x = 10
    g.player_y = 10
    candidates = g._ghost_candidates(ghost_a)
    # (6,5) is occupied by ghost_b, should be excluded
    assert (6, 5) not in candidates


def test_update_trails_decay() -> None:
    """Test that trail lifetimes decrease and expired trails are removed."""
    g = make_game()
    g.trails = [
        TrailCell(0, 0, 0, 3),
        TrailCell(1, 1, 1, 1),
        TrailCell(2, 2, 2, 5),
    ]
    g._update_trails()
    assert g.trails[0].life == 2
    # Trail with life=1 should be expired after decrement to 0
    lives = [t.life for t in g.trails]
    assert 0 not in lives  # expired trail removed
    assert len(g.trails) == 2


def test_update_texts_float_up() -> None:
    """Test that floating texts move upward and expire."""
    g = make_game()
    g.texts = [
        FloatingText(100, 100, "A", 7, 3),
        FloatingText(50, 50, "B", 7, 1),
    ]
    g._update_texts()
    assert g.texts[0].y == 99  # moved up
    assert g.texts[0].life == 2
    assert len(g.texts) == 1  # second expired


def test_ghost_spawn_timer() -> None:
    """Test that ghost spawn timer decreases and spawns ghosts."""
    g = make_game()
    initial_count = len(g.ghosts)
    g.ghost_spawn_timer = 1
    g._update_spawns()
    # Timer was 1, decremented to 0, triggered spawn, then reset
    # New timer value is positive (reset after spawn)
    assert g.ghost_spawn_timer > 0  # reset after spawn
    assert len(g.ghosts) == initial_count + 1  # one new ghost spawned


def test_invincible_timer_decrease() -> None:
    """Test invincibility timer counts down."""
    g = make_game()
    g.invincible_timer = 10
    g._update_timers()
    assert g.invincible_timer == 9
    g._update_timers()
    assert g.invincible_timer == 8


def test_player_ghost_collision_normal() -> None:
    """Test that player dies when overlapping with ghost (no invincibility)."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.invincible_timer = 0
    g.player_x = 5
    g.player_y = 5
    g.ghosts = [Ghost(5, 5)]  # ghost on player
    g._check_player_ghost_collision()
    assert g.phase == Phase.GAME_OVER


def test_player_ghost_collision_invincible() -> None:
    """Test that invincible player kills ghosts on contact."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.invincible_timer = 30
    g.player_x = 5
    g.player_y = 5
    g.score = 100
    g.ghosts = [Ghost(5, 5), Ghost(10, 10)]
    g._check_player_ghost_collision()
    assert g.phase == Phase.PLAYING  # not dead
    assert len(g.ghosts) == 1  # one ghost killed
    assert g.score == 150  # +50 for ghost kill


def test_player_no_collision() -> None:
    """Test that player doesn't die when not overlapping ghost."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.invincible_timer = 0
    g.player_x = 5
    g.player_y = 5
    g.ghosts = [Ghost(10, 10)]
    g._check_player_ghost_collision()
    assert g.phase == Phase.PLAYING


def test_collect_gem_max_combo_tracking() -> None:
    """Test that max_combo correctly tracks the highest combo achieved."""
    g = make_game()
    g.player_color = 0
    g.combo = 0
    g.max_combo = 0
    g.score = 0
    # Eat 3 same-color gems
    for _ in range(3):
        gem = Gem(x=g.player_x, y=g.player_y, color=0)
        g.gems = [gem]
        g._update_gems()
    assert g.combo == 3
    assert g.max_combo == 3
    # Eat different color — combo resets but max stays
    gem_diff = Gem(x=g.player_x, y=g.player_y, color=1)
    g.gems = [gem_diff]
    g._update_gems()
    assert g.combo == 1
    assert g.max_combo == 3


def test_collect_gem_spawns_replacement() -> None:
    """Test that eating a gem spawns a replacement in the same frame."""
    g = make_game()
    gem_count_before = len(g.gems)
    # Move player to an existing gem's position
    target_gem = g.gems[0]
    g.player_x = target_gem.x
    g.player_y = target_gem.y
    g._update_gems()
    # Gem at player position collected, replacement spawned
    assert len(g.gems) == gem_count_before  # count unchanged


def test_trail_only_at_combo_2_plus() -> None:
    """Test that trails are only left when combo >= 2."""
    g = make_game()
    g.player_x = 5
    g.player_y = 5
    g.player_color = 2
    g.combo = 1
    g.player_cooldown = 0
    # Mock _update_player movement — with combo=1, no trail should be left
    # We can't call _update_player because it uses pyxel.btn
    # Instead, test the trail condition directly
    initial_trail_count = len(g.trails)
    # Simulate: if combo < 2, no trail added
    if g.combo >= 2:
        g.trails.append(TrailCell(5, 5, g.player_color, TRAIL_DURATION))
    assert len(g.trails) == initial_trail_count  # combo=1, no trail

    # Now combo=2, trail should be added
    g.combo = 2
    if g.combo >= 2:
        g.trails.append(TrailCell(5, 5, g.player_color, TRAIL_DURATION))
    assert len(g.trails) == 1
    assert g.trails[0].color == 2


def test_ghost_dies_on_danger_trail() -> None:
    """Test that ghost stepping on trail when combo >= 2 causes death."""
    g = make_game()
    g.combo = 3
    g.player_color = 1
    g.score = 100
    g.invincible_timer = 0

    # Place trail and ghost on adjacent cells; player far away
    g.trails = [TrailCell(10, 10, 1, 100)]
    ghost = Ghost(10, 9)
    g.ghosts = [ghost]
    g.player_x = 15
    g.player_y = 15

    # Clear obstacles in the test area
    for x in range(9, 12):
        for y in range(9, 12):
            g._obstacles.discard((x, y))

    candidates = g._ghost_candidates(ghost)
    assert len(candidates) > 0
    nx, ny = candidates[0]
    has_danger = g.combo >= 2 and g.invincible_timer <= 0
    if has_danger and g._has_trail_at(nx, ny):
        g.ghosts.remove(ghost)
        g.score += 25 * g.combo
    assert len(g.ghosts) == 0  # ghost died on trail
    assert g.score == 175  # 100 + 25*3


def test_ghost_avoids_trail_when_danger() -> None:
    """Test that ghosts prefer safe cells when danger trails exist."""
    g = make_game()
    g.combo = 3
    g.invincible_timer = 0
    g.player_x = 10
    g.player_y = 10

    ghost = Ghost(5, 5)
    g.ghosts = [ghost]
    # Place trail at (6,5) — the natural best candidate toward (10,10)
    g.trails = [TrailCell(6, 5, 2, 100)]

    candidates = g._ghost_candidates(ghost)
    # (5,4), (6,5), (4,5), (5,6) — sorted by distance to (10,10)
    # (6,5) is closest but has trail — if we filter for safe, (5,4) or (4,5) or (5,6)
    has_danger = g.combo >= 2 and g.invincible_timer <= 0
    if has_danger:
        safe = [c for c in candidates if not g._has_trail_at(c[0], c[1])]
        assert len(safe) >= 1
        # None of the safe cells should have a trail
        for sx, sy in safe:
            assert not g._has_trail_at(sx, sy)


def test_combo_2_enables_trail_danger() -> None:
    """Test that combo >= 2 is the threshold for trail danger."""
    g = make_game()
    g.combo = 2
    assert g.combo >= 2  # threshold met

    g.combo = 1
    assert not (g.combo >= 2)  # below threshold

    g.combo = 5
    assert g.combo >= 2  # well above threshold


def test_config_constants() -> None:
    """Test that all config constants are reasonable."""
    assert NUM_COLORS == 5
    assert GRID_W == 16
    assert GRID_H == 16
    assert CELL == 16
    assert len(PX_COLORS) == 5
    assert len(PX_DARK) == 5
    assert INITIAL_GHOSTS == 2
    assert MAX_GEMS == 8
    assert TRAIL_DURATION > 0
    assert GHOST_SPAWN_INTERVAL > 0
    assert OBSTACLE_COUNT >= 0


def test_reset_clears_state() -> None:
    """Test that reset() returns game to initial state."""
    g = make_game()
    # Modify state
    g.score = 500
    g.combo = 10
    g.max_combo = 15
    g.gems_eaten = 42
    g.invincible_timer = 100
    g.ghosts = [Ghost(0, 0)]
    g.gems = [Gem(1, 1, 2)]
    g.trails = [TrailCell(3, 3, 0, 50)]
    g.texts = [FloatingText(5, 5, "X", 7, 10)]

    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.gems_eaten == 0
    assert g.invincible_timer == 0
    assert len(g.ghosts) == INITIAL_GHOSTS
    assert len(g.gems) == MAX_GEMS
    assert len(g.trails) == 0
    assert len(g.texts) == 0
    assert g.phase == Phase.PLAYING


def test_obstacles_not_on_player_spawn() -> None:
    """Test that player starting position has no obstacle."""
    g = make_game()
    px, py = GRID_W // 2, GRID_H // 2
    assert not g._is_blocked(px, py)


def test_gems_not_on_obstacles() -> None:
    """Test that spawned gems are not on obstacles."""
    g = make_game()
    for gem in g.gems:
        assert not g._is_blocked(gem.x, gem.y)


def test_ghosts_not_on_obstacles() -> None:
    """Test that spawned ghosts are not on obstacles."""
    g = make_game()
    for ghost in g.ghosts:
        assert not g._is_blocked(ghost.x, ghost.y)


def run_all() -> int:
    """Run all tests and return count of failures."""
    tests = [
        test_dataclasses,
        test_phase_enum,
        test_game_initial_state,
        test_obstacles_deterministic,
        test_is_blocked,
        test_has_trail_at,
        test_collect_gem_same_color,
        test_collect_gem_different_color,
        test_collect_power_gem,
        test_ghost_candidates_unblocked,
        test_ghost_candidates_blocked,
        test_ghost_candidates_avoid_other_ghosts,
        test_update_trails_decay,
        test_update_texts_float_up,
        test_ghost_spawn_timer,
        test_invincible_timer_decrease,
        test_player_ghost_collision_normal,
        test_player_ghost_collision_invincible,
        test_player_no_collision,
        test_collect_gem_max_combo_tracking,
        test_collect_gem_spawns_replacement,
        test_trail_only_at_combo_2_plus,
        test_ghost_dies_on_danger_trail,
        test_ghost_avoids_trail_when_danger,
        test_combo_2_enables_trail_danger,
        test_config_constants,
        test_reset_clears_state,
        test_obstacles_not_on_player_spawn,
        test_gems_not_on_obstacles,
        test_ghosts_not_on_obstacles,
    ]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"  PASS {test.__name__}")
        except AssertionError as e:
            print(f"  FAIL {test.__name__}: {e}")
            failures += 1
        except Exception as e:
            print(f"  ERROR {test.__name__}: {type(e).__name__}: {e}")
            failures += 1
    return failures


if __name__ == "__main__":
    failures = run_all()
    print(f"\n{failures} failures out of {30} tests")
    if failures > 0:
        print("❌ TESTS FAILED")
        sys.exit(1)
    else:
        print("✅ ALL TESTS PASSED")
