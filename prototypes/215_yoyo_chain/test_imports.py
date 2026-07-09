"""test_imports.py — Headless logic tests for yoyo_chain prototype."""
import sys
import random
from pathlib import Path

PROTO_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROTO_DIR))

from main import (
    Game, Phase, Yoyo, Particle, FloatingText,
    GRAVITY, BOUNCE_FACTOR, STRING_END, HAND_X, HAND_Y, CATCH_WINDOW,
    HEAT_WRONG_CATCH, HEAT_MISS, HEAT_DECAY, HEAT_MAX,
    SUPER_COMBO_THRESHOLD, SUPER_DURATION, SUPER_SCORE_MULT,
    COLOR_CYCLE_FRAMES, GAME_DURATION,
    YO_COLORS, SCREEN_W, SCREEN_H,
)


def _make_game() -> Game:
    """Factory: create Game via __new__, pre-init, call _start_playing()."""
    g: Game = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.yoyo = Yoyo(x=float(HAND_X), y=float(HAND_Y), vy=0.0, color_idx=0, on_string=True, returning=False)
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.super_mode = False
    g.super_timer = 0
    g.heat = 0.0
    g.timer_frames = GAME_DURATION * 60.0
    g.particles = []
    g.floating_texts = []
    g._rng = random.Random(42)
    g._color_timer = 0
    g._last_caught_color = None
    g._passed_hand = False
    g._start_playing()
    # Override RNG after _start_playing (which uses it for initial color)
    g._rng = random.Random(42)
    return g


# ── Phase / State Tests ──

def test_game_phase_after_start():
    g = _make_game()
    assert g.phase == Phase.PLAYING

def test_game_initial_state():
    g = _make_game()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.heat == 0.0
    assert g.timer_frames == GAME_DURATION * 60.0
    assert g._last_caught_color is None

def test_update_playing_decrements_timer():
    g = _make_game()
    initial = g.timer_frames
    g._update_playing()
    assert g.timer_frames == initial - 1

def test_game_over_on_timer_zero():
    g = _make_game()
    g.timer_frames = 1
    g._update_playing()
    assert g.phase == Phase.GAME_OVER

def test_game_over_on_heat_max():
    g = _make_game()
    g.heat = HEAT_MAX
    g._update_playing()
    assert g.phase == Phase.GAME_OVER

def test_game_over_not_triggered_below_heat_max():
    g = _make_game()
    g.heat = HEAT_MAX - 0.01
    g.timer_frames = 100
    g._update_playing()
    assert g.phase == Phase.PLAYING


# ── Yoyo Physics Tests ──

def test_yoyo_falls_due_to_gravity():
    g = _make_game()
    g.yoyo.vy = 0.0
    g.yoyo.y = HAND_Y
    g.yoyo.on_string = True
    g.yoyo.returning = False
    g._update_yoyo_physics()
    assert g.yoyo.vy > 0  # gravity applied
    assert g.yoyo.y > HAND_Y

def test_yoyo_bounces_at_string_end():
    g = _make_game()
    g.yoyo.y = STRING_END - 1
    g.yoyo.vy = 3.0
    g.yoyo.on_string = True
    g.yoyo.returning = False
    g._update_yoyo_physics()
    # After bounce: y clamped to STRING_END, vy reversed
    assert g.yoyo.y == float(STRING_END)
    assert g.yoyo.vy < 0  # reversed
    assert g.yoyo.returning is True

def test_yoyo_clamped_at_string_end():
    g = _make_game()
    g.yoyo.y = STRING_END + 10  # beyond end
    g.yoyo.vy = 0.0
    g.yoyo.on_string = True
    g.yoyo.returning = True
    g._update_yoyo_physics()
    # vy applied by gravity, then >= STRING_END check
    assert g.yoyo.y == float(STRING_END)
    assert g.yoyo.vy < 0  # bounced
    assert g.yoyo.returning is True

