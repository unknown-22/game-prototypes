"""Test logic for 245_climb_surge — headless tests (no Pyxel)."""

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/245_climb_surge")

from main import (  # noqa: E402
    CELL,
    COLOR_CYCLE_INITIAL,
    COLOR_CYCLE_MIN,
    COLORS,
    COLOR_NAMES,
    GAME_DURATION,
    GRID_COLS,
    GRID_OFFSET_X,
    GRID_OFFSET_Y,
    GRID_ROWS,
    HEAT_DECAY,
    HEAT_FALL,
    HEAT_MAX,
    HEAT_MISMATCH,
    HOLD_RADIUS,
    MAX_HOLDS,
    REACH_RADIUS,
    SCREEN_H,
    SCREEN_W,
    SHAKE_FRAMES,
    SPAWN_INTERVAL_INITIAL,
    SPAWN_INTERVAL_MIN,
    STUN_FALL,
    STUN_MISMATCH,
    SUPER_DURATION,
    FloatingText,
    Game,
    Hold,
    Particle,
    Phase,
)


def _make_game() -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g._pre_init()
    g.reset()
    return g


# ── Constants ────────────────────────────────────────────


def test_constants() -> None:
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert CELL == 24
    assert GRID_OFFSET_X == 36
    assert GRID_OFFSET_Y == 24
    assert GRID_COLS == 10
    assert GRID_ROWS == 8
    assert REACH_RADIUS == 36.0
    assert HOLD_RADIUS == 10
    assert MAX_HOLDS == 30
    assert SPAWN_INTERVAL_INITIAL == 60
    assert SPAWN_INTERVAL_MIN == 30
    assert COLOR_CYCLE_INITIAL == 90
    assert COLOR_CYCLE_MIN == 40
    assert GAME_DURATION == 1800
    assert SUPER_DURATION == 300
    assert HEAT_MAX == 100.0
    assert HEAT_DECAY == 0.02
    assert HEAT_MISMATCH == 15.0
    assert HEAT_FALL == 25.0
    assert STUN_MISMATCH == 10
    assert STUN_FALL == 20
    assert COLORS == (8, 11, 5, 10)
    assert COLOR_NAMES == ("RED", "LIME", "DARK_BLUE", "YELLOW")
    assert SHAKE_FRAMES == 15


# ── Dataclasses ──────────────────────────────────────────


def test_hold_dataclass() -> None:
    h = Hold(col=3, row=2, color=8)
    assert h.col == 3
    assert h.row == 2
    assert h.color == 8
    assert h.x == 0.0
    assert h.y == 0.0
    assert h.grabbed is False


def test_hold_position_computed() -> None:
    h = Hold(col=3, row=2, color=8)
    h.x = GRID_OFFSET_X + 3 * CELL + CELL // 2
    h.y = GRID_OFFSET_Y + 2 * CELL + CELL // 2
    assert h.x == 36 + 3 * 24 + 12
    assert h.y == 24 + 2 * 24 + 12


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
    assert g.player_col == GRID_COLS // 2
    assert g.player_row == GRID_ROWS - 1
    assert g.grip_color_index == 0
    assert g.grip_color == COLORS[0]
    assert g.color_timer == COLOR_CYCLE_INITIAL
    assert g.color_cycle_interval == COLOR_CYCLE_INITIAL
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.game_timer == GAME_DURATION
    assert g.stun_timer == 0
    assert g.spawn_timer == 0
    assert g.spawn_interval == SPAWN_INTERVAL_INITIAL
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.shake_frames == 0
    assert g.ghost_path == []
    assert g.best_score == 0


def test_initial_spawn() -> None:
    g = _make_game()
    assert len(g.holds) > 0
    assert len(g.holds) <= 15
    start_col = GRID_COLS // 2
    start_row = GRID_ROWS - 1
    has_start = any(h.col == start_col and h.row == start_row for h in g.holds)
    assert has_start
    occupied: set[tuple[int, int]] = set()
    for h in g.holds:
        assert 0 <= h.col < GRID_COLS
        assert 0 <= h.row < GRID_ROWS
        assert h.color in COLORS
        assert (h.col, h.row) not in occupied
        occupied.add((h.col, h.row))
        expected_x = GRID_OFFSET_X + h.col * CELL + CELL // 2
        expected_y = GRID_OFFSET_Y + h.row * CELL + CELL // 2
        assert h.x == expected_x
        assert h.y == expected_y


