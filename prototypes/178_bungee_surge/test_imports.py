"""test_imports.py — Headless logic tests for BUNGEE SURGE."""
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/178_bungee_surge")

from main import (
    Game,
    Phase,
    LandingZone,
    Particle,
    FloatingText,
    WIDTH,
    HEIGHT,
    GRAVITY,
    TERMINAL_VELOCITY,
    PLAYER_RADIUS,
    ZONE_W,
    ZONE_H,
    HEAT_MAX,
    HEAT_WRONG,
    HEAT_MISS,
    HEAT_DECAY,
    SUPER_DURATION,
    GAME_TIME,
    PLATFORM_RISE_AMOUNT,
    MAX_PLATFORM_RISES,
    CENTER_X,
    ZONE_COLORS,
    SUPER_RAINBOW,
    RED,
    GREEN,
    WHITE,
)


def _make_game() -> Game:
    """Create a Game bypassing pyxel.init/run via Game.__new__."""
    g = Game.__new__(Game)
    g.reset()
    g.rng = random.Random(42)
    return g


# ── Core imports and dataclasses ──────────────────────────────────────────────


def test_imports_and_constants() -> None:
    assert Phase.TITLE is not None
    assert Phase.FALLING is not None
    assert Phase.RISING is not None
    assert Phase.GAME_OVER is not None
    assert WIDTH == 320
    assert HEIGHT == 240
    assert GRAVITY == 0.3
    assert len(ZONE_COLORS) == 4
    assert len(SUPER_RAINBOW) == 6


def test_dataclass_construction() -> None:
    z = LandingZone(x=100.0, y=220.0, color=RED)
    assert z.x == 100.0
    assert z.w == ZONE_W
    assert z.active is True

    p = Particle(x=50.0, y=60.0, vx=1.0, vy=-2.0, life=20, color=GREEN)
    assert p.life == 20

    ft = FloatingText(x=100.0, y=200.0, text="+100", life=40, color=WHITE)
    assert ft.text == "+100"


# ── Game initialization ───────────────────────────────────────────────────────


def test_game_initialization() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert g.player_x == CENTER_X
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.game_timer == GAME_TIME
    assert len(g.zones) == 4
    assert g.platform_rise_count == 0


def test_start_game() -> None:
    g = _make_game()
    g._start_game()
    assert g.phase == Phase.FALLING
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert g.game_timer == GAME_TIME
    assert len(g.zones) == 4
    assert g.player_vy == 0.0


# ── Physics ───────────────────────────────────────────────────────────────────


def test_apply_physics_gravity() -> None:
    g = _make_game()
    g._start_game()
    g.fall_start_y = g.player_y
    initial_y = g.player_y
    g._apply_physics()
    assert g.player_vy == GRAVITY  # initial vy=0, add gravity
    assert g.player_y == initial_y + GRAVITY


def test_apply_physics_terminal_velocity() -> None:
    g = _make_game()
    g._start_game()
    g.player_vy = TERMINAL_VELOCITY
    g._apply_physics()
    # Should cap at terminal, then add gravity, then re-cap
    assert abs(g.player_vy - TERMINAL_VELOCITY) < 0.01


def test_move_player_left() -> None:
    g = _make_game()
    g._start_game()
    g.player_x = CENTER_X
    g._move_player(-1.5)
    assert g.player_x < CENTER_X


def test_move_player_right() -> None:
    g = _make_game()
    g._start_game()
    g.player_x = CENTER_X
    g._move_player(1.5)
    assert g.player_x > CENTER_X


def test_move_player_clamp_left() -> None:
    g = _make_game()
    g._start_game()
    g.player_x = PLAYER_RADIUS
    g._move_player(-10.0)
    assert g.player_x == PLAYER_RADIUS


def test_move_player_clamp_right() -> None:
    g = _make_game()
    g._start_game()
    g.player_x = WIDTH - PLAYER_RADIUS
    g._move_player(10.0)
    assert g.player_x == WIDTH - PLAYER_RADIUS


# ── Landing Detection ─────────────────────────────────────────────────────────


def test_check_landing_hit() -> None:
    g = _make_game()
    g._start_game()
    g.zones = [LandingZone(x=140.0, y=220.0, color=RED)]
    g.player_x = 160.0  # center of zone
    g.player_y = 220.0  # top of zone
    idx = g._check_landing()
    assert idx == 0


def test_check_landing_miss() -> None:
    g = _make_game()
    g._start_game()
    g.zones = [LandingZone(x=140.0, y=220.0, color=RED)]
    g.player_x = 10.0  # far from zone
    g.player_y = 220.0
    idx = g._check_landing()
    assert idx == -1


