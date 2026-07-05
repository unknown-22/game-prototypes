"""test_imports.py — Headless logic tests for 198_magnet_surge."""

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/198_magnet_surge")
from main import (
    Game,
    Phase,
    Scrap,
    Particle,
    FloatingText,
    COLORS,
    HEAT_MAX,
    HEAT_SYNTH_REDUCTION,
    SUPER_DURATION,
    SPAWN_INTERVAL,
    SCREEN_W,
    SCREEN_H,
)


def _make_seeded_game(seed: int = 42) -> Game:
    g = Game._make_game()
    g._rng = random.Random(seed)
    g.reset()
    return g


# --- Test: _make_game factory creates valid Game ---
def test_make_game() -> None:
    g = Game._make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert len(g.scraps) == 0
    assert len(g.nuggets) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g._last_syn_color is None


# --- Test: reset() initializes correctly ---
def test_reset_initial_state() -> None:
    g = _make_seeded_game(42)
    assert g.phase == Phase.TITLE
    assert g.magnet_x == SCREEN_W / 2
    assert g.magnet_y == SCREEN_H / 2
    assert g.magnet_color == 0
    assert g.game_timer == 3600
    assert len(g.scraps) == 0
    assert len(g.nuggets) == 0


# --- Test: spawn_scrap ---
def test_spawn_scrap() -> None:
    g = _make_seeded_game(42)
    g._spawn_scrap()
    assert len(g.scraps) == 1
    s = g.scraps[0]
    assert s.color in (0, 1, 2, 3)
    assert s.radius == 3


def test_spawn_scrap_max_limit() -> None:
    g = _make_seeded_game(42)
    for _ in range(30):
        g._spawn_scrap()
    assert len(g.scraps) == 30
    g._spawn_scrap()
    assert len(g.scraps) == 30


# --- Test: cycle_color ---
def test_cycle_color() -> None:
    g = _make_seeded_game(42)
    assert g.magnet_color == 0
    g._cycle_color()
    assert g.magnet_color == 1
    g._cycle_color()
    assert g.magnet_color == 2
    g._cycle_color()
    assert g.magnet_color == 3
    g._cycle_color()
    assert g.magnet_color == 0


# --- Test: attract_scraps ---
def test_attract_same_color() -> None:
    g = _make_seeded_game(42)
    g.magnet_x = 160
    g.magnet_y = 120
    g.magnet_color = 0
    s = Scrap(x=160, y=80, vx=0, vy=0, color=0)
    g.scraps.append(s)
    g._attract_scraps()
    assert s.vy > 0


def test_attract_different_color_no_attract() -> None:
    g = _make_seeded_game(42)
    g.magnet_x = 160
    g.magnet_y = 120
    g.magnet_color = 0
    s = Scrap(x=160, y=80, vx=0, vy=0, color=1)
    g.scraps.append(s)
    g._attract_scraps()
    assert abs(s.vy) < 0.01


def test_attract_super_mode_attracts_all() -> None:
    g = _make_seeded_game(42)
    g.super_timer = 100
    g.magnet_x = 160
    g.magnet_y = 120
    g.magnet_color = 0
    s = Scrap(x=160, y=80, vx=0, vy=0, color=1)
    g.scraps.append(s)
    g._attract_scraps()
    assert s.vy > 0


# --- Test: move_scraps and edge bouncing ---
def test_move_scraps_edge_bounce() -> None:
    g = _make_seeded_game(42)
    s = Scrap(x=0, y=120, vx=-2, vy=0, color=0)
    g.scraps.append(s)
    g._move_scraps()
    assert s.x >= s.radius
    assert s.vx >= 0


def test_move_scraps_nuggets() -> None:
    g = _make_seeded_game(42)
    n = Scrap(x=160, y=120, vx=0.5, vy=0, color=0, radius=5)
    g.nuggets.append(n)
    g._move_scraps()
    assert n.x > 160
    assert abs(n.vx) < 0.5


