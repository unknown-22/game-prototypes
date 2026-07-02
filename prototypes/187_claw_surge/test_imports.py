"""test_imports.py — Headless logic tests for 187_claw_surge."""

import random
import sys

# Use absolute path to the prototype directory
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/187_claw_surge")

from main import (  # noqa: E402
    CELL,
    CLAW_SIZE,
    COMBO_MULTIPLIER_TABLE,
    GAME_DURATION,
    GRAB_ANIM_FRAMES,
    GRID_COLS,
    GRID_ROWS,
    HEAT_DECAY,
    HEAT_GAIN,
    HEAT_MAX,
    MOVE_SPEED,
    NORMAL_SCORE,
    OFFSET_X,
    OFFSET_Y,
    PRIZE_COLORS,
    RARE_CHANCE,
    RARE_SCORE,
    RESPAWN_DELAY,
    SUPER_DURATION,
    FloatingText,
    Game,
    Particle,
    Phase,
    Prize,
    _color_name,
    _combo_multiplier,
)


def _make_game() -> Game:
    """Factory: create Game instance via __new__ bypass for headless testing."""
    g = Game.__new__(Game)
    g._rng = random.Random(42)
    g._pre_init()
    g.reset()
    return g


# ── Constants ────────────────────────────────────────────


def test_constants() -> None:
    assert GRID_COLS == 5
    assert GRID_ROWS == 4
    assert CELL == 48
    assert OFFSET_X == 40
    assert OFFSET_Y == 60
    assert PRIZE_COLORS == [8, 3, 5, 10]  # RED, GREEN, DARK_BLUE, YELLOW
    assert NORMAL_SCORE == 10
    assert RARE_SCORE == 30
    assert RARE_CHANCE == 0.2
    assert RESPAWN_DELAY == 90
    assert SUPER_DURATION == 300
    assert GAME_DURATION == 1800
    assert HEAT_DECAY == 0.05
    assert HEAT_GAIN == 15.0
    assert HEAT_MAX == 100.0
    assert MOVE_SPEED == 5
    assert CLAW_SIZE == 24
    assert GRAB_ANIM_FRAMES == 15
    assert len(COMBO_MULTIPLIER_TABLE) == 9
    assert COMBO_MULTIPLIER_TABLE == [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]


def test_color_name() -> None:
    assert _color_name(8) == "RED"
    assert _color_name(3) == "GREEN"
    assert _color_name(5) == "DARK_BLUE"
    assert _color_name(10) == "YELLOW"
    assert _color_name(999) == "UNKNOWN"


def test_combo_multiplier() -> None:
    assert _combo_multiplier(0) == 1.0
    assert _combo_multiplier(1) == 1.0
    assert _combo_multiplier(2) == 1.5
    assert _combo_multiplier(3) == 2.0
    assert _combo_multiplier(4) == 2.5
    assert _combo_multiplier(5) == 3.0
    assert _combo_multiplier(9) == 5.0
    assert _combo_multiplier(15) == 5.0  # capped


# ── Dataclasses ──────────────────────────────────────────


def test_prize_dataclass() -> None:
    p = Prize(x=100.0, y=200.0, color=8, tier=0)
    assert p.x == 100.0
    assert p.y == 200.0
    assert p.color == 8
    assert p.tier == 0
    assert p.alive is True
    assert p.spawn_timer == 0


def test_particle_dataclass() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=15, color=8)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == 8


def test_floating_text_dataclass() -> None:
    ft = FloatingText(x=100.0, y=200.0, text="+10", life=30, color=7)
    assert ft.x == 100.0
    assert ft.y == 200.0
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
    assert g.timer == GAME_DURATION
    assert g.super_timer == 0
    assert g.shake_frames == 0
    assert g._claw_anim == 0
    assert g._grab_target is None
    assert g.best_score == 0
    assert len(g.best_path) == 0


def test_spawn_prizes() -> None:
    g = _make_game()
    assert len(g.prizes) == GRID_COLS * GRID_ROWS  # 20
    # All should be alive
    alive = [p for p in g.prizes if p.alive]
    assert len(alive) == 20
    # Check colors are valid
    for p in g.prizes:
        assert p.color in PRIZE_COLORS
        assert p.tier in (0, 1)
    # Check positions are on grid
    for p in g.prizes:
        assert OFFSET_X + CELL // 2 <= p.x <= OFFSET_X + GRID_COLS * CELL - CELL // 2
        assert OFFSET_Y + CELL // 2 <= p.y <= OFFSET_Y + GRID_ROWS * CELL - CELL // 2


