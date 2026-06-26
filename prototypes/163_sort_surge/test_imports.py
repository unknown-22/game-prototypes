"""test_imports.py — Headless logic tests for Sort Surge."""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # type: ignore[import-not-found]
    BASE_SCORE,
    COMBO_SURGE_THRESHOLD,
    MAX_PACKAGES,
    OVERFLOW_DECAY,
    OVERFLOW_MAX,
    OVERFLOW_MISS,
    OVERFLOW_WRONG_SORT,
    PACKAGE_COLORS,
    PACKAGE_SPEED_INITIAL,
    PACKAGE_SPEED_MAX,
    RED,
    SPAWN_INTERVAL_INITIAL,
    SPAWN_INTERVAL_MIN,
    SURGE_DURATION,
    SURGE_SCORE_MULT,
    FloatingText,
    Game,
    Package,
    Particle,
    Phase,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    # Pre-init all attributes that reset() touches
    g.packages = []
    g.particles = []
    g.floating_texts = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.overflow = 0.0
    g.surge_timer = 0.0
    g.phase = Phase.TITLE
    g.spawn_timer = 0.0
    g.game_timer = 0.0
    g._last_sort_color = None
    g._auto_sort_timer = 0.0
    g._selected_bin_color = RED
    g.reset()
    return g


# ── Initialization ──


def test_game_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.overflow == 0.0
    assert g.surge_timer == 0.0
    assert g._last_sort_color is None
    assert g._auto_sort_timer == 0.0
    assert g._selected_bin_color == 8  # RED
    assert g.packages == []
    assert g.particles == []
    assert g.floating_texts == []


def test_start_game_transitions_to_playing() -> None:
    g = _make_game()
    g.start_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0


# ── Package Spawning ──


def test_package_spawns_with_valid_color() -> None:
    g = _make_game()
    g.start_game()
    g._spawn_package()
    assert len(g.packages) == 1
    pkg = g.packages[0]
    assert pkg.color in PACKAGE_COLORS
    assert pkg.sorted is False
    assert pkg.speed == PACKAGE_SPEED_INITIAL


def test_spawn_respects_max_packages() -> None:
    g = _make_game()
    g.start_game()
    for _ in range(MAX_PACKAGES + 5):
        g._spawn_package()
    assert len(g.packages) == MAX_PACKAGES


def test_multiple_packages_can_be_on_screen() -> None:
    g = _make_game()
    g.start_game()
    for _ in range(5):
        g._spawn_package()
    assert len(g.packages) == 5
    # Verify they're on different lanes or have different colors
    colors = {p.color for p in g.packages}
    assert len(colors) >= 1


# ── Package Movement ──


def test_package_moves_over_time() -> None:
    g = _make_game()
    g.start_game()
    g._spawn_package()
    pkg = g.packages[0]
    init_x = pkg.x
    g._update_packages()
    assert g.packages[0].x < init_x


def test_package_reaching_end_increases_overflow() -> None:
    g = _make_game()
    g.start_game()
    g.packages = [Package(x=5.0, y=30.0, color=8, speed=1.0)]
    g.overflow = 0.0
    g._update_packages()
    assert g.overflow == OVERFLOW_MISS
    assert len(g.packages) == 0  # removed


def test_package_not_at_end_stays() -> None:
    g = _make_game()
    g.start_game()
    g.packages = [Package(x=100.0, y=30.0, color=8, speed=1.0)]
    g._update_packages()
    assert len(g.packages) == 1
    assert g.packages[0].x == 99.0


# ── Sorting ──


def test_sort_correct_color_increments_combo() -> None:
    g = _make_game()
    g.start_game()
    g._selected_bin_color = 8  # RED
    g.packages = [Package(x=100.0, y=30.0, color=8, speed=1.0)]
    g._last_sort_color = None
    g.combo = 0
    result = g._sort_package(0)
    assert result is True
    assert g.combo == 1
    assert g.packages[0].sorted is True


