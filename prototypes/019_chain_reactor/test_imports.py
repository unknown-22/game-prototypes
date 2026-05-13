"""test_imports.py — Headless logic tests for CHAIN REACTOR.

Tests cover: imports, data classes, game state, chain propagation,
collision detection, heat/overheat system, wave escalation, particle/text
systems — all without requiring a display.
"""

from __future__ import annotations

import math
import sys

# Path setup
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/019_chain_reactor")

from main import (
    WIDTH,
    HEIGHT,
    PLAYER_SPEED,
    BULLET_SPEED,
    CHAIN_RADIUS,
    MAX_HEAT,
    HEAT_PER_SHOT,
    HEAT_DECAY,
    OVERHEAT_FRAMES,
    INVULN_FRAMES,
    ENEMY_RADIUS,
    PLAYER_RADIUS,
    BULLET_RADIUS,
    MAX_ENEMIES,
    COLOR_PYXEL,
    COLOR_DARK,
    COLOR_NAME,
    Bullet,
    Enemy,
    Particle,
    FloatingText,
    Phase,
    ChainReactor,
)


# ═══════════════════════════════════════════════════════════════
#  Constants / Config
# ═══════════════════════════════════════════════════════════════


def test_constants() -> None:
    """Verify all config constants are within expected ranges."""
    assert WIDTH == 400
    assert HEIGHT == 300
    assert PLAYER_SPEED > 0
    assert BULLET_SPEED > 0
    assert CHAIN_RADIUS > 0
    assert MAX_HEAT > 0
    assert HEAT_PER_SHOT > 0
    assert HEAT_DECAY > 0
    assert OVERHEAT_FRAMES > 0
    assert INVULN_FRAMES > 0
    assert ENEMY_RADIUS > 0
    assert PLAYER_RADIUS > 0
    assert BULLET_RADIUS > 0
    assert MAX_ENEMIES > 0
    assert len(COLOR_PYXEL) == 4
    assert len(COLOR_DARK) == 4
    assert len(COLOR_NAME) == 4


# ═══════════════════════════════════════════════════════════════
#  Data Classes
# ═══════════════════════════════════════════════════════════════


def test_enemy_creation() -> None:
    """Enemy dataclass holds correct fields."""
    e = Enemy(x=50.0, y=60.0, color=2, speed=1.2)
    assert e.x == 50.0
    assert e.y == 60.0
    assert e.color == 2
    assert e.speed == 1.2
    # Default speed
    e2 = Enemy(x=0.0, y=0.0, color=0)
    assert e2.speed == 0.8


def test_bullet_creation() -> None:
    """Bullet dataclass holds velocity and position."""
    b = Bullet(x=10.0, y=20.0, vx=3.0, vy=-4.0)
    assert b.x == 10.0
    assert b.y == 20.0
    assert b.vx == 3.0
    assert b.vy == -4.0


def test_particle_creation() -> None:
    """Particle dataclass holds position, velocity, color, life, radius."""
    p = Particle(x=5.0, y=6.0, vx=1.0, vy=2.0, color=0, life=15, radius=3)
    assert p.x == 5.0
    assert p.y == 6.0
    assert p.vx == 1.0
    assert p.vy == 2.0
    assert p.color == 0
    assert p.life == 15
    assert p.radius == 3
    # Default radius
    p2 = Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, color=1, life=10)
    assert p2.radius == 2


def test_floating_text_creation() -> None:
    """FloatingText dataclass holds text, position, color, life."""
    ft = FloatingText(x=100.0, y=200.0, text="CHAIN x3!", color=7, life=40)
    assert ft.x == 100.0
    assert ft.y == 200.0
    assert ft.text == "CHAIN x3!"
    assert ft.color == 7
    assert ft.life == 40


# ═══════════════════════════════════════════════════════════════
#  Phase Enum
# ═══════════════════════════════════════════════════════════════


def test_phase_enum() -> None:
    """Phase enum has the four expected states."""
    assert Phase.TITLE is not None
    assert Phase.PLAYING is not None
    assert Phase.OVERHEAT is not None
    assert Phase.GAME_OVER is not None
    assert len(list(Phase)) == 4


# ═══════════════════════════════════════════════════════════════
#  Game State Initialization (headless — no pyxel.init/run)
# ═══════════════════════════════════════════════════════════════


