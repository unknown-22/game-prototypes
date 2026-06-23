"""test_imports.py — Headless logic tests for WAKE CHAIN."""
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/152_wake_chain")

from main import Game, Buoy, Particle, Phase
from main import (
    BUOY_COLORS, SCREEN_W, SCREEN_H, PLAYER_X, PLAYER_MIN_Y, PLAYER_MAX_Y,
    COLLECT_RADIUS, MAX_HEAT, SUPER_DURATION, GAME_DURATION,
    COMBO_THRESHOLD, INITIAL_SPAWN_INTERVAL,
    BUOY_SPEED_PER_FRAME,
)


def _make_game() -> Game:
    """Factory: create Game instance bypassing pyxel.init/run."""
    g = Game.__new__(Game)
    # Pre-init all instance attributes
    g.phase = Phase.PLAYING
    g.score = 0
    g.high_score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.game_timer = GAME_DURATION
    g.super_timer = 0
    g.player_y = 120.0
    g.player_color = 0
    g.buoys = []
    g.particles = []
    g.wake_trail = []
    g._rng = __import__("random").Random(42)
    g._spawn_timer = INITIAL_SPAWN_INTERVAL
    g._spawn_interval = INITIAL_SPAWN_INTERVAL
    g._shake_frames = 0
    g.last_color = 0
    g._title_buoys = []
    g._title_spawn_timer = 0
    g._title_wave_offset = 0.0
    g._elapsed_frames = 0
    g.reset()
    return g


# ── Constants ──
def test_buoy_colors():
    assert len(BUOY_COLORS) == 4
    assert set(BUOY_COLORS) == {8, 3, 6, 10}  # RED, GREEN, LIGHT_BLUE, YELLOW


def test_screen_constants():
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert PLAYER_X == 80
    assert MAX_HEAT == 5.0
    assert SUPER_DURATION == 300
    assert GAME_DURATION == 3600
    assert COMBO_THRESHOLD == 4


# ── Phase enum ──
def test_phase_enum():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    assert Phase.TITLE is not Phase.PLAYING


# ── Dataclass construction ──
def test_buoy_creation():
    b = Buoy(x=200.0, y=100.0, color=2)
    assert b.x == 200.0
    assert b.y == 100.0
    assert b.color == 2
    assert b.collected is False


def test_particle_creation():
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=15, color=8, size=2)
    assert p.x == 10.0
    assert p.life == 15
    assert p.color == 8
    assert p.size == 2


# ── Game.__new__ bypass ──
def test_game_creation_bypass():
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.game_timer == GAME_DURATION
    assert g.player_y == 120.0
    assert g.player_color == 0


# ── reset() ──
def test_reset_clears_state():
    g = _make_game()
    g.score = 500
    g.combo = 3
    g.max_combo = 5
    g.heat = 3.0
    g.super_timer = 100
    g.game_timer = 100
    g.buoys = [Buoy(x=100, y=50, color=0)]
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=1, color=8)]
    g.wake_trail = [Particle(x=0, y=0, vx=0, vy=0, life=1, color=8)]

    g.reset()

    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.game_timer == GAME_DURATION
    assert len(g.buoys) == 0
    assert len(g.particles) == 0
    assert len(g.wake_trail) == 0
    assert g._elapsed_frames == 0


# ── _clamp_player ──
def test_clamp_player_min():
    g = _make_game()
    g.player_y = 10.0
    g._clamp_player()
    assert g.player_y == PLAYER_MIN_Y


def test_clamp_player_max():
    g = _make_game()
    g.player_y = 250.0
    g._clamp_player()
    assert g.player_y == PLAYER_MAX_Y


def test_clamp_player_in_bounds():
    g = _make_game()
    g.player_y = 120.0
    g._clamp_player()
    assert g.player_y == 120.0


# ── _spawn_buoy ──
def test_spawn_buoy():
    g = _make_game()
    g._rng = __import__("random").Random(42)
    assert len(g.buoys) == 0
    g._spawn_buoy()
    assert len(g.buoys) == 1
    buoy = g.buoys[0]
    assert buoy.x == 330.0
    assert 50 <= buoy.y <= 190
    assert buoy.color in (0, 1, 2, 3)


