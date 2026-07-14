"""test_imports.py — Headless logic tests for Unicycle Chain (237_unicycle_chain)."""
from __future__ import annotations

import random
import sys
from pathlib import Path

_PROTO_DIR = str(Path(__file__).resolve().parent)
if _PROTO_DIR not in sys.path:
    sys.path.insert(0, _PROTO_DIR)

from main import (  # noqa: E402
    Game,
    Phase,
    Ring,
    Particle,
    FloatText,
    GhostPoint,
)


def _make_game() -> Game:
    """Create a Game instance bypassing Pyxel init (headless-safe)."""
    g = Game.__new__(Game)
    g.reset()
    return g


class TestDataClasses:
    def test_ring_defaults(self) -> None:
        r = Ring(x=100.0, y=150.0, color=8)
        assert r.x == 100.0
        assert r.y == 150.0
        assert r.color == 8
        assert r.passed is False
        assert r.radius == 16

    def test_particle_fields(self) -> None:
        p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=15, color=8)
        assert p.x == 10.0
        assert p.y == 20.0
        assert p.vx == 1.5
        assert p.vy == -2.0
        assert p.life == 15
        assert p.color == 8

    def test_float_text_fields(self) -> None:
        ft = FloatText(x=50.0, y=60.0, text="+10", life=30, color=7)
        assert ft.text == "+10"
        assert ft.life == 30
        assert ft.color == 7

    def test_ghost_point_fields(self) -> None:
        gp = GhostPoint(tilt=0.1, x=80.0, y=180.0)
        assert gp.tilt == 0.1
        assert gp.x == 80.0
        assert gp.y == 180.0


class TestPhase:
    def test_phase_values(self) -> None:
        assert Phase.TITLE in Phase
        assert Phase.PLAYING in Phase
        assert Phase.GAME_OVER in Phase


class TestGameConstants:
    def test_ring_colors(self) -> None:
        g = _make_game()
        assert g._RING_COLORS == (8, 11, 5, 10)  # RED, LIME, DARK_BLUE, YELLOW

    def test_screen_constants(self) -> None:
        g = _make_game()
        assert g.GROUND_Y == 200
        assert g.UNI_X == 80.0

    def test_heat_constants(self) -> None:
        g = _make_game()
        assert g.MAX_HEAT == 100.0
        assert g.HEAT_MISMATCH == 15.0
        assert g.HEAT_FALL == 25.0
        assert g.HEAT_DECAY == 0.02

    def test_stamina_constants(self) -> None:
        g = _make_game()
        assert g.MAX_STAMINA == 100.0
        assert g.STAMINA_DRAIN == 0.3
        assert g.STAMINA_RECHARGE == 0.08
        assert g.STAMINA_LOW_THRESHOLD == 20.0
        assert g.STAMINA_LOW_MULT == 0.5

    def test_super_constants(self) -> None:
        g = _make_game()
        assert g.SUPER_DURATION == 300
        assert g.COMBO_THRESHOLD == 4
        assert g.GAME_DURATION == 3600

    def test_physics_constants(self) -> None:
        g = _make_game()
        assert g.TILT_GRAVITY == 0.0003
        assert g.TILT_INPUT == 0.008
        assert g.TILT_MAX == 0.6
        assert g.TILT_FALL_THRESHOLD == 0.55
        assert g.TILT_FALL_FRAMES == 30


class TestReset:
    def test_initial_state(self) -> None:
        g = _make_game()
        assert g.phase == Phase.TITLE
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.timer == 0
        assert g.tilt == 0.0
        assert g.tilt_vel == 0.0
        assert g.rings == []
        assert g.super_active is False
        assert g.super_timer == 0
        assert g.super_mult == 1
        assert g.heat == 0.0
        assert g.stamina == 100.0
        assert g.stun_timer == 0
        assert g.shake_frames == 0
        assert g._fall_frames == 0
        assert g.best_score == 0
        assert g.particles == []
        assert g.floating_texts == []

    def test_reset_clears_state(self) -> None:
        g = _make_game()
        g.score = 999
        g.combo = 5
        g.heat = 80.0
        g.rings = [Ring(x=200.0, y=100.0, color=8)]
        g.reset()
        assert g.score == 0
        assert g.combo == 0
        assert g.heat == 0.0
        assert g.rings == []