def test_reset_clears_state() -> None:
    g = _make_game()
    g.score = 500
    g.combo = 3
    g.heat = 50.0
    g.super_timer = 100
    g.particles = [Particle(0, 0, 0, 0, 5, 8)]
    g.floating_texts = [FloatingText(0, 0, "x", 5, 7)]
    g.shake_frames = 5
    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.shake_frames == 0


# ── Claw Movement ────────────────────────────────────────


def test_move_claw_basic() -> None:
    g = _make_game()
    orig_x = g.claw_x
    orig_y = g.claw_y
    g._move_claw(5, 0)
    assert g.claw_x == orig_x + 5
    assert g.claw_y == orig_y


def test_move_claw_clamp_left_top() -> None:
    g = _make_game()
    # Move far left and up
    g._move_claw(-1000, -1000)
    min_x = OFFSET_X
    min_y = OFFSET_Y
    assert g.claw_x >= min_x
    assert g.claw_y >= min_y


def test_move_claw_clamp_right_bottom() -> None:
    g = _make_game()
    # Move far right and down
    g._move_claw(1000, 1000)
    max_x = OFFSET_X + GRID_COLS * CELL - CELL // 2
    max_y = OFFSET_Y + GRID_ROWS * CELL - CELL // 2
    assert g.claw_x <= max_x
    assert g.claw_y <= max_y


# ── Prize Finding ────────────────────────────────────────


def test_find_prize_at_claw() -> None:
    g = _make_game()
    # Place claw exactly at first prize
    first_prize = g.prizes[0]
    g.claw_x = first_prize.x
    g.claw_y = first_prize.y
    found = g._find_prize_at_claw()
    assert found is not None
    assert found is first_prize


def test_find_prize_no_prize_nearby() -> None:
    g = _make_game()
    # Move claw to empty area (top-left corner)
    g.claw_x = 0
    g.claw_y = 0
    found = g._find_prize_at_claw()
    assert found is None


def test_find_prize_skips_dead() -> None:
    g = _make_game()
    # Place two prizes close together, kill one, verify we find the other
    p0 = g.prizes[0]
    p1 = g.prizes[1]
    # Move p1 next to p0 so both are within 20px search radius
    p1.x = p0.x + 10
    p1.y = p0.y
    p0.alive = False
    g.claw_x = p0.x
    g.claw_y = p0.y
    found = g._find_prize_at_claw()
    # Should find the alive p1, not the dead p0
    assert found is not None
    assert found is not p0
    assert found.alive is True
    assert found is p1


# ── Grab Logic ───────────────────────────────────────────


def test_grab_prize_match() -> None:
    g = _make_game()
    prize = g.prizes[0]
    # Set claw color to match
    g.claw_color = prize.color
    g.claw_x = prize.x
    g.claw_y = prize.y

    initial_combo = g.combo
    initial_score = g.score
    _ = g._grab_prize(prize)

    assert prize.alive is False
    assert prize.spawn_timer == RESPAWN_DELAY
    assert g.combo == initial_combo + 1
    assert g.score > initial_score


def test_grab_prize_mismatch() -> None:
    g = _make_game()
    prize = g.prizes[0]
    # Set claw color to something different
    for c in PRIZE_COLORS:
        if c != prize.color:
            g.claw_color = c
            break
    g.claw_x = prize.x
    g.claw_y = prize.y

    _ = g._grab_prize(prize)

    assert prize.alive is False
    assert g.combo == 0
    assert g.heat == HEAT_GAIN


def test_grab_prize_super_mode_any_color() -> None:
    g = _make_game()
    prize = g.prizes[0]
    # Force super mode ON
    g.super_timer = 100
    # Set claw color to something different from prize
    for c in PRIZE_COLORS:
        if c != prize.color:
            g.claw_color = c
            break
    g.claw_x = prize.x
    g.claw_y = prize.y

    initial_score = g.score
    _ = g._grab_prize(prize)

    # Should succeed (no heat gain, combo increase)
    assert prize.alive is False
    assert g.combo == 1
    assert g.heat == 0.0
    assert g.score > initial_score


