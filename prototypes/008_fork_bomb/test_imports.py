"""test_imports.py — Headless logic tests for Fork Bomb.

Validates that all classes, enums, and dataclasses import correctly
and that core game logic functions without a display.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add prototype directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # noqa: E402
    ENEMY_BASE_DMG,
    ENEMY_BASE_HP,
    MAX_RISK,
    MAX_TURN,
    PLAYER_BASE_HP,
    RISK_DECAY,
    SPLIT_RISK_COST,
    Die,
    ForkBomb,
    Particle,
    Phase,
)

# ── Test enums ──


def test_phases() -> None:
    """Verify all Phase enum members exist."""
    phases = list(Phase)
    assert len(phases) == 6
    assert Phase.ROLL in Phase
    assert Phase.ROUTE in Phase
    assert Phase.FIRE in Phase
    assert Phase.RESOLVE in Phase
    assert Phase.VICTORY in Phase
    assert Phase.DEFEAT in Phase


# ── Test dataclasses ──


def test_die_defaults() -> None:
    """Verify Die dataclass default values."""
    d = Die(value=5)
    assert d.value == 5
    assert d.lane == -1
    assert d.split_from == -1


def test_die_placed() -> None:
    """Verify Die with explicit lane placement."""
    d = Die(value=3, lane=1)
    assert d.value == 3
    assert d.lane == 1


def test_particle() -> None:
    """Verify Particle dataclass construction and field access."""
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=30, color=10, text="42")
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.life == 30
    assert p.color == 10
    assert p.text == "42"


def test_particle_default_text() -> None:
    """Verify Particle default text is empty string."""
    p = Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=7)
    assert p.text == ""


# ── Test constants ──


def test_constants() -> None:
    """Verify game constants are within expected ranges."""
    assert MAX_RISK == 10
    assert MAX_TURN == 12
    assert PLAYER_BASE_HP == 100
    assert ENEMY_BASE_HP == 150
    assert ENEMY_BASE_DMG == 6
    assert RISK_DECAY == 1
    assert SPLIT_RISK_COST == 2


# ── Test game class instantiation (no pyxel.run) ──


def test_fork_bomb_reset_state() -> None:
    """Verify ForkBomb.reset() initializes state correctly without display."""
    game = ForkBomb.__new__(ForkBomb)
    game.reset()
    assert game.phase == Phase.ROLL
    assert game.turn == 1
    assert game.hp == PLAYER_BASE_HP
    assert game.enemy_hp == ENEMY_BASE_HP
    assert game.risk == 0
    assert game.combo == 0
    assert game.max_combo == 0
    assert game.score == 0
    assert len(game.dice) == 4
    assert game.lanes == [None, None, None]
    assert game.selected_die == -1


# ── Test damage calculation ──


def test_calculate_damage_no_lanes() -> None:
    """Damage with empty lanes should be 0."""
    game = ForkBomb.__new__(ForkBomb)
    game.lanes = [None, None, None]
    base, final, msg = game._calculate_damage()
    assert base == 0
    assert final == 0
    assert msg == ""


def test_calculate_damage_no_recombine() -> None:
    """Damage with different values on adjacent lanes: no recombine."""
    game = ForkBomb.__new__(ForkBomb)
    game.lanes = [Die(value=3, lane=0), Die(value=5, lane=1), Die(value=2, lane=2)]
    base, final, msg = game._calculate_damage()
    assert base == 10  # 3+5+2
    assert final == 10  # no multiplier
    assert msg == ""


def test_calculate_damage_single_recombine() -> None:
    """Two adjacent lanes with same value: 2x recombine."""
    game = ForkBomb.__new__(ForkBomb)
    game.lanes = [Die(value=4, lane=0), Die(value=4, lane=1), Die(value=2, lane=2)]
    base, final, msg = game._calculate_damage()
    assert base == 10  # 4+4+2
    assert final == 20  # x2 multiplier
    assert msg == "RECOMBINE x2!"


def test_calculate_damage_triple_recombine() -> None:
    """All 3 lanes same value: 4x triple recombine."""
    game = ForkBomb.__new__(ForkBomb)
    game.lanes = [Die(value=6, lane=0), Die(value=6, lane=1), Die(value=6, lane=2)]
    base, final, msg = game._calculate_damage()
    assert base == 18  # 6+6+6
    assert final == 72  # x4 multiplier
    assert msg == "TRIPLE RECOMBINE x4!"


def test_calculate_damage_two_pairs() -> None:
    """Three lanes: 0-1 match AND 1-2 match = two recombines = x4."""
    game = ForkBomb.__new__(ForkBomb)
    game.lanes = [Die(value=3, lane=0), Die(value=3, lane=1), Die(value=3, lane=2)]
    base, final, msg = game._calculate_damage()
    assert base == 9
    assert final == 36  # x4
    assert msg == "TRIPLE RECOMBINE x4!"


def test_calculate_damage_zero_value_skip() -> None:
    """Zero-value lanes should not trigger recombines."""
    game = ForkBomb.__new__(ForkBomb)
    d0 = Die(value=0, lane=0)
    d1 = Die(value=0, lane=1)
    d2 = Die(value=5, lane=2)
    game.lanes = [d0, d1, d2]
    base, final, msg = game._calculate_damage()
    assert base == 5
    assert final == 5
    assert msg == ""


# ── Test split logic ──


def test_split_die_creates_halves() -> None:
    """Splitting a die should create two half-value dice on adjacent lanes."""
    game = ForkBomb.__new__(ForkBomb)
    game.reset()
    # Manually place a die on lane 1 (middle)
    d = Die(value=6, lane=1)
    game.lanes = [None, d, None]
    initial_risk = game.risk
    initial_dice_count = len(game.dice)

    game._split_die(1)

    # Risk should increase
    assert game.risk == initial_risk + SPLIT_RISK_COST
    # Original die consumed
    assert d.value == 0
    assert d.lane == -1
    # New dice created (2 halves)
    assert len(game.dice) == initial_dice_count + 2
    # Lanes 0 and 2 should be filled with halves
    assert game.lanes[0] is not None
    assert game.lanes[2] is not None
    lane_vals = [
        game.lanes[0].value if game.lanes[0] else 0,
        game.lanes[2].value if game.lanes[2] else 0,
    ]
    assert sum(lane_vals) == 6  # original value preserved


def test_split_die_on_edge_lane() -> None:
    """Splitting a die on lane 0 should only fill lane 1."""
    game = ForkBomb.__new__(ForkBomb)
    game.reset()
    d = Die(value=7, lane=0)
    game.lanes = [d, None, None]

    game._split_die(0)

    # Only lane 1 should be filled (lane -1 doesn't exist)
    assert game.lanes[1] is not None
    assert game.lanes[2] is None
    lane_vals = [game.lanes[1].value if game.lanes[1] else 0]
    # Half of 7 = 3, remaining = 4 (or vice versa)
    assert 3 <= sum(lane_vals) <= 4  # only one lane filled since only one adjacent


def test_split_die_value_one_does_nothing() -> None:
    """Splitting a die with value 1 should do nothing (too small)."""
    game = ForkBomb.__new__(ForkBomb)
    game.reset()
    d = Die(value=1, lane=1)
    game.lanes = [None, d, None]
    initial_risk = game.risk
    initial_dice_count = len(game.dice)

    game._split_die(1)

    # Nothing should change
    assert game.risk == initial_risk
    assert len(game.dice) == initial_dice_count
    assert game.lanes[1] is d


def test_split_no_empty_adjacent() -> None:
    """Splitting with both adjacent lanes full should do nothing."""
    game = ForkBomb.__new__(ForkBomb)
    game.reset()
    game.lanes = [Die(value=4, lane=0), Die(value=6, lane=1), Die(value=3, lane=2)]
    initial_risk = game.risk

    game._split_die(1)

    assert game.risk == initial_risk


# ── Test floating point resilience ──

def test_particle_position_float() -> None:
    """Particle positions should handle floating point values."""
    p = Particle(x=100.1, y=200.7, vx=0.5, vy=-0.3, life=15, color=7)
    # Move particle
    p.x += p.vx
    p.y += p.vy
    # Use tolerance for float comparison
    assert abs(p.x - 100.6) < 0.01
    assert abs(p.y - 200.4) < 0.01


# ── Run all tests ──

if __name__ == "__main__":
    test_phases()
    test_die_defaults()
    test_die_placed()
    test_particle()
    test_particle_default_text()
    test_constants()
    test_fork_bomb_reset_state()
    test_calculate_damage_no_lanes()
    test_calculate_damage_no_recombine()
    test_calculate_damage_single_recombine()
    test_calculate_damage_triple_recombine()
    test_calculate_damage_two_pairs()
    test_calculate_damage_zero_value_skip()
    test_split_die_creates_halves()
    test_split_die_on_edge_lane()
    test_split_die_value_one_does_nothing()
    test_split_no_empty_adjacent()
    test_particle_position_float()
    print("All 18 tests passed!")