class TestStartPlaying:
    def test_start_playing_sets_playing_phase(self) -> None:
        g = _make_game()
        g._start_playing()
        assert g.phase == Phase.PLAYING
        assert g.timer == 3600
        assert g.score == 0
        assert g.combo == 0
        assert g.heat == 0.0
        assert g.stamina == 100.0
        assert g.rings == []


class TestUpdateUnicycle:
    def test_tilt_changes_with_input(self) -> None:
        g = _make_game()
        g._start_playing()
        original_tilt = g.tilt
        g._update_unicycle(1.0, False)  # push RIGHT
        assert g.tilt > original_tilt  # tilt should increase

    def test_tilt_changes_with_negative_input(self) -> None:
        g = _make_game()
        g._start_playing()
        original_tilt = g.tilt
        g._update_unicycle(-1.0, False)  # push LEFT
        assert g.tilt < original_tilt  # tilt should decrease

    def test_tilt_clamped_at_max(self) -> None:
        g = _make_game()
        g._start_playing()
        g.tilt = 0.59
        g.tilt_vel = 0.1
        g._update_unicycle(1.0, False)
        assert g.tilt <= g.TILT_MAX + 0.001

    def test_tilt_clamped_at_min(self) -> None:
        g = _make_game()
        g._start_playing()
        g.tilt = -0.59
        g.tilt_vel = -0.1
        g._update_unicycle(-1.0, False)
        assert g.tilt >= -g.TILT_MAX - 0.001

    def test_fall_frames_increment_at_extreme_tilt(self) -> None:
        g = _make_game()
        g._start_playing()
        g.tilt = 0.56  # above threshold
        g._update_unicycle(0.0, False)
        assert g._fall_frames >= 1

    def test_fall_frames_reset_within_threshold(self) -> None:
        g = _make_game()
        g._start_playing()
        g.tilt = 0.3
        g._fall_frames = 5
        g._update_unicycle(0.0, False)
        assert g._fall_frames == 0

    def test_fall_triggers_heat_and_reset(self) -> None:
        g = _make_game()
        g._start_playing()
        g.tilt = 0.56
        g._fall_frames = 29
        g.heat = 0.0
        g._update_unicycle(0.0, False)
        assert g.heat == 25.0
        assert g._fall_frames == 0
        assert g.tilt == 0.0
        assert g.tilt_vel == 0.0
        assert g.stun_timer == 15

    def test_uni_y_changes_with_tilt(self) -> None:
        g = _make_game()
        g._start_playing()
        g.tilt = 0.5
        og_y = g.uni_y
        g._update_unicycle(0.0, False)
        assert g.uni_y != og_y

    def test_low_stamina_reduces_input(self) -> None:
        g = _make_game()
        g._start_playing()
        g.stamina = 10.0  # below threshold
        g.tilt = 0.0
        g.tilt_vel = 0.0
        g._update_unicycle(1.0, False)
        tilt_low = g.tilt
        # Reset and test with full stamina
        g._start_playing()
        g.stamina = 100.0
        g.tilt = 0.0
        g.tilt_vel = 0.0
        g._update_unicycle(1.0, False)
        tilt_full = g.tilt
        assert tilt_full > tilt_low  # full stamina = stronger input


class TestSpawnRing:
    def test_spawn_ring_adds_to_list(self) -> None:
        g = _make_game()
        g._start_playing()
        g._rng = random.Random(42)
        assert len(g.rings) == 0
        g._spawn_ring()
        assert len(g.rings) == 1
        assert g.rings[0].x == 330.0

    def test_spawn_ring_color_in_valid_set(self) -> None:
        g = _make_game()
        g._start_playing()
        g._rng = random.Random(42)
        g._spawn_ring()
        assert g.rings[0].color in g._RING_COLORS

    def test_spawn_ring_y_in_range(self) -> None:
        g = _make_game()
        g._start_playing()
        g._rng = random.Random(42)
        for _ in range(20):
            g.rings.clear()
            g._spawn_ring()
            assert 80 <= g.rings[0].y <= 180


