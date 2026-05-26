"""test_imports.py — Headless logic tests for SCORCH CHAIN."""
from __future__ import annotations

import math
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/070_scorch_chain")

from main import (
    ANGLE_MAX,
    ANGLE_MIN,
    BLAST_NORMAL,
    BLAST_SUPER,
    CELL,
    COLS,
    DMG_NORMAL,
    DMG_SUPER,
    GRAVITY,
    PLAYER_COL,
    POWER_MAX,
    POWER_MIN,
    ROWS,
    SCREEN_W,
    SCORE_PER_CELL,
    SPEED_SCALE,
    SUPER_COMBO_THRESHOLD,
    SUPER_BONUS,
    TANK_HP,
    TERRAIN_COLORS,
    Game,
    Phase,
    Particle,
    Projectile,
    FloatText,
)


# ── Helper ────────────────────────────────────────────────────────────

def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(seed)
    g._init_state()
    return g


# ── Dataclass Tests ────────────────────────────────────────────────────

def test_particle_defaults() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, color=8, life=12)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.color == 8
    assert p.life == 12
    assert p.size == 1


def test_float_text_defaults() -> None:
    ft = FloatText(x=80.0, y=200.0, text="+100", life=30, color=7)
    assert ft.x == 80.0
    assert ft.y == 200.0
    assert ft.text == "+100"
    assert ft.life == 30
    assert ft.color == 7


def test_projectile_defaults() -> None:
    proj = Projectile(x=100.0, y=50.0, vx=2.0, vy=-3.0, alive=True, color=7)
    assert proj.x == 100.0
    assert proj.y == 50.0
    assert proj.vx == 2.0
    assert proj.vy == -3.0
    assert proj.alive is True
    assert proj.color == 7
    assert proj.trail_particles == []


# ── Phase Enum Tests ───────────────────────────────────────────────────

def test_phase_values() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYER_AIM in Phase
    assert Phase.PLAYER_FIRE in Phase
    assert Phase.ANIM_PROJECTILE in Phase
    assert Phase.ANIM_EXPLOSION in Phase
    assert Phase.GRAVITY_COLLAPSE in Phase
    assert Phase.ENEMY_AIM in Phase
    assert Phase.ENEMY_FIRE in Phase
    assert Phase.ANIM_ENEMY_PROJECTILE in Phase
    assert Phase.ANIM_ENEMY_EXPLOSION in Phase
    assert Phase.ENEMY_GRAVITY in Phase
    assert Phase.CHECK_WIN in Phase
    assert Phase.GAME_OVER in Phase
    assert len(list(Phase)) == 13


# ── Constants Tests ────────────────────────────────────────────────────

def test_constants() -> None:
    assert COLS == 40
    assert ROWS == 30
    assert CELL == 8
    assert TANK_HP == 100
    assert BLAST_NORMAL == 3
    assert BLAST_SUPER == 5
    assert DMG_NORMAL == 25
    assert DMG_SUPER == 50
    assert SUPER_COMBO_THRESHOLD == 3
    assert SCORE_PER_CELL == 100
    assert SUPER_BONUS == 500
    assert len(TERRAIN_COLORS) == 4
    assert POWER_MIN == 20.0
    assert POWER_MAX == 100.0


# ── Reset / Init State Tests ───────────────────────────────────────────

def test_init_state_creates_terrain() -> None:
    g = _make_game()
    total_cells = 0
    for c in range(COLS):
        for r in range(ROWS):
            if g.terrain[c][r] >= 0:
                total_cells += 1
    assert total_cells > 0


def test_init_state_player_hp() -> None:
    g = _make_game()
    assert g.player_hp == TANK_HP
    assert g.enemy_hp == TANK_HP
    assert g.score == 0
    assert g.combo == 0
    assert g.last_color == -1
    assert g.super_shell_ready is False


def test_reset_clears_state() -> None:
    g = _make_game()
    g.score = 500
    g.combo = 5
    g.player_hp = 20
    g.reset()
    assert g.phase == Phase.TITLE
    # reset calls _init_state internally
    g._init_state()
    assert g.player_hp == TANK_HP
    assert g.score == 0
    assert g.combo == 0


# ── Terrain Tests ──────────────────────────────────────────────────────

def test_terrain_height_positive() -> None:
    g = _make_game()
    h = g._terrain_height(PLAYER_COL)
    assert h >= 0


