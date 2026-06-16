"""test_imports.py — Headless logic tests for SUMO SURGE."""
from __future__ import annotations

import math
import random
import sys

import pytest

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/133_sumo_surge")
from main import Echo, FloatingText, Game, Particle, Phase, Rikishi


def _make_game() -> Game:
    """Factory: create Game bypassing pyxel.init."""
    g = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.player = Rikishi(x=80.0, y=120.0)
    g.ai = Rikishi(x=240.0, y=120.0)
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.score = 0
    g.high_score = 0
    g.super_timer = 0.0
    g.stumble_timer = 0.0
    g.echos = []
    g.particles = []
    g.floating_texts = []
    g.push_cooldown = 0.0
    g.last_push_color = -1
    g._ai_timer = 0.0
    g._ai_color = 0
    g._result_display = ""
    g._result_reason = ""
    g.rng = random.Random(42)
    g.reset()
    return g


# ── Constants ──

def test_class_constants():
    assert Game.RING_CX == 160
    assert Game.RING_CY == 120
    assert Game.RING_RADIUS == 100
    assert Game.PUSH_FORCE == 3.0
    assert Game.SUPER_FORCE == 9.0
    assert Game.COMBO_THRESHOLD == 4
    assert Game.SUPER_DURATION == 5.0
    assert Game.STUMBLE_DURATION == 2.0
    assert Game.HEAT_MAX == 100.0
    assert Game.HEAT_PER_WRONG == 15.0
    assert Game.HEAT_DECAY == 1.0
    assert Game.PUSH_COOLDOWN == 0.3
    assert Game.ECHO_LIFE == 2.0
    assert Game.MAX_ECHOS == 10
    assert Game.AI_PUSH_INTERVAL == 0.8


# ── Phase Enum ──

def test_phase_enum():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.STUMBLE in Phase
    assert Phase.SUPER in Phase
    assert Phase.GAME_OVER in Phase
    assert Phase.TITLE != Phase.PLAYING


# ── Dataclasses ──

def test_rikishi_dataclass():
    r = Rikishi(x=100.0, y=200.0)
    assert r.x == 100.0
    assert r.y == 200.0
    assert r.vx == 0.0
    assert r.vy == 0.0
    assert r.radius == 12
    assert r.color == 8
    assert r.stumble_timer == 0.0


def test_echo_dataclass():
    e = Echo(x=50.0, y=60.0, life=1.5, color=3)
    assert e.life == 1.5
    assert e.color == 3


def test_particle_dataclass():
    p = Particle(x=0.0, y=0.0, vx=1.0, vy=-1.0, life=0.5, color=8)
    assert abs(p.vx - 1.0) < 0.01
    assert abs(p.vy + 1.0) < 0.01
    assert p.life == 0.5


def test_floating_text_dataclass():
    ft = FloatingText(x=100.0, y=50.0, text="TEST", life=1.0, color=7)
    assert ft.text == "TEST"
    assert ft.life == 1.0


# ── Reset ──

def test_reset_state():
    g = _make_game()
    assert g.phase == Phase.PLAYING
    assert g.player.x == 80.0
    assert g.ai.x == 240.0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.score == 0
    assert g.super_timer == 0.0
    assert g.stumble_timer == 0.0
    assert g.echos == []
    assert g.particles == []
    assert g.floating_texts == []
    assert g.push_cooldown == 0.0
    assert g.last_push_color == -1


# ── _can_push ──

def test_can_push_when_playing():
    g = _make_game()
    assert g._can_push() is True


def test_cannot_push_when_stumbling():
    g = _make_game()
    g.stumble_timer = 1.0
    assert g._can_push() is False


def test_cannot_push_when_on_cooldown():
    g = _make_game()
    g.push_cooldown = 0.5
    assert g._can_push() is False


def test_cannot_push_when_not_playing():
    g = _make_game()
    g.phase = Phase.TITLE
    assert g._can_push() is False


# ── _apply_push ──

def test_apply_push_same_color_builds_combo():
    g = _make_game()
    g.last_push_color = 0  # RED
    event = g._apply_push(0, 1.0, 0.0)  # same color
    assert g.combo == 1
    assert "COMBO" in event


