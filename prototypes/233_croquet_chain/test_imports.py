"""test_imports.py -- Headless logic tests for CROQUET CHAIN."""
from __future__ import annotations

import random
import sys
import traceback
import unittest.mock as mock

# Mock pyxel before importing main
mock_pyxel = mock.MagicMock()
mock_pyxel.COLOR_BLACK = 0
mock_pyxel.COLOR_NAVY = 1
mock_pyxel.COLOR_PURPLE = 2
mock_pyxel.COLOR_GREEN = 3
mock_pyxel.COLOR_BROWN = 4
mock_pyxel.COLOR_DARK_BLUE = 5
mock_pyxel.COLOR_LIGHT_BLUE = 6
mock_pyxel.COLOR_WHITE = 7
mock_pyxel.COLOR_RED = 8
mock_pyxel.COLOR_ORANGE = 9
mock_pyxel.COLOR_YELLOW = 10
mock_pyxel.COLOR_LIME = 11
mock_pyxel.COLOR_CYAN = 12
mock_pyxel.COLOR_GRAY = 13
mock_pyxel.COLOR_PINK = 14
mock_pyxel.COLOR_PEACH = 15
mock_pyxel.MOUSE_BUTTON_LEFT = 0
mock_pyxel.MOUSE_BUTTON_RIGHT = 1
mock_pyxel.MOUSE_BUTTON_MIDDLE = 2
mock_pyxel.KEY_SPACE = 8
mock_pyxel.KEY_RETURN = 9
mock_pyxel.btnp = mock.MagicMock(return_value=False)
mock_pyxel.btnr = mock.MagicMock(return_value=False)
mock_pyxel.btn = mock.MagicMock(return_value=False)
mock_pyxel.frame_count = 0
mock_pyxel.mouse_x = 0
mock_pyxel.mouse_y = 0
sys.modules["pyxel"] = mock_pyxel

sys.path.insert(0, "/home/unknown22/repos/game-prototypes/prototypes/233_croquet_chain")

from main import (  # noqa: E402
    Game, Phase, Ball, Wicket, Particle,
    WHITE, RED, LIME, BALL_COLORS, FIELD_LEFT, FIELD_TOP, FIELD_RIGHT, SUPER_DURATION, SUPER_COMBO_THRESHOLD,
    GAME_DURATION, HEAT_WRONG_WICKET, HEAT_BOUNDARY, HEAT_DECAY,
)


def _make_game(seed: int = 42) -> Game:
    g = Game.__new__(Game)
    g.phase = Phase.TITLE
    g.score = 0
    g.combo = 0
    g.max_combo = 0
    g.best_combo = 0
    g.heat = 0.0
    g.timer = GAME_DURATION
    g.super_timer = 0
    g.aim_start_x = 0.0
    g.aim_start_y = 0.0
    g.cue_ball = Ball(160.0, 210.0, radius=6, color=WHITE)
    g.balls = []
    g.wickets = []
    g.particles = []
    g.ghost_trail = []
    g.shot_trail = []
    g.spawn_timer = 0
    g.wicket_move_timer = 0
    g.dragging = False
    g.rng = random.Random(seed)
    return g


def _make_playing(seed: int = 42) -> Game:
    g = _make_game(seed)
    g._start_game()
    return g


# ---- 1. Shoot cue ball sets velocity ----
def test_shoot_cue_ball_sets_velocity() -> None:
    g = _make_game()
    g._start_game()
    g._shoot_cue_ball(100.0, 0.0, 100.0)
    assert g.cue_ball.vx > 0.0
    assert abs(g.cue_ball.vy) < 0.001


# ---- 2. Shoot cue ball ignores zero power ----
def test_shoot_cue_ball_zero_power() -> None:
    g = _make_game()
    g._start_game()
    g._shoot_cue_ball(10.0, 0.0, 1.0)
    assert g.cue_ball.vx == 0.0
    assert g.cue_ball.vy == 0.0


# ---- 3. Physics: move and apply friction ----
def test_update_physics_movement_and_friction() -> None:
    g = _make_game()
    g._start_game()
    g.cue_ball.vx = 10.0
    g.cue_ball.vy = 0.0
    orig_x = g.cue_ball.x
    g._update_physics()
    assert g.cue_ball.x > orig_x
    assert g.cue_ball.vx < 10.0


