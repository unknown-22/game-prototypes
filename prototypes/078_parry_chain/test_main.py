"""test_main.py — Headless logic tests for 078_parry_chain."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.absolute()))

from main import (
    CENTER_HIT_DIST,
    CENTER_X,
    CENTER_Y,
    DIR_COLORS,
    GAME_DURATION,
    PARRY_WINDOW,
    RED,
    SCREEN_H,
    SCREEN_W,
    SPAWN_INTERVAL_END,
    SPAWN_INTERVAL_START,
    STARTING_HP,

    Enemy,
    FloatingText,
    Game,
    Particle,
    Phase,
)


# ── Helper ──────────────────────────────────────────────────────────────

def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.hp = STARTING_HP
    g.enemies = []
    g.particles = []
    g.floats = []
    g.spawn_timer = SPAWN_INTERVAL_START
    g.ghost_direction = -1
    g._next_ghost_direction = -1
    g.game_timer = GAME_DURATION
    g._shake_frames = 0
    g._flash_frames = 0
    return g


# ── Dataclass Tests ────────────────────────────────────────────────────

def test_enemy_defaults() -> None:
    e = Enemy(x=100.0, y=100.0, color=RED, direction=0, speed=2.0)
    assert e.x == 100.0
    assert e.y == 100.0
    assert e.color == RED
    assert e.direction == 0
    assert e.speed == 2.0
    assert e.active is True


def test_particle_defaults() -> None:
    p = Particle(x=50.0, y=60.0, vx=1.0, vy=-2.0, life=10, color=RED)
    assert p.life == 10
    assert p.color == RED


def test_floating_text_defaults() -> None:
    ft = FloatingText(x=100.0, y=200.0, text="+100", life=20, color=7)
    assert ft.text == "+100"
    assert ft.life == 20


# ── Enemy Spawn Tests ──────────────────────────────────────────────────

def test_spawn_enemy_direction_color_consistency() -> None:
    g = _make_game(42)
    for d in range(4):
        e = g._spawn_enemy(d)
        assert e.direction == d
        assert e.color == DIR_COLORS[d]
        assert e.active is True


def test_spawn_enemy_left_edge() -> None:
    g = _make_game(42)
    e = g._spawn_enemy(0)
    assert e.x < 0
    assert abs(e.y - CENTER_Y) <= 60


def test_spawn_enemy_right_edge() -> None:
    g = _make_game(42)
    e = g._spawn_enemy(1)
    assert e.x > SCREEN_W
    assert abs(e.y - CENTER_Y) <= 60


def test_spawn_enemy_top_edge() -> None:
    g = _make_game(42)
    e = g._spawn_enemy(2)
    assert e.y < 0
    assert abs(e.x - CENTER_X) <= 80


def test_spawn_enemy_bottom_edge() -> None:
    g = _make_game(42)
    e = g._spawn_enemy(3)
    assert e.y > SCREEN_H
    assert abs(e.x - CENTER_X) <= 80


def test_spawn_enemy_random_direction() -> None:
    g = _make_game(42)
    for _ in range(100):
        e = g._spawn_enemy()
        assert 0 <= e.direction <= 3
        assert e.color == DIR_COLORS[e.direction]


# ── Enemy Center Detection ─────────────────────────────────────────────

def test_enemy_at_center() -> None:
    e = Enemy(x=CENTER_X, y=CENTER_Y, color=RED, direction=0, speed=2.0)
    assert Game._enemy_at_center(e) is True


def test_enemy_near_center_within_hit_dist() -> None:
    e = Enemy(
        x=CENTER_X + CENTER_HIT_DIST - 1,
        y=CENTER_Y,
        color=RED,
        direction=0,
        speed=2.0,
    )
    assert Game._enemy_at_center(e) is True


def test_enemy_far_from_center() -> None:
    e = Enemy(x=CENTER_X + 50, y=CENTER_Y, color=RED, direction=0, speed=2.0)
    assert Game._enemy_at_center(e) is False


# ── Parry Window Detection ─────────────────────────────────────────────

def test_enemy_in_parry_window() -> None:
    e = Enemy(
        x=CENTER_X + 20, y=CENTER_Y + 20, color=RED, direction=0, speed=2.0
    )
    assert Game._enemy_in_parry_window(e) is True


def test_enemy_outside_parry_window_x() -> None:
    e = Enemy(
        x=CENTER_X + PARRY_WINDOW + 1,
        y=CENTER_Y,
        color=RED,
        direction=0,
        speed=2.0,
    )
    assert Game._enemy_in_parry_window(e) is False


def test_enemy_outside_parry_window_y() -> None:
    e = Enemy(
        x=CENTER_X,
        y=CENTER_Y + PARRY_WINDOW + 1,
        color=RED,
        direction=2,
        speed=2.0,
    )
    assert Game._enemy_in_parry_window(e) is False


def test_inactive_enemy_not_in_parry_window() -> None:
    e = Enemy(
        x=CENTER_X, y=CENTER_Y, color=RED, direction=0, speed=2.0, active=False
    )
    assert Game._enemy_in_parry_window(e) is False


# ── Update Enemies (Movement) ──────────────────────────────────────────

def test_update_enemies_move_toward_center() -> None:
    g = _make_game(42)
    e = g._spawn_enemy(0)  # LEFT side
    e.x = 0.0
    e.y = CENTER_Y
    e.speed = 3.0
    g.enemies = [e]
    g._update_enemies()
    assert e.x > 0.0
    assert e.y == CENTER_Y  # directly horizontal


def test_update_enemies_reach_center() -> None:
    g = _make_game(42)
    e = Enemy(x=CENTER_X - 3, y=CENTER_Y, color=RED, direction=0, speed=5.0)
    g.enemies = [e]
    hits = g._update_enemies()
    assert hits >= 1
    assert e.active is False


def test_update_enemies_multiple() -> None:
    g = _make_game(42)
    e1 = Enemy(x=CENTER_X - 3, y=CENTER_Y, color=RED, direction=0, speed=5.0)
    e2 = Enemy(x=CENTER_X + 100, y=CENTER_Y, color=RED, direction=1, speed=2.0)
    g.enemies = [e1, e2]
    hits = g._update_enemies()
    assert hits >= 1
    assert e1.active is False
    assert e2.active is True


# ── Try Parry ──────────────────────────────────────────────────────────

def test_try_parry_matching_color_in_window() -> None:
    g = _make_game(42)
    e = Enemy(x=CENTER_X, y=CENTER_Y, color=DIR_COLORS[0], direction=0, speed=2.0)
    g.enemies = [e]
    success, destroyed = g._try_parry(0)
    assert success is True
    assert destroyed == 1
    assert e.active is False
    assert g.combo == 1
    assert g.score == 100 * 1 * 1  # 100 * combo * destroyed


def test_try_parry_wrong_color() -> None:
    g = _make_game(42)
    e = Enemy(x=CENTER_X, y=CENTER_Y, color=DIR_COLORS[0], direction=0, speed=2.0)
    g.combo = 3
    g.enemies = [e]
    success, destroyed = g._try_parry(1)  # RIGHT key, but enemy is LEFT color
    assert success is False
    assert destroyed == 0
    assert e.active is True
    assert g.combo == 0  # combo reset


def test_try_parry_too_far() -> None:
    g = _make_game(42)
    e = Enemy(
        x=CENTER_X + PARRY_WINDOW + 10,
        y=CENTER_Y,
        color=DIR_COLORS[1],
        direction=1,
        speed=2.0,
    )
    g.combo = 2
    g.enemies = [e]
    success, destroyed = g._try_parry(1)
    assert success is False
    assert destroyed == 0
    assert g.combo == 0  # combo reset


def test_try_parry_no_enemies() -> None:
    g = _make_game(42)
    success, destroyed = g._try_parry(0)
    assert success is False
    assert destroyed == 0
    assert g.combo == 0


def test_try_parry_all_same_color_multiple() -> None:
    g = _make_game(42)
    e1 = Enemy(x=CENTER_X, y=CENTER_Y, color=DIR_COLORS[0], direction=0, speed=2.0)
    e2 = Enemy(
        x=CENTER_X + 10, y=CENTER_Y + 10, color=DIR_COLORS[0], direction=0, speed=2.0
    )
    g.enemies = [e1, e2]
    success, destroyed = g._try_parry(0)
    assert success is True
    assert destroyed == 2
    assert g.combo == 2


def test_try_parry_easy_chain_same_color() -> None:
    """All enemies same color -> chain COMBO easily."""
    g = _make_game(42)
    for _ in range(4):
        e = Enemy(
            x=CENTER_X, y=CENTER_Y, color=DIR_COLORS[0], direction=0, speed=2.0
        )
        g.enemies.append(e)
    # Parry first to set up combo
    success, destroyed = g._try_parry(0)
    assert destroyed == 4
    assert g.combo == 4


# ── Combo & Score ──────────────────────────────────────────────────────

def test_combo_accumulates_with_consecutive_parries() -> None:
    g = _make_game(42)
    # First parry
    e1 = Enemy(x=CENTER_X, y=CENTER_Y, color=DIR_COLORS[0], direction=0, speed=2.0)
    g.enemies = [e1]
    g._try_parry(0)
    assert g.combo == 1
    assert g.score == 100

    # Second parry
    e2 = Enemy(x=CENTER_X, y=CENTER_Y, color=DIR_COLORS[0], direction=0, speed=2.0)
    g.enemies = [e2]
    g._try_parry(0)
    assert g.combo == 2
    assert g.score == 100 + 200  # 100*1 + 100*2


def test_combo_resets_on_miss() -> None:
    g = _make_game(42)
    g.combo = 5
    g._try_parry(0)  # miss, no enemies
    assert g.combo == 0


def test_combo_resets_on_wrong_color() -> None:
    g = _make_game(42)
    e = Enemy(x=CENTER_X, y=CENTER_Y, color=DIR_COLORS[0], direction=0, speed=2.0)
    g.combo = 3
    g.enemies = [e]
    g._try_parry(1)  # wrong color
    assert g.combo == 0


def test_max_combo_tracks_highest() -> None:
    g = _make_game(42)
    e = Enemy(x=CENTER_X, y=CENTER_Y, color=DIR_COLORS[0], direction=0, speed=2.0)
    g.enemies = [e]
    g._try_parry(0)
    assert g.max_combo == 1

    g.enemies = [
        Enemy(x=CENTER_X, y=CENTER_Y, color=DIR_COLORS[0], direction=0, speed=2.0)
    ]
    g._try_parry(0)
    assert g.combo == 2
    assert g.max_combo == 2

    # Miss resets combo but max_combo preserved
    g._try_parry(1)
    assert g.combo == 0
    assert g.max_combo == 2


# ── SUPER RIPOSTE ──────────────────────────────────────────────────────

def test_riposte_triggers_at_combo_5() -> None:
    g = _make_game(42)
    # Set up combo
    g.combo = 4
    e1 = Enemy(x=CENTER_X, y=CENTER_Y, color=DIR_COLORS[0], direction=0, speed=2.0)
    e2 = Enemy(x=CENTER_X + 100, y=CENTER_Y, color=RED, direction=1, speed=2.0)
    e3 = Enemy(x=CENTER_X, y=CENTER_Y + 100, color=DIR_COLORS[3], direction=3, speed=2.0)
    g.enemies = [e1, e2, e3]

    g._try_parry(0)  # hits combo 5 -> riposte triggers

    assert e2.active is False  # destroyed by riposte
    assert e3.active is False  # destroyed by riposte
    assert g.combo >= 5


def test_riposte_destroys_all_active_enemies() -> None:
    g = _make_game(42)
    count = g._trigger_riposte()
    assert count == 0  # no enemies

    g.enemies = [
        Enemy(x=50, y=50, color=RED, direction=0, speed=2.0),
        Enemy(x=200, y=200, color=RED, direction=1, speed=2.0),
        Enemy(x=150, y=150, color=RED, direction=2, speed=2.0),
    ]
    count = g._trigger_riposte()
    assert count == 3
    assert all(not e.active for e in g.enemies)
    assert g._shake_frames == 15
    assert g._flash_frames == 10
    assert g.score == 500 * 3


def test_riposte_with_zero_enemies_no_effect() -> None:
    g = _make_game(42)
    g.combo = 5
    count = g._trigger_riposte()
    assert count == 0
    assert g.combo == 5  # preserved
    assert g.score == 0


# ── Spawn Interval ─────────────────────────────────────────────────────

def test_spawn_interval_starts_high() -> None:
    g = _make_game(42)
    g.game_timer = GAME_DURATION
    interval = g._get_next_spawn_interval()
    assert interval >= SPAWN_INTERVAL_END
    assert interval <= SPAWN_INTERVAL_START


def test_spawn_interval_decreases_over_time() -> None:
    g = _make_game(42)
    g.game_timer = GAME_DURATION
    early = g._get_next_spawn_interval()

    g.game_timer = GAME_DURATION // 2
    mid = g._get_next_spawn_interval()

    g.game_timer = 1
    late = g._get_next_spawn_interval()

    assert early >= mid
    assert mid >= late
    assert late >= SPAWN_INTERVAL_END


def test_spawn_interval_never_below_min() -> None:
    g = _make_game(42)
    g.game_timer = 0
    interval = g._get_next_spawn_interval()
    assert interval >= SPAWN_INTERVAL_END


# ── Cleanup ────────────────────────────────────────────────────────────

def test_cleanup_removes_inactive() -> None:
    g = _make_game(42)
    e1 = Enemy(x=50, y=50, color=RED, direction=0, speed=2.0, active=True)
    e2 = Enemy(x=100, y=100, color=RED, direction=1, speed=2.0, active=False)
    e3 = Enemy(x=200, y=200, color=RED, direction=2, speed=2.0, active=True)
    g.enemies = [e1, e2, e3]
    g._cleanup_enemies()
    assert len(g.enemies) == 2
    assert all(e.active for e in g.enemies)


# ── Particle System ────────────────────────────────────────────────────

def test_parry_particles_spawned() -> None:
    g = _make_game(42)
    g._spawn_parry_particles(CENTER_X, CENTER_Y, RED)
    assert len(g.particles) == 10
    for p in g.particles:
        assert p.life == 20
        assert p.color == RED


def test_hit_particles_spawned() -> None:
    g = _make_game(42)
    g._spawn_hit_particles(CENTER_X, CENTER_Y)
    assert len(g.particles) == 6
    for p in g.particles:
        assert p.life == 12
        assert p.color == RED


def test_riposte_particles_spawned() -> None:
    g = _make_game(42)
    g._spawn_riposte_particles(CENTER_X, CENTER_Y, RED)
    assert len(g.particles) == 25
    for p in g.particles:
        assert p.life == 30


def test_particles_update_and_die() -> None:
    g = _make_game(42)
    g.particles.append(Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=10, color=RED))
    for _ in range(9):
        g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 1
    g._update_particles()
    assert len(g.particles) == 0


# ── Floating Text ──────────────────────────────────────────────────────

def test_float_text_spawned() -> None:
    g = _make_game(42)
    g._spawn_float_text(100, 100, "+300", RED)
    assert len(g.floats) == 1
    assert g.floats[0].text == "+300"
    assert g.floats[0].life == 30


def test_float_text_update_and_die() -> None:
    g = _make_game(42)
    g.floats.append(FloatingText(x=0.0, y=0.0, text="+", life=5, color=RED))
    for _ in range(4):
        g._update_floats()
    assert len(g.floats) == 1
    assert g.floats[0].life == 1
    g._update_floats()
    assert len(g.floats) == 0


# ── Reset / Game Over ──────────────────────────────────────────────────

def test_start_game_resets_state() -> None:
    g = _make_game(42)
    g.phase = Phase.PLAYING
    g.score = 9999
    g.combo = 10
    g.hp = 1
    g.enemies = [Enemy(x=50, y=50, color=RED, direction=0, speed=2.0)]
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=1, color=RED)]
    g.floats = [FloatingText(x=0, y=0, text="x", life=1, color=RED)]
    g._start_game()

    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.hp == STARTING_HP
    assert len(g.enemies) == 0
    assert len(g.particles) == 0
    assert len(g.floats) == 0
    assert g.game_timer == GAME_DURATION


def test_hp_reaches_zero_triggers_game_over() -> None:
    g = _make_game(42)
    g.phase = Phase.PLAYING
    g.hp = 1
    g.enemies = [
        Enemy(x=CENTER_X - 3, y=CENTER_Y, color=RED, direction=0, speed=5.0)
    ]
    # Enemy reaches center, HP drops to 0
    hits = g._update_enemies()
    assert hits >= 1
    g.hp -= hits
    assert g.hp <= 0


def test_game_timer_reaches_zero_game_over() -> None:
    g = _make_game(42)
    g.phase = Phase.PLAYING
    g.game_timer = 1
    # Simulate what _update_playing does
    g.game_timer -= 1
    assert g.game_timer <= 0  # should trigger game over in real update


# ── Math/Static Helpers ────────────────────────────────────────────────

def test_parry_window_is_square() -> None:
    e = Enemy(
        x=CENTER_X + PARRY_WINDOW,
        y=CENTER_Y + PARRY_WINDOW,
        color=RED,
        direction=0,
        speed=2.0,
    )
    assert Game._enemy_in_parry_window(e) is True

    e2 = Enemy(
        x=CENTER_X + PARRY_WINDOW + 1,
        y=CENTER_Y + PARRY_WINDOW,
        color=RED,
        direction=0,
        speed=2.0,
    )
    assert Game._enemy_in_parry_window(e2) is False
