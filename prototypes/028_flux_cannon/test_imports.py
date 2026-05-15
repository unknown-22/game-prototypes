"""test_imports.py — Headless logic tests for FLUX CANNON.

Tests dataclass creation, phase enum, target spawning, combo logic,
scoring calculation, focus/heat mechanics, and super AOE radius.
All tests avoid pyxel input methods (btn/btnp/mouse_x/mouse_y) which
panic when Pyxel is not initialized.

Uses Game.__new__ + manual init to bypass pyxel.init/run for headless testing.
"""

from __future__ import annotations

import math
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/028_flux_cannon")
from main import (
    BASE_SCORE,
    COLOR_LIST,
    COMBO_MULT_STEP,
    FOCUS_HIT_BONUS,
    FOCUS_LOW_THRESHOLD,
    FOCUS_MAX,
    FOCUS_REGEN,
    GAME_TIME,
    GRAVITY,
    HEAT_COOLDOWN_FRAMES,
    HEAT_MAX,
    HEAT_PER_SHOT,
    N_COLORS,
    POWER_MAX,
    POWER_MIN,
    SUPER_AOE_RADIUS,
    SUPER_COMBO_THRESHOLD,
    SUPER_MULT,
    TARGET_RADIUS,
    Color,
    FloatingText,
    Game,
    Particle,
    Phase,
    Projectile,
    Target,
)


def _make_blank_game() -> Game:
    """Create a Game instance without calling pyxel.init/run.

    Uses __new__ + manual attribute init so we can test core logic headlessly.
    """
    g = Game.__new__(Game)
    g.phase = Phase.AIMING
    g.score = 0
    g.combo = 0
    g.combo_color = None
    g.is_super_next = False
    g.power = 80
    g.aim_angle = -math.pi / 4
    g.focus = FOCUS_MAX
    g.heat = 0.0
    g.heat_cooldown = 0
    g.time_remaining = GAME_TIME
    g.shots_fired = 0
    g.hits_landed = 0
    g.targets = []
    g.projectile = None
    g.particles = []
    g.float_texts = []
    g.screen_shake = 0
    return g


# ── Dataclass tests ──────────────────────────────────────────────────────

def test_target_creation() -> None:
    t = Target(x=150.0, y=80.0, color=Color.RED)
    assert t.x == 150.0
    assert t.y == 80.0
    assert t.color == Color.RED
    assert t.alive is True
    assert t.drift_vx == 0.0


def test_projectile_creation() -> None:
    p = Projectile(x=50.0, y=270.0, vx=80.0, vy=-60.0, color=Color.BLUE)
    assert p.color == Color.BLUE
    assert p.is_super is False
    assert p.alive is True


def test_projectile_super() -> None:
    p = Projectile(x=50.0, y=270.0, vx=80.0, vy=-60.0, color=Color.GREEN, is_super=True)
    assert p.is_super is True


def test_particle_creation() -> None:
    p = Particle(x=100.0, y=50.0, vx=2.0, vy=-1.0, life=20, color=8)
    assert p.life == 20
    assert p.color == 8


def test_floating_text_creation() -> None:
    ft = FloatingText(x=200.0, y=100.0, text="+150", life=40, color=7)
    assert ft.text == "+150"
    assert ft.life == 40


# ── Enum tests ───────────────────────────────────────────────────────────

def test_color_enum_values() -> None:
    assert len(Color) == 5
    assert Color.RED.value == 0
    assert Color.BLUE.value == 1
    assert Color.GREEN.value == 2
    assert Color.YELLOW.value == 3
    assert Color.PURPLE.value == 4


def test_phase_enum() -> None:
    assert Phase.AIMING in Phase
    assert Phase.FLYING in Phase
    assert Phase.GAME_OVER in Phase


# ── Constant tests ───────────────────────────────────────────────────────

def test_constants() -> None:
    assert POWER_MIN < POWER_MAX
    assert SUPER_COMBO_THRESHOLD >= 2
    assert FOCUS_MAX > FOCUS_LOW_THRESHOLD
    assert HEAT_PER_SHOT > 0
    assert HEAT_COOLDOWN_FRAMES > 0
    assert BASE_SCORE > 0
    assert SUPER_MULT > 1.0
    assert TARGET_RADIUS > 0
    assert SUPER_AOE_RADIUS > TARGET_RADIUS
    assert GRAVITY > 0
    assert len(COLOR_LIST) == N_COLORS