def test_sort_correct_color_extends_combo() -> None:
    g = _make_game()
    g.start_game()
    g._selected_bin_color = 8
    g._last_sort_color = 8
    g.combo = 3
    g.packages = [Package(x=100.0, y=30.0, color=8, speed=1.0)]
    result = g._sort_package(0)
    assert result is True
    assert g.combo == 4


def test_sort_different_correct_color_starts_new_combo() -> None:
    g = _make_game()
    g.start_game()
    g._selected_bin_color = 10  # YELLOW
    g._last_sort_color = 8  # previously sorted RED
    g.combo = 3
    g.packages = [Package(x=100.0, y=30.0, color=10, speed=1.0)]
    result = g._sort_package(0)
    assert result is True
    assert g.combo == 1  # new combo starts
    assert g._last_sort_color == 10


def test_sort_wrong_color_resets_combo() -> None:
    g = _make_game()
    g.start_game()
    g._selected_bin_color = 8  # RED
    g._last_sort_color = 8
    g.combo = 4
    g.overflow = 0.0
    g.packages = [Package(x=100.0, y=30.0, color=3, speed=1.0)]  # GREEN
    result = g._sort_package(0)
    assert result is False
    assert g.combo == 0
    assert g._last_sort_color is None
    assert g.overflow == OVERFLOW_WRONG_SORT


def test_sort_wrong_color_increases_overflow() -> None:
    g = _make_game()
    g.start_game()
    g._selected_bin_color = 8
    g.overflow = 30.0
    g.packages = [Package(x=100.0, y=30.0, color=3, speed=1.0)]
    g._sort_package(0)
    assert g.overflow == 30.0 + OVERFLOW_WRONG_SORT


def test_sort_invalid_index_returns_false() -> None:
    g = _make_game()
    g.start_game()
    assert g._sort_package(-1) is False
    assert g._sort_package(0) is False  # empty list
    assert g._sort_package(999) is False


def test_sort_already_sorted_returns_false() -> None:
    g = _make_game()
    g.start_game()
    g.packages = [Package(x=100.0, y=30.0, color=8, sorted=True, speed=1.0)]
    assert g._sort_package(0) is False


# ── Score Calculation ──


def test_score_calculation_with_combo() -> None:
    g = _make_game()
    g.start_game()
    g._selected_bin_color = 8
    g.combo = 3
    g._last_sort_color = 8
    g.packages = [Package(x=100.0, y=30.0, color=8, speed=1.0)]
    g._sort_package(0)
    # combo 3→4, score += 10 * 4 = 40
    assert g.score == 40


def test_score_first_sort() -> None:
    g = _make_game()
    g.start_game()
    g._selected_bin_color = 8
    g._last_sort_color = None
    g.packages = [Package(x=100.0, y=30.0, color=8, speed=1.0)]
    g._sort_package(0)
    assert g.score == BASE_SCORE  # combo=1, 10*1=10


def test_max_combo_tracked() -> None:
    g = _make_game()
    g.start_game()
    g._selected_bin_color = 8
    g._last_sort_color = 8
    g.combo = 4
    g.max_combo = 4
    g.packages = [Package(x=100.0, y=30.0, color=8, speed=1.0)]
    g._sort_package(0)
    assert g.combo == 5
    assert g.max_combo == 5


def test_max_combo_persists_after_reset() -> None:
    g = _make_game()
    g.start_game()
    g._selected_bin_color = 8  # RED
    g._last_sort_color = 8
    g.combo = 4
    g.max_combo = 4
    g.packages = [Package(x=100.0, y=30.0, color=8, speed=1.0)]
    g._sort_package(0)  # combo→5, SURGE activates
    # Deactivate SURGE so second sort is not auto-matched
    g.surge_timer = 0.0
    g.packages = [Package(x=100.0, y=30.0, color=3, speed=1.0)]  # wrong color
    g._sort_package(0)
    assert g.combo == 0
    assert g.max_combo == 5  # persists


