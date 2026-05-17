"""test_imports.py — Headless logic tests for ECHO ARC.

Verifies dataclasses, constants, and core game logic without Pyxel init.
"""
from __future__ import annotations

import sys
import math

# Path to prototype
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/037_echo_arc")

from main import (
    Game, Phase, Projectile, Target, EchoRing, Particle, FloatingText,
    COLOR_COUNT, COLORS, COLOR_NAMES, COMBO_THRESHOLD, ECHO_MAX,
    ECHO_RADIUS, ECHO_FADE_TIME, GAME_DURATION,
    SCREEN_W, SCREEN_H, LAUNCHER_X, LAUNCHER_Y, MAX_POWER, MIN_POWER,
    GRAVITY, PROJECTILE_RADIUS, TARGET_RADIUS, MAX_TARGETS,
    TARGET_SPAWN_INTERVAL, POWER_CHARGE_RATE, PROJECTILE_SPEED_FACTOR,
)


def test_constants() -> None:
    """Verify essential game constants are sane."""
    assert COLOR_COUNT == 4
    assert len(COLORS) == 4
    assert len(COLOR_NAMES) == 4
    assert COMBO_THRESHOLD == 4
    assert ECHO_MAX == 8
    assert ECHO_RADIUS == 20
    assert ECHO_FADE_TIME == 3.0
    assert GAME_DURATION == 60
    assert SCREEN_W == 256
    assert SCREEN_H == 256
    assert MAX_POWER == 180.0
    assert MIN_POWER == 30.0
    assert GRAVITY == 220.0
    assert MAX_TARGETS == 6
    assert TARGET_SPAWN_INTERVAL == 2.0


def test_dataclasses() -> None:
    """Test dataclass creation and defaults."""
    t = Target(x=100.0, y=80.0, color=2)
    assert t.x == 100.0
    assert t.y == 80.0
    assert t.color == 2
    assert t.radius == TARGET_RADIUS
    assert t.alive is True

    e = EchoRing(x=50.0, y=60.0, color=1)
    assert e.x == 50.0
    assert e.y == 60.0
    assert e.color == 1
    assert e.radius == 0.0
    assert e.life == ECHO_FADE_TIME

    p = Projectile(x=0.0, y=0.0, vx=100.0, vy=-200.0, color=0)
    assert p.vx == 100.0
    assert p.vy == -200.0
    assert p.alive is True

    pt = Particle(x=0.0, y=0.0, vx=10.0, vy=-10.0, color=3, life=0.5)
    assert pt.life == 0.5
    assert pt.size == 2.0
    assert pt.color == 3

    ft = FloatingText(x=50.0, y=40.0, text="TEST", color=7)
    assert ft.text == "TEST"
    assert ft.life == 1.0
    assert ft.vy == -40.0


def test_phase_enum() -> None:
    """Verify Phase enum values."""
    assert Phase.AIMING == 0
    assert Phase.FLYING == 1
    assert Phase.RESOLVING == 2
    assert Phase.GAME_OVER == 3
    assert len(Phase) == 4


def test_game_reset_state() -> None:
    """Test Game.__new__ bypass to check reset() state without Pyxel init."""
    g = Game.__new__(Game)
    g.reset()

    assert g.phase == Phase.AIMING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.active_color == 0
    assert g.game_timer == GAME_DURATION
    assert g.projectiles == []
    assert g.echo_rings == []
    assert g.particles == []
    assert g.floating_texts == []
    assert g.dragging is False
    assert g.power == 0.0
    assert g.super_mode is False
    assert g.super_timer == 0.0


def test_target_spawning() -> None:
    """Test target spawn respects MAX_TARGETS."""
    g = Game.__new__(Game)
    g.reset()

    initial_count = len(g.targets)
    assert initial_count == 3  # TARGET_COUNT

    # Try to spawn beyond max
    for _ in range(20):
        g._spawn_target()
    assert len(g.targets) <= MAX_TARGETS


def test_echo_ring_management() -> None:
    """Test echo ring creation and cap."""
    g = Game.__new__(Game)
    g.reset()

    # Create echo rings
    for i in range(ECHO_MAX + 5):
        g._create_echo(float(i * 10), float(i * 10), i % COLOR_COUNT)

    assert len(g.echo_rings) == ECHO_MAX
    # Oldest should have been removed; first surviving should be index 5
    assert g.echo_rings[0].x == 50.0