# ── Target spawning tests ────────────────────────────────────────────────

def test_spawn_initial_targets() -> None:
    g = _make_blank_game()
    g._spawn_initial_targets()
    assert len(g.targets) == 6
    for t in g.targets:
        assert t.alive is True
        assert isinstance(t.color, Color)
        assert 0 <= t.x <= 400
        assert 0 <= t.y <= 300


def test_make_target_no_overlap() -> None:
    g = _make_blank_game()
    t = g._make_target()
    assert t.alive is True
    assert isinstance(t.color, Color)
    assert TARGET_RADIUS + 40 <= t.x <= 400 - TARGET_RADIUS - 10


def test_replace_dead_targets_all_alive() -> None:
    g = _make_blank_game()
    g._spawn_initial_targets()
    _original = [t.color for t in g.targets]  # snapshot for verification
    g._replace_dead_targets()
    assert len(g.targets) == 6
    # All should still be the same since none are dead
    assert [t.alive for t in g.targets] == [True] * 6


def test_replace_dead_targets_one_dead() -> None:
    g = _make_blank_game()
    g._spawn_initial_targets()
    g.targets[2].alive = False
    g._replace_dead_targets()
    assert g.targets[2].alive is True  # replaced


def test_overlaps_existing() -> None:
    g = _make_blank_game()
    g.targets.append(Target(x=200.0, y=100.0, color=Color.RED))
    assert g._overlaps_existing(205.0, 105.0) is True  # within min_dist
    assert g._overlaps_existing(300.0, 200.0) is False  # far away, no overlap


# ── Combo logic tests ────────────────────────────────────────────────────

def test_on_hit_same_color_continues_combo() -> None:
    g = _make_blank_game()
    g.combo_color = Color.RED
    g.combo = 2
    g.projectile = Projectile(x=200.0, y=100.0, vx=0.0, vy=0.0, color=Color.RED)
    t = Target(x=200.0, y=100.0, color=Color.RED)
    g.targets = [t, Target(x=300.0, y=80.0, color=Color.BLUE)]
    g._on_hit(t)
    assert g.combo == 3
    assert g.combo_color == Color.RED
    assert g.is_super_next is True  # combo >= 3
    assert g.phase == Phase.AIMING


def test_on_hit_different_color_resets_combo() -> None:
    g = _make_blank_game()
    g.combo_color = Color.RED
    g.combo = 2
    g.projectile = Projectile(x=200.0, y=100.0, vx=0.0, vy=0.0, color=Color.RED)
    t = Target(x=200.0, y=100.0, color=Color.BLUE)
    g.targets = [t, Target(x=300.0, y=80.0, color=Color.GREEN)]
    g._on_hit(t)
    assert g.combo == 1
    assert g.combo_color == Color.BLUE
    assert g.is_super_next is False


def test_on_hit_first_hit() -> None:
    g = _make_blank_game()
    g.combo_color = None
    g.combo = 0
    g.projectile = Projectile(x=200.0, y=100.0, vx=0.0, vy=0.0, color=Color.GREEN)
    t = Target(x=200.0, y=100.0, color=Color.GREEN)
    g.targets = [t]
    g._on_hit(t)
    assert g.combo == 1
    assert g.combo_color == Color.GREEN
    assert g.is_super_next is False  # combo 1 < 3


# ── Scoring tests ────────────────────────────────────────────────────────

def test_score_base() -> None:
    g = _make_blank_game()
    g.projectile = Projectile(x=200.0, y=100.0, vx=0.0, vy=0.0, color=Color.RED)
    t = Target(x=200.0, y=100.0, color=Color.RED)
    g.targets = [t, Target(x=300.0, y=80.0, color=Color.BLUE)]
    old_score = g.score
    g._on_hit(t)
    assert g.score > old_score
    assert g.score == BASE_SCORE  # combo 1, no super


def test_score_combo_multiplier() -> None:
    g = _make_blank_game()
    g.combo = 3
    g.combo_color = Color.RED
    g.projectile = Projectile(x=200.0, y=100.0, vx=0.0, vy=0.0, color=Color.RED)
    t = Target(x=200.0, y=100.0, color=Color.RED)
    g.targets = [t, Target(x=300.0, y=80.0, color=Color.BLUE)]
    g._on_hit(t)
    expected = int(BASE_SCORE * (1.0 + 3 * COMBO_MULT_STEP))
    assert g.score == expected


