"""test_imports.py — Headless logic tests for COLOR CATCH."""
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/068_color_catch")

from main import (
    Game,
    FallingObject,
    Particle,
    Phase,
    OBJECT_COLORS,
    MAX_MISSES,
    SUPER_COMBO_THRESHOLD,
    SUPER_DURATION,
    BASE_CATCH_SCORE,
    SCREEN_W,
    SCREEN_H,
    CATCHER_Y,
    CATCHER_W,
    CATCHER_W_SUPER,
    OBJECT_SIZE,
    OBJECT_SPEED_INITIAL,
    OBJECT_SPEED_INCREASE,
    SPAWN_INTERVAL_INITIAL,
    SPAWN_INTERVAL_DECREASE,
    SPAWN_INTERVAL_MIN,
)


# ── Helper ────────────────────────────────────────────────────────────

def _make_game(seed: int = 42) -> Game:
    """Create a Game instance bypassing pyxel.init for headless testing."""
    g = Game.__new__(Game)
    g._rng = __import__("random").Random(seed)
    g.reset()
    return g


# ── Dataclass tests ────────────────────────────────────────────────────

def test_falling_object_defaults() -> None:
    obj = FallingObject(x=100.0, y=50.0, color=OBJECT_COLORS[0], speed=80.0)
    assert obj.x == 100.0
    assert obj.y == 50.0
    assert obj.color == OBJECT_COLORS[0]
    assert obj.speed == 80.0


def test_particle_defaults() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, color=8, life=12)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.color == 8
    assert p.life == 12


# ── Phase enum tests ───────────────────────────────────────────────────

def test_phase_values() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    assert len(list(Phase)) == 3


# ── Constants tests ────────────────────────────────────────────────────

def test_constants() -> None:
    assert MAX_MISSES == 5
    assert SUPER_COMBO_THRESHOLD == 5
    assert SUPER_DURATION == 5.0
    assert BASE_CATCH_SCORE == 10
    assert len(OBJECT_COLORS) == 4
    assert CATCHER_W == 40
    assert CATCHER_W_SUPER == 80


# ── Reset / start game tests ───────────────────────────────────────────

def test_reset_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.misses == 0
    assert g.catcher_x == SCREEN_W / 2
    assert len(g.objects) == 0
    assert len(g.particles) == 0
    assert g._elapsed_time == 0.0
    assert g._spawn_timer == 0.0
    assert g._prev_catch_color is None
    assert g._super_timer == 0.0


def test_start_game_transitions_to_playing() -> None:
    g = _make_game()
    g._start_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.misses == 0


# ── Object speed tests ─────────────────────────────────────────────────

def test_get_current_object_speed_zero() -> None:
    assert Game._get_current_object_speed(0.0) == OBJECT_SPEED_INITIAL


def test_get_current_object_speed_right_before_increase() -> None:
    assert Game._get_current_object_speed(9.99) == OBJECT_SPEED_INITIAL


def test_get_current_object_speed_after_10s() -> None:
    assert Game._get_current_object_speed(10.0) == OBJECT_SPEED_INITIAL + OBJECT_SPEED_INCREASE


def test_get_current_object_speed_after_20s() -> None:
    assert Game._get_current_object_speed(20.0) == OBJECT_SPEED_INITIAL + 2 * OBJECT_SPEED_INCREASE


def test_get_current_object_speed_capped() -> None:
    speed = Game._get_current_object_speed(1000.0)
    assert speed == 200.0


# ── Spawn interval tests ───────────────────────────────────────────────

def test_get_spawn_interval_zero() -> None:
    assert Game._get_spawn_interval(0.0) == SPAWN_INTERVAL_INITIAL


def test_get_spawn_interval_after_10s() -> None:
    assert Game._get_spawn_interval(10.0) == SPAWN_INTERVAL_INITIAL - SPAWN_INTERVAL_DECREASE


def test_get_spawn_interval_min() -> None:
    ival = Game._get_spawn_interval(1000.0)
    assert ival == SPAWN_INTERVAL_MIN


# ── Spawn object tests ─────────────────────────────────────────────────

def test_spawn_object_returns_falling_object() -> None:
    g = _make_game()
    g._elapsed_time = 0.0
    obj = g._spawn_object()
    assert isinstance(obj, FallingObject)
    assert obj.y == float(-OBJECT_SIZE)
    assert obj.color in OBJECT_COLORS
    assert OBJECT_SIZE <= obj.x <= SCREEN_W - OBJECT_SIZE
    assert obj.speed == OBJECT_SPEED_INITIAL


