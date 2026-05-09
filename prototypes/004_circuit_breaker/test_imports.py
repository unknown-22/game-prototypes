"""Headless import tests for Circuit Breaker prototype."""
import sys

# Add prototype directory to path
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/004_circuit_breaker")

from main import Card, CardDef, CardType, CARD_DEFS, Phase, Particle, App


def test_card_definitions():
    assert len(CARD_DEFS) == 5
    for ct, defn in CARD_DEFS.items():
        assert isinstance(defn, CardDef)
        assert len(defn.abbr) == 3
        assert defn.threshold >= 2
        assert 0 <= defn.color <= 15
    print(f"  OK: {len(CARD_DEFS)} card definitions")


def test_card_instance():
    card = Card(CardType.VIRUS)
    assert card.defn == CARD_DEFS[CardType.VIRUS]
    assert card.defn.abbr == "VRS"
    print("  OK: Card instance")


def test_phase_enum():
    assert len(Phase) == 5
    for p in (Phase.DRAW, Phase.PLAYER_TURN, Phase.ENEMY_TURN, Phase.VICTORY, Phase.DEFEAT):
        assert p in Phase
    print("  OK: Phase enum")


def test_particle():
    p = Particle(10.0, 20.0, 1.0, -2.0, 24, 8)
    assert p.life == 24
    assert p.size == 2
    print("  OK: Particle dataclass")


def test_deck():
    deck_size = len(CardType) * App.COPIES_PER_TYPE
    assert deck_size == 15, f"Expected 15, got {deck_size}"
    print("  OK: Deck composition (15 cards)")


if __name__ == "__main__":
    print("=== Headless Tests ===\n")
    test_card_definitions()
    test_card_instance()
    test_phase_enum()
    test_particle()
    test_deck()
    print("\n=== ALL PASSED ===")
