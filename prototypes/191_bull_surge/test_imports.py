"""test_imports.py — Headless logic tests for BULL SURGE."""
import random
import sys
from dataclasses import is_dataclass

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/191_bull_surge")
from main import (
    BLACK, DARK_BLUE, GREEN, RED, WHITE, YELLOW,
    BUCK_COLORS, BUCK_INTERVAL_INITIAL, BUCK_INTERVAL_MIN,
    GAME_DURATION, HEAT_DECAY, HEAT_MAX, HEAT_TIMEOUT, HEAT_WRONG,
    REACTION_WINDOW, SCORE_BASE, SUPER_BUCK_INTERVAL, SUPER_DURATION,
    FloatingText, Game, Particle, Phase,
)


# ── Utility: headless game factory ──

def _make_game(**overrides) -> Game:
    """Create a Game bypassing pyxel.init, with seeded RNG."""
    g = Game.__new__(Game)
    g.phase: Phase = Phase.TITLE
    g.score: int = 0
    g.best_score: int = 0
    g.combo: int = 0
    g.max_combo: int = 0
    g.heat: float = 0.0
    g.buck_color: int = 0
    g.buck_timer: int = BUCK_INTERVAL_INITIAL
    g.reaction_timer: int = 0
    g.game_timer: int = GAME_DURATION
    g.buck_interval: int = BUCK_INTERVAL_INITIAL
    g.super_timer: int = 0
    g.shake_frames: int = 0
    g.shake_intensity: int = 0
    g.particles: list[Particle] = []
    g.floating_texts: list[FloatingText] = []
    g.game_over_reason: str = ""
    g.prev_combo: int = 0
    g.rng = random.Random(42)
    for k, v in overrides.items():
        setattr(g, k, v)
    g.reset()
    return g


# ── Data classes ──

def test_particle_dataclass():
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=30, color=RED, size=3)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 30
    assert p.color == RED
    assert p.size == 3
    assert is_dataclass(Particle)


def test_floating_text_dataclass():
    ft = FloatingText(x=100.0, y=50.0, text="+10", life=30, color=GREEN)
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "+10"
    assert ft.life == 30
    assert ft.color == GREEN
    assert ft.vy == -1.5
    assert is_dataclass(FloatingText)


# ── Phase enum ──

def test_phase_enum():
    assert Phase.TITLE.value == 0
    assert Phase.PLAYING.value == 1
    assert Phase.GAME_OVER.value == 2
    assert Phase.TITLE != Phase.PLAYING


# ── Constants ──

def test_color_constants():
    assert RED == 8
    assert GREEN == 3
    assert DARK_BLUE == 5
    assert YELLOW == 10
    assert WHITE == 7
    assert BLACK == 0
    assert len(BUCK_COLORS) == 4
    assert BUCK_COLORS == [RED, GREEN, DARK_BLUE, YELLOW]


def test_game_constants():
    assert GAME_DURATION == 3600
    assert REACTION_WINDOW == 45
    assert SUPER_DURATION == 300
    assert SUPER_BUCK_INTERVAL == 30
    assert BUCK_INTERVAL_INITIAL == 90
    assert BUCK_INTERVAL_MIN == 30
    assert HEAT_WRONG == 15.0
    assert HEAT_TIMEOUT == 15.0
    assert HEAT_DECAY == 0.02
    assert HEAT_MAX == 100.0
    assert SCORE_BASE == 10


# ── Game.reset() / _start_game() ──

def test_reset_initial_state():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.game_timer == GAME_DURATION
    assert g.super_timer == 0
    assert g.shake_frames == 0
    assert g.particles == []
    assert g.floating_texts == []


def test_start_game_transitions_to_playing():
    g = _make_game()
    g._start_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.game_timer == GAME_DURATION


def test_start_game_preserves_best_score():
    g = _make_game()
    g.best_score = 500
    g._start_game()
    assert g.best_score == 500
    assert g.score == 0


# ── _handle_match ──

def test_handle_match_correct_color_increases_combo():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.buck_color = 0  # RED
    g.reaction_timer = REACTION_WINDOW
    result = g._handle_match(0)
    assert result is True
    assert g.combo == 1
    assert g.score > 0