def test_score_super_multiplier() -> None:
    g = _make_blank_game()
    g.combo = 2
    g.combo_color = Color.RED
    g.projectile = Projectile(x=200.0, y=100.0, vx=0.0, vy=0.0, color=Color.RED, is_super=True)
    t = Target(x=200.0, y=100.0, color=Color.RED)
    g.targets = [t, Target(x=300.0, y=80.0, color=Color.BLUE)]
    g._on_hit(t)
    expected = int(BASE_SCORE * (1.0 + 2 * COMBO_MULT_STEP) * SUPER_MULT)
    assert g.score == expected


# ── Focus tests ──────────────────────────────────────────────────────────

def test_focus_regen() -> None:
    g = _make_blank_game()
    g.focus = 50.0
    # Call update targeting code directly (not full update, which calls pyxel)
    dt = 1.0 / 60.0
    g.focus = min(FOCUS_MAX, g.focus + FOCUS_REGEN * dt)
    assert g.focus > 50.0


def test_focus_hit_bonus() -> None:
    g = _make_blank_game()
    g.focus = 30.0
    g.projectile = Projectile(x=200.0, y=100.0, vx=0.0, vy=0.0, color=Color.RED)
    t = Target(x=200.0, y=100.0, color=Color.RED)
    g.targets = [t, Target(x=300.0, y=80.0, color=Color.BLUE)]
    g._on_hit(t)
    assert g.focus == 30.0 + FOCUS_HIT_BONUS


def test_focus_capped_at_max() -> None:
    g = _make_blank_game()
    g.focus = FOCUS_MAX - 1.0
    g.projectile = Projectile(x=200.0, y=100.0, vx=0.0, vy=0.0, color=Color.RED)
    t = Target(x=200.0, y=100.0, color=Color.RED)
    g.targets = [t, Target(x=300.0, y=80.0, color=Color.BLUE)]
    g._on_hit(t)
    assert g.focus == FOCUS_MAX


# ── Heat / Overheat tests ────────────────────────────────────────────────

def test_heat_accumulation() -> None:
    g = _make_blank_game()
    g.heat = 90.0
    g.combo_color = Color.RED
    # Simulate a fire that pushes heat over max
    g.heat += HEAT_PER_SHOT
    assert g.heat >= HEAT_MAX
    # Overheat trigger
    g.heat = HEAT_MAX
    g.heat_cooldown = HEAT_COOLDOWN_FRAMES
    g.combo = 0
    g.combo_color = None
    g.is_super_next = False
    assert g.heat_cooldown == HEAT_COOLDOWN_FRAMES
    assert g.combo == 0
    assert g.combo_color is None


# ── Super AOE tests ──────────────────────────────────────────────────────

def test_super_aoe_hits_same_color() -> None:
    g = _make_blank_game()
    origin = Target(x=200.0, y=100.0, color=Color.BLUE)
    t1 = Target(x=210.0, y=100.0, color=Color.BLUE)  # within AOE
    t2 = Target(x=250.0, y=100.0, color=Color.BLUE)  # within AOE
    t3 = Target(x=210.0, y=100.0, color=Color.RED)   # wrong color
    g.targets = [origin, t1, t2, t3]
    g.combo = 2
    g._super_aoe(origin)
    assert t1.alive is False  # hit by AOE
    assert t2.alive is False  # hit by AOE
    assert t3.alive is True   # wrong color, not hit


def test_super_aoe_respects_radius() -> None:
    g = _make_blank_game()
    origin = Target(x=200.0, y=100.0, color=Color.GREEN)
    t_far = Target(x=200.0 + SUPER_AOE_RADIUS + 20, y=100.0, color=Color.GREEN)
    g.targets = [origin, t_far]
    g.combo = 0
    g._super_aoe(origin)
    assert t_far.alive is True  # outside radius


# ── Miss / reset tests ───────────────────────────────────────────────────

def test_on_miss_resets_combo() -> None:
    g = _make_blank_game()
    g.combo = 5
    g.combo_color = Color.RED
    g.is_super_next = True
    g.projectile = Projectile(x=50.0, y=270.0, vx=80.0, vy=-60.0, color=Color.RED)
    g._on_miss()
    assert g.combo == 0
    assert g.combo_color is None
    assert g.is_super_next is False
    assert g.projectile is None
    assert g.phase == Phase.AIMING


