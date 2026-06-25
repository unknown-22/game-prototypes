"""test_imports.py — Headless logic tests for Hanoi Surge."""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (  # type: ignore[import-not-found]
    ANIM_DURATION,
    DISK_COLORS,
    DISK_COUNT,
    GAME_TIME,
    HEAT_DECAY,
    HEAT_INVALID,
    MAX_HEAT,
    OPTIMAL_MOVES,
    PEG_X,
    SCREEN_H,
    SCREEN_W,
    SUPER_THRESHOLD,
    Disk,
    FloatingText,
    Game,
    Particle,
    Phase,
    _generate_optimal_path,
)


def _make_game(seed: int = 42) -> Game:
    """Create a Game with deterministic RNG."""
    g = Game()
    g.rng = random.Random(seed)
    g._init_state()
    return g


def _make_simple_game(seed: int = 42) -> Game:
    """Create a game with a predictable disk layout: all RED disks of sizes 1-3."""
    g = Game()
    g.rng = random.Random(seed)
    g._init_state()
    # Override with simple setup: 3 disks, all same color
    g.pegs = [[], [], []]
    for size in range(3, 0, -1):
        g.pegs[0].append(Disk(size=size, color=8, peg=0))  # all RED
    return g


def _make_blank_game(seed: int = 42) -> Game:
    """Create a game with no disks (clean state)."""
    g = Game()
    g.rng = random.Random(seed)
    g._init_state()
    g.pegs = [[], [], []]
    return g


# ── Optimal Path Generation ──


def test_optimal_path_length():
    path = _generate_optimal_path(5)
    assert len(path) == OPTIMAL_MOVES  # 2^5 - 1 = 31


def test_optimal_path_starts_and_ends():
    path = _generate_optimal_path(5, 0, 2, 1)
    # First move should be from peg 0
    assert path[0][0] == 0
    # Last move should be from peg 0 or 1 to peg 2
    assert path[-1][1] == 2


def test_optimal_path_3_disks():
    path = _generate_optimal_path(3, 0, 2, 1)
    assert len(path) == 7  # 2^3 - 1


# ── Valid Move ──


def test_valid_move_empty_target():
    g = _make_blank_game()
    g.pegs[0].append(Disk(size=1, color=8, peg=0))
    assert g._valid_move(0, 1) is True


def test_valid_move_smaller_on_larger():
    g = _make_blank_game()
    g.pegs[0].append(Disk(size=1, color=8, peg=0))
    g.pegs[1].append(Disk(size=3, color=3, peg=1))
    assert g._valid_move(0, 1) is True  # size 1 on size 3


def test_valid_move_larger_on_smaller():
    g = _make_blank_game()
    g.pegs[0].append(Disk(size=3, color=8, peg=0))
    g.pegs[1].append(Disk(size=1, color=3, peg=1))
    assert g._valid_move(0, 1) is False  # size 3 on size 1


def test_valid_move_empty_source():
    g = _make_blank_game()
    assert g._valid_move(0, 1) is False


# ── Move Disk ──


def test_move_disk_valid():
    g = _make_blank_game()
    g.pegs[0].append(Disk(size=1, color=8, peg=0))
    color = g._move_disk(0, 1)
    assert color == 8
    assert len(g.pegs[0]) == 0
    assert len(g.pegs[1]) == 1
    assert g.pegs[1][0].size == 1
    assert g.pegs[1][0].peg == 1
    assert g.moves == 1


def test_move_disk_invalid():
    g = _make_blank_game()
    g.pegs[0].append(Disk(size=3, color=8, peg=0))
    g.pegs[1].append(Disk(size=1, color=3, peg=1))
    color = g._move_disk(0, 1)
    assert color == -1
    assert len(g.pegs[0]) == 1  # not moved
    assert g.moves == 0


# ── Combo System ──


def test_update_combo_first_move():
    g = _make_game()
    g.combo = 0
    g.last_color = -1
    g._update_combo(8)
    assert g.combo == 1
    assert g.last_color == 8


def test_update_combo_same_color():
    g = _make_game()
    g.combo = 1
    g.last_color = 8
    g._update_combo(8)
    assert g.combo == 2
    assert g.last_color == 8