# ---- 4. Physics: ball stops at low speed ----
def test_ball_stopping_detection() -> None:
    b1 = Ball(0.0, 0.0, vx=0.05, vy=0.0)
    b2 = Ball(0.0, 0.0, vx=0.5, vy=0.0)
    assert Game._ball_stopping(b1) is True
    assert Game._ball_stopping(b2) is False


# ---- 5. All stopped detection ----
def test_all_stopped() -> None:
    g = _make_game()
    g._start_game()
    g.cue_ball.vx = 0.0
    g.cue_ball.vy = 0.0
    for b in g.balls:
        b.vx = 0.0
        b.vy = 0.0
    assert g._all_stopped() is True

    g.cue_ball.vx = 5.0
    assert g._all_stopped() is False


# ---- 6. Ball collision: elastic transfer ----
def test_check_collisions_elastic() -> None:
    g = _make_game()
    g._start_game()
    a = g.cue_ball
    b = g.balls[0]
    a.x, a.y = 100.0, 100.0
    b.x, b.y = 110.0, 100.0
    a.vx = 5.0
    a.vy = 0.0
    b.vx = 0.0
    b.vy = 0.0
    a.radius = 6
    b.radius = 6
    g._check_collisions()
    # Cue ball should slow down, target should speed up
    assert b.vx > 0.0
    assert a.vx < 5.0


# ---- 7. Ball collision: separated balls no collision ----
def test_check_collisions_separated() -> None:
    g = _make_game()
    g._start_game()
    a = g.cue_ball
    b = g.balls[0]
    a.x, a.y = 100.0, 100.0
    b.x, b.y = 200.0, 200.0
    a.vx = 5.0
    a.vy = 0.0
    b.vx = 5.0
    b.vy = 0.0
    old_b_vx = b.vx
    g._check_collisions()
    assert b.vx == old_b_vx


# ---- 8. Wicket pass: ball centered in gate ----
def test_check_wicket_pass_centered() -> None:
    g = _make_game()
    ball = Ball(50.0, 50.0, radius=6, color=RED)
    wicket = Wicket(50.0, 50.0, color=RED)
    assert g._check_wicket_pass(ball, wicket) is True


# ---- 9. Wicket pass: ball outside gate horizontally ----
def test_check_wicket_pass_outside() -> None:
    g = _make_game()
    ball = Ball(80.0, 50.0, radius=6, color=RED)
    wicket = Wicket(50.0, 50.0, color=RED)
    assert g._check_wicket_pass(ball, wicket) is False


# ---- 10. Wicket pass: already scored returns false ----
def test_check_wicket_pass_already_scored() -> None:
    g = _make_game()
    ball = Ball(50.0, 50.0, radius=6, color=RED)
    wicket = Wicket(50.0, 50.0, color=RED, scored=True)
    assert g._check_wicket_pass(ball, wicket) is False


# ---- 11. Handle wicket score: matching color increases combo ----
def test_handle_wicket_score_match() -> None:
    g = _make_game()
    g._start_game()
    g.combo = 2
    g.score = 50
    ball = Ball(100.0, 50.0, radius=6, color=RED)
    wicket = Wicket(100.0, 50.0, color=RED)
    g._handle_wicket_score(ball, wicket)
    assert g.combo == 3
    assert g.score == 50 + int(10 * 3 * 1.0)
    assert wicket.scored is True


# ---- 12. Handle wicket score: mismatch resets combo, adds heat ----
def test_handle_wicket_score_mismatch() -> None:
    g = _make_game()
    g._start_game()
    g.combo = 3
    g.heat = 20.0
    ball = Ball(100.0, 50.0, radius=6, color=RED)
    wicket = Wicket(100.0, 50.0, color=LIME)
    g._handle_wicket_score(ball, wicket)
    assert g.combo == 0
    assert g.heat == 20.0 + HEAT_WRONG_WICKET
    assert wicket.scored is True


# ---- 13. Super activation at combo threshold ----
def test_super_activation_at_threshold() -> None:
    g = _make_game()
    g._start_game()
    g.combo = SUPER_COMBO_THRESHOLD - 1  # 3
    ball = Ball(100.0, 50.0, radius=6, color=RED)
    wicket = Wicket(100.0, 50.0, color=RED)
    g._handle_wicket_score(ball, wicket)
    assert g.combo == SUPER_COMBO_THRESHOLD  # 4
    assert g.super_timer == SUPER_DURATION


