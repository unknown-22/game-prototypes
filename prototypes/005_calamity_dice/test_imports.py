"""test_imports.py — Headless logic tests for Calamity Dice."""
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/005_calamity_dice")

# Import without triggering pyxel.run
from main import (
    CalamityDice, Phase, Die, Particle, Message,
    ELEMENTS, ELEM_NAMES, ELEM_COLORS, ELEM_DARK,
    HEAT_BASE, HEAT_PER_DIE, HEAT_COOL, HEAT_WARN, HEAT_DANGER, HEAT_DAMAGE,
    BASE_DICE, MAX_DICE, MAX_LOG, DAMAGE_PER_PIP,
    ENEMY_WAVES, W, H,
)

# ── Config tests ───────────────────────────────────────────────────────────
assert ELEMENTS == 5
assert len(ELEM_NAMES) == 5
assert len(ELEM_COLORS) == 5
assert len(ELEM_DARK) == 5
assert all(0 <= c <= 15 for c in ELEM_COLORS)
assert all(0 <= c <= 15 for c in ELEM_DARK)
assert HEAT_BASE == 3
assert HEAT_PER_DIE == 5
assert HEAT_COOL == 15
assert HEAT_WARN == 70
assert HEAT_DANGER == 90
assert HEAT_DAMAGE == 4
assert BASE_DICE == 3
assert MAX_DICE == 7
assert MAX_LOG == 4
assert DAMAGE_PER_PIP == 2
assert W == 400
assert H == 300

# ── Dataclass tests ─────────────────────────────────────────────────────────
# Die
d = Die(element=0, value=3)
assert d.element == 0
assert d.value == 3
assert d.active is False
assert d.elem_name == "FIRE"
assert d.color == ELEM_DARK[0]
d.active = True
assert d.color == ELEM_COLORS[0]

# Particle
p = Particle(x=100, y=50, vy=-1.0, text="5", color=8)
assert p.alive is True
assert p.timer == 0
p.timer = 30
assert p.alive is False

# Message
m = Message(text="HELLO", color=7)
assert m.alive is True
assert m.timer == 0
m.timer = 100
assert m.alive is False

# ── Phase enum tests ────────────────────────────────────────────────────────
phases = list(Phase)
assert len(phases) == 7
assert Phase.ROLL in phases
assert Phase.SELECT in phases
assert Phase.ANIMATE in phases
assert Phase.ENEMY_TURN in phases
assert Phase.CHECK in phases
assert Phase.VICTORY in phases
assert Phase.DEFEAT in phases

# ── Enemy waves tests ───────────────────────────────────────────────────────
assert len(ENEMY_WAVES) == 3
for wave in ENEMY_WAVES:
    assert "name" in wave
    assert "hp" in wave
    assert "atk" in wave
    assert "color" in wave
    assert wave["hp"] > 0
    assert wave["atk"] > 0

# ── Game state initialization (without pyxel.run) ───────────────────────────
# We can't call CalamityDice() because it calls pyxel.run().
# Verify reset() method exists and check key attributes are assigned there.
assert hasattr(CalamityDice, "reset")
# Check that reset() sets the expected attributes (inspect source bytecode)
import inspect
src = inspect.getsource(CalamityDice.reset)
expected_attrs = [
    "self.phase", "self.turn", "self.score", "self.wave",
    "self.hp", "self.max_hp", "self.heat",
    "self.dice", "self.log_dice",
    "self.enemy_hp", "self.enemy_max_hp", "self.enemy_atk",
    "self.particles", "self.messages",
]
for attr_ref in expected_attrs:
    assert attr_ref in src, f"Missing assignment in reset(): {attr_ref}"

print("ALL TESTS PASSED ✓")
print(f"  Elements: {ELEMENTS}")
print(f"  Element names: {ELEM_NAMES}")
print(f"  Enemy waves: {[w['name'] for w in ENEMY_WAVES]}")
print(f"  Heat thresholds: warn={HEAT_WARN} danger={HEAT_DANGER} dmg={HEAT_DAMAGE}")
print(f"  Dice: base={BASE_DICE} max={MAX_DICE} log={MAX_LOG}")
print(f"  Damage per pip: {DAMAGE_PER_PIP}")