def test_update_combo_different_color():
    g = _make_game()
    g.combo = 3
    g.last_color = 8
    g._update_combo(3)
    assert g.combo == 1  # reset to 1 with new color
    assert g.last_color == 3


def test_update_combo_tracks_max():
    g = _make_game()
    g.combo = 2
    g.max_combo = 2
    g.last_color = 8
    g._update_combo(8)
    assert g.combo == 3
    assert g.max_combo == 3


def test_has_just_reached_super_threshold():
    g = _make_game()
    assert g._has_just_reached_super_threshold(3) is False  # 3→4 not yet
    g.combo = 4
    assert g._has_just_reached_super_threshold(3) is True   # 3→4
    assert g._has_just_reached_super_threshold(4) is False   # already at 4


# ── Super Move ──


def test_can_super_move_no_charges():
    g = _make_game()
    g.super_moves_left = 0
    assert g._can_super_move() is False


def test_can_super_move_with_charges():
    g = _make_game()
    g.super_moves_left = 2
    assert g._can_super_move() is True


def test_do_super_move_no_charges():
    g = _make_blank_game()
    g.pegs[0].append(Disk(size=5, color=8, peg=0))
    g.pegs[1].append(Disk(size=1, color=3, peg=1))
    g.super_moves_left = 0
    result = g._do_super_move(0, 1)
    assert result is False
    assert len(g.pegs[0]) == 1  # disk not moved


def test_do_super_move_ignores_size():
    g = _make_blank_game()
    g.pegs[0].append(Disk(size=5, color=8, peg=0))
    g.pegs[1].append(Disk(size=1, color=3, peg=1))
    g.super_moves_left = 1
    result = g._do_super_move(0, 1)
    assert result is True
    assert len(g.pegs[0]) == 0
    assert len(g.pegs[1]) == 2  # size 5 on size 1 (would be invalid normally)
    assert g.super_moves_left == 0
    assert g.moves == 1


def test_do_super_move_empty_source():
    g = _make_blank_game()
    g.super_moves_left = 1
    result = g._do_super_move(0, 1)
    assert result is False


def test_do_super_move_same_peg():
    g = _make_blank_game()
    g.pegs[0].append(Disk(size=1, color=8, peg=0))
    g.super_moves_left = 1
    result = g._do_super_move(0, 0)
    assert result is False


# ── Victory Check ──


def test_check_victory_all_on_peg2():
    g = _make_blank_game()
    for size in range(5, 0, -1):
        g.pegs[2].append(Disk(size=size, color=8, peg=2))
    assert g._check_victory() is True


def test_check_victory_wrong_order():
    g = _make_blank_game()
    g.pegs[2].append(Disk(size=1, color=8, peg=2))
    g.pegs[2].append(Disk(size=2, color=8, peg=2))
    g.pegs[2].append(Disk(size=3, color=8, peg=2))
    g.pegs[2].append(Disk(size=4, color=8, peg=2))
    g.pegs[2].append(Disk(size=5, color=8, peg=2))
    assert g._check_victory() is False  # wrong order


def test_check_victory_not_all_disks():
    g = _make_blank_game()
    g.pegs[2].append(Disk(size=5, color=8, peg=2))
    assert g._check_victory() is False


def test_check_victory_empty_board():
    g = _make_blank_game()
    assert g._check_victory() is False


# ── Heat System ──


def test_add_heat():
    g = _make_game()
    g.heat = 30.0
    g._add_heat(15.0)
    assert g.heat == 45.0


def test_add_heat_capped():
    g = _make_game()
    g.heat = 95.0
    g._add_heat(20.0)
    assert g.heat == MAX_HEAT


def test_add_heat_game_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 90.0
    g._add_heat(15.0)
    assert g.heat >= MAX_HEAT
    assert g.phase == Phase.GAME_OVER


def test_update_heat_decay():
    g = _make_game()
    g.heat = 50.0
    g._update_heat(1.0 / 60.0)
    assert abs(g.heat - (50.0 - HEAT_DECAY)) < 0.001


def test_update_heat_floor():
    g = _make_game()
    g.heat = HEAT_DECAY / 2
    g._update_heat(1.0 / 60.0)
    assert g.heat == 0.0


# ── Timer ──


def test_update_timer_decrease():
    g = _make_game()
    g.game_timer = 100.0
    g._update_timer(0.016)
    assert abs(g.game_timer - 99.984) < 0.001


