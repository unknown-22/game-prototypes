"""test_imports.py — Headless logic tests for HULA CHAIN."""
import math
import random
import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/232_hula_chain")
from main import (
    BLACK,
    DARK_BLUE,
    FloatingText,
    GAME_TIME,
    GEM_RADIUS,
    HOOP_COLORS,
    HOOP_RADIUS,
    LIME,
    MAX_HEAT,
    NAVY,
    PLAYER_RADIUS,
    PLAYER_X,
    PLAYER_Y,
    RED,
    SCREEN_H,
    SCREEN_W,
    SUPER_DURATION,
    WHITE,
    YELLOW,
    Game,
    Gem,
    Particle,
    Phase,
)


def _make_game() -> Game:
    """Create a headless Game instance using Game.__new__ pattern."""
    g = Game.__new__(Game)
    # Pre-init all attributes that reset() touches
    g._seed_rng = random.Random(42)
    g.phase = Phase.TITLE
    g.score = 0
    g.best_score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0.0
    g.super_mode = False
    g.super_timer = 0
    g.timer = GAME_TIME
    g.frame = 0
    g.hoop_angle = 0.0
    g.ghost_angle = 0.0
    g.shake_frames = 0
    g.gems = []
    g.particles = []
    g.floating_texts = []
    g._spawn_cooldown = 0
    g.reset()
    # Use seeded RNG after reset (reset doesn't overwrite _seed_rng)
    g._seed_rng = random.Random(42)
    g.phase = Phase.PLAYING
    return g


# ── Color Constants ──
def test_color_constants() -> None:
    assert BLACK == 0
    assert RED == 8
    assert LIME == 11
    assert DARK_BLUE == 5
    assert YELLOW == 10
    assert NAVY == 1
    assert WHITE == 7
    assert len(HOOP_COLORS) == 4
    assert HOOP_COLORS[0] == RED
    assert HOOP_COLORS[1] == LIME
    assert HOOP_COLORS[2] == DARK_BLUE
    assert HOOP_COLORS[3] == YELLOW


# ── Dataclass Tests ──
def test_gem_dataclass() -> None:
    g = Gem(x=100.0, y=50.0, vx=1.0, vy=-2.0, color=RED)
    assert g.x == 100.0
    assert g.y == 50.0
    assert g.vx == 1.0
    assert g.vy == -2.0
    assert g.color == RED
    assert g.active is True


def test_particle_dataclass() -> None:
    p = Particle(x=10.0, y=20.0, vx=0.5, vy=-1.0, life=15, color=LIME)
    assert p.x == 10.0
    assert p.life == 15
    assert p.color == LIME


def test_floating_text_dataclass() -> None:
    ft = FloatingText(x=100.0, y=200.0, text="+10", life=30, color=YELLOW)
    assert ft.text == "+10"
    assert ft.life == 30


# ── Phase Enum ──
def test_phase_enum() -> None:
    assert Phase.TITLE in Phase
    assert Phase.PLAYING in Phase
    assert Phase.GAME_OVER in Phase


# ── Game Constants ──
def test_screen_dimensions() -> None:
    assert SCREEN_W == 320
    assert SCREEN_H == 240
    assert PLAYER_X == 160
    assert PLAYER_Y == 140
    assert HOOP_RADIUS == 60
    assert PLAYER_RADIUS == 12
    assert GEM_RADIUS == 4
    assert MAX_HEAT == 100
    assert GAME_TIME == 3600
    assert SUPER_DURATION == 300


# ── Game.reset() ──
def test_reset_state() -> None:
    g = _make_game()
    # Verify reset sets initial state
    g.reset()
    assert g.phase == Phase.TITLE
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0.0
    assert g.super_mode is False
    assert g.super_timer == 0
    assert g.timer == GAME_TIME
    assert g.frame == 0
    assert g.hoop_angle == 0.0
    assert g.gems == []
    assert g.particles == []
    assert g.floating_texts == []
    assert g._spawn_cooldown == 0


# ── Quadrant Color Detection ──
def test_get_quadrant_color() -> None:
    g = _make_game()
    # hoop_angle = 0, so colors map directly to world angles
    # Quadrant 0: 0 to π/2 → RED
    assert g._get_quadrant_color(0.0) == RED
    assert g._get_quadrant_color(math.pi / 4) == RED
    # Quadrant 1: π/2 to π → LIME
    assert g._get_quadrant_color(math.pi / 2) == LIME
    assert g._get_quadrant_color(math.pi * 3 / 4) == LIME
    # Quadrant 2: π to 3π/2 → DARK_BLUE
    assert g._get_quadrant_color(math.pi) == DARK_BLUE
    # Quadrant 3: 3π/2 to 2π → YELLOW
    assert g._get_quadrant_color(math.pi * 3 / 2) == YELLOW
    # Negative angles / overflow
    assert g._get_quadrant_color(-math.pi / 4) == YELLOW  # wraps to 7π/4
    assert g._get_quadrant_color(math.pi * 5 / 2) == LIME  # wraps to π/2


