"""test_imports.py — Headless logic tests for DUNGEON CHAIN."""
from __future__ import annotations

import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/071_dungeon_chain")

from main import (
    CELL,
    ENEMY_COLORS,
    ENEMY_MOVE_INTERVAL,
    GREEN,
    GRID_H,
    GRID_W,
    INVULN_FRAMES,
    RED,
    SCREEN_H,
    SCREEN_W,
    TILE_DOOR,
    TILE_EXIT,
    TILE_FLOOR,
    TILE_KEY,
    TILE_WALL,
    WHITE,
    Enemy,
    FloatingText,
    Game,
    Particle,
    Phase,
    Player,
)


# ── Helper ────────────────────────────────────────────────────────────

def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(seed)
    g._init_state()
    return g


# ── Dataclass Tests ────────────────────────────────────────────────────

def test_enemy_defaults() -> None:
    e = Enemy(x=3, y=5, color=RED)
    assert e.x == 3
    assert e.y == 5
    assert e.color == RED
    assert e.hp == 1
    assert e.alive is True


def test_player_defaults() -> None:
    p = Player(x=1, y=1)
    assert p.x == 1
    assert p.y == 1
    assert p.hp == 5
    assert p.max_hp == 5
    assert p.has_key is False


def test_particle_defaults() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, color=8, life=12)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.color == 8
    assert p.life == 12


def test_floating_text_defaults() -> None:
    ft = FloatingText(x=80.0, y=200.0, text="+100", life=30, color=7)
    assert ft.x == 80.0
    assert ft.y == 200.0
    assert ft.text == "+100"
    assert ft.life == 30
    assert ft.color == 7


# ── Phase Enum Tests ───────────────────────────────────────────────────

def test_phase_values() -> None:
    assert Phase.TITLE == 0
    assert Phase.PLAYING == 1
    assert Phase.GAME_OVER == 2
    assert Phase.VICTORY == 3
    assert len(list(Phase)) == 4


# ── Constants Tests ────────────────────────────────────────────────────

def test_constants() -> None:
    assert GRID_W == 16
    assert GRID_H == 12
    assert CELL == 20
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert ENEMY_MOVE_INTERVAL == 30
    assert INVULN_FRAMES == 30
    assert len(ENEMY_COLORS) == 4


# ── Init State Tests ───────────────────────────────────────────────────

def test_init_state_creates_dungeon() -> None:
    g = _make_game()
    assert len(g.dungeon) == GRID_H
    assert len(g.dungeon[0]) == GRID_W


def test_init_state_dungeon_has_tiles() -> None:
    g = _make_game()
    has_wall = False
    has_floor = False
    for y in range(GRID_H):
        for x in range(GRID_W):
            if g.dungeon[y][x] == TILE_WALL:
                has_wall = True
            if g.dungeon[y][x] == TILE_FLOOR:
                has_floor = True
    assert has_wall
    assert has_floor


def test_init_state_has_exit() -> None:
    g = _make_game()
    found = False
    for y in range(GRID_H):
        for x in range(GRID_W):
            if g.dungeon[y][x] == TILE_EXIT:
                found = True
    assert found


def test_init_state_has_key() -> None:
    g = _make_game()
    found = False
    for y in range(GRID_H):
        for x in range(GRID_W):
            if g.dungeon[y][x] == TILE_KEY:
                found = True
    assert found


def test_init_state_has_door() -> None:
    g = _make_game()
    found = False
    for y in range(GRID_H):
        for x in range(GRID_W):
            if g.dungeon[y][x] == TILE_DOOR:
                found = True
    assert found


def test_init_state_enemies() -> None:
    g = _make_game()
    assert len(g.enemies) > 0
    assert all(e.alive for e in g.enemies)


def test_init_state_player_start() -> None:
    g = _make_game()
    assert g.player.x == 1
    assert g.player.y == 1
    assert g.player.hp == 5
    assert g.player.has_key is False
    assert g.score == 0
    assert g.combo == 0


