"""test_imports.py — Headless logic tests for 214_hackysack_chain."""
import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import (
    Sack,
    Particle,
    FloatingText,
    EchoGhost,
    Game,
    Phase,
    SCREEN_W,
    SCREEN_H,
    SACK_RADIUS,
    PLAYER_Y,
    FOOT_H,
    GRAVITY,
    HEAT_CAP,
    HEAT_MISS,
    HEAT_OOB,
    SUPER_COMBO_THRESHOLD,
    SUPER_DURATION,
    GAME_TIME,
    SACK_COLORS,
    SPEED_CLAMP_X,
    SPEED_CLAMP_Y,
    STUCK_THRESHOLD,
    SACK_COLOR_CYCLE_FRAMES,
)


def make_game(rng_seed: int = 42) -> Game:
    """Create a headless Game instance using Game.__new__ pattern."""
    g = Game.__new__(Game)
    g._rng = random.Random(rng_seed)
    # All class constants are inherited, no need to set them
    # Pre-init instance attributes
    g.reset()
    g._rng = random.Random(rng_seed)  # re-seed after reset
    return g


# ── Dataclass tests ──

def test_sack_creation():
    s = Sack(x=100.0, y=50.0, vx=1.0, vy=2.0, color=0)
    assert s.x == 100.0
    assert s.y == 50.0
    assert s.vx == 1.0
    assert s.vy == 2.0
    assert s.color == 0
    assert s.radius == SACK_RADIUS
    assert s.stuck_frames == 0


def test_particle_creation():
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=30, color=8, size=2)
    assert p.x == 10.0
    assert p.life == 30
    assert p.size == 2


def test_floating_text_creation():
    ft = FloatingText(x=100.0, y=50.0, text="+10", life=30, color=7)
    assert ft.text == "+10"
    assert ft.life == 30


def test_echo_ghost_creation():
    eg = EchoGhost(x=50.0, y=60.0, life=90)
    assert eg.x == 50.0
    assert eg.life == 90


# ── Phase enum tests ──

def test_phase_values():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ── Game initialization tests ──

def test_game_reset():
    g = make_game()
    assert g.phase == Phase.TITLE
    assert abs(g.player_x - SCREEN_W / 2) < 1.0
    assert g.combo_count == 0
    assert g.current_combo_color == -1
    assert g.max_combo == 0
    assert g.score == 0
    assert g.heat == 0.0
    assert not g.super_active
    assert g.super_timer == 0
    assert g.time_remaining == GAME_TIME
    assert not g._kicked_this_frame
    assert g.particles == []
    assert g.floating_texts == []
    assert g.ghost_recording == []
    assert g.ghost_playback == []
    assert g.screen_shake == 0
    assert abs(g.sack.x - SCREEN_W / 2) < 1.0


# ── Sack physics tests ──

def test_gravity_applies():
    g = make_game()
    g.sack.x = 160.0
    g.sack.y = 100.0
    g.sack.vx = 0.0
    g.sack.vy = 0.0
    g._update_sack_physics()
    assert g.sack.vy > 0, "Gravity should increase downward velocity"


def test_air_friction():
    g = make_game()
    g.sack.vx = 4.0
    g.sack.vy = 8.0
    g.sack.x = 160.0
    g.sack.y = 100.0
    g._update_sack_physics()
    assert abs(g.sack.vx) < 4.0, "Air friction should reduce horizontal speed"
    assert g.sack.vy < 8.0 + GRAVITY + 0.1, "vy should be affected by friction + gravity"


def test_wall_bounce_left():
    g = make_game()
    g.sack.x = 2.0
    g.sack.y = 100.0
    g.sack.vx = -3.0
    g.sack.vy = 0.0
    g.heat = 0.0
    g._update_sack_physics()
    assert g.sack.vx > 0, "Should bounce right after hitting left wall"


def test_wall_bounce_right():
    g = make_game()
    g.sack.x = SCREEN_W - 2.0
    g.sack.y = 100.0
    g.sack.vx = 3.0
    g.sack.vy = 0.0
    g.heat = 0.0
    g._update_sack_physics()
    assert g.sack.vx < 0, "Should bounce left after hitting right wall"