# --- Test: synthesis clustering ---
def test_synthesis_three_same_color_near_magnet() -> None:
    g = _make_seeded_game(42)
    g.magnet_x = 160
    g.magnet_y = 120
    g.magnet_color = 0
    g.phase = Phase.PLAYING

    g.scraps = [
        Scrap(x=155, y=115, vx=0, vy=0, color=0),
        Scrap(x=160, y=118, vx=0, vy=0, color=0),
        Scrap(x=157, y=112, vx=0, vy=0, color=0),
    ]
    g._check_synthesis()
    assert len(g.scraps) == 0
    assert len(g.nuggets) == 1
    assert g.combo == 1


def test_synthesis_three_but_not_near_magnet() -> None:
    g = _make_seeded_game(42)
    g.magnet_x = 160
    g.magnet_y = 120
    g.magnet_color = 0
    g.phase = Phase.PLAYING

    g.scraps = [
        Scrap(x=30, y=30, vx=0, vy=0, color=0),
        Scrap(x=33, y=31, vx=0, vy=0, color=0),
        Scrap(x=31, y=33, vx=0, vy=0, color=0),
    ]
    g._check_synthesis()
    assert len(g.scraps) == 3
    assert len(g.nuggets) == 0


def test_synthesis_only_two_scraps() -> None:
    g = _make_seeded_game(42)
    g.magnet_x = 160
    g.magnet_y = 120
    g.magnet_color = 0
    g.phase = Phase.PLAYING

    g.scraps = [
        Scrap(x=155, y=115, vx=0, vy=0, color=0),
        Scrap(x=157, y=117, vx=0, vy=0, color=0),
    ]
    g._check_synthesis()
    assert len(g.scraps) == 2
    assert len(g.nuggets) == 0


def test_synthesis_mixed_colors_only_same_cluster() -> None:
    g = _make_seeded_game(42)
    g.magnet_x = 160
    g.magnet_y = 120
    g.magnet_color = 0
    g.phase = Phase.PLAYING

    # Color=1 scrap placed far from cluster to avoid CA spread
    g.scraps = [
        Scrap(x=155, y=115, vx=0, vy=0, color=0),
        Scrap(x=157, y=117, vx=0, vy=0, color=0),
        Scrap(x=158, y=116, vx=0, vy=0, color=0),
        Scrap(x=200, y=200, vx=0, vy=0, color=1),
    ]
    g._check_synthesis()
    assert len(g.scraps) == 1
    assert len(g.nuggets) == 1
    assert g.scraps[0].color == 1


# --- Test: CA spread ---
def test_ca_spread_changes_nearby_scraps() -> None:
    g = _make_seeded_game(42)
    g.magnet_x = 160
    g.magnet_y = 120
    g.magnet_color = 0
    g.phase = Phase.PLAYING
    g._last_syn_color = 0

    g.scraps = [
        Scrap(x=155, y=115, vx=0, vy=0, color=0),
        Scrap(x=157, y=117, vx=0, vy=0, color=0),
        Scrap(x=158, y=116, vx=0, vy=0, color=0),
        Scrap(x=162, y=118, vx=0, vy=0, color=1),
        Scrap(x=150, y=112, vx=0, vy=0, color=2),
    ]
    g._check_synthesis()
    for s in g.scraps:
        assert s.color == 0


# --- Test: combo chain ---
def test_combo_increments_on_same_color_synthesis() -> None:
    g = _make_seeded_game(42)
    g.magnet_x = 160
    g.magnet_y = 120
    g.magnet_color = 0
    g.phase = Phase.PLAYING

    g._last_syn_color = 0
    g.combo = 1
    g.scraps = [
        Scrap(x=155, y=115, vx=0, vy=0, color=0),
        Scrap(x=157, y=117, vx=0, vy=0, color=0),
        Scrap(x=158, y=116, vx=0, vy=0, color=0),
    ]
    g._check_synthesis()
    assert g.combo == 2
    assert g._last_syn_color == 0

    g.scraps = [
        Scrap(x=155, y=115, vx=0, vy=0, color=0),
        Scrap(x=157, y=117, vx=0, vy=0, color=0),
        Scrap(x=158, y=116, vx=0, vy=0, color=0),
    ]
    g._check_synthesis()
    assert g.combo == 3


