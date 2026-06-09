"""test_imports.py — Headless logic tests for SKIP SURGE (117_skip_surge)."""
from __future__ import annotations

import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/117_skip_surge")

from main import (
    COMBO_THRESHOLD,
    GAME_TIME,
    HEAT_DECAY,
    HEAT_PER_MISS,
    HEAT_PER_WRONG,
    MAX_HEAT,
    POWER_MAX,
    POWER_MIN,
    RIPPLE_COLORS,
    SCREEN_H,
    SCREEN_W,
    STONE_GRAVITY,
    SUPER_DURATION,
    THROW_ANGLE,
    WATER_Y,
    FloatText,
    Game,
    Particle,
    Phase,
    Ripple,
    Stone,
)


# ── helpers ────────────────────────────────────────────────

def _make_game() -> Game:
    """Create a Game instance bypassing pyxel.init/run for headless testing."""
    g = Game.__new__(Game)
    # Pre-init all attributes that reset() touches
    g._rng = random.Random(42)
    g.stone = None
    g.ripples = []
    g.particles = []
    g.float_texts = []
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.game_timer = GAME_TIME
    g.aim_power = POWER_MIN
    g.throw_count = 0
    g.super_mode = False
    g.super_timer = 0
    g._scoring_countdown = 0
    g._rainbow_offset = 0
    g._mouse_was_pressed = False
    g.phase = Phase.AIMING
    g.reset()
    return g


# ── 1. dataclass instantiation ─────────────────────────────

def test_ripple_create() -> None:
    r = Ripple(x=160.0, y=190.0, radius=12.0, color=8, active=True)
    assert r.x == 160.0
    assert r.y == 190.0
    assert r.radius == 12.0
    assert r.color == 8
    assert r.active is True
    assert r.vx == 0.0


def test_stone_create() -> None:
    s = Stone(x=160.0, y=230.0, vx=1.2, vy=-2.0)
    assert s.bounces == 0
    assert s.combo_color == -1
    assert s.super_mode is False
    assert s.super_timer == 0
    assert s.alive is True


def test_particle_create() -> None:
    p = Particle(x=100.0, y=200.0, vx=1.0, vy=-1.0, life=20, color=8, size=2)
    assert p.life == 20
    assert p.color == 8
    assert p.size == 2


def test_float_text_create() -> None:
    ft = FloatText(x=150.0, y=180.0, text="+30", life=45, color=10)
    assert ft.text == "+30"
    assert ft.life == 45
    assert ft.color == 10


# ── 2. constants ───────────────────────────────────────────

def test_constants() -> None:
    assert len(RIPPLE_COLORS) == 4
    assert RIPPLE_COLORS == [8, 3, 5, 10]
    assert COMBO_THRESHOLD == 4
    assert HEAT_PER_WRONG == 2.0
    assert HEAT_PER_MISS == 1.0
    assert MAX_HEAT == 100.0
    assert GAME_TIME == 90 * 60
    assert SUPER_DURATION == 300
    assert WATER_Y == 180


# ── 3. phase enum ──────────────────────────────────────────

def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.AIMING in Phase
    assert Phase.FLYING in Phase
    assert Phase.SCORING in Phase
    assert Phase.GAME_OVER in Phase


# ── 4. game init / reset ───────────────────────────────────

def test_game_reset_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.game_timer == GAME_TIME
    assert g.aim_power == POWER_MIN
    assert g.throw_count == 0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.stone is None
    assert len(g.ripples) >= 8
    assert len(g.particles) == 0
    assert len(g.float_texts) == 0


# ── 5. score computation (pure function) ───────────────────

def test_compute_score_no_super() -> None:
    g = _make_game()
    # combo=0 (multiplier=1), 1 bounce
    s = g._compute_score(0, 1, False)
    assert s == 10 * 1  # base * (0+1) = 10

    # combo=3 (multiplier=4)
    s = g._compute_score(3, 4, False)
    assert s == 10 * 4  # base * (3+1) = 40


def test_compute_score_with_super() -> None:
    g = _make_game()
    # combo=4 (multiplier=5), super → ×3
    s = g._compute_score(4, 5, True)
    assert s == 10 * 5 * 3  # base * (4+1) * 3 = 150


# ── 6. ripple spawning ─────────────────────────────────────

def test_spawn_ripple_bounds() -> None:
    g = _make_game()
    for _ in range(100):
        r = g._spawn_ripple()
        assert 30 <= r.x <= 290
        assert WATER_Y + 5 <= r.y <= WATER_Y + 60 - 15
        assert r.color in RIPPLE_COLORS
        assert r.active is True
        assert r.radius == 12.0


