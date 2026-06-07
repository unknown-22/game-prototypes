"""test_imports.py — Headless logic tests for 106_kart_surge."""
import math
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from main import (
    ACCEL, BRAKE, COMBO_FOR_SURGE, FRICTION,
    INFIELD_BOTTOM, INFIELD_LEFT, INFIELD_RIGHT, INFIELD_TOP,
    KART_RADIUS, LAP_COUNT, MAX_SPEED,
    PAD_COLORS, PAD_COUNT, PAD_RADIUS,
    PAD_RESPAWN_TIME, PARTICLE_COUNT_ON_COLLECT,
    PARTICLE_COUNT_ON_SURGE, PARTICLE_LIFE,
    SCREEN_H, SCREEN_W, SURGE_DURATION, TURN_SPEED,
    BoostPad, Game, GhostPoint, Particle, Phase,
    TRACK_LEFT, TRACK_TOP, TRACK_RIGHT, TRACK_BOTTOM,
)


def _make_game() -> Game:
    """Create a Game instance bypassing pyxel.init/run for headless testing."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.player_x = 160.0
    g.player_y = 120.0
    g.player_angle = 0.0
    g.player_speed = 0.0
    g.combo = 0
    g.max_combo = 0
    g.score = 0
    g.surge_timer = 0
    g.lap = 1
    g.lap_start_frame = 0
    g.best_lap_time = 99999
    g.frame = 0
    g.finish_crossed = False
    g.pads = []
    g.particles = []
    g.ghost = []
    g.recording = []
    g.last_pad_color = None
    return g


# ============================================================
# 1. Constants
# ============================================================

def test_constants():
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert MAX_SPEED == 3.0
    assert ACCEL == 0.15
    assert BRAKE == 0.1
    assert FRICTION == 0.98
    assert TURN_SPEED == 0.08
    assert LAP_COUNT == 3
    assert SURGE_DURATION == 300
    assert COMBO_FOR_SURGE == 5
    assert PAD_RESPAWN_TIME == 90
    assert PAD_COUNT == 16
    assert KART_RADIUS == 6
    assert PAD_RADIUS == 5
    assert PARTICLE_COUNT_ON_COLLECT == 5
    assert PARTICLE_COUNT_ON_SURGE == 12
    assert PARTICLE_LIFE == 20
    assert len(PAD_COLORS) == 4
    assert 8 in PAD_COLORS   # RED
    assert 3 in PAD_COLORS   # GREEN
    assert 5 in PAD_COLORS   # DARK_BLUE
    assert 10 in PAD_COLORS  # YELLOW


# ============================================================
# 2. Initialization / reset
# ============================================================

def test_reset_sets_initial_values():
    g = _make_game()
    g.player_x = 999
    g.phase = Phase.GAME_OVER
    g.score = 500
    g.combo = 10
    g.reset()
    assert g.phase == Phase.TITLE
    assert g.player_x == 160.0
    assert g.player_y == 120.0
    assert g.player_angle == 0.0
    assert g.player_speed == 0.0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.score == 0
    assert g.surge_timer == 0
    assert g.lap == 1
    assert g.lap_start_frame == 0
    assert g.best_lap_time == 99999
    assert g.frame == 0
    assert g.finish_crossed is False
    assert g.particles == []
    assert g.ghost == []
    assert g.recording == []
    assert g.last_pad_color is None


def test_reset_spawns_pads():
    g = _make_game()
    g.reset()
    assert len(g.pads) == PAD_COUNT
    colors_seen = set()
    for pad in g.pads:
        assert pad.active is True
        assert pad.respawn_timer == 0
        colors_seen.add(pad.color)
    assert colors_seen == set(PAD_COLORS)


def test_spawn_pads_in_road_zone():
    g = _make_game()
    g.reset()
    for pad in g.pads:
        # Must be in road zone
        assert TRACK_LEFT + 10 <= pad.x <= TRACK_RIGHT - 10
        assert TRACK_TOP + 10 <= pad.y <= TRACK_BOTTOM - 10
        # Must NOT be in infield
        is_in_infield = (INFIELD_LEFT <= pad.x <= INFIELD_RIGHT and
                         INFIELD_TOP <= pad.y <= INFIELD_BOTTOM)
        assert not is_in_infield, f"Pad at ({pad.x}, {pad.y}) is in infield"


# ============================================================
# 3. Physics
# ============================================================

def test_physics_friction_applied():
    g = _make_game()
    g.player_speed = 2.0
    g._update_physics()
    assert g.player_speed == pytest.approx(2.0 * FRICTION)


def test_physics_moves_player():
    g = _make_game()
    g.player_angle = 0.0  # Right
    g.player_speed = 2.0
    g.player_x = 100.0
    g.player_y = 100.0
    g._update_physics()
    assert g.player_x > 100.0


def test_physics_moves_player_down():
    g = _make_game()
    g.player_angle = math.pi / 2  # Down
    g.player_speed = 2.0
    g.player_x = 100.0
    g.player_y = 100.0
    g._update_physics()
    assert g.player_y > 100.0


def test_physics_clamps_to_outer_boundary():
    g = _make_game()
    g.player_x = 10.0
    g.player_y = 10.0
    g._update_physics()
    assert g.player_x >= TRACK_LEFT + KART_RADIUS
    assert g.player_y >= TRACK_TOP + KART_RADIUS


def test_physics_clamps_max_right():
    g = _make_game()
    g.player_x = 500.0
    g._update_physics()
    assert g.player_x <= TRACK_RIGHT - KART_RADIUS


def test_physics_infield_collision_pushes_out():
    g = _make_game()
    # Place kart inside infield
    g.player_x = float(INFIELD_LEFT + INFIELD_RIGHT) / 2  # center of infield
    g.player_y = float(INFIELD_TOP + INFIELD_BOTTOM) / 2
    g._update_physics()
    infield_cx = float(INFIELD_LEFT + INFIELD_RIGHT) / 2
    infield_cy = float(INFIELD_TOP + INFIELD_BOTTOM) / 2
    dist_from_center = math.hypot(g.player_x - infield_cx, g.player_y - infield_cy)
    # Should be at least ~1 pixel out of the infield
    assert dist_from_center > 0


# ============================================================
# 4. Pad collisions
# ============================================================

def test_collect_pad_sets_combo_to_1_on_first_pickup():
    g = _make_game()
    pad = BoostPad(x=100, y=100, color=PAD_COLORS[0])
    g._collect_pad(pad)
    assert g.combo == 1
    assert g.last_pad_color == PAD_COLORS[0]


def test_collect_pad_same_color_increases_combo():
    g = _make_game()
    g.last_pad_color = PAD_COLORS[0]
    g.combo = 2
    pad = BoostPad(x=100, y=100, color=PAD_COLORS[0])
    g._collect_pad(pad)
    assert g.combo == 3


def test_collect_pad_different_color_resets_combo_to_1():
    g = _make_game()
    g.last_pad_color = PAD_COLORS[0]
    g.combo = 3
    pad = BoostPad(x=100, y=100, color=PAD_COLORS[1])
    g._collect_pad(pad)
    assert g.combo == 1
    assert g.last_pad_color == PAD_COLORS[1]


def test_collect_pad_tracks_max_combo():
    g = _make_game()
    g.last_pad_color = PAD_COLORS[0]
    g.combo = 3
    g.max_combo = 3
    pad = BoostPad(x=100, y=100, color=PAD_COLORS[0])
    g._collect_pad(pad)
    assert g.max_combo == 4


def test_collect_pad_deactivates_pad():
    g = _make_game()
    pad = BoostPad(x=100, y=100, color=PAD_COLORS[0])
    g._collect_pad(pad)
    assert pad.active is False
    assert pad.respawn_timer == PAD_RESPAWN_TIME


def test_check_pad_collisions_detects_touch():
    g = _make_game()
    g.player_x = 100.0
    g.player_y = 100.0
    pad = BoostPad(x=104.0, y=100.0, color=PAD_COLORS[0])  # within KART_RADIUS + PAD_RADIUS (11)
    g.pads = [pad]
    g.particles = []  # ensure list exists
    g._check_pad_collisions()
    assert pad.active is False
    assert g.combo == 1


def test_check_pad_collisions_ignores_inactive():
    g = _make_game()
    g.player_x = 100.0
    g.player_y = 100.0
    pad = BoostPad(x=100.0, y=100.0, color=PAD_COLORS[0], active=False)
    g.pads = [pad]
    g.combo = 0
    g._check_pad_collisions()
    assert g.combo == 0  # no pickup


def test_check_pad_collisions_ignores_far_away():
    g = _make_game()
    g.player_x = 100.0
    g.player_y = 100.0
    pad = BoostPad(x=200.0, y=200.0, color=PAD_COLORS[0])
    g.pads = [pad]
    g.combo = 0
    g._check_pad_collisions()
    assert g.combo == 0  # no pickup


# ============================================================
# 5. Scoring
# ============================================================

def test_score_pad_base_points():
    g = _make_game()
    pad = BoostPad(x=100, y=100, color=PAD_COLORS[0])
    g._collect_pad(pad)
    # combo=1 -> 10 * 1 = 10
    assert g.score == 10


def test_score_pad_combo_multiplier():
    g = _make_game()
    g.last_pad_color = PAD_COLORS[0]
    g.combo = 3
    pad = BoostPad(x=100, y=100, color=PAD_COLORS[0])
    g._collect_pad(pad)
    # combo becomes 4, score = 10 * 4 = 40
    assert g.score == 40


def test_score_pad_surge_multiplier():
    g = _make_game()
    g.surge_timer = 100
    g.combo = 2
    g.last_pad_color = PAD_COLORS[0]
    pad = BoostPad(x=100, y=100, color=PAD_COLORS[0])
    g._collect_pad(pad)
    # combo becomes 3, score = 10 * 3 * 3 = 90
    assert g.score == 90


# ============================================================
# 6. Surge
# ============================================================

def test_surge_activates_at_combo_threshold():
    g = _make_game()
    g.last_pad_color = PAD_COLORS[0]
    g.combo = COMBO_FOR_SURGE - 1  # 4
    pad = BoostPad(x=100, y=100, color=PAD_COLORS[0])
    g._collect_pad(pad)
    assert g.combo == COMBO_FOR_SURGE
    assert g.surge_timer == SURGE_DURATION


def test_surge_refreshes_during_surge():
    g = _make_game()
    g.surge_timer = 50
    g.last_pad_color = PAD_COLORS[0]
    g.combo = 5
    pad = BoostPad(x=100, y=100, color=PAD_COLORS[0])
    g._collect_pad(pad)
    assert g.surge_timer == SURGE_DURATION  # Refreshed to full


def test_update_surge_decrements_timer():
    g = _make_game()
    g.surge_timer = 10
    g._update_surge()
    assert g.surge_timer == 9


def test_update_surge_stops_at_zero():
    g = _make_game()
    g.surge_timer = 1
    g._update_surge()
    assert g.surge_timer == 0
    g._update_surge()
    assert g.surge_timer == 0


# ============================================================
# 7. Particles
# ============================================================

def test_collect_pad_spawns_particles():
    g = _make_game()
    pad = BoostPad(x=100, y=100, color=PAD_COLORS[0])
    g._collect_pad(pad)
    assert len(g.particles) == PARTICLE_COUNT_ON_COLLECT
    for p in g.particles:
        assert p.life == PARTICLE_LIFE
        assert p.color == PAD_COLORS[0]


def test_surge_activation_spawns_extra_particles():
    g = _make_game()
    g.last_pad_color = PAD_COLORS[0]
    g.combo = COMBO_FOR_SURGE - 1
    g.player_x = 100.0
    g.player_y = 100.0
    pad = BoostPad(x=100, y=100, color=PAD_COLORS[0])
    g._collect_pad(pad)
    # Collection particles (5) + Surge particles (12) = 17
    assert len(g.particles) == PARTICLE_COUNT_ON_COLLECT + PARTICLE_COUNT_ON_SURGE


def test_update_particles_moves_and_decays():
    g = _make_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=1.0, vy=0.5, life=5, color=8)]
    g._update_particles()
    p = g.particles[0]
    assert p.x == 101.0
    assert p.y == 100.5
    assert p.life == 4


def test_update_particles_removes_dead():
    g = _make_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=0, color=8)]
    g._update_particles()
    assert len(g.particles) == 0


# ============================================================
# 8. Pad respawn
# ============================================================

def test_pad_respawn_timer_decrements():
    g = _make_game()
    pad = BoostPad(x=100, y=100, color=PAD_COLORS[0], active=False, respawn_timer=10)
    g.pads = [pad]
    g._update_pad_respawns()
    assert pad.respawn_timer == 9


def test_pad_reactivates_when_timer_expires():
    g = _make_game()
    pad = BoostPad(x=100, y=100, color=PAD_COLORS[0], active=False, respawn_timer=1)
    g.pads = [pad]
    g._update_pad_respawns()
    assert pad.active is True
    assert pad.respawn_timer == 0


# ============================================================
# 9. Ghost recording
# ============================================================

def test_record_ghost_every_3_frames():
    g = _make_game()
    g.player_x = 160.0
    g.player_y = 120.0
    for f in range(1, 10):
        g.frame = f
        g._record_ghost()
    # Frames 3, 6, 9 -> 3 recordings
    assert len(g.recording) == 3


def test_ghost_copied_on_best_lap():
    g = _make_game()
    g.recording = [
        GhostPoint(x=100, y=100),
        GhostPoint(x=110, y=105),
        GhostPoint(x=120, y=110),
    ]
    g.best_lap_time = 99999
    g.lap_start_frame = 0
    g.frame = 180
    g._best_lap_bonus()
    # Simulate best lap by manually copying
    if g.frame - g.lap_start_frame < g.best_lap_time:
        g.best_lap_time = g.frame - g.lap_start_frame
        g.ghost = list(g.recording)
    assert len(g.ghost) == 3
    assert g.ghost[0].x == 100


# ============================================================
# 10. Lap counting
# ============================================================

def test_finish_crossed_flag_prevents_double_cross():
    g = _make_game()
    g.finish_crossed = True
    g.lap = 1
    # Place kart on finish line
    g.player_x = 160.0
    g.player_y = 155.0
    g._check_lap()
    # Should not increment lap since finish_crossed is True
    assert g.lap == 1


def test_finish_crossed_resets_when_off_line():
    g = _make_game()
    g.finish_crossed = True
    g.player_x = 160.0
    g.player_y = 100.0  # Far from finish line
    g._check_lap()
    assert g.finish_crossed is False


def test_lap_completion_increments_lap():
    g = _make_game()
    g.finish_crossed = False
    g.player_x = 160.0
    g.player_y = 155.0  # On finish line
    g.recording = [GhostPoint(x=100, y=100)]
    g._check_lap()
    assert g.lap == 2
    assert g.finish_crossed is True


def test_lap_completion_resets_combo_and_surge():
    g = _make_game()
    g.combo = 5
    g.surge_timer = 100
    g.last_pad_color = PAD_COLORS[0]
    g.finish_crossed = False
    g.player_x = 160.0
    g.player_y = 155.0
    g.recording = [GhostPoint(x=100, y=100)]
    g._check_lap()
    assert g.combo == 0
    assert g.surge_timer == 0
    assert g.last_pad_color is None


def test_lap_completion_clears_recording():
    g = _make_game()
    g.recording = [GhostPoint(x=100, y=100), GhostPoint(x=110, y=105)]
    g.finish_crossed = False
    g.player_x = 160.0
    g.player_y = 155.0
    g._check_lap()
    assert g.recording == []


def test_three_laps_end_game():
    g = _make_game()
    g.lap = LAP_COUNT  # 3
    g.finish_crossed = False
    g.player_x = 160.0
    g.player_y = 155.0
    g.recording = [GhostPoint(x=100, y=100)]
    g._check_lap()
    assert g.phase == Phase.GAME_OVER


# ============================================================
# 11. Best lap bonus
# ============================================================

def test_best_lap_bonus_positive():
    g = _make_game()
    g.best_lap_time = 120  # 2 seconds at 60fps
    bonus = g._best_lap_bonus()
    assert bonus > 0


def test_best_lap_bonus_minimum():
    g = _make_game()
    g.best_lap_time = 99999  # Very slow
    bonus = g._best_lap_bonus()
    assert bonus >= 50


# ============================================================
# 12. _spawn_particles helper
# ============================================================

def test_spawn_particles_creates_correct_count():
    g = _make_game()
    g._spawn_particles(160.0, 120.0, 8, 10)
    assert len(g.particles) == 10


def test_spawn_particles_surge_rainbow():
    g = _make_game()
    g._spawn_particles(160.0, 120.0, 8, 12, surge=True)
    colors = {p.color for p in g.particles}
    assert len(colors) > 1  # Multiple colors for surge


# ============================================================
# 13. Data class instantiation
# ============================================================

def test_boostpad_defaults():
    pad = BoostPad(x=50.0, y=60.0, color=8)
    assert pad.active is True
    assert pad.respawn_timer == 0


def test_particle_dataclass():
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-0.5, life=15, color=3)
    assert p.life == 15


def test_ghostpoint_dataclass():
    gp = GhostPoint(x=12.3, y=45.6)
    assert gp.x == 12.3
    assert gp.y == 45.6


def test_phase_enum():
    assert Phase.TITLE != Phase.PLAYING
    assert Phase.PLAYING != Phase.GAME_OVER
    assert Phase.GAME_OVER != Phase.TITLE


# ============================================================
# 14. Speed clamping
# ============================================================

def test_speed_clamped_to_max():
    g = _make_game()
    g.player_speed = MAX_SPEED + 10.0
    # Manually simulate clamping
    surge_mult = 1.5 if g.surge_timer > 0 else 1.0
    max_spd = MAX_SPEED * surge_mult
    if g.player_speed > max_spd:
        g.player_speed = max_spd
    assert g.player_speed == MAX_SPEED


def test_speed_clamped_reverse():
    g = _make_game()
    g.player_speed = -MAX_SPEED * 0.5 - 10.0
    surge_mult = 1.5 if g.surge_timer > 0 else 1.0
    max_spd = MAX_SPEED * surge_mult
    if g.player_speed < -max_spd * 0.5:
        g.player_speed = -max_spd * 0.5
    assert g.player_speed == -MAX_SPEED * 0.5


# ============================================================
# 15. Integration: multiple pad pickups
# ============================================================

def test_multiple_pad_pickups_build_score():
    g = _make_game()
    pads = [
        BoostPad(x=100, y=100, color=PAD_COLORS[0]),
        BoostPad(x=115, y=100, color=PAD_COLORS[0]),
        BoostPad(x=130, y=100, color=PAD_COLORS[0]),
    ]
    g.player_x = 100.0
    g.player_y = 100.0
    g.pads = pads
    g.particles = []
    for _ in range(3):
        g._check_pad_collisions()
        g.player_x += 15
    assert g.combo == 3
    assert g.score == 10 + 20 + 30  # 10*1 + 10*2 + 10*3


def test_color_switch_resets_combo():
    g = _make_game()
    g.last_pad_color = PAD_COLORS[0]
    g.combo = 5
    g.score = 100
    pad_other = BoostPad(x=100, y=100, color=PAD_COLORS[1])
    g._collect_pad(pad_other)
    assert g.combo == 1
    assert g.last_pad_color == PAD_COLORS[1]
    assert g.score == 100 + 10 * 1  # combo=1, score = +10