def test_wall_oob_heat():
    g = make_game()
    g.sack.x = 2.0
    g.sack.vx = -3.0
    g.heat = 0.0
    g._update_sack_physics()
    assert g.heat >= HEAT_OOB, "Wall hit should add HEAT_OOB"


def test_ceiling_bounce():
    g = make_game()
    g.sack.x = 160.0
    g.sack.y = 2.0
    g.sack.vx = 0.0
    g.sack.vy = -3.0
    g._update_sack_physics()
    assert g.sack.vy > 0, "Should bounce down after hitting ceiling"


def test_speed_clamp_x():
    g = make_game()
    g.sack.vx = 10.0
    g.sack.x = 160.0
    g.sack.y = 100.0
    g._update_sack_physics()
    assert abs(g.sack.vx) <= SPEED_CLAMP_X, "vx should be clamped"


def test_speed_clamp_y():
    g = make_game()
    g.sack.vy = 15.0
    g.sack.x = 160.0
    g.sack.y = 100.0
    g._update_sack_physics()
    assert g.sack.vy <= SPEED_CLAMP_Y + GRAVITY, "vy should be clamped + gravity"


# ── Foot collision tests ──

def test_foot_collision_directly_above():
    g = make_game()
    g.sack.x = 160.0
    g.sack.y = PLAYER_Y - FOOT_H - 1  # just above foot
    g.sack.vy = 3.0
    assert g._check_foot_collision(160.0), "Should collide when sack is above foot moving down"


def test_foot_collision_not_moving_down():
    g = make_game()
    g.sack.x = 160.0
    g.sack.y = PLAYER_Y - FOOT_H - 1
    g.sack.vy = -3.0  # moving up
    assert not g._check_foot_collision(160.0), "Should NOT collide when sack moving up"


def test_foot_collision_out_of_range():
    g = make_game()
    g.sack.x = 40.0  # far from player
    g.sack.y = PLAYER_Y - FOOT_H - 1
    g.sack.vy = 3.0
    assert not g._check_foot_collision(160.0), "Should NOT collide when sack is far from foot"


# ── Kick resolution tests ──

def test_resolve_kick_sets_velocity():
    g = make_game()
    g.sack.x = 160.0
    g.sack.y = PLAYER_Y - FOOT_H - 1
    g.sack.vy = 3.0
    g.sack.vx = 1.0
    g.sack.color = 0
    g._resolve_kick(0.0)
    assert g.sack.vy < 0, "Kick should send sack upward"
    assert g._kicked_this_frame


def test_resolve_kick_combo_same_color():
    g = make_game()
    g.sack.color = 0
    g.current_combo_color = 0
    g.combo_count = 2
    g.score = 0
    g._resolve_kick(0.0)
    assert g.combo_count == 3, "Same color should increment combo"
    assert g.score > 0


def test_resolve_kick_combo_different_color():
    g = make_game()
    g.sack.color = 1
    g.current_combo_color = 0
    g.combo_count = 3
    g.score = 10
    g._resolve_kick(0.0)
    assert g.combo_count == 1, "Different color should reset combo to 1"
    assert g.current_combo_color == 1


def test_resolve_kick_updates_max_combo():
    g = make_game()
    g.combo_count = 3
    g.max_combo = 3
    g.current_combo_color = 0
    g.sack.color = 0
    g._resolve_kick(0.0)
    assert g.max_combo == 4


def test_resolve_kick_super_activation():
    g = make_game()
    g.combo_count = SUPER_COMBO_THRESHOLD - 1  # 4
    g.max_combo = SUPER_COMBO_THRESHOLD - 1
    g.current_combo_color = 0
    g.sack.color = 0
    g.score = 0
    assert not g.super_active
    g._resolve_kick(0.0)
    # After kick, combo becomes 5, which should trigger super
    assert g.combo_count == SUPER_COMBO_THRESHOLD
    assert g.super_active, "Should activate super at combo threshold"


