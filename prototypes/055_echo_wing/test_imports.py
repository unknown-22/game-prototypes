"""test_imports.py — Headless logic tests for ECHO WING.

Tests dataclasses, game state, combat logic, and chain burst mechanics
without initializing Pyxel graphics.
"""
from __future__ import annotations

import math
import sys
import types

# Patch pyxel before import to avoid init
_mock_pyxel = types.ModuleType("pyxel")
_mock_pyxel.COLOR_BLACK = 0
_mock_pyxel.COLOR_NAVY = 1
_mock_pyxel.COLOR_PURPLE = 2
_mock_pyxel.COLOR_GREEN = 3
_mock_pyxel.COLOR_BROWN = 4
_mock_pyxel.COLOR_DARK_BLUE = 5
_mock_pyxel.COLOR_LIGHT_BLUE = 6
_mock_pyxel.COLOR_WHITE = 7
_mock_pyxel.COLOR_RED = 8
_mock_pyxel.COLOR_ORANGE = 9
_mock_pyxel.COLOR_YELLOW = 10
_mock_pyxel.COLOR_LIME = 11
_mock_pyxel.COLOR_CYAN = 12
_mock_pyxel.COLOR_GRAY = 13
_mock_pyxel.COLOR_PINK = 14
_mock_pyxel.COLOR_PEACH = 15
_mock_pyxel.KEY_UP = 0
_mock_pyxel.KEY_DOWN = 1
_mock_pyxel.KEY_LEFT = 2
_mock_pyxel.KEY_RIGHT = 3
_mock_pyxel.KEY_Q = 4
_mock_pyxel.KEY_E = 5
_mock_pyxel.KEY_W = 6
_mock_pyxel.KEY_S = 7
_mock_pyxel.KEY_SPACE = 8
_mock_pyxel.KEY_RETURN = 9
_mock_pyxel.btn = lambda k: False  # all keys unpressed in headless tests
_mock_pyxel.btnp = lambda k: False  # all keys not just-pressed
sys.modules["pyxel"] = _mock_pyxel

# Now import game module
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/055_echo_wing")
from main import (  # noqa: E402
    BULLET_SPEED,
    BULLET_W,
    BULLET_H,
    CHAIN_BURST_COMBO,
    CHAIN_BURST_RADIUS,
    COLOR_IDS,
    COLOR_NAMES,
    ENEMY_RADIUS,
    ENEMY_SPEED_BASE,
    FORMATIONS,
    HEAT_COOL_RATE,
    HEAT_PER_BURST,
    HEAT_PER_KILL,
    MAX_HEAT,
    NUM_COLORS,
    PLAYER_RADIUS,
    PLAYER_X,
    PLAYER_SPEED,
    SCREEN_H,
    SCREEN_W,
    Bullet,
    Enemy,
    EnemyType,
    EnemyDef,
    ENEMY_DEFS,
    FloatingText,
    Formation,
    Game,
    Particle,
    Phase,
    Pos,
)


def test_constants() -> None:
    """Verify all constants are sensible."""
    assert SCREEN_W == 256
    assert SCREEN_H == 224
    assert NUM_COLORS == 4
    assert len(COLOR_IDS) == 4
    assert len(COLOR_NAMES) == 4
    assert PLAYER_X == 50
    assert BULLET_SPEED > 0
    assert BULLET_W > 0
    assert BULLET_H > 0
    assert CHAIN_BURST_COMBO >= 2
    assert CHAIN_BURST_RADIUS > 0
    assert MAX_HEAT > 0
    assert HEAT_COOL_RATE > 0
    assert ENEMY_SPEED_BASE > 0


def test_enums() -> None:
    """Verify enum definitions."""
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    assert EnemyType.NORMAL in EnemyType
    assert EnemyType.FAST in EnemyType
    assert EnemyType.TANK in EnemyType


def test_enemy_defs() -> None:
    """Verify enemy definitions are valid."""
    assert len(ENEMY_DEFS) == 3
    assert ENEMY_DEFS[EnemyType.NORMAL].hp == 1
    assert ENEMY_DEFS[EnemyType.FAST].hp == 1
    assert ENEMY_DEFS[EnemyType.TANK].hp == 3
    assert ENEMY_DEFS[EnemyType.FAST].speed_mult > ENEMY_DEFS[EnemyType.NORMAL].speed_mult
    assert ENEMY_DEFS[EnemyType.TANK].radius > ENEMY_DEFS[EnemyType.NORMAL].radius


