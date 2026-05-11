"""test_imports.py — Headless logic tests for Mining Front."""
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/012_mining_front")

import inspect
from main import (
    TowerKind,
    EnemyKind,
    Phase,
    TOWER_DEFS,
    ENEMY_DEFS,
    Tower,
    Enemy,
    Particle,
    FloatingText,
    Game,
)


# ── Tower definitions ──
def test_tower_defs_exist() -> None:
    assert len(TOWER_DEFS) == 3
    for kind, defn in TOWER_DEFS.items():
        assert defn.cost > 0
        assert defn.damage > 0
        assert defn.cooldown > 0
        assert isinstance(defn.name, str)
        assert isinstance(defn.desc, str)


def test_laser_def() -> None:
    td = TOWER_DEFS[TowerKind.LASER]
    assert td.name == "LASER"
    assert td.cost == 10
    assert td.damage == 15.0


def test_chain_def() -> None:
    td = TOWER_DEFS[TowerKind.CHAIN]
    assert td.name == "CHAIN"
    assert td.cost == 25
    assert td.damage == 12.0


def test_siphon_def() -> None:
    td = TOWER_DEFS[TowerKind.SIPHON]
    assert td.name == "SIPHON"
    assert td.cost == 15
    assert td.damage == 8.0


# ── Enemy definitions ──
def test_enemy_defs_exist() -> None:
    assert len(ENEMY_DEFS) == 3
    for kind, defn in ENEMY_DEFS.items():
        assert defn.hp > 0
        assert defn.speed > 0
        assert defn.reward > 0
        assert isinstance(defn.name, str)


def test_enemy_def_property() -> None:
    e = Enemy(EnemyKind.SCOUT, 100.0, 2, 20.0, 5)
    assert e.defn == ENEMY_DEFS[EnemyKind.SCOUT]
    assert e.defn.hp == 20.0
    assert e.defn.speed == 60.0


# ── Tower dataclass ──
def test_tower_creation() -> None:
    t = Tower(TowerKind.LASER, 3, 2)
    assert t.kind == TowerKind.LASER
    assert t.col == 3
    assert t.row == 2
    assert t.cooldown == 0.0


# ── Particle dataclass ──
def test_particle_creation() -> None:
    p = Particle(10.0, 20.0, 1.0, -2.0, 0.5, 0.5, 7)
    assert abs(p.x - 10.0) < 0.01
    assert abs(p.y - 20.0) < 0.01
    assert abs(p.vx - 1.0) < 0.01
    assert abs(p.vy + 2.0) < 0.01
    assert abs(p.life - 0.5) < 0.01


# ── FloatingText dataclass ──
def test_floating_text_creation() -> None:
    f = FloatingText(50.0, 30.0, "+10", 1.0, 8)
    assert f.text == "+10"
    assert f.color == 8


# ── Phase enum ──
def test_phase_values() -> None:
    assert Phase.PREP in Phase
    assert Phase.COMBAT in Phase
    assert Phase.VICTORY in Phase
    assert Phase.DEFEAT in Phase


# ── TowerKind enum ──
def test_tower_kinds() -> None:
    kinds = list(TowerKind)
    assert len(kinds) == 3
    assert TowerKind.LASER in kinds


# ── Grid helpers (via class) ──
def test_cell_center() -> None:
    x, y = Game._cell_center(0, 0)
    assert x > 0
    assert y > 0


def test_cell_rect() -> None:
    x, y, w, h = Game._cell_rect(0, 0)
    assert w == 38
    assert h == 38


def test_grid_pos_in_bounds() -> None:
    cx, cy = Game._cell_center(3, 2)
    result = Game._grid_pos(cx, cy)
    assert result is not None
    assert result == (3, 2)


def test_grid_pos_out_of_bounds() -> None:
    assert Game._grid_pos(-10, -10) is None
    assert Game._grid_pos(500, 500) is None


# ── Game reset() introspection ──
def test_game_reset_initializes_state() -> None:
    """Verify reset() sets all expected state attributes."""
    src = inspect.getsource(Game.reset)
    # Check key attributes are in the reset source
    for attr in [
        "self.hp",
        "self.ore",
        "self.wave",
        "self.phase",
        "self.towers",
        "self.enemies",
        "self.particles",
        "self.floaters",
        "self.selected_tower",
        "self.score",
    ]:
        assert attr in src, f"{attr} not found in Game.reset() source"


def test_game_method_exists() -> None:
    """Verify all key methods exist on Game."""
    methods = [
        "reset",
        "update",
        "draw",
        "_gen_wave",
        "_find_target",
        "_chain_bonus",
        "_update_combat",
        "_update_prep",
    ]
    for m in methods:
        assert hasattr(Game, m), f"Game.{m} missing"


def test_chain_bonus_logic() -> None:
    """Verify chain bonus calculation without running Pyxel."""
    game = Game.__new__(Game)
    game.rng = __import__("random").Random(42)
    game.towers = []
    # Place 3 chain reactors adjacent
    game.towers.append(Tower(TowerKind.CHAIN, 2, 2))
    game.towers.append(Tower(TowerKind.CHAIN, 3, 2))
    game.towers.append(Tower(TowerKind.CHAIN, 2, 3))
    # Tower at (2,2) has 2 adjacent chains
    bonus = game._chain_bonus(game.towers[0])
    assert abs(bonus - 2.0) < 0.01, f"expected 2.0, got {bonus}"
    # Tower at (3,2) has 1 adjacent chain
    bonus = game._chain_bonus(game.towers[1])
    assert abs(bonus - 1.5) < 0.01, f"expected 1.5, got {bonus}"
    # Tower at (2,3) has 1 adjacent chain
    bonus = game._chain_bonus(game.towers[2])
    assert abs(bonus - 1.5) < 0.01, f"expected 1.5, got {bonus}"
    # Non-chain tower gets no bonus
    game.towers.append(Tower(TowerKind.LASER, 1, 1))
    bonus = game._chain_bonus(game.towers[3])
    assert abs(bonus - 1.0) < 0.01


def test_tower_at_empty() -> None:
    game = Game.__new__(Game)
    game.towers = []
    assert game._tower_at(0, 0) is None


def test_tower_at_occupied() -> None:
    game = Game.__new__(Game)
    t = Tower(TowerKind.LASER, 3, 2)
    game.towers = [t]
    assert game._tower_at(3, 2) is t
    assert game._tower_at(0, 0) is None


# ── Game-specific constants ──
def test_enemy_rewards() -> None:
    # Check that tank is most rewarding (risk/reward)
    rewards = {k: d.reward for k, d in ENEMY_DEFS.items()}
    assert rewards[EnemyKind.TANK] > rewards[EnemyKind.SCOUT]
    assert rewards[EnemyKind.TANK] > rewards[EnemyKind.DRONE]


def test_tower_costs() -> None:
    costs = {k: d.cost for k, d in TOWER_DEFS.items()}
    assert costs[TowerKind.CHAIN] > costs[TowerKind.LASER], "CHAIN should be most expensive"
    assert costs[TowerKind.CHAIN] > costs[TowerKind.SIPHON]


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=False,
    )
    sys.exit(result.returncode)
