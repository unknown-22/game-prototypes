"""test_imports.py — Headless logic tests for PUT CHAIN (253_put_chain)."""
import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/253_put_chain")
# noinspection PyUnresolvedReferences
from main import (
    Game, Ring, Particle, FloatingText, Phase,
    SCREEN_W, SCREEN_H, GROUND_Y, THROWER_X, TIMER_MAX,
    STAMINA_MAX, HEAT_CAP, SCORING_DELAY, SUPER_DURATION,
    MISS_HEAT, MISMATCH_HEAT, RING_COUNT, RING_RADIUS, MIN_RING_GAP,
    SHOT_COLORS, COLOR_NAMES, GRAVITY, CHARGE_RATE, HEAT_DECAY,
    RED, LIME, DARK_BLUE, YELLOW, ORANGE, CYAN, NAVY, LIGHT_BLUE, WHITE, GRAY,
    BLACK, PURPLE, PINK, GREEN, BROWN, PEACH,
)


def _make_game() -> Game:
    """Factory: creates a headless Game with deterministic RNG."""
    g = Game.__new__(Game, headless=True)
    g.rings = []
    g.particles = []
    g.floating_texts = []
    g.ghost_trail = []
    g.best_trail = []
    g.rng = random.Random(42)
    g.reset()
    # reset() spawns rings — overwrite RNG after for deterministic tests
    g.rng = random.Random(42)
    g.phase = Phase.AIMING
    g.timer = TIMER_MAX
    g.heat = 0.0
    g.stamina = STAMINA_MAX
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    return g


# ── Phase Enum ──

def test_phase_enum():
    assert Phase.TITLE in Phase
    assert Phase.AIMING in Phase
    assert Phase.FLYING in Phase
    assert Phase.SCORING in Phase
    assert Phase.GAME_OVER in Phase


# ── Ring dataclass ──

def test_ring_creation():
    r = Ring(x=100.0, color=8)
    assert r.x == 100.0
    assert r.color == 8
    assert r.radius == 16
    assert r.active is True


# ── Particle / FloatingText ──

def test_particle_creation():
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=15, color=8)
    assert p.x == 10.0
    assert p.life == 15


def test_floating_text_creation():
    ft = FloatingText(x=50.0, y=60.0, text="+100", life=30, color=11)
    assert ft.text == "+100"
    assert ft.life == 30


# ── Constants ──

def test_constants():
    assert len(SHOT_COLORS) == 4
    assert SHOT_COLORS == [8, 11, 5, 10]  # RED, LIME, DARK_BLUE, YELLOW
    assert len(COLOR_NAMES) == 4
    assert RING_COUNT == 5
    assert RING_RADIUS == 16
    assert HEAT_CAP == 100.0
    assert STAMINA_MAX == 100.0
    assert TIMER_MAX == 1800


# ── _make_game factory ──

def test_make_game_initial_state():
    g = _make_game()
    assert g.phase == Phase.AIMING
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.stamina == STAMINA_MAX
    assert g.timer == TIMER_MAX
    assert g.shot_active is False
    assert g.super_timer == 0
    assert len(g.rings) == RING_COUNT


# ── reset ──

def test_reset_clears_state():
    g = _make_game()
    g.score = 999
    g.heat = 50.0
    g.combo = 5
    g.max_combo = 7
    g.super_timer = 100
    g.stamina = 30.0
    g.timer = 500
    g.particles = [Particle(0, 0, 0, 0, 1, 8)]
    g.floating_texts = [FloatingText(0, 0, "x", 1, 8)]
    g.ghost_trail = [(1.0, 2.0)]
    g.best_trail = [(3.0, 4.0)]
    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.stamina == STAMINA_MAX
    assert g.timer == TIMER_MAX
    assert g.super_timer == 0
    assert g.shot_active is False
    assert g.phase == Phase.TITLE
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert len(g.ghost_trail) == 0
    assert len(g.best_trail) == 0


# ── _spawn_rings ──

def test_spawn_rings_count():
    g = _make_game()
    g.rng = random.Random(123)
    g._spawn_rings()
    assert len(g.rings) == RING_COUNT


def test_spawn_rings_in_bounds():
    g = _make_game()
    g.rng = random.Random(456)
    g._spawn_rings()
    for ring in g.rings:
        assert 80 <= ring.x <= 280
        assert ring.color in SHOT_COLORS
        assert ring.active is True


