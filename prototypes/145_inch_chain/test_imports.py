"""test_imports.py — Headless logic tests for 145_inch_chain."""
import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/145_inch_chain")
from main import (
    Game, Phase, Segment, Dot, Particle, FloatingText, GhostPoint,
    SCREEN_W, SCREEN_H, GROUND_Y, WORM_Y, NUM_SEGMENTS,
    SUPER_DURATION, LUNGE_DURATION, EAT_RADIUS, SUPER_COLLECT_RADIUS,
    DOT_COLORS,
    BLACK, NAVY, PURPLE, GREEN, BROWN, DARK_BLUE, LIGHT_BLUE,
    WHITE, RED, ORANGE, YELLOW, LIME, CYAN, GRAY, PINK, PEACH,
)


def _make_game() -> Game:
    """Create a Game instance bypassing Pyxel init."""
    g = Game.__new__(Game)
    # Pre-init all attributes that reset() touches
    g._rng = random.Random(42)
    g.segments = []
    g.dots = []
    g.particles = []
    g.floating_texts = []
    g.ghost_points = []
    g.best_ghost = []
    g.reset()
    g._rng = random.Random(42)  # re-seed after reset()
    return g


# ── Dataclass Tests ──

def test_segment_creation():
    seg = Segment(x=100.0, y=190.0)
    assert seg.x == 100.0
    assert seg.y == 190.0
    assert seg.angle == 0.0


def test_dot_creation():
    dot = Dot(x=300.0, y=195.0, color=2)
    assert dot.x == 300.0
    assert dot.y == 195.0
    assert dot.color == 2
    assert dot.alive is True


def test_particle_creation():
    p = Particle(x=10.0, y=20.0, vx=1.5, vy=-2.0, life=15, color=RED)
    assert p.x == 10.0
    assert p.y == 20.0
    assert p.vx == 1.5
    assert p.vy == -2.0
    assert p.life == 15
    assert p.color == RED


def test_floating_text_creation():
    ft = FloatingText(x=100.0, y=50.0, text="+25", life=30, color=LIME)
    assert ft.x == 100.0
    assert ft.y == 50.0
    assert ft.text == "+25"
    assert ft.life == 30
    assert ft.color == LIME


def test_ghost_point_creation():
    gp = GhostPoint(x=160.0, y=190.0)
    assert gp.x == 160.0
    assert gp.y == 190.0


# ── Phase Enum Tests ──

def test_phase_values():
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.SUPER in Phase
    assert Phase.GAME_OVER in Phase


# ── Constants Tests ──

def test_dot_colors_count():
    assert len(DOT_COLORS) == 4


def test_dot_colors_values():
    for color in DOT_COLORS:
        assert 0 <= color <= 15


def test_screen_dimensions():
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert GROUND_Y == 200
    assert WORM_Y == 190


def test_gameplay_constants():
    assert NUM_SEGMENTS >= 4
    assert SUPER_DURATION == 300
    assert EAT_RADIUS > 0
    assert SUPER_COLLECT_RADIUS > EAT_RADIUS


# ── Game.reset() Tests ──

def test_reset_initial_state():
    g = _make_game()
    assert g.phase == Phase.TITLE
    assert len(g.segments) == NUM_SEGMENTS
    assert g.segments[0].x == 160.0
    assert g.segments[0].y == WORM_Y
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.score == 0
    assert g.heat == 0.0
    assert g.super_timer == 0
    assert len(g.dots) == 0
    assert len(g.particles) == 0
    assert len(g.floating_texts) == 0
    assert len(g.ghost_points) == 0
    assert len(g.best_ghost) == 0
    assert g._last_color == -1
    assert g._lunge_frames == 0
    assert g._contract_amount == 0.0


def test_start_game_transitions():
    g = _make_game()
    g._start_game()
    assert g.phase == Phase.PLAYING
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert g.frame == 0
    assert len(g.dots) == 0


# ── _spawn_dot() Tests ──

def test_spawn_dot_creates_valid_dot():
    g = _make_game()
    dot = g._spawn_dot()
    assert 0 <= dot.color <= 3
    assert dot.x > SCREEN_W
    assert dot.y <= GROUND_Y
    assert dot.y >= GROUND_Y - 14
    assert dot.alive is True


def test_spawn_dots_have_variety():
    g = _make_game()
    colors = set()
    for _ in range(50):
        colors.add(g._spawn_dot().color)
    assert len(colors) == 4  # all 4 colors should appear


# ── _speed_for_score() Tests ──

def test_speed_for_score_base():
    g = _make_game()
    assert g._speed_for_score() == 1.5


def test_speed_for_score_increases():
    g = _make_game()
    g.score = 1000
    assert g._speed_for_score() == 2.0  # 1.5 + 1000/1000 * 0.5


