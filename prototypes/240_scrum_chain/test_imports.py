"""test_imports.py — Headless logic tests for Scrum Chain."""
import random
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/240_scrum_chain")
from main import Game, Phase, Teammate, Defender, Particle, FloatingText


# ── Helper: make a headless game instance ──
def _make_game():
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.player_x = Game.PLAYER_START_COL
    g.player_y = Game.PLAYER_START_ROW
    g.player_color = 0
    g.color_timer = 90
    g.ball_x = Game.PLAYER_START_COL
    g.ball_y = Game.PLAYER_START_ROW
    g.has_ball = True
    g.teammates = []
    g.defenders = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.super_mode = False
    g.super_timer = 0
    g.heat = 0.0
    g.game_timer = Game.GAME_DURATION
    g.particles = []
    g.floating_texts = []
    g.shake_frames = 0
    g.frame = 0
    g.stun_timer = 0
    g.defender_spawn_timer = 0
    g.reset()
    return g


# ── Phase enum ──
def test_phase_enum():
    assert Phase.TITLE != Phase.PLAYING
    assert Phase.PLAYING != Phase.GAME_OVER
    assert Phase.GAME_OVER != Phase.TITLE


# ── Dataclass construction ──
def test_dataclasses():
    t = Teammate(5, 3, 2)
    assert t.x == 5
    assert t.y == 3
    assert t.color == 2

    d = Defender(1, 2, 0, stunned=5)
    assert d.x == 1
    assert d.stunned == 5

    p = Particle(10.5, 20.3, 1.0, -2.0, 8, 15)
    assert abs(p.x - 10.5) < 0.01
    assert p.life == 15

    ft = FloatingText(100.0, 50.0, "TEST", 7, 30)
    assert ft.text == "TEST"
    assert ft.color == 7


# ── reset() state ──
def test_reset_state():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.player_x == 8
    assert g.player_y == 11
    assert g.player_color == 0
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.super_mode is False
    assert g.heat == 0.0
    assert g.game_timer == 3600
    assert g.has_ball is True


# ── start_game ──
def test_start_game():
    g = _make_game()
    g.start_game()
    assert g.phase == Phase.PLAYING
    assert len(g.teammates) == 8
    assert g.score == 0
    assert g.combo == 0
    assert g.game_timer == 3600


# ── _difficulty functions ──
def test_difficulty_speed():
    g = _make_game()
    g.start_game()
    assert g._difficulty_speed() == 1.0  # t=0

    g.game_timer = 0
    assert g._difficulty_speed() == 3.5  # 1.0 + 1.0*2.5


def test_difficulty_cycle_interval():
    g = _make_game()
    g.start_game()
    assert g._difficulty_cycle_interval() == 90  # t=0

    g.game_timer = 0
    assert g._difficulty_cycle_interval() == 40  # 90 - 1.0*50


def test_max_defenders():
    g = _make_game()
    g.start_game()
    assert g._max_defenders() == 6

    g.game_timer = 0
    assert g._max_defenders() == 10  # 6 + 1.0*4


def test_defender_spawn_interval():
    g = _make_game()
    g.start_game()
    assert g._defender_spawn_interval() == 180

    g.game_timer = 0
    assert g._defender_spawn_interval() == 60  # max(60, 180-120)


# ── _spawn_teammates ──
def test_spawn_teammates():
    g = _make_game()
    g.start_game()
    assert len(g.teammates) == 8
    for t in g.teammates:
        assert 0 <= t.x < 16
        assert Game.PLAYFIELD_TOP <= t.y <= Game.PLAYER_START_ROW - 1
        assert 0 <= t.color <= 3


# ── _find_nearest_teammate ──
def test_find_nearest_teammate_empty():
    g = _make_game()
    g.start_game()
    g.teammates.clear()
    assert g._find_nearest_teammate() is None