def test_handle_match_wrong_color_resets_combo():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 3
    g.buck_color = 0  # RED
    g.reaction_timer = REACTION_WINDOW
    result = g._handle_match(1)  # GREEN — wrong
    assert result is False
    assert g.combo == 0
    assert g.heat == HEAT_WRONG


def test_handle_match_no_reaction_window_returns_false():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.reaction_timer = 0
    result = g._handle_match(0)
    assert result is False
    assert g.combo == 0


def test_handle_match_combo_builds_super():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.rng = random.Random(42)
    # Build combo 1,2,3
    for expected_combo in [1, 2, 3]:
        g.buck_color = 0
        g.reaction_timer = REACTION_WINDOW
        result = g._handle_match(0)
        assert result is True
        assert g.combo == expected_combo
    # Combo 4 should trigger SUPER
    g.buck_color = 0
    g.reaction_timer = REACTION_WINDOW
    g.combo = 3
    result = g._handle_match(0)
    assert result is True
    assert g.combo == 4
    assert g.super_timer == SUPER_DURATION


def test_handle_match_score_scales_with_combo():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.rng = random.Random(42)

    g.combo = 0
    g.buck_color = 0
    g.reaction_timer = REACTION_WINDOW
    g._handle_match(0)
    score_c1 = g.score

    g = _make_game()
    g.phase = Phase.PLAYING
    g.rng = random.Random(42)
    g.combo = 3
    g.buck_color = 0
    g.reaction_timer = REACTION_WINDOW
    g._handle_match(0)
    score_c4 = g.score
    assert score_c4 > score_c1  # Higher combo = more points


def test_handle_match_tracks_max_combo():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.rng = random.Random(42)
    for _ in range(3):
        g.buck_color = 0
        g.reaction_timer = REACTION_WINDOW
        g._handle_match(0)
    assert g.max_combo == 3
    # Wrong match resets combo but preserves max_combo
    g.buck_color = 0  # RED
    g.reaction_timer = REACTION_WINDOW
    g._handle_match(1)  # GREEN — wrong!
    assert g.combo == 0
    assert g.max_combo == 3


def test_handle_match_wrong_adds_heat():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 0.0
    g.buck_color = 0
    g.reaction_timer = REACTION_WINDOW
    g._handle_match(1)  # wrong
    assert g.heat == HEAT_WRONG


def test_handle_match_spawns_match_particles():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.rng = random.Random(42)
    g.buck_color = 0
    g.reaction_timer = REACTION_WINDOW
    g._handle_match(0)
    assert len(g.particles) > 0  # match spawns 10 particles


def test_handle_match_spawns_floating_text():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.buck_color = 0
    g.reaction_timer = REACTION_WINDOW
    g._handle_match(0)
    assert len(g.floating_texts) > 0


def test_handle_match_wrong_spawns_miss_particles():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.rng = random.Random(42)
    g.buck_color = 0
    g.reaction_timer = REACTION_WINDOW
    g._handle_match(1)
    assert len(g.particles) == 5  # miss spawns 5 particles


# ── _handle_timeout ──

def test_handle_timeout_resets_combo():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.combo = 3
    g._handle_timeout()
    assert g.combo == 0
    assert g.heat == HEAT_TIMEOUT


def test_handle_timeout_caps_heat():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 95.0
    g._handle_timeout()
    assert g.heat == HEAT_MAX


# ── _activate_super ──

def test_activate_super_sets_timer():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.rng = random.Random(42)
    g._activate_super()
    assert g.super_timer == SUPER_DURATION
    assert g.shake_frames == 15
    assert len(g.particles) == 20
    assert len(g.floating_texts) > 0


# ── _update_heat ──

def test_update_heat_decay():
    g = _make_game()
    g.heat = 10.0
    g._update_heat()
    assert g.heat == 10.0 - HEAT_DECAY


def test_update_heat_min_zero():
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_no_negative():
    g = _make_game()
    g.heat = HEAT_DECAY / 2
    g._update_heat()
    assert g.heat == 0.0


# ── _update_super_mode ──

def test_update_super_mode_decrements_timer():
    g = _make_game()
    g.super_timer = 10
    g._update_super_mode()
    assert g.super_timer == 9


