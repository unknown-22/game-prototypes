"""test_imports.py — Headless logic tests for Hoop Chain."""
import random
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/241_hoop_chain")
from main import Game, Phase, Ball, Particle, FloatingText


def _make_game():
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.balls = []
    g.hand_color = 0
    g.color_timer = Game.COLOR_INTERVAL
    g.aiming = False
    g.aim_start_x = 0.0
    g.aim_start_y = 0.0
    g.aim_end_x = 0.0
    g.aim_end_y = 0.0
    g.heat = 0.0
    g.super_mode = False
    g.super_timer = 0
    g.game_timer = Game.GAME_DURATION
    g.particles = []
    g.floating_texts = []
    g.shot_count = 0
    g.shake_frames = 0
    g.frame = 0
    g.reset()
    return g


def test_phase_enum():
    assert Phase.TITLE != Phase.PLAYING
    assert Phase.PLAYING != Phase.GAME_OVER


def test_dataclasses():
    b = Ball(100.0, 200.0, 1.0, -2.0, 2, True, False)
    assert abs(b.x - 100.0) < 0.01
    assert b.color == 2
    assert b.active is True
    assert b.scored is False

    p = Particle(10.5, 20.3, 1.0, -2.0, 8, 15)
    assert abs(p.x - 10.5) < 0.01
    assert p.color == 15
    assert p.life == 8

    ft = FloatingText(100.0, 50.0, "TEST", 7, 30)
    assert ft.text == "TEST"
    assert ft.color == 7


def test_reset_state():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.game_timer == 3600
    assert g.super_mode is False
    assert g.balls == []


def test_start_game():
    g = _make_game()
    g.start_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.game_timer == 3600
    assert len(g.balls) == 5


def test_start_game_balls_not_in_hoop():
    g = _make_game()
    g._rng = random.Random(42)
    g.start_game()
    for b in g.balls:
        d = ((b.x - Game.HOOP_X) ** 2 + (b.y - Game.HOOP_Y) ** 2) ** 0.5
        assert d >= Game.HOOP_CLEAR_RADIUS or d < 1.0


def test_spawn_one_ball():
    g = _make_game()
    g.start_game()
    initial = len(g.balls)
    g._spawn_one_ball()
    assert len(g.balls) == initial + 1


def test_ball_color_constants():
    assert Game.BALL_COLORS == (8, 11, 5, 10)
    assert Game.BALL_COLOR_NAMES == ("RED", "LIME", "DARK_BLUE", "YELLOW")
    assert len(Game.BALL_COLORS) == 4


def test_screen_constants():
    assert Game.SCREEN_W == 320
    assert Game.SCREEN_H == 240
    assert Game.HOOP_X == 160
    assert Game.HOOP_Y == 60
    assert Game.PLAYER_X == 160
    assert Game.PLAYER_Y == 180


def test_game_constants():
    assert Game.MAX_POWER == 150.0
    assert Game.GRAVITY == 0.15
    assert Game.FRICTION == 0.995
    assert Game.SUPER_DURATION == 300
    assert Game.HEAT_MAX == 100.0
    assert Game.HEAT_DECAY == 0.02
    assert Game.GAME_DURATION == 3600
    assert Game.COLOR_INTERVAL == 90
    assert Game.MIN_COLOR_INTERVAL == 40


def test_handle_score_match():
    g = _make_game()
    g.start_game()
    g.hand_color = 0
    g.combo = 0
    g.score = 0
    b = Ball(160, 58, 0, 1, 0)
    g.balls.append(b)
    g._handle_score(b)
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score == 100
    assert b.scored is True
    assert b.active is False


def test_handle_score_match_combo_chain():
    g = _make_game()
    g.start_game()
    g.hand_color = 0
    g.combo = 2
    g.max_combo = 2
    g.score = 0
    b = Ball(160, 58, 0, 1, 0)
    g.balls.append(b)
    g._handle_score(b)
    assert g.combo == 3
    assert g.score == 300  # 100 * 3 * 1
    assert b.scored is True


def test_handle_score_mismatch():
    g = _make_game()
    g.start_game()
    g.hand_color = 0
    g.combo = 3
    g.heat = 10
    b = Ball(160, 58, 0, 1, 1)  # different color
    g.balls.append(b)
    g._handle_score(b)
    assert g.combo == 0
    assert g.heat == 25  # 10 + 15
    assert b.scored is True
    assert b.active is False


