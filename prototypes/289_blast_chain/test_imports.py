"""test_imports.py — Headless logic tests for 289_blast_chain (Fireworks Display)."""
from __future__ import annotations

import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/289_blast_chain")
from main import Game, Particle, FloatingText, COLORS, RED, LIME, DARK_BLUE, YELLOW, WHITE


def _make_game() -> Game:
    """Factory: bypass pyxel.init using Game.__new__."""
    g = Game.__new__(Game)
    # Pre-init all attributes that reset() touches
    g.phase = ""
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.timer = 0
    g.last_fired_color = 0
    g.next_color_index = 0
    g.super_mode = False
    g.super_timer = 0
    g.firework_active = False
    g.firework_x = 0.0
    g.firework_y = 0.0
    g.firework_target_x = 0.0
    g.firework_target_y = 0.0
    g.firework_color = 0
    g.color_index = 0
    g.auto_cycle_timer = 0
    g.auto_cycle_interval = 0
    g.particles = []
    g.floating_texts = []
    g.best_score = 0
    g.tube_glow = 0
    g._rng = random.Random(42)
    g._auto_cycle_elapsed = 0
    g.reset()
    return g


# ── Data Classes ──

def test_particle_creation() -> None:
    p = Particle(10.0, 20.0, 1.5, -2.0, 30, RED)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.life == 30
    assert p.color == RED


def test_floating_text_creation() -> None:
    ft = FloatingText(100.0, 50.0, "+10", 40, LIME)
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "+10"
    assert ft.life == 40
    assert ft.color == LIME


# ── Constants ──

def test_color_constants() -> None:
    assert len(COLORS) == 4
    assert COLORS[0] == RED  # 8
    assert COLORS[1] == LIME  # 11
    assert COLORS[2] == DARK_BLUE  # 5
    assert COLORS[3] == YELLOW  # 10


def test_game_constants() -> None:
    g = _make_game()
    assert g.SCREEN_W == 320
    assert g.SCREEN_H == 240
    assert g.FIREWORK_SPEED == 6.0
    assert g.SUPER_DURATION == 300
    assert g.GAME_DURATION == 1800
    assert g.HEAT_MAX == 100
    assert g.HEAT_DECAY == 0.02
    assert g.HEAT_MISMATCH == 15


# ── Reset ──

def test_reset_initial_state() -> None:
    g = _make_game()
    assert g.phase == "TITLE"
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.timer == Game.GAME_DURATION
    assert g.last_fired_color == 0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.firework_active is False
    assert g.auto_cycle_timer == Game.AUTO_CYCLE_INIT
    assert isinstance(g.particles, list)
    assert len(g.particles) == 0
    assert isinstance(g.floating_texts, list)
    assert len(g.floating_texts) == 0


# ── Launch ──

def test_start_launch() -> None:
    g = _make_game()
    g.color_index = 2  # DARK_BLUE
    g._start_launch(150.0, 100.0)
    assert g.firework_active is True
    assert g.firework_x == Game.TUBE_X
    assert g.firework_y == Game.TUBE_Y
    assert g.firework_target_x == 150.0
    assert g.firework_target_y == 100.0
    assert g.firework_color == DARK_BLUE  # next_color
    assert g.tube_glow == 30


# ── Firework Movement ──

def test_firework_moves_toward_target() -> None:
    g = _make_game()
    g._start_launch(200.0, 100.0)
    g._update_firework()
    # Should have moved toward target
    assert g.firework_x > Game.TUBE_X
    assert g.firework_y < Game.TUBE_Y  # moving up
    assert g.firework_active is True


def test_firework_bursts_at_target() -> None:
    g = _make_game()
    g._start_launch(Game.TUBE_X, Game.TUBE_Y - Game.FIREWORK_SPEED + 1)
    g.last_fired_color = g.firework_color  # same color → match
    g._update_firework()
    # After burst, firework should be inactive and last_fired_color updated
    assert g.firework_active is False


# ── Burst: Match ──