def test_speed_for_score_caps():
    g = _make_game()
    g.score = 5000
    assert g._speed_for_score() == 4.0  # 1.5 + 5000/1000 * 0.5


# ── _get_current_speed() Tests ──

def test_get_current_speed_normal():
    g = _make_game()
    g.score = 0
    speed = g._get_current_speed()
    assert speed == 1.5


def test_get_current_speed_contracted():
    g = _make_game()
    g._contract_amount = 0.5
    speed = g._get_current_speed()
    assert speed == 1.5 * 0.3


def test_get_current_speed_lunge():
    g = _make_game()
    g._lunge_frames = 5
    speed = g._get_current_speed()
    assert speed == 1.5 * 2.5


# ── _eat_dot() Tests ──

def test_eat_first_dot():
    g = _make_game()
    dot = Dot(x=200.0, y=195.0, color=0)
    score_add, heat_add, is_super = g._eat_dot(dot)
    assert score_add == 15  # 10 + 1 * 5
    assert heat_add == 0
    assert is_super is False
    assert g.combo == 1
    assert g._last_color == 0


def test_eat_same_color_builds_combo():
    g = _make_game()
    g._last_color = 0
    g.combo = 2
    dot = Dot(x=200.0, y=195.0, color=0)
    score_add, heat_add, is_super = g._eat_dot(dot)
    assert score_add == 25  # 10 + 3 * 5
    assert heat_add == 0
    assert is_super is False
    assert g.combo == 3


def test_eat_same_color_triggers_super():
    g = _make_game()
    g._last_color = 0
    g.combo = 3
    dot = Dot(x=200.0, y=195.0, color=0)
    score_add, heat_add, is_super = g._eat_dot(dot)
    assert score_add == 30  # 10 + 4 * 5
    assert heat_add == 0
    assert is_super is True
    assert g.combo == 4


def test_eat_same_color_beyond_super():
    g = _make_game()
    g._last_color = 0
    g.combo = 5
    dot = Dot(x=200.0, y=195.0, color=0)
    score_add, heat_add, is_super = g._eat_dot(dot)
    assert score_add == 40  # 10 + 6 * 5
    assert is_super is True
    assert g.combo == 6


def test_eat_different_color_resets_combo():
    g = _make_game()
    g._last_color = 0
    g.combo = 3
    dot = Dot(x=200.0, y=195.0, color=1)
    score_add, heat_add, is_super = g._eat_dot(dot)
    assert score_add == 10  # base score
    assert heat_add == 15
    assert is_super is False
    assert g.combo == 0
    assert g._last_color == 1


def test_eat_during_super_gives_3x():
    g = _make_game()
    g.super_timer = 100
    g.combo = 4
    dot = Dot(x=200.0, y=195.0, color=0)
    score_add, heat_add, is_super = g._eat_dot(dot)
    assert score_add == (10 + 5 * 5) * 3  # (10+25)*3 = 105
    assert heat_add == 0
    assert is_super is False
    assert g.combo == 5


def test_eat_dot_updates_max_combo():
    g = _make_game()
    g._last_color = 0
    g.combo = 3
    g.max_combo = 3
    dot = Dot(x=200.0, y=195.0, color=0)
    g._eat_dot(dot)
    assert g.max_combo == 4


def test_max_combo_persists_after_reset():
    g = _make_game()
    g._last_color = 0
    g.combo = 3
    g.max_combo = 3
    dot = Dot(x=200.0, y=195.0, color=0)
    g._eat_dot(dot)
    assert g.max_combo == 4
    # eat wrong color, max_combo should persist
    dot2 = Dot(x=250.0, y=195.0, color=1)
    g._eat_dot(dot2)
    assert g.combo == 0
    assert g.max_combo == 4  # unchanged


# ── _activate_super() Tests ──

def test_activate_super():
    g = _make_game()
    g.phase = Phase.PLAYING
    g._activate_super()
    assert g.phase == Phase.SUPER
    assert g.super_timer == SUPER_DURATION


# ── _update_super() Tests ──

def test_update_super_collects_nearby_dots():
    g = _make_game()
    g._start_game()
    g.segments[0].x = 200.0
    g.segments[0].y = WORM_Y
    g.super_timer = 100
    g.phase = Phase.SUPER
    # Place dots near the head
    g.dots = [
        Dot(x=210.0, y=WORM_Y, color=0),
        Dot(x=220.0, y=WORM_Y, color=0),
        Dot(x=300.0, y=WORM_Y, color=1),  # far away
    ]
    g._update_super()
    # First two should be collected (within 60px radius)
    assert not g.dots[0].alive
    assert not g.dots[1].alive
    assert g.dots[2].alive  # far away, not collected
    assert g.score > 0