def test_reset_initializes_state() -> None:
    g = _make_game()
    g.score = 500
    g.combo = 5
    g.player.hp = 2
    g.reset()
    assert g.phase == Phase.TITLE
    g._init_state()
    assert g.player.hp == 5
    assert g.score == 0
    assert g.combo == 0


# ── Movement Tests ─────────────────────────────────────────────────────

def test_move_player_into_wall_blocked() -> None:
    g = _make_game()
    g._init_state()
    # Place player next to wall
    g.player.x = 1
    g.player.y = 1
    g._move_player(-1, 0)
    assert g.player.x == 1
    assert g.player.y == 1


def test_move_player_into_floor_succeeds() -> None:
    g = _make_game()
    g.player.x = 2
    g.player.y = 1
    g.dungeon[1][2] = TILE_FLOOR
    g.dungeon[1][3] = TILE_FLOOR
    g._move_player(1, 0)
    assert g.player.x == 3
    assert g.player.y == 1


def test_move_player_door_blocked_without_key() -> None:
    g = _make_game()
    g.player.x = 2
    g.player.y = 1
    g.dungeon[1][2] = TILE_FLOOR
    g.dungeon[1][3] = TILE_DOOR
    g.player.has_key = False
    g._move_player(1, 0)
    assert g.player.x == 2  # blocked
    assert g.player.y == 1


def test_move_player_door_unlocked_with_key() -> None:
    g = _make_game()
    g.player.x = 2
    g.player.y = 1
    g.dungeon[1][2] = TILE_FLOOR
    g.dungeon[1][3] = TILE_DOOR
    g.player.has_key = True
    g._move_player(1, 0)
    assert g.player.x == 3
    assert g.dungeon[1][3] == TILE_FLOOR  # door becomes floor


def test_move_player_collects_key() -> None:
    g = _make_game()
    g.player.x = 2
    g.player.y = 1
    g.dungeon[1][2] = TILE_FLOOR
    g.dungeon[1][3] = TILE_KEY
    g.player.has_key = False
    g._move_player(1, 0)
    assert g.player.x == 3
    assert g.player.has_key is True
    assert g.dungeon[1][3] == TILE_FLOOR


# ── Combat Tests ───────────────────────────────────────────────────────

def test_attack_enemy_kills_it() -> None:
    g = _make_game()
    e = Enemy(x=3, y=1, color=RED)
    g._attack_enemy(e)
    assert e.alive is False


def test_attack_enemy_first_kill_combo_1() -> None:
    g = _make_game()
    g.combo = 0
    g.last_kill_color = -1
    e = Enemy(x=3, y=1, color=RED)
    g._attack_enemy(e)
    assert g.combo == 1
    assert g.last_kill_color == RED
    assert g.score == 100  # 100 * 1


def test_attack_enemy_same_color_combo_grows() -> None:
    g = _make_game()
    g.combo = 1
    g.last_kill_color = RED
    g.score = 0
    e = Enemy(x=3, y=1, color=RED)
    g._attack_enemy(e)
    assert g.combo == 2
    assert g.score == 200  # 100 * 2


def test_attack_enemy_different_color_damage_and_reset() -> None:
    g = _make_game()
    g.combo = 3
    g.last_kill_color = RED
    g.score = 0
    g.player.hp = 5
    e = Enemy(x=3, y=1, color=GREEN)
    g._attack_enemy(e)
    assert g.combo == 1
    assert g.last_kill_color == GREEN
    assert g.player.hp == 4  # 5 - 1
    assert g.score == 100  # 100 * 1 (new combo)


def test_attack_enemy_no_damage_when_combo_zero() -> None:
    g = _make_game()
    g.combo = 0
    g.last_kill_color = -1
    g.player.hp = 5
    e = Enemy(x=3, y=1, color=GREEN)
    g._attack_enemy(e)
    assert g.player.hp == 5  # no damage when combo was 0


def test_attack_enemy_sets_max_combo() -> None:
    g = _make_game()
    g.combo = 3
    g.last_kill_color = RED
    g.max_combo = 3
    e = Enemy(x=3, y=1, color=RED)
    g._attack_enemy(e)
    assert g.combo == 4
    assert g.max_combo == 4


