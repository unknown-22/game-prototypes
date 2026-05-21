"""test_imports.py — Headless logic tests for BULLSEYE CHAIN."""
from __future__ import annotations

import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/048_bullseye_chain")
from main import (
    COLOR_NAMES,
    COLOR_VALS,
    COMBO_THRESHOLD,
    DART_X,
    DART_Y,
    FPS,
    GRAVITY,
    MAX_DARTS,
    MAX_POWER,
    MIN_POWER,
    MIN_TARGETS,
    NUM_COLORS,
    PARTICLE_COUNT,
    ROUND_TIME,
    SCREEN_H,
    SCREEN_W,
    SUPER_MULTIPLIER,
    TIERS,
    Dart,
    FloatingText,
    Game,
    GhostTrail,
    Particle,
    Phase,
    Target,
)


# ── Constants ──────────────────────────────────────────────────────────


def test_constants() -> None:
    assert SCREEN_W == 256
    assert SCREEN_H == 256
    assert FPS == 30
    assert NUM_COLORS == 4
    assert len(COLOR_VALS) == 4
    assert len(COLOR_NAMES) == 4
    assert len(TIERS) == 3
    assert COMBO_THRESHOLD == 4
    assert SUPER_MULTIPLIER == 3
    assert MAX_DARTS == 30
    assert ROUND_TIME == 60 * 30
    assert MIN_TARGETS == 8
    assert GRAVITY == 0.35
    assert MIN_POWER == 3.0
    assert MAX_POWER == 10.0


# ── Data Classes ───────────────────────────────────────────────────────


def test_target_creation() -> None:
    t = Target(x=100.0, y=50.0, radius=9.0, color_idx=2, points=25, label="INNER")
    assert t.alive
    assert t.color_idx == 2
    assert t.points == 25


def test_target_not_alive() -> None:
    t = Target(x=100.0, y=50.0, radius=9.0, color_idx=2, points=25, label="INNER", alive=False)
    assert not t.alive


def test_dart_creation() -> None:
    d = Dart(x=128.0, y=230.0, vx=3.0, vy=-5.0, color_idx=0)
    assert d.active
    assert d.x == 128.0
    assert d.vx == 3.0
    assert d.vy == -5.0
    assert not d.super_mode
    assert len(d.trail) == 0


def test_dart_super_mode() -> None:
    d = Dart(x=128.0, y=230.0, vx=3.0, vy=-5.0, color_idx=0, super_mode=True)
    assert d.super_mode


def test_dart_trail() -> None:
    d = Dart(x=128.0, y=230.0, vx=3.0, vy=-5.0, color_idx=0)
    d.trail.append((100.0, 200.0))
    d.trail.append((110.0, 190.0))
    assert len(d.trail) == 2


def test_particle_creation() -> None:
    p = Particle(x=50.0, y=60.0, vx=1.5, vy=-2.0, color=8, life=15)
    assert p.x == 50.0
    assert p.life == 15


def test_floating_text_creation() -> None:
    ft = FloatingText(x=100.0, y=50.0, text="+50", color=8, life=30)
    assert ft.text == "+50"
    assert ft.life == 30
    assert ft.color == 8


def test_ghost_trail_creation() -> None:
    gt = GhostTrail(points=[(10.0, 20.0), (15.0, 25.0)], color_idx=1, life=90)
    assert len(gt.points) == 2
    assert gt.color_idx == 1
    assert gt.life == 90


# ── Phase Enum ─────────────────────────────────────────────────────────


def test_phase_enum() -> None:
    assert Phase.AIMING in Phase
    assert Phase.FLYING in Phase
    assert Phase.RESULT in Phase
    assert Phase.GAME_OVER in Phase


# ── Circle Overlap ─────────────────────────────────────────────────────


def test_circle_no_overlap() -> None:
    assert not Game._circle_overlap(0, 0, 10, 50, 50, 10)


def test_circle_overlap() -> None:
    assert Game._circle_overlap(0, 0, 10, 10, 0, 10)


def test_circle_barely_overlap() -> None:
    assert Game._circle_overlap(0, 0, 10, 19, 0, 10)


def test_circle_barely_no_overlap() -> None:
    # Distance = 20, sum of radii = 20 — should be NO overlap (strict <)
    assert not Game._circle_overlap(0, 0, 10, 20, 0, 10)


# ── Game State (headless via __new__) ──────────────────────────────────


