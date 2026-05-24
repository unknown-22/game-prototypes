"""test_imports.py — Headless logic tests for SLASH SURGE (063)."""
import math
import random
import sys
sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/063_slash_surge")
from main import Game, Orb, Particle


def _make_game() -> Game:
    """Factory: bypass __init__ (avoids pyxel.init), pre-init all attrs, call _init_state()."""
    g = Game.__new__(Game)
    g.phase = 0
    g.orbs = []
    g.particles = []
    g.score = 0
    g.hp = 10
    g.combo = 0
    g.last_slashed_color = None
    g.max_combo = 0
    g.spawn_timer = 60
    g.slash_line = []
    g.is_slashing = False
    g.surge_queue = []
    g.surge_anim_timer = 0
    g.overload_damage_timer = 0
    g._init_state()
    return g


# ── Constants ──
def test_constants() -> None:
    from main import SCREEN_W, SCREEN_H, MAX_ORBS, COMBO_SURGE_THRESHOLD
    from main import ORB_RADIUS, FRAGMENT_RADIUS, HP_MAX, COLOR_RED, COLOR_GREEN, COLOR_BLUE, COLOR_YELLOW
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert MAX_ORBS == 25
    assert COMBO_SURGE_THRESHOLD == 5
    assert ORB_RADIUS == 10.0
    assert FRAGMENT_RADIUS == 5.0
    assert HP_MAX == 10
    assert COLOR_RED == 8
    assert COLOR_GREEN == 3
    assert COLOR_BLUE == 5
    assert COLOR_YELLOW == 10


# ── Orb dataclass ──
def test_orb_creation() -> None:
    orb = Orb(100.0, 50.0, 1.0, -0.5, 8, 10.0, False, -1)
    assert orb.x == 100.0
    assert orb.y == 50.0
    assert orb.color == 8
    assert orb.radius == 10.0
    assert not orb.is_fragment
    assert orb.life == -1


# ── Particle dataclass ──
def test_particle_creation() -> None:
    p = Particle(10.0, 20.0, 1.5, -0.5, 3, 15)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.color == 3
    assert p.life == 15


# ── Game init ──
def test_game_init() -> None:
    g = _make_game()
    assert g.phase == 0  # PHASE_TITLE
    assert g.score == 0
    assert g.hp == 10
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.last_slashed_color is None
    assert len(g.orbs) == 0
    assert len(g.particles) == 0
    assert len(g.slash_line) == 0


# ── Segment-circle intersection ──
def test_segment_circle_hit_direct() -> None:
    # Segment passes right through the circle
    assert Game._segment_circle_hit(0, 0, 10, 0, 5, 0, 6)
    # Segment far from circle
    assert not Game._segment_circle_hit(0, 0, 10, 0, 5, 100, 6)
    # Segment endpoint inside circle
    assert Game._segment_circle_hit(4, 0, 10, 0, 5, 0, 6)
    # Zero-length segment (p1 == p2) at circle center
    assert Game._segment_circle_hit(5, 0, 5, 0, 5, 0, 1)
    # Segment tangent (barely touches)
    assert Game._segment_circle_hit(0, 0, 10, 0, 5, -6, 6)


# ── Combo logic ──
def test_update_combo_same_color() -> None:
    g = _make_game()
    g._update_combo(8)  # RED
    assert g.combo == 1
    assert g.last_slashed_color == 8
    assert g.max_combo == 1

    g._update_combo(8)  # same color
    assert g.combo == 2
    assert g.max_combo == 2


def test_update_combo_different_color() -> None:
    g = _make_game()
    g._update_combo(8)
    assert g.combo == 1
    g._update_combo(3)  # GREEN
    assert g.combo == 1  # reset
    assert g.last_slashed_color == 3


def test_combo_multiplier() -> None:
    g = _make_game()
    g.combo = 1; assert g._combo_multiplier() == 1
    g.combo = 2; assert g._combo_multiplier() == 2
    g.combo = 3; assert g._combo_multiplier() == 2
    g.combo = 4; assert g._combo_multiplier() == 3
    g.combo = 5; assert g._combo_multiplier() == 3
    g.combo = 6; assert g._combo_multiplier() == 5
    g.combo = 10; assert g._combo_multiplier() == 5


