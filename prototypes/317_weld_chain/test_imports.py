"""test_imports.py — Headless logic tests for 317_weld_chain.

Run:  uv run python prototypes/317_weld_chain/test_imports.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # noqa: E402
    COLORS,
    GAME_TIME,
    HEAT_MAX,
    RED,
    LIME,
    DARK_BLUE,
    YELLOW,
    SEGS_MAX,
    SEG_W,
    SEG_H,
    SEG_X_START,
    SEAM_ROWS,
    FloatingText,
    Game,
    Particle,
    Phase,
    Segment,
    Seam,
)


def make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.reset(seed=seed)
    return g


def test_reset_initial_state() -> None:
    g = make_game()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == GAME_TIME == 3600
    assert g.frame == 0
    assert g.torch_index == 0
    assert g.super_timer == 0
    assert g.phase == Phase.TITLE
    assert len(g.seams) == 4
    assert all(seam.length == 4 for seam in g.seams)
    assert all(seam.color in COLORS for seam in g.seams)


def test_reset_seed_determinism() -> None:
    g1 = make_game(42)
    g2 = make_game(42)
    assert [s.color for s in g1.seams] == [s.color for s in g2.seams]
    g3 = make_game(7)
    assert [s.color for s in g3.seams] != [s.color for s in g1.seams]


def test_spawn_seam_fixed() -> None:
    g = make_game()
    n = len(g.seams)
    seam = g._spawn_seam(4, color=0, length=5)
    assert seam.color == RED
    assert seam.length == 5
    assert seam.y == SEAM_ROWS[4]
    assert len(g.seams) == n + 1


def test_spawn_seam_caps_length() -> None:
    g = make_game()
    seam = g._spawn_seam(4, color=2, length=99)
    assert seam.length == SEGS_MAX
    assert seam.color == DARK_BLUE  # COLORS[2]


def test_seam_properties() -> None:
    seam = Seam(
        y=40,
        segments=[Segment(color=RED, welded=True), Segment(color=RED, welded=False)],
    )
    assert seam.complete is False
    assert seam.active_index == 1
    assert seam.length == 2
    assert seam.color == RED

    done = Seam(y=40, segments=[Segment(color=LIME, welded=True)])
    assert done.complete is True
    assert done.active_index is None


def test_cycle_interval_escalation() -> None:
    g = make_game()
    g.frame = 0
    assert g._cycle_interval() == 20
    g.frame = 3600
    assert g._cycle_interval() == 12


def test_crack_interval_escalation() -> None:
    g = make_game()
    g.frame = 0
    assert g._crack_interval() == 240
    g.frame = 3600
    assert g._crack_interval() == 100


def test_update_torch_cycles() -> None:
    g = make_game()
    g.torch_timer = 0
    initial = g.torch_index
    g._update_torch()
    assert g.torch_index == (initial + 1) % 4
    assert g.torch_timer == g._cycle_interval()


def test_update_torch_full_cycle_returns_to_start() -> None:
    g = make_game()
    start = g.torch_index
    for _ in range(4):
        g.torch_timer = 0
        g._update_torch()
    assert g.torch_index == start


def test_update_cracks_grows_incomplete() -> None:
    g = make_game()
    g.crack_timer = 0
    grown = g._update_cracks()
    assert grown == 4
    assert all(seam.length == 5 for seam in g.seams)


def test_update_cracks_skips_complete_seams() -> None:
    g = make_game()
    for seg in g.seams[0].segments:
        seg.welded = True
    g.crack_timer = 0
    grown = g._update_cracks()
    assert grown == 3
    assert g.seams[0].length == 4  # complete seam unchanged
    assert g.seams[1].length == 5  # incomplete grew


def test_update_cracks_caps_at_max() -> None:
    g = make_game()
    for seam in g.seams:
        seam.segments = [Segment(color=seam.color, welded=False) for _ in range(SEGS_MAX)]
    g.crack_timer = 0
    grown = g._update_cracks()
    assert grown == 0
    assert all(seam.length == SEGS_MAX for seam in g.seams)


def test_weld_match() -> None:
    g = make_game()
    seam = g.seams[0]
    seg_color = seam.segments[0].color
    g.torch_index = COLORS.index(seg_color)
    result = g._weld_seam(seam)
    assert result == "match"
    assert seam.segments[0].welded is True
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score == 10


def test_weld_match_combo_scoring() -> None:
    g = make_game()
    seam = g.seams[0]
    g.torch_index = COLORS.index(seam.segments[0].color)
    g.combo = 3
    g._weld_seam(seam)
    assert g.combo == 4
    assert g.score == 40  # 10 * 4


def test_weld_mismatch() -> None:
    g = make_game()
    seam = g.seams[0]
    seg_color = seam.segments[0].color
    g.torch_index = (COLORS.index(seg_color) + 1) % 4
    g.combo = 3
    result = g._weld_seam(seam)
    assert result == "mismatch"
    assert seam.segments[0].welded is False  # stays
    assert g.combo == 0
    assert g.heat == 15.0
    assert g.score == 0


def test_weld_mismatch_game_over_at_heat_cap() -> None:
    g = make_game()
    seam = g.seams[0]
    seg_color = seam.segments[0].color
    g.torch_index = (COLORS.index(seg_color) + 1) % 4
    g.heat = 90.0
    g._weld_seam(seam)
    assert g.heat == 105.0
    assert g.phase == Phase.GAME_OVER


def test_weld_complete_removes_and_respawns() -> None:
    g = make_game()
    seam = g.seams[0]
    orig_y = seam.y
    g.torch_index = COLORS.index(seam.segments[0].color)
    for _ in range(3):
        assert g._weld_seam(seam) == "match"
    assert seam.complete is False
    assert g.combo == 3
    assert g.score == 60  # 10 + 20 + 30
    result = g._weld_seam(seam)  # final segment
    assert result == "complete"
    assert g.combo == 4
    assert g.score == 300  # 60 + 40 (segment) + 200 (bonus)
    assert seam not in g.seams
    assert any(s.y == orig_y for s in g.seams)


def test_weld_complete_on_complete_seam() -> None:
    g = make_game()
    seam = g.seams[0]
    for seg in seam.segments:
        seg.welded = True
    assert g._weld_seam(seam) == "none"


def test_super_mode_any_color_match_and_3x() -> None:
    g = make_game()
    seam = g.seams[0]
    seg_color = seam.segments[0].color
    g.torch_index = (COLORS.index(seg_color) + 1) % 4  # would mismatch
    g.super_timer = 300
    g.combo = 4
    result = g._weld_seam(seam)
    assert result == "match"
    assert seam.segments[0].welded is True
    assert g.combo == 5
    assert g.score == 150  # 10 * 5 * 3


def test_update_heat_game_over_before_decay() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.heat = HEAT_MAX
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.heat == HEAT_MAX  # no decay happened


def test_update_heat_decay() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.heat = 10.0
    g._update_heat()
    assert abs(g.heat - 9.98) < 0.01
    assert g.phase == Phase.PLAYING


def test_update_heat_frozen_in_super() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.heat = 50.0
    g.super_timer = 100
    g._update_heat()
    assert g.heat == 50.0


def test_update_timer_game_over() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.timer = 1
    g._update_timer()
    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER


def test_update_timer_super_decrement() -> None:
    g = make_game()
    g.phase = Phase.PLAYING
    g.super_timer = 5
    g.timer = 100
    g._update_timer()
    assert g.super_timer == 4
    assert g.timer == 99


def test_seam_at_hit_test() -> None:
    g = make_game()
    seam = g.seams[0]
    idx = seam.active_index
    assert idx == 0
    sx = SEG_X_START + idx * SEG_W
    sy = seam.y
    assert g._seam_at(sx, sy) is seam
    assert g._seam_at(sx + SEG_W - 1, sy + SEG_H - 1) is seam
    assert g._seam_at(sx - 1, sy) is None
    assert g._seam_at(sx, sy + SEG_H) is None


def test_seam_at_skips_complete_seam() -> None:
    g = make_game()
    seam = g.seams[0]
    for seg in seam.segments:
        seg.welded = True
    idx = None  # active_index is None
    sx = SEG_X_START
    sy = seam.y
    assert g._seam_at(sx, sy) is not seam
    assert idx is None


def test_max_combo_tracking() -> None:
    g = make_game()
    seam = g.seams[0]
    g.torch_index = COLORS.index(seam.segments[0].color)
    for _ in range(4):
        g._weld_seam(seam)
    assert g.max_combo == 4


def test_particle_lifecycle() -> None:
    g = make_game()
    g.particles = [Particle(x=10.0, y=10.0, vx=1.0, vy=1.0, life=1, color=RED)]
    g._update_particles()
    assert len(g.particles) == 0


def test_floating_text_lifecycle() -> None:
    g = make_game()
    g.floats = [FloatingText(x=10.0, y=10.0, text="x", life=1, color=RED)]
    g._update_floats()
    assert len(g.floats) == 0


def test_spawn_particles_and_texts() -> None:
    g = make_game()
    g._spawn_particles(100, 100, 8, RED)
    assert len(g.particles) == 8
    g._spawn_float_text(100, 100, "SEAM COMPLETE!", YELLOW)
    assert len(g.floats) == 1
    assert g.floats[0].text == "SEAM COMPLETE!"


def main() -> None:
    tests = [
        v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)
    ]
    passed = 0
    for fn in tests:
        fn()
        passed += 1
        print(f"  PASS {fn.__name__}")
    print(f"\n{passed}/{len(tests)} tests passed")


if __name__ == "__main__":
    main()