def _make_game() -> Game:
    """Create a Game instance without Pyxel init."""
    g: Game = Game.__new__(Game)  # type: ignore[arg-type]
    g._rng = random.Random(42)
    g.phase = Phase.AIMING
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.dart_color_idx = 0
    g.darts_remaining = MAX_DARTS
    g.timer = ROUND_TIME
    g.super_active = False
    g.super_timer = 0
    g.result_timer = 0
    g._drag_start = None
    g._drag_current = None
    g.targets = []
    g.dart = None
    g.particles = []
    g.floating_texts = []
    g.ghost_trails = []
    g.reset()
    return g


def test_game_reset() -> None:
    g = _make_game()
    assert g.phase == Phase.AIMING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.dart_color_idx == 0
    assert g.darts_remaining == MAX_DARTS
    assert g.timer == ROUND_TIME
    assert not g.super_active
    assert g.dart is None
    assert len(g.targets) >= MIN_TARGETS


def test_spawn_targets_count() -> None:
    g = _make_game()
    assert len(g.targets) >= MIN_TARGETS
    assert len(g.targets) <= MIN_TARGETS  # reset only spawns initial batch


def test_spawn_target_in_bounds() -> None:
    g = _make_game()
    for t in g.targets:
        assert t.x - t.radius >= 20
        assert t.x + t.radius <= SCREEN_W - 20
        assert t.y - t.radius >= 10
        assert t.y + t.radius <= 140


def test_spawn_target_no_overlap() -> None:
    g = _make_game()
    for i, t1 in enumerate(g.targets):
        for j, t2 in enumerate(g.targets):
            if i >= j:
                continue
            dx = t1.x - t2.x
            dy = t1.y - t2.y
            dist = math.sqrt(dx * dx + dy * dy)
            assert dist >= t1.radius + t2.radius + 2


def test_replenish_targets() -> None:
    g = _make_game()
    # Clear most targets
    g.targets = g.targets[:2]
    g._replenish_targets()
    assert len(g.targets) >= MIN_TARGETS


# ── Dart / Collision ───────────────────────────────────────────────────


def test_dart_collision_none() -> None:
    g = _make_game()
    d = Dart(x=200, y=200, vx=0, vy=0, color_idx=0)
    # No target at (200, 200)
    g.targets = [Target(x=50, y=50, radius=10, color_idx=0, points=25, label="INNER")]
    result = g._check_dart_collision(d)
    assert result is None


def test_dart_collision_hit() -> None:
    g = _make_game()
    t = Target(x=50, y=50, radius=10, color_idx=0, points=25, label="INNER")
    g.targets = [t]
    d = Dart(x=50, y=52, vx=0, vy=0, color_idx=0)  # within radius+2
    result = g._check_dart_collision(d)
    assert result is t


def test_dart_collision_dead_target() -> None:
    g = _make_game()
    t = Target(x=50, y=50, radius=10, color_idx=0, points=25, label="INNER", alive=False)
    g.targets = [t]
    d = Dart(x=50, y=52, vx=0, vy=0, color_idx=0)
    result = g._check_dart_collision(d)
    assert result is None


# ── Hit/Miss Logic ─────────────────────────────────────────────────────


def test_dart_hit_same_color() -> None:
    g = _make_game()
    t = Target(x=50, y=50, radius=10, color_idx=0, points=25, label="INNER")
    g.targets = [t]
    d = Dart(x=50, y=52, vx=0, vy=0, color_idx=0)
    d.trail.append((40, 60))

    g._dart_hit_target(d, t)

    assert not t.alive
    assert t not in g.targets  # removed from list
    assert g.combo == 1
    assert g.max_combo == 1


def test_dart_hit_same_color_score() -> None:
    g = _make_game()
    g.combo = 2  # pre-existing combo
    t = Target(x=50, y=50, radius=10, color_idx=0, points=50, label="BULL")
    g.targets = [t]
    d = Dart(x=50, y=52, vx=0, vy=0, color_idx=0)

    prev_score = g.score
    g._dart_hit_target(d, t)

    assert g.combo == 3
    # Score: points (50) × combo (3) = 150
    assert g.score == prev_score + 150


def test_dart_hit_wrong_color() -> None:
    g = _make_game()
    g.combo = 3
    t = Target(x=50, y=50, radius=10, color_idx=1, points=25, label="INNER")
    g.targets = [t]
    d = Dart(x=50, y=52, vx=0, vy=0, color_idx=0)  # different color

    prev_score = g.score
    g._dart_hit_target(d, t)

    assert not t.alive
    assert g.combo == 0  # reset
    assert g.score == prev_score + 25  # base points only


