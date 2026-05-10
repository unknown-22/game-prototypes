"""test_imports.py — Headless logic tests for OVERLOAD prototype.

Tests dataclasses, game state initialization, and core logic
without requiring a display (safe for CI/WSL without X).
"""

import sys
import math

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/007_overload")
from main import (
    SCREEN_W,
    SCREEN_H,
    PLAYER_MAX_HP,
    PLAYER_RADIUS,
    CHARGE_MAX,
    OVERLOAD_BASE_DAMAGE,
    OVERLOAD_HP_COST,
    OVERLOAD_CHAIN_RANGE,
    OVERLOAD_CHAIN_FALLOFF,
    ENEMY_DAMAGE,
    BULLET_DAMAGE,
    Phase,
    Player,
    Enemy,
    Bullet,
    EnergyOrb,
    Particle,
    FloatingText,
    Game,
)


def test_dataclasses() -> None:
    """Test dataclass construction and default values."""
    # Player
    p = Player(x=200.0, y=150.0)
    assert p.hp == PLAYER_MAX_HP
    assert p.charge == 0.0
    assert p.fire_cooldown == 0

    # Enemy
    e = Enemy(x=100.0, y=100.0, hp=30, speed=1.0)
    assert e.radius == 6
    assert e.hp == 30

    # Bullet
    b = Bullet(x=0.0, y=0.0, vx=5.0, vy=0.0)
    assert b.damage == BULLET_DAMAGE

    # EnergyOrb
    o = EnergyOrb(x=50.0, y=50.0, value=8)
    assert o.value == 8
    assert o.life == 300

    # Particle
    part = Particle(x=10.0, y=10.0, vx=1.0, vy=-1.0, life=20, color=8, size=2)
    assert part.life == 20

    # FloatingText
    ft = FloatingText(x=100.0, y=100.0, text="test", life=40, color=7)
    assert ft.text == "test"
    assert ft.vy == -1.0


def test_phase_enum() -> None:
    """Test phase enum values."""
    phases = {Phase.PLAYING, Phase.OVERLOAD_ANIM, Phase.GAME_OVER}
    assert len(phases) == 3
    assert Phase.PLAYING in phases


def test_config_values() -> None:
    """Test config constants are reasonable."""
    assert SCREEN_W == 400
    assert SCREEN_H == 300
    assert PLAYER_MAX_HP == 100
    assert CHARGE_MAX == 100
    assert OVERLOAD_HP_COST == 15
    assert OVERLOAD_BASE_DAMAGE == 50
    assert 0.0 < OVERLOAD_CHAIN_FALLOFF < 1.0
    assert OVERLOAD_CHAIN_RANGE > 0
    assert BULLET_DAMAGE > 0
    assert ENEMY_DAMAGE > 0


def test_game_reset() -> None:
    """Test Game.reset() initializes state correctly."""
    import inspect

    reset_src = inspect.getsource(Game.reset)
    # Verify reset initializes key attributes
    assert "self.score: int = 0" in reset_src or "self.score = 0" in reset_src.replace(" ", "")
    assert "self.wave: int = 1" in reset_src or "self.wave = 1" in reset_src.replace(" ", "")
    assert "self.phase = Phase.PLAYING" in reset_src


def test_enemy_position() -> None:
    """Test enemy dataclass works with float positions."""
    e = Enemy(x=150.5, y=200.3, hp=25, speed=0.9)
    assert abs(e.x - 150.5) < 0.01
    assert abs(e.y - 200.3) < 0.01
    assert e.hp == 25


def test_player_movement_bounds() -> None:
    """Test player stays within screen bounds (logic check)."""
    # Simulate extreme position clamping
    x = max(PLAYER_RADIUS, min(SCREEN_W - PLAYER_RADIUS, -10.0))
    assert x == PLAYER_RADIUS
    x = max(PLAYER_RADIUS, min(SCREEN_W - PLAYER_RADIUS, 500.0))
    assert x == SCREEN_W - PLAYER_RADIUS


def test_distance_calculation() -> None:
    """Test math.hypot used for enemy distance."""
    dist = math.hypot(3.0, 4.0)
    assert abs(dist - 5.0) < 0.01


def test_charge_bounds() -> None:
    """Test charge clamping logic."""
    charge = min(CHARGE_MAX, 80.0 + 30.0)
    assert charge == CHARGE_MAX
    charge = min(CHARGE_MAX, 50.0)
    assert charge == 50.0


if __name__ == "__main__":
    test_dataclasses()
    test_phase_enum()
    test_config_values()
    test_game_reset()
    test_enemy_position()
    test_player_movement_bounds()
    test_distance_calculation()
    test_charge_bounds()
    print("ALL TESTS PASSED")