def test_spawn_object_with_elapsed_time() -> None:
    g = _make_game()
    g._elapsed_time = 30.0
    obj = g._spawn_object()
    assert obj.speed == OBJECT_SPEED_INITIAL + 3 * OBJECT_SPEED_INCREASE


# ── Catcher width tests ────────────────────────────────────────────────

def test_catcher_width_normal() -> None:
    g = _make_game()
    assert g._catcher_width() == float(CATCHER_W)


def test_catcher_width_super() -> None:
    g = _make_game()
    g._super_timer = 3.0
    assert g._catcher_width() == float(CATCHER_W_SUPER)


# ── Update objects tests ───────────────────────────────────────────────

def test_update_objects_moves_down() -> None:
    g = _make_game()
    obj = FallingObject(x=100.0, y=0.0, color=OBJECT_COLORS[0], speed=60.0)
    g.objects.append(obj)
    g._update_objects(1.0)
    assert obj.y == 60.0
    assert len(g.objects) == 1


def test_update_objects_removes_off_screen() -> None:
    g = _make_game()
    obj = FallingObject(x=100.0, y=SCREEN_H + 50.0, color=OBJECT_COLORS[0], speed=60.0)
    g.objects.append(obj)
    missed = g._update_objects(0.1)
    assert len(g.objects) == 0
    assert len(missed) == 1
    assert missed[0] is obj


def test_update_objects_does_not_remove_visible() -> None:
    g = _make_game()
    obj = FallingObject(x=100.0, y=SCREEN_H - 10.0, color=OBJECT_COLORS[0], speed=60.0)
    g.objects.append(obj)
    missed = g._update_objects(0.1)
    assert len(g.objects) == 1
    assert len(missed) == 0


# ── Check catch tests ──────────────────────────────────────────────────

def test_check_catch_true_centered() -> None:
    g = _make_game()
    g.catcher_x = 160.0
    obj = FallingObject(x=160.0, y=CATCHER_Y, color=OBJECT_COLORS[0], speed=60.0)
    assert g._check_catch(obj) is True


def test_check_catch_true_left_edge() -> None:
    g = _make_game()
    g.catcher_x = 160.0
    hw = CATCHER_W / 2
    obj = FallingObject(x=160.0 - hw, y=CATCHER_Y, color=OBJECT_COLORS[0], speed=60.0)
    assert g._check_catch(obj) is True


def test_check_catch_false_beyond_left() -> None:
    g = _make_game()
    g.catcher_x = 160.0
    hw = CATCHER_W / 2
    obj = FallingObject(x=160.0 - hw - OBJECT_SIZE, y=CATCHER_Y, color=OBJECT_COLORS[0], speed=60.0)
    assert g._check_catch(obj) is False


def test_check_catch_false_above_catcher() -> None:
    g = _make_game()
    g.catcher_x = 160.0
    obj = FallingObject(x=160.0, y=CATCHER_Y - 20.0, color=OBJECT_COLORS[0], speed=60.0)
    assert g._check_catch(obj) is False


def test_check_catch_false_below_catcher() -> None:
    g = _make_game()
    g.catcher_x = 160.0
    obj = FallingObject(x=160.0, y=CATCHER_Y + 20.0, color=OBJECT_COLORS[0], speed=60.0)
    assert g._check_catch(obj) is False


def test_check_catch_super_wider_check() -> None:
    g = _make_game()
    g.catcher_x = 160.0
    g._super_timer = 3.0
    hw = CATCHER_W_SUPER / 2
    obj = FallingObject(x=160.0 + hw, y=CATCHER_Y, color=OBJECT_COLORS[0], speed=60.0)
    assert g._check_catch(obj) is True


# ── Handle catch tests ─────────────────────────────────────────────────

def test_handle_catch_first_catch() -> None:
    g = _make_game()
    obj = FallingObject(x=160.0, y=CATCHER_Y, color=OBJECT_COLORS[0], speed=60.0)
    points = g._handle_catch(obj)
    assert g.combo == 1
    assert g._prev_catch_color == OBJECT_COLORS[0]
    assert g.score == points
    assert points == int(BASE_CATCH_SCORE * 1.5)  # combo=1 => 1+1*0.5=1.5