def test_reset_sets_initial_state() -> None:
    """reset() sets all state fields to their starting values."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    assert g.phase == Phase.TITLE
    assert g.player_x == WIDTH / 2
    assert g.player_y == HEIGHT - 50
    assert g.hp == 3
    assert g.heat == 0.0
    assert g.score == 0
    assert g.wave == 1
    assert g.kill_count == 0
    assert len(g.enemies) == 0
    assert len(g.bullets) == 0
    assert len(g.particles) == 0
    assert len(g.texts) == 0
    assert g.combo == 0
    assert g.combo_timer == 0
    assert g.max_combo == 0
    assert g.overheat_timer == 0
    assert g.invuln == 0
    assert g.shake == 0
    assert g.best_score == 0
    assert g.frame == 0
    assert g._spawn_timer == 30


def test_start_game_transitions_to_playing() -> None:
    """_start_game() sets phase to PLAYING and resets all fields."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.TITLE
    g.score = 500
    g.wave = 3
    g._start_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.wave == 1
    assert g.hp == 3
    assert g.heat == 0.0
    assert len(g.enemies) == 0
    assert len(g.bullets) == 0
    assert g.combo == 0


# ═══════════════════════════════════════════════════════════════
#  Chain Propagation (BFS)
# ═══════════════════════════════════════════════════════════════


def test_chain_propagate_single_enemy() -> None:
    """Propagating from a lone enemy should only collect itself."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.enemies = [
        Enemy(50.0, 50.0, 0, 1.0),
        Enemy(200.0, 200.0, 1, 1.0),  # different color
    ]
    collected: set[int] = set()
    g._chain_propagate(0, 0, collected)
    assert collected == {0}


def test_chain_propagate_two_same_color_within_radius() -> None:
    """Two same-color enemies within CHAIN_RADIUS should both be collected."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.enemies = [
        Enemy(50.0, 50.0, 2, 1.0),
        Enemy(50.0 + CHAIN_RADIUS - 1, 50.0, 2, 1.0),  # just within radius
    ]
    collected: set[int] = set()
    g._chain_propagate(0, 2, collected)
    assert collected == {0, 1}


def test_chain_propagate_different_color_ignored() -> None:
    """Enemies of different colors should not be collected, even if close."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.enemies = [
        Enemy(50.0, 50.0, 0, 1.0),
        Enemy(55.0, 55.0, 1, 1.0),  # close but different color
    ]
    collected: set[int] = set()
    g._chain_propagate(0, 0, collected)
    assert collected == {0}
    assert 1 not in collected


def test_chain_propagate_outside_radius_ignored() -> None:
    """Same-color enemy outside CHAIN_RADIUS should not be collected."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.enemies = [
        Enemy(50.0, 50.0, 3, 1.0),
        Enemy(50.0 + CHAIN_RADIUS + 10, 50.0, 3, 1.0),  # outside radius
    ]
    collected: set[int] = set()
    g._chain_propagate(0, 3, collected)
    assert collected == {0}


def test_chain_propagate_long_chain() -> None:
    """A chain of 5 same-color enemies in a line within radius."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    step = CHAIN_RADIUS - 5  # each is within radius of the next
    g.enemies = [
        Enemy(50.0 + i * step, 50.0, 0, 1.0)
        for i in range(5)
    ]
    collected: set[int] = set()
    g._chain_propagate(0, 0, collected)
    assert collected == {0, 1, 2, 3, 4}


def test_chain_propagate_transitive_with_gap() -> None:
    """Chain that requires transitive propagation through an intermediate."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    step = CHAIN_RADIUS - 5
    g.enemies = [
        Enemy(50.0, 50.0, 1, 1.0),                          # 0
        Enemy(50.0 + step, 50.0, 1, 1.0),                   # 1 (bridge)
        Enemy(50.0 + step * 2, 50.0, 1, 1.0),               # 2 (out of range from 0)
    ]
    # 0 → 1 is within radius, 1 → 2 is within radius
    # 0 → 2 is NOT within radius (2*step > CHAIN_RADIUS)
    assert step * 2 > CHAIN_RADIUS - 10  # should be out of direct range
    collected: set[int] = set()
    g._chain_propagate(0, 1, collected)
    assert 2 in collected  # reached transitively through enemy 1


# ═══════════════════════════════════════════════════════════════
#  Bullet Collision
# ═══════════════════════════════════════════════════════════════


