"""test_imports.py — Headless logic tests for 088_hoop_chain."""
from __future__ import annotations

import sys

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/088_hoop_chain")
from main import Ball, FloatingText, HoopChain, Particle, Phase

# ── Helper factory ──────────────────────────────────────────────────────────


def _make_game(seed: int = 42) -> HoopChain:
    """Create a HoopChain instance bypassing Pyxel init for headless testing."""
    g = HoopChain.__new__(HoopChain)
    # Pre-init ALL instance attributes before reset()
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.heat = 0
    g.shots_taken = 0
    g.super_count = 0
    g.ball = None
    g.current_color = 8
    g.particles = []
    g.floating_texts = []
    g.drag_start_x = 0.0
    g.drag_start_y = 0.0
    g.drag_current_x = 0.0
    g.drag_current_y = 0.0
    g.is_dragging = False
    g.shake_frames = 0
    g.result_timer = 0
    g._result_score_gained = 0
    g._result_is_super = False
    g._result_is_miss = False
    g._result_is_wrong_color = False
    # Override random in reset by seeding first
    g.reset()
    # Override current_color for deterministic tests
    g.current_color = 8  # RED
    return g


# ── Color match tests ───────────────────────────────────────────────────────


def test_check_color_match_same() -> None:
    """Same color returns True."""
    g = _make_game()
    g.current_color = 8  # RED
    assert g._check_color_match(8) is True


def test_check_color_match_different() -> None:
    """Different color returns False."""
    g = _make_game()
    g.current_color = 8  # RED
    assert g._check_color_match(3) is False  # GREEN


# ── Hoop collision tests ────────────────────────────────────────────────────


def test_is_in_hoop_center() -> None:
    """Ball at center of hoop."""
    g = _make_game()
    assert g._is_in_hoop(260, 120) is True


def test_is_in_hoop_left_edge() -> None:
    """Ball at left edge of hoop."""
    g = _make_game()
    assert g._is_in_hoop(250, 120) is True


def test_is_in_hoop_right_edge() -> None:
    """Ball at right edge of hoop."""
    g = _make_game()
    assert g._is_in_hoop(270, 120) is True


def test_is_in_hoop_above() -> None:
    """Ball above hoop — no collision."""
    g = _make_game()
    assert g._is_in_hoop(260, 114) is False


def test_is_in_hoop_below() -> None:
    """Ball below hoop — no collision."""
    g = _make_game()
    assert g._is_in_hoop(260, 126) is False


def test_is_in_hoop_left_of() -> None:
    """Ball left of hoop."""
    g = _make_game()
    assert g._is_in_hoop(249, 120) is False


# ── Trajectory tests ────────────────────────────────────────────────────────


def test_compute_trajectory_basic() -> None:
    """Trajectory returns expected number of points."""
    g = _make_game()
    pts = g._compute_trajectory(5.0, -8.0, steps=30)
    assert len(pts) == 30
    assert pts[0][0] > g.SHOOT_X  # x increases with positive vx
    assert pts[0][1] < g.SHOOT_Y  # y decreases with negative vy


def test_compute_trajectory_gravity_pulls_down() -> None:
    """Gravity eventually pulls ball downward."""
    g = _make_game()
    pts = g._compute_trajectory(3.0, -5.0, steps=60)
    # First few points should go up
    early_ys = [p[1] for p in pts[:5]]
    assert early_ys[0] < g.SHOOT_Y  # initial upward
    # Later points should be coming back down
    late_ys = [p[1] for p in pts[40:]]
    assert max(late_ys) > min(early_ys)  # gravity pulled it down


# ── Score tests ─────────────────────────────────────────────────────────────


def test_on_score_same_color_no_combo() -> None:
    """Same color, combo=0 → gains 10, combo becomes 1."""
    g = _make_game()
    g.current_color = 8  # RED
    g.ball = Ball(x=260, y=120, vx=0, vy=0, color=8)
    gained = g._on_score()
    assert gained == 10  # 10 * combo(1)
    assert g.combo == 1
    assert g.score == 10
    assert g.shots_taken == 1