def test_combo_resets_on_different_color_synthesis() -> None:
    g = _make_seeded_game(42)
    g.magnet_x = 160
    g.magnet_y = 120
    g.magnet_color = 0
    g.phase = Phase.PLAYING

    g._last_syn_color = 0
    g.combo = 3
    g.scraps = [
        Scrap(x=155, y=115, vx=0, vy=0, color=1),
        Scrap(x=157, y=117, vx=0, vy=0, color=1),
        Scrap(x=158, y=116, vx=0, vy=0, color=1),
    ]
    g._check_synthesis()
    assert g.combo == 1
    assert g._last_syn_color == 1


# --- Test: max_combo tracks ---
def test_max_combo_tracks_peak() -> None:
    g = _make_seeded_game(42)
    g.magnet_x = 160
    g.magnet_y = 120
    g.magnet_color = 0
    g.phase = Phase.PLAYING

    g._last_syn_color = 0
    g.combo = 3
    g.max_combo = 3

    g.scraps = [
        Scrap(x=155, y=115, vx=0, vy=0, color=0),
        Scrap(x=157, y=117, vx=0, vy=0, color=0),
        Scrap(x=158, y=116, vx=0, vy=0, color=0),
    ]
    g._check_synthesis()
    assert g.combo == 4
    assert g.max_combo == 4

    g.scraps = [
        Scrap(x=155, y=115, vx=0, vy=0, color=1),
        Scrap(x=157, y=117, vx=0, vy=0, color=1),
        Scrap(x=158, y=116, vx=0, vy=0, color=1),
    ]
    g._check_synthesis()
    assert g.combo == 1
    assert g.max_combo == 4


# --- Test: super mode activation ---
def test_super_activates_at_combo_threshold() -> None:
    g = _make_seeded_game(42)
    g.magnet_x = 160
    g.magnet_y = 120
    g.magnet_color = 0
    g.phase = Phase.PLAYING

    g._last_syn_color = 0
    g.combo = 3

    g.scraps = [
        Scrap(x=155, y=115, vx=0, vy=0, color=0),
        Scrap(x=157, y=117, vx=0, vy=0, color=0),
        Scrap(x=158, y=116, vx=0, vy=0, color=0),
    ]
    g._check_synthesis()
    assert g.combo == 4
    assert g.super_timer == SUPER_DURATION
    assert g._is_super_active()


def test_super_not_reactivate_during_active() -> None:
    g = _make_seeded_game(42)
    g.magnet_x = 160
    g.magnet_y = 120
    g.magnet_color = 0
    g.phase = Phase.PLAYING

    g._last_syn_color = 0
    g.combo = 3
    g.super_timer = SUPER_DURATION

    g.scraps = [
        Scrap(x=155, y=115, vx=0, vy=0, color=0),
        Scrap(x=157, y=117, vx=0, vy=0, color=0),
        Scrap(x=158, y=116, vx=0, vy=0, color=0),
    ]
    g._check_synthesis()
    assert g.combo == 4
    assert g.super_timer == SUPER_DURATION


# --- Test: heat system ---
def test_heat_increases_without_synthesis() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLAYING
    g._frame_without_syn = 21
    g._tick()
    assert g.heat > 0.0


def test_heat_reduces_on_synthesis() -> None:
    g = _make_seeded_game(42)
    g.magnet_x = 160
    g.magnet_y = 120
    g.magnet_color = 0
    g.phase = Phase.PLAYING
    g.heat = 50.0

    g.scraps = [
        Scrap(x=155, y=115, vx=0, vy=0, color=0),
        Scrap(x=157, y=117, vx=0, vy=0, color=0),
        Scrap(x=158, y=116, vx=0, vy=0, color=0),
    ]
    g._check_synthesis()
    assert g.heat == 50.0 - HEAT_SYNTH_REDUCTION


def test_heat_game_over() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLAYING
    g.heat = HEAT_MAX
    g._tick()
    assert g.phase == Phase.GAME_OVER


# --- Test: score calculation ---
def test_score_on_synthesis() -> None:
    g = _make_seeded_game(42)
    g.magnet_x = 160
    g.magnet_y = 120
    g.magnet_color = 0
    g.phase = Phase.PLAYING
    g._last_syn_color = 0
    g.combo = 1

    g.scraps = [
        Scrap(x=155, y=115, vx=0, vy=0, color=0),
        Scrap(x=157, y=117, vx=0, vy=0, color=0),
        Scrap(x=158, y=116, vx=0, vy=0, color=0),
    ]
    score_before = g.score
    g._check_synthesis()
    assert g.score > score_before
    assert g.score == score_before + 200