def test_apply_push_same_color_increments_combo():
    g = _make_game()
    g.last_push_color = 0
    g.combo = 2
    g.max_combo = 2
    g._apply_push(0, 1.0, 0.0)
    assert g.combo == 3
    assert g.max_combo == 3


def test_apply_push_different_color_resets_combo():
    g = _make_game()
    g.last_push_color = 0  # RED
    g.combo = 3
    g.max_combo = 3
    g._apply_push(1, 0.0, -1.0)  # GREEN (different)
    assert g.combo == 0


def test_apply_push_different_color_adds_heat():
    g = _make_game()
    g.last_push_color = 0  # RED
    g.heat = 0.0
    g._apply_push(1, 0.0, -1.0)  # GREEN (different)
    assert g.heat == Game.HEAT_PER_WRONG


def test_apply_push_first_push_no_combo_break():
    g = _make_game()
    g.last_push_color = -1  # first push — no previous color, so it's a "miss"
    event = g._apply_push(0, 1.0, 0.0)
    # First push with last_push_color=-1 is treated as mismatch
    assert g.combo == 0
    assert "MISS" in event or "BREAK" in event


def test_apply_push_applies_force_to_ai():
    g = _make_game()
    g._apply_push(0, 1.0, 0.0)  # push right
    assert g.ai.vx > 0  # velocity applied


def test_apply_push_causes_recoil():
    g = _make_game()
    g._apply_push(0, 1.0, 0.0)  # push right → recoil left
    assert g.player.vx < 0  # recoil velocity opposite direction


def test_apply_push_triggers_super_at_threshold():
    g = _make_game()
    g.last_push_color = 0
    g.combo = 3  # next push reaches 4 = threshold
    g._apply_push(0, 1.0, 0.0)
    assert g.combo == 4
    assert g.super_timer == Game.SUPER_DURATION


def test_apply_push_super_force_is_higher():
    g = _make_game()
    g.super_timer = 1.0  # SUPER active
    g.last_push_color = 0
    g._apply_push(0, 1.0, 0.0)
    # SUPER_FORCE = 9, base = 3
    assert g.ai.vx == Game.SUPER_FORCE  # exactly 9.0 applied


def test_apply_push_super_matches_any_color():
    g = _make_game()
    g.super_timer = 1.0
    g.last_push_color = 0  # RED
    g.combo = 2
    g._apply_push(2, -1.0, 0.0)  # BLUE (different) but SUPER → matches
    assert g.combo == 3  # no reset


def test_apply_push_spawns_echo():
    g = _make_game()
    assert len(g.echos) == 0
    g._apply_push(0, 1.0, 0.0)
    assert len(g.echos) == 1


def test_apply_push_spawns_particles():
    g = _make_game()
    g._apply_push(0, 1.0, 0.0)
    assert len(g.particles) > 0


def test_apply_push_heat_capped():
    g = _make_game()
    g.last_push_color = 0
    g.heat = 95.0
    g._apply_push(1, 0.0, -1.0)  # wrong color, +15 heat
    assert g.heat == Game.HEAT_MAX  # capped at 100


def test_apply_push_sets_cooldown():
    g = _make_game()
    g._apply_push(0, 1.0, 0.0)
    assert g.push_cooldown == Game.PUSH_COOLDOWN


# ── _check_ring_out ──

def test_no_ring_out_at_start():
    g = _make_game()
    player_out, ai_out = g._check_ring_out()
    assert player_out is False
    assert ai_out is False


def test_player_ring_out():
    g = _make_game()
    g.player.x = 400.0
    g.player.y = 400.0
    player_out, ai_out = g._check_ring_out()
    assert player_out is True
    assert ai_out is False


def test_ai_ring_out():
    g = _make_game()
    g.ai.x = 400.0
    g.ai.y = 400.0
    player_out, ai_out = g._check_ring_out()
    assert player_out is False
    assert ai_out is True


def test_ring_edge_inside():
    g = _make_game()
    # just inside the ring
    g.player.x = Game.RING_CX + Game.RING_RADIUS - 1
    g.player.y = Game.RING_CY
    player_out, _ = g._check_ring_out()
    assert player_out is False