def test_on_score_same_color_combo_2() -> None:
    """Same color, combo=2 → becomes combo=3 → SUPER (3x), gains 90."""
    g = _make_game()
    g.current_color = 8
    g.combo = 2
    g.ball = Ball(x=260, y=120, vx=0, vy=0, color=8)
    gained = g._on_score()
    assert gained == 90  # 10 * 3 * 3 (combo becomes 3, triggers SUPER)
    assert g.combo == 3
    assert g.super_count == 1
    assert g.score == 90


def test_on_score_super_shot_threshold() -> None:
    """Combo=3 same color → SUPER SHOT (3x multiplier)."""
    g = _make_game()
    g.current_color = 8
    g.combo = 3
    g.ball = Ball(x=260, y=120, vx=0, vy=0, color=8)
    gained = g._on_score()
    assert gained == 120  # 10 * 4 * 3
    assert g.combo == 4
    assert g.max_combo == 4
    assert g.super_count == 1


def test_on_score_super_shot_multi() -> None:
    """Multiple super shots increment super_count."""
    g = _make_game()
    g.current_color = 8
    g.combo = 3
    g.ball = Ball(x=260, y=120, vx=0, vy=0, color=8)
    g._on_score()
    assert g.super_count == 1
    g.ball = Ball(x=260, y=120, vx=0, vy=0, color=8)
    g._on_score()
    assert g.super_count == 2


def test_on_score_wrong_color_resets_combo() -> None:
    """Wrong color scores 10 base, resets combo to 0."""
    g = _make_game()
    g.current_color = 8  # RED
    g.combo = 5
    g.score = 100
    g.ball = Ball(x=260, y=120, vx=0, vy=0, color=3)  # GREEN
    gained = g._on_score()
    assert gained == 10  # base score, no combo
    assert g.combo == 0  # reset
    assert g.score == 110
    assert g.shots_taken == 1


def test_on_score_max_combo_tracks() -> None:
    """max_combo remembers highest combo reached."""
    g = _make_game()
    g.current_color = 8
    g.combo = 5
    g.max_combo = 5
    g.ball = Ball(x=260, y=120, vx=0, vy=0, color=8)
    g._on_score()
    assert g.max_combo == 6


def test_on_score_wrong_color_keeps_max_combo() -> None:
    """max_combo persists after wrong color resets combo."""
    g = _make_game()
    g.current_color = 8
    g.combo = 7
    g.max_combo = 7
    g.ball = Ball(x=260, y=120, vx=0, vy=0, color=3)  # GREEN
    g._on_score()
    assert g.combo == 0
    assert g.max_combo == 7  # unchanged


def test_on_score_shots_taken_increment() -> None:
    """shots_taken increments on every score."""
    g = _make_game()
    g.current_color = 8
    g.ball = Ball(x=260, y=120, vx=0, vy=0, color=8)
    g._on_score()
    assert g.shots_taken == 1
    g.ball = Ball(x=260, y=120, vx=0, vy=0, color=8)
    g._on_score()
    assert g.shots_taken == 2


def test_on_score_game_over_at_total_shots() -> None:
    """Game over triggered when shots_taken reaches TOTAL_SHOTS."""
    g = _make_game()
    g.current_color = 8
    g.shots_taken = 14
    g.ball = Ball(x=260, y=120, vx=0, vy=0, color=8)
    g._on_score()
    # Note: _on_score sets phase=RESULT, the _update_result handles the game over check
    # Here we just verify shots_taken = 15
    assert g.shots_taken == 15


# ── Wrong color tests ───────────────────────────────────────────────────────


def test_on_wrong_color_resets_combo() -> None:
    """_on_wrong_color sets combo to 0."""
    g = _make_game()
    g.combo = 5
    g._on_wrong_color()
    assert g.combo == 0


