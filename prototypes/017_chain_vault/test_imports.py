"""test_imports.py — Headless logic tests for CHAIN VAULT.

Tests chain mechanics, shatter logic, collision, heat, and game-over
without requiring a display.  Uses Game.__new__ to bypass pyxel.init.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/017_chain_vault")
from main import (  # noqa: E402
    BLUE,
    CHAIN_THRESHOLD,
    GRAVITY,
    GREEN,
    HEAT_DECAY,
    HEAT_OVERLOAD,
    JUMP_VEL,
    MOVE_SPEED,
    PLATFORM_COLORS,
    RED,
    SCREEN_H,
    SCREEN_W,
    FloatText,
    Game,
    Particle,
    Platform,
)

# ═══════════════════════════════════════════════════════════════════════════
# Dataclass / constant tests
# ═══════════════════════════════════════════════════════════════════════════


def test_constants() -> None:
    assert SCREEN_W == 256
    assert SCREEN_H == 256
    assert GRAVITY > 0
    assert JUMP_VEL < 0
    assert MOVE_SPEED > 0
    assert CHAIN_THRESHOLD == 3
    assert len(PLATFORM_COLORS) == 3
    assert RED in PLATFORM_COLORS
    assert BLUE in PLATFORM_COLORS
    assert GREEN in PLATFORM_COLORS
    assert HEAT_OVERLOAD == 85.0


def test_platform_dataclass() -> None:
    p = Platform(x=10, y=100.0, w=60, color=RED)
    assert p.x == 10
    assert p.y == 100.0
    assert p.w == 60
    assert p.color == RED
    assert p.alive is True
    assert p.crumbling == 0


def test_particle_dataclass() -> None:
    p = Particle(x=5.0, y=10.0, vx=1.0, vy=-2.0, life=20, color=BLUE)
    assert p.x == 5.0
    assert p.y == 10.0
    assert p.vx == 1.0
    assert p.vy == -2.0
    assert p.life == 20


def test_float_text_dataclass() -> None:
    ft = FloatText(x=50.0, y=30.0, text="+100", life=40, color=GREEN)
    assert ft.text == "+100"
    assert ft.life == 40


# ═══════════════════════════════════════════════════════════════════════════
# Game logic tests (headless — no pyxel.init)
# ═══════════════════════════════════════════════════════════════════════════


def _make_game() -> Game:
    """Create a Game instance without calling pyxel.init."""
    g = Game.__new__(Game)
    g.player_x = SCREEN_W / 2
    g.player_y = SCREEN_H - 80.0
    g.player_vy = 0.0
    g.player_on_ground = True
    g.platforms = []
    g.particles = []
    g.float_texts = []
    g.chain_color = None
    g.chain_count = 0
    g.heat = 0.0
    g.score = 0
    g.high_score = 0
    g.max_height = g.player_y
    g.combo_bonus = 1.0
    g.game_over = False
    g.game_over_timer = 0
    g.win_count = 0
    g.camera_y = 0.0
    g.shake_timer = 0
    g.shake_mag = 0
    return g


# ── Platform generation ─────────────────────────────────────────────────


def test_spawn_platform() -> None:
    g = _make_game()
    p = g._spawn_platform(120.0)
    assert isinstance(p, Platform)
    assert p.y == 120.0
    assert p.color in PLATFORM_COLORS
    assert 44 <= p.w <= 80
    assert p.alive is True


def test_generate_initial() -> None:
    g = _make_game()
    g._generate_initial()
    assert len(g.platforms) >= 10
    # Platforms should be in descending y order (higher on screen = smaller y)
    for p in g.platforms:
        assert p.y < SCREEN_H + 20
        assert p.alive is True


def test_cull_and_fill() -> None:
    g = _make_game()
    g._generate_initial()
    initial_count = len(g.platforms)
    g._cull_and_fill()
    assert len(g.platforms) >= initial_count  # should have added more above


# ── Physics & Movement ──────────────────────────────────────────────────


def test_gravity_applies() -> None:
    g = _make_game()
    g.player_vy = 0.0
    g.player_y = 100.0
    g.player_on_ground = False
    g._update_physics()
    assert g.player_vy == GRAVITY  # one frame of gravity
    assert g.player_y == 100.0 + GRAVITY


def test_horizontal_clamp() -> None:
    g = _make_game()
    g.player_x = -10.0
    g._update_physics()
    assert g.player_x == 0.0
    g.player_x = SCREEN_W + 10.0
    g._update_physics()
    assert g.player_x == SCREEN_W - 10.0  # PLAYER_W = 10


# ── Chain Logic ─────────────────────────────────────────────────────────


def test_chain_builds_on_same_color() -> None:
    g = _make_game()
    # First landing
    g._on_land(Platform(x=50, y=100, w=60, color=RED))
    assert g.chain_color == RED
    assert g.chain_count == 1
    # Second landing — same color
    g._on_land(Platform(x=50, y=80, w=60, color=RED))
    assert g.chain_color == RED
    assert g.chain_count == 2


def test_chain_resets_on_different_color() -> None:
    g = _make_game()
    g._on_land(Platform(x=50, y=100, w=60, color=RED))
    assert g.chain_count == 1
    g._on_land(Platform(x=50, y=80, w=60, color=BLUE))
    assert g.chain_color == BLUE
    assert g.chain_count == 1  # reset


def test_chain_resets_on_same_color_landing_second_time() -> None:
    """Verify that two same-color landings build to count 2, not reset."""
    g = _make_game()
    g._on_land(Platform(x=50, y=100, w=60, color=RED))
    g._on_land(Platform(x=50, y=80, w=60, color=RED))
    assert g.chain_count == 2
    assert g.chain_color == RED


# ── Shatter Logic ───────────────────────────────────────────────────────


def test_shatter_triggers_at_threshold() -> None:
    g = _make_game()
    # Add platforms of RED and BLUE
    p1 = Platform(x=50, y=100, w=60, color=RED)
    p2 = Platform(x=120, y=90, w=50, color=RED)
    p3 = Platform(x=200, y=80, w=40, color=BLUE)
    g.platforms = [p1, p2, p3]
    # Build chain
    g.chain_color = RED
    g.chain_count = CHAIN_THRESHOLD - 1  # 2
    # Landing on p1 (RED) should trigger shatter
    g._on_land(p1)
    # After shatter, RED platforms should be dead/crumbling
    # p1 crumbles (18 frames), p2 dead
    # Only crumbling (not dead) platforms count as alive; p1 is crumbling
    red_remaining = [p for p in g.platforms if p.color == RED and p.alive]
    assert len(red_remaining) == 1  # p1 is crumbling but still alive
    assert not p2.alive
    # Blue platform untouched
    assert p3.alive
    # Score awarded
    assert g.score > 0
    assert g.win_count == 1
    # Chain reset
    assert g.chain_count == 0
    assert g.chain_color is None


def test_shatter_launches_player() -> None:
    g = _make_game()
    p1 = Platform(x=50, y=100, w=60, color=RED)
    p2 = Platform(x=120, y=90, w=50, color=RED)
    g.platforms = [p1, p2]
    g.chain_color = RED
    g.chain_count = CHAIN_THRESHOLD - 1
    g.player_on_ground = True
    g._on_land(p1)
    assert g.player_vy < 0  # launched upward
    assert not g.player_on_ground


def test_shatter_generates_particles() -> None:
    g = _make_game()
    p1 = Platform(x=50, y=100, w=60, color=RED)
    p2 = Platform(x=120, y=90, w=50, color=RED)
    g.platforms = [p1, p2]
    g.chain_color = RED
    g.chain_count = CHAIN_THRESHOLD - 1
    g._on_land(p1)
    assert len(g.particles) > 0


def test_shatter_generates_floating_text() -> None:
    g = _make_game()
    p1 = Platform(x=50, y=100, w=60, color=RED)
    p2 = Platform(x=120, y=90, w=50, color=RED)
    g.platforms = [p1, p2]
    g.chain_color = RED
    g.chain_count = CHAIN_THRESHOLD - 1
    g._on_land(p1)
    assert len(g.float_texts) > 0


def test_shatter_causes_shake() -> None:
    g = _make_game()
    p1 = Platform(x=50, y=100, w=60, color=RED)
    p2 = Platform(x=120, y=90, w=50, color=RED)
    g.platforms = [p1, p2]
    g.chain_color = RED
    g.chain_count = CHAIN_THRESHOLD - 1
    g._on_land(p1)
    assert g.shake_timer > 0


def test_shatter_increases_heat() -> None:
    g = _make_game()
    p1 = Platform(x=50, y=100, w=60, color=RED)
    p2 = Platform(x=120, y=90, w=50, color=RED)
    g.platforms = [p1, p2]
    g.chain_color = RED
    g.chain_count = CHAIN_THRESHOLD - 1
    g._on_land(p1)
    assert g.heat > 0


def test_shatter_score_scales_with_chain() -> None:
    g = _make_game()
    p1 = Platform(x=50, y=100, w=60, color=RED)
    p2 = Platform(x=120, y=90, w=50, color=RED)
    g.platforms = [p1, p2]
    # Chain of exactly 3 (multiplier 1x)
    g.chain_color = RED
    g.chain_count = CHAIN_THRESHOLD - 1
    g._on_land(p1)
    score_3 = g.score
    # Reset and try chain of 4
    p3 = Platform(x=50, y=100, w=60, color=RED)
    p4 = Platform(x=120, y=90, w=50, color=RED)
    g.platforms = [p3, p4]
    g.score = 0
    g.chain_color = RED
    g.chain_count = CHAIN_THRESHOLD  # 3, one more landing makes 4
    g._on_land(p3)
    score_4 = g.score
    # Chain 4 should give higher score (multiplier 2x vs 1x)
    assert score_4 > score_3


# ── Heat System ─────────────────────────────────────────────────────────


def test_heat_decays() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat < 50.0
    assert g.heat >= 50.0 - HEAT_DECAY


def test_heat_never_negative() -> None:
    g = _make_game()
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_heat_clamped_at_100() -> None:
    g = _make_game()
    g.heat = 200.0
    # _update_heat doesn't clamp, but _trigger_shatter does
    # Let's test the shatter clamping
    g.heat = 99.0
    g.chain_color = RED
    g.chain_count = CHAIN_THRESHOLD - 1
    p1 = Platform(x=50, y=100, w=60, color=RED)
    p2 = Platform(x=120, y=90, w=50, color=RED)
    g.platforms = [p1, p2]
    g._on_land(p1)
    assert g.heat <= 100.0


# ── Crumbling Platforms ─────────────────────────────────────────────────


def test_crumbling_platform_eventually_dies() -> None:
    g = _make_game()
    p = Platform(x=50, y=100, w=60, color=RED, crumbling=5)
    g.platforms = [p]
    for _ in range(6):
        g._update_crumbling()
    assert not p.alive


def test_crumbling_generates_particles_on_death() -> None:
    g = _make_game()
    p = Platform(x=50, y=100, w=60, color=RED, crumbling=2)
    g.platforms = [p]
    g._update_crumbling()
    g._update_crumbling()  # should die and burst
    assert not p.alive
    assert len(g.particles) > 0


def test_on_land_ignores_crumbling() -> None:
    g = _make_game()
    p = Platform(x=50, y=100, w=60, color=RED, crumbling=10)
    g.chain_color = RED
    g.chain_count = 1
    g._on_land(p)
    # Chain should NOT increment (crumbling platform ignored)
    assert g.chain_count == 1
    assert g.chain_color == RED


# ── Particle System ─────────────────────────────────────────────────────


def test_particles_update() -> None:
    g = _make_game()
    g.particles = [
        Particle(x=50.0, y=50.0, vx=1.0, vy=-2.0, life=30, color=RED),
        Particle(x=60.0, y=60.0, vx=-1.0, vy=1.0, life=1, color=BLUE),
    ]
    g._update_particles()
    # life=1 particle is now life=0, removed by filter
    assert len(g.particles) == 1
    remaining = g.particles[0]
    assert remaining.life == 29
    assert remaining.x != 50.0 or remaining.y != 50.0  # has moved
    g._update_particles()
    assert len(g.particles) == 1
    assert remaining.life == 28


def test_float_texts_update() -> None:
    g = _make_game()
    g.float_texts = [
        FloatText(x=50.0, y=50.0, text="+100", life=1, color=RED),
        FloatText(x=60.0, y=60.0, text="COMBO", life=40, color=BLUE),
    ]
    g._update_float_texts()
    g._update_float_texts()
    assert len(g.float_texts) == 1  # first one removed
    remaining = g.float_texts[0]
    assert remaining.y < 60.0  # moved up


# ── Collision ───────────────────────────────────────────────────────────


def test_collision_lands_on_platform() -> None:
    g = _make_game()
    plat = Platform(x=50, y=100.0, w=100, color=RED)
    g.platforms = [plat]
    # Physics runs before collision in the game loop
    g.player_x = 90.0  # center of platform
    g.player_y = plat.y - 10.0
    g.player_vy = 5.0  # falling
    g.player_on_ground = False
    g.chain_color = None
    g.chain_count = 0
    g._update_physics()
    g._update_collision()
    assert g.player_on_ground is True
    assert g.player_vy == 0.0
    assert abs(g.player_y - (plat.y - 12.0)) < 0.01  # PLAYER_H = 12


def test_collision_passes_through_from_below() -> None:
    """Player moving upward through a platform should not land."""
    g = _make_game()
    plat = Platform(x=50, y=100.0, w=100, color=RED)
    g.platforms = [plat]
    g.player_x = 90.0
    g.player_y = plat.y + 5.0  # below platform
    g.player_vy = -5.0  # moving up
    g.player_on_ground = False
    g._update_collision()
    assert g.player_on_ground is False  # should pass through


def test_collision_misses_narrow_platform() -> None:
    g = _make_game()
    plat = Platform(x=50, y=100.0, w=30, color=RED)
    g.platforms = [plat]
    g.player_x = 90.0  # beyond platform edge (50+30=80)
    g.player_y = plat.y - 15.0
    g.player_vy = 3.0
    g.player_on_ground = False
    g._update_collision()
    assert g.player_on_ground is False


# ── Death & Game Over ───────────────────────────────────────────────────


def test_death_when_far_below_camera() -> None:
    g = _make_game()
    g.camera_y = 0.0
    g.player_y = SCREEN_H + 100.0  # far below
    g._check_death()
    assert g.game_over is True


def test_no_death_when_in_bounds() -> None:
    g = _make_game()
    g.camera_y = 0.0
    g.player_y = 100.0
    g._check_death()
    assert g.game_over is False


def test_high_score_updates_on_death() -> None:
    g = _make_game()
    g.score = 500
    g.high_score = 200
    g.camera_y = 0.0
    g.player_y = SCREEN_H + 100.0
    g._check_death()
    assert g.high_score == 500


def test_high_score_preserved_on_lower_score() -> None:
    g = _make_game()
    g.score = 100
    g.high_score = 500
    g.camera_y = 0.0
    g.player_y = SCREEN_H + 100.0
    g._check_death()
    assert g.high_score == 500  # unchanged


# ── Camera ──────────────────────────────────────────────────────────────


def test_camera_follows_player() -> None:
    g = _make_game()
    g.camera_y = 0.0
    g.player_y = -200.0  # far above (climbed high)
    g._update_camera()
    assert g.camera_y < 0  # camera moved up


def test_max_height_tracks_highest_point() -> None:
    g = _make_game()
    g.max_height = 100.0
    g.player_y = 50.0
    g._update_camera()
    assert g.max_height == 50.0
    g.player_y = 80.0
    g._update_camera()
    assert g.max_height == 50.0  # unchanged (80 > 50)


# ── Burst Particles ─────────────────────────────────────────────────────


def test_burst_particles_count() -> None:
    g = _make_game()
    plat = Platform(x=50, y=100.0, w=60, color=RED)
    before = len(g.particles)
    g._burst_particles(plat)
    after = len(g.particles)
    assert after - before == 8  # 8 particles per burst


def test_burst_particles_have_correct_color() -> None:
    g = _make_game()
    plat = Platform(x=50, y=100.0, w=60, color=BLUE)
    g._burst_particles(plat)
    for p in g.particles:
        assert p.color == BLUE


# ── Integration: full update flow ───────────────────────────────────────


def test_full_update_maintains_state() -> None:
    """Run a few frames of update without crashing."""
    g = _make_game()
    g._generate_initial()
    g.player_on_ground = True
    g.player_vy = 0.0
    for _ in range(10):
        g._update_physics()
        g._update_collision()
        g._update_camera()
        g._update_heat()
        g._update_particles()
        g._update_float_texts()
        g._update_crumbling()
        g._update_shake()
        g._cull_and_fill()
    # Should not crash and should maintain reasonable state
    assert g.player_y is not None
    assert len(g.platforms) > 0


if __name__ == "__main__":
    import sys as _sys

    # Discover and run all test_* functions
    tests = [
        (name, obj)
        for name, obj in sorted(globals().items())
        if name.startswith("test_") and callable(obj)
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {name}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed out of {len(tests)} tests")
    if failed > 0:
        _sys.exit(1)