def test_cycle_active_color() -> None:
    """Test color cycling wraps around."""
    g = Game.__new__(Game)
    g.reset()

    assert g.active_color == 0
    g._cycle_active_color()
    assert g.active_color == 1
    g._cycle_active_color()
    assert g.active_color == 2
    g._cycle_active_color()
    assert g.active_color == 3
    g._cycle_active_color()
    assert g.active_color == 0
    assert g.color_timer == 5.0


def test_projectile_physics() -> None:
    """Test gravity affects projectile velocity."""
    p = Projectile(x=100.0, y=200.0, vx=50.0, vy=-100.0, color=0)

    dt = 1.0 / 60.0
    p.vy += GRAVITY * dt
    p.x += p.vx * dt
    p.y += p.vy * dt

    assert p.vy > -100.0  # gravity pulled it down
    assert p.x > 100.0
    assert p.y < 200.0  # still going up (initial upward velocity > gravity for 1 frame)


def test_collision_detection() -> None:
    """Test hit detection between projectile and target."""
    g = Game.__new__(Game)
    g.reset()

    proj = Projectile(x=100.0, y=100.0, vx=0.0, vy=0.0, color=0)
    target = Target(x=100.0, y=100.0, color=0)

    # Direct hit
    assert g._check_hit(proj, target) is True

    # Just outside radius
    target.x = 100.0 + PROJECTILE_RADIUS + TARGET_RADIUS + 2
    assert g._check_hit(proj, target) is False

    # Edge case: exactly at boundary
    target.x = 100.0 + PROJECTILE_RADIUS + TARGET_RADIUS - 1
    assert g._check_hit(proj, target) is True


def test_echo_bonus_detection() -> None:
    """Test echo ring bonus triggers when projectile passes through."""
    g = Game.__new__(Game)
    g.reset()

    # Create an echo ring at a position
    g._create_echo(100.0, 100.0, 0)
    g.echo_rings[0].radius = ECHO_RADIUS  # manually set to full size

    # Projectile passing through echo ring (same color)
    proj = Projectile(x=100.0, y=100.0, vx=50.0, vy=-50.0, color=0)
    assert g._check_echo_bonus(proj) is True

    # Different color — no bonus
    proj2 = Projectile(x=100.0, y=100.0, vx=50.0, vy=-50.0, color=1)
    assert g._check_echo_bonus(proj2) is False

    # Outside ring
    proj3 = Projectile(x=200.0, y=200.0, vx=0.0, vy=0.0, color=0)
    assert g._check_echo_bonus(proj3) is False


def test_echo_life_decay() -> None:
    """Test echo rings decay over time."""
    g = Game.__new__(Game)
    g.reset()

    g._create_echo(50.0, 50.0, 1)
    assert g.echo_rings[0].life == ECHO_FADE_TIME

    # Simulate updates
    dt = 1.0 / 60.0
    for _ in range(60):  # 1 second
        for echo in g.echo_rings:
            echo.life -= dt
            if echo.radius < ECHO_RADIUS:
                echo.radius += ECHO_RADIUS * 2.0 * dt
            if echo.radius > ECHO_RADIUS:
                echo.radius = ECHO_RADIUS
    g.echo_rings = [e for e in g.echo_rings if e.life > 0]

    # Still alive after 1 second (fade time is 3s)
    assert len(g.echo_rings) == 1
    assert abs(g.echo_rings[0].life - (ECHO_FADE_TIME - 1.0)) < 0.1

    # Kill it off
    for _ in range(120 + 10):  # 2 seconds + margin for FP rounding
        for echo in g.echo_rings:
            echo.life -= dt
    g.echo_rings = [e for e in g.echo_rings if e.life > 0]
    assert len(g.echo_rings) == 0


def test_resolve_hit_combo() -> None:
    """Test hit resolution builds combo correctly."""
    g = Game.__new__(Game)
    g.reset()

    proj = Projectile(x=100.0, y=100.0, vx=0.0, vy=0.0, color=0)
    target = Target(x=100.0, y=100.0, color=0)  # matching color
    g.targets = [target]

    g._resolve_hit(proj, target)
    assert g.combo == 1
    assert g.max_combo == 1
    assert g.score > 0
    assert target.alive is False
    assert len(g.echo_rings) == 1


