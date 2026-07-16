"""Test logic for 244_claw_surge — headless tests (no Pyxel)."""

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/244_claw_surge")

from main import (  # noqa: E402
    BASE_VALUE,
    CELL,
    COLORS,
    COLOR_CYCLE_FRAMES,
    COLS,
    GAME_TIME,
    GRID_X,
    GRID_Y,
    HEAT_DECAY,
    HEAT_EMPTY,
    HEAT_MISMATCH,
    MAX_HEAT,
    MOVE_COOLDOWN,
    ROWS,
    SPAWN_INTERVAL_START,
    SUPER_DURATION,
    FloatingText,
    Game,
    Particle,
    Phase,
    Prize,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g._pre_init()
    g.reset()
    return g


# ── Constants ────────────────────────────────────────────


def test_constants() -> None:
    assert COLS == 8
    assert ROWS == 6
    assert CELL == 32
    assert GRID_X == 32
    assert GRID_Y == 24
    assert COLORS == (8, 11, 5, 10)
    assert SUPER_DURATION == 300
    assert GAME_TIME == 1800
    assert MAX_HEAT == 100.0
    assert HEAT_DECAY == 0.02
    assert HEAT_MISMATCH == 15.0
    assert HEAT_EMPTY == 5.0
    assert BASE_VALUE == 10
    assert MOVE_COOLDOWN == 5
    assert SPAWN_INTERVAL_START == 60
    assert COLOR_CYCLE_FRAMES == 90


# ── Dataclasses ──────────────────────────────────────────


def test_prize_dataclass() -> None:
    p = Prize(x=3, y=2, color=8, value=10)
    assert p.x == 3
    assert p.y == 2
    assert p.color == 8
    assert p.value == 10


def test_particle_dataclass() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=15, color=8)
    assert p.x == 10.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == 8


def test_floating_text_dataclass() -> None:
    ft = FloatingText(x=100.0, y=200.0, text="+10", life=30, color=7)
    assert ft.text == "+10"
    assert ft.life == 30
    assert ft.color == 7


# ── Phase Enum ───────────────────────────────────────────


def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    assert Phase.TITLE is not Phase.PLAYING


# ── Game Initialization ──────────────────────────────────


def test_game_make() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == GAME_TIME
    assert g.super_timer == 0
    assert g.claw_col == COLS // 2
    assert g.claw_row == ROWS // 2
    assert g.claw_color == COLORS[0]
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0


def test_initial_spawn() -> None:
    g = _make_game()
    assert len(g.prizes) > 0
    assert len(g.prizes) <= COLS * ROWS
    occupied = set()
    for p in g.prizes:
        assert 0 <= p.x < COLS
        assert 0 <= p.y < ROWS
        assert p.color in COLORS
        assert p.value == BASE_VALUE
        assert (p.x, p.y) not in occupied
        occupied.add((p.x, p.y))


def test_reset_clears_state() -> None:
    g = _make_game()
    g.score = 500
    g.combo = 3
    g.heat = 50.0
    g.super_timer = 100
    g.particles = [Particle(0, 0, 0, 0, 5, 8)]
    g.floating_texts = [FloatingText(0, 0, "x", 5, 7)]
    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.phase == Phase.PLAYING


# ── Prize Grid ───────────────────────────────────────────


def test_get_prize_at() -> None:
    g = _make_game()
    p = g.prizes[0]
    assert g._get_prize_at(p.x, p.y) is p


def test_get_prize_at_empty() -> None:
    g = _make_game()
    # Find an empty slot
    occupied = {(p.x, p.y) for p in g.prizes}
    for col in range(COLS):
        for row in range(ROWS):
            if (col, row) not in occupied:
                assert g._get_prize_at(col, row) is None
                return
    # If grid is full, force remove one
    p = g.prizes[0]
    g._remove_prize_at(p.x, p.y)
    assert g._get_prize_at(p.x, p.y) is None


def test_remove_prize_at() -> None:
    g = _make_game()
    p = g.prizes[0]
    col, row = p.x, p.y
    g._remove_prize_at(col, row)
    assert g._get_prize_at(col, row) is None
    assert p not in g.prizes


def test_empty_slots() -> None:
    g = _make_game()
    slots = g._empty_slots()
    occupied = {(p.x, p.y) for p in g.prizes}
    assert len(slots) == COLS * ROWS - len(occupied)
    for col, row in slots:
        assert (col, row) not in occupied


# ── Claw Position ───────────────────────────────────────


