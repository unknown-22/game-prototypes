"""test_imports.py — Headless logic tests for KITE CHAIN (304)."""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # noqa: E402
    DARK_BLUE,
    KITE_COLORS,
    LIME,
    RED,
    WHITE,
    YELLOW,
    SCREEN_H,
    SCREEN_W,
    FloatingText,
    Game,
    Gust,
    Phase,
    TrailPoint,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.reset()
    g.rng = random.Random(seed)
    return g


def _start_clean(seed: int = 42) -> Game:
    g = _make_game(seed)
    g.start_playing()
    g.rng = random.Random(seed)
    g.gusts = []
    g.particles = []
    g.floating_texts = []
    return g


def _match_n(g: Game, n: int, color: int | None = None) -> int:
    """Perform n matching resolves; returns total score gained."""
    total = 0
    for _ in range(n):
        c = color if color is not None else g.kite_color()
        total += g.resolve_collision(Gust(0.0, 0.0, c, -1.0, 16))
    return total


def test_colors_defined() -> None:
    assert len(KITE_COLORS) == 4
    assert set(KITE_COLORS) == {RED, LIME, DARK_BLUE, YELLOW}


def test_reset_initial_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.kite_x == g.KITE_START_X
    assert g.kite_y == g.KITE_START_Y
    assert g.timer == g.GAME_DURATION
    assert g.gusts == []


def test_start_playing() -> None:
    g = _make_game()
    g.start_playing()
    assert g.phase == Phase.PLAYING
    assert len(g.gusts) == g.INITIAL_GUSTS
    assert g.timer == g.GAME_DURATION
    assert g.kite_color_idx == 0


def test_kite_color_cycling() -> None:
    g = _make_game()
    assert g.kite_color() == RED
    g.advance_color()
    assert g.kite_color() == LIME
    for _ in range(3):
        g.advance_color()
    assert g.kite_color() == RED  # wrapped around


def test_move_kite_cardinal() -> None:
    g = _make_game()
    g.start_playing()
    g.kite_x = 100.0
    g.kite_y = 100.0
    g.move_kite(1, 0)
    assert g.kite_x == 100.0 + g.KITE_SPEED
    assert g.kite_y == 100.0
    g.move_kite(0, -1)
    assert g.kite_y == 100.0 - g.KITE_SPEED


def test_move_kite_diagonal_normalized() -> None:
    g = _make_game()
    g.start_playing()
    g.kite_x = 100.0
    g.kite_y = 100.0
    g.move_kite(1, 1)
    expected = g.KITE_SPEED / math.sqrt(2)
    assert abs(g.kite_x - (100.0 + expected)) < 0.001
    assert abs(g.kite_y - (100.0 + expected)) < 0.001


def test_move_kite_clamp() -> None:
    g = _make_game()
    g.start_playing()
    g.kite_x = 0.0
    g.move_kite(-1, 0)
    assert g.kite_x == 0.0
    g.kite_x = float(SCREEN_W)
    g.move_kite(1, 0)
    assert g.kite_x == float(SCREEN_W)
    g.kite_y = float(SCREEN_H)
    g.move_kite(0, 1)
    assert g.kite_y == float(SCREEN_H)


def test_resolve_collision_match_builds_combo() -> None:
    g = _start_clean()
    gained = g.resolve_collision(Gust(0.0, 0.0, RED, -1.0, 16))
    assert gained == 10
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score == 10
    assert g.heat == 0.0


def test_resolve_collision_consecutive_matches() -> None:
    g = _start_clean()
    total = _match_n(g, 3)
    assert total == 10 + 20 + 30
    assert g.combo == 3
    assert g.score == 60
    assert g.super_timer == 0  # below threshold


def test_resolve_collision_super_activation() -> None:
    g = _start_clean()
    _match_n(g, 3)
    assert g.super_timer == 0
    gained = g.resolve_collision(Gust(0.0, 0.0, RED, -1.0, 16))
    assert gained == 40
    assert g.combo == 4
    assert g.super_timer == g.SUPER_DURATION


def test_resolve_collision_mismatch() -> None:
    g = _start_clean()
    _match_n(g, 2)  # combo = 2, score = 30
    gained = g.resolve_collision(Gust(0.0, 0.0, LIME, -1.0, 16))
    assert gained == 0
    assert g.combo == 0
    assert g.heat == g.HEAT_MISMATCH
    assert g.score == 30  # unchanged
    assert g.shake_frames == 8


def test_resolve_collision_super_any_color() -> None:
    g = _start_clean()
    _match_n(g, 4)  # combo = 4, super activated, score = 100
    assert g.super_timer == g.SUPER_DURATION
    heat_before = g.heat
    gained = g.resolve_collision(Gust(0.0, 0.0, LIME, -1.0, 16))  # wrong color
    assert gained == 10 * 5 * g.SUPER_MULT  # 150
    assert g.combo == 5
    assert g.heat == heat_before  # HEAT frozen in SUPER


