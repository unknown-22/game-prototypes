"""test_imports.py — Headless logic tests for CHROMA DRIVE.

Tests core mechanics without requiring a display.
Run: uv run python prototypes/030_chroma_drive/test_imports.py
"""

from __future__ import annotations

import math
import sys

# Add prototype dir to path for import
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/030_chroma_drive")

# Prevent pyxel.init from being called during import
_orig_init = None
try:
    import pyxel

    _orig_init = pyxel.init
    pyxel.init = lambda *a, **kw: None  # type: ignore[method-assign]
    pyxel.run = lambda *a, **kw: None  # type: ignore[method-assign]
except ImportError:
    pass

from main import (  # noqa: E402
    Ball,
    COLORS,
    COLOR_COUNT,
    FRICTION,
    Game,
    Hole,
    HOLE_RADIUS,
    MAX_POWER,
    MIN_SPEED,
    NUM_HOLES,
    NUM_PUTTS,
    Particle,
    Phase,
    SCREEN_H,
    SCREEN_W,
    TEE_X,
    TEE_Y,
)

# Restore pyxel.init
if _orig_init is not None:
    pyxel.init = _orig_init  # type: ignore[method-assign]

PASS = 0
FAIL = 0


def check(condition: bool, msg: str) -> None:
    """Assert and track results."""
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL: {msg}")


# ── Dataclass Tests ──


def test_hole_dataclass() -> None:
    """Hole dataclass construction and attributes."""
    h = Hole(x=50.0, y=30.0, color=8)
    check(h.x == 50.0, "Hole.x")
    check(h.y == 30.0, "Hole.y")
    check(h.color == 8, "Hole.color")


def test_ball_dataclass() -> None:
    """Ball dataclass construction and defaults."""
    b = Ball(x=100.0, y=200.0, color=6)
    check(b.x == 100.0, "Ball.x")
    check(b.y == 200.0, "Ball.y")
    check(b.vx == 0.0, "Ball.vx default")
    check(b.vy == 0.0, "Ball.vy default")
    check(b.color == 6, "Ball.color")
    check(b.active is True, "Ball.active default")


def test_particle_dataclass() -> None:
    """Particle dataclass construction."""
    p = Particle(x=10.0, y=20.0, vx=1.0, vy=-0.5, life=10, color=8)
    check(p.x == 10.0, "Particle.x")
    check(p.y == 20.0, "Particle.y")
    check(p.vx == 1.0, "Particle.vx")
    check(p.vy == -0.5, "Particle.vy")
    check(p.life == 10, "Particle.life")
    check(p.color == 8, "Particle.color")


# ── Config Tests ──


def test_config_values() -> None:
    """Verify game constants are reasonable."""
    check(SCREEN_W == 256, "SCREEN_W")
    check(SCREEN_H == 256, "SCREEN_H")
    check(NUM_HOLES == 6, "NUM_HOLES")
    check(NUM_PUTTS == 9, "NUM_PUTTS")
    check(HOLE_RADIUS == 7, "HOLE_RADIUS")
    check(MAX_POWER == 9.0, "MAX_POWER")
    check(0 < FRICTION < 1, "FRICTION in (0,1)")
    check(MIN_SPEED > 0, "MIN_SPEED > 0")
    check(COLOR_COUNT == 4, "COLOR_COUNT")
    check(len(COLORS) == 4, "COLORS length")


# ── Game State Tests ──


def test_game_construction() -> None:
    """Game object can be constructed without calling pyxel.init."""
    g = Game.__new__(Game)
    check(g is not None, "Game.__new__ works")


def test_game_reset_state() -> None:
    """Game.reset() initializes all fields."""
    g = Game.__new__(Game)
    g.reset()
    check(g.phase == Phase.AIM, "reset: phase=AIM")
    check(g.score == 0, "reset: score=0")
    check(g.combo == 0, "reset: combo=0")
    check(g.putts_left == NUM_PUTTS, "reset: putts_left")
    check(g.ball_color in COLORS, "reset: ball_color in COLORS")
    check(g.ball is not None, "reset: ball not None")
    check(g.ball.x == TEE_X, "reset: ball at tee X")
    check(g.ball.y == TEE_Y, "reset: ball at tee Y")
    check(g.ball.color == g.ball_color, "reset: ball.color == ball_color")
    check(len(g.holes) == NUM_HOLES, "reset: hole count")
    check(g.particles == [], "reset: particles empty")
    check(g.score_pop == 0, "reset: score_pop=0")
    check(g.best_combo == 0, "reset: best_combo=0")


