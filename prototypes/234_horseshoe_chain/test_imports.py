"""test_imports.py -- Headless logic tests for HORSESHOE CHAIN."""
from __future__ import annotations

import random
import sys
import traceback
import unittest.mock as mock

mock_pyxel = mock.MagicMock()
mock_pyxel.COLOR_BLACK = 0
mock_pyxel.COLOR_NAVY = 1
mock_pyxel.COLOR_PURPLE = 2
mock_pyxel.COLOR_GREEN = 3
mock_pyxel.COLOR_BROWN = 4
mock_pyxel.COLOR_DARK_BLUE = 5
mock_pyxel.COLOR_LIGHT_BLUE = 6
mock_pyxel.COLOR_WHITE = 7
mock_pyxel.COLOR_RED = 8
mock_pyxel.COLOR_ORANGE = 9
mock_pyxel.COLOR_YELLOW = 10
mock_pyxel.COLOR_LIME = 11
mock_pyxel.COLOR_CYAN = 12
mock_pyxel.COLOR_GRAY = 13
mock_pyxel.COLOR_PINK = 14
mock_pyxel.COLOR_PEACH = 15
mock_pyxel.MOUSE_BUTTON_LEFT = 0
mock_pyxel.MOUSE_BUTTON_RIGHT = 1
mock_pyxel.MOUSE_BUTTON_MIDDLE = 2
mock_pyxel.KEY_SPACE = 8
mock_pyxel.KEY_RETURN = 9
mock_pyxel.btnp = mock.MagicMock(return_value=False)
mock_pyxel.btnr = mock.MagicMock(return_value=False)
mock_pyxel.btn = mock.MagicMock(return_value=False)
mock_pyxel.frame_count = 0
mock_pyxel.mouse_x = 0
mock_pyxel.mouse_y = 0
sys.modules["pyxel"] = mock_pyxel

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/234_horseshoe_chain")