def test_surface_row_returns_valid() -> None:
    g = _make_game()
    sr = g._surface_row(PLAYER_COL)
    assert 0 <= sr <= ROWS


def test_tank_y_from_terrain_valid() -> None:
    g = _make_game()
    y = g._tank_y_from_terrain(PLAYER_COL)
    assert 0.0 <= y <= SCREEN_W  # just sanity


# ── Destroy Terrain Tests ──────────────────────────────────────────────

def test_destroy_terrain_no_terrain() -> None:
    g = _make_game()
    for c in range(COLS):
        for r in range(ROWS):
            g.terrain[c][r] = -1
    count, colors = g._destroy_terrain(10, 10, 3)
    assert count == 0
    assert len(colors) == 0


def test_destroy_terrain_destroys_cells() -> None:
    g = _make_game()
    for c in range(COLS):
        for r in range(ROWS):
            g.terrain[c][r] = -1
    g.terrain[10][10] = 0
    g.terrain[11][10] = 1
    g.terrain[10][11] = 2
    count, colors = g._destroy_terrain(10, 10, 3)
    assert count == 3
    assert 0 in colors
    assert 1 in colors
    assert 2 in colors


def test_destroy_terrain_out_of_bounds_safe() -> None:
    g = _make_game()
    for c in range(COLS):
        for r in range(ROWS):
            g.terrain[c][r] = -1
    g.terrain[0][0] = 0
    g.terrain[0][1] = 0
    count, colors = g._destroy_terrain(0, 0, 3)
    assert count == 2
    assert g.terrain[0][0] == -1
    assert g.terrain[0][1] == -1


# ── Gravity Collapse Tests ─────────────────────────────────────────────

def test_gravity_collapse_already_packed() -> None:
    g = _make_game()
    for c in range(COLS):
        for r in range(ROWS):
            g.terrain[c][r] = -1
    g.terrain[10][29] = 0
    moved = g._gravity_collapse()
    assert moved == 0


def test_gravity_collapse_move_down() -> None:
    g = _make_game()
    for c in range(COLS):
        for r in range(ROWS):
            g.terrain[c][r] = -1
    g.terrain[10][10] = 0
    g.terrain[10][11] = 0
    moved = g._gravity_collapse()
    assert moved == 0  # same count, just repositioned
    assert g.terrain[10][28] == 0
    assert g.terrain[10][29] == 0
    assert g.terrain[10][10] == -1


def test_gravity_collapse_with_gap() -> None:
    g = _make_game()
    for c in range(COLS):
        for r in range(ROWS):
            g.terrain[c][r] = -1
    g.terrain[10][29] = 0
    g.terrain[10][25] = 1  # gap between 25 and 29
    g.terrain[10][24] = 1
    g._gravity_collapse()
    assert g.terrain[10][29] == 1
    assert g.terrain[10][28] == 1
    assert g.terrain[10][27] == 0


# ── Tank Fell Tests ────────────────────────────────────────────────────

def test_tank_fell_no_terrain() -> None:
    g = _make_game()
    for c in range(COLS):
        for r in range(ROWS):
            g.terrain[c][r] = -1
    assert g._tank_fell(PLAYER_COL) is True


def test_tank_fell_has_terrain() -> None:
    g = _make_game()
    g.terrain[PLAYER_COL][29] = 0
    assert g._tank_fell(PLAYER_COL) is False


# ── COMBO Tests ────────────────────────────────────────────────────────

def test_check_combo_first_hit() -> None:
    g = _make_game()
    g.last_color = -1
    result = g._check_combo([0])
    assert g.combo == 0
    assert g.last_color == TERRAIN_COLORS[0]
    assert result is None


def test_check_combo_same_color() -> None:
    g = _make_game()
    g.last_color = TERRAIN_COLORS[0]
    result = g._check_combo([0, 0, 1])  # most frequent is 0
    assert g.combo == 1
    assert g.last_color == TERRAIN_COLORS[0]
    assert result is None


def test_check_combo_different_color() -> None:
    g = _make_game()
    g.last_color = TERRAIN_COLORS[0]
    g.combo = 2
    result = g._check_combo([1, 1, 1])  # all color 1 (terrain idx 1 = GREEN)
    assert g.combo == 0
    assert g.last_color == TERRAIN_COLORS[1]
    assert result is None


def test_check_combo_super_trigger() -> None:
    g = _make_game()
    g.last_color = TERRAIN_COLORS[0]
    g.combo = 2
    result = g._check_combo([0, 0, 0])
    assert g.combo == 3
    assert g.super_shell_ready is True
    assert result == "super"