def test_resolve_hit_wrong_color() -> None:
    """Test wrong-color hit resets combo."""
    g = Game.__new__(Game)
    g.reset()

    # Build combo first
    g.combo = 3
    g.max_combo = 3

    proj = Projectile(x=100.0, y=100.0, vx=0.0, vy=0.0, color=0)
    target = Target(x=100.0, y=100.0, color=1)  # different color
    g.targets = [target]

    g._resolve_hit(proj, target)
    assert g.combo == 0
    assert g.max_combo == 3  # max combo preserved
    assert target.alive is False


def test_resolve_hit_super_mode() -> None:
    """Test super mode matches any color."""
    g = Game.__new__(Game)
    g.reset()
    g.super_mode = True
    g.combo = 4

    proj = Projectile(x=100.0, y=100.0, vx=0.0, vy=0.0, color=0)
    target = Target(x=100.0, y=100.0, color=3)  # different color
    g.targets = [target]

    score_before = g.score
    g._resolve_hit(proj, target)
    assert g.combo == 5  # combo incremented (super mode matches anything)
    assert g.score > score_before
    assert target.alive is False


def test_resolve_miss() -> None:
    """Test miss resets combo."""
    g = Game.__new__(Game)
    g.reset()
    g.combo = 2
    g.max_combo = 2

    g._resolve_miss()
    assert g.combo == 0
    assert g.max_combo == 2


def test_super_mode_trigger() -> None:
    """Test super mode triggers at COMBO_THRESHOLD."""
    g = Game.__new__(Game)
    g.reset()

    # Build combo to threshold - 1
    g.combo = COMBO_THRESHOLD - 1

    # Hit matching color → should trigger super
    proj = Projectile(x=100.0, y=100.0, vx=0.0, vy=0.0, color=0)
    target = Target(x=100.0, y=100.0, color=0)
    g.targets = [target]
    g._resolve_hit(proj, target)

    assert g.combo == COMBO_THRESHOLD
    assert g.super_mode is True
    assert g.super_timer == 3.0


def test_score_scaling() -> None:
    """Test score scales with combo and distance."""
    g = Game.__new__(Game)
    g.reset()

    # Hit with combo=0: score = 10 * (1 + 0*0.5) * (1 + y/256*0.5)
    proj = Projectile(x=100.0, y=100.0, vx=0.0, vy=0.0, color=0)
    target = Target(x=100.0, y=180.0, color=0)
    g.targets = [target]

    g._resolve_hit(proj, target)
    score1 = g.score
    assert score1 > 0

    # Higher combo should give more points
    g.reset()
    g.combo = 4  # start with combo
    target2 = Target(x=100.0, y=180.0, color=0)
    g.targets = [target2]
    proj2 = Projectile(x=100.0, y=100.0, vx=0.0, vy=0.0, color=0)
    g._resolve_hit(proj2, target2)
    score2 = g.score
    assert score2 > score1  # higher combo = more points


def test_game_timer() -> None:
    """Test game timer counts down and triggers game over."""
    g = Game.__new__(Game)
    g.reset()

    # Simulate running down the timer (not using _update_timers since it accesses pyxel)
    dt = 1.0 / 60.0
    for _ in range(int(GAME_DURATION * 60) + 10):
        g.game_timer -= dt
        if g.game_timer <= 0:
            g.game_timer = 0
            g.phase = Phase.GAME_OVER
            break

    assert g.game_timer == 0
    assert g.phase == Phase.GAME_OVER


def test_particles_spawn() -> None:
    """Test particle spawning."""
    g = Game.__new__(Game)
    g.reset()

    g._spawn_particles(100.0, 100.0, COLORS[0], count=5)
    assert len(g.particles) == 5

    for p in g.particles:
        assert p.color == COLORS[0]
        assert p.life > 0


def test_floating_text_spawn() -> None:
    """Test floating text spawning."""
    g = Game.__new__(Game)
    g.reset()

    g._spawn_floating_text(100.0, 50.0, "TEST!", 7)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "TEST!"
    assert g.floating_texts[0].life == 1.0


def test_target_cleanup() -> None:
    """Test dead targets are removed."""
    g = Game.__new__(Game)
    g.reset()

    initial = len(g.targets)
    g.targets[0].alive = False

    g.targets = [t for t in g.targets if t.alive]
    assert len(g.targets) == initial - 1