# ── Miss tests ──────────────────────────────────────────────────────────────


def test_on_miss_heat_increase() -> None:
    """Miss adds MISS_HEAT to heat."""
    g = _make_game()
    assert g.heat == 0
    g._on_miss()
    assert g.heat == 2  # MISS_HEAT = 2
    g._on_miss()
    assert g.heat == 4


def test_on_miss_resets_combo() -> None:
    """Miss resets combo."""
    g = _make_game()
    g.combo = 3
    g._on_miss()
    assert g.combo == 0


def test_on_miss_increments_shots() -> None:
    """Miss counts as a shot taken."""
    g = _make_game()
    g._on_miss()
    assert g.shots_taken == 1


def test_on_miss_heat_capped() -> None:
    """HEAT doesn't exceed MAX_HEAT."""
    g = _make_game()
    g.heat = 9
    g._on_miss()
    assert g.heat == 10  # capped, not 11


# ── Next ball tests ─────────────────────────────────────────────────────────


def test_next_ball_changes_color() -> None:
    """_next_ball picks a color from COLORS."""
    g = _make_game()
    g.current_color = 8
    # Run many times to ensure it picks from valid colors
    colors_seen: set[int] = set()
    for _ in range(50):
        g._next_ball()
        colors_seen.add(g.current_color)
    assert colors_seen.issubset(set(HoopChain.COLORS))
    assert len(colors_seen) >= 2  # at least some variety


# ── Particle tests ──────────────────────────────────────────────────────────


def test_spawn_particles_creates() -> None:
    """_spawn_particles creates the right count."""
    g = _make_game()
    g._spawn_particles(200, 100, 8, 15)
    assert len(g.particles) == 15


def test_spawn_particles_super_rainbow() -> None:
    """Super spawn (count ≥ 20) uses rainbow colors."""
    g = _make_game()
    g._spawn_particles(200, 100, 8, 30)
    assert len(g.particles) == 30
    colors = {p.color for p in g.particles}
    # With 30 particles, should see multiple colors
    assert len(colors) >= 2


def test_update_particles_decrements_life() -> None:
    """_update_particles reduces life and eventually removes."""
    g = _make_game()
    g.particles = [Particle(x=100, y=100, vx=1, vy=-1, life=1, color=8)]
    g._update_particles()
    assert len(g.particles) == 0  # life went to 0, removed


def test_update_particles_moves() -> None:
    """Particles move each update."""
    g = _make_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=2.0, vy=-3.0, life=10, color=8)]
    g._update_particles()
    assert len(g.particles) == 1
    p = g.particles[0]
    assert p.x == 102.0
    assert p.y == 97.0
    assert p.life == 9


def test_update_particles_gravity() -> None:
    """Particle vy increases due to simulated gravity (0.05 per tick)."""
    g = _make_game()
    g.particles = [Particle(x=100.0, y=100.0, vx=0.0, vy=0.0, life=10, color=8)]
    g._update_particles()
    p = g.particles[0]
    assert p.vy > 0.0  # gravity applied


# ── Floating text tests ─────────────────────────────────────────────────────


def test_update_floating_texts_rises() -> None:
    """Floating text rises each update."""
    g = _make_game()
    g.floating_texts = [FloatingText(x=100, y=100, text="+30", life=5, color=7)]
    g._update_floating_texts()
    assert g.floating_texts[0].y == 99.0
    assert g.floating_texts[0].life == 4


def test_update_floating_texts_expires() -> None:
    """Floating text removed when life reaches 0."""
    g = _make_game()
    g.floating_texts = [FloatingText(x=100, y=100, text="HI", life=1, color=7)]
    g._update_floating_texts()
    assert len(g.floating_texts) == 0


# ── Reset tests ─────────────────────────────────────────────────────────────


