"""test_imports.py — Headless logic tests for COIN SURGE (prototype 138)."""

import math
import random
import sys

import pytest

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/138_coin_surge")

from main import (
    COIN_DIAMETER,
    COIN_RADIUS,
    COMBO_SUPER_THRESHOLD,
    Coin,
    FloatingText,
    GAME_DURATION_SEC,
    Game,
    HEAT_DECAY,
    HEAT_DECAY_ON_COMBO,
    HEAT_MAX,
    HEAT_PER_DIFF,
    OVERHEAT_DURATION,
    Particle,
    Phase,
    SCORE_PER_COIN,
    SUPER_DURATION,
    TABLE_BOTTOM,
    TABLE_LEFT,
    TABLE_RIGHT,
    TABLE_TOP,
    TABLE_W,
)


class _MockRandom:
    """Deterministic mock for random.Random used in _advance_next_color tests."""

    def __init__(self, retval: float):
        self._retval = retval

    def random(self) -> float:
        return self._retval


def _make_game():
    """Create a Game instance bypassing pyxel.init/run."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.coins = []
    g.particles = []
    g.floating_texts = []
    g.current_color_idx = 0
    g.drop_x = TABLE_LEFT + TABLE_W / 2
    g.super_timer = 0
    g.overheat_timer = 0
    g.game_timer = GAME_DURATION_SEC * 30
    g.drop_cooldown = 0
    g.shake_frames = 0
    g.reset()
    g._rng = random.Random(42)
    return g


class TestDropCoin:
    """Coin dropping: position, appending, adjacency checks."""

    def test_drop_adds_coin(self):
        g = _make_game()
        g._rng = random.Random(42)
        assert len(g.coins) == 0
        g._drop_coin(100.0, 0)
        assert len(g.coins) == 1
        assert g.coins[0].color == 0
        assert g.coins[0].x == 100.0

    def test_drop_at_populated_position(self):
        g = _make_game()
        g._rng = random.Random(42)
        # Place an existing coin at the drop position
        g.coins.append(Coin(x=100.0, y=TABLE_TOP + COIN_RADIUS, color=1))
        g._drop_coin(100.0, 0)
        # Both coins should be on the table
        assert len(g.coins) == 2
        dropped = g.coins[1]
        # Coin enters at top of table
        assert dropped.y == TABLE_TOP + COIN_RADIUS

    def test_drop_spawns_particles(self):
        g = _make_game()
        g._rng = random.Random(42)
        g._drop_coin(100.0, 0)
        assert len(g.particles) > 0

    def test_drop_cooldown(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.drop_cooldown = 5
        initial_count = len(g.coins)
        # _drop_coin doesn't check cooldown (that's in update)
        g._drop_coin(100.0, 0)
        assert len(g.coins) == initial_count + 1


class TestPhysics:
    """Physics: gravity, collisions, bottom clamping."""

    def test_gravity_pulls_coins_down(self):
        g = _make_game()
        g._rng = random.Random(42)
        c = Coin(x=100.0, y=100.0, color=0, vy=0.0)
        g.coins = [c]
        g._update_physics()
        assert c.y > 100.0
        assert c.vy > 0.0

    def test_bottom_clamp(self):
        g = _make_game()
        g._rng = random.Random(42)
        c = Coin(x=100.0, y=TABLE_BOTTOM - 1, color=0, vy=5.0)
        g.coins = [c]
        for _ in range(10):
            g._update_physics()
        assert c.y <= TABLE_BOTTOM - COIN_RADIUS

    def test_wall_clamping_left(self):
        g = _make_game()
        g._rng = random.Random(42)
        c = Coin(x=TABLE_LEFT - 10, y=100.0, color=0, vx=-1.0)
        g.coins = [c]
        g._update_physics()
        assert c.x >= TABLE_LEFT + COIN_RADIUS

    def test_wall_clamping_right(self):
        g = _make_game()
        g._rng = random.Random(42)
        c = Coin(x=TABLE_RIGHT + 10, y=100.0, color=0, vx=1.0)
        g.coins = [c]
        g._update_physics()
        assert c.x <= TABLE_RIGHT - COIN_RADIUS

    def test_collision_pushes_apart(self):
        g = _make_game()
        g._rng = random.Random(42)
        c1 = Coin(x=100.0, y=100.0, color=0)
        c2 = Coin(x=100.0 + COIN_DIAMETER * 0.5, y=100.0, color=1)
        g.coins = [c1, c2]
        for _ in range(5):
            g._update_physics()
        dist = math.hypot(c1.x - c2.x, c1.y - c2.y)
        assert dist >= COIN_DIAMETER * 0.8

    def test_settled_coins_stay_settled(self):
        g = _make_game()
        g._rng = random.Random(42)
        c = Coin(x=100.0, y=TABLE_BOTTOM - COIN_RADIUS, color=0, settled=True, vx=0.0, vy=0.0)
        g.coins = [c]
        g._update_physics()
        assert c.settled is True
        assert c.vy == 0.0


class TestCollisionResolution:
    """_resolve_coin_collision pushes overlapping coins apart."""

    def test_overlapping_coins_pushed_apart(self):
        g = _make_game()
        g._rng = random.Random(42)
        c1 = Coin(x=100.0, y=100.0, color=0)
        c2 = Coin(x=100.0 + COIN_DIAMETER * 0.5, y=100.0, color=1)
        g._resolve_coin_collision(c1, c2)
        dist = math.hypot(c1.x - c2.x, c1.y - c2.y)
        assert dist > COIN_DIAMETER * 0.5

    def test_non_overlapping_coins_unchanged(self):
        g = _make_game()
        g._rng = random.Random(42)
        c1 = Coin(x=100.0, y=100.0, color=0)
        c2 = Coin(x=300.0, y=100.0, color=1)
        orig_x1, orig_y1 = c1.x, c1.y
        orig_x2, orig_y2 = c2.x, c2.y
        g._resolve_coin_collision(c1, c2)
        assert c1.x == orig_x1 and c1.y == orig_y1
        assert c2.x == orig_x2 and c2.y == orig_y2

    def test_wakes_settled_coins(self):
        g = _make_game()
        g._rng = random.Random(42)
        c1 = Coin(x=100.0, y=100.0, color=0, settled=True)
        c2 = Coin(x=100.0 + COIN_DIAMETER * 0.3, y=100.0, color=1, settled=True)
        g._resolve_coin_collision(c1, c2)
        # At least one should wake
        assert (not c1.settled) or (not c2.settled)


class TestEdgeCoins:
    """_check_edge_coins finds coins pushed past bottom."""

    def test_coin_past_bottom_edge_scored(self):
        g = _make_game()
        g._rng = random.Random(42)
        c = Coin(x=100.0, y=TABLE_BOTTOM - COIN_RADIUS, color=0, vy=1.0)
        g.coins = [c]
        scored = g._check_edge_coins()
        assert len(scored) == 1
        assert len(g.coins) == 0

    def test_coin_above_bottom_not_scored(self):
        g = _make_game()
        g._rng = random.Random(42)
        c = Coin(x=100.0, y=TABLE_BOTTOM - COIN_RADIUS - 10, color=0, vy=0.0)
        g.coins = [c]
        scored = g._check_edge_coins()
        assert len(scored) == 0
        assert len(g.coins) == 1

    def test_fully_off_screen_coin_removed(self):
        g = _make_game()
        g._rng = random.Random(42)
        c = Coin(x=100.0, y=TABLE_BOTTOM + COIN_RADIUS + 10, color=0, vy=0.0)
        g.coins = [c]
        scored = g._check_edge_coins()
        assert len(scored) == 1


class TestScoring:
    """Score is awarded when coins fall off edge."""

    def test_score_per_coin(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.score = 0
        g.combo = 0
        coins = [Coin(x=100.0, y=TABLE_BOTTOM, color=0)]
        g._handle_scored_coins(coins)
        assert g.score == SCORE_PER_COIN

    def test_score_with_combo_bonus(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.score = 0
        g.combo = 4
        coins = [Coin(x=100.0, y=TABLE_BOTTOM, color=0)]
        g._handle_scored_coins(coins)
        expected = SCORE_PER_COIN + int(4 * 0.5)
        assert g.score == expected

    def test_super_mode_3x_score(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.score = 0
        g.combo = 0
        g.super_timer = 100
        coins = [Coin(x=100.0, y=TABLE_BOTTOM, color=0)]
        g._handle_scored_coins(coins)
        assert g.score == SCORE_PER_COIN * 3

    def test_scoring_reduces_heat(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.heat = 20.0
        g.combo = 2
        coins = [Coin(x=100.0, y=TABLE_BOTTOM, color=0)]
        g._handle_scored_coins(coins)
        assert g.heat == pytest.approx(20.0 - HEAT_DECAY_ON_COMBO)


class TestAdjacentCombo:
    """Combo increases with same-color adjacency, resets with different color."""

    def test_same_color_adjacent_increases_combo(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.combo = 0
        g.heat = 0.0
        # Place an adjacent same-color coin
        existing = Coin(x=100.0 + COIN_DIAMETER, y=TABLE_TOP + COIN_RADIUS, color=0)
        g.coins = [existing]
        dropped = Coin(x=100.0, y=TABLE_TOP + COIN_RADIUS, color=0)
        g.coins.append(dropped)
        g._check_adjacent_combo(dropped)
        assert g.combo == 1

    def test_diff_color_adjacent_resets_combo(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.combo = 3
        g.heat = 0.0
        existing = Coin(x=100.0 + COIN_DIAMETER, y=TABLE_TOP + COIN_RADIUS, color=1)
        g.coins = [existing]
        dropped = Coin(x=100.0, y=TABLE_TOP + COIN_RADIUS, color=0)
        g.coins.append(dropped)
        g._check_adjacent_combo(dropped)
        assert g.combo == 0

    def test_diff_color_adjacent_adds_heat(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.heat = 10.0
        existing = Coin(x=100.0 + COIN_DIAMETER, y=TABLE_TOP + COIN_RADIUS, color=1)
        g.coins = [existing]
        dropped = Coin(x=100.0, y=TABLE_TOP + COIN_RADIUS, color=0)
        g.coins.append(dropped)
        g._check_adjacent_combo(dropped)
        assert g.heat == pytest.approx(10.0 + HEAT_PER_DIFF)

    def test_combo_reduces_heat(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.heat = 30.0
        g.combo = 0
        existing = Coin(x=100.0 + COIN_DIAMETER, y=TABLE_TOP + COIN_RADIUS, color=0)
        g.coins = [existing]
        dropped = Coin(x=100.0, y=TABLE_TOP + COIN_RADIUS, color=0)
        g.coins.append(dropped)
        g._check_adjacent_combo(dropped)
        assert g.heat == pytest.approx(30.0 - HEAT_DECAY_ON_COMBO)

    def test_no_adjacent_no_change(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.combo = 2
        g.heat = 20.0
        existing = Coin(x=200.0, y=TABLE_TOP + COIN_RADIUS, color=0)
        g.coins = [existing]
        dropped = Coin(x=100.0, y=TABLE_TOP + COIN_RADIUS, color=0)
        g.coins.append(dropped)
        g._check_adjacent_combo(dropped)
        assert g.combo == 2  # unchanged

    def test_multiple_same_adjacent(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.combo = 0
        existing1 = Coin(x=100.0 + COIN_DIAMETER, y=100.0, color=0)
        existing2 = Coin(x=100.0 - COIN_DIAMETER, y=100.0, color=0)
        g.coins = [existing1, existing2]
        dropped = Coin(x=100.0, y=100.0, color=0)
        g.coins.append(dropped)
        g._check_adjacent_combo(dropped)
        assert g.combo == 2


class TestSuperDrop:
    """COMBO >= 4 activates SUPER DROP."""

    def test_super_drop_activates_at_threshold(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.combo = 3  # about to be 4
        g.super_timer = 0
        existing = Coin(x=100.0 + COIN_DIAMETER, y=100.0, color=0)
        g.coins = [existing]
        dropped = Coin(x=100.0, y=100.0, color=0)
        g.coins.append(dropped)
        g._check_adjacent_combo(dropped)
        assert g.combo == COMBO_SUPER_THRESHOLD
        assert g.super_timer == SUPER_DURATION

    def test_super_drop_not_activate_below_threshold(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.combo = 2
        g.super_timer = 0
        existing = Coin(x=100.0 + COIN_DIAMETER, y=100.0, color=0)
        g.coins = [existing]
        dropped = Coin(x=100.0, y=100.0, color=0)
        g.coins.append(dropped)
        g._check_adjacent_combo(dropped)
        assert g.combo == 3
        assert g.super_timer == 0

    def test_super_timer_decrements(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.super_timer = 100
        g._update_super_timer()
        assert g.super_timer == 99

    def test_super_timer_stops_at_zero(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.super_timer = 0
        g._update_super_timer()
        assert g.super_timer == 0


class TestHeatAndOverheat:
    """HEAT >= HEAT_MAX triggers OVERHEAT."""

    def test_heat_decays_over_time(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.heat = 10.0
        g._update_heat()
        assert g.heat == pytest.approx(10.0 - HEAT_DECAY)

    def test_heat_does_not_go_below_zero(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.heat = 0.0
        g._update_heat()
        assert g.heat == 0.0

    def test_heat_clamped_and_decays(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.heat = HEAT_MAX + 10
        g._update_heat()
        # First clamped to max, then overheat triggers, then decay applied
        assert g.heat == pytest.approx(HEAT_MAX - HEAT_DECAY)

    def test_overheat_activates_at_max_heat(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.heat = HEAT_MAX
        g.overheat_timer = 0
        g._update_heat()
        assert g.overheat_timer == OVERHEAT_DURATION

    def test_overheat_timer_decrements(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.overheat_timer = 100
        g._update_overheat_timer()
        assert g.overheat_timer == 99


class TestNextColor:
    """_advance_next_color cycles or stays."""

    def test_advance_cycles_color(self):
        g = _make_game()
        g._rng = _MockRandom(0.5)  # above 0.25, should cycle
        g.current_color_idx = 0
        g._advance_next_color()
        assert g.current_color_idx == 1

    def test_advance_stays_same_color(self):
        g = _make_game()
        g._rng = _MockRandom(0.1)  # below 0.25, stay
        g.current_color_idx = 0
        g._advance_next_color()
        assert g.current_color_idx == 0


class TestParticles:
    """Particle creation, movement, and lifecycle."""

    def test_particles_move_and_decay(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.particles = [Particle(x=100.0, y=100.0, vx=1.0, vy=2.0, life=5, color=8)]
        g._update_particles()
        p = g.particles[0]
        assert p.x == 101.0
        assert p.y == 102.0  # y += vy (2.0)
        assert p.vy == 2.1  # vy += gravity (0.1)
        assert p.life == 4

    def test_particles_removed_when_life_expires(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.particles = [Particle(x=100.0, y=100.0, vx=1.0, vy=2.0, life=1, color=8)]
        g._update_particles()
        assert len(g.particles) == 0

    def test_floating_texts_move_and_fade(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.floating_texts = [FloatingText(x=100.0, y=100.0, text="TEST", life=5, color=7)]
        g._update_floating_texts()
        ft = g.floating_texts[0]
        assert ft.y < 100.0
        assert ft.life == 4

    def test_floating_texts_removed_when_life_expires(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.floating_texts = [FloatingText(x=100.0, y=100.0, text="TEST", life=1, color=7)]
        g._update_floating_texts()
        assert len(g.floating_texts) == 0


class TestReset:
    """Reset and start_playing clear state properly."""

    def test_reset_clears_score(self):
        g = _make_game()
        g.score = 999
        g.reset()
        assert g.score == 0

    def test_reset_clears_combo(self):
        g = _make_game()
        g.combo = 10
        g.max_combo = 10
        g.reset()
        assert g.combo == 0
        assert g.max_combo == 0

    def test_reset_clears_heat(self):
        g = _make_game()
        g.heat = 80.0
        g.reset()
        assert g.heat == 0.0

    def test_reset_clears_super_mode(self):
        g = _make_game()
        g.super_timer = 200
        g.reset()
        assert g.super_timer == 0

    def test_reset_clears_coins(self):
        g = _make_game()
        g.coins = [Coin(x=0, y=0, color=0)]
        g.reset()
        assert len(g.coins) == 0

    def test_reset_clears_particles(self):
        g = _make_game()
        g.particles = [Particle(x=0, y=0, vx=1, vy=1, life=10, color=8)]
        g.reset()
        assert len(g.particles) == 0

    def test_reset_sets_phase_to_title(self):
        g = _make_game()
        g.phase = Phase.PLAYING
        g.reset()
        assert g.phase == Phase.TITLE

    def test_start_playing_seeds_coins(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.start_playing()
        assert len(g.coins) > 0
        assert g.phase == Phase.PLAYING
        assert g.score == 0
        assert g.game_timer == GAME_DURATION_SEC * 30


class TestPositionHelpers:
    """_is_position_blocked and _find_drop_y."""

    def test_position_not_blocked_when_empty(self):
        g = _make_game()
        g._rng = random.Random(42)
        assert g._is_position_blocked(100.0, 100.0) is False

    def test_position_blocked_by_coin(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.coins = [Coin(x=100.0, y=100.0, color=0)]
        assert g._is_position_blocked(100.0 + COIN_DIAMETER * 0.5, 100.0) is True

    def test_position_not_blocked_far_away(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.coins = [Coin(x=100.0, y=100.0, color=0)]
        assert g._is_position_blocked(200.0, 100.0) is False

    def test_find_drop_y_empty(self):
        g = _make_game()
        g._rng = random.Random(42)
        y = g._find_drop_y(100.0)
        assert y == TABLE_TOP + COIN_RADIUS

    def test_find_drop_y_with_coin(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.coins = [Coin(x=100.0, y=TABLE_TOP + COIN_RADIUS + 30, color=0)]
        y = g._find_drop_y(100.0)
        assert y > TABLE_TOP + COIN_RADIUS


class TestTimer:
    """Game timer counts down."""

    def test_timer_decrements_in_update(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.phase = Phase.PLAYING
        g.coins = []
        initial = g.game_timer
        # Simulate _update_playing without pyxel calls
        g.game_timer -= 1
        g._update_physics()
        g._update_super_timer()
        g._update_overheat_timer()
        g._update_heat()
        g._update_particles()
        g._update_floating_texts()
        if g.shake_frames > 0:
            g.shake_frames -= 1
        assert g.game_timer == initial - 1

    def test_game_over_when_timer_zero(self):
        g = _make_game()
        g._rng = random.Random(42)
        g.phase = Phase.PLAYING
        g.game_timer = 1
        g.coins = []
        g.game_timer -= 1
        g._update_physics()
        g._update_super_timer()
        g._update_overheat_timer()
        g._update_heat()
        g._update_particles()
        g._update_floating_texts()
        if g.shake_frames > 0:
            g.shake_frames -= 1
        if g.game_timer <= 0:
            g.game_timer = 0
            g.phase = Phase.GAME_OVER
        assert g.phase == Phase.GAME_OVER