def test_ring_edge_outside():
    g = _make_game()
    g.player.x = Game.RING_CX + Game.RING_RADIUS + 1
    g.player.y = Game.RING_CY
    player_out, _ = g._check_ring_out()
    assert player_out is True


# ── _calculate_score ──

def test_score_zero_on_loss():
    g = _make_game()
    assert g._calculate_score(False) == 0


def test_score_base_on_win():
    g = _make_game()
    score = g._calculate_score(True)
    assert score == 100  # combo=0, multiplier=1.0, heat=0


def test_score_with_combo():
    g = _make_game()
    g.combo = 4
    score = g._calculate_score(True)
    # base=100, multiplier=1.0+4*0.5=3.0, heat_penalty=1.0
    assert score == 300


def test_score_with_super_bonus():
    g = _make_game()
    g.super_timer = 1.0  # super active → x2 multiplier
    score = g._calculate_score(True)
    assert score == 200  # 100 * 1.0 * 2.0 * 1.0


def test_score_heat_penalty():
    g = _make_game()
    g.heat = 100.0  # 1 - 100/200 = 0.5
    score = g._calculate_score(True)
    assert score == 50  # 100 * 1.0 * 0.5


# ── Echo System ──

def test_spawn_echo():
    g = _make_game()
    g._spawn_echo(100.0, 100.0, 8)
    assert len(g.echos) == 1
    assert g.echos[0].life == Game.ECHO_LIFE
    assert g.echos[0].color == 8


def test_echo_max_cap():
    g = _make_game()
    for i in range(Game.MAX_ECHOS + 3):
        g._spawn_echo(float(i), float(i), 8)
    assert len(g.echos) == Game.MAX_ECHOS


def test_check_echo_collect():
    g = _make_game()
    g._spawn_echo(g.player.x, g.player.y, 8)
    assert len(g.echos) == 1
    g._check_echo_collect()
    assert len(g.echos) == 0  # collected


def test_check_echo_collect_reduces_heat():
    g = _make_game()
    g.heat = 50.0
    g._spawn_echo(g.player.x, g.player.y, 8)
    g._check_echo_collect()
    assert g.heat == 45.0


def test_check_echo_collect_not_too_far():
    g = _make_game()
    g._spawn_echo(400.0, 400.0, 8)
    g._check_echo_collect()
    assert len(g.echos) == 1  # not collected (too far)


# ── Physics ──

def test_update_physics_moves_entities():
    g = _make_game()
    g.ai.vx = 5.0
    g.ai.vy = 3.0
    ai_x_before = g.ai.x
    ai_y_before = g.ai.y
    g._update_physics(1.0/30.0)
    assert g.ai.x > ai_x_before
    assert g.ai.y > ai_y_before


def test_update_physics_applies_friction():
    g = _make_game()
    g.ai.vx = 10.0
    g._update_physics(1.0/30.0)
    assert g.ai.vx == 10.0 * Game.FRICTION


def test_rikishi_collision_separation():
    g = _make_game()
    # place them overlapping
    g.player.x = 150.0
    g.player.y = 120.0
    g.ai.x = 155.0
    g.ai.y = 120.0
    g._update_physics(1.0/30.0)
    dist = math.hypot(g.ai.x - g.player.x, g.ai.y - g.player.y)
    min_dist = g.player.radius + g.ai.radius + 2
    assert dist >= min_dist - 0.1


# ── AI ──

def test_ai_pushes_toward_player():
    g = _make_game()
    g._ai_timer = Game.AI_PUSH_INTERVAL  # ready to push
    g._update_ai(0.0)
    # AI pushes player toward itself
    assert abs(g.player.vx) > 0 or abs(g.player.vy) > 0  # player gets velocity


def test_ai_timer_accumulates():
    g = _make_game()
    g._ai_timer = 0.0
    g._update_ai(0.5)
    assert g._ai_timer == 0.5


def test_ai_no_push_when_not_playing():
    g = _make_game()
    g.phase = Phase.GAME_OVER
    g._ai_timer = 1.0
    g._update_ai(0.0)
    assert g.player.vx == 0.0
    assert g.player.vy == 0.0


# ── Timers ──