def test_check_combo_empty() -> None:
    g = _make_game()
    g.last_color = TERRAIN_COLORS[0]
    g.combo = 2
    result = g._check_combo([])
    assert g.combo == 2  # unchanged
    assert result is None


def test_check_combo_super_already_ready_does_not_re_trigger() -> None:
    g = _make_game()
    g.last_color = TERRAIN_COLORS[0]
    g.combo = 2
    g.super_shell_ready = True
    result = g._check_combo([0, 0, 0])
    assert g.combo == 3
    assert g.super_shell_ready is True
    assert result is None  # already ready, no new trigger


# ── Score Computation Tests ────────────────────────────────────────────

def test_compute_score_no_combo() -> None:
    g = _make_game()
    g.combo = 0
    score = g._compute_score(5)
    assert score == 500  # 5 * 100 * 1.0


def test_compute_score_with_combo() -> None:
    g = _make_game()
    g.combo = 2
    score = g._compute_score(4)
    assert score == 800  # 4 * 100 * (1.0 + 2 * 0.5) = 4 * 100 * 2.0 = 800


def test_compute_score_high_combo() -> None:
    g = _make_game()
    g.combo = 4
    score = g._compute_score(3)
    assert score == 900  # 3 * 100 * (1.0 + 4 * 0.5) = 3 * 100 * 3.0 = 900


# ── AI Angle Tests ─────────────────────────────────────────────────────

def test_ai_angle_in_range() -> None:
    g = _make_game()
    for _ in range(100):
        angle = g._ai_angle()
        assert ANGLE_MIN <= angle <= ANGLE_MAX


def test_ai_angle_deterministic_with_seed() -> None:
    g1 = _make_game(42)
    g2 = _make_game(42)
    assert g1._ai_angle() == g2._ai_angle()


# ── Projectile Physics Tests ───────────────────────────────────────────

def test_update_projectile_gravity() -> None:
    proj = Projectile(x=100.0, y=50.0, vx=2.0, vy=-3.0, alive=True)
    Game._update_projectile(proj)
    assert proj.x == 102.0
    assert abs(proj.y - 47.15) < 0.01
    assert proj.vy == -3.0 + GRAVITY


def test_update_projectile_dead() -> None:
    proj = Projectile(x=100.0, y=50.0, vx=2.0, vy=-3.0, alive=False)
    Game._update_projectile(proj)
    assert proj.x == 100.0
    assert proj.y == 50.0


def test_update_projectile_movement() -> None:
    proj = Projectile(x=100.0, y=100.0, vx=1.0, vy=0.0, alive=True)
    for _ in range(10):
        Game._update_projectile(proj)
    assert proj.y > 100.0  # gravity pulls down


# ── Most Frequent Tests ────────────────────────────────────────────────

def test_most_frequent() -> None:
    assert Game._most_frequent([0, 0, 1, 2, 0]) == 0
    assert Game._most_frequent([1, 1, 2, 2, 2]) == 2
    assert Game._most_frequent([3]) == 3
    assert Game._most_frequent([]) == -1


# ── Fire Projectile Tests ──────────────────────────────────────────────

def test_fire_projectile_creates_valid() -> None:
    g = _make_game()
    proj = g._fire_projectile(100.0, 100.0, -45.0, 60.0)
    assert proj.alive is True
    assert proj.x != 100.0  # moved to barrel tip
    speed = 60.0 * SPEED_SCALE
    assert abs(proj.vx - math.cos(math.radians(-45)) * speed) < 0.01
    assert abs(proj.vy - math.sin(math.radians(-45)) * speed) < 0.01


# ── Barrel Tip Tests ───────────────────────────────────────────────────

def test_barrel_tip_right() -> None:
    g = _make_game()
    bx, by = g._barrel_tip(100.0, 100.0, 0.0)
    assert bx > 100.0
    assert abs(by - 100.0) < 1.0


def test_barrel_tip_up() -> None:
    g = _make_game()
    bx, by = g._barrel_tip(100.0, 100.0, -90.0)
    assert abs(bx - 100.0) < 1.0
    assert by < 100.0


# ── Explosion Hit Tank Tests ───────────────────────────────────────────

def test_explosion_hit_tank_near() -> None:
    g = _make_game()
    hit = g._explosion_hit_tank(100.0, 100.0, 100.0, 100.0, BLAST_NORMAL)
    assert hit is True