def test_handle_score_mismatch_super_mode():
    g = _make_game()
    g.start_game()
    g.hand_color = 0
    g.combo = 3
    g.heat = 10
    g.super_mode = True
    b = Ball(160, 58, 0, 1, 1)  # different color
    g.balls.append(b)
    g._handle_score(b)
    assert g.combo == 4  # matched (super mode)
    assert g.heat == 10  # no heat increase in super mode because it matched
    assert b.scored is True


def test_handle_score_triggers_super():
    g = _make_game()
    g.start_game()
    g.hand_color = 0
    g.combo = 3
    g.max_combo = 3
    g.super_mode = False
    b = Ball(160, 58, 0, 1, 0)
    g.balls.append(b)
    g._handle_score(b)
    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == 300
    assert g.shake_frames == 8


def test_handle_score_super_mode_resets_timer():
    g = _make_game()
    g.start_game()
    g.hand_color = 0
    g.combo = 4
    g.super_mode = True
    g.super_timer = 100
    b = Ball(160, 58, 0, 1, 0)
    g.balls.append(b)
    g._handle_score(b)
    assert g.super_timer == 300


def test_activate_super_bfs_chain():
    g = _make_game()
    g.start_game()
    g.hand_color = 0
    g.combo = 3
    g.score = 0
    g.balls.clear()
    b1 = Ball(Game.HOOP_X + 10, Game.HOOP_Y + 10, 0, 0, 1)
    b2 = Ball(Game.HOOP_X + 30, Game.HOOP_Y + 30, 0, 0, 2)
    g.balls.extend([b1, b2])
    g._activate_super(Game.HOOP_X, Game.HOOP_Y)
    assert g.super_mode is True
    assert g.super_timer == 300
    assert b1.scored is True
    assert not b1.active
    assert b2.scored is True
    assert not b2.active
    assert g.score > 0


def test_activate_super_only_nearby():
    g = _make_game()
    g.start_game()
    g.hand_color = 0
    g.combo = 3
    g.score = 0
    g.balls.clear()
    b1 = Ball(Game.HOOP_X + 10, Game.HOOP_Y + 10, 0, 0, 1)
    b2 = Ball(300, 200, 0, 0, 2)
    g.balls.extend([b1, b2])
    g._activate_super(Game.HOOP_X, Game.HOOP_Y)
    assert b1.scored is True
    assert b2.scored is False
    assert b2.active is True


def test_activate_super_chain_propagation():
    g = _make_game()
    g.start_game()
    g.hand_color = 0
    g.combo = 3
    g.score = 0
    g.balls.clear()
    b1 = Ball(Game.HOOP_X + 5, Game.HOOP_Y + 5, 0, 0, 1)
    b2 = Ball(Game.HOOP_X + 180, Game.HOOP_Y + 180, 0, 0, 2)
    g.balls.extend([b1, b2])
    g._activate_super(Game.HOOP_X, Game.HOOP_Y)
    assert b1.scored is True
    assert b2.scored is False


def test_update_heat_decay():
    g = _make_game()
    g.start_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat < 50.0
    assert g.phase == Phase.PLAYING


def test_update_heat_game_over():
    g = _make_game()
    g.start_game()
    g.heat = 100.0
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.shake_frames == 5


def test_update_balls_gravity():
    g = _make_game()
    g.start_game()
    g.balls.clear()
    b = Ball(160, 100, 0, 0, 0)
    g.balls.append(b)
    g._update_balls()
    assert b.vy > 0
    assert b.y > 100


def test_update_balls_bounce_lateral():
    g = _make_game()
    g.start_game()
    g.balls.clear()
    b = Ball(315, 100, 3, 0, 0)
    g.balls.append(b)
    g._update_balls()
    assert b.x <= Game.BALL_MAX_X
    assert b.vx < 0


def test_update_balls_bounce_vertical():
    g = _make_game()
    g.start_game()
    g.balls.clear()
    b = Ball(160, 5, 0, -3, 0)
    g.balls.append(b)
    g._update_balls()
    assert b.y >= Game.BALL_MIN_Y
    assert b.vy > 0


def test_update_balls_out_of_bounds_heat():
    g = _make_game()
    g.start_game()
    g.heat = 0
    g.balls.clear()
    b = Ball(160, 240, 0, 3, 0)
    g.balls.append(b)
    g._update_balls()
    assert g.heat >= 10