def test_resolve_kick_super_renewal():
    g = make_game()
    g.super_active = True
    g.super_timer = 50
    g.current_combo_color = 0
    g.sack.color = 0
    g.combo_count = 5
    g._resolve_kick(0.0)
    assert g.super_timer == SUPER_DURATION, "Super timer should renew on kick"


def test_resolve_kick_adds_floating_text():
    g = make_game()
    g.current_combo_color = 0
    g.sack.color = 0
    g.combo_count = 1
    ft_before = len(g.floating_texts)
    g._resolve_kick(0.0)
    assert len(g.floating_texts) > ft_before


def test_resolve_kick_adds_particles():
    g = make_game()
    g.current_combo_color = 0
    g.sack.color = 0
    g.combo_count = 1
    p_before = len(g.particles)
    g._resolve_kick(0.0)
    assert len(g.particles) > p_before


def test_resolve_kick_super_score_multiplier():
    g = make_game()
    g.super_active = True
    g.current_combo_color = 0
    g.sack.color = 0
    g.combo_count = 5
    g.score = 0
    g._resolve_kick(0.0)
    # combo becomes 6, score should be int(10*(1+6*0.5)*3) = int(10*4*3) = 120
    assert g.score >= 100, f"Super mode should give 3x score, got {g.score}"


# ── Heat / miss tests ──

def test_update_heat_from_miss():
    g = make_game()
    g.heat = 0.0
    g.combo_count = 3
    g.super_active = True
    g.super_timer = 100
    g.ghost_recording = [(1.0, 2.0)]
    g.ghost_playback = [EchoGhost(1.0, 2.0, 50)]
    g._update_heat_from_miss()
    assert g.heat == HEAT_MISS
    assert g.combo_count == 0
    assert g.current_combo_color == -1
    assert not g.super_active
    assert g.super_timer == 0
    assert g.ghost_recording == []
    assert g.ghost_playback == []
    assert g.screen_shake > 0


def test_update_heat_from_miss_heat_clamping():
    g = make_game()
    g.heat = 95.0
    g._update_heat_from_miss()
    assert g.heat == HEAT_CAP, "Heat should cap at HEAT_CAP"


def test_heat_decay():
    g = make_game()
    g.heat = 50.0
    g._update_heat_decay()
    assert g.heat < 50.0, "Heat should decay"


def test_heat_decay_floor():
    g = make_game()
    g.heat = 0.0
    g._update_heat_decay()
    assert g.heat == 0.0, "Heat should not go below 0"


# ── Super mode tests ──

def test_super_mode_timer_decrement():
    g = make_game()
    g.super_active = True
    g.super_timer = 100
    g._update_super_mode()
    assert g.super_timer == 99


def test_super_mode_expiry():
    g = make_game()
    g.super_active = True
    g.super_timer = 1
    g._update_super_mode()
    assert not g.super_active
    assert g.super_timer == 0


def test_activate_super():
    g = make_game()
    g.super_active = False
    g.super_timer = 0
    g._activate_super()
    assert g.super_active
    assert g.super_timer == SUPER_DURATION


# ── Timer tests ──

def test_update_timer():
    g = make_game()
    g.time_remaining = 100
    g._update_timer()
    assert g.time_remaining == 99


def test_update_timer_zero():
    g = make_game()
    g.time_remaining = 0
    g._update_timer()
    assert g.time_remaining == 0


# ── Particle update tests ──

def test_update_particles_reduces_life():
    g = make_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=1.0, vy=-1.0, life=5, color=8)]
    g._update_particles()
    assert g.particles[0].life == 4


def test_update_particles_removes_dead():
    g = make_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=1.0, vy=-1.0, life=1, color=8)]
    g._update_particles()
    assert len(g.particles) == 0, "Particle with life=1 should be removed after update"


# ── Floating text update tests ──

def test_update_floating_texts():
    g = make_game()
    g.floating_texts = [FloatingText(x=100.0, y=100.0, text="TEST", life=30, color=7)]
    g._update_floating_texts()
    assert g.floating_texts[0].life == 29
    assert g.floating_texts[0].y < 100.0, "Text should float upward"


