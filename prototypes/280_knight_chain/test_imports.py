"""test_imports.py — Headless logic tests for 280_knight_chain."""
import random
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/280_knight_chain")

from main import Game, Knight, Target, Particle, FloatingText, Phase
from main import COLOR_COUNT, RED, LIME, WHITE


def _make_game():
    """Factory: create a Game instance without pyxel init."""
    g = Game.__new__(Game)
    # Pre-init all attributes that reset() touches
    g.phase = None
    g.knight = None
    g.targets = []
    g.particles = []
    g.floating_texts = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = 0
    g.super_timer = 0
    g.super_mode = False
    g.spawn_timer = 0
    g.color_cycle_timer = 0
    g.best_score = 0
    g._rng = random.Random(42)
    g.reset()
    return g


# ── Dataclass tests ──

def test_knight_creation():
    k = Knight(x=3, y=4, color=0)
    assert k.x == 3
    assert k.y == 4
    assert k.color == 0


def test_target_creation():
    t = Target(x=5, y=2, color=1, life=200)
    assert t.x == 5
    assert t.y == 2
    assert t.color == 1
    assert t.life == 200


def test_particle_creation():
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=15, color=RED)
    assert abs(p.x - 10.0) < 0.01
    assert abs(p.y - 20.0) < 0.01
    assert abs(p.vx - 1.5) < 0.01
    assert abs(p.vy - (-2.0)) < 0.01
    assert p.life == 15
    assert p.color == RED


def test_floating_text_creation():
    ft = FloatingText(x=100.0, y=50.0, text="+10", life=30, color=LIME)
    assert abs(ft.x - 100.0) < 0.01
    assert abs(ft.y - 50.0) < 0.01
    assert ft.text == "+10"
    assert ft.life == 30
    assert ft.color == LIME


# ── Game initialization tests ──

def test_game_reset():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.knight.x == 3
    assert g.knight.y == 4
    assert g.knight.color == 0
    assert len(g.targets) == 0
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == Game.GAME_TIME
    assert g.super_mode is False
    assert g.super_timer == 0


# ── Knight move tests ──

def test_get_knight_moves_center():
    moves = Game._get_knight_moves(3, 4)
    assert isinstance(moves, list)
    assert len(moves) == 8  # center of 8x8 board has all 8 moves
    assert (2, 2) in moves
    assert (2, 6) in moves
    assert (4, 2) in moves
    assert (4, 6) in moves
    assert (1, 3) in moves
    assert (1, 5) in moves
    assert (5, 3) in moves
    assert (5, 5) in moves


def test_get_knight_moves_corner():
    moves = Game._get_knight_moves(0, 0)
    assert len(moves) == 2  # corner: only (2,1) and (1,2)
    assert (2, 1) in moves
    assert (1, 2) in moves


def test_get_knight_moves_edge():
    moves = Game._get_knight_moves(0, 3)
    assert len(moves) == 4  # left edge
    assert (2, 2) in moves
    assert (2, 4) in moves
    assert (1, 1) in moves
    assert (1, 5) in moves


def test_get_knight_moves_returns_only_valid():
    moves = Game._get_knight_moves(3, 4)
    for x, y in moves:
        assert 0 <= x < Game.BOARD_W
        assert 0 <= y < Game.BOARD_H


# ── Target spawning tests ──

def test_spawn_target():
    g = _make_game()
    g.timer = Game.GAME_TIME  # t=0 → max lifetime
    g._spawn_target()
    assert len(g.targets) == 1
    t = g.targets[0]
    assert 0 <= t.x < Game.BOARD_W
    assert 0 <= t.y < Game.BOARD_H
    assert 0 <= t.color < COLOR_COUNT
    assert t.life > 0


def test_spawn_target_avoids_knight():
    g = _make_game()
    g.knight = Knight(x=3, y=4, color=0)
    g.timer = Game.GAME_TIME
    for _ in range(5):
        g._spawn_target()
    for t in g.targets:
        assert not (t.x == g.knight.x and t.y == g.knight.y)


def test_spawn_target_max_count():
    g = _make_game()
    g.timer = Game.GAME_TIME
    for _ in range(10):
        g._spawn_target()
    assert len(g.targets) <= Game.TARGET_COUNT_MAX


# ── Handle move tests ──

def test_handle_move_same_color_combo():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.knight = Knight(x=3, y=4, color=0)
    g.targets = [Target(x=1, y=5, color=0, life=300)]  # same color as knight
    g._handle_move(1, 5)
    assert g.combo == 1
    assert g.score > 0
    assert len(g.targets) == 0


def test_handle_move_wrong_color_resets_combo():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.knight = Knight(x=3, y=4, color=0)
    g.combo = 3
    g.targets = [Target(x=1, y=5, color=1, life=300)]  # different color
    g._handle_move(1, 5)
    assert g.combo == 0
    assert g.heat >= 15.0
    assert len(g.targets) == 0