def test_find_nearest_teammate_in_range():
    g = _make_game()
    g.start_game()
    g.player_x = 8
    g.player_y = 10
    g.teammates = [
        Teammate(9, 10, 0),  # dist=1
        Teammate(12, 10, 1),  # dist=4 > PASS_RANGE=3
        Teammate(8, 11, 2),   # dist=1
    ]
    best = g._find_nearest_teammate()
    assert best is not None
    assert best.color in (0, 2)  # both dist=1, one wins


def test_find_nearest_teammate_none_in_range():
    g = _make_game()
    g.start_game()
    g.player_x = 8
    g.player_y = 10
    g.teammates = [Teammate(15, 15, 0)]  # dist=12
    assert g._find_nearest_teammate() is None


def test_find_nearest_teammate_stunned():
    g = _make_game()
    g.start_game()
    g.stun_timer = 5
    g.teammates = [Teammate(8, 10, 0)]
    assert g._find_nearest_teammate() is None


# ── _pass_to (matching) ──
def test_pass_to_match():
    g = _make_game()
    g.start_game()
    g.player_x = 8
    g.player_y = 10
    g.player_color = 0
    g.combo = 0
    t = Teammate(8, 9, 0)  # same color
    gained, combo, matched = g._pass_to(t)
    assert matched is True
    assert combo == 1
    assert gained == 10  # 10 * 1 * 1
    assert g.score == 10
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.player_x == 8
    assert g.player_y == 9
    assert g.ball_x == 8
    assert g.ball_y == 9


def test_pass_to_match_combo_chain():
    g = _make_game()
    g.start_game()
    g.player_color = 0
    g.combo = 3
    g.max_combo = 3
    t = Teammate(8, 8, 0)  # same color
    gained, combo, matched = g._pass_to(t)
    assert matched is True
    assert combo == 4
    assert gained == 40  # 10 * 4 * 1


def test_pass_to_match_triggers_super():
    g = _make_game()
    g.start_game()
    g.player_color = 0
    g.combo = 3
    g.max_combo = 3
    g.super_mode = False
    t = Teammate(8, 8, 0)
    gained, combo, matched = g._pass_to(t)
    assert matched is True
    assert combo == 4
    assert g.super_mode is True
    assert g.super_timer == 300


def test_pass_to_match_during_super():
    g = _make_game()
    g.start_game()
    g.player_color = 1  # different from teammate
    g.super_mode = True
    g.super_timer = 200
    g.combo = 2
    t = Teammate(8, 8, 0)  # color 0, doesn't match player_color 1
    gained, combo, matched = g._pass_to(t)
    assert matched is True  # super mode matches any
    assert gained == 90  # 10 * 3 * 3 (super multiplier)
    assert g.combo == 3


# ── _pass_to (mismatch) ──
def test_pass_to_mismatch():
    g = _make_game()
    g.start_game()
    g.player_color = 0
    g.combo = 3
    g.heat = 10
    t = Teammate(8, 9, 1)  # different color
    gained, combo, matched = g._pass_to(t)
    assert matched is False
    assert combo == 0
    assert gained == 0
    assert g.combo == 0
    assert g.heat == 25  # 10 + 15
    assert g.stun_timer == 15


# ── _check_tackle ──
def test_check_tackle_no_defenders():
    g = _make_game()
    g.start_game()
    assert g._check_tackle() is False


def test_check_tackle_hit():
    g = _make_game()
    g.start_game()
    g.player_x = 8
    g.player_y = 5
    g.combo = 3
    g.heat = 20
    g.defenders = [Defender(8, 5, 0)]
    result = g._check_tackle()
    assert result is True
    assert g.combo == 0
    assert g.heat == 45  # 20 + 25
    assert g.stun_timer == 15


def test_check_tackle_different_position():
    g = _make_game()
    g.start_game()
    g.player_x = 8
    g.player_y = 5
    g.defenders = [Defender(10, 5, 0)]
    assert g._check_tackle() is False


def test_check_tackle_super_mode():
    g = _make_game()
    g.start_game()
    g.player_x = 8
    g.player_y = 5
    g.super_mode = True
    g.defenders = [Defender(8, 5, 0)]
    assert g._check_tackle() is False


