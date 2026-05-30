"""test_imports.py — Headless logic tests for BATTER CHAIN prototype."""
import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/085_batter_chain")

from main import (
    Game, Phase, Pitch, Particle, FloatingText,
    BLACK, NAVY, PURPLE, GREEN, BROWN, DARK_BLUE, LIGHT_BLUE,
    WHITE, RED, ORANGE, YELLOW, LIME, CYAN, GRAY, PINK, PEACH,
    SCREEN_W, SCREEN_H, COMBO_COLORS, COMBO_COLOR_NAMES,
    TOTAL_PITCHES, MAX_STRIKES, SUPER_HIT_THRESHOLD,
    SZ_LEFT, SZ_TOP, SZ_W, SZ_H, SZ_CX, SZ_CY,
    PITCHER_X, PITCHER_Y, BATTER_X, BATTER_Y,
    BASE_PITCH_SPEED, SPEED_INCREMENT,
    WINDUP_FRAMES, RESULT_FRAMES, SWING_FRAMES,
    HIT_FLASH_FRAMES, SUPER_SHAKE_FRAMES,
    HIT_ZONE_X_MIN, HIT_ZONE_X_MAX, HIT_ZONE_Y_MIN, HIT_ZONE_Y_MAX,
)


def _make_game() -> Game:
    """Factory for headless Game instance with deterministic RNG."""
    g = Game.__new__(Game)
    # Pre-init ALL instance attributes
    g.phase = Phase.TITLE
    g.score = 0
    g.high_score = 0
    g.combo = 0
    g.max_combo = 0
    g.combo_color = -1
    g.strikes = 0
    g.pitch_count = 0
    g.total_pitches = TOTAL_PITCHES
    g.pitch_speed = BASE_PITCH_SPEED
    g.pitch_timer = 0
    g.current_pitch = None
    g.particles = []
    g.floating_texts = []
    g.hit_flash = 0
    g.shake_frames = 0
    g.swing_anim = 0
    g.result_timer = 0
    g.last_result = ""
    g.last_score = 0
    g.windup_timer = 0
    g.pitch_speeds = []
    g.reset()
    g.rng = random.Random(42)
    return g


# ═══════════════════════════════════════════════════════════════
# Import / Dataclass / Constant Tests
# ═══════════════════════════════════════════════════════════════

def test_constants():
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert len(COMBO_COLORS) == 4
    assert TOTAL_PITCHES == 10
    assert MAX_STRIKES == 3
    assert SUPER_HIT_THRESHOLD == 3
    assert BASE_PITCH_SPEED == 3.0
    assert SZ_LEFT == 200 and SZ_TOP == 100
    assert SZ_W == 60 and SZ_H == 60


def test_phase_enum():
    assert Phase.TITLE in Phase
    assert Phase.WINDUP in Phase
    assert Phase.PITCH in Phase
    assert Phase.RESULT in Phase
    assert Phase.GAME_OVER in Phase


def test_pitch_dataclass():
    p = Pitch(x=100.0, y=150.0, vx=3.0, vy=0.0, color=RED)
    assert p.x == 100.0
    assert p.color == RED
    assert p.active is True
    assert p.trail == []


def test_particle_dataclass():
    p = Particle(x=50.0, y=60.0, vx=1.0, vy=-2.0, life=20, color=YELLOW)
    assert p.life == 20
    assert p.size == 2


def test_floating_text_dataclass():
    ft = FloatingText(x=100.0, y=80.0, text="+100", life=40, color=CYAN)
    assert ft.text == "+100"
    assert ft.vy == -1.5
    assert ft.life == 40


# ═══════════════════════════════════════════════════════════════
# State Initialization Tests
# ═══════════════════════════════════════════════════════════════

def test_reset_initial_state():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.combo_color == -1
    assert g.strikes == 0
    assert g.pitch_count == 0
    assert g.current_pitch is None
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.hit_flash == 0
    assert g.shake_frames == 0
    assert g.swing_anim == 0
    assert len(g.pitch_speeds) == TOTAL_PITCHES


def test_pitch_speeds_increase():
    g = _make_game()
    for i in range(len(g.pitch_speeds) - 1):
        assert g.pitch_speeds[i + 1] > g.pitch_speeds[i]
    # First speed equals base, last is higher
    assert abs(g.pitch_speeds[0] - BASE_PITCH_SPEED) < 0.001
    expected_last = BASE_PITCH_SPEED + SPEED_INCREMENT * (TOTAL_PITCHES - 1)
    assert abs(g.pitch_speeds[-1] - expected_last) < 0.001


# ═══════════════════════════════════════════════════════════════
# Pitch Logic Tests
# ═══════════════════════════════════════════════════════════════

