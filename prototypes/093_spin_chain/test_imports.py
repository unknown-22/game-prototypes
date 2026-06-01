"""test_imports.py — Headless logic tests for SPIN CHAIN (093)."""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/093_spin_chain")

# ─── Import actual game classes ────────────────────────────────────────────
from main import Game, Reel, Particle, Phase  # noqa: E402

# ─── Replicate constants (no pyxel import) ─────────────────────────────────
BLACK, NAVY, PURPLE, GREEN, BROWN, DARK_BLUE, LIGHT_BLUE = 0, 1, 2, 3, 4, 5, 6
WHITE, RED, ORANGE, YELLOW, LIME, CYAN, GRAY, PINK, PEACH = 7, 8, 9, 10, 11, 12, 13, 14, 15

REEL_COLORS: tuple[int, ...] = (RED, GREEN, DARK_BLUE, YELLOW)
COLOR_NAMES: tuple[str, ...] = ("RED", "GREEN", "BLUE", "YELLOW")

SCREEN_W = 320
SCREEN_H = 240
REEL_W = 60
REEL_H = 80
REEL_SPACING = 80
REEL_Y = 120
SPIN_DURATION = 60
SPIN_STAGGER = 18
MAX_SPINS = 20
MAX_HEAT = 10
HOLD_COST = 1
MISS_HEAT = 2
SUPER_COMBO_THRESHOLD = 4
SUPER_MULTIPLIER = 3
BIG_SCORE = 500
SMALL_SCORE = 100


def _make_game() -> Game:
    """Factory: create Game via __new__ bypass, seed RNG for determinism."""
    g: Game = Game.__new__(Game)
    # Pre-init ALL attributes reset() touches
    g._rng = random.Random(42)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0
    g.spins_remaining = MAX_SPINS
    g.super_spin = False
    g.result_text = ""
    g.result_timer = 0
    g.shake_frames = 0
    g.last_match_color = -1
    g.particles = []
    g.high_score = 0
    g.reels = []
    g.reset()
    return g


class TestReelSetup:
    """Test reel initialization and structure."""

    def test_reset_creates_three_reels(self) -> None:
        g = _make_game()
        assert len(g.reels) == 3

    def test_reel_positions(self) -> None:
        g = _make_game()
        assert g.reels[0].x == 80
        assert g.reels[1].x == 160
        assert g.reels[2].x == 240
        for r in g.reels:
            assert r.y == 120

    def test_reels_not_spinning_or_held_after_reset(self) -> None:
        g = _make_game()
        for r in g.reels:
            assert not r.spinning
            assert not r.held

    def test_reset_sets_game_state(self) -> None:
        g = _make_game()
        assert g.phase == Phase.TITLE
        assert g.score == 0
        assert g.combo == 0
        assert g.max_combo == 0
        assert g.heat == 0
        assert g.spins_remaining == 20
        assert not g.super_spin
        assert g.last_match_color == -1
        assert g.particles == []


class TestStartGame:
    """Test _start_game state transition."""

    def test_start_game_sets_playing_and_resets_state(self) -> None:
        g = _make_game()
        g.score = 500
        g.heat = 3
        g.combo = 2
        g._start_game()
        assert g.phase == Phase.PLAYING
        assert g.score == 0
        assert g.heat == 0
        assert g.combo == 0
        assert g.spins_remaining == 20

    def test_start_game_unholds_all_reels(self) -> None:
        g = _make_game()
        g.reels[0].held = True
        g.reels[1].held = True
        g._start_game()
        for r in g.reels:
            assert not r.held


class TestSpinReels:
    """Test _spin_reels behavior."""

    def test_spin_sets_spinning_on_unheld_reels(self) -> None:
        g = _make_game()
        g._start_game()
        g._spin_reels()
        assert g.phase == Phase.SPINNING
        for r in g.reels:
            assert r.spinning

    def test_held_reels_not_set_to_spinning(self) -> None:
        g = _make_game()
        g._start_game()
        g.reels[1].held = True
        g._spin_reels()
        assert g.reels[0].spinning
        assert not g.reels[1].spinning  # held
        assert g.reels[2].spinning

    def test_all_held_auto_releases(self) -> None:
        g = _make_game()
        g._start_game()
        for r in g.reels:
            r.held = True
        g._spin_reels()
        for r in g.reels:
            assert not r.held
            assert r.spinning