def test_reset_clears_state() -> None:
    g = _make_game()
    g.score = 500
    g.combo = 3
    g.heat = 50.0
    g.super_timer = 100
    g.game_timer = 500
    g.stun_timer = 5
    g.particles = [Particle(0, 0, 0, 0, 5, 8)]
    g.floating_texts = [FloatingText(0, 0, "x", 5, 7)]
    g.ghost_path = [(0, 0)]
    g.shake_frames = 5
    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.game_timer == GAME_DURATION
    assert g.stun_timer == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.ghost_path == []
    assert g.shake_frames == 0
    assert g.phase == Phase.PLAYING


# ── Hold Grid ────────────────────────────────────────────


def test_hold_at() -> None:
    g = _make_game()
    h = g.holds[0]
    assert g._hold_at(h.col, h.row) is h


def test_hold_at_empty() -> None:
    g = _make_game()
    g.holds = []
    assert g._hold_at(0, 0) is None


def test_holds_in_reach() -> None:
    g = _make_game()
    g.holds = []
    g.player_col = 4
    g.player_row = 4
    near = Hold(col=5, row=4, color=COLORS[0])
    near.x = GRID_OFFSET_X + 5 * CELL + CELL // 2
    near.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
    far = Hold(col=0, row=0, color=COLORS[1])
    far.x = GRID_OFFSET_X + 0 * CELL + CELL // 2
    far.y = GRID_OFFSET_Y + 0 * CELL + CELL // 2
    g.holds = [near, far]
    in_reach = g._holds_in_reach()
    assert near in in_reach
    assert far not in in_reach


# ── Movement ─────────────────────────────────────────────


def test_move_to_hold_match() -> None:
    g = _make_game()
    h = Hold(col=4, row=4, color=COLORS[0])
    h.x = GRID_OFFSET_X + 4 * CELL + CELL // 2
    h.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
    g.holds = [h]
    g.player_col = 4
    g.player_row = 4
    g.grip_color = COLORS[0]
    g._move_to_hold(h)
    assert g.combo == 1
    assert g.score == 10
    assert h.grabbed is True
    assert len(g.particles) > 0
    assert len(g.floating_texts) > 0


def test_move_to_hold_mismatch() -> None:
    g = _make_game()
    g.combo = 2
    h = Hold(col=4, row=4, color=COLORS[1])
    h.x = GRID_OFFSET_X + 4 * CELL + CELL // 2
    h.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
    g.holds = [h]
    g.player_col = 4
    g.player_row = 4
    g.grip_color = COLORS[0]
    g._move_to_hold(h)
    assert g.combo == 0
    assert g.heat == HEAT_MISMATCH
    assert g.stun_timer == STUN_MISMATCH


def test_move_to_hold_super_any_color() -> None:
    g = _make_game()
    g.super_timer = 100
    g.combo = 3
    h = Hold(col=4, row=4, color=COLORS[1])
    h.x = GRID_OFFSET_X + 4 * CELL + CELL // 2
    h.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
    g.holds = [h]
    g.player_col = 4
    g.player_row = 4
    g.grip_color = COLORS[0]
    g._move_to_hold(h)
    assert g.combo == 4
    assert g.heat == 0.0


def test_move_to_hold_super_3x_score() -> None:
    g = _make_game()
    g.super_timer = 100
    h = Hold(col=4, row=4, color=COLORS[0])
    h.x = GRID_OFFSET_X + 4 * CELL + CELL // 2
    h.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
    g.holds = [h]
    g.player_col = 4
    g.player_row = 4
    g.grip_color = COLORS[0]
    g._move_to_hold(h)
    assert g.score == 30


def test_move_to_hold_combo_chain() -> None:
    g = _make_game()
    g.player_col = 4
    g.player_row = 4
    g.grip_color = COLORS[0]
    for i in range(1, 4):
        h = Hold(col=4, row=4, color=COLORS[0])
        h.x = GRID_OFFSET_X + 4 * CELL + CELL // 2
        h.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
        g.holds = [h]
        g._move_to_hold(h)
        assert g.combo == i
    assert g.score == 10 + 20 + 30


