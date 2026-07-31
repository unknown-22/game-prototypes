"""test_imports.py — Headless logic tests for WAKE CHAIN."""
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/263_wake_chain")
from main import (
    BUOY_COLORS,
    C_LIME,
    C_RED,
    C_WHITE,
    COLLECT_RADIUS,
    GAME_DURATION,
    HEAT_CAP,
    HEAT_DECAY,
    HEAT_MISMATCH,
    HEAT_MISS,
    PLAYER_Y,
    SUPER_DURATION,
    Buoy,
    FloatingText,
    Particle,
    Phase,
    WakePoint,
    _make_game,
)


# ============================================================
# Data Class Tests
# ============================================================


def test_buoy_creation() -> None:
    b = Buoy(x=100.0, y=50.0, color=C_RED)
    assert b.x == 100.0
    assert b.y == 50.0
    assert b.color == C_RED
    assert b.alive is True


def test_particle_creation() -> None:
    p = Particle(x=50.0, y=60.0, vx=1.0, vy=-2.0, life=15, color=C_LIME)
    assert p.x == 50.0
    assert p.y == 60.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == C_LIME


def test_floating_text_creation() -> None:
    ft = FloatingText(x=100.0, y=80.0, text="+100", life=30, color=C_RED)
    assert ft.x == 100.0
    assert ft.y == 80.0
    assert ft.text == "+100"
    assert ft.life == 30
    assert ft.color == C_RED


def test_wake_point_creation() -> None:
    wp = WakePoint(x=160.0, y=120.0, frame=0)
    assert wp.x == 160.0
    assert wp.y == 120.0
    assert wp.frame == 0


# ============================================================
# Phase Enum Tests
# ============================================================


def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase
    assert Phase.TITLE != Phase.PLAYING


# ============================================================
# Factory Tests
# ============================================================


def test_make_game_creates_valid_game() -> None:
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_active is False
    assert g.super_timer == 0
    assert g.super_mult == 1
    assert g.player_x == 160.0
    assert g.player_color in BUOY_COLORS
    assert g._frame_count == 0
    assert g.buoys == []
    assert g.particles == []
    assert g.floating_texts == []
    assert g._headless is True


# ============================================================
# Escalate Tests
# ============================================================


def test_escalate_start() -> None:
    g = _make_game()
    g._frame_count = 0
    result = g._escalate(60, 25)
    assert result == 60.0


def test_escalate_end() -> None:
    g = _make_game()
    g._frame_count = GAME_DURATION
    result = g._escalate(60, 25)
    assert result == 25.0


def test_escalate_mid() -> None:
    g = _make_game()
    g._frame_count = GAME_DURATION // 2
    result = g._escalate(60, 25)
    assert 40 < result < 45


# ============================================================
# Buoy Collection Tests
# ============================================================


def test_collect_buoy_match() -> None:
    g = _make_game()
    g.player_color = C_RED
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.super_active = False
    g.super_timer = 0
    g.super_mult = 1
    buoy = Buoy(x=g.player_x, y=float(PLAYER_Y), color=C_RED)
    g._collect_buoy(buoy)
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score > 0
    assert buoy.alive is False


def test_collect_buoy_match_score_increases_with_combo() -> None:
    g = _make_game()
    g.player_color = C_RED
    g.combo = 2
    g.score = 0
    g.super_mult = 1
    buoy = Buoy(x=g.player_x, y=float(PLAYER_Y), color=C_RED)
    g._collect_buoy(buoy)
    assert g.combo == 3
    assert g.score >= 10 * 3  # 10 * combo * super_mult


def test_collect_buoy_mismatch() -> None:
    g = _make_game()
    g.player_color = C_RED
    g.combo = 3
    g.heat = 0.0
    g.super_active = False
    g.super_mult = 1
    buoy = Buoy(x=g.player_x, y=float(PLAYER_Y), color=C_LIME)
    g._collect_buoy(buoy)
    assert g.combo == 0
    assert g.heat == HEAT_MISMATCH


def test_collect_buoy_super_any_color_match() -> None:
    g = _make_game()
    g.player_color = C_RED
    g.super_active = True
    g.super_timer = 100
    g.super_mult = 3
    g.combo = 0
    g.score = 0
    g.heat = 10.0
    buoy = Buoy(x=g.player_x, y=float(PLAYER_Y), color=C_LIME)
    g._collect_buoy(buoy)
    assert g.combo == 1
    assert g.score >= 10 * 1 * 3  # super_mult = 3
    assert g.heat == 10.0  # heat unchanged (super prevents heat gain)
    assert buoy.alive is False