# ── Hole Spawning Tests ──


def test_holes_in_bounds() -> None:
    """All spawned holes are within screen bounds."""
    g = Game.__new__(Game)
    g.reset()
    for h in g.holes:
        check(0 < h.x < SCREEN_W, f"hole x={h.x} in bounds")
        check(0 < h.y < SCREEN_H, f"hole y={h.y} in bounds")
        check(h.color in COLORS, f"hole color={h.color} valid")


def test_holes_not_overlapping() -> None:
    """Spawned holes don't overlap."""
    g = Game.__new__(Game)
    g.reset()
    for i, h1 in enumerate(g.holes):
        for j, h2 in enumerate(g.holes):
            if i < j:
                dist = math.hypot(h1.x - h2.x, h1.y - h2.y)
                check(dist >= HOLE_RADIUS * 3 - 1, f"holes {i},{j} not overlapping (dist={dist:.1f})")


def test_holes_away_from_tee() -> None:
    """Holes are not too close to the tee."""
    g = Game.__new__(Game)
    g.reset()
    for h in g.holes:
        too_close = abs(h.x - TEE_X) < 30 and abs(h.y - TEE_Y) < 50
        check(not too_close, f"hole ({h.x:.0f},{h.y:.0f}) not too close to tee")


# ── Ball Reset Tests ──


def test_reset_ball() -> None:
    """Ball resets to tee with current ball_color."""
    g = Game.__new__(Game)
    g.reset()
    g.ball.x = 999
    g.ball.y = 999
    g.ball.vx = 5.0
    g.ball.vy = 5.0
    g.ball_color = COLORS[2]  # GREEN
    g._reset_ball()
    check(g.ball.x == TEE_X, "ball.x back to tee")
    check(g.ball.y == TEE_Y, "ball.y back to tee")
    check(g.ball.vx == 0.0, "ball.vx zeroed")
    check(g.ball.vy == 0.0, "ball.vy zeroed")
    check(g.ball.color == g.ball_color, "ball.color updated")
    check(g.ball.active is True, "ball.active True")


# ── Hole Entry Detection ──


def test_check_hole_entry_hit() -> None:
    """Ball inside hole radius is detected."""
    g = Game.__new__(Game)
    g.reset()
    # Replace holes with one at known position
    g.holes = [Hole(100.0, 100.0, COLORS[0])]
    g.ball.x = 100.0
    g.ball.y = 100.0
    result = g._check_hole_entry()
    check(result is not None, "ball at hole center detected")
    check(result is g.holes[0], "correct hole returned")


def test_check_hole_entry_near_hit() -> None:
    """Ball just inside hole radius is detected."""
    g = Game.__new__(Game)
    g.reset()
    g.holes = [Hole(100.0, 100.0, COLORS[0])]
    g.ball.x = 100.0 + HOLE_RADIUS - 0.5
    g.ball.y = 100.0
    result = g._check_hole_entry()
    check(result is not None, "ball at radius edge detected")


def test_check_hole_entry_miss() -> None:
    """Ball outside hole radius is not detected."""
    g = Game.__new__(Game)
    g.reset()
    g.holes = [Hole(100.0, 100.0, COLORS[0])]
    g.ball.x = 100.0 + HOLE_RADIUS + 1.0
    g.ball.y = 100.0
    result = g._check_hole_entry()
    check(result is None, "ball outside radius not detected")


# ── Putt Physics Tests ──


def test_putt_moves_ball() -> None:
    """Ball with velocity moves."""
    g = Game.__new__(Game)
    g.reset()
    g.ball.x = 100.0
    g.ball.y = 100.0
    g.ball.vx = 3.0
    g.ball.vy = 0.0
    g.phase = Phase.PUTT
    # Clear holes so it doesn't sink
    g.holes = []
    g._update_putt()
    check(g.ball.x > 100.0, "ball moved right")
    check(g.ball.y == 100.0, "ball y unchanged")