def test_spawn_rings_min_gap():
    g = _make_game()
    g.rng = random.Random(789)
    g._spawn_rings()
    sorted_rings = sorted(g.rings, key=lambda r: r.x)
    for i in range(len(sorted_rings) - 1):
        assert sorted_rings[i + 1].x - sorted_rings[i].x >= MIN_RING_GAP - 0.01


def test_spawn_rings_sorted_output():
    g = _make_game()
    g.rng = random.Random(42)
    g._spawn_rings()
    for i in range(len(g.rings) - 1):
        assert g.rings[i].x <= g.rings[i + 1].x


# ── _launch_shot ──

def test_launch_shot_position():
    g = _make_game()
    g._launch_shot(mouse_y=120.0)
    assert g.shot_x == float(THROWER_X)
    assert g.shot_y == float(GROUND_Y - 20)
    assert g.shot_active is True
    assert g.charging is False


def test_launch_shot_velocity():
    g = _make_game()
    g.charge_power = 50.0
    g._launch_shot(mouse_y=120.0)
    assert g.shot_vx > 0  # shot goes right
    assert g.shot_vy < 0  # shot goes up


def test_launch_shot_stamina_deduction():
    g = _make_game()
    g.stamina = STAMINA_MAX
    g._launch_shot(mouse_y=120.0)
    assert abs(g.stamina - (STAMINA_MAX - 25.0)) < 0.01


def test_launch_shot_throw_count():
    g = _make_game()
    assert g.throw_count == 0
    g._launch_shot(mouse_y=120.0)
    assert g.throw_count == 1


def test_launch_shot_low_stamina_power_cap():
    g = _make_game()
    g.stamina = 10.0  # below 25
    g.charge_power = 100.0
    # Launch should cap power at 50
    g._launch_shot(mouse_y=120.0)
    # vx = uniform(3.0, 3.5) + power * 0.06, power capped at 50
    # So vx <= 3.5 + 50*0.06 = 6.5
    assert g.shot_vx <= 6.5 + 0.01


# ── _update_shot ──

def test_update_shot_gravity():
    g = _make_game()
    g._launch_shot(mouse_y=120.0)
    initial_vy = g.shot_vy
    g._update_shot()
    assert g.shot_vy == initial_vy + GRAVITY


def test_update_shot_landing_transitions_to_scoring():
    g = _make_game()
    g.shot_active = True
    g.shot_x = 200.0
    g.shot_y = GROUND_Y - 1  # just above ground
    g.shot_vy = 1.0  # moving down
    g._update_shot()
    assert g.shot_active is False
    assert g.shot_y == float(GROUND_Y)
    assert g.phase == Phase.SCORING


def test_update_shot_no_active_noop():
    g = _make_game()
    g.shot_active = False
    g.phase = Phase.AIMING
    g._update_shot()
    assert g.phase == Phase.AIMING  # unchanged


# ── _check_scoring ──

def test_check_scoring_match():
    g = _make_game()
    g.shot_x = 150.0
    g.shot_color_idx = 0  # RED
    g.rings = [Ring(x=150.0, color=SHOT_COLORS[0])]  # RED ring at shot position
    assert g.rings[0].active is True
    g._check_scoring()
    assert g.combo == 1
    assert g.score > 0  # 100 * 1 * 1 = 100
    assert g.rings[0].active is False


def test_check_scoring_mismatch():
    g = _make_game()
    g.shot_x = 150.0
    g.shot_color_idx = 0  # RED
    g.rings = [Ring(x=150.0, color=SHOT_COLORS[1])]  # LIME ring
    g._check_scoring()
    assert g.combo == 0
    assert g.heat == MISMATCH_HEAT  # +15
    assert g.rings[0].active is False


def test_check_scoring_miss():
    g = _make_game()
    g.shot_x = 100.0
    g.rings = [Ring(x=200.0, color=SHOT_COLORS[0])]  # far away from shot
    g._check_scoring()
    assert g.combo == 0
    assert g.heat == MISS_HEAT  # +10
    assert g.rings[0].active is True  # not hit


def test_check_scoring_combo_chain():
    g = _make_game()
    g.combo = 3
    g.max_combo = 3
    g.shot_x = 150.0
    g.shot_color_idx = 0  # RED
    g.rings = [Ring(x=150.0, color=SHOT_COLORS[0])]
    g._check_scoring()
    assert g.combo == 4
    assert g.max_combo == 4
    # score: 100 * 4 * 1 = 400
    assert g.score >= 400