def test_update_super_decrements() -> None:
    g = _start_clean()
    g.super_timer = 300
    g.update_super()
    assert g.super_timer == 299
    g.super_timer = 0
    g.update_super()
    assert g.super_timer == 0


def test_update_heat_game_over() -> None:
    g = _start_clean()
    g.heat = g.HEAT_MAX
    g.update_heat()
    assert g.phase == Phase.GAME_OVER


def test_update_heat_decay() -> None:
    g = _start_clean()
    g.heat = 50.0
    g.update_heat()
    assert abs(g.heat - (50.0 - g.HEAT_DECAY)) < 0.001


def test_update_timer_game_over() -> None:
    g = _start_clean()
    g.timer = 1
    g.update_timer()
    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER


def test_update_difficulty_escalation() -> None:
    g = _make_game()
    g.elapsed = 0
    g.update_difficulty()
    assert g.max_gusts == g.MAX_GUSTS_START
    assert abs(g.gust_speed - g.GUST_SPEED_START) < 0.001
    g.elapsed = g.GAME_DURATION
    g.update_difficulty()
    assert g.max_gusts == g.MAX_GUSTS_END
    assert abs(g.gust_speed - g.GUST_SPEED_END) < 0.001


def test_spawn_gust_respects_cap() -> None:
    g = _start_clean()
    g.max_gusts = 3
    g.gusts = [Gust(10.0, 10.0, RED, -1.0, 16) for _ in range(3)]
    g.spawn_gust()
    assert len(g.gusts) == 3


def test_spawn_gust_adds_when_below_cap() -> None:
    g = _start_clean()
    g.max_gusts = 5
    g.gusts = []
    g.spawn_gust()
    assert len(g.gusts) == 1
    assert g.gusts[0].x == SCREEN_W + 10.0
    assert g.gusts[0].vx < 0


def test_collide_gusts_removes_and_resolves() -> None:
    g = _start_clean()
    g.kite_x = 100.0
    g.kite_y = 100.0
    g.gusts = [Gust(100.0, 100.0, RED, -1.0, 16)]
    g.collide_gusts()
    assert len(g.gusts) == 0
    assert g.combo == 1
    assert g.score == 10


def test_collide_gusts_no_hit_when_far() -> None:
    g = _start_clean()
    g.kite_x = 100.0
    g.kite_y = 100.0
    g.gusts = [Gust(300.0, 200.0, RED, -1.0, 16)]
    g.collide_gusts()
    assert len(g.gusts) == 1
    assert g.combo == 0


def test_update_gusts_removes_offscreen() -> None:
    g = _start_clean()
    g.gusts = [Gust(-15.0, 100.0, RED, -10.0, 16), Gust(100.0, 100.0, LIME, -1.0, 16)]
    g.update_gusts()
    assert len(g.gusts) == 1
    assert g.gusts[0].color == LIME


def test_update_trail_appends_every_3_frames() -> None:
    g = _start_clean()
    g.kite_x = 50.0
    g.kite_y = 50.0
    g.trail = []
    g.trail_tick = g.TRAIL_INTERVAL
    for _ in range(g.TRAIL_INTERVAL):
        g.update_trail()
    assert len(g.trail) == 1
    assert g.trail[0].x == 50.0
    assert g.trail[0].color == RED


def test_update_trail_removes_expired() -> None:
    g = _start_clean()
    g.trail = [TrailPoint(10.0, 10.0, 1, RED)]
    g.trail_tick = 10  # not yet time to append
    g.update_trail()
    assert len(g.trail) == 0


def test_floating_text_lifecycle() -> None:
    g = _start_clean()
    g.floating_texts = [FloatingText(10.0, 10.0, "HI", 2, WHITE)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1  # life 2 -> 1 survives
    g._update_floating_texts()
    assert len(g.floating_texts) == 0  # life 1 -> 0 removed


def test_max_combo_tracks_peak() -> None:
    g = _start_clean()
    _match_n(g, 3)  # combo = 3, below SUPER threshold (no super mode)
    assert g.max_combo == 3
    g.resolve_collision(Gust(0.0, 0.0, LIME, -1.0, 16))  # mismatch resets combo
    assert g.combo == 0
    assert g.max_combo == 3  # peak preserved


def test_particle_spawn_counts() -> None:
    g = _start_clean()
    g.resolve_collision(Gust(0.0, 0.0, RED, -1.0, 16))
    assert len(g.particles) == 8  # match
    g.particles = []
    g.resolve_collision(Gust(0.0, 0.0, LIME, -1.0, 16))
    assert len(g.particles) == 4  # mismatch


if __name__ == "__main__":
    tests = [
        v
        for k, v in sorted(globals().items())
        if k.startswith("test_") and callable(v)
    ]
    failures = 0
    for t in tests:
        try:
            t()
            print("PASS", t.__name__)
        except Exception as e:  # noqa: BLE001
            failures += 1
            print("FAIL", t.__name__, "->", repr(e))
    print(f"\n{tests and len(tests)} tests, {failures} failures")
    sys.exit(1 if failures else 0)