# ============================================================
# SUPER WAKE Tests
# ============================================================


def test_super_trigger_on_combo_four() -> None:
    g = _make_game()
    g.player_color = C_RED
    g.combo = 3
    g.super_active = False
    g.super_timer = 0
    g.super_mult = 1
    buoy = Buoy(x=g.player_x, y=float(PLAYER_Y), color=C_RED)
    g._collect_buoy(buoy)
    assert g.combo == 4
    assert g.super_active is True
    assert g.super_timer == SUPER_DURATION
    assert g.super_mult == 3


def test_super_timer_decrement() -> None:
    g = _make_game()
    g.super_active = True
    g.super_timer = 100
    g.super_mult = 3
    g._update_super()
    assert g.super_timer == 99
    assert g.super_active is True


def test_super_timer_expiry() -> None:
    g = _make_game()
    g.super_active = True
    g.super_timer = 1
    g.super_mult = 3
    g._update_super()
    assert g.super_timer == 0
    assert g.super_active is False
    assert g.super_mult == 1


def test_super_not_retriggered_when_active() -> None:
    g = _make_game()
    g.player_color = C_RED
    g.super_active = True
    g.super_timer = 100
    g.super_mult = 3
    g.combo = 5
    buoy = Buoy(x=g.player_x, y=float(PLAYER_Y), color=C_RED)
    g._collect_buoy(buoy)
    assert g.super_active is True  # still active
    assert g.super_timer == 100  # timer not reset


# ============================================================
# Heat System Tests
# ============================================================


def test_heat_decay() -> None:
    g = _make_game()
    g.heat = 50.0
    g.phase = Phase.PLAYING
    g._update_heat()
    assert g.heat == 50.0 - HEAT_DECAY


def test_heat_floor_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_heat_game_over() -> None:
    g = _make_game()
    g.heat = HEAT_CAP
    g.phase = Phase.PLAYING
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g._game_over_reason == "OVERHEAT!"


def test_heat_game_over_shake() -> None:
    g = _make_game()
    g.heat = HEAT_CAP
    g.phase = Phase.PLAYING
    g._update_heat()
    assert g._shake_frames == 15


# ============================================================
# Combo Cap Tests
# ============================================================


def test_combo_cap_at_99() -> None:
    g = _make_game()
    g.player_color = C_RED
    g.combo = 99
    g.super_active = False
    g.super_mult = 1
    buoy = Buoy(x=g.player_x, y=float(PLAYER_Y), color=C_RED)
    g._collect_buoy(buoy)
    assert g.combo == 99


# ============================================================
# Max Combo Tracking Tests
# ============================================================


def test_max_combo_tracking() -> None:
    g = _make_game()
    g.player_color = C_RED
    g.combo = 0
    g.max_combo = 0
    g.super_mult = 1
    buoy = Buoy(x=g.player_x, y=float(PLAYER_Y), color=C_RED)
    g._collect_buoy(buoy)
    assert g.max_combo == 1
    g._collect_buoy(Buoy(x=g.player_x, y=float(PLAYER_Y), color=C_LIME))
    assert g.max_combo == 1  # max_combo preserved after mismatch


# ============================================================
# Buoy Exit Screen Tests
# ============================================================


def test_buoy_exit_bottom_adds_heat() -> None:
    g = _make_game()
    g.heat = 0.0
    g.combo = 3
    g.super_active = False
    buoy = Buoy(x=160.0, y=260.0, color=C_RED)
    g.buoys = [buoy]
    g._buoy_speed = 1.0
    g._update_buoys()
    assert buoy.alive is False
    assert g.combo == 0
    assert g.heat == HEAT_MISS


def test_buoy_exit_during_super_no_heat() -> None:
    g = _make_game()
    g.heat = 10.0
    g.combo = 3
    g.super_active = True
    buoy = Buoy(x=160.0, y=260.0, color=C_RED)
    g.buoys = [buoy]
    g._buoy_speed = 1.0
    g._update_buoys()
    assert buoy.alive is False
    assert g.heat == 10.0  # heat unchanged during super


# ============================================================
# Reset Tests
# ============================================================


def test_reset_clears_score() -> None:
    g = _make_game()
    g.score = 500
    g.combo = 5
    g.max_combo = 5
    g.heat = 80.0
    g.super_active = True
    g.super_timer = 100
    g.super_mult = 3
    g.buoys = [Buoy(x=100.0, y=100.0, color=C_RED)]
    g.particles = [Particle(x=0, y=0, vx=0, vy=0, life=10, color=C_RED)]
    g.floating_texts = [FloatingText(x=0, y=0, text="x", life=5, color=C_RED)]
    g.reset()
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_active is False
    assert g.super_timer == 0
    assert g.super_mult == 1
    assert len(g.buoys) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert g._frame_count == 0
    assert g.phase == Phase.PLAYING