# ── SURGE Mode ──


def test_combo_5_activates_surge() -> None:
    g = _make_game()
    g.start_game()
    g._selected_bin_color = 8
    g._last_sort_color = 8
    g.combo = 4
    g.packages = [Package(x=100.0, y=30.0, color=8, speed=1.0)]
    g._sort_package(0)
    assert g.combo == COMBO_SURGE_THRESHOLD
    assert g.surge_timer == SURGE_DURATION


def test_surge_timer_counts_down() -> None:
    g = _make_game()
    g.start_game()
    g.surge_timer = 2.0
    g._update_surge(1.0 / 30.0)
    assert g.surge_timer < 2.0
    assert g.surge_timer > 1.9


def test_surge_auto_sorts_packages() -> None:
    g = _make_game()
    g.start_game()
    g.combo = 3
    g._last_sort_color = 8
    g.surge_timer = 3.0
    g._auto_sort_timer = 0.0
    g.packages = [Package(x=100.0, y=30.0, color=3, speed=1.0)]
    g._update_surge(1.0 / 30.0)
    # After update, auto_sort_timer becomes negative (decremented by dt)
    # On next call when auto_sort_timer <= 0, it auto-sorts
    g._auto_sort_timer = -0.1  # force auto-sort
    g._update_surge(1.0 / 30.0)
    assert g.packages[0].sorted is True
    assert g.combo == 4
    assert g.score > 0


def test_surge_sort_uses_3x_multiplier() -> None:
    g = _make_game()
    g.start_game()
    g._selected_bin_color = 8
    g.combo = 2
    g.surge_timer = 2.0
    g.packages = [Package(x=100.0, y=30.0, color=3, speed=1.0)]  # any color works in surge
    g._sort_package(0)
    # combo 2→3, score = 10 * 3 * 3 = 90
    assert g.score == BASE_SCORE * 3 * SURGE_SCORE_MULT


def test_surge_any_color_matches() -> None:
    g = _make_game()
    g.start_game()
    g._selected_bin_color = 8  # RED
    g.surge_timer = 2.0
    g.combo = 1
    g.packages = [Package(x=100.0, y=30.0, color=3, speed=1.0)]  # GREEN
    result = g._sort_package(0)
    # In surge, any color matches
    assert result is True
    assert g.combo == 2


def test_surge_ends_after_duration() -> None:
    g = _make_game()
    g.start_game()
    g.surge_timer = 0.01
    g._update_surge(1.0 / 30.0)
    assert g.surge_timer == 0.0


# ── Overflow ──


def test_overflow_decays_over_time() -> None:
    g = _make_game()
    g.start_game()
    g.overflow = 50.0
    g.update(1.0 / 30.0)
    assert g.overflow < 50.0


def test_overflow_does_not_go_negative() -> None:
    g = _make_game()
    g.start_game()
    g.overflow = OVERFLOW_DECAY / 2
    g.update(1.0 / 30.0)
    assert g.overflow == 0.0


def test_overflow_at_100_triggers_game_over() -> None:
    g = _make_game()
    g.start_game()
    g.overflow = OVERFLOW_MAX
    g.update(1.0 / 30.0)
    assert g.phase == Phase.GAME_OVER


def test_overflow_capped_at_max() -> None:
    g = _make_game()
    g.start_game()
    g.overflow = 90.0
    g.packages = [Package(x=5.0, y=30.0, color=8, speed=1.0)]
    g._update_packages()
    assert g.overflow == OVERFLOW_MAX  # 90 + 30 → capped at 100


# ── Difficulty Scaling ──


def test_difficulty_spawn_interval_decreases() -> None:
    g = _make_game()
    g.start_game()
    g.game_timer = 0.0
    si1, _ = g._difficulty_params()
    g.game_timer = 100.0
    si2, _ = g._difficulty_params()
    assert si2 < si1