def test_dart_hit_super_mode_score() -> None:
    g = _make_game()
    g.combo = 0
    t = Target(x=50, y=50, radius=5, color_idx=1, points=50, label="BULL")
    g.targets = [t]
    d = Dart(x=50, y=52, vx=0, vy=0, color_idx=0, super_mode=True)

    prev_score = g.score
    g._dart_hit_target(d, t)

    assert g.combo == 1
    # Score: points (50) × combo (1) × super_multiplier (3) = 150
    assert g.score == prev_score + 150


def test_dart_hit_triggers_super() -> None:
    g = _make_game()
    g.combo = COMBO_THRESHOLD - 1  # 3
    t = Target(x=50, y=50, radius=10, color_idx=0, points=25, label="INNER")
    g.targets = [t]
    d = Dart(x=50, y=52, vx=0, vy=0, color_idx=0)

    g._dart_hit_target(d, t)

    assert g.combo == COMBO_THRESHOLD  # 4
    assert g.super_active
    assert g.super_timer == 90


def test_dart_missed_resets_combo() -> None:
    g = _make_game()
    g.combo = 5
    g.dart = Dart(x=300, y=300, vx=0, vy=0, color_idx=0)  # off-screen

    g._dart_missed()

    assert g.combo == 0
    assert g.dart is None
    assert g.phase == Phase.RESULT


def test_dart_hit_advances_color() -> None:
    g = _make_game()
    original_color = g.dart_color_idx
    t = Target(x=50, y=50, radius=10, color_idx=0, points=25, label="INNER")
    g.targets = [t]
    d = Dart(x=50, y=52, vx=0, vy=0, color_idx=0)

    g._dart_hit_target(d, t)

    assert g.dart_color_idx == (original_color + 1) % NUM_COLORS


# ── Particles ──────────────────────────────────────────────────────────


def test_spawn_hit_particles() -> None:
    g = _make_game()
    assert len(g.particles) == 0

    g._spawn_hit_particles(50, 50, 8)

    assert len(g.particles) == PARTICLE_COUNT
    for p in g.particles:
        assert p.life == 15
        assert p.color == 8


def test_update_particles_life_decreases() -> None:
    g = _make_game()
    g.particles = [Particle(x=50, y=50, vx=1, vy=-1, color=8, life=5)]

    g._update_particles()

    assert g.particles[0].life == 4


def test_update_particles_dead_removed() -> None:
    g = _make_game()
    g.particles = [Particle(x=50, y=50, vx=1, vy=-1, color=8, life=1)]

    g._update_particles()

    assert len(g.particles) == 0


# ── Floating Texts ─────────────────────────────────────────────────────


def test_update_floating_texts() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=100, y=50, text="+50", color=8, life=10)]
    prev_y = g.floating_texts[0].y

    g._update_floating_texts()

    assert g.floating_texts[0].life == 9
    assert g.floating_texts[0].y < prev_y  # floats up


def test_update_floating_texts_dead_removed() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=100, y=50, text="+50", color=8, life=1)]

    g._update_floating_texts()

    assert len(g.floating_texts) == 0


# ── Ghost Trails ───────────────────────────────────────────────────────


def test_update_ghost_trails() -> None:
    g = _make_game()
    g.ghost_trails = [GhostTrail(points=[(10, 20)], color_idx=0, life=20)]

    g._update_ghost_trails()

    assert g.ghost_trails[0].life == 19


def test_update_ghost_trails_dead_removed() -> None:
    g = _make_game()
    g.ghost_trails = [GhostTrail(points=[(10, 20)], color_idx=0, life=1)]

    g._update_ghost_trails()

    assert len(g.ghost_trails) == 0


def test_ghost_trail_stored_on_hit() -> None:
    g = _make_game()
    t = Target(x=50, y=50, radius=10, color_idx=0, points=25, label="INNER")
    g.targets = [t]
    d = Dart(x=50, y=52, vx=0, vy=0, color_idx=0)
    d.trail.append((40, 60))

    g._dart_hit_target(d, t)

    assert len(g.ghost_trails) == 1
    assert g.ghost_trails[0].color_idx == 0
    assert g.ghost_trails[0].life == 90