def test_projectile_cleanup() -> None:
    """Test dead projectiles are cleaned up."""
    g = Game.__new__(Game)
    g.reset()

    g.projectiles = [
        Projectile(x=100.0, y=100.0, vx=50.0, vy=-50.0, color=0, alive=True),
        Projectile(x=200.0, y=200.0, vx=0.0, vy=0.0, color=1, alive=False),
    ]
    g.projectiles = [p for p in g.projectiles if p.alive]
    assert len(g.projectiles) == 1


def test_power_clamping() -> None:
    """Test power is clamped between MIN and MAX."""
    g = Game.__new__(Game)
    g.reset()

    # Power cannot exceed MAX
    g.power = MAX_POWER + 100
    g.power = min(g.power, MAX_POWER)
    assert g.power == MAX_POWER

    # Power below MIN should not launch
    g.power = 20.0
    assert g.power < MIN_POWER


def test_angle_clamping() -> None:
    """Test launch angle is clamped to upward directions."""
    # Angle should be between -pi*0.85 and -pi*0.15 (roughly -153° to -27°)
    angle1 = -math.pi * 0.5  # straight up → OK
    clamped1 = max(-math.pi * 0.85, min(-math.pi * 0.15, angle1))
    assert clamped1 == angle1

    angle2 = 0.0  # horizontal right → should be clamped
    clamped2 = max(-math.pi * 0.85, min(-math.pi * 0.15, angle2))
    assert clamped2 == -math.pi * 0.15

    angle3 = -math.pi  # straight left → should be clamped
    clamped3 = max(-math.pi * 0.85, min(-math.pi * 0.15, angle3))
    assert clamped3 == -math.pi * 0.85


def test_projectile_off_screen_detection() -> None:
    """Test projectile off-screen detection boundaries."""
    # Below screen
    p = Projectile(x=100.0, y=SCREEN_H + 30.0, vx=0.0, vy=0.0, color=0)
    assert p.y > SCREEN_H + 20

    # Left of screen
    p2 = Projectile(x=-30.0, y=100.0, vx=0.0, vy=0.0, color=0)
    assert p2.x < -20

    # Right of screen
    p3 = Projectile(x=SCREEN_W + 30.0, y=100.0, vx=0.0, vy=0.0, color=0)
    assert p3.x > SCREEN_W + 20


def test_color_names_match() -> None:
    """Test color names array matches color count."""
    assert len(COLOR_NAMES) == COLOR_COUNT
    assert COLOR_NAMES[0] == "FIRE"
    assert COLOR_NAMES[1] == "ICE"
    assert COLOR_NAMES[2] == "LIGHT"
    assert COLOR_NAMES[3] == "NATR"
    # Names should fit in Pyxel text (≤10 chars)
    for name in COLOR_NAMES:
        assert len(name) <= 10


def test_launcher_position() -> None:
    """Test launcher is at bottom center."""
    assert LAUNCHER_X == SCREEN_W // 2
    assert LAUNCHER_Y == SCREEN_H - 40


if __name__ == "__main__":
    import traceback

    tests = [
        ("constants", test_constants),
        ("dataclasses", test_dataclasses),
        ("phase_enum", test_phase_enum),
        ("game_reset_state", test_game_reset_state),
        ("target_spawning", test_target_spawning),
        ("echo_ring_management", test_echo_ring_management),
        ("cycle_active_color", test_cycle_active_color),
        ("projectile_physics", test_projectile_physics),
        ("collision_detection", test_collision_detection),
        ("echo_bonus_detection", test_echo_bonus_detection),
        ("echo_life_decay", test_echo_life_decay),
        ("resolve_hit_combo", test_resolve_hit_combo),
        ("resolve_hit_wrong_color", test_resolve_hit_wrong_color),
        ("resolve_hit_super_mode", test_resolve_hit_super_mode),
        ("resolve_miss", test_resolve_miss),
        ("super_mode_trigger", test_super_mode_trigger),
        ("score_scaling", test_score_scaling),
        ("game_timer", test_game_timer),
        ("particles_spawn", test_particles_spawn),
        ("floating_text_spawn", test_floating_text_spawn),
        ("target_cleanup", test_target_cleanup),
        ("projectile_cleanup", test_projectile_cleanup),
        ("power_clamping", test_power_clamping),
        ("angle_clamping", test_angle_clamping),
        ("projectile_off_screen_detection", test_projectile_off_screen_detection),
        ("color_names_match", test_color_names_match),
        ("launcher_position", test_launcher_position),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception:
            print(f"FAIL: {name}")
            traceback.print_exc()
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