def test_friction_slows_ball() -> None:
    """Friction reduces ball velocity."""
    g = Game.__new__(Game)
    g.reset()
    g.ball.vx = 5.0
    g.ball.vy = 0.0
    g.phase = Phase.PUTT
    g.holes = []
    g._update_putt()
    check(abs(g.ball.vx) < 5.0, "velocity reduced by friction")
    check(g.ball.vx == 5.0 * FRICTION, "vx = vx0 * FRICTION")


def test_ball_stops_below_min_speed() -> None:
    """Ball stops when speed < MIN_SPEED."""
    g = Game.__new__(Game)
    g.reset()
    g.ball.vx = MIN_SPEED * 0.5
    g.ball.vy = 0.0
    g.phase = Phase.PUTT
    g.holes = []
    initial_putts = g.putts_left
    g._update_putt()
    check(g.ball.vx == 0.0, "ball stopped (vx=0)")
    check(g.phase == Phase.AIM, "phase back to AIM after miss")
    check(g.putts_left == initial_putts - 1, "putts_left decremented")
    check(g.combo == 0, "combo reset after miss")


def test_wall_bounce_left() -> None:
    """Ball bounces off left wall."""
    g = Game.__new__(Game)
    g.reset()
    g.ball.x = 1.0  # near left wall
    g.ball.vx = -3.0
    g.ball.vy = 0.0
    g.phase = Phase.PUTT
    g.holes = []
    g._update_putt()
    check(g.ball.x >= 3, "ball not past left wall")  # BALL_RADIUS=3
    check(g.ball.vx > 0, "vx reversed (bounced right)")


def test_wall_bounce_right() -> None:
    """Ball bounces off right wall."""
    g = Game.__new__(Game)
    g.reset()
    g.ball.x = SCREEN_W - 1.0
    g.ball.vx = 3.0
    g.ball.vy = 0.0
    g.phase = Phase.PUTT
    g.holes = []
    g._update_putt()
    check(g.ball.x <= SCREEN_W - 3, "ball not past right wall")
    check(g.ball.vx < 0, "vx reversed (bounced left)")


def test_wall_bounce_top() -> None:
    """Ball bounces off top wall."""
    g = Game.__new__(Game)
    g.reset()
    g.ball.y = 1.0
    g.ball.vx = 0.0
    g.ball.vy = -3.0
    g.phase = Phase.PUTT
    g.holes = []
    g._update_putt()
    check(g.ball.y >= 3, "ball not past top wall")
    check(g.ball.vy > 0, "vy reversed (bounced down)")


def test_wall_bounce_bottom() -> None:
    """Ball bounces off bottom wall."""
    g = Game.__new__(Game)
    g.reset()
    g.ball.y = SCREEN_H - 1.0
    g.ball.vx = 0.0
    g.ball.vy = 3.0
    g.phase = Phase.PUTT
    g.holes = []
    g._update_putt()
    check(g.ball.y <= SCREEN_H - 3, "ball not past bottom wall")
    check(g.ball.vy < 0, "vy reversed (bounced up)")


# ── Scoring Tests ──


def test_matching_hole_scores_combo() -> None:
    """Sinking a matching-color hole gives combo score."""
    g = Game.__new__(Game)
    g.reset()
    g.score = 0
    g.combo = 0
    g.ball.color = COLORS[0]  # RED
    g.ball_color = COLORS[0]
    g.holes = [Hole(100.0, 50.0, COLORS[0])]
    g.ball.x = 100.0
    g.ball.y = 50.0
    g._on_hole_sunk(g.holes[0])
    check(g.score == 100, f"first matching = 100 (got {g.score})")
    check(g.combo == 1, f"combo incremented to 1 (got {g.combo})")
    check(g.ball_color == COLORS[0], "ball_color updated to sunk color")


def test_matching_hole_combo_x3() -> None:
    """Third consecutive matching hole = x3 score."""
    g = Game.__new__(Game)
    g.reset()
    g.score = 0
    g.combo = 2  # already have 2-combo
    g.ball.color = COLORS[1]  # BLUE
    g.ball_color = COLORS[1]
    g.holes = [Hole(100.0, 50.0, COLORS[1])]
    g.ball.x = 100.0
    g.ball.y = 50.0
    g._on_hole_sunk(g.holes[0])
    check(g.score == 300, f"3rd matching = 300 (got {g.score})")
    check(g.combo == 3, f"combo = 3 (got {g.combo})")
    check(g.best_combo == 3, f"best_combo = 3 (got {g.best_combo})")