def test_update_timer_game_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.game_timer = 0.01
    g._update_timer(0.02)
    assert g.game_timer == 0.0
    assert g.phase == Phase.GAME_OVER


# ── Score Computation ──


def test_compute_score_basic():
    g = _make_game()
    g.moves = 31  # optimal
    g.max_combo = 2
    score = g._compute_score()
    assert score == 1000 + 2 * 50  # optimal score + combo bonus


def test_compute_score_more_moves():
    g = _make_game()
    g.moves = 62  # twice optimal
    g.max_combo = 1
    score = g._compute_score()
    assert score == 500 + 50  # half score + combo


def test_compute_score_high_combo():
    g = _make_game()
    g.moves = 31
    g.max_combo = 10
    score = g._compute_score()
    assert score == 1000 + 500


# ── Handle Click ──


def test_handle_click_select_peg():
    g = _make_simple_game()
    g.phase = Phase.PLAYING
    result = g._handle_click(0)
    assert result == "selected"
    assert g.selected_peg == 0


def test_handle_click_deselect():
    g = _make_simple_game()
    g.phase = Phase.PLAYING
    g._handle_click(0)  # select
    result = g._handle_click(0)  # same peg = deselect
    assert result == "deselected"
    assert g.selected_peg == -1


def test_handle_click_move():
    g = _make_simple_game()
    g.phase = Phase.PLAYING
    g._handle_click(0)  # select peg 0
    result = g._handle_click(1)  # move to peg 1
    assert result == "moved"
    assert len(g.pegs[1]) == 1  # disk moved
    assert g.pegs[1][0].size == 1  # smallest disk (top)
    assert g.moves == 1
    assert g.combo == 1


def test_handle_click_invalid_move():
    g = _make_simple_game()
    g.phase = Phase.PLAYING
    g.pegs[1].append(Disk(size=1, color=8, peg=1))  # size 1 on peg 1
    g._handle_click(0)  # select peg 0 (has sizes 3,2,1)
    result = g._handle_click(1)  # try to move size 1 onto size 1
    assert result == "invalid"
    assert g.heat > 0


def test_handle_click_empty_peg():
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    result = g._handle_click(0)
    assert result == "empty_peg"


def test_handle_click_no_play_wrong_phase():
    g = _make_simple_game()
    g.phase = Phase.TITLE
    result = g._handle_click(0)
    assert result == "no_play"


def test_handle_click_super_move():
    g = _make_simple_game()
    g.phase = Phase.PLAYING
    g.super_moves_left = 1
    # Make the move invalid by putting size 1 on peg 1
    g.pegs[1].append(Disk(size=1, color=8, peg=1))
    g._handle_click(0)  # select peg 0 (top disk size 1)
    result = g._handle_click(1)  # would be invalid, but super move available
    assert result == "super_move"
    assert g.super_moves_left == 0
    assert len(g.pegs[1]) == 2  # disk moved despite size rule


def test_handle_click_combo_same_color():
    g = _make_simple_game()  # all RED (color 8)
    g.phase = Phase.PLAYING
    g._handle_click(0)  # select
    g._handle_click(1)  # move size 1 to peg 1
    # Now move the next disk (also RED, size 2)
    g._handle_click(0)  # select
    g._handle_click(2)  # move size 2 to peg 2
    assert g.combo == 2  # same color = combo++


def test_handle_click_combo_reset_different_color():
    g = _make_simple_game()  # all RED
    g.phase = Phase.PLAYING
    g.last_color = 3  # GREEN, different from disk color (RED=8)
    g.combo = 5
    g._handle_click(0)  # select
    g._handle_click(1)  # move
    assert g.combo == 1  # reset
    assert g.last_color == 8  # new color


# ── Combo Chain with Super Threshold ──