def test_formations() -> None:
    """Verify formations have offsets."""
    assert len(FORMATIONS) >= 3
    for f in FORMATIONS:
        assert len(f.offsets) >= 3
        assert f.name != ""


def test_enemy_dataclass() -> None:
    """Verify Enemy dataclass construction and defaults."""
    e = Enemy(x=200.0, y=100.0, color=0)
    assert e.x == 200.0
    assert e.y == 100.0
    assert e.color == 0
    assert e.etype == EnemyType.NORMAL
    assert e.hp == 1
    assert e.radius == ENEMY_RADIUS
    assert e.speed == ENEMY_SPEED_BASE
    assert e.alive is True
    assert e.defn == ENEMY_DEFS[EnemyType.NORMAL]


def test_bullet_dataclass() -> None:
    """Verify Bullet dataclass construction."""
    b = Bullet(x=100.0, y=50.0, color=2)
    assert b.x == 100.0
    assert b.y == 50.0
    assert b.color == 2
    assert b.speed == BULLET_SPEED
    assert b.hit is False


def test_particle_dataclass() -> None:
    """Verify Particle dataclass construction."""
    p = Particle(x=50.0, y=60.0, vx=1.0, vy=-2.0, color=8, life=20)
    assert p.x == 50.0
    assert p.y == 60.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.color == 8
    assert p.life == 20
    assert p.max_life == 20


def test_floating_text_dataclass() -> None:
    """Verify FloatingText dataclass construction."""
    ft = FloatingText(x=100.0, y=80.0, text="+100", color=8, life=30)
    assert ft.x == 100.0
    assert ft.y == 80.0
    assert ft.text == "+100"
    assert ft.color == 8
    assert ft.life == 30
    assert ft.vy == -1.5


def test_pos_namedtuple() -> None:
    """Verify Pos NamedTuple."""
    p = Pos(10.0, 20.0)
    assert p.x == 10.0
    assert p.y == 20.0


def test_game_reset() -> None:
    """Verify Game.reset() initializes all state correctly."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()
    assert g.phase == Phase.PLAYING
    assert g.frame == 0
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.hp == 5
    assert g.max_hp == 5
    assert g.player_color == 0
    assert g.invincible == 0
    assert g.player_y > 0
    assert len(g.enemies) == 0
    assert len(g.bullets) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.spawn_timer > 0
    assert g.enemies_killed == 0
    assert g.burst_count == 0
    assert len(g.stars) == 50
    assert len(g.echo_positions) == g.echo_positions.maxlen


def test_player_movement_boundaries() -> None:
    """Verify player_y stays within screen bounds after _update_player."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()

    # Test upper boundary: pushing up shouldn't go below 16
    g.player_y = 10.0
    g._update_player()
    assert g.player_y >= 16.0

    # Test lower boundary: pushing down shouldn't exceed SCREEN_H-16
    g.player_y = SCREEN_H + 50.0
    g._update_player()
    assert g.player_y <= SCREEN_H - 16


def test_weapon_cycle() -> None:
    """Verify player_color cycling."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()
    assert g.player_color == 0

    # Cycle forward
    for expected in range(1, NUM_COLORS):
        g.player_color = (g.player_color + 1) % NUM_COLORS
        assert g.player_color == expected

    # Wrap around
    g.player_color = (g.player_color + 1) % NUM_COLORS
    assert g.player_color == 0

    # Cycle backward
    g.player_color = (g.player_color - 1) % NUM_COLORS
    assert g.player_color == NUM_COLORS - 1


def test_bullet_movement() -> None:
    """Verify bullets move right and are removed off-screen."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()
    g.bullets = [Bullet(x=100.0, y=50.0, color=0)]
    g._update_bullets()
    assert len(g.bullets) == 1
    assert g.bullets[0].x == 100.0 + BULLET_SPEED

    # Off-screen bullet should be removed
    g.bullets = [Bullet(x=SCREEN_W + 20.0, y=50.0, color=0)]
    g._update_bullets()
    assert len(g.bullets) == 0

    # Hit bullet should be removed
    b = Bullet(x=100.0, y=50.0, color=0)
    b.hit = True
    g.bullets = [b]
    g._update_bullets()
    assert len(g.bullets) == 0


def test_enemy_movement() -> None:
    """Verify enemies move left and are removed off-screen."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()
    e = Enemy(x=200.0, y=100.0, color=0)
    g.enemies = [e]
    g._update_enemies()
    assert len(g.enemies) == 1
    assert g.enemies[0].x < 200.0  # moved left

    # Dead enemy should be removed
    e2 = Enemy(x=100.0, y=50.0, color=1)
    e2.alive = False
    e2.hp = 0  # must also be dead for the filter condition
    g.enemies = [e2]
    g._update_enemies()
    assert len(g.enemies) == 0

    # Off-screen enemy should be removed
    e3 = Enemy(x=-50.0, y=100.0, color=2)
    g.enemies = [e3]
    g._update_enemies()
    assert len(g.enemies) == 0


def test_particle_lifecycle() -> None:
    """Verify particles decay and are removed when life reaches 0."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()
    g.particles = [Particle(x=100.0, y=50.0, vx=0, vy=0, color=8, life=3)]
    assert len(g.particles) == 1
    g._update_particles()
    assert g.particles[0].life == 2
    g._update_particles()
    assert g.particles[0].life == 1
    g._update_particles()
    assert len(g.particles) == 0  # removed on life=0, not kept visible


def test_floating_text_lifecycle() -> None:
    """Verify floating texts decay and are removed."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()
    g.floating_texts = [FloatingText(x=100.0, y=80.0, text="TEST", color=8, life=2)]
    g._update_floating_texts()
    assert g.floating_texts[0].life == 1
    g._update_floating_texts()
    assert len(g.floating_texts) == 0  # removed on life=0


def test_heat_cooling() -> None:
    """Verify heat decreases over time."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()
    g.heat = 50.0
    g._update_heat()
    assert g.heat < 50.0
    assert g.heat >= 0.0

    # Heat shouldn't go below 0
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_heat_clamp() -> None:
    """Verify heat is clamped at MAX_HEAT."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()
    g.heat = MAX_HEAT + 50.0
    g._update_heat()
    assert g.heat <= MAX_HEAT


def test_starfield_init() -> None:
    """Verify starfield is properly initialized."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()
    assert len(g.stars) == 50
    for s in g.stars:
        assert 0 <= s[0] <= SCREEN_W
        assert 0 <= s[1] <= SCREEN_H
        assert 0.5 <= s[2] <= 2.5


def test_starfield_movement() -> None:
    """Verify stars move left."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()
    old_x = g.stars[0][0]
    g._update_stars()
    assert g.stars[0][0] < old_x  # moved left


def test_hit_enemy_same_color_builds_combo() -> None:
    """Verify same-color kill builds combo."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()
    e = Enemy(x=200.0, y=100.0, color=1, hp=1, alive=True)
    g.combo = 2  # already have some combo
    g._hit_enemy(e, bullet_color=1)  # same color
    assert g.combo == 3  # incremented
    assert e.alive is False
    assert g.enemies_killed == 1


def test_hit_enemy_wrong_color_resets_combo() -> None:
    """Verify wrong-color kill resets combo to 1."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()
    e = Enemy(x=200.0, y=100.0, color=2, hp=1, alive=True)
    g.combo = 3
    g._hit_enemy(e, bullet_color=0)  # wrong color
    assert g.combo == 1  # reset
    assert e.alive is False


def test_hit_enemy_non_lethal() -> None:
    """Verify non-lethal hits don't kill enemy."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()
    e = Enemy(x=200.0, y=100.0, color=0, hp=3, alive=True)
    g._hit_enemy(e, bullet_color=0)
    assert e.alive is True
    assert e.hp == 2
    assert e.flash_frames > 0
    assert g.enemies_killed == 0


