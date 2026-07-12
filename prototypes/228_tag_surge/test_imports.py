"""test_imports.py — Headless logic tests for TAG SURGE."""
import sys
import random
import unittest.mock as mock

mock_display = mock.MagicMock()
mock_display.return_value = None
sys.modules["pyxel"] = mock.MagicMock()
sys.modules["pyxel"].COLOR_BLACK = 0
sys.modules["pyxel"].COLOR_NAVY = 1
sys.modules["pyxel"].COLOR_PURPLE = 2
sys.modules["pyxel"].COLOR_GREEN = 3
sys.modules["pyxel"].COLOR_BROWN = 4
sys.modules["pyxel"].COLOR_DARK_BLUE = 5
sys.modules["pyxel"].COLOR_LIGHT_BLUE = 6
sys.modules["pyxel"].COLOR_WHITE = 7
sys.modules["pyxel"].COLOR_RED = 8
sys.modules["pyxel"].COLOR_ORANGE = 9
sys.modules["pyxel"].COLOR_YELLOW = 10
sys.modules["pyxel"].COLOR_LIME = 11
sys.modules["pyxel"].COLOR_CYAN = 12
sys.modules["pyxel"].COLOR_GRAY = 13
sys.modules["pyxel"].COLOR_PINK = 14
sys.modules["pyxel"].COLOR_PEACH = 15
sys.modules["pyxel"].MOUSE_BUTTON_LEFT = 0
sys.modules["pyxel"].MOUSE_BUTTON_RIGHT = 1
sys.modules["pyxel"].MOUSE_BUTTON_MIDDLE = 2
sys.modules["pyxel"].KEY_UP = 4
sys.modules["pyxel"].KEY_DOWN = 5
sys.modules["pyxel"].KEY_LEFT = 6
sys.modules["pyxel"].KEY_RIGHT = 7
sys.modules["pyxel"].KEY_SPACE = 8
sys.modules["pyxel"].KEY_RETURN = 9
sys.modules["pyxel"].KEY_A = 1
sys.modules["pyxel"].KEY_W = 3
sys.modules["pyxel"].KEY_S = 2
sys.modules["pyxel"].KEY_D = 3
sys.modules["pyxel"].KEY_R = 19
sys.modules["pyxel"].btnp = mock.MagicMock(return_value=False)
sys.modules["pyxel"].btn = mock.MagicMock(return_value=False)
sys.modules["pyxel"].frame_count = 0

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/228_tag_surge")