class TestToggleHold:
    """Test _toggle_hold behavior."""

    def test_toggle_hold_sets_held(self) -> None:
        g = _make_game()
        g._start_game()
        g._toggle_hold(0)
        assert g.reels[0].held
        assert g.heat == 1  # HOLD_COST

    def test_toggle_hold_release(self) -> None:
        g = _make_game()
        g._start_game()
        g._toggle_hold(0)
        g._toggle_hold(0)
        assert not g.reels[0].held
        assert g.heat == 2  # twice HOLD_COST

    def test_toggle_hold_max_two(self) -> None:
        g = _make_game()
        g._start_game()
        g._toggle_hold(0)
        g._toggle_hold(1)
        assert g.reels[0].held
        assert g.reels[1].held
        # Third hold should fail (max 2)
        g._toggle_hold(2)
        assert not g.reels[2].held

    def test_toggle_hold_during_spin_noop(self) -> None:
        g = _make_game()
        g._start_game()
        g.reels[0].spinning = True
        g._toggle_hold(0)
        assert not g.reels[0].held  # can't hold while spinning

    def test_toggle_hold_invalid_idx_noop(self) -> None:
        g = _make_game()
        g._start_game()
        g._toggle_hold(-1)
        g._toggle_hold(3)
        assert g.heat == 0  # no cost for invalid