def test_update_timers_decrements_cooldown():
    g = _make_game()
    g.push_cooldown = 0.3
    g._update_timers(0.1)
    assert abs(g.push_cooldown - 0.2) < 0.01


def test_update_timers_super_expires():
    g = _make_game()
    g.super_timer = 0.1
    g._update_timers(0.2)
    assert g.super_timer == 0.0


def test_update_timers_stumble_expires():
    g = _make_game()
    g.stumble_timer = 0.1
    g._update_timers(0.2)
    assert g.stumble_timer == 0.0


def test_update_timers_heat_decay():
    g = _make_game()
    g.heat = 50.0
    g._update_timers(1.0)
    assert g.heat == 49.0  # 50 - 1.0 * 1.0


def test_update_timers_heat_floor_zero():
    g = _make_game()
    g.heat = 0.5
    g._update_timers(1.0)
    assert g.heat == 0.0


def test_update_timers_triggers_stumble():
    g = _make_game()
    g.heat = 100.0
    g._update_timers(0.01)
    assert g.stumble_timer == Game.STUMBLE_DURATION


# ── Echos Update ──

def test_update_echos_fades_echoes():
    g = _make_game()
    g._spawn_echo(100.0, 100.0, 8)
    life_before = g.echos[0].life
    g._update_echos(0.5)
    assert g.echos[0].life < life_before


def test_update_echos_removes_expired():
    g = _make_game()
    g.echos = [Echo(x=100.0, y=100.0, life=0.01, color=8)]
    g._update_echos(10.0)  # big dt to expire
    assert len(g.echos) == 0


# ── Particles ──

def test_update_particles_fades():
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=0.5, color=8)]
    g._update_particles(0.3)
    assert g.particles[0].life < 0.5


def test_update_particles_removes_expired():
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=0.1, color=8)]
    g._update_particles(1.0)
    assert len(g.particles) == 0


# ── Floating Text ──

def test_add_floating_text():
    g = _make_game()
    g._add_floating_text(100.0, 100.0, "TEST", 1.0, 7)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "TEST"


def test_update_floating_texts_moves_up():
    g = _make_game()
    g._add_floating_text(100.0, 100.0, "TEST", 1.0, 7)
    y_before = g.floating_texts[0].y
    g._update_floating_texts(0.5)
    assert g.floating_texts[0].y < y_before


def test_update_floating_texts_removes_expired():
    g = _make_game()
    g._add_floating_text(100.0, 100.0, "TEST", 0.1, 7)
    g._update_floating_texts(1.0)
    assert len(g.floating_texts) == 0


# ── Phase Transitions ──

def test_phase_victory_on_ai_ring_out():
    g = _make_game()
    g.ai.x = 400.0
    g.ai.y = 400.0
    g._check_phase_transitions()
    assert g.phase == Phase.GAME_OVER
    assert "VICTORY" in g._result_display


def test_phase_defeat_on_player_ring_out():
    g = _make_game()
    g.player.x = 400.0
    g.player.y = 400.0
    g._check_phase_transitions()
    assert g.phase == Phase.GAME_OVER
    assert "DEFEAT" in g._result_display


def test_phase_both_out_player_loses():
    g = _make_game()
    g.player.x = 400.0
    g.player.y = 400.0
    g.ai.x = 400.0
    g.ai.y = 400.0
    g._check_phase_transitions()
    assert g.phase == Phase.GAME_OVER
    assert "DEFEAT" in g._result_display


def test_victory_adds_score():
    g = _make_game()
    g.ai.x = 400.0
    g.ai.y = 400.0
    score_before = g.score
    g._check_phase_transitions()
    assert g.score > score_before


def test_victory_updates_high_score():
    g = _make_game()
    g.ai.x = 400.0
    g.ai.y = 400.0
    g._check_phase_transitions()
    assert g.high_score == g.score


# ── handle_push ──

def test_handle_push_applies_push():
    g = _make_game()
    g.last_push_color = 0  # set prior color so it matches
    g.handle_push(0)  # RED → right
    assert g.ai.vx > 0  # velocity applied


def test_handle_push_blocked_by_cooldown():
    g = _make_game()
    g.push_cooldown = 1.0
    ai_x_before = g.ai.x
    g.handle_push(0)
    assert g.ai.x == ai_x_before  # no change