def test_non_matching_hole_resets_combo() -> None:
    """Sinking a different-color hole resets combo."""
    g = Game.__new__(Game)
    g.reset()
    g.score = 0
    g.combo = 3  # built up combo
    g.best_combo = 3
    g.ball.color = COLORS[0]  # RED ball
    g.ball_color = COLORS[0]
    g.holes = [Hole(100.0, 50.0, COLORS[1])]  # BLUE hole
    g.ball.x = 100.0
    g.ball.y = 50.0
    g._on_hole_sunk(g.holes[0])
    check(g.score == 50, f"non-matching = 50 (got {g.score})")
    check(g.combo == 0, f"combo reset to 0 (got {g.combo})")
    check(g.best_combo == 3, "best_combo preserved")


def test_on_hole_sunk_decrements_putts() -> None:
    """Sinking a hole decrements putts_left."""
    g = Game.__new__(Game)
    g.reset()
    initial = g.putts_left
    g.holes = [Hole(100.0, 50.0, COLORS[0])]
    g.ball.x = 100.0
    g.ball.y = 50.0
    g.ball.color = COLORS[0]
    g.ball_color = COLORS[0]
    g._on_hole_sunk(g.holes[0])
    check(g.putts_left == initial - 1, f"putts_left decremented ({g.putts_left})")


def test_on_hole_sunk_replaces_hole() -> None:
    """Sunk hole is removed and a new one spawned."""
    g = Game.__new__(Game)
    g.reset()
    g.holes = [Hole(100.0, 50.0, COLORS[0])]
    g.ball.x = 100.0
    g.ball.y = 50.0
    g.ball.color = COLORS[0]
    g.ball_color = COLORS[0]
    g._on_hole_sunk(g.holes[0])
    check(len(g.holes) >= 1, "at least one hole remains")


def test_putt_miss_resets_combo() -> None:
    """Missing a putt (ball stops outside hole) resets combo."""
    g = Game.__new__(Game)
    g.reset()
    g.combo = 4
    g.ball.vx = MIN_SPEED * 0.4  # will stop
    g.ball.vy = 0.0
    g.phase = Phase.PUTT
    g.holes = []  # no holes to sink
    g._update_putt()
    check(g.combo == 0, f"combo reset after miss (got {g.combo})")
    check(g.phase == Phase.AIM, "back to AIM after miss")


def test_game_over_when_no_putts_after_miss() -> None:
    """Game over when putts_left reaches 0 after miss."""
    g = Game.__new__(Game)
    g.reset()
    g.putts_left = 1
    g.ball.vx = MIN_SPEED * 0.4
    g.ball.vy = 0.0
    g.phase = Phase.PUTT
    g.holes = []
    g._update_putt()
    check(g.putts_left == 0, "putts_left = 0")
    check(g.phase == Phase.GAME_OVER, f"game over after last miss (got {g.phase})")


def test_game_over_when_no_putts_after_sink() -> None:
    """Game over when putts_left reaches 0 after sinking last hole."""
    g = Game.__new__(Game)
    g.reset()
    g.putts_left = 1
    g.holes = [Hole(100.0, 50.0, COLORS[0])]
    g.ball.x = 100.0
    g.ball.y = 50.0
    g.ball.color = COLORS[0]
    g.ball_color = COLORS[0]
    g._on_hole_sunk(g.holes[0])
    check(g.putts_left == 0, "putts_left = 0")
    # After score pop timer expires, should go to GAME_OVER
    g.score_pop_timer = 1
    g._update_score_pop()
    check(g.phase == Phase.GAME_OVER, f"game over after last sink (got {g.phase})")


# ── Phase Tests ──