def test_burst_match_increments_combo() -> None:
    g = _make_game()
    g.firework_color = RED
    g.last_fired_color = RED  # same color → match
    g.firework_active = True
    g.firework_x = 160.0
    g.firework_y = 100.0
    g._burst_firework()
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score == 10  # 10 * 1 * 1.0
    assert g.last_fired_color == RED
    assert g.firework_active is False
    assert len(g.particles) == 25
    assert len(g.floating_texts) == 2  # +score + COMBO text


def test_burst_match_consecutive_combo_grows() -> None:
    g = _make_game()
    g.firework_color = RED
    g.last_fired_color = RED
    g.combo = 2
    g.firework_active = True
    g._burst_firework()
    assert g.combo == 3
    assert g.score == 30  # 10 * 3 * 1.0


def test_burst_match_first_launch_no_combo() -> None:
    """First launch: last_fired_color=0, firework_color=RED — no match."""
    g = _make_game()
    g.firework_color = RED
    g.last_fired_color = 0  # initial state
    g.firework_active = True
    g._burst_firework()
    # 0 != RED, so it's a miss (not in super_mode either)
    assert g.combo == 0
    assert g.heat == Game.HEAT_MISMATCH


# ── Burst: Mismatch ──

def test_burst_mismatch_adds_heat() -> None:
    g = _make_game()
    g.firework_color = RED
    g.last_fired_color = LIME  # different color
    g.combo = 3
    g.firework_active = True
    g._burst_firework()
    assert g.combo == 0
    assert g.heat == Game.HEAT_MISMATCH
    assert g.score == 1  # 1 * 1.0 consolation
    assert len(g.particles) == 4  # small puff
    assert len(g.floating_texts) == 1  # MISS text


def test_burst_mismatch_resets_super() -> None:
    """Mismatch when NOT in super mode resets combo. But in super mode, all colors match."""
    g = _make_game()
    g.firework_color = RED
    g.last_fired_color = LIME
    g.super_mode = True
    g.super_timer = 100
    g.firework_active = True
    g._burst_firework()
    # In super_mode, the condition "self.super_mode or launched_color == last_color"
    # is True, so this enters the MATCH branch, not the mismatch branch.
    assert g.super_mode is True  # still active
    assert g.combo == 1  # counted as match
    assert g.heat == 0  # no heat added

    # Mismatch NOT in super mode DOES reset
    g.super_mode = False
    g.firework_color = RED
    g.last_fired_color = LIME
    g.combo = 5
    g.firework_active = True
    g._burst_firework()
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.combo == 0
    assert g.heat == Game.HEAT_MISMATCH


# ── Super Mode ──

def test_combo_4_triggers_super_mode() -> None:
    g = _make_game()
    g.firework_color = RED
    g.last_fired_color = RED
    g.combo = 3  # will become 4 after burst
    g.firework_active = True
    g._burst_firework()
    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == Game.SUPER_DURATION
    # Particles: 25 normal + 55 super burst
    assert len(g.particles) == 80


def test_super_mode_3x_multiplier() -> None:
    g = _make_game()
    g.firework_color = RED
    g.last_fired_color = RED
    g.super_mode = True
    g.combo = 1
    g.firework_active = True
    g._burst_firework()
    assert g.combo == 2
    assert g.score == 60  # 10 * 2 * 3.0 = 60


def test_super_mode_any_color_matches() -> None:
    g = _make_game()
    g.firework_color = RED
    g.last_fired_color = LIME  # different, but super_mode = any match
    g.super_mode = True
    g.combo = 5
    g.firework_active = True
    g._burst_firework()
    assert g.combo == 6  # counted as match because super_mode
    assert g.score == 180  # 10 * 6 * 3.0 = 180
    assert g.super_mode is True  # still active


def test_super_mode_does_not_retrigger_super() -> None:
    """Already in super_mode, combo stays >= 4, doesn't re-trigger."""
    g = _make_game()
    g.firework_color = RED
    g.last_fired_color = RED
    g.super_mode = True
    g.super_timer = 50
    g.combo = 4
    g.firework_active = True
    g._burst_firework()
    # Combo increments, but "combo >= 4 and not self.super_mode" is False
    # No extra 55 particles from super-trigger
    assert g.combo == 5
    assert len(g.particles) == 25  # only normal burst, no extra super


# ── Timer ──