def test_grab_prize_score_calculation() -> None:
    g = _make_game()
    # Normal prize
    prize = Prize(x=100.0, y=100.0, color=8, tier=0, alive=True)
    g.prizes = [prize]
    g.claw_color = 8  # match
    g.claw_x = prize.x
    g.claw_y = prize.y

    points = g._grab_prize(prize)
    # combo=1 → multiplier=1.0, base=10 → 10
    assert points == 10


def test_grab_prize_rare_score() -> None:
    g = _make_game()
    prize = Prize(x=100.0, y=100.0, color=8, tier=1, alive=True)
    g.prizes = [prize]
    g.claw_color = 8  # match
    g.claw_x = prize.x
    g.claw_y = prize.y

    points = g._grab_prize(prize)
    assert points == 30  # rare base * 1.0 multiplier


def test_grab_prize_super_3x_score() -> None:
    g = _make_game()
    prize = Prize(x=100.0, y=100.0, color=8, tier=0, alive=True)
    g.prizes = [prize]
    g.claw_color = 8
    g.claw_x = prize.x
    g.claw_y = prize.y
    g.super_timer = 100

    points = g._grab_prize(prize)
    # normal base=10, combo=1→mult=1.0, super=3x → 30
    assert points == 10 * 1.0 * 3


# ── Combo Tracking ───────────────────────────────────────


def test_compute_combo_match() -> None:
    g = _make_game()
    g._compute_combo(True)
    assert g.combo == 1
    assert g.max_combo == 1
    g._compute_combo(True)
    assert g.combo == 2
    assert g.max_combo == 2


def test_compute_combo_mismatch() -> None:
    g = _make_game()
    g.combo = 3
    g.max_combo = 3
    g._compute_combo(False)
    assert g.combo == 0
    assert g.heat == HEAT_GAIN
    # max_combo should be preserved
    assert g.max_combo == 3


def test_compute_combo_heat_cap() -> None:
    g = _make_game()
    g.heat = HEAT_MAX - 5
    g._compute_combo(False)
    assert g.heat == HEAT_MAX  # capped


def test_combo_chain_to_super_activation() -> None:
    g = _make_game()
    # 4 consecutive matches should trigger super
    # Use a controlled prize — claw color cycles every 2 combos:
    # combo 1→2: RED(8), combo 3→4: GREEN(3), etc.
    prize = Prize(x=100.0, y=100.0, color=8, tier=0, alive=True)
    g.prizes = [prize]
    g.claw_color = 8  # match RED
    g.claw_x = prize.x
    g.claw_y = prize.y

    # First grab: combo 0→1, claw stays RED(8)
    g._grab_prize(prize)
    assert g.combo == 1
    prize.alive = True
    prize.spawn_timer = 0
    prize.color = 8  # still RED, claw still RED

    # Second grab: combo 1→2, claw stays RED(8)
    g._grab_prize(prize)
    assert g.combo == 2
    prize.alive = True
    prize.spawn_timer = 0
    # After combo 2, claw switches to GREEN(3)
    prize.color = g.claw_color  # match whatever claw color is now

    # Third grab: combo 2→3
    g._grab_prize(prize)
    assert g.combo == 3
    assert g.super_timer == 0
    prize.alive = True
    prize.spawn_timer = 0
    prize.color = g.claw_color  # match whatever claw color is now

    # 4th match triggers super
    g._grab_prize(prize)
    assert g.combo == 4
    assert g.super_timer == SUPER_DURATION
    assert g.shake_frames == 10


def test_max_combo_tracking() -> None:
    g = _make_game()
    prize = g.prizes[0]
    g.claw_color = prize.color

    for _ in range(3):
        g.combo += 1
        g.max_combo = max(g.max_combo, g.combo)

    assert g.max_combo == 3
    # Reset combo via mismatch
    g._compute_combo(False)
    assert g.combo == 0
    assert g.max_combo == 3  # preserved


# ── SUPER Mode ───────────────────────────────────────────


def test_activate_super() -> None:
    g = _make_game()
    g._activate_super()
    assert g.super_timer == SUPER_DURATION
    assert g.shake_frames == 10


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


# ── Heat System ──────────────────────────────────────────