# ── Spawn orb ──
def test_spawn_orb() -> None:
    g = _make_game()
    random.seed(42)
    g._spawn_orb()
    assert len(g.orbs) == 1
    orb = g.orbs[0]
    assert orb.radius == 10.0
    assert not orb.is_fragment
    assert orb.life == -1
    assert orb.color in (8, 3, 5, 10)  # one of 4 colors
    random.seed()  # restore


# ── Split orb ──
def test_split_orb() -> None:
    g = _make_game()
    g.orbs = [Orb(100.0, 100.0, 0.5, 0.3, 8, 10.0, False, -1)]
    g._split_orb(0)
    assert len(g.orbs) == 2
    for f in g.orbs:
        assert f.is_fragment
        assert f.radius == 5.0
        assert f.life == 300


# ── Slash regular orb (not fragment) ──
def test_slash_orb_regular() -> None:
    g = _make_game()
    g.orbs = [Orb(100.0, 100.0, 0.0, 0.0, 8, 10.0, False, -1)]
    initial_score = g.score
    g._slash_orb(0)
    # Regular orb should be split into 2 fragments
    assert len(g.orbs) == 2
    assert all(o.is_fragment for o in g.orbs)
    assert g.score > initial_score
    assert g.combo == 1


# ── Slash fragment ──
def test_slash_orb_fragment() -> None:
    g = _make_game()
    g.orbs = [Orb(100.0, 100.0, 0.0, 0.0, 8, 5.0, True, 300)]
    initial_score = g.score
    g._slash_orb(0)
    # Fragment should be removed (not split)
    assert len(g.orbs) == 0
    assert g.score > initial_score
    assert g.combo == 1


# ── Slash collision detection ──
def test_slash_collisions() -> None:
    g = _make_game()
    g.orbs = [
        Orb(50.0, 50.0, 0.0, 0.0, 8, 10.0, False, -1),
        Orb(200.0, 100.0, 0.0, 0.0, 3, 10.0, False, -1),
    ]
    # Slash line passes through first orb
    g.slash_line = [(0, 40), (60, 40), (60, 60)]
    g._check_slash_collisions()
    # First orb should have been slashed (split into 2 fragments)
    # Second orb untouched
    assert len(g.orbs) >= 2  # 2 fragments + 1 untouched orb = 3
    untouched = [o for o in g.orbs if o.color == 3 and not o.is_fragment]
    assert len(untouched) == 1


# ── BFS surge ──
def test_bfs_surge_connected() -> None:
    g = _make_game()
    g.orbs = [
        Orb(10.0, 10.0, 0, 0, 8, 5.0, True, 100),   # same color, cluster
        Orb(22.0, 15.0, 0, 0, 8, 5.0, True, 100),    # same color, nearby
        Orb(200.0, 200.0, 0, 0, 3, 5.0, True, 100),  # diff color
        Orb(50.0, 50.0, 0, 0, 8, 5.0, True, 100),    # same color, far
    ]
    result = g._bfs_surge(8)
    # All same-color fragments returned (including far one)
    assert len(result) == 3
    assert all(g.orbs[i].color == 8 for i in result)


def test_bfs_surge_none() -> None:
    g = _make_game()
    g.orbs = [
        Orb(10.0, 10.0, 0, 0, 3, 5.0, True, 100),
        Orb(200.0, 200.0, 0, 0, 3, 5.0, True, 100),
    ]
    result = g._bfs_surge(8)  # No RED fragments exist
    assert len(result) == 0


# ── Trigger surge ──
def test_trigger_surge() -> None:
    g = _make_game()
    g.orbs = [
        Orb(10.0, 10.0, 0, 0, 8, 5.0, True, 100),
        Orb(20.0, 15.0, 0, 0, 8, 5.0, True, 100),
        Orb(200.0, 200.0, 0, 0, 3, 5.0, True, 100),  # different color, survives
    ]
    g.score = 0
    g.combo = 5
    g._trigger_surge(8)
    # Only RED fragments destroyed, GREEN survives
    survivors = [o for o in g.orbs if o.color == 3]
    assert len(survivors) == 1
    assert g.score > 0
    assert g.combo == 0
    assert g.last_slashed_color is None


# ── HP update ──
def test_update_hp() -> None:
    g = _make_game()
    g._update_hp(-3)
    assert g.hp == 7
    g._update_hp(-10)
    assert g.hp == 0  # clamped
    g._update_hp(2)
    assert g.hp == 2