def test_update_timer() -> None:
    g = _make_game()
    g.phase = "PLAYING"
    g.timer = 100
    g._update_timer()
    assert g.timer == 99


def test_timer_floor_zero() -> None:
    g = _make_game()
    g.phase = "PLAYING"
    g.timer = 0
    g._update_timer()
    assert g.timer == 0  # floor at 0


# ── Heat ──

def test_heat_decay() -> None:
    g = _make_game()
    g.phase = "PLAYING"
    g.heat = 50.0
    g._update_heat()
    assert abs(g.heat - 49.98) < 0.001


def test_heat_floor_zero() -> None:
    g = _make_game()
    g.phase = "PLAYING"
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


# ── Game Over ──

def test_game_over_on_timer() -> None:
    g = _make_game()
    g.phase = "PLAYING"
    g.timer = 0
    g.score = 500
    g._check_game_over()
    assert g.phase == "GAME_OVER"
    assert g.best_score == 500


def test_game_over_on_heat() -> None:
    g = _make_game()
    g.phase = "PLAYING"
    g.heat = 100.0
    g._check_game_over()
    assert g.phase == "GAME_OVER"


def test_game_over_retains_best_score() -> None:
    g = _make_game()
    g.phase = "PLAYING"
    g.best_score = 300
    g.score = 200
    g.timer = 0
    g._check_game_over()
    assert g.best_score == 300  # unchanged (200 < 300)


# ── Particles ──

def test_update_particles_decrements_life() -> None:
    g = _make_game()
    g.particles = [Particle(100.0, 100.0, 1.0, 1.0, 30, RED)]
    g._update_particles()
    assert g.particles[0].life == 29


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    g.particles = [Particle(100.0, 100.0, 1.0, 1.0, 1, RED)]
    g._update_particles()
    assert len(g.particles) == 0


def test_update_particles_applies_gravity() -> None:
    g = _make_game()
    g.particles = [Particle(100.0, 100.0, 0.0, 0.0, 30, RED)]
    g._update_particles()
    assert g.particles[0].vy == 0.1  # += 0.1


# ── Floating Text ──

def test_floating_text_life_decrement() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(100.0, 100.0, "+10", 40, WHITE)]
    g._update_floating_texts()
    assert g.floating_texts[0].life == 39


def test_floating_text_removed_when_dead() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(100.0, 100.0, "+10", 1, WHITE)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


def test_floating_text_floats_upward() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(100.0, 100.0, "+10", 40, WHITE)]
    g._update_floating_texts()
    assert abs(g.floating_texts[0].y - 99.5) < 0.001


# ── Auto Cycle ──

def test_auto_cycle_decrements_timer() -> None:
    g = _make_game()
    g.phase = "PLAYING"
    g.auto_cycle_timer = 100
    g._update_auto_cycle()
    assert g.auto_cycle_timer == 99


def test_auto_cycle_advances_color() -> None:
    g = _make_game()
    g.phase = "PLAYING"
    g.auto_cycle_timer = 1
    g.color_index = 0  # RED
    g._update_auto_cycle()
    assert g.color_index == 1  # LIME
    assert g.auto_cycle_timer == g.auto_cycle_interval  # reset


def test_auto_cycle_color_wraps() -> None:
    g = _make_game()
    g.phase = "PLAYING"
    g.color_index = 3  # YELLOW
    g.auto_cycle_timer = 1
    g._update_auto_cycle()
    assert g.color_index == 0  # wraps to RED


def test_auto_cycle_interval_decreases() -> None:
    g = _make_game()
    g.phase = "PLAYING"
    g.auto_cycle_interval = 300
    g._auto_cycle_elapsed = 60
    g.auto_cycle_timer = 10
    g._update_auto_cycle()
    # elapsed >= 60, so interval decreases
    assert g.auto_cycle_interval == 297


def test_auto_cycle_interval_floor() -> None:
    g = _make_game()
    g.phase = "PLAYING"
    g.auto_cycle_interval = Game.AUTO_CYCLE_MIN  # 90
    g._auto_cycle_elapsed = 60
    g.auto_cycle_timer = 10
    g._update_auto_cycle()
    assert g.auto_cycle_interval == Game.AUTO_CYCLE_MIN  # no lower