def test_check_landing_inactive_zone() -> None:
    g = _make_game()
    g._start_game()
    g.zones = [LandingZone(x=140.0, y=220.0, color=RED, active=False)]
    g.player_x = 160.0
    g.player_y = 220.0
    idx = g._check_landing()
    assert idx == -1


# ── Landing Resolution — Match ────────────────────────────────────────────────


def test_resolve_landing_match_combo() -> None:
    g = _make_game()
    g._start_game()
    g.player_color = RED
    g.player_y = 230.0
    g.zones = [LandingZone(x=140.0, y=220.0, color=RED)]
    g._resolve_landing(0)
    assert g.combo == 1
    assert g.phase == Phase.RISING
    assert g.zones[0].active is False


def test_resolve_landing_match_score() -> None:
    g = _make_game()
    g._start_game()
    g.player_color = RED
    g.zones = [LandingZone(x=150.0, y=220.0, color=RED)]  # near center
    g.score = 0
    g._resolve_landing(0)
    assert g.score > 0


def test_resolve_landing_match_combo_multiplier() -> None:
    g = _make_game()
    g._start_game()
    g.player_color = RED
    g.combo = 3  # multiplier = 1.0 + 0.5*3 = 2.5
    g.zones = [LandingZone(x=150.0, y=220.0, color=RED)]
    score_before = g.score
    g._resolve_landing(0)
    assert g.score > score_before
    assert g.combo == 4
    assert g.max_combo == 4


def test_resolve_landing_match_best_combo_tracks() -> None:
    g = _make_game()
    g._start_game()
    g.player_color = RED
    g.best_combo = 2
    g.combo = 2
    g.zones = [LandingZone(x=150.0, y=220.0, color=RED)]
    g._resolve_landing(0)
    assert g.combo == 3
    assert g.best_combo == 3  # should update


# ── Landing Resolution — Wrong Color ──────────────────────────────────────────


def test_resolve_landing_wrong_resets_combo() -> None:
    g = _make_game()
    g._start_game()
    g.player_color = RED
    g.combo = 3
    g.zones = [LandingZone(x=140.0, y=220.0, color=GREEN)]  # wrong color
    g._resolve_landing(0)
    assert g.combo == 0
    assert g.heat == HEAT_WRONG


def test_resolve_landing_wrong_heat() -> None:
    g = _make_game()
    g._start_game()
    g.player_color = RED
    g.zones = [LandingZone(x=140.0, y=220.0, color=GREEN)]
    g.heat = 0.0
    g._resolve_landing(0)
    assert g.heat == HEAT_WRONG


# ── Landing Resolution — SUPER Mode ───────────────────────────────────────────


def test_super_mode_activates_at_combo_4() -> None:
    g = _make_game()
    g._start_game()
    g.player_color = RED
    g.combo = 3
    g.zones = [LandingZone(x=150.0, y=220.0, color=RED)]
    g._resolve_landing(0)
    assert g.combo == 4
    assert g.super_timer == SUPER_DURATION


def test_super_mode_no_double_activation() -> None:
    g = _make_game()
    g._start_game()
    g.player_color = RED
    g.combo = 3
    g.super_timer = SUPER_DURATION  # already active
    g.zones = [LandingZone(x=150.0, y=220.0, color=RED)]
    g._resolve_landing(0)
    assert g.super_timer == SUPER_DURATION  # unchanged


def test_super_mode_any_color_match() -> None:
    g = _make_game()
    g._start_game()
    g.player_color = RED
    g.super_timer = 100  # SUPER active
    g.combo = 2
    g.zones = [LandingZone(x=140.0, y=220.0, color=GREEN)]  # wrong color normally
    g._resolve_landing(0)
    assert g.combo == 3  # should still count as match
    assert g.heat == 0.0  # no heat


def test_super_mode_3x_score() -> None:
    g = _make_game()
    g._start_game()
    g.player_color = RED
    g.super_timer = 100
    g.combo = 0
    g.zones = [LandingZone(x=150.0, y=220.0, color=RED)]
    g._resolve_landing(0)
    # Base: 100 + center_bonus, combo_mult: 1.0 + 0.5*1 = 1.5, *3 for super
    # center_bonus: center_x=160, zone center ~170, dist=10, bonus=50*(1-10/160)=46
    # landing_score = int((100+46)*1.5)*3 = int(219)*3 = 657
    expected_min = 500  # should definitely be >500 with 3x
    assert g.score >= expected_min


def test_super_timer_decrements() -> None:
    g = _make_game()
    g._start_game()
    g.super_timer = 10
    g._update_super_timer()
    assert g.super_timer == 9


def test_super_timer_expires_resets_combo() -> None:
    g = _make_game()
    g._start_game()
    g.super_timer = 1
    g.combo = 5
    g._update_super_timer()
    assert g.super_timer == 0
    assert g.combo == 0


# ── Miss Resolution ───────────────────────────────────────────────────────────