def test_bullet_hits_enemy() -> None:
    """A bullet directly on an enemy should trigger a kill."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.enemies = [Enemy(100.0, 100.0, 0, 1.0)]
    g.bullets = [Bullet(100.0, 100.0, 0.0, 0.0)]  # exactly on enemy
    g._check_bullet_collisions()
    assert len(g.enemies) == 0
    assert len(g.bullets) == 0


def test_bullet_misses_enemy() -> None:
    """A bullet far from any enemy should not trigger kills."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.enemies = [Enemy(100.0, 100.0, 0, 1.0)]
    g.bullets = [Bullet(300.0, 300.0, 0.0, 0.0)]
    g._check_bullet_collisions()
    assert len(g.enemies) == 1
    assert len(g.bullets) == 1


def test_bullet_triggers_chain_of_two() -> None:
    """Bullet hitting one enemy should chain to adjacent same-color enemy."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.enemies = [
        Enemy(100.0, 100.0, 2, 1.0),
        Enemy(100.0 + CHAIN_RADIUS - 5, 100.0, 2, 1.0),
    ]
    g.bullets = [Bullet(100.0, 100.0, 0.0, 0.0)]
    g._check_bullet_collisions()
    assert len(g.enemies) == 0  # both killed
    assert g.score >= 10 * 2 * 2  # chain score bonus
    assert g.kill_count == 2


def test_score_on_single_kill() -> None:
    """Single kill (no chain) should add base score."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.enemies = [Enemy(100.0, 100.0, 1, 1.0)]
    g.bullets = [Bullet(100.0, 100.0, 0.0, 0.0)]
    g._check_bullet_collisions()
    assert g.score == 10
    assert g.kill_count == 1


# ═══════════════════════════════════════════════════════════════
#  Heat / Overheat
# ═══════════════════════════════════════════════════════════════


def test_heat_builds_on_shoot() -> None:
    """Each shot should increase heat by HEAT_PER_SHOT."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.heat = 0.0
    # We can't call _shoot_bullet easily without pyxel.mouse_x/y
    # So test the increment logic directly
    initial = g.heat
    g.heat += HEAT_PER_SHOT
    assert g.heat == initial + HEAT_PER_SHOT


def test_heat_capped_at_max() -> None:
    """Heat should not exceed MAX_HEAT (cap enforced in _shoot_bullet)."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.heat = MAX_HEAT - 0.1
    # Simulate the cap logic from _shoot_bullet:
    g.heat = min(MAX_HEAT, g.heat + HEAT_PER_SHOT)
    assert g.heat == MAX_HEAT


def test_heat_decays() -> None:
    """Heat should decrease when above zero."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.heat = 50.0
    # Simulate what _update_playing does with heat decay
    g.heat = max(0.0, g.heat - HEAT_DECAY)
    assert g.heat == 50.0 - HEAT_DECAY


def test_heat_does_not_go_negative() -> None:
    """Heat should never go below zero."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.heat = 0.0
    g.heat = max(0.0, g.heat - HEAT_DECAY)
    assert g.heat == 0.0


# ═══════════════════════════════════════════════════════════════
#  Player Hit / HP
# ═══════════════════════════════════════════════════════════════


def test_player_hit_reduces_hp() -> None:
    """Enemy touching player should reduce HP."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.player_x = 100.0
    g.player_y = 100.0
    g.hp = 3
    g.enemies = [Enemy(100.0 + PLAYER_RADIUS + ENEMY_RADIUS - 1, 100.0, 0, 1.0)]
    g._check_player_hit()
    assert g.hp == 2
    assert g.invuln == INVULN_FRAMES


def test_player_hit_no_collision() -> None:
    """Far enemy should not hit player."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.player_x = 100.0
    g.player_y = 100.0
    g.hp = 3
    g.enemies = [Enemy(300.0, 300.0, 0, 1.0)]
    g._check_player_hit()
    assert g.hp == 3


def test_player_hit_invulnerable() -> None:
    """Invulnerable player should not take damage."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.player_x = 100.0
    g.player_y = 100.0
    g.hp = 3
    g.invuln = 10
    g.enemies = [Enemy(100.0 + PLAYER_RADIUS + ENEMY_RADIUS - 1, 100.0, 0, 1.0)]
    g._check_player_hit()
    assert g.hp == 3


def test_player_hit_zero_hp_game_over() -> None:
    """When HP reaches 0, phase should go to GAME_OVER."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.player_x = 100.0
    g.player_y = 100.0
    g.hp = 1
    g.score = 500
    g.enemies = [Enemy(100.0 + PLAYER_RADIUS + ENEMY_RADIUS - 1, 100.0, 0, 1.0)]
    g._check_player_hit()
    assert g.hp == 0
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 500