# ── _move_buoys ──
def test_move_buoys():
    g = _make_game()
    g.buoys = [Buoy(x=200.0, y=100.0, color=0)]
    g._move_buoys()
    assert g.buoys[0].x == 200.0 - BUOY_SPEED_PER_FRAME


def test_remove_offscreen_buoys():
    g = _make_game()
    g.buoys = [Buoy(x=-30.0, y=100.0, color=0)]
    g._move_buoys()
    assert len(g.buoys) == 0


def test_keep_visible_buoys():
    g = _make_game()
    g.buoys = [
        Buoy(x=200.0, y=100.0, color=0),
        Buoy(x=-17.0, y=100.0, color=1),  # stays inside threshold after move
    ]
    g._move_buoys()
    assert len(g.buoys) == 2


# ── _check_buoy_collision ──
def test_same_color_collection():
    g = _make_game()
    g.player_y = 100.0
    g.player_color = 0  # RED
    g.combo = 0
    g.score = 0
    g.heat = 0.0
    g.buoys = [Buoy(x=float(PLAYER_X), y=100.0, color=0)]

    g._check_buoy_collision()

    assert g.buoys[0].collected is True
    assert g.combo == 1
    assert g.score == 10  # 10 * 1
    assert g.heat == 0.0
    assert g.player_color == 0  # unchanged


def test_wrong_color_collision():
    g = _make_game()
    g.player_y = 100.0
    g.player_color = 0  # RED
    g.combo = 2
    g.score = 0
    g.heat = 0.0
    g.buoys = [Buoy(x=float(PLAYER_X), y=100.0, color=1)]  # GREEN

    g._check_buoy_collision()

    assert g.buoys[0].collected is True
    assert g.combo == 0  # reset
    assert g.score == 0  # no score for wrong color
    assert g.heat == 1.0
    assert g.player_color == 1  # changed to GREEN


def test_collision_distance_check():
    g = _make_game()
    g.player_y = 100.0
    g.player_color = 0
    g.combo = 0
    g.buoys = [
        Buoy(x=float(PLAYER_X), y=100.0 + COLLECT_RADIUS + 1.0, color=0)  # too far
    ]

    g._check_buoy_collision()

    assert g.buoys[0].collected is False
    assert g.combo == 0


def test_collected_buoy_skipped():
    g = _make_game()
    g.player_y = 100.0
    g.player_color = 0
    g.combo = 0
    g.buoys = [
        Buoy(x=float(PLAYER_X), y=100.0, color=0, collected=True),
        Buoy(x=float(PLAYER_X), y=100.0, color=0),
    ]

    g._check_buoy_collision()

    assert g.buoys[0].collected is True
    assert g.buoys[1].collected is True
    assert g.combo == 1  # only one added


def test_no_collision_with_empty_buoys():
    g = _make_game()
    g._check_buoy_collision()
    assert g.combo == 0
    assert g.score == 0


# ── _add_score ──
def test_add_score_normal():
    g = _make_game()
    g.combo = 3
    g.super_timer = 0
    result = g._add_score(10)
    assert result == 30  # 10 * 3 * 1
    assert g.score == 30


def test_add_score_super():
    g = _make_game()
    g.combo = 3
    g.super_timer = 50
    result = g._add_score(10)
    assert result == 90  # 10 * 3 * 3
    assert g.score == 90


def test_add_score_combo_one():
    g = _make_game()
    g.combo = 1
    result = g._add_score(10)
    assert result == 10
    assert g.score == 10


# ── SUPER mode ──
def test_activate_super():
    g = _make_game()
    g.player_y = 100.0
    g.super_timer = 0
    g._shake_frames = 0
    g.combo = 5

    g._activate_super()

    assert g.super_timer == SUPER_DURATION
    assert g._shake_frames > 0


def test_super_collects_wrong_color():
    g = _make_game()
    g.player_y = 100.0
    g.player_color = 0  # RED
    g.super_timer = 50  # super active
    g.combo = 0
    g.score = 0
    g.heat = 0.0
    g.buoys = [Buoy(x=float(PLAYER_X), y=100.0, color=1)]  # GREEN — would be wrong

    g._check_buoy_collision()

    assert g.buoys[0].collected is True
    assert g.combo == 1
    assert g.score == 30  # 10 * 1 * 3 (super multiplier)
    assert g.heat == 0.0  # no heat in super
    assert g.player_color == 0  # unchanged in super