def test_move_to_hold_combo_4_triggers_super() -> None:
    g = _make_game()
    g.player_col = 4
    g.player_row = 4
    g.grip_color = COLORS[0]
    for _ in range(3):
        h = Hold(col=4, row=4, color=COLORS[0])
        h.x = GRID_OFFSET_X + 4 * CELL + CELL // 2
        h.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
        g.holds = [h]
        g._move_to_hold(h)
    assert g.combo == 3
    assert g.super_timer == 0
    h = Hold(col=4, row=4, color=COLORS[0])
    h.x = GRID_OFFSET_X + 4 * CELL + CELL // 2
    h.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
    g.holds = [h]
    g._move_to_hold(h)
    assert g.combo == 4
    assert g.super_timer == SUPER_DURATION


# ── Try Move ─────────────────────────────────────────────


def test_try_move_valid() -> None:
    g = _make_game()
    target = Hold(col=5, row=3, color=COLORS[0])
    target.x = GRID_OFFSET_X + 5 * CELL + CELL // 2
    target.y = GRID_OFFSET_Y + 3 * CELL + CELL // 2
    g.holds = [target]
    g.player_col = 4
    g.player_row = 3
    g.grip_color = COLORS[0]
    g._try_move(1, 0)
    assert g.player_col == 5
    assert g.player_row == 3


def test_try_move_no_hold() -> None:
    g = _make_game()
    g.holds = []
    g.player_col = 4
    g.player_row = 3
    g._try_move(1, 0)
    assert g.player_col == 4
    assert g.player_row == 3


def test_try_move_out_of_bounds() -> None:
    g = _make_game()
    g.player_col = 0
    g.player_row = 3
    g._try_move(-1, 0)
    assert g.player_col == 0


# ── Fall Detection ───────────────────────────────────────


def test_check_fall_no_holds_in_reach() -> None:
    g = _make_game()
    g.holds = []
    g.player_col = 4
    g.player_row = 4
    g._check_fall()
    assert g.heat == HEAT_FALL
    assert g.stun_timer == STUN_FALL
    assert g.combo == 0


def test_check_fall_while_stunned() -> None:
    g = _make_game()
    g.holds = []
    g.stun_timer = 5
    g.heat = 10.0
    g.player_col = 4
    g.player_row = 4
    g._check_fall()
    assert g.heat == 10.0


def test_check_fall_has_reach() -> None:
    g = _make_game()
    h = Hold(col=5, row=4, color=COLORS[0])
    h.x = GRID_OFFSET_X + 5 * CELL + CELL // 2
    h.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
    g.holds = [h]
    g.player_col = 4
    g.player_row = 4
    g._check_fall()
    assert g.heat == 0.0
    assert g.stun_timer == 0


def test_check_fall_respawns_at_nearest() -> None:
    g = _make_game()
    near = Hold(col=3, row=4, color=COLORS[0])
    near.x = GRID_OFFSET_X + 3 * CELL + CELL // 2
    near.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
    far = Hold(col=9, row=7, color=COLORS[1])
    far.x = GRID_OFFSET_X + 9 * CELL + CELL // 2
    far.y = GRID_OFFSET_Y + 7 * CELL + CELL // 2
    g.holds = [far, near]
    g.player_col = 0
    g.player_row = 4
    g._check_fall()
    assert g.player_col == near.col
    assert g.player_row == near.row


def test_find_nearest_hold() -> None:
    g = _make_game()
    near = Hold(col=5, row=4, color=COLORS[0])
    near.x = GRID_OFFSET_X + 5 * CELL + CELL // 2
    near.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
    far = Hold(col=0, row=0, color=COLORS[1])
    far.x = GRID_OFFSET_X + 0 * CELL + CELL // 2
    far.y = GRID_OFFSET_Y + 0 * CELL + CELL // 2
    g.holds = [far, near]
    g.player_col = 4
    g.player_row = 4
    nearest = g._find_nearest_hold()
    assert nearest is near


def test_find_nearest_hold_none() -> None:
    g = _make_game()
    g.holds = []
    g.player_col = 4
    g.player_row = 4
    assert g._find_nearest_hold() is None


def test_find_nearest_hold_empty() -> None:
    g = _make_game()
    g.holds = []
    g.player_col = 4
    g.player_row = 4
    assert g._find_nearest_hold() is None


# ── Combo and Max Combo ─────────────────────────────────


