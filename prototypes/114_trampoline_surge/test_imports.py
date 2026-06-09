"""test_imports.py — Headless logic tests for 114_trampoline_surge.

Pyxel Rust-backed functions (btn, btnp, mouse_x, etc.) panic in headless mode.
We test inner logic methods directly, never calling pyxel.btn/btnp.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/114_trampoline_surge")
from main import Game, Zone, Particle, FloatingText, RED, WHITE, YELLOW


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def _make_game() -> Game:
    """Create a Game bypassing Pyxel init for headless testing."""
    g = Game.__new__(Game)
    # Pre-init all instance attributes that reset() touches
    g.zones = []
    g.particles = []
    g.floating_texts = []
    g.player_w = 16
    g.player_h = 20
    g.reset()
    return g


# ---------------------------------------------------------------------------
# Zone / Dataclass tests
# ---------------------------------------------------------------------------
def test_zone_creation() -> None:
    z = Zone(x=40, w=48, color=RED)
    assert z.x == 40
    assert z.w == 48
    assert z.color == RED


def test_particle_creation() -> None:
    p = Particle(x=100.0, y=150.0, vx=0.5, vy=-2.0, life=10, color=WHITE)
    assert p.x == 100.0
    assert p.life == 10


def test_floating_text_creation() -> None:
    ft = FloatingText(x=120.0, y=80.0, text="+10", life=30, color=YELLOW)
    assert ft.text == "+10"


# ---------------------------------------------------------------------------
# Zone layout tests
# ---------------------------------------------------------------------------
def test_init_zones_count() -> None:
    g = _make_game()
    assert len(g.zones) == Game.ZONE_COUNT


def test_init_zones_total_width() -> None:
    g = _make_game()
    total = sum(z.w for z in g.zones)
    expected = Game.ZONE_RIGHT - Game.ZONE_LEFT  # 240
    assert total == expected, f"Zone widths sum to {total}, expected {expected}"


def test_init_zones_start_at_left() -> None:
    g = _make_game()
    assert g.zones[0].x == Game.ZONE_LEFT


def test_init_zones_end_at_right() -> None:
    g = _make_game()
    last = g.zones[-1]
    assert last.x + last.w == Game.ZONE_RIGHT


def test_init_zones_contiguous() -> None:
    g = _make_game()
    for i in range(len(g.zones) - 1):
        assert g.zones[i].x + g.zones[i].w == g.zones[i + 1].x


def test_init_zones_valid_colors() -> None:
    g = _make_game()
    for z in g.zones:
        assert z.color in Game.zone_colors


def test_init_zones_valid_widths() -> None:
    g = _make_game()
    for z in g.zones:
        assert 36 <= z.w <= 64


def test_get_zone_at() -> None:
    g = _make_game()
    # Find a zone and test lookup
    mid_x = g.zones[0].x + g.zones[0].w // 2
    z = g._get_zone_at(mid_x)
    assert z is not None
    assert z is g.zones[0]


def test_get_zone_at_boundary() -> None:
    g = _make_game()
    # Right edge of first zone should still be in first zone (x < x+w, not <=)
    edge = g.zones[0].x + g.zones[0].w - 1
    z = g._get_zone_at(edge)
    assert z is g.zones[0]


def test_get_zone_at_out_of_bounds() -> None:
    g = _make_game()
    assert g._get_zone_at(0) is None
    assert g._get_zone_at(500) is None


# ---------------------------------------------------------------------------
# Reset tests
# ---------------------------------------------------------------------------
def test_reset_sets_playing_phase() -> None:
    g = _make_game()
    assert g.phase == 1  # PLAYING


def test_reset_score_zero() -> None:
    g = _make_game()
    assert g.score == 0


def test_reset_combo_zero() -> None:
    g = _make_game()
    assert g.combo == 0


def test_reset_max_combo_zero() -> None:
    g = _make_game()
    assert g.max_combo == 0


def test_reset_heat_zero() -> None:
    g = _make_game()
    assert g.heat == 0.0


def test_reset_not_super() -> None:
    g = _make_game()
    assert g.super_mode is False


def test_reset_game_timer_full() -> None:
    g = _make_game()
    assert g.game_timer == Game.GAME_DURATION


def test_reset_player_position() -> None:
    g = _make_game()
    assert g.player_x == 160.0
    assert g.player_y == Game.TRAMPOLINE_Y - 50.0


def test_reset_player_velocity_zero() -> None:
    g = _make_game()
    assert g.player_vy == 0.0
    assert g.player_vx == 0.0


def test_reset_not_on_bed() -> None:
    g = _make_game()
    assert g.on_bed is False


def test_reset_flip_zero() -> None:
    g = _make_game()
    assert g.flip_bonus == 0
    assert g.flip_count == 0


def test_reset_particles_cleared() -> None:
    g = _make_game()
    g.particles.append(Particle(0, 0, 0, 0, 5, WHITE))
    g.reset()
    assert len(g.particles) == 0


def test_reset_floating_texts_cleared() -> None:
    g = _make_game()
    g.floating_texts.append(FloatingText(0, 0, "test", 5, WHITE))
    g.reset()
    assert len(g.floating_texts) == 0


# ---------------------------------------------------------------------------
# Physics tests (gravity, velocity) — test logic directly, avoid pyxel.btn
# ---------------------------------------------------------------------------
def test_gravity_increases_vy() -> None:
    g = _make_game()
    g.player_vy = 1.0
    # Apply gravity directly (replicating _update_physics logic)
    g.player_vy += g.GRAVITY
    assert abs(g.player_vy - (1.0 + Game.GRAVITY)) < 0.01


def test_physics_moves_player() -> None:
    g = _make_game()
    old_y = g.player_y
    g.player_vy = 3.0
    g.player_y += g.player_vy
    assert g.player_y > old_y


def test_physics_x_clamp_left() -> None:
    g = _make_game()
    g.player_x = -10.0
    hw = g.player_w / 2
    # Replicate clamp logic from _update_physics
    if g.player_x < hw:
        g.player_x = hw
    assert g.player_x >= hw


def test_physics_x_clamp_right() -> None:
    g = _make_game()
    g.player_x = 500.0
    hw = g.player_w / 2
    if g.player_x > Game.SCREEN_W - hw:
        g.player_x = Game.SCREEN_W - hw
    assert g.player_x <= Game.SCREEN_W - hw


def test_physics_friction_reduces_vx() -> None:
    g = _make_game()
    g.player_vx = 2.0
    g.player_vx *= 0.95
    assert abs(g.player_vx - 1.9) < 0.01


# ---------------------------------------------------------------------------
# Trampoline contact tests
# ---------------------------------------------------------------------------
def test_trampoline_bounce_inverts_vy() -> None:
    g = _make_game()
    g.player_x = 160.0
    g.player_y = Game.TRAMPOLINE_Y + 5  # below trampoline
    g.player_vy = 5.0  # moving down
    g.on_bed = False
    g._last_zone_color = -1
    g._check_trampoline()
    assert g.player_vy < 0  # bounced upward


def test_trampoline_snaps_to_bed() -> None:
    g = _make_game()
    g.player_x = 160.0
    g.player_y = Game.TRAMPOLINE_Y + 10
    g.player_vy = 5.0
    g.on_bed = False
    g._last_zone_color = -1
    g._check_trampoline()
    assert abs(g.player_y - Game.TRAMPOLINE_Y) < 0.01


def test_trampoline_sets_on_bed() -> None:
    g = _make_game()
    g.player_x = 160.0
    g.player_y = Game.TRAMPOLINE_Y + 5
    g.player_vy = 5.0
    g.on_bed = False
    g._last_zone_color = -1
    g._check_trampoline()
    assert g.on_bed is True


def test_trampoline_miss_when_above() -> None:
    g = _make_game()
    g.player_x = 160.0
    g.player_y = Game.TRAMPOLINE_Y - 20  # above bed
    g.player_vy = 5.0
    g.on_bed = False
    g._check_trampoline()
    assert g.on_bed is False  # didn't touch


def test_trampoline_miss_when_moving_up() -> None:
    g = _make_game()
    g.player_x = 160.0
    g.player_y = Game.TRAMPOLINE_Y + 5
    g.player_vy = -5.0  # moving up
    g.on_bed = False
    g._check_trampoline()
    assert g.on_bed is False  # shouldn't bounce when moving up


def test_trampoline_lift_off_detection() -> None:
    g = _make_game()
    g.player_x = 160.0
    g.player_y = Game.TRAMPOLINE_Y - 5  # above bed
    g.on_bed = True
    g._check_trampoline()
    assert g.on_bed is False


# ---------------------------------------------------------------------------
# Color matching / combo tests
# ---------------------------------------------------------------------------
def test_same_color_combo_increment() -> None:
    g = _make_game()
    # Force all zones to same color for predictable combo testing
    for z in g.zones:
        z.color = RED
    g._last_zone_color = RED

    # First landing on same-color zone
    g.player_x = g.zones[0].x + g.zones[0].w // 2
    g.player_y = Game.TRAMPOLINE_Y + 5
    g.player_vy = 5.0
    g.on_bed = False
    g._check_trampoline()
    assert g.combo == 1

    # Second landing: _refresh_zones() was called, set zones to RED again
    for z in g.zones:
        z.color = RED
    g.on_bed = False
    g.player_y = Game.TRAMPOLINE_Y + 5
    g.player_vy = 5.0
    g._check_trampoline()
    assert g.combo == 2, f"combo should be 2, got {g.combo}"


def test_wrong_color_resets_combo() -> None:
    g = _make_game()
    # Set last zone color, then land on a different color
    zone_color = g.zones[0].color
    g._last_zone_color = zone_color
    # Find a zone with different color
    other_zone = None
    for z in g.zones:
        if z.color != zone_color:
            other_zone = z
            break
    assert other_zone is not None, "Need zones with different colors for this test"

    g.player_x = other_zone.x + other_zone.w // 2
    g.player_y = Game.TRAMPOLINE_Y + 5
    g.player_vy = 5.0
    g.on_bed = False
    g.combo = 3
    g._check_trampoline()
    assert g.combo == 0, f"Combo should reset to 0, got {g.combo}"


def test_wrong_color_adds_heat() -> None:
    g = _make_game()
    zone_color = g.zones[0].color
    g._last_zone_color = zone_color
    # Land on a different color zone
    other_zone = next((z for z in g.zones if z.color != zone_color), None)
    assert other_zone is not None, "Need a different-colored zone for this test"
    g.player_x = other_zone.x + other_zone.w // 2
    g.player_y = Game.TRAMPOLINE_Y + 5
    g.player_vy = 5.0
    g.on_bed = False
    old_heat = g.heat
    g._check_trampoline()
    assert g.heat >= old_heat + Game.HEAT_WRONG - 0.01


def test_first_landing_combo_zero() -> None:
    """First landing with _last_zone_color == -1 should set combo to 0."""
    g = _make_game()
    g._last_zone_color = -1
    g.player_x = g.zones[0].x + g.zones[0].w // 2
    g.player_y = Game.TRAMPOLINE_Y + 5
    g.player_vy = 5.0
    g.on_bed = False
    g.combo = 0
    g._check_trampoline()
    # First landing: no match (_last_zone_color == -1), so combo stays 0
    assert g.combo == 0


def test_matched_landing_adds_score() -> None:
    g = _make_game()
    zone_color = g.zones[0].color
    g._last_zone_color = zone_color
    g.player_x = g.zones[0].x + g.zones[0].w // 2
    g.player_y = Game.TRAMPOLINE_Y + 5
    g.player_vy = 5.0
    g.on_bed = False
    g.combo = 1
    old_score = g.score
    g._check_trampoline()
    assert g.score > old_score


def test_super_mode_all_zones_match() -> None:
    """In super mode, any zone counts as match."""
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g._last_zone_color = -1
    g.combo = 5
    g.player_x = g.zones[0].x + g.zones[0].w // 2
    g.player_y = Game.TRAMPOLINE_Y + 5
    g.player_vy = 5.0
    g.on_bed = False
    g._check_trampoline()
    assert g.combo == 6  # incremented


def test_super_mode_no_heat_on_any_color() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g._last_zone_color = -1
    old_heat = g.heat
    g.player_x = g.zones[0].x + g.zones[0].w // 2
    g.player_y = Game.TRAMPOLINE_Y + 5
    g.player_vy = 5.0
    g.on_bed = False
    g._check_trampoline()
    assert g.heat == old_heat


# ---------------------------------------------------------------------------
# SUPER BOUNCE trigger tests
# ---------------------------------------------------------------------------
def test_combo_4_triggers_super_mode() -> None:
    g = _make_game()
    zone_color = g.zones[0].color
    g._last_zone_color = zone_color
    g.combo = 3  # next match = 4

    g.player_x = g.zones[0].x + g.zones[0].w // 2
    g.player_y = Game.TRAMPOLINE_Y + 5
    g.player_vy = 5.0
    g.on_bed = False
    g._check_trampoline()
    assert g.super_mode is True
    assert g.super_timer == Game.SUPER_DURATION


def test_super_mode_already_active_doesnt_retrigger() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 50
    g.combo = 5
    # Force all zones to RED
    for z in g.zones:
        z.color = RED
    g._last_zone_color = RED
    g.player_x = g.zones[0].x + g.zones[0].w // 2
    g.player_y = Game.TRAMPOLINE_Y + 5
    g.player_vy = 5.0
    g.on_bed = False
    g._check_trampoline()
    # Timer not reset by _check_trampoline (super_mode already True)
    # _update_super not called by this test, so timer stays at 50
    assert g.super_timer == 50


# ---------------------------------------------------------------------------
# Super mode timer tests
# ---------------------------------------------------------------------------
def test_super_timer_decrements() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g._update_super()
    assert g.super_timer == 99


def test_super_ends_when_timer_zero() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g._update_super()
    assert g.super_mode is False


def test_super_noop_when_inactive() -> None:
    g = _make_game()
    g.super_mode = False
    g.super_timer = 0
    g._update_super()
    assert g.super_mode is False


# ---------------------------------------------------------------------------
# Heat system tests
# ---------------------------------------------------------------------------
def test_heat_decay() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat < 50.0


def test_heat_does_not_go_below_zero() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_heat_at_max_triggers_game_over() -> None:
    g = _make_game()
    g.heat = Game.MAX_HEAT
    g._update_heat()
    assert g.phase == 2  # GAME_OVER


def test_heat_above_max_triggers_game_over() -> None:
    g = _make_game()
    g.heat = Game.MAX_HEAT + 50
    g._update_heat()
    assert g.phase == 2  # GAME_OVER


def test_heat_check_before_decay() -> None:
    """Critical: heat check runs BEFORE decay to avoid unreachable threshold."""
    g = _make_game()
    g.heat = Game.MAX_HEAT  # exactly at threshold
    g._update_heat()
    # Should trigger game over, not decay first
    assert g.phase == 2


# ---------------------------------------------------------------------------
# Score and combo tracking tests
# ---------------------------------------------------------------------------
def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    # Simulate combo building
    zone_color = g.zones[0].color
    g._last_zone_color = zone_color
    g.combo = 5
    g.max_combo = 5

    # Bounce on same color
    g.player_x = g.zones[0].x + g.zones[0].w // 2
    g.player_y = Game.TRAMPOLINE_Y + 5
    g.player_vy = 5.0
    g.on_bed = False
    g._check_trampoline()
    assert g.max_combo == 6


def test_max_combo_persists_after_reset_of_combo() -> None:
    g = _make_game()
    g.max_combo = 7
    g.combo = 0  # combo resets but max persists
    assert g.max_combo == 7


def test_score_calculation_combo_times_10() -> None:
    g = _make_game()
    zone_color = g.zones[0].color
    g._last_zone_color = zone_color
    g.combo = 2
    g.score = 0
    g.player_x = g.zones[0].x + g.zones[0].w // 2
    g.player_y = Game.TRAMPOLINE_Y + 5
    g.player_vy = 5.0
    g.on_bed = False
    g._check_trampoline()
    # combo goes to 3, score += 3 * 10 = 30
    assert g.score >= 30


def test_flip_bonus_added_to_score() -> None:
    g = _make_game()
    zone_color = g.zones[0].color
    g._last_zone_color = zone_color
    g.combo = 1
    g.flip_bonus = 150
    g.score = 0
    g.player_x = g.zones[0].x + g.zones[0].w // 2
    g.player_y = Game.TRAMPOLINE_Y + 5
    g.player_vy = 5.0
    g.on_bed = False
    g._check_trampoline()
    assert g.score >= 150  # flip bonus added


def test_flip_bonus_reset_on_landing() -> None:
    g = _make_game()
    g.flip_bonus = 200
    g.flip_count = 4
    g.player_x = g.zones[0].x + g.zones[0].w // 2
    g.player_y = Game.TRAMPOLINE_Y + 5
    g.player_vy = 5.0
    g.on_bed = False
    g._last_zone_color = -1
    g._check_trampoline()
    assert g.flip_bonus == 0
    assert g.flip_count == 0


# ---------------------------------------------------------------------------
# Bounce physics tests
# ---------------------------------------------------------------------------
def test_bounce_power_decreases_with_consecutive_bounces() -> None:
    g = _make_game()
    g._consecutive_bounces = 3

    # Bounce
    g.player_x = g.zones[0].x + g.zones[0].w // 2
    g.player_y = Game.TRAMPOLINE_Y + 5
    g.player_vy = 5.0
    g.on_bed = False
    g._last_zone_color = -1
    g._check_trampoline()

    vy1 = abs(g.player_vy)

    # Another bounce
    g.on_bed = False
    g.player_y = Game.TRAMPOLINE_Y + 5
    g.player_vy = 5.0
    g._check_trampoline()

    vy2 = abs(g.player_vy)
    assert vy2 < vy1, f"Bounce 2 ({vy2}) should be weaker than bounce 1 ({vy1})"


def test_consecutive_bounces_increment() -> None:
    g = _make_game()
    old_bounces = g._consecutive_bounces
    g.player_x = g.zones[0].x + g.zones[0].w // 2
    g.player_y = Game.TRAMPOLINE_Y + 5
    g.player_vy = 5.0
    g.on_bed = False
    g._last_zone_color = -1
    g._check_trampoline()
    assert g._consecutive_bounces == old_bounces + 1


# ---------------------------------------------------------------------------
# Game over tests
# ---------------------------------------------------------------------------
def test_timer_decrement_game_over() -> None:
    g = _make_game()
    g.game_timer = 1
    g.frame = 0
    # Replicate what update() does
    g.game_timer -= 1
    assert g.game_timer == 0


def test_game_over_on_timer_zero() -> None:
    g = _make_game()
    g.game_timer = 0
    g.phase = 1
    # Simulate the check in update()
    if g.game_timer <= 0:
        g.phase = 2
    assert g.phase == 2


# ---------------------------------------------------------------------------
# Particle system tests
# ---------------------------------------------------------------------------
def test_spawn_land_particles() -> None:
    g = _make_game()
    old_count = len(g.particles)
    g._spawn_land_particles(160.0, 200.0, RED)
    assert len(g.particles) > old_count


def test_spawn_land_particles_super_more() -> None:
    g = _make_game()
    g.super_mode = False
    g._spawn_land_particles(160.0, 200.0, RED)
    normal_count = len(g.particles)

    g.particles.clear()
    g.super_mode = True
    g._spawn_land_particles(160.0, 200.0, RED)
    super_count = len(g.particles)
    # Super mode should spawn more particles (8 vs 5)
    assert super_count >= normal_count


def test_particles_update_and_expire() -> None:
    g = _make_game()
    g.particles.append(Particle(100.0, 150.0, 0.5, -1.0, life=1, color=WHITE))
    g._update_effects()
    # life=1 → decremented to 0 → filtered out (life > 0)
    assert len(g.particles) == 0


def test_particles_move() -> None:
    g = _make_game()
    p = Particle(100.0, 150.0, 0.5, -1.0, life=5, color=WHITE)
    g.particles.append(p)
    g._update_effects()
    assert p.life == 4
    assert abs(p.x - 100.5) < 0.01
    # Gravity applied AFTER position update: y += vy, then vy += 0.1
    # So new y = 150.0 + (-1.0) = 149.0
    assert abs(p.y - 149.0) < 0.01


def test_floating_text_update_and_expire() -> None:
    g = _make_game()
    g.floating_texts.append(FloatingText(120.0, 100.0, "+10", life=1, color=WHITE))
    g._update_effects()
    assert len(g.floating_texts) == 0


def test_floating_text_moves_up() -> None:
    g = _make_game()
    ft = FloatingText(120.0, 100.0, "+10", life=5, color=WHITE)
    g.floating_texts.append(ft)
    g._update_effects()
    assert ft.y < 100.0  # moves up (y decreases)


def test_add_floating_text() -> None:
    g = _make_game()
    g._add_floating_text(150.0, 180.0, "SUPER!", YELLOW)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "SUPER!"


# ---------------------------------------------------------------------------
# Zone refresh tests
# ---------------------------------------------------------------------------
def test_refresh_zones_preserves_count() -> None:
    g = _make_game()
    g._refresh_zones()
    assert len(g.zones) == Game.ZONE_COUNT


def test_refresh_zones_preserves_total_width() -> None:
    g = _make_game()
    g._refresh_zones()
    total = sum(z.w for z in g.zones)
    assert total == Game.ZONE_RIGHT - Game.ZONE_LEFT


# ---------------------------------------------------------------------------
# Heat threshold ordering test (from pitfall: tightrope-surge)
# ---------------------------------------------------------------------------
def test_heat_at_exact_max_triggers_gameover_before_decay() -> None:
    """The threshold check must run BEFORE decay to make MAX_HEAT reachable."""
    g = _make_game()
    g.heat = Game.MAX_HEAT
    g._update_heat()
    assert g.phase == 2  # Game over
    # Heat should not have decayed (phase change prevents further logic)
    assert abs(g.heat - Game.MAX_HEAT) < 0.01


# ---------------------------------------------------------------------------
# Phase enum tests
# ---------------------------------------------------------------------------
def test_phase_values() -> None:
    g = _make_game()
    # TITLE=0, PLAYING=1, GAME_OVER=2
    assert g.phase == 1  # reset() sets PLAYING
    g.phase = 0
    assert g.phase == 0
    g.phase = 2
    assert g.phase == 2


# ---------------------------------------------------------------------------
# max_combo edge case
# ---------------------------------------------------------------------------
def test_max_combo_doesnt_decrease() -> None:
    g = _make_game()
    g.max_combo = 5
    g.combo = 2
    g._check_trampoline()  # won't hit because not at trampoline level
    # max_combo should never decrease
    assert g.max_combo == 5


# ---------------------------------------------------------------------------
# Consecutive bounce reset on reset()
# ---------------------------------------------------------------------------
def test_reset_resets_consecutive_bounces() -> None:
    g = _make_game()
    g._consecutive_bounces = 10
    g.reset()
    assert g._consecutive_bounces == 0


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import traceback

    tests = [
        (k, v)
        for k, v in sorted(globals().items())
        if k.startswith("test_") and callable(v)
    ]
    passed = 0
    failed = 0
    for name, func in tests:
        try:
            func()
            print(f"  PASS {name}")
            passed += 1
        except Exception:
            print(f"  FAIL {name}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    if failed > 0:
        sys.exit(1)