def test_difficulty_spawn_interval_has_minimum() -> None:
    g = _make_game()
    g.start_game()
    g.game_timer = 10000.0
    si, _ = g._difficulty_params()
    assert si == SPAWN_INTERVAL_MIN


def test_difficulty_speed_increases() -> None:
    g = _make_game()
    g.start_game()
    g.game_timer = 0.0
    _, sp1 = g._difficulty_params()
    g.game_timer = 100.0
    _, sp2 = g._difficulty_params()
    assert sp2 > sp1


def test_difficulty_speed_has_maximum() -> None:
    g = _make_game()
    g.start_game()
    g.game_timer = 10000.0
    _, sp = g._difficulty_params()
    assert sp == PACKAGE_SPEED_MAX


def test_difficulty_initial_values() -> None:
    g = _make_game()
    g.start_game()
    si, sp = g._difficulty_params()
    assert si == SPAWN_INTERVAL_INITIAL
    assert sp == PACKAGE_SPEED_INITIAL


# ── Particles ──


def test_spawn_particles_creates_correct_count() -> None:
    g = _make_game()
    g.start_game()
    g._spawn_particles(100.0, 100.0, 8, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color == 8


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    g.start_game()
    g.particles = [
        Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, color=8, life=1),
        Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, color=8, life=0),
    ]
    g._update_particles()
    assert len(g.particles) == 0  # both removed: life=1 becomes 0, life=0 is already dead


def test_update_particles_keeps_alive() -> None:
    g = _make_game()
    g.start_game()
    g.particles = [
        Particle(x=0.0, y=0.0, vx=1.0, vy=-1.0, color=8, life=3),
    ]
    g._update_particles()
    assert len(g.particles) == 1
    p = g.particles[0]
    assert p.x == 1.0
    assert p.y == -1.0  # position update: 0 + (-1.0)
    assert abs(p.vy - (-0.95)) < 0.001  # gravity applied after: -1.0 + 0.05
    assert p.life == 2


# ── Floating Texts ──


def test_add_floating_text() -> None:
    g = _make_game()
    g.start_game()
    g._add_floating_text("TEST", 100.0, 50.0, 7)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "TEST"
    assert g.floating_texts[0].color == 7


def test_update_floating_texts() -> None:
    g = _make_game()
    g.start_game()
    g.floating_texts = [
        FloatingText(text="A", x=0.0, y=0.0, color=7, life=1),
        FloatingText(text="B", x=0.0, y=0.0, color=7, life=3),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.text == "B"
    assert ft.life == 2


# ── Reset ──


def test_reset_clears_all_state() -> None:
    g = _make_game()
    g.start_game()
    g.score = 500
    g.combo = 5
    g.max_combo = 7
    g.overflow = 80.0
    g.surge_timer = 3.0
    g._last_sort_color = 8
    g._auto_sort_timer = 1.0
    g._selected_bin_color = 3
    g.packages = [Package(x=100.0, y=30.0, color=8, speed=1.0)]
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, color=8, life=5)]
    g.floating_texts = [FloatingText(text="X", x=0.0, y=0.0, color=7, life=5)]
    g.game_timer = 30.0
    g.spawn_timer = 5.0

    g.reset()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.overflow == 0.0
    assert g.surge_timer == 0.0
    assert g._last_sort_color is None
    assert g._auto_sort_timer == 0.0
    assert g._selected_bin_color == 8  # RED
    assert g.packages == []
    assert g.particles == []
    assert g.floating_texts == []
    assert g.game_timer == 0.0
    assert g.spawn_timer == 0.0


# ── Select Bin ──


def test_select_bin_valid() -> None:
    g = _make_game()
    g.start_game()
    g.select_bin(2)  # DARK_BLUE
    assert g._selected_bin_color == PACKAGE_COLORS[2]


def test_select_bin_invalid_ignored() -> None:
    g = _make_game()
    g.start_game()
    original = g._selected_bin_color
    g.select_bin(-1)
    assert g._selected_bin_color == original
    g.select_bin(5)
    assert g._selected_bin_color == original