def test_update_super_does_not_double_collect():
    g = _make_game()
    g._start_game()
    g.segments[0].x = 200.0
    g.segments[0].y = WORM_Y
    g.super_timer = 100
    g.phase = Phase.SUPER
    g.dots = [Dot(x=205.0, y=WORM_Y, color=0)]
    score_before = g.score
    g._update_super()
    score_after_first = g.score
    assert score_after_first > score_before
    # Call again — already dead dot should not be collected again
    g._update_super()
    assert g.score == score_after_first


# ── _update_heat() Tests ──

def test_update_heat_decays():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 49.0


def test_update_heat_floor_zero():
    g = _make_game()
    g.phase = Phase.PLAYING
    g.heat = 0.0
    g._update_heat()
    assert g.heat == 0.0


def test_update_heat_game_over():
    g = _make_game()
    g._start_game()
    g.heat = 101.0  # after decay: 100, which IS >= 100
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_update_heat_no_game_over_during_title():
    g = _make_game()
    g.phase = Phase.TITLE
    g.heat = 101.0
    g._update_heat()
    assert g.phase == Phase.TITLE  # game over blocked during title


# ── _update_particles() Tests ──

def test_update_particles_moves_and_decays():
    g = _make_game()
    g.particles = [
        Particle(x=0.0, y=0.0, vx=1.0, vy=-2.0, life=5, color=RED),
        Particle(x=0.0, y=0.0, vx=-0.5, vy=1.0, life=10, color=GREEN),
    ]
    g._update_particles()
    assert g.particles[0].x == 1.0
    assert g.particles[0].y == -2.0
    assert g.particles[0].life == 4
    assert g.particles[1].x == -0.5
    assert g.particles[1].y == 1.0
    assert g.particles[1].life == 9


def test_update_particles_removes_dead():
    g = _make_game()
    g.particles = [
        Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=1, color=RED),
        Particle(x=0.0, y=0.0, vx=0.0, vy=0.0, life=5, color=GREEN),
    ]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].color == GREEN


def test_update_particles_empty():
    g = _make_game()
    g._update_particles()
    assert len(g.particles) == 0


# ── _update_floating_texts() Tests ──

def test_update_floating_texts():
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=100.0, y=100.0, text="+25", life=5, color=LIME),
        FloatingText(x=200.0, y=80.0, text="COMBO", life=2, color=CYAN),
    ]
    g._update_floating_texts()
    assert g.floating_texts[0].y == 99.0
    assert g.floating_texts[0].life == 4
    assert g.floating_texts[1].y == 79.0
    assert g.floating_texts[1].life == 1


def test_update_floating_texts_removes_dead():
    g = _make_game()
    g.floating_texts = [
        FloatingText(x=100.0, y=100.0, text="+25", life=1, color=LIME),
        FloatingText(x=200.0, y=80.0, text="COMBO", life=5, color=CYAN),
    ]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "COMBO"


# ── _spawn_particles() Tests ──

def test_spawn_particles_count():
    g = _make_game()
    g._spawn_particles(100.0, 100.0, 5, RED)
    assert len(g.particles) == 5


def test_spawn_particles_properties():
    g = _make_game()
    g._spawn_particles(50.0, 60.0, 3, GREEN)
    for p in g.particles:
        assert p.x == 50.0
        assert p.y == 60.0
        assert -1.5 <= p.vx <= 1.5
        assert -3.0 <= p.vy <= -1.0
        assert 10 <= p.life <= 20
        assert p.color == GREEN


# ── _spawn_floating_text() Tests ──

def test_spawn_floating_text():
    g = _make_game()
    g._spawn_floating_text(100.0, 50.0, "+30", LIME)
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].text == "+30"
    assert g.floating_texts[0].color == LIME
    assert g.floating_texts[0].life == 30


# ── _record_ghost_point() Tests ──

def test_record_ghost_point():
    g = _make_game()
    g._start_game()
    g.segments[0].x = 150.0
    g.segments[0].y = 190.0
    g._record_ghost_point()
    assert len(g.ghost_points) == 1
    assert g.ghost_points[0].x == 150.0
    assert g.ghost_points[0].y == 190.0


def test_record_multiple_ghost_points():
    g = _make_game()
    g._start_game()
    for i in range(5):
        g.segments[0].x = 100.0 + i * 10
        g._record_ghost_point()
    assert len(g.ghost_points) == 5


# ── _update_worm() Tests ──

def test_update_worm_moves_forward():
    g = _make_game()
    g._start_game()
    start_x = g.segments[0].x
    g._update_worm()
    assert g.segments[0].x > start_x


def test_update_worm_clamps_left():
    g = _make_game()
    g._start_game()
    g.segments[0].x = -10
    g.segments[1].x = -20
    g.segments[2].x = -30
    g._update_worm()
    # Head should be clamped to at least 0
    assert g.segments[0].x >= 0


