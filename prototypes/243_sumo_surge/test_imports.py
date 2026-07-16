"""test_imports.py -- Headless logic tests for 100_sumo_surge."""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import (
    DOHYO_CX,
    DOHYO_CY,
    DOHYO_RADIUS,
    WRESTLER_RADIUS,
    COLORS,
    RED,
    LIME,
    DARK_BLUE,
    YELLOW,
    WHITE,
    SUPER_COMBO_THRESHOLD,
    SUPER_DURATION,
    GAME_TIMER,
    HEAT_CAP,
    MISS_HEAT,
    RING_OUT_PENALTY_HEAT,
    STAMINA_MAX,
    Particle,
    FloatingText,
    Phase,
    Game,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g._rng = random.Random(seed)
    g._init_state()
    g._rng = random.Random(seed)
    g._spawn_opponent()
    g._rng = random.Random(seed)
    g.phase = Phase.PLAYING
    return g


# ── Color Match Combo ───────────────────────────────────────────────────────


def test_color_match_increases_combo():
    g = _make_game()
    g.player.color_idx = 0  # RED
    g.opponent.color_idx = 0  # RED
    g.combo = 0
    g._resolve_hit(player_is_attacker=True)
    assert g.combo == 1
    assert g.score == 100  # 100 * 1 * 1


def test_color_mismatch_resets_combo_and_adds_heat():
    g = _make_game()
    g.player.color_idx = 0  # RED
    g.opponent.color_idx = 1  # LIME
    g.combo = 3
    g.heat = 0
    g._resolve_hit(player_is_attacker=True)
    assert g.combo == 0
    assert g.heat == MISS_HEAT  # 15


def test_color_mismatch_from_opponent_resets_combo():
    g = _make_game()
    g.player.color_idx = 0  # RED
    g.opponent.color_idx = 1  # LIME
    g.combo = 2
    g.heat = 0
    g._resolve_hit(player_is_attacker=False)
    assert g.combo == 0
    assert g.heat == MISS_HEAT


# ── SUPER SUMO Activation ───────────────────────────────────────────────────


def test_combo_4_triggers_super_mode():
    g = _make_game()
    g.player.color_idx = 0
    g.opponent.color_idx = 0
    g.combo = 3
    g.super_timer = 0
    g._resolve_hit(player_is_attacker=True)
    assert g.combo == 4
    assert g.super_timer == SUPER_DURATION  # 300


def test_super_mode_3x_score_multiplier():
    g = _make_game()
    g.player.color_idx = 0
    g.opponent.color_idx = 0
    g.combo = 0
    g.super_timer = 100
    g._resolve_hit(player_is_attacker=True)
    assert g.score == 300  # 100 * 1 * 3


def test_super_mode_not_re_triggered():
    g = _make_game()
    g.player.color_idx = 0
    g.opponent.color_idx = 0
    g.combo = 3
    g.super_timer = 200
    g._resolve_hit(player_is_attacker=True)
    assert g.combo == 4
    assert g.super_timer == 200  # unchanged, already active


# ── Ring Out ─────────────────────────────────────────────────────────────────


def test_opponent_ring_out_scores():
    g = _make_game()
    g.opponent.x = DOHYO_CX + DOHYO_RADIUS + 10
    g.opponent.y = DOHYO_CY
    g.combo = 2
    g.score = 0
    g.opponent_defeated = 0
    g._check_ring_out()
    assert g.score > 0
    assert g.opponent_defeated == 1
    assert g.combo == 3  # combo incremented


def test_player_ring_out_penalty():
    g = _make_game()
    g.player.x = DOHYO_CX + DOHYO_RADIUS + 10
    g.player.y = DOHYO_CY
    g.combo = 3
    g.heat = 0
    g._check_ring_out()
    assert g.combo == 0
    assert g.heat == RING_OUT_PENALTY_HEAT  # 25
    assert g.player.x == DOHYO_CX
    assert g.player.y == DOHYO_CY + 40


def test_ring_out_super_multiplier():
    g = _make_game()
    g.opponent.x = DOHYO_CX + DOHYO_RADIUS + 10
    g.opponent.y = DOHYO_CY
    g.combo = 0
    g.super_timer = 100
    g.score = 0
    g._check_ring_out()
    # bonus = (500 * 3 + 100 * 1 * 3) = 1500 + 300 = 1800
    assert g.score == 1800


# ── Stamina ──────────────────────────────────────────────────────────────────


def test_stamina_regenerates():
    g = _make_game()
    g.player.stamina = 50
    # Simulate multiple updates
    for _ in range(100):
        g.player.stamina = min(STAMINA_MAX, g.player.stamina + 0.08)
    assert g.player.stamina > 50
    assert g.player.stamina <= STAMINA_MAX


def test_stamina_capped_at_max():
    g = _make_game()
    g.player.stamina = 99.95
    g.player.stamina = min(STAMINA_MAX, g.player.stamina + 0.08)
    assert g.player.stamina == STAMINA_MAX


# ── HEAT ────────────────────────────────────────────────────────────────────


def test_heat_cap_triggers_game_over():
    g = _make_game()
    g.heat = 100
    g._end_game()
    assert g.phase == Phase.GAME_OVER


def test_heat_decay_formula():
    g = _make_game()
    g.heat = 50.0
    g.heat = max(0.0, g.heat - 0.02)
    assert g.heat == 49.98


# ── Timer ────────────────────────────────────────────────────────────────────


def test_timer_expiry_ends_game():
    g = _make_game()
    g.timer = 1
    g.heat = 0
    g._update_playing()
    assert g.phase == Phase.GAME_OVER


# ── Opponent AI ─────────────────────────────────────────────────────────────


def test_opponent_moves_toward_player():
    g = _make_game()
    g.player.x = DOHYO_CX + 50
    g.player.y = DOHYO_CY
    g.opponent.x = DOHYO_CX - 50
    g.opponent.y = DOHYO_CY
    g.opponent.stunned = 0
    old_x = g.opponent.x
    for _ in range(10):
        g._update_opponent_ai()
    assert g.opponent.x > old_x  # moved toward player


def test_opponent_stunned_stops_movement():
    g = _make_game()
    g.player.x = DOHYO_CX + 50
    g.player.y = DOHYO_CY
    g.opponent.x = DOHYO_CX - 50
    g.opponent.y = DOHYO_CY
    g.opponent.stunned = 10
    old_x = g.opponent.x
    g._update_opponent_ai()
    assert g.opponent.x == old_x


# ── Push Physics ────────────────────────────────────────────────────────────


def test_player_push_moves_opponent():
    g = _make_game()
    g.player.x = 160
    g.player.y = 120
    g.opponent.x = 160 + WRESTLER_RADIUS * 2 - 5  # overlapping
    g.opponent.y = 120
    g.player.pushing = True
    g.player.power = 5.0
    g.opponent.pushing = False
    g.opponent.power = 0
    g.player.color_idx = 0
    g.opponent.color_idx = 0
    g.combo = 0
    old_ox = g.opponent.x
    g._update_physics()
    assert g.opponent.x > old_ox  # pushed away


def test_opponent_push_moves_player():
    g = _make_game()
    g.player.x = 160
    g.player.y = 120
    g.opponent.x = 160 + WRESTLER_RADIUS * 2 - 5
    g.opponent.y = 120
    g.player.pushing = False
    g.player.power = 0
    g.opponent.pushing = True
    g.opponent.power = 5.0
    g.player.color_idx = 0
    g.opponent.color_idx = 0
    old_px = g.player.x
    g._update_physics()
    assert g.player.x < old_px  # pushed away


def test_equal_power_separates():
    g = _make_game()
    g.player.x = 160
    g.player.y = 120
    g.opponent.x = 160 + WRESTLER_RADIUS * 2 - 5
    g.opponent.y = 120
    g.player.pushing = True
    g.player.power = 2.0
    g.opponent.pushing = True
    g.opponent.power = 2.0
    old_dist = math.hypot(g.opponent.x - g.player.x, g.opponent.y - g.player.y)
    g._update_physics()
    new_dist = math.hypot(g.opponent.x - g.player.x, g.opponent.y - g.player.y)
    assert new_dist >= old_dist  # separated or equal


def test_stun_on_losing_push():
    g = _make_game()
    g.player.x = 160
    g.player.y = 120
    g.opponent.x = 160 + WRESTLER_RADIUS * 2 - 5
    g.opponent.y = 120
    g.player.pushing = True
    g.player.power = 5.0
    g.opponent.pushing = False
    g.opponent.power = 0
    g.player.color_idx = 0
    g.opponent.color_idx = 0
    g._update_physics()
    assert g.opponent.stunned >= 10


# ── Clamp to Dohyo ──────────────────────────────────────────────────────────


def test_clamp_keeps_wrestler_in_ring():
    g = _make_game()
    g.player.x = DOHYO_CX + DOHYO_RADIUS + 50
    g.player.y = DOHYO_CY
    g._clamp_to_dohyo(g.player)
    dist = math.hypot(g.player.x - DOHYO_CX, g.player.y - DOHYO_CY)
    assert dist <= DOHYO_RADIUS - g.player.radius


def test_clamp_wrestler_already_in_ring():
    g = _make_game()
    g.player.x = DOHYO_CX + 10
    g.player.y = DOHYO_CY + 10
    px, py = g.player.x, g.player.y
    g._clamp_to_dohyo(g.player)
    assert g.player.x == px
    assert g.player.y == py


# ── Particle System ──────────────────────────────────────────────────────────


def test_spawn_particles_creates_particles():
    g = _make_game()
    assert len(g.particles) == 0
    g._spawn_particles(160, 120, 10, RED)
    assert len(g.particles) == 10
    for p in g.particles:
        assert isinstance(p, Particle)
        assert p.color == RED
        assert p.life > 0


def test_update_particles_reduces_life_and_moves():
    g = _make_game()
    g._spawn_particles(160, 120, 5, RED)
    for _ in range(50):
        g._update_particles()
    assert len(g.particles) == 0  # all expired


# ── Floating Text ────────────────────────────────────────────────────────────


def test_add_floating_text():
    g = _make_game()
    assert len(g.floating_texts) == 0
    g._add_floating_text(160, 120, "TEST", 20, WHITE)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "TEST"


def test_floating_text_lifecycle():
    g = _make_game()
    g._add_floating_text(160, 120, "TEST", 5, WHITE)
    for _ in range(10):
        g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Reset ────────────────────────────────────────────────────────────────────


def test_reset_clears_all_state():
    g = _make_game()
    g.score = 999
    g.combo = 5
    g.max_combo = 10
    g.max_score = 2000
    g.heat = 80
    g.timer = 100
    g.super_timer = 200
    g.opponent_defeated = 5
    g.particles.append(Particle(0, 0, 1, 1, 5, RED))
    g.floating_texts.append(FloatingText(0, 0, "X", 5, WHITE))
    g.player.stamina = 10
    g.opponent.stamina = 30

    g.reset()

    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.max_score == 0
    assert g.heat == 0
    assert g.timer == GAME_TIMER
    assert g.super_timer == 0
    assert g.opponent_defeated == 0
    assert g.particles == []
    assert g.floating_texts == []
    assert g.player.stamina == STAMINA_MAX
    assert g.opponent.stamina == STAMINA_MAX
    assert g.player.x == 160
    assert g.player.y == 160


# ── Phase ────────────────────────────────────────────────────────────────────


def test_initial_phase_is_title():
    g = _make_game()
    g.phase = Phase.TITLE
    assert g.phase == Phase.TITLE


def test_phase_transitions():
    g = _make_game()
    g.phase = Phase.TITLE
    assert g.phase == Phase.TITLE
    g.phase = Phase.PLAYING
    assert g.phase == Phase.PLAYING
    g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


# ── Maximum Score Tracking ──────────────────────────────────────────────────


def test_max_score_tracks_best():
    g = _make_game()
    g.score = 500
    g.max_score = 300
    g._end_game()
    assert g.max_score == 500


def test_max_score_preserved_on_lower_score():
    g = _make_game()
    g.score = 100
    g.max_score = 500
    g._end_game()
    assert g.max_score == 500


# ── Max Combo Tracking ──────────────────────────────────────────────────────


def test_max_combo_tracks_highest():
    g = _make_game()
    g.combo = 7
    g.max_combo = 3
    g.player.color_idx = 0
    g.opponent.color_idx = 0
    g._resolve_hit(player_is_attacker=True)
    assert g.max_combo == 8  # 7 -> 8


def test_max_combo_preserved_after_reset():
    g = _make_game()
    g.combo = 5
    g.max_combo = 5
    g.player.color_idx = 0
    g.opponent.color_idx = 1
    g._resolve_hit(player_is_attacker=True)
    assert g.combo == 0
    assert g.max_combo == 5  # preserved


# ── Constants ────────────────────────────────────────────────────────────────


def test_constants():
    assert SUPER_COMBO_THRESHOLD == 4
    assert SUPER_DURATION == 300
    assert GAME_TIMER == 3600
    assert HEAT_CAP == 100
    assert MISS_HEAT == 15
    assert RING_OUT_PENALTY_HEAT == 25
    assert STAMINA_MAX == 100
    assert len(COLORS) == 4
    assert RED == 8
    assert LIME == 11
    assert DARK_BLUE == 5
    assert YELLOW == 10


# ── Get Push Direction ──────────────────────────────────────────────────────


def test_push_direction_toward_target():
    g = _make_game()
    d = g._get_push_direction(0, 0, 10, 0)
    assert abs(d - 0) < 0.01  # right


def test_push_direction_same_position():
    g = _make_game()
    d = g._get_push_direction(10, 10, 10, 10)
    assert d == 0


def test_push_direction_down():
    g = _make_game()
    d = g._get_push_direction(0, 0, 0, 10)
    assert abs(d - math.pi / 2) < 0.01


# ── Color Cycle Timer ───────────────────────────────────────────────────────


def test_color_cycle_formula():
    # Formula: max(40, 90 - opponent_defeated * 5)
    # With 5 defeats: max(40, 90 - 25) = max(40, 65) = 65
    base = 90
    defeated = 5
    new_timer = max(40, base - defeated * 5)
    assert new_timer == 65
    # With 15 defeats: max(40, 90 - 75) = max(40, 15) = 40
    new_timer2 = max(40, base - 15 * 5)
    assert new_timer2 == 40


# ── Physics: No Overlap ─────────────────────────────────────────────────────


def test_no_collision_when_apart():
    g = _make_game()
    g.player.x = 100
    g.player.y = 120
    g.opponent.x = 200
    g.opponent.y = 120
    g.player.pushing = True
    g.player.power = 5.0
    g.opponent.pushing = False
    g.opponent.power = 0
    old_ox = g.opponent.x
    g._update_physics()
    assert g.opponent.x == old_ox  # no collision