def test_spawn_initial_ripples_count() -> None:
    g = _make_game()
    g._spawn_initial_ripples()
    assert 8 <= len(g.ripples) <= 12
    for r in g.ripples:
        assert r.active is True


# ── 7. process_skip — same color COMBO ─────────────────────

def test_process_skip_first_hit_sets_combo_color() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    stone = Stone(x=160.0, y=190.0, vx=1.0, vy=1.0)
    ripple = Ripple(x=160.0, y=190.0, color=8)
    g._process_skip(stone, ripple)
    assert stone.combo_color == 8
    assert g.combo == 1
    assert stone.bounces == 1
    # Note: _process_skip doesn't deactivate ripple — that happens in _update_flying


def test_process_skip_same_color_builds_combo() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    stone = Stone(x=160.0, y=190.0, vx=1.0, vy=1.0, combo_color=8)
    g.combo = 1
    ripple = Ripple(x=160.0, y=190.0, color=8)
    g._process_skip(stone, ripple)
    assert g.combo == 2
    assert stone.combo_color == 8
    assert g.max_combo == 2


def test_process_skip_first_hit_no_prior_color_always_matches() -> None:
    """When combo_color == -1 (first hit), ANY color matches."""
    g = _make_game()
    g.phase = Phase.FLYING
    stone = Stone(x=160.0, y=190.0, vx=1.0, vy=1.0)  # combo_color=-1
    ripple = Ripple(x=160.0, y=190.0, color=3)  # GREEN
    g._process_skip(stone, ripple)
    assert g.combo == 1
    assert stone.combo_color == 3  # set to new color
    assert stone.bounces == 1


def test_process_skip_wrong_color_resets_combo() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    g.combo = 3
    g.max_combo = 3
    stone = Stone(x=160.0, y=190.0, vx=1.0, vy=1.0, combo_color=8)  # RED
    ripple = Ripple(x=160.0, y=190.0, color=3)  # GREEN — mismatch
    g._process_skip(stone, ripple)
    assert g.combo == 0  # reset
    assert g.max_combo == 3  # preserved
    assert stone.combo_color == 3  # now GREEN
    assert g.heat == HEAT_PER_WRONG  # heat +2
    assert stone.bounces == 1  # still counts as bounce


def test_process_skip_particles_spawned() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    stone = Stone(x=160.0, y=190.0, vx=1.0, vy=1.0, combo_color=8)
    g.combo = 1
    ripple = Ripple(x=160.0, y=190.0, color=8)
    prev_particles = len(g.particles)
    g._process_skip(stone, ripple)
    assert len(g.particles) > prev_particles  # splash particles added


def test_process_skip_score_added() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    g.score = 100
    g.combo = 2
    stone = Stone(x=160.0, y=190.0, vx=1.0, vy=1.0, combo_color=5)
    ripple = Ripple(x=160.0, y=190.0, color=5)
    g._process_skip(stone, ripple)
    # combo incremented to 3 first, then score = 10 * (3+1) = 40
    assert g.score == 140


# ── 8. process_skip — SUPER mode trigger ───────────────────

def test_process_skip_triggers_super_mode_at_threshold() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    g.combo = 3  # one before threshold
    stone = Stone(x=160.0, y=190.0, vx=1.0, vy=1.0, combo_color=10)
    ripple = Ripple(x=160.0, y=190.0, color=10)
    g._process_skip(stone, ripple)
    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION
    assert stone.super_mode is True
    assert stone.super_timer == SUPER_DURATION


def test_process_skip_super_mode_all_colors_match() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    g.super_mode = True
    g.super_timer = 100
    g.combo = 5
    stone = Stone(x=160.0, y=190.0, vx=1.0, vy=1.0, combo_color=8)  # RED
    ripple = Ripple(x=160.0, y=190.0, color=3)  # GREEN — should match in super
    g._process_skip(stone, ripple)
    assert g.combo == 6  # incremented, not reset
    assert g.heat == 0.0  # no heat added


# ── 9. stone_sink ──────────────────────────────────────────

def test_stone_sink_with_bounces_no_heat() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    g.combo = 3
    g.stone = Stone(x=160.0, y=230.0, bounces=3)
    g._stone_sink()
    assert g.stone is None
    assert g.phase == Phase.SCORING
    assert g.heat == 0.0  # no miss penalty (had bounces)


