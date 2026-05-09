"""test_imports.py — Headless logic tests for Power Grid.

Tests dataclasses, card definitions, and game logic without running Pyxel.
"""

import sys
import os

# Add prototype directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import (
    CardType, CardDef, CARD_DEFS, Generator, Particle, Phase, PowerGrid,
    SCREEN_W, SCREEN_H, MAX_TURNS, CARDS_PER_TURN, MAX_HEAT,
)


def test_card_definitions() -> None:
    """Verify all card types have valid definitions."""
    assert len(CARD_DEFS) == len(CardType), \
        f"Expected {len(CardType)} card defs, got {len(CARD_DEFS)}"
    for ct, cdef in CARD_DEFS.items():
        assert isinstance(cdef.name, str) and len(cdef.name) > 0
        assert isinstance(cdef.abbr, str) and len(cdef.abbr) == 3
        assert isinstance(cdef.power, int)
        assert isinstance(cdef.heat, int)
        assert isinstance(cdef.cool, int)
        assert isinstance(cdef.mult_bonus, float)
        assert isinstance(cdef.description, str)

    # Verify specific cards
    fuel = CARD_DEFS[CardType.FUEL]
    assert fuel.power == 15 and fuel.heat == 25

    coolant = CARD_DEFS[CardType.COOLANT]
    assert coolant.cool == 30

    vent = CARD_DEFS[CardType.VENT]
    assert vent.heat == -5  # cools all generators by 5


def test_generator_heat() -> None:
    """Test generator heat and overload mechanics."""
    gen = Generator("Test", 0, 0, base_output=10, overload_threshold=100)

    assert gen.output == 10
    assert gen.heat == 0
    assert gen.heat_ratio == 0.0
    assert not gen.overloaded

    # Add safe amount of heat
    triggered = gen.add_heat(50)
    assert not triggered
    assert gen.heat == 50
    assert gen.heat_ratio == 0.5

    # Add heat to trigger overload
    triggered = gen.add_heat(60)
    assert triggered
    assert gen.overloaded
    assert gen.overload_timer == 15

    # Tick overload
    for _ in range(15):
        gen.tick_overload()
    assert not gen.overloaded
    assert gen.heat == 0


def test_generator_output_mult() -> None:
    """Test output multiplier affects power."""
    gen = Generator("Test", 0, 0, base_output=10)
    assert gen.output == 10
    gen.output_mult = 1.5
    assert gen.output == 15
    gen.output_mult = 0.5
    assert gen.output == 5


def test_particle_physics() -> None:
    """Test particle dataclass and basic simulation."""
    p = Particle(x=100, y=200, vx=1.5, vy=-2.0, life=20, color=10, size=3)
    assert p.x == 100
    assert p.y == 200
    assert p.life == 20

    # Simulate movement
    p.x += p.vx
    p.y += p.vy
    p.vy += 0.1  # gravity
    p.life -= 1

    assert p.x == 101.5
    assert abs(p.y - 198.0) < 0.01  # 200 + (-2.0); gravity affects next frame
    assert p.life == 19


def test_phases() -> None:
    """Test all phase enum values exist."""
    phases = list(Phase)
    assert Phase.DRAW in phases
    assert Phase.PLAY in phases
    assert Phase.RESOLVE in phases
    assert Phase.OVERLOAD_CHAIN in phases
    assert Phase.DEMAND_CHECK in phases
    assert Phase.TURN_END in phases
    assert Phase.VICTORY in phases
    assert Phase.DEFEAT in phases
    assert len(phases) == 8


def test_game_init_reset() -> None:
    """Test PowerGrid initialization and reset (without pyxel.run)."""
    # Can't call PowerGrid() because it runs pyxel.run(),
    # but we can verify the class structure and constants
    assert hasattr(PowerGrid, 'reset')
    assert hasattr(PowerGrid, 'update')
    assert hasattr(PowerGrid, 'draw')

    # Test game logic via direct state construction
    import inspect
    reset_src = inspect.getsource(PowerGrid.reset)
    assert "self.phase = Phase.DRAW" in reset_src
    assert "self.turn = 1" in reset_src
    assert "self.score = 0" in reset_src
    assert "self.hp = 100" in reset_src
    assert "self.generators" in reset_src
    assert "len(self.generators)" not in reset_src  # 3 generators hardcoded
    assert "Reactor A" in reset_src
    assert "Turbine B" in reset_src
    assert "Solar C" in reset_src
    assert "self._deal_cards()" in reset_src


def test_constants() -> None:
    """Test game constants are sensible."""
    assert SCREEN_W == 400
    assert SCREEN_H == 300
    assert MAX_TURNS == 12
    assert CARDS_PER_TURN == 4
    assert MAX_HEAT == 100


def test_card_deck_building() -> None:
    """Test card pool construction via class inspection."""
    import inspect
    draw_src = inspect.getsource(PowerGrid._deal_cards)
    assert "FUEL" in draw_src
    assert "COOLANT" in draw_src
    assert "random.shuffle" in draw_src
    # Should draw CARDS_PER_TURN cards
    assert "CARDS_PER_TURN" in draw_src


def test_overload_chain_logic() -> None:
    """Test overload chain method exists and handles adjacency."""
    import inspect
    chain_src = inspect.getsource(PowerGrid._start_overload_chain)
    assert "self.chain_count" in chain_src
    assert "self.phase = Phase.OVERLOAD_CHAIN" in chain_src
    assert "abs(i - gen_idx) == 1" in chain_src  # adjacent check
    assert "chain_heat = 40" in chain_src


if __name__ == "__main__":
    test_card_definitions()
    test_generator_heat()
    test_generator_output_mult()
    test_particle_physics()
    test_phases()
    test_game_init_reset()
    test_constants()
    test_card_deck_building()
    test_overload_chain_logic()
    print("All headless tests passed!")