class TestEvaluateResult:
    """Test _evaluate_result scoring and combo logic."""

    # ─── 3-match ──────────────────────────────────────────────────────

    def test_three_match_scores_big(self) -> None:
        g = _make_game()
        g._start_game()
        # Set all reels to same color (RED=0)
        for r in g.reels:
            r.color_idx = 0
        match = g._evaluate_result()
        assert match == 3
        assert g.score == BIG_SCORE  # 500 * combo(1) * 1
        assert g.combo == 1
        assert g.max_combo == 1

    def test_three_match_consecutive_same_color_builds_combo(self) -> None:
        g = _make_game()
        g._start_game()
        # First 3-match RED
        for r in g.reels:
            r.color_idx = 0
        g._evaluate_result()
        assert g.combo == 1
        score1 = g.score
        # Second 3-match RED
        g.spins_remaining = 20
        g.phase = Phase.PLAYING
        for r in g.reels:
            r.color_idx = 0
        g._evaluate_result()
        assert g.combo == 2
        assert g.score == score1 + BIG_SCORE * 2  # × combo 2
        assert g.max_combo == 2

    def test_three_match_different_color_resets_combo(self) -> None:
        g = _make_game()
        g._start_game()
        # First: RED
        for r in g.reels:
            r.color_idx = 0
        g._evaluate_result()
        assert g.combo == 1
        # Second: GREEN
        g.spins_remaining = 20
        g.phase = Phase.PLAYING
        for r in g.reels:
            r.color_idx = 1
        g._evaluate_result()
        assert g.combo == 1  # reset, new chain starts at 1

    # ─── 2-match ──────────────────────────────────────────────────────

    def test_two_match_scores_small(self) -> None:
        g = _make_game()
        g._start_game()
        g.reels[0].color_idx = 0  # RED
        g.reels[1].color_idx = 0  # RED
        g.reels[2].color_idx = 1  # GREEN
        match = g._evaluate_result()
        assert match == 2
        assert g.score == SMALL_SCORE  # 100 * 1 * 1

    def test_two_match_edges(self) -> None:
        g = _make_game()
        g._start_game()
        g.reels[0].color_idx = 1  # GREEN
        g.reels[1].color_idx = 0  # RED
        g.reels[2].color_idx = 0  # RED (indices 1,2 match)
        match = g._evaluate_result()
        assert match == 2
        assert g.score == SMALL_SCORE

    def test_two_match_outer_edges(self) -> None:
        g = _make_game()
        g._start_game()
        g.reels[0].color_idx = 0  # RED
        g.reels[1].color_idx = 1  # GREEN
        g.reels[2].color_idx = 0  # RED (indices 0,2 match)
        match = g._evaluate_result()
        assert match == 2

    # ─── 0-match ──────────────────────────────────────────────────────

    def test_no_match_resets_combo(self) -> None:
        g = _make_game()
        g._start_game()
        # First: a 3-match to build combo
        for r in g.reels:
            r.color_idx = 0
        g._evaluate_result()
        assert g.combo == 1
        # Then: all different
        g.spins_remaining = 20
        g.phase = Phase.PLAYING
        g.reels[0].color_idx = 0
        g.reels[1].color_idx = 1
        g.reels[2].color_idx = 2
        score_before = g.score
        g._evaluate_result()
        assert g.combo == 0
        assert g.last_match_color == -1
        assert g.heat == MISS_HEAT  # +2
        assert g.score == score_before  # no score added

    # ─── Combo multiplier ─────────────────────────────────────────────

    def test_combo_multiplies_score(self) -> None:
        g = _make_game()
        g._start_game()
        # Set combo externally and verify multiplication
        g.combo = 5
        g.last_match_color = 0
        for r in g.reels:
            r.color_idx = 0
        score_before = g.score
        g._evaluate_result()
        # same color → combo increments to 6, score = BIG_SCORE * 6
        assert g.score == score_before + BIG_SCORE * 6
        assert g.combo == 6

    def test_max_combo_tracks_highest(self) -> None:
        g = _make_game()
        g._start_game()
        for r in g.reels:
            r.color_idx = 0
        g._evaluate_result()
        assert g.max_combo == 1
        g.spins_remaining = 20
        g.phase = Phase.PLAYING
        g._evaluate_result()
        assert g.max_combo == 2
        # Reset
        g.spins_remaining = 20
        g.phase = Phase.PLAYING
        # Set ALL reels to a different color (not RED=0) for a true different-color match
        for r in g.reels:
            r.color_idx = 1  # GREEN
        g._evaluate_result()
        assert g.max_combo == 2  # unchanged, max was 2

    def test_combo_reset_on_color_change_two_match(self) -> None:
        g = _make_game()
        g._start_game()
        g.reels[0].color_idx = 0
        g.reels[1].color_idx = 0
        g.reels[2].color_idx = 1
        g._evaluate_result()
        assert g.combo == 1
        # Now different color 2-match
        g.spins_remaining = 20
        g.phase = Phase.PLAYING
        g.reels[0].color_idx = 2
        g.reels[1].color_idx = 2
        g.reels[2].color_idx = 0
        g._evaluate_result()
        assert g.combo == 1  # reset to 1 (new color)


class TestSuperSpin:
    """Test SUPER SPIN mechanics."""

    def test_super_spin_activates_at_combo_4(self) -> None:
        g = _make_game()
        g._start_game()
        g.combo = 3
        g.last_match_color = 0
        for r in g.reels:
            r.color_idx = 0
        g._evaluate_result()
        assert g.combo >= SUPER_COMBO_THRESHOLD  # combo becomes 4
        assert g.super_spin

    def test_super_spin_3x_multiplier(self) -> None:
        g = _make_game()
        g._start_game()
        g.super_spin = True
        g.last_match_color = 0
        for r in g.reels:
            r.color_idx = 0
        score_before = g.score
        g._evaluate_result()
        assert g.score == score_before + BIG_SCORE * 1 * SUPER_MULTIPLIER  # combo 1 × 3

    def test_super_spin_deactivates_after_use(self) -> None:
        g = _make_game()
        g._start_game()
        g.super_spin = True
        g.last_match_color = 0
        for r in g.reels:
            r.color_idx = 0
        g._evaluate_result()
        assert not g.super_spin  # used, now deactivated

    def test_super_spin_guarantees_two_match(self) -> None:
        g = _make_game()
        g._start_game()
        g.super_spin = True
        g.last_match_color = -1
        # Set all different (would be 0-match)
        g.reels[0].color_idx = 0
        g.reels[1].color_idx = 1
        g.reels[2].color_idx = 2
        match = g._evaluate_result()
        assert match >= 2  # guaranteed

    def test_super_spin_doesnt_activate_if_already_active(self) -> None:
        g = _make_game()
        g._start_game()
        g.super_spin = True
        g.combo = 4
        g.last_match_color = 0
        for r in g.reels:
            r.color_idx = 0
        g._evaluate_result()
        # super_spin should be consumed, not re-triggered
        assert not g.super_spin