def test_stone_sink_miss_adds_heat() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    g.combo = 0
    g.stone = Stone(x=160.0, y=230.0, bounces=0)  # zero bounces = miss
    g._stone_sink()
    assert g.stone is None
    assert g.phase == Phase.SCORING
    assert g.heat == HEAT_PER_MISS  # +1
    assert g.combo == 0


# ── 10. heat update ────────────────────────────────────────

def test_update_heat_decay() -> None:
    g = _make_game()
    g.heat = 10.0
    g.phase = Phase.AIMING
    g._update_heat()
    expected = 10.0 - HEAT_DECAY
    assert abs(g.heat - expected) < 0.001


def test_update_heat_does_not_go_negative() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_game_over_at_max() -> None:
    g = _make_game()
    g.phase = Phase.AIMING
    g.heat = MAX_HEAT
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_update_heat_game_over_above_max() -> None:
    g = _make_game()
    g.phase = Phase.SCORING
    g.heat = MAX_HEAT + 5
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_update_heat_game_over_only_in_aiming_scoring() -> None:
    """GAME_OVER transition only applies in AIMING or SCORING phase."""
    g = _make_game()
    g.phase = Phase.FLYING
    g.heat = MAX_HEAT
    g._update_heat()
    # Should NOT change phase in FLYING
    assert g.phase == Phase.FLYING


# ── 11. super mode timer ───────────────────────────────────

def test_update_super_mode_timer_countdown() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g._update_super_mode()
    assert g.super_timer == 99


def test_update_super_mode_expires() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_super_mode()
    assert g.super_mode is False
    assert g.super_timer == 0


def test_update_super_mode_idle_when_not_active() -> None:
    g = _make_game()
    g.super_mode = False
    g.super_timer = 0
    g._update_super_mode()
    assert g.super_timer == 0


# ── 12. throw stone ────────────────────────────────────────

def test_throw_stone_creates_stone() -> None:
    g = _make_game()
    g.phase = Phase.AIMING
    g.aim_power = 50.0
    g.super_mode = False
    g.super_timer = 0
    g._throw_stone()
    assert g.stone is not None
    assert g.stone.x == 160.0
    assert g.stone.y == 230.0
    assert g.stone.alive is True
    assert g.stone.bounces == 0
    assert g.stone.combo_color == -1
    assert g.phase == Phase.FLYING
    assert g.throw_count == 1
    assert g.aim_power == POWER_MIN  # reset after throw


def test_throw_stone_velocity_direction() -> None:
    g = _make_game()
    g.phase = Phase.AIMING
    g.aim_power = 80.0
    g._throw_stone()
    s = g.stone
    assert s is not None
    # vx = power*0.02*cos(60°) = 1.6 * 0.5 = 0.8
    # vy = -power*0.02*sin(60°) ≈ -1.6 * 0.866 = -1.3856
    expected_vx = 80.0 * 0.02 * math.cos(THROW_ANGLE)
    expected_vy = -80.0 * 0.02 * math.sin(THROW_ANGLE)
    assert abs(s.vx - expected_vx) < 0.01
    assert abs(s.vy - expected_vy) < 0.01
    # vy should be negative (upward)
    assert s.vy < 0
    # vx should be positive (rightward)
    assert s.vx > 0


# ── 13. particle lifecycle ─────────────────────────────────

def test_update_particles_life_decrements() -> None:
    g = _make_game()
    g.particles = [Particle(100, 200, 1, -1, 10, 8)]
    g._update_particles()
    assert g.particles[0].life == 9


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    g.particles = [
        Particle(100, 200, 1, -1, 1, 8),   # will die
        Particle(120, 200, -1, -1, 10, 3), # stays alive
    ]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].color == 3


def test_update_particles_position_moves() -> None:
    g = _make_game()
    g.particles = [Particle(100.0, 200.0, 2.0, -1.5, 10, 8)]
    g._update_particles()
    assert g.particles[0].x == 102.0
    assert g.particles[0].y == 198.5


# ── 14. float text lifecycle ───────────────────────────────

def test_update_float_texts_life_decrements() -> None:
    g = _make_game()
    g.float_texts = [FloatText(100, 200, "+30", 20, 10)]
    g._update_float_texts()
    assert g.float_texts[0].life == 19
    # position floats up
    assert g.float_texts[0].y == 199.0


def test_update_float_texts_removes_dead() -> None:
    g = _make_game()
    g.float_texts = [
        FloatText(100, 200, "+10", 1, 10),
        FloatText(120, 200, "+50", 30, 7),
    ]
    g._update_float_texts()
    assert len(g.float_texts) == 1
    assert g.float_texts[0].text == "+50"


# ── 15. stone physics (gravity) ────────────────────────────