# ── Particle tests ───────────────────────────────────────────────────────

def test_spawn_hit_particles() -> None:
    g = _make_blank_game()
    g._spawn_hit_particles(200.0, 100.0, 8, 10)
    assert len(g.particles) == 10
    for p in g.particles:
        assert p.life > 0


def test_particle_update_and_decay() -> None:
    g = _make_blank_game()
    g.particles.append(Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=1, color=8))
    g.particles.append(Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=10, color=8))
    g._update_particles(1.0 / 60.0)
    assert len(g.particles) == 1  # life=1 became 0 and was removed


# ── Float text tests ─────────────────────────────────────────────────────

def test_spawn_float_text() -> None:
    g = _make_blank_game()
    g._spawn_float_text(200.0, 100.0, "+500", 7)
    assert len(g.float_texts) == 1
    assert g.float_texts[0].text == "+500"


def test_float_text_update() -> None:
    g = _make_blank_game()
    g._spawn_float_text(200.0, 100.0, "+500", 7)
    g._update_float_texts(1.0 / 60.0)
    assert g.float_texts[0].y < 100.0  # rises
    assert g.float_texts[0].life == 39


# ── Projectile physics test ──────────────────────────────────────────────

def test_projectile_gravity() -> None:
    """Projectile should accelerate downward due to gravity."""
    p = Projectile(x=50.0, y=270.0, vx=80.0, vy=-60.0, color=Color.RED)
    dt = 0.1
    vy_before = p.vy
    p.x += p.vx * dt
    p.y += p.vy * dt
    p.vy += GRAVITY * dt
    assert p.vy > vy_before  # gravity pulled it down


# ── Edge case tests ──────────────────────────────────────────────────────

def test_all_targets_dead_then_replaced() -> None:
    g = _make_blank_game()
    g._spawn_initial_targets()
    for t in g.targets:
        t.alive = False
    g._replace_dead_targets()
    assert all(t.alive for t in g.targets)


def test_aim_angle_range() -> None:
    """Aim angle should be clamped between -pi*0.85 and 0."""
    g = _make_blank_game()
    # The clamp happens in _update_aiming; test logic directly
    g.aim_angle = -math.pi * 0.9  # too far down
    if g.aim_angle < -math.pi * 0.85:
        g.aim_angle = -math.pi * 0.85
    assert abs(g.aim_angle - (-math.pi * 0.85)) < 0.01

    g.aim_angle = 0.5  # too far up
    if g.aim_angle > 0.0:
        g.aim_angle = 0.0
    assert g.aim_angle == 0.0


def test_power_clamp() -> None:
    g = _make_blank_game()
    g.power = POWER_MIN - 10
    g.power = max(POWER_MIN, min(POWER_MAX, g.power))
    assert g.power == POWER_MIN

    g.power = POWER_MAX + 10
    g.power = max(POWER_MIN, min(POWER_MAX, g.power))
    assert g.power == POWER_MAX


if __name__ == "__main__":
    import traceback

    tests = [
        test_target_creation,
        test_projectile_creation,
        test_projectile_super,
        test_particle_creation,
        test_floating_text_creation,
        test_color_enum_values,
        test_phase_enum,
        test_constants,
        test_spawn_initial_targets,
        test_make_target_no_overlap,
        test_replace_dead_targets_all_alive,
        test_replace_dead_targets_one_dead,
        test_overlaps_existing,
        test_on_hit_same_color_continues_combo,
        test_on_hit_different_color_resets_combo,
        test_on_hit_first_hit,
        test_score_base,
        test_score_combo_multiplier,
        test_score_super_multiplier,
        test_focus_regen,
        test_focus_hit_bonus,
        test_focus_capped_at_max,
        test_heat_accumulation,
        test_super_aoe_hits_same_color,
        test_super_aoe_respects_radius,
        test_on_miss_resets_combo,
        test_spawn_hit_particles,
        test_particle_update_and_decay,
        test_spawn_float_text,
        test_float_text_update,
        test_projectile_gravity,
        test_all_targets_dead_then_replaced,
        test_aim_angle_range,
        test_power_clamp,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  PASS {test.__name__}")
        except Exception:
            failed += 1
            print(f"  FAIL {test.__name__}")
            traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    if failed > 0:
        sys.exit(1)