def test_attack_enemy_spawns_particles() -> None:
    g = _make_game(42)
    g.combo = 1
    g.last_kill_color = RED
    e = Enemy(x=3, y=1, color=RED)
    g._attack_enemy(e)
    assert len(g.particles) > 0


def test_attack_enemy_spawns_floating_text() -> None:
    g = _make_game(42)
    g.combo = 1
    g.last_kill_color = RED
    e = Enemy(x=3, y=1, color=RED)
    g._attack_enemy(e)
    assert len(g.floating_texts) > 0


# ── Find Adjacent Enemy Tests ──────────────────────────────────────────

def test_find_adjacent_enemy_finds() -> None:
    g = _make_game()
    g.enemies = [Enemy(x=3, y=1, color=RED)]
    g.player.x = 2
    g.player.y = 1
    e = g._find_adjacent_enemy(g.player.x, g.player.y)
    assert e is not None
    assert e.x == 3
    assert e.y == 1


def test_find_adjacent_enemy_not_found() -> None:
    g = _make_game()
    g.enemies = [Enemy(x=5, y=1, color=RED)]
    g.player.x = 2
    g.player.y = 1
    e = g._find_adjacent_enemy(g.player.x, g.player.y)
    assert e is None


def test_find_adjacent_enemy_ignores_dead() -> None:
    g = _make_game()
    g.enemies = [Enemy(x=3, y=1, color=RED, alive=False)]
    g.player.x = 2
    g.player.y = 1
    e = g._find_adjacent_enemy(g.player.x, g.player.y)
    assert e is None


# ── Room Detection Tests ───────────────────────────────────────────────

def test_get_room_cells_returns_cells() -> None:
    g = _make_game()
    cells = g._get_room_cells(3, 1)
    assert len(cells) > 0
    assert (3, 1) in cells


def test_get_room_cells_wall_returns_empty() -> None:
    g = _make_game()
    cells = g._get_room_cells(0, 0)
    assert len(cells) == 0


def test_get_room_cells_connected_room() -> None:
    g = _make_game()
    # Room 1 is cols 1-8, rows 1-2 connected
    c1 = g._get_room_cells(3, 1)
    c2 = g._get_room_cells(7, 1)
    assert c1 == c2  # same room


# ── ROOM SURGE Tests ───────────────────────────────────────────────────

def test_bfs_surge_kills_same_color_in_room() -> None:
    g = _make_game()
    g.enemies = [
        Enemy(x=2, y=1, color=RED),
        Enemy(x=4, y=1, color=RED),
        Enemy(x=6, y=1, color=RED),
        Enemy(x=3, y=1, color=GREEN),
    ]
    g.combo = 4
    g.last_kill_color = RED
    g.score = 0
    g._bfs_surge(2, 1, RED)
    assert not g.enemies[0].alive  # RED at (2,1) — already killed before surge? no, surge kills all
    assert not g.enemies[1].alive  # RED at (4,1)
    assert not g.enemies[2].alive  # RED at (6,1)
    assert g.enemies[3].alive  # GREEN survives


def test_bfs_surge_increases_combo() -> None:
    g = _make_game()
    g.enemies = [
        Enemy(x=2, y=1, color=RED),
        Enemy(x=4, y=1, color=RED),
    ]
    g.combo = 4
    g.last_kill_color = RED
    g.score = 0
    g._bfs_surge(2, 1, RED)
    assert g.combo == 6  # 4 + 2 killed
    assert g.score > 0


def test_bfs_surge_increases_max_combo() -> None:
    g = _make_game()
    g.enemies = [
        Enemy(x=2, y=1, color=RED),
        Enemy(x=4, y=1, color=RED),
    ]
    g.combo = 4
    g.max_combo = 4
    g.last_kill_color = RED
    g._bfs_surge(2, 1, RED)
    assert g.max_combo > 4


# ── Enemy AI Tests ─────────────────────────────────────────────────────

def test_enemy_moves_toward_player() -> None:
    g = _make_game()
    g.enemies = [Enemy(x=5, y=1, color=RED)]
    g.player.x = 3
    g.player.y = 1
    g.enemy_move_timer = 0
    g.dungeon[1][4] = TILE_FLOOR
    g._update_enemies()
    assert g.enemies[0].x == 4  # moved left toward player
    assert g.enemies[0].y == 1