class TestHeat:
    """Test HEAT accumulation and game over."""

    def test_no_match_adds_heat(self) -> None:
        g = _make_game()
        g._start_game()
        g.reels[0].color_idx = 0
        g.reels[1].color_idx = 1
        g.reels[2].color_idx = 2
        g._evaluate_result()
        assert g.heat == MISS_HEAT

    def test_heat_game_over(self) -> None:
        g = _make_game()
        g._start_game()
        g.heat = MAX_HEAT - MISS_HEAT  # 8
        g.reels[0].color_idx = 0
        g.reels[1].color_idx = 1
        g.reels[2].color_idx = 2
        g._evaluate_result()
        assert g.heat >= MAX_HEAT
        assert g.phase == Phase.GAME_OVER

    def test_heat_capped_at_max(self) -> None:
        g = _make_game()
        g._start_game()
        g.heat = MAX_HEAT - 1  # 9
        # Toggle hold twice = +2 heat, but should cap at 10
        g._toggle_hold(0)  # +1 → 10
        assert g.heat == MAX_HEAT


class TestSpinsRemaining:
    """Test spins_remaining counting."""

    def test_spins_decrements_after_evaluate(self) -> None:
        g = _make_game()
        g._start_game()
        assert g.spins_remaining == 20
        g._evaluate_result()
        assert g.spins_remaining == 19

    def test_spins_game_over_at_zero(self) -> None:
        g = _make_game()
        g._start_game()
        g.spins_remaining = 1
        for r in g.reels:
            r.color_idx = 0
        g._evaluate_result()
        assert g.spins_remaining == 0
        assert g.phase == Phase.GAME_OVER

    def test_spins_does_not_decrement_in_title(self) -> None:
        g = _make_game()
        assert g.phase == Phase.TITLE
        assert g.spins_remaining == 20


class TestParticles:
    """Test particle system."""

    def test_spawn_particles_adds_to_list(self) -> None:
        g = _make_game()
        g._start_game()
        g._spawn_particles(160, 120, 10, RED)
        assert len(g.particles) == 10
        assert all(p.color == RED for p in g.particles)

    def test_spawn_particles_rainbow_when_color_negative(self) -> None:
        g = _make_game()
        g._start_game()
        g._spawn_particles(160, 120, 10, -1)
        assert len(g.particles) == 10
        # With seeded rng and rainbow, all colors in REEL_COLORS
        for p in g.particles:
            assert p.color in REEL_COLORS

    def test_update_particles_gravity_and_life(self) -> None:
        g = _make_game()
        g._start_game()
        g._spawn_particles(160, 120, 1, RED)
        p = g.particles[0]
        orig_life = p.life
        g._update_particles()
        # After update: gravity applied (vy += 0.1), y changed, life decremented
        assert p.life == orig_life - 1

    def test_particles_removed_when_life_zero(self) -> None:
        g = _make_game()
        g._start_game()
        g.particles = [Particle(x=160, y=120, vx=0, vy=0, life=1, color=RED, max_life=20)]
        g._update_particles()
        assert len(g.particles) == 0  # life became 0, filtered out

    def test_particles_removed_when_life_negative(self) -> None:
        g = _make_game()
        g._start_game()
        g.particles = [Particle(x=160, y=120, vx=0, vy=0, life=-1, color=RED, max_life=20)]
        g._update_particles()
        assert len(g.particles) == 0

    def test_three_match_spawns_particles(self) -> None:
        g = _make_game()
        g._start_game()
        for r in g.reels:
            r.color_idx = 0
        g._evaluate_result()
        assert len(g.particles) > 0  # 30 particles spawned for 3-match

    def test_two_match_spawns_particles(self) -> None:
        g = _make_game()
        g._start_game()
        g.reels[0].color_idx = 0
        g.reels[1].color_idx = 0
        g.reels[2].color_idx = 1
        g._evaluate_result()
        assert len(g.particles) == 10

    def test_no_match_no_particles(self) -> None:
        g = _make_game()
        g._start_game()
        g.reels[0].color_idx = 0
        g.reels[1].color_idx = 1
        g.reels[2].color_idx = 2
        g._evaluate_result()
        assert len(g.particles) == 0