def test_max_combo_tracking() -> None:
    """Verify max_combo tracks highest combo reached."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()
    g.combo = 5
    g.max_combo = 5

    e1 = Enemy(x=200.0, y=100.0, color=0, hp=1, alive=True)
    g._hit_enemy(e1, bullet_color=0)
    assert g.combo == 6
    assert g.max_combo == 6

    e2 = Enemy(x=200.0, y=120.0, color=1, hp=1, alive=True)
    g._hit_enemy(e2, bullet_color=0)  # wrong color
    assert g.combo == 1
    assert g.max_combo == 6  # max stays


def test_chain_burst_triggers_at_threshold() -> None:
    """Verify chain burst at combo >= CHAIN_BURST_COMBO."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()

    # Setup: seed enemy at center, cluster of same-color enemies nearby
    g.enemies = [
        Enemy(x=200.0, y=100.0, color=1, hp=1, alive=True),  # seed (hit by burst)
        Enemy(x=210.0, y=105.0, color=1, hp=1, alive=True),  # within radius
        Enemy(x=220.0, y=100.0, color=1, hp=1, alive=True),  # within radius
        Enemy(x=250.0, y=80.0, color=0, hp=1, alive=True),   # wrong color, no burst
    ]
    g.combo = CHAIN_BURST_COMBO  # at threshold

    # Kill first enemy with same-color bullet
    g._hit_enemy(g.enemies[0], bullet_color=1)

    # Chain burst should have killed enemies 1 and 2 (same color, within radius)
    assert g.enemies[0].alive is False  # killed by direct hit
    assert g.enemies[1].alive is False  # killed by burst
    assert g.enemies[2].alive is False  # killed by burst
    assert g.enemies[3].alive is True   # wrong color, survived
    assert g.burst_count >= 1


def test_chain_burst_radius_boundary() -> None:
    """Verify chain burst only affects enemies within radius."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()

    # Far enemy just outside burst radius
    seed_y = 100.0
    far_x = 200.0 + CHAIN_BURST_RADIUS + 20.0

    g.enemies = [
        Enemy(x=200.0, y=seed_y, color=1, hp=1, alive=True),  # seed
        Enemy(x=far_x, y=seed_y, color=1, hp=1, alive=True),  # too far
    ]
    g.combo = CHAIN_BURST_COMBO

    g._hit_enemy(g.enemies[0], bullet_color=1)

    assert g.enemies[0].alive is False  # seed killed
    assert g.enemies[1].alive is True   # too far, survived


def test_chain_burst_bfs_propagation() -> None:
    """Verify BFS propagates through chain of same-color enemies."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()

    # Create a chain where each enemy is within radius of the next
    step = CHAIN_BURST_RADIUS * 0.8
    g.enemies = []
    for i in range(5):
        g.enemies.append(Enemy(
            x=200.0 + step * i, y=100.0, color=1, hp=1, alive=True,
        ))

    g.combo = CHAIN_BURST_COMBO

    # Kill the first enemy
    g._hit_enemy(g.enemies[0], bullet_color=1)

    # All 5 should be dead (BFS propagated through the chain)
    for e in g.enemies:
        assert e.alive is False


def test_heat_from_burst() -> None:
    """Verify heat increases after chain burst."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()

    initial_heat = g.heat

    # Setup for burst
    g.enemies = [
        Enemy(x=200.0, y=100.0, color=1, hp=1, alive=True),
        Enemy(x=210.0, y=105.0, color=1, hp=1, alive=True),
    ]
    g.combo = CHAIN_BURST_COMBO

    g._hit_enemy(g.enemies[0], bullet_color=1)

    # Heat should have increased
    assert g.heat > initial_heat


def test_hit_player_reduces_hp() -> None:
    """Verify player takes damage and becomes invincible."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()
    initial_hp = g.hp
    g._hit_player()
    assert g.hp == initial_hp - 1
    assert g.invincible > 0


def test_hit_player_resets_combo() -> None:
    """Verify combo resets after taking damage."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()
    g.combo = 7
    g._hit_player()
    assert g.combo == 0


def test_invincibility_prevents_damage() -> None:
    """Verify invincible player doesn't take damage from collision."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()
    g.invincible = 30
    initial_hp = g.hp

    # Place enemy right on player
    g.enemies = [Enemy(x=PLAYER_X, y=g.player_y, color=0, hp=1, alive=True)]
    g._update_collisions()
    assert g.hp == initial_hp  # no damage
    # Enemy should still be alive (invincibility doesn't destroy)
    assert g.enemies[0].alive is True