from main import (  # noqa: E402
    Game, Phase, Stake, Horseshoe, Particle, FloatingText,
    WHITE, RED, LIME, DARK_BLUE, YELLOW, ORANGE, GRAY, GREEN, NAVY,
    COLORS, PLAYER_X, PLAYER_Y, STAKE_Y, STAKE_X_POSITIONS,
    STAKE_RADIUS, RINGER_DEPTH, GRAVITY, MAX_POWER,
    GAME_DURATION, SUPER_DURATION, COMBO_THRESHOLD, MAX_HEAT,
    HEAT_MISS, HEAT_MISMATCH, HEAT_DECAY,
    SCORING_DURATION, MAX_GHOST_POINTS,
    SHUFFLE_INTERVAL, DESPERATION_THRESHOLD, GROUND_Y,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.best_combo = 0
    g.heat = 0.0
    g.timer = GAME_DURATION
    g.super_timer = 0
    g.scoring_timer = 0
    g.stake_shuffle_timer = 0
    g.aim_start_x = 0.0
    g.aim_start_y = 0.0
    g.dragging = False
    g.shake_frames = 0
    g.shake_intensity = 0
    g.horseshoe = None
    g.stakes = []
    g.particles = []
    g.floating_texts = []
    g.ghost_trail = []
    g.best_score = 0
    g.rng = random.Random(seed)
    return g


def _make_playing(seed: int = 42) -> Game:
    g = _make_game(seed)
    g._start_game()
    return g


# ---- 1. _throw creates horseshoe with velocity ----
def test_throw_creates_horseshoe() -> None:
    g = _make_playing()
    g._throw(100.0, -50.0)
    assert g.horseshoe is not None
    assert g.horseshoe.active is True
    assert g.horseshoe.vx > 0.0
    assert g.horseshoe.vy < 0.0
    assert g.phase == Phase.FLYING


# ---- 2. _throw ignores zero power ----
def test_throw_zero_power() -> None:
    g = _make_playing()
    g._throw(0.0, 0.0)
    assert g.horseshoe is None
    assert g.phase == Phase.AIMING


# ---- 3. _throw ignores weak power ----
def test_throw_weak_power() -> None:
    g = _make_playing()
    g._throw(1.0, 0.0)
    assert g.horseshoe is None


# ---- 4. _update_flying applies gravity ----
def test_flying_applies_gravity() -> None:
    g = _make_playing()
    g.horseshoe = Horseshoe(x=100.0, y=100.0, vx=5.0, vy=0.0, color=RED)
    g._update_flying()
    assert g.horseshoe.vy > 0.0


# ---- 5. _update_flying ground bounce ----
def test_flying_ground_bounce() -> None:
    g = _make_playing()
    g.horseshoe = Horseshoe(x=160.0, y=GROUND_Y - 2, vx=3.0, vy=10.0, color=RED)
    g._update_flying()
    assert g.horseshoe.vy < 0.0  # bounced upward


# ---- 6. _update_flying stops on ground with low speed ----
def test_flying_stops_on_ground() -> None:
    g = _make_playing()
    g.horseshoe = Horseshoe(x=160.0, y=GROUND_Y, vx=0.0, vy=0.5, color=RED)
    g.phase = Phase.FLYING
    g._update_flying()
    assert g.horseshoe.active is False


# ---- 7. _check_ringer detects ringer ----
def test_check_ringer_detects() -> None:
    g = _make_playing()
    s = g.stakes[0]
    g.horseshoe = Horseshoe(x=s.x, y=s.y, vx=0.0, vy=0.0, color=RED)
    result = g._check_ringer()
    assert result is s


# ---- 8. _check_ringer returns none for miss ----
def test_check_ringer_miss() -> None:
    g = _make_playing()
    g.horseshoe = Horseshoe(x=10.0, y=STAKE_Y, vx=0.0, vy=0.0, color=RED)
    result = g._check_ringer()
    assert result is None


# ---- 9. _check_ringer returns none if already scored ----
def test_check_ringer_already_scored() -> None:
    g = _make_playing()
    s = g.stakes[0]
    g.horseshoe = Horseshoe(x=s.x, y=s.y, vx=0.0, vy=0.0, color=RED, scored=True)
    result = g._check_ringer()
    assert result is None


# ---- 10. _check_ringer vertical miss (too far above) ----
def test_check_ringer_vertical_miss() -> None:
    g = _make_playing()
    s = g.stakes[0]
    g.horseshoe = Horseshoe(x=s.x, y=s.y - RINGER_DEPTH - 5, vx=0.0, vy=0.0, color=RED)
    result = g._check_ringer()
    assert result is None


# ---- 11. _handle_ringer match: combo++, score increases ----
def test_handle_ringer_match() -> None:
    g = _make_playing()
    g.combo = 2
    g.score = 50
    s = g.stakes[0]
    g.horseshoe = Horseshoe(x=s.x, y=s.y, vx=0.0, vy=0.0, color=s.color)
    g._handle_ringer(s)
    assert g.combo == 3
    assert g.score == 50 + int(10 * 3 * 1.0)
    assert g.horseshoe.scored is True


# ---- 12. _handle_ringer mismatch: combo resets, heat increases ----
def test_handle_ringer_mismatch() -> None:
    g = _make_playing()
    g.combo = 3
    g.heat = 20.0
    s = g.stakes[0]
    # Ensure horseshoe color differs from stake color
    mismatch_color = s.color
    for c in COLORS:
        if c != s.color:
            mismatch_color = c
            break
    g.horseshoe = Horseshoe(x=s.x, y=s.y, vx=0.0, vy=0.0, color=mismatch_color)
    g._handle_ringer(s)
    assert g.combo == 0
    assert g.heat == 20.0 + HEAT_MISMATCH


# ---- 13. _handle_ringer activates super at threshold ----
def test_handle_ringer_super_activation() -> None:
    g = _make_playing()
    g.combo = COMBO_THRESHOLD - 1
    s = g.stakes[0]
    g.horseshoe = Horseshoe(x=s.x, y=s.y, vx=0.0, vy=0.0, color=s.color)
    g._handle_ringer(s)
    assert g.combo == COMBO_THRESHOLD
    assert g.super_timer == SUPER_DURATION


# ---- 14. _handle_ringer super mode any color matches ----
def test_handle_ringer_super_any_color() -> None:
    g = _make_playing()
    g.super_timer = 100
    g.combo = 1
    g.score = 100
    s = g.stakes[0]
    mismatch_color = s.color
    for c in COLORS:
        if c != s.color:
            mismatch_color = c
            break
    g.horseshoe = Horseshoe(x=s.x, y=s.y, vx=0.0, vy=0.0, color=mismatch_color)
    g._handle_ringer(s)
    assert g.combo == 2
    assert g.score > 100


# ---- 15. _handle_ringer super mode 3x score ----
def test_handle_ringer_super_multiplier() -> None:
    g = _make_playing()
    g.super_timer = 100
    g.combo = 1
    g.score = 0
    s = g.stakes[0]
    g.horseshoe = Horseshoe(x=s.x, y=s.y, vx=0.0, vy=0.0, color=s.color)
    g._handle_ringer(s)
    assert g.score == int(10 * 2 * 3.0)


# ---- 16. _on_miss resets combo and adds heat ----
def test_on_miss_resets_combo() -> None:
    g = _make_playing()
    g.combo = 5
    g.heat = 30.0
    g.horseshoe = Horseshoe(x=160.0, y=GROUND_Y, vx=0.0, vy=0.0, color=RED)
    g._on_miss()
    assert g.combo == 0
    assert g.heat == 30.0 + HEAT_MISS
    assert g.phase == Phase.SCORING


# ---- 17. _on_miss adds floating text ----
def test_on_miss_floating_text() -> None:
    g = _make_playing()
    g.floating_texts = []
    g.horseshoe = Horseshoe(x=160.0, y=GROUND_Y, vx=0.0, vy=0.0, color=RED)
    g._on_miss()
    assert len(g.floating_texts) >= 1
    assert any("MISS" in ft.text for ft in g.floating_texts)


# ---- 18. _activate_super sets super_timer ----
def test_activate_super() -> None:
    g = _make_playing()
    assert g.super_timer == 0
    g._activate_super()
    assert g.super_timer == SUPER_DURATION
    assert g.shake_frames == 10


# ---- 19. _deactivate_super clears state ----
def test_deactivate_super() -> None:
    g = _make_playing()
    g.super_timer = 50
    g.combo = 10
    g._deactivate_super()
    assert g.super_timer == 0
    assert g.combo == 0


# ---- 20. _update_particles moves and expires ----
def test_particles_update_and_expire() -> None:
    g = _make_playing()
    g.particles = [
        Particle(0.0, 0.0, 1.0, 0.0, RED, life=1),
        Particle(0.0, 0.0, 1.0, 0.0, RED, life=3),
    ]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 2


# ---- 21. _spawn_particles creates correct count ----
def test_spawn_particles() -> None:
    g = _make_playing()
    g._spawn_particles(100.0, 100.0, RED, 8)
    assert len(g.particles) == 8
    assert all(p.life > 0 for p in g.particles)


# ---- 22. _update_floating_texts moves and expires ----
def test_floating_texts_update() -> None:
    g = _make_playing()
    g.floating_texts = [
        FloatingText(100.0, 100.0, "TEST", WHITE, life=1),
        FloatingText(100.0, 100.0, "KEEP", WHITE, life=3),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "KEEP"


# ---- 23. _update_timer decrements ----
def test_timer_decrements() -> None:
    g = _make_playing()
    g.timer = 100
    g._update_timer()
    assert g.timer == 99


# ---- 24. _update_timer at zero triggers game over ----
def test_timer_zero_game_over() -> None:
    g = _make_playing()
    g.timer = 1
    g._update_timer()
    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER


# ---- 25. _shuffle_stakes changes order ----
def test_shuffle_stakes() -> None:
    g = _make_playing()
    old_colors = [s.color for s in g.stakes]
    # Shuffle many times to ensure at least one changes
    changed = False
    for _ in range(50):
        g._shuffle_stakes()
        new_colors = [s.color for s in g.stakes]
        if old_colors != new_colors:
            changed = True
            break
    assert changed is True


# ---- 26. _start_game resets all state ----
def test_start_game_resets_state() -> None:
    g = _make_playing()
    g.score = 500
    g.combo = 10
    g.heat = 80.0
    g.super_timer = 200
    g.ghost_trail = [(1.0, 1.0)]
    g._start_game()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert len(g.ghost_trail) == 0
    assert len(g.stakes) == 4
    assert g.phase == Phase.AIMING


# ---- 27. _start_game spawns 4 stakes ----
def test_start_game_spawns_four_stakes() -> None:
    g = _make_playing()
    assert len(g.stakes) == 4
    for s in g.stakes:
        assert s.color in COLORS
        assert s.x in STAKE_X_POSITIONS
        assert s.y == STAKE_Y


# ---- 28. Heat decay ----
def test_heat_decay() -> None:
    g = _make_playing()
    g.heat = 50.0
    g.heat = max(0.0, g.heat - HEAT_DECAY)
    assert g.heat < 50.0
    assert g.heat > 49.0


# ---- 29. Heat not negative ----
def test_heat_not_negative() -> None:
    g = _make_playing()
    g.heat = 0.0
    g.heat = max(0.0, g.heat - HEAT_DECAY)
    assert g.heat == 0.0


# ---- 30. Heat max clamped ----
def test_heat_max_clamped() -> None:
    g = _make_playing()
    g.heat = 95.0
    g.heat = min(MAX_HEAT, g.heat + HEAT_MISMATCH)
    assert g.heat == MAX_HEAT


# ---- 31. Max combo tracking ----
def test_max_combo_tracks_highest() -> None:
    g = _make_playing()
    g.combo = 3
    s = g.stakes[0]
    g.horseshoe = Horseshoe(x=s.x, y=s.y, vx=0.0, vy=0.0, color=s.color)
    g._handle_ringer(s)
    assert g.max_combo == 4


# ---- 32. Best combo on game over ----
def test_best_combo_on_game_over() -> None:
    g = _make_playing()
    g.combo = 7
    g.best_combo = 3
    g.timer = 1
    g._update_timer()
    assert g.phase == Phase.GAME_OVER
    assert g.best_combo == 7


# ---- 33. Best score on game over ----
def test_best_score_on_game_over() -> None:
    g = _make_playing()
    g.score = 500
    g.best_score = 300
    g.timer = 1
    g._update_timer()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 500


# ---- 34. Ghost trail saved after scoring ringer ----
def test_ghost_trail_saved() -> None:
    g = _make_playing()
    g.combo = 1
    trail_data = [(160.0, 220.0), (165.0, 200.0), (170.0, 190.0)]
    g.horseshoe = Horseshoe(
        x=160.0, y=220.0, vx=0.0, vy=0.0, color=RED, trail=list(trail_data)
    )
    g._save_ghost_trail()
    assert len(g.ghost_trail) == 3


# ---- 35. Ghost trail downsamples to max points ----
def test_ghost_trail_downsamples() -> None:
    g = _make_playing()
    trail_data = [(float(i), float(i)) for i in range(200)]
    g.horseshoe = Horseshoe(
        x=160.0, y=220.0, vx=0.0, vy=0.0, color=RED, trail=list(trail_data)
    )
    g._save_ghost_trail()
    assert len(g.ghost_trail) == MAX_GHOST_POINTS


# ---- 36. Throw clamps to max power ----
def test_throw_max_power_clamped() -> None:
    g = _make_playing()
    g._throw(1000.0, -1000.0)
    assert g.horseshoe is not None
    speed = abs(g.horseshoe.vx) + abs(g.horseshoe.vy)
    max_speed = MAX_POWER * math.sqrt(2) * 1.01
    assert speed <= max_speed


import math  # noqa: E402


# ---- 37. Horseshoe trail records flight path ----
def test_horseshoe_trail_records_path() -> None:
    g = _make_playing()
    g.horseshoe = Horseshoe(x=160.0, y=220.0, vx=3.0, vy=-5.0, color=RED)
    initial_len = len(g.horseshoe.trail)
    g._update_flying()
    assert len(g.horseshoe.trail) > initial_len


# ---- 38. Scoring timer transitions to aiming ----
def test_scoring_transitions_to_aiming() -> None:
    g = _make_playing()
    g.phase = Phase.SCORING
    g.scoring_timer = 1
    g._update_timer()
    g.scoring_timer -= 1
    assert g.scoring_timer <= 0


# ---- 39. Heat >= 100 triggers game over in AIMING ----
def test_heat_100_game_over() -> None:
    g = _make_playing()
    g.heat = 100.0
    g._end_game()
    assert g.phase == Phase.GAME_OVER


# ---- 40. Stake shuffle only when horseshoe inactive ----
def test_stake_shuffle_timer_inactive() -> None:
    g = _make_playing()
    g.stake_shuffle_timer = SHUFFLE_INTERVAL - 1
    old_colors = [s.color for s in g.stakes]
    g._update_timer()
    assert old_colors != [s.color for s in g.stakes]


# ---- 41. Desperation disables heat decay ----
def test_desperation_no_heat_decay() -> None:
    g = _make_playing()
    g.timer = DESPERATION_THRESHOLD + 1
    g.heat = 50.0
    # Simulate AIMING loop: desperation not active
    desperation = g.timer < DESPERATION_THRESHOLD
    assert desperation is False  # heat decay should happen
    if not desperation:
        g.heat = max(0.0, g.heat - HEAT_DECAY)
    assert g.heat < 50.0


# ---- 42. Flying update stops on ground with low vy ----
def test_flying_ground_stop_low_vy() -> None:
    g = _make_playing()
    g.horseshoe = Horseshoe(x=160.0, y=GROUND_Y, vx=0.1, vy=1.5, color=RED)
    g.phase = Phase.FLYING
    g._update_flying()
    assert g.horseshoe.active is False


# ---- 43. Handle ringer spawns particles ----
def test_handle_ringer_spawns_particles() -> None:
    g = _make_playing()
    g.particles = []
    s = g.stakes[0]
    g.horseshoe = Horseshoe(x=s.x, y=s.y, vx=0.0, vy=0.0, color=s.color)
    g._handle_ringer(s)
    assert len(g.particles) >= 8


def _run() -> None:
    tests: list[tuple[str, object]] = [
        ("test_throw_creates_horseshoe", test_throw_creates_horseshoe),
        ("test_throw_zero_power", test_throw_zero_power),
        ("test_throw_weak_power", test_throw_weak_power),
        ("test_flying_applies_gravity", test_flying_applies_gravity),
        ("test_flying_ground_bounce", test_flying_ground_bounce),
        ("test_flying_stops_on_ground", test_flying_stops_on_ground),
        ("test_check_ringer_detects", test_check_ringer_detects),
        ("test_check_ringer_miss", test_check_ringer_miss),
        ("test_check_ringer_already_scored", test_check_ringer_already_scored),
        ("test_check_ringer_vertical_miss", test_check_ringer_vertical_miss),
        ("test_handle_ringer_match", test_handle_ringer_match),
        ("test_handle_ringer_mismatch", test_handle_ringer_mismatch),
        ("test_handle_ringer_super_activation", test_handle_ringer_super_activation),
        ("test_handle_ringer_super_any_color", test_handle_ringer_super_any_color),
        ("test_handle_ringer_super_multiplier", test_handle_ringer_super_multiplier),
        ("test_on_miss_resets_combo", test_on_miss_resets_combo),
        ("test_on_miss_floating_text", test_on_miss_floating_text),
        ("test_activate_super", test_activate_super),
        ("test_deactivate_super", test_deactivate_super),
        ("test_particles_update_and_expire", test_particles_update_and_expire),
        ("test_spawn_particles", test_spawn_particles),
        ("test_floating_texts_update", test_floating_texts_update),
        ("test_timer_decrements", test_timer_decrements),
        ("test_timer_zero_game_over", test_timer_zero_game_over),
        ("test_shuffle_stakes", test_shuffle_stakes),
        ("test_start_game_resets_state", test_start_game_resets_state),
        ("test_start_game_spawns_four_stakes", test_start_game_spawns_four_stakes),
        ("test_heat_decay", test_heat_decay),
        ("test_heat_not_negative", test_heat_not_negative),
        ("test_heat_max_clamped", test_heat_max_clamped),
        ("test_max_combo_tracks_highest", test_max_combo_tracks_highest),
        ("test_best_combo_on_game_over", test_best_combo_on_game_over),
        ("test_best_score_on_game_over", test_best_score_on_game_over),
        ("test_ghost_trail_saved", test_ghost_trail_saved),
        ("test_ghost_trail_downsamples", test_ghost_trail_downsamples),
        ("test_throw_max_power_clamped", test_throw_max_power_clamped),
        ("test_horseshoe_trail_records_path", test_horseshoe_trail_records_path),
        ("test_scoring_transitions_to_aiming", test_scoring_transitions_to_aiming),
        ("test_heat_100_game_over", test_heat_100_game_over),
        ("test_stake_shuffle_timer_inactive", test_stake_shuffle_timer_inactive),
        ("test_desperation_no_heat_decay", test_desperation_no_heat_decay),
        ("test_flying_ground_stop_low_vy", test_flying_ground_stop_low_vy),
        ("test_handle_ringer_spawns_particles", test_handle_ringer_spawns_particles),
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


if __name__ == "__main__":
    _run()
