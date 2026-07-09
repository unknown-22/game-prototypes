"""test_imports.py — Headless logic tests for 216_vine_chain."""
from __future__ import annotations

import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/216_vine_chain")
from main import (
    COMBO_BONUS,
    FLOOR_Y,
    GRAB_RADIUS,
    GRAVITY,
    HEAT_COOLDOWN,
    HEAT_DECAY,
    HEAT_PER_SUPER_FRAME,
    HEAT_PER_SWING,
    MAX_FALL_SPEED,
    MAX_HEAT,
    MIN_VINE_DIST,
    PLAY_AREA_TOP,
    SCORE_PER_SWING,
    SCREEN_H,
    SCREEN_W,
    SUPER_DURATION,
    SUPER_GRAB_RADIUS,
    SUPER_SCORE_MULT,
    SUPER_THRESHOLD,
    SWING_DAMPING,
    VINE_COUNT,
    VINE_COLORS,
    VINE_SPAWN_INTERVAL,
    FloatingText,
    Game,
    Particle,
    Phase,
    Vine,
)


def _make_game() -> Game:
    """Factory: bypass pyxel.init, pre-init all attributes, call reset(), seed RNG."""
    g: Game = Game.__new__(Game)
    g.reset()
    g._rng = random.Random(42)
    return g


def _make_playing_game() -> Game:
    """Factory: game already in PLAYING state with initial vines."""
    g: Game = Game.__new__(Game)
    g.reset()
    g._rng = random.Random(42)
    g._start_playing()
    g._rng = random.Random(42)  # re-seed after _start_playing overwrites
    return g


# === Dataclass Tests ===
def test_vine_creation() -> None:
    v = Vine(x=100.0, y=24.0, length=120.0, color=8)
    assert v.x == 100.0
    assert v.y == 24.0
    assert v.length == 120.0
    assert v.color == 8
    assert not v.grabbed


def test_particle_creation() -> None:
    p = Particle(x=50.0, y=60.0, vx=1.0, vy=-2.0, life=20, color=8, size=2)
    assert p.x == 50.0
    assert p.y == 60.0
    assert p.life == 20
    assert p.color == 8
    assert p.size == 2


def test_floating_text_creation() -> None:
    ft = FloatingText(x=100.0, y=80.0, text="+10", life=30, color=7, vy=-1.0)
    assert ft.text == "+10"
    assert ft.life == 30
    assert ft.color == 7


# === Phase / State Tests ===
def test_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert not g.super_mode
    assert g.heat == 0.0
    assert len(g.vines) == 0
    assert g._attached_vine is None


def test_start_playing_transitions_to_playing() -> None:
    g = _make_game()
    g._start_playing()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert len(g.vines) == VINE_COUNT


# === Vine Spawning Tests ===
def test_spawn_initial_vines_count() -> None:
    g = _make_game()
    g._spawn_initial_vines()
    assert len(g.vines) == VINE_COUNT


def test_spawn_initial_vines_positions() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_initial_vines()
    # Vines should span the screen width
    assert g.vines[0].x < g.vines[-1].x
    assert g.vines[0].x >= 30
    assert g.vines[-1].x <= SCREEN_W


def test_spawn_vine_adds_one() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_initial_vines()
    initial_count = len(g.vines)
    g._spawn_vine()
    assert len(g.vines) == initial_count + 1


def test_spawn_vine_respects_min_distance() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    # Clear vines and place one at right edge
    g.vines.clear()
    g.vines.append(Vine(x=float(SCREEN_W), y=float(PLAY_AREA_TOP), length=100.0, color=8))
    # Spawn a new vine — it should respect min distance from rightmost
    g._spawn_vine()
    sorted_vines = sorted(g.vines, key=lambda v: v.x)
    rightmost = sorted_vines[-1]
    second_rightmost = sorted_vines[-2]
    assert rightmost.x - second_rightmost.x >= MIN_VINE_DIST - 0.01


def test_spawn_vine_colors_in_palette() -> None:
    g = _make_game()
    g._rng = random.Random(42)
    g._spawn_initial_vines()
    for v in g.vines:
        assert v.color in VINE_COLORS