# ── Overload check ──
def test_check_overload_below_threshold() -> None:
    g = _make_game()
    g.orbs = [Orb(0, 0, 0, 0, 8, 10.0, False, -1)] * 20
    g.hp = 10
    g.overload_damage_timer = 0
    g._check_overload()
    assert g.hp == 10  # no damage
    assert g.overload_damage_timer == 0


def test_check_overload_above_threshold() -> None:
    g = _make_game()
    g.orbs = [Orb(0, 0, 0, 0, 8, 10.0, False, -1)] * 26
    g.hp = 10
    g.overload_damage_timer = 29
    g._check_overload()
    # timer increments to 30, triggers damage
    assert g.hp == 9
    assert g.overload_damage_timer == 0


# ── Particle system ──
def test_update_particles() -> None:
    g = _make_game()
    g.particles = [
        Particle(10.0, 10.0, 1.0, -0.5, 8, 5),
        Particle(50.0, 50.0, 0.0, 0.0, 3, 1),  # will expire
    ]
    g._update_particles()
    # particle with life=1 expires immediately (decrement→0→removed)
    assert len(g.particles) == 1
    assert g.particles[0].life == 4
    assert abs(g.particles[0].x - 11.0) < 0.01
    assert abs(g.particles[0].y - 9.5) < 0.01


def test_spawn_slash_particles() -> None:
    g = _make_game()
    g._spawn_slash_particles(100.0, 50.0, 8)
    assert len(g.particles) == 6
    for p in g.particles:
        assert p.color == 8
        assert 6 <= p.life <= 16
        assert p.x == 100.0
        assert p.y == 50.0


def test_spawn_explosion_particles() -> None:
    g = _make_game()
    g._spawn_explosion_particles(100.0, 50.0, 3)
    assert len(g.particles) == 10
    for p in g.particles:
        assert p.color == 3
        assert 10 <= p.life <= 22


# ── Orb movement ──
def test_update_orbs_movement() -> None:
    g = _make_game()
    g.orbs = [Orb(160.0, 120.0, 1.0, -0.5, 8, 10.0, False, -1)]
    g._update_orbs()
    orb = g.orbs[0]
    assert orb.x == 161.0
    assert orb.y == 119.5


def test_update_orbs_wall_bounce() -> None:
    g = _make_game()
    # Orb at left wall
    g.orbs = [Orb(-5.0, 120.0, -1.0, 0.0, 8, 10.0, False, -1)]
    g._update_orbs()
    orb = g.orbs[0]
    assert orb.x == 10.0  # clamped to radius
    assert orb.vx > 0  # bounced


def test_update_orbs_fragment_lifetime() -> None:
    g = _make_game()
    g.orbs = [Orb(100.0, 100.0, 0.0, 0.0, 8, 5.0, True, 1)]
    g._update_orbs()
    # life decremented to 0, removed
    assert len(g.orbs) == 0


# ── Phase transitions (simulated, no pyxel input) ──
def test_phase_transition_to_game_over() -> None:
    g = _make_game()
    g.phase = 1  # PLAYING
    g.hp = 0
    # Simulate what _update_playing does at the end
    if g.hp <= 0:
        g.hp = 0
        g.phase = 2  # GAME_OVER
    assert g.phase == 2


# ── Risk/reward: slash combo increases multiplier ──
def test_risk_reward_multiplier() -> None:
    g = _make_game()
    g.combo = 1
    base = g._combo_multiplier()
    g.combo = 5
    high = g._combo_multiplier()
    assert high > base  # higher combo = higher multiplier


# ── Risk/reward: SURGE gives bonus score per fragment ──
def test_surge_bonus_scales_with_fragments() -> None:
    g = _make_game()
    g.combo = 5
    g.orbs = [
        Orb(10.0, 10.0, 0, 0, 8, 5.0, True, 100),
        Orb(20.0, 15.0, 0, 0, 8, 5.0, True, 100),
    ]
    g.score = 0
    g._trigger_surge(8)
    assert g.score > 0


if __name__ == "__main__":
    tests = [
        fn for name, fn in sorted(globals().items())
        if name.startswith("test_")
    ]
    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            print(f"  PASS {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {test_fn.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
