"""test_imports.py -- Headless logic tests for STAR CHAIN (prototype 303).

Run standalone:  uv run python prototypes/303_star_chain/test_imports.py
Run via pytest:  uv run pytest prototypes/303_star_chain/test_imports.py
"""
from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import (  # noqa: E402
    DARK_BLUE,
    GRAY,
    LIME,
    RED,
    SCREEN_H,
    SCREEN_W,
    STAR_COLORS,
    WHITE,
    YELLOW,
    FloatingText,
    Game,
    Particle,
    Phase,
    Star,
)

GAME_TIME = 3600


def make_game() -> Game:
    """Bypass __init__ (avoids pyxel.init/run); reseed rng for determinism."""
    g = Game.__new__(Game)
    g.reset()
    g.rng = random.Random(42)
    return g


def make_star(color: int, life: int = 300) -> Star:
    return Star(100.0, 100.0, color, life, 0.0, 0.0, 0)


# -- Enum / dataclasses -------------------------------------------------------


def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


def test_star_colors() -> None:
    assert len(STAR_COLORS) == 4
    assert RED in STAR_COLORS
    assert LIME in STAR_COLORS
    assert DARK_BLUE in STAR_COLORS
    assert YELLOW in STAR_COLORS


def test_dataclass_instances() -> None:
    s = Star(1.5, 2.5, RED, 300, 0.1, -0.1, 7)
    assert s.x == 1.5 and s.color == RED and s.life == 300 and s.twinkle == 7
    p = Particle(0, 0, 1, 1, 10, GRAY)
    assert p.life == 10 and p.color == GRAY
    t = FloatingText(0, 0, "hi", 5, WHITE)
    assert t.text == "hi" and t.life == 5


# -- reset / start ------------------------------------------------------------


def test_reset_initial_state() -> None:
    g = make_game()
    assert g.phase == Phase.TITLE
    assert g.align_color == RED
    assert g.score == 0
    assert g.best_score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.timer == GAME_TIME
    assert g.elapsed == 0
    assert g.stars == []
    assert g.constellation == []
    assert g.last_obs_x is None and g.last_obs_y is None
    assert g.particles == []
    assert g.floating_texts == []


def test_start_playing_initializes_run() -> None:
    g = make_game()
    g.start_playing()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.timer == GAME_TIME
    assert g.super_timer == 0
    assert g.align_color == RED
    assert len(g.stars) == g.INITIAL_STARS


# -- observe_star: match / combo / score --------------------------------------


def test_first_match_increments_combo_and_score() -> None:
    g = make_game()
    gained = g.observe_star(make_star(RED))
    assert gained == 10
    assert g.combo == 1
    assert g.score == 10
    assert g.max_combo == 1
    assert g.heat == 0.0


def test_consecutive_same_color_builds_combo() -> None:
    g = make_game()
    g.observe_star(make_star(RED))
    gained = g.observe_star(make_star(RED))
    assert gained == 20  # 10 * 2
    assert g.combo == 2
    assert g.score == 30
    assert g.max_combo == 2


def test_constellation_segment_on_second_match() -> None:
    g = make_game()
    g.observe_star(make_star(RED))
    assert g.constellation == []  # no segment on first observation
    g.observe_star(make_star(RED))
    assert len(g.constellation) == 1
    x1, y1, x2, y2, c = g.constellation[0]
    assert (x1, y1, x2, y2) == (100.0, 100.0, 100.0, 100.0)
    assert c == RED


# -- observe_star: mismatch / re-align / heat ---------------------------------


def test_mismatch_resets_combo_and_adds_heat() -> None:
    g = make_game()
    g.observe_star(make_star(RED))
    g.observe_star(make_star(RED))
    assert g.combo == 2
    gained = g.observe_star(make_star(LIME))
    assert gained == 0
    assert g.combo == 0
    assert g.heat == 15.0
    assert g.align_color == LIME  # re-aligned
    assert g.last_obs_x is None and g.last_obs_y is None  # trail broken


def test_mismatch_keeps_max_combo() -> None:
    g = make_game()
    for _ in range(3):
        g.observe_star(make_star(RED))
    assert g.max_combo == 3
    g.observe_star(make_star(LIME))  # mismatch resets combo, not max_combo
    assert g.combo == 0
    assert g.max_combo == 3


def test_realign_then_new_color_matches() -> None:
    g = make_game()
    g.observe_star(make_star(LIME))  # mismatch: re-align to LIME
    assert g.align_color == LIME
    gained = g.observe_star(make_star(LIME))  # now matches
    assert gained == 10
    assert g.combo == 1


# -- SUPER TELESCOPE ----------------------------------------------------------


def test_combo_4_triggers_super() -> None:
    g = make_game()
    for _ in range(4):
        g.observe_star(make_star(RED))
    assert g.combo == 4
    assert g.super_timer == 300


def test_super_matches_any_color_with_3x() -> None:
    g = make_game()
    for _ in range(4):
        g.observe_star(make_star(RED))
    assert g.super_timer == 300
    # In SUPER mode, a different color still matches, at 3x multiplier.
    gained = g.observe_star(make_star(DARK_BLUE))
    assert gained == 150  # 10 * 5 * 3
    assert g.combo == 5
    assert g.align_color == RED  # unchanged in super match
    assert g.heat == 0.0  # no mismatch heat