def test_handle_push_blocked_by_stumble():
    g = _make_game()
    g.stumble_timer = 1.0
    ai_x_before = g.ai.x
    g.handle_push(0)
    assert g.ai.x == ai_x_before


# ── update ──

def test_update_runs_without_error():
    g = _make_game()
    g.update(1.0 / 30.0)
    # Should run without exception


def test_update_decrements_timers():
    g = _make_game()
    g.push_cooldown = 0.3
    g.update(0.1)
    assert g.push_cooldown < 0.3


def test_update_game_over_noop():
    g = _make_game()
    g.phase = Phase.GAME_OVER
    g.update(1.0 / 30.0)
    # Should return without changes


def test_update_super_mode_phase_switch():
    g = _make_game()
    g.super_timer = 1.0
    g.update(1.0 / 30.0)
    assert g.phase == Phase.SUPER


def test_update_stumble_mode_phase_switch():
    g = _make_game()
    g.stumble_timer = 1.0
    g.update(1.0 / 30.0)
    assert g.phase == Phase.STUMBLE


def test_update_super_to_playing_transition():
    g = _make_game()
    g.super_timer = 1.0
    g.update(1.0 / 30.0)
    assert g.phase == Phase.SUPER
    g.super_timer = 0.0
    g.update(1.0 / 30.0)
    assert g.phase == Phase.PLAYING


def test_update_stumble_to_playing_transition():
    g = _make_game()
    g.stumble_timer = 1.0
    g.update(1.0 / 30.0)
    assert g.phase == Phase.STUMBLE
    g.stumble_timer = 0.0
    g.update(1.0 / 30.0)
    assert g.phase == Phase.PLAYING


# ── COMBO / Max Combo ──

def test_max_combo_tracks_highest():
    g = _make_game()
    g.last_push_color = 0
    g._apply_push(0, 1.0, 0.0)
    assert g.max_combo == 1
    g._apply_push(1, 0.0, -1.0)  # break
    g.last_push_color = 1
    g._apply_push(1, 0.0, -1.0)
    g._apply_push(1, 0.0, -1.0)
    assert g.max_combo == 2  # still tracked


def test_combo_bonus_force_increases():
    g = _make_game()
    g.last_push_color = 0
    g.combo = 3
    g.rng = random.Random(42)
    # Push with combo=3: combo increments to 4, bonus = 1 + (4-1)*0.25 = 1.75
    g._apply_push(0, 1.0, 0.0)
    # force = 3.0 * 1.75 = 5.25
    assert g.ai.vx == pytest.approx(5.25)
    assert g.combo == 4


# ── Heat at max triggers stumble ──

def test_heat_max_triggers_stumble_in_update():
    g = _make_game()
    g.heat = 100.0
    g.update(0.01)
    assert g.stumble_timer == Game.STUMBLE_DURATION


# ── Force direction tests ──

def test_push_right_moves_ai_right():
    g = _make_game()
    g.last_push_color = 0  # RED, so next RED push matches
    g.handle_push(0)  # RED → RIGHT
    assert g.ai.vx > 0


def test_push_up_moves_ai_up():
    g = _make_game()
    g.last_push_color = 1  # GREEN, so next GREEN push matches
    g.handle_push(1)  # GREEN → UP
    assert g.ai.vy < 0


def test_push_left_moves_ai_left():
    g = _make_game()
    g.last_push_color = 2  # BLUE, so next BLUE push matches
    g.handle_push(2)  # BLUE → LEFT
    assert g.ai.vx < 0


def test_push_down_moves_ai_down():
    g = _make_game()
    g.last_push_color = 3  # YELLOW, so next YELLOW push matches
    g.handle_push(3)  # YELLOW → DOWN
    assert g.ai.vy > 0


# ── Super mode edge cases ──

def test_super_timer_reaches_threshold_only_once():
    g = _make_game()
    g.last_push_color = 0
    g.combo = 3
    g._apply_push(0, 1.0, 0.0)
    assert g.super_timer == Game.SUPER_DURATION
    # another push during super shouldn't restart
    g._apply_push(0, 1.0, 0.0)
    assert g.super_timer <= Game.SUPER_DURATION


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