def test_handle_catch_same_color_combo() -> None:
    g = _make_game()
    g._prev_catch_color = OBJECT_COLORS[0]
    g.combo = 1
    g.score = 15
    obj = FallingObject(x=160.0, y=CATCHER_Y, color=OBJECT_COLORS[0], speed=60.0)
    points = g._handle_catch(obj)
    assert g.combo == 2
    assert points == int(BASE_CATCH_SCORE * 2.0)  # combo=2 => 1+2*0.5=2.0


def test_handle_catch_different_color_resets_combo() -> None:
    g = _make_game()
    g._prev_catch_color = OBJECT_COLORS[0]
    g.combo = 3
    g.score = 100
    obj = FallingObject(x=160.0, y=CATCHER_Y, color=OBJECT_COLORS[1], speed=60.0)
    points = g._handle_catch(obj)
    assert g.combo == 1
    assert g._prev_catch_color == OBJECT_COLORS[1]
    assert points == int(BASE_CATCH_SCORE * 1.5)  # combo=1 => 1.5x


def test_handle_catch_triggers_super_mode() -> None:
    g = _make_game()
    g._prev_catch_color = OBJECT_COLORS[0]
    g.combo = 4
    obj = FallingObject(x=160.0, y=CATCHER_Y, color=OBJECT_COLORS[0], speed=60.0)
    g._handle_catch(obj)
    assert g.combo == 5
    assert g._super_timer == SUPER_DURATION


def test_handle_catch_super_mode_scoring() -> None:
    g = _make_game()
    g._super_timer = 3.0
    g.combo = 5
    obj = FallingObject(x=160.0, y=CATCHER_Y, color=OBJECT_COLORS[0], speed=60.0)
    points = g._handle_catch(obj)
    assert g.combo == 6
    # combo=6 => 1+6*0.5=4.0, *3 super = 12x, 10*12=120
    assert points == int(BASE_CATCH_SCORE * (1.0 + 6 * 0.5) * 3)


def test_handle_catch_updates_max_combo() -> None:
    g = _make_game()
    g._prev_catch_color = OBJECT_COLORS[0]
    g.combo = 2
    g.max_combo = 2
    obj = FallingObject(x=160.0, y=CATCHER_Y, color=OBJECT_COLORS[0], speed=60.0)
    g._handle_catch(obj)
    assert g.max_combo == 3
    assert g.combo == 3


def test_handle_catch_spawns_particles() -> None:
    g = _make_game()
    obj = FallingObject(x=160.0, y=CATCHER_Y, color=OBJECT_COLORS[0], speed=60.0)
    g._handle_catch(obj)
    assert len(g.particles) == 6  # normal catch


def test_handle_catch_super_spawns_more_particles() -> None:
    g = _make_game()
    g._super_timer = 3.0
    obj = FallingObject(x=160.0, y=CATCHER_Y, color=OBJECT_COLORS[0], speed=60.0)
    g._handle_catch(obj)
    assert len(g.particles) == 12  # super catch


# ── Handle miss tests ──────────────────────────────────────────────────

def test_handle_miss_increments_misses() -> None:
    g = _make_game()
    obj = FallingObject(x=160.0, y=SCREEN_H, color=OBJECT_COLORS[0], speed=60.0)
    g._handle_miss(obj)
    assert g.misses == 1
    assert g.combo == 0
    assert g._prev_catch_color is None


def test_handle_miss_game_over_on_max_misses() -> None:
    g = _make_game()
    g.misses = 4
    obj = FallingObject(x=160.0, y=SCREEN_H, color=OBJECT_COLORS[0], speed=60.0)
    g._handle_miss(obj)
    assert g.misses == 5
    assert g.phase == Phase.GAME_OVER


def test_handle_miss_spawns_particles() -> None:
    g = _make_game()
    obj = FallingObject(x=160.0, y=SCREEN_H, color=OBJECT_COLORS[0], speed=60.0)
    g._handle_miss(obj)
    assert len(g.particles) == 3


# ── Super timer tests ──────────────────────────────────────────────────

def test_update_super_timer_decrements() -> None:
    g = _make_game()
    g._super_timer = 3.0
    ended = g._update_super_timer(0.5)
    assert g._super_timer == 2.5
    assert ended is False