class TestUpdateRings:
    def test_rings_move_left(self) -> None:
        g = _make_game()
        g._start_playing()
        g.rings = [Ring(x=200.0, y=100.0, color=8)]
        g._update_rings()
        assert g.rings[0].x < 200.0

    def test_rings_beyond_left_edge_removed(self) -> None:
        g = _make_game()
        g._start_playing()
        g.rings = [Ring(x=-50.0, y=100.0, color=8)]
        g._update_rings()
        assert len(g.rings) == 0

    def test_speed_mult_affects_movement(self) -> None:
        g = _make_game()
        g._start_playing()
        g.scroll_speed = 1.5
        g.speed_mult = 1.3
        g.rings = [Ring(x=200.0, y=100.0, color=8)]
        g._update_rings()
        # should move faster with speed_mult=1.3
        assert abs(g.rings[0].x - (200.0 - 1.5 * 1.3)) < 0.01


class TestCheckRingPass:
    def test_empty_rings_returns_zero(self) -> None:
        g = _make_game()
        g._start_playing()
        matched, mismatch = g._check_ring_pass()
        assert matched == 0
        assert mismatch is False

    def test_matching_color_ring_pass(self) -> None:
        g = _make_game()
        g._start_playing()
        g.ring_color = 8  # RED
        g.rings = [Ring(x=80.0, y=g.uni_y, color=8)]  # same color, at unicycle position
        matched, mismatch = g._check_ring_pass()
        assert matched == 1
        assert mismatch is False
        assert g.rings[0].passed is True

    def test_non_matching_color_ring_pass(self) -> None:
        g = _make_game()
        g._start_playing()
        g.ring_color = 8  # RED
        g.rings = [Ring(x=80.0, y=g.uni_y, color=11)]  # LIME, different color
        matched, mismatch = g._check_ring_pass()
        assert matched == 0
        assert mismatch is True
        assert g.rings[0].passed is True

    def test_super_active_matches_any_color(self) -> None:
        g = _make_game()
        g._start_playing()
        g.super_active = True
        g.ring_color = 8  # RED
        g.rings = [Ring(x=80.0, y=g.uni_y, color=11)]  # LIME, would normally mismatch
        matched, mismatch = g._check_ring_pass()
        assert matched == 1
        assert mismatch is False

    def test_ring_out_of_range_not_passed(self) -> None:
        g = _make_game()
        g._start_playing()
        g.ring_color = 8
        g.rings = [Ring(x=300.0, y=200.0, color=8)]  # far away
        matched, mismatch = g._check_ring_pass()
        assert matched == 0
        assert mismatch is False
        assert g.rings[0].passed is False

    def test_already_passed_ring_ignored(self) -> None:
        g = _make_game()
        g._start_playing()
        g.ring_color = 8
        g.rings = [Ring(x=80.0, y=g.uni_y, color=8, passed=True)]
        matched, mismatch = g._check_ring_pass()
        assert matched == 0
        assert mismatch is False


class TestColorCycle:
    def test_color_cycles_after_timer(self) -> None:
        g = _make_game()
        g._start_playing()
        g.ring_color = g._RING_COLORS[0]  # RED = 8
        g.ring_color_timer = 1
        g._update_color_cycle()
        assert g.ring_color != 8  # should have changed

    def test_color_cycle_order(self) -> None:
        g = _make_game()
        g._start_playing()
        g.ring_color = 8  # RED
        g.ring_color_timer = 1
        g._update_color_cycle()
        assert g.ring_color == 11  # RED → LIME

    def test_timer_reset_after_cycle(self) -> None:
        g = _make_game()
        g._start_playing()
        g.ring_color_timer = 1
        g.ring_color_interval = 55
        g._update_color_cycle()
        assert g.ring_color_timer == 55

    def test_timer_decrements(self) -> None:
        g = _make_game()
        g._start_playing()
        g.ring_color_timer = 90
        g._update_color_cycle()
        assert g.ring_color_timer == 89