def test_update_super_decrements() -> None:
    g = make_game()
    for _ in range(4):
        g.observe_star(make_star(RED))
    g.update_super()
    assert g.super_timer == 299


# -- handle_click -------------------------------------------------------------


def test_handle_click_observes_and_removes_star() -> None:
    g = make_game()
    g.stars = [Star(100.0, 100.0, RED, 300, 0.0, 0.0, 0)]
    g.handle_click(102, 101)
    assert g.stars == []
    assert g.combo == 1
    assert g.score == 10


def test_handle_click_empty_is_noop() -> None:
    g = make_game()
    g.stars = [Star(100.0, 100.0, RED, 300, 0.0, 0.0, 0)]
    g.handle_click(200, 200)  # far away
    assert len(g.stars) == 1
    assert g.combo == 0
    assert g.score == 0


def test_handle_click_picks_nearest_within_radius() -> None:
    g = make_game()
    g.stars = [
        Star(100.0, 100.0, RED, 300, 0.0, 0.0, 0),
        Star(105.0, 105.0, LIME, 300, 0.0, 0.0, 0),
    ]
    g.handle_click(104, 104)  # closer to the LIME star
    assert len(g.stars) == 1
    assert g.stars[0].color == RED  # LIME star was removed
    assert g.align_color == LIME  # mismatch re-aligned to LIME


# -- update_heat / update_timer ----------------------------------------------


def test_heat_threshold_triggers_game_over_before_decay() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.heat = 100.0
    g.update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.heat == 100.0  # unchanged: check happens before decay


def test_heat_decays_when_below_threshold() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.heat = 50.0
    g.update_heat()
    assert g.phase == Phase.PLAYING
    assert abs(g.heat - 49.98) < 0.001


def test_heat_decay_floor_zero() -> None:
    g = make_game()
    g.heat = 0.01
    g.update_heat()
    assert g.heat == 0.0


def test_timer_decrements_and_ends() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.timer = 5
    g.update_timer()
    assert g.timer == 4
    assert g.phase == Phase.PLAYING
    g.timer = 1
    g.update_timer()
    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER


# -- difficulty / spawning / stars -------------------------------------------


def test_difficulty_start_values() -> None:
    g = make_game()
    g.elapsed = 0
    g.update_difficulty()
    assert g.spawn_interval == 60
    assert g.max_stars == 12
    assert g.star_lifetime == 300


def test_difficulty_end_values() -> None:
    g = make_game()
    g.elapsed = GAME_TIME
    g.update_difficulty()
    assert g.spawn_interval == 25
    assert g.max_stars == 24
    assert g.star_lifetime == 150


def test_spawn_respects_max_stars() -> None:
    g = make_game()
    g.max_stars = 2
    g.stars = [make_star(RED), make_star(LIME)]
    g.spawn_star()
    assert len(g.stars) == 2  # at capacity, no spawn


def test_update_spawning_spawns_and_resets_timer() -> None:
    g = make_game()
    g.spawn_interval = 60
    g.spawn_timer = 1
    g.stars = []
    g.max_stars = 12
    g.update_spawning()
    assert len(g.stars) == 1
    assert g.spawn_timer == 60


def test_update_stars_decrements_life_and_removes_dead() -> None:
    g = make_game()
    g.stars = [make_star(RED, life=1), make_star(LIME, life=2)]
    g.update_stars()
    assert len(g.stars) == 1
    assert g.stars[0].life == 1  # survived, life decremented 2 -> 1


def test_update_stars_wraps_position() -> None:
    g = make_game()
    s = Star(SCREEN_W - 0.1, SCREEN_H - 0.1, RED, 300, 0.3, 0.3, 0)
    g.stars = [s]
    g.update_stars()
    # (319.9 + 0.3) % 320 == 0.2 ; wrap-around occurred
    assert s.x < 1.0 and s.y < 1.0


# -- particles / floating text -----------------------------------------------


def test_match_spawns_particles_and_text() -> None:
    g = make_game()
    g.observe_star(make_star(RED))
    assert len(g.particles) == 8
    assert len(g.floating_texts) == 1  # "+10"


def test_mismatch_spawns_particles_and_text() -> None:
    g = make_game()
    g.observe_star(make_star(LIME))
    assert len(g.particles) == 4
    assert len(g.floating_texts) == 1  # "WRONG!"
    assert g.shake_frames == 8


def test_particle_update_removes_dead() -> None:
    g = make_game()
    g.particles = [Particle(0, 0, 0, 0, 1, RED), Particle(0, 0, 0, 0, 2, RED)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 1


def test_floating_text_update_removes_dead() -> None:
    g = make_game()
    g.floating_texts = [
        FloatingText(0, 0, "a", 1, WHITE),
        FloatingText(0, 0, "b", 2, WHITE),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "b"


# -- runner ------------------------------------------------------------------


def _run_all() -> None:
    tests = [
        v
        for k, v in sorted(globals().items())
        if k.startswith("test_") and callable(v)
    ]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    _run_all()