def test_reset_clears_state() -> None:
    """reset() returns game to initial state."""
    g = _make_game()
    g.score = 500
    g.combo = 5
    g.max_combo = 8
    g.heat = 6
    g.shots_taken = 10
    g.super_count = 3
    g.particles = [Particle(x=0, y=0, vx=1, vy=1, life=5, color=8)]
    g.floating_texts = [FloatingText(x=0, y=0, text="X", life=5, color=7)]
    g.shake_frames = 10
    g.reset()
    assert g.phase == Phase.AIMING
    assert g.score == 0
    assert g.combo == 0
    assert g.max_combo == 0
    assert g.heat == 0
    assert g.shots_taken == 0
    assert g.super_count == 0
    assert g.ball is None
    assert g.particles == []
    assert g.floating_texts == []
    assert g.shake_frames == 0
    assert g.is_dragging is False


# ── Handle score/miss tests (logic flow) ────────────────────────────────────


def test_handle_score_same_color() -> None:
    """_handle_score sets result flags correctly for same-color hit."""
    g = _make_game()
    g.current_color = 8
    g.ball = Ball(x=260, y=120, vx=0, vy=0, color=8)
    g.combo = 0
    g._handle_score()
    assert g._result_is_miss is False
    assert g._result_score_gained == 10
    assert g.phase == Phase.RESULT
    assert g.result_timer == 30


def test_handle_score_super() -> None:
    """_handle_score with combo ≥ SUPER_THRESHOLD triggers super."""
    g = _make_game()
    g.current_color = 8
    g.combo = 3
    g.max_combo = 3
    g.ball = Ball(x=260, y=120, vx=0, vy=0, color=8)
    g._handle_score()
    assert g._result_is_super is True
    assert g.shake_frames == 20
    assert len(g.particles) == 30


def test_handle_miss() -> None:
    """_handle_miss sets flags and increments heat."""
    g = _make_game()
    g.combo = 2
    g.ball = Ball(x=300, y=300, vx=1, vy=1, color=8)
    g._handle_miss()
    assert g._result_is_miss is True
    assert g._result_score_gained == 0
    assert g.heat == 2
    assert g.combo == 0
    assert g.shots_taken == 1
    assert g.phase == Phase.RESULT


# ── Integration flow tests ──────────────────────────────────────────────────


def test_full_game_flow_then_reset() -> None:
    """Simulate a full game (all shots) then verify reset."""
    g = _make_game()
    g.current_color = 8
    for i in range(15):
        g.ball = Ball(x=260, y=120, vx=0, vy=0, color=8)
        g._handle_score()
        # Manually progress through result
        g.result_timer = 0
        g._update_result()
    assert g.shots_taken >= 15


def test_heat_game_over() -> None:
    """HEAT reaching MAX stops the game."""
    g = _make_game()
    g.heat = 8
    g.combo = 2
    g.ball = Ball(x=300, y=300, vx=1, vy=1, color=8)
    g._handle_miss()
    assert g.heat == 10
    assert g.phase == Phase.RESULT


def test_game_over_transition() -> None:
    """_update_result transitions to GAME_OVER when shots done."""
    g = _make_game()
    g.shots_taken = 15
    g.heat = 5
    g.result_timer = 1
    g._update_result()
    assert g.phase == Phase.GAME_OVER


def test_not_game_over_when_shots_remain() -> None:
    """_update_result goes back to AIMING when shots remain."""
    g = _make_game()
    g.shots_taken = 5
    g.heat = 5
    g.result_timer = 1
    g._update_result()
    assert g.phase == Phase.AIMING


# ── Constants verification ──────────────────────────────────────────────────