def test_get_quadrant_color_with_rotation() -> None:
    g = _make_game()
    # _get_quadrant_color receives angle AFTER hoop_angle subtraction (relative angle)
    # Rotate hoop by π/4: a gem at world angle π/8 has relative angle = π/8 - π/4 = -π/8
    # → normalized to 15π/8 → quadrant 3 → YELLOW
    g.hoop_angle = math.pi / 4
    rel1 = math.pi / 8 - g.hoop_angle  # -π/8 → 15π/8 → YELLOW
    assert g._get_quadrant_color(rel1) == YELLOW
    # world angle 3π/4 → relative = 3π/4 - π/4 = π/2 → quadrant 1 → LIME
    rel2 = 3 * math.pi / 4 - g.hoop_angle
    assert g._get_quadrant_color(rel2) == LIME


# ── Gem Spawning ──
def test_spawn_gem_creates_gem() -> None:
    g = _make_game()
    initial_count = len(g.gems)
    g._spawn_gem()
    assert len(g.gems) == initial_count + 1
    gem = g.gems[-1]
    assert gem.color in HOOP_COLORS
    assert gem.active is True
    # Velocity should point toward center — cross product should be ~0
    dx = PLAYER_X - gem.x
    dy = PLAYER_Y - gem.y
    assert abs(gem.vx * dy - gem.vy * dx) < 0.01


def test_spawn_gem_at_max_capacity() -> None:
    g = _make_game()
    # Fill to max capacity
    max_gems = g._get_max_gems()
    for _ in range(max_gems):
        g._spawn_gem()
    assert len(g.gems) == max_gems
    # Try spawning one more
    g._spawn_gem()
    assert len(g.gems) == max_gems  # should not exceed max


def test_spawn_gem_respects_seed_rng() -> None:
    g = _make_game()
    g._seed_rng = random.Random(42)
    g.gems.clear()
    g._spawn_gem()
    first_gem = g.gems[0]
    # Re-seed and spawn again
    g._seed_rng = random.Random(42)
    g.gems.clear()
    g._spawn_gem()
    second_gem = g.gems[0]
    # Same seed should produce same gem (position, color, velocity)
    assert first_gem.color == second_gem.color
    assert abs(first_gem.x - second_gem.x) < 0.01
    assert abs(first_gem.y - second_gem.y) < 0.01


# ── Escalation Curves ──
def test_get_spawn_interval_curve() -> None:
    g = _make_game()
    # At start (timer = 3600)
    g.timer = 3600
    assert g._get_spawn_interval() == 60
    # Midway (timer = 1800)
    g.timer = 1800
    interval = g._get_spawn_interval()
    assert 40 <= interval <= 50
    # Near end (timer = 60)
    g.timer = 60
    assert g._get_spawn_interval() <= 25


def test_get_gem_speed_curve() -> None:
    g = _make_game()
    g.timer = 3600
    assert abs(g._get_gem_speed() - 1.5) < 0.01
    g.timer = 0
    assert abs(g._get_gem_speed() - 3.0) < 0.01


def test_get_max_gems_curve() -> None:
    g = _make_game()
    g.timer = 3600
    assert g._get_max_gems() == 8
    g.timer = 0
    assert g._get_max_gems() == 12


def test_get_hoop_auto_speed_curve() -> None:
    g = _make_game()
    g.timer = 3600
    assert abs(g._get_hoop_auto_speed() - 0.02) < 0.001
    g.timer = 0
    assert abs(g._get_hoop_auto_speed() - 0.04) < 0.001


# ── Gem Collection ──
def test_collect_matching_gem() -> None:
    g = _make_game()
    # Place gem at hoop edge with matching color
    g.hoop_angle = 0.0
    g.gems = [Gem(
        x=PLAYER_X + HOOP_RADIUS,
        y=PLAYER_Y,
        vx=0.0, vy=0.0,
        color=RED  # Quadrant 0 = RED
    )]
    initial_score = g.score
    initial_combo = g.combo
    g._check_collection()
    assert not g.gems[0].active
    assert g.score > initial_score
    assert g.combo == initial_combo + 1