def test_score_super_multiplier() -> None:
    g = _make_seeded_game(42)
    g.magnet_x = 160
    g.magnet_y = 120
    g.magnet_color = 0
    g.phase = Phase.PLAYING
    g._last_syn_color = 0
    g.combo = 2
    g.super_timer = 100

    g.scraps = [
        Scrap(x=155, y=115, vx=0, vy=0, color=0),
        Scrap(x=157, y=117, vx=0, vy=0, color=0),
        Scrap(x=158, y=116, vx=0, vy=0, color=0),
    ]
    score_before = g.score
    g._check_synthesis()
    assert g.score == score_before + 900


# --- Test: larger cluster synthesis ---
def test_synthesis_larger_cluster() -> None:
    g = _make_seeded_game(42)
    g.magnet_x = 160
    g.magnet_y = 120
    g.magnet_color = 0
    g.phase = Phase.PLAYING
    g._last_syn_color = 0
    g.combo = 1

    g.scraps = [
        Scrap(x=155, y=115, vx=0, vy=0, color=0),
        Scrap(x=156, y=116, vx=0, vy=0, color=0),
        Scrap(x=157, y=117, vx=0, vy=0, color=0),
        Scrap(x=158, y=118, vx=0, vy=0, color=0),
        Scrap(x=159, y=119, vx=0, vy=0, color=0),
    ]
    g._check_synthesis()
    assert len(g.scraps) == 0
    assert len(g.nuggets) == 1
    assert g.nuggets[0].radius > 5


# --- Test: BFS clustering across chain ---
def test_synthesis_bfs_chain() -> None:
    g = _make_seeded_game(42)
    g.magnet_x = 160
    g.magnet_y = 120
    g.magnet_color = 0
    g.phase = Phase.PLAYING

    g.scraps = [
        Scrap(x=155, y=115, vx=0, vy=0, color=0),
        Scrap(x=160, y=115, vx=0, vy=0, color=0),
        Scrap(x=165, y=115, vx=0, vy=0, color=0),
    ]
    g._check_synthesis()
    assert len(g.scraps) == 0
    assert len(g.nuggets) == 1


# --- Test: tick logic (no pyxel) ---
def test_tick_game_timer_decrements() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLAYING
    g.game_timer = 3600
    g._tick()
    assert g.game_timer == 3599


def test_tick_game_timer_game_over() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLAYING
    g.game_timer = 1
    g._tick()
    assert g.game_timer == 0
    assert g.phase == Phase.GAME_OVER


def test_tick_super_timer_decrements() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLAYING
    g.super_timer = 10
    g._tick()
    assert g.super_timer == 9


def test_tick_spawns_scraps() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.PLAYING
    g._spawn_timer = SPAWN_INTERVAL - 1
    g._tick()
    assert len(g.scraps) >= 1


# --- Test: particles ---
def test_add_particles() -> None:
    g = _make_seeded_game(42)
    g._add_particles(100, 100, 5, 8)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.x == 100.0
        assert p.y == 100.0
        assert p.color == 8
        assert 15 <= p.life <= 25


def test_add_particles_rainbow() -> None:
    g = _make_seeded_game(42)
    g._add_particles(100, 100, 10, -1)
    assert len(g.particles) == 10


def test_update_particles() -> None:
    g = _make_seeded_game(42)
    g._add_particles(100, 100, 3, 8)
    initial_positions = [(p.x, p.y) for p in g.particles]
    g._update_particles()
    assert len(g.particles) == 3
    for p, (ix, iy) in zip(g.particles, initial_positions):
        assert p.x != ix or p.y != iy
        assert p.life >= 14


def test_update_particles_removes_expired() -> None:
    g = _make_seeded_game(42)
    g.particles.append(Particle(x=100, y=100, vx=0, vy=0, life=1, color=8))
    assert len(g.particles) == 1
    g._update_particles()
    assert len(g.particles) == 0


# --- Test: floating text ---
def test_add_floating_text() -> None:
    g = _make_seeded_game(42)
    g._add_floating_text(100, 100, "Test", 7)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.x == 100.0
    assert ft.y == 100.0
    assert ft.text == "Test"
    assert ft.color == 7
    assert ft.life == 35