# ---- 14. Super mode: any color matches ----
def test_super_any_color_match() -> None:
    g = _make_game()
    g._start_game()
    g.super_timer = 100
    g.combo = 1
    g.score = 100
    ball = Ball(100.0, 50.0, radius=6, color=LIME)
    wicket = Wicket(100.0, 50.0, color=RED)
    g._handle_wicket_score(ball, wicket)
    assert g.combo == 2
    assert g.score > 100


# ---- 15. Super mode: 3x score multiplier ----
def test_super_score_multiplier() -> None:
    g = _make_game()
    g._start_game()
    g.super_timer = 100
    g.combo = 1
    g.score = 0
    ball = Ball(100.0, 50.0, radius=6, color=RED)
    wicket = Wicket(100.0, 50.0, color=RED)
    g._handle_wicket_score(ball, wicket)
    assert g.score == int(10 * 2 * 3.0)


# ---- 16. Timer decrements ----
def test_timer_decrements() -> None:
    g = _make_game()
    g._start_game()
    g.timer = 100
    g._update_timer()
    assert g.timer == 99


# ---- 17. Timer at zero triggers game over ----
def test_timer_zero_game_over() -> None:
    g = _make_game()
    g._start_game()
    g.timer = 1
    g._update_timer()
    assert g.timer == 0
    assert g.phase == Phase.GAME_OVER


# ---- 18. Heat decay ----
def test_heat_decay() -> None:
    g = _make_game()
    g._start_game()
    g.heat = 50.0
    # Simulate AIMING update's heat decay
    g.heat = max(0.0, g.heat - HEAT_DECAY)
    assert g.heat < 50.0
    assert g.heat > 49.0


# ---- 19. Heat clamped at zero ----
def test_heat_not_negative() -> None:
    g = _make_game()
    g._start_game()
    g.heat = 0.0
    g.heat = max(0.0, g.heat - HEAT_DECAY)
    assert g.heat == 0.0


# ---- 20. Heat wall bounce penalty ----
def test_heat_boundary_penalty() -> None:
    g = _make_game()
    g._start_game()
    g.heat = 10.0
    ball = g.balls[0]
    ball.x = FIELD_LEFT - 10
    ball.y = 100.0
    ball.vx = -5.0
    ball.vy = 0.0
    g._update_physics()
    assert g.heat > 10.0


# ---- 21. Heat clamped at 100 ----
def test_heat_max_clamped() -> None:
    g = _make_game()
    g._start_game()
    g.heat = 140.0
    # heat boundary add uses min(100, ...)
    g.heat = min(100.0, g.heat + HEAT_BOUNDARY)
    assert g.heat == 100.0


# ---- 22. Max combo tracking ----
def test_max_combo_tracks_highest() -> None:
    g = _make_game()
    g._start_game()
    g.combo = 3
    ball = Ball(100.0, 50.0, radius=6, color=RED)
    wicket = Wicket(100.0, 50.0, color=RED)
    g._handle_wicket_score(ball, wicket)
    assert g.max_combo == 4
    assert g.combo == 4


# ---- 23. Best combo saved on game over ----
def test_best_combo_on_game_over() -> None:
    g = _make_game()
    g._start_game()
    g.combo = 7
    g.best_combo = 3
    g.timer = 1
    g._update_timer()
    assert g.phase == Phase.GAME_OVER
    assert g.best_combo == 7


# ---- 24. Ghost trail captures cue ball path ----
def test_ghost_trail_saved_on_successful_shot() -> None:
    g = _make_game()
    g._start_game()
    g.combo = 1
    g.shot_trail = [(160.0, 210.0), (165.0, 200.0), (170.0, 190.0)]
    g.ghost_trail = []
    g._resolve_shot()
    assert len(g.ghost_trail) == 3


# ---- 25. Ghost trail empty if no combo ----
def test_ghost_trail_not_saved_on_no_combo() -> None:
    g = _make_game()
    g._start_game()
    g.combo = 0
    g.shot_trail = [(160.0, 210.0), (165.0, 200.0)]
    g.ghost_trail = [(150.0, 180.0)]  # old trail
    g._resolve_shot()
    assert len(g.ghost_trail) == 1  # old trail preserved