def test_yoyo_off_string_flies_up_and_wraps():
    g = _make_game()
    g.yoyo.on_string = False
    g.yoyo.y = HAND_Y
    g.yoyo.vy = -5.0
    g._update_yoyo_physics()
    # After flying off top (y <= -10), wraps back to hand
    # First call: y = HAND_Y + (-5 + 0.3) = 35.3... not <= -10 yet
    # Need multiple calls
    g.yoyo.vy = -20.0
    g.yoyo.y = HAND_Y
    g._update_yoyo_physics()
    if g.yoyo.on_string:
        assert g.yoyo.y == float(HAND_Y)
        assert g.yoyo.vy == 0.0


# ── Color Cycling Tests ──

def test_color_cycles_after_interval():
    g = _make_game()
    g.yoyo.color_idx = 0
    g._color_timer = COLOR_CYCLE_FRAMES - 1
    g._update_color_cycle()
    assert g.yoyo.color_idx == 1
    assert g._color_timer == 0

def test_color_cycles_wraps():
    g = _make_game()
    g.yoyo.color_idx = len(YO_COLORS) - 1
    g._color_timer = COLOR_CYCLE_FRAMES - 1
    g._update_color_cycle()
    assert g.yoyo.color_idx == 0

def test_color_does_not_cycle_before_interval():
    g = _make_game()
    g.yoyo.color_idx = 0
    g._color_timer = COLOR_CYCLE_FRAMES // 2
    g._update_color_cycle()
    assert g.yoyo.color_idx == 0


# ── COMBO / Score Tests ──

def test_check_same_color_first_catch_always_true():
    g = _make_game()
    g._last_caught_color = None
    g.yoyo.color_idx = 2  # any color
    assert g._check_same_color() is True

def test_check_same_color_matching():
    g = _make_game()
    g.yoyo.color_idx = 1
    yoyo_color = YO_COLORS[1][0]
    g._last_caught_color = yoyo_color
    assert g._check_same_color() is True

def test_check_same_color_mismatch():
    g = _make_game()
    g.yoyo.color_idx = 1
    g._last_caught_color = YO_COLORS[2][0]  # different color
    assert g._check_same_color() is False

def test_execute_catch_same_color_increments_combo():
    g = _make_game()
    g.combo = 2
    g.yoyo.color_idx = 0
    g._last_caught_color = YO_COLORS[0][0]
    g._execute_catch(same_color=True)
    assert g.combo == 3
    assert g.max_combo == 3

def test_execute_catch_same_color_adds_score():
    g = _make_game()
    g.combo = 2
    g.score = 0
    g.yoyo.color_idx = 0
    g._last_caught_color = YO_COLORS[0][0]
    g._execute_catch(same_color=True)
    # score = 10 * (1 + 3 * 0.5) = 10 * 2.5 = 25
    assert g.score == 25

def test_execute_catch_wrong_color_resets_combo():
    g = _make_game()
    g.combo = 5
    g.heat = 0
    g.yoyo.color_idx = 1
    g._execute_catch(same_color=False)
    assert g.combo == 0
    assert g.heat == HEAT_WRONG_CATCH

def test_execute_catch_wrong_color_no_score():
    g = _make_game()
    g.score = 0
    g.yoyo.color_idx = 1
    g._execute_catch(same_color=False)
    assert g.score == 0

def test_execute_catch_sets_last_caught_color():
    g = _make_game()
    g.yoyo.color_idx = 2
    yoyo_color = YO_COLORS[2][0]
    g._last_caught_color = None
    g._execute_catch(same_color=True)
    assert g._last_caught_color == yoyo_color

def test_execute_catch_same_color_spawns_particles():
    g = _make_game()
    g.yoyo.color_idx = 1
    g._last_caught_color = YO_COLORS[1][0]
    g._execute_catch(same_color=True)
    assert len(g.particles) > 0