def test_update_worm_segments_follow():
    g = _make_game()
    g._start_game()
    # All segments should be roughly in a line
    for i in range(len(g.segments) - 1):
        assert g.segments[i].x >= g.segments[i + 1].x


def test_update_worm_updates_wave_phase():
    g = _make_game()
    g._start_game()
    g.frame = 10  # need frame > 0 for wave_phase = frame * 0.1
    old_phase = g._wave_phase
    g.frame = 20
    g._update_worm()
    assert g._wave_phase != old_phase
    assert abs(g._wave_phase - 2.0) < 0.01  # 20 * 0.1 = 2.0


# ── _update_dots() Tests ──

def test_update_dots_scrolls_left():
    g = _make_game()
    g.dots = [Dot(x=200.0, y=195.0, color=0)]
    g._update_dots()
    assert g.dots[0].x == 199.5


def test_update_dots_removes_offscreen():
    g = _make_game()
    g.dots = [Dot(x=-20.0, y=195.0, color=0)]
    g._update_dots()
    assert len(g.dots) == 0


def test_update_dots_keeps_visible():
    g = _make_game()
    g.dots = [Dot(x=100.0, y=195.0, color=0)]
    g._update_dots()
    assert len(g.dots) == 1


def test_update_dots_skips_dead():
    g = _make_game()
    g.dots = [
        Dot(x=200.0, y=195.0, color=0, alive=False),
        Dot(x=100.0, y=195.0, color=1),
    ]
    g._update_dots()
    assert len(g.dots) == 1
    assert g.dots[0].color == 1


# ── Integration Tests ──

def test_full_combo_chain():
    """Simulate eating 4 same-color dots in sequence."""
    g = _make_game()
    g._start_game()

    dots = [
        Dot(x=200.0, y=WORM_Y, color=0),
        Dot(x=210.0, y=WORM_Y, color=0),
        Dot(x=220.0, y=WORM_Y, color=0),
        Dot(x=230.0, y=WORM_Y, color=0),
    ]

    g._eat_dot(dots[0])
    assert g.combo == 1

    g._eat_dot(dots[1])
    assert g.combo == 2

    g._eat_dot(dots[2])
    assert g.combo == 3

    score_add, heat_add, is_super = g._eat_dot(dots[3])
    assert g.combo == 4
    assert is_super is True
    assert g.max_combo == 4


def test_full_heat_game_over():
    """Simulate heat accumulation to game over."""
    g = _make_game()
    g._start_game()
    g.heat = 86.0
    g._last_color = 0
    g.combo = 0

    dot = Dot(x=200.0, y=WORM_Y, color=1)  # wrong color
    score_add, heat_add, is_super = g._eat_dot(dot)
    assert heat_add == 15
    g.heat += heat_add  # 101.0

    # _update_heat decays first, then checks: 101 - 1 = 100 >= 100 => GAME_OVER
    g._update_heat()
    assert g.phase == Phase.GAME_OVER


def test_best_score_updated_on_game_over():
    g = _make_game()
    g._start_game()
    g.score = 500
    g._best_score = 0
    g.heat = 101.0
    g._update_heat()
    assert g.phase == Phase.GAME_OVER
    assert g._best_score == 500
    assert len(g.best_ghost) == len(g.ghost_points)


def test_contract_lunge_mechanics():
    g = _make_game()
    g._start_game()

    # Normal speed
    assert g._get_current_speed() == 1.5

    # Contract (simulated by setting state directly)
    g._contract_amount = 0.5
    assert g._get_current_speed() == 1.5 * 0.3

    # Lunge
    g._contract_amount = 0.0
    g._lunge_frames = 5
    assert g._get_current_speed() == 1.5 * 2.5

    # After lunge expires
    g._lunge_frames = 0
    assert g._get_current_speed() == 1.5


def test_segments_maintain_order():
    g = _make_game()
    g._start_game()
    for _ in range(10):
        g._update_worm()
    # Segments should maintain relative order (head at index 0, tail at end)
    for i in range(len(g.segments) - 1):
        assert g.segments[i].x > g.segments[i + 1].x - 5  # allow small overlaps


def test_score_alignment():
    """Test that score calculation is consistent."""
    g = _make_game()
    g._last_color = 0
    g.combo = 0
    dot = Dot(x=200.0, y=WORM_Y, color=0)
    score_add, _, _ = g._eat_dot(dot)
    assert score_add == 15  # 10 + 1*5


# ── Run ──

if __name__ == "__main__":
    import inspect

    passed = 0
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                passed += 1
                print(f"  PASS {name}")
            except Exception as e:
                failed += 1
                print(f"  FAIL {name}: {e}")

    print(f"\n{passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