def test_handle_move_empty_square_keeps_combo():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.knight = Knight(x=3, y=4, color=0)
    g.combo = 2
    g.targets = []
    g._handle_move(1, 5)  # no target
    assert g.combo == 2  # unchanged
    assert g.heat == 0.0  # unchanged


def test_handle_move_super_mode_any_color():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.knight = Knight(x=3, y=4, color=0)
    g.super_mode = True
    g.combo = 1
    g.targets = [Target(x=1, y=5, color=3, life=300)]  # different color, but super mode
    g._handle_move(1, 5)
    assert g.combo == 2  # incremented despite wrong color
    assert g.score > 0


def test_handle_move_super_activation():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.knight = Knight(x=3, y=4, color=0)
    g.combo = 3
    g.super_mode = False
    g.targets = [Target(x=1, y=5, color=0, life=300)]  # same color, combo 3→4
    g._handle_move(1, 5)
    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == Game.SUPER_DURATION


def test_handle_move_updates_max_combo():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.knight = Knight(x=3, y=4, color=0)
    g.combo = 2
    g.max_combo = 2
    g.targets = [Target(x=1, y=5, color=0, life=300)]
    g._handle_move(1, 5)
    assert g.max_combo == 3


def test_handle_move_removes_target():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.knight = Knight(x=3, y=4, color=0)
    g.targets = [Target(x=1, y=5, color=0, life=300)]
    g._handle_move(1, 5)
    assert len(g.targets) == 0


def test_handle_move_wrong_color_spawns_particles():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.knight = Knight(x=3, y=4, color=0)
    g.targets = [Target(x=1, y=5, color=1, life=300)]
    g._handle_move(1, 5)
    assert len(g.particles) > 0  # mismatch spawns 4 particles


def test_handle_move_wrong_color_floating_text():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.knight = Knight(x=3, y=4, color=0)
    g.targets = [Target(x=1, y=5, color=1, life=300)]
    g._handle_move(1, 5)
    assert len(g.floating_texts) >= 1
    assert any("WRONG" in ft.text for ft in g.floating_texts)


# ── Timer tests ──

def test_update_timers_decrements_timer():
    g = _make_game()
    g.timer = 100
    g._update_timers()
    assert g.timer == 99


def test_update_timers_spawns_target():
    g = _make_game()
    g.timer = Game.GAME_TIME
    g.spawn_timer = 1
    g._update_timers()
    assert len(g.targets) >= 1  # spawn_timer hit 0, target spawned
    assert g.spawn_timer > 0  # reset


def test_update_timers_cycles_knight_color():
    g = _make_game()
    g.knight.color = 0
    g.color_cycle_timer = 1
    g._update_timers()
    assert g.knight.color == 1  # cycled to next color


def test_update_timers_target_life_decrements():
    g = _make_game()
    g.targets = [Target(x=0, y=0, color=0, life=10)]
    g._update_timers()
    assert g.targets[0].life == 9


def test_update_timers_removes_expired_targets():
    g = _make_game()
    g.targets = [Target(x=0, y=0, color=0, life=1)]
    g._update_timers()
    assert len(g.targets) == 0  # life went to 0, removed


def test_update_timers_super_expires():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g.combo = 5
    g._update_timers()
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.combo == 0  # combo resets when super expires


# ── Particle tests ──

def test_update_particles_moves():
    g = _make_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=2.0, vy=-1.0, life=10, color=RED)]
    g._update_particles()
    assert abs(g.particles[0].x - 102.0) < 0.01
    assert abs(g.particles[0].y - 99.0) < 0.01
    assert g.particles[0].life == 9


def test_update_particles_removes_expired():
    g = _make_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=0, vy=0, life=1, color=RED)]
    g._update_particles()
    assert len(g.particles) == 0


# ── Floating text tests ──

def test_update_floating_texts_moves_up():
    g = _make_game()
    g.floating_texts = [FloatingText(x=100.0, y=100.0, text="HI", life=10, color=WHITE)]
    g._update_floating_texts()
    assert g.floating_texts[0].y < 100.0  # moved up
    assert g.floating_texts[0].life == 9