def test_claw_px() -> None:
    g = _make_game()
    g.claw_col = 3
    g.claw_row = 2
    cx, cy = g._claw_px()
    assert cx == GRID_X + 3 * CELL + CELL // 2
    assert cy == GRID_Y + 2 * CELL + CELL // 2


# ── Grab Logic ──────────────────────────────────────────


def test_grab_prize_match() -> None:
    g = _make_game()
    p = g.prizes[0]
    g.claw_col = p.x
    g.claw_row = p.y
    g.claw_color = p.color
    g._grab_prize()
    assert g.combo == 1
    assert g.score > 0
    assert g._get_prize_at(p.x, p.y) is None
    assert len(g.particles) > 0


def test_grab_prize_mismatch() -> None:
    g = _make_game()
    p = g.prizes[0]
    for c in COLORS:
        if c != p.color:
            g.claw_color = c
            break
    g.claw_col = p.x
    g.claw_row = p.y
    g._grab_prize()
    assert g.combo == 0
    assert g.heat == HEAT_MISMATCH
    assert g._get_prize_at(p.x, p.y) is None


def test_grab_prize_empty_slot() -> None:
    g = _make_game()
    slots = g._empty_slots()
    if not slots:
        return
    g.claw_col, g.claw_row = slots[0]
    g._grab_prize()
    assert g.combo == 0
    assert g.heat == HEAT_EMPTY


def test_grab_prize_combo_chain() -> None:
    g = _make_game()
    g.prizes = [Prize(x=3, y=2, color=COLORS[0], value=BASE_VALUE)]
    g.claw_col = 3
    g.claw_row = 2
    g.claw_color = COLORS[0]

    # Grab 1
    g._grab_prize()
    assert g.combo == 1
    assert g.score == BASE_VALUE * 1  # combo=1

    # Re-add prize
    g.prizes = [Prize(x=3, y=2, color=COLORS[0], value=BASE_VALUE)]
    g._grab_prize()
    assert g.combo == 2
    # combo=2 → score += 10*2 = 20, total=30
    assert g.score == BASE_VALUE * 1 + BASE_VALUE * 2

    g.prizes = [Prize(x=3, y=2, color=COLORS[0], value=BASE_VALUE)]
    g._grab_prize()
    assert g.combo == 3
    assert g.score == BASE_VALUE * 1 + BASE_VALUE * 2 + BASE_VALUE * 3


def test_grab_prize_combo4_triggers_super() -> None:
    g = _make_game()
    g.claw_col = 3
    g.claw_row = 2
    g.claw_color = COLORS[0]

    for _ in range(3):
        g.prizes = [Prize(x=3, y=2, color=COLORS[0], value=BASE_VALUE)]
        g._grab_prize()
    assert g.combo == 3
    assert g.super_timer == 0

    g.prizes = [Prize(x=3, y=2, color=COLORS[0], value=BASE_VALUE)]
    g._grab_prize()
    assert g.combo == 4
    assert g.super_timer == SUPER_DURATION


def test_grab_prize_super_any_color() -> None:
    g = _make_game()
    g.claw_col = 3
    g.claw_row = 2
    g.claw_color = COLORS[0]
    g.super_timer = 100
    g.combo = 3

    # Prize of a different color
    g.prizes = [Prize(x=3, y=2, color=COLORS[1], value=BASE_VALUE)]
    g._grab_prize()
    # Super mode: any color matches, combo increments, no heat
    assert g.combo == 4
    assert g.heat == 0.0


def test_grab_prize_super_3x_score() -> None:
    g = _make_game()
    g.claw_col = 3
    g.claw_row = 2
    g.claw_color = COLORS[0]
    g.super_timer = 100

    g.prizes = [Prize(x=3, y=2, color=COLORS[0], value=BASE_VALUE)]
    g._grab_prize()
    # combo=1, super=3x → 10 * 1 * 3 = 30
    assert g.score == 30


# ── Combo and Max Combo ─────────────────────────────────


def test_max_combo_tracking() -> None:
    g = _make_game()
    g.claw_col = 3
    g.claw_row = 2
    g.claw_color = COLORS[0]

    for _ in range(3):
        g.prizes = [Prize(x=3, y=2, color=COLORS[0], value=BASE_VALUE)]
        g._grab_prize()
    assert g.max_combo == 3

    # Mismatch resets combo but max_combo preserved
    g.prizes = [Prize(x=3, y=2, color=COLORS[1], value=BASE_VALUE)]
    g._grab_prize()
    assert g.combo == 0
    assert g.max_combo == 3