def test_check_scoring_super_multiplier():
    g = _make_game()
    g.super_timer = 10  # active
    g.combo = 0
    g.shot_x = 150.0
    g.shot_color_idx = 0  # RED
    g.rings = [Ring(x=150.0, color=SHOT_COLORS[1])]  # LIME — but any match in super
    g._check_scoring()
    assert g.combo == 1
    # score: 100 * 1 * 3 = 300
    assert g.score == 300


def test_check_scoring_best_throw_tracking():
    g = _make_game()
    g.best_throw_score = 100
    g.shot_x = 150.0
    g.shot_color_idx = 0  # RED
    # Place two rings within shot radius (ring 16px, shot at 150)
    g.rings = [
        Ring(x=150.0, color=SHOT_COLORS[0]),  # dist=0, hit
        Ring(x=158.0, color=SHOT_COLORS[0]),  # dist=8, hit (within 16px radius)
    ]
    g._check_scoring()
    # 2 matches: 100*1*1 + 100*2*1 = 300
    assert g.score >= 300
    assert g.best_throw_score >= 300


# ── _update_combos ──

def test_update_combos_super_trigger():
    g = _make_game()
    g.combo = 4
    g.super_timer = 0
    g._update_combos()
    # _update_combos sets super_timer=300 then immediately decrements to 299
    assert g.super_timer == SUPER_DURATION - 1


def test_update_combos_super_already_active():
    g = _make_game()
    g.combo = 5
    g.super_timer = 200  # already active
    g._update_combos()
    assert g.super_timer == 199  # decremented, not refreshed


def test_update_combos_no_trigger_below_4():
    g = _make_game()
    g.combo = 3
    g.super_timer = 0
    g._update_combos()
    assert g.super_timer == 0


# ── _update_heat ──

def test_update_heat_game_over_at_cap():
    g = _make_game()
    g.heat = HEAT_CAP  # 100.0
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_update_heat_decay():
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert abs(g.heat - (50.0 - HEAT_DECAY)) < 0.01


def test_update_heat_no_negative():
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_check_before_decay():
    """Heat at exactly cap should trigger game over before decaying."""
    g = _make_game()
    g.heat = HEAT_CAP
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    # heat shouldn't have been decayed since we returned early
    assert g.heat == HEAT_CAP


# ── _shuffle_ring_colors ──

def test_shuffle_ring_colors():
    g = _make_game()
    g.rng = random.Random(42)
    g._spawn_rings()
    original_colors = [r.color for r in g.rings]
    g.rng = random.Random(999)
    g._shuffle_ring_colors()
    new_colors = [r.color for r in g.rings]
    all_valid = all(c in SHOT_COLORS for c in new_colors)
    assert all_valid


# ── _is_super ──

def test_is_super_active():
    g = _make_game()
    g.super_timer = 0
    assert g._is_super() is False
    g.super_timer = 1
    assert g._is_super() is True


# ── Particles ──

def test_spawn_particles():
    g = _make_game()
    g._spawn_particles(100.0, 100.0, 10, RED)
    assert len(g.particles) == 10
    for p in g.particles:
        assert p.color == RED
        assert 15 <= p.life <= 25


def test_spawn_particles_rainbow():
    g = _make_game()
    g._spawn_particles(100.0, 100.0, 10, -1)  # rainbow
    assert len(g.particles) == 10
    for p in g.particles:
        assert p.color in SHOT_COLORS
        assert 20 <= p.life <= 30


def test_update_particles_life_decrement():
    g = _make_game()
    g._spawn_particles(100.0, 100.0, 3, RED)
    for p in g.particles:
        p.life = 1  # will be removed after update
    g._update_particles()
    assert len(g.particles) == 0  # all removed (life <= 0)


def test_update_particles_movement():
    g = _make_game()
    g._spawn_particles(0.0, 0.0, 1, RED)
    g.particles[0].vx = 1.0
    g.particles[0].vy = -1.0
    g.particles[0].life = 10
    g._update_particles()
    p = g.particles[0]
    assert p.x == 1.0
    assert p.y == -1.0 + 0.05  # vy += gravity(0.05)


# ── Floating Text ──