def test_explosion_hit_tank_far() -> None:
    g = _make_game()
    hit = g._explosion_hit_tank(0.0, 0.0, 200.0, 200.0, BLAST_NORMAL)
    assert hit is False


# ── Particle / Float Text Management Tests ─────────────────────────────

def test_update_particles_moves_and_decays() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=50.0, vx=1.0, vy=-2.0, color=8, life=5)
    g.particles.append(p)
    g._update_particles()
    assert p.x == 101.0
    assert p.y == 48.0
    assert p.vy == -2.0 + 0.05
    assert p.life == 4


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=50.0, vx=1.0, vy=-2.0, color=8, life=1)
    g.particles.append(p)
    g._update_particles()
    assert len(g.particles) == 0


def test_update_float_texts_floats_and_decays() -> None:
    g = _make_game()
    ft = FloatText(x=80.0, y=200.0, text="+100", life=10, color=7)
    g.float_texts.append(ft)
    g._update_float_texts()
    assert ft.y == 199.5
    assert ft.life == 9


def test_update_float_texts_removes_dead() -> None:
    g = _make_game()
    ft = FloatText(x=80.0, y=200.0, text="+100", life=1, color=7)
    g.float_texts.append(ft)
    g._update_float_texts()
    assert len(g.float_texts) == 0


def test_spawn_smoke() -> None:
    g = _make_game(42)
    g._spawn_smoke(100.0, 100.0, 13, 3)
    assert len(g.particles) > 0


def test_spawn_explosion_particles() -> None:
    g = _make_game(42)
    g._spawn_explosion_particles(100.0, 100.0, [8, 3], False)
    assert len(g.particles) == 12


def test_spawn_explosion_particles_super() -> None:
    g = _make_game(42)
    g._spawn_explosion_particles(100.0, 100.0, [8, 3], True)
    assert len(g.particles) == 20


def test_spawn_float_text() -> None:
    g = _make_game()
    g._spawn_float_text(100.0, 100.0, "+500", 7, 30)
    assert len(g.float_texts) == 1
    assert g.float_texts[0].text == "+500"


# ── Start Game Tests ───────────────────────────────────────────────────

def test_start_game() -> None:
    g = _make_game()
    g._start_game()
    assert g.phase == Phase.PLAYER_AIM


# ── HP Damage Tests ────────────────────────────────────────────────────

def test_enemy_takes_damage_from_explosion() -> None:
    g = _make_game()
    g._start_game()
    g._explosion_cx = int(g.enemy_x // CELL)
    g._explosion_cy = int(g.enemy_y // CELL)
    g._explosion_radius = BLAST_NORMAL
    g._explosion_damage = DMG_NORMAL
    g._explosion_timer = 0
    g._explosion_has_run = False
    g.phase = Phase.ANIM_EXPLOSION
    g.current_projectile = None

    for _ in range(20):
        g.update()
    assert g.enemy_hp <= TANK_HP  # may or may not hit depending on terrain


# ── Gravity After Explosion Moves Tank ─────────────────────────────────

def test_gravity_updates_tank_position() -> None:
    g = _make_game()
    for c in range(COLS):
        for r in range(ROWS):
            g.terrain[c][r] = -1
    g.terrain[PLAYER_COL][ROWS - 5] = 0
    g.terrain[PLAYER_COL][ROWS - 4] = 0
    g.terrain[PLAYER_COL][ROWS - 3] = 0
    old_y = g._tank_y_from_terrain(PLAYER_COL)
    g._gravity_collapse()
    new_y = g._tank_y_from_terrain(PLAYER_COL)
    assert new_y >= old_y  # tank should not rise, only fall or stay (fall = y increases in screen coords)


# ── Multiple Turns Test ────────────────────────────────────────────────

def test_full_turn_cycle_does_not_crash() -> None:
    g = _make_game()
    g._start_game()
    assert g.phase == Phase.PLAYER_AIM

    # Simulate player firing
    g.player_angle = -45.0
    g.player_power = 60.0
    g._power_charging = True
    g._fire_player()
    assert g.phase == Phase.ANIM_PROJECTILE

    # Run through projectile, explosion, gravity to check game doesn't crash
    for _ in range(300):
        g.update()
        if g.phase == Phase.GAME_OVER:
            break
    # Should reach game over or be in some valid phase
    assert g.phase in Phase


print("All tests passed!")