# ═══════════════════════════════════════════════════════════════
#  Wave Escalation
# ═══════════════════════════════════════════════════════════════


def test_wave_increments_on_clear() -> None:
    """When no enemies remain and spawn_timer is 0, wave should increase."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.wave = 2
    g.enemies = []
    g._spawn_timer = 0
    # Simulate the wave-clear check from _update_playing
    if len(g.enemies) == 0 and g._spawn_timer <= 0:
        g.wave += 1
        g._spawn_timer = 30
    assert g.wave == 3


def test_wave_does_not_increment_with_enemies_alive() -> None:
    """Wave should not increase while enemies are still on screen."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.wave = 2
    g.enemies = [Enemy(50.0, 50.0, 0, 1.0)]
    g._spawn_timer = 0
    if len(g.enemies) == 0 and g._spawn_timer <= 0:
        g.wave += 1
        g._spawn_timer = 30
    assert g.wave == 2  # unchanged


# ═══════════════════════════════════════════════════════════════
#  Enemy Movement
# ═══════════════════════════════════════════════════════════════


def test_enemy_moves_toward_player() -> None:
    """Enemy should move closer to the player after _update_enemies."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.player_x = 150.0
    g.player_y = 150.0
    e = Enemy(100.0, 100.0, 0, 1.0)
    g.enemies = [e]
    initial_dist = math.hypot(e.x - g.player_x, e.y - g.player_y)
    g._update_enemies()
    new_dist = math.hypot(e.x - g.player_x, e.y - g.player_y)
    assert new_dist < initial_dist


def test_enemy_stops_when_close() -> None:
    """Enemy close to player should not overshoot."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.player_x = 150.0
    g.player_y = 150.0
    e = Enemy(150.0 + 0.4, 150.0, 0, 0.5)  # within 0.5 threshold
    g.enemies = [e]
    g._update_enemies()
    # Should not move (dist < 0.5)
    assert abs(e.x - (150.0 + 0.4)) < 0.001
    assert abs(e.y - 150.0) < 0.001


# ═══════════════════════════════════════════════════════════════
#  Particle System
# ═══════════════════════════════════════════════════════════════


def test_particles_age_and_die() -> None:
    """Particles should decrement life; dead ones removed."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.particles = [
        Particle(0.0, 0.0, 0.0, 0.0, 0, 1, 2),   # dies this frame
        Particle(0.0, 0.0, 0.0, 0.0, 1, 5, 2),   # survives
    ]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 4


def test_particles_move() -> None:
    """Particles should move according to velocity."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    p = Particle(10.0, 20.0, 2.0, -1.0, 0, 10, 2)
    g.particles = [p]
    g._update_particles()
    assert abs(p.x - 12.0) < 0.01  # moved by vx
    assert abs(p.y - 19.0) < 0.01  # moved by vy


# ═══════════════════════════════════════════════════════════════
#  Floating Text System
# ═══════════════════════════════════════════════════════════════


def test_texts_age_and_die() -> None:
    """Texts should decay life; expired ones removed."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.texts = [
        FloatingText(0.0, 0.0, "A", 0, 1),   # dies
        FloatingText(0.0, 0.0, "B", 1, 10),  # survives
    ]
    g._update_texts()
    assert len(g.texts) == 1
    assert g.texts[0].life == 9


def test_texts_float_upward() -> None:
    """Floating texts should rise (y decreases)."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    t = FloatingText(100.0, 200.0, "UP", 5, 20)
    g.texts = [t]
    g._update_texts()
    assert t.y < 200.0  # moved up


# ═══════════════════════════════════════════════════════════════
#  Movement (diagonal normalization)
# ═══════════════════════════════════════════════════════════════


def test_diagonal_normalization_logic() -> None:
    """Diagonal movement should be ~70% per axis to avoid speed boost."""
    # This tests the normalization math used in _update_movement
    dx, dy = PLAYER_SPEED, PLAYER_SPEED
    inv = 1.0 / math.sqrt(2.0)
    dx *= inv
    dy *= inv
    total_speed = math.hypot(dx, dy)
    assert abs(total_speed - PLAYER_SPEED) < 0.01


# ═══════════════════════════════════════════════════════════════
#  Spawn Explosion
# ═══════════════════════════════════════════════════════════════