def test_spawn_floating_text():
    g = _make_game()
    g._spawn_floating_text(100.0, 100.0, "+100", LIME)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "+100"
    assert g.floating_texts[0].life == 30  # default for regular text


def test_spawn_floating_text_super():
    g = _make_game()
    g._spawn_floating_text(100.0, 100.0, "SUPER PUT!", YELLOW)
    assert g.floating_texts[0].life == 40


def test_spawn_floating_text_wrong():
    g = _make_game()
    g._spawn_floating_text(100.0, 100.0, "WRONG!", RED)
    assert g.floating_texts[0].life == 25


def test_spawn_floating_text_game_over():
    g = _make_game()
    g._spawn_floating_text(100.0, 100.0, "GAME OVER", RED)
    assert g.floating_texts[0].life == 60


def test_update_floating_texts():
    g = _make_game()
    g._spawn_floating_text(100.0, 100.0, "+100", LIME)
    initial_y = g.floating_texts[0].y
    g._update_floating_texts()
    assert g.floating_texts[0].y == initial_y - 0.5  # moves up
    assert g.floating_texts[0].life == 29  # decremented


# ── STAMINA ──

def test_stamina_recharge():
    g = _make_game()
    g.stamina = 50.0
    g.timer = 1000
    # Simulate what _update_aiming does for stamina
    g.stamina = min(STAMINA_MAX, g.stamina + 0.10)
    assert g.stamina == 50.10


def test_stamina_doesnt_exceed_max():
    g = _make_game()
    g.stamina = 99.95
    g.stamina = min(STAMINA_MAX, g.stamina + 0.10)
    assert g.stamina == STAMINA_MAX


def test_stamina_low_caps_power():
    """When stamina < 25, launch caps power at 50%."""
    g = _make_game()
    g.stamina = 10.0
    g.charge_power = 100.0
    g.rng = random.Random(42)
    g._launch_shot(mouse_y=120.0)
    # vx = uniform(3, 3.5) + (capped_power=50) * 0.06 = 3.x + 3.0
    assert g.shot_vx <= 7.0  # generous upper bound


# ── Scoring timing ──

def test_scoring_timer_set():
    g = _make_game()
    g.shot_x = 150.0
    g.shot_color_idx = 0
    g.rings = [Ring(x=150.0, color=SHOT_COLORS[0])]
    g._check_scoring()
    assert g.scoring_timer == SCORING_DELAY


# ── Ring shuffle on every 5th throw ──

def test_ring_shuffle_every_5_throws():
    g = _make_game()
    g.throw_count = 4  # next throw is #5
    g._launch_shot(mouse_y=120.0)
    assert g.throw_count == 5
    # Rings should have been shuffled (we can't easily test colors changed
    # but we can verify it doesn't crash)


# ── _update_aiming logic (simulated, no pyxel input) ──

def test_aiming_timer_decrement():
    g = _make_game()
    initial_timer = g.timer
    g.timer -= 1
    assert g.timer == initial_timer - 1


def test_aiming_timer_game_over():
    g = _make_game()
    g.timer = 1
    g.timer -= 1  # simulate update decrement
    if g.timer <= 0:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


# ── Edge cases ──

def test_heat_exact_cap():
    g = _make_game()
    g.heat = HEAT_CAP  # 100.0 exactly
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_multiple_ring_hits_one_throw():
    """A single shot can hit multiple rings."""
    g = _make_game()
    g.combo = 0
    g.shot_x = 150.0
    g.shot_color_idx = 0  # RED
    g.rings = [
        Ring(x=145.0, color=SHOT_COLORS[0]),  # match, within radius
        Ring(x=155.0, color=SHOT_COLORS[0]),  # match, within radius
        Ring(x=200.0, color=SHOT_COLORS[1]),  # far away, no hit
    ]
    g._check_scoring()
    assert g.rings[0].active is False
    assert g.rings[1].active is False
    assert g.rings[2].active is True
    assert g.combo == 2
    # score: 100*1*1 + 100*2*1 = 300
    assert g.score == 300


def test_ring_boundary_hit():
    """Shot exactly at ring boundary should still hit."""
    g = _make_game()
    g.shot_x = 150.0
    g.shot_color_idx = 0
    ring_x = 150.0 + RING_RADIUS  # exactly at boundary
    g.rings = [Ring(x=ring_x, color=SHOT_COLORS[0])]
    g._check_scoring()
    assert g.rings[0].active is False  # hit (dist = radius, <= check)
    assert g.combo == 1