def test_max_combo_tracking() -> None:
    g = _make_game()
    g.player_col = 4
    g.player_row = 4
    g.grip_color = COLORS[0]
    for _ in range(3):
        h = Hold(col=4, row=4, color=COLORS[0])
        h.x = GRID_OFFSET_X + 4 * CELL + CELL // 2
        h.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
        g.holds = [h]
        g._move_to_hold(h)
    assert g.max_combo == 3

    h = Hold(col=4, row=4, color=COLORS[1])
    h.x = GRID_OFFSET_X + 4 * CELL + CELL // 2
    h.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
    g.holds = [h]
    g._move_to_hold(h)
    assert g.combo == 0
    assert g.max_combo == 3


# ── Ghost Path ───────────────────────────────────────────


def test_ghost_path_recording() -> None:
    g = _make_game()
    g.player_col = 4
    g.player_row = 4
    g.grip_color = COLORS[0]
    h = Hold(col=4, row=4, color=COLORS[0])
    h.x = GRID_OFFSET_X + 4 * CELL + CELL // 2
    h.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
    g.holds = [h]
    g._move_to_hold(h)
    assert len(g.ghost_path) == 1
    assert g.ghost_path[0] == (4, 4)


def test_ghost_path_not_recorded_on_mismatch() -> None:
    g = _make_game()
    g.player_col = 4
    g.player_row = 4
    g.grip_color = COLORS[0]
    h = Hold(col=4, row=4, color=COLORS[1])
    h.x = GRID_OFFSET_X + 4 * CELL + CELL // 2
    h.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
    g.holds = [h]
    g._move_to_hold(h)
    assert g.ghost_path == []


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


def test_is_super() -> None:
    g = _make_game()
    assert g._is_super() is False
    g.super_timer = 100
    assert g._is_super() is True
    g.super_timer = 0
    assert g._is_super() is False


# ── Color Cycle ─────────────────────────────────────────


def test_color_cycle() -> None:
    g = _make_game()
    initial_color = g.grip_color
    g.color_timer = 1
    g._update_color_cycle()
    assert g.color_timer == g.color_cycle_interval
    assert g.grip_color != initial_color
    assert g.grip_color in COLORS


def test_color_cycle_wraps() -> None:
    g = _make_game()
    g.grip_color_index = 3
    g.grip_color = COLORS[3]
    g.color_timer = 1
    g._update_color_cycle()
    assert g.grip_color_index == 0
    assert g.grip_color == COLORS[0]


def test_color_cycle_paused_during_super() -> None:
    g = _make_game()
    g.super_timer = 100
    initial_color = g.grip_color
    initial_timer = g.color_timer
    g._update_color_cycle()
    assert g.grip_color == initial_color
    assert g.color_timer == initial_timer


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
    g.heat = HEAT_MAX + HEAT_DECAY
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.shake_frames == SHAKE_FRAMES


def test_heat_never_exceeds_max() -> None:
    g = _make_game()
    g.heat = HEAT_MAX - 1
    h = Hold(col=4, row=4, color=COLORS[1])
    h.x = GRID_OFFSET_X + 4 * CELL + CELL // 2
    h.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
    g.holds = [h]
    g.player_col = 4
    g.player_row = 4
    g.grip_color = COLORS[0]
    g._move_to_hold(h)
    assert g.heat == HEAT_MAX


def test_heat_decay_over_time() -> None:
    g = _make_game()
    g.heat = 10.0
    for _ in range(10):
        g._update_heat()
    expected = 10.0 - HEAT_DECAY * 10
    assert abs(g.heat - expected) < 0.01


# ── Timer ────────────────────────────────────────────────


def test_game_timer_decrement() -> None:
    g = _make_game()
    t = g.game_timer
    g.game_timer -= 1
    assert g.game_timer == t - 1


def test_game_timer_game_over() -> None:
    g = _make_game()
    g.game_timer = 1
    g.stun_timer = 0
    g._update_playing()
    assert g.phase == Phase.GAME_OVER


# ── Stun ─────────────────────────────────────────────────


def test_stun_prevents_actions() -> None:
    g = _make_game()
    target = Hold(col=5, row=3, color=COLORS[0])
    target.x = GRID_OFFSET_X + 5 * CELL + CELL // 2
    target.y = GRID_OFFSET_Y + 3 * CELL + CELL // 2
    g.holds = [target]
    g.player_col = 4
    g.player_row = 3
    g.grip_color = COLORS[0]
    g.stun_timer = 5
    assert g.stun_timer > 0
    assert g.player_col == 4


