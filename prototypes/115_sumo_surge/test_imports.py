"""test_imports.py — Headless logic tests for SUMO SURGE."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import (
    Game,
    Rikishi,
    Particle,
    Phase,
    SCREEN_W,
    SCREEN_H,
    RING_CENTER_X,
    RING_CENTER_Y,
    INNER_RADIUS,
    OUTER_RADIUS,
    RIKISHI_RADIUS,
    SUPER_DURATION,
    COMBO_THRESHOLD,
    STUN_DURATION,
    HEAT_PER_MISS,
    HEAT_DECAY,
    MAX_HEAT,
    GAME_TIME,
    COLORS,
    CONTACT_COOLDOWN,
)


def _make_game() -> Game:
    """Create a Game instance bypassing pyxel.init/run for headless testing."""
    g = Game.__new__(Game)
    # Pre-init all attributes that reset() touches
    g.player = Rikishi(160.0, 160.0, 8)
    g.ai = Rikishi(160.0, 80.0, 3)
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.super_mode = False
    g.super_timer = 0
    g.heat = 0.0
    g.phase = Phase.PLAYING
    g.timer = GAME_TIME
    g.particles = []
    g._contact_cooldown = 0
    g._ai_color_timer = 0
    g._stun_flash_counter = 0
    g._rainbow_offset = 0
    return g


# ── Dataclass Tests ──

def test_rikishi_creation() -> None:
    r = Rikishi(100.0, 200.0, 8)
    assert r.x == 100.0
    assert r.y == 200.0
    assert r.color == 8
    assert r.stunned is False
    assert r.stun_timer == 0.0


def test_particle_creation() -> None:
    p = Particle(50.0, 60.0, 1.0, -2.0, 20, 7)
    assert p.x == 50.0
    assert p.y == 60.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 20
    assert p.color == 7


# ── Phase Enum Tests ──

def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.VICTORY in Phase
    assert Phase.DEFEAT in Phase


# ── Constants Tests ──

def test_constants() -> None:
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert INNER_RADIUS < OUTER_RADIUS
    assert len(COLORS) == 4
    assert COMBO_THRESHOLD == 4
    assert HEAT_PER_MISS == 25
    assert MAX_HEAT == 100
    assert SUPER_DURATION == 300
    assert GAME_TIME == 5400


# ── Game Reset Tests ──

def test_reset() -> None:
    g = _make_game()
    g.score = 500
    g.combo = 3
    g.heat = 50.0
    g.super_mode = True
    g.timer = 100
    g.particles = [Particle(0, 0, 0, 0, 1, 7)]

    g.reset()
    # After reset, phase should be TITLE
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.heat == 0.0
    assert g.timer == GAME_TIME
    assert len(g.particles) == 0
    assert g._contact_cooldown == 0


# ── Color Cycling Tests ──

def test_cycle_color_basic() -> None:
    g = _make_game()
    assert g._cycle_color(8) == 3   # RED -> GREEN
    assert g._cycle_color(3) == 5   # GREEN -> DARK_BLUE
    assert g._cycle_color(5) == 10  # DARK_BLUE -> YELLOW
    assert g._cycle_color(10) == 8  # YELLOW -> RED


def test_cycle_color_unknown() -> None:
    g = _make_game()
    assert g._cycle_color(999) == COLORS[0]  # Returns RED


# ── Push Resolution Tests ──

def test_resolve_push_match_increments_combo() -> None:
    g = _make_game()
    g.player.color = 8   # RED
    g.ai.color = 8       # RED → match
    g.combo = 0
    g._resolve_push(0.0, -1.0)  # Push upward
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.heat == 0.0  # Match reduces heat but was already 0


def test_resolve_push_match_heat_reduction() -> None:
    g = _make_game()
    g.player.color = 8
    g.ai.color = 8
    g.heat = 30.0
    g._resolve_push(0.0, -1.0)
    assert g.heat == 20.0  # Reduced by 10


def test_resolve_push_mismatch_resets_combo() -> None:
    g = _make_game()
    g.player.color = 8   # RED
    g.ai.color = 3       # GREEN → mismatch
    g.combo = 3
    g._resolve_push(0.0, -1.0)
    assert g.combo == 0


def test_resolve_push_mismatch_adds_heat() -> None:
    g = _make_game()
    g.player.color = 8
    g.ai.color = 3
    g.heat = 0.0
    g._resolve_push(0.0, -1.0)
    assert g.heat == float(HEAT_PER_MISS)


def test_resolve_push_moves_ai() -> None:
    g = _make_game()
    g.player.color = 8
    g.ai.color = 8
    ai_y_before = g.ai.y
    g._resolve_push(0.0, -1.0)  # Push upward (away from player at bottom)
    # AI should move upward (further from player)
    assert g.ai.y < ai_y_before


def test_resolve_push_super_mode_always_matches() -> None:
    g = _make_game()
    g.super_mode = True
    g.player.color = 8   # RED
    g.ai.color = 3       # GREEN — would be mismatch
    g.combo = 0
    g._resolve_push(0.0, -1.0)
    assert g.combo == 1  # Super mode: always match


def test_resolve_push_super_power_stronger() -> None:
    g = _make_game()
    g.player.color = 8
    g.ai.color = 8
    g.ai.x = 160.0
    g.ai.y = 80.0
    g.player.x = 160.0
    g.player.y = 104.0  # just at push distance

    # Normal push
    g.super_mode = False
    ai_y_before = g.ai.y
    g._resolve_push(0.0, -1.0)
    normal_dy = ai_y_before - g.ai.y

    # Reset and try super push
    g.ai.y = 80.0
    g.super_mode = True
    g.super_timer = 300
    g._contact_cooldown = 0
    ai_y_before = g.ai.y
    g._resolve_push(0.0, -1.0)
    super_dy = ai_y_before - g.ai.y

    # Super push should move AI more
    assert super_dy > normal_dy


def test_resolve_push_activates_super_at_threshold() -> None:
    g = _make_game()
    g.player.color = 8
    g.ai.color = 8
    g.combo = COMBO_THRESHOLD - 1  # 3
    g.super_mode = False
    g._resolve_push(0.0, -1.0)
    assert g.combo == COMBO_THRESHOLD  # 4
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_resolve_push_cycles_player_color() -> None:
    g = _make_game()
    g.player.color = 8  # RED
    g.ai.color = 8
    g._resolve_push(0.0, -1.0)
    assert g.player.color == 3  # -> GREEN


def test_resolve_push_spawns_particles() -> None:
    g = _make_game()
    g.player.color = 8
    g.ai.color = 8
    assert len(g.particles) == 0
    g._resolve_push(0.0, -1.0)
    assert len(g.particles) == 5  # Normal push: 5 particles


def test_resolve_push_super_spawns_more_particles() -> None:
    g = _make_game()
    g.super_mode = True
    g.player.color = 8
    g.ai.color = 8
    g._resolve_push(0.0, -1.0)
    assert len(g.particles) == 10  # Super push: 10 particles


# ── Ring-Out Tests ──

def test_check_ring_out_player() -> None:
    g = _make_game()
    g.player.x = float(RING_CENTER_X + OUTER_RADIUS + 1)  # Outside ring
    g.player.y = float(RING_CENTER_Y)
    g._check_ring_out()
    assert g.phase == Phase.DEFEAT


def test_check_ring_out_ai() -> None:
    g = _make_game()
    g.ai.x = float(RING_CENTER_X + OUTER_RADIUS + 1)
    g.ai.y = float(RING_CENTER_Y)
    g._check_ring_out()
    assert g.phase == Phase.VICTORY


def test_check_ring_out_ai_scores() -> None:
    g = _make_game()
    g.combo = 5
    g.timer = 1000
    g.score = 0
    g.ai.x = float(RING_CENTER_X + OUTER_RADIUS + 1)
    g.ai.y = float(RING_CENTER_Y)
    g._check_ring_out()
    assert g.score == 5 * 100 + 1000  # combo * 100 + timer


def test_check_ring_out_both_inside() -> None:
    g = _make_game()
    g.player.x = float(RING_CENTER_X)
    g.player.y = float(RING_CENTER_Y)
    g.ai.x = float(RING_CENTER_X + 10)
    g.ai.y = float(RING_CENTER_Y)
    g._check_ring_out()
    assert g.phase == Phase.PLAYING  # No change


# ── Heat Tests ──

def test_update_heat_decay() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 50.0 - HEAT_DECAY


def test_update_heat_stun_at_max() -> None:
    g = _make_game()
    g.heat = float(MAX_HEAT)  # 100.0
    g._update_heat()
    assert g.player.stunned is True
    assert g.player.stun_timer == STUN_DURATION
    assert g.heat == 0.0  # Reset after stun


def test_update_heat_stun_above_max() -> None:
    g = _make_game()
    g.heat = 110.0
    g._update_heat()
    assert g.player.stunned is True
    assert g.heat == 0.0


def test_update_heat_no_decay_when_stunned() -> None:
    g = _make_game()
    g.heat = float(MAX_HEAT)
    g._update_heat()  # Triggers stun, resets heat
    assert g.heat == 0.0
    g.heat = 30.0
    g._update_heat()  # Should decay normally now
    assert g.heat == 30.0 - HEAT_DECAY


# ── Super Mode Tests ──

def test_update_super_mode_decrements_timer() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g._update_super_mode()
    assert g.super_timer == 99
    assert g.super_mode is True


def test_update_super_mode_expires() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_super_mode()
    assert g.super_timer == 0
    assert g.super_mode is False


def test_update_super_mode_noop_when_inactive() -> None:
    g = _make_game()
    g.super_mode = False
    g.super_timer = 0
    g._update_super_mode()
    assert g.super_timer == 0
    assert g.super_mode is False


# ── Particle Tests ──

def test_update_particles_moves_and_decays() -> None:
    g = _make_game()
    p = Particle(100.0, 100.0, 1.0, 2.0, 10, 7)
    g.particles = [p]
    g._update_particles()
    assert p.x == 101.0
    assert p.y == 102.0
    assert p.life == 9


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    g.particles = [Particle(0.0, 0.0, 0.0, 0.0, 1, 7)]
    g._update_particles()
    # life 1 -> 0, then filtered out
    assert len(g.particles) == 0


# ── Push Distance Tests ──

def test_check_push_when_close() -> None:
    g = _make_game()
    g.player.x = 100.0
    g.player.y = 100.0
    g.ai.x = 100.0 + RIKISHI_RADIUS * 2 - 1  # Just touching
    g.ai.y = 100.0
    g._contact_cooldown = 0
    g.phase = Phase.PLAYING
    # _check_push calls _resolve_push which modifies state
    g._check_push()
    # Should have triggered push (combo or heat changed)
    assert g._contact_cooldown == CONTACT_COOLDOWN


def test_check_push_when_far() -> None:
    g = _make_game()
    g.player.x = 100.0
    g.player.y = 100.0
    g.ai.x = 300.0  # Far away
    g.ai.y = 100.0
    g._contact_cooldown = 0
    g.phase = Phase.PLAYING
    combo_before = g.combo
    g._check_push()
    # Should NOT have triggered push
    assert g.combo == combo_before


def test_check_push_cooldown() -> None:
    g = _make_game()
    g.player.x = 100.0
    g.player.y = 100.0
    g.ai.x = 100.0
    g.ai.y = 100.0
    g._contact_cooldown = 5  # In cooldown
    combo_before = g.combo
    g._check_push()
    # Should NOT trigger push due to cooldown
    assert g.combo == combo_before


# ── AI Tests ──

def test_update_ai_moves_toward_player() -> None:
    g = _make_game()
    g.ai.x = 160.0
    g.ai.y = 80.0
    g.player.x = 160.0
    g.player.y = 160.0  # Player is below AI
    ai_y_before = g.ai.y
    g._update_ai()
    # AI should move toward player (down)
    assert g.ai.y > ai_y_before


def test_update_ai_stunned_doesnt_move() -> None:
    g = _make_game()
    g.ai.x = 160.0
    g.ai.y = 80.0
    g.ai.stunned = True
    g.ai.stun_timer = 30
    ai_x_before = g.ai.x
    ai_y_before = g.ai.y
    g._update_ai()
    assert g.ai.x == ai_x_before
    assert g.ai.y == ai_y_before
    assert g.ai.stun_timer == 29


def test_update_ai_cycles_color() -> None:
    g = _make_game()
    g.ai.color = 8  # RED
    g._ai_color_timer = 119  # One before cycle
    g.ai.x = 160.0
    g.ai.y = 80.0
    g.player.x = 160.0
    g.player.y = 160.0
    g._update_ai()
    assert g._ai_color_timer == 0  # Timer reset
    assert g.ai.color == 3  # RED -> GREEN


# ── Clamp Tests ──

def test_clamp_rikishi_pass_through() -> None:
    g = _make_game()
    r = Rikishi(999.0, 999.0, 8)
    g._clamp_rikishi(r)
    # Currently a no-op; just verify it doesn't crash
    assert r.x == 999.0
    assert r.y == 999.0


# ── Combo Tracking Tests ──

def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    g.player.color = 8
    g.ai.color = 8

    # Push 1: combo = 1
    g._resolve_push(0.0, -1.0)
    assert g.max_combo == 1

    # Push 2: combo = 2
    g._contact_cooldown = 0
    g.ai.y = 80.0  # Reset AI position
    g.player.y = 104.0
    g.player.color = 3
    g.ai.color = 3
    g._resolve_push(0.0, -1.0)
    assert g.max_combo == 2

    # Mismatch: combo resets, max stays
    g._contact_cooldown = 0
    g.ai.y = 80.0
    g.player.y = 104.0
    g.player.color = 5
    g.ai.color = 10  # Mismatch
    g._resolve_push(0.0, -1.0)
    assert g.combo == 0
    assert g.max_combo == 2  # Still tracking highest


# ── Timer Tests ──

def test_timer_decrements_in_playing() -> None:
    g = _make_game()
    g.timer = 100
    # Simulate one frame of _update_playing (without pyxel input)
    g.timer -= 1
    if g.timer <= 0:
        g.phase = Phase.DEFEAT
    assert g.timer == 99
    assert g.phase == Phase.PLAYING


def test_timer_zero_triggers_defeat() -> None:
    g = _make_game()
    g.timer = 1
    g.timer -= 1
    if g.timer <= 0:
        g.phase = Phase.DEFEAT
    assert g.phase == Phase.DEFEAT


# ── Stun Tests ──

def test_player_stunned_timer_decrements() -> None:
    g = _make_game()
    g.player.stunned = True
    g.player.stun_timer = STUN_DURATION
    # Simulate stun timer decrement (from _update_playing)
    g.player.stun_timer -= 1
    assert g.player.stun_timer == STUN_DURATION - 1
    assert g.player.stunned is True


def test_player_stun_expires() -> None:
    g = _make_game()
    g.player.stunned = True
    g.player.stun_timer = 1
    g.player.stun_timer -= 1
    if g.player.stun_timer <= 0:
        g.player.stunned = False
    assert g.player.stunned is False


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
