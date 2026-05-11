"""test_imports.py — Headless logic tests for FORESIGHT."""
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/013_foresight")
from main import (
    Game, Phase, Pos, FutureCard, Particle, FloatingText,
    SCREEN_W, SCREEN_H, GRID_COLS, GRID_ROWS, CELL_SIZE,
    GRID_X, GRID_Y,
    MAX_HP, INITIAL_FUTURE, MAX_FUTURE, SPAWN_HORIZON,
    BASE_SPAWNS_PER_TURN, KILL_FUTURE_CHANCE,
)

# ── Test constants ──
assert SCREEN_W == 320
assert SCREEN_H == 256
assert GRID_COLS == 8
assert GRID_ROWS == 8
assert CELL_SIZE == 28
assert MAX_HP == 10
assert INITIAL_FUTURE == 5
assert MAX_FUTURE == 8
assert SPAWN_HORIZON == 4
assert BASE_SPAWNS_PER_TURN == 2
assert 0.0 < KILL_FUTURE_CHANCE < 1.0

# ── Test Phase enum ──
assert Phase.PLAYER_TURN in Phase
assert Phase.ENEMY_TURN in Phase
assert Phase.GAME_OVER in Phase

# ── Test Pos ──
p = Pos(3, 5)
assert p.x == 3
assert p.y == 5

# ── Test FutureCard ──
fc = FutureCard(Pos(1, 2), 3)
assert fc.pos == Pos(1, 2)
assert fc.turns_until_spawn == 3
fc.turns_until_spawn -= 1
assert fc.turns_until_spawn == 2

# ── Test Particle ──
part = Particle(10.0, 20.0, 0.5, -0.5, 12, 8)
assert part.x == 10.0
assert part.y == 20.0
assert part.vx == 0.5
assert part.vy == -0.5
assert part.life == 12
assert part.color == 8

# ── Test FloatingText ──
ft = FloatingText(100.0, 200.0, "+5", 20, 10)
assert ft.text == "+5"
assert ft.life == 20

# ── Test Game state (via __new__ + reset, no pyxel.init) ──
g = Game.__new__(Game)
g.reset()

assert g.phase == Phase.PLAYER_TURN
assert g.player_pos == Pos(GRID_COLS // 2, GRID_ROWS - 1)  # (4, 7)
assert g.hp == MAX_HP
assert g.score == 0
assert g.turn == 0
assert g.future_count == INITIAL_FUTURE
assert isinstance(g.enemies, list)
assert isinstance(g.future_cards, list)
assert isinstance(g.particles, list)
assert isinstance(g.floating_texts, list)

# ── Test future cards seeded ──
assert len(g.future_cards) == INITIAL_FUTURE
for fc in g.future_cards:
    assert isinstance(fc, FutureCard)
    assert 1 <= fc.turns_until_spawn <= SPAWN_HORIZON
    assert 0 <= fc.pos.x < GRID_COLS
    assert 0 <= fc.pos.y < GRID_ROWS

# ── Test helpers ──
assert g._is_adjacent(Pos(3, 3), Pos(3, 4)) is True
assert g._is_adjacent(Pos(3, 3), Pos(4, 4)) is False
assert g._is_adjacent(Pos(3, 3), Pos(2, 3)) is True
assert g._is_adjacent(Pos(3, 3), Pos(3, 3)) is False

# ── Test grid_to_screen ──
sx, sy = g._grid_to_screen(Pos(0, 0))
assert sx == GRID_X + CELL_SIZE // 2  # center of cell
assert sy == GRID_Y + CELL_SIZE // 2

# ── Test enemy_step ──
g.player_pos = Pos(4, 4)
dx, dy = g._enemy_step(Pos(4, 5))   # enemy below player
assert dy == -1  # moves up toward player

dx, dy = g._enemy_step(Pos(2, 4))   # enemy left of player
assert dx == 1   # moves right toward player

# ── Test edge position generation ──
edge_pos = g._rand_edge_pos()
assert 0 <= edge_pos.x < GRID_COLS
assert 0 <= edge_pos.y < GRID_ROWS
# Must be on an edge
assert edge_pos.x == 0 or edge_pos.x == GRID_COLS - 1 or edge_pos.y == 0 or edge_pos.y == GRID_ROWS - 1

# ── Test spawns per turn escalation ──
g.turn = 0
assert g._spawns_per_turn == BASE_SPAWNS_PER_TURN
g.turn = 8
assert g._spawns_per_turn == BASE_SPAWNS_PER_TURN + 1
g.turn = 16
assert g._spawns_per_turn == BASE_SPAWNS_PER_TURN + 2

# ── Test attack with no enemies (should not crash) ──
g.enemies = []
g.future_count = 5
g._do_attack()
# No enemies, message should be "NO TARGET"
assert g.future_count == 5  # unchanged (no valid attack)

# ── Test attack with adjacent enemy ──
import random as _random
_old_random = _random.random
_random.random = lambda: 0.9  # always > KILL_FUTURE_CHANCE → no regain
g.future_count = 5
g.player_pos = Pos(4, 4)
g.enemies = [Pos(4, 5)]  # adjacent
g._do_attack()
assert g.enemies == []  # enemy killed
assert g.future_count == 4  # -1 for attack
assert g.score == 5  # +5 for kill
_random.random = _old_random  # restore

# ── Test attack with no future left ──
g.future_count = 0
g.player_pos = Pos(4, 4)
g.enemies = [Pos(4, 5)]
g._do_attack()
assert len(g.enemies) == 1  # enemy NOT killed (can't attack)
assert g.future_count == 0

# ── Test enemy turn: enemy reaches player ──
g.reset()
g.hp = 5
g.player_pos = Pos(4, 4)
g.enemies = [Pos(4, 5)]  # enemy below player, will move up into player
g.future_cards = []  # clear future cards to simplify
g.phase = Phase.ENEMY_TURN
g._update_enemy_turn()
# Enemy should have dealt damage
assert g.hp == 4
assert g.phase == Phase.PLAYER_TURN  # back to player

# ── Test enemy turn: enemy reaches player → game over ──
g.reset()
g.hp = 1
g.player_pos = Pos(4, 4)
g.enemies = [Pos(4, 5)]
g.future_cards = []
g.phase = Phase.ENEMY_TURN
g._update_enemy_turn()
assert g.hp == 0
assert g.phase == Phase.GAME_OVER

# ── Test enemy turn: spawn from future cards ──
g.reset()
g.player_pos = Pos(4, 4)
g.enemies = []
safe_pos = Pos(0, 0)  # far from player
g.future_cards = [FutureCard(safe_pos, 0)]  # spawns NOW
g.phase = Phase.ENEMY_TURN
g._update_enemy_turn()
assert len(g.enemies) == 1
assert g.enemies[0] == safe_pos
# Future cards: old one consumed, new ones added by escalation
assert len(g.future_cards) == g._spawns_per_turn  # new cards added

# ── Test enemy turn: future card at player position (should not spawn) ──
g.reset()
g.player_pos = Pos(4, 4)
g.enemies = []
g.future_cards = [FutureCard(Pos(4, 4), 0)]  # spawns at player → blocked
g.phase = Phase.ENEMY_TURN
g._update_enemy_turn()
assert len(g.enemies) == 0  # no spawn (blocked)
# But future cards will have new ones added
assert len(g.future_cards) == g._spawns_per_turn

print("All 30+ assertions passed!")