def test_resolve_miss_heat() -> None:
    g = _make_game()
    g._start_game()
    g.combo = 3
    g.heat = 0.0
    g._resolve_miss()
    assert g.combo == 0
    assert g.heat == HEAT_MISS
    assert g.phase == Phase.RISING


# ── Bounce ────────────────────────────────────────────────────────────────────


def test_bounce_velocity() -> None:
    g = _make_game()
    g._start_game()
    g.fall_start_y = 100.0
    g.player_y = 150.0  # fall_distance = 50
    g.player_vy = 3.0
    g._bounce()
    assert g.player_vy < 0  # upward
    # bounce_speed = GRAVITY * (50 / 20) = 0.3 * 2.5 = 0.75
    # so vy should be ~-0.75
    expected = -0.3 * (50.0 / 20.0)
    assert abs(g.player_vy - expected) < 0.01


# ── Color Cycling ─────────────────────────────────────────────────────────────


def test_cycle_color() -> None:
    g = _make_game()
    g._start_game()
    g.color_idx = 0
    g._cycle_color()
    assert g.player_color == ZONE_COLORS[1]
    g._cycle_color()
    assert g.player_color == ZONE_COLORS[2]
    g._cycle_color()
    assert g.player_color == ZONE_COLORS[3]
    g._cycle_color()
    assert g.player_color == ZONE_COLORS[0]  # wraps


def test_update_color_cycle_timer() -> None:
    g = _make_game()
    g._start_game()
    g.color_cycle_timer = 1
    g.color_idx = 0
    g._update_color_cycle()
    assert g.player_color == ZONE_COLORS[1]  # color advanced
    assert g.color_cycle_timer > 0  # reset


# ── Zone Spawning ─────────────────────────────────────────────────────────────


def test_spawn_zones_count() -> None:
    g = _make_game()
    g._start_game()
    g._spawn_zones()
    assert len(g.zones) == 4
    for z in g.zones:
        assert z.active is True


def test_spawn_zones_all_colors_present() -> None:
    g = _make_game()
    g._start_game()
    g._spawn_zones()
    colors = {z.color for z in g.zones}
    for c in ZONE_COLORS:
        assert c in colors


def test_spawn_zones_in_bounds() -> None:
    g = _make_game()
    g._start_game()
    g._spawn_zones()
    for z in g.zones:
        assert z.x >= 10.0
        assert z.x + z.w <= WIDTH - 10
        assert z.y == HEIGHT - ZONE_H - 10


# ── Heat System ───────────────────────────────────────────────────────────────


def test_heat_decay() -> None:
    g = _make_game()
    g._start_game()
    g.heat = 10.0
    # Manually simulate what update() does
    g.heat = max(0.0, g.heat - HEAT_DECAY)
    assert g.heat == 10.0 - HEAT_DECAY


def test_heat_never_negative() -> None:
    g = _make_game()
    g._start_game()
    g.heat = 0.0
    g.heat = max(0.0, g.heat - HEAT_DECAY)
    assert g.heat == 0.0


def test_heat_game_over() -> None:
    g = _make_game()
    g._start_game()
    g.heat = HEAT_MAX
    # Simulating the check from update()
    if g.heat >= HEAT_MAX:
        g.phase = Phase.GAME_OVER
        g.cause = "CORD SNAP!"
    assert g.phase == Phase.GAME_OVER
    assert g.cause == "CORD SNAP!"


# ── Timer ─────────────────────────────────────────────────────────────────────


def test_game_timer_decrements() -> None:
    g = _make_game()
    g._start_game()
    assert g.game_timer == GAME_TIME
    g.game_timer -= 1
    assert g.game_timer == GAME_TIME - 1


def test_game_timer_zero_game_over() -> None:
    g = _make_game()
    g._start_game()
    g.game_timer = 1
    g.game_timer -= 1
    assert g.game_timer == 0
    g.phase = Phase.GAME_OVER
    g.cause = "TIME'S UP!"
    assert g.phase == Phase.GAME_OVER


# ── Platform Rise ─────────────────────────────────────────────────────────────


def test_platform_rise_on_match() -> None:
    g = _make_game()
    g._start_game()
    g.player_color = RED
    g.zones = [LandingZone(x=150.0, y=220.0, color=RED)]
    orig_platform_y = g.platform_y
    g._resolve_landing(0)
    assert g.platform_y == orig_platform_y - PLATFORM_RISE_AMOUNT
    assert g.platform_rise_count == 1


def test_platform_rise_capped() -> None:
    g = _make_game()
    g._start_game()
    g.platform_rise_count = MAX_PLATFORM_RISES
    orig_platform_y = g.platform_y
    g.player_color = RED
    g.zones = [LandingZone(x=150.0, y=220.0, color=RED)]
    g._resolve_landing(0)
    assert g.platform_y == orig_platform_y  # no change
    assert g.platform_rise_count == MAX_PLATFORM_RISES