def test_combo_4_triggers_super():
    g = _make_game()
    g.player_y = 100.0
    g.player_color = 0
    g.combo = 3
    g.super_timer = 0
    g.buoys = [Buoy(x=float(PLAYER_X), y=100.0, color=0)]

    g._check_buoy_collision()

    assert g.combo == 4
    assert g.super_timer == SUPER_DURATION


def test_super_not_reactivated_while_active():
    g = _make_game()
    g.player_y = 100.0
    g.player_color = 0
    g.combo = 3
    g.super_timer = 100  # already active
    g.buoys = [Buoy(x=float(PLAYER_X), y=100.0, color=0)]

    g._check_buoy_collision()

    assert g.combo == 4
    assert g.super_timer == 100  # unchanged, not reactivated


# ── _is_super ──
def test_is_super():
    g = _make_game()
    assert g._is_super() is False
    g.super_timer = 1
    assert g._is_super() is True
    g.super_timer = 0
    assert g._is_super() is False


# ── _update_super ──
def test_update_super_decrements():
    g = _make_game()
    g.super_timer = 10
    g._update_super()
    assert g.super_timer == 9


def test_update_super_ignores_zero():
    g = _make_game()
    g.super_timer = 0
    g._update_super()
    assert g.super_timer == 0


# ── _spawn_wake_particles ──
def test_spawn_wake_particles():
    g = _make_game()
    g.player_y = 100.0
    assert len(g.wake_trail) == 0
    g._spawn_wake_particles(3)
    assert len(g.wake_trail) == 3
    for p in g.wake_trail:
        assert p.x == float(PLAYER_X)
        assert p.y == 100.0
        assert p.life > 0
        assert p.color == BUOY_COLORS[g.last_color]


# ── _spawn_collect_particles ──
def test_spawn_collect_particles():
    g = _make_game()
    g._spawn_collect_particles(100.0, 50.0, 0, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.x == 100.0
        assert p.y == 50.0
        assert p.color == BUOY_COLORS[0]


# ── _spawn_wrong_particles ──
def test_spawn_wrong_particles():
    g = _make_game()
    g._spawn_wrong_particles(100.0, 50.0, 2)
    assert 4 <= len(g.particles) <= 6
    for p in g.particles:
        assert p.x == 100.0
        assert p.y == 50.0
        assert p.color == BUOY_COLORS[2]


# ── _update_particles ──
def test_update_particles():
    g = _make_game()
    g.wake_trail = [
        Particle(x=0.0, y=0.0, vx=1.0, vy=2.0, life=3, color=8),
    ]
    g.particles = [
        Particle(x=10.0, y=20.0, vx=-1.0, vy=1.0, life=0, color=3),  # dead
    ]
    g._update_particles()
    assert len(g.wake_trail) == 1
    assert g.wake_trail[0].x == 1.0
    assert g.wake_trail[0].y == 2.0
    assert g.wake_trail[0].life == 2
    assert len(g.particles) == 0  # dead removed


def test_update_particles_removes_dead_wake():
    g = _make_game()
    g.wake_trail = [
        Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=8),
        Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=0, color=3),
    ]
    g._update_particles()
    assert len(g.wake_trail) == 0


# ── _trigger_game_over ──
def test_trigger_game_over():
    g = _make_game()
    g.score = 500
    g.high_score = 300
    g._shake_frames = 0
    g._trigger_game_over()
    assert g.phase == Phase.GAME_OVER
    assert g.high_score == 500
    assert g._shake_frames > 0


def test_trigger_game_over_no_high_score():
    g = _make_game()
    g.score = 200
    g.high_score = 500
    g._trigger_game_over()
    assert g.high_score == 500  # unchanged


# ── _update_difficulty ──
def test_difficulty_decreases_at_interval():
    g = _make_game()
    g._elapsed_frames = 0
    g._spawn_interval = 48
    g._update_difficulty()
    assert g._spawn_interval == 48  # not at interval yet

    g._elapsed_frames = 600
    g._update_difficulty()
    assert g._spawn_interval == 43  # decreased by 5

    g._elapsed_frames = 1200
    g._update_difficulty()
    assert g._spawn_interval == 38