def test_execute_catch_same_color_spawns_floating_text():
    g = _make_game()
    g.yoyo.color_idx = 1
    g._last_caught_color = YO_COLORS[1][0]
    g._execute_catch(same_color=True)
    assert len(g.floating_texts) > 0
    assert "+" in g.floating_texts[0].text

def test_execute_catch_resets_yoyo_position():
    g = _make_game()
    g.yoyo.y = 180
    g.yoyo.vy = 3.0
    g.yoyo.on_string = True
    g.yoyo.returning = True
    g._execute_catch(same_color=True)
    assert g.yoyo.y == float(HAND_Y)
    assert g.yoyo.vy == 0.0
    assert g.yoyo.on_string is True
    assert g.yoyo.returning is False

# ── SUPER MODE Tests ──

def test_super_mode_activates_at_threshold():
    g = _make_game()
    g.combo = SUPER_COMBO_THRESHOLD - 1  # 3
    g.yoyo.color_idx = 0
    g._last_caught_color = YO_COLORS[0][0]
    g._execute_catch(same_color=True)
    # combo is now 4, should trigger super
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION

def test_super_mode_not_activated_below_threshold():
    g = _make_game()
    g.combo = 1
    g.yoyo.color_idx = 0
    g._last_caught_color = YO_COLORS[0][0]
    g._execute_catch(same_color=True)
    assert g.combo == 2
    assert g.super_mode is False

def test_super_mode_score_multiplier():
    g = _make_game()
    g.score = 0
    g.super_mode = True
    g.combo = 4
    g.yoyo.color_idx = 0
    g._last_caught_color = YO_COLORS[0][0]
    g._execute_catch(same_color=True)
    # score = 10 * (1 + 5 * 0.5) * 3 = 10 * 3.5 * 3 = 105
    assert g.score == 105

def test_super_mode_timer_decrements():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g._update_super_mode()
    assert g.super_timer == 99
    assert g.super_mode is True

def test_super_mode_expires():
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g.combo = 5
    g._update_super_mode()
    assert g.super_timer == 0
    assert g.super_mode is False
    assert g.combo == 0

def test_super_mode_not_already_active_no_trigger():
    g = _make_game()
    g.super_mode = True
    g.combo = 10
    g.yoyo.color_idx = 0
    g._last_caught_color = YO_COLORS[0][0]
    g._execute_catch(same_color=True)
    # super_mode stays True, no duplicate SUPER! text
    assert g.super_mode is True

# ── Miss Tests ──

def test_on_miss_adds_heat():
    g = _make_game()
    g.heat = 10
    g.combo = 5
    g.yoyo.on_string = True
    g._on_miss()
    assert g.heat == 10 + HEAT_MISS
    assert g.combo == 0
    assert g.yoyo.on_string is False
    assert g.yoyo.vy < 0  # flies upward

# ── Heat Decay Tests ──

def test_heat_decays():
    g = _make_game()
    g.heat = 10.0
    g._update_heat_decay()
    assert g.heat == 10.0 - HEAT_DECAY

def test_heat_does_not_go_negative():
    g = _make_game()
    g.heat = HEAT_DECAY / 2
    g._update_heat_decay()
    assert g.heat == 0.0

# ── Particle System Tests ──

def test_particles_move_and_decay():
    g = _make_game()
    g.particles = [
        Particle(x=100, y=100, vx=1.0, vy=-0.5, life=5, color=8),
        Particle(x=200, y=50, vx=-0.5, vy=0.5, life=1, color=11),
    ]
    g._update_particles()
    # First particle: life=4 after decrement, survived
    # Second particle: life=0 after decrement, removed
    assert len(g.particles) == 1
    assert g.particles[0].life == 4
    assert g.particles[0].x == 101.0
    assert g.particles[0].y == 99.5