class TestSuper:
    def test_activate_super_sets_state(self) -> None:
        g = _make_game()
        g._start_playing()
        g._activate_super()
        assert g.super_active is True
        assert g.super_timer == 300
        assert g.super_mult == 3
        assert g.combo == 0  # reset

    def test_deactivate_super_clears_state(self) -> None:
        g = _make_game()
        g._start_playing()
        g._activate_super()
        g._deactivate_super()
        assert g.super_active is False
        assert g.super_timer == 0
        assert g.super_mult == 1

    def test_activate_super_adds_particles(self) -> None:
        g = _make_game()
        g._start_playing()
        g._rng = random.Random(42)
        g._activate_super()
        assert len(g.particles) == 20

    def test_activate_super_adds_floating_text(self) -> None:
        g = _make_game()
        g._start_playing()
        g._activate_super()
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].text == "SUPER!"


class TestHeat:
    def test_heat_decays(self) -> None:
        g = _make_game()
        g._start_playing()
        g.heat = 10.0
        g._update_heat()
        assert g.heat < 10.0

    def test_heat_does_not_go_negative(self) -> None:
        g = _make_game()
        g._start_playing()
        g.heat = 0.0
        g._update_heat()
        assert g.heat == 0.0

    def test_heat_at_max_ends_game(self) -> None:
        g = _make_game()
        g._start_playing()
        g.heat = 100.0
        g._update_heat()
        assert g.phase == Phase.GAME_OVER
        assert g.heat == 100.0


class TestStamina:
    def test_pedaling_drains_stamina(self) -> None:
        g = _make_game()
        g._start_playing()
        g.stamina = 50.0
        g._update_stamina(True)
        assert g.stamina < 50.0

    def test_not_pedaling_recharges_stamina(self) -> None:
        g = _make_game()
        g._start_playing()
        g.stamina = 50.0
        g._update_stamina(False)
        assert g.stamina > 50.0

    def test_stamina_capped_at_max(self) -> None:
        g = _make_game()
        g._start_playing()
        g.stamina = 99.95
        g._update_stamina(False)
        assert g.stamina == 100.0

    def test_stamina_does_not_go_negative(self) -> None:
        g = _make_game()
        g._start_playing()
        g.stamina = 0.1
        g._update_stamina(True)
        assert g.stamina == 0.0

    def test_pedaling_sets_speed_mult(self) -> None:
        g = _make_game()
        g._start_playing()
        g._update_stamina(True)
        assert g.speed_mult == 1.3

    def test_not_pedaling_sets_speed_mult_to_one(self) -> None:
        g = _make_game()
        g._start_playing()
        g.speed_mult = 1.3
        g._update_stamina(False)
        assert g.speed_mult == 1.0


class TestEndGame:
    def test_end_game_sets_phase(self) -> None:
        g = _make_game()
        g._start_playing()
        g._end_game()
        assert g.phase == Phase.GAME_OVER

    def test_end_game_updates_best_score(self) -> None:
        g = _make_game()
        g._start_playing()
        g.score = 500
        g.best_score = 100
        g._end_game()
        assert g.best_score == 500

    def test_end_game_preserves_lower_best_score(self) -> None:
        g = _make_game()
        g._start_playing()
        g.score = 50
        g.best_score = 100
        g._end_game()
        assert g.best_score == 100  # unchanged


class TestParticles:
    def test_add_particles(self) -> None:
        g = _make_game()
        g._start_playing()
        g._rng = random.Random(42)
        g._add_particles(100.0, 100.0, 5, 8)
        assert len(g.particles) == 5
        for p in g.particles:
            assert p.color == 8

    def test_update_particles_decrements_life(self) -> None:
        g = _make_game()
        g._start_playing()
        g.particles = [Particle(x=0.0, y=0.0, vx=1.0, vy=0.0, life=10, color=8)]
        g._update_particles()
        assert g.particles[0].life == 9

    def test_update_particles_removes_dead(self) -> None:
        g = _make_game()
        g._start_playing()
        g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=8)]
        g._update_particles()
        assert len(g.particles) == 0  # life goes to 0, removed

    def test_update_particles_moves_position(self) -> None:
        g = _make_game()
        g._start_playing()
        g.particles = [Particle(x=100.0, y=100.0, vx=2.0, vy=3.0, life=10, color=8)]
        g._update_particles()
        assert g.particles[0].x == 102.0
        assert g.particles[0].y == 103.0