# ---- 26. Ghost trail downsamples to max points ----
def test_ghost_trail_downsamples() -> None:
    g = _make_game()
    g._start_game()
    g.combo = 1
    from main import MAX_GHOST_POINTS
    g.shot_trail = [(float(i), float(i)) for i in range(200)]
    g._resolve_shot()
    assert len(g.ghost_trail) == MAX_GHOST_POINTS


# ---- 27. Resolve shot resets cue ball position ----
def test_resolve_shot_resets_cue_ball() -> None:
    g = _make_game()
    g._start_game()
    g.cue_ball.x = 200.0
    g.cue_ball.y = 180.0
    g.cue_ball.vx = 3.0
    g.cue_ball.vy = 2.0
    g._resolve_shot()
    assert g.cue_ball.x == 160.0
    assert g.cue_ball.y == 210.0
    assert g.cue_ball.vx == 0.0
    assert g.cue_ball.vy == 0.0
    assert g.phase == Phase.AIMING


# ---- 28. Spawn particles creates particles ----
def test_spawn_particles() -> None:
    g = _make_game()
    g._start_game()
    g._spawn_particles(100.0, 100.0, RED, 8)
    assert len(g.particles) == 8
    assert all(p.life > 0 for p in g.particles)


# ---- 29. Particles update and expire ----
def test_particles_update_and_expire() -> None:
    g = _make_game()
    g._start_game()
    g.particles = [
        Particle(0.0, 0.0, 1.0, 0.0, life=1, color=WHITE),
        Particle(0.0, 0.0, 1.0, 0.0, life=3, color=WHITE),
    ]
    g._update_particles()
    # First should be dead (life became 0), second alive
    assert len(g.particles) == 1
    assert g.particles[0].life == 2


# ---- 30. Spawn balls creates 4 balls ----
def test_spawn_balls_creates_four() -> None:
    g = _make_game()
    g._start_game()
    assert len(g.balls) == 4
    for b in g.balls:
        assert b.color in BALL_COLORS


# ---- 31. Spawn wickets creates 4 wickets ----
def test_spawn_wickets_creates_four() -> None:
    g = _make_game()
    g._start_game()
    assert len(g.wickets) == 4
    for w in g.wickets:
        assert w.color in BALL_COLORS


# ---- 32. Start game resets all state ----
def test_start_game_resets_state() -> None:
    g = _make_game()
    g._start_game()
    g.score = 500
    g.combo = 10
    g.heat = 80.0
    g.shot_trail = [(1.0, 1.0)]
    g._start_game()
    assert g.score == 0
    assert g.combo == 0
    assert g.heat == 0.0
    assert len(g.shot_trail) == 0
    assert len(g.balls) == 4
    assert len(g.wickets) == 4
    assert g.phase == Phase.AIMING


# ---- 33. Difficulty: wickets move ----
def test_difficulty_wickets_move() -> None:
    g = _make_game(seed=123)
    g._start_game()
    old_positions = [(w.x, w.y) for w in g.wickets]
    g.wicket_move_timer = 899
    g._update_difficulty()
    new_positions = [(w.x, w.y) for w in g.wickets]
    assert old_positions != new_positions


# ---- 34. Difficulty: wicket clamped to field ----
def test_difficulty_wickets_clamped() -> None:
    g = _make_game(seed=999)
    g._start_game()
    for _ in range(10):
        g.wicket_move_timer = 899
        g._update_difficulty()
    for w in g.wickets:
        assert FIELD_LEFT + 20 <= w.x <= FIELD_RIGHT - 20
        assert FIELD_TOP <= w.y <= FIELD_TOP + 100


# ---- 35. Launch toward nearest targets nearest ball ----
def test_launch_toward_nearest() -> None:
    g = _make_game()
    g._start_game()
    g.cue_ball.x = 160.0
    g.cue_ball.y = 210.0
    g.cue_ball.vx = 0.0
    g.cue_ball.vy = 0.0
    # Place balls at known positions
    g.balls[0].x = 200.0
    g.balls[0].y = 100.0
    g.balls[1].x = 50.0
    g.balls[1].y = 80.0
    g.balls[2].x = 280.0
    g.balls[2].y = 60.0
    g.balls[3].x = 100.0
    g.balls[3].y = 80.0
    g._launch_toward_nearest()
    assert g.cue_ball.vx > 0.0  # should go toward nearest ball


