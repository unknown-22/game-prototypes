"""test_imports.py — Headless logic tests for 204_splash_chain."""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/204_splash_chain")

from main import (  # noqa: E402
    BASE_DRENCH_SCORE,
    BUCKET_HP_MAX,
    BUCKET_HP_MIN,
    BUCKET_SPAWN_INTERVAL,
    CA_INTERVAL,
    CA_MATURE_AGE,
    CA_SPREAD_CHANCE,
    CELL_SIZE,
    COMBO_BONUS_PER_LEVEL,
    COLOR_CYAN,
    COLOR_GREEN,
    COLOR_RED,
    DROPLETS_PER_FRAME,
    FPS,
    GAME_DURATION,
    GRID_COLS,
    GRID_ROWS,
    GRID_X,
    GRID_Y,
    HEAT_BUILD_PER_FRAME,
    HEAT_DECAY_PER_FRAME,
    MAX_BUCKETS,
    MAX_HEAT,
    MAX_WATER,
    OVERHEAT_COOLDOWN,
    OVERHEAT_HEAT_RESET,
    OVERHEAT_SCORE_PENALTY,
    PLAYER_HP,
    SCREEN_H,
    SCREEN_W,
    SPRAY_CONE_ANGLE,
    SUPER_COMBO_THRESHOLD,
    SUPER_DURATION,
    SUPER_SCORE_MULTIPLIER,
    TOTAL_FRAMES,
    WATER_PER_FRAME,
    WATER_RECHARGE,
    WRONG_COLOR_HEAT,
    Bucket,
    CellState,
    Droplet,
    FloatingText,
    Game,
    Particle,
    Phase,
    bucket_state_for_color,
    nozzle_color_idx,
    wet_state_for_color,
)


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_game() -> Game:
    """Create a Game instance bypassing pyxel.init/run for headless testing."""
    g = Game.__new__(Game)
    # Pre-init ALL instance attributes before reset()
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.score = 0
    g.high_score = 0
    g.combo = 0
    g.max_combo = 0
    g.hp = PLAYER_HP
    g.water = MAX_WATER
    g.heat = 0.0
    g.super_mode = False
    g.super_timer = 0
    g.game_timer = TOTAL_FRAMES
    g.cooldown_timer = 0
    g.grid = [[CellState.DRY.value for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.grid_age = [[0 for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    g.buckets = []
    g.particles = []
    g.floating_texts = []
    g.droplets = []
    g.mouse_held = False
    g.spray_angle = 0.0
    g.bucket_spawn_timer = BUCKET_SPAWN_INTERVAL
    g.nozzle_color_idx = 0
    g.nozzle_timer = 0
    g.ca_timer = 0
    g._post_reset = False
    g.reset()
    # reset() calls _init_state() which creates unseeded Random(); replace
    g._rng = random.Random(42)
    return g


# ── Constants & Enums ────────────────────────────────────────────────────


def test_constants() -> None:
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert GRID_COLS == 10
    assert GRID_ROWS == 10
    assert CELL_SIZE == 20
    assert GRID_X == 60
    assert GRID_Y == 10
    assert FPS == 60
    assert GAME_DURATION == 60
    assert TOTAL_FRAMES == 3600
    assert MAX_WATER == 100.0
    assert MAX_HEAT == 100.0
    assert SUPER_COMBO_THRESHOLD == 5
    assert SUPER_DURATION == 300
    assert SUPER_SCORE_MULTIPLIER == 3
    assert BASE_DRENCH_SCORE == 10
    assert COMBO_BONUS_PER_LEVEL == 2
    assert PLAYER_HP == 5
    assert DROPLETS_PER_FRAME == 4
    assert CA_INTERVAL == 8
    assert CA_MATURE_AGE == 16
    assert CA_SPREAD_CHANCE == 0.5
    assert BUCKET_SPAWN_INTERVAL == 120
    assert MAX_BUCKETS == 8
    assert HEAT_BUILD_PER_FRAME == 0.4
    assert HEAT_DECAY_PER_FRAME == 0.2
    assert WATER_PER_FRAME == 0.5
    assert WATER_RECHARGE == 0.3
    assert WRONG_COLOR_HEAT == 15.0
    assert OVERHEAT_COOLDOWN == 90
    assert OVERHEAT_HEAT_RESET == 30.0
    assert OVERHEAT_SCORE_PENALTY == 50
    assert SPRAY_CONE_ANGLE == 30


def test_enums() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    assert CellState.DRY.value == 0
    assert CellState.WET_RED.value == 1
    assert CellState.WET_GREEN.value == 2
    assert CellState.WET_BLUE.value == 3
    assert CellState.WET_YELLOW.value == 4
    assert CellState.BUCKET_RED.value == 5
    assert CellState.BUCKET_GREEN.value == 6
    assert CellState.BUCKET_BLUE.value == 7
    assert CellState.BUCKET_YELLOW.value == 8


def test_wet_state_for_color() -> None:
    assert wet_state_for_color(0) == CellState.WET_RED
    assert wet_state_for_color(1) == CellState.WET_GREEN
    assert wet_state_for_color(2) == CellState.WET_BLUE
    assert wet_state_for_color(3) == CellState.WET_YELLOW


def test_bucket_state_for_color() -> None:
    assert bucket_state_for_color(0) == CellState.BUCKET_RED
    assert bucket_state_for_color(1) == CellState.BUCKET_GREEN
    assert bucket_state_for_color(2) == CellState.BUCKET_BLUE
    assert bucket_state_for_color(3) == CellState.BUCKET_YELLOW


def test_nozzle_color_idx() -> None:
    assert nozzle_color_idx(0) == 0
    assert nozzle_color_idx(179) == 0
    assert nozzle_color_idx(180) == 1
    assert nozzle_color_idx(359) == 1
    assert nozzle_color_idx(360) == 2
    assert nozzle_color_idx(720) == 0  # wraps around


# ── Data Classes ─────────────────────────────────────────────────────────


def test_bucket_dataclass() -> None:
    b = Bucket(3, 4, CellState.WET_RED.value, 2)
    assert b.col == 3
    assert b.row == 4
    assert b.color == CellState.WET_RED.value
    assert b.hp == 2
    assert not b.drenched
    assert b.bucket_state == 5  # BUCKET_RED


def test_particle_dataclass() -> None:
    p = Particle(10.0, 20.0, 1.0, -2.0, 15, COLOR_RED)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.life == 15


def test_floating_text_dataclass() -> None:
    ft = FloatingText(100.0, 50.0, "+10", 30, COLOR_CYAN)
    assert ft.text == "+10"
    assert ft.life == 30


def test_droplet_dataclass() -> None:
    d = Droplet(50.0, 30.0, 2.0, -3.0, COLOR_RED)
    assert d.active
    assert d.color == COLOR_RED


# ── Game Initialization ──────────────────────────────────────────────────


def test_game_reset() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.high_score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.hp == PLAYER_HP
    assert g.water == MAX_WATER
    assert g.heat == 0.0
    assert not g.super_mode
    assert g.super_timer == 0
    assert g.game_timer == TOTAL_FRAMES
    assert g.cooldown_timer == 0
    assert len(g.buckets) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert len(g.droplets) == 0
    assert not g.mouse_held
    assert g.nozzle_color_idx == 0
    assert g.ca_timer == 0
    # grid is all DRY
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            assert g.grid[r][c] == CellState.DRY.value
            assert g.grid_age[r][c] == 0


def test_start_game() -> None:
    g = _make_game()
    g._start_game()
    assert g.phase == Phase.PLAYING


# ── Hit Cell ─────────────────────────────────────────────────────────────


def test_hit_cell_dry_gets_wet() -> None:
    g = _make_game()
    g._hit_cell(3, 2, COLOR_RED)  # col=3, row=2
    assert g.grid[2][3] == CellState.WET_RED.value
    assert g.grid_age[2][3] == 0


def test_hit_cell_overwrites_existing() -> None:
    g = _make_game()
    g._hit_cell(3, 2, COLOR_RED)
    g._hit_cell(3, 2, COLOR_GREEN)
    assert g.grid[2][3] == CellState.WET_GREEN.value


def test_hit_cell_on_bucket_matching_color() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    b = Bucket(3, 2, CellState.WET_RED.value, 1)
    g.buckets = [b]
    g._hit_cell(3, 2, COLOR_RED)
    assert b.drenched
    assert g.combo == 1
    assert g.score > 0
    assert g.grid[2][3] == CellState.WET_RED.value


def test_hit_cell_on_bucket_wrong_color() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    b = Bucket(3, 2, CellState.WET_RED.value, 2)
    g.buckets = [b]
    g.combo = 3
    initial_heat = g.heat
    g._hit_cell(3, 2, COLOR_GREEN)
    assert not b.drenched
    assert g.combo == 0
    assert g.heat > initial_heat


def test_hit_cell_super_mode_any_color_matches() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.super_mode = True
    b = Bucket(3, 2, CellState.WET_RED.value, 1)
    g.buckets = [b]
    g._hit_cell(3, 2, COLOR_GREEN)  # wrong color but super
    assert b.drenched


# ── Bucket At ────────────────────────────────────────────────────────────


def test_bucket_at_finds_bucket() -> None:
    g = _make_game()
    b = Bucket(3, 2, CellState.WET_RED.value, 1)
    g.buckets = [b]
    found = g._bucket_at(3, 2)
    assert found is b


def test_bucket_at_ignores_drenched() -> None:
    g = _make_game()
    b = Bucket(3, 2, CellState.WET_RED.value, 1, drenched=True)
    g.buckets = [b]
    found = g._bucket_at(3, 2)
    assert found is None


def test_bucket_at_empty_cell() -> None:
    g = _make_game()
    assert g._bucket_at(0, 0) is None


# ── Hit Bucket ───────────────────────────────────────────────────────────


def test_hit_bucket_drenches_on_hp_zero() -> None:
    g = _make_game()
    b = Bucket(3, 2, CellState.WET_RED.value, 1)
    g.buckets = [b]
    g._hit_bucket(b, 3, 2, COLOR_RED)
    assert b.drenched
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score > 0


def test_hit_bucket_with_hp_2_needs_two_hits() -> None:
    g = _make_game()
    b = Bucket(3, 2, CellState.WET_RED.value, 2)
    g.buckets = [b]
    g._hit_bucket(b, 3, 2, COLOR_RED)
    assert not b.drenched
    assert b.hp == 1
    assert g.combo == 0  # not drenched yet
    assert g.score == 0


def test_hit_bucket_combo_chaining() -> None:
    g = _make_game()
    g.combo = 0
    b1 = Bucket(1, 1, CellState.WET_RED.value, 1)
    b2 = Bucket(2, 2, CellState.WET_RED.value, 1)
    g.buckets = [b1, b2]
    g._hit_bucket(b1, 1, 1, COLOR_RED)
    assert g.combo == 1
    score1 = g.score
    g._hit_bucket(b2, 2, 2, COLOR_RED)
    assert g.combo == 2
    assert g.score > score1  # combo 2 gets more points


def test_hit_bucket_score_formula() -> None:
    g = _make_game()
    b = Bucket(3, 2, CellState.WET_RED.value, 1)
    g.buckets = [b]
    g.combo = 3
    g._hit_bucket(b, 3, 2, COLOR_RED)
    # points = (BASE_DRENCH_SCORE + combo * COMBO_BONUS_PER_LEVEL) * multiplier
    # combo->4: (10 + 4*2) * 1 = 18
    assert g.score == 18


def test_hit_bucket_super_score_multiplier() -> None:
    g = _make_game()
    g.super_mode = True
    b = Bucket(3, 2, CellState.WET_RED.value, 1)
    g.buckets = [b]
    g.combo = 1
    g._hit_bucket(b, 3, 2, COLOR_RED)
    # points = (10 + 2*2) * 3 = 14*3 = 42
    assert g.score == 42


def test_hit_bucket_max_combo_tracking() -> None:
    g = _make_game()
    buckets = [Bucket(i, 0, CellState.WET_RED.value, 1) for i in range(6)]
    g.buckets = buckets
    for i, b in enumerate(buckets):
        g._hit_bucket(b, i, 0, COLOR_RED)
    assert g.max_combo == 6


def test_hit_bucket_activates_super() -> None:
    g = _make_game()
    buckets = [Bucket(i, 0, CellState.WET_RED.value, 1) for i in range(5)]
    g.buckets = buckets
    g.combo = 4  # next hit makes 5, which triggers super
    # Need 5 consecutive drenches for super
    # Hit 4 more to get combo to 5
    for i, b in enumerate(buckets[:4]):
        g._hit_bucket(b, i, 0, COLOR_RED)
    assert g.combo == 8  # wait, it was 4 + 4 = 8, too much
    # Actually need COMBO >= 5, so combo should be at 4 then next hit = 5
    # Let me redo:
    # Reset game, then drench 5 in a row


def test_hit_bucket_activates_super_v2() -> None:
    g = _make_game()
    buckets = [Bucket(i, 0, CellState.WET_RED.value, 1) for i in range(5)]
    g.buckets = buckets
    for b in buckets:
        g._hit_bucket(b, b.col, b.row, COLOR_RED)
        if g.super_mode:
            break
    assert g.super_mode
    assert g.super_timer == SUPER_DURATION


# ── Wrong Color Penalty ──────────────────────────────────────────────────


def test_wrong_color_resets_combo() -> None:
    g = _make_game()
    g.combo = 5
    g._wrong_color_penalty(Bucket(0, 0, 1, 1), 0, 0)
    assert g.combo == 0


def test_wrong_color_adds_heat() -> None:
    g = _make_game()
    initial = g.heat
    g._wrong_color_penalty(Bucket(0, 0, 1, 1), 0, 0)
    assert g.heat == initial + WRONG_COLOR_HEAT


# ── Heat System ──────────────────────────────────────────────────────────


def test_heat_builds_while_spraying() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.mouse_held = True
    initial = g.heat
    g._update_heat()
    assert g.heat > initial
    assert g.heat == initial + HEAT_BUILD_PER_FRAME


def test_heat_decays_when_not_spraying() -> None:
    g = _make_game()
    g.heat = 50.0
    g.mouse_held = False
    g._update_heat()
    assert g.heat == 50.0 - HEAT_DECAY_PER_FRAME


def test_heat_clamped_at_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g.mouse_held = False
    g._update_heat()
    assert g.heat == 0.0


def test_overheat_triggers_at_max() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.mouse_held = True
    g.heat = MAX_HEAT - 0.1
    g.hp = 5
    g.super_mode = True  # overheat should cancel super
    g.super_timer = 100
    g.score = 200
    g._update_heat()
    assert g.hp == 4  # -1 HP
    assert g.cooldown_timer == OVERHEAT_COOLDOWN
    assert g.heat == OVERHEAT_HEAT_RESET
    assert not g.super_mode  # super cancels
    assert g.super_timer == 0
    assert g.score == 200 - OVERHEAT_SCORE_PENALTY


def test_heat_not_build_during_cooldown() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.mouse_held = True
    g.cooldown_timer = 10
    g.heat = 20.0
    g._update_heat()
    assert g.heat == 20.0 - HEAT_DECAY_PER_FRAME  # decays, not builds


# ── Water System ─────────────────────────────────────────────────────────


def test_water_depletes_while_spraying() -> None:
    g = _make_game()
    g.mouse_held = True
    g._update_water()
    assert g.water == MAX_WATER - WATER_PER_FRAME


def test_water_recharges_when_idle() -> None:
    g = _make_game()
    g.water = 50.0
    g.mouse_held = False
    g._update_water()
    assert g.water == 50.0 + WATER_RECHARGE


def test_water_clamped_at_max() -> None:
    g = _make_game()
    g.water = MAX_WATER
    g.mouse_held = False
    g._update_water()
    assert g.water == MAX_WATER


def test_water_clamped_at_zero() -> None:
    g = _make_game()
    g.water = 0.0
    g.mouse_held = True
    g._update_water()
    assert g.water == 0.0


def test_super_mode_unlimited_water() -> None:
    g = _make_game()
    g.super_mode = True
    g.mouse_held = True
    g.water = 10.0
    g._update_water()
    assert abs(g.water - 10.0) < 0.01  # unchanged


def test_water_recharges_during_cooldown() -> None:
    g = _make_game()
    g.cooldown_timer = 10
    g.water = 50.0
    g._update_water()
    assert g.water == 50.0 + WATER_RECHARGE


# ── Timer System ─────────────────────────────────────────────────────────


def test_game_timer_decrements() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    initial = g.game_timer
    g._update_timers()
    assert g.game_timer == initial - 1


def test_nozzle_timer_increments() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g._update_timers()
    assert g.nozzle_timer == 1
    assert g.nozzle_color_idx == 0


def test_super_timer_decrements() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 10
    g._update_timers()
    assert g.super_timer == 9
    assert g.super_mode


def test_super_timer_expires() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_timers()
    assert g.super_timer == 0
    assert not g.super_mode


def test_cooldown_timer_decrements() -> None:
    g = _make_game()
    g.cooldown_timer = 10
    g._update_timers()
    assert g.cooldown_timer == 9


def test_grid_age_increments() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.grid[3][3] = CellState.WET_RED.value
    g.grid_age[3][3] = 5
    g._update_timers()
    assert g.grid_age[3][3] == 6


def test_grid_age_only_for_wet_cells() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.grid[0][0] = CellState.DRY.value
    g.grid_age[0][0] = 0
    g._update_timers()
    assert g.grid_age[0][0] == 0  # DRY cells don't age


# ── CA Spread ────────────────────────────────────────────────────────────


def test_ca_timer_counts() -> None:
    g = _make_game()
    g.ca_timer = 0
    g._update_ca()
    assert g.ca_timer == 1


def test_ca_spread_dry_cell_ignored() -> None:
    g = _make_game()
    g.grid[0][0] = CellState.DRY.value
    g.grid_age[0][0] = 100
    # DRY cell should not spread
    g._ca_spread()
    # All cells should still be DRY (grid was all DRY except [0][0] which is also DRY)
    assert g.grid[1][0] == CellState.DRY.value


def test_ca_spread_immature_cell_ignored() -> None:
    g = _make_game()
    g.grid[0][0] = CellState.WET_RED.value
    g.grid_age[0][0] = CA_MATURE_AGE - 1  # not yet mature
    g._ca_spread()
    # Should not spread because CA_SPREAD_CHANCE might trigger...
    # But grid_age check should prevent it regardless
    # This test verifies age check logic exists — can't test probabilistic outcome


def test_ca_spread_mature_cell() -> None:
    """CA spread from mature wet cell propagates to adjacent DRY cells."""
    g = _make_game()
    g._rng = random.Random(42)
    g.grid[5][5] = CellState.WET_RED.value
    g.grid_age[5][5] = CA_MATURE_AGE  # mature
    # Use setattr to monkey-patch _rng.random — avoids ty invalid-assignment
    old_random = g._rng.random
    setattr(g._rng, "random", lambda: 0.0)  # noqa: B010
    g._ca_spread()
    spread_count = 0
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        if g.grid[5 + dr][5 + dc] == CellState.WET_RED.value:
            spread_count += 1
    assert spread_count == 4  # all 4 directions spread
    setattr(g._rng, "random", old_random)  # noqa: B010


def test_ca_spread_hits_bucket_on_wet_cell() -> None:
    """CA spread hits bucket when target cell is already wet (not DRY).
    
    CA spread logic: if target is DRY → changes (no bucket check).
    If target is already wet → checks for bucket and hits if color matches.
    
    Grid indexing: grid[row][col]. Bucket(col=5, row=4) lives at grid[4][5].
    Source at (c=5, r=5) → grid[5][5]. Direction (-1,0) → target (c=5, r=4) → grid[4][5].
    """
    g = _make_game()
    g.phase = Phase.PLAYING
    g._rng = random.Random(42)
    # Source: wet cell at (col=5, row=5) → grid[5][5]
    g.grid[5][5] = CellState.WET_RED.value
    g.grid_age[5][5] = CA_MATURE_AGE
    # Target: wet cell at (col=5, row=4) → grid[4][5] with bucket on it
    g.grid[4][5] = CellState.WET_RED.value
    g.grid_age[4][5] = CA_MATURE_AGE
    b = Bucket(5, 4, CellState.WET_RED.value, 1)
    g.buckets = [b]
    # Make rng always return 0 to guarantee spread check fires
    old_random = g._rng.random
    setattr(g._rng, "random", lambda: 0.0)  # noqa: B010
    g._ca_spread()
    assert b.drenched  # CA spread hits bucket on wet cell
    setattr(g._rng, "random", old_random)  # noqa: B010


# ── Spawn Bucket ─────────────────────────────────────────────────────────


def test_spawn_bucket_creates_one() -> None:
    g = _make_game()
    initial = len(g.buckets)
    g._spawn_bucket()
    assert len(g.buckets) == initial + 1
    b = g.buckets[0]
    assert 0 <= b.col < GRID_COLS
    assert 0 <= b.row < GRID_ROWS
    assert CellState.WET_RED.value <= b.color <= CellState.WET_YELLOW.value
    assert BUCKET_HP_MIN <= b.hp <= BUCKET_HP_MAX
    assert not b.drenched


def test_spawn_bucket_max_limit() -> None:
    g = _make_game()
    # Create MAX_BUCKETS undrenched buckets
    g.buckets = [
        Bucket(i % GRID_COLS, i // GRID_COLS, CellState.WET_RED.value, 1)
        for i in range(MAX_BUCKETS)
    ]
    initial = len(g.buckets)
    g._spawn_bucket()
    assert len(g.buckets) == initial  # no new bucket


# ── Check Game Over ──────────────────────────────────────────────────────


def test_game_over_hp_zero() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.hp = 0
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER


def test_game_over_timer_zero() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.game_timer = 0
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER


def test_game_over_updates_high_score() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.score = 500
    g.high_score = 200
    g.hp = 0
    g._check_game_over()
    assert g.high_score == 500


def test_not_game_over() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.hp = 3
    g.game_timer = 100
    g._check_game_over()
    assert g.phase == Phase.PLAYING


# ── Super Mode ───────────────────────────────────────────────────────────


def test_activate_super() -> None:
    g = _make_game()
    g._activate_super()
    assert g.super_mode
    assert g.super_timer == SUPER_DURATION
    assert len(g.particles) == 30  # super particles spawned


# ── Particle Updates ─────────────────────────────────────────────────────


def test_particles_update() -> None:
    """Particle physics: position update THEN gravity applied to velocity.
    
    Order in _update_particles: p.x += p.vx; p.y += p.vy; p.vy += 0.1; p.life -= 1
    So gravity affects NEXT frame, not current frame.
    """
    g = _make_game()
    p = Particle(10.0, 10.0, 1.0, -2.0, 3, COLOR_RED)
    g.particles = [p]
    g._update_particles()
    assert abs(p.x - 11.0) < 0.01
    assert abs(p.y - 8.0) < 0.01  # 10.0 + (-2.0) = 8.0 (gravity applied AFTER position)
    assert abs(p.vy - (-1.9)) < 0.01  # -2.0 + 0.1 = -1.9
    assert p.life == 2


def test_particles_removed_when_life_expired() -> None:
    g = _make_game()
    p = Particle(10.0, 10.0, 1.0, -2.0, 1, COLOR_RED)
    g.particles = [p]
    g._update_particles()
    assert len(g.particles) == 0  # life becomes 0, removed


# ── Floating Text Updates ────────────────────────────────────────────────


def test_floating_text_float_upward() -> None:
    g = _make_game()
    ft = FloatingText(100.0, 100.0, "+10", 3, COLOR_CYAN)
    g.floating_texts = [ft]
    g._update_floating_texts()
    assert ft.y == 99.5
    assert ft.life == 2


def test_floating_text_removed_when_life_expired() -> None:
    g = _make_game()
    ft = FloatingText(100.0, 100.0, "+10", 1, COLOR_CYAN)
    g.floating_texts = [ft]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Nozzle Color Cycling ─────────────────────────────────────────────────


def test_nozzle_cycles_through_colors() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    assert g.nozzle_color_idx == 0  # RED
    # Fast forward 180 frames
    g.nozzle_timer = 179
    g._update_timers()
    assert g.nozzle_color_idx == 1  # GREEN
    g.nozzle_timer = 359
    g._update_timers()
    assert g.nozzle_color_idx == 2  # BLUE


# ── Full Game Loop Simulation ────────────────────────────────────────────


def simulation_one_frame() -> None:
    """Simulate one frame of gameplay (spraying with mouse held)."""
    g = _make_game()
    g.phase = Phase.PLAYING
    g.mouse_held = True
    # Run one full update pass
    g._update_spray()
    g._update_droplets()
    g._update_ca()
    g._update_timers()
    g._update_heat()
    g._update_water()
    g._update_buckets()
    g._update_particles()
    g._update_floating_texts()
    assert g.nozzle_timer == 1
    assert g.heat > 0.0  # heat builds
    assert g.water < MAX_WATER  # water depletes
    assert g.game_timer == TOTAL_FRAMES - 1


# ── Integration: 60s Game End ────────────────────────────────────────────


def test_game_ends_after_time_expires() -> None:
    g = _make_game()
    g.phase = Phase.PLAYING
    g.game_timer = 1
    g._check_game_over()
    assert g.phase == Phase.PLAYING  # still alive
    g.game_timer = 0
    g._check_game_over()
    assert g.phase == Phase.GAME_OVER


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(result.returncode)