def test_stun_decrements() -> None:
    g = _make_game()
    g.stun_timer = 5
    g._update_playing()
    assert g.stun_timer == 4


# ── Spawn System ─────────────────────────────────────────


def test_spawn_hold() -> None:
    g = _make_game()
    g.spawn_timer = 1
    hold_count_before = len(g.holds)
    g._spawn_hold()
    assert g.spawn_timer > 0
    if hold_count_before < MAX_HOLDS:
        assert len(g.holds) == hold_count_before + 1
    for h in g.holds:
        assert h.color in COLORS
        assert 0 <= h.col < GRID_COLS
        assert 0 <= h.row < GRID_ROWS


def test_spawn_hold_at_max() -> None:
    g = _make_game()
    g.holds = []
    for _ in range(MAX_HOLDS):
        g.holds.append(Hold(col=0, row=0, color=COLORS[0]))
    g._spawn_hold()
    assert len(g.holds) == MAX_HOLDS


def test_spawn_hold_no_empty_slots() -> None:
    g = _make_game()
    g.holds = []
    for col in range(GRID_COLS):
        for row in range(GRID_ROWS):
            g.holds.append(Hold(col=col, row=row, color=COLORS[0]))
    hold_count = len(g.holds)
    g._spawn_hold()
    assert len(g.holds) == hold_count


# ── Difficulty Escalation ────────────────────────────────


def test_difficulty_escalation_start() -> None:
    g = _make_game()
    g.game_timer = GAME_DURATION
    g._update_difficulty()
    assert g.spawn_interval == SPAWN_INTERVAL_INITIAL
    assert g.color_cycle_interval == COLOR_CYCLE_INITIAL


def test_difficulty_escalation_mid() -> None:
    g = _make_game()
    g.game_timer = GAME_DURATION // 2
    g._update_difficulty()
    mid_spawn = int(SPAWN_INTERVAL_INITIAL - (SPAWN_INTERVAL_INITIAL - SPAWN_INTERVAL_MIN) * 0.5)
    assert g.spawn_interval == mid_spawn


def test_difficulty_escalation_end() -> None:
    g = _make_game()
    g.game_timer = 0
    g._update_difficulty()
    assert g.spawn_interval == SPAWN_INTERVAL_MIN
    assert g.color_cycle_interval == COLOR_CYCLE_MIN


# ── Particles ────────────────────────────────────────────


def test_update_particles_move_and_decay() -> None:
    g = _make_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=2.0, vy=-1.0, life=5, color=8)]
    g._update_particles()
    p = g.particles[0]
    assert p.x == 102.0
    assert p.y == 99.0
    assert p.vy == -0.95
    assert p.life == 4


def test_update_particles_remove_dead() -> None:
    g = _make_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=1, color=8)]
    g._update_particles()
    assert len(g.particles) == 0


def test_add_particles_match() -> None:
    g = _make_game()
    g._add_particles(100.0, 100.0, 8, 8, False)
    assert 8 <= len(g.particles) <= 8
    for p in g.particles:
        assert p.color == 8


def test_add_particles_super() -> None:
    g = _make_game()
    g._add_particles(100.0, 100.0, 8, 15, True)
    assert len(g.particles) == 15
    for p in g.particles:
        assert p.color in COLORS


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


def test_add_floating_text() -> None:
    g = _make_game()
    g._add_floating_text(100.0, 200.0, "test", 7, 30)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.x == 100.0
    assert ft.y == 200.0
    assert ft.text == "test"
    assert ft.life == 30
    assert ft.color == 7


# ── Game Over ────────────────────────────────────────────


def test_end_game() -> None:
    g = _make_game()
    g.score = 500
    g.best_score = 300
    g._end_game()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 500
    assert g.shake_frames == SHAKE_FRAMES


def test_end_game_best_score_not_beaten() -> None:
    g = _make_game()
    g.score = 200
    g.best_score = 300
    g._end_game()
    assert g.best_score == 300


def test_best_score_persists_across_resets() -> None:
    g = _make_game()
    g.score = 500
    g._end_game()
    assert g.best_score == 500
    g.reset()
    assert g.best_score == 500
    assert g.score == 0