def test_enemy_does_not_move_if_far() -> None:
    g = _make_game()
    g.enemies = [Enemy(x=10, y=10, color=RED)]
    g.player.x = 1
    g.player.y = 1
    g.enemy_move_timer = 0
    g._update_enemies()
    assert g.enemies[0].x == 10  # too far, no move


def test_enemy_contact_damages_player() -> None:
    g = _make_game()
    g.enemies = [Enemy(x=2, y=1, color=RED)]
    g.player.x = 2
    g.player.y = 1
    g.enemy_move_timer = 0
    g.invuln_timer = 0
    g.player.hp = 5
    g._update_enemies()
    assert g.player.hp == 4
    assert g.invuln_timer > 0


def test_enemy_no_damage_during_invuln() -> None:
    g = _make_game()
    g.enemies = [Enemy(x=2, y=1, color=RED)]
    g.player.x = 2
    g.player.y = 1
    g.enemy_move_timer = 0
    g.invuln_timer = 10
    g.player.hp = 5
    g._update_enemies()
    assert g.player.hp == 5


# ── Particle / Floating Text Tests ─────────────────────────────────────

def test_update_particles_moves_and_decays() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=50.0, vx=1.0, vy=-2.0, color=8, life=5)
    g.particles.append(p)
    g._update_particles()
    assert p.x == 101.0
    assert p.y == 48.0
    assert p.life == 4


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=50.0, vx=1.0, vy=-2.0, color=8, life=1)
    g.particles.append(p)
    g._update_particles()
    assert len(g.particles) == 0


def test_update_floating_texts_floats_and_decays() -> None:
    g = _make_game()
    ft = FloatingText(x=80.0, y=200.0, text="+100", life=10, color=7)
    g.floating_texts.append(ft)
    g._update_floating_texts()
    assert ft.y == 199.5
    assert ft.life == 9


def test_update_floating_texts_removes_dead() -> None:
    g = _make_game()
    ft = FloatingText(x=80.0, y=200.0, text="+100", life=1, color=7)
    g.floating_texts.append(ft)
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_spawn_particles() -> None:
    g = _make_game(42)
    g._spawn_particles(3, 1, RED, count=6)
    assert len(g.particles) == 6


def test_spawn_floating_text() -> None:
    g = _make_game()
    g._spawn_floating_text(3, 1, "+100", WHITE, 20)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "+100"


# ── Click Handling Tests ───────────────────────────────────────────────

def test_handle_click_on_adjacent_enemy() -> None:
    g = _make_game()
    g.enemies = [Enemy(x=3, y=1, color=GREEN)]
    g.player.x = 2
    g.player.y = 1
    g.combo = 0
    g.last_kill_color = -1
    g._handle_click(3 * CELL + CELL // 2, 1 * CELL + CELL // 2)
    assert not g.enemies[0].alive


def test_handle_click_not_adjacent() -> None:
    g = _make_game()
    g.enemies = [Enemy(x=5, y=1, color=GREEN)]
    g.player.x = 2
    g.player.y = 1
    g._handle_click(5 * CELL + CELL // 2, 1 * CELL + CELL // 2)
    assert g.enemies[0].alive  # not adjacent to player


# ── Score Tests ────────────────────────────────────────────────────────

def test_score_increases_with_combo() -> None:
    g = _make_game()
    g.combo = 1
    g.last_kill_color = RED
    g.score = 0
    e = Enemy(x=3, y=1, color=RED)
    g._attack_enemy(e)
    assert g.score == 200  # 100 * 2


def test_score_surge_adds_bonus() -> None:
    g = _make_game()
    g.enemies = [
        Enemy(x=2, y=1, color=RED),
        Enemy(x=4, y=1, color=RED),
    ]
    g.combo = 4
    g.last_kill_color = RED
    g.score = 0
    g._bfs_surge(2, 1, RED)
    # 2 killed * 50 * combo(6) = 2 * 50 * 6 = 600
    assert g.score == 600


print("All tests passed!")