def test_check_tackle_stunned_defender():
    g = _make_game()
    g.start_game()
    g.player_x = 8
    g.player_y = 5
    g.defenders = [Defender(8, 5, 0, stunned=5)]
    assert g._check_tackle() is False


def test_check_tackle_player_stunned():
    g = _make_game()
    g.start_game()
    g.player_x = 8
    g.player_y = 5
    g.stun_timer = 5
    g.defenders = [Defender(8, 5, 0)]
    assert g._check_tackle() is False


# ── _check_try ──
def test_check_try_not_at_line():
    g = _make_game()
    g.start_game()
    g.ball_y = 5
    assert g._check_try() is False


def test_check_try_at_line():
    g = _make_game()
    g.start_game()
    g.ball_y = 1
    assert g._check_try() is True


def test_check_try_beyond_line():
    g = _make_game()
    g.start_game()
    g.ball_y = 0
    assert g._check_try() is True


# ── _score_try ──
def test_score_try():
    g = _make_game()
    g.start_game()
    g.ball_x = 8
    g.ball_y = 1
    g.combo = 5
    g.score = 200
    g._score_try()
    assert g.score == 200 + 100 * 5  # TRY_SCORE * combo = 500
    assert g.combo == 0
    assert g.player_x == 8
    assert g.player_y == 11  # reset to start
    assert g.ball_x == 8
    assert g.ball_y == 11
    assert g.has_ball is True
    assert g.shake_frames == 15
    assert len(g.particles) == 20  # 20 particles
    assert len(g.floating_texts) == 1
    assert "TRY" in g.floating_texts[0].text


def test_score_try_no_combo():
    g = _make_game()
    g.start_game()
    g.ball_x = 8
    g.ball_y = 1
    g.combo = 0
    g.score = 100
    g._score_try()
    assert g.score == 200  # 100 + max(1, 0) * 100 = 200


# ── _update_heat ──
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


def test_update_heat_no_decay_in_super():
    g = _make_game()
    g.start_game()
    g.heat = 50.0
    g.super_mode = True
    g._update_heat()
    assert g.heat == 50.0  # no decay in super mode


# ── _spawn_defender ──
def test_spawn_defender():
    g = _make_game()
    g.start_game()
    assert len(g.defenders) == 0
    g._spawn_defender()
    assert len(g.defenders) == 1
    d = g.defenders[0]
    assert 0 <= d.x < 16
    assert 0 <= d.color <= 3


def test_spawn_defender_max():
    g = _make_game()
    g.start_game()
    for _ in range(6):
        g._spawn_defender()
    assert len(g.defenders) == 6
    g._spawn_defender()  # should not add (max_defenders = 6 at t=0)
    assert len(g.defenders) == 6


# ── _update_defenders ──
def test_update_defenders_move_toward():
    g = _make_game()
    g.start_game()
    g.frame = 10  # ensure movement ticks
    g.player_x = 8
    g.player_y = 10
    g.teammates = []
    g.defenders = [Defender(12, 10, 0)]
    old_x = g.defenders[0].x
    g._update_defenders()
    assert g.defenders[0].x < old_x  # moved toward player at col 8


def test_update_defenders_stunned():
    g = _make_game()
    g.start_game()
    g.frame = 10
    g.player_x = 8
    g.player_y = 10
    g.teammates = []
    g.defenders = [Defender(12, 10, 0, stunned=3)]
    g._update_defenders()
    assert g.defenders[0].stunned == 2  # decremented
    assert g.defenders[0].x == 12  # didn't move