def test_update_floating_texts() -> None:
    g = _make_seeded_game(42)
    g._add_floating_text(100, 100, "Test", 7)
    g._update_floating_texts()
    ft = g.floating_texts[0]
    assert ft.y < 100.0
    assert ft.life == 34


def test_update_floating_texts_removes_expired() -> None:
    g = _make_seeded_game(42)
    g.floating_texts.append(FloatingText(x=100, y=100, text="X", life=1, color=7))
    assert len(g.floating_texts) == 1
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# --- Test: helpers ---
def test_is_super_active() -> None:
    g = _make_seeded_game(42)
    assert not g._is_super_active()
    g.super_timer = 1
    assert g._is_super_active()
    g.super_timer = 0
    assert not g._is_super_active()


def test_heat_percent() -> None:
    g = _make_seeded_game(42)
    g.heat = 50
    assert abs(g._heat_percent() - 0.5) < 0.01
    g.heat = 0
    assert g._heat_percent() == 0.0
    g.heat = HEAT_MAX
    assert g._heat_percent() == 1.0


def test_magnet_col() -> None:
    g = _make_seeded_game(42)
    assert g._magnet_col() == COLORS[0]
    g.magnet_color = 2
    assert g._magnet_col() == COLORS[2]


def test_determinism() -> None:
    g1 = _make_seeded_game(42)
    g2 = _make_seeded_game(42)
    g1._spawn_scrap()
    g2._spawn_scrap()
    assert len(g1.scraps) == len(g2.scraps)
    assert g1.scraps[0].color == g2.scraps[0].color
    assert g1.scraps[0].x == g2.scraps[0].x
    assert g1.scraps[0].y == g2.scraps[0].y


def test_title_to_playing_via_reset() -> None:
    g = _make_seeded_game(42)
    assert g.phase == Phase.TITLE
    g.phase = Phase.PLAYING
    assert g.phase == Phase.PLAYING


def test_game_over_to_title_restart() -> None:
    g = _make_seeded_game(42)
    g.phase = Phase.GAME_OVER
    g.score = 5000
    g.reset()
    assert g.phase == Phase.TITLE
    assert g.score == 0


# --- Smoke: run all tests ---
if __name__ == "__main__":
    import traceback

    tests = [
        test_make_game,
        test_reset_initial_state,
        test_spawn_scrap,
        test_spawn_scrap_max_limit,
        test_cycle_color,
        test_attract_same_color,
        test_attract_different_color_no_attract,
        test_attract_super_mode_attracts_all,
        test_move_scraps_edge_bounce,
        test_move_scraps_nuggets,
        test_synthesis_three_same_color_near_magnet,
        test_synthesis_three_but_not_near_magnet,
        test_synthesis_only_two_scraps,
        test_synthesis_mixed_colors_only_same_cluster,
        test_ca_spread_changes_nearby_scraps,
        test_combo_increments_on_same_color_synthesis,
        test_combo_resets_on_different_color_synthesis,
        test_max_combo_tracks_peak,
        test_super_activates_at_combo_threshold,
        test_super_not_reactivate_during_active,
        test_heat_increases_without_synthesis,
        test_heat_reduces_on_synthesis,
        test_heat_game_over,
        test_score_on_synthesis,
        test_score_super_multiplier,
        test_synthesis_larger_cluster,
        test_synthesis_bfs_chain,
        test_tick_game_timer_decrements,
        test_tick_game_timer_game_over,
        test_tick_super_timer_decrements,
        test_tick_spawns_scraps,
        test_add_particles,
        test_add_particles_rainbow,
        test_update_particles,
        test_update_particles_removes_expired,
        test_add_floating_text,
        test_update_floating_texts,
        test_update_floating_texts_removes_expired,
        test_is_super_active,
        test_heat_percent,
        test_magnet_col,
        test_determinism,
        test_title_to_playing_via_reset,
        test_game_over_to_title_restart,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
            print(f"  OK {test_fn.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL {test_fn.__name__}: {e}")
            traceback.print_exc()

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    if failed > 0:
        sys.exit(1)
    else:
        print("All tests passed!")