from main import (  # noqa: E402
    Game, Phase, Runner, Particle, FloatingText,
    SCREEN_W, SCREEN_H, PLAYER_RADIUS, TAG_RADIUS,
    RUNNER_BASE_SPEED, MAX_RUNNERS, INITIAL_RUNNERS, COLORS,
    GAME_TIME, SUPER_DURATION, STUN_DURATION,
    HEAT_MAX, HEAT_DECAY, HEAT_MISMATCH,
    COLOR_CYCLE_INTERVAL, SUPER_SCORE_MULT,
    WHITE, RED,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.player_x = SCREEN_W / 2
    g.player_y = SCREEN_H / 2
    g.color_idx = 0
    g.player_color = COLORS[0]
    g.color_timer = COLOR_CYCLE_INTERVAL
    g.stun_timer = 0
    g.super_timer = 0
    g.game_timer = GAME_TIME
    g.shake_frames = 0
    g.frame = 0
    g.runners = []
    g.particles = []
    g.floating_texts = []
    g.difficulty_level = 0
    g.max_runners_now = INITIAL_RUNNERS
    g.rng = random.Random(42)
    return g


# ---- Test reset ----

def test_reset_clears_all_state() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.score = 100
    g.combo = 5
    g.heat = 80
    g.game_timer = 100
    g.stun_timer = 10
    g.super_timer = 50
    g.shake_frames = 12
    g.difficulty_level = 3
    g.max_runners_now = 8
    g.runners = [Runner(50, 50, COLORS[0])]
    g.particles = [Particle(10, 10, 0, 0, 5, RED)]
    g.floating_texts = [FloatingText(10, 10, "test", 10, WHITE)]

    g.reset()

    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.player_x == SCREEN_W / 2
    assert g.player_y == SCREEN_H / 2
    assert g.color_idx == 0
    assert g.player_color == COLORS[0]
    assert g.color_timer == COLOR_CYCLE_INTERVAL
    assert g.stun_timer == 0
    assert g.super_timer == 0
    assert g.game_timer == GAME_TIME
    assert g.shake_frames == 0
    assert g.frame == 0
    assert g.runners == []
    assert g.particles == []
    assert g.floating_texts == []
    assert g.difficulty_level == 0
    assert g.max_runners_now == INITIAL_RUNNERS


# ---- Test reset_playing ----

def test_reset_playing_spawns_runners() -> None:
    g = _make_game()
    g.reset_playing()
    assert g.phase == Phase.PLAYING
    assert len(g.runners) == INITIAL_RUNNERS


# ---- Test runner spawning ----

def test_spawn_runner_valid_position() -> None:
    g = _make_game()
    g._spawn_runner()
    assert len(g.runners) == 1
    r = g.runners[0]
    assert 0 <= r.x <= SCREEN_W
    assert 0 <= r.y <= SCREEN_H
    assert r.color in COLORS
    assert r.speed == RUNNER_BASE_SPEED


def test_runner_not_on_player() -> None:
    g = _make_game()
    for _ in range(20):
        g.runners = []
        g._spawn_runner()
        r = g.runners[0]
        dist = ((r.x - g.player_x) ** 2 + (r.y - g.player_y) ** 2) ** 0.5
        assert dist >= 40


def test_spawn_runner_respects_max() -> None:
    g = _make_game()
    g.max_runners_now = 3
    for _ in range(5):
        g._spawn_runner()
    assert len(g.runners) == 3


# ---- Test color cycling ----

def test_color_cycle_advances() -> None:
    g = _make_game()
    idx_before = g.color_idx
    g.color_timer = 1
    g._cycle_color()
    assert g.color_idx == (idx_before + 1) % len(COLORS)
    assert g.player_color == COLORS[g.color_idx]


def test_color_cycle_interval_decreases_with_difficulty() -> None:
    g = _make_game()
    g.difficulty_level = 5
    g.color_timer = 1
    g._cycle_color()
    interval = COLOR_CYCLE_INTERVAL - 5 * 3
    interval = max(60, interval)
    assert g.color_timer == interval


# ---- Test runner AI (flee) ----

def test_runner_flees_from_player() -> None:
    g = _make_game()
    r = Runner(100, 120, COLORS[0], 0, 0, RUNNER_BASE_SPEED)
    g.runners = [r]
    g.player_x = 200
    g.player_y = 120
    init_x = r.x
    g._update_runners()
    assert r.x < init_x  # flees left, away from player at 200


def test_runner_clamped_to_screen() -> None:
    g = _make_game()
    r = Runner(SCREEN_W + 10, SCREEN_H + 10, COLORS[0], 0, 0, RUNNER_BASE_SPEED)
    g.runners = [r]
    g.player_x = 0
    g.player_y = 0
    g._update_runners()
    assert 0 <= r.x <= SCREEN_W
    assert 0 <= r.y <= SCREEN_H


# ---- Test tag handling ----

def test_same_color_tag_increases_combo() -> None:
    g = _make_game()
    g.player_color = COLORS[0]
    r = Runner(g.player_x, g.player_y, COLORS[0], 0, 0, 1.2)
    g.runners = [r]
    g._handle_tag(0)
    assert g.combo == 1
    assert g.score > 0
    assert len(g.runners) == 0


def test_wrong_color_tag_resets_combo_and_adds_heat() -> None:
    g = _make_game()
    g.combo = 3
    g.player_color = COLORS[0]
    r = Runner(g.player_x, g.player_y, COLORS[1], 0, 0, 1.2)
    g.runners = [r]
    g._handle_tag(0)
    assert g.combo == 0
    assert g.heat == HEAT_MISMATCH
    assert g.stun_timer == STUN_DURATION


def test_super_tag_always_matches() -> None:
    g = _make_game()
    g.super_timer = 100
    g.player_color = COLORS[0]
    r = Runner(g.player_x, g.player_y, COLORS[1], 0, 0, 1.2)
    g.runners = [r]
    g._handle_tag(0)
    assert g.combo == 1
    assert len(g.runners) == 0


def test_combo_4_triggers_super() -> None:
    g = _make_game()
    g.combo = 3
    g.player_color = COLORS[0]
    r = Runner(g.player_x, g.player_y, COLORS[0], 0, 0, 1.2)
    g.runners = [r]
    g._handle_tag(0)
    assert g.super_timer == SUPER_DURATION
    assert g.combo == 4


# ---- Test score calculation ----

def test_score_with_combo_multiplier() -> None:
    g = _make_game()
    g.combo = 0
    g.player_color = COLORS[0]
    r = Runner(g.player_x, g.player_y, COLORS[0], 0, 0, 1.2)
    g.runners = [r]
    g._handle_tag(0)
    multiplier = 1.0 + 1 * 0.5
    expected = int(10 * multiplier)
    assert g.score == expected


def test_score_with_super_multiplier() -> None:
    g = _make_game()
    g.super_timer = 100
    g.combo = 0
    g.player_color = COLORS[0]
    r = Runner(g.player_x, g.player_y, COLORS[1], 0, 0, 1.2)
    g.runners = [r]
    g._handle_tag(0)
    multiplier = 1.0 + 1 * 0.5
    expected = int(10 * multiplier * SUPER_SCORE_MULT)
    assert g.score == expected


def test_score_with_high_combo() -> None:
    g = _make_game()
    g.combo = 4
    g.player_color = COLORS[0]
    r = Runner(g.player_x, g.player_y, COLORS[0], 0, 0, 1.2)
    g.runners = [r]
    g._handle_tag(0)
    multiplier = 1.0 + 5 * 0.5
    expected = int(10 * multiplier)
    assert g.score == expected


# ---- Test SUPER expiry ----

def test_super_timer_decrements() -> None:
    g = _make_game()
    g.super_timer = 100
    g.combo = 5
    g._update_super()
    assert g.super_timer == 99
    assert g.combo == 5


def test_super_expiry_resets_combo() -> None:
    g = _make_game()
    g.super_timer = 1
    g.combo = 5
    g._update_super()
    assert g.super_timer == 0
    assert g.combo == 0


# ---- Test auto-tag ----

def test_auto_tag_nearby_runners() -> None:
    g = _make_game()
    g.combo = 5
    g.player_x = 160
    g.player_y = 120
    r1 = Runner(165, 120, COLORS[0], 0, 0, 1.2)
    r2 = Runner(130, 125, COLORS[1], 0, 0, 1.2)
    g.runners = [r1, r2]
    g._auto_tag_nearby()
    assert len(g.runners) == 0
    assert g.combo == 7
    assert g.score > 0


# ---- Test heat ----

def test_heat_decays_over_time() -> None:
    g = _make_game()
    g.heat = 20.0
    g._update_heat()
    assert g.heat == 20.0 - HEAT_DECAY


def test_heat_at_zero_stays_at_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_heat_at_max_triggers_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = HEAT_MAX
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_heat_cannot_exceed_max() -> None:
    g = _make_game()
    g.heat = HEAT_MAX + 10
    assert g.heat == HEAT_MAX + 10
    g._update_heat()
    assert g.heat <= HEAT_MAX


# ---- Test timer ----

def test_game_timer_decrements() -> None:
    g = _make_game()
    g.game_timer = 100
    g._update_playing()
    assert g.game_timer == 99


# ---- Test difficulty ----

def test_difficulty_level_increases() -> None:
    g = _make_game()
    assert g.difficulty_level == 0
    g.game_timer = GAME_TIME - 10 * 30  # 10 seconds elapsed
    g._update_difficulty()
    assert g.difficulty_level == 1


def test_difficulty_increases_max_runners() -> None:
    g = _make_game()
    g.game_timer = GAME_TIME - 10 * 30
    g._update_difficulty()
    assert g.max_runners_now == INITIAL_RUNNERS + 1


def test_difficulty_max_runners_capped() -> None:
    g = _make_game()
    g.game_timer = GAME_TIME - 60 * 30
    g._update_difficulty()
    assert g.max_runners_now <= MAX_RUNNERS


# ---- Test particles ----

def test_spawn_particles() -> None:
    g = _make_game()
    g._spawn_particles(100, 100, RED, 10)
    assert len(g.particles) == 10
    for p in g.particles:
        assert p.x == 100
        assert p.y == 100
        assert p.color == RED


def test_particles_update_and_expire() -> None:
    g = _make_game()
    g._spawn_particles(100, 100, RED, 5)
    for _ in range(50):
        g._update_particles()
    assert len(g.particles) == 0


# ---- Test floating texts ----

def test_floating_text_spawn_and_update() -> None:
    g = _make_game()
    g._add_floating_text(100, 100, "+10", WHITE)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.text == "+10"
    assert ft.color == WHITE
    assert ft.life == 30

    for _ in range(50):
        g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ---- Test player movement (logic only) ----

def test_player_clamped_to_screen() -> None:
    g = _make_game()
    g.player_x = -10
    g.player_y = 300
    g.stun_timer = 0
    g._update_playing()
    assert g.player_x >= PLAYER_RADIUS
    assert g.player_y <= SCREEN_H - PLAYER_RADIUS


def test_stunned_player_cannot_move() -> None:
    g = _make_game()
    g.stun_timer = 10
    orig_x = g.player_x
    orig_y = g.player_y
    g._update_playing()
    assert g.stun_timer == 9
    assert g.player_x == orig_x
    assert g.player_y == orig_y


# ---- Test collision detection ----

def test_tag_detection_distance() -> None:
    g = _make_game()
    g.player_x = 100
    g.player_y = 100
    r = Runner(100 + TAG_RADIUS - 1, 100, COLORS[0], 0, 0, 1.2)
    g.runners = [r]
    g._check_tags()
    assert len(g.runners) == 0


def test_no_tag_outside_distance() -> None:
    g = _make_game()
    g.player_x = 100
    g.player_y = 100
    g.combo = 0
    r = Runner(100 + TAG_RADIUS + 5, 100, COLORS[0], 0, 0, 1.2)
    g.runners = [r]
    g._check_tags()
    assert len(g.runners) == 1


# ---- Test max_combo tracking ----

def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    g.max_combo = 3
    g.combo = 4
    g.player_color = COLORS[0]
    r = Runner(g.player_x, g.player_y, COLORS[0], 0, 0, 1.2)
    g.runners = [r]
    g._handle_tag(0)
    assert g.max_combo == 5
    assert g.combo == 5


# ---- Run all tests ----
if __name__ == "__main__":
    import traceback

    tests = [
        ("test_reset_clears_all_state", test_reset_clears_all_state),
        ("test_reset_playing_spawns_runners", test_reset_playing_spawns_runners),
        ("test_spawn_runner_valid_position", test_spawn_runner_valid_position),
        ("test_runner_not_on_player", test_runner_not_on_player),
        ("test_spawn_runner_respects_max", test_spawn_runner_respects_max),
        ("test_color_cycle_advances", test_color_cycle_advances),
        ("test_color_cycle_interval_decreases_with_difficulty", test_color_cycle_interval_decreases_with_difficulty),
        ("test_runner_flees_from_player", test_runner_flees_from_player),
        ("test_runner_clamped_to_screen", test_runner_clamped_to_screen),
        ("test_same_color_tag_increases_combo", test_same_color_tag_increases_combo),
        ("test_wrong_color_tag_resets_combo_and_adds_heat", test_wrong_color_tag_resets_combo_and_adds_heat),
        ("test_super_tag_always_matches", test_super_tag_always_matches),
        ("test_combo_4_triggers_super", test_combo_4_triggers_super),
        ("test_score_with_combo_multiplier", test_score_with_combo_multiplier),
        ("test_score_with_super_multiplier", test_score_with_super_multiplier),
        ("test_score_with_high_combo", test_score_with_high_combo),
        ("test_super_timer_decrements", test_super_timer_decrements),
        ("test_super_expiry_resets_combo", test_super_expiry_resets_combo),
        ("test_auto_tag_nearby_runners", test_auto_tag_nearby_runners),
        ("test_heat_decays_over_time", test_heat_decays_over_time),
        ("test_heat_at_zero_stays_at_zero", test_heat_at_zero_stays_at_zero),
        ("test_heat_at_max_triggers_game_over", test_heat_at_max_triggers_game_over),
        ("test_heat_cannot_exceed_max", test_heat_cannot_exceed_max),
        ("test_difficulty_level_increases", test_difficulty_level_increases),
        ("test_difficulty_increases_max_runners", test_difficulty_increases_max_runners),
        ("test_difficulty_max_runners_capped", test_difficulty_max_runners_capped),
        ("test_spawn_particles", test_spawn_particles),
        ("test_particles_update_and_expire", test_particles_update_and_expire),
        ("test_floating_text_spawn_and_update", test_floating_text_spawn_and_update),
        ("test_player_clamped_to_screen", test_player_clamped_to_screen),
        ("test_stunned_player_cannot_move", test_stunned_player_cannot_move),
        ("test_tag_detection_distance", test_tag_detection_distance),
        ("test_no_tag_outside_distance", test_no_tag_outside_distance),
        ("test_max_combo_tracks_highest", test_max_combo_tracks_highest),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS {name}")
            passed += 1
        except Exception:
            print(f"  FAIL {name}")
            traceback.print_exc()
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