# ---- 36. Collision handles balls at same position ----
def test_check_collisions_edge_dist_zero() -> None:
    g = _make_game()
    g._start_game()
    a = g.cue_ball
    b = g.balls[0]
    a.x, a.y = 100.0, 100.0
    b.x, b.y = 100.0, 100.0  # exactly overlapping
    a.radius = 6
    b.radius = 6
    # Should not crash
    g._check_collisions()


# ---- 37. Multiple balls stop check in super mode ----
def test_all_stopped_all_active() -> None:
    g = _make_game()
    g._start_game()
    for b in g.balls:
        b.active = True
        b.vx = 1.0
        b.vy = 0.0
    g.cue_ball.vx = 0.0
    g.cue_ball.vy = 0.0
    assert g._all_stopped() is False


# ---- 38. All wickets scored triggers respawn ----
def test_all_wickets_scored_respawns() -> None:
    g = _make_game(seed=42)
    g._start_game()
    for w in g.wickets:
        w.scored = True
    g._resolve_shot()
    assert len(g.wickets) == 4
    assert all(not w.scored for w in g.wickets)
    assert sorted(w.color for w in g.wickets) == sorted(c for c in BALL_COLORS)


def _run() -> None:
    tests: list[tuple[str, object]] = [
        ("test_shoot_cue_ball_sets_velocity", test_shoot_cue_ball_sets_velocity),
        ("test_shoot_cue_ball_zero_power", test_shoot_cue_ball_zero_power),
        ("test_update_physics_movement_and_friction", test_update_physics_movement_and_friction),
        ("test_ball_stopping_detection", test_ball_stopping_detection),
        ("test_all_stopped", test_all_stopped),
        ("test_check_collisions_elastic", test_check_collisions_elastic),
        ("test_check_collisions_separated", test_check_collisions_separated),
        ("test_check_wicket_pass_centered", test_check_wicket_pass_centered),
        ("test_check_wicket_pass_outside", test_check_wicket_pass_outside),
        ("test_check_wicket_pass_already_scored", test_check_wicket_pass_already_scored),
        ("test_handle_wicket_score_match", test_handle_wicket_score_match),
        ("test_handle_wicket_score_mismatch", test_handle_wicket_score_mismatch),
        ("test_super_activation_at_threshold", test_super_activation_at_threshold),
        ("test_super_any_color_match", test_super_any_color_match),
        ("test_super_score_multiplier", test_super_score_multiplier),
        ("test_timer_decrements", test_timer_decrements),
        ("test_timer_zero_game_over", test_timer_zero_game_over),
        ("test_heat_decay", test_heat_decay),
        ("test_heat_not_negative", test_heat_not_negative),
        ("test_heat_boundary_penalty", test_heat_boundary_penalty),
        ("test_heat_max_clamped", test_heat_max_clamped),
        ("test_max_combo_tracks_highest", test_max_combo_tracks_highest),
        ("test_best_combo_on_game_over", test_best_combo_on_game_over),
        ("test_ghost_trail_saved_on_successful_shot", test_ghost_trail_saved_on_successful_shot),
        ("test_ghost_trail_not_saved_on_no_combo", test_ghost_trail_not_saved_on_no_combo),
        ("test_ghost_trail_downsamples", test_ghost_trail_downsamples),
        ("test_resolve_shot_resets_cue_ball", test_resolve_shot_resets_cue_ball),
        ("test_spawn_particles", test_spawn_particles),
        ("test_particles_update_and_expire", test_particles_update_and_expire),
        ("test_spawn_balls_creates_four", test_spawn_balls_creates_four),
        ("test_spawn_wickets_creates_four", test_spawn_wickets_creates_four),
        ("test_start_game_resets_state", test_start_game_resets_state),
        ("test_difficulty_wickets_move", test_difficulty_wickets_move),
        ("test_difficulty_wickets_clamped", test_difficulty_wickets_clamped),
        ("test_launch_toward_nearest", test_launch_toward_nearest),
        ("test_check_collisions_edge_dist_zero", test_check_collisions_edge_dist_zero),
        ("test_all_stopped_all_active", test_all_stopped_all_active),
        ("test_all_wickets_scored_respawns", test_all_wickets_scored_respawns),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS {name}")
            passed += 1
        except Exception:
            print(f"  FAIL {name}")
            traceback.print_exc()
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    _run()