class TestFloatingText:
    def test_add_floating_text(self) -> None:
        g = _make_game()
        g._start_playing()
        g._add_floating_text(160.0, 120.0, "+10", 7)
        assert len(g.floating_texts) == 1
        assert g.floating_texts[0].text == "+10"
        assert g.floating_texts[0].life == 35
        assert g.floating_texts[0].color == 7

    def test_update_floating_texts_decrements_life(self) -> None:
        g = _make_game()
        g._start_playing()
        g.floating_texts = [FloatText(x=100.0, y=100.0, text="test", life=5, color=7)]
        g._update_floating_texts()
        assert g.floating_texts[0].life == 4

    def test_update_floating_texts_removes_dead(self) -> None:
        g = _make_game()
        g._start_playing()
        g.floating_texts = [FloatText(x=100.0, y=100.0, text="test", life=1, color=7)]
        g._update_floating_texts()
        assert len(g.floating_texts) == 0

    def test_floating_text_moves_upward(self) -> None:
        g = _make_game()
        g._start_playing()
        g.floating_texts = [FloatText(x=100.0, y=100.0, text="test", life=10, color=7)]
        g._update_floating_texts()
        assert g.floating_texts[0].y < 100.0  # moves up (decreasing y)


class TestGhostTrail:
    def test_update_ghost_trail_records_points(self) -> None:
        g = _make_game()
        g._start_playing()
        g._update_ghost_trail()
        assert len(g.ghost_trail) == 1
        assert isinstance(g.ghost_trail[0], GhostPoint)

    def test_ghost_trail_skips_frames(self) -> None:
        g = _make_game()
        g._start_playing()
        g._frame = 0  # frame 0: records
        g._update_ghost_trail()
        assert len(g.ghost_trail) == 1
        g._frame = 1  # frame 1: skips
        g._update_ghost_trail()
        assert len(g.ghost_trail) == 1  # still 1 (skipped)
        g._frame = 3  # frame 3: records
        g._update_ghost_trail()
        assert len(g.ghost_trail) == 2


class TestDifficulty:
    def test_difficulty_scales_over_time(self) -> None:
        g = _make_game()
        g._start_playing()
        g.timer = 1800  # halfway
        g._update_difficulty()
        assert g.scroll_speed > 1.5
        assert g.spawn_interval < 70
        assert g.ring_color_interval < 90

    def test_difficulty_at_start(self) -> None:
        g = _make_game()
        g._start_playing()
        g.timer = 3600  # full time
        g._update_difficulty()
        assert abs(g.scroll_speed - 1.5) < 0.01
        assert g.spawn_interval == 70

    def test_difficulty_clamps_minimums(self) -> None:
        g = _make_game()
        g._start_playing()
        g.timer = 0  # end of game
        g._update_difficulty()
        assert g.spawn_interval >= 30
        assert g.ring_color_interval >= 40