def test_aim_to_putt_transition() -> None:
    """Phase transitions from AIM to PUTT correctly simulated."""
    g = Game.__new__(Game)
    g.reset()
    g.phase = Phase.AIM
    # Simulate the putt initiation logic directly
    g.ball.x = 50.0
    g.ball.y = 200.0
    g.ball.vx = 3.0
    g.ball.vy = -2.0
    g.phase = Phase.PUTT
    check(g.phase == Phase.PUTT, "phase = PUTT")
    check(g.ball.vx == 3.0, "ball has velocity")


def test_phase_enum_values() -> None:
    """Phase enum has all expected values."""
    phases = {Phase.AIM, Phase.PUTT, Phase.SCORE_POP, Phase.GAME_OVER}
    check(len(phases) == 4, "4 phases defined")


# ── Particle System Tests ──


def test_particles_update_and_expire() -> None:
    """Particles move and expire over time."""
    g = Game.__new__(Game)
    g.reset()
    g.particles = [
        Particle(0.0, 0.0, 1.0, 0.0, 5, 8),
        Particle(0.0, 0.0, 0.0, 1.0, 1, 6),
    ]
    g._update_particles()
    # Particle with life=1 decrements to 0 and expires; only life=5 survives
    check(len(g.particles) == 1, "one particle alive after 1 tick")
    # After 5 more ticks, first should still be alive, second gone
    for _ in range(5):
        g._update_particles()
    check(len(g.particles) == 0, "all particles expired")


def test_burst_particles() -> None:
    """Burst creates particles."""
    g = Game.__new__(Game)
    g.reset()
    g._burst_particles(50.0, 50.0, 8, 10)
    check(len(g.particles) == 10, f"10 particles created (got {len(g.particles)})")
    for p in g.particles:
        check(p.life == 15, f"particle life=15 (got {p.life})")
        check(p.color == 8, f"particle color=8 (got {p.color})")


# ── Score Pop Phase Test ──


def test_score_pop_transitions() -> None:
    """Score pop phase transitions back to AIM."""
    g = Game.__new__(Game)
    g.reset()
    g.putts_left = 5
    g.phase = Phase.SCORE_POP
    g.score_pop_timer = 0  # expired
    g._update_score_pop()
    check(g.phase == Phase.AIM, "score_pop -> AIM when putts remain")


# ── Game Over Reset Test ──


def test_game_over_reset() -> None:
    """Game over reset restores initial state."""
    g = Game.__new__(Game)
    g.reset()
    g.score = 5000
    g.combo = 4
    g.best_combo = 5
    g.putts_left = 0
    g.phase = Phase.GAME_OVER
    g.reset()
    check(g.score == 0, "score reset")
    check(g.combo == 0, "combo reset")
    check(g.best_combo == 0, "best_combo reset")
    check(g.putts_left == NUM_PUTTS, "putts_left reset")
    check(g.phase == Phase.AIM, "phase = AIM")
    check(len(g.holes) == NUM_HOLES, "holes respawned")


# ── Best Combo Tracking Test ──


def test_best_combo_tracks_max() -> None:
    """best_combo records the maximum combo achieved."""
    g = Game.__new__(Game)
    g.reset()
    g.best_combo = 3
    g.combo = 2
    g.ball.color = COLORS[0]
    g.ball_color = COLORS[0]
    g.holes = [Hole(100.0, 50.0, COLORS[0])]
    g.ball.x = 100.0
    g.ball.y = 50.0
    g._on_hole_sunk(g.holes[0])
    # combo goes 2→3, best stays 3
    check(g.best_combo == 3, f"best_combo preserved (got {g.best_combo})")
    check(g.combo == 3, f"combo = 3 (got {g.combo})")


def test_best_combo_updates_on_new_max() -> None:
    """best_combo updates when combo exceeds previous max."""
    g = Game.__new__(Game)
    g.reset()
    g.best_combo = 2
    g.combo = 2
    g.ball.color = COLORS[0]
    g.ball_color = COLORS[0]
    g.holes = [Hole(100.0, 50.0, COLORS[0])]
    g.ball.x = 100.0
    g.ball.y = 50.0
    g._on_hole_sunk(g.holes[0])
    # combo goes 2→3, best should update to 3
    check(g.best_combo == 3, f"best_combo updated to {g.best_combo}")
    check(g.combo == 3, f"combo = 3 (got {g.combo})")


# ── Ball Color Constraint Tests ──


