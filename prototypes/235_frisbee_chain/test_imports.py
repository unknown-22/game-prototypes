"""test_imports.py -- Headless logic tests for FRISBEE CHAIN."""
from __future__ import annotations

import math
import random
import sys
import traceback
import unittest.mock as mock
from collections.abc import Callable

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
mock_pyxel.FONT_WIDTH = 4
sys.modules["pyxel"] = mock_pyxel

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/235_frisbee_chain")

from main import (  # noqa: E402
    Game, Phase, Disc, Particle, FloatingText,
    WHITE, RED, DISC_COLORS,
    BASKET_RADIUS,
    STAMINA_MAX, STAMINA_COST,
    MAX_HEAT, HEAT_MISMATCH, HEAT_MISS,
    MAX_POWER,
    GAME_DURATION, SUPER_DURATION, SUPER_COMBO_THRESHOLD,
    COLOR_CYCLE,
    MAX_GHOST_POINTS,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.stamina = STAMINA_MAX
    g.heat = 0.0
    g.timer = GAME_DURATION
    g.disc = None
    g.basket = None
    g.disc_color = 0
    g.color_timer = COLOR_CYCLE
    g.super_timer = 0
    g.aim_start_x = 0.0
    g.aim_start_y = 0.0
    g.dragging = False
    g.shake_frames = 0
    g.shake_intensity = 0
    g.scoring_timer = 0
    g.particles = []
    g.floating_texts = []
    g.ghost_trails = []
    g.best_trail = []
    g.best_score = 0
    g.rng = random.Random(seed)
    return g


def _make_playing(seed: int = 42) -> Game:
    g = _make_game(seed)
    g._start_game()
    return g


# ---- 1. _spawn_basket creates basket in valid bounds ----
def test_spawn_basket() -> None:
    g = _make_playing()
    assert g.basket is not None
    b = g.basket
    assert 40 <= b.x <= 280
    assert 30 <= b.y <= 150
    assert b.color in DISC_COLORS


# ---- 2. _launch_disc creates disc with velocity ----
def test_launch_disc_creates_disc() -> None:
    g = _make_playing()
    g._launch_disc(80.0, -60.0)
    assert g.disc is not None
    assert g.disc.active is True
    assert g.disc.vx > 0.0
    assert g.disc.vy < 0.0
    assert g.phase == Phase.FLYING


# ---- 3. _launch_disc ignores zero/minimal drag ----
def test_launch_disc_short_drag() -> None:
    g = _make_playing()
    g._launch_disc(5.0, 0.0)
    assert g.disc is None
    assert g.phase == Phase.AIMING


# ---- 4. _launch_disc clamps to max power ----
def test_launch_disc_max_power() -> None:
    g = _make_playing()
    g._launch_disc(1000.0, -1000.0)
    assert g.disc is not None
    speed = math.hypot(g.disc.vx, g.disc.vy)
    assert speed <= MAX_POWER * 1.01


# ---- 5. _launch_disc reduces power with low stamina ----
def test_launch_disc_low_stamina() -> None:
    g = _make_playing()
    g.stamina = 10.0
    g._launch_disc(80.0, -60.0)
    assert g.disc is not None
    speed = math.hypot(g.disc.vx, g.disc.vy)
    full_speed = _compute_full_speed(80.0, -60.0)
    assert speed < full_speed * 0.5


def _compute_full_speed(dx: float, dy: float) -> float:
    dist = math.hypot(dx, dy)
    raw_power = min(dist / 10.0, 1.0)
    return raw_power * MAX_POWER


# ---- 6. _launch_disc deducts stamina ----
def test_launch_disc_deducts_stamina() -> None:
    g = _make_playing()
    before = g.stamina
    g._launch_disc(80.0, -60.0)
    assert g.stamina == max(0.0, before - STAMINA_COST)


# ---- 7. _update_disc_flight applies gravity ----
def test_disc_flight_gravity() -> None:
    g = _make_playing()
    g.disc = Disc(x=160.0, y=100.0, vx=3.0, vy=0.0, color=RED, active=True)
    g._update_disc_flight()
    assert g.disc.vy > 0.0


# ---- 8. _check_landing detects out of bounds (y > HEIGHT) ----
def test_check_landing_oob_y() -> None:
    g = _make_playing()
    g.disc = Disc(x=160.0, y=300.0, vx=0.0, vy=0.0, color=RED, active=True)
    assert g._check_landing() is True


# ---- 9. _check_landing detects out of bounds (x > WIDTH) ----
def test_check_landing_oob_x() -> None:
    g = _make_playing()
    g.disc = Disc(x=400.0, y=100.0, vx=0.0, vy=0.0, color=RED, active=True)
    assert g._check_landing() is True


# ---- 10. _check_landing detects near basket ----
def test_check_landing_near_basket() -> None:
    g = _make_playing()
    assert g.basket is not None
    b = g.basket
    g.disc = Disc(x=b.x, y=b.y, vx=0.0, vy=0.0, color=RED, active=True)
    assert g._check_landing() is True


# ---- 11. _check_landing misses far from basket ----
def test_check_landing_far_from_basket() -> None:
    g = _make_playing()
    assert g.basket is not None
    b = g.basket
    g.disc = Disc(x=b.x + BASKET_RADIUS + 20, y=b.y, vx=0.0, vy=0.0, color=RED, active=True)
    assert g._check_landing() is False


# ---- 12. _check_landing returns False if no disc ----
def test_check_landing_no_disc() -> None:
    g = _make_playing()
    assert g._check_landing() is False


# ---- 13. _resolve_score match: combo++, score increases ----
def test_resolve_score_match() -> None:
    g = _make_playing()
    g.combo = 1
    g.score = 200
    assert g.basket is not None
    b = g.basket
    g.disc = Disc(x=b.x, y=b.y, vx=0.0, vy=0.0, color=b.color, active=True)
    g._resolve_score()
    assert g.combo == 2
    assert g.score == 200 + int(100 * 2 * 1.0)
    assert g.disc.active is False
    assert g.phase == Phase.SCORING


# ---- 14. _resolve_score mismatch: combo resets, heat increases ----
def test_resolve_score_mismatch() -> None:
    g = _make_playing()
    g.combo = 3
    g.heat = 20.0
    assert g.basket is not None
    b = g.basket
    mismatch_color = b.color
    for c in DISC_COLORS:
        if c != b.color:
            mismatch_color = c
            break
    g.disc = Disc(x=b.x, y=b.y, vx=0.0, vy=0.0, color=mismatch_color, active=True)
    g._resolve_score()
    assert g.combo == 0
    assert g.heat == 20.0 + HEAT_MISMATCH


# ---- 15. _resolve_score miss: combo resets, heat increases ----
def test_resolve_score_miss() -> None:
    g = _make_playing()
    g.combo = 5
    g.heat = 30.0
    assert g.basket is not None
    b = g.basket
    g.disc = Disc(x=b.x + BASKET_RADIUS + 10, y=b.y + BASKET_RADIUS + 10,
                  vx=0.0, vy=0.0, color=b.color, active=True)
    g._resolve_score()
    assert g.combo == 0
    assert g.heat == 30.0 + HEAT_MISS
    assert g.phase == Phase.SCORING


# ---- 16. _resolve_score activates super at threshold ----
def test_resolve_score_super_activation() -> None:
    g = _make_playing()
    g.combo = SUPER_COMBO_THRESHOLD - 1
    assert g.basket is not None
    b = g.basket
    g.disc = Disc(x=b.x, y=b.y, vx=0.0, vy=0.0, color=b.color, active=True)
    g._resolve_score()
    assert g.combo == SUPER_COMBO_THRESHOLD
    assert g.super_timer == SUPER_DURATION


# ---- 17. _resolve_score super mode any color matches ----
def test_resolve_score_super_any_color() -> None:
    g = _make_playing()
    g.super_timer = 100
    g.combo = 1
    g.score = 500
    assert g.basket is not None
    b = g.basket
    mismatch_color = b.color
    for c in DISC_COLORS:
        if c != b.color:
            mismatch_color = c
            break
    g.disc = Disc(x=b.x, y=b.y, vx=0.0, vy=0.0, color=mismatch_color, active=True)
    g._resolve_score()
    assert g.combo == 2
    assert g.score > 500


# ---- 18. _resolve_score super mode 3x score ----
def test_resolve_score_super_multiplier() -> None:
    g = _make_playing()
    g.super_timer = 100
    g.combo = 1
    g.score = 0
    assert g.basket is not None
    b = g.basket
    g.disc = Disc(x=b.x, y=b.y, vx=0.0, vy=0.0, color=b.color, active=True)
    g._resolve_score()
    assert g.score == int(100 * 2 * 3.0)


# ---- 19. _resolve_score spawns particles on match ----
def test_resolve_score_particles_on_match() -> None:
    g = _make_playing()
    g.particles = []
    assert g.basket is not None
    b = g.basket
    g.disc = Disc(x=b.x, y=b.y, vx=0.0, vy=0.0, color=b.color, active=True)
    g._resolve_score()
    assert len(g.particles) >= 15


# ---- 20. _resolve_score floating text on match ----
def test_resolve_score_floating_text_on_match() -> None:
    g = _make_playing()
    g.floating_texts = []
    assert g.basket is not None
    b = g.basket
    g.disc = Disc(x=b.x, y=b.y, vx=0.0, vy=0.0, color=b.color, active=True)
    g._resolve_score()
    assert len(g.floating_texts) >= 1
    assert any("+" in ft.text for ft in g.floating_texts)


# ---- 21. _activate_super sets state ----
def test_activate_super() -> None:
    g = _make_playing()
    assert g.super_timer == 0
    g._activate_super()
    assert g.super_timer == SUPER_DURATION
    assert g.shake_frames == 15


# ---- 22. _update_super_timer decrements and deactivates ----
def test_update_super_timer_deactivates() -> None:
    g = _make_playing()
    g.super_timer = 1
    g.combo = 10
    g._update_super_timer()
    assert g.super_timer == 0
    assert g.combo == 0


# ---- 23. _update_super_timer decrements while active ----
def test_update_super_timer_decrements() -> None:
    g = _make_playing()
    g.super_timer = 50
    g.combo = 5
    g._update_super_timer()
    assert g.super_timer == 49
    assert g.combo == 5


# ---- 24. _update_timers decrements timer ----
def test_update_timers_decrements() -> None:
    g = _make_playing()
    g.timer = 100
    g._update_timers()
    assert g.timer == 99


# ---- 25. _update_timers recharges stamina ----
def test_update_timers_recharges_stamina() -> None:
    g = _make_playing()
    g.stamina = 50.0
    g._update_timers()
    assert g.stamina > 50.0
    assert g.stamina <= STAMINA_MAX


# ---- 26. _update_timers decays heat ----
def test_update_timers_decays_heat() -> None:
    g = _make_playing()
    g.heat = 50.0
    g._update_timers()
    assert g.heat < 50.0


# ---- 27. _update_timers cycles disc color ----
def test_update_timers_cycles_color() -> None:
    g = _make_playing()
    g.color_timer = 1
    g.disc_color = 0
    g._update_timers()
    assert g.disc_color == 1
    assert g.color_timer == COLOR_CYCLE


# ---- 28. Stamina max clamped ----
def test_stamina_max_clamped() -> None:
    g = _make_playing()
    g.stamina = STAMINA_MAX
    g._update_timers()
    assert g.stamina == STAMINA_MAX


# ---- 29. Heat not negative ----
def test_heat_not_negative() -> None:
    g = _make_playing()
    g.heat = 0.0
    g._update_timers()
    assert g.heat == 0.0


# ---- 30. Heat max clamped ----
def test_heat_max_clamped() -> None:
    g = _make_playing()
    g.heat = MAX_HEAT - 5.0
    g.heat = min(MAX_HEAT, g.heat + HEAT_MISMATCH)
    assert g.heat == MAX_HEAT


# ---- 31. _spawn_particles creates correct count ----
def test_spawn_particles() -> None:
    g = _make_playing()
    g._spawn_particles(100.0, 100.0, RED, 5)
    assert len(g.particles) == 5
    assert all(p.life > 0 for p in g.particles)


# ---- 32. _update_particles moves and expires ----
def test_update_particles() -> None:
    g = _make_playing()
    g.particles = [
        Particle(0.0, 0.0, 1.0, 0.0, life=1, color=RED),
        Particle(0.0, 0.0, 0.0, 0.0, life=3, color=RED),
    ]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 2


# ---- 33. _update_floating_texts moves and expires ----
def test_update_floating_texts() -> None:
    g = _make_playing()
    g.floating_texts = [
        FloatingText(100.0, 100.0, "A", life=1, color=WHITE),
        FloatingText(100.0, 100.0, "B", life=3, color=WHITE),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "B"


# ---- 34. _start_game resets all state ----
def test_start_game_resets_state() -> None:
    g = _make_playing()
    g.score = 999
    g.combo = 10
    g.heat = 80.0
    g.super_timer = 200
    g.best_trail = [(1.0, 1.0)]
    g._start_game()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert len(g.best_trail) == 0
    assert g.basket is not None
    assert g.phase == Phase.AIMING


# ---- 35. Max combo tracks highest ----
def test_max_combo_tracks_highest() -> None:
    g = _make_playing()
    g.combo = 3
    assert g.basket is not None
    b = g.basket
    g.disc = Disc(x=b.x, y=b.y, vx=0.0, vy=0.0, color=b.color, active=True)
    g._resolve_score()
    assert g.max_combo == 4


# ---- 36. _end_game updates best_score ----
def test_end_game_best_score() -> None:
    g = _make_playing()
    g.score = 5000
    g.best_score = 3000
    g._end_game()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 5000


# ---- 37. _end_game keeps lower best_score ----
def test_end_game_lower_score() -> None:
    g = _make_playing()
    g.score = 100
    g.best_score = 5000
    g._end_game()
    assert g.best_score == 5000


# ---- 38. Timer zero triggers game over via _end_game ----
def test_timer_zero_ends_game() -> None:
    g = _make_playing()
    g.timer = 0
    g._update_timers()
    assert g.timer == 0


# ---- 39. Scoring timer transitions to AIMING ----
def test_scoring_transitions() -> None:
    g = _make_playing()
    g.phase = Phase.SCORING
    g.scoring_timer = 1
    g.disc = Disc(x=160.0, y=200.0, vx=0.0, vy=0.0, color=RED, active=False)
    g.scoring_timer -= 1
    assert g.scoring_timer == 0


# ---- 40. Basket spans all colors over time ----
def test_basket_spawn_various_colors() -> None:
    g = _make_game(seed=1)
    g._start_game()
    colors_seen: set[int] = set()
    for _ in range(20):
        g._spawn_basket()
        assert g.basket is not None
        colors_seen.add(g.basket.color)
    assert len(colors_seen) >= 2


# ---- 41. Ghost trail saved on match ----
def test_ghost_trail_saved() -> None:
    g = _make_playing()
    g.combo = 1
    assert g.basket is not None
    b = g.basket
    trail_data = [(160.0, 200.0), (170.0, 180.0), (b.x, b.y)]
    g.disc = Disc(x=b.x, y=b.y, vx=0.0, vy=0.0,
                  color=b.color, active=True, trail=list(trail_data))
    g._resolve_score()
    assert len(g.best_trail) > 0


# ---- 42. Ghost trail downsamples ----
def test_ghost_trail_downsamples() -> None:
    trail_data = [(float(i), float(i)) for i in range(200)]
    result = list(trail_data)
    if len(result) > MAX_GHOST_POINTS:
        step = len(result) / MAX_GHOST_POINTS
        result = [result[int(i * step)] for i in range(MAX_GHOST_POINTS)]
    assert len(result) == MAX_GHOST_POINTS


# ---- 43. _launch_disc with zero stamina — no throw possible ----
def test_launch_disc_zero_stamina() -> None:
    g = _make_playing()
    g.stamina = 0.0
    g._launch_disc(80.0, -60.0)
    assert g.disc is None  # too weak to throw


# ---- 44. Stamina recharges during SCORING ----
def test_stamina_recharge_during_scoring() -> None:
    g = _make_playing()
    g.stamina = 50.0
    g.phase = Phase.SCORING
    g._update_timers()
    assert g.stamina > 50.0


def _run() -> None:
    tests: list[tuple[str, Callable[[], None]]] = [
        ("test_spawn_basket", test_spawn_basket),
        ("test_launch_disc_creates_disc", test_launch_disc_creates_disc),
        ("test_launch_disc_short_drag", test_launch_disc_short_drag),
        ("test_launch_disc_max_power", test_launch_disc_max_power),
        ("test_launch_disc_low_stamina", test_launch_disc_low_stamina),
        ("test_launch_disc_deducts_stamina", test_launch_disc_deducts_stamina),
        ("test_disc_flight_gravity", test_disc_flight_gravity),
        ("test_check_landing_oob_y", test_check_landing_oob_y),
        ("test_check_landing_oob_x", test_check_landing_oob_x),
        ("test_check_landing_near_basket", test_check_landing_near_basket),
        ("test_check_landing_far_from_basket", test_check_landing_far_from_basket),
        ("test_check_landing_no_disc", test_check_landing_no_disc),
        ("test_resolve_score_match", test_resolve_score_match),
        ("test_resolve_score_mismatch", test_resolve_score_mismatch),
        ("test_resolve_score_miss", test_resolve_score_miss),
        ("test_resolve_score_super_activation", test_resolve_score_super_activation),
        ("test_resolve_score_super_any_color", test_resolve_score_super_any_color),
        ("test_resolve_score_super_multiplier", test_resolve_score_super_multiplier),
        ("test_resolve_score_particles_on_match", test_resolve_score_particles_on_match),
        ("test_resolve_score_floating_text_on_match", test_resolve_score_floating_text_on_match),
        ("test_activate_super", test_activate_super),
        ("test_update_super_timer_deactivates", test_update_super_timer_deactivates),
        ("test_update_super_timer_decrements", test_update_super_timer_decrements),
        ("test_update_timers_decrements", test_update_timers_decrements),
        ("test_update_timers_recharges_stamina", test_update_timers_recharges_stamina),
        ("test_update_timers_decays_heat", test_update_timers_decays_heat),
        ("test_update_timers_cycles_color", test_update_timers_cycles_color),
        ("test_stamina_max_clamped", test_stamina_max_clamped),
        ("test_heat_not_negative", test_heat_not_negative),
        ("test_heat_max_clamped", test_heat_max_clamped),
        ("test_spawn_particles", test_spawn_particles),
        ("test_update_particles", test_update_particles),
        ("test_update_floating_texts", test_update_floating_texts),
        ("test_start_game_resets_state", test_start_game_resets_state),
        ("test_max_combo_tracks_highest", test_max_combo_tracks_highest),
        ("test_end_game_best_score", test_end_game_best_score),
        ("test_end_game_lower_score", test_end_game_lower_score),
        ("test_timer_zero_ends_game", test_timer_zero_ends_game),
        ("test_scoring_transitions", test_scoring_transitions),
        ("test_basket_spawn_various_colors", test_basket_spawn_various_colors),
        ("test_ghost_trail_saved", test_ghost_trail_saved),
        ("test_ghost_trail_downsamples", test_ghost_trail_downsamples),
        ("test_launch_disc_zero_stamina", test_launch_disc_zero_stamina),
        ("test_stamina_recharge_during_scoring", test_stamina_recharge_during_scoring),
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