# === Vine Scrolling Tests ===
def test_update_vines_scrolls_left() -> None:
    g = _make_playing_game()
    old_positions = [(v.x, v.color) for v in g.vines]
    g._update_vines()
    for i, v in enumerate(g.vines):
        if i < len(old_positions):
            assert v.x < old_positions[i][0]  # moved left


def test_update_vines_removes_offscreen() -> None:
    g = _make_playing_game()
    # Move all vines far left
    for v in g.vines:
        v.x = -100.0
    g._vine_spawn_timer = 999  # prevent spawning
    g._update_vines()
    # Vines at -100 scrolled to -101.5, filtered out (x > -40 keeps them)
    # But when all vines gone, _spawn_initial_vines replenishes
    # Verify the original off-screen vines were removed
    assert len(g.vines) == VINE_COUNT  # respawned by _spawn_initial_vines
    # All new vines should be on screen
    for v in g.vines:
        assert v.x > -40


# === Physics Tests ===
def test_freefall_applies_gravity() -> None:
    g = _make_playing_game()
    g._attached_vine = None
    g.player_y = 100.0
    g.player_vy = 0.0
    g._update_freefall_physics()
    assert g.player_vy > 0.0  # gravity applied
    assert g.player_y > 100.0  # moved down


def test_freefall_max_fall_speed() -> None:
    g = _make_playing_game()
    g._attached_vine = None
    g.player_vy = MAX_FALL_SPEED
    g._update_freefall_physics()
    assert g.player_vy <= MAX_FALL_SPEED


def test_landing_on_floor() -> None:
    g = _make_playing_game()
    g._attached_vine = None
    g.player_y = FLOOR_Y - 1.0
    g.player_vy = 5.0
    g._update_freefall_physics()
    assert g.player_y == float(FLOOR_Y)
    assert g.player_vy == 0.0
    assert g._on_ground


def test_swing_physics_updates_position() -> None:
    g = _make_playing_game()
    v = g.vines[0]
    g._attached_vine = v
    g._swing_angle = 0.3
    g._swing_angular_vel = 0.02
    old_x = g.player_x
    old_y = g.player_y
    g._update_swing_physics()
    # Position should change due to swing
    assert g.player_x != old_x or g.player_y != old_y


def test_swing_physics_damping() -> None:
    g = _make_playing_game()
    v = g.vines[0]
    g._attached_vine = v
    g._swing_angular_vel = 0.1
    g._update_swing_physics()
    assert abs(g._swing_angular_vel) < 0.1  # damped


def test_swing_player_not_on_ground() -> None:
    g = _make_playing_game()
    v = g.vines[0]
    g._attached_vine = v
    g._swing_angle = 0.3
    g._swing_angular_vel = 0.01
    g._update_swing_physics()
    assert not g._on_ground


# === Player Wrap Tests ===
def test_wrap_player_right_to_left() -> None:
    g = _make_playing_game()
    g.player_x = SCREEN_W + 20.0
    g._attached_vine = None
    g._wrap_player()
    assert g.player_x == -10.0


def test_wrap_player_left_to_right() -> None:
    g = _make_playing_game()
    g.player_x = -20.0
    g._attached_vine = None
    g._wrap_player()
    assert g.player_x == float(SCREEN_W + 10)


def test_wrap_detaches_vine() -> None:
    g = _make_playing_game()
    g._attached_vine = g.vines[0]
    g.vines[0].grabbed = True
    g.player_x = SCREEN_W + 20.0
    g._wrap_player()
    assert g._attached_vine is None
    assert not g.vines[0].grabbed


# === Grab / Release Tests ===
def test_try_grab_vine_in_range() -> None:
    g = _make_playing_game()
    v = g.vines[0]
    g.player_x = v.x
    g.player_y = v.y + v.length  # player at vine tip
    g._try_grab_vine()
    assert g._attached_vine is v
    assert v.grabbed


def test_try_grab_vine_out_of_range() -> None:
    g = _make_playing_game()
    v = g.vines[0]
    g.player_x = v.x + GRAB_RADIUS + 50
    g.player_y = v.y + v.length + 50
    g._try_grab_vine()
    assert g._attached_vine is None


