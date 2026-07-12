"""test_imports.py — Headless logic tests for HIDE SURGE."""
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

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/229_hide_surge")

from main import (  # noqa: E402
    Game, Phase, HidingSpot, Seeker, Particle, FloatingText,
    SCREEN_W, SCREEN_H, CELL, COLS, ROWS, OFFSET_X, OFFSET_Y,
    GAME_TIME, SUPER_DURATION, HEAT_MAX, HEAT_DECAY, HEAT_MISMATCH, HEAT_CAUGHT,
    COMBO_SUPER_THRESHOLD, SPOT_COLORS, SEEKER_SPEED_INITIAL,
    SEEKER_AWARENESS_INITIAL, SPOT_RESPAWN_BASE,
    WHITE, RED, GREEN, DARK_BLUE, GRAY, YELLOW, LIME,
    MAX_SPOTS, MIN_SPOTS, SEEKER_COUNT,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.player_col = COLS // 2
    g.player_row = ROWS // 2
    g.player_color = GREEN
    g.is_hidden = False
    g.current_spot_color = None
    g.spots = []
    g.seekers = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.super_mode = False
    g.super_timer = 0
    g.heat = 0.0
    g.game_timer = GAME_TIME
    g.move_cooldown = 0
    g.particles = []
    g.floating_texts = []
    g.awareness_interval = SEEKER_AWARENESS_INITIAL
    g.speed_frames_current = SEEKER_SPEED_INITIAL
    g.respawn_interval = SPOT_RESPAWN_BASE
    g.frame = 0
    g.elapsed_seconds = 0
    g.rng = random.Random(42)
    return g


# ---- Test reset ----

def test_reset_clears_all_state() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.score = 100
    g.combo = 5
    g.heat = 80.0
    g.game_timer = 100
    g.is_hidden = True
    g.current_spot_color = RED
    g.super_mode = True
    g.super_timer = 50
    g.spots = [HidingSpot(0, 0, RED)]
    g.seekers = [Seeker(0, 0, set(), 1, 0, 30, 0, 0, RED)]
    g.particles = [Particle(10, 10, 0, 0, 5, RED)]
    g.floating_texts = [FloatingText(10, 10, "test", 10, WHITE)]

    g.reset()

    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.player_col == COLS // 2
    assert g.player_row == ROWS // 2
    assert g.is_hidden is False
    assert g.current_spot_color is None
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.game_timer == GAME_TIME
    assert g.spots == []
    assert g.seekers == []
    assert g.particles == []
    assert g.floating_texts == []


# ---- Test reset_playing ----

def test_reset_playing_spawns_spots_and_seekers() -> None:
    g = _make_game()
    g.reset_playing()
    assert g.phase == Phase.PLAYING
    assert len(g.spots) > 0
    assert len(g.seekers) == SEEKER_COUNT


# ---- Test spot spawning ----

def test_spawn_spots_populates_grid() -> None:
    g = _make_game()
    g._spawn_spots()
    assert len(g.spots) > 0
    positions = {(s.col, s.row) for s in g.spots}
    assert len(positions) == len(g.spots)
    for s in g.spots:
        assert 0 <= s.col < COLS
        assert 0 <= s.row < ROWS


def test_respawn_spot_respects_max() -> None:
    g = _make_game()
    for _ in range(MAX_SPOTS + 5):
        g._respawn_spot()
    assert len(g.spots) <= MAX_SPOTS


def test_respawn_spot_avoids_occupied() -> None:
    g = _make_game()
    g.spots = [HidingSpot(c, 0, RED) for c in range(COLS)]
    g.player_col = 0
    g.player_row = 1
    g._respawn_spot()
    assert len(g.spots) <= MAX_SPOTS


# ---- Test hide mechanic ----

def test_try_hide_first_time() -> None:
    g = _make_game()
    gained = g._try_hide(SPOT_COLORS[0])
    assert gained == 10
    assert g.combo == 1
    assert g.is_hidden is True
    assert g.current_spot_color == SPOT_COLORS[0]
    assert g.score == 10


def test_try_hide_same_color_continues_combo() -> None:
    g = _make_game()
    g.current_spot_color = SPOT_COLORS[0]
    g.combo = 2
    g.score = 30
    g._try_hide(SPOT_COLORS[0])
    g.is_hidden = False
    g._try_hide(SPOT_COLORS[0])
    assert g.combo == 4
    assert g.score == 30 + 30 + 40


def test_try_hide_wrong_color_resets_combo() -> None:
    g = _make_game()
    g.current_spot_color = SPOT_COLORS[0]
    g.combo = 3
    g.score = 60
    gained = g._try_hide(SPOT_COLORS[1])
    assert gained == 0
    assert g.combo == 0
    assert g.heat == HEAT_MISMATCH


def test_try_hide_when_already_hidden() -> None:
    g = _make_game()
    g.is_hidden = True
    g.current_spot_color = SPOT_COLORS[0]
    g.combo = 3
    gained = g._try_hide(SPOT_COLORS[0])
    assert gained == 0
    assert g.is_hidden is False
    assert g.current_spot_color is None
    assert g.combo == 3


def test_try_hide_super_mode_3x_multiplier() -> None:
    g = _make_game()
    g.super_mode = True
    g.combo = 2
    gained = g._try_hide(SPOT_COLORS[0])
    assert gained == 10 * 3 * 3
    assert g.combo == 3


def test_combo_4_triggers_super() -> None:
    g = _make_game()
    g.combo = 3
    g.score = 60
    g.super_mode = False
    g.super_timer = 0
    g._try_hide(SPOT_COLORS[0])
    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


# ---- Test SUPER mode ----

def test_super_mode_updates() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g._update_super_mode()
    assert g.super_timer == 99
    assert g.super_mode is True


def test_super_mode_expires_resets_combo() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g.combo = 5
    g._update_super_mode()
    assert g.super_timer == 0
    assert g.super_mode is False
    assert g.combo == 0


# ---- Test seekers ----

def test_seekers_spawned_correct_count() -> None:
    g = _make_game()
    g._spawn_seekers()
    assert len(g.seekers) == SEEKER_COUNT
    for s in g.seekers:
        assert 0 <= s.col < COLS
        assert 0 <= s.row < ROWS


def test_seeker_movement_clamped() -> None:
    g = _make_game()
    seeker = Seeker(0, 0, set(), -1, 0, 1, 1, 0, RED)
    g.seekers = [seeker]
    g.rng = random.Random(42)
    for _ in range(20):
        g._move_seeker(seeker)
        assert 0 <= seeker.col < COLS
        assert 0 <= seeker.row < ROWS


def test_awareness_expands() -> None:
    g = _make_game()
    g.rng = random.Random(42)
    seeker = Seeker(5, 4, set(), 1, 0, 30, 0, 0, RED)
    g._expand_awareness(seeker)
    assert len(seeker.awareness) > 0
    assert (5, 4) in seeker.awareness


# ---- Test caught check ----

def test_not_caught_when_hidden() -> None:
    g = _make_game()
    g.is_hidden = True
    g.player_col = 5
    g.player_row = 4
    seeker = Seeker(5, 4, set(), 1, 0, 30, 0, 0, RED)
    g.seekers = [seeker]
    result = g._check_caught()
    assert result is False


def test_caught_when_exposed_and_same_cell() -> None:
    g = _make_game()
    g.is_hidden = False
    g.phase = Phase.PLAYING
    g.player_col = 5
    g.player_row = 4
    seeker = Seeker(5, 4, set(), 1, 0, 30, 0, 0, RED)
    g.seekers = [seeker]
    result = g._check_caught()
    assert result is True
    assert g.heat == HEAT_CAUGHT
    assert g.combo == 0


def test_not_caught_in_super_mode() -> None:
    g = _make_game()
    g.super_mode = True
    g.player_col = 5
    g.player_row = 4
    seeker = Seeker(5, 4, set(), 1, 0, 30, 0, 0, RED)
    g.seekers = [seeker]
    result = g._check_caught()
    assert result is False


# ---- Test heat ----

def test_update_heat_adds_and_clamps() -> None:
    g = _make_game()
    g._update_heat(30.0)
    assert g.heat == 30.0
    g._update_heat(80.0)
    assert g.heat == HEAT_MAX


def test_heat_at_max_triggers_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._update_heat(HEAT_MAX)
    assert g.phase == Phase.GAME_OVER


def test_heat_decays_naturally() -> None:
    g = _make_game()
    g.heat = 20.0
    g._update_playing()
    assert g.heat == 20.0 - HEAT_DECAY


def test_heat_cannot_go_negative() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_playing()
    assert g.heat == 0.0


# ---- Test difficulty ----

def test_difficulty_increases_seeker_speed() -> None:
    g = _make_game()
    g.game_timer = GAME_TIME - 12 * 60
    g._update_difficulty()
    assert g.speed_frames_current == SEEKER_SPEED_INITIAL - 1


def test_difficulty_min_seeker_speed() -> None:
    g = _make_game()
    g.game_timer = 1
    g._update_difficulty()
    assert g.speed_frames_current >= 8


def test_difficulty_increases_awareness_speed() -> None:
    g = _make_game()
    g.game_timer = GAME_TIME - 60 * 60
    g._update_difficulty()
    assert g.awareness_interval <= SEEKER_AWARENESS_INITIAL


# ---- Test particles ----

def test_spawn_particles() -> None:
    g = _make_game()
    g._spawn_particles(100, 100, RED, 10)
    assert len(g.particles) == 10
    for p in g.particles:
        assert p.x == 100
        assert p.y == 100
        assert p.color == RED
        assert p.life > 0


def test_particles_update_and_expire() -> None:
    g = _make_game()
    g._spawn_particles(100, 100, RED, 5)
    for _ in range(50):
        g._update_particles()
    assert len(g.particles) == 0


# ---- Test floating texts ----

def test_floating_text() -> None:
    g = _make_game()
    g._add_floating_text(100, 100, "+10", WHITE)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.text == "+10"
    assert ft.color == WHITE
    assert ft.life == 30


def test_floating_text_expires() -> None:
    g = _make_game()
    g._add_floating_text(100, 100, "test", WHITE)
    for _ in range(50):
        g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ---- Test spots respawn ----

def test_spots_respawn_ensures_min() -> None:
    g = _make_game()
    g.spots = [HidingSpot(0, 0, RED, respawn_timer=1) for _ in range(2)]
    g._update_spots()
    assert len(g.spots) >= MIN_SPOTS


def test_spot_respawn_timer_decrements() -> None:
    g = _make_game()
    g.rng = random.Random(42)
    g.spots = [HidingSpot(0, 0, RED, respawn_timer=5)]
    g._update_spots()
    assert g.spots[0].respawn_timer == 4


# ---- Test max_combo tracking ----

def test_max_combo_records_highest() -> None:
    g = _make_game()
    g.max_combo = 3
    g.combo = 3
    g.current_spot_color = SPOT_COLORS[0]
    g._try_hide(SPOT_COLORS[0])
    assert g.max_combo == 4
    assert g.combo == 4


# ---- Test game timer ----

def test_game_timer_decrements() -> None:
    g = _make_game()
    g.game_timer = 100
    g.phase = Phase.PLAYING
    g._update_playing()
    assert g.game_timer == 99


def test_game_over_on_timer_zero() -> None:
    g = _make_game()
    g.game_timer = 1
    g.phase = Phase.PLAYING
    g._update_playing()
    assert g.phase == Phase.GAME_OVER


# ---- Run all tests ----
if __name__ == "__main__":
    import traceback

    tests = [
        ("test_reset_clears_all_state", test_reset_clears_all_state),
        ("test_reset_playing_spawns_spots_and_seekers", test_reset_playing_spawns_spots_and_seekers),
        ("test_spawn_spots_populates_grid", test_spawn_spots_populates_grid),
        ("test_respawn_spot_respects_max", test_respawn_spot_respects_max),
        ("test_respawn_spot_avoids_occupied", test_respawn_spot_avoids_occupied),
        ("test_try_hide_first_time", test_try_hide_first_time),
        ("test_try_hide_same_color_continues_combo", test_try_hide_same_color_continues_combo),
        ("test_try_hide_wrong_color_resets_combo", test_try_hide_wrong_color_resets_combo),
        ("test_try_hide_when_already_hidden", test_try_hide_when_already_hidden),
        ("test_try_hide_super_mode_3x_multiplier", test_try_hide_super_mode_3x_multiplier),
        ("test_combo_4_triggers_super", test_combo_4_triggers_super),
        ("test_super_mode_updates", test_super_mode_updates),
        ("test_super_mode_expires_resets_combo", test_super_mode_expires_resets_combo),
        ("test_seekers_spawned_correct_count", test_seekers_spawned_correct_count),
        ("test_seeker_movement_clamped", test_seeker_movement_clamped),
        ("test_awareness_expands", test_awareness_expands),
        ("test_not_caught_when_hidden", test_not_caught_when_hidden),
        ("test_caught_when_exposed_and_same_cell", test_caught_when_exposed_and_same_cell),
        ("test_not_caught_in_super_mode", test_not_caught_in_super_mode),
        ("test_update_heat_adds_and_clamps", test_update_heat_adds_and_clamps),
        ("test_heat_at_max_triggers_game_over", test_heat_at_max_triggers_game_over),
        ("test_heat_decays_naturally", test_heat_decays_naturally),
        ("test_heat_cannot_go_negative", test_heat_cannot_go_negative),
        ("test_difficulty_increases_seeker_speed", test_difficulty_increases_seeker_speed),
        ("test_difficulty_min_seeker_speed", test_difficulty_min_seeker_speed),
        ("test_difficulty_increases_awareness_speed", test_difficulty_increases_awareness_speed),
        ("test_spawn_particles", test_spawn_particles),
        ("test_particles_update_and_expire", test_particles_update_and_expire),
        ("test_floating_text", test_floating_text),
        ("test_floating_text_expires", test_floating_text_expires),
        ("test_spots_respawn_ensures_min", test_spots_respawn_ensures_min),
        ("test_spot_respawn_timer_decrements", test_spot_respawn_timer_decrements),
        ("test_max_combo_records_highest", test_max_combo_records_highest),
        ("test_game_timer_decrements", test_game_timer_decrements),
        ("test_game_over_on_timer_zero", test_game_over_on_timer_zero),
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