def test_collision_bullet_enemy() -> None:
    """Verify bullet hits enemy at close range."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()

    g.enemies = [Enemy(x=200.0, y=100.0, color=0, hp=1, alive=True)]
    # Place bullet right on top of enemy
    g.bullets = [Bullet(x=200.0, y=100.0, color=0)]

    g._update_collisions()
    assert g.bullets[0].hit is True
    assert g.enemies[0].alive is False


def test_collision_bullet_miss() -> None:
    """Verify bullet far from enemy doesn't hit."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()

    g.enemies = [Enemy(x=200.0, y=100.0, color=0, hp=1, alive=True)]
    # Place bullet far away
    g.bullets = [Bullet(x=50.0, y=200.0, color=0)]

    g._update_collisions()
    assert g.bullets[0].hit is False
    assert g.enemies[0].alive is True


def test_spawn_formation() -> None:
    """Verify _spawn_formation creates enemies."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()

    initial_count = len(g.enemies)
    g._spawn_formation()
    assert len(g.enemies) > initial_count
    # All enemies should be to the right of screen center
    for e in g.enemies:
        assert e.x > SCREEN_W / 2


def test_spawn_timer_creates_formation() -> None:
    """Verify spawn timer triggers formation spawning."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()

    g.spawn_timer = 1  # ready to spawn
    initial_count = len(g.enemies)
    g._update_spawns()
    assert len(g.enemies) > initial_count
    assert g.spawn_timer > 0  # reset to new interval


def test_game_over_on_hp_zero() -> None:
    """Verify game transitions to GAME_OVER when HP reaches 0."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()

    g.hp = 0
    g._hit_player = lambda: None  # no-op to avoid side effects
    g._update_player = lambda: None
    g._update_weapon_cycle = lambda: None
    g._update_echo_orbital = lambda: None
    g._update_shooting = lambda: None
    g._update_bullets = lambda: None
    g._update_enemies = lambda: None
    g._update_spawns = lambda: None
    g._update_collisions = lambda: None
    g._update_particles = lambda: None
    g._update_floating_texts = lambda: None
    g._update_heat = lambda: None
    g._update_stars = lambda: None

    g.update()
    assert g.phase == Phase.GAME_OVER


def test_game_over_on_timer_zero() -> None:
    """Verify game transitions to GAME_OVER when timer reaches 0."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()

    g.game_timer = 0
    # No-op all update methods
    for attr in dir(g):
        if attr.startswith("_update_") and callable(getattr(g, attr)):
            setattr(g, attr, lambda: None)

    g.update()
    assert g.phase == Phase.GAME_OVER


def test_echo_positions_recorded() -> None:
    """Verify player_y is recorded in echo_positions after _update_player."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()

    g.player_y = 150.0
    g._update_player()
    # Last entry should be current player_y
    assert g.echo_positions[-1] == g.player_y


def test_enemy_flash_frames() -> None:
    """Verify flash_frames decrement when enemy is updated."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()

    e = Enemy(x=200.0, y=100.0, color=0, hp=1, alive=True)
    e.flash_frames = 10
    g.enemies = [e]
    g._update_enemies()
    assert g.enemies[0].flash_frames == 9


def test_tank_hp_multiple_hits() -> None:
    """Verify tank enemies require multiple hits to kill."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()

    tank = Enemy(x=200.0, y=100.0, color=0, etype=EnemyType.TANK, hp=3)
    assert tank.hp == 3

    g.combo = 1
    g._hit_enemy(tank, bullet_color=0)
    assert tank.alive is True
    assert tank.hp == 2

    g._hit_enemy(tank, bullet_color=0)
    assert tank.alive is True
    assert tank.hp == 1

    g._hit_enemy(tank, bullet_color=0)
    assert tank.alive is False
    assert tank.hp == 0


def test_score_increases_on_kill() -> None:
    """Verify score increases when enemy is killed."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()

    initial_score = g.score
    e = Enemy(x=200.0, y=100.0, color=1, hp=1, alive=True)
    g.combo = 1
    g._hit_enemy(e, bullet_color=1)
    assert g.score > initial_score