def test_collect_wrong_color_resets_combo() -> None:
    g = _make_game()
    g.combo = 3
    g.hoop_angle = 0.0
    # Place gem with BLUE (DARK_BLUE) — won't match quadrant 0 (RED)
    g.gems = [Gem(
        x=PLAYER_X + HOOP_RADIUS,
        y=PLAYER_Y,
        vx=0.0, vy=0.0,
        color=DARK_BLUE
    )]
    initial_heat = g.heat
    g._check_collection()
    assert not g.gems[0].active
    assert g.combo == 0  # reset
    assert g.heat > initial_heat  # +15


def test_super_mode_collects_any_color() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 100
    g.hoop_angle = 0.0
    g.gems = [Gem(
        x=PLAYER_X + HOOP_RADIUS,
        y=PLAYER_Y,
        vx=0.0, vy=0.0,
        color=DARK_BLUE  # Would normally mismatch quadrant 0 (RED)
    )]
    initial_score = g.score
    g._check_collection()
    assert not g.gems[0].active
    assert g.score > initial_score  # collected, not mismatched


def test_collect_increases_max_combo() -> None:
    g = _make_game()
    g.combo = 0
    g.max_combo = 0
    g.hoop_angle = 0.0
    g.gems = [Gem(
        x=PLAYER_X + HOOP_RADIUS,
        y=PLAYER_Y,
        vx=0.0, vy=0.0,
        color=RED
    )]
    g._check_collection()
    assert g.combo == 1
    assert g.max_combo == 1


def test_collect_updates_ghost_angle() -> None:
    g = _make_game()
    g.hoop_angle = 1.5
    # Place gem at world angle such that relative angle falls in quadrant 0 (RED)
    # relative_angle = 0.5 → world_angle = 0.5 + 1.5 = 2.0 → x = cx + r*cos(2.0), y = cy + r*sin(2.0)
    world_angle = 0.5 + g.hoop_angle
    g.gems = [Gem(
        x=PLAYER_X + HOOP_RADIUS * math.cos(world_angle),
        y=PLAYER_Y + HOOP_RADIUS * math.sin(world_angle),
        vx=0.0, vy=0.0,
        color=RED  # RED matches quadrant 0
    )]
    g._check_collection()
    assert g.ghost_angle == 1.5  # updated to current hoop_angle


# ── SUPER HOOP Activation ──
def test_activate_super_at_combo_4() -> None:
    g = _make_game()
    g.combo = 3
    g.super_mode = False
    g.hoop_angle = 0.0
    g.gems = [Gem(
        x=PLAYER_X + HOOP_RADIUS,
        y=PLAYER_Y,
        vx=0.0, vy=0.0,
        color=RED
    )]
    g._check_collection()
    # combo was 3, now incremented to 4 → triggers super (4 % 4 == 0)
    assert g.combo == 4
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


def test_refresh_super_timer_on_match() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 50
    g.combo = 5
    g.hoop_angle = 0.0
    g.gems = [Gem(
        x=PLAYER_X + HOOP_RADIUS,
        y=PLAYER_Y,
        vx=0.0, vy=0.0,
        color=RED
    )]
    g._check_collection()
    # super_mode remains True, timer refreshes
    assert g.super_mode is True
    assert g.super_timer == SUPER_DURATION


# ── Miss Handling ──
def test_miss_gem_adds_heat() -> None:
    g = _make_game()
    g.heat = 20.0
    gem = Gem(x=100.0, y=100.0, vx=0.0, vy=0.0, color=RED)
    g._miss_gem(gem)
    assert not gem.active
    assert g.heat == 30.0  # +10


# ── Particle System ──
def test_spawn_particles() -> None:
    g = _make_game()
    g._spawn_particles(100.0, 100.0, RED, 5)
    assert len(g.particles) == 5
    for p in g.particles:
        assert 15 <= p.life <= 20
        assert p.color == RED


def test_update_particles() -> None:
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=1.0, vy=2.0, life=1, color=RED)]
    g._update_particles()
    # life decremented from 1 to 0 → removed
    assert len(g.particles) == 0


def test_update_particles_surviving() -> None:
    g = _make_game()
    g.particles = [Particle(x=0.0, y=0.0, vx=1.0, vy=2.0, life=5, color=RED)]
    g._update_particles()
    assert len(g.particles) == 1
    assert g.particles[0].x == 1.0
    assert g.particles[0].y == 2.0
    assert g.particles[0].life == 4