# ── SUPER Mode ───────────────────────────────────────────


def test_update_super_decrement() -> None:
    g = _make_game()
    g.super_timer = 10
    g._update_super()
    assert g.super_timer == 9


def test_update_super_stops_at_zero() -> None:
    g = _make_game()
    g.super_timer = 1
    g._update_super()
    assert g.super_timer == 0
    g._update_super()
    assert g.super_timer == 0


# ── Color Cycle ─────────────────────────────────────────


def test_color_cycle() -> None:
    g = _make_game()
    initial_color = g.claw_color
    g._color_timer = 1
    g._update_color_cycle()
    assert g._color_timer == COLOR_CYCLE_FRAMES
    assert g.claw_color != initial_color
    assert g.claw_color in COLORS


def test_color_cycle_paused_during_super() -> None:
    g = _make_game()
    g.super_timer = 100
    initial_color = g.claw_color
    initial_timer = g._color_timer
    g._update_color_cycle()
    assert g.claw_color == initial_color
    assert g._color_timer == initial_timer


# ── Heat System ──────────────────────────────────────────


def test_update_heat_decay() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 50.0 - HEAT_DECAY


def test_update_heat_not_negative() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_game_over() -> None:
    g = _make_game()
    g.heat = MAX_HEAT + HEAT_DECAY
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


# ── Timer ────────────────────────────────────────────────


def test_update_timer_decrement() -> None:
    g = _make_game()
    t = g.timer
    g._update_timer()
    assert g.timer == t - 1


def test_update_timer_game_over() -> None:
    g = _make_game()
    g.timer = 1
    g._update_timer()
    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER


# ── Prize Spawning ──────────────────────────────────────


def test_spawn_prizes() -> None:
    g = _make_game()
    g.timer = GAME_TIME
    slot_count_before = len(g._empty_slots())
    g._spawn_timer = 1
    g._spawn_prizes()
    # New spawn interval set
    assert g._spawn_timer > 0
    if slot_count_before > 0:
        # A prize was spawned
        assert len(g._empty_slots()) == slot_count_before - 1
    # Check spawned prize is valid
    for p in g.prizes:
        assert p.color in COLORS
        assert p.value == BASE_VALUE


def test_spawn_prizes_no_empty_slots() -> None:
    g = _make_game()
    # Fill all slots
    g.prizes = []
    for col in range(COLS):
        for row in range(ROWS):
            g.prizes.append(Prize(x=col, y=row, color=COLORS[0], value=BASE_VALUE))
    g._spawn_timer = 1
    count_before = len(g.prizes)
    g._spawn_prizes()
    assert len(g.prizes) == count_before  # No new prize (grid full)


# ── Particles ────────────────────────────────────────────


def test_update_particles_move_and_decay() -> None:
    g = _make_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=2.0, vy=-1.0, life=5, color=8)]
    g._update_particles()
    p = g.particles[0]
    assert p.x == 102.0
    assert p.y == 99.0
    assert p.vy == -0.95  # vy += 0.05 gravity
    assert p.life == 4


def test_update_particles_remove_dead() -> None:
    g = _make_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=1, color=8)]
    g._update_particles()
    assert len(g.particles) == 0


# ── Floating Texts ───────────────────────────────────────


def test_update_floating_texts_move_and_decay() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=100.0, y=200.0, text="+10", life=30, color=7)]
    g._update_floating_texts()
    ft = g.floating_texts[0]
    assert ft.y == 199.5
    assert ft.life == 29


def test_update_floating_texts_remove_dead() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=100.0, y=200.0, text="x", life=1, color=7)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Game Over ────────────────────────────────────────────


def test_end_game() -> None:
    g = _make_game()
    g.score = 500
    g.best_score = 300
    g._end_game()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 500


def test_end_game_best_score_not_beaten() -> None:
    g = _make_game()
    g.score = 200
    g.best_score = 300
    g._end_game()
    assert g.best_score == 300


def test_end_game_best_score_tie() -> None:
    g = _make_game()
    g.score = 300
    g.best_score = 300
    g._end_game()
    assert g.best_score == 300  # unchanged on tie


# ── Spawn Particles ─────────────────────────────────────


def test_spawn_grab_particles() -> None:
    g = _make_game()
    g._spawn_grab_particles(100.0, 100.0, 8, 8, False)
    assert 6 <= len(g.particles) <= 10
    for p in g.particles:
        assert p.color == 8