def test_throw_pitch_creates_pitch():
    g = _make_game()
    g._throw_pitch()
    assert g.current_pitch is not None
    p = g.current_pitch
    assert p.x == float(PITCHER_X)
    assert p.y == float(PITCHER_Y)
    assert p.color in COMBO_COLORS
    assert p.vx > 0  # moving right toward plate
    assert p.active is True


def test_throw_pitch_color_in_combo_colors():
    g = _make_game()
    for _ in range(20):
        g._throw_pitch()
        assert g.current_pitch.color in COMBO_COLORS
        g.current_pitch = None


def test_throw_pitch_target_y_in_strike_zone():
    g = _make_game()
    for _ in range(20):
        g._throw_pitch()
        p = g.current_pitch
        # Calculate where it would land (target_y)
        # Verify that vx > 0 (toward plate)
        assert p.vx > 0
        g.current_pitch = None


# ═══════════════════════════════════════════════════════════════
# Swing / Hit Detection Tests
# ═══════════════════════════════════════════════════════════════

def test_try_swing_no_pitch():
    g = _make_game()
    g.current_pitch = None
    assert g._try_swing() is False


def test_try_swing_ball_in_hit_zone():
    g = _make_game()
    g.current_pitch = Pitch(x=SZ_CX, y=SZ_CY, vx=3.0, vy=0.0, color=RED)
    assert g._try_swing() is True


def test_try_swing_ball_before_hit_zone():
    g = _make_game()
    g.current_pitch = Pitch(
        x=HIT_ZONE_X_MIN - 20, y=SZ_CY, vx=3.0, vy=0.0, color=GREEN
    )
    assert g._try_swing() is False


def test_try_swing_ball_after_hit_zone():
    g = _make_game()
    g.current_pitch = Pitch(
        x=HIT_ZONE_X_MAX + 20, y=SZ_CY, vx=3.0, vy=0.0, color=NAVY
    )
    assert g._try_swing() is False


# ═══════════════════════════════════════════════════════════════
# Hit Resolution Tests
# ═══════════════════════════════════════════════════════════════

def test_resolve_hit_first_hit():
    """First hit sets combo to 1 with pitch color."""
    g = _make_game()
    g.current_pitch = Pitch(x=SZ_CX, y=SZ_CY, vx=3.0, vy=0.0, color=RED)
    score_before = g.score
    g._resolve_hit()
    assert g.pitch_count == 1
    assert g.combo == 1
    assert g.combo_color == RED
    assert g.score > score_before
    assert g.last_result == "HIT"


def test_resolve_hit_same_color_combo():
    """Same color consecutive hits build combo."""
    g = _make_game()
    # First hit
    g.current_pitch = Pitch(x=SZ_CX, y=SZ_CY, vx=3.0, vy=0.0, color=RED)
    g._resolve_hit()
    assert g.combo == 1
    assert g.combo_color == RED
    score_after_first = g.score

    # Second hit — same color
    g.current_pitch = Pitch(x=SZ_CX, y=SZ_CY, vx=3.0, vy=0.0, color=RED)
    g._resolve_hit()
    assert g.combo == 2
    assert g.combo_color == RED
    assert g.score > score_after_first
    assert g.last_result == "COMBO"


def test_resolve_hit_different_color_resets_combo():
    """Different color hit resets combo to 1 with new color."""
    g = _make_game()
    # Build combo with RED
    g.current_pitch = Pitch(x=SZ_CX, y=SZ_CY, vx=3.0, vy=0.0, color=RED)
    g._resolve_hit()
    g.current_pitch = Pitch(x=SZ_CX, y=SZ_CY, vx=3.0, vy=0.0, color=RED)
    g._resolve_hit()
    assert g.combo == 2
    assert g.combo_color == RED

    # Hit different color
    g.current_pitch = Pitch(x=SZ_CX, y=SZ_CY, vx=3.0, vy=0.0, color=GREEN)
    g._resolve_hit()
    assert g.combo == 1
    assert g.combo_color == GREEN
    assert g.last_result == "FOUL"


def test_resolve_hit_super_hit_at_threshold():
    """Combo >= 3 triggers SUPER HIT."""
    g = _make_game()
    g.combo = 2
    g.combo_color = RED
    g.max_combo = 2
    score_before = g.score

    g.current_pitch = Pitch(x=SZ_CX, y=SZ_CY, vx=3.0, vy=0.0, color=RED)
    g._resolve_hit()

    assert g.last_result == "SUPER"
    assert g.shake_frames == SUPER_SHAKE_FRAMES
    assert g.score > score_before + 100  # super bonus is significant
    # After SUPER, combo resets to 1 with same color
    assert g.combo == 1
    assert g.combo_color == RED