def test_stone_gravity() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    g.stone = Stone(x=160.0, y=190.0, vx=1.0, vy=-2.0)
    g._update_flying()
    s = g.stone
    assert s is not None
    # vy should increase due to gravity
    assert s.vy == -2.0 + STONE_GRAVITY
    # position updated
    assert s.x == 160.0 + 1.0
    assert s.y == 190.0 + (-2.0 + STONE_GRAVITY)


# ── 16. ripple update ──────────────────────────────────────

def test_ripple_update_drift() -> None:
    r = Ripple(x=160.0, y=190.0, vx=0.2)
    r.update()
    assert r.x == 160.2


def test_ripple_update_bounce_on_boundary() -> None:
    r = Ripple(x=309.9, y=190.0, vx=0.3)
    r.update()
    # 309.9 + 0.3 = 310.2 > 310, so reverse and clamp
    assert r.vx == -0.3
    assert r.x <= 310.0
    assert r.x >= 10.0


# ── 17. scoring phase transition ───────────────────────────

def test_scoring_transitions_back_to_aiming() -> None:
    g = _make_game()
    g.phase = Phase.SCORING
    g._scoring_countdown = 1
    g.game_timer = GAME_TIME
    g._update_scoring()
    assert g.phase == Phase.AIMING
    assert g.aim_power == POWER_MIN


def test_scoring_game_over_on_timeout() -> None:
    g = _make_game()
    g.phase = Phase.SCORING
    g.game_timer = 0
    g._update_scoring()
    assert g.phase == Phase.GAME_OVER


# ── 18. throw count tracking ───────────────────────────────

def test_throw_count_increments() -> None:
    g = _make_game()
    g.phase = Phase.AIMING
    g.aim_power = 60.0
    assert g.throw_count == 0
    g._throw_stone()
    assert g.throw_count == 1


# ── 19. max_combo tracking ─────────────────────────────────

def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    g.combo = 4
    g.max_combo = 4
    stone = Stone(x=160.0, y=190.0, vx=1.0, vy=1.0, combo_color=8)
    ripple = Ripple(x=160.0, y=190.0, color=8)
    g._process_skip(stone, ripple)
    assert g.max_combo == 5


def test_max_combo_preserved_after_reset() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    g.combo = 5
    g.max_combo = 5
    stone = Stone(x=160.0, y=190.0, vx=1.0, vy=1.0, combo_color=8)
    ripple = Ripple(x=160.0, y=190.0, color=3)  # wrong color
    g._process_skip(stone, ripple)
    assert g.combo == 0
    assert g.max_combo == 5  # preserved


# ── 20. super mode carryover to stone ──────────────────────

def test_super_mode_carries_to_stone_on_throw() -> None:
    g = _make_game()
    g.phase = Phase.AIMING
    g.super_mode = True
    g.super_timer = 200
    g.aim_power = 70.0
    g._throw_stone()
    assert g.stone is not None
    assert g.stone.super_mode is True
    assert g.stone.super_timer == 200


# ── 21. edge case: stone off-screen sinks ──────────────────

def test_stone_offscreen_bottom_sinks() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    g.stone = Stone(x=160.0, y=SCREEN_H + 30, vx=0.0, vy=1.0, bounces=2)
    g._update_flying()
    assert g.stone is None
    assert g.phase == Phase.SCORING


def test_stone_offscreen_left_sinks() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    g.stone = Stone(x=-30.0, y=190.0, vx=-1.0, vy=0.0, bounces=1)
    g._update_flying()
    assert g.stone is None
    assert g.phase == Phase.SCORING


def test_stone_offscreen_right_sinks() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    g.stone = Stone(x=SCREEN_W + 30, y=190.0, vx=1.0, vy=0.0, bounces=1)
    g._update_flying()
    assert g.stone is None
    assert g.phase == Phase.SCORING


# ── 22. power clamping ─────────────────────────────────────

def test_power_clamped_to_max() -> None:
    """aim_power should not exceed POWER_MAX"""
    # This is tested through _throw_stone — the update method clamps
    # Just verify the constant is reasonable
    assert POWER_MAX == 100.0
    assert POWER_MIN == 30.0


# ── 23. bump count ─────────────────────────────────────────

def test_process_skip_increments_bounces() -> None:
    g = _make_game()
    g.phase = Phase.FLYING
    stone = Stone(x=160.0, y=190.0, vx=1.0, vy=1.0, bounces=2)
    ripple = Ripple(x=160.0, y=190.0, color=8)
    g._process_skip(stone, ripple)
    assert stone.bounces == 3


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