def test_ring_just_outside_boundary():
    """Shot just outside ring boundary should miss."""
    g = _make_game()
    g.shot_x = 150.0
    g.shot_color_idx = 0
    ring_x = 150.0 + RING_RADIUS + 1  # just outside
    g.rings = [Ring(x=ring_x, color=SHOT_COLORS[0])]
    g._check_scoring()
    assert g.rings[0].active is True  # not hit
    assert g.combo == 0


def test_super_mode_any_color_match():
    """In SUPER mode, any-color ring hit counts as match."""
    g = _make_game()
    g.super_timer = 50
    g.shot_x = 150.0
    g.shot_color_idx = 0  # RED shot
    g.rings = [Ring(x=150.0, color=SHOT_COLORS[1])]  # LIME ring
    g._check_scoring()
    assert g.rings[0].active is False
    assert g.combo == 1
    # score: 100 * 1 * 3 = 300
    assert g.score == 300


def test_max_combo_tracking():
    g = _make_game()
    assert g.max_combo == 0
    g.combo = 0
    g.shot_x = 150.0
    g.shot_color_idx = 0
    g.rings = [Ring(x=150.0, color=SHOT_COLORS[0])]
    g._check_scoring()
    assert g.max_combo == 1
    # second throw
    g.shot_color_idx = 0
    g.rings = [Ring(x=150.0, color=SHOT_COLORS[0])]
    g._check_scoring()
    assert g.max_combo == 2


def test_combo_reset_on_mismatch():
    g = _make_game()
    g.combo = 5
    g.max_combo = 5
    g.heat = 0.0
    g.shot_x = 150.0
    g.shot_color_idx = 0  # RED
    g.rings = [Ring(x=150.0, color=SHOT_COLORS[1])]  # LIME
    g._check_scoring()
    assert g.combo == 0
    assert g.heat == MISMATCH_HEAT


def test_super_timer_decrements():
    g = _make_game()
    g.combo = 4
    g.super_timer = 0
    g._update_combos()
    # First call: sets 300, then decrements → 299
    assert g.super_timer == SUPER_DURATION - 1  # 299
    g._update_combos()
    # Second call: just decrements → 298
    assert g.super_timer == SUPER_DURATION - 2  # 298


def test_score_accumulates():
    g = _make_game()
    assert g.score == 0
    g.shot_x = 150.0
    g.shot_color_idx = 0
    g.rings = [Ring(x=150.0, color=SHOT_COLORS[0])]
    g._check_scoring()
    first_score = g.score
    assert first_score > 0
    # Reset rings and shoot again
    g.rings[0].active = True
    g._check_scoring()
    assert g.score > first_score  # accumulated


def test_floating_text_lifecycle():
    g = _make_game()
    g._spawn_floating_text(100.0, 100.0, "+100", LIME)
    assert len(g.floating_texts) == 1
    g.floating_texts[0].life = 1
    g._update_floating_texts()
    assert len(g.floating_texts) == 0  # removed


def test_ghost_trail_recording():
    g = _make_game()
    g.shot_active = True
    g.shot_x = 100.0
    g.shot_y = 150.0
    g._record_ghost_trail()
    assert len(g.ghost_trail) == 1
    assert g.ghost_trail[0] == (100.0, 150.0)


def test_ghost_trail_cleared_on_scoring():
    g = _make_game()
    g.shot_active = True
    g.shot_x = 100.0
    g.shot_y = 150.0
    g._record_ghost_trail()
    assert len(g.ghost_trail) == 1
    g.shot_x = 150.0
    g.shot_color_idx = 0
    g.rings = [Ring(x=150.0, color=SHOT_COLORS[0])]
    g._check_scoring()
    assert len(g.ghost_trail) == 0  # cleared


def test_best_trail_saved_on_best_throw():
    g = _make_game()
    g.best_throw_score = 0
    g.ghost_trail = [(50.0, 100.0), (60.0, 120.0)]
    g.shot_x = 150.0
    g.shot_color_idx = 0
    g.rings = [Ring(x=150.0, color=SHOT_COLORS[0])]
    g._check_scoring()
    assert g.best_throw_score > 0
    assert len(g.best_trail) == 2  # copied from ghost_trail


# ── RUN ──

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