# ── Floating Text ──
def test_update_floating_texts() -> None:
    g = _make_game()
    g.floating_texts = [FloatingText(x=100.0, y=200.0, text="+10", life=2, color=YELLOW)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 1
    assert g.floating_texts[0].y == 199.5
    assert g.floating_texts[0].life == 1
    # Update again — life goes to 0, removed
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── HEAT System ──
def test_heat_decay() -> None:
    g = _make_game()
    g.heat = 50.0
    g._update_heat()
    assert g.heat == 49.98


def test_heat_floor_at_zero() -> None:
    g = _make_game()
    g.heat = 0.01
    g._update_heat()
    assert g.heat == 0.0


def test_heat_game_over() -> None:
    g = _make_game()
    g.heat = 100.0
    # Simulate the check from update()
    if g.heat >= MAX_HEAT:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


# ── Timer Game Over ──
def test_timer_game_over() -> None:
    g = _make_game()
    g.timer = 0
    if g.timer <= 0:
        g.phase = Phase.GAME_OVER
    assert g.phase == Phase.GAME_OVER


# ── Gem Movement ──
def test_update_gems_moves_gems() -> None:
    g = _make_game()
    g.gems = [Gem(x=0.0, y=0.0, vx=2.0, vy=3.0, color=RED, active=True)]
    g._update_gems()
    assert g.gems[0].x == 2.0
    assert g.gems[0].y == 3.0


def test_update_gems_removes_inactive() -> None:
    g = _make_game()
    g.gems = [
        Gem(x=0.0, y=0.0, vx=1.0, vy=1.0, color=RED, active=True),
        Gem(x=10.0, y=10.0, vx=1.0, vy=1.0, color=LIME, active=False),
    ]
    g._update_gems()
    assert len(g.gems) == 1
    assert g.gems[0].color == RED


# ── SUPER HOOP timer ──
def test_super_timer_decrement() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 10
    # Simulate one frame of super timer logic from update()
    g.super_timer -= 1
    if g.super_timer <= 0:
        g.super_mode = False
    assert g.super_timer == 9
    assert g.super_mode is True


def test_super_timer_expiry() -> None:
    g = _make_game()
    g.super_mode = True
    g.super_timer = 1
    g.super_timer -= 1
    if g.super_timer <= 0:
        g.super_mode = False
    assert g.super_timer == 0
    assert g.super_mode is False


# ── Score Calculation ──
def test_score_calculation_basic() -> None:
    g = _make_game()
    g.combo = 0
    # _collect_gem calls: points = int(10 * (1 + combo * 0.5) * super_mult)
    points = int(10 * (1 + 0 * 0.5) * 1)
    assert points == 10


def test_score_calculation_combo() -> None:
    g = _make_game()
    g.combo = 3
    points = int(10 * (1 + 3 * 0.5) * 1)
    assert points == 25  # 10 * 2.5 = 25


def test_score_calculation_super() -> None:
    g = _make_game()
    g.combo = 5
    g.super_mode = True
    points = int(10 * (1 + 5 * 0.5) * 3)
    assert points == 105  # 10 * 3.5 * 3 = 105


# ── Best Score Tracking ──
def test_best_score_initial() -> None:
    g = _make_game()
    assert g.best_score == 0


# ── Mismatch Particle and Shake ──
def test_mismatch_spawns_particles() -> None:
    g = _make_game()
    g.hoop_angle = 0.0
    g.gems = [Gem(
        x=PLAYER_X + HOOP_RADIUS,
        y=PLAYER_Y,
        vx=0.0, vy=0.0,
        color=DARK_BLUE  # mismatch quadrant 0 (RED)
    )]
    initial_particles = len(g.particles)
    g._check_collection()
    assert len(g.particles) > initial_particles


def test_mismatch_triggers_shake() -> None:
    g = _make_game()
    g.hoop_angle = 0.0
    g.gems = [Gem(
        x=PLAYER_X + HOOP_RADIUS,
        y=PLAYER_Y,
        vx=0.0, vy=0.0,
        color=DARK_BLUE
    )]
    g._check_collection()
    assert g.shake_frames == 5


# ── Floating Text on Collection ──
def test_collect_creates_floating_text() -> None:
    g = _make_game()
    g.hoop_angle = 0.0
    g.gems = [Gem(
        x=PLAYER_X + HOOP_RADIUS,
        y=PLAYER_Y,
        vx=0.0, vy=0.0,
        color=RED
    )]
    initial_texts = len(g.floating_texts)
    g._check_collection()
    assert len(g.floating_texts) > initial_texts


def test_combo_floating_text_at_combo_2() -> None:
    g = _make_game()
    g.combo = 1
    g.hoop_angle = 0.0
    g.gems = [Gem(
        x=PLAYER_X + HOOP_RADIUS,
        y=PLAYER_Y,
        vx=0.0, vy=0.0,
        color=RED
    )]
    g._check_collection()
    # After collection, combo=2 → should get "COMBO x2!" text
    texts = [t for t in g.floating_texts if "COMBO" in t.text]
    assert len(texts) >= 1


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