# ── Player Position (pixel coordinates) ─────────────────


def test_player_start_position() -> None:
    g = _make_game()
    assert g.player_col == GRID_COLS // 2
    assert g.player_row == GRID_ROWS - 1
    assert g.grip_color == COLORS[0]


# ── Score Calculation ────────────────────────────────────


def test_score_calculation_normal() -> None:
    g = _make_game()
    g.player_col = 4
    g.player_row = 4
    g.grip_color = COLORS[0]
    for i in range(1, 4):
        h = Hold(col=4, row=4, color=COLORS[0])
        h.x = GRID_OFFSET_X + 4 * CELL + CELL // 2
        h.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
        g.holds = [h]
        prev = g.score
        g._move_to_hold(h)
        expected_gain = 10 * i * 1
        assert g.score == prev + expected_gain


def test_score_calculation_super() -> None:
    g = _make_game()
    g.super_timer = 100
    g.player_col = 4
    g.player_row = 4
    g.grip_color = COLORS[0]
    h = Hold(col=4, row=4, color=COLORS[0])
    h.x = GRID_OFFSET_X + 4 * CELL + CELL // 2
    h.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
    g.holds = [h]
    g._move_to_hold(h)
    assert g.score == 30


# ── Phase Transitions ────────────────────────────────────


def test_title_to_playing() -> None:
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g._pre_init()
    g.phase = Phase.TITLE
    g.best_score = 0
    g.reset()
    assert g.phase == Phase.PLAYING


def test_playing_to_game_over_timer() -> None:
    g = _make_game()
    g.game_timer = 1
    g.stun_timer = 0
    g._update_playing()
    assert g.phase == Phase.GAME_OVER


def test_playing_to_game_over_heat() -> None:
    g = _make_game()
    g.heat = HEAT_MAX + HEAT_DECAY
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


# ── Screen Shake ─────────────────────────────────────────


def test_shake_on_end_game() -> None:
    g = _make_game()
    g._end_game()
    assert g.shake_frames == SHAKE_FRAMES


# ── Integration ─────────────────────────────────────────


def test_full_match_flow() -> None:
    g = _make_game()
    g.player_col = 4
    g.player_row = 4
    g.grip_color = COLORS[0]
    h = Hold(col=4, row=4, color=COLORS[0])
    h.x = GRID_OFFSET_X + 4 * CELL + CELL // 2
    h.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
    g.holds = [h]
    g._move_to_hold(h)
    assert g.combo == 1
    assert g.score == 10
    assert len(g.particles) > 0
    assert len(g.floating_texts) > 0
    assert len(g.ghost_path) == 1


def test_full_mismatch_flow() -> None:
    g = _make_game()
    g.player_col = 4
    g.player_row = 4
    g.grip_color = COLORS[0]
    h = Hold(col=4, row=4, color=COLORS[1])
    h.x = GRID_OFFSET_X + 4 * CELL + CELL // 2
    h.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
    g.holds = [h]
    g._move_to_hold(h)
    assert g.combo == 0
    assert g.heat == HEAT_MISMATCH
    assert g.stun_timer == STUN_MISMATCH
    assert g.ghost_path == []


def test_consecutive_matches_increasing_score() -> None:
    g = _make_game()
    g.player_col = 4
    g.player_row = 4
    g.grip_color = COLORS[0]
    h = Hold(col=4, row=4, color=COLORS[0])
    h.x = GRID_OFFSET_X + 4 * CELL + CELL // 2
    h.y = GRID_OFFSET_Y + 4 * CELL + CELL // 2
    g.holds = [h]
    g._move_to_hold(h)
    assert g.score == 10

    h2 = Hold(col=4, row=3, color=COLORS[0])
    h2.x = GRID_OFFSET_X + 4 * CELL + CELL // 2
    h2.y = GRID_OFFSET_Y + 3 * CELL + CELL // 2
    g.holds = [h2]
    g._move_to_hold(h2)
    assert g.score == 30

    h3 = Hold(col=4, row=2, color=COLORS[0])
    h3.x = GRID_OFFSET_X + 4 * CELL + CELL // 2
    h3.y = GRID_OFFSET_Y + 2 * CELL + CELL // 2
    g.holds = [h3]
    g._move_to_hold(h3)
    assert g.score == 60


if __name__ == "__main__":
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=False,
    )
    sys.exit(result.returncode)