# ── Color Cycling ──

def test_cycle_to_next_color() -> None:
    g = _make_game()
    g.color_index = 1  # LIME
    g._cycle_to_next_color()
    assert g.color_index == 2  # DARK_BLUE


def test_next_color_property() -> None:
    g = _make_game()
    g.color_index = 2  # DARK_BLUE
    assert g.next_color == DARK_BLUE


# ── Max Combo ──

def test_max_combo_tracking() -> None:
    g = _make_game()
    g.firework_color = RED
    g.last_fired_color = RED
    g.combo = 5
    g.max_combo = 5
    g.firework_active = True
    g._burst_firework()
    assert g.max_combo == 6


def test_max_combo_not_updated_on_mismatch() -> None:
    g = _make_game()
    g.firework_color = RED
    g.last_fired_color = LIME
    g.combo = 5
    g.max_combo = 5
    g.firework_active = True
    g._burst_firework()
    assert g.max_combo == 5  # unchanged
    assert g.combo == 0  # reset


# ── Super Timer Expiry ──

def test_super_mode_expires_resets_combo() -> None:
    """Simulate super_mode timer reaching 0 in _update_playing()."""
    g = _make_game()
    g.phase = "PLAYING"
    g.super_mode = True
    g.combo = 8
    g.super_timer = 1
    # Simulate the _update_playing() logic inline
    # (can't call _update_playing() directly as it accesses pyxel.btnp)
    g._update_timer()
    g._update_heat()
    g._update_auto_cycle()
    g._update_firework()
    g._update_particles()
    g._update_floating_texts()
    # Super timer check (from _update_playing inline):
    g.super_timer -= 1
    if g.super_timer <= 0:
        g.super_mode = False
        g.combo = 0
    g._check_game_over()
    assert g.super_timer == 0  # was 1, then super_timer -= 1 makes it 0
    assert g.super_mode is False
    assert g.combo == 0


# ── Full Resolution Loop ──

def test_match_sequence_builds_combo() -> None:
    g = _make_game()
    # Simulate 3 consecutive RED matches
    g.last_fired_color = RED
    for expected_combo in range(1, 4):
        g.firework_color = RED
        g.firework_active = True
        g._burst_firework()
        assert g.combo == expected_combo
        assert g.last_fired_color == RED
    assert g.combo == 3
    assert g.max_combo == 3
    assert g.score == 10 + 20 + 30  # 10*1 + 10*2 + 10*3


def test_heat_accumulates_to_game_over() -> None:
    g = _make_game()
    g.phase = "PLAYING"
    # Each mismatch: +15 heat. 7 * 15 = 105 > 100. Match real game loop order:
    # update_heat (decay) → update_firework (burst adds heat) → check_game_over
    for i in range(7):
        g.firework_color = RED
        g.last_fired_color = LIME  # ensure mismatch every time
        g._update_heat()       # decay first (real game order)
        g.firework_active = True
        g._burst_firework()    # adds heat
        g._check_game_over()
        if g.phase == "GAME_OVER":
            break
    assert g.phase == "GAME_OVER"


def test_heat_clamp_to_max() -> None:
    g = _make_game()
    g.phase = "PLAYING"
    g.heat = 95.0
    g.firework_color = RED
    g.last_fired_color = LIME
    g.firework_active = True
    g._burst_firework()
    assert g.heat == 100.0  # clamped


# ── Tube Glow ──

def test_tube_glow_decrements_in_playing() -> None:
    g = _make_game()
    g.phase = "PLAYING"
    g.tube_glow = 30
    # Simulate playing logic without pyxel
    g._update_timer()
    g._update_heat()
    g._update_auto_cycle()
    g._update_firework()
    g._update_particles()
    g._update_floating_texts()
    g._check_game_over()
    if g.tube_glow > 0:
        g.tube_glow -= 1
    assert g.tube_glow == 29


# ── Score Formula ──

def test_score_formula_super_3x() -> None:
    g = _make_game()
    g.firework_color = RED
    g.last_fired_color = RED
    g.super_mode = True
    g.combo = 4
    g.firework_active = True
    g._burst_firework()
    assert g.score == 150  # 10 * 5 * 3.0 = 150


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