def test_ball_color_updated_on_sink() -> None:
    """After sinking, ball_color updates to sunk hole's color."""
    g = Game.__new__(Game)
    g.reset()
    original_color = g.ball_color
    # Pick a different color
    new_color = COLORS[(COLORS.index(original_color) + 1) % COLOR_COUNT]
    g.holes = [Hole(100.0, 50.0, new_color)]
    g.ball.x = 100.0
    g.ball.y = 50.0
    g.ball.color = original_color
    g.ball_color = original_color
    g._on_hole_sunk(g.holes[0])
    check(g.ball_color == new_color, f"ball_color updated to sunk color (got {g.ball_color})")


# ── Hole Replacement Test ──


def test_add_new_hole_in_bounds() -> None:
    """Replacement hole is in bounds and non-overlapping."""
    g = Game.__new__(Game)
    g.reset()
    g.holes = [Hole(50.0, 50.0, COLORS[0])]
    g._add_new_hole()
    check(len(g.holes) == 2, "new hole added")
    new_hole = g.holes[1]
    check(0 < new_hole.x < SCREEN_W, "new hole x in bounds")
    check(0 < new_hole.y < SCREEN_H, "new hole y in bounds")
    check(new_hole.color in COLORS, "new hole color valid")


# ── Run All Tests ──

if __name__ == "__main__":
    print("CHROMA DRIVE — Headless Logic Tests")
    print("=" * 50)

    tests = [
        ("Hole dataclass", test_hole_dataclass),
        ("Ball dataclass", test_ball_dataclass),
        ("Particle dataclass", test_particle_dataclass),
        ("Config values", test_config_values),
        ("Game construction", test_game_construction),
        ("Game reset state", test_game_reset_state),
        ("Holes in bounds", test_holes_in_bounds),
        ("Holes non-overlapping", test_holes_not_overlapping),
        ("Holes away from tee", test_holes_away_from_tee),
        ("Reset ball", test_reset_ball),
        ("Hole entry: hit", test_check_hole_entry_hit),
        ("Hole entry: near hit", test_check_hole_entry_near_hit),
        ("Hole entry: miss", test_check_hole_entry_miss),
        ("Putt moves ball", test_putt_moves_ball),
        ("Friction slows ball", test_friction_slows_ball),
        ("Ball stops below min speed", test_ball_stops_below_min_speed),
        ("Wall bounce left", test_wall_bounce_left),
        ("Wall bounce right", test_wall_bounce_right),
        ("Wall bounce top", test_wall_bounce_top),
        ("Wall bounce bottom", test_wall_bounce_bottom),
        ("Matching hole scores combo", test_matching_hole_scores_combo),
        ("Matching hole combo x3", test_matching_hole_combo_x3),
        ("Non-matching hole resets combo", test_non_matching_hole_resets_combo),
        ("Sink decrements putts", test_on_hole_sunk_decrements_putts),
        ("Sink replaces hole", test_on_hole_sunk_replaces_hole),
        ("Putt miss resets combo", test_putt_miss_resets_combo),
        ("Game over after miss", test_game_over_when_no_putts_after_miss),
        ("Game over after last sink", test_game_over_when_no_putts_after_sink),
        ("AIM->PUTT transition", test_aim_to_putt_transition),
        ("Phase enum values", test_phase_enum_values),
        ("Particles update/expire", test_particles_update_and_expire),
        ("Burst particles", test_burst_particles),
        ("Score pop transition", test_score_pop_transitions),
        ("Game over reset", test_game_over_reset),
        ("Best combo tracks max", test_best_combo_tracks_max),
        ("Best combo updates on new max", test_best_combo_updates_on_new_max),
        ("Ball color updated on sink", test_ball_color_updated_on_sink),
        ("Add new hole in bounds", test_add_new_hole_in_bounds),
    ]

    for name, fn in tests:
        print(f"\n{name}...")
        try:
            fn()
        except Exception as e:
            FAIL += 1
            print(f"  ERROR: {e}")

    total = PASS + FAIL
    print("\n" + "=" * 50)
    print(f"Results: {PASS}/{total} passed, {FAIL} failed")
    if FAIL > 0:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
    else:
        print("✅ ALL TESTS PASSED")
        sys.exit(0)