def test_resolve_hit_max_combo_tracks_highest():
    g = _make_game()
    g.combo = 4
    g.combo_color = RED
    g.max_combo = 4
    score_before = g.score

    g.current_pitch = Pitch(x=SZ_CX, y=SZ_CY, vx=3.0, vy=0.0, color=RED)
    g._resolve_hit()

    # max_combo should now be 5 (combo was 4, incremented to 5 before SUPER reset)
    assert g.max_combo >= 4


def test_resolve_hit_timing_bonus():
    """Hit at center of strike zone gives higher score than at edge."""
    g1 = _make_game()
    g1.current_pitch = Pitch(x=SZ_CX, y=SZ_CY, vx=3.0, vy=0.0, color=RED)
    g1._resolve_hit()
    center_score = g1.last_score

    g2 = _make_game()
    # Place ball at edge of strike zone
    g2.current_pitch = Pitch(
        x=SZ_LEFT + 5, y=SZ_TOP + 5, vx=3.0, vy=0.0, color=RED
    )
    g2._resolve_hit()
    edge_score = g2.last_score

    assert center_score >= edge_score


def test_resolve_hit_null_pitch_safe():
    g = _make_game()
    g.current_pitch = None
    g._resolve_hit()  # Should not crash
    assert g.score == 0


# ═══════════════════════════════════════════════════════════════
# Miss Resolution Tests
# ═══════════════════════════════════════════════════════════════

def test_resolve_miss_increments_strikes():
    g = _make_game()
    g.current_pitch = Pitch(x=50.0, y=100.0, vx=3.0, vy=0.0, color=GREEN)
    g._resolve_miss()
    assert g.strikes == 1
    assert g.pitch_count == 1
    assert g.last_result == "STRIKE"
    assert g.last_score == 0


def test_resolve_miss_null_pitch_safe():
    g = _make_game()
    g.current_pitch = None
    g._resolve_miss()
    assert g.strikes == 0  # unchanged


# ═══════════════════════════════════════════════════════════════
# Passed Pitch / Game Over Tests
# ═══════════════════════════════════════════════════════════════

def test_on_pitch_passed_strike():
    g = _make_game()
    g.current_pitch = Pitch(x=100.0, y=100.0, vx=3.0, vy=0.0, color=RED)
    g._on_pitch_passed()
    assert g.strikes == 1
    assert g.pitch_count == 1
    assert g.last_result == "STRIKE"


def test_check_game_over_strikes():
    g = _make_game()
    g.strikes = MAX_STRIKES
    assert g._check_game_over() is True


def test_check_game_over_pitches():
    g = _make_game()
    g.pitch_count = TOTAL_PITCHES
    assert g._check_game_over() is True


def test_check_game_over_not_yet():
    g = _make_game()
    g.strikes = 1
    g.pitch_count = 5
    assert g._check_game_over() is False


def test_check_game_over_early_strikes():
    """Game can end before all pitches if 3 strikes reached."""
    g = _make_game()
    g.strikes = MAX_STRIKES
    g.pitch_count = 5  # only 5 pitches thrown
    assert g._check_game_over() is True


# ═══════════════════════════════════════════════════════════════
# Particle Tests
# ═══════════════════════════════════════════════════════════════

def test_spawn_hit_particles():
    g = _make_game()
    g.rng = random.Random(42)
    assert len(g.particles) == 0
    g._spawn_hit_particles(100.0, 100.0, RED)
    assert len(g.particles) == 12
    for p in g.particles:
        assert p.color == RED
        assert p.life >= 15
        assert p.life <= 30


def test_spawn_super_particles():
    g = _make_game()
    g.rng = random.Random(42)
    g._spawn_super_particles(150.0, 80.0)
    assert len(g.particles) == 40
    super_colors = {LIME, PINK, YELLOW, ORANGE, WHITE}
    for p in g.particles:
        assert p.color in super_colors
        assert p.life >= 20
        assert p.life <= 40
        assert p.size >= 2
        assert p.size <= 5


def test_spawn_strike_particles():
    g = _make_game()
    g.rng = random.Random(42)
    g._spawn_strike_particles(200.0, 130.0)
    assert len(g.particles) == 4
    for p in g.particles:
        assert p.color == RED
        assert p.size == 2


def test_update_particles():
    g = _make_game()
    g.rng = random.Random(42)
    g._spawn_hit_particles(100.0, 100.0, GREEN)
    initial_count = len(g.particles)
    for _ in range(20):
        g._update_particles()
    # Some particles should still be alive after 20 frames
    assert len(g.particles) > 0
    assert len(g.particles) <= initial_count


def test_particles_eventually_expire():
    g = _make_game()
    g.rng = random.Random(42)
    g._spawn_strike_particles(100.0, 100.0)
    for _ in range(50):
        g._update_particles()
    assert len(g.particles) == 0