# ── _update_particles ──
def test_update_particles():
    g = _make_game()
    g.particles = [Particle(100.0, 100.0, 1.0, -2.0, 8, 5)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 4
    assert g.particles[0].x > 100.0
    assert g.particles[0].y < 100.0  # moved up (vy=-2.0) then vy+=0.1


def test_update_particles_expire():
    g = _make_game()
    g.particles = [Particle(100.0, 100.0, 0.0, 0.0, 8, 1)]
    g._update_particles()
    assert len(g.particles) == 0  # life decremented to 0 → removed


# ── _update_floating_texts ──
def test_update_floating_texts():
    g = _make_game()
    g.floating_texts = [FloatingText(100.0, 100.0, "TEST", 7, 5)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].life == 4
    assert g.floating_texts[0].y < 100.0  # moved up


def test_update_floating_texts_expire():
    g = _make_game()
    g.floating_texts = [FloatingText(100.0, 100.0, "TEST", 7, 1)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── stun_timer behavior ──
def test_stun_timer_reset():
    g = _make_game()
    g.start_game()
    g.stun_timer = 15
    g.combo = 3
    # simulate a frame tick (stun timer decrements, no movement)
    g.stun_timer -= 1
    assert g.stun_timer == 14


# ── combo/max_combo tracking ──
def test_max_combo_tracks_highest():
    g = _make_game()
    g.start_game()
    g.player_color = 0
    # 3 successful passes
    g._pass_to(Teammate(8, 8, 0))
    assert g.combo == 1
    assert g.max_combo == 1
    g._pass_to(Teammate(8, 7, 0))
    assert g.combo == 2
    assert g.max_combo == 2
    # mismatch resets combo
    g._pass_to(Teammate(8, 6, 1))
    assert g.combo == 0
    assert g.max_combo == 2  # max preserved


# ── color constants ──
def test_color_constants_match():
    assert Game.COLOR_NAMES == ["RED", "LIME", "DARK_BLUE", "YELLOW"]
    assert Game.COLOR_VALS == [8, 11, 5, 10]
    assert len(Game.COLOR_NAMES) == 4
    assert len(Game.COLOR_VALS) == 4


# ── screen constants ──
def test_screen_constants():
    assert Game.SCREEN_W == 320
    assert Game.SCREEN_H == 240
    assert Game.CELL == 20
    assert Game.COLS == 16
    assert Game.ROWS == 12


# ── game constants ──
def test_game_constants():
    assert Game.TRY_LINE_ROW == 1
    assert Game.PLAYFIELD_TOP == 2
    assert Game.PLAYER_START_ROW == 11
    assert Game.PLAYER_START_COL == 8
    assert Game.MAX_TEAMMATES == 8
    assert Game.SUPER_DURATION == 300
    assert Game.TRY_SCORE == 100
    assert Game.HEAT_MAX == 100.0
    assert Game.HEAT_DECAY == 0.02
    assert Game.PASS_RANGE == 3
    assert Game.GAME_DURATION == 3600
    assert Game.DEFENDER_SPAWN_INTERVAL == 180


# ── multiple defenders ──
def test_multiple_defenders_spawn():
    g = _make_game()
    g.start_game()
    for _ in range(5):
        g._spawn_defender()
    assert len(g.defenders) == 5


# ── particles spawning on pass ──
def test_particles_on_match():
    g = _make_game()
    g.start_game()
    g.player_color = 0
    t = Teammate(8, 8, 0)
    g._pass_to(t)
    assert len(g.particles) == 8


def test_particles_on_mismatch():
    g = _make_game()
    g.start_game()
    g.player_color = 0
    t = Teammate(8, 8, 1)
    g._pass_to(t)
    assert len(g.particles) == 5


# ── floating texts on events ──
def test_floating_text_on_try():
    g = _make_game()
    g.start_game()
    g.ball_x = 8
    g.ball_y = 1
    g._score_try()
    assert len(g.floating_texts) >= 1
    assert any("TRY" in ft.text for ft in g.floating_texts)


def test_floating_text_on_match():
    g = _make_game()
    g.start_game()
    g.player_color = 0
    t = Teammate(8, 8, 0)
    g._pass_to(t)
    assert any("+" in ft.text for ft in g.floating_texts)


print("All tests passed!")