def test_release_vine_gives_score() -> None:
    g = _make_playing_game()
    v = g.vines[0]
    g._attached_vine = v
    v.grabbed = True
    g.combo = 2
    g.score = 0
    g._release_vine()
    assert g._attached_vine is None
    assert not v.grabbed
    expected = SCORE_PER_SWING + COMBO_BONUS * 2
    assert g.score == expected


def test_release_vine_no_vine_attached() -> None:
    g = _make_playing_game()
    g._attached_vine = None
    g.score = 0
    g._release_vine()
    assert g.score == 0  # no-op


# === Combo Logic Tests ===
def test_same_color_combo_increment() -> None:
    g = _make_playing_game()
    g._last_vine_color = RED = 8
    v = Vine(x=200.0, y=PLAY_AREA_TOP, length=100.0, color=8)
    g.vines.append(v)
    g.player_x = v.x
    g.player_y = v.y + v.length
    g.combo = 0
    g._try_grab_vine()
    assert g.combo == 1
    assert g._last_vine_color == 8


def test_same_color_consecutive_combo_increment() -> None:
    g = _make_playing_game()
    g._last_vine_color = 8  # RED
    g.combo = 3
    v = Vine(x=200.0, y=PLAY_AREA_TOP, length=100.0, color=8)
    g.vines.append(v)
    g.player_x = v.x
    g.player_y = v.y + v.length
    g._try_grab_vine()
    assert g.combo == 4
    assert g.max_combo == 4


def test_different_color_resets_combo() -> None:
    g = _make_playing_game()
    g._last_vine_color = 8  # RED
    g.combo = 3
    g.max_combo = 3
    v = Vine(x=200.0, y=PLAY_AREA_TOP, length=100.0, color=9)  # ORANGE
    g.vines.append(v)
    g.player_x = v.x
    g.player_y = v.y + v.length
    g._try_grab_vine()
    assert g.combo == 0
    assert g._last_vine_color == 9
    # max_combo should still be 3
    assert g.max_combo == 3


def test_first_vine_sets_color_no_combo_check() -> None:
    g = _make_playing_game()
    g._last_vine_color = None
    g.combo = 0
    v = Vine(x=200.0, y=PLAY_AREA_TOP, length=100.0, color=8)
    g.vines.append(v)
    g.player_x = v.x
    g.player_y = v.y + v.length
    g._try_grab_vine()
    assert g.combo == 1
    assert g._last_vine_color == 8


# === SUPER Mode Tests ===
def test_super_mode_activates_at_threshold() -> None:
    g = _make_playing_game()
    g._last_vine_color = 8
    g.combo = SUPER_THRESHOLD - 1  # 4
    v = Vine(x=200.0, y=PLAY_AREA_TOP, length=100.0, color=8)
    g.vines.append(v)
    g.player_x = v.x
    g.player_y = v.y + v.length
    assert not g.super_mode
    g._try_grab_vine()
    assert g.combo == SUPER_THRESHOLD  # 5
    assert g.super_mode
    assert g.super_timer == SUPER_DURATION


def test_super_mode_exact_threshold_not_before() -> None:
    g = _make_playing_game()
    g._last_vine_color = 8
    g.combo = SUPER_THRESHOLD - 2  # 3
    v = Vine(x=200.0, y=PLAY_AREA_TOP, length=100.0, color=8)
    g.vines.append(v)
    g.player_x = v.x
    g.player_y = v.y + v.length
    g._try_grab_vine()
    assert g.combo == 4
    assert not g.super_mode  # not yet at threshold


def test_super_mode_timer_decrements() -> None:
    g = _make_playing_game()
    g.super_mode = True
    g.super_timer = 100
    g._update_super_mode()
    assert g.super_timer == 99
    assert g.super_mode


def test_super_mode_expires() -> None:
    g = _make_playing_game()
    g.super_mode = True
    g.super_timer = 1
    g.combo = 5
    g._update_super_mode()
    assert g.super_timer == 0
    assert not g.super_mode
    assert g.combo == 0  # combo resets on expire