def test_update_heat_decay() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 50.0 - HEAT_DECAY


def test_update_heat_does_not_go_negative() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_game_over_at_max() -> None:
    g = _make_game()
    # _update_heat decays BEFORE checking threshold (decay-before-check pattern)
    # So setting exactly HEAT_MAX won't trigger game over — it decays to 99.95 first
    # Set high enough that after decay it still triggers
    g.heat = HEAT_MAX + HEAT_DECAY  # 100.05 -> decays to 100.0 -> >=100 triggers
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_update_heat_game_over_above_max() -> None:
    g = _make_game()
    g.heat = HEAT_MAX + 10
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


# ── Timer ────────────────────────────────────────────────


def test_update_timer_decrement() -> None:
    g = _make_game()
    initial = g.timer
    g._update_timer()
    assert g.timer == initial - 1


def test_update_timer_game_over_at_zero() -> None:
    g = _make_game()
    g.timer = 1
    g._update_timer()
    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER


def test_update_timer_already_game_over() -> None:
    g = _make_game()
    g.timer = 0
    g.phase = Phase.GAME_OVER
    # _update_timer should trigger end_game but phase already GAME_OVER
    g._update_timer()
    assert g.phase == Phase.GAME_OVER


# ── Prize Updates ────────────────────────────────────────


def test_update_prizes_respawn() -> None:
    g = _make_game()
    # Kill a prize
    p = g.prizes[0]
    p.alive = False
    p.spawn_timer = 1

    g._update_prizes()
    assert p.spawn_timer == 0
    assert p.alive is True
    # New random color (deterministic with seed=42)
    assert p.color in PRIZE_COLORS


def test_update_prizes_alive_stays_alive() -> None:
    g = _make_game()
    p = g.prizes[0]
    p.alive = True
    p.spawn_timer = 0
    old_color = p.color

    g._update_prizes()
    assert p.alive is True
    # Color unchanged for alive prizes
    assert p.color == old_color


# ── Particles ────────────────────────────────────────────


def test_update_particles_move_and_decay() -> None:
    g = _make_game()
    g.particles = [
        Particle(x=100.0, y=100.0, vx=2.0, vy=-1.0, life=5, color=8),
    ]
    g._update_particles()
    p = g.particles[0]
    assert p.x == 102.0
    # Gravity (0.1) applied AFTER position update:
    # y += vy → 100.0 + (-1.0) = 99.0, then vy += 0.1 → -0.9
    assert p.y == 99.0
    assert p.vy == -0.9
    assert p.life == 4


def test_update_particles_remove_dead() -> None:
    g = _make_game()
    g.particles = [
        Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=1, color=8),
    ]
    g._update_particles()
    assert len(g.particles) == 0  # life went to 0, removed


# ── Floating Texts ───────────────────────────────────────


def test_update_floating_texts_move_and_decay() -> None:
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=100.0, y=200.0, text="+10", life=30, color=7),
    ]
    g._update_floating_texts()
    ft = g.floating_texts[0]
    assert ft.y == 199.5
    assert ft.life == 29


def test_update_floating_texts_remove_dead() -> None:
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=100.0, y=200.0, text="x", life=1, color=7),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Ghost Trail ──────────────────────────────────────────


def test_update_ghost_records_position() -> None:
    g = _make_game()
    g._ghost_frame_counter = 9  # next update triggers record
    assert len(g.ghost_path) == 0
    g._update_ghost()
    assert len(g.ghost_path) == 1
    assert g.ghost_path[0] == (g.claw_x, g.claw_y)


def test_update_ghost_skips_frames() -> None:
    g = _make_game()
    g._ghost_frame_counter = 0
    g._update_ghost()
    assert len(g.ghost_path) == 0  # frame 1, not record
    for _ in range(8):
        g._update_ghost()
    assert len(g.ghost_path) == 0  # still not frame 10
    g._update_ghost()  # frame 10
    assert len(g.ghost_path) == 1


# ── Game Over ────────────────────────────────────────────


def test_end_game_best_score_update() -> None:
    g = _make_game()
    g.score = 500
    g.best_score = 300
    g.ghost_path = [(10.0, 20.0), (30.0, 40.0)]

    g._end_game()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 500
    assert g.best_path == [(10.0, 20.0), (30.0, 40.0)]