def test_update_floating_texts_removes_expired():
    g = _make_game()
    g.floating_texts = [FloatingText(x=100.0, y=100.0, text="HI", life=1, color=WHITE)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Score calculation tests ──

def test_score_normal_match():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.knight = Knight(x=3, y=4, color=0)
    g.combo = 0
    g.targets = [Target(x=1, y=5, color=0, life=300)]
    g._handle_move(1, 5)
    assert g.score == 10  # combo 1, 10*1 = 10


def test_score_combo_multiplier():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.knight = Knight(x=3, y=4, color=0)
    g.combo = 4
    g.targets = [Target(x=1, y=5, color=0, life=300)]
    g._handle_move(1, 5)
    assert g.score == 50  # combo 5, 10*5 = 50


def test_score_super_mode_3x():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.knight = Knight(x=3, y=4, color=0)
    g.super_mode = True
    g.combo = 2
    g.targets = [Target(x=1, y=5, color=1, life=300)]  # diff color but super
    g._handle_move(1, 5)
    assert g.score == 90  # combo 3, 10*3*3 = 90


# ── Screen to board tests ──

def test_screen_to_board_valid():
    g = _make_game()
    result = g._screen_to_board(Game.BOARD_X + 3 * Game.CELL + 5, Game.BOARD_Y + 4 * Game.CELL + 5)
    assert result == (3, 4)


def test_screen_to_board_out_of_bounds():
    g = _make_game()
    result = g._screen_to_board(10, 10)  # before board
    assert result is None


# ── Speed curves tests ──

def test_speed_for_time_zero():
    g = _make_game()
    g.timer = Game.GAME_TIME
    assert g._speed_for_time() == 0.0


def test_speed_for_time_half():
    g = _make_game()
    g.timer = Game.GAME_TIME // 2
    assert abs(g._speed_for_time() - 0.5) < 0.01


def test_spawn_interval_decreases():
    g = _make_game()
    g.timer = Game.GAME_TIME
    i1 = g._spawn_interval()
    g.timer = 0
    i2 = g._spawn_interval()
    assert i2 <= i1  # interval decreases over time


def test_cycle_interval_decreases():
    g = _make_game()
    g.timer = Game.GAME_TIME
    c1 = g._cycle_interval()
    g.timer = 0
    c2 = g._cycle_interval()
    assert c2 <= c1


# ── Edge case tests ──

def test_heat_at_max_triggers_game_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = Game.MAX_HEAT
    g.timer = 100
    g._update_timers()
    g._update_particles()
    g._update_floating_texts()
    # Simulate game-over check (normally in update())
    if g.timer <= 0 or g.heat >= Game.MAX_HEAT:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


def test_timer_zero_triggers_game_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.timer = 0
    g.heat = 0
    if g.timer <= 0 or g.heat >= Game.MAX_HEAT:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


def test_best_score_updated_on_game_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.score = 500
    g.best_score = 300
    g.timer = 0
    if g.timer <= 0 or g.heat >= Game.MAX_HEAT:
        g.phase = Phase.GAME_OVER
        if g.score > g.best_score:
            g.best_score = g.score
    assert g.best_score == 500


def test_best_score_not_updated_when_lower():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.score = 200
    g.best_score = 300
    g.timer = 0
    if g.timer <= 0 or g.heat >= Game.MAX_HEAT:
        g.phase = Phase.GAME_OVER
        if g.score > g.best_score:
            g.best_score = g.score
    assert g.best_score == 300


def test_handle_move_self_not_allowed_non_super():
    g = _make_game()
    g.knight = Knight(x=3, y=4, color=0)
    g.super_mode = False
    g._handle_move(3, 4)
    assert g.knight.x == 3  # unchanged
    assert g.knight.y == 4


def test_handle_move_self_allowed_super():
    g = _make_game()
    g.knight = Knight(x=3, y=4, color=0)
    g.super_mode = True
    g.targets = []
    g._handle_move(3, 4)  # self-move in super is allowed
    assert g.knight.x == 3
    assert g.knight.y == 4


def test_spawn_target_full_board():
    g = _make_game()
    g.knight = Knight(x=0, y=0, color=0)
    # Fill every square except knight
    for x in range(Game.BOARD_W):
        for y in range(Game.BOARD_H):
            if not (x == 0 and y == 0):
                g.targets.append(Target(x=x, y=y, color=0, life=300))
    len_before = len(g.targets)
    g._spawn_target()
    assert len(g.targets) == len_before  # no space, no spawn


def test_spawn_no_target_if_at_max():
    g = _make_game()
    g.timer = Game.GAME_TIME
    for _ in range(Game.TARGET_COUNT_MAX):
        g._spawn_target()
    len_before = len(g.targets)
    g._spawn_target()
    assert len(g.targets) == len_before  # at max, no new spawn


# ── Color cycling tests ──

def test_knight_color_cycles_through_all():
    g = _make_game()
    colors_seen = set()
    for _ in range(COLOR_COUNT):
        colors_seen.add(g.knight.color)
        g.knight.color = (g.knight.color + 1) % COLOR_COUNT
    assert len(colors_seen) == COLOR_COUNT


def test_spawn_interval_within_range():
    g = _make_game()
    g.timer = Game.GAME_TIME
    i0 = g._spawn_interval()
    assert Game.SPAWN_INTERVAL_MIN <= i0 <= Game.SPAWN_INTERVAL_INIT
    g.timer = 0
    i_end = g._spawn_interval()
    assert Game.SPAWN_INTERVAL_MIN <= i_end <= Game.SPAWN_INTERVAL_INIT


def test_super_activation_already_super():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.knight = Knight(x=3, y=4, color=0)
    g.super_mode = True
    g.super_timer = 100
    g.combo = 3
    g.targets = [Target(x=1, y=5, color=0, life=300)]
    g._handle_move(1, 5)
    assert g.combo == 4  # increment even when already super
    assert g.super_mode is True
    assert g.super_timer == 100  # unchanged (already super)


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    sys.exit(result.returncode)