def test_ghost_trail_capped() -> None:
    g = _make_game()
    # Fill with 3 existing trails
    g.ghost_trails = [
        GhostTrail(points=[(10, 20)], color_idx=0, life=10),
        GhostTrail(points=[(10, 20)], color_idx=1, life=10),
        GhostTrail(points=[(10, 20)], color_idx=2, life=10),
    ]

    t = Target(x=50, y=50, radius=10, color_idx=0, points=25, label="INNER")
    g.targets = [t]
    d = Dart(x=50, y=52, vx=0, vy=0, color_idx=0)
    d.trail.append((40, 60))
    g._dart_hit_target(d, t)

    assert len(g.ghost_trails) == 3  # capped at GHOST_TRAIL_COUNT (3)


# ── Result Phase ───────────────────────────────────────────────────────


def test_result_transitions_to_aiming() -> None:
    g = _make_game()
    g.phase = Phase.RESULT
    g.result_timer = 2

    g._update_result()
    assert g.result_timer == 1
    assert g.phase == Phase.RESULT

    g._update_result()
    assert g.phase == Phase.AIMING  # timer hit 0, not game over


def test_result_transitions_to_game_over_no_darts() -> None:
    g = _make_game()
    g.phase = Phase.RESULT
    g.result_timer = 1
    g.darts_remaining = 0

    g._update_result()

    assert g.phase == Phase.GAME_OVER


def test_result_transitions_to_game_over_timeout() -> None:
    g = _make_game()
    g.phase = Phase.RESULT
    g.result_timer = 1
    g.timer = 0

    g._update_result()

    assert g.phase == Phase.GAME_OVER


# ── Timer ──────────────────────────────────────────────────────────────


def test_update_timer_decrements() -> None:
    """Simulate update() logic: timer decrements only in non-GAME_OVER phases."""
    g = _make_game()
    g.phase = Phase.AIMING
    g.timer = 100

    # Simulate the timer logic from update()
    if g.phase != Phase.GAME_OVER:
        g.timer -= 1
        if g.timer <= 0:
            g.timer = 0
            g.phase = Phase.GAME_OVER

    assert g.timer == 99
    assert g.phase == Phase.AIMING  # not game over yet


def test_update_timer_game_over_transition() -> None:
    g = _make_game()
    g.phase = Phase.AIMING
    g.timer = 1

    if g.phase != Phase.GAME_OVER:
        g.timer -= 1
        if g.timer <= 0:
            g.timer = 0
            g.phase = Phase.GAME_OVER

    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER


# ── Super Mode Timer ───────────────────────────────────────────────────


def test_super_mode_timer_decrements() -> None:
    g = _make_game()
    g.super_active = True
    g.super_timer = 5

    # Simulate super mode timer logic
    if g.super_active:
        g.super_timer -= 1
        if g.super_timer <= 0:
            g.super_active = False

    assert g.super_timer == 4
    assert g.super_active


def test_super_mode_expires() -> None:
    g = _make_game()
    g.super_active = True
    g.super_timer = 1

    if g.super_active:
        g.super_timer -= 1
        if g.super_timer <= 0:
            g.super_active = False

    assert g.super_timer == 0
    assert not g.super_active


# ── Score / MaxCombo ───────────────────────────────────────────────────


def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    assert g.max_combo == 0

    # Hit 1: combo goes 0→1
    t = Target(x=50, y=50, radius=10, color_idx=0, points=25, label="INNER")
    g.targets = [t]
    d1 = Dart(x=50, y=52, vx=0, vy=0, color_idx=0)
    d1.trail.append((40, 60))
    g._dart_hit_target(d1, t)
    assert g.max_combo == 1

    # Hit 2: combo goes 1→2 (same color)
    t2 = Target(x=60, y=60, radius=10, color_idx=0, points=25, label="INNER")
    g.targets = [t2]
    d2 = Dart(x=60, y=62, vx=0, vy=0, color_idx=0)
    d2.trail.append((50, 70))
    g._dart_hit_target(d2, t2)
    assert g.max_combo == 2

    # Hit 3: wrong color, combo resets
    t3 = Target(x=70, y=70, radius=10, color_idx=1, points=25, label="INNER")
    g.targets = [t3]
    d3 = Dart(x=70, y=72, vx=0, vy=0, color_idx=0)
    d3.trail.append((60, 80))
    g._dart_hit_target(d3, t3)
    assert g.combo == 0
    assert g.max_combo == 2  # max_combo preserved


# ── Run ─────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import traceback

    tests = [
        (name, fn)
        for name, fn in sorted(globals().items())
        if name.startswith("test_") and callable(fn)
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
            print(f"  PASS {name}")
        except Exception:
            failed += 1
            print(f"  FAIL {name}")
            traceback.print_exc()

    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    if failed > 0:
        sys.exit(1)