def test_update_super_mode_expires_resets_combo():
    g = _make_game()
    g.super_timer = 1
    g.combo = 5
    g._update_super_mode()
    assert g.super_timer == 0
    assert g.combo == 0


# ── _update_difficulty ──

def test_update_difficulty_initial():
    g = _make_game()
    g.game_timer = GAME_DURATION
    g._update_difficulty()
    assert g.buck_interval == BUCK_INTERVAL_INITIAL


def test_update_difficulty_decreases_over_time():
    g = _make_game()
    g.game_timer = GAME_DURATION - 30 * 60  # 30s elapsed
    g._update_difficulty()
    assert g.buck_interval < BUCK_INTERVAL_INITIAL
    assert g.buck_interval >= BUCK_INTERVAL_MIN


def test_update_difficulty_clamped_to_min():
    g = _make_game()
    g.game_timer = 0  # 60s elapsed
    g._update_difficulty()
    assert g.buck_interval == BUCK_INTERVAL_MIN


# ── _get_score_multiplier ──

def test_score_multiplier_normal():
    g = _make_game()
    g.super_timer = 0
    assert g._get_score_multiplier() == 1.0


def test_score_multiplier_super():
    g = _make_game()
    g.super_timer = 100
    assert g._get_score_multiplier() == 3.0


# ── _spawn_buck ──

def test_spawn_buck_sets_reaction_window():
    g = _make_game()
    g.rng = random.Random(42)
    g._spawn_buck()
    assert g.reaction_timer == REACTION_WINDOW
    assert g.buck_timer == g.buck_interval


def test_spawn_buck_during_super_no_reaction_window():
    g = _make_game()
    g.rng = random.Random(42)
    g.super_timer = 100
    g._spawn_buck()
    assert g.reaction_timer == 0
    assert g.buck_timer == SUPER_BUCK_INTERVAL


# ── _update_buck_timers ──

def test_update_buck_timers_decrements_reaction():
    g = _make_game()
    g.reaction_timer = 10
    g._update_buck_timers()
    assert g.reaction_timer == 9


def test_update_buck_timers_timeout_triggers():
    g = _make_game()
    g.reaction_timer = 1
    g.combo = 2
    g.rng = random.Random(42)
    g._update_buck_timers()
    assert g.combo == 0
    assert g.heat == HEAT_TIMEOUT


def test_update_buck_timers_spawns_buck_when_timer_expires():
    g = _make_game()
    g.rng = random.Random(42)
    g.reaction_timer = 0
    g.buck_timer = 1
    g.super_timer = 0
    g._update_buck_timers()
    assert g.reaction_timer == REACTION_WINDOW
    assert g.buck_timer == g.buck_interval


def test_update_buck_timers_auto_match_in_super():
    g = _make_game()
    g.rng = random.Random(42)
    g.reaction_timer = 0
    g.super_timer = 100
    g.buck_timer = 1
    g.combo = 2
    g._update_buck_timers()
    assert g.combo == 3  # auto-matched
    assert g.buck_timer == SUPER_BUCK_INTERVAL


# ── _auto_match ──

def test_auto_match_increases_combo_and_score():
    g = _make_game()
    g.rng = random.Random(42)
    g.super_timer = 100  # so multiplier is 3.0
    g.combo = 2
    g.score = 100
    g._auto_match()
    assert g.combo == 3
    assert g.score > 100
    assert g.max_combo == 3


# ── _update_playing ──

def test_update_playing_decrements_game_timer():
    g = _make_game()
    g.phase = Phase.PLAYING
    g._update_playing()
    assert g.game_timer == GAME_DURATION - 1


def test_update_playing_time_up_game_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.game_timer = 1
    g.score = 200
    g.best_score = 100
    g._update_playing()
    assert g.game_timer == 0
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 200
    assert g.game_over_reason == "TIME'S UP!"


def test_update_playing_heat_game_over():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = HEAT_MAX
    g.score = 200
    g.best_score = 100
    g._update_playing()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 200
    assert g.game_over_reason == "THROWN OFF!"


def test_update_playing_does_not_override_best_score():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = HEAT_MAX
    g.score = 50
    g.best_score = 500
    g._update_playing()
    assert g.phase == Phase.GAME_OVER
    assert g.best_score == 500  # not overwritten