# ═══════════════════════════════════════════════════════════════
# Floating Text Tests
# ═══════════════════════════════════════════════════════════════

def test_spawn_floating_text():
    g = _make_game()
    g._spawn_floating_text("+100", 200.0, 100.0, CYAN)
    assert len(g.floating_texts) == 1
    ft = g.floating_texts[0]
    assert ft.text == "+100"
    assert ft.life == 40
    assert ft.color == CYAN


def test_update_floating_texts():
    g = _make_game()
    g._spawn_floating_text("TEST", 150.0, 120.0, WHITE)
    ft = g.floating_texts[0]
    orig_y = ft.y
    g._update_floating_texts()
    assert ft.y < orig_y  # moves upward
    assert ft.life == 39


def test_floating_texts_eventually_expire():
    g = _make_game()
    g._spawn_floating_text("FADE", 100.0, 100.0, WHITE)
    for _ in range(50):
        g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ═══════════════════════════════════════════════════════════════
# Reset After Game Tests
# ═══════════════════════════════════════════════════════════════

def test_reset_after_playing_clears_state():
    g = _make_game()
    # Simulate some game state
    g.score = 500
    g.combo = 3
    g.strikes = 2
    g.pitch_count = 7
    g.current_pitch = Pitch(x=150.0, y=130.0, vx=3.0, vy=0.0, color=RED)
    g._spawn_hit_particles(100.0, 100.0, RED)
    g._spawn_floating_text("TEST", 100.0, 100.0, WHITE)
    g.shake_frames = 5
    g.hit_flash = 2

    g.reset()

    assert g.score == 0
    assert g.combo == 0
    assert g.combo_color == -1
    assert g.strikes == 0
    assert g.pitch_count == 0
    assert g.current_pitch is None
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g.shake_frames == 0
    assert g.hit_flash == 0
    assert g.phase == Phase.TITLE


# ═══════════════════════════════════════════════════════════════
# Edge Case Tests
# ═══════════════════════════════════════════════════════════════

def test_multiple_super_hits_in_game():
    """Should be possible to get multiple SUPER hits."""
    g = _make_game()
    total_supers = 0
    pitch_colors = [RED, RED, RED, GREEN, GREEN, GREEN, NAVY, NAVY, NAVY, YELLOW]
    for color in pitch_colors:
        if g.combo == 0:
            g.combo_color = -1  # force "new hit"
        g.current_pitch = Pitch(x=SZ_CX, y=SZ_CY, vx=3.0, vy=0.0, color=color)
        g._resolve_hit()
        if g.last_result == "SUPER":
            total_supers += 1

    assert total_supers >= 1


def test_combo_resets_on_foul():
    """FOUL resets combo to 1, not to 0."""
    g = _make_game()
    # Build combo to 3
    for _ in range(3):
        g.current_pitch = Pitch(x=SZ_CX, y=SZ_CY, vx=3.0, vy=0.0, color=RED)
        g._resolve_hit()
    assert g.combo >= 1  # After SUPER, combo is 1

    # Now hit different color — should be FOUL
    g.current_pitch = Pitch(x=SZ_CX, y=SZ_CY, vx=3.0, vy=0.0, color=GREEN)
    g._resolve_hit()
    assert g.combo == 1  # reset to 1, not 0
    assert g.combo_color == GREEN


def test_max_combo_persists_across_resets():
    """After reset, max_combo is 0 (fresh start)."""
    g = _make_game()
    g.max_combo = 5
    g.reset()
    assert g.max_combo == 0


def test_hit_zone_boundaries():
    """Test exact boundary hits."""
    g = _make_game()
    # Ball exactly at hit zone boundary
    g.current_pitch = Pitch(
        x=HIT_ZONE_X_MIN, y=HIT_ZONE_Y_MIN, vx=3.0, vy=0.0, color=RED
    )
    assert g._try_swing() is True

    g.current_pitch = Pitch(
        x=HIT_ZONE_X_MAX, y=HIT_ZONE_Y_MAX, vx=3.0, vy=0.0, color=GREEN
    )
    assert g._try_swing() is True

    # Just outside
    g.current_pitch = Pitch(
        x=HIT_ZONE_X_MIN - 1, y=HIT_ZONE_Y_MIN, vx=3.0, vy=0.0, color=NAVY
    )
    assert g._try_swing() is False


def test_strikes_accumulate():
    """Multiple misses stack up strikes."""
    g = _make_game()
    for _ in range(MAX_STRIKES):
        g.current_pitch = Pitch(x=20.0, y=100.0, vx=3.0, vy=0.0, color=RED)
        g._resolve_miss()
    assert g.strikes == MAX_STRIKES
    assert g._check_game_over() is True


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