def test_combo_multiplies_score() -> None:
    """Verify higher combo gives higher score."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()

    # Kill at combo 1
    e1 = Enemy(x=200.0, y=100.0, color=0, hp=1, alive=True)
    g.combo = 1
    g._hit_enemy(e1, bullet_color=0)
    score_at_combo1 = g.score

    g2: Game = Game.__new__(Game)
    g2._rng = __import__("random").Random()
    g2.reset()

    # Kill at combo 5
    e2 = Enemy(x=200.0, y=100.0, color=0, hp=1, alive=True)
    g2.combo = 5
    g2._hit_enemy(e2, bullet_color=0)
    score_at_combo5 = g2.score

    assert score_at_combo5 > score_at_combo1


def test_fast_enemy_more_score() -> None:
    """Verify fast enemies give more score than normal."""
    g: Game = Game.__new__(Game)
    g._rng = __import__("random").Random()
    g.reset()

    normal = Enemy(x=200.0, y=100.0, color=0, etype=EnemyType.NORMAL, hp=1, alive=True)
    g.combo = 1
    g._hit_enemy(normal, bullet_color=0)
    normal_score = g.score

    g2: Game = Game.__new__(Game)
    g2._rng = __import__("random").Random()
    g2.reset()

    fast = Enemy(x=200.0, y=100.0, color=0, etype=EnemyType.FAST, hp=1, alive=True)
    g2.combo = 1
    g2._hit_enemy(fast, bullet_color=0)
    fast_score = g2.score

    assert fast_score > normal_score


if __name__ == "__main__":
    import traceback

    tests = [
        ("constants", test_constants),
        ("enums", test_enums),
        ("enemy_defs", test_enemy_defs),
        ("formations", test_formations),
        ("enemy_dataclass", test_enemy_dataclass),
        ("bullet_dataclass", test_bullet_dataclass),
        ("particle_dataclass", test_particle_dataclass),
        ("floating_text_dataclass", test_floating_text_dataclass),
        ("pos_namedtuple", test_pos_namedtuple),
        ("game_reset", test_game_reset),
        ("player_movement_boundaries", test_player_movement_boundaries),
        ("weapon_cycle", test_weapon_cycle),
        ("bullet_movement", test_bullet_movement),
        ("enemy_movement", test_enemy_movement),
        ("particle_lifecycle", test_particle_lifecycle),
        ("floating_text_lifecycle", test_floating_text_lifecycle),
        ("heat_cooling", test_heat_cooling),
        ("heat_clamp", test_heat_clamp),
        ("starfield_init", test_starfield_init),
        ("starfield_movement", test_starfield_movement),
        ("hit_enemy_same_color_builds_combo", test_hit_enemy_same_color_builds_combo),
        ("hit_enemy_wrong_color_resets_combo", test_hit_enemy_wrong_color_resets_combo),
        ("hit_enemy_non_lethal", test_hit_enemy_non_lethal),
        ("max_combo_tracking", test_max_combo_tracking),
        ("chain_burst_triggers_at_threshold", test_chain_burst_triggers_at_threshold),
        ("chain_burst_radius_boundary", test_chain_burst_radius_boundary),
        ("chain_burst_bfs_propagation", test_chain_burst_bfs_propagation),
        ("heat_from_burst", test_heat_from_burst),
        ("hit_player_reduces_hp", test_hit_player_reduces_hp),
        ("hit_player_resets_combo", test_hit_player_resets_combo),
        ("invincibility_prevents_damage", test_invincibility_prevents_damage),
        ("collision_bullet_enemy", test_collision_bullet_enemy),
        ("collision_bullet_miss", test_collision_bullet_miss),
        ("spawn_formation", test_spawn_formation),
        ("spawn_timer_creates_formation", test_spawn_timer_creates_formation),
        ("game_over_on_hp_zero", test_game_over_on_hp_zero),
        ("game_over_on_timer_zero", test_game_over_on_timer_zero),
        ("echo_positions_recorded", test_echo_positions_recorded),
        ("enemy_flash_frames", test_enemy_flash_frames),
        ("tank_hp_multiple_hits", test_tank_hp_multiple_hits),
        ("score_increases_on_kill", test_score_increases_on_kill),
        ("combo_multiplies_score", test_combo_multiplies_score),
        ("fast_enemy_more_score", test_fast_enemy_more_score),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
            print(f"  PASS {name}")
        except Exception as e:
            failed += 1
            print(f"  FAIL {name}: {e}")
            traceback.print_exc()

    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    if failed > 0:
        sys.exit(1)