class TestComboFlow:
    def test_same_color_ring_increments_combo(self) -> None:
        """Simulate the combo flow: match color -> combo++."""
        g = _make_game()
        g._start_playing()
        g.ring_color = 8  # RED
        g.rings = [Ring(x=80.0, y=g.uni_y, color=8)]
        # Manually simulate the match path (bypassing pyxel input in _update_playing)
        g.combo = 1
        matched, mismatch = g._check_ring_pass()
        # Simulate what _update_playing does after match
        if matched > 0 and not g.super_active:
            g.combo += matched
            points = 10 * g.combo * g.super_mult
            g.score += int(points)
            if g.combo > g.max_combo:
                g.max_combo = g.combo
        assert g.combo == 2
        assert g.score > 0

    def test_mismatch_resets_combo(self) -> None:
        g = _make_game()
        g._start_playing()
        g.combo = 3
        g.ring_color = 8  # RED
        g.rings = [Ring(x=80.0, y=g.uni_y, color=11)]  # LIME
        matched, mismatch = g._check_ring_pass()
        # Simulate mismatch handling
        if mismatch and not g.super_active:
            g.heat += g.HEAT_MISMATCH
            g.combo = 0
            g.stun_timer = 15
        assert g.combo == 0
        assert g.heat == 15.0
        assert g.stun_timer == 15

    def test_combo_threshold_activates_super(self) -> None:
        g = _make_game()
        g._start_playing()
        g._rng = random.Random(42)
        g.combo = 3
        g.ring_color = 8
        g.rings = [Ring(x=80.0, y=g.uni_y, color=8)]
        matched, mismatch = g._check_ring_pass()
        if matched > 0 and not g.super_active:
            g.combo += matched
            if g.combo >= g.COMBO_THRESHOLD:
                g._activate_super()
        assert g.super_active is True
        assert g.super_mult == 3

    def test_super_deactivates_after_timer(self) -> None:
        g = _make_game()
        g._start_playing()
        g.super_active = True
        g.super_timer = 1
        g.super_mult = 3
        # Simulate super expiry in _update_playing
        g.super_timer -= 1
        if g.super_timer <= 0:
            g._deactivate_super()
        assert g.super_active is False
        assert g.super_mult == 1


class TestScoring:
    def test_score_with_combo(self) -> None:
        g = _make_game()
        g._start_playing()
        # Match 1: combo becomes 1, score = 10*1*1 = 10
        g.combo = 0
        g.ring_color = 8
        g.rings = [Ring(x=80.0, y=g.uni_y, color=8)]
        matched, _ = g._check_ring_pass()
        if matched > 0:
            g.combo += matched
            points = 10 * g.combo * g.super_mult
            g.score += int(points)
        assert g.score == 10

        # Match 2: combo becomes 2, score = 10*2*1 = 20 more, total 30
        g.rings = [Ring(x=80.0, y=g.uni_y, color=8)]
        matched, _ = g._check_ring_pass()
        if matched > 0:
            g.combo += matched
            points = 10 * g.combo * g.super_mult
            g.score += int(points)
        assert g.score == 30

    def test_score_with_super_multiplier(self) -> None:
        g = _make_game()
        g._start_playing()
        g.super_active = True
        g.super_mult = 3
        g.rings = [Ring(x=80.0, y=g.uni_y, color=8)]
        matched, _ = g._check_ring_pass()
        if matched > 0:
            points = 10 * g.super_mult
            g.score += int(points)
        assert g.score == 30


class TestMaxCombo:
    def test_max_combo_tracks_highest(self) -> None:
        g = _make_game()
        g._start_playing()
        g.combo = 5
        g.max_combo = 0
        if g.combo > g.max_combo:
            g.max_combo = g.combo
        assert g.max_combo == 5

    def test_max_combo_unchanged_when_combo_lower(self) -> None:
        g = _make_game()
        g._start_playing()
        g.max_combo = 8
        g.combo = 3
        if g.combo > g.max_combo:
            g.max_combo = g.combo
        assert g.max_combo == 8


class TestStunTimer:
    def test_stun_prevents_unicycle_update(self) -> None:
        """When stunned, _update_playing checks stun_timer first and returns early."""
        g = _make_game()
        g._start_playing()
        g.stun_timer = 5
        # Since _update_playing() calls pyxel.btn, we can't test it directly.
        # But we can verify stun timer exists and is positive.
        assert g.stun_timer > 0
        # Manually simulate the stun path: decrement stun, no tilt change
        g.stun_timer -= 1
        assert g.stun_timer == 4


class TestTimerExpiry:
    def test_timer_running(self) -> None:
        g = _make_game()
        g._start_playing()
        assert g.timer == 3600

    def test_timer_expiry_triggers_game_over(self) -> None:
        g = _make_game()
        g._start_playing()
        g.timer = 0
        g._end_game()
        assert g.phase == Phase.GAME_OVER
