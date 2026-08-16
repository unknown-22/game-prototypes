"""Headless logic tests for SWISH CHAIN (314_swish_chain).

Imports the game module directly (no Pyxel window). Uses Game.__new__ to bypass
pyxel.init/pyxel.run, then reset() to build a deterministic state. Never calls
methods that touch pyxel input (update/_update_aim).
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import BALL_COLORS, Game, Particle, Phase  # noqa: E402


def make_game() -> Game:
    g = Game.__new__(Game)
    g.best_score = 0
    g.reset()
    g.rng = random.Random(42)
    return g


# ---------------------------------------------------------------------------
# Reset / initialization
# ---------------------------------------------------------------------------

def test_reset_initializes_state():
    g = make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.game_timer == Game.GAME_TIME
    assert g.player_color == BALL_COLORS[0]
    assert len(g.hoops) == 3
    assert g.ball.active is False
    assert g.super_active is False
    assert g.super_timer == 0


def test_reset_clears_transient_state():
    g = make_game()
    g.score = 999
    g.combo = 5
    g.heat = 80.0
    g.super_active = True
    g.super_timer = 120
    g.particles.append(Particle(0.0, 0.0, 0.0, 0.0, 10, 8))  # non-empty transient container
    g.floating_texts = []  # ensure list exists
    g.hoops = []
    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.super_active is False
    assert g.super_timer == 0
    assert len(g.hoops) == 3
    assert g.game_timer == Game.GAME_TIME


def test_hoop_layout_multipliers():
    g = make_game()
    assert g.hoops[0].multiplier == 1
    assert g.hoops[1].multiplier == 2
    assert g.hoops[2].multiplier == 3
    assert g.hoops[0].y == g.hoops[1].y == g.hoops[2].y == Game.HOOP_Y
    assert g.hoops[0].x < g.hoops[1].x < g.hoops[2].x


# ---------------------------------------------------------------------------
# Launch / physics
# ---------------------------------------------------------------------------

def test_launch_sets_ball_state():
    g = make_game()
    g._launch(3.0, -8.0)
    assert g.ball.active is True
    assert g.ball.x == Game.LAUNCH_X
    assert g.ball.y == Game.LAUNCH_Y
    assert g.ball.vx == 3.0
    assert g.ball.vy == -8.0
    assert g.ball.color == g.player_color


def test_physics_applies_gravity():
    g = make_game()
    g.ball.vy = 0.0
    g._update_physics()
    assert g.ball.vy == Game.GRAVITY


def test_physics_integrates_position():
    g = make_game()
    g.ball.x = 100.0
    g.ball.y = 100.0
    g.ball.vx = 2.0
    g.ball.vy = -3.0
    g._update_physics()
    assert g.ball.x == 102.0
    assert g.ball.y == 100.0 - 3.0 + Game.GRAVITY


# ---------------------------------------------------------------------------
# Shot resolution: swish / clank / rim_out
# ---------------------------------------------------------------------------

def test_swish_matching_color():
    g = make_game()
    hoop = g.hoops[0]
    g.ball.color = hoop.color
    g.ball.x = hoop.x
    result = g._resolve_shot(hoop, hoop.x)
    assert result == "swish"
    assert g.combo == 1
    assert g.score == 10 * 1 * 1
    assert g.max_combo == 1
    assert g.ball.active is False


def test_swish_combo_increments_before_scoring():
    g = make_game()
    hoop = g.hoops[0]
    g.ball.color = hoop.color
    g.combo = 3
    g._swish(hoop, hoop.x)
    assert g.combo == 4
    # 10 * 4 * 1 (near mult) — combo incremented first, so it uses 4 not 3
    assert g.score == 10 * 4 * 1


def test_risk_reward_far_hoop_scores_more():
    g_near = make_game()
    g_near.ball.color = g_near.hoops[0].color
    g_near._swish(g_near.hoops[0], g_near.hoops[0].x)

    g_far = make_game()
    g_far.ball.color = g_far.hoops[2].color
    g_far._swish(g_far.hoops[2], g_far.hoops[2].x)

    assert g_far.score > g_near.score
    assert g_near.score == 10  # 10 * 1 * 1
    assert g_far.score == 30  # 10 * 1 * 3


def test_clank_wrong_color():
    g = make_game()
    hoop = g.hoops[0]
    other = next(c for c in BALL_COLORS if c != hoop.color)
    g.ball.color = other
    g.ball.x = hoop.x
    g.ball.active = True
    g.combo = 3
    result = g._resolve_shot(hoop, hoop.x)
    assert result == "clank"
    assert g.heat == 8.0
    assert g.combo == 0
    assert g.ball.active is True  # clank does not end the shot


def test_rim_out():
    g = make_game()
    hoop = g.hoops[0]
    g.ball.x = hoop.x + hoop.radius  # dx == radius (between radius-2 and radius+4)
    g.combo = 2
    result = g._resolve_shot(hoop, hoop.x)
    assert result == "rim_out"
    assert g.heat == 5.0
    assert g.combo == 2  # rim_out does not reset combo


def test_shot_misses_far_outside():
    g = make_game()
    hoop = g.hoops[0]
    g.ball.x = hoop.x + 100.0
    result = g._resolve_shot(hoop, hoop.x)
    assert result is None
    assert g.heat == 0.0
    assert g.combo == 0


# ---------------------------------------------------------------------------
# Integration: _update_ball crossing detection
# ---------------------------------------------------------------------------

def test_update_ball_crossing_triggers_swish():
    g = make_game()
    hoop = g.hoops[1]  # mid, mult 2
    g.ball.active = True
    g.ball.color = hoop.color
    g.ball.x = hoop.x
    g.ball.y = hoop.y - 1.0
    g.ball.vy = 1.0
    g.ball.vx = 0.0
    g._update_ball()
    assert g.ball.active is False
    assert g.combo == 1
    assert g.score == 20  # 10 * 1 * 2


def test_update_ball_airball_offscreen():
    g = make_game()
    g.ball.active = True
    g.ball.color = BALL_COLORS[0]
    g.ball.x = 160.0
    g.ball.y = Game.SCREEN_H + 7.0
    g.ball.vy = 2.0
    g.combo = 3
    g._update_ball()
    assert g.ball.active is False
    assert g.heat == 15.0
    assert g.combo == 0
    assert g.respawn_timer == g.respawn_delay


def test_update_ball_inactive_respawn_timer():
    g = make_game()
    g.ball.active = False
    g.ball.x = 0.0
    g.ball.y = 0.0
    g.respawn_timer = 1
    g._update_ball()
    assert g.respawn_timer == 0
    assert g.ball.x == Game.LAUNCH_X
    assert g.ball.y == Game.LAUNCH_Y


# ---------------------------------------------------------------------------
# SUPER SHOT
# ---------------------------------------------------------------------------

def test_super_shot_activates_at_combo_4():
    g = make_game()
    hoop = g.hoops[0]
    g.ball.color = hoop.color
    g.combo = 3
    g._swish(hoop, hoop.x)
    assert g.combo == 4
    assert g.super_active is True
    assert g.super_timer == Game.SUPER_DURATION


def test_super_shot_scores_3x():
    g = make_game()
    hoop = g.hoops[0]
    g.super_active = True
    g.super_timer = 10
    g.ball.color = hoop.color
    g._swish(hoop, hoop.x)
    assert g.combo == 1
    assert g.score == 10 * 1 * 1 * 3  # 30


def test_super_allows_any_color_swish():
    g = make_game()
    hoop = g.hoops[0]
    g.super_active = True
    other = next(c for c in BALL_COLORS if c != hoop.color)
    g.ball.color = other
    g.ball.x = hoop.x
    result = g._resolve_shot(hoop, hoop.x)
    assert result == "swish"


def test_super_expiry_resets_combo():
    g = make_game()
    g.super_timer = 1
    g.super_active = True
    g.combo = 5
    g._update_super()
    assert g.super_timer == 0
    assert g.super_active is False
    assert g.combo == 0


# ---------------------------------------------------------------------------
# HEAT risk
# ---------------------------------------------------------------------------

def test_heat_threshold_triggers_game_over():
    g = make_game()
    g.heat = 100.0
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g.game_over_reason == "BENCHED"


def test_heat_decay_applied_when_below_threshold():
    g = make_game()
    g.heat = 50.0
    g._update_heat()
    assert abs(g.heat - (50.0 - Game.HEAT_DECAY)) < 1e-6


def test_heat_frozen_during_super():
    g = make_game()
    g.heat = 50.0
    g.super_active = True
    g._update_heat()
    assert g.heat == 50.0


def test_heat_never_negative():
    g = make_game()
    g.heat = 0.01
    g._update_heat()
    assert g.heat == 0.0


# ---------------------------------------------------------------------------
# Timer / game over
# ---------------------------------------------------------------------------

def test_game_over_records_best_score():
    g = make_game()
    g.score = 1234
    g._game_over("TIME UP")
    assert g.phase == Phase.GAME_OVER
    assert g.game_over_reason == "TIME UP"
    assert g.best_score == 1234


def test_game_over_keeps_higher_best():
    g = make_game()
    g.best_score = 5000
    g.score = 1234
    g._game_over("TIME UP")
    assert g.best_score == 5000


# ---------------------------------------------------------------------------
# Color cycle & difficulty escalation
# ---------------------------------------------------------------------------

def test_color_cycle_advances_after_interval():
    g = make_game()
    start = g.player_color
    start_index = g.player_color_index
    for _ in range(g.cycle_interval):
        g._cycle_player_color()
    assert g.player_color_index == (start_index + 1) % len(BALL_COLORS)
    assert g.player_color == BALL_COLORS[(start_index + 1) % len(BALL_COLORS)]
    assert g.player_color != start


def test_difficulty_escalation_end_vs_start():
    g = make_game()
    g.game_timer = Game.GAME_TIME  # elapsed 0
    g._update_difficulty()
    assert g.cycle_interval == 20
    assert g.respawn_delay == 30
    assert g.drift_amp == 0

    g.game_timer = 0  # elapsed 3600
    g._update_difficulty()
    assert g.cycle_interval == 12
    assert g.respawn_delay == 15
    assert g.drift_amp == 8


def test_cycle_interval_clamped_at_minimum():
    g = make_game()
    g.game_timer = 0
    g._update_difficulty()
    assert g.cycle_interval >= 12
    assert g.respawn_delay >= 15


# ---------------------------------------------------------------------------
# Geometry sanity
# ---------------------------------------------------------------------------

def test_hoops_within_screen_bounds():
    g = make_game()
    for hoop in g.hoops:
        assert hoop.x - hoop.radius > 0
        assert hoop.x + hoop.radius < Game.SCREEN_W


def test_hoop_effective_x_no_drift_at_start():
    g = make_game()
    g.drift_amp = 0
    for hoop in g.hoops:
        assert g._hoop_eff_x(hoop) == hoop.x


def test_hoop_effective_x_drift_bounded():
    g = make_game()
    g.game_timer = 0
    g._update_difficulty()
    amp = g.drift_amp
    for hoop in g.hoops:
        eff = g._hoop_eff_x(hoop)
        assert abs(eff - hoop.x) <= amp + 1e-6


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