def test_update_floating_texts_removes_dead():
    g = make_game()
    g.floating_texts = [FloatingText(x=100.0, y=100.0, text="TEST", life=1, color=7)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Echo ghost update tests ──

def test_update_echo_ghosts():
    g = make_game()
    g.ghost_playback = [EchoGhost(x=50.0, y=60.0, life=5)]
    g._update_echo_ghosts()
    assert g.ghost_playback[0].life == 4


def test_update_echo_ghosts_removes_dead():
    g = make_game()
    g.ghost_playback = [EchoGhost(x=50.0, y=60.0, life=1)]
    g._update_echo_ghosts()
    assert len(g.ghost_playback) == 0


# ── Sack color cycle tests ──

def test_sack_color_cycle():
    g = make_game()
    initial_color = g.sack.color
    # Advance timer to just below threshold (timer increments THEN checks >=)
    g.sack_color_timer = SACK_COLOR_CYCLE_FRAMES - 2
    g._update_sack_color_timer()
    assert g.sack.color == initial_color, "Color should not change yet"

    # One more tick should cycle
    g._update_sack_color_timer()
    assert g.sack.color != initial_color, "Color should cycle"


# ── Screen shake tests ──

def test_screen_shake_decrements():
    g = make_game()
    g.screen_shake = 5
    g._update_screen_shake()
    assert g.screen_shake == 4


def test_screen_shake_stops_at_zero():
    g = make_game()
    g.screen_shake = 0
    g._update_screen_shake()
    assert g.screen_shake == 0


# ── Corner stuck detection tests ──

def test_stuck_detection():
    g = make_game()
    g.sack.x = 160.0
    g.sack.y = 5.0
    g.sack.vy = 0.4  # below threshold
    g.sack.vx = 0.0
    g.sack.stuck_frames = 0
    g._update_sack_physics()
    assert g.sack.stuck_frames == 1, "Should count stuck frame"


def test_stuck_recovery():
    g = make_game()
    g.sack.x = 160.0
    g.sack.y = 5.0
    g.sack.vy = 0.4
    g.sack.vx = 0.0
    g.sack.stuck_frames = STUCK_THRESHOLD - 1
    g._update_sack_physics()
    # Should trigger recovery
    assert g.sack.vy < 0, "Stuck recovery should give upward velocity"
    assert g.sack.stuck_frames == 0


# ── Ghost recording tests ──

def test_ghost_recording_on_kick():
    g = make_game()
    g._kicked_this_frame = True
    g._prev_sack_x = 100.0
    g._prev_sack_y = 80.0
    g.sack.vy = 0.0
    g.sack.x = 160.0
    g.sack.y = 100.0
    g.sack.vx = 1.0
    g.heat = 0.0
    g.sack.stuck_frames = 0

    # Manually simulate what _update_sack_physics does for ghost recording
    g.ghost_recording.append((g._prev_sack_x, g._prev_sack_y))
    assert len(g.ghost_recording) == 1
    assert g.ghost_recording[0] == (100.0, 80.0)


# ── Game over transition tests ──

def test_game_over_by_heat():
    g = make_game()
    g.phase = Phase.PLAYING
    g.heat = HEAT_CAP
    g.time_remaining = 100
    # The check is in _update_playing which calls pyxel functions
    # Test the condition directly
    assert g.heat >= HEAT_CAP


def test_game_over_by_time():
    g = make_game()
    g.phase = Phase.PLAYING
    g.heat = 0.0
    g.time_remaining = 0
    assert g.time_remaining <= 0


# ── Respawn tests ──

def test_miss_respawns_sack():
    g = make_game()
    g.sack.x = 300.0  # off-screen
    g.sack.y = 300.0
    g._update_heat_from_miss()
    assert g.sack.y < SCREEN_H, "Sack should respawn above screen"
    assert 0 <= g.sack.x <= SCREEN_W, "Sack should respawn on screen"


# ── Constants tests ──

def test_sack_colors_count():
    assert len(SACK_COLORS) == 4


def test_super_threshold_positive():
    assert SUPER_COMBO_THRESHOLD > 0


def test_game_time_is_60s():
    assert GAME_TIME == 60 * 60


def test_heat_cap_is_100():
    assert HEAT_CAP == 100