def test_super_mode_allows_any_color() -> None:
    g = _make_playing_game()
    g.super_mode = True
    g._last_vine_color = 8  # RED
    g.combo = 5
    v = Vine(x=200.0, y=PLAY_AREA_TOP, length=100.0, color=9)  # ORANGE (different)
    g.vines.append(v)
    g.player_x = v.x
    g.player_y = v.y + v.length
    g._try_grab_vine()
    assert g.combo == 6  # combo incremented (super ignores color)
    assert g._last_vine_color == 9


def test_super_mode_score_multiplier() -> None:
    g = _make_playing_game()
    g.super_mode = True
    v = g.vines[0]
    g._attached_vine = v
    v.grabbed = True
    g.combo = 5
    g.score = 0
    g._release_vine()
    expected = (SCORE_PER_SWING + COMBO_BONUS * 5) * SUPER_SCORE_MULT
    assert g.score == expected


# === HEAT Tests ===
def test_heat_decays_on_ground() -> None:
    g = _make_playing_game()
    g.heat = 50.0
    g._on_ground = True
    g.super_mode = False
    g._update_heat()
    assert g.heat < 50.0
    assert g.heat == max(0.0, 50.0 - HEAT_DECAY)


def test_heat_cooldown_while_swinging() -> None:
    g = _make_playing_game()
    g.heat = 50.0
    g._on_ground = False
    g._attached_vine = g.vines[0]
    g.super_mode = False
    g._update_heat()
    assert g.heat < 50.0
    assert g.heat == max(0.0, 50.0 - HEAT_COOLDOWN)


def test_heat_increases_during_super() -> None:
    g = _make_playing_game()
    g.heat = 50.0
    g.super_mode = True
    g._update_heat()
    assert g.heat > 50.0
    assert abs(g.heat - (50.0 + HEAT_PER_SUPER_FRAME)) < 0.001


def test_heat_clamped_to_max() -> None:
    g = _make_playing_game()
    g.heat = MAX_HEAT + 10.0
    g.super_mode = False
    g._on_ground = False
    g._attached_vine = None
    g._update_heat()
    assert g.heat == MAX_HEAT


def test_heat_does_not_go_below_zero() -> None:
    g = _make_playing_game()
    g.heat = 0.0
    g._on_ground = True
    g.super_mode = False
    g._update_heat()
    assert g.heat == 0.0


# === Game Over Tests ===
def test_game_over_from_overheat() -> None:
    g = _make_playing_game()
    g.heat = MAX_HEAT
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER
    assert g._death_cause == "Overheated!"


def test_game_over_from_falling() -> None:
    g = _make_playing_game()
    g.player_y = SCREEN_H + 30.0
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER
    assert g._death_cause == "Fell!"


def test_no_game_over_normal_state() -> None:
    g = _make_playing_game()
    g.heat = 50.0
    g.player_y = 100.0
    g._check_game_over()
    assert g.phase == Phase.PLAYING


# === Particle Tests ===
def test_particle_life_decrements() -> None:
    g = _make_playing_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=5, color=8, size=2)]
    g._update_particles()
    assert g.particles[0].life == 4


def test_particle_removed_when_life_zero() -> None:
    g = _make_playing_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=1, color=8, size=2)]
    g._update_particles()
    assert len(g.particles) == 0  # life=1 → 0 → removed same tick


def test_particle_moves() -> None:
    g = _make_playing_game()
    p = Particle(x=100.0, y=100.0, vx=2.0, vy=-1.0, life=10, color=8, size=2)
    g.particles = [p]
    g._update_particles()
    assert p.x == 102.0
    assert p.y == 99.0


# === Floating Text Tests ===
def test_floating_text_life_decrements() -> None:
    g = _make_playing_game()
    g.floating_texts = [FloatingText(x=100.0, y=100.0, text="+10", life=5, color=7, vy=-1.0)]
    g._update_floating_texts()
    assert g.floating_texts[0].life == 4


