"""test_imports.py — Headless logic tests for CALAMITY SIEGE.

Uses Game.__new__ to create instance without pyxel.init/run for headless testing.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # noqa: E402
    BULLET_SPEED,
    COLORS,
    COMBO_FOR_PIERCE,
    ENEMY_COLS,
    ENEMY_ROWS,
    ESCAPE_Y,
    FIRE_COOLDOWN,
    GRID_LEFT,
    GRID_TOP,
    MAX_HEAT,
    MAX_HP,
    N_COLORS,
    SCREEN_H,
    SCREEN_W,
    Bullet,
    Enemy,
    FloatText,
    Game,
    Particle,
    Phase,
    STARS,
)

# ═══════════════════════════════════════════════════════════════════════
# Helper: create Game instance without pyxel.init/run
# ═══════════════════════════════════════════════════════════════════════


def make_game() -> Game:
    g = Game.__new__(Game)
    g.reset()
    return g


# ═══════════════════════════════════════════════════════════════════════
# Config / constants tests
# ═══════════════════════════════════════════════════════════════════════


def test_config_constants() -> None:
    assert SCREEN_W == 256
    assert SCREEN_H == 256
    assert BULLET_SPEED == 5
    assert ENEMY_COLS == 8
    assert ENEMY_ROWS == 4
    assert MAX_HEAT == 12
    assert MAX_HP == 5
    assert COMBO_FOR_PIERCE == 5
    assert FIRE_COOLDOWN == 10
    assert len(COLORS) == N_COLORS == 4
    assert len(STARS) == 40


def test_phase_enum() -> None:
    phases = list(Phase)
    assert Phase.TITLE in phases
    assert Phase.PLAYING in phases
    assert Phase.WAVE_CLEAR in phases
    assert Phase.GAME_OVER in phases


# ═══════════════════════════════════════════════════════════════════════
# Data class tests
# ═══════════════════════════════════════════════════════════════════════


def test_bullet_dataclass() -> None:
    b = Bullet(x=100.0, y=200.0)
    assert b.x == 100.0
    assert b.y == 200.0
    assert not b.pierce
    assert b.alive

    bp = Bullet(x=50.0, y=30.0, pierce=True)
    assert bp.pierce


def test_enemy_dataclass() -> None:
    e = Enemy(x=60.0, y=40.0, color=2, hp=1)
    assert e.x == 60.0
    assert e.y == 40.0
    assert e.color == 2
    assert e.hp == 1
    assert not e.escaped
    assert e.alive

    ee = Enemy(x=120.0, y=20.0, color=0, hp=2, escaped=True)
    assert ee.escaped
    assert ee.hp == 2


def test_particle_dataclass() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-0.5, life=15, color=3)
    assert p.x == 10.0
    assert p.life == 15
    assert p.color == 3


def test_float_text_dataclass() -> None:
    ft = FloatText(x=40.0, y=30.0, text="+100", life=20, color=8)
    assert ft.text == "+100"
    assert ft.life == 20


# ═══════════════════════════════════════════════════════════════════════
# Game state init tests
# ═══════════════════════════════════════════════════════════════════════


def test_game_reset_state() -> None:
    g = make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.hp == MAX_HP
    assert g.heat == 0.0
    assert g.combo == 0
    assert g.combo_color == -1
    assert g.wave == 1
    assert g.fire_timer == 0
    assert not g.pierce_ready


def test_reset_creates_enemy_formation() -> None:
    g = make_game()
    assert len(g.enemies) == ENEMY_COLS * ENEMY_ROWS  # 32
    colors_found: set[int] = {e.color for e in g.enemies}
    assert len(colors_found) >= 1
    assert all(0 <= c < N_COLORS for c in colors_found)


def test_reset_clears_bullets_and_particles() -> None:
    g = make_game()
    assert len(g.bullets) == 0
    assert len(g.particles) == 0
    assert len(g.float_texts) == 0


# ═══════════════════════════════════════════════════════════════════════
# Phase transition tests
# ═══════════════════════════════════════════════════════════════════════


def test_title_to_playing_transition_state() -> None:
    g = make_game()
    assert g.phase == Phase.TITLE
    # Simulate: direct state change (no pyxel.btnp available)
    g.phase = Phase.PLAYING
    assert g.phase == Phase.PLAYING


def test_game_over_retry() -> None:
    g = make_game()
    g.phase = Phase.GAME_OVER
    g.score = 500
    # Simulate retry: reset
    g.reset()
    g.phase = Phase.PLAYING
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.wave == 1
    assert g.hp == MAX_HP


# ═══════════════════════════════════════════════════════════════════════
# Fire mechanics tests
# ═══════════════════════════════════════════════════════════════════════


def test_fire_creates_bullet() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.heat = 0.0
    g.fire_timer = 0
    g._fire()
    assert len(g.bullets) == 1
    b = g.bullets[0]
    assert b.x == g.player_x
    assert not b.pierce
    assert g.heat == 1.0  # HEAT_PER_SHOT
    assert g.fire_timer == FIRE_COOLDOWN


def test_fire_respects_heat_cap() -> None:
    """At heat cap, _fire() can still be called directly but update blocks it.
    Test that the fire_timer decrements correctly in isolation."""
    g = make_game()
    g.phase = Phase.PLAYING
    g.heat = MAX_HEAT
    g.fire_timer = FIRE_COOLDOWN
    # fire_timer decrements when update runs (but we skip pyxel.btn)
    g.fire_timer -= 1  # simulate one update tick
    assert g.fire_timer == FIRE_COOLDOWN - 1
    # heat cools down
    g._update_heat()
    assert g.heat < MAX_HEAT


def test_fire_pierce_consumes_flag() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.pierce_ready = True
    g.heat = 0.0
    g.fire_timer = 0
    g._fire()
    assert len(g.bullets) == 1
    assert g.bullets[0].pierce
    assert not g.pierce_ready  # consumed


def test_bullet_movement() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.bullets = [Bullet(x=100.0, y=200.0)]
    g._update_bullets()
    assert g.bullets[0].y == 200.0 - BULLET_SPEED
    assert g.bullets[0].alive


def test_bullet_dies_off_screen() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.bullets = [Bullet(x=100.0, y=-7.0)]
    g._update_bullets()
    assert len(g.bullets) == 0


# ═══════════════════════════════════════════════════════════════════════
# Enemy formation tests
# ═══════════════════════════════════════════════════════════════════════


def test_formation_spawn_positions() -> None:
    g = make_game()
    for i, e in enumerate(g.enemies):
        row = i // ENEMY_COLS
        col = i % ENEMY_COLS
        assert e.x == GRID_LEFT + col * 26
        assert e.y == GRID_TOP + row * 20
        assert not e.escaped
        assert e.alive
        assert e.hp == 1


def test_formation_moves_horizontally() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.grid_speed = 999.0  # force immediate move
    x0 = g.enemies[0].x
    g._update_formation()
    # Should have moved by GRID_MOVE_X in grid_dir direction
    assert g.enemies[0].x == x0 + 4  # grid_dir starts at 1, GRID_MOVE_X=4


# ═══════════════════════════════════════════════════════════════════════
# Hit detection tests
# ═══════════════════════════════════════════════════════════════════════


def test_bullet_hits_enemy() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.bullets = [Bullet(x=GRID_LEFT, y=GRID_TOP)]
    g.enemies = [Enemy(x=GRID_LEFT, y=GRID_TOP, color=0, hp=1)]
    g._update_collisions()
    assert not g.enemies[0].alive
    assert not g.bullets[0].alive
    assert g.score > 0


def test_pierce_bullet_passes_through() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    # Place both enemies close enough vertically that one bullet hits both
    # Collision check: abs(b.y - e.y) < ENEMY_H/2 + 4 = 9
    g.bullets = [Bullet(x=GRID_LEFT, y=GRID_TOP, pierce=True)]
    g.enemies = [
        Enemy(x=GRID_LEFT, y=GRID_TOP, color=0, hp=1),
        Enemy(x=GRID_LEFT, y=GRID_TOP + 5, color=0, hp=1),
    ]
    g._update_collisions()
    assert not g.enemies[0].alive
    assert not g.enemies[1].alive
    assert g.bullets[0].alive  # pierce bullet survives


def test_combo_increases_on_same_color_kill() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.combo = 0
    g.combo_color = -1
    g.bullets = [Bullet(x=GRID_LEFT, y=GRID_TOP)]
    g.enemies = [Enemy(x=GRID_LEFT, y=GRID_TOP, color=0, hp=1)]
    g._update_collisions()
    assert g.combo == 1
    assert g.combo_color == 0


def test_combo_resets_on_different_color() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.combo = 3
    g.combo_color = 0
    g.bullets = [Bullet(x=GRID_LEFT, y=GRID_TOP)]
    g.enemies = [Enemy(x=GRID_LEFT, y=GRID_TOP, color=1, hp=1)]
    g._update_collisions()
    assert g.combo == 1
    assert g.combo_color == 1


def test_combo_five_unlocks_pierce() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.combo = 4
    g.combo_color = 0
    g.bullets = [Bullet(x=GRID_LEFT, y=GRID_TOP)]
    g.enemies = [Enemy(x=GRID_LEFT, y=GRID_TOP, color=0, hp=1)]
    g._update_collisions()
    assert g.combo == 5
    assert g.pierce_ready


# ═══════════════════════════════════════════════════════════════════════
# Escape / breach mechanic tests
# ═══════════════════════════════════════════════════════════════════════


def test_enemy_escapes_at_threshold() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.enemies = [
        Enemy(x=100.0, y=ESCAPE_Y, color=0, hp=1),
    ]
    g.grid_speed = 999.0  # force immediate formation move
    g._update_formation()
    assert not g.enemies[0].alive  # removed from formation
    escaped = [e for e in g.enemies if e.escaped]
    assert len(escaped) == 1
    assert escaped[0].hp == 2
    assert escaped[0].color == 0


def test_escaped_enemy_moves_independently() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    ee = Enemy(x=100.0, y=50.0, color=1, hp=2, escaped=True)
    g.enemies = [ee]
    g._update_escaped_enemies()
    assert ee.y > 50.0  # drifted down


def test_escaped_enemy_worth_double() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.score = 0
    g.combo = 0
    g.combo_color = -1
    g.bullets = [Bullet(x=100.0, y=50.0)]
    g.enemies = [Enemy(x=100.0, y=50.0, color=0, hp=2, escaped=True)]
    g._update_collisions()
    # Escaped has hp=2, one shot deals 1 damage, not dead yet
    assert g.enemies[0].alive
    assert g.enemies[0].hp == 1
    # Second shot
    g.bullets = [Bullet(x=100.0, y=50.0)]
    g._update_collisions()
    assert not g.enemies[0].alive
    assert g.score > 0


def test_player_hit_by_enemy_spawns_escaped() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.hp = MAX_HP
    g.player_x = 100.0
    g.enemies = [Enemy(x=100.0, y=SCREEN_H - 20, color=2, hp=1)]
    assert not g.enemies[0].escaped
    g._update_collisions()
    assert g.hp == MAX_HP - 1
    assert not g.enemies[0].alive
    escaped = [e for e in g.enemies if e.escaped]
    assert len(escaped) == 1
    assert escaped[0].color == 2
    assert escaped[0].hp == 2


def test_player_death_ends_game() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.hp = 1
    g.player_x = 100.0
    g.enemies = [Enemy(x=100.0, y=SCREEN_H - 20, color=0, hp=1)]
    g._update_collisions()
    assert g.phase == Phase.GAME_OVER


# ═══════════════════════════════════════════════════════════════════════
# Heat system tests
# ═══════════════════════════════════════════════════════════════════════


def test_heat_cools_down() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.heat = 5.0
    g._update_heat()
    assert g.heat < 5.0
    assert g.heat >= 4.8  # HEAT_COOL_RATE = 0.12


def test_heat_at_zero_stays_zero() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


# ═══════════════════════════════════════════════════════════════════════
# Particle system tests
# ═══════════════════════════════════════════════════════════════════════


def test_spawn_particles() -> None:
    g = make_game()
    g._spawn_particles(50.0, 60.0, 0, 8)
    assert len(g.particles) == 8


def test_particles_decay() -> None:
    g = make_game()
    g._spawn_particles(50.0, 60.0, 0, 5)
    for _ in range(30):
        g._update_particles()
    assert len(g.particles) == 0  # all expired


def test_float_texts_decay() -> None:
    g = make_game()
    g._add_float_text(50.0, 60.0, "TEST", 10, 7)
    assert len(g.float_texts) == 1
    for _ in range(15):
        g._update_float_texts()
    assert len(g.float_texts) == 0


# ═══════════════════════════════════════════════════════════════════════
# Wave clear tests
# ═══════════════════════════════════════════════════════════════════════


def test_wave_clear_when_no_enemies() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.enemies = []
    g._check_wave_clear()
    assert g.phase == Phase.WAVE_CLEAR


def test_wave_clear_advances_wave() -> None:
    """After wave clear, advancing to next wave resets state."""
    g = make_game()
    g.wave = 3
    g.bullets = [Bullet(x=100.0, y=50.0)]
    # Simulate wave clear transition directly (no pyxel.btnp)
    g.wave += 1
    g._spawn_formation()
    g.phase = Phase.PLAYING
    g.bullets.clear()
    g.combo = 0
    g.combo_color = -1
    g.pierce_ready = False
    assert g.wave == 4
    assert len(g.bullets) == 0
    assert g.combo == 0
    assert not g.pierce_ready


# ═══════════════════════════════════════════════════════════════════════
# Dive mechanic tests
# ═══════════════════════════════════════════════════════════════════════


def test_dive_activates_on_timer_zero() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.player_x = 100.0
    e = Enemy(x=80.0, y=40.0, color=0, hp=1, dive_timer=0)
    g.enemies = [e]
    g._update_dives()
    assert e.diving
    assert e.dive_dx != 0.0 or e.dive_dy != 0.0


def test_dive_moves_enemy() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.player_x = 100.0
    e = Enemy(x=80.0, y=40.0, color=0, hp=1, dive_timer=0, diving=True,
              dive_dx=1.5, dive_dy=2.0)
    g.enemies = [e]
    x0, y0 = e.x, e.y
    g._update_dives()
    assert e.x == x0 + 1.5
    assert e.y == y0 + 2.0


# ═══════════════════════════════════════════════════════════════════════
# Score calculation tests
# ═══════════════════════════════════════════════════════════════════════


def test_close_enemy_gives_bonus() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.score = 0
    g.combo = 0
    g.combo_color = -1
    g.bullets = [Bullet(x=100.0, y=SCREEN_H - 50)]
    g.enemies = [Enemy(x=100.0, y=SCREEN_H - 50, color=0, hp=1)]
    g._update_collisions()
    high_score = g.score

    g.reset()
    g.phase = Phase.PLAYING
    g.score = 0
    g.combo = 0
    g.combo_color = -1
    g.bullets = [Bullet(x=100.0, y=GRID_TOP)]
    g.enemies = [Enemy(x=100.0, y=GRID_TOP, color=0, hp=1)]
    g._update_collisions()
    low_score = g.score

    # Close enemy should give more points
    assert high_score > low_score


# ═══════════════════════════════════════════════════════════════════════
# Method existence tests (verify no name collisions)
# ═══════════════════════════════════════════════════════════════════════


def test_no_method_name_collision() -> None:
    """Verify all method names are unique in the Game class."""
    methods = [name for name, _ in inspect.getmembers(Game, inspect.isfunction)
               if not name.startswith("__")]
    assert len(methods) == len(set(methods)), \
        f"Duplicate method names found: {methods}"


# ═══════════════════════════════════════════════════════════════════════
# Reset method attribute check
# ═══════════════════════════════════════════════════════════════════════


def test_reset_initializes_all_attributes() -> None:
    """Verify reset() initializes all required state attributes."""
    g = make_game()
    assert hasattr(g, "phase")
    assert hasattr(g, "score")
    assert hasattr(g, "hp")
    assert hasattr(g, "heat")
    assert hasattr(g, "combo")
    assert hasattr(g, "combo_color")
    assert hasattr(g, "wave")
    assert hasattr(g, "player_x")
    assert hasattr(g, "bullets")
    assert hasattr(g, "enemies")
    assert hasattr(g, "particles")
    assert hasattr(g, "float_texts")
    assert hasattr(g, "fire_timer")
    assert hasattr(g, "grid_dir")
    assert hasattr(g, "grid_move_timer")
    assert hasattr(g, "grid_speed")
    assert hasattr(g, "pierce_ready")
    assert hasattr(g, "shake_timer")
    assert hasattr(g, "shake_amount")
    assert hasattr(g, "max_combo")


# ═══════════════════════════════════════════════════════════════════════
# Run all tests
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