def test_spawn_grab_particles_super() -> None:
    g = _make_game()
    g._spawn_grab_particles(100.0, 100.0, 15, 8, True)
    assert len(g.particles) == 15
    for p in g.particles:
        assert p.color in COLORS


def test_spawn_mismatch_particles() -> None:
    g = _make_game()
    g._spawn_mismatch_particles(100.0, 100.0)
    assert 3 <= len(g.particles) <= 5
    for p in g.particles:
        assert p.color == 13


def test_spawn_miss_particles() -> None:
    g = _make_game()
    g._spawn_miss_particles(100.0, 100.0)
    assert 3 <= len(g.particles) <= 5
    for p in g.particles:
        assert p.color == 13


def test_spawn_super_particles() -> None:
    g = _make_game()
    g._spawn_super_particles(100.0, 100.0)
    assert 15 <= len(g.particles) <= 20
    for p in g.particles:
        assert p.color in COLORS


def test_spawn_floating_text() -> None:
    g = _make_game()
    g._spawn_floating_text(100.0, 200.0, "test", 7, 30)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.x == 100.0
    assert ft.y == 200.0
    assert ft.text == "test"
    assert ft.life == 30
    assert ft.color == 7


# ── Heat Cap ────────────────────────────────────────────


def test_heat_never_exceeds_max() -> None:
    g = _make_game()
    g.heat = MAX_HEAT - 1
    # Empty grab adds HEAT_EMPTY (5)
    g.claw_col = 0
    g.claw_row = 0
    # Make sure slot is empty
    g.prizes = []
    g._grab_prize()
    assert g.heat == MAX_HEAT


# ── Integration ─────────────────────────────────────────


def test_full_grab_flow() -> None:
    g = _make_game()
    g.prizes = [Prize(x=3, y=2, color=COLORS[0], value=BASE_VALUE)]
    g.claw_col = 3
    g.claw_row = 2
    g.claw_color = COLORS[0]
    g._grab_prize()
    assert g.combo == 1
    assert g.score == 10
    assert len(g.particles) > 0
    assert len(g.floating_texts) >= 1


def test_full_mismatch_flow() -> None:
    g = _make_game()
    g.prizes = [Prize(x=3, y=2, color=COLORS[0], value=BASE_VALUE)]
    g.claw_col = 3
    g.claw_row = 2
    g.claw_color = COLORS[1]  # mismatch
    g._grab_prize()
    assert g.combo == 0
    assert g.heat == HEAT_MISMATCH
    has_gray = any(p.color == 13 for p in g.particles)
    assert has_gray


def test_consecutive_matches_increasing_score() -> None:
    g = _make_game()
    g.claw_col = 3
    g.claw_row = 2
    g.claw_color = COLORS[0]

    # Grab 1
    g.prizes = [Prize(x=3, y=2, color=COLORS[0], value=BASE_VALUE)]
    g._grab_prize()
    assert g.score == 10  # 10*1

    # Grab 2
    g.prizes = [Prize(x=3, y=2, color=COLORS[0], value=BASE_VALUE)]
    g._grab_prize()
    assert g.score == 30  # 10+20

    # Grab 3
    g.prizes = [Prize(x=3, y=2, color=COLORS[0], value=BASE_VALUE)]
    g._grab_prize()
    assert g.score == 60  # 30+30


def test_heat_decay_over_time() -> None:
    g = _make_game()
    g.heat = 10.0
    for _ in range(10):
        g._update_heat()
    expected = 10.0 - HEAT_DECAY * 10
    assert abs(g.heat - expected) < 0.01


def test_best_score_persists_across_resets() -> None:
    g = _make_game()
    g.score = 500
    g._end_game()
    assert g.best_score == 500
    g.reset()
    assert g.best_score == 500  # preserved
    assert g.score == 0


def test_spawn_interval_escalation() -> None:
    g = _make_game()
    g.timer = GAME_TIME  # start
    g._spawn_timer = 1
    g._spawn_prizes()
    assert g._spawn_timer == SPAWN_INTERVAL_START  # max interval at start

    g._spawn_timer = 1
    g.timer = GAME_TIME // 2  # mid
    g._spawn_prizes()
    assert 45 - 1 <= g._spawn_timer <= 45 + 1  # ~45 at mid

    g._spawn_timer = 1
    g.timer = 0  # end
    g._spawn_prizes()
    assert g._spawn_timer == 30  # min interval at end


if __name__ == "__main__":
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=False,
    )
    sys.exit(result.returncode)