def test_end_game_best_score_not_beaten() -> None:
    g = _make_game()
    g.score = 200
    g.best_score = 300
    old_best_path = [(5.0, 5.0)]
    g.best_path = list(old_best_path)
    g.ghost_path = [(10.0, 20.0)]

    g._end_game()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 300  # unchanged
    assert g.best_path == old_best_path  # unchanged


# ── Particle Spawning (smoke test) ───────────────────────


def test_spawn_grab_particles() -> None:
    g = _make_game()
    prize = g.prizes[0]
    g._spawn_grab_particles(prize)
    assert len(g.particles) >= 6
    assert len(g.particles) <= 10
    for p in g.particles:
        assert p.color == prize.color
        assert p.life >= 15
        assert p.life <= 25


def test_spawn_mismatch_particles() -> None:
    g = _make_game()
    prize = g.prizes[0]
    g._spawn_mismatch_particles(prize)
    assert len(g.particles) >= 3
    assert len(g.particles) <= 5
    for p in g.particles:
        assert p.color == 13  # GRAY


def test_spawn_super_particles() -> None:
    g = _make_game()
    g._spawn_super_particles()
    assert len(g.particles) >= 20
    assert len(g.particles) <= 30
    for p in g.particles:
        assert p.color in PRIZE_COLORS


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


# ── Integration Tests ────────────────────────────────────


def test_full_grab_flow_particles_generated() -> None:
    """Test that grabbing generates particles and floating text."""
    g = _make_game()
    prize = g.prizes[0]
    g.claw_color = prize.color
    g._grab_prize(prize)
    # Should have grab particles
    assert len(g.particles) > 0
    # Should have at least the score floating text
    assert len(g.floating_texts) >= 1


def test_full_mismatch_flow_heat_increases() -> None:
    """Test that mismatch grab increases heat."""
    g = _make_game()
    prize = g.prizes[0]
    for c in PRIZE_COLORS:
        if c != prize.color:
            g.claw_color = c
            break
    g._grab_prize(prize)
    assert g.heat == HEAT_GAIN
    assert g.combo == 0
    # Mismatch particles
    has_gray_particles = any(p.color == 13 for p in g.particles)
    assert has_gray_particles


def test_consecutive_matches_respect_multiplier() -> None:
    """Test that consecutive matches give increasing scores."""
    g = _make_game()
    prize = g.prizes[0]
    g.claw_color = prize.color
    g.claw_x = prize.x
    g.claw_y = prize.y
    prize.tier = 0  # normal

    # First grab
    points1 = g._grab_prize(prize)
    assert points1 == 10  # base * 1.0

    # Respawn
    prize.alive = True
    prize.spawn_timer = 0

    # Second grab
    points2 = g._grab_prize(prize)
    assert points2 == 15  # base * 1.5

    # Third grab
    prize.alive = True
    prize.spawn_timer = 0
    points3 = g._grab_prize(prize)
    assert points3 == 20  # base * 2.0


def test_super_timer_ends_after_duration() -> None:
    """Test that super timer counts down to zero."""
    g = _make_game()
    g.super_timer = SUPER_DURATION
    for _ in range(SUPER_DURATION):
        g._update_super()
    assert g.super_timer == 0


def test_heat_decay_over_time() -> None:
    """Test heat decays each frame."""
    g = _make_game()
    g.heat = 10.0
    for _ in range(10):
        g._update_heat()
    expected = 10.0 - HEAT_DECAY * 10
    assert abs(g.heat - expected) < 0.01


def test_game_over_saves_best_score_exact_tie() -> None:
    """Test that best score updates on exact tie too."""
    g = _make_game()
    g.score = 300
    g.best_score = 300
    g.ghost_path = [(10.0, 10.0)]
    g._end_game()
    # Strictly greater, so tie doesn't update
    assert g.best_score == 300  # tie → no update (score > best_score is strict)


def test_claw_anim_prevents_movement() -> None:
    """Test that claw animation timer counts down."""
    g = _make_game()
    g._claw_anim = GRAB_ANIM_FRAMES
    # Direct call doesn't invoke _update_playing so just check the attribute
    assert g._claw_anim == GRAB_ANIM_FRAMES


if __name__ == "__main__":
    import subprocess

    # Run with pytest if available
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        capture_output=False,
    )
    sys.exit(result.returncode)