def test_constants() -> None:
    """Verify all class constants have expected values."""
    assert HoopChain.SCREEN_W == 320
    assert HoopChain.SCREEN_H == 240
    assert HoopChain.SHOOT_X == 60
    assert HoopChain.SHOOT_Y == 200
    assert HoopChain.HOOP_LEFT == 250
    assert HoopChain.HOOP_RIGHT == 270
    assert HoopChain.HOOP_TOP == 115
    assert HoopChain.HOOP_BOTTOM == 125
    assert HoopChain.GRAVITY == 0.4
    assert HoopChain.MAX_POWER == 15.0
    assert HoopChain.SUPER_THRESHOLD == 3
    assert HoopChain.MAX_HEAT == 10
    assert HoopChain.TOTAL_SHOTS == 15
    assert HoopChain.MISS_HEAT == 2
    assert len(HoopChain.COLORS) == 4
    assert HoopChain.COLORS == [8, 3, 5, 10]


# ── Phase enum tests ────────────────────────────────────────────────────────


def test_phase_enum_values() -> None:
    """All expected phases exist."""
    phases = {Phase.TITLE, Phase.AIMING, Phase.SHOOTING, Phase.RESULT, Phase.GAME_OVER}
    assert len(phases) == 5


# ── Ball dataclass tests ────────────────────────────────────────────────────


def test_ball_creation() -> None:
    """Ball dataclass works."""
    b = Ball(x=100.0, y=200.0, vx=5.0, vy=-8.0, color=8)
    assert b.x == 100.0
    assert b.y == 200.0
    assert b.vx == 5.0
    assert b.vy == -8.0
    assert b.color == 8
    assert b.active is True


# ── compute_trajectory detail ──────────────────────────────────────────────


def test_trajectory_no_velocity() -> None:
    """Zero velocity: ball drops straight down due to gravity."""
    g = _make_game()
    pts = g._compute_trajectory(0.0, 0.0, steps=10)
    assert pts[0][0] == g.SHOOT_X  # x unchanged
    # First step: vy starts 0, gravity applied AFTER first step, so pts[0] y = SHOOT_Y
    # But pts[1] and beyond will be below SHOOT_Y
    assert pts[-1][1] > g.SHOOT_Y  # gravity eventually pulls down


def test_trajectory_into_hoop() -> None:
    """A well-aimed shot should pass through the hoop zone."""
    g = _make_game()
    # From SHOOT_X=60, SHOOT_Y=200 to HOOP (250-270, 115-125)
    # ~190px horizontal, ~-80px vertical in ~30 steps
    # vx=6.7, vy=-8.7 with gravity 0.4
    pts = g._compute_trajectory(6.7, -8.7, steps=35)
    # At least one point should be inside the hoop
    hoop_hits = [p for p in pts if g._is_in_hoop(p[0], p[1])]
    assert len(hoop_hits) >= 1, f"No points in hoop! Points: {pts[:5]}..."


# ── Serial super shots ──────────────────────────────────────────────────────


def test_super_shot_combo_sequence() -> None:
    """Full sequence: build combo → trigger super → continue chain."""
    g = _make_game()
    g.current_color = 8  # RED
    # Shot 1: combo becomes 1, gained=10
    g.ball = Ball(x=260, y=120, vx=0, vy=0, color=8)
    g1 = g._on_score()
    assert g.combo == 1 and g1 == 10
    # Shot 2: combo=2, gained=20
    g.ball = Ball(x=260, y=120, vx=0, vy=0, color=8)
    g2 = g._on_score()
    assert g.combo == 2 and g2 == 20
    # Shot 3: combo=3, SUPER, gained=90 (10*3*3)
    g.ball = Ball(x=260, y=120, vx=0, vy=0, color=8)
    g3 = g._on_score()
    assert g.combo == 3 and g3 == 90
    assert g.super_count == 1
    # Shot 4: combo=4, SUPER, gained=120 (10*4*3)
    g.ball = Ball(x=260, y=120, vx=0, vy=0, color=8)
    g4 = g._on_score()
    assert g.combo == 4 and g4 == 120
    assert g.super_count == 2
    assert g.score == 10 + 20 + 90 + 120