# ── _update_particles ──

def test_update_particles_removes_dead():
    g = _make_game()
    g.particles = [
        Particle(0, 0, 0, 0, 1, RED),
        Particle(0, 0, 0, 0, 2, GREEN),
    ]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 1


def test_update_particles_applies_gravity():
    g = _make_game()
    p = Particle(0, 0, 0, 0, 10, RED)
    expected_vy = p.vy + 0.1
    g.particles = [p]
    g._update_particles()
    assert abs(g.particles[0].vy - expected_vy) < 0.001


# ── _update_floating_texts ──

def test_update_floating_texts_removes_expired():
    g = _make_game()
    g.floating_texts = [
        FloatingText(0, 0, "+10", 1, RED),
        FloatingText(0, 0, "+20", 2, GREEN),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].life == 1


def test_update_floating_texts_moves_upward():
    g = _make_game()
    ft = FloatingText(100, 100, "+10", 10, RED, vy=-1.5)
    g.floating_texts = [ft]
    g._update_floating_texts()
    assert g.floating_texts[0].y == 100.0 - 1.5


# ── Best score persistence ──

def test_best_score_persists_across_runs():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.score = 300
    g.heat = HEAT_MAX
    g._update_playing()
    assert g.best_score == 300

    g._start_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.best_score == 300


# ── SUPER RIDE full flow ──

def test_super_ride_full_activation_flow():
    g = _make_game()
    g.rng = random.Random(42)
    g.phase = Phase.PLAYING
    # Build combo 1-3
    for _ in range(3):
        g.buck_color = 0
        g.reaction_timer = REACTION_WINDOW
        g._handle_match(0)
    assert g.combo == 3
    assert g.super_timer == 0
    # Combo 4 triggers SUPER
    g.buck_color = 0
    g.reaction_timer = REACTION_WINDOW
    g._handle_match(0)
    assert g.combo == 4
    assert g.super_timer == SUPER_DURATION
    assert g._get_score_multiplier() == 3.0


def test_super_score_multiplier_applied():
    g = _make_game()
    g.rng = random.Random(42)
    g.phase = Phase.PLAYING
    g.combo = 3
    g.buck_color = 0
    g.reaction_timer = REACTION_WINDOW
    # This triggers SUPER and applies 3x
    score_before = g.score
    g._handle_match(0)
    assert g.score > score_before
    # During SUPER, multiplier is 3x
    assert g._get_score_multiplier() == 3.0


# ── Edge cases ──

def test_heat_capped_at_max_via_handle_match():
    g = _make_game()
    g.heat = 95.0
    g.buck_color = 0
    g.reaction_timer = REACTION_WINDOW
    g._handle_match(1)  # wrong — adds HEAT_WRONG=15, should cap at 100
    assert g.heat == HEAT_MAX


def test_handle_match_heat_capped():
    g = _make_game()
    g.heat = 95.0
    g.buck_color = 0
    g.reaction_timer = REACTION_WINDOW
    g._handle_match(1)  # wrong
    assert g.heat == HEAT_MAX


def test_super_reactivation_extends_duration():
    g = _make_game()
    g.rng = random.Random(42)
    g.super_timer = 100
    g.combo = 3  # simulate combo at 3 in super
    g.phase = Phase.PLAYING
    # During super, auto_match handles buck, but _handle_match can also trigger
    g.buck_color = 0
    g.reaction_timer = REACTION_WINDOW
    # Since super_timer > 0, _spawn_buck won't set reaction_timer normally
    # but if we manually set it for testing:
    g._handle_match(0)
    # Should have re-activated super (reset to 300)
    assert g.super_timer == SUPER_DURATION


def test_score_always_integer():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.buck_color = 0
    g.reaction_timer = REACTION_WINDOW
    g._handle_match(0)
    assert isinstance(g.score, int)


def test_particle_list_clears_on_start():
    g = _make_game()
    g.particles = [Particle(0, 0, 0, 0, 1, RED)]
    g._start_game()
    assert g.particles == []


def test_floating_texts_clear_on_start():
    g = _make_game()
    g.floating_texts = [FloatingText(0, 0, "test", 1, RED)]
    g._start_game()
    assert g.floating_texts == []


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-x"])