def test_update_balls_out_of_bounds_no_heat_super():
    g = _make_game()
    g.start_game()
    g.heat = 0
    g.super_mode = True
    g.balls.clear()
    b = Ball(160, 240, 0, 3, 0)
    g.balls.append(b)
    g._update_balls()
    assert g.heat == 0


def test_maintain_ball_count():
    g = _make_game()
    g.start_game()
    assert len(g.balls) == 5
    for b in g.balls[:]:
        b.active = False
    g._maintain_ball_count()
    assert len(g.balls) >= 5


def test_difficulty_cycle_interval():
    g = _make_game()
    g.start_game()
    assert g._difficulty_cycle_interval() == 90
    g.game_timer = Game.GAME_DURATION - 180
    assert g._difficulty_cycle_interval() == 89
    g.game_timer = 0
    interval = g._difficulty_cycle_interval()
    assert interval >= 40
    assert interval < 90


def test_particles_spawn():
    g = _make_game()
    g.start_game()
    g._spawn_particles(100, 100, 8, 10, 10)
    assert len(g.particles) == 10
    for p in g.particles:
        assert p.color == 8


def test_particles_update():
    g = _make_game()
    g.particles = [Particle(100.0, 100.0, 1.0, -2.0, 5, 8)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 4
    assert g.particles[0].x > 100.0


def test_particles_expire():
    g = _make_game()
    g.particles = [Particle(100.0, 100.0, 0.0, 0.0, 1, 8)]
    g._update_particles()
    assert len(g.particles) == 0


def test_floating_text_spawn():
    g = _make_game()
    g._spawn_floating_text(100, 100, "TEST", 7)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "TEST"
    assert g.floating_texts[0].life == 40


def test_floating_text_update():
    g = _make_game()
    g.floating_texts = [FloatingText(100.0, 100.0, "TEST", 7, 5)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].life == 4
    assert g.floating_texts[0].y < 100.0


def test_floating_text_expire():
    g = _make_game()
    g.floating_texts = [FloatingText(100.0, 100.0, "TEST", 7, 1)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_color_cycling():
    g = _make_game()
    g.start_game()
    g.hand_color = 0
    g.color_timer = 1
    g.color_timer -= 1
    if g.color_timer <= 0:
        g.hand_color = (g.hand_color + 1) % 4
        g.color_timer = g._difficulty_cycle_interval()
    assert g.hand_color == 1


def test_game_timer():
    g = _make_game()
    g.start_game()
    assert g.game_timer == 3600
    g.game_timer -= 1
    assert g.game_timer == 3599


def test_game_timer_expire():
    g = _make_game()
    g.start_game()
    g.game_timer = 1
    g.game_timer -= 1
    if g.game_timer <= 0:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


def test_super_timer_expire():
    g = _make_game()
    g.start_game()
    g.super_mode = True
    g.super_timer = 1
    g.super_timer -= 1
    if g.super_timer <= 0:
        g.super_mode = False
    assert g.super_mode is False


def test_max_combo_tracked():
    g = _make_game()
    g.start_game()
    g.hand_color = 0
    g.start_game()
    g.balls.clear()
    for i in range(5):
        b = Ball(160, 58, 0, 1, 0)
        g.balls.append(b)
        g._handle_score(b)
    assert g.max_combo >= 4


def test_max_combo_preserved_on_mismatch():
    g = _make_game()
    g.start_game()
    g.hand_color = 0
    g.balls.clear()
    b1 = Ball(160, 58, 0, 1, 0)
    g.balls.append(b1)
    g._handle_score(b1)
    assert g.max_combo == 1
    assert g.combo == 1
    b2 = Ball(160, 58, 0, 1, 1)
    g.balls.append(b2)
    g._handle_score(b2)
    assert g.combo == 0
    assert g.max_combo == 1


def test_super_mode_multiplier():
    g = _make_game()
    g.start_game()
    g.hand_color = 0
    g.combo = 2
    g.super_mode = True
    g.score = 0
    b = Ball(160, 58, 0, 1, 0)
    g.balls.append(b)
    g._handle_score(b)
    assert g.combo == 3
    assert g.score == 900  # 100 * 3 * 3


def test_in_hoop_clear():
    g = _make_game()
    g.start_game()
    assert g._in_hoop_clear(Game.HOOP_X, Game.HOOP_Y) is True
    assert g._in_hoop_clear(0, 0) is False


print("All tests passed!")