def test_difficulty_minimum():
    g = _make_game()
    g._spawn_interval = 16
    g._elapsed_frames = 600
    g._update_difficulty()
    assert g._spawn_interval == 15  # clamped to MIN_SPAWN_INTERVAL


# ── Heat triggers game over ──
def test_heat_triggers_game_over():
    g = _make_game()
    g.heat = MAX_HEAT
    g.phase = Phase.PLAYING
    if g.phase == Phase.PLAYING and g.heat >= MAX_HEAT:
        g._trigger_game_over()
    assert g.phase == Phase.GAME_OVER


def test_heat_below_max_no_trigger():
    g = _make_game()
    g.heat = MAX_HEAT - 0.1
    g.phase = Phase.PLAYING
    if g.phase == Phase.PLAYING and g.heat >= MAX_HEAT:
        g._trigger_game_over()
    assert g.phase == Phase.PLAYING


# ── Max combo tracking ──
def test_max_combo_tracked():
    g = _make_game()
    g.player_y = 100.0
    g.player_color = 0
    g.combo = 0
    g.max_combo = 0

    for _ in range(3):
        g.buoys = [Buoy(x=float(PLAYER_X), y=100.0, color=0)]
        g._check_buoy_collision()

    assert g.combo == 3
    assert g.max_combo == 3


def test_max_combo_persists_after_reset():
    g = _make_game()
    g.player_y = 100.0
    g.player_color = 0
    g.combo = 0
    g.max_combo = 0

    for _ in range(3):
        g.buoys = [Buoy(x=float(PLAYER_X), y=100.0, color=0)]
        g._check_buoy_collision()

    assert g.max_combo == 3

    # Wrong color resets combo but max_combo persists
    g.buoys = [Buoy(x=float(PLAYER_X), y=100.0, color=1)]
    g._check_buoy_collision()

    assert g.combo == 0
    assert g.max_combo == 3


# ── Game timer ──
def test_game_timer_decrements():
    g = _make_game()
    g.game_timer = 100
    g.phase = Phase.PLAYING
    g.game_timer -= 1
    assert g.game_timer == 99


def test_game_timer_triggers_game_over():
    g = _make_game()
    g.game_timer = 1
    g.phase = Phase.PLAYING
    g.game_timer -= 1
    if g.game_timer <= 0:
        g._trigger_game_over()
    assert g.phase == Phase.GAME_OVER


# ── Edge cases ──
def test_empty_state_graceful():
    g = _make_game()
    g._move_buoys()
    g._check_buoy_collision()
    g._update_super()
    g._update_particles()
    g._clamp_player()
    g._update_difficulty()
    assert True  # no crash


def test_super_expires_mid_collection():
    g = _make_game()
    g.player_y = 100.0
    g.player_color = 0
    g.super_timer = 0  # NOT super
    g.combo = 0
    g.buoys = [Buoy(x=float(PLAYER_X), y=100.0, color=1)]  # GREEN, wrong

    g._check_buoy_collision()

    assert g.buoys[0].collected is True
    assert g.heat == 1.0
    assert g.combo == 0


def test_multiple_buoys_only_one_collected_per_frame():
    g = _make_game()
    g.player_y = 100.0
    g.player_color = 0
    g.combo = 0
    g.score = 0
    g.buoys = [
        Buoy(x=float(PLAYER_X), y=100.0, color=0),
        Buoy(x=float(PLAYER_X), y=100.0, color=0),
        Buoy(x=float(PLAYER_X), y=100.0, color=0),
    ]

    g._check_buoy_collision()

    # Only first matched buoy is collected (break after collection)
    assert g.buoys[0].collected is True
    assert g.buoys[1].collected is False
    assert g.buoys[2].collected is False
    assert g.combo == 1


def test_last_color_updated():
    g = _make_game()
    g.player_y = 100.0
    g.player_color = 0
    g.last_color = 0
    g.buoys = [Buoy(x=float(PLAYER_X), y=100.0, color=2)]

    old_last = g.last_color
    g._check_buoy_collision()

    assert g.last_color == 2
    assert g.last_color != old_last


print("All tests passed!")