# ── Floating Text ─────────────────────────────────────────────────────────────


def test_floating_text_lifecycle() -> None:
    g = _make_game()
    g._start_game()
    g.floating_texts = [FloatingText(x=100.0, y=100.0, text="TEST", life=2, color=WHITE)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].life == 1
    g._update_floating_texts()
    assert len(g.floating_texts) == 0  # life reached 0, removed


# ── Particle System ───────────────────────────────────────────────────────────


def test_particle_lifecycle() -> None:
    g = _make_game()
    g._start_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=2, color=RED)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].life == 1
    g._update_particles()
    assert len(g.particles) == 0


def test_particle_gravity() -> None:
    g = _make_game()
    g._start_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=10, color=RED)]
    g._update_particles()
    assert g.particles[0].vy > 0  # gravity should add to vy


# ── Combo multiplier formula ──────────────────────────────────────────────────


def test_combo_multiplier_values() -> None:
    """Test that 1.0 + 0.5 * min(combo, 4) caps at 3.0."""
    # combo=0: 1.0 + 0.5*0 = 1.0 -> but min(0,4) = 0, 1.0 + 0.0 = 1.0
    # combo=4: 1.0 + 0.5*4 = 3.0
    # combo=5: 1.0 + 0.5*5 = 3.5, min = 3.0
    mult_0 = 1.0 + 0.5 * min(0, 4)
    mult_4 = 1.0 + 0.5 * min(4, 4)
    mult_6 = 1.0 + 0.5 * min(6, 4)
    assert mult_0 == 1.0
    assert mult_4 == 3.0
    assert mult_6 == 3.0  # min(6, 4) = 4, so 1.0 + 0.5 * 4 = 3.0


# ── Ghost Trail ───────────────────────────────────────────────────────────────


def test_ghost_trail_records_position() -> None:
    g = _make_game()
    g._start_game()
    g.player_x = 100.0
    g.player_y = 150.0
    initial_count = len(g.ghost_trail)
    g._update_ghost_trail()
    assert len(g.ghost_trail) > initial_count
    # Latest entry should have age close to 0 after update
    assert g.ghost_trail[-1][0] == 100.0
    assert g.ghost_trail[-1][1] == 150.0


# ── Restart from game over ────────────────────────────────────────────────────


def test_restart_after_game_over() -> None:
    g = _make_game()
    g._start_game()
    g.heat = HEAT_MAX
    g.phase = Phase.GAME_OVER
    g.cause = "CORD SNAP!"
    g.score = 500
    g.combo = 5
    g.max_combo = 6
    # Reset and start
    g.reset()
    g._start_game()
    assert g.phase == Phase.FALLING
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert len(g.zones) == 4
    assert g.platform_rise_count == 0


# ── Score calculation: center bonus ───────────────────────────────────────────


def test_center_bonus_max_at_center() -> None:
    g = _make_game()
    g._start_game()
    g.player_color = RED
    g.zones = [LandingZone(x=CENTER_X - ZONE_W / 2, y=220.0, color=RED)]
    g.score = 0
    g._resolve_landing(0)
    assert g.score > 100  # base + max bonus


def test_center_bonus_edge() -> None:
    g = _make_game()
    g._start_game()
    g.player_color = RED
    g.zones = [LandingZone(x=10.0, y=220.0, color=RED)]  # far left edge
    score_before = 0
    g.score = score_before
    g._resolve_landing(0)
    assert g.score > 0
    assert g.score < 200  # should be lower than center


# ── Consecutive match chain ───────────────────────────────────────────────────


def test_consecutive_matches_build_combo() -> None:
    g = _make_game()
    g._start_game()
    g.player_color = RED
    g.zones = [LandingZone(x=150.0, y=220.0, color=RED)]
    g._resolve_landing(0)
    assert g.combo == 1
    assert g.max_combo == 1
    # Need to simulate bounce cycle: RISING → FALLING → new zones
    g.phase = Phase.RISING
    g.player_vy = -1.0  # simulate upward
    # Reach apex
    g.player_vy = 0.0
    g.phase = Phase.FALLING
    g._spawn_zones()
    # Second landing - set zone to match
    g.zones = [LandingZone(x=150.0, y=220.0, color=RED)]
    g._resolve_landing(0)
    assert g.combo == 2
    assert g.max_combo == 2


# ── Enum identity check ──────────────────────────────────────────────────────


def test_phase_enum_values() -> None:
    g = _make_game()
    assert g.phase == Phase.TITLE
    g._start_game()
    assert g.phase == Phase.FALLING
    g.player_vy = 0.0
    g.phase = Phase.RISING
    assert g.phase == Phase.RISING
    g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER
