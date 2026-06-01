"""test_imports.py — Headless logic tests for POLE CHAIN (095_pole_chain)."""
import math
import random
import sys
from pathlib import Path

PROTO_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROTO_DIR))

from main import (
    BASE_SPEED,
    BASE_VAULT,
    BAR_DECREASE,
    DARK_BLUE,
    FloatingText,
    Game,
    GREEN,
    INITIAL_BAR_Y,
    MAX_COMBO,
    MAX_HEAT,
    MAX_ROUNDS,
    MIN_BAR_Y,
    Particle,
    Phase,
    RED,
    RUNWAY_END_X,
    SPEED_PER_COMBO,
    SUPER_VAULT_COMBO,
    SUPER_VAULT_SCORE_MULT,
    VAULT_PER_COMBO,
    YELLOW,
    ZONE_COLORS,
    ZONE_COUNT_MAX,
    ZONE_COUNT_MIN,
    Zone,
)


def _make_game(seed: int = 42) -> Game:
    """Create a Game instance for headless testing (bypasses pyxel.init)."""
    g: Game = Game.__new__(Game)
    # Pre-init ALL attributes that _init_state() touches
    g.phase = Phase.TITLE
    g.round = 1
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0
    g.player_x = 20.0
    g.player_color = ZONE_COLORS[0]
    g.zones = []
    g.particles = []
    g.floats = []
    g.bar_y = INITIAL_BAR_Y
    g.speed = BASE_SPEED
    g._vault_timer = 0
    g._vault_height = 0
    g._vault_cleared = False
    g._shake_frames = 0
    g._shake_seed = 0
    g._result_timer = 0
    g._rng = random.Random()
    g._title_flash = 0
    g._super_vault_active = False
    g._init_state()
    g._rng = random.Random(seed)
    return g


# ── Dataclass tests ──


def test_zone_dataclass() -> None:
    z = Zone(x=30.0, w=28.0, color=RED)
    assert z.x == 30.0
    assert z.w == 28.0
    assert z.color == RED


def test_floating_text_dataclass() -> None:
    f = FloatingText(x=100.0, y=50.0, text="+100", color=YELLOW, life=30)
    assert f.text == "+100"
    assert f.color == YELLOW
    assert f.life == 30


def test_particle_dataclass() -> None:
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-2.0, life=15, color=RED, size=3)
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 15
    assert p.size == 3


# ── Phase enum tests ──


def test_phase_exists() -> None:
    assert Phase.TITLE is not Phase.RUNNING
    assert len(list(Phase)) == 5
    phases = {Phase.TITLE, Phase.RUNNING, Phase.VAULTING, Phase.RESULT, Phase.GAME_OVER}
    assert len(phases) == 5


# ── Color/constant tests ──


def test_zone_colors() -> None:
    assert len(ZONE_COLORS) == 4
    assert ZONE_COLORS == [RED, GREEN, DARK_BLUE, YELLOW]
    assert RED == 8
    assert GREEN == 3
    assert DARK_BLUE == 5
    assert YELLOW == 10


# ── Initial state tests ──


def test_init_state() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.round == 1
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0
    assert g.player_color == ZONE_COLORS[0]
    assert g.bar_y == INITIAL_BAR_Y
    assert g.speed == BASE_SPEED
    assert g._super_vault_active is False
    assert len(g.zones) == 0
    assert len(g.particles) == 0
    assert len(g.floats) == 0


# ── Zone spawning tests ──


def test_spawn_zones_creates_zones() -> None:
    g = _make_game()
    g._spawn_zones()
    assert ZONE_COUNT_MIN <= len(g.zones) <= ZONE_COUNT_MAX


def test_spawn_zones_all_within_bounds() -> None:
    g = _make_game()
    g._spawn_zones()
    for zone in g.zones:
        assert zone.x >= 20
        assert zone.x + zone.w <= 200
        assert zone.w >= 24
        assert zone.w <= 36
        assert zone.color in ZONE_COLORS


def test_spawn_zones_no_overlap() -> None:
    g = _make_game()
    g._spawn_zones()
    for i in range(len(g.zones) - 1):
        curr = g.zones[i]
        nxt = g.zones[i + 1]
        assert nxt.x >= curr.x + curr.w + 12


# ── Zone color matching tests ──


def test_match_zone_same_color_increments_combo() -> None:
    g = _make_game()
    assert g.combo == 0
    result = g._match_zone(g.player_color)
    assert result is True
    assert g.combo == 1
    assert g.max_combo == 1


def test_match_zone_consecutive_same_color_builds_combo() -> None:
    g = _make_game()
    for i in range(3):
        result = g._match_zone(g.player_color)
        assert result is True
    assert g.combo == 3
    assert g.max_combo == 3


def test_match_zone_wrong_color_resets_combo() -> None:
    g = _make_game()
    # Build combo first
    g._match_zone(g.player_color)
    g._match_zone(g.player_color)
    assert g.combo == 2

    # Now match wrong color
    wrong_color = [c for c in ZONE_COLORS if c != g.player_color][0]
    result = g._match_zone(wrong_color)
    assert result is False
    assert g.combo == 0


def test_match_zone_wrong_color_keeps_max_combo() -> None:
    g = _make_game()
    g._match_zone(g.player_color)
    g._match_zone(g.player_color)
    assert g.max_combo == 2

    wrong_color = [c for c in ZONE_COLORS if c != g.player_color][0]
    g._match_zone(wrong_color)
    assert g.combo == 0
    assert g.max_combo == 2


def test_match_zone_combo_capped_at_max() -> None:
    g = _make_game()
    for _ in range(MAX_COMBO + 5):
        g._match_zone(g.player_color)
    assert g.combo == MAX_COMBO


def test_match_zone_super_vault_activates_at_threshold() -> None:
    g = _make_game()
    for i in range(SUPER_VAULT_COMBO):
        g._match_zone(g.player_color)
    assert g.combo >= SUPER_VAULT_COMBO
    assert g._super_vault_active is True


def test_match_zone_super_vault_deactivates_on_reset() -> None:
    g = _make_game()
    for _ in range(SUPER_VAULT_COMBO):
        g._match_zone(g.player_color)
    assert g._super_vault_active is True

    wrong_color = [c for c in ZONE_COLORS if c != g.player_color][0]
    g._match_zone(wrong_color)
    assert g._super_vault_active is False


def test_match_zone_speed_increases_with_combo() -> None:
    g = _make_game()
    assert g.speed == BASE_SPEED
    g._match_zone(g.player_color)
    assert g.speed == BASE_SPEED + 1 * SPEED_PER_COMBO
    g._match_zone(g.player_color)
    assert g.speed == BASE_SPEED + 2 * SPEED_PER_COMBO


def test_match_zone_speed_resets_on_wrong_color() -> None:
    g = _make_game()
    g._match_zone(g.player_color)
    g._match_zone(g.player_color)
    assert g.speed > BASE_SPEED

    wrong_color = [c for c in ZONE_COLORS if c != g.player_color][0]
    g._match_zone(wrong_color)
    assert g.speed == BASE_SPEED


# ── Player color cycling tests ──


def test_player_color_cycles_after_match() -> None:
    g = _make_game()
    original = g.player_color
    g._match_zone(original)
    assert g.player_color != original
    assert g.player_color in ZONE_COLORS


def test_player_color_cycles_after_wrong_match() -> None:
    g = _make_game()
    original = g.player_color
    wrong = [c for c in ZONE_COLORS if c != original][0]
    g._match_zone(wrong)
    assert g.player_color != original
    assert g.player_color in ZONE_COLORS


def test_player_color_wraps_around() -> None:
    g = _make_game()
    for _ in range(len(ZONE_COLORS)):
        g._match_zone(g.player_color)
    assert g.player_color == ZONE_COLORS[0]


# ── Vault height computation tests ──


def test_compute_vault_height_base() -> None:
    g = _make_game()
    assert g._compute_vault_height() == BASE_VAULT


def test_compute_vault_height_with_combo() -> None:
    g = _make_game()
    g._match_zone(g.player_color)
    g._match_zone(g.player_color)
    assert g._compute_vault_height() == BASE_VAULT + 2 * VAULT_PER_COMBO


def test_compute_vault_height_super_guaranteed_clear() -> None:
    g = _make_game()
    # Build super vault
    for _ in range(SUPER_VAULT_COMBO):
        g._match_zone(g.player_color)
    assert g._super_vault_active is True
    h = g._compute_vault_height()
    # Super vault guarantees clearance: h >= bar_y + 10
    assert h >= g.bar_y + 10


# ── Vault clear check tests ──


def test_check_vault_clear_sufficient() -> None:
    g = _make_game()
    assert g._check_vault_clear(g.bar_y) is True
    assert g._check_vault_clear(g.bar_y + 10) is True


def test_check_vault_clear_insufficient() -> None:
    g = _make_game()
    assert g._check_vault_clear(g.bar_y - 10) is False


# ── Super vault tests ──


def test_is_super_vault_below_threshold() -> None:
    g = _make_game()
    assert g._is_super_vault() is False
    g._match_zone(g.player_color)
    assert g._is_super_vault() is False


def test_is_super_vault_at_threshold() -> None:
    g = _make_game()
    for _ in range(SUPER_VAULT_COMBO):
        g._match_zone(g.player_color)
    assert g._is_super_vault() is True


# ── Round advancement tests ──


def test_advance_round_increments_round_and_resets_state() -> None:
    g = _make_game()
    g.combo = 5
    g.max_combo = 5
    g.heat = 2
    g.speed = BASE_SPEED + 5
    g._vault_height = 100
    g._super_vault_active = True

    g._advance_round()
    assert g.round == 2
    assert g.combo == 0
    assert g.speed == BASE_SPEED
    assert g._vault_height == 0
    assert g._vault_cleared is False
    assert g._super_vault_active is False
    assert g._vault_timer == 0
    assert g.phase == Phase.RUNNING


def test_advance_round_bar_rises() -> None:
    g = _make_game()
    old_bar = g.bar_y
    g._advance_round()
    assert g.bar_y == old_bar - BAR_DECREASE


def test_advance_round_bar_caps_at_minimum() -> None:
    g = _make_game()
    g.bar_y = MIN_BAR_Y + 2
    g._advance_round()
    assert g.bar_y == MIN_BAR_Y


def test_advance_round_spawns_new_zones() -> None:
    g = _make_game()
    g._advance_round()
    assert len(g.zones) >= ZONE_COUNT_MIN


# ── Game over tests ──


def test_is_game_over_heat_limit() -> None:
    g = _make_game()
    assert g._is_game_over() is False
    g.heat = MAX_HEAT
    assert g._is_game_over() is True


def test_is_game_over_round_limit() -> None:
    g = _make_game()
    assert g._is_game_over() is False
    g.round = MAX_ROUNDS + 1
    assert g._is_game_over() is True


def test_is_game_over_both_limits() -> None:
    g = _make_game()
    g.heat = MAX_HEAT
    g.round = MAX_ROUNDS + 1
    assert g._is_game_over() is True


# ── Phase transition tests ──


def test_start_vault_sets_state() -> None:
    g = _make_game()
    g._match_zone(g.player_color)
    g._start_vault()
    assert g.phase == Phase.VAULTING
    assert g._vault_timer == 0
    assert g._vault_height == BASE_VAULT + VAULT_PER_COMBO


def test_start_vault_super_vault_guaranteed_clear() -> None:
    g = _make_game()
    for _ in range(SUPER_VAULT_COMBO):
        g._match_zone(g.player_color)
    g._start_vault()
    assert g._vault_cleared is True


def test_start_result_clear_adds_score() -> None:
    g = _make_game()
    g.combo = 3
    g._vault_height = INITIAL_BAR_Y + 10
    g._vault_cleared = True
    g._super_vault_active = False
    old_score = g.score
    g._start_result()
    assert g.score == old_score + 100 * 3
    assert g.phase == Phase.RESULT


def test_start_result_super_vault_triple_score() -> None:
    g = _make_game()
    g.combo = 4
    g._vault_height = INITIAL_BAR_Y + 10
    g._vault_cleared = True
    g._super_vault_active = True
    old_score = g.score
    g._start_result()
    assert g.score == old_score + 100 * 4 * SUPER_VAULT_SCORE_MULT


def test_start_result_miss_adds_heat() -> None:
    g = _make_game()
    g._vault_height = INITIAL_BAR_Y - 50
    g._vault_cleared = False
    g._super_vault_active = False
    old_heat = g.heat
    old_score = g.score
    g._start_result()
    assert g.heat == old_heat + 1
    assert g.score == old_score
    assert g.phase == Phase.RESULT


def test_maybe_end_round_game_over_heat() -> None:
    g = _make_game()
    g.heat = MAX_HEAT
    g._maybe_end_round()
    assert g.phase == Phase.GAME_OVER


def test_maybe_end_round_continues() -> None:
    g = _make_game()
    g.heat = 0
    g.round = 1
    g._maybe_end_round()
    assert g.phase == Phase.RUNNING
    assert g.round == 2


# ── Particle system tests ──


def test_spawn_particles_creates_expected_count() -> None:
    g = _make_game()
    assert len(g.particles) == 0
    g._spawn_particles(100.0, 100.0, RED, 5)
    assert len(g.particles) == 5


def test_update_particles_reduces_life() -> None:
    g = _make_game()
    g._spawn_particles(100.0, 100.0, RED, 3, (0.0, 0.0))
    for p in g.particles:
        assert p.life >= 8  # min life is 8
    g._update_particles()
    for p in g.particles:
        assert p.life >= 7  # decreased by 1


def test_update_particles_removes_dead() -> None:
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=RED)]
    g._update_particles()
    assert len(g.particles) == 0


def test_update_particles_applies_gravity() -> None:
    g = _make_game()
    p = Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=10, color=RED)
    g.particles = [p]
    g._update_particles()
    assert p.vy == 0.3


# ── Floating text tests ──


def test_spawn_floating_text() -> None:
    g = _make_game()
    g._spawn_floating_text("TEST", YELLOW, 40)
    assert len(g.floats) == 1
    assert g.floats[0].text == "TEST"
    assert g.floats[0].color == YELLOW
    assert g.floats[0].life == 40


def test_update_floats_moves_and_decrements() -> None:
    g = _make_game()
    g._spawn_floating_text("TEST", YELLOW, 40)
    old_y = g.floats[0].y
    old_life = g.floats[0].life
    g._update_floats()
    assert g.floats[0].y == old_y - 0.6
    assert g.floats[0].life == old_life - 1


def test_update_floats_removes_expired() -> None:
    g = _make_game()
    g.floats = [FloatingText(x=0.0, y=0.0, text="X", color=RED, life=1)]
    g._update_floats()
    assert len(g.floats) == 0


# ── Start running test ──


def test_start_running_initializes_run_state() -> None:
    g = _make_game()
    g._start_running()
    assert g.phase == Phase.RUNNING
    assert g.player_x == 20.0
    assert g.combo == 0
    assert g.speed == BASE_SPEED
    assert g._super_vault_active is False
    assert len(g.zones) >= ZONE_COUNT_MIN


# ── Reset test ──


def test_reset_restores_initial_state() -> None:
    g = _make_game()
    g.round = 5
    g.score = 1000
    g.combo = 7
    g.max_combo = 7
    g.heat = 3
    g.phase = Phase.GAME_OVER

    g.reset()
    assert g.round == 1
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0
    assert g.phase == Phase.TITLE
    assert g.player_color == ZONE_COLORS[0]


# ── Scoring edge cases ──


def test_score_with_zero_combo_clear() -> None:
    g = _make_game()
    g._vault_height = INITIAL_BAR_Y + 10
    g._vault_cleared = True
    g._super_vault_active = False
    old_score = g.score
    g._start_result()
    # max(1, combo=0) = 1 → 100 * 1 = 100
    assert g.score == old_score + 100


def test_score_min_combo_guaranteed() -> None:
    g = _make_game()
    g.combo = 0
    g._vault_height = INITIAL_BAR_Y
    g._vault_cleared = True
    g._super_vault_active = False
    old_score = g.score
    g._start_result()
    assert g.score > old_score  # at least 100 points


# ── Deterministic spawn test ──


def test_spawn_zones_deterministic_with_seed() -> None:
    g1 = _make_game(42)
    g1._spawn_zones()
    g2 = _make_game(42)
    g2._spawn_zones()
    assert len(g1.zones) == len(g2.zones)
    for z1, z2 in zip(g1.zones, g2.zones):
        assert z1.x == z2.x
        assert z1.w == z2.w
        assert z1.color == z2.color


# ── next_zone_color wrap test ──


def test_next_zone_color_full_cycle() -> None:
    g = _make_game()
    seen = set()
    for _ in range(len(ZONE_COLORS)):
        seen.add(g.player_color)
        g.player_color = g._next_zone_color()
    assert seen == set(ZONE_COLORS)
    # Should be back to start
    assert g.player_color == ZONE_COLORS[0]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