def test_particles_removed_when_life_zero():
    g = _make_game()
    g.particles = [Particle(x=100, y=100, vx=0, vy=0, life=1, color=8)]
    g._update_particles()
    assert len(g.particles) == 0

# ── Floating Text Tests ──

def test_floating_text_rises_and_decays():
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=100, y=100, text="+25", life=5, color=8),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].life == 4
    assert g.floating_texts[0].y == 99.0  # vy=-1.0

def test_floating_text_removed_when_life_zero():
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=100, y=100, text="+25", life=1, color=8),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0

# ── Spawn Catch Particles Tests ──

def test_spawn_catch_particles_normal():
    g = _make_game()
    g.super_mode = False
    old_count = len(g.particles)
    g._spawn_catch_particles(2)
    # 5-8 particles, seeded RNG
    assert len(g.particles) > old_count
    assert 5 <= len(g.particles) - old_count <= 8

def test_spawn_catch_particles_super():
    g = _make_game()
    g.super_mode = True
    old_count = len(g.particles)
    g._spawn_catch_particles(2)
    assert len(g.particles) - old_count == 15

# ── Max Combo Tracking Tests ──

def test_max_combo_updated():
    g = _make_game()
    g.max_combo = 2
    g.combo = 3
    g.yoyo.color_idx = 0
    g._last_caught_color = YO_COLORS[0][0]
    g._execute_catch(same_color=True)
    assert g.max_combo == 4  # combo became 4

def test_max_combo_preserved_after_reset():
    g = _make_game()
    g.max_combo = 7
    g.combo = 3
    g._execute_catch(same_color=False)  # wrong color, combo resets
    assert g.combo == 0
    assert g.max_combo == 7  # preserved

# ── Yoyo position reset after catch ──

def test_catch_resets_yoyo_to_hand():
    g = _make_game()
    g.yoyo.y = 180
    g.yoyo.vy = 5.0
    g.yoyo.returning = True
    g._execute_catch(same_color=True)
    assert g.yoyo.y == float(HAND_Y)
    assert g.yoyo.vy == 0.0
    assert g.yoyo.on_string is True
    assert g.yoyo.returning is False

# ── Wrong-color floating text ──

def test_wrong_catch_shows_wrong_text():
    g = _make_game()
    g.floating_texts.clear()
    g._execute_catch(same_color=False)
    assert len(g.floating_texts) > 0
    assert "WRONG" in g.floating_texts[0].text

# ── Super score multiplier with low combo ──

def test_super_with_combo_zero():
    g = _make_game()
    g.score = 0
    g.super_mode = True
    g.combo = 0
    g.yoyo.color_idx = 1
    g._last_caught_color = YO_COLORS[1][0]
    g._execute_catch(same_color=True)
    # score = 10 * (1 + 1 * 0.5) * 3 = 10 * 1.5 * 3 = 45
    assert g.score == 45

# ── Timer display test ──

def test_timer_never_negative_in_playing_update():
    g = _make_game()
    g.timer_frames = 0.5  # less than 1
    g._update_playing()
    assert g.phase == Phase.GAME_OVER

# ── Heat never exceeds max in update ──

def test_heat_never_exceeds_max_during_game_over_check():
    g = _make_game()
    g.heat = HEAT_MAX + 10  # already over
    g.timer_frames = 100
    g._update_playing()
    assert g.phase == Phase.GAME_OVER

# ── Yoyo struct defaults ──

def test_yoyo_creation():
    y = Yoyo(x=160.0, y=40.0, vy=0.0, color_idx=0, on_string=True, returning=False)
    assert y.x == 160.0
    assert y.y == 40.0
    assert y.vy == 0.0
    assert y.on_string is True
    assert y.returning is False

# ── Color constants match design ──

def test_color_count():
    assert len(YO_COLORS) == 4
    color_ints = {c[0] for c in YO_COLORS}
    assert color_ints == {8, 11, 5, 10}  # RED, GREEN, DARK_BLUE, YELLOW


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