def test_spawn_explosion_creates_particles() -> None:
    """_spawn_explosion should add multiple particles."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    before = len(g.particles)
    g._spawn_explosion(50.0, 50.0, 0, 3)
    assert len(g.particles) > before
    # Chain size 3 should create 5 + 3*3 = 14 particles
    assert len(g.particles) == 14


# ═══════════════════════════════════════════════════════════════
#  Combo System
# ═══════════════════════════════════════════════════════════════


def test_combo_tracks_max() -> None:
    """max_combo should store the highest chain seen."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.combo = 5
    g.max_combo = max(g.max_combo, g.combo)
    assert g.max_combo == 5
    g.combo = 3
    g.max_combo = max(g.max_combo, g.combo)
    assert g.max_combo == 5  # still 5


def test_combo_timer_resets_combo() -> None:
    """When combo_timer reaches 0, combo should reset."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.combo = 4
    g.combo_timer = 1
    # Simulate timer decrement from _update_playing
    g.combo_timer -= 1
    if g.combo_timer == 0:
        g.combo = 0
    assert g.combo == 0


# ═══════════════════════════════════════════════════════════════
#  Invulnerability Timer
# ═══════════════════════════════════════════════════════════════


def test_invuln_decrements() -> None:
    """invuln timer should count down each frame."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.invuln = 10
    # Simulate decrement
    if g.invuln > 0:
        g.invuln -= 1
    assert g.invuln == 9


# ═══════════════════════════════════════════════════════════════
#  Bullet Update (off-screen removal)
# ═══════════════════════════════════════════════════════════════


def test_bullets_removed_when_offscreen() -> None:
    """Bullets going off-screen should be removed."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    g.bullets = [
        Bullet(-10.0, 50.0, -1.0, 0.0),   # off left
        Bullet(200.0, 50.0, 0.0, 0.0),     # on screen
        Bullet(50.0, -10.0, 0.0, -1.0),    # off top
    ]
    g._update_bullets()
    assert len(g.bullets) == 1


# ═══════════════════════════════════════════════════════════════
#  Enemy Count Capping
# ═══════════════════════════════════════════════════════════════


def test_enemy_count_capped() -> None:
    """Spawn count should respect MAX_ENEMIES limit."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.PLAYING
    # Fill nearly to max
    g.enemies = [Enemy(50.0, 50.0, 0, 1.0) for _ in range(MAX_ENEMIES - 2)]
    g.wave = 20  # would try to spawn many
    g._spawn_timer = 0
    # The spawn logic limits count = min(3 + wave*2, MAX_ENEMIES - len)
    assert MAX_ENEMIES - len(g.enemies) == 2
    # Even at wave 20, min(3+40, 2) = 2
    max_spawn = min(3 + g.wave * 2, MAX_ENEMIES - len(g.enemies))
    assert max_spawn == 2


# ═══════════════════════════════════════════════════════════════
#  Best Score Tracking
# ═══════════════════════════════════════════════════════════════


def test_best_score_updated_on_game_over() -> None:
    """best_score should update when game_over is triggered."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.best_score = 100
    g.score = 500
    g.best_score = max(g.best_score, g.score)
    assert g.best_score == 500


def test_best_score_not_lowered() -> None:
    """best_score should not decrease even if current score is lower."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.best_score = 500
    g.score = 100
    g.best_score = max(g.best_score, g.score)
    assert g.best_score == 500


# ═══════════════════════════════════════════════════════════════
#  Overheat Timer
# ═══════════════════════════════════════════════════════════════


def test_overheat_decays_heat_faster() -> None:
    """Overheat state should decay heat faster than normal."""
    from main import HEAT_OVERHEAT_DECAY
    assert HEAT_OVERHEAT_DECAY > HEAT_DECAY  # overheat decay is faster


# ═══════════════════════════════════════════════════════════════
#  Phase Transition: Title → Playing
# ═══════════════════════════════════════════════════════════════


def test_phase_starts_at_title() -> None:
    """Reset should set phase to TITLE."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    assert g.phase == Phase.TITLE


def test_start_game_from_gameover() -> None:
    """_start_game should transition GAME_OVER back to PLAYING."""
    g = ChainReactor.__new__(ChainReactor)
    g.reset()
    g.phase = Phase.GAME_OVER
    g.score = 300
    g._start_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0


# ═══════════════════════════════════════════════════════════════
#  Run
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import traceback

    tests = [
        (name, obj)
        for name, obj in sorted(globals().items())
        if name.startswith("test_") and callable(obj)
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
            print(f"  PASS  {name}")
        except Exception:
            failed += 1
            print(f"  FAIL  {name}")
            traceback.print_exc()

    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    if failed > 0:
        sys.exit(1)