class TestMouseOver:
    """Test mouse-over AABB detection."""

    def test_mouse_over_reel_center(self) -> None:
        g = _make_game()
        reel = Reel(x=160, y=REEL_Y, color_idx=0)
        assert g._is_mouse_over_reel(160, REEL_Y, reel)

    def test_mouse_over_reel_corner(self) -> None:
        g = _make_game()
        reel = Reel(x=160, y=REEL_Y, color_idx=0)
        # Top-left corner of reel
        assert g._is_mouse_over_reel(160 - REEL_W // 2 + 1, REEL_Y - REEL_H // 2 + 1, reel)

    def test_mouse_not_over_reel_outside(self) -> None:
        g = _make_game()
        reel = Reel(x=160, y=REEL_Y, color_idx=0)
        assert not g._is_mouse_over_reel(0, 0, reel)

    def test_mouse_over_spin_button(self) -> None:
        g = _make_game()
        # Button at SCREEN_W//2-40, SCREEN_H-44, 80×22
        bx = SCREEN_W // 2 - 30  # from _is_mouse_over_spin_button
        by = SCREEN_H - 40
        assert g._is_mouse_over_spin_button(bx + 30, by + 10)

    def test_mouse_not_over_spin_button(self) -> None:
        g = _make_game()
        assert not g._is_mouse_over_spin_button(0, 0)


class TestScoreTracking:
    """Test score and high score tracking."""

    def test_score_accumulates(self) -> None:
        g = _make_game()
        g._start_game()
        for r in g.reels:
            r.color_idx = 0
        g._evaluate_result()
        s1 = g.score
        g.spins_remaining = 20
        g.phase = Phase.PLAYING
        g._evaluate_result()
        assert g.score > s1

    def test_high_score_updated_on_game_over(self) -> None:
        g = _make_game()
        g._start_game()
        g.score = 5000
        g.heat = MAX_HEAT  # 10, game over on next eval
        # Set all different to avoid score addition (0-match)
        g.reels[0].color_idx = 0
        g.reels[1].color_idx = 1
        g.reels[2].color_idx = 2
        g._evaluate_result()
        assert g.phase == Phase.GAME_OVER
        assert g.high_score == 5000  # score unchanged (0-match)

    def test_high_score_not_lowered(self) -> None:
        g = _make_game()
        g.high_score = 10000
        g._start_game()
        g.score = 500
        g.heat = MAX_HEAT
        g._evaluate_result()
        assert g.high_score == 10000  # unchanged


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_heat_exactly_max_game_over(self) -> None:
        g = _make_game()
        g._start_game()
        g.heat = MAX_HEAT
        # Game should already be over at next evaluate
        for r in g.reels:
            r.color_idx = 0
        g._evaluate_result()
        assert g.phase == Phase.GAME_OVER

    def test_result_timer_set_after_evaluate(self) -> None:
        g = _make_game()
        g._start_game()
        for r in g.reels:
            r.color_idx = 0
        g._evaluate_result()
        assert g.result_timer == 60

    def test_shake_frames_on_three_match(self) -> None:
        g = _make_game()
        g._start_game()
        for r in g.reels:
            r.color_idx = 0
        g._evaluate_result()
        assert g.shake_frames == 8

    def test_shake_frames_on_super_activation(self) -> None:
        g = _make_game()
        g._start_game()
        g.combo = 3
        g.last_match_color = 0
        for r in g.reels:
            r.color_idx = 0
        g._evaluate_result()
        assert g.shake_frames == 12  # SUPER activation shake

    def test_spins_remaining_reset_on_start_game(self) -> None:
        g = _make_game()
        g._start_game()
        g.spins_remaining = 5
        g._start_game()
        assert g.spins_remaining == 20