# ── Click Bin (coordinate-based) ──


def test_click_bin_returns_correct_index() -> None:
    from main import BINS_X_START, BIN_Y

    g = _make_game()
    g.start_game()
    # Click roughly on the first bin
    bx = BINS_X_START + 10
    by = BIN_Y + 10
    idx = g.click_bin(float(bx), float(by))
    assert idx == 0
    assert g._selected_bin_color == PACKAGE_COLORS[0]


def test_click_bin_out_of_bounds() -> None:
    g = _make_game()
    g.start_game()
    assert g.click_bin(-10.0, 100.0) == -1
    assert g.click_bin(500.0, 100.0) == -1
    assert g.click_bin(100.0, -10.0) == -1
    assert g.click_bin(100.0, 300.0) == -1


# ── Click Package (coordinate-based) ──


def test_click_package_success() -> None:
    g = _make_game()
    g.start_game()
    g._selected_bin_color = 8  # RED
    g.packages = [Package(x=100.0, y=30.0, color=8, speed=1.0)]
    assert g.click_package(100.0, 30.0) is True
    assert g.packages[0].sorted is True


def test_click_package_miss_click() -> None:
    g = _make_game()
    g.start_game()
    g.packages = [Package(x=100.0, y=30.0, color=8, speed=1.0)]
    # Click far from package
    assert g.click_package(200.0, 200.0) is False


def test_click_package_closest_selected() -> None:
    g = _make_game()
    g.start_game()
    g._selected_bin_color = 8  # RED
    g.packages = [
        Package(x=50.0, y=30.0, color=3, speed=1.0),  # GREEN (wrong color)
        Package(x=54.0, y=30.0, color=8, speed=1.0),  # RED (correct color)
    ]
    # Click near pkg1 (RED) — within PACKAGE_R + 4 radius
    result = g.click_package(54.0, 30.0)
    assert result is True
    assert g.packages[1].sorted is True


# ── Surge Activation via Combo ──


def test_surge_activation_spawns_particles() -> None:
    g = _make_game()
    g.start_game()
    g.combo = 4
    g._last_sort_color = 8
    g._selected_bin_color = 8
    g.packages = [Package(x=100.0, y=30.0, color=8, speed=1.0)]
    g._sort_package(0)
    assert g.surge_timer == SURGE_DURATION
    assert len(g.particles) > 0  # SURGE particles + sort particles


# ── DataClass Fields ──


def test_package_fields() -> None:
    p = Package(x=50.0, y=30.0, color=8, speed=0.5)
    assert p.x == 50.0
    assert p.y == 30.0
    assert p.color == 8
    assert p.sorted is False
    assert p.speed == 0.5


def test_particle_fields() -> None:
    p = Particle(x=1.0, y=2.0, vx=0.5, vy=-0.3, color=7, life=15)
    assert p.x == 1.0
    assert p.life == 15
    assert p.color == 7


def test_floating_text_fields() -> None:
    ft = FloatingText(text="+10", x=100.0, y=50.0, color=7, life=30)
    assert ft.text == "+10"
    assert ft.life == 30


# ── Phase Transitions ──


def test_phase_enum_values() -> None:
    assert Phase.TITLE is not Phase.PLAYING
    assert Phase.PLAYING is not Phase.GAME_OVER
    assert Phase.GAME_OVER is not Phase.TITLE


# ── Run ──

if __name__ == "__main__":
    import inspect as _inspect

    _tests = [
        obj
        for _name, obj in _inspect.getmembers(sys.modules[__name__])
        if callable(obj) and _name.startswith("test_")
    ]
    passed = 0
    failed = 0
    for _test in _tests:
        try:
            _test()
            print(f"  PASS {_test.__name__}")
            passed += 1
        except Exception as _e:
            print(f"  FAIL {_test.__name__}: {_e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {len(_tests)} total")
    if failed > 0:
        sys.exit(1)