def test_floating_text_removed_when_life_zero() -> None:
    g = _make_playing_game()
    g.floating_texts = [FloatingText(x=100.0, y=100.0, text="+10", life=1, color=7, vy=-1.0)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_floating_text_rises() -> None:
    g = _make_playing_game()
    ft = FloatingText(x=100.0, y=100.0, text="+10", life=5, color=7, vy=-1.0)
    g.floating_texts = [ft]
    g._update_floating_texts()
    assert ft.y < 100.0  # moved up


# === Reset Tests ===
def test_reset_clears_all_state() -> None:
    g = _make_playing_game()
    g.score = 500
    g.combo = 3
    g.max_combo = 6
    g.heat = 80.0
    g.super_mode = True
    g.super_timer = 100
    g._attached_vine = g.vines[0]
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=8, size=2)]
    g.floating_texts = [FloatingText(x=0.0, y=0.0, text="x", life=1, color=7)]
    g.reset()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert not g.super_mode
    assert g.super_timer == 0
    assert g._attached_vine is None
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert len(g.vines) == 0


# === Combo max_combo tracking ===
def test_max_combo_tracks_highest() -> None:
    g = _make_playing_game()
    g._last_vine_color = 8
    g.combo = 0
    g.max_combo = 0
    # Grab 3 same-color vines
    for i in range(6):
        v = Vine(x=200.0 + i * 10, y=PLAY_AREA_TOP, length=100.0, color=8)
        g.vines.append(v)
        g.player_x = v.x
        g.player_y = v.y + v.length
        g._try_grab_vine()
        # release between grabs
        g._release_vine()
    assert g.max_combo == 6


# === Super auto-grab extended range ===
def test_super_auto_grab_uses_extended_range() -> None:
    g = _make_playing_game()
    g.super_mode = True
    g._attached_vine = None
    # Clear vines and place only one at a known position
    g.vines.clear()
    target = Vine(x=200.0, y=float(PLAY_AREA_TOP), length=100.0, color=8)
    g.vines.append(target)
    # Place player at SUPER_GRAB_RADIUS - 5 from vine tip
    vine_tip_y = target.y + target.length  # 124
    g.player_x = target.x + SUPER_GRAB_RADIUS - 15
    g.player_y = vine_tip_y
    g._super_auto_grab()
    assert g._attached_vine is target
    assert target.grabbed


def test_super_auto_grab_beyond_range() -> None:
    g = _make_playing_game()
    g.super_mode = True
    g._attached_vine = None
    # Clear all vines and place one far away
    g.vines.clear()
    far_vine = Vine(x=500.0, y=float(PLAY_AREA_TOP), length=100.0, color=8)
    g.vines.append(far_vine)
    g.player_x = 20.0
    g.player_y = 120.0
    g._super_auto_grab()
    # Player at (20,120), vine tip at (500,124) — distance ~480 >> SUPER_GRAB_RADIUS
    assert g._attached_vine is None


# === Scrolling wraps and preserves state ===
def test_vine_scroll_preserves_attachment() -> None:
    g = _make_playing_game()
    v = g.vines[0]
    g._attached_vine = v
    v.grabbed = True
    # Vine at typical starting position, scroll once
    g._vine_spawn_timer = 999
    g._update_vines()
    # Vine should still be grabbed and attached
    assert g._attached_vine is v
    assert v.grabbed


# === Vine count in _spawn_initial_vines with seeded RNG ===
def test_spawn_initial_vines_deterministic() -> None:
    g1 = _make_game()
    g1._rng = random.Random(42)
    g1._spawn_initial_vines()

    g2 = _make_game()
    g2._rng = random.Random(42)
    g2._spawn_initial_vines()

    assert len(g1.vines) == len(g2.vines) == VINE_COUNT
    for i in range(VINE_COUNT):
        assert g1.vines[i].x == g2.vines[i].x
        assert g1.vines[i].length == g2.vines[i].length
        assert g1.vines[i].color == g2.vines[i].color


# === Physics: pendulum position calculation ===
def test_swing_physics_pendulum_math() -> None:
    g = _make_playing_game()
    v = Vine(x=160.0, y=PLAY_AREA_TOP, length=100.0, color=8)
    g._attached_vine = v
    g._swing_angle = 0.0  # straight down
    g._swing_angular_vel = 0.0
    g._update_swing_physics()
    # At angle 0, sin(0)=0, cos(0)=1 → player at (anchor_x, anchor_y + length)
    assert abs(g.player_x - v.x) < 0.01
    assert abs(g.player_y - (v.y + v.length)) < 0.01


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