def test_reset_player_position() -> None:
    g = _make_game()
    g.player_x = 50.0
    g.reset()
    assert g.player_x == 160.0


# ============================================================
# Particle Lifecycle Tests
# ============================================================


def test_particle_lifecycle() -> None:
    g = _make_game()
    g._add_particles(100.0, 100.0, C_RED, 3, 3)
    assert len(g.particles) == 3
    for _ in range(4):
        g._update_particles()
    assert len(g.particles) == 0


def test_particle_gravity() -> None:
    g = _make_game()
    g._add_particles(100.0, 100.0, C_RED, 1, 10)
    p = g.particles[0]
    orig_vy = p.vy
    g._update_particles()
    assert p.vy == orig_vy + 0.1


# ============================================================
# Floating Text Lifecycle Tests
# ============================================================


def test_floating_text_lifecycle() -> None:
    g = _make_game()
    g._add_floating_text(100.0, 80.0, "test", C_WHITE, 3)
    assert len(g.floating_texts) == 1
    for _ in range(4):
        g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_floating_text_moves_upward() -> None:
    g = _make_game()
    g._add_floating_text(100.0, 80.0, "test", C_WHITE, 10)
    ft = g.floating_texts[0]
    orig_y = ft.y
    g._update_floating_texts()
    assert ft.y < orig_y


# ============================================================
# Color Cycling Tests
# ============================================================


def test_player_color_cycles() -> None:
    g = _make_game()
    for _ in range(20):
        g._update_player_color()
    assert g.player_color in BUOY_COLORS


# ============================================================
# Player Bounds Tests
# ============================================================


def test_player_clamped_left() -> None:
    g = _make_game()
    g.player_x = 10.0
    g.player_x = max(20.0, g.player_x - 3.0)
    assert g.player_x == 20.0


def test_player_clamped_right() -> None:
    g = _make_game()
    g.player_x = 310.0
    g.player_x = min(300.0, g.player_x + 3.0)
    assert g.player_x <= 300.0


# ============================================================
# Spawn Buoy Tests
# ============================================================


def test_spawn_buoy_in_bounds() -> None:
    g = _make_game()
    buoy = g._spawn_buoy()
    assert 30 <= buoy.x <= 290
    assert buoy.y == -10.0
    assert buoy.color in BUOY_COLORS
    assert buoy.alive is True


# ============================================================
# Check Collection Tests
# ============================================================


def test_check_collection_hit() -> None:
    g = _make_game()
    buoy = Buoy(x=160.0, y=160.0, color=C_RED)
    result = g._check_collection(buoy, 160.0, 160.0)
    assert result is True


def test_check_collection_miss() -> None:
    g = _make_game()
    buoy = Buoy(x=100.0, y=100.0, color=C_RED)
    result = g._check_collection(buoy, 160.0, 160.0)
    assert result is False


def test_check_collection_edge() -> None:
    g = _make_game()
    buoy = Buoy(x=160.0 + COLLECT_RADIUS - 1, y=160.0, color=C_RED)
    result = g._check_collection(buoy, 160.0, 160.0)
    assert result is True


# ============================================================
# Difficulty Escalation Tests
# ============================================================


def test_difficulty_spawn_interval_decreases() -> None:
    g = _make_game()
    g._frame_count = GAME_DURATION
    g._update_difficulty()
    assert g._spawn_interval == 25


def test_difficulty_buoy_speed_increases() -> None:
    g = _make_game()
    g._frame_count = GAME_DURATION
    g._update_difficulty()
    assert g._buoy_speed == 3.0


# ============================================================
# Timer Tests
# ============================================================


def test_timer_game_over() -> None:
    g = _make_game()
    g._frame_count = GAME_DURATION
    g.phase = Phase.PLAYING
    g._update_timer()
    assert g.phase == Phase.GAME_OVER
    assert g._game_over_reason == "Time Up!"


# ============================================================
# Super Mult Tests
# ============================================================


def test_super_mult_normal() -> None:
    g = _make_game()
    assert g.super_mult == 1


def test_super_mult_during_super() -> None:
    g = _make_game()
    g.super_active = True
    g.super_timer = 100
    g.super_mult = 3
    assert g.super_mult == 3