def test_combo_reaches_super_threshold():
    """Moving 4 same-color disks in a row triggers super move charge."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.rng = random.Random(42)
    # Set up 4 disks all same color on peg 0
    for size in range(4, 0, -1):
        g.pegs[0].append(Disk(size=size, color=8, peg=0))

    # Move each to peg 1 → peg 2 alternately to build combo
    g.last_color = 8
    g.combo = 3  # already 3 same-color moves

    g._handle_click(0)  # select peg 0 (top disk = size 1)
    g._handle_click(1)  # move to peg 1
    assert g.combo == 4  # 4th consecutive same-color
    assert g.super_moves_left >= 1  # charge granted


# ── Game Over via Heat ──


def test_heat_game_over_via_invalid_moves():
    g = _make_simple_game()
    g.phase = Phase.PLAYING
    g.pegs[1].append(Disk(size=1, color=8, peg=1))  # size 1 on peg 1
    g.heat = MAX_HEAT - HEAT_INVALID + 0.1  # just below threshold

    g._handle_click(0)  # select
    result = g._handle_click(1)  # invalid move
    assert result == "invalid"
    assert g.phase == Phase.GAME_OVER


# ── Victory via Handle Click ──


def test_handle_click_victory():
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    # Set up all 5 disks on peg 2 in correct order
    for size in range(5, 0, -1):
        g.pegs[2].append(Disk(size=size, color=8, peg=2))
    assert g._check_victory() is True


# ── Reset / Start Game ──


def test_start_game_resets_all():
    g = _make_game()
    g.combo = 5
    g.max_combo = 7
    g.heat = 80.0
    g.moves = 20
    g.super_moves_left = 3
    g.last_color = 8
    g.game_timer = 50.0
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=5, color=8)]
    g.floating_texts = [FloatingText(x=0, y=0, text="TEST", life=5, color=8)]

    g.start_game()

    assert g.phase == Phase.PLAYING
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.moves == 0
    assert g.super_moves_left == 0
    assert g.last_color == -1
    assert g.game_timer == GAME_TIME
    assert g.particles == []
    assert g.floating_texts == []
    assert g.selected_peg == -1


def test_init_state_creates_disks():
    g = _make_game()
    total = sum(len(peg) for peg in g.pegs)
    assert total == DISK_COUNT


def test_init_state_all_disks_on_peg_zero_initially():
    g = _make_game()
    assert len(g.pegs[0]) == DISK_COUNT
    assert len(g.pegs[1]) == 0
    assert len(g.pegs[2]) == 0


# ── Particles ──


def test_spawn_particles():
    g = _make_game()
    g.rng = random.Random(42)
    g._spawn_particles(100.0, 100.0, 8, 5, 10)
    assert len(g.particles) == 5
    for p in g.particles:
        assert p.color == 8


def test_update_particles_moves_and_removes():
    g = _make_game()
    g.particles = [
        Particle(x=0.0, y=0.0, vx=1.0, vy=-1.0, life=2, color=8),
        Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=0, color=8),
    ]
    g._update_particles()
    assert len(g.particles) == 1
    p = g.particles[0]
    assert p.x == 1.0
    assert p.y == -1.0  # moved by vy before gravity applied
    assert p.vy == -0.9  # gravity removed (applied after move)
    assert p.life == 1


# ── Floating Texts ──


def test_floating_text():
    g = _make_game()
    g._spawn_floating_text(100.0, 100.0, "TEST", 7, 10)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "TEST"


def test_floating_text_moves_and_removes():
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=0.0, y=0.0, text="A", life=1, color=7),
        FloatingText(x=0.0, y=0.0, text="B", life=3, color=7),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1  # "A" died (life=1→0)
    ft = g.floating_texts[0]
    assert ft.text == "B"
    assert abs(ft.y - (-0.8)) < 0.001
    assert ft.life == 2


# ── Data Class Fields ──


def test_disk_fields():
    d = Disk(size=3, color=8, peg=0)
    assert d.size == 3
    assert d.color == 8
    assert d.peg == 0


def test_particle_fields():
    p = Particle(x=1.5, y=2.5, vx=0.5, vy=-0.5, life=10, color=8)
    assert p.x == 1.5
    assert p.y == 2.5


def test_floating_text_fields():
    ft = FloatingText(x=10.0, y=20.0, text="COMBO", life=30, color=10)
    assert ft.text == "COMBO"
    assert ft.life == 30


# ── Phase Default ──


def test_phase_default_title():
    g = Game()
    assert g.phase == Phase.TITLE


# ── Super Move Edge Cases ──


def test_super_move_from_empty_peg():
    g = _make_blank_game()
    g.super_moves_left = 1
    g._handle_click(0)  # empty
    assert g.selected_peg == -1  # nothing happens


def test_super_move_no_charges_invalid_click():
    g = _make_simple_game()
    g.phase = Phase.PLAYING
    g.pegs[1].append(Disk(size=1, color=8, peg=1))  # blocks normal move
    g.super_moves_left = 0
    g._handle_click(0)
    result = g._handle_click(1)
    assert result == "invalid"
    assert len(g.pegs[1]) == 1  # unchanged


# ── Constant Sanity ──


def test_constants():
    assert DISK_COUNT == 5
    assert OPTIMAL_MOVES == 31
    assert MAX_HEAT == 100.0
    assert SUPER_THRESHOLD == 4
    assert GAME_TIME == 120.0
    assert ANIM_DURATION == 0.5
    assert len(PEG_X) == 3
    assert len(DISK_COLORS) == 5
    assert SCREEN_W == 320
    assert SCREEN_H == 240


# ── Move Sequences ──


def test_complete_hanoi_solve_sequence():
    """Walk through a valid Hanoi solution for 2 disks and verify it works."""
    g = _make_blank_game()
    g.phase = Phase.PLAYING
    g.pegs[0] = [
        Disk(size=2, color=8, peg=0),
        Disk(size=1, color=8, peg=0),
    ]

    # Move 1: peg 0 → peg 1 (size 1)
    g._handle_click(0)
    result = g._handle_click(1)
    assert result == "moved"
    assert len(g.pegs[0]) == 1
    assert g.pegs[0][0].size == 2
    assert len(g.pegs[1]) == 1
    assert g.pegs[1][0].size == 1

    # Move 2: peg 0 → peg 2 (size 2)
    g._handle_click(0)
    result = g._handle_click(2)
    assert result == "moved"
    assert len(g.pegs[0]) == 0
    assert len(g.pegs[2]) == 1
    assert g.pegs[2][0].size == 2

    # Move 3: peg 1 → peg 2 (size 1 onto size 2)
    g._handle_click(1)
    result = g._handle_click(2)
    assert result == "moved"
    assert len(g.pegs[1]) == 0
    assert len(g.pegs[2]) == 2
    assert g.pegs[2][0].size == 2
    assert g.pegs[2][1].size == 1


# ── ANIM Phase ──


def test_super_move_enters_anim_phase():
    g = _make_simple_game()
    g.phase = Phase.PLAYING
    g.pegs[1].append(Disk(size=1, color=8, peg=1))  # invalid normal move
    g.super_moves_left = 1
    g._handle_click(0)
    result = g._handle_click(1)
    assert result == "super_move"
    assert g.phase == Phase.ANIM
    assert g._anim_timer == ANIM_DURATION
    assert g._camera_shake > 0


def test_anim_returns_to_playing():
    g = _make_simple_game()
    g.phase = Phase.ANIM
    g._anim_timer = 0.01  # almost done
    g._camera_shake = 0.01
    g.update()  # dt = 1/60 ≈ 0.0167
    assert g._anim_timer <= 0
    assert g.phase == Phase.PLAYING


# ── Handle Click Edge Cases ──


def test_handle_click_invalid_peg():
    g = _make_simple_game()
    g.phase = Phase.PLAYING
    result = g._handle_click(-1)
    assert result == "invalid_peg"
    result = g._handle_click(3)
    assert result == "invalid_peg"


def test_handle_click_deselect_after_reselect():
    g = _make_simple_game()
    g.phase = Phase.PLAYING
    g._handle_click(0)  # select
    g._handle_click(0)  # click same = deselect
    assert g.selected_peg == -1


def test_handle_click_deselects_after_invalid_move():
    g = _make_simple_game()
    g.phase = Phase.PLAYING
    g.pegs[1].append(Disk(size=1, color=8, peg=1))
    g.super_moves_left = 0
    g._handle_click(0)  # select
    g._handle_click(1)  # invalid move
    assert g.selected_peg == -1  # should deselect after any move attempt


def test_handle_click_deselects_after_valid_move():
    g = _make_simple_game()
    g.phase = Phase.PLAYING
    g._handle_click(0)  # select
    g._handle_click(1)  # valid move
    assert g.selected_peg == -1


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
            print(f"  ✅ {_test.__name__}")
            passed += 1
        except Exception as _e:
            print(f"  ❌ {_test.__name__}: {_e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {len(_tests)} total")
    if failed > 0:
        sys.exit(1)