def test_update_super_timer_ends() -> None:
    g = _make_game()
    g._super_timer = 0.1
    g.combo = 7
    g._prev_catch_color = OBJECT_COLORS[0]
    ended = g._update_super_timer(0.2)
    assert g._super_timer == 0.0
    assert ended is True
    assert g.combo == 0
    assert g._prev_catch_color is None


def test_update_super_timer_noop_when_zero() -> None:
    g = _make_game()
    g._super_timer = 0.0
    ended = g._update_super_timer(1.0)
    assert g._super_timer == 0.0
    assert ended is False


# ── Particle tests ─────────────────────────────────────────────────────

def test_spawn_particles_adds_particles() -> None:
    g = _make_game()
    g._spawn_particles(160.0, 100.0, OBJECT_COLORS[0], 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color == OBJECT_COLORS[0]
        assert p.life >= 12


def test_update_particles_moves_and_decays() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=50.0, vx=1.0, vy=-2.0, color=8, life=5)
    g.particles.append(p)
    g._update_particles()
    assert p.x == 101.0
    assert p.y == 48.0
    assert p.vy == -1.9
    assert p.life == 4


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    p = Particle(x=100.0, y=50.0, vx=1.0, vy=-2.0, color=8, life=1)
    g.particles.append(p)
    g._update_particles()
    assert len(g.particles) == 0


# ── Combo scoring tests ────────────────────────────────────────────────

def test_combo_multiplier_values() -> None:
    """Verify combo multiplier formula: 1 + combo * 0.5."""
    g = _make_game()
    obj = FallingObject(x=160.0, y=CATCHER_Y, color=OBJECT_COLORS[0], speed=60.0)

    g._prev_catch_color = None
    g._handle_catch(obj)  # combo becomes 1, points = 10*1.5 = 15
    assert g.score == 15

    g._handle_catch(obj)  # combo becomes 2, points = 10*2.0 = 20
    assert g.score == 35

    g._handle_catch(obj)  # combo becomes 3, points = 10*2.5 = 25
    assert g.score == 60

    g._handle_catch(obj)  # combo becomes 4, points = 10*3.0 = 30
    assert g.score == 90

    g._handle_catch(obj)  # combo becomes 5, points = 10*3.5 = 35, triggers super
    assert g.score == 125
    assert g._super_timer == SUPER_DURATION


# ── Flow tests ─────────────────────────────────────────────────────────

def test_full_miss_flow() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    # objects fall, miss 5 times
    objs = [
        FallingObject(x=160.0, y=SCREEN_H + 20.0, color=OBJECT_COLORS[i % 4], speed=60.0)
        for i in range(5)
    ]
    g.objects.extend(objs)
    missed = g._update_objects(0.1)
    assert len(missed) == 5
    for obj in missed:
        g._handle_miss(obj)
    assert g.misses == 5
    assert g.phase == Phase.GAME_OVER


def test_catch_then_miss_resets_combo() -> None:
    g = _make_game()
    g._prev_catch_color = OBJECT_COLORS[0]
    g.combo = 3
    obj_miss = FallingObject(x=160.0, y=SCREEN_H + 50.0, color=OBJECT_COLORS[1], speed=60.0)
    g.objects.append(obj_miss)
    missed = g._update_objects(0.1)
    g._handle_miss(missed[0])
    assert g.combo == 0
    assert g._prev_catch_color is None


def test_spawn_interval_produces_correct_count() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    # elapsed=0, interval=0.8s, dt=0.0333s per frame
    # Add 0.8 of timer, should spawn 1
    g._spawn_timer = 0.8
    interval = g._get_spawn_interval(0.0)
    count = 0
    while g._spawn_timer >= interval:
        g._spawn_timer -= interval
        g.objects.append(g._spawn_object())
        count += 1
    assert count == 1
    assert len(g.objects) == 1


def test_combo_does_not_trigger_super_below_threshold() -> None:
    g = _make_game()
    g._prev_catch_color = OBJECT_COLORS[0]
    g.combo = 3
    obj = FallingObject(x=160.0, y=CATCHER_Y, color=OBJECT_COLORS[0], speed=60.0)
    g._handle_catch(obj)
    assert g.combo == 4
    assert g._super_timer == 0.0  # Not triggered yet


print("All tests passed!")
